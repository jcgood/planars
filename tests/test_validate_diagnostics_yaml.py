"""Tests for validate_diagnostics_yaml() in coding/validate_diagnostics.py."""
from __future__ import annotations

import pytest

from coding.validate_diagnostics import validate_diagnostics_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_data(lang_id: str = "stan1293") -> dict:
    return {
        "language": lang_id,
        "classes": {
            "ciscategorial": {
                "constructions": ["general"],
                "criteria": {
                    "V-combines": ["y", "n"],
                    "N-combines": ["y", "n"],
                    "A-combines": ["y", "n"],
                },
            }
        },
    }


def _errors(data, lang_id="stan1293"):
    return [i for i in validate_diagnostics_yaml(data, lang_id) if i.level == "error"]


def _warnings(data, lang_id="stan1293"):
    return [i for i in validate_diagnostics_yaml(data, lang_id) if i.level == "warning"]


# ---------------------------------------------------------------------------
# Check 1: top-level structure
# ---------------------------------------------------------------------------

def test_valid_data_has_no_errors():
    assert _errors(_valid_data()) == []


def test_non_dict_root_is_error():
    errs = _errors(["not", "a", "dict"])
    assert any("root must be a mapping" in e.message for e in errs)


def test_language_mismatch_is_error():
    data = _valid_data("stan1293")
    errs = _errors(data, "arao1248")
    assert any("does not match expected" in e.message for e in errs)


def test_missing_classes_is_error():
    data = {"language": "stan1293"}
    errs = _errors(data)
    assert any("classes" in e.message for e in errs)


def test_empty_classes_is_error():
    data = {"language": "stan1293", "classes": {}}
    errs = _errors(data)
    assert any("classes" in e.message for e in errs)


# ---------------------------------------------------------------------------
# Check 2: constructions
# ---------------------------------------------------------------------------

def test_missing_constructions_is_error():
    data = _valid_data()
    del data["classes"]["ciscategorial"]["constructions"]
    errs = _errors(data)
    assert any("constructions" in e.message for e in errs)


def test_empty_constructions_is_error():
    data = _valid_data()
    data["classes"]["ciscategorial"]["constructions"] = []
    errs = _errors(data)
    assert any("constructions" in e.message for e in errs)


def test_general_with_others_is_error():
    data = _valid_data()
    data["classes"]["ciscategorial"]["constructions"] = ["general", "also_this"]
    errs = _errors(data)
    assert any("general" in e.message for e in errs)


def test_duplicate_construction_is_error():
    data = _valid_data()
    data["classes"]["ciscategorial"]["constructions"] = ["general", "general"]
    errs = _errors(data)
    assert any("Duplicate" in e.message for e in errs)


# ---------------------------------------------------------------------------
# Check 3: criteria
# ---------------------------------------------------------------------------

def test_missing_criteria_is_error():
    data = _valid_data()
    del data["classes"]["ciscategorial"]["criteria"]
    errs = _errors(data)
    assert any("criteria" in e.message for e in errs)


def test_empty_criterion_value_list_is_error():
    data = _valid_data()
    data["classes"]["ciscategorial"]["criteria"]["V-combines"] = []
    errs = _errors(data)
    assert any("non-empty list" in e.message for e in errs)


def test_unknown_criterion_is_warning():
    data = _valid_data()
    data["classes"]["ciscategorial"]["criteria"]["totally_made_up_zyx"] = ["y", "n"]
    warns = _warnings(data)
    assert any("totally_made_up_zyx" in w.message for w in warns)


# ---------------------------------------------------------------------------
# Check 4: class names vs. analysis modules
# ---------------------------------------------------------------------------

def test_unknown_class_is_warning():
    data = {
        "language": "stan1293",
        "classes": {
            "made_up_class_xyz": {
                "constructions": ["general"],
                "criteria": {"V-combines": ["y", "n"]},
            }
        },
    }
    warns = _warnings(data)
    assert any("made_up_class_xyz" in w.message for w in warns)


# ---------------------------------------------------------------------------
# Check 6: Glottocode format
# ---------------------------------------------------------------------------

def test_invalid_glottocode_format_is_warning():
    data = _valid_data("not_a_glottocode")
    warns = _warnings(data, "not_a_glottocode")
    assert any("Glottocode format" in w.message for w in warns)
