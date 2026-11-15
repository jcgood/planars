# Scripts Index

The porting checks, verification scripts and exploratory prototypes in
`NonCollaborative/scripts/`. The analysis modules are the `laminar/` package
at the repo root (moved 2026-10-24) and are indexed in `laminar/INDEX.md`. The
hand-written R and the LaTeX utilities at the top of `scripts/` are described
in `NonCollaborative/CLAUDE.md` instead.

**Where to run them from:** `NonCollaborative/`. Paths below are relative to
it.

## Porting checks

**`planarsviz_checks/`** — twenty-three checks (fourteen in R, nine in Python) that
prove the `planarsviz` package draws what the old scripts drew, and that the
bundle carries the same numbers the Python analysis produces. Each runs on its
own and says what it checked:

```
Rscript scripts/planarsviz_checks/check_pooled.R          # one chart family
python scripts/planarsviz_checks/verify_forest_export.py  # bundle vs. archived script
```

The `check_*.R` ones render a chart and pixel-compare it with a frozen
reference in `results/chart_checks/reference/`; the `verify_*.py` ones compare
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

**`exploratory/max_fragmentation_search.py`**
- **Purpose**: how fragmented *can* a covering of N layers over the planar
  structure get? A few hand-built "maximally crossing" ladders plus a
  randomized local search, using the real family-count function as the
  objective. Whatever it finds is a lower bound from a cheap search, not a
  certified maximum — the conflict graph induced by crossing intervals is a
  circle graph and no closed form is derived here.
- **Status**: exploratory. The chance-baseline half of this script became
  `laminar/arbitrary_layers_test.py` on 2026-09-22; what is left is the
  search, which looks for a bound rather than testing a hypothesis and so
  does not fit the shape the project's permutation tests share.
- **Its published 1238-family figure is for the wrong layer count.** Both
  halves originally ran at 25 total layers where nyan1308 has 26. `N_FREE` is
  corrected, but the search has not been re-run, so do not quote 1238 for 26
  layers.
- **Note**: raises `laminar_analysis.MAX_FAMILIES` by monkeypatch, not the
  restoring context manager `arbitrary_layers_test.py` uses. Fine in a
  standalone run; another reason not to import it.

**`exploratory/max_fragmentation_describe.py`**
- **Purpose**: describe a fragmented covering rather than just count it — an
  ASCII bracket diagram and a factoring into independent conflict-graph
  components, which is what explains a high count (independent clusters
  multiply their option counts together).
- **Status**: exploratory; its hardcoded covering is the old 25-layer one.

**`exploratory/treeTraversal.py`**
- **Purpose**: Earlier prototype for tree traversal and analysis
- **Status**: Superseded by `laminar_analysis.py`
- **Note**: Kept for historical reference; do not use for new work

**`exploratory/catalan_old.py`**
- **Purpose**: Earlier version of Catalan enumeration
- **Status**: Archive
- **Note**: Superseded by `laminar/catalan.py`
## Slides

One-off figures for talks: a package chart with annotation added on top
(colours, emphasis) that the package itself doesn't need. Each is one R
script, run from the repo root, writing to `results/<dataset>/slides/`. It
builds on the package's exported chart functions rather than copying them,
so the tree always matches the bundle. Add a new slide figure here as a new
script; if the same annotation is wanted a third time, make it a package
option instead.

**`slides/nyan1308_most_binary_orthographic_word.R`**
- **Purpose**: the most binary tree, plain and with the orthographic word
  (5–19) emphasised: thick edges out to 5 and 19 (the package's `emphasis`),
  and those edges, every edge inside the word and the labels of positions
  5–19 in dark red. A pixel-aligned pair for a
  dissolve between slides. 16:9, no title.
- **Run**: `Rscript NonCollaborative/scripts/slides/nyan1308_most_binary_orthographic_word.R`

**`slides/nyan1308_all_families_word_5_17.R`**
- **Purpose**: the combined constituency forest (`all_families_labeled`),
  plain and annotated with a possible word domain 5–17: in each stacked
  family, edges lying inside 5–17 in blue (below the 5–17 node, where the
  family has one: 37 of 69), labels 5–17 blue; then a third slide adding
  the orthographic word's extension as a dark red "shield": edges inside
  5–19 not already blue, labels 18–19 dark red. Colours checked for
  colour-blind readers (see the script's header).
  Pixel-aligned slides for dissolves. The package chart's own 20 × 14 in canvas.
- **Run**: `Rscript NonCollaborative/scripts/slides/nyan1308_all_families_word_5_17.R`

**`slides/nyan1308_consensus_vs_depth.R`**
- **Purpose**: every tree (maximal laminar family) placed by its consensus
  score (the sum, over its domains, of how many trees contain each) against
  its depth and its number of binary nodes, in two panels with the same
  vertical scale; the consensus tree and the most binary tree labelled.
  Stops if its top score isn't `selections.tsv`'s `consensus_all`. Also
  writes the numbers as a `.tsv`. 16:9 slide, not a package chart.
- **Run**: `Rscript NonCollaborative/scripts/slides/nyan1308_consensus_vs_depth.R`

**`slides/nyan1308_resolution_profile.R`**
- **Purpose**: every stretch [left, right] as a tile, in two panels on the
  same grid: resolution less chance (diverging, dots for p < 0.05) and
  domains crossing. Real domains outlined in black, 5–17 and 5–19 in dark
  red. Reads `laminar/resolution_profile.py`'s profile TSV. 16:9 slide, not
  a package chart.
- **Run**: `Rscript NonCollaborative/scripts/slides/nyan1308_resolution_profile.R`

**`slides/nyan1308_conflict_profile.R`**
- **Purpose**: conflict density (plan decision 11) in two panels: every
  stretch as a tile, conflict density less chance (green less, orange
  more), real domains outlined; and, by the position added, the conflict a
  one-position step brings in less chance (mean, with the range of steps),
  for stretches growing rightward and leftward. The caption gives the
  quantal test. Reads `laminar/resolution_profile.py`'s profile, positions
  and quantal TSVs. 16:9 slide, not a package chart.
- **Run**: `Rscript NonCollaborative/scripts/slides/nyan1308_conflict_profile.R`

---

## Organization Guide

- **`laminar/` (repo root)** — the analysis modules, the CCDB import, the exporter, the renderer and `python -m laminar charts`; indexed in `laminar/INDEX.md`
- **verification/** — Verification scripts (`verify_*.py`)
- **exploratory/** — Prototype and archive work (`treeTraversal.py`)
- **planarsviz_checks/** — Checks that the R package draws what the old scripts drew
- **slides/** — One-off annotated figures for talks, built on the package's charts
- The hand-written R and LaTeX utilities at the top of `scripts/` are in `CLAUDE.md`, not here

See `docs/VERIFICATION.md` for methodology, results, and theoretical framework,
`planarsviz/docs/charts.md` (repo root) for every chart the package draws, and
`results/visualizations.md` for what each artifact in `results/` shows.
