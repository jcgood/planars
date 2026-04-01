#!/usr/bin/env python3
"""Remove retired analysis class entries from the Drive manifest and archive their TSVs.

When an analysis class is removed from diagnostics_{lang_id}.yaml (and the TSV regenerated
via `sync-diagnostics-yaml --apply`), the Drive manifest retains the stale entry
indefinitely. This causes import-sheets to keep downloading the old sheet and writing
TSVs to the retired class directory.

Run from the repo root:
    python -m coding prune-manifest           # dry run — show what would change
    python -m coding prune-manifest --apply   # archive TSVs and remove manifest entries
    python -m coding prune-manifest --apply --all  # skip per-class confirmation prompts

For each stale class (in manifest but not in diagnostics.tsv), --apply will:
  1. Write a timestamped manifest snapshot to manifest_archives/ (gitignored)
  2. Archive each active *.tsv in coded_data/{lang}/{class}/ to its archive/ subdirectory
  3. Remove the now-archived active TSV files
  4. Remove the class entry from the Drive manifest and re-upload it

The retired Google Sheets on Drive are NOT deleted — they remain as a record.
Only the manifest entry and local TSVs are cleaned up.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
MANIFEST_ARCHIVES = ROOT / "manifest_archives"

from . import make_forms as _mf
from .make_forms import _read_diagnostics_for_language
from .drive import (
    _get_clients,
    _load_manifest_from_drive,
    _upload_planars_config,
    _load_drive_config,
    _save_drive_config,
)
from .import_sheets import _archive_tsv


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _active_classes(lang_id: str) -> set[str]:
    """Return the set of class names currently active in diagnostics_{lang_id}.tsv."""
    planar_input = CODED_DATA / lang_id / "planar_input"
    if not planar_input.exists():
        return set()
    _mf.DATA_DIR = str(planar_input)
    try:
        rows = _read_diagnostics_for_language(lang_id)
    except Exception:
        return set()
    return {class_name for class_name, _, _, _ in rows}


def _find_stale(manifest: dict) -> Dict[str, List[str]]:
    """Return {lang_id: [stale_class_name, ...]} for all languages in the manifest."""
    result: Dict[str, List[str]] = {}
    for lang_id, lang_data in manifest.items():
        manifest_classes = set(lang_data.get("sheets", {}).keys())
        active = _active_classes(lang_id)
        stale = sorted(manifest_classes - active)
        if stale:
            result[lang_id] = stale
    return result


def _tsv_paths(lang_id: str, class_name: str) -> List[Path]:
    """Return all active *.tsv files in coded_data/{lang_id}/{class_name}/."""
    class_dir = CODED_DATA / lang_id / class_name
    if not class_dir.exists():
        return []
    return sorted(class_dir.glob("*.tsv"))


# ---------------------------------------------------------------------------
# Manifest archiving
# ---------------------------------------------------------------------------

def _archive_manifest(manifest: dict, timestamp: str) -> Path:
    """Write a timestamped snapshot of the manifest to manifest_archives/."""
    MANIFEST_ARCHIVES.mkdir(exist_ok=True)
    dest = MANIFEST_ARCHIVES / f"manifest_{timestamp}.json"
    dest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return dest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for `python -m coding prune-manifest`."""
    apply = "--apply" in sys.argv
    skip_prompts = "--all" in sys.argv

    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)

    stale_map = _find_stale(manifest)

    if not stale_map:
        print("All manifest entries match active diagnostics — nothing to prune.")
        return

    # Always show dry-run summary; warn if annotation data exists (possible rename)
    print(f"{'DRY RUN — ' if not apply else ''}Stale manifest entries found:\n")
    for lang_id, stale_classes in stale_map.items():
        print(f"  {lang_id}:")
        print(f"    stale classes: {', '.join(stale_classes)}")
        for class_name in stale_classes:
            tsvs = _tsv_paths(lang_id, class_name)
            if tsvs:
                for tsv in tsvs:
                    print(f"    would archive: {tsv.relative_to(ROOT)}")
                print(
                    f"    WARNING: {class_name}/ contains annotation data.\n"
                    f"    If this class was renamed rather than retired, use:\n"
                    f"      python -m coding restructure-sheets --rename-class {class_name}:NEW_NAME --apply\n"
                    f"    instead of pruning it (--rename-class preserves annotations under the new name)."
                )
            else:
                print(f"    no local TSVs for {class_name}/")
            print(f"    would remove from manifest: {lang_id}/{class_name}")
        print()

    if not apply:
        print("Run with --apply to make these changes.")
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Archive manifest before any mutation
    snapshot_path = _archive_manifest(manifest, timestamp)
    print(f"Manifest snapshot written to {snapshot_path.relative_to(ROOT)}\n")

    any_changes = False

    for lang_id, stale_classes in stale_map.items():
        print(f"  {lang_id}:")
        for class_name in stale_classes:
            # Per-class confirmation unless --all
            if not skip_prompts:
                resp = input(f"    Prune '{class_name}' from {lang_id}? [y/N] ").strip().lower()
                if resp != "y":
                    print(f"    Skipped {class_name}.")
                    continue

            # Archive and remove active TSVs
            tsvs = _tsv_paths(lang_id, class_name)
            for tsv in tsvs:
                archived = _archive_tsv(tsv, timestamp)
                tsv.unlink()
                print(f"    archived: {tsv.name} → {archived.relative_to(CODED_DATA / lang_id / class_name)}")

            if not tsvs:
                print(f"    no local TSVs to archive for {class_name}/")

            # Remove from manifest
            del manifest[lang_id]["sheets"][class_name]
            print(f"    removed from manifest: {lang_id}/{class_name}")
            any_changes = True

        print()

    if any_changes:
        drive_cfg = _load_drive_config()
        file_id = drive_cfg.get("_planars_config_file_id")
        root_id = drive_cfg.get("_root_folder_id")
        new_id = _upload_planars_config(drive, manifest, root_id, file_id)
        if new_id != file_id:
            drive_cfg["_planars_config_file_id"] = new_id
            _save_drive_config(drive_cfg)
        print("Drive manifest updated.")
    else:
        print("No changes made (all classes skipped).")
