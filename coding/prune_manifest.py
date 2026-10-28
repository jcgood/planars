#!/usr/bin/env python3
"""Remove retired analysis class entries from the Drive manifest and archive their TSVs.

When an analysis class is removed from diagnostics_{lang_id}.yaml (and the TSV regenerated
via `sync-diagnostics-yaml --apply`), the Drive manifest retains the stale entry
indefinitely. This causes import-sheets to keep downloading the old sheet and writing
TSVs to the retired class directory.

Run from the repo root:
    python -m coding prune-manifest           # dry run — show what would change
    python -m coding prune-manifest --apply   # archive TSVs, move Drive sheet, remove manifest entry
    python -m coding prune-manifest --apply --all  # skip per-class confirmation prompts

For each stale class (in manifest but not in diagnostics_{lang_id}.yaml, or its TSV if
there is no YAML), --apply will:
  1. Write a timestamped manifest snapshot to manifest_archives/ (gitignored)
  2. Remove each *.tsv in coded_data/{lang}/{class}/ through the local-file door
     (coding/file_door.py), which keeps its last version in
     coded_data/{lang}/archive/{class}/, logs it in the language's changes.tsv,
     removes the emptied class folder, and commits and pushes the change in
     planars-data when the command ends
  3. Move the Drive spreadsheet into an _archived/ subfolder in the language's Drive folder,
     and make it read-only for everyone but its owner (drive.make_read_only)
  4. Remove the class entry from the Drive manifest and re-upload it

Without --all it asks about each class. The Drive manifest is uploaded right
after each class is archived, not once at the end, so a crash partway through
never leaves it listing an already-archived class. A stale class here means a
retired one; to rename a class instead, use `restructure-sheets --rename-class`.

The Drive sheet is moved to _archived/, not deleted — annotation data is irreplaceable.
A recency warning is shown if the sheet was modified within the last 14 days, in case
there is unapplied annotation work.

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml as _yaml

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
MANIFEST_ARCHIVES = ROOT / "manifest_archives"

from .drive import (
    load_manifest,
    make_read_only,
    upload_manifest,
    _load_drive_config,
    _save_drive_config,
)
from .drive_doorway import get_doorway
from . import drive_door
from .sheet_spec import ARCHIVE_FOLDER_NAME
from . import file_door


_RECENCY_DAYS = 14  # warn if sheet was modified within this many days

# One Drive read per sheet per run. The dry-run summary and the apply pass both
# want the sheet's name and last-edit time, and asking twice for a fact that
# cannot change mid-run is just latency. Cleared at the top of main().
_SHEET_META: Dict[str, Optional[Dict]] = {}


# ---------------------------------------------------------------------------
# Drive sheet archival
# ---------------------------------------------------------------------------

def _sheet_metadata(doorway, spreadsheet_id: str, class_name: str) -> Optional[Dict]:
    """Name and last-edit time for a sheet, or None if Drive would not say.

    Read during the *dry run* as well as the apply pass, deliberately: the
    "edited N days ago" warning below is the only thing standing between a
    coordinator and archiving a sheet somebody is still annotating, and until
    2026-08-02 it was read in apply mode only — which meant it printed after
    the "Prune 'X'? [y/N]" it should have informed. See issue #277.
    """
    if spreadsheet_id in _SHEET_META:
        return _SHEET_META[spreadsheet_id]
    try:
        meta = doorway.get_file(
            spreadsheet_id,
            fields="name,modifiedTime",
            supports_all_drives=True,
        )
    except Exception as exc:
        print(f"    WARNING: could not read sheet metadata for {class_name}: {exc}")
        meta = None
    _SHEET_META[spreadsheet_id] = meta
    return meta


def _warn_if_recently_edited(meta: Dict, spreadsheet_id: str) -> None:
    modified_str = meta.get("modifiedTime", "")
    if not modified_str:
        return
    modified_dt = datetime.fromisoformat(modified_str.replace("Z", "+00:00"))
    age_days = (datetime.now(timezone.utc) - modified_dt).days
    if age_days < _RECENCY_DAYS:
        print(
            f"    WARNING: '{meta.get('name', spreadsheet_id)}' was edited "
            f"{age_days} day(s) ago — check for unapplied annotation work "
            f"before proceeding."
        )


def _archive_drive_sheet(
    doorway, lang_id: str, class_name: str, manifest: dict, apply: bool
) -> bool:
    """Move the Drive spreadsheet for a retired class into _archived/ in the language folder.

    In dry-run mode prints what would happen; in apply mode performs the move.
    Returns True if the sheet was (or would be) archived.
    """
    lang_data = manifest.get(lang_id, {})
    sheet_info = lang_data.get("sheets", {}).get(class_name, {})
    spreadsheet_id = sheet_info.get("spreadsheet_id")
    folder_id = lang_data.get("folder_id")

    if not spreadsheet_id:
        print(f"    no spreadsheet_id in manifest for {class_name} — skipping Drive archival")
        return False
    if not folder_id:
        print(f"    no folder_id in manifest for {lang_id} — skipping Drive archival")
        return False

    meta = _sheet_metadata(doorway, spreadsheet_id, class_name)

    if not apply:
        ss_url = sheet_info.get("spreadsheet_url", spreadsheet_id)
        print(f"    would move Drive sheet → _archived/  ({ss_url})")
        if meta:
            _warn_if_recently_edited(meta, spreadsheet_id)
        return True

    if meta is None:
        print(f"    Skipping Drive archival — remove the sheet manually if needed.")
        return False

    sheet_name = meta.get("name", spreadsheet_id)
    _warn_if_recently_edited(meta, spreadsheet_id)

    try:
        archived_folder_id = doorway.get_or_create_folder(
            ARCHIVE_FOLDER_NAME, folder_id, identity=drive_door.folder("archive", lang_id))
        doorway.move_file(spreadsheet_id, archived_folder_id)
        print(f"    archived Drive sheet: '{sheet_name}' → _archived/")
        # Labelled archived before the annotator is lowered to reader, which
        # is the role the door expects on an archived sheet.
        doorway.mark_archived(spreadsheet_id)
        lowered = make_read_only(doorway, spreadsheet_id)
        if lowered:
            print(f"    made read-only for: {', '.join(lowered)}")
        return True
    except Exception as exc:
        print(f"    WARNING: could not move Drive sheet for {class_name}: {exc}")
        print(f"    Remove the sheet manually from Drive if needed.")
        return False


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _active_classes(lang_id: str) -> set[str]:
    """Return the set of class names currently active for lang_id.

    Reads diagnostics_{lang_id}.yaml. A language with no YAML stops the
    command: without one every class would look stale and its sheets would
    be archived (until 2026-10-27 that is what happened when neither the YAML
    nor its TSV copy was there).
    """
    yaml_path = CODED_DATA / lang_id / "lang_setup" / f"diagnostics_{lang_id}.yaml"
    if not yaml_path.exists():
        raise SystemExit(
            f"ERROR: {lang_id} has sheets in the manifest but no {yaml_path.name} in "
            f"coded_data/{lang_id}/lang_setup/, so prune-manifest can't tell which "
            f"classes are active. Pull planars-data (git -C coded_data pull) or restore "
            f"the file from its history, then re-run.")
    with open(yaml_path, encoding="utf-8") as f:
        data = _yaml.safe_load(f)
    return set(((data or {}).get("classes") or {}).keys())


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

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding prune-manifest`."""
    ap = argparse.ArgumentParser(
        description="Archive retired class TSVs and remove stale manifest entries."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="archive TSVs, move Drive sheet, remove manifest entry (default: dry run)",
    )
    ap.add_argument(
        "--all", action="store_true", dest="skip_prompts",
        help="skip per-class confirmation prompts",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for `python -m coding prune-manifest`."""
    if args is None:
        args = build_parser().parse_args()
    apply = args.apply
    skip_prompts = args.skip_prompts

    # coded_data_clean_tree is enforced centrally at the python -m coding
    # dispatch chokepoint now -- see coding/preconditions.py -- not here. It
    # still guards against exactly what it always has: coded_data/ (which
    # this command archives TSVs out of) left stale/partially-reverted by a
    # prior step's failed auto-commit.
    _SHEET_META.clear()
    doorway = get_doorway()
    manifest = load_manifest(doorway)

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
            tsvs = file_door.annotation_files(lang_id, class_name)
            if tsvs:
                for tsv in tsvs:
                    print(f"    would archive: {tsv.path.relative_to(ROOT)}")
                print(
                    f"    WARNING: {class_name}/ contains annotation data.\n"
                    f"    If this class was renamed rather than retired, use:\n"
                    f"      python -m coding restructure-sheets --rename-class {class_name}:NEW_NAME --apply\n"
                    f"    instead of pruning it (--rename-class preserves annotations under the new name)."
                )
            else:
                print(f"    no local TSVs for {class_name}/")
            _archive_drive_sheet(doorway, lang_id, class_name, manifest, apply=False)
            print(f"    would remove from manifest: {lang_id}/{class_name}")
        print()

    if not apply:
        print("Run with --apply to make these changes.")
        return

    timestamp = file_door.stamp()

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

            # Remove the class's TSVs through the local-file door, which keeps
            # each one's last version in archive/{class}/, logs it, removes the
            # emptied class folder, and commits when the command ends.
            tsvs = file_door.annotation_files(lang_id, class_name)
            for tsv in tsvs:
                file_door.remove(tsv, why=f"class {class_name} retired (prune-manifest)")
                print(f"    archived: {tsv.name} → archive/{class_name}/")

            if not tsvs:
                print(f"    no local TSVs to archive for {class_name}/")

            # Move Drive sheet to _archived/ subfolder
            _archive_drive_sheet(doorway, lang_id, class_name, manifest, apply=True)

            # Remove from manifest
            del manifest[lang_id]["sheets"][class_name]
            print(f"    removed from manifest: {lang_id}/{class_name}")
            any_changes = True

            # Upload the manifest right after this class's local/Drive
            # archiving is done, not once after the whole loop -- a crash
            # partway through must not leave Drive's manifest still showing
            # an already-archived class as present, which would make a retry
            # reprocess it (issue #280).
            drive_cfg = _load_drive_config()
            file_id = drive_cfg.get("_planars_config_file_id")
            root_id = drive_cfg.get("_root_folder_id")
            new_id = upload_manifest(doorway, manifest, root_id, file_id)
            if new_id != file_id:
                drive_cfg["_planars_config_file_id"] = new_id
                _save_drive_config(drive_cfg)

        print()

    if any_changes:
        print("Drive manifest updated.")
    else:
        print("No changes made (all classes skipped).")
