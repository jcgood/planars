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
BUNDLES was built for). Its colour, #FFDC91, is the seventh member of the
same eight-colour qualitative palette CLASS_COLORS and BUNDLES already draw
from (BUNDLES reuses three of that palette's first five entries rather than
picking new ones); #6F99AD (the sixth) went to `indeterminate` itself, so
#FFDC91 is the next unused member and stays visually distinct from every
domain-type and bundle colour already in use.
"""

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
            ("morsyn_indet", ["morphosyntactic", "indeterminate"], "#FFDC91",
             "Morphosyntactic + indeterminate"),
        ],
        "filters": [],
    },
}
