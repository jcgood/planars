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
    ]
    check_snapshot("new_construction.txt", "\n".join(parts))


def test_transcript_of_the_four_ways_a_check_can_fail(env, monkeypatch):
    """All four on one page, which is where they have to look different.

    Before this, every one of them printed the same sentence and asked the same
    question, so the page could not tell the coordinator whether the entry was
    wrong, their access was wrong, or the wifi was.
    """
    doorway, run = env
    entry = construction_entry(True, SUBSPAN, ["auxiliary_construction"])
    parts = [run([construction_entry(True, "", ["auxiliary_construction"])], ["n"]).output,
             run([construction_entry(True, "no_such_sheet", ["auxiliary_construction"])],
                 ["n"]).output]

    monkeypatch.setattr(doorway, "open_spreadsheet", unreachable(PermissionError()))
    parts.append(run([entry], ["n"]).output)

    monkeypatch.setattr(doorway, "open_spreadsheet",
                        unreachable(ConnectionError("network is down")))
    parts.append(run([entry], ["n"]).output)

    check_snapshot("cannot_check.txt", "\n".join(parts))


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
#
# Four different reasons, and they used to print one sentence between them. A
# stale spreadsheet ID read exactly like a dropped connection, and either way
# the coordinator was asked to confirm from memory.
# ---------------------------------------------------------------------------

def unreachable(exc: Exception):
    """Make the doorway fail the way Drive would."""
    def refuse(*args, **kwargs):
        raise exc
    return refuse


def test_a_spreadsheet_id_pointing_nowhere_says_so(env):
    _, run = env
    entry = construction_entry(True, "no_such_sheet", ["auxiliary_construction"])
    out = run([entry], ["n"]).output
    assert "Drive has no spreadsheet with the ID recorded on this entry" in out
    assert "no_such_sheet" in out
    assert "python -m coding integrity-check --sheets" in out
    # Not the same question as "have the tabs been added" — they cannot have been.
    assert "Close this entry anyway?" in out


def test_an_entry_with_no_spreadsheet_id_names_the_sheet_to_look_in(env):
    """Nothing to check against, so the coordinator is told where to look."""
    _, run = env
    entry = construction_entry(True, "", ["auxiliary_construction"])
    out = run([entry], ["n"]).output
    assert "never recorded which spreadsheet to look in" in out
    assert "'subspanrepetition_arao1248'" in out       # the Sheet's real name
    assert "'arao1248' folder on Drive" in out
    assert "Mark as resolved?" in out


def test_a_sheet_not_shared_with_this_account_says_what_to_ask_for(env, monkeypatch):
    doorway, run = env
    monkeypatch.setattr(doorway, "open_spreadsheet", unreachable(PermissionError()))
    entry = construction_entry(True, SUBSPAN, ["auxiliary_construction"])
    out = run([entry], ["n"]).output
    assert "Drive refused access" in out
    assert "Ask whoever owns it to share" in out


def test_a_dropped_connection_says_the_entry_is_fine(env, monkeypatch):
    """The one case where nothing is wrong and trying again later is the fix."""
    doorway, run = env
    monkeypatch.setattr(doorway, "open_spreadsheet",
                        unreachable(ConnectionError("network is down")))
    entry = construction_entry(True, SUBSPAN, ["auxiliary_construction"])
    out = run([entry], ["n"]).output
    assert "Could not reach Drive to check" in out
    assert "Nothing is wrong with the entry itself" in out
    # The question admits what it is asking for.
    assert "Mark as resolved without checking?" in out


def fail_reading_tab_names(doorway, monkeypatch, exc: Exception):
    """Let the spreadsheet open, then fail on the call that lists its tabs."""
    real_open = doorway.open_spreadsheet

    def open_then_fail(spreadsheet_id):
        ss = real_open(spreadsheet_id)
        monkeypatch.setattr(ss, "worksheets", unreachable(exc))
        return ss

    monkeypatch.setattr(doorway, "open_spreadsheet", open_then_fail)


@pytest.mark.parametrize("code,expected", [
    (404, "Drive has no spreadsheet with the ID recorded on this entry"),
    (403, "Drive refused access"),
    (400, "Could not reach Drive to check"),
])
def test_a_failure_while_reading_tab_names_is_told_apart_by_its_status(
        env, monkeypatch, code, expected):
    """The second call reports a vanished sheet as a status code, not a type.

    Opening the spreadsheet and listing its tabs are two calls, and only the
    first turns 404 and 403 into exceptions of their own. Without the status
    check, a sheet deleted between the two would read as a network problem.
    """
    from fake_drive import api_error

    doorway, run = env
    fail_reading_tab_names(doorway, monkeypatch, api_error(code, "boom"))
    entry = construction_entry(True, SUBSPAN, ["auxiliary_construction"])
    assert expected in run([entry], ["n"]).output


def test_a_busy_drive_is_retried_first_and_only_then_reported(env, monkeypatch):
    """429 and friends are Drive asking to wait, not an answer about the entry."""
    import coding.drive as drive_module
    from fake_drive import api_error

    doorway, run = env
    waits: List[int] = []
    monkeypatch.setattr(drive_module.time, "sleep", waits.append)
    fail_reading_tab_names(doorway, monkeypatch, api_error(429, "rate limited"))

    entry = construction_entry(True, SUBSPAN, ["auxiliary_construction"])
    out = run([entry], ["n"]).output
    assert len(waits) == 4                       # five attempts, four waits
    assert "Could not reach Drive to check" in out


@pytest.mark.parametrize("spreadsheet_id", ["no_such_sheet", ""])
def test_an_unanswerable_check_still_asks_rather_than_deciding(env, spreadsheet_id):
    """However it failed, the coordinator can always clear the entry themselves.

    That matters: an entry naming a spreadsheet nobody can reach would
    otherwise be stuck open forever.
    """
    _, run = env
    entry = construction_entry(True, spreadsheet_id, ["auxiliary_construction"])
    assert run([entry], ["y"]).remaining == []
    assert run([entry], ["n"]).remaining == [entry]


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


# ---------------------------------------------------------------------------
# Idempotency (Phase 8 of the data layer redesign, issue #271) -- proving
# the #280 fix's own claim for real: pending_changes.json is rewritten after
# every entry's decision, not once at the end of the loop, so a crash right
# after one entry's command has already run for real doesn't leave that
# entry still listed (which would make a retry run it a second time). The
# fixture's own `run()` stubs _run_command to always succeed, so this test
# builds its own scripted version that succeeds once, then raises -- a real
# crash mid-loop, not a hand-set file.
# ---------------------------------------------------------------------------

def test_a_crash_after_one_entry_succeeds_does_not_leave_it_listed(monkeypatch, tmp_path):
    pending_path = tmp_path / "pending_changes.json"
    entry_a = dict(planar_entry(), description="first change")
    entry_b = dict(planar_entry(), description="second change")
    pending_path.write_text(json.dumps([entry_a, entry_b], indent=2), encoding="utf-8")
    monkeypatch.setattr(apply_pending, "PENDING_PATH", pending_path)

    calls = {"n": 0}

    def flaky_run_command(cmd):
        calls["n"] += 1
        if calls["n"] == 1:
            return 0  # entry_a's command genuinely succeeds
        raise RuntimeError("simulated crash while running entry_b's command")

    monkeypatch.setattr(apply_pending, "_run_command", flaky_run_command)
    monkeypatch.setattr(apply_pending, "_close_pending_issue", lambda: None)
    replies = iter(["y", "y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(replies))
    monkeypatch.setattr(sys, "argv", ["apply-pending"])

    with pytest.raises(RuntimeError, match="simulated crash"):
        apply_pending.main()

    left = json.loads(pending_path.read_text(encoding="utf-8"))
    # entry_a's success was saved immediately -- not still listed, so a
    # retry won't run its command a second time. entry_b never got a save
    # for its own decision (the crash landed before that line), so it's
    # still exactly where it was -- correctly re-attempted next time, since
    # its command never actually completed.
    assert left == [entry_b]
