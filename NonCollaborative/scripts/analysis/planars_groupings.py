"""Named groupings of domain types used across charts, defined once.

Before this module, the three pooled "bundles" were written out separately in
laminar_analysis.py's __main__ block and in laminar_tree_counts.py (BUNDLES,
with its own copy of the colours). They are data, so they live in one place:
laminar_analysis.py, laminar_tree_counts.py and export_planarsviz_data.py all
import them from here.

BUNDLES: (name, domain types, colour, display label). A crude approximation
of a morphosyntax/phonology split, on purpose -- this project's diagnostic
classes don't map cleanly onto that binary (see the "Morphosyntax/phonology
divide hypothesis" in laminar_analysis.py's module docstring).

FILTERS: (filter id, domain types left out). Each is a fresh analysis of
every other observed domain type -- different spans, families and layer
numbers from the full analysis, not a filtered view of it. The exporter
writes one bundle subset per filter, and the planarsviz package draws the
no-tono variant of a chart from that subset.

GROUPINGS: which BUNDLES/FILTERS set a dataset uses, keyed by name and passed
to the exporter with --groupings. nyan1308 keeps "chichewa" (today's BUNDLES
and FILTERS, unchanged -- every importer of those two names is unaffected).
CCDB structures use "ccdb": one bundle, morphosyntactic + indeterminate set
against phonological on its own, no filters (plan section 2.4/6.2 -- CCDB's
own domain types don't support the morphosyntax/tonosegmental/length split
BUNDLES was built for). Its colour, #EE4C97, is the eighth member of the
same eight-colour qualitative palette CLASS_COLORS and BUNDLES already draw
from (BUNDLES reuses three of that palette's first five entries rather than
picking new ones); #6F99AD (the sixth) went to `indeterminate` itself. The
seventh, #FFDC91, was skipped as too pale for thin lines on white (Jeff,
2026-09-23), so #EE4C97 stays in the palette and distinct from every
domain-type and bundle colour already in use.

CLASS_ORDER: the order domain types are listed in, wherever a script lists
them one by one. Only types a dataset actually has are listed, then any type
not named here, alphabetically (`observed_groups()`), so a dataset with other
types needs nothing added here. The order is part of what the permutation
tests' numbers mean: they advance one random stream across the groups in
order.

observed_groups(): the per-type groups and the bundles one dataset is
analysed with -- the single place every script builds them, so a script run
on its own and the exporter's bundle get the same groups in the same order.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CLASS_ORDER: list[str] = ["morphosyntactic", "phonological", "tonosegmental", "intonational", "length"]

BUNDLES: list[tuple[str, list[str], str, str]] = [
    ("phonologylike", ["phonological", "intonational"], "#0072B5", "Phonology-like"),
    ("syntaxlike", ["morphosyntactic", "tonosegmental", "length"], "#BC3C29", "Syntax-like"),
    ("syntaxlike_notono", ["morphosyntactic", "length"], "#E18727", "Syntax-like (no Tono)"),
]

FILTERS: list[tuple[str, list[str]]] = [
    ("no_tono", ["tonosegmental"]),
]

GROUPINGS: dict[str, dict] = {
    "chichewa": {"bundles": BUNDLES, "filters": FILTERS},
    "ccdb": {
        "bundles": [
            ("morsyn_indet", ["morphosyntactic", "indeterminate"], "#EE4C97",
             "Morphosyntactic + indeterminate"),
        ],
        "filters": [],
    },
}


def observed_domain_types(domain_file: Path) -> set[str]:
    """The Domain_Type values a domains file's active (uncommented) rows have."""
    tests = pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")
    return set(tests["Domain_Type"].dropna().str.strip())


def observed_groups(domain_file: Path, bundles: list) -> tuple[list[str], list]:
    """(classes, bundles) for one dataset.

    classes: its domain types, in CLASS_ORDER, then any other type
    alphabetically. bundles: the entries of `bundles` (a GROUPINGS set's
    "bundles") with at least one type the data has. A group with no tests
    can't be analysed (load_spans() fails on an empty subset), so neither
    list names one.
    """
    observed = observed_domain_types(domain_file)
    classes = [c for c in CLASS_ORDER if c in observed] + sorted(observed - set(CLASS_ORDER))
    return classes, [b for b in bundles if set(b[1]) & observed]


def permutation_groups(domain_file: Path, bundles: list, pooled: bool) -> list[tuple[str, list[str] | None]]:
    """The (group name, domain types) list a permutation test runs over:
    with `pooled`, "all" (every type, None) first; then each class; then each
    bundle -- observed_groups()'s order."""
    classes, live_bundles = observed_groups(domain_file, bundles)
    return (([("all", None)] if pooled else [])
            + [(c, [c]) for c in classes]
            + [(name, list(types)) for name, types, _colour, _display in live_bundles])
