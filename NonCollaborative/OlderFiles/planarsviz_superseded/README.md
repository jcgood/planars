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

`scripts/` — 4 hand-written scripts:

- `domain_charts-cgpt.r` — the pooled constituency charts (1–4), also
  `source()`d by the exemplary-trees script
- `nyan_boundary_skyline.r` — chart 5
- `analysis/boundary_strength_plot.r` — chart 18
- `analysis/bundle_forest_trees.r` — the 22 individual forest trees, archived
  2026-09-21 when `plot_forest_tree()` absorbed them into the package

## One of these is evidence in a different way

No check runs `analysis/bundle_forest_trees.r`. It is here because it drew the
22 charts whose reference images were frozen in
`results/planarsviz/reference/laminar-families/` before the package could
overwrite them, and those references are what the renderer check compares
`plot_forest_tree()` against. So the chain runs through the frozen images
rather than through a live evaluation of the script — but the script is still
the only record of how those images were made, and its header still describes
the flat-`results/` writing the package replaced. Left unedited for the same
reason as the out-of-date comment above: it is a record of what drew the
published charts, not a file to keep current.

## Not here

`results/nyan1308_random_tree_overlay.r` stays in `results/`: it was never
ported, being a random sample rather than a fixed chart, and is scheduled for
the `illustrations` bundle in Phase E.

The older hand-written R in `../../scripts/` (`constituencyforest-all.r` and
its siblings) predates the laminar-family pipeline entirely. It was not
superseded by this port and was left where it was.
