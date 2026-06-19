"""
Verify laminar family algorithms on real Chichewa [nyan1308] data.

VERIFICATION METHODOLOGY:
========================

Two independent algorithms for finding maximal laminar families:

1. EXHAUSTIVE SEARCH
   - Checks all 2^n subsets of observed spans
   - Tests each subset for laminarity (no conflicts between any pair)
   - Identifies which subsets are maximal (cannot be extended)
   - Provably correct but slow: O(2^n × n²)
   - For 26 spans: ~67 million subsets, ~60-90 seconds

2. NETWORKX BRON-KERBOSCH (via complement graph)
   - Key insight: maximal independent sets of conflict graph
     = maximal cliques of complement graph
   - Algorithm: Build G' where edges = non-conflicts, find cliques
   - Uses NetworkX's tested, optimized implementation
   - Much faster: ~seconds
   - Theoretically equivalent to exhaustive search

THEORETICAL FRAMEWORK:
======================

Laminar families = sets of spans with no partial overlaps (conflicts).
Mathematically: maximal independent sets of the conflict graph.

Conflict graph G:
  - Nodes = observed spans
  - Edges = conflicts (partial overlaps)
  - Independent set = set of nodes with no edges = laminar family

Bron-Kerbosch finds CLIQUES (complete subgraphs), not independent sets.
Solution: Work with complement graph G':
  - Nodes = observed spans (same as G)
  - Edges = NON-conflicts (inverse of G)
  - Cliques in G' = independent sets in G = laminar families

This transformation is critical. Without it, naive application of
Bron-Kerbosch to the conflict graph fails.

RESULTS FOR CHICHEWA [nyan1308]:
================================

Data: 26 unique observed spans, 65 conflict pairs, positions 1-22

Expected: Both algorithms should find the same number of maximal families
(strong independent verification).

Actual: Both algorithms find exactly 69 maximal families ✓

See ../docs/VERIFICATION.md for detailed results and theoretical background.
"""

import csv
from itertools import combinations
import networkx as nx

# ============================================================================
# LOAD CHICHEWA DATA
# ============================================================================

def load_chichewa_spans(filepath):
    """Load observed spans from domains_nyan1308.tsv."""
    spans = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            left = int(row['Left_Edge'])
            right = int(row['Right_Edge'])
            spans.append((left, right))

    return list(set(spans))


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def span_to_set(span):
    """Convert (start, end) tuple to set of positions."""
    start, end = span
    return set(range(start, end + 1))


def relationships(span1, span2):
    """Classify relationship between two spans."""
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


# ============================================================================
# ALGORITHM 1: EXHAUSTIVE SEARCH
# ============================================================================

def find_maximal_independent_sets_exhaustive(observed_spans):
    """Find all maximal laminar families via exhaustive search.

    ALGORITHM: Brute-force enumeration
    - Iterate through all 2^n subsets of observed_spans
    - For each subset, test if it's a laminar family (no conflicts)
    - For each laminar family, test if it's maximal (cannot add any other span)
    - Collect and return all maximal families

    COMPLEXITY: O(2^n × n²)
    - For n=26 spans: ~67 million subsets, ~60-90 seconds

    CORRECTNESS: Provably correct (checks all possibilities)

    RETURNS: List of maximal laminar families, where each family is a sorted
             list of spans that can coexist without conflict.
    """
    families = []

    for r in range(len(observed_spans) + 1):
        for subset in combinations(observed_spans, r):
            if not is_laminar_family(list(subset)):
                continue

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
# ALGORITHM 2: NETWORKX BRON-KERBOSCH
# ============================================================================

def find_maximal_independent_sets_bk(spans):
    """Find all maximal laminar families using NetworkX Bron-Kerbosch algorithm.

    ALGORITHM: Complement graph + clique enumeration

    Key insight: Maximal independent sets of conflict graph G
    = Maximal cliques of complement graph G'

    Process:
    1. Build complement graph G': nodes=spans, edges=NON-conflicts
       (In the conflict graph, edges represent conflicts; in the complement,
        edges represent non-conflicts, i.e., pairs that can coexist.)
    2. Find all maximal cliques in G' using NetworkX's Bron-Kerbosch
    3. Each maximal clique is a maximal laminar family

    Contrast with naive approach: If you try to use Bron-Kerbosch directly
    on the conflict graph, it fails because Bron-Kerbosch finds cliques
    (fully connected subgraphs), but the conflict graph has edges
    representing what CANNOT be together. The complement inversion fixes this.

    COMPLEXITY: O(3^(n/3)) worst-case, much faster in practice
    - For n=26 spans: ~seconds

    CORRECTNESS: Uses NetworkX's tested, optimized Bron-Kerbosch

    RETURNS: List of maximal laminar families (same format as exhaustive search)
    """
    # Build complement graph: edges where spans DON'T conflict
    G = nx.Graph()
    G.add_nodes_from(spans)

    for i, s1 in enumerate(spans):
        for s2 in spans[i+1:]:
            if relationships(s1, s2) != 'conflict':
                G.add_edge(s1, s2)

    # Find all maximal cliques in complement = maximal independent sets in conflict
    maximal_cliques = list(nx.find_cliques(G))

    # Convert to sorted lists for comparison
    families = [sorted(list(clique)) for clique in maximal_cliques]
    return families


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("VERIFICATION: Exhaustive Search vs. NetworkX Bron-Kerbosch")
    print("Chichewa [nyan1308]")
    print("=" * 80)

    # Load data
    filepath = '/Users/jcgood/gitrepos/planars/NonCollaborative/domains/domains_nyan1308.tsv'
    spans = load_chichewa_spans(filepath)
    spans_sorted = sorted(spans)

    print(f"\n1. DATA:")
    print(f"   Unique observed spans: {len(spans)}")
    print(f"   Span range: {min(s[0] for s in spans)}-{max(s[1] for s in spans)}")

    # Count conflicts
    conflict_count = 0
    for i, s1 in enumerate(spans):
        for s2 in spans[i+1:]:
            if relationships(s1, s2) == 'conflict':
                conflict_count += 1

    print(f"   Conflict pairs: {conflict_count}")

    # Algorithm 1: Exhaustive search
    print(f"\n2. ALGORITHM 1: Exhaustive Search")
    print(f"   Computing (checking all 2^{len(spans)} ≈ {2**len(spans):,} subsets)...")
    families_exhaustive = find_maximal_independent_sets_exhaustive(spans)
    print(f"   Result: {len(families_exhaustive)} maximal families")

    # Algorithm 2: NetworkX Bron-Kerbosch
    print(f"\n3. ALGORITHM 2: NetworkX Bron-Kerbosch")
    print(f"   Computing...")
    families_bk = find_maximal_independent_sets_bk(spans)
    print(f"   Result: {len(families_bk)} maximal families")

    # Compare
    print(f"\n" + "=" * 80)
    print("VERIFICATION:")
    print("=" * 80)

    if len(families_exhaustive) == len(families_bk):
        print(f"✓ SAME COUNT: {len(families_exhaustive)} families")
    else:
        print(f"✗ DIFFERENT COUNTS: {len(families_exhaustive)} vs {len(families_bk)}")

    # Check if they're the same sets
    families_exhaustive_normalized = [frozenset(f) for f in families_exhaustive]
    families_bk_normalized = [frozenset(f) for f in families_bk]

    if set(families_exhaustive_normalized) == set(families_bk_normalized):
        print(f"✓ IDENTICAL RESULTS: Both algorithms find the same families")
    else:
        print(f"✗ DIFFERENT RESULTS: Algorithms diverge")

    print(f"\n" + "=" * 80)


if __name__ == '__main__':
    main()
