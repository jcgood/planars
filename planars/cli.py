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

from planars import ciscategorial as _cisc
from planars import subspanrepetition as _subspan
from planars import noninterruption as _nonint

_ANALYSES = {
    "ciscategorial":    (_cisc.derive_v_ciscategorial_fractures,  _cisc.format_result),
    "subspanrepetition": (_subspan.derive_subspanrepetition_spans, _subspan.format_result),
    "noninterruption":  (_nonint.derive_noninterruption_domains,  _nonint.format_result),
}


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]

    if len(args) != 2 or args[0] not in _ANALYSES:
        print("Usage: python -m planars <analysis> <tsv_file>", file=sys.stderr)
        print(f"Analyses: {', '.join(_ANALYSES)}", file=sys.stderr)
        sys.exit(1)

    analysis, tsv_file = args
    derive_fn, fmt_fn = _ANALYSES[analysis]
    print(fmt_fn(derive_fn(Path(tsv_file).resolve())))


if __name__ == "__main__":
    main()
