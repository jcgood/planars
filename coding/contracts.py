"""Data contract for coding/make_forms.py's planar-load boundary.

Phase 6 of the data layer redesign (issue #271), second of the four
candidate boundaries the plan names — see `planars/contracts.py` for the
first (the filled-TSV/sheet loader) and its module docstring for the full
rationale, which applies here unchanged. This one lives in `coding/`
rather than `planars/` because `build_element_index` is coordinator
tooling only (`generate_sheets.py`, `update_sheets.py`,
`restructure_sheets.py`) — nothing in the `planars` package Colab installs
imports it, so unlike the first boundary this doesn't add a Colab runtime
dependency (pandera was already added there for the first boundary).

`build_element_index` (`make_forms.py`) processes planar TSV rows in two
narrowing stages, each with its own contract, mirroring the row-by-row
order the original hand-written loop used:

1. Rows matching the target `Language_ID` with a non-blank `Position`:
   `position_integer_schema()` checks `Position` is castable to `int` —
   using an actual `int()` attempt in the check, not a regex, so it accepts
   exactly what `int()` accepts (e.g. a leading `+`).
2. Of those, rows with non-blank `Elements`: `class_type_schema()` checks
   `Class_Type` (already lowercased/stripped) is one of `open`/`list`/`mixed`.

A row with blank `Position` or blank `Elements` is silently skipped by
`build_element_index` itself (not a contract violation — a planar TSV can
have placeholder/reserved position rows with nothing filled in yet), which
is why the schemas apply to the narrowed subsets rather than the whole
sheet: a bogus `Class_Type` on a row nobody is going to read from is not
this contract's concern.

The row-explosion duplicate-key check (`element@position` collisions,
e.g. from the same element listed twice in one position's comma-separated
`Elements` cell) stays procedural in `make_forms.py` rather than moving
here — it depends on per-row multi-element splitting
(`_split_elements`), which doesn't fit a per-column schema check.

Both schemas raise `pandera.errors.SchemaError` on violation;
`build_element_index` catches that and re-raises `ValueError` with the
same message format the original inline `raise` statements used, so its
three callers keep seeing the exception type — and message shape — they
always have.
"""
from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

CHECK_POSITION_INTEGER = "position_integer"
CHECK_CLASS_TYPE_VALID = "class_type_valid"

VALID_CLASS_TYPES = ("open", "list", "mixed")


def position_is_integer(s: pd.Series) -> pd.Series:
    def _ok(v: str) -> bool:
        try:
            int(v)
            return True
        except ValueError:
            return False

    return s.map(_ok)


def position_integer_schema() -> pa.DataFrameSchema:
    """Contract for rows already filtered to: matching Language_ID, non-blank
    Position. Position must be castable to int."""
    return pa.DataFrameSchema(
        {
            "Position": pa.Column(
                str,
                pa.Check(
                    position_is_integer,
                    name=CHECK_POSITION_INTEGER,
                    error="Non-integer Position value.",
                ),
            ),
        },
        strict=False,
    )


def class_type_schema() -> pa.DataFrameSchema:
    """Contract for rows already filtered to: matching Language_ID, non-blank
    Position, non-blank Elements. Class_Type must be a known value."""
    return pa.DataFrameSchema(
        {
            "Class_Type": pa.Column(
                str,
                pa.Check.isin(
                    VALID_CLASS_TYPES,
                    name=CHECK_CLASS_TYPE_VALID,
                    error=f"Unexpected Class_Type (must be one of {list(VALID_CLASS_TYPES)}).",
                ),
            ),
        },
        strict=False,
    )
