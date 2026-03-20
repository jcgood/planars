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

## Repository structure

This repository contains the `planars` library and coordinator tooling (`coding/`). Annotation
data lives in a separate private repository, **planars-data**, which is restricted to authorized
coordinators. If you are a coordinator, see [Coordinator setup](#coordinator-setup) below.

## Requirements

- Python 3.9+
- [pandas](https://pandas.pydata.org/)
- [gspread](https://docs.gspread.org/) + google-auth + google-api-python-client (Google Sheets workflow only)

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Coordinator setup

Coordinators work with both this repo and the private `planars-data` repo. Clone both, then
nest `planars-data` inside `planars` as `coded_data/`:

```bash
# Clone both repos (replace jcgood with the org/user as appropriate)
git clone https://github.com/jcgood/planars.git
git clone https://github.com/jcgood/planars-data.git planars/coded_data
```

`coded_data/` is a fully independent git repo nested inside `planars/`. The outer repo ignores
it entirely (it is listed in `.gitignore`). All `coding/` scripts find data at the expected path
with no extra configuration.

**Using GitHub Desktop?** The second clone must be done from the command line (GitHub Desktop
can't clone into a specific subfolder). Use **Repository → Open in Terminal** from your planars
repo, then run `git clone https://github.com/jcgood/planars-data.git coded_data`. After that,
add `coded_data/` to GitHub Desktop via **File → Add Local Repository** so both repos appear in
the switcher. If you already have a `coded_data/` folder, delete it first before cloning.

**Daily workflow — two separate git operations:**

```bash
# Committing code changes (inside planars/)
git add coding/generate_sheets.py
git commit -m "..."
git push

# Committing data changes (cd into coded_data first)
cd coded_data
git add stan1293/ciscategorial/general_filled.tsv
git commit -m "..."
git push

# Pulling the latest code
cd /path/to/planars
git pull

# Pulling the latest annotation data
cd /path/to/planars/coded_data
git pull
```

Changes to code and data are always committed and pushed separately — they go to different
repositories. `git pull` in `planars/` never touches `coded_data/`, and vice versa.

### Adding a new language

1. In `coded_data/`, create `{lang_id}/planar_input/planar_{lang_id}-{date}.tsv` with the planar structure and `{lang_id}/planar_input/diagnostics.tsv` with the analysis classes and parameters.

2. Generate annotation sheets and notebooks:
   ```bash
   python -m coding generate-sheets
   ```
   This creates one Google Sheets file per analysis class, uploads per-language and coordinator Colab notebooks to Drive, and updates the manifest.

3. On first use, create the top-level Drive folder structure:
   ```bash
   python -m coding setup-root-folder
   ```
   This only needs to be run once (it is idempotent).

4. Share the language Drive folder and contributor notebook link with your collaborator.

**Ongoing maintenance:** use `sync-params --apply` when `diagnostics.tsv` param columns change, and `update-sheets --apply` when new elements are added to the planar structure.

## Workflow

### 1. Generate annotation forms and notebooks

```bash
python -m coding generate-sheets           # creates sheets for new classes; skips existing ones
python -m coding generate-sheets --force   # regenerate all from scratch
```

Creates one Google Sheets file per analysis class with one tab per construction. Each tab has per-parameter dropdown validation and a free-text Comments column. Google Sheets is the definitive copy of annotation forms. On re-runs, only classes not yet in the Drive manifest are created.

`generate-sheets` automatically runs `generate-notebooks` at the end — it uploads per-language contributor notebooks (`domains_{lang_id}.ipynb`) and a coordinator notebook (`all_languages.ipynb`) to Drive. See [Colab notebooks](#colab-notebooks) below for details.

Authentication uses OAuth2. On first run a browser window opens for authorization; the token is cached at `~/.config/gspread/authorized_user.json`. OAuth credentials must be at `~/.config/planars/oauth_credentials.json` (override with `PLANARS_OAUTH_CREDENTIALS`).

The manifest is stored on Google Drive as a single merged `planars_config.json` containing all languages' sheet metadata and folder IDs. A local `drive_config.json` (gitignored) bootstraps the Drive lookup.

### 2. Annotate

Specialists fill in values in the shared Google Sheets. Keystone rows (`v:verbstem`) are pre-filled with `NA` and should not be changed.

### 3. Import

```bash
python -m coding import-sheets           # downloads filled sheets → TSVs in coded_data/
python -m coding import-sheets --force   # overwrite existing files
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
python -m coding update-sheets           # dry run — show what would change
python -m coding update-sheets --apply   # add missing rows to existing sheets

python -m coding sync-params                                 # dry run — show param column changes needed
python -m coding sync-params --apply                         # insert new param columns, update validation
python -m coding sync-params --apply --rename old:new        # rename a column in all classes
python -m coding sync-params --apply --rename class:old:new  # rename only in one analysis class

python -m coding generate-notebooks      # regenerate and upload contributor/coordinator notebooks

python -m coding validate-coding                   # re-validate all languages; update pink highlighting
python -m coding validate-coding --lang arao1248   # one language only

python -m coding restructure-sheets           # dry run — show what would be archived/regenerated
python -m coding restructure-sheets --apply   # archive old sheets and regenerate from current planar
python -m coding restructure-sheets --rename-map "old_pos:new_pos" --apply   # carry over renamed positions
python -m coding restructure-sheets --rename-element Ad-VP:AD-VP --apply     # carry over renamed elements
```

Use `update-sheets` when new elements are added to the planar structure. Use `sync-params` when `diagnostics.tsv` param columns change — it preserves existing annotations while inserting new columns before Comments, then regenerates notebooks. Use `restructure-sheets` when the planar structure itself changes (positions added, dropped, or renamed) — it archives each affected sheet and regenerates it with values carried over from the old version. Only classes with actual changes (new rows, drops, or renames) are archived; unchanged classes are left untouched. `generate-notebooks` can also be run standalone to refresh notebooks without changing sheets.

`validate-coding` is safe to run repeatedly — it clears all existing pink cell highlights and re-highlights any remaining invalid cells. Collaborators can run the Colab validation notebook (see below) to do the same from a browser without needing local setup.

### 5. Explore results interactively

See [Colab notebooks](#colab-notebooks) below. Notebooks are browser-only — no local install required. Open the shared Drive link and choose **Runtime → Run all**.

## Analyses

| Analysis | Parameters | Spans derived | Status |
|---|---|---|---|
| `ciscategorial` | `V-combines`, `N-combines`, `A-combines` | 4 (strict/loose × complete/partial) | — |
| `subspanrepetition` | `widescope_left`, `widescope_right`, `fillable_botheither_conjunct` | 20 (5 categories × 4) | — |
| `noninterruption` | `free`, `multiple` | 4 strict spans (2 domain types × complete/partial) | — |
| `stress` | `stressed`, `obligatory`, `independence`, `left-interaction`, `right-interaction` | 4 (2 domain types × complete/partial) | — |
| `aspiration` | `stressed`, `obligatory`, `independence`, `left-interaction`, `right-interaction` | 4 (2 domain types × complete/partial) | [NEEDS REVIEW] |
| `nonpermutability` †| `permutable`, `scopal` | 4 strict spans (2 domain types × complete/partial) | [AUTO-DERIVED] |
| `free_occurrence` †| `free` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `biuniqueness` †| `biunique` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `repair` †| `restart` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `segmental` †| `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `suprasegmental` †| `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `pausing` ‡| `pause_domain` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `proform` ‡| `substitutable` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `play_language` ‡| `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `idiom` ‡| `idiomatic` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |

**Status key:**
- `[NEEDS REVIEW]` — rule is human-designed but provisional; specific parameters under review (see `codebook.yaml`).
- `[AUTO-DERIVED]` — parameter design and qualification rules were automatically derived by reading Tallman et al. 2024 (_Constituency and convergence in the Americas_, langsci/291) and have not been verified by a domain expert. Treat these as drafts: check `codebook.yaml` for details before using them for annotation or analysis.

† Derived from specific language chapters in langsci/291 (Araona ch. 13, Cup'ik ch. 2) — has concrete data support but still needs expert sign-off.

‡ Derived from the Discussion chapter (ch. 17) description only — no concrete language data was reviewed; parameter design is more speculative.

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

Colab notebooks support browser-only use without installing anything locally. They are generated automatically by `python -m coding generate-notebooks` (which runs as part of `generate-sheets`, `sync-params --apply`, and `restructure-sheets --apply`) and uploaded directly to Google Drive. Contributors and coordinators open the shared links — they do not need to manage notebooks manually.

**Contributor notebook (`domains_{lang_id}.ipynb`) — for annotators**

One notebook per language, stored in the language's Drive folder. Shows a domain chart for that language and per-construction text reports for each analysis class.

1. Open the shared notebook link from Google Drive — it opens in Colab automatically
2. Choose **Runtime → Run all**
3. When prompted, sign in with your Google account and allow access
4. Results and domain chart appear at the bottom of the page

**Coordinator notebook (`all_languages.ipynb`) — for project coordinators**

A single notebook covering all languages. Shows per-construction text reports and one domain chart per language across all languages in the manifest.

1. Open the shared notebook link from Google Drive
2. Choose **Runtime → Run all**
3. When prompted, sign in and allow access

The notebook template files live in `notebooks/templates/`. To update the boilerplate (e.g. setup cell, chart cell), edit the template and re-run `python -m coding generate-notebooks`.

**Validation notebook (`validation_{lang_id}.ipynb`) — for collaborators fixing errors**

One notebook per language. Reads the current sheet values, runs the same validation as `import-sheets`, highlights any invalid cells pink, and prints an issue summary. Collaborators can run this themselves as they fix errors — they do not need to wait for a coordinator to run `import-sheets` or `validate-coding`.

1. Open the shared notebook link from the language's Drive folder
2. Choose **Runtime → Run all**
3. When prompted, sign in with your Google account and allow access
4. Invalid cells are highlighted pink in the Google Sheets; the summary appears at the bottom of the notebook

The predecessor notebooks (`sync_colab.ipynb`, `span_results_colab.ipynb`) are archived in `notebooks/archive/` for reference.

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
coding/                         Google Sheets workflow tools (python -m coding <command>)
  make_forms.py                 Planar structure and diagnostics utilities
  generate_sheets.py            Create annotation forms in Google Drive
  update_sheets.py              Add missing rows to existing sheets
  sync_params.py                Sync param columns when diagnostics.tsv changes
  import_sheets.py              Download filled sheets to TSVs
  validate.py                   Shared validation type (ValidationIssue)
  validate_planar.py            Planar structure TSV validation (validate_planar_df)
  validate_diagnostics.py       diagnostics.tsv validation (validate_diagnostics_df)
  validate_coding.py            Annotation sheet validation + validate-coding command
  restructure_sheets.py         Archive and regenerate sheets after structural changes
  generate_notebooks.py         Generate and upload contributor/coordinator Colab notebooks
  populate_sheets.py            Upload legacy TSV data to sheets (one-time utility)
  check_codebook.py             Check consistency between codebook.yaml and analysis modules
coded_data/{lang_id}/           Annotation data per language
  planar_input/                 Planar structure TSV + diagnostics.tsv
  {class_name}/                 Filled TSVs per analysis class
coded_data/synth0001/           Synthetic second-language dataset (not real data — for testing)
notebooks/
  templates/                    Boilerplate notebooks used by generate-notebooks
    domains_boilerplate.ipynb         Contributor notebook template
    all_languages_boilerplate.ipynb   Coordinator notebook template
    validation_boilerplate.ipynb      Validation notebook template
  archive/                      Superseded notebooks (span_results.ipynb, sync_colab.ipynb, span_results_colab.ipynb)
tests/snapshots/                Regression test baselines
codebook.yaml                   Parameter and term definitions
```

## Regression testing

```bash
python generate_snapshots.py   # regenerate baselines
python check_snapshots.py      # verify output matches baselines
```

## Multi-language support

All workflow commands (`generate-sheets`, `import-sheets`, `sync-params`, `update-sheets`, `restructure-sheets`, `generate-notebooks`) loop over every language found in `coded_data/` — no language-specific flags are needed. Each language has its own `planar_input/` directory with a planar structure TSV and `diagnostics.tsv`, and its own Drive folder. Languages have independent planar structures and are never mixed in analysis.

### Multi-language testing

`coded_data/synth0001/` is a synthetic second-language dataset derived from `stan1293` for testing multi-language code paths. It has a different planar structure (28 positions vs. 37, keystone at position 23 vs. 30) and quasi-randomly flipped parameter values. It is not real data.

```bash
python tests/make_synthetic_lang.py           # dry run
python tests/make_synthetic_lang.py --apply   # regenerate synth0001
python tests/make_synthetic_lang.py --clean --apply  # remove synth0001
```
