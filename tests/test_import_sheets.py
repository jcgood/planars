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

import textwrap

import pandas as pd

from coding.import_sheets import (
    _archive_tsv,
    _check_coded_data_clean,
    _detect_diagnostics_changes,
    _detect_planar_changes,
    _tsv_content_changed,
    _verify_manifest_sheet_ids,
    _check_yaml_drift,
)
import coding.import_sheets as _is


# ---------------------------------------------------------------------------
# _archive_tsv
# ---------------------------------------------------------------------------

class TestArchiveTsv:
    # _archive_tsv expects path to be {lang}/{class}/file.tsv and archives to
    # {lang}/archive/{class}/file_timestamp.tsv — tests use lang/class/file structure.

    def test_creates_archive_dir(self, tmp_path):
        class_dir = tmp_path / "ciscategorial"
        class_dir.mkdir()
        tsv = class_dir / "general.tsv"
        tsv.write_text("Position\tval\n1\ty\n", encoding="utf-8")
        _archive_tsv(tsv, "20260325_120000")
        assert (tmp_path / "archive" / "ciscategorial").is_dir()

    def test_archive_file_has_timestamp_suffix(self, tmp_path):
        class_dir = tmp_path / "ciscategorial"
        class_dir.mkdir()
        tsv = class_dir / "general.tsv"
        tsv.write_text("a\tb\n", encoding="utf-8")
        archived = _archive_tsv(tsv, "20260325_120000")
        assert archived.name == "general_20260325_120000.tsv"

    def test_archive_content_matches_original(self, tmp_path):
        content = "Position\tcriterion\n1\ty\n2\tn\n"
        class_dir = tmp_path / "ciscategorial"
        class_dir.mkdir()
        tsv = class_dir / "general.tsv"
        tsv.write_text(content, encoding="utf-8")
        archived = _archive_tsv(tsv, "20260325_120000")
        assert archived.read_text(encoding="utf-8") == content

    def test_original_file_unchanged(self, tmp_path):
        content = "Position\tval\n"
        class_dir = tmp_path / "ciscategorial"
        class_dir.mkdir()
        tsv = class_dir / "general.tsv"
        tsv.write_text(content, encoding="utf-8")
        _archive_tsv(tsv, "20260325_120000")
        assert tsv.read_text(encoding="utf-8") == content

    def test_archive_dir_created_if_missing(self, tmp_path):
        class_dir = tmp_path / "ciscategorial"
        class_dir.mkdir()
        tsv = class_dir / "general.tsv"
        tsv.write_text("x\n", encoding="utf-8")
        assert not (tmp_path / "archive").exists()
        _archive_tsv(tsv, "ts")
        assert (tmp_path / "archive" / "ciscategorial").is_dir()

    def test_multiple_archives_distinct(self, tmp_path):
        class_dir = tmp_path / "ciscategorial"
        class_dir.mkdir()
        tsv = class_dir / "general.tsv"
        tsv.write_text("v1\n", encoding="utf-8")
        a1 = _archive_tsv(tsv, "20260325_100000")
        tsv.write_text("v2\n", encoding="utf-8")
        a2 = _archive_tsv(tsv, "20260325_110000")
        assert a1 != a2
        assert a1.read_text(encoding="utf-8") == "v1\n"
        assert a2.read_text(encoding="utf-8") == "v2\n"

    def test_returns_archive_path(self, tmp_path):
        class_dir = tmp_path / "ciscategorial"
        class_dir.mkdir()
        tsv = class_dir / "general.tsv"
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


# ---------------------------------------------------------------------------
# _check_yaml_drift
# ---------------------------------------------------------------------------

_YAML_CONTENT = textwrap.dedent("""\
    language: lang0001
    classes:
      ciscategorial:
        constructions: [general]
        criteria:
          V-combines: [y, n]
          N-combines: [y, n]
""")


class TestCheckYamlDrift:
    def _tsv_df(self, criteria="V-combines, N-combines"):
        return pd.DataFrame(
            [{"Class": "ciscategorial", "Language": "lang0001",
              "Constructions": "general", "Criteria": criteria}],
            columns=["Class", "Language", "Constructions", "Criteria"],
        )

    def test_returns_empty_when_no_yaml(self, tmp_path, monkeypatch):
        """No YAML → no drift."""
        monkeypatch.setattr(_is, "ROOT", tmp_path)
        tsv_df = self._tsv_df()
        result = _check_yaml_drift("lang0001", tsv_df)
        assert result == []

    def test_returns_empty_when_in_sync(self, tmp_path, monkeypatch):
        """TSV matches YAML → no ambiguous drift."""
        monkeypatch.setattr(_is, "ROOT", tmp_path)
        yaml_dir = tmp_path / "coded_data" / "lang0001" / "lang_setup"
        yaml_dir.mkdir(parents=True)
        (yaml_dir / "diagnostics_lang0001.yaml").write_text(_YAML_CONTENT)
        result = _check_yaml_drift("lang0001", self._tsv_df())
        assert result == []

    def test_returns_ambiguous_for_unknown_criterion(self, tmp_path, monkeypatch):
        """Unknown criterion in TSV surfaces as ambiguous drift entry."""
        monkeypatch.setattr(_is, "ROOT", tmp_path)
        yaml_dir = tmp_path / "coded_data" / "lang0001" / "lang_setup"
        yaml_dir.mkdir(parents=True)
        (yaml_dir / "diagnostics_lang0001.yaml").write_text(_YAML_CONTENT)
        tsv_df = self._tsv_df("V-combines, N-combines, totally_made_up_zyx")
        result = _check_yaml_drift("lang0001", tsv_df)
        assert len(result) == 1
        assert result[0]["kind"] == "unknown_criterion"


# ---------------------------------------------------------------------------
# _tsv_content_changed
# ---------------------------------------------------------------------------

def _write_tsv_file(path: Path, header: list[str], records: list[dict]) -> None:
    import csv
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, delimiter="\t",
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


class TestTsvContentChanged:
    def test_returns_false_when_identical(self, tmp_path):
        header = ["Element", "criterion"]
        records = [{"Element": "a", "criterion": "y"}, {"Element": "b", "criterion": "n"}]
        p = tmp_path / "data.tsv"
        _write_tsv_file(p, header, records)
        assert _tsv_content_changed(p, header, records) is False

    def test_returns_true_when_value_differs(self, tmp_path):
        header = ["Element", "criterion"]
        old_records = [{"Element": "a", "criterion": "y"}]
        new_records = [{"Element": "a", "criterion": "n"}]
        p = tmp_path / "data.tsv"
        _write_tsv_file(p, header, old_records)
        assert _tsv_content_changed(p, header, new_records) is True

    def test_returns_true_when_row_added(self, tmp_path):
        header = ["Element", "criterion"]
        old_records = [{"Element": "a", "criterion": "y"}]
        new_records = [{"Element": "a", "criterion": "y"}, {"Element": "b", "criterion": "n"}]
        p = tmp_path / "data.tsv"
        _write_tsv_file(p, header, old_records)
        assert _tsv_content_changed(p, header, new_records) is True

    def test_returns_true_when_file_missing(self, tmp_path):
        header = ["Element", "criterion"]
        records = [{"Element": "a", "criterion": "y"}]
        p = tmp_path / "nonexistent.tsv"
        assert _tsv_content_changed(p, header, records) is True

    def test_handles_column_reorder(self, tmp_path):
        # File written with columns in different order — both reindexed to header.
        file_header = ["criterion", "Element"]
        new_header = ["Element", "criterion"]
        records = [{"Element": "a", "criterion": "y"}]
        p = tmp_path / "data.tsv"
        _write_tsv_file(p, file_header, records)
        assert _tsv_content_changed(p, new_header, records) is False


# ---------------------------------------------------------------------------
# _detect_planar_changes
# ---------------------------------------------------------------------------

def _planar_df(positions: list[tuple[str, str]]) -> "pd.DataFrame":
    import pandas as pd
    nums, names = zip(*positions) if positions else ([], [])
    return pd.DataFrame({"Position": list(nums), "Position_Name": list(names)})


class TestDetectPlanarChanges:
    def test_no_change_returns_empty(self):
        df = _planar_df([("1", "p1"), ("2", "p2")])
        safe, pending = _detect_planar_changes(df, df, "lang0001")
        assert safe == set()
        assert pending == []

    def test_pure_addition_at_end_queues_update_sheets(self):
        old = _planar_df([("1", "p1"), ("2", "p2")])
        new = _planar_df([("1", "p1"), ("2", "p2"), ("3", "p3")])
        safe, pending = _detect_planar_changes(old, new, "lang0001")
        assert any("update-sheets" in cmd for cmd in safe)
        assert pending == []

    def test_pure_addition_inserted_in_middle_queues_update_sheets(self):
        # New position inserted between existing ones — old positions still in order.
        old = _planar_df([("1", "p1"), ("3", "p3")])
        new = _planar_df([("1", "p1"), ("2", "p2"), ("3", "p3")])
        safe, pending = _detect_planar_changes(old, new, "lang0001")
        assert any("update-sheets" in cmd for cmd in safe)
        assert pending == []

    def test_deletion_produces_pending(self):
        old = _planar_df([("1", "p1"), ("2", "p2")])
        new = _planar_df([("1", "p1")])
        safe, pending = _detect_planar_changes(old, new, "lang0001")
        assert len(pending) == 1
        assert pending[0]["change_type"] == "planar_deletion_or_reorder"

    def test_reorder_produces_pending(self):
        old = _planar_df([("1", "p1"), ("2", "p2")])
        new = _planar_df([("2", "p2"), ("1", "p1")])
        safe, pending = _detect_planar_changes(old, new, "lang0001")
        assert len(pending) == 1
        assert pending[0]["change_type"] == "planar_deletion_or_reorder"

    def test_addition_with_removal_produces_pending(self):
        # Adding p3 while removing p2 is not a safe-add — it goes to pending.
        old = _planar_df([("1", "p1"), ("2", "p2")])
        new = _planar_df([("1", "p1"), ("3", "p3")])
        safe, pending = _detect_planar_changes(old, new, "lang0001")
        assert len(pending) == 1


# ---------------------------------------------------------------------------
# _detect_diagnostics_changes
# ---------------------------------------------------------------------------

def _diag_df(rows: list[dict]) -> "pd.DataFrame":
    import pandas as pd
    cols = ["Class", "Language", "Constructions", "Criteria"]
    return pd.DataFrame(rows, columns=cols)


def _row_diag(cls: str, constructions: str = "general", criteria: str = "V-combines") -> dict:
    return {"Class": cls, "Language": "lang0001",
            "Constructions": constructions, "Criteria": criteria}


class TestDetectDiagnosticsChanges:
    def test_no_change_returns_empty(self):
        df = _diag_df([_row_diag("ciscategorial")])
        safe, pending = _detect_diagnostics_changes(df, df, "lang0001")
        assert safe == set()
        assert pending == []

    def test_new_class_queues_generate_sheets(self):
        old = _diag_df([_row_diag("ciscategorial")])
        new = _diag_df([_row_diag("ciscategorial"), _row_diag("noninterruption")])
        safe, pending = _detect_diagnostics_changes(old, new, "lang0001")
        assert any("generate-sheets" in cmd for cmd in safe)

    def test_removed_class_produces_pending(self):
        old = _diag_df([_row_diag("ciscategorial"), _row_diag("noninterruption")])
        new = _diag_df([_row_diag("ciscategorial")])
        safe, pending = _detect_diagnostics_changes(old, new, "lang0001")
        assert any(p["change_type"] == "diagnostics_class_removed" for p in pending)

    def test_new_construction_produces_pending(self):
        old = _diag_df([_row_diag("nonpermutability", constructions="element_prescreening")])
        new = _diag_df([_row_diag("nonpermutability",
                                  constructions="element_prescreening, general")])
        safe, pending = _detect_diagnostics_changes(old, new, "lang0001")
        assert any(p["change_type"] == "diagnostics_new_construction" for p in pending)

    def test_removed_construction_produces_pending(self):
        old = _diag_df([_row_diag("nonpermutability",
                                  constructions="element_prescreening, general")])
        new = _diag_df([_row_diag("nonpermutability", constructions="element_prescreening")])
        safe, pending = _detect_diagnostics_changes(old, new, "lang0001")
        assert any(p["change_type"] == "diagnostics_construction_removed" for p in pending)

    def test_added_criterion_queues_sync_params(self):
        old = _diag_df([_row_diag("ciscategorial", criteria="V-combines")])
        new = _diag_df([_row_diag("ciscategorial", criteria="V-combines, N-combines")])
        safe, pending = _detect_diagnostics_changes(old, new, "lang0001")
        assert any("sync-params" in cmd for cmd in safe)

    def test_removed_criterion_produces_pending(self):
        old = _diag_df([_row_diag("ciscategorial", criteria="V-combines, N-combines")])
        new = _diag_df([_row_diag("ciscategorial", criteria="V-combines")])
        safe, pending = _detect_diagnostics_changes(old, new, "lang0001")
        assert any(p["change_type"] == "diagnostics_criteria_removed" for p in pending)
