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
"""

BUNDLES: list[tuple[str, list[str], str, str]] = [
    ("phonologylike", ["phonological", "intonational"], "#0072B5", "Phonology-like"),
    ("syntaxlike", ["morphosyntactic", "tonosegmental", "length"], "#BC3C29", "Syntax-like"),
    ("syntaxlike_notono", ["morphosyntactic", "length"], "#E18727", "Syntax-like (no Tono)"),
]
