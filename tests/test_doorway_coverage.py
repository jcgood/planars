"""Which commands still reach Google directly, derived from the code.

The migration's progress was originally tracked by a hand-written list of
eleven files in `docs/data-layer-implementation-plan.md`. On 2026-08-02 a scan
found seventeen. The seven missed included `import_planar` (the command at the
centre of the #248 revert) and `check_notes` (the only user of Google Docs).

That is the project's recurring defect in miniature — a written description
trusted over the thing it describes — so the list is derived here instead. The
count of files left to migrate is now answered by running this test.

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
    "__main__.py",        # dispatch only
    # Read-only recorder that deliberately uses the low-level helpers: it
    # exists to capture raw API responses, so going through an abstraction
    # would defeat its purpose. See coding/capture_drive_state.py.
    "capture_drive_state.py",
}

# Files still to migrate, smallest first. Ordering rationale is in
# docs/data-layer-progress.md § "Migration order".
_REMAINING = {
    "generate_status_sheet.py",
    "validate_coding.py",
    "sync_params.py",
    "integrity_check.py",
    "import_sheets.py",
    "restructure_sheets.py",
    "generate_sheets.py",
}


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


def test_progress_is_recorded_where_it_is_claimed():
    """coding/CLAUDE.md names the migrated files; keep it true, not approximate."""
    claimed = (CODING / "CLAUDE.md").read_text(encoding="utf-8")
    match = re.search(r"\*\*Migrated so far: (.+?)\.\*\*", claimed)
    assert match, "coding/CLAUDE.md no longer states which files are migrated"
    named = set(re.findall(r"`([a-z_]+\.py)`", match.group(1)))
    actual = {
        path.name for path in sorted(CODING.glob("*.py"))
        if path.name not in _EXEMPT and _uses_doorway(path.name)
    }
    assert named == actual, (
        f"coding/CLAUDE.md says {sorted(named)}; the code says {sorted(actual)}"
    )


def test_stated_counts_match_the_code():
    """The progress doc says how many files are done; keep it arithmetic, not memory.

    The list of remaining files has been derived since 2026-08-02, but the
    *count* was still hand-copied into docs/data-layer-progress.md — and it went
    stale within two days, reading "of 17" when the real total was 18. Same
    defect as the list it replaced, one level up.
    """
    doc = (ROOT / "docs" / "data-layer-progress.md").read_text(encoding="utf-8")
    match = re.search(r"migrating callers, (\d+) of (\d+) done", doc)
    assert match, "docs/data-layer-progress.md no longer states the migration count"
    said_done, said_total = int(match.group(1)), int(match.group(2))

    migrated = {
        path.name for path in sorted(CODING.glob("*.py"))
        if path.name not in _EXEMPT and _uses_doorway(path.name)
    }
    remaining = _reaches_google_directly()
    assert (said_done, said_total) == (len(migrated), len(migrated) + len(remaining)), (
        f"the doc says {said_done} of {said_total}; the code says "
        f"{len(migrated)} of {len(migrated) + len(remaining)}"
    )
