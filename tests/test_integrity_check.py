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
    _section_dependent_construction_staleness,
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


# ---------------------------------------------------------------------------
# _section_dependent_construction_staleness -- coreference's source_set
# (issue #285: this used to approximate "in scope" as any non-n/na row, a
# union, instead of matching _filter_reflex_pairs_by_prescreening's real
# element-level exclusion (any 'n' row poisons the whole element) -- a false
# "stale" report for any element referential=y at one position and
# referential=n at another, which is exactly synth0001's real data shape.
# ---------------------------------------------------------------------------

_COREFERENCE_DIAG_CLASSES = {
    "coreference": {
        "constructions": [
            {"name": "prescreening", "row_type": "element"},
            {"name": "reflexivization", "row_type": "pair_rows",
             "depends_on": "prescreening", "staleness_check": "element_set"},
        ],
        "required_criteria": [],
    }
}


_DEP_COLUMNS = ["Element_A", "Position_A", "Position_B", "Direction",
                "reflexive_allowed", "Source", "Comments"]


def _write_coreference_fixture(tmp_path, lang_id, prescreening_rows, dep_rows):
    d = tmp_path / lang_id / "coreference"
    d.mkdir(parents=True)
    pd.DataFrame(prescreening_rows).to_csv(d / "prescreening.tsv", sep="\t", index=False)
    # Explicit columns even when dep_rows is empty -- an empty DataFrame with
    # no columns writes a file pandas can't read back ("No columns to parse").
    pd.DataFrame(dep_rows, columns=_DEP_COLUMNS).to_csv(
        d / "reflexivization.tsv", sep="\t", index=False)
    # A matching planar, so _find_stale_position_cells (a separate check --
    # see its own module docstring) has real position names to compare
    # against instead of an empty dict, which would flag every position cell
    # as stale regardless of the element-set logic under test here.
    positions = sorted({int(r["Position_Number"]) for r in prescreening_rows})
    planar_dir = tmp_path / lang_id / "lang_setup"
    planar_dir.mkdir(parents=True)
    pd.DataFrame([
        {"Position": p, "Position_Name": next(
            r["Position_Name"] for r in prescreening_rows if int(r["Position_Number"]) == p)}
        for p in positions
    ]).to_csv(planar_dir / f"planar_{lang_id}.tsv", sep="\t", index=False)


def test_element_divergent_across_positions_is_not_reported_stale(tmp_path, monkeypatch, capsys):
    """The real filter excludes 'a' everywhere (one of its rows is n) -- so a
    pair tab correctly missing 'a' entirely is NOT stale, matching what
    --regen-construction would actually produce, not a naive union."""
    import coding.integrity_check as _ic
    monkeypatch.setattr(_ic, "CODED_DATA", tmp_path)
    _write_coreference_fixture(
        tmp_path, "lang0001",
        prescreening_rows=[
            {"Element": "a", "Position_Name": "p1", "Position_Number": "1", "referential": "n"},
            {"Element": "a", "Position_Name": "p2", "Position_Number": "2", "referential": "y"},
            {"Element": "b", "Position_Name": "p3", "Position_Number": "3", "referential": "y"},
        ],
        dep_rows=[
            {"Element_A": "b", "Position_A": "3 (p3)", "Position_B": "3 (p3)",
             "Direction": "same", "reflexive_allowed": "y", "Source": "", "Comments": ""},
        ],
    )
    total_e, total_w = _section_dependent_construction_staleness(["lang0001"], _COREFERENCE_DIAG_CLASSES)
    out = capsys.readouterr().out
    assert total_e == 0
    assert "✗" not in out


def test_element_genuinely_missing_is_still_reported_stale(tmp_path, monkeypatch, capsys):
    """Sanity check the fix didn't just silence the section outright: an
    element with no divergence, referential=y throughout, missing from the
    pair tab, is still a real staleness report. 'c' is already correctly
    paired so dep_set isn't empty -- an entirely empty dependent tab is its
    own "not yet populated, skip" case, not what this test is about."""
    import coding.integrity_check as _ic
    monkeypatch.setattr(_ic, "CODED_DATA", tmp_path)
    _write_coreference_fixture(
        tmp_path, "lang0001",
        prescreening_rows=[
            {"Element": "b", "Position_Name": "p3", "Position_Number": "3", "referential": "y"},
            {"Element": "c", "Position_Name": "p4", "Position_Number": "4", "referential": "y"},
        ],
        dep_rows=[
            {"Element_A": "c", "Position_A": "4 (p4)", "Position_B": "4 (p4)",
             "Direction": "same", "reflexive_allowed": "y", "Source": "", "Comments": ""},
        ],
    )
    total_e, total_w = _section_dependent_construction_staleness(["lang0001"], _COREFERENCE_DIAG_CLASSES)
    out = capsys.readouterr().out
    assert total_e == 1
    assert "✗" in out
    assert "now in scope but absent from pairs" in out
