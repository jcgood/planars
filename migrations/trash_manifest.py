"""One-time migration: put the manifest on Drive in the trash.

Motivation: Phase 10 unit 11c-5 (docs/ownership-design.md § 6 item 7, Q7).
The manifest (manifest.json in the root Drive folder) was a list of every
language's sheets kept for the Colab notebooks; it went stale more than once.
Since 11c-2 it was only a copy rebuilt from the ID file, and since 11c-4 the
notebooks find their sheets by label instead (planars.from_sheets): Jeff's
test with a second, non-owner account passed on 2026-10-29. Nothing reads it.

What it does:
  - every live file labelled planars_kind=manifest, and the one
    drive_config.json names (_planars_config_file_id), goes to Drive's trash
    (restorable for 30 days);
  - _planars_config_file_id leaves drive_config.json (written through the
    local-file door, which commits it).
Each step skips what is already done, so a second run finds nothing to do.

Run: 2026-10-29, after the new notebooks were published and before
"manifest" left drive_door.KINDS (the door has to place a file to let it
into the trash).

Usage:
    python migrations/trash_manifest.py           # dry run: reads only
    python migrations/trash_manifest.py --apply

Post-run checks: run the dry run again (it should find nothing); open one
annotator notebook and run it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding import drive_door  # noqa: E402
from coding.drive import _load_drive_config, _save_drive_config  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402

_CONFIG_KEY = "_planars_config_file_id"


def _manifests(doorway, config: Dict) -> Dict[str, str]:
    """{file id: where it was found} for every live manifest."""
    found: Dict[str, str] = {}
    query = ("properties has { key='planars_kind' and value='manifest' } "
             "and trashed=false")
    for f in doorway.list_files(query, fields="files(id, name, properties)"):
        found[f["id"]] = f"{f['name']} (by its label)"
    file_id = config.get(_CONFIG_KEY)
    if file_id and file_id not in found:
        try:
            meta = doorway.get_file(file_id, fields="id,name,trashed")
        except Exception:  # noqa: BLE001 - already gone; only the config entry is left
            meta = {"trashed": True}
        if not meta.get("trashed"):
            found[file_id] = f"{meta.get('name')} (from drive_config.json)"
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    apply = ap.parse_args().apply

    doorway = get_doorway()
    config = _load_drive_config()
    manifests = _manifests(doorway, config)

    print(f"{'DRY RUN — ' if not apply else ''}Putting the manifest in the trash")
    print(f"\n{'Trashing' if apply else 'Would trash'} {len(manifests)} file(s):")
    for file_id, where in manifests.items():
        print(f"  {where}  [{file_id}]")
        if apply:
            doorway.trash_file(file_id)

    has_key = _CONFIG_KEY in config
    print(f"\n{'Removing' if apply else 'Would remove'} {_CONFIG_KEY} from drive_config.json: "
          f"{'yes' if has_key else 'already gone'}")
    if apply and has_key:
        del config[_CONFIG_KEY]
        _save_drive_config(config)

    if not (manifests or has_key):
        print("\nNothing left to do.")
    elif not apply:
        print("\nRun with --apply to make these changes.")


if __name__ == "__main__":
    # Runs outside `python -m coding`, so it tells the Drive door itself.
    with drive_door.running("migration trash_manifest", may_write="--apply" in sys.argv):
        main()
