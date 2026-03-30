# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository structure

This repository (`planars`) contains the library and coordinator tooling. Annotation data lives in a **separate private repository**, `planars-data`, which is restricted to authorized coordinators.

Coordinators clone both repos and nest `planars-data` inside `planars` as `coded_data/`:

```bash
git clone https://github.com/jcgood/planars.git
git clone https://github.com/jcgood/planars-data.git planars/coded_data
```

`coded_data/` is a fully independent git repo nested inside `planars/`. The outer repo ignores it entirely (`coded_data/` is in `.gitignore`). All `coding/` scripts find data at the expected path with no extra configuration.

**Daily workflow — two separate git operations:**

```bash
# Committing code changes (inside planars/)
git add coding/generate_sheets.py
git commit -m "..."
git push

# Committing data changes (cd into coded_data first)
cd coded_data
git add stan1293/ciscategorial/general.tsv
git commit -m "..."
git push

# Pulling the latest code
cd /path/to/planars && git pull

# Pulling the latest annotation data
cd /path/to/planars/coded_data && git pull
```

Changes to code and data are always committed and pushed separately — they go to different repositories. `git pull` in `planars/` never touches `coded_data/`, and vice versa.

## Running the scripts

Full command reference with flags: [docs/coordinator-guide.md](docs/coordinator-guide.md). Quick reference:

```bash
# Sheet lifecycle
python -m coding generate-sheets          # create annotation sheets (--force blocked if sheets exist)
python -m coding import-sheets            # dry run: show what would be written
python -m coding import-sheets --apply    # download filled sheets → TSVs (--overwrite-existing to re-download)
python -m coding apply-pending            # review destructive changes written by import-sheets
python -m coding validate-coding          # re-validate + update pink highlights (--lang for one)

# Sheet maintenance
python -m coding sync-params              # sync criterion columns (--apply, --rename, --split, --merge, --remove)
python -m coding update-sheets            # add missing rows/columns (--apply)
python -m coding restructure-sheets       # archive + regenerate after planar changes (--apply, --rename-map, --rename-element, --rename-class)
python -m coding prune-manifest           # archive retired class TSVs and remove stale manifest entries (--apply, --all)

# Health checks
python -m coding integrity-check          # full project health report (--lang, --sheets)
python -m coding check-codebook           # criterion/module/diagnostics consistency

# Notebooks and reports
python -m coding generate-notebooks       # regenerate and upload Colab notebooks (--apply)
python -m coding generate-reports         # generate and upload PDF reports to Drive (--apply)

# Other
python -m coding lookup-lang arao1248     # fetch + cache Glottolog metadata (--refresh, --all)
python -m coding setup-root-folder        # one-time Drive folder setup
python -m planars <module> <tsv>          # run a single analysis

# Testing
pytest                                    # all tests (io, restructure, snapshots)
python generate_snapshots.py              # regenerate baselines; review with: git diff tests/snapshots/
```

**Setup** (first time or after recreating the venv):
```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```
The `-e .` line in `requirements.txt` installs the `planars` package in editable mode. Notebooks are run via Colab, not locally.

## Architecture and data flow

This is a linguistic typology analysis project for morphosyntactic domain derivation. The ultimate analytical goal is to test three hypotheses about constituency structure within a language (developed in Good, "Domains of linearization, constituency, and wordhood in Chichewa," draft): (i) **Tree hypothesis** — the domains of constituency diagnostics should nest within each other; (ii) **Morphosyntax/phonology divide hypothesis** — deviations from nesting are allowed between morphosyntactic and phonological diagnostics, but not within each class; (iii) **Word hypothesis** — a set of diagnostics will converge on a consistently small span that can be identified as a word domain, with the larger domain completely partitioned into such spans. The span computations performed by planars' analysis modules are the primary instrument for testing these hypotheses. The workflow is:

1. **Input** (`coded_data/{lang_id}/planar_input/`): `planar_<lang>-<date>.tsv` defines positions and elements for a language. `diagnostics_{lang_id}.tsv` specifies which analyses to run (class, construction, criteria). `coding/make_forms.py` provides utility functions used by other scripts (`build_element_index`, `_read_diagnostics_for_language`) — it no longer generates blank TSVs directly.

2. **Manual annotation**: Specialists fill in values via Google Sheets forms generated by `python -m coding generate-sheets`. Google Sheets is the definitive copy of annotation forms. The Sheets workflow creates one file per analysis class with one tab per construction, y/n dropdown validation, and a shared Drive folder. OAuth credentials must be at `~/.config/planars/oauth_credentials.json` (set `PLANARS_OAUTH_CREDENTIALS` to override). The token is cached after first authorization. The manifest is stored on Drive as a single merged `manifest.json` containing all languages' sheet metadata and folder IDs; `drive_config.json` (gitignored) bootstraps the Drive lookup by holding `_root_folder_id`, `_planars_config_file_id`, and per-language `folder_id`, `domains_notebook_file_id`, `planar_spreadsheet_id`, and `diagnostics_spreadsheet_id`. `python -m coding import-sheets` loads the manifest from Drive, downloads each annotation tab, validates values (warning on blanks or unexpected entries), and writes `{construction}.tsv` to `coded_data/{lang_id}/{class_name}/`. Existing files are skipped unless `--overwrite-existing` is passed; when overwriting, the existing TSV is automatically archived to `coded_data/{lang_id}/{class_name}/archive/` before being replaced. `import-sheets` also aborts if `coded_data/` has uncommitted TSV changes (to protect local edits). It also downloads the planar and diagnostics Sheets for each language, validates them, auto-applies safe downstream commands (update-sheets, sync-params, generate-sheets), and writes destructive changes (deletions, reorders, renames, new construction tabs) to `pending_changes.json` for coordinator review. If any warnings are generated, they are written to `import_errors/{lang}_{timestamp}.txt` (gitignored) in addition to stdout. As a side effect, invalid cells are highlighted pink in the Google Sheet during import (the same write-back that `validate-coding` performs); this happens regardless of `--overwrite-existing` and even when a local TSV is skipped. When `diagnostics_{lang_id}.tsv` criterion columns change, use `python -m coding sync-params --apply` to add new columns to existing sheets while preserving annotations.

   **Drive folder structure**: `python -m coding setup-root-folder` (run once after the first `generate-sheets`) creates a top-level `ConstituencyTypology` Drive folder and moves `manifest.json` and `all_languages.ipynb` there. New language folders created afterwards are placed inside this root folder. `drive_config.json` tracks per-language `folder_id`, `domains_notebook_file_id`, `planar_spreadsheet_id`, and `diagnostics_spreadsheet_id`, plus top-level keys: `_root_folder_id` (the ConstituencyTypology folder), `_planars_config_file_id`, `_all_languages_notebook_file_id`. Each run of `generate-sheets` also creates editable Google Sheets for `planar_*.tsv` and `diagnostics_{lang_id}.tsv` in the language's Drive folder so collaborators can view (and coordinators can edit) the planar structure alongside their annotation sheets. `import-sheets` reads these Sheets back and detects changes.

3. **Analysis** (`planars/`): Each analysis module reads a filled TSV and derives spans. All share the same core logic:
   - **Keystone position**: Identified by `Position_Name == 'v:verbstem'`; anchors all span computations.
   - **Partial positions**: ≥1 element in the position qualifies.
   - **Complete positions**: ALL elements in the position qualify.
   - **Strict span**: Contiguous expansion from keystone (no gaps).
   - **Loose span**: Extends to farthest qualifying position on each side regardless of gaps.

4. **Analysis modules**: Per-module qualification rules, required criteria, and span counts are in `schemas/diagnostic_classes.yaml` (under `qualification_rule`) and summarized in `docs/analyses.md`. Each module in `planars/` exposes `derive_*()` and `format_result()`.

## Design principles (influenced by AUTOTYP)

Late aggregation, autotypology (dynamic schema), definition files vs. data files, and language reports are documented in [docs/data-management.md](docs/data-management.md#design-principles). The key operational implication: never aggregate during data collection; never store derived values (spans, domain types) in annotation TSVs.

**Checkers don't proliferate; commands do.** New validation logic belongs in `integrity-check` (summary) or `check-codebook` (detail) — not in new standalone scripts. New scripts are commands (they transform or generate data) and may validate as a side effect, but are not primarily checkers. When proposing a new validation, route it to an existing tool. When `integrity-check` grows too long, add `--section` flags rather than splitting into more scripts. This principle is enforced by documentation (here and in `docs/coordinator-guide.md`), not by code structure.

## Package structure

`planars/` is the core library:
- `io.py`: `load_filled_tsv()` — shared TSV loader. `load_filled_sheet(ws, required_criteria)` — same but reads from a gspread Worksheet. Both share `_parse_filled_df` and return `(data_df, keystone_pos, pos_to_name, criterion_cols, keystone_df)`. `keystone_df` carries the keystone rows separately so analyses that need blocking checks against the ROOT (stress, aspiration) can include it without adding the keystone to the position expansion set.
- `spans.py`: `strict_span`, `loose_span`, `position_sets_from_element_mask`, `fmt_span` — shared span math and formatting helper.
- `ciscategorial.py`, `subspanrepetition.py`, `noninterruption.py`, `stress.py`, `aspiration.py`, `nonpermutability.py`, `free_occurrence.py`, `biuniqueness.py`, `repair.py`, `segmental.py`, `metrical.py`, `tonal.py`, `tonosegmental.py`, `intonational.py`, `pausing.py`, `proform.py`, `play_language.py`, `idiom.py`: each exposes `derive_*()` (takes an optional `Path` or `_data` kwarg, returns a result dict) and `format_result()` (takes a result dict, returns a formatted string).
- `reports.py`: the data layer for all downstream analysis. `project_spans(source, repo_root, gc, manifest)` and `language_spans(lang_id, source, ...)` — collect spans for all or one language, returning `(DataFrame, lang_meta)`; DataFrame columns: `Language, Test_Labels, Analysis, Left_Edge, Right_Edge, Size`. `language_completeness` / `project_completeness` — per-construction fill stats. `language_status(lang_id, gc, manifest)` — reads Status tab from Sheets (Sheets only). `language_report_data(lang_id, source, ...)` — full bundle: `{lang_id, display_name, generated_at, completeness, status, spans, lang_meta}`. Also owns `_CLASS_HANDLERS` (the analysis registry) and all span label constants. `collect_all_spans` / `collect_all_spans_from_sheets` remain as backward-compat aliases for `project_spans`.
- `html_report.py`: `render_language_report(data)` — takes a `language_report_data()` bundle and returns a self-contained HTML string with annotation completeness table and embedded interactive Plotly domain chart. For Colab display or local browser use. `render_language_report_pdf(data)` — same but returns PDF bytes with a static PNG chart (requires `weasyprint` + `kaleido`); upload to Drive for a natively rendered shareable URL.
- `charts.py`: visualization only. Imports `_CLASS_HANDLERS` and span collection from `reports.py`. `domain_chart(df, keystone_pos, pos_to_name)` — single-language chart (caller filters df by language first). `charts_by_language(df, lang_meta)` — produces one chart per language, returns `dict[lang_id, Figure]`. Span label constants re-exported for backward compat.
- `cli.py` + `__main__.py`: CLI entry point (`python -m planars <analysis> <tsv>`).

`coding/` contains the coordinator tooling:
- `drive.py`: Shared Google Drive/Sheets client helpers used by all coordinator commands — `_get_clients()`, `_load/save_drive_config()`, `_open_spreadsheet()`, `_load/upload_manifest`, folder/permission helpers, and `_with_retry(fn)` for 429 quota backoff. All OAuth2 auth logic lives here.
- `schemas.py`: Cached loaders for schema YAML files — `load_diagnostic_classes()` and `load_diagnostic_criteria()`. Each file is read once per process. `languages.yaml` is intentionally excluded (written to mid-session by `lookup-lang`; callers read it fresh at point of use).
- `make_forms.py`: `build_element_index`, `_read_diagnostics_for_language` — utilities used by other scripts.
- `generate_sheets.py`: `generate-sheets` command. Validates planar and diagnostics before creating sheets. Backs up the Drive manifest to `manifest_backup.json` (gitignored) at the start of each run. Aborts if the manifest is empty for an established language (stale manifest guard). **`--force` aborts with a hard error if any language already has annotation sheet IDs in the manifest** — annotation data is irreplaceable and must never be destroyed by a flag. To add new classes only, omit `--force`. To restructure existing sheets use `restructure-sheets --apply`. Each annotation spreadsheet gets a `Status` tab (last tab) with one row per construction and an `in-progress` / `ready-for-review` dropdown.
- `update_sheets.py`: `update-sheets` — adds missing rows/trailing columns to existing sheets. Also ensures the Status tab exists and is last in each spreadsheet. Retries `get_all_values()` with exponential backoff (up to 5 retries, 15s×attempt) on 429 quota errors.
- `sync_params.py`: `sync-params` — syncs criterion columns when `diagnostics_{lang_id}.tsv` changes; supports rename, split, merge, and remove lifecycle operations.
- `restructure_sheets.py`: `restructure-sheets` — archives and regenerates sheets after structural changes; carries over annotations using `--rename-map` (position renames), `--rename-element` (element label renames), and `--rename-class` (analysis class renames: archives old sheet, creates new sheet under new name, renames local TSV directory in-place, updates manifest); only processes classes with actual changes. `--rename-class` requires diagnostics_{lang_id}.tsv to already use the new name (enforced by pre-flight check); pair with `prune-manifest` if retiring (not renaming) a class.
- `import_sheets.py`: `import-sheets` — downloads filled annotation sheets to TSVs; also downloads planar/diagnostics Sheets, detects changes, auto-applies safe downstream commands, and writes destructive changes to `pending_changes.json`; highlights invalid cells pink in the Sheet as a side effect. Aborts if `coded_data/` has uncommitted TSV changes. Skips existing TSVs by default; `--overwrite-existing` re-downloads them (auto-archives to `archive/` first). When destructive changes are written, opens or updates a GitHub issue labeled `pending-changes` (requires `gh` CLI). Skips constructions whose Status tab entry is not `ready-for-review` unless `--ignore-status` is passed.
- `apply_pending.py`: `apply-pending` — interactive review and application of pending destructive changes written by `import-sheets`. Closes the `pending-changes` GitHub issue when all entries are cleared.
- `prune_manifest.py`: `prune-manifest` — removes retired analysis class entries from the Drive manifest and archives their local TSVs. Run after removing a class from `diagnostics_{lang_id}.tsv`. Dry-run by default; `--apply` to execute, `--all` to skip per-class prompts. Writes a timestamped manifest snapshot to `manifest_archives/` (gitignored) before any mutation.
- `validate.py`: Shared base — just the `ValidationIssue` dataclass.
- `validate_planar.py`: `validate_planar_df(df)` — validates planar structure TSVs (sequential positions, unique names, keystone present, valid Position_Type/Class_Type, element conventions including collapse detection).
- `validate_diagnostics.py`: `validate_diagnostics_df(df, lang_id)` — validates diagnostics_{lang_id}.tsv (required columns, Language field, brace syntax, criterion names against diagnostic_criteria.yaml, class names against planars/ modules, construction naming rules).
- `validate_coding.py`: `validate-coding` command — reads annotation sheets, validates values, clears/updates pink cell highlights. Also calls `validate_planar_df` and `validate_diagnostics_df` before sheet validation. Exits with code 1 if any issues are found (used by the scheduled sheet-validation GitHub Actions workflow).
- `generate_notebooks.py`: `generate-notebooks` — generates per-language contributor, validation, and report notebooks, plus the coordinator notebook. Report notebooks (`report_{lang_id}.ipynb`) are lightweight Colab notebooks that generate and upload `report_{lang_id}.html` to Drive. Stores `report_notebook_file_id` in `drive_config.json`.
- `generate_reports.py`: `generate-reports` — generates and uploads `report_{lang_id}.pdf` directly (no Colab needed; used by the nightly GitHub Action). Uses `source="local"` from checked-out TSVs. Stores `report_file_id` in `drive_config.json` (migrates legacy `report_html_file_id` on first run).
- `check_codebook.py`: `check-codebook` — consistency check between diagnostic_criteria.yaml, diagnostic_classes.yaml, analysis modules, and diagnostics_{lang_id}.tsv.
- `integrity_check.py`: `integrity-check` — full project-wide health report across six sections (PLANAR STRUCTURE, DIAGNOSTICS, CODEBOOK CONSISTENCY, ANALYSIS CONSISTENCY, ANNOTATION SHEETS, NEEDS REVIEW). Use `--lang` to restrict per-language sections; `--sheets` to include live Google Sheets structural validation.
- `glottolog.py`: `lookup-lang` — fetch and cache Glottolog metadata for a language ID. Writes to both `glottolog_cache.json` (gitignored, local) and `schemas/languages.yaml` (source of truth, committed). Always refreshes Glottolog fields; scaffolds empty `meta` block in `languages.yaml` only if absent. Also provides `is_valid_format()` and `cached_entry()` used by `validate_diagnostics.py` for check 6 (Glottocode format + advisory).
- `populate_sheets.py`: One-time utility for uploading legacy TSV data.
- `setup_root_folder.py`: One-time Drive folder setup (run once after first `generate-sheets`).

`coded_data/{lang_id}/{class_name}/` contains the filled TSVs imported from Google Sheets (local dev use only — Colab reads directly from Sheets). Archive TSVs live in `coded_data/{lang_id}/{class_name}/archive/`.

`generate_snapshots.py` at the repo root regenerates snapshot baselines; `pytest` (via `tests/test_snapshots.py`) runs the snapshot regression tests alongside all other tests. Snapshots live in `tests/snapshots/`. Auto-discovers all planars modules with `derive` + `format_result`. `check_snapshots.py` remains as a quick CLI alternative for snapshot-only checks.

`coded_data/synth0001/` is a synthetic second-language dataset for multi-language testing (not real data). It has a genuinely different planar structure (28 positions, keystone at 23) derived from `stan1293` by dropping 9 positions and flipping ~25% of criterion values. `tests/make_synthetic_lang.py` generates it (`--apply` to write, `--clean --apply` to remove).

## diagnostics_{lang_id}.tsv format

Criteria default to `y/n` dropdowns. To specify custom values use brace syntax:

```
accented{y/n/both}, independence, left-interaction, right-interaction
```

`coding/make_forms.py` parses this into `(criterion_names, criterion_values)`. `python -m coding generate-sheets` applies per-column dropdown validation and appends a free-text `Comments` column to every tab. `python -m coding import-sheets` validates each criterion against its allowed set (always also accepts `na` and `?`) and passes Comments through unchanged.

`python -m coding update-sheets` brings existing sheets up to date when new elements are added to the planar structure. Always dry-run first.

`diagnostics_{lang_id}.tsv` is also the source of truth for notebook generation. `python -m coding generate-notebooks` reads each language's `diagnostics_{lang_id}.tsv` to discover analysis classes and generates three kinds of notebooks: a per-language contributor notebook (`domains_{lang_id}.ipynb`), per-language validation notebooks (`validation_{lang_id}.ipynb`), and a single coordinator notebook (`all_languages.ipynb`) covering all languages. Per-class cells in the coordinator notebook are generated automatically from the class list — adding a new class to `diagnostics_{lang_id}.tsv` and updating `_CLASS_DISPLAY_NAMES` in `coding/generate_notebooks.py`, then running `generate-notebooks --apply`, is all that's needed to include it. Notebook generation is triggered automatically at the end of `generate-sheets`, `sync-params --apply`, and `restructure-sheets --apply`. Templates live in `notebooks/templates/`; the generated notebooks are artifacts uploaded to Drive, not source files. Each analysis module must define a `derive` alias pointing to its primary derive function so the generation script can call it without a per-module name mapping (see e.g. `planars/ciscategorial.py`).

## Glottolog metadata convention

Language IDs in this project are Glottocodes (e.g., `arao1248`, `stan1293`). Glottolog metadata (human-readable name, ISO 639-3 code, language family, coordinates) is fetched once via `python -m coding lookup-lang <glottocode>` and cached locally in `glottolog_cache.json` (gitignored).

**Convention:** wherever a language ID appears in user-facing output — notebook headers, chart titles, report tables, Drive folder names, terminal output — prefer the `Name [glottocode]` format (e.g., `Araona [arao1248]`) over the bare Glottocode. The canonical helper for this is `planars.languages.get_display_name(glottocode)`.

Metadata is also written into `manifest.json` on Drive (by `generate-sheets` and `import-sheets`) so the data lives near the annotation sheets. `schemas/languages.yaml` is the source of truth; the Drive manifest carries a synced copy. `lookup-lang` scaffolds the `meta` block for new languages; `integrity-check --sheets` warns when `source` or `author` are blank in `languages.yaml`.

Use Glottolog metadata proactively for:
- Display names in notebooks, chart legends, and terminal output
- Family/macroarea grouping in future coverage tables and maps (issue #62)
- Language onboarding validation (`lookup-lang` before `generate-sheets`)

## schemas/ package

`schemas/` is a Python package (it has `__init__.py`) so that its YAML files are delivered to Colab when planars is installed via `pip install`. Files are readable via `importlib.resources`. `pyproject.toml` includes `schemas*` in `packages.find` and lists `schemas = ["*.yaml"]` in `package-data`. Documentation for each file lives in `schemas/__init__.py`.

`schemas/languages.yaml` is the source of truth for per-language metadata. Glottolog fields (`name`, `iso639_3`, `family`, coordinates) are written/refreshed by `python -m coding lookup-lang <glottocode>`. Project metadata (`language`, `glottocode`, `source`, `author`, `annotator`, `annotation_status`, `notes`) is hand-edited by coordinators. Valid `annotation_status` values: `planned | in-progress | complete`. The Drive manifest carries a copy written by `generate-sheets`; always edit `languages.yaml`, not the manifest. `planars/languages.py` provides `get_display_name(glottocode)` → `"Name [glottocode]"` for use in notebooks and charts. Note: `lookup-lang` rewrites `languages.yaml` using PyYAML, which strips YAML comments — documentation lives in `schemas/__init__.py` for this reason.

## Codebook and diagnostic classes

`schemas/diagnostic_criteria.yaml` is the source of truth for diagnostic criterion definitions, valid values, and linguistic descriptions. Entries marked `[PLACEHOLDER]` need linguistic descriptions; entries marked `[NEEDS REVIEW]` have provisional rules that need confirmation (currently aspiration; stress qualification rule is settled but `left-interaction` and `right-interaction` criteria remain under review).

`schemas/terms.yaml` is the source of truth for analytical terms (keystone, partial, complete, strict, loose) and chart label glossary.

`schemas/planar.yaml` is the source of truth for structural column definitions and element conventions.

`schemas/diagnostic_classes.yaml` is the normative schema for analysis classes — what they cover, when they apply, what diagnostic criteria they require, and how spans are computed (qualification_rule). It is separate from `schemas/diagnostic_criteria.yaml` (which owns criterion semantics) and serves as the source of truth for:
- Which classes exist and their domain types (morphosyntactic / phonological / indeterminate)
- Whether a class is universal or conditional and when it applies
- Whether a class uses a single general construction or is construction-specific
- Which diagnostic criteria must appear in diagnostics_{lang_id}.tsv for each class
- Whether a class is required for all languages (`collection_required: true/false`) — values are `[NEEDS COORDINATOR INPUT]` until Adam decides
- Non-exhaustive examples of known construction types for variable classes

`check-codebook` validates diagnostics_{lang_id}.tsv against both files. Human-editable workflow: edit `schemas/diagnostic_classes.yaml` to add or update a class, then ask Claude to propagate changes to diagnostics_{lang_id}.tsv and scaffold the module.

`render_codebook.py` at the repo root renders the schemas as human-readable Markdown (reads from all four schema files): `python render_codebook.py` (stdout) or `python render_codebook.py codebook.md` (file).

`generate_diagram.py` at the repo root generates a Graphviz diagram of the analysis class taxonomy: classes grouped by domain type with diagnostic criteria listed inside each node, and language instances connected on the right with construction names on edges for construction-specific classes. Output: `python generate_diagram.py out.svg` (or `.pdf`, `.dot`, `.png`). Requires `dot` (Graphviz) to be installed.

`Makefile` at the repo root provides short `make` aliases for all coordinator commands. Run `make help` for the full list. The venv must be activated before using `make`.

## NonCollaborative/

Personal working area not part of the shared analysis pipeline:

- `make_file.R` — R equivalent of `make_forms.py`
- `domains/` — domain TSV files for various languages (Chac, Mart, Nyan, Quech, Yupik, etc.)
- `domainGenerationTests/` — earlier prototypes of the analysis scripts
- `planar_tables/` — CSV/TSV versions of the planar structure for stan1293
- `scripts/` — active R and Python scripts for visualization and analysis (constituency forests, domain charts, tree traversal, etc.)
- `OlderFiles/` — archive of older scripts and data, including prior versions of planar_tables and scripts

## Documentation maintenance

Keep the following files up to date as the project evolves. Check each one at the end of any session where relevant changes were made.

| File | Update when |
|------|-------------|
| `CLAUDE.md` | Architecture changes, new scripts, new conventions, workflow changes |
| `schemas/languages.yaml` | New language onboarded, or coordinator edits `source`/`author`/`annotation_status` fields |
| `schemas/diagnostic_criteria.yaml` | New diagnostic criteria, new analyses, `[PLACEHOLDER]` or `[NEEDS REVIEW]` entries resolved |
| `schemas/diagnostic_classes.yaml` | New analysis classes added, applicability, required criteria, qualification rules, or known construction types change |
| `schemas/planar.yaml` | New standard element labels or structural column conventions |
| `schemas/terms.yaml` | New analytical terms or chart label changes |
| `README.md` | Changes to the annotated TOC (audience routing, guide descriptions) |
| `docs/*.md` | User-facing workflow changes, setup instructions, new dependencies, new commands |
| `notebooks/templates/domains_boilerplate.ipynb` | Contributor notebook boilerplate changes (setup, auth, chart cell) — then run `generate-notebooks --apply` |
| `notebooks/templates/all_languages_boilerplate.ipynb` | Coordinator notebook boilerplate changes (setup, auth, helper, chart) — then run `generate-notebooks --apply` |
| `notebooks/templates/validation_boilerplate.ipynb` | Validation notebook boilerplate changes — then run `generate-notebooks --apply` |
| `notebooks/templates/report_boilerplate.ipynb` | Report notebook boilerplate changes — then run `generate-notebooks --apply` |
| `pyproject.toml` version | Any change to `planars/` library code (Colab installs from GitHub, not PyPI) |

When in doubt, update. These files are the primary onboarding resource for collaborators and future contributors.

## Commit conventions

Commit frequently — after each logical unit of work rather than accumulating changes across a full session. Good commit points:
- A new script or command is working
- A bug is fixed
- Documentation is updated to reflect completed changes
- A self-contained refactor is done

Separate `coded_data/` annotation changes from tooling/library changes into distinct commits — they have different authors (human annotators vs. code changes) and different review needs.

## In-progress annotation work

### Araona (arao1248) — partially annotated

Language files are in `coded_data/arao1248/`. Source: Adam Tallman, "Graded constituency in the Araona (Takana) verb complex," chapter 13 in *Constituency and convergence in the Americas* (langsci/291). Glottolog ID: arao1248.

**Completed:**
- `planar_input/planar_arao1248-20260319.tsv` — 18-position verbal planar structure (XP1 zone through rightXP zone)
- `planar_input/diagnostics_{lang_id}.tsv` — ciscategorial, noninterruption, subspanrepetition (2 constructions)
- `ciscategorial/general.tsv` — V/N/A-combines annotated; runs and produces spans
- `noninterruption/general.tsv` — free/multiple annotated; runs and produces spans
- `subspanrepetition/auxiliary_construction.tsv` — maximal vpref–aspect (4–15), minimal vcore (6); no narrowscope elements
- `subspanrepetition/tso_clause_linkage.tsv` — maximal XP1–connector (1–17), minimal vpref–tamesuf (4–14); rightXP excluded from tso-clauses

All four analyses run and produce spans. Source: Adam Tallman §4.5 (langsci/291, ch. 13). Source .tex at `/tmp/araona.tex` (may need re-downloading from langsci/291 GitHub if gone).

### Chichewa (nyan1308) — planned

Source: Jeff Good, "Domains of linearization, constituency, and wordhood in Chichewa" (draft ms.). Glottolog ID: nyan1308. Not yet set up in planars — requires `tonosegmental` and `intonational` modules (issues #70, #71) before onboarding. See issue #72.

## Issue tracking

Feature requests and bugs are tracked on GitHub Issues: https://github.com/jcgood/planars/issues

When creating a new issue, apply at least one label from the set below. Use `gh issue create --label "..."` or apply labels immediately after creation with `gh issue edit <n> --add-label "..."`.

### Labels

| Label | Meaning |
|-------|---------|
| `diagnostics` | Module design, diagnostic criteria, or qualification rules requiring linguistic validation — input from Adam needed before implementation. Filter: `gh issue list --label diagnostics` |
| `sheet-validation` | Filed automatically by the `sheet-validation.yml` workflow when `validate-coding` detects invalid cell values. Auto-closed when clean. |
| `sheet-drift` | Filed automatically by the `data-refresh.yml` workflow when `update-sheets` (dry-run) detects sheets out of sync with the data model. Resolve by running `update-sheets --apply`. Auto-closed when clean. |
| `pending-changes` | Filed automatically by `import-sheets` when destructive changes are written to `pending_changes.json`. Resolve by running `apply-pending`. |

### Notable open issues

Run `gh issue list` for the full list. Key active issues:

- **#88** — Archive planars data as versioned CLDF release on Zenodo (depends on #84).
- **#87** — Add cross-language annotator assignment and status tracking (Drive sheet or yaml in planars-data).
- **#84** — Add `export-cldf` command to produce a CLDF StructureDataset from planars annotation data.
- **#81** — Add collaborator notes alongside annotation sheets: per-language Google Doc with tabs per class/construction; download notes in `import-sheets` to surface uncertain codings and propose refinements.
- **#80** — Auto-generate schema structure diagrams from YAML schema files. Initial implementation in `generate_diagram.py` (class taxonomy with criteria + language instances); layout refinement still needed.
- **#72** — Prepare Chichewa (nyan1308) for onboarding. `[Jeff]`
- **#70** — New analysis module: tonosegmental domain. Stub created; qualification rule and status need Adam's sign-off. `[diagnostics]`
- **#109** — Multi-coordinator manifest coordination: `drive_config.json` not shared via git and no conflict detection on concurrent manifest mutations. `[Jeff]`
- **#107** — Allow explicit NA value for inapplicable diagnostic criteria (e.g. English stress); needs Adam's input on which criteria and computational treatment. `[diagnostics]` `[needs-input]`
- **#104** — Keystone coding for phonological blocked-span tests: verbstem row should have real accented/obligatory/independence values, not `na`. Needs documentation, sheet fix, and Adam's input on correct values. `[diagnostics]`
- **#112** — Restructure coordinator guide: workflow-oriented sections, automatic vs. manual actions, and tool-roles table (enforces "checkers don't proliferate" principle).
- **#113** — `sync-diagnostics-yaml`: per-language YAML as coordinator-facing diagnostics source of truth; round-trips with TSV. Split out from #110. `[enhancement]`
- **#101** — Tonal alternations from hybrid morphemes: does this need a new phonological category distinct from `tonal` and `tonosegmental`? Needs Adam's input. `[diagnostics]`
- **#99** — `free_occurrence` redesign: needs `depends-on` criterion (position reference for non-free elements), min-max fracture spans, and conditional validation pattern. Qualification rule and span labels need Adam's input before implementation. `[diagnostics]`
- **#9** — Fill in `[PLACEHOLDER]` and `[NEEDS REVIEW]` entries in schema files. Requires input from Adam. `[needs-input]`

## Work phases

This is a **research project**: the schemas, qualification rules, and analytical models are themselves outputs of the research process, not fixed inputs. Annotation work informs theory, which changes the schema files (`schemas/`), which changes what gets annotated. This makes it fundamentally unlike a business application with stable requirements — the tools serve a moving target by design. As understanding deepens across languages, all facets of the project (data model, diagnostics, module logic, documentation) are subject to revision.

Sessions tend to fall into a few natural patterns. Naming the primary focus at the start of a session helps keep scope manageable.

**Schema work** — Editing any file in `schemas/` or the qualification rules in analysis modules. The most consequential work; mistakes here cascade across languages and analyses. Go slow, run `integrity-check` after changes. Qualification rule changes must also propagate to inline comments and module docstrings — not just the YAML files.

Snapshot lifecycle: the pre-commit hook (`regenerate_snapshots_hook.py`) regenerates affected snapshots automatically when any `planars/*.py` file is staged — qualification rule changes are covered here. The daily `data-refresh.yml` GitHub Action imports fresh annotations from Google Sheets and regenerates snapshots — data changes are covered there. A snapshot diff in a commit is the expected record of how a change altered span output. A snapshot failure on a PR means a code change altered output without going through the hook.

Retiring a class: when a class is removed from `diagnostics_{lang_id}.tsv`, run `python -m coding prune-manifest --apply` afterward. This archives the retired class's local TSVs (rather than deleting them) and removes the stale entry from the Drive manifest. Skipping this step causes `import-sheets` and `data-refresh` to keep re-importing the old sheet indefinitely.

Renaming a class: update `diagnostics_{lang_id}.tsv` to use the new name first, then run `python -m coding restructure-sheets --rename-class OLD:NEW --apply`. This archives the old sheet, creates a new sheet under the new name with all annotations carried over, renames the local TSV directory in-place (preserving git history), and updates the Drive manifest. Do NOT use `prune-manifest` for a rename — it would discard annotation data.

**Language onboarding** — End-to-end work for a new language: gathering source material, drafting `diagnostics_{lang_id}.tsv`, running `generate-sheets`, producing a first-pass annotation, importing, and verifying analysis output. During prototyping, this has involved reading finished book chapters; in production, onboarding will be a collaborative process with contributors who may provide information in varied and yet-to-be-modeled forms (notes, drafts, conversation, partial data). The tooling should remain open to this rather than assuming a finished written source is always available. Automated first-pass coding may eventually be possible, but will always require expert review.

**Contributor tooling** — Building or improving the `coding/` scripts, sheet generation, import/validation pipelines, and notebook generation. Standard software work, but changes to sheet structure need `update-sheets` or `restructure-sheets` to propagate.

**Audit** — Checking consistency between code, documentation, codebook, and annotation data. Includes `integrity-check` (and `check-codebook` for lower-level detail), snapshot tests, and reviewing CLAUDE.md/docs for drift. Also includes verifying that inline comments and module docstrings match current behavior — code evolves faster than comments. A good way to start a session after a gap.

**Refactoring** — Structural cleanup with no behavior changes. Targets: duplicated logic, oversized modules, inconsistent patterns. Run a refactoring pass after any major feature addition or every few sessions. Track known targets in a dedicated issue (issue #98 is now closed — `coding/drive.py` extraction, retry consolidation, and schema loading centralization are all complete). Open a new issue when the next round of targets is identified.

## Analysis status convention

The `status` field in `diagnostic_classes.yaml` uses three values: `stable`, `[AUTO-DERIVED]`, and `[NEEDS REVIEW]`. **Only a coordinator (Adam Tallman or equivalent domain expert) may promote a module's status out of `[AUTO-DERIVED]`.** Claude should not change `[AUTO-DERIVED]` to `stable` or remove that designation, even when cross-language evidence is strong. Claude may:

- Add "likely stable" notes or cross-language evidence summaries within the status comment
- Change `[AUTO-DERIVED]` to `[NEEDS REVIEW]` if a specific known concern warrants it
- Downgrade `stable` to `[NEEDS REVIEW]` if a bug or data problem is discovered

## Key conventions

- File naming: imported TSVs use `{construction}.tsv` under `coded_data/{lang_id}/{class_name}/`. The lang and class are encoded in the path, not the filename.
- Language ID is inferred from the planar filename: `planar_stan1293-20260209.tsv` → `stan1293`.
- Elements with leading/trailing hyphens are wrapped in `[brackets]` to avoid Excel parsing issues.
- Analysis functions take a `Path` object; path resolution happens at the call site (CLI or wrapper scripts), not inside the library.
- Keystone rows have `Position_Name == 'v:verbstem'`. In filled TSVs they carry actual criterion values (not `NA`) so they can participate in blocking condition checks (stress, aspiration). They are excluded from span expansion — `data_df` never contains the keystone; it is returned separately as `keystone_df`.
- Result dicts use `complete_positions` / `partial_positions` and `*_span` key suffixes consistently across all modules.
- `_TRAILING_COLS = ["Source", "Comments"]` is defined in `coding/generate_sheets.py` (source of truth for sheet creation) and `coding/validate_coding.py` (for validation). `coding/sync_params.py` and `coding/restructure_sheets.py` import it from `generate_sheets.py`. `coding/integrity_check.py` has its own independent copy (`_TRAILING = {"Source", "Comments"}` inside `_section_sheets`). Add new trailing columns in all three places to propagate them to new and existing sheets. `update-sheets --apply` rolls out missing trailing columns to existing sheets.
- `coding/populate_sheets.py` is a one-time utility for uploading legacy TSV data. Unnamed trailing columns in legacy TSVs are concatenated with ` | ` into Comments.
