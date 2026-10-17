#!/usr/bin/env python3
"""Command-line entry point for planars analysis modules.

Usage:
    python -m planars <analysis> <tsv_file>

Where <analysis> is any class in schemas/diagnostic_classes.yaml whose module
in planars/ has ``derive`` and ``format_result`` (run with no arguments for
the list). For biuniqueness_deviations, give the class's morphs.tsv.

Examples:
    python -m planars ciscategorial coded_data/stan1293/ciscategorial/general.tsv
    python -m planars metrical coded_data/stan1293/metrical/stress_domain.tsv
"""
from __future__ import annotations

import importlib
import sys
from importlib.resources import files as _res_files
from pathlib import Path

import yaml


def _analyses() -> dict:
    """{class_name: (derive, format_result)} for every class in the schema
    whose module has both. Derived, so it cannot fall behind (hidden-facts
    R-1: the typed list it replaced was missing four modules and named three
    retired ones whose import raises, which broke every invocation)."""
    text = _res_files("schemas").joinpath("diagnostic_classes.yaml").read_text(encoding="utf-8")
    found = {}
    for cls in (yaml.safe_load(text) or {}).get("classes", []):
        try:
            mod = importlib.import_module(f"planars.{cls['name']}")
        except ModuleNotFoundError:
            continue  # a class with no module yet
        if hasattr(mod, "derive") and hasattr(mod, "format_result"):
            found[cls["name"]] = (mod.derive, mod.format_result)
    return found


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and print formatted analysis results to stdout.

    Args:
        argv: argument list to parse; defaults to sys.argv[1:] when None.

    Exits with status 1 if the analysis name is unrecognised or arguments are missing.
    """
    args = argv if argv is not None else sys.argv[1:]
    analyses = _analyses()

    if len(args) != 2 or args[0] not in analyses:
        print("Usage: python -m planars <analysis> <tsv_file>", file=sys.stderr)
        print(f"Analyses: {', '.join(analyses)}", file=sys.stderr)
        sys.exit(1)

    analysis, tsv_file = args
    derive_fn, fmt_fn = analyses[analysis]
    print(fmt_fn(derive_fn(Path(tsv_file).resolve())))


if __name__ == "__main__":
    main()
