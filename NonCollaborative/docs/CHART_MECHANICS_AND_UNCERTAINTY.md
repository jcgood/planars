# Chart mechanics and uncertainty-reduction — session notes (2026-09-14)

Working notes from a long session covering two connected things: (1) a reframing of
constituency diagnostics as *reducers of uncertainty* rather than *drivers of certainty*,
and (2) a fully-verified, plain-language explanation of how the nyan1308 "all 69 families"
overlay chart actually encodes evidence — because the mechanics turned out to be genuinely
non-obvious, worth being able to explain to another linguist, and easy to lose track of.

Related files:
- `REFERENCES.md` — the permanent citations and definitions for the math in Part 1 below
  (little Schröder vs. Catalan numbers, laminar vs. cross-free families, the
  partially-resolved-tree/polytomy/refinement vocabulary, the survivor-space framing).
  This document doesn't repeat that content — see the "Counting Constituency Trees" section
  there for the full, sourced version.
- `scripts/analysis/laminar_analysis.py` — the analysis discussed throughout (`classify_pair`,
  `find_conflicts`, `enumerate_maximal_laminar_families`).
- `r/planarsviz/R/overlays.R` — how the overlay is drawn. Until the 2026-09-20
  cutover this was `laminar_analysis.py`'s own `generate_r_overlay_script()` /
  `run_domain_overlay()`, which is what earlier passages here name; both are gone,
  and the archived script they wrote is in
  `OlderFiles/planarsviz_superseded/results/nyan1308_laminar_overlay.r`.
- `results/nyan1308_all_families_labeled.pdf` — the chart itself.
  `results/nyan1308_all_families_labeled_orthographic_word.pdf` — a variant with positions
  5–19 (the orthographic word) in red and position 17 (FV, the final vowel) in blue
  (colorblind-safe pairing, not red/green). Both are now drawn by the
  `planarsviz` R package from the exported data bundle; the `.r` files of the
  same names are the superseded generated scripts, archived in
  `OlderFiles/planarsviz_superseded/results/`, and the variant's file name comes
  from the highlight id in the data, which is why it is no longer called
  `_wordhood`.
- `docs/PLAN_planarsviz_refactor.md` — the R-visualization refactor plan, with a "Review:
  Claude" section appended; separate track of work, not covered further here.

---

## Part 1: The math, in one paragraph (full version in REFERENCES.md)

There are three different objects that "how many trees are there" can mean, and it matters
which one you mean: (1) the **Schröder space** — every tree shape logically possible over n
positions at all, A001003(n−1), the space of hypotheses before any evidence; (2) the
**maximal-family space** — given one dataset, the largest sets of *its own* spans that can
coexist without conflict, capped at Catalan(n−1), a fact with a clean proof (distinct maximal
families require distinct binary completions); (3) the **survivor space** — of all the trees
in (1), how many are still possible once a set of diagnostics has been applied as a filter,
`T_n(D) = {T : T doesn't contradict D}`. (3) is the one that matches "diagnostics reduce
uncertainty, they don't prove a single tree" — with `|T_n(D)|/|T_n|` as the natural measure of
how much uncertainty remains. It has a hard floor at exactly 1 survivor (the totally
uncommitted flat tree always survives any D, since nothing can contradict silence), and no
single dataset's maximal families can ever cover the full survivor space (the ceiling for that
is the smaller Catalan number). Vocabulary: what we were calling a "meta-tree" is properly a
**partially resolved tree**; its flat multi-way nodes are **(soft) polytomies**; the finer
trees it stands in for are its **refinements**. What this project computes is a **laminar
family**, not a **cross-free family** — checked directly against the code (`classify_pair`
flags a crossing pair as a conflict even when their union covers the whole structure, which is
exactly the case cross-free families would tolerate and laminar families don't).

---

## Part 2: How the chart actually encodes evidence

### Two independent signals, not one

The chart carries two deliberately separate pieces of information per edge:

- **Darkness** = how many of the 69 stacked, semi-transparent trees happen to draw a line
  through that exact spot — i.e. how many of the 69 *internally-consistent full analyses*
  agree that piece of structure is real. This is literally just "draw 69 very faint copies and
  let them pile up," unchanged from the original design. `alphaval` is one number, computed once,
  applied identically to every edge of every one of the 69 trees.
- **Thickness** = how many raw diagnostic *tests* independently produced that exact span
  (`convergence`), regardless of how many of the 69 trees agree with it. This varies per span,
  per tree — even a single one of the 69 trees, drawn completely alone, already shows some
  edges fatter than others.

These were once collapsed into one signal (both derived from family count) and deliberately
split apart, because they answer different questions: darkness = "how many interpretations
agree," thickness = "how much raw evidence supports this specific claim." E.g. `[2,22]` has
low convergence (2 tests) but is in all 69 families (maximal darkness, thin line); `[6,17]` has
the highest convergence in the dataset (19 tests) but is in only 23/69 families (moderate
darkness, the thickest line in the chart).

Current thickness formula: `max(convergence, 1) ** thickness_exponent`, with
`thickness_exponent=0.75` for this specific chart (raised from the default `0.5`/sqrt
specifically to make high-convergence spans like `[6,17]` stand out more, per request — checked
against 0.85 first, which started producing a visible bulge/blob at the tips, so 0.75 was kept
as "thicker, not crazy"). The colored multi-domain-type overlay (`nyan1308_laminar_overlay.r`)
keeps the original 0.5.

### `ladderize=FALSE` — why every tree needs the same leaf order

ggtree's own default is to re-sort each tree's siblings by clade size independently
(`ladderize=TRUE`) — good for reading one phylogenetic tree, actively wrong here, because the
"leaves" are positions 1–22 in a fixed *linguistic* order, not an arbitrary drawing choice.
Since the 69 trees differ from each other in a few spots, independent ladderizing can reorder
siblings differently tree to tree, so the same physical x-position can hold a different
position number in different trees — misaligning the overlay into a smeared, bowed mess.
`ladderize=FALSE` on every `ggtree()` call fixes this by keeping the 1→22 order fixed everywhere.
(Checked in git history: one of the hand-written forest scripts had *no* ladderize handling for
about five months, 2025-07-23 to 2025-12-16, and was fixed — apparently by accident — in an
unrelated "restructuring folders" commit on 2026-03-15.)

### Round line-caps and the dark "bulge" at busy junctions

A rounded line cap (`lineend="round"`, apparently ggtree's default for this geom) draws a small
filled disc at every segment endpoint. Where many of the 69 trees share (or nearly share) a
junction, those discs stack and compound into a visibly darker "bulge" beyond what the plain
edges' own alpha would produce — worse at junctions with more children (a node with 3 children
gets 4 line-ends per tree meeting there: 1 in, 3 out; an ordinary 2-child node only gets 3).
Verified directly by re-rendering the same real trees with `lineend` forced to `"round"` (bulge
present) vs. `"butt"` (bulge gone). **This was tried as a fix and then reverted at the user's
request — the round-cap look is preferred, kept as-is.** Left here only as an explanation of the
mechanism, not a recommendation to change it.

Separately, a single unusually thick edge (like `[6,17]` at thickness ≈9.1 vs. neighbors at
3–5) has a proportionally larger round cap purely because caps scale with line width — this
produces a distinct, *sudden* rounded lump right at that one edge's endpoint, not a gradual
fade, and doesn't require multiple trees to explain (confirmed by rendering three isolated
single lines at real thickness values with round caps: the thick one's cap is visibly bulbous,
the thin one's is barely there).

### Worked example: what happens at `[5,17]` → `[6,17]`

This is the fully-traced case, useful as a template for explaining any other segment:

- `[5,17]` ("Neg1 through FV") is a real constituent in **37 of 69** families.
- Of those 37, all of them have to resolve what's *inside* `[5,17]` somehow — there's no
  "leave it undecided" option once you're committed to the parent span. There turn out to be
  exactly three distinct ways they do it:
  - **23 families** → peel off leaf 5 alone, treat `[6,17]` ("SM through FV") as one piece.
  - **9 families** → pair Neg1+SM (`[5,6]`), leave Neg2 alone, treat `[8,17]` ("TAM through FV")
    as one piece.
  - **5 families** → lump Neg1-through-CAUS together (`[5,13]`), leave APPL/REC/PASS/FV as four
    separate, unconnected leaves.
- **23 + 9 + 5 = 37, exactly.** This is guaranteed, not a coincidence: the 37 families are
  partitioned (mutually exclusive, exhaustive) by which of the three shapes they use, so the
  group sizes must sum to the total. This generalizes: at any node, the branches' family-counts
  always sum back to that node's own darkness.
- **Important subtlety:** the branch-specific counts (9, 5) are *not* the same as those spans'
  own global darkness elsewhere in the chart. `[8,17]`'s overall family-count is 18 (not 9) and
  `[5,13]`'s is 10 (not 5) — because those same spans also appear as constituents in other
  families that never go through `[5,17]` at all. A span's global darkness (what's printed on
  it wherever it appears) mixes in evidence from unrelated parts of the family-space; a branch's
  local share at one specific node does not.
- Similarly, `[6,17]`'s own two children (`[6,8]`, convergence 3; `[9,17]`, convergence 5) are
  *not* just thinner echoes of `[6,17]`'s strength — they're independently-evidenced claims
  about a narrower, more specific question ("how does the inside of `[6,17]` break down"), and
  15 of each of their ~24-25 total supporting families don't even go through `[6,17]` as an
  ancestor at all. Strong agreement on the outer boundary does not imply strong agreement on
  the internal shape — that's a separate question the tests have to answer on their own.

### Boundary-frequency asymmetry (checked, not assumed)

Asked whether the right edge of `[6,17]` (the cut after position 17, FV|2P) is more widely
attested as *a boundary* than its left edge (the cut after position 5, Neg1|SM) — a different
question from whole-span darkness. Checked directly:

| | unique spans using this cut | total tests backing it | families with something there |
|---|---|---|---|
| left cut (5\|6) | 4 | 32 | 45/69 |
| right cut (17\|18) | 5 | 48 | 51/69 |

Yes, the right edge is more broadly attested here, by both measures, even after setting aside
the one span (`[6,17]`) that uses both edges. **This is local, not a general rule** — checked
separately whether "the complex/continuing side of a branch is usually on the right" holds
across the whole tree, and it doesn't: 148 nodes where the left child keeps splitting further
vs. 166 where the right child does — close to even, no systematic bias.

### The five-step algorithm, in plain terms

1. Collect every diagnostic test result as a candidate span, each tagged with how many
   independent tests produced it.
2. Check every pair of spans: nested, disjoint, or genuinely conflicting (partial overlap,
   neither contains the other)?
3. Find every *maximal* way of picking a bundle of mutually non-conflicting spans — each bundle
   is one complete, internally-consistent way of organizing the whole word. 69 such bundles for
   nyan1308.
4. For any one specific span, count (a) how many raw tests produced it (→ thickness) and
   (b) how many of the 69 bundles include it (→ darkness) — computed fresh, independently, per
   span, never inherited from a neighboring span.
5. Draw all 69 bundles as trees, stack them semi-transparently, and let each edge's own
   thickness and darkness (from step 4) do the rest.

---

## Open items / where this was left

- Nothing currently pending — this is a reference for re-orienting quickly if the same
  questions come up again, or for explaining the chart to a colleague.
- If picking this back up: start from the worked `[5,17]`→`[6,17]` example above as a template,
  and reuse the small Python snippets in this session's transcript (querying
  `laminar_analysis.py`'s `load_spans`/`find_conflicts`/`enumerate_maximal_laminar_families`
  directly) rather than re-deriving the logic from scratch.
