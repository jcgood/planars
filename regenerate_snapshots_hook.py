#!/usr/bin/env python3
"""Pre-commit hook: when planars/ library code changes, regenerate the
snapshots and bump the package version.

Triggered automatically by pre-commit when any planars/*.py file is staged.
Regenerates all snapshots and stages the result so updated snapshots are
included in the same commit as the analysis change. Also raises the alpha
number in pyproject.toml's version (0.1.0aN -> 0.1.0aN+1) unless the commit
already changes it, and stages that too: Colab installs planars from GitHub,
so a library change needs a new version, and remembering to bump it by hand
was a fact kept only by memory (Phase 10 unit 7, 2026-10-12).

Not intended to be run directly — use generate_snapshots.py for manual
regeneration and check_snapshots.py for standalone checking.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_VERSION_LINE = re.compile(r'^version = "(\d+\.\d+\.\d+a)(\d+)"$', re.MULTILINE)


def bump_version(text: str) -> str:
    """pyproject.toml text with its alpha version number raised by one."""
    m = _VERSION_LINE.search(text)
    if not m:
        raise SystemExit("ERROR: pyproject.toml has no 'version = \"X.Y.ZaN\"' line to bump.")
    return text[:m.start()] + f'version = "{m.group(1)}{int(m.group(2)) + 1}"' + text[m.end():]


def _bump_version_unless_already_changed() -> None:
    def version_in(ref_spec: str) -> str:
        out = subprocess.run(["git", "show", ref_spec], capture_output=True, text=True, cwd=ROOT)
        m = _VERSION_LINE.search(out.stdout)
        return m.group(0) if m else ""
    if version_in(":pyproject.toml") != version_in("HEAD:pyproject.toml"):
        return  # this commit already sets a new version
    path = ROOT / "pyproject.toml"
    path.write_text(bump_version(path.read_text(encoding="utf-8")), encoding="utf-8")
    subprocess.run(["git", "add", "pyproject.toml"], cwd=ROOT)
    print(f"Version bumped: {_VERSION_LINE.search(path.read_text()).group(0)}")


def main() -> None:
    _bump_version_unless_already_changed()
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
