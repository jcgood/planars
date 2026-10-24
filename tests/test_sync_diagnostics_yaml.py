"""Tests for coding/sync_diagnostics_yaml.py — _sync_to_tsv. (The Sheet
direction is in test_sync_diagnostics_yaml_snapshot.py; --from-tsv was
retired in Phase 10 unit 11b.)"""
from __future__ import annotations

import textwrap

import pandas as pd
import pytest

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

# _sync_to_tsv gates on validate_diagnostics_yaml's errors, including check 9
# (every collection_required: "y" class must be present) — YAML_CONTENT above
# omits those classes, so it is used only for the validation-error test;
# the other tests need a genuinely valid YAML, so they exercise the
# create/update/no-change logic rather than the required-classes gate.
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
    """Set up a coded_data/lang0001/lang_setup/ tree and point CODED_DATA (the
    command's and the local-file door's) at it. The tests call the sync
    functions directly, so they run inside a command run, as the dispatcher's
    would be, for the door's sake."""
    from coding import drive_door, file_door
    d = tmp_path / "coded_data" / "lang0001" / "lang_setup"
    d.mkdir(parents=True)
    monkeypatch.setattr(_sdy, "CODED_DATA", tmp_path / "coded_data")
    monkeypatch.setattr(file_door, "CODED_DATA", tmp_path / "coded_data")
    with drive_door.running("sync-diagnostics-yaml-test", may_write=True):
        yield d


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
