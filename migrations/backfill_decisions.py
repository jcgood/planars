"""One-time migration: record the decisions of issues closed before the
decision rule began, and relabel the tooling issues among them.

Motivation: Phase 10 unit 16e (docs/plain-record-design.md § 4, § 7 Q4).
Every issue closed under `diagnostics` or `linguistics` must have a line in a
decision log, but the rule (`coding.decisions.CHECK_FROM`) started on
2026-11-01. This records one line for each of the 38 such issues closed before
then that settled something or moved to another thread
(`decision_backfill.tsv`, the `record-decision --batch` format), and
relabels the 8 that were tooling issues (`RELABEL`). Drafted 2026-10-31 by
Jeff's Claude from each thread; Adam checks the lines that name him or
concern English on #332.

Run: after Jeff's and Adam's approval (#332). Then move `CHECK_FROM` back
so the daily check covers every closed issue.

Usage:
    python migrations/backfill_decisions.py           # dry run
    python migrations/backfill_decisions.py --apply   # record and relabel

Post-run checks:
    python -m coding integrity-check     # its DECISIONS section lists no issue
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coding import decisions, issues  # noqa: E402

BATCH = Path(__file__).with_name("decision_backfill.tsv")

# (issue, label to remove, label to add or "", why)
RELABEL = [
    (201, "diagnostics", "", "sheet feature (planar reference tab); already has enhancement"),
    (204, "diagnostics", "enhancement", "tooling: carrying planar renames into pair sheets"),
    (266, "diagnostics", "bug", "filed by the tooling for synth0001; duplicate of #267"),
    (267, "diagnostics", "bug", "synth0001 generator noise, fixed in the generator"),
    (269, "diagnostics", "bug", "issue filing had no duplicate check"),
    (286, "diagnostics", "bug", "synth0001 test artifact (same data as #285)"),
    (287, "diagnostics", "bug", "synth0001 test artifact (same data as #285)"),
    (288, "diagnostics", "bug", "synth0001 generator artifact"),
]


def main(apply: bool) -> None:
    decisions._batch(BATCH, apply)
    for number, remove, add, why in RELABEL:
        change = f"#{number}: remove {remove}" + (f", add {add}" if add else "") + f" ({why})"
        if apply:
            issues.relabel(number, [add] if add else [], [remove])
            print(f"Relabelled {change}")
        else:
            print(f"Would relabel {change}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
