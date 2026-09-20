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
- **Output**: `results/nyan1308_refinement_counts.tsv` (per family),
  `results/nyan1308_refinement_polytomies.tsv` (per distinct polytomy, so
  the aggregate can be checked against the nodes it came from)
- **Example**: `python scripts/analysis/refinement_counts.py`

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
- **Output**: `results/nyan1308_class_fragmentation_test.tsv` (5 domain
  types), `_bundle_fragmentation_test.tsv` (3 bundles),
  `_fragmentation_null_draws.tsv` (every draw, long format, for the chart).
  The two summary files record the draw count and seed that produced them.
- **Imports**: `BUNDLES` from `planars_groupings.py`, `CLASS_COLORS` from
  `laminar_tree_counts.py` — each defined in one place, not redefined here
- **Example**: `python scripts/analysis/class_fragmentation_test.py`
  (reproduces the committed files exactly: 5000 draws, seed 0)

**`analysis/fragmentation_test_plot.r`**
- **Purpose**: Draw the test above — one horizontal violin per group (the
  null distribution) with the observed family count as a filled dot, classes
  and bundles as two stacked panels on a shared axis, p-value per row
- **Input**: `results/nyan1308_fragmentation_null_draws.tsv` and the two
  summary TSVs; it does not re-run the permutation
- **Output**: `results/nyan1308_fragmentation_test_plot.pdf`
- **Example**: `Rscript scripts/analysis/fragmentation_test_plot.r` (it
  resolves `results/` from its own location, so any working directory is fine)
- **Not yet in the package**: this is the one chart still drawn by a
  standalone script rather than by `planarsviz` from the bundle. Porting it is
  planned as chart 19; it has no matplotlib original, so its own committed PDF
  is the reference a port must reproduce.

**`analysis/laminar_tree_counts.py`**
- **Purpose**: Count maximal laminar families pooled, per domain class, per
  bundle, and with size-2 (adjacent-position) spans removed
- **Output**: `results/nyan1308_tree_counts.tsv`. The bar charts of these
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
- **Output**: `results/nyan1308_boundary_strength.tsv`; `--subset` restricts
  the analysis to some domain types and tags the filename with them. The
  charts are drawn by the package; this script drew them in matplotlib until
  the cutover.
- **Example**: `python scripts/analysis/boundary_strength.py`

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
- **Output**: `results/nyan1308_random_tree_overlay.r` and its PDF — the one
  generated R script still in `results/`. Never ported to the package
  (it samples rather than drawing a fixed chart); scheduled for phase E.
- **Example**: `python scripts/analysis/random_tree_overlay.py` (`--n-trees`,
  `--n-leaves`, `--alpha`, `--seed`, `--r-only`)

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
  pooled pair per domain type, a forest per `forests.json` entry, a variant per
  highlight and per filter subset, and so on). Run with `--list` to see the
  charts a given bundle supports.
- **Example**: `Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 --output results`

## Porting checks

**`planarsviz_checks/`** — twenty checks (twelve in R, eight in Python) that
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
check calls, not a check of its own.

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
- **Output**: `results/supercatalan_trees_n2.pdf` … `_n5_sample15.pdf`, and
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
- `results/nyan1308_random_tree_overlay.r` is the one generated R script
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
