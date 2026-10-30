"""One-time migration: class sheets, status sheets and notification issues,
manifest on Drive → the ID file (drive_config.json).

What it does: reads the manifest on Drive and records, for each language, its
class sheets (ID and version), its status sheet and its notification issue in
the ID file (``coding/drive_ids.py``, which does the copying:
``copy_from_manifest``). IDs the ID file already holds are left alone. Reads
Drive only; writes the ID file through the local-file door, which commits
and pushes it in planars-data.

Motivation: Phase 10 unit 11c (``docs/ownership-design.md`` § 6 item 7).
These IDs were kept only in the manifest; from 11c every command reads them
from the ID file, and the manifest becomes a copy rebuilt from it
(``coding/manifest_copy.py``) until 11c-5 deletes it.
Run: 2026-10-28 on Jeff's machine, before the 11c-2 commit that switches the
commands to the ID file. It no longer runs: 11c-5 (2026-10-29) deleted the
manifest, ``load_manifest`` and ``drive_ids.copy_from_manifest``.

Usage:
    python migrations/ids_from_manifest.py           # dry run
    python migrations/ids_from_manifest.py --apply   # write, commit, push

Post-run checks:
    git -C coded_data show --stat HEAD     # drive_config.json changed
    python -m coding integrity-check
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coding import drive_ids, issues  # noqa: E402
from coding.drive import _load_drive_config, _save_drive_config, load_manifest  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402


def main() -> None:
    apply = "--apply" in sys.argv
    config = _load_drive_config()
    before = json.dumps(config, sort_keys=True)
    manifest = load_manifest(get_doorway())
    for lang_id, entry in sorted(manifest.items()):
        if lang_id.startswith("_") or not isinstance(entry, dict):
            continue
        drive_ids.copy_from_manifest(config, lang_id, entry)
        if drive_ids.notification_issue(config, lang_id) is None:
            # The manifest lost arao1248's (#326, made 2026-10-25): find it by title.
            found = issues.find_open("sheet-updates", f"Sheet updates — {lang_id}")
            if found:
                drive_ids.set_notification_issue(config, lang_id, found)
        sheets = drive_ids.class_sheets(config, lang_id)
        print(f"  {lang_id}: {len(sheets)} class sheet(s); status sheet "
              f"{drive_ids.status_sheet_id(config, lang_id) or '(none)'}; "
              f"notification issue {drive_ids.notification_issue(config, lang_id) or '(none)'}")
    if json.dumps(config, sort_keys=True) == before:
        print("The ID file already holds all of these; nothing to do.")
        return
    if not apply:
        print("\nDry run: the ID file is unchanged. Re-run with --apply.")
        return
    _save_drive_config(config)
    print("\nID file written; the local-file door commits and pushes it.")


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration ids_from_manifest", may_write="--apply" in sys.argv):
        main()
