"""Tests for coding/validate_planar.py — planar structure TSV validation.

Covers the element-type classification checks added alongside
coding.make_forms.classify_element() (issue #249): unregistered ALL CAPS
labels must raise an error rather than silently defaulting, and the optional
Element_Types column must be checked for drift against a fresh recomputation.
"""
from __future__ import annotations

import pandas as pd
import pytest

from coding.validate_planar import validate_planar_df, _is_all_caps_token


def _base_rows(elements_row):
    """One keystone row plus one caller-supplied row, as a DataFrame."""
    rows = [
        {
            "Position": "1", "Position_Name": "v:verbstem", "Position_Type": "Slot",
            "Elements": "KEYSTONE", "Class_Type": "open",
        },
        elements_row,
    ]
    return pd.DataFrame(rows)


def _errors(df):
    return [i for i in validate_planar_df(df) if i.level == "error"]


def _warnings(df):
    return [i for i in validate_planar_df(df) if i.level == "warning"]


# ---------------------------------------------------------------------------
# _is_all_caps_token — Unicode-aware
# ---------------------------------------------------------------------------

def test_is_all_caps_token_unicode_aware():
    assert _is_all_caps_token("NP{S,A}")
    assert _is_all_caps_token("AD-S")
    assert not _is_all_caps_token("he")
    assert not _is_all_caps_token("наш")  # non-ASCII, not uppercase — must not raise/misfire
    assert not _is_all_caps_token("-ed")


# ---------------------------------------------------------------------------
# Unregistered ALL CAPS label -> error, not a silent default
# ---------------------------------------------------------------------------

def test_unregistered_all_caps_label_is_an_error():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "TOTALLYNEWLABEL", "Class_Type": "open",
    }
    df = _base_rows(row)
    errors = _errors(df)
    assert any("TOTALLYNEWLABEL" in e.message and "element_type registered" in e.message
                for e in errors)


def test_registered_label_is_not_an_error():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "NP{S,A}, PRON", "Class_Type": "open",
    }
    df = _base_rows(row)
    errors = _errors(df)
    assert not any("element_type registered" in e.message for e in errors)


# ---------------------------------------------------------------------------
# Element_Types drift
# ---------------------------------------------------------------------------

def test_element_types_absent_is_not_flagged():
    """No Element_Types column at all -> no drift errors (not yet backfilled, issue #249)."""
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "he, NP{S,A}", "Class_Type": "open",
    }
    df = _base_rows(row)
    assert not any("Element_Types" in e.message for e in _errors(df))


def test_element_types_matching_is_clean():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "he, NP{S,A}", "Class_Type": "open",
        "Element_Types": "formative, embedded_structure",
    }
    df = _base_rows(row)
    assert not any("Element_Types" in e.message for e in _errors(df))


def test_element_types_mismatch_is_an_error():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "he, NP{S,A}", "Class_Type": "open",
        "Element_Types": "embedded_structure, formative",  # swapped, wrong
    }
    df = _base_rows(row)
    errors = _errors(df)
    assert any("Element_Types" in e.message and "recomputing" in e.message for e in errors)


def test_element_types_count_mismatch_is_an_error():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "he, NP{S,A}", "Class_Type": "open",
        "Element_Types": "formative",  # only one, Elements has two
    }
    df = _base_rows(row)
    errors = _errors(df)
    assert any("stay aligned" in e.message for e in errors)


# ---------------------------------------------------------------------------
# Biuniqueness_Scope drift (issue #254 Part 2a)
# ---------------------------------------------------------------------------

def test_biuniqueness_scope_absent_is_not_flagged():
    """No Biuniqueness_Scope column at all -> no drift errors (not yet backfilled)."""
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "he, PRON, NP{S,A}", "Class_Type": "open",
    }
    df = _base_rows(row)
    assert not any("Biuniqueness_Scope" in e.message for e in _errors(df))


def test_biuniqueness_scope_matching_is_clean():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "he, PRON, NP{S,A}", "Class_Type": "open",
        "Biuniqueness_Scope": "filled, open_category, excluded",
    }
    df = _base_rows(row)
    assert not any("Biuniqueness_Scope" in e.message for e in _errors(df))


def test_biuniqueness_scope_mismatch_is_an_error():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "he, PRON, NP{S,A}", "Class_Type": "open",
        "Biuniqueness_Scope": "open_category, filled, excluded",  # first two swapped
    }
    df = _base_rows(row)
    errors = _errors(df)
    assert any("Biuniqueness_Scope" in e.message and "recomputing" in e.message for e in errors)


def test_biuniqueness_scope_count_mismatch_is_an_error():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "he, PRON, NP{S,A}", "Class_Type": "open",
        "Biuniqueness_Scope": "filled, open_category",  # only two, Elements has three
    }
    df = _base_rows(row)
    errors = _errors(df)
    assert any("stay aligned" in e.message for e in errors)


# ---------------------------------------------------------------------------
# Class_Type: mixed (issue #270) — an open category alongside an
# exhaustively-enumerated closed lexical set, no ALL-CAPS convention enforced
# ---------------------------------------------------------------------------

def test_mixed_is_a_valid_class_type():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "NP{S,A}, I, you, he, she, it, we, they", "Class_Type": "mixed",
    }
    df = _base_rows(row)
    assert not any("must be one of" in e.message for e in _errors(df))


def test_mixed_lowercase_elements_are_not_flagged_not_all_caps():
    """Regression for #270: 'mixed' must not trip the 'open' ALL-CAPS warning —
    that's exactly the bug that let a closed pronoun paradigm get mistaken for
    noise across multiple sessions."""
    row = {
        "Position": "2", "Position_Name": "v:npsubj1", "Position_Type": "Slot",
        "Elements": "NP{S,A}, I, you, he, she, it, we, they", "Class_Type": "mixed",
    }
    df = _base_rows(row)
    warnings = _warnings(df)
    assert not any("not ALL CAPS" in w.message for w in warnings)


def test_open_still_flags_the_same_lowercase_elements():
    """Confirms the fix is meaningful: the same row under 'open' still warns."""
    row = {
        "Position": "2", "Position_Name": "v:npsubj1", "Position_Type": "Slot",
        "Elements": "NP{S,A}, I, you, he, she, it, we, they", "Class_Type": "open",
    }
    df = _base_rows(row)
    warnings = _warnings(df)
    assert any("not ALL CAPS" in w.message and "'he'" in w.message for w in warnings)


# ---------------------------------------------------------------------------
# Class_Type: closed removed — folded into list (no minimum element count)
# ---------------------------------------------------------------------------

def test_closed_is_no_longer_a_valid_class_type():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "foo", "Class_Type": "closed",
    }
    df = _base_rows(row)
    errors = _errors(df)
    assert any("must be one of" in e.message and "closed" in e.message for e in errors)


def test_list_with_a_single_element_is_not_flagged():
    row = {
        "Position": "2", "Position_Name": "v:test", "Position_Type": "Slot",
        "Elements": "foo", "Class_Type": "list",
    }
    df = _base_rows(row)
    assert _errors(df) == []
    assert _warnings(df) == []
