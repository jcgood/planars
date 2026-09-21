# NonCollaborative/

Personal R/Python working area for the planars project — scripts, prototypes, domain data, and older files. **Not part of the main analysis pipeline.** Nothing here is imported by `planars/` or `coding/`.

This folder contains the precursor work that evolved into the main pipeline, plus ongoing exploratory analysis and visualization code, most of it now built around the Chichewa (nyan1308) laminar-family analysis described in `docs/VERIFICATION.md`.

## Do not run the old code

**Nothing under `OlderFiles/` may be run.** Not as a shortcut, not to see what a chart used to look like, not to regenerate something that seems missing.

This matters more here than the usual "don't use old code" warning, because the old code still works. `OlderFiles/planarsviz_superseded/` holds the R scripts the `planarsviz` package replaced, and they are kept deliberately: the porting checks run them to prove the package draws what they drew. The checks read each script's text and evaluate it in memory **with `ggsave` disabled**, so nothing is written. Run the same file with `Rscript` and `ggsave` is live — and it writes its old output straight over charts the package produced, under the same filenames, with nothing anywhere recording which program made the file you are now looking at.

`.Rprofile` enforces this: R started in `NonCollaborative/` refuses to run any file under `OlderFiles/` and says what to run instead. The escape hatch, for the rare deliberate case, is `PLANARS_RUN_ARCHIVED=1 Rscript <file>` — if you find yourself reaching for it, stop and check you are not about to overwrite a committed chart.

The same rule applies more loosely to the hand-written R at the top of `scripts/` (`constituencyforest-all.r`, `domainSignificance.r` and their siblings) and to `domainGenerationTests/`: those predate the current pipeline, are not guarded, and are there to be read rather than executed.

**To draw a chart, use the package.** `Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308`. To check one against the script it replaced, run its check in `scripts/planarsviz_checks/`.

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

- **`scripts/analysis/`** — the active Chichewa/nyan1308 pipeline: `laminar_analysis.py` (core laminar-family enumeration engine), `laminar_tree_counts.py` (family counts, pooled and per class), `boundary_strength.py` (per-juncture boundary strength), `class_fragmentation_test.py` + `fragmentation_test_plot.r` (is a class more fragmented than its test count predicts?), `refinement_counts.py` (how much tree structure each family leaves open), `planars_groupings.py` (the named domain-type bundles and filters, defined once), `random_tree_overlay.py` (ghost-overlay of sampled trees), and `export_planarsviz_data.py` (writes the data bundle the R package draws from). See `scripts/README_laminar_analysis.md` for the full walkthrough and `scripts/INDEX.md` for a per-script index.
- **`scripts/verification/`** — `verify_barthelmemy_correspondence.py` and `verify_chichewa.py` cross-check the laminar-family algorithm against independent methods (exhaustive search, alternate graph formulations). See `docs/VERIFICATION.md`.
- **`scripts/exploratory/`** — earlier prototypes kept for reference, not for new work: `treeTraversal.py` (superseded by `laminar_analysis.py`), `catalan.py`/`catalan_old.py` (Catalan-number tree enumeration), `generate_supercatalan_rows.py` + `render_supercatalan_rows.r` (super-Catalan tree-shape figures).
- **`scripts/planarsviz_checks/`** — twenty checks that the `planarsviz` package draws what the scripts it replaced drew, and that the exported bundle carries the same numbers the Python analysis produces. They are the evidence behind the port; they reach the archived originals through `superseded.R` (for the checks written in R) and `superseded.py` (for the ones in Python).
- **Top-level `scripts/*.r` and `scripts/*.py`** — `render_planarsviz.R` (draws every chart from a bundle — the only planarsviz code that writes files) and `planarsviz_compare.py` (its pixel-comparison helper); `make_forestspans_table.py` (the ForestSpans LaTeX table); older, hand-written R visualization scripts predating the laminar-family pipeline (`constituencyforest-all.r`, `morsynconstituencyforest-all.r`, `phonconstituencyforest-all.r`, `tonosegconstituencyforest-all.r`, `allsubtypes-forest-byhand.r`, `ColorTree-Example.r`, `domainSignificance.r`, `domain_charts-older.r` — an earlier variant of the pooled charts, whose successor `domain_charts-cgpt.r` has since moved to `OlderFiles/planarsviz_superseded/scripts/` along with `nyan_boundary_skyline.r`, both replaced by the `planarsviz` package); plus a few standalone utilities: `make_file.R` (builds an element index from planar structure files), `makeLaTeXDomains.py` (domains TSV → LaTeX table), `highlight_planar_example.py` and `make_planar_latex.py` (generate the highlighted planar-table/example-card PDFs under `results/`). `laminar_forest.r` is a generated forest script left over from before the port; it is archived with the rest in `OlderFiles/planarsviz_superseded/results/`.

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
- `planarsviz_guide.md` — user guide for the planarsviz chart library (`r/planarsviz/`): exporting a data bundle, drawing and rendering charts, adding a language, checking charts.
- `planarsviz_charts.md` — chart catalogue: every planarsviz chart, its function call, options, canvas and an example image (`planarsviz_charts/`).
- `PLAN_planarsviz_library.md` / `PLANARSVIZ_LIBRARY_PROGRESS.md` — why the library is built as it is, and the chart-by-chart record of how each port was checked, with open questions. **`PLANARSVIZ_LIBRARY_PROGRESS.md` is the current state of that work** — read it before resuming.
- `CHART_MECHANICS_AND_UNCERTAINTY.md` — how the charts encode what they encode, and what they do and don't establish.

### `examples/`

Glossed Chichewa examples (`nyan1308_*.yaml`) transcribed for use with `scripts/highlight_planar_example.py`, which renders each into a highlighted planar-table PDF and matching example card under `results/`.

### `readings/`

Reference PDFs cited in `REFERENCES.md` (currently: Barthélemy 1989, on the copair-hypergraph algorithm used as a cross-check in `scripts/verification/`).

### `results/`

Generated output — PDFs, `.tex` sources and `.tsv` data — plus `results/planarsviz/`, which holds the exported data bundle, the frozen reference images the porting checks compare against, and the comparison images those checks write. Both the reference and comparison images are grouped by topic into four subfolders (`laminar-families/`, `pooled/`, `boundaries/`, `counts-and-chance/`) rather than sitting flat — see `docs/planarsviz_guide.md` § 6. `results/visualizations.md` documents every chart and table here: what it shows, what produced it, and how to regenerate it. Keep that file in sync whenever something starts writing a new `results/` artifact.

The generated `.r` scripts that used to sit here beside the PDFs are gone: the `planarsviz` package draws the charts now, and those scripts are archived (see `OlderFiles/` below). The one exception is `nyan1308_random_tree_overlay.r`, which was never ported.

### `tests/`

A real `pytest` suite, run with `pytest NonCollaborative/tests/` from the repo root (or `pytest tests/` from inside `NonCollaborative/`). The root `pyproject.toml` sets `testpaths = ["tests"]`, so a bare `pytest` never reaches this directory — it has to be named.

**CI runs the part of it that needs no R**, as `pytest NonCollaborative/tests -m "not needs_r"`: the two bundle tests and the tree-traversal snapshots, about a minute. The rest is marked `needs_r` and stays a local step. That is not a gap waiting to be closed — the chart checks pixel-compare against reference images rendered on a Mac, and Linux fonts differ enough that every glyph would read as a changed pixel, so on a CI runner they would fail on charts that are perfectly fine.

Two of the R-dependent checks run on **pre-push** instead, where R and the pinned packages already are: `check-snapshots` always, and `roxygen-up-to-date` when anything under `r/planarsviz/` changed (about 7 seconds). See `.pre-commit-config.yaml`.

- `test_tree_traversal.py` runs `scripts/exploratory/treeTraversal.py` against each `domains/*.tsv` file and compares its output to the checked-in snapshots in `tests/snapshots/`; known-hanging inputs are marked `xfail` rather than fixed.
- `test_planarsviz_checks.py` runs all 21 porting checks in `scripts/planarsviz_checks/` and compares each one's whole output to a snapshot under `tests/snapshots/planarsviz_checks/`, so a drifted chart fails instead of printing a number nobody reads. Takes about 6m20s — most of it `R CMD INSTALL`, once per check. Skips cleanly without R, poppler or the project venv.
- `test_roxygen_up_to_date.py` fails if `r/planarsviz/`'s `NAMESPACE` or `man/` no longer match what roxygen2 would generate from `R/`.
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

**Run everything from `NonCollaborative/`.** That is where the porting checks run, what `scripts/INDEX.md` and `results/visualizations.md` document, and what the exported bundle records as the path it read. Two exceptions, both because the script reads a file from the working directory: `scripts/exploratory/render_supercatalan_rows.r` (run `generate_supercatalan_rows.py --pdf` instead, which launches it correctly), and `pytest`, which works from either the repo root (`pytest NonCollaborative/tests/`) or here (`pytest tests/`).

The `planarsviz` package's dependencies are in `r/planarsviz/DESCRIPTION`; `scripts/render_planarsviz.R` installs the package into a temporary library itself, so there is no install step. The tree charts also need `ape` and `ggtree`. The older hand-written R at the top of `scripts/` needs `ggplot2`, `ape`, `ggtree` and `patchwork` installed by hand.

**Which versions of those packages is pinned by `renv`.** `renv.lock` records all 130, `.Rprofile` makes R use them automatically whenever it starts here, and `renv::restore()` installs them on a machine that has never run this project. The lockfile deliberately covers more than `DESCRIPTION` does, because the porting checks run the archived scripts in `OlderFiles/planarsviz_superseded/` and those load `pacman`, `here`, `tidyverse` and `ggsci`. `.renvignore` lists the hand-written scripts renv does not read and says why. After changing what anything loads, run `renv::snapshot()` and commit the lockfile with the change. Full account: `docs/planarsviz_guide.md` § 7.

Python scripts depend on packages already in the main project's `.venv` (`requirements.txt`): `pandas`, `numpy`, `networkx`, `pyyaml`. `tests/` additionally needs `pytest`. Nothing here uses `matplotlib` any more — C3 removed the last of it.
