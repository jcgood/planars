#!/usr/bin/env python3
"""Restructure existing Google Sheets when the planar structure has changed significantly.

Use this when position numbers have changed or rows have been reordered — situations
where update_sheets.py (which only appends) is insufficient.

Run from the repo root:
    python -m coding restructure-sheets           # dry run — show what would change
    python -m coding restructure-sheets --apply   # archive old sheets and regenerate
    python -m coding restructure-sheets --lang LANG_ID   # restrict to one language

    # Map renamed positions so their annotations are carried over instead of dropped:
    python -m coding restructure-sheets --rename-map v:npsubj1:v:subj1
    python -m coding restructure-sheets --rename-map v:old1:v:new1 --rename-map v:old2:v:new2 --apply

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

    --rename-map takes "old_pos_name:new_pos_name" and can be repeated. Position names
      contain a colon themselves, so v:npsubj1:v:subj1 means v:npsubj1 -> v:subj1.
    --rename-element takes "old_element:new_element" and can be repeated.
    --split-element takes "old_element:new1,new2,..." (comma-separated, at least 2 targets)
      and can be repeated. There's no principled 1:1 value to carry over from one generic
      old element to several specific new ones, so new rows are left blank as usual — but
      if the old element had existing annotations, each new row's first answer cell gets
      a note quoting them so re-annotators aren't working from memory (a note, never
      Comments, which is the annotator's own column). An element cannot appear in both --rename-element and --split-element.
      Also cascades into every pair-row construction (nonpermutability's `general`,
      coreference's three, and any future one — found generically via row_type:
      pair_rows, not hardcoded by class name) that references the retired element in
      Element_A/Element_B: each old pair-row fans out into one new row per replacement
      element, left BLANK (never pre-filled with the old value, even though it's often
      linguistically the same fact — a coordinator happening to know the language
      doesn't scale to contributor languages nobody on the team speaks), with the old
      row's criterion value, Example, Source and Comments quoted in a note on the new
      row's criterion cell. A row where BOTH sides of a pair are the retired element (a
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

    # If a previous --apply run was interrupted mid-class (crash, network failure),
    # the next run of any kind refuses to start new work and reports which class(es)
    # are stuck and how, until one of these resolves them:
    python -m coding restructure-sheets --resume --apply    # finish or safely undo, then continue
    python -m coding restructure-sheets --rollback --apply  # undo what's safely undoable, then stop

What this does per spreadsheet:
  1. Downloads current annotations from each tab
  2. [--apply] Moves the spreadsheet to _archived/ in Drive (renamed to include _v{N})
  3. [--apply] Creates a new spreadsheet from the updated planar structure
  4. Carries over annotations matched by (Element, Position_Name)
  5. Leaves unmatched rows blank for re-annotation
  6. Updates sheets_manifest.json to point to the new spreadsheets

Each tab's local annotation TSV is rewritten to match, through the local-file
door (coding/file_door.py): the previous version goes to
coded_data/{lang}/archive/{class}/, the change to the language's changes.tsv,
and the files are committed and pushed in planars-data when the command ends.

Recoverability (Phase 7 of the data layer redesign, issue #271): each class's
progress through steps 2-6 is journaled to restructure_journal.json (in
planars-data, `state_files.JOURNAL_PATH`) before each Drive-mutating step, so
a crash partway through is detected by the next run, on any machine (the
command refuses a copy of planars-data older than GitHub's), rather than silently re-attempted or left unexplained. Undoing is only
offered where it's actually safe -- step 2 alone, before step 3 has created
anything -- since a step-3 replacement sheet already holds real carried-over
annotation data that undoing would destroy; past that point recovery always
finishes forward (--resume), never deletes. This covers --rename-class's own
archive/create sequence too (unit 2, same day as the main loop's unit 1) --
both refuse to start new work while the other's interrupted class is still
stuck, since they share one journal. See restructure_journal.py's module
docstring for the full reasoning and #248 for the incident this closes.

For --rename-class, step 3 creates a spreadsheet under the new class name, and
the class's local TSVs move from coded_data/{lang}/{old}/ to
coded_data/{lang}/{new}/ (file_door.move_class: each written under the new
name and removed from the old, whose last versions stay in archive/{old}/).

After `--apply`, for each language whose sheets actually changed:
  - the planar Sheet is brought up to date with `planar_{lang_id}.tsv`
    (`sync_planar.sync_planars`), which first renumbers any position numbers
    typed in the answers. This command only reads that file, never writes it:
    the coordinator or Claude edits it first for a structural change, and the
    flags above only supply the old -> new mapping used to carry annotations
    forward.
  - a comment goes to the language's `sheet-updates` issue (`notify.py`),
    because terminal output reaches no annotator.

Archived sheets: `_lock_archived_sheet` sets the annotator's grant to reader
(`drive.set_user_role`) and removes any link share; `_rollback_unit` undoes only
that one grant. To retire a class rather than rename it, use `prune-manifest`.
The Drive door retries every call and checks the writes.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
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
from .schemas import apply_schema_criteria, free_entry_kind, load_diagnostic_classes
from planars.schema_values import (
    ELEMENT_ROW_COLUMNS,
    PAIR_ROW_SHAPES,
    TRAILING_COLUMNS as _TRAILING_COLS, trailing_columns_for,
    row_columns, row_columns_of, row_key_of, row_type_of,
)
from .drive import (
    _load_drive_config, _save_drive_config,
    load_manifest, remove_anyone_permission, set_user_role, upload_manifest,
)
from .drive_doorway import SpreadsheetHandle, WorksheetHandle, WorksheetNotFound, get_doorway
from .generate_sheets import (
    _annotator_email,
    _build_criterion_notes,
    _create_status_tab,
    _format_and_validate,
    _populate_tab_keyed,
    _refresh_locked_tabs,
    starting_rows,
)
from .locked_tabs import reorder_tabs
from . import biuniqueness_rows as _br
from .notify import (
    build_change_comment,
    changed_lang_ids,
    ensure_notification_issue,
    post_notification_comment,
)
from . import restructure_journal
from . import drive_door, file_door
from .sheet_spec import ARCHIVE_FOLDER_NAME

MANIFEST_PATH = ROOT / "sheets_manifest.json"
CODED_DATA = ROOT / "coded_data"
_STRUCTURAL_COLS = set(ELEMENT_ROW_COLUMNS)


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

    Archived sheets carry real prior judgments (the full record behind
    --split-element's notes) so the annotator still needs to be able to open
    and read them — just not edit them, since they're no longer the live copy.

    Uses `drive.remove_anyone_permission`, the one copy of that sequence
    (it was inlined here and in two other files until 2026-10-12). Retry on a
    rate-limit blip happens in the Drive door (`coding/drive_door.py`).

    The annotator's grant is *set* to reader (`drive.set_user_role`), not
    added: until 2026-10-13 this created a reader grant beside the writer one
    every class sheet gives its annotator, and Google kept the writer, so no
    archived sheet was ever actually read-only.

    The sheet is labelled archived first (`doorway.mark_archived`), because
    the Drive door expects an archived class sheet's annotator to be a reader
    and a live one's a writer.
    """
    doorway.mark_archived(file_id)
    remove_anyone_permission(doorway, file_id)
    email = _annotator_email(lang_id)
    if email:
        set_user_role(doorway, file_id, email, "reader")


# ---------------------------------------------------------------------------
# Interrupted-run recovery (Phase 7 of the data layer redesign, issue #271)
# ---------------------------------------------------------------------------

def _rollback_unit(doorway, manifest, entry: dict) -> None:
    """Undo an OLD_SHEET_ARCHIVED-only unit: move the archived sheet back to
    its language folder, rename it back to its live title, and restore the
    annotator's write access -- the exact inverse of `_lock_archived_sheet`.

    Only called for entries `restructure_journal.is_rollback_safe()` confirms
    are still pre-recreate (see that module's docstring for why nothing later
    is undone this way). Does not touch the manifest -- it was never updated
    for this unit, so it already still points at the sheet being restored
    here.

    Changes only the ONE permission `_lock_archived_sheet` itself changed
    (the annotator's grant, matched by email, set back to writer by
    `drive.set_user_role`) rather than every 'user'-type permission on the
    sheet. An earlier version swept all
    'user'-type grants, which silently dropped a co-annotator's pre-existing
    access if the sheet had one before archiving even started -- found by
    Phase 8's fault-injection tests (issue #271), which is exactly the class
    of assumption this module's docstring had flagged as unverified. Needs
    `emailAddress` in the requested fields to match by email at all -- the
    real Drive API honors that field mask and omits the address otherwise,
    unlike the fake, which returns every field regardless of what's asked.

    Retry on a rate-limit blip happens in the Drive door
    (`coding/drive_door.py`).
    """
    lang_id = entry["lang_id"]
    class_name = entry["class_name"]
    detail = entry["detail"]
    archived_id = detail["archived_spreadsheet_id"]
    folder_id = detail.get("folder_id")
    if folder_id:
        doorway.move_file(archived_id, folder_id)
    doorway.update_file(archived_id, name=f"{class_name}_{lang_id}")
    # Live again before the annotator goes back to writer (see _lock_archived_sheet).
    doorway.mark_archived(archived_id, archived=False)
    email = _annotator_email(lang_id)
    if email:
        set_user_role(doorway, archived_id, email, "writer")
    print(f"    [{lang_id}] {class_name}: rolled back — sheet restored, un-archived.")


def _finish_new_sheet_created_unit(manifest, entry: dict) -> Tuple[str, str, str]:
    """Finish a NEW_SHEET_CREATED unit: the replacement sheet itself is
    already done, only the manifest bookkeeping (pointing at it) never
    happened. Pure local bookkeeping, no further Drive-sheet mutation --
    always safe to finish forward. The actual Drive upload of this manifest
    change, and clearing the unit from the journal, happen where they
    already do for a normal run's classes -- once, in the end-of-run upload
    block -- so a crash between this write and that upload leaves the
    journal entry in place and correctly re-detected, rather than marked
    done early.

    Handles both shapes this checkpoint can mean: an ordinary restructure
    (`class_name` unchanged) and a `--rename-class` unit (`detail`'s
    `new_class_name` differs from the journal key `class_name`, which is
    the OLD class name -- see `_rename_class_for_language`). For a rename,
    also finishes the local TSV directory rename if it didn't already
    happen (deliberately deferred here rather than done before this
    checkpoint, same reasoning as the manifest write: neither is unsafe to
    redo/skip if already done, unlike archiving or creating a sheet) and
    drops the old class's now-stale manifest entry.

    Returns (lang_id, DISPLAY class name, url) for the caller's
    sheet_links/notify list -- the new name for a rename, same as the
    journal key otherwise. Callers that need to clear this unit from the
    journal must use `entry["lang_id"]`/`entry["class_name"]` (the journal
    key) instead, not this return value -- clearing by the display name
    would silently no-op for a renamed unit and leave it stuck forever.
    """
    lang_id = entry["lang_id"]
    class_name = entry["class_name"]  # journal key; OLD class name for a rename
    detail = entry["detail"]
    new_class_name = detail.get("new_class_name") or class_name
    if new_class_name != class_name:
        old_dir = file_door.class_folder(lang_id, class_name)
        new_dir = file_door.class_folder(lang_id, new_class_name)
        if old_dir.exists() and not new_dir.exists():
            file_door.move_class(lang_id, class_name, new_class_name,
                                 why=f"class renamed {class_name} -> {new_class_name} "
                                     f"(restructure-sheets --resume)")
            print(f"    [{lang_id}] {class_name} -> {new_class_name}: "
                  f"moved local TSVs.")
        manifest.get(lang_id, {}).get("sheets", {}).pop(class_name, None)
    manifest.setdefault(lang_id, {}).setdefault("sheets", {})[new_class_name] = {
        "spreadsheet_id": detail["spreadsheet_id"],
        "url": detail["url"],
        "constructions": detail["constructions"],
        "construction_params": detail["construction_params"],
        "version": detail["version"],
    }
    print(f"    [{lang_id}] {new_class_name}: resumed — manifest now points at the "
          f"already-created sheet ({detail['url']}).")
    return lang_id, new_class_name, detail["url"]


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
    tsv_target: Optional[file_door.LocalFile] = None,
    split_element_map: Dict[str, List[str]] = {},
    *,
    trailing: List[str],
) -> Tuple[int, int, int]:
    """Create/clear a tab and populate it, carrying over matching annotations.
    ``trailing`` is the language's trailing columns (trailing_columns_for).

    ``tsv_target``: the tab's annotation TSV, rewritten to match through the
    local-file door (which keeps the previous version).

    Matching is by (Element, Position_Name), with optional rename_map (old→new
    position renames) and element_rename_map (old→new element label renames).

    split_element_map ({old_element: [new1, new2, ...]}) marks elements being split
    into several finer-grained replacements. There's no principled value to carry
    over 1:1 for these (a generic annotation doesn't tell us how each new element
    individually behaves), so they're left as new blank rows — but if the old
    element had existing annotations, the new row's first answer cell gets a note
    quoting them (``_split_note``), so the annotator decides with the old judgment
    in view. Comments is never written: it is the annotator's.

    Returns:
        (carried_count, new_count, dropped_count)
    """
    old_for_new    = {v: k for k, v in rename_map.items()}
    old_el_for_new = {v: k for k, v in element_rename_map.items()}
    new_to_old_split: Dict[str, str] = {
        n: old for old, news in split_element_map.items() for n in news
    }
    all_cols = param_names + trailing
    header = ELEMENT_ROW_COLUMNS + all_cols

    carried = 0
    new = 0
    reachable_old_keys: set = set()
    all_rows = [header]
    notes: List[Tuple[int, int, str]] = []

    for row in rows:
        element = str(row[0])
        pos_name = str(row[1])
        pos_num = str(row[2])

        old_values = _lookup_existing(element, pos_name, existing, old_for_new, old_el_for_new)
        if old_values is not None:
            param_vals = [old_values.get(p, "") for p in param_names]
            trailing_vals = [old_values.get(c, "") for c in trailing]
            reachable_old_keys.add(_old_key(element, pos_name, existing, old_for_new, old_el_for_new))
            carried += 1
        else:
            # Nothing to carry over: the values the row starts with
            # (generate_sheets.starting_rows: keystone na, pre-fills).
            param_vals = [str(v) for v in row[len(ELEMENT_ROW_COLUMNS):][:len(param_names)]]
            param_vals += [""] * (len(param_names) - len(param_vals))
            trailing_vals = [""] * len(trailing)
            split_source = new_to_old_split.get(element)
            old_split = existing.get((split_source, pos_name)) if split_source else None
            if old_split is not None and param_names:
                notes.append((len(all_rows) - 1, len(ELEMENT_ROW_COLUMNS),
                              _split_note(split_source, old_split)))
            new += 1

        all_rows.append([element, pos_name, pos_num] + param_vals + trailing_vals)

    # Count existing annotations that were not matched by any row in the new structure.
    # These correspond to positions/elements that were removed from the planar file.
    dropped = sum(1 for k in existing if k not in reachable_old_keys)

    if tsv_target is not None:
        header = all_rows[0]
        file_door.write(
            tsv_target, file_door.frame_text(pd.DataFrame(all_rows[1:], columns=header)),
            why="rebuilt for the new planar structure by restructure-sheets",
            drops=(f"restructure-sheets carried {carried} row(s) over by element and "
                   f"position name and dropped {dropped} for positions or elements "
                   f"no longer in the planar"))

    try:
        ws = spreadsheet.worksheet(tab_name)
        ws.clear()
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(rows) + 2, cols=len(all_cols) + 3
        )

    ws.update(all_rows, "A1")
    per_col_values = [param_values[p] for p in param_names]  # values come from criteria_for
    per_col_notes = _build_criterion_notes(param_names)
    _format_and_validate(ws, len(rows), per_col_values, param_notes=per_col_notes)
    _add_cell_notes(ws, notes)

    return carried, new, dropped


def _split_note(old_element: str, old_values: Dict[str, str]) -> str:
    """The note on a split row's first answer cell: what the element it was
    split from had here. The annotator decides with it in view; Comments stays
    theirs (the tooling never writes there, schemas/planar.yaml)."""
    answered = "; ".join(f"{c}: {v}" for c, v in old_values.items() if str(v).strip())
    return (f"Split from {old_element}, which had " + (answered or "no answers")
            + ". Decide this row afresh.")


def _add_cell_notes(ws, notes: List[Tuple[int, int, str]]) -> None:
    """Attach each (data row index, column index, text) as a note on that
    cell (row 0 is the first row under the header)."""
    if not notes:
        return
    requests = [{"repeatCell": {
        "range": {"sheetId": ws.id, "startRowIndex": r + 1, "endRowIndex": r + 2,
                  "startColumnIndex": c, "endColumnIndex": c + 1},
        "cell": {"note": text}, "fields": "note"}} for r, c, text in notes]
    ws.spreadsheet.batch_update({"requests": requests})


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
        rows: new rows from _element_rows_for (the regenerated planar structure).
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

# The Position_A/Position_B columns of the position_pairs row shape (planar.yaml).
_PAIR_POS_COLS = tuple(c for c in PAIR_ROW_SHAPES["position_pairs"]
                       if c.startswith("Position_"))


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


def _get_keyed_row_constructions() -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    """Return {class_name: {construction: {"columns": [...], "key": [...]}}} for
    every keyed_rows construction in diagnostic_classes.yaml.

    Checks every construction's row shape on the way (planars.schema_values'
    row_type_of/row_columns_of/row_key_of, the one copy of those rules): every
    caller that branches on row shape (generate_sheets, validate_coding,
    import_sheets, update_sheets, restructure_sheets, generate_status_sheet,
    integrity_check) goes through this or _get_pair_row_constructions, so a
    typo'd row_type, a pair construction without its pair_shape, or a
    keyed_rows construction missing its columns stops here rather than being
    read as element rows by default.
    """
    from .schemas import load_diagnostic_classes
    result: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    for cls in load_diagnostic_classes().get("classes", []):
        for con in (cls.get("constructions") or []):
            if not isinstance(con, dict):
                continue
            where = f"{cls['name']}/{con.get('name')}"
            columns, key = row_columns_of(con, where), row_key_of(con, where)
            if row_type_of(con, where) != "keyed_rows":
                continue
            result.setdefault(cls["name"], {})[con["name"]] = {
                "columns": columns, "key": key,
                "blank_ok_when": [dict(r) for r in (con.get("blank_ok_when") or [])]}
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
# it and its counterpart structurally, not by element identity). The shapes
# are declared in planar.yaml's pair_row_shapes; this code reads the columns
# it needs by name from each header.


def _apply_split_to_pair_rows(
    header: List[str],
    data_rows: List[List[str]],
    split_element_map: Dict[str, List[str]],
    criterion_col: Optional[str],
) -> Tuple[List[List[str]], int, int, List[Tuple[int, int, str]]]:
    """Fan out pair-row(s) referencing a retired (split) element into one row per
    replacement element, per issue #241's resolved design (policy (b)).

    For each data row where Element_A or Element_B (whichever are present in header)
    equals an element being split, generates one new row per replacement element
    with that column substituted, the criterion column BLANKED (never carried
    forward as a live default -- a coordinator happening to know the language
    doesn't scale to contributor languages nobody on the team speaks, see #262).
    The old row's criterion value and every filled trailing column (Example,
    Source, Comments) are quoted in a note on the new row's criterion cell
    (``_split_note``), and the new row's trailing columns start blank, so the
    prior judgment is visible right where the new decision is made. Until
    2026-10-22 the quote went into Comments, the annotator's own column, where
    nothing could tell it from what they wrote (#318).

    A row where BOTH Element_A and Element_B match an element being split (a
    self-pair) is left untouched but counted separately -- fanning out both sides
    at once has no principled combination to prefer over any other, so it's
    reported for manual review rather than guessed at.

    No-ops (returns data_rows unchanged) if split_element_map is empty or the
    header has no Element_A column at all (not an element-identified pair shape).

    Returns (new_data_rows, n_fanned_out, n_needs_manual_review, notes), notes
    as ``_add_cell_notes`` takes them (indexes into new_data_rows).
    """
    if not split_element_map or "Element_A" not in header:
        return data_rows, 0, 0, []

    col_idx = {c: i for i, c in enumerate(header)}
    a_idx = col_idx["Element_A"]
    b_idx = col_idx.get("Element_B")
    trailing_idx = {c: col_idx[c] for c in _TRAILING_COLS if c in col_idx}
    crit_idx = col_idx.get(criterion_col) if criterion_col else None
    note_idx = crit_idx if crit_idx is not None else a_idx

    new_rows: List[List[str]] = []
    notes: List[Tuple[int, int, str]] = []
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
        old_values = {c: padded[i] for c, i in trailing_idx.items()}
        if crit_idx is not None:
            old_values = {criterion_col: padded[crit_idx], **old_values}
        note = _split_note(old_el, old_values)

        for new_el in split_element_map[old_el]:
            new_row = list(padded)
            if a_hit:
                new_row[a_idx] = new_el
            else:
                new_row[b_idx] = new_el
            if crit_idx is not None:
                new_row[crit_idx] = ""
            for i in trailing_idx.values():
                new_row[i] = ""
            notes.append((len(new_rows), note_idx, note))
            new_rows.append(new_row)
            n_fanned += 1

    return new_rows, n_fanned, n_manual, notes


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
    _, fanned, manual, _ = _apply_split_to_pair_rows(
        list(df.columns), df.values.tolist(), split_element_map, criterion_col
    )
    return fanned, manual


def _cascade_rename_pair_tsv(target: file_door.LocalFile, rename_map: Dict[str, str]) -> int:
    """Update position name components in Position_A/Position_B cells of a local TSV,
    through the local-file door.

    Parses each combined 'N (name)' cell and replaces the name component when it
    appears in rename_map.  Returns the count of cell values changed.
    """
    if not target.path.exists():
        return 0
    df = pd.read_csv(target.path, sep="\t", dtype=str, keep_default_na=False)
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
        # A row keyed by its position cell ("N (name)") gets a new key when
        # the name changes, though it is the same row with the same answers.
        renamed = ", ".join(f"{o} -> {n}" for o, n in rename_map.items())
        file_door.write(target, file_door.frame_text(df),
                        why=f"position renamed ({renamed})",
                        drops=f"rows keep their answers under the renamed position ({renamed})")
    return changed


def _cascade_rename_pair_tab(
    ws: WorksheetHandle, rename_map: Dict[str, str]
) -> int:
    """Update position name components in Position_A/Position_B cells of a Drive tab.

    Updates cells in-place via batch_update.  Returns the count of cell values changed.
    """
    all_values = ws.get_all_values()
    if not all_values:
        return 0
    header = all_values[0]
    col_indices = {col: header.index(col) for col in _PAIR_POS_COLS if col in header}
    if not col_indices:
        return 0

    updates: List[Dict] = []
    # Each range names the tab: the values API sends a bare "D5" to the
    # spreadsheet's first tab, not to this one (it did until 2026-10-15).
    tab = "'" + ws.title.replace("'", "''") + "'"
    for row_idx, row in enumerate(all_values[1:], start=2):
        for col_name, col_idx in col_indices.items():
            cell_val = row[col_idx] if col_idx < len(row) else ""
            new_val, changed = _apply_rename_to_position_cell(cell_val, rename_map)
            if changed:
                col_letter = gspread.utils.rowcol_to_a1(1, col_idx + 1)[:-1]
                updates.append({"range": f"{tab}!{col_letter}{row_idx}", "values": [[new_val]]})

    if updates:
        ws.spreadsheet.values_batch_update({
            "valueInputOption": "RAW",
            "data": updates,
        })
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
    *,
    class_name: str,
    trailing: List[str],
) -> Tuple[int, int, int, int]:
    """Copy a pair tab from old_ss to new_ss with rename_map applied to position cells
    and split_element_map applied to Element_A/Element_B cells (see
    _apply_split_to_pair_rows, issue #241).

    Used when a class sheet is being archived+recreated and the class has pair
    constructions that should be preserved (not regenerated from the planar structure).
    An old tab that is missing or empty gives a new tab with just its header
    (the schema's row columns, the criteria, the trailing columns), ready for
    --regen-construction to fill.
    Returns (rows_copied, cells_renamed, rows_split, rows_needing_manual_review).
    """
    try:
        old_ws = old_ss.worksheet(tab_name)
        all_values = old_ws.get_all_values()
    except WorksheetNotFound:
        all_values = []

    if not all_values:
        header = row_columns(class_name, tab_name) + list(param_names) + list(trailing)
        ws = new_ss.add_worksheet(title=tab_name, rows=10, cols=len(header))
        ws.update([header], "A1")
        return 0, 0, 0, 0

    # The trailing columns are the language's (``trailing``), in the schema's
    # order, whatever the old tab had: a column added to schemas/planar.yaml
    # since the old sheet was made (Example, 2026-10-22) must be on the
    # rebuilt one, and a trailing column the language doesn't carry must not
    # be. Cells move by column name.
    old_header = all_values[0]
    header = [c for c in old_header if c not in _TRAILING_COLS] + list(trailing)
    old_idx = {c: i for i, c in enumerate(old_header)}
    rows_by_name = [[(row[old_idx[c]] if c in old_idx and old_idx[c] < len(row) else "")
                     for c in header] for row in all_values[1:]]
    col_indices = {col: header.index(col) for col in _PAIR_POS_COLS if col in header}
    renamed = 0
    new_data = [header]
    for row in rows_by_name:
        new_row = list(row)
        for col_name, col_idx in col_indices.items():
            if col_idx < len(new_row):
                new_val, changed = _apply_rename_to_position_cell(new_row[col_idx], rename_map)
                if changed:
                    new_row[col_idx] = new_val
                    renamed += 1
        new_data.append(new_row)

    new_data[1:], split_fanned, split_manual, split_notes = _apply_split_to_pair_rows(
        header, new_data[1:], split_element_map, criterion_col
    )

    try:
        ws = new_ss.worksheet(tab_name)
        ws.clear()
    except WorksheetNotFound:
        ws = new_ss.add_worksheet(
            title=tab_name, rows=len(new_data) + 2, cols=len(header) + 2
        )

    ws.update(new_data, "A1")
    per_col = [param_values[p] for p in param_names]  # values come from criteria_for
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
        col_start = len(header) - len(trailing) - len(param_names)
    _format_and_validate(ws, len(new_data) - 1, per_col, col_start=col_start)
    _add_cell_notes(ws, split_notes)
    return len(new_data) - 1, renamed, split_fanned, split_manual


# ---------------------------------------------------------------------------
# Keyed-row tabs (biuniqueness_deviations' morphemes/morphs, #254)
# ---------------------------------------------------------------------------
# Keyed tabs name positions and elements, never position numbers, so a plain
# renumbering leaves them alone. They are copied from the archived sheet,
# like pair tabs, with renames applied to every cell that names a position
# (Position_Name, Found_At, any <position_names> criterion such as
# conditioned_by) or an element (Morpheme, Form). A co-exponent label
# ("be + v:verbinflection") names both. A split element cannot be resolved
# automatically: its rows are kept unchanged, flagged with a cell note, and counted
# for manual review.

_POSITION_LIST_COLS = ("Found_At",)


def _rename_list_cell(cell: str, rename_map: Dict[str, str]) -> str:
    parts = [p.strip() for p in str(cell).split(",") if p.strip()]
    return ", ".join(rename_map.get(p, p) for p in parts)


def _rename_co_label(label: str, rename_map: Dict[str, str],
                     element_rename_map: Dict[str, str]) -> str:
    """'be + v:verbinflection' with element and position renames applied."""
    if " + " not in label:
        return element_rename_map.get(label, label)
    element, positions = label.split(" + ", 1)
    return (f"{element_rename_map.get(element, element)} + "
            f"{_rename_list_cell(positions, rename_map)}")


def _transform_keyed_rows(
    header: List[str],
    data_rows: List[List[str]],
    position_param_cols: Set[str],
    rename_map: Dict[str, str],
    element_rename_map: Dict[str, str],
    split_element_map: Dict[str, List[str]],
) -> Tuple[List[List[str]], int, int, List[Tuple[int, int, str]]]:
    """Apply renames to a keyed tab's rows. Returns (rows, cells_changed,
    rows_flagged, notes): a row naming a split element is kept as it is and
    flagged with a note on its first cell (``_add_cell_notes``), never in
    Comments, which is the annotator's."""
    idx = {c: i for i, c in enumerate(header)}
    changed = flagged = 0
    out = []
    notes: List[Tuple[int, int, str]] = []
    for raw in data_rows:
        row = list(raw) + [""] * (len(header) - len(raw))
        before = list(row)
        if "Morpheme" in idx:
            row[idx["Morpheme"]] = _rename_co_label(row[idx["Morpheme"]], rename_map,
                                                    element_rename_map)
        if "Form" in idx:
            row[idx["Form"]] = element_rename_map.get(row[idx["Form"]], row[idx["Form"]])
        if "Position_Name" in idx:
            row[idx["Position_Name"]] = rename_map.get(row[idx["Position_Name"]],
                                                       row[idx["Position_Name"]])
        for col in list(_POSITION_LIST_COLS) + sorted(position_param_cols):
            if col in idx and row[idx[col]]:
                row[idx[col]] = _rename_list_cell(row[idx[col]], rename_map)
        changed += sum(1 for a, b in zip(before, row) if a != b)

        touched = {row[idx["Morpheme"]]} if "Morpheme" in idx else set()
        touched |= {row[idx["Form"]]} if "Form" in idx else set()
        touched |= {row[idx["Morpheme"]].split(" + ", 1)[0]} if "Morpheme" in idx else set()
        split_hits = [old for old in split_element_map if old in touched]
        if split_hits:
            notes.append((len(out), 0, "; ".join(
                f"{old} was split into {', '.join(split_element_map[old])}: "
                f"check which this row is about" for old in split_hits)))
            flagged += 1
        out.append(row)
    return out, changed, flagged, notes


def _position_param_cols(param_values: Dict[str, List[str]]) -> Set[str]:
    return {p for p, vals in (param_values or {}).items()
            if free_entry_kind(vals) == "position_names"}


def _element_rows_for(class_name: str, construction: str, element_index, lang_id: str,
                      param_names: List[str], planar_file: Path) -> List[List[object]]:
    """The element rows a rebuilt tab should have, with the values the tooling
    fills in itself (generate_sheets.starting_rows). Every class takes every
    planar element, except biuniqueness_deviations' elements tab, which takes
    only those in biuniqueness scope (biuniqueness_rows.scoped_elements, #254)."""
    if class_name == _br.CLASS_NAME and construction == _br.ELEMENTS:
        planar_df = pd.read_csv(planar_file.parent / f"planar_{lang_id}.tsv", sep="\t",
                                dtype=str, keep_default_na=False)
        return _br.element_rows(planar_df, lang_id, param_names)
    return starting_rows(element_index, lang_id, class_name, construction, param_names,
                         data_dir=planar_file.parent)


def _rename_positions_in_annotations(
    existing: Dict, param_values: Dict[str, List[str]], rename_map: Dict[str, str],
) -> Dict:
    """Apply position renames inside <position_names> answers (co_exponents)
    before they are carried into a rebuilt element tab."""
    cols = _position_param_cols(param_values)
    if not cols or not rename_map:
        return existing
    return {k: {c: (_rename_list_cell(v, rename_map) if c in cols and v else v)
                for c, v in vals.items()}
            for k, vals in existing.items()}


def _count_keyed_impacts(
    tsv_path: Path, param_values: Dict[str, List[str]], rename_map: Dict[str, str],
    element_rename_map: Dict[str, str], split_element_map: Dict[str, List[str]],
) -> Tuple[int, int]:
    """(cells that would change, rows that would be flagged) in a local keyed TSV."""
    if not tsv_path.exists():
        return 0, 0
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    _, changed, flagged, _ = _transform_keyed_rows(
        list(df.columns), df.values.tolist(), _position_param_cols(param_values),
        rename_map, element_rename_map, split_element_map)
    return changed, flagged


def _copy_keyed_tab_with_rename(
    old_ss: SpreadsheetHandle,
    new_ss: SpreadsheetHandle,
    tab_name: str,
    keyed: Dict,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    rename_map: Dict[str, str],
    element_rename_map: Dict[str, str],
    split_element_map: Dict[str, List[str]],
    *,
    trailing: List[str],
) -> Tuple[int, int, int]:
    """Copy a keyed tab into the recreated sheet with renames applied; its
    trailing columns become the language's (``trailing``).
    Returns (rows_copied, cells_changed, rows_flagged)."""
    try:
        all_values = old_ss.worksheet(tab_name).get_all_values()
    except WorksheetNotFound:
        all_values = []
    header = all_values[0] if all_values else keyed["columns"] + param_names + list(trailing)
    rows, changed, flagged, notes = _transform_keyed_rows(
        header, all_values[1:], _position_param_cols(param_values),
        rename_map, element_rename_map, split_element_map)
    ws = _populate_tab_keyed(new_ss, tab_name, keyed["columns"], param_names, param_values,
                             [dict(zip(header, r)) for r in rows], trailing=trailing)
    _add_cell_notes(ws, notes)
    return len(rows), changed, flagged


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
    old_class in the manifest must also have new_class in its diagnostics file
    (and must NOT have old_class in it).  This enforces the required
    ordering: edit diagnostics_{lang_id}.yaml first (and run
    sync-diagnostics-yaml --apply), then rename.  The file is read the way
    every command reads it: the YAML, or the TSV only if there is no YAML.
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
            # Old class still in the diagnostics file — coordinator must remove it first.
            if old_class in active_classes:
                errors.append(
                    f"  {lang_id}: {old_class!r} is still in diagnostics_{lang_id}.yaml.\n"
                    f"    Replace it with {new_class!r} there, run "
                    f"`python -m coding sync-diagnostics-yaml --apply`, then re-run --rename-class."
                )
            # Old class in manifest but new class absent from the diagnostics file.
            if old_class in manifest_classes and new_class not in active_classes:
                errors.append(
                    f"  {lang_id}: {new_class!r} is not in diagnostics_{lang_id}.yaml.\n"
                    f"    Add it there, run "
                    f"`python -m coding sync-diagnostics-yaml --apply`, then re-run --rename-class."
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
    journal_units: Optional[Set[Tuple[str, str]]] = None,
) -> bool:
    """Rename one analysis class for one language.

    Downloads annotations from the old class sheet, archives it, creates a new
    sheet under new_class with all annotations carried over, renames the local
    TSV directory, and updates the manifest in-place.

    Journals its archive/create progress the same way the main per-class
    loop does (Phase 7 unit 2, issue #271) -- one entry keyed by
    (lang_id, old_class), with `new_class_name` in its detail so recovery
    code can tell a rename apart from an ordinary restructure. On a real
    apply, `journal_units` collects (lang_id, old_class) so the caller can
    clear it from the journal once the end-of-run Drive upload actually
    succeeds -- same "only clear after the real upload lands" discipline as
    `restructured_classes`, not right after this function's own local write.

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

    # This path rebuilds every tab as element rows. A pair-row or keyed-row tab
    # would be rebuilt in the wrong shape and lose its answers, so refuse
    # rather than guess (found 2026-10-11 adding keyed_rows, #254; the pair
    # case predates it).
    odd = sorted(set(constructions) & (
        _get_pair_row_constructions().get(old_class, set())
        | set(_get_keyed_row_constructions().get(old_class, {}))))
    if odd:
        print(f"    REFUSED: {old_class} has pair-row or keyed-row tabs ({', '.join(odd)}), "
              f"which --rename-class can only rebuild as element rows, losing their "
              f"answers. Rename this class by hand (new class sheet via generate-sheets, "
              f"then copy the tabs across) or extend --rename-class first.")
        return False

    # Download annotations from old sheet
    ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])
    all_annotations: Dict[str, Dict[Tuple[str, str], Dict[str, str]]] = {}
    for construction in constructions:
        try:
            ws = ss.worksheet(construction)
            all_annotations[construction] = _download_tab_annotations(ws)
            print(f"    [{construction}] downloaded {len(all_annotations[construction])} rows")
        except WorksheetNotFound:
            all_annotations[construction] = {}
            print(f"    [{construction}] tab not found")

    # Compute carry-over stats (dry-run or apply)
    for construction, (param_names, _) in new_specs.items():
        rows = starting_rows(element_index, lang_id, new_class, construction, param_names)
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

    # Archive old sheet. (Retry on a transient Google error happens in the
    # Drive door, coding/drive_door.py.)
    if folder_id:
        archive_id = doorway.get_or_create_folder(
            ARCHIVE_FOLDER_NAME, parent_id=folder_id,
            identity=drive_door.folder("archive", lang_id))
        doorway.update_file(ss.id, name=f"{old_class}_{lang_id}_v{version}")
        doorway.move_file(ss.id, archive_id)
        _lock_archived_sheet(doorway, ss.id, lang_id)
        restructure_journal.record_checkpoint(
            lang_id, old_class, restructure_journal.OLD_SHEET_ARCHIVED,
            archived_spreadsheet_id=ss.id, folder_id=folder_id, new_class_name=new_class,
        )
        print(f"    Archived {old_class}_{lang_id} → _archived/{old_class}_{lang_id}_v{version}")

    # Create new sheet
    sheet_title = f"{new_class}_{lang_id}"
    new_ss = doorway.create_spreadsheet(
        sheet_title, identity=drive_door.class_sheet(lang_id, new_class), replaces=ss.id)
    if folder_id:
        doorway.move_file(new_ss.id, folder_id)
        email = _annotator_email(lang_id)
        if email:
            doorway.create_permission(new_ss.id, type="user", role="writer", email=email)

    default_ws = new_ss.sheet1
    tab_names = []
    new_construction_params = {}

    for construction in constructions:
        if construction not in new_specs:
            print(f"    [{construction}] not in new diagnostics — skipped")
            continue
        param_names, param_values = new_specs[construction]
        rows = starting_rows(element_index, lang_id, new_class, construction, param_names)
        existing = all_annotations.get(construction, {})
        carried, new_count, dropped_count = _write_tab_with_carryover(
            new_ss, construction, param_names, param_values, rows, existing, {}, {},
            trailing=trailing_columns_for(lang_id),
        )
        tab_names.append(construction)
        new_construction_params[construction] = {"param_names": param_names}
        print(f"    [{construction}] wrote: carried {carried}, new blank {new_count}, dropped {dropped_count}")

    if default_ws.title not in tab_names:
        new_ss.del_worksheet(default_ws)

    _create_status_tab(new_ss, tab_names)   # the main restructure path's Status, as on every class sheet
    if planar_path:
        _refresh_locked_tabs(new_ss, new_class, lang_id, planar_path)
    reorder_tabs(new_ss)

    # Checkpoint here, before the local dir rename / manifest update below --
    # a real replacement sheet with real carried-over data exists as of this
    # point, so recovery must never delete it (restructure_journal.py's
    # is_rollback_safe() keys off exactly this checkpoint). The dir rename
    # and manifest write that follow are pure bookkeeping, safe to redo or
    # skip if a crash lands between them and are handled uniformly for both
    # a fresh run and --resume by _finish_new_sheet_created_unit.
    restructure_journal.record_checkpoint(
        lang_id, old_class, restructure_journal.NEW_SHEET_CREATED,
        spreadsheet_id=new_ss.id, url=new_ss.url, constructions=tab_names,
        construction_params=new_construction_params, version=new_version,
        new_class_name=new_class,
    )
    if journal_units is not None:
        journal_units.add((lang_id, old_class))

    # Move the local TSVs to the new class's folder, through the local-file
    # door (each old file's last version stays in archive/{old_class}/).
    if old_dir.exists():
        if new_dir.exists():
            print(f"    WARNING: {new_dir.relative_to(ROOT)} already exists — local rename skipped")
        else:
            file_door.move_class(lang_id, old_class, new_class,
                                 why=f"class renamed {old_class} -> {new_class} "
                                     f"(restructure-sheets --rename-class)")
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


def _parse_position_rename_map(argv: List[str], flag: str = "--rename-map") -> Dict[str, str]:
    """Parse --rename-map OLD:NEW where OLD and NEW are position names.

    Position names themselves contain a colon ("v:npsubj1"), so the plain
    first-colon split of _parse_flag_map read "v:npsubj1:v:subj" as renaming
    "v" to "npsubj1:v:subj" -- nothing matched, and the run dropped every
    element at the position instead of carrying it over (found 2026-10-11;
    the saved restructure transcripts had recorded the drop as expected).
    A value with three colons is split in the middle; one colon is a plain
    pair; anything else is ambiguous and refused.
    """
    result: Dict[str, str] = {}
    for i, arg in enumerate(argv):
        if arg != flag or i + 1 >= len(argv):
            continue
        pair = argv[i + 1]
        parts = pair.split(":")
        if len(parts) == 4:
            old, new = f"{parts[0]}:{parts[1]}", f"{parts[2]}:{parts[3]}"
        elif len(parts) == 2:
            old, new = parts
        else:
            raise SystemExit(
                f"{flag} {pair!r}: can't tell where the old position name ends. "
                f"Write it as OLD:NEW with both full names, e.g. "
                f"{flag} v:npsubj1:v:npsubj1new")
        if not old.strip() or not new.strip():
            raise SystemExit(f"{flag} requires 'old:new' format, got: {pair!r}")
        result[old.strip()] = new.strip()
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
    annotations (meaning the new rows will carry a note quoting them).
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
                f"({len(news_present)} new, old answers in a note on each)"
            )
    return lines



def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding restructure-sheets`.

    Declares every flag so `--help` and unknown-flag detection work, but the
    hand-rolled colon/comma helpers above (`_parse_flag_map`,
    `_parse_position_rename_map`, `_parse_split_flag_map`) still do the actual
    value extraction from `sys.argv` — they have their own tested parsing and error messages
    (`tests/test_restructure.py`), not reimplemented here.
    """
    ap = argparse.ArgumentParser(
        description="Archive and regenerate sheets after structural changes."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="archive old sheets and regenerate (default: dry run)",
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict to this language",
    )
    ap.add_argument(
        "--rename-map", metavar="OLD:NEW", action="append",
        help='rename a position, "old_pos_name:new_pos_name" (repeatable)',
    )
    ap.add_argument(
        "--rename-element", metavar="OLD:NEW", action="append",
        help='rename an element, "old_element:new_element" (repeatable)',
    )
    ap.add_argument(
        "--rename-class", metavar="OLD:NEW", action="append",
        help='rename a class, "old_class_name:new_class_name" (repeatable)',
    )
    ap.add_argument(
        "--split-element", metavar="OLD:NEW1,NEW2,...", action="append",
        help='retire one element into several, "old_element:new1,new2,..." '
             "(comma-separated, at least 2 targets)",
    )
    ap.add_argument(
        "--resume", action="store_true",
        help="finish or safely undo classes an interrupted run left mid-flight, "
             "then continue (requires --apply)",
    )
    ap.add_argument(
        "--rollback", action="store_true",
        help="undo classes an interrupted run left mid-flight (only where an old "
             "sheet was archived but no replacement was created yet), then stop "
             "(requires --apply)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
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
    and updates the manifest.  diagnostics_{lang_id}.yaml must be updated to use
    the new name BEFORE running this command (enforced by pre-flight checks).

    With --split-element old:new1,new2,..., retires one element in favor of several
    finer-grained replacements within the same position. New rows are left blank
    (no principled 1:1 value to carry over from a generic annotation), but each
    gets a note quoting the old element's answers if it had any, so
    re-annotators see the prior judgment instead of needing to remember or
    hunt for it. This also cascades
    into every pair-row construction referencing the retired element (see
    _apply_split_to_pair_rows) -- not just the "home" element-row construction.
    """
    # args itself is unused below -- build_parser().parse_args() (called here
    # when this isn't invoked with an already-parsed args from __main__.py's
    # dispatch) exists for --help and to hard-error on unknown flags. The
    # actual values are still pulled from sys.argv by the flag-map helpers
    # below, which have their own tested colon/comma parsing and error
    # messages (tests/test_restructure.py) -- not reimplemented here.
    if args is None:
        args = build_parser().parse_args()

    apply = "--apply" in sys.argv
    resume = "--resume" in sys.argv
    rollback = "--rollback" in sys.argv
    rename_map         = _parse_position_rename_map(sys.argv[1:], "--rename-map")
    element_rename_map = _parse_flag_map(sys.argv[1:], "--rename-element")
    rename_class_map   = _parse_flag_map(sys.argv[1:], "--rename-class")
    split_element_map  = _parse_split_flag_map(sys.argv[1:], "--split-element")
    conflict = set(split_element_map) & set(element_rename_map)
    if conflict:
        raise SystemExit(
            f"Element(s) {sorted(conflict)} appear in both --rename-element and "
            f"--split-element — pick one treatment per element."
        )
    if (resume or rollback) and not apply:
        raise SystemExit(
            "--resume/--rollback recover live Drive state left mid-flight by an "
            "interrupted run and require --apply."
        )
    lang_idx = sys.argv.index("--lang") if "--lang" in sys.argv else -1
    lang_filter = sys.argv[lang_idx + 1] if lang_idx >= 0 else None

    # coded_data_clean_tree is enforced centrally at the python -m coding
    # dispatch chokepoint now -- see coding/preconditions.py -- not here. It
    # still guards against exactly what it always has: this command reads
    # planar_{lang_id}.tsv/diagnostics_{lang_id}.tsv from coded_data/ as its
    # source of truth for the new sheet structure, and is the single most
    # destructive command in the project (archive-then-recreate). Phase 7 of
    # the data layer redesign (issue #271) closed the "no rollback" half of
    # that risk -- see restructure_journal.py's module docstring and the
    # journal-recovery block just below -- but a prior step's failed
    # auto-commit leaving coded_data/ stale/reverted is a different risk this
    # precondition still guards against. See update_sheets.py's guard comment
    # for why (issue #248's stray-row incident).
    doorway = get_doorway()
    manifest = load_manifest(doorway)

    # Interrupted-run recovery (Phase 7, issue #271). Anything still in the
    # journal is evidence a previous --apply run died mid-class; refuse to
    # start any new work -- including --rename-class below -- until it's
    # resolved, so a second run never has to guess which of two interrupted
    # sequences it's looking at.
    journal = restructure_journal.load_journal()
    if journal and not (resume or rollback):
        raise SystemExit(restructure_journal.format_incomplete_report(journal))

    resumed_units: Set[Tuple[str, str]] = set()
    sheet_links: List[Tuple[str, str, str]] = []  # (lang_id, class_name, url), for the summary
    lang_folder_urls: Dict[str, str] = {}  # lang_id -> Drive folder url (stable across restructures)

    if journal and rollback:
        stuck = {k: e for k, e in journal.items() if not restructure_journal.is_rollback_safe(e)}
        if stuck:
            raise SystemExit(
                "--rollback can't undo every interrupted class — some already have "
                "a real replacement sheet with carried-over annotation data, which "
                "rollback will not delete. Use --resume instead to finish those "
                "(rollback still isn't offered for them).\n\n"
                + restructure_journal.format_incomplete_report(stuck)
            )
        print("\nRolling back interrupted classes (old sheet restored, nothing else touched):")
        for entry in journal.values():
            _rollback_unit(doorway, manifest, entry)
            restructure_journal.clear_unit(entry["lang_id"], entry["class_name"])
        print("\nDone. Re-run without --rollback to continue restructuring normally.")
        return

    if journal and resume:
        print("\nResuming interrupted classes:")
        for entry in list(journal.values()):
            if restructure_journal.is_rollback_safe(entry):
                # Nothing of value existed past the archive yet, so "resume"
                # and "roll back, then let the loop below redo it cleanly"
                # are the same operation here -- reuse the safe primitive
                # rather than a second way to reach the same state.
                _rollback_unit(doorway, manifest, entry)
                restructure_journal.clear_unit(entry["lang_id"], entry["class_name"])
            else:
                _, display_class_name, url = _finish_new_sheet_created_unit(manifest, entry)
                # Clear by the journal KEY (old class name for a rename), not
                # the display name the function returns -- clearing by the
                # new name would silently no-op and leave this unit stuck.
                resumed_units.add((entry["lang_id"], entry["class_name"]))
                sheet_links.append((entry["lang_id"], display_class_name, url))

    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if lang_filter:
        planar_files = [f for f in planar_files
                        if _infer_language_id_from_planar_filename(f.name) == lang_filter]
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    pair_row_constructions = _get_pair_row_constructions()
    keyed_row_constructions = _get_keyed_row_constructions()
    restructured_classes: Set[Tuple[str, str]] = set()
    renamed_classes: Set[Tuple[str, str]] = set()  # (lang_id, old_class) journal keys
    # sheet_links/lang_folder_urls were initialized above, before the journal-
    # recovery block, so a resumed class's entry lands in the same summary/
    # notify list as one this run restructured fresh.

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
                _rename_class_for_language(
                    doorway, manifest, lang_id, old_class, new_class,
                    element_index, specs, apply, folder_id, planar_path,
                    sheet_links=sheet_links, journal_units=renamed_classes,
                )

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

        # The same per-tab criteria rule generate_sheets uses (coding.schemas.criteria_for),
        # so restructure produces the same param_names/param_values as initial generation.
        # (Until 2026-10-12 this was a hand-copied mirror that had already drifted: it
        # never handled phrasal_accent.)
        for _cls, _cons in list(classes.items()):
            classes[_cls] = apply_schema_criteria(_cls, _cons, lang_id)

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
                    ws = ss.worksheet(construction)
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
                keyed = keyed_row_constructions.get(class_name, {}).get(construction)
                if keyed:
                    tsv_path = CODED_DATA / lang_id / class_name / f"{construction}.tsv"
                    n_cells, n_flagged = _count_keyed_impacts(
                        tsv_path, param_values, rename_map, element_rename_map,
                        split_element_map)
                    if n_cells or n_flagged:
                        msg = f"    [{construction}] (keyed tab) rename {n_cells} cell(s)"
                        if n_flagged:
                            msg += (f", {n_flagged} row(s) on a split element — "
                                    f"NEEDS MANUAL REVIEW, flagged with a note on the row")
                        print(msg)
                        class_needs_restructure = True
                    continue
                if construction in pair_row_constructions.get(class_name, set()):
                    if rename_map:
                        tsv_path = CODED_DATA / lang_id / class_name / f"{construction}.tsv"
                        n_cells = _count_pair_rename_impacts(tsv_path, rename_map)
                        if n_cells:
                            print(f"    [{construction}] (pair tab) rename {n_cells} position cell(s)")
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
                            class_needs_restructure = True
                    continue
                rows = _element_rows_for(class_name, construction, element_index, lang_id,
                                         param_names, planar_file)
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

            if not class_needs_restructure:
                print(f"    (no changes — skipping)")
                continue

            if not apply:
                continue

            # Step 3: Archive existing sheet. (Retry on a transient
            # Google error happens in the Drive door, coding/drive_door.py.)
            new_version = version + 1
            if folder_id:
                archive_id = doorway.get_or_create_folder(
                    ARCHIVE_FOLDER_NAME, parent_id=folder_id,
                    identity=drive_door.folder("archive", lang_id))
                doorway.update_file(ss.id, name=f"{class_name}_{lang_id}_v{version}")
                doorway.move_file(ss.id, archive_id)
                _lock_archived_sheet(doorway, ss.id, lang_id)
                restructure_journal.record_checkpoint(
                    lang_id, class_name, restructure_journal.OLD_SHEET_ARCHIVED,
                    archived_spreadsheet_id=ss.id, folder_id=folder_id,
                )
                print(f"    Archived to _archived/{class_name}_{lang_id}_v{version}")

            # Step 4: Create new sheet and populate with carry-over
            sheet_title = f"{class_name}_{lang_id}"
            new_ss = doorway.create_spreadsheet(
                sheet_title, identity=drive_door.class_sheet(lang_id, class_name),
                replaces=ss.id)
            if folder_id:
                doorway.move_file(new_ss.id, folder_id)
                email = _annotator_email(lang_id)
                if email:
                    doorway.create_permission(new_ss.id, type="user", role="writer", email=email)

            default_ws = new_ss.sheet1
            tab_names = []
            new_construction_params = {}

            for construction, param_names, param_values in constructions_list:
                keyed = keyed_row_constructions.get(class_name, {}).get(construction)
                if keyed:
                    copied, changed, flagged = _copy_keyed_tab_with_rename(
                        ss, new_ss, construction, keyed, param_names, param_values,
                        rename_map, element_rename_map, split_element_map,
                        trailing=trailing_columns_for(lang_id))
                    tab_names.append(construction)
                    new_construction_params[construction] = {"param_names": param_names}
                    msg = f"    [{construction}] (keyed tab) copied {copied} rows, {changed} cell(s) renamed"
                    if flagged:
                        msg += f", {flagged} row(s) on a split element — NEEDS MANUAL REVIEW"
                    print(msg)
                    continue
                if construction in pair_row_constructions.get(class_name, set()):
                    # Pair-row constructions are copied from the archived sheet with
                    # rename_map applied to Position_A/Position_B cells and
                    # split_element_map applied to Element_A/Element_B cells; they
                    # are not regenerated from the planar structure.
                    criterion_col = _pair_construction_criterion(class_name, construction)
                    rows_copied, cells_renamed, rows_split, rows_manual = _copy_pair_tab_with_rename(
                        ss, new_ss, construction, rename_map, param_names, param_values,
                        split_element_map=split_element_map, criterion_col=criterion_col,
                        class_name=class_name, trailing=trailing_columns_for(lang_id),
                    )
                    tab_names.append(construction)
                    new_construction_params[construction] = {"param_names": param_names}
                    msg = f"    [{construction}] (pair tab) copied {rows_copied} rows, {cells_renamed} cell(s) renamed"
                    if rows_split:
                        msg += f", {rows_split} row(s) split (blank, old judgment quoted in a note)"
                    if rows_manual:
                        msg += f", {rows_manual} self-pair row(s) on a split element — NEEDS MANUAL REVIEW, not auto-handled"
                    print(msg)
                    continue
                rows = _element_rows_for(class_name, construction, element_index, lang_id,
                                         param_names, planar_file)
                existing = all_annotations.get(construction, {})
                if class_name == _br.CLASS_NAME:
                    existing = _rename_positions_in_annotations(existing, param_values, rename_map)
                carried, new_count, dropped_count = _write_tab_with_carryover(
                    new_ss, construction, param_names, param_values, rows, existing,
                    rename_map, element_rename_map,
                    tsv_target=file_door.annotation(lang_id, class_name, construction),
                    split_element_map=split_element_map,
                    trailing=trailing_columns_for(lang_id),
                )
                tab_names.append(construction)
                new_construction_params[construction] = {"param_names": param_names}
                print(f"    [{construction}] wrote: carried {carried}, new blank {new_count}, dropped {dropped_count}")

            if default_ws.title not in tab_names:
                new_ss.del_worksheet(default_ws)

            planar_path = planar_file.parent / f"planar_{lang_id}.tsv"
            _refresh_locked_tabs(new_ss, class_name, lang_id, planar_path)
            _create_status_tab(new_ss, tab_names)
            reorder_tabs(new_ss)

            restructured_classes.add((lang_id, class_name))
            restructure_journal.record_checkpoint(
                lang_id, class_name, restructure_journal.NEW_SHEET_CREATED,
                spreadsheet_id=new_ss.id, url=new_ss.url, constructions=tab_names,
                construction_params=new_construction_params, version=new_version,
            )

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
                    if apply:
                        tsv_changed = _cascade_rename_pair_tsv(
                            file_door.annotation(lang_id, class_name, construction), rename_map)
                        if tsv_changed:
                            print(
                                f"\n  [{lang_id} {class_name}/{construction}]"
                                f" local TSV: updated {tsv_changed} position cell(s)"
                            )
                    if apply and (lang_id, class_name) not in restructured_classes:
                        if not sheet_info:
                            continue
                        ss_pair = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])
                        try:
                            ws = ss_pair.worksheet(construction)
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
        # Only now -- after the Drive upload actually succeeded -- clear these
        # units from the journal. A crash between the write above and here
        # leaves them recorded as NEW_SHEET_CREATED, correctly re-detected as
        # still not synced to Drive rather than marked done early (Phase 7,
        # issue #271; see restructure_journal.py's module docstring).
        for lang_id, class_name in restructured_classes | resumed_units | renamed_classes:
            restructure_journal.clear_unit(lang_id, class_name)

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
        # The TSVs written above are committed by the local-file door when the
        # command ends.

        # restructure-sheets reads planar_{lang_id}.tsv but never writes it,
        # so the planar Sheet still shows the planar as it was. Bring it up to
        # date now rather than at the next daily refresh; this also renumbers
        # position numbers typed in the new sheets' answers, which were
        # carried over as typed (sync_planar._renumber_class_sheets). If that
        # fails, the daily refresh tries again and says so in planar-changed.
        print("\n--- Syncing planar Sheet ---")
        from .sync_planar import sync_planars
        try:
            sync_planars(lang_ids=sorted(set(processed_lang_ids)), apply=True)
        except SystemExit as exc:
            print(f"  {exc}")

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
