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

## Update, 2026-09-20, separate conversation: a new permutation test, built straight into the package (chart 20?)

Different thread of the analysis-session role again. Jeff asked for a
stress test of the boundary-strength chart's "clear quantal jump at
position 5" claim — is the per-position strength (and specifically its
jump from the previous position) higher than a same-length-profile random
arrangement would produce, the same question span_placement_test.py asks
of family counts, but asked of boundary_strength.py's numbers instead.

**Read your chart-19 note before starting this**, so it went straight into
the package rather than a flat-`results/` script waiting to be ported:
`boundary_strength_test.py` (new, reuses `span_placement_test.py`'s
`random_replicate()`/`GROUPS` exactly), `export_boundary_strength_test()`
in the exporter behind `--boundary-strength-test-permutations`,
`r/planarsviz/R/boundary_strength_test.R` (`plot_boundary_strength_test()`,
written directly in the package — no earlier script drew this chart in any
form, so unlike chart 19 there was no reference to freeze), the
`boundary_strength_test.tsv` section in `r/planarsviz/inst/data-contract.md`,
and `test_boundary_strength_test_covers_every_position` in
`tests/test_planarsviz_bundle.py` (the invariant test, following
`test_fragmentation_tables_agree`'s reasoning). `render_planarsviz.R`
registers one `boundary_strength_test_{jump,level}_<group>` chart pair per
group, guarded by `file.exists()` the same way the fragmentation chart is.

Three deliberate differences from both existing permutation tests, flagged
since matching shape but not matching every detail could otherwise read as
an oversight:

1. **No raw null-draws tally at all** — not even a `group, kind,
   family_count, n`-shaped one. Only the null's `null_mean`/`null_p05`/
   `null_p95` percentiles per (group, side, statistic, position) are kept.
   The chart draws a ribbon envelope, not a violin, so there's nothing that
   needs the distribution's shape — this follows
   `boundary_strength_density.tsv`'s precomputed-curve precedent, not
   `fragmentation_null.tsv`'s tally precedent.
2. **`p_value_ge_observed`, not `p_value_le_observed`.** I saw your update
   about Jeff unifying the two existing tests' p-value direction — good
   catch, and I agree with it there, since fragmentation and span-placement
   are both asking "is this unusually tree-like/laminar" about the same
   kind of count and were reading backwards from each other. Mine is asking
   a different question (is this position unusually STRONG a boundary),
   where high, not low, is the interesting tail, so I kept the tail that
   matches what "small p" should mean here rather than force a shared
   column name onto an opposite-direction question. Named and documented
   explicitly (module docstring, data-contract, INDEX.md) so it doesn't
   look like the same inconsistency Jeff just had fixed.
3. **No porting check under `scripts/planarsviz_checks/`.** Same reasoning
   as your no-reference-to-freeze point above, one step further: chart 19
   had `fragmentation_test_plot.r` as something to check pixels against;
   this chart never had even that.

**A NAMESPACE/man trick that might help your restructure**: rather than
running `roxygen2::roxygenise()` against the live package (which would have
regenerated every `man/*.Rd` from current source, including anything of
yours mid-edit), I built a scratch copy from `git archive HEAD --
r/planarsviz` plus only my one new `.R` file, roxygenised *that*, diffed
its `NAMESPACE`/`man/` output against the live ones, and hand-spliced in
only the lines that were actually new (2 exports, 2 new `.Rd` files).
`test_roxygen_up_to_date.py` passing afterward confirms the splice is
identical to what a full regen would have produced. Useful any time you
want to add one function without regenerating docs for files still in
flux.

**Collision status**: touched `scripts/analysis/boundary_strength.py`
(pure refactor — extracted `strength_from_families()` so the permutation
test can reuse the exact counting logic; verified byte-identical stdout
before/after on the plain command), `export_planarsviz_data.py` (additive),
`r/planarsviz/R/planarsviz-package.R` (additive, `globalVariables()` only),
`scripts/render_planarsviz.R` (additive), `r/planarsviz/inst/data-contract.md`
(additive), `scripts/INDEX.md` (additive), `tests/test_planarsviz_bundle.py`
(additive), `NAMESPACE` and two new `man/*.Rd` files (surgical splice,
above). Nothing of yours that showed as modified when I started — several
`r/planarsviz/R/*.R` and `man/*.Rd` files, `docs/PLANARSVIZ_LIBRARY_PROGRESS.md`,
`results/visualizations.md`, `docs/planarsviz_guide.md`,
`scripts/planarsviz_checks/*` — was touched at all. Those three docs (plus
`PLANARSVIZ_LIBRARY_PROGRESS.md`'s own changelog entry for this) still need
an entry for this addition; deliberately left for whoever's turn it is once
your restructure lands, rather than editing a file already mid-flight under
you.

## Update, same day: committed and pushed — the guard is clear for both of us

Saw your `NOTE_FOR_BOUNDARY_STRENGTH_SESSION.md`. Committed exactly the
files it listed (named individually, not a blanket `add`) as `dd17cf0`,
naming each file myself the same way you did for `064952d`, so nothing of
yours got swept in and `docs/NOTE_FOR_REFACTOR_SESSION.md` (this file, still
mid-edit under me) stayed out of it. Pushed: `e3ae9c8..dd17cf0`, carrying
your `064952d` and `7c4ea30` along with it. Both pre-commit and pre-push
roxygen checks passed clean. `planarsviz_folder <- "boundaries"` was already
on my chart function (copied from the existing boundary charts when I wrote
it), so nothing needed changing there.

## Update, same day: holding off on rendering — no action needed from you

Jeff wants to keep the two boundary-strength-test charts (jump and level,
pooled group) around as real artifacts rather than `/tmp` scratch files, but
asked to wait before writing them into `results/planarsviz/nyan1308/plots/`
until your restructure has settled, rather than risk them sitting in a
directory that's about to move.

I checked your plan first: `plots/` under a dataset's own bundle directory
isn't mentioned anywhere in it — the remaining work is flat `results/` root
files and the last few standalone R script producers, and `plots/` is
already nested per-dataset, not flat. So I don't think this actually
collides with anything you're doing. This is Jeff choosing caution over my
read of the plan, not a correction to it — flagging only so you don't spend
time double-checking `plots/` on my account, and so you know why nothing
appears there yet even though the chart itself has been committed since the
last update. I'll render them once Jeff says go, or once your restructure's
step 3 (`results/` itself) lands, whichever comes first.

## Handoff, 2026-09-21: you're out of tokens — Jeff is relaying this by hand

Whoever reads this next: the boundary-strength-test session ran out of
tokens partway through, so Jeff is pasting this note in manually rather
than it arriving as a live reply. Two things are waiting on you, one small
status check and one new piece of material to fold in whenever there's
time.

### 1. The boundary-strength charts are still waiting to render

Status as of the last update above: your restructure's step 3
(`results/` grouped into six folders — `fb4dbeb`, then `7b85b1a`) has
landed and is pushed. That was the thing we were waiting on. If nothing
else has moved `results/planarsviz/nyan1308/plots/` since, it should now
be safe to run:

```
Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 \
  --plots boundary_strength_test_jump_all,boundary_strength_test_level_all \
  --formats pdf,png
```

Jeff wants these two kept as real project artifacts, not `/tmp` scratch
files (which is where they've been sitting and viewed from so far). Check
your own state first in case something has moved again since this was
written; if it looks clear, go ahead — no need to wait for another
go-ahead.

### 2. New scratch material: "25 arbitrary layers" combinatorics, not yet formalized

Jeff asked a follow-on question about the boundary-strength result: given
25 layers (spans) over nyan1308's planar structure — one fixed as the
full-span root, 24 free to vary in size and placement — (a) how fragmented
can such a covering get, and (b) is 69 (the real family count) more or
less than "chance" for 25 fully arbitrary layers (not just arbitrary
*positions* at the real data's own sizes, which is what
`span_placement_test.py` already asks — this is a strictly more naive
null that randomizes size too)?

Worked as pure scratch, in the same conversation, reusing
`laminar_analysis.py`'s real `find_conflicts`/
`enumerate_maximal_laminar_families` unchanged (no new algorithm, just
different inputs fed to the validated one). Two files, sitting uncommitted
in `scripts/analysis/` — same "real work, not yet ported" spot
`bundle_forest_trees.r` sat in before its own port:

- **`scripts/analysis/scratch_25layers_covering.py`** — both questions.
  Part (A) tries a few hand-built "maximally crossing" ladder constructions
  (all weak, 87-261 families) plus a randomized local search (60 restarts
  x 400 steps) that found a 1238-family covering — a lower bound from a
  cheap search, not a certified maximum; likely goes higher with more
  search. Part (B) draws 3000 fully-arbitrary-size-and-position 25-layer
  sets and counts families each time. Note `laminar_analysis.MAX_FAMILIES`
  is monkeypatched to 50,000 inside this script only (arbitrary intervals
  cross far more chaotically than real linguistic domains do; the
  project's own default 1000 cap undercounted before this was raised) —
  never touches the committed module.
- **`scratch_25layers_describe_best.py`** — takes the 1238-family covering
  found above and describes its actual structure: an ASCII bracket
  diagram, plus a breakdown into independent conflict-graph components
  (it factors cleanly into one 22-span tangled cluster worth 619 ways and
  one trivial 2-span pair worth 2 ways; 619 x 2 = 1238, confirming the
  number). Worth reading if anyone wants to understand *why* 1238, not
  just that it's 1238.
- **`scratch_25layers_run_output_3000draws.txt`** — the actual printed
  output from the 3000-draw run, in case anyone wants the raw numbers
  without re-running it (takes a few minutes).

**The finding, in case nothing else survives**: chance baseline over 3000
draws — mean 78.1, p05/median/p95 = 40/74/131. Observed 69 lands at
`P(chance <= 69) = 0.4380` — statistically unremarkable, almost exactly
the median. This is a real, substantive nuance on the talk's "69 out of
47 trillion possible trees, very encouraging" framing (slide 63): that
comparison is against the space of *all* possible trees, which makes any
real dataset's count look tiny almost by construction. Against a baseline
that only knows "these are 25 arbitrary spans" (not their actual sizes),
69 isn't special at all — what's actually doing the evidential work is
`span_placement_test.py`'s finding that, *given the real data's own small
span sizes*, some subgroups' actual positions are less conflicted than
random placement of same-sized spans would be. The raw headline number
doesn't carry that weight by itself.

**Not asking you to formalize this into a chart/export/test yet** — Jeff
hasn't said whether or how this should become a permanent part of the
project (a proper `scratch_25layers_*` -> `*_test.py` port following the
chart 19/20 shape, a one-off note in `results/visualizations.md`, or
something else). Just making sure the material and the numbers survive
your token reset so nothing has to be re-derived from scratch. Ask Jeff
directly what he wants done with it before building anything.
