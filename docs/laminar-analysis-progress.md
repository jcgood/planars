# Progress: the laminar analysis for any language

The plan and its decisions are `docs/laminar-analysis-plan.md`. This file is
the current state; update it at every phase boundary, in the same commit.

| Phase | Status |
|---|---|
| 1. Take out the Chichewa assumptions, in place | done 2026-10-24 |
| 2. Move the code (`laminar/`, `planarsviz/` to the root) | done 2026-10-24 |
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

## Phase 2 as built (2026-10-24)

- **`laminar/` is a package at the repo root**, installed by `pip install -e .`
  (`pyproject.toml` lists it). The fourteen analysis modules kept their names
  and import each other as `laminar.*`; `catalan.py` came along from
  `scripts/exploratory/` because the illustrations exporter and
  `refinement_counts.py` use it. Each module runs on its own from anywhere
  (`python -m laminar.<module>`). `datasets.py` owns the two paths, `REPO`
  and `NC` (`NonCollaborative/`, where Chichewa's and the CCDB structures'
  inputs and outputs stay, decision 8); nothing else works out a path from
  its own location.
- **One command**, `python -m laminar charts <dataset>` (or `--ccdb` for all
  21 structures, with the batch summary), replaces `planarsviz_language.py`
  and `planarsviz_ccdb_batch.py`, both deleted. `laminar/render_planarsviz.R`
  is the renderer, run from the repo root.
- **`planarsviz/` and renv are at the root**: `renv.lock`, `renv/`,
  `_dependencies.R`, `lint_and_style_planarsviz.R`, a new `.renvignore` (renv
  reads only the folders with R code: 72 files, not 4,009) and the root
  `.Rprofile`, which holds the archive guard (now pointed at
  `NonCollaborative/OlderFiles/`) and starts renv. `NonCollaborative/.Rprofile`
  hands over to it, so the porting checks, which stay in `NonCollaborative/`,
  get the same packages and guard; the guard test now runs from both folders.
- **A bundle records its input files relative to the repo root**
  (`NonCollaborative/domains/...`), so it no longer depends on where the
  exporter ran; `producer` and `analysis_source` name `laminar/`. That covers
  the planar, labels and conflict-group paths as well as the domain file the
  plan mentioned.
- **Checked:** nyan1308, the 21 CCDB structures and the shifted test bundle
  re-exported with their permutation tests: every data table byte-identical;
  in metadata only those path and producer fields changed (checked by
  script). The illustrations bundle came back byte-identical. All charts were
  redrawn: 1,404 PDFs differ from the committed ones only in their date
  stamp, and the 24 drawn with Quartz (IPA labels in ayau1235_verbal and
  moco1246_verbal) are pixel-identical, so the committed PDFs were kept.
  Roxygen, lintr, styler, guard and no-R NonCollaborative tests pass;
  `tests/test_no_leftovers.py` now covers `laminar/`.
- **Side fixes:** `matplotlib` dropped from `requirements.in` (nothing imports
  it since the charts moved to R); the shifted bundle's documented export
  command now includes the `--fragmentation-permutations 5000` it was made
  with.

## Findings

- `check_forestspans.R` had failed since 2026-09-23 without anyone seeing it
  (the R checks run only locally): `expand_limits(x = 1)`, added then so the
  axis always starts at 1, gives the library's chart an extra, invisible
  layer, and the check compared layer counts. The check now leaves blank
  layers out of the comparison; its output matches the snapshot again
  (2026-10-24). Lesson: after a chart change, run
  `pytest NonCollaborative/tests` (the R checks), not only the renderer check.

- `laminar_analysis.py`'s printed report now lists domain types in
  `CLASS_ORDER` rather than the forest order; it writes no file, so nothing
  committed changed.
