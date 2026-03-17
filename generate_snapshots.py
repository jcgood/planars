#!/usr/bin/env python3
"""Generate text snapshots of all analysis results for regression testing.

Run from the repo root:
    python generate_snapshots.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

from planars import ciscategorial as _cisc
from planars import subspanrepetition as _subspan
from planars import noninterruption as _nonint

SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"

_SUFFIX_RE = re.compile(r"_(filled?|full|test|blank)$", re.IGNORECASE)
_FILLED_RE = re.compile(r"_(fill(?:ed)?|full|test)\.tsv$", re.IGNORECASE)
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")

_CLASS_HANDLERS = [
    ("ciscategorial",    _cisc.derive_v_ciscategorial_fractures,  _cisc.format_result),
    ("subspanrepetition", _subspan.derive_subspanrepetition_spans, _subspan.format_result),
    ("noninterruption",  _nonint.derive_noninterruption_domains,  _nonint.format_result),
]

TASKS = [
    (tsv_path, derive_fn, fmt_fn)
    for class_name, derive_fn, fmt_fn in _CLASS_HANDLERS
    for lang_dir in sorted((ROOT / "coded_data").iterdir())
    if lang_dir.is_dir()
    for tsv_path in sorted((lang_dir / class_name).glob("*.tsv"))
    if (lang_dir / class_name).exists() and _FILLED_RE.search(tsv_path.name)
]


def snapshot_stem(tsv_path: Path) -> str:
    """Return snapshot filename stem: {lang_id}_{class_name}_{tsv_stem}."""
    # tsv_path is coded_data/{lang_id}/{class_name}/{construction}_filled.tsv
    class_name = tsv_path.parent.name
    lang_id = tsv_path.parent.parent.name
    return f"{lang_id}_{class_name}_{tsv_path.stem}"


def tsv_to_title(tsv_path: Path) -> str:
    stem = snapshot_stem(tsv_path)
    stem = _SUFFIX_RE.sub("", stem)
    stem = stem.replace("stan1293", "English")
    stem = _CAMEL_RE.sub("-", stem)
    stem = stem.replace("_", " ").lower()
    return stem.title()


def main() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for tsv_path, derive_fn, fmt_fn in TASKS:
        title = tsv_to_title(tsv_path)
        result = derive_fn(tsv_path, strict=False)
        body = fmt_fn(result)
        out_text = f"{title}\n{'=' * len(title)}\n\n{body}\n"
        out_path = SNAPSHOTS_DIR / (snapshot_stem(tsv_path) + ".txt")
        out_path.write_text(out_text, encoding="utf-8")
        print(f"Wrote: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
