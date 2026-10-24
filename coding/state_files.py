"""Where the tooling's own files live in planars-data (Phase 10 units 12, 6b).

A command's record of its own work used to stay on the machine that ran it,
at the repo root and gitignored. The daily refresh runs on a GitHub machine
that is thrown away afterwards, so its records never reached a coordinator,
and its provenance log and snapshots were lost every day. They now live in
``coded_data/.state/`` (hidden, like ``.test_fixtures/``, so nothing takes it
for a language folder). (A ``pending_changes.json`` of destructive changes
from the planar and diagnostics Sheets was here too, read by apply-pending;
both went when those Sheets became read-only copies, unit 11b, 2026-10-24.)

- ``PROVENANCE_LOG``: one line per tab or Drive file a command wrote (the
  Drive door, ``provenance.append_writes``). Append-only; planars-data's
  ``.gitattributes`` merges it with ``merge=union``, so two machines'
  lines never conflict.
- ``SNAPSHOT_DIR``: each tab as it was before ``drive_door.replacing``
  let its answers be replaced (one file per tab, the latest only).
- ``JOURNAL_PATH``: restructure-sheets' record of a run interrupted
  mid-class (``restructure_journal``).
- ``NOTES_STATE_PATH``: what check-notes last saw in each notes Doc, and
  each annotator's open notes issue (at planars-data's top level until unit
  6b).
- ``COMMENTS_STATE_PATH``: what check-comments last saw in each Comments
  cell, and each language's open comments issue.
- ``RENUMBERING_PATH``: sync-planar's record, while a new planar's
  numbers are being carried into the class sheets, of the numbering each
  sheet's position cells already use, so a run that stops partway never
  renumbers a sheet twice (``sync_planar._renumber_class_sheets``).

and, at planars-data's top level, ``ID_FILE`` (``drive_config.json``): the
Drive IDs of the files the tooling made.

This module is the one statement of where they are; every reader uses these
names at call time (tests point them at a temporary folder,
``tests/conftest.py``). Every write goes through the local-file door
(``file_door.write_state`` and its kinds, ``file_door.STATE_KINDS``), which
commits and pushes what a command wrote when it ends. ``behind_remote`` is
the ``coded_data_up_to_date`` precondition: a command that acts on another
machine's state (restructure-sheets) refuses to run on a copy of planars-data
older than GitHub's.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
STATE_DIR = CODED_DATA / ".state"

PROVENANCE_LOG = STATE_DIR / "provenance_log.jsonl"
SNAPSHOT_DIR = STATE_DIR / "regen_snapshots"
JOURNAL_PATH = STATE_DIR / "restructure_journal.json"
NOTES_STATE_PATH = STATE_DIR / "notes_state.json"
COMMENTS_STATE_PATH = STATE_DIR / "comments_state.json"
RENUMBERING_PATH = STATE_DIR / "renumbering.json"
ID_FILE = CODED_DATA / "drive_config.json"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def behind_remote(repo: Optional[Path] = None) -> Optional[int]:
    """How many commits planars-data's branch is behind GitHub's (after a
    fetch). None when that can't be told: not a git repository, no upstream
    branch, or the fetch failed."""
    repo = repo or CODED_DATA
    if not (repo / ".git").exists():
        return None
    if _git(repo, "fetch", "--quiet").returncode != 0:
        return None
    count = _git(repo, "rev-list", "--count", "HEAD..@{u}")
    if count.returncode != 0:
        return None
    return int(count.stdout.strip() or 0)
