"""Tests for coding/import_sheets.py — data-protection helpers.

Covers the three safety functions added to prevent annotation data loss:
  - _archive_tsv: copies a TSV to archive/ before overwriting
  - _check_coded_data_clean: aborts when coded_data/ has uncommitted TSV changes
  - _verify_manifest_sheet_ids: aborts when any manifest sheet ID is inaccessible
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from coding.import_sheets import (
    _archive_tsv,
    _check_coded_data_clean,
    _verify_manifest_sheet_ids,
)


# ---------------------------------------------------------------------------
# _archive_tsv
# ---------------------------------------------------------------------------

class TestArchiveTsv:
    def test_creates_archive_dir(self, tmp_path):
        tsv = tmp_path / "general.tsv"
        tsv.write_text("Position\tval\n1\ty\n", encoding="utf-8")
        _archive_tsv(tsv, "20260325_120000")
        assert (tmp_path / "archive").is_dir()

    def test_archive_file_has_timestamp_suffix(self, tmp_path):
        tsv = tmp_path / "general.tsv"
        tsv.write_text("a\tb\n", encoding="utf-8")
        archived = _archive_tsv(tsv, "20260325_120000")
        assert archived.name == "general_20260325_120000.tsv"

    def test_archive_content_matches_original(self, tmp_path):
        content = "Position\tcriterion\n1\ty\n2\tn\n"
        tsv = tmp_path / "general.tsv"
        tsv.write_text(content, encoding="utf-8")
        archived = _archive_tsv(tsv, "20260325_120000")
        assert archived.read_text(encoding="utf-8") == content

    def test_original_file_unchanged(self, tmp_path):
        content = "Position\tval\n"
        tsv = tmp_path / "general.tsv"
        tsv.write_text(content, encoding="utf-8")
        _archive_tsv(tsv, "20260325_120000")
        assert tsv.read_text(encoding="utf-8") == content

    def test_archive_dir_created_if_missing(self, tmp_path):
        tsv = tmp_path / "subdir" / "general.tsv"
        tsv.parent.mkdir()
        tsv.write_text("x\n", encoding="utf-8")
        assert not (tsv.parent / "archive").exists()
        _archive_tsv(tsv, "ts")
        assert (tsv.parent / "archive").is_dir()

    def test_multiple_archives_distinct(self, tmp_path):
        tsv = tmp_path / "general.tsv"
        tsv.write_text("v1\n", encoding="utf-8")
        a1 = _archive_tsv(tsv, "20260325_100000")
        tsv.write_text("v2\n", encoding="utf-8")
        a2 = _archive_tsv(tsv, "20260325_110000")
        assert a1 != a2
        assert a1.read_text(encoding="utf-8") == "v1\n"
        assert a2.read_text(encoding="utf-8") == "v2\n"

    def test_returns_archive_path(self, tmp_path):
        tsv = tmp_path / "general.tsv"
        tsv.write_text("x\n", encoding="utf-8")
        result = _archive_tsv(tsv, "ts")
        assert isinstance(result, Path)
        assert result.exists()


# ---------------------------------------------------------------------------
# _check_coded_data_clean
# ---------------------------------------------------------------------------

def _make_git_repo(path: Path) -> None:
    """Initialise a bare git repo at path with a committed TSV."""
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


class TestCheckCodedDataClean:
    def test_passes_when_no_git_repo(self, tmp_path):
        # Should silently skip if coded_data/ is not a git repo.
        _check_coded_data_clean(coded_data_dir=tmp_path)  # no error

    def test_passes_on_clean_repo(self, tmp_path):
        _make_git_repo(tmp_path)
        _check_coded_data_clean(coded_data_dir=tmp_path)  # no error

    def test_aborts_on_modified_tsv(self, tmp_path):
        _make_git_repo(tmp_path)
        (tmp_path / "general.tsv").write_text("Position\tval\n1\tn\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            _check_coded_data_clean(coded_data_dir=tmp_path)

    def test_aborts_on_new_untracked_tsv(self, tmp_path):
        _make_git_repo(tmp_path)
        (tmp_path / "new_construction.tsv").write_text("x\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            _check_coded_data_clean(coded_data_dir=tmp_path)

    def test_passes_when_only_non_tsv_dirty(self, tmp_path):
        _make_git_repo(tmp_path)
        (tmp_path / "notes.txt").write_text("scratch\n", encoding="utf-8")
        _check_coded_data_clean(coded_data_dir=tmp_path)  # no error — .txt, not .tsv

    def test_passes_after_committing_changes(self, tmp_path):
        _make_git_repo(tmp_path)
        (tmp_path / "general.tsv").write_text("updated\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "update"],
            check=True, capture_output=True,
        )
        _check_coded_data_clean(coded_data_dir=tmp_path)  # no error after commit


# ---------------------------------------------------------------------------
# _verify_manifest_sheet_ids
# ---------------------------------------------------------------------------

def _make_drive_mock(bad_ids: set = frozenset()):
    """Return a minimal Drive mock where bad_ids raise on execute()."""
    class _Files:
        def get(self, fileId, fields=None):
            class _Req:
                def execute(self_inner):
                    if fileId in bad_ids:
                        raise Exception(f"404: File not found: {fileId}")
                    return {"id": fileId}
            return _Req()
    class _Drive:
        def files(self):
            return _Files()
    return _Drive()


class TestVerifyManifestSheetIds:
    def _manifest(self, ids: dict[str, str]) -> dict:
        """Build a minimal manifest with one class per lang_id."""
        result = {}
        for lang_id, spreadsheet_id in ids.items():
            result[lang_id] = {
                "sheets": {
                    "ciscategorial": {"spreadsheet_id": spreadsheet_id}
                }
            }
        return result

    def test_passes_with_all_accessible(self):
        manifest = self._manifest({"arao1248": "sheet_id_1", "stan1293": "sheet_id_2"})
        drive = _make_drive_mock()
        _verify_manifest_sheet_ids(drive, manifest)  # no error

    def test_aborts_when_sheet_inaccessible(self):
        manifest = self._manifest({"arao1248": "bad_id"})
        drive = _make_drive_mock(bad_ids={"bad_id"})
        with pytest.raises(SystemExit):
            _verify_manifest_sheet_ids(drive, manifest)

    def test_aborts_on_any_bad_id_among_multiple(self):
        manifest = self._manifest({"arao1248": "good_id", "stan1293": "bad_id"})
        drive = _make_drive_mock(bad_ids={"bad_id"})
        with pytest.raises(SystemExit):
            _verify_manifest_sheet_ids(drive, manifest)

    def test_passes_empty_manifest(self):
        _verify_manifest_sheet_ids(_make_drive_mock(), {})  # no error

    def test_skips_entries_without_spreadsheet_id(self):
        manifest = {
            "arao1248": {
                "sheets": {"ciscategorial": {"url": "https://example.com"}}
            }
        }
        _verify_manifest_sheet_ids(_make_drive_mock(), manifest)  # no error

    def test_skips_non_dict_lang_data(self):
        manifest = {"_root_folder_id": "some_folder_id"}
        _verify_manifest_sheet_ids(_make_drive_mock(), manifest)  # no error
