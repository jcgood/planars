# Laminar Family Analysis: Nyangatom (nyan1308)

*Generated 2026-04-18 from `domains_nyan1308.tsv` using `laminar_analysis.py`.*  
*Position labels from `constituencyforest-all.r` (treeTraversal.py output).*

---

## Data summary

- 26 unique spans over 22 positions (size-1 spans excluded)
- 21 spans involved in at least one conflict; 5 spans conflict-free
- 65 conflict pairs total: 28 within domain type, 37 across domain types

Position labels (1–22):
QM, PreSbj, Sbj, PostSbj, Neg1, SM, Neg2, TAM, OM, Root, Ext, STAT, CAUS, APPL, REC, PASS, FV, 2P, Enc, Obj1, Obj2, PostObj

---

## Result: 69 maximal laminar families

A maximal laminar family is a set of observed spans that (a) are all mutually
nested or disjoint (no partial overlaps), and (b) cannot be extended — every
other observed span partially overlaps at least one span already in the family.
Each maximal laminar family corresponds to one valid branching tree rooted at
the full span [1–22].

**All 26 observed spans appear in at least one maximal family.**

---

## Span occurrence across the 69 families

Spans are ordered from most to least prevalent. Occurrence counts tell you how
structurally robust each span is: a span in all 69 families is present
regardless of how conflicts elsewhere in the data are resolved; a span in only
4 families is present only under very specific conditions.

| Span | Positions | Domain type(s) | Convergence (n) | Families (of 69) |
|------|-----------|----------------|-----------------|------------------|
| [1–22] | QM–PostObj | intonational/morphosyntactic | 5 | 69/69 |
| [2–22] | PreSbj–PostObj | intonational | 2 | 69/69 |
| [3–21] | Sbj–Obj2 | phonological | 4 | 69/69 |
| [5–19] | Neg1–Enc | morphosyntactic | 1 | 69/69 |
| [5–21] | Neg1–Obj2 | morphosyntactic/phonological | 5 | 69/69 |
| [5–18] | Neg1–2P | length/morphosyntactic | 2 | 51/69 |
| [13–15] | CAUS–REC | morphosyntactic | 1 | 40/69 |
| [10–16] | Root–PASS | phonological | 1 | 38/69 |
| [5–17] | Neg1–FV | length/morphosyntactic/tonosegmental | 10 | 37/69 |
| [9–16] | OM–PASS | tonosegmental | 1 | 36/69 |
| [9–10] | OM–Root | tonosegmental | 1 | 27/69 |
| [9–17] | OM–FV | length/phonological/tonosegmental | 5 | 25/69 |
| [5–6] | Neg1–SM | phonological | 1 | 24/69 |
| [6–8] | SM–TAM | phonological/tonosegmental | 3 | 24/69 |
| [10–13] | Root–CAUS | phonological | 1 | 23/69 |
| [6–17] | SM–FV | intonational/phonological/tonosegmental | 19 | 23/69 |
| [8–16] | TAM–PASS | tonosegmental | 2 | 20/69 |
| [17–19] | FV–Enc | phonological | 1 | 18/69 |
| [8–17] | TAM–FV | tonosegmental | 8 | 18/69 |
| [6–16] | SM–PASS | tonosegmental | 7 | 18/69 |
| [10–17] | Root–FV | length/morphosyntactic/phonological | 6 | 14/69 |
| [9–18] | OM–2P | length/morphosyntactic | 2 | 14/69 |
| [8–10] | TAM–Root | tonosegmental | 1 | 11/69 |
| [5–13] | Neg1–CAUS | morphosyntactic | 1 | 10/69 |
| [6–10] | SM–Root | phonological/tonosegmental | 3 | 8/69 |
| [10–18] | Root–2P | length/morphosyntactic | 2 | 4/69 |

---

## The central conflict: [5–13] vs [6–17]

These two spans are the most important structural alternative in the data.
They partially overlap (SM through CAUS) and therefore cannot coexist in any
tree. They define two broad groups among the 69 families:

- **10 families include [5–13]** (Neg1–CAUS, morphosyntactic): these are trees
  where the morphosyntactic domain closes at CAUS, creating a small inner
  domain with substructure at SM–TAM or SM–Root.

- **23 families include [6–17]** (SM–FV, intonational/phonological/tonosegmental,
  n=19): these are trees where a large phonological/tonosegmental domain covers
  SM through FV, with rich internal nesting (TAM–FV, OM–FV, Root–FV, etc.).

- **36 families include neither**: these use other combinations of spans that
  are incompatible with both [5–13] and [6–17].

The high convergence of [6–17] (n=19 diagnostic tests) makes its absence from
most families analytically interesting — it is broadly evidenced but
structurally incompatible with many other spans.

---

## Conflict structure by hypothesis

### Tree hypothesis

Data is **not** perfectly laminar: 65 conflict pairs require 69 alternative
trees to cover all observed spans. The hypothesis is challenged, but the
5 always-present spans ([1–22], [2–22], [3–21], [5–19], [5–21]) represent
a robust nested core that holds across all 69 trees.

### Morphosyntax/phonology divide hypothesis

- 28 conflicts are **within** a single domain type (challenge the divide hypothesis)
- 37 conflicts are **across** domain types (consistent with the divide hypothesis)

The within-type conflicts are concentrated in the tonosegmental class (e.g.,
[6–8] vs [6–10], [8–16] vs [8–17], [9–16] vs [9–17]) and the morphosyntactic
class ([5–13] vs [10–17], [5–13] vs [9–18], [5–13] vs [13–15],
[5–13] vs [10–18]). These represent genuine unresolved structure within each
domain type.

### Word hypothesis

The Neg1–FV span [5–17] (n=10, 37/69 families) is the highest-convergence
span not in all families, and the strongest word-domain candidate. The
Neg1–Enc span [5–19] is in all 69 families but has convergence n=1 only.

---

## Relationship to treeTraversal.py output

treeTraversal.py (the earlier algorithm) produced 16 trees for nyan1308.
All 16 are valid laminar families, but only **5 are maximal**:

| treeTraversal tree | Status | Confirmed in 69? | Key distinctive spans |
|-------------------|--------|------------------|-----------------------|
| TT1 | Maximal | Yes (BK family 58) | [6–17], [8–17], [9–17], [10–17], [10–16], [13–15] |
| TT2 | Maximal | Yes (BK family 38) | [6–17], [8–17], [9–17], [9–16], [10–16], [13–15] |
| TT3 | Maximal | Yes (BK family 34) | [6–17], [8–17], [8–16], [9–16], [10–16], [13–15] |
| TT4 | Maximal | Yes (BK family 49) | [6–17], [6–16], [8–16], [9–16], [10–16], [13–15] |
| TT9 | Maximal | Yes (BK family 4) | [5–13], [6–10], [8–10], [9–10] |
| TT5–8, TT10–16 | Non-maximal | — | Each can be extended by ≥1 compatible span |

The 11 non-maximal treeTraversal trees are valid families but incomplete:
treeTraversal.py builds linear chains without checking whether spans at the
same tree level would conflict with each other, so it can terminate early
without adding all compatible spans.

The 64 families found only by the correct Bron-Kerbosch algorithm were missed
by treeTraversal.py because it does not enumerate all combinations — it
follows a single greedy path per starting configuration.

---

## Algorithm notes

`laminar_analysis.py` uses the Bron-Kerbosch algorithm for maximal independent
sets (MIS) in the conflict graph. A maximal IS in the conflict graph = a
maximal set of mutually compatible spans = a maximal laminar family.

An earlier version of the algorithm had a bug: it iterated over
*compatible* (non-conflict) neighbors of the pivot vertex instead of
*conflict* neighbors, which is the algorithm for maximal cliques in the
conflict graph (the wrong problem). That version found only 4 families.
The corrected non-pivoted BK finds all 69.

The chromatic number of the conflict graph (minimum number of families
needed to cover every span at least once) is a separate quantity; the
minimum partition approach (used in an even earlier version) also found 4,
which was coincidentally the same number as the buggy BK output but for a
different reason.
