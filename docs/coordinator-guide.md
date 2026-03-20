# Coordinator guide

This guide is for project coordinators who manage annotation data, Google Sheets, and the `coding/` workflow scripts. You will need both the `planars` repo and the private `planars-data` repo, and a terminal for running Python commands.

For background on the analyses and span types, see the [Analyses guide](analyses.md). For details on Colab notebooks — what they contain and how to share them with collaborators — see the [Notebooks guide](notebooks.md).

---

## Repository setup

### Initial clone

Coordinators work with two repositories. Clone both, then nest `planars-data` inside `planars` as `coded_data/`:

```bash
git clone https://github.com/jcgood/planars.git
git clone https://github.com/jcgood/planars-data.git planars/coded_data
```

`coded_data/` is a fully independent git repo nested inside `planars/`. The outer repo ignores it entirely (listed in `.gitignore`). All `coding/` scripts find data at this path with no extra configuration.

**Using GitHub Desktop?** The second clone must be done from the command line — GitHub Desktop cannot clone into a specific subfolder. Use **Repository → Open in Terminal** from your planars repo, then run:

```bash
git clone https://github.com/jcgood/planars-data.git coded_data
```

After that, add `coded_data/` to GitHub Desktop via **File → Add Local Repository** so both repos appear in the switcher. If you already have a `coded_data/` folder, delete it first.

### Python environment

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Activate the environment at the start of each session:

```bash
source .venv/bin/activate
```

### Google OAuth credentials

Authentication uses OAuth2. Place your credentials at `~/.config/planars/oauth_credentials.json` (or set `PLANARS_OAUTH_CREDENTIALS` to override the path). On first run of any `coding/` command that touches Google Drive or Sheets, a browser window opens for authorization. The token is cached after first authorization.

---

## Daily git workflow

Code and data live in separate repositories and are always committed separately:

```bash
# Committing code changes (inside planars/)
git add coding/generate_sheets.py
git commit -m "..."
git push

# Committing annotation data (cd into coded_data first — separate step)
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

`git pull` in `planars/` never touches `coded_data/`, and vice versa.

---

## Adding a new language

1. In `coded_data/`, create:
   - `{lang_id}/planar_input/planar_{lang_id}-{date}.tsv` — planar structure
   - `{lang_id}/planar_input/diagnostics.tsv` — analysis classes and parameters

   See [Data management](data-management.md) for the required format of both files.

2. Generate annotation sheets and notebooks:
   ```bash
   python -m coding generate-sheets
   ```
   This creates one Google Sheets file per analysis class, uploads contributor and coordinator Colab notebooks to Drive, and updates the Drive manifest. On re-runs, only classes not yet in the manifest are created.

3. On first use (run once after the very first `generate-sheets`):
   ```bash
   python -m coding setup-root-folder
   ```
   Creates the top-level `ConstituencyTypology` Drive folder and moves global files there. This is idempotent — safe to re-run.

4. Share the language Drive folder and the contributor notebook link with your collaborator.

---

## Sheet lifecycle

### 1. Generate annotation forms

```bash
python -m coding generate-sheets           # creates sheets for new classes only
python -m coding generate-sheets --force   # regenerate all from scratch
```

Creates one Google Sheets file per analysis class with one tab per construction. Each tab has per-parameter dropdown validation and a free-text Comments column. Also runs `generate-notebooks` automatically at the end.

### 2. Collaborators annotate

Collaborators fill in values in the shared Google Sheets. See the [Collaborator guide](collaborator-guide.md). Keystone rows (`v:verbstem`) are pre-filled with `NA` and should not be changed.

### 3. Import filled sheets

```bash
python -m coding import-sheets           # downloads filled sheets → TSVs in coded_data/
python -m coding import-sheets --force   # overwrite existing files
```

Skips existing files by default. Validates values on import (blanks and unexpected entries produce warnings). If any warnings are found, they are written to `import_errors/{lang}_{timestamp}.txt` as well as printed to the terminal.

### 4. Run analyses

From the repo root:

```bash
python -m planars ciscategorial     coded_data/stan1293/ciscategorial/general_filled.tsv
python -m planars noninterruption   coded_data/stan1293/noninterruption/general_filled.tsv
python -m planars stress            coded_data/stan1293/stress/general_filled.tsv
# etc. — all 15 analysis modules are available; see docs/analyses.md for the full list
```

Results are also available via the coordinator and contributor Colab notebooks. See the [Notebooks guide](notebooks.md).

---

## Sheet maintenance commands

### Adding elements to the planar structure

When new elements are added to `planar_input/planar_{lang_id}-{date}.tsv`:

```bash
python -m coding update-sheets           # dry run — show what would change
python -m coding update-sheets --apply   # add missing rows to existing sheets
```

### Updating parameters in diagnostics.tsv

When `diagnostics.tsv` param columns change (new parameters added, parameters renamed):

```bash
python -m coding sync-params                                  # dry run
python -m coding sync-params --apply                          # insert new columns, update validation
python -m coding sync-params --apply --rename old:new         # rename a column in all classes
python -m coding sync-params --apply --rename class:old:new   # rename only in one class
```

Preserves existing annotations while inserting new columns before Comments. Automatically regenerates and uploads notebooks afterward.

### Restructuring after planar changes

When the planar structure itself changes (positions added, dropped, or renamed):

```bash
python -m coding restructure-sheets                                       # dry run
python -m coding restructure-sheets --apply                               # archive old sheets, regenerate
python -m coding restructure-sheets --rename-map "old_pos:new_pos" --apply   # carry over renamed positions
python -m coding restructure-sheets --rename-element Ad-VP:AD-VP --apply     # carry over renamed elements
```

Only classes with actual changes are archived; unchanged classes are left untouched. Automatically regenerates and uploads notebooks afterward.

### Validating annotation sheets

```bash
python -m coding validate-coding                    # all languages
python -m coding validate-coding --lang arao1248    # one language
```

Reads current sheet values, clears existing pink highlights, re-highlights any invalid cells, and prints an issue summary. Safe to run repeatedly. Collaborators can also run the validation notebook themselves — see the [Notebooks guide](notebooks.md#validation-notebook).

### Regenerating notebooks

```bash
python -m coding generate-notebooks
```

Regenerates and uploads contributor (`domains_{lang_id}.ipynb`), coordinator (`all_languages.ipynb`), and validation (`validation_{lang_id}.ipynb`) notebooks to Drive. Also runs automatically at the end of `generate-sheets`, `sync-params --apply`, and `restructure-sheets --apply`. See the [Notebooks guide](notebooks.md) for what each notebook contains.

### Consistency checks

```bash
python -m coding check-codebook
```

Verifies that parameter names in `codebook.yaml`, analysis modules, and `diagnostics.tsv` are consistent. Run this after adding new parameters or analyses.

---

## Drive folder structure

The Drive manifest (`planars_config.json`) is stored on Drive and contains all languages' sheet metadata and folder IDs. A local `drive_config.json` (gitignored) bootstraps the Drive lookup — it holds `_root_folder_id`, `_planars_config_file_id`, and per-language `folder_id` and `domains_notebook_file_id`.

Each `generate-sheets` run also uploads `planar_*.tsv` and `diagnostics.tsv` to the language's Drive folder so collaborators can view the planar structure alongside their annotation sheets.
