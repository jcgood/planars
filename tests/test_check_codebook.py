"""Tests for coverage-reporting additions to coding/check_codebook.py."""
from __future__ import annotations

import pytest

from coding.check_codebook import _collect_coverage, _report_schema_stubs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_diagnostics(tmp_path, lang_id: str, classes: list[str]) -> None:
    """Write a minimal diagnostics_{lang_id}.tsv under tmp_path/coded_data/{lang_id}/planar_input/."""
    d = tmp_path / "coded_data" / lang_id / "planar_input"
    d.mkdir(parents=True)
    lines = ["Class\tLanguage\tConstructions\tCriteria"]
    for cls in classes:
        lines.append(f"{cls}\t{lang_id}\tgeneral\tfree")
    (d / f"diagnostics_{lang_id}.tsv").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# _collect_coverage
# ---------------------------------------------------------------------------

def test_collect_coverage_single_lang_single_class(tmp_path):
    _write_diagnostics(tmp_path, "lang0001", ["ciscategorial"])
    assert _collect_coverage(tmp_path) == {"ciscategorial": ["lang0001"]}


def test_collect_coverage_single_lang_multiple_classes(tmp_path):
    _write_diagnostics(tmp_path, "lang0001", ["ciscategorial", "noninterruption"])
    cov = _collect_coverage(tmp_path)
    assert set(cov.keys()) == {"ciscategorial", "noninterruption"}
    assert cov["ciscategorial"] == ["lang0001"]


def test_collect_coverage_multiple_langs(tmp_path):
    _write_diagnostics(tmp_path, "lang0001", ["ciscategorial"])
    _write_diagnostics(tmp_path, "lang0002", ["ciscategorial", "metrical"])
    cov = _collect_coverage(tmp_path)
    assert sorted(cov["ciscategorial"]) == ["lang0001", "lang0002"]
    assert cov["metrical"] == ["lang0002"]


def test_collect_coverage_absent_class_not_in_result(tmp_path):
    _write_diagnostics(tmp_path, "lang0001", ["ciscategorial"])
    cov = _collect_coverage(tmp_path)
    assert "nonpermutability" not in cov


def test_collect_coverage_empty_coded_data(tmp_path):
    (tmp_path / "coded_data").mkdir()
    assert _collect_coverage(tmp_path) == {}


# ---------------------------------------------------------------------------
# _report_schema_stubs
# ---------------------------------------------------------------------------

def _minimal_diag_classes(*names: str) -> dict:
    """Build a minimal diag_classes dict for the given class names."""
    return {
        name: {
            "name": name,
            "specificity": "general",
            "required_criteria": ["free"],
            "known_constructions": [],
        }
        for name in names
    }


def test_report_schema_stubs_none_uncovered(capsys):
    diag_classes = _minimal_diag_classes("ciscategorial")
    coverage = {"ciscategorial": ["lang0001"]}
    count = _report_schema_stubs(diag_classes, coverage)
    assert count == 0
    out = capsys.readouterr().out
    assert "All schema classes" in out


def test_report_schema_stubs_one_uncovered(capsys):
    diag_classes = _minimal_diag_classes("ciscategorial", "nonpermutability")
    coverage = {"ciscategorial": ["lang0001"]}
    count = _report_schema_stubs(diag_classes, coverage)
    assert count == 1
    out = capsys.readouterr().out
    assert "nonpermutability" in out
    assert "ciscategorial" not in out


def test_report_schema_stubs_all_uncovered(capsys):
    diag_classes = _minimal_diag_classes("free_occurrence", "repair")
    coverage = {}
    count = _report_schema_stubs(diag_classes, coverage)
    assert count == 2
    out = capsys.readouterr().out
    assert "free_occurrence" in out
    assert "repair" in out


def test_report_schema_stubs_construction_specific(capsys):
    diag_classes = {
        "idiom": {
            "name": "idiom",
            "specificity": "construction_specific",
            "required_criteria": ["idiomatic"],
            "known_constructions": ["verb-particle idiom"],
        }
    }
    coverage = {}
    _report_schema_stubs(diag_classes, coverage)
    out = capsys.readouterr().out
    assert "verb-particle idiom" in out
