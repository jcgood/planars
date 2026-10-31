"""Who edited a Drive file (Phase 10 unit 16c; docs/plain-record-design.md § 3.3).

`people.editors` turns the doorway's `list_revisions` into names: everyone
but the account the tooling runs as, after a given time, never an address,
and never the name a person gives themselves in Drive.
"""
from coding import drive_door, people
from fake_drive import FakeDriveDoorway

UNLISTED = people.UNLISTED_EDITOR


def _revisions(*extra):
    fake = FakeDriveDoorway()
    file_id = fake.seed_doc("notes")
    fake.seed_revision(file_id, "2026-10-29T10:00:00.000Z", "Jeff Good", me=True)
    fake.seed_revision(file_id, "2026-10-29T11:00:00.500Z", "adam t", "annotator@example.org")
    fake.seed_revision(file_id, "2026-10-30T09:00:00Z", "A Visitor", "visitor@example.org")
    fake.seed_revision(file_id, "2026-10-30T09:30:00Z", "adam t", "annotator@example.org")
    for when, name, email in extra:
        fake.seed_revision(file_id, when, name, email)
    # Read through the Drive door, as commands do.
    return drive_door.CheckedDoorway(fake, mode=drive_door.ENFORCE).list_revisions(file_id)


def test_the_tooling_account_is_left_out_and_people_are_named_from_people_yaml():
    assert people.editors(_revisions()) == ["Adam Tallman", UNLISTED]


def test_only_revisions_after_the_given_time_count():
    assert people.editors(_revisions(), since="2026-10-29T11:00:00Z") == \
        ["Adam Tallman", UNLISTED]
    assert people.editors(_revisions(), since="2026-10-29T11:00:01Z") == \
        [UNLISTED, "Adam Tallman"]
    assert people.editors(_revisions(), since="2026-10-30T10:00:00Z") == []


def test_no_address_and_no_outsiders_name_is_returned():
    names = people.editors(_revisions())
    assert not any("@" in name for name in names)
    assert "A Visitor" not in names


def test_a_drive_name_copying_a_listed_persons_is_not_taken_for_them():
    revisions = _revisions(("2026-10-31T08:00:00Z", "Adam Tallman", "impostor@example.org"))
    assert people.editors(revisions, since="2026-10-31T00:00:00Z") == [UNLISTED]
