"""Tests for rename-map logic in restructure_sheets.py."""
from __future__ import annotations

import pytest

from coding.restructure_sheets import _compute_stats, _lookup_existing, _parse_flag_map


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _existing(*tuples):
    """Build an existing-annotations dict from (element, pos_name, {values}) tuples."""
    return {(el, pn): vals for el, pn, vals in tuples}


def _rows(*tuples):
    """Build a rows list from (element, pos_name, pos_num) tuples."""
    return [[el, pn, num] for el, pn, num in tuples]


# ---------------------------------------------------------------------------
# _parse_rename_map
# ---------------------------------------------------------------------------

FLAG = "--rename-map"


def test_parse_flag_map_empty():
    assert _parse_flag_map([], FLAG) == {}


def test_parse_flag_map_single():
    assert _parse_flag_map(["--rename-map", "old:new"], FLAG) == {"old": "new"}


def test_parse_flag_map_multiple():
    assert _parse_flag_map(["--rename-map", "a:b", "--rename-map", "c:d"], FLAG) == {"a": "b", "c": "d"}


def test_parse_flag_map_colon_in_new_name():
    assert _parse_flag_map(["--rename-map", "old:new:extra"], FLAG) == {"old": "new:extra"}


def test_parse_flag_map_ignores_other_flags():
    assert _parse_flag_map(["--apply", "--rename-map", "x:y"], FLAG) == {"x": "y"}


def test_parse_flag_map_missing_colon_raises():
    with pytest.raises(SystemExit):
        _parse_flag_map(["--rename-map", "nocolon"], FLAG)


# ---------------------------------------------------------------------------
# _lookup_existing
# ---------------------------------------------------------------------------

@pytest.fixture
def existing():
    return _existing(
        ("NP", "subj",     {"V-combines": "y"}),
        ("VP", "old-name", {"V-combines": "n"}),
    )


def test_lookup_existing_direct_match(existing):
    assert _lookup_existing("NP", "subj", existing, {}) == {"V-combines": "y"}


def test_lookup_existing_no_match(existing):
    assert _lookup_existing("VP", "new-name", existing, {}) is None


def test_lookup_existing_rename_match(existing):
    assert _lookup_existing("VP", "new-name", existing, {"new-name": "old-name"}) == {"V-combines": "n"}


def test_lookup_existing_rename_element_mismatch(existing):
    assert _lookup_existing("NP", "new-name", existing, {"new-name": "old-name"}) is None


def test_lookup_existing_direct_takes_priority(existing):
    assert _lookup_existing("NP", "subj", existing, {"subj": "old-name"}) == {"V-combines": "y"}


# ---------------------------------------------------------------------------
# _compute_stats — no rename
# ---------------------------------------------------------------------------

@pytest.fixture
def existing2():
    return _existing(
        ("NP",  "subj", {"p": "y"}),
        ("VP",  "obj",  {"p": "n"}),
        ("ADV", "gone", {"p": "y"}),
    )


@pytest.fixture
def rows2():
    return _rows(
        ("NP", "subj",    "1"),
        ("VP", "obj2",    "2"),
        ("PP", "new-pos", "3"),
    )


def test_compute_stats_no_rename_carried(existing2, rows2):
    carried, renamed, new, dropped = _compute_stats(rows2, existing2, {})
    assert carried == 1   # only subj matched directly


def test_compute_stats_no_rename_renamed(existing2, rows2):
    carried, renamed, new, dropped = _compute_stats(rows2, existing2, {})
    assert renamed == 0   # no rename map given


def test_compute_stats_no_rename_new(existing2, rows2):
    carried, renamed, new, dropped = _compute_stats(rows2, existing2, {})
    assert new == 2       # obj2 and new-pos are new


def test_compute_stats_no_rename_dropped(existing2, rows2):
    carried, renamed, new, dropped = _compute_stats(rows2, existing2, {})
    assert len(dropped) == 2
    assert ("VP", "obj")   in dropped
    assert ("ADV", "gone") in dropped


# ---------------------------------------------------------------------------
# _compute_stats — with rename map
# ---------------------------------------------------------------------------

def test_compute_stats_rename_carried(existing2, rows2):
    carried, renamed, new, dropped = _compute_stats(rows2, existing2, {"obj": "obj2"})
    assert carried == 1   # subj direct
    assert renamed == 1   # obj→obj2 via rename map


def test_compute_stats_rename_new(existing2, rows2):
    carried, renamed, new, dropped = _compute_stats(rows2, existing2, {"obj": "obj2"})
    assert new == 1       # only new-pos


def test_compute_stats_rename_dropped(existing2, rows2):
    carried, renamed, new, dropped = _compute_stats(rows2, existing2, {"obj": "obj2"})
    assert len(dropped) == 1
    assert ("ADV", "gone") in dropped
    assert ("VP", "obj")   not in dropped


# ---------------------------------------------------------------------------
# _compute_stats — unmatched rename
# ---------------------------------------------------------------------------

def test_compute_stats_unmatched_rename(existing2, rows2):
    carried, renamed, new, dropped = _compute_stats(rows2, existing2, {"obj": "obj2", "ghost": "other"})
    assert carried == 1
    assert renamed == 1
    assert new == 1
