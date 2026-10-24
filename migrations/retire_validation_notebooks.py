"""One-time migration: retire the validation notebooks and the manifest's copy of each criterion's values.

Motivation (Jeff, 2026-10-23): each language had a Colab notebook,
`validation_{lang_id}.ipynb`, that marked bad cells pink. It checked cells
against a copy of each criterion's allowed values kept in the manifest
(`construction_params[construction].param_values`), not against the
diagnostics file, and checked every tab as if it had one row per element.
That copy went stale on its own (synth0001's coreference prescreening entry
carried the three pair criteria's values from 2026-10-10 until the daily
refresh-dropdowns cleared it on 2026-10-23), and integrity-check's warning
about it was read as old noise. The daily refresh already lists every cell
that needs fixing on each sheet's Status tab (#309), with validate-coding's
real rules. Nothing else read the copy once the notebook was gone, so both
go: the notebooks to Drive's trash (restorable for 30 days), the copy out of
the manifest, and the notebooks' ids out of drive_config.json. The code
stopped making either in the same change.

What it does:
  - every validation notebook, found by its label (planars_kind=notebook,
    planars_name=validation) and by drive_config.json's
    validation_notebook_file_id, goes to Drive's trash;
  - each language's validation_notebook_file_id leaves drive_config.json
    (written through the local-file door, which commits it);
  - every construction's param_values leaves the manifest, which is uploaded
    once if anything changed (param_names stays: the analysis notebooks read
    it).
Each step skips what is already done, so a second run finds nothing to do.

Run: 2026-10-23, before "validation" left drive_door.KINDS (the door has to
place a notebook to let it into the trash). Trashed the three notebooks
(arao1248, stan1293, synth0001), removed their three drive_config.json
entries and 50 constructions' param_values; a second dry run found nothing.
A re-run's dry run still works; its --apply could no longer trash a
validation notebook, since the door no longer knows the kind.

Usage:
    python migrations/retire_validation_notebooks.py           # dry run: reads only
    python migrations/retire_validation_notebooks.py --apply

Post-run checks: run the dry run again (it should find nothing); then
python -m coding integrity-check, and refreeze the test data
(python -m coding capture-drive-state --apply).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding import drive_door  # noqa: E402
from coding.drive import (_load_drive_config, _save_drive_config, load_manifest,  # noqa: E402
                          upload_manifest)
from coding.drive_doorway import get_doorway  # noqa: E402

_CONFIG_KEY = "validation_notebook_file_id"


def _notebooks(doorway, config: Dict) -> Dict[str, str]:
    """{file id: where it was found} for every live validation notebook."""
    found: Dict[str, str] = {}
    # Spelled out: "validation" has left drive_door.KINDS, so no Identity
    # can be made for it any more.
    labels = {"planars_kind": "notebook", "planars_name": "validation"}
    query = " and ".join(
        [f"properties has {{ key='{k}' and value='{v}' }}" for k, v in labels.items()]
        + ["trashed=false"])
    for f in doorway.list_files(query, fields="files(id, name, properties)"):
        lang = (f.get("properties") or {}).get("planars_lang", "?")
        found[f["id"]] = f"{f['name']} ({lang}, by its label)"
    for lang, entry in sorted(config.items()):
        if lang.startswith("_") or not isinstance(entry, dict) or not entry.get(_CONFIG_KEY):
            continue
        file_id = entry[_CONFIG_KEY]
        if file_id in found:
            continue
        try:
            meta = doorway.get_file(file_id, fields="id,name,trashed")
        except Exception:  # noqa: BLE001 - already gone; only the config entry is left
            continue
        if not meta.get("trashed"):
            found[file_id] = f"{meta.get('name')} ({lang}, from drive_config.json)"
    return found


def _strip_values(manifest: Dict) -> List[Tuple[str, str, str]]:
    """Remove every construction's param_values; return what was removed."""
    removed = []
    for lang, entry in sorted(manifest.items()):
        if lang.startswith("_") or not isinstance(entry, dict):
            continue
        for class_name, info in sorted((entry.get("sheets") or {}).items()):
            for construction, cp in (info.get("construction_params") or {}).items():
                if isinstance(cp, dict) and "param_values" in cp:
                    del cp["param_values"]
                    removed.append((lang, class_name, construction))
    return removed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    apply = ap.parse_args().apply

    doorway = get_doorway()
    config = _load_drive_config()
    manifest = load_manifest(doorway)

    notebooks = _notebooks(doorway, config)
    stale_keys = sorted(lang for lang, entry in config.items()
                        if not lang.startswith("_") and isinstance(entry, dict)
                        and _CONFIG_KEY in entry)
    removed = _strip_values(manifest)

    verb = "Trashing" if apply else "Would trash"
    print(f"{'DRY RUN — ' if not apply else ''}Retiring the validation notebooks")
    print(f"\n{verb} {len(notebooks)} notebook(s):")
    for file_id, where in notebooks.items():
        print(f"  {where}  [{file_id}]")
        if apply:
            doorway.trash_file(file_id)

    print(f"\n{'Removing' if apply else 'Would remove'} {_CONFIG_KEY} from drive_config.json "
          f"for {len(stale_keys)} language(s): {', '.join(stale_keys) or '-'}")
    if apply and stale_keys:
        for lang in stale_keys:
            del config[lang][_CONFIG_KEY]
        _save_drive_config(config)

    print(f"\n{'Removing' if apply else 'Would remove'} param_values from "
          f"{len(removed)} construction(s) in the manifest")
    if apply and removed:
        file_id = upload_manifest(doorway, manifest, config.get("_root_folder_id"),
                                  config.get("_planars_config_file_id"))
        if config.get("_planars_config_file_id") != file_id:
            config["_planars_config_file_id"] = file_id
            _save_drive_config(config)
        print("Manifest updated on Drive.")

    if not (notebooks or stale_keys or removed):
        print("\nNothing left to do.")
    elif not apply:
        print("\nRun with --apply to make these changes.")


if __name__ == "__main__":
    # Runs outside `python -m coding`, so it tells the Drive door itself.
    with drive_door.running("migration retire_validation_notebooks",
                            may_write="--apply" in sys.argv):
        main()
