"""Tests for coding/sync_diagnostics_yaml.py — _load_valid_yaml, the gate
before any Sheet is touched. (The Sheet push itself is in
test_sync_diagnostics_yaml_snapshot.py. The YAML → TSV direction these tests
covered until 2026-10-27 went with the TSV; --from-tsv was retired in
Phase 10 unit 11b.)"""
from __future__ import annotations

import textwrap

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


@pytest.fixture()
def lang_dir(tmp_path, monkeypatch):
    """A coded_data/lang0001/lang_setup/ tree, with the command's CODED_DATA
    pointed at it."""
    d = tmp_path / "coded_data" / "lang0001" / "lang_setup"
    d.mkdir(parents=True)
    monkeypatch.setattr(_sdy, "CODED_DATA", tmp_path / "coded_data")
    return d


def test_a_missing_yaml_is_skipped_without_an_error(lang_dir):
    error_langs: list = []
    assert _sdy._load_valid_yaml("lang0001", error_langs) is None
    assert error_langs == []          # a missing YAML isn't a validation error


def test_a_blocking_error_skips_the_language_and_is_reported(lang_dir):
    (lang_dir / "diagnostics_lang0001.yaml").write_text(
        YAML_CONTENT.replace("language: lang0001", "language: other_lang"))
    error_langs: list = []
    assert _sdy._load_valid_yaml("lang0001", error_langs) is None
    # issue #283: a blocking validation error used to be visible only in the
    # printed log -- error_langs is what lets main() turn it into a non-zero
    # exit code so the daily automation actually notices.
    assert error_langs == ["lang0001"]


def test_a_non_blocking_error_does_not_withhold_the_push(lang_dir):
    """YAML_CONTENT lacks the collection_required classes: an error, but not
    a blocking one (a class not drafted yet), so the YAML is still pushed."""
    (lang_dir / "diagnostics_lang0001.yaml").write_text(YAML_CONTENT)
    error_langs: list = []
    data = _sdy._load_valid_yaml("lang0001", error_langs)
    assert data is not None and set(data["classes"]) == {"ciscategorial", "metrical"}
    assert error_langs == []
