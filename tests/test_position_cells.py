"""Position cells: answers written as position numbers or names
(planars/position_cells.py), and their renumbering by sync-planar when the
planar's numbers shift (coding/sync_planar.py, _renumber_class_sheets)."""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import pytest

from coding import drive as drive_module
from coding import drive_doorway, file_door
from coding import sync_planar as sp
from coding.biuniqueness_rows import morpheme_rows
from coding.schemas import position_criteria
from command_runner import run_command
from fake_drive import FakeDriveDoorway, use_frozen_coded_data
from planars.position_cells import as_names, renumber

NAMES = {3: "v:frontedauxiliary", 12: "v:perfect", 31: "v:verbinflection", 34: "v:neg1"}


# ---------------------------------------------------------------------------
# Reading and renumbering one cell
# ---------------------------------------------------------------------------

def test_numbers_and_names_both_read_as_names():
    assert as_names("31", NAMES) == (["v:verbinflection"], [])
    assert as_names("3, v:perfect", NAMES) == (["v:frontedauxiliary", "v:perfect"], [])
    assert as_names("99, v:nowhere", NAMES) == ([], ["99", "v:nowhere"])
    assert as_names("", NAMES) == ([], [])


def test_renumber_moves_numbers_by_name_and_leaves_names_alone():
    new = {"v:frontedauxiliary": 4, "v:perfect": 13, "v:verbinflection": 32, "v:neg1": 35}
    assert renumber("3, 12", NAMES, new) == ("4, 13", [])
    # The 1 in v:neg1 is part of a name, never a number.
    assert renumber("v:neg1, 31", NAMES, new) == ("v:neg1, 32", [])
    assert renumber("na", NAMES, new) == ("na", [])


def test_renumber_leaves_a_number_whose_position_is_gone_and_says_so():
    new = {"v:frontedauxiliary": 3}
    assert renumber("3, 31", NAMES, new) == ("3, 31", [31])
    assert renumber("77", NAMES, new) == ("77", [77])


def test_position_criteria_come_from_the_schema():
    crits = position_criteria()
    assert {"co_exponents", "conditioned_by", "dependent-on-left",
            "dependent-on-right"} <= crits
    assert "has_allomorphs" not in crits


# ---------------------------------------------------------------------------
# The morphemes tab names positions even where numbers were typed
# ---------------------------------------------------------------------------

def test_co_exponent_labels_use_names_for_typed_numbers():
    planar = pd.DataFrame({
        "Language_ID": ["x"] * 3, "Position": ["3", "12", "31"],
        "Position_Name": ["v:frontedauxiliary", "v:perfect", "v:verbinflection"],
        "Elements": ["be", "ha", "-ed"], "Class_Type": ["list"] * 3})
    elements = pd.DataFrame({
        "Element": ["[-ed]", "be"], "Position_Name": ["v:verbinflection", "v:frontedauxiliary"],
        "has_allomorphs": ["n", "n"], "members": ["", ""],
        "co_exponents": ["3, 12", "v:verbinflection"]})
    labels = [r["Morpheme"] for r in morpheme_rows(elements, planar, "x")]
    assert labels == ["be + v:verbinflection",
                      "[-ed] + v:frontedauxiliary, v:perfect"]


# ---------------------------------------------------------------------------
# sync-planar renumbers the class sheets before the planar Sheet takes a new planar
# ---------------------------------------------------------------------------

LANG = "stan1293"
PLANAR_ID = "1nmaNay3ne53-Gkm4wBTOy7vebYcX70WPvCwfvjT5Tc0"
BIUNIQ = "1Xz8_4aMFr4xfkNrlomiURODtbUuFFEmkMTr9WO6_5aI"
FREE_OCC = "1L3kfV-g278NMxbdqfu2sN343nmKp1r-29jq60fr9YsQ"


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures(langs=[LANG])
    # The whole language folder: the Drive door checks each sheet it wrote
    # against a spec built from the language's files.
    coded = use_frozen_coded_data(monkeypatch, tmp_path)
    config = FakeDriveDoorway.drive_config()
    config.setdefault(LANG, {})["planar_spreadsheet_id"] = PLANAR_ID
    monkeypatch.setattr(sp, "PLANAR_CHANGES_PATH", tmp_path / "planar_changes.json")
    monkeypatch.setattr(drive_module, "_load_drive_config", lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(file_door, "_commit", lambda run: None)
    drive_doorway.set_doorway(doorway)
    try:
        yield doorway, coded, tmp_path / "planar_changes.json"
    finally:
        drive_doorway.reset_doorway()


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", argv)
    buf = io.StringIO()
    code = 0
    try:
        with redirect_stdout(buf):
            run_command(sp, "sync-planar")
    except SystemExit as exc:
        code = exc.code or 0
    return code, buf.getvalue()


def _cell_at(ws, column: str, row_index: int):
    rows = ws.get_all_values()
    c = rows[0].index(column)
    return rows[row_index][c] if c < len(rows[row_index]) else ""


def _set(ws, column: str, row_index: int, value: str) -> None:
    from gspread.utils import rowcol_to_a1
    c = ws.get_all_values()[0].index(column) + 1
    ws.update([[value]], rowcol_to_a1(row_index + 1, c))


def _planar_path(coded) -> Path:
    return coded / LANG / "lang_setup" / f"planar_{LANG}.tsv"


def _write_planar(coded, rows) -> None:
    pd.DataFrame(rows[1:], columns=rows[0]).to_csv(_planar_path(coded), sep="\t", index=False)


def _planar_rows(coded):
    df = pd.read_csv(_planar_path(coded), sep="\t", dtype=str, keep_default_na=False)
    return [list(df.columns)] + [[str(v) for v in r] for _, r in df.iterrows()]


def _insert_position_at_2(coded) -> None:
    """The planar file gains a position at number 2; every later one shifts.
    The planar Sheet still holds the old numbering."""
    rows = _planar_rows(coded)
    header, data = rows[0], rows[1:]
    pos, name = header.index("Position"), header.index("Position_Name")
    new_row = list(data[1])
    new_row[pos], new_row[name] = "2", "v:inserted"
    for r in data[1:]:
        r[pos] = str(int(r[pos]) + 1)
    _write_planar(coded, [header, data[0], new_row] + data[1:])


def _seed_answers(doorway) -> None:
    _set(doorway.spreadsheet(BIUNIQ).worksheet("elements"), "co_exponents", 1, "3, 31")
    _set(doorway.spreadsheet(BIUNIQ).worksheet("elements"), "co_exponents", 2, "v:verbinflection")
    _set(doorway.spreadsheet(FREE_OCC).worksheet("general"), "dependent-on-left", 1, "30")
    doorway.clear_mutations()


def test_insertion_renumbers_typed_numbers_in_every_class_sheet(env, monkeypatch):
    doorway, coded, changes_path = env
    _seed_answers(doorway)
    _insert_position_at_2(coded)

    code, out = _run(monkeypatch, ["sync-planar", "--apply"])

    assert code == 0, out
    elements = doorway.spreadsheet(BIUNIQ).worksheet("elements")
    assert _cell_at(elements, "co_exponents", 1) == "4, 32"
    assert _cell_at(elements, "co_exponents", 2) == "v:verbinflection"
    assert _cell_at(doorway.spreadsheet(FREE_OCC).worksheet("general"),
                    "dependent-on-left", 1) == "31"
    assert doorway.spreadsheet(PLANAR_ID).sheet1.get_all_values() == _planar_rows(coded)
    cells = json.loads(changes_path.read_text())[LANG]["position_cells"]
    assert any("3, 31 → 4, 32" in line for line in cells["changed"])
    assert not file_door.renumbering().path.exists()

    # Nothing left to do: a second run changes nothing.
    doorway.clear_mutations()
    code, out = _run(monkeypatch, ["sync-planar", "--apply"])
    assert code == 0 and "up to date" in out
    assert _cell_at(elements, "co_exponents", 1) == "4, 32"


def test_dry_run_reports_but_writes_nothing(env, monkeypatch):
    doorway, coded, _ = env
    _seed_answers(doorway)
    _insert_position_at_2(coded)
    code, out = _run(monkeypatch, ["sync-planar"])
    assert code == 0
    assert "would renumber: biuniqueness_deviations / elements" in out
    assert _cell_at(doorway.spreadsheet(BIUNIQ).worksheet("elements"), "co_exponents", 1) == "3, 31"
    assert not doorway.mutations_of("values_batch_update")


def test_a_run_stopped_partway_never_renumbers_a_sheet_twice(env, monkeypatch):
    doorway, coded, _ = env
    _seed_answers(doorway)
    planar_sheet = doorway.spreadsheet(PLANAR_ID).sheet1
    before = planar_sheet.get_all_values()
    _insert_position_at_2(coded)

    # biuniqueness_deviations is renumbered first (sheets go in name order).
    # Its write lands, then the run dies before recording it as done.
    doorway.fail_after("values_batch_update", 1, RuntimeError("connection lost"))
    code, out = _run(monkeypatch, ["sync-planar", "--apply"])
    assert code != 0
    assert planar_sheet.get_all_values() == before, "planar Sheet must wait for the sheets"
    elements = doorway.spreadsheet(BIUNIQ).worksheet("elements")
    assert _cell_at(elements, "co_exponents", 1) == "4, 32"
    assert "pending" in json.loads(file_door.renumbering().path.read_text())[LANG][BIUNIQ]

    doorway.clear_faults()
    code, out = _run(monkeypatch, ["sync-planar", "--apply"])
    assert code == 0, out
    assert _cell_at(elements, "co_exponents", 1) == "4, 32"   # not 5, 33
    assert _cell_at(doorway.spreadsheet(FREE_OCC).worksheet("general"),
                    "dependent-on-left", 1) == "31"
    assert not file_door.renumbering().path.exists()


def test_a_number_whose_position_is_gone_is_left_and_listed(env, monkeypatch):
    doorway, coded, changes_path = env
    _set(doorway.spreadsheet(BIUNIQ).worksheet("elements"), "co_exponents", 1, "38")
    doorway.clear_mutations()
    _write_planar(coded, _planar_rows(coded)[:-1])   # the last position (38, v:rightedge) removed

    code, out = _run(monkeypatch, ["sync-planar", "--apply"])
    assert code == 0, out
    assert _cell_at(doorway.spreadsheet(BIUNIQ).worksheet("elements"), "co_exponents", 1) == "38"
    unresolved = json.loads(changes_path.read_text())[LANG]["position_cells"]["unresolved"]
    assert any("38 — position 38 (v:rightedge) is not in the new planar" in u for u in unresolved)


def test_the_planar_changed_issue_lists_renumbered_and_unresolved_cells():
    from coding.daily_refresh import planar_changed_body
    body = planar_changed_body(
        {LANG: {"diff": {"added": {"2": "v:inserted"}, "deleted": {}, "renamed": {},
                         "remaps": [[2, 3]], "columns_added": []},
                "recommendation": "python -m coding restructure-sheets --lang stan1293 --apply",
                "position_cells": {"changed": ["biuniqueness_deviations / elements, row 2: 3 → 4"],
                                   "unresolved": ["free_occurrence / general, row 5: 38 — gone"]}}},
        failure="Traceback ... Drive is down")
    assert "could not be updated" in body and "Drive is down" in body
    assert "position 2 is now position 3" in body
    assert "row 2: 3 → 4" in body
    assert "Check these answers" in body and "38 — gone" in body
