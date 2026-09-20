# planarsviz_superseded/

The R scripts that drew the nyan1308 charts before the `planarsviz` package
took over. Archived here in cutover step C2 (2026-09-20).

**Do not delete these.** Unlike the rest of `OlderFiles/`, they are still
load-bearing. The porting checks in `scripts/planarsviz_checks/` prove the
package draws what these scripts drew by running each old script in memory
(with `ggsave` disabled, so nothing is written) and comparing the result layer
by layer against the package's chart. Delete a script here and its check stops
being able to prove anything.

They are archived rather than left in place because the published charts now
come from the package, and a chart script sitting in `results/` next to the
PDFs implies it still makes them. Several of them can no longer be
regenerated either: they were written by Python generators that cutover step
C3 removes.

Every check reaches them through `superseded()` in
`scripts/planarsviz_checks/superseded.R`, so this directory's location is
recorded in one place.

## What is here

`results/` — 18 generated scripts, written by the R-writing generators in
`scripts/analysis/laminar_analysis.py`:

- `laminar_conflict_groups.r`, `laminar_four_trees.r`, `laminar_freqtree.r`,
  `laminar_spanchart.r` — charts 12, 13, 14, 15
- `nyan1308_all_families_labeled.r`, `_wordhood.r` — chart 8 and its
  highlight variant (the package names that variant after the highlight id,
  `orthographic_word`, so the `_wordhood` name survives only here)
- `nyan1308_laminar_overlay.r` — chart 7
- `nyan1308_exemplary_trees.r` — chart 10
- `nyan1308_forestspans_plot.r`, `_no_tono.r` — chart 11
- `nyan1308_<id>_laminar_forest.r` ×8 — chart 6, one per class and bundle

`scripts/` — 3 hand-written scripts:

- `domain_charts-cgpt.r` — the pooled constituency charts (1–4), also
  `source()`d by the exemplary-trees script
- `nyan_boundary_skyline.r` — chart 5
- `analysis/boundary_strength_plot.r` — chart 18

## Not here

`results/nyan1308_random_tree_overlay.r` stays in `results/`: it was never
ported, being a random sample rather than a fixed chart, and is scheduled for
the `illustrations` bundle in Phase E.

The older hand-written R in `../../scripts/` (`constituencyforest-all.r` and
its siblings) predates the laminar-family pipeline entirely. It was not
superseded by this port and was left where it was.
