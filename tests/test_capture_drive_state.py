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


_TAB_LABELS = [
    {"metadataId": 1, "metadataKey": "planars_tab_kind", "metadataValue": "construction",
     "location": {"sheetId": 0, "locationType": "SHEET"}, "visibility": "DOCUMENT"},
    {"metadataId": 2, "metadataKey": "planars_tab", "metadataValue": "general",
     "location": {"sheetId": 0, "locationType": "SHEET"}, "visibility": "DOCUMENT"},
]
_SHEET_LABELS = {"planars_kind": "class_sheet", "planars_lang": "stan1293",
                 "planars_class": "metrical"}


def _seeded_doorway() -> FakeDriveDoorway:
    doorway = FakeDriveDoorway.from_fixtures()
    doorway.seed_spreadsheet({
        "spreadsheet_id": "probe_sheet",
        "title": "probe_stan1293",
        "properties": _SHEET_LABELS,
        "worksheets": [{
            "sheet_id": 0, "title": "general", "row_count": 5, "col_count": 3,
            "values": [["Element", "accented", "Comments"], ["and", "y", ""]],
            "developer_metadata": _TAB_LABELS,
        }],
        "permissions": _GRANTS,
    })
    return doorway


# Recorded by name, never address; one person people.yaml doesn't know.
_GRANTS = [
    {"id": "g1", "type": "user", "role": "writer", "person": "Adam Tallman"},
    {"id": "g2", "type": "user", "role": "reader", "person": None},
    {"id": "g3", "type": "anyone", "role": "reader"},
]


class _DriveV3:
    """The two Drive v3 calls capture makes (``files().get(...)`` and
    ``permissions().list(...)``, each ``.execute()``d), answered from the
    stand-in Drive."""

    def __init__(self, doorway: FakeDriveDoorway) -> None:
        self._doorway = doorway

    def files(self):
        return _Files(self._doorway)

    def permissions(self):
        return _Permissions(self._doorway)


def _request(result):
    return type("_Request", (), {"execute": lambda _self: result})()


class _Files:
    def __init__(self, doorway: FakeDriveDoorway) -> None:
        self._doorway = doorway

    def get(self, fileId, fields):
        return _request(self._doorway.get_file(fileId, fields=fields))


class _Permissions:
    def __init__(self, doorway: FakeDriveDoorway) -> None:
        self._doorway = doorway

    def list(self, fileId, fields):
        return _request({"permissions": self._doorway.list_permissions(fileId, fields=fields)})


# ---------------------------------------------------------------------------
# Idempotency (Phase 8 of the data layer redesign, issue #271) --
# operations.yaml's own claim: "running it twice with nothing changed on
# Drive in between produces byte-identical per-spreadsheet fixture files."
# ---------------------------------------------------------------------------

def test_capturing_the_same_worksheet_twice_is_byte_identical():
    doorway = _seeded_doorway()
    ws = doorway.spreadsheet("probe_sheet").worksheet("general")

    first = _capture_worksheet(ws, _TAB_LABELS)
    second = _capture_worksheet(ws, _TAB_LABELS)

    assert second == first


class _GCFor:
    def __init__(self, doorway):
        self._doorway = doorway

    def open_by_key(self, spreadsheet_id):
        return self._doorway.spreadsheet(spreadsheet_id)


def test_capturing_the_same_spreadsheet_twice_is_byte_identical():
    doorway = _seeded_doorway()
    gc, drive = _GCFor(doorway), _DriveV3(doorway)

    first = _capture_spreadsheet(gc, drive, "probe_sheet", role="stan1293:ciscategorial")
    second = _capture_spreadsheet(gc, drive, "probe_sheet", role="stan1293:ciscategorial")

    assert second == first


def test_capture_records_the_labels_and_the_fake_replays_them():
    """The sheet's identity label, its tabs' labels and its grants are
    recorded, and a recording seeded into the stand-in Drive is captured back
    unchanged, so the door in tests places recorded sheets by label, and
    finds them shared, as it does live. A tab's labels are recorded sorted
    by key, so a refreeze doesn't show them as changed when Google returns
    them in another order."""
    doorway = _seeded_doorway()
    data = _capture_spreadsheet(_GCFor(doorway), _DriveV3(doorway), "probe_sheet",
                                role="stan1293:class:metrical")
    assert data["properties"] == _SHEET_LABELS
    assert data["worksheets"][0]["developer_metadata"] == [_TAB_LABELS[1], _TAB_LABELS[0]]
    assert data["permissions"] == _GRANTS
    assert "@" not in json.dumps(data["permissions"])

    replayed = FakeDriveDoorway.from_fixtures()
    replayed.seed_spreadsheet(data)
    again = _capture_spreadsheet(_GCFor(replayed), _DriveV3(replayed), "probe_sheet",
                                 role="stan1293:class:metrical")
    assert again == data


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

    monkeypatch.setattr(cds, "FIXTURE_DIR", fixture_dir)
    monkeypatch.setattr(cds, "FROZEN_CODED_DATA", frozen)
    monkeypatch.setattr(cds, "CODED_DATA", live)
    monkeypatch.setattr(cds, "ROOT", tmp_path)
    monkeypatch.setattr(cds, "_get_clients", lambda: (_GCFor(doorway), _DriveV3(doorway)))
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
