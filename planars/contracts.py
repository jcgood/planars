"""Data contracts for two planars/ DataFrame boundaries (Phase 6, issue #271).

Both declare what a DataFrame must look like as an inspectable pandera
schema object, rather than as prose in a docstring plus a chain of
hand-rolled `if`/`raise` blocks buried in a function's body. The schema is
checked on every call, so it cannot go stale the way a comment can — and it
is the one place a reader goes to see the full contract at a glance,
instead of reading the function top to bottom. Both raise
`pandera.errors.SchemaError`/`SchemaErrors` on violation; their one caller
each catches that and re-raises `ValueError`, so every existing caller of
that function keeps seeing the exception type it has always caught.

Section 1 — planars/io.py's filled-TSV/sheet boundary (boundary 1 of the
plan's four candidates). `_parse_filled_df` (this package's `io.py`) is the
only caller, at two points that mirror where the old manual checks used to
run:

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
Fifteen `planars/*.py` analysis modules, `integrity-check`, and
`check-codebook` all depend on `_parse_filled_df` transitively.

Section 2 — planars/coreference.py's pair-row boundary (boundary 3).
Thinner than section 1's: `coreference.py` deliberately treats most bad
*values* (an unrecognized element, an unparseable `Position_B`) as
warnings collected into `missing_data`, not hard failures, only raised at
all when the caller passes `strict=True`. Real bug-catching value here is
narrower and different in kind: both `_load_planar_for_coreference` and
`derive_coreference_domains` read required columns via `row.get(col, "")`
with a silent `""` fallback, so a genuinely missing column (a typo'd
header, a tab regenerated with a different shape) doesn't crash; it
quietly makes every row look "unknown" and, unless `strict=True`, produces
a wrong-but-plausible-looking empty result instead of an error. Column
presence for both TSVs is now checked explicitly in `coreference.py`
itself, ahead of everything else, plain checks rather than pandera, same
as section 1's "Missing required column(s)" check and for the same
reason: catches the case the old `.get()` fallback would have silently
swallowed, before any code that assumes the columns exist gets to run.

`coreference_planar_rows_schema()` is the one pandera schema this section
adds, applied to the planar TSV's rows already filtered to one language
(after the column-presence check above). Checks `Position` is castable to
`int` (previously an unguarded `int(...)` call raising a raw, unclear
`ValueError`) and that a keystone row exists.

The pair TSV's per-row value leniency, an unrecognized element or an
unparseable `Position_B`, both collected into `missing_data` rather than
failed outright, stays exactly as it was: that leniency is deliberate, not
a gap.
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


# ---------------------------------------------------------------------------
# Section 2 — planars/coreference.py's pair-row boundary
# ---------------------------------------------------------------------------

CHECK_COREFERENCE_POSITION_INTEGER = "coreference_position_integer"
CHECK_COREFERENCE_HAS_KEYSTONE = "coreference_has_keystone"


def coreference_position_is_integer(s: pd.Series) -> pd.Series:
    def _ok(v: str) -> bool:
        try:
            int(v)
            return True
        except ValueError:
            return False

    return s.map(_ok)


def _coreference_has_keystone(df: pd.DataFrame) -> bool:
    return bool((df["Position_Name"].str.strip().str.lower() == "v:verbstem").any())


def coreference_planar_rows_schema() -> pa.DataFrameSchema:
    """Contract for the coreference planar TSV's rows already filtered to one
    language (column presence checked first, in _load_planar_for_coreference
    itself, ahead of this schema): Position must be castable to int, and
    there must be a keystone row."""
    return pa.DataFrameSchema(
        {
            "Position": pa.Column(
                str,
                pa.Check(
                    coreference_position_is_integer,
                    name=CHECK_COREFERENCE_POSITION_INTEGER,
                    error="Non-integer Position value.",
                ),
            ),
        },
        checks=[
            pa.Check(
                _coreference_has_keystone,
                name=CHECK_COREFERENCE_HAS_KEYSTONE,
                error="No keystone row (Position_Name == 'v:verbstem') in planar.",
            ),
        ],
        strict=False,
    )
