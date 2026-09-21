# Note for the planarsviz-cutover session

From the analysis session, 2026-09-20 (later the same day as the
fragmentation-test port request). Another port request, smaller than that
one — Jeff asked for it after noticing a script I'd written was writing
straight to flat `results/`, bypassing the package and the manifest
entirely, the same way the fragmentation test's original R script did
before it was ported.

## What exists right now (uncommitted, works, NOT in the package/manifest)

`scripts/analysis/bundle_forest_trees.r` — draws every INDIVIDUAL maximal
family tree in a named forest, one PDF per tree, as opposed to:
- the ghost-overlay charts (`phonologylike_laminar_forest.pdf` etc.), which
  stack every tree in one semi-transparent image, or
- the exemplary-tree charts, which show a curated 7-family subset of the
  *pooled* analysis only.

It reads `results/planarsviz/nyan1308/data/forests/<name>.tsv` (already
exported — `tree_number`, `newick`, plus `group_spans`/`strengths` it
doesn't use) directly, so it complies with "Python computes, R only draws
from the bundle." What it doesn't comply with: it writes straight to flat
`results/` with no `--plots` name and no manifest row, so nothing records
that these files exist or how they were made. Current output: 22 files —
`nyan1308_phonologylike_tree_01.pdf`..`_06.pdf`,
`nyan1308_syntaxlike_tree_01.pdf`..`_16.pdf`.

Its drawing logic is not new — it's copied verbatim from
`planarsviz_exemplary_tree()` in `r/planarsviz/R/exemplary.R` (same layout,
same boxed "N\nName" tip labels, same margins), just keyed by
`(forest_name, tree_number)` reading `forests/<name>.tsv` instead of by
`family_id` reading `bundle$families`. I didn't generalize that function or
touch `r/planarsviz/R/` myself — that's your package to edit, and I didn't
want to risk the kind of collision the handoff notes exist to prevent.

## The request

Port this into the package properly, the way `exemplary_trees_<rank>` and
its slide variants already handle "one chart name per item in a list" —
this is the same shape of problem, not a new one. Concretely, in
`scripts/render_planarsviz.R`'s `chart_table()`
(render_planarsviz.R:146-154 is the exact precedent to copy):

```r
selections <- read_tsv("selections.tsv")
for (r in sort(as.integer(selections$rank[selections$selection == "exemplary"]))) {
  local({
    rank <- r
    add(paste0("exemplary_trees_", rank), function() plot_exemplary_tree(bundle, rank, "page"))
    ...
  })
}
```

The forest equivalent would loop over `forests.json` (already has
`forest_id` and `n_trees` per forest — `phonologylike`/`syntaxlike` both
present, `n_trees` 6 and 16, matching what I found by hand) and, for each
`forest_id`, register `n_trees` chart names
(`<forest_id>_tree_1` .. `<forest_id>_tree_<n_trees>`), each calling a new
function analogous to `plot_exemplary_tree()` but reading
`forests/<forest_id>.tsv`'s `tree_number`/`newick` instead of
`bundle$families`/`family_id`.

One thing to decide that I don't have a strong opinion on: whether every
forest gets this (`morsyn`, `tono`, `length`, `phon`, `inton` are forests
too, per `forests.json` — I only asked for `phonologylike`/`syntaxlike`
because that's what Jeff asked me for individual trees on) or just the
bundle forests (`phonologylike`, `syntaxlike`, `syntaxlike_notono`).
Registering it generically over every `forests.json` entry costs nothing
extra in code and avoids a future "why does this forest not have
individual trees" question. Checked `forests.json` directly rather than
trusting memory (a first draft of this note had these wrong) — actual
`n_trees` per forest: `morsyn` 3, `tono` 9, `length` 3, `phon` 6, `inton` 1,
`phonologylike` 6, `syntaxlike` 16, `syntaxlike_notono` 4. Registering all
eight would add 48 chart names; just the three bundles, 26.

## Not urgent, no collision risk right now

`bundle_forest_trees.r` and its 22 output files are not committed. Nothing
of mine is mid-edit in `render_planarsviz.R`, `exemplary.R`, or anywhere
else this would touch. Once ported, I'd expect `bundle_forest_trees.r` and
its flat-`results/` output files to go away the same way the
fragmentation-test's original matplotlib-equivalent situation resolved —
except this one never had any equivalent at all before today, so there's
no "original to preserve as a reference" question this time; the port can
just replace it outright.

## Update, same day: I touched fragmentation_test_plot.r — verified it's still your reference

You told me in your reply note that `fragmentation_test_plot.r`'s
all-groups output is the pixel reference chart 19's port is checked
against. Jeff asked for a second chart from it — just the two bundles
(`phonologylike`, `syntaxlike`) on their own, for a talk — so I refactored
the file into a function (`plot_fragmentation_test(groups, output_name,
width, height)`) called twice: once with every class and bundle (unchanged
groups, unchanged output filename), once filtered to just those two.

**Before touching it, I backed up the committed `nyan1308_fragmentation_test_plot.pdf`,
re-ran the refactored script, and pixel-diffed old against new at 200dpi:
0/2,600,000 pixels differ (0.0000%).** The all-groups call is unaffected —
your porting check's reference should still pass exactly as it did before.
The new file, `nyan1308_fragmentation_test_syntax_phon_plot.pdf`, is a
single un-faceted panel (the function drops `facet_grid` entirely when a
filtered call only has one `kind` left, since a one-strip facet label was
pointless) — not part of any port request, just a presentation extra.

Also touched (not part of any port request, but you should know the file
changed regardless): `span_placement_test_plot.r` — same kind of
refactor into `plot_span_placement(groups, output_name, ncol, width,
height, fill_color)`, called for the existing 9-group chart (verified
pixel-identical the same way, 0/3,960,000 differ) plus two new single-bundle
files, `nyan1308_span_placement_test_syntaxlike_plot.pdf` and
`_phonologylike_plot.pdf`, colored to match each bundle's own
laminar-forest color (`#BC3C29`/`#0072B5` from `BUNDLES`) instead of the
neutral blue the 9-panel chart uses. The old combined two-bundle file
(`nyan1308_span_placement_test_syntax_phon_plot.pdf`) is deleted — replaced
by the two separate ones, not kept alongside them. `span_placement_test.py`
itself (the Python side) is untouched. This script isn't part of any
current port request (see the fragmentation-test port's own note: this one
is "one step behind" it), so nothing here should affect your work unless
you'd already started on it — if so, say so the way the collision-avoidance
convention asks.

## Update, 2026-09-20, separate conversation: the fragmentation test's p-value flipped direction

Different thread of the analysis-session role, same day, working a request
Jeff raised independently of the forest/two-bundle-chart work above — flagging
it here since it also touches `fragmentation_test_plot.r` and the files your
"Collision status" section handed over. No conflict with the refactor above:
it landed first, and the refactor's own pixel-diff (0/2,600,000, logged above)
already proves the two compose cleanly.

Jeff noticed `class_fragmentation_test.py`'s `p_value_ge_observed` (small p =
*more fragmented* than chance) and `span_placement_test.py`'s
`p_value_le_observed` (small p = *more laminar* than chance) read in opposite
directions for the same kind of question, and asked for the fragmentation
test to match the other one's convention.

**Changed**: `class_fragmentation_test.py` now computes and writes
`p_value_le_observed` (fraction of permutations with family count <=
observed) instead of `p_value_ge_observed` (>= observed) — same null model,
same permutation, same underlying counts, only the reported tail and its
column name changed. Propagated the rename through everything that reads that
column: `export_planarsviz_data.py`, `fragmentation_test_plot.r` (the `aes()`
label and its design-note comment — done *before* the `plot_fragmentation_test()`
refactor above landed on top of it), `r/planarsviz/R/fragmentation.R`,
`r/planarsviz/R/planarsviz-package.R`'s `globalVariables()`,
`r/planarsviz/inst/data-contract.md`, and `check_fragmentation.R`'s
shared-columns list. Regenerated `man/read_planars_fragmentation.Rd` via
`roxygen2::roxygenise(".")` (one-line diff), the committed
`nyan1308_class_fragmentation_test.tsv`/`nyan1308_bundle_fragmentation_test.tsv`
(5000 draws, seed 0 — same as before, only the one column differs), the frozen
porting reference `results/planarsviz/reference/nyan1308_fragmentation_test_plot.png`,
and both bundles' `data/fragmentation_test.tsv` (`nyan1308`, `shifted_nyan`)
via `export_planarsviz_data.py --fragmentation-permutations 5000
--fragmentation-seed 0`. Ran `check_fragmentation.R` both ways afterward:
nyan1308 numbers identical, pixels 0.0000% different; shifted_nyan
(`library-only`) rendered clean.

**One real finding, not just plumbing**: intonational's old p was `1.00`, but
that was a floor artifact — family count can't go below 1 for any nonempty
span set, and intonational's observed count already *is* 1, so
`P(null >= 1)` is trivially 1.0 regardless of how surprising the result
actually is. The new `P(null <= 1) = 0.034` is the real, non-degenerate
number (only 3.4% of 5000 relabelings also hit the floor). Noted in
`results/visualizations.md`, whose fragmentation-test prose I also updated
with the flipped numbers throughout (old `p_ge` -> new `p_le`: tonosegmental
0.91->0.14, intonational 1.00->0.03, phonology-like 0.92->0.16, syntax-like
0.91->0.11, syntax-like-without-tonosegmental 0.77->0.45).

Left `docs/PLANARSVIZ_LIBRARY_PROGRESS.md` alone on purpose — dated changelog,
should keep saying what the column was called when that entry was written.

## Update, same day: cosmetic-only pass on the two single-bundle span_placement charts

Back on the forest/two-bundle-chart thread. Jeff asked for two more rounds
of adjustments to `nyan1308_span_placement_test_syntaxlike_plot.pdf` /
`_phonologylike_plot.pdf` (the two single-bundle files from the update
above) — a p-value label that overlapped the histogram bars, then larger
axis text/title/strip fonts. Both landed as new optional parameters on
`plot_span_placement()`, defaulting to the exact prior values, so the
9-group chart (`nyan1308_span_placement_test_by_group_plot.pdf`) is
unaffected. Re-verified pixel-identical against it (200dpi) after **each**
of the two changes, not just once — the first attempt at the label fix
briefly broke it (see below), which is exactly why: `label_hjust`/
`x_left_pad` (default -0.05/0.05, matching the original unlabeled
behavior), `axis_text_size`/`axis_title_size`/`strip_text_size` (default
8.8/11/9, matching `theme_bw(base_size=11)`'s own automatic sizing and the
strip text's prior hardcoded value).

**One real mistake worth knowing about in case the shape looks familiar**:
my first fix for the label overlap flipped `hjust` globally (label ends
left of the observed line instead of starting right of it) rather than as
a new parameter. That's wrong as a blanket default — several groups in the
9-panel chart have `observed` sitting right at their own panel's own axis
minimum (`morphosyntactic`, `syntax-like`, others), so a left-extending
label there ran straight off the panel edge and got clipped. Confirmed
happening by rendering, not caught by reasoning about it first. Fixed by
making it per-call: the two single-bundle files pass `label_hjust = 1.05`
(safe for them specifically, since their `observed` sits in the null
distribution's rising left tail with shorter bars to its left) and the
9-group chart keeps the original rightward default.

No effect on anything you'd be porting — `span_placement_test.py` itself
is still untouched, and this script is still "one step behind" the
fragmentation test's own port per the earlier note.
