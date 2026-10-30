"""A language's annotation, read from its Google Sheets into the same folder
layout as ``coded_data/``, so the reports run on it exactly as they run on
the imported TSVs.

This is how the Colab notebooks read the annotation (Phase 10 unit 11c,
``docs/ownership-design.md`` § 3.6 and § 6 item 7). They find the
language's sheets by the labels the tooling writes on every file it makes
(``planars/drive_labels.py``), never by a list of IDs kept somewhere else.
That list was the manifest, which went stale.

``download_language`` writes, under ``dest``::

    coded_data/{lang_id}/{class}/{construction}.tsv   one per construction tab
    coded_data/{lang_id}/lang_setup/planar_{lang_id}.tsv   from the planar Sheet

Each construction tab is found by its tab labels, so a tab renamed by hand
is still found. Each is written exactly as the sheet holds it: its header,
and every row padded or cut to the header's width. The reports then read
``dest`` as their ``repo_root`` (``planars.reports``). What the diagnostics
YAML expects but no sheet has yet is not known here, since the YAML is not
on Drive; ``validate-coding`` reports that to the coordinator.

It also returns each class sheet's Status tab (``planars.schema_values.status_map``).

``open_language`` (one language) and ``open_all_languages`` (every language
with a planar Sheet, ``languages``) are the Colab entry points: they take
the notebook's Drive service and gspread client. Tests call
``download_language`` with the offline fake's ``list_files`` and
``open_spreadsheet``.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from planars import drive_labels as L
from planars.schema_values import STATUS_TAB, status_map

ListFiles = Callable[[str], List[Dict[str, Any]]]
OpenSpreadsheet = Callable[[str], Any]

_TAB_FIELDS = "sheets(properties(sheetId,title,index),developerMetadata)"


@dataclass
class Language:
    """What ``download_language`` read: ``root`` to pass to the reports as
    ``repo_root``, and each class's Status tab."""
    lang_id: str
    root: Path
    status: Dict[str, Dict[str, str]] = field(default_factory=dict)


def _query(kind: str, lang_id: str) -> str:
    return (f"properties has {{ key='{L.KIND}' and value='{kind}' }} and "
            f"properties has {{ key='{L.LANG}' and value='{lang_id}' }} and trashed=false")


def _live(found: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Leave out sheets retired or replaced (kept read-only, labelled archived)."""
    return [f for f in found if (f.get("properties") or {}).get(L.STATE) != L.ARCHIVED]


def _write_tsv(path: Path, values: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = list(values[0]) if values else []
    width = len(header)
    with open(path, "w", encoding="utf-8", newline="") as f:
        out = csv.writer(f, delimiter="\t", lineterminator="\n")
        out.writerow(header)
        for row in values[1:]:
            out.writerow((list(row) + [""] * width)[:width])


def _construction_tabs(ss) -> List[Any]:
    """(construction, worksheet) for each tab labelled as a construction."""
    meta = ss.fetch_sheet_metadata(params={"fields": _TAB_FIELDS})
    names = {}
    for sheet in meta.get("sheets", []):
        labels = {m["metadataKey"]: m.get("metadataValue", "")
                  for m in sheet.get("developerMetadata", [])}
        if labels.get(L.TAB_KIND) == L.CONSTRUCTION_TAB and labels.get(L.TAB_NAME):
            names[sheet["properties"]["sheetId"]] = labels[L.TAB_NAME]
    return [(names[ws.id], ws) for ws in ss.worksheets() if ws.id in names]


def download_language(lang_id: str, dest: Path, *, list_files: ListFiles,
                      open_spreadsheet: OpenSpreadsheet) -> Language:
    """Read ``lang_id``'s class sheets and planar Sheet into ``dest``."""
    dest = Path(dest)
    lang_dir = dest / "coded_data" / lang_id
    result = Language(lang_id, dest)

    planars_ = _live(list_files(_query(L.PLANAR_SHEET, lang_id)))
    if len(planars_) != 1:
        raise RuntimeError(f"expected one planar Sheet labelled for {lang_id}, "
                           f"found {len(planars_)}")
    planar = open_spreadsheet(planars_[0]["id"])
    _write_tsv(lang_dir / "lang_setup" / f"planar_{lang_id}.tsv",
               planar.worksheets()[0].get_all_values())

    by_class: Dict[str, str] = {}
    for f in _live(list_files(_query(L.CLASS_SHEET, lang_id))):
        cls = (f.get("properties") or {}).get(L.CLASS)
        if not cls:
            raise RuntimeError(f"class sheet {f.get('name')!r} ({f['id']}) has no class label")
        if cls in by_class:
            raise RuntimeError(f"two {cls} sheets labelled for {lang_id} and neither archived: "
                               f"{by_class[cls]} and {f['id']}")
        by_class[cls] = f["id"]

    for cls, sid in sorted(by_class.items()):
        ss = open_spreadsheet(sid)
        for construction, ws in _construction_tabs(ss):
            _write_tsv(lang_dir / cls / f"{construction}.tsv", ws.get_all_values())
        status_ws = next((ws for ws in ss.worksheets() if ws.title == STATUS_TAB), None)
        if status_ws is not None:
            statuses = status_map(status_ws.get_all_values())
            if statuses:
                result.status[cls] = statuses
    return result


def languages(list_files: ListFiles) -> List[str]:
    """Every language with a planar Sheet (each language has exactly one), sorted."""
    found = list_files(f"properties has {{ key='{L.KIND}' and value='{L.PLANAR_SHEET}' }} "
                       "and trashed=false")
    return sorted({(f.get("properties") or {}).get(L.LANG) for f in _live(found)} - {None})


def open_language(lang_id: str, drive_service, gc, dest: Optional[Path] = None) -> Language:
    """In Colab: read ``lang_id``'s sheets with the notebook's Drive service
    and gspread client, into ``dest`` (a new temporary folder if not given)."""
    root = Path(dest) if dest else _temp_root()
    return download_language(lang_id, root, list_files=_colab_list_files(drive_service),
                             open_spreadsheet=gc.open_by_key)


def open_all_languages(drive_service, gc, dest: Optional[Path] = None) -> Dict[str, Language]:
    """In Colab: every language's sheets into one folder (``dest``, or a new
    temporary one), for the project-wide reports. Each ``Language`` has the
    same ``root``."""
    list_files = _colab_list_files(drive_service)
    root = Path(dest) if dest else _temp_root()
    return {lang_id: download_language(lang_id, root, list_files=list_files,
                                       open_spreadsheet=gc.open_by_key)
            for lang_id in languages(list_files)}


def _temp_root() -> Path:
    import tempfile
    return Path(tempfile.mkdtemp(prefix="planars_sheets_"))


def _colab_list_files(drive_service) -> ListFiles:
    def list_files(q: str) -> List[Dict[str, Any]]:
        found, token = [], None
        while True:
            page = drive_service.files().list(
                q=q, fields="nextPageToken, files(id, name, properties)",
                pageSize=100, pageToken=token,
                supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            found += page.get("files", [])
            token = page.get("nextPageToken")
            if not token:
                return found
    return list_files
