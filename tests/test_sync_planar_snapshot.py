"""Snapshot tests for `python -m coding sync-planar`, run against the fake.

`planar_{lang_id}.tsv` is the planar's one editable home and the planar
Sheet a read-only copy of it (Phase 10 unit 11b, 2026-10-24). The command's
promises:

- the Sheet ends up holding exactly the file, no rows left over from a
  longer previous version, and it is protected;
- it never writes a language's files (only its own renumbering record);
- what changed since the last push is worked out from the Sheet, which still
  holds that push, and written to `PLANAR_CHANGES_PATH` for the daily
  refresh's `planar-changed` issue, with the command that carries it into
  the class sheets.

Renumbering the position numbers typed in answers is in
tests/test_position_cells.py. Until 2026-10-24 this file tested
`import-planar`, which also read the Sheet back into the file; the round trip
between the two copies was the shape of #248.

`CODED_DATA` is redirected into a temp tree in every test, and so is
`PLANAR_CHANGES_PATH`.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_sync_planar_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable, List

import pandas as pd
import pytest

from coding import drive as drive_module
from coding import drive_doorway, file_door
from coding import sync_planar as sp
from coding.locked_tabs import PROTECTION_DESCRIPTION
from command_runner import run_command
from fake_drive import FROZEN_CODED_DATA, FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "sync_planar"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANG = "stan1293"
LANGS = ["arao1248", "stan1293", "synth0001"]
PLANAR_ID = {
    "arao1248": "1hM2L5bLbt8gsOdb4FgMc0uS2652Gia1W66FrpJuVuPI",
    "stan1293": "1nmaNay3ne53-Gkm4wBTOy7vebYcX70WPvCwfvjT5Tc0",
    "synth0001": "16OFIc1O-RkT9Ex9pZajA2h1G4c8F-SYbAz3OX6hpIgs",
}


class Env:
    """One stand-in Drive, one private copy of the planar files, one command."""

    def __init__(self, doorway: FakeDriveDoorway, coded: Path, config: dict,
                 changes_path: Path, autocommits: List[dict],
                 run: Callable[[List[str]], str]) -> None:
        self.doorway = doorway
        self.coded = coded
        self.config = config
        self.changes_path = changes_path
        self.autocommits = autocommits
        self.run = run

    def tsv(self, lang: str = LANG) -> Path:
        return self.coded / lang / "lang_setup" / f"planar_{lang}.tsv"

    def tsv_rows(self, lang: str = LANG) -> List[List[str]]:
        """Header row then data rows, read the way the command reads it."""
        df = pd.read_csv(self.tsv(lang), sep="\t", dtype=str, keep_default_na=False)
        return [list(df.columns)] + [[str(v) for v in row] for _, row in df.iterrows()]

    def write_tsv_rows(self, rows: List[List[str]], lang: str = LANG) -> None:
        pd.DataFrame(rows[1:], columns=rows[0]).to_csv(self.tsv(lang), sep="\t", index=False)

    def sheet(self, lang: str = LANG):
        return self.doorway.spreadsheet(PLANAR_ID[lang]).sheet1

    def sheet_rows(self, lang: str = LANG) -> List[List[str]]:
        return self.sheet(lang).get_all_values()

    def protected(self, lang: str = LANG) -> bool:
        ss = self.doorway.spreadsheet(PLANAR_ID[lang])
        ws = ss.sheet1
        return any(p.get("description") == PROTECTION_DESCRIPTION
                   for p in ss.list_protected_ranges(ws.id))

    def writes(self) -> list:
        """The Drive writes made (the fake records writes only)."""
        return list(self.doorway.mutations)


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        dest = coded / lang / "lang_setup"
        dest.mkdir(parents=True)
        src = FROZEN_CODED_DATA / lang / "lang_setup" / f"planar_{lang}.tsv"
        shutil.copy2(src, dest / src.name)

    # The recorded ID file, so renumbering finds the recorded class sheets.
    config = dict(FakeDriveDoorway.drive_config())
    for lang in LANGS:
        config.setdefault(lang, {}).update({"folder_id": f"folder_{lang}",
                                            "planar_spreadsheet_id": PLANAR_ID[lang]})

    changes_path = tmp_path / "planar_changes.json"
    autocommits: List[dict] = []

    monkeypatch.setattr(sp, "CODED_DATA", coded)
    monkeypatch.setattr(sp, "PLANAR_CHANGES_PATH", changes_path)
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(
        file_door, "_commit",
        lambda run: autocommits.append({"paths": [p.name for p in dict.fromkeys(run.written)]}))
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                run_command(sp, "sync-planar")
        except SystemExit as exc:
            if exc.code:
                buf.write(f"[SystemExit: {exc.code}]\n")
        return buf.getvalue()

    try:
        yield Env(doorway, coded, config, changes_path, autocommits, run)
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


# ---------------------------------------------------------------------------
# Edits to the planar file
# ---------------------------------------------------------------------------

def add_position(rows: List[List[str]]) -> List[List[str]]:
    """One more position on the right, numbered after the current last."""
    numbers = [int(r[2]) for r in rows[1:] if r[2].strip().isdigit()]
    added = list(rows[-1])
    added[2], added[4], added[5] = str(max(numbers) + 1), "x:newpos", "-new"
    return rows + [added[:len(rows[0])]]


def drop_last_position(rows: List[List[str]]) -> List[List[str]]:
    return rows[:-1]


NEW_COLUMN = "Test_New_Column"


def add_column(rows: List[List[str]]) -> List[List[str]]:
    assert NEW_COLUMN not in rows[0]
    return [row + [NEW_COLUMN if i == 0 else "filled"] for i, row in enumerate(rows)]


def drop_notes_column(rows: List[List[str]]) -> List[List[str]]:
    notes = rows[0].index("Notes")
    return [row[:notes] + row[notes + 1:] for row in rows]


def edit_a_note(rows: List[List[str]]) -> List[List[str]]:
    rows = [list(r) for r in rows]
    rows[1][8] = "a note that was not there before"
    return rows


def three_languages_changed(env: Env) -> None:
    """One addition, one deletion, one content-only edit, all in the files."""
    env.write_tsv_rows(add_position(env.tsv_rows("arao1248")), "arao1248")
    env.write_tsv_rows(drop_last_position(env.tsv_rows(LANG)), LANG)
    env.write_tsv_rows(edit_a_note(env.tsv_rows("synth0001")), "synth0001")


def protect_all(env: Env) -> None:
    """Every Sheet protected, so a test sees only the content writes."""
    env.run(["sync-planar", "--apply"])
    env.doorway.clear_mutations()
    env.autocommits.clear()
    env.changes_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    """Every language, files and Sheets as recorded: nothing to do."""
    check_snapshot("dry_run.txt", env.run(["sync-planar"]))


def test_dry_run_with_changes_transcript(env):
    """Each kind of change names the command that would handle it."""
    protect_all(env)
    three_languages_changed(env)
    check_snapshot("dry_run_changed.txt", env.run(["sync-planar"]))


def test_apply_transcript(env):
    protect_all(env)
    three_languages_changed(env)
    check_snapshot("apply.txt", env.run(["sync-planar", "--apply"]))


def test_skips_transcript(env):
    """The ways a language is passed over, in one run — each one named."""
    env.tsv("arao1248").unlink()
    env.config[LANG].pop("planar_spreadsheet_id")
    check_snapshot("skips.txt", env.run(["sync-planar", "--apply"]))


def test_column_changes_transcript(env):
    """One file gains a column, one loses one: both named before the write."""
    protect_all(env)
    env.write_tsv_rows(add_column(env.tsv_rows("arao1248")), "arao1248")
    env.write_tsv_rows(drop_notes_column(env.tsv_rows(LANG)), LANG)
    check_snapshot("columns.txt", env.run(["sync-planar", "--apply"]))


# ---------------------------------------------------------------------------
# The Sheet becomes the file, and only the Sheet is written
# ---------------------------------------------------------------------------

def test_the_dry_run_changes_nothing_anywhere(env):
    three_languages_changed(env)
    before_local = {lang: env.tsv_rows(lang) for lang in LANGS}
    before_sheets = {lang: env.sheet_rows(lang) for lang in LANGS}

    env.run(["sync-planar"])

    assert env.writes() == []
    assert {lang: env.tsv_rows(lang) for lang in LANGS} == before_local
    assert {lang: env.sheet_rows(lang) for lang in LANGS} == before_sheets
    assert env.autocommits == []
    assert not env.changes_path.exists()


def test_apply_makes_each_sheet_hold_exactly_its_file(env):
    three_languages_changed(env)
    env.run(["sync-planar", "--apply"])
    for lang in LANGS:
        assert env.sheet_rows(lang) == env.tsv_rows(lang)


def test_a_shorter_file_leaves_no_rows_behind_in_the_sheet(env):
    """It clears before writing. Otherwise a retired position would live on."""
    env.write_tsv_rows(drop_last_position(env.tsv_rows()))
    env.run(["sync-planar", "--lang", LANG, "--apply"])
    assert env.sheet_rows() == env.tsv_rows()


def test_a_column_removed_from_the_file_leaves_the_sheet(env):
    env.write_tsv_rows(drop_notes_column(env.tsv_rows()))
    out = env.run(["sync-planar", "--lang", LANG, "--apply"])
    assert "- column Notes" in out
    assert "Notes" not in env.sheet_rows()[0]


def test_apply_never_writes_a_language_file(env):
    three_languages_changed(env)
    before = {lang: env.tsv(lang).read_bytes() for lang in LANGS}

    env.run(["sync-planar", "--apply"])

    assert {lang: env.tsv(lang).read_bytes() for lang in LANGS} == before
    assert not list(env.coded.glob("*/archive/**/*.tsv"))
    assert not list(env.coded.glob("*/changes.tsv"))


def test_a_second_apply_is_a_no_op(env):
    three_languages_changed(env)
    env.run(["sync-planar", "--apply"])
    env.doorway.clear_mutations()
    env.changes_path.unlink()

    out = env.run(["sync-planar", "--apply"])

    assert out.count("up to date") == len(LANGS)
    assert env.writes() == []
    assert not env.changes_path.exists()


def test_each_sheet_is_protected_once_even_when_up_to_date(env):
    """A Sheet made before unit 11b is protected by the next run, and a
    protected one is left alone."""
    for lang in LANGS:                    # as recorded before 2026-10-24
        env.doorway.spreadsheet(PLANAR_ID[lang])._protected_ranges.clear()
    assert not any(env.protected(lang) for lang in LANGS)

    out = env.run(["sync-planar", "--apply"])

    assert out.count("protected the planar Sheet") == len(LANGS)
    assert all(env.protected(lang) for lang in LANGS)
    assert all(env.sheet_rows(lang) == env.tsv_rows(lang) for lang in LANGS)
    env.doorway.clear_mutations()
    env.run(["sync-planar", "--apply"])
    assert env.writes() == []


def test_the_recorded_changes_name_every_language_that_moved(env):
    """`planar_changes.json` is what the daily run turns into the issue body."""
    three_languages_changed(env)
    env.run(["sync-planar", "--apply"])

    changes = json.loads(env.changes_path.read_text())
    assert sorted(changes) == LANGS
    assert changes["arao1248"]["diff"]["added"] == {"19": "x:newpos"}
    assert changes[LANG]["diff"]["deleted"] == {"38": "v:rightedge"}
    assert changes["synth0001"]["recommendation"].startswith("(content-only")


def test_one_language_at_a_time_leaves_the_others_untouched(env):
    three_languages_changed(env)
    before = {lang: env.sheet_rows(lang) for lang in LANGS if lang != LANG}

    env.run(["sync-planar", "--lang", LANG, "--apply"])

    assert {lang: env.sheet_rows(lang) for lang in before} == before
    assert list(json.loads(env.changes_path.read_text())) == [LANG]


def test_one_unreachable_sheet_does_not_stop_the_others(env):
    for lang in LANGS:
        env.write_tsv_rows(add_position(env.tsv_rows(lang)), lang)
    del env.doorway._spreadsheets[PLANAR_ID[LANG]]

    out = env.run(["sync-planar", "--apply"])

    assert f"{LANG}\n  ERROR reading the planar Sheet" in out
    for lang in ("arao1248", "synth0001"):
        assert env.sheet_rows(lang) == env.tsv_rows(lang)
