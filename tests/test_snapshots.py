"""Snapshot regression tests for all analysis modules.

Compares current analysis output against committed .txt files in
tests/snapshots/. Covers every filled TSV in coded_data/ for every
planars module that exposes `derive` and `format_result`.

If a test fails due to an intentional change (bug fix, logic update,
new data), regenerate the baseline and review the diff before committing:

    python generate_snapshots.py
    git diff tests/snapshots/
"""
from __future__ import annotations

from pathlib import Path

import pytest

from generate_snapshots import TASKS, SNAPSHOTS_DIR, snapshot_stem, tsv_to_title

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "tsv_path,derive_fn,fmt_fn",
    TASKS,
    ids=[snapshot_stem(t[0]) for t in TASKS],
)
def test_snapshot(tsv_path, derive_fn, fmt_fn):
    out_path = SNAPSHOTS_DIR / (snapshot_stem(tsv_path) + ".txt")

    if not out_path.exists():
        pytest.fail(
            f"Snapshot missing: {out_path.relative_to(ROOT)}\n"
            f"Run: python generate_snapshots.py"
        )

    title     = tsv_to_title(tsv_path)
    body      = fmt_fn(derive_fn(tsv_path, strict=False))
    current   = f"{title}\n{'=' * len(title)}\n\n{body}\n"
    committed = out_path.read_text(encoding="utf-8")

    assert current == committed, (
        f"Output differs from snapshot: {out_path.name}\n"
        f"If this change is intentional, run: python generate_snapshots.py"
    )
