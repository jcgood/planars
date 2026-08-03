"""Snapshot tests for `python -m coding import-planar`, run against the fake.

File 9 of 18 migrated to the Drive doorway (#271), and the first that both
reads *and* writes the planar spreadsheet — the sheet that says which positions
a language has and which elements sit in them. It is also the command at the
centre of #248, where a local planar edit was silently reverted by the next
scheduled run, so its two directions are exactly the pair worth pinning down:

- **Sheet → TSV** (the default) treats the Sheet as the source of truth. Its
  promise is that it never writes to Drive at all, and never blanks a local
  planar from a Sheet it could not read.
- **TSV → Sheet** (`--to-sheet`) is the reverse, used after a local edit. Its
  promise is that it never writes locally, and that the Sheet ends up matching
  the TSV exactly — no rows left over from a longer previous version.

Together they must round-trip: pushing a local planar up and importing it back
returns the file unchanged. That is the property whose absence #248 exploited.

Before migrating, the old code was driven from this same stand-in Drive through
shims, across thirty scenarios covering both directions. Output, the local file
tree, the sheets' contents, the recorded Drive changes, the auto-commit and
`planar_changes.json` all came back byte-identical afterwards.

`CODED_DATA` is redirected into a temp tree in every test — this command
overwrites planar TSVs — and so is `PLANAR_CHANGES_PATH`, which in real use is
the file the data-refresh workflow reads to build the `planar-changed` issue.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_import_planar_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List

import pandas as pd
import pytest

from coding import drive as drive_module
from coding import drive_doorway
from coding import import_planar as ip
from fake_drive import FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "import_planar"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANG = "stan1293"
LANGS = ["arao1248", "stan1293", "synth0001"]
PLANAR_ID = {
    "arao1248": "1hM2L5bLbt8gsOdb4FgMc0uS2652Gia1W66FrpJuVuPI",
    "stan1293": "1nmaNay3ne53-Gkm4wBTOy7vebYcX70WPvCwfvjT5Tc0",
    "synth0001": "16OFIc1O-RkT9Ex9pZajA2h1G4c8F-SYbAz3OX6hpIgs",
}

# The archive filename and the auto-commit message both carry a timestamp, so
# the clock is pinned. Frozen rather than stripped: the timestamp linking a TSV
# to its archived predecessor is part of what these snapshots record.
FROZEN = datetime(2026, 8, 2, 11, 22, 33, tzinfo=timezone.utc)


class _FrozenDatetime:
    @staticmethod
    def now(tz=None):
        return FROZEN if tz is None else FROZEN.astimezone(tz)


class Env:
    """One stand-in Drive, one private copy of the planar TSVs, one command."""

    def __init__(self, doorway: FakeDriveDoorway, coded: Path, config: dict,
                 changes_path: Path, autocommits: List[dict],
                 run: Callable[[List[str]], str]) -> None:
        self.doorway = doorway
        self.coded = coded
        self.config = config
        self.changes_path = changes_path
        self.autocommits = autocommits
        self.run = run

    # -- local planar TSVs --------------------------------------------------
    def tsv(self, lang: str = LANG) -> Path:
        return self.coded / lang / "lang_setup" / f"planar_{lang}.tsv"

    def tsv_rows(self, lang: str = LANG) -> List[List[str]]:
        """Header row then data rows, read the way the command reads it.

        Through pandas rather than by splitting on tabs: a planar cell holding
        a comma-separated element list is written quoted, and a naive split
        would report the quotes as a difference from the Sheet.
        """
        df = pd.read_csv(self.tsv(lang), sep="\t", dtype=str).fillna("")
        return [list(df.columns)] + [[str(v) for v in row]
                                     for _, row in df.iterrows()]

    def write_tsv_rows(self, rows: List[List[str]], lang: str = LANG) -> None:
        pd.DataFrame(rows[1:], columns=rows[0]).to_csv(
            self.tsv(lang), sep="\t", index=False)

    def archives(self, lang: str = LANG) -> List[Path]:
        return sorted((self.coded / lang / "archive" / "lang_setup").glob("*.tsv"))

    # -- the planar sheet ---------------------------------------------------
    def sheet(self, lang: str = LANG):
        return self.doorway.spreadsheet(PLANAR_ID[lang]).sheet1

    def sheet_rows(self, lang: str = LANG) -> List[List[str]]:
        return self.sheet(lang).get_all_values()

    def write_sheet_rows(self, rows: List[List[str]], lang: str = LANG) -> None:
        ws = self.sheet(lang)
        ws.clear()
        ws.update(rows, "A1")
        self.doorway.clear_mutations()


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()

    coded = tmp_path / "coded_data"
    for lang in LANGS:
        dest = coded / lang / "lang_setup"
        dest.mkdir(parents=True)
        src = ROOT / "coded_data" / lang / "lang_setup" / f"planar_{lang}.tsv"
        shutil.copy2(src, dest / src.name)

    config = {"_root_folder_id": "root", "_planars_config_file_id": "manifest"}
    for lang in LANGS:
        config[lang] = {"folder_id": f"folder_{lang}",
                        "planar_spreadsheet_id": PLANAR_ID[lang]}

    changes_path = tmp_path / "planar_changes.json"
    autocommits: List[dict] = []

    monkeypatch.setattr(ip, "CODED_DATA", coded)
    monkeypatch.setattr(ip, "PLANAR_CHANGES_PATH", changes_path)
    monkeypatch.setattr(ip, "datetime", _FrozenDatetime)
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(
        drive_module, "_autocommit_data",
        lambda paths, message: autocommits.append(
            {"paths": [p.name for p in paths], "message": message}))
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                ip.main()
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
# Edits used to make one side disagree with the other
# ---------------------------------------------------------------------------

def add_position(rows: List[List[str]]) -> List[List[str]]:
    """One more position on the right, numbered after the current last."""
    numbers = [int(r[2]) for r in rows[1:] if r[2].strip().isdigit()]
    added = list(rows[-1])
    added[2], added[4], added[5] = str(max(numbers) + 1), "x:newpos", "-new"
    return rows + [added[:len(rows[0])]]


def drop_last_position(rows: List[List[str]]) -> List[List[str]]:
    return rows[:-1]


def rename_position(rows: List[List[str]]) -> List[List[str]]:
    rows = [list(r) for r in rows]
    rows[3][4] = "x:renamed"
    return rows


def edit_a_note(rows: List[List[str]]) -> List[List[str]]:
    rows = [list(r) for r in rows]
    rows[1][8] = "a note that was not there before"
    return rows


def three_languages_changed(env: Env) -> None:
    """One structural addition, one deletion, one content-only edit."""
    env.write_sheet_rows(add_position(env.sheet_rows("arao1248")), "arao1248")
    env.write_sheet_rows(drop_last_position(env.sheet_rows(LANG)), LANG)
    env.write_sheet_rows(edit_a_note(env.sheet_rows("synth0001")), "synth0001")


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    """Every language, sheets as recorded — the ordinary "nothing to do" run."""
    check_snapshot("dry_run.txt", env.run(["import-planar"]))


def test_dry_run_with_changes_transcript(env):
    """Each kind of change names the command that would handle it."""
    three_languages_changed(env)
    check_snapshot("dry_run_changed.txt", env.run(["import-planar"]))


def test_apply_transcript(env):
    three_languages_changed(env)
    check_snapshot("apply.txt", env.run(["import-planar", "--apply"]))


def test_to_sheet_dry_run_transcript(env):
    env.write_tsv_rows(add_position(env.tsv_rows()))
    check_snapshot("to_sheet_dry_run.txt", env.run(["import-planar", "--to-sheet"]))


def test_to_sheet_apply_transcript(env):
    env.write_tsv_rows(add_position(env.tsv_rows()))
    check_snapshot("to_sheet_apply.txt",
                   env.run(["import-planar", "--to-sheet", "--apply"]))


def test_skips_transcript(env):
    """The three ways a language is passed over, in one run."""
    env.tsv("arao1248").unlink()
    env.config[LANG].pop("planar_spreadsheet_id")
    env.sheet("synth0001").clear()
    env.doorway.clear_mutations()
    check_snapshot("skips.txt", env.run(["import-planar", "--apply"]))


# ---------------------------------------------------------------------------
# Sheet → TSV: never writes to Drive
# ---------------------------------------------------------------------------

def test_the_dry_run_changes_nothing_anywhere(env):
    three_languages_changed(env)
    before_local = {lang: env.tsv_rows(lang) for lang in LANGS}
    before_sheets = {lang: env.sheet_rows(lang) for lang in LANGS}

    env.run(["import-planar"])

    assert env.doorway.mutations == []
    assert {lang: env.tsv_rows(lang) for lang in LANGS} == before_local
    assert {lang: env.sheet_rows(lang) for lang in LANGS} == before_sheets
    assert env.autocommits == []
    assert not env.changes_path.exists()


def test_apply_never_writes_to_the_planar_sheet(env):
    """The download direction is one-way. #248 was a write landing where a read belonged."""
    three_languages_changed(env)
    before_sheets = {lang: env.sheet_rows(lang) for lang in LANGS}

    env.run(["import-planar", "--apply"])

    assert env.doorway.mutations == []
    assert {lang: env.sheet_rows(lang) for lang in LANGS} == before_sheets


def test_apply_archives_the_old_tsv_before_overwriting(env):
    before = env.tsv(LANG).read_text(encoding="utf-8")
    three_languages_changed(env)

    env.run(["import-planar", "--apply"])

    archived = env.archives(LANG)
    assert [p.name for p in archived] == [f"planar_{LANG}_20260802_112233.tsv"]
    assert archived[0].read_text(encoding="utf-8") == before
    assert env.tsv(LANG).read_text(encoding="utf-8") != before


def test_apply_leaves_the_tsv_saying_what_the_sheet_says(env):
    three_languages_changed(env)
    env.run(["import-planar", "--apply"])
    for lang in LANGS:
        assert env.tsv_rows(lang) == env.sheet_rows(lang)


def test_a_second_apply_is_a_no_op(env):
    three_languages_changed(env)
    env.run(["import-planar", "--apply"])
    env.autocommits.clear()
    env.changes_path.unlink()

    out = env.run(["import-planar", "--apply"])

    assert out.count("up to date") == len(LANGS)
    assert env.autocommits == []
    assert not env.changes_path.exists()
    assert len(env.archives(LANG)) == 1          # no second archive copy


def test_an_empty_sheet_does_not_wipe_the_local_planar(env):
    """A sheet that reads back empty is a fault, not an instruction to delete."""
    before = env.tsv_rows(LANG)
    env.sheet(LANG).clear()
    env.doorway.clear_mutations()

    out = env.run(["import-planar", "--apply"])

    assert "planar sheet is empty — skipping" in out
    assert env.tsv_rows(LANG) == before
    assert env.archives(LANG) == []


def test_an_unreachable_sheet_leaves_that_planar_alone_and_does_not_stop_the_rest(env):
    three_languages_changed(env)
    before = env.tsv_rows(LANG)
    del env.doorway._spreadsheets[PLANAR_ID[LANG]]

    out = env.run(["import-planar", "--apply"])

    assert f"{LANG}\n  ERROR reading planar sheet" in out
    assert env.tsv_rows(LANG) == before
    assert env.tsv_rows("arao1248") == env.sheet_rows("arao1248")
    assert sorted(json.loads(env.changes_path.read_text())) == ["arao1248", "synth0001"]


def test_the_recorded_changes_name_every_language_that_moved(env):
    """`planar_changes.json` is what the daily run turns into the issue body."""
    three_languages_changed(env)
    env.run(["import-planar", "--apply"])

    changes = json.loads(env.changes_path.read_text())
    assert sorted(changes) == LANGS
    assert changes["arao1248"]["diff"]["added"] == {"19": "x:newpos"}
    assert changes[LANG]["diff"]["deleted"] == {"38": "v:rightedge"}
    assert changes["synth0001"]["recommendation"].startswith("(content-only")
    assert env.autocommits == [{
        "paths": [f"planar_{lang}{suffix}.tsv" for lang in LANGS
                  for suffix in ("", "_20260802_112233")],
        "message": ("data: import planar for arao1248, stan1293, synth0001 "
                    "from Google Sheets 2026-08-02"),
    }]


def test_one_language_at_a_time_leaves_the_others_untouched(env):
    three_languages_changed(env)
    before = {lang: env.tsv_rows(lang) for lang in LANGS if lang != LANG}

    env.run(["import-planar", "--lang", LANG, "--apply"])

    assert {lang: env.tsv_rows(lang) for lang in before} == before
    assert list(json.loads(env.changes_path.read_text())) == [LANG]


# ---------------------------------------------------------------------------
# TSV → Sheet: never writes locally
# ---------------------------------------------------------------------------

def test_the_to_sheet_dry_run_changes_nothing_anywhere(env):
    env.write_tsv_rows(add_position(env.tsv_rows()))
    before_local = {lang: env.tsv_rows(lang) for lang in LANGS}
    before_sheets = {lang: env.sheet_rows(lang) for lang in LANGS}

    env.run(["import-planar", "--to-sheet"])

    assert env.doorway.mutations == []
    assert {lang: env.tsv_rows(lang) for lang in LANGS} == before_local
    assert {lang: env.sheet_rows(lang) for lang in LANGS} == before_sheets


def test_to_sheet_apply_makes_the_sheet_match_the_tsv(env):
    env.write_tsv_rows(add_position(env.tsv_rows()))
    env.run(["import-planar", "--to-sheet", "--apply"])
    assert env.sheet_rows() == env.tsv_rows()


def test_a_shorter_tsv_leaves_no_rows_behind_in_the_sheet(env):
    """It clears before writing. Otherwise a retired position would live on."""
    env.write_tsv_rows(drop_last_position(env.tsv_rows()))
    env.run(["import-planar", "--to-sheet", "--apply"])
    assert env.sheet_rows() == env.tsv_rows()


def test_to_sheet_apply_writes_nothing_locally(env):
    env.write_tsv_rows(add_position(env.tsv_rows()))
    before = {lang: env.tsv_rows(lang) for lang in LANGS}

    env.run(["import-planar", "--to-sheet", "--apply"])

    assert {lang: env.tsv_rows(lang) for lang in LANGS} == before
    assert env.archives(LANG) == []
    assert env.autocommits == []


def test_a_second_to_sheet_apply_is_a_no_op(env):
    env.write_tsv_rows(add_position(env.tsv_rows()))
    env.run(["import-planar", "--to-sheet", "--apply"])
    env.doorway.clear_mutations()

    out = env.run(["import-planar", "--to-sheet", "--apply"])

    assert out.count("Sheet already up to date") == len(LANGS)
    assert env.doorway.mutations == []


def test_a_sheet_that_already_agrees_is_not_rewritten(env):
    """No churn, and no revision in the Sheet's history saying nothing changed."""
    out = env.run(["import-planar", "--to-sheet", "--apply"])
    assert out.count("Sheet already up to date") == len(LANGS)
    assert env.doorway.mutations == []


def test_one_unreachable_sheet_does_not_stop_the_others(env):
    for lang in LANGS:
        env.write_tsv_rows(add_position(env.tsv_rows(lang)), lang)
    del env.doorway._spreadsheets[PLANAR_ID[LANG]]

    out = env.run(["import-planar", "--to-sheet", "--apply"])

    assert f"[{LANG}] ERROR reading planar sheet" in out
    for lang in ("arao1248", "synth0001"):
        assert env.sheet_rows(lang) == env.tsv_rows(lang)


# ---------------------------------------------------------------------------
# The two directions agree — the property #248 needed
# ---------------------------------------------------------------------------

def test_a_local_edit_pushed_up_survives_the_next_import(env):
    """Push, then import. #248 was this round trip failing in the second half."""
    edited = add_position(env.tsv_rows())
    env.write_tsv_rows(edited)

    env.run(["import-planar", "--to-sheet", "--lang", LANG, "--apply"])
    out = env.run(["import-planar", "--lang", LANG, "--apply"])

    assert "up to date" in out
    assert env.tsv_rows() == edited
    assert env.archives(LANG) == []          # nothing was overwritten, so nothing archived


def test_an_import_followed_by_a_push_leaves_the_sheet_alone(env):
    """The other order. Neither direction may ping-pong the two copies."""
    three_languages_changed(env)
    before_sheets = {lang: env.sheet_rows(lang) for lang in LANGS}

    env.run(["import-planar", "--apply"])
    out = env.run(["import-planar", "--to-sheet", "--apply"])

    assert out.count("Sheet already up to date") == len(LANGS)
    assert {lang: env.sheet_rows(lang) for lang in LANGS} == before_sheets
