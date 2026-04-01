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
    DATA_DIR,
)
import coding.make_forms as _mf


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
    d = tmp_path / "coded_data" / "lang0001" / "planar_input"
    d.mkdir(parents=True)
    return d


# ---------------------------------------------------------------------------
# _read_diagnostics_for_language — YAML path
# ---------------------------------------------------------------------------

def test_read_diagnostics_prefers_yaml(planar_dir, monkeypatch):
    """When YAML is present it is used; the TSV is ignored even if it exists."""
    (planar_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    (planar_dir / "diagnostics_lang0001.tsv").write_text(TSV_CONTENT)
    monkeypatch.setattr(_mf, "DATA_DIR", str(planar_dir))

    rows = _read_diagnostics_for_language("lang0001")
    classes = [r[0] for r in rows]
    assert "ciscategorial" in classes
    assert "metrical" in classes


def test_read_diagnostics_yaml_criteria(planar_dir, monkeypatch):
    """Criteria from YAML are parsed correctly, including non-default value lists."""
    (planar_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    monkeypatch.setattr(_mf, "DATA_DIR", str(planar_dir))

    rows = _read_diagnostics_for_language("lang0001")
    metrical = next(r for r in rows if r[0] == "metrical")
    _class, construction, crit_names, crit_values = metrical
    assert construction == "stress_domain"
    assert "accented" in crit_names
    assert crit_values["accented"] == ["y", "n", "both"]
    assert crit_values["obligatory"] == ["y", "n"]


def test_read_diagnostics_falls_back_to_tsv(planar_dir, monkeypatch):
    """When no YAML is present, TSV is read as before."""
    (planar_dir / "diagnostics_lang0001.tsv").write_text(TSV_CONTENT)
    monkeypatch.setattr(_mf, "DATA_DIR", str(planar_dir))

    rows = _read_diagnostics_for_language("lang0001")
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
        Path(__file__).parent.parent / "coded_data" / "stan1293" / "planar_input" / "diagnostics_stan1293.tsv",
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
