# NonCollaborative/

Personal R/Python working area for the planars project — scripts, prototypes, domain data, and older files. **Not part of the main analysis pipeline.** Nothing here is imported by `planars/` or `coding/`.

This folder contains the precursor work that evolved into the main pipeline, plus ongoing exploratory analysis and visualization code.

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
- `domains_nyan1308.tsv` — Nyangatom (Nilotic)
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

Older timestamped CSV snapshots are archived in `OlderFiles/planar_tables/`.

### `scripts/`

R and Python scripts for analysis and visualization. These are run interactively, not from the pipeline.

**R scripts (ggplot2/ggtree-based visualization)**:
- `domain_charts.r` — Reads `domains/domains.tsv`; plots constituency spans across the planar structure, colored by domain type. Core visualization script.
- `domain_charts-cgpt.r` — ChatGPT-assisted variant of `domain_charts.r`.
- `constituencyforest-all.r` — Phylogenetic-style tree plots showing domain nesting relationships; line thickness encodes domain strength.
- `morsynconstituencyforest-all.r` — Morphosyntactic-specific forest plot.
- `phonconstituencyforest-all.r` — Phonological-specific forest plot.
- `tonosegconstituencyforest-all.r` — Tonosegmental-specific forest plot.
- `allsubtypes-forest-byhand.r` — Hand-crafted forest plot with specific orderings.
- `ColorTree-Example.r` — Reference code for tree coloring techniques.
- `domainSignificance.r` — Statistical significance testing for domain patterns.
- `make_file.R` — Builds an element index from planar structure files; maps elements to position numbers. Reads TSVs with columns: Class_Type, Elements, Position_Name.

**Python scripts**:
- `treeTraversal.py` — Analyzes constituency domains; builds and reduces tree structures; tracks domain strength (convergence counts); outputs tree statistics and visualization.
- `catalan.py` — Enumerates all possible binary tree structures for a given number of items (Catalan number generator). Used to explore the space of possible constituency structures.
- `makeLaTeXDomains.py` — Converts a domains TSV to a LaTeX tabular table for publication output.

### `domainGenerationTests/`

Early prototypes for domain derivation from linguistic parameter files. Represents the pre-pipeline exploratory phase.

- `ciscategorial.py` — Early ciscategorial domain derivation. Precursor to `planars/ciscategorial.py`.
- `make_forms.py` — Generates parameter template files for different test types. Precursor to `coding/make_forms.py`.
- `ciscategorial_parameters.tsv` — Parameter header template (V-combines, N-combines, A-combines).
- `ciscategorial_stan1293_filled.tsv` — Filled parameter matrix for English (11 positions × 3 parameters).
- `ciscategorial_stan1293_blank.tsv` — Blank template version of the above.
- `planar_stan1293.tsv` — Reference planar structure used by these scripts.
- `early/` — Earlier iterations: `makeDomains.py` (construction-based domain generation), `planar_stan1293.tsv`, `construction_domains.txt`.

### `OlderFiles/`

Archived scripts and data kept for historical reference. See `OlderFiles/README.md`. Do not use for new work.

## Data provenance

The `domains/` TSV files are drawn from the **Constituency and Convergence Database (CCDB)**. Methodology documented in:

- Tallman (2021): "Constituency and Convergence in Chácobo." *Studies in Language* 45(2).
- Tallman (in press): Introduction to *Constituency and Convergence in the Americas* (Language Science Press, langsci/291).
- Auderset et al. (in press): Discussion chapter in the same volume.

License: CC BY-SA 4.0.

## Running scripts

R scripts require `ggplot2`, `ape`, `ggtree`. No package management file — install manually.

Python scripts have no external dependencies beyond the standard library.

Scripts read data files using relative paths from their own location (or a configured `DATA_DIR`). Run from the script's directory or adjust paths as needed.
