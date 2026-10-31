"""Tests for coding/issues.py — the one GitHub issue path and the label registry.

Phase 10 unit 10 (issue #271). Runs against the in-memory GitHub that
conftest installs for every test.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from coding import issues

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# The registry and its copies
# ---------------------------------------------------------------------------

def test_registry_loads_and_every_entry_is_complete():
    names = [e["name"] for e in issues.load_labels()]
    assert "sheet-validation" in names and "diagnostics" in names
    assert len(names) == len(set(names))


def test_claude_md_label_table_is_current():
    """The pre-commit hook rewrites it; this catches a commit made without it."""
    text = issues.CLAUDE_MD_PATH.read_text(encoding="utf-8")
    assert issues.with_label_table(text) == text, (
        "CLAUDE.md's label table is out of date with schemas/issue_labels.yaml. "
        "Run: python -m coding issue --write-label-table")


def test_a_registry_entry_missing_a_field_is_refused(tmp_path):
    path = tmp_path / "labels.yaml"
    path.write_text("labels:\n  - {name: x, color: '000000', description: d, meaning: m}\n")
    with pytest.raises(ValueError, match="filed_by"):
        issues.load_labels(path)


@pytest.mark.parametrize("call", [
    lambda: issues.find_open("sheet-validaton"),
    lambda: issues.file_issue("sheet-validaton", "t", "b"),
    lambda: issues.create("sheet-validaton", "t", "b"),
    lambda: issues.close_open("sheet-validaton", "m"),
    lambda: issues.remind_stale("sheet-validaton", 7, "m"),
])
def test_an_unknown_label_is_refused_before_github_is_touched(call, github):
    with pytest.raises(issues.UnknownLabel, match="schemas/issue_labels.yaml"):
        call()
    assert github.calls == []


# ---------------------------------------------------------------------------
# Filing, closing, reminding
# ---------------------------------------------------------------------------

def test_file_creates_when_nothing_is_open(github):
    number, created = issues.file_issue("import-error", "Import error", "body")
    assert created and github.issue(number)["labels"] == ["import-error"]


def test_filing_under_a_label_github_lacks_creates_it_from_the_registry(github):
    # A newly registered label reaches GitHub only at the next daily sync;
    # filing must not wait for it (#310).
    entry = next(e for e in issues.load_labels() if e["name"] == "needs-fixing")
    issues.create("needs-fixing", "Values to fix", "body")
    assert github.labels == [{"name": "needs-fixing", "color": str(entry["color"]),
                              "description": entry["description"]}]
    issues.create("needs-fixing", "Values to fix again", "body")
    assert len(github.calls_of("create_label")) == 1


def test_file_comments_on_the_open_issue_by_default(github):
    open_number = github.seed_issue("Import error (yesterday)", "import-error")
    assert issues.file_issue("import-error", "Import error (today)", "new") == (open_number, False)
    assert github.comments[open_number] == ["new"]


def test_no_email_address_reaches_github(github):
    # planars is public; text quoted from a notes Doc or a Drive comment
    # (a +mention) can carry an address.
    text = "From jo.smith+x@uni.example.ac.uk: ask @adamtallman, see pkg@1.2.3"
    number = issues.create("import-error", f"About {text}", text)
    issues.comment(number, text)
    issues.edit(number, text, text)
    issues.file_issue("import-error", text, text, replace=True)
    sent = [github.issue(number)["title"], github.issue(number)["body"]] + github.comments[number]
    for out in sent:
        assert "jo.smith" not in out and issues.ADDRESS_REMOVED in out
        assert "@adamtallman" in out and "pkg@1.2.3" in out


def test_file_with_replace_rewrites_the_open_issue(github):
    open_number = github.seed_issue("Import error (yesterday)", "import-error", body="old")
    issues.file_issue("import-error", "Import error (today)", "new", replace=True)
    assert github.issue(open_number)["title"] == "Import error (today)"
    assert github.issue(open_number)["body"] == "new"
    assert open_number not in github.comments


def test_file_matching_title_ignores_other_issues_under_the_label(github):
    github.seed_issue("Something else", "diagnostics")
    number, created = issues.file_issue("diagnostics", "[x] divergent", "b", match_title=True)
    assert created


def test_the_file_command_can_match_a_per_language_title(github, tmp_path, monkeypatch):
    # sheet-updates has one issue per language: filing for Araona must not
    # comment on English's (the CLI had no way to ask, 2026-10-25).
    english = github.seed_issue("Sheet updates — stan1293", "sheet-updates")
    body = tmp_path / "body.md"
    body.write_text("note", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["issue", "--file", "sheet-updates", "--match-title",
                                      "--title", "Sheet updates — arao1248",
                                      "--body-file", str(body)])
    issues.main()
    assert english not in github.comments
    assert [i["title"] for i in github.issues] == ["Sheet updates — stan1293",
                                                   "Sheet updates — arao1248"]


def test_a_closed_issue_does_not_count_as_open(github):
    github.seed_issue("Import error", "import-error", state="CLOSED")
    assert issues.find_open("import-error") is None


def test_close_open_closes_every_open_issue_under_the_label(github):
    a = github.seed_issue("a", "sheet-drift")
    b = github.seed_issue("b", "sheet-drift")
    other = github.seed_issue("c", "import-error")
    assert issues.close_open("sheet-drift", "fixed") == [a, b]
    assert github.issue(a)["state"] == github.issue(b)["state"] == "CLOSED"
    assert github.issue(other)["state"] == "OPEN"
    assert github.comments[a] == ["fixed"]


def test_remind_comments_only_on_issues_older_than_the_limit(github):
    old = github.seed_issue("old", "sheet-drift", created_at="2026-10-01T00:00:00Z")
    github.seed_issue("new", "sheet-drift", created_at="2026-10-12T00:00:00Z")
    now = datetime(2026, 10, 13, tzinfo=timezone.utc)
    assert issues.remind_stale("sheet-drift", 7, "nudge", now=now) == [old]


def test_a_retired_label_stays_registered_but_takes_no_new_issue(github):
    """Its closed issues keep it (no label-drift), nothing new goes under it,
    and CLAUDE.md's table leaves it out."""
    retired = [e for e in issues.load_labels() if e.get("retired")]
    assert {e["name"] for e in retired} >= {"pending-changes", "diagnostics-drift"}
    with pytest.raises(issues.UnknownLabel, match="retired"):
        issues.file_issue("pending-changes", "t", "b")
    assert "`pending-changes`" not in issues.label_table()


# ---------------------------------------------------------------------------
# Keeping GitHub's labels in line
# ---------------------------------------------------------------------------

REG = [{"name": "a", "color": "ffffff", "description": "A"},
       {"name": "b", "color": "000000", "description": "B"}]


def test_label_plan_creates_edits_deletes_and_refuses():
    live = [{"name": "b", "color": "111111", "description": "B"},
            {"name": "unused", "color": "000000", "description": ""},
            {"name": "hand-made", "color": "000000", "description": ""}]
    plan = issues.label_plan(REG, live, {"unused": 0, "hand-made": 3})
    assert [(a, n) for a, n, _ in plan] == [
        ("create", "a"), ("edit", "b"), ("refuse", "hand-made"), ("delete", "unused")]


def test_label_plan_is_empty_when_github_matches():
    live = [{"name": "a", "color": "FFFFFF", "description": "A"},
            {"name": "b", "color": "000000", "description": "B"}]
    assert issues.label_plan(REG, live, {}) == []


def test_sync_dry_run_changes_nothing(github):
    github.labels = [{"name": "stray", "color": "000000", "description": ""}]
    issues.sync_labels(apply=False)
    assert [c for c in github.calls if c[0] != "list"] == []


def test_sync_apply_makes_github_match_and_closes_label_drift(github):
    issues.sync_labels(apply=True)
    assert {l["name"] for l in github.labels} == {e["name"] for e in issues.load_labels()}
    assert issues.sync_labels(apply=True) == []


def test_an_unregistered_label_in_use_files_label_drift(github):
    github.labels = [{"name": "hand-made", "color": "000000", "description": ""}]
    github.seed_issue("someone's issue", "hand-made")
    assert issues.sync_labels(apply=True) == ["hand-made"]
    drift = issues.find_open("label-drift")
    assert drift is not None and "`hand-made`" in github.issue(drift)["body"]
    assert any(l["name"] == "hand-made" for l in github.labels)  # never deleted


# ---------------------------------------------------------------------------
# One path: nothing else talks to GitHub, and every label named is registered
# ---------------------------------------------------------------------------

def _sources():
    for path in sorted((ROOT / "coding").glob("*.py")):
        yield path, path.read_text(encoding="utf-8")
    for path in sorted((ROOT / ".github").rglob("*")):
        if path.is_file():
            yield path, path.read_text(encoding="utf-8")


def test_only_coding_issues_runs_gh_for_issues_or_labels():
    pattern = re.compile(r"""gh["',\s]+(issue|label)\b""")
    offenders = [str(p.relative_to(ROOT)) for p, text in _sources()
                 if p.name != "issues.py" and pattern.search(text)]
    assert offenders == [], (
        "These files call GitHub's issue/label commands directly. File, find, "
        f"comment on or close issues through coding/issues.py instead: {offenders}")


def test_every_label_the_code_and_workflows_name_is_registered():
    registered = {e["name"] for e in issues.load_labels()}
    named = set()
    call = re.compile(r"""issues\.(?:file_issue|create|find_open|close_open|remind_stale)\(\s*["']([\w-]+)["']""")
    flag = re.compile(r"python -m coding issue\s+--(?:file|close|remind)\s+([a-z][\w-]+)")
    for path, text in _sources():
        named |= set(call.findall(text)) | set(flag.findall(text))
    assert named, "the scan found nothing — its patterns have gone stale"
    assert named - registered == set()
