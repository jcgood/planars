"""check-comments: new or changed Comments cells become one issue per language."""
from __future__ import annotations

import json
import sys

import pytest

from coding import check_comments, state_files
from command_runner import run_command
from fake_drive import point_coded_data_at
from planars.schema_values import ELEMENT_ROW_COLUMNS, TRAILING_COLUMNS

LANG = "stan1293"
TAB = ("ciscategorial", "general")


def _write_tab(coded, rows, columns=None):
    folder = coded / LANG / TAB[0]
    folder.mkdir(parents=True, exist_ok=True)
    columns = columns or ELEMENT_ROW_COLUMNS + ["n-combines"] + TRAILING_COLUMNS
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
