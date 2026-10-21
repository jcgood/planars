"""The tooling's state files, kept in planars-data (Phase 10 unit 12, #271).

A command's record of its own work used to stay on the machine that ran it,
at the repo root and gitignored. The daily refresh runs on a GitHub machine
that is thrown away afterwards, so its pending changes never reached a
coordinator's ``apply-pending``, and its provenance log and snapshots were
lost every day. They now live in ``coded_data/.state/`` (hidden, like
``.test_fixtures/``, so nothing takes it for a language folder):

- ``PENDING_PATH``: destructive changes waiting for review. import-sheets
  writes it, apply-pending reads and rewrites it, the dispatcher warns when
  it is non-empty.
- ``PROVENANCE_LOG``: one line per tab or Drive file a command wrote (the
  Drive door, ``provenance.append_writes``). Append-only; planars-data's
  ``.gitattributes`` merges it with ``merge=union``, so two machines'
  lines never conflict.
- ``SNAPSHOT_DIR``: each tab as it was before ``drive_door.replacing``
  let its answers be replaced (one file per tab, the latest only).
- ``JOURNAL_PATH``: restructure-sheets' record of a run interrupted
  mid-class (``restructure_journal``).

This module is the one statement of where they are; every reader and writer
uses these names at call time (tests point them at a temporary folder,
``tests/conftest.py``). ``commit_changed`` commits and pushes whichever of
them changed, and the dispatcher calls it when every command ends, however
it ends, so nothing is left behind on the machine. ``behind_remote`` is the
``coded_data_up_to_date`` precondition: a command that acts on another
machine's state (apply-pending, restructure-sheets) refuses to run on a copy
of planars-data older than GitHub's.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"
STATE_DIR = CODED_DATA / ".state"

PENDING_PATH = STATE_DIR / "pending_changes.json"
PROVENANCE_LOG = STATE_DIR / "provenance_log.jsonl"
SNAPSHOT_DIR = STATE_DIR / "regen_snapshots"
JOURNAL_PATH = STATE_DIR / "restructure_journal.json"


def paths() -> List[Path]:
    """Every state file and folder, as currently set (tests move them)."""
    return [PENDING_PATH, PROVENANCE_LOG, SNAPSHOT_DIR, JOURNAL_PATH]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _repo_paths(repo: Path) -> List[str]:
    """The state paths inside ``repo``, relative to it. A path outside it
    (a test's temporary folder) is not this repository's to commit."""
    out = []
    for path in paths():
        try:
            out.append(str(path.resolve().relative_to(repo.resolve())))
        except ValueError:
            continue
    return out


def commit_changed(command: str, repo: Optional[Path] = None) -> bool:
    """Commit and push the state files that changed, if any. True if a
    commit was made.

    Only the state files are staged, never anything else in planars-data. A
    failed ``git add`` or ``git commit`` raises (a write that reached disk
    but not git leaves planars-data dirty, #248); a failed push is printed
    and not raised: the commit is safe locally, and the next push carries it.
    Does nothing when planars-data is not a git repository.
    """
    repo = repo or CODED_DATA
    if not (repo / ".git").exists():
        return False
    rel = _repo_paths(repo)
    if not rel:
        return False
    status = _git(repo, "status", "--porcelain", "--untracked-files=all", "--", *rel)
    if status.returncode != 0:
        return False
    # Only what git lists: a state file that never existed (no interrupted
    # restructure, say) would make `git add` fail.
    changed = [line[3:].strip().strip('"') for line in status.stdout.splitlines() if line.strip()]
    if not changed:
        return False
    for step in (["add", "-A", "--", *changed],
                 ["commit", "-m", f"state: after {command}", "--", *changed]):
        done = _git(repo, *step)
        if done.returncode != 0:
            raise RuntimeError(
                f"Could not commit the tooling's state files in planars-data "
                f"(git {step[0]}): {done.stderr.strip() or done.stdout.strip()}. "
                f"They are written but not committed; commit coded_data/.state/ "
                f"by hand and push.")
    push = _git(repo, "push")
    if push.returncode != 0:
        print(f"WARNING: committed coded_data/.state/ but could not push it: "
              f"{push.stderr.strip()}. Run: git -C coded_data push")
    return True


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
