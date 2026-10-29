"""Check collaborator notes docs for new content and file GitHub issues.

Each language has one Google Doc in its Drive folder where collaborators write
freeform observations, questions, and concerns. This command reads those docs
daily, detects new content, and files or updates one open GitHub issue per
annotator containing the new notes plus a ready-to-paste Claude triage prompt.

After filing/updating an issue, an acknowledgment line is appended to the doc
so the collaborator knows their notes were received.

New content is detected by a hash of the Doc's text with the acknowledgment
lines stripped, kept per language in ``notes_state.json``
(``state_files.NOTES_STATE_PATH``, written through the local-file door). A
language with no notes Doc yet gets one made on ``--apply``; its ID goes in
the ID file (drive_config.json), which also lists the languages checked, and
the manifest copy is republished. One issue per
annotator covers every language that annotator has: the issue number is
stored in the state (``_annotator_issues``) and preferred over a title
search, so renaming the issue doesn't start a second thread. A closed issue
is never reused (closing is how the coordinator marks a batch triaged), so
new notes after that start a fresh issue. The state is saved right after
each issue and each acknowledgment, so a crash cannot make a retry treat
already-reported content as new (#280).

Usage:
    python -m coding check-notes          # dry run (no writes)
    python -m coding check-notes --apply  # file issues, write back to docs, save state
    python -m coding check-notes --lang arao1248 --apply
"""
from __future__ import annotations

import argparse
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
    file_door.write_state(file_door.notes_state(), json.dumps(state, indent=2))


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


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
    lang_notes: List[Tuple[str, str]],  # [(display_name, notes_text), ...]
) -> str:
    today = date.today().isoformat()
    lines = [
        f"## Collaborator notes — {annotator} — {today}",
        "",
    ]
    for display_name, notes_text in lang_notes:
        lines += [
            f"### {display_name}",
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
        "**Notes (raw):**",
        "",
    ]
    for display_name, notes_text in lang_notes:
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
    from . import drive_ids, manifest_copy
    from .drive_doorway import get_doorway
    from planars.languages import get_display_name, get_entry

    print("Connecting to Google APIs...")
    doorway = get_doorway()
    config = _load_drive_config()

    state = _load_notes_state()
    today = date.today().isoformat()

    # Collect new-content languages grouped by annotator.
    # annotator_notes: annotator -> [(display_name, raw_text)]
    annotator_notes: Dict[str, List[Tuple[str, str]]] = {}
    # Track (lang_id, doc_id, new_hash) for write-back after issue filing.
    to_acknowledge: List[Tuple[str, str, str]] = []
    # Languages successfully checked (for last_checked state update on --apply).
    checked_lang_ids: List[str] = []
    config_dirty = False

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
        new_hash = _hash_text(collaborator_text)

        lang_state = state.get(lang_id, {})
        stored_hash = lang_state.get("notes_hash", "")

        checked_lang_ids.append(lang_id)

        if new_hash == stored_hash:
            print(f"[{lang_id}] No new notes.")
            continue

        # Content has changed.
        stripped = collaborator_text.strip()
        if not stripped:
            # Doc is empty (only whitespace/ack lines) — update hash but don't file.
            state.setdefault(lang_id, {})["notes_hash"] = new_hash
            print(f"[{lang_id}] Notes doc is empty — hash updated.")
            continue

        print(f"[{lang_id}] New notes detected ({annotator}).")
        annotator_notes.setdefault(annotator, []).append((display_name, collaborator_text))
        to_acknowledge.append((lang_id, doc_id, new_hash))

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

    # Write-back acknowledgments and update state.
    if to_acknowledge:
        ack_text = acknowledgment_line(today)
        for lang_id, doc_id, new_hash in to_acknowledge:
            if apply:
                try:
                    doorway.append_doc_text(doc_id, ack_text)
                    print(f"[{lang_id}] Acknowledgment appended to notes doc.")
                except Exception as e:
                    print(f"[{lang_id}] Could not append acknowledgment: {e}")
            state.setdefault(lang_id, {})["notes_hash"] = new_hash
            state[lang_id]["last_changed"] = today
            if apply:
                # Persist immediately, not once at the end of main() -- a
                # crash between appending this acknowledgment and the final
                # save must not leave the old hash on disk, or a retry
                # re-detects this doc's content as new and re-files/
                # re-acknowledges it (issue #280).
                _save_notes_state(state)

    # Persist state, and the ID file if a notes Doc was made.
    if apply:
        for lang_id in checked_lang_ids:
            state.setdefault(lang_id, {})["last_checked"] = today
        _save_notes_state(state)
        print("\nnotes_state.json updated.")
        if config_dirty:
            _save_drive_config(config)
            manifest_copy.publish(doorway, config)
            _save_drive_config(config)
            print("ID file updated with new notes_doc_id(s); manifest copy republished.")

    if not annotator_notes:
        print("\nNo new notes to report.")
