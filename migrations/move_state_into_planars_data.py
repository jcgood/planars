"""One-time migration: the tooling's state files, repo root → planars-data.

What it does: moves whichever of these a machine still has at the planars repo
root into ``coded_data/.state/`` (``coding/state_files.py``), then commits and
pushes them there:

    pending_changes.json      → .state/pending_changes.json
    provenance_log.jsonl      → .state/provenance_log.jsonl   (lines appended
                                 to any already there, none repeated)
    regen_snapshots/*.json    → .state/regen_snapshots/        (if both exist,
                                 the one saved later is kept)
    restructure_journal.json  → .state/restructure_journal.json

A pending-changes file or journal already in planars-data that differs from
this machine's stops the migration for that file: both may hold work, so a
coordinator merges them by hand.

Motivation: Phase 10 unit 12 (#271). These files stayed on the machine that
ran the command, so the daily refresh's (on GitHub's machine) were lost each
day, and its pending changes never reached a coordinator's apply-pending.
Run: 2026-10-20 on Jeff's machine, with the unit 12 commit. Any other
machine that has run the tooling (Adam's) runs it once too; until then its
old files sit untracked at the repo root, which `git status` shows.

Usage:
    python migrations/move_state_into_planars_data.py           # dry run
    python migrations/move_state_into_planars_data.py --apply   # move, commit, push

Post-run checks:
    git status                       # nothing left at the repo root
    git -C coded_data log -1 --stat  # the moved files
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coding import state_files  # noqa: E402

OLD_PENDING = ROOT / "pending_changes.json"
OLD_LOG = ROOT / "provenance_log.jsonl"
OLD_SNAPSHOTS = ROOT / "regen_snapshots"
OLD_JOURNAL = ROOT / "restructure_journal.json"


def _saved_at(path: Path) -> str:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("saved_at", "")
    except (ValueError, OSError):
        return ""


def _move_whole(old: Path, new: Path, apply: bool) -> bool:
    """Move a file that must not be merged. False if it must be merged by hand."""
    if not old.exists():
        return True
    if new.exists() and new.read_text(encoding="utf-8") != old.read_text(encoding="utf-8"):
        print(f"STOPPED: {new} already exists and differs from {old}. Both may "
              f"hold work: merge them by hand, delete {old}, and re-run.")
        return False
    print(f"  {old.name} → {new.relative_to(ROOT)}")
    if apply:
        new.parent.mkdir(parents=True, exist_ok=True)
        if new.exists():
            old.unlink()
        else:
            shutil.move(str(old), str(new))
    return True


def _move_log(apply: bool) -> None:
    if not OLD_LOG.exists():
        return
    new = state_files.PROVENANCE_LOG
    have = set(new.read_text(encoding="utf-8").splitlines()) if new.exists() else set()
    lines = [l for l in OLD_LOG.read_text(encoding="utf-8").splitlines() if l and l not in have]
    print(f"  {OLD_LOG.name}: {len(lines)} line(s) → {new.relative_to(ROOT)}")
    if apply:
        new.parent.mkdir(parents=True, exist_ok=True)
        with open(new, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
        OLD_LOG.unlink()


def _move_snapshots(apply: bool) -> None:
    if not OLD_SNAPSHOTS.exists():
        return
    for old in sorted(OLD_SNAPSHOTS.glob("*.json")):
        new = state_files.SNAPSHOT_DIR / old.name
        keep_old = not new.exists() or _saved_at(old) > _saved_at(new)
        print(f"  regen_snapshots/{old.name} → {new.relative_to(ROOT)}"
              + ("" if keep_old else " (the one already there is newer; kept)"))
        if apply:
            new.parent.mkdir(parents=True, exist_ok=True)
            if keep_old:
                shutil.move(str(old), str(new))
            else:
                old.unlink()
    if apply and not any(OLD_SNAPSHOTS.iterdir()):
        OLD_SNAPSHOTS.rmdir()


def main() -> None:
    apply = "--apply" in sys.argv
    print(f"Moving the state files into {state_files.STATE_DIR.relative_to(ROOT)}/"
          f" ({'apply' if apply else 'dry run'}):")
    ok = _move_whole(OLD_PENDING, state_files.PENDING_PATH, apply)
    ok = _move_whole(OLD_JOURNAL, state_files.JOURNAL_PATH, apply) and ok
    _move_log(apply)
    _move_snapshots(apply)
    if not apply:
        print("\nDry run: nothing moved. Re-run with --apply.")
        return
    if _commit_state_folder():
        print("\nCommitted and pushed to planars-data.")
    if not ok:
        raise SystemExit(1)


def _commit_state_folder() -> bool:
    """Commit and push .state/ in planars-data, and nothing else. (The
    commands commit what they write through the local-file door; this
    migration moves files outside it.)"""
    repo = state_files.CODED_DATA
    rel = str(state_files.STATE_DIR.relative_to(repo))

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)

    if not git("status", "--porcelain", "--", rel).stdout.strip():
        return False
    for step in (["add", "-A", "--", rel],
                 ["commit", "-m", "state: migration move_state_into_planars_data", "--", rel]):
        done = git(*step)
        if done.returncode != 0:
            raise SystemExit(f"git {step[0]} failed in planars-data: {done.stderr.strip()}. "
                             f"Commit {rel}/ there by hand and push.")
    if git("push").returncode != 0:
        print("WARNING: committed but could not push. Run: git -C coded_data push")
    return True


if __name__ == "__main__":
    main()
