#!/usr/bin/env python3
"""Compare current analysis output against committed snapshots.

Run from the repo root:
    python check_snapshots.py

Exits with code 0 if all snapshots match, 1 if any differ.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

from generate_snapshots import TASKS, SNAPSHOTS_DIR, tsv_to_title, snapshot_stem


def main() -> None:
    failures: list[str] = []

    for tsv_path, derive_fn, fmt_fn in TASKS:
        out_path = SNAPSHOTS_DIR / (snapshot_stem(tsv_path) + ".txt")

        if not out_path.exists():
            print(f"MISSING  {out_path.relative_to(ROOT)}")
            failures.append(tsv_path.name)
            continue

        title = tsv_to_title(tsv_path)
        body = fmt_fn(derive_fn(tsv_path, strict=False))
        current = f"{title}\n{'=' * len(title)}\n\n{body}\n"
        committed = out_path.read_text(encoding="utf-8")

        if current == committed:
            print(f"PASS     {out_path.relative_to(ROOT)}")
        else:
            print(f"FAIL     {out_path.relative_to(ROOT)}")
            current_lines = current.splitlines()
            committed_lines = committed.splitlines()
            for i, (a, b) in enumerate(zip(committed_lines, current_lines), 1):
                if a != b:
                    print(f"  line {i}:")
                    print(f"    expected: {a!r}")
                    print(f"    got:      {b!r}")
            if len(current_lines) != len(committed_lines):
                print(f"  line count: expected {len(committed_lines)}, got {len(current_lines)}")
            failures.append(tsv_path.name)

    if failures:
        print(f"\n{len(failures)} snapshot(s) failed.")
        sys.exit(1)
    else:
        print(f"\nAll {len(TASKS)} snapshots match.")


if __name__ == "__main__":
    main()
