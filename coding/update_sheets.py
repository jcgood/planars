#!/usr/bin/env python3
"""Update existing Google Sheets: add missing columns and missing rows.

Run from the repo root:
    python -m coding update-sheets           # dry run — show what would change
    python -m coding update-sheets --apply   # apply changes to sheets

Operations performed per tab:
  1. Add missing trailing columns (e.g. Comments) after existing param columns
  2. Add missing rows for elements present in the current planar structure
     but absent from the sheet tab

Does NOT renumber positions or restructure existing content — use
python -m coding restructure-sheets for that (archives old sheet, regenerates with carry-over).

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

from . import make_forms as _mf
from .make_forms import build_element_index, _infer_language_id_from_planar_filename
from .generate_sheets import _get_clients, _load_manifest_from_drive

CODED_DATA = ROOT / "coded_data"
_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}
_TRAILING_COLS = ["Comments"]


# ---------------------------------------------------------------------------
# Element index helpers
# ---------------------------------------------------------------------------

def _sheet_element_keys(rows: List[List[str]], header: List[str]) -> Set[Tuple[str, str]]:
    """Return set of (element, position_number) keys present in a sheet tab."""
    try:
        el_idx = header.index("Element")
        pos_idx = header.index("Position_Number")
    except ValueError:
        return set()
    return {
        (row[el_idx].strip(), row[pos_idx].strip())
        for row in rows[1:]
        if len(row) > max(el_idx, pos_idx)
    }


def _planar_rows_for_lang(element_index, lang_id: str) -> List[Tuple[int, str, str]]:
    """Return sorted (pos, element, pos_name) tuples for a language."""
    items = [
        (pos, element, pos_name)
        for _, (pos, pos_name, lang, element) in element_index.items()
        if lang == lang_id
    ]
    return sorted(items, key=lambda t: (t[0], t[1].lower(), t[1]))


# ---------------------------------------------------------------------------
# Structural drift detection
# ---------------------------------------------------------------------------

def _build_planar_pos_map(element_index, lang_id: str) -> Dict[str, int]:
    """Build {position_name: position_number} from the element index."""
    result = {}
    for _, (pos, pos_name, lang, _) in element_index.items():
        if lang == lang_id:
            result[pos_name] = pos
    return result


def _check_structural_drift(
    rows: List[List[str]],
    planar_pos_map: Dict[str, int],
) -> List[str]:
    """Compare sheet position names/numbers against the current planar structure.

    Returns a list of warning strings (empty if no drift detected).
    Drift means a position was inserted, deleted, or renumbered in the planar
    file since the sheet was generated.
    """
    if len(rows) < 2:
        return []
    header = rows[0]
    try:
        name_idx = header.index("Position_Name")
        num_idx  = header.index("Position_Number")
    except ValueError:
        return []

    sheet_pos_map: Dict[str, int] = {}
    for row in rows[1:]:
        if len(row) <= max(name_idx, num_idx):
            continue
        name    = row[name_idx].strip()
        num_str = row[num_idx].strip()
        if name and num_str:
            try:
                sheet_pos_map[name] = int(num_str)
            except ValueError:
                pass

    warnings = []
    for pos_name, sheet_num in sheet_pos_map.items():
        if pos_name.lower() == "v:verbroot":
            continue
        if pos_name not in planar_pos_map:
            warnings.append(
                f"    '{pos_name}' (pos {sheet_num} in sheet) no longer exists in planar structure"
            )
        elif planar_pos_map[pos_name] != sheet_num:
            warnings.append(
                f"    '{pos_name}': sheet has pos {sheet_num}, "
                f"planar has pos {planar_pos_map[pos_name]}"
            )
    return warnings


# ---------------------------------------------------------------------------
# Per-tab update logic
# ---------------------------------------------------------------------------

def _compute_tab_updates(
    ws: gspread.Worksheet,
    element_index,
    lang_id: str,
    param_names: List[str],
) -> Tuple[List[str], List[List[str]]]:
    """Compute missing columns and missing rows for a sheet tab.

    Returns:
        missing_cols: list of column names to add
        missing_rows: list of new rows to append (as lists of strings)
    """
    rows = ws.get_all_values()
    header = rows[0] if rows else []

    # --- Missing trailing columns ---
    missing_cols = [c for c in _TRAILING_COLS if c not in header]

    # --- Missing rows ---
    existing_keys = _sheet_element_keys(rows, header)
    planar_rows = _planar_rows_for_lang(element_index, lang_id)

    num_param_cols = len(param_names)
    num_trailing = len(_TRAILING_COLS)
    total_data_cols = 3 + num_param_cols + num_trailing  # Element, Pos_Name, Pos_Num, params, trailing

    missing_rows = []
    for pos, element, pos_name in planar_rows:
        element = element.strip()
        if element.startswith("-") or element.endswith("-"):
            element = f"[{element}]"
        key = (element, str(pos))
        if key not in existing_keys:
            is_keystone = pos_name.strip().lower() == "v:verbroot"
            param_vals = ["NA"] * num_param_cols if is_keystone else [""] * num_param_cols
            row = [element, pos_name, str(pos)] + param_vals + [""] * num_trailing
            missing_rows.append(row)

    return missing_cols, missing_rows


def _clear_trailing_col_validation(
    ws: gspread.Worksheet,
    num_data_rows: int,
    header: List[str],
) -> None:
    """Remove any data validation from trailing columns (e.g. Comments)."""
    for col_name in _TRAILING_COLS:
        if col_name not in header:
            continue
        col_idx = header.index(col_name)  # 0-based
        ws.spreadsheet.batch_update({"requests": [{
            "setDataValidation": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": 1,
                    "endRowIndex": 1 + num_data_rows,
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1,
                }
                # No "rule" key = clear validation
            }
        }]})


def _apply_tab_updates(
    ws: gspread.Worksheet,
    missing_cols: List[str],
    missing_rows: List[List[str]],
    num_data_rows_current: int,
    param_names: List[str],
    spreadsheet: gspread.Spreadsheet,
) -> None:
    """Apply column and row additions to a sheet tab."""
    rows = ws.get_all_values()
    header = rows[0] if rows else []
    sheet_id = ws.id

    requests = []

    # Add missing columns: expand grid if needed, then write header cell
    for col_name in missing_cols:
        new_col_idx = len(header)  # 0-based
        header.append(col_name)

        # Expand grid to fit the new column
        ws.resize(rows=ws.row_count, cols=new_col_idx + 1)

        # Header cell
        ws.update_cell(1, new_col_idx + 1, col_name)

    # Add missing rows via append
    if missing_rows:
        ws.append_rows(missing_rows, value_input_option="RAW")

    # Re-apply dropdown validation to param columns to cover newly appended rows
    if missing_rows and param_names:
        from .generate_sheets import _format_and_validate
        total_rows = num_data_rows_current + len(missing_rows)
        per_col_values = [["y", "n"]] * len(param_names)
        _format_and_validate(ws, total_rows, per_col_values)

    # Always clear validation from trailing columns (fixes any pre-existing incorrect validation)
    total_rows = num_data_rows_current + len(missing_rows)
    _clear_trailing_col_validation(ws, total_rows, header)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    apply = "--apply" in sys.argv

    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)

    # Load planar structure
    planar_files = sorted(CODED_DATA.glob("*/planar_input/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/planar_input/")
    planar_file = planar_files[0]
    lang_id = _infer_language_id_from_planar_filename(planar_file.name)

    _mf.DATA_DIR = str(planar_file.parent)
    element_index = build_element_index(planar_file.name)
    planar_pos_map = _build_planar_pos_map(element_index, lang_id)

    print(f"{'DRY RUN — ' if not apply else ''}Language: {lang_id}")
    if not apply:
        print("(run with --apply to make changes)\n")

    any_changes = False
    any_drift = False

    for manifest_lang, lang_data in manifest.items():
        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            ss = gc.open_by_key(sheet_info["spreadsheet_id"])

            construction_params = sheet_info.get("construction_params", {})

            for construction in sheet_info["constructions"]:
                try:
                    ws = ss.worksheet(construction)
                except gspread.WorksheetNotFound:
                    print(f"    [{construction}] tab not found, skipping")
                    continue

                param_names = construction_params.get(construction, {}).get("param_names", [])
                rows = ws.get_all_values()
                num_data_rows = max(0, len(rows) - 1)

                # Check for structural drift before anything else
                drift_warnings = _check_structural_drift(rows, planar_pos_map)
                if drift_warnings:
                    any_drift = True
                    print(f"    [{construction}] WARNING: planar structure has changed:")
                    for w in drift_warnings:
                        print(w)
                    print(f"    → Run python -m coding restructure-sheets --apply to rebuild this sheet.")
                    continue

                missing_cols, missing_rows = _compute_tab_updates(
                    ws, element_index, lang_id, param_names
                )

                if not missing_cols and not missing_rows:
                    print(f"    [{construction}] up to date")
                    if apply:
                        # Always clear trailing column validation as a repair step
                        header = rows[0] if rows else []
                        _clear_trailing_col_validation(ws, num_data_rows, header)
                    continue

                any_changes = True
                if missing_cols:
                    print(f"    [{construction}] add column(s): {missing_cols}")
                if missing_rows:
                    elements = [r[0] for r in missing_rows]
                    print(f"    [{construction}] add {len(missing_rows)} row(s): {elements}")

                if apply:
                    _apply_tab_updates(
                        ws, missing_cols, missing_rows,
                        num_data_rows, param_names, ss,
                    )
                    print(f"    [{construction}] done")

    if any_drift:
        print("\nSome sheets are out of sync with the planar structure.")
        print("Run: python -m coding restructure-sheets --apply")
    elif not any_changes:
        print("\nAll sheets are up to date.")
    elif not apply:
        print("\nRun with --apply to make these changes.")
    else:
        print("\nDone.")


if __name__ == "__main__":
    main()
