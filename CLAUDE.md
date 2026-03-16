# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the scripts

Each script is self-contained and run directly from its own folder:

```bash
# Generate blank test forms from planar structure + diagnostics
cd 01_planar_input && python make_forms.py

# Analyze v-ciscategorial domains
cd 02_ciscategorial_output && python ciscategorial.py

# Analyze subspan repetition spans
cd 03_subspanrepetition_output && python subspanrepetition.py

# Analyze non-interruption domains
cd 04_noninterruption && python noninterruption.py
```

Dependencies: `pandas` (standard library otherwise). No build system, test framework, or linter is configured.

## Architecture and data flow

This is a linguistic typology analysis project for morphosyntactic domain derivation. The workflow is:

1. **Input** (`01_planar_input/`): `planar_<lang>-<date>.tsv` defines positions and elements for a language. `diagnostics.tsv` specifies which analyses to run (class, construction, parameters). `make_forms.py` reads both and generates blank test TSVs — one per (class, construction) combination.

2. **Manual annotation**: Linguists fill in y/n values in the blank TSVs for each element/position row.

3. **Analysis modules** (folders `02`–`04`): Each reads a filled TSV and derives spans. All share the same core span logic:
   - **Keystone position**: Identified by `Position_Name == 'v:verbroot'`; anchors all span computations.
   - **Partial positions**: ≥1 element in the position qualifies.
   - **Complete positions**: ALL elements in the position qualify.
   - **Strict span**: Contiguous expansion from keystone (no gaps).
   - **Loose span**: Extends to farthest qualifying position on each side regardless of gaps.

4. **Analysis modules in detail**:
   - `ciscategorial.py`: A position qualifies if elements have `V-combines=y` and all other params `=n`. Returns 4 fractures (strict/loose × complete/partial).
   - `subspanrepetition.py`: 5 span categories (fillable, widescope_left/right, narrowscope_left/right), each with 4 spans = 20 total.
   - `noninterruption.py`: Two domain types (no-free: `free=n`; single-free: `free=n` or `free=y,multiple=n`), each with complete/partial = 4 strict spans.

## Key conventions

- File naming: `{Class}_{Language}_{Construction}_blank.tsv` → `..._filled.tsv` (or `..._fill.tsv`).
- Language ID is inferred from the planar filename: `planar_stan1293-20260209.tsv` → `stan1293`.
- Elements with leading/trailing hyphens are wrapped in `[brackets]` to avoid Excel parsing issues.
- `DATA_DIR = ""` at the top of each script controls file resolution; when empty, files are resolved relative to the script's own directory.
- Keystone rows always have `Position_Name == 'v:verbroot'` and receive `NA` parameter values in blank forms.
