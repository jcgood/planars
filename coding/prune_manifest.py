#!/usr/bin/env python3
"""Retire analysis classes: remove them from the ID file and archive their TSVs and sheets.

(The command keeps its old name, prune-manifest; what it prunes is the ID file's
list of class sheets. The manifest it once pruned was deleted in unit 11c-5.)

When an analysis class is removed from diagnostics_{lang_id}.yaml (and the TSV regenerated
via `sync-diagnostics-yaml --apply`), the ID file (drive_config.json) retains the stale
class sheet indefinitely. This causes import-sheets to keep downloading the old sheet and
writing TSVs to the retired class directory.

Run from the repo root:
    python -m coding prune-manifest           # dry run — show what would change
    python -m coding prune-manifest --apply   # archive TSVs, move Drive sheet, remove it from the ID file
    python -m coding prune-manifest --apply --all  # skip per-class confirmation prompts

For each stale class (a class sheet in the ID file but not in diagnostics_{lang_id}.yaml),
--apply will:
  1. Remove each *.tsv in coded_data/{lang}/{class}/ through the local-file door
     (coding/file_door.py), which keeps its last version in
     coded_data/{lang}/archive/{class}/, logs it in the language's changes.tsv,
     removes the emptied class folder, and commits and pushes the change in
     planars-data when the command ends
  2. Move the Drive spreadsheet into an _archived/ subfolder in the language's Drive folder,
     and make it read-only for everyone but its owner (drive.make_read_only)
  3. Remove the class sheet from the ID file (`drive_ids.remove_class_sheet`)
     and save it, through the local-file door, which commits it in
     planars-data (its history there is the record of what was removed)

Without --all it asks about each class. The ID file is saved right after each
class is archived, not once at the end, so a crash partway through never
leaves it listing an already-archived class. The Colab notebooks leave an
archived sheet out by its label (`planars.from_sheets`), so nothing else
needs telling. A stale class here means a retired one; to rename
a class instead, use `restructure-sheets --rename-class`.

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

from .drive import (
    make_read_only,
    _load_drive_config,
    _save_drive_config,
)
from .drive_doorway import get_doorway
from . import drive_door, drive_ids
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
    doorway, lang_id: str, class_name: str, config: dict, apply: bool
) -> bool:
    """Move the Drive spreadsheet for a retired class into _archived/ in the language folder.

    The sheet and folder come from the ID file (``config``). In dry-run mode
    prints what would happen; in apply mode performs the move. Returns True
    if the sheet was (or would be) archived.
    """
    spreadsheet_id = drive_ids.class_sheet_id(config, lang_id, class_name)
    folder_id = config.get(lang_id, {}).get("folder_id")

    if not spreadsheet_id:
        print(f"    no sheet ID in the ID file for {class_name} — skipping Drive archival")
        return False
    if not folder_id:
        print(f"    no folder_id in the ID file for {lang_id} — skipping Drive archival")
        return False

    meta = _sheet_metadata(doorway, spreadsheet_id, class_name)

    if not apply:
        ss_url = drive_ids.sheet_url(spreadsheet_id)
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
            f"ERROR: {lang_id} has sheets in the ID file but no {yaml_path.name} in "
            f"coded_data/{lang_id}/lang_setup/, so prune-manifest can't tell which "
            f"classes are active. Pull planars-data (git -C coded_data pull) or restore "
            f"the file from its history, then re-run.")
    with open(yaml_path, encoding="utf-8") as f:
        data = _yaml.safe_load(f)
    return set(((data or {}).get("classes") or {}).keys())


def _find_stale(config: dict) -> Dict[str, List[str]]:
    """Return {lang_id: [stale_class_name, ...]} for the languages in the ID file
    (the classes with a sheet there that the diagnostics YAML no longer has)."""
    result: Dict[str, List[str]] = {}
    for lang_id in drive_ids.languages(config):
        sheet_classes = set(drive_ids.class_sheets(config, lang_id))
        if not sheet_classes:
            continue
        active = _active_classes(lang_id)
        stale = sorted(sheet_classes - active)
        if stale:
            result[lang_id] = stale
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding prune-manifest`."""
    ap = argparse.ArgumentParser(
        description="Archive retired class TSVs and sheets and remove them from the ID file."
    )
    ap.add_argument(
        "--apply", action="store_true",
        help="archive TSVs, move Drive sheet, remove it from the ID file (default: dry run)",
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
    config = _load_drive_config()

    stale_map = _find_stale(config)

    if not stale_map:
        print("Every class sheet in the ID file matches active diagnostics — nothing to prune.")
        return

    # Always show dry-run summary; warn if annotation data exists (possible rename)
    print(f"{'DRY RUN — ' if not apply else ''}Stale class sheets found in the ID file:\n")
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
            _archive_drive_sheet(doorway, lang_id, class_name, config, apply=False)
            print(f"    would remove from the ID file: {lang_id}/{class_name}")
        print()

    if not apply:
        print("Run with --apply to make these changes.")
        return

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
            _archive_drive_sheet(doorway, lang_id, class_name, config, apply=True)

            # Remove from the ID file, and save it right after this class's
            # local/Drive archiving is done, not once after the whole loop --
            # a crash partway through must not leave the ID file still
            # showing an already-archived class as present, which would make
            # a retry reprocess it (issue #280).
            drive_ids.remove_class_sheet(config, lang_id, class_name)
            _save_drive_config(config)
            print(f"    removed from the ID file: {lang_id}/{class_name}")
            any_changes = True

        print()

    if any_changes:
        print("ID file updated.")
    else:
        print("No changes made (all classes skipped).")
