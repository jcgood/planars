"""The ID file's class sheets, status sheet and notification issue
(coding/drive_ids.py), and the door's construction_tabs() (Phase 10 unit 11c)."""
from __future__ import annotations

import pytest

from coding import drive_door, drive_ids
from planars.from_sheets import _construction_tabs
from tests.fake_drive import FakeDriveDoorway


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


def test_the_door_and_the_notebooks_read_the_same_construction_tabs():
    """The door (commands) and planars.from_sheets (the Colab notebooks) each
    find a class sheet's constructions by its tabs' labels; they must agree,
    and every class sheet the ID file lists has some."""
    door, fake = _door(), FakeDriveDoorway.from_fixtures()
    config = FakeDriveDoorway.drive_config()
    for lang in drive_ids.languages(config):
        for cls, sid in drive_ids.class_sheets(config, lang).items():
            tabs = door.open_spreadsheet(sid).construction_tabs()
            assert tabs, (lang, cls)
            assert tabs == [name for name, _ws in _construction_tabs(fake.spreadsheet(sid))], \
                (lang, cls)
