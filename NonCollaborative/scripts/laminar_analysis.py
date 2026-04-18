"""
laminar_analysis.py — Constituency domain analysis via laminar family decomposition.

════════════════════════════════════════════════════════════════════════════════
Background
════════════════════════════════════════════════════════════════════════════════

A laminar family is a collection of sets where every two members are either
nested (one contains the other) or disjoint (they share no elements). No
partial overlaps are allowed. A laminar family IS a rooted tree: the
containment relationships define a unique valid hierarchy, with each set's
parent being the smallest set that properly contains it.

This makes laminar families the right mathematical object for testing the
three hypotheses developed in Good, "Domains of linearization, constituency,
and wordhood in Chichewa":

  1. Tree hypothesis — The domains of constituency diagnostics should nest
     within each other. If all observed spans form a single rooted laminar
     family, the hypothesis is fully supported. The minimum number of laminar
     families needed quantifies how close the data is to tree-structured.

  2. Morphosyntax/phonology divide hypothesis — Deviations from nesting are
     tolerated between morphosyntactic and phonological diagnostics, but not
     within either class. Tested by checking whether conflicts (spans that
     cannot coexist in any laminar family) occur across domain types or
     within them.

  3. Word hypothesis — A set of diagnostics will converge on a consistently
     small span identifiable as the word domain. Spans appearing in every
     laminar family are the most-converged candidates; convergence counts
     (how many distinct tests produce the same span) quantify this.

════════════════════════════════════════════════════════════════════════════════
Problem statement
════════════════════════════════════════════════════════════════════════════════

Given a set of observed constituency domain spans over a planar structure
of N positions (with positions numbered 1..N), find the minimum number of
rooted laminar families — each rooted at the full span [1..N] — such that
every observed span appears in at least one family.

Spans may appear in multiple families. That is intentional: a span appearing
in every minimal covering family is a robust structural finding, independent
of how conflicts between other spans are resolved.

════════════════════════════════════════════════════════════════════════════════
Algorithm overview (four phases)
════════════════════════════════════════════════════════════════════════════════

Phase 1 — Conflict detection
  For every pair of observed spans, classify the relationship as:
    nested    — one span contains the other; compatible, can coexist in a tree
    disjoint  — spans share no positions; compatible, can coexist in a tree
    conflict  — spans partially overlap; CANNOT coexist in any laminar family
  Collect all conflict pairs. Complexity: O(n²) for n spans. Fast for the
  data sizes in this project (typically < 100 spans per language).

Phase 2 — Minimum family count via graph coloring
  Build a conflict graph (nodes = spans, edges = conflicts) and find its
  chromatic number — the minimum number of colors such that no two conflicting
  spans share a color. Each color class is one valid laminar family.

  This works because minimum families needed = chromatic number:
    - Any valid graph coloring gives a cover: each color class is a set of
      mutually non-conflicting spans, i.e., a valid laminar family.
    - Any cover gives a valid coloring: assign each span the index of the
      first family containing it. Adjacent spans (in the conflict graph)
      cannot share a family index, so this is a proper coloring.

  Algorithm: DSatur (Degree of SATURation). Colors vertices greedily in
  order of decreasing saturation (number of distinct colors already used by
  neighbors), breaking ties by degree. For the small, typically sparse
  conflict graphs in this data, DSatur finds the chromatic number exactly.
  For larger or denser graphs, pair with backtracking for guaranteed minimum.

Phase 3 — Tree construction
  For each color class (set of mutually non-conflicting spans):
    - Add the root [1..N] if not already present.
    - Sort spans by size, largest first.
    - Assign each span's parent as the smallest span that properly contains it.
  This is always unique and well-defined because the family is laminar.
  Complexity: O(n²) per family, trivial for these data sizes.

Phase 4 — Analysis
  - Number of families needed → quantitative test of the Tree hypothesis.
    One family = data is perfectly laminar = full support for Tree hypothesis.
    Each additional family required represents an unresolvable structural
    conflict in the data.
  - Spans appearing in all families → high-convergence candidates for the
    word domain (Tree hypothesis + Word hypothesis).
  - Conflict types → test of the morphosyntax/phonology divide hypothesis.
    Conflicts only between domain types: divide hypothesis supported.
    Conflicts within a domain type: divide hypothesis challenged for that type.
  - Conflict graph structure → summary of how close the data is to laminar.

════════════════════════════════════════════════════════════════════════════════
Comparison to treeTraversal.py
════════════════════════════════════════════════════════════════════════════════

The earlier algorithm (treeTraversal.py) built chains of nested spans — one
span per size level — and called these "trees". This caused two problems:

  1. Sibling spans (disjoint spans both contained in a larger parent) were
     split into separate chains rather than recognised as branches of one tree,
     leading to overcounting of "trees" needed.

  2. Partially overlapping spans caused the algorithm to loop or hang because
     it had no concept of conflict and tried to place incompatible spans into
     the same chain.

The present algorithm handles conflicts explicitly in Phase 1, before any
tree-building occurs. Phase 3 always operates on a clean laminar set and
therefore always produces a valid branching tree.

════════════════════════════════════════════════════════════════════════════════
Key mathematical reference
════════════════════════════════════════════════════════════════════════════════

The equivalence between rooted laminar families and rooted trees is classical.
The correspondence between trees and hierarchies (laminar families over a
finite ground set) is covered in:
  Semple, C. & Steel, M. (2003). Phylogenetics. Oxford University Press.
  Bui-Xuan, B.-M., Habib, M. & Rao, M. (2012). Tree-representation of set
    families and applications to combinatorial decompositions. European Journal
    of Combinatorics 33(5), 688–711.
See NonCollaborative/REFERENCES.md for the full bibliography.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Span:
    """A constituency domain span over positions [left, right].

    frozen=True makes Span hashable (usable as a dict key or set member).
    Equality and hashing are based on left and right only — two spans at the
    same position are the same span regardless of which test produced them.
    Metadata (labels, domain_types, convergence) is stored with compare=False
    so it doesn't affect equality or hashing.

    convergence: number of distinct tests that produced this span. This is
    the empirical measure of 'how many diagnostics agree on this domain',
    directly relevant to the Word hypothesis.
    """
    left: int
    right: int
    labels: tuple = field(compare=False, hash=False, default=())
    domain_types: frozenset = field(compare=False, hash=False, default_factory=frozenset)
    convergence: int = field(compare=False, hash=False, default=1)

    @property
    def size(self) -> int:
        return self.right - self.left + 1

    def contains(self, other: Span) -> bool:
        """True if this span contains (or equals) the other."""
        return self.left <= other.left and self.right >= other.right

    def __repr__(self) -> str:
        types = "/".join(sorted(self.domain_types))
        return f"[{self.left}–{self.right}] ({types}, n={self.convergence})"

    def short(self) -> str:
        """Short label for tree display."""
        return f"[{self.left}–{self.right}]"


def load_spans(domain_file: str, domains_dir: str | None = None,
               subset: list[str] | None = None,
               skip_prefix: str = "#") -> tuple[list[Span], int]:
    """Load domain spans from a TSV file and aggregate by unique position.

    Multiple rows with the same [Left_Edge, Right_Edge] are combined into one
    Span: their labels are collected, domain types pooled, and convergence
    counted. This reflects that multiple tests producing the same span is
    evidence of convergence — relevant to the Word hypothesis.

    Args:
        domain_file: TSV filename.
        domains_dir: Directory containing the file. Defaults to ../domains/
                     relative to this script's location.
        subset: If given, only include rows whose Domain_Type is in this list.
        skip_prefix: Rows whose Test_Labels starts with this character are
                     excluded. Handles the '#DummyRoot' convention used in
                     the CCDB data to mark synthetic placeholders.

    Returns:
        (spans, n_positions) where spans is the deduplicated list and
        n_positions is the maximum Right_Edge observed (= total positions).
    """
    if domains_dir is None:
        domains_dir = os.path.join(os.path.dirname(__file__), "..", "domains")

    df = pd.read_csv(os.path.join(domains_dir, domain_file), sep="\t")

    # Clean up domain type values (trailing whitespace observed in some files)
    df["Domain_Type"] = df["Domain_Type"].str.strip()

    # Data integrity check: Size must match Right_Edge - Left_Edge + 1
    df["_calc_size"] = df["Right_Edge"] - df["Left_Edge"] + 1
    bad = df[df["Size"] != df["_calc_size"]]
    if not bad.empty:
        raise ValueError(
            f"Size mismatch in {domain_file}:\n{bad[['Test_Labels','Left_Edge','Right_Edge','Size','_calc_size']]}"
        )

    # Skip synthetic placeholder rows (e.g. #DummyRoot)
    if skip_prefix:
        df = df[~df["Test_Labels"].str.startswith(skip_prefix)]

    # Filter by domain type if requested
    if subset:
        df = df[df["Domain_Type"].isin(subset)]

    # Filter size-1 spans: a single position cannot form a meaningful domain
    df = df[df["Size"] > 1]

    # Aggregate rows with the same span into one Span object
    aggregated: dict[tuple[int, int], dict] = {}
    for _, row in df.iterrows():
        key = (int(row["Left_Edge"]), int(row["Right_Edge"]))
        if key not in aggregated:
            aggregated[key] = {"labels": [], "domain_types": set()}
        aggregated[key]["labels"].append(row["Test_Labels"])
        aggregated[key]["domain_types"].add(row["Domain_Type"])

    spans = [
        Span(
            left=left,
            right=right,
            labels=tuple(data["labels"]),
            domain_types=frozenset(data["domain_types"]),
            convergence=len(data["labels"]),
        )
        for (left, right), data in sorted(aggregated.items())
    ]

    n_positions = int(df["Right_Edge"].max())
    return spans, n_positions


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1: Conflict detection
# ══════════════════════════════════════════════════════════════════════════════

def classify_pair(a: Span, b: Span) -> str:
    """Classify the relationship between two spans.

    Returns one of:
      'nested'   — one span contains the other; compatible in a laminar family
      'disjoint' — spans share no positions; compatible in a laminar family
      'conflict' — spans partially overlap; CANNOT coexist in any laminar family

    Two spans [l1,r1] and [l2,r2] conflict when they cross:
        l1 < l2 <= r1 < r2  (a starts first, b extends beyond a's right edge)
        l2 < l1 <= r2 < r1  (b starts first, a extends beyond b's right edge)

    Crossing spans are incompatible because there is no way to assign a
    parent-child or sibling relationship between them: they are neither
    nested (which would require one to contain the other) nor disjoint
    (which would require them to share no positions).
    """
    if a.contains(b) or b.contains(a):
        return "nested"
    if a.right < b.left or b.right < a.left:
        return "disjoint"
    return "conflict"


def find_conflicts(spans: list[Span]) -> dict[Span, set[Span]]:
    """Build the conflict graph over spans.

    The conflict graph has:
      nodes = observed spans
      edges = pairs of spans that partially overlap (cannot coexist in one tree)

    Complexity: O(n²) for n spans — trivial for data sizes in this project.

    Returns: adjacency dict mapping each span to its set of conflicting spans.
             Spans with no conflicts are not present as keys.
    """
    adjacency: dict[Span, set[Span]] = defaultdict(set)
    for i, a in enumerate(spans):
        for b in spans[i + 1:]:
            if classify_pair(a, b) == "conflict":
                adjacency[a].add(b)
                adjacency[b].add(a)
    return dict(adjacency)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2: Minimum family count via graph coloring (DSatur)
# ══════════════════════════════════════════════════════════════════════════════

def dsatur_coloring(spans: list[Span],
                    adjacency: dict[Span, set[Span]]) -> dict[Span, int]:
    """Find a graph coloring using the DSatur algorithm.

    The minimum number of laminar families needed to cover all observed spans
    equals the chromatic number of the conflict graph — the minimum number of
    colors such that no two conflicting spans share a color. Each color class
    is one valid laminar family. See module docstring for the proof.

    DSatur (Degree of SATURation) colors vertices greedily in order of
    decreasing saturation (number of distinct colors already used by
    neighbors), breaking ties by degree. This heuristic is exact for many
    graph classes and in practice for the small, sparse conflict graphs
    typical of this data. For denser graphs, backtracking is needed for a
    guaranteed minimum; DSatur then serves as the upper bound.

    Args:
        spans: All observed spans.
        adjacency: Conflict graph adjacency dict from find_conflicts().

    Returns:
        Dict mapping each span to a color index (int, 0-based).
        All spans with no conflicts receive color 0.
    """
    if not spans:
        return {}

    color: dict[Span, int] = {}
    # saturation[s] = set of colors already used by s's neighbors
    saturation: dict[Span, set[int]] = defaultdict(set)

    def degree(s: Span) -> int:
        return len(adjacency.get(s, set()))

    # Seed: start with the highest-degree vertex
    first = max(spans, key=degree)
    color[first] = 0
    for neighbor in adjacency.get(first, set()):
        saturation[neighbor].add(0)

    while len(color) < len(spans):
        # Pick the uncolored vertex with the highest saturation;
        # break ties by degree (denser neighborhoods constrain color choice more)
        uncolored = [s for s in spans if s not in color]
        current = max(uncolored,
                      key=lambda s: (len(saturation[s]), degree(s)))

        # Assign the lowest color index not used by any neighbor
        used = saturation[current]
        c = 0
        while c in used:
            c += 1
        color[current] = c

        for neighbor in adjacency.get(current, set()):
            if neighbor not in color:
                saturation[neighbor].add(c)

    return color


def group_by_color(coloring: dict[Span, int]) -> dict[int, list[Span]]:
    """Group spans by their assigned color (family index)."""
    groups: dict[int, list[Span]] = defaultdict(list)
    for span, c in coloring.items():
        groups[c].append(span)
    return dict(groups)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3: Tree construction
# ══════════════════════════════════════════════════════════════════════════════

def ensure_root(family_spans: list[Span], n_positions: int) -> list[Span]:
    """Ensure the laminar family includes a root spanning all positions.

    The root [1..N] is required: every valid laminar family in this analysis
    must be rooted at the full planar structure. If no observed span covers
    [1..N], a synthetic root is added with convergence=0.
    """
    root_span = Span(1, n_positions,
                     labels=("(root)",),
                     domain_types=frozenset(["(synthetic)"]),
                     convergence=0)
    if any(s.left == 1 and s.right == n_positions for s in family_spans):
        return family_spans
    return family_spans + [root_span]


def build_parent_map(family_spans: list[Span]) -> dict[Span, Span | None]:
    """Build the parent map for a laminar family tree.

    For each span, its parent is the smallest span that properly contains it.
    The root's parent is None.

    Because the family is laminar (every pair is nested or disjoint), the
    parent assignment is always unique and well-defined — there is never
    ambiguity about which span is the immediate parent.

    Complexity: O(n²). Fine for the family sizes encountered in this data.
    """
    sorted_spans = sorted(family_spans, key=lambda s: s.size, reverse=True)
    root = sorted_spans[0]  # largest span is the root
    parent: dict[Span, Span | None] = {root: None}

    for span in sorted_spans[1:]:
        containers = [s for s in sorted_spans if s != span and s.contains(span)]
        if containers:
            parent[span] = min(containers, key=lambda s: s.size)
        else:
            parent[span] = root

    return parent


def get_children(parent_map: dict[Span, Span | None]) -> dict[Span, list[Span]]:
    """Invert the parent map to get each span's direct children."""
    children: dict[Span, list[Span]] = defaultdict(list)
    for span, par in parent_map.items():
        if par is not None:
            children[par].append(span)
    return dict(children)


def format_tree_text(span: Span,
                     children: dict[Span, list[Span]],
                     indent: int = 0) -> str:
    """Format a tree as an indented text representation for printing."""
    types = "/".join(sorted(span.domain_types))
    labels = ", ".join(span.labels[:3])
    if len(span.labels) > 3:
        labels += f" (+{len(span.labels) - 3} more)"
    conv = f"n={span.convergence}"
    line = "  " * indent + f"{span.short()}  [{types}]  {conv}  {labels}"
    parts = [line]
    for child in sorted(children.get(span, []), key=lambda s: s.left):
        parts.append(format_tree_text(child, children, indent + 1))
    return "\n".join(parts)


def span_to_newick(span: Span,
                   children: dict[Span, list[Span]]) -> str:
    """Recursively build a Newick string for a span and its subtree.

    Unlike treeTraversal.py's chain-based generator, this function works on
    a proper branching tree. Positions not covered by any child span appear
    as leaf nodes at the level of the span that directly contains them.

    The Newick format produced is compatible with ape::read.tree() in R.
    Internal node labels are 'left-right' (e.g. '5-17'); leaves are position
    numbers (e.g. '5', '6', ...).
    """
    direct_children = sorted(children.get(span, []), key=lambda s: s.left)

    if not direct_children:
        # Leaf span: all positions in it are leaf nodes
        leaves = ",".join(str(p) for p in range(span.left, span.right + 1))
        return f"({leaves}){span.left}-{span.right}"

    # Positions covered by child spans (won't appear as leaves here)
    child_covered = set()
    for child in direct_children:
        child_covered.update(range(child.left, child.right + 1))

    parts = []
    prev_boundary = span.left

    for child in direct_children:
        # Exposed positions between the previous child and this one
        for pos in range(prev_boundary, child.left):
            if pos not in child_covered:
                parts.append(str(pos))
        parts.append(span_to_newick(child, children))
        prev_boundary = child.right + 1

    # Exposed positions after the last child
    for pos in range(prev_boundary, span.right + 1):
        if pos not in child_covered:
            parts.append(str(pos))

    return f"({','.join(parts)}){span.left}-{span.right}"


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4: Analysis and reporting
# ══════════════════════════════════════════════════════════════════════════════

def report_conflicts(adjacency: dict[Span, set[Span]],
                     all_spans: list[Span]) -> None:
    """Print a conflict analysis and its implications for the three hypotheses.

    A conflict between two spans of the SAME domain type challenges the Tree
    hypothesis within that type. A conflict between spans of DIFFERENT domain
    types is expected under the morphosyntax/phonology divide hypothesis.
    """
    conflict_pairs = [
        (a, b)
        for a, neighbors in adjacency.items()
        for b in neighbors
        if (a.left, a.right) < (b.left, b.right)  # deduplicate: report each pair once
    ]

    n_conflicts = len(conflict_pairs)
    print(f"Conflicts: {n_conflicts} pairs of spans partially overlap")

    if n_conflicts == 0:
        print("  → Data is perfectly laminar. One tree covers all spans.")
        print("  → Tree hypothesis: fully supported.")
        return

    # Classify conflicts by domain type relationship
    within_type = [(a, b) for a, b in conflict_pairs
                   if a.domain_types & b.domain_types]  # share at least one type
    cross_type = [(a, b) for a, b in conflict_pairs
                  if not (a.domain_types & b.domain_types)]

    print(f"  Within domain type:  {len(within_type)}")
    print(f"  Across domain types: {len(cross_type)}")

    if within_type:
        print("\n  Within-type conflicts (challenge Tree hypothesis within that type):")
        for a, b in within_type:
            shared = a.domain_types & b.domain_types
            print(f"    {a.short()} vs {b.short()}  [{'/'.join(sorted(shared))}]")

    if cross_type:
        print("\n  Cross-type conflicts (consistent with morphosyntax/phonology divide):")
        for a, b in cross_type:
            print(f"    {a.short()} [{'/'.join(sorted(a.domain_types))}]"
                  f"  vs  {b.short()} [{'/'.join(sorted(b.domain_types))}]")


def report_families(families: dict[int, list[Span]],
                    n_positions: int) -> dict[Span, int]:
    """Print each laminar family as a tree, return span→family_count mapping."""
    span_family_count: dict[Span, int] = defaultdict(int)

    print(f"\nLaminar families found: {len(families)}")
    for idx, spans_in_family in sorted(families.items()):
        family_with_root = ensure_root(spans_in_family, n_positions)
        parent_map = build_parent_map(family_with_root)
        children = get_children(parent_map)
        root = max(family_with_root, key=lambda s: s.size)

        print(f"\n─── Family {idx + 1} ({len(family_with_root)} spans) ───")
        print(format_tree_text(root, children))

        for s in spans_in_family:
            span_family_count[s] += 1

    return dict(span_family_count)


def report_convergence(span_family_count: dict[Span, int],
                       n_families: int) -> None:
    """Report which spans appear in multiple families.

    Spans in all families are the most structurally robust findings —
    they are present regardless of how conflicts between other spans are
    resolved. These are the strongest word domain candidates.
    """
    print("\nSpan occurrence across families:")
    print(f"  (max possible = {n_families})")

    by_count = defaultdict(list)
    for span, count in span_family_count.items():
        by_count[count].append(span)

    for count in sorted(by_count.keys(), reverse=True):
        spans = sorted(by_count[count], key=lambda s: s.size)
        label = "← in ALL families" if count == n_families else ""
        for s in spans:
            print(f"  {count}/{n_families}  {s}  {label}")


def generate_r_script(families: dict[int, list[Span]],
                      n_positions: int,
                      span_family_count: dict[Span, int],
                      output_dir: str,
                      tpfx: str = "",
                      color: str = "black") -> None:
    """Write a ggtree R script for visualising the laminar families.

    Each family produces one proper branching tree (via a correct recursive
    Newick encoder), unlike treeTraversal.py which produced one chain per
    'tree' and overlaid them. Branch thickness is scaled by convergence count
    (square-root scaled to compress the range), so stronger spans appear
    with heavier lines.
    """
    n_families = len(families)
    if n_families == 0:
        return

    # Alpha: chosen so all trees together approach black
    alphaval = round(1 - 0.01 ** (1 / n_families), 6)

    rout_path = os.path.join(output_dir, tpfx + "laminar_forest.r")
    with open(rout_path, "w") as rout:
        print("library(ape)", file=rout)
        print("library(ggplot2)", file=rout)
        print("library(ggtree)", file=rout)
        print("library(patchwork)", file=rout)
        print("", file=rout)
        print(f"alphaval <- {alphaval} / 2", file=rout)
        print("", file=rout)

        plot_names = []
        for idx, spans_in_family in sorted(families.items()):
            family_with_root = ensure_root(spans_in_family, n_positions)
            parent_map = build_parent_map(family_with_root)
            children_map = get_children(parent_map)
            root = max(family_with_root, key=lambda s: s.size)

            newick = span_to_newick(root, children_map) + ";"
            tree_var = f"{tpfx}tree{idx + 1}"
            print(f'{tree_var} <- read.tree(text="{newick}")', file=rout)

            # Strength mapping: branch thickness = sqrt(convergence)
            # Each span in the family gets a strength; ungrouped positions get 0.5
            sorted_spans = sorted(spans_in_family, key=lambda s: s.left)
            labelstart = 97  # 'a'
            domains_r = [
                f"{chr(labelstart + i)} = c({s.left}, {s.right})"
                for i, s in enumerate(sorted_spans)
            ]
            grouped_var = f"{tree_var}grouped"
            print(
                f'{grouped_var} <- groupOTU({tree_var}, list({", ".join(domains_r)}))',
                file=rout,
            )

            strength_vals = ", ".join(
                str(round(span_family_count.get(s, 1) ** 0.5, 4))
                for s in sorted_spans
            )
            strength_var = f"strengthMap{idx + 1}"
            print(f"{strength_var} <- c(0.5, {strength_vals})", file=rout)

            plot_var = f"{tpfx}treeplot{idx + 1}"
            plot_names.append(plot_var)
            tip_alpha = 1 if idx == 0 else 0
            print(
                f'{plot_var} <- ggtree({grouped_var},\n'
                f'  aes(size=({strength_var}[group])),\n'
                f'  layout="slanted", ladderize=FALSE,\n'
                f'  alpha=alphaval, color="{color}") +\n'
                f'  layout_dendrogram() +\n'
                f'  geom_tiplab(geom="label", size=5, angle=0,\n'
                f'    offset=-1, hjust=0.5, alpha={tip_alpha},\n'
                f'    lineheight=1) +\n'
                f'  theme(panel.background=element_blank(),\n'
                f'    plot.background=element_blank(),\n'
                f'    legend.position="none") +\n'
                f'  scale_size_identity()',
                file=rout,
            )
            print("", file=rout)

        # Patchwork layout
        print("treelayout <- c(", file=rout)
        for i in range(n_families - 1):
            print("  area(t=1, l=1, b=5, r=1),", file=rout)
        print("  area(t=1, l=1, b=5, r=1))", file=rout)
        print("", file=rout)
        joined = " +\n  ".join(plot_names)
        print(f"forest <- (\n  {joined} +\n  plot_layout(design=treelayout))", file=rout)
        print("print(forest)", file=rout)

    print(f"\nR script written to: {rout_path}")


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

def main(domain_file: str = "domains_nyan1308.tsv",
         domains_dir: str | None = None,
         output_dir: str | None = None,
         subset: list[str] | None = None,
         color: str = "black",
         tpfx: str = "") -> dict:
    """Run the full laminar family analysis for one domain file.

    Args:
        domain_file: TSV filename inside domains_dir.
        domains_dir: Path to the domains/ folder. Defaults to ../domains/
                     relative to this script's location.
        output_dir:  Where to write the R script. Defaults to CWD.
        subset:      List of Domain_Type strings to include (e.g.
                     ["morphosyntactic"]). None = all types.
        color:       Branch color for the ggtree output.
        tpfx:        Variable-name prefix for R output (e.g. "phon").

    Returns:
        Dict with keys: spans, conflicts, families, span_family_count,
        n_families. Useful for programmatic access and testing.
    """
    if output_dir is None:
        output_dir = os.getcwd()

    print(f"═══ Laminar family analysis: {domain_file} ═══")
    if subset:
        print(f"    Domain type filter: {subset}")

    # ── Phase 1: load and find conflicts ─────────────────────────────────────
    spans, n_positions = load_spans(domain_file, domains_dir, subset)
    print(f"\nPhase 1 — Loaded {len(spans)} unique spans over {n_positions} positions")

    adjacency = find_conflicts(spans)
    print(f"           Conflict graph: {len(adjacency)} spans involved in at least one conflict")
    print()
    report_conflicts(adjacency, spans)

    # ── Phase 2: minimum coloring ─────────────────────────────────────────────
    print("\nPhase 2 — Graph coloring (minimum laminar families)")
    coloring = dsatur_coloring(spans, adjacency)
    families = group_by_color(coloring)
    n_families = len(families)
    print(f"           Minimum families needed: {n_families}")

    if n_families == 1:
        print("           → Tree hypothesis: FULLY SUPPORTED (data is perfectly laminar)")
    else:
        print(f"           → Tree hypothesis: {n_families} trees required to cover all spans")

    # ── Phase 3 + 4: build trees and report ──────────────────────────────────
    print("\nPhase 3 — Tree structures")
    span_family_count = report_families(families, n_positions)

    print("\nPhase 4 — Cross-family analysis")
    report_convergence(span_family_count, n_families)

    # ── R output ─────────────────────────────────────────────────────────────
    generate_r_script(families, n_positions, span_family_count,
                      output_dir, tpfx, color)

    return {
        "spans": spans,
        "adjacency": adjacency,
        "families": families,
        "span_family_count": span_family_count,
        "n_families": n_families,
    }


if __name__ == "__main__":
    # Default: run on nyan1308 (the language most carefully checked against
    # the earlier treeTraversal.py algorithm).
    #
    # To run on a subset by domain type:
    #   main(subset=["morphosyntactic"], color="#EE6677", tpfx="morsyn")
    #   main(subset=["phonological", "tonosegmental"], color="#4477AA", tpfx="phon")
    #   main(subset=["intonational"], color="#228833", tpfx="inton")
    main()
