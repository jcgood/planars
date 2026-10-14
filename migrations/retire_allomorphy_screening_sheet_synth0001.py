"""One-time migration: retire the standalone allomorphy screening sheet (synth0001).

Motivation: allomorphy is part of the biuniqueness_deviations class since
2026-10-11 (#254), and Adam's answers were copied into its class sheet by
migrate_allomorphy_prescreening_synth0001.py. This moves the old, frozen
biuniqueness_allomorphy_synth0001 spreadsheet into synth0001's Drive
_archived/ folder (kept read-only for Adam, as it was frozen) and removes the
manifest keys that pointed at it (biuniqueness_allomorphy_spreadsheet_id,
biuniqueness_allomorphy_url), which nothing reads once the
generate-biuniqueness-allomorphy-sheet command is gone.

Run: 2026-10-11, after the answer migration, alongside the commit that
     deletes coding/generate_biuniqueness_allomorphy_sheet.py.

Usage:
    python migrations/retire_allomorphy_screening_sheet_synth0001.py           # dry run
    python migrations/retire_allomorphy_screening_sheet_synth0001.py --apply

Post-run checks:
    The sheet is in synth0001's _archived/ folder; the manifest's synth0001
    entry has no biuniqueness_allomorphy_* keys; the class sheet is untouched.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding.drive import (  # noqa: E402
    _load_drive_config, _save_drive_config, load_manifest, upload_manifest,
)
from coding.drive_doorway import get_doorway  # noqa: E402

LANG = "synth0001"
OLD_SHEET_ID = "1YEtSlw9t05OI6RKGgCtbez0u3oX1p5Xfe_6UH1dweGA"
KEYS = ("biuniqueness_allomorphy_spreadsheet_id", "biuniqueness_allomorphy_url")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    apply = ap.parse_args().apply

    doorway = get_doorway()
    manifest = load_manifest(doorway)
    entry = manifest[LANG]
    folder_id = entry["folder_id"]
    present = [k for k in KEYS if k in entry]
    parents = doorway.get_file(OLD_SHEET_ID, fields="id,name,parents").get("parents", [])

    print(f"{'DRY RUN — ' if not apply else ''}retire {OLD_SHEET_ID}")
    print(f"  move to {LANG}/_archived/ (now in parents {parents})")
    print(f"  remove manifest keys: {present or 'none present'}")
    if not apply:
        print("\nRun with --apply to write.")
        return

    from coding import drive_door
    archive_id = doorway.get_or_create_folder("_archived", parent_id=folder_id,
                                              identity=drive_door.folder("archive", LANG))
    if archive_id not in parents:
        doorway.move_file(OLD_SHEET_ID, archive_id)
    if present:
        for k in present:
            entry.pop(k)
        config = _load_drive_config()
        file_id = upload_manifest(doorway, manifest, config.get("_root_folder_id"),
                                  config.get("_planars_config_file_id"))
        config["_planars_config_file_id"] = file_id
        _save_drive_config(config)
    print("\nDone.")


if __name__ == "__main__":
    import sys

    from coding import drive_door
    # Runs outside `python -m coding`, so it tells the Drive door itself.
    with drive_door.running("migration retire_allomorphy_screening_sheet_synth0001",
                            may_write="--apply" in sys.argv):
        main()
