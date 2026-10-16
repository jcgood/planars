"""One-time migration: give every existing Drive file the tooling made its identity label.

Motivation: Phase 10 unit 5d (issue #271; docs/drive-door-design.md § 8,
decision 8 of the 2026-10-14 "identity labels" entry in
docs/data-layer-progress.md). Since 5d every file the tooling makes is
labelled with what it is (Drive properties `planars_kind`, `planars_lang`,
`planars_class`, `planars_name`; `planars_state=archived` once archived), and
each tab of a class sheet with what it is (developer metadata). Files made
before then carry no label, so the Drive door still places class sheets from
the manifest. This script labels what already exists, so that fallback can be
deleted.

What it labels, found from the places that record each file:
  - from drive_config.json: the root folder, the manifest, the all-languages
    notebook; per language its folder, planar and diagnostics sheets, notes
    Doc, PDF report and three notebooks;
  - from the manifest: each language's class sheets (live), and each class
    sheet's tabs;
  - each language folder's `_archived/` folder and the older `_archived/v{N}/`
    folders inside it, and the class sheets in them (named `{class}_{lang}`
    or `{class}_{lang}_v{N}`), labelled archived;
  - the "Annotation Status" folder and the `status_{lang}` sheets in it.
A file already labelled as what it is is left alone. A file labelled as
something else is never relabelled; it is reported. A file in `_archived/`
whose name isn't a class sheet's is reported and left unlabelled. A file the
tooling can't reach is reported.

Run: 2026-10-15. Labelled 127 files (24 live class sheets and their 108
tabs, 51 archived class sheets, 9 folders, and each language's other files);
left unlabelled only synth0001's retired allomorphy screening sheet. A second
dry run found every file labelled.

Usage:
    python migrations/label_drive_files.py           # dry run: reads only
    python migrations/label_drive_files.py --apply

Post-run checks: run the dry run again: every line should say "labelled".
Then refreeze the test data (python -m coding capture-drive-state --apply),
which now records the labels.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding import drive_door  # noqa: E402
from coding.drive import _load_drive_config, load_manifest  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402

_FOLDER_MIME = "application/vnd.google-apps.folder"
_SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
_STATUS_FOLDER_NAME = "Annotation Status"   # generate_status_sheet._STATUS_FOLDER_NAME
_ARCHIVE_FOLDER_NAME = "_archived"
_VERSION_FOLDER = re.compile(r"^v\d+$")
# Sheets in _archived/ named like a class sheet that aren't one: the
# standalone allomorphy screening sheet, retired 2026-10-11
# (migrations/retire_allomorphy_screening_sheet_synth0001.py). No kind fits
# it, so it stays unlabelled.
_NOT_CLASS_SHEETS = {"biuniqueness_allomorphy"}

# Per-language entries of drive_config.json and the kind each one is.
_LANG_FILES = {
    "folder_id": lambda lang: drive_door.folder("language", lang),
    "planar_spreadsheet_id": lambda lang: drive_door.lang_file("planar_sheet", lang),
    "diagnostics_spreadsheet_id": lambda lang: drive_door.lang_file("diagnostics_sheet", lang),
    "notes_doc_id": lambda lang: drive_door.lang_file("notes_doc", lang),
    "report_file_id": lambda lang: drive_door.lang_file("report", lang),
    "domains_notebook_file_id": lambda lang: drive_door.notebook("domains", lang),
    "validation_notebook_file_id": lambda lang: drive_door.notebook("validation", lang),
    "report_notebook_file_id": lambda lang: drive_door.notebook("report", lang),
}


@dataclass
class Target:
    file_id: str
    identity: drive_door.Identity
    archived: bool = False
    where: str = ""          # which record named it


def _targets(doorway, config: Dict, manifest: Dict, unplaced: List[str]) -> List[Target]:
    targets: List[Target] = []
    if config.get("_root_folder_id"):
        targets.append(Target(config["_root_folder_id"], drive_door.folder("root"),
                              where="drive_config"))
    if config.get("_planars_config_file_id"):
        targets.append(Target(config["_planars_config_file_id"], drive_door.manifest(),
                              where="drive_config"))
    if config.get("_all_languages_notebook_file_id"):
        targets.append(Target(config["_all_languages_notebook_file_id"],
                              drive_door.notebook("all_languages"), where="drive_config"))

    langs = sorted({k for k, v in list(config.items()) + list(manifest.items())
                    if not k.startswith("_") and isinstance(v, dict)})
    for lang in langs:
        for source, entry in (("drive_config", config.get(lang) or {}),
                              ("manifest", manifest.get(lang) or {})):
            for key, make in _LANG_FILES.items():
                if entry.get(key):
                    targets.append(Target(entry[key], make(lang), where=f"{source} {key}"))
        for class_name, info in sorted((manifest.get(lang, {}).get("sheets") or {}).items()):
            sid = isinstance(info, dict) and (info.get("spreadsheet_id") or info.get("id"))
            if sid:
                targets.append(Target(sid, drive_door.class_sheet(lang, class_name),
                                      where="manifest sheets"))

        folder_id = (config.get(lang) or {}).get("folder_id") or (manifest.get(lang) or {}).get("folder_id")
        if not folder_id:
            continue
        archive_pattern = re.compile(rf"^(?P<cls>.+)_{re.escape(lang)}(?:_v\d+)?$")
        # Before restructure-sheets put a _v{N} suffix on the sheet's name,
        # it archived into _archived/v{N}/ folders; those are archive folders too.
        folders = [(a["id"], f"{lang}/{_ARCHIVE_FOLDER_NAME}") for a in doorway.list_files(
            f"name='{_ARCHIVE_FOLDER_NAME}' and mimeType='{_FOLDER_MIME}' "
            f"and '{folder_id}' in parents and trashed=false")]
        while folders:
            archive_id, path = folders.pop(0)
            targets.append(Target(archive_id, drive_door.folder("archive", lang), where=path))
            for f in doorway.list_files(f"'{archive_id}' in parents and trashed=false",
                                        fields="files(id, name, mimeType)"):
                m = archive_pattern.match(f["name"])
                where = f"{path}/{f['name']}"
                if f.get("mimeType") == _FOLDER_MIME and _VERSION_FOLDER.match(f["name"]):
                    folders.append((f["id"], where))
                elif (f.get("mimeType") == _SPREADSHEET_MIME and m
                        and m["cls"] not in _NOT_CLASS_SHEETS):
                    targets.append(Target(f["id"], drive_door.class_sheet(lang, m["cls"]),
                                          archived=True, where=where))
                else:
                    unplaced.append(f"{where} ({f['id']}): not a class sheet")

    status_pattern = re.compile(r"^status_(?P<lang>.+)$")
    for status in doorway.list_files(f"name='{_STATUS_FOLDER_NAME}' and "
                                     f"mimeType='{_FOLDER_MIME}' and trashed=false"):
        targets.append(Target(status["id"], drive_door.folder("status"),
                              where=_STATUS_FOLDER_NAME))
        for f in doorway.list_files(f"'{status['id']}' in parents and trashed=false",
                                    fields="files(id, name, mimeType)"):
            m = status_pattern.match(f["name"])
            if f.get("mimeType") == _SPREADSHEET_MIME and m:
                targets.append(Target(f["id"], drive_door.lang_file("status_sheet", m["lang"]),
                                      where=f"{_STATUS_FOLDER_NAME}/{f['name']}"))
            else:
                unplaced.append(f"{_STATUS_FOLDER_NAME}/{f['name']} ({f['id']}): "
                                "not named like a status sheet")
    return targets


def _dedupe(targets: List[Target], problems: List[str]) -> List[Target]:
    """One target per file. Two records naming one file as different things
    is a problem to report, not to choose between."""
    by_id: Dict[str, Target] = {}
    for t in targets:
        seen = by_id.get(t.file_id)
        if seen is None:
            by_id[t.file_id] = t
        elif (seen.identity, seen.archived) != (t.identity, t.archived):
            problems.append(f"{t.file_id}: {seen.where} says {seen.identity.describe()}, "
                            f"{t.where} says {t.identity.describe()}; left unlabelled")
            seen.identity = None  # type: ignore[assignment]
    return [t for t in by_id.values() if t.identity is not None]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    apply = ap.parse_args().apply

    doorway = get_doorway()
    config = _load_drive_config()
    manifest = load_manifest(doorway)
    unplaced: List[str] = []
    problems: List[str] = []
    targets = _dedupe(_targets(doorway, config, manifest, unplaced), problems)

    print(f"{'DRY RUN — ' if not apply else ''}{len(targets)} Drive file(s) found:")
    counts = {"labelled": 0, "to label": 0, "tabs to label": 0}
    for t in sorted(targets, key=lambda t: (t.identity.lang_id or "", t.identity.kind,
                                            t.identity.describe())):
        what = t.identity.describe() + (" (archived)" if t.archived else "")
        try:
            meta = doorway.get_file(t.file_id, fields="id,name,trashed,properties")
        except Exception as exc:  # noqa: BLE001 - reported, the run goes on
            problems.append(f"{what} {t.file_id}: cannot be read ({exc.__class__.__name__}: "
                            f"{str(exc).splitlines()[0][:120]})")
            continue
        if meta.get("trashed"):
            problems.append(f"{what} {t.file_id} ({meta.get('name')}): in the Drive bin")
            continue
        props = meta.get("properties") or {}
        existing = drive_door.Identity.from_labels(props)
        if existing is None and drive_door._LABEL["kind"] in props:
            problems.append(f"{what} {t.file_id}: carries a label the door can't place {props}")
            continue
        if existing is not None and existing != t.identity:
            problems.append(f"{what} {t.file_id}: already labelled {existing.describe()}; "
                            "not relabelled")
            continue
        archived_now = props.get(drive_door.STATE_LABEL) == drive_door.ARCHIVED
        needs_identity = existing is None
        needs_state = t.archived and not archived_now
        if archived_now and not t.archived:
            problems.append(f"{what} {t.file_id}: labelled archived but recorded as live; "
                            "left as it is")

        tabs = 0
        if t.identity.kind == drive_door.CLASS_SHEET and not t.archived:
            # When this ran, the door still placed an unlabelled class sheet
            # from the manifest, which was enough to read its spec on a dry run.
            # Since that fallback was deleted (2026-10-16), --apply still works:
            # the identity label is written before the tabs are labelled.
            tabs = len(doorway.unlabelled_tabs(doorway.open_spreadsheet(t.file_id)))

        if not (needs_identity or needs_state or tabs):
            counts["labelled"] += 1
            print(f"  labelled      {what}")
            continue
        steps = (["identity"] if needs_identity else []) + (["archived"] if needs_state else []) \
            + ([f"{tabs} tab(s)"] if tabs else [])
        counts["to label"] += 1
        counts["tabs to label"] += tabs
        print(f"  {'labelling' if apply else 'to label':<13} {what}: {', '.join(steps)}"
              f"   [{meta.get('name')}]")
        if not apply:
            continue
        if needs_identity:
            doorway.set_identity(t.file_id, t.identity)
        if needs_state:
            doorway.mark_archived(t.file_id)
        if tabs:
            doorway.label_tabs(doorway.open_spreadsheet(t.file_id))

    print(f"\n{counts['labelled']} already labelled; {counts['to label']} "
          f"{'labelled now' if apply else 'to label'} "
          f"({counts['tabs to label']} class-sheet tab(s)).")
    if unplaced:
        print("\nFound but not placed (left unlabelled):")
        for line in unplaced:
            print(f"  {line}")
    if problems:
        print("\nProblems (nothing written for these):")
        for line in problems:
            print(f"  {line}")
    if not apply:
        print("\nRun with --apply to write the labels.")


if __name__ == "__main__":
    # Runs outside `python -m coding`, so it tells the Drive door itself.
    with drive_door.running("migration label_drive_files",
                            may_write="--apply" in sys.argv):
        main()
