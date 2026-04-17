#!/usr/bin/env python3
"""Review and apply pending destructive changes from pending_changes.json.

Run from the repo root:
    python -m coding apply-pending           # prompt for each change
    python -m coding apply-pending --all     # apply all without prompting

Destructive changes (planar deletions/reorders, criterion renames/removals,
construction additions) are written to pending_changes.json by import-sheets
rather than applied immediately. This command lets coordinators review each
change, see the diff summary, and confirm before the downstream command runs.

Once a change is confirmed and applied, its entry is removed from the file.
Skipped entries remain in the file for the next run.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
PENDING_PATH = ROOT / "pending_changes.json"


def _load_pending() -> List[Dict]:
    if not PENDING_PATH.exists():
        return []
    text = PENDING_PATH.read_text(encoding="utf-8").strip()
    if not text or text in ("[]", ""):
        return []
    return json.loads(text)


def _save_pending(entries: List[Dict]) -> None:
    PENDING_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _run_command(cmd: str) -> int:
    """Run a shell command in the repo root, streaming output. Returns exit code."""
    result = subprocess.run(cmd.split(), cwd=str(ROOT))
    return result.returncode


def _verify_construction_tabs(spreadsheet_id: str, constructions: List[str]) -> Optional[Dict[str, bool]]:
    """Check whether each construction tab exists in the Google Sheet.

    Returns a dict mapping construction name → True/False, or None if
    Drive verification was unavailable (auth failure, network error, etc.).
    """
    if not spreadsheet_id:
        return None
    try:
        from .drive import _get_clients, _with_retry
        gc, _ = _get_clients()
        ss = gc.open_by_key(spreadsheet_id)
        existing_titles = {ws.title for ws in _with_retry(ss.worksheets)}
        return {c: c in existing_titles for c in constructions}
    except Exception:
        return None


def _handle_new_construction(entry: Dict, all_flag: bool) -> Tuple[bool, Dict]:
    """Handle a diagnostics_new_construction pending entry.

    Returns (resolved, updated_entry). resolved=True means remove from pending.
    updated_entry may have instructions_shown set to True.
    """
    cls = entry.get("class_name", "?")
    lang_id = entry.get("lang_id", "?")
    constructions = entry.get("new_constructions", [])
    spreadsheet_id = entry.get("spreadsheet_id", "")
    instructions_shown = entry.get("instructions_shown", False)

    if all_flag:
        print("  ⚠  Skipped — new-construction entries cannot be applied automatically.")
        print("     Run `python -m coding apply-pending` interactively to resolve.")
        return False, entry

    if not instructions_shown:
        print()
        print("  ⚠  This change cannot be automated without archiving existing annotations.")
        print("     Confirming will print instructions — no command will run.")
        print("     This entry will remain open until the tab(s) are verified in the Sheet.")
        try:
            confirm = input("  Show instructions? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"

        if confirm != "y":
            print("  Skipped.")
            return False, entry

        print()
        print("  To add this construction, choose one of the following options:")
        print()
        print(f"  Option 1 — Add the tab manually (recommended):")
        print(f"    1. Open the Google Sheet for '{cls}' / '{lang_id}'.")
        print(f"    2. Add tab(s) for: {constructions}")
        print(f"    3. Set each new tab to 'ready-for-review' in the Status tab.")
        print(f"    4. Re-run: python -m coding import-sheets --apply")
        print()
        print(f"  Option 2 — Recreate the sheet from scratch:")
        print(f"    python -m coding generate-sheets --force")
        print(f"    WARNING: --force archives ALL existing annotations for '{cls}'")
        print(f"    and recreates the sheet. Only use this if annotations are expendable.")
        print()
        print("  This entry will remain open. Run `python -m coding apply-pending` again")
        print("  after adding the tab(s) to verify and close it.")

        updated = dict(entry)
        updated["instructions_shown"] = True
        return False, updated

    # instructions already shown — try to verify via Drive
    print()
    print(f"  Checking Google Sheet for tab(s): {constructions} ...")
    result = _verify_construction_tabs(spreadsheet_id, constructions)

    if result is None:
        print("  Could not verify (Drive unavailable or spreadsheet ID not recorded).")
        print("  Please confirm manually: have all the tab(s) been added to the Sheet")
        print(f"  and set to 'ready-for-review'? Constructions: {constructions}")
        try:
            confirm = input("  Mark as resolved? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"
        return confirm == "y", entry

    missing = [c for c, found in result.items() if not found]
    present = [c for c, found in result.items() if found]

    if present:
        print(f"  Found in Sheet:   {present}")
    if missing:
        print(f"  Not found in Sheet: {missing}")
        print("  Action still needed — add the missing tab(s) and re-run apply-pending.")
        return False, entry

    print("  All tab(s) found in Sheet.")
    try:
        confirm = input("  Mark as resolved? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        confirm = "n"
    return confirm == "y", entry


def _close_pending_issue() -> None:
    """Close the open pending-changes GitHub issue, if any. Silently skips if gh unavailable."""
    import subprocess as _sp
    try:
        _sp.run(["gh", "auth", "status"], capture_output=True, check=True)
        result = _sp.run(
            ["gh", "issue", "list", "--label", "pending-changes",
             "--state", "open", "--json", "number", "--jq", ".[0].number"],
            capture_output=True, text=True,
        )
        issue_num = result.stdout.strip()
        if issue_num and issue_num != "null":
            _sp.run(
                ["gh", "issue", "comment", issue_num,
                 "--body", "All pending changes applied — closing."],
                check=True,
            )
            _sp.run(["gh", "issue", "close", issue_num], check=True)
            print(f"GitHub issue #{issue_num} closed.")
    except Exception:
        pass


def main() -> None:
    """Entry point for `python -m coding apply-pending`."""
    all_flag = "--all" in sys.argv

    entries = _load_pending()
    if not entries:
        print("No pending changes.")
        return

    print(f"{len(entries)} pending change(s):\n")

    remaining: List[Dict] = []
    for i, entry in enumerate(entries, 1):
        print(f"[{i}/{len(entries)}]  {entry['lang_id']}  —  {entry['description']}")
        print(f"  Type:    {entry['change_type']}")
        if entry.get("diff_summary"):
            for line in entry["diff_summary"].splitlines():
                print(f"  {line}")

        if entry.get("change_type") == "diagnostics_new_construction":
            resolved, updated = _handle_new_construction(entry, all_flag)
            if not resolved:
                remaining.append(updated)
            else:
                print("  Resolved.")
            print()
            continue

        print(f"  Command: {entry['command']}")

        if all_flag:
            confirm = "y"
        else:
            try:
                confirm = input("  Apply? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                confirm = "n"

        if confirm == "y":
            print(f"  Running: {entry['command']}")
            rc = _run_command(entry["command"])
            if rc == 0:
                print("  Done.")
            else:
                print(f"  Command exited with code {rc} — entry kept in pending.")
                remaining.append(entry)
        else:
            print("  Skipped.")
            remaining.append(entry)
        print()

    _save_pending(remaining)
    applied = len(entries) - len(remaining)
    print(f"Applied {applied} of {len(entries)} change(s). {len(remaining)} still pending.")

    if not remaining:
        _close_pending_issue()


if __name__ == "__main__":
    main()
