"""One-time migration: start the record of changes to the sources.

What it does:

1. every ``coded_data/{lang}/changes.tsv`` whose header is the seven columns
   before unit 17 gets the five new ones (``file_door.SOURCE_COLUMNS``:
   change, layer, answers broken, spans moved, fingerprint), every existing
   line's cells left empty;
2. each language's sources (its planar and diagnostics file) get one
   ``baseline`` line with the file's fingerprint;
3. ``schemas/changes.tsv`` is made, with one ``baseline`` line per logged
   schema file (``source_log.SCHEMA_SOURCES``).

A source that already has a fingerprinted line is left alone, so a second
run does nothing.

Why: Phase 10 unit 17 (docs/change-log-design.md § 3, § 6.2): every change to
a source is logged from now on, and each stream's version is counted from
its baseline (Jeff, 2026-10-31: start every stream today; history before it
stays in git). The local-file door refuses to append to a log whose header
is not ``file_door.CHANGE_LOG_COLUMNS``, so this runs before the code that
writes the columns reaches the daily refresh.

Run: 2026-10-31, with unit 17 step 1.

Usage:
    python migrations/start_source_logs.py           # dry run
    python migrations/start_source_logs.py --apply   # rewrite the logs

Then commit and push the logs in coded_data/, and schemas/changes.tsv here.

Post-run checks:
    python -m coding integrity-check --check-changes
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coding import file_door, source_log  # noqa: E402

OLD = file_door.CHANGE_LOG_COLUMNS[:7]
BY = "migration start_source_logs"
WHY = "the record of changes to this file starts here (unit 17)"


def _widen(log: Path, apply: bool) -> None:
    with open(log, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    header = tuple(rows[0]) if rows else ()
    if header == file_door.CHANGE_LOG_COLUMNS:
        print(f"{log.parent.name}: already has the columns")
        return
    if header != OLD:
        sys.exit(f"{log}: unexpected header {list(header)}; nothing changed.")
    out = io.StringIO()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(file_door.CHANGE_LOG_COLUMNS)
    for row in rows[1:]:
        writer.writerow(row + [""] * (len(file_door.CHANGE_LOG_COLUMNS) - len(row)))
    print(f"{log.parent.name}: {'added' if apply else 'would add'} the five columns "
          f"({len(rows) - 1} lines)")
    if apply:
        with open(log, "w", encoding="utf-8", newline="") as f:
            f.write(out.getvalue())


def _baseline(source: source_log.Source) -> list:
    return source_log.line(source, what="baseline", by=BY, why=WHY,
                           change=file_door.BASELINE, layer="",
                           mark=file_door.fingerprint(source.path.read_bytes()))


def main(apply: bool) -> None:
    for lang_id in file_door.language_ids():
        log = file_door.change_log(lang_id)
        if log.exists():
            _widen(log, apply)
        marked = source_log.last_fingerprints(lang_id)
        rows = [_baseline(s) for s in source_log.language_sources(lang_id) if s.name not in marked]
        for r in rows:
            print(f"{lang_id}: {'adding' if apply else 'would add'} baseline for {r[1]}")
        if apply and rows:
            new = not log.exists()
            with open(log, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter="\t", lineterminator="\n")
                if new:
                    writer.writerow(file_door.CHANGE_LOG_COLUMNS)
                writer.writerows(rows)
    marked = source_log.last_fingerprints(source_log.SCHEMAS)
    rows = [_baseline(s) for s in source_log.sources([source_log.SCHEMAS]) if s.name not in marked]
    for r in rows:
        print(f"schemas: {'adding' if apply else 'would add'} baseline for {r[1]}")
    if apply and rows:
        source_log.append_project_lines(rows)
    if not apply:
        print("Dry run. Run with --apply to write.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
