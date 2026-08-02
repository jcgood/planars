"""Snapshot tests for `python -m coding generate-biuniqueness-allomorphy-sheet`.

File 7 of 17 migrated to the Drive doorway, and the first to create a
spreadsheet from scratch and share it with a named person — neither of which
anything had exercised.

What is worth pinning here is mostly about not losing work someone has already
done. The command clears and rewrites the tab on every run, so the things that
must hold are: the dry run writes nothing at all; a re-run reuses the same
spreadsheet rather than minting a new URL and stranding the old one; and the
sheet is shared with Adam by name, never "anyone with the link" — this is
unpublished research data, and a link is not access control.

Before migrating, the old code was driven from this same stand-in Drive through
shims, across five scenarios. Output, the sheet's contents, and the recorded
Drive changes came back byte-identical afterwards.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_biuniqueness_allomorphy_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List

import pytest

from coding import drive as drive_module
from coding import drive_doorway
from coding import generate_biuniqueness_allomorphy_sheet as gen
from fake_drive import MANIFEST_FILE_ID, ROOT_FOLDER_ID, FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "biuniqueness_allomorphy"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANG = "synth0001"
ADAM = "adamjamesrosstallman@gmail.com"
SHEET_NAME = f"biuniqueness_allomorphy_{LANG}"


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """A stand-in Drive with synth0001's folder, and the real planar as input.

    Yields (doorway, run, saved). `run(argv)` plays one command and returns its
    output with the generated spreadsheet ID blanked, since it is a fresh id
    each time.
    """
    doorway = FakeDriveDoorway.from_fixtures()
    config = {"_planars_config_file_id": MANIFEST_FILE_ID,
              "_root_folder_id": ROOT_FOLDER_ID}
    saved: Dict = {}
    # sheets_manifest.json lives at the repo root; never let a test write it.
    monkeypatch.setattr(gen, "MANIFEST_PATH", tmp_path / "sheets_manifest.json")
    monkeypatch.setattr(gen, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(gen, "_save_drive_config", saved.update)
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                gen.main()
        except SystemExit as exc:
            buf.write(f"[SystemExit: {exc.code}]\n")
        return re.sub(r"fake_ss_\d+", "NEW_SHEET_ID", buf.getvalue())

    try:
        yield doorway, run, saved
    finally:
        drive_doorway.reset_doorway()


def check_snapshot(name: str, actual: str) -> None:
    path = SNAPSHOT_DIR / name
    if UPDATING:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"updated snapshot {path.relative_to(ROOT)}")
    assert path.exists(), (
        f"Snapshot missing: {path.relative_to(ROOT)}\n"
        f"Run: PLANARS_UPDATE_SNAPSHOTS=1 pytest {Path(__file__).relative_to(ROOT)}")
    assert actual == path.read_text(encoding="utf-8"), (
        f"Output differs from {path.name}. If intended, regenerate with "
        f"PLANARS_UPDATE_SNAPSHOTS=1 and review the diff.")


def the_sheet(doorway):
    for ss in doorway._spreadsheets.values():
        if ss.title == SHEET_NAME:
            return ss
    raise AssertionError(f"no spreadsheet called {SHEET_NAME}")


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    _, run, _ = env
    out = run(["gen", "--lang", LANG])
    # 135 element rows; keep the shape, not the listing.
    lines = out.splitlines()
    trimmed = "\n".join(lines[:5] + [f"    ... {len(lines) - 7} more rows ..."] + lines[-2:])
    check_snapshot("dry_run.txt", trimmed + "\n")


def test_apply_transcript(env):
    _, run, _ = env
    out = run(["gen", "--lang", LANG, "--apply"])
    lines = out.splitlines()
    trimmed = "\n".join(lines[:5] + [f"    ... {len(lines) - 7} more rows ..."] + lines[-2:])
    check_snapshot("apply.txt", trimmed + "\n")


# ---------------------------------------------------------------------------
# The dry run is a dry run
# ---------------------------------------------------------------------------

def test_dry_run_touches_nothing(env):
    doorway, run, saved = env
    out = run(["gen", "--lang", LANG])
    assert doorway.mutations == []
    assert saved == {}
    assert "Run with --apply" in out


# ---------------------------------------------------------------------------
# Creating it, and re-creating it
# ---------------------------------------------------------------------------

def test_the_sheet_lands_in_the_languages_folder(env):
    doorway, run, _ = env
    run(["gen", "--lang", LANG, "--apply"])
    ss = the_sheet(doorway)
    folder = doorway.download_file_json(MANIFEST_FILE_ID)[LANG]["folder_id"]
    moved = doorway.mutations_of("move_file")
    assert [(m["file_id"], m["to_parent"]) for m in moved] == [(ss.id, folder)]


def test_it_is_shared_with_adam_by_name_not_by_link(env):
    """Unpublished research data. A link is not access control."""
    doorway, run, _ = env
    run(["gen", "--lang", LANG, "--apply"])
    perms = doorway.mutations_of("create_permission")
    assert len(perms) == 1
    assert perms[0]["type"] == "user"
    assert perms[0]["role"] == "writer"
    assert perms[0]["email"] == ADAM
    assert perms[0]["notify"] is False       # no surprise email


def test_a_second_run_reuses_the_same_spreadsheet(env):
    """Or the URL Adam has been given would go stale on every regeneration."""
    doorway, run, _ = env
    run(["gen", "--lang", LANG, "--apply"])
    first_id = the_sheet(doorway).id
    doorway.clear_mutations()

    run(["gen", "--lang", LANG, "--apply"])
    assert the_sheet(doorway).id == first_id
    assert doorway.mutations_of("create_spreadsheet") == []
    assert doorway.mutations_of("move_file") == []


def test_the_tab_is_called_prescreening(env):
    doorway, run, _ = env
    run(["gen", "--lang", LANG, "--apply"])
    assert [w.title for w in the_sheet(doorway).worksheets()] == ["prescreening"]


def test_the_manifest_records_where_the_sheet_is(env):
    doorway, run, saved = env
    run(["gen", "--lang", LANG, "--apply"])
    ss = the_sheet(doorway)
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    assert manifest[LANG]["biuniqueness_allomorphy_spreadsheet_id"] == ss.id
    assert manifest[LANG]["biuniqueness_allomorphy_url"] == ss.url


# ---------------------------------------------------------------------------
# What ends up on the sheet
# ---------------------------------------------------------------------------

def test_the_banner_sits_above_the_header_and_the_header_is_frozen(env):
    doorway, run, _ = env
    run(["gen", "--lang", LANG, "--apply"])
    ws = the_sheet(doorway).worksheet("prescreening")
    values = ws.get_all_values()
    header_row = next(i for i, row in enumerate(values) if row[0] == "Position_Name")
    assert header_row > 0, "the banner should come first"
    assert values[header_row] == gen._HEADER
    assert ws.frozen_rows == header_row + 1


def test_every_in_scope_element_gets_a_row_and_excluded_ones_do_not(env):
    doorway, run, _ = env
    out = run(["gen", "--lang", LANG, "--apply"])
    ws = the_sheet(doorway).worksheet("prescreening")
    values = ws.get_all_values()
    header_row = next(i for i, row in enumerate(values) if row[0] == "Position_Name")
    data = values[header_row + 1:]
    assert f"{len(data)} row(s)" in out
    assert {row[2] for row in data} == {"filled", "open_category"}


def test_the_annotation_columns_start_blank(env):
    """The coordinator and Adam fill these; nothing is pre-answered for them."""
    doorway, run, _ = env
    run(["gen", "--lang", LANG, "--apply"])
    ws = the_sheet(doorway).worksheet("prescreening")
    values = ws.get_all_values()
    header_row = next(i for i, row in enumerate(values) if row[0] == "Position_Name")
    for row in values[header_row + 1:]:
        assert row[3:] == ["", "", ""]       # has_allomorphs, Members, Notes


def test_the_dropdown_covers_the_has_allomorphs_column_and_only_the_data_rows(env):
    doorway, run, _ = env
    run(["gen", "--lang", LANG, "--apply"])
    ws = the_sheet(doorway).worksheet("prescreening")
    values = ws.get_all_values()
    header_row = next(i for i, row in enumerate(values) if row[0] == "Position_Name")
    col = gen._HEADER.index("has_allomorphs")

    assert ws._cell(header_row + 1, col).validation is not None
    rule = ws._cell(header_row + 1, col).validation
    assert [v["userEnteredValue"] for v in rule["condition"]["values"]] == ["y", "n"]
    # Not on the header, and not on the neighbouring columns.
    assert ws._cell(header_row, col).validation is None
    assert ws._cell(header_row + 1, col - 1).validation is None
    assert ws._cell(header_row + 1, col + 1).validation is None


def test_a_rerun_does_not_leave_rows_from_the_previous_structure_behind(env):
    """It clears before writing — a shrunk planar must not leave orphan rows."""
    doorway, run, _ = env
    run(["gen", "--lang", LANG, "--apply"])
    ws = the_sheet(doorway).worksheet("prescreening")
    ws.update([["LEFTOVER"]], f"A{len(ws.get_all_values()) + 5}")
    assert any("LEFTOVER" in row for row in ws.get_all_values())

    run(["gen", "--lang", LANG, "--apply"])
    ws = the_sheet(doorway).worksheet("prescreening")
    assert not any("LEFTOVER" in row for row in ws.get_all_values())


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------

def test_a_planar_without_the_scope_column_stops_with_the_fix(env, monkeypatch, tmp_path):
    doorway, run, _ = env
    coded = tmp_path / "coded_data" / LANG / "lang_setup"
    coded.mkdir(parents=True)
    (coded / f"planar_{LANG}.tsv").write_text(
        "Position_Number\tPosition_Name\tElements\n1\tv:leftedge\tand, also\n",
        encoding="utf-8")
    monkeypatch.setattr(gen, "CODED_DATA", tmp_path / "coded_data")

    out = run(["gen", "--lang", LANG, "--apply"])
    assert "no Biuniqueness_Scope column" in out
    assert "backfill" in out
    assert doorway.mutations == []


def test_a_language_with_no_drive_folder_stops_before_writing(env):
    doorway, run, _ = env
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    del manifest[LANG]["folder_id"]
    doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode()

    out = run(["gen", "--lang", LANG, "--apply"])
    assert "No Drive folder found" in out
    assert "generate-sheets --apply" in out
    assert doorway.mutations == []


def test_a_language_with_no_planar_stops_before_touching_drive(env):
    doorway, run, _ = env
    out = run(["gen", "--lang", "nyan1308", "--apply"])
    assert "No planar_nyan1308.tsv found" in out
    assert doorway.mutations == []


def test_no_lang_flag_is_refused(env):
    _, run, _ = env
    out = run(["gen", "--apply"])
    assert "Usage:" in out
