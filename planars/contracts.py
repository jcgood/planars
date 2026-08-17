"""Data contract for planars/io.py's filled-TSV/sheet boundary.

Phase 6 of the data layer redesign (issue #271): declare what every filled
annotation TSV or Sheet must look like as an inspectable pandera schema
object, rather than as prose in `_parse_filled_df`'s docstring plus a chain
of hand-rolled `if`/`raise` blocks buried in that function's body. The
schema is checked on every call, so it cannot go stale the way a comment
can — and it is the one place a reader goes to see the full contract at a
glance, instead of reading a 100-line function top to bottom.

`_parse_filled_df` (this package's `io.py`) is the only caller, at two
points that mirror where the old manual checks used to run:

- `raw_shape_schema(required_criteria)` — applied right after the required
  structural columns (`Element`, `Position_Name`, `Position_Number`) and
  every `required_criteria` column are normalized (stripped; criteria also
  lowercased) and `Position_Number` is cast to `int`. Checks the
  `Position_Name` <-> `Position_Number` mapping is 1-to-1, and that there is
  exactly one keystone row (`Position_Name == 'v:verbstem'`, case-
  insensitive — matching `_parse_filled_df`'s own keystone lookup).
- `strict_criteria_schema(required_criteria)` — applied to `data_df` only
  (after the keystone split), when the caller asked for `strict=True`.
  Checks every required criterion is non-blank in every non-keystone row.

Column *presence* (the "Missing required column(s)" check) and blank
`Position_Number` detection stay as plain checks in `_parse_filled_df`
itself, ahead of these two schemas — both preconditions the normalization
step needs to hold before it can run at all, so validating them via a
schema built from columns that might not exist yet would be circular.

Both schemas raise `pandera.errors.SchemaError`/`SchemaErrors` on
violation. `_parse_filled_df` catches those and re-raises `ValueError`, so
every existing caller — fifteen `planars/*.py` analysis modules,
`integrity-check`, `check-codebook` — keeps seeing the exception type it
has always caught.
"""
from __future__ import annotations

from typing import Set

import pandas as pd
import pandera.pandas as pa

# Names for the raw_shape_schema checks, so callers that need to build a
# richer message than the generic `error=` text (e.g. _parse_filled_df
# listing which specific Position_Names collided) can identify which check
# failed via `SchemaError.check.name` instead of parsing the error string.
CHECK_NAME_TO_NUMBER = "name_to_number_consistent"
CHECK_NUMBER_TO_NAME = "number_to_name_consistent"
CHECK_HAS_KEYSTONE = "has_keystone"
CHECK_ONE_KEYSTONE = "exactly_one_keystone_position"


def _name_to_number_consistent(df: pd.DataFrame) -> bool:
    return bool(df.groupby("Position_Name")["Position_Number"].nunique().le(1).all())


def _number_to_name_consistent(df: pd.DataFrame) -> bool:
    return bool(df.groupby("Position_Number")["Position_Name"].nunique().le(1).all())


def _keystone_mask(df: pd.DataFrame) -> pd.Series:
    return df["Position_Name"].str.lower() == "v:verbstem"


def _has_keystone(df: pd.DataFrame) -> bool:
    return bool(_keystone_mask(df).any())


def _exactly_one_keystone_position(df: pd.DataFrame) -> bool:
    mask = _keystone_mask(df)
    if not mask.any():
        return True  # _has_keystone reports this failure; don't double-report
    return df.loc[mask, "Position_Number"].nunique() == 1


def raw_shape_schema(required_criteria: Set[str]) -> pa.DataFrameSchema:
    """Contract for the full sheet, post-normalization, pre-keystone-split.

    `required_criteria` columns are declared explicitly so the schema lists
    the exact set a given caller depends on, but the check logic itself
    (Name<->Number consistency, exactly one keystone) doesn't touch them —
    only the structural columns matter here.
    """
    columns = {
        "Element": pa.Column(str),
        "Position_Name": pa.Column(str),
        "Position_Number": pa.Column(int),
    }
    for c in required_criteria:
        columns[c] = pa.Column(str)
    return pa.DataFrameSchema(
        columns,
        checks=[
            pa.Check(
                _name_to_number_consistent,
                name=CHECK_NAME_TO_NUMBER,
                error="Inconsistent Position_Name <-> Position_Number mapping "
                "(sheet may be out of sync with the planar structure — "
                "run restructure_sheets.py).",
            ),
            pa.Check(
                _number_to_name_consistent,
                name=CHECK_NUMBER_TO_NAME,
                error="Inconsistent Position_Name <-> Position_Number mapping "
                "(sheet may be out of sync with the planar structure — "
                "run restructure_sheets.py).",
            ),
            pa.Check(
                _has_keystone,
                name=CHECK_HAS_KEYSTONE,
                error="No keystone row found (Position_Name == 'v:verbstem').",
            ),
            pa.Check(
                _exactly_one_keystone_position,
                name=CHECK_ONE_KEYSTONE,
                error="Expected exactly 1 keystone position, found more than one.",
            ),
        ],
        strict=False,  # extra (non-required) criterion and trailing columns are expected
    )


def _non_blank_column(name: str) -> pa.Column:
    # A lambda capturing `name` in a dict/generator comprehension would close
    # over the loop variable itself (late binding), so every column's check
    # would report the last name in required_criteria. This factory gives
    # each Column its own closure instead.
    return pa.Column(str, pa.Check(lambda s: s != "", error=f"Blank value(s) in column '{name}'."))


def strict_criteria_schema(required_criteria: Set[str]) -> pa.DataFrameSchema:
    """Contract for data_df (non-keystone rows) when strict=True: every
    required criterion must be non-blank in every row."""
    columns = {c: _non_blank_column(c) for c in required_criteria}
    return pa.DataFrameSchema(columns, strict=False)
