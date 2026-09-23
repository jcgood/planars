# planarsviz reconciliation review — feedback

Written 2026-09-13 by the Claude session that built the working-script changes
this reconciliation is meant to preserve (tip-label placement, the
convergence-vs-family-frequency split, representative-family selection, the
exemplary-tree pairing). `CLAUDE_PLANARSVIZ_HANDOFF.md` and
`PLANARSVIZ_RECONCILIATION.md` state reconciliation is complete and that
legacy/package visual comparisons were done. This note is the result of
actually doing that comparison — rendering two package outputs and looking at
them directly, not re-running the test suite. Both had real problems. Please
treat "reconciliation complete" as not yet accurate until these are addressed.

## Method

Rendered `results/chart_data/nyan1308/plots/pooled/all_family_overlay.pdf`
and `results/chart_data/nyan1308/plots/exemplary/family_001.pdf` to PNG and
inspected them directly, alongside the corresponding legacy outputs
(`results/nyan1308_all_families_labeled.pdf`,
`results/nyan1308_exemplary_trees_*.pdf`). No changes were made to any
package file — this is a report, not a fix.

## Finding 1: `plot_all_family_overlay()` is not a port of the legacy chart

The legacy `nyan1308_all_families_labeled.pdf` is a ghost-overlay dendrogram:
69 semi-transparent trees stacked so darkness = how many families share a
span and thickness = convergence (independent test count), with boxed
two-line tip labels ("10\nRoot" style).

`plot_all_family_overlay()` renders something structurally different: a
binary presence/absence matrix, 69 rows (one per family) × observed spans as
columns, filled/unfilled cells. It covers related analytical ground (which
families contain which spans) but is not a restyled version of the same
chart — there's no tree, no darkness/thickness encoding, no tip labels. If a
matrix view is intentionally a *new*, additional chart rather than a
reconciled replacement, that's fine, but the handoff doc lists it under
"working-script changes preserved... ported into the package," which implies
equivalence that isn't there.

## Finding 2: `plot_exemplary_trees()` — right structure, concrete bugs

The tree-above-pooled-plot layout matches the legacy design (`family_001.pdf`
compared against `nyan1308_exemplary_trees_1.pdf`). Three problems within
that structure:

1. **Position labels are wrong, not just differently styled.** Position 10 is
   labeled `V`; the project's established label (used everywhere else,
   including `laminar_analysis.py`'s own `_NYAN1308_POS_LABELS`) is `Root`.
   Position 11 is labeled `Un`; it should be `Ext`. These aren't abbreviation
   choices — they don't correspond to the real position names at all. Worth
   checking the package's position-label source against
   `_NYAN1308_POS_LABELS` (or wherever the bundle now sources it from)
   directly, since two positions being wrong suggests a systematic mismatch,
   not a typo.

2. **The pooled-plot test labels overlap into illegible text.** Multiple
   `Test_Labels` strings render stacked on top of each other on the same row
   (visible directly in `family_001.pdf`, e.g. the layer-13 and layer-12
   rows). This is the same failure mode the legacy `nyan1308_exemplary_trees`
   script hit on its first attempt this session — cross-referencing that
   fix (giving the pooled panel real height per test,
   `domain_charts-cgpt.r`'s own `max(7, n_tests*0.7)` cm convention, not a
   compressed shared row) may be directly useful here.

3. **A stray 0–20 axis is rendered on the tree panel.** Looks like a
   `ggtree` default (branch-length axis) leaking through rather than a
   deliberate choice — the legacy tree panels have no axis at all.

## Recommendation

Don't treat this as blocking the package's existence or direction — the
tree-plus-pooled-evidence structure for exemplary trees is a genuine match
for the legacy design's intent. But before writing "reconciliation complete"
or "visual comparisons completed" again: actually render a chart, look at it,
and check specific numbers/labels (e.g., does position 10 say "Root"?) rather
than relying on tests passing / package installing / smoke tests. None of
those would have caught either finding above.

For the eventual cutover (separate question from this review): swap file by
file, not in bulk, and only after each specific chart has been visually
diffed against its legacy counterpart — see the conversation this note came
out of for the fuller reasoning.

---

## Follow-up review — 2026-09-13, same day, after the above was addressed

`CLAUDE_PLANARSVIZ_HANDOFF.md` was updated to claim "Direct visual comparison
found and fixed incorrect labels, tree axes, and pooled-label collisions in
the exemplary output" and to add `plot_all_family_tree_overlay()` alongside
`plot_family_membership_matrix()` (with `plot_all_family_overlay()` kept as a
compatibility alias). Re-rendered and re-inspected directly, same method as
before, against the same two files.

**Genuinely fixed, confirmed by rendering:**

- Position labels are correct now — `family_001.pdf` shows `10 Root` and
  `11 Ext`, matching `_NYAN1308_POS_LABELS` exactly. Same fix carried over to
  `plot_all_family_tree_overlay()`.
- The stray 0–20 tree-panel axis is gone.
- `plot_all_family_tree_overlay()` is a real ghost-overlay dendrogram now —
  vertical orientation, root at top — not the presence/absence matrix. Good
  call keeping the matrix as its own honestly-named function
  (`plot_family_membership_matrix()`) instead of overloading one name for two
  different chart types.

**Not fixed — the pooled-plot label collision changed shape, it didn't go
away.** In `family_001.pdf`, the overlapping-horizontal-text problem from the
last review is gone, but it's been replaced by a different illegible layout:
every `Test_Labels` string on a shared layer now renders as 90°-rotated
vertical text climbing straight up from that layer's line into blank space
above the plot — e.g. `NegTonePattern3-PERM-NoOM-Other` as a single vertical
string extending roughly a third of the page height, several of these
side by side and overlapping each other near the top of the panel. Confirmed
by cropping directly into that region. This is still the same underlying
issue as before (not enough allotted space per test, or the wrong text
orientation/layout strategy for showing many co-occurring tests on one
layer) — worth comparing against `domain_charts-cgpt.r`'s actual
`constituency.plot()` behavior, which gives each *test* its own horizontal
row (readable left-to-right at the row's own y-position), not one row per
layer with all co-occurring test names crammed into it.

**Two smaller new issues, both in `plot_all_family_tree_overlay()`:**

1. The legend reads "Domain type — all families" with a single grey swatch —
   that's the multi-color domain-type legend template left in place on a
   single-group (all-black) chart. This is the exact bug from the legacy
   `generate_r_overlay_script()` that I hit and fixed this session (see the
   conversation this file came out of): gate legend generation on whether
   more than one colored group actually contributed trees, and show
   something else (or nothing) for the single-group case.
2. The subtitle reads "Overlay of 1 exported family sets" — reads like a
   debug/placeholder string (a variable substitution showing the count of
   *subset exports*, which is 1 for the unfiltered "all" case, rather than
   anything a reader would want to know) rather than intended chart text.

**Updated recommendation:** two of the three original exemplary-tree issues
are solved and confirmed. The third (pooled-panel label legibility) needs a
different approach, not a smaller version of the current one — rotating text
90° into open space above the plot doesn't scale any better than the
horizontal overlap it replaced once a layer has more than a handful of
co-occurring tests (several of these families have 40+ tests total). The
"reconciliation complete" / "visual comparison completed" language should
wait until this specific panel is legible for a real family with a high
test count, not just checked structurally.
