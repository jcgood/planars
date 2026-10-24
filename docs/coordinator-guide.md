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
| Daily, scheduled 06:00 UTC (GitHub often starts it hours later) | `data-refresh.yml` → `python -m coding daily-refresh --apply` | Imports the latest sheets, syncs, checks, rebuilds status sheets and snapshots, commits; files or closes one issue per kind of problem (see [What each workflow does](#what-each-workflow-does)) |
| Daily, scheduled 09:00 UTC | `sheet-validation.yml` | Runs `validate-coding`; opens a `sheet-validation` issue if problems found; closes it when clean |
| After each data refresh | `generate-reports.yml` | Generates and uploads PDF reports to Drive |

The hooks require a one-time install per machine — see [Regression testing and hooks](#regression-testing-and-hooks). The GitHub Actions require secrets configured in the repo — see [Automated workflows](#automated-workflows).

**When something goes wrong automatically:** the daily workflows open labeled GitHub issues so nothing is silently dropped. Check the Issues tab if something looks out of sync. Every label, what it means and how to resolve it is in the [Labels table in CLAUDE.md](../CLAUDE.md#labels), which is generated from `schemas/issue_labels.yaml` — the one place labels are defined. To add a label, add it there and commit; the daily refresh creates it on GitHub.

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

**Re-authorization after scope changes:** if a new Google API scope is added to the project (e.g., the `documents` scope added for collaborator notes), the cached token at `~/.config/gspread/authorized_user.json` will not include that scope. Delete it and trigger a fresh browser authorization with a non-destructive command:

```bash
rm ~/.config/gspread/authorized_user.json
python -m coding integrity-check --sheets
```

A browser window will open for re-authorization. After completing it, update the `GOOGLE_OAUTH_TOKEN` secret in GitHub Actions with the contents of the newly refreshed `~/.config/gspread/authorized_user.json` so the nightly runs work too.

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

The tooling keeps its own record of its work in `coded_data/.state/`: pending
changes, the log of every Drive write, each tab as it was before a rebuild
replaced it, and the journal of an interrupted `restructure-sheets`. Every
command commits and pushes those files itself when it ends, so you never
commit them by hand, and the daily refresh's copies reach you with a pull
(`coding/state_files.py`).

The same goes for a language's files that a command writes: annotation
TSVs, the planar file, the diagnostics YAML and TSV. Every such write goes
through the local-file door (`coding/file_door.py`), which keeps the
previous version in the language's `archive/` folder, adds a line to the
language's `changes.tsv` (when, which file, what changed, which command,
why, where the previous version went), and commits and pushes the files
when the command ends. `changes.tsv` opens in a spreadsheet: it is the
place to look for what changed in a file and why, without git. Only your
own hand edits (to the YAML or the planar) still need committing by hand.

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
   If the annotator is new, add them to `coded_data/people.yaml` (private planars-data), keyed by the name exactly as `languages.yaml` writes it: their `email` (the sheets are shared with it), and their `github` username if they have one. Commit and push it in `coded_data/`.
   ```yaml
   Annotator Name:
     email: annotator@example.org
     github: their-username   # leave out if they have none
   ```
   With a GitHub username, they hear about values to fix by an @-mention on a `needs-fixing` issue. Without one, they hear by a comment on their spreadsheet that names their address, which makes Google email them (`coding/annotator_notices.py`, issue #309). **That second route has not yet been tried live**: for the first annotator without GitHub, check with them that the email arrives the first time they have something to fix.

   Commit `schemas/languages.yaml` to the `planars` repo before running `generate-sheets` — this ensures display names appear correctly in notebooks and charts:
   ```bash
   git add schemas/languages.yaml
   git commit -m "Register {lang_id} in languages.yaml"
   ```

2. In `coded_data/`, create:
   - `{lang_id}/lang_setup/planar_{lang_id}.tsv` — planar structure
   - `{lang_id}/lang_setup/diagnostics_{lang_id}.yaml` — analysis classes and diagnostic criteria (YAML is the source of truth; the TSV is generated from it)

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
   python -m coding generate-sheets --apply
   ```
   This creates one Google Sheets file per analysis class, uploads contributor and coordinator Colab notebooks to Drive, creates read-only Google Sheets copying the planar structure and diagnostics files, and updates the Drive manifest. On re-runs, only classes not yet in the manifest are created. Omit `--apply` first to see a dry-run report of what would be created.

4. If this is the first language in the project, run `setup-root-folder` once after `generate-sheets` — see [Drive folder structure](#drive-folder-structure) below.

5. Share the language Drive folder and the contributor notebook link with your collaborator.

6. After collaborators have filled in sheets, import and verify:
   ```bash
   python -m coding import-sheets
   python -m coding integrity-check --lang {lang_id}
   ```

### Annotation cycle

#### 1. Generate annotation forms

```bash
python -m coding generate-sheets                    # dry run: show what would be created
python -m coding generate-sheets --apply             # creates sheets for new classes only
python -m coding generate-sheets --force --apply     # blocked with a hard error if annotation sheets already exist
```

**If `generate-sheets --apply` aborts with "already exists in the Drive folder but is not registered in the manifest":** a spreadsheet with that name is in Drive but not in the manifest. This usually means a previous run created an orphaned sheet (e.g. after clearing the manifest during debugging). Resolve by either (a) registering the existing sheet — add its spreadsheet ID to that class's manifest entry (ask Claude; the manifest is on Drive), as the error message says — or (b) moving the sheet to `_archived/` in the language's Drive folder and re-running `generate-sheets --apply`.

Creates one Google Sheets file per analysis class with one tab per construction. Each tab has per-criterion dropdown validation, an optional **Source** column (page or section reference justifying each annotation, e.g. `§4.3`, `p. 217`, `Table 6.2`), and a free-text **Comments** column. Source comes before Comments; both are free-text and not validated. Each spreadsheet also gets a **Status tab** (always the last tab) with one row per construction and a dropdown (`in-progress` / `ready-for-review`). Also runs `generate-notebooks` automatically at the end.

At the start of each run, the current Drive manifest is backed up to `manifest_backup.json` (gitignored) in the repo root. If something goes wrong during a run, this file can be used to recover sheet IDs without needing to access Drive directly.

#### 2. Collaborators annotate

Collaborators fill in values in the shared Google Sheets. See the [Collaborator guide](collaborator-guide.md). Keystone rows (`v:verbstem`) are pre-filled with `NA` and should not be changed.

**Blank / `?` / `NA` / `untestable` semantics** — these four values are distinct and should not be used interchangeably:

| Value | Meaning | Import behavior |
|-------|---------|-----------------|
| blank | Not yet annotated — annotator has not examined this element | Warning on import; excluded from span computations |
| `?` | Uncertain — source was consulted but answer could not be determined | Warning on import; excluded from span computations |
| `NA` | Not applicable — criterion inapplicable by design for this position | Silently accepted; excluded from span computations |
| `untestable` | Untestable — the required construction cannot appear for independent reasons | Silently accepted; excluded from span computations |

The blank/`?` distinction matters for data quality: a `?` is a positive annotation of uncertainty ("I looked and could not decide"), while a blank means the cell has not been filled. Both are flagged on import, but they are semantically different — especially for cross-database comparison.

The `NA`/`untestable` distinction also matters: `NA` means the criterion is inapplicable *by design* for that position (e.g. the keystone), whereas `untestable` means annotation was *attempted* but the required construction cannot appear for independent grammatical reasons. `untestable` is opt-in — it appears in a criterion's dropdown only when listed in that criterion's `values` in `diagnostics_{lang_id}.yaml` (currently: coreference pair criteria). `NA` does not appear in any dropdown (annotators type it manually for keystone rows).

When a construction is complete, the collaborator sets its row in the **Status tab** to `ready-for-review`. This signals to the coordinator that the construction is ready to import.

From then on, an invalid value on that tab is an error, not just a pink cell (issue #309; the rule is `validate_coding.needs_fixing`). `validate-coding` (daily, `sheet-validation.yml`, and at the end of `import-sheets --apply`) lists each one in the Status tab's **Needs fixing** column, one line per cell naming the row, element, column, value and what it should be, and blanks the cell once the tab is clean; the `sheet-validation` issue reports them to the coordinator. `update-sheets --apply` adds the column to a sheet that predates it. An invalid value is never an `import-error`: that issue means the import itself broke.

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

#### 2c. Comments cells

A sheet's **Comments** column is the annotator's other channel to you: questions, doubts about a value, a test that doesn't fit. (Examples go in **Example**, page references in **Source**; the tooling never writes in Comments.) The daily refresh runs `check-comments --apply` after the import: every new or changed comment goes into one `collaborator-comments` issue per language, with its tab, row, answers and a ready-to-paste Claude prompt. Paste the prompt into a Claude Code session; it sorts the comments and drafts replies and issues for you to approve. Then close the issue. No API key is involved: the refresh only collects, and the session you start does the reading.

```bash
python -m coding check-comments          # dry run: what would be filed
python -m coding check-comments --apply  # file/update the issues, save what was seen
```

#### 3. Import filled sheets

```bash
python -m coding import-sheets                               # dry run: show what would be written
python -m coding import-sheets --apply                       # import ready-for-review constructions only
python -m coding import-sheets --apply --ignore-status       # import all constructions regardless of status
python -m coding import-sheets --apply --overwrite-existing  # also rewrite TSVs whose cells match but whose text differs
```

Dry-run by default — pass `--apply` to write any TSVs. A TSV whose cells match the sheet is skipped; a changed one is rewritten, its previous version kept in `coded_data/{lang_id}/archive/{class}/` and the change logged in `coded_data/{lang_id}/changes.tsv` (the local-file door, below).

Only the class sheets are imported. The planar and diagnostics Sheets are read-only copies of `planar_{lang_id}.tsv` and `diagnostics_{lang_id}.yaml`, rebuilt daily and never read back; see [Changing the planar or the diagnostics](#changing-the-planar-or-the-diagnostics).

If any annotation warnings are found, they are written to `import_errors/{lang}_{timestamp}.txt` as well as printed to the terminal. Invalid cells are highlighted pink in the Google Sheet regardless of `--overwrite-existing`.

#### 4. Run analyses

Spans are computed for you; there is no command to run. Each place shows them:

- **Colab notebooks**, per language, for coordinators and contributors. See the [Notebooks guide](notebooks.md).
- **PDF reports** on Drive (`generate-reports --apply`).
- **Snapshot files** in `tests/snapshots/` (`{lang}_{class}_{construction}.txt`), one per tab, regenerated by the daily refresh after each import. A change in a snapshot's git diff is a change in that tab's spans. To see the spans from a TSV you've just edited locally, run `python generate_snapshots.py` and look at `git diff tests/snapshots/`.

See [analyses.md](analyses.md) for what each analysis computes.

#### Cross-sheet criterion consistency

Some criteria appear in more than one sheet. Currently:

- **`free`** appears in both `noninterruption` and `free_occurrence`. The `free_occurrence` sheet is generated with `free` **pre-filled from the noninterruption TSV** — annotate noninterruption first, then generate the free_occurrence sheet. Free elements (`free=y`) receive `na` in all annotation columns; bound elements (`free=n`) have all annotation columns left blank to fill in.

If noninterruption is updated after the free_occurrence sheet is generated, the two sheets can drift. `python -m coding integrity-check` includes a **CROSS-SHEET CONSISTENCY** section that compares `free` values and reports mismatches as warnings. A mismatch usually means noninterruption was corrected after free_occurrence was generated — update the free_occurrence sheet to match, or regenerate it.

### Updating a span rule

A **span rule** is the formal description of how span computations work for an analysis class — which criterion values put a position inside the span, whether strict or loose spans are computed, and what blocking conditions apply. The rule text lives in `schemas/diagnostic_classes.yaml` under `span_rule:`, and the Python module in `planars/` must implement exactly that rule.

To guard against the rule and code drifting apart, `schemas/diagnostic_classes_status.yaml` stores a `span_rule_hash` for each class — a short fingerprint of the rule text, kept in a separate file from the rule itself because it's process bookkeeping (when was this last reviewed), not a linguistic fact (see that file's own header for why). `check-codebook` (and CI) verify that the hash matches the current rule. If you edit the rule text without updating the hash, CI files a `codebook-error` issue.

#### How to recognize the error

The `codebook-error` GitHub issue body will contain a line like:

```
✗ [metrical] span_rule_hash mismatch: diagnostic_classes_status.yaml has "56e9aeb2"
  but span_rule hashes to "a1b2c3d4" — the rule was edited without a module review
  cycle; run: python -m coding generate-rule-update-prompt metrical
```

#### The 7-step workflow

1. Edit `span_rule` in `schemas/diagnostic_classes.yaml`.
2. `check-codebook` (CI or local) detects the hash mismatch → `codebook-error` issue filed.
   The issue body includes a ready-to-paste Claude prompt.
3. Copy the Claude prompt from the issue and paste it into a Claude Code session.
4. Claude reads the new rule, updates `planars/{name}.py` (logic + docstring), runs tests.
5. Review the diff.
6. Stamp the new hash:
   ```bash
   python -m coding sync-span-rule-hashes --apply --class {name}
   ```
7. `check-codebook` passes → `codebook-error` issue auto-closes.

Claude enters only at step 3, with all context pre-assembled. Steps 1, 2, 5–7 are fully deterministic.

#### What "the hash" means

`span_rule_hash` is a record that the Python module was verified against this exact rule text. It does **not** guarantee correctness — that is Claude's job in step 4. It guarantees that a human reviewed the change. Run `sync-span-rule-hashes --apply` only after you are satisfied with the module diff.

#### Generating a prompt manually

If you want to update a module without waiting for CI:

```bash
python -m coding generate-rule-update-prompt metrical   # one class
python -m coding generate-rule-update-prompt            # all stale classes
```

The prompt includes the current rule text, the current module source, and the exact command to run afterward.

#### If the change is non-trivial or you are unsure

Paste the generated prompt into Claude and ask it to explain what changed before making any edits. The prompt contains enough context for Claude to reason about the linguistic implications of the rule change.

### Reviewing a span rule with the domain expert

The hash records that the code matches the span rule. Whether the span rule is *right* is a separate question, and only the domain expert (Adam, or an equivalent coordinator) can answer it. Until they do, the class's `status` in `schemas/diagnostic_classes_status.yaml` stays `[AUTO-DERIVED]` or `[NEEDS REVIEW]`.

The expert works through the classes with their own Claude, using a language whose annotation is complete enough to give real spans. A tracking issue (labels `linguistics` and `needs-input`, assigned to the expert) holds the order, one checkbox per class, and the known questions for each. The expert and Claude agree the rule. The expert's Claude writes it into the YAML. The other coordinator's Claude then makes the code match. The steps below are written for the expert's Claude.

**For each class, in the issue's order:**

1. **Get current.** Pull this repo and `coded_data/`, then run `python generate_snapshots.py`. The spans the rule gives today are in `tests/snapshots/{lang_id}_{class}_*.txt`.
2. **Read** the following:
   - the class's entry in `schemas/diagnostic_classes.yaml`: `span_rule`, criteria and applicability;
   - its criteria in `schemas/diagnostic_criteria.yaml`;
   - `schemas/terms.yaml`;
   - the module docstring in `planars/{class}.py`;
   - the language's TSVs in `coded_data/{lang_id}/{class}/`, including their Example and Comments columns;
   - the snapshots;
   - the issues the tracking issue names for that class.
3. **Walk the expert through it** in plain words, a few lines at a time. Cover what the rule does now, what spans their answers give, and each place where the answers and the rule seem to disagree. Put each disagreement as a question, and say what changes under either answer. Where it helps, work out the spans an alternative would give with a scratch script, without changing the module.
4. **Agree the rule.** It must say what every value a criterion can take does to the span: `y`, `n`, `both`, `na`, `?` and blank. No value may be left to a default (CLAUDE.md, "Explicit, not implicit"). It must also say how complete and partial positions and strict and loose spans are formed, where the class uses them. Use the words in `terms.yaml`. There are three possible outcomes:
   - **Confirmed as is.** Comment that on the tracking issue and tick the box. The expert sets `status: stable` in `diagnostic_classes_status.yaml`, citing the issue. Only a coordinator promotes a class.
   - **The rule changes.** Go to step 5.
   - **The data was wrong.** The expert fixes the sheet. After the next daily import, regenerate the snapshots and look again.
5. **Write it on a branch**, `span-rule/{class}`.
   - Edit `span_rule` in `diagnostic_classes.yaml`. If a criterion's meaning turned out to be unclear, also edit its description in `diagnostic_criteria.yaml`.
   - Change nothing else: not the module, not the hash, not `status`.
   - Run `python -m coding check-codebook`. The only error should be that class's hash mismatch, which is the sign that the code hasn't caught up yet.
6. **Open a pull request** titled `Span rule: {class}`, and comment the link on the tracking issue. Its body gives:
   - the agreed rule in plain words;
   - each decision and its reason;
   - the spans the new rule should give for the language.

   The test suite will fail on the hash until the code is updated. That is expected.
7. **The other coordinator** reviews the pull request. They then follow the 7-step workflow above (module, docstring, tests, snapshots) on the same branch. They check that the spans match what the pull request said, stamp the hash and merge. The expert ticks the box and promotes the class.

Answers on one class often settle a question several classes share, such as what `na` means to a span (#133). Record those on the shared issue as well, so later classes start from them.

---

### Schema changes

When the diagnostic model changes — a new analysis class, a class renamed or retired, or criteria added or modified — the general sequence is:

1. Edit `schemas/diagnostic_classes.yaml` (add the class, set required criteria, span rule, etc.)
2. Scaffold or rename the analysis module in `planars/` if needed.
3. Run `check-codebook` to verify consistency and get a ready-to-paste schema stub:
   ```bash
   python -m coding check-codebook
   ```
   Section 5 prints the TSV row to paste into each applicable language's `diagnostics_{lang_id}.tsv`. Section 6 shows the current language × class coverage matrix.
4. Edit `diagnostics_{lang_id}.yaml` for each applicable language (see [Editing the diagnostics YAML](#editing-the-diagnostics-yaml)).
5. Run the appropriate command below.

#### Editing the diagnostics YAML

`diagnostics_{lang_id}.yaml` in `coded_data/{lang_id}/lang_setup/` is the source of truth for which analyses run for a language. After editing it, regenerate the derived TSV:

```bash
python -m coding sync-diagnostics-yaml --lang {lang_id}                  # dry run: show what would change
python -m coding sync-diagnostics-yaml --apply --lang {lang_id}          # regenerate TSV from YAML
python -m coding sync-diagnostics-yaml --to-sheet --apply --lang {lang_id} # copy the YAML to the diagnostics Sheet
```

The daily refresh runs both, so the TSV and the diagnostics Google Sheet follow the YAML within a day. Run them by hand only if you want the Sheet updated sooner.

#### Changing the planar or the diagnostics

`planar_{lang_id}.tsv` and `diagnostics_{lang_id}.yaml` in planars-data are the only places to change a language's planar structure or diagnostics. The planar and diagnostics Google Sheets are read-only copies for the annotator (Phase 10 unit 11b, 2026-10-24): nothing is ever read back from them, and the daily refresh rebuilds them (`sync-planar --apply`, `sync-diagnostics-yaml --to-sheet --apply`).

- **You** edit the file, commit it in planars-data, and let the daily refresh carry it to the Sheets (or run the command now).
- **An annotator** suggests a change on the language's "planars and diagnostics" sheet (e.g. "English [stan1293] planars and diagnostics"; in the code, the proposal sheet); you review it with `accept-proposal`, which writes the accepted parts to the file. See [the collaborator guide](collaborator-guide.md#suggesting-changes-to-the-planar-structure-or-the-diagnostics).

When the planar's positions changed, `sync-planar` first renumbers any position numbers typed in the class sheets' answers, then updates the Sheet, and files a `planar-changed` issue naming the command that carries the change into the class sheets (`update-sheets` for added positions, `restructure-sheets` for moved, renamed or removed ones).

#### Adding a new analysis class

After step 4 above:

```bash
python -m coding generate-sheets --apply  # creates annotation sheets for the new class
python -m coding sync-params --apply      # if existing sheets need the new criteria columns
```

#### Multi-stage annotation workflows (nonpermutability and coreference)

Some classes have a multi-stage annotation structure where one construction must be completed before another can be generated.

**Nonpermutability** (2 stages):

1. Annotate the `element_prescreening` sheet (`scopal={y,n,both}` per element) and mark it `ready-for-review`.
2. Run `python -m coding import-sheets` to download it locally.
3. Regenerate the dependent `general` (pair-row) sheet filtered by the prescreening results:

```bash
python -m coding generate-sheets --lang LANG_ID --regen-construction nonpermutability:general
```

**Coreference** (4 stages — one prescreening + three pair constructions):

1. Annotate the `prescreening` sheet (`referential={y,n}` per element) and mark it `ready-for-review`. This identifies which elements can participate as binder or bindee. `NP{…}` rows arrive filled in as `y`.
2. Run `python -m coding import-sheets` to download it locally.
3. Regenerate each pair construction filtered to referential elements:

```bash
python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:reflexive_coreference
python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:pronoun_coreference
python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:np_coreference
```

Each pair sheet uses its own criterion column: `reflexive_allowed` (Principle A), `pronoun_allowed` (Principle B), `np_allowed` (Principle C).

4. Annotate each pair sheet and mark `ready-for-review` when done.

**For both classes:** if `integrity-check` or `data-refresh` files a **`dependent-stale`** issue, the pair sheet is out of sync with the current prescreening TSV (e.g. after a correction). Re-run the relevant `--regen-construction` command. The issue closes automatically when the element sets are back in sync.

`data-refresh` fills a dependent construction by itself when it has no rows: when the dependent TSV does not yet exist locally, or when it exists but is empty and its source tab has been marked `ready-for-review` in the Status tab. So an annotator who finishes a prescreening tab and marks it gets the next tab the following day, with no command to remember. Once the dependent has rows (even with blank values), it is never regenerated automatically; the `dependent-stale` issue body tells you which manual command to run.

**`--regen-construction` refuses to silently drop annotated pairs.** If regenerating would remove a pair-row that has a real (non-blank) criterion value, it aborts instead of writing, listing exactly what would be lost (element, value, Source, Comments) rather than letting it vanish from the Sheet. Two ways this comes up:

- **The element was renamed or split** — run `restructure-sheets --rename-element`/`--split-element` first (see below); that carries the judgment forward and the guard then passes cleanly, since the old rows are already gone by the time `--regen-construction` runs.
- **The position numbers shifted** (a position was inserted or deleted elsewhere in the planar structure) — the annotation is for a still-valid element, just filed under a stale position number. `integrity-check`'s DEPENDENT CONSTRUCTION STALENESS section detects this proactively (not just when you happen to hit the guard) and prints the exact `--pos-remap` flags to use — no need to compare old and new planar TSVs by hand:

```bash
python -m coding generate-sheets --lang LANG_ID --regen-construction coreference:reflexive_coreference \
    --pos-remap 5:6 --pos-remap 34:35
```

If the drop really is intentional — a genuine prescreening scope change, not a rename/split/renumbering — re-run with `--confirm-drop` to proceed anyway.

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

Preserves existing annotations while inserting each new column where `diagnostics_{lang_id}.yaml` lists it among the tab's criteria. Rename, split and merge also make the same change to the criteria in `diagnostics_{lang_id}.yaml` (only those lines change; comments are kept) and regenerate `diagnostics_{lang_id}.tsv` from it, so there is no need to edit the YAML by hand first; commit and push both files inside `coded_data/` afterwards. Rename updates headers and validation in place. Split/merge rename the old column(s) to `_split_`/`_merged_` prefixes and add the new column(s) — coordinator remaps values then removes stale columns manually. `integrity-check --sheets` warns on any stale prefixed columns. Automatically regenerates and uploads notebooks afterward.

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

#### Renaming a construction

A construction is a tab of a class sheet. Rename it in `schemas/diagnostic_classes.yaml` first (the command refuses until the schema lists the new name and not the old), then:

```bash
python -m coding rename-construction CLASS:OLD:NEW            # dry run, every language
python -m coding rename-construction CLASS:OLD:NEW --apply    # repeat CLASS:OLD:NEW for several
```

In every language that has it, `--apply` renames it in `diagnostics_{lang_id}.yaml` (and regenerates the TSV and the diagnostics Sheet), renames the tab and its Status row in place — the sheet keeps its link and its answers — and renames it in the manifest, the local TSV and check-comments' record. Tell the annotators: their tab has a new name. Do the schema commit, the run and both pushes in one sitting; the daily refresh would otherwise add an empty tab under the new name beside the answered one. A run that stopped partway is finished by running it again.

#### Retiring an analysis class

Remove the class from `diagnostics_{lang_id}.yaml` and run `sync-diagnostics-yaml --apply` to regenerate the TSV, then run `prune-manifest` to clean up:

```bash
python -m coding prune-manifest                  # dry run — show what would be archived and removed
python -m coding prune-manifest --apply          # archive TSVs and remove manifest entries
python -m coding prune-manifest --apply --all    # same, skipping per-class confirmation prompts
```

For each retired class, `--apply`:
1. Writes a timestamped manifest snapshot to `manifest_archives/` (local audit trail, gitignored)
2. Removes each TSV in `coded_data/{lang}/{class}/`, keeping its last version in `coded_data/{lang}/archive/{class}/` and logging it in the language's `changes.tsv` (committed and pushed when the command ends)
3. Moves the Drive spreadsheet into an `_archived/` subfolder inside the language's Drive folder
4. Removes the class entry from the Drive manifest

The Drive sheet is moved, not deleted — annotation data is irreplaceable. A warning is shown if the sheet was edited within the last 14 days (possible unapplied annotation work). If the move fails for any reason, a warning is printed and the sheet can be moved manually from Drive; the manifest entry is still removed.

If `prune-manifest` warns "this class contains annotation data — consider `--rename-class` instead", check whether the class was renamed rather than retired before proceeding.

### Sheet maintenance

For changes to the planar structure itself — positions added, dropped, or renamed.

#### Adding elements to the planar structure

Add them to `lang_setup/planar_{lang_id}.tsv` and commit and push it inside `coded_data/` (the daily refresh runs from what is on GitHub). The daily refresh updates the planar Sheet and adds the rows. To do it now:

```bash
python -m coding sync-planar --lang LANG_ID --apply   # the planar Sheet
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
python -m coding restructure-sheets --split-element "PRON{P,T}:me,you,him,her,it,us,them" --apply  # split one element into several
```

Only classes with actual changes are archived; unchanged classes are left untouched. Automatically regenerates and uploads notebooks afterward.

A position that only changed number needs no flag: answers are carried over by position name. **Position numbers written inside answers** (co_exponents, conditioned_by, dependent-on-left/right — annotators may write positions as numbers or names) are renumbered by `sync-planar` before it updates the planar Sheet: at the end of `restructure-sheets --apply`, or by the daily refresh, whichever comes first. The `planar-changed` issue lists every cell it renumbered, and under "Check these answers" any number whose position is gone, left as typed for the annotator to settle. If that renumbering fails, the planar Sheet is left as it was and the issue says why; the next refresh tries again.

`restructure-sheets` reads `planar_{lang_id}.tsv` but never writes it: edit the file first, then run it.

`--split-element old:new1,new2,...` retires one element in favor of several finer-grained replacements within the same position (e.g. a generic placeholder like `PRON{P,T}` replaced by specific pronoun forms). There's no principled way to carry a generic annotation over 1:1 to several specific new elements, so the new rows are left blank as usual — but if the old element had existing annotations, each new row's first answer cell gets a note (the small corner triangle) quoting them, so re-annotators see the prior judgment instead of having to remember it or hunt through Drive. The tooling never writes into `Comments`, which is the annotator's channel to you. Requires at least 2 comma-separated replacement elements; an element cannot appear in both `--rename-element` and `--split-element`.

**This also cascades into every pair-row construction that references the retired element** (`nonpermutability`'s `general`, `coreference`'s three constructions, and any future pair-row diagnostic — found generically, not hardcoded by class name), not just the element's "home" construction. Each old pair-row involving the retired element fans out into one new row per replacement element, left blank, with the old row's criterion value, `Example`, `Source` and `Comments` quoted in a note on the new row's criterion cell — the same blank-plus-note policy as above, just extended to pairs. A pair where *both* sides are the retired element (a self-pair) is left untouched and flagged for manual review rather than guessed at.

**Tell annotators to bookmark the Drive folder, not individual sheet links.** Every class spreadsheet gets a brand-new URL each time `restructure-sheets --apply` runs (the old one is archived, a new one is created) — any sheet link an annotator has bookmarked from before a restructure is now stale, pointing at an archived, no-longer-live copy. The failure mode is silent: a stale link still opens a perfectly normal-looking spreadsheet, just one that's disconnected from the manifest, so annotation done there would never reach `import-sheets`. The language's top-level Drive folder URL, by contrast, never changes — restructures only move old spreadsheets into an `_archived/` subfolder *within* it and create new ones directly in it. `restructure-sheets --apply` prints this folder link (labeled "Bookmark this instead") alongside the per-class sheet links in its final summary specifically so this doesn't need to be remembered separately each time.

#### Refreshing dropdowns after criterion value changes

The daily refresh runs `refresh-dropdowns --apply`, which reads each sheet's real dropdowns and makes them match the codebook: a criterion's allowed values from `diagnostics_{lang_id}.yaml`, and no dropdown on Example/Source/Comments or on a criterion that takes position numbers. It touches only dropdowns, never data or sheet structure. To see or apply a change at once rather than wait a day:

```bash
python -m coding refresh-dropdowns              # dry run — list each column whose dropdown differs
python -m coding refresh-dropdowns --apply      # fix them
python -m coding refresh-dropdowns --lang stan1293 --apply   # one language only
```

#### Collaborator status pages

Adam needs to find current Sheet links and completion status without hunting through Drive or asking the coordinator each time. `generate-status-sheet` builds one locked, read-only `status_{lang_id}` spreadsheet per language listing every construction from `diagnostics_{lang_id}.yaml`, with a completeness percentage, a color-coded status cell, and a direct link to that construction's live tab:

```bash
python -m coding generate-status-sheet                       # dry run — all languages
python -m coding generate-status-sheet --lang stan1293        # dry run — one language
python -m coding generate-status-sheet --lang stan1293 --apply
```

The spreadsheets live in a freestanding top-level "Annotation Status" Drive folder, outside the project's root folder, so they can be read-only for annotators while the annotation sheets are editable. Each status spreadsheet is shared read-only with its language's annotator by name (addresses come from private planars-data via `coding/people.py`); nothing in the project is shared "anyone with the link" except generated notebooks and PDF reports (policy since 2026-10-12, Phase 10 unit 14). Re-running `--apply` overwrites the existing `status_{lang_id}` spreadsheet in place rather than minting a new URL, since there's no annotation history to preserve. The daily `data-refresh` rebuilds every language's status sheet, so the percentages are at most a day behind the annotators' edits; if that rebuild fails it files a `status-sheet-error` issue. Run the command by hand only when someone needs today's numbers sooner.

### Health checks

#### Audit procedure

An audit is due when the daily refresh files an `audit` issue (it does when
none has been closed for 30 days, `daily_refresh.AUDIT_EVERY_DAYS`), and after
any change that cuts across the project, when the coordinator opens one by
hand. Either way the audit lives in that issue: Claude works through the
steps below, comments what it found and what was done about each finding, and
closes the issue. The closing date is the date of the last audit.

The daily refresh already runs every check and files an issue for each
failure, so an audit does not re-run checks for their own sake. It does the
three things the refresh can't: it looks at **warnings**, which never file an
issue; it confirms the checks are **actually running**, since a check that
stopped reporting looks exactly like a clean one (no live command was checked
for four days before unit 20's fix, and every refresh looked clean); and it
reads what changed since the last audit.

1. **Run the refresh and wait for it** (about 20 minutes):
   ```bash
   gh workflow run data-refresh.yml
   ```
   Then pull planars-data (`git -C coded_data pull`) so local checks see what it imported.

2. **Every open issue the tooling filed.** Each label in `schemas/issue_labels.yaml`
   whose `filed_by` is not "by hand" belongs to the tooling; list its open
   issues (`gh issue list --label LABEL`). For each one, either it is being
   handled (say by whom) or it is fixed now. An issue a later run should have
   closed but didn't is a bug.

3. **The checks ran.** In the refresh's log (`gh run view RUN_ID --log`):
   every step reached "done"; each writing command ends with a `Drive door
   (...): checked N write(s)` line (a writing step with no such line means the
   door didn't run); and the steps with no issue of their own (labels,
   collaborator notes, criterion columns, snapshots) succeeded. CI on the
   latest `main` commit is green (`gh run list --workflow ci.yml --limit 1`).

4. **Every warning.** Run
   ```bash
   python -m coding integrity-check
   python -m coding check-codebook
   ```
   and sort each warning into one of three: **fix it** (it's a bug, or the
   data is wrong — file or fix); **declare it** (it's expected; record the
   exception where the check reads it, so it stops printing); or **ask** (a
   linguistic question for Adam — find the issue that asks it, or file one).
   A warning that appears in every audit with no decision is the failure this
   step exists to catch.

5. **What changed since the last audit.**
   `git log --since=DATE --stat -- coding planars schemas` (DATE: when the
   last `audit` issue closed). For each module changed, read its docstring
   against what the code now does; a stale one is a bug, fixed in the same
   change. The tests already check commands named in text, files nothing
   reaches and typed copies of schema values (`tests/test_no_hidden_facts.py`,
   `tests/test_no_leftovers.py`), so this step is about described behaviour.

#### Running the checks

```bash
python -m coding integrity-check                      # full health report — all languages, all schemas
python -m coding integrity-check --lang arao1248      # one language only
python -m coding integrity-check --sheets             # also validate live Google Sheets structure
```

`integrity-check` runs six sections: PLANAR STRUCTURE, DIAGNOSTICS, CODEBOOK CONSISTENCY, ANALYSIS CONSISTENCY, ANNOTATION SHEETS (with `--sheets`), and NEEDS REVIEW. The daily refresh runs it and files `integrity-error` on an error; its warnings file nothing and are read during an audit (see Audit procedure above).

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
| `integrity-check` | Full project health report across all layers | After any major change; an audit's warnings step |
| `check-codebook` | Schema/module/diagnostics consistency + schema stubs + coverage matrix | When adding a class or criterion; for detailed codebook diagnostics |
| `validate-coding` | Validates local TSVs + updates pink cell highlights and each Status tab's Needs fixing column in Sheets | Before a review cycle; runs automatically via `sheet-validation.yml`. Requires local TSVs — run `import-sheets` first if missing. |
| `check-snapshots` | Snapshot regression against current analysis output | Runs automatically via pre-push hook and CI |

---

## Reference

### Makefile aliases

A `Makefile` in the repo root provides short aliases for all common commands. Run `make help` for the full list. Examples:

```bash
make generate-sheets        # python -m coding generate-sheets  (dry run)
make generate-sheets-apply  # python -m coding generate-sheets --apply
make import-sheets          # python -m coding import-sheets  (dry run)
make import-sheets-apply    # python -m coding import-sheets --apply
make update-sheets          # python -m coding update-sheets  (dry run)
make update-sheets-apply    # python -m coding update-sheets --apply
make restructure-sheets       # python -m coding restructure-sheets  (dry run)
make restructure-sheets-apply # python -m coding restructure-sheets --apply  ⚠ destructive
make integrity-check        # python -m coding integrity-check
make lookup-lang LANG=arao1248
make test
make snapshots
```

For commands that accept extra flags not covered by the aliases (e.g. `--rename-map`, `--rename-element`, `--lang`), use the full `python -m coding ...` form directly. The venv must be activated before using `make` (see [Python environment](#python-environment) above).

### Command inventory

```bash
python -m coding registry                          # one line per command
python -m coding registry --command generate-sheets # full detail: flags, side effects,
                                                     # idempotency, preconditions, ordering
```

Derived fresh on every call from `coding/__main__.py`'s command table, each command's own flags, and `data_dependency_schema/operations.yaml` — never hand-maintained, so it can't go stale the way a written-out command list would.

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

Snapshot baselines live in `tests/snapshots/`. When analysis output changes intentionally (e.g., after a span rule fix), regenerate the baselines and review the diff before committing:

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

Three GitHub Actions workflows run daily (times in the table at the top of this guide). All three use the same secrets.

#### Secrets setup

Add the following secrets under **Settings → Secrets and variables → Actions** in the GitHub repo:

| Secret | Where to get it |
|--------|-----------------|
| `PLANARS_DATA_TOKEN` | Already exists — used by the existing CI workflow to read `jcgood/planars-data`. No action needed. |
| `PLANARS_OAUTH_CREDENTIALS` | Contents of `~/.config/planars/oauth_credentials.json` on your laptop — the OAuth client secret downloaded from Google Cloud Console during initial setup. |
| `GOOGLE_OAUTH_TOKEN` | Contents of `~/.config/gspread/authorized_user.json` on your laptop — written by gspread after your first interactive login. Contains a refresh token so the workflow can renew its Google access silently. Stays valid as long as the workflow runs at least once every few months. |

Note: `drive_config.json` lives in **planars-data** (`coded_data/drive_config.json`) — it holds only Drive folder and sheet IDs, no credentials, but those IDs point at unpublished data, so it stays out of the public `planars` repo (moved 2026-10-12). The workflows already check out planars-data, so no secret is needed for it.

#### What each workflow does

**`data-refresh.yml`** — the main daily automation pipeline. It sets up the machine and runs one command, `python -m coding daily-refresh --apply`, which imports the planars and annotation sheets, syncs the diagnostics files, adds new criterion columns and rows, checks everything, rebuilds the status sheets and snapshots, commits to planars-data, and files or closes one issue per kind of problem. To see every step in order, run it without `--apply`:

```bash
python -m coding daily-refresh
```

Each issue closes by itself on the next clean run. The run's summary page on GitHub (Actions → the run) shows each command's output and a table of the steps. You can trigger the workflow manually from the Actions tab after a large annotation session to sync immediately (`gh workflow run data-refresh.yml`).

**`sheet-validation.yml`** — runs `validate-coding` against all live Google Sheets and opens a GitHub issue labeled `sheet-validation` if problems are found. Closes the issue automatically when the next run comes back clean.

**`generate-reports.yml`** — runs `generate-reports --apply` and uploads refreshed PDF reports to Drive. The report timestamp at the top of each PDF shows when it was last regenerated. You can trigger it manually at any time. Requires WeasyPrint system libraries (installed automatically in the workflow; not needed locally unless you run `generate-reports --apply` yourself).

### Drive folder structure

The Drive manifest (`manifest.json`) is stored on Drive and contains all languages' sheet metadata and folder IDs. `coded_data/drive_config.json` (in planars-data) bootstraps the Drive lookup — it holds `_root_folder_id`, `_planars_config_file_id`, and per-language `folder_id`, `planar_spreadsheet_id`, and `diagnostics_spreadsheet_id`. It contains no credentials, only IDs; they point at unpublished data, so it lives in the private repo.

`drive_config.json` is created and updated automatically — you never need to edit it by hand. `generate-sheets` writes per-language IDs as it creates Drive folders and files; `setup-root-folder` adds the top-level `_root_folder_id`.

For a new language, `generate-sheets` also creates the planar and diagnostics Sheets in its Drive folder: read-only copies of `planar_{lang_id}.tsv` and `diagnostics_{lang_id}.yaml`, so collaborators can see them beside their annotation sheets. To change either, see [Changing the planar or the diagnostics](#changing-the-planar-or-the-diagnostics).

#### First-time project setup

After the very first `generate-sheets`, run `setup-root-folder` once to create the top-level `ConstituencyTypology` Drive folder and move shared files there:

```bash
python -m coding setup-root-folder
```

This is idempotent — safe to re-run, but only needs to happen once per project.

#### Joining an existing project

`drive_config.json` is in planars-data, so it arrives when you clone `planars-data` as `coded_data/` — no file sharing needed. Once you have cloned both repos and set up the three GitHub Actions secrets above, the workflows can locate the existing Drive manifest and language folders without any additional configuration.
