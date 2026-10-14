"""The Drive door's rules, one at a time (coding/drive_door.py).

Each test runs one write against the recorded English ciscategorial sheet
(Instructions, general, Status) through the door, in enforce mode unless the
test is about watch mode, and checks the door refused or allowed it.
"""
from __future__ import annotations

import argparse
import json

import pytest

from coding import drive as drive_module
from coding import drive_door, drive_doorway
from coding.drive_door import CheckedDoorway, DoorViolation
from coding.sheet_spec import class_sheet_spec
from fake_drive import FakeDriveDoorway, api_error, use_frozen_coded_data

LANG, CLASS = "stan1293", "ciscategorial"
APPLY = argparse.Namespace(apply=True)
DRY = argparse.Namespace(apply=False)


@pytest.fixture()
def env(monkeypatch, tmp_path):
    fake = FakeDriveDoorway.from_fixtures(langs=[LANG])
    coded = use_frozen_coded_data(monkeypatch, tmp_path)
    monkeypatch.setattr(drive_module, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr("coding.drive_door.time.sleep", lambda *a, **kw: None)
    drive_doorway.set_doorway(fake)
    door = drive_doorway.get_doorway()
    sheet_id = drive_module.load_manifest(door)[LANG]["sheets"][CLASS]["spreadsheet_id"]
    try:
        yield fake, door, sheet_id, coded
    finally:
        drive_doorway.reset_doorway()


def _tab(door, sheet_id, title):
    return door.open_spreadsheet(sheet_id).worksheet(title)


def _col(ws, name):
    return ws.get_all_values()[0].index(name)


# -- may this command write at all --------------------------------------------

def test_a_write_with_no_command_running_is_refused(env):
    _, door, sheet_id, _ = env
    ws = _tab(door, sheet_id, "general")
    with pytest.raises(DoorViolation, match="no command is running"):
        ws.update_cell(2, 1, "also")


def test_a_dry_run_cannot_write(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", DRY):
        ws = _tab(door, sheet_id, "general")
        with pytest.raises(DoorViolation, match="dry run"):
            ws.update_cell(2, 1, "also")


def test_an_always_made_write_is_allowed_on_a_dry_run_only_where_declared(env):
    _, door, sheet_id, _ = env
    paint = {"requests": [{"repeatCell": {
        "range": {"sheetId": 0}, "cell": {}, "fields": "userEnteredFormat.backgroundColor"}}]}
    with drive_door.running("import-sheets", DRY):
        ss = door.open_spreadsheet(sheet_id)
        paint["requests"][0]["repeatCell"]["range"]["sheetId"] = ss.worksheet("general").id
        with drive_door.always_on("highlighting"):
            ss.batch_update(paint)                      # declared for import-sheets
        with pytest.raises(DoorViolation):
            ss.batch_update(paint)                      # outside the block
    with drive_door.running("update-sheets", DRY):
        with drive_door.always_on("highlighting"), pytest.raises(DoorViolation):
            door.open_spreadsheet(sheet_id).batch_update(paint)  # not declared there


# -- only writes the door understands --------------------------------------------

def test_an_unknown_request_type_is_refused(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ss = door.open_spreadsheet(sheet_id)
        with pytest.raises(DoorViolation, match="does not know the 'deleteSheet'"):
            ss.batch_update({"requests": [{"deleteSheet": {"sheetId": 0}}]})


def test_a_handle_has_only_the_methods_the_door_checks(env):
    _, door, sheet_id, _ = env
    ws = _tab(door, sheet_id, "general")
    with pytest.raises(AttributeError):
        ws.batch_clear(["A1:B2"])     # a real gspread method, deliberately absent


# -- rule 1: annotations are never lost silently ---------------------------------

def test_changing_a_filled_answer_is_refused(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        c = _col(ws, "V-combines")
        with pytest.raises(DoorViolation, match="filled annotation"):
            ws.update_cell(2, c + 1, "n" if ws.get_all_values()[1][c] != "n" else "y")


def test_filling_an_empty_answer_and_rewriting_the_same_one_are_allowed(env):
    fake, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        c = _col(ws, "Comments")
        rows = ws.get_all_values()
        empty = next(i for i, r in enumerate(rows) if i and r[c] == "")
        ws.update_cell(empty + 1, c + 1, "a note")
        ws.update(ws.get_all_values(), "A1")          # unchanged content
        with pytest.raises(DoorViolation):
            ws.update(rows, "A1")                     # read before the note: blanks it
    assert fake.spreadsheet(sheet_id).worksheet("general").get_all_values()[empty][c] == "a note"


def test_the_tooling_may_change_its_own_columns(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        ws.update_cell(2, _col(ws, "Element") + 1, "renamed")


def test_clearing_or_cutting_an_annotated_tab_is_refused(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ss = door.open_spreadsheet(sheet_id)
        ws = ss.worksheet("general")
        with pytest.raises(DoorViolation, match="would clear"):
            ws.clear()
        c = _col(ws, "V-combines")
        with pytest.raises(DoorViolation, match="would delete columns"):
            ss.batch_update({"requests": [{"deleteDimension": {"range": {
                "sheetId": ws.id, "dimension": "COLUMNS",
                "startIndex": c, "endIndex": c + 1}}}]})
        with pytest.raises(DoorViolation, match="would delete the tab"):
            ss.del_worksheet(ws)


def test_replacing_says_the_loss_is_meant(env):
    fake, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        with drive_door.replacing(ws, "a test that means it"):
            ws.clear()
        with pytest.raises(DoorViolation):           # only that tab, only in the block
            _tab(door, sheet_id, "Status").clear()
    assert fake.spreadsheet(sheet_id).worksheet("general").get_all_values() == []


# -- rule 2: locked tabs hold their builder's content -----------------------------

def test_a_locked_tab_takes_only_its_builders_content(env):
    _, door, sheet_id, coded = env
    built = class_sheet_spec(LANG, CLASS, coded).tab("Instructions").rows
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "Instructions")
        ws.update([list(built[0])], "A1")
        with pytest.raises(DoorViolation, match="locked tab"):
            ws.update([["something else"]], "A1")


# -- rule 3: dropdowns match the spec ----------------------------------------------

def _dropdown(ws, col, values):
    return {"requests": [{"setDataValidation": {
        "range": {"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": 5,
                  "startColumnIndex": col, "endColumnIndex": col + 1},
        "rule": {"condition": {"type": "ONE_OF_LIST",
                               "values": [{"userEnteredValue": v} for v in values]}}}}]}


def test_dropdowns_only_on_criterion_columns_with_the_spec_values(env):
    _, door, sheet_id, coded = env
    allowed = class_sheet_spec(LANG, CLASS, coded).tab("general").column("V-combines").allowed
    with drive_door.running("update-sheets", APPLY):
        ss = door.open_spreadsheet(sheet_id)
        ws = ss.worksheet("general")
        ss.batch_update(_dropdown(ws, _col(ws, "V-combines"), allowed))
        with pytest.raises(DoorViolation, match="allows"):
            ss.batch_update(_dropdown(ws, _col(ws, "V-combines"), ["y", "n"]
                                      if list(allowed) != ["y", "n"] else ["y"]))
        with pytest.raises(DoorViolation, match="not a criterion column"):
            ss.batch_update(_dropdown(ws, _col(ws, "Comments"), allowed))


# -- rule 4: protection only on locked tabs -----------------------------------------

def test_only_locked_tabs_are_protected(env):
    _, door, sheet_id, _ = env

    def protect(ws):
        return {"requests": [{"addProtectedRange": {"protectedRange": {
            "range": {"sheetId": ws.id}, "warningOnly": False}}}]}

    with drive_door.running("update-sheets", APPLY):
        ss = door.open_spreadsheet(sheet_id)
        ss.batch_update(protect(ss.worksheet("Instructions")))
        with pytest.raises(DoorViolation, match="only locked tabs"):
            ss.batch_update(protect(ss.worksheet("general")))


# -- rule 5: sharing ----------------------------------------------------------------

def test_a_class_sheet_is_shared_only_with_its_annotator_by_name(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        door.create_permission(sheet_id, type="user", role="writer",
                               email="annotator@example.org")
        with pytest.raises(DoorViolation, match="named people only"):
            door.create_permission(sheet_id, type="anyone", role="reader")
        with pytest.raises(DoorViolation, match="annotator"):
            door.create_permission(sheet_id, type="user", role="writer",
                                   email="someone.else@example.org")


# -- retry ------------------------------------------------------------------------

def test_a_busy_drive_is_retried(env):
    fake, door, sheet_id, _ = env
    fake.fail_after("update_cell", 1, exc=api_error(429, "rate limited"))
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        ws.update_cell(2, _col(ws, "Element") + 1, "renamed")
    assert fake.spreadsheet(sheet_id).worksheet("general").get_all_values()[1][0] == "renamed"


def test_a_create_that_landed_before_the_error_is_not_made_twice(env):
    fake, door, sheet_id, _ = env
    fake.fail_after("create_file", 1, exc=api_error(503, "unavailable"))
    with drive_door.running("update-sheets", APPLY):
        file_id = door.create_file("notes.txt", parents=["fake_root_folder"],
                                   content=b"x", mimetype="text/plain")
    assert len(fake.mutations_of("create_file")) == 1
    assert fake.file(file_id).name == "notes.txt"


# -- watch mode --------------------------------------------------------------------

def test_watch_mode_lets_the_write_through_and_files_one_issue(env, github):
    fake, _, sheet_id, _ = env
    drive_doorway.set_doorway(CheckedDoorway(fake, mode=drive_door.WATCH))
    door = drive_doorway.get_doorway()
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        ws.clear()
        ws.clear()
    assert fake.spreadsheet(sheet_id).worksheet("general").get_all_values() == []
    filed = github.list_issues(drive_door.VIOLATION_LABEL)
    assert len(filed) == 1
    assert "update-sheets" in github.issue(filed[0]["number"])["body"]


def test_a_sheet_the_door_cannot_place_is_not_held_to_class_sheet_rules(env):
    fake, door, _, _ = env
    with drive_door.running("update-sheets", APPLY):
        ss = door.create_spreadsheet("scratch")
        ws = ss.sheet1
        ws.update([["a", "b"], ["1", "2"]], "A1")
        ws.clear()
    assert ss.identity is None


# -- replacing(): snapshot, answered rows, mid-run edits (unit 5c) -----------------

def _keys(ws):
    """Every row key of the tab, as the schema defines them."""
    from planars.schema_values import row_key
    rows = ws.get_all_values()
    cols = [rows[0].index(k) for k in row_key(CLASS, ws.title)]
    return [[r[c] for c in cols] for r in rows[1:]]


def _answered_row(ws):
    """Index (0-based, header = 0) of the first row holding an answer."""
    rows = ws.get_all_values()
    c = rows[0].index("V-combines")
    return next(i for i, r in enumerate(rows) if i and r[c].strip())


def test_replacing_saves_the_tab_first(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        before = ws.get_all_values()
        with drive_door.replacing(ws, "a test that means it"):
            ws.clear()
    saved = json.loads((drive_door.SNAPSHOT_DIR / f"{LANG}_{CLASS}_general.json")
                       .read_text(encoding="utf-8"))
    assert saved["rows"] == before
    assert saved["reason"] == "a test that means it"
    assert saved["command"] == "update-sheets"


def test_replacing_refuses_to_drop_an_answered_row_in_any_mode(env):
    fake, _, sheet_id, _ = env
    drive_doorway.set_doorway(CheckedDoorway(fake, mode=drive_door.WATCH))
    door = drive_doorway.get_doorway()
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        gone = _answered_row(ws)
        keys = _keys(ws)
        kept = keys[:gone - 1] + keys[gone:]
        with pytest.raises(drive_door.AnswersWouldBeDropped) as refused:
            with drive_door.replacing(ws, "rebuild", kept=kept):
                ws.clear()
        assert len(refused.value.lines) == 1
        assert "V-combines" in refused.value.lines[0]
        with drive_door.replacing(ws, "rebuild", kept=kept, allow_drop=True):
            ws.clear()
    assert fake.spreadsheet(sheet_id).worksheet("general").get_all_values() == []


def test_replacing_lets_an_unanswered_row_go(env):
    fake, door, sheet_id, _ = env
    recorded = fake.spreadsheet(sheet_id).worksheet("general")
    header = recorded.get_all_values()[0]
    blank = len(recorded.get_all_values()) + 1           # a row with no answers
    for name, value in [("Position_Name", "v:test"), ("Element", "unanswered")]:
        recorded.update_cell(blank, header.index(name) + 1, value)
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        keys = _keys(ws)
        with drive_door.replacing(ws, "rebuild", kept=keys[:-1]):
            pass


def test_replacing_notices_an_annotator_editing_mid_run(env):
    fake, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        ws.get_all_values()                       # the command reads the tab...
        c = _col(ws, "Comments")
        fake.spreadsheet(sheet_id).worksheet("general").update_cell(2, c + 1, "typed meanwhile")
        with pytest.raises(DoorViolation, match="while the command ran"):
            with drive_door.replacing(ws, "rebuild"):
                pass


# -- provenance: one line per tab written (unit 5c) ---------------------------------

def _log():
    from coding import provenance
    if not provenance.LOG_PATH.exists():
        return []
    return [json.loads(l) for l in provenance.LOG_PATH.read_text(encoding="utf-8").splitlines()]


def test_each_tab_written_gets_one_provenance_line(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        ws = _tab(door, sheet_id, "general")
        c = _col(ws, "Element")
        ws.update_cell(2, c + 1, "renamed")
        ws.update_cell(3, c + 1, "renamed too")
        with drive_door.replacing(_tab(door, sheet_id, "Status"), "a test that means it"):
            _tab(door, sheet_id, "Status").clear()
    lines = {l["tab"]: l for l in _log()}
    assert set(lines) == {"general", "Status"}
    general = lines["general"]
    assert general["command"] == "update-sheets" and general["args"] == {"apply": True}
    assert general["identity"] == f"{CLASS}_{LANG}"
    assert (general["writes"], general["cells"], general["actions"]) == (2, 2, ["update_cell"])
    assert general["replacing"] == []
    assert lines["Status"]["replacing"] == ["a test that means it"]


def test_a_command_that_writes_nothing_logs_nothing(env):
    _, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        _tab(door, sheet_id, "general").get_all_values()
    assert _log() == []
