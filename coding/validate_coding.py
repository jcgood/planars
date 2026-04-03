#!/usr/bin/env python3
"""Annotation sheet validation and the validate-coding command.

Validates filled annotation sheets (Google Sheets tabs) against their
expected criterion columns and allowed values. Updates pink cell highlighting
so collaborators can find and fix errors without coordinator help.

Run from the repo root:
    python -m coding validate-coding                   # all languages
    python -m coding validate-coding --lang arao1248   # one language

For each annotation sheet, reads current cell values, re-runs validation,
clears stale pink highlights, and re-highlights any remaining invalid cells.
Prints an issue summary to the terminal.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from .drive import _get_clients, _load_manifest_from_drive, _open_spreadsheet
from .generate_sheets import _STATUS_TAB
from .make_forms import (
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from . import make_forms as _mf
from .validate import ValidationIssue
from .validate_planar import validate_planar_df
from .validate_diagnostics import validate_diagnostics_df
from .schemas import load_diagnostic_criteria, load_planar_schema

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STRUCTURAL_COLS  = {"Element", "Position_Name", "Position_Number"}
_TRAILING_COLS    = load_planar_schema().get("trailing_columns", ["Source", "Comments"])
_DEFAULT_EXPECTED = set(load_diagnostic_criteria().get("default_allowed_values", ["y", "n", "na", "?"]))

_PINK  = {"red": 1.0, "green": 0.8, "blue": 0.8}
_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}

_KEYSTONE_NAME = load_planar_schema().get("keystone_position_name", "v:verbstem")

# ---------------------------------------------------------------------------
# Cell highlighting
# ---------------------------------------------------------------------------

def highlight_cells(ws, bad_cells: List[Tuple[int, int]]) -> None:
    """Set pink background on invalid cells. bad_cells are (row_idx, col_idx) 0-based."""
    if not bad_cells:
        return
    requests = [
        {
            "updateCells": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": r,
                    "endRowIndex": r + 1,
                    "startColumnIndex": c,
                    "endColumnIndex": c + 1,
                },
                "rows": [{"values": [{"userEnteredFormat": {"backgroundColor": _PINK}}]}],
                "fields": "userEnteredFormat.backgroundColor",
            }
        }
        for r, c in bad_cells
    ]
    ws.spreadsheet.batch_update({"requests": requests})


def clear_highlights(ws) -> None:
    """Clear all pink highlighting from a worksheet by resetting backgrounds to white."""
    ws.spreadsheet.batch_update({"requests": [{
        "repeatCell": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 0,
                "endRowIndex": ws.row_count,
                "startColumnIndex": 0,
                "endColumnIndex": ws.col_count,
            },
            "cell": {"userEnteredFormat": {"backgroundColor": _WHITE}},
            "fields": "userEnteredFormat.backgroundColor",
        }
    }]})


# ---------------------------------------------------------------------------
# Annotation sheet validation
# ---------------------------------------------------------------------------

def validate_annotation_rows(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
) -> Tuple[List[Dict], List[ValidationIssue]]:
    """Validate annotation sheet rows.

    Returns (records, issues). records are dicts ready to write as TSV rows.
    """
    issues: List[ValidationIssue] = []

    if not rows:
        return [], [ValidationIssue("error", tab_name, "sheet is empty")]

    header    = rows[0]
    data_rows = rows[1:]

    for col in ("Element", "Position_Name", "Position_Number"):
        if col not in header:
            issues.append(ValidationIssue("error", tab_name, f"missing structural column '{col}'"))

    actual_params = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
    if actual_params != expected_params:
        issues.append(ValidationIssue(
            "warning", tab_name,
            f"criterion columns differ from manifest — "
            f"expected {expected_params}, got {actual_params}"
        ))

    col_index  = {name: i for i, name in enumerate(header)}
    param_cols = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]

    records = []
    for row_num, row in enumerate(data_rows, start=2):
        while len(row) < len(header):
            row.append("")

        record   = {col: row[col_index[col]] for col in header if col in col_index}
        pos_name = record.get("Position_Name", "").strip()
        is_keystone = pos_name.lower() == _KEYSTONE_NAME

        for param in param_cols:
            val = record.get(param, "").strip().lower()
            record[param] = val

            allowed = (
                {v.lower() for v in (param_values or {}).get(param, [])} | {"na", "?"}
                if param_values and param in param_values
                else _DEFAULT_EXPECTED
            )

            if is_keystone:
                if val == "":
                    record[param] = "na"
            else:
                if val == "":
                    issues.append(ValidationIssue(
                        "warning",
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                        f"blank value in '{param}'",
                        cell=(row_num - 1, col_index[param]),
                    ))
                elif val not in allowed:
                    issues.append(ValidationIssue(
                        "warning",
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                        f"unexpected value '{val}' in '{param}' (allowed: {sorted(allowed)})",
                        cell=(row_num - 1, col_index[param]),
                    ))

        records.append(record)

    return records, issues


def annotation_status(
    rows: List[List[str]],
    expected_params: List[str],
    param_values: Dict[str, List[str]] = None,
) -> dict:
    """Return completeness/validity counts for one annotation sheet tab.

    Returns {'total': int, 'filled': int, 'blank': int, 'invalid': int}.
    Keystone rows (v:verbstem) are excluded from all counts.
    """
    if not rows or len(rows) < 2:
        return {"total": 0, "filled": 0, "blank": 0, "invalid": 0}

    header = rows[0]
    param_cols = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
    n_params = len(param_cols)
    pos_idx = header.index("Position_Name") if "Position_Name" in header else -1
    n_data_rows = sum(
        1 for row in rows[1:]
        if not (pos_idx >= 0 and len(row) > pos_idx and row[pos_idx].lower() == _KEYSTONE_NAME)
    )
    total = n_data_rows * n_params

    _, issues = validate_annotation_rows(rows, expected_params, "", param_values)
    blank = sum(1 for i in issues if "blank value" in i.message)
    invalid = sum(1 for i in issues if "unexpected value" in i.message)
    return {"total": total, "filled": total - blank, "blank": blank, "invalid": invalid}


def revalidate_sheet(
    ws,
    expected_params: List[str],
    param_values: Dict[str, List[str]] = None,
) -> List[ValidationIssue]:
    """Read a worksheet, validate it, update cell highlighting, return issues.

    Clears all existing highlights first, then re-highlights bad cells.
    Safe to call repeatedly as collaborators fix errors.
    """
    rows = ws.get_all_values()
    _, issues = validate_annotation_rows(rows, expected_params, ws.title, param_values)
    bad_cells = [issue.cell for issue in issues if issue.cell is not None]
    clear_highlights(ws)
    highlight_cells(ws, bad_cells)
    return issues


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _load_param_map(lang_id: str) -> Dict[str, Dict[str, dict]]:
    """Return {class_name: {construction: {params, values}}} for a language."""
    planar_files = sorted((CODED_DATA / lang_id / "planar_input").glob("planar_*.tsv"))
    if not planar_files:
        return {}
    _mf.DATA_DIR = str(planar_files[0].parent)
    inferred = _infer_language_id_from_planar_filename(planar_files[0].name)
    param_map: Dict[str, Dict[str, dict]] = {}
    for class_name, construction, param_names, param_values in _read_diagnostics_for_language(inferred):
        param_map.setdefault(class_name, {})[construction] = {
            "params": param_names,
            "values": param_values,
        }
    return param_map


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    lang_filter = args[args.index("--lang") + 1] if "--lang" in args else None
    verbose = "--verbose" in args

    pending = ROOT / "pending_changes.json"
    if pending.exists() and pending.stat().st_size > 2:
        print("WARNING: Pending destructive changes require coordinator approval.")
        print("         Run: python -m coding apply-pending\n")

    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)
    if not manifest:
        raise SystemExit("No manifest found. Run generate-sheets first.")

    total_blocking = 0
    total_sheets = 0

    for lang_id, lang_data in sorted(manifest.items()):
        if lang_filter and lang_id != lang_filter:
            continue

        param_map = _load_param_map(lang_id)
        if not param_map:
            print(f"\n[{lang_id}] No planar file found — skipping")
            continue

        print(f"\n{lang_id}")

        # Validate planar structure and diagnostics_{lang_id}.tsv.
        planar_files = sorted((CODED_DATA / lang_id / "planar_input").glob("planar_*.tsv"))
        if planar_files:
            planar_df = pd.read_csv(planar_files[0], sep="\t")
            planar_issues = validate_planar_df(planar_df)
            if planar_issues:
                print(f"  Planar validation ({len(planar_issues)} issue(s)):")
                for issue in planar_issues:
                    print(f"    {issue}")

            diag_path = planar_files[0].parent / f"diagnostics_{lang_id}.tsv"
            if diag_path.exists():
                diag_df = pd.read_csv(diag_path, sep="\t")
                diag_issues = validate_diagnostics_df(diag_df, lang_id)
                if diag_issues:
                    print(f"  Diagnostics validation ({len(diag_issues)} issue(s)):")
                    for issue in diag_issues:
                        print(f"    {issue}")

        for class_name, sheet_info in sorted(lang_data.get("sheets", {}).items()):
            sid = sheet_info.get("spreadsheet_id") or sheet_info.get("id")
            if not sid:
                continue
            try:
                ss = _open_spreadsheet(gc, sid)
            except Exception as e:
                print(f"  [{class_name}] could not open spreadsheet: {e}")
                continue

            for ws in ss.worksheets():
                construction = ws.title
                if construction == _STATUS_TAB:
                    continue
                info = param_map.get(class_name, {}).get(construction, {})
                issues = revalidate_sheet(
                    ws,
                    info.get("params", []),
                    info.get("values", {}),
                )
                total_sheets += 1

                # Separate actionable issues from blank-cell completeness noise.
                # Blank cells are expected during annotation and highlighted pink
                # in the Sheet for annotators, but should not trigger exit(1) or
                # clutter the report. Use --verbose to see them individually.
                blocking = [i for i in issues if "blank value" not in i.message]
                blank_count = len(issues) - len(blocking)
                total_blocking += len(blocking)

                if blocking:
                    print(f"  [{class_name}/{construction}] {len(blocking)} issue(s):")
                    for issue in blocking:
                        print(f"    {issue}")
                    if blank_count and not verbose:
                        print(f"    ({blank_count} blank cell(s) — annotation in progress; use --verbose to list)")
                elif blank_count:
                    print(f"  [{class_name}/{construction}] {blank_count} blank cell(s) — annotation in progress")
                else:
                    print(f"  [{class_name}/{construction}] no issues")

                if verbose and blank_count:
                    for issue in issues:
                        if "blank value" in issue.message:
                            print(f"    {issue}")

    print(f"\n{'─' * 50}")
    print(f"Validated {total_sheets} sheet(s).  Blocking issues: {total_blocking}")
    if total_blocking:
        print("Cell highlighting updated in Google Sheets.")
        sys.exit(1)
    else:
        print("All blocking issues cleared. (Pink highlighting for blank cells preserved.)")


if __name__ == "__main__":
    main()
