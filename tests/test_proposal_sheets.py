"""`python -m coding proposal-sheets` (Phase 10 unit 11a), against the offline
Drive and a copy of the frozen language folders.

Each language gets one proposal sheet (Last review, Planar, Diagnostics),
shared with its annotator; what it was filled with is saved as the
language's base; a tab still holding the base is refilled when its source
changes, and a tab holding a proposal is left alone.
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from typing import List

import pytest

from coding import drive_door, drive_doorway, file_door, state_files
from coding import proposal_sheets as cmd
from coding.sheet_spec import (PROPOSAL_DIAGNOSTICS_TAB, PROPOSAL_PLANAR_TAB, REVIEW_TAB_TITLE,
                               WHAT_CHANGED_COLUMN)
from command_runner import run_command
from fake_drive import FIXTURE_DIR, FakeDriveDoorway, use_frozen_coded_data

ANNOTATOR = "annotator@example.org"  # tests/conftest.py's placeholder address
LANG = "stan1293"


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """Yields (doorway, run, coded). ``run(*flags)`` plays the command and
    returns (output, exit code)."""
    doorway = FakeDriveDoorway.from_fixtures()
    coded = use_frozen_coded_data(monkeypatch, tmp_path)
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    config = FakeDriveDoorway.drive_config()
    for lang_id, entry in manifest.items():
        if isinstance(entry, dict) and entry.get("folder_id"):
            config[lang_id] = {"folder_id": entry["folder_id"]}
    state_files.ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    state_files.ID_FILE.write_text(json.dumps(config), encoding="utf-8")
    drive_doorway.set_doorway(doorway)

    def run(*flags: str):
        monkeypatch.setattr(sys, "argv", ["proposal-sheets", "--lang", LANG, *flags])
        buf, code = io.StringIO(), 0
        try:
            with redirect_stdout(buf):
                run_command(cmd, "proposal-sheets")
        except SystemExit as exc:
            code = exc.code
        return buf.getvalue(), code

    try:
        yield doorway, run, coded
    finally:
        drive_doorway.reset_doorway()


def the_sheet(doorway):
    found = [ss for ss in doorway._spreadsheets.values() if ss.title == f"proposal_{LANG}"]
    assert len(found) == 1, f"{len(found)} proposal sheets"
    return found[0]


def planar_grid(coded) -> List[List[str]]:
    lines = (coded / LANG / "lang_setup" / f"planar_{LANG}.tsv").read_text(
        encoding="utf-8").splitlines()
    return [line.split("\t") for line in lines if line.strip()]


def trimmed(grid):
    return cmd._normal(grid)


def edit_planar_file(coded, old: str, new: str) -> None:
    path = coded / LANG / "lang_setup" / f"planar_{LANG}.tsv"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_a_dry_run_makes_nothing(env):
    doorway, run, coded = env
    out, code = run()
    assert code == 0
    assert f"would make proposal_{LANG}" in out
    assert not [ss for ss in doorway._spreadsheets.values() if ss.title.startswith("proposal_")]
    assert not file_door.proposal_base(LANG).path.exists()


def test_apply_makes_the_sheet_filled_from_the_sources(env):
    doorway, run, coded = env
    out, code = run("--apply")
    assert code == 0, out
    ss = the_sheet(doorway)
    assert [ws.title for ws in ss.worksheets()] == [
        REVIEW_TAB_TITLE, PROPOSAL_PLANAR_TAB, PROPOSAL_DIAGNOSTICS_TAB]
    planar = ss.worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    source = planar_grid(coded)
    assert planar[0] == source[0] + [WHAT_CHANGED_COLUMN]
    assert trimmed([r[:len(source[0])] for r in planar]) == trimmed(source)
    assert ss.worksheet(PROPOSAL_DIAGNOSTICS_TAB).get_all_values()[0][-1] == WHAT_CHANGED_COLUMN
    assert "No proposal has been reviewed yet." in str(
        ss.worksheet(REVIEW_TAB_TITLE).get_all_values())
    # In the language's folder, labelled, shared with its annotator as writer.
    config = json.loads(state_files.ID_FILE.read_text(encoding="utf-8"))
    assert config[LANG][cmd.ID_KEY] == ss.id
    assert doorway.file(ss.id).parents == [config[LANG]["folder_id"]]
    assert drive_door.Identity.from_labels(doorway.file(ss.id).properties) == \
        drive_door.lang_file(drive_door.PROPOSAL_SHEET, LANG)
    grants = {p.get("emailAddress"): p["role"] for p in doorway.list_permissions(ss.id)}
    assert grants.get(ANNOTATOR) == "writer"
    base = json.loads(file_door.proposal_base(LANG).path.read_text(encoding="utf-8"))
    assert trimmed(base[PROPOSAL_PLANAR_TAB]) == trimmed(planar)


def test_a_second_run_with_nothing_changed_writes_nothing(env):
    doorway, run, coded = env
    run("--apply")
    doorway.clear_mutations()
    out, code = run("--apply")
    assert code == 0, out
    assert doorway.mutations == []
    assert out.count("up to date") == 2


def test_a_tab_holding_no_proposal_is_refilled_when_its_source_changes(env):
    doorway, run, coded = env
    run("--apply")
    first_name = planar_grid(coded)[1][1]
    edit_planar_file(coded, first_name, first_name + "X")
    out, code = run("--apply")
    assert code == 0, out
    assert f"{PROPOSAL_PLANAR_TAB}: refilled" in out
    planar = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    assert planar[1][1] == first_name + "X"
    base = json.loads(file_door.proposal_base(LANG).path.read_text(encoding="utf-8"))
    assert base[PROPOSAL_PLANAR_TAB][1][1] == first_name + "X"


def test_a_tab_holding_a_proposal_is_left_alone(env):
    doorway, run, coded = env
    run("--apply")
    ws = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB)
    ws.update_cell(2, len(ws.get_all_values()[0]), "a clitic form")   # the annotator
    first_name = planar_grid(coded)[1][1]
    edit_planar_file(coded, first_name, first_name + "X")              # the coordinator
    before = ws.get_all_values()
    out, code = run("--apply")
    assert code == 0, out
    assert f"{PROPOSAL_PLANAR_TAB}: holds a proposal; left as it is" in out
    assert ws.get_all_values() == before


def test_a_sheet_with_no_base_is_reported_and_left_alone(env):
    doorway, run, coded = env
    run("--apply")
    file_door.proposal_base(LANG).path.unlink()
    doorway.clear_mutations()
    out, code = run("--apply")
    assert code == 1
    assert "can't be told; nothing was written" in out
    assert doorway.mutations == []


def test_an_unrecorded_sheet_in_the_folder_stops_a_second_one_being_made(env):
    doorway, run, coded = env
    run("--apply")
    config = json.loads(state_files.ID_FILE.read_text(encoding="utf-8"))
    del config[LANG][cmd.ID_KEY]
    state_files.ID_FILE.write_text(json.dumps(config), encoding="utf-8")
    out, code = run("--apply")
    assert code == 1
    assert "doesn't record; nothing was made" in out
    the_sheet(doorway)      # still exactly one


def test_the_door_refuses_a_dropdown_on_a_proposal_tab(env):
    doorway, run, coded = env
    run("--apply")
    ss_id = the_sheet(doorway).id
    with drive_door.running("proposal-sheets", cmd.build_parser().parse_args(["--apply"])):
        ss = drive_doorway.get_doorway().open_spreadsheet(ss_id)
        ws = ss.worksheet(PROPOSAL_PLANAR_TAB)
        with pytest.raises(drive_door.DoorViolation, match="no dropdowns on proposal sheet"):
            ss.batch_update({"requests": [{"setDataValidation": {
                "range": {"sheetId": ws.id, "startRowIndex": 1, "startColumnIndex": 0,
                          "endColumnIndex": 1},
                "rule": {"condition": {"type": "ONE_OF_LIST",
                                       "values": [{"userEnteredValue": "y"}]}}}}]})
