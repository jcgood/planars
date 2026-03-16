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
sys.path.insert(0, str(ROOT / "02_ciscategorial_output"))
sys.path.insert(0, str(ROOT / "03_subspanrepetition_output"))
sys.path.insert(0, str(ROOT / "04_noninterruption"))

import ciscategorial as _cisc
import subspanrepetition as _subspan
import noninterruption as _nonint

SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"

_SUFFIX_RE = re.compile(r"_(filled?|full|test|blank)$", re.IGNORECASE)
_FILLED_RE = re.compile(r"_(fill(?:ed)?|full|test)\.tsv$", re.IGNORECASE)
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")

_FOLDER_MAP = [
    (ROOT / "02_ciscategorial_output", _cisc.format_result, _cisc.derive_v_ciscategorial_fractures),
    (ROOT / "03_subspanrepetition_output", _subspan.format_result, _subspan.derive_subspanrepetition_spans),
    (ROOT / "04_noninterruption", _nonint.format_result, _nonint.derive_noninterruption_domains),
]

TASKS = [
    (tsv_path, fmt_fn, derive_fn)
    for folder, fmt_fn, derive_fn in _FOLDER_MAP
    for tsv_path in sorted(folder.glob("*.tsv"))
    if _FILLED_RE.search(tsv_path.name)
]


def tsv_to_title(tsv_filename: str) -> str:
    stem = Path(tsv_filename).stem
    stem = _SUFFIX_RE.sub("", stem)
    stem = stem.replace("stan1293", "English")
    stem = _CAMEL_RE.sub("-", stem)
    stem = stem.replace("_", " ").lower()
    return stem.title()


def main() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for tsv_path, fmt_fn, derive_fn in TASKS:
        title = tsv_to_title(tsv_path.name)
        result = derive_fn(tsv_path.name)
        body = fmt_fn(result)
        out_text = f"{title}\n{'=' * len(title)}\n\n{body}\n"
        out_path = SNAPSHOTS_DIR / (tsv_path.stem + ".txt")
        out_path.write_text(out_text, encoding="utf-8")
        print(f"Wrote: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
