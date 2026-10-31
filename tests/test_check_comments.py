"""check-comments: new or changed Comments cells become one issue per language."""
from __future__ import annotations

import json
import sys

import pytest

from coding import check_comments, state_files
from command_runner import run_command
from fake_drive import point_coded_data_at
from planars.schema_values import ELEMENT_ROW_COLUMNS, trailing_columns_for

LANG = "stan1293"
TAB = ("ciscategorial", "general")


def _write_tab(coded, rows, columns=None):
    folder = coded / LANG / TAB[0]
    folder.mkdir(parents=True, exist_ok=True)
    columns = columns or ELEMENT_ROW_COLUMNS + ["n-combines"] + trailing_columns_for(LANG)
    lines = ["\t".join(columns)] + ["\t".join(r) for r in rows]
    (folder / f"{TAB[1]}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row(element, pos_name, pos_num, answer="y", example="", source="", comment=""):
    return [element, pos_name, pos_num, answer, example, source, comment]


@pytest.fixture
def coded(tmp_path, monkeypatch):
    coded = tmp_path / "coded"
    point_coded_data_at(monkeypatch, coded)
    return coded


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["check-comments", "--lang", LANG, *argv])
    run_command(check_comments, "check-comments")


def _title():
    return check_comments.issue_title(LANG)


def test_new_comment_files_one_issue_with_its_row_and_a_prompt(coded, monkeypatch, github):
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "2", example="which man",
                            comment="I don't know what to do with this.")])
    _run(monkeypatch, "--apply")
    created = github.calls_of("create")
    assert len(created) == 1
    _, _, title, label, body = created[0]
    assert (title, label) == (_title(), "collaborator-comments")
    assert "I don't know what to do with this." in body
    assert "Element QWORDS" in body and "n-combines=y" in body
    assert "Example: which man" in body
    assert "Prompt for Claude" in body


def test_second_run_with_nothing_new_files_nothing(coded, monkeypatch, github):
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "2", comment="unclear")])
    _run(monkeypatch, "--apply")
    _run(monkeypatch, "--apply")
    assert len(github.calls_of("create")) == 1
    assert github.calls_of("comment") == []


def test_changed_comment_is_reported_on_the_open_issue_with_what_it_was(
        coded, monkeypatch, github):
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "2", comment="unclear")])
    _run(monkeypatch, "--apply")
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "2", comment="unclear: which man?")])
    _run(monkeypatch, "--apply")
    (_, number, body), = github.calls_of("comment")
    assert number == github.calls_of("create")[0][1]
    assert "unclear: which man?" in body and "(was: unclear)" in body


def test_renumbered_positions_do_not_report_comments_again(coded, monkeypatch, github):
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "2", comment="unclear")])
    _run(monkeypatch, "--apply")
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "3", comment="unclear")])
    _run(monkeypatch, "--apply")
    assert len(github.calls_of("create")) == 1
    assert github.calls_of("comment") == []


def test_dry_run_files_nothing_and_saves_nothing(coded, monkeypatch, github):
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "2", comment="unclear")])
    _run(monkeypatch)
    assert github.calls_of("create") == []
    assert not state_files.COMMENTS_STATE_PATH.exists()


def test_state_records_every_comment_seen(coded, monkeypatch, github):
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "2", comment="unclear"),
                       _row("also", "v:leftedge", "1")])
    _run(monkeypatch, "--apply")
    state = json.loads(state_files.COMMENTS_STATE_PATH.read_text(encoding="utf-8"))
    assert state[LANG]["seen"] == {"ciscategorial/general | QWORDS | 2": "unclear"}


def test_a_tab_the_schema_does_not_describe_fails_the_run(coded, monkeypatch, github):
    folder = coded / LANG / "no_such_class"
    folder.mkdir(parents=True)
    (folder / "general.tsv").write_text("Element\tComments\nx\thello\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "--apply")
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# Drive comment threads (Phase 10 unit 16d)
# ---------------------------------------------------------------------------

SHEET = "sheet_metrical"
DOC = "notes_doc"
ADAM = "annotator@example.org"      # Adam Tallman in tests/conftest.py's people


@pytest.fixture
def drive(coded, monkeypatch):
    """A Drive with one class sheet and a notes Doc for the language, and
    the ID file naming them."""
    from coding import drive as drive_module, drive_doorway, drive_ids
    from fake_drive import FakeDriveDoorway
    doorway = FakeDriveDoorway()
    doorway.seed_file("metrical", "application/vnd.google-apps.spreadsheet", file_id=SHEET)
    doorway.seed_doc("notes", file_id=DOC)
    config = {}
    drive_ids.set_class_sheet(config, LANG, "metrical", SHEET)
    config[LANG]["notes_doc_id"] = DOC
    monkeypatch.setattr(drive_module, "_load_drive_config", lambda: json.loads(json.dumps(config)))
    drive_doorway.set_doorway(doorway)
    yield doorway
    drive_doorway.reset_doorway()


def _record():
    return check_comments.read_drive_record(LANG)


def test_an_annotators_reply_to_the_toolings_comment_is_reported_and_recorded(
        drive, monkeypatch, github):
    notice = drive.create_comment(SHEET, "+someone@example.org 3 cells need fixing")
    drive.seed_comment(SHEET, "Fixed two; the third is right as it is.", "Adam Tallman",
                       email=ADAM, when="2026-10-31T09:00:00.000Z", reply_to=notice)
    _run(monkeypatch, "--apply")
    (_, _, title, label, body), = github.calls_of("create")
    assert (title, label) == (_title(), "collaborator-comments")
    assert "### class sheet: metrical" in body
    assert "**Adam Tallman**, reply, 2026-10-31: Fixed two; the third is right as it is." in body
    assert "in reply to the tooling's account: [address removed] 3 cells need fixing" in body
    rows = _record()
    assert [(r["author"], r["resolved"]) for r in rows] == [
        ("the tooling's account", "no"), ("Adam Tallman", "")]
    assert rows[1]["thread"] == rows[0]["comment"] == notice


def test_the_toolings_own_comments_are_recorded_but_not_reported(drive, monkeypatch, github):
    drive.create_comment(SHEET, "3 cells need fixing")
    _run(monkeypatch, "--apply")
    assert github.calls_of("create") == []
    assert [r["text"] for r in _record()] == ["3 cells need fixing"]


def test_a_comment_already_recorded_is_not_reported_again(drive, monkeypatch, github):
    drive.seed_comment(DOC, "Is 'both' allowed here?", "Adam Tallman", email=ADAM)
    _run(monkeypatch, "--apply")
    _run(monkeypatch, "--apply")
    assert len(github.calls_of("create")) == 1
    assert github.calls_of("comment") == []


def test_a_new_reply_later_comments_on_the_open_issue(drive, monkeypatch, github):
    first = drive.seed_comment(DOC, "Is 'both' allowed here?", "Adam Tallman", email=ADAM)
    _run(monkeypatch, "--apply")
    drive.seed_comment(DOC, "Never mind, found it.", "Adam Tallman", email=ADAM, reply_to=first)
    _run(monkeypatch, "--apply")
    (_, _, body), = github.calls_of("comment")
    assert "Never mind, found it." in body and "Is 'both' allowed here?" in body
    assert len(_record()) == 2


def test_cells_and_drive_comments_go_in_one_issue(drive, coded, monkeypatch, github):
    _write_tab(coded, [_row("QWORDS", "v:frontedXP", "2", comment="unclear")])
    drive.seed_comment(SHEET, "See row 12.", "Adam Tallman", email=ADAM)
    _run(monkeypatch, "--apply")
    (_, _, _, _, body), = github.calls_of("create")
    assert "Comments: unclear" in body and "See row 12." in body


def test_someone_not_in_people_yaml_is_not_named(drive, monkeypatch, github):
    drive.seed_comment(SHEET, "hello", "Some Stranger", email="stranger@example.net")
    _run(monkeypatch, "--apply")
    (_, _, _, _, body), = github.calls_of("create")
    assert "Some Stranger" not in body and "someone not in people.yaml" in body
    assert "Some Stranger" not in _record()[0]["author"]


def test_a_name_shown_in_drive_is_not_trusted_without_the_sharing_list(
        drive, monkeypatch, github):
    # Shows Adam's name, but the file isn't shared with any "Adam Tallman".
    drive.seed_comment(SHEET, "hello", "Adam Tallman")
    _run(monkeypatch, "--apply")
    assert _record()[0]["author"] == "someone not in people.yaml"


def test_a_mentioned_address_is_recorded_as_the_persons_name(drive, monkeypatch, github):
    drive.seed_comment(SHEET, f"+{ADAM} can you look?", "Adam Tallman", email=ADAM)
    _run(monkeypatch, "--apply")
    assert _record()[0]["text"] == "+Adam Tallman can you look?"


def test_dry_run_reads_drive_but_writes_no_record(drive, monkeypatch, github):
    drive.seed_comment(SHEET, "hello", "Adam Tallman", email=ADAM)
    _run(monkeypatch)
    assert github.calls_of("create") == []
    assert _record() is None


def test_an_unreadable_file_keeps_the_previous_record_and_fails_the_run(
        drive, monkeypatch, github):
    drive.seed_comment(SHEET, "hello", "Adam Tallman", email=ADAM)
    _run(monkeypatch, "--apply")

    def refuse(file_id):
        raise RuntimeError("no access")
    monkeypatch.setattr(drive, "list_comments", refuse)
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "--apply")
    assert exc.value.code == 1
    assert [r["text"] for r in _record()] == ["hello"]
