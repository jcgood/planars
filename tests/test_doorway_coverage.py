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
    "prune_manifest.py",
    "check_notes.py",
    "generate_biuniqueness_stage1_sheet.py",
    "sync_diagnostics_yaml.py",
    "import_planar.py",
    "generate_notebooks.py",
    "update_sheets.py",
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
