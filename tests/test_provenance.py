"""Tests for coding/provenance.py (Phase 5 unit E, issue #271).

Provenance capture: log a run only when it actually reaches a Drive-writing
path, derived from each command's own operations.yaml writes_to_drive field
(base + modes), gated per real invocation the same way
coding/preconditions.py gates preconditions -- not per command. These tests
exercise it against the real, live operations.yaml, same reasoning as
tests/test_preconditions.py.
"""
from __future__ import annotations

import json
from argparse import Namespace

import pytest

from coding import provenance


def _ns(**kwargs) -> Namespace:
    return Namespace(**kwargs)


# ---------------------------------------------------------------------------
# writes_to_drive(): per-invocation, not per-command
# ---------------------------------------------------------------------------

def test_update_sheets_apply_writes_to_drive():
    assert provenance.writes_to_drive("update_sheets", _ns(apply=True)) is True


def test_update_sheets_dry_run_does_not_write_to_drive():
    assert provenance.writes_to_drive("update_sheets", _ns(apply=False)) is False


def test_sync_diagnostics_yaml_default_direction_does_not_write_to_drive():
    """The default (YAML -> TSV) and --from-tsv directions only touch local
    files; only --to-sheet reaches the live Sheet."""
    args = _ns(apply=True, to_sheet=False, from_tsv=False)
    assert provenance.writes_to_drive("sync_diagnostics_yaml", args) is False


def test_sync_diagnostics_yaml_to_sheet_writes_to_drive():
    args = _ns(apply=True, to_sheet=True, from_tsv=False)
    assert provenance.writes_to_drive("sync_diagnostics_yaml", args) is True


def test_sync_diagnostics_yaml_from_tsv_does_not_write_to_drive():
    args = _ns(apply=True, to_sheet=False, from_tsv=True)
    assert provenance.writes_to_drive("sync_diagnostics_yaml", args) is False


def test_import_planar_default_direction_does_not_write_to_drive():
    args = _ns(apply=True, to_sheet=False)
    assert provenance.writes_to_drive("import_planar", args) is False


def test_import_planar_to_sheet_writes_to_drive():
    args = _ns(apply=True, to_sheet=True)
    assert provenance.writes_to_drive("import_planar", args) is True


def test_generate_sheets_regen_dependents_writes_to_drive_even_without_apply():
    """--regen-dependents has no --apply gate of its own -- it's live whenever passed."""
    args = _ns(apply=False, regen_construction=None, regen_dependents=True)
    assert provenance.writes_to_drive("generate_sheets", args) is True


def test_read_only_commands_never_write_to_drive():
    for op_id in ["capture_drive_state", "integrity_check", "check_codebook",
                  "registry", "lookup_lang", "validation_report"]:
        assert provenance.writes_to_drive(op_id, _ns(apply=True)) is False


def test_apply_pending_never_logs_its_own_writes():
    """Its Drive-writing work is delegated to a subprocess call to another
    python -m coding ... --apply, which logs itself independently -- logging
    apply-pending too would double-count the same change."""
    assert provenance.writes_to_drive("apply_pending", _ns(apply=True)) is False


def test_unknown_op_id_does_not_write_to_drive():
    assert provenance.writes_to_drive("not_a_real_command", _ns()) is False


# ---------------------------------------------------------------------------
# record(): actually appends (or doesn't)
# ---------------------------------------------------------------------------

def test_record_appends_one_line_when_it_writes_to_drive(tmp_path):
    log_path = tmp_path / "provenance_log.jsonl"
    provenance.record("update-sheets", "update_sheets", _ns(apply=True), log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["command"] == "update-sheets"
    assert entry["args"] == {"apply": True}
    assert entry["timestamp"].endswith("Z")


def test_record_appends_nothing_on_a_dry_run(tmp_path):
    log_path = tmp_path / "provenance_log.jsonl"
    provenance.record("update-sheets", "update_sheets", _ns(apply=False), log_path=log_path)
    assert not log_path.exists()


def test_record_appends_across_multiple_calls(tmp_path):
    log_path = tmp_path / "provenance_log.jsonl"
    provenance.record("update-sheets", "update_sheets", _ns(apply=True), log_path=log_path)
    provenance.record("prune-manifest", "prune_manifest", _ns(apply=True), log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(l)["command"] for l in lines] == ["update-sheets", "prune-manifest"]
