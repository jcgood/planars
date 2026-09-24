# NonCollaborative/

Personal R/Python working area for the planars project — scripts, prototypes, domain data, and older files. **Not part of the main analysis pipeline.** Nothing here is imported by `planars/` or `coding/`.

This folder contains the precursor work that evolved into the main pipeline, plus ongoing exploratory analysis and visualization code, most of it now built around the Chichewa (nyan1308) laminar-family analysis described in `docs/VERIFICATION.md`.

## Do not run the old code

**Nothing under `OlderFiles/` may be run.** Not as a shortcut, not to see what a chart used to look like, not to regenerate something that seems missing.

This matters more here than the usual "don't use old code" warning, because the old code still works. `OlderFiles/planarsviz_superseded/` holds the R scripts the `planarsviz` package replaced, and they are kept deliberately: the porting checks run them to prove the package draws what they drew. The checks read each script's text and evaluate it in memory **with `ggsave` disabled**, so nothing is written. Run the same file with `Rscript` and `ggsave` is live — and it writes its old output straight over charts the package produced, under the same filenames, with nothing anywhere recording which program made the file you are now looking at.

`.Rprofile` enforces this: R started in `NonCollaborative/` refuses to run any file under `OlderFiles/` and says what to run instead. The escape hatch, for the rare deliberate case, is `PLANARS_RUN_ARCHIVED=1 Rscript <file>` — if you find yourself reaching for it, stop and check you are not about to overwrite a committed chart.

The same rule applies more loosely to the hand-written R at the top of `scripts/` (`constituencyforest-all.r`, `domainSignificance.r` and their siblings) and to `domainGenerationTests/`: those predate the current pipeline, are not guarded, and are there to be read rather than executed.

**To draw a chart, use the package.** `python scripts/planarsviz_language.py <dataset> --apply` exports a language's bundle and draws every chart from it; `Rscript scripts/render_planarsviz.R --bundle results/chart_data/nyan1308` redraws from an existing bundle. To check one against the script it replaced, run its check in `scripts/planarsviz_checks/`.

## Relationship to the main pipeline

Several scripts here are early versions of code that was later formalized:

| Here | Main pipeline equivalent |
|------|--------------------------|
| `domainGenerationTests/ciscategorial.py` | `planars/ciscategorial.py` |
| `domainGenerationTests/make_forms.py` | `coding/make_forms.py` |
| `domainGenerationTests/early/makeDomains.py` | `planars/` analysis modules generally |

The versions here are historical prototypes. For the canonical implementation, use the main pipeline.

## Directory structure

### `domains/`

TSV files containing constituency test results from the Constituency and Convergence Database (CCDB). Each row is one test result for one language; columns include span edges, domain type, fracture types, convergence metrics, and test labels.

- `domains.tsv` — Master dataset (all languages, ~464 rows)
- `domains_nyan1308.tsv` — Chichewa (Bantu)
- `domains_nyan1293_test.tsv` — Test fixture (not a real language dataset)
- `domains_chac.tsv` — Chácobo (Pano)
- `domains_yupik.tsv` — Yupik (Eskimo-Aleut)
- `domains_mart.tsv` — Martuthunira (Pama-Nyungan)
- `domains_quech.tsv` — Quechua
- `catalanPlus.tsv` — Catalan
- `SparseNotes.txt` — Brainstorming notes on visualization approaches
- `tests.txt` — Mapping of constructions to test classes
- `testClasses.txt` — Definitions of test class features

### `planar_tables/`

Planar structure files (slot/position templates for each language's morphosyntactic template).

- `planar_stan1293.tsv` — Canonical planar structure for Standard English (19 positions)
- `planar_nyan1308.tsv` — Planar structure for Chichewa

Older timestamped CSV snapshots are archived in `OlderFiles/planar_tables/`.

### `scripts/`

R and Python scripts for analysis and visualization. These are run interactively, not from the pipeline. As of the current laminar-family work, `scripts/` is organized into subfolders rather than kept flat:

- **`scripts/analysis/`** — the active Chichewa/nyan1308 pipeline: `laminar_analysis.py` (core laminar-family enumeration engine), `laminar_tree_counts.py` (family counts, pooled and per class), `boundary_strength.py` (per-juncture boundary strength), `class_fragmentation_test.py` (is a class more fragmented than its test count predicts? — its charts come from the package), `span_placement_test.py` and `arbitrary_layers_test.py` (the project's two other permutation nulls, each weaker than the last — see `arbitrary_layers_test.py`'s docstring for how the three relate), `refinement_counts.py` (how much tree structure each family leaves open), `planars_groupings.py` (the named domain-type bundles and filters, defined once), `export_planarsviz_illustrations.py` (writes the one bundle with no language behind it: tree shapes, Catalan/little-Schröder count growth, and a uniformly-random tree sample, phase E, 2026-09-22), and `export_planarsviz_data.py` (writes the data bundle the R package draws from). See `scripts/README_laminar_analysis.md` for the full walkthrough and `scripts/INDEX.md` for a per-script index.
- **`scripts/verification/`** — `verify_barthelmemy_correspondence.py` and `verify_chichewa.py` cross-check the laminar-family algorithm against independent methods (exhaustive search, alternate graph formulations). See `docs/VERIFICATION.md`.
- **`scripts/exploratory/`** — `catalan.py` is the one live exception in this folder: still-used counting, enumeration and uniform-sampling code for n-ary trees (`export_planarsviz_illustrations.py` imports it directly), not a kept-for-reference prototype. Everything else here is: `treeTraversal.py` (superseded by `laminar_analysis.py`), `catalan_old.py` (superseded by `catalan.py`), `max_fragmentation_search.py` + `max_fragmentation_describe.py` (how fragmented a covering of N arbitrary layers *can* get — a search for a bound, not a test; its committed 1238 figure is for a superseded layer count).
- **`scripts/planarsviz_checks/`** — twenty-three checks that the `planarsviz` package draws what the scripts it replaced drew, and that the exported bundle carries the same numbers the Python analysis produces. They are the evidence behind the port; they reach the archived originals through `superseded.R` (for the checks written in R) and `superseded.py` (for the ones in Python).
- **Top-level `scripts/*.r` and `scripts/*.py`** — `render_planarsviz.R` (draws every chart from a bundle — the only planarsviz code that writes files), `planarsviz_language.py` (one language in one step: runs the exporter and then `render_planarsviz.R` with that language's settings) and `planarsviz_compare.py` (its pixel-comparison helper); `make_forestspans_table.py` (the ForestSpans LaTeX table); older, hand-written R visualization scripts predating the laminar-family pipeline (`constituencyforest-all.r`, `morsynconstituencyforest-all.r`, `phonconstituencyforest-all.r`, `tonosegconstituencyforest-all.r`, `allsubtypes-forest-byhand.r`, `ColorTree-Example.r`, `domainSignificance.r`, `domain_charts-older.r` — an earlier variant of the pooled charts, whose successor `domain_charts-cgpt.r` has since moved to `OlderFiles/planarsviz_superseded/scripts/` along with `nyan_boundary_skyline.r`, both replaced by the `planarsviz` package); plus a few standalone utilities: `make_file.R` (builds an element index from planar structure files), `makeLaTeXDomains.py` (domains TSV → LaTeX table), `highlight_planar_example.py` and `make_planar_latex.py` (generate the highlighted planar-table/example-card PDFs under `results/`). `laminar_forest.r` is a generated forest script left over from before the port; it is archived with the rest in `OlderFiles/planarsviz_superseded/results/`.

**Nothing under `scripts/` writes an R script or a matplotlib figure any more.** Charts come from the `planarsviz` package reading a bundle: `export_planarsviz_data.py` writes the bundle, `render_planarsviz.R` draws from it. That happened in the 2026-09-20 cutover; the scripts the package replaced are archived under `OlderFiles/planarsviz_superseded/` and **must not be deleted** (see below).

`scripts/INDEX.md` and `scripts/README_laminar_analysis.md` are the authoritative, actively-maintained guides to the `analysis/`/`verification/`/`exploratory/`/`planarsviz_checks/` scripts — read those for algorithm details and usage rather than this file.

### `domainGenerationTests/`

Early prototypes for domain derivation from linguistic parameter files. Represents the pre-pipeline exploratory phase.

- `ciscategorial.py` — Early ciscategorial domain derivation. Precursor to `planars/ciscategorial.py`.
- `make_forms.py` — Generates parameter template files for different test types. Precursor to `coding/make_forms.py`.
- `ciscategorial_parameters.tsv` — Parameter header template (V-combines, N-combines, A-combines).
- `ciscategorial_stan1293_filled.tsv` — Filled parameter matrix for English (11 positions × 3 parameters).
- `ciscategorial_stan1293_blank.tsv` — Blank template version of the above.
- `planar_stan1293.tsv` — Reference planar structure used by these scripts.
- `early/` — Earlier iterations: `makeDomains.py` (construction-based domain generation), `planar_stan1293.tsv`, `construction_domains.txt`.

### `docs/`

- `VERIFICATION.md` — methodology, theoretical framework, and verified results for the laminar-family analysis (the two independent algorithms that both confirm 69 maximal families for nyan1308).
- `planarsviz_guide.md` — user guide for the planarsviz chart library (`planarsviz/`): exporting a data bundle, drawing and rendering charts, adding a language, checking charts.
- `planarsviz_charts.md` — chart catalogue: every planarsviz chart, its function call, options, canvas and an example image (`planarsviz_charts/`).
- `PLAN_planarsviz_library.md` / `PLANARSVIZ_LIBRARY_PROGRESS.md` — why the library is built as it is, and the chart-by-chart record of how each port was checked, with open questions. **`PLANARSVIZ_LIBRARY_PROGRESS.md` is the current state of that work** — read it before resuming.
- `PLAN_ccdb_planarsviz.md` / `CCDB_PLANARSVIZ_PROGRESS.md` — putting the 21 planar structures of the Constituency and Convergence Database (imported by `scripts/analysis/import_ccdb.py` into `domains/` and `planar_tables/` as `*_<Planar_ID>.*`) through the same analysis and charts as nyan1308. **`CCDB_PLANARSVIZ_PROGRESS.md` is the current state of that work** — read it before resuming.
- `PLAN_planarsviz_doc_fixes.md` — the 2026-09-22 documentation gaps; carried out in `ae0f9cb`, kept as the record.
- `CHART_MECHANICS_AND_UNCERTAINTY.md` — how the charts encode what they encode, and what they do and don't establish.

### `examples/`

Glossed Chichewa examples (`nyan1308_*.yaml`) transcribed for use with `scripts/highlight_planar_example.py`, which renders each into a highlighted planar-table PDF and matching example card under `results/planar-structure/`.

### `readings/`

Reference PDFs cited in `REFERENCES.md` (currently: Barthélemy 1989, on the copair-hypergraph algorithm used as a cross-check in `scripts/verification/`).

### `results/`

Generated output — PDFs, `.tex` sources and `.tsv` data — plus `results/chart_data/`, which holds the exported data bundle, and `results/chart_checks/`, which holds the frozen reference images the porting checks compare against and the comparison images those checks write.

**`results/` is grouped by language first, then by topic — except the one dataset with no language.** The four topic folders a `planarsviz` chart can land in for a real language — `laminar-families/`, `pooled/`, `boundaries/`, `counts-and-chance/` — sit under a per-language folder (`results/nyan1308/`), so a second language's charts land beside nyan1308's rather than colliding with them (2026-09-22). `illustrations/` is also `planarsviz`-drawn (phase E, 2026-09-22) but stays flat rather than nesting a topic folder inside it: that bundle has exactly one topic, itself, so its charts' `planarsviz_folder` is `""` and they land directly in `results/illustrations/`. `planar-structure/` is unrelated to the `planarsviz` package entirely and also sits flat. Only `visualizations.md` (and `ccdb_batch/`, the CCDB batch's logs and summary) sit at the very top alongside these folders; each dataset's `<dataset>_planarsviz_manifest.tsv` sits inside its own folder (`results/nyan1308/`, `results/illustrations/`), with file paths relative to that folder (2026-09-23). The reference and comparison images under `results/chart_checks/` mirror the same layout (`reference/nyan1308/<topic>/`, `reference/illustrations/` flat) — see `docs/planarsviz_guide.md` § 6.

**Which folder a chart belongs to is recorded in exactly one place:** a `planarsviz_folder` attribute on the object each chart function returns, beside the `planarsviz_size` attribute that gives its canvas. The renderer reads it to decide where to write, the manifest's `file` column carries the result, and the porting checks find a chart's reference image at that same address. Nothing keeps a second copy of the mapping, so adding a chart means setting one attribute.

`results/visualizations.md` documents every chart and table here: what it shows, what produced it, and how to regenerate it. Keep that file in sync whenever something starts writing a new `results/` artifact.

The generated `.r` scripts that used to sit here beside the PDFs are gone: the `planarsviz` package draws the charts now, and those scripts are archived (see `OlderFiles/` below). Phase E (2026-09-22) absorbed the last one, `illustrations/nyan1308_random_tree_overlay.r` — no generated script writes into `results/` any more.

### `tests/`

A real `pytest` suite, run with `pytest NonCollaborative/tests/` from the repo root (or `pytest tests/` from inside `NonCollaborative/`). The root `pyproject.toml` sets `testpaths = ["tests"]`, so a bare `pytest` never reaches this directory — it has to be named.

**CI runs the part of it that needs no R**, as `pytest NonCollaborative/tests -m "not needs_r"`: the two bundle tests and the tree-traversal snapshots, about a minute. The rest is marked `needs_r` and stays a local step. That is not a gap waiting to be closed — the chart checks pixel-compare against reference images rendered on a Mac, and Linux fonts differ enough that every glyph would read as a changed pixel, so on a CI runner they would fail on charts that are perfectly fine.

Two of the R-dependent checks run on **pre-push** instead, where R and the pinned packages already are: `check-snapshots` always, and `roxygen-up-to-date` when anything under `planarsviz/` changed (about 7 seconds). See `.pre-commit-config.yaml`.

- `test_tree_traversal.py` runs `scripts/exploratory/treeTraversal.py` against each `domains/*.tsv` file and compares its output to the checked-in snapshots in `tests/snapshots/`; known-hanging inputs are marked `xfail` rather than fixed.
- `test_planarsviz_checks.py` runs all 23 porting checks in `scripts/planarsviz_checks/` and compares each one's whole output to a snapshot under `tests/snapshots/planarsviz_checks/`, so a drifted chart fails instead of printing a number nobody reads. Takes about 6m20s — most of it `R CMD INSTALL`, once per check. Skips cleanly without R, poppler or the project venv.
- `test_roxygen_up_to_date.py` fails if `planarsviz/`'s `NAMESPACE` or `man/` no longer match what roxygen2 would generate from `R/`.
- `test_archived_scripts_refuse_to_run.py` checks that `.Rprofile` still blocks a direct `Rscript` run of anything under `OlderFiles/`, that `PLANARS_RUN_ARCHIVED=1` still overrides it, and that scripts outside the archive are unaffected. It drives a throwaway probe file, not a real archived script — proving the guard by running something it is meant to stop would write the very charts it protects.
- `test_planarsviz_bundle.py` and `test_planarsviz_shifted_bundle.py` check the exported data bundles.

Run `pytest --update-snapshots` to regenerate snapshots after a deliberate output change — then read the diff before committing it. A snapshot updated without being read is worse than no snapshot, because it looks like evidence.

### `OlderFiles/`

Archived scripts and data kept for historical reference. See `OlderFiles/README.md`. Do not use for new work.

One exception: `OlderFiles/planarsviz_superseded/` holds the R scripts the `planarsviz` package replaced, and **those must not be deleted**. The porting checks run them to prove the package draws the same charts, so they are the evidence behind every "0.0000% differing pixels" claim in the progress file, and most of them can no longer be regenerated: cutover step C3 removed the Python that wrote them.

## Data provenance

The `domains/` TSV files are drawn from the **Constituency and Convergence Database (CCDB)**. Methodology documented in:

- Tallman (2021): "Constituency and Convergence in Chácobo." *Studies in Language* 45(2).
- Tallman (in press): Introduction to *Constituency and Convergence in the Americas* (Language Science Press, langsci/291).
- Auderset et al. (in press): Discussion chapter in the same volume.

License: CC BY-SA 4.0.

See also `REFERENCES.md` for the mathematical/linguistic literature behind the laminar-family analysis, and `readings/` for the PDFs it cites.

## Running scripts

**Run everything from `NonCollaborative/`.** That is where the porting checks run, what `scripts/INDEX.md` and `results/visualizations.md` document, and what the exported bundle records as the path it read. The one exception is `pytest`, which works from either the repo root (`pytest NonCollaborative/tests/`) or here (`pytest tests/`).

The `planarsviz` package's dependencies are in `planarsviz/DESCRIPTION`; `scripts/render_planarsviz.R` installs the package into a temporary library itself, so there is no install step. The tree charts also need `ape` and `ggtree`. The older hand-written R at the top of `scripts/` needs `ggplot2`, `ape`, `ggtree` and `patchwork` installed by hand.

**Which versions of those packages is pinned by `renv`.** `renv.lock` records all 130, `.Rprofile` makes R use them automatically whenever it starts here, and `renv::restore()` installs them on a machine that has never run this project. The lockfile deliberately covers more than `DESCRIPTION` does, because the porting checks run the archived scripts in `OlderFiles/planarsviz_superseded/` and those load `pacman`, `here`, `tidyverse` and `ggsci`. `.renvignore` lists the hand-written scripts renv does not read and says why. After changing what anything loads, run `renv::snapshot()` and commit the lockfile with the change. Full account: `docs/planarsviz_guide.md` § 7.

Python scripts depend on packages already in the main project's `.venv` (`requirements.txt`): `pandas`, `numpy`, `networkx`, `pyyaml`. `tests/` additionally needs `pytest`. Nothing here uses `matplotlib` any more — C3 removed the last of it.
