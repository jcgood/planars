"""Check collaborator notes docs for new content and file GitHub issues.

Each language has one Google Doc in its Drive folder where collaborators write
freeform observations, questions, and concerns. This command reads those docs
daily, detects new content, and files or updates one open GitHub issue per
annotator containing the new notes plus a ready-to-paste Claude triage prompt.

After filing/updating an issue, an acknowledgment line is appended to the doc
so the collaborator knows their notes were received.

Usage:
    python -m coding check-notes          # dry run (no writes)
    python -m coding check-notes --apply  # file issues, write back to docs, save state
    python -m coding check-notes --lang arao1248 --apply
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
NOTES_STATE_PATH = CODED_DATA / "notes_state.json"


def _load_notes_state() -> Dict:
    if NOTES_STATE_PATH.exists():
        return json.loads(NOTES_STATE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_notes_state(state: Dict) -> None:
    NOTES_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _get_open_notes_issue(annotator: str) -> Optional[int]:
    """Return the issue number of the first open collaborator-notes issue for this annotator."""
    result = subprocess.run(
        ["gh", "issue", "list", "--label", "collaborator-notes",
         "--state", "open", "--json", "number,title"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    issues = json.loads(result.stdout or "[]")
    for issue in issues:
        if annotator in issue.get("title", ""):
            return issue["number"]
    return None


def _file_or_update_issue(annotator: str, body_path: str) -> None:
    today = date.today().isoformat()
    open_issue = _get_open_notes_issue(annotator)
    if open_issue:
        subprocess.run(
            ["gh", "issue", "comment", str(open_issue), "--body-file", body_path],
            check=True,
        )
        print(f"  → Commented on issue #{open_issue}")
    else:
        result = subprocess.run(
            ["gh", "issue", "create",
             "--label", "collaborator-notes",
             "--title", f"Collaborator notes — {annotator} ({today})",
             "--body-file", body_path],
            capture_output=True, text=True, check=True,
        )
        url = result.stdout.strip()
        print(f"  → Created issue: {url}")


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


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    lang_filter = args[args.index("--lang") + 1] if "--lang" in args else None

    if not apply:
        print("DRY RUN — pass --apply to file issues, write back to docs, and save state.")
        print()

    from .drive import (
        _get_clients, _get_docs_client, _load_manifest_from_drive,
        _read_notes_doc_text, _strip_acknowledgment_lines, _append_to_notes_doc,
        _upload_planars_config, _load_drive_config, _save_drive_config,
        _ACK_PREFIX,
    )
    from planars.languages import get_display_name

    print("Connecting to Google APIs...")
    gc, drive = _get_clients()
    docs = _get_docs_client(gc)
    manifest = _load_manifest_from_drive(drive)
    config = _load_drive_config()
    root_folder_id = config.get("_root_folder_id")
    existing_config_file_id = config.get("_planars_config_file_id")

    state = _load_notes_state()
    today = date.today().isoformat()

    # Collect new-content languages grouped by annotator.
    # annotator_notes: annotator -> [(display_name, raw_text)]
    annotator_notes: Dict[str, List[Tuple[str, str]]] = {}
    # Track (lang_id, doc_id, new_hash) for write-back after issue filing.
    to_acknowledge: List[Tuple[str, str, str]] = []
    manifest_dirty = False

    for lang_id, lang_data in sorted(manifest.items()):
        if lang_id.startswith("_"):
            continue
        if lang_filter and lang_id != lang_filter:
            continue

        doc_id = lang_data.get("notes_doc_id")
        if not doc_id:
            # Create-on-first-use: generate the doc now and store in manifest.
            folder_id = lang_data.get("folder_id")
            if not folder_id:
                print(f"[{lang_id}] No folder_id in manifest — skipping")
                continue
            if apply:
                from .drive import _create_notes_doc
                try:
                    doc_id = _create_notes_doc(drive, lang_id, folder_id, get_display_name(lang_id))
                    lang_data["notes_doc_id"] = doc_id
                    manifest[lang_id]["notes_doc_id"] = doc_id
                    config.setdefault(lang_id, {})["notes_doc_id"] = doc_id
                    manifest_dirty = True
                    print(f"[{lang_id}] Created notes doc: https://docs.google.com/document/d/{doc_id}")
                except Exception as e:
                    print(f"[{lang_id}] Could not create notes doc: {e}")
                    continue
            else:
                print(f"[{lang_id}] No notes_doc_id in manifest (would create on --apply)")
                continue

        annotator = lang_data.get("meta", {}).get("annotator") or "Unknown"
        display_name = get_display_name(lang_id)

        try:
            raw_text = _read_notes_doc_text(docs, doc_id)
        except Exception as e:
            print(f"[{lang_id}] Could not read notes doc: {e}")
            continue

        collaborator_text = _strip_acknowledgment_lines(raw_text)
        new_hash = _hash_text(collaborator_text)

        lang_state = state.get(lang_id, {})
        stored_hash = lang_state.get("notes_hash", "")

        state.setdefault(lang_id, {})["last_checked"] = today

        if new_hash == stored_hash:
            print(f"[{lang_id}] No new notes.")
            continue

        # Content has changed.
        stripped = collaborator_text.strip()
        if not stripped:
            # Doc is empty (only whitespace/ack lines) — update hash but don't file.
            state[lang_id]["notes_hash"] = new_hash
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
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write(body)
                body_path = f.name
            try:
                _file_or_update_issue(annotator, body_path)
            finally:
                Path(body_path).unlink(missing_ok=True)
        else:
            print("  [dry run] Would file/update issue with body:")
            print("  " + "\n  ".join(body.splitlines()[:10]) + "\n  ...")

    # Write-back acknowledgments and update state.
    if to_acknowledge:
        ack_text = f"[{today}] {_ACK_PREFIX}. Please consult with them for an update."
        for lang_id, doc_id, new_hash in to_acknowledge:
            if apply:
                try:
                    _append_to_notes_doc(docs, doc_id, ack_text)
                    print(f"[{lang_id}] Acknowledgment appended to notes doc.")
                except Exception as e:
                    print(f"[{lang_id}] Could not append acknowledgment: {e}")
            state[lang_id]["notes_hash"] = new_hash
            state[lang_id]["last_changed"] = today

    # Persist state and manifest if changed.
    if apply:
        _save_notes_state(state)
        print("\nnotes_state.json updated.")
        if manifest_dirty and root_folder_id and existing_config_file_id:
            _upload_planars_config(drive, manifest, root_folder_id, existing_config_file_id)
            _save_drive_config(config)
            print("Drive manifest updated with new notes_doc_id(s).")
    else:
        # Even in dry run, update last_checked so it's accurate when --apply is used.
        pass

    if not annotator_notes:
        print("\nNo new notes to report.")
