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

  diagnostics_{lang_id}.yaml — per-language criterion source of truth (edit this).
                               --rename/--split/--merge --apply edit it directly
                               (_edit_diagnostics_yaml): only the criteria named change,
                               and its comments and layout are kept
  diagnostics_{lang_id}.tsv  — a copy generated from the YAML; after those edits it is
                               regenerated the way sync-diagnostics-yaml --apply does it
                               (#315: until 2026-10-18 the TSV was edited and the YAML
                               rebuilt from it, losing every field but notes)
  Google Sheets              — annotation form column headers (always updated)

Imported TSVs in coded_data/ are downstream of Sheets; after any lifecycle operation run
  python -m coding import-sheets --overwrite-existing --apply
to bring them in sync.

--rename renames a criterion in-place, preserving all cell values and validation.
--split adds new1/new2 columns and renames old to _split_old; coordinator remaps values then
  removes the stale column manually.
--merge adds a new column and renames old1/old2 to _merged_old1/_merged_old2; same cleanup.
Every added column goes where the diagnostics file lists it among the tab's criteria
(_insert_at), so the sheet's criteria stay in the file's order.

integrity-check --sheets warns on any _split_ or _merged_ prefixed column headers
(sheet_spec.PARKED_COLUMN_PREFIXES).

Reads: one open, one tab list and one batch of header rows per spreadsheet
(_read_headers), however many tabs it has; a tab is re-read only after this run
writes to it. Reading tab by tab took two reads per tab and brought the
2026-10-20 daily refresh within one retry of Google's per-minute read limit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

from .make_forms import (
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
    _dump_diagnostics_yaml,
    _encode_criteria_dict,
    _load_diagnostics_yaml_for_edit,
    _resolve_diagnostics_yaml_path,
)
from .sync_diagnostics_yaml import _sync_to_tsv
from .validate_diagnostics import validate_diagnostics_yaml
from .schemas import criteria_for, criterion_values
from planars.schema_values import is_keystone
from .drive import (
    _load_drive_config, _save_drive_config,
    load_manifest, upload_manifest,
)
from .drive_doorway import WorksheetHandle, get_doorway
from .generate_sheets import CODED_DATA
from .schemas import is_free_entry
from .sheet_spec import MERGED_PREFIX, SPLIT_PREFIX, parked_operation
from . import biuniqueness_rows as _br
from . import drive_door
from planars.schema_values import (
    ELEMENT_ROWS,
    ROW_IDENTITY_COLUMNS,
    TRAILING_COLUMNS,
    header_shape,
)

_TRAILING_SET = set(TRAILING_COLUMNS)

# Structural columns that are never param columns, across all sheet types:
# the element-row and pair-row columns declared in planar.yaml, plus the
# keyed-row columns (biuniqueness_deviations, #254) declared in
# diagnostic_classes.yaml.
_STRUCTURAL_SET = (ROW_IDENTITY_COLUMNS
                   | {c for cols, _ in _br.KEYED.values() for c in cols})


# ---------------------------------------------------------------------------
# Sheet introspection
# ---------------------------------------------------------------------------

def _read_headers(ss, titles: List[str]) -> Dict[str, List[str]]:
    """Each named tab's header row, in one read for the whole spreadsheet.

    Reading tab by tab cost two reads per tab (finding it, then its header);
    the daily refresh's run came within one retry of Google's per-minute read
    limit on 2026-10-20. Every tab in ``titles`` must exist.
    """
    if not titles:
        return {}
    ranges = [gspread.utils.absolute_range_name(t, "1:1") for t in titles]
    got = ss.values_batch_get(ranges).get("valueRanges", [])
    if len(got) != len(titles):
        raise RuntimeError(
            f"Asked {ss.title!r} for {len(titles)} header rows and got "
            f"{len(got)} back; nothing was changed.")
    return {t: list((vr.get("values") or [[]])[0]) for t, vr in zip(titles, got)}


def _get_current_params(header: List[str]) -> Tuple[List[str], int]:
    """Return (param_names, comments_col_0based) from a tab's header row.

    Param columns are those that are neither structural nor trailing — identified
    by exclusion rather than by a fixed positional offset. This handles both
    nonpermutability pair sheets (Element_A, Element_B — 2 fixed cols) and
    coreference pair sheets (Element_A, Position_A, Position_B, Direction — 4
    fixed cols) without needing to distinguish between them.
    """
    params = []
    comments_col = len(header)  # default: insert at end if Comments not found
    for i, col in enumerate(header):
        if col in _TRAILING_SET:
            comments_col = i
            break
        if col not in _STRUCTURAL_SET:
            params.append(col)
    return params, comments_col


# ---------------------------------------------------------------------------
# Column rename
# ---------------------------------------------------------------------------

def _rename_column(ws: WorksheetHandle, old_name: str, new_name: str) -> bool:
    """Rename a column header in-place. Returns True if found and renamed."""
    header = ws.row_values(1)
    try:
        col_1based = header.index(old_name) + 1
    except ValueError:
        return False
    ws.update_cell(1, col_1based, new_name)
    return True


# ---------------------------------------------------------------------------
# Criterion edits (diagnostics_{lang_id}.yaml — a class's criteria mappings)
# ---------------------------------------------------------------------------
# Each edit replaces some criteria of one mapping ({name: [values]}) with new
# ones at the first old one's place. Only the criteria named change: the rest
# of the file, comments included, is written back as it was read.

def _replace_criteria(crit: Dict, olds: List[str], news: List[Tuple[str, List[str]]]) -> bool:
    """Replace the criteria `olds` present in `crit` with `news`, in place.

    The new criteria go where the first old one was. A comment written above
    or beside a replaced criterion moves to the first new one, so no comment
    is lost. Returns False (and changes nothing) if none of `olds` is there.
    """
    present = [o for o in olds if o in crit]
    if not present:
        return False
    for name, _ in news:
        if name in crit and name not in olds:
            raise SystemExit(
                f"ERROR: criterion '{name}' is already listed beside "
                f"{', '.join(present)}; renaming, splitting or merging onto an "
                f"existing criterion would merge two columns' answers. "
                f"Choose another name.")
    keys = list(crit)
    at = min(keys.index(o) for o in present)
    comments = getattr(crit, "ca", None)
    moved = [comments.items.pop(o) for o in present
             if comments is not None and o in comments.items]
    for o in present:
        del crit[o]
    for i, (name, values) in enumerate(news):
        crit.insert(at + i, name, values)
    if moved:
        comments.items[news[0][0]] = _merge_comment_slots(moved)
    return True


def _merge_comment_slots(slots: List[list]) -> list:
    """Combine ruamel comment entries of several criteria into one.

    Slot 1 holds the comment lines written above a key; those are joined.
    Any other slot (a comment at the end of the line) can hold only one, so
    two of them stop the command rather than drop one.
    """
    merged = [None, None, None, None]
    for slot in slots:
        for i, part in enumerate(slot):
            if part is None:
                continue
            if i == 1:
                merged[1] = (merged[1] or []) + list(part)
            elif merged[i] is None:
                merged[i] = part
            else:
                raise SystemExit(
                    "ERROR: two of the criteria being merged each have a comment "
                    "at the end of their line in the diagnostics YAML. Move one "
                    "of them above its line by hand, then re-run.")
    return merged


def _criteria_mappings(class_data: Dict) -> List[Tuple[Optional[str], Dict]]:
    """A class's criteria mappings: (None, criteria) and
    (construction, its criteria) for each entry of construction_criteria."""
    out: List[Tuple[Optional[str], Dict]] = []
    if class_data.get("criteria"):
        out.append((None, class_data["criteria"]))
    for construction, crit in (class_data.get("construction_criteria") or {}).items():
        if crit:
            out.append((construction, crit))
    return out


def _edit_yaml_criteria(
    yaml_data: Dict,
    olds: List[str],
    news_fn,
    class_filter: Optional[str],
) -> List[str]:
    """Replace criteria `olds` with `news_fn(crit)` in every matching class.

    news_fn: (criteria mapping) -> [(name, values), ...] — the replacements.
    class_filter: restrict to this class (None = every class).
    Edits yaml_data in place; returns one description per mapping changed.
    """
    changes = []
    for cls, class_data in (yaml_data.get("classes") or {}).items():
        if class_filter and cls != class_filter:
            continue
        for construction, crit in _criteria_mappings(class_data):
            if not any(o in crit for o in olds):
                continue
            before = ", ".join(_encode_criteria_dict(crit))
            _replace_criteria(crit, olds, news_fn(crit))
            where = f"{cls}/{construction}" if construction else cls
            changes.append(
                f"  [{where}] diagnostics criteria: {before!r} -> "
                f"{', '.join(_encode_criteria_dict(crit))!r}")
    return changes


def _rename_in_yaml(yaml_data: Dict, old: str, new: str,
                    class_filter: Optional[str]) -> List[str]:
    """Rename criterion `old` to `new`, keeping its values."""
    return _edit_yaml_criteria(
        yaml_data, [old], lambda crit: [(new, crit[old])], class_filter)


def _split_in_yaml(yaml_data: Dict, old: str, new1: str, new2: str) -> List[str]:
    """Replace criterion `old` with `new1, new2`, each with its schema values."""
    return _edit_yaml_criteria(
        yaml_data, [old],
        lambda crit: [(new1, _schema_values(new1)), (new2, _schema_values(new2))],
        None)


def _merge_in_yaml(yaml_data: Dict, old1: str, old2: str, new: str) -> List[str]:
    """Replace criteria `old1` and `old2` with `new` (its schema values), at
    the place of whichever of the two comes first."""
    return _edit_yaml_criteria(
        yaml_data, [old1, old2], lambda crit: [(new, _schema_values(new))], None)


def _edit_diagnostics_yaml(lang_id: str, planar_dir: Path, renames, splits, merges,
                           apply: bool) -> None:
    """Apply --rename/--split/--merge to diagnostics_{lang_id}.yaml.

    Prints each criteria change. With apply, writes the YAML (only the
    criteria named change; comments and layout are kept) and regenerates
    diagnostics_{lang_id}.tsv from it, as sync-diagnostics-yaml --apply does.
    An edit that would leave the YAML failing validation writes nothing.
    """
    yaml_path = _resolve_diagnostics_yaml_path(lang_id, planar_dir)
    if not yaml_path.exists():
        raise SystemExit(
            f"ERROR: {yaml_path} does not exist. --rename/--split/--merge edit "
            f"the diagnostics YAML; create it first, then re-run.")
    data = _load_diagnostics_yaml_for_edit(yaml_path)
    changes: List[str] = []
    for cls_filter, old, new in renames:
        changes += _rename_in_yaml(data, old, new, cls_filter)
    for old, new1, new2 in splits:
        changes += _split_in_yaml(data, old, new1, new2)
    for old1, old2, new in merges:
        changes += _merge_in_yaml(data, old1, old2, new)
    for change in changes:
        print(change)
    if not (apply and changes):
        return

    blocking = [i for i in validate_diagnostics_yaml(data, lang_id)
                if i.level == "error" and i.blocking]
    if blocking:
        for e in blocking:
            print(f"  [{lang_id}] ERROR {e.location}: {e.message}")
        raise SystemExit(
            f"ERROR: the edited diagnostics_{lang_id}.yaml would not pass "
            f"validation (above); nothing was written.")
    yaml_path.write_text(_dump_diagnostics_yaml(data), encoding="utf-8")
    print(f"  [{lang_id}] YAML updated → {yaml_path.name}")
    _sync_to_tsv(lang_id, apply=True, error_langs=[])


def _schema_values(name: str) -> List[str]:
    """A new criterion's allowed values, from diagnostic_criteria.yaml.

    A criterion created by --split or --merge must already be defined in the
    schema: there is no `[y, n]` default any more (removed 2026-10-12, Phase
    10), so a criterion with no values stops the command instead of quietly
    getting values nobody chose.
    """
    vals = criterion_values(name)
    if not vals:
        raise SystemExit(
            f"ERROR: criterion '{name}' is not defined (with values) in "
            f"schemas/diagnostic_criteria.yaml. Add it there first, then re-run.")
    return vals


# ---------------------------------------------------------------------------
# Column insertion
# ---------------------------------------------------------------------------

def _insert_at(header: List[str], param: str, order: List[str], trailing_at: int) -> int:
    """Where a new criterion column goes (0-based): before the first column
    that comes after it in ``order`` (the tab's criteria in the language's
    diagnostics file), else before the trailing columns. So the sheet's
    criteria keep the file's order, as the Drive door's spec expects."""
    later = set(order[order.index(param) + 1:]) if param in order else set()
    for i, col in enumerate(header[:trailing_at]):
        if col in later:
            return i
    return trailing_at


def _insert_param_columns(
    ws: WorksheetHandle,
    new_params: List[str],
    param_values_map: Dict[str, List[str]],
    order: List[str],
) -> None:
    """Insert new criterion columns, each where ``order`` puts it (_insert_at)."""
    for param in new_params:
        header = ws.row_values(1)
        _, trailing_at = _get_current_params(header)
        _insert_param_column(ws, param, param_values_map,
                             _insert_at(header, param, order, trailing_at))


def _insert_param_column(
    ws: WorksheetHandle,
    param: str,
    param_values_map: Dict[str, List[str]],
    insert_at: int,
) -> None:
    """Insert one criterion column at 0-based ``insert_at``, header and keystone
    NA filled, with its dropdown."""
    new_params = [param]
    spreadsheet = ws.spreadsheet
    sheet_id = ws.id
    n = 1

    # 1. Insert a blank column at insert_at
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

    # Only element-row tabs have a keystone row. A keyed morphs tab also has
    # Position_Name second, and its stems sit at v:verbstem, but those rows
    # are ordinary rows to annotate, not a keystone to NA out.
    keystone_row: Optional[int] = None
    is_element_tab = bool(all_values) and header_shape(all_values[0]) == ELEMENT_ROWS
    for i, row in enumerate(all_values):
        if i == 0 or not is_element_tab:
            continue
        if len(row) > 1 and is_keystone(row[1]):
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
        values = param_values_map[param_name]  # criteria_for guarantees every column has values
        if is_free_entry(values):
            continue
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

def _apply_split_to_sheet(
    ws: WorksheetHandle,
    old_name: str,
    new1: str,
    new2: str,
    param_values_map: Dict[str, List[str]],
    order: List[str],
) -> bool:
    """Split old_name into new1 + new2 in a sheet tab.

    Inserts new1 and new2 columns where ``order`` (the tab's criteria in the
    diagnostics file) puts them, then renames old_name to _split_{old_name}
    so annotators can remap values before cleanup.
    Returns True if old_name was found.
    """
    header = ws.row_values(1)
    if old_name not in header:
        return False
    _insert_param_columns(ws, [new1, new2], param_values_map, order)
    _rename_column(ws, old_name, f"{SPLIT_PREFIX}{old_name}")
    return True


def _apply_merge_to_sheet(
    ws: WorksheetHandle,
    old1: str,
    old2: str,
    new: str,
    param_values_map: Dict[str, List[str]],
    order: List[str],
) -> Tuple[bool, bool]:
    """Merge old1 and old2 into new in a sheet tab.

    Inserts a new column where ``order`` puts it, then renames old1/old2 to
    _merged_{old1}/_merged_{old2} so annotators can remap values.
    Returns (old1_found, old2_found).
    """
    header = ws.row_values(1)
    old1_found = old1 in header
    old2_found = old2 in header
    if not old1_found and not old2_found:
        return False, False
    _insert_param_columns(ws, [new], param_values_map, order)
    if old1_found:
        _rename_column(ws, old1, f"{MERGED_PREFIX}{old1}")
    if old2_found:
        _rename_column(ws, old2, f"{MERGED_PREFIX}{old2}")
    return old1_found, old2_found


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _build_dropdown_refresh_requests(
    ws: WorksheetHandle,
    header: List[str],
    stale_params: List[str],
    exp_values: Dict[str, List[str]],
) -> List[dict]:
    """Build setDataValidation requests for params with stale allowed values.

    ``header`` is the tab's current header row. Uses ws.row_count as the end
    row so validation covers all current data rows.
    """
    if not stale_params:
        return []
    num_rows = ws.row_count
    requests = []
    for param in stale_params:
        if param not in header:
            continue
        col_idx = header.index(param)  # 0-based
        values = exp_values[param]  # criteria_for guarantees every column has values
        if is_free_entry(values):
            continue
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


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding sync-params`.

    Declares every flag so `--help` and unknown-flag detection work, but the
    actual values are still pulled from sys.argv by _parse_renames/
    _parse_splits/_parse_merges below, which have their own tested parsing
    and error messages (tests/test_sync_params.py) -- not reimplemented here.
    """
    ap = argparse.ArgumentParser(
        description="Sync diagnostic criterion columns when diagnostics_{lang_id}.yaml changes."
    )
    ap.add_argument("--apply", action="store_true",
                     help="apply changes to sheets (default: dry run)")
    ap.add_argument("--remove", action="store_true",
                     help="also remove stale columns")
    ap.add_argument("--refresh-dropdowns", action="store_true",
                     help="refresh allowed values on existing dropdowns instead of syncing columns")
    ap.add_argument("--rename", metavar="[CLASS:]OLD:NEW", action="append",
                     help="rename a criterion, in one class or all classes (repeatable)")
    ap.add_argument("--split", metavar="OLD:NEW1:NEW2", action="append",
                     help="split one criterion into two (repeatable)")
    ap.add_argument("--merge", metavar="OLD1:OLD2:NEW", action="append",
                     help="merge two criteria into one (repeatable)")
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding sync-params`.

    Compares expected param columns (from diagnostics_{lang_id}.yaml, or the TSV if there
    is no YAML) against actual sheet headers, inserts new columns in the diagnostics
    file's order (_insert_at), optionally removes stale columns,
    applies dropdown validation, and updates the Drive manifest if anything changed.
    In dry-run mode (no --apply) only prints what would change.
    """
    # args itself is unused below -- see build_parser()'s docstring.
    if args is None:
        args = build_parser().parse_args()

    apply = "--apply" in sys.argv
    remove = "--remove" in sys.argv
    refresh_dropdowns = "--refresh-dropdowns" in sys.argv
    renames = _parse_renames()
    splits  = _parse_splits()
    merges  = _parse_merges()

    # coded_data_clean_tree is enforced centrally at the python -m coding
    # dispatch chokepoint now -- see coding/preconditions.py -- not here.
    # See update_sheets.py's guard comment for why: a prior step's failed
    # auto-commit can leave coded_data/ (including the diagnostics/planar
    # TSVs this command reads) in a stale, partially-reverted state.
    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    print("Connecting to Google APIs...")
    doorway = get_doorway()
    manifest = load_manifest(doorway)

    any_changes = False
    manifest_changed = False

    for planar_file in planar_files:
        planar_dir = planar_file.parent
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)

        # Rename/split/merge edit diagnostics_{lang_id}.yaml, the source,
        # before it is read below, so the sheet operations see the new
        # criteria; the TSV is then regenerated from it (#315).
        if renames or splits or merges:
            _edit_diagnostics_yaml(lang_id, planar_dir, renames, splits, merges, apply)

        specs = _read_diagnostics_for_language(lang_id, planar_dir)

        # Build expected: class_name -> construction -> (param_names, param_values)
        expected: Dict[str, Dict[str, Tuple[List[str], Dict[str, List[str]]]]] = {}
        for class_name, construction, param_names, param_values in specs:
            expected.setdefault(class_name, {})[construction] = (param_names, param_values)

        # Each tab's own criteria (a construction with a schema `criterion:` gets
        # just that column): the one rule, coding.schemas.criteria_for. Until
        # 2026-10-12 this was a coreference-only copy of it.
        for class_name, by_con in expected.items():
            for con_name, (names, values) in list(by_con.items()):
                by_con[con_name] = criteria_for(class_name, con_name, names, values, lang_id)

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
                print(f"[{class_name}] Not in diagnostics_{lang_id}.yaml — skipping")
                continue

            ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])
            # One read for the tab list and one for every header row, per
            # spreadsheet; a tab is re-read only after this run writes to it.
            tabs = {ws.title: ws for ws in ss.worksheets()}
            headers = _read_headers(ss, [c for c in expected[class_name] if c in tabs])

            for construction, (exp_params, exp_values) in expected[class_name].items():
                ws = tabs.get(construction)
                if ws is None:
                    print(f"  [{class_name}/{construction}] Tab not found — skipping")
                    continue
                header = headers[construction]

                # Apply renames first so add/remove detection sees the updated headers
                if renames:
                    for cls_filter, old_name, new_name in renames:
                        if cls_filter is not None and cls_filter != class_name:
                            continue
                        found = old_name in header
                        if found:
                            print(f"  [{class_name}/{construction}] Rename: {old_name} → {new_name}")
                            if apply:
                                _rename_column(ws, old_name, new_name)
                                header = ws.row_values(1)
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
                    default_vals = {n: _schema_values(n) for n in (new1, new2)}
                    if old in header:
                        print(f"  [{class_name}/{construction}] Split: {old} -> {new1}, {new2}")
                        if apply:
                            _apply_split_to_sheet(ws, old, new1, new2, default_vals, exp_params)
                            header = ws.row_values(1)
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
                    default_vals = {new: _schema_values(new)}
                    o1_found = old1 in header
                    o2_found = old2 in header
                    if o1_found or o2_found:
                        print(f"  [{class_name}/{construction}] Merge: {old1}, {old2} -> {new}")
                        if apply:
                            _apply_merge_to_sheet(ws, old1, old2, new, default_vals, exp_params)
                            header = ws.row_values(1)
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

                current_params, _ = _get_current_params(header)
                current_set = set(current_params)
                expected_set = set(exp_params)

                # Preserve expected order; only add params that are genuinely new.
                # Exclude _split_/_merged_ stale columns from removed_params — these
                # are preserved intentionally until the coordinator remaps values.
                new_params = [p for p in exp_params if p not in current_set]
                removed_params = [
                    p for p in current_params
                    if p not in expected_set
                    and not parked_operation(p)
                ]
                # Snapshot before either branch below overwrites it. Only the
                # columns a branch actually inserts or deletes get their sheet
                # dropdown touched, so the manifest's record for every other
                # criterion of this construction must carry over unchanged —
                # see the "manifest lied about param_values" fix below.
                prior_values = dict(
                    sheet_info.get("construction_params", {})
                    .get(construction, {}).get("param_values", {})
                )

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
                                requests = _build_dropdown_refresh_requests(
                                    ws, header, stale, exp_values)
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
                        _insert_param_columns(ws, new_params, exp_values, exp_params)
                        # Update manifest construction_params so Colab reads the right params.
                        # Only the columns just inserted got a dropdown written — a
                        # pre-existing criterion's values are untouched by this call,
                        # so recording exp_values for it here would tell the next
                        # --refresh-dropdowns run "up to date" for a column that was
                        # never actually pushed. Carry the rest forward from prior_values.
                        cp = sheet_info.setdefault("construction_params", {})
                        cp.setdefault(construction, {})["param_names"] = exp_params
                        cp[construction]["param_values"] = {
                            **prior_values,
                            **{p: exp_values[p] for p in new_params if p in exp_values},
                        }
                        manifest_changed = True
                        print(f"    Added: {new_params}")

                if removed_params:
                    if remove and apply:
                        print(f"  [{class_name}/{construction}] Removing params: {removed_params}")
                        # Re-read header after any insertions above so indices are current.
                        if new_params:
                            header = ws.row_values(1)
                        # Delete columns right-to-left to preserve indices during deletion.
                        # --remove is the coordinator saying these answers go.
                        reason = (f"sync-params --remove: {', '.join(removed_params)} "
                                  "removed from the diagnostics file")
                        with drive_door.replacing(ws, reason):
                            for param in sorted(removed_params, key=lambda p: header.index(p),
                                                reverse=True):
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
                        # Update manifest construction_params. Deleting a column says
                        # nothing about whether a DIFFERENT column's dropdown is
                        # current, so drop only the removed keys rather than
                        # re-stamping every criterion with exp_values (same fix as
                        # the new_params branch above, same reason).
                        cp = sheet_info.setdefault("construction_params", {})
                        cp.setdefault(construction, {})["param_names"] = exp_params
                        current_values = cp[construction].get("param_values", prior_values)
                        cp[construction]["param_values"] = {
                            p: v for p, v in current_values.items() if p not in removed_params
                        }
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
                            # Columns were just inserted or deleted: read the header afresh.
                            requests = _build_dropdown_refresh_requests(
                                ws, ws.row_values(1), stale2, exp_values)
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
        file_id = upload_manifest(doorway, manifest, root_folder_id, existing_file_id)
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
