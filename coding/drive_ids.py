"""Where each language's class sheets, status sheet and notification issue
are, read from and written to the ID file (``drive_config.json``).

Phase 10 unit 11c (``docs/ownership-design.md`` § 6 item 7): the ID file is
the one record of where every Drive file the tooling made is. Until 11c the
class sheets' IDs, the status sheet and the notification issue were kept
only in the manifest on Drive, a copy that went stale; they live here now,
and the manifest is written from them until it is deleted.

Every function takes the ID file's contents as loaded by the command
(``drive._load_drive_config()``) and, for the setters, changes them in place;
the command saves them with ``drive._save_drive_config()``, which writes
through the local-file door. Taking the contents rather than reading the
file lets each command load it once and lets tests hand in their own.

A language's entry in the ID file::

    "stan1293": {
      "folder_id": ...,                # and the other keys its writers own
      "class_sheets": {"ciscategorial": {"id": "1O3d…", "version": 2}, …},
      "status_sheet_id": "1ebu…",
      "notification_issue": 243
    }

``version`` counts how many times restructure-sheets has replaced the sheet;
it names the archived copy (``{class}_{lang}_v{version}``).
"""
from __future__ import annotations

from typing import Dict, List, Optional

CLASS_SHEETS = "class_sheets"
STATUS_SHEET_ID = "status_sheet_id"
NOTIFICATION_ISSUE = "notification_issue"

_SHEETS_URL = "https://docs.google.com/spreadsheets/d/{}"


def sheet_url(spreadsheet_id: str) -> str:
    """The address a person opens a Sheet at, built from its ID."""
    return _SHEETS_URL.format(spreadsheet_id)


def _lang(config: Dict, lang_id: str) -> Dict:
    return config.get(lang_id) or {}


def languages(config: Dict) -> List[str]:
    """Every language the ID file has an entry for, sorted. Keys starting
    with ``_`` are the project's own files (the root folder …), not
    languages."""
    return sorted(k for k, v in config.items()
                  if not k.startswith("_") and isinstance(v, dict))


def class_sheets(config: Dict, lang_id: str) -> Dict[str, str]:
    """``{class_name: spreadsheet_id}`` for every class sheet the language has."""
    return {cls: entry["id"]
            for cls, entry in _lang(config, lang_id).get(CLASS_SHEETS, {}).items()}


def class_sheet_id(config: Dict, lang_id: str, class_name: str) -> Optional[str]:
    """The class sheet's ID, or None if the language has none for the class."""
    return class_sheets(config, lang_id).get(class_name)


def class_sheet_version(config: Dict, lang_id: str, class_name: str) -> int:
    """How many sheets the class has had (1 for one never replaced)."""
    entry = _lang(config, lang_id).get(CLASS_SHEETS, {}).get(class_name)
    if entry is None:
        raise KeyError(f"{lang_id} has no {class_name} sheet in the ID file")
    return entry.get("version", 1)


def set_class_sheet(config: Dict, lang_id: str, class_name: str,
                    spreadsheet_id: str, version: int = 1) -> None:
    """Record the language's sheet for the class (made or replaced)."""
    config.setdefault(lang_id, {}).setdefault(CLASS_SHEETS, {})[class_name] = {
        "id": spreadsheet_id, "version": version}


def remove_class_sheet(config: Dict, lang_id: str, class_name: str) -> None:
    """Forget the class's sheet (retired: archived on Drive, not deleted)."""
    _lang(config, lang_id).get(CLASS_SHEETS, {}).pop(class_name, None)


def status_sheet_id(config: Dict, lang_id: str) -> Optional[str]:
    return _lang(config, lang_id).get(STATUS_SHEET_ID)


def set_status_sheet_id(config: Dict, lang_id: str, spreadsheet_id: str) -> None:
    config.setdefault(lang_id, {})[STATUS_SHEET_ID] = spreadsheet_id


def notification_issue(config: Dict, lang_id: str) -> Optional[int]:
    """The number of the language's long-lived ``sheet-updates`` issue."""
    return _lang(config, lang_id).get(NOTIFICATION_ISSUE)


def set_notification_issue(config: Dict, lang_id: str, number: int) -> None:
    config.setdefault(lang_id, {})[NOTIFICATION_ISSUE] = int(number)


def copy_from_manifest(config: Dict, lang_id: str, entry: Dict) -> None:
    """Record what one language's manifest entry says about its class sheets,
    status sheet and notification issue. Used once by
    ``migrations/ids_from_manifest.py`` and by the tests' offline Drive,
    whose saved data has a manifest but no ID file; both go with the
    manifest in 11c-5. The other IDs the live ID file already holds (folder,
    notes Doc, planar and diagnostics Sheets) are copied only where missing."""
    lang = config.setdefault(lang_id, {})
    for key in ("folder_id", "notes_doc_id",
                "planar_spreadsheet_id", "diagnostics_spreadsheet_id"):
        if entry.get(key) and not lang.get(key):
            lang[key] = entry[key]
    for class_name, info in (entry.get("sheets") or {}).items():
        set_class_sheet(config, lang_id, class_name, info["spreadsheet_id"],
                        info.get("version", 1))
    url = entry.get("status_sheet_url")
    if url:
        set_status_sheet_id(config, lang_id, url.rstrip("/").rsplit("/", 1)[-1])
    if entry.get("notification_issue"):
        set_notification_issue(config, lang_id, entry["notification_issue"])
