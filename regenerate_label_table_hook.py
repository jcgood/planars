#!/usr/bin/env python3
"""Pre-commit hook: when schemas/issue_labels.yaml changes, regenerate the
Labels table in CLAUDE.md and stage it, so the table never needs editing by
hand (Phase 10 unit 10, issue #271).

tests/test_issues.py also fails if the table is out of date, which catches a
commit made on a machine without the hook installed.

Not intended to be run directly — use `python -m coding issue --write-label-table`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    result = subprocess.run([sys.executable, "-m", "coding", "issue", "--write-label-table"],
                            cwd=ROOT)
    if result.returncode != 0:
        print("ERROR: could not regenerate CLAUDE.md's label table — aborting commit.")
        sys.exit(1)
    subprocess.run(["git", "add", "CLAUDE.md"], cwd=ROOT)


if __name__ == "__main__":
    main()
