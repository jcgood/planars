# planarsviz_superseded/

The R scripts that drew the nyan1308 charts before the `planarsviz` package
took over. Archived here in cutover step C2 (2026-09-20).

**Do not delete these.** Unlike the rest of `OlderFiles/`, they are still
load-bearing. The porting checks in `scripts/planarsviz_checks/` prove the
package draws what these scripts drew by running each old script in memory
(with `ggsave` disabled, so nothing is written) and comparing the result layer
by layer against the package's chart. Delete a script here and its check stops
being able to prove anything.

**Do not run these either.** They still work, which is precisely the hazard.
The checks are safe because they evaluate a script's text in memory with
`ggsave` disabled; run the same file with `Rscript` and `ggsave` is live, and
it writes its old output over a chart the package produced, under the same
filename, with nothing recording the swap. `.Rprofile` in `NonCollaborative/`
refuses the direct run and names what to use instead;
`PLANARS_RUN_ARCHIVED=1 Rscript <file>` is the deliberate override. So the two
rules here point the same way: these files are read and evaluated by the
checks, and touched by nothing else — not deleted, not edited, not run.

They are archived rather than left in place because the published charts now
come from the package, and a chart script sitting in `results/` next to the
PDFs implies it still makes them. Several of them can no longer be
regenerated either: they were written by Python generators that cutover step
C3 removed.

Every check reaches them through `superseded()` — `superseded.R` for the
checks written in R, `superseded.py` for the ones written in Python, both in
`scripts/planarsviz_checks/` — so this directory's location is recorded in
one place per language.

## One comment in here is now out of date, and must stay that way

`scripts/domain_charts-cgpt.r` says, above two of its paths, that `here()`
resolves from the planars repo root "regardless of where Rscript is invoked
from". That stopped being true on 2026-09-20, when `renv` arrived in
`NonCollaborative/`: `rprojroot` counts an renv project as a project root, and
`here()` walks up only as far as the nearest one, so it now stops at
`NonCollaborative/`. Three scripts in here build a path that way
(`domain_charts-cgpt.r` twice, `nyan1308_forestspans_plot.r` and its
`_no_tono.r` sibling once each for an `output_dir` that nothing writes to,
since the checks disable `ggsave`).

The comment is wrong and is being left wrong on purpose. These scripts are
the evidence the checks compare against; editing one to correct a comment
would mean the thing being compared is no longer quite the thing that drew
the published charts. The checks handle it instead, by naming the file
outright in place of the `here()` lookup — `check_pooled.R` already did this
for its own reasons, and `check_exemplary.R` was given the same substitution
the day renv landed, after the doubled path made it fail.

## What is here

`results/` — 19 generated scripts, written by the R-writing generators that
used to live in `scripts/analysis/laminar_analysis.py`:

- `laminar_conflict_groups.r`, `laminar_four_trees.r`, `laminar_freqtree.r`,
  `laminar_spanchart.r` — charts 12, 13, 14, 15
- `nyan1308_all_families_labeled.r`, `_wordhood.r` — chart 8 and its
  highlight variant (the package names that variant after the highlight id,
  `orthographic_word`, so the `_wordhood` name survives only here)
- `nyan1308_laminar_overlay.r` — chart 7
- `nyan1308_exemplary_trees.r` — chart 10
- `nyan1308_forestspans_plot.r`, `_no_tono.r` — chart 11
- `nyan1308_<id>_laminar_forest.r` ×8 — chart 6, one per class and bundle
- `laminar_forest.r` — an earlier, unlabelled all-families forest that sat in
  `scripts/` rather than `results/`, which is why the C2 sweep missed it.
  Archived in C4. No check compares against it; it is here because the Python
  that wrote it is gone and nothing else records what it drew.

`scripts/` — 6 hand-written scripts:

- `domain_charts-cgpt.r` — the pooled constituency charts (1–4), also
  `source()`d by the exemplary-trees script
- `nyan_boundary_skyline.r` — chart 5
- `analysis/boundary_strength_plot.r` — chart 18
- `analysis/bundle_forest_trees.r` — the 22 individual forest trees, archived
  2026-09-21 when `plot_forest_tree()` absorbed them into the package
- `analysis/fragmentation_test_plot.r` — chart 19 and its two-bundle variant,
  archived 2026-09-21 when `plot_fragmentation_test(groups = )` absorbed the
  second one
- `analysis/span_placement_test_plot.r` — the three span-placement charts,
  archived 2026-09-21 when `plot_span_placement_test()` absorbed all three

## Three of these are evidence in a different way

No check runs `analysis/bundle_forest_trees.r`,
`analysis/fragmentation_test_plot.r` or `analysis/span_placement_test_plot.r`.
They are here because they drew charts whose reference images were frozen
before the package could overwrite them — the 22 forest trees in
`reference/laminar-families/`, and both fragmentation charts and all three
span-placement charts in `reference/counts-and-chance/` — and those references
are what the checks compare the package against. So the chain runs through the
frozen images rather than through a live evaluation of the script.

They are still the only record of how those images were made, and all three
headers still describe writing into `results/` themselves, which the package
does now. Left unedited for the same reason as the out-of-date comment above:
they record what drew the published charts, not what is current.

`fragmentation_test_plot.r` is also the clearest case for the no-running rule.
Until it was archived, it and the package both wrote
`nyan1308_fragmentation_test_plot.pdf` — whichever ran last won, and nothing
anywhere recorded which. That is this project's own core diagnosis in
miniature: one fact in two places with no owner.

## Phase E: the illustrations bundle (2026-09-22)

Three more archived, all under `scripts/` this time rather than `results/`,
since none of them ever wrote a generated script *into* `results/` the way
the C2 batch did -- they wrote finished PDFs (and, for the third, a
generated `.r` file that drew one) straight there themselves:

- `scripts/exploratory/generate_supercatalan_rows.py` and
  `scripts/exploratory/render_supercatalan_rows.r` — wrote
  `supercatalan_trees_n2.pdf` .. `_n5_sample15.pdf` (a Python enumerator
  feeding an R renderer, not a single-language script like everything else
  here). Superseded by `plot_tree_shapes()`, checked against these two at
  0.0000% differing pixels before they were archived — see
  `scripts/planarsviz_checks/check_illustrations.R`'s header comment for why
  that check compares against a frozen reference rather than re-running
  these live. `supercatalan_trees.json`, the intermediate file
  `generate_supercatalan_rows.py` wrote for the R side to read, is archived
  alongside it for the same reason the scripts themselves are: without it,
  `render_supercatalan_rows.r` can no longer be evaluated at all.
- `scripts/analysis/random_tree_overlay.py` — wrote
  `nyan1308_random_tree_overlay.r`, a 2200-line generated R file (one
  hand-templated block per sampled tree), and the PDF it drew. Superseded by
  `plot_random_tree_overlay()`; its sampler (`sample_tree`, `sample_forest`,
  `sample_labeled_tree`, `to_newick`) moved to `catalan.py` first, since that
  logic is still live -- `scripts/analysis/export_planarsviz_illustrations.py`
  calls it directly -- only this script's job of hand-writing a full R file
  from the sample was retired.

`results/illustrations/nyan1308_random_tree_overlay.r` and `.pdf`, and
`supercatalan_trees_n2.pdf` .. `_n5_sample15.pdf`, are deleted rather than
kept: their replacements (`illustrations_tree_shapes_n2.pdf` etc.,
`illustrations_random_tree_overlay.pdf`) have different names, so there was
no existing file for the new ones to land on top of the way most of this
archive's charts did in C1.

## Not here

The older hand-written R in `../../scripts/` (`constituencyforest-all.r` and
its siblings) predates the laminar-family pipeline entirely. It was not
superseded by this port and was left where it was.
