"""Tests for coding/make_forms.py — YAML read path and serializers."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pandas as pd
import pytest
import yaml

from coding.make_forms import (
    _read_diagnostics_for_language,
    _yaml_to_tsv_df,
    _tsv_df_to_yaml,
    _dump_diagnostics_yaml,
    _diff_diagnostics_tsv_yaml,
    _apply_yaml_diff,
    build_element_index,
    classify_element,
    classify_biuniqueness_scope,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

YAML_CONTENT = textwrap.dedent("""\
    language: lang0001
    classes:
      ciscategorial:
        constructions: [general]
        criteria:
          V-combines: [y, n]
          N-combines: [y, n]
      metrical:
        constructions: [stress_domain]
        criteria:
          accented: [y, n, both]
          obligatory: [y, n]
        notes: "test notes"
""")

TSV_CONTENT = textwrap.dedent("""\
    Class\tLanguage\tConstructions\tCriteria
    ciscategorial\tlang0001\tgeneral\tV-combines, N-combines
    metrical\tlang0001\tstress_domain\taccented{y/n/both}, obligatory
""")


@pytest.fixture()
def planar_dir(tmp_path):
    d = tmp_path / "coded_data" / "lang0001" / "lang_setup"
    d.mkdir(parents=True)
    return d


# ---------------------------------------------------------------------------
# _read_diagnostics_for_language — YAML path
# ---------------------------------------------------------------------------

def test_read_diagnostics_prefers_yaml(planar_dir):
    """When YAML is present it is used; the TSV is ignored even if it exists."""
    (planar_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    (planar_dir / "diagnostics_lang0001.tsv").write_text(TSV_CONTENT)

    rows = _read_diagnostics_for_language("lang0001", planar_dir)
    classes = [r[0] for r in rows]
    assert "ciscategorial" in classes
    assert "metrical" in classes


def test_read_diagnostics_yaml_criteria(planar_dir):
    """Criteria from YAML are parsed correctly, including non-default value lists."""
    (planar_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)

    rows = _read_diagnostics_for_language("lang0001", planar_dir)
    metrical = next(r for r in rows if r[0] == "metrical")
    _class, construction, crit_names, crit_values = metrical
    assert construction == "stress_domain"
    assert "accented" in crit_names
    assert crit_values["accented"] == ["y", "n", "both"]
    assert crit_values["obligatory"] == ["y", "n"]


def test_read_diagnostics_falls_back_to_tsv(planar_dir):
    """When no YAML is present, TSV is read as before."""
    (planar_dir / "diagnostics_lang0001.tsv").write_text(TSV_CONTENT)

    rows = _read_diagnostics_for_language("lang0001", planar_dir)
    classes = [r[0] for r in rows]
    assert "ciscategorial" in classes
    assert "metrical" in classes


# ---------------------------------------------------------------------------
# _yaml_to_tsv_df
# ---------------------------------------------------------------------------

def test_yaml_to_tsv_df_default_values():
    """Criteria with [y, n] values are serialized without brace syntax."""
    data = yaml.safe_load(YAML_CONTENT)
    df = _yaml_to_tsv_df(data, "lang0001")
    cisc_row = df[df["Class"] == "ciscategorial"].iloc[0]
    assert "V-combines" in cisc_row["Criteria"]
    assert "{" not in cisc_row["Criteria"]


def test_yaml_to_tsv_df_non_default_values():
    """Criteria with non-default values use brace syntax."""
    data = yaml.safe_load(YAML_CONTENT)
    df = _yaml_to_tsv_df(data, "lang0001")
    met_row = df[df["Class"] == "metrical"].iloc[0]
    assert "accented{y/n/both}" in met_row["Criteria"]


# ---------------------------------------------------------------------------
# _tsv_df_to_yaml
# ---------------------------------------------------------------------------

def test_tsv_df_to_yaml_round_trip():
    """TSV → YAML → TSV round-trip preserves class/construction/criteria.

    Classes with construction_criteria emit one row per construction in both
    df and df2, so we compare by (Class, Constructions) rather than Class alone.
    """
    df = pd.read_csv(
        Path(__file__).parent.parent / "coded_data" / "stan1293" / "lang_setup" / "diagnostics_stan1293.tsv",
        sep="\t", dtype=str, keep_default_na=False,
    )
    yaml_data = _tsv_df_to_yaml(df, "stan1293")
    df2 = _yaml_to_tsv_df(yaml_data, "stan1293")

    assert set(df["Class"]) == set(df2["Class"])
    # Index df2 by (Class, Constructions) for O(1) lookup; construction-criteria
    # classes have one row per construction so this key is unique.
    df2_index = {
        (r["Class"], r["Constructions"]): r
        for _, r in df2.iterrows()
    }
    for _, row in df.iterrows():
        key = (row["Class"], row["Constructions"])
        assert key in df2_index, f"Row {key} missing from round-tripped DataFrame"
        assert row["Criteria"] == df2_index[key]["Criteria"]


# ---------------------------------------------------------------------------
# _dump_diagnostics_yaml
# ---------------------------------------------------------------------------

def test_dump_diagnostics_yaml_inline_lists():
    """Value lists are serialized inline ([y, n]) not as block sequences."""
    data = yaml.safe_load(YAML_CONTENT)
    output = _dump_diagnostics_yaml(data)
    assert "[y, n]" in output
    assert "[y, n, both]" in output


# ---------------------------------------------------------------------------
# _diff_diagnostics_tsv_yaml
# ---------------------------------------------------------------------------

def _make_tsv_df(rows):
    """Build a diagnostics TSV DataFrame from a list of (Class, Constructions, Criteria) tuples."""
    return pd.DataFrame(
        [{"Class": c, "Language": "lang0001", "Constructions": cons, "Criteria": crit}
         for c, cons, crit in rows],
        columns=["Class", "Language", "Constructions", "Criteria"],
    )


def test_diff_no_changes():
    """Identical TSV and YAML produce empty diff lists."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    tsv_df = _make_tsv_df([
        ("ciscategorial", "general", "V-combines, N-combines"),
        ("metrical",      "stress_domain", "accented{y/n/both}, obligatory"),
    ])
    det, amb = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, "lang0001")
    assert det == []
    assert amb == []


def test_diff_criterion_added():
    """A new criterion in the TSV (matching the schema) is deterministic."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    tsv_df = _make_tsv_df([
        ("ciscategorial", "general", "V-combines, N-combines, A-combines"),
        ("metrical",      "stress_domain", "accented{y/n/both}, obligatory"),
    ])
    det, amb = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, "lang0001")
    kinds = [c["kind"] for c in det]
    assert "criterion_added" in kinds
    added = next(c for c in det if c["kind"] == "criterion_added")
    assert added["criterion"] == "A-combines"
    assert amb == []


def test_diff_construction_removed():
    """A construction missing from a class still present in TSV is a deterministic removal."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    # metrical in YAML has stress_domain; TSV has metrical with a different construction
    tsv_df = _make_tsv_df([
        ("ciscategorial", "general", "V-combines, N-combines"),
        ("metrical",      "other_construction", "accented{y/n/both}, obligatory"),
    ])
    det, amb = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, "lang0001")
    kinds = [c["kind"] for c in det]
    assert "construction_removed" in kinds
    removed = next(c for c in det if c["kind"] == "construction_removed")
    assert removed["construction"] == "stress_domain"


def test_diff_class_removed_is_ambiguous():
    """A class entirely absent from the TSV is flagged as ambiguous (may be intentional)."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    # metrical class absent entirely from TSV
    tsv_df = _make_tsv_df([
        ("ciscategorial", "general", "V-combines, N-combines"),
    ])
    _det, amb = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, "lang0001")
    assert any(c["kind"] == "class_removed" for c in amb)


def test_diff_unknown_criterion_flagged():
    """A criterion not in diagnostic_criteria.yaml is flagged as ambiguous."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    tsv_df = _make_tsv_df([
        ("ciscategorial", "general", "V-combines, N-combines, totally_made_up_criterion_xyz"),
        ("metrical",      "stress_domain", "accented{y/n/both}, obligatory"),
    ])
    det, amb = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, "lang0001")
    assert any(c["kind"] == "unknown_criterion" for c in amb)


def test_diff_criterion_values_changed():
    """Changed criterion value list is a deterministic change."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    # Change accented from [y,n,both] to [y,n]
    tsv_df = _make_tsv_df([
        ("ciscategorial", "general", "V-combines, N-combines"),
        ("metrical",      "stress_domain", "accented, obligatory"),
    ])
    det, amb = _diff_diagnostics_tsv_yaml(tsv_df, yaml_data, "lang0001")
    kinds = [c["kind"] for c in det]
    assert "criterion_values_changed" in kinds
    changed = next(c for c in det if c["kind"] == "criterion_values_changed")
    assert changed["criterion"] == "accented"
    assert changed["new_values"] == ["y", "n"]


# ---------------------------------------------------------------------------
# _apply_yaml_diff
# ---------------------------------------------------------------------------

def test_apply_yaml_diff_criterion_added():
    """Deterministic criterion_added change is applied to the YAML."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    changes = [{"kind": "criterion_added", "class_name": "ciscategorial",
                "criterion": "A-combines", "values": ["y", "n"]}]
    result = _apply_yaml_diff(yaml_data, changes)
    assert "A-combines" in result["classes"]["ciscategorial"]["criteria"]


def test_apply_yaml_diff_preserves_notes():
    """_apply_yaml_diff does not strip the notes field from metrical."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    # metrical has notes: "test notes" in YAML_CONTENT
    changes = [{"kind": "construction_added", "class_name": "metrical",
                "construction": "extra_construction"}]
    result = _apply_yaml_diff(yaml_data, changes)
    assert result["classes"]["metrical"].get("notes") == "test notes"


def test_apply_yaml_diff_does_not_mutate_original():
    """_apply_yaml_diff returns a new dict; original is unchanged."""
    yaml_data = yaml.safe_load(YAML_CONTENT)
    original_criteria = set(yaml_data["classes"]["ciscategorial"]["criteria"].keys())
    changes = [{"kind": "criterion_added", "class_name": "ciscategorial",
                "criterion": "A-combines", "values": ["y", "n"]}]
    _apply_yaml_diff(yaml_data, changes)
    assert set(yaml_data["classes"]["ciscategorial"]["criteria"].keys()) == original_criteria


# ---------------------------------------------------------------------------
# classify_element
# ---------------------------------------------------------------------------

_PLANAR_SCHEMA = {
    "element_conventions": {
        "standard_labels": {
            "phrase_types": [
                {"label": "NP", "element_type": "embedded_structure"},
            ],
            "adverb_scope_labels": [
                {"label": "AD-S", "element_type": "formative"},
            ],
            "other_labels": [
                {"label": "PRON", "element_type": "formative"},
                {"label": "KEYSTONE", "element_type": "reserved"},
            ],
        }
    },
    "element_type_conventions": {
        "formative_capitalization_exceptions": {
            "items": [{"form": "I", "language": "stan1293"}],
        }
    },
}


def test_classify_element_embedded_structure():
    assert classify_element("NP{S,A}", _PLANAR_SCHEMA) == "embedded_structure"
    assert classify_element("NP", _PLANAR_SCHEMA) == "embedded_structure"


def test_classify_element_registered_formative_label():
    assert classify_element("PRON", _PLANAR_SCHEMA) == "formative"
    assert classify_element("AD-S", _PLANAR_SCHEMA) == "formative"


def test_classify_element_keystone_is_reserved():
    assert classify_element("KEYSTONE", _PLANAR_SCHEMA) == "reserved"


def test_classify_element_lowercase_and_hyphenated_forms_are_formative():
    assert classify_element("he", _PLANAR_SCHEMA) == "formative"
    assert classify_element("-ed", _PLANAR_SCHEMA) == "formative"
    assert classify_element("not", _PLANAR_SCHEMA) == "formative"


def test_classify_element_unicode_formative_not_misclassified():
    """A non-ASCII formative must not be caught by an ASCII-only caps check."""
    assert classify_element("наш", _PLANAR_SCHEMA) == "formative"
    assert classify_element("日本語", _PLANAR_SCHEMA) == "formative"


def test_classify_element_capitalization_exception():
    """'I' is all-uppercase by the typography rule but is a listed exception."""
    assert classify_element("I", _PLANAR_SCHEMA) == "formative"


def test_classify_element_unregistered_all_caps_is_unknown():
    """An ALL CAPS token with no registry entry must never silently default."""
    assert classify_element("FOOBAR", _PLANAR_SCHEMA) == "unknown"


def test_classify_element_real_schema_smoke():
    """Sanity check against the actual schemas/planar.yaml, not a fixture."""
    assert classify_element("NP{S,A}") == "embedded_structure"
    assert classify_element("I") == "formative"
    assert classify_element("he") == "formative"
    assert classify_element("KEYSTONE") == "reserved"


# ---------------------------------------------------------------------------
# classify_biuniqueness_scope (issue #254 Part 2a)
# ---------------------------------------------------------------------------

def test_classify_biuniqueness_scope_embedded_structure_is_excluded():
    assert classify_biuniqueness_scope("NP{S,A}", _PLANAR_SCHEMA) == "excluded"
    assert classify_biuniqueness_scope("NP", _PLANAR_SCHEMA) == "excluded"


def test_classify_biuniqueness_scope_keystone_is_excluded():
    assert classify_biuniqueness_scope("KEYSTONE", _PLANAR_SCHEMA) == "excluded"


def test_classify_biuniqueness_scope_registered_all_caps_formative_is_open_category():
    assert classify_biuniqueness_scope("PRON", _PLANAR_SCHEMA) == "open_category"
    assert classify_biuniqueness_scope("AD-S", _PLANAR_SCHEMA) == "open_category"


def test_classify_biuniqueness_scope_concrete_forms_are_filled():
    assert classify_biuniqueness_scope("he", _PLANAR_SCHEMA) == "filled"
    assert classify_biuniqueness_scope("-ed", _PLANAR_SCHEMA) == "filled"
    assert classify_biuniqueness_scope("not", _PLANAR_SCHEMA) == "filled"


def test_classify_biuniqueness_scope_capitalization_exception_is_filled():
    """'I' is all-uppercase by typography but a listed exception, so it's a
    concrete form (filled), not a category placeholder."""
    assert classify_biuniqueness_scope("I", _PLANAR_SCHEMA) == "filled"


def test_classify_biuniqueness_scope_unregistered_all_caps_is_unknown():
    assert classify_biuniqueness_scope("FOOBAR", _PLANAR_SCHEMA) == "unknown"


def test_classify_biuniqueness_scope_real_schema_smoke():
    """Sanity check against the actual schemas/planar.yaml, not a fixture."""
    assert classify_biuniqueness_scope("NP{S,A}") == "excluded"
    assert classify_biuniqueness_scope("KEYSTONE") == "excluded"
    assert classify_biuniqueness_scope("I") == "filled"
    assert classify_biuniqueness_scope("he") == "filled"
    assert classify_biuniqueness_scope("PRON") == "open_category"


# ---------------------------------------------------------------------------
# build_element_index — Class_Type branches (issue #270's "mixed" addition)
# ---------------------------------------------------------------------------

_INDEX_HEADER = "Language_ID\tPlanar_Type\tPosition\tPosition_Type\tPosition_Name\tElements\tClass_Type\n"


def _write_planar(tmp_path: Path, rows: str) -> Path:
    d = tmp_path
    path = d / "planar_lang0001.tsv"
    path.write_text(_INDEX_HEADER + rows, encoding="utf-8")
    return d


def test_build_element_index_open_list_mixed_all_index_the_same_way(tmp_path):
    rows = (
        "lang0001\tverbal\t1\tSlot\tv:a\tFOO\topen\n"
        "lang0001\tverbal\t2\tSlot\tv:b\tbar, baz\tlist\n"
        "lang0001\tverbal\t3\tSlot\tv:c\tNP, he, she\tmixed\n"
    )
    data_dir = _write_planar(tmp_path, rows)
    index = build_element_index("planar_lang0001.tsv", data_dir)
    assert "FOO@1" in index
    assert "bar@2" in index and "baz@2" in index
    assert "NP@3" in index and "he@3" in index and "she@3" in index


def test_build_element_index_single_element_list_is_valid(tmp_path):
    """list has no minimum element count -- a single-item list is normal,
    not something that needs a separate 'closed' Class_Type (removed; it
    was never actually distinguished from list in any check)."""
    rows = "lang0001\tverbal\t1\tSlot\tv:a\tonly-one\tlist\n"
    data_dir = _write_planar(tmp_path, rows)
    index = build_element_index("planar_lang0001.tsv", data_dir)
    assert "only-one@1" in index


def test_build_element_index_unknown_class_type_raises(tmp_path):
    rows = "lang0001\tverbal\t1\tSlot\tv:a\tFOO\tbogus\n"
    data_dir = _write_planar(tmp_path, rows)
    with pytest.raises(ValueError, match="Unexpected Class_Type"):
        build_element_index("planar_lang0001.tsv", data_dir)


def test_build_element_index_missing_required_column_raises(tmp_path):
    d = tmp_path
    path = d / "planar_lang0001.tsv"
    # No Class_Type column.
    path.write_text(
        "Language_ID\tPlanar_Type\tPosition\tPosition_Type\tPosition_Name\tElements\n"
        "lang0001\tverbal\t1\tSlot\tv:a\tFOO\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Missing required column"):
        build_element_index("planar_lang0001.tsv", d)


def test_build_element_index_non_integer_position_raises(tmp_path):
    rows = "lang0001\tverbal\tabc\tSlot\tv:a\tFOO\topen\n"
    data_dir = _write_planar(tmp_path, rows)
    with pytest.raises(ValueError, match="Non-integer Position"):
        build_element_index("planar_lang0001.tsv", data_dir)


def test_build_element_index_blank_position_row_is_skipped_not_raised(tmp_path):
    # A row with no Position at all is a placeholder, not an error --
    # matches the original loop's "if not pos_raw: continue".
    rows = (
        "lang0001\tverbal\t\tSlot\tv:a\tFOO\topen\n"
        "lang0001\tverbal\t2\tSlot\tv:b\tbar\tlist\n"
    )
    data_dir = _write_planar(tmp_path, rows)
    index = build_element_index("planar_lang0001.tsv", data_dir)
    assert index == {"bar@2": (2, "v:b", "lang0001", "bar")}


def test_build_element_index_duplicate_key_raises(tmp_path):
    # Same element name repeated within one position's Elements cell.
    rows = "lang0001\tverbal\t1\tSlot\tv:a\tFOO, FOO\topen\n"
    data_dir = _write_planar(tmp_path, rows)
    with pytest.raises(ValueError, match="Duplicate unique key"):
        build_element_index("planar_lang0001.tsv", data_dir)


def test_build_element_index_other_language_rows_ignored(tmp_path):
    # A planar file can hold multiple languages' rows; only lang_id's own
    # rows should ever reach the Position/Class_Type checks -- a garbage
    # Class_Type on a different language's row must not raise.
    rows = (
        "otherlang\tverbal\t1\tSlot\tv:a\tBAD\tbogus\n"
        "lang0001\tverbal\t2\tSlot\tv:b\tbar\tlist\n"
    )
    data_dir = _write_planar(tmp_path, rows)
    index = build_element_index("planar_lang0001.tsv", data_dir)
    assert index == {"bar@2": (2, "v:b", "lang0001", "bar")}
