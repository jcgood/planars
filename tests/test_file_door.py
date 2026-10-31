"""Tests for coding/file_door.py, the local-file door (Phase 10 unit 6a).

Each rule in the module docstring, the archive and change log it keeps,
what the log says about overwrites, and the commit when a command ends. The
files are a private copy of the frozen data (fake_drive.use_frozen_coded_data),
so the spec checks run against real diagnostics files.
"""
from __future__ import annotations

import contextlib
import csv
import io
import subprocess
from pathlib import Path

import pytest

from coding import drive_door, file_door
from coding.file_door import DoorViolation
from coding.registry import _load_operations
from fake_drive import use_frozen_coded_data

LANG, CLASS, CON = "synth0001", "ciscategorial", "general"


@pytest.fixture()
def coded(monkeypatch, tmp_path) -> Path:
    """A private copy of the frozen data, with empty change logs, so each
    test reads only the lines its own writes added. Every language's, not
    only LANG's: refresh_writes and overwrites read them all."""
    coded = use_frozen_coded_data(monkeypatch, tmp_path)
    for log in coded.glob("*/changes.tsv"):
        log.unlink()
    return coded


def _rows(text: str):
    return list(csv.reader(io.StringIO(text, newline=""), delimiter="\t"))


def _text(rows) -> str:
    buf = io.StringIO()
    csv.writer(buf, delimiter="\t", lineterminator="\r\n").writerows(rows)
    return buf.getvalue()


def _target():
    return file_door.annotation(LANG, CLASS, CON)


def _answered(coded: Path) -> str:
    """The frozen TSV with an answer in its first row, written as the old
    version (outside the door: it stands for what is already on disk)."""
    rows = _rows(file_door.read(_target()))
    rows[1][3] = "y"
    text = _text(rows)
    _target().path.write_bytes(text.encode("utf-8"))
    return text


def _log(coded: Path):
    return list(csv.DictReader(open(coded / LANG / "changes.tsv", encoding="utf-8"),
                               delimiter="\t"))


def _archives(coded: Path, folder: str = CLASS):
    d = coded / LANG / "archive" / folder
    return set(d.glob("*")) if d.exists() else set()


# ---------------------------------------------------------------------------
# Naming files by what they are
# ---------------------------------------------------------------------------

def test_each_kind_builds_its_own_path(coded):
    assert file_door.annotation(LANG, CLASS, CON).path == coded / LANG / CLASS / "general.tsv"
    assert file_door.planar(LANG).path == coded / LANG / "lang_setup" / f"planar_{LANG}.tsv"
    assert file_door.diagnostics_yaml(LANG).relpath == f"lang_setup/diagnostics_{LANG}.yaml"
    assert file_door.proposal_base(LANG).name == f"proposal_base_{LANG}.json"
    assert file_door.tab_status(LANG).relpath == "records/tab_status.tsv"
    assert file_door.proposal_sheet_copy(LANG).relpath == "records/proposal_sheet.json"


def test_a_status_change_is_described_tab_by_tab():
    header = ["Class", "Construction", "Status", "Marked by"]
    old = [header, ["metrical", "stress_domain", "in-progress", ""],
           ["metrical", "old_tab", "in-progress", ""]]
    new = [header, ["metrical", "stress_domain", "ready-for-review", "annotator, 2026-10-29"],
           ["metrical", "new_tab", "in-progress", ""]]
    assert file_door._describe_statuses(old, new) == (
        "metrical/stress_domain: in-progress → ready-for-review (annotator, 2026-10-29); "
        "metrical/new_tab: in-progress; metrical/old_tab: no longer listed")


def test_an_unknown_kind_or_missing_part_cannot_be_named():
    with pytest.raises(ValueError, match="unknown kind"):
        file_door.LocalFile("notes", LANG)
    with pytest.raises(ValueError, match="needs class_name"):
        file_door.LocalFile(file_door.ANNOTATION, LANG, construction=CON)
    with pytest.raises(ValueError, match="has no class_name"):
        file_door.LocalFile(file_door.PLANAR, LANG, class_name=CLASS)


def test_every_record_names_only_real_sources():
    for op_id, record in _load_operations().items():
        for part in [record, *record.get("modes", [])]:
            assert set(part.get("edits_sources", [])) <= file_door.SOURCES, op_id


def test_every_part_that_writes_locally_needs_a_git_identity():
    """The door commits what it wrote, so a writing part of a record declares
    preconditions.yaml's coded_data_git_identity_configured."""
    for op_id, record in _load_operations().items():
        for part in [record, *record.get("modes", [])]:
            if part["writes_locally"]:
                assert "coded_data_git_identity_configured" in part["preconditions"], op_id


def test_a_record_naming_an_unknown_source_stops_the_command(monkeypatch):
    ops = _load_operations()
    ops["accept_proposal"] = dict(ops["accept_proposal"], edits_sources=["planr"])
    monkeypatch.setattr("coding.registry._load_operations", lambda: ops)
    with pytest.raises(ValueError, match="not sources"):
        file_door.begin("accept-proposal")


# ---------------------------------------------------------------------------
# Rule 1: a command is running, and may write
# ---------------------------------------------------------------------------

def test_no_command_running_is_refused(coded):
    with pytest.raises(DoorViolation, match="no command is running"):
        file_door.write(_target(), "x\n", why="test")


def test_a_dry_run_writes_nothing(coded):
    import argparse
    before = file_door.read(_target())
    with drive_door.running("import-sheets", argparse.Namespace(apply=False)):
        with pytest.raises(DoorViolation, match="dry run"):
            file_door.write(_target(), before.replace("also", "ALSO"), why="test")
    assert file_door.read(_target()) == before


def test_write_needs_a_reason(coded):
    with drive_door.running("t", may_write=True):
        with pytest.raises(ValueError, match="reason"):
            file_door.write(_target(), "x", why=" ")


# ---------------------------------------------------------------------------
# Rule 2: sources
# ---------------------------------------------------------------------------

def test_a_source_is_written_only_by_a_command_that_says_it_edits_it(coded):
    import argparse
    target = file_door.diagnostics_yaml(LANG)
    text = file_door.read(target) + "# a comment\n"
    with drive_door.running("restructure-sheets", argparse.Namespace(apply=True)):
        with pytest.raises(DoorViolation, match="edits_sources"):
            file_door.write(target, text, why="test")
    with drive_door.running("sync-params", argparse.Namespace(apply=True)):
        assert file_door.write(target, text, why="test")


def test_a_migration_may_write_a_source(coded):
    """Code with no operations.yaml record says it may write (a migration)."""
    target = file_door.planar(LANG)
    with drive_door.running("migration", may_write=True):
        assert file_door.write(target, file_door.read(target) + "\n", why="test")


# ---------------------------------------------------------------------------
# What every write does: only if different, archive, change log
# ---------------------------------------------------------------------------

def test_identical_content_is_not_written_archived_or_logged(coded):
    with drive_door.running("t", may_write=True):
        assert file_door.write(_target(), file_door.read(_target()), why="test") is False
    assert not (coded / LANG / "changes.tsv").exists()


def test_a_new_file_is_logged_with_no_previous_version(coded):
    target = file_door.annotation(LANG, CLASS, "brand_new")
    text = file_door.read(_target())
    with drive_door.running("t", may_write=True):
        assert file_door.write(target, text, why="made for the test")
    assert file_door.read(target) == text
    [line] = _log(coded)
    assert line["file"] == f"{CLASS}/brand_new.tsv"
    assert line["what changed"].startswith("created (")
    assert line["by"] == "t" and line["why"] == "made for the test"
    assert line["previous version"] == ""


def test_an_overwrite_archives_the_old_text_and_logs_what_changed(coded):
    old = file_door.read(_target())
    before = _archives(coded)
    rows = _rows(old)
    rows[1][3] = "y"
    with drive_door.running("t", may_write=True):
        assert file_door.write(_target(), _text(rows), why="answered")
    [archived] = _archives(coded) - before
    assert archived.read_text(encoding="utf-8", newline="") == old
    [line] = _log(coded)
    assert line["what changed"] == "1 cell(s) changed"
    assert line["previous version"] == str(archived.relative_to(coded / LANG))


def test_the_door_keeps_the_bytes_it_is_given(coded):
    """CRLF line ends (as some annotation TSVs still have) survive the write."""
    text = _text(_rows(file_door.read(_target())))
    _target().path.write_bytes(text.encode("utf-8"))   # the file on disk, CRLF
    assert "\r\n" in file_door.read(_target())
    rows = _rows(text)
    rows[2][3] = "n"
    with drive_door.running("t", may_write=True):
        file_door.write(_target(), _text(rows), why="test")
    assert _target().path.read_bytes() == _text(rows).encode("utf-8")


def test_an_archive_copy_is_never_overwritten(coded, monkeypatch):
    monkeypatch.setattr(file_door, "stamp", lambda: "20260101_000000")
    rows = _rows(file_door.read(_target()))
    before = _archives(coded)
    with drive_door.running("t", may_write=True):
        for value in ("y", "n"):
            rows[1][3] = value
            file_door.write(_target(), _text(rows), why="test")
    added = sorted(p.name for p in _archives(coded) - before)
    assert added == ["general_20260101_000000.tsv", "general_20260101_000000_2.tsv"]


# ---------------------------------------------------------------------------
# Rule 3: an annotation TSV has its tab's columns
# ---------------------------------------------------------------------------

def test_a_column_the_tab_should_not_have_is_refused(coded):
    rows = _rows(file_door.read(_target()))
    rows = [r[:6] + ["stray"] + r[6:] for r in rows]
    with drive_door.running("t", may_write=True):
        with pytest.raises(DoorViolation, match="column the spec does not have"):
            file_door.write(_target(), _text(rows), why="test")


def test_a_mismatch_the_old_version_already_had_is_not_blamed_on_this_write(coded):
    rows = _rows(file_door.read(_target()))
    rows = [r[:6] + ["stray"] + r[6:] for r in rows]
    _target().path.write_bytes(_text(rows).encode("utf-8"))
    rows[1][3] = "y"
    with drive_door.running("t", may_write=True):
        assert file_door.write(_target(), _text(rows), why="test")


def test_a_parked_split_column_is_allowed(coded):
    rows = _rows(file_door.read(_target()))
    rows = [r[:6] + (["_split_old"] if i == 0 else [""]) + r[6:] for i, r in enumerate(rows)]
    with drive_door.running("t", may_write=True):
        assert file_door.write(_target(), _text(rows), why="test")


# ---------------------------------------------------------------------------
# Rule 4: no answered row is lost without a reason
# ---------------------------------------------------------------------------

def test_dropping_an_answered_row_is_refused(coded):
    old = _answered(coded)
    rows = _rows(old)
    del rows[1]
    with drive_door.running("t", may_write=True):
        with pytest.raises(DoorViolation, match="1 answered row"):
            file_door.write(_target(), _text(rows), why="test")
    assert file_door.read(_target()) == old


def test_dropping_an_unanswered_row_is_fine(coded):
    _answered(coded)
    rows = _rows(file_door.read(_target()))
    del rows[2]
    with drive_door.running("t", may_write=True):
        assert file_door.write(_target(), _text(rows), why="test")
    assert "1 row(s) removed" in _log(coded)[0]["what changed"]


def test_a_drop_with_a_reason_goes_ahead_and_is_logged(coded):
    rows = _rows(_answered(coded))
    del rows[1]
    with drive_door.running("t", may_write=True):
        assert file_door.write(_target(), _text(rows), why="test", drops="position removed")
    assert "answered rows not matched in the new version (position removed)" in \
        _log(coded)[0]["what changed"]


# ---------------------------------------------------------------------------
# Removing and moving
# ---------------------------------------------------------------------------

def test_remove_archives_logs_and_removes_the_emptied_folder(coded):
    text = file_door.read(_target())
    before = _archives(coded)
    with drive_door.running("t", may_write=True):
        assert file_door.remove(_target(), why="class retired")
        assert file_door.remove(_target(), why="again") is False
    assert not (coded / LANG / CLASS).exists()
    [archived] = _archives(coded) - before
    assert archived.read_text(encoding="utf-8", newline="") == text
    [line] = _log(coded)
    assert line["what changed"].startswith("removed (") and line["why"] == "class retired"


def test_move_class_writes_under_the_new_name_and_removes_the_old(coded, monkeypatch):
    # The new class must be one the diagnostics file lists, or its columns
    # can't be checked: borrow the spec of the class being moved.
    real = file_door._tab_spec
    monkeypatch.setattr(file_door, "_tab_spec", lambda run, t: real(
        run, file_door.annotation(t.lang_id, CLASS, t.construction)))
    text = file_door.read(_target())
    with drive_door.running("t", may_write=True):
        assert file_door.move_class(LANG, CLASS, "ciscategorial_new", why="renamed") == 1
    assert file_door.read(file_door.annotation(LANG, "ciscategorial_new", CON)) == text
    assert not (coded / LANG / CLASS).exists()
    whats = [l["what changed"] for l in _log(coded)]
    assert whats[0] == f"moved from {CLASS}/general.tsv" and whats[1].startswith("removed")


# ---------------------------------------------------------------------------
# The daily refresh in the log, and overwrites
# ---------------------------------------------------------------------------

def _change(value: str, *commands: str) -> None:
    """Answer the first row with ``value`` inside the nested runs named."""
    rows = _rows(file_door.read(_target()))
    rows[1][3] = value
    with contextlib.ExitStack() as stack:
        for command in commands:
            stack.enter_context(drive_door.running(command, may_write=True))
        file_door.write(_target(), _text(rows), why="test")


def test_a_write_inside_the_daily_refresh_says_so_in_the_log(coded):
    _change("y", "daily-refresh", "import-sheets")
    _change("n", "import-sheets")
    assert [l["by"] for l in _log(coded)] == ["import-sheets (daily refresh)", "import-sheets"]


def test_the_refresh_replacing_another_commands_change_is_an_overwrite(coded):
    _change("y", "a-migration")
    _change("n", "daily-refresh", "import-sheets")
    [o] = file_door.overwrites("2000-01-01T00:00:00Z")
    assert (o.lang_id, o.file, o.replaced_by) == (LANG, f"{CLASS}/general.tsv", "a-migration")
    assert o.replaced_version == _log(coded)[1]["previous version"]


def _revision(when: str, email: str):
    return {"id": when, "modifiedTime": when,
            "lastModifyingUser": {"displayName": "x", "emailAddress": email, "me": False}}


def _answer_read_from_drive(value: str, revisions, *commands: str) -> None:
    rows = _rows(file_door.read(_target()))
    rows[1][3] = value
    with contextlib.ExitStack() as stack:
        for command in commands:
            stack.enter_context(drive_door.running(command, may_write=True))
        file_door.write(_target(), _text(rows), why="test", revisions=lambda: revisions)


def test_the_log_names_who_edited_the_sheet_since_the_files_last_line(coded):
    """Unit 16c: edited by is everyone with a revision after the file's
    previous change-log line, by people.yaml name; a write given no
    revisions leaves it empty."""
    _change("y", "a-migration")
    revisions = [_revision("2000-01-01T00:00:00Z", "visitor@example.org"),
                 _revision("2999-01-01T00:00:00Z", "annotator@example.org")]
    _answer_read_from_drive("n", revisions, "import-sheets")
    lines = _log(coded)
    assert [l["edited by"] for l in lines] == ["", "Adam Tallman"]
    assert list(lines[0]) == list(file_door.CHANGE_LOG_COLUMNS)


def test_with_no_earlier_line_every_revision_counts(coded):
    revisions = [_revision("2000-01-01T00:00:00Z", "visitor@example.org"),
                 _revision("2001-01-01T00:00:00Z", "annotator@example.org")]
    _answer_read_from_drive("y", revisions, "import-sheets")
    assert _log(coded)[0]["edited by"] == "someone not in people.yaml; Adam Tallman"


def test_revisions_are_not_read_when_nothing_changes(coded):
    def never():
        raise AssertionError("read revisions for an unchanged file")
    with drive_door.running("import-sheets", may_write=True):
        assert not file_door.write(_target(), file_door.read(_target()), why="test",
                                   revisions=never)


def test_a_log_with_another_header_is_refused(coded):
    (coded / LANG / "changes.tsv").write_text("when (UTC)\tfile\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="add_edited_by_to_change_logs"):
        _change("y", "import-sheets")


def test_an_overwrite_names_who_edited_the_sheet(coded):
    _change("y", "a-migration")
    _answer_read_from_drive("n", [_revision("2999-01-01T00:00:00Z", "annotator@example.org")],
                            "daily-refresh", "import-sheets")
    [o] = file_door.overwrites("2000-01-01T00:00:00Z")
    assert o.edited_by == "Adam Tallman"


def test_a_file_edited_by_someone_unlisted_is_found(coded):
    _answer_read_from_drive("y", [_revision("2999-01-01T00:00:00Z", "annotator@example.org")],
                            "daily-refresh", "import-sheets")
    assert file_door.unlisted_edits("2000-01-01T00:00:00Z") == []
    _answer_read_from_drive("n", [_revision("2999-01-01T00:00:00Z", "visitor@example.org")],
                            "daily-refresh", "import-sheets")
    assert file_door.unlisted_edits("2000-01-01T00:00:00Z") == [(LANG, f"{CLASS}/general.tsv")]
    assert file_door.unlisted_edits("2999-12-31T00:00:00Z") == []


def test_the_same_command_or_an_earlier_refresh_is_not_an_overwrite(coded):
    _change("y", "import-sheets")
    _change("n", "daily-refresh", "import-sheets")
    _change("y", "daily-refresh", "import-sheets")
    assert file_door.overwrites("2000-01-01T00:00:00Z") == []


def test_rebuilding_a_file_built_from_another_is_not_an_overwrite(coded):
    target = file_door.proposal_base(LANG)
    with drive_door.running("accept-proposal", may_write=True):
        file_door.write(target, '{"a": 1}\n', why="test")
    with drive_door.running("daily-refresh", may_write=True):
        with drive_door.running("proposal-sheets", may_write=True):
            file_door.write(target, '{"a": 2}\n', why="test")
    assert file_door.overwrites("2000-01-01T00:00:00Z") == []


def test_only_writes_since_the_given_time_count(coded):
    _change("y", "a-migration")
    _change("n", "daily-refresh", "import-sheets")
    assert file_door.overwrites("2999-01-01T00:00:00Z") == []


def test_refresh_writes_counts_only_the_refreshs_own_lines_since_then(coded):
    _change("y", "a-migration")
    _change("n", "daily-refresh", "import-sheets")
    _change("y", "daily-refresh", "import-sheets")
    assert file_door.refresh_writes("2000-01-01T00:00:00Z") == 2
    assert file_door.refresh_writes("2999-01-01T00:00:00Z") == 0


# ---------------------------------------------------------------------------
# Committing when the command ends
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _make_repo(coded: Path) -> None:
    _git(coded, "init")
    _git(coded, "config", "user.email", "test@example.com")
    _git(coded, "config", "user.name", "Test")
    _git(coded, "add", "-A")
    _git(coded, "commit", "-m", "init")


def test_the_files_written_are_committed_and_nothing_else(coded):
    _make_repo(coded)
    stray = coded / "stray.txt"
    stray.write_text("not the door's\n", encoding="utf-8")
    rows = _rows(file_door.read(_target()))
    rows[1][3] = "y"
    with drive_door.running("t", may_write=True):
        file_door.write(_target(), _text(rows), why="answered")
    message = _git(coded, "log", "-1", "--format=%B")
    assert message.startswith("data: t changed 1 file(s)")
    assert f"{LANG}/{CLASS}/general.tsv: 1 cell(s) changed (answered)" in message
    assert _git(coded, "status", "--porcelain") == "?? stray.txt\n"


def test_a_failed_commit_raises_and_leaves_the_files_written(coded):
    _make_repo(coded)
    hook = coded / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    rows = _rows(file_door.read(_target()))
    rows[1][3] = "y"
    with pytest.raises(RuntimeError, match="not committed"):
        with drive_door.running("t", may_write=True):
            file_door.write(_target(), _text(rows), why="answered")
    assert _git(coded, "status", "--porcelain") != ""


def test_a_failed_push_does_not_raise(coded):
    """No remote: the commit is made, the push fails, the command succeeds."""
    _make_repo(coded)
    rows = _rows(file_door.read(_target()))
    rows[1][3] = "y"
    with drive_door.running("t", may_write=True):
        file_door.write(_target(), _text(rows), why="answered")
    assert _git(coded, "status", "--porcelain") == ""


def test_a_nested_command_commits_its_own_files(coded):
    """daily-refresh runs each command inside its own run."""
    _make_repo(coded)
    rows = _rows(file_door.read(_target()))
    rows[1][3] = "y"
    with drive_door.running("outer", may_write=True):
        with drive_door.running("inner", may_write=True):
            file_door.write(_target(), _text(rows), why="answered")
        assert _git(coded, "log", "-1", "--format=%s").startswith("data: inner")


# ---------------------------------------------------------------------------
# The chapters' files in .papers/
# ---------------------------------------------------------------------------

def test_a_built_paper_file_is_rewritten_and_removed():
    import argparse
    target = file_door.paper_built("stan1293/fragments/x.tex")
    with drive_door.running("build-chapters", argparse.Namespace(apply=True)):
        assert file_door.write_paper(target, "a\n")
        assert not file_door.write_paper(target, "a\n")
        assert file_door.write_paper(target, "b\n")
        assert file_door.remove_paper(target)
    assert not target.path.exists()


def test_a_stub_is_made_once_and_never_written_over_or_removed_blind():
    target = file_door.paper_stub("stan1293/prose/background.tex")
    with drive_door.running("t", may_write=True):
        assert file_door.write_paper(target, "\\proseslot{background}\n")
        assert not file_door.write_paper(target, "\\proseslot{background}\n")
        with pytest.raises(DoorViolation, match="never writes over"):
            file_door.write_paper(target, "something else\n")
        with pytest.raises(DoorViolation, match="never removes"):
            file_door.remove_paper(target)
        with pytest.raises(DoorViolation, match="no longer there"):
            file_door.remove_paper(target, replaces="an older version\n")
    assert file_door.read_paper(target) == "\\proseslot{background}\n"
    with drive_door.running("t", may_write=True):
        assert file_door.remove_paper(target, replaces="\\proseslot{background}\n")


def test_a_dry_run_writes_no_paper_file():
    import argparse
    target = file_door.paper_built("main.tex")
    with drive_door.running("build-chapters", argparse.Namespace(apply=False)):
        with pytest.raises(DoorViolation, match="dry run"):
            file_door.write_paper(target, "x\n")
    assert not target.path.exists()


def test_a_paper_file_stays_inside_papers():
    with pytest.raises(ValueError, match="inside .papers"):
        file_door.paper_built("../stan1293/planar_stan1293.tsv")
