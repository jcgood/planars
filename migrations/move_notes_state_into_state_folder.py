"""One-time migration: planars-data's notes_state.json → .state/notes_state.json.

What it does: moves check-notes' record of what it last saw in each notes
Doc (and each annotator's open notes issue) from planars-data's top level
into ``.state/`` beside the other state files (``coding/state_files.py``,
``NOTES_STATE_PATH``), with ``git mv``, then commits and pushes.

Motivation: Phase 10 unit 6b (#271). The state files go through the
local-file door and all live in ``.state/``; this one predated the folder.
Run: 2026-10-21 on Jeff's machine, with the unit 6b commit. It is a change to
planars-data itself, so other machines get it by pulling; nobody else runs it.

Usage:
    python migrations/move_notes_state_into_state_folder.py           # dry run
    python migrations/move_notes_state_into_state_folder.py --apply   # move, commit, push

Post-run checks:
    git -C coded_data log -1 --stat   # the rename
    python -m coding check-notes      # dry run: reads the moved file, finds no new notes
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coding import state_files  # noqa: E402

OLD = state_files.CODED_DATA / "notes_state.json"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(state_files.CODED_DATA), *args],
                          capture_output=True, text=True)


def main() -> None:
    apply = "--apply" in sys.argv
    new = state_files.NOTES_STATE_PATH
    if not OLD.exists():
        print(f"Nothing to move: {OLD} does not exist.")
        return
    if new.exists():
        raise SystemExit(f"STOPPED: both {OLD} and {new} exist. Keep the newer by hand.")
    old_rel = str(OLD.relative_to(state_files.CODED_DATA))
    new_rel = str(new.relative_to(state_files.CODED_DATA))
    print(f"  {old_rel} → {new_rel}")
    if not apply:
        print("\nDry run: nothing moved. Re-run with --apply.")
        return
    new.parent.mkdir(parents=True, exist_ok=True)
    for step in (["mv", old_rel, new_rel],
                 ["commit", "-m", "state: move notes_state.json into .state/ (unit 6b)",
                  "--", old_rel, new_rel]):
        done = _git(*step)
        if done.returncode != 0:
            raise SystemExit(f"git {step[0]} failed: {done.stderr.strip()}")
    if _git("push").returncode != 0:
        print("WARNING: committed but could not push. Run: git -C coded_data push")
        return
    print("\nMoved, committed and pushed to planars-data.")


if __name__ == "__main__":
    main()
