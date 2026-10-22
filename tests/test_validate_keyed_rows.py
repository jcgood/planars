"""Validation of free-entry criteria and keyed-row tabs (biuniqueness_deviations, #254)."""
from __future__ import annotations

import pytest

from coding import validate_coding as vc

KEYED = ["Morpheme", "Position_Name", "Form", "Origin"]
PARAMS = ["occurs_here", "conditioning_type", "conditioning_features",
          "conditioned_by", "trigger_filled"]
VALUES = {"occurs_here": ["y", "n"],
          "conditioning_type": ["phonological", "morphosyntactic",
                                "lexico-constructional", "prosodic"],
          "conditioning_features": ["<free_text>"],
          "conditioned_by": ["<position_names>"],
          "trigger_filled": ["y", "n"]}
BLANK_OK = [{"occurs_here": "n"}, {"conditioning_features": "elsewhere"}]
HEADER = KEYED + PARAMS + ["Source", "Comments"]


@pytest.fixture(autouse=True)
def known_positions(monkeypatch):
    monkeypatch.setattr(vc, "_planar_position_names",
                        lambda lang: {"5": "v:npsubj1", "8": "v:modal1", "9": "v:neg1",
                                      "31": "v:verbinflection"})


def row(morpheme, pos, form, *vals):
    return [morpheme, pos, form, "filled", *vals, "", ""]


def validate(*rows):
    return vc.validate_keyed_rows([HEADER, *rows], KEYED, PARAMS, "morphs", VALUES, BLANK_OK,
                                  class_name="biuniqueness_deviations", lang_id="x")


def messages(issues):
    return [i.message for i in issues]


def test_a_complete_row_passes_and_free_text_is_kept_as_typed():
    records, issues = validate(
        row("will", "v:modal1", "won't", "Y", "Morphosyntactic", "Polarity=NEG", "v:neg1", "n"))
    assert issues == []
    assert records[0]["occurs_here"] == "y"                  # fixed values lowercased
    assert records[0]["conditioning_features"] == "Polarity=NEG"   # free text untouched
    assert records[0]["Form"] == "won't"


def test_conditioned_by_must_name_real_positions():
    _, issues = validate(
        row("will", "v:modal1", "'ll", "y", "prosodic", "host", "v:npsubj1, v:nowhere", "y"))
    assert any("not a position in the planar: v:nowhere" in m for m in messages(issues))


def test_a_position_number_is_answered_with_its_name():
    _, issues = validate(
        row("will", "v:modal1", "'ll", "y", "prosodic", "host", "5, 31", "y"))
    assert any("write position names, not numbers (5 is v:npsubj1, 31 is v:verbinflection)"
               in m for m in messages(issues))


def test_a_form_that_does_not_occur_needs_nothing_else():
    _, issues = validate(row("will", "v:frontedauxiliary", "'ll", "n", "", "", "", ""))
    assert issues == []


def test_the_elsewhere_form_needs_no_trigger():
    _, issues = validate(row("do", "v:frontedauxiliary", "do", "y", "morphosyntactic",
                             "elsewhere", "", ""))
    assert issues == []


def test_an_ordinary_row_left_blank_is_reported_blank():
    _, issues = validate(row("do", "v:frontedauxiliary", "does", "y", "", "person=3", "", ""))
    msgs = messages(issues)
    assert "blank value in 'conditioning_type'" in msgs
    assert "blank value in 'trigger_filled'" in msgs
    assert not any("conditioned_by" in m for m in msgs)       # free entry may be blank


def test_an_unknown_choice_is_reported_with_the_allowed_set():
    _, issues = validate(row("do", "v:frontedauxiliary", "does", "maybe", "morphosyntactic",
                             "person=3", "v:npsubj1", "y"))
    assert any("unexpected value 'maybe' in 'occurs_here'" in m for m in messages(issues))


def test_a_tab_whose_key_columns_are_wrong_is_reported_once():
    records, issues = vc.validate_keyed_rows(
        [["Element", "Position_Name", "x"], ["a", "b", "c"]], KEYED, PARAMS, "morphs", VALUES)
    assert len(issues) == 1 and "keyed rows (Morpheme, Position_Name, Form, Origin)" in issues[0].message
    assert records == [{"Element": "a", "Position_Name": "b", "x": "c"}]    # rows still returned


def test_completeness_does_not_count_blank_ok_rows_or_free_text():
    rows = [HEADER,
            row("will", "v:frontedauxiliary", "'ll", "n", "", "", "", ""),
            row("do", "v:frontedauxiliary", "does", "y", "morphosyntactic", "x", "v:npsubj1", "")]
    status = vc.keyed_annotation_status(rows, KEYED, PARAMS, VALUES, BLANK_OK)
    # row 1: only occurs_here counts (1 filled); row 2: three choice columns, one blank.
    assert status == {"total": 4, "filled": 3, "blank": 1, "invalid": 0}


def test_element_rows_keep_free_text_members_as_typed():
    header = ["Element", "Position_Name", "Position_Number",
              "has_allomorphs", "members", "co_exponents", "Source", "Comments"]
    rows = [header, ["be", "v:frontedauxiliary", "3", "Y", "Am, Are, Is", "", "", ""]]
    values = {"has_allomorphs": ["y", "n"], "members": ["<free_text>"],
              "co_exponents": ["<position_names>"]}
    records, issues = vc.validate_annotation_rows(
        rows, ["has_allomorphs", "members", "co_exponents"], "elements", values, lang_id="x")
    assert issues == []
    assert records[0]["members"] == "Am, Are, Is" and records[0]["has_allomorphs"] == "y"


def test_element_rows_check_co_exponent_positions():
    header = ["Element", "Position_Name", "Position_Number",
              "has_allomorphs", "co_exponents", "Source", "Comments"]
    rows = [header, ["be", "v:progressive", "22", "n", "v:verbinflexion", "", ""]]
    values = {"has_allomorphs": ["y", "n"], "co_exponents": ["<position_names>"]}
    _, issues = vc.validate_annotation_rows(rows, ["has_allomorphs", "co_exponents"],
                                            "elements", values, lang_id="x")
    assert any("v:verbinflexion" in i.message for i in issues)
