"""
Verify laminar family algorithms on controlled toy data.

PURPOSE: Validate that our algorithm correctly identifies maximal laminar
families by comparing multiple independent approaches on data where we can
manually verify the results.

TOY PROBLEM: 12 positions, 12 observed spans, ~15 conflicts

ALGORITHMS TESTED:
1. Exhaustive search — checks all 2^12=4096 subsets
2. Asymmetric hypergraph — maximal independent sets (same as exhaustive)
3. NetworkX Bron-Kerbosch — cliques of complement graph (fast alternative)
4. Copair hypergraph (Barthélemy) — maximal cliques (for comparison)

EXPECTED RESULTS:
- Algorithms 1, 2, 3: Should all find exactly 5 maximal families ✓
- Algorithm 4: Should find 25 cliques (different problem)

KEY INSIGHT FROM TESTING:
The copair hypergraph approach (Barthélemy's framework) doesn't apply here
because it assumes symmetric splits (phylogenetics). Constituency evidence
is asymmetric: a span provides positive evidence for itself but says nothing
about its complement. Thus we use the complement graph approach (algorithms 1-3).

VALIDATION: When toy results show algorithms 1-3 agreeing on 5 families,
this confirms the methodology is sound before applying to real data.

See ../docs/VERIFICATION.md for theoretical framework.
"""

from itertools import combinations, chain
import networkx as nx

# ============================================================================
# TOY PROBLEM: 6 positions, observed spans with deliberate conflicts
# ============================================================================

POSITIONS = set(range(1, 13))  # {1, 2, ..., 12}

# Observed spans — intermediate complexity toy (12 spans, ~15 conflicts)
# Designed to be larger than the minimal toy but still computationally feasible
OBSERVED_SPANS = [
    (1, 12),   # full span
    (1, 6),    # left half
    (7, 12),   # right half
    (1, 3),    # left-left
    (4, 6),    # left-right
    (7, 9),    # right-left
    (10, 12),  # right-right
    (2, 5),    # partial [1-6], conflicts with [4-6]
    (8, 11),   # partial [7-12], conflicts with [10-12]
    (3, 8),    # crosses midpoint, conflicts with [7-12], [1-6], [4-6], [7-9]
    (2, 3),    # nested in [1-3]
    (11, 12),  # nested in [10-12]
]


# ============================================================================
# PART 1: LAMINAR FAMILIES (spans with no partial overlaps)
# ============================================================================

def span_to_set(span):
    """Convert (start, end) tuple to set of positions."""
    start, end = span
    return set(range(start, end + 1))


def relationships(span1, span2):
    """Classify relationship between two spans.

    Returns: 'nested', 'disjoint', or 'conflict'
    """
    s1 = span_to_set(span1)
    s2 = span_to_set(span2)

    inter = s1 & s2

    if not inter:
        return 'disjoint'
    elif s1 <= s2 or s2 <= s1:
        return 'nested'
    else:
        return 'conflict'


def is_laminar_family(spans):
    """Check if a set of spans forms a laminar family (no partial overlaps)."""
    for i, s1 in enumerate(spans):
        for s2 in spans[i+1:]:
            if relationships(s1, s2) == 'conflict':
                return False
    return True


def find_maximal_laminar_families(observed_spans):
    """Find all maximal laminar families.

    A maximal laminar family is one where:
    - All spans are mutually nested or disjoint (no conflicts)
    - Adding any other observed span would create a conflict
    """
    families = []

    # Check all possible subsets of observed spans
    for r in range(len(observed_spans) + 1):
        for subset in combinations(observed_spans, r):
            if not is_laminar_family(list(subset)):
                continue

            # Check if maximal (can't add any other span)
            is_maximal = True
            for other in observed_spans:
                if other not in subset:
                    extended = list(subset) + [other]
                    if is_laminar_family(extended):
                        is_maximal = False
                        break

            if is_maximal and list(subset) not in families:
                families.append(list(subset))

    return families


# ============================================================================
# PART 2: BARTHÉLEMY'S COPAIR HYPERGRAPH
# ============================================================================

class CopairHypergraph:
    """Barthélemy's copair hypergraph H = (X, ℌ).

    X = set of positions
    ℌ = set of hyperedges (each span A comes with its complement A')
    """

    def __init__(self, positions, observed_spans):
        self.X = positions
        self.observed_spans = observed_spans

        # Build hyperedge set: for each observed span, add it and its complement
        self.hyperedges = []
        for span in observed_spans:
            span_set = span_to_set(span)
            complement = self.X - span_set
            self.hyperedges.append(frozenset(span_set))
            self.hyperedges.append(frozenset(complement))

        # Remove duplicates
        self.hyperedges = list(set(self.hyperedges))

    def is_clique(self, hyperedges_subset):
        """Check if a set of hyperedges forms a clique.

        A clique is a set where each pair has non-empty intersection.
        """
        he_list = list(hyperedges_subset)
        for i, h1 in enumerate(he_list):
            for h2 in he_list[i+1:]:
                if not (h1 & h2):  # intersection is empty
                    return False
        return True

    def is_maximal_clique(self, clique):
        """Check if a clique is maximal (can't add another hyperedge)."""
        if not self.is_clique(clique):
            return False

        for he in self.hyperedges:
            if he not in clique:
                extended = clique | {he}
                if self.is_clique(extended):
                    return False

        return True

    def find_maximal_cliques(self):
        """Find all maximal cliques of the copair hypergraph."""
        cliques = []

        # Check all subsets of hyperedges
        for r in range(len(self.hyperedges) + 1):
            for subset in combinations(self.hyperedges, r):
                subset_set = set(subset)
                if not self.is_clique(subset_set):
                    continue

                if self.is_maximal_clique(subset_set):
                    cliques.append(subset_set)

        # Remove duplicates
        unique_cliques = []
        for c in cliques:
            if c not in unique_cliques:
                unique_cliques.append(c)

        return unique_cliques


def find_maximal_independent_sets_networkx(spans):
    """Find maximal independent sets using NetworkX (Bron-Kerbosch algorithm).

    Maximal independent sets of the conflict graph = maximal cliques of the
    complement graph. We build the complement graph (edges between non-conflicting
    spans) and find maximal cliques using NetworkX's tested implementation.
    """
    # Build complement graph: edges where spans DON'T conflict
    G = nx.Graph()
    G.add_nodes_from(spans)

    for i, s1 in enumerate(spans):
        for s2 in spans[i+1:]:
            if relationships(s1, s2) != 'conflict':  # Include non-conflicting pairs
                G.add_edge(s1, s2)

    # Find all maximal cliques in complement = maximal independent sets in conflict
    maximal_cliques = list(nx.find_cliques(G))

    # Convert to sorted lists for comparison
    families = [sorted(list(clique)) for clique in maximal_cliques]
    return families


class AsymmetricHypergraph:
    """Regular hypergraph with only observed spans (no complements).

    Find maximal independent sets: sets of spans that don't conflict.
    This should directly correspond to maximal laminar families.
    """

    def __init__(self, observed_spans):
        self.hyperedges = observed_spans

    def conflict(self, span1, span2):
        """Check if two spans conflict (partial overlap)."""
        return relationships(span1, span2) == 'conflict'

    def is_independent_set(self, spans):
        """Check if a set of spans has no conflicts."""
        for i, s1 in enumerate(spans):
            for s2 in spans[i+1:]:
                if self.conflict(s1, s2):
                    return False
        return True

    def is_maximal_independent_set(self, spans):
        """Check if an independent set is maximal."""
        if not self.is_independent_set(spans):
            return False

        for other in self.hyperedges:
            if other not in spans:
                extended = list(spans) + [other]
                if self.is_independent_set(extended):
                    return False

        return True

    def find_maximal_independent_sets(self):
        """Find all maximal independent sets."""
        sets = []

        for r in range(len(self.hyperedges) + 1):
            for subset in combinations(self.hyperedges, r):
                if not self.is_independent_set(list(subset)):
                    continue

                if self.is_maximal_independent_set(list(subset)):
                    sets.append(list(subset))

        # Remove duplicates
        unique_sets = []
        for s in sets:
            if s not in unique_sets:
                unique_sets.append(s)

        return unique_sets


# ============================================================================
# PART 3: COMPARISON
# ============================================================================

def format_span(span):
    """Format span tuple as string."""
    return f"[{span[0]}-{span[1]}]"


def format_family(family):
    """Format a laminar family for display."""
    return "{" + ", ".join(format_span(s) for s in sorted(family)) + "}"


def format_clique(clique):
    """Format a clique of hyperedges for display."""
    return "{" + ", ".join(str(sorted(h)) for h in sorted(clique)) + "}"


def main():
    print("=" * 80)
    print("TOY VERIFICATION: Laminar Families vs. Maximal Cliques")
    print("=" * 80)

    print("\n1. OBSERVED SPANS:")
    for span in OBSERVED_SPANS:
        s = span_to_set(span)
        print(f"   {format_span(span)} = {sorted(s)}")

    print("\n2. CONFLICT ANALYSIS:")
    for i, s1 in enumerate(OBSERVED_SPANS):
        for s2 in OBSERVED_SPANS[i+1:]:
            rel = relationships(s1, s2)
            if rel == 'conflict':
                print(f"   CONFLICT: {format_span(s1)} ↔ {format_span(s2)}")

    print("\n3. MAXIMAL LAMINAR FAMILIES:")
    families = find_maximal_laminar_families(OBSERVED_SPANS)
    for i, fam in enumerate(families, 1):
        print(f"   Family {i}: {format_family(fam)}")

    print("\n4. COPAIR HYPERGRAPH:")
    H = CopairHypergraph(POSITIONS, OBSERVED_SPANS)
    print(f"   X = {sorted(POSITIONS)}")
    print(f"   # hyperedges = {len(H.hyperedges)}")
    print(f"   Hyperedges:")
    for he in sorted(H.hyperedges, key=lambda x: (len(x), sorted(x))):
        print(f"      {sorted(he)}")

    print("\n5. MAXIMAL CLIQUES OF COPAIR HYPERGRAPH:")
    cliques = H.find_maximal_cliques()
    for i, clique in enumerate(cliques, 1):
        print(f"   Clique {i}: {len(clique)} hyperedges")
        for he in sorted(clique, key=lambda x: (len(x), sorted(x))):
            print(f"      {sorted(he)}")

    print("\n6. ASYMMETRIC HYPERGRAPH (observed spans only):")
    G = AsymmetricHypergraph(OBSERVED_SPANS)
    print(f"   Hyperedges (observed spans only):")
    for span in sorted(OBSERVED_SPANS):
        print(f"      {format_span(span)}")

    print("\n7. MAXIMAL INDEPENDENT SETS (asymmetric hypergraph):")
    indep_sets = G.find_maximal_independent_sets()
    for i, indep_set in enumerate(indep_sets, 1):
        print(f"   Independent set {i}: {format_family(indep_set)}")

    print("\n8. BRON-KERBOSCH (conflict graph):")
    bk_sets = find_maximal_independent_sets_networkx(OBSERVED_SPANS)
    for i, bk_set in enumerate(bk_sets, 1):
        print(f"   BK set {i}: {format_family(bk_set)}")

    print("\n" + "=" * 80)
    print("COMPARISON:")
    print("=" * 80)
    print(f"# Maximal laminar families:        {len(families)}")
    print(f"# Maximal cliques (copair):        {len(cliques)}")
    print(f"# Maximal independent sets (asym): {len(indep_sets)}")
    print(f"# Bron-Kerbosch sets:              {len(bk_sets)}")

    print("\n--- Correspondence check ---")
    if len(families) == len(cliques):
        print("✓ Laminar families = Copair cliques")
    else:
        print("✗ Laminar families ≠ Copair cliques")

    if len(families) == len(indep_sets):
        print("✓ Laminar families = Asymmetric independent sets")
    else:
        print("✗ Laminar families ≠ Asymmetric independent sets")

    if len(families) == len(bk_sets):
        print("✓ Laminar families = Bron-Kerbosch sets")
    else:
        print("✗ Laminar families ≠ Bron-Kerbosch sets")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
