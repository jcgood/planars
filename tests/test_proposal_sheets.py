"""`python -m coding proposal-sheets` (Phase 10 unit 11a), against the offline
Drive and a copy of the frozen language folders.

Each language gets one proposal sheet, "English [stan1293] planars and
diagnostics" (Instructions, Last review, Planar, Diagnostics),
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
from coding.sheet_spec import (PROPOSAL_DIAGNOSTICS_TAB, PROPOSAL_INSTRUCTIONS_TAB,
                               PROPOSAL_PLANAR_TAB, REVIEW_TAB_TITLE, WHAT_CHANGED_COLUMN)
from coding.proposal_diff import compare, describe, normal, three_way
from command_runner import run_command
from fake_drive import FakeDriveDoorway, use_frozen_coded_data

ANNOTATOR = "annotator@example.org"  # tests/conftest.py's placeholder address
LANG = "stan1293"


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """Yields (doorway, run, coded). ``run(*flags)`` plays the command and
    returns (output, exit code)."""
    doorway = FakeDriveDoorway.from_fixtures()
    coded = use_frozen_coded_data(monkeypatch, tmp_path)
    # No language has a proposal sheet yet here (the ID file below records
    # none), so none has the record of what one was filled with either; the
    # frozen data holds the real ones since 2026-10-22.
    for base in coded.glob("*/lang_setup/proposal_base_*.json"):
        base.unlink()
    config = FakeDriveDoorway.drive_config()
    for lang_id, entry in list(config.items()):
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


def accept(monkeypatch, answers: List[str], *flags: str):
    """Play accept-proposal, answering its questions in order; returns
    (output, exit code)."""
    from coding import accept_proposal
    replies = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(replies))
    monkeypatch.setattr(sys, "argv", ["accept-proposal", "--lang", LANG, *flags])
    buf, code = io.StringIO(), 0
    try:
        with redirect_stdout(buf):
            run_command(accept_proposal, "accept-proposal")
    except SystemExit as exc:
        code = exc.code
    return buf.getvalue(), code


def the_sheet(doorway):
    found = [ss for ss in doorway._spreadsheets.values()
             if ss.title == "English [stan1293] planars and diagnostics"]
    assert len(found) == 1, f"{len(found)} proposal sheets"
    return found[0]


def planar_grid(coded) -> List[List[str]]:
    lines = (coded / LANG / "lang_setup" / f"planar_{LANG}.tsv").read_text(
        encoding="utf-8").splitlines()
    return [line.split("\t") for line in lines if line.strip()]


def trimmed(grid):
    return [list(r) for r in normal(grid)]


def open_proposals(github):
    return [i for i in github.issues if cmd.LABEL in i["labels"] and i["state"] == "OPEN"]


def annotate(doorway, row: int, column: str, value: str) -> None:
    """The annotator edits one cell of the Planar tab (row 1 is the header)."""
    ws = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB)
    header = ws.get_all_values()[0]
    ws.update_cell(row, header.index(column) + 1, value)


def edit_planar_file(coded, old: str, new: str) -> None:
    path = coded / LANG / "lang_setup" / f"planar_{LANG}.tsv"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_a_sheet_made_before_2026_10_24_is_retitled_and_given_its_instructions(env):
    """The live sheets were titled proposal_{lang} and had no Instructions
    tab; the next run brings them up to date, and the one after writes
    nothing."""
    doorway, run, coded = env
    run("--apply")
    ss = the_sheet(doorway)
    ss.del_worksheet(ss.worksheet(PROPOSAL_INSTRUCTIONS_TAB))
    doorway.file(ss.id).name = ss.title = f"proposal_{LANG}"
    review = ss.worksheet(REVIEW_TAB_TITLE)
    review.clear()
    review.update([[REVIEW_TAB_TITLE], ["No proposal reviewed yet."], [""],
                   ["To propose a change, edit the Planar or Diagnostics tab."]], "A1")
    doorway.clear_mutations()

    out, code = run("--apply")

    assert code == 0, out
    assert f"retitle 'proposal_{LANG}'" in out
    ss = the_sheet(doorway)
    assert [ws.title for ws in ss.worksheets()][:2] == [PROPOSAL_INSTRUCTIONS_TAB,
                                                        REVIEW_TAB_TITLE]
    assert ss.list_protected_ranges(ss.worksheet(PROPOSAL_INSTRUCTIONS_TAB).id)
    assert "propose" not in str(ss.worksheet(REVIEW_TAB_TITLE).get_all_values())
    doorway.clear_mutations()
    run("--apply")
    assert doorway.mutations == []


def test_a_dry_run_makes_nothing(env):
    doorway, run, coded = env
    out, code = run()
    assert code == 0
    assert "would make English [stan1293] planars and diagnostics" in out
    assert not [ss for ss in doorway._spreadsheets.values()
                if ss.title.endswith("planars and diagnostics")]
    assert not file_door.proposal_base(LANG).path.exists()


def test_apply_makes_the_sheet_filled_from_the_sources(env):
    doorway, run, coded = env
    out, code = run("--apply")
    assert code == 0, out
    ss = the_sheet(doorway)
    assert [ws.title for ws in ss.worksheets()] == [
        PROPOSAL_INSTRUCTIONS_TAB, REVIEW_TAB_TITLE, PROPOSAL_PLANAR_TAB,
        PROPOSAL_DIAGNOSTICS_TAB]
    instructions = ss.worksheet(PROPOSAL_INSTRUCTIONS_TAB)
    assert "This sheet is for editing" in str(instructions.get_all_values())
    assert ss.list_protected_ranges(instructions.id)
    planar = ss.worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    source = planar_grid(coded)
    assert planar[0] == source[0] + [WHAT_CHANGED_COLUMN]
    assert trimmed([r[:len(source[0])] for r in planar]) == trimmed(source)
    assert ss.worksheet(PROPOSAL_DIAGNOSTICS_TAB).get_all_values()[0][-1] == WHAT_CHANGED_COLUMN
    assert "No changes reviewed yet." in str(
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
    assert f"{PROPOSAL_PLANAR_TAB}: took in the source's changes" in out
    planar = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    assert planar[1][1] == first_name + "X"
    base = json.loads(file_door.proposal_base(LANG).path.read_text(encoding="utf-8"))
    assert base[PROPOSAL_PLANAR_TAB][1][1] == first_name + "X"


def test_a_proposal_files_an_issue_naming_each_change_and_its_reason(env, github):
    doorway, run, coded = env
    run("--apply")
    annotate(doorway, 2, "Elements", "and, also, then, so, CONJUNCT")
    annotate(doorway, 2, WHAT_CHANGED_COLUMN, "so is a conjunct too")
    out, code = run("--apply")
    assert code == 0, out
    [issue] = open_proposals(github)
    assert issue["title"] == cmd.issue_title(LANG)
    assert "position 1 `v:leftedge`: Elements" in issue["body"], issue["body"]
    assert "*so is a conjunct too*" in issue["body"]
    assert "## Diagnostics" not in issue["body"]
    # Run again with nothing new: the same one issue, brought up to date.
    run("--apply")
    assert len(open_proposals(github)) == 1


def test_the_sources_changes_are_taken_in_around_a_proposal(env, github):
    doorway, run, coded = env
    run("--apply")
    annotate(doorway, 2, "Elements", "and, also, then, so, CONJUNCT")   # the annotator
    last = planar_grid(coded)[-1]
    edit_planar_file(coded, last[4], last[4] + "X")                     # the coordinator
    out, code = run("--apply")
    assert code == 0, out
    grid = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    header = grid[0]
    assert grid[1][header.index("Elements")] == "and, also, then, so, CONJUNCT"
    assert trimmed(grid)[-1][header.index("Position_Name")] == last[4] + "X"
    [issue] = open_proposals(github)
    assert "Changed by both" not in issue["body"]


def test_a_change_the_coordinator_also_makes_in_the_source_closes_the_issue(env, github):
    doorway, run, coded = env
    run("--apply")
    annotate(doorway, 2, "Elements", "and, also, then, so, CONJUNCT")
    annotate(doorway, 2, WHAT_CHANGED_COLUMN, "so is a conjunct too")
    run("--apply")
    assert len(open_proposals(github)) == 1
    edit_planar_file(coded, "and, also, then, CONJUNCT", "and, also, then, so, CONJUNCT")
    out, code = run("--apply")
    assert code == 0, out
    assert open_proposals(github) == []
    # The reason stays on the sheet: it is the annotator's.
    grid = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    assert grid[1][grid[0].index(WHAT_CHANGED_COLUMN)] == "so is a conjunct too"


def test_a_row_both_changed_differently_is_a_conflict_kept_as_the_annotator_left_it(env, github):
    doorway, run, coded = env
    run("--apply")
    annotate(doorway, 2, "Elements", "and, also, then, so, CONJUNCT")
    edit_planar_file(coded, "and, also, then, CONJUNCT", "and, then, CONJUNCT")
    out, code = run("--apply")
    assert code == 0, out
    [issue] = open_proposals(github)
    assert "Changed by both" in issue["body"]
    grid = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    assert grid[1][grid[0].index("Elements")] == "and, also, then, so, CONJUNCT"


def test_a_dry_run_files_no_issue_and_writes_nothing(env, github):
    doorway, run, coded = env
    run("--apply")
    annotate(doorway, 2, "Elements", "and, also, then, so, CONJUNCT")
    edit_planar_file(coded, planar_grid(coded)[-1][4], planar_grid(coded)[-1][4] + "X")
    doorway.clear_mutations()
    out, code = run()
    assert code == 0, out
    assert "would file or update" in out and "would take in the source's changes" in out
    assert open_proposals(github) == []
    assert doorway.mutations == []


# --- the three-way comparison on its own ---------------------------------------

H = ("Position", "Position_Name", "Elements", WHAT_CHANGED_COLUMN)


def rows(*items):
    return [H] + [tuple(i) for i in items]


def test_an_inserted_position_is_one_change_not_a_renumbering_of_every_row():
    base = rows(("1", "a", "x"), ("2", "b", "y"), ("3", "c", "z"))
    sheet = rows(("1", "a", "x"), ("2", "new", "n", "a new slot"), ("3", "b", "y"),
                 ("4", "c", "z"))
    c = compare(base, sheet, base, WHAT_CHANGED_COLUMN)
    assert len(c.changes) == 1 and not c.conflicts and not c.refreshed
    assert describe(H, c.base, c.changes[0], WHAT_CHANGED_COLUMN) == [
        "row added after position 1 `a`: Position '2', Position_Name 'new', Elements 'n' — *a new slot*",
        "positions renumbered: 2 → 3, 3 → 4"]


@pytest.mark.parametrize("beside", [1, 3], ids=["row above", "row below"])
def test_a_deleted_rows_reason_is_taken_from_the_row_beside_it(beside):
    base = rows(("1", "a", "x"), ("2", "b", "y"), ("3", "c", "z"))
    kept = [list(r) for r in base if r[0] != "2"]
    kept[1 if beside == 1 else 2].append("b is part of a")
    c = compare(base, kept, base, WHAT_CHANGED_COLUMN)
    [change] = c.changes
    assert describe(H, c.base, change, WHAT_CHANGED_COLUMN) == [
        "position 2 `b` removed — *b is part of a*"]


def test_separate_changes_by_each_side_are_both_kept():
    base = rows(("1", "a", "x"), ("2", "b", "y"), ("3", "c", "z"), ("4", "d", "w"))
    sheet = rows(("1", "a", "x2"), ("2", "b", "y"), ("3", "c", "z"), ("4", "d", "w"))
    source = rows(("1", "a", "x"), ("2", "b", "y"), ("3", "c", "z"), ("4", "d", "w2"))
    m = three_way(normal(base), normal(sheet), normal(source))
    assert m.sheet[1][2] == "x2" and m.sheet[4][2] == "w2"
    assert m.base[1][2] == "x" and m.base[4][2] == "w2"
    assert not m.conflicts and len(m.proposal) == 1


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


# --- accept-proposal -------------------------------------------------------------

NEW_ELEMENTS = "and, also, then, so, CONJUNCT"


def propose_so(doorway, run):
    """The annotator proposes adding `so` at position 1; the daily run files the issue."""
    run("--apply")
    annotate(doorway, 2, "Elements", NEW_ELEMENTS)
    annotate(doorway, 2, WHAT_CHANGED_COLUMN, "so is a conjunct too")
    run("--apply")


def planar_cell(coded, column: str, row: int = 1) -> str:
    grid = planar_grid(coded)
    return grid[row][grid[0].index(column)]


def review_text(doorway) -> str:
    return "\n".join(r[0] for r in
                     the_sheet(doorway).worksheet(REVIEW_TAB_TITLE).get_all_values() if r)


def test_accept_proposal_without_apply_lists_the_changes_and_writes_nothing(env, monkeypatch):
    doorway, run, coded = env
    propose_so(doorway, run)
    doorway.clear_mutations()
    out, code = accept(monkeypatch, [])
    assert code == 0, out
    assert "1 change(s) to decide" in out and "position 1 `v:leftedge`: Elements" in out
    assert doorway.mutations == []
    assert planar_cell(coded, "Elements") == "and, also, then, CONJUNCT"


def test_an_accepted_change_reaches_the_planar_and_the_annotator_is_told(env, monkeypatch, github):
    doorway, run, coded = env
    propose_so(doorway, run)
    [issue] = open_proposals(github)
    out, code = accept(monkeypatch, ["y"], "--apply")
    assert code == 0, out
    assert planar_cell(coded, "Elements") == NEW_ELEMENTS
    # The change log names the issue and the annotator's reason.
    log = file_door.change_log(LANG).read_text(encoding="utf-8")
    assert f"accepted from #{issue['number']}" in log and "so is a conjunct too" in log
    # The sheet is refilled from the new planar, reasons cleared, and says what happened.
    grid = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    assert grid[1][grid[0].index("Elements")] == NEW_ELEMENTS
    assert grid[1][grid[0].index(WHAT_CHANGED_COLUMN)] == ""
    assert "Accepted:" in review_text(doorway)
    assert open_proposals(github) == []
    assert "**Accepted:**" in github.comments[issue["number"]][-1]
    # Nothing left to decide; the daily run agrees.
    assert "holds no proposal" in accept(monkeypatch, [])[0]
    out, _ = run("--apply")
    assert out.count("up to date") == 2


def test_a_rejected_change_goes_back_to_the_source_with_the_reason(env, monkeypatch, github):
    doorway, run, coded = env
    propose_so(doorway, run)
    out, code = accept(monkeypatch, ["n", "so is an adverb here"], "--apply")
    assert code == 0, out
    assert planar_cell(coded, "Elements") == "and, also, then, CONJUNCT"
    grid = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    assert grid[1][grid[0].index("Elements")] == "and, also, then, CONJUNCT"
    assert "Not accepted:" in review_text(doorway)
    assert "so is an adverb here" in review_text(doorway)
    assert open_proposals(github) == []


def test_a_conflict_kept_as_the_source_has_it(env, monkeypatch, github):
    doorway, run, coded = env
    run("--apply")
    annotate(doorway, 2, "Elements", NEW_ELEMENTS)
    edit_planar_file(coded, "and, also, then, CONJUNCT", "and, then, CONJUNCT")
    run("--apply")
    out, code = accept(monkeypatch, ["n", "also was dropped on purpose"], "--apply")
    assert code == 0, out
    assert "CONFLICT" in out
    assert planar_cell(coded, "Elements") == "and, then, CONJUNCT"
    grid = the_sheet(doorway).worksheet(PROPOSAL_PLANAR_TAB).get_all_values()
    assert grid[1][grid[0].index("Elements")] == "and, then, CONJUNCT"


def test_a_change_that_breaks_the_planar_writes_nothing(env, monkeypatch):
    doorway, run, coded = env
    run("--apply")
    annotate(doorway, 2, "Position", "first")
    run("--apply")
    before = planar_grid(coded)
    doorway.clear_mutations()
    out, code = accept(monkeypatch, ["y"], "--apply")
    assert code == 1
    assert "nothing was written" in out
    assert planar_grid(coded) == before
    assert doorway.mutations == []


def test_an_accepted_diagnostics_change_reaches_the_yaml(env, monkeypatch):
    doorway, run, coded = env
    run("--apply")
    ws = the_sheet(doorway).worksheet(PROPOSAL_DIAGNOSTICS_TAB)
    grid = ws.get_all_values()
    col = grid[0].index("Criteria")
    row = next(i for i, r in enumerate(grid) if r[0] == "ciscategorial")
    assert "A-combines{y/n}" in grid[row][col]
    ws.update_cell(row + 1, col + 1, "V-combines{y/n}, N-combines{y/n}")
    run("--apply")
    out, code = accept(monkeypatch, ["y"], "--apply")
    assert code == 0, out
    import yaml
    data = yaml.safe_load(file_door.diagnostics_yaml(LANG).path.read_text(encoding="utf-8"))
    criteria = data["classes"]["ciscategorial"]["criteria"]
    assert "A-combines" not in criteria and "V-combines" in criteria
