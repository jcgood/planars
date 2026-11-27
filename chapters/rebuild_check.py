"""``python -m chapters rebuild-check --release DIR --values FILE``.

The progress report's rebuild check (docs/zenodo-report-plan.md, item 6):
from a released dataset (an unpacked export-release folder, DIR) and this
software, work out every value a language's chapter cites
(chapters.data.release_data) and compare them with the values.tex the
report was built with (FILE, in the report's record). Prints each value
that differs, is missing or is new, and exits 1 if any does; exits 0 when
every value is rebuilt as released. Writes nothing.

It first checks the release itself (chapters.data.release_problems): every
file is the one release.json lists, and this software is the version the
release names (its code version and its schema files). Any problem is
printed and the check stops (exit 1), since a comparison made with other
files or other code proves nothing.

Run it with the software at the release's tag:

    pip install "git+https://github.com/jcgood/planars@v<version>"
    python -m chapters rebuild-check --release <dataset folder> --values <report>/stan1293/values.tex
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chapters import tex
from chapters.data import ChapterDataError, release_data, release_problems


def differences(released: dict, rebuilt: dict) -> list:
    """Plain-words lines for each value that differs between two
    {name: values.tex text}."""
    out = []
    for name in sorted(set(released) | set(rebuilt)):
        if name not in rebuilt:
            out.append(f"{name}: released {released[name]!r}, not rebuilt")
        elif name not in released:
            out.append(f"{name}: rebuilt {rebuilt[name]!r}, not in the released values.tex")
        elif released[name] != rebuilt[name]:
            out.append(f"{name}: released {released[name]!r}, rebuilt {rebuilt[name]!r}")
    return out


def rebuilt_values(release: Path) -> dict:
    """{name: values.tex text} worked out from the release."""
    chapter = release_data(release)
    return tex.read_values_tex(tex.values_tex(chapter.values, ""))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m chapters rebuild-check",
                                     description=__doc__.split("\n\n")[1])
    parser.add_argument("--release", required=True, type=Path, metavar="DIR",
                        help="the unpacked dataset folder (the one holding release.json)")
    parser.add_argument("--values", required=True, type=Path, metavar="FILE",
                        help="the language's values.tex from the report's record")
    args = parser.parse_args(argv)
    problems = release_problems(args.release)
    if problems:
        print(f"The release can't be checked ({len(problems)}):")
        for p in problems:
            print(f"  {p}")
        sys.exit(1)
    try:
        rebuilt = rebuilt_values(args.release)
    except ChapterDataError as e:
        sys.exit(str(e))
    released = tex.read_values_tex(args.values.read_text(encoding="utf-8"))
    lines = differences(released, rebuilt)
    if lines:
        print(f"{len(lines)} of {len(set(released) | set(rebuilt))} values are not rebuilt as released:")
        for line in lines:
            print(f"  {line}")
        sys.exit(1)
    print(f"All {len(released)} values rebuilt from the release are the ones released.")


if __name__ == "__main__":
    main()
