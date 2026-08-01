"""Tests for coding/integrity_check.py's position-number drift detection.

Covers _find_stale_position_cells / _suggest_position_remap / _planar_position_names
(issue #241 follow-up): a pair-row can be element-identity-correct and still
reference a position by a number that's since been superseded by a structural
insertion/deletion elsewhere in the planar -- invisible to element-set
comparison alone. Discovered 2026-07-31 via stan1293's coreference pairs
referencing v:obj-part/v:rec by pre-v:obj-R-insertion position numbers.
"""
from __future__ import annotations

import pandas as pd
import pytest

from coding.integrity_check import (
    _find_stale_position_cells,
    _planar_position_names,
    _suggest_position_remap,
)


# ---------------------------------------------------------------------------
# _find_stale_position_cells
# ---------------------------------------------------------------------------

def test_find_stale_position_cells_detects_mismatch():
    df = pd.DataFrame([
        {"Position_A": "5 (v:npsubj1)", "Position_B": "33 (v:obj-part)"},
    ])
    names = {5: "v:npsubj1", 34: "v:obj-part"}  # obj-part is now 34, not 33
    stale = _find_stale_position_cells(df, names)
    assert stale == [(33, "v:obj-part")]


def test_find_stale_position_cells_matching_is_clean():
    df = pd.DataFrame([
        {"Position_A": "5 (v:npsubj1)", "Position_B": "34 (v:obj-part)"},
    ])
    names = {5: "v:npsubj1", 34: "v:obj-part"}
    assert _find_stale_position_cells(df, names) == []


def test_find_stale_position_cells_deduplicates():
    df = pd.DataFrame([
        {"Position_A": "5 (v:npsubj1)", "Position_B": "33 (v:obj-part)"},
        {"Position_A": "5 (v:npsubj1)", "Position_B": "33 (v:obj-part)"},
        {"Position_A": "5 (v:npsubj1)", "Position_B": "33 (v:obj-part)"},
    ])
    names = {5: "v:npsubj1", 34: "v:obj-part"}
    assert _find_stale_position_cells(df, names) == [(33, "v:obj-part")]


def test_find_stale_position_cells_missing_columns_is_noop():
    df = pd.DataFrame([{"Element_A": "and", "Element_B": "not"}])
    assert _find_stale_position_cells(df, {1: "v:leftedge"}) == []


def test_find_stale_position_cells_unparseable_cell_is_skipped():
    df = pd.DataFrame([{"Position_A": "garbage", "Position_B": "34 (v:obj-part)"}])
    names = {34: "v:obj-part"}
    assert _find_stale_position_cells(df, names) == []


def test_find_stale_position_cells_position_removed_entirely():
    df = pd.DataFrame([{"Position_A": "5 (v:npsubj1)", "Position_B": "99 (v:ghost)"}])
    names = {5: "v:npsubj1"}  # position 99 doesn't exist at all
    assert _find_stale_position_cells(df, names) == [(99, "v:ghost")]


# ---------------------------------------------------------------------------
# _suggest_position_remap
# ---------------------------------------------------------------------------

def test_suggest_position_remap_recoverable_case():
    stale = [(33, "v:obj-part"), (34, "v:rec")]
    names = {34: "v:obj-part", 35: "v:rec"}
    remap, unresolvable = _suggest_position_remap(stale, names)
    assert remap == {33: 34, 34: 35}
    assert unresolvable == []


def test_suggest_position_remap_unresolvable_case():
    stale = [(99, "v:ghost")]
    names = {5: "v:npsubj1"}  # v:ghost doesn't exist anywhere current
    remap, unresolvable = _suggest_position_remap(stale, names)
    assert remap == {}
    assert unresolvable == [(99, "v:ghost")]


def test_suggest_position_remap_mixed():
    stale = [(33, "v:obj-part"), (99, "v:ghost")]
    names = {34: "v:obj-part"}
    remap, unresolvable = _suggest_position_remap(stale, names)
    assert remap == {33: 34}
    assert unresolvable == [(99, "v:ghost")]


def test_suggest_position_remap_empty_input():
    assert _suggest_position_remap([], {1: "v:leftedge"}) == ({}, [])


# ---------------------------------------------------------------------------
# _planar_position_names
# ---------------------------------------------------------------------------

def test_planar_position_names_reads_current_planar(tmp_path, monkeypatch):
    import coding.integrity_check as _ic
    monkeypatch.setattr(_ic, "CODED_DATA", tmp_path)
    lang_dir = tmp_path / "lang0001" / "lang_setup"
    lang_dir.mkdir(parents=True)
    pd.DataFrame([
        {"Position": "1", "Position_Name": "v:leftedge"},
        {"Position": "2", "Position_Name": "v:verbstem"},
    ]).to_csv(lang_dir / "planar_lang0001.tsv", sep="\t", index=False)
    assert _planar_position_names("lang0001") == {1: "v:leftedge", 2: "v:verbstem"}


def test_planar_position_names_missing_file_returns_empty(tmp_path, monkeypatch):
    import coding.integrity_check as _ic
    monkeypatch.setattr(_ic, "CODED_DATA", tmp_path)
    assert _planar_position_names("nonexistent_lang") == {}
