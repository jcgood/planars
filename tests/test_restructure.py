"""Tests for rename-map and rename-class logic in restructure_sheets.py."""
from __future__ import annotations

import pytest

from coding.restructure_sheets import (
    _apply_rename_to_position_cell,
    _apply_split_to_pair_rows,
    _cascade_rename_pair_tsv,
    _compute_stats,
    _count_pair_rename_impacts,
    _describe_split_impacts,
    _get_pair_row_constructions,
    _lookup_existing,
    _parse_flag_map,
    _parse_position_cell,
    _parse_split_flag_map,
    _pair_construction_criterion,
    _preflight_rename_class,
)


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
# _parse_split_flag_map
# ---------------------------------------------------------------------------

SPLIT_FLAG = "--split-element"


def test_parse_split_flag_map_empty():
    assert _parse_split_flag_map([], SPLIT_FLAG) == {}


def test_parse_split_flag_map_basic():
    result = _parse_split_flag_map(["--split-element", "PRON:me,you,him"], SPLIT_FLAG)
    assert result == {"PRON": ["me", "you", "him"]}


def test_parse_split_flag_map_strips_whitespace():
    result = _parse_split_flag_map(["--split-element", "PRON: me , you ,him"], SPLIT_FLAG)
    assert result == {"PRON": ["me", "you", "him"]}


def test_parse_split_flag_map_multiple_occurrences():
    result = _parse_split_flag_map(
        ["--split-element", "A:a1,a2", "--split-element", "B:b1,b2"], SPLIT_FLAG
    )
    assert result == {"A": ["a1", "a2"], "B": ["b1", "b2"]}


def test_parse_split_flag_map_missing_colon_raises():
    with pytest.raises(SystemExit):
        _parse_split_flag_map(["--split-element", "nocolon"], SPLIT_FLAG)


def test_parse_split_flag_map_single_target_raises():
    """A single replacement is a rename, not a split — should point at --rename-element."""
    with pytest.raises(SystemExit):
        _parse_split_flag_map(["--split-element", "PRON:me"], SPLIT_FLAG)


def test_parse_split_flag_map_ignores_other_flags():
    result = _parse_split_flag_map(["--apply", "--split-element", "A:a1,a2"], SPLIT_FLAG)
    assert result == {"A": ["a1", "a2"]}


# ---------------------------------------------------------------------------
# _describe_split_impacts
# ---------------------------------------------------------------------------

def test_describe_split_impacts_reports_when_old_had_data():
    existing = _existing(("PRON{P,T}", "v:obj-part", {"free": "y"}))
    rows = _rows(
        ("NP{P,T}", "v:obj-part", "34"),
        ("me", "v:obj-part", "34"),
        ("you", "v:obj-part", "34"),
    )
    lines = _describe_split_impacts(rows, existing, {"PRON{P,T}": ["me", "you", "him"]})
    assert len(lines) == 1
    assert "PRON{P,T} -> me, you, him" in lines[0]
    assert "2 new" in lines[0]
    assert "breadcrumbed" in lines[0]


def test_describe_split_impacts_silent_when_old_had_no_data():
    existing = _existing(("NP{P,T}", "v:obj-part", {"free": "y"}))
    rows = _rows(("me", "v:obj-part", "34"), ("you", "v:obj-part", "34"))
    lines = _describe_split_impacts(rows, existing, {"PRON{P,T}": ["me", "you"]})
    assert lines == []


def test_describe_split_impacts_no_split_map():
    existing = _existing(("PRON{P,T}", "v:obj-part", {"free": "y"}))
    rows = _rows(("me", "v:obj-part", "34"))
    assert _describe_split_impacts(rows, existing, {}) == []


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


# ---------------------------------------------------------------------------
# _preflight_rename_class
# ---------------------------------------------------------------------------

def _make_planar_file(tmp_path, lang_id: str) -> "Path":
    """Create a minimal planar file so _infer_language_id_from_planar_filename works."""
    f = tmp_path / f"planar_{lang_id}-20260101.tsv"
    f.write_text("Position_Number\tPosition_Name\n1\tv:verbstem\n")
    return f


def _make_diagnostics(tmp_path, lang_id: str, classes: list[str]) -> None:
    """Write a minimal diagnostics_{lang_id}.tsv with the given class names."""
    lines = ["Class\tLanguage\tConstructions\tCriteria"]
    for cls in classes:
        lines.append(f"{cls}\t{lang_id}\tgeneral\tfree")
    (tmp_path / f"diagnostics_{lang_id}.tsv").write_text("\n".join(lines) + "\n")


@pytest.fixture
def lang_id():
    return "test1234"


@pytest.fixture
def manifest_with_old(lang_id):
    """Manifest where lang has 'old_class' but not 'new_class'."""
    return {lang_id: {"sheets": {"old_class": {"spreadsheet_id": "abc"}}}}


def test_preflight_passes_when_new_in_diagnostics_old_absent(tmp_path, lang_id, manifest_with_old):
    """No error when diagnostics has new_class and old_class is gone."""
    _make_diagnostics(tmp_path, lang_id, ["new_class"])
    planar = _make_planar_file(tmp_path, lang_id)
    _preflight_rename_class(manifest_with_old, {"old_class": "new_class"}, [planar])  # should not raise


def test_preflight_errors_when_old_still_in_diagnostics(tmp_path, lang_id, manifest_with_old):
    """Abort when old class still present in diagnostics (coordinator forgot to update)."""
    _make_diagnostics(tmp_path, lang_id, ["old_class", "new_class"])
    planar = _make_planar_file(tmp_path, lang_id)
    with pytest.raises(SystemExit):
        _preflight_rename_class(manifest_with_old, {"old_class": "new_class"}, [planar])


def test_preflight_errors_when_new_absent_from_diagnostics(tmp_path, lang_id, manifest_with_old):
    """Abort when new class is missing from diagnostics (coordinator forgot to add it)."""
    _make_diagnostics(tmp_path, lang_id, ["other_class"])
    planar = _make_planar_file(tmp_path, lang_id)
    with pytest.raises(SystemExit):
        _preflight_rename_class(manifest_with_old, {"old_class": "new_class"}, [planar])


def test_preflight_skips_language_with_no_involvement(tmp_path, lang_id):
    """No error for a language that has neither old class in manifest nor new class in diagnostics."""
    manifest = {lang_id: {"sheets": {"unrelated_class": {}}}}
    _make_diagnostics(tmp_path, lang_id, ["unrelated_class"])
    planar = _make_planar_file(tmp_path, lang_id)
    _preflight_rename_class(manifest, {"old_class": "new_class"}, [planar])  # should not raise


def test_preflight_parse_rename_class_flag():
    """--rename-class uses the same _parse_flag_map as --rename-map."""
    result = _parse_flag_map(["--rename-class", "stress:metrical"], "--rename-class")
    assert result == {"stress": "metrical"}


# ---------------------------------------------------------------------------
# _parse_position_cell
# ---------------------------------------------------------------------------

def test_parse_position_cell_typical():
    assert _parse_position_cell("5 (v:npsubj1)") == (5, "v:npsubj1")


def test_parse_position_cell_leading_zeros_not_expected():
    assert _parse_position_cell("30 (v:verbstem)") == (30, "v:verbstem")


def test_parse_position_cell_name_with_colon():
    assert _parse_position_cell("12 (v:obj:dative)") == (12, "v:obj:dative")


def test_parse_position_cell_plain_number_fails():
    assert _parse_position_cell("5") is None


def test_parse_position_cell_empty_fails():
    assert _parse_position_cell("") is None


def test_parse_position_cell_no_parens_fails():
    assert _parse_position_cell("5 v:npsubj1") is None


def test_parse_position_cell_extra_whitespace():
    assert _parse_position_cell("  7 (v:aux)  ") == (7, "v:aux")


# ---------------------------------------------------------------------------
# _apply_rename_to_position_cell
# ---------------------------------------------------------------------------

def test_apply_rename_changes_name():
    new_cell, changed = _apply_rename_to_position_cell("5 (v:npsubj1)", {"v:npsubj1": "v:subj1"})
    assert new_cell == "5 (v:subj1)"
    assert changed is True


def test_apply_rename_number_preserved():
    new_cell, _ = _apply_rename_to_position_cell("34 (v:npobj1)", {"v:npobj1": "v:obj1"})
    assert new_cell.startswith("34 ")


def test_apply_rename_no_match_unchanged():
    new_cell, changed = _apply_rename_to_position_cell("5 (v:npsubj1)", {"v:other": "v:new"})
    assert new_cell == "5 (v:npsubj1)"
    assert changed is False


def test_apply_rename_unparseable_unchanged():
    new_cell, changed = _apply_rename_to_position_cell("", {"v:old": "v:new"})
    assert new_cell == ""
    assert changed is False


# ---------------------------------------------------------------------------
# _cascade_rename_pair_tsv
# ---------------------------------------------------------------------------

def _make_pair_tsv(tmp_path, rows):
    """Write a minimal pair TSV and return its path."""
    import pandas as pd
    p = tmp_path / "reflexivization.tsv"
    df = pd.DataFrame(rows)
    df.to_csv(p, sep="\t", index=False)
    return p


def test_cascade_rename_pair_tsv_updates_position_a(tmp_path):
    p = _make_pair_tsv(tmp_path, [
        {"Element_A": "NP", "Position_A": "5 (v:npsubj1)", "Position_B": "34 (v:npobj1)",
         "Direction": "forward", "reflexive_allowed": "y"},
    ])
    changed = _cascade_rename_pair_tsv(p, {"v:npsubj1": "v:subj1"})
    assert changed == 1
    import pandas as pd
    df = pd.read_csv(p, sep="\t", dtype=str, keep_default_na=False)
    assert df["Position_A"].iloc[0] == "5 (v:subj1)"
    assert df["Position_B"].iloc[0] == "34 (v:npobj1)"  # untouched


def test_cascade_rename_pair_tsv_updates_position_b(tmp_path):
    p = _make_pair_tsv(tmp_path, [
        {"Element_A": "NP", "Position_A": "5 (v:npsubj1)", "Position_B": "34 (v:npobj1)",
         "Direction": "forward", "reflexive_allowed": "y"},
    ])
    changed = _cascade_rename_pair_tsv(p, {"v:npobj1": "v:obj1"})
    assert changed == 1
    import pandas as pd
    df = pd.read_csv(p, sep="\t", dtype=str, keep_default_na=False)
    assert df["Position_B"].iloc[0] == "34 (v:obj1)"


def test_cascade_rename_pair_tsv_both_columns(tmp_path):
    p = _make_pair_tsv(tmp_path, [
        {"Element_A": "NP", "Position_A": "5 (v:npsubj1)", "Position_B": "34 (v:npobj1)",
         "Direction": "forward", "reflexive_allowed": "y"},
        {"Element_A": "VP", "Position_A": "5 (v:npsubj1)", "Position_B": "20 (v:aux)",
         "Direction": "forward", "reflexive_allowed": "n"},
    ])
    changed = _cascade_rename_pair_tsv(p, {"v:npsubj1": "v:subj1", "v:npobj1": "v:obj1"})
    assert changed == 3  # 2 Position_A cells + 1 Position_B cell


def test_cascade_rename_pair_tsv_no_match(tmp_path):
    p = _make_pair_tsv(tmp_path, [
        {"Element_A": "NP", "Position_A": "5 (v:npsubj1)", "Position_B": "34 (v:npobj1)",
         "Direction": "forward", "reflexive_allowed": "y"},
    ])
    changed = _cascade_rename_pair_tsv(p, {"v:other": "v:new"})
    assert changed == 0


def test_cascade_rename_pair_tsv_missing_file(tmp_path):
    missing = tmp_path / "nonexistent.tsv"
    assert _cascade_rename_pair_tsv(missing, {"v:old": "v:new"}) == 0


def test_count_pair_rename_impacts(tmp_path):
    p = _make_pair_tsv(tmp_path, [
        {"Element_A": "NP", "Position_A": "5 (v:npsubj1)", "Position_B": "34 (v:npobj1)",
         "Direction": "forward", "reflexive_allowed": "y"},
        {"Element_A": "VP", "Position_A": "5 (v:npsubj1)", "Position_B": "20 (v:aux)",
         "Direction": "forward", "reflexive_allowed": "n"},
    ])
    assert _count_pair_rename_impacts(p, {"v:npsubj1": "v:subj1"}) == 2
    assert _count_pair_rename_impacts(p, {"v:npsubj1": "v:subj1", "v:npobj1": "v:obj1"}) == 3
    assert _count_pair_rename_impacts(p, {"v:other": "v:new"}) == 0


# ---------------------------------------------------------------------------
# _pair_construction_criterion
# ---------------------------------------------------------------------------

def test_pair_construction_criterion_coreference():
    assert _pair_construction_criterion("coreference", "reflexivization") == "reflexive_allowed"
    assert _pair_construction_criterion("coreference", "pronominalization") == "pronoun_allowed"
    assert _pair_construction_criterion("coreference", "np_reference") == "np_allowed"


def test_pair_construction_criterion_nonpermutability():
    assert _pair_construction_criterion("nonpermutability", "general") == "scopal"


def test_pair_construction_criterion_unknown_returns_none():
    assert _pair_construction_criterion("nonpermutability", "nonexistent") is None
    assert _pair_construction_criterion("nonexistent_class", "general") is None


# ---------------------------------------------------------------------------
# _apply_split_to_pair_rows (issue #241's resolved design, policy (b))
# ---------------------------------------------------------------------------

_COREF_HEADER = ["Element_A", "Position_A", "Position_B", "Direction", "reflexive_allowed", "Source", "Comments"]
_NONPERM_HEADER = ["Element_A", "Element_B", "scopal", "Source", "Comments"]


def test_apply_split_element_a_side_coreference_shape_fans_out_blank():
    # Real-world shape: the citation lives in Source (index 5), Comments (index 6)
    # starts empty -- matches the actual stan1293 PRON{P,T} reflexivization row.
    rows = [
        ["PRON{P,T}", "33 (v:obj-part)", "34 (v:rec)", "forward", "y",
         "Lasnik example", ""],
    ]
    new_rows, fanned, manual = _apply_split_to_pair_rows(
        _COREF_HEADER, rows, {"PRON{P,T}": ["me", "you", "him"]}, "reflexive_allowed"
    )
    assert fanned == 3
    assert manual == 0
    assert [r[0] for r in new_rows] == ["me", "you", "him"]
    # Position_A/Position_B/Direction unchanged; criterion blanked; old Source
    # quoted into Comments; Source itself cleared for a fresh citation.
    for r in new_rows:
        assert r[1] == "33 (v:obj-part)"
        assert r[2] == "34 (v:rec)"
        assert r[3] == "forward"
        assert r[4] == ""  # criterion left blank, never carried forward
        assert r[5] == ""  # old Source cleared, not duplicated
        assert "PRON{P,T}" in r[6]
        assert "reflexive_allowed='y'" in r[6]
        assert "Lasnik example" in r[6]


def test_apply_split_nonpermutability_shape_element_a_side():
    rows = [["PRON{P,T}", "not", "n", "", ""]]
    new_rows, fanned, manual = _apply_split_to_pair_rows(
        _NONPERM_HEADER, rows, {"PRON{P,T}": ["me", "you"]}, "scopal"
    )
    assert fanned == 2
    assert manual == 0
    assert [r[0] for r in new_rows] == ["me", "you"]
    assert all(r[1] == "not" for r in new_rows)  # Element_B untouched
    assert all(r[2] == "" for r in new_rows)  # scopal blanked


def test_apply_split_nonpermutability_shape_element_b_side():
    rows = [["not", "PRON{P,T}", "y", "", ""]]
    new_rows, fanned, manual = _apply_split_to_pair_rows(
        _NONPERM_HEADER, rows, {"PRON{P,T}": ["me", "you"]}, "scopal"
    )
    assert fanned == 2
    assert [r[1] for r in new_rows] == ["me", "you"]
    assert all(r[0] == "not" for r in new_rows)  # Element_A untouched
    assert all(r[2] == "" for r in new_rows)


def test_apply_split_self_pair_flagged_not_guessed():
    rows = [["PRON{P,T}", "PRON{P,T}", "n", "", ""]]
    new_rows, fanned, manual = _apply_split_to_pair_rows(
        _NONPERM_HEADER, rows, {"PRON{P,T}": ["me", "you"]}, "scopal"
    )
    assert fanned == 0
    assert manual == 1
    assert new_rows == rows  # left untouched, not guessed at


def test_apply_split_no_match_leaves_row_unchanged():
    rows = [["not", "and", "y", "", ""]]
    new_rows, fanned, manual = _apply_split_to_pair_rows(
        _NONPERM_HEADER, rows, {"PRON{P,T}": ["me", "you"]}, "scopal"
    )
    assert fanned == 0
    assert manual == 0
    assert new_rows == rows


def test_apply_split_empty_map_is_noop():
    rows = [["PRON{P,T}", "and", "y", "", ""]]
    new_rows, fanned, manual = _apply_split_to_pair_rows(_NONPERM_HEADER, rows, {}, "scopal")
    assert new_rows == rows
    assert fanned == 0
    assert manual == 0


def test_apply_split_no_element_a_column_is_noop():
    header = ["Position_A", "Position_B", "Direction", "reflexive_allowed"]
    rows = [["5 (v:x)", "6 (v:y)", "forward", "y"]]
    new_rows, fanned, manual = _apply_split_to_pair_rows(
        header, rows, {"PRON{P,T}": ["me", "you"]}, "reflexive_allowed"
    )
    assert new_rows == rows
    assert fanned == 0


def test_apply_split_no_criterion_col_still_fans_out():
    """criterion_col=None (construction has no declared criterion) shouldn't crash --
    still fans out, just without a criterion value in the breadcrumb."""
    rows = [["PRON{P,T}", "and", "y", "", "existing note"]]
    new_rows, fanned, manual = _apply_split_to_pair_rows(
        _NONPERM_HEADER, rows, {"PRON{P,T}": ["me", "you"]}, None
    )
    assert fanned == 2
    for r in new_rows:
        assert "existing note" in r[4]
        assert "scopal" not in r[4]


def test_apply_split_multiple_rows_only_matching_ones_split():
    rows = [
        ["PRON{P,T}", "not", "n", "", ""],
        ["and", "not", "y", "", ""],
    ]
    new_rows, fanned, manual = _apply_split_to_pair_rows(
        _NONPERM_HEADER, rows, {"PRON{P,T}": ["me", "you", "him"]}, "scopal"
    )
    assert fanned == 3
    assert len(new_rows) == 4  # 3 fanned + 1 untouched
    assert new_rows[-1] == ["and", "not", "y", "", ""]


# ---------------------------------------------------------------------------
# _get_pair_row_constructions
# ---------------------------------------------------------------------------

def test_get_pair_row_constructions_covers_all_registered_classes():
    """Every class/construction validate_coding.py's is_pair_sheet check relies on
    this generic, schema-driven set instead of a hardcoded per-class-name check.

    Regression for the bug behind issue #260's 2026-08-01 failure: phrasal_accent's
    `general` tab is a pair-row sheet (row_type: pair_rows in diagnostic_classes.yaml,
    issue #237) but validate_coding.py's is_pair_sheet check only recognized
    "nonpermutability" and "coreference" by name, so phrasal_accent/general fell
    through to the standard-structure validator and failed with spurious "missing
    structural column" errors. This asserts the schema-driven set actually contains
    every pair-row construction currently registered, so a future addition can't
    silently repeat the same gap.
    """
    result = _get_pair_row_constructions()
    assert "phrasal_accent" in result
    assert "general" in result["phrasal_accent"]
    assert "nonpermutability" in result
    assert "general" in result["nonpermutability"]
    assert "coreference" in result
    assert {"reflexivization", "pronominalization", "np_reference"} <= result["coreference"]
