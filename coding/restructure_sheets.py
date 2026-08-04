#!/usr/bin/env python3
"""Restructure existing Google Sheets when the planar structure has changed significantly.

Use this when position numbers have changed or rows have been reordered — situations
where update_sheets.py (which only appends) is insufficient.

Run from the repo root:
    python -m coding restructure-sheets           # dry run — show what would change
    python -m coding restructure-sheets --apply   # archive old sheets and regenerate

    # Map renamed positions so their annotations are carried over instead of dropped:
    python -m coding restructure-sheets --rename-map "old name:new name"
    python -m coding restructure-sheets --rename-map old:new1 --rename-map old2:new2 --apply

    # Map renamed elements (e.g. casing fixes) so their annotations are carried over:
    python -m coding restructure-sheets --rename-element Ad-VP:AD-VP --apply
    python -m coding restructure-sheets --rename-element Ad-VP:AD-VP --rename-element Ad-V:AD-V --apply

    # Split one element into several finer-grained replacements (e.g. a generic
    # placeholder replaced by specific forms) so re-annotators get a pointer back
    # to the old judgment instead of having to hunt for it:
    python -m coding restructure-sheets --split-element "PRON{P,T}:me,you,him,her,it,us,them" --apply

    # Rename an analysis class across all languages (renames sheet, local TSV dir, manifest):
    python -m coding restructure-sheets --rename-class old_class:new_class --apply
    python -m coding restructure-sheets --rename-class old:new1 --rename-class old2:new2 --apply

    --rename-map takes "old_pos_name:new_pos_name" and can be repeated.
    --rename-element takes "old_element:new_element" and can be repeated.
    --split-element takes "old_element:new1,new2,..." (comma-separated, at least 2 targets)
      and can be repeated. There's no principled 1:1 value to carry over from one generic
      old element to several specific new ones, so new rows are left blank as usual — but
      if the old element had existing annotations, each new row's Comments cell gets a
      breadcrumb note pointing back to the archived sheet so re-annotators aren't working
      from memory. An element cannot appear in both --rename-element and --split-element.
      Also cascades into every pair-row construction (nonpermutability's `general`,
      coreference's three, and any future one — found generically via row_type:
      pair_rows, not hardcoded by class name) that references the retired element in
      Element_A/Element_B: each old pair-row fans out into one new row per replacement
      element, left BLANK (never pre-filled with the old value, even though it's often
      linguistically the same fact — a coordinator happening to know the language
      doesn't scale to contributor languages nobody on the team speaks), with the old
      row's criterion value, Source, and Comments quoted verbatim into the new row's
      Comments cell. A row where BOTH sides of a pair are the retired element (a
      self-pair) is left untouched and flagged for manual review instead of guessed at.
      See issues #241/#262 for the design discussion this resolves.
    --rename-class takes "old_class_name:new_class_name" and can be repeated.
    Without these flags, renamed positions/elements are treated as drops + new blank rows.

    IMPORTANT for --rename-class: update diagnostics_{lang_id}.yaml to use the new class name
    BEFORE running this command, then run
        python -m coding sync-diagnostics-yaml --apply
    to regenerate the TSV.
    The pre-flight check will abort if the old name is still present in any language's
    diagnostics file, or if the new name is absent.

What this does per spreadsheet:
  1. Downloads current annotations from each tab
  2. [--apply] Moves the spreadsheet to _archived/ in Drive (renamed to include _v{N})
  3. [--apply] Creates a new spreadsheet from the updated planar structure
  4. Carries over annotations matched by (Element, Position_Name)
  5. Leaves unmatched rows blank for re-annotation
  6. Updates sheets_manifest.json to point to the new spreadsheets

For --rename-class, step 3 creates a spreadsheet under the new class name, and
local TSV directories are renamed in-place (coded_data/{lang}/{old}/ ->
coded_data/{lang}/{new}/) preserving git history.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

import gspread

from .make_forms import (
    build_element_index,
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from .schemas import load_diagnostic_classes
from .drive import (
    _autocommit_data, _check_coded_data_clean, _load_drive_config, _save_drive_config, _with_retry,
    load_manifest, upload_manifest,
)
from .drive_doorway import SpreadsheetHandle, WorksheetHandle, WorksheetNotFound, get_doorway
from .generate_sheets import (
    _annotator_email,
    _build_criterion_notes,
    _build_rows,
    _create_status_tab,
    _format_and_validate,
    _maybe_create_planar_reference_tab,
    _reorder_system_tabs,
    _TRAILING_COLS,
)
from .notify import (
    build_change_comment,
    changed_lang_ids,
    ensure_notification_issue,
    post_notification_comment,
)

MANIFEST_PATH = ROOT / "sheets_manifest.json"
CODED_DATA = ROOT / "coded_data"
_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}


# ---------------------------------------------------------------------------
# Annotation download
# ---------------------------------------------------------------------------

def _download_tab_annotations(
    ws: WorksheetHandle,
) -> Dict[Tuple[str, str], Dict[str, str]]:
    """Download annotations from a tab, keyed by (element, pos_name).

    All non-structural columns (params + Comments) are included in the value dict.
    """
    rows = ws.get_all_values()
    if not rows:
        return {}
    header = rows[0]
    try:
        el_idx = header.index("Element")
        pos_name_idx = header.index("Position_Name")
    except ValueError:
        return {}

    annotation_cols = [
        (i, h) for i, h in enumerate(header) if h not in _STRUCTURAL_COLS
    ]

    result: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in rows[1:]:
        if len(row) <= max(el_idx, pos_name_idx):
            continue
        element = row[el_idx].strip()
        pos_name = row[pos_name_idx].strip()
        key = (element, pos_name)
        values = {col: (row[i] if i < len(row) else "") for i, col in annotation_cols}
        result[key] = values
    return result


# ---------------------------------------------------------------------------
# Rename-aware carry-over lookup
# ---------------------------------------------------------------------------

def _lookup_existing(
    element: str,
    pos_name: str,
    existing: Dict[Tuple[str, str], Dict[str, str]],
    old_for_new: Dict[str, str],
    old_el_for_new: Dict[str, str] = {},
) -> Optional[Dict[str, str]]:
    """Look up an annotation by (element, pos_name), falling back to rename aliases.

    Tries in order:
      1. Direct match: (element, pos_name)
      2. Position rename: (element, old_pos_name)
      3. Element rename: (old_element, pos_name)
      4. Both renames:   (old_element, old_pos_name)
    """
    if (v := existing.get((element, pos_name))) is not None:
        return v
    old_name = old_for_new.get(pos_name)
    if old_name and (v := existing.get((element, old_name))) is not None:
        return v
    old_el = old_el_for_new.get(element)
    if old_el:
        if (v := existing.get((old_el, pos_name))) is not None:
            return v
        if old_name and (v := existing.get((old_el, old_name))) is not None:
            return v
    return None


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _folder_id_from_url(folder_url: str) -> str:
    """Extract the Drive folder ID from a Drive folder URL (last path segment)."""
    return folder_url.rstrip("/").rsplit("/", 1)[-1]


def _lock_archived_sheet(doorway, file_id: str, lang_id: str) -> None:
    """Remove any 'anyone' permission from a just-archived sheet and share it
    read-only with the language's annotator, if one is on file.

    Archived sheets carry real prior judgments (--split-element's breadcrumb
    notes point back to them) so the annotator still needs to be able to open
    and read them — just not edit them, since they're no longer the live copy.

    No doorway-level convenience for removing the 'anyone' grant -- inlined
    here from the same two doorway primitives, same precedent as
    `generate_status_sheet._lock_read_only`.
    """
    for p in doorway.list_permissions(file_id, fields="permissions(id,type)"):
        if p.get("type") == "anyone":
            doorway.delete_permission(file_id, p["id"])
    email = _annotator_email(lang_id)
    if email:
        doorway.create_permission(file_id, type="user", role="reader", email=email)


# ---------------------------------------------------------------------------
# Tab population with carry-over
# ---------------------------------------------------------------------------

def _old_key(
    element: str,
    pos_name: str,
    existing: Dict[Tuple[str, str], Dict[str, str]],
    old_for_new: Dict[str, str],
    old_el_for_new: Dict[str, str],
) -> Tuple[str, str]:
    """Return the key that was actually consumed in existing for this (element, pos_name)."""
    old_el  = old_el_for_new.get(element, element)
    old_pos = old_for_new.get(pos_name, pos_name)
    for key in [(element, pos_name), (element, old_pos), (old_el, pos_name), (old_el, old_pos)]:
        if key in existing:
            return key
    return (element, pos_name)  # fallback (won't be in existing, harmless)


def _write_tab_with_carryover(
    spreadsheet: SpreadsheetHandle,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    rows: List[List[object]],
    existing: Dict[Tuple[str, str], Dict[str, str]],
    rename_map: Dict[str, str],
    element_rename_map: Dict[str, str] = {},
    tsv_path: Optional[Path] = None,
    split_element_map: Dict[str, List[str]] = {},
) -> Tuple[int, int, int]:
    """Create/clear a tab and populate it, carrying over matching annotations.

    Matching is by (Element, Position_Name), with optional rename_map (old→new
    position renames) and element_rename_map (old→new element label renames).

    split_element_map ({old_element: [new1, new2, ...]}) marks elements being split
    into several finer-grained replacements. There's no principled value to carry
    over 1:1 for these (a generic annotation doesn't tell us how each new element
    individually behaves), so they're left as new blank rows — but if the old
    element had existing annotations, the new row's Comments cell gets a breadcrumb
    pointing back to it, since that data is only recoverable from the archived sheet.

    Returns:
        (carried_count, new_count, dropped_count)
    """
    old_for_new    = {v: k for k, v in rename_map.items()}
    old_el_for_new = {v: k for k, v in element_rename_map.items()}
    new_to_old_split: Dict[str, str] = {
        n: old for old, news in split_element_map.items() for n in news
    }
    all_cols = param_names + _TRAILING_COLS
    header = ["Element", "Position_Name", "Position_Number"] + all_cols

    carried = 0
    new = 0
    reachable_old_keys: set = set()
    all_rows = [header]

    for row in rows:
        element = str(row[0])
        pos_name = str(row[1])
        pos_num = str(row[2])
        is_keystone = pos_name.strip().lower() == "v:verbstem"

        old_values = _lookup_existing(element, pos_name, existing, old_for_new, old_el_for_new)
        if old_values is not None:
            param_vals = [old_values.get(p, "") for p in param_names]
            trailing_vals = [old_values.get(c, "") for c in _TRAILING_COLS]
            reachable_old_keys.add(_old_key(element, pos_name, existing, old_for_new, old_el_for_new))
            carried += 1
        else:
            param_vals = ["NA"] * len(param_names) if is_keystone else [""] * len(param_names)
            trailing_vals = [""] * len(_TRAILING_COLS)
            split_source = new_to_old_split.get(element)
            if split_source is not None and existing.get((split_source, pos_name)) is not None:
                if "Comments" in _TRAILING_COLS:
                    c_idx = _TRAILING_COLS.index("Comments")
                    trailing_vals[c_idx] = (
                        f"[split from {split_source} — see archived sheet for prior judgment]"
                    )
            new += 1

        all_rows.append([element, pos_name, pos_num] + param_vals + trailing_vals)

    # Count existing annotations that were not matched by any row in the new structure.
    # These correspond to positions/elements that were removed from the planar file.
    dropped = sum(1 for k in existing if k not in reachable_old_keys)

    if tsv_path is not None:
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        header = all_rows[0]
        pd.DataFrame(all_rows[1:], columns=header).to_csv(tsv_path, sep="\t", index=False)

    try:
        ws = _with_retry(lambda: spreadsheet.worksheet(tab_name))
        ws.clear()
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(rows) + 2, cols=len(all_cols) + 3
        )

    ws.update(all_rows, "A1")
    per_col_values = [param_values.get(p, ["y", "n"]) for p in param_names]
    per_col_notes = _build_criterion_notes(param_names)
    _format_and_validate(ws, len(rows), per_col_values, param_notes=per_col_notes)

    return carried, new, dropped


# ---------------------------------------------------------------------------
# Dry-run stats
# ---------------------------------------------------------------------------

def _compute_stats(
    rows: List[List[object]],
    existing: Dict[Tuple[str, str], Dict[str, str]],
    rename_map: Dict[str, str],
    element_rename_map: Dict[str, str] = {},
) -> Tuple[int, int, int, List[Tuple[str, str]]]:
    """Compute carry-over stats for a dry run without touching any sheet.

    Args:
        rows: new rows from _build_rows (the regenerated planar structure).
        existing: current annotations keyed by (element, pos_name).
        rename_map: {old_pos_name: new_pos_name} for renamed positions.
        element_rename_map: {old_element: new_element} for renamed element labels.

    Returns:
        (carried_count, renamed_count, new_count, dropped_keys) where:
          - carried_count: rows carried over by direct match
          - renamed_count: rows carried over via a rename (position or element)
          - new_count:     rows in rows with no match in existing (need re-annotation)
          - dropped_keys:  (element, pos_name) pairs in existing not matched by any row
    """
    old_for_new    = {v: k for k, v in rename_map.items()}
    old_el_for_new = {v: k for k, v in element_rename_map.items()}
    reachable_old_keys: set = set()
    new = 0
    renamed = 0
    for r in rows:
        element, pos_name = str(r[0]), str(r[1])
        old_values = _lookup_existing(element, pos_name, existing, old_for_new, old_el_for_new)
        if old_values is not None:
            old_k = _old_key(element, pos_name, existing, old_for_new, old_el_for_new)
            reachable_old_keys.add(old_k)
            if old_k != (element, pos_name):
                renamed += 1
        else:
            new += 1
    carried = len(reachable_old_keys) - renamed
    dropped = [k for k in existing if k not in reachable_old_keys]
    return carried, renamed, new, dropped


# ---------------------------------------------------------------------------
# Pair-row cascade rename helpers (for coreference and similar classes)
# ---------------------------------------------------------------------------

_PAIR_POS_COLS = ("Position_A", "Position_B")


def _parse_position_cell(cell: str) -> Optional[Tuple[int, str]]:
    """Parse '5 (v:npsubj1)' → (5, 'v:npsubj1'). Returns None on failure."""
    m = re.match(r"^(\d+)\s+\((.+)\)\s*$", cell.strip())
    if m:
        return int(m.group(1)), m.group(2)
    return None


def _apply_rename_to_position_cell(
    cell: str, rename_map: Dict[str, str]
) -> Tuple[str, bool]:
    """Apply rename_map to a combined position cell. Returns (new_cell, changed)."""
    parsed = _parse_position_cell(cell)
    if parsed is None:
        return cell, False
    num, name = parsed
    new_name = rename_map.get(name, name)
    if new_name == name:
        return cell, False
    return f"{num} ({new_name})", True


def _get_pair_row_constructions() -> Dict[str, Set[str]]:
    """Return {class_name: {construction_name}} for all pair-row constructions."""
    from .schemas import load_diagnostic_classes
    dc = load_diagnostic_classes()
    result: Dict[str, Set[str]] = {}
    for cls in dc.get("classes", []):
        pair_cons = {
            con["name"]
            for con in (cls.get("constructions") or [])
            if isinstance(con, dict) and con.get("row_type") == "pair_rows"
        }
        if pair_cons:
            result[cls["name"]] = pair_cons
    return result


def _pair_construction_criterion(class_name: str, construction: str) -> Optional[str]:
    """Return the single annotated criterion column name for a pair-row construction.

    Every pair_rows construction declares this explicitly in diagnostic_classes.yaml
    (criterion: <name>) -- never inferred/guessed, per the project's "explicit
    registration, never silent default" convention (see #241's design discussion).
    Returns None if the construction isn't found or has no criterion field.
    """
    dc = load_diagnostic_classes()
    for cls in dc.get("classes", []):
        if cls.get("name") != class_name:
            continue
        for con in (cls.get("constructions") or []):
            if isinstance(con, dict) and con.get("name") == construction:
                return con.get("criterion")
    return None


# Element-identity columns pair-row TSVs may use to name a specific element:
# Element_A + Element_B (nonpermutability/general, phrasal_accent/general -- two
# named elements, no position columns) or Element_A alone (coreference's three
# pair constructions -- one named element, Position_A/Position_B/Direction locate
# it and its counterpart structurally, not by element identity).
_PAIR_ELEMENT_COLS = ("Element_A", "Element_B")


def _apply_split_to_pair_rows(
    header: List[str],
    data_rows: List[List[str]],
    split_element_map: Dict[str, List[str]],
    criterion_col: Optional[str],
) -> Tuple[List[List[str]], int, int]:
    """Fan out pair-row(s) referencing a retired (split) element into one row per
    replacement element, per issue #241's resolved design (policy (b)).

    For each data row where Element_A or Element_B (whichever are present in header)
    equals an element being split, generates one new row per replacement element
    with that column substituted, the criterion column BLANKED (never carried
    forward as a live default -- a coordinator happening to know the language
    doesn't scale to contributor languages nobody on the team speaks, see #262).
    The old row's criterion value, Source, and Comments are quoted verbatim into
    the new row's Comments cell (Source is cleared on the new row, ready for a
    fresh citation) so the prior judgment is visible right where the new decision
    needs to be made instead of requiring a hunt through an archived sheet.

    A row where BOTH Element_A and Element_B match an element being split (a
    self-pair) is left untouched but counted separately -- fanning out both sides
    at once has no principled combination to prefer over any other, so it's
    reported for manual review rather than guessed at.

    No-ops (returns data_rows unchanged) if split_element_map is empty or the
    header has no Element_A column at all (not an element-identified pair shape).

    Returns (new_data_rows, n_fanned_out, n_needs_manual_review).
    """
    if not split_element_map or "Element_A" not in header:
        return data_rows, 0, 0

    col_idx = {c: i for i, c in enumerate(header)}
    a_idx = col_idx["Element_A"]
    b_idx = col_idx.get("Element_B")
    comments_idx = col_idx.get("Comments")
    source_idx = col_idx.get("Source")
    crit_idx = col_idx.get(criterion_col) if criterion_col else None

    new_rows: List[List[str]] = []
    n_fanned = 0
    n_manual = 0
    for row in data_rows:
        padded = list(row) + [""] * (len(header) - len(row))
        a_val = padded[a_idx]
        b_val = padded[b_idx] if b_idx is not None else None
        a_hit = a_val in split_element_map
        b_hit = b_val is not None and b_val in split_element_map

        if a_hit and b_hit:
            new_rows.append(row)
            n_manual += 1
            continue
        if not a_hit and not b_hit:
            new_rows.append(row)
            continue

        old_el = a_val if a_hit else b_val
        old_crit_val = padded[crit_idx] if crit_idx is not None else ""
        old_comment = padded[comments_idx] if comments_idx is not None else ""
        old_source = padded[source_idx] if source_idx is not None else ""
        crit_part = (
            f"{criterion_col}={old_crit_val!r}" if criterion_col else None
        )
        breadcrumb = f"[carried from split of {old_el!r}]"
        if crit_part:
            breadcrumb += f" {crit_part}"
        if old_source:
            breadcrumb += f"; old Source: {old_source}"
        if old_comment:
            breadcrumb += f"; old Comments: {old_comment}"

        for new_el in split_element_map[old_el]:
            new_row = list(padded)
            if a_hit:
                new_row[a_idx] = new_el
            else:
                new_row[b_idx] = new_el
            if crit_idx is not None:
                new_row[crit_idx] = ""
            if source_idx is not None:
                new_row[source_idx] = ""
            if comments_idx is not None:
                new_row[comments_idx] = breadcrumb
            new_rows.append(new_row)
            n_fanned += 1

    return new_rows, n_fanned, n_manual


def _count_pair_rename_impacts(tsv_path: Path, rename_map: Dict[str, str]) -> int:
    """Count how many Position_A/Position_B cells in a local TSV would be renamed."""
    if not tsv_path.exists():
        return 0
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    return sum(
        1
        for col in _PAIR_POS_COLS
        if col in df.columns
        for val in df[col]
        if _apply_rename_to_position_cell(val, rename_map)[1]
    )


def _count_pair_split_impacts(
    tsv_path: Path, split_element_map: Dict[str, List[str]], criterion_col: Optional[str]
) -> Tuple[int, int]:
    """Count how many local-TSV rows a split would fan out (and how many need manual
    review as self-pairs), for the dry-run report. See _apply_split_to_pair_rows."""
    if not tsv_path.exists() or not split_element_map:
        return 0, 0
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    _, fanned, manual = _apply_split_to_pair_rows(
        list(df.columns), df.values.tolist(), split_element_map, criterion_col
    )
    return fanned, manual


def _cascade_rename_pair_tsv(tsv_path: Path, rename_map: Dict[str, str]) -> int:
    """Update position name components in Position_A/Position_B cells of a local TSV.

    Parses each combined 'N (name)' cell and replaces the name component when it
    appears in rename_map.  Returns the count of cell values changed.
    """
    if not tsv_path.exists():
        return 0
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    changed = 0
    for col in _PAIR_POS_COLS:
        if col not in df.columns:
            continue
        for i, val in df[col].items():
            new_val, did_change = _apply_rename_to_position_cell(val, rename_map)
            if did_change:
                df.at[i, col] = new_val
                changed += 1
    if changed:
        df.to_csv(tsv_path, sep="\t", index=False)
    return changed


def _cascade_rename_pair_tab(
    ws: WorksheetHandle, rename_map: Dict[str, str]
) -> int:
    """Update position name components in Position_A/Position_B cells of a Drive tab.

    Updates cells in-place via batch_update.  Returns the count of cell values changed.
    """
    all_values = _with_retry(lambda: ws.get_all_values())
    if not all_values:
        return 0
    header = all_values[0]
    col_indices = {col: header.index(col) for col in _PAIR_POS_COLS if col in header}
    if not col_indices:
        return 0

    updates: List[Dict] = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        for col_name, col_idx in col_indices.items():
            cell_val = row[col_idx] if col_idx < len(row) else ""
            new_val, changed = _apply_rename_to_position_cell(cell_val, rename_map)
            if changed:
                col_letter = gspread.utils.rowcol_to_a1(1, col_idx + 1)[:-1]
                updates.append({"range": f"{col_letter}{row_idx}", "values": [[new_val]]})

    if updates:
        _with_retry(lambda: ws.spreadsheet.values_batch_update({
            "valueInputOption": "RAW",
            "data": updates,
        }))
    return len(updates)


def _copy_pair_tab_with_rename(
    old_ss: SpreadsheetHandle,
    new_ss: SpreadsheetHandle,
    tab_name: str,
    rename_map: Dict[str, str],
    param_names: List[str],
    param_values: Dict[str, List[str]],
    split_element_map: Dict[str, List[str]] = {},
    criterion_col: Optional[str] = None,
) -> Tuple[int, int, int, int]:
    """Copy a pair tab from old_ss to new_ss with rename_map applied to position cells
    and split_element_map applied to Element_A/Element_B cells (see
    _apply_split_to_pair_rows, issue #241).

    Used when a class sheet is being archived+recreated and the class has pair
    constructions that should be preserved (not regenerated from the planar structure).
    Returns (rows_copied, cells_renamed, rows_split, rows_needing_manual_review).
    """
    try:
        old_ws = _with_retry(lambda: old_ss.worksheet(tab_name))
        all_values = _with_retry(lambda: old_ws.get_all_values())
    except WorksheetNotFound:
        all_values = []

    if not all_values:
        new_ss.add_worksheet(title=tab_name, rows=10, cols=len(param_names) + 6)
        return 0, 0, 0, 0

    header = all_values[0]
    col_indices = {col: header.index(col) for col in _PAIR_POS_COLS if col in header}
    renamed = 0
    new_data = [header]
    for row in all_values[1:]:
        new_row = list(row)
        for col_name, col_idx in col_indices.items():
            if col_idx < len(new_row):
                new_val, changed = _apply_rename_to_position_cell(new_row[col_idx], rename_map)
                if changed:
                    new_row[col_idx] = new_val
                    renamed += 1
        new_data.append(new_row)

    new_data[1:], split_fanned, split_manual = _apply_split_to_pair_rows(
        header, new_data[1:], split_element_map, criterion_col
    )

    try:
        ws = _with_retry(lambda: new_ss.worksheet(tab_name))
        ws.clear()
    except WorksheetNotFound:
        ws = new_ss.add_worksheet(
            title=tab_name, rows=len(new_data) + 2, cols=len(header) + 2
        )

    ws.update(new_data, "A1")
    per_col = [param_values.get(p, ["y", "n"]) for p in param_names]
    # Column position is derived from the tab's own header, never hardcoded --
    # see docs/data-layer-progress.md's Finding 16. A literal col_start=4 used
    # to sit here; it is right for coreference's four-structural-column pair
    # shape (Element_A, Position_A, Position_B, Direction, THEN the criterion)
    # but wrong for nonpermutability's/phrasal_accent's two-column "general"
    # shape (Element_A, Element_B, THEN the criterion at column 2), where it
    # landed the dropdown on Comments and left the criterion column with none.
    if criterion_col and criterion_col in header:
        col_start = header.index(criterion_col)
    elif param_names and param_names[0] in header:
        col_start = header.index(param_names[0])
    else:
        # Last-resort derived fallback (not a literal guess): the criterion
        # columns are the ones immediately before the trailing columns.
        col_start = len(header) - len(_TRAILING_COLS) - len(param_names)
    _format_and_validate(ws, len(new_data) - 1, per_col, col_start=col_start)
    return len(new_data) - 1, renamed, split_fanned, split_manual


# ---------------------------------------------------------------------------
# Class rename helpers
# ---------------------------------------------------------------------------

def _preflight_rename_class(
    manifest: dict,
    rename_class_map: Dict[str, str],
    planar_files: list,
) -> None:
    """Abort if any language fails the --rename-class pre-flight checks.

    For each rename pair (old_class -> new_class), every language that has
    old_class in the manifest must also have new_class in its diagnostics.tsv
    (and must NOT have old_class in diagnostics.tsv).  This enforces the
    required ordering: edit diagnostics_{lang_id}.tsv first, then rename.
    """
    errors = []
    for planar_file in planar_files:
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)
        try:
            specs = _read_diagnostics_for_language(lang_id, planar_file.parent)
        except Exception:
            continue
        active_classes = {c for c, _, _, _ in specs}
        manifest_classes = set(manifest.get(lang_id, {}).get("sheets", {}).keys())

        for old_class, new_class in rename_class_map.items():
            # Language doesn't involve this rename at all — skip.
            if old_class not in manifest_classes and new_class not in active_classes:
                continue
            # Old class still in diagnostics.tsv — coordinator must remove it first.
            if old_class in active_classes:
                errors.append(
                    f"  {lang_id}: {old_class!r} is still in diagnostics_{lang_id}.tsv.\n"
                    f"    Replace it with {new_class!r} before running --rename-class."
                )
            # Old class in manifest but new class absent from diagnostics.tsv.
            if old_class in manifest_classes and new_class not in active_classes:
                errors.append(
                    f"  {lang_id}: {new_class!r} is not in diagnostics_{lang_id}.tsv.\n"
                    f"    Add it before running --rename-class."
                )

    if errors:
        print("Pre-flight checks failed:\n")
        for e in errors:
            print(e)
        raise SystemExit(1)


def _rename_class_for_language(
    doorway,
    manifest: dict,
    lang_id: str,
    old_class: str,
    new_class: str,
    element_index: dict,
    specs: list,
    apply: bool,
    folder_id: Optional[str],
    planar_path: Optional[Path] = None,
    sheet_links: Optional[List[Tuple[str, str, str]]] = None,
) -> bool:
    """Rename one analysis class for one language.

    Downloads annotations from the old class sheet, archives it, creates a new
    sheet under new_class with all annotations carried over, renames the local
    TSV directory, and updates the manifest in-place.

    Returns True if changes were made (or would be made in dry-run).
    """
    lang_data = manifest.get(lang_id, {})
    sheet_info = lang_data.get("sheets", {}).get(old_class)

    if not sheet_info:
        if lang_data.get("sheets", {}).get(new_class):
            print(f"  {lang_id}/{old_class}: already renamed to {new_class!r} in manifest — skipping")
        else:
            print(f"  {lang_id}/{old_class}: no manifest entry — skipping")
        return False

    version = sheet_info.get("version", 1)
    new_version = version + 1
    constructions = sheet_info.get("constructions", [])

    # Param info from new diagnostics entry
    new_specs = {constr: (pn, pv) for cls, constr, pn, pv in specs if cls == new_class}

    if not new_specs:
        print(f"  {lang_id}/{old_class}: {new_class!r} not found in diagnostics — skipping")
        return False

    print(f"\n  {lang_id}: {old_class} -> {new_class} (v{version}):")

    # Download annotations from old sheet
    ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])
    all_annotations: Dict[str, Dict[Tuple[str, str], Dict[str, str]]] = {}
    for construction in constructions:
        try:
            ws = _with_retry(lambda: ss.worksheet(construction))
            all_annotations[construction] = _download_tab_annotations(ws)
            print(f"    [{construction}] downloaded {len(all_annotations[construction])} rows")
        except WorksheetNotFound:
            all_annotations[construction] = {}
            print(f"    [{construction}] tab not found")

    # Compute carry-over stats (dry-run or apply)
    for construction, (param_names, _) in new_specs.items():
        rows = _build_rows(element_index, lang_id, param_names)
        existing = all_annotations.get(construction, {})
        carried, renamed_count, new_count, dropped = _compute_stats(rows, existing, {}, {})
        parts = [f"carry over {carried}"]
        if renamed_count:
            parts.append(f"rename {renamed_count}")
        if new_count:
            parts.append(f"new blank {new_count}")
        if dropped:
            parts.append(f"drop {len(dropped)}")
        print(f"    [{construction}] {'; '.join(parts)}")

    old_dir = CODED_DATA / lang_id / old_class
    new_dir = CODED_DATA / lang_id / new_class

    if old_dir.exists():
        if new_dir.exists():
            print(f"    WARNING: {new_dir.relative_to(ROOT)} already exists — local rename will be skipped")
        else:
            print(f"    would rename: {old_dir.relative_to(ROOT)} -> {new_dir.relative_to(ROOT)}")
    else:
        print(f"    no local TSVs for {old_class}/")

    print(f"    would archive: {old_class}_{lang_id} → _archived/{old_class}_{lang_id}_v{version}")
    print(f"    would create: {new_class}_{lang_id} (v{new_version})")
    print(f"    would update manifest: {old_class} -> {new_class}")

    if not apply:
        return True

    # --- apply ---

    # Archive old sheet
    if folder_id:
        archive_id = doorway.get_or_create_folder("_archived", parent_id=folder_id)
        doorway.update_file(ss.id, name=f"{old_class}_{lang_id}_v{version}")
        doorway.move_file(ss.id, archive_id)
        _lock_archived_sheet(doorway, ss.id, lang_id)
        print(f"    Archived {old_class}_{lang_id} → _archived/{old_class}_{lang_id}_v{version}")

    # Create new sheet
    sheet_title = f"{new_class}_{lang_id}"
    new_ss = doorway.create_spreadsheet(sheet_title)
    if folder_id:
        doorway.move_file(new_ss.id, folder_id)
        email = _annotator_email(lang_id)
        if email:
            doorway.create_permission(new_ss.id, type="user", role="writer", email=email)

    default_ws = _with_retry(lambda: new_ss.sheet1)
    tab_names = []
    new_construction_params = {}

    for construction in constructions:
        if construction not in new_specs:
            print(f"    [{construction}] not in new diagnostics — skipped")
            continue
        param_names, param_values = new_specs[construction]
        rows = _build_rows(element_index, lang_id, param_names)
        existing = all_annotations.get(construction, {})
        carried, new_count, dropped_count = _write_tab_with_carryover(
            new_ss, construction, param_names, param_values, rows, existing, {}, {}
        )
        tab_names.append(construction)
        new_construction_params[construction] = {
            "param_names": param_names,
            "param_values": param_values,
        }
        print(f"    [{construction}] wrote: carried {carried}, new blank {new_count}, dropped {dropped_count}")

    if default_ws.title not in tab_names:
        new_ss.del_worksheet(default_ws)

    if planar_path:
        created_ref = _maybe_create_planar_reference_tab(new_ss, new_class, planar_path, lang_id)
        if created_ref:
            print(f"    Tab: Planar Structure (planar reference)")
        _reorder_system_tabs(new_ss)

    # Rename local TSV directory in-place (preserves git history)
    if old_dir.exists():
        if new_dir.exists():
            print(f"    WARNING: {new_dir.relative_to(ROOT)} already exists — local rename skipped")
        else:
            old_dir.rename(new_dir)
            print(f"    Renamed: {old_dir.relative_to(ROOT)} -> {new_dir.relative_to(ROOT)}")

    # Update manifest in-place
    del manifest[lang_id]["sheets"][old_class]
    manifest[lang_id]["sheets"][new_class] = {
        "spreadsheet_id": new_ss.id,
        "url": new_ss.url,
        "constructions": tab_names,
        "construction_params": new_construction_params,
        "version": new_version,
    }
    print(f"    Manifest: {old_class} -> {new_class} (v{new_version}): {new_ss.url}")
    if sheet_links is not None:
        sheet_links.append((lang_id, new_class, new_ss.url))
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_flag_map(argv: List[str], flag: str) -> Dict[str, str]:
    """Parse all occurrences of --flag old:new into {old: new}."""
    result: Dict[str, str] = {}
    i = 0
    while i < len(argv):
        if argv[i] == flag and i + 1 < len(argv):
            pair = argv[i + 1]
            if ":" not in pair:
                raise SystemExit(f"{flag} requires 'old:new' format, got: {pair!r}")
            old, new = pair.split(":", 1)
            result[old.strip()] = new.strip()
            i += 2
        else:
            i += 1
    return result


def _parse_split_flag_map(argv: List[str], flag: str) -> Dict[str, List[str]]:
    """Parse all occurrences of --flag old:new1,new2,... into {old: [new1, new2, ...]}.

    Requires at least 2 comma-separated targets per occurrence — a single
    replacement is a rename, not a split, and should use --rename-element instead.
    """
    result: Dict[str, List[str]] = {}
    i = 0
    while i < len(argv):
        if argv[i] == flag and i + 1 < len(argv):
            pair = argv[i + 1]
            if ":" not in pair:
                raise SystemExit(f"{flag} requires 'old:new1,new2,...' format, got: {pair!r}")
            old, news = pair.split(":", 1)
            targets = [n.strip() for n in news.split(",") if n.strip()]
            if len(targets) < 2:
                raise SystemExit(
                    f"{flag} requires at least 2 comma-separated replacement elements, "
                    f"got: {pair!r}\n"
                    f"  (a single replacement is a rename — use --rename-element instead)"
                )
            result[old.strip()] = targets
            i += 2
        else:
            i += 1
    return result


def _describe_split_impacts(
    rows: List[List[object]],
    existing: Dict[Tuple[str, str], Dict[str, str]],
    split_element_map: Dict[str, List[str]],
) -> List[str]:
    """Return human-readable lines describing split-element impacts for a dry run/apply report.

    For each old_element -> [new1, new2, ...] mapping, reports how many of the new
    elements are present in the new row set and whether the old element had existing
    annotations (meaning the new rows will carry a breadcrumb Comments note).
    """
    lines: List[str] = []
    for old, news in split_element_map.items():
        old_positions = {pn for (el, pn) in existing if el == old}
        if not old_positions:
            continue
        news_present = [
            n for n in news
            if any(str(r[0]) == n and str(r[1]) in old_positions for r in rows)
        ]
        if news_present:
            lines.append(
                f"split: {old} -> {', '.join(news)} "
                f"({len(news_present)} new, breadcrumbed to archived sheet)"
            )
    return lines



def main() -> None:
    """Entry point for `python -m coding restructure-sheets`.

    For each class in the manifest, downloads current annotations, optionally
    archives the existing spreadsheet to _archived/ in Drive (renamed to include _v{N}), creates a new
    spreadsheet from the updated planar structure, and carries over matching
    annotations by (Element, Position_Name). Unmatched rows are left blank for
    re-annotation. Updates the manifest on Drive and locally.
    In dry-run mode (no --apply) only prints what would change.

    With --rename-class old:new, renames the class across all languages: archives
    the old sheet, creates a new one under the new name with all annotations
    carried over, renames coded_data/{lang}/{old}/ to coded_data/{lang}/{new}/,
    and updates the manifest.  diagnostics_{lang_id}.tsv must be updated to use
    the new name BEFORE running this command (enforced by pre-flight checks).

    With --split-element old:new1,new2,..., retires one element in favor of several
    finer-grained replacements within the same position. New rows are left blank
    (no principled 1:1 value to carry over from a generic annotation), but each
    gets a Comments breadcrumb pointing back to the archived sheet if the old
    element had existing data, so re-annotators have a pointer to the prior
    judgment instead of needing to remember or hunt for it. This also cascades
    into every pair-row construction referencing the retired element (see
    _apply_split_to_pair_rows) -- not just the "home" element-row construction.
    """
    apply = "--apply" in sys.argv
    rename_map         = _parse_flag_map(sys.argv[1:], "--rename-map")
    element_rename_map = _parse_flag_map(sys.argv[1:], "--rename-element")
    rename_class_map   = _parse_flag_map(sys.argv[1:], "--rename-class")
    split_element_map  = _parse_split_flag_map(sys.argv[1:], "--split-element")
    conflict = set(split_element_map) & set(element_rename_map)
    if conflict:
        raise SystemExit(
            f"Element(s) {sorted(conflict)} appear in both --rename-element and "
            f"--split-element — pick one treatment per element."
        )
    lang_idx = sys.argv.index("--lang") if "--lang" in sys.argv else -1
    lang_filter = sys.argv[lang_idx + 1] if lang_idx >= 0 else None

    if apply:
        # This command reads planar_{lang_id}.tsv/diagnostics_{lang_id}.tsv from
        # coded_data/ as its source of truth for the new sheet structure, and is
        # the single most destructive command in the project (archive-then-
        # recreate, no rollback) -- refuse if a prior step's failed auto-commit
        # left coded_data/ in a stale/reverted state. See update_sheets.py's
        # guard for why (issue #248's stray-row incident).
        _check_coded_data_clean(extensions=(".tsv",))

    doorway = get_doorway()
    manifest = load_manifest(doorway)

    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if lang_filter:
        planar_files = [f for f in planar_files
                        if _infer_language_id_from_planar_filename(f.name) == lang_filter]
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    any_changes = False
    written_tsvs: List[Path] = []
    pair_row_constructions = _get_pair_row_constructions()
    restructured_classes: Set[Tuple[str, str]] = set()
    sheet_links: List[Tuple[str, str, str]] = []  # (lang_id, class_name, url), for the summary
    lang_folder_urls: Dict[str, str] = {}  # lang_id -> Drive folder url (stable across restructures)

    # --rename-class pass: runs before the main restructure loop so the manifest
    # reflects the new class names when the main loop processes each language.
    if rename_class_map:
        print(f"\n{'DRY RUN — ' if not apply else ''}Class renames:")
        for old, new in rename_class_map.items():
            print(f"  {old!r} -> {new!r}")
        _preflight_rename_class(manifest, rename_class_map, list(planar_files))
        for planar_file in planar_files:
            lang_id = _infer_language_id_from_planar_filename(planar_file.name)
            element_index = build_element_index(planar_file.name, planar_file.parent)
            specs = _read_diagnostics_for_language(lang_id, planar_file.parent)
            lang_data = manifest.get(lang_id, {})
            folder_url = lang_data.get("folder_url", "")
            folder_id = _folder_id_from_url(folder_url) if folder_url else None
            for old_class, new_class in rename_class_map.items():
                planar_path = planar_file.parent / f"planar_{lang_id}.tsv"
                changed = _rename_class_for_language(
                    doorway, manifest, lang_id, old_class, new_class,
                    element_index, specs, apply, folder_id, planar_path,
                    sheet_links=sheet_links,
                )
                if changed:
                    any_changes = True

        if not apply:
            print("\nRun with --apply to make these changes.")
            return

    for planar_file in planar_files:
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)

        element_index = build_element_index(planar_file.name, planar_file.parent)
        specs = _read_diagnostics_for_language(lang_id, planar_file.parent)

        classes: Dict[str, List[Tuple[str, List[str], Dict[str, List[str]]]]] = {}
        for class_name, construction, param_names, param_values in specs:
            classes.setdefault(class_name, []).append((construction, param_names, param_values))

        # Mirror the special-case criterion overrides from generate_sheets.py so that
        # restructure produces the same param_names/param_values as initial generation.
        _dc_classes_map = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
        _coreference_pair_criterion = {
            con["name"]: con["criterion"]
            for con in (_dc_classes_map.get("coreference", {}).get("constructions") or [])
            if isinstance(con, dict) and "criterion" in con
        }
        for _cls, _cons in list(classes.items()):
            if _cls == "nonpermutability":
                classes[_cls] = [
                    (c, pn, {"scopal": ["y", "n", "both"]} if c == "element_prescreening" else pv)
                    for c, pn, pv in _cons
                ]
            elif _cls == "coreference":
                _new: List[Tuple[str, List[str], Dict[str, List[str]]]] = []
                for c, pn, pv in _cons:
                    if c == "prescreening":
                        _new.append((c, ["referential"], {"referential": ["y", "n"]}))
                    elif c in _coreference_pair_criterion:
                        crit = _coreference_pair_criterion[c]
                        _new.append((c, [crit], {crit: pv.get(crit, ["y", "n"])}))
                    else:
                        _new.append((c, pn, pv))
                classes[_cls] = _new

        print(f"\n{'DRY RUN — ' if not apply else ''}Language: {lang_id}")
        if rename_map:
            for old, new in rename_map.items():
                print(f"  rename position: {old!r} -> {new!r}")
        if element_rename_map:
            for old, new in element_rename_map.items():
                print(f"  rename element:  {old!r} -> {new!r}")
        if split_element_map:
            for old, news in split_element_map.items():
                print(f"  split element:   {old!r} -> {', '.join(news)}")
        if not apply:
            print("(run with --apply to archive old sheets and regenerate)")

        lang_data = manifest.get(lang_id, {})
        folder_url = lang_data.get("folder_url", "")
        folder_id = _folder_id_from_url(folder_url) if folder_url else None
        if folder_url:
            lang_folder_urls[lang_id] = folder_url

        for class_name, constructions_list in classes.items():
            sheet_info = lang_data.get("sheets", {}).get(class_name)
            if not sheet_info:
                print(f"\n  {class_name}: not in manifest, skipping (run python -m coding generate-sheets --apply first)")
                continue

            version = sheet_info.get("version", 1)
            print(f"\n  {class_name} (current v{version})")

            ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])

            # Step 1: Download current annotations from all tabs
            all_annotations: Dict[str, Dict[Tuple[str, str], Dict[str, str]]] = {}
            for construction in sheet_info["constructions"]:
                try:
                    ws = _with_retry(lambda: ss.worksheet(construction))
                    all_annotations[construction] = _download_tab_annotations(ws)
                    print(f"    [{construction}] downloaded {len(all_annotations[construction])} rows")
                except WorksheetNotFound:
                    all_annotations[construction] = {}
                    print(f"    [{construction}] tab not found")

            # Step 2: Compute and report stats per tab; decide if this class needs restructuring.
            # Pair-row constructions (coreference) are excluded from the element-criterion
            # restructure path and are reported separately.
            class_needs_restructure = False
            for construction, param_names, param_values in constructions_list:
                if construction in pair_row_constructions.get(class_name, set()):
                    if rename_map:
                        tsv_path = CODED_DATA / lang_id / class_name / f"{construction}.tsv"
                        n_cells = _count_pair_rename_impacts(tsv_path, rename_map)
                        if n_cells:
                            print(f"    [{construction}] (pair tab) rename {n_cells} position cell(s)")
                            any_changes = True
                            class_needs_restructure = True
                        else:
                            print(f"    [{construction}] (pair tab) no position renames needed")
                    if split_element_map:
                        tsv_path = CODED_DATA / lang_id / class_name / f"{construction}.tsv"
                        criterion_col = _pair_construction_criterion(class_name, construction)
                        n_fanned, n_manual = _count_pair_split_impacts(
                            tsv_path, split_element_map, criterion_col
                        )
                        if n_fanned or n_manual:
                            msg = f"    [{construction}] (pair tab) split would fan out {n_fanned} row(s)"
                            if n_manual:
                                msg += f", {n_manual} self-pair row(s) need manual review"
                            print(msg)
                            any_changes = True
                            class_needs_restructure = True
                    continue
                rows = _build_rows(element_index, lang_id, param_names)
                existing = all_annotations.get(construction, {})
                carried, renamed, new_count, dropped = _compute_stats(rows, existing, rename_map, element_rename_map)
                parts = [f"carry over {carried}"]
                if renamed:
                    parts.append(f"rename {renamed}")
                parts.append(f"new blank {new_count}")
                if dropped:
                    dropped_labels = [f"{el}@{pn}" for el, pn in dropped]
                    parts.append(f"drop {len(dropped)} ({', '.join(dropped_labels)})")
                print(f"    [{construction}] {'; '.join(parts)}")
                for split_line in _describe_split_impacts(rows, existing, split_element_map):
                    print(f"    [{construction}] {split_line}")
                if renamed or new_count or dropped:
                    class_needs_restructure = True
                    any_changes = True

            if not class_needs_restructure:
                print(f"    (no changes — skipping)")
                continue

            if not apply:
                continue

            # Step 3: Archive existing sheet
            new_version = version + 1
            if folder_id:
                archive_id = doorway.get_or_create_folder("_archived", parent_id=folder_id)
                doorway.update_file(ss.id, name=f"{class_name}_{lang_id}_v{version}")
                doorway.move_file(ss.id, archive_id)
                _lock_archived_sheet(doorway, ss.id, lang_id)
                print(f"    Archived to _archived/{class_name}_{lang_id}_v{version}")

            # Step 4: Create new sheet and populate with carry-over
            sheet_title = f"{class_name}_{lang_id}"
            new_ss = doorway.create_spreadsheet(sheet_title)
            if folder_id:
                doorway.move_file(new_ss.id, folder_id)
                email = _annotator_email(lang_id)
                if email:
                    doorway.create_permission(new_ss.id, type="user", role="writer", email=email)

            default_ws = _with_retry(lambda: new_ss.sheet1)
            tab_names = []
            new_construction_params = {}

            for construction, param_names, param_values in constructions_list:
                if construction in pair_row_constructions.get(class_name, set()):
                    # Pair-row constructions are copied from the archived sheet with
                    # rename_map applied to Position_A/Position_B cells and
                    # split_element_map applied to Element_A/Element_B cells; they
                    # are not regenerated from the planar structure.
                    criterion_col = _pair_construction_criterion(class_name, construction)
                    rows_copied, cells_renamed, rows_split, rows_manual = _copy_pair_tab_with_rename(
                        ss, new_ss, construction, rename_map, param_names, param_values,
                        split_element_map=split_element_map, criterion_col=criterion_col,
                    )
                    tab_names.append(construction)
                    new_construction_params[construction] = {
                        "param_names": param_names,
                        "param_values": param_values,
                    }
                    msg = f"    [{construction}] (pair tab) copied {rows_copied} rows, {cells_renamed} cell(s) renamed"
                    if rows_split:
                        msg += f", {rows_split} row(s) split (blank, old judgment quoted in Comments)"
                    if rows_manual:
                        msg += f", {rows_manual} self-pair row(s) on a split element — NEEDS MANUAL REVIEW, not auto-handled"
                    print(msg)
                    continue
                rows = _build_rows(element_index, lang_id, param_names)
                existing = all_annotations.get(construction, {})
                tsv_path = CODED_DATA / lang_id / class_name / f"{construction}.tsv"
                carried, new_count, dropped_count = _write_tab_with_carryover(
                    new_ss, construction, param_names, param_values, rows, existing,
                    rename_map, element_rename_map, tsv_path=tsv_path,
                    split_element_map=split_element_map,
                )
                written_tsvs.append(tsv_path)
                tab_names.append(construction)
                new_construction_params[construction] = {
                    "param_names": param_names,
                    "param_values": param_values,
                }
                print(f"    [{construction}] wrote: carried {carried}, new blank {new_count}, dropped {dropped_count}")

            if default_ws.title not in tab_names:
                new_ss.del_worksheet(default_ws)

            planar_path = planar_file.parent / f"planar_{lang_id}.tsv"
            created_ref = _maybe_create_planar_reference_tab(new_ss, class_name, planar_path, lang_id)
            if created_ref:
                print(f"    Tab: Planar Structure (planar reference)")
            _create_status_tab(new_ss, tab_names)
            _reorder_system_tabs(new_ss)

            restructured_classes.add((lang_id, class_name))

            # Step 5: Update manifest
            manifest[lang_id]["sheets"][class_name] = {
                "spreadsheet_id": new_ss.id,
                "url": new_ss.url,
                "constructions": tab_names,
                "construction_params": new_construction_params,
                "version": new_version,
            }
            # Write local manifest copy immediately so it survives if a later API
            # error prevents the final upload block from running.
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"    New sheet (v{new_version}): {new_ss.url}")
            sheet_links.append((lang_id, class_name, new_ss.url))

    # Cascade rename to pair tabs that were NOT covered by the archive+recreate path
    # (i.e., the class sheet was unchanged except for position name cells in pair tabs).
    # For classes that WERE archived+recreated, _copy_pair_tab_with_rename already
    # handled the Drive sheet; we still update local TSVs for those classes here.
    if rename_map and pair_row_constructions:
        for planar_file in planar_files:
            lang_id = _infer_language_id_from_planar_filename(planar_file.name)
            lang_data = manifest.get(lang_id, {})
            for class_name, pair_cons in pair_row_constructions.items():
                sheet_info = lang_data.get("sheets", {}).get(class_name)
                for construction in sorted(pair_cons):
                    tsv_path = CODED_DATA / lang_id / class_name / f"{construction}.tsv"
                    if apply:
                        tsv_changed = _cascade_rename_pair_tsv(tsv_path, rename_map)
                        if tsv_changed:
                            written_tsvs.append(tsv_path)
                            print(
                                f"\n  [{lang_id} {class_name}/{construction}]"
                                f" local TSV: updated {tsv_changed} position cell(s)"
                            )
                    if apply and (lang_id, class_name) not in restructured_classes:
                        if not sheet_info:
                            continue
                        ss_pair = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])
                        try:
                            ws = _with_retry(lambda: ss_pair.worksheet(construction))
                            sheet_changed = _cascade_rename_pair_tab(ws, rename_map)
                            if sheet_changed:
                                print(
                                    f"  [{lang_id} {class_name}/{construction}]"
                                    f" Drive tab: updated {sheet_changed} position cell(s)"
                                )
                        except WorksheetNotFound:
                            pass

    if apply:
        # Update local manifest and upload to Drive.
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        config = _load_drive_config()
        for lid, ld in manifest.items():
            if "folder_id" not in ld:
                folder_url = ld.get("folder_url", "")
                if folder_url:
                    ld["folder_id"] = folder_url.rstrip("/").rsplit("/", 1)[-1]
            config.setdefault(lid, {})["folder_id"] = ld.get("folder_id", "")
            config[lid].pop("manifest_file_id", None)
        existing_file_id = config.get("_planars_config_file_id")
        root_folder_id = config.get("_root_folder_id")
        file_id = upload_manifest(doorway, manifest, root_folder_id, existing_file_id)
        config["_planars_config_file_id"] = file_id
        _save_drive_config(config)
        print("\nManifest updated on Drive.")

    if not apply:
        print("\nRun with --apply to make these changes.")
    else:
        print("\nDone.")
        from .generate_notebooks import regenerate_notebooks
        regenerate_notebooks()
        processed_lang_ids = [
            _infer_language_id_from_planar_filename(f.name) for f in planar_files
        ]
        print("\n--- Revalidating sheets ---")
        from .validate_coding import revalidate_sheets
        revalidate_sheets(lang_ids=processed_lang_ids)
        langs = ", ".join(sorted(set(processed_lang_ids)))
        _autocommit_data(
            written_tsvs,
            f"data: restructure {langs} TSVs after planar changes {date.today().isoformat()}",
        )

        # restructure-sheets reads planar_{lang_id}.tsv as its source of truth but
        # never writes it — so if it was edited locally (directly, or by a future
        # tool) before this run, the master planar Sheet is now stale and the next
        # scheduled import-planar --apply would silently revert it (issue #248,
        # exactly what happened to the #236 pronoun split). Push it back in sync
        # here so that can't happen again.
        print("\n--- Syncing planar Sheet ---")
        from .import_planar import push_planars_to_sheets
        push_planars_to_sheets(lang_ids=sorted(set(processed_lang_ids)), apply=True)

        if lang_folder_urls:
            print("\n--- Bookmark this instead ---")
            print("  Every sheet below just got a NEW URL (restructure-sheets always creates a")
            print("  fresh spreadsheet and archives the old one) — any previously bookmarked")
            print("  sheet links are now stale. The Drive folder link does NOT change across")
            print("  restructures, so it's the one worth bookmarking long-term:")
            for lang_id, folder_url in lang_folder_urls.items():
                print(f"  [{lang_id}] {folder_url}")

        if sheet_links:
            print("\n--- Affected sheets (new URLs — old bookmarks to these classes are stale) ---")
            for lang_id, class_name, url in sheet_links:
                print(f"  [{lang_id}] {class_name}: {url}")

        # Notify each affected language's tracking issue. The printing above does
        # NOT reach Adam -- he works through his own separate Claude Code instance
        # and never watches this terminal. A GitHub issue comment does, because he
        # can subscribe to just the languages he annotates. Same content as the
        # "Affected sheets" / "Bookmark this instead" blocks above, new sink.
        # See coding/notify.py for the one-issue-per-language design rationale.
        if sheet_links:
            print("\n--- Notifying language tracking issues ---")
            manifest_dirty = False
            for notify_lang_id in changed_lang_ids(sheet_links):
                lang_sheet_links = [
                    (class_name, url)
                    for lid, class_name, url in sheet_links
                    if lid == notify_lang_id
                ]
                folder_url = lang_folder_urls.get(notify_lang_id)
                status_sheet_url = manifest.get(notify_lang_id, {}).get("status_sheet_url")
                issue_number, created = ensure_notification_issue(notify_lang_id, manifest)
                manifest_dirty = manifest_dirty or created
                body = build_change_comment(notify_lang_id, lang_sheet_links, folder_url, status_sheet_url)
                post_notification_comment(issue_number, body)
                print(f"  [{notify_lang_id}] commented on issue #{issue_number}")
            if manifest_dirty:
                # A new notification issue was created for at least one language --
                # persist the updated manifest the same way the rest of this
                # command already does (MANIFEST_PATH.write_text + upload_manifest).
                MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                config = _load_drive_config()
                existing_file_id = config.get("_planars_config_file_id")
                root_folder_id = config.get("_root_folder_id")
                file_id = upload_manifest(doorway, manifest, root_folder_id, existing_file_id)
                config["_planars_config_file_id"] = file_id
                _save_drive_config(config)
                print("  Manifest updated on Drive (new notification_issue number(s)).")


if __name__ == "__main__":
    main()
