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
git add stan1293/ciscategorial/general.tsv
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

1. Fetch Glottolog metadata and register the language:
   ```bash
   python -m coding lookup-lang {lang_id}
   ```
   Verifies the Glottocode is valid, fetches the language name, family, and ISO code from Glottolog, and writes them into `schemas/languages.yaml`. It also scaffolds an empty `meta` block if none exists.

   Open `schemas/languages.yaml` and fill in the `meta` block for the new language:
   ```yaml
   meta:
     source: "Author, Title (year)"
     author: "Author Name"
     annotator: "Annotator Name"
     annotation_status: planned   # planned | in-progress | complete
     notes: ""
   ```
   Commit `schemas/languages.yaml` to the `planars` repo before running `generate-sheets` — this ensures display names appear correctly in notebooks and charts:
   ```bash
   git add schemas/languages.yaml
   git commit -m "Register {lang_id} in languages.yaml"
   ```

2. In `coded_data/`, create:
   - `{lang_id}/planar_input/planar_{lang_id}-{date}.tsv` — planar structure
   - `{lang_id}/planar_input/diagnostics_{lang_id}.tsv` — analysis classes and diagnostic criteria

   See [Data management](data-management.md) for the required format of both files.

3. Generate annotation sheets and notebooks:
   ```bash
   python -m coding generate-sheets
   ```
   This creates one Google Sheets file per analysis class, uploads contributor and coordinator Colab notebooks to Drive, creates editable Google Sheets for the planar structure and diagnostics files, and updates the Drive manifest. On re-runs, only classes not yet in the manifest are created.

4. If this is the first language in the project, run `setup-root-folder` once after `generate-sheets` — see [Drive folder structure](#drive-folder-structure) below.

5. Share the language Drive folder and the contributor notebook link with your collaborator.

6. After collaborators have filled in sheets, import and verify:
   ```bash
   python -m coding import-sheets
   python -m coding apply-pending        # if any destructive changes were detected
   python -m coding integrity-check --lang {lang_id}
   ```

---

## Sheet lifecycle

### 1. Generate annotation forms

```bash
python -m coding generate-sheets           # creates sheets for new classes only
python -m coding generate-sheets --force   # DESTRUCTIVE: clears and rewrites all sheets (annotation data will be lost)
```

Creates one Google Sheets file per analysis class with one tab per construction. Each tab has per-criterion dropdown validation and a free-text Comments column. Each spreadsheet also gets a **Status tab** (always the last tab) with one row per construction and a dropdown (`in-progress` / `ready-for-review`). Also runs `generate-notebooks` automatically at the end.

At the start of each run, the current Drive manifest is backed up to `manifest_backup.json` (gitignored) in the repo root. If something goes wrong during a run, this file can be used to recover sheet IDs without needing to access Drive directly.

### 2. Collaborators annotate

Collaborators fill in values in the shared Google Sheets. See the [Collaborator guide](collaborator-guide.md). Keystone rows (`v:verbstem`) are pre-filled with `NA` and should not be changed.

When a construction is complete, the collaborator sets its row in the **Status tab** to `ready-for-review`. This signals to the coordinator that the construction is ready to import.

### 3. Import filled sheets

```bash
python -m coding import-sheets                  # import ready-for-review constructions only
python -m coding import-sheets --ignore-status  # import all constructions regardless of status
python -m coding import-sheets --force          # overwrite existing annotation TSVs
```

Skips existing annotation TSVs by default. On each run, `import-sheets` also:

- **Downloads and validates** the planar structure and diagnostics Sheets for each language, writing them to `coded_data/{lang_id}/planar_input/`.
- **Auto-applies safe downstream commands** (`update-sheets --apply`, `sync-params --apply`, `generate-sheets`) when additive changes are detected (new positions, new criteria, new construction tabs).
- **Writes destructive changes** (planar deletions/reorders, criterion renames/removals, new constructions within existing classes) to `pending_changes.json` for coordinator review rather than applying them immediately.

After import, review and apply any pending changes:

```bash
python -m coding apply-pending           # prompt for each change
python -m coding apply-pending --all     # apply all without prompting
```

When destructive changes are detected, `import-sheets` automatically opens a GitHub issue labeled `pending-changes` (or comments on an existing open one) with a summary of each change. When `apply-pending` clears all entries, it closes the issue. This requires `gh` to be installed and authenticated; if it isn't, the terminal warning is the only notification.

If any annotation warnings are found, they are written to `import_errors/{lang}_{timestamp}.txt` as well as printed to the terminal. Invalid cells are highlighted pink in the Google Sheet regardless of `--force`.

### 4. Run analyses

From the repo root:

```bash
python -m planars ciscategorial     coded_data/stan1293/ciscategorial/general.tsv
python -m planars noninterruption   coded_data/stan1293/noninterruption/general.tsv
python -m planars stress            coded_data/stan1293/stress/general.tsv
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

If you see `(quota exceeded — waiting Xs before retry)` messages, the command is handling Google Sheets API rate limits automatically — just let it run.

### Updating diagnostic criteria in diagnostics_{lang_id}.tsv

When `diagnostics_{lang_id}.tsv` criterion columns change (new criteria added, criteria renamed):

```bash
python -m coding sync-params                                   # dry run
python -m coding sync-params --apply                           # insert new columns, update validation
python -m coding sync-params --apply --rename old:new          # rename a column in all classes
python -m coding sync-params --apply --rename class:old:new    # rename only in one class
python -m coding sync-params --apply --split old:new1:new2     # split one criterion into two
python -m coding sync-params --apply --merge old1:old2:new     # merge two criteria into one
python -m coding sync-params --apply --remove                  # also remove stale columns
```

Preserves existing annotations while inserting new columns before Comments. Rename updates headers and validation in place. Split/merge rename the old column(s) to `_split_`/`_merged_` prefixes and add the new column(s) — coordinator remaps values then removes stale columns manually. `integrity-check --sheets` warns on any stale prefixed columns. Automatically regenerates and uploads notebooks afterward.

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

### Full integrity check

```bash
python -m coding integrity-check                        # all languages, local checks
python -m coding integrity-check --lang arao1248        # one language only
python -m coding integrity-check --sheets               # also validate live Google Sheets structure
```

Runs a full project-wide health report across six sections: PLANAR STRUCTURE, DIAGNOSTICS, CODEBOOK CONSISTENCY, ANALYSIS CONSISTENCY, ANNOTATION SHEETS, and NEEDS REVIEW. Run this after any significant change — new language, schema edit, or module addition. The `--sheets` flag adds live validation of Google Sheets structure but requires Drive access.

### Codebook consistency check

```bash
python -m coding check-codebook
```

Verifies that criterion names in `schemas/diagnostic_criteria.yaml`, analysis modules, and `diagnostics_{lang_id}.tsv` are consistent. Run this after adding new diagnostic criteria or analyses. `integrity-check` includes this check; `check-codebook` is useful for lower-level detail.

---

## Makefile aliases

A `Makefile` in the repo root provides short aliases for all common commands. Run `make help` for the full list. Examples:

```bash
make generate-sheets      # python -m coding generate-sheets
make import-sheets        # python -m coding import-sheets
make update-sheets        # python -m coding update-sheets --apply
make update-sheets-dry    # python -m coding update-sheets  (dry run)
make restructure-sheets   # python -m coding restructure-sheets --apply  ⚠ destructive
make integrity-check      # python -m coding integrity-check
make lookup-lang LANG=arao1248
make test
make snapshots
```

For commands that accept extra flags not covered by the aliases (e.g. `--rename-map`, `--rename-element`, `--lang`), use the full `python -m coding ...` form directly. The venv must be activated before using `make` (see [Python environment](#python-environment) above).

---

## Schema utilities

Two standalone scripts in the repo root generate human-readable views of the schema files:

```bash
python render_codebook.py              # print schema reference to stdout
python render_codebook.py codebook.md # write to file

python generate_diagram.py out.svg    # analysis class taxonomy diagram (requires Graphviz)
python generate_diagram.py out.pdf    # same, PDF output
```

`generate_diagram.py` shows all 15 analysis classes grouped by domain type, with diagnostic criteria inside each node and the languages that instantiate each class connected on the right.

---

## Regression testing

```bash
pytest                          # run all tests (I/O, restructure, snapshots)
python check_snapshots.py       # quick CLI alternative for snapshot-only checks
```

Snapshot baselines live in `tests/snapshots/`. When analysis output changes intentionally (e.g., after a qualification rule fix), regenerate the baselines and review the diff before committing:

```bash
python generate_snapshots.py    # regenerate snapshot baselines
git diff tests/snapshots/       # review what changed
```

Run `pytest` after any change to an analysis module, `io.py`, or `spans.py`.

### Pre-push snapshot check (recommended)

A pre-push hook catches stale snapshots locally before they reach CI. Install it once after setting up the project:

```bash
.venv/bin/pip install pre-commit
.venv/bin/pre-commit install --hook-type pre-push
```

After installation, `git push` will automatically run `check_snapshots.py` and block the push if any snapshots are stale, with a message showing which analyses differ. Snapshots go stale when analysis logic changes (a module, `io.py`, or `spans.py`) but `generate_snapshots.py` has not been re-run — the most common case is fixing a qualification rule and forgetting to regenerate before pushing. If the diff is intentional, regenerate snapshots and include them in the push:

```bash
python generate_snapshots.py
git diff tests/snapshots/       # review
git add tests/snapshots/
git commit -m "Update snapshots: ..."
git push
```

CI also runs `check_snapshots.py` as a dedicated step, so stale snapshots will fail the build even if the hook is not installed.

### Scheduled sheet validation

A daily GitHub Actions workflow (`.github/workflows/sheet-validation.yml`) runs `validate-coding` against all live Google Sheets and opens a GitHub issue (labeled `sheet-validation`) if problems are found. When the issue is resolved and the next daily run comes back clean, the issue is closed automatically.

To enable it, add the following four secrets under **Settings → Secrets and variables → Actions** in the GitHub repo (`https://github.com/jcgood/planars` → Settings → Secrets and variables → Actions → New repository secret):

| Secret | Where to get it |
|--------|-----------------|
| `PLANARS_DATA_TOKEN` | Already exists — used by the existing CI workflow to read `jcgood/planars-data`. No action needed. |
| `PLANARS_OAUTH_CREDENTIALS` | Contents of `~/.config/planars/oauth_credentials.json` on your laptop — the OAuth client secret downloaded from Google Cloud Console during initial setup. |
| `GOOGLE_OAUTH_TOKEN` | Contents of `~/.config/gspread/authorized_user.json` on your laptop — written by gspread after your first interactive login. Contains a refresh token, so the workflow can renew its Google access silently without browser interaction. Stays valid as long as the workflow runs at least once every few months. |
| `PLANARS_DRIVE_CONFIG` | Contents of `drive_config.json` in the repo root — tells the workflow how to find the Drive manifest and language folders. |

**Keeping `PLANARS_DRIVE_CONFIG` current:** `generate-sheets` rewrites `drive_config.json` whenever it creates a new language folder or updates sheet IDs. After any such run, copy the updated file contents into the secret. `generate-sheets` prints a reminder at the end of each run when the secret may need updating.

You can also trigger the workflow manually from the Actions tab at any time.

---

## Drive folder structure

The Drive manifest (`manifest.json`) is stored on Drive and contains all languages' sheet metadata and folder IDs. A local `drive_config.json` (gitignored) bootstraps the Drive lookup — it holds `_root_folder_id`, `_planars_config_file_id`, and per-language `folder_id`, `planar_spreadsheet_id`, and `diagnostics_spreadsheet_id`.

`drive_config.json` is created and updated automatically — you never need to edit it by hand. `generate-sheets` writes per-language IDs as it creates Drive folders and files; `setup-root-folder` adds the top-level `_root_folder_id`.

Each `generate-sheets` run also creates editable Google Sheets for `planar_*.tsv` and `diagnostics_{lang_id}.tsv` in the language's Drive folder so collaborators can view (and coordinators can edit) the planar structure alongside their annotation sheets. `import-sheets` reads these Sheets back to local TSVs and detects any changes.

### First-time project setup

After the very first `generate-sheets`, run `setup-root-folder` once to create the top-level `ConstituencyTypology` Drive folder and move shared files there:

```bash
python -m coding setup-root-folder
```

This is idempotent — safe to re-run, but only needs to happen once per project.

### Joining an existing project

`drive_config.json` is gitignored and cannot be recovered from the repo. If you are joining a project that is already set up, ask the lead coordinator to share their `drive_config.json` and place it at the root of your `planars/` clone. Without it, `generate-sheets` and `import-sheets` cannot locate the existing Drive manifest or language folders.
