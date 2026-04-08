#!/usr/bin/env python3
"""Sync param columns in existing Google Sheets when diagnostics_{lang_id}.yaml changes.

Usage:
    python -m coding sync-params                                         # dry run
    python -m coding sync-params --apply                                 # apply changes to sheets
    python -m coding sync-params --apply --remove                        # also remove stale columns
    python -m coding sync-params --apply --rename old:new                # rename criterion in all classes
    python -m coding sync-params --apply --rename class:old:new          # rename in one class only
    python -m coding sync-params --apply --split old:new1:new2           # split one criterion into two
    python -m coding sync-params --apply --merge old1:old2:new           # merge two criteria into one
    python -m coding sync-params --refresh-dropdowns                     # dry run: show stale dropdowns
    python -m coding sync-params --refresh-dropdowns --apply             # push updated allowed values to sheets

This script propagates diagnostic criterion changes across all downstream layers:

  diagnostics_{lang_id}.yaml — per-language criterion source of truth (edit this)
  diagnostics_{lang_id}.tsv  — derived artifact (regenerated to match YAML after each run)
  Google Sheets              — annotation form column headers (always updated)

Imported TSVs in coded_data/ are downstream of Sheets; re-run import-sheets --force after
any lifecycle operation to bring them in sync.

--rename renames a criterion in-place, preserving all cell values and validation.
--split adds new1/new2 columns and renames old to _split_old; coordinator remaps values then
  removes the stale column manually.
--merge adds a new column and renames old1/old2 to _merged_old1/_merged_old2; same cleanup.

integrity-check --sheets warns on any _split_ or _merged_ prefixed column headers.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

import pandas as pd
import gspread

import yaml as _yaml

from .make_forms import (
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
    _tsv_df_to_yaml,
    _dump_diagnostics_yaml,
    _resolve_diagnostics_yaml_path,
)
from .drive import (
    _get_clients, _load_manifest_from_drive, _upload_planars_config,
    _load_drive_config, _save_drive_config, _open_spreadsheet,
)
from .generate_sheets import CODED_DATA, _TRAILING_COLS

_TRAILING_SET = set(_TRAILING_COLS)


# ---------------------------------------------------------------------------
# Sheet introspection
# ---------------------------------------------------------------------------

def _get_current_params(ws: gspread.Worksheet) -> Tuple[List[str], int]:
    """Return (param_names, comments_col_0based) from the header row.

    Fixed columns: Element (0), Position_Name (1), Position_Number (2).
    Param columns follow; trailing columns (Comments) come last.
    """
    header = ws.row_values(1)
    fixed_count = 3  # Element, Position_Name, Position_Number
    params = []
    comments_col = len(header)  # default: insert at end if Comments not found
    for i in range(fixed_count, len(header)):
        if header[i] in _TRAILING_SET:
            comments_col = i
            break
        params.append(header[i])
    return params, comments_col


# ---------------------------------------------------------------------------
# Column rename
# ---------------------------------------------------------------------------

def _rename_column(ws: gspread.Worksheet, old_name: str, new_name: str) -> bool:
    """Rename a column header in-place. Returns True if found and renamed."""
    header = ws.row_values(1)
    try:
        col_1based = header.index(old_name) + 1
    except ValueError:
        return False
    ws.update_cell(1, col_1based, new_name)
    return True


# ---------------------------------------------------------------------------
# Criterion token manipulation (diagnostics_{lang_id}.tsv — Criteria cell)
# ---------------------------------------------------------------------------

def _criterion_name_from_spec(spec: str) -> str:
    """Extract criterion name from a spec, stripping brace-syntax values.

    'free'               -> 'free'
    'stressed{y/n/both}' -> 'stressed'
    """
    return spec.split("{")[0].strip()


def _rename_criterion_in_cell(cell: str, old: str, new: str) -> str:
    """Rename criterion token 'old' to 'new' in a comma-separated Criteria cell.

    Preserves brace-syntax value lists on the renamed criterion.
    """
    specs = [s.strip() for s in cell.split(",") if s.strip()]
    result = []
    for spec in specs:
        name = _criterion_name_from_spec(spec)
        if name == old:
            brace_part = spec[len(name):]   # e.g. '{y/n/both}' or ''
            result.append(new + brace_part)
        else:
            result.append(spec)
    return ", ".join(result)


def _split_criterion_in_cell(cell: str, old: str, new1: str, new2: str) -> str:
    """Replace criterion 'old' with 'new1, new2' in a Criteria cell."""
    specs = [s.strip() for s in cell.split(",") if s.strip()]
    result = []
    for spec in specs:
        if _criterion_name_from_spec(spec) == old:
            result.extend([new1, new2])
        else:
            result.append(spec)
    return ", ".join(result)


def _merge_criteria_in_cell(cell: str, old1: str, old2: str, new: str) -> str:
    """Replace criterion tokens 'old1' and 'old2' with 'new' in a Criteria cell.

    The new token is inserted at the position of the first matched old token.
    """
    specs = [s.strip() for s in cell.split(",") if s.strip()]
    result = []
    inserted = False
    for spec in specs:
        name = _criterion_name_from_spec(spec)
        if name in (old1, old2):
            if not inserted:
                result.append(new)
                inserted = True
        else:
            result.append(spec)
    return ", ".join(result)


def _update_diagnostics_tsv(
    diag_path: "Path",
    transform_fn,
    class_filter: Optional[str],
    dry_run: bool,
) -> List[str]:
    """Apply transform_fn to the Criteria cell of each matching row.

    transform_fn: (cell: str) -> str
    class_filter: restrict to this Class value (None = all rows)
    dry_run: if True, return descriptions without writing

    Returns list of human-readable change descriptions.
    """
    df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
    changes = []

    for i, row in df.iterrows():
        if class_filter and row.get("Class", "") != class_filter:
            continue
        old_val = row.get("Criteria", "")
        new_val = transform_fn(old_val)
        if new_val != old_val:
            cls = row.get("Class", "?")
            changes.append(
                f"  [{cls}] diagnostics Criteria: {old_val!r} -> {new_val!r}"
            )
            if not dry_run:
                df.at[i, "Criteria"] = new_val

    if not dry_run and changes:
        df.to_csv(diag_path, sep="\t", index=False)

    return changes


# ---------------------------------------------------------------------------
# Column insertion
# ---------------------------------------------------------------------------

def _insert_param_columns(
    ws: gspread.Worksheet,
    new_params: List[str],
    param_values_map: Dict[str, List[str]],
    comments_col_0based: int,
) -> None:
    """Insert new param columns before the trailing (Comments) column."""
    if not new_params:
        return

    spreadsheet = ws.spreadsheet
    sheet_id = ws.id
    n = len(new_params)
    insert_at = comments_col_0based  # 0-based column index to insert before

    # 1. Insert n blank columns at insert_at
    spreadsheet.batch_update({"requests": [{
        "insertDimension": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": insert_at,
                "endIndex": insert_at + n,
            },
            "inheritFromBefore": False,
        }
    }]})

    # 2. Read all values to know row count and find keystone row
    all_values = ws.get_all_values()
    num_rows = len(all_values)

    keystone_row: Optional[int] = None
    for i, row in enumerate(all_values):
        if i == 0:
            continue
        if len(row) > 1 and row[1].strip().lower() == "v:verbstem":
            keystone_row = i + 1  # 1-based
            break

    # 3. Build and write the values grid (header + data rows)
    grid = [new_params]  # header row
    for row_1based in range(2, num_rows + 1):
        if row_1based == keystone_row:
            grid.append(["NA"] * n)
        else:
            grid.append([""] * n)

    start_cell = gspread.utils.rowcol_to_a1(1, insert_at + 1)
    ws.update(grid, start_cell)

    # 4. Apply dropdown validation for each new column
    validation_requests = []
    for i, param_name in enumerate(new_params):
        col_idx = insert_at + i
        values = param_values_map.get(param_name, ["y", "n"])
        validation_requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": num_rows,
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": v} for v in values],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        })
    if validation_requests:
        spreadsheet.batch_update({"requests": validation_requests})


# ---------------------------------------------------------------------------
# Split / merge sheet operations
# ---------------------------------------------------------------------------

_STALE_PREFIXES = ("_split_", "_merged_")


def _apply_split_to_sheet(
    ws: gspread.Worksheet,
    old_name: str,
    new1: str,
    new2: str,
    param_values_map: Dict[str, List[str]],
) -> bool:
    """Split old_name into new1 + new2 in a sheet tab.

    Inserts new1 and new2 columns before Comments, then renames old_name to
    _split_{old_name} so annotators can remap values before cleanup.
    Returns True if old_name was found.
    """
    header = ws.row_values(1)
    if old_name not in header:
        return False
    _, comments_col = _get_current_params(ws)
    _insert_param_columns(ws, [new1, new2], param_values_map, comments_col)
    _rename_column(ws, old_name, f"_split_{old_name}")
    return True


def _apply_merge_to_sheet(
    ws: gspread.Worksheet,
    old1: str,
    old2: str,
    new: str,
    param_values_map: Dict[str, List[str]],
) -> Tuple[bool, bool]:
    """Merge old1 and old2 into new in a sheet tab.

    Inserts a new column before Comments, then renames old1/old2 to
    _merged_{old1}/_merged_{old2} so annotators can remap values.
    Returns (old1_found, old2_found).
    """
    header = ws.row_values(1)
    old1_found = old1 in header
    old2_found = old2 in header
    if not old1_found and not old2_found:
        return False, False
    _, comments_col = _get_current_params(ws)
    _insert_param_columns(ws, [new], param_values_map, comments_col)
    if old1_found:
        _rename_column(ws, old1, f"_merged_{old1}")
    if old2_found:
        _rename_column(ws, old2, f"_merged_{old2}")
    return old1_found, old2_found


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _build_dropdown_refresh_requests(
    ws: gspread.Worksheet,
    stale_params: List[str],
    exp_values: Dict[str, List[str]],
) -> List[dict]:
    """Build setDataValidation requests for params with stale allowed values.

    Uses ws.row_count as the end row so validation covers all current data rows.
    """
    if not stale_params:
        return []
    header = ws.row_values(1)
    num_rows = ws.row_count
    requests = []
    for param in stale_params:
        if param not in header:
            continue
        col_idx = header.index(param)  # 0-based
        values = exp_values.get(param, ["y", "n"])
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": 1,
                    "endRowIndex": num_rows,
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": v} for v in values],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        })
    return requests


def _parse_renames() -> List[Tuple[Optional[str], str, str]]:
    """Parse --rename [class:]old:new pairs from sys.argv.

    Returns a list of (class_filter, old, new) tuples. class_filter is None
    when no class prefix is given (applies to all classes).

    Syntax:
        --rename old:new                  # rename in all classes
        --rename stress:stressable:stressed  # rename only in the 'stress' class
    """
    renames = []
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--rename" and i + 1 < len(args):
            pair = args[i + 1]
            renames.append(_parse_rename_pair(pair))
        elif arg.startswith("--rename="):
            pair = arg[len("--rename="):]
            renames.append(_parse_rename_pair(pair))
    return renames


def _parse_rename_pair(pair: str) -> Tuple[Optional[str], str, str]:
    """Parse a single rename value into (class_filter, old, new).

    Two colons → class:old:new; one colon → old:new (no class filter).
    """
    parts = pair.split(":")
    if len(parts) >= 3:
        return parts[0].strip(), parts[1].strip(), ":".join(p.strip() for p in parts[2:])
    elif len(parts) == 2:
        return None, parts[0].strip(), parts[1].strip()
    return None, pair.strip(), pair.strip()


def _parse_splits() -> List[Tuple[str, str, str]]:
    """Parse --split old:new1:new2 pairs from sys.argv.

    Returns a list of (old, new1, new2) tuples.
    """
    result = []
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--split" and i + 1 < len(args):
            parts = args[i + 1].split(":")
            if len(parts) == 3:
                result.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
            else:
                print(f"WARNING: --split requires old:new1:new2, got: {args[i + 1]!r}")
        elif arg.startswith("--split="):
            parts = arg[len("--split="):].split(":")
            if len(parts) == 3:
                result.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return result


def _parse_merges() -> List[Tuple[str, str, str]]:
    """Parse --merge old1:old2:new pairs from sys.argv.

    Returns a list of (old1, old2, new) tuples.
    """
    result = []
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--merge" and i + 1 < len(args):
            parts = args[i + 1].split(":")
            if len(parts) == 3:
                result.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
            else:
                print(f"WARNING: --merge requires old1:old2:new, got: {args[i + 1]!r}")
        elif arg.startswith("--merge="):
            parts = arg[len("--merge="):].split(":")
            if len(parts) == 3:
                result.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return result


def main() -> None:
    """Entry point for `python -m coding sync-params`.

    Compares expected param columns (from diagnostics_{lang_id}.tsv) against actual sheet
    headers, inserts new columns before Comments, optionally removes stale columns,
    applies dropdown validation, and updates the Drive manifest if anything changed.
    In dry-run mode (no --apply) only prints what would change.
    """
    apply = "--apply" in sys.argv
    remove = "--remove" in sys.argv
    refresh_dropdowns = "--refresh-dropdowns" in sys.argv
    renames = _parse_renames()
    splits  = _parse_splits()
    merges  = _parse_merges()

    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)

    any_changes = False
    manifest_changed = False

    for planar_file in planar_files:
        planar_dir = planar_file.parent
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)

        # Update diagnostics_{lang_id}.tsv before re-reading so sheet operations
        # see the already-updated criterion list.
        diag_path = planar_dir / f"diagnostics_{lang_id}.tsv"
        if diag_path.exists():
            for cls_filter, old, new in renames:
                fn = lambda cell, o=old, n=new: _rename_criterion_in_cell(cell, o, n)
                for change in _update_diagnostics_tsv(diag_path, fn, cls_filter, dry_run=not apply):
                    print(change)
            for old, new1, new2 in splits:
                fn = lambda cell, o=old, n1=new1, n2=new2: _split_criterion_in_cell(cell, o, n1, n2)
                for change in _update_diagnostics_tsv(diag_path, fn, None, dry_run=not apply):
                    print(change)
            for old1, old2, new in merges:
                fn = lambda cell, o1=old1, o2=old2, n=new: _merge_criteria_in_cell(cell, o1, o2, n)
                for change in _update_diagnostics_tsv(diag_path, fn, None, dry_run=not apply):
                    print(change)

            # After TSV mutations, regenerate the YAML if one exists.
            yaml_path = _resolve_diagnostics_yaml_path(lang_id, planar_dir)
            if apply and yaml_path.exists() and (renames or splits or merges):
                tsv_df = pd.read_csv(diag_path, sep="\t", dtype=str, keep_default_na=False)
                # Preserve fields not in the TSV (e.g. notes) by loading existing YAML first.
                with open(yaml_path, encoding="utf-8") as _f:
                    existing_yaml = _yaml.safe_load(_f)
                new_yaml = _tsv_df_to_yaml(tsv_df, lang_id)
                # Merge: carry over notes from existing YAML into regenerated structure.
                for cls, cls_data in (existing_yaml.get("classes") or {}).items():
                    if cls in new_yaml.get("classes", {}) and "notes" in cls_data:
                        new_yaml["classes"][cls]["notes"] = cls_data["notes"]
                yaml_path.write_text(_dump_diagnostics_yaml(new_yaml), encoding="utf-8")
                print(f"  [{lang_id}] YAML updated → {yaml_path.name}")

        specs = _read_diagnostics_for_language(lang_id, planar_dir)

        # Build expected: class_name -> construction -> (param_names, param_values)
        expected: Dict[str, Dict[str, Tuple[List[str], Dict[str, List[str]]]]] = {}
        for class_name, construction, param_names, param_values in specs:
            expected.setdefault(class_name, {})[construction] = (param_names, param_values)

        print(f"\nLanguage: {lang_id}")
        print(f"Mode:     {'apply' if apply else 'dry run'}")
        if renames:
            rename_strs = [f"{cls + ':' if cls else ''}{old}:{new}" for cls, old, new in renames]
            print(f"Renames:  {rename_strs}")
        if splits:
            print(f"Splits:   {[f'{o}:{n1}:{n2}' for o, n1, n2 in splits]}")
        if merges:
            print(f"Merges:   {[f'{o1}:{o2}:{n}' for o1, o2, n in merges]}")

        lang_data = manifest.get(lang_id, {})
        sheets = lang_data.get("sheets", {})

        for class_name, sheet_info in sheets.items():
            if class_name not in expected:
                print(f"[{class_name}] Not in diagnostics_{lang_id}.tsv — skipping")
                continue

            ss = _open_spreadsheet(gc, sheet_info["spreadsheet_id"])

            for construction, (exp_params, exp_values) in expected[class_name].items():
                try:
                    ws = ss.worksheet(construction)
                except gspread.WorksheetNotFound:
                    print(f"  [{class_name}/{construction}] Tab not found — skipping")
                    continue

                # Apply renames first so add/remove detection sees the updated headers
                if renames:
                    for cls_filter, old_name, new_name in renames:
                        if cls_filter is not None and cls_filter != class_name:
                            continue
                        found = old_name in ws.row_values(1)
                        if found:
                            print(f"  [{class_name}/{construction}] Rename: {old_name} → {new_name}")
                            if apply:
                                _rename_column(ws, old_name, new_name)
                                any_changes = True
                                # Update manifest construction_params
                                cp = sheet_info.setdefault("construction_params", {})
                                cp.setdefault(construction, {})
                                param_names = cp[construction].get("param_names", [])
                                cp[construction]["param_names"] = [
                                    new_name if p == old_name else p for p in param_names
                                ]
                                manifest_changed = True
                                print(f"    Renamed.")
                        else:
                            print(f"  [{class_name}/{construction}] Rename: {old_name} not found — skipping")

                # Apply splits to this sheet tab
                for old, new1, new2 in splits:
                    default_vals = {new1: ["y", "n"], new2: ["y", "n"]}
                    if old in ws.row_values(1):
                        print(f"  [{class_name}/{construction}] Split: {old} -> {new1}, {new2}")
                        if apply:
                            _apply_split_to_sheet(ws, old, new1, new2, default_vals)
                            cp = sheet_info.setdefault("construction_params", {})
                            cp.setdefault(construction, {})
                            pnames = [p for p in cp[construction].get("param_names", []) if p != old]
                            for p in (new1, new2):
                                if p not in pnames:
                                    pnames.append(p)
                            cp[construction]["param_names"] = pnames
                            manifest_changed = True
                            any_changes = True
                            print(f"    Split applied.")
                    else:
                        print(f"  [{class_name}/{construction}] Split: {old} not found — skipping")

                # Apply merges to this sheet tab
                for old1, old2, new in merges:
                    default_vals = {new: ["y", "n"]}
                    header_now = ws.row_values(1)
                    o1_found = old1 in header_now
                    o2_found = old2 in header_now
                    if o1_found or o2_found:
                        print(f"  [{class_name}/{construction}] Merge: {old1}, {old2} -> {new}")
                        if apply:
                            _apply_merge_to_sheet(ws, old1, old2, new, default_vals)
                            cp = sheet_info.setdefault("construction_params", {})
                            cp.setdefault(construction, {})
                            pnames = [p for p in cp[construction].get("param_names", [])
                                      if p not in (old1, old2)]
                            if new not in pnames:
                                pnames.append(new)
                            cp[construction]["param_names"] = pnames
                            manifest_changed = True
                            any_changes = True
                            print(f"    Merge applied.")
                    else:
                        print(f"  [{class_name}/{construction}] Merge: neither {old1} nor {old2} found — skipping")

                current_params, comments_col = _get_current_params(ws)
                current_set = set(current_params)
                expected_set = set(exp_params)

                # Preserve expected order; only add params that are genuinely new.
                # Exclude _split_/_merged_ stale columns from removed_params — these
                # are preserved intentionally until the coordinator remaps values.
                new_params = [p for p in exp_params if p not in current_set]
                removed_params = [
                    p for p in current_params
                    if p not in expected_set
                    and not any(p.startswith(pfx) for pfx in _STALE_PREFIXES)
                ]

                if not new_params and not removed_params:
                    # Sheet columns match diagnostics. Sync param_names in manifest if needed,
                    # but do NOT update param_values here — only update param_values when dropdowns
                    # are actually pushed to the sheet, so it remains a reliable staleness reference.
                    if apply:
                        cp = sheet_info.setdefault("construction_params", {})
                        existing_cp = cp.get(construction, {})
                        if existing_cp.get("param_names") != exp_params:
                            cp.setdefault(construction, {})["param_names"] = exp_params
                            manifest_changed = True
                            if not refresh_dropdowns:
                                print(f"  [{class_name}/{construction}] Manifest param_names updated")
                        else:
                            if not renames and not splits and not merges and not refresh_dropdowns:
                                print(f"  [{class_name}/{construction}] OK — no changes")
                    else:
                        if not renames and not splits and not merges and not refresh_dropdowns:
                            print(f"  [{class_name}/{construction}] OK — no changes")

                    if refresh_dropdowns:
                        existing_cp = sheet_info.get("construction_params", {}).get(construction, {})
                        stored_values = existing_cp.get("param_values", {})
                        stale = [p for p in exp_params if exp_values.get(p) != stored_values.get(p)]
                        if stale:
                            any_changes = True
                            print(f"  [{class_name}/{construction}] Would update dropdowns:")
                            for p in stale:
                                old = stored_values.get(p, "?")
                                print(f"    {p}: {old} → {exp_values.get(p)}")
                            if apply:
                                requests = _build_dropdown_refresh_requests(ws, stale, exp_values)
                                if requests:
                                    ws.spreadsheet.batch_update({"requests": requests})
                                    cp = sheet_info.setdefault("construction_params", {})
                                    cp.setdefault(construction, {})["param_values"] = exp_values
                                    manifest_changed = True
                                    any_changes = True
                                    print(f"    Done.")
                        else:
                            print(f"  [{class_name}/{construction}] OK — dropdowns up to date")
                    continue

                any_changes = True

                if new_params:
                    print(f"  [{class_name}/{construction}] New params: {new_params}")
                    if apply:
                        _insert_param_columns(ws, new_params, exp_values, comments_col)
                        # Update manifest construction_params so Colab reads the right params
                        cp = sheet_info.setdefault("construction_params", {})
                        cp.setdefault(construction, {})["param_names"] = exp_params
                        cp[construction]["param_values"] = exp_values
                        manifest_changed = True
                        print(f"    Added: {new_params}")

                if removed_params:
                    if remove and apply:
                        print(f"  [{class_name}/{construction}] Removing params: {removed_params}")
                        # Re-read header after any insertions above so indices are current.
                        header = ws.row_values(1)
                        # Delete columns right-to-left to preserve indices during deletion.
                        for param in sorted(removed_params, key=lambda p: header.index(p), reverse=True):
                            col_idx = header.index(param)  # 0-based
                            ws.spreadsheet.batch_update({"requests": [{
                                "deleteDimension": {
                                    "range": {
                                        "sheetId": ws.id,
                                        "dimension": "COLUMNS",
                                        "startIndex": col_idx,
                                        "endIndex": col_idx + 1,
                                    }
                                }
                            }]})
                            header.pop(col_idx)
                        # Update manifest construction_params
                        cp = sheet_info.setdefault("construction_params", {})
                        cp.setdefault(construction, {})["param_names"] = exp_params
                        cp[construction]["param_values"] = exp_values
                        manifest_changed = True
                        print(f"    Removed: {removed_params}")
                    else:
                        marker = "(pass --apply --remove to delete)" if apply else "(pass --remove with --apply)"
                        print(
                            f"  [{class_name}/{construction}] WARNING: columns in sheet but not in "
                            f"diagnostics: {removed_params}\n    {marker}"
                        )

                # For tabs with structural changes, also refresh dropdowns on existing columns
                # if requested. (New columns already get correct validation from _insert_param_columns.)
                if refresh_dropdowns:
                    existing_cp2 = sheet_info.get("construction_params", {}).get(construction, {})
                    stored_values2 = existing_cp2.get("param_values", {})
                    stale2 = [
                        p for p in exp_params
                        if p not in new_params and exp_values.get(p) != stored_values2.get(p)
                    ]
                    if stale2:
                        any_changes = True
                        print(f"  [{class_name}/{construction}] Would update dropdowns on existing columns:")
                        for p in stale2:
                            old = stored_values2.get(p, "?")
                            print(f"    {p}: {old} → {exp_values.get(p)}")
                        if apply:
                            requests = _build_dropdown_refresh_requests(ws, stale2, exp_values)
                            if requests:
                                ws.spreadsheet.batch_update({"requests": requests})
                                cp = sheet_info.setdefault("construction_params", {})
                                cp.setdefault(construction, {})["param_values"] = exp_values
                                manifest_changed = True
                                print(f"    Done.")

    # Update the merged manifest.json on Drive if anything changed.
    if apply and manifest_changed:
        config = _load_drive_config()
        # Ensure folder_id is present in each manifest entry.
        for lid in manifest:
            manifest[lid].setdefault("folder_id", config.get(lid, {}).get("folder_id", ""))
        existing_file_id = config.get("_planars_config_file_id")
        root_folder_id = config.get("_root_folder_id")
        file_id = _upload_planars_config(drive, manifest, root_folder_id, existing_file_id)
        config["_planars_config_file_id"] = file_id
        _save_drive_config(config)
        print("\nManifest updated on Drive.")

    print()
    if not any_changes:
        print("All sheets are up to date.")
    elif not apply:
        apply_args = [a for a in sys.argv[1:] if a != "--apply"] + ["--apply"]
        apply_cmd = "python -m coding sync-params " + " ".join(apply_args)
        print(f"Dry run — changes detected. To apply:\n\n    {apply_cmd}\n")

    if apply and any_changes:
        from .generate_notebooks import regenerate_notebooks
        regenerate_notebooks()


if __name__ == "__main__":
    main()
