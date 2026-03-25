#!/usr/bin/env python3
"""Pre-commit hook: regenerate snapshots when analysis modules change.

Triggered automatically by pre-commit when any planars/*.py file is staged.
Regenerates all snapshots and stages the result so updated snapshots are
included in the same commit as the analysis change.

Not intended to be run directly — use generate_snapshots.py for manual
regeneration and check_snapshots.py for standalone checking.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    # Regenerate all snapshots.
    result = subprocess.run(
        [sys.executable, str(ROOT / "generate_snapshots.py")],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print("ERROR: generate_snapshots.py failed — aborting commit.")
        sys.exit(1)

    # Find modified snapshots (tracked files with unstaged changes).
    diff = subprocess.run(
        ["git", "diff", "--name-only", "tests/snapshots/"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    # Find new snapshots (untracked files in the snapshots dir).
    new_files = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "tests/snapshots/"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    changed = [l for l in diff.stdout.splitlines() if l]
    added = [l for l in new_files.stdout.splitlines() if l]
    all_changed = sorted(changed + added)

    if all_changed:
        subprocess.run(["git", "add", "tests/snapshots/"], cwd=ROOT)
        print(f"Snapshots regenerated and staged ({len(all_changed)} file(s)):")
        for f in all_changed:
            print(f"  {f}")
        print("Review with: git show HEAD:tests/snapshots/<file>  (after commit)")
    else:
        print("Snapshots unchanged.")


if __name__ == "__main__":
    main()
