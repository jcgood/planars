"""Decision logs and the rule that a closed diagnostics or linguistics issue
has its decision in one (coding/decisions.py; Phase 10 unit 16e,
docs/plain-record-design.md § 4)."""
from __future__ import annotations

import csv
import io
import sys

import pytest

from coding import decisions, file_door, issues
from command_runner import run_command

LANG = "stan1293"


@pytest.fixture
def logs(monkeypatch, tmp_path):
    """The framework log in tmp_path (never this repository's, so nothing is
    committed) and an empty language folder for the language log."""
    monkeypatch.setattr(decisions, "FRAMEWORK_LOG", tmp_path / "decisions.tsv")
    (file_door.CODED_DATA / LANG).mkdir(parents=True)
    return tmp_path


@pytest.fixture
def labelled(github):
    github.labels = [{"name": e["name"], "color": e["color"], "description": e["description"]}
                     for e in issues.load_labels()]
    return github


def record_decision(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["record-decision", *argv])
    run_command(decisions, "record-decision")


def rows(text):
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def test_the_needs_decision_labels_are_diagnostics_and_linguistics():
    assert issues.decision_labels() == ["diagnostics", "linguistics"]


def test_the_framework_log_in_the_repository_has_the_columns():
    header = decisions.ROOT.joinpath("schemas", "decisions.tsv").read_text(
        encoding="utf-8").splitlines()[0]
    assert tuple(header.split("\t")) == decisions.COLUMNS


def test_without_apply_nothing_is_written_or_posted(logs, labelled, monkeypatch, capsys):
    n = labelled.seed_issue("Keep vp_ellipsis", "diagnostics")
    record_decision(monkeypatch, "--issue", str(n), "--by", "Adam Tallman",
                    "--decision", "Keep vp_ellipsis as one construction.")
    assert "Would add to" in capsys.readouterr().out
    assert not decisions.FRAMEWORK_LOG.exists()
    assert labelled.issue(n)["state"] == "OPEN" and n not in labelled.comments


def test_a_framework_decision_is_logged_commented_and_closes_the_issue(logs, labelled, monkeypatch):
    n = labelled.seed_issue("Keep vp_ellipsis", "diagnostics")
    record_decision(monkeypatch, "--issue", str(n), "--by", "Adam Tallman", "--decision",
                    "Keep vp_ellipsis as one construction.", "--scope", "proform", "--apply")
    [line] = rows(decisions.FRAMEWORK_LOG.read_text(encoding="utf-8"))
    assert line["issue"] == f"#{n}" and line["decided by"] == "Adam Tallman"
    assert line["decision"] == "Keep vp_ellipsis as one construction."
    assert line["scope"] == "proform"
    assert labelled.issue(n)["state"] == "CLOSED"
    assert "Keep vp_ellipsis as one construction." in labelled.comments[n][-1]
    assert n in decisions.recorded_issues()


def test_a_language_decision_goes_through_the_door(logs, labelled, monkeypatch):
    n = labelled.seed_issue("English: what is -n?", "diagnostics")
    record_decision(monkeypatch, "--issue", str(n), "--by", "Adam Tallman", "--lang", LANG,
                    "--decision", "-n is the participle.", "--apply")
    target = file_door.decisions(LANG)
    assert target.path == file_door.CODED_DATA / LANG / "decisions.tsv"
    [line] = rows(file_door.read(target))
    assert line["decision"] == "-n is the participle."
    # The change log says so, naming the issue.
    log = file_door.change_log(LANG).read_text(encoding="utf-8")
    assert f"decision for #{n}" in log and "\tdecisions.tsv\t" in log
    assert not decisions.FRAMEWORK_LOG.exists()
    assert n in decisions.recorded_issues()


def test_a_repeated_run_writes_no_second_line(logs, labelled, monkeypatch):
    n = labelled.seed_issue("Settles two things", "linguistics")
    argv = ("--issue", str(n), "--by", "Adam Tallman", "--decision", "One thing.",
            "--keep-open", "--apply")
    record_decision(monkeypatch, *argv)
    record_decision(monkeypatch, *argv)
    assert len(rows(decisions.FRAMEWORK_LOG.read_text(encoding="utf-8"))) == 1
    assert labelled.issue(n)["state"] == "OPEN"   # --keep-open


def test_a_name_not_in_people_yaml_is_refused(logs, labelled, monkeypatch):
    n = labelled.seed_issue("x", "diagnostics")
    with pytest.raises(SystemExit) as exc:
        record_decision(monkeypatch, "--issue", str(n), "--by", "Adam Talman",
                        "--decision", "x", "--apply")
    assert "not a name in planars-data's people.yaml" in str(exc.value)
    assert not decisions.FRAMEWORK_LOG.exists()


def test_an_issue_closed_without_a_decision_is_reopened(logs, labelled):
    after = labelled.seed_issue("Closed after the rule began", "diagnostics", state="CLOSED",
                                closed_at="2026-11-02T10:00:00Z")
    before = labelled.seed_issue("Closed before it", "linguistics", state="CLOSED",
                                 closed_at="2026-10-20T10:00:00Z")
    tooling = labelled.seed_issue("A tooling bug", "bug", state="CLOSED",
                                  closed_at="2026-11-02T10:00:00Z")
    assert [i["number"] for i in decisions.unrecorded()] == [after]
    assert decisions.reopen_unrecorded() == [after]
    assert labelled.issue(after)["state"] == "OPEN"
    assert f"record-decision --issue {after}" in labelled.comments[after][-1]
    assert labelled.issue(before)["state"] == "CLOSED"
    assert labelled.issue(tooling)["state"] == "CLOSED"


def test_a_recorded_issue_is_not_reopened(logs, labelled, monkeypatch):
    n = labelled.seed_issue("Decided", "diagnostics")
    record_decision(monkeypatch, "--issue", str(n), "--by", "Adam Tallman",
                    "--decision", "Decided.", "--apply")
    labelled.issue(n)["closedAt"] = "2026-11-02T10:00:00Z"
    assert decisions.unrecorded() == []


def test_a_batch_records_every_line_and_posts_nothing(logs, labelled, monkeypatch):
    a = labelled.seed_issue("Old framework call", "diagnostics", state="CLOSED",
                            closed_at="2026-11-02T10:00:00Z")
    b = labelled.seed_issue("Old English call", "linguistics", state="CLOSED",
                            closed_at="2026-11-02T10:00:00Z")
    batch = logs / "backfill.tsv"
    batch.write_text("\t".join(decisions.BATCH_COLUMNS) + "\n"
                     f"#{a}\t\t2026-08-01\tAdam Tallman; Jeff Good\tKeep it.\t\n"
                     f"{b}\t{LANG}\t\tAdam Tallman\t-n is the participle.\tv:aux\n",
                     encoding="utf-8")
    monkeypatch.setattr("coding.people._load_people",
                        lambda: {"Adam Tallman": {}, "Jeff Good": {}})
    record_decision(monkeypatch, "--batch", str(batch), "--apply")
    [line] = rows(decisions.FRAMEWORK_LOG.read_text(encoding="utf-8"))
    assert line["date"] == "2026-08-01" and line["decided by"] == "Adam Tallman; Jeff Good"
    [line] = rows(file_door.read(file_door.decisions(LANG)))
    assert line["scope"] == "v:aux"
    assert labelled.comments == {} and decisions.unrecorded() == []


def test_a_batch_with_a_bad_line_records_nothing(logs, labelled, monkeypatch):
    batch = logs / "backfill.tsv"
    batch.write_text("\t".join(decisions.BATCH_COLUMNS) + "\n"
                     "1\t\t\tAdam Tallman\tFine.\t\n"
                     "2\t\t\tSomeone Else\tNot fine.\t\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        record_decision(monkeypatch, "--batch", str(batch), "--apply")
    assert "line 3" in str(exc.value)
    assert not decisions.FRAMEWORK_LOG.exists()


def test_relabelling_takes_an_issue_out_of_the_rule(logs, labelled):
    n = labelled.seed_issue("Really a bug", "diagnostics", state="CLOSED",
                            closed_at="2026-11-02T10:00:00Z")
    issues.relabel(n, ["bug"], ["diagnostics"])
    assert labelled.issue(n)["labels"] == ["bug"]
    assert decisions.unrecorded() == []
    with pytest.raises(issues.UnknownLabel):
        issues.relabel(n, ["no-such-label"], [])
