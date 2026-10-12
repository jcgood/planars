"""Tests for coding/biuniqueness_rows.py: building the biuniqueness_deviations
tabs, and carrying answers over when they are regenerated (issue #254).

Includes the both-directions checks Jeff asked for (2026-10-11):
  forward  -- a change in a source tab reaches its dependent tab;
  backward -- a dependent row is never silently lost.
"""
from __future__ import annotations

import pandas as pd
import pytest

from coding import biuniqueness_rows as br
from coding.restructure_sheets import _get_keyed_row_constructions

LANG = "test0001"

PLANAR = pd.DataFrame([
    # Position, Position_Name, Elements, Biuniqueness_Scope
    (1, "v:leftedge", "and, CONJUNCT", "filled, open_category"),
    (3, "v:frontedauxiliary", "be, do, will", "filled, filled, filled"),
    (5, "v:npsubj1", "NP{S,A}, I, he", "excluded, filled, filled"),
    (6, "v:ad-S1", "AD-S", "open_category"),
    (8, "v:modal1", "can, will", "filled, filled"),
    (9, "v:sd-S2", "AD-S", "open_category"),
    (22, "v:progressive", "be", "filled"),
    (30, "v:verbstem", "KEYSTONE", "excluded"),
    (31, "v:verbinflection", "-ed, -s, -ing", "filled, filled, filled"),
], columns=["Position", "Position_Name", "Elements", "Biuniqueness_Scope"]).assign(
    Language_ID=LANG)

PRESCREEN_PARAMS = ["has_allomorphs", "members", "co_exponents"]
MORPHEME_ANSWERS = ["morpheme_class", "forms_relation", "Source", "Comments"]
MORPH_ANSWERS = ["occurs_here", "conditioning_type", "conditioning_features",
                 "conditioned_by", "trigger_filled", "Source", "Comments"]


def prescreen(answers):
    """A filled prescreening tab: every in-scope row, with `answers` applied
    by (Element, Position_Name)."""
    rows = br.prescreening_rows(PLANAR, LANG, PRESCREEN_PARAMS)
    df = pd.DataFrame(rows, columns=["Element", "Position_Name", "Position_Number"]
                      + PRESCREEN_PARAMS)
    for (element, pos), vals in answers.items():
        mask = (df["Element"] == element) & (df["Position_Name"] == pos)
        assert mask.any(), (element, pos)
        for col, v in vals.items():
            df.loc[mask, col] = v
    return df


ANSWERS = {
    ("be", "v:frontedauxiliary"): {"has_allomorphs": "y", "members": "am, are, is"},
    ("do", "v:frontedauxiliary"): {"has_allomorphs": "y", "members": "do, does"},
    ("will", "v:modal1"): {"has_allomorphs": "y", "members": "'ll, won't"},
    ("will", "v:frontedauxiliary"): {"has_allomorphs": "y"},
    ("can", "v:modal1"): {"has_allomorphs": "n"},
    ("AD-S", "v:ad-S1"): {"members": "probably"},
    ("be", "v:progressive"): {"has_allomorphs": "n", "co_exponents": "v:verbinflection"},
}


def as_df(rows, columns):
    return pd.DataFrame([{c: r.get(c, "") for c in columns} for r in rows], columns=columns)


def tab(rows, columns):
    """Rows as a tab reads back: header first, every cell a string."""
    return [list(columns)] + [[str(r.get(c, "")) for c in columns] for r in rows]


# ---------------------------------------------------------------------------
# prescreening
# ---------------------------------------------------------------------------

def test_prescreening_keeps_only_in_scope_elements_in_planar_order():
    rows = br.prescreening_rows(PLANAR, LANG, PRESCREEN_PARAMS)
    keys = [(r[0], r[1]) for r in rows]
    assert ("NP{S,A}", "v:npsubj1") not in keys       # excluded
    assert ("KEYSTONE", "v:verbstem") not in keys     # excluded
    assert keys[0] == ("and", "v:leftedge")
    assert ("[-ing]", "v:verbinflection") in keys      # hyphen elements bracketed


def test_prescreening_open_category_rows_answer_through_members_not_yes_no():
    rows = {(r[0], r[1]): r for r in br.prescreening_rows(PLANAR, LANG, PRESCREEN_PARAMS)}
    assert rows[("AD-S", "v:ad-S1")][3] == "NA"        # has_allomorphs
    assert rows[("and", "v:leftedge")][3] == ""


def test_a_planar_without_the_scope_column_is_refused_with_the_fix():
    with pytest.raises(ValueError, match="no Biuniqueness_Scope column"):
        br.prescreening_rows(PLANAR.drop(columns=["Biuniqueness_Scope"]), LANG, PRESCREEN_PARAMS)


# ---------------------------------------------------------------------------
# morphemes
# ---------------------------------------------------------------------------

def test_morphemes_come_from_yes_rows_open_category_members_and_co_exponents():
    m = {r["Morpheme"]: r for r in br.morpheme_rows(prescreen(ANSWERS), PLANAR, LANG)}
    assert m["be"]["Origin"] == "filled"
    assert m["will"]["Found_At"] == "v:frontedauxiliary, v:modal1"   # one row, both positions
    assert m["probably"]["Origin"] == "open_category"
    co = m["be + v:verbinflection"]
    assert co["Origin"] == "co_exponent" and co["forms_relation"] == "co-occur"
    assert "can" not in m                                            # has_allomorphs=n


# ---------------------------------------------------------------------------
# morphs
# ---------------------------------------------------------------------------

def morphs_for(answers=ANSWERS):
    ps = prescreen(answers)
    morphemes = as_df(br.morpheme_rows(ps, PLANAR, LANG), br.MORPHEMES_STRUCT)
    return br.morph_rows(morphemes, ps, PLANAR, LANG)


def test_a_filled_morpheme_gets_every_form_at_every_position_it_sits_at():
    will = {(r["Position_Name"], r["Form"]) for r in morphs_for() if r["Morpheme"] == "will"}
    assert will == {(p, f) for p in ("v:frontedauxiliary", "v:modal1")
                    for f in ("will", "'ll", "won't")}


def test_an_open_category_member_appears_where_it_was_listed():
    probably = [r for r in morphs_for() if r["Morpheme"] == "probably"]
    assert [(r["Position_Name"], r["Form"]) for r in probably] == [("v:ad-S1", "probably")]


def test_a_co_exponent_lists_every_element_at_the_partner_position():
    co = [(r["Position_Name"], r["Form"]) for r in morphs_for()
          if r["Morpheme"] == "be + v:verbinflection"]
    assert co == [("v:progressive", "be"), ("v:verbinflection", "[-ed]"),
                  ("v:verbinflection", "[-s]"), ("v:verbinflection", "[-ing]")]


# ---------------------------------------------------------------------------
# carry_over: forward (a source change reaches the dependent)
# ---------------------------------------------------------------------------

def test_forward_a_new_yes_row_adds_rows_and_keeps_every_existing_answer():
    first = morphs_for()
    answered = [dict(r, occurs_here="y", conditioning_type="morphosyntactic") for r in first]
    existing = tab(answered, br.MORPHS_STRUCT + MORPH_ANSWERS)

    more = {**ANSWERS, ("he", "v:npsubj1"): {"has_allomorphs": "y", "members": "him"}}
    rows, drops, counts = br.carry_over(morphs_for(more), existing,
                                        br.MORPHS_KEY, MORPH_ANSWERS)
    assert drops == []
    assert counts["added"] == 2 and counts["removed"] == 0         # he, him at v:npsubj1
    by_key = {(r["Morpheme"], r["Position_Name"], r["Form"]): r for r in rows}
    for r in first:
        kept = by_key[(r["Morpheme"], r["Position_Name"], r["Form"])]
        assert kept["occurs_here"] == "y" and kept["conditioning_type"] == "morphosyntactic"
    assert by_key[("he", "v:npsubj1", "him")].get("occurs_here", "") == ""


def test_forward_a_new_member_form_reaches_every_position_of_the_morpheme():
    more = dict(ANSWERS)
    more[("do", "v:frontedauxiliary")] = {"has_allomorphs": "y", "members": "do, does, did"}
    rows, _, counts = br.carry_over(morphs_for(more), tab(morphs_for(), br.MORPHS_STRUCT),
                                    br.MORPHS_KEY, MORPH_ANSWERS)
    assert ("do", "v:frontedauxiliary", "did") in {
        (r["Morpheme"], r["Position_Name"], r["Form"]) for r in rows}
    assert counts["added"] == 1


def test_forward_an_existing_answer_beats_a_generated_prefill():
    """forms_relation is pre-filled co-occur for a co-exponent; if the
    annotator changed it, regeneration must not change it back."""
    ps = prescreen(ANSWERS)
    gen = br.morpheme_rows(ps, PLANAR, LANG)
    existing = [dict(r) for r in gen]
    for r in existing:
        if r["Morpheme"] == "be + v:verbinflection":
            r["forms_relation"] = "alternate"
    rows, _, _ = br.carry_over(gen, tab(existing, br.MORPHEMES_STRUCT + MORPHEME_ANSWERS),
                               br.MORPHEMES_KEY, MORPHEME_ANSWERS)
    co = next(r for r in rows if r["Morpheme"] == "be + v:verbinflection")
    assert co["forms_relation"] == "alternate"


# ---------------------------------------------------------------------------
# carry_over: backward (a dependent row is never silently lost)
# ---------------------------------------------------------------------------

def test_backward_an_answered_row_whose_source_is_gone_is_reported_not_dropped():
    answered = [dict(r, occurs_here="y") if r["Morpheme"] == "do" else dict(r)
                for r in morphs_for()]
    existing = tab(answered, br.MORPHS_STRUCT + MORPH_ANSWERS)
    fewer = {k: v for k, v in ANSWERS.items() if k != ("do", "v:frontedauxiliary")}
    rows, drops, counts = br.carry_over(morphs_for(fewer), existing, br.MORPHS_KEY, MORPH_ANSWERS)
    assert sorted(d["Form"] for d in drops) == ["do", "does"]
    assert counts["removed"] == 2
    assert "occurs_here='y'" in br.describe_drop(drops[0], br.MORPHS_KEY, MORPH_ANSWERS)


def test_backward_an_unanswered_row_whose_source_is_gone_drops_quietly():
    existing = tab(morphs_for(), br.MORPHS_STRUCT + MORPH_ANSWERS)
    fewer = {k: v for k, v in ANSWERS.items() if k != ("do", "v:frontedauxiliary")}
    rows, drops, _ = br.carry_over(morphs_for(fewer), existing, br.MORPHS_KEY, MORPH_ANSWERS)
    assert drops == []
    assert not any(r["Morpheme"] == "do" for r in rows)


def test_backward_a_hand_added_row_survives_every_regeneration():
    hand = {"Morpheme": "probably", "Position_Name": "v:ad-S1", "Form": "prob'ly",
            "Origin": "", "occurs_here": "y"}
    existing = tab(morphs_for() + [hand], br.MORPHS_STRUCT + MORPH_ANSWERS)
    rows, drops, counts = br.carry_over(morphs_for(), existing, br.MORPHS_KEY, MORPH_ANSWERS)
    kept = [r for r in rows if r["Form"] == "prob'ly"]
    assert len(kept) == 1 and kept[0]["Origin"] == "hand-added" and kept[0]["occurs_here"] == "y"
    assert drops == [] and counts["hand_added"] == 1

    # ...and again, now that it is marked hand-added.
    rows2, _, _ = br.carry_over(morphs_for(), tab(rows, br.MORPHS_STRUCT + MORPH_ANSWERS),
                                br.MORPHS_KEY, MORPH_ANSWERS)
    assert [r["Origin"] for r in rows2 if r["Form"] == "prob'ly"] == ["hand-added"]


def test_round_trip_regenerating_unchanged_sources_changes_nothing():
    first, _, _ = br.carry_over(morphs_for(), [], br.MORPHS_KEY, MORPH_ANSWERS)
    answered = [dict(r, occurs_here="n") for r in first]
    again, drops, counts = br.carry_over(
        morphs_for(), tab(answered, br.MORPHS_STRUCT + MORPH_ANSWERS), br.MORPHS_KEY, MORPH_ANSWERS)
    assert drops == [] and counts["added"] == 0 and counts["removed"] == 0
    assert [(r["Morpheme"], r["Position_Name"], r["Form"], r["occurs_here"]) for r in again] == \
           [(r["Morpheme"], r["Position_Name"], r["Form"], "n") for r in first]


# ---------------------------------------------------------------------------
# restructure-sheets: renames carried into keyed tabs
# ---------------------------------------------------------------------------

def test_restructure_renames_positions_and_elements_in_keyed_rows():
    from coding.restructure_sheets import _transform_keyed_rows
    header = br.MORPHS_STRUCT + ["occurs_here", "conditioned_by", "Source", "Comments"]
    rows = [
        ["do", "v:frontedauxiliary", "does", "filled", "y", "v:npsubj1", "", ""],
        ["be + v:verbinflection", "v:verbinflection", "[-ing]", "co_exponent", "y", "", "", ""],
    ]
    out, changed, flagged = _transform_keyed_rows(
        header, rows, {"conditioned_by"},
        rename_map={"v:npsubj1": "v:subj", "v:verbinflection": "v:infl"},
        element_rename_map={"do": "doo"}, split_element_map={})
    assert out[0][:3] == ["doo", "v:frontedauxiliary", "does"]
    assert out[0][5] == "v:subj"                                   # conditioned_by
    assert out[1][:2] == ["be + v:infl", "v:infl"]                 # label and position
    assert changed == 4 and flagged == 0


def test_restructure_flags_rows_on_a_split_element_rather_than_guessing():
    from coding.restructure_sheets import _transform_keyed_rows
    header = br.MORPHS_STRUCT + ["occurs_here", "Source", "Comments"]
    rows = [["will", "v:modal1", "'ll", "filled", "y", "", "seen in corpus"]]
    out, changed, flagged = _transform_keyed_rows(
        header, rows, set(), {}, {}, {"will": ["will.FUT", "will.VOL"]})
    assert flagged == 1 and changed == 0
    assert out[0][:3] == ["will", "v:modal1", "'ll"]               # unchanged
    assert out[0][-1] == "split will -> will.FUT, will.VOL: review | seen in corpus"


def test_restructure_rebuilds_prescreening_from_in_scope_elements_only(tmp_path):
    from coding.restructure_sheets import _element_rows_for
    lang_setup = tmp_path / LANG / "lang_setup"
    lang_setup.mkdir(parents=True)
    PLANAR.to_csv(lang_setup / f"planar_{LANG}.tsv", sep="\t", index=False)
    rows = _element_rows_for(br.CLASS_NAME, "prescreening", None, LANG,
                             PRESCREEN_PARAMS, lang_setup / f"planar_{LANG}.tsv")
    assert ("KEYSTONE", "v:verbstem") not in {(r[0], r[1]) for r in rows}
    assert rows == br.prescreening_rows(PLANAR, LANG, PRESCREEN_PARAMS)


def test_restructure_renames_positions_inside_co_exponent_answers():
    from coding.restructure_sheets import _rename_positions_in_annotations
    existing = {("be", "22"): {"has_allomorphs": "n", "co_exponents": "v:verbinflection"}}
    out = _rename_positions_in_annotations(
        existing, {"has_allomorphs": ["y", "n"], "co_exponents": ["<position_names>"]},
        {"v:verbinflection": "v:infl"})
    assert out[("be", "22")] == {"has_allomorphs": "n", "co_exponents": "v:infl"}


# ---------------------------------------------------------------------------
# make_synthetic_lang: keyed rows follow the position drop by name
# ---------------------------------------------------------------------------

def test_synthetic_generator_drops_keyed_rows_at_dropped_positions():
    import random
    import make_synthetic_lang as msl
    text = ("Morpheme\tPosition_Name\tForm\tOrigin\toccurs_here\tSource\tComments\n"
            "will\tv:modal1\t'll\tfilled\ty\t\t\n"
            "will\tv:gone\twill\tfilled\ty\t\t\n")
    out, kept, dropped, _ = msl._transform_filled_tsv(
        text, {8: 8}, random.Random(0), {}, surviving_names={"v:modal1"})
    assert (kept, dropped) == (1, 1)
    assert "v:gone" not in out and "v:modal1" in out


# ---------------------------------------------------------------------------
# integrity-check: a keyed tab out of step with its source
# ---------------------------------------------------------------------------

def test_integrity_check_reports_a_keyed_tab_out_of_step_with_its_source(tmp_path, monkeypatch):
    from coding import integrity_check as ic
    monkeypatch.setattr(ic, "CODED_DATA", tmp_path)
    (tmp_path / LANG / "lang_setup").mkdir(parents=True)
    PLANAR.to_csv(tmp_path / LANG / "lang_setup" / f"planar_{LANG}.tsv", sep="\t", index=False)
    cls_dir = tmp_path / LANG / br.CLASS_NAME
    cls_dir.mkdir()
    prescreen(ANSWERS).to_csv(cls_dir / "prescreening.tsv", sep="\t", index=False)
    morphemes = br.morpheme_rows(prescreen(ANSWERS), PLANAR, LANG)
    as_df(morphemes, br.MORPHEMES_STRUCT + ["forms_relation"]).to_csv(
        cls_dir / "morphemes.tsv", sep="\t", index=False)
    con = {"name": "morphemes", "depends_on": "prescreening", "staleness_check": "keyed_source"}

    assert ic._keyed_staleness(LANG, br.CLASS_NAME, con) == (set(), set())

    # Adam answers one more row in prescreening, and it is imported.
    more = {**ANSWERS, ("he", "v:npsubj1"): {"has_allomorphs": "y"}}
    prescreen(more).to_csv(cls_dir / "prescreening.tsv", sep="\t", index=False)
    assert ic._keyed_staleness(LANG, br.CLASS_NAME, con) == ({"he"}, set())


# ---------------------------------------------------------------------------
# The schema and this module agree
# ---------------------------------------------------------------------------

def test_the_schema_declares_the_same_keyed_columns_as_this_module():
    keyed = _get_keyed_row_constructions()[br.CLASS_NAME]
    for construction, (columns, key) in br.KEYED.items():
        assert keyed[construction]["columns"] == columns
        assert keyed[construction]["key"] == key


def test_an_unknown_row_type_is_refused(monkeypatch):
    import coding.schemas as schemas
    monkeypatch.setattr(schemas, "load_diagnostic_classes", lambda: {"classes": [
        {"name": "x", "constructions": [{"name": "y", "row_type": "pairs_rows"}]}]})
    with pytest.raises(ValueError, match="row_type 'pairs_rows'"):
        _get_keyed_row_constructions()


def test_a_keyed_construction_without_its_columns_is_refused(monkeypatch):
    import coding.schemas as schemas
    monkeypatch.setattr(schemas, "load_diagnostic_classes", lambda: {"classes": [
        {"name": "x", "constructions": [{"name": "y", "row_type": "keyed_rows"}]}]})
    with pytest.raises(ValueError, match="must declare keyed_columns and a key"):
        _get_keyed_row_constructions()
