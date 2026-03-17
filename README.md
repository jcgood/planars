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
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name planars --display-name planars
```

## Workflow

### 1. Generate annotation forms

```bash
python generate_sheets.py   # creates sheets for new classes; skips existing ones
python generate_sheets.py --force  # regenerate all from scratch
```

Creates one Google Sheets file per analysis class with one tab per construction. Each tab has per-parameter dropdown validation and a free-text Comments column. Google Sheets is the definitive copy of annotation forms. On re-runs, only classes not yet in the Drive manifest are created.

Authentication uses OAuth2. On first run a browser window opens for authorization; the token is cached at `~/.config/gspread/authorized_user.json`. OAuth credentials must be at `~/.config/planars/oauth_credentials.json` (override with `PLANARS_OAUTH_CREDENTIALS`).

The manifest is stored on Google Drive as `manifest_{lang_id}.json` in the language folder. A local `drive_config.json` (gitignored) bootstraps the Drive lookup.

### 2. Annotate

Specialists fill in values in the shared Google Sheets. Keystone rows (`v:verbroot`) are pre-filled with `NA` and should not be changed.

### 3. Import

```bash
python import_sheets.py          # downloads filled sheets → TSVs in coded_data/
python import_sheets.py --force  # overwrite existing files
```

Skips existing files by default. If any validation warnings are found (blank cells, unexpected values), they are written to `import_errors/{lang}_{timestamp}.txt` as well as printed to the terminal.

### 4. Run analyses

From the repo root:

```bash
python -m planars ciscategorial     <path/to/filled.tsv>
python -m planars subspanrepetition <path/to/filled.tsv>
python -m planars noninterruption   <path/to/filled.tsv>
python -m planars stress            <path/to/filled.tsv>
python -m planars aspiration        <path/to/filled.tsv>
```

## Maintaining sheets

```bash
python update_sheets.py           # dry run — show what would change
python update_sheets.py --apply   # add missing rows/trailing columns to existing sheets

python sync_params.py             # dry run — show param column changes needed
python sync_params.py --apply     # insert new param columns, update dropdown validation
```

Use `update_sheets.py` when new elements are added to the planar structure or a new trailing column (e.g. Comments) needs propagating. Use `sync_params.py` when `diagnostics.tsv` param columns change — it preserves existing annotations while inserting new columns before Comments.

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
| `stress` | `stressable`, `obligatory`, `independence`, `left-interaction`, `right-interaction` | 4 (provisional — qualification rule under review) |
| `aspiration` | `stressable`, `obligatory`, `independence`, `left-interaction`, `right-interaction` | 4 (provisional — qualification rule under review) |

See `codebook.yaml` for qualification rules. Stress and aspiration entries are marked `[NEEDS REVIEW]`.

## Charting

`planars.charts` provides two functions for visualizing span results:

```python
from planars.charts import collect_all_spans, domain_chart

df, keystone_pos, pos_to_name = collect_all_spans(repo_root)
fig = domain_chart(df, keystone_pos, pos_to_name)
fig.show()   # interactive Plotly figure
fig.write_image("domains.pdf")  # or save to file
```

`collect_all_spans` runs all analyses over all filled TSVs in `coded_data/` and returns a DataFrame with columns `Test_Labels`, `Analysis`, `Left_Edge`, `Right_Edge`, `Size`. `collect_all_spans_from_sheets(gc, manifest)` does the same but reads directly from Google Sheets (used by Colab notebooks). `domain_chart` renders this as a horizontal segment chart with one row per span, colored by analysis type, with the keystone marked by a dotted line.

### Colab notebooks

Two notebooks in `notebooks/` support browser-only use without a local install:

- **`sync_colab.ipynb`** — for non-technical collaborators: set `DRIVE_FOLDER_PATH` and run all cells to view the domain chart
- **`span_results_colab.ipynb`** — for contributors: step-by-step cells for setup, manifest loading, and charting

## diagnostics.tsv

Controls which analyses and constructions are generated for each language. Parameters default to `y/n` dropdowns; custom values use brace syntax:

```
stressable{y/n/both}, independence, left-interaction, right-interaction
```

## Repository structure

```
planars/                        Core library
  io.py                         Shared TSV/Sheets loader
  spans.py                      Span computation functions
  ciscategorial.py              }
  subspanrepetition.py          }
  noninterruption.py            } Analysis modules
  stress.py                     }
  aspiration.py                 }
  charts.py                     Span collection and domain chart
  cli.py                        Command-line entry point
coded_data/{lang_id}/           Annotation data per language
  planar_input/                 Planar structure TSV + diagnostics.tsv
  {class_name}/                 Filled TSVs per analysis class
make_forms.py                   Planar structure and diagnostics utilities
generate_sheets.py              Create annotation forms in Google Drive
update_sheets.py                Add missing rows/trailing columns to existing sheets
sync_params.py                  Sync param columns when diagnostics.tsv changes
import_sheets.py                Download filled sheets to TSVs
restructure_sheets.py           Archive and regenerate sheets after structural changes
notebooks/                      Jupyter notebooks (local + Colab)
tests/snapshots/                Regression test baselines
codebook.yaml                   Parameter and term definitions
```

## Regression testing

```bash
python generate_snapshots.py   # regenerate baselines
python check_snapshots.py      # verify output matches baselines
```
