"""Check collaborator notes docs for new content and file GitHub issues.

Each language has one Google Doc in its Drive folder where collaborators write
freeform observations, questions, and concerns. This command reads those docs
daily, detects new content, and files or updates one open GitHub issue per
annotator containing the new notes plus a ready-to-paste Claude triage prompt.

After filing/updating an issue, an acknowledgment line is appended to the doc
so the collaborator knows their notes were received.

Each Doc's text, acknowledgment lines left out, is kept in planars-data as
the language's record, ``records/notes.txt`` (``file_door.notes_text``;
Phase 10 unit 16, docs/plain-record-design.md § 3.2), archived and logged at
every change. What is new is the difference between the Doc and that record,
and the issue quotes only the lines added or changed since. A change that
adds nothing (a note deleted) is recorded without an issue. The record is
written right after the language's acknowledgment, so a crash cannot make a
retry treat already-reported content as new (#280). (Until 2026-10-30 a hash
in the state file stood in for the text; a language's first run since then
reads that hash once, to tell whether the Doc still holds only what was
reported, and the hash is then dropped.)

A language with no notes Doc yet gets one made on ``--apply``; its ID goes in
the ID file (drive_config.json), which also lists the languages checked. One
issue per annotator covers every language that annotator has: the issue
number is kept in ``notes_state.json`` (``state_files.NOTES_STATE_PATH``,
``_annotator_issues``), saved right after each issue, and preferred over a
title search, so renaming the issue doesn't start a second thread. A closed
issue is never reused (closing is how the coordinator marks a batch
triaged), so new notes after that start a fresh issue.

Usage:
    python -m coding check-notes          # dry run (no writes)
    python -m coding check-notes --apply  # file issues, write back to docs, save state
    python -m coding check-notes --lang arao1248 --apply
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from datetime import date
from typing import Dict, List, Optional, Tuple

from . import file_door, issues, state_files


def _load_notes_state() -> Dict:
    path = state_files.NOTES_STATE_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_notes_state(state: Dict) -> None:
    """Only the issue numbers are state now; a language's own entry (the old
    hash and dates) is dropped once its text is recorded."""
    file_door.write_state(file_door.notes_state(), json.dumps(state, indent=2))


def _old_hash(text: str) -> str:
    """The hash the state file kept until 2026-10-30, read once per language
    to tell whether its Doc still holds only what was last reported."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _new_lines(recorded: str, now: str) -> List[str]:
    """The Doc's lines added or changed since the record, in Doc order;
    blank lines and deletions left out."""
    return [line[2:] for line in difflib.ndiff(recorded.splitlines(), now.splitlines())
            if line.startswith("+ ") and line[2:].strip()]


def doc_url(doc_id: str) -> str:
    return f"https://docs.google.com/document/d/{doc_id}"


def _get_open_notes_issue(annotator: str, state: Dict) -> Optional[int]:
    """Return the open collaborator-notes issue number for this annotator, if any.

    Prefers the ID stored in state["_annotator_issues"][annotator] (set once
    an issue is found or created) over a fresh title-substring search -- a
    stored ID survives the issue being renamed, which a substring match does
    not (this was issue-lookup's half of collaborator_notes_surfaced_state's
    drift_risk in facts.yaml: a manually-renamed issue silently stopped being
    found, and the next run opened a new thread instead of continuing the
    old one). Falls back to the substring search only when no ID is stored
    yet -- covers an issue filed before this tracking existed, or state that
    fell out of sync -- and backfills the ID once found, so the fallback is
    only ever needed once per annotator.

    A CLOSED issue is deliberately NOT reused: closing is how a coordinator
    marks a batch of notes as triaged (see CLAUDE.md's collaborator-notes
    label), so new content afterward should start a fresh issue, not reopen
    an already-handled one. The stored ID is dropped in that case so the
    caller creates a new issue and this function stores its ID instead.
    """
    annotator_issues = state.setdefault("_annotator_issues", {})
    stored = annotator_issues.get(annotator)
    if stored is not None:
        # Anything but a confirmed OPEN (closed, deleted, unreadable) means
        # stop trusting the stored ID and fall back.
        if issues.is_open(stored):
            return stored
        annotator_issues.pop(annotator, None)

    number = issues.find_open("collaborator-notes", title_contains=annotator)
    if number is not None:
        annotator_issues[annotator] = number
    return number


def _file_or_update_issue(annotator: str, body: str, state: Dict) -> None:
    today = date.today().isoformat()
    open_issue = _get_open_notes_issue(annotator, state)
    if open_issue:
        issues.comment(open_issue, body)
        print(f"  → Commented on issue #{open_issue}")
    else:
        issue_number = issues.create("collaborator-notes",
                                     f"Collaborator notes — {annotator} ({today})", body)
        state.setdefault("_annotator_issues", {})[annotator] = issue_number
        print(f"  → Created issue #{issue_number}")


def _build_issue_body(
    annotator: str,
    lang_notes: List[Tuple[str, str, str]],  # [(display_name, new lines, Doc URL), ...]
) -> str:
    """The issue (or comment) for one annotator: per language, the lines new
    or changed since the last report, and a link to the whole Doc."""
    today = date.today().isoformat()
    lines = [
        f"## Collaborator notes — {annotator} — {today}",
        "",
    ]
    for display_name, notes_text, url in lang_notes:
        lines += [
            f"### {display_name}",
            "",
            f"New or changed since the last report ([the whole notes Doc]({url})):",
            "",
            notes_text.strip(),
            "",
        ]
    lines += [
        "---",
        "",
        "## Ready-to-paste Claude prompt",
        "",
        f"The following notes were written by {annotator} in their annotation notes "
        "document(s). Please identify items that should become GitHub issues.",
        "For each actionable item, suggest:",
        "- A concise issue title",
        "- Appropriate label(s) (`diagnostics` / `needs-input` / `infrastructure` / `bug`)",
        "- A one-sentence description of the issue",
        "",
        "When done, share the list with the coordinator for review and filing.",
        "",
        "---",
        "",
        "**Notes new since the last report (raw; earlier ones are in the Doc):**",
        "",
    ]
    for display_name, notes_text, _ in lang_notes:
        lines += [
            f"**{display_name}:**",
            "",
            "```",
            notes_text.strip(),
            "```",
            "",
        ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding check-notes`."""
    ap = argparse.ArgumentParser(
        description="Check collaborator notes docs for new content and file issues."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="file/update GitHub issues, acknowledge in doc, save state (default: dry run)",
    )
    ap.add_argument(
        "--lang", metavar="LANG_ID", dest="lang",
        help="restrict to this language",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()
    apply = args.apply
    lang_filter = args.lang

    if not apply:
        print("DRY RUN — pass --apply to file issues, write back to docs, and save state.")
        print()

    from .drive import (
        _strip_acknowledgment_lines, _load_drive_config, _save_drive_config,
        acknowledgment_line,
    )
    from . import drive_ids
    from .drive_doorway import get_doorway
    from planars.languages import get_display_name, get_entry

    print("Connecting to Google APIs...")
    doorway = get_doorway()
    config = _load_drive_config()

    state = _load_notes_state()
    today = date.today().isoformat()

    # Collect new-content languages grouped by annotator.
    # annotator_notes: annotator -> [(display_name, new lines, Doc URL)]
    annotator_notes: Dict[str, List[Tuple[str, str, str]]] = {}
    # (lang_id, doc_id, the Doc's text) to acknowledge and record after the
    # issue is filed.
    to_acknowledge: List[Tuple[str, str, str]] = []
    config_dirty = False

    def record(lang_id: str, text: str, why: str) -> None:
        """Keep the Doc's text as the language's record, and drop the
        language's old state entry (its hash), which the record replaces."""
        if not apply:
            return
        file_door.write(file_door.notes_text(lang_id), text, why=why)
        if state.pop(lang_id, None) is not None:
            _save_notes_state(state)

    for lang_id in drive_ids.languages(config):
        if lang_filter and lang_id != lang_filter:
            continue

        doc_id = config[lang_id].get("notes_doc_id")
        if not doc_id:
            # Create-on-first-use: generate the doc now and record it in the ID file.
            folder_id = config[lang_id].get("folder_id")
            if not folder_id:
                print(f"[{lang_id}] No folder_id in the ID file — skipping")
                continue
            if apply:
                from .drive import create_notes_doc
                try:
                    doc_id = create_notes_doc(doorway, lang_id, folder_id)
                    config[lang_id]["notes_doc_id"] = doc_id
                    config_dirty = True
                    print(f"[{lang_id}] Created notes doc: https://docs.google.com/document/d/{doc_id}")
                except Exception as e:
                    print(f"[{lang_id}] Could not create notes doc: {e}")
                    continue
            else:
                print(f"[{lang_id}] No notes_doc_id in the ID file (would create on --apply)")
                continue

        lang_entry = get_entry(lang_id) or {}
        annotator = lang_entry.get("meta", {}).get("annotator") or "Unknown"
        display_name = get_display_name(lang_id)

        try:
            raw_text = doorway.get_doc_text(doc_id)
        except Exception as e:
            print(f"[{lang_id}] Could not read notes doc: {e}")
            continue

        collaborator_text = _strip_acknowledgment_lines(raw_text)
        recorded = file_door.read(file_door.notes_text(lang_id))
        if recorded is None:
            # This language's first run since the text began to be kept: its
            # old hash says whether the Doc holds only what was reported.
            old = state.get(lang_id, {}).get("notes_hash")
            if old is not None and old == _old_hash(collaborator_text):
                record(lang_id, collaborator_text,
                       "the notes Doc as it stood when its text began to be kept "
                       "(all of it reported before)")
                print(f"[{lang_id}] No new notes.")
                continue
            recorded = ""

        if collaborator_text == recorded:
            print(f"[{lang_id}] No new notes.")
            continue

        new = _new_lines(recorded, collaborator_text)
        if not new:
            # Emptied, or notes deleted: nothing for anyone to read, but the
            # record keeps the change (and the archive what was there).
            record(lang_id, collaborator_text, "read from the notes Doc (nothing added)")
            print(f"[{lang_id}] Notes doc changed with nothing added — recorded, no issue.")
            continue

        print(f"[{lang_id}] New notes detected ({annotator}).")
        annotator_notes.setdefault(annotator, []).append(
            (display_name, "\n".join(new), doc_url(doc_id)))
        to_acknowledge.append((lang_id, doc_id, collaborator_text))

    # File or update one issue per annotator.
    for annotator, lang_notes_list in annotator_notes.items():
        print(f"\nFiling/updating issue for: {annotator}")
        body = _build_issue_body(annotator, lang_notes_list)

        if apply:
            _file_or_update_issue(annotator, body, state)
            # Persist the issue-ID tracking right away, same incremental-save
            # reasoning as the #280 fix below -- don't lose a just-created
            # issue's ID to a later crash in this loop or the next one.
            _save_notes_state(state)
        else:
            print("  [dry run] Would file/update issue with body:")
            print("  " + "\n  ".join(body.splitlines()[:10]) + "\n  ...")

    # Acknowledge in each Doc, then record its text. Recorded right away,
    # language by language, not once at the end: a crash after an
    # acknowledgment must not leave the old record, or a retry re-reports
    # this Doc's content and acknowledges it again (issue #280).
    if to_acknowledge:
        ack_text = acknowledgment_line(today)
        for lang_id, doc_id, text in to_acknowledge:
            if apply:
                try:
                    doorway.append_doc_text(doc_id, ack_text)
                    print(f"[{lang_id}] Acknowledgment appended to notes doc.")
                except Exception as e:
                    print(f"[{lang_id}] Could not append acknowledgment: {e}")
            record(lang_id, text, "read from the notes Doc; the new lines reported on "
                                  "the annotator's collaborator-notes issue")

    # The ID file, if a notes Doc was made.
    if apply:
        if config_dirty:
            _save_drive_config(config)
            print("ID file updated with new notes_doc_id(s).")

    if not annotator_notes:
        print("\nNo new notes to report.")
