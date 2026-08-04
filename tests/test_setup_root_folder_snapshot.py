"""Snapshot tests for `python -m coding setup-root-folder`, run against the fake.

File 3 of 17 migrated to the Drive doorway. This command was never on the plan's
list of files to migrate — it was one of seven found by scanning the code
instead of trusting that list (see tests/test_doorway_coverage.py).

It is a one-time setup command with no dry run: it always acts. That makes it a
good first step for the newly-found group — nothing it touches holds annotation
data — and it is the first command to exercise the folder and sharing parts of
the doorway, which nothing had covered before.

Before migrating, the old code was driven from this same stand-in Drive through
a shim, and its output and Drive calls were recorded. The migrated code
produces both identically.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_setup_root_folder_snapshot.py`
"""
from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive_doorway, setup_root_folder
from fake_drive import MANIFEST_FILE_ID, FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "setup_root_folder"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

FOLDER_MIME = "application/vnd.google-apps.folder"
NOTEBOOK_ID = "fake_notebook_file"


@pytest.fixture()
def env(monkeypatch):
    """A stand-in Drive where nothing has been tidied up yet.

    Language folders still carry the old 'planars — {lang}' names and sit
    outside the root folder, which is the state this command exists to fix.
    """
    doorway = FakeDriveDoorway()
    manifest = json.loads(
        (ROOT / "tests/fixtures/drive_state/manifest.json").read_text(encoding="utf-8"))
    config: dict = {}
    for lang, entry in sorted(manifest.items()):
        if not entry.get("folder_id"):
            continue
        doorway.seed_file(f"planars — {lang}", FOLDER_MIME, [], file_id=entry["folder_id"])
        config[lang] = {"folder_id": entry["folder_id"]}
    doorway.seed_json_file("manifest.json", manifest, [], file_id=MANIFEST_FILE_ID)
    doorway.seed_file("all_languages.ipynb", "application/json", [], file_id=NOTEBOOK_ID)
    config["_planars_config_file_id"] = MANIFEST_FILE_ID
    config["_all_languages_notebook_file_id"] = NOTEBOOK_ID

    saved: dict = {}
    monkeypatch.setattr(setup_root_folder, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(setup_root_folder, "_save_drive_config", saved.update)
    drive_doorway.set_doorway(doorway)
    try:
        yield doorway, config, saved
    finally:
        drive_doorway.reset_doorway()


def run() -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        setup_root_folder.main()
    return buf.getvalue()


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
# First run — an untidied Drive
# ---------------------------------------------------------------------------

def test_first_run_output(env, monkeypatch):
    check_snapshot("first_run.txt", run())


def test_first_run_creates_the_root_folder_and_shares_it(env):
    doorway, _, _ = env
    run()
    created = doorway.mutations_of("create_file")
    assert [c["name"] for c in created] == ["ConstituencyTypology"]
    assert created[0]["mimetype"] == FOLDER_MIME
    assert created[0]["parents"] == []          # deliberately at the Drive root
    perms = doorway.mutations_of("create_permission")
    assert [(p["type"], p["role"]) for p in perms] == [("anyone", "reader")]


def test_first_run_moves_every_language_folder_into_the_root(env):
    doorway, config, _ = env
    run()
    root_id = doorway.mutations_of("create_file")[0]["file_id"]
    langs = [k for k in config if not k.startswith("_")]
    moved = {m["file_id"]: m["to_parent"] for m in doorway.mutations_of("move_file")}
    for lang in langs:
        assert moved[config[lang]["folder_id"]] == root_id
    # manifest.json and the coordinator notebook move too.
    assert moved[MANIFEST_FILE_ID] == root_id
    assert moved[NOTEBOOK_ID] == root_id


def test_first_run_renames_folders_to_the_bare_language_id(env):
    doorway, config, _ = env
    run()
    renamed = {m["file_id"]: m["name"] for m in doorway.mutations_of("update_file")}
    for lang in [k for k in config if not k.startswith("_")]:
        assert renamed[config[lang]["folder_id"]] == lang


def test_first_run_records_the_root_folder_id(env):
    doorway, _, saved = env
    run()
    assert saved["_root_folder_id"] == doorway.mutations_of("create_file")[0]["file_id"]


# ---------------------------------------------------------------------------
# Second run — the command claims to be safe to repeat
# ---------------------------------------------------------------------------

def test_second_run_changes_nothing_at_all(env, monkeypatch):
    """Its docstring promises idempotence, and now it actually is.

    Before issue #276, the sharing call ran unconditionally, so every repeat
    added another "anyone with the link" grant on the root folder instead of
    checking for one first. `ensure_anyone_permission` (coding/drive.py) fixes
    this: it lists existing permissions first and only creates one if no
    "anyone" grant is already there, so a second run makes zero Drive calls of
    any kind.
    """
    doorway, config, saved = env
    run()
    monkeypatch.setattr(setup_root_folder, "_load_drive_config",
                        lambda: json.loads(json.dumps({**config, **saved})))
    doorway.clear_mutations()
    out = run()

    assert doorway.mutations == []
    assert "already inside root folder" in out
    assert "already has correct name" in out


def test_a_manually_revoked_share_is_restored_on_the_next_run(env, monkeypatch):
    """ensure_anyone_permission's other half: not just no duplicates, also self-heals.

    Before issue #276, only generate_notebooks.py's grant repaired itself after
    a manual revoke; setup_root_folder.py's did not because it never checked
    at all (it just always fired, which is a different bug — see the test
    above). The same shared helper now gives every sharing call site both
    properties from one mechanism.
    """
    doorway, config, saved = env
    run()
    root_id = doorway.mutations_of("create_file")[0]["file_id"]
    perm = next(p for p in doorway.list_permissions(root_id) if p["type"] == "anyone")
    doorway.delete_permission(root_id, perm["id"])
    assert not any(p["type"] == "anyone" for p in doorway.list_permissions(root_id))

    monkeypatch.setattr(setup_root_folder, "_load_drive_config",
                        lambda: json.loads(json.dumps({**config, **saved})))
    doorway.clear_mutations()
    run()

    assert any(p["type"] == "anyone" and p["role"] == "reader"
               for p in doorway.list_permissions(root_id))
    assert len(doorway.mutations_of("create_permission")) == 1


def test_second_run_output(env, monkeypatch):
    doorway, config, saved = env
    run()
    monkeypatch.setattr(setup_root_folder, "_load_drive_config",
                        lambda: json.loads(json.dumps({**config, **saved})))
    check_snapshot("second_run.txt", run())


# ---------------------------------------------------------------------------
# Missing pieces are reported, not fatal
# ---------------------------------------------------------------------------

def test_a_language_without_a_folder_id_is_reported_and_skipped(env, monkeypatch):
    doorway, config, _ = env
    partial = {**config, "arao1248": {}}
    monkeypatch.setattr(setup_root_folder, "_load_drive_config",
                        lambda: json.loads(json.dumps(partial)))
    out = run()
    assert "No folder_id for 'arao1248'" in out
    assert config["arao1248"]["folder_id"] not in {
        m["file_id"] for m in doorway.mutations_of("move_file")}


def test_absent_manifest_and_notebook_are_reported_with_the_fix(env, monkeypatch):
    """The message has to say what to run — nobody memorises this command's order."""
    doorway, config, _ = env
    bare = {k: v for k, v in config.items() if not k.startswith("_")}
    monkeypatch.setattr(setup_root_folder, "_load_drive_config",
                        lambda: json.loads(json.dumps(bare)))
    out = run()
    assert "No manifest.json found" in out
    assert "No all_languages.ipynb found" in out
    # Twice for the two missing files, plus once in the closing next-steps list.
    assert out.count("generate-notebooks --apply") == 3
