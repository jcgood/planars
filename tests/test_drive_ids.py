"""The ID file's class sheets, status sheet and notification issue
(coding/drive_ids.py), the door's construction_tabs(), and the manifest
rebuilt from them (coding/manifest_copy.py; Phase 10 unit 11c)."""
from __future__ import annotations

import json

import pytest

from coding import drive_door, drive_ids, manifest_copy
from tests.fake_drive import FIXTURE_DIR, FROZEN_CODED_DATA, FakeDriveDoorway


def test_setters_and_getters():
    config = {"_root_folder_id": "root"}
    drive_ids.set_class_sheet(config, "xxxx1234", "ciscategorial", "abc", 2)
    drive_ids.set_status_sheet_id(config, "xxxx1234", "st")
    drive_ids.set_notification_issue(config, "xxxx1234", "12")
    assert drive_ids.languages(config) == ["xxxx1234"]
    assert drive_ids.class_sheets(config, "xxxx1234") == {"ciscategorial": "abc"}
    assert drive_ids.class_sheet_id(config, "xxxx1234", "proform") is None
    assert drive_ids.class_sheet_version(config, "xxxx1234", "ciscategorial") == 2
    assert drive_ids.status_sheet_id(config, "xxxx1234") == "st"
    assert drive_ids.notification_issue(config, "xxxx1234") == 12
    drive_ids.remove_class_sheet(config, "xxxx1234", "ciscategorial")
    assert drive_ids.class_sheets(config, "xxxx1234") == {}
    with pytest.raises(KeyError):
        drive_ids.class_sheet_version(config, "xxxx1234", "ciscategorial")


def _door():
    return drive_door.CheckedDoorway(FakeDriveDoorway.from_fixtures())


def _saved_manifest():
    return json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_construction_tabs_are_the_labelled_construction_tabs():
    """Each class sheet's labelled construction tabs are the constructions
    the manifest recorded when the data was captured."""
    door, saved = _door(), _saved_manifest()
    config = FakeDriveDoorway.drive_config()
    for lang in drive_ids.languages(config):
        for cls, sid in drive_ids.class_sheets(config, lang).items():
            assert (door.open_spreadsheet(sid).construction_tabs()
                    == saved[lang]["sheets"][cls]["constructions"]), (lang, cls)


def test_publish_manifest_command(monkeypatch, tmp_path):
    """publish-manifest: a dry run uploads nothing; --apply replaces the
    manifest on Drive with the rebuilt copy and saves its ID."""
    import io
    import sys
    from contextlib import redirect_stdout

    from coding import drive_doorway
    from tests.command_runner import run_command
    from tests.fake_drive import MANIFEST_FILE_ID, use_frozen_coded_data

    fake = FakeDriveDoorway.from_fixtures()
    use_frozen_coded_data(monkeypatch, tmp_path)
    saved = []
    monkeypatch.setattr(sys.modules["coding.drive"], "_load_drive_config",
                        FakeDriveDoorway.drive_config)
    monkeypatch.setattr(sys.modules["coding.drive"], "_save_drive_config", saved.append)
    drive_doorway.set_doorway(fake)
    # Make the manifest on Drive stale, as a command that edited it by hand would.
    fake.file(MANIFEST_FILE_ID).content = json.dumps({"stan1293": {"sheets": {}}}).encode()
    try:
        for argv in (["publish-manifest"], ["publish-manifest", "--apply"]):
            monkeypatch.setattr(sys, "argv", argv)
            with redirect_stdout(io.StringIO()) as out:
                run_command(manifest_copy, "publish-manifest")
            if "--apply" not in argv:
                assert "Would publish" in out.getvalue()
                assert fake.download_file_json(MANIFEST_FILE_ID) == {"stan1293": {"sheets": {}}}
                assert saved == []
    finally:
        drive_doorway.set_doorway(None)
    published = fake.download_file_json(MANIFEST_FILE_ID)
    assert sorted(published) == ["arao1248", "stan1293", "synth0001"]
    assert published["stan1293"]["sheets"]
    assert saved and saved[-1]["_planars_config_file_id"] == MANIFEST_FILE_ID


def test_rebuilt_manifest_matches_the_saved_one():
    """The manifest rebuilt from the ID file and the sources says what the
    saved one says, but for keys nothing reads any more."""
    saved = _saved_manifest()
    built = manifest_copy.build(_door(), FakeDriveDoorway.drive_config(), FROZEN_CODED_DATA)
    assert sorted(built) == sorted(saved)
    dead = {"biuniqueness_stage1_spreadsheet_id", "biuniqueness_stage1_url"}
    for lang, entry in saved.items():
        want = {k: v for k, v in entry.items() if k not in dead}
        got = dict(built[lang])
        for info in got["sheets"].values():
            info.pop("version")
        for info in want["sheets"].values():
            info.pop("version", None)
        assert got == want, lang
