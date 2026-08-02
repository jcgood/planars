"""Snapshot tests for `python -m coding prune-manifest`, run against the fake.

File 5 of 17 migrated to the Drive doorway, and the first that moves anything
in Drive — though only sheets for classes already retired, and it moves them
into an `_archived/` folder rather than deleting them.

Three things this command does are worth pinning down, and all three are here:
it never deletes, only archives, on both sides (local TSVs go to `archive/`,
the Drive sheet goes to `_archived/`); it warns before archiving a sheet
somebody edited recently, which is the only guard against pruning work that
was still in progress; and declining at the prompt leaves everything exactly
as it was.

Before migrating, the old code was driven from this same stand-in Drive
through a shim, across five scenarios. Output, the local file tree, and the
recorded Drive changes came back byte-identical afterwards.

`CODED_DATA` is redirected into a temp tree in every test. This command
deletes local TSVs, and must never run against the real `coded_data/`.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_prune_manifest_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pytest

from coding import drive as drive_module
from coding import drive_doorway, prune_manifest
from fake_drive import MANIFEST_FILE_ID, ROOT_FOLDER_ID, FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "prune_manifest"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANG = "stan1293"
RETIRED = "stress"          # in the manifest, absent from diagnostics
LANGS = ["arao1248", "stan1293", "synth0001"]
SHEET_ID = "retired_sheet_id"


def _recently(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace(
        "+00:00", "Z")


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """A Drive still listing one retired class, and that class's TSVs on disk.

    Yields (doorway, run, coded), where `run(argv, answers)` plays one command.
    """
    doorway = FakeDriveDoorway.from_fixtures()
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)

    doorway.seed_spreadsheet({
        "spreadsheet_id": SHEET_ID,
        "title": f"{RETIRED}_{LANG}",
        "worksheets": [{"sheet_id": 0, "title": "general", "row_count": 3,
                        "col_count": 2,
                        "values": [["Element", "accented"], ["also", "y"]]}],
    })
    doorway.file(SHEET_ID).parents = [manifest[LANG]["folder_id"]]
    doorway.file(SHEET_ID).modified_time = _recently(400)
    manifest[LANG]["sheets"][RETIRED] = {
        "spreadsheet_id": SHEET_ID,
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}",
        "constructions": ["general"],
    }
    doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode()

    coded = tmp_path / "coded_data"
    (coded / LANG / RETIRED).mkdir(parents=True)
    (coded / LANG / RETIRED / "general.tsv").write_text(
        "Element\taccented\nalso\ty\n", encoding="utf-8")
    (coded / LANG / RETIRED / "stress_domain.tsv").write_text(
        "Element\taccented\nand\tn\n", encoding="utf-8")
    # Every language's diagnostics, or the ones without would look wholly stale.
    for lang in LANGS:
        setup = coded / lang / "lang_setup"
        setup.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            ROOT / "coded_data" / lang / "lang_setup" / f"diagnostics_{lang}.yaml",
            setup / f"diagnostics_{lang}.yaml")

    monkeypatch.setattr(prune_manifest, "CODED_DATA", coded)
    monkeypatch.setattr(prune_manifest, "MANIFEST_ARCHIVES", tmp_path / "manifest_archives")
    monkeypatch.setattr(prune_manifest, "ROOT", tmp_path)
    # The real drive_config.json holds live IDs; a test must never write it.
    config = {"_planars_config_file_id": MANIFEST_FILE_ID,
              "_root_folder_id": ROOT_FOLDER_ID}
    saved: Dict = {}
    monkeypatch.setattr(prune_manifest, "_load_drive_config", lambda: dict(config))
    monkeypatch.setattr(prune_manifest, "_save_drive_config", saved.update)
    monkeypatch.setattr(drive_module, "_load_drive_config", lambda: dict(config))
    drive_doorway.set_doorway(doorway)

    def run(argv: List[str], answers: List[str] = ()) -> str:
        replies = iter(answers)

        def scripted_input(prompt: str = "") -> str:
            try:
                answer = next(replies)
            except StopIteration:
                raise EOFError
            print(f"{prompt}{answer}")
            return answer

        monkeypatch.setattr("builtins.input", scripted_input)
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            prune_manifest.main()
        # Archive filenames carry a wall-clock stamp.
        return re.sub(r"\d{8}_\d{6}", "TIMESTAMP", buf.getvalue())

    try:
        yield doorway, run, coded, saved
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


def manifest_of(doorway) -> Dict:
    return doorway.download_file_json(MANIFEST_FILE_ID)


def active_tsvs(coded: Path) -> List[str]:
    d = coded / LANG / RETIRED
    return sorted(p.name for p in d.glob("*.tsv")) if d.exists() else []


def archived_tsvs(coded: Path) -> List[str]:
    d = coded / LANG / "archive" / RETIRED
    return sorted(p.name for p in d.glob("*.tsv")) if d.exists() else []


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    _, run, _, _ = env
    check_snapshot("dry_run.txt", run(["prune-manifest"]))


def test_apply_transcript(env):
    _, run, _, _ = env
    check_snapshot("apply.txt", run(["prune-manifest", "--apply"], ["y"]))


# ---------------------------------------------------------------------------
# The dry run is a dry run
# ---------------------------------------------------------------------------

def test_dry_run_changes_nothing_anywhere(env):
    doorway, run, coded, saved = env
    run(["prune-manifest"])
    assert doorway.mutations == []
    assert active_tsvs(coded) == ["general.tsv", "stress_domain.tsv"]
    assert archived_tsvs(coded) == []
    assert RETIRED in manifest_of(doorway)[LANG]["sheets"]
    assert saved == {}


def test_dry_run_says_the_sheet_would_move_without_reading_it(env):
    """It quotes the manifest's URL rather than asking Drive for the name."""
    doorway, run, _, _ = env
    out = run(["prune-manifest"])
    assert f"would move Drive sheet → _archived/  (https://docs.google.com/spreadsheets/d/{SHEET_ID})" in out


# ---------------------------------------------------------------------------
# Nothing is deleted — on either side
# ---------------------------------------------------------------------------

def test_local_tsvs_are_archived_not_deleted(env):
    doorway, run, coded, _ = env
    run(["prune-manifest", "--apply"], ["y"])
    assert active_tsvs(coded) == []
    assert not (coded / LANG / RETIRED).exists()      # empty directory tidied away
    assert len(archived_tsvs(coded)) == 2
    assert all(name.endswith(".tsv") for name in archived_tsvs(coded))


def test_the_drive_sheet_is_moved_into_archived_not_removed(env):
    doorway, run, _, _ = env
    run(["prune-manifest", "--apply"], ["y"])
    created = doorway.mutations_of("create_file")
    assert [c["name"] for c in created] == ["_archived"]
    moved = doorway.mutations_of("move_file")
    assert [m["file_id"] for m in moved] == [SHEET_ID]
    assert moved[0]["to_parent"] == created[0]["file_id"]
    # The spreadsheet is still there, contents intact.
    assert doorway.spreadsheet(SHEET_ID).worksheet("general").get_all_values() == [
        ["Element", "accented"], ["also", "y"]]


def test_the_manifest_snapshot_is_written_before_anything_changes(env, tmp_path):
    _, run, _, _ = env
    out = run(["prune-manifest", "--apply"], ["y"])
    assert "Manifest snapshot written to" in out
    snapshots = list((tmp_path / "manifest_archives").glob("manifest_*.json"))
    assert len(snapshots) == 1
    # The snapshot is the state *before* the prune — the retired class is in it.
    assert RETIRED in json.loads(snapshots[0].read_text())[LANG]["sheets"]


def test_the_retired_class_leaves_the_manifest_on_drive(env):
    doorway, run, _, _ = env
    before = manifest_of(doorway)[LANG]["sheets"]
    run(["prune-manifest", "--apply"], ["y"])
    after = manifest_of(doorway)[LANG]["sheets"]
    assert RETIRED in before and RETIRED not in after
    # And nothing else was dropped along the way.
    assert set(before) - {RETIRED} == set(after)


# ---------------------------------------------------------------------------
# Declining
# ---------------------------------------------------------------------------

def test_declining_leaves_everything_as_it_was(env):
    doorway, run, coded, _ = env
    out = run(["prune-manifest", "--apply"], ["n"])
    assert "Skipped stress." in out
    assert "No changes made (all classes skipped)." in out
    assert doorway.mutations == []
    assert active_tsvs(coded) == ["general.tsv", "stress_domain.tsv"]
    assert RETIRED in manifest_of(doorway)[LANG]["sheets"]


def test_all_skips_the_prompt(env):
    doorway, run, coded, _ = env
    run(["prune-manifest", "--apply", "--all"], answers=[])   # a prompt would raise
    assert active_tsvs(coded) == []
    assert RETIRED not in manifest_of(doorway)[LANG]["sheets"]


# ---------------------------------------------------------------------------
# The recency warning — the only guard against pruning work in progress
# ---------------------------------------------------------------------------

def test_a_recently_edited_sheet_is_flagged_before_it_is_archived(env):
    doorway, run, _, _ = env
    doorway.file(SHEET_ID).modified_time = _recently(2)
    out = run(["prune-manifest", "--apply"], ["y"])
    assert "was edited 2 day(s) ago" in out
    assert "check for unapplied annotation work" in out


def test_a_long_untouched_sheet_is_not_flagged(env):
    doorway, run, _, _ = env
    out = run(["prune-manifest", "--apply"], ["y"])
    assert "day(s) ago" not in out


def test_the_dry_run_flags_it_too(env):
    """The dry run is where the decision gets made, so it has to say this."""
    doorway, run, _, _ = env
    doorway.file(SHEET_ID).modified_time = _recently(3)
    out = run(["prune-manifest"], answers=[])
    assert "was edited 3 day(s) ago" in out


def test_the_warning_comes_before_the_prompt_it_should_inform(env):
    """Issue #277. It used to print after the answer, which is no use at all.

    It stays a warning rather than a gate — the sheet is archived, not deleted,
    and a coordinator who has read the line is entitled to go ahead. What
    changed is that they get to read it first.
    """
    doorway, run, coded, _ = env
    doorway.file(SHEET_ID).modified_time = _recently(1)
    out = run(["prune-manifest", "--apply"], ["y"])

    warning = out.index("was edited 1 day(s) ago")
    prompt = out.index(f"Prune '{RETIRED}' from")
    assert warning < prompt, "the warning has to come first to be worth printing"
    assert active_tsvs(coded) == []
    assert RETIRED not in manifest_of(doorway)[LANG]["sheets"]


# ---------------------------------------------------------------------------
# When Drive will not answer
# ---------------------------------------------------------------------------

def test_an_unreadable_sheet_is_reported_and_the_move_is_skipped(env, monkeypatch):
    doorway, run, _, _ = env

    def refuse(*args, **kwargs):
        raise RuntimeError("no")

    monkeypatch.setattr(doorway, "get_file", refuse)
    out = run(["prune-manifest", "--apply"], ["y"])
    assert "could not read sheet metadata" in out
    assert doorway.mutations_of("move_file") == []
    # The manifest entry goes anyway, which is worth knowing: the sheet stays
    # where it is and stops being listed.
    assert RETIRED not in manifest_of(doorway)[LANG]["sheets"]


def test_nothing_stale_does_nothing(env, monkeypatch):
    doorway, run, coded, _ = env
    manifest = manifest_of(doorway)
    del manifest[LANG]["sheets"][RETIRED]
    doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode()
    shutil.rmtree(coded / LANG / RETIRED)
    out = run(["prune-manifest", "--apply", "--all"])
    assert "nothing to prune" in out
    assert doorway.mutations == []
