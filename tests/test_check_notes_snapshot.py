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
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List

import pytest

from coding import check_notes, drive_doorway
from coding import drive as drive_module
from coding.drive import _ACK_PREFIX, _strip_acknowledgment_lines
from fake_drive import MANIFEST_FILE_ID, ROOT_FOLDER_ID, FakeDriveDoorway

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "coordinator" / "check_notes"
UPDATING = os.environ.get("PLANARS_UPDATE_SNAPSHOTS") == "1"

LANG = "arao1248"
DOC_ID = "notes_doc_arao"
NOTES = ("Position 14 looks wrong to me — the stem boundary sits left of where\n"
         "the tone rule wants it. Also: is 'both' allowed for accented?\n")


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """A stand-in Drive with one language's notes Doc, and a scratch state file.

    Yields (doorway, run, state_path). `run(argv, ...)` plays one command and
    returns its output; `gh` is stubbed, since filing issues is not Drive.
    """
    doorway = FakeDriveDoorway.from_fixtures()
    manifest = doorway.download_file_json(MANIFEST_FILE_ID)

    def seed_doc(text: str = NOTES) -> None:
        doorway.seed_doc("Araona [arao1248] — Annotation Notes", text,
                         parent_id=manifest[LANG]["folder_id"], file_id=DOC_ID)
        manifest[LANG]["notes_doc_id"] = DOC_ID
        doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode()

    def seed_no_doc() -> None:
        # The recording already carries a real notes_doc_id; drop it, or the
        # create-on-first-use path is never reached.
        manifest[LANG].pop("notes_doc_id", None)
        doorway.file(MANIFEST_FILE_ID).content = json.dumps(manifest).encode()

    state_path = tmp_path / "notes_state.json"
    state_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(check_notes, "NOTES_STATE_PATH", state_path)

    config = {"_planars_config_file_id": MANIFEST_FILE_ID,
              "_root_folder_id": ROOT_FOLDER_ID}
    saved: Dict = {}
    monkeypatch.setattr(drive_module, "_load_drive_config",
                        lambda: json.loads(json.dumps(config)))
    monkeypatch.setattr(drive_module, "_save_drive_config", saved.update)
    drive_doorway.set_doorway(doorway)

    gh_calls: List[List[str]] = []

    open_issues: List[Dict] = []

    def fake_run(cmd, **kwargs):
        """Stand-in gh that remembers what it filed.

        It has to: the command is supposed to comment on an annotator's open
        issue rather than file a second one, and a stub that always answers
        "no open issues" would let a regression to filing duplicates pass.
        """
        gh_calls.append([str(p) for p in cmd])
        out = ""
        if "list" in cmd:
            out = json.dumps(open_issues)
        elif "create" in cmd:
            title = cmd[cmd.index("--title") + 1]
            open_issues.append({"number": 900 + len(open_issues), "title": title})
            out = f"https://github.com/jcgood/planars/issues/{open_issues[-1]['number']}"
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(check_notes.subprocess, "run", fake_run)

    def run(argv: List[str]) -> str:
        monkeypatch.setattr(sys, "argv", argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            check_notes.main()
        text = re.sub(r"\d{4}-\d{2}-\d{2}", "DATE", buf.getvalue())
        return re.sub(r"\S*/tmp\w+\.md", "BODY_FILE", text)

    def state() -> Dict:
        return json.loads(state_path.read_text(encoding="utf-8"))

    yield type("Env", (), {
        "doorway": doorway, "run": staticmethod(run), "state": staticmethod(state),
        "seed_doc": staticmethod(seed_doc), "seed_no_doc": staticmethod(seed_no_doc),
        "gh_calls": gh_calls, "saved": saved,
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
    assert env.gh_calls == []
    assert env.state() == {}
    assert env.doorway.get_doc_text(DOC_ID) == NOTES


# ---------------------------------------------------------------------------
# The round trip
# ---------------------------------------------------------------------------

def test_new_notes_reach_a_github_issue(env):
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    created = [c for c in env.gh_calls if "create" in c]
    assert len(created) == 1
    assert "collaborator-notes" in created[0]
    assert "Collaborator notes — Adam Tallman" in " ".join(created[0])


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
    env.gh_calls.clear()
    env.doorway.clear_mutations()

    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "No new notes." in out
    assert env.gh_calls == []
    assert env.doorway.mutations_of("append_doc_text") == []


def test_unchanged_notes_file_nothing(env):
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    first = env.state()[LANG]["notes_hash"]
    env.gh_calls.clear()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    assert env.state()[LANG]["notes_hash"] == first
    assert [c for c in env.gh_calls if "create" in c] == []


def test_notes_added_later_are_picked_up(env):
    env.seed_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    env.gh_calls.clear()
    env.doorway.append_doc_text(DOC_ID, "One more thing: v:obj-R feels doubtful.")

    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "New notes detected" in out
    # An issue is already open for this annotator, so it comments rather than
    # filing a second one — the find-or-edit convention, not a fresh issue
    # every day.
    assert [c for c in env.gh_calls if "create" in c] == []
    assert [c for c in env.gh_calls if "comment" in c]


def test_an_empty_doc_files_nothing_but_is_remembered(env):
    env.seed_doc(text="\n   \n")
    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "Notes doc is empty" in out
    assert env.gh_calls == []
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


def test_apply_creates_the_doc_shared_with_anyone_holding_the_link(env):
    """Deliberately the loosest sharing in the project — see drive.create_notes_doc.

    Everything else is shared with named people, because a link is not access
    control. The notes Doc is the exception: collaborators must be able to
    reach it without an invite.
    """
    env.seed_no_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    created = env.doorway.mutations_of("create_file")
    doc = [c for c in created
           if c["mimetype"] == "application/vnd.google-apps.document"]
    assert len(doc) == 1
    assert doc[0]["name"] == "Araona [arao1248] — Annotation Notes"
    perms = env.doorway.mutations_of("create_permission")
    assert [(p["type"], p["role"]) for p in perms] == [("anyone", "writer")]


def test_a_newly_created_doc_is_readable_and_empty(env):
    """One call makes it; there is no second step that turns it into a Doc."""
    env.seed_no_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    new_id = env.doorway.mutations_of("create_file")[0]["file_id"]
    assert env.doorway.get_doc_text(new_id) == ""


def test_the_new_docs_id_is_written_back_to_the_manifest(env):
    """Or the next run creates a second Doc and the collaborator loses the first."""
    env.seed_no_doc()
    env.run(["check-notes", "--lang", LANG, "--apply"])
    new_id = env.doorway.mutations_of("create_file")[0]["file_id"]
    manifest = env.doorway.download_file_json(MANIFEST_FILE_ID)
    assert manifest[LANG]["notes_doc_id"] == new_id
    assert env.saved[LANG]["notes_doc_id"] == new_id


# ---------------------------------------------------------------------------
# When the Doc cannot be read
# ---------------------------------------------------------------------------

def test_an_unreadable_doc_is_reported_and_the_language_is_skipped(env, monkeypatch):
    env.seed_doc()

    def refuse(*args, **kwargs):
        raise RuntimeError("no")

    monkeypatch.setattr(env.doorway, "get_doc_text", refuse)
    out = env.run(["check-notes", "--lang", LANG, "--apply"])
    assert "Could not read notes doc" in out
    assert env.gh_calls == []
    # Not recorded as checked, so tomorrow's run tries again.
    assert LANG not in env.state()
