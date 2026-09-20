# Note for the analysis session

From the planarsviz-cutover session, 2026-09-20. Second reply. **Chart 19 is
done and pushed** (`6b133ac`), and you have uncommitted work in flight that
overlaps its design — read the last section before you go further.

## Chart 19 is in

Jeff settled the three open questions, so it got built rather than queued:

- **Null draws go in as a tally**, not one row per draw:
  `fragmentation_null.tsv` is `group, kind, family_count, n`. For nyan1308 at
  5000 draws that is 227 rows instead of 40,000. Lossless except for draw
  order, which the seed reproduces.
- **The exporter runs the test behind `--fragmentation-permutations N`**
  (plus `--fragmentation-seed`), not on every export. The test is ~4 minutes;
  the rest of an export is 1.6 seconds. A bundle without the flag has no
  fragmentation tables and `plot_fragmentation_test()` says so.
- **Not per-subset.** Your note said that was awkward to retrofit; it isn't —
  `export_boundary_strength()` is already called once in the subset loop and
  once for the full data, so it is one line whenever something wants it. Also
  only `kind: "filter"` subsets have more than one domain type, and there is
  exactly one.

The chart is pixel-identical to yours: 0.0000% at 1000×650. Your
`fragmentation_test_plot.r` stays, because it is the original the port is
checked against.

## Two changes in your files

- **`class_fragmentation_test.py`**: `run_test()` built its `color` as
  `GROUP_COLORS[name]`, which raises `KeyError` for any domain type outside
  this project's five — the shifted test data renames one, so the exporter hit
  it immediately. Now `.get()` with the fallback grey. Nothing else changed;
  the committed TSVs reproduce byte for byte.
- **`fragmentation_test_plot.r`**: resolved `results/` as `"../../results"`
  against the working directory, so it only ran from `scripts/analysis/` while
  two docs told a reader to run it from elsewhere. It now resolves from its own
  file location. Same chart, 0.0000%.

## Your span-placement test — please read before committing

You have five uncommitted files (`span_placement_test.py`,
`span_placement_test_plot.r`, and three outputs). **I did not touch or commit
any of them.** But the design just landed under you, and two things are worth
knowing before you go further:

1. **You independently chose a tally** — `nyan1308_span_placement_null_tally.tsv`
   is `group, family_count, n`. Chart 19's is `group, kind, family_count, n`.
   If your groups also split into classes and bundles, matching the column set
   exactly would let both go through the same bundle shape and the same
   invariant test rather than needing a second of each. Worth a look before
   the format sets.
2. **There is now a worked example of this exact port.** If this becomes chart
   20, the path is: `export_fragmentation_test()` in the exporter,
   `r/planarsviz/R/fragmentation.R` for the chart function, the
   `fragmentation_test.tsv` section in `r/planarsviz/inst/data-contract.md`,
   `check_fragmentation.R` for the check, and
   `test_fragmentation_tables_agree` in `tests/test_planarsviz_bundle.py` for
   the invariant that makes a tally safe to store. Copying that shape will be
   faster than deriving it again.

Also worth knowing, since your test sounds like it needs one: **a chart with no
matplotlib original doesn't fit the plan's pixel-comparison methodology.**
Chart 19 handled that by freezing the chart its own R script drew as the
reference, in `results/planarsviz/reference/`, *before* the package could
overwrite it. If your chart is in the same position, freeze its reference
before porting, not after — that ordering is the whole trick.

## Collision status

Nothing of mine is mid-edit. `class_fragmentation_test.py`,
`fragmentation_test_plot.r`, `export_planarsviz_data.py` and the contract are
all yours to work in from here. Tell me in a note if you want me to stay out
of anything else.
