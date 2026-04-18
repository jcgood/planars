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

---

## Matroids

**Laminar matroids (2017).** *European Journal of Combinatorics.*  
https://dl.acm.org/doi/10.1016/j.ejc.2017.01.002  
> Characterizes the class of matroids definable by laminar families (laminar matroids), including excluded minor characterizations. Useful background if the project ever moves toward independence-system formalizations of constituency, but not immediately necessary.

---

## Connections to Linguistics

The mathematical literature on laminar families does not, to my knowledge, directly engage with morphosyntactic constituency in the sense used in this project. The closest bridges are:

- The phylogenetics literature (Semple & Steel above), where the problem of reconstructing a tree from observed clusters is formally identical to reconstructing a constituency hierarchy from observed domain spans.
- The computational linguistics literature on constituency *parsing*, which implicitly assumes a laminar structure (context-free grammars produce laminar parse trees by definition) but does not study what to do when observed evidence is not laminar.

The CCDB papers (Tallman 2021; Tallman et al. in press) are the primary applied references for the specific linguistic methodology; see the project's existing bibliography.

---

## Search Terms for Further Reading

- `laminar family tree representation combinatorics`
- `laminar family interval spans linear order`
- `hierarchy cluster system rooted tree`
- `maximum laminar subfamily` (for the algorithmic problem of finding the largest laminar subset of a non-laminar family)
- `set cover laminar` (for the minimum covering set problem)
- `phylogenetic tree cluster` + Semple Steel

---

*Last updated: 2026-04-18. Citations verified via web search; check DOIs before citing formally.*
