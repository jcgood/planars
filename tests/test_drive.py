"""Tests for coding/drive.py — the coded_data/ git-safety helpers.

Covers:
  - _check_coded_data_clean: aborts when coded_data/ has uncommitted changes
    (shared by import-sheets, update-sheets, sync-params, and
    generate-sheets --regen-dependents)
  - _autocommit_data: commits+pushes writes to coded_data/; raises on a
    failed add/commit rather than silently warning (see issue #248's
    stray-row incident, caused by exactly that silent-warning gap)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coding.drive import _autocommit_data, _check_coded_data_clean


def _make_git_repo(path: Path) -> None:
    """Initialise a git repo at path with a committed TSV."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )
    tsv = path / "general.tsv"
    tsv.write_text("Position\tval\n1\ty\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "init"],
        check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# _check_coded_data_clean
# ---------------------------------------------------------------------------

class TestCheckCodedDataClean:
    def test_passes_when_no_git_repo(self, tmp_path):
        _check_coded_data_clean(coded_data_dir=tmp_path)  # no error

    def test_passes_on_clean_repo(self, tmp_path):
        _make_git_repo(tmp_path)
        _check_coded_data_clean(coded_data_dir=tmp_path)  # no error

    def test_aborts_on_modified_tsv(self, tmp_path):
        _make_git_repo(tmp_path)
        (tmp_path / "general.tsv").write_text("Position\tval\n1\tn\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            _check_coded_data_clean(coded_data_dir=tmp_path)

    def test_passes_when_only_non_matching_extension_dirty(self, tmp_path):
        _make_git_repo(tmp_path)
        (tmp_path / "notes.txt").write_text("scratch\n", encoding="utf-8")
        _check_coded_data_clean(coded_data_dir=tmp_path)  # no error — .txt, not .tsv

    def test_extensions_param_widens_the_check(self, tmp_path):
        _make_git_repo(tmp_path)
        (tmp_path / "notes.txt").write_text("scratch\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            _check_coded_data_clean(coded_data_dir=tmp_path, extensions=(".tsv", ".txt"))


# ---------------------------------------------------------------------------
# _autocommit_data
# ---------------------------------------------------------------------------

class TestAutocommitData:
    def test_no_paths_is_a_noop(self, tmp_path, monkeypatch):
        monkeypatch.setattr("coding.drive.CODED_DATA", tmp_path)
        _autocommit_data([], "message")  # no error, nothing to do

    def test_commits_successfully(self, tmp_path, monkeypatch):
        _make_git_repo(tmp_path)
        monkeypatch.setattr("coding.drive.CODED_DATA", tmp_path)
        new_file = tmp_path / "new_construction.tsv"
        new_file.write_text("x\n", encoding="utf-8")
        _autocommit_data([new_file], "add construction")
        log = subprocess.run(
            ["git", "-C", str(tmp_path), "log", "--oneline", "-1"],
            check=True, capture_output=True, text=True,
        )
        assert "add construction" in log.stdout
        status = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain"],
            check=True, capture_output=True, text=True,
        )
        assert status.stdout == ""  # clean after commit (push failure is not fatal)

    def test_nothing_to_commit_does_not_raise(self, tmp_path, monkeypatch):
        _make_git_repo(tmp_path)
        monkeypatch.setattr("coding.drive.CODED_DATA", tmp_path)
        unchanged = tmp_path / "general.tsv"
        _autocommit_data([unchanged], "no real change")  # no error

    def test_commit_failure_raises_and_leaves_dirty_tree(self, tmp_path, monkeypatch):
        # Force a commit failure deterministically (independent of whatever
        # git identity happens to be configured on the host) via a
        # pre-commit hook that always fails -- mirrors the #248 failure mode
        # in kind, if not in exact cause: some commit-time failure happens,
        # and it must not be treated as a silent no-op.
        _make_git_repo(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hook = hooks_dir / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        monkeypatch.setattr("coding.drive.CODED_DATA", tmp_path)
        new_file = tmp_path / "new_construction.tsv"
        new_file.write_text("x\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            _autocommit_data([new_file], "add construction")
        # The write reached disk (as it did on 2026-07-29) but must NOT be
        # silently treated as committed -- the tree should still read dirty.
        status = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain"],
            check=True, capture_output=True, text=True,
        )
        assert status.stdout != ""

    def test_add_failure_raises(self, tmp_path, monkeypatch):
        _make_git_repo(tmp_path)
        monkeypatch.setattr("coding.drive.CODED_DATA", tmp_path)
        missing = tmp_path / "does_not_exist.tsv"
        with pytest.raises(SystemExit):
            _autocommit_data([missing], "add nothing")

    def test_push_failure_does_not_raise(self, tmp_path, monkeypatch):
        # A commit with no configured remote fails to push, but the commit
        # itself succeeded -- coded_data/ is clean locally, so this must not
        # raise (only the remote lags, not local git state).
        _make_git_repo(tmp_path)
        monkeypatch.setattr("coding.drive.CODED_DATA", tmp_path)
        new_file = tmp_path / "new_construction.tsv"
        new_file.write_text("x\n", encoding="utf-8")
        _autocommit_data([new_file], "add construction")  # no error despite no remote
