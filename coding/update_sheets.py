#!/usr/bin/env python3
"""Update existing Google Sheets: add missing rows for new planar elements.

Run from the repo root:
    python -m coding update-sheets           # dry run — show what would change
    python -m coding update-sheets --apply   # apply changes to sheets

Operations performed per tab:
  1. Add missing trailing columns (e.g. Source) before existing ones
  2. Add missing rows for elements present in the current planar structure
     but absent from the sheet tab

Does NOT renumber positions or restructure existing content — use
python -m coding restructure-sheets for that (archives old sheet, regenerates with carry-over).

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

from .make_forms import build_element_index, _infer_language_id_from_planar_filename
from .drive import _get_clients, _load_manifest_from_drive, _open_spreadsheet, _with_retry
from .generate_sheets import _create_status_tab, _move_status_tab_to_end, _TRAILING_COLS

CODED_DATA = ROOT / "coded_data"
_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

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
        if pos_name.lower() == "v:verbstem":
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
# Trailing column helpers
# ---------------------------------------------------------------------------

_TRAILING_ORDER = {col: i for i, col in enumerate(_TRAILING_COLS)}


def _add_trailing_columns(
    ws: gspread.Worksheet,
    header: List[str],
    rows: List[List[str]],
) -> List[str]:
    """Insert any missing trailing columns at their correct ordered position.

    Trailing columns are defined by _TRAILING_COLS (ordered). Each missing
    column is inserted immediately before the first existing trailing column
    that follows it in _TRAILING_COLS order, or appended at the end if none
    follow it.

    Returns the updated header list (mutated in place on the sheet).
    """
    missing = [col for col in _TRAILING_COLS if col not in header]
    if not missing:
        return header

    num_rows = len(rows)  # includes header row
    header = list(header)

    for col_name in missing:
        col_order = _TRAILING_ORDER[col_name]

        # Find the first existing column that is a trailing col ranked after this one
        insert_before_idx = None
        for idx, existing in enumerate(header):
            if existing in _TRAILING_ORDER and _TRAILING_ORDER[existing] > col_order:
                insert_before_idx = idx
                break

        if insert_before_idx is not None:
            insert_col_1 = insert_before_idx + 1  # gspread uses 1-based column indices
        else:
            insert_col_1 = len(header) + 1  # append after all existing columns

        col_data = [col_name] + [""] * (num_rows - 1)
        ws.insert_cols([col_data], col=insert_col_1)
        header.insert(insert_before_idx if insert_before_idx is not None else len(header), col_name)

    return header


# ---------------------------------------------------------------------------
# Per-tab update logic
# ---------------------------------------------------------------------------

def _compute_missing_rows(
    ws: gspread.Worksheet,
    element_index,
    lang_id: str,
    param_names: List[str],
) -> List[List[str]]:
    """Compute rows present in the planar structure but missing from the sheet tab."""
    rows = _with_retry(ws.get_all_values)
    header = rows[0] if rows else []

    existing_keys = _sheet_element_keys(rows, header)
    planar_rows = _planar_rows_for_lang(element_index, lang_id)

    # Count trailing columns (everything after param columns)
    num_trailing = max(0, len(header) - 3 - len(param_names))

    missing_rows = []
    for pos, element, pos_name in planar_rows:
        element = element.strip()
        if element.startswith("-") or element.endswith("-"):
            element = f"[{element}]"
        key = (element, str(pos))
        if key not in existing_keys:
            is_keystone = pos_name.strip().lower() == "v:verbstem"
            param_vals = ["NA"] * len(param_names) if is_keystone else [""] * len(param_names)
            row = [element, pos_name, str(pos)] + param_vals + [""] * num_trailing
            missing_rows.append(row)

    return missing_rows


def _apply_missing_rows(
    ws: gspread.Worksheet,
    missing_rows: List[List[str]],
    num_data_rows_current: int,
    param_names: List[str],
) -> None:
    """Append missing rows and re-apply dropdown validation to param columns.

    Validation is re-applied to all data rows (existing + new) so that the
    dropdown rules cover the full range after appending.

    Args:
        ws: the gspread Worksheet to update.
        missing_rows: rows to append (already formatted with element, pos_name,
            pos_number, param_values, trailing columns).
        num_data_rows_current: count of existing data rows before appending.
        param_names: ordered list of param column names (for validation).
    """
    ws.append_rows(missing_rows, value_input_option="RAW")

    if param_names:
        from .generate_sheets import _format_and_validate
        total_rows = num_data_rows_current + len(missing_rows)
        # Use default y/n validation for newly added rows; per-param custom
        # values are not tracked in update_sheets (use sync_params for that).
        per_col_values = [["y", "n"]] * len(param_names)
        _format_and_validate(ws, total_rows, per_col_values)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding update-sheets`.

    Compares each sheet tab against the current planar structure and appends
    any elements that are present in the planar file but missing from the tab.
    Detects and warns about structural drift (position renumbering) without
    attempting to fix it — use restructure-sheets for that.
    In dry-run mode (no --apply) only prints what would change.
    """
    apply = "--apply" in sys.argv

    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)

    # Build element index and planar position map for every language
    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    lang_planar_data: Dict[str, tuple] = {}
    for planar_file in planar_files:
        lid = _infer_language_id_from_planar_filename(planar_file.name)
        ei = build_element_index(planar_file.name, planar_file.parent)
        lang_planar_data[lid] = (ei, _build_planar_pos_map(ei, lid))

    print(f"{'DRY RUN — ' if not apply else ''}Languages: {list(lang_planar_data.keys())}")
    if not apply:
        print("(run with --apply to make changes)\n")

    any_changes = False
    any_drift = False

    for manifest_lang, lang_data in manifest.items():
        if manifest_lang not in lang_planar_data:
            print(f"\n  [{manifest_lang}] No local planar file found — skipping")
            continue
        element_index, planar_pos_map = lang_planar_data[manifest_lang]

        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            ss = _open_spreadsheet(gc, sheet_info["spreadsheet_id"])

            construction_params = sheet_info.get("construction_params", {})
            constructions = sheet_info["constructions"]

            for construction in constructions:
                try:
                    ws = _with_retry(lambda: ss.worksheet(construction))
                except gspread.WorksheetNotFound:
                    print(f"    [{construction}] tab not found, skipping")
                    continue

                param_names = construction_params.get(construction, {}).get("param_names", [])
                rows = _with_retry(ws.get_all_values)
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

                header = rows[0] if rows else []
                missing_trailing = [col for col in _TRAILING_COLS if col not in header]
                if missing_trailing:
                    any_changes = True
                    print(f"    [{construction}] add trailing column(s): {missing_trailing}")
                    if apply:
                        _add_trailing_columns(ws, header, rows)
                        # Re-fetch rows so _compute_missing_rows sees the updated header
                        rows = _with_retry(ws.get_all_values)
                        num_data_rows = max(0, len(rows) - 1)

                missing_rows = _compute_missing_rows(
                    ws, element_index, manifest_lang, param_names
                )

                if not missing_rows and not missing_trailing:
                    print(f"    [{construction}] up to date")
                    continue

                if missing_rows:
                    any_changes = True
                    elements = [r[0] for r in missing_rows]
                    print(f"    [{construction}] add {len(missing_rows)} row(s): {elements}")
                    if apply:
                        _apply_missing_rows(ws, missing_rows, num_data_rows, param_names)

                if apply and (missing_rows or missing_trailing):
                    print(f"    [{construction}] done")

            # Ensure Status tab exists and is last
            if apply:
                _create_status_tab(ss, constructions)
                _move_status_tab_to_end(ss)

    if any_drift:
        print("\nSome sheets are out of sync with the planar structure.")
        print("Run: python -m coding restructure-sheets --apply")
        sys.exit(1)
    elif not any_changes:
        print("\nAll sheets are up to date.")
    elif not apply:
        print("\nRun with --apply to make these changes.")
        sys.exit(1)
    else:
        print("\nDone.")


if __name__ == "__main__":
    main()
