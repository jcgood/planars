# planars

A Python toolkit for deriving morphosyntactic constituency spans from annotated planar structures. Designed for cross-linguistic typological research.

## Overview

Planar structures are ordered sequences of positions representing the morphosyntactic template of a language's verbal domain. Each position is filled by one or more elements (forms or form-types). Researchers annotate elements with diagnostic parameters, and this toolkit derives **spans** — ranges of positions identified as domains by various constituency tests.

Four span types are computed for each analysis:

| | Complete positions | Partial positions |
|---|---|---|
| **Strict** (no gaps) | strict complete | strict partial |
| **Loose** (gaps allowed) | loose complete | loose partial |

See `codebook.yaml` for definitions of all parameters, values, and terms.

This toolkit builds on the theoretical framework developed in:

> Tallman, Adam J. R., Sandra Auderset, and Hiroto Uchihara (eds.). 2024. *Constituency and convergence in the Americas*. Topics in Phonological Diversity 1. Berlin: Language Science Press. doi:[10.5281/zenodo.10559861](https://doi.org/10.5281/zenodo.10559861)

## Requirements

- Python 3.9+
- [pandas](https://pandas.pydata.org/)

## Workflow

### 1. Generate blank annotation forms

```bash
cd 01_planar_input
python make_forms.py
```

Reads `planar_<lang>.tsv` (the planar structure) and `diagnostics.tsv` (which analyses to run), and writes one blank TSV per analysis/construction combination.

### 2. Annotate

Fill in `y` or `n` for each element/parameter cell in the blank TSVs. Keystone rows (`v:verbroot`) are pre-filled with `NA` and should not be changed.

### 3. Run analyses

From the repo root:

```bash
python -m planars ciscategorial     <path/to/filled.tsv>
python -m planars subspanrepetition <path/to/filled.tsv>
python -m planars noninterruption   <path/to/filled.tsv>
```

Or from within a numbered folder using the default filled file:

```bash
cd 02_ciscategorial_output && python ciscategorial.py
```

## Analyses

| Analysis | Parameters | Spans derived |
|---|---|---|
| `ciscategorial` | `V-combines`, `N-combines`, `A-combines` | 4 (strict/loose × complete/partial) |
| `subspanrepetition` | `widescope_left`, `widescope_right`, `fillable_botheither_conjunct` | 20 (5 categories × 4) |
| `noninterruption` | `free`, `multiple` | 4 strict spans (2 domain types × complete/partial) |

## Repository structure

```
planars/                  Core library
  io.py                   Shared TSV loader
  spans.py                Span computation functions
  ciscategorial.py        }
  subspanrepetition.py    } Analysis modules
  noninterruption.py      }
  cli.py                  Command-line entry point
01_planar_input/          Planar structure, diagnostics, form generator
02_ciscategorial_output/  Ciscategorial data files
03_subspanrepetition_output/  Subspan repetition data files
04_noninterruption/       Non-interruption data files
tests/snapshots/          Regression test baselines
codebook.yaml             Parameter and term definitions
```

## Regression testing

```bash
python generate_snapshots.py   # regenerate baselines
python check_snapshots.py      # verify output matches baselines
```
