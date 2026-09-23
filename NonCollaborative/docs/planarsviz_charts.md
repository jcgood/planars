# planarsviz chart catalogue

Every chart the library draws: what it shows, the call, its options, the
canvas it was designed for, and an example from nyan1308 (Chichewa). The
**renderer name** is what `scripts/render_planarsviz.R --plots` takes and
what follows the dataset in the file name; **old file** is the file in
`results/` it replaces.

The canvases below are for 22 positions (nyan1308). Every chart with a
position axis is widened in proportion for a structure with more
(28 positions: 28/22 of the width); one with 22 or fewer keeps the width
shown. Heights and the count and permutation-test charts, which have no
position axis, do not change.

Setup for every example:

```r
library(planarsviz)
bundle <- read_planars_bundle("results/planarsviz/nyan1308")
```

Contents: [Pooled plots](#1-pooled-plots) ·
[Boundary skyline](#2-boundary-frequency-skyline) ·
[Span chart](#3-span-frequency-chart) ·
[Forests](#4-per-class-laminar-forests) ·
[One family of a forest](#4a-one-family-of-a-forest-on-its-own) ·
[Overlays](#5-stacked-overlays) ·
[Frequency tree](#6-frequency-tree) ·
[Four trees](#7-four-trees) ·
[Conflict groups](#8-conflict-groups) ·
[Exemplary trees](#9-exemplary-trees-and-slides) ·
[ForestSpans](#10-forestspans-plot) ·
[Tree counts](#11-tree-count-bar-charts) ·
[Boundary strength](#12-boundary-strength) ·
[Boundary-strength overlay](#13-boundary-strength-overlay) ·
[Fragmentation test](#14-fragmentation-test) ·
[Span placement](#15-span-placement-test) ·
[Arbitrary layers](#16-arbitrary-layers-test) ·
[Illustrations](#17-illustrations) ·
[Boundary-strength test](#18-boundary-strength-test) ·
[Name changes](#name-changes-for-cutover)

---

## 1. Pooled plots

One line per test across the planar positions, coloured by domain type.
Tests that pick out the same span share a numbered layer (1 = largest). The
dotted line marks the root.

![Pooled plot](planarsviz_charts/pooled_plot.png)

```r
plot_pooled(bundle)                                        # all tests
plot_pooled(bundle, group_by_domain = TRUE)                # rows grouped by domain type
plot_pooled(bundle, domain_types = "phonological", layers = "local")
plot_pooled(bundle, domain_types = "phonological", layers = "global")
```

| Option | Meaning |
|---|---|
| `domain_types` | `NULL` for all tests, or the types to keep. |
| `layers` | With `domain_types`: `"local"` renumbers layers for those tests alone; `"global"` keeps the numbers they have in the all-tests plot, so "layer 3" means the same thing on every chart. |
| `group_by_domain` | Group rows by domain type first (all tests only). |

Canvas: 26 cm wide (25 cm for one type); height grows with the number of
tests (0.7 cm each, at least 7 cm).

| Renderer name | Old file |
|---|---|
| `pooled_plot` | `nyan1308_pooled_plot.pdf` |
| `pooled_domainplot` | `nyan1308_pooled_domainplot.pdf` |
| `pooled_plot_<type>` | `nyan1308_pooled_plot_<type>.pdf` |
| `pooled_plot_<type>_global_layers` | `nyan1308_pooled_plot_<type>_global_layers.pdf` |

Grouped by domain type · one type, local layers · one type, global layers:

![Grouped](planarsviz_charts/pooled_domainplot.png)
![Phonological](planarsviz_charts/pooled_plot_phonological.png)
![Phonological, global layers](planarsviz_charts/pooled_plot_phonological_global_layers.png)

---

## 2. Boundary-frequency skyline

How often each position is the start or end of a test's span: all tests in
the top panel, then split by domain type.

![Boundary skyline](planarsviz_charts/boundary_skyline.png)

```r
plot_boundary_skyline(bundle)
```

No options. Canvas 16 × 11 in. The counts behind it are attached as
attribute `planarsviz_boundary_counts`.
Renderer name `boundary_skyline`; old file `nyan1308_boundary_skyline.pdf`.

---

## 3. Span-frequency chart

Every span except the full root as a horizontal segment, ordered by how many
maximal families contain it (fewest at the bottom); width and opacity show
that share, colour the span's main domain type.

![Span chart](planarsviz_charts/spanchart.png)

```r
plot_span_chart(bundle)
```

| Option | Meaning |
|---|---|
| `positions` | `"all"` (default) shows every position in the planar structure; `"drawn"` shows only the stretch the charted spans cover, as the old file does — which silently dropped position 1, reached only by the excluded full root. |

Canvas 14 × 8 in. Renderer name `spanchart`; old file
`nyan1308_spanchart.pdf`.

---

## 4. Per-class laminar forests

All maximal families of one domain type (or bundle of types), each drawn as
a faint tree and stacked, so structure shared by many families reads darker
and thicker.

![Phonological forest](planarsviz_charts/phon_laminar_forest.png)

```r
plot_laminar_forest(bundle, "phon")
```

| Option | Meaning |
|---|---|
| `forest_id` | A class id from the bundle's `forests.json`: `morsyn`, `tono`, `length`, `phon`, `inton`, or a bundle `phonologylike`, `syntaxlike`, `syntaxlike_notono`. |

Canvas 20 × 14 in. Renderer name `<id>_laminar_forest`; old file
`nyan1308_<id>_laminar_forest.pdf`.

### 4a. One family of a forest, on its own

The same forest taken apart: each maximal family drawn as its own labelled
tree, rather than stacked with the rest. Drawn by the same code as the
exemplary trees below, keyed by forest and tree number instead of family id.

![One syntax-like family](planarsviz_charts/syntaxlike_tree_09.png)

```r
plot_forest_tree(bundle, "syntaxlike", 9)
```

| Option | Meaning |
|---|---|
| `forest_id` | As above. |
| `tree_number` | Which family of that forest, as numbered in `data/forests/<forest_id>.tsv` (1 = first). |

Canvas 12 × 8 in. Renderer names `<id>_tree_<nn>`, one per tree of every
forest — 48 for nyan1308, the number padded to at least two digits. Old files
`nyan1308_phonologylike_tree_01.pdf` … `_06.pdf` and
`nyan1308_syntaxlike_tree_01.pdf` … `_16.pdf`; the other six forests' trees
had no older file, having never been drawn before the package drew them.

---

## 5. Stacked overlays

Every maximal family of one or more groups stacked in one panel: darkness
shows how many trees share a branch, thickness how many tests support the
span. One function draws the coloured domain-type overlay, the black
all-families overlay, and the version with highlighted position labels.

![Overlay with legend](planarsviz_charts/laminar_overlay_legend.png)

```r
plot_laminar_overlay(bundle)                                   # coloured by domain type
plot_laminar_overlay(bundle, groups = "all", alpha_divisor = 1,
                     thickness_exponent = 0.75)                # all families
plot_laminar_overlay(bundle, groups = "all", alpha_divisor = 1,
                     thickness_exponent = 0.75,
                     highlight = "orthographic_word")          # word highlighted
# add legend = TRUE to any of these for the legend version
```

| Option | Meaning |
|---|---|
| `groups` | `NULL` = every domain-type group, coloured; `"all"` = every family of the full data; or group ids from `overlay_groups.json`. |
| `alpha_divisor` | Divides each tree's opacity, `1 − 0.01^(1/trees)`. |
| `thickness_exponent` | Line thickness is convergence to this power. |
| `legend` | Add an inset legend: a colour key for several groups, a darkness/thickness key for one. |
| `highlight` | A highlight id from `highlights.tsv` to colour position labels by. |
| `legend_thickness_exponent` | Exponent for the legend's "More" thickness swatch; defaults to `thickness_exponent`, so the swatch matches the thickest lines. The old legends always used 0.5, which was too thin for the all-families charts; `0.5` reproduces them. |

Canvas 20 × 14 in.

| Renderer name | Old file |
|---|---|
| `laminar_overlay`, `laminar_overlay_legend` | `nyan1308_laminar_overlay.pdf`, `_legend.pdf` |
| `all_families_labeled`, `_legend` | `nyan1308_all_families_labeled.pdf`, `_legend.pdf` |
| `all_families_labeled_orthographic_word`, `_legend` | `nyan1308_all_families_labeled_wordhood.pdf`, `_legend.pdf` |

All families, orthographic word highlighted:

![Highlighted overlay](planarsviz_charts/all_families_labeled_orthographic_word_legend.png)

---

## 6. Frequency tree

The most consensus-like family — the one whose spans occur in the most
families overall — with each branch's opacity and thickness showing the
share of all families containing it.

![Frequency tree](planarsviz_charts/freqtree.png)

```r
plot_frequency_tree(bundle)
```

| Option | Meaning |
|---|---|
| `selection` | Which selection in `selections.tsv` to draw (default `"consensus_all"`). |
| `title` | Plot title; the default names the number of families. |
| `weight` | What branch opacity and thickness show: `"families"` (default, the share of families containing the span), `"tests"` (support relative to the best-tested span), or `"none"` (solid — shape alone). |
| `branch_size` | Thickness of a fully supported branch. Defaults to 4, the weighted charts' heaviest line; with `weight = "none"`, where every branch would be drawn at that weight, it defaults to 0.5 — ggtree's own default, matching the exemplary trees. |

Canvas 16 × 10 in. Renderer name `freqtree`; old file `nyan1308_freqtree.pdf`.

### 6a. Maximal binary branching

The same drawing used for an illustration: the family that branches most
binarily, drawn solid. Every span rests on at least one test, so this is the
most branching structure the data supports — for nyan1308, 13 nested spans
with 7 strictly binary nodes and nothing wider than four children.

![Maximal binary branching](planarsviz_charts/most_binary_tree.png)

```r
plot_frequency_tree(bundle, selection = "most_binary", weight = "none",
                    title = "Maximal binary branching supported by the data")
```

Renderer name `most_binary_tree`; no old file — this chart is new. The
exporter picks the family (`most_binary` in `selections.tsv`): most strictly
binary nodes, then most tests behind the tree, then the narrowest widest
node.

A second version traces a highlight's extent — for nyan1308, the
orthographic word — with thicker edges running down to its first and last
positions:

![Word extent traced](planarsviz_charts/most_binary_tree_orthographic_word.png)

```r
plot_frequency_tree(bundle, selection = "most_binary", weight = "none",
                    emphasis = "orthographic_word")
```

| Option | Meaning |
|---|---|
| `emphasis` | A `highlight_id` from `highlights.tsv`; its first and last positions are traced. `NULL` (default) traces nothing. |
| `emphasis_size` | Thickness of the traced edges (default 2.5). |

The traced edges are those covering one of the two positions but not the
other — the path from each boundary tip up to the smallest node holding
both. Renderer name `most_binary_tree_<highlight_id>`, one per highlight in
the bundle.

---

## 7. Four trees

The most consensus-like family overall and in each conflict group, each
weighted by frequency within its group. Needs conflict groups in the bundle.

![Four trees](planarsviz_charts/four_trees.png)

```r
plot_four_trees(bundle)
```

| Option | Meaning |
|---|---|
| `other_label` | Title text for the group of families with no defining span (default `"neither"`). |

Canvas 24 × 16 in (three groups in a 2 × 2 grid; other numbers of groups two
per row). Renderer name `four_trees`; old file `nyan1308_four_trees.pdf`.

---

## 8. Conflict groups

Every family stacked in a large panel, and below it one panel per conflict
group. Groups larger than the exporter's cap (12) show a selection chosen to
cover every span in the group.

![Conflict groups](planarsviz_charts/conflict_groups.png)

```r
plot_conflict_groups(bundle)
```

| Option | Meaning |
|---|---|
| `other_label` | As for four trees. |
| `panel_titles` | Show each panel's title (default `TRUE`). The old chart's titles never appeared; `FALSE` reproduces it. |
| `title_size` | Title size in points (default 24). |

Canvas 24 × 20 in. Renderer name `conflict_groups`; old file
`nyan1308_conflict_groups.pdf` (which has no visible titles).

---

## 9. Exemplary trees and slides

Representative families (chosen to cover the variety of spans, plus the
family with the least evidence), each drawn as a clean tree beside the
pooled plot of the tests that produced it. Layer numbers are the all-tests
plot's. Also as a pair of 16:9 slides.

![Exemplary tree page](planarsviz_charts/exemplary_trees_1.png)

```r
plot_exemplary_tree(bundle, rank = 1)                          # print page
plot_exemplary_tree(bundle, rank = 1, view = "slide_tree")
plot_exemplary_tree(bundle, rank = 1, view = "slide_evidence")
```

| Option | Meaning |
|---|---|
| `rank` | Which selected family (1 to 7 for nyan1308). |
| `view` | `"page"`, `"slide_tree"` or `"slide_evidence"`. |
| `selection` | A selection in `selections.tsv` (default `"exemplary"`). |

Canvas: page 76 cm wide, slide tree 13.333 × 7.5 in, evidence 25 cm wide;
page and evidence heights grow with the number of tests.

| Renderer name | Old file |
|---|---|
| `exemplary_trees_<n>` | `nyan1308_exemplary_trees_<n>.pdf` |
| `exemplary_trees_slide_<n>_tree` | `nyan1308_exemplary_trees_slide_<n>_tree.pdf` |
| `exemplary_trees_slide_<n>_evidence` | `nyan1308_exemplary_trees_slide_<n>_evidence.pdf` |

Slide tree · slide evidence:

![Slide tree](planarsviz_charts/exemplary_trees_slide_1_tree.png)
![Slide evidence](planarsviz_charts/exemplary_trees_slide_1_evidence.png)

---

## 10. ForestSpans plot

One row per span, ordered by how many maximal families contain it, drawn
like a pooled plot with its layer number at both edges, in a colour blended
from its domain types, with the family count at the right.

![ForestSpans plot](planarsviz_charts/forestspans_plot.png)

```r
plot_forestspans(bundle)
plot_forestspans(bundle, subset = "no_tono")    # fresh analysis without tonosegmental
```

| Option | Meaning |
|---|---|
| `subset` | `NULL`, or a subset id from `subsets.json`; its layers and counts are its own. |
| `legend_position` | `"inside"` (default) puts the colour key in the panel's empty lower-left corner, in a bordered white box; `"right"` puts it beside the panel, as the old file has it. |
| `legend_inside` | Where the inset legend's lower-left corner sits, as a share of the panel. |
| `count_header_size` | Sizes of the count column's header, `c(trees, n)`: "Trees" (default 6) above a smaller "(n = N)" (default 4.5). `NULL` gives the old single label, both lines at size 4. |

Canvas 34 × 24 cm. Renderer names `forestspans_plot`,
`forestspans_plot_<subset>`; old files `nyan1308_forestspans_plot.pdf`,
`_no_tono.pdf`.

---

## 11. Tree-count bar charts

How many maximal families the data allows: per domain type, per class
bundle, for all tests, and for all tests without size-2 spans. The two
horizontal charts have transparent backgrounds for slides.

![Tree counts by class](planarsviz_charts/tree_count_by_class.png)

```r
plot_tree_counts(bundle, "by_class")
plot_tree_counts(bundle, "bundles")
plot_tree_counts(bundle, "all")
plot_tree_counts(bundle, "without_adjacent")
```

Canvas: 8 × 3.8 in (by class, bundles), 7 × 5 in (all), 8 × 5 in (without
adjacent). Renderer names `tree_count_<chart>`; old files
`nyan1308_tree_count_<chart>.pdf`. Ported from matplotlib: fonts differ
slightly from the old files.

![Without size-2 spans](planarsviz_charts/tree_count_without_adjacent.png)

---

## 12. Boundary strength

How strongly each position is a left (top) or right (bottom) constituent
edge: bars add up each span's family count over the spans starting or ending
there; black marks count the families with at least one such span, never
above the dotted line at the family count. The distributions chart shows
the same strengths as two smoothed curves.

![Boundary strength](planarsviz_charts/boundary_strength.png)

```r
plot_boundary_strength(bundle)
plot_boundary_strength(bundle, subset = "no_tono")
plot_boundary_strength_distributions(bundle)
```

| Option | Meaning |
|---|---|
| `subset` | `NULL`, or a subset id from `subsets.json`. |
| `bar_colour` | Bar colour (bars chart). |
| `colours` | Named `left` and `right` curve colours (distributions). |

Canvas 11 × 7 in (bars), 11 × 5 in (distributions). Renderer names
`boundary_strength`, `boundary_strength_<subset>`,
`boundary_strength_distributions`. Ported from matplotlib: fonts differ
slightly. The no-tonosegmental legend now gives that analysis's own family
count (24); the old file said 69.

![Distributions](planarsviz_charts/boundary_strength_distributions.png)

---

## 13. Boundary-strength overlay

Left and right boundary strength as paired bars over smoothed curves, with
boxed position labels coloured by a highlight.

![Boundary-strength overlay](planarsviz_charts/boundary_strength_overlay.png)

```r
plot_boundary_strength_overlay(bundle)
plot_boundary_strength_overlay(bundle, subset = "no_tono",
                               colours = c(Left = "#009E73", Right = "#CC79A7"))
```

| Option | Meaning |
|---|---|
| `subset` | `NULL`, or a subset id from `subsets.json`. |
| `colours` | Named `Left` and `Right` bar and curve colours. |
| `highlight` | Highlight id for label colours (default `"orthographic_word"`), or `NULL` for black. |

Canvas 13 × 7 in. Renderer names `boundary_strength_overlay`,
`boundary_strength_overlay_<subset>`; old files
`nyan1308_boundary_strength_overlay.pdf`, `_no_tono.pdf`.

---

## 14. Fragmentation test

Is a domain type's family count higher than its own number of tests would
predict by chance? One horizontal violin per group — the family counts under
permuted domain-type labels — with the observed count as a filled dot and the
one-sided p-value at the right. Domain types and bundles are two stacked
panels on one shared x axis, so the raw scale stays comparable.

![Fragmentation test](planarsviz_charts/fragmentation_test.png)

```r
plot_fragmentation_test(bundle)
plot_fragmentation_test(bundle, groups = c("phonologylike", "syntaxlike"))
```

| Option | Meaning |
|---|---|
| `groups` | Draw only these groups. Default: every group the bundle's table holds, in its own colours and labels. When what is left is all one kind, the facet strip is dropped — there is nothing for it to distinguish. |

Canvas 10 × 6.5 in for every group, 9 × 3.2 in for a filtered call. Those were
two hardcoded `ggsave()` sizes in the script this came from and no formula
connects them, so another `groups` list may want a size of its own — set
`planarsviz_size` on the returned plot to change it.

**This chart needs a bundle exported with `--fragmentation-permutations`.**
The permutation test takes minutes where the rest of an export takes seconds,
so the exporter only runs it on request. Without it, `plot_fragmentation_test()`
stops and says how to re-export.

| Renderer name | Old file |
|---|---|
| `fragmentation_test_plot` | `nyan1308_fragmentation_test_plot.pdf` |
| `fragmentation_test_syntax_phon_plot` | `nyan1308_fragmentation_test_syntax_phon_plot.pdf` |

Which two bundles the filtered variant shows is a presentation choice rather
than anything in the data, so the renderer sets it where it sets the other
choices that used to be separate script calls, and registers the chart only
for a bundle that has both.

Unlike every other chart here, this one was written in R from the start —
there is no matplotlib original, so the chart the standalone script drew is
itself the reference its porting check compares against.

---

## 15. Span-placement test

Does the real arrangement of a group's spans give fewer laminar families than
those same span *lengths* placed at random would? One panel per group: its
null distribution of family counts, its real count as a dashed line, and its
p-value in the panel. Panels share no axis — an absolute family count is not
comparable across groups with very different span counts, and the comparable
quantity is each panel's own p-value.

![Span-placement test](planarsviz_charts/span_placement_test_syntaxlike_plot.png)

```r
plot_span_placement_test(bundle)
plot_span_placement_test(bundle, groups = "syntaxlike", view = "standalone")
```

| Option | Meaning |
|---|---|
| `groups` | Draw only these groups, in the order given. Default: all nine. |
| `view` | `"grid"` (the default) packs the panels three across in a neutral colour, with room above each peak for its label. `"standalone"` draws one group in its own colour, with a larger label and an axis that hugs the data. |

Canvas 11 × 9 in for the grid, 9 × 5.5 in standalone. The ten numbers that
differ between the two views are not independent knobs — at the standalone
label's larger size a right-extending label runs into the bars, and in the
grid a left-extending one gets clipped where a group's observed count sits at
its panel's axis minimum — so they travel together as one `view` rather than
as ten arguments.

**This chart needs a bundle exported with `--span-placement-permutations`**,
for the same reason as the fragmentation chart.

| Renderer name | Old file |
|---|---|
| `span_placement_test_by_group_plot` | `nyan1308_span_placement_test_by_group_plot.pdf` |
| `span_placement_test_syntaxlike_plot` | `nyan1308_span_placement_test_syntaxlike_plot.pdf` |
| `span_placement_test_phonologylike_plot` | `nyan1308_span_placement_test_phonologylike_plot.pdf` |

---

## 16. Arbitrary-layers test

The same panels as chart 15, from the weakest of the project's three nulls:
one that knows only *how many* spans a group has, not how big they are. Every
draw picks that many intervals of arbitrary size at arbitrary positions. This
is the baseline a raw family count is implicitly read against, which is why it
is worth measuring rather than assuming.

```r
plot_arbitrary_layers_test(bundle)
plot_arbitrary_layers_test(bundle, groups = "syntaxlike", view = "standalone")
```

| Option | Meaning |
|---|---|
| `groups` | Draw only these groups, in the order given. Default: all nine. |
| `view` | As chart 15. Only the grid is registered in the renderer — nobody has asked for a standalone group here. |

Canvas 11 × 9 in for the grid, 9 × 5.5 in standalone, sharing chart 15's two
presentations through `R/null_panels.R`: the two charts are the same drawing
from different tables, so the drawing lives in one place.

**This chart needs a bundle exported with `--arbitrary-layers-permutations`.**

| Renderer name | Old file |
|---|---|
| `arbitrary_layers_test_by_group_plot` | *(none — no earlier script drew this)* |

**It is the one chart here with no reference image.** Every other chart was
ported from something that already drew it; this one was integrated from
scratch work that printed numbers and drew nothing. The renderer check reports
it as having no reference. What it is checked against instead is
`arbitrary_layers_test.py`'s committed TSVs, which the bundle must reproduce,
and a bundle test that fails if the null was truncated.

---

## 17. Illustrations

The one bundle with no language behind it (phase E, 2026-09-22): pure
tree-shape combinatorics, kept separate because the library's rule is
"Python computes, R draws from a data folder," and these have data, just no
language. Setup differs from every chart above:

```r
ref <- read_planars_illustrations("results/planarsviz/illustrations")
bundle <- read_planars_bundle("results/planarsviz/nyan1308")  # for 17b/17c only
```

### 17a. Tree shapes

One row of every (or a sample of) the n-ary tree shapes with a given leaf
count.

![Tree shapes, n=4](planarsviz_charts/tree_shapes_n4.png)

```r
plot_tree_shapes(ref, 4)
```

| Option | Meaning |
|---|---|
| `n` | Leaf count — one of `tree_shapes.tsv`'s `n` values (2–5 by default: 2, 3 and 4 exhaustive; 5 a 15-of-45 sample). |

Canvas varies with `n` and the row's tree count (a fixed 0.9 in tall; width
scales with leaf count and how many trees are in the row). Renderer names
`tree_shapes_n2` .. `tree_shapes_n5`; old files
`supercatalan_trees_n2.pdf` .. `_n5_sample15.pdf`.

### 17b. Tree-shape count growth

Catalan numbers (binary trees) and little Schröder numbers (n-ary trees,
OEIS A001003) against leaf count, log scale — how fast the tree space grows.
A new chart: the old scripts only ever showed this as
`tree_counting_equations.tex`'s static table.

![Tree-shape count growth](planarsviz_charts/tree_count_growth.png)

```r
plot_tree_count_growth(ref, bundle)
```

| Option | Meaning |
|---|---|
| `bundle` | A language bundle, for a dotted reference line at its `n_maximal_families` — omit (`NULL`, the default) for the two series with no reference line. |

Canvas 7 × 5 in. Renderer name `tree_count_growth`; no old file (new chart).

### 17c. Random tree overlay

Many uniformly-random n-ary tree shapes over a language's real positions,
stacked as faint ghost trees onto one panel — how vast the tree space is next
to the handful of laminar families actually observed. Reuses chart 5's
"stack N ghost trees on one patchwork cell" mechanism, minus the
span/strength colouring: there is no target span to highlight in a purely
combinatorial sample, so every edge is the same fixed alpha.

![Random tree overlay](planarsviz_charts/random_tree_overlay.png)

```r
plot_random_tree_overlay(ref, bundle)
```

| Option | Meaning |
|---|---|
| `alpha` | Per-tree edge opacity. Default `0.02`. |

Canvas 16 × 10 in. Renderer name `random_tree_overlay`; old file
`nyan1308_random_tree_overlay.pdf` (see "Name changes" below — the new file
drops the language prefix, since this chart's *sample* isn't nyan1308's
data, only its positions).

**No reference image proves this one draws correctly, and none can.** A
fresh random sample is supposed to look different from the last — that is
the entire content of the chart. What is checked instead: the sample is a
well-formed tree over exactly the right leaves
(`verify_random_trees_export.py`), and re-running the exporter with the same
recorded seed reproduces it exactly. `metadata.json`'s `random_trees.seed`
is what makes that possible at all — the script this replaced never
recorded one.

---

## 18. Boundary-strength test

Is a position's boundary strength (chart 12's summed strength) — and
especially its *jump* from the previous position — higher than the same
spans placed at random would give? It reuses `span_placement_test.py`'s
null: each span keeps its length, position is randomized over the whole
structure. This is the direct test of the "clear jump at the left edge of
the orthographic word" reading of chart 12.

For one group, two stacked panels, left edge on top and right edge below.
At each position: the real value (line and points) against the null's
5th–95th percentile band (ribbon) and mean (dashed). Points with
`p_value_ge_observed` below `alpha` are filled, the rest open, so a run of
filled points stands out from noise.

![Boundary-strength test](planarsviz_charts/boundary_strength_test_jump_all.png)

```r
plot_boundary_strength_test(bundle)                          # pooled, jump
plot_boundary_strength_test(bundle, statistic = "level")
plot_boundary_strength_test(bundle, group = "tonosegmental")
```

| Option | Meaning |
|---|---|
| `group` | `"all"` (the default — pooled), a domain type, or a bundle name. |
| `statistic` | `"jump"` (the default: strength at p minus strength at p−1) or `"level"` (the strength itself). |
| `alpha` | Significance threshold for filled vs. open points (default 0.05). |
| `line_colour` | Observed-curve colour. |

Canvas 11 × 7 in. Folder: `boundaries`.

**This chart needs a bundle exported with
`--boundary-strength-test-permutations`.** Without it,
`plot_boundary_strength_test()` stops and says: "This bundle has no
boundary_strength_test.tsv. The permutation test is slow, so the exporter
only runs it when asked: re-export with
`--boundary-strength-test-permutations 5000`." Use 5000 to match the
committed files.

| Renderer name | Old file |
|---|---|
| `boundary_strength_test_jump_<group>`, `boundary_strength_test_level_<group>` | none |

One pair of files per group in the bundle's table — for nyan1308 that is
nine groups (`all`, the five domain types, `syntaxlike`,
`syntaxlike_notono`, `phonologylike`), so 18 files.

Like §16, this chart has no reference image: it was written in the package
from the start, with no earlier script or chart to port or freeze. What
checks it instead: `tests/test_planarsviz_bundle.py`'s
`test_boundary_strength_test_covers_every_position` confirms every group has
exactly one row per (side, statistic, position) and that the jump
statistic's position-1 row is always zero — a shape check, not a check of
the p-values or observed strengths themselves. No `scripts/planarsviz_checks/`
check compares this chart's numbers against an independent run, unlike the
fragmentation test's `check_fragmentation.R`: `boundary_strength_test.py`'s
`run_test()` is the only place these numbers are computed, so there is
nothing separate to check it against.

---

## Name changes for cutover

Renderer output is `<dataset>_<renderer name>.pdf`, which equals the old
file name for every chart except:

| Old file | New file | Why |
|---|---|---|
| `nyan1308_all_families_labeled_wordhood.pdf` | `nyan1308_all_families_labeled_orthographic_word.pdf` | The name comes from the highlight id in the data. |
| `nyan1308_all_families_labeled_wordhood_legend.pdf` | `nyan1308_all_families_labeled_orthographic_word_legend.pdf` | Same. |
| `nyan1308_random_tree_overlay.pdf` | `illustrations_random_tree_overlay.pdf` | Belongs to the `illustrations` dataset now, not `nyan1308` — its sample isn't this language's data, only its positions. |
| `supercatalan_trees_n2.pdf` .. `_n5_sample15.pdf` | `illustrations_tree_shapes_n2.pdf` .. `_n5.pdf` | Same reason; the `_sample15` suffix moved into `docs/PLANARSVIZ_LIBRARY_PROGRESS.md`'s own record rather than the filename. |
