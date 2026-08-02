"""Tests for the pure-logic pieces of coding/generate_biuniqueness_allomorphy_sheet.py
(issue #254 Part 2c).

No live Drive/Sheets API calls are made or mocked here — see the module's
docstring for why _get_or_create_allomorphy_spreadsheet/_write_prescreening_tab are
left untested (same convention as test_generate_status_sheet.py).
"""
from __future__ import annotations

import pandas as pd
import pytest

from coding.generate_biuniqueness_allomorphy_sheet import (
    _HEADER,
    _banner_rows,
    _build_prescreening_rows,
    _rows_to_sheet_values,
)


def _planar_df(rows):
    """Build a minimal planar DataFrame from (Position_Name, Elements, Biuniqueness_Scope) tuples."""
    return pd.DataFrame([
        {"Position_Name": pn, "Elements": elements, "Biuniqueness_Scope": scope}
        for pn, elements, scope in rows
    ])


# ---------------------------------------------------------------------------
# _build_prescreening_rows
# ---------------------------------------------------------------------------

def test_build_prescreening_rows_excludes_excluded_scope():
    df = _planar_df([
        ("v:verbstem", "KEYSTONE", "excluded"),
        ("v:npsubj1", "NP{S,A}, he", "excluded, filled"),
    ])
    rows = _build_prescreening_rows(df)
    assert rows == [{"position_name": "v:npsubj1", "element": "he", "scope": "filled"}]


def test_build_prescreening_rows_keeps_filled_and_open_category():
    df = _planar_df([
        ("v:leftedge", "and, CONJUNCT", "filled, open_category"),
    ])
    rows = _build_prescreening_rows(df)
    assert rows == [
        {"position_name": "v:leftedge", "element": "and", "scope": "filled"},
        {"position_name": "v:leftedge", "element": "CONJUNCT", "scope": "open_category"},
    ]


def test_build_prescreening_rows_missing_column_raises():
    df = pd.DataFrame([{"Position_Name": "v:leftedge", "Elements": "and"}])
    with pytest.raises(ValueError, match="Biuniqueness_Scope"):
        _build_prescreening_rows(df)


def test_build_prescreening_rows_token_count_mismatch_raises():
    df = _planar_df([("v:leftedge", "and, then", "filled")])  # only one scope, two elements
    with pytest.raises(ValueError, match="drifted|token"):
        _build_prescreening_rows(df)


def test_build_prescreening_rows_empty_elements_yields_no_rows():
    df = _planar_df([("v:leftedge", "", "")])
    assert _build_prescreening_rows(df) == []


# ---------------------------------------------------------------------------
# _rows_to_sheet_values
# ---------------------------------------------------------------------------

def test_rows_to_sheet_values_header():
    assert _rows_to_sheet_values([])[0] == _HEADER


def test_rows_to_sheet_values_blank_annotation_columns():
    rows = [{"position_name": "v:leftedge", "element": "and", "scope": "filled"}]
    values = _rows_to_sheet_values(rows)
    assert values[1] == ["v:leftedge", "and", "filled", "", "", ""]


def test_rows_to_sheet_values_row_count_matches_input():
    rows = [
        {"position_name": "v:leftedge", "element": "and", "scope": "filled"},
        {"position_name": "v:leftedge", "element": "CONJUNCT", "scope": "open_category"},
    ]
    values = _rows_to_sheet_values(rows)
    assert len(values) == len(rows) + 1  # + header


# ---------------------------------------------------------------------------
# _banner_rows
# ---------------------------------------------------------------------------

def test_banner_rows_mentions_both_scope_values():
    banner_text = " ".join(cell for row in _banner_rows() for cell in row)
    assert "filled" in banner_text
    assert "open_category" in banner_text
    assert "has_allomorphs" in banner_text
    assert "Members" in banner_text
