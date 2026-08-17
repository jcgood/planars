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

import argparse
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

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


# How a look at the Google Sheet turned out. Only CHECKED carries an answer
# about the tabs; the other four are reasons no check happened, and each one
# needs a different thing from the coordinator.
CHECKED = "checked"
NO_ID_RECORDED = "no_id_recorded"
SHEET_NOT_FOUND = "sheet_not_found"
NO_ACCESS = "no_access"
DRIVE_UNREACHABLE = "drive_unreachable"


def _verify_construction_tabs(spreadsheet_id: str,
                              constructions: List[str]) -> Tuple[str, Dict[str, bool]]:
    """Check whether each construction tab exists in the Google Sheet.

    Returns (outcome, tabs). ``tabs`` maps construction name → present, and
    says anything only when the outcome is CHECKED.

    The four ways of not getting an answer used to be one: any failure at all
    meant "could not verify", so a spreadsheet ID pointing at a sheet that no
    longer exists read exactly like a dropped connection. Both then asked the
    coordinator to confirm from memory, and a "yes" closed the entry with
    nothing checked — see docs/data-layer-progress.md, finding 3.
    """
    if not spreadsheet_id:
        return NO_ID_RECORDED, {}

    # Imported here, not at the top of the file, so that a run with nothing
    # to verify — the common case — never signs in to Google at all.
    from .drive import _with_retry
    from .drive_doorway import APIError, NoAccess, SpreadsheetNotFound, get_doorway

    try:
        # open_spreadsheet retries by itself; opening used not to. Reading tab
        # names is idempotent, so the extra attempts can only help.
        ss = get_doorway().open_spreadsheet(spreadsheet_id)
        existing_titles = {ws.title for ws in _with_retry(ss.worksheets)}
    except SpreadsheetNotFound:
        return SHEET_NOT_FOUND, {}
    except NoAccess:
        return NO_ACCESS, {}
    except APIError as e:
        # Reading the tab names is a second call, and it reports a vanished or
        # unshared sheet as a plain status code rather than by exception type.
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code == 404:
            return SHEET_NOT_FOUND, {}
        if code == 403:
            return NO_ACCESS, {}
        return DRIVE_UNREACHABLE, {}
    except Exception:
        return DRIVE_UNREACHABLE, {}

    return CHECKED, {c: c in existing_titles for c in constructions}


def _unchecked_report(outcome: str, entry: Dict) -> Tuple[List[str], str]:
    """What to tell the coordinator when the Sheet could not be checked.

    Returns (lines to print, the question to ask). The question differs on
    purpose: "have the tabs been added" is answerable when Drive merely could
    not be reached, and is not answerable at all when the sheet the entry names
    no longer exists.
    """
    cls = entry.get("class_name", "?")
    lang_id = entry.get("lang_id", "?")
    constructions = entry.get("new_constructions", [])
    sheet_name = f"{cls}_{lang_id}"

    if outcome == NO_ID_RECORDED:
        return ([
            "  This entry never recorded which spreadsheet to look in, so the",
            "  tab(s) cannot be checked for you.",
            f"  The Sheet for this class is named '{sheet_name}', in the",
            f"  '{lang_id}' folder on Drive.",
            f"  Have tab(s) {constructions} been added there and set to",
            "  'ready-for-review'?",
        ], "Mark as resolved?")

    if outcome == SHEET_NOT_FOUND:
        return ([
            "  Drive has no spreadsheet with the ID recorded on this entry",
            f"  ({entry.get('spreadsheet_id', '')}).",
            "  It was deleted, or replaced by a newer sheet — so the entry is",
            "  pointing at the wrong place, and adding a tab cannot fix that.",
            "  → Run: python -m coding integrity-check --sheets",
            "    It lists which spreadsheet IDs are unreachable and what to do",
            "    next. Close this entry only if the work it describes is done.",
        ], "Close this entry anyway?")

    if outcome == NO_ACCESS:
        return ([
            "  Drive refused access to that spreadsheet — the Google account",
            "  this command signed in as is not shared on it.",
            f"  The Sheet is named '{sheet_name}'. Ask whoever owns it to share",
            "  it, then run: python -m coding apply-pending",
        ], "Close this entry anyway?")

    return ([
        "  Could not reach Drive to check (no network, or sign-in failed).",
        "  Nothing is wrong with the entry itself — running",
        "  python -m coding apply-pending again later will check properly.",
    ], "Mark as resolved without checking?")


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
        print(f"    python -m coding generate-sheets --force --apply")
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
    outcome, result = _verify_construction_tabs(spreadsheet_id, constructions)

    if outcome != CHECKED:
        lines, question = _unchecked_report(outcome, entry)
        for line in lines:
            print(line)
        try:
            confirm = input(f"  {question} [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"
        return confirm == "y", entry

    missing = [c for c, found in result.items() if not found]
    present = [c for c, found in result.items() if found]

    if present:
        print(f"  Found in Sheet:   {present}")
    if missing:
        print(f"  Not found in Sheet: {missing}")
        print("  Action still needed — add the missing tab(s), then run:")
        print("    python -m coding apply-pending")
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


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding apply-pending`."""
    ap = argparse.ArgumentParser(
        description="Review and apply pending destructive changes."
    )
    ap.add_argument(
        "--all", action="store_true", dest="all_flag",
        help="apply all pending changes without prompting",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding apply-pending`."""
    if args is None:
        args = build_parser().parse_args()
    all_flag = args.all_flag

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
            # Persist after every entry, not once at the end of the loop -- a
            # crash after this entry's command has already run for real must
            # not leave pending_changes.json still listing it, or a retry
            # re-runs it a second time (issue #280).
            _save_pending(remaining + entries[i:])
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
        # Same incremental-save reasoning as above.
        _save_pending(remaining + entries[i:])
        print()

    applied = len(entries) - len(remaining)
    print(f"Applied {applied} of {len(entries)} change(s). {len(remaining)} still pending.")

    if not remaining:
        _close_pending_issue()


if __name__ == "__main__":
    main()
