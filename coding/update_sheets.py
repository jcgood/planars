#!/usr/bin/env python3
"""Update existing Google Sheets: add missing rows for new planar elements.

Run from the repo root:
    python -m coding update-sheets           # dry run — show what would change
    python -m coding update-sheets --apply   # apply changes to sheets

Operations performed per tab:
  1. Add missing trailing columns (e.g. Source) before existing ones
  2. Add missing rows for elements present in the current planar structure
     but absent from the sheet tab

And per sheet: add tabs for constructions new in the diagnostics YAML;
rebuild and protect the locked tabs (coding/locked_tabs.py) wherever they
differ from their sources; and give the Status tab any column
`planar.yaml`'s `status_tab.columns` lists that it lacks, and a row for
every construction. The sheets are the language's class sheets in the ID file,
and the tabs a sheet has are those labelled as constructions
(``construction_tabs()``). The daily refresh runs this with --apply. The planar file is read as the
source of truth, so ``--apply`` stops if ``coded_data/`` has uncommitted
changes (``coded_data_clean_tree``, enforced centrally by preconditions.py).

Which columns of a tab hold criteria, how wide an added row should be, and
what each dropdown allows come from the tab's own header plus the diagnostics
YAML, via ``_resolve_criterion_columns`` and ``_fresh_param_values``
(written for refresh-dropdowns, #272; moved here 2026-10-23 when that
command began reading the sheet spec instead). When the two cannot be
reconciled the tab is skipped with a reason rather than written to (otherwise a new row could narrow the whole
tab's dropdowns, or write ``NA`` into ``Source``/``Comments``).

Does NOT renumber positions or restructure existing content — use
python -m coding restructure-sheets for that (archives old sheet, regenerates with carry-over).

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

from .make_forms import (
    build_element_index,
    element_rows,
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from . import drive_ids
from .drive import _load_drive_config
from .drive_doorway import WorksheetHandle, WorksheetNotFound, get_doorway
from .schemas import criteria_for
from .generate_sheets import (
    _add_constructions_to_existing_sheet,
    _build_criterion_notes,
    _create_status_tab,
    starting_rows,
)
from .locked_tabs import rebuild_locked_tabs, reorder_tabs
from . import biuniqueness_rows as _br
from planars.schema_values import (
    ELEMENT_ROW_COLUMNS,
    PAIR_ROW_SHAPES,
    TRAILING_COLUMNS as _TRAILING_COLS, trailing_columns_for,
    is_keystone as _is_keystone,
)

import pandas as pd

CODED_DATA = ROOT / "coded_data"
_STRUCTURAL_COLS = set(ELEMENT_ROW_COLUMNS)


# ---------------------------------------------------------------------------
# Which columns hold criteria, and what each allows (#272)
# ---------------------------------------------------------------------------

def _fresh_param_values(
    class_name: str,
    construction: str,
    construction_criteria: Dict[str, List[str]],
    lang_id: str = "",
) -> Dict[str, List[str]]:
    """Derive fresh param_values for ONE construction from the diagnostics YAML.

    ``construction_criteria`` must be the criteria declared for this
    construction specifically. Passing a whole class's criteria here was
    issue #272: classes that declare per-construction criteria (``segmental``
    has ``aspiration_prominence`` and ``flapping``; ``phrasal_accent`` has
    ``prescreening`` and ``general``) had every construction resolved against
    the *first* one's values, so the rest fell through to a generic ``[y, n]``.
    That would have narrowed ``flapping`` from ``[y, n, both, na]`` and
    ``joint_accent`` from ``[always, sometimes, never]`` — the latter offering
    an annotator nothing but wrong answers.

    Which criterion a construction owns, and its values, come from
    ``coding.schemas.criteria_for`` — the one copy of that rule (until
    2026-10-12 this function carried its own per-class blocks).
    """
    return criteria_for(class_name, construction, list(construction_criteria),
                        construction_criteria, lang_id)[1]


def _detect_col_start(header: List[str], param_names: List[str]) -> int:
    """Return the 0-based column index where criterion columns begin."""
    for i, col in enumerate(header):
        if col in param_names:
            return i
    return 3  # fallback: standard element-row layout


def _resolve_criterion_columns(
    header: List[str],
    fresh: Dict[str, List[str]],
    class_criteria: Dict[str, List[str]],
) -> Tuple[Optional[int], List[List[str]], Optional[str]]:
    """Work out which columns get dropdowns, reading the SHEET, not the manifest.

    Returns ``(col_start, per_column_values, error)``. On any doubt it returns
    an error string and writes nothing, rather than guessing.

    This is the second half of issue #272. The old code took the *count* of
    dropdown columns from the manifest's ``param_names`` while taking their
    *start* from the header. When those disagreed — as on synth0001's
    coreference prescreening tab, whose manifest entry still listed the three
    pair criteria while the sheet had a single ``referential`` column — it
    wrote one dropdown per manifest entry starting at the header's offset, and
    ran off the end of the criteria onto ``Source`` and ``Comments``: y/n
    dropdowns on the two free-text columns an annotator writes prose in.

    The sheet's own header is authoritative for which columns exist. The
    diagnostics YAML is authoritative for what values each one allows. Neither
    job belongs to the manifest, which is bookkeeping and can go stale.
    """
    trailing = [header.index(c) for c in _TRAILING_COLS if c in header]
    end = min(trailing) if trailing else len(header)

    known = set(fresh) | set(class_criteria)
    col_start = _detect_col_start(header, known)
    if col_start >= end:
        return None, [], (
            f"no criterion columns between column {col_start} and "
            f"{header[end] if trailing else 'end of header'}"
        )

    names = header[col_start:end]
    per_col: List[List[str]] = []
    for name in names:
        # fresh first (this construction's own criteria), then the class's —
        # a sibling construction's criterion column left behind on this tab is
        # still a real criterion and should keep its real values.
        values = fresh.get(name) or class_criteria.get(name)
        if not values:
            return None, [], (
                f"column {header.index(name)} is {name!r}, which is not a "
                f"criterion of this class — refusing to write a dropdown onto "
                f"it. Known criteria: {sorted(known)}"
            )
        per_col.append(values)
    return col_start, per_col, None


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
        if _is_keystone(pos_name):
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
    ws: WorksheetHandle,
    header: List[str],
    rows: List[List[str]],
    trailing: List[str],
) -> List[str]:
    """Insert any missing trailing columns at their correct ordered position.

    ``trailing`` is the language's trailing columns (trailing_columns_for),
    in the schema's order (_TRAILING_COLS). Each missing column is inserted
    immediately before the first existing trailing column that follows it
    in that order, or appended at the end if none follow it.

    Returns the updated header list (mutated in place on the sheet).
    """
    missing = [col for col in trailing if col not in header]
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
# Header note helpers
# ---------------------------------------------------------------------------

def _write_header_notes(ws: WorksheetHandle, col_start: int,
                        criterion_names: List[str]) -> bool:
    """Write criterion description notes to header cells for element-row tabs.

    Looks up each criterion in diagnostic_criteria.yaml and writes the prose
    description as a hover note on the corresponding header cell.  Idempotent —
    safe to call on tabs that already have notes (overwrites with the same text).

    ``criterion_names`` are the tab's *own* header columns, and ``col_start`` is
    where they begin in that header. Both used to be taken from the manifest —
    a fixed column 3 and the manifest's criterion list — so on a tab whose
    manifest entry had gone stale the notes ran past the criteria and landed on
    ``Source`` and ``Comments``, describing criteria the tab does not have. Same
    mistake as issue #272 made with dropdowns.

    Returns True if any notes were written, False if the codebook had no
    descriptions for any of the criteria.
    """
    notes = _build_criterion_notes(criterion_names)
    sheet_id = ws.id
    requests = []
    for col_offset, note in enumerate(notes):
        if note:
            col_idx = col_start + col_offset
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    },
                    "cell": {"note": note},
                    "fields": "note",
                }
            })
    if requests:
        ws.spreadsheet.batch_update({"requests": requests})
        return True
    return False


# ---------------------------------------------------------------------------
# Per-tab update logic
# ---------------------------------------------------------------------------

def _compute_missing_rows(
    ws: WorksheetHandle,
    element_index,
    lang_id: str,
    col_start: int,
    num_criteria: int,
    *,
    class_name: str,
    construction: str,
) -> List[List[str]]:
    """Compute rows present in the planar structure but missing from the sheet tab.

    ``col_start`` and ``num_criteria`` describe the tab's own criterion block,
    read from its header. They used to be a hardcoded 3 and the length of the
    manifest's criterion list; where the manifest had gone stale that made the
    new row the wrong width, and on a keystone row it wrote ``NA`` into
    ``Source`` and ``Comments``.

    A missing row starts with the values a newly generated tab would give it
    (generate_sheets.starting_rows: keystone na, pre-fills); until
    2026-10-23 it got only the keystone's na, so an element added later
    missed every pre-fill.
    """
    rows = ws.get_all_values()
    header = rows[0] if rows else []

    existing_keys = _sheet_element_keys(rows, header)
    missing_keys = [(element, str(pos)) for element, _, pos in element_rows(element_index, lang_id)
                    if (element, str(pos)) not in existing_keys]
    if not missing_keys:
        return []

    # Everything after the criterion block: Source, Comments, and any others.
    num_trailing = max(0, len(header) - col_start - num_criteria)
    param_names = header[col_start:col_start + num_criteria]
    wanted = set(missing_keys)

    missing_rows = []
    for row in starting_rows(element_index, lang_id, class_name, construction, param_names):
        element, pos_name, pos = str(row[0]), str(row[1]), str(row[2])
        if (element, pos) in wanted:
            values = [str(v) for v in row[len(ELEMENT_ROW_COLUMNS):]]
            missing_rows.append([element, pos_name, pos] + values + [""] * num_trailing)

    return missing_rows


def _compute_missing_biuniq_element_rows(
    rows: List[List[str]],
    header: List[str],
    lang_id: str,
    col_start: int,
    num_criteria: int,
) -> List[List[str]]:
    """Missing rows for biuniqueness_deviations' elements tab (#254).

    Unlike _compute_missing_rows, only elements in biuniqueness scope
    (biuniqueness_rows.scoped_elements), built by the same element_rows
    that first built the tab (so an open-category row gets NA in has_allomorphs).
    """
    planar_path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
    planar_df = pd.read_csv(planar_path, sep="\t", dtype=str, keep_default_na=False)
    params = header[col_start:col_start + num_criteria]
    existing_keys = _sheet_element_keys(rows, header)
    num_trailing = max(0, len(header) - col_start - num_criteria)
    return [[str(v) for v in r] + [""] * num_trailing
            for r in _br.element_rows(planar_df, lang_id, params)
            if (r[0], str(r[2])) not in existing_keys]


def _apply_missing_rows(
    ws: WorksheetHandle,
    missing_rows: List[List[str]],
    num_data_rows_current: int,
    col_start: int,
    per_column_values: List[List[str]],
) -> None:
    """Append missing rows and re-apply dropdown validation to criterion columns.

    Validation is re-applied to all data rows (existing + new) so that the
    dropdown rules cover the full range after appending.

    ``per_column_values`` is each criterion column's real allowed-value set,
    resolved from the tab's header and the diagnostics YAML. It used to be
    ``[["y", "n"]] * len(param_names)`` — a hardcoded pair — so adding a single
    row narrowed the whole tab's dropdowns, dropping ``both`` and ``na`` from
    segmental's criteria and ``<position_number>`` from free_occurrence's, on
    rows nobody had touched.

    Args:
        ws: the worksheet to update.
        missing_rows: rows to append (already formatted with element, pos_name,
            pos_number, criterion values, trailing columns).
        num_data_rows_current: count of existing data rows before appending.
        col_start: 0-based column index where the criterion columns begin.
        per_column_values: allowed values per criterion column, in header order.
    """
    ws.append_rows(missing_rows, value_input_option="RAW")

    if per_column_values:
        from .generate_sheets import _format_and_validate
        total_rows = num_data_rows_current + len(missing_rows)
        _format_and_validate(ws, total_rows, per_column_values, col_start=col_start)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding update-sheets`."""
    ap = argparse.ArgumentParser(
        description="Add missing rows/columns to existing annotation sheets."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write changes (default: dry run)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding update-sheets`.

    Compares each sheet tab against the current planar structure and appends
    any elements that are present in the planar file but missing from the tab.
    Detects and warns about structural drift (position renumbering) without
    attempting to fix it — python -m coding restructure-sheets does that.
    In dry-run mode (no --apply) only prints what would change.
    """
    if args is None:
        args = build_parser().parse_args()
    apply = args.apply

    # coded_data_clean_tree is enforced centrally at the python -m coding
    # dispatch chokepoint now -- see coding/preconditions.py -- not here. It
    # still guards against exactly what it always has: planar_{lang_id}.tsv
    # (read below) left in a reverted/stale state mid-run if an earlier
    # step's auto-commit failed silently (issue #248's stray-row incident,
    # where this exact gap let update-sheets write bogus rows to 16 live
    # sheets from a stale planar file).
    doorway = get_doorway()
    config = _load_drive_config()
    # Imported here: restructure_sheets imports generate_sheets at load time,
    # as this module does.
    from .restructure_sheets import _get_keyed_row_constructions
    keyed_row_constructions = _get_keyed_row_constructions()

    # Build element index and planar position map for every language
    planar_files = sorted(CODED_DATA.glob("*/lang_setup/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/lang_setup/")

    lang_planar_data: Dict[str, tuple] = {}
    for planar_file in planar_files:
        lid = _infer_language_id_from_planar_filename(planar_file.name)
        ei = build_element_index(planar_file.name, planar_file.parent)
        lang_planar_data[lid] = (ei, _build_planar_pos_map(ei, lid), planar_file)

    print(f"{'DRY RUN — ' if not apply else ''}Languages: {list(lang_planar_data.keys())}")
    if not apply:
        print("(run with --apply to make changes)\n")

    any_changes = False
    any_drift = False

    for lang_id in drive_ids.languages(config):
        if lang_id not in lang_planar_data:
            print(f"\n  [{lang_id}] No local planar file found — skipping")
            continue
        element_index, planar_pos_map, planar_path = lang_planar_data[lang_id]

        # The diagnostics YAML says what values each criterion allows, and it
        # says so per *construction*: several classes give their constructions
        # different criteria (segmental's aspiration_prominence and flapping,
        # phrasal_accent's prescreening and general), so a per-class reading
        # would give all but the first the wrong values — that was issue #272.
        lang_setup_dir = CODED_DATA / lang_id / "lang_setup"
        try:
            diag_rows = _read_diagnostics_for_language(lang_id, lang_setup_dir)
        except Exception as exc:
            print(f"\n  [{lang_id}] Could not read diagnostics: {exc}")
            diag_rows = []
        criteria_by_construction = {
            (cls, con): values for cls, con, _names, values in diag_rows
        }
        # Only a fallback, for naming the values of a criterion column left on
        # this tab that belongs to a sibling construction of the same class.
        class_criteria_union: Dict[str, Dict[str, List[str]]] = {}
        for cls, _con, _names, values in diag_rows:
            class_criteria_union.setdefault(cls, {}).update(values)

        for class_name, spreadsheet_id in drive_ids.class_sheets(config, lang_id).items():
            print(f"\n  {class_name}")
            ss = doorway.open_spreadsheet(spreadsheet_id)

            # The tabs the sheet has now; the diagnostics YAML says which
            # it should have (new ones are added below).
            constructions = ss.construction_tabs()

            for construction in constructions:
                try:
                    ws = ss.worksheet(construction)
                except WorksheetNotFound:
                    print(f"    [{construction}] tab not found, skipping")
                    continue

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

                header = rows[0] if rows else []

                # Pair-row tabs (e.g. nonpermutability/general) use Element_A/Element_B
                # instead of Element/Position_Name. Row structure is managed by
                # --regen-construction, not update-sheets. Skip row updates entirely.
                #
                # Deliberately reads the tab's own live header rather than asking the
                # schema (diagnostic_classes.yaml's row_type, via
                # restructure_sheets._get_pair_row_constructions() -- the pattern
                # validate_coding.py/import_sheets.py use). This command is about to
                # WRITE to the tab, and the header is what's actually there right now;
                # the schema is what a construction is eventually supposed to look
                # like, and the two can disagree (stan1293's phrasal_accent/general is
                # a live example -- row_type: pair_rows in the schema, still
                # element-row-shaped on the live Sheet, per facts.yaml's
                # pair_row_construction_set drift_risk). Trusting the header keeps
                # this command from corrupting a tab that hasn't been rebuilt yet.
                #
                # "Any of element_pairs' columns anywhere in the header" (not
                # header_shape()'s starts-with test): a half-edited pair header must
                # still count as pair-row here, so the tab is skipped, not written to.
                is_pair_row = any(c in header for c in PAIR_ROW_SHAPES["element_pairs"])

                lang_trailing = trailing_columns_for(lang_id)
                missing_trailing = [col for col in lang_trailing if col not in header]
                if missing_trailing:
                    any_changes = True
                    print(f"    [{construction}] add trailing column(s): {missing_trailing}")
                    if apply:
                        _add_trailing_columns(ws, header, rows, lang_trailing)
                        # Re-read so the header and row count below describe the
                        # tab as it now is, not as it was before the insert.
                        rows = ws.get_all_values()
                        header = rows[0] if rows else []
                        num_data_rows = max(0, len(rows) - 1)

                if is_pair_row:
                    if not missing_trailing:
                        print(f"    [{construction}] up to date (pair-row tab — row updates skipped)")
                    continue

                # Keyed-row tabs (biuniqueness_deviations' morphemes/morphs) are
                # rebuilt from their source tab by --regen-construction, never
                # extended row by row here.
                if construction in keyed_row_constructions.get(class_name, {}):
                    if not missing_trailing:
                        print(f"    [{construction}] up to date (keyed-row tab — rows are "
                              f"managed by --regen-construction)")
                    continue

                # Which columns hold criteria comes from the tab's own header;
                # what each one allows comes from the diagnostics YAML. When the two cannot be reconciled, say so and
                # leave the tab alone: an added row of the wrong width puts
                # values under the wrong headings, which is worse than not
                # adding it.
                col_start, per_col, error = _resolve_criterion_columns(
                    header,
                    _fresh_param_values(
                        class_name, construction,
                        criteria_by_construction.get((class_name, construction), {}),
                        lang_id),
                    class_criteria_union.get(class_name, {}))
                if error:
                    print(f"    [{construction}] SKIPPED — {error}")
                    continue

                # Write criterion notes to all element-row tabs on every apply
                # (idempotent — safe to rewrite; skipped in dry-run to avoid
                # an extra API call just to read existing note text for comparison).
                if apply:
                    _write_header_notes(
                        ws, col_start, header[col_start:col_start + len(per_col)])

                if class_name == _br.CLASS_NAME and construction == _br.ELEMENTS:
                    # Only elements in biuniqueness scope, built exactly as
                    # the tab was first built.
                    missing_rows = _compute_missing_biuniq_element_rows(
                        rows, header, lang_id, col_start, len(per_col))
                else:
                    missing_rows = _compute_missing_rows(
                        ws, element_index, lang_id, col_start, len(per_col),
                        class_name=class_name, construction=construction,
                    )

                if not missing_rows and not missing_trailing:
                    print(f"    [{construction}] up to date")
                    continue

                if missing_rows:
                    any_changes = True
                    elements = [r[0] for r in missing_rows]
                    print(f"    [{construction}] add {len(missing_rows)} row(s): {elements}")
                    if apply:
                        _apply_missing_rows(ws, missing_rows, num_data_rows,
                                            col_start, per_col)

                if apply and (missing_rows or missing_trailing):
                    print(f"    [{construction}] done")

            # Detect constructions in the diagnostics YAML that the sheet has no
            # tab for (i.e. added after the sheet was first generated).  Create
            # a tab for each.
            yaml_constructions = {
                construction: (names, values)
                for cls, construction, names, values in diag_rows
                if cls == class_name
            }

            new_construction_names = sorted(set(yaml_constructions) - set(constructions))
            if new_construction_names:
                new_for_class = [
                    (c, yaml_constructions[c][0], yaml_constructions[c][1])
                    for c in new_construction_names
                ]
                for c, pn, _ in new_for_class:
                    action = "Adding" if apply else "Would add"
                    print(f"    [{c}] {action} new tab ({len(pn)} criterion/criteria)")
                    any_changes = True
                if apply:
                    _add_constructions_to_existing_sheet(
                        ss, class_name, new_for_class, lang_id,
                        element_index, planar_path,
                    )

            # The locked tabs (Instructions, Planar Structure — schemas/planar.yaml
            # locked_tabs) are rebuilt from their sources and protected on every
            # sheet, every day; only what differs is written. This is the run
            # that keeps them current whichever command changed their source.
            for change in rebuild_locked_tabs(ss, class_name, lang_id,
                                              planar_path, apply=apply):
                any_changes = True
                print(f"    [locked tab] {'' if apply else 'would '}{change}")

            # Ensure the Status tab exists with every column planar.yaml gives
            # it and a row per construction, and every tab is in its place
            # (reflects any new tabs added above).
            all_constructions = list(constructions) + new_construction_names if new_construction_names else constructions
            for change in _create_status_tab(ss, all_constructions, apply=apply):
                any_changes = True
                print(f"    {'' if apply else 'would '}{change}")
            if apply:
                reorder_tabs(ss, list(yaml_constructions))

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
