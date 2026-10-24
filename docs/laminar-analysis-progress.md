# Progress: the laminar analysis for any language

The plan and its decisions are `docs/laminar-analysis-plan.md`. This file is
the current state; update it at every phase boundary, in the same commit.

| Phase | Status |
|---|---|
| 1. Take out the Chichewa assumptions, in place | done 2026-10-24 |
| 2. Move the code (`laminar/`, `planarsviz/` to the root) | not started |
| 3. Connect a planars language (adapter, *k of n*, metadata) | not started |
| 4. Run English; one command for Adam's Claude | not started |
| 5. Documentation and tests | not started |

## Phase 1 as built (2026-10-24)

- **Groups are built in one place.** `planars_groupings.py` holds
  `CLASS_ORDER` (was copied in four scripts) and `observed_groups()` /
  `permutation_groups()`: a dataset's own domain types and the bundles of
  its grouping that it has data for, in a fixed order. The exporter (five
  copies of that code before) and every standalone script use them.
- **`datasets.py` (new) says what a dataset name means:** its domains file,
  planar table and position count, and its settings (`dataset_settings()`,
  moved from `planarsviz_language.py`), plus the command-line options the
  standalone scripts share. A script run on its own now picks the
  dataset's groupings (`ccdb` for a CCDB structure), uses the planar
  table's position count where the exporter does, and writes
  `results/<dataset>/<topic>/<dataset>_*`.
- **Checked:** all 22 bundles re-exported with all four permutation tests,
  and the seven standalone scripts re-run on nyan1308 into their committed
  paths: every file came back byte-identical. The three tests that crashed
  on CCDB data run on chac1251_verbal. Renderer check and the no-R analysis
  tests pass.

## Findings

- `laminar_analysis.py`'s printed report now lists domain types in
  `CLASS_ORDER` rather than the forest order; it writes no file, so nothing
  committed changed.
