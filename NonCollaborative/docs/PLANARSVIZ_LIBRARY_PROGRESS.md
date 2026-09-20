# planarsviz library rebuild — progress

Plan: `docs/PLAN_planarsviz_library.md`. Branch `planarsviz-library`, worktree
`/Users/jcgood/gitrepos/planars-planarsviz`. Started 2026-09-14/15 overnight by
Claude (Opus) with Jeff's authorization to proceed without waiting.

Honesty rule: nothing below says "matches" without naming the comparison file.

## Where things stand (2026-09-20)

- **All 18 planned charts are ported, plus chart 19** (66 chart outputs as of
  2026-09-20). Every chart copied from working R reproduces its reference
  exactly: identical plot data and 0.0000% differing pixels. The two
  matplotlib charts (16, 17) are ported to R with every visual setting mapped;
  they differ only in fonts. Chart 19 (fragmentation test) was added after the
  cutover, at Jeff's request, and is also 0.0000%.
- **Renderer done** (`scripts/render_planarsviz.R`): draws every chart a
  bundle supports; its nyan1308 output passes `check_renderer.py`.
- **Generalization pass done**: every chart also renders from the shifted
  test data with only the expected differences, and the shifted bundle is
  in the Python tests.
- **Cutover done, all four commits** (2026-09-20). C1 `results/` holds
  library-rendered charts; C2 the superseded R scripts are archived in
  `OlderFiles/planarsviz_superseded/`, where the checks still run them; C3
  the Python that wrote them is removed; C4 the documentation matches. See
  the four entries at the end of this file.
- **Phase B is finished (2026-09-20).** All eleven questions below are
  settled or moot: question 8 (branch not pushed) went away when PR #294
  merged, and question 11 (boundary-strength files missing from
  `results/visualizations.md`) was folded into C4, which rewrote that file.
- **Not done, both deliberately deferred:** Phase E (the `illustrations`
  bundle — question 1 has its design) and tooling (R9: CI, `renv`, `lintr`,
  `R CMD check`, `vdiffr`, roxygen/testthat), which the plan holds back until
  the charts match. They do now, so R9 is unblocked rather than blocked.
- **Seen by Jeff: still none.** Every "0.0000%" in this file was read by
  Claude off a check's output; nobody has looked at the charts themselves.
  Comparison images are under `results/planarsviz/comparisons/`
  (reference | new | difference). This is the one outstanding item that
  only Jeff can clear.

---

## Open questions for Jeff

1. **Settled 2026-09-19: keep them, as their own bundle.** They are research
   output, and more general illustrations are expected. They fit the
   library's rule (Python computes, R draws from a data folder); what they
   lack is a *language*, not data. So: an `illustrations` bundle at
   `results/planarsviz/illustrations/data/` holding `tree_shapes.tsv` (n,
   shape number, Newick — exhaustive for n=2–4, sampled above that),
   `tree_counts.tsv` (n, Catalan, little Schröder A001003, n-ary A007052)
   and a `metadata.json` recording what is exhaustive, what is sampled, and
   the random seed. Written by a new
   `scripts/analysis/export_planarsviz_illustrations.py` reusing the
   enumerator in `generate_supercatalan_rows.py`. R draws it with
   `plot_tree_shapes(ref, n)` and a new `plot_tree_count_growth(ref)` (the
   counts become data, so the growth of the tree space against the 69
   families can be a chart rather than a table). Named `illustrations` and
   not `reference` because `results/planarsviz/reference/` already holds the
   frozen images the porting checks compare against.
   `tree_counting_equations.pdf` stays LaTeX — typeset mathematics, which
   ggplot would render worse — and is documented as part of this family.
   `nyan1308_random_tree_overlay.pdf` joins it too: it was out of scope only
   because it samples randomly, and a recorded seed is the same fix; it
   reads both bundles, since its positions are real but its content is
   illustrative. Scheduled as **Phase E, after cutover**, since it is purely
   additive.
   Original question: these five files are in `results/` but were never in
   the §3.2 inventory — port, or treat as out of scope like the other
   exploratory/LaTeX outputs?
2. **Settled 2026-09-19: nothing to apply.** Jeff made the file to point at
   something during a conversation, not as feedback on the chart. It stays
   in `results/` as a one-off; it is not a chart output, gets no reference
   image, and no check covers it. (What the red ellipse marks: two thick
   edges ending in rounded line caps, which read as dark blobs. If that ever
   does want fixing, squaring off the line ends is a one-line change to the
   ghost-tree drawing, worth an option rather than a new default.)
   Original question: is there feedback in it the port should apply?
3. **Settled 2026-09-19: keep them where they are.** Jeff: "at the moment,
   these labels are a charting concern only." So
   `planar_tables/display_labels_<dataset>.tsv` stays the home, read by the
   exporter via `--labels-file` (defaulting to that name), falling back to
   the planar table's `Position_Label` and then to plain numbers. They are
   deliberately *not* a column on `planar_nyan1308.tsv`: that file is shared
   structure the main pipeline reads, and a charts-only column there would
   give one fact two owners.
   **If that changes** — if these become the canonical display names for
   Chichewa positions rather than chart labels — the move is small: the
   exporter reads from wherever they then live and nothing in R changes,
   since R only ever sees `position_labels.tsv` inside the bundle.
   Original question: the planar table's `Position_Label` column has short
   slot codes (`V`, `Un`, `PrS`…), but every chart uses different labels
   (`Root`, `Ext`, `PreSbj`…), which lived only in `laminar_analysis.py`'s
   `_NYAN1308_POS_LABELS`; the salvaged exporter special-cased
   `dataset == "nyan1308"` to get them (a leak).
4. **Settled 2026-09-19: `Elements == "root"` for now; the pipeline's
   keystone convention takes over once Chichewa is onboarded.** Established
   while answering: *neither* planar table in `NonCollaborative/`
   (nyan1308's or stan1293's) has a `Position_Name` column — they are an
   older format than the `coded_data/` tables the main pipeline reads, so
   `Position_Name == 'v:verbstem'` was never available here. nyan1308's root
   row is the file's only `Elements == "root"`: position 10, label `V`,
   description "verb root". `Elements` is used rather than `Position_Label`
   because it says what the position contains, whereas labels are a charting
   concern (question 3); `load_root_position()` raises if more than one row
   matches, and with no match `root_position` is null and charts omit the
   dotted root line instead of drawing it somewhere wrong.
   **When issue #72 lands** (Chichewa onboarded, needs the tonosegmental and
   intonational modules first) there will be a `coded_data` planar table
   with a real keystone row; the exporter should then read that file and use
   `Position_Name == 'v:verbstem'`, so the keystone has one definition
   rather than two. Nothing to point at today.
   Original question: confirm `--root-element root` is the right marker.
5. **Settled 2026-09-19: fixed — the axis shows every position.** The range
   came from the drawn spans, so nyan1308's axis started at PreSbj: only the
   full `[1-22]` root reaches position 1, and that root is excluded from
   this chart. Every other chart shows the whole structure, the axis is the
   planar structure rather than the data, and the truncation is silent — a
   reader comparing two charts would assume the axes align. Not
   Chichewa-specific: any language whose first position is not a span
   boundary loses it the same way. `positions = "drawn"` restores the old
   behaviour and is what the check compares against (numbers identical);
   the new default differs from the old file by 2.4% of pixels, all of it
   the bars shifting as the panel widens.
6. **Settled 2026-09-20: keep `#AA3377`.** Jeff confirmed Tol bright's
   purple, matching what `results/visualizations.md` already documents
   ("length = purple") and consistent with the four observed colours. The
   decision changes no pixel in nyan1308 — length never decides a colour
   there — it fixes the convention for the next language, where it may.
   Original question: the span chart's colour for `length` is inferred, not
   observed; see the chart 15 entry.
7. **Settled 2026-09-15: fixed.** The swatch now follows the lines'
   exponent (`legend_thickness_exponent`, default `thickness_exponent`;
   `0.5` reproduces the old legend exactly), and a swatch too thick for the
   legend box is pulled in so its rounded ends stay inside. All-families and
   wordhood legends: 0.05% differing pixels from the old files (the swatch
   only). Original question:
   **Overlay legend's "More" thickness swatch.** The generator draws the
   swatch at `sqrt(highest convergence)` even when the lines are drawn with
   exponent 0.75 (the all-families chart), so in chart 8/9's legend the
   swatch is thinner than the thickest line. Reproduced faithfully; say if
   the swatch should follow the chart's exponent.
8. **The branch is not pushed.** The repo's push hook requires syncing
   `planars-data` first, and syncing that repo was off-limits for this work,
   so every `planarsviz-library` commit exists only on this machine (worktree
   `/Users/jcgood/gitrepos/planars-planarsviz`). Push it yourself after the
   usual `coded_data` pull, or tell me to.
9. **Settled 2026-09-15: fixed.** Titles show by default, at 24 pt
   (`panel_titles`, `title_size`); `panel_titles = FALSE` reproduces the old
   chart exactly. With titles: 8.7% differing pixels from the old file
   (titles plus a small shift of each panel). Original question:
   **Conflict-groups chart has no panel titles.** The script sets titles
   ("All 69 families", "Group A: [5–13] (10 families)"…) with
   `plot_annotation()` on each panel, but patchwork ignores annotations on a
   panel nested inside a larger layout, so the committed PDF shows none —
   the reader can't tell which small panel is which group. Reproduced
   faithfully (the library builds the same titles, equally invisible). Fix
   by drawing the titles another way?
10. **Settled 2026-09-15: scipy added** to `requirements.in` (1.18.1 pinned
    in `requirements.txt`) and installed. `verify_boundary_density.py`: the
    exporter's numpy curves equal scipy's `gaussian_kde` for the full
    analysis and all six subsets (largest difference 1.3e-14, rounding
    only), so the numpy version stays and the exporter needs no scipy.
    `boundary_strength.py` now runs here and reproduces its committed table.
    Original question:
    **scipy is not installed.** The boundary-strength distributions chart
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
  patchwork, tidyverse, here, jsonlite. **Not installed at the time:**
  testthat, devtools, roxygen2 — so `NAMESPACE` was hand-written and the
  package installed with `R CMD INSTALL`. Consistent with R9 (no tooling
  yet). **roxygen2 was installed on 2026-09-20 and now generates
  `NAMESPACE` and `man/`** — see the entry at the end of this file.
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
- **Question 6, settled 2026-09-20: `#AA3377` stays.** It is inferred, not
  observed — in nyan1308 every length span also has a higher-priority type,
  so length never decides a colour — but it matches `visualizations.md`
  ("length = purple") and Jeff confirmed it. No pixel changes; the value
  is now the stated convention for the next language.
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
- **Changed 2026-09-16 at Jeff's request:** the colour key moved from beside
  the panel into the panel's empty lower-left corner, in a white box with a
  border (`legend_position`, default `"inside"`; `"right"` reproduces the old
  chart exactly, checked; `legend_inside` moves the box). Nothing is
  covered: every span in that corner starts at position 5 or later and the
  box ends before position 4, on both the full and the no-tonosegmental
  chart. Pixel difference from the old files: 5.2% and 4.2%, all of it the
  legend moving.
- **Changed 2026-09-16 at Jeff's request:** the count column's header is
  now two sizes, "Trees" (size 6, matching the counts) above a smaller
  "(n = N)" (size 4.5); it was one label at size 4 (`count_header_size`,
  `NULL` for the old label). Checked in close-up: no overlap, nothing cut
  off. With both changes switched off (`legend_position = "right"`,
  `count_header_size = NULL`) the charts are still identical to the old
  files; the check now compares the old script's plot data against that
  version. Both charts copied over `results/nyan1308_forestspans_plot*.pdf`
  for use before cutover.

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

## Chart 18: boundary-strength overlay (2 files)
- Source copied: `scripts/analysis/boundary_strength_plot.r:1-157` →
  `R/boundary_strength_overlay.R`, commit `0426f73` (line-for-line check).
- One function (`0902d5b`):
  `plot_boundary_strength_overlay(bundle, subset = NULL, colours, highlight
  = "orthographic_word")`. The script's two calls become options: the
  no-tonosegmental chart is `subset = "no_tono", colours = c(Left =
  "#009E73", Right = "#CC79A7")`. The function body is otherwise the
  script's, including its own weighted `density()` in R (no scipy involved).
- Literals replaced: the TSV path → the bundle's `boundary_strength.tsv`
  (chart 17's exporter addition, full or subset); position labels →
  `position_labels.tsv`; label text colours (black, red 5–19, `#0072B5` at
  17) → the `orthographic_word` highlight in `highlights.tsv`, the same data
  chart 9 uses. No new exporter fields.
- Numbers comparison (`check_boundary_strength_overlay.R`, which runs the
  script's function with `ggsave` replaced by one that keeps the plot): both
  variants' plot data and y breaks identical. Pixel comparison:
  `comparisons/nyan1308_boundary_strength_overlay{,_no_tono}.png`, both
  0.0000%.
- Shifted-dataset check
  (`comparisons/shifted/shifted_nyan_boundary_strength_overlay.png`): 24
  boxed labels with renamed positions, red on 7–21 and blue on 19 — the
  highlight moved with the data; bars and density curves two positions
  later. `no_tono` skipped. No leaks.
- Faithful behaviour worth knowing: y-axis ticks are every 50 by the
  script's own rule, so the no-tonosegmental chart (maximum 88) shows only 0
  and 50. Could become an option if wanted.
- Deviation from plan §6 (items 11–12), decided here: the plan said to fold
  charts 5, 17 and 18 into one boundary function with options. They stay
  three functions (`plot_boundary_skyline()`, `plot_boundary_strength()`,
  `plot_boundary_strength_overlay()`) because they are different charts, not
  variants of one: test counts faceted by domain type; matplotlib-style
  stacked panels with capped marks; dodged bars over density curves. One
  function would be a switch between three unrelated bodies, which removes
  no copy (the §1 "options, not copies" aim) and makes each harder to read.
  What they do share is already shared data: the bundle's
  `boundary_strength.tsv`, subsets and highlights.

## New chart, 2026-09-19: maximal binary branching (illustration)
- Asked for by Jeff: one tree showing as much binary branching as the
  evidence allows, for illustration rather than analysis.
- Any consistent tree is a subset of one of the 69 families, so this is a
  choice among them, not a new structure. Every observed span has at least
  one test behind it, so "supported" rules nothing out; branching is
  maximised by packing in the most compatible spans. The ceiling is 13
  spans, reached by 32 of the 69.
- Rule (exporter, `most_binary_order()`): most strictly binary nodes, then
  most tests supporting the tree, then the narrowest widest node, then
  family order. A node's children count its child spans plus the positions
  it covers directly — what the drawn tree shows. nyan1308 picks
  family_031: 7 binary nodes, nothing wider than 4 children, 69 tests, the
  highest of any family. The shifted test data picks the same family number.
- Notable: family_031 is also what greedy selection by test support gives
  (see the consensus note below), so the most branching tree is also the
  best-attested one — they agree here, which is worth saying in a caption.
- R: `plot_frequency_tree()` gained `title`, `weight` (`"families"`
  default, `"tests"`, `"none"`) and `branch_size`. Drawn with
  `weight = "none"`: frequency shading made the deep binary spine — the very
  structure being illustrated — nearly invisible, and test weighting faded
  the outer backbone instead, which rests on few tests.
- Thickness: the weighted charts scale line width up to 4 at full support,
  so drawing unweighted put every branch at that maximum and the first
  version came out far too heavy (Jeff asked). `branch_size` now controls
  it, defaulting to 4 as before and to 0.5 when nothing is weighted —
  ggtree's own default, so the illustration matches the exemplary trees,
  which pass no line width (Jeff asked for that specifically). The weighted
  charts are untouched (re-checked, both still 0.0000%).
- Checks: frequency tree and four trees re-checked after the `weight`
  change, both still identical (0.0000%); 14 bundle tests pass, including a
  new one pinning that `most_binary` names a maximally resolved family.
- Renderer name `most_binary_tree`; copied to
  `results/nyan1308_most_binary_tree.pdf` for use before cutover. No old
  file — this chart did not exist before.
- **Second version, 2026-09-19 at Jeff's request:** the same tree with the
  orthographic word's extent traced in thicker lines (`emphasis`,
  `emphasis_size`; new `planarsviz_highlight_range()`). The traced edges are
  those covering one boundary position but not the other — for [5–19], the
  descent to Neg1 and the edge out to Enc, drawn as a bold inverted V around
  the word. The positions come from `highlights.tsv`, so the renderer makes
  one such chart per highlight a bundle has (`most_binary_tree_<id>`); the
  plain version is kept. Weighted trees re-checked, still 0.0000%.
- Consensus note (for the record): strict consensus over the 69 keeps 5
  spans, majority rule 10 (guaranteed a tree), greedy by family count 13
  (= family_016, the existing frequency tree), greedy by test support 13
  (= family_031). Family count largely measures how uncontested a span is,
  not how well attested: [5–19] is in all 69 families on 1 test, while
  [6–17] has 19 tests but sits in 23 families.

## Renderer (§8.3) and final generalization pass (§10.3)
- `scripts/render_planarsviz.R --bundle DIR [--output DIR] [--plots
  all|names] [--formats pdf,png] [--list]`. The chart list is built from the
  bundle, not typed in: a pooled pair per observed domain type, a forest per
  `forests.json` entry, highlight and filter variants from `highlights.tsv`
  and `subsets.json`, exemplary charts per selected family, conflict-group
  charts only when groups are defined. Canvas sizes come from the chart
  functions (each carries its source script's `ggsave()` size), so there is
  no second size table as §8.3 suggested — one place instead of two.
  Refuses truncated bundles; reports and exits non-zero on any failed chart;
  writes `manifest.tsv` (bookkeeping only).
- Rendering choice kept in the renderer: filtered boundary-strength
  overlays use the script's second colour pair (`#009E73`/`#CC79A7`).
- File naming change for cutover: highlight variants are
  `all_families_labeled_<highlight_id>` (`_orthographic_word`), not
  `_wordhood`, because the name must come from the data.
- Small fix: `plot_pooled()` now sets `planarsviz_units` ("cm") like every
  other chart function; the renderer needs it.
- Check (`scripts/planarsviz_checks/check_renderer.py` on a render of the
  nyan1308 bundle): 63 of 63 charts; all 57 charts copied from R 0.0000%
  differing pixels; the 6 matplotlib-port files show their recorded font
  differences (5.1–10.3%); no reference without a render.
- Final pass on the shifted bundle through the renderer: 59 of 59 charts
  rendered. Charts only in nyan1308: `tono_laminar_forest` and the
  `pooled_plot_tonosegmental` pair (type renamed), and the three `no_tono`
  variants (no tonosegmental to leave out). Only in shifted:
  `pooled_plot_tonal` pair. Exactly the expected set. Every chart's
  nyan1308-vs-shifted side by side was already looked at chart by chart
  (entries above); §10.3 step 5 (shifted bundle in the Python tests) is
  `tests/test_planarsviz_shifted_bundle.py`.
- Remaining by plan (§6 item 7): tooling (R9) and the cutover conversation.
- R6 search: comments and doc references only.
- Looked at by Claude: yes (shifted side by side). Seen by Jeff: no.
- Status: done pending Jeff's review.

## Cutover C1: results/ is where the charts are rendered (2026-09-20)

- **What changed.** `Rscript scripts/render_planarsviz.R --bundle
  results/planarsviz/nyan1308 --output results --formats pdf` now writes the
  published charts. 65 of 65 charts, 63 replacing an existing file and 2
  under the new highlight-id name. The superseded
  `nyan1308_all_families_labeled_wordhood.pdf` and `_wordhood_legend.pdf`
  are deleted; everything else in `results/` keeps its name.
- **The count is 65, not the 63 the earlier entries say.** The
  maximal-binary-branching chart added two on 2026-09-19. Nothing was lost.
- **Fidelity, checked before writing to `results/`.** A clean full render to
  a scratch directory, then `check_renderer.py` on it: every chart copied
  from working R at 0.0000% differing pixels, the five deliberate changes
  and the six matplotlib-port font differences exactly as recorded above,
  no reference without a render, no chart failed. `most_binary_tree` and
  `most_binary_tree_orthographic_word` report "no reference" — correct, they
  are new and have no old file to compare against.
- **Manifest renamed** to `<dataset>_planarsviz_manifest.tsv`. `results/` is
  shared with everything else this project generates, where a file called
  `manifest.tsv` says nothing about what it belongs to. `check_renderer.py`
  finds it by pattern and stops if a directory holds more than one.
- **A bundle's `plots/` is no longer tracked in git**
  (`.gitignore`: `NonCollaborative/results/planarsviz/*/plots/`; 129 files
  untracked, not deleted). It is the renderer's default output and where
  `scripts/planarsviz_checks/` writes its trial renders — a working area.
  With `results/` holding the published charts, tracking both would keep two
  copies of every chart, which is the duplication this project treats as a
  defect. **Consequence for C2:** several checks compare a shifted-bundle
  render against `results/planarsviz/nyan1308/plots/<file>.pdf`, which now
  has to be rendered before those checks run. C2 repoints them at `results/`
  (it is already updating their paths), which removes the precondition.
- **Docs fixed on sight, not deferred to C4.** `scripts/INDEX.md`'s
  `render_planarsviz.R` entry named a `manifest.json` that never existed,
  listed thirteen chart names that are not the renderer's, and gave an
  `--output` that would have written plots inside the data bundle; it now
  says the chart list comes from `--list`. `docs/CHART_MECHANICS_AND_
  UNCERTAINTY.md`'s pointer to the `_wordhood` files now names the
  `_orthographic_word` ones and says where they come from.
- Looked at by Claude: yes (the check output). Seen by Jeff: no.
- Status: done.

## Two things C3 must not get wrong (found 2026-09-20 while checking the concurrent session's note)

C3 removes the matplotlib plotting from `laminar_tree_counts.py`. Two facts
about that file turned up while verifying the concurrent analysis session's
handoff note, and both would be easy to destroy by accident:

- **`CLASS_COLORS` must survive.** Its only remaining in-file consumer is
  `save_class_figure()`, which C3 deletes — so a straightforward "remove the
  plotting" pass takes the dict with it. But
  `scripts/analysis/class_fragmentation_test.py` (the concurrent session's
  work, not yet committed) imports it, and so does its R plot by way of a
  `color` column. Keep the dict, drop only the drawing.
- **Those same five colours are also written out in
  `export_planarsviz_data.py`'s `DOMAIN_TYPE_STYLE`** (`colour` field —
  identical values, verified against the bundle's `domain_types.tsv`). One
  fact, two owners, which is the defect this project keeps paying for. The
  exporter already imports `CLASS_ORDER` from `laminar_tree_counts`, so
  taking `colour` from `CLASS_COLORS` is not a new coupling. Deliberately
  **not** fixed on sight: changing the exporter regenerates the bundle and
  so needs the chart checks re-run, and the concurrent session is live in
  these same files. Do it in C3, with the checks.
  (The exporter's comment calling `DOMAIN_TYPE_STYLE` "the one place R gets
  them from" is true of R and misleading about Python — fix the wording in
  the same pass.)

## Cutover C2: the superseded scripts are archived, not deleted (2026-09-20)

- **21 scripts moved to `OlderFiles/planarsviz_superseded/`** with `git mv`,
  so their history follows them: 18 generated ones out of `results/` (the
  eight chart-6 forests, chart 7's overlay, chart 8 and its `_wordhood`
  variant, chart 10's exemplary trees, chart 11's two ForestSpans scripts,
  and charts 12, 13, 14, 15) and 3 hand-written ones
  (`scripts/domain_charts-cgpt.r` for charts 1-4,
  `scripts/nyan_boundary_skyline.r` for chart 5,
  `scripts/analysis/boundary_strength_plot.r` for chart 18).
- **Only `results/nyan1308_random_tree_overlay.r` stays** in `results/`: it
  was never ported (random sampling) and belongs to Phase E.
- **Why archived rather than deleted.** The porting checks run each old
  script in memory and compare — they are the evidence behind every
  "0.0000% differing pixels" claim above. Several also can no longer be
  regenerated: C3 removes the Python that wrote them. Both
  `OlderFiles/README.md` and `NonCollaborative/CLAUDE.md` previously said
  "do not use for new work" of the whole archive; each now carries the
  exception, because a reader tidying `OlderFiles/` would otherwise be
  destroying the proof without knowing it.
- **The archive path has one owner**,
  `scripts/planarsviz_checks/superseded.R`. Eleven sourcing sites across ten
  checks went through it rather than each spelling the path out, and it stops
  with an explanation if a script is missing instead of letting a check skip
  quietly. The `results/` path deliberately did *not* get the same treatment:
  it is referenced throughout the project already and is not going to move.
- **C1's leftover closed.** The twelve sites that compared a shifted-bundle
  render against `results/planarsviz/nyan1308/plots/<file>.pdf` now read
  `results/`, so the checks no longer depend on an untracked working
  directory having been populated first.
- **Verified: every check still proves what it proved before.** All thirteen
  run clean from the archive — pooled (12 charts, 0.0000%), forests (8,
  0.0000%), skyline, spanchart, exemplary (7 exemplars x 3 layouts),
  conflict groups, ForestSpans, summary trees, boundary-strength overlay,
  boundary strength, tree counts. Each deliberate change and each
  matplotlib-port font difference reports its recorded percentage, unchanged.
- **Docs fixed in this commit rather than left for C4**, because these were
  broken commands, not stale prose: `results/visualizations.md` told a reader
  to run `domain_charts-cgpt.r` and `nyan_boundary_skyline.r` at paths that
  no longer exist (now the `render_planarsviz.R` equivalents, with a pointer
  to the archived original), and `CLAUDE.md` listed both as living in
  top-level `scripts/`.
- Looked at by Claude: yes (all thirteen check outputs). Seen by Jeff: no.
- Status: done.

## C2 left four checks pointing at an empty shelf (fixed 2026-09-20)

C2 moved the superseded scripts and repointed the ten checks written in R,
through the new `superseded()` helper. It missed the four written in Python:
`verify_forest_export.py`, `verify_forestspans_export.py`,
`verify_overlay_export.py` and `verify_selection_export.py` all still read
`results/`, so each one crashed with a missing-file error the moment it ran.
C2's own "all thirteen run clean" was true of the R checks it counted and
silent about these.

- **Fixed with a Python twin of the helper**, `superseded.py`, with the same
  single-owner property and the same refuse-to-skip behaviour: a missing
  script raises with the reason rather than letting a check quietly pass over
  it. All four now pass against the archive.
- **Why the same helper twice rather than one of them.** The two languages
  cannot import from each other, so the choice was two small files naming one
  directory, or fifteen call sites naming it. Each file says the other exists
  and must agree with it.
- Looked at by Claude: yes (all four check outputs). Seen by Jeff: no.
- Status: done.

## Cutover C3: the superseded Python is removed (2026-09-20)

The analysis stays, the drawing goes. Nothing in `NonCollaborative/` writes an
R script or a matplotlib figure any more; every chart comes from the
`planarsviz` package reading the exporter's bundle.

- **`laminar_analysis.py`: 1808 lines to 865.** Gone: `generate_r_script`,
  `generate_r_overlay_script`, `run_domain_overlay`,
  `generate_r_exemplary_trees_script`, `generate_exemplary_trees`, and the
  `__main__` block's calls to them. `main()` lost `output_dir`, `color`,
  `tpfx` and `pos_labels` — every one of them an argument only the R output
  used — and now prints its report and returns, writing nothing.
  `select_representative_families` stays: the exporter calls it.
  `_NYAN1308_POS_LABELS` goes, because `planar_tables/
  display_labels_nyan1308.tsv` holds the same 22 labels (checked key by key
  before deleting, identical) and the exporter reads that file.
- **`laminar_tree_counts.py` and `boundary_strength.py`** keep their counting
  and lose their matplotlib. Both write the same TSV they always did:
  regenerated and diffed byte for byte against the committed
  `results/nyan1308_tree_counts.tsv` and
  `results/nyan1308_boundary_strength.tsv`.
- **`make_forestspans_table.py`** keeps the two LaTeX outputs — both
  regenerate byte-identically — and loses `make_r_plot_script`,
  `run_r_script`, and the domain-type palette and blend used only by that
  chart. **`make_forestspans_table_no_tono.py` is deleted outright**: it
  existed only to run that generator over a filtered analysis, and the
  library draws the no-tono chart from the bundle's `subsets/no_tono/`.
- **The duplicated palette is fixed, as the traps entry said to do it here.**
  `export_planarsviz_data.py`'s `DOMAIN_TYPE_STYLE` no longer writes the five
  colours out; it reads them from `laminar_tree_counts.CLASS_COLORS`, which is
  now their only home. The orders and the second (Tol) palette stay in the
  exporter, since they are chart facts, not domain-type facts. `CLASS_COLORS`
  itself survived the plotting removal, the other half of that trap.
  Regenerating the whole bundle afterwards gives files identical to the
  committed ones, `domain_types.tsv` included.
- **Every check still proves what it proved.** All seven Python export checks
  and all six R porting checks re-run: pooled 0.0000%, forests 0.0000% across
  all eight, overlays, exemplary, conflict groups, ForestSpans, summary trees,
  skyline, boundary-strength overlay all unchanged, and each deliberate change
  and matplotlib-port font difference reports its recorded percentage. The
  renderer check compares all 65 renders and passes.
- **One check lost a half it can no longer run.** `verify_forest_export.py`
  used to regenerate each bundle's forest script with `laminar_analysis.main()`
  and compare byte for byte. With the generator gone that half is deleted; the
  archived scripts are still what every tree, span list and thickness value is
  compared against, so the check's substance is intact.

### A second thing C1 left pointing at itself

`check_tree_counts.R` printed a transparency figure for "port" and
"reference". Since C1 the reference it read, `results/nyan1308_tree_count_
by_class.pdf`, has been the library's own output — so the line compared the
port with itself, and printed the same number twice without anyone noticing.

- **Caught before C3 made it unfixable.** The matplotlib that drew the real
  reference was about to be deleted, so it was restored from `ffa9032`, run,
  and its two transparent charts frozen as
  `results/planarsviz/reference/nyan1308_tree_count_{by_class,bundles}
  _transp.png`, beside the other frozen references. The check reads those now.
- **The numbers it should have been printing**: reference 86.3% and 85.1%
  fully transparent, port 85.1% and 83.9%. Close, and the port is slightly the
  less transparent of the two — the difference is font and bar geometry, the
  same source as these charts' recorded 6-8% pixel difference.
- `check_renderer.py` skips `*_transp.png` when listing references with no
  render; they are measurements, not charts.
- **The concurrent session's scripts are unaffected**, which was the other
  thing to get right: `class_fragmentation_test.py` reproduces both its
  summary TSVs byte for byte at 5000 draws after the edits, and
  `refinement_counts.py` and the whole `NonCollaborative/tests/` suite run
  clean.
- Looked at by Claude: yes (all thirteen check outputs, the bundle diff, the
  five TSV diffs). Seen by Jeff: no.
- Status: done. C4 next — the documentation pass.

## Cutover C4: the documentation pass (2026-09-20)

The last of the four cutover commits. Four files were named for it; a fifth
and a sixth turned out to need the same treatment, and one more generated
script turned up that C2 had missed.

- **`results/visualizations.md`** (787 → 913 lines). Its opening told a reader
  to run a command that no longer exists and render an R script that is no
  longer there; both are replaced by the two commands that actually make these
  charts. Six section headings named a generated script rather than the chart
  it drew, and are renamed after the chart, each with the `--plots` name to
  draw it and a pointer to its archived original. Every in-body reference to a
  removed generator function is gone.
- **The file was also incomplete, which the cutover exposed.** Fifteen charts
  in `results/` had no entry at all — the coloured overlay, the eight per-class
  forests, ForestSpans, the four boundary-strength charts, the most-binary
  trees. Rather than write fifteen entries duplicating
  `docs/planarsviz_charts.md`, which already catalogues every one with an
  example image, the file now says which of the two to read for what and
  carries a table pointing each uncovered chart at its catalogue section. Two
  more sections cover what was left: the supercatalan illustrations, the
  renderer manifest, the 2026-04-18 written summary, and what lives under
  `results/planarsviz/`.
- **`scripts/INDEX.md`.** Claimed `laminar_analysis.py` writes an R script and
  a markdown summary — the first was true until C3, the second has not been
  true since April. Its whole "Visualization (R) — Generated Output" section
  described files that no longer exist, and is replaced by an account of where
  the charts went. Six scripts in its own remit had no entry
  (`laminar_tree_counts.py`, `boundary_strength.py`, `planars_groupings.py`,
  `random_tree_overlay.py`, the two supercatalan ones) and now do, as does
  `planarsviz_checks/`.
- **`scripts/README_laminar_analysis.md`** was the worst of them. It
  documented an input format with eight columns that do not exist
  (`Position_Name`, `Element`, `Span_Start`, `Span_End`, `Test_Name`,
  `Criterion`, `Value`) — the real file has six — and a command
  `python laminar_analysis.py <file>` that has never worked, since the script
  takes no arguments. Both corrected against the code, along with the output
  section, the key-functions list, the troubleshooting entries and the
  see-also links.
- **`NonCollaborative/CLAUDE.md`.** Its `scripts/analysis/` list named three of
  the eight scripts there; it did not mention `planarsviz_checks/`,
  `render_planarsviz.R` or `make_forestspans_table.py` at all; and its
  "Running scripts" section still said to `cd scripts/analysis` and listed
  `matplotlib` as a dependency.

### Three things found while checking that the commands run

Every command in these files was run rather than read.

- **`fragmentation_test_plot.r` could not be run as documented.** It resolved
  `results/` as `"../../results"` against the working directory, so it only
  worked from `scripts/analysis/` — but both `INDEX.md` and
  `visualizations.md` told a reader to run it from elsewhere. It now resolves
  from its own file location, the way `render_planarsviz.R` does. The chart it
  draws is unchanged: 0.0000% differing pixels against the committed PDF.
- **`render_supercatalan_rows.r` has the same shape of dependency** and is
  documented rather than changed, because the Python script launches it with
  the right working directory and is the supported way to run it. The
  documented command is now `generate_supercatalan_rows.py --pdf`, which does
  the whole job.
- **One working directory, not two.** The committed bundle was exported from
  `NonCollaborative/`, and the exporter records the domain file's path as
  given, so running the documented command from the repo root produced a
  bundle differing in that one field. Every command in these files now runs
  from `NonCollaborative/`, matching the porting checks; verified by
  re-exporting and diffing the whole bundle, which came back identical.

### A generated script C2 missed

`scripts/laminar_forest.r` — an earlier, unlabelled 69-family forest — sat in
`scripts/` rather than `results/`, so C2's sweep of `results/` did not see it.
Archived with the others. No check compares against it; it is kept because the
Python that wrote it is gone and nothing else records what it drew.

- Looked at by Claude: yes (every command in all four files run; pytest; three
  porting checks re-run after the archive move). Seen by Jeff: no.
- Status: done. **Cutover complete.** Phase E next — the `illustrations`
  bundle — and chart 19, the fragmentation test, requested during C4 (below).

## Chart 19, requested 2026-09-20: port the fragmentation test

Jeff asked, through the analysis session, that the class-fragmentation test be
part of `planarsviz` proper — a bundle table and a chart function, the way
`boundary_strength` and `tree_counts` are — rather than a standalone script
reading its own TSVs. Not started. What it needs:

- A `fragmentation_test.tsv` in the bundle, combining the class and bundle
  summary rows under a `kind` column, the way `tree_counts.tsv` already does.
  `class_fragmentation_test.run_test()` has the same calling shape as
  `boundary_strength.compute_boundary_strength()`, so it slots into the
  exporter the same way.
- A decision about the null draws. `nyan1308_fragmentation_null_draws.tsv` is
  5000 draws × 8 groups = 40,000 rows for one language, which does not fit the
  bundle's usual one-row-per-position/span/family shape. `subsets.json`'s
  pattern — an index plus a directory of per-item files — may fit better than
  one flat table. Worth settling before the table is written, not after.
- A section in `r/planarsviz/inst/data-contract.md` for whichever shape it
  takes, written the way the `boundary_strength.tsv` section is.
- **This port has no matplotlib original.** Every other chart had one to
  compare against pixel for pixel, and the plan's whole methodology assumes
  that. This chart was written in R from the start, so
  `results/nyan1308_fragmentation_test_plot.pdf` is itself the reference a
  port must reproduce. The shifted-dataset leak check applies normally; only
  the pixel comparison against an original is different.
### Settled by Jeff, 2026-09-20

Three questions went to Jeff before any of this was built. His answers:

1. **The null draws go in the bundle as a tally**, not as raw draws and not as
   an index-plus-directory. `family_count` is a small integer with few
   distinct values, so `(group, kind, family_count, n)` collapses nyan1308's
   40,000 draws to **227 rows** with nothing lost but draw order, which
   nothing uses and the seed reproduces anyway. For scale: the raw file is
   900K against the whole rest of the bundle's 508K; the tally is about 5K.
   The violin draws from a weight, and the p-value recomputes.
2. **The exporter runs the test behind a flag**, not on every export and not
   by reading the committed TSVs. A full export is 1.6 seconds; the test at
   5000 draws is about four minutes (measured: 12.3s at 250 draws), and there
   are two bundles, so always-on would make every export ~150× slower for the
   chart-iteration loop. Reading the TSVs was rejected for the usual reason —
   it would put the same numbers in two places with no single owner, which is
   what this project keeps paying for. The flag keeps the exporter deriving
   rather than reading, and the test is deterministic, so a bundle built with
   the flag is reproducible by anyone. The cost accepted with it: a bundle
   built without the flag has no fragmentation table, and the chart has to
   say so rather than fail.
3. **Not per-subset, for now.** The note that raised this said it was easy to
   add now and awkward to retrofit; that is not right —
   `export_boundary_strength()` is already called once inside the subset loop
   and once for the full data, so adding this there later is one line using
   machinery that already exists. Worth knowing too: only `kind: "filter"`
   subsets have more than one domain type, and there is exactly one
   (`no_tono`) — the six per-domain-type subsets cannot support a label
   shuffle at all, since every row in them carries the same label. So
   "per-subset" meant precisely "also run it for `no_tono`", roughly doubling
   an already-slow computation to answer a secondary question nothing
   currently asks.

Everything else follows precedent rather than choice: the table shape takes
`tree_counts.tsv`'s `kind` column, the chart function sits beside
`plot_tree_counts()`, and `class_fragmentation_test.py` keeps its CLI and
loses its R script, the way `boundary_strength.py` kept its CLI and lost its
matplotlib.

## Chart 19: the fragmentation test, ported (2026-09-20)

Built on the three decisions above. The chart the package draws is
**pixel-identical to the one the standalone script drew** — 0.0000% over a
1000 × 650 render — and the bundle's numbers equal the committed TSVs exactly.

- **Two new bundle tables, both only when asked.**
  `--fragmentation-permutations N` (and `--fragmentation-seed`) on the
  exporter writes `fragmentation_test.tsv` (one row per group: `group`,
  `kind`, `label`, `colour`, `n_tests`, `observed_families`, the null's mean
  and 5th/95th percentiles, `p_value_ge_observed`, `n_permutations`, `seed`)
  and `fragmentation_null.tsv` (the tally). Both are documented in
  `r/planarsviz/inst/data-contract.md`, and the run's draw count and seed go
  into `metadata.json` so a bundle says what produced its p-values.
- **227 tally rows for 40,000 draws**, exactly as the arithmetic predicted.
  The check proves the tally lost nothing by expanding it back and comparing
  per group against the committed raw draws, sorted — the tally drops draw
  order and nothing else.
- **The R expands the tally before drawing rather than using a weight.**
  `geom_violin` does take a `weight` aesthetic, but its density estimate
  weights and normalises differently enough that an identical result is not
  guaranteed, and identical is this chart's whole claim. 40,000 rows is
  nothing to hold in R, so the expansion buys exactness for no real cost.
- **Two nyan1308 facts came out of the R in the move**: the eight display
  labels were a hardcoded lookup and the colours came from a `color` column
  the Python filled from its own palette. Both now come from the bundle
  (`label`, `colour`), which is what makes the leak check meaningful.
- **The exporter builds its groups from the domain types the data has**,
  the way `export_tree_counts()` does, rather than from
  `class_fragmentation_test.py`'s fixed `CLASS_GROUPS`. That is what lets the
  shifted test data — which renames one domain type — work at all. One real
  bug fell out of writing it: `run_test()` looked its colour up as
  `GROUP_COLORS[name]`, which raises `KeyError` on any domain type outside
  this project's five. Now `.get()` with the fallback grey.
- **The published file keeps its name.** The renderer's chart is
  `fragmentation_test_plot`, not `fragmentation_test`, so
  `results/nyan1308_fragmentation_test_plot.pdf` is still what it was. No
  entry needed in the name-changes table.
- **`fragmentation_test_plot.r` stays.** It is the original the port is
  checked against, the same reason the archived scripts stay. It still reads
  the committed TSVs and still draws the same chart.
- **Checks:** `scripts/planarsviz_checks/check_fragmentation.R` — numbers
  against the committed TSVs, the tally's expansion against the committed raw
  draws, and pixels against the frozen reference. `check_renderer.py` now
  compares 66 charts, up from 65, with no reference unmatched. A new
  `test_fragmentation_tables_agree` in `tests/test_planarsviz_bundle.py`
  guards the one invariant that makes the tally safe to store instead of the
  raw draws: every group's counts must sum to its own `n_permutations`. If
  they stopped, the violin would be drawn from an incomplete null with
  nothing looking wrong.
- **The shifted-dataset leak check passes, and passing means differing.**
  The shifted bundle was exported with the test too, and its chart differs
  from nyan1308's by 6.16% of pixels — which is the point: a 0.0000% here
  would mean the chart was drawing nyan1308 facts rather than the bundle in
  front of it. What changed is exactly what should: the renamed domain type
  appears as its own row, labelled **Tonal** and drawn in the fallback grey
  because the palette has no entry for it, while carrying the same numbers
  nyan1308's tonosegmental row does, the two being the same data renamed.
  One consequence worth not mistaking for a bug: `syntaxlike` and
  `syntaxlike_notono` come out identical there, because `syntaxlike`'s
  definition names `tonosegmental`, which that dataset does not have, so it
  collapses to the same two types the no-tono bundle has.
- Looked at by Claude: yes (the new check, the renderer check, the bundle
  diff). Seen by Jeff: no.

## Phase D, first step: roxygen2 generates NAMESPACE and man/ (2026-09-20)

The R tooling the plan held back under R9 ("no tooling until every chart
matches") is now unblocked, since the charts match. Jeff named this **phase D**
— the phase list agreed back in September went B, C, E and skipped D entirely,
and the tooling was the one substantial piece of work with no letter at all.

This first step was worth doing for a reason beyond hygiene: **the hand-written
`NAMESPACE` was exporting internal helpers by accident.** `exportPattern
("^planarsviz_")` matched every name with that prefix, so 45 objects were
public while only 36 carried an `@export` tag. Roxygen exports only what is
tagged, so these nine stopped being part of the API:

`planarsviz_analysis_dir`, `planarsviz_house_bar_chart`,
`planarsviz_mpl_bar_expand`, `planarsviz_mpl_breaks`, `planarsviz_mpl_theme`,
`planarsviz_pooled_setup`, `planarsviz_require_trees`,
`planarsviz_selected_family`, `planarsviz_vertical_bar_chart`.

`planarsviz_mpl_theme` and `planarsviz_mpl_breaks` exist only to imitate
matplotlib's defaults for the two cross-language ports; they should never have
been callable from outside. Nothing outside the package called any of the nine
— checked before the change, across `scripts/` — so narrowing the surface
broke nothing.

- **The trap, caught before anything ran.** The R source had 36 `@export` tags
  and **zero** `@import`/`@importFrom` tags: every import directive lived only
  in the hand-written `NAMESPACE`. Running roxygen straight would have
  regenerated a `NAMESPACE` with no imports at all, and every unqualified
  `ggplot()`, `%>%` and `mutate()` call in the package would have failed —
  installing fine and breaking on first use. So a package-level block,
  `R/planarsviz-package.R`, now carries those imports as roxygen tags. The
  generated import directives were diffed against the old file's: identical,
  no package or function added or dropped.
- **Two helpers stayed exported on purpose-of-record:**
  `planarsviz_ghost_tree` and `planarsviz_conflict_tree` carry their own
  `@export` tags, written before this change, so roxygen kept them. They are
  shared drawing primitives rather than accidents of the pattern, and dropping
  an export is an API change rather than part of switching the mechanism, so
  they were left alone. Cheap to revisit.
- **The apparent tradeoff was not real.** `NAMESPACE` and `man/` are ordinary
  committed files; `R CMD INSTALL` never needs roxygen2, only regenerating
  them does. The package stays installable on a machine without roxygen.
- **Result:** 36 exports, no `exportPattern`, 37 `.Rd` files (one per export
  plus the package page). `R CMD check` goes from 2 warnings to 1 — the
  missing-documentation warning is gone. What remains is all pre-existing and
  unrelated: non-ASCII dashes in two strings, a stray `.DS_Store`, and the
  undefined-globals note from bare column names in `aes()`.
- **Still missing, and the one real cost of this change: nothing guards
  drift.** Edit a roxygen comment without re-running roxygen and `NAMESPACE`
  and `man/` go quietly stale. The guard — a test that regenerating produces
  no diff — needs testthat and belongs with that work. Until it exists this is
  an unguarded manual step.
- Looked at by Claude: yes. The subagent's report was checked rather than
  taken on trust: the import diff, the 36-export count, which nine names lost
  export, and two chart checks it had not run (`check_forests.R`, which
  exercises the ghost-tree helper, and `check_fragmentation.R`) — both
  0.0000%. Seen by Jeff: no.
