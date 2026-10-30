"""Snapshot tests for `python -m coding check-notes`, run against the fake.

File 6 of 17 migrated to the Drive doorway, and the only command that touches
Google Docs — so it is the first to exercise that part of the doorway at all.

This is the one command whose whole purpose is to carry something *from* a
collaborator rather than to them: Adam writes freeform notes in a Doc, and this
reads them, files a GitHub issue, and writes an acknowledgment line back into
the Doc so he knows they arrived. The tests below are mostly about that round
trip not losing or duplicating anything.

The acknowledgment line is the subtle part. It is written into the same Doc
being watched for changes, so it has to be stripped before hashing — otherwise
every run would see its own last acknowledgment as new collaborator content and
file an issue about it, forever.

Before migrating, the old code was driven from this same stand-in Drive and
Docs through shims, across five scenarios. Output, the state file, the Doc's
contents, and the recorded Drive changes came back byte-identical afterwards.

Regenerate: `PLANARS_UPDATE_SNAPSHOTS=1 pytest tests/test_check_notes_snapshot.py`
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

from coding import check_notes, drive_doorway, state_files
from coding import drive as drive_module
from coding.drive import _ACK_PREFIX, _strip_acknowledgment_lines
from command_runner import run_command
from fake_drive import ROOT_FOLDER_ID, FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "check_notes"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANG = "arao1248"
DOC_ID = "notes_doc_arao"
NOTES = ("Position 14 looks wrong to me — the stem boundary sits left of where\n"
         "the tone rule wants it. Also: is 'both' allowed for accented?\n")


@pytest.fixture()
def env(monkeypatch, tmp_path, github):
    """A stand-in Drive with one language's notes Doc, and a scratch state file.

    `run(argv)` plays one command and returns its output. GitHub is the
    in-memory stand-in from conftest, which remembers what it filed: the
    command is supposed to comment on an annotator's open issue rather than
    file a second one, and a stub that always answered "no open issues" would
    let a regression to filing duplicates pass.
    """
    doorway = FakeDriveDoorway.from_fixtures()
    # The ID file the command reads (notes_doc_id is one of its entries).
    config = FakeDriveDoorway.drive_config()

    def seed_doc(text: str = NOTES) -> None:
        doorway.seed_doc("Araona [arao1248] — Annotation Notes", text,
                         parent_id=config[LANG]["folder_id"], file_id=DOC_ID)
        config[LANG]["notes_doc_id"] = DOC_ID

    def seed_no_doc() -> None:
        # The recording already carries a real notes_doc_id; drop it, or the
        # create-on-first-use path is never reached.
        config[LANG].pop("notes_doc_id", None)

    # In tmp_path (tests/conftest.py); written outside the door here, as
    # what is already on disk.
    state_path = state_files.NOTES_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{}", encoding="utf-8")

    saved: Dict = {}

    def save(new):
        saved.update(new)
        config.clear()
        config.update(json.loads(json.dumps(new)))

    monkeypatch.setattr(drive_module, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(drive_module, "_save_drive_config", save)
    drive_doorway.set_doorway(doorway)

    def close_issue(number: int) -> None:
        """Simulate the coordinator closing an issue after triage."""
        github.issue(number)["state"] = "CLOSED"

    def rename_issue(number: int, new_title: str) -> None:
        """Simulate a manual rename that would break a title-substring lookup."""
        github.issue(number)["title"] = new_title

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_command(check_notes, "check-notes")
        return re.sub(r"\d{4}-\d{2}-\d{2}", "DATE", buf.getvalue())

    def state() -> Dict:
        return json.loads(state_path.read_text(encoding="utf-8"))

    def set_state(new_state: Dict) -> None:
        state_path.write_text(json.dumps(new_state), encoding="utf-8")

    yield type("Env", (), {
        "doorway": doorway, "run": staticmethod(run), "state": staticmethod(state),
        "set_state": staticmethod(set_state),
        "seed_doc": staticmethod(seed_doc), "seed_no_doc": staticmethod(seed_no_doc),
        "github": github, "saved": saved,
        "close_issue": staticmethod(close_issue), "rename_issue": staticmethod(rename_issue),
    })
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


# ---------------------------------------------------------------------------
# What the coordinator sees
# ---------------------------------------------------------------------------

def test_dry_run_transcript(env):
    env.seed_doc()
    check_snapshot("dry_run.txt", env.run(["check-notes", "--lang", LANG]))


def test_apply_transcript(env):
    env.seed_doc()
    check_snapshot("apply.txt", env.run(["check-notes", "--lang", LANG, "--apply"]))


# ---------------------------------------------------------------------------
# The dry run is a dry run
# ---------------------------------------------------------------------------

def test_dry_run_files_nothing_and_writes_nothing(env):
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG])
    assert env.doorway.mutations == []
    assert env.github.calls == []
    assert env.state() == {}
    assert env.doorway.get_doc_text(DOC_ID) == NOTES


# ---------------------------------------------------------------------------
# The round trip
# ---------------------------------------------------------------------------

def test_new_notes_reach_a_github_issue(env):
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    created = env.github.calls_of("create")
    assert len(created) == 1
    _, _, title, label, _ = created[0]
    assert label == "collaborator-notes"
    assert "Collaborator notes — Adam Tallman" in title


def test_the_collaborator_is_told_their_notes_arrived(env):
    """The Doc is the only channel back to them — stdout reaches nobody."""
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    appended = env.doorway.mutations_of("append_doc_text")
    assert len(appended) == 1
    assert _ACK_PREFIX in appended[0]["text"]
    assert env.doorway.get_doc_text(DOC_ID).startswith(NOTES)


def test_the_acknowledgment_does_not_look_like_new_notes_next_time(env):
    """Otherwise every run would file an issue about its own last line."""
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    env.github.calls.clear()
    env.doorway.clear_mutations()

    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "No new notes." in out
    assert env.github.calls == []
    assert env.doorway.mutations_of("append_doc_text") == []


def test_unchanged_notes_file_nothing(env):
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    first = env.state()[LANG]["notes_hash"]
    env.github.calls.clear()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    assert env.state()[LANG]["notes_hash"] == first
    assert env.github.calls_of("create") == []


def test_notes_added_later_are_picked_up(env):
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    env.github.calls.clear()
    env.doorway.append_doc_text(DOC_ID, "One more thing: v:obj-R feels doubtful.")

    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "New notes detected" in out
    # An issue is already open for this annotator, so it comments rather than
    # filing a second one — the find-or-edit convention, not a fresh issue
    # every day.
    assert env.github.calls_of("create") == []
    assert env.github.calls_of("comment")


def test_an_empty_doc_files_nothing_but_is_remembered(env):
    env.seed_doc(text="\n   \n")
    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "Notes doc is empty" in out
    assert env.github.calls == []
    assert env.state()[LANG]["notes_hash"]


def test_only_the_collaborators_own_words_are_hashed(env):
    """Pure check on the rule the round trip depends on."""
    with_ack = NOTES + f"[2026-08-02] {_ACK_PREFIX}. Please consult with them."
    assert _strip_acknowledgment_lines(with_ack).strip() == NOTES.strip()


# ---------------------------------------------------------------------------
# Creating the Doc on first use
# ---------------------------------------------------------------------------

def test_dry_run_only_says_it_would_create_the_doc(env):
    env.seed_no_doc()
    out = env.run(["check-notes", "--lang", LANG])
    assert "would create on --apply" in out
    assert env.doorway.mutations == []


def test_apply_creates_the_doc_editable_by_the_annotator_by_name(env):
    """The annotator writes notes in this doc, so they get edit access — by
    name, like every other project file, never by link (Phase 10 unit 14,
    2026-10-12). It used to be "anyone with the link can edit"; the live docs
    had lost that grant and left the annotator view-only."""
    env.seed_no_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    created = env.doorway.mutations_of("create_file")
    doc = [c for c in created
           if c["mimetype"] == "application/vnd.google-apps.document"]
    assert len(doc) == 1
    assert doc[0]["name"] == "Araona [arao1248] — Annotation Notes"
    perms = env.doorway.mutations_of("create_permission")
    assert [(p["type"], p["role"], p["email"]) for p in perms] == [
        ("user", "writer", "annotator@example.org")]


def test_a_newly_created_doc_is_readable_and_empty(env):
    """One call makes it; there is no second step that turns it into a Doc."""
    env.seed_no_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    new_id = env.doorway.mutations_of("create_file")[0]["file_id"]
    assert env.doorway.get_doc_text(new_id) == ""


def test_the_new_docs_id_is_written_back_to_the_id_file(env):
    """Or the next run creates a second Doc and the collaborator loses the first."""
    env.seed_no_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    new_id = env.doorway.mutations_of("create_file")[0]["file_id"]
    assert env.saved[LANG]["notes_doc_id"] == new_id


# ---------------------------------------------------------------------------
# When the Doc cannot be read
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Finding 27 / the second half of #280's review: issue lookup by stored ID,
# not title-substring search, so a rename doesn't lose the thread and a
# closed (triaged) issue doesn't get silently reused.
# ---------------------------------------------------------------------------

def test_the_issue_id_is_stored_after_filing(env):
    """So later runs don't need the title search at all."""
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    assert env.state()["_annotator_issues"]["Adam Tallman"] > 0


def test_a_renamed_but_still_open_issue_is_still_found(env):
    """A title-substring search would miss this; the stored ID does not."""
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    issue_number = env.state()["_annotator_issues"]["Adam Tallman"]
    env.rename_issue(issue_number, "Renamed by someone, no longer mentions the annotator")
    env.github.calls.clear()
    env.doorway.append_doc_text(DOC_ID, "One more thing: v:obj-R feels doubtful.")

    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "New notes detected" in out
    assert env.github.calls_of("create") == []
    commented = env.github.calls_of("comment")
    assert commented and commented[0][1] == issue_number


def test_a_closed_issue_is_not_reused(env):
    """Closing is how the coordinator marks a batch triaged -- new content
    after that starts a fresh issue rather than reopening an old one."""
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    first_issue = env.state()["_annotator_issues"]["Adam Tallman"]
    env.close_issue(first_issue)
    env.github.calls.clear()
    env.doorway.append_doc_text(DOC_ID, "One more thing: v:obj-R feels doubtful.")

    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "New notes detected" in out
    created = env.github.calls_of("create")
    assert len(created) == 1
    second_issue = env.state()["_annotator_issues"]["Adam Tallman"]
    assert second_issue != first_issue


def test_an_open_issue_predating_id_tracking_is_found_by_title_and_backfilled(env):
    """Migration path: an issue that already existed before this fix has no
    stored ID yet, so the title search is still needed once, and afterward
    the ID takes over."""
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    # Simulate pre-fix state: forget the ID this run just stored, as if it
    # had been filed before _annotator_issues tracking existed.
    state = env.state()
    del state["_annotator_issues"]["Adam Tallman"]
    env.set_state(state)

    env.github.calls.clear()
    env.doorway.append_doc_text(DOC_ID, "One more thing: v:obj-R feels doubtful.")
    env.run(["check-notes", "--lang", LANG, "--apply"])
    assert env.github.calls_of("create") == []
    assert env.github.calls_of("comment")
    # Backfilled for next time.
    assert env.state()["_annotator_issues"]["Adam Tallman"]


def test_an_unreadable_doc_is_reported_and_the_language_is_skipped(env, monkeypatch):
    env.seed_doc()

    def refuse(*args, **kwargs):
        raise RuntimeError("no")

    monkeypatch.setattr(env.doorway, "get_doc_text", refuse)
    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "Could not read notes doc" in out
    assert env.github.calls == []
    # Not recorded as checked, so tomorrow's run tries again.
    assert LANG not in env.state()
