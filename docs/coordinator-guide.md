# Coordinator guide

This guide is for project coordinators who manage annotation data, Google Sheets, and the `coding/` workflow scripts. You will need both the `planars` repo and the private `planars-data` repo, and a terminal for running Python commands.

For background on the analyses and span types, see the [Analyses guide](analyses.md). For details on Colab notebooks — what they contain and how to share them with collaborators — see the [Notebooks guide](notebooks.md).

---

## What happens automatically

Once set up, the following run without coordinator action:

| Trigger | What runs | What it does |
|---------|-----------|--------------|
| Every commit to `planars/*.py` | pre-commit hook | Regenerates affected snapshots and stages them |
| Every push | pre-push hook | Verifies all snapshots are current; blocks push if stale |
| Daily at 06:00 UTC | `data-refresh.yml` | Imports latest sheets → syncs diagnostics YAML → regenerates snapshots → commits; opens GitHub issues for import failures (`import-error`), sheet drift (`sheet-drift`), pending destructive changes (`pending-changes`), ambiguous diagnostics YAML drift (`diagnostics-drift`), schema inconsistencies (`codebook-error`), stale manifest entries (`stale-manifest`), or overwritten coordinator commits (`data-overwrite`) |
| Daily at 06:00 UTC | `sheet-validation.yml` | Runs `validate-coding`; opens a `sheet-validation` issue if problems found; closes it when clean |
| Daily at 06:00 UTC | `generate-reports.yml` | Generates and uploads PDF reports to Drive |

The hooks require a one-time install per machine — see [Regression testing and hooks](#regression-testing-and-hooks). The GitHub Actions require secrets configured in the repo — see [Automated workflows](#automated-workflows).

**When something goes wrong automatically:** the daily workflows open labeled GitHub issues so nothing is silently dropped. Check the Issues tab if something looks out of sync. Labels and what they mean:

| Label | Meaning | Resolution |
|-------|---------|------------|
| `import-error` | `import-sheets` crashed or failed | Check issue body for error; fix root cause; next run closes it |
| `sheet-drift` | Sheets are out of sync with data model | Run `update-sheets --apply` |
| `pending-changes` | Destructive annotation changes need review | Run `apply-pending` |
| `diagnostics-drift` | Ambiguous TSV→YAML differences found | Review drift, edit YAML, run `sync-diagnostics-yaml --apply` |
| `codebook-error` | Schema inconsistency detected | Run `check-codebook` locally for details |
| `stale-manifest` | Manifest has classes no longer in diagnostics | Run `prune-manifest --apply` |
| `data-overwrite` | Coordinator commits may have been overwritten by refresh | Check `git log`/`git show` in planars-data to verify |
| `integrity-error` | Planar TSV structure or analysis module consistency error | Run `integrity-check` locally for details |
| `sheet-validation` | Invalid cell values in annotation sheets | Run `validate-coding` locally for details |

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

**Re-authorization after scope changes:** if a new Google API scope is added to the project (e.g., the `documents` scope added for collaborator notes), the cached token at `~/.config/gspread/authorized_user.json` will not include that scope. The next `coding/` command will open a browser window for re-authorization automatically. For the GitHub Actions workflow, update the `GOOGLE_OAUTH_TOKEN` secret with the contents of the newly refreshed token file after re-authorizing locally.

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

## Workflows

### Onboarding a new language

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
   - `{lang_id}/planar_input/diagnostics_{lang_id}.yaml` — analysis classes and diagnostic criteria (YAML is the source of truth; the TSV is generated from it)

   Minimal YAML example:
   ```yaml
   language: arao1248
   classes:
     ciscategorial:
       constructions: [general]
       criteria:
         V-combines: [y, n]
         N-combines: [y, n]
   ```

   After writing the YAML, generate the TSV:
   ```bash
   python -m coding sync-diagnostics-yaml --apply --lang {lang_id}
   ```

   See [Data management](data-management.md) for the required format of both files. `check-codebook` section 7 prints a ready-to-paste YAML snippet for each class not yet covered by any language.

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

### Annotation cycle

#### 1. Generate annotation forms

```bash
python -m coding generate-sheets           # creates sheets for new classes only
python -m coding generate-sheets --force   # blocked with a hard error if annotation sheets already exist
```

Creates one Google Sheets file per analysis class with one tab per construction. Each tab has per-criterion dropdown validation, an optional **Source** column (page or section reference justifying each annotation, e.g. `§4.3`, `p. 217`, `Table 6.2`), and a free-text **Comments** column. Source comes before Comments; both are free-text and not validated. Each spreadsheet also gets a **Status tab** (always the last tab) with one row per construction and a dropdown (`in-progress` / `ready-for-review`). Also runs `generate-notebooks` automatically at the end.

At the start of each run, the current Drive manifest is backed up to `manifest_backup.json` (gitignored) in the repo root. If something goes wrong during a run, this file can be used to recover sheet IDs without needing to access Drive directly.

#### 2. Collaborators annotate

Collaborators fill in values in the shared Google Sheets. See the [Collaborator guide](collaborator-guide.md). Keystone rows (`v:verbstem`) are pre-filled with `NA` and should not be changed.

**Blank / `?` / `NA` semantics** — these three values are distinct and should not be used interchangeably:

| Value | Meaning | Import behavior |
|-------|---------|-----------------|
| blank | Not yet annotated — annotator has not examined this element | Warning on import; excluded from span computations |
| `?` | Uncertain — source was consulted but answer could not be determined | Warning on import; excluded from span computations |
| `NA` | Not applicable — keystone row only (`v:verbstem`) | Silently accepted; keystone excluded from span expansion by design |

The blank/`?` distinction matters for data quality: a `?` is a positive annotation of uncertainty ("I looked and could not decide"), while a blank means the cell has not been filled. Both are flagged on import, but they are semantically different — especially for cross-database comparison.

When a construction is complete, the collaborator sets its row in the **Status tab** to `ready-for-review`. This signals to the coordinator that the construction is ready to import.

#### 2b. Collaborator notes

Each language has a **Notes Google Doc** in its Drive folder (created automatically by `generate-sheets`). Collaborators write freeform observations, questions, and concerns there — anything they'd want to flag to the coordinator but wouldn't know how to file as a GitHub issue.

**For collaborators:** just write freely. There's no required format. The doc is yours to use as a scratchpad.

**For coordinators:** the daily data-refresh reads all notes docs and surfaces new content as GitHub issues. Each open issue has a ready-to-paste Claude prompt — paste it into your Claude session to get a proposed list of issues to file. Review the list, file what's warranted, then close the `collaborator-notes` issue.

When notes are downloaded, an acknowledgment line is automatically appended to the doc (e.g., `[2026-04-06] Notes transferred to coordinator. Please consult with them for an update.`) so the collaborator knows their notes were received.

To check notes manually:
```bash
python -m coding check-notes          # dry run: show what would be filed
python -m coding check-notes --apply  # file/update issues, acknowledge in doc, save state
```

#### 3. Import filled sheets

```bash
python -m coding import-sheets                               # dry run: show what would be written
python -m coding import-sheets --apply                       # import ready-for-review constructions only
python -m coding import-sheets --apply --ignore-status       # import all constructions regardless of status
python -m coding import-sheets --apply --overwrite-existing  # re-download and overwrite existing TSVs (auto-archives first)
```

Dry-run by default — pass `--apply` to write any TSVs. Skips existing annotation TSVs unless `--overwrite-existing` is also passed; when overwriting, the existing TSV is automatically archived to `archive/` first. On each run, `import-sheets` also:

- **Downloads and validates** the planar structure and diagnostics Sheets for each language, writing them to `coded_data/{lang_id}/planar_input/`.
- **Auto-applies safe downstream commands** (`update-sheets --apply`, `sync-params --apply`, `generate-sheets`) when additive changes are detected (new positions, new criteria, new construction tabs).
- **Writes destructive changes** (planar deletions/reorders, criterion renames/removals, new constructions within existing classes) to `pending_changes.json` for coordinator review rather than applying them immediately.

After import, review and apply any pending changes:

```bash
python -m coding apply-pending           # prompt for each change
python -m coding apply-pending --all     # apply all without prompting
```

When destructive changes are detected, `import-sheets` automatically opens a GitHub issue labeled `pending-changes` (or comments on an existing open one) with a summary of each change. When `apply-pending` clears all entries, it closes the issue. This requires `gh` to be installed and authenticated; if it isn't, the terminal warning is the only notification.

If any annotation warnings are found, they are written to `import_errors/{lang}_{timestamp}.txt` as well as printed to the terminal. Invalid cells are highlighted pink in the Google Sheet regardless of `--overwrite-existing`.

#### 4. Run analyses

From the repo root:

```bash
python -m planars ciscategorial     coded_data/stan1293/ciscategorial/general.tsv
python -m planars noninterruption   coded_data/stan1293/noninterruption/general.tsv
python -m planars metrical          coded_data/stan1293/metrical/stress_domain.tsv
python -m planars segmental         coded_data/stan1293/segmental/aspiration_prominence.tsv
# etc. — all analysis modules are available; see docs/analyses.md for the full list
```

Results are also available via the coordinator and contributor Colab notebooks. See the [Notebooks guide](notebooks.md).

### Updating a qualification rule

A **qualification rule** is the formal description of how span computations work for an analysis class — which criterion values cause a position to qualify, whether strict or loose spans are computed, and what blocking conditions apply. The rule text lives in `schemas/diagnostic_classes.yaml` under `qualification_rule:`, and the Python module in `planars/` must implement exactly that rule.

To guard against the rule and code drifting apart, `diagnostic_classes.yaml` stores a `qualification_rule_hash` for each class — a short fingerprint of the rule text. `check-codebook` (and CI) verify that the hash matches the current rule. If you edit the rule text without updating the hash, CI files a `codebook-error` issue.

#### How to recognize the error

The `codebook-error` GitHub issue body will contain a line like:

```
✗ [metrical] qualification_rule_hash mismatch: YAML has "56e9aeb2" but qualification_rule
  hashes to "a1b2c3d4" — the rule was edited without a module review cycle;
  run: python -m coding generate-rule-update-prompt metrical
```

#### The 7-step workflow

1. Edit `qualification_rule` in `schemas/diagnostic_classes.yaml`.
2. `check-codebook` (CI or local) detects the hash mismatch → `codebook-error` issue filed.
   The issue body includes a ready-to-paste Claude prompt.
3. Copy the Claude prompt from the issue and paste it into a Claude Code session.
4. Claude reads the new rule, updates `planars/{name}.py` (logic + docstring), runs tests.
5. Review the diff.
6. Stamp the new hash:
   ```bash
   python -m coding sync-qualification-hashes --apply --class {name}
   ```
7. `check-codebook` passes → `codebook-error` issue auto-closes.

Claude enters only at step 3, with all context pre-assembled. Steps 1, 2, 5–7 are fully deterministic.

#### What "the hash" means

`qualification_rule_hash` is a record that the Python module was verified against this exact rule text. It does **not** guarantee correctness — that is Claude's job in step 4. It guarantees that a human reviewed the change. Run `sync-qualification-hashes --apply` only after you are satisfied with the module diff.

#### Generating a prompt manually

If you want to update a module without waiting for CI:

```bash
python -m coding generate-rule-update-prompt metrical   # one class
python -m coding generate-rule-update-prompt            # all stale classes
```

The prompt includes the current rule text, the current module source, and the exact command to run afterward.

#### If the change is non-trivial or you are unsure

Paste the generated prompt into Claude and ask it to explain what changed before making any edits. The prompt contains enough context for Claude to reason about the linguistic implications of the rule change.

---

### Schema changes

When the diagnostic model changes — a new analysis class, a class renamed or retired, or criteria added or modified — the general sequence is:

1. Edit `schemas/diagnostic_classes.yaml` (add the class, set required criteria, qualification rule, etc.)
2. Scaffold or rename the analysis module in `planars/` if needed.
3. Run `check-codebook` to verify consistency and get a ready-to-paste schema stub:
   ```bash
   python -m coding check-codebook
   ```
   Section 5 prints the TSV row to paste into each applicable language's `diagnostics_{lang_id}.tsv`. Section 6 shows the current language × class coverage matrix.
4. Edit `diagnostics_{lang_id}.yaml` for each applicable language (see [Editing the diagnostics YAML](#editing-the-diagnostics-yaml)).
5. Run the appropriate command below.

#### Editing the diagnostics YAML

`diagnostics_{lang_id}.yaml` in `coded_data/{lang_id}/planar_input/` is the source of truth for which analyses run for a language. After editing it, regenerate the derived TSV:

```bash
python -m coding sync-diagnostics-yaml --lang {lang_id}                  # dry run: show what would change
python -m coding sync-diagnostics-yaml --apply --lang {lang_id}          # regenerate TSV from YAML
python -m coding sync-diagnostics-yaml --to-sheet --apply --lang {lang_id} # push YAML back to diagnostics Sheet
```

The `--to-sheet` direction is run automatically by `data-refresh.yml` after every import, so the diagnostics Google Sheet stays in sync with the YAML. Run it manually after renaming a class or criterion locally if you want the Sheet updated before the next daily refresh.

When `import-sheets` downloads a diagnostics TSV from Google Sheets that differs from the YAML, it diffs them automatically:
- **Deterministic changes** (known classes/criteria added or removed) are applied to the YAML by running `sync-diagnostics-yaml --from-tsv --apply`.
- **Ambiguous changes** (unknown class/criterion names, class removals) are written to `diagnostics_drift.json` and surface as a `diagnostics-drift` GitHub issue.

To resolve a `diagnostics-drift` issue:
1. Pull the latest data and run `python -m coding sync-diagnostics-yaml --from-tsv` (dry run) to see the diff.
2. Edit the YAML directly for any ambiguous items.
3. Run `python -m coding sync-diagnostics-yaml --apply` to regenerate the TSV from the corrected YAML.

#### Adding a new analysis class

After step 4 above:

```bash
python -m coding generate-sheets      # creates annotation sheets for the new class
python -m coding sync-params --apply  # if existing sheets need the new criteria columns
```

#### Updating diagnostic criteria

**Adding new criteria** — edit `diagnostics_{lang_id}.yaml` and commit. The daily `data-refresh.yml` runs `sync-params --apply` automatically, so the new column will appear in annotation sheets within 24 hours. No manual action needed.

**Destructive operations** (rename, remove, split, merge) are never automated — they require explicit flags and coordinator judgment:

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

#### Renaming an analysis class

**Required ordering:**
1. Update `diagnostics_{lang_id}.yaml` for all affected languages to use the new class name, then run `sync-diagnostics-yaml --apply` to regenerate the TSV.
2. Run `restructure-sheets --rename-class` (pre-flight check enforces this order).

```bash
# Dry run — shows what would be archived, created, and renamed
python -m coding restructure-sheets --rename-class old_class:new_class

# Apply — archives old sheet, creates new sheet under new name, renames local TSV directory
python -m coding restructure-sheets --rename-class old_class:new_class --apply

# Multiple renames in one pass
python -m coding restructure-sheets --rename-class old1:new1 --rename-class old2:new2 --apply
```

For each renamed class, `--apply` archives the old spreadsheet, creates a new one under the new name with all annotations carried over, renames `coded_data/{lang}/{old}/` to `coded_data/{lang}/{new}/` in-place (preserving git history), and updates the Drive manifest.

**Do NOT use `prune-manifest` for a rename** — it would discard annotation data. `prune-manifest` is for retiring a class entirely.

#### Retiring an analysis class

Remove the class from `diagnostics_{lang_id}.yaml` and run `sync-diagnostics-yaml --apply` to regenerate the TSV, then run `prune-manifest` to clean up:

```bash
python -m coding prune-manifest                  # dry run — show what would be archived and removed
python -m coding prune-manifest --apply          # archive TSVs and remove manifest entries
python -m coding prune-manifest --apply --all    # same, skipping per-class confirmation prompts
```

For each retired class, `--apply`:
1. Writes a timestamped manifest snapshot to `manifest_archives/` (local audit trail, gitignored)
2. Archives each active TSV in `coded_data/{lang}/{class}/` to its `archive/` subdirectory
3. Moves the Drive spreadsheet into an `_archived/` subfolder inside the language's Drive folder
4. Removes the class entry from the Drive manifest

The Drive sheet is moved, not deleted — annotation data is irreplaceable. A warning is shown if the sheet was edited within the last 14 days (possible unapplied annotation work). If the move fails for any reason, a warning is printed and the sheet can be moved manually from Drive; the manifest entry is still removed.

If `prune-manifest` warns "this class contains annotation data — consider `--rename-class` instead", check whether the class was renamed rather than retired before proceeding.

### Sheet maintenance

For changes to the planar structure itself — positions added, dropped, or renamed.

#### Adding elements to the planar structure

When new elements are added to `planar_input/planar_{lang_id}-{date}.tsv`:

```bash
python -m coding update-sheets           # dry run — show what would change
python -m coding update-sheets --apply   # add missing rows to existing sheets
```

If you see `(quota exceeded — waiting Xs before retry)` messages, the command is handling Google Sheets API rate limits automatically — just let it run.

#### Restructuring after planar changes

When position numbers change or rows are reordered:

```bash
python -m coding restructure-sheets                                            # dry run
python -m coding restructure-sheets --apply                                    # archive old sheets, regenerate
python -m coding restructure-sheets --rename-map "old_pos:new_pos" --apply    # carry over renamed positions
python -m coding restructure-sheets --rename-element Ad-VP:AD-VP --apply      # carry over renamed elements
```

Only classes with actual changes are archived; unchanged classes are left untouched. Automatically regenerates and uploads notebooks afterward.

### Health checks

Two commands cover project health at different levels of detail. Run both after any significant change — new language, schema edit, or module addition.

```bash
python -m coding integrity-check                      # full health report — all languages, all schemas
python -m coding integrity-check --lang arao1248      # one language only
python -m coding integrity-check --sheets             # also validate live Google Sheets structure
```

`integrity-check` runs six sections: PLANAR STRUCTURE, DIAGNOSTICS, CODEBOOK CONSISTENCY, ANALYSIS CONSISTENCY, ANNOTATION SHEETS (with `--sheets`), and NEEDS REVIEW. Use it as the first tool when starting an audit or after any major change.

```bash
python -m coding check-codebook
```

`check-codebook` provides lower-level schema detail and three informational reports:
- **keystone_active unresolved** (section 6): active (language, class) pairs whose `keystone_active_default` is `[NEEDS REVIEW]` and have no language-level override — a reminder to declare an explicit value when the linguistic question is resolved
- **Schema stubs** (section 7): classes with no language coverage, with a ready-to-paste `diagnostics_{lang_id}.tsv` row for each
- **Coverage matrix** (section 8): language × class grid showing which classes are active per language

Use `check-codebook` when adding criteria or classes, or when `integrity-check` flags a codebook inconsistency and you want more detail. `integrity-check` includes all `check-codebook` checks; `check-codebook` is faster and more detailed for schema-specific diagnosis.

---

## Tool roles

Each checker has a defined scope. New validation belongs in one of these tools, not in a new script.

| Tool | Role | When to reach for it |
|------|------|----------------------|
| `integrity-check` | Full project health report across all layers | After any major change; start of an audit session |
| `check-codebook` | Schema/module/diagnostics consistency + schema stubs + coverage matrix | When adding a class or criterion; for detailed codebook diagnostics |
| `validate-coding` | Live annotation sheet values + pink cell highlights | Before a review cycle; runs automatically via `sheet-validation.yml` |
| `check-snapshots` | Snapshot regression against current analysis output | Runs automatically via pre-push hook and CI |

---

## Reference

### Makefile aliases

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

### Schema utilities

Two standalone scripts in the repo root generate human-readable views of the schema files:

```bash
python render_codebook.py              # print schema reference to stdout
python render_codebook.py codebook.md # write to file

python generate_diagram.py out.svg    # analysis class taxonomy diagram (requires Graphviz)
python generate_diagram.py out.pdf    # same, PDF output
```

`generate_diagram.py` shows all analysis classes grouped by domain type, with diagnostic criteria inside each node and the languages that instantiate each class connected on the right.

### Regression testing and hooks

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

#### Local snapshot hooks (recommended)

Two local hooks keep snapshots in sync automatically. Install both at once after setting up the project:

```bash
.venv/bin/pip install pre-commit
.venv/bin/pre-commit install                              # pre-commit hook (auto-regenerate)
.venv/bin/pre-commit install --hook-type pre-push        # pre-push hook (safety check)
```

**Pre-commit hook (`regenerate-snapshots`):** Triggers whenever any `planars/*.py` file is staged. Regenerates all snapshots and stages the updated files automatically, so snapshot updates are always included in the same commit as the analysis change.

**Pre-push hook (`check-snapshots`):** Runs `check_snapshots.py` against the full local state before every push. Blocks the push if any snapshots are stale — a safety net for cases the pre-commit hook didn't catch.

If the pre-push hook blocks and the diff is intentional, regenerate and commit manually before pushing:

```bash
python generate_snapshots.py
git diff tests/snapshots/       # review
git add tests/snapshots/
git commit -m "Update snapshots: ..."
git push
```

CI also runs `check_snapshots.py` as a dedicated step, so stale snapshots will fail the build even if neither hook is installed.

### Automated workflows

Three daily GitHub Actions workflows run at 06:00 UTC. All three use the same four secrets.

#### Secrets setup

Add the following secrets under **Settings → Secrets and variables → Actions** in the GitHub repo:

| Secret | Where to get it |
|--------|-----------------|
| `PLANARS_DATA_TOKEN` | Already exists — used by the existing CI workflow to read `jcgood/planars-data`. No action needed. |
| `PLANARS_OAUTH_CREDENTIALS` | Contents of `~/.config/planars/oauth_credentials.json` on your laptop — the OAuth client secret downloaded from Google Cloud Console during initial setup. |
| `GOOGLE_OAUTH_TOKEN` | Contents of `~/.config/gspread/authorized_user.json` on your laptop — written by gspread after your first interactive login. Contains a refresh token so the workflow can renew its Google access silently. Stays valid as long as the workflow runs at least once every few months. |

Note: `drive_config.json` is **committed to the repo** (it contains only Drive folder and sheet IDs, no credentials) and is read directly by the workflows — no secret is needed for it.

#### What each workflow does

**`data-refresh.yml`** — the main daily automation pipeline. Runs at 06:00 UTC and does the following in order:

1. Records planars-data HEAD and any human-committed files (for overwrite detection later).
2. Imports latest annotation data from Google Sheets into planars-data (`import-sheets --apply`).
3. Regenerates all diagnostics TSVs from their YAML source of truth (`sync-diagnostics-yaml --apply`).
4. Pushes YAML content back to the diagnostics Google Sheets (`sync-diagnostics-yaml --to-sheet --apply`), keeping Sheets in sync after any class or criterion renames.
5. Adds missing criterion columns and updates dropdown validation in annotation sheets (`sync-params --apply`). Additive only — destructive operations remain manual.
6. Checks for ambiguous TSV→YAML drift and files a `diagnostics-drift` issue if found.
7. Runs `check-codebook` and files a `codebook-error` issue if schema inconsistencies are found.
8. Runs `integrity-check --check-manifest` and files a `stale-manifest` issue if retired classes remain in the Drive manifest.
9. Runs `integrity-check` (non-sheets) and files an `integrity-error` issue if planar structure or analysis module errors are found.
10. Regenerates snapshot baselines and commits them (`if: always()` — runs even if earlier steps failed).
11. Commits and pushes planars-data changes.
12. Detects whether the import overwrote any human commits to planars-data and files a `data-overwrite` issue if so.
13. Applies additive sheet updates (`update-sheets --apply`) and files a `sheet-drift` issue for any remaining non-additive drift.
14. Writes an annotation scope summary (language/class/construction counts) to the run's step summary.

All issue types are auto-closed on the next clean run. You can trigger the workflow manually from the Actions tab after a large annotation session to sync immediately.

**`sheet-validation.yml`** — runs `validate-coding` against all live Google Sheets and opens a GitHub issue labeled `sheet-validation` if problems are found. Closes the issue automatically when the next run comes back clean.

**`generate-reports.yml`** — runs `generate-reports --apply` and uploads refreshed PDF reports to Drive. The report timestamp at the top of each PDF shows when it was last regenerated. You can trigger it manually at any time. Requires WeasyPrint system libraries (installed automatically in the workflow; not needed locally unless you run `generate-reports --apply` yourself).

### Drive folder structure

The Drive manifest (`manifest.json`) is stored on Drive and contains all languages' sheet metadata and folder IDs. `drive_config.json` (committed to the repo) bootstraps the Drive lookup — it holds `_root_folder_id`, `_planars_config_file_id`, and per-language `folder_id`, `planar_spreadsheet_id`, and `diagnostics_spreadsheet_id`. It contains no credentials, only IDs, so it is safe to commit.

`drive_config.json` is created and updated automatically — you never need to edit it by hand. `generate-sheets` writes per-language IDs as it creates Drive folders and files; `setup-root-folder` adds the top-level `_root_folder_id`.

Each `generate-sheets` run also creates an editable Google Sheet for `planar_*.tsv` in the language's Drive folder so collaborators can view (and coordinators can edit) the planar structure alongside their annotation sheets. The `diagnostics_{lang_id}.tsv` Sheet is a read-only view — a derived artifact. To change diagnostics, edit `diagnostics_{lang_id}.yaml` locally and run `sync-diagnostics-yaml --apply`. `import-sheets` reads the planar Sheet back to local TSVs and detects any changes.

#### First-time project setup

After the very first `generate-sheets`, run `setup-root-folder` once to create the top-level `ConstituencyTypology` Drive folder and move shared files there:

```bash
python -m coding setup-root-folder
```

This is idempotent — safe to re-run, but only needs to happen once per project.

#### Joining an existing project

`drive_config.json` is committed to the `planars` repo and will be present in your clone automatically — no file sharing needed. It contains only Drive folder and sheet IDs (no credentials), so it is safe to commit. Once you have cloned the repo and set up the three GitHub Actions secrets above, the workflows can locate the existing Drive manifest and language folders without any additional configuration.
