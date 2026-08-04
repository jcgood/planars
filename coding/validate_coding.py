#!/usr/bin/env python3
"""Annotation sheet validation and the validate-coding command.

Validates filled annotation sheets against their expected criterion columns
and allowed values. Updates pink cell highlighting so collaborators can find
and fix errors without coordinator help.

Run from the repo root:
    python -m coding validate-coding                   # all languages
    python -m coding validate-coding --lang arao1248   # one language

Reads cell values from local TSVs (written by import-sheets) rather than
re-fetching them from Google Sheets, then writes pink highlights back to
Sheets only where invalid cells are found. Local TSVs must exist — if any
are missing, run `python -m coding import-sheets` first.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

from .drive import _with_retry, load_manifest
from .drive_doorway import get_doorway
from .generate_sheets import _INSTRUCTIONS_TAB, _PLANAR_REF_TAB, _STATUS_TAB
from .restructure_sheets import _get_pair_row_constructions
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
    criterion_values,
    load_diagnostic_criteria,
    load_planar_schema,
    load_diagnostic_classes,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STRUCTURAL_COLS      = {"Element", "Position_Name", "Position_Number"}
_PAIR_STRUCTURAL_COLS = {"Element_A", "Element_B", "Position_A", "Position_B", "Direction"}
_TRAILING_COLS        = load_planar_schema().get("trailing_columns", ["Source", "Comments"])
_DEFAULT_EXPECTED = set(load_diagnostic_criteria().get("default_allowed_values", ["y", "n", "na", "?"]))

# Per-construction criterion for coreference pair sheets, derived from schema.
# Each coreference construction annotates exactly one criterion, but the
# per-language diagnostics YAML lists all of them together under the class, so
# param_map alone would put every criterion column on every construction's tab.
# This narrows each construction to its own criterion.
#
# Both the criterion NAME and its allowed VALUES come from the schema. The
# values were previously hardcoded as ["y", "n"], which silently overrode
# diagnostic_criteria.yaml's [y, n, untestable] for reflexive_allowed /
# pronoun_allowed / np_allowed -- so the generated dropdowns offered
# "untestable" (they are built from the per-language YAML) while validation
# rejected it and highlighted the cell pink. Never restate a criterion's values
# here; ask the schema.
def _entry_for(crit: str) -> dict:
    """Build a {params, values} entry for a single criterion, values from schema."""
    vals = criterion_values(crit)
    # No declared values -> omit the key so validation falls back to defaults,
    # rather than asserting an empty allowed-set that rejects everything.
    return {"params": [crit], "values": {crit: vals}} if vals else {"params": [crit]}


def _build_coreference_params() -> Dict[str, dict]:
    _dc = {c["name"]: c for c in load_diagnostic_classes().get("classes", [])}
    # prescreening is row_type: element and declares no `criterion` in
    # diagnostic_classes.yaml, so its criterion NAME still has to be named here.
    # That remaining hardcode is catalogued in docs/hidden-facts-inventory.md and
    # belongs to Phase 3; resolving it means adding `criterion: referential` to
    # the schema, which changes sheet generation and wants snapshots first.
    result: Dict[str, dict] = {"prescreening": _entry_for("referential")}
    for con in (_dc.get("coreference", {}).get("constructions") or []):
        if isinstance(con, dict) and "criterion" in con:
            result[con["name"]] = _entry_for(con["criterion"])
    return result

_COREFERENCE_CONSTRUCTION_PARAMS: Dict[str, dict] = _build_coreference_params()
# Placeholder used in diagnostic_criteria.yaml for criteria that accept any
# non-negative integer (e.g. dependent-on-left, dependent-on-right).
_POSITION_NUMBER_PLACEHOLDER = "<position_number>"

_PINK  = {"red": 1.0, "green": 0.8, "blue": 0.8}
_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}

_KEYSTONE_NAME = load_planar_schema().get("keystone_position_name", "v:verbstem")

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
    _with_retry(lambda: ws.spreadsheet.batch_update({"requests": requests}))


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
    _with_retry(lambda: ws.spreadsheet.batch_update(body))


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
                              "element rows (Element, Position_Name, Position_Number)",
                              class_name, lang_id)])

    for col in ("Element", "Position_Name", "Position_Number"):
        if col not in header:
            issues.append(ValidationIssue("error", tab_name, f"missing structural column '{col}'"))

    actual_params = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
    if actual_params != expected_params:
        issues.append(ValidationIssue(
            "warning", tab_name,
            f"criterion columns differ from manifest — "
            f"expected {expected_params}, got {actual_params}"
        ))

    col_index  = {name: i for i, name in enumerate(header)}
    param_cols = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]

    records = []
    for row_num, row in enumerate(data_rows, start=2):
        while len(row) < len(header):
            row.append("")

        record   = {col: row[col_index[col]] for col in header if col in col_index}
        pos_name = record.get("Position_Name", "").strip()
        is_keystone = pos_name.lower() == _KEYSTONE_NAME

        for param in param_cols:
            val = record.get(param, "").strip().lower()
            record[param] = val

            allowed = (
                {v.lower() for v in (param_values or {}).get(param, [])} | {"na", "?"}
                if param_values and param in param_values
                else _DEFAULT_EXPECTED
            )
            accepts_pos_num = _POSITION_NUMBER_PLACEHOLDER in allowed

            if is_keystone:
                _na_criteria = keystone_na_criteria or []
                if keystone_active and param not in _na_criteria:
                    # Keystone participates in this analysis — treat like any row.
                    if val == "":
                        issues.append(ValidationIssue(
                            "warning",
                            f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                            f"blank value in '{param}' (keystone is active for this construction)",
                            cell=(row_num - 1, col_index[param]),
                        ))
                    elif val == "na":
                        issues.append(ValidationIssue(
                            "warning",
                            f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                            f"'na' in '{param}' but keystone is active — expected a real annotation value",
                            cell=(row_num - 1, col_index[param]),
                        ))
                    elif val not in allowed and not (accepts_pos_num and val.isdigit()):
                        issues.append(ValidationIssue(
                            "warning",
                            f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                            f"unexpected value '{val}' in '{param}' (allowed: {sorted(allowed)})",
                            cell=(row_num - 1, col_index[param]),
                        ))
                else:
                    # Keystone does not participate (or criterion is self-referential
                    # on the keystone) — should always be 'na'.
                    if val == "":
                        record[param] = "na"
                    elif val != "na":
                        issues.append(ValidationIssue(
                            "warning",
                            f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                            f"unexpected value '{val}' in '{param}' for keystone row (expected 'na')",
                            cell=(row_num - 1, col_index[param]),
                        ))
            else:
                if val == "":
                    issues.append(ValidationIssue(
                        "warning",
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                        f"blank value in '{param}'",
                        cell=(row_num - 1, col_index[param]),
                    ))
                elif val not in allowed and not (accepts_pos_num and val.isdigit()):
                    issues.append(ValidationIssue(
                        "warning",
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                        f"unexpected value '{val}' in '{param}' (allowed: {sorted(allowed)})",
                        cell=(row_num - 1, col_index[param]),
                    ))

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
    param_cols = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
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
    sheet_header = _with_retry(lambda: ws.row_values(1))
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
            f"criterion columns differ from manifest — "
            f"expected {expected_params}, got {actual_params}"
        ))

    col_index  = {name: i for i, name in enumerate(header)}
    param_cols = [c for c in header if c not in _PAIR_STRUCTURAL_COLS and c not in _TRAILING_COLS]

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

            allowed = (
                {v.lower() for v in (param_values or {}).get(param, [])} | {"na", "?"}
                if param_values and param in param_values
                else _DEFAULT_EXPECTED
            )

            if val == "":
                issues.append(ValidationIssue(
                    "warning",
                    f"{tab_name} row {row_num} '{label}'",
                    f"blank value in '{param}'",
                    cell=(row_num - 1, col_index[param]),
                ))
            elif val not in allowed:
                issues.append(ValidationIssue(
                    "warning",
                    f"{tab_name} row {row_num} '{label}'",
                    f"unexpected value '{val}' in '{param}' (allowed: {sorted(allowed)})",
                    cell=(row_num - 1, col_index[param]),
                ))

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
        param_map.setdefault(class_name, {})[construction] = {
            "params": param_names,
            "values": param_values,
        }
    return param_map


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------

def revalidate_sheets(
    lang_ids: list[str] | None = None,
    verbose: bool = False,
) -> int:
    """Revalidate annotation sheets for the given languages (all if None).

    Returns the number of blocking issues found.  Updates pink highlighting
    in Sheets as a side effect.  Called by restructure_sheets after --apply
    to refresh highlighting on newly created sheets.
    """
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

        for class_name, sheet_info in sorted(lang_data.get("sheets", {}).items()):
            sid = sheet_info.get("spreadsheet_id") or sheet_info.get("id")
            if not sid:
                continue
            try:
                ss = doorway.open_spreadsheet(sid)
            except Exception as e:
                print(f"  [{class_name}] could not open spreadsheet: {e}")
                continue

            for ws in _with_retry(lambda: ss.worksheets()):
                construction = ws.title
                if construction in (_STATUS_TAB, _INSTRUCTIONS_TAB, _PLANAR_REF_TAB):
                    continue
                if class_name == "coreference" and construction in _COREFERENCE_CONSTRUCTION_PARAMS:
                    info = _COREFERENCE_CONSTRUCTION_PARAMS[construction]
                else:
                    info = param_map.get(class_name, {}).get(construction, {})
                try:
                    is_pair_sheet = construction in pair_row_constructions.get(class_name, set())
                    if is_pair_sheet:
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
                    continue
                total_sheets += 1

                # Separate actionable issues from blank-cell completeness noise.
                # Blank cells are expected during annotation and highlighted pink
                # in the Sheet for annotators, but should not trigger exit(1) or
                # clutter the report. Use --verbose to see them individually.
                blocking = [i for i in issues if "blank value" not in i.message]
                blank_count = len(issues) - len(blocking)
                total_blocking += len(blocking)

                if blocking:
                    print(f"  [{class_name}/{construction}] {len(blocking)} issue(s):")
                    for issue in blocking:
                        print(f"    {issue}")
                    if blank_count and not verbose:
                        print(f"    ({blank_count} blank cell(s) — annotation in progress; use --verbose to list)")
                elif blank_count:
                    print(f"  [{class_name}/{construction}] {blank_count} blank cell(s) — annotation in progress")
                else:
                    print(f"  [{class_name}/{construction}] no issues")

                if verbose and blank_count:
                    for issue in issues:
                        if "blank value" in issue.message:
                            print(f"    {issue}")

    print(f"\n{'─' * 50}")
    print(f"Validated {total_sheets} sheet(s).  Data coding issues: {total_blocking}")
    if total_missing:
        print(f"{total_missing} construction(s) skipped — no local TSV. Run `python -m coding import-sheets` first.")
    if total_blocking:
        print("Cell highlighting updated in Google Sheets.")
    else:
        print("All data coding issues cleared. (Pink highlighting for blank cells preserved.)")
    return total_blocking


def main() -> None:
    args = sys.argv[1:]
    lang_filter = args[args.index("--lang") + 1] if "--lang" in args else None
    verbose = "--verbose" in args

    pending = ROOT / "pending_changes.json"
    if pending.exists() and pending.stat().st_size > 2:
        print("WARNING: Pending destructive changes require coordinator approval.")
        print("         Run: python -m coding apply-pending\n")

    print("Connecting to Google APIs...")
    lang_ids = [lang_filter] if lang_filter else None
    blocking = revalidate_sheets(lang_ids=lang_ids, verbose=verbose)
    if blocking:
        sys.exit(1)


if __name__ == "__main__":
    main()
