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

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

from .make_forms import (
    build_element_index,
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from .drive import (
    _check_coded_data_clean,
    _load_drive_config,
    _with_retry,
    load_manifest,
    upload_manifest,
)
from .drive_doorway import WorksheetHandle, WorksheetNotFound, get_doorway
# Which columns of a tab hold criteria, and what each one allows, is a rule
# refresh_dropdowns already owns — it was rewritten there for issue #272. Two
# commands answering the same question separately is how they came to disagree
# in the first place, so this imports the answer rather than restating it.
from .refresh_dropdowns import (
    _coreference_pair_criterion_map,
    _fresh_param_values,
    _resolve_criterion_columns,
)
from .generate_sheets import (
    _add_constructions_to_existing_sheet,
    _build_criterion_notes,
    _create_status_tab,
    _move_status_tab_to_end,
    _TRAILING_COLS,
)

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
    ws: WorksheetHandle,
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
        _with_retry(lambda: ws.spreadsheet.batch_update({"requests": requests}))
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
) -> List[List[str]]:
    """Compute rows present in the planar structure but missing from the sheet tab.

    ``col_start`` and ``num_criteria`` describe the tab's own criterion block,
    read from its header. They used to be a hardcoded 3 and the length of the
    manifest's criterion list; where the manifest had gone stale that made the
    new row the wrong width, and on a keystone row it wrote ``NA`` into
    ``Source`` and ``Comments``.
    """
    rows = _with_retry(ws.get_all_values)
    header = rows[0] if rows else []

    existing_keys = _sheet_element_keys(rows, header)
    planar_rows = _planar_rows_for_lang(element_index, lang_id)

    # Everything after the criterion block: Source, Comments, and any others.
    num_trailing = max(0, len(header) - col_start - num_criteria)

    missing_rows = []
    for pos, element, pos_name in planar_rows:
        element = element.strip()
        if element.startswith("-") or element.endswith("-"):
            element = f"[{element}]"
        key = (element, str(pos))
        if key not in existing_keys:
            is_keystone = pos_name.strip().lower() == "v:verbstem"
            param_vals = ["NA" if is_keystone else ""] * num_criteria
            row = [element, pos_name, str(pos)] + param_vals + [""] * num_trailing
            missing_rows.append(row)

    return missing_rows


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

    if apply:
        # planar_{lang_id}.tsv (read below) can be left in a reverted/stale
        # state mid-run if an earlier step's auto-commit failed silently —
        # see issue #248's stray-row incident, where this exact gap let
        # update-sheets write bogus rows to 16 live sheets from a stale
        # planar file. Refuse to proceed rather than risk repeating that.
        _check_coded_data_clean(extensions=(".tsv",))

    doorway = get_doorway()
    manifest = load_manifest(doorway)
    coref_pair_map = _coreference_pair_criterion_map()

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
    manifest_modified = False

    for manifest_lang, lang_data in manifest.items():
        if manifest_lang not in lang_planar_data:
            print(f"\n  [{manifest_lang}] No local planar file found — skipping")
            continue
        element_index, planar_pos_map, planar_path = lang_planar_data[manifest_lang]

        # The diagnostics YAML says what values each criterion allows, and it
        # says so per *construction*: several classes give their constructions
        # different criteria (segmental's aspiration_prominence and flapping,
        # phrasal_accent's prescreening and general), so a per-class reading
        # would give all but the first the wrong values — that was issue #272.
        lang_setup_dir = CODED_DATA / manifest_lang / "lang_setup"
        try:
            diag_rows = _read_diagnostics_for_language(manifest_lang, lang_setup_dir)
        except Exception as exc:
            print(f"\n  [{manifest_lang}] Could not read diagnostics: {exc}")
            diag_rows = []
        criteria_by_construction = {
            (cls, con): values for cls, con, _names, values in diag_rows
        }
        # Only a fallback, for naming the values of a criterion column left on
        # this tab that belongs to a sibling construction of the same class.
        class_criteria_union: Dict[str, Dict[str, List[str]]] = {}
        for cls, _con, _names, values in diag_rows:
            class_criteria_union.setdefault(cls, {}).update(values)

        for class_name, sheet_info in lang_data["sheets"].items():
            print(f"\n  {class_name}")
            ss = doorway.open_spreadsheet(sheet_info["spreadsheet_id"])

            construction_params = sheet_info.get("construction_params", {})
            constructions = sheet_info["constructions"]

            for construction in constructions:
                try:
                    ws = _with_retry(lambda: ss.worksheet(construction))
                except WorksheetNotFound:
                    print(f"    [{construction}] tab not found, skipping")
                    continue

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
                is_pair_row = "Element_A" in header or "Element_B" in header

                missing_trailing = [col for col in _TRAILING_COLS if col not in header]
                if missing_trailing:
                    any_changes = True
                    print(f"    [{construction}] add trailing column(s): {missing_trailing}")
                    if apply:
                        _add_trailing_columns(ws, header, rows)
                        # Re-read so the header and row count below describe the
                        # tab as it now is, not as it was before the insert.
                        rows = _with_retry(ws.get_all_values)
                        header = rows[0] if rows else []
                        num_data_rows = max(0, len(rows) - 1)

                if is_pair_row:
                    if not missing_trailing:
                        print(f"    [{construction}] up to date (pair-row tab — row updates skipped)")
                    continue

                # Which columns hold criteria comes from the tab's own header;
                # what each one allows comes from the diagnostics YAML. Neither
                # answer is the manifest's to give — it is bookkeeping, and it
                # goes stale. When the two cannot be reconciled, say so and
                # leave the tab alone: an added row of the wrong width puts
                # values under the wrong headings, which is worse than not
                # adding it.
                col_start, per_col, error = _resolve_criterion_columns(
                    header,
                    _fresh_param_values(
                        class_name, construction,
                        criteria_by_construction.get((class_name, construction), {}),
                        coref_pair_map),
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

                missing_rows = _compute_missing_rows(
                    ws, element_index, manifest_lang, col_start, len(per_col)
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

            # Detect constructions in the diagnostics YAML that are not yet in the
            # manifest (i.e. added after the sheet was first generated).  Create a
            # tab for each and update the manifest entry in memory.
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
                # Set outside the apply branch: adding a tab rewrites the
                # manifest too, and the dry run is what a coordinator reads to
                # decide whether to run the apply. This used to be set only on
                # apply, which made the "Would update manifest" line below
                # unreachable.
                manifest_modified = True
                if apply:
                    new_params = _add_constructions_to_existing_sheet(
                        ss, class_name, new_for_class, manifest_lang,
                        element_index, planar_path,
                    )
                    sheet_info["constructions"].extend(new_construction_names)
                    sheet_info.setdefault("construction_params", {}).update(new_params)

            # Ensure Status tab exists and is last (reflects any new tabs added above)
            if apply:
                all_constructions = list(constructions) + new_construction_names if new_construction_names else constructions
                _create_status_tab(ss, all_constructions)
                _move_status_tab_to_end(ss)

    if manifest_modified:
        drive_config = _load_drive_config()
        root_folder_id = drive_config.get("_root_folder_id", "")
        existing_file_id = drive_config.get("_planars_config_file_id", "")
        if apply:
            upload_manifest(doorway, manifest, root_folder_id, existing_file_id)
            print("\nManifest updated on Drive.")
        else:
            print("\nWould update manifest on Drive (new tabs detected).")

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
