#!/usr/bin/env python3
"""Validation for planar structure TSVs (planar_*.tsv).

Called by generate-sheets and validate-coding to flag structural issues
before sheets are created or revalidated.
"""
from __future__ import annotations

import re
from typing import Dict, List

from .validate import ValidationIssue
from .schemas import load_planar_schema

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_POSITION_TYPES = {"Zone", "Slot"}
_VALID_CLASS_TYPES    = {"open", "list", "closed"}
_KEYSTONE_NAME        = load_planar_schema().get("keystone_position_name", "v:verbstem")

# ALL CAPS label: starts with an uppercase letter, contains only uppercase
# letters, digits, hyphens, underscores, and optional brace-enclosed suffixes.
_ALL_CAPS_RE = re.compile(r'^[A-Z][A-Z0-9\-_]*(\{[^}]*\})?$')


def _is_all_caps_token(token: str) -> bool:
    return bool(_ALL_CAPS_RE.match(token.strip()))


def _tokenize_elements(s: str) -> List[str]:
    """Split element string by comma, but not commas inside brace notation (e.g. NP{S,A,P})."""
    tokens = []
    depth = 0
    current: List[str] = []
    for ch in s:
        if ch == "{":
            depth += 1
            current.append(ch)
        elif ch == "}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            token = "".join(current).strip()
            if token:
                tokens.append(token)
            current = []
        else:
            current.append(ch)
    token = "".join(current).strip()
    if token:
        tokens.append(token)
    return tokens


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_planar_df(df) -> List[ValidationIssue]:
    """Validate a planar structure DataFrame loaded from planar_*.tsv.

    Checks:
    - Position values are sequential integers 1..N
    - Position_Name values are unique
    - Exactly one v:verbstem (keystone) row exists
    - Position_Type is Zone or Slot for every row
    - Class_Type is open, list, or closed for every row
    - Element convention consistency:
        list  → warn if ALL elements are ALL CAPS (probably should be open)
        open  → warn if ANY element is not ALL CAPS; distinguish between
                simple casing errors and collapses with existing labels
    """
    issues: List[ValidationIssue] = []

    required = {"Position", "Position_Name", "Position_Type", "Elements", "Class_Type"}
    missing = required - set(df.columns)
    if missing:
        issues.append(ValidationIssue(
            "error", "planar structure",
            f"Missing columns: {sorted(missing)}"
        ))
        return issues

    # Sequential position numbers
    try:
        pos_nums = [int(p) for p in df["Position"]]
    except (ValueError, TypeError):
        issues.append(ValidationIssue(
            "error", "Position",
            "Non-integer value(s) in Position column"
        ))
        pos_nums = []

    if pos_nums and pos_nums != list(range(1, len(pos_nums) + 1)):
        issues.append(ValidationIssue(
            "error", "Position",
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
        bad_pos = [df["Position"].iloc[i] for i in keystone_rows]
        issues.append(ValidationIssue(
            "error", "planar structure",
            f"Multiple keystone rows at positions: {bad_pos}"
        ))

    # Pre-compute: ALL CAPS labels and where they appear (for collapse detection).
    caps_positions: Dict[str, List[str]] = {}  # ALL-CAPS label → [pos_names]
    for _, row in df.iterrows():
        pn = str(row.get("Position_Name", "")).strip()
        if pn.lower() == _KEYSTONE_NAME:
            continue
        for t in _tokenize_elements(str(row.get("Elements", "")).strip()):
            if _is_all_caps_token(t):
                caps_positions.setdefault(t, []).append(pn)

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
            if caps and len(caps) == len(tokens):
                issues.append(ValidationIssue(
                    "warning", f"row {i + 2} '{pos_name}'",
                    f"Type 'list' but all elements are ALL CAPS {caps} — "
                    f"consider type 'open' if these are category labels"
                ))
        elif ct == "open":
            not_caps = [t for t in tokens if not _is_all_caps_token(t)]
            for t in not_caps:
                normalized = t.upper()
                other_pos = [p for p in caps_positions.get(normalized, []) if p != pos_name]
                if other_pos:
                    issues.append(ValidationIssue(
                        "warning", f"row {i + 2} '{pos_name}'",
                        f"Type 'open' element '{t}' is not ALL CAPS — correcting to "
                        f"'{normalized}' would collapse it with the same label at: {other_pos}"
                    ))
                else:
                    issues.append(ValidationIssue(
                        "warning", f"row {i + 2} '{pos_name}'",
                        f"Type 'open' element '{t}' is not ALL CAPS — "
                        f"open positions should use ALL CAPS labels (e.g. '{normalized}')"
                    ))

    return issues
