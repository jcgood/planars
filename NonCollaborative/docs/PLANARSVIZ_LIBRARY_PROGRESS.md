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
5. Span chart x-axis drops labels left of the first charted span — see the
   chart 15 entry.
6. Span chart colour for `length` is inferred — see the chart 15 entry.
7. **Overlay legend's "More" thickness swatch.** The generator draws the
   swatch at `sqrt(highest convergence)` even when the lines are drawn with
   exponent 0.75 (the all-families chart), so in chart 8/9's legend the
   swatch is thinner than the thickest line. Reproduced faithfully; say if
   the swatch should follow the chart's exponent.
8. **The branch is not pushed.** The repo's push hook requires syncing
   `planars-data` first, and syncing that repo was off-limits for this work,
   so every `planarsviz-library` commit exists only on this machine (worktree
   `/Users/jcgood/gitrepos/planars-planarsviz`). Push it yourself after the
   usual `coded_data` pull, or tell me to.
9. **Conflict-groups chart has no panel titles.** The script sets titles
   ("All 69 families", "Group A: [5–13] (10 families)"…) with
   `plot_annotation()` on each panel, but patchwork ignores annotations on a
   panel nested inside a larger layout, so the committed PDF shows none —
   the reader can't tell which small panel is which group. Reproduced
   faithfully (the library builds the same titles, equally invisible). Fix
   by drawing the titles another way?
10. **scipy is not installed.** The boundary-strength distributions chart
    (chart 17) uses scipy's weighted smoothing, but scipy isn't in the
    project's environment or declared in `requirements.in`, so that
    committed PDF can't be regenerated on this machine. The exporter rebuilds
    the calculation in numpy; it matches the scipy-drawn chart by eye and at
    its peaks, but equality to the last decimal can't be checked without
    scipy. Add scipy (a `requirements.in` change) so it can be confirmed, or
    accept the numpy version?
11. **Undocumented boundary-strength files.** `results/visualizations.md`
    has no entries for the boundary-strength charts, and no script writes
    the `_no_tono` file names (`boundary_strength.py --subset` would name
    them after the four kept types; they were presumably renamed by hand —
    the numbers do match that four-type analysis exactly). Not fixed here
    because that doc lives on `main`.

---

## Setup (§3)

- `main` commits: `e362364`, `0cd41a8`, `d240737`, `43a308f`; pushed.
  Worktree created from `43a308f`. The branch itself is not pushed
  (question 8).
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

## Shifted test dataset (§10.1–10.2)

- `tests/fixtures/make_shifted_nyan.py` → `domains_shifted_nyan.tsv`,
  `planar_shifted_nyan.tsv`, `display_labels_shifted_nyan.tsv`; exported as
  `results/planarsviz/shifted_nyan/` with `--language-name "Shifted test data"`.
- **Leak found and fixed on first export (exporter, not R):** the shifted
  data doesn't cover position 1, so the family enumeration adds a synthetic
  root `[1-24]` to every family, but the main span table didn't list it —
  memberships named an unknown span and the R validator refused the bundle.
  nyan1308 never hit this (its `[1-22]` is observed). Now spans.tsv lists the
  synthetic root flagged `synthetic=True`, excluded from observed counts
  (main and subset metadata); R validator counts observed spans.
  Side effect on nyan1308's bundle: subset `n_unique_spans` /
  `n_universal_spans` no longer count their synthetic roots (they did before).
- `tests/test_planarsviz_shifted_bundle.py`: same counts, spans shifted by 2,
  conflicts shifted, same families in the same `family_NNN` order (ignoring
  the synthetic root), root 12, 24 positions, renamed labels, `tonal` in
  fallback grey. 9 bundle tests pass (nyan1308 + shifted).

---

## Charts 1–4: pooled plots (12 files)
- Reference current? Re-rendered `domain_charts-cgpt.r` into a scratch dir
  (output path swapped in memory, script file untouched): all 12 PDFs 0.0000%
  differing pixels vs frozen references (`comparisons/refcheck/`).
- Source copied: `scripts/domain_charts-cgpt.r:14-202` → `R/pooled.R`, commit `9b4e37d`.
- Literals replaced (`180ffcf`): domain-type factor levels, colours, legend
  order (→ `domain_types.tsv`), root position (→ `metadata.root_position`),
  position count (→ `metadata.n_positions`). Exporter fields added:
  `domain_types.tsv`, `root_position`. Public function: `plot_pooled()`
  (`group_by_domain`, `domain_types`, `layers = "global"|"local"`).
- Numbers comparison (`scripts/planarsviz_checks/check_pooled.R`): for all 12,
  every ggplot_build layer data frame, y-axis labels, title and canvas size
  identical to the working script.
- Pixel comparison: `results/planarsviz/comparisons/nyan1308_pooled_*.png`,
  0.0000% differing pixels, all 12.
- Shifted-dataset check: `comparisons/shifted/shifted_nyan_pooled_*.png`.
  Only expected differences: positions +2 with empty 1–2, axis to 24, root
  line at 12, renamed labels, `tonal` in grey in the legend. Also, as a direct
  consequence of the fallback sort order for an unknown type, `tonal` rows
  sort after the known types within a layer and its group moves last in the
  grouped-by-domain chart — expected, not a leak. No leaks found.
- §5 fixes: global layer numbers (chart 4) — checked, filtered view of the
  already-numbered data.
- R6 search: hits only in doc-comment examples and the 26/25 cm canvas widths
  (rendering choices).
- Looked at by Claude: yes (full images and zoomed legend/axis/row crops).
  Seen by Jeff: no.
- Status: done pending Jeff's review.

## Chart 5: boundary skyline
- Reference current? Yes by transitivity: the library's plot data equals the
  working script's (below) and its render has 0.0000% differing pixels
  against the reference.
- Source copied: `scripts/nyan_boundary_skyline.r:1-129` → `R/boundary.R`, commit `a0401a8`.
- Literals replaced (`22e13bc`): position labels and 1..22 range, panel
  order (→ new `facet_order` column), language name in the title (→ new
  `metadata.language_name`, `--language-name`). Count table returned as an
  attribute instead of written. Unused `type_colors` dropped. Public
  function: `plot_boundary_skyline()`; helper `planarsviz_dataset_title()`.
- Behaviour note: in the working script an unknown domain type would become
  NA and silently disappear from the lower panel; the library gives it a
  panel. Invisible for nyan1308 (all five types known).
- Numbers comparison (`check_skyline.R`): both panels' plot data, facet
  panels, x labels, title, subtitle, and the boundary-count table identical.
- Pixel comparison: `comparisons/nyan1308_boundary_skyline.png`, 0.0000%.
- Shifted-dataset check: `comparisons/shifted/shifted_nyan_boundary_skyline.png`
  — title "Shifted test data (shifted_nyan)", empty New1/New2, renamed labels,
  `tonal` panel last; bar heights unchanged. No leaks found.
- R6 search: clean apart from the Start/End colours and 16×11 in canvas
  (rendering choices).
- Looked at by Claude: yes. Seen by Jeff: no.
- Status: done pending Jeff's review.

## Chart 15: span-frequency chart
- Source copied: `results/laminar_spanchart.r:1-35` → `R/spanchart.R`, commit `7c064b9`.
  The script is generated and its generator was never committed; its data
  frame was pasted in, so the rules behind it were recovered by matching its
  values (`891575f`), all exact for nyan1308:
  - rows: every span except the full root, ordered by family count
    ascending; ties in the order `report_families()` first counts spans
    (iterating families in order, each family's frozenset in Python's
    iteration order) — deterministic but arbitrary. Exporter writes
    `spans.tsv` `span_chart_rank`. (Simpler guesses — first appearance in the
    domain file, `report_convergence()` order — were tested and did not match.)
  - width `0.5 + 5 × share`, share `round(count/69, 6)`;
  - colour: a second palette (Paul Tol "bright"), taking the colour of the
    span's highest-priority domain type (morphosyntactic > phonological >
    tonosegmental > intonational > length). Exporter writes `alt_colour`,
    `colour_priority`.
- Numbers comparison (`check_spanchart.R`): plot data, title, x labels, legend
  name identical. Pixel comparison: `comparisons/nyan1308_spanchart.png`, 0.0000%.
- Shifted-dataset check (`comparisons/shifted/shifted_nyan_spanchart.png`):
  expected differences only — `[3-24]` appears as a row (it is not the full
  `[1-24]` root), tie order among equal counts differs (the recovered tie rule
  depends on Python set iteration, which changes with coordinates), `tonal`
  spans in fallback grey, renamed labels. No leaks.
- **Question 5 for Jeff:** the working chart's x-axis drops tick labels left of
  the leftmost charted span (nyan1308's axis starts at PreSbj, not QM, because
  the root `[1-22]` is excluded and nothing else starts at 1). Reproduced
  faithfully; say if it should show every position instead.
- **Question 6 for Jeff:** the span chart's colour for `length` (`#AA3377`,
  Tol purple) is inferred, not observed — in nyan1308 every length span also
  has a higher-priority type, so length never decides a colour. Matches
  `visualizations.md` ("length = purple").
- Looked at by Claude: yes. Seen by Jeff: no.
- Status: done pending Jeff's review.

## Chart 6: per-class laminar forests (8 files)
- Source copied: `results/nyan1308_inton_laminar_forest.r:1-37` (what
  `generate_r_script()` writes, one tree's worth) → `R/ghost_trees.R`,
  commit `34c8738`. Shared building block `planarsviz_ghost_tree()` + chart
  function `plot_laminar_forest(bundle, forest_id)` (`c4ed37f`).
- Exporter additions: `data/forests.json` + `data/forests/<id>.tsv` (per tree:
  Newick, groupOTU span order, thickness), computed with the same
  `build_parent_map`/`get_children`/`span_to_newick` the generator uses and
  the **subset's own position count** (length 18, tono 17, phon 21) — the
  analysis subsets in `data/subsets/` use the full 22 and would draw
  different trees. `verify_forest_export.py`: all 8 exported forests
  reproduce their generated scripts tree by tree (Newick, groups, thickness,
  alpha, colour, count).
- Bundles moved to `scripts/analysis/planars_groupings.py`, read by
  `laminar_analysis.py` `__main__`, `laminar_tree_counts.py`, and the
  exporter. Verified unchanged: bundle tree counts equal
  `nyan1308_tree_counts.tsv`; `laminar_analysis.main()` regenerates the three
  bundle forest scripts byte-identically apart from the `ggsave` path line.
- Numbers comparison (`check_forests.R`): every tree's ggplot_build data
  identical for all 8 forests. Pixel comparison: all 8 at 0.0000%
  (`comparisons/nyan1308_*_laminar_forest.png`).
- Shifted-dataset check: another exporter leak found and fixed — a forest
  whose domain types don't occur in the data (tono, since tonosegmental is
  renamed) crashed `load_spans()`; now skipped. 7 shifted forests rendered
  (`comparisons/shifted/`): shapes unchanged, positions +2, renamed labels,
  per-class position counts +2. Expected consequence of the rename, not a
  leak: the syntax-like bundle is defined by type *names*, so without
  `tonosegmental` it has 4 trees instead of 16. Label boxes crowd slightly on
  forests with 23–24 tips (same 20-inch canvas).
- §5 fixes checked: invisible spacer `colour = NA, fill = NA`; `vjust = 0.35`
  on the original 20×14 in canvas; alpha formula `(1 − 0.01^(1/n))/2`; white
  page background.
- R6 search: clean (rendering constants only).
- Looked at by Claude: yes (tono and shifted phon side by side). Seen by Jeff: no.
- Status: done pending Jeff's review.

## Charts 7–9: stacked overlays (6 files)
- Source copied: `results/nyan1308_laminar_overlay.r`,
  `results/nyan1308_all_families_labeled.r` (both written by
  `generate_r_overlay_script()`) and `results/nyan1308_all_families_labeled_wordhood.r`
  (a hand edit of the second — it has no generator) → `R/overlays.R`, commit `2f6cb1a`.
- One function replaces the three scripts (`21b6111`):
  `plot_laminar_overlay(bundle, groups, alpha_divisor, thickness_exponent, legend, highlight)`.
  Chart 7 = defaults; chart 8 = `groups = "all", alpha_divisor = 1,
  thickness_exponent = 0.75`; chart 9 = chart 8 + `highlight = "orthographic_word"`
  (decision 4: wordhood is an option). `legend = TRUE` gives the `_legend` versions.
- Exporter additions: `data/overlay_groups.json` + `data/overlay_groups/<id>.tsv`
  (per tree: Newick, groupOTU span order, convergence), replaying
  `run_domain_overlay()` — subset families with the **full** dataset's
  position count, unlike chart 6. `data/highlights.tsv` from the new
  `planar_tables/highlights_nyan1308.tsv` (orthographic word 5–19 red, final
  vowel 17 `#0072B5`), `--highlights-file`. `verify_overlay_export.py`: every
  tree's Newick, groups, thickness, colour and the alpha formula reproduce
  both generated scripts.
- Computed in R rather than pasted: alpha `(1 − 0.01^(1/total trees)) / divisor`,
  thickness `max(convergence, 1)^exponent`, the darkness/thickness legend's
  swatch values. `planarsviz_ghost_tree()` gained `spacer_lineheight` (this
  generator leaves it unset; chart 6's sets 1) — chart 6 re-checked afterwards,
  still identical.
- Behaviour note: the colour legend lists the domain types of the groups
  actually drawn; the generator always listed its fixed five (the same five
  for nyan1308).
- Numbers comparison (`check_overlays.R`): every tree's ggplot_build data and
  the legend plot's data identical, all three charts.
- Pixel comparison: `comparisons/nyan1308_{laminar_overlay,all_families_labeled,all_families_labeled_wordhood}{,_legend}.png`,
  all six 0.0000%.
- Shifted-dataset check (`comparisons/shifted/`): all six rendered, same
  canvas. Expected differences only: positions +2, renamed labels, no
  tonosegmental group (renamed, so not one of the overlay groups), legend
  without it. Wordhood labels: red on 7–21, blue on 19 — the highlight moved
  with the data. No leaks.
- Question 7 above (legend thickness swatch).
- R6 search: font sizes and legend-panel coordinates only.
- Looked at by Claude: yes (nyan legend comparison; shifted wordhood label
  row). Seen by Jeff: no.
- Status: done pending Jeff's review.

## Charts 14 and 13: frequency tree and four trees
- Source copied: `results/laminar_freqtree.r:1-31` and
  `results/laminar_four_trees.r:1-104` → `R/summary_trees.R`, commit `9125812`
  (checked line-for-line identical before committing).
- Recovered rules re-run in the worktree (§4.1): consensus picks families
  15 / 46 / 15 / 6 (0-based) for All / A / B / C; conflict groups 10 / 23 / 36;
  B drawn as 9, 25, 16, 18, 10–15, 17, 19 and C as 0, 40, 53, 37, 1–8 — all
  equal to the plan's lists.
- Exporter additions: `families.tsv` `newick`; `conflict_groups.tsv`
  (group, defining span, family, draw rank under the cap);
  `selections.tsv` (`consensus_all`, `consensus_<group>`); metadata
  `conflict_group_cap`, `source_conflict_groups_file`. The defining spans are
  data — `planar_tables/conflict_groups_nyan1308.tsv` (A 5-13, B 6-17, C =
  the rest), `--conflict-groups-file`; the cap is `--conflict-group-cap`
  (default 12). A group no larger than the cap is drawn whole in family order
  (A); larger groups use the greedy-coverage seed then family order. Ties in
  consensus (never seen) go to the lower family number — a choice, not
  recovered. `verify_selection_export.py`: the freqtree, four-trees and all
  four conflict-group panels' Newick strings reproduce in drawing order.
- R (`03405d7`): `plot_frequency_tree(bundle, selection)`,
  `plot_four_trees(bundle, other_label = "neither")`, shared
  `planarsviz_summary_tree()`; frequencies counted from
  `family_membership.tsv` (rounding 6 places, thickness 4 × share). Group
  titles are built from the defining span; "neither" is an option. Layout:
  the script's 2×2 for three groups, two panels per row otherwise.
- Numbers comparison (`check_summary_trees.R`): every panel's plot data,
  title and opacity-scale name identical. Pixel comparison:
  `comparisons/nyan1308_freqtree.png`, `comparisons/nyan1308_four_trees.png`,
  both 0.0000%.
- Shifted-dataset check (`comparisons/shifted/shifted_nyan_{freqtree,four_trees}.png`):
  same trees with New1/New2 as extra top-level tips, renamed labels, titles
  `[7-15]` / `[8-19]`; same families selected (bundle test). Labels crowd in
  the four-tree panels with 24 tips (same canvas). No leaks.
- Also fixed: `inst/data-contract.md` was out of date (listed none of the
  files added since the salvage, and said `n_unique_spans` counts every span
  row); rewritten to match the exporter.
- R6 search: clean.
- Looked at by Claude: yes (both shifted side-by-sides). Seen by Jeff: no.
- Status: done pending Jeff's review.

## Chart 12: conflict groups
- Source copied: `results/laminar_conflict_groups.r:1-1684` →
  `R/conflict_groups.R`, commit `3cab0a8` (written by a small script and
  checked line-for-line identical, since 1684 lines are too many to retype).
- Replaced (`2af1e7d`) by `planarsviz_conflict_tree()` and
  `plot_conflict_groups(bundle, other_label = "neither")`. Uses the
  exporter files added for charts 13–14 (`families.tsv` newick,
  `conflict_groups.tsv` draw ranks); no new exporter fields.
- Rules the pasted numbers follow, now computed in R: per-panel opacity
  `1 − 0.01^(1/trees drawn)` (69 → 0.064563, 10 → 0.369043, 12 → 0.318708);
  thickness `sqrt(span family count over ALL families)`, not within the
  group; groupOTU order by left edge, larger first. No tip labels. Opacity
  and colour are set on the built layer (`aes_params`), as the script does.
- Numbers comparison (`check_conflict_groups.R`): all 103 trees' plot data
  identical. Pixel comparison: `comparisons/nyan1308_conflict_groups.png`,
  0.0000%.
- Shifted-dataset check (`comparisons/shifted/shifted_nyan_conflict_groups.png`):
  same shapes plus the two new leading tips; group membership and draw order
  identical (bundle test). No leaks.
- Question 9 above: panel titles are invisible in the original too.
- R6 search: clean.
- Looked at by Claude: yes. Seen by Jeff: no.
- Status: done pending Jeff's review.

## Chart 10: exemplary trees and slides (21 files)
- Source copied: `results/nyan1308_exemplary_trees.r:1-225` (written by
  `generate_r_exemplary_trees_script()`) → `R/exemplary.R`, commit `9b4ed22`
  (line-for-line check).
- Selection re-run in the worktree: `select_representative_families(k=6)`
  + sparsest = families 15, 0, 37, 53, 46, 6, 67 (0-based); every drawn
  tree, test list and page height matches.
- Exporter: `selections.tsv` `exemplary` ranks 1–7, calling
  `select_representative_families()` directly (this rule was never lost);
  `--exemplary-k` (6), `--no-exemplary-sparsest`; metadata `exemplary_k`,
  `exemplary_include_sparsest`. `verify_selection_export.py` now also checks
  the seven exemplary trees.
- R: `plot_exemplary_tree(bundle, rank, view = "page" | "slide_tree" |
  "slide_evidence")`, from `planarsviz_exemplary_tree()` and
  `planarsviz_family_evidence()`. The test list is the member spans'
  `labels` (synthetic root excluded). The evidence panel no longer
  `source()`s `domain_charts-cgpt.r` (which re-saved every pooled PDF as a
  side effect). New shared `planarsviz_pooled_setup()` used by
  `plot_pooled()` too — charts 1–4 re-checked: all 12 still identical.
- §5 fixes checked: evidence filters the already-numbered data (global
  layers); slide tree size 4.6 with `label.padding = 0.12 lines`.
- Numbers comparison (`check_exemplary.R`, evaluates the script with
  `ggsave` disabled so nothing committed is rewritten): all 7 print trees,
  evidence panels and slide trees identical. Pixel comparison: all 21 files
  0.0000% at the script's sizes (`comparisons/nyan1308_exemplary_trees_*.png`).
- Shifted-dataset check (`comparisons/shifted/shifted_nyan_exemplary_trees_*.png`):
  21 rendered, same canvas sizes (same test counts per family); same
  families selected (bundle test). Exemplar 7 looked at: same 21 tests and
  layer numbers, axis to 24, root line at 12. No leaks.
- Housekeeping: the rendered PDFs and comparison images for charts 12–14
  were missing from their commits; added with this one. Pooled PDFs that
  the charts 1–4 re-check rewrote (pixel-identical, file metadata only)
  were restored rather than committed.
- R6 search: clean.
- Looked at by Claude: yes. Seen by Jeff: no.
- Status: done pending Jeff's review.

## Chart 11: ForestSpans plot (2 files)
- Source copied: `results/nyan1308_forestspans_plot.r:1-140` (written by
  `make_forestspans_table.py` `make_r_plot_script()`) → `R/forestspans.R`,
  commit `e0a7791` (line-for-line check). The no-tono script is the same
  code with other data rows (checked by diff), so it was not copied.
- One function (decision on options, §4.2): `plot_forestspans(bundle,
  subset = NULL)`; `subset = "no_tono"` gives the no-tonosegmental chart.
- Exporter additions:
  - `spans.tsv` `blend_colour` — `mix_hex_colors()` copied into the
    exporter (Python rounding kept). One deliberate change: an unknown
    domain type contributes the fallback grey instead of being skipped.
  - `planars_groupings.FILTERS` (`no_tono` leaves out tonosegmental), the
    one place a filter is defined. Exported as a fresh analysis in
    `subsets/no_tono/` (`kind: filter`, only when the data has a type to
    leave out); `subsets.json` and subset metadata gain `kind` and
    `domain_types`. This is the §4.2 "domain-type filter = fresh analysis".
  - `verify_forestspans_export.py`: both pasted tables (26 and 20 rows:
    layer, edges, count, colour, row order) and tree counts (69, 24)
    rebuilt exactly from the bundle.
- Computed in R: layer = size rank inverted, rows by count then layer,
  synthetic root dropped; tree count, root and position count from the
  bundle; legend colours and order from `domain_types.tsv`.
- §5 fixes checked: `show.legend = FALSE` on the `I(Color)` layers; margins
  by `expansion(add = 1)`, no hard limits.
- Numbers comparison (`check_forestspans.R`): plot data, row order and
  legend title identical for both. Pixel comparison:
  `comparisons/nyan1308_forestspans_plot{,_no_tono}.png`, both 0.0000%.
  Forest, overlay and selection export checks re-run after the exporter
  change: still identical.
- Shifted-dataset check (`comparisons/shifted/shifted_nyan_forestspans_plot.png`):
  same counts and layer numbers; positions +2, root line at 12; `tonal`
  spans grey or grey-blended. `no_tono` skipped (the shifted data has no
  tonosegmental to leave out). Two faithful behaviours, not leaks:
  - the x-axis starts at 2, because its range comes from the data and the
    shifted spans start at 3 — the same kind of behaviour as question 5;
  - the legend lists every known domain type (including tonosegmental,
    absent here) plus `tonal`, as the original always listed its five.
- R6 search: comments and a point-shape number only.
- Looked at by Claude: yes (shifted side by side). Seen by Jeff: no.
- Status: done pending Jeff's review.

## Chart 16: tree-count bar charts (4 files) — cross-language port (§4.3)
- Step 1, calculation: the exporter calls `laminar_tree_counts.py`'s
  `collect_counts()` and `collect_bundle_counts()` and writes
  `tree_counts.tsv` (the script's four columns, plus `kind`, `label`,
  `colour`). Both functions gained an optional list of types/bundles,
  because with a fixed list of five types the shifted data (no
  tonosegmental) crashed `load_spans()`. Defaults unchanged: re-running the
  script gives a `nyan1308_tree_counts.tsv` identical to the committed one,
  and `verify_tree_counts_export.py` finds the exported numbers identical,
  15 rows.
- Step 2, visual settings (all listed with source lines in the header of
  `R/tree_counts.R`):
  - house style, lines 169–213: 8 × 3.8 in; ascending, ties in input order;
    bar height 0.45; value labels 6 pt right, 15 pt; x label 14 pt; x to
    1.2 × max; tick labels 14/13 pt; no spines; tick length 0; transparent;
    no title;
  - vertical, lines 142–166 and 242–258: 7 × 5 / 8 × 5 in; colours `#444444`
    / `#777777`, `#222222`; widths 0.55 / 0.6; value labels 5 pt above,
    12 pt; y to 1.18 / 1.25 × max; default 10 pt ticks and y label, 12 pt
    title; box; white background.
  - Two unstated matplotlib defaults the charts depend on, found by
    comparing: bars fill their axis up to a 5% margin (a single bar fills
    most of the panel), and ticks step by 1/2/2.5/5/10 with at most 9
    intervals (the bundles chart counts by 2.5). Both reproduced.
- Step 3: `plot_tree_counts(bundle, chart = "by_class" | "bundles" | "all" |
  "without_adjacent")`. Title stem from the bundle (`Chichewa (nyan1308)`),
  not typed in.
- Step 4, comparison (`check_tree_counts.R`,
  `comparisons/nyan1308_tree_count_*.png`): 8.1%, 6.8%, 7.2%, 7.1%
  differing pixels. By eye: bar lengths, order, colours, ticks, value labels
  and margins match. Remaining differences are fonts (R's sans is narrower
  than DejaVu Sans) and hyphens in labels drawing long like minus signs (a
  WinAnsi PDF encoding was tried and changed nothing). Horizontal renders are
  1 px shorter than the references (380 vs 381).
- Transparency (`pdftocairo -png -transp`, `check_transparency.py`): both
  house-style charts' backgrounds fully transparent, corner alpha 0, 85%/84%
  of pixels transparent vs 86%/85% for the references.
- Shifted-dataset check (`comparisons/shifted/shifted_nyan_tree_count_*.png`;
  new test `test_tree_counts_unchanged`): same counts; `Tonal` bar in grey;
  the syntax-like bundle drops to 4 trees (defined by type names, as in
  chart 6), which reorders the bundles chart and changes its ticks to steps
  of 1. No leaks.
- The matplotlib plotting functions are not deleted (§4.3: only after Jeff
  approves cutover).
- R6 search: comments only.
- Looked at by Claude: yes (all four comparisons twice, the shifted type and
  bundles charts). Seen by Jeff: no.
- Status: done pending Jeff's review.

## Chart 17: boundary-strength charts (3 files) — cross-language port (§4.3)
- Step 1, calculation: the exporter calls `boundary_strength.py`'s
  `compute_boundary_strength()` unchanged for the full data and every subset
  analysis, writing `boundary_strength.tsv`. `verify_boundary_strength_export.py`:
  the full table and `subsets/no_tono/` equal the committed
  `nyan1308_boundary_strength.tsv` and `_no_tono.tsv`, 22 rows each. That
  also settles what the unnamed `_no_tono` table was: exactly the four
  non-tonosegmental types (question 11).
- Density: the distributions chart's curves are scipy's weighted
  `gaussian_kde`, and scipy is missing (question 10). The exporter rebuilds
  it in numpy (`weighted_gaussian_kde()`, scipy's documented rule for a
  numeric bandwidth) into `boundary_strength_density.tsv`: area 1, left
  peak 0.2332 at 5.07, right peak 0.1519 at 21.5 — the reference's peaks;
  the comparison image shows the curves on top of scipy's.
- Step 2, visual settings: listed with source lines in the header of
  `R/boundary_strength.R` (bars lines 126–156, distributions 159–200),
  including the matplotlib margin and tick rules reused from chart 16.
- Step 3: `plot_boundary_strength(bundle, subset = NULL)` (bars; the
  no-tonosegmental file is `subset = "no_tono"`) and
  `plot_boundary_strength_distributions(bundle, subset = NULL)`.
- Deliberate difference: the legend reads "capped (reference only, max N)"
  with the analysis's own family count. The script typed in 69, so the
  committed no-tonosegmental chart says "max 69" while its dotted line sits
  at 24; the port says 24. Full chart unchanged (69).
- Step 4, comparison (`check_boundary_strength.R`,
  `comparisons/nyan1308_boundary_strength{,_no_tono,_distributions}.png`):
  5.7%, 5.1%, 10.3% differing pixels. By eye: bar heights, capped marks,
  dotted line, ticks, curves and dot rows match; differences are fonts,
  line weights and legend key shapes. One fix found by looking: zero-strength
  positions drew tiny specks in the dot rows (matplotlib draws nothing
  there); now left out.
- White background (not a transparent chart), so no alpha check needed.
- Shifted-dataset check (`comparisons/shifted/shifted_nyan_boundary_strength*.png`;
  new test `test_boundary_strength_shifted`): same strengths two positions
  later. One expected difference, predicted by the test before rendering:
  position 1 has a capped mark at 69, because every shifted family contains
  the added full root `[1-24]` (nothing is summed there). `no_tono`
  skipped (no tonosegmental in that data).
- Plotting functions in `boundary_strength.py` not deleted (§4.3).
- R6 search: comments and doc references only.
- Looked at by Claude: yes (all three comparisons, twice for the
  distributions; shifted bars). Seen by Jeff: no.
- Status: done pending Jeff's review.
