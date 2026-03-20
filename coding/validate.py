#!/usr/bin/env python3
"""Shared validation functions for planar structure and annotation sheets.

Used by:
  - import_sheets.py      (annotation validation during import)
  - validate_sheets.py    (standalone revalidation command, closes #49)
  - Colab validation notebook (#14)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    level: str                          # "error" or "warning"
    location: str                       # human-readable location string
    message: str
    cell: Optional[Tuple[int, int]] = None  # (row_idx, col_idx) 0-based for Sheets

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.location}: {self.message}"


# ---------------------------------------------------------------------------
# Planar structure validation
# ---------------------------------------------------------------------------

_VALID_POSITION_TYPES = {"Zone", "Slot"}
_VALID_CLASS_TYPES    = {"open", "list", "closed"}
_KEYSTONE_NAME        = "v:verbstem"

# ALL CAPS label: starts with an uppercase letter, contains only uppercase
# letters, digits, hyphens, underscores, and optional brace-enclosed suffixes.
_ALL_CAPS_RE = re.compile(r'^[A-Z][A-Z0-9\-_]*(\{[^}]*\})?$')


def _is_all_caps_token(token: str) -> bool:
    return bool(_ALL_CAPS_RE.match(token.strip()))


def _tokenize_elements(s: str) -> List[str]:
    return [t.strip() for t in s.split(",") if t.strip()]


def validate_planar_df(df) -> List[ValidationIssue]:
    """Validate a planar structure DataFrame loaded from planar_*.tsv.

    Checks:
    - Position_Number values are sequential integers 1..N
    - Position_Name values are unique
    - Exactly one v:verbstem (keystone) row exists
    - Position_Type is Zone or Slot for every non-keystone row
    - Class_Type is open, list, or closed for every row
    - Element convention consistency:
        list  → elements should be lowercase morpheme forms
        open  → elements should be ALL CAPS category labels (possibly mixed
                with lowercase as an abbreviation for "more not listed")
    """
    issues: List[ValidationIssue] = []

    required = {"Position_Number", "Position_Name", "Position_Type", "Elements", "Class_Type"}
    missing = required - set(df.columns)
    if missing:
        issues.append(ValidationIssue(
            "error", "planar structure",
            f"Missing columns: {sorted(missing)}"
        ))
        return issues

    # Sequential position numbers
    try:
        pos_nums = [int(p) for p in df["Position_Number"]]
    except (ValueError, TypeError):
        issues.append(ValidationIssue(
            "error", "Position_Number",
            "Non-integer value(s) in Position_Number column"
        ))
        pos_nums = []

    if pos_nums and pos_nums != list(range(1, len(pos_nums) + 1)):
        issues.append(ValidationIssue(
            "error", "Position_Number",
            f"Position numbers are not sequential integers 1..{len(pos_nums)}: {pos_nums}"
        ))

    # Unique Position_Name
    seen: Dict[str, int] = {}
    for i, name in enumerate(df["Position_Name"]):
        name = str(name).strip()
        if name in seen:
            issues.append(ValidationIssue(
                "error", f"row {i + 2}",
                f"Duplicate Position_Name '{name}' (first at row {seen[name] + 2})"
            ))
        else:
            seen[name] = i

    # Exactly one v:verbstem
    keystone_rows = [
        i for i, n in enumerate(df["Position_Name"])
        if str(n).strip().lower() == _KEYSTONE_NAME
    ]
    if len(keystone_rows) == 0:
        issues.append(ValidationIssue(
            "error", "planar structure",
            f"No keystone row found (Position_Name == '{_KEYSTONE_NAME}')"
        ))
    elif len(keystone_rows) > 1:
        bad_pos = [df["Position_Number"].iloc[i] for i in keystone_rows]
        issues.append(ValidationIssue(
            "error", "planar structure",
            f"Multiple keystone rows at positions: {bad_pos}"
        ))

    for i, row in df.iterrows():
        pos_name = str(row.get("Position_Name", "")).strip()
        is_keystone = pos_name.lower() == _KEYSTONE_NAME

        # Position_Type
        pt = str(row.get("Position_Type", "")).strip()
        if pt not in _VALID_POSITION_TYPES:
            issues.append(ValidationIssue(
                "error", f"row {i + 2} '{pos_name}'",
                f"Position_Type '{pt}' must be one of {sorted(_VALID_POSITION_TYPES)}"
            ))

        # Class_Type + element conventions
        ct = str(row.get("Class_Type", "")).strip().lower()
        elements_str = str(row.get("Elements", "")).strip()

        if is_keystone:
            continue  # KEYSTONE element is a special reserved value

        if ct not in _VALID_CLASS_TYPES:
            issues.append(ValidationIssue(
                "error", f"row {i + 2} '{pos_name}'",
                f"Class_Type '{ct}' must be one of {sorted(_VALID_CLASS_TYPES)}"
            ))
            continue

        tokens = _tokenize_elements(elements_str)
        if not tokens:
            continue

        if ct == "list":
            caps = [t for t in tokens if _is_all_caps_token(t)]
            if caps:
                issues.append(ValidationIssue(
                    "warning", f"row {i + 2} '{pos_name}'",
                    f"Type 'list' but contains ALL CAPS token(s) {caps} — "
                    f"consider type 'open' if these are category labels"
                ))
        elif ct == "open":
            all_lower = all(t[0].islower() for t in tokens if t)
            if all_lower:
                issues.append(ValidationIssue(
                    "warning", f"row {i + 2} '{pos_name}'",
                    f"Type 'open' but all elements appear lowercase {tokens} — "
                    f"consider type 'list' if these are specific morphemes"
                ))

    return issues


# ---------------------------------------------------------------------------
# Annotation sheet validation
# ---------------------------------------------------------------------------

_STRUCTURAL_COLS  = {"Element", "Position_Name", "Position_Number"}
_TRAILING_COLS    = {"Comments"}
_DEFAULT_EXPECTED = {"y", "n", "na", "?"}


def validate_annotation_rows(
    rows: List[List[str]],
    expected_params: List[str],
    tab_name: str,
    param_values: Dict[str, List[str]] = None,
) -> Tuple[List[Dict], List[ValidationIssue]]:
    """Validate annotation sheet rows.

    Returns (records, issues).  records are dicts ready to write as TSV rows.
    Supersedes import_sheets._validate_tab; callers should use this instead.
    """
    issues: List[ValidationIssue] = []

    if not rows:
        return [], [ValidationIssue("error", tab_name, "sheet is empty")]

    header    = rows[0]
    data_rows = rows[1:]

    for col in ("Element", "Position_Name", "Position_Number"):
        if col not in header:
            issues.append(ValidationIssue("error", tab_name, f"missing structural column '{col}'"))

    actual_params = [c for c in header if c not in _STRUCTURAL_COLS and c not in _TRAILING_COLS]
    if actual_params != expected_params:
        issues.append(ValidationIssue(
            "warning", tab_name,
            f"parameter columns differ from manifest — "
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

            if is_keystone:
                if val == "":
                    record[param] = "na"
            else:
                if val == "":
                    issues.append(ValidationIssue(
                        "warning",
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                        f"blank value in '{param}'",
                        cell=(row_num - 1, col_index[param]),
                    ))
                elif val not in allowed:
                    issues.append(ValidationIssue(
                        "warning",
                        f"{tab_name} row {row_num} '{record.get('Element', '?')}'",
                        f"unexpected value '{val}' in '{param}' (allowed: {sorted(allowed)})",
                        cell=(row_num - 1, col_index[param]),
                    ))

        records.append(record)

    return records, issues


# ---------------------------------------------------------------------------
# Google Sheets cell highlighting
# ---------------------------------------------------------------------------

_PINK  = {"red": 1.0, "green": 0.8, "blue": 0.8}
_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}


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
    ws.spreadsheet.batch_update({"requests": requests})


def clear_highlights(ws) -> None:
    """Clear all pink highlighting from a worksheet by resetting backgrounds to white."""
    ws.spreadsheet.batch_update({"requests": [{
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
    }]})


def revalidate_sheet(
    ws,
    expected_params: List[str],
    param_values: Dict[str, List[str]] = None,
) -> List[ValidationIssue]:
    """Read a worksheet, validate it, update cell highlighting, return issues.

    Clears all existing highlights first, then re-highlights bad cells.
    Safe to call repeatedly as collaborators fix errors.
    """
    rows = ws.get_all_values()
    _, issues = validate_annotation_rows(rows, expected_params, ws.title, param_values)
    bad_cells = [issue.cell for issue in issues if issue.cell is not None]
    clear_highlights(ws)
    highlight_cells(ws, bad_cells)
    return issues
