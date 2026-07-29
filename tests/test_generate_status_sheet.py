"""Tests for the pure-logic pieces of coding/generate_status_sheet.py.

Covers the completeness-to-color/text mapping and the row-skeleton builder.
No live Drive/Sheets API calls are made or mocked here — see
coding/generate_status_sheet.py's module docstring for why those pieces
(_gather_status_rows, _write_status_sheet, locking) are left untested.
"""
from __future__ import annotations

from coding.generate_status_sheet import (
    _GRAY,
    _GREEN,
    _YELLOW,
    _build_row_skeletons,
    _completeness_pct,
    _missing_sheet_status,
    _row_status,
    _status_color,
    _status_text,
)


# ---------------------------------------------------------------------------
# _completeness_pct
# ---------------------------------------------------------------------------

def test_completeness_pct_basic():
    assert _completeness_pct(50, 100) == 50.0


def test_completeness_pct_full():
    assert _completeness_pct(10, 10) == 100.0


def test_completeness_pct_zero_total_is_none():
    assert _completeness_pct(0, 0) is None


def test_completeness_pct_negative_total_is_none():
    # Defensive: total should never be negative in practice, but guard anyway.
    assert _completeness_pct(0, -1) is None


# ---------------------------------------------------------------------------
# _status_color
# ---------------------------------------------------------------------------

def test_status_color_none_is_gray():
    assert _status_color(None) == _GRAY


def test_status_color_below_100_is_yellow():
    assert _status_color(0) == _YELLOW
    assert _status_color(50) == _YELLOW
    assert _status_color(75) == _YELLOW
    assert _status_color(89.9) == _YELLOW
    assert _status_color(99.9) == _YELLOW


def test_status_color_90_boundary_is_yellow():
    # 90% used to be the green cutoff; it no longer is -- only 100% is green.
    assert _status_color(90) == _YELLOW


def test_status_color_100_is_green():
    assert _status_color(100) == _GREEN


# ---------------------------------------------------------------------------
# _status_text
# ---------------------------------------------------------------------------

def test_status_text_basic_format():
    assert _status_text(128, 142) == "128/142 filled (90%)"


def test_status_text_rounds_percentage():
    # 1/3 = 33.33...% -> rounds to 33%
    assert _status_text(1, 3) == "1/3 filled (33%)"


def test_status_text_zero_total():
    assert _status_text(0, 0) == "0/0 filled (n/a)"


def test_status_text_fully_complete():
    assert _status_text(10, 10) == "10/10 filled (100%)"


def test_status_text_fully_blank():
    assert _status_text(0, 10) == "0/10 filled (0%)"


# ---------------------------------------------------------------------------
# _row_status
# ---------------------------------------------------------------------------

def test_row_status_pair_ignores_status_dict():
    text, color = _row_status(True, {"total": 100, "filled": 3, "blank": 97, "invalid": 0})
    assert text == "pair-row tab"
    assert color == _GRAY


def test_row_status_element_row_uses_status_dict():
    # 128/142 is 90.1% -- not fully complete, so yellow, not green.
    text, color = _row_status(False, {"total": 142, "filled": 128, "blank": 14, "invalid": 0})
    assert text == "128/142 filled (90%)"
    assert color == _YELLOW


def test_row_status_element_row_fully_complete_is_green():
    text, color = _row_status(False, {"total": 100, "filled": 100, "blank": 0, "invalid": 0})
    assert text == "100/100 filled (100%)"
    assert color == _GREEN


def test_row_status_element_row_low_completeness_is_yellow():
    text, color = _row_status(False, {"total": 100, "filled": 10, "blank": 90, "invalid": 0})
    assert text == "10/100 filled (10%)"
    assert color == _YELLOW


def test_row_status_element_row_missing_keys_defaults_to_zero():
    text, color = _row_status(False, {})
    assert text == "0/0 filled (n/a)"
    assert color == _GRAY


# ---------------------------------------------------------------------------
# _missing_sheet_status
# ---------------------------------------------------------------------------

def test_missing_sheet_status():
    text, color = _missing_sheet_status()
    assert text == "no sheet found"
    assert color == _GRAY


# ---------------------------------------------------------------------------
# _build_row_skeletons
# ---------------------------------------------------------------------------

def _spec(class_name, construction, params=None, values=None):
    return (class_name, construction, params or [], values or {})


def test_build_row_skeletons_preserves_order():
    specs = [
        _spec("ciscategorial", "general"),
        _spec("nonpermutability", "element_prescreening"),
        _spec("nonpermutability", "general"),
    ]
    skeletons = _build_row_skeletons(specs, {})
    assert [s["construction"] for s in skeletons] == ["general", "element_prescreening", "general"]
    assert [s["class_name"] for s in skeletons] == ["ciscategorial", "nonpermutability", "nonpermutability"]


def test_build_row_skeletons_marks_pair_row_constructions():
    specs = [
        _spec("nonpermutability", "element_prescreening"),
        _spec("nonpermutability", "general"),
        _spec("coreference", "prescreening"),
        _spec("coreference", "reflexivization"),
    ]
    pair_row_constructions = {
        "nonpermutability": {"general"},
        "coreference": {"reflexivization", "pronominalization", "np_reference"},
    }
    skeletons = _build_row_skeletons(specs, pair_row_constructions)
    is_pair_by_construction = {s["construction"]: s["is_pair"] for s in skeletons}
    assert is_pair_by_construction["element_prescreening"] is False
    assert is_pair_by_construction["general"] is True
    assert is_pair_by_construction["prescreening"] is False
    assert is_pair_by_construction["reflexivization"] is True


def test_build_row_skeletons_no_pair_map_defaults_to_element_rows():
    specs = [_spec("ciscategorial", "general")]
    skeletons = _build_row_skeletons(specs, {})
    assert skeletons[0]["is_pair"] is False


def test_build_row_skeletons_carries_param_names_and_values():
    specs = [_spec("ciscategorial", "general", ["V-combines"], {"V-combines": ["y", "n"]})]
    skeletons = _build_row_skeletons(specs, {})
    assert skeletons[0]["param_names"] == ["V-combines"]
    assert skeletons[0]["param_values"] == {"V-combines": ["y", "n"]}
