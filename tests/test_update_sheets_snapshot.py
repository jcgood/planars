"""Snapshot tests for `python -m coding update-sheets`, run against the fake.

File 11 of 18 migrated to the Drive doorway (#271), and the first one that
appends to the annotation sheets Adam is working in. Everything migrated before
this wrote to generated artifacts — dropdowns, reports, notebooks, the manifest,
the planar sheet. This one adds rows to the tabs holding the annotations
themselves, which are irreplaceable, so its promises are asserted structurally
rather than left to a reading of the transcript:

- the dry run writes nothing at all;
- `--apply` only ever *adds* — no cell that already had a value is rewritten,
  no row, column or tab is removed;
- a tab whose sheet disagrees with the planar structure is left alone entirely
  and the command stops with a non-zero exit;
- pair-row tabs never get rows appended, whatever the planar says;
- a second `--apply` appends nothing.

Before migrating, the old code was driven from this same stand-in Drive through
gspread-client and Drive-service shims, across twelve scenarios covering both
modes, both kinds of change, structural drift, a missing tab, a missing trailing
column, a new construction, and a language with no local planar. Stdout, the
mutation log, every tab of every spreadsheet, and the manifest all came back
byte-identical afterwards.

These snapshots first recorded three bugs and then, in the next commit, their
fixes — docs/data-layer-progress.md § Findings 9, 10 and 11. All three came of
the same thing: the manifest was treated as the authority on which columns a tab
has and how wide a new row should be, when the tab's own header is.

`CODED_DATA` is redirected into a temp tree in every test, for both this module
and `generate_sheets` (whose `_add_constructions_to_existing_sheet` reads the
planar from its own copy of the constant).

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_update_sheets_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable, Dict, List

import pandas as pd
import pytest
import yaml

from coding import drive as drive_module
from coding import drive_doorway
from coding import generate_sheets as gs
from coding import update_sheets as us
from fake_drive import FakeDriveDoorway, MANIFEST_FILE_ID
from render_mutations import render

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "update_sheets"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANGS = ["arao1248", "stan1293", "synth0001"]
NEW_ELEMENT = "zzz-new-element"

# The command reads each language's planar TSV and diagnostics YAML from
# coded_data/, a separate repo that a bare worktree may not have.
pytestmark = pytest.mark.skipif(
    not (ROOT / "coded_data").exists(),
    reason="coded_data/ (planars-data) is not checked out",
)


class Env:
    """One stand-in Drive, one private copy of the language setup files."""

    def __init__(self, doorway: FakeDriveDoorway, coded: Path,
                 clean_checks: List[dict], run: Callable[[List[str]], str]) -> None:
        self.doorway = doorway
        self.coded = coded
        self.clean_checks = clean_checks
        self.run = run

    # -- the manifest -------------------------------------------------------
    def manifest(self) -> Dict:
        return self.doorway.download_file_json(MANIFEST_FILE_ID)

    def sheet_id(self, lang: str, class_name: str) -> str:
        return self.manifest()[lang]["sheets"][class_name]["spreadsheet_id"]

    def tab(self, lang: str, class_name: str, construction: str):
        return self.doorway.spreadsheet(
            self.sheet_id(lang, class_name)).worksheet(construction)

    # -- the local planar ---------------------------------------------------
    def planar(self, lang: str) -> Path:
        return self.coded / lang / "lang_setup" / f"planar_{lang}.tsv"

    def edit_planar(self, lang: str, fn) -> None:
        df = pd.read_csv(self.planar(lang), sep="\t", dtype=str).fillna("")
        fn(df)
        df.to_csv(self.planar(lang), sep="\t", index=False)

    def add_element(self, lang: str) -> None:
        """One more element in the first position — the ordinary new-row case."""
        def edit(df):
            df.at[0, "Elements"] = df.at[0, "Elements"] + f", {NEW_ELEMENT}"
        self.edit_planar(lang, edit)

    def renumber_first_position(self, lang: str) -> None:
        """Structural drift: a position number the sheets do not have."""
        def edit(df):
            df.at[0, "Position"] = str(int(df.at[0, "Position"]) + 500)
        self.edit_planar(lang, edit)

    def add_construction(self, lang: str, class_name: str,
                         construction: str) -> None:
        """A construction in the diagnostics YAML the manifest has never seen."""
        path = self.coded / lang / "lang_setup" / f"diagnostics_{lang}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        entry = data["classes"][class_name]
        entry["constructions"] = list(entry.get("constructions", [])) + [construction]
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    # -- reading the stand-in Drive back ------------------------------------
    def all_tab_values(self) -> Dict:
        return {
            (ss_id, ws.title): ws.get_all_values()
            for ss_id, ss in self.doorway._spreadsheets.items()
            for ws in ss.worksheets()
        }


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        shutil.copytree(ROOT / "coded_data" / lang / "lang_setup",
                        coded / lang / "lang_setup")

    clean_checks: List[dict] = []

    monkeypatch.setattr(us, "CODED_DATA", coded)
    monkeypatch.setattr(gs, "CODED_DATA", coded)
    monkeypatch.setattr(us, "_check_coded_data_clean",
                        lambda **kw: clean_checks.append(kw))
    monkeypatch.setattr(us, "_load_drive_config", FakeDriveDoorway.drive_config)
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        FakeDriveDoorway.drive_config)
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                us.main()
        except SystemExit as exc:
            if exc.code:
                buf.write(f"[SystemExit: {exc.code}]\n")
        return buf.getvalue()

    try:
        yield Env(doorway, coded, clean_checks, run)
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


def captured_tabs() -> Dict:
    """Every tab as recorded by capture-drive-state, before any command ran."""
    index = json.loads(
        (ROOT / "tests" / "fixtures" / "drive_state" / "index.json").read_text())
    before = {}
    for entry in index["spreadsheets"]:
        data = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
        for tab in data["worksheets"]:
            before[(data["spreadsheet_id"], tab["title"])] = tab["values"]
    return before


def appended_rows(doorway) -> List[dict]:
    return [m for m in doorway.mutations if m["op"] == "append_rows"]


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    """Sheets as recorded against planars as committed — the "nothing to do" run."""
    check_snapshot("dry_run.txt", env.run(["update-sheets"]))


def test_dry_run_with_a_new_element_transcript(env):
    env.add_element("arao1248")
    check_snapshot("dry_run_changed.txt", env.run(["update-sheets"]))


def test_apply_transcript(env):
    env.add_element("arao1248")
    check_snapshot("apply.txt", env.run(["update-sheets", "--apply"]))


def test_apply_digest(env):
    """The rendered write log — tab titles and column headers resolved.

    This is the artifact to review, not the raw JSON: raw IDs and 0-based
    column indices hid one of the two bugs behind #272 through a first reading.
    """
    env.add_element("arao1248")
    env.run(["update-sheets", "--apply"])
    check_snapshot("apply_digest.txt", render(env.doorway.mutations))


def test_drift_transcript(env):
    """A renumbered position stops the command and names the way out."""
    env.renumber_first_position("arao1248")
    check_snapshot("drift.txt", env.run(["update-sheets"]))


def test_new_construction_transcript(env):
    env.add_construction("arao1248", "ciscategorial", "second_frame")
    check_snapshot("new_construction.txt", env.run(["update-sheets", "--apply"]))


def test_new_construction_dry_run_transcript(env):
    """The dry run names both consequences: a new tab, and a rewritten manifest."""
    env.add_construction("arao1248", "ciscategorial", "second_frame")
    check_snapshot("new_construction_dry_run.txt", env.run(["update-sheets"]))


def test_a_language_with_no_local_planar_is_named_not_skipped_silently(env):
    shutil.rmtree(env.coded / "synth0001")
    out = env.run(["update-sheets"])
    assert "[synth0001] No local planar file found — skipping" in out


def test_a_tab_the_sheet_does_not_have_is_named(env):
    ss = env.doorway.spreadsheet(env.sheet_id("arao1248", "ciscategorial"))
    ss.del_worksheet(ss.worksheet("general"))
    out = env.run(["update-sheets"])
    assert "[general] tab not found, skipping" in out


# ---------------------------------------------------------------------------
# The dry run writes nothing
# ---------------------------------------------------------------------------

def test_the_dry_run_changes_nothing_anywhere(env):
    env.add_element("arao1248")
    before = env.all_tab_values()

    env.run(["update-sheets"])

    assert env.doorway.mutations == []
    assert env.all_tab_values() == before


def test_the_dry_run_does_not_ask_whether_coded_data_is_clean(env):
    """The guard belongs to --apply. A dry run reads nothing it could corrupt."""
    env.run(["update-sheets"])
    assert env.clean_checks == []


def test_apply_refuses_to_read_a_half_written_planar(env):
    """The #248 guard: a stale planar is what wrote bogus rows to 16 live sheets."""
    env.run(["update-sheets", "--apply"])
    assert env.clean_checks == [{"extensions": (".tsv",)}]


# ---------------------------------------------------------------------------
# --apply only ever adds
# ---------------------------------------------------------------------------

def test_apply_with_nothing_to_do_leaves_every_tab_byte_identical(env):
    """It still writes notes and dropdowns, but not one cell value."""
    before = captured_tabs()

    env.run(["update-sheets", "--apply"])

    for (ss_id, title), values in before.items():
        assert env.doorway.spreadsheet(ss_id).worksheet(title).get_all_values() == values


def test_apply_never_rewrites_a_cell_that_already_had_a_value(env):
    """Adam's annotations are irreplaceable; this command may only append."""
    before = captured_tabs()
    env.add_element("stan1293")

    env.run(["update-sheets", "--apply"])

    for (ss_id, title), rows in before.items():
        after = env.doorway.spreadsheet(ss_id).worksheet(title).get_all_values()
        assert after[:len(rows)] == rows, f"{title} was rewritten, not appended to"


def test_apply_never_removes_a_row_a_column_or_a_tab(env):
    env.add_element("stan1293")

    env.run(["update-sheets", "--apply"])

    ops = {m["op"] for m in env.doorway.mutations}
    assert not ops & {"clear", "resize", "del_worksheet", "update_title"}
    request_types = {m["request_type"] for m in env.doorway.mutations
                     if m["op"] == "batch_request"}
    assert "deleteDimension" not in request_types


def test_the_appended_row_says_what_the_planar_says(env):
    env.add_element("arao1248")

    env.run(["update-sheets", "--apply"])

    rows = env.tab("arao1248", "ciscategorial", "general").get_all_values()
    assert rows[-1][:3] == [NEW_ELEMENT, "v:leftXP", "1"]
    assert all(cell == "" for cell in rows[-1][3:])


def test_a_keystone_row_is_added_with_na_not_blank(env):
    """A keystone carries real values elsewhere; here it must not read as unannotated."""
    def edit(df):
        keystone = df.index[df["Position_Name"] == "v:verbstem"][0]
        df.at[keystone, "Elements"] = df.at[keystone, "Elements"] + f", {NEW_ELEMENT}"
    env.edit_planar("stan1293", edit)

    env.run(["update-sheets", "--apply"])

    rows = env.tab("stan1293", "ciscategorial", "general").get_all_values()
    added = [r for r in rows if r[0] == NEW_ELEMENT]
    assert len(added) == 1
    assert added[0][1] == "v:verbstem"
    criteria = rows[0][3:rows[0].index("Source")]
    assert added[0][3:3 + len(criteria)] == ["NA"] * len(criteria)


def test_a_second_apply_appends_nothing(env):
    env.add_element("arao1248")
    env.run(["update-sheets", "--apply"])
    env.doorway.clear_mutations()

    out = env.run(["update-sheets", "--apply"])

    assert appended_rows(env.doorway) == []
    assert NEW_ELEMENT not in out


# ---------------------------------------------------------------------------
# What it refuses to touch
# ---------------------------------------------------------------------------

def test_a_drifted_tab_is_left_alone_and_the_command_stops(env):
    """Renumbering is restructure-sheets' job; guessing here would smear data."""
    before = captured_tabs()
    env.renumber_first_position("arao1248")

    out = env.run(["update-sheets", "--apply"])

    assert "[SystemExit: 1]" in out
    assert "python -m coding restructure-sheets --apply" in out
    for (ss_id, title), rows in before.items():
        if ss_id in {env.sheet_id("arao1248", c)
                     for c in env.manifest()["arao1248"]["sheets"]}:
            assert (env.doorway.spreadsheet(ss_id)
                    .worksheet(title).get_all_values() == rows)


def test_pair_row_tabs_never_get_rows_appended(env):
    """Their rows are pairs of elements, generated by --regen-construction.

    Pair-ness is taken from each tab's own header rather than from a list of
    class names, so this keeps holding while stan1293's `phrasal_accent/general`
    is still element-shaped and awaiting its rebuild (#275).
    """
    env.add_element("stan1293")

    out = env.run(["update-sheets", "--apply"])

    assert "up to date (pair-row tab — row updates skipped)" in out
    checked = 0
    for (ss_id, title), rows in env.all_tab_values().items():
        if not rows or not {"Element_A", "Element_B"} & set(rows[0]):
            continue
        checked += 1
        assert not any(NEW_ELEMENT in row for row in rows), f"{title} gained a row"
    assert checked, "no pair-row tab was exercised"


def test_a_dry_run_reporting_no_changes_exits_zero(env):
    out = env.run(["update-sheets"])
    assert "All sheets are up to date." in out
    assert "[SystemExit" not in out


def test_a_dry_run_with_changes_exits_non_zero(env):
    """Non-zero is what makes the daily workflow file a sheet-drift issue."""
    env.add_element("arao1248")
    out = env.run(["update-sheets"])
    assert "Run with --apply to make these changes." in out
    assert "[SystemExit: 1]" in out


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------

def test_the_manifest_is_only_rewritten_when_a_tab_was_added(env):
    env.add_element("arao1248")
    env.run(["update-sheets", "--apply"])
    assert env.doorway.mutations_of("update_file") == []


def test_a_new_construction_becomes_a_tab_and_reaches_the_manifest(env):
    env.add_construction("arao1248", "ciscategorial", "second_frame")

    env.run(["update-sheets", "--apply"])

    ss = env.doorway.spreadsheet(env.sheet_id("arao1248", "ciscategorial"))
    assert "second_frame" in [ws.title for ws in ss.worksheets()]

    entry = env.manifest()["arao1248"]["sheets"]["ciscategorial"]
    assert "second_frame" in entry["constructions"]
    assert "second_frame" in entry["construction_params"]
    assert [m["file_id"] for m in env.doorway.mutations_of("update_file")] \
        == [MANIFEST_FILE_ID]
    assert env.doorway.mutations_of("create_file") == []


def test_the_dry_run_says_it_would_add_the_tab_without_adding_it(env):
    env.add_construction("arao1248", "ciscategorial", "second_frame")

    out = env.run(["update-sheets"])

    assert "[second_frame] Would add new tab" in out
    assert env.doorway.mutations == []


def test_the_dry_run_says_the_manifest_would_change_too(env):
    """Finding 11, fixed. Adding a tab rewrites the manifest; say so up front.

    The line was written but unreachable — the flag that guards it was only
    ever set inside the --apply branch.
    """
    env.add_construction("arao1248", "ciscategorial", "second_frame")
    out = env.run(["update-sheets"])
    assert "Would update manifest on Drive (new tabs detected)." in out


def test_the_status_tab_stays_last(env):
    """Annotators read it as the summary; a Status tab in the middle is noise."""
    env.add_construction("arao1248", "ciscategorial", "second_frame")

    env.run(["update-sheets", "--apply"])

    ss = env.doorway.spreadsheet(env.sheet_id("arao1248", "ciscategorial"))
    assert [ws.title for ws in ss.worksheets()][-1] == "Status"


# ---------------------------------------------------------------------------
# Trailing columns
# ---------------------------------------------------------------------------

def test_a_missing_trailing_column_is_added_back_without_disturbing_the_rest(env):
    ws = env.tab("arao1248", "ciscategorial", "general")
    rows = ws.get_all_values()
    comments = rows[0].index("Comments")
    ws.clear()
    ws.update([row[:comments] + row[comments + 1:] for row in rows], "A1")
    env.doorway.clear_mutations()

    out = env.run(["update-sheets", "--apply"])

    assert "add trailing column(s): ['Comments']" in out
    after = env.tab("arao1248", "ciscategorial", "general").get_all_values()
    assert after == rows


# ---------------------------------------------------------------------------
# Findings 9 and 10 — the manifest is not the authority on a tab's columns
# ---------------------------------------------------------------------------

def test_appending_a_row_keeps_the_tabs_real_allowed_values(env):
    """Finding 9, fixed. Adding one row used to narrow every dropdown to y/n.

    segmental's criteria allow `both` and `na`. Validation is re-applied across
    every data row after an append, so a hardcoded [y, n] took two of the four
    options away on rows nobody had touched.
    """
    env.add_element("stan1293")

    env.run(["update-sheets", "--apply"])

    flapping = env.tab("stan1293", "segmental", "flapping")
    written = [m for m in env.doorway.mutations
               if m["op"] == "batch_request"
               and m["request_type"] == "setDataValidation"
               and m["payload"]["range"]["sheetId"] == flapping.id]
    assert written, "expected validation to be re-applied after the append"
    for m in written:
        values = [v["userEnteredValue"]
                  for v in m["payload"]["rule"]["condition"]["values"]]
        assert values == ["y", "n", "both", "na"]


def test_no_dropdown_is_ever_written_onto_source_or_comments(env):
    """The columns an annotator writes prose in are never given a value list."""
    env.add_element("stan1293")

    env.run(["update-sheets", "--apply"])

    for m in env.doorway.mutations:
        if m["op"] != "batch_request" or m["request_type"] != "setDataValidation":
            continue
        rng = m["payload"]["range"]
        ws = (env.doorway.spreadsheet(m["spreadsheet"])
              ._worksheet_by_sheet_id(rng["sheetId"]))
        header = ws.row_values(1)
        for col in range(rng["startColumnIndex"], rng["endColumnIndex"]):
            assert header[col] not in ("Source", "Comments")


def test_header_notes_are_placed_from_the_header_not_the_manifest(env):
    """Finding 10, fixed. Same shape as #272 bug 2, in a different command.

    synth0001's coreference prescreening tab has one criterion column,
    `referential`; the manifest still lists the three pair criteria. Written at
    manifest positions, two of the notes landed on Source and Comments.
    """
    env.run(["update-sheets", "--apply"])

    ws = env.tab("synth0001", "coreference", "prescreening")
    noted = [m for m in env.doorway.mutations
             if m["op"] == "batch_request" and m["request_type"] == "repeatCell"
             and m["payload"]["range"]["sheetId"] == ws.id
             and "note" in m["payload"].get("cell", {})]
    header = ws.row_values(1)
    columns = [header[m["payload"]["range"]["startColumnIndex"]] for m in noted]
    assert columns == ["referential"]


def test_a_keystone_row_writes_na_only_into_criterion_columns(env):
    """Part of finding 9's family: the row's width came from the manifest too.

    Where the manifest listed more criteria than the tab has, a keystone row
    carried NA past the last criterion and into Source and Comments.
    """
    def edit(df):
        keystone = df.index[df["Position_Name"] == "v:verbstem"][0]
        df.at[keystone, "Elements"] = df.at[keystone, "Elements"] + f", {NEW_ELEMENT}"
    env.edit_planar("synth0001", edit)

    env.run(["update-sheets", "--apply"])

    ws = env.tab("synth0001", "coreference", "prescreening")
    rows = ws.get_all_values()
    added = [r for r in rows if r[0] == NEW_ELEMENT]
    assert len(added) == 1
    assert added[0] == [NEW_ELEMENT, "v:verbstem", "30", "NA", "", ""]
