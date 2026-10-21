"""Tests for coding/file_door.py, the local-file door (Phase 10 unit 6a).

Each rule in the module docstring, the archive and change log it keeps, the
commit when a command ends, and watch mode. The files are a private copy of
the frozen data (fake_drive.use_frozen_coded_data), so the spec checks run
against real diagnostics files. The door enforces in every test
(tests/conftest.py); a test of watch mode sets it.
"""
from __future__ import annotations

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
    return use_frozen_coded_data(monkeypatch, tmp_path)


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
    assert file_door.diagnostics_tsv(LANG).name == f"diagnostics_{LANG}.tsv"


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
    ops["import_planar"] = dict(ops["import_planar"], edits_sources=["planr"])
    monkeypatch.setattr("coding.registry._load_operations", lambda: ops)
    with pytest.raises(ValueError, match="not sources"):
        file_door.begin("import-planar")


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
    """CRLF line ends (import-sheets' csv writer) survive the write."""
    text = file_door.read(_target())
    assert "\r\n" in text
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
# Watch mode
# ---------------------------------------------------------------------------

def test_watch_mode_lets_the_write_through_and_files_one_issue(coded, monkeypatch, github):
    monkeypatch.setattr(file_door, "MODE", file_door.WATCH)
    rows = _rows(_answered(coded))
    del rows[1]
    with drive_door.running("t", may_write=True):
        assert file_door.write(_target(), _text(rows), why="test")
    assert file_door.read(_target()) == _text(rows)
    [issue] = github.list_issues(drive_door.VIOLATION_LABEL)
    assert issue["title"] == "Local-file door: writes that broke a rule"
    assert "answered row(s) would be lost" in issue["body"]


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
