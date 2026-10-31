#!/usr/bin/env python3
"""Import filled Google Sheets annotation forms back to TSVs for analysis.

Run from the repo root:
    python -m coding import-sheets              # dry run: report what would be written
    python -m coding import-sheets --apply      # write TSVs when content has changed
    python -m coding import-sheets --apply --overwrite-existing  # rewrite even if the cells match

Reads each language's class sheets from the ID file (drive_config.json),
downloads each sheet tab (the constructions the sheet has a tab for),
validates values, and writes {construction}.tsv to
coded_data/{lang_id}/{class_name}/.

Every file is written through the local-file door (coding/file_door.py): a
TSV whose downloaded content is unchanged is skipped; a changed one's
previous version goes to coded_data/{lang_id}/archive/{class_name}/, the
change goes in the language's changes.tsv, and the files written are
committed and pushed in planars-data when the command ends. Refuses to run
with --apply while coded_data/ has uncommitted changes (precondition
coded_data_clean_tree, checked by the dispatcher).

It also keeps each language's tab-status record,
coded_data/{lang_id}/records/tab_status.tsv (file_door.tab_status; Phase 10
unit 16): every class sheet's Status tab as read (each tab's status and its
Marked by cell), so the record holds them as well as Google. A sheet that
could not be read keeps its previous rows. Nothing reads the record back;
the Status tab stays the source.

Exits non-zero only when the import itself broke: a class's spreadsheet
could not be opened, or a tab is missing from it. Invalid values are not an
import failure (issue #309): they are printed here, graded by
validate_coding.needs_fixing, and reported by validate-coding (run at the
end of an --apply that wrote anything, and daily by sheet-validation.yml),
which lists them in each sheet's Status tab.

What happens depends on each tab's Status:
  ready-for-review  imported in full; problems printed.
  in-progress       imported as a backup with warnings suppressed; missing
                    rows or columns, or a large drop in filled cells, file a
                    collaborator-check issue instead. --ignore-status treats
                    every tab as ready-for-review.

Only the class sheets are imported. The planar and diagnostics Sheets are
read-only copies of their sources in planars-data and are never read back
(Phase 10 unit 11b, 2026-10-24); a change to either source is proposed on
the language's proposal sheet (proposal-sheets, accept-proposal).

Which constructions have pair rows comes from diagnostic_classes.yaml
(`_get_pair_row_constructions`, the same source validate-coding uses), never
from a list in this file (data_dependency_schema/facts.yaml,
`pair_row_construction_set`).

Side effect: invalid cells are highlighted pink in the Google Sheet during
import (same behaviour as validate-coding), on every tab whatever its Status.
This write-back happens even without --apply and even when the local TSV is
skipped.

Authentication: same OAuth2 setup as generate_sheets.py (see drive.py).
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent

import pandas as pd

from . import drive_ids
from .drive import _load_drive_config
from .drive_doorway import get_doorway, WorksheetNotFound
from planars.schema_values import (STATUS_CONSTRUCTION_COLUMN, STATUS_IN_PROGRESS,
                                   STATUS_MARKED_BY_COLUMN, STATUS_READY,
                                   STATUS_STATUS_COLUMN, is_keystone)
from .restructure_sheets import _get_keyed_row_constructions, _get_pair_row_constructions
from . import file_door, issues
from . import validate_coding as _val
from .validate import ValidationIssue
from .make_forms import (
    resolve_keystone_active,
    resolve_keystone_na_criteria,
)

ERROR_DIR    = ROOT / "import_errors"

# The share of an in-progress tab's filled cells (in rows present before and
# after) that may disappear in one import before it files a collaborator-check
# issue. A policy setting, not a linguistic fact; the one place it is stated
# (hidden-facts M4). schemas/issue_labels.yaml's prose says ">10%".
COLLABORATOR_CHECK_DECREASE = 0.10

# Re-export constants so external code that imported them directly still works.
_STRUCTURAL_COLS      = _val._STRUCTURAL_COLS
_PAIR_STRUCTURAL_COLS = _val._PAIR_STRUCTURAL_COLS
_TRAILING_COLS        = _val._TRAILING_COLS


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

def _get_output_path(lang_id: str, class_name: str, construction: str) -> Path:
    """The construction's annotation TSV under coded_data/ (the local-file door's path)."""
    return file_door.annotation(lang_id, class_name, construction).path


# ---------------------------------------------------------------------------
# The tab-status record (Phase 10 unit 16; docs/plain-record-design.md § 3.1)
# ---------------------------------------------------------------------------

# The Status tab's columns the record keeps: what only the Status tab holds.
# Needs fixing is left out: validate-coding rebuilds it from the TSVs.
_RECORD_STATUS_COLUMNS = (STATUS_CONSTRUCTION_COLUMN, STATUS_STATUS_COLUMN,
                          STATUS_MARKED_BY_COLUMN)
_RECORD_HEADER = ("Class",) + _RECORD_STATUS_COLUMNS


def _status_cells(rows: List[List[str]]) -> List[List[str]]:
    """A Status tab's rows as [construction, status, marked by], in tab order,
    found by header name; a column the tab lacks reads as blank."""
    if not rows:
        return []
    header = [h.strip() for h in rows[0]]
    at = [header.index(c) if c in header else None for c in _RECORD_STATUS_COLUMNS]
    out = []
    for r in rows[1:]:
        cells = [r[i].strip() if i is not None and i < len(r) else "" for i in at]
        if cells[0]:
            out.append(cells)
    return out


def _status_record_text(lang_id: str, classes, read: Dict[str, List[List[str]]]) -> str:
    """The language's tab-status record: a row per class and tab, for every
    class sheet the language has (``classes``, in their order). A class whose
    sheet could not be read this run keeps its rows from the previous record,
    so a failed read never looks like the tabs' statuses being cleared."""
    previous: Dict[str, List[List[str]]] = {}
    for row in list(csv.reader(io.StringIO(file_door.read(file_door.tab_status(lang_id)) or ""),
                               delimiter="\t"))[1:]:
        if row:
            previous.setdefault(row[0], []).append(row[1:])
    records = []
    for class_name in classes:
        for cells in read.get(class_name, previous.get(class_name, [])):
            records.append(dict(zip(_RECORD_HEADER, [class_name, *cells])))
    return file_door.tsv_text(_RECORD_HEADER, records)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _highlight_invalid_cells(ws, bad_cells: List[Tuple[int, int]]) -> None:
    """Delegate to validate_coding.highlight_cells."""
    _val.highlight_cells(ws, bad_cells)


def _validate_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    keystone_active: bool = False,
    keystone_na_criteria: List[str] = None,
    class_name: str = None,
    lang_id: str = None,
) -> Tuple[List[Dict], List[ValidationIssue], List[Tuple[int, int]]]:
    """Delegate to validate_coding.validate_annotation_rows.

    Returns (records, issues, bad_cells).
    """
    records, issues = _val.validate_annotation_rows(
        rows, expected_params, tab_name, param_values,
        keystone_active=keystone_active,
        keystone_na_criteria=keystone_na_criteria,
        class_name=class_name, lang_id=lang_id,
    )
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, issues, bad_cells


def _validate_pair_tab(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    class_name: str = None,
    lang_id: str = None,
) -> Tuple[List[Dict], List[ValidationIssue], List[Tuple[int, int]]]:
    """Delegate to validate_coding.validate_pair_rows for pair-row tabs.

    Returns (records, issues, bad_cells) in the same format as _validate_tab.
    """
    records, issues = _val.validate_pair_rows(rows, expected_params, tab_name, param_values,
                                              class_name=class_name, lang_id=lang_id)
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, issues, bad_cells


def _validate_keyed_tab(
    rows: List[List[str]],
    keyed: Dict,
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    class_name: str = None,
    lang_id: str = None,
) -> Tuple[List[Dict], List[ValidationIssue], List[Tuple[int, int]]]:
    """Delegate to validate_coding.validate_keyed_rows for keyed-row tabs
    (biuniqueness_deviations' morphemes/morphs). Same return format as _validate_tab."""
    header = rows[0] if rows else []
    expected_params = [c for c in header[len(keyed["columns"]):] if c not in _TRAILING_COLS]
    records, issues = _val.validate_keyed_rows(
        rows, keyed["columns"], expected_params, tab_name, param_values,
        keyed.get("blank_ok_when"), class_name=class_name, lang_id=lang_id)
    bad_cells = [i.cell for i in issues if i.cell is not None]
    return records, issues, bad_cells


# ---------------------------------------------------------------------------
# TSV writing
# ---------------------------------------------------------------------------

def _tsv_content_changed(path: Path, header: List[str], records: List[Dict]) -> bool:
    """Return True if the new header+records differ from the existing file at path.

    A different header (a column added, removed or moved on the sheet) is a
    change. Otherwise compares cell text element-wise after normalising
    NaN → "". Returns True when content differs or the file cannot be parsed.

    The header check came first only on 2026-10-13: before, the old file was
    lined up to the new header before comparing, which threw away any column
    the sheet no longer had — so a column deleted on the sheet never left the
    local file (synth0001's coreference tabs kept two dead columns for months).
    """
    try:
        existing = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    except Exception:
        return True
    if list(existing.columns) != list(header):
        return True
    new_df = pd.DataFrame(records).reindex(columns=header).fillna("")
    existing = existing.reindex(columns=header).fillna("")
    if existing.shape != new_df.shape:
        return True
    # Compare cell text, not DataFrames: DataFrame.equals also compares column
    # dtypes, and a tab with a header but no rows reads from disk as string
    # columns but builds from an empty record list as float columns -- so an
    # empty tab always looked "changed" and was re-archived on every import.
    return existing.astype(str).values.tolist() != new_df.astype(str).values.tolist()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _write_error_report(lang_id: str, lines: List[str], timestamp: str) -> Path:
    """Write warning lines to import_errors/{lang_id}_{timestamp}.txt."""
    ERROR_DIR.mkdir(exist_ok=True)
    report_path = ERROR_DIR / f"{lang_id}_{timestamp}.txt"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _detect_collaborator_anomalies(
    out_path: Path,
    header: List[str],
    records: List[Dict],
    expected_params: List[str],
    lang_id: str,
    class_name: str,
    construction: str,
) -> List[str]:
    """Detect structural anomalies in an in-progress sheet vs the existing local TSV.

    Checks:
      A: Missing rows — (Element, Position_Number) keys present in local TSV
         but absent from the downloaded sheet.
      B: Missing/renamed param columns — columns in the local TSV header that
         no longer appear in the downloaded sheet.
      D: >10% annotated-cell decrease — significant value loss in matching rows.

    Returns a list of human-readable anomaly description strings (empty if none).
    Skips the check if no local TSV exists yet (first backup).
    """
    if not out_path.exists():
        return []
    try:
        old_df = pd.read_csv(out_path, sep="\t", dtype=str, keep_default_na=False)
    except Exception:
        return []

    anomalies: List[str] = []

    # A: Missing rows
    if "Element" in old_df.columns and "Position_Number" in old_df.columns:
        old_keys = {
            (str(r["Element"]).strip(), str(r["Position_Number"]).strip())
            for _, r in old_df.iterrows()
        }
        new_keys = {
            (r.get("Element", "").strip(), r.get("Position_Number", "").strip())
            for r in records
        }
        missing = old_keys - new_keys
        if missing:
            samples = sorted(f"{el} (pos {pos})" for el, pos in missing)
            suffix = "..." if len(samples) > 5 else ""
            anomalies.append(
                f"Missing rows: {len(missing)} row(s) present in local TSV absent from "
                f"sheet: {', '.join(samples[:5])}{suffix}"
            )

    # B: Missing/renamed param columns
    if expected_params:
        trailing_set = set(_TRAILING_COLS)
        old_params = [
            c for c in old_df.columns
            if c not in _STRUCTURAL_COLS and c not in trailing_set
        ]
        missing_cols = [c for c in old_params if c not in header]
        if missing_cols:
            anomalies.append(
                f"Missing columns: param column(s) in local TSV absent from sheet: "
                f"{missing_cols}"
            )

    # D: >10% annotated-cell decrease (restricted to rows present in both)
    if expected_params and "Element" in old_df.columns and "Position_Number" in old_df.columns:
        old_key_to_row: Dict[tuple, object] = {}
        for _, row in old_df.iterrows():
            if is_keystone(row.get("Position_Name", "")):
                continue
            key = (str(row.get("Element", "")).strip(), str(row.get("Position_Number", "")).strip())
            old_key_to_row[key] = row

        new_key_to_row: Dict[tuple, Dict] = {}
        for r in records:
            if is_keystone(r.get("Position_Name", "")):
                continue
            key = (r.get("Element", "").strip(), r.get("Position_Number", "").strip())
            new_key_to_row[key] = r

        common_keys = set(old_key_to_row) & set(new_key_to_row)
        if common_keys:
            old_params_in_df = [p for p in expected_params if p in old_df.columns]
            old_annotated = sum(
                1 for key in common_keys
                for p in old_params_in_df
                if str(old_key_to_row[key].get(p, "")).strip() not in ("", "na", "?")
            )
            new_annotated = sum(
                1 for key in common_keys
                for p in expected_params
                if new_key_to_row[key].get(p, "").strip() not in ("", "na", "?")
            )
            if old_annotated > 0:
                decrease = (old_annotated - new_annotated) / old_annotated
                if decrease > COLLABORATOR_CHECK_DECREASE:
                    anomalies.append(
                        f"Annotated-cell decrease: {old_annotated} → {new_annotated} "
                        f"({decrease:.0%} decrease, threshold {COLLABORATOR_CHECK_DECREASE:.0%})"
                    )

    return anomalies


def _notify_collaborator_check(entries: List[Dict]) -> None:
    """Create or update a GitHub collaborator-check issue for in-progress anomalies.

    Anomalies (missing rows, missing columns, >10% cell decrease) in in-progress
    sheets are coordinator-facing signals, not blocking errors. The coordinator
    should verify with the collaborator whether the change was intentional.
    """
    if not issues.available():
        return

    lines = [
        f"{len(entries)} in-progress sheet(s) have structural anomalies that warrant a "
        f"check with the collaborator. These sheets are still marked `in-progress` so "
        f"no pipeline action is blocked — but the coordinator should verify that the "
        f"changes are intentional.\n"
    ]
    for e in entries:
        lines.append(f"### {e['lang_id']} / {e['class_name']} / {e['construction']}")
        for a in e["anomalies"]:
            lines.append(f"- {a}")
        lines.append("")

    try:
        number, created = issues.file_issue(
            "collaborator-check",
            "In-progress sheet anomalies — verify with collaborator",
            "\n".join(lines))
        print(f"   GitHub issue #{number} {'created' if created else 'updated'} "
              "(collaborator-check).")
    except Exception as exc:
        print(f"   (Could not create GitHub issue: {exc})")


def _verify_sheet_ids(doorway, config: Dict, lang_filter: str = None) -> None:
    """Abort if any class sheet ID in the ID file is inaccessible.

    Protects against writing TSVs from an ID file that points to wrong
    (empty, deleted, or duplicate) spreadsheets. Runs a lightweight Drive
    metadata fetch for each sheet ID — no sheet content is downloaded at
    this stage.
    """
    bad: List[str] = []
    for lang_id in drive_ids.languages(config):
        if lang_filter and lang_id != lang_filter:
            continue
        for class_name, spreadsheet_id in drive_ids.class_sheets(config, lang_id).items():
            try:
                doorway.get_file(spreadsheet_id, fields="id,trashed")
            except Exception as e:
                bad.append(f"  {lang_id}/{class_name}: {spreadsheet_id} — {e}")
    if bad:
        print("ERROR: The ID file contains inaccessible spreadsheet IDs:")
        for line in bad:
            print(line)
        print("The ID file may point to deleted/moved sheets.")
        print("→ Run: python -m coding integrity-check --sheets")
        print("  This will list which spreadsheet IDs are unreachable and what to do next.")
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding import-sheets`."""
    ap = argparse.ArgumentParser(
        description="Download filled annotation sheets to TSVs."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="write TSVs (default: dry run)",
    )
    ap.add_argument(
        "--overwrite-existing", action="store_true", dest="force",
        help="rewrite a TSV even when its cells match the sheet (e.g. to bring its "
             "formatting in line); a file whose bytes are already identical is "
             "never rewritten",
    )
    ap.add_argument(
        "--ignore-status", action="store_true",
        help="treat all tabs as ready-for-review, regardless of their Status tab",
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict to this language",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding import-sheets`.

    Dry-run by default — pass --apply to write any TSVs. Reads the class
    sheets from the ID file, downloads each construction tab, validates values, and writes
    filled TSVs under coded_data/{lang_id}/{class_name}/. Compares downloaded
    content to the existing file: if changed, writes the new one through the
    local-file door (which archives the old); if unchanged, skips with "No
    changes". --overwrite-existing rewrites a file whose cells match but whose
    text differs; the door never rewrites identical bytes.
    Writes an error report to import_errors/ if any warnings are generated.
    """
    if args is None:
        args = build_parser().parse_args()
    apply = args.apply
    force = args.force
    ignore_status = args.ignore_status
    lang_filter = args.lang
    timestamp = file_door.stamp()

    if not apply:
        print("DRY RUN — pass --apply to write TSVs.\n")

    # coded_data_clean_tree is enforced centrally at the python -m coding
    # dispatch chokepoint now -- see coding/preconditions.py -- not here.
    print("Connecting to Google...")
    doorway = get_doorway()
    config = _load_drive_config()

    if apply:
        _verify_sheet_ids(doorway, config, lang_filter)

    total_files = 0
    in_progress_files = 0
    total_warnings = 0
    # Problems that mean the import itself broke, and make this command exit
    # non-zero so the daily refresh files an import-error issue (#283): a
    # class's spreadsheet couldn't be opened, or a tab is missing from a
    # sheet. Problems in the data (an invalid value on a ready-for-review tab)
    # are not counted here since #309: validate-coding reports them, to the
    # annotator (the sheet's Status tab) and in a sheet-validation issue.
    total_import_errors = 0
    all_collaborator_check: List[Dict] = []
    pair_row_constructions = _get_pair_row_constructions()
    keyed_row_constructions = _get_keyed_row_constructions()

    for lang_id in drive_ids.languages(config):
        if lang_filter and lang_id != lang_filter:
            continue
        print(f"\nLanguage: {lang_id}")
        lang_warning_lines: List[str] = []
        lang_param_map = _val._load_param_map(lang_id)
        # {class: its Status tab's rows}, for the language's tab-status record.
        lang_statuses: Dict[str, List[List[str]]] = {}
        lang_classes = drive_ids.class_sheets(config, lang_id)

        for class_name, spreadsheet_id in lang_classes.items():
            print(f"\n  {class_name}")
            try:
                ss = doorway.open_spreadsheet(spreadsheet_id)
            except Exception as e:
                msg = f"[{class_name}] could not open spreadsheet {spreadsheet_id!r} for {lang_id}: {e}"
                print(f"    ERROR: {msg}")
                lang_warning_lines.append(f"ERROR: {msg}")
                total_import_errors += 1
                continue

            status_rows = _val.read_status_tab(ss)[1]
            lang_statuses[class_name] = _status_cells(status_rows)
            status_map = _val.status_map(status_rows)
            marked_by = _val.marked_by_map(status_rows)
            if not status_map and not ignore_status:
                print(f"    (no Status tab found — importing all constructions)")

            # The tabs the sheet has, then any construction its Status tab lists
            # that has no tab (deleted by hand): reported below as a missing tab.
            tabs = ss.construction_tabs()
            for construction in tabs + [c for c in status_map if c not in tabs]:
                try:
                    ws = ss.worksheet(construction)
                except WorksheetNotFound:
                    msg = f"[{class_name}/{construction}] tab not found in sheet, skipping"
                    print(f"    ERROR: {msg}")
                    lang_warning_lines.append(f"ERROR: {msg}")
                    total_import_errors += 1
                    continue

                # Determine tab status. In-progress sheets are imported for backup
                # and validation (pink highlighting), but pipeline warnings are
                # suppressed and anomalies are raised as collaborator-check.
                # --ignore-status treats all tabs as ready.
                tab_status = STATUS_READY
                if not ignore_status and status_map:
                    tab_status = status_map.get(construction, STATUS_IN_PROGRESS)
                in_progress = (tab_status != STATUS_READY)
                # What the annotator's Status tab says, for the change log:
                # --ignore-status must not record a tab as ready-for-review
                # when its annotator has not marked it so. Who marked a
                # ready tab is recorded with it.
                sheet_status = (status_map.get(construction, STATUS_IN_PROGRESS)
                                if status_map else "no Status tab")
                if marked_by.get(construction):
                    sheet_status += f", marked by {marked_by[construction]}"

                rows = ws.get_all_values()

                header = rows[0] if rows else []

                # Per-param allowed values: the language's diagnostics YAML through
                # coding.schemas.criteria_for — the same source validate-coding
                # uses.
                param_values = lang_param_map.get(class_name, {}).get(construction, {}).get("values")

                # Which constructions have pair rows comes from the schema, not
                # from a list written out here. This used to name only
                # nonpermutability and coreference, and so missed
                # phrasal_accent/general — which validate-coding, reading the
                # schema, treated as pair rows all along. Two places deciding
                # the same thing and disagreeing is the defect this project
                # keeps hitting; validate_coding.revalidate_sheets is the pattern copied.
                is_pair_tab = construction in pair_row_constructions.get(class_name, set())
                keyed = keyed_row_constructions.get(class_name, {}).get(construction)
                if keyed:
                    expected_params = [c for c in header[len(keyed["columns"]):]
                                       if c not in _TRAILING_COLS]
                    records, found, bad_cells =_validate_keyed_tab(
                        rows, keyed, construction, param_values,
                        class_name=class_name, lang_id=lang_id,
                    )
                elif is_pair_tab:
                    expected_params = (
                        [c for c in header if c not in _PAIR_STRUCTURAL_COLS and c not in _TRAILING_COLS]
                    )
                    records, found, bad_cells =_validate_pair_tab(
                        rows, expected_params, construction, param_values,
                        class_name=class_name, lang_id=lang_id,
                    )
                else:
                    expected_params = (
                        [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
                    )
                    ka = resolve_keystone_active(
                        lang_id, class_name, construction,
                        data_dir=file_door.planar(lang_id).path.parent,
                    )
                    kna = resolve_keystone_na_criteria(class_name)
                    records, found, bad_cells =_validate_tab(
                        rows, expected_params, construction, param_values,
                        keystone_active=bool(ka),
                        keystone_na_criteria=kna,
                        class_name=class_name, lang_id=lang_id,
                    )

                if bad_cells:
                    try:
                        _highlight_invalid_cells(ws, bad_cells)
                    except Exception as e:
                        print(f"    WARNING: could not highlight cells: {e}")

                # For ready-for-review tabs, show what is wrong (structural and
                # invalid-value), graded by validate_coding's one rule against
                # the tab's real Status (--ignore-status changes what is
                # imported, not how serious a value is). For in-progress tabs,
                # say nothing — partial or invalid annotation is expected there.
                # None of it stops the import (#309).
                if not in_progress:
                    shown = [i for i in _val.grade(found, status_map.get(construction, STATUS_IN_PROGRESS))
                             if i.kind != _val.BLANK]
                    for i in shown:
                        print(f"    {i}")
                        lang_warning_lines.append(f"[{class_name}/{construction}] {i}")
                    total_warnings += len(shown)
                else:
                    print(f"    [{construction}] status: {tab_status!r} — importing for backup")

                out_path = _get_output_path(lang_id, class_name, construction)
                out_name = out_path.name
                dest = f"coded_data/{lang_id}/{class_name}/{out_name}"
                label = " [backup]" if in_progress else ""

                if not apply:
                    if out_path.exists():
                        changed = _tsv_content_changed(out_path, header, records)
                        action = "Would overwrite (changed)" if changed else "No changes"
                    else:
                        action = "Would create"
                    print(f"    [{construction}]{label} {action} → {dest}")
                    continue

                if out_path.exists():
                    if not force and not _tsv_content_changed(out_path, header, records):
                        print(f"    [{construction}]{label} No changes → {dest}")
                        continue

                    if in_progress:
                        anomalies = _detect_collaborator_anomalies(
                            out_path, header, records, expected_params,
                            lang_id, class_name, construction,
                        )
                        if anomalies:
                            all_collaborator_check.append({
                                "lang_id": lang_id,
                                "class_name": class_name,
                                "construction": construction,
                                "anomalies": anomalies,
                            })
                            for a in anomalies:
                                print(f"    [{construction}] ANOMALY: {a}")

                # The door keeps the previous version in archive/{class}/ and
                # logs the change in the language's changes.tsv.
                file_door.write(file_door.annotation(lang_id, class_name, construction),
                                file_door.tsv_text(header, records),
                                why=f"imported from the annotator's sheet ({sheet_status})")

                # Count rows with at least one blank param cell (for status line).
                # Pair-row and keyed-row sheets have no keystone; element-row
                # sheets exclude it.
                if is_pair_tab or keyed:
                    blank_count = sum(
                        1 for r in records
                        if any(r.get(p, "") == "" for p in expected_params)
                    )
                else:
                    blank_count = sum(
                        1 for r in records
                        if not is_keystone(r.get("Position_Name", ""))
                        and any(r.get(p, "") == "" for p in expected_params)
                    )
                status = f"{len(records)} rows"
                if blank_count:
                    status += f", {blank_count} blank param cells"
                print(f"    [{construction}]{label} {status} → {dest}")
                if in_progress:
                    in_progress_files += 1
                else:
                    total_files += 1

        record = _status_record_text(lang_id, lang_classes, lang_statuses)
        if apply:
            file_door.write(file_door.tab_status(lang_id), record,
                            why="read from the class sheets' Status tabs")
        elif record != file_door.read(file_door.tab_status(lang_id)):
            print(f"\n  Would update {lang_id}'s tab-status record "
                  f"({file_door.tab_status(lang_id).relpath})")

        if lang_warning_lines:
            report_path = _write_error_report(lang_id, lang_warning_lines, timestamp)
            print(f"\n  Error report: {report_path.relative_to(ROOT)}")

    backup_part = f", {in_progress_files} in-progress backup(s)" if in_progress_files else ""
    print(f"\nDone. {total_files} file(s) written{backup_part}, {total_warnings} warning(s).")

    # Raise collaborator-check issue if any in-progress anomalies were detected.
    if all_collaborator_check:
        if apply:
            print(f"\n⚠  {len(all_collaborator_check)} in-progress sheet(s) have anomalies — verify with collaborator")
            _notify_collaborator_check(all_collaborator_check)
        else:
            print(f"\n⚠  {len(all_collaborator_check)} in-progress sheet(s) have anomalies (dry run):")
            for e in all_collaborator_check:
                print(f"   {e['lang_id']}/{e['class_name']}/{e['construction']}: "
                      f"{len(e['anomalies'])} anomaly(s)")

    if apply and (total_files > 0 or in_progress_files > 0):
        print("\n--- Revalidating sheets ---")
        from .validate_coding import revalidate_sheets
        lang_ids = [lang_filter] if lang_filter else None
        revalidate_sheets(lang_ids=lang_ids)

    if total_import_errors:
        # Issue #283: these used to never affect the exit code, so the daily
        # refresh's import-error issue never fired for them -- only a hard
        # crash did. Checked last, after every other step above, so one
        # unreadable sheet doesn't cut short notification/revalidation work
        # this run should still do regardless.
        print(f"\n{total_import_errors} sheet(s) or tab(s) could not be read — see ERROR lines above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
