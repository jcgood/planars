#!/usr/bin/env python3
"""Annotation sheet validation and the validate-coding command.

Validates filled annotation sheets against their expected criterion columns
and allowed values. Updates pink cell highlighting so collaborators can find
and fix errors without coordinator help.

How serious a problem is depends on the tab's Status (`needs_fixing`, the
one rule; issue #309): an invalid value on a ready-for-review tab is an
error, listed in that sheet's Status tab ("Needs fixing" column, one line
per cell, rewritten every run and blank when clean) and counted in the exit
code, so the sheet-validation workflow files an issue for it. On an
in-progress tab it is a warning and a pink cell only. Blank cells are never
errors.

Run from the repo root:
    python -m coding validate-coding                   # all languages
    python -m coding validate-coding --lang arao1248   # one language
    python -m coding validate-coding --notify          # and tell annotators

With --notify (daily, sheet-validation.yml), each language's annotator is
told about values to fix: coding/annotator_notices.py.

Three row shapes are checked, each by its own validator: element rows,
pair rows (``row_type: pair_rows``) and keyed rows (``row_type: keyed_rows``);
which constructions have the last two comes from ``diagnostic_classes.yaml``
(``restructure_sheets._get_pair_row_constructions`` / ``_get_keyed_row_constructions``).
``read_status_tab`` / ``tab_statuses`` are the one reader of a sheet's Status tab.

If a tab's header isn't the row shape its construction declares, it is
reported once (``_wrong_shape``) and nothing else on that tab is checked,
since every value would be read from the wrong column. The message names
both ways out: the ``generate-sheets --regen-construction`` command that
rebuilds the sheet, and the ``row_type`` field to correct if the sheet is
the one that's right. The rows still come back unchanged
(``_plain_records``), because ``import-sheets`` writes whatever it is
handed straight to the TSV.

Reaches Drive only through the doorway (``get_doorway()``).

Reads cell values from local TSVs (written by import-sheets) rather than
re-fetching them from Google Sheets, then writes pink highlights back to
Sheets only where invalid cells are found. Local TSVs must exist — if any
are missing, run `python -m coding import-sheets` first. Each tab's Status
is read live from the sheet.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from gspread.utils import rowcol_to_a1

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from . import drive_door
from .drive import load_manifest
from .drive_doorway import WorksheetNotFound, get_doorway
from .locked_tabs import system_tab_titles
from .restructure_sheets import _get_keyed_row_constructions, _get_pair_row_constructions
from .make_forms import (
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
    resolve_keystone_active,
    resolve_keystone_na_criteria,
)
from .validate import ValidationIssue
from .validate_planar import validate_planar_df
from .validate_diagnostics import validate_diagnostics_df
from .schemas import (
    criteria_for,
    free_entry_kind,
    load_diagnostic_criteria,
    placeholder,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

from planars.position_cells import as_names, position_numbers  # noqa: E402
from planars.schema_values import (  # noqa: E402
    ELEMENT_ROW_COLUMNS, PAIR_ROW_SHAPES, STATUS_READY, TRAILING_COLUMNS,
)

# Row-identifying and trailing columns, read from schemas/planar.yaml.
_STRUCTURAL_COLS      = set(ELEMENT_ROW_COLUMNS)
_PAIR_STRUCTURAL_COLS = set().union(*PAIR_ROW_SHAPES.values())
_TRAILING_COLS        = TRAILING_COLUMNS
# Values every criterion accepts in addition to its own list (unknown, not
# applicable) — diagnostic_criteria.yaml's shared values. There is no default
# list for a criterion whose own values are unknown: the [y, n] default was
# removed 2026-10-12 (Phase 10); such a column is reported, not guessed.
_ALWAYS_ALLOWED = set(load_diagnostic_criteria()["always_allowed_values"])

# Each tab's criterion columns come from coding.schemas.criteria_for, applied in
# _load_param_map — the one copy of the rule that narrows, e.g., a coreference
# pair tab to its own criterion. (A coreference-only copy,
# _COREFERENCE_CONSTRUCTION_PARAMS, lived here until 2026-10-12.)

# Placeholder values (diagnostic_criteria.yaml value_placeholders): a
# criterion that accepts any position number (e.g. dependent-on-left) lists
# <position_number> among its values. Criteria that take free entry
# (biuniqueness_deviations, #254) keep a value exactly as typed (never
# lowercased -- "'ll" and "tense=past" are data), and it may be blank.
_POSITION_NUMBER_PLACEHOLDER = placeholder("position_number")


def _columns_without_values(param_cols, param_values, tab_name: str,
                            issues: List[ValidationIssue]) -> set:
    """Criterion columns on this tab with no allowed values known, reported once each.

    Their cells are not checked: there is no [y, n] default to check them
    against (removed 2026-10-12, Phase 10). A warning, not an error — it is
    usually a column the diagnostics YAML no longer lists.
    """
    unknown = {p for p in param_cols if not (param_values and param_values.get(p))}
    for p in sorted(unknown):
        issues.append(ValidationIssue(
            "warning", tab_name,
            f"column '{p}' has no allowed values in the diagnostics YAML, so its cells "
            f"were not checked — list its values there, or remove the column"))
    return unknown


_free_entry_kind = free_entry_kind


_POSITION_NAME_CACHE: Dict[str, Dict[str, str]] = {}


def _planar_position_names(lang_id: Optional[str]) -> Optional[Dict[str, str]]:
    """The language's planar as {position number: position name}, or None if
    unknown (no lang_id, no planar) -- then position-name values are not
    checked."""
    if not lang_id:
        return None
    if lang_id not in _POSITION_NAME_CACHE:
        path = CODED_DATA / lang_id / "lang_setup" / f"planar_{lang_id}.tsv"
        if not path.exists():
            return None
        df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
        _POSITION_NAME_CACHE[lang_id] = {
            num.strip(): name.strip()
            for num, name in zip(df["Position"], df["Position_Name"])}
    return _POSITION_NAME_CACHE[lang_id]


def _check_free_entry(kind: str, value: str, lang_id: Optional[str]) -> Optional[str]:
    """None if a free-entry value is acceptable, else what is wrong with it.
    Positions may be written as numbers or names (planars.position_cells)."""
    if kind != "position_names" or not value:
        return None
    by_number = _planar_position_names(lang_id)
    if by_number is None:
        return None
    _, unknown = as_names(value, {int(n): name for n, name in by_number.items()
                                  if n.isdigit()})
    if not unknown:
        return None
    return f"not a position in the planar: {', '.join(unknown)}"


def _check_position_numbers(value: str, lang_id: Optional[str]) -> Optional[str]:
    """None if a <position_number> cell's value is positions (``8|12|30``),
    each in the planar when the planar is known; else what is wrong with it."""
    numbers, problems = position_numbers(value)
    if problems:
        return problems[0]
    by_number = _planar_position_names(lang_id)
    if by_number is None:
        return None
    missing = [str(n) for n in numbers if str(n) not in by_number]
    if missing:
        return f"not a position in the planar: {', '.join(missing)}"
    return None


# ---------------------------------------------------------------------------
# Cell problems, and how serious each is (issue #309)
# ---------------------------------------------------------------------------

# ValidationIssue.kind for a problem in one cell.
BLANK, INVALID = "blank", "invalid"


def needs_fixing(issue: ValidationIssue, tab_status: str) -> bool:
    """The one rule for how serious a cell problem is.

    An invalid value on a tab its annotator has marked ready-for-review is an
    error: it is reported (a `sheet-validation` issue) and listed in the
    sheet's Status tab. On an in-progress tab it is only highlighted pink,
    since the annotator is still working there. A blank cell is never an
    error. import-sheets and validate-coding both decide through here
    (until #309 import-sheets decided for itself and the two disagreed)."""
    return issue.kind == INVALID and tab_status == STATUS_READY


def grade(issues: List[ValidationIssue], tab_status: str) -> List[ValidationIssue]:
    """``issues`` with every one that `needs_fixing` raised to an error."""
    return [dataclasses.replace(i, level="error") if needs_fixing(i, tab_status) else i
            for i in issues]


def _blank(where: str, param: str, cell: Tuple[int, int],
           message: Optional[str] = None) -> ValidationIssue:
    return ValidationIssue("warning", where, message or f"blank value in '{param}'",
                           cell=cell, kind=BLANK)


def _invalid(where: str, row_num: int, label: str, param: str, value: str,
             should: str, cell: Tuple[int, int], message: str) -> ValidationIssue:
    """An invalid cell; ``should`` says what it should be, for the line the
    annotator reads in the Status tab."""
    return ValidationIssue("warning", where, message, cell=cell, kind=INVALID,
                           fix=f"row {row_num} ({label}), {param}: '{value}' — {should}")


# ---------------------------------------------------------------------------
# The Status tab: each tab's status, and the problems listed beside it (#309)
# ---------------------------------------------------------------------------

# More lines than this in one Status cell are summarised; the pink cells show
# the rest.
_MAX_PROBLEM_LINES = 20


def read_status_tab(ss) -> Tuple[Optional[object], List[List[str]]]:
    """(the Status worksheet, its cells), or (None, []) if the sheet has none.
    ``planars.schema_values.status_map`` turns the cells into each tab's status."""
    try:
        ws = ss.worksheet(STATUS_TAB)
    except WorksheetNotFound:
        return None, []
    return ws, ws.get_all_values()


def tab_statuses(ss) -> Dict[str, str]:
    """{construction: status} from the sheet's Status tab ({} if it has none)."""
    return status_map(read_status_tab(ss)[1])


def marked_by_map(rows: List[List[str]]) -> Dict[str, str]:
    """{construction: its Marked by cell} from a Status tab's cells, for the
    rows that have one ({} for a tab without the column)."""
    header = [h.strip() for h in rows[0]] if rows else []
    if STATUS_CONSTRUCTION_COLUMN not in header or STATUS_MARKED_BY_COLUMN not in header:
        return {}
    ci, mi = header.index(STATUS_CONSTRUCTION_COLUMN), header.index(STATUS_MARKED_BY_COLUMN)
    return {_cell(r, ci): _cell(r, mi) for r in rows[1:] if _cell(r, ci) and _cell(r, mi)}


def problems_text(issues: List[ValidationIssue]) -> str:
    """What the Status tab says needs fixing on one tab: one line per error
    an annotator can fix, blank when there are none."""
    lines = [i.fix for i in issues if i.level == "error" and i.fix]
    if len(lines) > _MAX_PROBLEM_LINES:
        rest = len(lines) - _MAX_PROBLEM_LINES
        lines = lines[:_MAX_PROBLEM_LINES] + [f"…and {rest} more (the pink cells on the tab)"]
    return "\n".join(lines)


def looks_finished(issues: List[ValidationIssue], tab_status: str, lang_id: str,
                   class_name: str, construction: str) -> bool:
    """A finished tab not yet marked: still in-progress, at least one row,
    and nothing blank, invalid or misshapen. Such a tab counts as
    ready-for-review (Jeff, 2026-10-26): annotators forget to mark tabs, and
    a tab built from this one waits until it is marked, so
    `revalidate_sheets` marks it and the needs-fixing issue tells the
    annotator."""
    if tab_status == STATUS_READY or issues:
        return False
    return len(_read_tsv_rows(lang_id, class_name, construction)) > 1


def marked_by_text(by: str, when: Optional[datetime.date] = None) -> str:
    """The Marked by cell: who (a planar.yaml status_tab.marked_by value) and when."""
    return f"{by}, {(when or datetime.date.today()).isoformat()}"


def _cell(row: List[str], i: Optional[int]) -> str:
    return row[i].strip() if i is not None and i < len(row) else ""


def write_status(ws, rows: List[List[str]], construction: str, status: str,
                 reason: str, by: str) -> Optional[str]:
    """Set ``construction``'s Status in the Status tab (``ws``, whose cells
    are ``rows``), through the Drive door as replacing the annotator's value,
    and its Marked by cell: ``by`` (a planar.yaml status_tab.marked_by value)
    and today's date when ready-for-review, blank otherwise. Returns the
    previous status ('' if blank), or None if the tab has no row for
    ``construction``. Writes only cells that change; ``rows`` is updated to
    match."""
    header = [h.strip() for h in rows[0]] if rows else []
    if STATUS_CONSTRUCTION_COLUMN not in header or STATUS_STATUS_COLUMN not in header:
        return None
    ci, si = header.index(STATUS_CONSTRUCTION_COLUMN), header.index(STATUS_STATUS_COLUMN)
    mi = (header.index(STATUS_MARKED_BY_COLUMN) if STATUS_MARKED_BY_COLUMN in header
          else None)
    for r, row in enumerate(rows[1:], start=2):
        if _cell(row, ci) != construction:
            continue
        current = _cell(row, si)
        if current != status:
            with drive_door.replacing(ws, reason):
                ws.update_cell(r, si + 1, status)
        marked = marked_by_text(by) if status == STATUS_READY else ""
        # An unchanged ready tab keeps its date unless someone else marked it.
        if (mi is not None and _cell(row, mi) != marked
                and (current != status or not _cell(row, mi).startswith(f"{by},"))):
            ws.update_cell(r, mi + 1, marked)
        row.extend([""] * (max(si, mi or 0) + 1 - len(row)))
        row[si] = status
        if mi is not None:
            row[mi] = marked
        return current
    return None


def record_marked_by(ws, rows: List[List[str]]) -> None:
    """Keep the Status tab's Marked by column true to its Status column: a
    ready-for-review tab with no Marked by was marked by its annotator (the
    tooling writes the cell whenever it marks one), so it gets
    MARKED_BY_ANNOTATOR and today's date; a tab no longer ready has its
    Marked by cleared, so a later hand mark is read as the annotator's.
    ``rows`` is updated to match. Does nothing on a tab without the column."""
    header = [h.strip() for h in rows[0]] if rows else []
    if not {STATUS_CONSTRUCTION_COLUMN, STATUS_STATUS_COLUMN,
            STATUS_MARKED_BY_COLUMN} <= set(header):
        return
    ci, si = header.index(STATUS_CONSTRUCTION_COLUMN), header.index(STATUS_STATUS_COLUMN)
    mi = header.index(STATUS_MARKED_BY_COLUMN)
    for r, row in enumerate(rows[1:], start=2):
        if not _cell(row, ci):
            continue
        ready, marked = _cell(row, si) == STATUS_READY, _cell(row, mi)
        want = (marked_by_text(MARKED_BY_ANNOTATOR) if ready and not marked
                else "" if not ready and marked else None)
        if want is not None:
            ws.update_cell(r, mi + 1, want)
            row.extend([""] * (mi + 1 - len(row)))
            row[mi] = want


def write_problems(ws, rows: List[List[str]], problems: Dict[str, str]) -> Optional[str]:
    """Rewrite the Status tab's problems column for each construction in
    ``problems``, only where it differs. A construction not in ``problems``
    (its tab was not checked) is left alone. Returns a note if the tab has no
    such column yet, else None."""
    header = [h.strip() for h in rows[0]] if rows else []
    if STATUS_PROBLEMS_COLUMN not in header or STATUS_CONSTRUCTION_COLUMN not in header:
        return (f"its {STATUS_TAB} tab has no '{STATUS_PROBLEMS_COLUMN}' column yet, so "
                f"nothing was listed for the annotator — python -m coding update-sheets "
                f"--apply adds it")
    ci = header.index(STATUS_CONSTRUCTION_COLUMN)
    pi = header.index(STATUS_PROBLEMS_COLUMN)
    for r, row in enumerate(rows[1:], start=2):
        name = row[ci].strip() if ci < len(row) else ""
        current = row[pi] if pi < len(row) else ""
        if name in problems and current != problems[name]:
            ws.update([[problems[name]]], rowcol_to_a1(r, pi + 1))
    return None


def _one_of(allowed) -> str:
    values = sorted(v for v in allowed if v != _POSITION_NUMBER_PLACEHOLDER)
    if _POSITION_NUMBER_PLACEHOLDER in allowed:
        values.append("position numbers (e.g. 8|12)")
    return "should be one of: " + ", ".join(values)


def _value_problem(val: str, allowed, accepts_pos_num: bool,
                   lang_id: Optional[str]) -> Optional[str]:
    """What is wrong with a value not in ``allowed``, or None if it is
    acceptable positions. A value with a digit in a <position_number>
    column is read as positions, so the annotator is told what is wrong
    with them (a comma, a number not in the planar); anything else is told
    the allowed values."""
    if accepts_pos_num and any(c.isdigit() for c in val):
        return _check_position_numbers(val, lang_id)
    return _one_of(allowed)

_PINK  = {"red": 1.0, "green": 0.8, "blue": 0.8}
_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}

from planars.schema_values import KEYSTONE_NAME as _KEYSTONE_NAME  # noqa: E402
from planars.schema_values import (  # noqa: E402
    MARKED_BY_ANNOTATOR, MARKED_BY_CHECK, STATUS_CONSTRUCTION_COLUMN, STATUS_IN_PROGRESS,
    STATUS_MARKED_BY_COLUMN, STATUS_PROBLEMS_COLUMN, STATUS_READY,
    STATUS_STATUS_COLUMN, STATUS_TAB, status_map,
)

# ---------------------------------------------------------------------------
# Cell highlighting
# ---------------------------------------------------------------------------

def highlight_cells(ws, bad_cells: List[Tuple[int, int]]) -> None:
    """Set pink background on invalid cells. bad_cells are (row_idx, col_idx) 0-based."""
    if not bad_cells:
        return
    requests = [
        {
            "updateCells": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": r,
                    "endRowIndex": r + 1,
                    "startColumnIndex": c,
                    "endColumnIndex": c + 1,
                },
                "rows": [{"values": [{"userEnteredFormat": {"backgroundColor": _PINK}}]}],
                "fields": "userEnteredFormat.backgroundColor",
            }
        }
        for r, c in bad_cells
    ]
    # Painted on a dry run too (operations.yaml always_on_writes).
    with drive_door.always_on("highlighting"):
        ws.spreadsheet.batch_update({"requests": requests})


def clear_highlights(ws) -> None:
    """Clear all pink highlighting from a worksheet by resetting backgrounds to white."""
    body = {"requests": [{
        "repeatCell": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 0,
                "endRowIndex": ws.row_count,
                "startColumnIndex": 0,
                "endColumnIndex": ws.col_count,
            },
            "cell": {"userEnteredFormat": {"backgroundColor": _WHITE}},
            "fields": "userEnteredFormat.backgroundColor",
        }
    }]}
    with drive_door.always_on("highlighting"):
        ws.spreadsheet.batch_update(body)


# ---------------------------------------------------------------------------
# Annotation sheet validation
# ---------------------------------------------------------------------------

def _plain_records(header: List[str], data_rows: List[List[str]]) -> List[Dict]:
    """Row dicts with every value exactly as the sheet holds it.

    Used when the sheet's shape is not the one expected, so no column can be
    read as a criterion. The values still have to come back: `import-sheets`
    writes whatever it is handed straight to the TSV, so returning nothing here
    would empty a live annotation file.
    """
    records = []
    for row in data_rows:
        row = list(row) + [""] * (len(header) - len(row))
        records.append({name: row[i] for i, name in enumerate(header)})
    return records


def _wrong_shape(tab_name: str, header: List[str], expected: str,
                 class_name: Optional[str], lang_id: Optional[str]) -> ValidationIssue:
    """One error saying the sheet is not the shape the schema says it is.

    Said once, and then nothing else is checked. Before this, a sheet whose
    rows were not the expected shape had every cell checked anyway against a
    column map built for the other shape — so `stan1293`'s phrasal_accent
    sheet reported 2 real errors under 427 complaints that element names and
    position numbers are not `y`/`n` (issue #275).
    """
    lang = f"--lang {lang_id} " if lang_id else "--lang LANG "
    target = f"{class_name}:{tab_name}" if class_name else "CLASS:CONSTRUCTION"
    rebuild = f"python -m coding generate-sheets {lang}--regen-construction {target}"
    return ValidationIssue(
        "error", tab_name,
        f"the sheet's rows are not the shape this construction is supposed to "
        f"have. Expected {expected}; the sheet's columns are {header}. "
        f"Nothing else was checked, because every value would have been read "
        f"from the wrong column.\n"
        f"    → Either rebuild the sheet:  {rebuild}\n"
        f"      or correct row_type for this construction in "
        f"schemas/diagnostic_classes.yaml, if the sheet is the one that is right."
    )


def validate_annotation_rows(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    keystone_active: bool = False,
    keystone_na_criteria: List[str] = None,
    class_name: Optional[str] = None,
    lang_id: Optional[str] = None,
) -> Tuple[List[Dict], List[ValidationIssue]]:
    """Validate annotation sheet rows.

    Returns (records, issues). records are dicts ready to write as TSV rows.
    """
    issues: List[ValidationIssue] = []

    if not rows:
        return [], [ValidationIssue("error", tab_name, "sheet is empty")]

    header    = rows[0]
    data_rows = rows[1:]

    if not set(header) & _STRUCTURAL_COLS:
        return (_plain_records(header, data_rows),
                [_wrong_shape(tab_name, header,
                              f"element rows ({', '.join(ELEMENT_ROW_COLUMNS)})",
                              class_name, lang_id)])

    for col in ELEMENT_ROW_COLUMNS:
        if col not in header:
            issues.append(ValidationIssue("error", tab_name, f"missing structural column '{col}'"))

    actual_params = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
    if actual_params != expected_params:
        issues.append(ValidationIssue(
            "warning", tab_name,
            f"criterion columns differ from the diagnostics file — "
            f"expected {expected_params}, got {actual_params}"
        ))

    col_index  = {name: i for i, name in enumerate(header)}
    param_cols = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]

    unknown = _columns_without_values(param_cols, param_values, tab_name, issues)

    records = []
    for row_num, row in enumerate(data_rows, start=2):
        while len(row) < len(header):
            row.append("")

        record   = {col: row[col_index[col]] for col in header if col in col_index}
        pos_name = record.get("Position_Name", "").strip()
        is_keystone = pos_name.lower() == _KEYSTONE_NAME
        label = record.get('Element', '?')
        where = f"{tab_name} row {row_num} '{label}'"

        for param in param_cols:
            cell = (row_num - 1, col_index[param])
            if param in unknown:
                record[param] = record.get(param, "").strip().lower()
                continue
            free_kind = _free_entry_kind((param_values or {}).get(param))
            if free_kind:
                # Free entry: kept as typed, may be blank; position names checked.
                raw = record.get(param, "").strip()
                record[param] = raw
                problem = _check_free_entry(free_kind, raw, lang_id)
                if problem:
                    issues.append(_invalid(
                        where, row_num, label, param, raw, problem, cell,
                        f"unexpected value '{raw}' in '{param}' ({problem})"))
                continue

            val = record.get(param, "").strip().lower()
            record[param] = val

            allowed = {v.lower() for v in param_values[param]} | _ALWAYS_ALLOWED
            accepts_pos_num = _POSITION_NUMBER_PLACEHOLDER in allowed

            if is_keystone:
                _na_criteria = keystone_na_criteria or []
                if keystone_active and param not in _na_criteria:
                    # Keystone participates in this analysis — treat like any row.
                    if val == "":
                        issues.append(_blank(
                            where, param, cell,
                            f"blank value in '{param}' (keystone is active for this construction)"))
                    elif val == "na":
                        issues.append(_invalid(
                            where, row_num, label, param, val,
                            "should be a real answer, not 'na' (the keystone takes part "
                            "in this construction)", cell,
                            f"'na' in '{param}' but keystone is active — expected a real annotation value"))
                    elif val not in allowed:
                        problem = _value_problem(val, allowed, accepts_pos_num, lang_id)
                        if problem:
                            issues.append(_invalid(
                                where, row_num, label, param, val, problem, cell,
                                f"unexpected value '{val}' in '{param}' ({problem})"))
                else:
                    # Keystone does not participate (or criterion is self-referential
                    # on the keystone) — should always be 'na'.
                    if val == "":
                        record[param] = "na"
                    elif val != "na":
                        issues.append(_invalid(
                            where, row_num, label, param, val, "should be 'na'", cell,
                            f"unexpected value '{val}' in '{param}' for keystone row (expected 'na')"))
            else:
                if val == "":
                    issues.append(_blank(where, param, cell))
                elif val not in allowed:
                    problem = _value_problem(val, allowed, accepts_pos_num, lang_id)
                    if problem:
                        issues.append(_invalid(
                            where, row_num, label, param, val, problem, cell,
                            f"unexpected value '{val}' in '{param}' ({problem})"))

        records.append(record)

    return records, issues


def annotation_status(
    rows: List[List[str]],
    expected_params: List[str],
    param_values: Dict[str, List[str]] = None,
    keystone_active: bool = False,
    keystone_na_criteria: List[str] = None,
) -> dict:
    """Return completeness/validity counts for one annotation sheet tab.

    Returns {'total': int, 'filled': int, 'blank': int, 'invalid': int}.
    Keystone rows (v:verbstem) are excluded from all counts unless
    keystone_active is True, in which case they count for every param except
    those in keystone_na_criteria — this must mirror validate_annotation_rows'
    per-cell logic exactly (same rows/params it can raise a "blank value"
    issue for), otherwise total and blank drift apart and filled can go
    negative. That drift was invisible for every previously-onboarded
    keystone-active class (metrical) because their keystone rows were already
    fully annotated by the time this ran; it first surfaced with
    phrasal_accent, whose keystone row started out blank.
    """
    if not rows or len(rows) < 2:
        return {"total": 0, "filled": 0, "blank": 0, "invalid": 0}

    header = rows[0]
    # Free-entry criteria (members, co_exponents: #254) may legitimately stay
    # blank, so they never count toward completeness.
    param_cols = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS
                  and not _free_entry_kind((param_values or {}).get(c))]
    n_params = len(param_cols)
    pos_idx = header.index("Position_Name") if "Position_Name" in header else -1
    na_criteria = set(keystone_na_criteria or [])
    total = 0
    for row in rows[1:]:
        is_keystone = pos_idx >= 0 and len(row) > pos_idx and row[pos_idx].lower() == _KEYSTONE_NAME
        if is_keystone:
            if keystone_active:
                total += sum(1 for p in param_cols if p not in na_criteria)
        else:
            total += n_params

    _, issues = validate_annotation_rows(
        rows, expected_params, "", param_values,
        keystone_active=keystone_active,
        keystone_na_criteria=keystone_na_criteria,
    )
    blank = sum(1 for i in issues if "blank value" in i.message)
    invalid = sum(1 for i in issues if "unexpected value" in i.message)
    return {"total": total, "filled": total - blank, "blank": blank, "invalid": invalid}


def pair_annotation_status(
    rows: List[List[str]],
    expected_params: List[str],
    param_values: Dict[str, List[str]] = None,
) -> dict:
    """Return completeness/validity counts for one pair-row annotation sheet tab.

    Same shape as annotation_status(), for pair-row sheets (nonpermutability's
    `general`, coreference's `reflexive_coreference`/`pronoun_coreference`/
    `np_coreference`) instead of element rows. There is no keystone row to
    exclude here -- pair rows are generated from element pairs, not from
    positions, so every data row counts in full. Reads whatever rows the live
    sheet has at call time, so a caller that re-reads the sheet after pairs
    are added, removed, or regenerated gets a count that reflects the new
    pairs automatically -- nothing here caches a prior row count.
    Returns {'total': int, 'filled': int, 'blank': int, 'invalid': int}.
    """
    if not rows or len(rows) < 2:
        return {"total": 0, "filled": 0, "blank": 0, "invalid": 0}

    header = rows[0]
    param_cols = [c for c in header if c not in _PAIR_STRUCTURAL_COLS and c not in _TRAILING_COLS]
    total = len(param_cols) * len(rows[1:])

    _, issues = validate_pair_rows(rows, expected_params, "", param_values)
    blank = sum(1 for i in issues if "blank value" in i.message)
    invalid = sum(1 for i in issues if "unexpected value" in i.message)
    return {"total": total, "filled": total - blank, "blank": blank, "invalid": invalid}


# ---------------------------------------------------------------------------
# TSV reader
# ---------------------------------------------------------------------------

def _read_tsv_rows(lang_id: str, class_name: str, construction: str) -> List[List[str]]:
    """Read a local annotation TSV and return rows as List[List[str]].

    Raises FileNotFoundError with an actionable message if the TSV does not
    exist (i.e. import-sheets has not been run for this construction).
    """
    tsv_path = CODED_DATA / lang_id / class_name / f"{construction}.tsv"
    if not tsv_path.exists():
        raise FileNotFoundError(
            f"No local TSV for {lang_id}/{class_name}/{construction}. "
            "Run `python -m coding import-sheets` first."
        )
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    return [list(df.columns)] + df.values.tolist()


def _check_header_sync(
    ws,
    lang_id: str,
    class_name: str,
    construction: str,
) -> Optional[ValidationIssue]:
    """Return a warning if the live Sheet header differs from the local TSV header.

    Reads the TSV header raw (without pandas column deduplication) so that a
    duplicate column in the Sheet shows up as a mismatch against the clean TSV,
    catching sheet corruption before it propagates into the committed data.
    Returns None if the TSV does not exist (already reported as missing elsewhere).
    """
    tsv_path = CODED_DATA / lang_id / class_name / f"{construction}.tsv"
    if not tsv_path.exists():
        return None
    with tsv_path.open() as f:
        tsv_header = f.readline().rstrip("\n").split("\t")
    sheet_header = ws.row_values(1)
    # gspread may pad with trailing empty strings for empty cells; trim to TSV width.
    sheet_header = sheet_header[:len(tsv_header)]
    if sheet_header != tsv_header:
        return ValidationIssue(
            "warning", construction,
            f"live Sheet header differs from local TSV — "
            f"Sheet: {sheet_header}, TSV: {tsv_header}",
        )
    return None


def revalidate_sheet(
    ws,
    lang_id: str,
    class_name: str,
    construction: str,
    expected_params: List[str],
    param_values: Dict[str, List[str]] = None,
    keystone_active: bool = False,
    keystone_na_criteria: List[str] = None,
) -> List[ValidationIssue]:
    """Read a local TSV, validate it, update cell highlighting in the Sheet, return issues.

    Reads cell values from the local TSV produced by import-sheets rather than
    fetching them from Google Sheets, then writes pink highlights back only
    where invalid cells are found.

    Raises FileNotFoundError if the local TSV does not exist.
    """
    rows = _read_tsv_rows(lang_id, class_name, construction)
    _, issues = validate_annotation_rows(
        rows, expected_params, construction, param_values,
        keystone_active=keystone_active,
        keystone_na_criteria=keystone_na_criteria,
        class_name=class_name, lang_id=lang_id,
    )
    bad_cells = [issue.cell for issue in issues if issue.cell is not None]
    clear_highlights(ws)
    highlight_cells(ws, bad_cells)
    return issues


# ---------------------------------------------------------------------------
# Pair-row sheet validation (nonpermutability)
# ---------------------------------------------------------------------------

def validate_pair_rows(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    class_name: Optional[str] = None,
    lang_id: Optional[str] = None,
) -> Tuple[List[Dict], List[ValidationIssue]]:
    """Validate pair-row annotation sheets (nonpermutability, coreference).

    Structural columns depend on the sheet type — nonpermutability uses
    Element_A/Element_B; coreference uses Element_A/Position_A/Position_B/Direction.
    All required structural cols are checked via _PAIR_STRUCTURAL_COLS intersection.
    Returns (records, issues).
    """
    issues: List[ValidationIssue] = []

    if not rows:
        return [], [ValidationIssue("error", tab_name, "sheet is empty")]

    header    = rows[0]
    data_rows = rows[1:]

    if not set(header) & _PAIR_STRUCTURAL_COLS:
        return (_plain_records(header, data_rows),
                [_wrong_shape(tab_name, header,
                              "pair rows (Element_A, Element_B)", class_name, lang_id)])

    actual_params = [c for c in header if c not in _PAIR_STRUCTURAL_COLS and c not in _TRAILING_COLS]
    if actual_params != expected_params:
        issues.append(ValidationIssue(
            "warning", tab_name,
            f"criterion columns differ from the diagnostics file — "
            f"expected {expected_params}, got {actual_params}"
        ))

    col_index  = {name: i for i, name in enumerate(header)}
    param_cols = [c for c in header if c not in _PAIR_STRUCTURAL_COLS and c not in _TRAILING_COLS]
    unknown = _columns_without_values(param_cols, param_values, tab_name, issues)

    records = []
    for row_num, row in enumerate(data_rows, start=2):
        while len(row) < len(header):
            row.append("")

        record = {col: row[col_index[col]] for col in header if col in col_index}
        if "Position_B" in col_index:
            label = f"{record.get('Element_A', '?')} → pos {record.get('Position_B', '?')}"
        else:
            label = f"{record.get('Element_A', '?')} × {record.get('Element_B', '?')}"

        for param in param_cols:
            val = record.get(param, "").strip().lower()
            record[param] = val
            if param in unknown:
                continue

            allowed = {v.lower() for v in param_values[param]} | _ALWAYS_ALLOWED
            where, cell = f"{tab_name} row {row_num} '{label}'", (row_num - 1, col_index[param])

            if val == "":
                issues.append(_blank(where, param, cell))
            elif val not in allowed:
                issues.append(_invalid(
                    where, row_num, label, param, val, _one_of(allowed), cell,
                    f"unexpected value '{val}' in '{param}' (allowed: {sorted(allowed)})"))

        records.append(record)

    return records, issues


def revalidate_pair_sheet(
    ws,
    lang_id: str,
    class_name: str,
    construction: str,
    expected_params: List[str],
    param_values: Dict[str, List[str]] = None,
) -> List[ValidationIssue]:
    """Read a local pair-row TSV, validate it, update cell highlighting, return issues.

    Like revalidate_sheet() but for pair-row sheets (nonpermutability: Element_A/
    Element_B; coreference: Element_A/Position_A/Position_B/Direction; no keystone).

    Raises FileNotFoundError if the local TSV does not exist.
    """
    rows = _read_tsv_rows(lang_id, class_name, construction)
    _, issues = validate_pair_rows(rows, expected_params, construction, param_values,
                                   class_name=class_name, lang_id=lang_id)
    bad_cells = [issue.cell for issue in issues if issue.cell is not None]
    clear_highlights(ws)
    highlight_cells(ws, bad_cells)
    return issues


# ---------------------------------------------------------------------------
# Keyed-row sheet validation (row_type: keyed_rows -- biuniqueness_deviations)
# ---------------------------------------------------------------------------

def validate_keyed_rows(
    rows: List[List[str]],
    keyed_columns: List[str],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
    blank_ok_when: List[Dict[str, str]] = None,
    class_name: Optional[str] = None,
    lang_id: Optional[str] = None,
) -> Tuple[List[Dict], List[ValidationIssue]]:
    """Validate a keyed-row tab (morphemes, morphs). Returns (records, issues).

    The generator-written keyed_columns come first and are never checked as
    criteria. Fixed-value criteria are lowercased and checked like everywhere
    else; free-entry criteria (<free_text>, <position_names>) are kept as typed.
    A row matching one of blank_ok_when (e.g. occurs_here=n) may leave its
    other criteria blank without a warning.
    """
    issues: List[ValidationIssue] = []
    if not rows:
        return [], [ValidationIssue("error", tab_name, "sheet is empty")]
    header, data_rows = rows[0], rows[1:]

    if header[:len(keyed_columns)] != list(keyed_columns):
        return (_plain_records(header, data_rows),
                [_wrong_shape(tab_name, header, f"keyed rows ({', '.join(keyed_columns)})",
                              class_name, lang_id)])

    param_cols = [c for c in header[len(keyed_columns):] if c not in _TRAILING_COLS]
    if param_cols != expected_params:
        issues.append(ValidationIssue(
            "warning", tab_name,
            f"criterion columns differ from the diagnostics file — "
            f"expected {expected_params}, got {param_cols}"))

    col_index = {name: i for i, name in enumerate(header)}
    rules = [{k: str(v).lower() for k, v in r.items()} for r in (blank_ok_when or [])]
    unknown = _columns_without_values(param_cols, param_values, tab_name, issues)
    records = []
    for row_num, row in enumerate(data_rows, start=2):
        row = list(row) + [""] * (len(header) - len(row))
        record = {col: row[col_index[col]] for col in header}
        label = " / ".join(record.get(k, "") for k in keyed_columns[:3])
        lowered = {p: record.get(p, "").strip().lower() for p in param_cols}
        blank_ok = any(all(lowered.get(k) == v for k, v in r.items()) for r in rules)

        for param in param_cols:
            if param in unknown:
                record[param] = lowered[param]
                continue
            values = (param_values or {}).get(param)
            free_kind = _free_entry_kind(values)
            where, cell = f"{tab_name} row {row_num} '{label}'", (row_num - 1, col_index[param])
            if free_kind:
                raw = record.get(param, "").strip()
                record[param] = raw
                problem = _check_free_entry(free_kind, raw, lang_id)
                if problem:
                    issues.append(_invalid(
                        where, row_num, label, param, raw, problem, cell,
                        f"unexpected value '{raw}' in '{param}' ({problem})"))
                continue
            val = lowered[param]
            record[param] = val
            allowed = {v.lower() for v in values} | _ALWAYS_ALLOWED
            if val == "":
                if not blank_ok:
                    issues.append(_blank(where, param, cell))
            elif val not in allowed:
                issues.append(_invalid(
                    where, row_num, label, param, val, _one_of(allowed), cell,
                    f"unexpected value '{val}' in '{param}' (allowed: {sorted(allowed)})"))
        records.append(record)
    return records, issues


def keyed_annotation_status(
    rows: List[List[str]],
    keyed_columns: List[str],
    expected_params: List[str],
    param_values: Dict[str, List[str]] = None,
    blank_ok_when: List[Dict[str, str]] = None,
) -> dict:
    """Completeness/validity counts for a keyed-row tab, same shape as
    annotation_status(). Counts only fixed-value criteria, and none on a row
    whose answers make the rest blank-ok (blank_ok_when) beyond the ones it set."""
    if not rows or len(rows) < 2:
        return {"total": 0, "filled": 0, "blank": 0, "invalid": 0}
    header = rows[0]
    counted = [c for c in header[len(keyed_columns):]
               if c not in _TRAILING_COLS and not _free_entry_kind((param_values or {}).get(c))]
    _, issues = validate_keyed_rows(rows, keyed_columns, expected_params, "", param_values,
                                    blank_ok_when)
    blank = sum(1 for i in issues if "blank value" in i.message)
    invalid = sum(1 for i in issues if "unexpected value" in i.message)
    # A blank-ok row counts only the cells actually filled in.
    rules = [{k: str(v).lower() for k, v in r.items()} for r in (blank_ok_when or [])]
    total = 0
    for row in rows[1:]:
        rec = dict(zip(header, list(row) + [""] * (len(header) - len(row))))
        low = {c: str(rec.get(c, "")).strip().lower() for c in counted}
        if any(all(low.get(k) == v for k, v in r.items()) for r in rules):
            total += sum(1 for c in counted if low[c])
        else:
            total += len(counted)
    return {"total": total, "filled": total - blank, "blank": blank, "invalid": invalid}


def revalidate_keyed_sheet(
    ws, lang_id: str, class_name: str, construction: str,
    keyed: Dict, expected_params: List[str], param_values: Dict[str, List[str]] = None,
) -> List[ValidationIssue]:
    """Like revalidate_sheet() for a keyed-row tab: validate the local TSV,
    repaint pink highlights, return issues."""
    rows = _read_tsv_rows(lang_id, class_name, construction)
    _, issues = validate_keyed_rows(rows, keyed["columns"], expected_params, construction,
                                    param_values, keyed.get("blank_ok_when"),
                                    class_name=class_name, lang_id=lang_id)
    bad_cells = [issue.cell for issue in issues if issue.cell is not None]
    clear_highlights(ws)
    highlight_cells(ws, bad_cells)
    return issues


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _load_param_map(lang_id: str) -> Dict[str, Dict[str, dict]]:
    """Return {class_name: {construction: {params, values}}} for a language."""
    planar_files = sorted((CODED_DATA / lang_id / "lang_setup").glob("planar_*.tsv"))
    if not planar_files:
        return {}
    data_dir = planar_files[0].parent
    inferred = _infer_language_id_from_planar_filename(planar_files[0].name)
    param_map: Dict[str, Dict[str, dict]] = {}
    for class_name, construction, param_names, param_values in _read_diagnostics_for_language(inferred, data_dir):
        # Each tab's own criteria (one schema `criterion:` where declared) —
        # the same rule generate-sheets builds the tab with.
        names, values = criteria_for(class_name, construction, param_names, param_values, inferred)
        param_map.setdefault(class_name, {})[construction] = {"params": names, "values": values}
    return param_map


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------

def revalidate_sheets(
    lang_ids: list[str] | None = None,
    verbose: bool = False,
    notices: Optional[Dict[str, Optional[list]]] = None,
) -> int:
    """Revalidate annotation sheets for the given languages (all if None).

    Returns the number of errors found. Updates pink highlighting and each
    Status tab's problems column in Sheets as a side effect. Called by
    import-sheets and restructure-sheets after --apply, to refresh both.

    ``notices``, if given, is filled with {lang_id: [SheetProblems, ...]}
    for `annotator_notices.notify` — or None for a language not checked
    completely (a sheet that couldn't be opened, a tab with no local TSV),
    whose notice must not be judged from part of its sheets.
    """
    from .annotator_notices import SheetProblems
    doorway = get_doorway()
    manifest = load_manifest(doorway)
    if not manifest:
        raise SystemExit("No manifest found. Run python -m coding generate-sheets --apply first.")

    total_blocking = 0
    total_sheets = 0
    total_missing = 0

    # Schema-driven, not hardcoded per class name -- a pair-row construction
    # (Element_A/Element_B rows instead of the standard Element/Position_Name/
    # Position_Number structure) is whatever diagnostic_classes.yaml marks
    # row_type: pair_rows. Before this, the check below hardcoded just
    # "nonpermutability" and "coreference", so phrasal_accent/general (added
    # for issue #237) fell through to the standard-structure validator and
    # failed with spurious "missing structural column" errors even though its
    # pair-row structure is correct and already registered in the schema.
    pair_row_constructions = _get_pair_row_constructions()
    keyed_row_constructions = _get_keyed_row_constructions()

    for lang_id, lang_data in sorted(manifest.items()):
        if lang_ids and lang_id not in lang_ids:
            continue

        param_map = _load_param_map(lang_id)
        if not param_map:
            print(f"\n[{lang_id}] No planar file found — skipping")
            continue

        print(f"\n{lang_id}")

        # Validate planar structure and diagnostics_{lang_id}.tsv.
        planar_files = sorted((CODED_DATA / lang_id / "lang_setup").glob("planar_*.tsv"))
        if planar_files:
            planar_df = pd.read_csv(planar_files[0], sep="\t")
            planar_issues = validate_planar_df(planar_df)
            if planar_issues:
                print(f"  Planar validation ({len(planar_issues)} issue(s)):")
                for issue in planar_issues:
                    print(f"    {issue}")

            diag_path = planar_files[0].parent / f"diagnostics_{lang_id}.tsv"
            if diag_path.exists():
                diag_df = pd.read_csv(diag_path, sep="\t")
                diag_issues = validate_diagnostics_df(diag_df, lang_id)
                if diag_issues:
                    print(f"  Diagnostics validation ({len(diag_issues)} issue(s)):")
                    for issue in diag_issues:
                        print(f"    {issue}")

        lang_notices: Optional[list] = []
        for class_name, sheet_info in sorted(lang_data.get("sheets", {}).items()):
            sid = sheet_info.get("spreadsheet_id") or sheet_info.get("id")
            if not sid:
                continue
            try:
                ss = doorway.open_spreadsheet(sid)
            except Exception as e:
                print(f"  [{class_name}] could not open spreadsheet: {e}")
                lang_notices = None
                continue

            status_ws, status_rows = read_status_tab(ss)
            if status_ws is not None:
                record_marked_by(status_ws, status_rows)
            statuses = status_map(status_rows)
            problems: Dict[str, str] = {}
            notice_lines: List[str] = []
            finished: List[str] = []
            system_tabs = set(system_tab_titles())
            for ws in ss.worksheets():
                construction = ws.title
                if construction in system_tabs:
                    continue
                info = param_map.get(class_name, {}).get(construction, {})
                try:
                    is_pair_sheet = construction in pair_row_constructions.get(class_name, set())
                    keyed = keyed_row_constructions.get(class_name, {}).get(construction)
                    if keyed:
                        issues = revalidate_keyed_sheet(
                            ws, lang_id, class_name, construction, keyed,
                            info.get("params", []), info.get("values", {}),
                        )
                    elif is_pair_sheet:
                        issues = revalidate_pair_sheet(
                            ws,
                            lang_id,
                            class_name,
                            construction,
                            info.get("params", []),
                            info.get("values", {}),
                        )
                    else:
                        ka = resolve_keystone_active(lang_id, class_name, construction,
                                                    data_dir=CODED_DATA / lang_id / "lang_setup")
                        if ka is None:
                            print(f"  [{class_name}/{construction}] WARNING: keystone_active unresolved — treating as False")
                            ka = False
                        kna = resolve_keystone_na_criteria(class_name)
                        issues = revalidate_sheet(
                            ws,
                            lang_id,
                            class_name,
                            construction,
                            info.get("params", []),
                            info.get("values", {}),
                            keystone_active=ka,
                            keystone_na_criteria=kna,
                        )
                    header_issue = _check_header_sync(ws, lang_id, class_name, construction)
                    if header_issue:
                        issues = [header_issue] + issues
                except FileNotFoundError as e:
                    print(f"  [{class_name}/{construction}] ERROR: {e}")
                    total_missing += 1
                    lang_notices = None
                    continue
                total_sheets += 1
                tab_status = statuses.get(construction, STATUS_IN_PROGRESS)
                issues = grade(issues, tab_status)
                problems[construction] = problems_text(issues)
                if (status_ws is not None
                        and looks_finished(issues, tab_status, lang_id, class_name, construction)
                        and write_status(status_ws, status_rows, construction, STATUS_READY,
                                         "every cell answered with no errors",
                                         MARKED_BY_CHECK) is not None):
                    finished.append(construction)
                notice_lines += [f"{construction}: {i.fix}" for i in issues
                                 if i.level == "error" and i.fix]

                # Separate reportable issues from blank-cell completeness noise.
                # Blank cells are expected during annotation and highlighted pink
                # in the Sheet for annotators, but are not listed in the report.
                # Use --verbose to see them individually. Only errors (an
                # invalid value on a ready-for-review tab, a tab of the wrong
                # shape) count toward the exit code; see needs_fixing().
                shown = [i for i in issues if i.kind != BLANK]
                blank_count = len(issues) - len(shown)
                total_blocking += sum(1 for i in shown if i.level == "error")

                if shown:
                    print(f"  [{class_name}/{construction}] {len(shown)} issue(s):")
                    for issue in shown:
                        print(f"    {issue}")
                    if blank_count and not verbose:
                        print(f"    ({blank_count} blank cell(s) — annotation in progress; use --verbose to list)")
                elif blank_count:
                    print(f"  [{class_name}/{construction}] {blank_count} blank cell(s) — annotation in progress")
                else:
                    print(f"  [{class_name}/{construction}] no issues")

                if verbose and blank_count:
                    for issue in issues:
                        if issue.kind == BLANK:
                            print(f"    {issue}")

            if status_ws is None:
                print(f"  [{class_name}] no {STATUS_TAB} tab, so nothing was listed for the "
                      f"annotator — python -m coding update-sheets --apply adds it")
            else:
                note = write_problems(status_ws, status_rows, problems)
                if note:
                    print(f"  [{class_name}] {note}")
            if finished:
                print(f"  [{class_name}] every cell answered with no errors, so marked "
                      f"{STATUS_READY}: {', '.join(finished)}")
            if lang_notices is not None and (notice_lines or finished):
                lang_notices.append(SheetProblems(class_name, sid, ss.url, tuple(notice_lines),
                                                  tuple(finished)))

        if notices is not None:
            notices[lang_id] = lang_notices

    print(f"\n{'─' * 50}")
    print(f"Validated {total_sheets} sheet(s).  Errors: {total_blocking}")
    if total_missing:
        print(f"{total_missing} construction(s) skipped — no local TSV. Run `python -m coding import-sheets` first.")
    if total_blocking:
        print("Cell highlighting and each sheet's Status tab updated in Google Sheets.")
    else:
        print("No errors. (Pink highlighting for blank cells, and for invalid values on "
              "in-progress tabs, preserved.)")
    return total_blocking


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding validate-coding`."""
    ap = argparse.ArgumentParser(
        description="Re-validate annotation sheets and update cell highlighting."
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict to this language",
    )
    ap.add_argument(
        "--verbose", action="store_true",
        help="print each blank-cell issue individually",
    )
    ap.add_argument(
        "--notify", action="store_true",
        help="tell each language's annotator about values to fix on ready-for-review "
             "tabs (the needs-fixing issue; coding/annotator_notices.py)",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    lang_filter = args.lang
    verbose = args.verbose

    # (The pending-changes reminder is printed by the dispatcher before every
    # command; this used to print it a second time.)
    print("Connecting to Google APIs...")
    lang_ids = [lang_filter] if lang_filter else None
    notices: Optional[Dict[str, Optional[list]]] = {} if args.notify else None
    blocking = revalidate_sheets(lang_ids=lang_ids, verbose=verbose, notices=notices)
    if notices is not None:
        from .annotator_notices import notify
        print("\nNotices to annotators:")
        for lang_id, sheets in sorted(notices.items()):
            if sheets is None:
                print(f"  {lang_id}: not every sheet could be checked, so no notice "
                      f"was sent or closed (see the lines above)")
            else:
                print(f"  {lang_id}: {notify(lang_id, sheets)}")
    if blocking:
        sys.exit(1)


if __name__ == "__main__":
    main()
