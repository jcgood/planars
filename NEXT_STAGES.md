# Next Stages — Planning Document

Internal planning doc. Not user-facing.

Last updated: 2026-03-19

---

## Near-term (next session priorities)

These are sequenced — #33 and #32 should be done first because they unblock Drive organization
for everything that follows.

### ~~1. Create ConstituencyTypology root Drive folder (#33)~~ ✓ DONE

`python -m coding setup-root-folder` implemented. Creates the root folder, moves global files,
saves `_root_folder_id` to `drive_config.json`. New language folders are placed inside the root
automatically. **Still needs to be run once against the live Drive.** See issue #33.

### ~~2. Move coordinator notebook to root folder (#32)~~ ✓ DONE

`_get_global_folder_id()` updated to prefer `_root_folder_id`. Once `setup-root-folder` is run,
the next `generate-notebooks --apply` will upload `all_languages.ipynb` to the root folder.
`setup-root-folder` also physically moves the existing file. **Completes when `setup-root-folder`
is run.** See issue #32.

### (OLD) 1. Create ConstituencyTypology root Drive folder (#33)

Currently all language folders are siblings at the top level of the Drive space. The coordinator
notebook and `planars_config.json` have no natural home outside a language folder, so
`planars_config.json` currently lives in the first language folder alphabetically (stan1293).

Steps:
- Create a top-level folder named `ConstituencyTypology` in Drive
- Add `_root_folder_id` to `drive_config.json`
- Update `_get_global_folder_id()` in `coding/generate_notebooks.py` to use the root folder
- Update `coding/generate_sheets.py` to create new language folders inside the root folder
  (existing folders can remain where they are or be moved manually)
- Move `planars_config.json` on Drive to the root folder; update the stored file ID in
  `drive_config.json` (key `_planars_config_file_id`)

### 2. Move coordinator notebook to root folder (#32)

`all_languages.ipynb` covers all languages and doesn't belong in any one language folder.
After #33:
- Update `generate_notebooks.py` to upload `all_languages.ipynb` to the root folder instead of
  the first language folder
- Update `drive_config.json` key `_all_languages_notebook_file_id` to point to the new location
- Set Viewer permissions on the root folder so coordinators can see the notebook

### 3. Update contributor notebook template to include per-class sections (#31)

The coordinator notebook (`all_languages_boilerplate.ipynb`) already generates per-class report
cells automatically from the class list. The contributor notebook (`domains_boilerplate.ipynb`)
currently shows only a domain chart; it should also show per-class text reports (construction-by-
construction results) so contributors can see the same level of detail.

Steps:
- Add per-class report cells to the template (mirror the coordinator notebook's class-cell
  insertion logic in `generate_notebooks.py`)
- Re-run `python -m coding generate-notebooks` to push updated notebooks to Drive

### 4. Consolidate manifest + planars_config into one Drive config file (#30)

Currently there are two types of config files on Drive per language: `manifest_{lang_id}.json`
(maps class → sheet ID) and `planars_config.json` (maps lang_id → folder_id). These could be
merged into a single top-level config, reducing the number of Drive API calls and simplifying
bootstrap.

Design notes:
- Top-level `planars_config.json` would contain per-language manifest data plus folder IDs
- `drive_config.json` would shrink to just `_root_folder_id` + `_planars_config_file_id`
- All scripts that currently load `manifest_{lang_id}.json` would switch to loading the merged
  config and extracting the relevant section
- This is a refactor with no user-visible change; do after #33 so the file location is stable

### 5. Investigate Drive file visibility for contributors (#34)

Contributors (annotators) need to see their annotation sheets and their language notebook, but
should not see admin files (manifest JSON, planars_config.json, other languages' folders).
Currently everything in the shared language folder is visible to anyone with folder access.

Questions to answer:
- Can per-file permissions override folder permissions in Drive? (i.e., share a folder but
  restrict specific files within it?)
- Alternatively, can we put admin files in a subfolder with restricted access?
- What does the contributor experience look like — do they navigate Drive, or do they only
  ever open a shared link?
- Document findings and open a follow-up issue if action is needed

---

## Medium-term

### Expand code comments throughout repo (#29)

The codebase has grown significantly. Many functions in `coding/` are lightly commented or
uncommented. Priority areas:
- `generate_notebooks.py` (new and complex)
- `generate_sheets.py` (retry logic, manifest structure)
- `charts.py` (multi-language data flow)
- `io.py` (keystone_df separation logic)

### planars_prep: John's one-button Colab workflow (#13)

John (representative non-technical collaborator) needs a Colab notebook that:
- Has no configuration cells
- Opens, authenticates, and shows results with a single "Run all"
- Reads from the language folder he was already given access to

This is essentially a zero-config wrapper around the contributor notebook. It may just be a
matter of simplifying the auth cell and pre-baking the folder ID into a shared Drive copy.
Needs coordination with John to test.

### Import coordination: knowing when sheets are ready (#20)

Currently the coordinator must manually decide when to run `import-sheets`. There is no
mechanism for contributors to signal that their annotations are complete. Options:
- A "ready" tab or cell in the sheet that contributors mark
- A separate lightweight tracking sheet
- Out-of-band communication (e.g. email, Slack)

This likely needs a workflow decision before any code is written.

### PyPI uploads

Several library changes have accumulated since the last PyPI release:
- `derive` alias added to all five analysis modules
- Multi-language charts_by_language verified working
- (Check pyproject.toml for current version)

Pending releases: bump version in `pyproject.toml`, build, upload to PyPI, update Colab notebooks
if they pin a version.

---

## Deferred / needs external input

### Meso domains (#16) and interaction domains (#17)

Both require input from Adam (lead linguist) on the theoretical definition and the correct
operationalization in terms of existing parameters. Do not implement until definitions are
confirmed. `codebook.yaml` has stub entries with `[NEEDS REVIEW]` for the relevant parameters
(`left-interaction`, `right-interaction`).

### Rename diagnostics.tsv → diagnostic_classes.yaml (#21)

Deferred. The current name is functional and a rename requires updating all scripts, the
codebook, CLAUDE.md, and README. Not worth the disruption until the schema is more stable.

### pytest migration (#15)

Current regression testing uses `generate_snapshots.py` / `check_snapshots.py` (bespoke
snapshot diffing). Migration to pytest with snapshot plugins would improve discoverability and
CI integration. Deferred — not blocking any current work.

---

## Architecture notes for next session

### drive_config.json current structure

Per-language keys:
```json
{
  "stan1293": {
    "folder_id": "...",
    "manifest_file_id": "...",
    "domains_notebook_file_id": "..."
  }
}
```

Top-level keys (added by generate_notebooks):
```json
{
  "_planars_config_file_id": "...",
  "_all_languages_notebook_file_id": "..."
}
```

When #33 (root folder) is added, also add:
```json
{
  "_root_folder_id": "..."
}
```

### generate_notebooks.py: where things live

- `_get_global_folder_id()` — currently returns first language folder ID (stan1293); should
  return root folder ID once #33 is done
- `planars_config.json` on Drive — maps lang_id → folder_id; currently uploaded to stan1293
  folder; should move to root folder after #33
- `all_languages.ipynb` on Drive — same situation as planars_config.json

### Old notebooks

`notebooks/sync_colab.ipynb` and `notebooks/span_results_colab.ipynb` are the predecessor
manually-maintained Colab notebooks. They are superseded by the template+generation system
but still exist in the repo. Consider archiving to `notebooks/archive/` or deleting once the
generated notebooks are confirmed working for all collaborators.
