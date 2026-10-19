"""The Drive door's rules, one at a time (coding/drive_door.py).

Each test runs one write against the recorded English ciscategorial sheet
(Instructions, general, Status) through the door, in enforce mode unless the
test is about watch mode, and checks the door refused or allowed it.
"""
from __future__ import annotations

import argparse
import contextlib
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


def _unlabel_tabs(fake, sheet_id):
    """The recorded sheets are labelled (since the 2026-10-15 migration); this
    makes one whose tabs are not, as a tab added by hand would be."""
    fake.spreadsheet(sheet_id)._developer_metadata = []


def _tab(door, sheet_id, title):
    return door.open_spreadsheet(sheet_id).worksheet(title)


def _col(ws, name):
    return ws.get_all_values()[0].index(name)


@contextlib.contextmanager
def _running_out_of_shape(command="update-sheets"):
    """Run as ``command`` writes no real command makes (blanking a tab,
    renaming an element to nonsense), testing some other rule. They leave the
    sheet out of shape, which rule 6 reports when the command ends."""
    with pytest.raises(DoorViolation, match="shape at the end of the command"):
        with drive_door.running(command, APPLY):
            yield


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
        c = _col(ws, "Element")
        was = ws.get_all_values()[1][c]
        ws.update_cell(2, c + 1, "renamed")
        ws.update_cell(2, c + 1, was)     # back again, or rule 6 reports the shape


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
    with _running_out_of_shape():
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
        with pytest.raises(DoorViolation, match="not shared with this address"):
            door.create_permission(sheet_id, type="user", role="writer",
                                   email="someone.else@example.org")


def _labelled_file(fake, identity):
    """A file carrying ``identity``'s label, as the tooling would have made it."""
    return fake.create_file("a file", [], properties=identity.labels())


@pytest.mark.parametrize("identity, role", [
    (drive_door.lang_file("planar_sheet", LANG), "writer"),
    (drive_door.lang_file("diagnostics_sheet", LANG), "writer"),
    (drive_door.lang_file("notes_doc", LANG), "writer"),
    (drive_door.lang_file("status_sheet", LANG), "reader"),
    (drive_door.folder("language", LANG), "reader"),
    (drive_door.folder("status"), "reader"),
])
def test_every_kind_is_shared_with_its_annotator_at_its_role_and_never_by_link(
        env, identity, role):
    fake, door, _, _ = env
    file_id = _labelled_file(fake, identity)
    other = "writer" if role == "reader" else "reader"
    with drive_door.running("update-sheets", APPLY):
        door.create_permission(file_id, type="user", role=role, email=ANNOTATOR)
        with pytest.raises(DoorViolation, match=f"is a {role}, not a {other}"):
            door.create_permission(file_id, type="user", role=other, email=ANNOTATOR)
        with pytest.raises(DoorViolation, match="not by link"):
            door.create_permission(file_id, type="anyone", role="reader")
        with pytest.raises(DoorViolation, match="removing the grant is not"):
            door.delete_permission(file_id, _grant(fake, file_id))


@pytest.mark.parametrize("identity", [
    drive_door.manifest(), drive_door.folder("root"), drive_door.folder("archive", LANG),
])
def test_files_shared_with_nobody_take_no_grant(env, identity):
    fake, door, _, _ = env
    file_id = _labelled_file(fake, identity)
    with drive_door.running("update-sheets", APPLY):
        with pytest.raises(DoorViolation, match="names nobody"):
            door.create_permission(file_id, type="user", role="reader", email=ANNOTATOR)


@pytest.mark.parametrize("identity", [
    drive_door.lang_file("report", LANG), drive_door.notebook("domains", LANG),
])
def test_notebooks_and_reports_keep_their_link_share_until_q4(env, identity):
    fake, door, _, _ = env
    file_id = _labelled_file(fake, identity)
    with drive_door.running("generate-notebooks", APPLY):
        with pytest.raises(DoorViolation, match="gives reader, not writer"):
            door.create_permission(file_id, type="anyone", role="writer")
        door.create_permission(file_id, type="anyone", role="reader")
        link = next(p["id"] for p in fake.list_permissions(file_id, fields="permissions(id,type)")
                    if p["type"] == "anyone")
        with pytest.raises(DoorViolation, match="link share is in its sharing spec"):
            door.delete_permission(file_id, link)


def test_removing_a_grant_the_spec_does_not_call_for_is_allowed(env):
    fake, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        door.create_permission(sheet_id, type="user", role="writer", email=ANNOTATOR)
    fake.create_permission(sheet_id, type="anyone", role="reader")     # added by hand
    link = next(p["id"] for p in fake.list_permissions(sheet_id, fields="permissions(id,type)")
                if p["type"] == "anyone")
    with drive_door.running("update-sheets", APPLY):
        door.delete_permission(sheet_id, link)


def test_coordinators_are_writers_on_the_root_folder(env, monkeypatch):
    import coding.people
    fake, door, _, _ = env
    monkeypatch.setattr(coding.people, "_load_people", lambda: {
        "Adam Tallman": {"email": ANNOTATOR},
        "A Coordinator": {"email": "coordinator@example.org", "coordinator": True}})
    root = _labelled_file(fake, drive_door.folder("root"))
    with drive_door.running("update-sheets", APPLY):
        door.create_permission(root, type="user", role="writer",
                               email="coordinator@example.org")
        with pytest.raises(DoorViolation, match="not shared with this address"):
            door.create_permission(root, type="user", role="writer", email=ANNOTATOR)


def test_a_coordinator_flag_that_is_not_true_or_false_is_refused(monkeypatch):
    import coding.people
    monkeypatch.setattr(coding.people, "_load_people", lambda: {
        "Adam Tallman": {"email": ANNOTATOR, "coordinator": "yes"}})
    with pytest.raises(ValueError, match="write true or false"):
        coding.people.coordinator_emails()


# -- standing grants: integrity-check's SHARING section ----------------------------

def test_standing_grants_are_compared_with_the_rule_by_name_not_address():
    from coding.sheet_spec import sharing_differences, sharing_spec
    spec = sharing_spec(drive_door.class_sheet(LANG, CLASS))
    assert sharing_differences(spec, [
        {"type": "user", "role": "writer", "emailAddress": ANNOTATOR}]) == []
    differences = sharing_differences(spec, [
        {"type": "user", "role": "reader", "emailAddress": ANNOTATOR},
        {"type": "user", "role": "writer", "emailAddress": "stranger@example.org"},
        {"type": "anyone", "role": "reader"},
        {"type": "user", "role": "writer", "emailAddress": "x@example.org",     # inherited
         "permissionDetails": [{"inherited": True}]},
        {"type": "user", "role": "owner", "emailAddress": "owner@example.org"},
    ])
    assert differences == [
        "Adam Tallman is a reader, not a writer",
        "someone not in people.yaml has writer access the sharing rule doesn't give them",
        "shared by link (reader); it should be named people only",
    ]
    assert sharing_differences(spec, []) == ["Adam Tallman should be a writer and has no access"]


def test_integrity_check_reports_a_grant_made_by_hand(env, capsys):
    from coding import integrity_check
    fake, _, sheet_id, _ = env
    assert integrity_check._section_sharing() == (0, 0)       # the recording matches
    fake.create_permission(sheet_id, type="anyone", role="reader")  # in the Drive window
    assert integrity_check._section_sharing() == (1, 0)
    assert "ciscategorial_stan1293): shared by link" in capsys.readouterr().out


def test_every_kind_has_a_sharing_rule():
    from coding.sheet_spec import sharing_spec
    for kind, rule in drive_door.KINDS.items():
        names = sorted(rule["name"]) if rule["name"] else [None]
        for name in names:
            lang = None
            if kind == "folder":
                lang = LANG if name in ("language", "archive") else None
            elif rule["lang"] == "required" or (kind == "notebook" and name != "all_languages"):
                lang = LANG
            sharing_spec(drive_door.Identity(kind, lang, CLASS if kind == "class_sheet" else None,
                                             name))


# -- rule 7: comments ---------------------------------------------------------------

NOTIFY = argparse.Namespace(lang=None, verbose=False, notify=True)


def test_a_comment_may_mention_only_the_sheets_annotator(env):
    fake, door, sheet_id, _ = env
    with drive_door.running("validate-coding", NOTIFY):
        door.create_comment(sheet_id, "+annotator@example.org 1 cell needs fixing.")
        with pytest.raises(DoorViolation, match="only stan1293's annotator"):
            door.create_comment(sheet_id, "+someone.else@example.org look at this")
    assert [c["content"] for c in fake.list_comments(sheet_id)] == [
        "+annotator@example.org 1 cell needs fixing."]


def test_a_comment_goes_only_on_a_class_sheet(env):
    fake, door, _, _ = env
    manifest_id = next(fid for fid, f in fake._files.items() if f.name == "manifest.json")
    with drive_door.running("validate-coding", NOTIFY):
        with pytest.raises(DoorViolation, match="only on class sheets"):
            door.create_comment(manifest_id, "hello")


def test_a_comment_that_landed_before_the_error_is_not_posted_twice(env):
    fake, door, sheet_id, _ = env
    original = fake.create_comment

    def lands_then_fails(file_id, content):
        original(file_id, content)
        raise api_error(503, "unavailable")
    fake.create_comment = lands_then_fails
    with drive_door.running("validate-coding", NOTIFY):
        door.create_comment(sheet_id, "+annotator@example.org 2 cells need fixing.")
    assert len(fake.list_comments(sheet_id)) == 1


# -- retry ------------------------------------------------------------------------

def test_a_busy_drive_is_retried(env):
    fake, door, sheet_id, _ = env
    fake.fail_after("update_cell", 1, exc=api_error(429, "rate limited"))
    with _running_out_of_shape():
        ws = _tab(door, sheet_id, "general")
        ws.update_cell(2, _col(ws, "Element") + 1, "renamed")
    assert fake.spreadsheet(sheet_id).worksheet("general").get_all_values()[1][0] == "renamed"


def test_a_create_that_landed_before_the_error_is_not_made_twice(env):
    fake, door, sheet_id, _ = env
    fake.fail_after("create_file", 1, exc=api_error(503, "unavailable"))
    with drive_door.running("update-sheets", APPLY):
        file_id = door.create_file("manifest.json", parents=["fake_root_folder"],
                                   content=b"{}", mimetype="application/json",
                                   identity=drive_door.manifest())
    assert len(fake.mutations_of("create_file")) == 1
    assert fake.file(file_id).name == "manifest.json"


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


def test_a_command_run_inside_another_has_its_violations_reported_once(env, github):
    # daily-refresh runs each command inside its own running(); the inner
    # command reports what it broke, and the outer one must not report it again.
    fake, _, sheet_id, _ = env
    drive_doorway.set_doorway(CheckedDoorway(fake, mode=drive_door.WATCH))
    door = drive_doorway.get_doorway()
    with drive_door.running("daily-refresh", argparse.Namespace(apply=True)):
        with drive_door.running("update-sheets", APPLY):
            ws = _tab(door, sheet_id, "general")
            ws.clear()
            ws.clear()
    [issue] = github.list_issues(drive_door.VIOLATION_LABEL)
    assert "update-sheets" in github.issue(issue["number"])["body"]
    assert len(github.calls_of("create")) == 1 and not github.calls_of("comment")


def test_a_live_command_whose_door_is_made_inside_it_still_logs_and_reports(
        env, github, monkeypatch):
    # Live, no door exists when the dispatcher's running() starts: the command
    # makes one with its first get_doorway(). Until 2026-10-17 running() only
    # looked for an existing door, so live runs never logged their writes,
    # never checked their sheets' shape at the end and never filed a
    # door-violation issue (every test installs its door first, so none saw it).
    fake, _, sheet_id, _ = env
    drive_doorway.reset_doorway()
    monkeypatch.setattr(drive_doorway, "GspreadDoorway", lambda: fake)
    with drive_door.running("update-sheets", APPLY):
        door = drive_doorway.get_doorway()
        assert door.mode == drive_door.LIVE_MODE
        _tab(door, sheet_id, "general").clear()
    assert {l["tab"] for l in _log()} >= {"general"}
    assert len(github.list_issues(drive_door.VIOLATION_LABEL)) == 1


def test_a_sheet_the_door_cannot_place_is_not_held_to_class_sheet_rules(env):
    fake, door, _, _ = env
    scratch = fake.create_spreadsheet("scratch")      # made by hand: no label
    with drive_door.running("update-sheets", APPLY):
        ss = door.open_spreadsheet(scratch.id)
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
    with _running_out_of_shape():
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
    fake, door, sheet_id, _ = env
    _unlabel_tabs(fake, sheet_id)
    with _running_out_of_shape():
        ws = _tab(door, sheet_id, "general")
        c = _col(ws, "Element")
        ws.update_cell(2, c + 1, "renamed")
        ws.update_cell(3, c + 1, "renamed too")
        with drive_door.replacing(_tab(door, sheet_id, "Status"), "a test that means it"):
            _tab(door, sheet_id, "Status").clear()
    lines = {l["tab"]: l for l in _log()}
    # None: the sheet itself, whose tabs the door labelled at the end.
    assert set(lines) == {"general", "Status", None}
    assert lines[None]["actions"] == ["label_tabs"]
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


# -- identity labels (unit 5d) ----------------------------------------------------

@pytest.mark.parametrize("make, message", [
    (lambda: drive_door.Identity("spreadsheet", "stan1293"), "unknown kind"),
    (lambda: drive_door.Identity(drive_door.CLASS_SHEET, "stan1293"), "needs its class"),
    (lambda: drive_door.Identity("manifest", "stan1293"), "has no language"),
    (lambda: drive_door.notebook("domains"), "needs its language"),
    (lambda: drive_door.notebook("all_languages", "stan1293"), "has no language"),
    (lambda: drive_door.folder("language"), "needs its language"),
    (lambda: drive_door.folder("scratch"), "name is one of"),
])
def test_an_identity_the_door_cannot_place_cannot_be_made(make, message):
    with pytest.raises(ValueError, match=message):
        make()


def test_labels_round_trip():
    for identity in (drive_door.class_sheet(LANG, CLASS), drive_door.manifest(),
                     drive_door.notebook("all_languages"), drive_door.folder("archive", LANG)):
        assert drive_door.Identity.from_labels(identity.labels()) == identity
    assert drive_door.Identity.from_labels({}) is None
    assert drive_door.Identity.from_labels({"planars_kind": "spreadsheet"}) is None


def test_every_create_writes_its_label_and_the_label_places_the_file(env):
    fake, door, _, _ = env
    identity = drive_door.class_sheet(LANG, "noninterruption")
    with _running_out_of_shape():                       # made, never filled in
        ss = door.create_spreadsheet("noninterruption_stan1293", identity=identity)
        folder_id = door.get_or_create_folder("_archived", "fake_root_folder",
                                              identity=drive_door.folder("archive", LANG))
    assert fake.file(ss.id).properties == identity.labels()
    assert fake.file(folder_id).properties == drive_door.folder("archive", LANG).labels()
    with drive_door.running("update-sheets", APPLY):    # a new command: from the label
        assert door.open_spreadsheet(ss.id).identity == identity


def test_a_found_folder_labelled_as_something_else_is_reported(env):
    fake, door, _, _ = env
    with drive_door.running("update-sheets", APPLY):
        door.get_or_create_folder("_archived", "fake_root_folder",
                                  identity=drive_door.folder("archive", LANG))
    with drive_door.running("update-sheets", APPLY), \
            pytest.raises(DoorViolation, match="was expected"):
        door.get_or_create_folder("_archived", "fake_root_folder",
                                  identity=drive_door.folder("archive", "arao1248"))


# -- rule 5 and the archived label: writer while live, reader once archived -----------

ANNOTATOR = "annotator@example.org"


def _grant(fake, sheet_id):
    return next(p for p in fake.list_permissions(sheet_id, fields="permissions(id,emailAddress)")
                if p.get("emailAddress") == ANNOTATOR)["id"]


def test_the_annotators_role_follows_the_archived_label(env):
    fake, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        door.create_permission(sheet_id, type="user", role="writer", email=ANNOTATOR)
        grant = _grant(fake, sheet_id)
        with pytest.raises(DoorViolation, match=r"\(live\): this person is a writer"):
            door.update_permission(sheet_id, grant, "reader")
        door.mark_archived(sheet_id)
        assert fake.file(sheet_id).properties[drive_door.STATE_LABEL] == drive_door.ARCHIVED
        door.update_permission(sheet_id, grant, "reader")
        with pytest.raises(DoorViolation, match=r"\(archived\): this person is a reader"):
            door.update_permission(sheet_id, grant, "writer")
        door.mark_archived(sheet_id, archived=False)            # rolled back
        assert drive_door.STATE_LABEL not in fake.file(sheet_id).properties
        door.update_permission(sheet_id, grant, "writer")


def test_an_unlabelled_sheet_cannot_be_marked_archived(env):
    """The manifest no longer places a sheet (deleted 2026-10-16, once every
    file was labelled): a sheet with no label is one the door can't name."""
    fake, door, sheet_id, _ = env
    fake.file(sheet_id).properties.clear()
    with drive_door.running("prune-manifest", APPLY), \
            pytest.raises(DoorViolation, match="has no label"):
        door.mark_archived(sheet_id)
    assert fake.file(sheet_id).properties == {}


# -- tab labels --------------------------------------------------------------------

def _tab_labels(fake, sheet_id):
    meta = fake.spreadsheet(sheet_id).fetch_sheet_metadata()
    return {s["properties"]["title"]: {m["metadataKey"]: m["metadataValue"]
                                       for m in s["developerMetadata"]}
            for s in meta["sheets"]}


def _touch(door, sheet_id):
    ws = _tab(door, sheet_id, "general")
    ws.update_cell(2, _col(ws, "Element") + 1, ws.get_all_values()[1][_col(ws, "Element")])


def test_a_command_that_writes_a_class_sheet_labels_its_tabs(env):
    fake, door, sheet_id, _ = env
    _unlabel_tabs(fake, sheet_id)
    with drive_door.running("update-sheets", APPLY):
        _touch(door, sheet_id)
    labels = _tab_labels(fake, sheet_id)
    assert labels["general"] == {"planars_tab_kind": "construction", "planars_tab": "general"}
    assert labels["Instructions"]["planars_tab_kind"] == "locked"
    assert labels["Status"]["planars_tab_kind"] == "status"
    fake.clear_mutations()
    with drive_door.running("update-sheets", APPLY):    # already labelled: nothing to do
        _touch(door, sheet_id)
    assert fake.mutations_of("batch_update") == []


def test_tabs_are_not_labelled_after_a_dry_run_or_a_failed_command(env):
    fake, door, sheet_id, _ = env
    _unlabel_tabs(fake, sheet_id)
    with drive_door.running("import-sheets", DRY):
        ss = door.open_spreadsheet(sheet_id)
        with drive_door.always_on("highlighting"):
            ss.batch_update({"requests": [{"repeatCell": {
                "range": {"sheetId": ss.worksheet("general").id}, "cell": {},
                "fields": "userEnteredFormat.backgroundColor"}}]})
    with pytest.raises(RuntimeError):
        with drive_door.running("update-sheets", APPLY):
            _touch(door, sheet_id)
            raise RuntimeError("the command failed")
    assert all(not v for v in _tab_labels(fake, sheet_id).values())


def test_a_tab_renamed_by_hand_is_still_recognised_by_its_label(env):
    fake, door, sheet_id, coded = env
    with drive_door.running("update-sheets", APPLY):
        _touch(door, sheet_id)
    fake.spreadsheet(sheet_id).worksheet("general").update_title("general (done)")
    allowed = class_sheet_spec(LANG, CLASS, coded).tab("general").column("V-combines").allowed
    with drive_door.running("update-sheets", APPLY):
        ss = door.open_spreadsheet(sheet_id)
        ws = ss.worksheet("general (done)")
        ss.batch_update(_dropdown(ws, _col(ws, "V-combines"), allowed))   # the spec's general


def test_renaming_a_tab_through_the_door_drops_its_labels(env):
    fake, door, sheet_id, _ = env
    with drive_door.running("update-sheets", APPLY):
        _touch(door, sheet_id)
    with _running_out_of_shape():
        _tab(door, sheet_id, "general").update_title("renamed")
    # Not a tab the spec lists, so it is left unlabelled, and rule 6 reports it.
    assert _tab_labels(fake, sheet_id)["renamed"] == {}


# -- rule 6: shape at the end of the command (unit 5d) -----------------------------

def _drop_rows_by_hand(fake, sheet_id, start, end):
    """Delete rows of the recorded general tab outside the door, as drift
    that was there before any command ran."""
    ss = fake.spreadsheet(sheet_id)
    ss.batch_update({"requests": [{"deleteDimension": {"range": {
        "sheetId": ss.worksheet("general").id, "dimension": "ROWS",
        "startIndex": start, "endIndex": end}}}]})


def test_a_row_the_spec_does_not_have_is_reported(env):
    _, door, sheet_id, _ = env
    with pytest.raises(DoorViolation, match="row the spec does not have: Element 'stray'"):
        with drive_door.running("update-sheets", APPLY):
            ws = _tab(door, sheet_id, "general")
            header = ws.get_all_values()[0]
            stray = {"Element": "stray", "Position_Name": "v:test", "Position_Number": "99"}
            ws.append_rows([[stray.get(c, "") for c in header]])


def test_tabs_put_out_of_order_are_reported(env):
    _, door, sheet_id, _ = env
    with pytest.raises(DoorViolation, match="tabs out of order"):
        with drive_door.running("update-sheets", APPLY):
            ss = door.open_spreadsheet(sheet_id)
            ss.reorder_worksheets(list(reversed(ss.worksheets())))


def test_a_class_sheet_made_and_left_empty_is_reported(env):
    _, door, _, _ = env
    with pytest.raises(DoorViolation, match="noninterruption_stan1293/general: tab missing"):
        with drive_door.running("update-sheets", APPLY):
            door.create_spreadsheet("noninterruption_stan1293",
                                    identity=drive_door.class_sheet(LANG, "noninterruption"))


def test_drift_already_there_is_not_blamed_on_the_command(env):
    fake, door, sheet_id, _ = env
    rows = fake.spreadsheet(sheet_id).worksheet("general").get_all_values()
    _drop_rows_by_hand(fake, sheet_id, 1, 3)               # two rows already missing
    with drive_door.running("update-sheets", APPLY):       # an unrelated write
        ws = _tab(door, sheet_id, "general")
        c = _col(ws, "Comments")
        empty = next(i for i, r in enumerate(ws.get_all_values()) if i and r[c] == "")
        ws.update_cell(empty + 1, c + 1, "a note")
    with drive_door.running("update-sheets", APPLY):       # puts one of the two back
        _tab(door, sheet_id, "general").append_rows([rows[1]])


def test_a_dry_run_is_not_held_to_the_shape(env):
    _, door, sheet_id, _ = env
    with drive_door.running("import-sheets", DRY):
        ss = door.open_spreadsheet(sheet_id)
        with drive_door.always_on("highlighting"):
            ss.batch_update({"requests": [{"repeatCell": {
                "range": {"sheetId": ss.worksheet("general").id}, "cell": {},
                "fields": "userEnteredFormat.backgroundColor"}}]})
    # Ends without a violation: a dry run's highlights change no shape, so
    # the sheet's metadata is not even read.


def test_in_watch_mode_shape_problems_go_into_the_issue(env, github):
    fake, _, sheet_id, _ = env
    drive_doorway.set_doorway(CheckedDoorway(fake, mode=drive_door.WATCH))
    door = drive_doorway.get_doorway()
    with drive_door.running("update-sheets", APPLY):
        ss = door.open_spreadsheet(sheet_id)
        ss.reorder_worksheets(list(reversed(ss.worksheets())))
    filed = github.list_issues(drive_door.VIOLATION_LABEL)
    assert len(filed) == 1
    assert "tabs out of order" in github.issue(filed[0]["number"])["body"]


# -- reads the door adds (Q6) ------------------------------------------------------

def test_many_requests_to_one_tab_read_its_tab_list_once(env, monkeypatch):
    """import-sheets paints one request per invalid cell; finding each one's
    tab by re-reading the tab list exhausted Google's read quota (#306)."""
    fake, door, sheet_id, _ = env
    inner = fake.spreadsheet(sheet_id)
    reads = []
    real = inner.worksheets
    monkeypatch.setattr(inner, "worksheets", lambda: reads.append(1) or real())
    with drive_door.running("import-sheets", DRY):
        ss = door.open_spreadsheet(sheet_id)
        tab = ss.worksheet("general").id
        with drive_door.always_on("highlighting"):
            ss.batch_update({"requests": [{"updateCells": {
                "range": {"sheetId": tab, "startRowIndex": r, "endRowIndex": r + 1,
                          "startColumnIndex": 3, "endColumnIndex": 4},
                "rows": [{"values": [{"userEnteredFormat": {}}]}],
                "fields": "userEnteredFormat.backgroundColor"}} for r in range(1, 60)]})
    assert len(reads) == 1
