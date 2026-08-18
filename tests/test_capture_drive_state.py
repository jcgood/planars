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

from coding.capture_drive_state import _capture_spreadsheet, _capture_worksheet
from fake_drive import FakeDriveDoorway


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
