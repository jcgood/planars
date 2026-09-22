# planarsviz

Charts for planar constituency analyses: pooled test plots, boundary
frequencies, laminar-family forests and overlays, representative trees,
conflict groups, tree counts and boundary strength.

planarsviz draws; it does not analyse. The analysis — loading domain spans,
finding conflicts, enumerating maximal laminar families, choosing
representative families — stays in Python
(`scripts/analysis/laminar_analysis.py` and its companions). A small
exporter writes the results into a **data bundle**, a folder of plain TSV and
JSON files, and every chart function in this package reads that bundle.

```
domains_<dataset>.tsv ─┐
planar_<dataset>.tsv  ─┼─► export_planarsviz_data.py ─► results/planarsviz/<dataset>/data/
optional settings     ─┘                                          │
                                                                  ▼
                                   R: read_planars_bundle() ─► plot_*() ─► render_planarsviz.R
```

Facts about a language — how many positions, where the root is, position
names, domain types and their colours, which spans define conflict groups,
which positions form the orthographic word — live in the bundle, never in
the R code. The same functions draw any language's data.

## Status

All 19 charts from the nyan1308 (Chichewa) work are reproduced: the charts
that were already R are identical to the old scripts' output (same plot
data, no differing pixels); the two that were matplotlib are ported with
every visual setting carried over (they differ only in fonts). Cutover is
done — nothing under `NonCollaborative/` writes a chart any other way. The
scripts this package replaced are archived in
`OlderFiles/planarsviz_superseded/`, where the porting checks still run them
to prove the two draw the same thing, and must not be deleted. The porting
record is `docs/PLANARSVIZ_LIBRARY_PROGRESS.md`.

## Requirements

- R 4.2 or later with dplyr, ggplot2, jsonlite, magrittr, patchwork,
  scales, stringr and tidyr; ape and ggtree for the tree charts.
- The project's Python environment (pandas, numpy) for the exporter.
- `pdftoppm` (poppler) if you want PNG output from the renderer.

Those are the packages the code needs. Which *versions* it was checked
against is a separate question, and `NonCollaborative/renv.lock` answers it —
see "Package versions" in
[`docs/planarsviz_guide.md`](../../docs/planarsviz_guide.md).

## Quick start

From `NonCollaborative/`:

```sh
# 1. Export a bundle
python scripts/analysis/export_planarsviz_data.py \
    --domain-file domains/domains_nyan1308.tsv \
    --planar-file planar_tables/planar_nyan1308.tsv \
    --language-name Chichewa

# 2. Render every chart the bundle supports
Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 --formats pdf,png
```

Or draw one chart in R:

```r
install.packages("r/planarsviz", repos = NULL, type = "source")
library(planarsviz)

bundle <- read_planars_bundle("results/planarsviz/nyan1308")
p <- plot_pooled(bundle, domain_types = "phonological")
size <- attr(p, "planarsviz_size")
ggplot2::ggsave("phonological.pdf", p, width = size[["width"]],
                height = size[["height"]], units = attr(p, "planarsviz_units"))
```

Every chart function returns an ordinary ggplot or patchwork object, with
its intended canvas size attached as `planarsviz_size` and
`planarsviz_units`, so you can adjust it before saving.

## Documentation

- **User guide** — `docs/planarsviz_guide.md`: exporting, drawing,
  rendering, adding a language, the settings files, and checking charts.
- **Chart catalogue** — `docs/planarsviz_charts.md`: every chart, what it
  shows, the call that draws it, its options and an example.
- **Bundle contents** — `inst/data-contract.md`: every file the exporter
  writes and what each column means.
- **Function reference** — each exported function has a description of its
  arguments in a comment block above it in `R/` (help pages are not built
  yet).

## Functions at a glance

| Chart | Function |
|---|---|
| Pooled test plots | `plot_pooled()` |
| Boundary-frequency skyline | `plot_boundary_skyline()` |
| Span-frequency chart | `plot_span_chart()` |
| Per-class laminar forests | `plot_laminar_forest()` |
| One family of a forest, on its own | `plot_forest_tree()` |
| Stacked overlays (coloured, all families, highlighted) | `plot_laminar_overlay()` |
| Frequency tree | `plot_frequency_tree()` |
| Four trees | `plot_four_trees()` |
| Conflict groups | `plot_conflict_groups()` |
| Exemplary trees and slides | `plot_exemplary_tree()` |
| ForestSpans plot | `plot_forestspans()` |
| Tree-count bar charts | `plot_tree_counts()` |
| Boundary strength, distributions | `plot_boundary_strength()`, `plot_boundary_strength_distributions()` |
| Boundary-strength overlay | `plot_boundary_strength_overlay()` |
| Class-fragmentation permutation test | `plot_fragmentation_test()` |
| Span-placement permutation test | `plot_span_placement_test()` |
| Boundary-strength permutation test | `plot_boundary_strength_test()` |

Reading data: `read_planars_bundle()`, `read_planars_subset()`,
`validate_planars_bundle()`, and `read_planars_*()` for each data file.

## License

MIT; see `LICENSE`.
