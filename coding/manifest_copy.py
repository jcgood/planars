"""The manifest on Drive, rebuilt from the ID file and the sources.

Phase 10 unit 11c (``docs/ownership-design.md`` § 6 item 7). The manifest
(``manifest.json`` in the root Drive folder) is read only by the published
Colab notebooks, until they find their sheets by label (11c-5), when it is
deleted along with this module. Until then it is a copy, rebuilt whole by
``publish`` from each fact's one home, never edited:

- which sheets exist, the status sheet, the notification issue: the ID file
  (``drive_ids``), and its other IDs (folder, notes Doc, planar and
  diagnostics Sheets);
- each class sheet's constructions: the tabs it has (``construction_tabs``);
  each construction's criteria (``param_names``): the diagnostics YAML, with
  the schema's per-construction criteria applied, as generate-sheets builds
  the tabs;
- the planar: the planar TSV; ``glottolog`` and ``meta``: ``schemas/languages.yaml``.

``publish`` runs at the end of every command that records a new or retired
sheet in the ID file, so the notebooks see a new sheet the same day, and
daily as its own command (the refresh's ``manifest copy`` step)::

    python -m coding publish-manifest           # dry run: say what would be published
    python -m coding publish-manifest --apply   # rebuild and upload it
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Optional

from planars.languages import load_languages

from . import drive_ids

# The ID file's keys copied into the manifest as they are, for the notebooks.
_COPIED_IDS = ("folder_id", "notes_doc_id",
               "planar_spreadsheet_id", "diagnostics_spreadsheet_id")
_FOLDER_URL = "https://drive.google.com/drive/folders/{}"


def build(doorway, config: Dict, coded_data: Optional[Path] = None) -> Dict:
    """The manifest as it should be now: one entry per language in the ID
    file. Opens each class sheet to read which construction tabs it has."""
    from .file_door import CODED_DATA, planar
    from .make_forms import _read_diagnostics_for_language, planar_to_manifest_dict
    from .schemas import apply_schema_criteria

    coded = Path(coded_data) if coded_data else CODED_DATA
    languages = load_languages()
    manifest: Dict = {}
    for lang_id in drive_ids.languages(config):
        ids = config[lang_id]
        entry: Dict = {}
        known = languages.get(lang_id) or {}
        for key in ("glottolog", "meta"):
            if key in known:
                entry[key] = known[key]
        for key in _COPIED_IDS:
            if ids.get(key):
                entry[key] = ids[key]
        if ids.get("folder_id"):
            entry["folder_url"] = _FOLDER_URL.format(ids["folder_id"])
        for kind in ("planar", "diagnostics"):
            sid = ids.get(f"{kind}_spreadsheet_id")
            if sid:
                entry[f"{kind}_spreadsheet_url"] = drive_ids.sheet_url(sid)

        setup = coded / lang_id / "lang_setup"
        try:
            diagnostics = _read_diagnostics_for_language(lang_id, setup)
        except FileNotFoundError:
            diagnostics = []
        by_class: Dict[str, list] = {}
        for cls, construction, names, values in diagnostics:
            by_class.setdefault(cls, []).append((construction, names, values))

        sheets: Dict = {}
        for cls, sid in drive_ids.class_sheets(config, lang_id).items():
            tabs = doorway.open_spreadsheet(sid).construction_tabs()
            criteria = {c: pn for c, pn, _ in
                        apply_schema_criteria(cls, by_class.get(cls, []), lang_id)}
            sheets[cls] = {
                "spreadsheet_id": sid,
                "url": drive_ids.sheet_url(sid),
                "constructions": tabs,
                "construction_params": {c: {"param_names": criteria[c]}
                                        for c in tabs if c in criteria},
                "version": drive_ids.class_sheet_version(config, lang_id, cls),
            }
        entry["sheets"] = sheets

        planar_path = planar(lang_id).path
        if coded_data:
            planar_path = coded / planar_path.relative_to(CODED_DATA)
        if planar_path.exists():
            entry["planar"] = planar_to_manifest_dict(planar_path, lang_id)
        status = drive_ids.status_sheet_id(config, lang_id)
        if status:
            entry["status_sheet_url"] = drive_ids.sheet_url(status)
        issue = drive_ids.notification_issue(config, lang_id)
        if issue:
            entry["notification_issue"] = issue
        manifest[lang_id] = entry
    return manifest


def publish(doorway, config: Dict) -> str:
    """Rebuild the manifest and write it to Drive (through the door, which
    checks it against its contract). Records its ID in ``config`` and returns
    it; the caller saves ``config``."""
    from .drive import upload_manifest
    file_id = upload_manifest(doorway, build(doorway, config),
                              config.get("_root_folder_id"),
                              config.get("_planars_config_file_id"))
    config["_planars_config_file_id"] = file_id
    return file_id


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m coding publish-manifest",
        description="Rebuild the manifest copy the Colab notebooks read, and upload it.")
    p.add_argument("--apply", action="store_true", help="upload it (default: dry run)")
    return p


def main(args: argparse.Namespace | None = None) -> None:
    args = args or build_parser().parse_args()
    from .drive import _load_drive_config, _save_drive_config
    from .drive_doorway import get_doorway
    doorway = get_doorway()
    config = _load_drive_config()
    if not args.apply:
        manifest = build(doorway, config)
        sheets = sum(len(e.get("sheets", {})) for e in manifest.values())
        print(f"Would publish the manifest copy: {len(manifest)} language(s), "
              f"{sheets} class sheet(s). Add --apply to upload it.")
        return
    file_id = publish(doorway, config)
    _save_drive_config(config)
    print(f"Manifest copy published (id: {file_id}).")
