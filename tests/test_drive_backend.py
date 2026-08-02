"""Tests for the Drive/Sheets seam and its in-memory fake.

Two jobs:

1. **Replay fidelity.** The fake is only trustworthy if it reproduces the
   recorded live responses *exactly*. ``test_replay_*`` asserts that for all
   80 captured tabs, byte for byte — including the 10 whose used range is
   narrower than their declared grid. This is the empirical anchor the plan
   demands: the fake is built from recordings, not from the gspread docs, and
   this is what proves it stayed that way.

2. **Protocol smoke coverage.** Phase 0a is "done when a smoke test exercises
   every protocol operation against the fake", so every method on
   ``DriveBackend`` and both handle protocols is called at least once here.

See docs/data-layer-implementation-plan.md § "Phase 0a".
"""
from __future__ import annotations

import json

import gspread
import pytest

from coding import drive_backend
from coding.drive_backend import (
    DriveBackend,
    GspreadBackend,
    SpreadsheetHandle,
    WorksheetHandle,
)
from fake_drive import FIXTURE_DIR, ROOT, FakeDriveBackend, _parse_query


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def captured():
    """The raw capture index plus every recorded spreadsheet payload."""
    index = json.loads((FIXTURE_DIR / "index.json").read_text(encoding="utf-8"))
    return [
        json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
        for entry in index["spreadsheets"]
    ]


@pytest.fixture(scope="module")
def seeded():
    return FakeDriveBackend.from_fixtures()


@pytest.fixture()
def backend():
    """A small fake with one seeded folder, for write-path tests."""
    b = FakeDriveBackend()
    b.seed_folder("planars", file_id="folder_root")
    return b


# ---------------------------------------------------------------------------
# 1. Replay fidelity against the live capture
# ---------------------------------------------------------------------------

def test_capture_is_non_trivial(captured):
    """Guard against a silently-empty fixture set making every test below vacuous."""
    tabs = sum(len(ss["worksheets"]) for ss in captured)
    assert len(captured) >= 29 and tabs >= 80


def test_replay_get_all_values_matches_recording_exactly(captured, seeded):
    """Every tab replays byte-for-byte — the padding rule is the recorded one."""
    for ss_data in captured:
        ss = seeded.open_spreadsheet(ss_data["spreadsheet_id"])
        for tab in ss_data["worksheets"]:
            got = ss.worksheet(tab["title"]).get_all_values()
            assert got == tab["values"], f"{ss_data['role']}/{tab['title']}"


def test_replay_preserves_tab_order(captured, seeded):
    """worksheets() returns live UI order; sorting it would break drift detection."""
    for ss_data in captured:
        ss = seeded.open_spreadsheet(ss_data["spreadsheet_id"])
        assert [ws.title for ws in ss.worksheets()] == ss_data["tab_order"]


def test_replay_preserves_declared_grid_and_sheet_ids(captured, seeded):
    """Declared grid size is recorded separately from the used range — keep both."""
    for ss_data in captured:
        ss = seeded.open_spreadsheet(ss_data["spreadsheet_id"])
        for tab in ss_data["worksheets"]:
            ws = ss.worksheet(tab["title"])
            assert (ws.id, ws.row_count, ws.col_count) == (
                tab["sheet_id"], tab["row_count"], tab["col_count"])


def test_used_range_can_be_narrower_than_declared_grid(captured, seeded):
    """The real hazard the capture found — 10 of 80 tabs are narrower than col_count.

    The falsified hypothesis was raggedness; this is what actually bites. If
    the fake ever starts padding to col_count, this test fails and the
    ``len(row) >= N`` guards in generate_sheets.py stop being exercised.
    """
    narrower = 0
    for ss_data in captured:
        ss = seeded.open_spreadsheet(ss_data["spreadsheet_id"])
        for tab in ss_data["worksheets"]:
            ws = ss.worksheet(tab["title"])
            values = ws.get_all_values()
            width = max(len(r) for r in values)
            assert width <= ws.col_count
            narrower += width < ws.col_count
    assert narrower == 10


def test_replayed_rows_are_rectangular(seeded, captured):
    """No ragged responses exist in reality; the fake must not invent any."""
    for ss_data in captured:
        ss = seeded.open_spreadsheet(ss_data["spreadsheet_id"])
        for tab in ss_data["worksheets"]:
            values = ss.worksheet(tab["title"]).get_all_values()
            assert len({len(r) for r in values}) <= 1


# ---------------------------------------------------------------------------
# 2. Read semantics
# ---------------------------------------------------------------------------

def test_get_all_values_is_empty_list_for_empty_sheet(backend):
    ws = backend.create_spreadsheet("empty").sheet1
    assert ws.get_all_values() == []


def test_get_all_values_pads_to_used_range_not_to_grid(backend):
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["a", "b"], ["c"]], "A1")
    # Padded to the used width (2), not to the declared 26-column grid.
    assert ws.get_all_values() == [["a", "b"], ["c", ""]]


def test_formatting_a_blank_cell_does_not_extend_the_used_range(backend):
    ss = backend.create_spreadsheet("s")
    ws = ss.sheet1
    ws.update([["a"]], "A1")
    ss.batch_update({"requests": [{"repeatCell": {
        "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 5,
                  "startColumnIndex": 0, "endColumnIndex": 5},
        "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1.0}}},
        "fields": "userEnteredFormat.backgroundColor",
    }}]})
    assert ws.get_all_values() == [["a"]]


def test_row_values_is_one_based_and_trimmed(backend):
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["h1", "h2", ""], ["v1"]], "A1")
    assert ws.row_values(1) == ["h1", "h2"]
    assert ws.row_values(2) == ["v1"]
    assert ws.row_values(9) == []


# ---------------------------------------------------------------------------
# 3. Write semantics
# ---------------------------------------------------------------------------

def test_update_writes_only_its_own_range(backend):
    """update() is not "replace the sheet" — it writes the cells it covers."""
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["a", "b"], ["c", "d"]], "A1")
    ws.update([["X"]], "B1")
    assert ws.get_all_values() == [["a", "X"], ["c", "d"]]


def test_update_at_computed_anchor(backend):
    """sync_params.py:258 is the one call site writing at a non-A1 anchor."""
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["h"], ["1"], ["2"]], "D1")
    assert ws.get_all_values() == [
        ["", "", "", "h"], ["", "", "", "1"], ["", "", "", "2"]]


def test_raw_false_marks_formula_cells(backend):
    """raw=False changes what the write means (formula), not how it displays."""
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([['=HYPERLINK("u","t")'], ["plain"]], "A1", raw=False)
    assert ws._cells[(0, 0)].formula is True
    assert ws._cells[(1, 0)].formula is False
    # Deliberate fidelity limit: the fake does not evaluate formulas.
    assert ws.get_all_values()[0][0] == '=HYPERLINK("u","t")'


def test_mutation_is_visible_to_the_next_read_on_the_same_handle(backend):
    """update_sheets.py:391->393 re-reads its own write through one handle."""
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["a"]], "A1")
    assert ws.get_all_values() == [["a"]]
    ws.insert_cols([["new"]], col=1)
    assert ws.row_values(1) == ["new", "a"]


def test_insert_cols_is_one_based_and_shifts_right(backend):
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["A", "B", "C"], ["1", "2", "3"]], "A1")
    before = ws.col_count
    ws.insert_cols([["NEW", "x"]], col=2)
    assert ws.get_all_values() == [["A", "NEW", "B", "C"], ["1", "x", "2", "3"]]
    assert ws.col_count == before + 1


def test_update_cell_is_one_based_on_both_axes(backend):
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["a", "b"], ["c", "d"]], "A1")
    ws.update_cell(2, 1, "Z")
    assert ws.get_all_values() == [["a", "b"], ["Z", "d"]]


def test_append_rows_starts_after_the_last_used_row(backend):
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["h"], ["1"]], "A1")
    ws.append_rows([["2"], ["3"]], value_input_option="RAW")
    assert ws.get_all_values() == [["h"], ["1"], ["2"], ["3"]]


def test_clear_removes_values_but_keeps_formatting_and_grid(backend):
    """generate_sheets._reset_worksheet exists precisely because of this."""
    ss = backend.create_spreadsheet("s")
    ws = ss.sheet1
    ws.update([["a"]], "A1")
    ss.batch_update({"requests": [{"repeatCell": {
        "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                  "startColumnIndex": 0, "endColumnIndex": 1},
        "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1.0}}},
        "fields": "userEnteredFormat.backgroundColor",
    }}]})
    rows, cols = ws.row_count, ws.col_count
    ws.clear()
    assert ws.get_all_values() == []
    assert ws._cells[(0, 0)].background == {"red": 1.0}
    assert (ws.row_count, ws.col_count) == (rows, cols)


def test_resize_discards_out_of_bounds_cells(backend):
    ws = backend.create_spreadsheet("s").sheet1
    ws.update([["a", "b", "c"], ["d", "e", "f"]], "A1")
    ws.resize(rows=1, cols=2)
    assert ws.get_all_values() == [["a", "b"]]


def test_update_title_rejects_a_duplicate(backend):
    ss = backend.create_spreadsheet("s")
    ss.add_worksheet("Status", 5, 2)
    with pytest.raises(gspread.exceptions.APIError):
        ss.sheet1.update_title("Status")


def test_write_past_the_declared_grid_is_recorded(backend):
    """The live behaviour here was not captured, so the fake flags rather than guesses."""
    ws = backend.create_spreadsheet("s").sheet1
    ws.resize(rows=2, cols=2)
    ws.update([["a"], ["b"], ["c"]], "A1")
    assert backend.mutations_of("update")[-1]["exceeded_grid"] is True
    assert ws.row_count == 3


# ---------------------------------------------------------------------------
# 4. Tab lifecycle
# ---------------------------------------------------------------------------

def test_worksheet_lookup_raises_worksheet_not_found(backend):
    """The ~15 try/except WorksheetNotFound call sites must keep working."""
    ss = backend.create_spreadsheet("s")
    with pytest.raises(gspread.exceptions.WorksheetNotFound):
        ss.worksheet("nope")


def test_add_delete_and_reorder_worksheets(backend):
    ss = backend.create_spreadsheet("s")
    first = ss.sheet1
    a = ss.add_worksheet("a", 10, 3)
    b = ss.add_worksheet("b", 10, 3)
    assert [w.title for w in ss.worksheets()] == ["Sheet1", "a", "b"]
    ss.del_worksheet(first)
    ss.reorder_worksheets([b, a])
    assert [w.title for w in ss.worksheets()] == ["b", "a"]
    assert ss.sheet1.title == "b"


def test_reorder_rejects_an_incomplete_order(backend):
    ss = backend.create_spreadsheet("s")
    ss.add_worksheet("a", 5, 2)
    with pytest.raises(gspread.exceptions.APIError):
        ss.reorder_worksheets([ss.sheet1])


def test_created_spreadsheet_has_the_default_sheet1(backend):
    ss = backend.create_spreadsheet("new")
    assert [(w.title, w.id, w.row_count, w.col_count) for w in ss.worksheets()] == [
        ("Sheet1", 0, 1000, 26)]
    assert ss.url.endswith(ss.id)


# ---------------------------------------------------------------------------
# 5. The two batch endpoints — kept distinct on purpose
# ---------------------------------------------------------------------------

def test_batch_update_rejects_a_values_body(backend):
    ss = backend.create_spreadsheet("s")
    with pytest.raises(gspread.exceptions.APIError, match="values_batch_update"):
        ss.batch_update({"valueInputOption": "RAW", "data": [{"range": "A1", "values": [["x"]]}]})


def test_values_batch_update_rejects_a_requests_body(backend):
    ss = backend.create_spreadsheet("s")
    with pytest.raises(gspread.exceptions.APIError, match="batch_update"):
        ss.values_batch_update({"requests": []})


def test_values_batch_update_writes_ranges(backend):
    ss = backend.create_spreadsheet("s")
    ws = ss.sheet1
    ws.update([["a", "b"], ["c", "d"]], "A1")
    ss.values_batch_update({"valueInputOption": "RAW",
                            "data": [{"range": "B2", "values": [["Z"]]}]})
    assert ws.get_all_values() == [["a", "b"], ["c", "Z"]]


def test_unprefixed_values_range_resolves_against_the_first_sheet(backend):
    """Faithful reproduction of a live oddity, not a convenience.

    restructure_sheets._cascade_rename_pair_tab builds bare ranges like "D5"
    and sends them via ws.spreadsheet.values_batch_update. The Sheets values
    API resolves an unprefixed range against the FIRST sheet, so the write
    lands on sheet1 even when the caller was holding another tab. Recorded
    here so the behaviour is visible; not fixed (plan Phase 0b/1 non-goal:
    record current behaviour, including behaviour that looks wrong).
    """
    ss = backend.create_spreadsheet("s")
    other = ss.add_worksheet("pairs", 10, 4)
    ss.values_batch_update({"valueInputOption": "RAW",
                            "data": [{"range": "A1", "values": [["landed"]]}]})
    assert ss.sheet1.get_all_values() == [["landed"]]
    assert other.get_all_values() == []
    # With an explicit sheet prefix it goes where the caller meant.
    ss.values_batch_update({"valueInputOption": "RAW",
                            "data": [{"range": "'pairs'!A1", "values": [["here"]]}]})
    assert other.get_all_values() == [["here"]]


def test_unknown_batch_request_type_raises(backend):
    """An unmodelled request must never pass silently — a snapshot would enshrine it."""
    ss = backend.create_spreadsheet("s")
    with pytest.raises(NotImplementedError, match="autoResizeDimensions"):
        ss.batch_update({"requests": [{"autoResizeDimensions": {}}]})


@pytest.mark.parametrize("request_type", [
    "updateSheetProperties", "repeatCell", "setDataValidation", "insertDimension",
    "deleteDimension", "updateDimensionProperties", "updateCells", "mergeCells",
])
def test_every_request_type_used_by_coding_is_modelled(request_type):
    """The eight request types the eleven caller files actually send."""
    from fake_drive import FakeSpreadsheet
    assert hasattr(FakeSpreadsheet, f"_req_{request_type}")


def test_structural_requests_move_data(backend):
    ss = backend.create_spreadsheet("s")
    ws = ss.sheet1
    ws.update([["A", "B", "C"], ["1", "2", "3"]], "A1")
    ss.batch_update({"requests": [{"insertDimension": {"range": {
        "sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
        "inheritFromBefore": False}}]})
    assert ws.get_all_values() == [["A", "", "B", "C"], ["1", "", "2", "3"]]
    ss.batch_update({"requests": [{"deleteDimension": {"range": {
        "sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}}}]})
    assert ws.get_all_values() == [["A", "B", "C"], ["1", "2", "3"]]


def test_delete_dimension_right_to_left_matches_sync_params(backend):
    """sync_params deletes columns right-to-left so earlier deletes don't shift later ones."""
    ss = backend.create_spreadsheet("s")
    ws = ss.sheet1
    ws.update([["A", "B", "C", "D"]], "A1")
    for idx in sorted([1, 2], reverse=True):
        ss.batch_update({"requests": [{"deleteDimension": {"range": {
            "sheetId": ws.id, "dimension": "COLUMNS",
            "startIndex": idx, "endIndex": idx + 1}}}]})
    assert ws.get_all_values() == [["A", "D"]]


def test_update_cells_paints_scattered_cells(backend):
    """validate_coding's pink highlighting: one updateCells request per bad cell."""
    ss = backend.create_spreadsheet("s")
    ws = ss.sheet1
    ws.update([["a", "b"], ["c", "d"]], "A1")
    pink = {"red": 1.0, "green": 0.8, "blue": 0.8}
    ss.batch_update({"requests": [
        {"updateCells": {
            "range": {"sheetId": ws.id, "startRowIndex": r, "endRowIndex": r + 1,
                      "startColumnIndex": c, "endColumnIndex": c + 1},
            "rows": [{"values": [{"userEnteredFormat": {"backgroundColor": pink}}]}],
            "fields": "userEnteredFormat.backgroundColor",
        }} for r, c in [(0, 1), (1, 0)]
    ]})
    assert ws._cells[(0, 1)].background == pink
    assert ws._cells[(1, 0)].background == pink
    assert ws._cells[(0, 0)].background is None
    # Values untouched by a format-only write.
    assert ws.get_all_values() == [["a", "b"], ["c", "d"]]


def test_merge_and_dimension_properties_are_recorded(backend):
    ss = backend.create_spreadsheet("s")
    ws = ss.sheet1
    ss.batch_update({"requests": [
        {"mergeCells": {"range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                                  "startColumnIndex": 0, "endColumnIndex": 3},
                        "mergeType": "MERGE_ALL"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": ws.id, "dimension": "COLUMNS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 220}, "fields": "pixelSize"}},
        {"updateSheetProperties": {
            "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount"}},
    ]})
    assert ws.merges == [{"startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": 3,
                          "mergeType": "MERGE_ALL"}]
    assert ws.dimension_pixel_sizes[("COLUMNS", 0)] == 220
    assert ws.frozen_rows == 1


def test_real_format_and_validate_helper_runs_against_the_fake():
    """The seam is drop-in for helpers shared with not-yet-migrated files.

    generate_sheets._format_and_validate is called by four of the eleven
    callers and takes a worksheet directly. It must work unchanged whether
    handed a real gspread.Worksheet or a fake one — that is the whole reason
    the handle protocols mirror gspread's method names.
    """
    from coding.generate_sheets import _format_and_validate

    backend = FakeDriveBackend()
    ss = backend.create_spreadsheet("s")
    ws = ss.sheet1
    ws.update([["Element", "Position_Name", "Position_Number", "accented"]], "A1")
    _format_and_validate(ws, num_data_rows=2, param_values=[["y", "n", "both"]],
                         col_start=3, param_notes=["whether it bears accent"])
    assert ws.frozen_rows == 1
    assert ws._cells[(0, 0)].bold is True
    assert ws._cells[(0, 3)].note == "whether it bears accent"
    rule = ws._cells[(1, 3)].validation
    assert [v["userEnteredValue"] for v in rule["condition"]["values"]] == ["y", "n", "both"]
    assert (3, 3) not in ws._cells  # only num_data_rows rows carry validation


# ---------------------------------------------------------------------------
# 6. Drive files, permissions, docs
# ---------------------------------------------------------------------------

def test_get_or_create_folder_is_idempotent(backend):
    first = backend.get_or_create_folder("lang_stan1293", "folder_root")
    second = backend.get_or_create_folder("lang_stan1293", "folder_root")
    assert first == second
    # A same-named folder under a different parent is a different folder.
    other_parent = backend.seed_folder("elsewhere")
    assert backend.get_or_create_folder("lang_stan1293", other_parent) != first


def test_list_files_filters_on_every_clause(backend):
    folder = backend.get_or_create_folder("nested", "folder_root")
    backend.create_spreadsheet("metrical_stan1293")
    ss_id = backend.list_files("name='metrical_stan1293' and trashed=false")[0]["id"]
    backend.move_file(ss_id, folder)
    q = (f"name='metrical_stan1293' and '{folder}' in parents"
         " and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false")
    assert [f["id"] for f in backend.list_files(q, fields="files(id)")] == [ss_id]
    assert backend.list_files(q.replace(folder, "folder_root")) == []


def test_list_files_page_size(backend):
    for i in range(3):
        backend.seed_file(f"n{i}", "text/plain", ["folder_root"])
    assert len(backend.list_files("'folder_root' in parents", page_size=2)) == 2


def test_unparseable_query_raises_rather_than_matching_nothing(backend):
    with pytest.raises(NotImplementedError, match="fullText"):
        backend.list_files("fullText contains 'planar'")


def test_parse_query_handles_every_shape_built_by_coding():
    parsed = _parse_query(
        "name='x' and 'PARENT' in parents "
        "and mimeType='application/vnd.google-apps.folder' and trashed=false")
    assert parsed == {"name": "x", "parent": "PARENT",
                      "mimeType": "application/vnd.google-apps.folder",
                      "trashed": "false"}


def test_file_create_update_move_and_download(backend):
    file_id = backend.create_file("manifest.json", ["folder_root"],
                                  content=json.dumps({"a": 1}).encode(),
                                  mimetype="application/json")
    assert backend.download_file_json(file_id) == {"a": 1}
    backend.update_file(file_id, content=json.dumps({"a": 2}).encode())
    assert backend.download_file_json(file_id) == {"a": 2}
    # Rename independent of content — the four upload implementations disagree
    # on whether an update renames, so the seam lets each caller choose.
    backend.update_file(file_id, name="renamed.json")
    assert backend.get_file(file_id, fields="name")["name"] == "renamed.json"
    other = backend.seed_folder("_archived")
    backend.move_file(file_id, other)
    assert backend.get_file(file_id, fields="parents")["parents"] == [other]


def test_missing_file_raises_a_not_found_api_error(backend):
    with pytest.raises(gspread.exceptions.APIError) as exc:
        backend.get_file("nope")
    assert exc.value.response.status_code == 404


def test_open_missing_spreadsheet_raises_spreadsheet_not_found(backend):
    with pytest.raises(gspread.exceptions.SpreadsheetNotFound):
        backend.open_spreadsheet("nope")


def test_permission_grant_list_and_revoke(backend):
    file_id = backend.seed_file("sheet", "application/vnd.google-apps.spreadsheet")
    anyone = backend.create_permission(file_id, type="anyone", role="writer")
    backend.create_permission(file_id, type="user", role="reader",
                              email="a@example.com", notify=False)
    perms = backend.list_permissions(file_id, fields="permissions(id,type)")
    assert {p["type"] for p in perms} == {"anyone", "user"}
    backend.delete_permission(file_id, anyone)
    assert [p["type"] for p in backend.list_permissions(file_id)] == ["user"]


def test_docs_create_read_append(backend):
    doc_id = backend.create_doc("Notes", "folder_root")
    assert backend.get_doc_text(doc_id) == ""
    backend.append_doc_text(doc_id, "[2026-08-01] Notes transferred to coordinator")
    assert "transferred" in backend.get_doc_text(doc_id)


def test_seeded_doc_text_is_readable(backend):
    doc_id = backend.seed_doc("Notes", "collaborator wrote this", parent_id="folder_root")
    assert backend.get_doc_text(doc_id) == "collaborator wrote this"


# ---------------------------------------------------------------------------
# 7. Mutation log and protocol conformance
# ---------------------------------------------------------------------------

def test_mutation_log_is_ordered_and_json_serialisable(backend):
    ss = backend.create_spreadsheet("s")
    ws = ss.add_worksheet("tab", 5, 3)
    ws.update([["a"]], "A1")
    ws.append_rows([["b"]])
    ss.batch_update({"requests": [{"updateSheetProperties": {
        "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount"}}]})
    assert [m["op"] for m in backend.mutations] == [
        "create_spreadsheet", "add_worksheet", "update", "append_rows", "batch_request"]
    json.dumps(backend.mutations)  # snapshots serialise this log verbatim


def test_reads_do_not_appear_in_the_mutation_log(seeded):
    seeded.clear_mutations()
    ss = seeded.open_spreadsheet(
        next(iter(seeded._spreadsheets)))
    ss.worksheets()[0].get_all_values()
    ss.worksheets()[0].row_values(1)
    assert seeded.mutations == []


@pytest.mark.parametrize("implementation", [GspreadBackend, FakeDriveBackend])
def test_both_backends_implement_every_protocol_method(implementation):
    expected = [m for m in vars(DriveBackend) if not m.startswith("_")]
    missing = [m for m in expected if not hasattr(implementation, m)]
    assert not missing, f"{implementation.__name__} is missing {missing}"


def test_fake_handles_satisfy_the_handle_protocols(backend):
    ss = backend.create_spreadsheet("s")
    assert isinstance(ss, SpreadsheetHandle)
    assert isinstance(ss.sheet1, WorksheetHandle)


def test_real_gspread_objects_satisfy_the_handle_protocols():
    """The protocols mirror gspread, so migration is substitution, not rewrite."""
    assert isinstance(gspread.Spreadsheet, type)
    for name in ("get_all_values", "row_values", "update", "update_cell",
                 "insert_cols", "append_rows", "clear", "resize", "update_title"):
        assert hasattr(gspread.Worksheet, name)
    for name in ("worksheets", "worksheet", "add_worksheet", "del_worksheet",
                 "reorder_worksheets", "batch_update", "values_batch_update", "sheet1"):
        assert hasattr(gspread.Spreadsheet, name)


def test_get_backend_defaults_to_the_real_one_and_can_be_overridden():
    drive_backend.reset_backend()
    assert isinstance(drive_backend.get_backend(), GspreadBackend)
    fake = FakeDriveBackend()
    drive_backend.set_backend(fake)
    try:
        assert drive_backend.get_backend() is fake
    finally:
        drive_backend.reset_backend()


def test_constructing_the_real_backend_performs_no_auth(monkeypatch):
    """Clients are lazy: building a backend must not trigger an OAuth flow."""
    def explode(*a, **k):  # pragma: no cover - fails the test if reached
        raise AssertionError("_get_clients() must not be called at construction")

    monkeypatch.setattr(drive_backend, "_get_clients", explode)
    GspreadBackend()
