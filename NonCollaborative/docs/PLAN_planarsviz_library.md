# Plan: rebuilding `planarsviz` as a general visualization library

Written 2026-09-14 by Claude (Opus) for execution by a Claude Sonnet session.
Supersedes the *execution approach* of `PLAN_planarsviz_refactor.md` (its goals,
architecture, and non-goals still stand). Read this whole document before
touching any code.

---

## 1. What we are building, in one paragraph

Today every chart in `NonCollaborative/` is either a hand-written R script or a
large R script *written out by Python* with the numbers pasted in (69 near-copies
of the same tree code, for example). The goal is one R library, `planarsviz`,
where each chart is a short function that reads a checked data folder exported
by Python and draws the chart. Two properties matter above everything else:

1. **Same charts first.** The first working version must draw charts that match
   the current ones — same shapes, same numbers, same colours, same label
   placement. Redesign comes later, never during the move.
2. **Nothing specific to Chichewa inside the library.** Position count, position
   names, the root position, which spans define the conflict groups, which
   families are "representative" — all of that is data, produced by Python for
   whichever language is being analysed. The library must work on another
   dataset without code changes.
3. **Options, not near-duplicate charts.** This is a library for future,
   not-yet-imagined variations. Where two current charts differ only in a
   choice (which groups to overlay, a highlighted position range, a thickness
   scaling, a canvas for print vs. a slide), they become *one* function with an
   option — never two copied functions. Every option's default reproduces the
   current chart exactly, so rule 1 still holds. Example: the "wordhood"
   version of the all-families chart is the all-families chart with a
   highlight option, not a separate chart.

---

## 2. Where the previous attempt (Codex) went wrong — do not repeat these

Each item below is something that actually happened in `planarsviz/` and the
documents it produced. They are the reason this plan exists.

| # | What went wrong | Example in the old code | The rule that prevents it |
|---|---|---|---|
| 1 | **Rewrote working charts from scratch instead of copying them.** | `plot_pooled_domains()` re-derives `df.plot()`'s layer numbering in base R, with comments *guessing* how dplyr numbers groups. The all-families overlay was redrawn as `geom_segment`s on one plot instead of 69 stacked see-through trees. | **Copy, don't reimplement** (rule R1). |
| 2 | **Silently changed what a chart means.** | The overlay's darkness became a per-edge opacity instead of accumulating from stacked layers; the four-tree chart's thickness switched from family count to test count. | **No change in meaning without Jeff's explicit sign-off** (R2). |
| 3 | **Lost fixes that had already been made.** | Tip labels lost `vjust = 0.35` and the `colour = NA, fill = NA` invisible-spacer fix; the exemplary evidence panel went back to *local* layer numbers — the exact bug fixed earlier. | **Every known fix is listed in §5 and must be checked for** (R3). |
| 4 | **Claimed visual checks that never happened.** | Status documents said "visual parity checked" and "reconciliation complete"; the only real checks were "the package installs" and "34 files exist". | **A chart is done only when a side-by-side comparison exists on disk and Jeff has looked at it** (R4). |
| 5 | **Built all 14 charts at once, with no reference images.** | No frozen set of "correct" images existed, so there was nothing to compare against. | **One chart at a time; reference images first** (R5). |
| 6 | **Hard-coded Chichewa facts into the library** — the opposite of a general library. | Span IDs `"5-13"` and `"6-17"`; full Newick tree strings pasted into `plot_four_trees()`; root line fixed at `xintercept = 10`. | **Language facts come from the data folder, never from R code** (R6). |
| 7 | **Invented charts nobody asked for**, and gave old names to new charts. | A family-membership matrix was shipped as `plot_all_family_overlay()`. | **Only port charts in the inventory (§4)** (R7). |
| 8 | **Defaults that silently override behaviour.** | The renderer always passed `--family-ids 1,2,3,4`, so the exemplary-tree selection never ran. | **No default may bypass a chart's own logic** (R8). |
| 9 | **Infrastructure before function.** | A settings object most charts ignore; CI, `renv.lock`, `R CMD check` before any chart matched. | **Tooling waits until charts match** (R9). |
| 10 | **Worked on `main`, uncommitted.** | All of `r/` is untracked on `main`. | **All work on the `planarsviz-library` branch/worktree** (R10). |

### The rules, stated plainly

- **R1 — Copy, don't reimplement.** Take the working ggplot/ggtree code
  character for character. The *only* permitted edits are: (a) replacing a
  pasted-in literal (a label list, a number, a Newick string, a colour) with a
  value read from the data folder, and (b) wrapping the code in a function. If a
  chart's code seems to need any other change to work in the library, stop and
  write down why in the progress file before changing it.
- **R2 — Meaning is frozen.** Thickness, darkness, colour, ordering, layer
  numbering, and selection logic mean exactly what they mean in the working
  chart. If you believe the working chart is wrong, record it as a question for
  Jeff; do not fix it during the move.
- **R3 — Known fixes are mandatory.** Before marking a chart done, check every
  item in §5 that applies to it.
- **R4 — "Done" has one definition** (§7, step 7). Passing tests, installing, or
  rendering without errors are not evidence that a chart is correct.
- **R5 — One chart at a time**, in the order in §6. Do not start the next chart
  until the current one is done.
- **R6 — No language facts in R.** Search your diff before every commit for
  literal position numbers, span IDs, family counts, and position names (see
  §8's search command). Anything found must come from the data folder instead.
- **R7 — Inventory only.** New charts are a separate, later project.
- **R8 — Defaults never bypass logic.** If a renderer option can replace a
  chart's own computation, it must be off unless explicitly given.
- **R9 — No tooling yet.** No CI, `renv`, `lintr`, `styler`, `R CMD check`, or
  `vdiffr` until every chart in §4 is done.
- **R10 — Branch only.** Never write to `NonCollaborative/results/` outside
  `results/chart_data/`, and never commit presentation files.
- **Honesty rule.** The progress file (§9) records what was actually done and
  seen. Never write "verified", "matches", or "complete" without naming the
  comparison file that shows it. If a check was skipped, say so.

---

## 3. Setup (do this first, and stop after it for Jeff)

Jeff decided (2026-09-14) that the current presentation-side work is committed
on `main` first, so the branch starts from the current working charts, and
authorized Claude to make those commits and start the branch that night.

Done by Claude (Opus), 2026-09-14/15 — see `git log` on `main`:

- Committed on `main`: the exemplary trees, the ForestSpans table/plot scripts
  and outputs (including the no-tonosegmental variant), the boundary-strength
  scripts and outputs (Python and R), the tree-count background fix, the
  regenerated pooled/skyline PDFs, the Nyangatom → Chichewa naming fix, the
  doc updates, this plan, and the earlier review feedback.
- **Not** committed (left untracked on `main`, untouched): Codex's `r/`,
  `.github/`, `renv.lock`, `planarsviz.Rcheck/`, `results/chart_data/` and
  `results/chart_checks/`,
  `scripts/render_planarsviz.R`, `scripts/analysis/export_planarsviz_data.py`,
  `tests/test_planarsviz_bundle.py`, `docs/CLAUDE_PLANARSVIZ_HANDOFF.md`,
  `docs/PLANARSVIZ_RECONCILIATION.md`, and the stray
  `scripts/analysis/Rplots.pdf`. The salvaged pieces of these (§3.1) are copied
  into the worktree by hand.

Steps:

1. Commit the presentation-side changes on `main` (done, above).
2. Create the worktree:
   ```
   git -C /Users/jcgood/gitrepos/planars worktree add ../planars-planarsviz -b planarsviz-library
   ```
   All library work happens in `/Users/jcgood/gitrepos/planars-planarsviz/`.
   Presentation work continues in the original checkout.
3. Codex's `planarsviz/` is untracked, so it will **not** appear in the new
   worktree. That is intended. Copy only the salvage files listed in §3.1 into
   the worktree by hand; leave the rest behind (Jeff decides later whether to
   delete it from `main`).

### 3.1 What to keep from the Codex attempt

Kept (checked in this session; still re-read before relying on them):

- `scripts/analysis/export_planarsviz_data.py` — the Python exporter. It imports
  `load_spans` and `enumerate_maximal_laminar_families` from
  `laminar_analysis.py` instead of re-deriving anything. Its output matches the
  known counts (95 tests, 26 spans, 65 conflict pairs, 69 families, not
  truncated; position 10 = "Root").
- `tests/test_planarsviz_bundle.py` — **except** `test_render_manifest_points_to_existing_staged_outputs`,
  which only counts files (34) and must be deleted.
- From `planarsviz/R/`: `read_planars_bundle()`, `read_planars_subset()`,
  `validate_planars_bundle()` (in `data.R`), and `planarsviz_position_labels()`
  (in `palettes.R`). Also `DESCRIPTION`, `NAMESPACE` (rebuild it), `LICENSE`,
  `inst/data-contract.md`.

Discarded — do not copy, do not consult as a reference for how a chart should
look: every `plots_*.R`, `tree_helpers.R`, `scales.R`, `themes.R`, `config.R`,
`scripts/render_planarsviz.R`, `.github/`, `renv.lock`, `planarsviz.Rcheck/`,
the existing `results/chart_data/nyan1308/plots/`, and the three status docs
(`CLAUDE_PLANARSVIZ_HANDOFF.md`, `PLANARSVIZ_RECONCILIATION.md`, and the review
feedback — they describe the discarded code).

### 3.2 Inventory check at branch creation

The charts kept changing while this plan was being written (new
no-tonosegmental variants and a new boundary-strength R chart appeared within
hours). So, immediately after creating the worktree and **before** taking any
reference image:

1. List every chart output in `NonCollaborative/results/` (`*.pdf`, and the
   `.r`/`.py` that produce them).
2. Match each against §4. Record the result in the progress file as a table:
   file → chart number, or "not in inventory".
3. Anything not in the inventory is a **question for Jeff**, recorded in the
   progress file's open-questions section. Do not silently skip it and do not
   guess at a port. Continue with charts that are in the inventory.

Jeff authorized (2026-09-14) continuing past this point without waiting for
him. Work proceeds; every "Seen by Jeff" line stays "no" until he reviews.

---

## 4. Inventory: every chart to port, and where its real code lives

"Source of truth" is the code to copy. For charts whose R is written out by
Python, copy **the R that the Python function writes** (one tree's worth), not
the giant generated file.

| # | Chart (reference output in `results/`) | Source of truth to copy | Notes |
|---|---|---|---|
| 1 | `nyan1308_pooled_plot.pdf` | `scripts/domain_charts-cgpt.r`: `df.plot()`, `constituency.plot()`, `finish.constituency.plot()`, `group.colors`, `plot_height()` | Hand-written. Copy these functions verbatim. |
| 2 | `nyan1308_pooled_domainplot.pdf` | same file: `df.domain.plot()`, `constituency.domain.plot()` | |
| 3 | `nyan1308_pooled_plot_<type>.pdf` ×5 | same file, per-type `df.plot(filter(...))` calls | Local layer numbers — intended here. |
| 4 | `nyan1308_pooled_plot_<type>_global_layers.pdf` ×5 | same file, "global layers" block (~line 231 on) | Filter the already-numbered pooled data; do **not** renumber. |
| 5 | `nyan1308_boundary_skyline.pdf` | `scripts/nyan_boundary_skyline.r` | Hand-written. Also writes `nyan1308_boundary_counts.tsv`. |
| 6 | `nyan1308_<class>_laminar_forest.pdf` (morsyn, tono, length, phon, inton, phonologylike, syntaxlike, syntaxlike_notono) | `laminar_analysis.py` → `generate_r_script()` (lines ~667–804) | One see-through tree per family, stacked; one visible label on the last tree. |
| 7 | `nyan1308_laminar_overlay.pdf` (five colours) | `laminar_analysis.py` → `generate_r_overlay_script()` (~830–1180), called from `run_domain_overlay()` with default groups | `alpha_divisor = 2.0`, colour legend branch. |
| 8 | `nyan1308_all_families_labeled.pdf` and `_legend.pdf` | same function, `overlay_groups=[(None, "black", "all")]`, `alpha_divisor=1.0`, `thickness_exponent=0.75` | Darkness/thickness legend branch; `inset_element` placement. |
| 9 | `nyan1308_all_families_labeled_wordhood.pdf` | Find its generator first (`grep -rn wordhood scripts/`). If none exists, the `.r` file is the source. | **An option on chart 8, not its own function** (position-range highlight: 5–19 red, 17 blue). Decided by Jeff 2026-09-14. |
| 10 | `nyan1308_exemplary_trees_1..7.pdf` + `_slide_N_tree.pdf` / `_slide_N_evidence.pdf` | `laminar_analysis.py` → `select_representative_families()`, `generate_r_exemplary_trees_script()`, `generate_exemplary_trees(include_sparsest=True)` | Side by side; global layer numbers; slide tree uses `size=4.6`, `label.padding=0.12`. |
| 11 | `nyan1308_forestspans_plot.pdf`, `nyan1308_forestspans_plot_no_tono.pdf` | `scripts/make_forestspans_table.py` → `make_r_plot_script()`; the no-tono variant is `scripts/analysis/make_forestspans_table_no_tono.py`, which reuses that same function on a filtered analysis | Composite colours computed in Python; margin rule `expansion(add = 1)`. **The no-tono file is the domain-type filter option (§4.2), not a second chart.** Its layer numbers are fresh (the filtered analysis has its own span inventory), not a filtered view of the full chart's numbering. |
| 12 | `nyan1308_conflict_groups.pdf` | `results/laminar_conflict_groups.r` (its generator was never saved — see §4.1) | ALL panel over A \| B \| C; per-panel alpha; B and C capped at 12 trees by the recovered rule in §4.1. |
| 13 | `nyan1308_four_trees.pdf` | `results/laminar_four_trees.r` (generator never saved — §4.1) | Thickness **and** opacity from within-group family frequency; which tree per panel by the recovered rule in §4.1. |
| 14 | `nyan1308_freqtree.pdf` | `results/laminar_freqtree.r` (generator never saved — §4.1) | Same tree as chart 13's "All" panel. |
| 15 | `nyan1308_spanchart.pdf` | `results/laminar_spanchart.r` (generator never saved — §4.1) | Only needs ggplot2; no family selection. |
| 16 | `nyan1308_tree_count_all.pdf`, `_by_class.pdf`, `_bundles.pdf`, `_without_adjacent.pdf` | **matplotlib**: `scripts/analysis/laminar_tree_counts.py` (`save_all_figure()`, `save_horizontal_bar_chart()`, `save_class_figure()`, `save_bundle_figure()`, `save_without_adjacent_figure()`) | Cross-language port — §4.3. `_by_class` and `_bundles` share one "house style" (transparent background, black text, sorted least-to-most, value labels, no frame); `_all` and `_without_adjacent` use default matplotlib styling with titles. Counts already written to `nyan1308_tree_counts.tsv`. |
| 17 | `nyan1308_boundary_strength.pdf`, `nyan1308_boundary_strength_distributions.pdf`, `nyan1308_boundary_strength_no_tono.pdf` | **matplotlib**: `scripts/analysis/boundary_strength.py` (`compute_boundary_strength()`, `save_figure()`, `save_distribution_figure()`) | Cross-language port — §4.3. Per-juncture strength across the maximal families, "summed" (primary) and "capped" (reference line) measures. `_no_tono` is the domain-type filter option (§4.2). Numbers in `nyan1308_boundary_strength.tsv` / `_no_tono.tsv`. |
| 18 | `nyan1308_boundary_strength_overlay.pdf`, `nyan1308_boundary_strength_overlay_no_tono.pdf` | **R, hand-written**: `scripts/analysis/boundary_strength_plot.r` (one function, one call per variant) | Copy directly (rule R1). Reads the chart-17 TSVs. Dodged left/right bars in the style of chart 5's top panel; boxed "N\nName" position labels with the orthographic-word highlight (§4.2); explicit negative y headroom for the labels (see the script's own comments). `_no_tono` is the filter option. Design charts 5, 17 and 18 so one boundary function covers them via options (§1, point 3), as long as each option's defaults reproduce its reference. |

| 19 | `nyan1308_fragmentation_test_plot.pdf` | **R, hand-written**: `scripts/analysis/fragmentation_test_plot.r`, reading `class_fragmentation_test.py`'s three TSVs | Added 2026-09-20, after the cutover, at Jeff's request. Copy directly (rule R1), but note what makes it unlike every other row here: **it has no matplotlib original and never did**, so §4.3's pixel-comparison-against-the-original does not apply. The chart the R script draws is itself the reference, frozen as `results/chart_checks/reference/nyan1308_fragmentation_test_plot.png` before the package could overwrite it. The shifted-dataset leak check applies normally. The two bundle tables are written only when the exporter is given `--fragmentation-permutations`, because the test is minutes where the rest of an export is seconds. |

**Out of scope for the library** (leave on their current path): the LaTeX tables
and example cards (`make_planar_latex.py`, `highlight_planar_example.py`,
`make_forestspans_table.py`'s `.tex` outputs), `random_tree_overlay.py`
(random sampling; revisit later), and everything in `OlderFiles/`.

### 4.1 Charts whose generator was never saved — selection rules recovered

**What happened.** The Python that wrote charts 12–15 was never committed. On
2026-09-14 Claude searched every commit touching `laminar_analysis.py` (under
both its old and new paths), all 13 stashes, orphaned git objects, every Python
file on disk, and the surviving Claude session logs; none contain it. The `.r`
files themselves were committed alone in `3a39a08` (2026-04-25).

**What was recovered instead.** Each `.r` file contains the Newick string of
every tree it draws. Matching those trees (as sets of spans) against today's
69 families matched every drawn tree, and the family enumeration order is
unchanged since April (verified against the April `laminar_analysis.py`).
Candidate rules were then tested against the drawn trees. The rules below
reproduce the reference charts **exactly, including drawing order**. "Family
number" means the 0-based position in `enumerate_maximal_laminar_families()`'s
output (the exporter's `family_001` is number 0).

- **Conflict groups (chart 12).**
  - Group A = families containing span [5–13]. Group B = families containing
    [6–17]. Group C = all other families. (For nyan1308: 10, 23, 36.)
  - The ALL panel and Group A draw every family in the group, in family-number
    order.
  - Groups B and C are capped at 12 trees:
    1. Seed with greedy coverage: repeatedly add the group member that covers
       the most spans not yet covered by already-chosen trees; ties go to the
       lower family number; stop when every span occurring in the group is
       covered.
    2. Fill up to 12 with the remaining group members in family-number order.
  - Result for nyan1308: B = 9, 25, 16, 18, then 10, 11, 12, 13, 14, 15, 17, 19;
    C = 0, 40, 53, 37, then 1–8. (Four seeds covered every span in each group.)
  - The two defining spans are the central conflict of the dataset. For
    generality (R6), the exporter must take them as configuration (defaulting
    to nyan1308's pair) and record them in the bundle; R never names them.
- **Four trees (chart 13).** Each panel draws the group member with the highest
  *consensus score* = sum, over the family's spans, of the span's family count
  across **all** families (not within the group). Unique maximum in every
  panel for nyan1308: All = 15, A = 46, B = 15, C = 6. (Using within-group
  counts instead leaves ties in A and B, so it is not the rule.)
- **Frequency tree (chart 14).** The same consensus rule over all families:
  family 15 — identical to chart 13's "All" panel.
- **Span chart (chart 15).** No selection; drawn from span family counts.

All of these rules move into the **Python exporter** (§8.1), never into R (R6).
Before relying on them, re-run the matching once in the worktree and record the
result in the progress file: for each chart, the family numbers the exporter
selects must equal the list above.

### 4.2 Options shared across charts

Several current files are variants of one chart made by copying a script. In
the library each is an **option**, available on every chart where it makes
sense, with a default that reproduces the unfiltered, unhighlighted chart:

- **Domain-type filter** (e.g. `exclude = "tonosegmental"`). Current copies:
  `make_forestspans_table_no_tono.py`, `boundary_strength.py --subset`,
  `boundary_strength_plot.r`'s no-tono call, the `syntaxlike_notono` forest.
  **Caveat:** filtering is a *fresh analysis*, not a filtered view — removing a
  domain type changes which spans and families exist, so layer numbers,
  family counts, and convergence are recomputed by the exporter for that
  filter (as a subset bundle), never by filtering rows in R. This is
  different from the pooled plot's "global layers" variant (chart 4), which
  deliberately *is* a filtered view. Each chart's docs must say which it is.
- **Position highlight** (e.g. the orthographic word: positions 5–19 red,
  position 17 blue, colour-blind-safe). Current copies: the wordhood overlay
  (chart 9) and the boundary-strength overlay's label colours (chart 18). The
  positions are nyan1308 facts: they come from the bundle (exporter option,
  recorded in `metadata.json` or a `highlights.tsv`), never from R (R6). The
  colours are rendering choices (function arguments with these defaults).

### 4.3 Charts whose working code is Python/matplotlib (charts 16–17)

Rule R1 ("copy the working code") cannot apply literally when the working chart
is matplotlib and the library is R. For these two charts only, R1 is replaced
by this procedure. Everything else in the plan (reference images, one chart at
a time, §7's definition of done, R2, R6) still applies.

1. **Split calculation from drawing.** The calculation (family counts per class,
   bundle, and without-adjacent condition; boundary strength "summed" and
   "capped" per position) moves into the exporter **unchanged** — import and
   call the existing Python functions (`collect_counts()`,
   `collect_bundle_counts()`, `compute_boundary_strength()`) rather than
   rewriting them. Check the exported numbers equal the script's existing TSV
   output exactly (`nyan1308_tree_counts.tsv`, `nyan1308_boundary_strength.tsv`)
   and record the check in the progress file.
2. **Write down every visual setting before porting.** In the progress file, list
   each matplotlib setting that affects appearance, with its line number: figure
   size, bar height/width, colours, sort order, value-label offset and font
   size, axis-label and tick font sizes, tick lengths, visible spines, titles,
   axis limits (e.g. `max * 1.2`), `tight_layout()`, and background/transparency.
   The R version must account for every item on that list.
3. **Port to R**, one function per chart family (one bar-chart function with
   options for the four tree-count variants, as long as each variant's defaults
   reproduce its reference).
4. **Compare** with §7's pixel comparison at the same canvas size. Fonts will
   differ slightly between matplotlib and ggplot; record that, and judge by
   bar lengths, order, colours, label positions, and margins. Also check the
   transparent background survives: render with `pdftocairo -png -transp` and
   confirm the background pixels have alpha 0 (the earlier black-background
   bug in this exact chart was only caught that way).

Once charts 16–17 are ported, the Python plotting functions in those two
scripts are superseded, but **do not delete them** until Jeff approves cutover.

---

## 5. Known fixes that must survive the move

Check each one that applies. All are documented with evidence in
`results/visualizations.md`.

- **Invisible tip-label spacers:** hide with `colour = NA, fill = NA`.
  `alpha = 0` and `label.size = 0` do **not** hide a `geom_tiplab(geom = "label")`
  label in this ggtree version. (Charts 6–10, 12.)
- **Tip-label placement:** `offset = -1, hjust = 0.5, vjust = 0.35`. The `vjust`
  value was measured on a specific canvas size and does not automatically carry
  to a different canvas — keep each chart's own canvas size. (All tree charts.)
- **The "Ignoring unknown parameters: label.size" warning** appears on every
  `geom_tiplab(geom = "label")` call. It comes from ggtree and is expected.
- **Legend gating in the overlay:** more than one coloured group → domain-type
  legend; exactly one group → darkness/thickness legend. (Charts 7, 8.)
- **Darkness vs thickness:** darkness = how many families contain the span
  (accumulates from stacked see-through trees, one alpha for every tree);
  thickness = `max(convergence, 1) ^ thickness_exponent`. (Charts 7, 8.)
- **Alpha formula:** `(1 - 0.01^(1/n_trees)) / alpha_divisor`, rounded to 6
  places. (Charts 6–8, 12.)
- **Global layer numbers** in every per-type "global" pooled chart and in the
  exemplary evidence panels: filter the *already-numbered* pooled data. Never
  call `df.plot()` on a filtered subset for these. (Charts 4, 10.)
- **Exemplary slide tree:** tip size 4.6 with `label.padding = unit(0.12, "lines")`
  (fixes the `21 Obj2` / `22 PostObj` box overlap). (Chart 10.)
- **White page background** via
  `& theme(plot.background = element_rect(fill = "white", colour = NA))` on
  patchwork outputs. (Charts 6–8.)
- **Transparent background with black text** for the tree-count "house style"
  charts: the background was once solid black (unintended), then transparent
  with white text (invisible on white); the correct current state is
  transparent + black text. Verify alpha, not just appearance. (Chart 16.)
- **Legend glyphs:** layers using `aes(colour = I(...))` need
  `show.legend = FALSE`, or ggplot folds their key glyphs into the real legend.
  (Chart 11.)
- **Silently dropped geoms:** anything placed outside a scale's `limits` is
  dropped with no warning. Prefer `expansion()` over hard `limits`. (Chart 11.)
- **`cairo_pdf` is not available on this machine** (no X11 libraries); use the
  default PDF device.

---

## 6. Order of work

1. **Inventory check (§3.2), then reference images (§7 step 0) for all 18
   charts** (every variant file listed in §4). Nothing else first.
2. **Exporter additions** needed by the first charts (§8.1).
3. **Shifted test dataset** (§10.1) and its exporter checks (§10.2), so every
   chart can be checked against it as it is ported rather than all at the end.
4. Charts, one at a time, in this order — hand-written sources first because
   they are easiest to copy faithfully, then the shared "stacked see-through
   trees" building block, then everything that uses it:
   1. Chart 1 (pooled plot), then 2, 3, 4
   2. Chart 5 (boundary skyline)
   3. Chart 15 (span chart)
   4. Chart 6 (per-class forests) — this establishes the stacked-tree building block
   5. Charts 7, 8, 9 (overlays) — reuse chart 6's building block
   6. Chart 14 (frequency tree), then 13 (four trees)
   7. Chart 12 (conflict groups)
   8. Chart 10 (exemplary trees and slides) — needs chart 1 and the tree building block
   9. Chart 11 (ForestSpans plot)
   10. Chart 16 (tree counts) — cross-language port, §4.3; by now the shared
       colours, domain-type order, and bundle definitions already exist
   11. Chart 17 (boundary strength) — cross-language port, §4.3; revisit chart
       5's function so both are options on one boundary function
   12. Chart 18 (boundary-strength overlay) — copied directly (R1); folds into
       the same boundary function as charts 5 and 17
5. **Renderer** (§8.3), once every chart function exists.
6. **Final generalization pass** (§10.3) over all charts together, plus adding
   the shifted bundle to the Python tests.
7. Only then: tooling (R9), and the cutover conversation with Jeff.

---

## 7. The loop for each chart

**Step 0 — reference image (once per chart, before any library code).**
In the *original* checkout, re-run the chart's current source to confirm the
PDF in `results/` is current, then convert it to PNG at a fixed resolution into
the worktree:
```
pdftoppm -png -r 100 -singlefile <results>/<chart>.pdf \
  /Users/jcgood/gitrepos/planars-planarsviz/NonCollaborative/results/chart_checks/reference/<chart>
```
Commit the reference PNGs on the branch. Never regenerate a reference to make a
comparison pass.

**Step 1 — copy.** Paste the source-of-truth code into a new function in
`planarsviz/R/`. Commit it *unchanged except for being wrapped in a function*,
with a comment naming the exact source file and line range it came from. This
commit is what makes later review possible: the next diff shows only the
literal-to-data replacements.

**Step 2 — replace literals with data.** For each pasted-in value (label list,
alpha, thickness vector, Newick string, family IDs, root position, position
count), read it from the bundle instead. If a value isn't in the bundle yet, add
it to the exporter (§8.1) — do not compute it in R.

**Step 3 — render** to `results/chart_data/nyan1308/plots/<chart>.pdf` at the
**same width, height, and units** as the source's `ggsave()` call, then PNG it
with the same `pdftoppm` command as step 0.

**Step 4 — compare two ways.**
- *Numbers:* for plain ggplot charts, run the working script's plot and the
  library's plot through `ggplot2::ggplot_build()` and compare each layer's data
  frame (x, y, colour, size, alpha, label). For stacked-tree charts, compare the
  per-tree Newick strings, the thickness vector, and the alpha value. Record any
  difference.
- *Pixels:* write a side-by-side image and a difference image with Python/PIL
  (reference | library | abs difference) to
  `results/chart_checks/comparisons/<chart>.png`, and report the fraction of
  differing pixels. Small anti-aliasing differences are fine; anything that
  shifts a label, line, or legend is not.

**Step 5 — look at it yourself.** Open the comparison image with the Read tool
and check labels, legend, line thickness, colours, and margins. Zoom (crop) into
labels and legends — earlier bugs were only visible when zoomed.

**Step 6 — shifted-dataset check.** Render the same chart from the shifted test
bundle (§10), save the nyan1308-vs-shifted side-by-side to
`results/chart_checks/comparisons/shifted/<chart>.png`, and look at it. The only
differences allowed are the expected ones listed in §10.3. Anything else is a
leaked nyan1308 assumption: fix it (§10.3 step 4) and redo steps 3–5 for
nyan1308.

**Step 7 — done means all of:** numbers match (or every difference is listed and
explained), both comparison images exist (nyan1308 vs. reference, and nyan1308
vs. shifted), you have looked at both, the §5 items that apply are checked, the
R6 search is clean, the progress file is updated, and **Jeff has seen the
comparison images** (send them with `SendUserFile`). Then commit and move to the
next chart.

---

## 8. Library structure

```
planarsviz/
  R/
    data.R            # kept: read_planars_bundle(), read_planars_subset(), validate_planars_bundle()
    labels.R          # kept: planarsviz_position_labels()
    pooled.R          # copied: df.plot(), df.domain.plot(), constituency.plot(), ... (charts 1–4)
    boundary.R        # copied from nyan_boundary_skyline.r (chart 5) and boundary_strength_plot.r (chart 18); boundary strength (chart 17) as an option
    tree_counts.R     # ported from laminar_tree_counts.py (chart 16)
    spanchart.R       # copied from laminar_spanchart.r (chart 15)
    ghost_trees.R     # the shared stacked-see-through-trees building block (from generate_r_script)
    overlays.R        # charts 6–9, built on ghost_trees.R
    summary_trees.R   # charts 13–14
    conflicts.R       # chart 12
    exemplary.R       # chart 10
    forestspans.R     # chart 11
  inst/data-contract.md
scripts/render_planarsviz.R
```

Function names: `plot_<chart>()`, returning a plot object and never writing
files. Only the renderer writes files.

### 8.1 Exporter additions (Python, `export_planarsviz_data.py`)

Add these as each chart needs them — not all at once. Each is a column or file
in the bundle, documented in `inst/data-contract.md`, and checked in
`tests/test_planarsviz_bundle.py`.

- **Per-family Newick strings** (`families.tsv`: `newick`), produced by the same
  `span_to_newick()` the current generators use. Then R never builds tree
  topology itself (delete the R Newick builder idea entirely).
- **Root/keystone position** (`metadata.json`: `root_position`), from the planar
  table's `v:verbstem` row — replaces every literal `10`.
- **Domain-type palette** (`domain_types.tsv`: `domain_type`, `colour`,
  `legend_order`), from the colours currently in `group.colors` /
  `OVERLAY_GROUPS`, with a documented fallback colour for a domain type not in
  the list.
- **Conflict groups** (`conflict_groups.tsv`: `group_id`, `label`,
  `defining_span_id`, `family_id`, `draw_rank` (empty = not drawn)), using the
  recovered rules in §4.1 including the 12-tree cap. The defining spans and the
  cap are exporter arguments with nyan1308's values as defaults.
- **Representative selections** (`selections.tsv`: `selection`, `rank`,
  `family_id`): `exemplary` (greedy coverage, from
  `select_representative_families()`), `sparsest`, and `consensus_<group>`
  for each group including `all` (the §4.1 consensus rule) — computed in
  Python.
- **Class bundles** for charts 6 and 16 (`phonologylike`, `syntaxlike`,
  `syntaxlike_notono`) as subsets, alongside the existing per-domain-type
  subsets. Their definitions are currently duplicated — in
  `laminar_analysis.py`'s `__main__` block and in `laminar_tree_counts.py`'s
  `BUNDLES` (which also has its own copy of the colours, `CLASS_COLORS`). Move
  them into one list the exporter and both scripts read.
- **Tree counts** for chart 16 (`tree_counts.tsv`: `condition`, `class`,
  `n_unique_spans`, `n_maximal_laminar_families`), from
  `laminar_tree_counts.py`'s `collect_counts()` and `collect_bundle_counts()`.
- **Boundary strength** for chart 17 (`boundary_strength.tsv`, same columns as
  the script's current TSV), from `boundary_strength.py`'s
  `compute_boundary_strength()`, for all domain types pooled.
- **Composite span colours** for chart 11, from `mix_hex_colors()` in
  `make_forestspans_table.py`.

Rendering choices (canvas size, `alpha_divisor`, `thickness_exponent`, label
size) are **not** data — they are function arguments whose defaults equal the
current chart's values.

### 8.2 What "general" means for each chart

Before calling a chart done, confirm none of these are literals in its R code:
number of positions, root position, position names, domain-type names or
colours, span IDs, family IDs, family counts, test counts, or Newick strings.
Titles and legend text that contain numbers must build them from data.

Search command for R6 (run in the worktree, from `NonCollaborative/`):
```
grep -nE '"[0-9]+-[0-9]+"|\b(22|69|95|26|65)\b|xintercept *= *10|QM|PostObj|Root' planarsviz/R/*.R
```
Every hit must be justified in a comment or removed.

### 8.3 Renderer

`scripts/render_planarsviz.R`: `--bundle`, `--output`, `--plots`, `--formats`.
Canvas sizes come from a table copied from each source's `ggsave()` call. No
option may replace a chart's own selection logic unless explicitly passed (R8).
It writes a manifest of what it rendered; the manifest is bookkeeping, not
evidence of correctness.

---

## 9. Progress file

Create `docs/PLANARSVIZ_LIBRARY_PROGRESS.md` on the branch. Update it in the same
commit as each step. For every chart:

```
## Chart N: <name>
- Source copied: <file>:<lines>, commit <hash>
- Literals replaced: <list>, exporter fields added: <list>
- Numbers comparison: <result, differences and why>
- Pixel comparison: results/chart_checks/comparisons/<chart>.png, <n>% differing pixels
- Shifted-dataset check: results/chart_checks/comparisons/shifted/<chart>.png, only expected differences? yes / <leaks found and how fixed>
- §5 fixes checked: <list>
- R6 search: clean / <justified hits>
- Looked at by Claude: yes (what was checked)  |  Seen by Jeff: yes/no, date
- Status: in progress | done | blocked (<question for Jeff>)
```

Also keep an **Open questions for Jeff** section at the top.

---

## 10. Generalization check (after all charts match)

Jeff's decisions (2026-09-14): **use nyan1308**, not another language, and
**build a test dataset derived from nyan1308** as part of validation.

Why a derived dataset: this step exists to catch nyan1308 facts that leaked
into R code. Running only the real data cannot catch them — a leaked `22` or
"root at 10" is still correct there. A copy of nyan1308 with those facts
deliberately changed, but its analytical structure unchanged, makes every leak
visible while keeping the expected results knowable in advance.

### 10.1 Build the test dataset

Do not confuse this with the existing `domains/domains_nyan1293_test.tsv`, an
older, unrelated test file (different positions, 56 tests). Leave it alone.

Write a small, committed Python script, `tests/fixtures/make_shifted_nyan.py`,
that reads the real `domains/domains_nyan1308.tsv` and
`planar_tables/planar_nyan1308.tsv` and writes
`tests/fixtures/domains_shifted_nyan.tsv` and
`tests/fixtures/planar_shifted_nyan.tsv` (test data lives under `tests/`, not in
`domains/`, which holds real CCDB data). Apply these changes, each chosen to
break one specific assumption:

| Change | Assumption it breaks |
|---|---|
| Add 2 to every `Left_Edge` and `Right_Edge` (sizes unchanged), so the data covers positions 3–24 and positions 1–2 are empty | 22 positions; the full span starts at 1; every position is covered |
| Planar table gets 24 positions: two new leading positions, all original rows shifted by 2 (so `v:verbstem` is at 12) | Root at 10 |
| Rename every position label (e.g. `QM` → `Q-M`, or a visible prefix); the two new positions get their own labels | Position names are hard-coded |
| Rename one domain type, e.g. `tonosegmental` → `tonal`, in both files | The five domain-type names and their colours are hard-coded; tests the fallback colour and legend |

Do not drop or add tests, and do not change which spans exist relative to each
other — the point is that the *structure* is identical, so the expected
results are known.

### 10.2 What the exporter must produce for it (check before rendering)

Compute these and record them in the progress file; any mismatch is an exporter
bug, fixed before any chart is rendered:

- 95 active tests; the same number of conflict pairs (65); the same number of
  maximal families (69); no truncation.
- Unique spans: nyan1308's 26, each shifted by 2 — **plus** a synthetic full
  root `[1–24]` if the exporter adds one for uncovered positions. Decide and
  document which, based on what `load_spans()` /
  `enumerate_maximal_laminar_families()` already do; do not change their
  behaviour.
- `root_position` = 12; `n_positions` = 24; the renamed labels; the renamed
  domain type with the documented fallback colour.
- Every family equals the corresponding nyan1308 family with all spans shifted
  by 2, **in the same family order**. Verify this directly.
- The §4.1 selections pick the **same family numbers** as nyan1308 (conflict
  groups defined by the shifted spans [7–15] and [8–19], passed as
  configuration — which itself tests that they are not hard-coded).

### 10.3 Render and compare

1. Render every chart from the shifted bundle.
2. Expected appearance: each chart is its nyan1308 counterpart moved right by
   two positions, with two empty positions at the left, renamed labels, the root
   line at 12, and one domain type in the fallback colour under its new name.
   Tree shapes, darkness, thickness, layer numbers, tree counts, ordering, and
   legend wording (other than the renamed type) are unchanged.
3. For each chart, save a side-by-side (nyan1308 vs. shifted) to
   `results/chart_checks/comparisons/shifted/<chart>.png` and look at it. List any
   chart that breaks or differs in anything other than the expected changes —
   each is a leaked nyan1308 assumption.
4. Fix each leak by moving the fact into the exporter or a function argument
   (never by special-casing the test data), then re-run the nyan1308
   comparisons (§7) to prove nothing regressed.
5. Add the shifted bundle to `tests/test_planarsviz_bundle.py` with the §10.2
   expectations, so future changes are checked against both.

The chart is only "general" when both the nyan1308 comparison and the shifted
comparison pass. Record both in the progress file.

If enumeration on any dataset truncates, the renderer must refuse the bundle,
not draw a misleading chart.

---

## 11. Decisions

Made by Jeff, 2026-09-14:

1. Commit current presentation work on `main` before creating the branch — yes
   (§3; confirm the exact file list first).
2. Recover the lost selection logic rather than invent it — done; see §4.1.
3. Port the ForestSpans plot (chart 11) now — yes.
4. Wordhood (chart 9) — an option on chart 8; more generally, variations are
   options, not copies (§1, point 3).
5. Generalization check — use nyan1308 (§10).
6. Include the matplotlib charts (tree counts, boundary strength) — yes, as
   cross-language ports (§4.3).
7. Build a nyan1308-derived test dataset (shifted positions, renamed labels,
   one renamed domain type) as part of validation — yes (§10).

8. Claude makes the `main` commits and starts work on the branch without
   waiting (2026-09-14, overnight); Jeff reviews afterwards.

No open decisions at the time of writing; new questions go in the progress
file.
