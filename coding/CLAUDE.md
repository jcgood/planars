# coding/ package structure

`coding/` contains the coordinator tooling:
- `drive.py`: Shared Drive/Sheets client helpers — OAuth2 auth, config load/save, manifest upload/download, and `_with_retry(fn)` for 429/500/503 backoff.
- `schemas.py`: Cached loaders for `load_diagnostic_classes()` and `load_diagnostic_criteria()`; `languages.yaml` excluded (read fresh by callers).
- `make_forms.py`: `build_element_index`, `_read_diagnostics_for_language` — utilities used by other scripts. Also provides `resolve_keystone_active` and `resolve_keystone_na_criteria`. Handles `construction_criteria` — emits one TSV row per construction for classes that use it.
- `generate_sheets.py`: Creates annotation sheets; validates planar/diagnostics first; **`--force` aborts if any language already has sheet IDs in the manifest** (annotation data is irreplaceable); each spreadsheet gets a `Status` tab with `in-progress`/`ready-for-review` dropdowns. Supports two-stage pair-sheet workflows for **nonpermutability** (`element_prescreening` first, then `--regen-construction nonpermutability:general`) and **coreference** (`prescreening` first, then `--regen-construction coreference:reflexivization` etc. for each pair construction). `_regen_dependents_simple` runs automatically during `data-refresh`. Pass `--pos-remap OLD_NUM:NEW_NUM` (repeatable) when position numbers have shifted.
- `update_sheets.py`: Adds missing rows/trailing columns to existing sheets; ensures Status tab exists and is last. Also detects and creates new construction tabs for constructions in the diagnostics YAML not yet in the manifest; updates the manifest on Drive.
- `sync_params.py`: Syncs criterion columns when `diagnostics_{lang_id}.yaml` changes; supports rename, split, merge, remove; regenerates YAML afterward.
- `sync_diagnostics_yaml.py`: Syncs YAML → TSV (default), YAML → Sheet (`--to-sheet`), or diffs TSV → YAML (`--from-tsv`) writing ambiguous differences to `diagnostics_drift.json`.
- `sync_qualification_hashes.py`: Stamps `qualification_rule_hash` in `diagnostic_classes.yaml` after module review; run as the final step of the qualification rule update workflow.
- `generate_rule_update_prompt.py`: Generates a coordinator-facing Claude prompt for each class with a missing or stale `qualification_rule_hash`; used by `data-refresh.yml` to enrich `codebook-error` issue bodies.
- `restructure_sheets.py`: Archives and regenerates sheets after structural changes; `--rename-map` (positions), `--rename-element` (elements), `--split-element old:new1,new2,...` (retires one element into several finer-grained replacements within the same position; new rows get a Comments breadcrumb pointing back to the archived sheet if the old element had data), `--rename-class` (archives old sheet, creates new, renames local TSV dir, updates manifest); pair with `prune-manifest` if retiring rather than renaming.
- `import_sheets.py`: Downloads filled annotation sheets to TSVs; auto-applies safe downstream commands; writes destructive changes to `pending_changes.json`; aborts if `coded_data/` has uncommitted changes. **Import behavior by status**: `ready-for-review` tabs are fully imported — pipeline warnings surfaced, pending changes recorded. `in-progress` tabs are imported for backup and validated (pink highlighting updated), but pipeline warnings are suppressed and structural anomalies (missing rows/columns, >10% annotated-cell decrease) raise a `collaborator-check` issue instead of going to `pending_changes.json`. Use `--ignore-status` to treat all tabs as ready-for-review.
- `apply_pending.py`: Interactive review and application of destructive changes from `import-sheets`; closes the `pending-changes` issue when cleared.
- `prune_manifest.py`: Removes retired class entries from the Drive manifest, archives local TSVs, and moves Drive spreadsheets to `_archived/`; warns if a sheet was edited within 14 days.
- `validate.py`: Shared base — just the `ValidationIssue` dataclass.
- `validate_planar.py`: `validate_planar_df(df)` — validates planar TSV structure.
- `validate_diagnostics.py`: `validate_diagnostics_df(df, lang_id)` and `validate_diagnostics_yaml(data, lang_id)` — validate TSV and YAML forms against schema files.
- `validate_coding.py`: `validate-coding` — reads annotation sheets, validates values, updates pink highlights; exits code 1 on issues (used by the sheet-validation workflow).
- `generate_notebooks.py`: Generates per-language contributor, validation, and report notebooks, plus the coordinator notebook.
- `generate_reports.py`: Generates and uploads `report_{lang_id}.pdf` directly (no Colab; used by nightly GitHub Action).
- `check_codebook.py`: Consistency check between diagnostic_criteria.yaml, diagnostic_classes.yaml, analysis modules, and diagnostics_{lang_id}.tsv.
- `integrity_check.py`: Full project-wide health report; `--lang` restricts per-language sections; `--sheets` includes live Sheets structural validation.
- `glottolog.py`: Fetches and caches Glottolog metadata to `glottolog_cache.json` and `schemas/languages.yaml`; provides `is_valid_format()` and `cached_entry()`.
- `populate_sheets.py`: One-time utility for uploading legacy TSV data.
- `setup_root_folder.py`: One-time Drive folder setup (run once after first `generate-sheets`).
