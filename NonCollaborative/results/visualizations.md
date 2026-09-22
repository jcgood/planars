# Visualizations: nyan1308

Everything in `NonCollaborative/results/` — what it shows, what produced it,
and how to make it again.

**Where the charts come from.** Almost all of them are drawn by the
`planarsviz` R package from a data bundle the Python analysis exports. Two
commands make every chart in this file that the package draws:

```
cd NonCollaborative

python scripts/analysis/export_planarsviz_data.py \
  --domain-file domains/domains_nyan1308.tsv \
  --output-dir results/planarsviz \
  --language-name Chichewa

Rscript scripts/render_planarsviz.R \
  --bundle results/planarsviz/nyan1308 \
  --output results
```

**Run these from `NonCollaborative/`**, which is where the porting checks run
too. The exporter records the domain file's path as you gave it, so running it
from somewhere else writes a bundle that differs from the committed one in
that one field and nothing else. Add `--plots name1,name2` to the second
command to draw only some charts; `--list` prints the names a bundle supports.
The sections below give the `--plots` name for each chart.

**Where the files sit.** `results/` is grouped by topic rather than flat:
`laminar-families/`, `pooled/`, `boundaries/`, `counts-and-chance/`,
`planar-structure/` and `illustrations/`. Only this file and the render
manifest sit at the top. Each section below is headed by a bare file name,
because file names are unique across the whole tree; for a chart the package
draws, `nyan1308_planarsviz_manifest.tsv` gives its exact path. Which folder a
chart belongs to is recorded once, as an attribute on the chart function
itself, and the renderer reads it — so a new chart lands in the right place
without anything here having to be updated to match.

**Two files, two jobs.** This file says what each artifact in `results/`
*shows* and what it means for the analysis.
[`../docs/planarsviz_charts.md`](../docs/planarsviz_charts.md) is the chart
catalogue: every chart the package draws, its R call, its options, its canvas
and an example image. Look there for how to draw a chart, here for what to
make of it. A few charts in `results/` have a catalogue entry but no section
here — they are listed under "Charts covered only by the catalogue" at the
end.

**The scripts that used to make these are gone.** Until the 2026-09-20
cutover, the charts below were drawn by generated R scripts that sat in
`results/` beside the PDFs, written by generator functions in
`scripts/analysis/laminar_analysis.py`. The package replaced them: step C2
archived the scripts in
`OlderFiles/planarsviz_superseded/results/`, where the
porting checks still run them to prove the package draws the same thing, and
step C3 removed the Python that wrote them. Where a section below names one
of those scripts, it is naming the archived original — the explanation of how
the chart works still holds, because the package reproduces it.

---

## Laminar family charts

---

## nyan1308_conflict_groups.pdf

**Draw it:** `--plots conflict_groups`. Archived original: `laminar_conflict_groups.r`.

**What it shows:** Four panels arranged as a full-width top row and three equal panels below
(`(panel_all / (panel_A | panel_B | panel_C)) + plot_layout(heights=c(2, 1))`).

- **Panel ALL** (top): Ghost overlay of all 69 maximal families. Every family is drawn as a
  semi-transparent tree (`alpha=0.064563`, tuned so 69 stacked layers give comparable overall
  density to the smaller panels below); edges that appear in many families accumulate opacity
  and look darker. There is no separate consensus-backbone layer — every edge in every panel is
  plain black (`colour <- 'black'` throughout the script; confirmed directly, no red anywhere).
  What stands in for a backbone instead is per-family edge weight: each tree's edges are grouped
  by span (`groupOTU()`) and given a `size` aesthetic scaled by how often that span recurs across
  the family set (`sqrt`-scaled — e.g. `8.3066 ≈ sqrt(69)` for a span in all 69 families), so
  high-convergence spans are already drawn thicker within a single tree, before the transparency
  stacking adds further density on top.
- **Panel A** (bottom-left): Ghost overlay of the 10 families that contain span [5–13]
  (Neg1–CAUS, morphosyntactic). All 10 are drawn (`alpha=0.369043`).
- **Panel B** (bottom-center): Ghost overlay of the 23 families that contain span [6–17]
  (SM–FV, high convergence n=19). Capped at 12 representative trees (`alpha=0.318708`) — the
  selection logic isn't in this file, so it must live in the Python script that generates this
  one; not yet traced further.
- **Panel C** (bottom-right): Ghost overlay of the 36 families that contain neither [5–13]
  nor [6–17]. Same 12-tree cap and alpha as Panel B.

The three groups are defined by the central conflict in nyan1308: [5–13] and [6–17] partially
overlap and cannot coexist in any laminar family, so every family must resolve this conflict
one way or the other.

**Output size:** 24 × 20 in.

---

## nyan1308_all_families_labeled.pdf / _legend.pdf

**Draw it:** `--plots all_families_labeled,all_families_labeled_legend`. Archived
original: `nyan1308_all_families_labeled.r`. The highlight variant
`nyan1308_all_families_labeled_orthographic_word.pdf` is the same chart with the
orthographic-word span picked out; it was `_wordhood` before the cutover and is
named after the highlight id in the data now.

**What it shows:** A single-panel version of Panel ALL above — all 69 maximal families ghost
overlaid in black, same density (`alpha_divisor=1.0` reproduces Panel ALL's 0.064563-ish alpha,
not the `/2` tuning used for the multi-color domain-type overlay below) — but with the boxed,
two-line ("position number" over "name") tip labels of the coloured overlay, using the
same invisible-per-tree-spacer + one-visible-label-on-top pattern. It is the coloured
domain-type overlay `nyan1308_laminar_overlay.pdf` with one unfiltered black group in place of
five coloured ones, and half the per-layer transparency — one function in the package
(`plot_laminar_overlay()`, with `groups = "all"`), two archived scripts before the cutover.

**Thickness and darkness encode two different things, not the same one measured twice.**
An earlier version set both from family count (`sqrt(family_count)` for thickness, accumulated
opacity from family-count-many stacked layers for darkness) — accurate, but redundant: two
channels showing one signal. Now:
- **Darkness** = how many of the 69 families contain the span (structural robustness). This one
  isn't a free choice — it's an unavoidable side effect of the ghost-overlay technique itself
  (how many of the 69 stacked semi-transparent layers happen to draw a matching segment at that
  position), so it can't be repurposed to show something else without breaking the overlay
  mechanism. This is what makes the consensus backbone (see the conflict-groups chart above)
  visually obvious: the 5 always-present spans render as the darkest edges.
- **Thickness** = `sqrt` of convergence (how many independent diagnostic tests produced the span —
  evidential support), set per edge, independent of darkness.
These genuinely diverge in the data: [5–17] (Neg1–FV) has the highest convergence of any
non-backbone span (n=10 tests) but sits in only 37/69 families — thick but not especially dark.
[2–22] has convergence n=2 but is in all 69 families — dark but comparatively thin. The 5
always-present spans are uniformly dark but *not* uniformly thick; [6–17] (n=19, the highest
convergence in the whole dataset) stands out as the thickest edge in the chart despite being in
only 23/69 families — visibly less dark than the backbone. Neither of those contrasts was visible
under the old same-source encoding.

Tip-label `offset`/`vjust`/margin build on the verified fix described under
`nyan1308_random_tree_overlay.pdf` further below — not the plain `offset=-1` the coloured overlay
used at the time, whose gap was measured too small (39px on a comparable canvas) to read cleanly
at normal viewing scale. The fix went into the shared generator, so it reached the coloured
overlay too, and the package inherited it from there. The exact `vjust`
value was re-measured directly on this file's own 20×14in canvas rather than assumed from the
16×10in numbers elsewhere (canvas size changes the pixel-per-data-unit scale, so a value verified
on one canvas doesn't transfer as-is to another): `vjust=1.25` measured at 145px, `0.6` at 75px,
and `0.35` — the value used here — at 45px, all via the same true-tip-marker technique
(`geom_tippoint()`), chosen to sit closer to the vertex than the first pass while keeping a clear,
unambiguous gap.

**Ghost-label bug, found and fixed here:** the invisible per-tree tip-label spacer (there to
reserve identical panel space on all 69 trees so they stack in exact alignment) wasn't actually
invisible. `alpha=0` and `label.size=0` both looked like they should hide it but don't:
`geom_tiplab(geom="label", ...)` in this ggtree version silently ignores `label.size` entirely
(that's what the "Ignoring unknown parameters: `label.size`" warning seen on every run in this
project — long assumed harmless — was actually reporting), and `alpha=0` doesn't suppress a
`geom="label"` tip label at all; it rendered at full opacity regardless. Since every placeholder
sits at the identical reserved position, the practical effect was one small extra box (bare tip
number, no name) peeking out from behind the real, larger, two-line visible label — not 69
distinct duplicates, but a visible artifact all the same. Verified with an isolated single-tree
test (`geom_tippoint` reference point, same technique as the `random_tree_overlay.py` offset work)
that the fix that actually works is `colour=NA, fill=NA` — confirmed those two alone produce a
fully invisible label, `alpha=0` and `label.size=0` confirmed to do nothing.

**Legend** (`_legend.pdf`, same 20×14in canvas as the base file — no widening needed): one bordered
box (`plot.background=element_rect(fill="white", color="black", linewidth=1.2)`, a heavier border
than a first pass at `0.6`) inset in the top-left corner via `inset_element(legend_plot, left=0.01,
bottom=0.67, right=0.27, top=0.97, ...)` — tightened from an earlier, looser `bottom=0.63` plus
wider `plot.margin` and row spacing, per direct feedback that it had too much dead space. Two
sections stacked inside that one box — "Darkness: Trees sharing span" (a 2-row gradient,
"More"/"Fewer") and "Thickness: Tests supporting span" (same, "More"/"Fewer") — each just two
swatches (no unlabeled middle step; the box stays compact). Section headers use `:` rather than
`=`, capitalize the word right after the colon, are unbolded, and are set larger than the swatch
labels (`size=7` vs `5.8`) — a plain, capitalized colon and a bigger, regular-weight header reads
more like ordinary figure-legend prose than the lowercase, bolded `=` of the first version.
"Trees," not "families," in the visible text — a maximal laminar family *is* a tree (see this
module's own docstring), and that's the term a linguist reading the chart will expect, even though
`family`/`families` stays the accurate internal vocabulary everywhere else in this codebase (spans,
conflict graphs, Bron-Kerbosch). No specific numbers appear anywhere in the legend text (no family
count, no `n_total`, no test count) — the wording is entirely generic so the same legend reads
correctly for any language's tree set without touching the code. The "More" swatches still render
at this run's own real formula (`1 - (1-alphaval)**n_total` for darkness, `sqrt(max_convergence)`
for thickness); "Fewer" does *not* — the darkness key's real single-layer alpha (~0.065 for
`n_total=69`) was reported as nearly invisible, so `dark_lo` is a fixed, deliberately schematic
`0.4` instead: visibly lighter than "More" without vanishing. The thickness key's "Fewer" (a thin
but fully opaque black line, `sqrt(1)=1.0`) didn't have that problem and is untouched.

Went through two placement attempts before this one. First was a real side-by-side panel
(`(forest | (darkness_legend_plot / thickness_legend_plot)) + plot_layout(widths=c(5, 1))` on a
widened 24in canvas) — verified not to overlap (structurally impossible, being in its own column),
but not what was asked for: a dedicated side panel that permanently costs canvas width isn't a
"boxed legend in the corner," and its per-key captions ("Darkness: how many of the 69 maximal
families contain the span...") named the specific family count, which doesn't generalize to a
different language's tree set. Before that, the very first attempt used `inset_element()` in the
top-left but with the box too wide (`right=0.42`) for how low its bottom sat (`bottom=0.55`),
so it visibly crossed into the outer envelope's diagonal — confirmed by inspecting the actual
rendered page, not assumed from the bounds alone. This version keeps the same top-left inset
mechanism but narrower (`right=0.27`) with a bottom bound left clear of that diagonal at that
width, checked against a render before shipping.

A domain-type color legend (the kind `nyan1308_laminar_overlay.pdf` gets, five colors, also
inset) would be meaningless on this all-black chart, so the chart branches on how many groups it
was given: more than one colored group → color legend; exactly one → this darkness/thickness
legend instead. The package keeps that rule inside `plot_laminar_overlay(legend = TRUE)`.

**Output size:** 20 × 14 in (base and `_legend.pdf` both).

---

## nyan1308_four_trees.pdf

**Draw it:** `--plots four_trees`. Archived original: `laminar_four_trees.r`.

**What it shows:** A 2×2 grid of four clean representative trees — one per structural group —
with no ghost overlay. Each panel shows the single most consensus-like family in its group,
where "most consensus-like" means the family whose spans have the highest total frequency
within that group.

Edge thickness and opacity in each panel are proportional to **within-group span frequency**:
how many families in that group share each edge. This makes the structurally stable edges
within the group visually prominent and contingent edges faint.

- **Top-left (All):** Most consensus-like family across all 69 families; edge weight = overall
  span frequency / 69.
- **Top-right (A):** Most consensus-like family among the 10 [5–13] families; edge weight =
  within-group frequency.
- **Bottom-left (B):** From the 23 [6–17] families.
- **Bottom-right (C):** From the 36 "neither" families.

**Output size:** 24 × 16 in.

---

## nyan1308_freqtree.pdf

**Draw it:** `--plots freqtree`. Archived original: `laminar_freqtree.r`.

**What it shows:** A single frequency-weighted tree implementing edge bundling. Instead of
overlaying 69 transparent trees, all families that share an edge contribute to one weighted
stroke. The most consensus-like family (highest total span frequency across all 69 families)
is used as the tree skeleton; per-edge weights are attached via ggtree's `%<+%` operator.

Edge thickness and opacity encode **overall span frequency / 69**:
- Backbone spans (in all 69 families): thick, fully opaque edges.
- High-frequency optional spans: moderately thick and opaque.
- Low-frequency spans: thin and faint.

Spans absent from the representative tree are not shown. This is a "modal tree" — the best
single summary of the full family space — rather than a complete picture.

**Output size:** 16 × 10 in.

---

## nyan1308_spanchart.pdf

**Draw it:** `--plots spanchart`. Archived original: `laminar_spanchart.r`.

**What it shows:** A non-tree frequency chart. Each of the 25 observed spans (excluding the
root [1–22]) is drawn as a horizontal segment spanning its position range. Segments are sorted
vertically by frequency (most frequent at top) and labeled with their coordinates and count.

- **Line width and opacity:** proportional to frequency / 69.
- **Color:** domain type (morphosyntactic = red, phonological = blue, tonosegmental = green,
  intonational = yellow, length = purple).
- **x-axis:** positions 1–22 with labels (QM … PostObj).

This is the most direct way to read per-span frequencies. It answers the question "which spans
are universal vs contingent?" without the complications of tree topology.

**Output size:** 14 × 8 in.

---

## nyan1308_exemplary_trees_1.pdf .. _7.pdf

**Draw it:** `--plots exemplary_trees_1,...` (or leave `--plots` off). Archived
original: `nyan1308_exemplary_trees.r`.

**What it shows:** Seven of the 69 maximal families — six selected as representative examples plus
one deliberately unrepresentative one (see below) — each its own file: a clean single tree (no
ghost overlay, one family, boxed position-labeled tips) next to
the pooled plot of exactly the tests whose spans make up that family. The pooled plot beside each
tree is the direct evidence for it — every horizontal line is one diagnostic test, colored by
domain type, and the tree shows the single consistent structure all of those tests' spans combine
into. Edge labels use **global** layer numbers — filtered from the already-numbered `tests_plot`
(the same object `nyan1308_pooled_plot.pdf` is built from), not recomputed fresh per family. A
span labeled "17" here is the same "17" in the master pooled plot and in any other exemplar that
happens to share it; an earlier version called `df.plot()` on each family's own filtered subset,
which renumbers layers locally from 1 — the same problem the `_global_layers` pooled-chart variants
were built to avoid, fixed here the same way (confirmed directly: cross-checked several specific
spans' numbers against `nyan1308_pooled_plot.pdf` and they match).

**Selection** (`select_representative_families()` in `laminar_analysis.py`): greedy coverage,
tie-broken by consensus. Repeatedly pick the family that adds the most spans not yet shown by an
already-picked family (structural diversity across the 6); break ties by highest total
`span_family_count` among tied candidates (lean toward the more consensus-like ones). This
combines two selection ideas already named elsewhere in this project — the conflict-groups
chart's Panels B/C ("structurally diverse representatives... by greedy coverage") and the
four-trees chart's "most consensus-like family" — into one function, because neither existed
as reusable code anywhere in `scripts/` (checked directly; whatever produced those two selections
wasn't saved). With only 26 unique spans across 69 families, every span is typically already
covered well before 6 families are picked, so the later picks are decided by the consensus
tiebreak alone — a graceful degradation, not a bug.

**Exemplar 7 is different on purpose: the sparsest family in the forest**, not a 7th pick from the
same selection. The selection appends the family with the
fewest individual tests, tie-broken by fewest distinct domain types (for nyan1308 the two criteria
agree exactly — family 67 in enumeration order is the unique minimum on both: 21 tests, 3 domain
types, 9 spans). The greedy-coverage/consensus selection has no reason to ever surface this family
on its own — coverage and consensus both favor families that explain a lot, and a sparse family by
definition doesn't — so this is a second, deliberate axis (least evidence) rather than something a
larger `k` on the main selection would find.

**Why seven separate files, not one combined figure:** the first version tried a 6-row page with
tree and pooled plot both compressed to fit a shared row. That failed outright — confirmed by
rendering it, not assumed — because a tree needs real width for 22 boxed leaf labels and a pooled
plot needs real height for however many tests it contains (some of these families draw on 40+
individual tests), and shrinking both to share a compact row made both illegible at once. Each
exemplar now gets a full page instead, tree and pooled plot placed side by side (not stacked) so
each keeps the dimension it actually needs: the tree at the same ~20in-equivalent width (51cm)
already proven elsewhere in this module for 22 boxed labels, the pooled plot at
the pooled chart's own untouched `plot_height()` formula (`max(7, n_tests*0.7)` cm) — exactly
as legible as any standalone pooled chart, not a scaled-down approximation. Placed side
by side, patchwork gives both panels the pooled plot's height, which can leave a low-test-count
tree panel with some blank space around it — checked directly at both ends of the range (a
59-test family and an 18-test family) and the tree stays legible either way, just flatter or
taller proportioned; nothing gets squeezed.

**The evidence panel is the pooled chart, not a lookalike.** The archived script got it by
`source()`-ing `domain_charts-cgpt.r`, which had the side effect of re-saving every standard
pooled-plot PDF on each run. The package draws both from the same bundle instead, so the side
effect is gone and the two still cannot drift apart. Each family's own test set is read directly
off `Span.labels` (the original `Test_Labels` collected when spans are aggregated in
`load_spans()`), not re-derived, so the evidence beside each tree is exactly the tests that
produced it.

**Output size:** 76cm wide (51cm tree column + 25cm pooled-plot column) per file; height matches
the pooled plot's own `max(7, n_tests*0.7)` cm — roughly 18–41cm tall depending on how many tests
that family draws on.

---

## Slide variant: nyan1308_exemplary_trees_slide_1_tree.pdf / _evidence.pdf .. _slide_7_*

**What it shows:** The same seven families, as **two slides per family**, not one. Slide one is the
tree alone, full frame, fixed at 13.333×7.5in (the literal size of 1920×1080 at the standard
144dpi PowerPoint uses, not just a pixel count — true 16:9). Slide two is the evidence panel — and
is literally the same `plot_var` object used in the combined print file next to it, saved on its
own rather than paired with the tree, at that object's own proven size (`pooled_width_cm` ×
`pooled_height_cm`, the same sizing the print file uses) rather than forced into 13.333×7.5in.
Every test shown individually, same global layer numbers as the print file and
`nyan1308_pooled_plot.pdf` — not a summary.

An earlier version of this evidence slide built a *different* chart: one row per span instead of
per test, with a test count instead of each test's name, to fit a fixed 7.5in slide height. Wrong
call, per explicit correction — showing a count instead of the actual tests read as data going
missing, not as a deliberate simplification, especially once its per-span test-count numbers sat
next to the print file's per-test global-layer numbers and looked like a second, inconsistent
numbering scheme rather than two views of the same thing. Reusing `plot_var` directly instead of
building a second implementation keeps this file automatically consistent with the print file —
same object, same tests, same numbers, nothing to drift out of sync — at the cost of the evidence
slide's height varying by family (18–41cm, matching the print file's own pooled panel) rather than
staying fixed at 7.5in like the tree slide.

**Why two slides, not the tree and evidence together on one:** tried combining them on a single
13.333×7.5in frame at several width splits (even, then 9.7in tree / 3.6in evidence) — neither
split left the tree's 22 boxed labels legible. Rendered the tree alone at the full 13.333in width
to check whether the frame itself was the constraint or just the split: it was legible, right up
against the width limit, confirmed by rendering it, not assumed. There's no room left beside it
for a second panel at that point — and once the evidence panel needs its full per-test height
(up to 59 rows for the busiest family here) rather than a compressed summary, it needs even more
room than that split ever gave it. Two full-frame slides — tree, then its evidence — also matches
how a talk would actually present this rather than forcing both into one busy slide.

**Tree tip-label size (4.6) is smaller than the print file's (5), with tighter `label.padding`
(0.12 lines, vs. `geom_label`'s 0.25-line default) too** — both needed, not either alone. The
print tree never has this problem (checked directly: it has ~20in for these same 22 labels), but
at the slide tree's narrower 13.333in, text size alone went through 7 (clipped `PostSbj`, the
longest of the 22 names, on every tree), 5.5 (`PostSbj` still clipped by one character, same
consistent failure), and 5 (no more text clipping, but the *boxes themselves* still touched or
crossed borders at `21 Obj2` / `22 PostObj` — reported directly, not something the earlier checks
had caught, since they'd only looked for cut-off text, not touching borders). Diagnosed by
inspecting the tree's actual panel coordinate ranges (`ggplot_build()`) rather than guessing
further: the panel expansion wasn't asymmetric in a way that explained it (`scale_y_continuous`
made left/right expansion symmetric and the boxes still touched), so the real fix was shrinking
the boxes themselves. Verified on the full 22-label row, not just the one pair that prompted the
check, and confirmed clean gaps on all 7 trees, not just the one first tested.

**Output size:** tree slides fixed at 13.333×7.5in; evidence slides 25cm wide, 18–41cm tall
depending on how many tests that family draws on (same as the print file's pooled panel).

---

## nyan1308_&lt;forest&gt;_tree_01.pdf .. (48 files, one per family per forest)

**What they are:** every individual maximal family in a forest, one tree per
page. The other two ways of looking at a forest both lose the individual trees: the
ghost-overlay charts (`nyan1308_phonologylike_laminar_forest.pdf` and its siblings)
stack every family into one semi-transparent image, and the exemplary-tree charts show
a curated seven-family subset of the *pooled* analysis only. These show each family in
a forest on its own terms — 3 for `morsyn`, 9 for `tono`, 3 for `length`, 6 for
`phon`, 1 for `inton`, 6 for `phonologylike`, 16 for `syntaxlike`, 4 for
`syntaxlike_notono`.

The drawing is the exemplary trees': same layout, same boxed "number over name" tip
labels, same margins. Since 2026-09-21 it is literally the same code —
`planarsviz_labelled_tree()`, which both `plot_forest_tree()` and
`planarsviz_exemplary_tree()` call. What differs is only what the tree is keyed by:
`(forest_id, tree_number)` read from the bundle's `data/forests/<id>.tsv`, rather than
`family_id` read from `bundle$families`.

To regenerate one:
```
Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 \
  --output results --plots syntaxlike_tree_09
```
or leave `--plots` off to draw every chart in the bundle.

**Only 22 of the 48 have a reference image.** Before the package absorbed these,
a standalone script drew the `phonologylike` and `syntaxlike` trees and nothing else;
those 22 were frozen as reference images and the port is checked against them at
0.0000%. The other 26 — `morsyn`, `tono`, `length`, `phon`, `inton`,
`syntaxlike_notono` — had never been drawn by anything, so the renderer check reports
"no reference" for them, the same way it does for `most_binary_tree`.

`scripts/analysis/bundle_forest_trees.r`, which drew these 22 straight into
`results/laminar-families/` with no chart name and no manifest row, was archived to
`OlderFiles/planarsviz_superseded/scripts/analysis/` on the same day. It must not be
run: it would write its own output over the package's under the same filenames, which
is what `.Rprofile`'s guard on `OlderFiles/` exists to prevent.

---

## Laminar family notes

- The renderer writes every chart to whatever `--output` names, so the PDF lands where you asked
  for it rather than where the chart's code happened to hard-code.
- The conflict-group split (target spans [5–13] and [6–17]) now comes from
  `planar_tables/conflict_groups_nyan1308.tsv`, not from a number baked into a chart. It used to
  be hard-coded as the nyan1308 default.
- Four of these charts — conflict groups, four trees, frequency tree, span chart — had no
  committed generator at all (the scripts were added alone in commit `3a39a08`), so the archived
  `.r` files are the only record of how they chose which families to draw. Those rules were
  recovered from the files themselves and are now in the exporter; see
  `docs/PLAN_planarsviz_library.md` §4.1 for how each was recovered.
- `scripts/render_planarsviz.R` installs the package into a temporary library itself, so there
  is no install step to remember. The package's own dependencies are in
  `r/planarsviz/DESCRIPTION`; the tree charts additionally need `ape` and `ggtree`, which are
  listed under `Suggests` because the other charts do not.

---

## Pooled constituency charts

Drawn by the `planarsviz` package from the exported data bundle. Reads the same underlying
CCDB test data, `domains/domains_nyan1308.tsv`, by way of the bundle the
exporter writes. PDFs are written to `results/pooled/`.

To render:
```
Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 \
  --output results --plots pooled_plot,pooled_domainplot
```
Leave `--plots` off to draw every chart the bundle supports.

The hand-written script these came from, `domain_charts-cgpt.r`, is archived at
`OlderFiles/planarsviz_superseded/scripts/`. It is kept because the porting
check runs it to prove the package draws the same thing — see that directory's `README.md`.

### nyan1308_pooled_plot.pdf

**What it shows:** One horizontal line per test, spanning its `Left_Edge`–`Right_Edge` range,
colored by `Domain_Type`. Rows are ordered with the largest domains at top; tests that pick out
the exact same span are grouped into one layer and numbered together. A dotted vertical line
marks the root/keystone position (10); the x-axis covers all 22 planar positions.

### nyan1308_pooled_domainplot.pdf

**What it shows:** The same span data, but rows are grouped by `Domain_Type` first
(morphosyntactic, tonosegmental, length, phonological, intonational, in that order) rather than
purely by domain size.

### nyan1308_pooled_plot_length.pdf / _morphosyntactic.pdf / _phonological.pdf / _tonosegmental.pdf / _intonational.pdf

**What they show:** The same chart as `nyan1308_pooled_plot.pdf`, restricted to tests of one
`Domain_Type` at a time — one file per class. Current test counts: tonosegmental 44,
phonological 21, intonational 12, morphosyntactic 11, length 7. Each chart numbers its own
domains 1..N from scratch (computed by calling `df.plot()` on just that subset), so the same
number in two different per-type charts — or in the pooled plot — refers to unrelated domains.
See the `_global_layers` variant below if you need the numbers to line up instead.

### nyan1308_pooled_plot_length_global_layers.pdf / _morphosyntactic_global_layers.pdf / _phonological_global_layers.pdf / _tonosegmental_global_layers.pdf / _intonational_global_layers.pdf

**What they show:** The same five per-type breakdowns, but built by filtering the
already-numbered pooled `tests_plot` down to one `Domain_Type`, instead of calling `df.plot()`
independently on each subset — so a domain's number here is the *same* number it carries in
`nyan1308_pooled_plot.pdf`, not a fresh 1..N local count. Lets you look up a span in one of
these breakdowns and go find the identical number in the pooled overview, or compare the same
number across two different per-type charts and know it's the same domain. The original
per-type charts above are unaffected and still get their own local numbering — both variants
are generated on every run.

---

## Pooled chart notes

- File naming matches the laminar charts above (`nyan1308_*.pdf`); these are written to
  `results/pooled/` rather than `results/laminar-families/`.
- Chart height scales with the number of distinct tests in that chart (`plot_height()`, 7 cm
  floor) so small classes like `length` (7 tests) don't render unreadably short.

## Boundary-frequency skyline

Drawn by the `planarsviz` package from the exported data bundle:

```
Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 \
  --output results --plots boundary_skyline
```

The hand-written script this came from, `nyan_boundary_skyline.r`, is archived at
`OlderFiles/planarsviz_superseded/scripts/` and is still run by the porting
check — see that directory's `README.md`.

### nyan1308_boundary_skyline.pdf

This chart counts the positions at which observed domains begin and end. The top panel pools
all tests; the lower panel has one row for starts and one for ends, with columns for the five
domain types. The active dataset contains 95 tests, so there are 95 start observations and 95
end observations. This is a distribution of test boundaries, not a frequency of unique spans
or of laminar families. The accompanying `nyan1308_boundary_counts.tsv` contains the plotted
counts.

---

## Planar structure table

Generated by `scripts/make_planar_latex.py` from
`planar_tables/planar_nyan1308.tsv` (22 positions, matching the manuscript's
own `\tref{ChichPlan}` table in `ChichewaWordhood.tex`). Each variant is written as both a
`.tex` fragment and a standalone `.pdf` preview (true white page background, not the default
transparent one — set via `xcolor`'s `\pagecolor{white}` in the preview wrapper only, not in
the `.tex` fragment itself). The preview wrappers also match the manuscript's own font setup
(`ChichewaWordhood.tex:15-20`): Times New Roman as the main font, small caps routed through TeX
Gyre Termes's real small-cap glyphs rather than a synthetically-scaled substitute.

To render:
```
python scripts/make_planar_latex.py planar_tables/planar_nyan1308.tsv
```
Add `--tex-only` to skip the PDF render (e.g. if `xelatex` isn't on `PATH`). Needs `xelatex`
specifically, not `pdflatex` — `fontspec` with a system font name only works under
xelatex/lualatex.

### nyan1308_planar_table_exact.tex / .pdf

**What it is:** A drop-in replacement for the manuscript's own `\begin{table}...\end{table}`
block — same columns (Position/Type/Elements/Description), same macro-based position labels
(`\QM`, `\Su`, ...; these are defined earlier in `ChichewaWordhood.tex` and aren't redefined in
the `.tex` fragment), same rotated "Orthographic word" side-bracket and `\hdashline` rules
around positions 5–19. The fragment requires `array`, `arydshln`, `multirow`, `graphicx` (all
already loaded in the manuscript) and a custom `\Hline` (already defined there too) — the PDF
preview supplies throwaway stand-ins for these so it can compile standalone; it isn't a claim to
match the manuscript's exact typesetting.

### nyan1308_planar_table_reduced.tex / .pdf

**What it is:** A narrower Position/Type/Elements table for slides — Position is the plain
integer (1–22), not the manuscript's `Position_Label` abbreviation (`QM`, `PrS`, `NegT`, `2P`,
...); those mix upper- and lower-case letters within a single label, which read as genuinely
mixed case next to a column that's actually small caps, not a second small-caps style. No
Description column, no orthographic-word bracket, no caption. Headings and the Elements column
are small caps; Position and Type stay plain text. No `\begin{table}` float wrapper either,
since this is meant to be pasted directly into a slide as a cropped image, not to float in a
document — the `.tex` fragment is a bare `tabular`. Its PDF is rendered with the `standalone`
document class, so the page is cropped to the table's own bounding box instead of sitting on a
full letter page — copy-paste-ready with no margin to crop out first. The table is wrapped in a
white-filled `tikz` node (not a plain `\pagecolor`) so the page is genuinely opaque, not just
apparently white — see Notes.

### Notes

- The orthographic-word boundary (positions 5–19) is hardcoded in the script
  (`ORTHOGRAPHIC_WORD_RANGE`), not stored in the TSV — it's presentation, not data.
- The manuscript's own table uses `\multirow{14}{*}{...Orthographic word}}`, but positions 5–19
  is 15 rows, not 14 — looks like an off-by-one in the hand-written version. The generated table
  computes the row count from the range instead, so it comes out as `\multirow{15}{*}{...}`.
- The PDF preview's position-label macros (`\def\QM{1\xspace}` etc.) are derived from the TSV's
  `Position_Label`/`Position` columns at render time, rather than being a second hardcoded copy
  of the manuscript's `\def` list — so the preview can't quietly drift out of sync with the TSV.
  Only the "exact" variant needs these; "reduced" doesn't use macros at all.
- `\sc` only shrinks lowercase letters into small-cap glyphs — any letter already uppercase in
  the source text stays a full-size regular capital. So header cells are written in lowercase
  (`{\sc position}`, not `{\sc Position}`) to get uniform small caps rather than one big capital
  followed by small caps.
- Both `.tex` variants were compile-checked with `xelatex` before being treated as done.
- A plain `\pagecolor{white}` doesn't reliably survive the `standalone` class's bounding-box
  crop for "reduced" — its fill sits outside what `standalone` measures as content, so it can be
  cropped away along with the rest of the unused page. This rendered as white under `pdftoppm`
  (which always flattens onto an opaque white canvas regardless of actual transparency) but was
  confirmed transparent — alpha 0 everywhere — under `pdftocairo -transp`, which preserves the
  real alpha channel. Fixed by wrapping the table in a white-filled `tikz` node instead, so the
  fill is part of the measured content rather than a separate page-level layer — verify any
  future background change against `pdftocairo -transp`, not `pdftoppm`, since the latter can't
  tell a real opaque background from a transparent one rendered onto its own default canvas.

---

## Highlighted table + matching example card

Generated by `scripts/highlight_planar_example.py` from a planar TSV plus one
example's data file (`examples/<lang>_<name>.yaml`). Produces a pair of PDFs
meant to sit side by side: a copy of the "reduced" planar table with the Position rows the
example actually uses recolored, and a standalone card of the example itself with the same
morphemes/position numbers recolored to match — one shared color, so it's visually obvious which
table rows a given glossed example draws on.

To render (given a planar TSV and an example YAML):
```
python scripts/highlight_planar_example.py \
    planar_tables/planar_nyan1308.tsv \
    examples/nyan1308_not_just_chairs.yaml
```
`--color <hex, no #>` overrides the default (`A23E40`, a dark warm red); `--positions
5,6,10,...` overrides which Position numbers get highlighted (default: every position any
morpheme in the example uses); `--tex-only` skips the PDF render.

**Example YAML format:** an example is a sequence of `lines` (each rendered as one
bracket-notation row plus one gloss row below it). Each line has `chunks` — independent words,
rendered space-separated (e.g. a question particle sitting beside a subject NP). Each chunk has
`morphemes` — bound forms of one word, rendered hyphen-chained (e.g. a verb's SM-TAM-root-FV). A
chunk of a single morpheme is just one bracketed word. A "morpheme" can itself be a multi-word
phrase under one Position — its `text`/`gloss` just contain internal spaces (e.g. a subject NP
like `"anyaní á mísala"` glossed `"2.baboon 2.ass 4.madness"` under one `Su` position); the
renderer treats `text`/`gloss` as opaque strings, so this isn't a separate case it needs to know
about. An optional per-line `trailing_punct` (e.g. `"?"`) is appended to that line's bracket row
only, not its gloss row, matching how sentence-final punctuation attaches to the last bracketed
word in the source. Top-level `language_id`, `name`, `translation`, `citation` round it out.
`nyan1308_not_just_chairs.yaml` is the simple case (one line, one chunk, the whole verb
hyphen-chained, plus one more line for the object NP); `nyan1308_mad_baboons.yaml` is the case
that actually needs more than one chunk per line (a question particle beside a subject NP; a
hyphen-chained verb beside a separate object NP).

**To add another example:** write a new `examples/<lang>_<name>.yaml` (copy
whichever of the two above is structurally closer to what you're transcribing), then run the
script against it. No code changes needed for a new example.

### nyan1308_planar_table_<name>_highlighted.tex / .pdf

**What it is:** `make_reduced()` from `make_planar_latex.py`, extended with an optional
`highlight_positions`/`highlight_color_name` pair — rows whose Position is in the set get
`\textcolor{...}` wrapped around all three cells; everything else stays plain black. Reuses the
same `PDF_WRAPPER_CROPPED` wrapper (Times New Roman, `standalone` class, white `tikz` node
background) as the plain reduced table.

### nyan1308_example_<name>.tex / .pdf

**What it is:** A standalone card reproducing the coordinator's own hand-made example slides —
one bracket-notation row plus one gloss row per YAML `line` (see the format note above), then
the translation in quotes with its citation. Gloss glyphs use full caps for grammatical glosses,
left as given for lexical ones (see Notes). Set in **Gill Sans** (the manuscript's planar table
uses Times New Roman instead — these are two different artifacts serving two different visual
roles, not meant to match each other). Same recolored-morphemes-and-subscripts treatment as the
table, using the identical color. All lines except the translation are set at their own natural
width and never wrap; the translation wraps like the coordinator's original slide, but only
within the width the other lines already established (see Notes) rather than some separately
guessed width. White background via the same white-filled `tikz` node approach as the reduced
table (see the transparency note above — a plain `\pagecolor` would have the same
problem here).

### Notes

- Position numbers in an example YAML are ChichPlan numbers (`planar_nyan1308.tsv`'s own
  numbering), not necessarily the source text's original numbering — Mchombo (2004), which the
  first example is drawn from, uses its own different slot numbers. Transcribe against
  `planar_nyan1308.tsv`, not the cited source, when adding an example.
- A morpheme with more than one `positions` entry (like the object in the first example, 21/22)
  is genuinely ambiguous between them, not a typo — see
  [issue #293](https://github.com/jcgood/planars/issues/293). Its subscript renders as
  `21/22` and it counts toward the highlight set if *either* position is highlighted.
- Only the translation line wraps, to the width of the widest other line, via a `\parbox`. The
  width is **not** measured with a `\newlength`/`\settowidth` register in the real document —
  confirmed by direct testing (bisecting a minimal reproduction down to no `tikz` layer at all:
  plain `\documentclass{standalone}`, a two-row `tabular`, `\makebox[\reg]`), a box width read
  from a length register adds stray left-side padding under the `standalone` class that an
  identical *literal* width doesn't, even when the register is set with a plain `\setlength`, no
  `\settowidth` involved. `measure_widths_pt()` instead compiles a small throwaway document that
  measures each candidate line and `\typeout`s the result, parses the printed values back out in
  Python, and `make_example_tex()` bakes the winning value into the real document as a literal
  `"123.45pt"` string. The measurement document must also receive `colordefs` (the same
  `\definecolor` the real document gets) — an undefined `\textcolor` reference silently corrupts
  the `\typeout` log parsing that follows it, which is what a first attempt at this fix ran into
  (measured a ~1118pt width for a ~365pt line). If a future change to this script needs to
  measure a line's width again, keep both of these in mind rather than reaching for `\settowidth`
  directly in the document being rendered.
- Gloss line: `format_gloss()` auto-detects grammatical vs. lexical glosses from casing in the
  YAML (`NEG`, `10OM`, `PRS-GO-JUST` → grammatical; `break`, `too`, `4.chairs` → lexical, left
  alone) and uppercases the grammatical ones — the Leipzig convention is small caps for these,
  but real small caps don't work here: tested directly, plain Gill Sans has no small-caps glyphs,
  so `{\sc ...}` silently falls back to the regular shape under fontspec rather than erroring,
  which would have printed flat lowercase text with no visual distinction at all. (The planar
  table doesn't have this problem — it pairs Times New Roman with TeX Gyre Termes specifically
  for real small-cap glyphs.) The substitute used is full caps at the *same* size as the rest of
  the gloss line, not a reduced one — genuine small-cap glyphs are drawn close to lowercase
  x-height, so real small caps read as roughly the same size as surrounding text; a same-size
  substitute matches that better than an artificially shrunk one. The case contrast alone (full
  caps vs. lowercase — `NEG` vs. `break`) carries the grammatical/lexical distinction.

---

## Tree-counting reference: Catalan vs. little Schröder (A001003) numbers

### tree_counting_equations.tex / .pdf

**What it is:** A side-by-side comparison of Catalan numbers (strictly binary trees) and the
little Schröder numbers (arbitrary n-ary trees, ≥2 children per internal node — the correct
sequence for the laminar family problem, see `../REFERENCES.md` § "Counting Constituency Trees"
and `../scripts/exploratory/catalan.py`) — what each counts, their first several values, closed
form (Catalan only — no comparably simple closed form is known for the Schröder numbers),
recurrence, and generating function. Both recurrences and generating functions were verified
numerically against the known sequences (`sympy` series expansion, checked against
`all_trees_new()`'s output) before typesetting, not just recalled from memory. Times New Roman,
white background, `standalone` class, generated the same way as the planar-table PDFs in
`make_planar_latex.py`.

### nyan1308_random_tree_overlay.r / .pdf

**What it is:** A ghost-overlay diagram of 200 uniformly-randomly-sampled n-ary trees over 22
leaves (positions), illustrating how vast the A001003(22) = 47,574,827,600,981 tree space is
relative to the 69 actual maximal laminar families found for nyan1308. Generated by
`scripts/analysis/random_tree_overlay.py`, which reuses the exact rendering convention already
established in the archived `laminar_conflict_groups.r` for its ghost
panels — each tree is a `read.tree()` Newick string sharing the same fixed leaf order, drawn via
`ggtree(..., layout='slanted') + layout_dendrogram()` with its edge layer's alpha set low and
colour forced to `'black'` (so it's inherently greyscale — edges recurring across many sampled
trees accumulate opacity), then every tree's plot stacked onto one shared `patchwork` grid cell
(identical `area()` for all 200) so they visually overlay into a single panel. No
`groupOTU`/branch-size mapping is used, unlike the conflict-groups script — there's no target
span to highlight for a purely combinatorial illustration, so every edge is uniform thickness.
No title. Tip labels use the same boxed, two-line ("position number" over "name",
`geom_tiplab(geom='label', size=5, angle=0, offset=-1, hjust=0.5, vjust=1.25, label.size=0, ...)`)
style as the archived `laminar_freqtree.r`'s `posLabel`-based tip labels, plus a widened bottom
`plot.margin` so `vjust`'s extra downward shift doesn't get clipped at the panel edge — added once
(on the last tree drawn, so the
label layer sits on top of all 200 edge layers, not underneath most of them) rather than once
per tree, since every tree shares the same leaf order and so the same tip positions after
`layout_dendrogram()`. The canvas is sized to match the frequency tree's own `ggsave` call
exactly (`width=16, height=10`, inches) — an earlier version used a physically smaller canvas
(24×16 *centimeters*, roughly half the page) that was too cramped for 22 boxed labels at this
size, and they overlapped each other.

**This is the one generated R script still sitting in `results/`** (in
`illustrations/`). It was never ported to the
package — it draws a random sample rather than a fixed chart — and is scheduled to become part
of the `illustrations` bundle in phase E of the planarsviz work.

`offset` direction was checked directly rather than inferred from the pre-flip coordinate
description (tips at `x=0`, root at negative `x`), which is easy to get backwards — two earlier
attempts (`offset=0.7`, then `offset=2.3`) did exactly that and left the box floating with a
visible gap. The check: built an isolated test tree, plotted `geom_tippoint()` at the true tip
locations next to `geom_tiplab()` boxes at a few trial offsets, and compared box position to that
known reference point directly. Negative offset pushes the box *away* from the tree, into space
that's always empty since every one of the 200 trees' tips align at the same `x` and nothing is
ever drawn beyond it — a negative offset can never hide a crossing, only add a gap below the tip;
positive offset pushes the box the other way, up into the tree, toward real crossings. `offset=0`
sits the box exactly flush on the tip — confirmed against the true tip marker — but at this box
size and line width that read as overlapping the vertex, not just touching it. `offset=-1` alone
(the frequency tree's own single-tree value) does put a small gap between the vertex and the box
— measured directly at 39px on the actual 16×10in canvas (200 dpi render) — but that gap turned
out too small to read as clearly separated at normal viewing scale; anti-aliasing on the thin
low-alpha lines makes a gap that size still look like it's touching the box corner. Adding
`vjust=1.25` on top of the same `offset=-1` roughly triples that gap to 111px, measured the same
way (true tip marker vs. box-top pixel row) — a difference easy to miss eyeballing a screenshot but
obvious once measured, which is why it's stated in pixels here rather than only described.

Trees are **sampled, not enumerated** — 47.5 trillion trees is computationally and visually
infeasible. The sampler (`sample_tree()`/`sample_forest()` in `random_tree_overlay.py`) uses the
standard method for turning a counting recurrence into a uniform sampler: at each split, the
choice is weighted by how many completions it contributes (`all_trees_new(j) *
_ordered_forests(n-j)`, mirroring the recurrence's own terms), which yields an exactly-uniform
sample over the whole tree space — verified directly by sampling 11,000 trees at n=4 (11 distinct
shapes) and confirming each appeared at ~9.09% ± noise, matching 1/11.

To render:
```
python scripts/analysis/random_tree_overlay.py
```
`--n-trees`, `--n-leaves`, `--alpha`, `--seed` (for a reproducible sample), `--r-only` (skip the
R render, just write the `.r` file) are all adjustable — see the script's own docstring.

**Note on what the picture shows:** the regular criss-cross lattice visible in the render is a
real mathematical property of uniform sampling, not an artifact — near-balanced binary-like
splits vastly outnumber lopsided ones combinatorially, so they dominate visually even though
every internal node is allowed ≥2 children, not just 2.

## Maximal laminar family counts

### nyan1308_tree_count_all.pdf / _by_class.pdf / _bundles.pdf / _without_adjacent.pdf / nyan1308_tree_counts.tsv

**What it is:** Bar charts (and the underlying counts) summarizing how many maximal laminar
families ("trees" in the project's terms — a maximal set of observed spans that are mutually
nested or disjoint) nyan1308's data supports under a few conditions. The counting is
`scripts/analysis/laminar_tree_counts.py`, which reuses `laminar_analysis.py`'s own span-loading
and family-enumeration logic, so these counts agree with the conflict and forest charts above.

- **`nyan1308_tree_count_all.pdf`** — single bar: 69 maximal families across all 26 unique
  observed spans (all domain classes pooled).
- **`nyan1308_tree_count_by_class.pdf`** — one bar per domain class (morphosyntactic,
  phonological, tonosegmental, intonational, length), each colored to match the pooled
  constituency charts. **Read this one next to the fragmentation test below**: a class with more
  tests has more chances to produce conflicting spans, so these bars are not comparable across
  classes as they stand.
- **`nyan1308_tree_count_bundles.pdf`** — the same, for the three pooled bundles
  (phonology-like, syntax-like, syntax-like without tonosegmental).
- **`nyan1308_tree_count_without_adjacent.pdf`** — "all tests" vs. "without size-2 spans"
  (adjacent-position spans), to see how much of the family count is driven by trivially-adjacent
  pairs.
- **`nyan1308_tree_counts.tsv`** — the raw counts behind all four charts: `condition` (`all_tests`
  / `without_adjacent_spans`), `class` (`all`, one domain class, or one bundle),
  `n_unique_spans`, `n_maximal_laminar_families`.

To regenerate the TSV:
```
python scripts/analysis/laminar_tree_counts.py
```
`--domain-file`, `--domains-dir`, `--output-dir` are adjustable — see the script's own docstring.
The charts come from the two commands at the top of this file
(`--plots tree_count_all,tree_count_by_class,tree_count_bundles,tree_count_without_adjacent`).
Until the 2026-09-20 cutover this script drew them itself, in matplotlib; the package redraws
them in ggplot, so they differ from the pre-cutover PDFs by fonts and a pixel of canvas height.

## Is a class more fragmented than its number of tests predicts?

### nyan1308_fragmentation_test_plot.pdf / nyan1308_class_fragmentation_test.tsv / nyan1308_bundle_fragmentation_test.tsv / nyan1308_fragmentation_null_draws.tsv

**What it is:** The family counts in the charts above cannot be compared across classes as they
stand. A class with more tests has more chances to produce spans that conflict with each other,
so a high family count may say nothing except that the class was well studied. This chart puts
each count against what chance alone would give a class of that size.

The test shuffles the `Domain_Type` labels across the 95 cleaned test rows, holding each class's
row count fixed, rebuilds the conflict graph and re-counts maximal families — 5000 times. Only
which label sits on which row is randomised; the spans themselves never move. Classes and the
three bundles share one set of draws, which is sound because a bundle's own test count does not
change under a per-type shuffle.

- **`nyan1308_fragmentation_test_plot.pdf`** — one horizontal violin per group (the null
  distribution from the 5000 draws) with the observed family count as a filled dot, classes and
  bundles as two stacked panels on a shared axis, and the p-value printed on each row.
- **`nyan1308_class_fragmentation_test.tsv`** — five domain types;
  **`nyan1308_bundle_fragmentation_test.tsv`** — the three bundles. Columns: `group`, `color`,
  `n_tests`, `observed_families`, `null_mean`, `null_p05`, `null_p95`, `p_value_le_observed`, and
  `n_permutations` / `seed`, which record the run that produced the file. `p_value_le_observed` is
  the fraction of permutations with family count <= observed; small = unusually laminar, the same
  "small p = more tree-like" direction `span_placement_test.py`'s own p-value uses (see "Does the
  real arrangement produce fewer trees..." below) — this column used to be `p_value_ge_observed`
  (fraction >= observed, so small p meant *more fragmented*), which pointed the opposite way from
  every other p-value in this file and was flipped to match.
- **`nyan1308_fragmentation_test_syntax_phon_plot.pdf`** — the same chart filtered to the two
  bundles (`phonologylike`, `syntaxlike`) on their own, drawn for a talk. A single un-faceted
  panel: with one `kind` left there was nothing for the facet strip to distinguish, so it is
  dropped. Drawn by the package since 2026-09-21, as
  `--plots fragmentation_test_syntax_phon_plot`.
- **`nyan1308_fragmentation_null_draws.tsv`** — every individual draw, long format (`group`,
  `kind`, `family_count`), so the chart can be redrawn without re-running the permutation.

**What it shows:** tonosegmental's 9 families read as the worst fragmentation in
`nyan1308_tree_count_by_class.pdf`, but tonosegmental carries 44 of the 95 tests, and a random
44-test sample typically yields about 17 families. It is therefore markedly *more* laminar than
chance (p=0.143), not less — and intonational more sharply still (p=0.034, 1 family against an
expected 3.4; 1 is also the theoretical floor for any nonempty span set, per REFERENCES.md's "hard
floor at exactly 1 survivor" — under the old `p_value_ge_observed` convention this floor made
intonational's p trivially 1.0 no matter how surprising the result was, since every null draw is
also >= 1; `p_value_le_observed` doesn't have that degeneracy). Morphosyntactic, phonological and
length sit where chance puts them. The bundles inherit the pattern: phonologylike (p=0.160) and
syntaxlike (p=0.112) are each carried by their most laminar component, and dropping tonosegmental
from syntaxlike moves it back toward unremarkable (p=0.454).

To regenerate the tables:
```
python scripts/analysis/class_fragmentation_test.py
```
The plain command reproduces the committed files exactly (5000 draws, seed 0). `--n-permutations`
and `--seed` are adjustable; both summary files record what they were.

**Both charts come from the package** (chart 19, `--plots fragmentation_test_plot` and
`--plots fragmentation_test_syntax_phon_plot`), but this is the
one chart whose bundle tables are not written on every export:

```
python scripts/analysis/export_planarsviz_data.py \
  --domain-file domains/domains_nyan1308.tsv \
  --output-dir results/planarsviz --language-name Chichewa \
  --fragmentation-permutations 5000
```

Without `--fragmentation-permutations` the bundle simply has no fragmentation tables and the
chart says so. The test takes about four minutes where the rest of an export takes 1.6 seconds,
which is why it is asked for rather than assumed. `fragmentation_test_plot.r`, which drew both
charts before the package did, was archived to
`OlderFiles/planarsviz_superseded/scripts/analysis/` on 2026-09-21 — until then it and the
package both wrote `nyan1308_fragmentation_test_plot.pdf`, whichever ran last winning, with
nothing recording which. Since there was never a matplotlib version, the charts it drew are the
references the porting checks compare against.

The null distributions go into the bundle as a tally (`fragmentation_null.tsv`: one row per
distinct family count per group, with how many draws gave it) rather than one row per draw —
227 rows instead of 40,000, losing only draw order, which the seed reproduces.

## Does the real arrangement produce fewer trees than the spans' own lengths alone would predict?

### nyan1308_span_placement_test_by_group_plot.pdf / nyan1308_span_placement_test.tsv / nyan1308_span_placement_null_tally.tsv

**What it is:** A different question from the fragmentation test above, though it looks similar.
That one asked whether a class's family count was surprising given how many *tests* it has,
by shuffling which label sits on which test while every span stayed put. This one holds a
group's own span *lengths* fixed and asks whether the real *positions* of those spans — not
their count, their actual placement on the planar structure — produce fewer conflicting trees
than an arbitrary placement of same-length spans would. A direct test of the Tree hypothesis:
do real constituency domains nest more than their sizes alone would explain?

The null redraws every span at a uniformly random legal left edge for its own length (a
length-22 span has exactly one legal position on this 22-position structure; a length-2 span has
21 — smaller spans get more freedom purely as a consequence of this constraint, nothing extra
is built in), grouped by length so same-length spans can never collide, keeping each replicate's
span count identical to the real group's. Every group draws over the full 22-position structure
regardless of its own observed range, matching the project-wide convention that a subset
analysis still spans the complete structure. Run for the pooled dataset ("all"), the five domain
types, and the three bundles — 5000 draws each, one shared random stream across all nine so the
whole run reproduces from one seed.

- **`nyan1308_span_placement_test_by_group_plot.pdf`** — one panel per group: a histogram and
  density curve of that group's own null distribution, the real observed count as a dashed
  vertical line, the count and p-value printed in-panel. Panels use independent axes (`scales =
  "free"`), not a shared one — unlike the fragmentation-test chart, the absolute family count
  here is not comparable across groups of very different span counts, so each panel is read on
  its own terms.
- **`nyan1308_span_placement_test.tsv`** — one row per group. Columns: `group`, `n_spans`,
  `n_positions`, `observed_families`, `n_permutations`, `seed`, `n_truncated`, `null_mean`,
  `null_p05`, `null_p50`, `null_p95`, `p_value_le_observed` (the fraction of null draws at or
  below the observed count — small means the real arrangement is unusually laminar for its
  length profile).
- **`nyan1308_span_placement_test_syntaxlike_plot.pdf`** and
  **`nyan1308_span_placement_test_phonologylike_plot.pdf`** — each bundle on its own, one panel,
  filled in that bundle's own laminar-forest colour (`#BC3C29` and `#0072B5`) rather than the
  neutral blue the nine-panel chart uses, with larger axis and title text for projection. They
  replace an earlier combined two-bundle file, which is deleted rather than kept alongside them.
- **`nyan1308_span_placement_null_tally.tsv`** — `(group, family_count, n)`: how many of the 5000
  draws gave each family count, per group, rather than one row per draw.

**What it shows:** morphosyntactic (p=0.019) and syntax-like without tonosegmental (p=0.020) are
genuinely more tree-like than their own span lengths predict — a real, if modest, effect.
Syntax-like (p=0.051) and phonology-like (p=0.077) trend the same way more mildly. Tonosegmental
(p=0.755) and intonational (p=0.901) trend the other way — not more coherent than chance given
their sizes, if anything slightly less so, though intonational has only 3 spans and very little
room for this number to move regardless of the real linguistic structure. The pooled result
(p=0.335) is unremarkable on its own — the breakdown is where the real signal is, and it points
in a different direction than the fragmentation test's own findings, since the two ask genuinely
different questions about the same 26 spans.

To regenerate the tables:
```
python scripts/analysis/span_placement_test.py
```

**All three charts come from the package** since 2026-09-21 —
`--plots span_placement_test_by_group_plot`, `_syntaxlike_plot`, `_phonologylike_plot`. Like the
fragmentation chart, they need a bundle exported with the test asked for:

```
python scripts/analysis/export_planarsviz_data.py \
  --domain-file domains/domains_nyan1308.tsv \
  --planar-file planar_tables/planar_nyan1308.tsv --language-name Chichewa \
  --span-placement-permutations 5000
```

The exporter calls `span_placement_test.py`'s own `run_test()`, so the bundle and the committed
TSVs above carry the same numbers. `span_placement_test_plot.r`, which drew all three charts
before the package did, was archived to `OlderFiles/planarsviz_superseded/scripts/analysis/`.

## Is the family count remarkable for that many arbitrary spans?

### nyan1308_arbitrary_layers_test_by_group_plot.pdf / nyan1308_arbitrary_layers_test.tsv / nyan1308_arbitrary_layers_null_tally.tsv

**What it is:** the third and weakest of the project's three permutation nulls, and the one a
raw family count is implicitly read against. It holds nothing about the real data except how
many spans each group has: every draw picks that many intervals of arbitrary size at arbitrary
positions. Generated by `scripts/analysis/arbitrary_layers_test.py` (5000 draws, seed 0), one
panel per group.

The three tests differ deliberately, and the ordering is the point:

| Test | What it holds fixed | What it randomizes |
|---|---|---|
| `class_fragmentation_test.py` | every span's position | which domain-type label sits on which test |
| `span_placement_test.py` | each span's own length | that span's position |
| `arbitrary_layers_test.py` | only how many spans there are | size and position together |

**Where the root goes.** If a group's real spans include the full-structure span [1–22] — the
pooled set does, since `synthetic_root` is false for nyan1308 — the null fixes that span and
draws the rest freely. A group without it draws all of them freely. Either way the null and the
observed set agree on span count and on whether one span covers everything, so only the
arbitrary sizes and positions vary. The `includes_root` column records which applied.

**What it shows, and it is not what the pooled number alone suggests.** Pooled, nyan1308's 69
families sit at p=0.287 against a null averaging 90.9 — unremarkable, almost the middle of the
distribution. But the breakdown is where the signal is: **syntax-like (p=0.014) and
morphosyntactic (p=0.044) are unusually laminar even against this weakest null**, with
phonology-like (p=0.058) and syntax-like without tonosegmental (p=0.064) just outside.
Tonosegmental (p=0.540), intonational (p=0.666) and length (p=0.549) are not.

So the pooled "nothing to see" verdict masks real subgroup structure. The practical consequence
is for how the headline number is stated: "69 families out of 47 trillion possible trees"
compares against the space of all trees, which makes any real dataset look tiny almost by
construction, and against a baseline that knows only "these are 26 arbitrary spans" the pooled
69 is not special. What carries the weight is the per-group result — here and in the
span-placement test, which asks the same question one notch less naively.

To regenerate the tables:
```
python scripts/analysis/arbitrary_layers_test.py
```

The chart comes from the package (`--plots arbitrary_layers_test_by_group_plot`) and needs a
bundle exported with `--arbitrary-layers-permutations 5000`. Unlike every other chart here it
has no reference image: no earlier script ever drew it, so the renderer check reports it as
having none. What it is checked against instead is the committed TSVs above, which the bundle
must reproduce.

**The enumeration cap is raised for this test only.** Arbitrary intervals cross far more
chaotically than real linguistic domains do, and `laminar_analysis.MAX_FAMILIES`'s default of
1000 truncates this null badly — a truncated draw is counted as its cap rather than its real
value, biasing every summary downward. `arbitrary_layers_test.py` raises it to 50,000 for the
duration of a run and restores it afterwards, so no other caller is affected, and a bundle test
fails if any draw hit the raised cap anyway.

## How much tree structure each family leaves open

### nyan1308_refinement_counts.tsv / nyan1308_refinement_polytomies.tsv

**What it is:** A maximal laminar family is not a single tree. Where a node has more than two
children (a polytomy), the observed spans do not say how those children group, so each polytomy
stands for many finer trees. These two tables count them, per family and per polytomy, generated
by `scripts/analysis/refinement_counts.py`.

Two conventions are reported side by side, because whether a constituent must be binary is an
open question rather than a settled one:

- **little Schröder per polytomy** — any arity allowed in the refinement. The project calls this
  sequence "super-Catalan" (see `scripts/exploratory/catalan.py`). Total across all 69 families:
  8,599,689.
- **Catalan per polytomy** — binary refinements only. Total: 125,032.

- **`nyan1308_refinement_counts.tsv`** — one row per maximal family.
- **`nyan1308_refinement_polytomies.tsv`** — one row per distinct polytomy node (its span edges,
  arity, how many families contain it, and its count under each convention), so the totals can be
  checked against the nodes they were multiplied from rather than taken on trust.

To regenerate:
```
python scripts/analysis/refinement_counts.py
```

---

## Charts covered only by the catalogue

These are in `results/` and drawn by the same two commands at the top of this
file, but have no section of their own here — there is nothing to say about
them beyond what they are, and
[`../docs/planarsviz_charts.md`](../docs/planarsviz_charts.md) says that,
with an example image, its options and its canvas size.

| File | `--plots` name | Catalogue section |
|---|---|---|
| `nyan1308_laminar_overlay.pdf`, `_legend.pdf` | `laminar_overlay`, `laminar_overlay_legend` | 5. Stacked overlays |
| `nyan1308_all_families_labeled_orthographic_word.pdf`, `_legend.pdf` | `all_families_labeled_orthographic_word`, `…_legend` | 5. Stacked overlays |
| `nyan1308_morsyn_laminar_forest.pdf` and the other seven `*_laminar_forest.pdf` | `morsyn_laminar_forest` … | 4. Per-class laminar forests |
| `nyan1308_most_binary_tree.pdf`, `_orthographic_word.pdf` | `most_binary_tree`, `most_binary_tree_orthographic_word` | 6. Frequency tree |
| `nyan1308_forestspans_plot.pdf`, `_no_tono.pdf` | `forestspans_plot`, `forestspans_plot_no_tono` | 10. ForestSpans plot |
| `nyan1308_boundary_strength.pdf`, `_no_tono.pdf`, `_distributions.pdf` | `boundary_strength`, … | 12. Boundary strength |
| `nyan1308_boundary_strength_overlay.pdf`, `_no_tono.pdf` | `boundary_strength_overlay`, `…_no_tono` | 13. Boundary-strength overlay |

The numbers behind the last four rows come from Python, and those commands are
worth knowing separately from the drawing:

```
python scripts/analysis/boundary_strength.py
python scripts/make_forestspans_table.py
```

The first writes `nyan1308_boundary_strength.tsv`. The second writes the
ForestSpans LaTeX table — `nyan1308_forestspans_table.tex` for the manuscript
and `nyan1308_forestspans_slide.tex`/`.pdf` for slides — which is a table, not
a chart, and has no catalogue entry. (It needs `xelatex` on PATH for the slide
PDF; `--tex-only` skips that and writes just the sources.)

`nyan1308_boundary_strength_no_tono.tsv` is the same computation over the four
non-tonosegmental domain types. The exporter writes it into the bundle at
`results/planarsviz/nyan1308/data/subsets/no_tono/boundary_strength.tsv`, and
the copy in `results/boundaries/` carries the shorter name by hand:
`boundary_strength.py --subset morphosyntactic,phonological,length,intonational`
produces identical numbers but names its file after all four types. The copy is
kept because a porting check compares the bundle against it.

## Other files in results/

- `nyan1308_laminar_analysis.md` — a one-off written summary of the analysis
  from 2026-04-18, not generated by anything. Its span-occurrence table and
  hypothesis discussion still hold; its position labels came from
  `treeTraversal.py`, the superseded enumerator, so treat the prose as the
  record of a moment rather than current output.
- `nyan1308_planarsviz_manifest.tsv` — written by `render_planarsviz.R` on
  every run: one row per chart file here, with that chart's canvas size, and
  what the renderer check reads to know which files to compare. A `--plots`
  run merges into it rather than replacing it, so a partial render does not
  shrink it to the few charts it drew; a row whose file has gone is dropped,
  so it keeps describing what is actually in this directory.
- `supercatalan_trees_n2.pdf`, `_n3.pdf`, `_n4.pdf`, `_n5_sample15.pdf` —
  every distinct n-ary tree shape over 2, 3 and 4 leaves, and 15 sampled
  shapes of the 45 over 5 leaves. Illustrations for the counting discussion
  in `../REFERENCES.md`, not analyses of any language. Regenerate with
  `python scripts/exploratory/generate_supercatalan_rows.py --pdf`, which
  calls the R renderer and `pdfcrop` itself; without `--pdf` it only rewrites
  `scripts/exploratory/supercatalan_trees.json`, the shapes the renderer
  draws. (`render_supercatalan_rows.r` reads that file from the working
  directory, so it only runs correctly the way the Python script launches it,
  from `scripts/exploratory/`.) Scheduled to move into the `illustrations`
  bundle in phase E alongside `nyan1308_random_tree_overlay.r`.
- `results/planarsviz/` — the exported bundle (`nyan1308/data/`), the frozen
  reference images the porting checks compare against (`reference/`), and the
  comparison images those checks write (`comparisons/`, including
  `comparisons/shifted/`). Both `reference/` and `comparisons/` are grouped
  by topic into four subfolders — `laminar-families/`, `pooled/`,
  `boundaries/`, `counts-and-chance/` — so a chart's images always sit next
  to the other charts of its kind. A bundle's own `plots/` directory is
  written but not tracked in git; the published copies are the PDFs in
  `results/` itself.
