"""Tests for coding/import_sheets.py — data-protection helpers.

Covers _verify_manifest_sheet_ids (aborts when any manifest sheet ID is
inaccessible) and _tsv_content_changed. Archiving a TSV before it is
overwritten is the local-file door's since Phase 10 unit 6a:
tests/test_file_door.py. (The planar and diagnostics Sheet downloads, with
their change detection and YAML drift check, were retired in unit 11b.)

_check_coded_data_clean now lives in coding/drive.py (shared by import-sheets,
update-sheets, sync-params, and generate-sheets --regen-dependents) — its
tests moved to tests/test_drive.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from coding.import_sheets import (
    _tsv_content_changed,
    _verify_manifest_sheet_ids,
)


# ---------------------------------------------------------------------------
# _verify_manifest_sheet_ids
# ---------------------------------------------------------------------------

class _DoorwayStub:
    """Minimal doorway-shaped stub: only get_file(file_id, fields=None).

    _verify_manifest_sheet_ids now takes a doorway rather than a raw Drive
    service (coding/drive_doorway.py's migration, #271 file 15), so this
    replaces the old _make_drive_mock's .files().get(fileId=...).execute()
    shape with the one method the doorway actually exposes.
    """

    def __init__(self, bad_ids: set = frozenset()):
        self._bad_ids = bad_ids

    def get_file(self, file_id, fields=None):
        if file_id in self._bad_ids:
            raise Exception(f"404: File not found: {file_id}")
        return {"id": file_id}


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
        doorway = _DoorwayStub()
        _verify_manifest_sheet_ids(doorway, manifest)  # no error

    def test_aborts_when_sheet_inaccessible(self):
        manifest = self._manifest({"arao1248": "bad_id"})
        doorway = _DoorwayStub(bad_ids={"bad_id"})
        with pytest.raises(SystemExit):
            _verify_manifest_sheet_ids(doorway, manifest)

    def test_aborts_on_any_bad_id_among_multiple(self):
        manifest = self._manifest({"arao1248": "good_id", "stan1293": "bad_id"})
        doorway = _DoorwayStub(bad_ids={"bad_id"})
        with pytest.raises(SystemExit):
            _verify_manifest_sheet_ids(doorway, manifest)

    def test_passes_empty_manifest(self):
        _verify_manifest_sheet_ids(_DoorwayStub(), {})  # no error

    def test_skips_entries_without_spreadsheet_id(self):
        manifest = {
            "arao1248": {
                "sheets": {"ciscategorial": {"url": "https://example.com"}}
            }
        }
        _verify_manifest_sheet_ids(_DoorwayStub(), manifest)  # no error

    def test_skips_non_dict_lang_data(self):
        manifest = {"_root_folder_id": "some_folder_id"}
        _verify_manifest_sheet_ids(_DoorwayStub(), manifest)  # no error


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

    def test_column_reorder_is_a_change(self, tmp_path):
        # The local file mirrors the sheet, column order included; one rewrite
        # (archiving the old file) brings it back in line.
        file_header = ["criterion", "Element"]
        new_header = ["Element", "criterion"]
        records = [{"Element": "a", "criterion": "y"}]
        p = tmp_path / "data.tsv"
        _write_tsv_file(p, file_header, records)
        assert _tsv_content_changed(p, new_header, records) is True

    def test_a_column_removed_on_the_sheet_is_a_change(self, tmp_path):
        # Used to compare equal: the old file was lined up to the new header
        # first, dropping the removed column before the comparison.
        old_header = ["Element", "reflexive_allowed", "np_allowed"]
        new_header = ["Element", "reflexive_allowed"]
        p = tmp_path / "reflexive_coreference.tsv"
        _write_tsv_file(p, old_header, [{"Element": "a", "reflexive_allowed": "y", "np_allowed": ""}])
        assert _tsv_content_changed(p, new_header, [{"Element": "a", "reflexive_allowed": "y"}]) is True

    def test_header_only_tab_is_not_changed(self, tmp_path):
        # A tab with a header and no rows used to compare as changed every run
        # (string columns from disk vs float columns from an empty record list),
        # so synth0001's empty phrasal_accent tab was re-archived daily.
        header = ["Element_A", "Element_B", "joint_accent", "Source", "Comments"]
        p = tmp_path / "general.tsv"
        _write_tsv_file(p, header, [])
        assert _tsv_content_changed(p, header, []) is False


# ---------------------------------------------------------------------------
# Which constructions have pair rows is one fact, in one place (issue #275)
# ---------------------------------------------------------------------------

def test_import_sheets_reads_the_pair_row_list_from_the_schema():
    """It used to name the classes itself, and left phrasal_accent out.

    validate-coding has read this from schemas/diagnostic_classes.yaml since
    the row_type field was added, so the two commands disagreed about
    phrasal_accent/general: one treated it as pair rows, the other as element
    rows. Two places holding the same fact is the failure this project keeps
    repeating, so there is now only one.
    """
    import inspect

    import coding.import_sheets as _is
    from coding.restructure_sheets import _get_pair_row_constructions

    source = inspect.getsource(_is.main)
    assert "pair_row_constructions.get(class_name" in source, (
        "import-sheets no longer derives pair-row routing from the schema")
    assert 'class_name == "nonpermutability"' not in source, (
        "the hardcoded class list is back")

    # And the schema does list the one that was missing.
    assert "general" in _get_pair_row_constructions()["phrasal_accent"]
