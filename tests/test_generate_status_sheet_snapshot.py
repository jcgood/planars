"""Snapshot tests for `python -m coding generate-status-sheet`.

File 12 of 18 migrated to the Drive doorway, and the first command to create a
**root-level** Drive folder (parent = Drive root, not the project's root
folder from `setup-root-folder`) -- see the module docstring for why: the
project root folder has an inherited "anyone" permission that Google's API
refuses to remove at a child level, so a status sheet nested inside it could
never be locked down to read-only. It is also the first migrated command that
*reads* other languages' already-existing annotation spreadsheets rather than
only writing to sheets it owns.

Before migrating, the old code was driven from this same stand-in Drive
through shims, across eight scenarios (a dry run over every language, a dry
run restricted to one, a first apply, a second apply that must reuse the
folder and spreadsheet, a small language with no coreference/phrasal_accent,
a language absent from the manifest, a language with no
coded_data/lang_setup/ directory, and --apply with no --lang at all). Output,
the mutation logs, the resulting manifest, and every written sheet's contents
and permissions came back byte-identical afterwards.

Regenerate: PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_generate_status_sheet_snapshot.py
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
from coding import generate_status_sheet as gen
from fake_drive import MANIFEST_FILE_ID, ROOT_FOLDER_ID, FakeDriveDoorway, api_error

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "generate_status_sheet"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

ADAM = "adamjamesrosstallman@gmail.com"
FOLDER_NAME = "Annotation Status"


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """A stand-in Drive seeded from the three fixture languages.

    Yields (doorway, run, saved). `run(argv)` plays one command and returns
    its output with generated spreadsheet/folder IDs blanked, since they are
    fresh every time.
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
        out = buf.getvalue()
        out = re.sub(r"fake_ss_\d+", "NEW_SHEET_ID", out)
        out = re.sub(r"fake_file_\d+", "NEW_FOLDER_ID", out)
        return out

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


def the_folder(doorway):
    for f in doorway._files.values():
        if f.name == FOLDER_NAME:
            return f
    raise AssertionError(f"no {FOLDER_NAME!r} folder")


def the_sheet(doorway, name: str):
    for ss in doorway._spreadsheets.values():
        if ss.title == name:
            return ss
    raise AssertionError(f"no spreadsheet called {name}")


def _construction_name(cell_text: str) -> str:
    """The construction name, whether the cell is plain text or a HYPERLINK formula."""
    m = re.search(r'HYPERLINK\("[^"]*",\s*"([^"]*)"\)', cell_text)
    return m.group(1) if m else cell_text


def status_row_index(ss, class_name: str, construction: str) -> int:
    """0-based row index (into get_all_values()) of one (class, construction) row."""
    ws = ss.worksheet("Status")
    values = ws.get_all_values()
    header_row = next(i for i, row in enumerate(values) if row == gen._HEADER)
    for i, row in enumerate(values[header_row + 1:], start=header_row + 1):
        if row[0] == class_name and _construction_name(row[1]) == construction:
            return i
    raise AssertionError(f"no row for {class_name}/{construction}")


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    _, run, _ = env
    out = run(["gen", "--lang", "stan1293"])
    check_snapshot("dry_run.txt", out)


def test_apply_transcript(env):
    _, run, _ = env
    out = run(["gen", "--lang", "arao1248", "--apply"])
    check_snapshot("apply.txt", out)


# ---------------------------------------------------------------------------
# The dry run is a dry run
# ---------------------------------------------------------------------------

def test_dry_run_touches_nothing(env):
    doorway, run, saved = env
    out = run(["gen"])
    assert doorway.mutations == []
    assert saved == {}
    assert "Run with --apply" in out


# ---------------------------------------------------------------------------
# The freestanding root-level folder
# ---------------------------------------------------------------------------

def test_the_status_folder_is_created_at_drive_root(env):
    """Not nested under the project root folder -- see the module docstring:
    the project root folder's inherited 'anyone' permission can't be removed
    at a child level, so a status sheet living inside it could never be
    locked down to read-only."""
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    folder = the_folder(doorway)
    assert folder.parents == []
    folder_creates = [m for m in doorway.mutations_of("create_file")
                      if m["name"] == FOLDER_NAME]
    assert len(folder_creates) == 1
    assert folder_creates[0]["parents"] == []


def test_the_status_sheet_is_moved_into_the_status_folder(env):
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    folder = the_folder(doorway)
    ss = the_sheet(doorway, "status_arao1248")
    moved = doorway.mutations_of("move_file")
    assert [(m["file_id"], m["to_parent"]) for m in moved] == [(ss.id, folder.id)]


# ---------------------------------------------------------------------------
# Re-running reuses what already exists
# ---------------------------------------------------------------------------

def test_a_second_run_reuses_the_same_folder_and_spreadsheet(env):
    """Or Adam's bookmarked link and permission would go stale every regeneration."""
    doorway, run, _ = env
    run(["gen", "--lang", "synth0001", "--apply"])
    folder_id = the_folder(doorway).id
    sheet_id = the_sheet(doorway, "status_synth0001").id
    doorway.clear_mutations()

    run(["gen", "--lang", "synth0001", "--apply"])
    assert the_folder(doorway).id == folder_id
    assert the_sheet(doorway, "status_synth0001").id == sheet_id
    assert [m for m in doorway.mutations_of("create_file") if m["name"] == FOLDER_NAME] == []
    assert doorway.mutations_of("create_spreadsheet") == []
    assert doorway.mutations_of("move_file") == []


def test_the_manifest_records_where_the_sheet_is(env):
    doorway, run, _ = env
    out = run(["gen", "--lang", "arao1248", "--apply"])
    ss = the_sheet(doorway, "status_arao1248")
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    assert manifest["arao1248"]["status_sheet_url"] == ss.url
    assert "Manifest updated on Drive (status_sheet_url)." in out


def test_a_second_run_with_no_url_change_does_not_rewrite_the_manifest(env):
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    doorway.clear_mutations()

    out = run(["gen", "--lang", "arao1248", "--apply"])
    assert doorway.mutations_of("update_file") == []
    assert "Manifest updated on Drive" not in out


# ---------------------------------------------------------------------------
# Locking: read-only, named person, no "anyone" grant
# ---------------------------------------------------------------------------

def test_folder_and_sheet_are_shared_with_adam_as_reader_not_writer(env):
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    folder = the_folder(doorway)
    ss = the_sheet(doorway, "status_arao1248")
    for file_id in (folder.id, ss.id):
        perms = doorway.list_permissions(file_id, fields="permissions(type,role,emailAddress)")
        assert all(p["type"] != "anyone" for p in perms)
        user_perms = [p for p in perms if p["type"] == "user"]
        assert len(user_perms) == 1
        assert user_perms[0]["role"] == "reader"
        assert user_perms[0]["emailAddress"] == ADAM

    creates = doorway.mutations_of("create_permission")
    assert len(creates) == 2  # folder + sheet
    for c in creates:
        assert c["type"] == "user"
        assert c["role"] == "reader"
        assert c["email"] == ADAM
        assert c["notify"] is False


def test_a_pre_existing_anyone_permission_is_removed_on_rerun(env):
    """Defensive: freestanding files shouldn't get one, but Drive sometimes
    adds one by default on creation."""
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    ss = the_sheet(doorway, "status_arao1248")
    doorway.create_permission(ss.id, type="anyone", role="writer")
    assert any(p["type"] == "anyone"
              for p in doorway.list_permissions(ss.id, fields="permissions(type)"))

    run(["gen", "--lang", "arao1248", "--apply"])
    perms = doorway.list_permissions(ss.id, fields="permissions(type,role,emailAddress)")
    assert not any(p["type"] == "anyone" for p in perms)
    adam_perms = [p for p in perms if p.get("emailAddress") == ADAM]
    assert len(adam_perms) == 1
    assert adam_perms[0]["role"] == "reader"


def test_a_second_run_does_not_duplicate_adams_permission(env):
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    ss = the_sheet(doorway, "status_arao1248")
    doorway.clear_mutations()

    run(["gen", "--lang", "arao1248", "--apply"])
    perms = doorway.list_permissions(ss.id, fields="permissions(type,emailAddress)")
    adam_perms = [p for p in perms if p.get("emailAddress") == ADAM]
    assert len(adam_perms) == 1
    assert doorway.mutations_of("create_permission") == []


# ---------------------------------------------------------------------------
# Status cell colors
# ---------------------------------------------------------------------------

def test_green_for_a_fully_annotated_construction(env):
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    ss = the_sheet(doorway, "status_arao1248")
    ws = ss.worksheet("Status")
    row = status_row_index(ss, "subspanrepetition", "auxiliary_construction")
    assert ws._cell(row, 2).background == gen._GREEN


def test_yellow_for_a_not_yet_complete_construction(env):
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    ss = the_sheet(doorway, "status_arao1248")
    ws = ss.worksheet("Status")
    row = status_row_index(ss, "ciscategorial", "general")
    assert ws._cell(row, 2).background == gen._YELLOW


def test_gray_for_a_missing_sheet(env):
    doorway, run, _ = env
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    del manifest["arao1248"]["sheets"]["noninterruption"]
    doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode("utf-8")

    run(["gen", "--lang", "arao1248", "--apply"])
    ss = the_sheet(doorway, "status_arao1248")
    ws = ss.worksheet("Status")
    row = status_row_index(ss, "noninterruption", "general")
    assert ws._cell(row, 2).background == gen._GRAY
    assert ws.get_all_values()[row][2] == "no sheet found"


def test_gray_for_a_pair_row_construction(env):
    doorway, run, _ = env
    run(["gen", "--lang", "stan1293", "--apply"])
    ss = the_sheet(doorway, "status_stan1293")
    ws = ss.worksheet("Status")
    row = status_row_index(ss, "nonpermutability", "general")
    assert ws._cell(row, 2).background == gen._GRAY
    assert ws.get_all_values()[row][2] == "pair-row tab"


# ---------------------------------------------------------------------------
# The hyperlink construction
# ---------------------------------------------------------------------------

def test_the_folder_link_in_the_banner_is_a_hyperlink_formula(env):
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    ss = the_sheet(doorway, "status_arao1248")
    ws = ss.worksheet("Status")
    values = ws.get_all_values()
    folder_url = doorway.download_file_json(MANIFEST_FILE_ID)["arao1248"]["folder_url"]
    assert values[2][0] == f'=HYPERLINK("{folder_url}", "📁 Annotation folder for Araona [arao1248]")'


def test_each_construction_cell_links_to_its_own_tab(env):
    doorway, run, _ = env
    run(["gen", "--lang", "arao1248", "--apply"])
    ss = the_sheet(doorway, "status_arao1248")
    ws = ss.worksheet("Status")
    row = status_row_index(ss, "ciscategorial", "general")
    cell = ws.get_all_values()[row][1]
    assert cell.startswith('=HYPERLINK("')
    assert "#gid=" in cell
    assert cell.endswith('"general")')


# ---------------------------------------------------------------------------
# Skips: absent from the manifest, no lang_setup dir, unreadable diagnostics
# ---------------------------------------------------------------------------

def test_a_language_absent_from_the_manifest_is_skipped(env):
    doorway, run, _ = env
    out = run(["gen", "--lang", "nyan1308", "--apply"])
    assert "not found in manifest — skipping" in out
    # The folder is created/locked up front, before any per-language work --
    # that is the only Drive activity unavoidable ahead of the skip.
    assert doorway.mutations_of("create_spreadsheet") == []
    assert doorway.mutations_of("move_file") == []


def test_a_language_with_no_lang_setup_dir_is_skipped(env, monkeypatch, tmp_path):
    doorway, run, _ = env
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)
    manifest["fakelang0001"] = {
        "folder_id": "fake_lang_folder_xyz",
        "folder_url": "https://drive.google.com/drive/folders/fake_lang_folder_xyz",
        "sheets": {},
    }
    doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode("utf-8")

    out = run(["gen", "--lang", "fakelang0001", "--apply"])
    assert "no coded_data/fakelang0001/lang_setup/ found" in out
    assert doorway.mutations_of("create_spreadsheet") == []
    assert doorway.mutations_of("move_file") == []


def test_a_language_with_unreadable_diagnostics_is_skipped(env, monkeypatch, tmp_path):
    doorway, run, _ = env
    coded = tmp_path / "coded_data"
    (coded / "synth0001" / "lang_setup").mkdir(parents=True)
    monkeypatch.setattr(gen, "CODED_DATA", coded)

    out = run(["gen", "--lang", "synth0001", "--apply"])
    assert "could not read diagnostics_synth0001.yaml" in out
    assert "skipping" in out
    assert doorway.mutations_of("create_spreadsheet") == []
    assert doorway.mutations_of("move_file") == []


def test_no_lang_flag_runs_every_manifest_language(env):
    _, run, _ = env
    out = run(["gen"])
    for lang_id in ("arao1248", "stan1293", "synth0001"):
        assert f"[{lang_id}]" in out


# ---------------------------------------------------------------------------
# Retry on a transient rate limit (issue #284) -- this file's structural
# doorway calls (get_or_create_folder, delete_permission, create_permission)
# were not wrapped in _with_retry until this fix, unlike restructure_sheets.py
# which got the same treatment during Phase 8 fault injection (issue #271).
# A single 429 while creating the status folder used to crash the whole run.
# ---------------------------------------------------------------------------

def test_a_transient_429_creating_the_status_folder_is_retried_not_a_crash(env, monkeypatch):
    """`fail_after` fires exactly once by design (see fake_drive.py), so this
    is a real "one 429, then the retry succeeds" case. time.sleep is mocked
    so the real ~15s backoff wait doesn't slow the suite down.
    """
    doorway, run, _ = env
    monkeypatch.setattr(drive_module.time, "sleep", lambda *a, **kw: None)
    doorway.fail_after("create_file", 1, exc=api_error(429, "rate limited"))
    out = run(["gen", "--lang", "arao1248", "--apply"])
    assert "[SystemExit:" not in out
    folder = the_folder(doorway)
    assert folder.parents == []
    folder_creates = [m for m in doorway.mutations_of("create_file") if m["name"] == FOLDER_NAME]
    assert len(folder_creates) == 1
