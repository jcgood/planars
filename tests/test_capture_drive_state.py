"""Tests for coding/capture_drive_state.py.

No dedicated test file existed for this module before Phase 8 of the data
layer redesign (issue #271) turned up the gap while auditing every command's
idempotency claim in operations.yaml. This is the one command exempt from
the Drive doorway (its whole job is recording raw API responses, so going
through an abstraction would defeat the purpose -- see
tests/test_doorway_coverage.py's `_EXEMPT`), and the one live Drive call
permitted before Phase 9, so it can't be driven end-to-end through `main()`
offline the way every other command's tests are. What's testable without
live Drive is its pure capture logic (`_capture_worksheet`/
`_capture_spreadsheet`): given the same worksheet/spreadsheet content, do
two calls produce the same recorded shape? `FakeWorksheet`/`FakeSpreadsheet`
already implement the same interface (`.title`, `.id`, `.get_all_values()`,
etc.) real gspread handles do, so they stand in here exactly as they do for
every other command's tests.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
from contextlib import redirect_stdout

from coding import capture_drive_state as cds
from coding.capture_drive_state import _capture_spreadsheet, _capture_worksheet
from fake_drive import FIXTURE_DIR, MANIFEST_FILE_ID, FakeDriveDoorway


def _seeded_doorway() -> FakeDriveDoorway:
    doorway = FakeDriveDoorway.from_fixtures()
    doorway.seed_spreadsheet({
        "spreadsheet_id": "probe_sheet",
        "title": "probe_stan1293",
        "worksheets": [{
            "sheet_id": 0, "title": "general", "row_count": 5, "col_count": 3,
            "values": [["Element", "accented", "Comments"], ["and", "y", ""]],
        }],
    })
    return doorway


# ---------------------------------------------------------------------------
# Idempotency (Phase 8 of the data layer redesign, issue #271) --
# operations.yaml's own claim: "running it twice with nothing changed on
# Drive in between produces byte-identical per-spreadsheet fixture files."
# ---------------------------------------------------------------------------

def test_capturing_the_same_worksheet_twice_is_byte_identical():
    doorway = _seeded_doorway()
    ws = doorway.spreadsheet("probe_sheet").worksheet("general")

    first = _capture_worksheet(ws)
    second = _capture_worksheet(ws)

    assert second == first


def test_capturing_the_same_spreadsheet_twice_is_byte_identical():
    doorway = _seeded_doorway()

    class _GC:
        def open_by_key(self, spreadsheet_id):
            return doorway.spreadsheet(spreadsheet_id)

    first = _capture_spreadsheet(_GC(), "probe_sheet", role="stan1293:ciscategorial")
    second = _capture_spreadsheet(_GC(), "probe_sheet", role="stan1293:ciscategorial")

    assert second == first


# ---------------------------------------------------------------------------
# --apply refreezes both halves together (2026-10-10)
# ---------------------------------------------------------------------------

def test_apply_refreezes_sheets_and_local_folders_together(tmp_path, monkeypatch):
    """`--apply --lang stan1293` replaces stan1293's saved Sheets AND its frozen
    local folder, and leaves the other languages' saved Sheets in the index.
    Main() is driven against the stand-in Drive through a minimal `gc` shim."""
    doorway = FakeDriveDoorway.from_fixtures()
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)

    fixture_dir = tmp_path / "fx" / "drive_state"
    fixture_dir.mkdir(parents=True)
    shutil.copy(FIXTURE_DIR / "index.json", fixture_dir / "index.json")
    frozen = tmp_path / "fx" / "coded_data"
    (frozen / "stan1293").mkdir(parents=True)
    (frozen / "stan1293" / "stale.tsv").write_text("old\n", encoding="utf-8")
    live = tmp_path / "live"
    (live / "stan1293" / "lang_setup").mkdir(parents=True)
    (live / "stan1293" / "lang_setup" / "marker.tsv").write_text("new\n", encoding="utf-8")

    class _GC:
        def open_by_key(self, spreadsheet_id):
            return doorway.spreadsheet(spreadsheet_id)

    monkeypatch.setattr(cds, "FIXTURE_DIR", fixture_dir)
    monkeypatch.setattr(cds, "FROZEN_CODED_DATA", frozen)
    monkeypatch.setattr(cds, "CODED_DATA", live)
    monkeypatch.setattr(cds, "ROOT", tmp_path)
    monkeypatch.setattr(cds, "_get_clients", lambda: (_GC(), None))
    monkeypatch.setattr(cds, "_load_drive_config",
                        lambda: {"_planars_config_file_id": MANIFEST_FILE_ID})
    monkeypatch.setattr(cds, "_download_file_json", lambda drive, file_id: manifest)

    with redirect_stdout(io.StringIO()):
        cds.main(argparse.Namespace(apply=True, lang="stan1293"))

    index = json.loads((fixture_dir / "index.json").read_text(encoding="utf-8"))
    langs = {e["lang_id"] for e in index["spreadsheets"]}
    assert langs == {"arao1248", "stan1293", "synth0001"}
    for entry in index["spreadsheets"]:
        if entry["lang_id"] == "stan1293":
            assert (fixture_dir / entry["path"]).exists()
    assert (frozen / "stan1293" / "lang_setup" / "marker.tsv").exists()
    assert not (frozen / "stan1293" / "stale.tsv").exists()
