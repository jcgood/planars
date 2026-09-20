# Scripts Index

This directory contains Python and R scripts for laminar family analysis and verification.

## Core Analysis

**`analysis/laminar_analysis.py`**
- **Purpose**: Main workhorse for laminar family enumeration
- **Input**: Domain span TSV file (`../../domains/domains_{lang_id}.tsv`)
- **Algorithm**: Four-phase approach:
  1. Conflict detection (O(n²)) — classify span pairs as nested/disjoint/conflict
  2. Bron-Kerbosch enumeration (complement graph) — find all maximal independent sets
  3. Tree construction — build parent maps and Newick trees
  4. Analysis — test three hypotheses (Tree, Morphosyntax/Phonology divide, Word)
- **Output**: 
  - `../../results/{lang_id}_laminar_forest.r` — R visualization of all families
  - `../../results/{lang_id}_laminar_analysis.md` — markdown summary
  - Console output with statistics
- **Dependencies**: Standard library only
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
- **Example**: `Rscript scripts/analysis/fragmentation_test_plot.r`

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

## Verification (New)

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

## Visualization (R) — Generated Output

**`../../results/laminar_forest.r`** (GENERATED)
- Outputs: `laminar_forest.pdf`
- Visualization of all maximal laminar families as dendrogram forest
- Branch thickness = convergence strength (√families_containing_span)

**`../../results/laminar_conflict_groups.r`** (GENERATED)
- Outputs: `laminar_conflict_groups.pdf`
- Categorizes families by conflict patterns
- Three-panel comparative visualization

**Other `../../results/*.r` files** (GENERATED)
- Language-specific overlays, frequency analysis, etc.
- All generated by `laminar_analysis.py` — not hand-written

---

## Organization Guide

- **analysis/** — Core algorithms (`laminar_analysis.py`)
- **verification/** — Verification scripts (`verify_*.py`)
- **exploratory/** — Prototype and archive work (`treeTraversal.py`, `catalan.py`)

See `../docs/VERIFICATION.md` for methodology, results, and theoretical framework.
