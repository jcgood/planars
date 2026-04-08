# Data management

This document describes the two-repository architecture, the format of input files, and how annotation data is organized on disk.

---

## Two-repository architecture

The project uses two separate git repositories:

- **`planars`** (this repo) — the library and coordinator tooling. Public.
- **`planars-data`** — annotation data. Private; restricted to authorized coordinators.

Coordinators clone both and nest `planars-data` inside `planars` as `coded_data/`. The outer repo ignores `coded_data/` entirely (it is listed in `.gitignore`). All `coding/` scripts find data at `coded_data/` with no extra configuration.

Code and data are always committed and pushed separately — they go to different repositories. See the [Coordinator guide](coordinator-guide.md) for setup instructions and the daily git workflow.

---

## Repository structure

```
planars/                        Core library
  io.py                         Shared TSV/Sheets loader
  spans.py                      Span computation functions
  ciscategorial.py              }
  subspanrepetition.py          }
  noninterruption.py            }
  stress.py                     } Analysis modules
  aspiration.py                 }
  nonpermutability.py           }
  free_occurrence.py            }
  biuniqueness.py               }
  repair.py                     }
  segmental.py                  }
  suprasegmental.py             }
  pausing.py                    }
  proform.py                    }
  play_language.py              }
  idiom.py                      }
  charts.py                     Span collection and domain chart
  cli.py                        Command-line entry point
coding/                         Google Sheets workflow tools (python -m coding <command>)
  make_forms.py                 Planar structure and diagnostics utilities
  generate_sheets.py            Create annotation forms in Google Drive
  update_sheets.py              Add missing rows to existing sheets
  sync_params.py                Sync param columns when diagnostics_{lang_id}.tsv changes
  restructure_sheets.py         Archive and regenerate sheets after structural changes
  import_sheets.py              Download filled sheets to TSVs; sync planar/diagnostics Sheets
  apply_pending.py              Review and apply pending destructive changes
  validate.py                   Shared validation type (ValidationIssue)
  validate_planar.py            Planar structure TSV validation
  validate_diagnostics.py       diagnostics_{lang_id}.tsv validation
  validate_coding.py            Annotation sheet validation + validate-coding command
  generate_notebooks.py         Generate and upload Colab notebooks
  check_codebook.py             Consistency check: diagnostic_criteria.yaml ↔ modules ↔ diagnostics_{lang_id}.tsv
  populate_sheets.py            Upload legacy TSV data (one-time utility)
  setup_root_folder.py          One-time Drive folder setup
coded_data/{lang_id}/           Annotation data per language (in planars-data repo)
  lang_setup/                 Planar structure TSV + diagnostics_{lang_id}.tsv
  {class_name}/                 Filled TSVs per analysis class
  archive/{class_name}/         Superseded TSVs (after import-sheets --overwrite-existing or prune-manifest)
coded_data/synth0001/           Synthetic second-language dataset (not real data)
notebooks/
  templates/                    Boilerplate notebooks used by generate-notebooks
  archive/                      Superseded notebooks
tests/snapshots/                Regression test baselines
schemas/
  diagnostic_criteria.yaml      Diagnostic criterion definitions and allowed values
  diagnostic_classes.yaml       Analysis class schema (applicability, required criteria, qualification rules)
  planar.yaml                   Planar structure ontology (structural columns, element conventions)
  terms.yaml                    Analytical vocabulary (strict/loose span, etc.) and chart labels
  codebook.yaml                 Redirect stub — see the four files above
docs/                           Documentation (this directory)
```

---

## Planar structure: lang_setup/

Each language has a `lang_setup/` directory containing:

- `planar_{lang_id}-{date}.tsv` — the planar structure
- `diagnostics_{lang_id}.tsv` — which analyses to run and with which diagnostic criteria

The language ID is inferred from the planar filename: `planar_stan1293-20260209.tsv` → `stan1293`.

### Planar structure TSV

Defines the ordered sequence of positions and their elements. Required columns:

| Column | Contents |
|---|---|
| `Position_Number` | Sequential integer; positions must be contiguous |
| `Position_Name` | Unique name for the position; keystone must be named `v:verbstem` |
| `Element` | Element label (form or form-type within the position) |
| `Position_Type` | Type of position (see `schemas/planar.yaml`) |
| `Class_Type` | Class of element |

Elements with leading or trailing hyphens are wrapped in `[brackets]` to avoid spreadsheet parsing issues (e.g., `-suffix` → `[-suffix]`).

The **keystone position** (`v:verbstem`) is the anchor for all span computations. It must be present. In filled TSVs, keystone rows carry actual criterion values (not `NA`) so they can participate in blocking condition checks (stress, aspiration). They are excluded from span expansion — `load_filled_tsv` returns the keystone rows separately as `keystone_df`.

---

## diagnostics_{lang_id}.tsv

Controls which analyses and constructions are run for a language. Required columns:

| Column | Contents |
|---|---|
| `Language` | Language ID (must match the planar filename) |
| `Class` | Name of the analysis module (e.g., `ciscategorial`) |
| `Constructions` | Tab name(s) in Google Sheets; comma-separated list for construction-specific classes |
| `Criteria` | Comma-separated list of diagnostic criteria for this analysis |

Criteria default to `y/n` dropdowns. To specify custom allowed values, use brace syntax:

```
accented{y/n/both}, independence, left-interaction, right-interaction
```

`coding/generate_sheets.py` applies per-column dropdown validation using these values. `coding/import-sheets` validates each cell against its allowed set (always also accepts `na` and `?`).

`diagnostics_{lang_id}.tsv` is also the source of truth for notebook generation — `generate-notebooks` reads it to discover analysis classes and constructions. Adding a new class to `diagnostics_{lang_id}.tsv` and running `generate-notebooks --apply` will include it in the notebooks — but you must also add the class name to `_CLASS_DISPLAY_NAMES` in `coding/generate_notebooks.py` first (this dict controls the human-readable section headers).

---

## coded_data/ layout

```
coded_data/
  {lang_id}/
    lang_setup/
      planar_{lang_id}-{date}.tsv
      diagnostics_{lang_id}.tsv
    {class_name}/
      {construction}.tsv              ← imported from Google Sheets
      archive/                        ← old sheets archived to Drive (not local files)
  synth0001/                          ← synthetic test language (not real data)
```

Filled TSV filenames use the pattern `{construction}.tsv`. The language ID and analysis class are encoded in the directory path, not the filename.

### Google Drive manifest

The Drive manifest (`manifest.json`) is stored on Drive and contains all languages' sheet metadata and folder IDs. A local `drive_config.json` (gitignored, in the repo root) bootstraps the Drive lookup. It holds:

- `_root_folder_id` — the `ConstituencyTypology` top-level Drive folder
- `_planars_config_file_id` — the manifest file
- `_all_languages_notebook_file_id` — the coordinator notebook
- Per-language: `folder_id`, `domains_notebook_file_id`, `validation_notebook_file_id`, `planar_spreadsheet_id`, `diagnostics_spreadsheet_id`

Do not commit `drive_config.json` — it is gitignored.

---

## Design principles

The planars data model was developed independently but shares fundamental design principles with [AUTOTYP](https://github.com/autotyp/autotyp-data) (see Witzlack-Makarevich et al., "Managing AUTOTYP Data: Design Principles and Implementation," ch. 56 in *The Open Handbook of Linguistic Data Management*, MIT Press). These principles explain architectural decisions that might otherwise seem arbitrary.

**Late aggregation**: Raw annotation data is stored exhaustively at the lowest level — y/n per element per position. All derived categories (spans, domain types, partial vs. complete distinctions) are computed algorithmically in the analysis modules, not stored. This means the same annotation files can answer different research questions as the theoretical framework evolves, without recoding. Never aggregate during data collection.

**Autotypology (dynamic schema)**: The diagnostic criterion definitions in `schemas/diagnostic_criteria.yaml` and analysis classes in `schemas/diagnostic_classes.yaml` are not a fixed a priori etic grid. They are updated throughout data collection as new languages reveal new phenomena. The `[PLACEHOLDER]` and `[NEEDS REVIEW]` markers in these files reflect genuine ongoing theoretical work, not incomplete implementation. This is by design; AUTOTYP observes that typologies typically stabilize after ~40–50 entries.

**Definition files vs. data files**: `schemas/` files are *definition files* — they list possible criterion values with linguistic definitions and are updated dynamically. Filled TSVs under `coded_data/` are *data files* — actual annotations for individual languages. Keep them clearly separate.

**Language reports**: Free-text documents containing paradigms, citation examples, and motivation for coding decisions serve as an audit trail connecting annotations to their empirical basis. Planars currently relies on source chapters in this role; a structured language report format for production onboarding is an open question (see issue #68).
