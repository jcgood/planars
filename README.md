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
- [gspread](https://docs.gspread.org/) + google-auth + google-api-python-client (Google Sheets workflow only)

Install dependencies: `pip install -r requirements.txt`

## Workflow

### 1. Generate blank annotation forms

```bash
cd 01_planar_input
python make_forms.py
```

Reads `planar_<lang>.tsv` (the planar structure) and `diagnostics.tsv` (which analyses to run and their parameters), and writes one blank TSV per analysis/construction combination.

### 2. Annotate

**Option A — TSV files directly:** Fill in values for each element/parameter cell. Keystone rows (`v:verbroot`) are pre-filled with `NA` and should not be changed.

**Option B — Google Sheets:** Generate annotation forms as shared Google Sheets, fill them in collaboratively, then import back to TSVs.

```bash
python generate_sheets.py   # creates one Sheet per analysis class in Google Drive
# (specialist fills in values)
python import_sheets.py     # downloads filled sheets → TSVs in numbered output folders
python import_sheets.py --force  # overwrite existing files
```

Authentication uses OAuth2. On first run a browser window opens for authorization; the token is cached at `~/.config/gspread/authorized_user.json`. OAuth credentials must be at `~/.config/planars/oauth_credentials.json` (override with `PLANARS_OAUTH_CREDENTIALS`).

If any validation warnings are found during import (blank cells, unexpected values), they are written to `import_errors/{lang}_{timestamp}.txt` as well as printed to the terminal.

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
| `stress` | `stressable`, `independence`, `left-interaction`, `right-interaction` | TBD |

## diagnostics.tsv

Controls which analyses and constructions are generated for each language. Parameters default to `y/n` dropdowns; custom values use brace syntax:

```
stressable{y/n/both}, independence, left-interaction, right-interaction
```

## Repository structure

```
planars/                      Core library
  io.py                       Shared TSV loader
  spans.py                    Span computation functions
  ciscategorial.py            }
  subspanrepetition.py        } Analysis modules
  noninterruption.py          }
  cli.py                      Command-line entry point
01_planar_input/              Planar structure, diagnostics, form generator
02_ciscategorial_output/      Ciscategorial data files
03_subspanrepetition_output/  Subspan repetition data files
04_noninterruption/           Non-interruption data files
05_stress/                    Stress data files
tests/snapshots/              Regression test baselines
codebook.yaml                 Parameter and term definitions
generate_sheets.py            Google Sheets form generator
import_sheets.py              Google Sheets importer
```

## Regression testing

```bash
python generate_snapshots.py   # regenerate baselines
python check_snapshots.py      # verify output matches baselines
```
