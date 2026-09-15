# planarsviz chart catalogue

Every chart the library draws: what it shows, the call, its options, the
canvas it was designed for, and an example from nyan1308 (Chichewa). The
**renderer name** is what `scripts/render_planarsviz.R --plots` takes and
what follows the dataset in the file name; **old file** is the file in
`results/` it replaces.

Setup for every example:

```r
library(planarsviz)
bundle <- read_planars_bundle("results/planarsviz/nyan1308")
```

Contents: [Pooled plots](#1-pooled-plots) ·
[Boundary skyline](#2-boundary-frequency-skyline) ·
[Span chart](#3-span-frequency-chart) ·
[Forests](#4-per-class-laminar-forests) ·
[Overlays](#5-stacked-overlays) ·
[Frequency tree](#6-frequency-tree) ·
[Four trees](#7-four-trees) ·
[Conflict groups](#8-conflict-groups) ·
[Exemplary trees](#9-exemplary-trees-and-slides) ·
[ForestSpans](#10-forestspans-plot) ·
[Tree counts](#11-tree-count-bar-charts) ·
[Boundary strength](#12-boundary-strength) ·
[Boundary-strength overlay](#13-boundary-strength-overlay) ·
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

No options. Canvas 14 × 8 in. Renderer name `spanchart`; old file
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

Canvas 16 × 10 in. Renderer name `freqtree`; old file `nyan1308_freqtree.pdf`.

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

## Name changes for cutover

Renderer output is `<dataset>_<renderer name>.pdf`, which equals the old
file name for every chart except:

| Old file | New file | Why |
|---|---|---|
| `nyan1308_all_families_labeled_wordhood.pdf` | `nyan1308_all_families_labeled_orthographic_word.pdf` | The name comes from the highlight id in the data. |
| `nyan1308_all_families_labeled_wordhood_legend.pdf` | `nyan1308_all_families_labeled_orthographic_word_legend.pdf` | Same. |
