"""Tests for coding/sync_qualification_hashes.py.

qualification_rule lives in diagnostic_classes.yaml (research content);
qualification_rule_hash lives in diagnostic_classes_status.yaml (process
tracking) — split in Phase 3 of the data layer redesign (issue #271). This
script reads the rule from one file and stamps the hash into the other.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from coding.sync_qualification_hashes import (
    _normalize,
    _compute_hash,
    _collect_wanted,
    _current_hashes,
    _apply_hashes,
)

# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------

def test_normalize_collapses_whitespace():
    assert _normalize("  a  b\n  c  ") == "a b c"


def test_compute_hash_deterministic():
    h1 = _compute_hash("A position qualifies if free=y.")
    h2 = _compute_hash("A position qualifies if free=y.")
    assert h1 == h2
    assert len(h1) == 8


def test_compute_hash_whitespace_insensitive():
    h1 = _compute_hash("A position qualifies if free=y.")
    h2 = _compute_hash("A  position\n  qualifies   if free=y.")
    assert h1 == h2


# ---------------------------------------------------------------------------
# Live YAML: _collect_wanted and _current_hashes
# ---------------------------------------------------------------------------

def test_collect_wanted_covers_all_18_classes():
    wanted = _collect_wanted(None)
    assert len(wanted) == 18


def test_collect_wanted_hashes_are_8_chars():
    wanted = _collect_wanted(None)
    for name, h in wanted.items():
        assert len(h) == 8, f"[{name}] hash is not 8 chars: {h!r}"


def test_collect_wanted_single_class():
    wanted = _collect_wanted("metrical")
    assert set(wanted.keys()) == {"metrical"}


def test_current_hashes_all_stamped():
    wanted = _collect_wanted(None)
    current = _current_hashes(None, wanted)
    for name, h in current.items():
        assert h is not None, f"[{name}] hash is not stamped"


def test_current_hashes_match_expected():
    wanted = _collect_wanted(None)
    current = _current_hashes(None, wanted)
    stale = [(n, wanted[n], current.get(n)) for n in wanted if current.get(n) != wanted[n]]
    assert stale == [], f"Stale hashes after bootstrap: {stale}"


# ---------------------------------------------------------------------------
# _apply_hashes: update existing hash (writes only to STATUS_YAML)
# ---------------------------------------------------------------------------

_MINIMAL_STATUS_YAML = """\
classes:

  - name: testclass
    qualification_rule_hash: "oldvalue"
    status: stable
"""

_MINIMAL_STATUS_YAML_NO_HASH = """\
classes:

  - name: testclass
    status: stable
"""

# Regression fixture: a two-stage class whose sheet_instructions (a multi-line
# `>` block scalar) comes BEFORE qualification_rule_hash in the status file —
# the shape nonpermutability, coreference, and phrasal_accent actually have.
# The block-scalar continuation lines must not be mistaken for a new field or
# a new class boundary.
_TWO_STAGE_STATUS_YAML_NO_HASH = """\
classes:

  - name: twostageclass
    sheet_instructions: >
      STEP 1 — prescreening: annotate accented.
        y = eligible
        n = excluded
      STEP 2 — general: annotate joint_accent.
    status: "[NEEDS REVIEW]"
"""


def test_apply_hashes_updates_existing(tmp_path, monkeypatch):
    status_path = tmp_path / "diagnostic_classes_status.yaml"
    status_path.write_text(_MINIMAL_STATUS_YAML)

    import coding.sync_qualification_hashes as sqh
    monkeypatch.setattr(sqh, "STATUS_YAML", status_path)

    rule = "A position qualifies if free=y."
    expected = _compute_hash(rule)
    sqh._apply_hashes({"testclass": expected})

    updated = status_path.read_text()
    assert f'qualification_rule_hash: "{expected}"' in updated
    assert "oldvalue" not in updated


def test_apply_hashes_inserts_missing(tmp_path, monkeypatch):
    status_path = tmp_path / "diagnostic_classes_status.yaml"
    status_path.write_text(_MINIMAL_STATUS_YAML_NO_HASH)

    import coding.sync_qualification_hashes as sqh
    monkeypatch.setattr(sqh, "STATUS_YAML", status_path)

    rule = "A position qualifies if free=y."
    expected = _compute_hash(rule)
    sqh._apply_hashes({"testclass": expected})

    updated = status_path.read_text()
    assert f'qualification_rule_hash: "{expected}"' in updated
    assert yaml.safe_load(updated)["classes"][0]["status"] == "stable"


def test_apply_hashes_two_stage_class_sheet_instructions_block_not_mistaken_for_boundary(tmp_path, monkeypatch):
    """Regression test: a multi-line sheet_instructions block (indent 6 content,
    itself containing lines that look like 'y = ...'/'n = ...') must not be
    mistaken for a new field or class boundary, or the hash never gets
    inserted for a two-stage class."""
    status_path = tmp_path / "diagnostic_classes_status.yaml"
    status_path.write_text(_TWO_STAGE_STATUS_YAML_NO_HASH)

    import coding.sync_qualification_hashes as sqh
    monkeypatch.setattr(sqh, "STATUS_YAML", status_path)

    rule = "[DEFERRED] Derivation not yet decided."
    expected = _compute_hash(rule)
    sqh._apply_hashes({"twostageclass": expected})

    updated = status_path.read_text()
    assert f'qualification_rule_hash: "{expected}"' in updated
    parsed = yaml.safe_load(updated)["classes"][0]
    # The sheet_instructions block must survive untouched.
    assert "STEP 1" in parsed["sheet_instructions"]
    assert "STEP 2" in parsed["sheet_instructions"]
    assert parsed["status"] == "[NEEDS REVIEW]"


def test_apply_hashes_preserves_surrounding_content(tmp_path, monkeypatch):
    status_path = tmp_path / "diagnostic_classes_status.yaml"
    status_path.write_text(_MINIMAL_STATUS_YAML)

    import coding.sync_qualification_hashes as sqh
    monkeypatch.setattr(sqh, "STATUS_YAML", status_path)

    rule = "A position qualifies if free=y."
    expected = _compute_hash(rule)
    sqh._apply_hashes({"testclass": expected})

    updated = status_path.read_text()
    assert "status: stable" in updated
    assert "- name: testclass" in updated


def test_a_second_apply_with_nothing_changed_writes_the_same_file(tmp_path, monkeypatch):
    """Idempotency (Phase 8 of the data layer redesign, issue #271) --
    operations.yaml's own claim: "re-running with nothing changed re-derives
    and writes the same hash value." No existing test called _apply_hashes
    twice; this proves it directly rather than trusting the claim's own
    determinism tests (test_compute_hash_deterministic) to stand in for it.
    """
    status_path = tmp_path / "diagnostic_classes_status.yaml"
    status_path.write_text(_MINIMAL_STATUS_YAML)

    import coding.sync_qualification_hashes as sqh
    monkeypatch.setattr(sqh, "STATUS_YAML", status_path)

    rule = "A position qualifies if free=y."
    expected = _compute_hash(rule)
    sqh._apply_hashes({"testclass": expected})
    first_write = status_path.read_text()

    sqh._apply_hashes({"testclass": expected})
    second_write = status_path.read_text()

    assert second_write == first_write
