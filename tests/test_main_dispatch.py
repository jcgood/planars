"""Tests for coding/__main__.py's dispatch chokepoint (Phase 5 units B/D,
issue #271): it parses once and calls preconditions.enforce(cmd, args)
before mod.main(args) -- not inside mod.main() itself. coding/preconditions.py
carries the actual precondition logic and is tested on its own in
tests/test_preconditions.py; these tests only check that the dispatch wires
the two together correctly, i.e. that a failed precondition check aborts
before the command's own main() ever runs.
"""
from __future__ import annotations

import sys

import pytest

from coding import __main__ as coding_main
from coding import preconditions, update_sheets


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
