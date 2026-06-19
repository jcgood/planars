# Verification: Laminar Family Enumeration

## Overview

This document explains the verification methodology for laminar family analysis, the theoretical framework, key insights, and verified results.

**Bottom line**: Two independent algorithms (exhaustive search and NetworkX Bron-Kerbosch) both find **69 maximal laminar families** for Chichewa [nyan1308], confirming the analysis is mathematically correct.

## The Problem

Given a set of observed constituency domain spans, find **all maximal laminar families** (sets of spans where every pair is either nested or disjoint — no partial overlaps).

A maximal laminar family is:
- A set of mutually compatible spans (no conflicts)
- That cannot be extended by adding another observed span

Each maximal family represents one valid interpretation of the constituency structure given the observed evidence.

## Theoretical Framework

### Maximal Independent Sets

A **laminar family** (in graph-theoretic terms) is an **independent set of the conflict graph**:
- Nodes = observed spans
- Edges = conflicts (partial overlaps)
- Independent set = set of nodes with no edges between them

A **maximal** independent set cannot be extended by adding another node.

Therefore: **Finding maximal laminar families = Finding maximal independent sets of the conflict graph**

### Complement Graph Transformation

The Bron-Kerbosch algorithm naturally finds **maximal cliques** (fully connected subgraphs), not independent sets.

**Key insight**: A maximal independent set in graph G is a maximal clique in the complement graph G':
- G: conflict graph (edges = conflicts)
- G': complement graph (edges = non-conflicts)
- Independent set in G = Clique in G'

Therefore: To use Bron-Kerbosch to find independent sets, we must:
1. Build the complement graph (add edges where spans DON'T conflict)
2. Find maximal cliques in the complement
3. Each clique is a maximal laminar family

This transformation is critical. Without it, naive application of Bron-Kerbosch fails.

## Verification Approach

### Algorithm 1: Exhaustive Search

**Method**: Check all 2^n subsets
1. For each subset of observed spans
2. Test if it's a laminar family (no conflicts between any pair)
3. If laminar, check if maximal (cannot add any other span without creating a conflict)
4. Collect all maximal families

**Properties**:
- Provably correct (checks all possibilities)
- Slow: O(2^n × n²) per subset check
- For 26 spans: ~67 million subsets, ~60-90 seconds

**Status**: ✓ Mathematically correct, verified on toy and real data

### Algorithm 2: NetworkX Bron-Kerbosch

**Method**: Use NetworkX's `nx.find_cliques()` on complement graph
1. Build complement graph G' where edges = non-conflicts
2. Call `nx.find_cliques(G')` — standard Bron-Kerbosch
3. Each clique returned is a maximal laminar family

**Properties**:
- Uses tested, optimized library implementation
- Efficient: O(3^(n/3)) worst-case, much faster in practice
- For 26 spans: ~seconds

**Status**: ✓ Independent verification via library, agrees with exhaustive search

## Key Mistake & Resolution

### The Broken Approach

Initial attempt: Use Bron-Kerbosch directly on the conflict graph to find independent sets.

**Problem**: 
- Bron-Kerbosch finds cliques (fully connected sets)
- Conflict graph has edges = conflicts
- Trying to find cliques in the conflict graph finds sets of spans that all conflict with each other — the opposite of what we want

**Result**: Only 1 or 12 families returned instead of 69 (on toy and real data respectively)

### The Fix

**Transform the graph before applying Bron-Kerbosch:**
- Build G' = complement of the conflict graph
- In G': edges represent non-conflicts
- Cliques in G' = independent sets in G = laminar families

This is a conceptual shift, not a modification to Bron-Kerbosch itself. The algorithm remains standard; the input is transformed.

## Verified Results

### Toy Example (12 spans, intermediate complexity)

**Data**:
- 12 observed spans
- 15 conflict pairs
- Subset space: 2^12 = 4,096

**Results**:
| Algorithm | Count | Match |
|-----------|-------|-------|
| Exhaustive search | 5 | ✓ |
| Asymmetric hypergraph | 5 | ✓ |
| NetworkX Bron-Kerbosch | 5 | ✓ |
| Copair hypergraph (Barthélemy) | 25 | ✗ (different problem) |

**Conclusion**: Three independent correct algorithms agree on 5 families.

### Chichewa [nyan1308] (26 spans, real linguistic data)

**Data**:
- 26 unique observed spans
- 65 conflict pairs
- Position range: 1-22
- Subset space: 2^26 ≈ 67,108,864

**Results**:
| Algorithm | Count | Time | Match |
|-----------|-------|------|-------|
| Exhaustive search | 69 | ~60-90s | ✓ |
| NetworkX Bron-Kerbosch | 69 | ~5s | ✓ |

**Conclusion**: ✓ Both algorithms find exactly **69 maximal laminar families**

This is **strong independent verification**. Two fundamentally different approaches (exhaustive enumeration vs. complement graph cliques) agree on the same answer.

## Linguistic Interpretation

69 maximal families means:
- The three constituency hypotheses (Tree, Morphosyntax/Phonology divide, Word) are supported but not uniquely determined
- Different subsets of diagnostics suggest different valid domain structures
- Spans appearing in all 69 families are the most robust (candidate word domains)
- Spans in fewer families are contingent on conflict resolution elsewhere

## Files

- `../scripts/verify_barthelmemy_correspondence.py` — Toy verification (12 spans)
- `../scripts/verify_chichewa.py` — Real data verification (26 spans, Chichewa)
- `../scripts/laminar_analysis.py` — Main analysis (uses optimized Bron-Kerbosch approach)

## Related Work

- Semple & Steel (2003) — Phylogenetics trees and compatible splits
- Barthélemy (1989) — "From Copair Hypergraphs to Median Graphs with Latent Vertices"
- Bron & Kerbosch (1973) — "Finding all cliques of an undirected graph"

Note: Copair hypergraphs and median graphs are relevant for phylogenetics (symmetric splits) but do not apply to asymmetric linguistic evidence. The complement graph approach is the correct mapping.
