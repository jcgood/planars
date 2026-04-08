"""Tests for coding/check_codebook.py."""
from __future__ import annotations

import hashlib

import pytest

from coding.check_codebook import (
    _collect_coverage,
    _report_schema_stubs,
    _check_qualification_rule_drift,
    _discover_analysis_modules,
    _report_keystone_active_unresolved,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_diagnostics(tmp_path, lang_id: str, classes: list[str]) -> None:
    """Write a minimal diagnostics_{lang_id}.tsv under tmp_path/coded_data/{lang_id}/lang_setup/."""
    d = tmp_path / "coded_data" / lang_id / "lang_setup"
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


# ---------------------------------------------------------------------------
# _discover_analysis_modules
# ---------------------------------------------------------------------------

def test_discover_analysis_modules_finds_known_modules():
    modules = _discover_analysis_modules()
    assert "ciscategorial" in modules
    assert "metrical" in modules
    assert "noninterruption" in modules


def test_discover_analysis_modules_excludes_non_analysis():
    modules = _discover_analysis_modules()
    assert "io" not in modules
    assert "spans" not in modules
    assert "reports" not in modules
    assert "charts" not in modules


# ---------------------------------------------------------------------------
# _check_qualification_rule_drift
# ---------------------------------------------------------------------------

def _make_rule_hash(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:8]


def _diag_class_with_rule(name: str, rule: str, hash_val: str | None = None) -> dict:
    cls: dict = {"name": name, "qualification_rule": rule}
    if hash_val is not None:
        cls["qualification_rule_hash"] = hash_val
    return {name: cls}


def test_qr_drift_all_clean_no_errors(monkeypatch):
    import coding.check_codebook as ccb
    rule = "A position qualifies if free=y."
    expected_hash = _make_rule_hash(rule)
    diag_classes = _diag_class_with_rule("noninterruption", rule, expected_hash)
    monkeypatch.setattr(ccb, "_discover_analysis_modules", lambda: {"noninterruption"})
    errors = _check_qualification_rule_drift(diag_classes)
    assert errors == []


def test_qr_drift_missing_hash_is_warning_not_error(monkeypatch, capsys):
    import coding.check_codebook as ccb
    rule = "A position qualifies if free=y."
    diag_classes = _diag_class_with_rule("noninterruption", rule, hash_val=None)
    monkeypatch.setattr(ccb, "_discover_analysis_modules", lambda: {"noninterruption"})
    errors = _check_qualification_rule_drift(diag_classes)
    assert errors == []
    out = capsys.readouterr().out
    assert "qualification_rule_hash not set" in out


def test_qr_drift_wrong_hash_is_hard_error(monkeypatch):
    import coding.check_codebook as ccb
    rule = "A position qualifies if free=y."
    diag_classes = _diag_class_with_rule("noninterruption", rule, hash_val="deadbeef")
    monkeypatch.setattr(ccb, "_discover_analysis_modules", lambda: {"noninterruption"})
    errors = _check_qualification_rule_drift(diag_classes)
    assert any("mismatch" in e for e in errors)
    assert any("noninterruption" in e for e in errors)


def test_qr_drift_no_rule_skipped(monkeypatch):
    import coding.check_codebook as ccb
    # class has no qualification_rule; module exists → no error (rule not required)
    diag_classes = {"ciscategorial": {"name": "ciscategorial"}}
    monkeypatch.setattr(ccb, "_discover_analysis_modules", lambda: {"ciscategorial"})
    errors = _check_qualification_rule_drift(diag_classes)
    assert errors == []


def test_qr_drift_module_with_no_yaml_class_is_hard_error(monkeypatch):
    import coding.check_codebook as ccb
    # Module is discovered but not in diag_classes → hard error
    monkeypatch.setattr(ccb, "_discover_analysis_modules", lambda: {"biuniqueness"})
    errors = _check_qualification_rule_drift({})
    assert len(errors) == 1
    assert "no entry in diagnostic_classes.yaml" in errors[0]


def test_qr_drift_yaml_class_with_rule_but_no_module_is_warning(monkeypatch, capsys):
    import coding.check_codebook as ccb
    # Class has a rule but no module → warning only
    rule = "Some rule text."
    diag_classes = _diag_class_with_rule("hypothetical_class_xyz", rule, hash_val=None)
    monkeypatch.setattr(ccb, "_discover_analysis_modules", lambda: set())
    errors = _check_qualification_rule_drift(diag_classes)
    assert errors == []
    out = capsys.readouterr().out
    assert "hypothetical_class_xyz" in out
    assert "no `derive` attribute" in out


# ---------------------------------------------------------------------------
# _report_keystone_active_unresolved
# ---------------------------------------------------------------------------

def _make_lang_yaml(tmp_path, lang_id: str, classes: dict) -> None:
    """Write a minimal diagnostics_{lang_id}.yaml under tmp_path/coded_data/{lang_id}/lang_setup/."""
    import yaml
    d = tmp_path / "coded_data" / lang_id / "lang_setup"
    d.mkdir(parents=True)
    data = {"language": lang_id, "classes": classes}
    (d / f"diagnostics_{lang_id}.yaml").write_text(
        yaml.dump(data, default_flow_style=False), encoding="utf-8"
    )


def _dc_needs_review(name: str) -> dict:
    return {name: {"name": name, "keystone_active_default": "[NEEDS REVIEW]"}}


def _dc_resolved(name: str, default: bool) -> dict:
    return {name: {"name": name, "keystone_active_default": default}}


def test_keystone_active_all_resolved_no_output(tmp_path, capsys):
    # Class has a resolved default → no warning even without an override
    diag_classes = _dc_resolved("metrical", True)
    coverage = {"metrical": ["lang0001"]}
    _make_lang_yaml(tmp_path, "lang0001", {"metrical": {"constructions": ["stress_domain"],
                                                         "criteria": {"accented": ["y", "n"]}}})
    count = _report_keystone_active_unresolved(diag_classes, coverage, root=tmp_path)
    assert count == 0
    assert "All active classes" in capsys.readouterr().out


def test_keystone_active_needs_review_no_override_warns(tmp_path, capsys):
    # Class has [NEEDS REVIEW] default, no override in language YAML
    diag_classes = _dc_needs_review("pausing")
    coverage = {"pausing": ["lang0001"]}
    _make_lang_yaml(tmp_path, "lang0001", {"pausing": {"constructions": ["general"],
                                                        "criteria": {"pause_domain": ["y", "n"]}}})
    count = _report_keystone_active_unresolved(diag_classes, coverage, root=tmp_path)
    assert count == 1
    out = capsys.readouterr().out
    assert "lang0001/pausing" in out


def test_keystone_active_needs_review_with_override_clean(tmp_path, capsys):
    # Class has [NEEDS REVIEW] default, but language YAML has an explicit override
    diag_classes = _dc_needs_review("pausing")
    coverage = {"pausing": ["lang0001"]}
    _make_lang_yaml(tmp_path, "lang0001", {
        "pausing": {
            "constructions": ["general"],
            "criteria": {"pause_domain": ["y", "n"]},
            "keystone_active": False,
        }
    })
    count = _report_keystone_active_unresolved(diag_classes, coverage, root=tmp_path)
    assert count == 0


def test_keystone_active_no_yaml_file_counts_as_unresolved(tmp_path, capsys):
    # Language has no YAML at all → treated as unresolved
    diag_classes = _dc_needs_review("pausing")
    coverage = {"pausing": ["lang0001"]}
    # Don't create the YAML file
    (tmp_path / "coded_data" / "lang0001" / "lang_setup").mkdir(parents=True)
    count = _report_keystone_active_unresolved(diag_classes, coverage, root=tmp_path)
    assert count == 1


def test_keystone_active_multiple_langs_partial(tmp_path, capsys):
    # Two languages use a [NEEDS REVIEW] class; one has an override, one doesn't
    diag_classes = _dc_needs_review("pausing")
    coverage = {"pausing": ["lang0001", "lang0002"]}
    _make_lang_yaml(tmp_path, "lang0001", {
        "pausing": {"constructions": ["general"], "criteria": {"pause_domain": ["y", "n"]},
                    "keystone_active": True}
    })
    _make_lang_yaml(tmp_path, "lang0002", {
        "pausing": {"constructions": ["general"], "criteria": {"pause_domain": ["y", "n"]}}
    })
    count = _report_keystone_active_unresolved(diag_classes, coverage, root=tmp_path)
    assert count == 1
    out = capsys.readouterr().out
    assert "lang0002/pausing" in out
    assert "lang0001" not in out
