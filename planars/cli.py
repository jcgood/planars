#!/usr/bin/env python3
"""Command-line entry point for planars analysis modules.

Usage:
    python -m planars <analysis> <tsv_file>

Where <analysis> is one of:
    ciscategorial
    subspanrepetition
    noninterruption

Examples:
    python -m planars ciscategorial 02_ciscategorial_output/ciscategorial_stan1293_general_filled.tsv
    python -m planars noninterruption 04_noninterruption/noninterruption_stan1293_general_fill.tsv
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "02_ciscategorial_output"))
sys.path.insert(0, str(ROOT / "03_subspanrepetition_output"))
sys.path.insert(0, str(ROOT / "04_noninterruption"))

import ciscategorial as _cisc
import subspanrepetition as _subspan
import noninterruption as _nonint

_ANALYSES = {
    "ciscategorial": (_cisc, _cisc.derive_v_ciscategorial_fractures, _cisc.format_result),
    "subspanrepetition": (_subspan, _subspan.derive_subspanrepetition_spans, _subspan.format_result),
    "noninterruption": (_nonint, _nonint.derive_noninterruption_domains, _nonint.format_result),
}


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]

    if len(args) != 2 or args[0] not in _ANALYSES:
        print(f"Usage: python -m planars <analysis> <tsv_file>", file=sys.stderr)
        print(f"Analyses: {', '.join(_ANALYSES)}", file=sys.stderr)
        sys.exit(1)

    analysis, tsv_file = args
    module, derive_fn, fmt_fn = _ANALYSES[analysis]

    tsv_path = Path(tsv_file).resolve()
    module.DATA_DIR = str(tsv_path.parent)
    try:
        print(fmt_fn(derive_fn(tsv_path.name)))
    finally:
        module.DATA_DIR = ""


if __name__ == "__main__":
    main()
