"""Tests for planars/contracts.py's pandera schemas, in isolation from their
wrapping (see tests/test_io.py for section 1's wrapped ValueError-raising
behaviour through load_filled_tsv, and tests/test_coreference.py for
section 2's through _load_planar_for_coreference/derive_coreference_domains).
"""
from __future__ import annotations

import pandas as pd
import pytest
from pandera.errors import SchemaError

from planars.contracts import (
    CHECK_COREFERENCE_HAS_KEYSTONE,
    CHECK_COREFERENCE_POSITION_INTEGER,
    CHECK_HAS_KEYSTONE,
    CHECK_NAME_TO_NUMBER,
    CHECK_NUMBER_TO_NAME,
    CHECK_ONE_KEYSTONE,
    coreference_planar_rows_schema,
    coreference_position_is_integer,
    raw_shape_schema,
    strict_criteria_schema,
)


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"Element": "elem-L", "Position_Name": "v:left",     "Position_Number": 3, "crit": "y"},
        {"Element": "ks",     "Position_Name": "v:verbstem", "Position_Number": 5, "crit": "na"},
        {"Element": "elem-R", "Position_Name": "v:right",    "Position_Number": 7, "crit": "n"},
    ])


class TestRawShapeSchema:
    def test_valid_df_passes(self):
        raw_shape_schema({"crit"}).validate(_valid_df())  # no raise

    def test_missing_required_criterion_column_raises(self):
        df = _valid_df().drop(columns=["crit"])
        with pytest.raises(SchemaError):
            raw_shape_schema({"crit"}).validate(df)

    def test_wrong_position_number_dtype_raises(self):
        df = _valid_df()
        df["Position_Number"] = df["Position_Number"].astype(str)
        with pytest.raises(SchemaError):
            raw_shape_schema({"crit"}).validate(df)

    def test_name_to_number_inconsistency_raises_with_named_check(self):
        df = pd.DataFrame([
            {"Element": "a", "Position_Name": "v:left",     "Position_Number": 3},
            {"Element": "b", "Position_Name": "v:left",     "Position_Number": 4},
            {"Element": "k", "Position_Name": "v:verbstem", "Position_Number": 5},
        ])
        with pytest.raises(SchemaError) as exc_info:
            raw_shape_schema(set()).validate(df)
        assert exc_info.value.check.name == CHECK_NAME_TO_NUMBER

    def test_number_to_name_inconsistency_raises_with_named_check(self):
        df = pd.DataFrame([
            {"Element": "a", "Position_Name": "v:left",     "Position_Number": 3},
            {"Element": "b", "Position_Name": "v:other",    "Position_Number": 3},
            {"Element": "k", "Position_Name": "v:verbstem", "Position_Number": 5},
        ])
        with pytest.raises(SchemaError) as exc_info:
            raw_shape_schema(set()).validate(df)
        assert exc_info.value.check.name == CHECK_NUMBER_TO_NAME

    def test_no_keystone_raises_with_named_check(self):
        df = _valid_df()
        df["Position_Name"] = df["Position_Name"].replace("v:verbstem", "v:notakey")
        with pytest.raises(SchemaError) as exc_info:
            raw_shape_schema({"crit"}).validate(df)
        assert exc_info.value.check.name == CHECK_HAS_KEYSTONE

    def test_multiple_keystone_positions_raises(self):
        # Two distinct raw Position_Name spellings that both case-fold to
        # 'v:verbstem' but carry different Position_Numbers: the name<->number
        # consistency checks don't catch this (each name maps to one number),
        # so this is CHECK_ONE_KEYSTONE's own reason to exist.
        df = pd.DataFrame([
            {"Element": "a",  "Position_Name": "v:left",      "Position_Number": 3},
            {"Element": "k1", "Position_Name": "v:verbstem",  "Position_Number": 5},
            {"Element": "k2", "Position_Name": "V:VERBSTEM",  "Position_Number": 9},
        ])
        with pytest.raises(SchemaError) as exc_info:
            raw_shape_schema(set()).validate(df)
        assert exc_info.value.check.name == CHECK_ONE_KEYSTONE


class TestStrictCriteriaSchema:
    def test_valid_df_passes(self):
        df = pd.DataFrame({"crit": ["y", "n"]})
        strict_criteria_schema({"crit"}).validate(df)  # no raise

    def test_blank_value_raises(self):
        df = pd.DataFrame({"crit": ["y", ""]})
        with pytest.raises(SchemaError, match="Blank value.*'crit'"):
            strict_criteria_schema({"crit"}).validate(df)

    def test_each_required_criterion_gets_its_own_check(self):
        # Regression test for the late-binding closure bug: a schema built
        # for {'a', 'b'} must report the actual offending column's name, not
        # whichever name a shared lambda closed over last.
        df = pd.DataFrame({"a": ["y", "y"], "b": ["y", ""]})
        with pytest.raises(SchemaError, match="'b'"):
            strict_criteria_schema({"a", "b"}).validate(df)


class TestCoreferencePlanarRowsSchema:
    def _valid_df(self):
        return pd.DataFrame({
            "Position": ["1", "5", "9"],
            "Position_Name": ["v:left", "v:verbstem", "v:right"],
        })

    def test_valid_df_passes(self):
        coreference_planar_rows_schema().validate(self._valid_df())  # no raise

    def test_non_integer_position_raises_with_named_check(self):
        df = self._valid_df()
        df.loc[0, "Position"] = "abc"
        with pytest.raises(SchemaError) as exc_info:
            coreference_planar_rows_schema().validate(df)
        assert exc_info.value.check.name == CHECK_COREFERENCE_POSITION_INTEGER

    def test_no_keystone_raises_with_named_check(self):
        df = self._valid_df()
        df["Position_Name"] = df["Position_Name"].replace("v:verbstem", "v:notakey")
        with pytest.raises(SchemaError) as exc_info:
            coreference_planar_rows_schema().validate(df)
        assert exc_info.value.check.name == CHECK_COREFERENCE_HAS_KEYSTONE

    def test_case_insensitive_keystone_match(self):
        df = self._valid_df()
        df["Position_Name"] = df["Position_Name"].replace("v:verbstem", "V:VERBSTEM")
        coreference_planar_rows_schema().validate(df)  # no raise


class TestCoreferencePositionIsInteger:
    def test_matches_python_int_semantics(self):
        s = pd.Series(["1", "-2", "+3", "4.0", "", "abc"])
        assert coreference_position_is_integer(s).tolist() == [True, True, True, False, False, False]
