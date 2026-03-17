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

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name planars --display-name planars
```

## Workflow

### 1. Generate annotation forms

```bash
python generate_sheets.py   # creates one Sheet per analysis class in Google Drive
```

Creates one Google Sheets file per analysis class with one tab per construction. Each tab has per-parameter dropdown validation and a free-text Comments column. Google Sheets is the definitive copy of annotation forms.

Authentication uses OAuth2. On first run a browser window opens for authorization; the token is cached at `~/.config/gspread/authorized_user.json`. OAuth credentials must be at `~/.config/planars/oauth_credentials.json` (override with `PLANARS_OAUTH_CREDENTIALS`).

### 2. Annotate

Specialists fill in values in the shared Google Sheets. Keystone rows (`v:verbroot`) are pre-filled with `NA` and should not be changed.

### 3. Import

```bash
python import_sheets.py          # downloads filled sheets → TSVs in numbered output folders
python import_sheets.py --force  # overwrite existing files
```

Skips existing files by default. If any validation warnings are found (blank cells, unexpected values), they are written to `import_errors/{lang}_{timestamp}.txt` as well as printed to the terminal.

### 4. Run analyses

From the repo root:

```bash
python -m planars ciscategorial     <path/to/filled.tsv>
python -m planars subspanrepetition <path/to/filled.tsv>
python -m planars noninterruption   <path/to/filled.tsv>
```

## Maintaining sheets

```bash
python update_sheets.py           # dry run — show what would change
python update_sheets.py --apply   # add missing columns/rows to existing sheets
```

Use `update_sheets.py` when the schema changes (e.g. a new trailing column is added) or when new elements are added to the planar structure. Does not handle position renumbering — see [issue #5](https://github.com/jcgood/planars/issues/5).

### 5. Explore results interactively

```bash
source .venv/bin/activate
jupyter lab
```

Open `notebooks/span_results.ipynb`. Make sure the kernel in the top-right says **planars** (if not, go to **Kernel → Change Kernel** and select it). Run all cells with **Run → Run All Cells**. The notebook reads the filled TSVs directly and reports spans for all analyses, noting any positions with missing annotations.

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
01_planar_input/              Planar structure, diagnostics, make_forms.py utilities
02_ciscategorial_output/      Ciscategorial data files
03_subspanrepetition_output/  Subspan repetition data files
04_noninterruption/           Non-interruption data files
05_stress/                    Stress data files
notebooks/                    Jupyter notebooks for interactive exploration
tests/snapshots/              Regression test baselines
codebook.yaml                 Parameter and term definitions
generate_sheets.py            Create annotation forms in Google Drive
update_sheets.py              Add missing columns/rows to existing sheets
import_sheets.py              Download filled sheets to TSVs
populate_sheets.py            One-time upload of legacy TSV data to sheets
```

## Regression testing

```bash
python generate_snapshots.py   # regenerate baselines
python check_snapshots.py      # verify output matches baselines
```
