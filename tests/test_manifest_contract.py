"""Tests for coding/manifest_contract.py (Phase 6 boundary 4, issue #271).

check() is deliberately permissive and deliberately never raises -- see the
module docstring for why. These tests pin both of those promises directly,
plus validate against the real captured fixture so the model is checked
against real manifest shape, not just synthetic examples.
"""
from __future__ import annotations

import json
from pathlib import Path

from coding.manifest_contract import check

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "drive_state" / "manifest.json"


def test_real_fixture_validates_clean():
    manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert check(manifest) == []


def test_minimal_entry_is_fine():
    # Every field is Optional -- a language entry with nothing but a name
    # must not be flagged.
    assert check({"lang0001": {}}) == []


def test_unrecognized_fields_are_never_a_problem():
    # extra="allow" at every level: a brand-new field this model has never
    # seen must not fail. This is the central design promise -- a schema
    # that changes weekly with new language-onboarding fields can't be
    # allowed to treat "unknown" as "wrong".
    assert check({
        "lang0001": {
            "folder_id": "abc",
            "a_field_from_next_months_feature": {"nested": ["whatever"]},
        }
    }) == []


def test_leading_underscore_keys_are_excluded_not_validated():
    # drive_config.json's own bookkeeping (_planars_config_file_id etc.)
    # sometimes ends up merged into the same dict by a caller -- it isn't a
    # language entry and was never meant to satisfy this shape.
    assert check({"_planars_config_file_id": "xyz", "lang0001": {}}) == []


def test_non_dict_language_entry_is_flagged():
    problems = check({"lang0001": "not-a-dict"})
    assert len(problems) == 1
    assert "lang0001" in problems[0]


def test_non_dict_top_level_does_not_raise():
    # check()'s own promise: never raises, regardless of what full_config
    # actually is.
    problems = check("not-even-a-dict-of-dicts")
    assert len(problems) == 1
    assert "not shaped like" in problems[0]


def test_none_does_not_raise():
    problems = check(None)
    assert len(problems) == 1
