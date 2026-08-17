"""Tests for coding/__main__.py's dispatch chokepoint (Phase 5 units B/D/E,
issue #271): it parses once and calls preconditions.enforce(cmd, args) and
provenance.record(cmd, op_id, args) before mod.main(args) runs -- not inside
mod.main() itself. coding/preconditions.py and coding/provenance.py carry
the actual logic and are tested on their own in tests/test_preconditions.py
and tests/test_provenance.py; these tests only check that the dispatch
wires them together correctly.

Every test here redirects provenance.LOG_PATH to a tmp_path -- the real one
(at the repo root) must never be touched by a test run.
"""
from __future__ import annotations

import sys

import pytest

from coding import __main__ as coding_main
from coding import preconditions, provenance, update_sheets


@pytest.fixture(autouse=True)
def _redirect_provenance_log(monkeypatch, tmp_path):
    monkeypatch.setattr(provenance, "LOG_PATH", tmp_path / "provenance_log.jsonl")


def test_precondition_failure_aborts_before_the_command_runs(monkeypatch):
    calls = []
    monkeypatch.setattr(update_sheets, "main", lambda args: calls.append(args))

    def _boom(**kw):
        raise SystemExit("coded_data/ has uncommitted changes")

    monkeypatch.setattr(preconditions, "_check_coded_data_clean", _boom)
    monkeypatch.setattr(sys, "argv", ["coding", "update-sheets", "--apply"])

    with pytest.raises(SystemExit):
        coding_main.main()
    assert calls == []  # update_sheets.main() must never have been reached


def test_a_satisfied_precondition_lets_the_command_run(monkeypatch):
    calls = []
    monkeypatch.setattr(update_sheets, "main", lambda args: calls.append(args))
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: None)
    monkeypatch.setattr(sys, "argv", ["coding", "update-sheets", "--apply"])

    coding_main.main()
    assert len(calls) == 1
    assert calls[0].apply is True


def test_a_dry_run_needs_no_precondition_check_and_still_runs(monkeypatch):
    calls = []
    monkeypatch.setattr(update_sheets, "main", lambda args: calls.append(args))

    def _boom(**kw):
        raise AssertionError("dry run should never call _check_coded_data_clean")

    monkeypatch.setattr(preconditions, "_check_coded_data_clean", _boom)
    monkeypatch.setattr(sys, "argv", ["coding", "update-sheets"])

    coding_main.main()
    assert len(calls) == 1
    assert calls[0].apply is False


def test_an_apply_run_that_writes_to_drive_is_logged(monkeypatch):
    monkeypatch.setattr(update_sheets, "main", lambda args: None)
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: None)
    monkeypatch.setattr(sys, "argv", ["coding", "update-sheets", "--apply"])

    coding_main.main()

    assert provenance.LOG_PATH.exists()
    assert '"command": "update-sheets"' in provenance.LOG_PATH.read_text(encoding="utf-8")


def test_a_dry_run_is_not_logged(monkeypatch):
    monkeypatch.setattr(update_sheets, "main", lambda args: None)
    monkeypatch.setattr(sys, "argv", ["coding", "update-sheets"])

    coding_main.main()

    assert not provenance.LOG_PATH.exists()
