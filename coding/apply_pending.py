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
from typing import Dict, List

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
