"""Tests for planars/biuniqueness_deviations.py (issue #254).

The worked rows are the ones in the design posted on #254 (2026-10-11):
do/does, go/went, sing/sang/sung, cut, will/'ll/won't, and the progressive
be ... -ing as extended exponence.
"""
from __future__ import annotations

import pandas as pd
import pytest
import yaml
from importlib.resources import files

from planars import biuniqueness_deviations as bd

LANG = "test0001"

# A cut-down English-like planar: only the positions the worked rows use.
PLANAR = [
    (3, "v:frontedauxiliary", "be, have, do, will"),
    (4, "v:frontedauxiliaryinflection", "-n, -s, -v"),
    (5, "v:npsubj1", "NP{S,A}, I, you, he"),
    (8, "v:modal1", "can, will"),
    (10, "v:neg1", "not"),
    (12, "v:perfect", "ha"),
    (22, "v:progressive", "be"),
    (30, "v:verbstem", "KEYSTONE"),
    (31, "v:verbinflection", "-ed, -s, -ing"),
]

MORPHEMES = [
    # Morpheme, morpheme_class, forms_relation
    ("do", "", "alternate"),
    ("go", "", "alternate"),
    ("sing", "ablaut_i_a_u", "alternate"),
    ("cut", "zero_td_monosyllabic", "alternate"),
    ("will", "", "alternate"),
    ("PROG", "", "co-occur"),
    ("-s", "", "alternate"),
]

MORPHS = [
    # Morpheme, Position_Name, Form, occurs_here, conditioning_type,
    # conditioning_features, conditioned_by, trigger_filled
    ("do", "v:frontedauxiliary", "do", "y", "morphosyntactic", "elsewhere", "", ""),
    ("do", "v:frontedauxiliary", "does", "y", "morphosyntactic",
     "person=3, number=sg, tense=present", "v:npsubj1", "y"),
    ("go", "v:verbstem", "go", "y", "morphosyntactic", "elsewhere", "", ""),
    ("go", "v:verbstem", "went", "y", "morphosyntactic", "tense=past", "v:verbinflection", "n"),
    ("sing", "v:verbstem", "sing", "y", "morphosyntactic", "elsewhere", "", ""),
    ("sing", "v:verbstem", "sang", "y", "morphosyntactic", "tense=past", "v:verbinflection", "n"),
    ("sing", "v:verbstem", "sung", "y", "morphosyntactic", "aspect=perfect", "v:perfect", "y"),
    ("cut", "v:verbstem", "cut", "y", "morphosyntactic", "elsewhere", "", ""),
    ("cut", "v:verbstem", "cut", "y", "morphosyntactic", "tense=past", "v:verbinflection", "n"),
    ("will", "v:modal1", "will", "y", "morphosyntactic", "elsewhere", "", ""),
    ("will", "v:modal1", "'ll", "y", "prosodic", "host", "v:npsubj1", "y"),
    ("will", "v:modal1", "won't", "y", "morphosyntactic", "polarity=neg", "v:neg1", "n"),
    ("will", "v:frontedauxiliary", "will", "y", "morphosyntactic", "elsewhere", "", ""),
    ("will", "v:frontedauxiliary", "'ll", "n", "", "", "", ""),
    ("PROG", "v:progressive", "be", "y", "morphosyntactic", "aspect=progressive", "", ""),
    ("PROG", "v:verbinflection", "-ing", "y", "morphosyntactic", "aspect=progressive", "", ""),
    # Predictable alternation: excluded from every domain.
    ("-s", "v:verbinflection", "-iz", "y", "phonological", "after sibilant",
     "v:verbstem", "y"),
]

MORPH_COLS = ["Morpheme", "Position_Name", "Form", "occurs_here", "conditioning_type",
              "conditioning_features", "conditioned_by", "trigger_filled"]


def write_lang(tmp_path, morphs=MORPHS, morphemes=MORPHEMES):
    lang = tmp_path / LANG
    (lang / "lang_setup").mkdir(parents=True)
    pd.DataFrame(
        [{"Language_ID": LANG, "Position": n, "Position_Name": name, "Elements": els}
         for n, name, els in PLANAR]
    ).to_csv(lang / "lang_setup" / f"planar_{LANG}.tsv", sep="\t", index=False)
    cls = lang / "biuniqueness_deviations"
    cls.mkdir()
    pd.DataFrame(morphemes, columns=["Morpheme", "morpheme_class", "forms_relation"]).to_csv(
        cls / "morphemes.tsv", sep="\t", index=False)
    pd.DataFrame(morphs, columns=MORPH_COLS).to_csv(cls / "morphs.tsv", sep="\t", index=False)
    return cls / "morphs.tsv"


def domains_by_key(result):
    return {(d["type"], d["morpheme"], d["position_name"]): d for d in result["domains"]}


@pytest.fixture
def result(tmp_path):
    return bd.derive(write_lang(tmp_path))


# ---------------------------------------------------------------------------
# The worked rows
# ---------------------------------------------------------------------------

def test_each_worked_row_lands_in_the_expected_domain(result):
    d = domains_by_key(result)
    expected = {
        ("extended_exponence", "PROG", None): ((22, 31), (22, 31)),
        ("allomorphy", "do", "v:frontedauxiliary"): ((3, 5), (3, 30)),
        ("allomorphy", "sing", "v:verbstem"): ((12, 30), (12, 30)),
        ("allomorphy", "will", "v:modal1"): ((5, 8), (5, 30)),
        ("cumulative_exponence", "go", "v:verbstem"): ((30, 31), (30, 31)),
        ("cumulative_exponence", "sing", "v:verbstem"): ((30, 31), (30, 31)),
        ("cumulative_exponence", "will", "v:modal1"): ((8, 10), (8, 30)),
        ("zero_morph", "cut", "v:verbstem"): ((30, 31), (30, 31)),
    }
    assert set(d) == set(expected)
    for key, (raw, anchored) in expected.items():
        assert d[key]["raw_span"] == raw, key
        assert d[key]["anchored_span"] == anchored, key


def test_a_raw_span_can_miss_the_keystone_but_the_anchored_one_never_does(result):
    """does is conditioned by the subject: v:frontedauxiliary..v:npsubj1."""
    do = domains_by_key(result)[("allomorphy", "do", "v:frontedauxiliary")]
    keystone = result["keystone_position"]
    assert not (do["raw_span"][0] <= keystone <= do["raw_span"][1])
    assert do["anchored_span"][0] <= keystone <= do["anchored_span"][1]


def test_one_morpheme_at_one_position_gets_one_domain_per_type(result):
    """will at v:modal1: prosodic 'll (allomorphy) and fused won't (cumulative)
    keep separate domains, since their triggers differ."""
    d = domains_by_key(result)
    assert d[("allomorphy", "will", "v:modal1")]["positions"] == [5, 8]
    assert d[("cumulative_exponence", "will", "v:modal1")]["positions"] == [8, 10]


def test_elsewhere_phonological_and_non_occurring_forms_make_no_domain(result):
    morphemes = {d["morpheme"] for d in result["domains"]}
    assert "-s" not in morphemes                      # phonological only
    assert not any(d["morpheme"] == "will" and d["position_name"] == "v:frontedauxiliary"
                   for d in result["domains"])         # elsewhere + occurs_here=n only


def test_the_form_table_carries_each_rows_derived_type(result):
    ft = result["form_table"]
    types = dict(zip(ft["Form"] + "@" + ft["Position_Name"], ft["deviation_type"]))
    assert types["went@v:verbstem"] == "cumulative_exponence"
    assert types["does@v:frontedauxiliary"] == "allomorphy"
    assert types["-ing@v:verbinflection"] == "extended_exponence"
    assert types["-iz@v:verbinflection"] == ""        # excluded, no deviation
    assert types["'ll@v:frontedauxiliary"] == ""      # occurs_here=n


def test_format_result_names_every_domain(result):
    text = bd.format_result(result)
    for heading in ("== extended_exponence ==", "== allomorphy ==",
                    "== cumulative_exponence ==", "== zero_morph =="):
        assert heading in text
    assert "will at v:modal1:" in text
    assert "PROG at (all its pieces):" in text


# ---------------------------------------------------------------------------
# Rows the rules cannot place: an error, never a silent default
# ---------------------------------------------------------------------------

BAD_TRIGGER = ("go", "v:verbstem", "gone", "y", "morphosyntactic", "aspect=perfect",
               "v:perfect", "")
BAD_POSITION = ("go", "v:nowhere", "went", "y", "morphosyntactic", "tense=past",
                "v:verbinflection", "n")
BAD_TRIGGER_POSITION = ("go", "v:verbstem", "went", "y", "morphosyntactic", "tense=past",
                        "v:nowhere", "n")
UNLISTED_MORPHEME = ("be", "v:progressive", "is", "y", "morphosyntactic", "person=3",
                     "v:npsubj1", "y")


@pytest.mark.parametrize("bad, fragment", [
    (BAD_TRIGGER, "trigger_filled is ''"),
    (BAD_POSITION, "position 'v:nowhere' is not in the planar"),
    (BAD_TRIGGER_POSITION, "conditioned_by names 'v:nowhere'"),
    (UNLISTED_MORPHEME, "not listed in morphemes.tsv"),
])
def test_strict_mode_refuses_an_unplaceable_row(tmp_path, bad, fragment):
    path = write_lang(tmp_path, morphs=MORPHS + [bad])
    with pytest.raises(ValueError, match=fragment.replace("(", r"\(")):
        bd.derive(path)


def test_lenient_mode_reports_the_row_and_skips_it(tmp_path):
    path = write_lang(tmp_path, morphs=MORPHS + [BAD_TRIGGER])
    result = bd.derive(path, strict=False)
    assert any("trigger_filled is ''" in m for m in result["missing_data"]["unplaced_rows"])
    assert "NOTE: Some form rows could not be placed" in bd.format_result(result)
    # Everything placeable still comes through.
    assert ("cumulative_exponence", "go", "v:verbstem") in domains_by_key(result)


def test_an_unknown_forms_relation_is_refused(tmp_path):
    morphemes = [m if m[0] != "go" else ("go", "", "both") for m in MORPHEMES]
    path = write_lang(tmp_path, morphemes=morphemes)
    with pytest.raises(ValueError, match="forms_relation is 'both'"):
        bd.derive(path)


# ---------------------------------------------------------------------------
# The schema and the module agree
# ---------------------------------------------------------------------------

def test_derived_types_match_the_schemas_registry():
    classes = yaml.safe_load(files("schemas").joinpath("diagnostic_classes.yaml").read_text())
    entry = next(c for c in classes["classes"] if c["name"] == "biuniqueness_deviations")
    derived = [t["name"] for t in entry["deviation_types"] if t["derived"]]
    assert tuple(derived) == bd.DERIVED_TYPES
