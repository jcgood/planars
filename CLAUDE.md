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

# Or run a module directly from its own folder (uses default filled file)
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

3. **Analysis** (`planars/`): Each analysis module reads a filled TSV and derives spans. All share the same core logic:
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

`planars/` is the core library:
- `io.py`: `load_filled_tsv()` — shared TSV loader used by all analysis modules. Reads, normalizes columns, locates the keystone row, validates no blank parameter values, returns `(data_df, keystone_pos, pos_to_name, param_cols)`.
- `spans.py`: `strict_span`, `loose_span`, `position_sets_from_element_mask`, `fmt_span` — shared span math and formatting helper.
- `ciscategorial.py`, `subspanrepetition.py`, `noninterruption.py`: each exposes `derive_*()` (takes a `Path`, returns a result dict) and `format_result()` (takes a result dict, returns a formatted string).
- `cli.py` + `__main__.py`: CLI entry point (`python -m planars <analysis> <tsv>`).

The numbered folders (`02`–`04`) contain only data files and thin wrapper scripts that resolve local paths and call the library.

`generate_snapshots.py` and `check_snapshots.py` at the repo root drive regression testing. Snapshots live in `tests/snapshots/`.

## Codebook

`codebook.yaml` at the repo root is the source of truth for parameter definitions, valid values, analytical terms (keystone, partial, complete, strict, loose), and qualification rules per analysis. Parameter definitions marked `[PLACEHOLDER]` are pending linguistic descriptions from the user.

A rendering script (`render_codebook.py`) will be added later to produce human-readable output from this file.

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
- Analysis functions take a `Path` object; path resolution happens at the call site (CLI or wrapper scripts), not inside the library.
- Keystone rows always have `Position_Name == 'v:verbroot'` and receive `NA` parameter values in blank forms.
- Result dicts use `complete_positions` / `partial_positions` and `*_span` key suffixes consistently across all modules.
