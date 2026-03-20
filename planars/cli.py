#!/usr/bin/env python3
"""Command-line entry point for planars analysis modules.

Usage:
    python -m planars <analysis> <tsv_file>

Where <analysis> is one of:
    ciscategorial
    subspanrepetition
    noninterruption
    stress
    aspiration
    nonpermutability
    free_occurrence
    biuniqueness
    repair
    segmental
    suprasegmental
    pausing
    proform
    play_language
    idiom

Examples:
    python -m planars ciscategorial coded_data/stan1293/ciscategorial/general_filled.tsv
    python -m planars stress coded_data/stan1293/stress/general_filled.tsv
"""
from __future__ import annotations

import sys
from pathlib import Path

from planars import ciscategorial as _cisc
from planars import subspanrepetition as _subspan
from planars import noninterruption as _nonint
from planars import stress as _stress
from planars import aspiration as _aspiration
from planars import nonpermutability as _nonperm
from planars import free_occurrence as _freeoc
from planars import biuniqueness as _biuniq
from planars import repair as _repair
from planars import segmental as _segmental
from planars import suprasegmental as _supra
from planars import pausing as _pausing
from planars import proform as _proform
from planars import play_language as _play
from planars import idiom as _idiom

_ANALYSES = {
    "ciscategorial":     (_cisc.derive_v_ciscategorial_fractures,  _cisc.format_result),
    "subspanrepetition": (_subspan.derive_subspanrepetition_spans, _subspan.format_result),
    "noninterruption":   (_nonint.derive_noninterruption_domains,  _nonint.format_result),
    "stress":            (_stress.derive_stress_domains,           _stress.format_result),
    "aspiration":        (_aspiration.derive_aspiration_domains,   _aspiration.format_result),
    "nonpermutability":  (_nonperm.derive,   _nonperm.format_result),
    "free_occurrence":   (_freeoc.derive,    _freeoc.format_result),
    "biuniqueness":      (_biuniq.derive,    _biuniq.format_result),
    "repair":            (_repair.derive,    _repair.format_result),
    "segmental":         (_segmental.derive, _segmental.format_result),
    "suprasegmental":    (_supra.derive,     _supra.format_result),
    "pausing":           (_pausing.derive,   _pausing.format_result),
    "proform":           (_proform.derive,   _proform.format_result),
    "play_language":     (_play.derive,      _play.format_result),
    "idiom":             (_idiom.derive,     _idiom.format_result),
}


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and print formatted analysis results to stdout.

    Args:
        argv: argument list to parse; defaults to sys.argv[1:] when None.

    Exits with status 1 if the analysis name is unrecognised or arguments are missing.
    """
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
