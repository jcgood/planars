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
domain-type and bundle colour already in use. A language annotated through
planars uses "planars_types" or "planars_classes", built from the schema's
domain types by _planars_groupings() (decision 4 of
docs/laminar-analysis-plan.md); laminar/planars_language.py writes its
domains files to match. Those two also carry "styles": each domain type's
(or class's) colours, display order and forest id, which the exporter uses
in place of its own table for the other datasets' types
(export_planarsviz_data.grouping_style()).

CLASS_COLORS: the domain types' colours, the one place they are written
down (moved here from laminar_tree_counts.py so the planars groupings can
use them without a circular import).

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

# Exact pooled-plot colours of the domain types, the one place they are
# written down. Read by class_fragmentation_test.py and by
# export_planarsviz_data.py's DOMAIN_TYPE_STYLE, which is where R gets them.
# `indeterminate` is CCDB's third domain type (absent from nyan1308); it is
# not in CLASS_ORDER, so it never displaces the five nyan1308 classes --
# it only supplies a colour for datasets (CCDB's) that observe it.
CLASS_COLORS: dict[str, str] = {
    "morphosyntactic": "#BC3C29",
    "tonosegmental": "#0072B5",
    "length": "#E18727",
    "phonological": "#20845E",
    "intonational": "#7876B1",
    "indeterminate": "#6F99AD",
}

BUNDLES: list[tuple[str, list[str], str, str]] = [
    ("phonologylike", ["phonological", "intonational"], "#0072B5", "Phonology-like"),
    ("syntaxlike", ["morphosyntactic", "tonosegmental", "length"], "#BC3C29", "Syntax-like"),
    ("syntaxlike_notono", ["morphosyntactic", "length"], "#E18727", "Syntax-like (no Tono)"),
]

FILTERS: list[tuple[str, list[str]]] = [
    ("no_tono", ["tonosegmental"]),
]

_MORSYN_INDET = ("morsyn_indet", ["morphosyntactic", "indeterminate"], "#EE4C97",
                 "Morphosyntactic + indeterminate")

# Colours for the planars groupings' bundles that are not a domain type of
# their own (a phonological subtype, all phonological classes together).
# Provisional: English's charts are first drawn in Phase 4 of
# docs/laminar-analysis-plan.md, which settles them.
_SUBTYPE_COLOURS = {"segmental": "#0072B5", "prosodic": "#7876B1", "tonal": "#E18727"}
_PHONOLOGICAL_ALL_COLOUR = "#20845E"


# Second colour of each planars type, for the span-frequency chart (Paul
# Tol's "bright" palette, as export_planarsviz_data._DOMAIN_TYPE_ORDERS
# gives the other datasets' types).
_TYPE_ALT_COLOURS = {"morphosyntactic": "#EE6677", "indeterminate": "#66CCEE",
                     "phonological": "#4477AA", "segmental": "#228833",
                     "prosodic": "#CCBB44", "tonal": "#AA3377"}

# One colour per class for the planars_classes grouping, fixed per class (not
# per language) so a class looks the same in every language's charts. Every
# class in the schema must be here: a new class fails until it gets one.
# Provisional (Phase 4, 2026-10-24): the strongest colours (Okabe-Ito, then
# Paul Tol's "muted") go to the classes English has data for.
_CLASS_COLOURS = {
    "ciscategorial":           "#D55E00",
    "subspanrepetition":       "#0072B2",
    "noninterruption":         "#009E73",
    "nonpermutability":        "#CC79A7",
    "coreference":             "#E69F00",
    "free_occurrence":         "#56B4E9",
    "proform":                 "#882255",
    "idiom":                   "#999933",
    "biuniqueness_deviations": "#332288",
    "repair":                  "#DDCC77",
    "metrical":                "#117733",
    "phrasal_accent":          "#44AA99",
    "segmental":               "#AA4499",
    "tonal":                   "#88CCEE",
    "tonosegmental":           "#CC6677",
    "intonational":            "#6699CC",
    "pausing":                 "#997700",
    "play_language":           "#000000",
}

# The short id each planars type's forest is named by (forest ids are file
# names; a class's own name is its id).
_TYPE_SHORT = {"morphosyntactic": "morsyn", "indeterminate": "indet", "phonological": "phon"}


def _style_rows(entries: list[tuple[str, str, str, str]]) -> list[dict]:
    """Style rows (export_planarsviz_data's domain_types.tsv columns, plus
    the forest id `short`) from (domain_type, short, colour, alt_colour) in
    display order."""
    return [{"domain_type": dt, "short": short, "colour": colour, "alt_colour": alt,
             "sort_order": i, "legend_order": i, "facet_order": i, "colour_priority": i}
            for i, (dt, short, colour, alt) in enumerate(entries, start=1)]


def planars_domain_type(domain_type: str, subtype: str | None) -> str:
    """The Domain_Type a planars class's spans carry in the `planars_types`
    grouping: its domain type, joined to its subtype when it has one
    (``phonological-prosodic``), so each subtype is a group of its own."""
    return f"{domain_type}-{subtype}" if subtype else domain_type


def _planars_groupings() -> dict[str, dict]:
    """The two groupings for a language annotated through planars
    (docs/laminar-analysis-plan.md decision 4), built from each class's
    domain_type and domain_subtype in schemas/diagnostic_classes.yaml:

    - planars_types: each span's Domain_Type is its class's type-subtype
      (planars_domain_type()); bundles: every phonological type together,
      and the CCDB-style morphosyntactic + indeterminate.
    - planars_classes: each span's Domain_Type is its class name; bundles:
      the classes of each domain type, of each subtype, and the CCDB-style
      bundle of morphosyntactic and indeterminate classes.

    observed_groups() keeps only the bundles a dataset has data for, so a
    class with no spans yet costs nothing here.
    """
    from planars.schema_values import class_domain_types

    types = class_domain_types()
    labels = {planars_domain_type(t, s) for t, s in types.values()}
    phonological = sorted(l for l in labels if l.split("-")[0] == "phonological")
    by_type: dict[str, list[str]] = {}
    by_subtype: dict[str, list[str]] = {}
    for name, (domain_type, subtype) in types.items():
        by_type.setdefault(domain_type, []).append(name)
        if subtype:
            by_subtype.setdefault(subtype, []).append(name)
    for what, missing, table in (
            ("domain subtype", set(by_subtype) - set(_SUBTYPE_COLOURS), "_SUBTYPE_COLOURS"),
            ("domain type", set(by_type) - set(CLASS_COLORS), "CLASS_COLORS"),
            ("domain type", set(by_type) - set(_TYPE_SHORT), "_TYPE_SHORT"),
            ("class", set(types) - set(_CLASS_COLOURS), "_CLASS_COLOURS")):
        if missing:
            raise KeyError(f"No entry for {what}(s) {sorted(missing)}: add to planars_groupings.{table}.")

    type_entries = []
    for label in dict.fromkeys(planars_domain_type(t, s) for t, s in types.values()):
        domain_type, _, subtype = label.partition("-")
        if subtype:
            type_entries.append((label, f"{_TYPE_SHORT[domain_type]}_{subtype}",
                                 _SUBTYPE_COLOURS[subtype], _TYPE_ALT_COLOURS[subtype]))
        else:
            type_entries.append((label, _TYPE_SHORT[domain_type], CLASS_COLORS[domain_type],
                                 _TYPE_ALT_COLOURS[domain_type]))
    class_entries = [(name, name, _CLASS_COLOURS[name], _CLASS_COLOURS[name]) for name in types]
    return {
        "planars_types": {
            "bundles": [
                ("phonological_all", phonological, _PHONOLOGICAL_ALL_COLOUR, "Phonological (all)"),
                _MORSYN_INDET,
            ],
            "filters": [],
            "styles": _style_rows(type_entries),
        },
        "planars_classes": {
            "bundles": (
                [(t, names, CLASS_COLORS[t], t.capitalize()) for t, names in by_type.items()]
                # phon_<subtype>, not the bare subtype: a subtype can share
                # its name with a class (segmental, tonal), and forest ids
                # are file names.
                + [(f"phon_{s}", names, _SUBTYPE_COLOURS[s], f"Phonological ({s})")
                   for s, names in by_subtype.items()]
                + [("morsyn_indet", by_type.get("morphosyntactic", []) + by_type.get("indeterminate", []),
                    _MORSYN_INDET[2], _MORSYN_INDET[3])]
            ),
            "filters": [],
            "styles": _style_rows(class_entries),
        },
    }


GROUPINGS: dict[str, dict] = {
    "chichewa": {"bundles": BUNDLES, "filters": FILTERS},
    "ccdb": {"bundles": [_MORSYN_INDET], "filters": []},
    **_planars_groupings(),
}


def observed_domain_types(domain_file: Path) -> set[str]:
    """The Domain_Type values of a domains file's active (uncommented) rows
    that the analysis keeps: a span of one position is dropped
    (laminar_analysis.load_domain_dataframe()), so a type with only those
    has nothing to analyse and is no group (English's proform, in the
    complete selection, crashed the boundary-strength test that way)."""
    tests = pd.read_csv(domain_file, sep="\t", dtype=str, comment="#")
    tests = tests[pd.to_numeric(tests["Size"]) > 1]
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
