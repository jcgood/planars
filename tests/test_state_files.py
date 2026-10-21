"""The tooling's own files live in planars-data (Phase 10 units 12 and 6b).

coding/state_files.py says where each is; the local-file door
(coding/file_door.py) writes them and commits and pushes them when the
command ends; the coded_data_up_to_date check keeps apply-pending and
restructure-sheets off a copy older than GitHub's. Run against scratch git
repositories.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from coding import drive_door, file_door, preconditions, state_files
from coding.file_door import DoorViolation
from conftest import point_state_files_at


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _identity(repo: Path) -> None:
    _git(repo, "config", "user.name", "test")
    _git(repo, "config", "user.email", "t@example.org")


@pytest.fixture()
def data(tmp_path, monkeypatch):
    """A scratch planars-data with a remote; the door and the state files
    both point into it."""
    remote = tmp_path / "remote.git"
    # The branch is named, not left to the machine's default (main here,
    # master on GitHub's runners, where the clone below then checked out
    # nothing and its push never reached main).
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    repo = tmp_path / "coded_data"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _identity(repo)
    (repo / "people.yaml").write_text("{}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "start")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")

    point_state_files_at(monkeypatch, repo)
    monkeypatch.setattr(file_door, "CODED_DATA", repo)
    return repo, remote


def _on_remote(remote: Path) -> list:
    return _git(remote, "ls-tree", "-r", "--name-only", "main").split()


def test_each_kind_names_its_own_file(data):
    repo, _ = data
    assert file_door.pending_changes().path == repo / ".state" / "pending_changes.json"
    assert file_door.notes_state().relpath == ".state/notes_state.json"
    assert file_door.regen_snapshot("t").path == repo / ".state" / "regen_snapshots" / "t.json"
    assert file_door.id_file().path == repo / "drive_config.json"
    with pytest.raises(ValueError, match="unknown kind"):
        file_door.StateFile("cache")
    with pytest.raises(ValueError, match="needs name"):
        file_door.StateFile(file_door.REGEN_SNAPSHOT)


def test_state_files_written_are_committed_and_pushed(data):
    repo, remote = data
    with drive_door.running("import-sheets", may_write=True):
        file_door.write_state(file_door.pending_changes(), "[]")
        file_door.write_state(file_door.regen_snapshot("tab"), "{}")
        file_door.write_state(file_door.id_file(), "{}")

    assert _git(repo, "status", "--porcelain") == ""
    assert {".state/pending_changes.json", ".state/regen_snapshots/tab.json",
            "drive_config.json"} <= set(_on_remote(remote))
    message = _git(repo, "log", "-1", "--format=%B")
    assert message.startswith("data: import-sheets changed 3 file(s)")
    assert ".state/pending_changes.json: written" in message


def test_nothing_but_what_was_written_is_committed(data):
    """Another file left uncommitted (a coordinator's edit in progress) stays
    exactly as it was."""
    repo, _ = data
    (repo / "people.yaml").write_text("{changed: true}\n")
    with drive_door.running("update-sheets", may_write=True):
        file_door.append_state(file_door.provenance_log(), '{"x": 1}\n')
    assert _git(repo, "status", "--porcelain").strip() == "M people.yaml"


def test_unchanged_content_makes_no_commit(data):
    repo, _ = data
    with drive_door.running("check-notes", may_write=True):
        file_door.write_state(file_door.notes_state(), "{}")
    head = _git(repo, "rev-parse", "HEAD")
    with drive_door.running("check-notes", may_write=True):
        assert not file_door.write_state(file_door.notes_state(), "{}")
    assert _git(repo, "rev-parse", "HEAD") == head


def test_a_cleared_journal_is_committed_as_removed(data):
    repo, remote = data
    with drive_door.running("restructure-sheets", may_write=True):
        file_door.write_state(file_door.restructure_journal(), '{"a": 1}')
    assert ".state/restructure_journal.json" in _on_remote(remote)
    with drive_door.running("restructure-sheets", may_write=True):
        assert file_door.remove_state(file_door.restructure_journal())
    assert ".state/restructure_journal.json" not in _on_remote(remote)


def test_a_journal_made_and_cleared_in_one_run_commits_nothing(data):
    """A restructure that finishes clears its journal: nothing for git."""
    repo, _ = data
    head = _git(repo, "rev-parse", "HEAD")
    with drive_door.running("restructure-sheets", may_write=True):
        file_door.write_state(file_door.restructure_journal(), '{"a": 1}')
        file_door.remove_state(file_door.restructure_journal())
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "status", "--porcelain") == ""


def test_a_dry_run_writes_no_state_file(data):
    with drive_door.running("check-notes", argparse.Namespace(apply=False)):
        with pytest.raises(DoorViolation, match="dry run"):
            file_door.write_state(file_door.notes_state(), "{}")
    assert not state_files.NOTES_STATE_PATH.exists()


def test_a_dry_run_still_logs_the_drive_writes_it_was_allowed(data):
    """import-sheets' highlighting is written even on a dry run
    (always_on_writes), and the Drive door logs it."""
    with drive_door.running("import-sheets", argparse.Namespace(apply=False)):
        file_door.append_state(file_door.provenance_log(), '{"x": 1}\n')
    assert state_files.PROVENANCE_LOG.read_text() == '{"x": 1}\n'


def test_no_command_running_is_refused(data):
    with pytest.raises(DoorViolation, match="no command is running"):
        file_door.write_state(file_door.pending_changes(), "[]")


def _advance_remote(tmp_path: Path, remote: Path) -> None:
    """Another machine (the daily refresh) pushes a commit."""
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", "-b", "main", str(remote), str(other))
    _identity(other)
    (other / ".state").mkdir()
    (other / ".state" / "pending_changes.json").write_text('[{"type": "x"}]')
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "data: import-sheets changed 1 file(s)")
    _git(other, "push", "-q")


def test_behind_remote_counts_what_the_refresh_pushed(data, tmp_path):
    repo, remote = data
    assert state_files.behind_remote() == 0
    _advance_remote(tmp_path, remote)
    assert state_files.behind_remote() == 1


def test_apply_pending_stops_on_a_copy_older_than_githubs(data, tmp_path):
    """The done-when of unit 12: a daily-refresh import's pending changes are
    visible to local apply-pending — it pulls first, or is told to."""
    _, remote = data
    _advance_remote(tmp_path, remote)
    with pytest.raises(SystemExit) as stopped:
        preconditions._check_coded_data_up_to_date("apply_pending")
    assert "git -C coded_data pull" in str(stopped.value.code)
    assert "apply-pending" in str(stopped.value.code)


def test_up_to_date_lets_it_run(data):
    preconditions._check_coded_data_up_to_date("apply_pending")


def test_no_upstream_branch_stops_and_says_why(data):
    repo, _ = data
    _git(repo, "branch", "--unset-upstream")
    with pytest.raises(SystemExit) as stopped:
        preconditions._check_coded_data_up_to_date("restructure_sheets")
    assert "could not check" in str(stopped.value.code)


def test_both_commands_declare_it():
    from coding.registry import _load_operations
    ops = _load_operations()
    for op in ("apply_pending", "restructure_sheets"):
        assert "coded_data_up_to_date" in ops[op]["preconditions"]
