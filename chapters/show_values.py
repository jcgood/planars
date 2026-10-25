"""``python -m chapters values --lang LANG [--version COMMIT]``.

Prints every named value chapters.data.chapter_data gives for a language
(one ``key<TAB>value`` per line, sorted), the size of each table, and what
is missing. For whoever writes or checks a chapter's templates: it shows
the names a sentence can cite. Writes nothing.
"""

from __future__ import annotations

import argparse
import sys

from chapters.data import ChapterDataError, chapter_data


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m chapters values", description=__doc__.split("\n\n")[1])
    parser.add_argument("--lang", required=True, help="Glottocode, e.g. stan1293.")
    parser.add_argument("--version", default=None,
                        help="A planars-data commit to read (default: coded_data/ as it is).")
    parser.add_argument("--prefix", default="",
                        help="Print only values whose name starts with this (e.g. stan1293.span.).")
    args = parser.parse_args(argv)
    try:
        chapter = chapter_data(args.lang, version=args.version)
    except ChapterDataError as e:
        sys.exit(str(e))
    version = chapter.version
    print(f"planars-data {version['planars_data_commit'][:12]} ({version['date']})"
          + (", with uncommitted changes for this language" if version["uncommitted_changes"] else ""))
    for key in sorted(chapter.values):
        if key.startswith(args.prefix):
            print(f"{key}\t{chapter.values[key]}")
    print("\nTables: " + ", ".join(f"{name} ({len(t)} rows)" for name, t in chapter.tables.items()))
    print("Analysis bundles used: " + (", ".join(chapter.bundles) or "none"))
    if chapter.missing:
        print("\nMissing:")
        for line in chapter.missing:
            print(f"  - {line}")


if __name__ == "__main__":
    main()
