"""The tooling's state files live in planars-data (Phase 10 unit 12).

coding/state_files.py: what a command's end commits and pushes, and the
coded_data_up_to_date check that keeps apply-pending and restructure-sheets
off a copy older than GitHub's. Run against scratch git repositories.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coding import preconditions, state_files


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _identity(repo: Path) -> None:
    _git(repo, "config", "user.name", "test")
    _git(repo, "config", "user.email", "t@example.org")


@pytest.fixture()
def data(tmp_path, monkeypatch):
    """A scratch planars-data with a remote, and the state files inside it."""
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    repo = tmp_path / "coded_data"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _identity(repo)
    (repo / "people.yaml").write_text("{}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "start")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "main")

    state = repo / ".state"
    monkeypatch.setattr(state_files, "CODED_DATA", repo)
    monkeypatch.setattr(state_files, "STATE_DIR", state)
    monkeypatch.setattr(state_files, "PENDING_PATH", state / "pending_changes.json")
    monkeypatch.setattr(state_files, "PROVENANCE_LOG", state / "provenance_log.jsonl")
    monkeypatch.setattr(state_files, "SNAPSHOT_DIR", state / "regen_snapshots")
    monkeypatch.setattr(state_files, "JOURNAL_PATH", state / "restructure_journal.json")
    return repo, remote


def _on_remote(remote: Path) -> list:
    return _git(remote, "ls-tree", "-r", "--name-only", "main").split()


def test_changed_state_files_are_committed_and_pushed(data):
    repo, remote = data
    state_files.PENDING_PATH.parent.mkdir(parents=True)
    state_files.PENDING_PATH.write_text("[]")
    state_files.SNAPSHOT_DIR.mkdir()
    (state_files.SNAPSHOT_DIR / "tab.json").write_text("{}")

    assert state_files.commit_changed("import-sheets")

    assert _git(repo, "status", "--porcelain") == ""
    assert {".state/pending_changes.json", ".state/regen_snapshots/tab.json"} \
        <= set(_on_remote(remote))
    assert _git(repo, "log", "-1", "--format=%s").strip() == "state: after import-sheets"


def test_nothing_but_the_state_files_is_committed(data):
    """Another file left uncommitted (a coordinator's edit in progress) stays
    exactly as it was."""
    repo, _ = data
    (repo / "people.yaml").write_text("{changed: true}\n")
    state_files.PROVENANCE_LOG.parent.mkdir(parents=True)
    state_files.PROVENANCE_LOG.write_text('{"x": 1}\n')

    state_files.commit_changed("update-sheets")

    assert _git(repo, "status", "--porcelain").strip() == "M people.yaml"


def test_a_cleared_journal_is_committed_as_removed(data):
    repo, remote = data
    state_files.JOURNAL_PATH.parent.mkdir(parents=True)
    state_files.JOURNAL_PATH.write_text("{}")
    state_files.commit_changed("restructure-sheets")
    state_files.JOURNAL_PATH.unlink()

    assert state_files.commit_changed("restructure-sheets --resume")

    assert ".state/restructure_journal.json" not in _on_remote(remote)


def test_no_change_makes_no_commit(data):
    repo, _ = data
    head = _git(repo, "rev-parse", "HEAD")
    assert not state_files.commit_changed("registry")
    assert _git(repo, "rev-parse", "HEAD") == head


def test_not_a_git_repository_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(state_files, "CODED_DATA", tmp_path)
    state_files.PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    state_files.PENDING_PATH.write_text("[]")
    assert not state_files.commit_changed("import-sheets")


def _advance_remote(tmp_path: Path, remote: Path) -> None:
    """Another machine (the daily refresh) pushes a commit."""
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(remote), str(other))
    _identity(other)
    (other / ".state").mkdir()
    (other / ".state" / "pending_changes.json").write_text('[{"type": "x"}]')
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "state: after import-sheets")
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
