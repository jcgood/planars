# References: Laminar Families, Tree Representations, and Constituency

This file collects references relevant to the mathematical and linguistic foundations of the tree traversal analysis. Annotations explain why each work is relevant to the project.

---

## Laminar Families: Foundational Combinatorics

**Cunningham, W.H. & Edmonds, J. (1980).** A combinatorial decomposition theory. *Canadian Journal of Mathematics*, 32, 734–765.  
https://www.cambridge.org/core/journals/canadian-journal-of-mathematics/article/combinatorial-decomposition-theory/7D1C38CA2A3408CAFE4490276794AA78  
> Foundational paper on decomposition theory for graphs. Introduces the idea that a connected graph has a unique minimal decomposition representable as a tree; laminar families are the natural structure for encoding such decompositions. The general framework here underlies much subsequent work on tree representations of set systems.

**Schrijver, A. (2003).** *Combinatorial Optimization: Polyhedra and Efficiency* (3 vols.). Springer.  
https://www.amazon.com/Combinatorial-Optimization-3-B-C/dp/3540443894  
> The standard comprehensive reference for combinatorial optimization. Covers laminar families in the context of submodular functions, network flows, and polymatroids. Heavy going but authoritative. Relevant sections: trees, branchings and connectors; submodular functions.

**Wikipedia: Laminar set family.**  
https://en.wikipedia.org/wiki/Laminar_set_family  
> Useful starting point with the formal definition, the tree representation theorem, and pointers to applications. The key result stated here: every laminar family over a finite ground set can be represented as a rooted tree where containment = ancestor/descendant and disjointness = different subtrees.

---

## Tree Representations of Set Families

**Bui-Xuan, B.-M., Habib, M. & Rao, M. (2012).** Tree-representation of set families and applications to combinatorial decompositions. *European Journal of Combinatorics*, 33(5), 688–711.  
https://www.sciencedirect.com/science/article/pii/S0195669811001806  
https://hal.science/hal-00555520 (open access)  
> The most directly relevant mathematical paper. Gives a general framework for representing *any* set family (not just laminar ones) by a tree, and shows how laminar families are the special case where the representation is cleanest. Covers weakly partitive families and union-difference families as generalizations. Good starting point for understanding what goes wrong when spans partially overlap (i.e., when the family is not laminar).

**Ehrenfeucht, A., Harju, T. & Rozenberg, G. (1999).** *The Theory of 2-Structures: A Framework for Decomposition and Transformation of Graphs.* World Scientific.  
> Covers tree-based representations of relational structures on sets, with a focus on graph decomposition. The labeled tree families framework is a generalization of the laminar case. Background reading for the Bui-Xuan et al. paper.

---

## Phylogenetics: Laminar Families as Hierarchies

**Semple, C. & Steel, M. (2003).** *Phylogenetics.* Oxford University Press (Oxford Lecture Series in Mathematics and Its Applications).  
https://global.oup.com/academic/product/phylogenetics-9780198509424  
> The standard mathematical reference for phylogenetic trees. Establishes the 1-to-1 correspondence between rooted phylogenetic trees and *hierarchies* — which are exactly laminar families over a set of taxa (here: positions). Chapter 3 covers cluster systems. Highly relevant because the constituency tree problem in this project is structurally identical to rooted phylogenetic tree reconstruction from a set of clusters.

**Clustering systems of phylogenetic networks (2023).** *Theory in Biosciences.*  
https://pmc.ncbi.nlm.nih.gov/articles/PMC10564800/  
> More recent work extending the Semple & Steel framework to phylogenetic *networks* (which allow partial overlaps — analogous to the partially overlapping spans in this project). Relevant for understanding what happens when the data is not perfectly laminar.

### Splits, compatibility, and the phylogenetic analogy

The "splits" formalism in phylogenetics is the direct biological analog of the laminarity question here. A *split* of a taxon set X is a bipartition {A, B}; two splits are *compatible* if at least one of the four intersections A₁∩A₂, A₁∩B₂, B₁∩A₂, B₁∩B₂ is empty. The **Splits Equivalence Theorem** (proved in Semple & Steel Ch. 3) states that a set of splits is simultaneously representable by a single tree iff every pair of splits is compatible — i.e., iff the family is laminar on the bipartition structure.

Mapping to planars: diagnostic classes ≈ characters, positions ≈ taxa, qualifying positions ≈ one half of the bipartition. The key disanalogy is that planars positions have a linear order (the planar template) that breaks the symmetry of the splits formulation — splits don't care about order, our spans do. But the compatibility question is structurally the same. When splits are not all compatible, the data is better represented by a *splits graph* (phylogenetic network) that shows where conflicts cluster — exactly what `laminar_conflict_groups` is computing.

**Bandelt, H.-J. & Dress, A.W.M. (1992).** Split decomposition: a new and useful approach to phylogenetic analysis of distance data. *Molecular Phylogenetics and Evolution*, 1(3), 242–252.
> Introduced split decomposition as a method for finding the largest compatible sub-family of a set of splits and visualizing the conflict structure of the rest. When the data is not perfectly laminar, split decomposition finds a tree-like "core" and a network periphery — analogous to finding the maximum laminar subfamily and the remaining conflicting spans. *[Fairly confident; verify page numbers.]*

**Huson, D.H. & Bryant, D. (2006).** Application of phylogenetic networks in evolutionary studies. *Molecular Biology and Evolution*, 23(2), 254–267.
> Describes the SplitsTree software and the general "network when not laminar" strategy in biology. Good overview of how the phylogenetics community handles non-tree-compatible data in practice. The circular split systems and neighbor-net algorithm described here have potential structural analogs for the planars conflict visualization problem. *[Fairly confident; verify DOI.]*

---

## Matroids

**Laminar matroids (2017).** *European Journal of Combinatorics.*  
https://dl.acm.org/doi/10.1016/j.ejc.2017.01.002  
> Characterizes the class of matroids definable by laminar families (laminar matroids), including excluded minor characterizations. Useful background if the project ever moves toward independence-system formalizations of constituency, but not immediately necessary.

---

## Counting Constituency Trees: Catalan and Schröder Numbers

**Schröder, E. (1870).** Vier combinatorische Probleme. *Zeitschrift für Mathematik und Physik*, 15, 361–376.  
> The original source for what are now called the little Schröder numbers (OEIS A001003: 1, 1, 3, 11, 45, 197, ...). Schröder posed four combinatorial problems; the relevant one asks how many ways a product of n+1 symbols can be parenthesized, grouping ≥2 factors at a time. This is equivalent to counting rooted ordered (plane) trees with n+1 leaves in which every internal node has ≥2 children — the correct theoretical maximum for laminar families over n positions with arbitrary n-ary branching.

**Stanley, R. P. (1999).** *Enumerative Combinatorics*, Vol. 2. Cambridge University Press.  
> The standard modern reference. The little Schröder numbers appear in Chapter 6 (exercise 6.19 and surrounding discussion) with multiple equivalent interpretations: polygon dissections, parenthesizations, plane tree enumeration. Reliable citation for the tree-counting interpretation.

**Rogers, D. G. (1978).** A Schröder triangle: three combinatorial problems. In: *Combinatorial Mathematics V*, Lecture Notes in Mathematics 622, Springer, 175–196.  
> **Cited with uncertainty — verify before citing formally.** I believe this paper introduces or surveys combinatorial interpretations of the Schröder numbers via a triangular array, but I have not confirmed the exact title, page range, or content. The volume and series are plausible. Check via Springer or MathSciNet before relying on this reference.

### Little vs. large Schröder numbers

Both sequences appear in Schröder's 1870 paper. The exact relationship:

```
n:       0   1   2    3    4    5
little:  1   1   3   11   45  197   (A001003)
large:   1   2   6   22   90  394   (A006318)
ratio:   1   2   2    2    2    2
```

**S(n) = 2 × s(n) for n ≥ 1.** The cleanest explanation is via lattice paths: both count paths from (0,0) to (n,n) using steps East, North, and diagonal Northeast that don't cross above y=x, but little Schröder paths additionally forbid diagonal steps *on* the main diagonal.

In tree terms, the large Schröder numbers are sometimes described as counting the same trees as the little Schröder numbers but also allowing **unary nodes** — internal nodes with exactly one child. A unary node doesn't branch; it's a chain link. Allowing them without bound makes the count infinite (you can always insert another unary node into any chain), so the large Schröder numbers must be constraining unary nodes in some specific way. The precise combinatorial characterization is more subtle in pure tree terms than in the lattice path formulation; **treat the "unary node" description as a heuristic, not a formal definition, until verified against a primary source.**

For linguistics: unary nodes appear in X-bar theory (intermediate projections XP → X' → X), but are absent from strict binary-branching frameworks. The laminar family problem uses little Schröder numbers (no unary nodes) because every internal span must dominate at least two sub-spans or positions.

### Relationship to the laminar family problem

The Catalan numbers (OEIS A000108: 1, 1, 2, 5, 14, 42, ...) count binary-branching ordered trees and are the implicit background assumption in most generative syntax. The little Schröder numbers are the n-ary generalization: A001003(n) counts the number of distinct constituency trees for n ordered positions if every possible contiguous span is observed with no conflicts. For Chichewa (nyan1308, 22 positions), the 69 maximal laminar families found by Bron-Kerbosch are a small fraction of A001003(22). The Schröder/n-ary tree connection does not appear to have been explicitly discussed in the linguistics literature; most work assumes binary branching and cites Catalan numbers implicitly.

Note: OEIS A007052 ("order-consecutive partitions of n") is a related but distinct sequence (1, 3, 10, 34, 116, ...) that counts only trees where every internal node has at least one direct leaf child. See `scripts/catalan.py` for the distinction and the generating function analysis.

---

## Ordered Hypergraphs, Interval Systems, and the Structure of Loose Spans

This section records theoretical observations about how the planars span structure maps onto hypergraph theory. The immediate motivation was the question of whether loose spans are fully arbitrary set systems or have additional mathematical structure.

### The set-system hierarchy

Positions in the planar template are linearly ordered vertices. Spans are hyperedges. The full span set system is not arbitrary — it sits in a well-defined containment hierarchy:

1. **Power set** — fully arbitrary subsets of positions (no constraint)
2. **Interval-dominated** — each hyperedge is a subset of some interval; its convex hull (extent) is always a contiguous interval. Loose spans live here: qualifying positions can have internal gaps, but the extent [leftmost_qualifying, rightmost_qualifying] is always an interval.
3. **Interval hypergraph** — every hyperedge IS an interval (no internal gaps). Strict spans live here.
4. **Laminar family** — intervals that are pairwise nested or disjoint. The Tree hypothesis proposes that diagnostic spans should live here.

"Loosening but not chaos": loose spans are constrained by their extents even when their interiors aren't. They sit strictly between arbitrary set systems and interval hypergraphs.

### The two-layer structure of loose spans

Loose spans decompose naturally into two analytical layers:

- **Extent layer.** The interval [leftmost_qualifying, rightmost_qualifying]. This is always a contiguous interval. *Laminarity lives here*: two loose spans conflict (partially overlap) iff their extents cross, regardless of the gap structure within each extent.
- **Interior layer.** Which positions within the extent actually qualify (the qualifying position set, possibly with gaps). *The Word hypothesis lives here*: whether spans can partition the template into consistently small sub-spans depends on where qualifying positions actually fall, not just on the outer boundaries.

**Practical consequence:** laminarity checking for loose spans reduces to laminarity checking on their extents, which are intervals. The gap structure does not affect conflict detection. This is the same mathematics as for strict spans, just applied to coarser intervals.

### Containment poset and Dilworth's theorem

Ordering spans by containment gives a Hasse diagram (partial order). Its properties:
- **Height** = maximum nesting depth of the span system
- **Maximum antichain size** = maximum number of mutually conflicting spans (those with no containment relation)
- **Dilworth's theorem** connects these: the minimum number of chains (linearly ordered subsets) needed to cover the poset equals the maximum antichain size. This gives a principled measure of how far a language's span structure is from a tree, with a clean algorithmic interpretation.

### VC dimension as a laminarity index

A perfectly laminar family (a tree) has VC dimension 1: no pair of sets can be shattered, since every pair is nested or disjoint. An interval system on a linearly ordered set has VC dimension 2. VC dimension could serve as a scalar summary of deviation from the Tree hypothesis across languages — more grounded than a raw conflict count.

**Caveat:** the precise VC dimension of laminar families vs. interval systems is stated here as a plausible conjecture based on the definitions; verify against a primary source before asserting it in writing.

### References

**Berge, C. (1989).** *Hypergraphs: Combinatorics of Finite Sets.* North-Holland.
> The canonical hypergraph theory textbook. Defines interval hypergraphs and establishes the Helly property: if every two hyperedges in a family have a common element, then all share a common element. Strict spans (being intervals on a linearly ordered set) have this property; loose spans in general do not. Chapter 7 covers interval hypergraphs.

**Booth, K.S. & Lueker, G.S. (1976).** Testing for the consecutive ones property, interval graphs, and graph planarity using PQ-tree algorithms. *Journal of Computer and System Sciences*, 13(3), 335–379.
> Gives the linear-time algorithm for testing whether a set system is an interval hypergraph (the "consecutive ones property"). Relevant if the project ever wants to algorithmically verify that a span set qualifies as strict-span-representable. PQ-trees are the data structure for compactly representing all valid orderings. *[Fairly confident about this citation; verify DOI before citing formally.]*

**Edelman, P.H. & Jamison, R.E. (1985).** The theory of convex geometries. *Geometriae Dedicata*, 19(3), 247–270.
> Convex geometries generalize the notion of "convex sets" on a linearly ordered ground set. The interval sets (strict spans) form a convex geometry; loose spans (subsets of intervals) are related to the feasible sets of *antimatroids*, the dual structure. The "loosening but not chaos" observation above has a formal home in this framework. *[Fairly confident; verify before citing formally.]*

**Vapnik, V.N. & Chervonenkis, A.Ya. (1971).** On the uniform convergence of relative frequencies of events to their probabilities. *Theory of Probability and Its Applications*, 16(2), 264–280.
> Original VC dimension paper. The application to set systems (rather than learning-theoretic contexts) is developed in subsequent literature; see also Blumer et al. (1989), "Learnability and the Vapnik-Chervonenkis dimension," *Journal of the ACM*, 36(4), 929–965. *[Blumer et al. citation is fairly confident; verify page numbers.]*

---

## Partial Orders and the Containment Poset

A *partially ordered set* (poset) is a set equipped with a binary relation ≤ that is reflexive (A ≤ A), antisymmetric (A ≤ B and B ≤ A implies A = B), and transitive (A ≤ B and B ≤ C implies A ≤ C). Unlike a total order (the integers), a partial order does not require every pair to be comparable — two elements can be *incomparable*, meaning neither A ≤ B nor B ≤ A.

Vocabulary:
- **Chain** — a totally ordered subset (every pair is comparable). In the span containment poset: a sequence of nested spans S₁ ⊂ S₂ ⊂ … ⊂ Sₖ.
- **Antichain** — a set of mutually incomparable elements. In the span containment poset: a set of spans where no one contains another. Note this includes *both* crossing spans *and* disjoint spans — incomparability in the containment poset is not the same as conflict.
- **Height** — length of the longest chain (maximum nesting depth of spans).
- **Width** — size of the largest antichain.
- **Hasse diagram** — the standard visual representation: draw an edge from A up to B when A < B with no C strictly between them. The Hasse diagram of the span containment poset is a DAG directly visualizing the nesting structure.

**Dilworth's theorem** (1950): the minimum number of chains needed to *partition* a finite poset equals its width (maximum antichain size). In span terms: the minimum number of chain-families (each a sequence of nested spans) needed to cover all spans equals the size of the largest set of mutually non-nested spans. This gives an upper bound on the minimum number of laminar families needed, since every chain is a laminar family but not vice versa.

**Mirsky's theorem** (1971): the minimum number of antichains needed to partition a poset equals its height (length of the longest chain).

**Caveat on the antichain/conflict distinction:** in the containment poset, an antichain can contain pairs of spans that are *disjoint* (compatible, not conflicting) alongside pairs that *cross* (conflicting). The maximum antichain is therefore not the same as the maximum clique in the conflict graph (see Coloring section), which counts only mutually crossing spans. Dilworth and the chromatic number give different decompositions.

### References

**Dilworth, R.P. (1950).** A decomposition theorem for partially ordered sets. *Annals of Mathematics*, 51(1), 161–166.
> The original proof. Short (6 pages) and readable. The theorem is now a standard result in combinatorics with multiple proof strategies.

**Mirsky, L. (1971).** A dual of Dilworth's decomposition theorem. *American Mathematical Monthly*, 78(8), 876–877.
> One-page proof of the dual: minimum antichain partition = height. *[Fairly confident; verify page numbers.]*

**Davey, B.A. & Priestley, H.A. (2002).** *Introduction to Lattices and Order* (2nd ed.). Cambridge University Press.
> The standard accessible textbook for posets, chains, antichains, Hasse diagrams, and Dilworth's theorem. Good entry point before Schrijver.

---

## Graph Coloring and the Conflict Graph

### The conflict graph and what coloring measures

The *conflict graph* G of a span system has nodes = spans and edges = pairs of *crossing* spans (partially overlapping: neither nested nor disjoint). A *proper coloring* of G assigns colors to nodes so no two adjacent (conflicting) nodes share a color. Each color class is a set of mutually non-crossing spans — i.e., a laminar family. The *chromatic number* χ(G) is the minimum number of colors needed.

**The direct connection to treeness:** χ(G) is the minimum number of laminar families (= trees, via the containment-tree representation) needed to partition the full span system. Therefore:

- χ(G) = 1 ↔ all spans are already laminar ↔ the Tree hypothesis holds outright
- χ(G) = k → the data requires at least k trees to be fully covered
- χ(G) is a principled, scalar measure of deviation from the Tree hypothesis

The user's intuition is correct: coloring and treeness are directly connected via this equivalence.

### The conflict graph is a circle graph

Represent each span [a, b] as a chord connecting point a to point b on a circle (positions on the circle correspond to positions in the planar template, read in order). Two chords cross inside the circle iff their corresponding intervals partially overlap — exactly the conflict condition. So the conflict graph for strict spans (or for loose spans analyzed at the extent level) is a *circle graph*: the intersection graph of a set of chords of a circle.

Circle graphs are a well-studied class with polynomial-time algorithms for maximum clique and maximum independent set (Gavril 1973). They are *not* in general perfect: a 5-cycle (C₅) is a circle graph with χ = 3 but ω = 2, so χ > ω is possible. This means the minimum number of trees needed (χ) can exceed the size of the largest mutually-conflicting set of spans (ω); the two quantities are related but not equal.

**Caveat:** claims about complexity of *coloring* (as opposed to finding the maximum clique) in circle graphs are not verified here — general graph coloring is NP-hard and it is unclear whether the circle graph structure makes it tractable. Flag for verification before asserting.

### Relationship to Dilworth

Dilworth gives the minimum *chain* partition of the containment poset; coloring gives the minimum *laminar family* partition of the full span system. Since every chain is a laminar family but not vice versa, the minimum laminar cover (χ) ≤ minimum chain cover (Dilworth width). The two bounds coincide only when the "slack" spans (disjoint, non-nested pairs) happen not to help — not guaranteed in general.

### Hypergraph coloring (flagged for exploration)

A different coloring: assign colors to *positions* (vertices) such that no span (hyperedge) is monochromatic. This "property B" / hypergraph chromatic number might be relevant to the Word hypothesis — whether positions can be partitioned into color classes that respect span boundaries. Less developed as an application; noted here so the thread is not lost.

### References

**Diestel, R. (2017).** *Graph Theory* (5th ed.). Springer. Free online: diestel-graph-theory.com.
> The standard comprehensive reference. Covers chromatic number, perfect graphs, clique/coloring relationships, and graph classes. Good first stop for any coloring question.

**Golumbic, M.C. (2004).** *Algorithmic Graph Theory and Perfect Graphs* (2nd ed.). Elsevier.
> Covers circle graphs explicitly as a named graph class, including the representation theorem (chords of a circle), the relationship to other graph classes, and algorithms for maximum clique and independent set. The key reference for understanding the structure of the conflict graph.

**Gavril, F. (1973).** Algorithms for a maximum clique and a maximum independent set of a circle graph. *Networks*, 3(3), 261–273.
> Introduced circle graphs as a class and gave polynomial algorithms for maximum clique and independent set. The maximum clique algorithm is what you would use to find ω(G) — the largest set of mutually pairwise-conflicting spans — directly from the span endpoints. *[Fairly confident; verify page numbers before citing formally.]*

**Chudnovsky, M., Robertson, N., Seymour, P. & Thomas, R. (2006).** The strong perfect graph theorem. *Annals of Mathematics*, 164(1), 51–229.
> Proves that a graph is perfect iff it contains no odd hole or odd antihole as an induced subgraph. Circle graphs are *not* perfect in general (they can contain C₅ as an induced subgraph), so this theorem does not apply to our conflict graph directly. Included as the definitive reference on perfect graphs, for background when reasoning about when χ = ω does or does not hold.

---

## Connections to Linguistics

The mathematical literature on laminar families does not, to my knowledge, directly engage with morphosyntactic constituency in the sense used in this project. The closest bridges:

**Phylogenetics** (Semple & Steel above): the problem of reconstructing a tree from observed clusters is formally identical to reconstructing a constituency hierarchy from observed domain spans. The splits compatibility framework is the most direct structural parallel.

**Prosodic phonology** — the closest linguistic bridge. The *prosodic hierarchy* (mora < syllable < foot < prosodic word < phonological phrase < intonational phrase < utterance) is explicitly a laminar structure. Selkirk's *strict layer hypothesis* formalizes this: each category must dominate only categories from the adjacent lower level, with no skipping and no partial overlap. Violations of strict layering are exactly the kind of partial-overlap conflicts studied in this project. The prosodic phonology literature has accumulated substantial discussion of where laminarity breaks down — directly relevant to the Morphosyntax/Phonology divide hypothesis.

**Nespor, M. & Vogel, I. (1986).** *Prosodic Phonology.* Foris Publications.
> The foundational text for prosodic constituency. Proposes that phonological domains form a strict hierarchy — a laminar family. The project's Morphosyntax/Phonology divide hypothesis is in part a claim that phonological spans are more laminar (more tree-like) than morphosyntactic ones; Nespor & Vogel frame this qualitatively, not mathematically.

**Selkirk, E. (1984).** *Phonology and Syntax: The Relation between Sound and Structure.* MIT Press.
> Introduced the strict layer hypothesis as a formal constraint on prosodic constituency. The hypothesis is a laminarity requirement: prosodic categories may not partially overlap. Subsequent literature (Itô & Mester, Truckenbrodt) documents and debates how often it is violated — again exactly the question this project addresses in the morphosyntactic domain.

**Selkirk, E. (2011).** The syntax-phonology interface. In: J. Goldsmith, J. Riggle & A. Yu (eds.), *The Handbook of Phonological Theory* (2nd ed.), Blackwell, 435–484.
> Updated treatment, covering violations of strict layering and revised accounts of phonological phrasing. Good entry point for the "laminarity assumed but violated" literature in phonology. *[Page range approximate; verify before citing formally.]*

**Computational linguistics / span-based parsing.** The chart-parsing tradition (Earley 1970; CYK) works with spans [i, j] of an input string — intervals on a linearly ordered token sequence, the same structure as strict spans in this project. Every complete parse tree is a laminar family of spans by construction. The NLP literature implicitly assumes laminarity (it is imposed by the grammar formalism) and has no formal treatment of what to do when observed evidence is not laminar. As the user notes, NLP parsing is a recognition/generation problem, not a typological one; the structural parallel is informative but the methodology is not transferable.

**Earley, J. (1970).** An efficient context-free parsing algorithm. *Communications of the ACM*, 13(2), 94–102.
> Defines chart parsing with spans as [i, j] intervals. Included here as a pointer to the implicit laminarity assumption in computational linguistics, not as a direct methodological reference.

The CCDB papers (Tallman 2021; Tallman et al. in press) are the primary applied references for the specific linguistic methodology; see the project's existing bibliography.

---

## Search Terms for Further Reading

- `laminar family tree representation combinatorics`
- `laminar family interval spans linear order`
- `hierarchy cluster system rooted tree`
- `maximum laminar subfamily` (for the algorithmic problem of finding the largest laminar subset of a non-laminar family)
- `set cover laminar` (for the minimum covering set problem)
- `phylogenetic tree cluster` + Semple Steel
- `phylogenetic splits compatibility network`
- `interval hypergraph Helly property`
- `prosodic hierarchy strict layer hypothesis laminarity`
- `VC dimension set system interval learnability`
- `Hasse diagram containment poset Dilworth theorem`
- `convex geometry antimatroid linear order`
- `split decomposition Bandelt Dress` (for the non-laminar / network case in phylogenetics)
- `circle graph chromatic number crossing intervals`
- `conflict graph laminar family coloring`
- `Dilworth theorem chain antichain poset decomposition`
- `hypergraph coloring property B vertex coloring`

---

*Last updated: 2026-04-23. Citations verified via web search except Rogers (1978), Booth & Lueker (1976) page numbers, Edelman & Jamison (1985), Blumer et al. (1989) page numbers, Bandelt & Dress (1992) page numbers, and Selkirk (2011) page range — all flagged with uncertainty. Check DOIs before citing formally.*
