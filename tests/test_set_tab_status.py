"""set-tab-status against the offline Drive and the frozen data."""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive_doorway
from coding import set_tab_status as sts
from command_runner import run_command
from fake_drive import MANIFEST_FILE_ID, FakeDriveDoorway, use_frozen_coded_data
from coding.validate_coding import marked_by_text
from planars.schema_values import (
    MARKED_BY_ANNOTATOR, MARKED_BY_COORDINATOR, STATUS_CONSTRUCTION_COLUMN,
    STATUS_IN_PROGRESS, STATUS_MARKED_BY_COLUMN, STATUS_READY, STATUS_STATUS_COLUMN,
    STATUS_TAB,
)

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(not (ROOT / "coded_data").exists(),
                                reason="coded_data/ (planars-data) is not checked out")

LANG, CLS, TAB = "stan1293", "phrasal_accent", "prescreening"
ARGS = ["--lang", LANG, "--class", CLS, "--construction", TAB]


def _status_ws(doorway):
    info = doorway.download_file_json(MANIFEST_FILE_ID)[LANG]["sheets"][CLS]
    return doorway.spreadsheet(info["spreadsheet_id"]).worksheet(STATUS_TAB)


def _cell(doorway, column: str) -> str:
    rows = _status_ws(doorway).get_all_values()
    ci, xi = rows[0].index(STATUS_CONSTRUCTION_COLUMN), rows[0].index(column)
    return next(r[xi] if xi < len(r) else "" for r in rows[1:] if r[ci] == TAB)


def _status(doorway) -> str:
    return _cell(doorway, STATUS_STATUS_COLUMN)


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()
    use_frozen_coded_data(monkeypatch, tmp_path)
    monkeypatch.setattr(sys.modules["coding.drive"], "_load_drive_config",
                        FakeDriveDoorway.drive_config)
    drive_doorway.set_doorway(doorway)
    # Start from what the annotator left: the tab still in progress.
    ws = _status_ws(doorway)
    rows = ws.get_all_values()
    ci, si = rows[0].index(STATUS_CONSTRUCTION_COLUMN), rows[0].index(STATUS_STATUS_COLUMN)
    r = next(i for i, row in enumerate(rows[1:], start=2) if row[ci] == TAB)
    ws.update([[STATUS_IN_PROGRESS]], f"{chr(ord('A') + si)}{r}")

    def run(*argv: str) -> str:
        monkeypatch.setattr(sys, "argv", ["set-tab-status", *argv])
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_command(sts, "set-tab-status")
        return buf.getvalue()

    try:
        yield doorway, run
    finally:
        drive_doorway.set_doorway(None)


def test_a_dry_run_changes_nothing(env):
    doorway, run = env
    out = run(*ARGS)
    assert f"{STATUS_IN_PROGRESS} -> {STATUS_READY}" in out
    assert _status(doorway) == STATUS_IN_PROGRESS


def test_apply_marks_it_ready_and_names_the_tab_waiting_on_it(env):
    doorway, run = env
    out = run(*ARGS, "--apply")
    assert _status(doorway) == STATUS_READY
    assert _cell(doorway, STATUS_MARKED_BY_COLUMN) == marked_by_text(MARKED_BY_COORDINATOR)
    assert "general is built from it" in out
    assert "already" in run(*ARGS, "--apply")


def test_a_tab_the_annotator_marked_is_re_marked_as_the_coordinators(env):
    doorway, run = env
    run(*ARGS, "--status", STATUS_READY, "--apply")
    ws = _status_ws(doorway)
    rows = ws.get_all_values()
    ci, mi = rows[0].index(STATUS_CONSTRUCTION_COLUMN), rows[0].index(STATUS_MARKED_BY_COLUMN)
    r = next(i for i, row in enumerate(rows[1:], start=2) if row[ci] == TAB)
    ws.update([[marked_by_text(MARKED_BY_ANNOTATOR)]], f"{chr(ord('A') + mi)}{r}")
    out = run(*ARGS, "--apply")
    assert f"-> {MARKED_BY_COORDINATOR}" in out
    assert _cell(doorway, STATUS_MARKED_BY_COLUMN) == marked_by_text(MARKED_BY_COORDINATOR)


def test_setting_it_back_clears_marked_by(env):
    doorway, run = env
    run(*ARGS, "--apply")
    run(*ARGS, "--status", STATUS_IN_PROGRESS, "--apply")
    assert _cell(doorway, STATUS_MARKED_BY_COLUMN) == ""


def test_an_unknown_tab_says_which_tabs_there_are(env):
    _, run = env
    with pytest.raises(SystemExit) as e:
        run("--lang", LANG, "--class", CLS, "--construction", "nosuch")
    assert "prescreening" in str(e.value)
