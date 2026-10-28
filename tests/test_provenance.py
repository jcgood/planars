"""Tests for coding/provenance.py (issue #271).

writes_to_drive(): whether an invocation may write to Drive at all (the
Drive door refuses every write when it says no), derived from each
command's own operations.yaml writes_to_drive field (base + modes), gated
per real invocation the same way coding/preconditions.py gates
preconditions -- not per command. These tests exercise it against the real,
live operations.yaml, same reasoning as tests/test_preconditions.py.

append_writes(): the log itself. What goes into it -- one line per tab or
file a command wrote -- is the Drive door's, tested in tests/test_drive_door.py.
"""
from __future__ import annotations

import json
from argparse import Namespace

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


def test_sync_diagnostics_yaml_writes_to_drive_only_with_apply():
    """Its one job, since the TSV copy went (2026-10-27), is the diagnostics Sheet."""
    assert provenance.writes_to_drive("sync_diagnostics_yaml", _ns(apply=True)) is True
    assert provenance.writes_to_drive("sync_diagnostics_yaml", _ns(apply=False)) is False


def test_sync_planar_writes_to_drive_only_with_apply():
    """With --apply it updates the planar Sheet (and may renumber the class
    sheets' position cells first); a dry run never writes."""
    assert provenance.writes_to_drive("sync_planar", _ns(apply=True)) is True
    assert provenance.writes_to_drive("sync_planar", _ns(apply=False)) is False


def test_generate_sheets_regen_dependents_writes_to_drive_even_without_apply():
    """--regen-dependents has no --apply gate of its own -- it's live whenever passed."""
    args = _ns(apply=False, regen_construction=None, regen_dependents=True)
    assert provenance.writes_to_drive("generate_sheets", args) is True


def test_read_only_commands_never_write_to_drive():
    for op_id in ["capture_drive_state", "integrity_check", "check_codebook",
                  "registry", "lookup_lang", "validation_report"]:
        assert provenance.writes_to_drive(op_id, _ns(apply=True)) is False


def test_unknown_op_id_does_not_write_to_drive():
    assert provenance.writes_to_drive("not_a_real_command", _ns()) is False


# ---------------------------------------------------------------------------
# append_writes(): actually appends
# ---------------------------------------------------------------------------

def test_append_writes_adds_one_line_per_entry_across_calls():
    """Through the local-file door, so inside a command (the log is
    state_files.PROVENANCE_LOG, in tmp_path: tests/conftest.py)."""
    from coding import drive_door, state_files
    with drive_door.running("update-sheets", may_write=True):
        provenance.append_writes([{"command": "update-sheets", "tab": "general"},
                                  {"command": "update-sheets", "tab": "Status"}])
        provenance.append_writes([{"command": "prune-manifest", "tab": None}])
    lines = [json.loads(l) for l in
             state_files.PROVENANCE_LOG.read_text(encoding="utf-8").splitlines()]
    assert [(l["command"], l["tab"]) for l in lines] == [
        ("update-sheets", "general"), ("update-sheets", "Status"), ("prune-manifest", None)]


def test_append_writes_with_nothing_writes_nothing():
    from coding import drive_door, state_files
    with drive_door.running("update-sheets", may_write=True):
        provenance.append_writes([])
    assert not state_files.PROVENANCE_LOG.exists()
