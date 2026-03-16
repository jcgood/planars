# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the scripts

```bash
# Generate blank test forms from planar structure + diagnostics
cd 01_planar_input && python make_forms.py

# Run a single analysis via the CLI (from repo root)
python -m planars ciscategorial 02_ciscategorial_output/ciscategorial_stan1293_general_filled.tsv
python -m planars subspanrepetition 03_subspanrepetition_output/subspanrepetition_stan1293_andCoordination_full.tsv
python -m planars noninterruption 04_noninterruption/noninterruption_stan1293_general_fill.tsv

# Or run a module directly from its own folder
cd 02_ciscategorial_output && python ciscategorial.py

# Regression testing
python generate_snapshots.py   # regenerate baseline snapshots
python check_snapshots.py      # verify current output matches snapshots
```

Dependencies: `pandas` (standard library otherwise). No build system or linter is configured.

## Architecture and data flow

This is a linguistic typology analysis project for morphosyntactic domain derivation. The workflow is:

1. **Input** (`01_planar_input/`): `planar_<lang>-<date>.tsv` defines positions and elements for a language. `diagnostics.tsv` specifies which analyses to run (class, construction, parameters). `make_forms.py` reads both and generates blank test TSVs — one per (class, construction) combination.

2. **Manual annotation**: Linguists fill in y/n values in the blank TSVs for each element/position row.

3. **Analysis modules** (folders `02`–`04`): Each reads a filled TSV and derives spans. All share the same core span logic in `planars/spans.py`:
   - **Keystone position**: Identified by `Position_Name == 'v:verbroot'`; anchors all span computations.
   - **Partial positions**: ≥1 element in the position qualifies.
   - **Complete positions**: ALL elements in the position qualify.
   - **Strict span**: Contiguous expansion from keystone (no gaps).
   - **Loose span**: Extends to farthest qualifying position on each side regardless of gaps.

4. **Analysis modules in detail**:
   - `ciscategorial.py`: A position qualifies if elements have `V-combines=y` and all other params `=n`. Returns 4 spans (strict/loose × complete/partial).
   - `subspanrepetition.py`: 5 span categories (fillable, widescope_left/right, narrowscope_left/right), each with 4 spans = 20 total.
   - `noninterruption.py`: Two domain types (no-free: `free=n`; single-free: `free=n` or `free=y,multiple=n`), each with complete/partial = 4 strict spans.

## Package structure

`planars/` is a shared library:
- `spans.py`: `strict_span`, `loose_span`, `position_sets_from_element_mask` — imported by all analysis modules.
- `cli.py` + `__main__.py`: CLI entry point (`python -m planars <analysis> <tsv>`).

Each analysis module exposes two public functions: `derive_*()` returns a result dict, and `format_result()` returns a formatted string for display or snapshot comparison.

`generate_snapshots.py` and `check_snapshots.py` at the repo root drive regression testing. Snapshots live in `tests/snapshots/`.

## NonCollaborative/

Personal working area not part of the shared analysis pipeline:

- `make_file.R` — R equivalent of `make_forms.py`
- `domains/` — domain TSV files for various languages (Chac, Mart, Nyan, Quech, Yupik, etc.)
- `domainGenerationTests/` — earlier prototypes of the analysis scripts
- `planar_tables/` — CSV/TSV versions of the planar structure for stan1293
- `scripts/` — active R and Python scripts for visualization and analysis (constituency forests, domain charts, tree traversal, etc.)
- `OlderFiles/` — archive of older scripts and data, including prior versions of planar_tables and scripts

## Key conventions

- File naming: `{Class}_{Language}_{Construction}_blank.tsv` → `..._filled.tsv` (or `..._fill.tsv`, `..._full.tsv`).
- Language ID is inferred from the planar filename: `planar_stan1293-20260209.tsv` → `stan1293`.
- Elements with leading/trailing hyphens are wrapped in `[brackets]` to avoid Excel parsing issues.
- `DATA_DIR = ""` at the top of each analysis module controls file resolution; when empty, files resolve relative to the module's own directory. The CLI sets this before calling analysis functions.
- Keystone rows always have `Position_Name == 'v:verbroot'` and receive `NA` parameter values in blank forms.
