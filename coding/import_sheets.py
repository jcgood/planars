#!/usr/bin/env python3
"""Import filled Google Sheets annotation forms back to TSVs for analysis.

Run from the repo root:
    python -m coding import-sheets           # skip files that already exist
    python -m coding import-sheets --force   # overwrite existing files

Reads the manifest from Drive (via drive_config.json), downloads each sheet
tab, validates values, and writes {construction}.tsv to
coded_data/{lang_id}/{class_name}/.

Side effect: invalid cells are highlighted pink in the Google Sheet during
import (same behaviour as validate-coding). This write-back happens even
without --force and even when the local TSV is skipped.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

import pandas as pd
import gspread

from .generate_sheets import _get_clients, _load_manifest_from_drive, _open_spreadsheet
from . import validate_coding as _val
from .validate_planar import validate_planar_df as _validate_planar_df
from .validate_diagnostics import validate_diagnostics_df as _validate_diagnostics_df

ERROR_DIR    = ROOT / "import_errors"
PENDING_PATH = ROOT / "pending_changes.json"

# Re-export constants so external code that imported them directly still works.
_STRUCTURAL_COLS  = _val._STRUCTURAL_COLS
_TRAILING_COLS    = _val._TRAILING_COLS
_DEFAULT_EXPECTED = _val._DEFAULT_EXPECTED


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def _get_output_path(lang_id: str, class_name: str, construction: str) -> Path:
    """Return the output TSV path under coded_data/, creating directories as needed."""
    folder = ROOT / "coded_data" / lang_id / class_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{construction}.tsv"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _highlight_invalid_cells(ws, bad_cells: List[Tuple[int, int]]) -> None:
    """Delegate to validate.highlight_cells (kept for backwards compatibility)."""
    _val.highlight_cells(ws, bad_cells)


def _validate_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
) -> Tuple[List[Dict], List[str], List[Tuple[int, int]]]:
    """Delegate to validate.validate_annotation_rows (kept for backwards compatibility).

    Returns (records, warnings, bad_cells) in the original format.
    """
    records, issues = _val.validate_annotation_rows(
        rows, expected_params, tab_name, param_values
    )
    warnings  = [str(i) for i in issues]
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, warnings, bad_cells


# ---------------------------------------------------------------------------
# TSV writing
# ---------------------------------------------------------------------------

def _write_tsv(path: Path, header: List[str], records: List[Dict]) -> None:
    """Write records to a tab-separated file with the given header order.

    Extra keys in records beyond the header are silently ignored
    (extrasaction='ignore').
    """
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=header, delimiter="\t",
            extrasaction="ignore", quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _write_error_report(lang_id: str, lines: List[str], timestamp: str) -> Path:
    """Write warning lines to import_errors/{lang_id}_{timestamp}.txt."""
    ERROR_DIR.mkdir(exist_ok=True)
    report_path = ERROR_DIR / f"{lang_id}_{timestamp}.txt"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Planar / diagnostics Sheet download and change detection
# ---------------------------------------------------------------------------

def _read_sheet_as_df(gc: gspread.Client, spreadsheet_id: str) -> Optional[pd.DataFrame]:
    """Download sheet1 of a Google Sheet and return as a DataFrame, or None if empty."""
    ss = _open_spreadsheet(gc, spreadsheet_id)
    rows = ss.sheet1.get_all_values()
    if not rows:
        return None
    return pd.DataFrame(rows[1:], columns=rows[0], dtype=str).fillna("")


def _position_list(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """Return [(position_number, position_name), ...] from a planar DataFrame."""
    return list(zip(df.get("Position", pd.Series(dtype=str)).astype(str),
                    df.get("Position_Name", pd.Series(dtype=str)).astype(str)))


def _parse_criteria_names(criteria_str: str) -> List[str]:
    """Extract criterion names (stripping brace-syntax values) from a criteria cell."""
    return [s.split("{")[0].strip() for s in criteria_str.split(",") if s.strip()]


def _detect_planar_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    lang_id: str,
) -> Tuple[Set[str], List[Dict]]:
    """Compare old and new planar DataFrames for structural changes.

    Returns (safe_commands, pending_entries).
    safe_commands: set of CLI command strings that can be auto-applied.
    pending_entries: list of dicts for pending_changes.json (destructive changes).
    """
    safe_cmds: Set[str] = set()
    pending: List[Dict] = []

    old_positions = _position_list(old_df)
    new_positions = _position_list(new_df)

    if old_positions == new_positions:
        return safe_cmds, pending  # no structural change; overwrite freely

    old_names = [p[1] for p in old_positions]
    new_names = [p[1] for p in new_positions]
    added_names   = set(new_names) - set(old_names)
    removed_names = set(old_names) - set(new_names)

    if added_names and not removed_names:
        # Check old positions appear in same relative order within new list
        it = iter(old_names)
        cur = next(it, None)
        for name in new_names:
            if cur and name == cur:
                cur = next(it, None)
        in_order = cur is None
        if in_order:
            print(f"  [planar] New positions: {sorted(added_names)} — queuing update-sheets")
            safe_cmds.add("python -m coding update-sheets --apply")
            return safe_cmds, pending

    # Deletions or reordering — destructive
    diff_parts: List[str] = []
    if removed_names:
        diff_parts.append(f"Removed positions: {sorted(removed_names)}")
    if added_names:
        diff_parts.append(f"Added positions (alongside removals/reorder): {sorted(added_names)}")
    if not removed_names and not added_names:
        diff_parts.append("Position order changed")
    diff_parts.append(f"Old order: {' | '.join(old_names)}")
    diff_parts.append(f"New order: {' | '.join(new_names)}")

    pending.append({
        "lang_id": lang_id,
        "change_type": "planar_deletion_or_reorder",
        "description": "Planar structure has deleted or reordered positions — restructure-sheets required",
        "diff_summary": "\n".join(diff_parts),
        "command": "python -m coding restructure-sheets --apply",
    })
    return safe_cmds, pending


def _detect_diagnostics_changes(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    lang_id: str,
) -> Tuple[Set[str], List[Dict]]:
    """Compare old and new diagnostics DataFrames for changes to criteria and constructions.

    Returns (safe_commands, pending_entries).
    """
    safe_cmds: Set[str] = set()
    pending: List[Dict] = []

    def _parse_row(row) -> Tuple[Set[str], Set[str]]:
        criteria = set(_parse_criteria_names(str(row.get("Criteria", ""))))
        constructions = {c.strip() for c in str(row.get("Constructions", "")).split(",") if c.strip()}
        return criteria, constructions

    old_by_class: Dict[str, Tuple[Set, Set]] = {}
    for _, row in old_df.iterrows():
        cls = str(row.get("Class", "")).strip()
        if cls:
            old_by_class[cls] = _parse_row(row)

    new_by_class: Dict[str, Tuple[Set, Set]] = {}
    for _, row in new_df.iterrows():
        cls = str(row.get("Class", "")).strip()
        if cls:
            new_by_class[cls] = _parse_row(row)

    all_classes = set(old_by_class) | set(new_by_class)
    for cls in sorted(all_classes):
        if cls not in old_by_class:
            print(f"  [diagnostics] New class '{cls}' — queuing generate-sheets")
            safe_cmds.add("python -m coding generate-sheets")
            continue
        if cls not in new_by_class:
            pending.append({
                "lang_id": lang_id,
                "change_type": "diagnostics_class_removed",
                "description": f"Analysis class '{cls}' removed from diagnostics_{lang_id}.tsv",
                "diff_summary": f"Class '{cls}' was in old diagnostics but not in new.",
                "command": "python -m coding sync-params --remove --apply",
            })
            continue

        old_criteria, old_constructions = old_by_class[cls]
        new_criteria, new_constructions = new_by_class[cls]

        added_criteria   = new_criteria   - old_criteria
        removed_criteria = old_criteria   - new_criteria
        added_cons       = new_constructions - old_constructions
        removed_cons     = old_constructions - new_constructions

        if added_criteria:
            print(f"  [diagnostics/{cls}] New criteria: {sorted(added_criteria)} — queuing sync-params")
            safe_cmds.add("python -m coding sync-params --apply")

        if removed_criteria:
            diff = (
                f"Class '{cls}': criteria removed: {sorted(removed_criteria)}\n"
                f"If renamed: python -m coding sync-params --rename old:new --apply\n"
                f"If removed: python -m coding sync-params --remove --apply"
            )
            pending.append({
                "lang_id": lang_id,
                "change_type": "diagnostics_criteria_removed",
                "description": f"Criteria removed from class '{cls}' — rename or removal required",
                "diff_summary": diff,
                "command": "python -m coding sync-params --remove --apply",
            })

        if added_cons:
            diff = (
                f"Class '{cls}': new constructions: {sorted(added_cons)}\n"
                f"Add new tab(s) to the existing {cls}_{lang_id} sheet manually,\n"
                f"or run generate-sheets --force to recreate (archives existing annotations)."
            )
            pending.append({
                "lang_id": lang_id,
                "change_type": "diagnostics_new_construction",
                "description": f"New construction(s) in class '{cls}' — new sheet tab required",
                "diff_summary": diff,
                "command": "python -m coding generate-sheets",
            })

        if removed_cons:
            pending.append({
                "lang_id": lang_id,
                "change_type": "diagnostics_construction_removed",
                "description": f"Construction(s) removed from class '{cls}'",
                "diff_summary": f"Class '{cls}': removed: {sorted(removed_cons)}",
                "command": "python -m coding sync-params --apply",
            })

    return safe_cmds, pending


def _append_pending_changes(new_entries: List[Dict]) -> None:
    """Append new_entries to pending_changes.json, preserving existing entries."""
    if not new_entries:
        return
    existing: List[Dict] = []
    if PENDING_PATH.exists():
        try:
            existing = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    PENDING_PATH.write_text(
        json.dumps(existing + new_entries, indent=2), encoding="utf-8"
    )


def _download_planar_input_sheets(
    gc: gspread.Client,
    lang_id: str,
    lang_data: Dict,
) -> Tuple[Set[str], List[Dict]]:
    """Download planar and diagnostics Sheets for one language to local TSVs.

    Validates the downloaded data before writing. Detects structural changes
    and classifies them as safe (auto-applicable) or destructive (pending).

    Returns (safe_commands, pending_entries).
    """
    safe_cmds: Set[str] = set()
    pending: List[Dict] = []

    planar_dir = ROOT / "coded_data" / lang_id / "planar_input"

    # --- Planar sheet ---
    planar_id = lang_data.get("planar_spreadsheet_id")
    if planar_id:
        new_df = _read_sheet_as_df(gc, planar_id)
        if new_df is not None:
            issues = _validate_planar_df(new_df)
            errors = [i for i in issues if i.level == "error"]
            if errors:
                print(f"  [planar] Validation errors — skipping download:")
                for i in errors:
                    print(f"    {i}")
            else:
                for i in issues:
                    print(f"  [planar] WARNING: {i}")

                existing = sorted(planar_dir.glob("planar_*.tsv")) if planar_dir.exists() else []
                if existing:
                    old_df = pd.read_csv(existing[-1], sep="\t", dtype=str).fillna("")
                    s, p = _detect_planar_changes(old_df, new_df, lang_id)
                    safe_cmds |= s
                    pending   += p
                    out_path = existing[-1]   # overwrite most recent file in place
                else:
                    from datetime import date
                    today    = date.today().strftime("%Y%m%d")
                    out_path = planar_dir / f"planar_{lang_id}-{today}.tsv"

                planar_dir.mkdir(parents=True, exist_ok=True)
                new_df.to_csv(out_path, sep="\t", index=False)
                print(f"  [planar] Downloaded → {out_path.name}")

    # --- Diagnostics sheet ---
    diag_id = lang_data.get("diagnostics_spreadsheet_id")
    if diag_id:
        new_df = _read_sheet_as_df(gc, diag_id)
        if new_df is not None:
            issues = _validate_diagnostics_df(new_df, lang_id)
            errors = [i for i in issues if i.level == "error"]
            if errors:
                print(f"  [diagnostics] Validation errors — skipping download:")
                for i in errors:
                    print(f"    {i}")
            else:
                for i in issues:
                    print(f"  [diagnostics] WARNING: {i}")

                diag_path = planar_dir / f"diagnostics_{lang_id}.tsv"
                if diag_path.exists():
                    old_df = pd.read_csv(diag_path, sep="\t", dtype=str).fillna("")
                    s, p = _detect_diagnostics_changes(old_df, new_df, lang_id)
                    safe_cmds |= s
                    pending   += p

                planar_dir.mkdir(parents=True, exist_ok=True)
                new_df.to_csv(diag_path, sep="\t", index=False)
                print(f"  [diagnostics] Downloaded → {diag_path.name}")

    return safe_cmds, pending


def main() -> None:
    """Entry point for `python -m coding import-sheets`.

    Loads the manifest from Drive, downloads each construction tab, validates
    values, and writes filled TSVs under coded_data/{lang_id}/{class_name}/.
    Skips existing files unless --force is passed. Writes an error report to
    import_errors/ if any warnings are generated.
    """
    force = "--force" in sys.argv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("Connecting to Google...")
    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)

    total_files = 0
    total_warnings = 0
    all_safe_cmds: Set[str] = set()
    all_pending: List[Dict] = []

    for lang_id, lang_data in manifest.items():
        print(f"\nLanguage: {lang_id}")
        lang_warning_lines: List[str] = []

        # Download planar and diagnostics Sheets to local TSVs; detect changes.
        s, p = _download_planar_input_sheets(gc, lang_id, lang_data)
        all_safe_cmds |= s
        all_pending   += p

        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            ss = _open_spreadsheet(gc, sheet_info["spreadsheet_id"])

            for construction in sheet_info["constructions"]:
                try:
                    ws = ss.worksheet(construction)
                except gspread.WorksheetNotFound:
                    msg = f"[{class_name}/{construction}] tab not found in sheet, skipping"
                    print(f"    WARNING: {msg}")
                    lang_warning_lines.append(f"WARNING: {msg}")
                    total_warnings += 1
                    continue

                rows = ws.get_all_values()

                # Determine expected params from header row (skip structural cols)
                expected_params = (
                    [c for c in rows[0] if c not in _STRUCTURAL_COLS] if rows else []
                )
                header = rows[0] if rows else []

                # Per-param allowed values from manifest (if present)
                construction_params = sheet_info.get("construction_params", {})
                param_values = construction_params.get(construction, {}).get("param_values")

                records, warnings, bad_cells = _validate_tab(rows, expected_params, construction, param_values)

                if bad_cells:
                    try:
                        _highlight_invalid_cells(ws, bad_cells)
                    except Exception as e:
                        print(f"    WARNING: could not highlight cells: {e}")

                for w in warnings:
                    print(f"    WARNING: {w}")
                    lang_warning_lines.append(f"[{class_name}/{construction}] {w}")
                total_warnings += len(warnings)

                out_path = _get_output_path(lang_id, class_name, construction)
                out_name = out_path.name

                if out_path.exists() and not force:
                    print(f"    [{construction}] SKIPPED (file exists, use --force to overwrite) → coded_data/{lang_id}/{class_name}/{out_name}")
                    continue

                _write_tsv(out_path, header, records)

                # Count non-keystone rows that still have at least one blank param cell,
                # so the status line can warn the user about incomplete annotations.
                blank_count = sum(
                    1 for r in records
                    if r.get("Position_Name", "").lower() != "v:verbstem"
                    and any(r.get(p, "") == "" for p in expected_params)
                )
                status = f"{len(records)} rows"
                if blank_count:
                    status += f", {blank_count} blank param cells"
                print(f"    [{construction}] {status} → coded_data/{lang_id}/{class_name}/{out_name}")
                total_files += 1

        if lang_warning_lines:
            report_path = _write_error_report(lang_id, lang_warning_lines, timestamp)
            print(f"\n  Error report: {report_path.relative_to(ROOT)}")

    print(f"\nDone. {total_files} file(s) written, {total_warnings} warning(s).")

    # Write destructive changes to pending_changes.json for coordinator review.
    if all_pending:
        _append_pending_changes(all_pending)
        print(f"\n⚠  {len(all_pending)} destructive change(s) written to pending_changes.json")
        print("   Review and apply with: python -m coding apply-pending")

    # Auto-apply safe downstream commands (new elements → update-sheets, etc.)
    if all_safe_cmds:
        print(f"\nAuto-applying {len(all_safe_cmds)} safe downstream command(s):")
        import importlib
        for cmd in sorted(all_safe_cmds):
            print(f"  {cmd}")
            parts = cmd.split()
            # parts: ["python", "-m", "coding", "<command>", ...]
            mod_name = "coding." + parts[3].replace("-", "_")
            extra_args = parts[4:]
            sys.argv = [parts[3]] + extra_args
            mod = importlib.import_module(mod_name)
            mod.main()


if __name__ == "__main__":
    main()
