"""Tests for coding/drive.py.

Covers:
  - _check_coded_data_clean: aborts when coded_data/ has uncommitted changes
    (shared by import-sheets, update-sheets, sync-params, and
    generate-sheets --regen-dependents)
  - _autocommit_data: commits+pushes writes to coded_data/; raises on a
    failed add/commit rather than silently warning (see issue #248's
    stray-row incident, caused by exactly that silent-warning gap)
  - ensure_anyone_permission / create_or_update_shared_file /
    get_or_create_spreadsheet: the three shared Drive-sharing/creation
    helpers issue #276 collapsed generate_notebooks.py's, generate_reports.py's,
    setup_root_folder.py's, generate_status_sheet.py's, and
    generate_biuniqueness_allomorphy_sheet.py's per-file duplicates into.
    Exercised here directly, against a bare FakeDriveDoorway, since they are
    pure Drive primitives with no per-language data dependency (unlike most
    of this project's other Drive-facing tests, which are command-level
    snapshot tests under a seeded fixture).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coding.drive import (
    _autocommit_data,
    _check_coded_data_clean,
    create_or_update_shared_file,
    ensure_anyone_permission,
    get_or_create_spreadsheet,
)
from fake_drive import FakeDriveDoorway


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


# ---------------------------------------------------------------------------
# ensure_anyone_permission
# ---------------------------------------------------------------------------

class TestEnsureAnyonePermission:
    def test_creates_a_grant_when_none_exists(self):
        doorway = FakeDriveDoorway()
        file_id = doorway.seed_file("f.txt", "text/plain")
        ensure_anyone_permission(doorway, file_id)
        perms = doorway.list_permissions(file_id)
        assert [(p["type"], p["role"]) for p in perms] == [("anyone", "reader")]
        assert len(doorway.mutations_of("create_permission")) == 1

    def test_role_is_passed_through(self):
        doorway = FakeDriveDoorway()
        file_id = doorway.seed_file("f.txt", "text/plain")
        ensure_anyone_permission(doorway, file_id, role="writer")
        assert doorway.list_permissions(file_id)[0]["role"] == "writer"

    def test_skips_creating_a_second_grant_when_one_already_exists(self):
        """The property that makes it safe to call unconditionally every run:
        a repeat call finds the existing grant and does nothing."""
        doorway = FakeDriveDoorway()
        file_id = doorway.seed_file("f.txt", "text/plain")
        ensure_anyone_permission(doorway, file_id)
        doorway.clear_mutations()
        ensure_anyone_permission(doorway, file_id)
        assert doorway.mutations_of("create_permission") == []
        assert len(doorway.list_permissions(file_id)) == 1

    def test_a_named_person_grant_does_not_count_as_anyone(self):
        """Only an 'anyone' entry satisfies the check; a named share does not."""
        doorway = FakeDriveDoorway()
        file_id = doorway.seed_file("f.txt", "text/plain")
        doorway.create_permission(file_id, type="user", role="reader",
                                  email="adam@example.com")
        ensure_anyone_permission(doorway, file_id)
        types = {p["type"] for p in doorway.list_permissions(file_id)}
        assert types == {"user", "anyone"}


# ---------------------------------------------------------------------------
# create_or_update_shared_file
# ---------------------------------------------------------------------------

class TestCreateOrUpdateSharedFile:
    def test_creates_and_shares_when_no_existing_id(self):
        doorway = FakeDriveDoorway()
        folder_id = doorway.seed_folder("lang")
        file_id = create_or_update_shared_file(
            doorway, b"content", "notebook.ipynb", "application/json", folder_id)
        creates = doorway.mutations_of("create_file")
        assert [c["name"] for c in creates] == ["notebook.ipynb"]
        assert creates[0]["parents"] == [folder_id]
        assert doorway.mutations_of("update_file") == []
        perms = doorway.list_permissions(file_id)
        assert [(p["type"], p["role"]) for p in perms] == [("anyone", "reader")]

    def test_updates_in_place_and_renames_when_existing_id_given(self):
        doorway = FakeDriveDoorway()
        folder_id = doorway.seed_folder("lang")
        existing = doorway.seed_file("old_name.ipynb", "application/json", [folder_id])
        file_id = create_or_update_shared_file(
            doorway, b"new content", "new_name.ipynb", "application/json",
            folder_id, existing_file_id=existing)
        assert file_id == existing
        assert doorway.mutations_of("create_file") == []
        updates = doorway.mutations_of("update_file")
        assert len(updates) == 1 and updates[0]["name"] == "new_name.ipynb"

    def test_update_path_also_shares_reasserting_but_not_duplicating(self):
        """The behavioural change issue #276 makes: update reshares every run,
        but ensure_anyone_permission means a second run adds no duplicate."""
        doorway = FakeDriveDoorway()
        folder_id = doorway.seed_folder("lang")
        file_id = create_or_update_shared_file(
            doorway, b"v1", "report.pdf", "application/pdf", folder_id)
        doorway.clear_mutations()
        create_or_update_shared_file(
            doorway, b"v2", "report.pdf", "application/pdf", folder_id,
            existing_file_id=file_id)
        assert doorway.mutations_of("update_file")
        assert doorway.mutations_of("create_permission") == []  # already shared


# ---------------------------------------------------------------------------
# get_or_create_spreadsheet
# ---------------------------------------------------------------------------

class TestGetOrCreateSpreadsheet:
    def test_creates_and_moves_when_none_exists(self):
        doorway = FakeDriveDoorway()
        folder_id = doorway.seed_folder("Annotation Status")
        ss, created = get_or_create_spreadsheet(doorway, folder_id, "status_stan1293")
        assert created is True
        assert doorway.file(ss.id).name == "status_stan1293"
        moves = doorway.mutations_of("move_file")
        assert [(m["file_id"], m["to_parent"]) for m in moves] == [(ss.id, folder_id)]

    def test_finds_the_existing_spreadsheet_by_name_instead_of_creating(self):
        doorway = FakeDriveDoorway()
        folder_id = doorway.seed_folder("Annotation Status")
        first, created_first = get_or_create_spreadsheet(doorway, folder_id, "status_stan1293")
        doorway.clear_mutations()
        second, created_second = get_or_create_spreadsheet(doorway, folder_id, "status_stan1293")
        assert created_first is True
        assert created_second is False
        assert second.id == first.id
        assert doorway.mutations_of("create_file") == []
        assert doorway.mutations_of("move_file") == []
