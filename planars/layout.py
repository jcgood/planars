"""How a language's folder in planars-data is laid out: the one statement.

``coded_data/{lang_id}/`` holds one folder per class (its constructions'
annotation TSVs) and these folders, which are not classes:

- ``lang_setup/``: the planar file, the diagnostics file and the proposal
  sheet's base;
- ``archive/``: every previous version the local-file door replaced;
- ``records/``: copies of what people write in Google that no other file
  holds (Phase 10 unit 16, docs/plain-record-design.md).

Files at the language's top level (the change log, ``changes.tsv``) are
never in a class.

The local-file door (``coding/file_door.py``) writes to these folders by
these names, and everything that walks a language's folder for its classes
calls ``class_folders``, so a new kind of folder is added here once.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

SETUP_FOLDER = "lang_setup"
ARCHIVE_FOLDER = "archive"
RECORDS_FOLDER = "records"
NOT_CLASS_FOLDERS = frozenset({SETUP_FOLDER, ARCHIVE_FOLDER, RECORDS_FOLDER})


def class_folders(lang_dir: Path) -> List[Path]:
    """A language's class folders, in name order: every folder in it except
    the ones above and hidden ones. [] if the folder doesn't exist."""
    lang_dir = Path(lang_dir)
    if not lang_dir.is_dir():
        return []
    return sorted(d for d in lang_dir.iterdir()
                  if d.is_dir() and d.name not in NOT_CLASS_FOLDERS
                  and not d.name.startswith("."))
