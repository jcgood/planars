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
| `stress` | `stressed`, `obligatory`, `independence`, `left-interaction`, `right-interaction` | 4 (2 domain types × complete/partial) |
| `aspiration` | `stressed`, `obligatory`, `independence`, `left-interaction`, `right-interaction` | 4 (2 domain types × complete/partial) |

Stress and aspiration use `blocked_span`: expand from the keystone outward, stopping just before the first blocking position. The keystone itself can trigger a blocking condition. Two domain types (minimal, maximal), each with a complete/partial distinction = 4 spans per analysis. See `codebook.yaml` for qualification rules; `left-interaction` and `right-interaction` parameters are marked `[NEEDS REVIEW]`.

## Charting

`planars.charts` provides two functions for visualizing span results:

```python
from planars.charts import collect_all_spans, charts_by_language

df, lang_meta = collect_all_spans(repo_root)
for lang_id, fig in charts_by_language(df, lang_meta).items():
    fig.show()   # interactive Plotly figure
```

`collect_all_spans` runs all analyses over all filled TSVs in `coded_data/` and returns `(df, lang_meta)`. The DataFrame has columns `Language`, `Test_Labels`, `Analysis`, `Left_Edge`, `Right_Edge`, `Size`. `lang_meta` is a dict keyed by language ID, each entry holding that language's `keystone_pos` and `pos_to_name` — languages have independent planar structures and are never mixed. `collect_all_spans_from_sheets(gc, manifest)` does the same but reads directly from Google Sheets. `domain_chart(df, keystone_pos, pos_to_name)` renders a single-language DataFrame as a horizontal segment chart. `charts_by_language(df, lang_meta)` produces one chart per language and returns `dict[lang_id, Figure]`.

### Colab notebooks

Two Colab notebooks support browser-only use without installing anything locally. They serve different audiences:

**Contributor notebook (`sync_colab.ipynb`) — for annotators**

Intended for language contributors working on a single language. Shows a domain chart for that language only. The coordinator shares this notebook via Google Drive (stored in the language's Drive folder) with `DRIVE_FOLDER_ID` pre-set.

1. Open the shared notebook link in Google Drive — it opens in Colab automatically
2. Choose **Runtime → Run all**
3. When prompted, sign in with your Google account and allow access
4. The domain chart appears at the bottom of the page

If setting up for a new language, set `DRIVE_FOLDER_ID` in the configure cell to the Drive folder ID (the alphanumeric string at the end of the folder's URL).

**Director notebook (`span_results_colab.ipynb`) — for project directors**

Shows full per-construction text reports and one domain chart per language across all languages in the manifest. Intended for project directors reviewing the full dataset.

1. Run the **Setup** cell — installs planars if needed and requests Google permissions (once per session)
2. Set `DRIVE_FOLDER_ID` in the **Configure** cell
3. Run **Load manifest**, then run analysis and chart cells as needed, or use **Runtime → Run all**

## diagnostics.tsv

Controls which analyses and constructions are generated for each language. Parameters default to `y/n` dropdowns; custom values use brace syntax:

```
stressed{y/n/both}, independence, left-interaction, right-interaction
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
coded_data/synth0001/           Synthetic second-language dataset (not real data — for testing)
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

## Multi-language testing

`coded_data/synth0001/` is a synthetic second-language dataset derived from `stan1293` for testing multi-language code paths. It has a different planar structure (28 positions vs. 37, keystone at position 23 vs. 30) and quasi-randomly flipped parameter values. It is not real data.

```bash
python tests/make_synthetic_lang.py           # dry run
python tests/make_synthetic_lang.py --apply   # regenerate synth0001
python tests/make_synthetic_lang.py --clean --apply  # remove synth0001
```
