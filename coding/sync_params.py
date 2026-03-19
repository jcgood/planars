#!/usr/bin/env python3
"""Sync param columns in existing Google Sheets when diagnostics.tsv changes.

Usage:
    python -m coding sync-params                              # dry run — shows what would change
    python -m coding sync-params --apply                      # apply changes to sheets
    python -m coding sync-params --apply --remove             # also remove columns not in diagnostics
    python -m coding sync-params --apply --rename old:new     # rename a column header in all sheets

This script:
  - Reads diagnostics.tsv to get the expected params for each class/construction
  - Compares against current column headers in each sheet tab
  - In --apply mode: inserts new param columns before Comments, applies dropdown validation
  - Warns about params present in sheets but not in diagnostics (requires --remove to delete)
  - --rename renames a column header in-place, preserving all cell values and validation
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

from . import make_forms as _mf
from .make_forms import (
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from .generate_sheets import (
    _get_clients,
    _load_manifest_from_drive,
    _upload_manifest_to_drive,
    _load_drive_config,
    _save_drive_config,
    CODED_DATA,
    _TRAILING_COLS,
)

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
        if len(row) > 1 and row[1].strip().lower() == "v:verbroot":
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
# Main
# ---------------------------------------------------------------------------

def _parse_renames() -> Dict[str, str]:
    """Parse --rename old:new pairs from sys.argv."""
    renames = {}
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--rename" and i + 1 < len(args):
            pair = args[i + 1]
            if ":" in pair:
                old, new = pair.split(":", 1)
                renames[old.strip()] = new.strip()
        elif arg.startswith("--rename="):
            pair = arg[len("--rename="):]
            if ":" in pair:
                old, new = pair.split(":", 1)
                renames[old.strip()] = new.strip()
    return renames


def main() -> None:
    apply = "--apply" in sys.argv
    remove = "--remove" in sys.argv
    renames = _parse_renames()

    # Find planar file to establish lang_id and DATA_DIR
    planar_files = sorted(CODED_DATA.glob("*/planar_input/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/planar_input/")
    planar_file = planar_files[0]
    planar_dir = planar_file.parent
    lang_id = _infer_language_id_from_planar_filename(planar_file.name)

    _mf.DATA_DIR = str(planar_dir)
    specs = _read_diagnostics_for_language(lang_id)

    # Build expected: class_name -> construction -> (param_names, param_values)
    expected: Dict[str, Dict[str, Tuple[List[str], Dict[str, List[str]]]]] = {}
    for class_name, construction, param_names, param_values in specs:
        expected.setdefault(class_name, {})[construction] = (param_names, param_values)

    print(f"Language: {lang_id}")
    print(f"Mode:     {'apply' if apply else 'dry run'}")
    if renames:
        print(f"Renames:  {renames}")
    print()

    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)
    lang_data = manifest.get(lang_id, {})
    sheets = lang_data.get("sheets", {})

    any_changes = False
    manifest_changed = False

    for class_name, sheet_info in sheets.items():
        if class_name not in expected:
            print(f"[{class_name}] Not in diagnostics.tsv — skipping")
            continue

        ss = gc.open_by_key(sheet_info["spreadsheet_id"])

        for construction, (exp_params, exp_values) in expected[class_name].items():
            try:
                ws = ss.worksheet(construction)
            except gspread.WorksheetNotFound:
                print(f"  [{class_name}/{construction}] Tab not found — skipping")
                continue

            # Apply renames first so add/remove detection sees the updated headers
            if renames:
                for old_name, new_name in renames.items():
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

            current_params, comments_col = _get_current_params(ws)
            current_set = set(current_params)
            expected_set = set(exp_params)

            # Preserve expected order; only add params that are genuinely new
            new_params = [p for p in exp_params if p not in current_set]
            removed_params = [p for p in current_params if p not in expected_set]

            if not new_params and not removed_params:
                # Sheet columns are correct; still sync manifest construction_params
                # in case they were updated out-of-band (e.g. manual column rename).
                if apply:
                    cp = sheet_info.setdefault("construction_params", {})
                    existing_cp = cp.get(construction, {})
                    if existing_cp.get("param_names") != exp_params or existing_cp.get("param_values") != exp_values:
                        cp[construction] = {"param_names": exp_params, "param_values": exp_values}
                        manifest_changed = True
                        print(f"  [{class_name}/{construction}] Manifest construction_params updated")
                    else:
                        if not renames:
                            print(f"  [{class_name}/{construction}] OK — no changes")
                else:
                    if not renames:
                        print(f"  [{class_name}/{construction}] OK — no changes")
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
                    # Column removal not yet implemented
                    print(f"    (column removal not yet implemented — remove manually in Sheets)")
                else:
                    marker = "(pass --apply --remove to delete)" if apply else "(pass --remove with --apply)"
                    print(
                        f"  [{class_name}/{construction}] WARNING: columns in sheet but not in "
                        f"diagnostics: {removed_params}\n    {marker}"
                    )

    # Update Drive manifest if anything changed
    if apply and manifest_changed:
        config = _load_drive_config()
        for lid, ld in manifest.items():
            folder_id = config.get(lid, {}).get("folder_id")
            existing_file_id = config.get(lid, {}).get("manifest_file_id")
            if folder_id:
                file_id = _upload_manifest_to_drive(drive, ld, folder_id, lid, existing_file_id)
                config.setdefault(lid, {})["manifest_file_id"] = file_id
        _save_drive_config(config)
        print("\nManifest updated on Drive.")

    print()
    if not any_changes:
        print("All sheets are up to date.")
    elif not apply:
        print("Dry run — pass --apply to make changes.")


if __name__ == "__main__":
    main()
