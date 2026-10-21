"""Tests for coding/restructure_journal.py (Phase 7 of the data layer
redesign, issue #271 -- restructure-sheets crash recovery).

The journal is state_files.JOURNAL_PATH, which tests/conftest.py points at
each test's tmp_path. It is written through the local-file door, so the
writing tests run inside restructure-sheets (`_running`), as the command
does.
"""
from __future__ import annotations

import pytest

from coding import drive_door, state_files
from coding import restructure_journal as rj


@pytest.fixture()
def _running():
    with drive_door.running("restructure-sheets", may_write=True):
        yield


# ---------------------------------------------------------------------------
# load_journal / record_checkpoint / clear_unit: basic read/write behaviour
# ---------------------------------------------------------------------------

def test_load_journal_missing_file_is_empty():
    assert rj.load_journal() == {}


def test_record_checkpoint_then_load_round_trips(_running):
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED,
                          archived_spreadsheet_id="abc123", folder_id="folder1")
    journal = rj.load_journal()
    assert set(journal) == {"stan1293:ciscategorial"}
    entry = journal["stan1293:ciscategorial"]
    assert entry["lang_id"] == "stan1293"
    assert entry["class_name"] == "ciscategorial"
    assert entry["checkpoint"] == rj.OLD_SHEET_ARCHIVED
    assert entry["detail"] == {"archived_spreadsheet_id": "abc123", "folder_id": "folder1"}


def test_record_checkpoint_overwrites_same_unit(_running):
    """A unit's second checkpoint replaces its first -- one entry per unit,
    not a history of every checkpoint it ever passed through."""
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED)
    rj.record_checkpoint("stan1293", "ciscategorial", rj.NEW_SHEET_CREATED,
                          spreadsheet_id="new1")
    journal = rj.load_journal()
    assert len(journal) == 1
    assert journal["stan1293:ciscategorial"]["checkpoint"] == rj.NEW_SHEET_CREATED


def test_record_checkpoint_tracks_multiple_units_independently(_running):
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED)
    rj.record_checkpoint("arao1248", "noninterruption", rj.NEW_SHEET_CREATED)
    journal = rj.load_journal()
    assert set(journal) == {"stan1293:ciscategorial", "arao1248:noninterruption"}


def test_clear_unit_removes_only_that_unit(_running):
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED)
    rj.record_checkpoint("arao1248", "noninterruption", rj.NEW_SHEET_CREATED)
    rj.clear_unit("stan1293", "ciscategorial")
    journal = rj.load_journal()
    assert set(journal) == {"arao1248:noninterruption"}


def test_clear_unit_last_entry_removes_the_file(_running):
    """The journal file itself should not exist once every unit is clear --
    'file exists' is the signal a run checks, not 'file exists and is {}'."""
    rj.record_checkpoint("stan1293", "ciscategorial", rj.OLD_SHEET_ARCHIVED)
    rj.clear_unit("stan1293", "ciscategorial")
    assert not state_files.JOURNAL_PATH.exists()


def test_clear_unit_on_untracked_unit_is_a_no_op(_running):
    rj.clear_unit("stan1293", "ciscategorial")  # must not raise
    assert rj.load_journal() == {}


# ---------------------------------------------------------------------------
# is_rollback_safe: only OLD_SHEET_ARCHIVED with nothing later
# ---------------------------------------------------------------------------

def test_is_rollback_safe_true_for_old_sheet_archived():
    entry = {"checkpoint": rj.OLD_SHEET_ARCHIVED}
    assert rj.is_rollback_safe(entry) is True


def test_is_rollback_safe_false_for_new_sheet_created():
    entry = {"checkpoint": rj.NEW_SHEET_CREATED}
    assert rj.is_rollback_safe(entry) is False


# ---------------------------------------------------------------------------
# format_incomplete_report: names the unit, the checkpoint, and the fix
# ---------------------------------------------------------------------------

def test_format_incomplete_report_old_sheet_archived_mentions_rollback_and_resume():
    journal = {
        "stan1293:ciscategorial": {
            "lang_id": "stan1293", "class_name": "ciscategorial",
            "checkpoint": rj.OLD_SHEET_ARCHIVED, "detail": {},
        },
    }
    report = rj.format_incomplete_report(journal)
    assert "stan1293" in report
    assert "ciscategorial" in report
    assert "--rollback" in report
    assert "--resume" in report


def test_format_incomplete_report_new_sheet_created_mentions_resume_only():
    journal = {
        "stan1293:ciscategorial": {
            "lang_id": "stan1293", "class_name": "ciscategorial",
            "checkpoint": rj.NEW_SHEET_CREATED, "detail": {},
        },
    }
    report = rj.format_incomplete_report(journal)
    assert "--resume" in report
    assert "rollback isn't offered" in report


def test_format_incomplete_report_lists_every_stuck_unit():
    journal = {
        "stan1293:ciscategorial": {
            "lang_id": "stan1293", "class_name": "ciscategorial",
            "checkpoint": rj.OLD_SHEET_ARCHIVED, "detail": {},
        },
        "arao1248:noninterruption": {
            "lang_id": "arao1248", "class_name": "noninterruption",
            "checkpoint": rj.NEW_SHEET_CREATED, "detail": {},
        },
    }
    report = rj.format_incomplete_report(journal)
    assert "stan1293" in report and "ciscategorial" in report
    assert "arao1248" in report and "noninterruption" in report
