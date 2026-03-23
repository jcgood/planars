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

```bash
# Generate Google Sheets annotation forms (opens browser for OAuth on first run)
# On re-runs, only creates sheets for classes not yet in the Drive manifest
python -m coding generate-sheets
python -m coding generate-sheets --force  # regenerate all from scratch

# Sync criterion columns when diagnostics_{lang_id}.tsv changes (dry run by default)
python -m coding sync-params                                 # dry run
python -m coding sync-params --apply                         # insert new criterion columns, update validation
python -m coding sync-params --apply --rename old:new        # rename a column in all classes
python -m coding sync-params --apply --rename class:old:new  # rename only in one analysis class

# Update existing sheets: add missing rows/trailing columns (dry run by default)
python -m coding update-sheets
python -m coding update-sheets --apply   # apply changes

# Restructure sheets after planar structure changes (archive old, regenerate with carry-over)
python -m coding restructure-sheets
python -m coding restructure-sheets --apply   # archive old sheets and regenerate
python -m coding restructure-sheets --rename-map "old_pos:new_pos" --apply   # carry over renamed positions
python -m coding restructure-sheets --rename-element Ad-VP:AD-VP --apply     # carry over renamed elements
# Only classes with actual changes (new rows, drops, or renames) are archived and regenerated.

# Import filled sheets back to TSVs (skips existing files by default)
python -m coding import-sheets
python -m coding import-sheets --force   # overwrite existing files

# Re-validate annotation sheets and update pink cell highlighting (for collaborators fixing errors)
python -m coding validate-coding                   # all languages
python -m coding validate-coding --lang arao1248   # one language

# Full project-wide integrity check (planar structure, diagnostics, schemas, modules)
python -m coding integrity-check                       # all languages, local checks
python -m coding integrity-check --lang arao1248       # one language
python -m coding integrity-check --sheets              # also check live sheet structure

# Check consistency between diagnostic_criteria.yaml, analysis modules, and diagnostics_{lang_id}.tsv
python -m coding check-codebook

# Look up Glottolog metadata for a language ID (fetches from API on first use, then caches)
# Cache lives at glottolog_cache.json (gitignored). Used by validate_diagnostics for format check.
python -m coding lookup-lang arao1248            # fetch + display + cache
python -m coding lookup-lang --refresh arao1248  # force re-fetch
python -m coding lookup-lang --all               # list all cached languages

# One-time Drive setup: create ConstituencyTypology root folder and move global files
# Run once after generate-sheets; idempotent (safe to re-run)
python -m coding setup-root-folder

# Run a single analysis via the CLI (from repo root)
python -m planars ciscategorial coded_data/stan1293/ciscategorial/general.tsv
python -m planars subspanrepetition coded_data/stan1293/subspanrepetition/andCoordination.tsv
python -m planars noninterruption coded_data/stan1293/noninterruption/general.tsv
python -m planars stress coded_data/stan1293/stress/general.tsv

# Regression testing
pytest                         # run all tests (io, restructure, snapshots)
python generate_snapshots.py   # regenerate snapshot baselines after intentional output changes
                               # review with: git diff tests/snapshots/
python check_snapshots.py      # quick CLI alternative to pytest for snapshot-only checks
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

2. **Manual annotation**: Specialists fill in values via Google Sheets forms generated by `python -m coding generate-sheets`. Google Sheets is the definitive copy of annotation forms. The Sheets workflow creates one file per analysis class with one tab per construction, y/n dropdown validation, and a shared Drive folder. OAuth credentials must be at `~/.config/planars/oauth_credentials.json` (set `PLANARS_OAUTH_CREDENTIALS` to override). The token is cached after first authorization. The manifest is stored on Drive as a single merged `planars_config.json` containing all languages' sheet metadata and folder IDs; `drive_config.json` (gitignored) bootstraps the Drive lookup by holding `_root_folder_id`, `_planars_config_file_id`, and per-language `folder_id` and `domains_notebook_file_id`. `python -m coding import-sheets` loads the manifest from Drive, downloads each tab, validates values (warning on blanks or unexpected entries), and writes `{construction}_filled.tsv` to `coded_data/{lang_id}/{class_name}/`. Existing files are skipped unless `--force` is passed. If any warnings are generated, they are written to `import_errors/{lang}_{timestamp}.txt` (gitignored) in addition to stdout. When `diagnostics_{lang_id}.tsv` criterion columns change, use `python -m coding sync-params --apply` to add new columns to existing sheets while preserving annotations.

   **Drive folder structure**: `python -m coding setup-root-folder` (run once after the first `generate-sheets`) creates a top-level `ConstituencyTypology` Drive folder and moves `planars_config.json` and `all_languages.ipynb` there. New language folders created afterwards are placed inside this root folder. `drive_config.json` tracks per-language `folder_id` and `domains_notebook_file_id`, plus top-level keys: `_root_folder_id` (the ConstituencyTypology folder), `_planars_config_file_id`, `_all_languages_notebook_file_id`. Each run of `generate-sheets` also uploads `planar_*.tsv` and `diagnostics_{lang_id}.tsv` to the language's Drive folder (updating existing files in place) so collaborators can view the planar structure alongside their annotation sheets.

3. **Analysis** (`planars/`): Each analysis module reads a filled TSV and derives spans. All share the same core logic:
   - **Keystone position**: Identified by `Position_Name == 'v:verbstem'`; anchors all span computations.
   - **Partial positions**: ≥1 element in the position qualifies.
   - **Complete positions**: ALL elements in the position qualify.
   - **Strict span**: Contiguous expansion from keystone (no gaps).
   - **Loose span**: Extends to farthest qualifying position on each side regardless of gaps.

4. **Analysis modules in detail**:
   - `ciscategorial.py`: A position qualifies if elements have `V-combines=y` and all other criteria `=n`. Returns 4 spans (strict/loose × complete/partial).
   - `subspanrepetition.py`: 5 span categories (fillable, widescope_left/right, narrowscope_left/right), each with 4 spans = 20 total.
   - `noninterruption.py`: Two domain types (no-free: `free=n`; single-free: `free=n` or `free=y,multiple=n`), each with complete/partial = 4 strict spans.
   - `stress.py`: Uses `blocked_span` with complete/partial distinction — expand from keystone outward, stopping just before the first position where the blocking condition holds. Two domain types, each with complete/partial = 4 spans total. Partial blocking: any element in the position satisfies the condition (smaller domain). Complete blocking: all elements satisfy the condition (larger domain). Minimal: blocked by `stressed ∈ {y, both} AND independence=y`. Maximal: blocked by `obligatory=y AND independence=y`. The keystone always remains in the domain. See `schemas/diagnostic_criteria.yaml` and `schemas/diagnostic_classes.yaml` for open questions on `left-interaction`, `right-interaction`, and meso/interaction domains (issues #16, #17).
   - `aspiration.py`: `[NEEDS REVIEW]` — mirrors stress structure but qualification rules are provisional. See `schemas/diagnostic_classes.yaml`.
   - `nonpermutability.py`: Two domain types (strict, flexible) based on whether elements' linear ordering is fixed. Criteria: `permutable` (y/n), `scopal` (y/n). Strict = absolutely fixed order (permutable=n). Flexible = fixed OR variable-with-scope (permutable=n OR (permutable=y AND scopal=y)). Each with complete/partial = 4 strict spans. Based on Tallman et al. 2024 intro §Fracturing.
   - `free_occurrence.py`: The free occurrence domain — positions where elements are free forms (free=y). Reuses the `free` criterion from noninterruption. If a language runs both analyses, a single sheet with `free` and `multiple` columns covers both. Returns 4 spans (strict/loose × complete/partial). Classified as an indeterminate domain (Tallman et al. 2024).
   - `biuniqueness.py`: The biuniqueness (extended exponence) domain — span covered by a discontinuous morpheme (circumfix) or extended exponent. Criterion: `biunique` (y/n) where n = element is a piece of the circumfix. One TSV per circumfix/construction. The loose partial span is the primary result (extends from prefix piece to suffix piece). Returns 4 spans (strict/loose × complete/partial). Based on Araona §Extended exponence.
   - `repair.py`: The repair domain — positions where a production error triggers restart from the domain's left edge. Criterion: `restart` (y/n). Returns 4 spans. Based on Cup'ik §Repair domain.
   - `segmental.py`: A segmental phonological domain — span within which a segmental phonological process applies (vowel deletion, consonant coalescence, etc.). Criterion: `applies` (y/n). One TSV per process. Returns 4 spans. Examples: Araona vowel syncope domain, Cup'ik uvular-velar coalescence domain.
   - `suprasegmental.py`: A suprasegmental (prosodic) phonological domain — span governed by a pitch, stress, or tone assignment rule. Criterion: `applies` (y/n). One TSV per rule. Returns 4 spans. Distinct from stress.py/aspiration.py (which use blocked_span logic for boundary-defined domains). Examples: Araona LH* pitch-accent domain, Cup'ik iambic foot domain.
   - `pausing.py`: The pausing domain — span where elements cannot be separated by a prosodic pause. Criterion: `pause_domain` (y/n). Returns 4 spans.
   - `proform.py`: The proform substitution domain — span that can be replaced by a proform (pronoun, pro-verb, etc.). Criterion: `substitutable` (y/n). Returns 4 spans.
   - `play_language.py`: The play language (ludling) domain — span targeted by play language operations (infixation, reversal, etc.). Criterion: `applies` (y/n). Returns 4 spans. Attested in Zenzontepec Chatino.
   - `idiom.py`: The idiom domain — span forming a non-compositional idiomatic unit. Criterion: `idiomatic` (y/n). Returns 4 spans.

## Design principles (influenced by AUTOTYP)

The planars data model was developed independently but shares several fundamental design principles with AUTOTYP. These are articulated in Witzlack-Makarevich, Nichols, Hildebrandt, Zakharko & Bickel, "Managing AUTOTYP Data: Design Principles and Implementation," ch. 56 in *The Open Handbook of Linguistic Data Management* (MIT Press, doi:10.7551/mitpress/12200.001.0001). Understanding these principles explains architectural decisions that might otherwise seem arbitrary.

**Late aggregation**: Raw annotation data is stored exhaustively at the lowest level (y/n per element per position). All derived categories — spans, domain types, partial vs. complete distinctions — are computed algorithmically outside the stored data (in the analysis modules). This means the same annotation files can answer different research questions as the theoretical framework evolves, without recoding. Never aggregate during data collection.

**Autotypology (dynamic schema)**: The diagnostic criterion definitions in `schemas/diagnostic_criteria.yaml` and analysis classes in `schemas/diagnostic_classes.yaml` are not a fixed a priori etic grid. They are updated throughout data collection as new languages reveal new phenomena; initial codings are often revised as the typology stabilizes (AUTOTYP observes this typically takes ~40–50 entries before new types stop emerging). The `[PLACEHOLDER]` and `[NEEDS REVIEW]` markers in these files reflect genuine ongoing theoretical work, not incomplete implementation. This is by design.

**Definition files vs. data files**: `schemas/diagnostic_criteria.yaml`, `schemas/diagnostic_classes.yaml`, `schemas/planar.yaml`, and `schemas/terms.yaml` are *definition files* — they list possible criterion values with linguistic definitions and coding procedure descriptions, and are updated dynamically throughout data collection. Filled TSVs under `coded_data/` are *data files* — actual annotations for individual languages. Definition files serve qualitative typological work (what distinctions are cross-linguistically viable?); data files enable quantitative analysis. Keep them clearly separate.

**Language reports**: AUTOTYP uses free-text language reports as intermediate documents during module development — text documents containing paradigms, citation examples, and explicit motivation for coding decisions. These are especially valuable when new values are being identified and coding decisions are being revised, and serve as an audit trail connecting annotations to their empirical basis. Planars currently relies on source chapters in this role during prototyping; a structured language report format for production onboarding is an open question (see issue #68).

## Package structure

`planars/` is the core library:
- `io.py`: `load_filled_tsv()` — shared TSV loader. `load_filled_sheet(ws, required_criteria)` — same but reads from a gspread Worksheet. Both share `_parse_filled_df` and return `(data_df, keystone_pos, pos_to_name, criterion_cols, keystone_df)`. `keystone_df` carries the keystone rows separately so analyses that need blocking checks against the ROOT (stress, aspiration) can include it without adding the keystone to the position expansion set.
- `spans.py`: `strict_span`, `loose_span`, `position_sets_from_element_mask`, `fmt_span` — shared span math and formatting helper.
- `ciscategorial.py`, `subspanrepetition.py`, `noninterruption.py`, `stress.py`, `aspiration.py`, `nonpermutability.py`, `free_occurrence.py`, `biuniqueness.py`, `repair.py`, `segmental.py`, `suprasegmental.py`, `pausing.py`, `proform.py`, `play_language.py`, `idiom.py`: each exposes `derive_*()` (takes an optional `Path` or `_data` kwarg, returns a result dict) and `format_result()` (takes a result dict, returns a formatted string).
- `charts.py`: `collect_all_spans(repo_root)` — runs all analyses over all filled TSVs in `coded_data/`, returns `(df, lang_meta)`. `collect_all_spans_from_sheets(gc, manifest)` — same but reads from Google Sheets. Both return a DataFrame with a `Language` column and a `lang_meta` dict `{lang_id: {"keystone_pos": int, "pos_to_name": dict}}` — each language has its own independent planar structure. `domain_chart(df, keystone_pos, pos_to_name)` — single-language chart (caller filters df by language first). `charts_by_language(df, lang_meta)` — produces one chart per language, returns `dict[lang_id, Figure]`.
- `cli.py` + `__main__.py`: CLI entry point (`python -m planars <analysis> <tsv>`).

`coding/` contains the coordinator tooling:
- `make_forms.py`: `build_element_index`, `_read_diagnostics_for_language` — utilities used by other scripts.
- `generate_sheets.py`: `generate-sheets` command. Validates planar and diagnostics before creating sheets.
- `update_sheets.py`: `update-sheets` — adds missing rows/trailing columns to existing sheets.
- `sync_params.py`: `sync-params` — syncs criterion columns when `diagnostics_{lang_id}.tsv` changes.
- `restructure_sheets.py`: `restructure-sheets` — archives and regenerates sheets after structural changes; carries over annotations using `--rename-map` (position renames) and `--rename-element` (element label renames); only processes classes with actual changes.
- `import_sheets.py`: `import-sheets` — downloads filled sheets to TSVs.
- `validate.py`: Shared base — just the `ValidationIssue` dataclass.
- `validate_planar.py`: `validate_planar_df(df)` — validates planar structure TSVs (sequential positions, unique names, keystone present, valid Position_Type/Class_Type, element conventions including collapse detection).
- `validate_diagnostics.py`: `validate_diagnostics_df(df, lang_id)` — validates diagnostics_{lang_id}.tsv (required columns, Language field, brace syntax, criterion names against diagnostic_criteria.yaml, class names against planars/ modules, construction naming rules).
- `validate_coding.py`: `validate-coding` command — reads annotation sheets, validates values, clears/updates pink cell highlights. Also calls `validate_planar_df` and `validate_diagnostics_df` before sheet validation.
- `generate_notebooks.py`: `generate-notebooks` — generates per-language and coordinator Colab notebooks.
- `check_codebook.py`: `check-codebook` — consistency check between diagnostic_criteria.yaml, diagnostic_classes.yaml, analysis modules, and diagnostics_{lang_id}.tsv.
- `integrity_check.py`: `integrity-check` — full project-wide health report across six sections (PLANAR STRUCTURE, DIAGNOSTICS, CODEBOOK CONSISTENCY, ANALYSIS CONSISTENCY, ANNOTATION SHEETS, NEEDS REVIEW). Use `--lang` to restrict per-language sections; `--sheets` to include live Google Sheets structural validation.
- `glottolog.py`: `lookup-lang` — fetch and cache Glottolog metadata (name, family, ISO code, coordinates) for a language ID. Cache at `glottolog_cache.json` (gitignored). Also provides `is_valid_format()` and `cached_entry()` used by `validate_diagnostics.py` for check 6 (Glottocode format + advisory).
- `populate_sheets.py`: One-time utility for uploading legacy TSV data.
- `setup_root_folder.py`: One-time Drive folder setup (run once after first `generate-sheets`).

`coded_data/{lang_id}/{class_name}/` contains the filled TSVs imported from Google Sheets (local dev use only — Colab reads directly from Sheets). Archive TSVs live in `coded_data/{lang_id}/{class_name}/archive/`.

`generate_snapshots.py` at the repo root regenerates snapshot baselines; `pytest` (via `tests/test_snapshots.py`) runs the snapshot regression tests alongside all other tests. Snapshots live in `tests/snapshots/`. Auto-discovers all planars modules with `derive` + `format_result`. `check_snapshots.py` remains as a quick CLI alternative for snapshot-only checks.

`coded_data/synth0001/` is a synthetic second-language dataset for multi-language testing (not real data). It has a genuinely different planar structure (28 positions, keystone at 23) derived from `stan1293` by dropping 9 positions and flipping ~25% of criterion values. `tests/make_synthetic_lang.py` generates it (`--apply` to write, `--clean --apply` to remove).

## diagnostics_{lang_id}.tsv format

Criteria default to `y/n` dropdowns. To specify custom values use brace syntax:

```
stressed{y/n/both}, independence, left-interaction, right-interaction
```

`coding/make_forms.py` parses this into `(criterion_names, criterion_values)`. `python -m coding generate-sheets` applies per-column dropdown validation and appends a free-text `Comments` column to every tab. `python -m coding import-sheets` validates each criterion against its allowed set (always also accepts `na` and `?`) and passes Comments through unchanged.

`python -m coding update-sheets` brings existing sheets up to date when new elements are added to the planar structure. Always dry-run first.

`diagnostics_{lang_id}.tsv` is also the source of truth for notebook generation. `python -m coding generate-notebooks` reads each language's `diagnostics_{lang_id}.tsv` to discover analysis classes and generates three kinds of notebooks: a per-language contributor notebook (`domains_{lang_id}.ipynb`), per-language validation notebooks (`validation_{lang_id}.ipynb`), and a single coordinator notebook (`all_languages.ipynb`) covering all languages. Per-class cells in the coordinator notebook are generated automatically from the class list — adding a new class to `diagnostics_{lang_id}.tsv` and updating `_CLASS_DISPLAY_NAMES` in `coding/generate_notebooks.py`, then running `generate-notebooks --apply`, is all that's needed to include it. Notebook generation is triggered automatically at the end of `generate-sheets`, `sync-params --apply`, and `restructure-sheets --apply`. Templates live in `notebooks/templates/`; the generated notebooks are artifacts uploaded to Drive, not source files. Each analysis module must define a `derive` alias pointing to its primary derive function so the generation script can call it without a per-module name mapping (see e.g. `planars/ciscategorial.py`).

## Glottolog metadata convention

Language IDs in this project are Glottocodes (e.g., `arao1248`, `stan1293`). Glottolog metadata (human-readable name, ISO 639-3 code, language family, coordinates) is fetched once via `python -m coding lookup-lang <glottocode>` and cached locally in `glottolog_cache.json` (gitignored).

**Convention:** wherever a language ID appears in user-facing output — notebook headers, chart titles, report tables, Drive folder names, terminal output — prefer the `Name [glottocode]` format (e.g., `Araona [arao1248]`) over the bare Glottocode. The canonical helper for this is `coding/glottolog.py:cached_entry(glottocode)["name"]`.

Metadata is also written into `planars_config.json` on Drive (by `generate-sheets`) so Colab notebooks can access it without any local files. Per-language project metadata lives in a `meta` block in the same manifest entry: `source` (publication/chapter), `author`, `annotator`, `annotation_status`, `notes`. `generate-sheets` scaffolds empty `meta` fields for new languages; `integrity-check --sheets` warns when `source` or `author` are blank.

Use Glottolog metadata proactively for:
- Display names in notebooks, chart legends, and terminal output
- Family/macroarea grouping in future coverage tables and maps (issue #62)
- Language onboarding validation (`lookup-lang` before `generate-sheets`)

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
| `schemas/diagnostic_criteria.yaml` | New diagnostic criteria, new analyses, `[PLACEHOLDER]` or `[NEEDS REVIEW]` entries resolved |
| `schemas/diagnostic_classes.yaml` | New analysis classes added, applicability, required criteria, qualification rules, or known construction types change |
| `schemas/planar.yaml` | New standard element labels or structural column conventions |
| `schemas/terms.yaml` | New analytical terms or chart label changes |
| `README.md` | Changes to the annotated TOC (audience routing, guide descriptions) |
| `docs/*.md` | User-facing workflow changes, setup instructions, new dependencies, new commands |
| `notebooks/templates/domains_boilerplate.ipynb` | Contributor notebook boilerplate changes (setup, auth, chart cell) — then run `generate-notebooks --apply` |
| `notebooks/templates/all_languages_boilerplate.ipynb` | Coordinator notebook boilerplate changes (setup, auth, helper, chart) — then run `generate-notebooks --apply` |
| `notebooks/templates/validation_boilerplate.ipynb` | Validation notebook boilerplate changes — then run `generate-notebooks --apply` |
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

Source: Jeff Good, "Domains of linearization, constituency, and wordhood in Chichewa" (draft ms.). Glottolog ID: nyan1308. First African language in planars; first language with an active cross-theoretic wordhood debate.

**Documented in source paper, not yet set up in planars:**
- 22-position clausal planar structure (Question Marker through postobject zone; keystone at Position 10, verb root)
- 96 constituency diagnostics (57 base + fractures) across six categories: free occurrence (indeterminate), morphosyntactic (non-interruptability, non-permutability, ciscategorial selection, repetition, biuniqueness), phonological (6 segmental processes + penultimate lengthening accentual), tonosegmental (29 tonal melody domains — a category absent from Tallman 2021 and TallmanEtAl 2024, needed for Bantu), and intonational (12 pitch/downdrift domains)
- Results (draft): 26 distinct domains, largely nesting, centered on verb root; forest visualization via `NonCollaborative/scripts/treeTraversal.py`

Onboarding will require scaffolding `tonosegmental` and `intonational` analysis modules (see issues #70, #71) before the full diagnostic set can be run.

## Issue tracking

Feature requests and bugs are tracked on GitHub Issues: https://github.com/jcgood/planars/issues

When creating a new issue, apply at least one label from the set below. Use `gh issue create --label "..."` or apply labels immediately after creation with `gh issue edit <n> --add-label "..."`.

### Labels

| Label | Meaning |
|-------|---------|
| `diagnostics` | Module design, diagnostic criteria, or qualification rules requiring linguistic validation — input from Adam needed before implementation. Filter: `gh issue list --label diagnostics` |

### Notable open issues

- **#80** — Auto-generate schema structure diagrams from YAML schema files.
- **#79** — Add references list and "How to cite" section to repository documentation.
- **#78** — Add `collection_required` field to `diagnostic_classes.yaml`; validate presence per language. Field added (all classes marked `[NEEDS COORDINATOR INPUT]`); validation logic and final values pending Adam's input.
- **#76** — Proactive detection of unauthorized sheet edits (scheduled `validate-coding`).
- **#75** — Auto-trigger snapshot regeneration when analysis output changes.
- **#74** — Schema change propagation: diagnostic criterion lifecycle tooling (add, remove, rename, split, merge across languages). Prerequisite for managing criterion evolution at scale.
- **#73** — `validate_diagnostics.py` conformance check: each language's `diagnostics_{lang_id}.tsv` must only use diagnostic criteria listed in `diagnostic_classes.yaml` (opt-in model enforcement).
- **#72** — Prepare Chichewa (nyan1308) for onboarding: planar structure, diagnostics, tonosegmental/intonational domains. `[Jeff]`
- **#71** — New analysis module: intonational domain (clause-level pitch patterns). `[diagnostics]`
- **#70** — New analysis module: tonosegmental domain (tonal melody overlaid on morphosyntax). `[diagnostics]`
- **#69** — Multilingual contributor assistant: chatbot to help contributors navigate the coding process.
- **#68** — Survey open typology codebases (Grambank, CLDF, AUTOTYP) for design ideas.
- **#67** — Verb-class-conditioned permutability: gap in nonpermutability qualification rules. `[diagnostics]`
- **#66** — Fluid/multi-position formatives: annotation challenge for nonpermutability. `[diagnostics]`
- **#65** — Prosodic minimality (bimoraicity) as a constituency diagnostic. `[diagnostics]`
- **#64** — Culminativity constraints as a constituency diagnostic class. `[diagnostics]`
- **#62** — New contributor and language onboarding: document and consolidate setup steps.
- **#61** — Replace hardcoded chart colors with auto-assigned colorblind-friendly palette.
- **#60** — Clarify `aspiration.py` scope: prosodic domain vs. segmental process. `[diagnostics]`
- **#59** — Nominal planar structures: scope expansion (Zapotec ch. 07 applies full test battery to noun complex). `[diagnostics]`
- **#58** — Biuniqueness type 2: non-automatic allomorphy as a distinct diagnostic. `[diagnostics]`
- **#57** — New analysis module: maximal reduplication domain. `[diagnostics]`
- **#56** — New analysis module: non-displacement domain. `[diagnostics]`
- **#55** — ~~Per-language metadata/documentation file (author, source, etc.)~~ — implemented: `meta` block scaffolded by `generate-sheets`; `integrity-check --sheets` warns on blank key fields.
- **#9** — Fill in `[PLACEHOLDER]` and `[NEEDS REVIEW]` entries in schema files (`diagnostic_criteria.yaml`, `diagnostic_classes.yaml`). Requires input from Adam. `[needs-input]`

## Work phases

This is a **research project**: the schemas, qualification rules, and analytical models are themselves outputs of the research process, not fixed inputs. Annotation work informs theory, which changes the schema files (`schemas/`), which changes what gets annotated. This makes it fundamentally unlike a business application with stable requirements — the tools serve a moving target by design. As understanding deepens across languages, all facets of the project (data model, diagnostics, module logic, documentation) are subject to revision.

Sessions tend to fall into a few natural patterns. Naming the primary focus at the start of a session helps keep scope manageable.

**Schema work** — Editing any file in `schemas/` or the qualification rules in analysis modules. The most consequential work; mistakes here cascade across languages and analyses. Go slow, run `integrity-check` after changes. Qualification rule changes must also propagate to inline comments and module docstrings — not just the YAML files.

**Language onboarding** — End-to-end work for a new language: gathering source material, drafting `diagnostics_{lang_id}.tsv`, running `generate-sheets`, producing a first-pass annotation, importing, and verifying analysis output. During prototyping, this has involved reading finished book chapters; in production, onboarding will be a collaborative process with contributors who may provide information in varied and yet-to-be-modeled forms (notes, drafts, conversation, partial data). The tooling should remain open to this rather than assuming a finished written source is always available. Automated first-pass coding may eventually be possible, but will always require expert review.

**Contributor tooling** — Building or improving the `coding/` scripts, sheet generation, import/validation pipelines, and notebook generation. Standard software work, but changes to sheet structure need `update-sheets` or `restructure-sheets` to propagate.

**Audit** — Checking consistency between code, documentation, codebook, and annotation data. Includes `integrity-check` (and `check-codebook` for lower-level detail), snapshot tests, and reviewing CLAUDE.md/docs for drift. Also includes verifying that inline comments and module docstrings match current behavior — code evolves faster than comments. A good way to start a session after a gap.

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
- `_TRAILING_COLS = ["Comments"]` is defined in `coding/generate_sheets.py` (source of truth for sheet creation) and `coding/validate_coding.py` (for validation). `coding/sync_params.py` and `coding/restructure_sheets.py` import it from `generate_sheets.py`. Add new trailing columns in both `generate_sheets.py` and `validate_coding.py` to propagate them to all new and existing sheets.
- `coding/populate_sheets.py` is a one-time utility for uploading legacy TSV data. Unnamed trailing columns in legacy TSVs are concatenated with ` | ` into Comments.
