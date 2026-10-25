"""Which commands still reach Google directly, derived from the code.

The migration's progress was originally tracked by a hand-written list of
eleven files in `docs/data-layer-implementation-plan.md`. On 2026-08-02 a scan
found seventeen. The seven missed included `import_planar` (the command at the
centre of the #248 revert) and `check_notes` (the only user of Google Docs).

That is the project's recurring defect in miniature — a written description
trusted over the thing it describes — so the list is derived here instead.
(A test that kept a hand-written count in docs/data-layer-progress.md in
step with the code was dropped on 2026-10-24, with the count: it made every
new command update a number.)

When the migration is finished, `_REMAINING` is empty, this file's main test
flips from "the list is exactly this" to "the list is empty", and no new
command can quietly open its own connection to Google without failing it.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set

ROOT = Path(__file__).resolve().parent.parent
CODING = ROOT / "coding"

# Reaching Google without going through the doorway.
_DIRECT_ACCESS = re.compile(
    r"_get_clients|_get_docs_client|_open_spreadsheet|gc\.open_by_key"
    r"|drive\.files\(\)|drive\.permissions\(\)|docs\.documents\(\)"
)

# Not commands, and legitimately below the doorway.
_EXEMPT = {
    "drive.py",           # the low-level helpers the doorway itself calls
    "drive_doorway.py",   # the doorway
    "drive_door.py",      # the checks wrapped around it
    "__main__.py",        # dispatch only
    # Read-only recorder that deliberately uses the low-level helpers: it
    # exists to capture raw API responses, so going through an abstraction
    # would defeat its purpose. See coding/capture_drive_state.py.
    "capture_drive_state.py",
}

# Files still to migrate, smallest first. Ordering rationale is in
# docs/data-layer-progress.md § "Migration order".
#
# Empty as of restructure_sheets.py (file 18 of 18) -- Phase 0b/1 is done.
_REMAINING: Set[str] = set()


def _reaches_google_directly() -> Set[str]:
    return {
        path.name for path in sorted(CODING.glob("*.py"))
        if path.name not in _EXEMPT and _DIRECT_ACCESS.search(
            path.read_text(encoding="utf-8"))
    }


def _uses_doorway(name: str) -> bool:
    text = (CODING / name).read_text(encoding="utf-8")
    return "drive_doorway" in text or "get_doorway()" in text


def test_remaining_list_matches_the_code():
    """The tracked list is the real one — no file migrated or added unnoticed."""
    actual = _reaches_google_directly()
    assert actual == _REMAINING, (
        f"Migrated but still listed: {sorted(_REMAINING - actual)}\n"
        f"Reaches Google but not listed: {sorted(actual - _REMAINING)}\n"
        "Update _REMAINING in this file, and the status table in "
        "docs/data-layer-progress.md, in the same commit as the migration."
    )


def test_migrated_files_do_not_reach_google_directly():
    """A migrated command must not keep a private connection alongside the doorway."""
    migrated = [
        path.name for path in sorted(CODING.glob("*.py"))
        if path.name not in _EXEMPT and _uses_doorway(path.name)
    ]
    assert migrated, "no command uses the doorway — something is wrong with detection"
    leftovers = {name for name in migrated if name in _reaches_google_directly()}
    assert not leftovers, (
        f"{sorted(leftovers)} use the doorway but also reach Google directly. "
        "A half-migrated command is worse than an unmigrated one: its writes "
        "are no longer all visible in one place."
    )


_PAST_THE_DOOR = re.compile(r"\._inner\b|\.inner\b")


def test_nothing_reaches_past_the_door():
    """The Drive door checks every write only if no command holds what it wraps
    (docs/drive-door-design.md § 2.2, point 3). A command that took the raw
    gspread object out of a door handle could write anything, unchecked."""
    reaching = sorted(
        path.name for path in CODING.glob("*.py")
        if path.name != "drive_door.py" and _PAST_THE_DOOR.search(
            path.read_text(encoding="utf-8")))
    assert not reaching, (
        f"{reaching} reach inside a Drive door handle (`._inner`/`.inner`). Add "
        "the method the command needs to coding/drive_door.py, with its check.")

