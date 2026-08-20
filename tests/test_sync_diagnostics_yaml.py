"""Tests for coding/sync_diagnostics_yaml.py — _sync_to_tsv and _sync_from_tsv."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pandas as pd
import pytest
import yaml

import coding.sync_diagnostics_yaml as _sdy


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

TSV_CONTENT = (
    "Class\tLanguage\tConstructions\tCriteria\n"
    "ciscategorial\tlang0001\tgeneral\tV-combines, N-combines\n"
    "metrical\tlang0001\tstress_domain\taccented{y/n/both}, obligatory\n"
)

# _sync_to_tsv gates on validate_diagnostics_yaml's errors, including check 9
# (every collection_required: "y" class must be present) — YAML_CONTENT above
# deliberately omits those classes to stay minimal for _sync_from_tsv tests,
# which don't call validate_diagnostics_yaml at all. _sync_to_tsv tests need a
# genuinely valid YAML instead, so they exercise the create/update/no-change
# logic rather than the required-classes gate.
YAML_CONTENT_ALL_REQUIRED = textwrap.dedent("""\
    language: lang0001
    classes:
      ciscategorial:
        constructions: [general]
        criteria:
          V-combines: [y, n]
          N-combines: [y, n]
      subspanrepetition:
        constructions: [andCoordination]
        criteria:
          widescope_left: [y, n]
          widescope_right: [y, n]
          fillable_botheither_conjunct: [y, n]
      noninterruption:
        constructions: [general]
        criteria:
          free: [y, n]
          multiple: [y, n]
      nonpermutability:
        constructions: [element_prescreening, general]
        criteria:
          scopal: [y, n, both]
      free_occurrence:
        constructions: [general]
        criteria:
          free: [y, n]
          left-edge-of-free-form: [y, n, na]
          right-edge-of-free-form: [y, n, na]
          dependent-on-left: [na, "<position_number>"]
          dependent-on-right: [na, "<position_number>"]
      proform:
        constructions: [do_so_substitution]
        criteria:
          shareable_proform_replace: [y, n, both]
""")


@pytest.fixture()
def lang_dir(tmp_path, monkeypatch):
    """Set up a coded_data/lang0001/lang_setup/ tree and patch CODED_DATA."""
    d = tmp_path / "coded_data" / "lang0001" / "lang_setup"
    d.mkdir(parents=True)
    monkeypatch.setattr(_sdy, "CODED_DATA", tmp_path / "coded_data")
    return d


# ---------------------------------------------------------------------------
# _sync_to_tsv
# ---------------------------------------------------------------------------

def test_sync_to_tsv_creates_tsv(lang_dir):
    """Dry run with no existing TSV reports 'Would create' but does not write."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT_ALL_REQUIRED)
    changed = _sdy._sync_to_tsv("lang0001", apply=False, error_langs=[])
    assert changed is True
    assert not (lang_dir / "diagnostics_lang0001.tsv").exists()


def test_sync_to_tsv_writes_when_apply(lang_dir):
    """--apply writes the TSV."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT_ALL_REQUIRED)
    _sdy._sync_to_tsv("lang0001", apply=True, error_langs=[])
    tsv_path = lang_dir / "diagnostics_lang0001.tsv"
    assert tsv_path.exists()
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    assert set(df["Class"]) == {
        "ciscategorial", "subspanrepetition", "noninterruption",
        "nonpermutability", "free_occurrence", "proform",
    }


def test_sync_to_tsv_no_change_when_up_to_date(lang_dir):
    """Returns False when TSV already matches YAML content."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT_ALL_REQUIRED)
    _sdy._sync_to_tsv("lang0001", apply=True, error_langs=[])
    changed = _sdy._sync_to_tsv("lang0001", apply=False, error_langs=[])
    assert changed is False


def test_sync_to_tsv_skips_missing_yaml(lang_dir):
    """Returns False and prints a skip message when no YAML exists."""
    error_langs: list = []
    changed = _sdy._sync_to_tsv("lang0001", apply=True, error_langs=error_langs)
    assert changed is False
    assert error_langs == []          # a missing YAML isn't a validation error


def test_sync_to_tsv_skips_on_validation_error(lang_dir):
    """Returns False when YAML has validation errors (mismatched language field)."""
    bad_yaml = YAML_CONTENT.replace("language: lang0001", "language: other_lang")
    (lang_dir / "diagnostics_lang0001.yaml").write_text(bad_yaml)
    error_langs: list = []
    changed = _sdy._sync_to_tsv("lang0001", apply=True, error_langs=error_langs)
    assert changed is False
    assert not (lang_dir / "diagnostics_lang0001.tsv").exists()
    # issue #283: a blocking validation error used to be visible only in the
    # printed log -- error_langs is what lets main() turn it into a non-zero
    # exit code so the daily automation actually notices.
    assert error_langs == ["lang0001"]


# ---------------------------------------------------------------------------
# _sync_from_tsv
# ---------------------------------------------------------------------------

def test_sync_from_tsv_no_diff(lang_dir):
    """Returns False when TSV and YAML are in sync."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    (lang_dir / "diagnostics_lang0001.tsv").write_text(TSV_CONTENT)
    drift: list = []
    changed = _sdy._sync_from_tsv("lang0001", apply=False, drift_entries=drift)
    assert changed is False
    assert drift == []


def test_sync_from_tsv_detects_criterion_added(lang_dir):
    """Detects and applies a new (known) criterion in the TSV."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    tsv_with_extra = TSV_CONTENT.replace(
        "V-combines, N-combines", "V-combines, N-combines, A-combines"
    )
    (lang_dir / "diagnostics_lang0001.tsv").write_text(tsv_with_extra)
    drift: list = []
    changed = _sdy._sync_from_tsv("lang0001", apply=True, drift_entries=drift)
    assert changed is True
    updated = yaml.safe_load((lang_dir / "diagnostics_lang0001.yaml").read_text())
    assert "A-combines" in updated["classes"]["ciscategorial"]["criteria"]


def test_sync_from_tsv_preserves_notes(lang_dir):
    """Applying deterministic changes does not strip notes from the YAML."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    tsv_with_extra = TSV_CONTENT.replace(
        "V-combines, N-combines", "V-combines, N-combines, A-combines"
    )
    (lang_dir / "diagnostics_lang0001.tsv").write_text(tsv_with_extra)
    _sdy._sync_from_tsv("lang0001", apply=True, drift_entries=[])
    updated = yaml.safe_load((lang_dir / "diagnostics_lang0001.yaml").read_text())
    assert updated["classes"]["metrical"].get("notes") == "test notes"


def test_sync_from_tsv_ambiguous_goes_to_drift(lang_dir):
    """An unknown criterion is flagged as ambiguous and appended to drift_entries."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    tsv_with_unknown = TSV_CONTENT.replace(
        "V-combines, N-combines", "V-combines, N-combines, totally_made_up_zyx"
    )
    (lang_dir / "diagnostics_lang0001.tsv").write_text(tsv_with_unknown)
    drift: list = []
    _sdy._sync_from_tsv("lang0001", apply=True, drift_entries=drift)
    assert len(drift) == 1
    assert drift[0]["lang_id"] == "lang0001"
    assert any(c["kind"] == "unknown_criterion" for c in drift[0]["ambiguous"])


def test_sync_from_tsv_skips_missing_yaml(lang_dir):
    """Returns False when YAML does not exist."""
    (lang_dir / "diagnostics_lang0001.tsv").write_text(TSV_CONTENT)
    drift: list = []
    changed = _sdy._sync_from_tsv("lang0001", apply=False, drift_entries=drift)
    assert changed is False


def test_sync_from_tsv_skips_missing_tsv(lang_dir):
    """Returns False when TSV does not exist."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    drift: list = []
    changed = _sdy._sync_from_tsv("lang0001", apply=False, drift_entries=drift)
    assert changed is False
