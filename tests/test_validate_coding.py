"""Tests for coding/validate_coding.py — validate_annotation_rows."""
from __future__ import annotations

from coding.validate_coding import validate_annotation_rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HEADER = ["Element", "Position_Name", "Position_Number", "aspirated"]

def _rows(keystone_val: str, other_val: str = "y") -> list[list[str]]:
    return [
        _HEADER,
        ["KEYSTONE", "v:verbstem", "14", keystone_val],
        ["elem-a",   "slot-left",  "13", other_val],
    ]


# ---------------------------------------------------------------------------
# Regression: aspirated=both on keystone with keystone_active=True
# ---------------------------------------------------------------------------

def test_keystone_active_both_is_valid():
    """aspirated=both on the keystone row produces no issues when keystone_active=True.

    Regression for issue #161: Colab validation notebook was stale (generated before
    keystone_active Phase A, #104) and defaulted keystone_active to False, causing a
    false-positive warning for segmental/aspiration_prominence.
    """
    param_values = {"aspirated": ["y", "n", "both"]}
    _, issues = validate_annotation_rows(
        _rows("both"),
        expected_params=["aspirated"],
        tab_name="aspiration_prominence",
        param_values=param_values,
        keystone_active=True,
    )
    assert issues == []


def test_keystone_active_false_both_warns():
    """aspirated=both on the keystone row warns when keystone_active=False (default).

    Confirms the other side of the regression: without keystone_active=True the warning
    does fire, so the fix is meaningful.
    """
    param_values = {"aspirated": ["y", "n", "both"]}
    _, issues = validate_annotation_rows(
        _rows("both"),
        expected_params=["aspirated"],
        tab_name="aspiration_prominence",
        param_values=param_values,
        keystone_active=False,
    )
    assert any("unexpected value" in i.message and "aspirated" in i.message for i in issues)


def test_keystone_active_na_on_na_criterion_is_valid():
    """na on the keystone for a self-referential criterion is valid even when keystone_active=True."""
    _, issues = validate_annotation_rows(
        _rows("na"),
        expected_params=["aspirated"],
        tab_name="aspiration_prominence",
        keystone_active=True,
        keystone_na_criteria=["aspirated"],
    )
    assert issues == []


# ---------------------------------------------------------------------------
# Position-number placeholder: dependent-on-left / dependent-on-right
# ---------------------------------------------------------------------------

_FREE_HEADER = ["Element", "Position_Name", "Position_Number", "free", "dependent-on-left", "dependent-on-right"]
_FREE_PV = {"free": ["y", "n"], "dependent-on-left": ["na", "<position_number>"], "dependent-on-right": ["na", "<position_number>"]}

def test_position_number_value_is_valid():
    """An integer position number in dependent-on-left/right is accepted without a warning."""
    rows = [
        _FREE_HEADER,
        ["KEYSTONE", "v:verbstem", "30", "na", "na", "na"],
        ["elem-a",   "v:left",     "1",  "n",  "5",  "na"],
        ["elem-b",   "v:right",    "35", "n",  "na", "30"],
    ]
    _, issues = validate_annotation_rows(rows, ["free", "dependent-on-left", "dependent-on-right"],
                                         "general", _FREE_PV)
    pos_issues = [i for i in issues if "dependent-on" in i.message and "unexpected value" in i.message]
    assert pos_issues == []


def test_non_integer_position_value_warns():
    """A non-integer, non-na value in dependent-on-left still triggers a warning."""
    rows = [
        _FREE_HEADER,
        ["KEYSTONE", "v:verbstem", "30", "na", "na",    "na"],
        ["elem-a",   "v:left",     "1",  "n",  "left",  "na"],
    ]
    _, issues = validate_annotation_rows(rows, ["free", "dependent-on-left", "dependent-on-right"],
                                         "general", _FREE_PV)
    assert any("unexpected value" in i.message and "dependent-on-left" in i.message for i in issues)
