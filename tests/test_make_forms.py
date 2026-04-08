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
    """TSV → YAML → TSV round-trip preserves class/construction/criteria."""
    df = pd.read_csv(
        Path(__file__).parent.parent / "coded_data" / "stan1293" / "lang_setup" / "diagnostics_stan1293.tsv",
        sep="\t", dtype=str, keep_default_na=False,
    )
    yaml_data = _tsv_df_to_yaml(df, "stan1293")
    df2 = _yaml_to_tsv_df(yaml_data, "stan1293")

    assert set(df["Class"]) == set(df2["Class"])
    for _, row in df.iterrows():
        row2 = df2[df2["Class"] == row["Class"]].iloc[0]
        assert row["Constructions"] == row2["Constructions"]


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
