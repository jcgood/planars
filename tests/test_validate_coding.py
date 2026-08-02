"""Tests for coding/validate_coding.py — validate_annotation_rows."""
from __future__ import annotations

from coding.schemas import criterion_values
from coding.validate_coding import (
    _COREFERENCE_CONSTRUCTION_PARAMS,
    validate_annotation_rows,
    validate_pair_rows,
)


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


# ---------------------------------------------------------------------------
# Criterion values come from the schema, never restated in code
# ---------------------------------------------------------------------------

def test_criterion_values_reads_schema():
    assert criterion_values("reflexive_allowed") == ["y", "n", "untestable"]
    assert criterion_values("referential") == ["y", "n"]


def test_criterion_values_unknown_returns_none():
    """None rather than [] so callers can distinguish 'absent' from 'empty'."""
    assert criterion_values("no_such_criterion_anywhere") is None


def test_coreference_pair_params_carry_untestable():
    """Regression: these were hardcoded ["y", "n"], overriding the schema's
    [y, n, untestable]. Dropdowns are built from the per-language YAML and so
    offered "untestable", which validation then flagged pink."""
    for construction, crit in [
        ("reflexivization", "reflexive_allowed"),
        ("pronominalization", "pronoun_allowed"),
        ("np_reference", "np_allowed"),
    ]:
        vals = _COREFERENCE_CONSTRUCTION_PARAMS[construction]["values"][crit]
        assert "untestable" in vals, f"{construction}/{crit} lost untestable"


def test_coreference_prescreening_still_resolves():
    """prescreening is row_type: element and declares no `criterion` in
    diagnostic_classes.yaml, so the constructions loop does not pick it up.
    Without an explicit entry it falls through to the per-language param map
    and wrongly inherits all three pair criteria as its columns."""
    entry = _COREFERENCE_CONSTRUCTION_PARAMS["prescreening"]
    assert entry["params"] == ["referential"]
    assert entry["values"]["referential"] == ["y", "n"]


_PAIR_HEADER = ["Element_A", "Position_A", "Element_B", "Position_B",
                "Direction", "reflexive_allowed", "Source", "Comments"]


def _pair_rows(value: str) -> list[list[str]]:
    return [_PAIR_HEADER, ["a", "1", "b", "2", "A>B", value, "", ""]]


def test_untestable_accepted_on_coreference_pair_sheet():
    """End-to-end: the value the dropdown offers must validate cleanly."""
    info = _COREFERENCE_CONSTRUCTION_PARAMS["reflexivization"]
    _, issues = validate_pair_rows(_pair_rows("untestable"), info["params"],
                                   "reflexivization", info["values"])
    assert [i for i in issues if "unexpected value" in i.message] == []


def test_genuinely_invalid_value_still_rejected_on_pair_sheet():
    """Confirms the fix widened the allowed set rather than disabling the check."""
    info = _COREFERENCE_CONSTRUCTION_PARAMS["reflexivization"]
    _, issues = validate_pair_rows(_pair_rows("maybe"), info["params"],
                                   "reflexivization", info["values"])
    assert any("unexpected value" in i.message for i in issues)


# ---------------------------------------------------------------------------
# A sheet whose rows are not the shape the schema says (issue #275)
#
# stan1293's phrasal_accent/general has element rows while the schema says
# pair rows. The validator used to report that twice and then check all 142
# rows against a column map built for the other shape, objecting once per cell
# that element names and position numbers are not y/n — 2 real errors under
# 427 lines of noise.
# ---------------------------------------------------------------------------

_ELEMENT_SHAPED = [
    ["Element", "Position_Name", "Position_Number", "joint_accent", "Source", "Comments"],
    ["also", "v:leftedge", "1", "", "", ""],
    ["CONJUNCT", "v:leftedge", "1", "", "", ""],
]


def test_element_rows_where_pair_rows_are_expected_report_once():
    _, issues = validate_pair_rows(_ELEMENT_SHAPED, ["joint_accent"], "general")
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert "not the shape" in issues[0].message


def test_pair_rows_where_element_rows_are_expected_report_once():
    """The same mistake the other way round, which was equally unguarded."""
    _, issues = validate_annotation_rows(_pair_rows("y"), ["reflexive_allowed"],
                                         "reflexivization")
    assert len(issues) == 1
    assert issues[0].level == "error"


def test_the_error_says_which_command_would_rebuild_the_sheet():
    """Nobody should have to remember the flags from the message alone."""
    _, issues = validate_pair_rows(_ELEMENT_SHAPED, ["joint_accent"], "general",
                                   class_name="phrasal_accent", lang_id="stan1293")
    assert ("python -m coding generate-sheets --lang stan1293 "
            "--regen-construction phrasal_accent:general") in issues[0].message
    # And names the other possibility, since the schema may be the wrong one.
    assert "schemas/diagnostic_classes.yaml" in issues[0].message


def test_the_rows_still_come_back_untouched():
    """The reason this stops at reporting instead of returning nothing.

    import-sheets writes whatever the validator hands back straight to the
    TSV. Returning no rows for a mis-shaped sheet would empty a live
    annotation file — and 'CONJUNCT' must not come back lowercased either,
    which is what happened when its column was read as a criterion.
    """
    records, _ = validate_pair_rows(_ELEMENT_SHAPED, ["joint_accent"], "general")
    assert len(records) == len(_ELEMENT_SHAPED) - 1
    assert records[1]["Element"] == "CONJUNCT"
    assert records[0] == {"Element": "also", "Position_Name": "v:leftedge",
                          "Position_Number": "1", "joint_accent": "",
                          "Source": "", "Comments": ""}


def test_a_correctly_shaped_sheet_is_still_checked_cell_by_cell():
    """The stop only fires on a shape mismatch, not on a bad value."""
    info = _COREFERENCE_CONSTRUCTION_PARAMS["reflexivization"]
    _, issues = validate_pair_rows(_pair_rows("maybe"), info["params"],
                                   "reflexivization", info["values"])
    assert any("unexpected value" in i.message for i in issues)
