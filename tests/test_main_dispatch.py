"""Tests for coding/__main__.py's dispatch chokepoint (issue #271): it parses
once, calls preconditions.enforce(cmd, args), and runs mod.main(args) inside
drive_door.running(cmd, args) -- not inside mod.main() itself.
coding/preconditions.py and coding/drive_door.py carry the actual logic and
are tested on their own (tests/test_preconditions.py, tests/test_drive_door.py,
where the door's per-write provenance log is tested); these tests only check
that the dispatch wires them together correctly.
"""
from __future__ import annotations

import sys

import pytest

from coding import __main__ as coding_main
from coding import drive_door, preconditions, provenance, update_sheets


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


def test_the_command_runs_with_the_door_told_which_command_it_is(monkeypatch):
    seen = []
    monkeypatch.setattr(update_sheets, "main",
                        lambda args: seen.append((drive_door._context.command,
                                                  drive_door._context.may_write)))
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: None)
    monkeypatch.setattr(sys, "argv", ["coding", "update-sheets", "--apply"])
    coding_main.main()
    assert seen == [("update-sheets", True)]
    assert drive_door._context is None


def test_a_run_that_writes_nothing_is_not_logged(monkeypatch):
    """The log records writes, not invocations: an --apply run that found
    nothing to do leaves no line."""
    monkeypatch.setattr(update_sheets, "main", lambda args: None)
    monkeypatch.setattr(preconditions, "_check_coded_data_clean", lambda **kw: None)
    monkeypatch.setattr(sys, "argv", ["coding", "update-sheets", "--apply"])
    coding_main.main()
    assert not provenance.LOG_PATH.exists()
