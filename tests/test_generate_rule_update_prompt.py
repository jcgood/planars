"""Tests for coding/generate_rule_update_prompt.py."""
from __future__ import annotations

import hashlib

import pytest

from coding.generate_rule_update_prompt import (
    _normalize,
    _compute_hash,
    _stale_classes,
    _generate_prompt,
)


def _make_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# _stale_classes against live YAML
# ---------------------------------------------------------------------------

def test_stale_classes_empty_when_all_hashes_current():
    stale = _stale_classes(None)
    assert stale == [], f"Expected no stale classes, got: {[c['name'] for c in stale]}"


def test_stale_classes_single_class_filter():
    stale = _stale_classes("metrical")
    assert stale == []


def test_stale_classes_unknown_class_filter_returns_empty():
    stale = _stale_classes("nonexistent_class_xyz")
    assert stale == []


# ---------------------------------------------------------------------------
# _generate_prompt output structure
# ---------------------------------------------------------------------------

def _fake_cls(name: str, rule: str, hash_val: str | None = None) -> dict:
    cls: dict = {"name": name, "display_name": name.title(), "qualification_rule": rule}
    if hash_val is not None:
        cls["qualification_rule_hash"] = hash_val
    return cls


def test_generate_prompt_contains_class_name():
    cls = _fake_cls("metrical", "Some rule.", hash_val="deadbeef")
    prompt = _generate_prompt(cls)
    assert "metrical" in prompt


def test_generate_prompt_contains_rule_text():
    rule = "A position qualifies if free=y."
    cls = _fake_cls("testcls", rule, hash_val="deadbeef")
    prompt = _generate_prompt(cls)
    assert rule in prompt


def test_generate_prompt_contains_sync_command():
    cls = _fake_cls("metrical", "Some rule.", hash_val="deadbeef")
    prompt = _generate_prompt(cls)
    assert "sync-qualification-hashes" in prompt
    assert "--class metrical" in prompt


def test_generate_prompt_update_existing_module():
    cls = _fake_cls("metrical", "Some rule.", hash_val="deadbeef")
    prompt = _generate_prompt(cls)
    assert "update" in prompt.lower()
    assert "planars/metrical.py" in prompt


def test_generate_prompt_new_module_no_source(tmp_path, monkeypatch):
    import coding.generate_rule_update_prompt as grp
    # Point PLANARS_DIR somewhere that doesn't have the module
    monkeypatch.setattr(grp, "PLANARS_DIR", tmp_path)
    cls = _fake_cls("brand_new_class", "Some rule.", hash_val="deadbeef")
    prompt = grp._generate_prompt(cls)
    assert "from scratch" in prompt
    assert "planars/brand_new_class.py" in prompt


def test_generate_prompt_is_a_pure_function_of_its_input(tmp_path, monkeypatch):
    """Idempotency (Phase 8 of the data layer redesign, issue #271) --
    operations.yaml's own claim: "pure function of the current hash-mismatch
    state -- same input state produces the same prompt text." No existing
    test called _generate_prompt twice with the same class dict; this proves
    it directly, including against the module-source-reading branch
    (test_generate_prompt_update_existing_module's path), not just the
    no-source branch already exercised above.
    """
    import coding.generate_rule_update_prompt as grp
    cls = _fake_cls("metrical", "A position qualifies if free=y.", hash_val="deadbeef")
    first = grp._generate_prompt(cls)
    second = grp._generate_prompt(cls)
    assert second == first
