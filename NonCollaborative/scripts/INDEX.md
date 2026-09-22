# Scripts Index

Every script under `analysis/`, `verification/`, `exploratory/` and
`planarsviz_checks/`. The hand-written R and the LaTeX utilities that sit at
the top of `scripts/` are described in `CLAUDE.md` instead.

**Where to run them from:** `NonCollaborative/`. Every path below is relative
to it, and that is where the porting checks run too.

## Core Analysis

**`analysis/laminar_analysis.py`**
- **Purpose**: Main workhorse for laminar family enumeration
- **Input**: Domain span TSV file (`domains/domains_{lang_id}.tsv`)
- **Algorithm**: Four-phase approach:
  1. Conflict detection (O(n²)) — classify span pairs as nested/disjoint/conflict
  2. Bron-Kerbosch enumeration (complement graph) — find all maximal independent sets
  3. Tree construction — build parent maps and Newick trees
  4. Analysis — test three hypotheses (Tree, Morphosyntax/Phonology divide, Word)
- **Output**: the four-phase report on stdout, and a result dict for callers
  (`spans`, `adjacency`, `families`, `span_family_count`, `n_families`,
  `truncated`). It writes nothing to disk. Until the 2026-09-20 cutover it
  also wrote the charts' R scripts; the `planarsviz` package draws them now
  from the bundle `export_planarsviz_data.py` writes.
- **Run it**: `python scripts/analysis/laminar_analysis.py` prints the report
  for nyan1308 pooled, then per domain type, then per bundle. It takes no
  arguments — call `main()` from Python to analyse a different file.
- **Dependencies**: `pandas`
- **Reading the rows instead of the spans**: `load_spans()` aggregates rows
  that share a span, which throws away each row's own `Domain_Type`. Callers
  that need the per-row labels — a permutation test over which label sits on
  which row, say — use `load_domain_dataframe()` (read and clean, no subset
  filter, no aggregation) and then `aggregate_spans()` themselves.
  `load_spans()` is those two in sequence and is unchanged.

**`analysis/refinement_counts.py`**
- **Purpose**: For each of the 69 maximal laminar families, count how many
  finer trees hide inside it at its polytomies (nodes with more than two
  children) — i.e. how much tree structure the family leaves undetermined
- **Two conventions, both reported** because whether constituents must be
  binary is an open question: little Schröder per polytomy (any arity
  allowed; this project calls the sequence "super-Catalan", see
  `exploratory/catalan.py`) and Catalan per polytomy (binary only). Totals
  across all 69 families: 8,599,689 against 125,032.
- **Output**: `results/laminar-families/nyan1308_refinement_counts.tsv` (per family),
  `results/laminar-families/nyan1308_refinement_polytomies.tsv` (per distinct polytomy, so
  the aggregate can be checked against the nodes it came from)
- **Example**: `python scripts/analysis/refinement_counts.py`

**`analysis/span_placement_test.py`**
- **Purpose**: A different Tree-hypothesis test from the fragmentation test
  below, though it looks similar. That one shuffles which *label* sits on
  which test; this one holds a group's own span *lengths* fixed and asks
  whether the real *positions* of those spans produce fewer conflicting
  trees than an arbitrary placement of same-length spans would.
- **Method**: every span redraws a uniformly random legal left edge for its
  own length (a length-22 span has exactly one legal position on this
  22-position structure, a length-2 span has 21 — smaller spans get more
  freedom purely from that constraint), grouped by length so same-length
  spans can never collide; 5000 draws, run for "all" plus the five domain
  types plus the three bundles, one shared random stream. Every group draws
  over the full 22-position structure regardless of its own observed range.
- **Finding**: morphosyntactic (p=0.019) and syntax-like without
  tonosegmental (p=0.020) are genuinely more tree-like than their own span
  lengths predict; syntax-like (p=0.051) and phonology-like (p=0.077) trend
  the same way more mildly. Tonosegmental (p=0.755) and intonational
  (p=0.901) trend the other way — not more coherent than chance given their
  sizes. The pooled result (p=0.335) is unremarkable; the breakdown is
  where the signal is, and it points differently than the fragmentation
  test's own findings, since the two ask genuinely different questions
  about the same 26 spans.
- **Output**: `results/counts-and-chance/nyan1308_span_placement_test.tsv` (one row per
  group), `_span_placement_null_tally.tsv` (`group, family_count, n` —
  a tally, not one row per draw)
- **Example**: `python scripts/analysis/span_placement_test.py`
- **Also in the bundle**, since 2026-09-21: the exporter calls this same
  `run_test()` behind `--span-placement-permutations`, so the package's
  charts and the committed TSVs above carry the same numbers.

*(The R that drew this test, `analysis/span_placement_test_plot.r`, was
archived to `OlderFiles/planarsviz_superseded/scripts/analysis/` on
2026-09-21. The package draws all three of its charts now —
`plot_span_placement_test()`, with `groups` and `view` — from a bundle
exported with `--span-placement-permutations`. Panels there still use
independent axes (`scales = "free"`), unlike the fragmentation chart: the
absolute family count is not comparable across groups of very different span
counts, so a shared axis would squash the small groups and misplace their own
annotations, which actually happened with `scales = "free_x"` alone.)*

**`analysis/class_fragmentation_test.py`**
- **Purpose**: Ask whether a domain class is more fragmented than its own
  number of tests would predict by chance. A class with many tests has more
  chances to produce conflicting spans, so a raw family count cannot be read
  as fragmentation on its own.
- **Method**: shuffle `Domain_Type` labels across the 95 cleaned test rows,
  holding each class's row count fixed, rebuild the conflict graph and
  re-count families; 5000 draws. Classes and bundles share one pass — a
  bundle's test count does not change under a per-type shuffle.
- **Finding**: tonosegmental's 9 families look like the worst fragmentation
  until you notice it carries 44 of the 95 tests, where chance alone gives
  about 17 — so it is markedly *more* laminar than chance (p=0.91), as is
  intonational. Morphosyntactic, phonological and length are unremarkable.
- **Output**: `results/counts-and-chance/nyan1308_class_fragmentation_test.tsv` (5 domain
  types), `_bundle_fragmentation_test.tsv` (3 bundles),
  `_fragmentation_null_draws.tsv` (every draw, long format, for the chart).
  The two summary files record the draw count and seed that produced them.
- **Imports**: `BUNDLES` from `planars_groupings.py`, `CLASS_COLORS` from
  `laminar_tree_counts.py` — each defined in one place, not redefined here
- **Also called by the exporter**, through `run_test()`, when
  `--fragmentation-permutations` is given. The exporter builds the groups from
  the domain types the data actually has rather than from this file's
  `CLASS_GROUPS`, so an unfamiliar dataset still works.
- **Example**: `python scripts/analysis/class_fragmentation_test.py`
  (reproduces the committed files exactly: 5000 draws, seed 0)

*(The R that drew this test, `analysis/fragmentation_test_plot.r`, was archived
to `OlderFiles/planarsviz_superseded/scripts/analysis/` on 2026-09-21. The
package draws both of its charts now — `plot_fragmentation_test()`, chart 19,
with `groups` for the two-bundle variant — from a bundle exported with
`--fragmentation-permutations`. Until then it and the package both wrote
`nyan1308_fragmentation_test_plot.pdf` and nothing recorded which had won.)*

**`analysis/laminar_tree_counts.py`**
- **Purpose**: Count maximal laminar families pooled, per domain class, per
  bundle, and with size-2 (adjacent-position) spans removed
- **Output**: `results/counts-and-chance/nyan1308_tree_counts.tsv`. The bar charts of these
  counts are drawn by the package; until the 2026-09-20 cutover this script
  drew them itself, in matplotlib.
- **Also owns `CLASS_COLORS`** — the five domain-type colours, in one place.
  `class_fragmentation_test.py` imports them and so does the exporter's
  `DOMAIN_TYPE_STYLE`, which is how they reach R.
- **Example**: `python scripts/analysis/laminar_tree_counts.py`

**`analysis/boundary_strength.py`**
- **Purpose**: Per-position boundary ("juncture") strength — for each cut
  between positions, how strongly it is treated as a constituent edge across
  the 69 families, on each side. A different unit of analysis from everything
  else here: the object measured is a juncture, not a domain.
- **Two measures**: `summed` (the analytical target — every span with that
  edge counts, including nested ones) and `capped` (how many of the 69
  families have at least one span with that edge, a reference line). See the
  module docstring for why they diverge.
- **Output**: `results/boundaries/nyan1308_boundary_strength.tsv`; `--subset` restricts
  the analysis to some domain types and tags the filename with them. The
  charts are drawn by the package; this script drew them in matplotlib until
  the cutover.
- **Example**: `python scripts/analysis/boundary_strength.py`
- **`strength_from_families()`** is the reusable core (spans + an
  already-enumerated family list in, summed/capped left/right dicts out),
  factored out so `boundary_strength_test.py` below can run the same
  counting logic on a permuted replicate's own spans/families.

**`analysis/boundary_strength_test.py`**
- **Purpose**: Is `boundary_strength.py`'s per-position strength — and,
  specifically, the jump from one position to the next — higher than a
  same-length-profile random arrangement of spans would produce by chance?
  A direct stress test of the "clear quantal jump" claim on the left edge
  of the orthographic word (and the more equivocal one on the right) made
  informally from the bar chart.
- **Method**: reuses `span_placement_test.py`'s null model and `GROUPS`
  list exactly (same `random_replicate()`, same "draw over the full
  22-position structure regardless of group" convention) but computes a
  fresh boundary-strength curve from each replicate's own family
  enumeration, rather than just a family count. Two statistics per
  (group, side, position): `level` (the strength itself) and `jump`
  (`strength[p] - strength[p-1]`, signed — the direct test of a rise at a
  candidate left edge). One-sided `p_value_ge_observed` (small = higher
  than chance), the mirror of `span_placement_test.py`'s own convention.
- **Finding**: on the pooled data, the left-edge jump at position 5 is
  robustly significant (p=0.0010, 5000 draws) — the "clear jump" claim
  holds up quantitatively. The best right-edge position (21, on the jump
  statistic) lands at p=0.0522 — right at the edge of the conventional
  threshold, matching the talk's own "more diffuse" hedge almost exactly.
  Tonosegmental's right edge at position 17 (the final vowel) is the
  single strongest result of any group (p=0.0004).
- **Output**: `results/boundaries/nyan1308_boundary_strength_test.tsv` — one row per
  (group, side, statistic, position): `observed`, `null_mean`, `null_p05`,
  `null_p95`, `p_value_ge_observed`, plus `n_permutations`/`seed`. No raw
  per-draw table — only percentiles are kept, the same choice
  `boundary_strength_density.tsv`'s precomputed curves already made, since
  the chart needs an envelope band, not a distribution shape.
- **Also called by the exporter**, through `run_test()`, when
  `--boundary-strength-test-permutations` is given.
- **Example**: `python scripts/analysis/boundary_strength_test.py`
  (reproduces the committed file exactly: 5000 draws, seed 0)
- **In the package** as `plot_boundary_strength_test()` — written directly
  there from the start, like `plot_fragmentation_test()`, with no earlier
  script to port or reference image to freeze.

**`analysis/planars_groupings.py`**
- **Purpose**: The named groupings of domain types, defined once — `BUNDLES`
  (the three pooled morphosyntax/phonology approximations, with colours and
  display labels) and `FILTERS` (the domain types a subset analysis leaves
  out). Imported by `laminar_analysis.py`, `laminar_tree_counts.py`,
  `class_fragmentation_test.py` and the exporter. Not runnable on its own.

**`analysis/random_tree_overlay.py`**
- **Purpose**: A ghost overlay of randomly sampled n-ary trees over 22
  positions, showing how vast the tree space is next to the 69 families the
  data actually allows. Illustration, not analysis.
- **Output**: `results/illustrations/nyan1308_random_tree_overlay.r` and its PDF — the one
  generated R script still in `results/`. Never ported to the package
  (it samples rather than drawing a fixed chart); scheduled for phase E.
- **Example**: `python scripts/analysis/random_tree_overlay.py` (`--n-trees`,
  `--n-leaves`, `--alpha`, `--seed`, `--r-only`)

### Scratch: the 25-arbitrary-layers question (2026-09-21)

**Committed so the numbers survive, deliberately not formalized.** These two
scripts answer a follow-on question of Jeff's about the boundary-strength
result and are named `scratch_` because nothing has decided yet whether they
should become a proper test, a note in `results/visualizations.md`, or
nothing. They print and return; neither writes a file, so neither is a
producer of anything in `results/`. Both reuse `laminar_analysis.py`'s real
`find_conflicts` / `enumerate_maximal_laminar_families` unchanged — different
inputs fed to the validated machinery, not a new algorithm.

**`analysis/scratch_25layers_covering.py`**
- **Question**: given 25 layers over the 22-position structure, one fixed as
  the full-span root and 24 free in both size and placement — (A) how
  fragmented can such a covering get, and (B) where does nyan1308's real 69
  sit against chance for 25 *fully arbitrary* layers?
- **(B)'s null is deliberately more naive than `span_placement_test.py`'s**,
  which holds each span's real length fixed and randomizes only position.
  This one randomizes size too, so it knows nothing about how big real
  linguistic domains are.
- **Finding**: over 3000 draws, mean 78.1, p05/median/p95 = 40/74/131;
  observed 69 gives `P(chance <= 69) = 0.4380` — almost exactly the median.
  (A)'s best is 1238 families from a randomized local search: a lower bound
  from a cheap search, not a certified maximum.
- **`laminar_analysis.MAX_FAMILIES` is monkeypatched to 50,000 inside this
  script only** — arbitrary intervals cross far more chaotically than real
  domains, and the project's own 1000 cap was undercounting. The committed
  module is untouched.
- **Open question for Jeff**: the script reads "25 layers" as 25 total
  (1 root + 24 free), one fewer than nyan1308's real 26 domains. `N_FREE` is
  the single knob if that reading is wrong.

**`analysis/scratch_25layers_describe_best.py`**
- **Purpose**: describe the 1238-family covering rather than just report it —
  an ASCII bracket diagram, and a factoring into independent conflict-graph
  components (one 22-span tangled cluster worth 619 ways, one trivial 2-span
  pair worth 2; 619 x 2 = 1238, which is where the number comes from).

**`analysis/scratch_25layers_run_output_3000draws.txt`** — the captured output
of the 3000-draw run, which takes a few minutes, so the numbers can be read
without re-running it.

## Data export

**`analysis/export_planarsviz_data.py`**
- **Purpose**: Export validated Python analysis results for the `planarsviz` R package
- **Output**: `results/planarsviz/<dataset>/data/` TSV/JSON bundle
- **Source of truth**: Reuses `laminar_analysis.py`; does not re-enumerate families
- **Example**: `python scripts/analysis/export_planarsviz_data.py --domain-file domains/domains_nyan1308.tsv`

**`render_planarsviz.R`**
- **Purpose**: Render the charts from a validated planarsviz bundle — the only
  planarsviz code that writes files
- **Output**: one PDF per chart in `--output` (default `<bundle>/plots`), plus
  `<dataset>_planarsviz_manifest.tsv` listing every file written and its canvas
  size. For nyan1308 the published copies live in `results/`.
- **Plots**: not a fixed list — the charts come from what the bundle holds (a
  pooled pair per domain type, a forest per `forests.json` entry plus one chart
  per tree in that forest, a variant per highlight and per filter subset, and so
  on). Run with `--list` to see the charts a given bundle supports.
- **Example**: `Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 --output results`

## Porting checks

**`planarsviz_checks/`** — twenty-one checks (thirteen in R, eight in Python) that
prove the `planarsviz` package draws what the old scripts drew, and that the
bundle carries the same numbers the Python analysis produces. Each runs on its
own and says what it checked:

```
Rscript scripts/planarsviz_checks/check_pooled.R          # one chart family
python scripts/planarsviz_checks/verify_forest_export.py  # bundle vs. archived script
```

The `check_*.R` ones render a chart and pixel-compare it with a frozen
reference in `results/planarsviz/reference/`; the `verify_*.py` ones compare
the bundle's numbers with what the archived scripts have pasted into them.
Both reach the archive through one place — `superseded.R` for R,
`superseded.py` for Python — so moving it again is two edits, not fifteen.
`check_renderer.py` compares every chart the renderer writes against the
reference set in one pass. `check_transparency.py` is a helper the tree-count
check calls, not a check of its own. `check_fragmentation.R` is the one that
works differently: chart 19 had no earlier script to run, so it compares
against the chart that chart's own R script drew, frozen as a reference.

## Verification

**`verification/verify_barthelmemy_correspondence.py`**
- **Purpose**: Verify laminar family algorithms on controlled toy data
- **Data**: 12-span intermediate-complexity toy example
- **Algorithms tested**:
  1. Exhaustive search — check all 2^n subsets
  2. Asymmetric hypergraph — maximal independent sets via hypergraph theory
  3. Copair hypergraph (Barthélemy) — maximal cliques (for comparison)
  4. NetworkX Bron-Kerbosch — cliques of complement graph
- **Expected result**: Algorithms 1, 2, 4 should all find 5 maximal families; algorithm 3 should find 25 cliques (different problem)
- **Key insight**: Demonstrates why complement graph transformation is necessary
- **Dependencies**: `networkx`

**`verification/verify_chichewa.py`**
- **Purpose**: Verify algorithms on real linguistic data
- **Data**: Chichewa [nyan1308] observed spans (26 spans, 65 conflicts)
- **Algorithms compared**:
  1. Exhaustive search — checks all 2^26 ≈ 67 million subsets
  2. NetworkX Bron-Kerbosch — finds maximal cliques of complement graph
- **Expected result**: Both should find 69 maximal families (verified ✓)
- **Runtime**: NetworkX Bron--Kerbosch is the practical verification path;
  exhaustive enumeration over 26 spans checks roughly 67 million subsets and
  may take several minutes or be impractical on some machines.
- **Dependencies**: `networkx`
- **Status**: The optimized algorithms agree on 69 families. The exhaustive
  implementation remains a reference check and should not be treated as a
  routine CI step.

## Exploratory / Archive

**`exploratory/treeTraversal.py`**
- **Purpose**: Earlier prototype for tree traversal and analysis
- **Status**: Superseded by `laminar_analysis.py`
- **Note**: Kept for historical reference; do not use for new work

**`exploratory/catalan.py`**
- **Purpose**: Enumerates all binary tree structures (Catalan number generator)
- **Status**: Exploratory; used to understand theoretical maximum tree count
- **Note**: Has bugs in enumeration logic (see project memory)

**`exploratory/catalan_old.py`**
- **Purpose**: Earlier version of Catalan enumeration
- **Status**: Archive
- **Note**: Superseded by current catalan.py

**`exploratory/generate_supercatalan_rows.py`** + **`render_supercatalan_rows.r`**
- **Purpose**: Draw every distinct n-ary tree shape over 2, 3 and 4 leaves,
  and 15 of the 45 over 5 leaves — one PDF per row, illustrations for the
  counting discussion in `REFERENCES.md`
- **Output**: `results/illustrations/supercatalan_trees_n2.pdf` … `_n5_sample15.pdf`, and
  `exploratory/supercatalan_trees.json`, the shapes the renderer reads
- **Example**: `python scripts/exploratory/generate_supercatalan_rows.py --pdf`
  — it launches the R renderer and `pdfcrop` itself. Don't run the `.r` file
  directly: it reads the JSON from the working directory, so it only works
  from `scripts/exploratory/`, which is where the Python script puts it.
- **Status**: scheduled to move into the `illustrations` bundle in phase E

## Where the charts went

Until the 2026-09-20 cutover, most charts were drawn by generated R scripts
sitting in `results/` beside the PDFs, written by generator functions in
`analysis/laminar_analysis.py`. The `planarsviz` package replaced all of them.

- The scripts are archived in `OlderFiles/planarsviz_superseded/`, where
  the porting checks still run them to prove the package draws the same thing.
  Do not delete them — see that directory's `README.md`.
- The generators are gone from `laminar_analysis.py` (cutover step C3), as is
  the matplotlib plotting that was in `laminar_tree_counts.py` and
  `boundary_strength.py`.
- `results/illustrations/nyan1308_random_tree_overlay.r` is the one generated R script
  still in `results/`: it draws a random sample rather than a fixed chart, was
  never ported, and is scheduled for phase E.
- `planarsviz_checks/` holds the porting checks — the R ones reach the archive
  through `superseded.R`, the Python ones through `superseded.py`.

---

## Organization Guide

- **analysis/** — Core algorithms and the exporter
- **verification/** — Verification scripts (`verify_*.py`)
- **exploratory/** — Prototype and archive work (`treeTraversal.py`, `catalan.py`)
- **planarsviz_checks/** — Checks that the R package draws what the old scripts drew

See `docs/VERIFICATION.md` for methodology, results, and theoretical framework,
`docs/planarsviz_charts.md` for every chart the package draws, and
`results/visualizations.md` for what each artifact in `results/` shows.
