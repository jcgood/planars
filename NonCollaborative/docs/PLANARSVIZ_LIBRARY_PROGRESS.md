# planarsviz library rebuild — progress

Plan: `docs/PLAN_planarsviz_library.md`. Branch `planarsviz-library`, worktree
`/Users/jcgood/gitrepos/planars-planarsviz`. Started 2026-09-14/15 overnight by
Claude (Opus) with Jeff's authorization to proceed without waiting.

Honesty rule: nothing below says "matches" without naming the comparison file.

---

## Open questions for Jeff

1. **Chart files not in the inventory** (§3.2): `supercatalan_trees_n2.pdf`,
   `_n3.pdf`, `_n4.pdf`, `_n5_sample15.pdf` (from
   `scripts/exploratory/render_supercatalan_rows.r`), and
   `tree_counting_equations.pdf` (LaTeX). Port, or treat as out of scope like
   the other exploratory/LaTeX outputs? Not started.
2. **`nyan1308_all_families_labeled_legend-JGAnn.pdf`** looks like your hand
   annotation of the legend, not a chart output. Committed on `main` as-is;
   not treated as a chart. Is there feedback in it the port should apply?
3. **Display labels for nyan1308.** The planar table's `Position_Label`
   column has short slot codes (`V`, `Un`, `PrS`…), but every chart uses
   different labels (`Root`, `Ext`, `PreSbj`…), which lived only in
   `laminar_analysis.py`'s `_NYAN1308_POS_LABELS`. The salvaged exporter
   special-cased `dataset == "nyan1308"` to get them (a leak). Now: the
   exporter reads an explicit labels file, and nyan1308's is committed as
   `planar_tables/display_labels_nyan1308.tsv` (same 22 labels). OK to keep a
   data file there, or should chart labels live elsewhere?
4. **Root position.** The main project's keystone convention is
   `Position_Name == 'v:verbstem'`, but `planar_nyan1308.tsv` has no
   `Position_Name` column; its root row has `Elements == "root"`. The
   exporter uses `--root-element root` (default) and records
   `root_position` in `metadata.json`. Confirm this is the right marker.

---

## Setup (§3)

- `main` commits: `e362364`, `0cd41a8`, `d240737`, `43a308f`; pushed.
  Worktree created from `43a308f`.
- Salvaged into the worktree: `scripts/analysis/export_planarsviz_data.py`,
  `tests/test_planarsviz_bundle.py` (file-counting manifest test deleted),
  `r/planarsviz/{DESCRIPTION,LICENSE,inst/data-contract.md}`,
  `R/data.R` (bundle reader/validator), `R/labels.R` (position labels only;
  Codex's hard-coded palette removed).
- Tooling on this machine: R 4.6.1, ggplot2 4.0.3, ggtree 4.2.0, ape,
  patchwork, tidyverse, here, jsonlite. **Not installed:** testthat,
  devtools, roxygen2 — so `NAMESPACE` is hand-written and the package is
  installed with `R CMD INSTALL`. Consistent with R9 (no tooling yet).
- Comparison helper: `scripts/planarsviz_compare.py` (reference | new |
  difference image, differing-pixel fraction).

### Exporter changes (§8.1)

- Removed the `dataset == "nyan1308"` label special case (question 3).
- Added `root_position` / `root_element` / `source_labels_file` to
  `metadata.json` (question 4).
- Added `domain_types.tsv` (colour, within-layer sort order, legend order,
  known flag) from `domain_charts-cgpt.r`'s values; unknown observed types
  get fallback colour `#7F7F7F` and sort after the known ones.
- Re-export check: see chart 1 entry.

---

## Inventory check (§3.2)

Every `*.pdf` in `NonCollaborative/results/` at `43a308f`:

| File(s) | Chart |
|---|---|
| `nyan1308_pooled_plot.pdf` | 1 |
| `nyan1308_pooled_domainplot.pdf` | 2 |
| `nyan1308_pooled_plot_<type>.pdf` ×5 | 3 |
| `nyan1308_pooled_plot_<type>_global_layers.pdf` ×5 | 4 |
| `nyan1308_boundary_skyline.pdf` | 5 |
| `nyan1308_{inton,length,morsyn,phon,tono,phonologylike,syntaxlike,syntaxlike_notono}_laminar_forest.pdf` | 6 |
| `nyan1308_laminar_overlay.pdf`, `_legend.pdf` | 7 |
| `nyan1308_all_families_labeled.pdf`, `_legend.pdf` | 8 |
| `nyan1308_all_families_labeled_wordhood.pdf`, `_wordhood_legend.pdf` | 9 (option on 8) |
| `nyan1308_exemplary_trees_1..7.pdf`, `_slide_N_tree.pdf`, `_slide_N_evidence.pdf` | 10 |
| `nyan1308_forestspans_plot.pdf`, `_plot_no_tono.pdf` | 11 |
| `nyan1308_conflict_groups.pdf` | 12 |
| `nyan1308_four_trees.pdf` | 13 |
| `nyan1308_freqtree.pdf` | 14 |
| `nyan1308_spanchart.pdf` | 15 |
| `nyan1308_tree_count_{all,by_class,bundles,without_adjacent}.pdf` | 16 |
| `nyan1308_boundary_strength.pdf`, `_distributions.pdf`, `_no_tono.pdf` | 17 |
| `nyan1308_boundary_strength_overlay.pdf`, `_overlay_no_tono.pdf` | 18 |
| `nyan1308_example_*.pdf`, `nyan1308_planar_table_*.pdf`, `nyan1308_forestspans_slide.pdf` | out of scope (LaTeX) |
| `nyan1308_random_tree_overlay.pdf` | out of scope (random sampling) |
| `supercatalan_trees_*.pdf` ×4, `tree_counting_equations.pdf` | **not in inventory — question 1** |
| `nyan1308_all_families_labeled_legend-JGAnn.pdf` | not a chart output — question 2 |

Reference images: 63 PNGs at 100 dpi in `results/planarsviz/reference/`
(every in-scope PDF above), taken from the committed PDFs at `43a308f`.

---

## Chart 1: pooled plot (`nyan1308_pooled_plot.pdf`)
- Reference current? Re-rendered `domain_charts-cgpt.r` into a scratch dir
  (output path swapped in memory, script file untouched) and compared all 12
  pooled PDFs (charts 1–4) to the frozen references: 0.0000% differing pixels
  for every one (`results/planarsviz/comparisons/refcheck/`).
- Source copied: `scripts/domain_charts-cgpt.r:14-202` → `R/pooled.R`
- Status: in progress
