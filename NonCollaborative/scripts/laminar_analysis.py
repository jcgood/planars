"""
laminar_analysis.py — Constituency domain analysis via laminar family enumeration.

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

MAX_FAMILIES = 500  # safeguard: abort enumeration beyond this count

class _TooManyFamilies(Exception):
    pass


def _bron_kerbosch(R: frozenset, P: frozenset, X: frozenset,
                   adjacency: dict, results: list) -> None:
    """Recursive Bron-Kerbosch for maximal independent sets.

    Maintains three sets:
      R = current independent set (all mutually compatible spans)
      P = candidate spans (compatible with all of R, not yet decided)
      X = excluded spans (compatible with all of R, already processed;
          if X is non-empty at termination, R is not maximal)

    When P and X are both empty, R is a maximal independent set. Report it.

    'Compatible' here means NOT in the conflict graph — i.e., nested or
    disjoint. Conflicting neighbors of a span v are removed from P and X
    when v is added to R.

    Pivoting: choose pivot u from P ∪ X to minimise branching. We pick the
    vertex with the most neighbors in P (maximises pruning).

    Raises _TooManyFamilies after MAX_FAMILIES results to prevent runaway
    enumeration on pathological inputs.
    """
    if not P and not X:
        results.append(frozenset(R))
        if len(results) >= MAX_FAMILIES:
            raise _TooManyFamilies()
        return

    if not P:
        return

    # Pivot: choose u in P ∪ X with the most neighbors in P (most pruning)
    all_candidates = P | X
    pivot = max(all_candidates,
                key=lambda u: len(adjacency.get(u, set()) & P))

    # Expand on vertices in P that do NOT conflict with the pivot.
    # (Conflicting with pivot = pivot is already in X or excluded from this
    # branch, so we only recurse on vertices that don't conflict with pivot —
    # this is the standard Tomita-style pivot optimisation.)
    pivot_conflicts = adjacency.get(pivot, frozenset())
    for v in list(P - pivot_conflicts):
        v_conflicts = adjacency.get(v, frozenset())
        new_P = P & (frozenset(P) - v_conflicts) - {v}
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
                    truncated: bool) -> dict[Span, int]:
    """Print each maximal laminar family as a tree.

    Returns a mapping from span → number of families in which it appears.
    This count is the primary measure of structural robustness: a span
    appearing in all families is present regardless of how conflicts are
    resolved elsewhere in the tree.
    """
    span_family_count: dict[Span, int] = defaultdict(int)

    n = len(families)
    trunc_note = f" (enumeration halted at {MAX_FAMILIES})" if truncated else ""
    print(f"\nMaximal laminar families: {n}{trunc_note}")

    for idx, family_set in enumerate(families):
        family_list = sorted(family_set, key=lambda s: s.size, reverse=True)
        parent_map = build_parent_map(family_list)
        children = get_children(parent_map)
        root = max(family_list, key=lambda s: s.size)

        print(f"\n─── Tree {idx + 1} ({len(family_list)} spans) ───")
        print(format_tree_text(root, children))

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
                      color: str = "black") -> None:
    """Write a ggtree R script for visualising the maximal laminar families.

    Each family produces one proper branching tree (via a correct recursive
    Newick encoder), unlike treeTraversal.py which produced one chain per
    'tree' and overlaid them. Branch thickness is scaled by how many families
    a span appears in (sqrt-scaled to compress the range): spans present in
    all trees appear with the heaviest lines.
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
        Dict with keys: spans, adjacency, families, span_family_count,
        n_families, truncated. Useful for programmatic access and testing.
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
    span_family_count = report_families(families, n_positions, truncated)

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
        "truncated": truncated,
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
