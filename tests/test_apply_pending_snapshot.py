"""Snapshot tests for `python -m coding apply-pending`, run against the fake.

File 4 of 17 migrated to the Drive doorway. The lowest-risk of the sixteen that
were left: the only thing it asks Drive for is the list of tab names in one
spreadsheet, and it never writes.

That makes it the first command whose *whole* job is a conversation with the
coordinator — everything it does is decided by what they type at a prompt — so
the snapshots here are transcripts of those conversations, and the assertions
are about what a given answer does to `pending_changes.json`.

Before migrating, the old code was driven from this same stand-in Drive through
a shim, across fourteen scenarios. Output and the recorded Drive changes came
back byte-identical afterwards.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_apply_pending_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List

import pytest

from coding import apply_pending, drive_doorway
from fake_drive import FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "apply_pending"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

# Two real spreadsheets from the recorded Drive. subspanrepetition has tabs
# 'auxiliary_construction', 'tso_clause_linkage' and 'Status'; ciscategorial has
# 'general' and 'Status', so it stands in for a sheet where the tab is absent.
SUBSPAN = "12negOahPnlSq02aET6kuU_NCkC5T2u8XeJaxg1nJQ70"
CIS = "1BTORcAYwVZGEf_rftRxXAsC4wMeVunozbhoiu_3Pnxc"


def planar_entry() -> Dict:
    """A change that apply-pending can resolve by running one command."""
    return {
        "lang_id": "arao1248",
        "change_type": "planar_deletion_or_reorder",
        "description": "Planar structure has deleted or reordered positions",
        "diff_summary": "Removed positions: ['v:oldslot']\nOld order: a | b\nNew order: b",
        "command": "python -m coding restructure-sheets --apply",
    }


def construction_entry(shown: bool, spreadsheet_id: str,
                       constructions: List[str]) -> Dict:
    """A change that only a person adding a tab in the Sheet can resolve."""
    return {
        "lang_id": "arao1248",
        "change_type": "diagnostics_new_construction",
        "class_name": "subspanrepetition",
        "new_constructions": constructions,
        "spreadsheet_id": spreadsheet_id,
        "instructions_shown": shown,
        "description": f"New construction(s) in class 'subspanrepetition': {constructions}",
        "diff_summary": "Class 'subspanrepetition': new construction(s)",
        "command": "",
    }


class Session:
    """One apply-pending run: what it printed, what it ran, what it left behind."""

    def __init__(self, output: str, commands: List[str], remaining: List[Dict],
                 issue_closed: bool) -> None:
        self.output = output
        self.commands = commands
        self.remaining = remaining
        self.issue_closed = issue_closed


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """A stand-in Drive, a scratch pending_changes.json, and scripted answers.

    Yields a `run(entries, answers, all_flag)` that plays one session. The
    GitHub call and the subprocess are stubbed: this command's own behaviour is
    which of them it reaches for, not what they then do.
    """
    doorway = FakeDriveDoorway.from_fixtures()
    drive_doorway.set_doorway(doorway)
    pending_path = tmp_path / "pending_changes.json"
    monkeypatch.setattr(apply_pending, "PENDING_PATH", pending_path)

    def run(entries: List[Dict], answers: List[str] = (),
            all_flag: bool = False, command_exit_code: int = 0) -> Session:
        pending_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        replies = iter(answers)
        commands: List[str] = []
        closed: List[bool] = []

        def scripted_input(prompt: str = "") -> str:
            try:
                answer = next(replies)
            except StopIteration:  # ran out of answers — same as Ctrl-D
                raise EOFError
            print(f"{prompt}{answer}")
            return answer

        monkeypatch.setattr("builtins.input", scripted_input)
        monkeypatch.setattr(
            apply_pending, "_run_command",
            lambda cmd: (commands.append(cmd), command_exit_code)[1])
        monkeypatch.setattr(apply_pending, "_close_pending_issue",
                            lambda: closed.append(True))
        monkeypatch.setattr(
            sys, "argv", ["apply-pending"] + (["--all"] if all_flag else []))

        buf = io.StringIO()
        with redirect_stdout(buf):
            apply_pending.main()

        left = json.loads(pending_path.read_text(encoding="utf-8"))
        return Session(buf.getvalue(), commands, left, bool(closed))

    try:
        yield doorway, run
    finally:
        drive_doorway.reset_doorway()


def check_snapshot(name: str, actual: str) -> None:
    path = SNAPSHOT_DIR / name
    if UPDATING:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"updated snapshot {path.relative_to(ROOT)}")
    assert path.exists(), (
        f"Snapshot missing: {path.relative_to(ROOT)}\n"
        f"Run: PLANARS_UPDATE_SNAPSHOTS=1 pytest {Path(__file__).relative_to(ROOT)}")
    assert actual == path.read_text(encoding="utf-8"), (
        f"Output differs from {path.name}. If intended, regenerate with "
        f"PLANARS_UPDATE_SNAPSHOTS=1 and review the diff.")


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_transcript_of_a_change_applied_and_one_skipped(env):
    _, run = env
    parts = [
        run([], []).output,
        run([planar_entry()], ["y"]).output,
        run([planar_entry()], ["n"]).output,
        run([planar_entry()], all_flag=True).output,
    ]
    check_snapshot("commands.txt", "\n".join(parts))


def test_transcript_of_the_new_construction_conversation(env):
    """Two visits: the first prints instructions, the second checks the Sheet."""
    _, run = env
    parts = [
        run([construction_entry(False, SUBSPAN, ["auxiliary_construction"])],
            ["y"]).output,
        run([construction_entry(True, SUBSPAN,
                                ["auxiliary_construction", "tso_clause_linkage"])],
            ["y"]).output,
        run([construction_entry(True, SUBSPAN,
                                ["auxiliary_construction", "not_yet_added"])],
            ["y"]).output,
        run([construction_entry(True, "no_such_sheet", ["auxiliary_construction"])],
            ["y"]).output,
    ]
    check_snapshot("new_construction.txt", "\n".join(parts))


# ---------------------------------------------------------------------------
# What it promises: nothing it does here changes anything in Drive
# ---------------------------------------------------------------------------

def test_it_never_changes_anything_in_drive(env):
    """Every path through the command, and not one Drive change between them."""
    doorway, run = env
    run([planar_entry()], ["y"])
    run([construction_entry(False, SUBSPAN, ["auxiliary_construction"])], ["y"])
    run([construction_entry(True, SUBSPAN, ["auxiliary_construction"])], ["y"])
    run([construction_entry(True, SUBSPAN, ["not_yet_added"])], ["y"])
    run([construction_entry(True, "no_such_sheet", ["auxiliary_construction"])], ["y"])
    assert doorway.mutations == []


def test_a_run_with_nothing_to_verify_never_opens_a_spreadsheet(env, monkeypatch):
    """The Drive import is inside the check, so signing in is not the price of asking."""
    doorway, run = env

    def refuse(*args, **kwargs):
        raise AssertionError("opened a spreadsheet with nothing to verify")

    monkeypatch.setattr(doorway, "open_spreadsheet", refuse)
    session = run([planar_entry()], ["y"])
    assert session.commands == ["python -m coding restructure-sheets --apply"]


# ---------------------------------------------------------------------------
# What an answer does to the file
# ---------------------------------------------------------------------------

def test_a_skipped_entry_is_left_exactly_as_it_was(env):
    _, run = env
    entry = planar_entry()
    session = run([entry], ["n"])
    assert session.remaining == [entry]
    assert session.commands == []
    assert not session.issue_closed


def test_clearing_the_last_entry_closes_the_github_issue(env):
    _, run = env
    assert run([planar_entry()], ["y"]).issue_closed
    assert not run([planar_entry(), planar_entry()], ["y", "n"]).issue_closed


def test_a_command_that_fails_leaves_its_entry_pending(env):
    _, run = env
    session = run([planar_entry()], ["y"], command_exit_code=1)
    assert session.remaining == [planar_entry()]
    assert "exited with code 1" in session.output
    assert not session.issue_closed


def test_showing_the_instructions_records_that_they_were_shown(env):
    """So the next run checks the Sheet instead of printing the same page again."""
    _, run = env
    session = run([construction_entry(False, SUBSPAN, ["auxiliary_construction"])],
                  ["y"])
    assert session.remaining[0]["instructions_shown"] is True
    assert session.commands == []
    assert "generate-sheets --force --apply" in session.output


def test_declining_the_instructions_leaves_them_unshown(env):
    _, run = env
    session = run([construction_entry(False, SUBSPAN, ["auxiliary_construction"])],
                  ["n"])
    assert session.remaining[0]["instructions_shown"] is False


def test_a_missing_tab_is_not_resolvable_and_is_not_even_asked_about(env):
    """No prompt at all — there is nothing the coordinator could truthfully answer."""
    _, run = env
    session = run(
        [construction_entry(True, SUBSPAN, ["auxiliary_construction", "not_yet_added"])],
        answers=[])          # any prompt would raise EOFError
    assert len(session.remaining) == 1
    assert "Not found in Sheet: ['not_yet_added']" in session.output


def test_every_tab_present_lets_the_entry_be_closed(env):
    _, run = env
    session = run(
        [construction_entry(True, SUBSPAN,
                            ["auxiliary_construction", "tso_clause_linkage"])],
        ["y"])
    assert session.remaining == []
    assert "All tab(s) found in Sheet." in session.output


def test_a_tab_absent_from_a_different_sheet_reads_as_absent(env):
    """The tab exists elsewhere in Drive; what matters is this class's own sheet."""
    _, run = env
    session = run([construction_entry(True, CIS, ["auxiliary_construction"])],
                  answers=[])
    assert len(session.remaining) == 1
    assert "Not found in Sheet: ['auxiliary_construction']" in session.output


# ---------------------------------------------------------------------------
# When Drive cannot answer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spreadsheet_id", ["no_such_sheet", ""])
def test_an_unanswerable_check_asks_instead_of_deciding(env, spreadsheet_id):
    """A sheet that cannot be reached, and an entry that never recorded an ID.

    Both hand the question back rather than guessing — and both let the
    coordinator close the entry on their own word, which is the only way a
    lost spreadsheet ID can ever be cleared.
    """
    _, run = env
    entry = construction_entry(True, spreadsheet_id, ["auxiliary_construction"])
    assert run([entry], ["y"]).remaining == []
    assert run([entry], ["n"]).remaining == [entry]
    assert "Could not verify" in run([entry], ["n"]).output


# ---------------------------------------------------------------------------
# --all
# ---------------------------------------------------------------------------

def test_all_applies_command_entries_without_asking(env):
    _, run = env
    session = run([planar_entry()], answers=[], all_flag=True)
    assert session.commands == ["python -m coding restructure-sheets --apply"]
    assert session.remaining == []


def test_all_refuses_new_construction_entries(env):
    """They need a person in the Sheet, so 'apply everything' cannot mean them."""
    _, run = env
    entry = construction_entry(True, SUBSPAN, ["auxiliary_construction"])
    session = run([entry], answers=[], all_flag=True)
    assert session.remaining == [entry]
    assert "cannot be applied automatically" in session.output
