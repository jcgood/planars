"""Tests for coding/contracts.py's pandera schemas, in isolation from
coding/make_forms.py's wrapping (see tests/test_make_forms.py for the
wrapped ValueError-raising behaviour exercised through build_element_index).
"""
from __future__ import annotations

import pandas as pd
import pytest
from pandera.errors import SchemaError

from coding.contracts import (
    CHECK_CLASS_TYPE_VALID,
    CHECK_POSITION_INTEGER,
    class_type_schema,
    position_integer_schema,
    position_is_integer,
)


class TestPositionIntegerSchema:
    def test_valid_positions_pass(self):
        df = pd.DataFrame({"Position": ["1", "-2", "+3", "004"]})
        position_integer_schema().validate(df)  # no raise

    def test_non_integer_position_raises_with_named_check(self):
        df = pd.DataFrame({"Position": ["1", "abc"]})
        with pytest.raises(SchemaError) as exc_info:
            position_integer_schema().validate(df)
        assert exc_info.value.check.name == CHECK_POSITION_INTEGER

    def test_blank_position_raises(self):
        # position_integer_schema is applied only to already-filtered
        # non-blank rows by build_element_index; on its own a blank string
        # is not int-castable either.
        df = pd.DataFrame({"Position": [""]})
        with pytest.raises(SchemaError):
            position_integer_schema().validate(df)


class TestClassTypeSchema:
    def test_valid_class_types_pass(self):
        df = pd.DataFrame({"Class_Type": ["open", "list", "mixed"]})
        class_type_schema().validate(df)  # no raise

    def test_unknown_class_type_raises_with_named_check(self):
        df = pd.DataFrame({"Class_Type": ["open", "bogus"]})
        with pytest.raises(SchemaError) as exc_info:
            class_type_schema().validate(df)
        assert exc_info.value.check.name == CHECK_CLASS_TYPE_VALID


class TestPositionIsInteger:
    def test_matches_python_int_semantics(self):
        s = pd.Series(["1", "-2", "+3", " 4 ".strip(), "4.0", "", "abc"])
        result = position_is_integer(s).tolist()
        assert result == [True, True, True, True, False, False, False]
