"""rename-construction (#318 d) against the offline Drive and the frozen data.

The test renames coreference's np_reference to np_coreference, the rename
the schema made on 2026-10-23. Whichever name the frozen data has (it is
recaptured after the live rename), the test first gives English and synth0001
the old name everywhere — tab, Status row, diagnostics file, TSV — so it
always starts from the state the live run started from. (The ID file holds
sheet IDs, not tab names, so the rename leaves it alone; the manifest copy
on Drive lists the tab names and is republished after a renamed tab.)
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from coding import drive_doorway, drive_ids
from coding import rename_construction as rc
from command_runner import run_command
from fake_drive import MANIFEST_FILE_ID, FakeDriveDoorway, use_frozen_coded_data
from planars.schema_values import STATUS_CONSTRUCTION_COLUMN, STATUS_TAB

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(not (ROOT / "coded_data").exists(),
                                reason="coded_data/ (planars-data) is not checked out")

OLD, NEW, CLS = "np_reference", "np_coreference", "coreference"
LANGS = ["stan1293", "synth0001"]
# All three at once, as the live run did: the schema renamed all three, so a
# file renamed in one only would not pass validation.
RENAMES = {"reflexivization": "reflexive_coreference",
           "pronominalization": "pronoun_coreference", OLD: NEW}
SPECS = [f"{CLS}:{o}:{n}" for o, n in RENAMES.items()]


def _manifest(doorway):
    return doorway.download_file_json(MANIFEST_FILE_ID)


def _status_names(ws):
    rows = ws.get_all_values()
    col = rows[0].index(STATUS_CONSTRUCTION_COLUMN)
    return [r[col] for r in rows[1:]]


def _give_old_names(doorway, coded: Path) -> None:
    """Put each construction back under its old name wherever it has the new."""
    for lang in LANGS:
        ss = doorway.spreadsheet(drive_ids.class_sheet_id(FakeDriveDoorway.drive_config(), lang, CLS))
        status = ss.worksheet(STATUS_TAB)
        rows = status.get_all_values()
        col = rows[0].index(STATUS_CONSTRUCTION_COLUMN)
        setup = coded / lang / "lang_setup"
        for old, new in RENAMES.items():
            if new in [ws.title for ws in ss.worksheets()]:
                tab = ss.worksheet(new)
                tab.update_title(old)
                # The tab's name label goes back too (the door reads it).
                for meta in ss._developer_metadata:
                    if (meta["metadataKey"] == "planars_tab" and meta["metadataValue"] == new
                            and meta["location"].get("sheetId") == tab.id):
                        meta["metadataValue"] = old
            for r, row in enumerate(rows[1:], start=2):
                if row[col] == new:
                    status.update([[old]], f"{chr(ord('A') + col)}{r}")
            p = setup / f"diagnostics_{lang}.yaml"
            p.write_text(p.read_text(encoding="utf-8").replace(new, old), encoding="utf-8")
            tsv = coded / lang / CLS / f"{new}.tsv"
            if tsv.exists():
                tsv.rename(tsv.with_name(f"{old}.tsv"))


@pytest.fixture()
def env(monkeypatch, tmp_path):
    doorway = FakeDriveDoorway.from_fixtures()
    coded = use_frozen_coded_data(monkeypatch, tmp_path)
    for mod in (rc, sys.modules["coding.drive"]):
        monkeypatch.setattr(mod, "_load_drive_config", FakeDriveDoorway.drive_config)
        monkeypatch.setattr(mod, "_save_drive_config", lambda cfg: None)
    drive_doorway.set_doorway(doorway)
    _give_old_names(doorway, coded)

    def run(*argv: str) -> str:
        monkeypatch.setattr(sys, "argv", ["rename-construction", *argv])
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_command(rc, "rename-construction")
        return buf.getvalue()

    try:
        yield doorway, coded, run
    finally:
        drive_doorway.set_doorway(None)


def test_a_dry_run_changes_nothing(env):
    doorway, coded, run = env
    before = json.dumps(_manifest(doorway), sort_keys=True)
    out = run(*SPECS)
    assert "rename tab np_reference → np_coreference" in out
    assert json.dumps(_manifest(doorway), sort_keys=True) == before
    assert (coded / "stan1293" / CLS / f"{OLD}.tsv").exists()


def test_apply_renames_everywhere_and_keeps_the_answers(env):
    doorway, coded, run = env
    ids = FakeDriveDoorway.drive_config()
    sheet_id = drive_ids.class_sheet_id(ids, "stan1293", CLS)
    answers = doorway.spreadsheet(sheet_id).worksheet(OLD).get_all_values()

    out = run(*SPECS, "--apply")
    assert "0 broke a rule" in out, out
    assert "Manifest copy republished" in out

    manifest = _manifest(doorway)
    for lang in LANGS:
        info = manifest[lang]["sheets"][CLS]
        # The ID file is untouched: same sheet. The manifest copy lists the new tab names.
        assert info["spreadsheet_id"] == drive_ids.class_sheet_id(ids, lang, CLS)
        ss = doorway.spreadsheet(info["spreadsheet_id"])
        titles = [ws.title for ws in ss.worksheets()]
        assert set(RENAMES.values()) <= set(titles) and not set(RENAMES) & set(titles)
        assert NEW in _status_names(ss.worksheet(STATUS_TAB))
        assert OLD not in _status_names(ss.worksheet(STATUS_TAB))
        yaml_text = (coded / lang / "lang_setup" / f"diagnostics_{lang}.yaml").read_text()
        assert NEW in yaml_text and OLD not in yaml_text
        assert (coded / lang / CLS / f"{NEW}.tsv").exists()
        assert not (coded / lang / CLS / f"{OLD}.tsv").exists()
    # Same spreadsheet, same answers: only the tab's name changed.
    assert manifest["stan1293"]["sheets"][CLS]["spreadsheet_id"] == sheet_id
    assert doorway.spreadsheet(sheet_id).worksheet(NEW).get_all_values() == answers


def test_the_republished_manifest_copy_lists_the_new_tab_names(env):
    doorway, _, run = env
    run(*SPECS, "--apply")
    for lang in LANGS:
        info = _manifest(doorway)[lang]["sheets"][CLS]
        assert set(RENAMES.values()) <= set(info["constructions"])
        assert not set(RENAMES) & set(info["constructions"])


def test_a_second_run_changes_nothing(env):
    doorway, coded, run = env
    run(*SPECS, "--apply")
    manifest = json.dumps(_manifest(doorway), sort_keys=True)
    out = run(*SPECS, "--apply")
    assert "rename tab" not in out and "local:" not in out
    assert "already renamed" in out and "Done: 0 language(s)" in out
    assert json.dumps(_manifest(doorway), sort_keys=True) == manifest


def test_refused_until_the_schema_is_renamed(env):
    _, _, run = env
    with pytest.raises(SystemExit, match="still lists 'prescreening'"):
        run(f"{CLS}:prescreening:{NEW}")
    with pytest.raises(SystemExit, match="no construction 'nowhere'"):
        run(f"{CLS}:{OLD}:nowhere")


def test_seen_comments_follow_the_tab(env, monkeypatch):
    from coding import check_comments, state_files
    _, _, run = env
    state_files.COMMENTS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state_files.COMMENTS_STATE_PATH.write_text(json.dumps({"stan1293": {"seen": {
        f"{CLS}/{OLD} | NP | 2 | 5 | forward": "a question",
        f"{CLS}/prescreening | NP | 2": "kept"}}}))
    run(*SPECS, "--apply")
    seen = check_comments._load_state()["stan1293"]["seen"]
    assert seen == {f"{CLS}/{NEW} | NP | 2 | 5 | forward": "a question",
                    f"{CLS}/prescreening | NP | 2": "kept"}
