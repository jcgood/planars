"""Tests for coding/integrity_check.py's position-number drift detection.

Covers _find_stale_position_cells / _suggest_position_remap / _planar_position_names
(issue #241 follow-up): a pair-row can be element-identity-correct and still
reference a position by a number that's since been superseded by a structural
insertion/deletion elsewhere in the planar -- invisible to element-set
comparison alone. Discovered 2026-07-31 via stan1293's coreference pairs
referencing v:obj-part/v:rec by pre-v:obj-R-insertion position numbers.

Also covers the pair-tab row comparison in
_section_dependent_construction_staleness (below).
"""
from __future__ import annotations

import pandas as pd

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
# _section_dependent_construction_staleness -- pair tabs are compared with
# the rows the generator would make now (sheet_spec.expected_row_keys), not
# with a copy of each class's scope rule. The copy went wrong twice: #285
# (coreference) and 2026-10-27 (phrasal_accent's adjacency step, which made
# it report 17 elements "missing" that the generator rightly leaves out, and
# hid 38 real missing coreference pairs at a newly referential position).
# ---------------------------------------------------------------------------

_DIAG_CLASSES = {
    "coreference": {
        "constructions": [
            {"name": "prescreening", "row_type": "element"},
            {"name": "reflexive_coreference", "row_type": "pair_rows",
             "depends_on": "prescreening", "staleness_check": "element_set"},
        ],
    }
}
_KEY = ("Element_A", "Position_A", "Position_B", "Direction")
_DEP_COLUMNS = list(_KEY) + ["reflexive_allowed", "Example", "Source", "Comments"]


def _setup(tmp_path, monkeypatch, dep_rows, generated):
    """A prescreening TSV, a pair TSV holding `dep_rows`, a planar, and the
    generator stubbed to return `generated` (a set of row keys, or None)."""
    from types import SimpleNamespace
    import coding.integrity_check as _ic
    monkeypatch.setattr(_ic, "CODED_DATA", tmp_path)
    d = tmp_path / "lang0001" / "coreference"
    d.mkdir(parents=True)
    pd.DataFrame([{"Element": "b", "Position_Name": "p3", "Position_Number": "3",
                   "referential": "y"}]).to_csv(d / "prescreening.tsv", sep="\t", index=False)
    pd.DataFrame(dep_rows, columns=_DEP_COLUMNS).to_csv(
        d / "reflexive_coreference.tsv", sep="\t", index=False)
    setup = tmp_path / "lang0001" / "lang_setup"
    setup.mkdir(parents=True)
    pd.DataFrame([{"Position": 3, "Position_Name": "p3"}, {"Position": 4, "Position_Name": "p4"}]
                 ).to_csv(setup / "planar_lang0001.tsv", sep="\t", index=False)
    tab = SimpleNamespace(row_key=_KEY)
    monkeypatch.setattr(_ic, "class_sheet_spec",
                        lambda lang, cls, data: SimpleNamespace(tab=lambda name: tab))
    monkeypatch.setattr(_ic, "expected_row_keys",
                        lambda lang, cls, t, data: None if generated is None
                        else frozenset(generated))


def _row(a, pa, pb, d):
    return {"Element_A": a, "Position_A": pa, "Position_B": pb, "Direction": d,
            "reflexive_allowed": "y", "Example": "", "Source": "", "Comments": ""}


def test_tab_matching_the_generator_is_clean(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, [_row("b", "3 (p3)", "4 (p4)", "forward")],
           {("b", "3 (p3)", "4 (p4)", "forward")})
    total_e, _ = _section_dependent_construction_staleness(["lang0001"], _DIAG_CLASSES)
    assert total_e == 0
    assert "✗" not in capsys.readouterr().out


def test_pairs_the_generator_now_makes_are_reported(tmp_path, monkeypatch, capsys):
    """An element already paired at one position, newly answered at another:
    an element-set comparison could not see this."""
    _setup(tmp_path, monkeypatch, [_row("b", "3 (p3)", "4 (p4)", "forward")],
           {("b", "3 (p3)", "4 (p4)", "forward"), ("b", "4 (p4)", "3 (p3)", "backward")})
    total_e, _ = _section_dependent_construction_staleness(["lang0001"], _DIAG_CLASSES)
    out = capsys.readouterr().out
    assert total_e == 1
    assert "pairs the source now calls for (1): ['b / 4 (p4) / 3 (p3) / backward']" in out
    assert "--regen-construction coreference:reflexive_coreference" in out


def test_pairs_the_generator_no_longer_makes_are_reported(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, [_row("b", "3 (p3)", "4 (p4)", "forward"),
                                   _row("b", "4 (p4)", "3 (p3)", "backward")],
           {("b", "3 (p3)", "4 (p4)", "forward")})
    total_e, _ = _section_dependent_construction_staleness(["lang0001"], _DIAG_CLASSES)
    assert total_e == 1
    assert "pairs the source no longer calls for (1)" in capsys.readouterr().out


def test_generator_refusing_to_guess_is_a_warning_not_an_error(tmp_path, monkeypatch, capsys):
    """An element answered differently at two positions: the generator won't
    pick (#285), so the tab is not compared and nothing is called stale."""
    _setup(tmp_path, monkeypatch, [_row("b", "3 (p3)", "4 (p4)", "forward")], None)
    total_e, _ = _section_dependent_construction_staleness(["lang0001"], _DIAG_CLASSES)
    out = capsys.readouterr().out
    assert total_e == 0
    assert "not compared" in out and "✗" not in out


