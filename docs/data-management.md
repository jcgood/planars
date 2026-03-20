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
  sync_params.py                Sync param columns when diagnostics.tsv changes
  restructure_sheets.py         Archive and regenerate sheets after structural changes
  import_sheets.py              Download filled sheets to TSVs
  validate.py                   Shared validation type (ValidationIssue)
  validate_planar.py            Planar structure TSV validation
  validate_diagnostics.py       diagnostics.tsv validation
  validate_coding.py            Annotation sheet validation + validate-coding command
  generate_notebooks.py         Generate and upload Colab notebooks
  check_codebook.py             Consistency check: codebook.yaml ↔ modules ↔ diagnostics.tsv
  populate_sheets.py            Upload legacy TSV data (one-time utility)
  setup_root_folder.py          One-time Drive folder setup
coded_data/{lang_id}/           Annotation data per language (in planars-data repo)
  planar_input/                 Planar structure TSV + diagnostics.tsv
  {class_name}/                 Filled TSVs per analysis class
  {class_name}/archive/         Superseded TSVs (after restructure-sheets)
coded_data/synth0001/           Synthetic second-language dataset (not real data)
notebooks/
  templates/                    Boilerplate notebooks used by generate-notebooks
  archive/                      Superseded notebooks
tests/snapshots/                Regression test baselines
codebook.yaml                   Parameter and term definitions
docs/                           Documentation (this directory)
```

---

## Planar structure: planar_input/

Each language has a `planar_input/` directory containing:

- `planar_{lang_id}-{date}.tsv` — the planar structure
- `diagnostics.tsv` — which analyses to run and with which parameters

The language ID is inferred from the planar filename: `planar_stan1293-20260209.tsv` → `stan1293`.

### Planar structure TSV

Defines the ordered sequence of positions and their elements. Required columns:

| Column | Contents |
|---|---|
| `Position_Number` | Sequential integer; positions must be contiguous |
| `Position_Name` | Unique name for the position; keystone must be named `v:verbstem` |
| `Element` | Element label (form or form-type within the position) |
| `Position_Type` | Type of position (see `codebook.yaml`) |
| `Class_Type` | Class of element |

Elements with leading or trailing hyphens are wrapped in `[brackets]` to avoid spreadsheet parsing issues (e.g., `-suffix` → `[-suffix]`).

The **keystone position** (`v:verbstem`) is the anchor for all span computations. It must be present. In filled TSVs, keystone rows carry actual parameter values (not `NA`) so they can participate in blocking condition checks (stress, aspiration). They are excluded from span expansion — `load_filled_tsv` returns the keystone rows separately as `keystone_df`.

---

## diagnostics.tsv

Controls which analyses and constructions are run for a language. Required columns:

| Column | Contents |
|---|---|
| `Language` | Language ID (must match the planar filename) |
| `Analysis_Class` | Name of the analysis module (e.g., `ciscategorial`) |
| `Construction` | Construction name (used as tab name in Google Sheets) |
| `Parameters` | Comma-separated list of parameter columns for this analysis |

Parameters default to `y/n` dropdowns. To specify custom allowed values, use brace syntax:

```
stressed{y/n/both}, independence, left-interaction, right-interaction
```

`coding/generate_sheets.py` applies per-column dropdown validation using these values. `coding/import-sheets` validates each cell against its allowed set (always also accepts `na` and `?`).

`diagnostics.tsv` is also the source of truth for notebook generation — `generate-notebooks` reads it to discover analysis classes and constructions. Adding a new class to `diagnostics.tsv` and running `generate-notebooks --apply` is all that is needed to include it in the notebooks.

---

## coded_data/ layout

```
coded_data/
  {lang_id}/
    planar_input/
      planar_{lang_id}-{date}.tsv
      diagnostics.tsv
    {class_name}/
      {construction}_filled.tsv       ← imported from Google Sheets
      archive/
        {construction}_filled_{date}.tsv   ← archived by restructure-sheets
  synth0001/                          ← synthetic test language (not real data)
```

Filled TSV filenames use the pattern `{construction}_filled.tsv`. The language ID and analysis class are encoded in the directory path, not the filename. Legacy files may use `_fill.tsv` or `_full.tsv` suffixes.

### Google Drive manifest

The Drive manifest (`planars_config.json`) is stored on Drive and contains all languages' sheet metadata and folder IDs. A local `drive_config.json` (gitignored, in the repo root) bootstraps the Drive lookup. It holds:

- `_root_folder_id` — the `ConstituencyTypology` top-level Drive folder
- `_planars_config_file_id` — the manifest file
- `_all_languages_notebook_file_id` — the coordinator notebook
- Per-language: `folder_id`, `domains_notebook_file_id`

Do not commit `drive_config.json` — it is gitignored.
