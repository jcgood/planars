#!/usr/bin/env python3
"""Pre-commit hook: raise the code version when a commit changes code that
produces results.

Runs on every commit. If any staged file is under one of
``coding.versions.RESULT_CODE`` (the library, the analysis, the chapter
builder, the R chart package), it raises the alpha number in
pyproject.toml's version (0.1.0aN -> 0.1.0aN+1) unless the commit already
changes it, and stages that too. Every result records this version
(``versions.stamp``; Phase 10 unit 18, docs/result-stamp-design.md § 5), so
two results with the same version come from the same code; and Colab
installs planars from GitHub, so a library change needs a new version
(Phase 10 unit 7, 2026-10-12). Remembering to bump it by hand was a fact
kept only by memory.

Not intended to be run directly.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
_VERSION_LINE = re.compile(r'^version = "(\d+\.\d+\.\d+a)(\d+)"$', re.MULTILINE)


def bump_version(text: str) -> str:
    """pyproject.toml text with its alpha version number raised by one."""
    m = _VERSION_LINE.search(text)
    if not m:
        raise SystemExit("ERROR: pyproject.toml has no 'version = \"X.Y.ZaN\"' line to bump.")
    return text[:m.start()] + f'version = "{m.group(1)}{int(m.group(2)) + 1}"' + text[m.end():]


def changes_result_code(paths: Iterable[str]) -> bool:
    """Whether any of these repository paths is code that produces results."""
    from coding.versions import RESULT_CODE
    return any(Path(p).parts[:1] and Path(p).parts[0] in RESULT_CODE for p in paths)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT).stdout


def main() -> None:
    if not changes_result_code(_git("diff", "--cached", "--name-only").splitlines()):
        return

    def version_in(ref_spec: str) -> str:
        m = _VERSION_LINE.search(_git("show", ref_spec))
        return m.group(0) if m else ""
    if version_in(":pyproject.toml") != version_in("HEAD:pyproject.toml"):
        return  # this commit already sets a new version
    path = ROOT / "pyproject.toml"
    path.write_text(bump_version(path.read_text(encoding="utf-8")), encoding="utf-8")
    subprocess.run(["git", "add", "pyproject.toml"], cwd=ROOT)
    print(f"Version bumped: {_VERSION_LINE.search(path.read_text()).group(0)}")


if __name__ == "__main__":
    main()
