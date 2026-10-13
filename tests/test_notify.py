"""Tests for coding/notify.py.

Mostly the "decide what to do" / formatting functions. The GitHub calls go
through coding/issues.py, so the last section runs them against the
in-memory GitHub from conftest.
"""
from __future__ import annotations

from coding.notify import (
    build_change_comment,
    build_first_issue_body,
    changed_lang_ids,
    ensure_notification_issue,
    get_notification_issue,
    post_notification_comment,
)


# ---------------------------------------------------------------------------
# The live path, against the stand-in GitHub
# ---------------------------------------------------------------------------

def test_first_change_creates_a_labelled_issue_and_records_it(github):
    manifest = {"stan1293": {}}
    number, created = ensure_notification_issue("stan1293", manifest)
    assert created
    assert manifest["stan1293"]["notification_issue"] == number
    _, _, title, label, _ = github.calls_of("create")[0]
    assert (title, label) == ("Sheet updates — stan1293", "sheet-updates")


def test_later_changes_reuse_the_recorded_issue_even_when_closed(github):
    number = github.seed_issue("Sheet updates — stan1293", "sheet-updates", state="CLOSED")
    manifest = {"stan1293": {"notification_issue": number}}
    assert ensure_notification_issue("stan1293", manifest) == (number, False)
    post_notification_comment(number, "hello")
    assert github.comments[number] == ["hello"]
    assert github.calls_of("create") == []


# ---------------------------------------------------------------------------
# changed_lang_ids
# ---------------------------------------------------------------------------

def test_changed_lang_ids_empty():
    assert changed_lang_ids([]) == []


def test_changed_lang_ids_single_language():
    sheet_links = [("stan1293", "ciscategorial", "https://x/1")]
    assert changed_lang_ids(sheet_links) == ["stan1293"]


def test_changed_lang_ids_dedupes_multiple_classes_same_language():
    sheet_links = [
        ("stan1293", "ciscategorial", "https://x/1"),
        ("stan1293", "metrical", "https://x/2"),
    ]
    assert changed_lang_ids(sheet_links) == ["stan1293"]


def test_changed_lang_ids_multiple_languages_first_seen_order():
    sheet_links = [
        ("arao1248", "ciscategorial", "https://x/1"),
        ("stan1293", "metrical", "https://x/2"),
        ("arao1248", "noninterruption", "https://x/3"),
    ]
    assert changed_lang_ids(sheet_links) == ["arao1248", "stan1293"]


# ---------------------------------------------------------------------------
# get_notification_issue
# ---------------------------------------------------------------------------

def test_get_notification_issue_present():
    manifest = {"stan1293": {"notification_issue": 243}}
    assert get_notification_issue("stan1293", manifest) == 243


def test_get_notification_issue_absent_lang_field():
    manifest = {"stan1293": {}}
    assert get_notification_issue("stan1293", manifest) is None


def test_get_notification_issue_absent_lang_entirely():
    manifest = {}
    assert get_notification_issue("stan1293", manifest) is None


def test_get_notification_issue_does_not_confuse_languages():
    manifest = {
        "stan1293": {"notification_issue": 243},
        "arao1248": {"notification_issue": 250},
    }
    assert get_notification_issue("arao1248", manifest) == 250
    assert get_notification_issue("stan1293", manifest) == 243


# ---------------------------------------------------------------------------
# build_first_issue_body
# ---------------------------------------------------------------------------

def test_build_first_issue_body_mentions_lang_id():
    body = build_first_issue_body("stan1293")
    assert "stan1293" in body


def test_build_first_issue_body_says_subscribe_not_watch():
    body = build_first_issue_body("stan1293")
    assert "Subscribe" in body
    assert "Watch" in body  # mentioned, but to explain why NOT to use it
    assert "not \"Watch\" the" in body or "not Watch the" in body.replace('"', "")


def test_build_first_issue_body_explains_repo_watch_would_flood():
    body = build_first_issue_body("stan1293")
    assert "flood" in body.lower()


def test_build_first_issue_body_mentions_manifest_field():
    body = build_first_issue_body("stan1293")
    assert "sheets_manifest.json" in body
    assert "notification_issue" in body


# ---------------------------------------------------------------------------
# build_change_comment
# ---------------------------------------------------------------------------

def test_build_change_comment_lists_affected_sheets():
    comment = build_change_comment(
        "stan1293",
        [("ciscategorial", "https://sheets/1"), ("metrical", "https://sheets/2")],
        None,
    )
    assert "ciscategorial" in comment
    assert "https://sheets/1" in comment
    assert "metrical" in comment
    assert "https://sheets/2" in comment


def test_build_change_comment_includes_folder_url_when_given():
    comment = build_change_comment(
        "stan1293",
        [("ciscategorial", "https://sheets/1")],
        "https://drive/folder",
    )
    assert "https://drive/folder" in comment
    assert "Bookmark this instead" in comment


def test_build_change_comment_omits_folder_section_when_absent():
    comment = build_change_comment(
        "stan1293",
        [("ciscategorial", "https://sheets/1")],
        None,
    )
    assert "Bookmark this instead" not in comment


def test_build_change_comment_mentions_lang_id_in_heading():
    comment = build_change_comment("stan1293", [], None)
    assert "stan1293" in comment


def test_build_change_comment_no_sheets_no_folder_still_returns_heading():
    comment = build_change_comment("stan1293", [], None)
    assert comment.strip() != ""
    assert "Affected sheets" not in comment


def test_build_change_comment_includes_status_sheet_url_when_given():
    comment = build_change_comment(
        "stan1293",
        [("ciscategorial", "https://sheets/1")],
        None,
        status_sheet_url="https://sheets/status_stan1293",
    )
    assert "https://sheets/status_stan1293" in comment
    assert "Status/links page" in comment


def test_build_change_comment_omits_status_sheet_section_when_absent():
    comment = build_change_comment(
        "stan1293",
        [("ciscategorial", "https://sheets/1")],
        None,
    )
    assert "Status/links page" not in comment
