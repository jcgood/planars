"""Snapshot tests for `python -m coding sync-diagnostics-yaml --to-sheet`.

File 8 of 18 migrated to the Drive doorway (#271), and the first that writes to
a *reference* sheet — one nobody annotates, holding the list of classes,
constructions and criteria a language is being coded for.

The YAML is the source of truth and the Sheet is a copy of it, so what has to
hold is that the copy only ever moves toward the YAML:

- the dry run touches nothing;
- a sheet that already agrees is left alone rather than rewritten;
- an apply makes the sheet match the YAML exactly, with no rows left over from
  a longer previous version;
- a YAML with errors in it never reaches the sheet, so a broken edit cannot
  wipe the live copy;
- one unreachable sheet does not stop the other languages.

Before migrating, the old code was driven from this same stand-in Drive through
shims, across fifteen scenarios covering both directions of the command.
Output, the sheets' contents and the recorded Drive changes came back
byte-identical afterwards.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_sync_diagnostics_yaml_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import sys
import textwrap
from contextlib import redirect_stdout
from pathlib import Path
from typing import List

import pytest
import yaml

from coding import drive as drive_module
from coding import drive_doorway
from coding import sync_diagnostics_yaml as sdy
from coding.make_forms import _yaml_to_tsv_df
from fake_drive import MANIFEST_FILE_ID, ROOT_FOLDER_ID, FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "sync_diagnostics_yaml"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANG = "stan1293"
DIAG_ID = {
    "arao1248": "1A0r232Wdi3bpBj7ZcIPVcrSi9uQ9z0mc-7TYQfluO-s",
    "stan1293": "1lFgsWrMO5mS4meixITG51T3JcmfW3UcIvfxK_ohyg3Q",
    "synth0001": "1L-J3EWgZRMnqIaaXmlpBAVZt98wgmbdlyI2DhJOHhjQ",
}


@pytest.fixture()
def env(monkeypatch):
    """A stand-in Drive holding the three recorded diagnostics sheets.

    Yields (doorway, run). `run(argv)` plays one command and returns its output.
    """
    doorway = FakeDriveDoorway.from_fixtures()
    config = {"_planars_config_file_id": MANIFEST_FILE_ID,
              "_root_folder_id": ROOT_FOLDER_ID}
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                sdy.main()
        except SystemExit as exc:
            buf.write(f"[SystemExit: {exc.code}]\n")
        return buf.getvalue()

    try:
        yield doorway, run
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


def sheet(doorway, lang=LANG):
    return doorway.spreadsheet(DIAG_ID[lang]).sheet1


def yaml_rows(lang=LANG) -> List[List[str]]:
    """What the sheet should say, straight from the language's YAML."""
    path = sdy.CODED_DATA / lang / "lang_setup" / f"diagnostics_{lang}.yaml"
    df = _yaml_to_tsv_df(yaml.safe_load(path.read_text(encoding="utf-8")), lang)
    return [list(df.columns)] + [[str(v) for v in row] for _, row in df.iterrows()]


def make_stale(doorway, lang=LANG) -> None:
    """Make the sheet disagree with the YAML three ways at once."""
    ws = sheet(doorway, lang)
    rows = ws.get_all_values()
    rows[1][0] = "a_class_the_yaml_never_heard_of"    # one class removed, one added
    rows[2][-1] = "not, the, real, criteria"          # one class changed
    ws.clear()
    ws.update(rows[:-1], "A1")                        # and one class missing
    doorway.clear_mutations()


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    """Every language, sheets as recorded — the ordinary "nothing to do" run."""
    _, run = env
    check_snapshot("dry_run.txt", run(["sdy", "--to-sheet"]))


def test_dry_run_against_a_stale_sheet_transcript(env):
    """Names the classes that would be removed, added and changed."""
    doorway, run = env
    make_stale(doorway)
    check_snapshot("dry_run_stale.txt", run(["sdy", "--to-sheet", "--lang", LANG]))


def test_apply_transcript(env):
    doorway, run = env
    make_stale(doorway)
    check_snapshot("apply_stale.txt",
                   run(["sdy", "--to-sheet", "--lang", LANG, "--apply"]))


# ---------------------------------------------------------------------------
# The dry run is a dry run
# ---------------------------------------------------------------------------

def test_dry_run_touches_nothing(env):
    doorway, run = env
    make_stale(doorway)
    before = sheet(doorway).get_all_values()
    out = run(["sdy", "--to-sheet", "--lang", LANG])

    assert doorway.mutations == []
    assert sheet(doorway).get_all_values() == before
    assert "use --apply to write" in out


# ---------------------------------------------------------------------------
# What the sheet ends up saying
# ---------------------------------------------------------------------------

def test_apply_makes_the_sheet_match_the_yaml(env):
    doorway, run = env
    make_stale(doorway)
    run(["sdy", "--to-sheet", "--lang", LANG, "--apply"])
    assert sheet(doorway).get_all_values() == yaml_rows()


def test_a_shrunk_yaml_leaves_no_rows_behind(env):
    """It clears before writing. Otherwise a retired class would live on."""
    doorway, run = env
    ws = sheet(doorway)
    ws.update([["a_retired_class", LANG, "general", "V-combines"]],
              f"A{len(ws.get_all_values()) + 1}")

    run(["sdy", "--to-sheet", "--lang", LANG, "--apply"])
    assert sheet(doorway).get_all_values() == yaml_rows()


def test_a_sheet_that_already_agrees_is_not_rewritten(env):
    """No churn, and no revision in the Sheet's history saying nothing changed."""
    doorway, run = env
    out = run(["sdy", "--to-sheet", "--lang", LANG, "--apply"])
    assert "already up to date" in out
    assert doorway.mutations == []


def test_a_second_apply_is_a_no_op(env):
    doorway, run = env
    make_stale(doorway)
    run(["sdy", "--to-sheet", "--lang", LANG, "--apply"])
    doorway.clear_mutations()

    out = run(["sdy", "--to-sheet", "--lang", LANG, "--apply"])
    assert "already up to date" in out
    assert doorway.mutations == []


def test_a_change_to_a_second_row_of_a_class_is_written_but_not_named(env):
    """Pins current behaviour, which under-reports. See the progress doc, finding 5.

    The "removed / added / changed" list is keyed on the Class column, and
    several classes have a row per construction — `segmental` and
    `phrasal_accent` here. A difference confined to the second row of such a
    class is found and written correctly, but the coordinator is told only
    "Would update", with nothing named. Pinned so that changing it is visible.
    """
    doorway, run = env
    ws = sheet(doorway)
    rows = ws.get_all_values()
    assert rows[-1][0] == "phrasal_accent" and rows[-2][0] == "phrasal_accent"
    rows[-1][-1] = "joint_accent{never}"
    ws.clear()
    ws.update(rows, "A1")

    out = run(["sdy", "--to-sheet", "--lang", LANG, "--apply"])
    assert "Updated → diagnostics Sheet" in out
    assert "changed:" not in out                     # nothing named
    assert sheet(doorway).get_all_values() == yaml_rows()


# ---------------------------------------------------------------------------
# Refusals — a live sheet is never overwritten from a YAML that is not sound
# ---------------------------------------------------------------------------

def test_a_yaml_with_errors_never_reaches_the_sheet(env, monkeypatch, tmp_path):
    doorway, run = env
    lang_setup = tmp_path / LANG / "lang_setup"
    lang_setup.mkdir(parents=True)
    (lang_setup / f"diagnostics_{LANG}.yaml").write_text(textwrap.dedent("""\
        language: some_other_language
        classes:
          ciscategorial:
            constructions: [general]
            criteria:
              V-combines: [y, n]
        """), encoding="utf-8")
    monkeypatch.setattr(sdy, "CODED_DATA", tmp_path)
    before = sheet(doorway).get_all_values()

    out = run(["sdy", "--to-sheet", "--lang", LANG, "--apply"])
    assert "ERROR" in out
    assert "fix errors above before uploading" in out
    assert doorway.mutations == []
    assert sheet(doorway).get_all_values() == before


def test_a_language_with_no_yaml_is_skipped(env, monkeypatch, tmp_path):
    doorway, run = env
    monkeypatch.setattr(sdy, "CODED_DATA", tmp_path)
    out = run(["sdy", "--to-sheet", "--lang", LANG, "--apply"])
    assert "No YAML found" in out
    assert doorway.mutations == []


def test_a_language_with_no_sheet_recorded_is_skipped_not_created(env):
    """`--to-sheet` only updates; making the sheet is generate-sheets' job."""
    doorway, run = env
    out = run(["sdy", "--to-sheet", "--lang", "nyan1308", "--apply"])
    assert "No diagnostics_spreadsheet_id in manifest" in out
    assert doorway.mutations == []


def test_one_unreachable_sheet_does_not_stop_the_others(env):
    doorway, run = env
    make_stale(doorway, "synth0001")
    del doorway._spreadsheets[DIAG_ID[LANG]]

    out = run(["sdy", "--to-sheet", "--apply"])
    assert f"[{LANG}] Could not read Sheet" in out
    assert sheet(doorway, "synth0001").get_all_values() == yaml_rows("synth0001")
    assert "Done: 1 Sheet(s) updated." in out


# ---------------------------------------------------------------------------
# The other two directions do not go near Drive
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [["sdy"], ["sdy", "--from-tsv"]])
def test_the_local_directions_touch_no_sheet(env, argv):
    doorway, run = env
    run(argv)
    assert doorway.mutations == []
