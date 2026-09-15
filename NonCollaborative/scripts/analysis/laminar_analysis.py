"""
laminar_analysis.py — Constituency domain analysis via laminar family enumeration.

════════════════════════════════════════════════════════════════════════════════
Background
════════════════════════════════════════════════════════════════════════════════

A laminar family is a collection of sets where every two members are either
nested (one contains the other) or disjoint (they share no elements). No
partial overlaps are allowed. A laminar family induces a rooted containment
tree once a root is supplied (and uncovered ground-set positions are treated
as leaves): each set's parent is the smallest set that properly contains it.

This makes laminar families the right mathematical object for testing the
three hypotheses developed in Good, "Domains of linearization, constituency,
and wordhood in Chichewa":

  1. Tree hypothesis — The domains of constituency diagnostics should nest
     within each other. If all observed spans form a single laminar family,
     the hypothesis is fully supported. The number of maximal laminar families
     quantifies the space of consistent tree interpretations.

  2. Morphosyntax/phonology divide hypothesis — Deviations from nesting are
     tolerated between morphosyntactic and phonological diagnostics, but not
     within either class. Tested by checking whether conflicts occur across
     domain types or within them.

  3. Word hypothesis — A set of diagnostics will converge on a consistently
     small span identifiable as the word domain. Spans appearing in every
     maximal family are the most structurally robust candidates.

════════════════════════════════════════════════════════════════════════════════
Problem statement
════════════════════════════════════════════════════════════════════════════════

Given a set of observed constituency domain spans over a planar structure of N
positions (numbered 1..N), enumerate ALL MAXIMAL LAMINAR FAMILIES rooted at
the full span [1..N].

A maximal laminar family is a set of spans such that:
  (a) every pair of spans is either nested or disjoint (no partial overlaps);
  (b) it is impossible to add any further observed span without creating a
      partial overlap — it is "greedy" in the sense that every compatible
      span is included.

A span appears in a family if and only if it is compatible (nested or
disjoint) with every other span in that family. Each span may appear in
multiple families; appearing in ALL families is the strongest finding.

This is equivalent to enumerating all MAXIMAL INDEPENDENT SETS of the conflict
graph (the graph whose nodes are observed spans and whose edges connect pairs
of spans that partially overlap). Each maximal independent set is a maximal
set of mutually compatible spans, i.e., a valid laminar family.

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

Phase 2 — Enumerate all maximal laminar families
  Use the Bron-Kerbosch algorithm to enumerate all maximal independent sets
  of the conflict graph. Each maximal independent set is one valid maximal
  laminar family.

  Bron-Kerbosch with pivoting maintains three sets at each recursive call:
    R = current independent set (committed spans, all mutually compatible)
    P = candidates (compatible with all of R, not yet decided)
    X = excluded (compatible with all of R, but already processed — used to
        detect non-maximality: if X is non-empty at a leaf, we can still
        extend R and have NOT found a maximal set)

  When P and X are both empty, R is a maximal independent set. Report it.

  The root [1..N] is always compatible with every other span (they are all
  contained in [1..N]), so it is placed directly into the starting R set and
  added to every reported family.

Phase 3 — Tree construction
  For each maximal laminar family:
    - Spans are already mutually compatible, so parent assignment is unique.
    - Sort spans by size, largest first.
    - Assign each span's parent as the smallest span that properly contains it.
  Complexity: O(n²) per family, trivial for these data sizes.

Phase 4 — Analysis
  - Number of distinct maximal families → quantitative test of Tree hypothesis.
    One family = data is perfectly laminar = full support for Tree hypothesis.
    More families = data is consistent with more interpretations.
  - Spans appearing in all families → high-convergence word-domain candidates.
  - Conflict types → test of the morphosyntax/phonology divide hypothesis.

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
The correspondence is covered in:
  Semple, C. & Steel, M. (2003). Phylogenetics. Oxford University Press.
  Bui-Xuan, B.-M., Habib, M. & Rao, M. (2012). Tree-representation of set
    families and applications to combinatorial decompositions. European Journal
    of Combinatorics 33(5), 688–711.

The Bron-Kerbosch algorithm for enumerating maximal cliques (here applied to
maximal independent sets via the conflict graph) is described in:
  Bron, C. & Kerbosch, J. (1973). Finding all cliques of an undirected graph.
    Communications of the ACM 16(9), 575–577.
  Tomita, E., Tanaka, A. & Takahashi, H. (2006). The worst-case time complexity
    for generating all maximal cliques. Theoretical Computer Science 363, 28–42.

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
        domains_dir: Directory containing the file. Defaults to ../../domains/
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
        domains_dir = os.path.join(os.path.dirname(__file__), "..", "..", "domains")

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
             Only spans involved in at least one conflict appear as keys.
    """
    adjacency: dict[Span, set[Span]] = defaultdict(set)
    for i, a in enumerate(spans):
        for b in spans[i + 1:]:
            if classify_pair(a, b) == "conflict":
                adjacency[a].add(b)
                adjacency[b].add(a)
    return dict(adjacency)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2: Enumerate all maximal laminar families (Bron-Kerbosch)
# ══════════════════════════════════════════════════════════════════════════════

MAX_FAMILIES = 1000  # safeguard: abort enumeration beyond this count

class _TooManyFamilies(Exception):
    pass


def _bron_kerbosch(R: frozenset, P: frozenset, X: frozenset,
                   adjacency: dict, results: list) -> None:
    """Recursive Bron-Kerbosch for maximal independent sets (MIS) in the
    conflict graph G.

    Equivalently: finds maximal cliques in the compatibility graph G^c, where
    G^c has an edge between two spans iff they are nested or disjoint.

    VERIFICATION: This implementation has been independently verified against
    NetworkX's nx.find_cliques() on the complement graph. Both algorithms
    produce identical results. See ../verification/verify_chichewa.py for the
    NetworkX implementation used for verification (69 families on Chichewa
    [nyan1308]).

    Maintains three sets:
      R = current independent set (all mutually compatible spans)
      P = candidate spans (compatible with all of R, not yet decided)
      X = excluded spans (compatible with all of R, already processed;
          non-empty X at a leaf means R is not maximal)

    When P and X are both empty, R is a maximal independent set. Report it.

    When adding v to R, the new P and X are restricted to spans compatible
    with v — i.e., spans NOT in adjacency[v] (the conflict neighbours of v).

    Non-pivoted version: iterate over every vertex in P in turn. This is
    straightforwardly correct. The pivot optimisation for MIS requires
    iterating over the CONFLICT-neighbours of the pivot (not the compatible
    ones), which is the opposite of the clique-graph intuition and easy to
    get wrong; the non-pivoted version avoids that risk and is fast enough
    for the graph sizes in this project (typically < 100 spans per language).

    Raises _TooManyFamilies after MAX_FAMILIES results to prevent runaway
    enumeration on pathological inputs.
    """
    if not P and not X:
        results.append(frozenset(R))
        if len(results) >= MAX_FAMILIES:
            raise _TooManyFamilies()
        return

    for v in list(P):
        v_conflicts = adjacency.get(v, frozenset())
        # new_P: candidates compatible with v (remove v and v's conflict neighbours)
        new_P = (P - v_conflicts) - {v}
        # new_X: excluded spans that are also compatible with v
        new_X = X - v_conflicts
        _bron_kerbosch(R | {v}, new_P, new_X, adjacency, results)
        P = P - {v}
        X = X | {v}


def enumerate_maximal_laminar_families(
        spans: list[Span],
        adjacency: dict[Span, set[Span]],
        n_positions: int,
) -> tuple[list[frozenset[Span]], bool]:
    """Enumerate all maximal laminar families rooted at [1..N].

    A maximal laminar family is a maximal independent set of the conflict
    graph — a set of mutually compatible spans to which no further observed
    span can be added without creating a conflict.

    The root [1..N] is compatible with every observed span (all spans are
    contained in the root), so it is always included in the starting set R
    and appears in every reported family. If [1..N] is not in the observed
    spans, a synthetic root is added with convergence=0.

    Args:
        spans: All observed spans (output of load_spans).
        adjacency: Conflict graph from find_conflicts.
        n_positions: Total positions in the planar structure.

    Returns:
        (families, truncated) where:
          families — list of frozensets, each a maximal laminar family
                     (including the root span)
          truncated — True if enumeration was halted at MAX_FAMILIES
    """
    # Identify or synthesise the root span
    root_match = next((s for s in spans
                       if s.left == 1 and s.right == n_positions), None)
    if root_match is not None:
        root = root_match
        non_root_spans = [s for s in spans if s != root]
    else:
        root = Span(1, n_positions,
                    labels=("(root)",),
                    domain_types=frozenset(["(synthetic)"]),
                    convergence=0)
        non_root_spans = spans

    # The root is compatible with everything, so we seed R = {root}
    # and let Bron-Kerbosch freely include all compatible non-root spans.
    # No non-root span conflicts with the root (they are all nested in it),
    # so P starts as the full set of non-root spans.
    results: list[frozenset[Span]] = []
    truncated = False

    try:
        _bron_kerbosch(
            R=frozenset({root}),
            P=frozenset(non_root_spans),
            X=frozenset(),
            adjacency=adjacency,
            results=results,
        )
    except _TooManyFamilies:
        truncated = True

    # Each result already contains the root (it was in the seed R).
    # Sort families for deterministic output: by size (descending), then
    # by the sorted tuple of (left, right) of their spans.
    results.sort(key=lambda fam: (
        -len(fam),
        tuple(sorted((s.left, s.right) for s in fam)),
    ))

    return results, truncated


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3: Tree construction
# ══════════════════════════════════════════════════════════════════════════════

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


def report_families(families: list[frozenset[Span]],
                    n_positions: int,
                    truncated: bool,
                    show_trees: bool = True,
                    max_trees_to_show: int = 20) -> dict[Span, int]:
    """Print each maximal laminar family as a tree.

    Returns a mapping from span → number of families in which it appears.
    This count is the primary measure of structural robustness: a span
    appearing in all families is present regardless of how conflicts are
    resolved elsewhere in the tree.

    Args:
        show_trees: If True, print indented tree structure for each family.
                    If False (or if n > max_trees_to_show), print only the
                    span list. Full trees can be inspected in the R output.
        max_trees_to_show: Automatically suppress tree bodies above this count.
    """
    span_family_count: dict[Span, int] = defaultdict(int)

    n = len(families)
    trunc_note = f" (enumeration halted at {MAX_FAMILIES})" if truncated else ""
    print(f"\nMaximal laminar families: {n}{trunc_note}")

    verbose = show_trees and (n <= max_trees_to_show)
    if not verbose and show_trees:
        print(f"  (tree bodies suppressed for {n} > {max_trees_to_show} families;"
              f" see R output for full visualisation)")

    for idx, family_set in enumerate(families):
        family_list = sorted(family_set, key=lambda s: s.size, reverse=True)

        if verbose:
            parent_map = build_parent_map(family_list)
            children = get_children(parent_map)
            root = max(family_list, key=lambda s: s.size)
            print(f"\n─── Tree {idx + 1} ({len(family_list)} spans) ───")
            print(format_tree_text(root, children))
        else:
            span_labels = " ".join(
                f"[{s.left}–{s.right}]"
                for s in sorted(family_list, key=lambda s: s.size, reverse=True)
            )
            print(f"  Tree {idx + 1:3d} ({len(family_list):2d} spans): {span_labels}")

        for s in family_set:
            span_family_count[s] += 1

    return dict(span_family_count)


def report_convergence(span_family_count: dict[Span, int],
                       n_families: int) -> None:
    """Report which spans appear in how many families.

    Spans in all families are the most structurally robust findings —
    they are present regardless of how conflicts between other spans are
    resolved. These are the strongest word domain candidates.

    Spans in only one family are structurally contingent — they can be
    included in a consistent tree, but only under one particular resolution
    of the conflict structure.
    """
    print(f"\nSpan occurrence across {n_families} maximal trees:")

    by_count: dict[int, list[Span]] = defaultdict(list)
    for span, count in span_family_count.items():
        by_count[count].append(span)

    for count in sorted(by_count.keys(), reverse=True):
        spans = sorted(by_count[count], key=lambda s: s.size)
        label = "← in ALL trees" if count == n_families else ""
        for s in spans:
            print(f"  {count}/{n_families}  {s}  {label}")


def generate_r_script(families: list[frozenset[Span]],
                      n_positions: int,
                      span_family_count: dict[Span, int],
                      output_dir: str,
                      tpfx: str = "",
                      color: str = "black",
                      pos_labels: dict[int, str] | None = None) -> None:
    """Write a ggtree R script for visualising the maximal laminar families.

    Each family produces one proper branching tree (via a correct recursive
    Newick encoder), unlike treeTraversal.py which produced one chain per
    'tree' and overlaid them. Branch thickness is scaled by how many families
    a span appears in (sqrt-scaled to compress the range): spans present in
    all trees appear with the heaviest lines.

    pos_labels: Position number -> label (e.g. _NYAN1308_POS_LABELS). If
    given, tips show as boxed "N\\nName" labels, matching
    generate_r_overlay_script()'s convention -- only the last tree's copy is
    made visible (colour=NA, fill=NA on every other copy; alpha=0 alone does
    NOT hide a geom="label" tip in this ggtree version, and neither does
    label.size=0 -- see that function's docstring for the verified writeup).
    If omitted, tips fall back to bare position numbers.
    """
    n_families = len(families)
    if n_families == 0:
        return

    # Alpha: chosen so all trees together approach black
    alphaval = round(1 - 0.01 ** (1 / n_families), 6)

    rout_path = os.path.join(output_dir, tpfx + "laminar_forest.r")
    pdf_path = rout_path[:-2] + ".pdf" if rout_path.endswith(".r") else rout_path + ".pdf"
    with open(rout_path, "w") as rout:
        print("library(ape)", file=rout)
        print("library(ggplot2)", file=rout)
        print("library(ggtree)", file=rout)
        print("library(patchwork)", file=rout)
        print("", file=rout)
        if pos_labels:
            pairs = ", ".join(
                f'"{k}" = "{v}"' for k, v in sorted(pos_labels.items())
            )
            print(f"posLabel <- list({pairs})", file=rout)
            print("", file=rout)
        print(f"alphaval <- {alphaval} / 2", file=rout)
        print("", file=rout)

        plot_names = []
        for idx, family_set in enumerate(families):
            family_list = sorted(family_set, key=lambda s: s.size, reverse=True)
            parent_map = build_parent_map(family_list)
            children_map = get_children(parent_map)
            root = max(family_list, key=lambda s: s.size)

            newick = span_to_newick(root, children_map) + ";"
            tree_var = f"{tpfx}tree{idx + 1}"
            print(f'{tree_var} <- read.tree(text="{newick}")', file=rout)

            # Branch thickness = sqrt(number of families span appears in).
            # Spans in all families = heaviest lines; contingent spans = thinner.
            sorted_spans = sorted(family_list, key=lambda s: s.left)
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
            # Every tree's own tip labels are fully invisible placeholders
            # that just reserve panel space -- the one real, visible label is
            # added once, to the last tree, after the loop (see below).
            # colour=NA, fill=NA is what actually hides a geom="label" tip;
            # alpha=0 alone is silently ignored, and label.size=0 is dropped
            # outright by this ggtree version -- see
            # generate_r_overlay_script()'s docstring for the verified
            # writeup of that bug.
            print(
                f'{plot_var} <- ggtree({grouped_var},\n'
                f'  aes(size=({strength_var}[group])),\n'
                f'  layout="slanted", ladderize=FALSE,\n'
                f'  alpha=alphaval, color="{color}") +\n'
                f'  layout_dendrogram() +\n'
                f'  geom_tiplab(geom="label", size=5, angle=0,\n'
                f'    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA,\n'
                f'    lineheight=1) +\n'
                f'  theme(panel.background=element_blank(),\n'
                f'    plot.background=element_blank(),\n'
                f'    legend.position="none",\n'
                f'    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +\n'
                f'  scale_size_identity()',
                file=rout,
            )
            print("", file=rout)

        last_plot = plot_names[-1]
        if pos_labels:
            print(
                f'{last_plot} <- {last_plot} + geom_tiplab(geom="label", size=6, angle=0,\n'
                '  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,\n'
                '  aes(label=paste(label, posLabel[label], sep="\\n")), lineheight=1)',
                file=rout,
            )
        else:
            print(
                f'{last_plot} <- {last_plot} + geom_tiplab(geom="label", size=6, angle=0,\n'
                '  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0, lineheight=1)',
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
        print(
            f'ggsave("{pdf_path}", forest & theme(plot.background=element_rect(fill=\'white\', color=NA)), '
            f'width=20, height=14)',
            file=rout,
        )

    print(f"\nR script written to: {rout_path}")


# ══════════════════════════════════════════════════════════════════════════════
# Overlay: multi-domain-type forest visualization
# ══════════════════════════════════════════════════════════════════════════════

# Standard colors matching the pooled-plot convention
OVERLAY_GROUPS: list[tuple[list[str], str, str]] = [
    (["morphosyntactic"], "#BC3C29", "morsyn"),
    (["tonosegmental"],   "#0072B5", "tono"),
    (["length"],          "#E18727", "length"),
    (["phonological"],    "#20845E", "phon"),
    (["intonational"],    "#7876B1", "inton"),
]

_NYAN1308_POS_LABELS: dict[int, str] = {
    1: "QM",    2: "PreSbj", 3: "Sbj",   4: "PostSbj",
    5: "Neg1",  6: "SM",     7: "Neg2",  8: "TAM",
    9: "OM",   10: "Root",  11: "Ext",  12: "STAT",
   13: "CAUS", 14: "APPL",  15: "REC",  16: "PASS",
   17: "FV",   18: "2P",    19: "Enc",  20: "Obj1",
   21: "Obj2", 22: "PostObj",
}


def generate_r_overlay_script(
        subsets: list[tuple[list, dict, str, str]],
        output_dir: str,
        output_name: str = "laminar_overlay.r",
        pos_labels: dict[int, str] | None = None,
        alpha_divisor: float = 2.0,
        thickness_exponent: float = 0.5,
) -> None:
    """Write a ggtree R script that overlays trees from multiple domain-type groups.

    Each group is drawn in its own color; all trees are stacked in one panel
    using patchwork's area() overlay. This is the computed equivalent of
    allsubtypes-forest-byhand.r — same visual logic, trees from the algorithm.

    Alpha is computed from the total tree count so the combined overlay
    approaches opacity. Branch thickness encodes within-group frequency
    (convergence, i.e. how many independent tests produced that span —
    deliberately not family count; see the thickness_exponent docs below
    for why the two are kept separate).

    Args:
        subsets: List of (families, span_family_count, color, tpfx) tuples.
        output_dir: Where to write the R script.
        output_name: R script filename.
        pos_labels: Position number → label. If given, the first tree shows
                    tip labels as 'N\\nName'; all other trees suppress them.
        alpha_divisor: Divides the opacity-matched alpha formula before use.
                       Default 2.0 matches this function's original tuning
                       for the ~20-tree colored multi-group overlay
                       (nyan1308_laminar_overlay.r). Pass 1.0 for a single
                       black all-families overlay to match the density of
                       laminar_conflict_groups.r's Panel ALL (its 69-family
                       alpha of 0.064563 is what (1 - 0.01**(1/69)) / 1
                       gives, not /2).
        thickness_exponent: Power applied to convergence for branch
                       thickness (thickness = max(convergence, 1) **
                       thickness_exponent). 0.5 (sqrt, the default) keeps
                       every span within a ~4x width range for nyan1308
                       (convergence runs 1..19) — deliberately gentle so
                       rare spans stay visible, but it also means a highly
                       convergent span (e.g. [5-17], 10 tests) isn't much
                       thicker than a barely-attested one. Raising this
                       towards 1.0 (linear) spreads the high end out more
                       — 0.75 roughly doubles the width ratio (~8x) without
                       the extremes linear scaling produces (~19x, which
                       reads as "crazy thick" against the sqrt-scaled
                       darkness accumulation). Tune per chart; this does
                       not affect darkness, which is family-count-driven
                       and independent of this parameter (see the
                       convergence-vs-family-count note where strength_vals
                       is computed below).
    """
    n_total = sum(len(fams) for fams, _, _, _ in subsets if fams)
    if n_total == 0:
        return

    # Alpha: chosen so all trees together approach opacity
    alphaval = round((1 - 0.01 ** (1 / n_total)) / alpha_divisor, 6)

    rout_path = os.path.join(output_dir, output_name)
    pdf_path = rout_path[:-2] + ".pdf" if rout_path.endswith(".r") else rout_path + ".pdf"
    all_plot_names: list[str] = []

    with open(rout_path, "w") as rout:
        print("library(ape)", file=rout)
        print("library(ggplot2)", file=rout)
        print("library(ggtree)", file=rout)
        print("library(patchwork)", file=rout)
        print("", file=rout)

        if pos_labels:
            pairs = ", ".join(
                f'"{k}" = "{v}"' for k, v in sorted(pos_labels.items())
            )
            print(f"posLabel <- list({pairs})", file=rout)
            print("", file=rout)

        print(f"alphaval <- {alphaval}", file=rout)
        print("", file=rout)

        for families, span_family_count, color, tpfx in subsets:
            if not families:
                continue

            print(f"# ── {tpfx}: {len(families)} families ──", file=rout)

            for idx, family_set in enumerate(families):
                family_list = sorted(family_set, key=lambda s: s.size, reverse=True)
                parent_map = build_parent_map(family_list)
                children_map = get_children(parent_map)
                root = max(family_list, key=lambda s: s.size)

                newick = span_to_newick(root, children_map) + ";"
                tree_var    = f"{tpfx}tree{idx + 1}"
                grouped_var = f"{tree_var}grouped"
                strength_var = f"{tpfx}smap{idx + 1}"
                plot_var    = f"{tpfx}treeplot{idx + 1}"

                print(f'{tree_var} <- read.tree(text="{newick}")', file=rout)

                sorted_spans = sorted(family_list, key=lambda s: s.left)
                domains_r = [
                    f"{chr(97 + i)} = c({s.left}, {s.right})"
                    for i, s in enumerate(sorted_spans)
                ]
                print(
                    f'{grouped_var} <- groupOTU({tree_var},'
                    f' list({", ".join(domains_r)}))',
                    file=rout,
                )

                # Thickness = convergence (how many independent diagnostic
                # tests produced this span), NOT family count. Darkness comes
                # from the ghost-overlay mechanism itself -- how many of the
                # n_total stacked semi-transparent layers happen to draw a
                # matching segment at that position, which is unavoidably
                # family count (there's no way to vary that per-edge without
                # also disturbing the alpha-accumulation the overlay depends
                # on). Convergence and family count are genuinely different
                # measures of the same span (evidential support vs.
                # structural robustness -- see the Word hypothesis discussion
                # in this module's docstring): [5-17] (Neg1-FV) has the
                # highest convergence of any non-backbone span (n=10 tests)
                # but sits in only 37/69 families, while e.g. [2-22] has
                # convergence n=2 but is in all 69 -- strong on one axis,
                # weak on the other. Using the same family-count-derived
                # value for both thickness and darkness (the previous
                # convention here) collapsed that distinction into one
                # signal shown twice.
                strength_vals = ", ".join(
                    str(round(max(s.convergence, 1) ** thickness_exponent, 4))
                    for s in sorted_spans
                )
                print(f"{strength_var} <- c(0.5, {strength_vals})", file=rout)

                # Suppress tip labels on every tree, but still reserve the same
                # panel space every visible label will need (offset + vjust),
                # so all trees share identical panel bounds when stacked. They
                # are added once below, to the topmost tree, after all edge
                # plots have been assembled.
                #
                # offset=-1 alone (the previous convention here) was verified
                # too small a gap between vertex and box at this box size —
                # measured directly at 39px on a 16x10in/200dpi render, which
                # still reads as touching/overlapping at normal viewing scale.
                # vjust on top of the same offset controls how much further:
                # measured directly on THIS 20x14in canvas (not assumed from
                # the 16x10in random_tree_overlay.py numbers, which don't
                # transfer 1:1 across canvas sizes) at vjust=1.25 (145px),
                # 0.6 (75px), 0.35 (45px) via a true tip marker
                # (geom_tippoint()), giving a close-to-linear ~108px/unit
                # relationship on this canvas. vjust=0.35 was chosen as
                # closer to the vertex than the first (145px) pass while
                # keeping a clearly visible, unambiguous gap. The widened
                # bottom plot.margin keeps vjust's extra downward shift from
                # being clipped at the panel edge.
                #
                # colour=NA, fill=NA is what actually makes this invisible --
                # verified directly with an isolated single-tree test. Two
                # other params that look like they should do it don't:
                # alpha=0 is silently ignored by geom_tiplab(geom="label", ...)
                # in this ggtree version (the label rendered at FULL opacity
                # regardless), and label.size=0 is dropped outright (ggplot2
                # warns "Ignoring unknown parameters: label.size" every run --
                # that warning, seen throughout this project's R output and
                # long assumed harmless noise, was actually reporting this).
                # The visible symptom: every one of the ~69 "invisible"
                # placeholders was rendering in full, at the same reserved
                # position on every tree, so they stacked into what looked
                # like one small extra box (its own bare tip number, no name)
                # peeking out from behind the one real, larger, two-line
                # visible label added afterward -- not fully invisible, just
                # fully covered except at the edges.
                geom_tip = (
                    '  geom_tiplab(geom="label", size=5, angle=0,\n'
                    '    offset=-1, hjust=0.5, vjust=0.35, alpha=0, colour=NA, fill=NA) +'
                )

                print(
                    f'{plot_var} <- ggtree({grouped_var},\n'
                    f'  aes(size=({strength_var}[group])),\n'
                    f'  layout="slanted", ladderize=FALSE,\n'
                    f'  alpha=alphaval, color="{color}") +\n'
                    f'  layout_dendrogram() +\n'
                    f'{geom_tip}\n'
                    f'  theme(panel.background=element_blank(),\n'
                    f'    plot.background=element_blank(),\n'
                    f'    legend.position="none",\n'
                    f'    plot.margin=margin(t=5, r=5, b=25, l=5, unit="pt")) +\n'
                    f'  scale_size_identity()',
                    file=rout,
                )
                print("", file=rout)

                all_plot_names.append(plot_var)

        n_plots = len(all_plot_names)
        last_plot = all_plot_names[-1]
        if pos_labels:
                print(
                    f'{last_plot} <- {last_plot} + geom_tiplab(geom="label", size=6, angle=0,\n'
                '  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,\n'
                '  aes(label=paste(label, posLabel[label], sep="\\n")), lineheight=1)',
                file=rout,
            )
        else:
                print(
                    f'{last_plot} <- {last_plot} + geom_tiplab(geom="label", size=6, angle=0,\n'
                '  offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0, lineheight=1)',
                file=rout,
            )
        print("", file=rout)
        print("treelayout <- c(", file=rout)
        for _ in range(n_plots - 1):
            print("  area(t=1, l=1, b=5, r=1),", file=rout)
        print("  area(t=1, l=1, b=5, r=1))", file=rout)
        print("", file=rout)

        joined = " +\n  ".join(all_plot_names)
        print(
            f"forest <- (\n  {joined} +\n  plot_layout(design=treelayout))",
            file=rout,
        )
        bg_theme = "theme(plot.background=element_rect(fill='white', color=NA))"
        print(
            f'ggsave("{pdf_path}", forest & {bg_theme}, width=20, height=14)',
            file=rout,
        )
        # The domain-type color legend only means something when more than one
        # colored group actually contributed trees -- a single-group (e.g. one
        # black "all families" overlay) has no color variation for a legend to
        # explain, and showing all 5 domain-type colors regardless would be
        # actively misleading (implying colors that don't appear anywhere).
        # For that single-group case, a darkness/thickness legend is the
        # meaningful one instead: both encode the same quantity (how many of
        # the n_total families share a span), so one legend explains both.
        used_groups = sum(1 for fams, _, _, _ in subsets if fams)
        legend_pdf_path = pdf_path[:-4] + "_legend.pdf" if pdf_path.endswith(".pdf") else pdf_path + "_legend.pdf"
        if used_groups > 1:
            print("", file=rout)
            print("legend_data <- data.frame(", file=rout)
            print('  Domain_Type = factor(c("morphosyntactic", "tonosegmental", "length", "phonological", "intonational"),', file=rout)
            print('    levels=c("morphosyntactic", "tonosegmental", "length", "phonological", "intonational")),', file=rout)
            print("  x=1, y=1", file=rout)
            print(")", file=rout)
            print("legend_plot <- ggplot(legend_data, aes(x=x, y=y, color=Domain_Type)) +", file=rout)
            print("  geom_point(size=3, alpha=0) +", file=rout)
            print('  scale_color_manual(values=c(morphosyntactic="#BC3C29", tonosegmental="#0072B5", length="#E18727", phonological="#20845E", intonational="#7876B1"),', file=rout)
            print('    name="Domain type") +', file=rout)
            print('  guides(color=guide_legend(override.aes=list(alpha=1))) +', file=rout)
            print("  theme_void() + theme(legend.position=\"inside\", legend.position.inside=c(0.02, 0.98), legend.justification=c(\"left\", \"top\"), legend.direction=\"vertical\",", file=rout)
            print("    legend.background=element_rect(fill=\"white\", color=\"black\", linewidth=0.5),", file=rout)
            print("    legend.text=element_text(size=26), legend.title=element_text(size=28, face=\"bold\"),", file=rout)
            print("    legend.key.height=unit(2.2, \"lines\"), legend.key.width=unit(1.2, \"lines\"),", file=rout)
            print("    legend.spacing.y=unit(0.45, \"in\"), legend.margin=margin(18, 20, 18, 20),", file=rout)
            print("    plot.margin=margin(8, 8, 8, 8))", file=rout)
            print("legend_version <- forest + inset_element(legend_plot, left=0.002, bottom=0.55, right=0.40, top=0.97, align_to=\"panel\", on_top=TRUE)", file=rout)
            print(
                f'ggsave("{legend_pdf_path}", legend_version, width=20, height=14)',
                file=rout,
            )
        elif used_groups == 1:
            # One compact, bordered legend box, inset in the top-left corner
            # -- not a side panel. A side panel (the previous version here)
            # guarantees no overlap but permanently costs canvas width and
            # only suits this one script; a boxed corner inset is the more
            # ordinary convention (matches the domain-type legend above) and
            # generalizes better across languages/canvas sizes, provided its
            # bounds are chosen conservatively. The very first inset attempt
            # overlapped real tree content because its bounds (up to 42% of
            # panel width) crossed where the outer envelope's diagonal
            # actually sits; this one stays narrow (27% width) with a bottom
            # bound well clear of that diagonal at that width, checked
            # directly against a render before shipping, not just estimated.
            #
            # Two sections (darkness, thickness), no numbers in the text at
            # all -- no family/test counts, no n_total -- so the same legend
            # reads correctly for any language's tree set without
            # regeneration-specific wording. "Trees," not "families," in the
            # visible text -- a maximal laminar family IS a tree (see this
            # module's own docstring), and "trees" is the term a linguist
            # reading this chart will expect. Each swatch pair still renders
            # at the real formula (composited alpha for darkness, sqrt for
            # thickness) using this run's own actual data range; only the
            # *labels* are generic ("More"/"Fewer"). Header size=7, no bold
            # (bold at a small size read as heavier than intended once the
            # font itself got bigger), tightened margins, and a heavier
            # border (linewidth=1.2, was 0.6) per direct feedback on the
            # first version's styling.
            all_spans_seen: set = set()
            for fams, _, _, _ in subsets:
                for fam in fams:
                    all_spans_seen.update(fam)
            max_conv = max((s.convergence for s in all_spans_seen), default=1)

            dark_hi = round(1 - (1 - alphaval) ** n_total, 6)
            # dark_lo is deliberately NOT the real single-layer alphaval
            # (e.g. ~0.065 for n_total=69) -- at that opacity the "Fewer"
            # swatch was reported as nearly invisible. This legend is already
            # schematic (a qualitative More/Fewer key, not a precise n/n_total
            # readout, per earlier feedback), so the swatch doesn't need to
            # match one specific layer's real opacity -- it needs to read
            # clearly as "the lighter end of the gradient" without vanishing.
            # A fixed, visibly-legible-but-still-clearly-lighter value serves
            # that better than the true formula would here.
            dark_lo = 0.4
            thick_hi = round(max_conv ** 0.5, 4)
            thick_lo = round(1 ** 0.5, 4)

            print("", file=rout)
            print("legend_header_data <- data.frame(", file=rout)
            print("  y = c(7, 3.65),", file=rout)
            print('  label = c("Darkness: Trees sharing span",', file=rout)
            print('    "Thickness: Tests supporting span")', file=rout)
            print(")", file=rout)
            print("legend_swatch_data <- data.frame(", file=rout)
            print("  y = c(6.0, 5.15, 2.65, 1.8),", file=rout)
            print(f"  alpha_val = c({dark_hi}, {dark_lo}, 1, 1),", file=rout)
            print(f"  lw = c(3, 3, {thick_hi}, {thick_lo}),", file=rout)
            print('  label = c("More", "Fewer", "More", "Fewer")', file=rout)
            print(")", file=rout)
            print(
                "legend_plot <- ggplot() +\n"
                "  geom_text(data=legend_header_data, aes(x=0, y=y, label=label),\n"
                '    hjust=0, size=7) +\n'
                "  geom_segment(data=legend_swatch_data,\n"
                "    aes(x=0, xend=0.9, y=y, yend=y, alpha=alpha_val, linewidth=lw),\n"
                '    color="black", lineend="round") +\n'
                "  geom_text(data=legend_swatch_data, aes(x=1.05, y=y, label=label),\n"
                "    hjust=0, size=5.8) +\n"
                "  scale_alpha_identity() + scale_linewidth_identity() +\n"
                "  xlim(0, 4.9) + ylim(1.3, 7.5) +\n"
                "  theme_void() +\n"
                '  theme(plot.background=element_rect(fill="white", color="black", linewidth=1.2),\n'
                "    plot.margin=margin(6, 8, 6, 6))",
                file=rout,
            )
            print(
                f'legend_version <- (forest & {bg_theme}) + inset_element(legend_plot,\n'
                '  left=0.01, bottom=0.67, right=0.27, top=0.97,\n'
                '  align_to="panel", on_top=TRUE)',
                file=rout,
            )
            print(
                f'ggsave("{legend_pdf_path}", legend_version, width=20, height=14)',
                file=rout,
            )

    print(f"\nR overlay script written to: {rout_path}")


def run_domain_overlay(
        domain_file: str = "domains_nyan1308.tsv",
        domains_dir: str | None = None,
        output_dir: str | None = None,
        overlay_groups: list | None = None,
        pos_labels: dict[int, str] | None = None,
        output_name: str | None = None,
        alpha_divisor: float = 2.0,
        thickness_exponent: float = 0.5,
) -> None:
    """Run laminar analysis per domain type and write a combined colored overlay.

    Each domain type is analyzed independently (Bron-Kerbosch); all trees are
    overlaid in one panel, colored by domain type. Computed equivalent of
    allsubtypes-forest-byhand.r.

    n_positions is derived from the full unfiltered dataset so subset analyses
    always produce trees spanning the complete planar structure — even when a
    subset's spans don't reach the last position (e.g. tonosegmental stops at 17).

    Pass overlay_groups=[(None, "black", tpfx)] for a single unfiltered
    all-families overlay instead of one colored group per domain type (e.g.
    nyan1308_all_families_labeled.r, the labeled equivalent of
    laminar_conflict_groups.r's Panel ALL) — with alpha_divisor=1.0 to match
    that panel's density; see generate_r_overlay_script()'s alpha_divisor doc.

    thickness_exponent: passed straight through to generate_r_overlay_script()
    — see its docstring. Left at 0.5 (sqrt) by default for the colored
    multi-domain-type overlay; nyan1308_all_families_labeled.r is generated
    with 0.75 to make high-convergence spans more visually distinct without
    the extremes linear scaling would produce (see that call site).
    """
    if domains_dir is None:
        domains_dir = os.path.join(os.path.dirname(__file__), "..", "..", "domains")
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "results")
    if overlay_groups is None:
        overlay_groups = OVERLAY_GROUPS
    if pos_labels is None and "nyan1308" in domain_file:
        pos_labels = _NYAN1308_POS_LABELS
    if output_name is None:
        lang_id = domain_file.replace("domains_", "").replace(".tsv", "")
        output_name = f"{lang_id}_laminar_overlay.r"

    # True n_positions from the full dataset — not derived from any subset
    _, n_positions = load_spans(domain_file, domains_dir)
    print(f"\n═══ Domain overlay: {domain_file} ({n_positions} positions) ═══")

    subsets = []
    for type_filter, color, tpfx in overlay_groups:
        print(f"\n── {tpfx} ({color}) ──")
        spans, _ = load_spans(domain_file, domains_dir, subset=type_filter)
        if not spans:
            print("   No spans — skipping.")
            continue
        print(f"   {len(spans)} unique spans")
        adjacency = find_conflicts(spans)
        families, truncated = enumerate_maximal_laminar_families(
            spans, adjacency, n_positions,
        )
        if truncated:
            print(f"   WARNING: enumeration halted at {MAX_FAMILIES} families.")
        else:
            print(f"   {len(families)} maximal families")
        span_family_count: dict[Span, int] = defaultdict(int)
        for fam in families:
            for s in fam:
                span_family_count[s] += 1
        subsets.append((families, dict(span_family_count), color, tpfx))

    generate_r_overlay_script(
        subsets, output_dir, output_name, pos_labels, alpha_divisor, thickness_exponent)


# ══════════════════════════════════════════════════════════════════════════════
# Exemplary trees: a handful of representative families, each paired with the
# pooled plot of just the tests that produced it
# ══════════════════════════════════════════════════════════════════════════════

def select_representative_families(
        families: list[frozenset[Span]],
        span_family_count: dict[Span, int],
        k: int = 6,
) -> list[frozenset[Span]]:
    """Greedy-coverage selection of k structurally diverse, consensus-leaning families.

    Neither of the two selection ideas already named elsewhere in this project
    exists as code: "structurally diverse representatives... by greedy
    coverage" (laminar_conflict_groups.r's Panels B/C) and "most consensus-like
    family" (laminar_four_trees.r) are both described in visualizations.md and
    visible in those scripts' output, but the functions that produced them
    aren't in this file or anywhere else in scripts/ -- checked directly, not
    assumed. This combines both ideas into one function instead of leaving the
    gap twice: repeatedly pick the family that adds the most spans not yet
    shown by an already-selected family (diversity), breaking ties by highest
    total span_family_count among the tied candidates (consensus). Once every
    span is already covered by some selected family (there are only 26 unique
    spans in nyan1308's data but 69 families, so this happens well before
    k trees are picked), every remaining candidate ties at zero new coverage
    and the tiebreak alone decides the rest -- which degrades gracefully into
    pure "most consensus-like" selection, not an error case.
    """
    remaining = list(families)
    covered: set[Span] = set()
    selected: list[frozenset[Span]] = []
    for _ in range(min(k, len(remaining))):
        def _new_coverage(fam: frozenset[Span]) -> int:
            return len(fam - covered)

        def _consensus_score(fam: frozenset[Span]) -> int:
            return sum(span_family_count.get(s, 0) for s in fam)

        best = max(remaining, key=lambda fam: (_new_coverage(fam), _consensus_score(fam)))
        selected.append(best)
        covered |= best
        remaining.remove(best)
    return selected


def generate_r_exemplary_trees_script(
        selected: list[frozenset[Span]],
        n_total: int,
        output_dir: str,
        output_name: str = "nyan1308_exemplary_trees.r",
        pos_labels: dict[int, str] | None = None,
) -> None:
    """Write an R script producing, per selected family: a print file (clean
    tree next to the pooled plot of just the tests that produced it) and a
    pair of 16:9 slide files (tree alone, evidence alone -- see below for
    why they're not combined).

    Reuses df.plot()/constituency.plot() from domain_charts-cgpt.r via
    source() rather than reimplementing the pooled-plot logic in
    Python-generated R -- that function is the single source of truth for
    what a pooled plot looks like (colors, layer numbering, legend behavior),
    and it's hand-maintained directly in scripts/ (see that file's own
    docstring), not something this generator should fork a second copy of.
    One side effect worth knowing: source()-ing that file re-runs it end to
    end, which re-saves all the standard pooled-plot PDFs it already
    produces (nyan1308_pooled_plot.pdf and friends) as a side effect of
    generating this one. Harmless (same data in, same data out -- it's
    idempotent) but worth knowing about if this script's run time or file
    timestamps look surprising.

    One file per exemplar, NOT one combined page -- a first version tried
    to fit all 6 trees and pooled plots into one shared page with shrunk
    rows, and the result was illegible in both directions at once:
    overlapping tree label boxes, and 40-plus test-label rows stacked into a
    few cm of vertical space. Confirmed directly by rendering it, not
    assumed. Each exemplar gets its own full-size page instead.

    Tree and pooled plot are placed side by side (`|`), not stacked -- each
    keeps the dimension it actually needs: the tree keeps the same
    ~20in-equivalent width (51cm) proven elsewhere in this module for 22
    boxed labels, and the pooled plot keeps domain_charts-cgpt.r's own
    untouched per-test height (plot_height()'s max(7, n*0.7) cm). Side by
    side, patchwork gives both panels the pooled plot's height, which can
    make a low-test-count tree panel taller than it needs -- but that just
    adds blank space around a normally-proportioned tree, unlike the earlier
    shared-row version where BOTH panels were squeezed below what either
    needed.
    """
    k = len(selected)
    if k == 0:
        return

    if pos_labels is None:
        pos_labels = _NYAN1308_POS_LABELS
    named = bool(pos_labels)

    rout_path = os.path.join(output_dir, output_name)
    base_pdf_path = rout_path[:-2] if rout_path.endswith(".r") else rout_path

    with open(rout_path, "w") as rout:
        print("library(ape)", file=rout)
        print("library(ggtree)", file=rout)
        print("library(patchwork)", file=rout)
        print("", file=rout)
        # df.plot(), constituency.plot(), group.colors, `tests`, `b`, `o` all
        # come from here -- see this function's docstring for why source()
        # rather than a reimplementation. Requires being run with the
        # planars/ repo root as the working directory, same as
        # domain_charts-cgpt.r's own documented usage -- here::here()
        # resolves relative to cwd, not this script's file location, and
        # resolves to the wrong place (a doubled NonCollaborative/NonCollaborative
        # path) if run from inside scripts/ or scripts/analysis/.
        print('source(here::here("NonCollaborative", "scripts", "domain_charts-cgpt.r"))', file=rout)
        print("", file=rout)

        if named:
            pos_label_entries = ", ".join(
                f'"{i}" = "{label}"' for i, label in enumerate(
                    [pos_labels[i] for i in sorted(pos_labels)], 1)
            )
            print(f"posLabel <- list({pos_label_entries})", file=rout)
            print("", file=rout)

        for idx, family_set in enumerate(selected, 1):
            family_list = sorted(family_set, key=lambda s: s.size, reverse=True)
            parent_map = build_parent_map(family_list)
            children_map = get_children(parent_map)
            root = max(family_list, key=lambda s: s.size)
            newick = span_to_newick(root, children_map) + ";"

            tree_var = f"ex_tree{idx}"
            tp_var = f"ex_tp{idx}"
            print(f'{tree_var} <- read.tree(text="{newick}")', file=rout)
            if named:
                print(
                    f'{tp_var} <- ggtree({tree_var}, layout="slanted", ladderize=FALSE) +\n'
                    "  layout_dendrogram() +\n"
                    '  geom_tiplab(geom="label", size=5, angle=0,\n'
                    "    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,\n"
                    '    aes(label=paste(label, posLabel[label], sep="\\n")), lineheight=1) +\n'
                    "  theme(panel.background=element_blank(),\n"
                    '    plot.background=element_blank(), legend.position="none",\n'
                    '    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))',
                    file=rout,
                )
            else:
                print(
                    f'{tp_var} <- ggtree({tree_var}, layout="slanted", ladderize=FALSE) +\n'
                    "  layout_dendrogram() +\n"
                    '  geom_tiplab(size=5, angle=0, offset=-1, hjust=0.5, vjust=0.35) +\n'
                    "  theme(panel.background=element_blank(),\n"
                    '    plot.background=element_blank(), legend.position="none",\n'
                    '    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))',
                    file=rout,
                )

            # The exact test rows that produced this family's spans -- Span's
            # own .labels field (set in load_spans()) carries the original
            # Test_Labels, so this is a direct filter, not a re-derivation.
            #
            # Filtered from the already-numbered `tests_plot` (global layer
            # numbers, matching nyan1308_pooled_plot.pdf), NOT re-run through
            # df.plot() on a fresh subset -- the latter renumbers layers
            # locally from 1 for whatever's in the subset, same issue the
            # "_global_layers" pooled-chart variants were already built to
            # avoid (see domain_charts-cgpt.r's own
            # tests_plot_<type>_global pattern, which this mirrors exactly).
            # Local numbering would make "layer 3" here mean something
            # different than "layer 3" in the main pooled plot or in a
            # different exemplar's panel; global numbering keeps one
            # consistent numbering everywhere.
            test_labels = sorted({label for s in family_list for label in s.labels})
            labels_r = ", ".join(f'"{lbl}"' for lbl in test_labels)
            plot_var = f"ex_plot{idx}"
            print(f'{plot_var}_data <- filter(tests_plot, Test_Labels %in% c({labels_r}))', file=rout)
            print(f"{plot_var} <- constituency.plot({plot_var}_data, b, o)", file=rout)
            print("", file=rout)

            page_var = f"ex_page{idx}"
            # Side by side (tree | pooled plot), not stacked. Tree keeps the
            # same ~20in-equivalent width (51cm) it needed when it had the
            # full page to itself, so its 22 boxed labels stay legible; the
            # pooled panel keeps domain_charts-cgpt.r's own per-test height
            # (max(7, n_tests*0.7) cm) since that's what keeps ITS labels
            # legible, and shares that height with the tree column
            # (patchwork gives side-by-side panels equal row height) even
            # though the tree itself doesn't need that much vertical room --
            # unlike a shared shrunk row, neither panel loses legibility here,
            # since the constraint each panel actually needs (tree: width,
            # pooled plot: height) is still what it gets.
            tree_width_cm = 51.0
            pooled_width_cm = 25.0
            pooled_height_cm = max(7.0, len(test_labels) * 0.7)
            print(
                f"{page_var} <- ({tp_var} | {plot_var}) +\n"
                f"  plot_layout(widths=c({tree_width_cm}, {pooled_width_cm}))",
                file=rout,
            )
            total_width = round(tree_width_cm + pooled_width_cm, 1)
            pdf_path = f"{base_pdf_path}_{idx}.pdf"
            print(
                f'ggsave("{pdf_path}", {page_var}, device="pdf",\n'
                f"  width={total_width}, height={round(pooled_height_cm, 2)}, "
                'units="cm", limitsize=FALSE)',
                file=rout,
            )
            print("", file=rout)

            # --- Slide variant: tree at a fixed 13.333x7.5in (1920x1080
            # @144dpi, the standard PowerPoint 16:9 size); evidence reuses
            # the SAME per-test, global-layer-numbered plot_var built above
            # for the combined print file -- not a separate aggregated
            # summary. An earlier version here built a one-row-per-span
            # summary (a test count per span instead of every test) to fit a
            # fixed slide height, since the busiest family runs to 59 test
            # rows. That was the wrong call: per explicit correction, "all
            # tests" is the wanted content, and showing a count instead of
            # the actual tests reads as data going missing, not as a
            # deliberate simplification -- especially once its per-span
            # numbering (test counts) sat next to the print file's per-test
            # global layer numbers and looked like a second, inconsistent
            # numbering scheme, not two views of the same thing. Reusing
            # plot_var directly keeps this slide file automatically
            # consistent with the print file (same object, same numbers,
            # same tests) with no second implementation to drift out of
            # sync -- at the cost of the evidence slide's height varying by
            # family (matching plot_var's own proven cm sizing) rather than
            # staying fixed at 7.5in like the tree slide.
            # size=4.6 + a smaller label.padding than the ggplot2 default
            # (0.25 lines) -- the print tree's own 5/default-padding boxes
            # never overlap (checked directly: it has ~20in for these same
            # 22 labels), but at the slide tree's narrower 13.333in, the
            # last two boxes (21 Obj2, 22 PostObj) butted borders/slightly
            # crossed at every size tried down to 5 with default padding.
            # Diagnosed by inspecting the actual panel coordinate ranges
            # (ggplot_build()) before guessing further: confirmed the panel
            # expansion itself was NOT asymmetric in a way that explains it
            # (scale_y_continuous(expand=...) made left/right expansion
            # symmetric but the 21/22 pair still touched), so the fix is
            # shrinking the boxes themselves (font + padding together),
            # verified by rendering the full 22-label row at this exact
            # combination and finding a clean gap everywhere, not just at
            # the one pair that prompted the check.
            slide_tp_var = f"ex_slide_tp{idx}"
            if named:
                print(
                    f'{slide_tp_var} <- ggtree({tree_var}, layout="slanted", ladderize=FALSE) +\n'
                    "  layout_dendrogram() +\n"
                    '  geom_tiplab(geom="label", size=4.6, angle=0,\n'
                    "    offset=-1, hjust=0.5, vjust=0.35, alpha=1, label.size=0,\n"
                    '    label.padding=unit(0.12, "lines"),\n'
                    '    aes(label=paste(label, posLabel[label], sep="\\n")), lineheight=1) +\n'
                    "  theme(panel.background=element_blank(),\n"
                    '    plot.background=element_blank(), legend.position="none",\n'
                    '    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))',
                    file=rout,
                )
            else:
                print(
                    f'{slide_tp_var} <- ggtree({tree_var}, layout="slanted", ladderize=FALSE) +\n'
                    "  layout_dendrogram() +\n"
                    '  geom_tiplab(size=4.6, angle=0, offset=-1, hjust=0.5, vjust=0.35) +\n'
                    "  theme(panel.background=element_blank(),\n"
                    '    plot.background=element_blank(), legend.position="none",\n'
                    '    plot.margin=margin(t=10, r=10, b=25, l=10, unit="pt"))',
                    file=rout,
                )

            # Two slides, not one combined frame -- tested putting both
            # panels on one 13.333x7.5in slide at several width splits
            # (roughly even, then 9.7/3.6) and neither panel was legible at
            # either split. Tested the tree alone at the full 13.333in width
            # and it fit cleanly (confirmed by rendering, not assumed) --
            # there just isn't room left for a second panel beside it once
            # the tree has the width its 22 boxed labels actually need. Two
            # full-frame slides (tree, then its evidence) also matches how a
            # talk would actually present this -- show the tree, then show
            # what supports it -- rather than compressing both into one busy
            # slide.
            slide_tree_pdf_path = f"{base_pdf_path}_slide_{idx}_tree.pdf"
            print(
                f'ggsave("{slide_tree_pdf_path}", {slide_tp_var}, device="pdf",\n'
                '  width=13.333, height=7.5, units="in", limitsize=FALSE)',
                file=rout,
            )
            # Same object, same sizing as the print file's pooled panel
            # (plot_var / pooled_width_cm / pooled_height_cm, built above) --
            # not resized to 13.333x7.5in like the tree slide. Forcing it
            # into a fixed 7.5in height is exactly what motivated the
            # (rejected) aggregated-summary version; keeping its own proven
            # per-test cm sizing is what keeps every test legible here.
            slide_evidence_pdf_path = f"{base_pdf_path}_slide_{idx}_evidence.pdf"
            print(
                f'ggsave("{slide_evidence_pdf_path}", {plot_var}, device="pdf",\n'
                f'  width={pooled_width_cm}, height={round(pooled_height_cm, 2)}, '
                'units="cm", limitsize=FALSE)',
                file=rout,
            )
            print("", file=rout)

    print(f"\nR script written to: {rout_path}")
    print(f"Produces {k} print files: {base_pdf_path}_1.pdf .. {base_pdf_path}_{k}.pdf")
    print(f"Produces {k} slide pairs: {base_pdf_path}_slide_1_tree.pdf / _evidence.pdf .. "
          f"{base_pdf_path}_slide_{k}_tree.pdf / _evidence.pdf")


def generate_exemplary_trees(
        domain_file: str = "domains_nyan1308.tsv",
        domains_dir: str | None = None,
        output_dir: str | None = None,
        pos_labels: dict[int, str] | None = None,
        k: int = 6,
        output_name: str = "nyan1308_exemplary_trees.r",
        include_sparsest: bool = False,
) -> None:
    """Select k representative families and write their tree+pooled-plot R script.

    The one call that ties select_representative_families() and
    generate_r_exemplary_trees_script() together -- load the full unfiltered
    span set (not per-domain-type; this picks across all 69 families), find
    conflicts, enumerate, select, generate.

    include_sparsest: append one more family beyond the k selected by
    coverage/consensus -- specifically the family drawing on the fewest
    individual tests (ties broken by fewest distinct domain types, though
    for nyan1308 the two criteria agree exactly: family 67 in enumeration
    order is the unique minimum on both at once, 21 tests / 3 domain types,
    not just the smaller of two different answers). The greedy-coverage
    selection has no reason to pick the sparsest family on its own --
    coverage/consensus favor families that explain a lot, and a sparse
    family by definition doesn't -- so this is a deliberate second axis
    (least evidence) alongside the first (most representative), not
    something k=7 on the main selection would surface.
    """
    if domains_dir is None:
        domains_dir = os.path.join(os.path.dirname(__file__), "..", "..", "domains")
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "results")
    if pos_labels is None and "nyan1308" in domain_file:
        pos_labels = _NYAN1308_POS_LABELS

    spans, n_positions = load_spans(domain_file, domains_dir)
    adjacency = find_conflicts(spans)
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    print(f"\n═══ Exemplary trees: {domain_file} ({len(families)} families) ═══")

    span_family_count: dict[Span, int] = defaultdict(int)
    for fam in families:
        for s in fam:
            span_family_count[s] += 1

    selected = select_representative_families(families, dict(span_family_count), k=k)
    print(f"   Selected {len(selected)} representative families")

    if include_sparsest:
        def _sparsity_key(fam: frozenset[Span]) -> tuple[int, int]:
            n_tests = len({label for s in fam for label in s.labels})
            n_domains = len({dt for s in fam for dt in s.domain_types})
            return (n_tests, n_domains)

        sparsest = min(families, key=_sparsity_key)
        if sparsest not in selected:
            selected = selected + [sparsest]
            n_tests, n_domains = _sparsity_key(sparsest)
            print(f"   Added sparsest family: {len(sparsest)} spans, "
                  f"{n_tests} tests, {n_domains} domain types")
        else:
            print("   Sparsest family already among the selected representatives")

    generate_r_exemplary_trees_script(
        selected, len(families), output_dir, output_name, pos_labels)


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

def main(domain_file: str = "domains_nyan1308.tsv",
         domains_dir: str | None = None,
         output_dir: str | None = None,
         subset: list[str] | None = None,
         color: str = "black",
         tpfx: str = "",
         show_trees: bool = True,
         max_trees_to_show: int = 20,
         pos_labels: dict[int, str] | None = None) -> dict:
    """Run the full laminar family analysis for one domain file.

    Args:
        domain_file: TSV filename inside domains_dir.
        domains_dir: Path to the domains/ folder. Defaults to ../../domains/
                     relative to this script's location.
        output_dir:  Where to write the R script. Defaults to CWD.
        subset:      List of Domain_Type strings to include (e.g.
                     ["morphosyntactic"]). None = all types.
        color:       Branch color for the ggtree output.
        tpfx:        Variable-name prefix for R output (e.g. "phon").
        show_trees:  If True, print indented tree structure in Phase 3.
                     Automatically suppressed when n > max_trees_to_show.
        max_trees_to_show: Threshold above which tree bodies are suppressed.
        pos_labels:  Position number -> label, passed straight through to
                     generate_r_script() for boxed "N\\nName" tip labels.
                     Defaults to _NYAN1308_POS_LABELS when domain_file
                     mentions nyan1308, matching run_domain_overlay().

    Returns:
        Dict with keys: spans, adjacency, families, span_family_count,
        n_families, truncated. Useful for programmatic access and testing.
    """
    if output_dir is None:
        output_dir = os.getcwd()
    if pos_labels is None and "nyan1308" in domain_file:
        pos_labels = _NYAN1308_POS_LABELS

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

    # ── Phase 2: enumerate all maximal laminar families ───────────────────────
    print("\nPhase 2 — Enumerating all maximal laminar families (Bron-Kerbosch)")
    families, truncated = enumerate_maximal_laminar_families(spans, adjacency, n_positions)
    n_families = len(families)

    if truncated:
        print(f"           WARNING: enumeration halted at {MAX_FAMILIES} families.")
        print(f"           The conflict structure may be more complex than expected.")
    elif n_families == 1:
        print(f"           Found {n_families} maximal family.")
        print("           → Tree hypothesis: FULLY SUPPORTED (data is perfectly laminar)")
    else:
        print(f"           Found {n_families} maximal families.")

    # ── Phase 3 + 4: build trees and report ──────────────────────────────────
    print("\nPhase 3 — Tree structures")
    span_family_count = report_families(
        families, n_positions, truncated,
        show_trees=show_trees, max_trees_to_show=max_trees_to_show,
    )

    print("\nPhase 4 — Cross-family analysis")
    report_convergence(span_family_count, n_families)

    # ── R output ─────────────────────────────────────────────────────────────
    generate_r_script(families, n_positions, span_family_count,
                      output_dir, tpfx, color, pos_labels)

    return {
        "spans": spans,
        "adjacency": adjacency,
        "families": families,
        "span_family_count": span_family_count,
        "n_families": n_families,
        "truncated": truncated,
    }


if __name__ == "__main__":
    # Default: run on nyan1308 (the language most carefully checked against
    # the earlier treeTraversal.py algorithm).
    main()
    run_domain_overlay()

    # One single-domain-type forest per class -- each domain type analyzed
    # entirely on its own (not overlaid with the others), same colors as
    # OVERLAY_GROUPS above. Writes {tpfx}laminar_forest.r per class into
    # results/, not CWD (main()'s own default) -- kept explicit here so these
    # land next to every other nyan1308_* output.
    _results_dir = os.path.join(os.path.dirname(__file__), "..", "..", "results")
    for subset_types, color, short_tpfx in OVERLAY_GROUPS:
        main(subset=subset_types, color=color,
             tpfx=f"nyan1308_{short_tpfx}_", output_dir=_results_dir)

    # Two-bundle approximation of a morphosyntax/phonology split -- crude on
    # purpose (this project's own diagnostic classes don't map cleanly onto
    # that binary; see the "Morphosyntax/phonology divide hypothesis" in this
    # module's own docstring), grouping phonological+intonational into one
    # pooled analysis and morphosyntactic+tonosegmental+length into the other.
    main(
        subset=["phonological", "intonational"],
        color="#0072B5",
        tpfx="nyan1308_phonologylike_",
        output_dir=_results_dir,
    )
    main(
        subset=["morphosyntactic", "tonosegmental", "length"],
        color="#BC3C29",
        tpfx="nyan1308_syntaxlike_",
        output_dir=_results_dir,
    )
    # Same syntax-like bundle with tonosegmental dropped, to see how much of
    # its structure that domain type alone was contributing.
    main(
        subset=["morphosyntactic", "length"],
        color="#E18727",
        tpfx="nyan1308_syntaxlike_notono_",
        output_dir=_results_dir,
    )

    # All-conflict-groups-stacked overlay: every maximal family in one panel
    # (the labeled equivalent of laminar_conflict_groups.r's Panel ALL), with
    # nyan1308_laminar_overlay.r's boxed position-labeled tips. One unfiltered
    # group (type_filter=None) instead of one color per domain type;
    # alpha_divisor=1.0 matches Panel ALL's density (its 69-family alpha of
    # 0.064563), not the colored overlay's /2 tuning.
    run_domain_overlay(
        overlay_groups=[(None, "black", "all")],
        output_name="nyan1308_all_families_labeled.r",
        alpha_divisor=1.0,
        thickness_exponent=0.75,
    )

    # Six exemplary trees (greedy coverage, tied broken by consensus), plus
    # a 7th: the sparsest family (fewest tests/domain types) in the forest --
    # each paired with the pooled plot of just the tests that produced it.
    generate_exemplary_trees(include_sparsest=True)
