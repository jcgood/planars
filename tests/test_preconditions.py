"""Tests for coding/preconditions.py (Phase 5 unit D, issue #271).

Centralized precondition enforcement, driven directly off each command's
own data_dependency_schema/operations.yaml record rather than a scattered,
hand-written drive._check_coded_data_clean() call per file. These tests
exercise active_preconditions()/enforce() against the real, live
operations.yaml -- not a copy pinned here -- the same reasoning
test_registry.py uses: a hand-copied expectation could drift out of sync
with the record it's meant to check.
"""
from __future__ import annotations

from argparse import Namespace

import pytest

from coding import preconditions


def _ns(**kwargs) -> Namespace:
    """A minimal argparse.Namespace with only the dests a test cares about.
    getattr(args, dest, False) in preconditions.py means an absent dest
    reads as falsy, same as an unset store_true flag really would.
    """
    return Namespace(**kwargs)


# ---------------------------------------------------------------------------
# generate-sheets: base has no precondition; --regen-dependents does (a
# mode with a null apply_gate, active on its own flag); --regen-construction
# doesn't.
# ---------------------------------------------------------------------------

def test_generate_sheets_base_apply_has_no_precondition():
    args = _ns(apply=True, regen_construction=None, regen_dependents=False)
    assert preconditions.active_preconditions("generate_sheets", args) == []


def test_generate_sheets_regen_dependents_requires_clean_tree():
    args = _ns(apply=False, regen_construction=None, regen_dependents=True)
    assert preconditions.active_preconditions("generate_sheets", args) == [
        "coded_data_clean_tree"
    ]


def test_generate_sheets_regen_construction_has_no_precondition():
    args = _ns(apply=False, regen_construction="metrical:stress_domain", regen_dependents=False)
    assert preconditions.active_preconditions("generate_sheets", args) == []


# ---------------------------------------------------------------------------
# sync-params: base --apply requires coded_data_clean_tree; the
# --refresh-dropdowns mode restates the same precondition under its own
# fuller gate ("--apply --refresh-dropdowns") -- both being active at once
# must dedupe to one entry, not two.
# ---------------------------------------------------------------------------

def test_sync_params_apply_requires_clean_tree():
    args = _ns(apply=True, refresh_dropdowns=False)
    assert preconditions.active_preconditions("sync_params", args) == [
        "coded_data_clean_tree"
    ]


def test_sync_params_dry_run_has_no_precondition():
    args = _ns(apply=False, refresh_dropdowns=False)
    assert preconditions.active_preconditions("sync_params", args) == []


def test_sync_params_apply_and_refresh_dropdowns_dedupes_to_one_entry():
    args = _ns(apply=True, refresh_dropdowns=True)
    assert preconditions.active_preconditions("sync_params", args) == [
        "coded_data_clean_tree"
    ]


# ---------------------------------------------------------------------------
# sync-diagnostics-yaml: all three directions (base, --to-sheet, --from-tsv)
# require coded_data_clean_tree -- this is the command whose enforcement
# call needs the (".yaml", ".tsv") extensions exception, checked via enforce()
# below rather than active_preconditions() (which only reports ids, not
# enforcement parameters).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    dict(apply=True, to_sheet=False, from_tsv=False),
    dict(apply=True, to_sheet=True, from_tsv=False),
    dict(apply=True, to_sheet=False, from_tsv=True),
])
def test_sync_diagnostics_yaml_every_direction_requires_clean_tree(kwargs):
    assert preconditions.active_preconditions("sync_diagnostics_yaml", _ns(**kwargs)) == [
        "coded_data_clean_tree"
    ]


def test_sync_diagnostics_yaml_dry_run_has_no_precondition():
    args = _ns(apply=False, to_sheet=False, from_tsv=False)
    assert preconditions.active_preconditions("sync_diagnostics_yaml", args) == []


# ---------------------------------------------------------------------------
# import-sheets / prune-manifest / update-sheets: a plain --apply gate, no
# modes, coded_data_clean_tree the only declared precondition.
# restructure-sheets also declares coded_data_git_identity_configured
# (checked separately below, since it has no central enforcer either).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("op_id", ["import_sheets", "prune_manifest", "update_sheets"])
def test_apply_only_commands_require_clean_tree_on_apply(op_id):
    assert preconditions.active_preconditions(op_id, _ns(apply=True)) == [
        "coded_data_clean_tree"
    ]


@pytest.mark.parametrize("op_id", ["import_sheets", "prune_manifest", "update_sheets"])
def test_apply_only_commands_have_no_precondition_on_dry_run(op_id):
    assert preconditions.active_preconditions(op_id, _ns(apply=False)) == []


def test_restructure_sheets_apply_requires_clean_tree_and_git_identity():
    assert preconditions.active_preconditions("restructure_sheets", _ns(apply=True)) == [
        "coded_data_clean_tree", "coded_data_git_identity_configured",
    ]


# ---------------------------------------------------------------------------
# Preconditions with no central enforcer (coded_data_git_identity_configured,
# check_notes_documents_scope_authorized) are still reported by
# active_preconditions() -- they ARE declared -- but enforce() must not call
# the coded_data_clean_tree enforcer for them, and must not raise just
# because no enforcer is registered.
# ---------------------------------------------------------------------------

def test_import_planar_git_identity_precondition_is_reported_but_not_enforced_here(monkeypatch):
    calls = []
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: calls.append(kw))
    args = _ns(apply=True, to_sheet=False)
    assert preconditions.active_preconditions("import_planar", args) == [
        "coded_data_git_identity_configured"
    ]
    preconditions.enforce("import_planar", args)  # must not raise
    assert calls == []


def test_check_notes_scope_precondition_is_reported_but_not_enforced_here(monkeypatch):
    calls = []
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: calls.append(kw))
    args = _ns(apply=True)
    assert preconditions.active_preconditions("check_notes", args) == [
        "check_notes_documents_scope_authorized"
    ]
    preconditions.enforce("check_notes", args)  # must not raise
    assert calls == []


# ---------------------------------------------------------------------------
# Unknown command: no matching operations.yaml record.
# ---------------------------------------------------------------------------

def test_unknown_op_id_has_no_preconditions():
    assert preconditions.active_preconditions("not_a_real_command", _ns()) == []


# ---------------------------------------------------------------------------
# enforce(): actually calls the registered enforcer with the right
# extensions -- the one place the per-command exception
# (sync_diagnostics_yaml needs both ".yaml" and ".tsv") is exercised.
# ---------------------------------------------------------------------------

def test_enforce_calls_check_coded_data_clean_with_tsv_only_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: calls.append(kw))
    preconditions.enforce("update_sheets", _ns(apply=True))
    assert calls == [{"extensions": (".tsv",)}]


def test_enforce_calls_check_coded_data_clean_with_yaml_and_tsv_for_sync_diagnostics_yaml(monkeypatch):
    calls = []
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: calls.append(kw))
    preconditions.enforce("sync_diagnostics_yaml", _ns(apply=True, to_sheet=False, from_tsv=False))
    assert calls == [{"extensions": (".yaml", ".tsv")}]


def test_enforce_skips_the_unenforced_git_identity_precondition_for_restructure_sheets(monkeypatch):
    calls = []
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: calls.append(kw))
    preconditions.enforce("restructure_sheets", _ns(apply=True))
    assert calls == [{"extensions": (".tsv",)}]  # one call, for coded_data_clean_tree only


def test_enforce_calls_nothing_on_a_dry_run(monkeypatch):
    calls = []
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: calls.append(kw))
    preconditions.enforce("update_sheets", _ns(apply=False))
    assert calls == []
