"""free_occurrence spans with dependent-on lists (#318): `8|12|30` means any
one of those positions is enough for the element to surface."""
from __future__ import annotations

import pandas as pd
import pytest

from planars.free_occurrence import bound_keystone_span, derive_free_occurrence_spans
from planars.position_cells import position_numbers

_K = 10
_NAMES = {n: f"v:p{n}" for n in range(1, 21)}
_NAMES[_K] = "v:verbstem"
_COLS = ["free", "left-edge-of-free-form", "right-edge-of-free-form",
         "dependent-on-left", "dependent-on-right"]


def _derive(rows, ks_free="y", ks_left="na", ks_right="na", strict=True):
    data_df = pd.DataFrame([dict(zip(["Element", "Position_Number", *_COLS], r)) for r in rows])
    keystone_df = pd.DataFrame([{"Element": "STEM", "Position_Number": _K, "free": ks_free,
                                 "left-edge-of-free-form": "na", "right-edge-of-free-form": "na",
                                 "dependent-on-left": ks_left, "dependent-on-right": ks_right}])
    return derive_free_occurrence_spans(
        strict=strict, _data=(data_df, _K, _NAMES, _COLS, keystone_df))


@pytest.mark.parametrize("cell, numbers", [
    ("8|12|30", [8, 12, 30]), ("8 | 12", [8, 12]), ("5", [5]),
    ("na", []), ("NA", []), ("?", []), ("", []), (None, []),
])
def test_position_numbers_reads_a_bar_list(cell, numbers):
    assert position_numbers(cell) == (numbers, [])


@pytest.mark.parametrize("cell", ["3,4", "3|", "left", "3|x"])
def test_position_numbers_reports_anything_else(cell):
    numbers, problems = position_numbers(cell)
    assert numbers == [] and problems


def test_a_position_is_internal_when_its_list_includes_the_anchor():
    """Rule 3: the anchor anywhere in the list is enough."""
    result = _derive([
        ["pro", 5,  "n", "n", "na", "3|4", f"8|{_K}|12"],
        ["x",   15, "n", "na", "n", "na", "17|18"],
    ])
    assert result["free_occurrence_internal_positions"] == [5, _K]


def test_a_one_item_list_reads_as_before():
    result = _derive([["pro", 5, "n", "n", "na", "na", str(_K)]])
    assert result["maximal_span"] == (5, _K)


def test_bound_keystone_minimal_span_uses_the_nearest_listed_position():
    assert bound_keystone_span("3|7|5", "14|12|19", _K) == (7, 12)
    assert bound_keystone_span("na", "14|12", _K) == (_K, 12)
    assert bound_keystone_span("na", "na", _K) == (_K, _K)
    result = _derive([], ks_free="n", ks_left="3|7", ks_right="12|19")
    assert result["minimal_span"] == (7, 12)


def test_a_comma_raises_with_strict_and_is_unannotated_without():
    rows = [["pro", 5, "n", "n", "na", "na", f"8,{_K}"]]
    with pytest.raises(ValueError, match="not commas"):
        _derive(rows)
    result = _derive(rows, strict=False)
    assert result["missing_data"] == {"dependent-on-right": ["pro"]}
    assert result["free_occurrence_internal_positions"] == [_K]
