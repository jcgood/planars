#!/usr/bin/env python3
"""Restructure existing Google Sheets when the planar structure has changed significantly.

Use this when position numbers have changed or rows have been reordered — situations
where update_sheets.py (which only appends) is insufficient.

Run from the repo root:
    python -m coding restructure-sheets           # dry run — show what would change
    python -m coding restructure-sheets --apply   # archive old sheets and regenerate

    # Map renamed positions so their annotations are carried over instead of dropped:
    python -m coding restructure-sheets --rename-map "old name:new name"
    python -m coding restructure-sheets --rename-map old:new1 --rename-map old2:new2 --apply

    # Map renamed elements (e.g. casing fixes) so their annotations are carried over:
    python -m coding restructure-sheets --rename-element Ad-VP:AD-VP --apply
    python -m coding restructure-sheets --rename-element Ad-VP:AD-VP --rename-element Ad-V:AD-V --apply

    --rename-map takes "old_pos_name:new_pos_name" and can be repeated.
    --rename-element takes "old_element:new_element" and can be repeated.
    Without these flags, renamed positions/elements are treated as drops + new blank rows.

What this does per spreadsheet:
  1. Downloads current annotations from each tab
  2. [--apply] Moves the spreadsheet to archive/v{N}/ in Drive
  3. [--apply] Creates a new spreadsheet from the updated planar structure
  4. Carries over annotations matched by (Element, Position_Name)
  5. Leaves unmatched rows blank for re-annotation
  6. Updates sheets_manifest.json to point to the new spreadsheets

Authentication: same OAuth2 setup as generate_sheets.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

import gspread

from . import make_forms as _mf
from .make_forms import (
    build_element_index,
    _infer_language_id_from_planar_filename,
    _read_diagnostics_for_language,
)
from .generate_sheets import (
    _get_clients,
    _build_rows,
    _format_and_validate,
    _move_to_folder,
    _share_anyone_with_link,
    _open_spreadsheet,
    _TRAILING_COLS,
    _load_manifest_from_drive,
    _upload_planars_config,
    _load_drive_config,
    _save_drive_config,
)

MANIFEST_PATH = ROOT / "sheets_manifest.json"
CODED_DATA = ROOT / "coded_data"
_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}


# ---------------------------------------------------------------------------
# Annotation download
# ---------------------------------------------------------------------------

def _download_tab_annotations(
    ws: gspread.Worksheet,
) -> Dict[Tuple[str, str], Dict[str, str]]:
    """Download annotations from a tab, keyed by (element, pos_name).

    All non-structural columns (params + Comments) are included in the value dict.
    """
    rows = ws.get_all_values()
    if not rows:
        return {}
    header = rows[0]
    try:
        el_idx = header.index("Element")
        pos_name_idx = header.index("Position_Name")
    except ValueError:
        return {}

    annotation_cols = [
        (i, h) for i, h in enumerate(header) if h not in _STRUCTURAL_COLS
    ]

    result: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in rows[1:]:
        if len(row) <= max(el_idx, pos_name_idx):
            continue
        element = row[el_idx].strip()
        pos_name = row[pos_name_idx].strip()
        key = (element, pos_name)
        values = {col: (row[i] if i < len(row) else "") for i, col in annotation_cols}
        result[key] = values
    return result


# ---------------------------------------------------------------------------
# Rename-aware carry-over lookup
# ---------------------------------------------------------------------------

def _lookup_existing(
    element: str,
    pos_name: str,
    existing: Dict[Tuple[str, str], Dict[str, str]],
    old_for_new: Dict[str, str],
    old_el_for_new: Dict[str, str] = {},
) -> Optional[Dict[str, str]]:
    """Look up an annotation by (element, pos_name), falling back to rename aliases.

    Tries in order:
      1. Direct match: (element, pos_name)
      2. Position rename: (element, old_pos_name)
      3. Element rename: (old_element, pos_name)
      4. Both renames:   (old_element, old_pos_name)
    """
    if (v := existing.get((element, pos_name))) is not None:
        return v
    old_name = old_for_new.get(pos_name)
    if old_name and (v := existing.get((element, old_name))) is not None:
        return v
    old_el = old_el_for_new.get(element)
    if old_el:
        if (v := existing.get((old_el, pos_name))) is not None:
            return v
        if old_name and (v := existing.get((old_el, old_name))) is not None:
            return v
    return None


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _folder_id_from_url(folder_url: str) -> str:
    """Extract the Drive folder ID from a Drive folder URL (last path segment)."""
    return folder_url.rstrip("/").rsplit("/", 1)[-1]


def _get_or_create_subfolder(drive, parent_id: str, name: str) -> str:
    """Get or create a named subfolder inside parent_id."""
    results = drive.files().list(
        q=(
            f"name='{name}' and '{parent_id}' in parents"
            " and mimeType='application/vnd.google-apps.folder'"
            " and trashed=false"
        ),
        fields="files(id)",
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    folder = drive.files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id",
    ).execute()
    return folder["id"]


# ---------------------------------------------------------------------------
# Tab population with carry-over
# ---------------------------------------------------------------------------

def _old_key(
    element: str,
    pos_name: str,
    existing: Dict[Tuple[str, str], Dict[str, str]],
    old_for_new: Dict[str, str],
    old_el_for_new: Dict[str, str],
) -> Tuple[str, str]:
    """Return the key that was actually consumed in existing for this (element, pos_name)."""
    old_el  = old_el_for_new.get(element, element)
    old_pos = old_for_new.get(pos_name, pos_name)
    for key in [(element, pos_name), (element, old_pos), (old_el, pos_name), (old_el, old_pos)]:
        if key in existing:
            return key
    return (element, pos_name)  # fallback (won't be in existing, harmless)


def _write_tab_with_carryover(
    spreadsheet: gspread.Spreadsheet,
    tab_name: str,
    param_names: List[str],
    param_values: Dict[str, List[str]],
    rows: List[List[object]],
    existing: Dict[Tuple[str, str], Dict[str, str]],
    rename_map: Dict[str, str],
    element_rename_map: Dict[str, str] = {},
) -> Tuple[int, int, int]:
    """Create/clear a tab and populate it, carrying over matching annotations.

    Matching is by (Element, Position_Name), with optional rename_map (old→new
    position renames) and element_rename_map (old→new element label renames).

    Returns:
        (carried_count, new_count, dropped_count)
    """
    old_for_new    = {v: k for k, v in rename_map.items()}
    old_el_for_new = {v: k for k, v in element_rename_map.items()}
    all_cols = param_names + _TRAILING_COLS
    header = ["Element", "Position_Name", "Position_Number"] + all_cols

    carried = 0
    new = 0
    reachable_old_keys: set = set()
    all_rows = [header]

    for row in rows:
        element = str(row[0])
        pos_name = str(row[1])
        pos_num = str(row[2])
        is_keystone = pos_name.strip().lower() == "v:verbstem"

        old_values = _lookup_existing(element, pos_name, existing, old_for_new, old_el_for_new)
        if old_values is not None:
            param_vals = [old_values.get(p, "") for p in param_names]
            trailing_vals = [old_values.get(c, "") for c in _TRAILING_COLS]
            reachable_old_keys.add(_old_key(element, pos_name, existing, old_for_new, old_el_for_new))
            carried += 1
        else:
            param_vals = ["NA"] * len(param_names) if is_keystone else [""] * len(param_names)
            trailing_vals = [""] * len(_TRAILING_COLS)
            new += 1

        all_rows.append([element, pos_name, pos_num] + param_vals + trailing_vals)

    # Count existing annotations that were not matched by any row in the new structure.
    # These correspond to positions/elements that were removed from the planar file.
    dropped = sum(1 for k in existing if k not in reachable_old_keys)

    try:
        ws = spreadsheet.worksheet(tab_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=len(rows) + 2, cols=len(all_cols) + 3
        )

    ws.update(all_rows, "A1")
    per_col_values = [param_values.get(p, ["y", "n"]) for p in param_names]
    _format_and_validate(ws, len(rows), per_col_values)

    return carried, new, dropped


# ---------------------------------------------------------------------------
# Dry-run stats
# ---------------------------------------------------------------------------

def _compute_stats(
    rows: List[List[object]],
    existing: Dict[Tuple[str, str], Dict[str, str]],
    rename_map: Dict[str, str],
    element_rename_map: Dict[str, str] = {},
) -> Tuple[int, int, int, List[Tuple[str, str]]]:
    """Compute carry-over stats for a dry run without touching any sheet.

    Args:
        rows: new rows from _build_rows (the regenerated planar structure).
        existing: current annotations keyed by (element, pos_name).
        rename_map: {old_pos_name: new_pos_name} for renamed positions.
        element_rename_map: {old_element: new_element} for renamed element labels.

    Returns:
        (carried_count, renamed_count, new_count, dropped_keys) where:
          - carried_count: rows carried over by direct match
          - renamed_count: rows carried over via a rename (position or element)
          - new_count:     rows in rows with no match in existing (need re-annotation)
          - dropped_keys:  (element, pos_name) pairs in existing not matched by any row
    """
    old_for_new    = {v: k for k, v in rename_map.items()}
    old_el_for_new = {v: k for k, v in element_rename_map.items()}
    reachable_old_keys: set = set()
    new = 0
    renamed = 0
    for r in rows:
        element, pos_name = str(r[0]), str(r[1])
        old_values = _lookup_existing(element, pos_name, existing, old_for_new, old_el_for_new)
        if old_values is not None:
            old_k = _old_key(element, pos_name, existing, old_for_new, old_el_for_new)
            reachable_old_keys.add(old_k)
            if old_k != (element, pos_name):
                renamed += 1
        else:
            new += 1
    carried = len(reachable_old_keys) - renamed
    dropped = [k for k in existing if k not in reachable_old_keys]
    return carried, renamed, new, dropped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_flag_map(argv: List[str], flag: str) -> Dict[str, str]:
    """Parse all occurrences of --flag old:new into {old: new}."""
    result: Dict[str, str] = {}
    i = 0
    while i < len(argv):
        if argv[i] == flag and i + 1 < len(argv):
            pair = argv[i + 1]
            if ":" not in pair:
                raise SystemExit(f"{flag} requires 'old:new' format, got: {pair!r}")
            old, new = pair.split(":", 1)
            result[old.strip()] = new.strip()
            i += 2
        else:
            i += 1
    return result


def main() -> None:
    """Entry point for `python -m coding restructure-sheets`.

    For each class in the manifest, downloads current annotations, optionally
    archives the existing spreadsheet to archive/v{N}/ in Drive, creates a new
    spreadsheet from the updated planar structure, and carries over matching
    annotations by (Element, Position_Name). Unmatched rows are left blank for
    re-annotation. Updates the manifest on Drive and locally.
    In dry-run mode (no --apply) only prints what would change.
    """
    apply = "--apply" in sys.argv
    rename_map         = _parse_flag_map(sys.argv[1:], "--rename-map")
    element_rename_map = _parse_flag_map(sys.argv[1:], "--rename-element")

    gc, drive = _get_clients()
    manifest = _load_manifest_from_drive(drive)

    planar_files = sorted(CODED_DATA.glob("*/planar_input/planar_*.tsv"))
    if not planar_files:
        raise SystemExit("No planar_*.tsv found in coded_data/*/planar_input/")

    any_changes = False

    for planar_file in planar_files:
        lang_id = _infer_language_id_from_planar_filename(planar_file.name)

        _mf.DATA_DIR = str(planar_file.parent)
        element_index = build_element_index(planar_file.name)
        specs = _read_diagnostics_for_language(lang_id)

        classes: Dict[str, List[Tuple[str, List[str], Dict[str, List[str]]]]] = {}
        for class_name, construction, param_names, param_values in specs:
            classes.setdefault(class_name, []).append((construction, param_names, param_values))

        print(f"\n{'DRY RUN — ' if not apply else ''}Language: {lang_id}")
        if rename_map:
            for old, new in rename_map.items():
                print(f"  rename position: {old!r} -> {new!r}")
        if element_rename_map:
            for old, new in element_rename_map.items():
                print(f"  rename element:  {old!r} -> {new!r}")
        if not apply:
            print("(run with --apply to archive old sheets and regenerate)")

        lang_data = manifest.get(lang_id, {})
        folder_url = lang_data.get("folder_url", "")
        folder_id = _folder_id_from_url(folder_url) if folder_url else None

        for class_name, constructions_list in classes.items():
            sheet_info = lang_data.get("sheets", {}).get(class_name)
            if not sheet_info:
                print(f"\n  {class_name}: not in manifest, skipping (run python -m coding generate-sheets first)")
                continue

            version = sheet_info.get("version", 1)
            print(f"\n  {class_name} (current v{version})")

            ss = _open_spreadsheet(gc, sheet_info["spreadsheet_id"])

            # Step 1: Download current annotations from all tabs
            all_annotations: Dict[str, Dict[Tuple[str, str], Dict[str, str]]] = {}
            for construction in sheet_info["constructions"]:
                try:
                    ws = ss.worksheet(construction)
                    all_annotations[construction] = _download_tab_annotations(ws)
                    print(f"    [{construction}] downloaded {len(all_annotations[construction])} rows")
                except gspread.WorksheetNotFound:
                    all_annotations[construction] = {}
                    print(f"    [{construction}] tab not found")

            # Step 2: Compute and report stats per tab; decide if this class needs restructuring
            class_needs_restructure = False
            for construction, param_names, param_values in constructions_list:
                rows = _build_rows(element_index, lang_id, param_names)
                existing = all_annotations.get(construction, {})
                carried, renamed, new_count, dropped = _compute_stats(rows, existing, rename_map, element_rename_map)
                parts = [f"carry over {carried}"]
                if renamed:
                    parts.append(f"rename {renamed}")
                parts.append(f"new blank {new_count}")
                if dropped:
                    dropped_labels = [f"{el}@{pn}" for el, pn in dropped]
                    parts.append(f"drop {len(dropped)} ({', '.join(dropped_labels)})")
                print(f"    [{construction}] {'; '.join(parts)}")
                if renamed or new_count or dropped:
                    class_needs_restructure = True
                    any_changes = True

            if not class_needs_restructure:
                print(f"    (no changes — skipping)")
                continue

            if not apply:
                continue

            # Step 3: Archive existing sheet
            new_version = version + 1
            if folder_id:
                archive_id = _get_or_create_subfolder(drive, folder_id, "archive")
                ver_folder_id = _get_or_create_subfolder(drive, archive_id, f"v{version}")
                _move_to_folder(drive, ss.id, ver_folder_id)
                print(f"    Archived to archive/v{version}/")

            # Step 4: Create new sheet and populate with carry-over
            sheet_title = f"{class_name}_{lang_id}"
            new_ss = gc.create(sheet_title)
            if folder_id:
                _move_to_folder(drive, new_ss.id, folder_id)
                _share_anyone_with_link(drive, new_ss.id)

            default_ws = new_ss.sheet1
            tab_names = []
            new_construction_params = {}

            for construction, param_names, param_values in constructions_list:
                rows = _build_rows(element_index, lang_id, param_names)
                existing = all_annotations.get(construction, {})
                carried, new_count, dropped_count = _write_tab_with_carryover(
                    new_ss, construction, param_names, param_values, rows, existing,
                    rename_map, element_rename_map,
                )
                tab_names.append(construction)
                new_construction_params[construction] = {
                    "param_names": param_names,
                    "param_values": param_values,
                }
                print(f"    [{construction}] wrote: carried {carried}, new blank {new_count}, dropped {dropped_count}")

            if default_ws.title not in tab_names:
                new_ss.del_worksheet(default_ws)

            # Step 5: Update manifest
            manifest[lang_id]["sheets"][class_name] = {
                "spreadsheet_id": new_ss.id,
                "url": new_ss.url,
                "constructions": tab_names,
                "construction_params": new_construction_params,
                "version": new_version,
            }
            print(f"    New sheet (v{new_version}): {new_ss.url}")

    if apply:
        # Update local manifest (gitignored reference copy)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # Upload the merged planars_config.json to Drive.
        config = _load_drive_config()
        for lid, ld in manifest.items():
            # Ensure folder_id is present (derive from folder_url if missing).
            if "folder_id" not in ld:
                folder_url = ld.get("folder_url", "")
                if folder_url:
                    ld["folder_id"] = folder_url.rstrip("/").rsplit("/", 1)[-1]
            config.setdefault(lid, {})["folder_id"] = ld.get("folder_id", "")
            config[lid].pop("manifest_file_id", None)
        existing_file_id = config.get("_planars_config_file_id")
        root_folder_id = config.get("_root_folder_id")
        file_id = _upload_planars_config(drive, manifest, root_folder_id, existing_file_id)
        config["_planars_config_file_id"] = file_id
        _save_drive_config(config)
        print("\nManifest updated on Drive.")

    if not apply:
        print("\nRun with --apply to make these changes.")
    else:
        print("\nDone.")
        from .generate_notebooks import regenerate_notebooks
        regenerate_notebooks()


if __name__ == "__main__":
    main()
