"""Tests for coding/sync_qualification_hashes.py."""
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

def test_collect_wanted_covers_all_16_classes():
    wanted = _collect_wanted(None)
    assert len(wanted) == 16


def test_collect_wanted_hashes_are_8_chars():
    wanted = _collect_wanted(None)
    for name, h in wanted.items():
        assert len(h) == 8, f"[{name}] hash is not 8 chars: {h!r}"


def test_collect_wanted_single_class():
    wanted = _collect_wanted("metrical")
    assert set(wanted.keys()) == {"metrical"}


def test_current_hashes_all_stamped():
    current = _current_hashes(None)
    for name, h in current.items():
        assert h is not None, f"[{name}] hash is not stamped"


def test_current_hashes_match_expected():
    wanted = _collect_wanted(None)
    current = _current_hashes(None)
    stale = [(n, wanted[n], current.get(n)) for n in wanted if current.get(n) != wanted[n]]
    assert stale == [], f"Stale hashes after bootstrap: {stale}"


# ---------------------------------------------------------------------------
# _apply_hashes: update existing hash
# ---------------------------------------------------------------------------

_MINIMAL_YAML = """\
classes:

  - name: testclass
    qualification_rule: >
      A position qualifies if free=y.
    qualification_rule_hash: "oldvalue"
    status: stable
"""

_MINIMAL_YAML_NO_HASH = """\
classes:

  - name: testclass
    qualification_rule: >
      A position qualifies if free=y.
    status: stable
"""


def test_apply_hashes_updates_existing(tmp_path, monkeypatch):
    yaml_path = tmp_path / "diagnostic_classes.yaml"
    yaml_path.write_text(_MINIMAL_YAML)

    import coding.sync_qualification_hashes as sqh
    monkeypatch.setattr(sqh, "CLASSES_YAML", yaml_path)

    rule = "A position qualifies if free=y."
    expected = _compute_hash(rule)
    sqh._apply_hashes({"testclass": expected}, {"testclass": "oldvalue"})

    updated = yaml_path.read_text()
    assert f'qualification_rule_hash: "{expected}"' in updated
    assert "oldvalue" not in updated


def test_apply_hashes_inserts_missing(tmp_path, monkeypatch):
    yaml_path = tmp_path / "diagnostic_classes.yaml"
    yaml_path.write_text(_MINIMAL_YAML_NO_HASH)

    import coding.sync_qualification_hashes as sqh
    monkeypatch.setattr(sqh, "CLASSES_YAML", yaml_path)

    rule = "A position qualifies if free=y."
    expected = _compute_hash(rule)
    sqh._apply_hashes({"testclass": expected}, {"testclass": None})

    updated = yaml_path.read_text()
    assert f'qualification_rule_hash: "{expected}"' in updated


def test_apply_hashes_preserves_surrounding_content(tmp_path, monkeypatch):
    yaml_path = tmp_path / "diagnostic_classes.yaml"
    yaml_path.write_text(_MINIMAL_YAML)

    import coding.sync_qualification_hashes as sqh
    monkeypatch.setattr(sqh, "CLASSES_YAML", yaml_path)

    rule = "A position qualifies if free=y."
    expected = _compute_hash(rule)
    sqh._apply_hashes({"testclass": expected}, {"testclass": "oldvalue"})

    updated = yaml_path.read_text()
    assert "status: stable" in updated
    assert "- name: testclass" in updated
