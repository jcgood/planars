# NonCollaborative/

Personal R/Python working area for the planars project — scripts, prototypes, domain data, and older files. **Not part of the main analysis pipeline.** Nothing here is imported by `planars/` or `coding/`.

This folder contains the precursor work that evolved into the main pipeline, plus ongoing exploratory analysis and visualization code, most of it now built around the Chichewa (nyan1308) laminar-family analysis described in `docs/VERIFICATION.md`.

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

- **`scripts/analysis/`** — the active Chichewa/nyan1308 pipeline: `laminar_analysis.py` (core laminar-family enumeration engine), `laminar_tree_counts.py` (family-count bar charts), `random_tree_overlay.py` (ghost-overlay of sampled trees). See `scripts/README_laminar_analysis.md` for the full walkthrough and `scripts/INDEX.md` for a per-script index.
- **`scripts/verification/`** — `verify_barthelmemy_correspondence.py` and `verify_chichewa.py` cross-check the laminar-family algorithm against independent methods (exhaustive search, alternate graph formulations). See `docs/VERIFICATION.md`.
- **`scripts/exploratory/`** — earlier prototypes kept for reference, not for new work: `treeTraversal.py` (superseded by `laminar_analysis.py`), `catalan.py`/`catalan_old.py` (Catalan-number tree enumeration), `generate_supercatalan_rows.py` + `render_supercatalan_rows.r` (super-Catalan tree-shape figures).
- **Top-level `scripts/*.r` and `scripts/*.py`** — older, largely hand-written R visualization scripts predating the laminar-family pipeline (`constituencyforest-all.r`, `morsynconstituencyforest-all.r`, `phonconstituencyforest-all.r`, `tonosegconstituencyforest-all.r`, `allsubtypes-forest-byhand.r`, `ColorTree-Example.r`, `domainSignificance.r`, `domain_charts-older.r` — an earlier variant, since superseded by `domain_charts-cgpt.r` — and `nyan_boundary_skyline.r`), plus a few standalone utilities: `make_file.R` (builds an element index from planar structure files), `makeLaTeXDomains.py` (domains TSV → LaTeX table), `highlight_planar_example.py` and `make_planar_latex.py` (generate the highlighted planar-table/example-card PDFs under `results/`).

`scripts/INDEX.md` and `scripts/README_laminar_analysis.md` are the authoritative, actively-maintained guides to the `analysis/`/`verification/`/`exploratory/` scripts — read those for algorithm details and usage rather than this file.

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
- `PLAN_planarsviz_library.md` / `PLANARSVIZ_LIBRARY_PROGRESS.md` — why the library is built as it is, and the chart-by-chart record of how each port was checked, with open questions.

### `examples/`

Glossed Chichewa examples (`nyan1308_*.yaml`) transcribed for use with `scripts/highlight_planar_example.py`, which renders each into a highlighted planar-table PDF and matching example card under `results/`.

### `readings/`

Reference PDFs cited in `REFERENCES.md` (currently: Barthélemy 1989, on the copair-hypergraph algorithm used as a cross-check in `scripts/verification/`).

### `results/`

Generated output — PDFs, `.tex` sources, `.tsv` data, and the `.r` scripts that produced them. `results/visualizations.md` documents every chart and table here: what it shows, which script generates it, and how to regenerate it. Keep that file in sync whenever a script here starts writing a new `results/` artifact.

### `tests/`

A real `pytest` suite, run with `pytest NonCollaborative/tests/` from the repo root (or `pytest tests/` from inside `NonCollaborative/`). `test_tree_traversal.py` runs `scripts/exploratory/treeTraversal.py` against each `domains/*.tsv` file and compares its output to the checked-in snapshots in `tests/snapshots/`; known-hanging inputs are marked `xfail` rather than fixed. Run `pytest --update-snapshots` to regenerate snapshots after a deliberate output change.

### `OlderFiles/`

Archived scripts and data kept for historical reference. See `OlderFiles/README.md`. Do not use for new work.

## Data provenance

The `domains/` TSV files are drawn from the **Constituency and Convergence Database (CCDB)**. Methodology documented in:

- Tallman (2021): "Constituency and Convergence in Chácobo." *Studies in Language* 45(2).
- Tallman (in press): Introduction to *Constituency and Convergence in the Americas* (Language Science Press, langsci/291).
- Auderset et al. (in press): Discussion chapter in the same volume.

License: CC BY-SA 4.0.

See also `REFERENCES.md` for the mathematical/linguistic literature behind the laminar-family analysis, and `readings/` for the PDFs it cites.

## Running scripts

R scripts require `ggplot2`, `ape`, `ggtree`, `patchwork`. No package management file — install manually.

Python scripts mostly use the standard library, but some depend on third-party packages already in the main project's `.venv` (`requirements.txt`): `pandas`, `networkx`, `matplotlib`, `pyyaml`. `tests/` additionally needs `pytest`.

Scripts read data files using relative paths from their own location (or a configured `DATA_DIR`). Run from the script's directory (e.g. `cd scripts/analysis`) or adjust paths as needed.
