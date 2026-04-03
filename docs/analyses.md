# Analyses

This document describes the span types computed by planars, the available analysis modules, and their status. Four YAML files in `schemas/` govern the analysis framework:

- **`schemas/diagnostic_classes.yaml`** — the normative schema for analysis classes: which classes exist, when each applies (universal vs. conditional), construction-specific variants, required diagnostic criteria, qualification rules, and known construction types. See [The diagnostic classes schema](#the-diagnostic-classes-schema) below.
- **`schemas/diagnostic_criteria.yaml`** — the authoritative reference for diagnostic criterion semantics, allowed values, and linguistic definitions. See [The diagnostic criteria schema](#the-diagnostic-criteria-schema) below.
- **`schemas/terms.yaml`** — definitions of analytical terms (strict/loose span, partial/complete position, keystone, etc.) and chart label glossary.
- **`schemas/planar.yaml`** — planar structure ontology: structural columns, element conventions, and label standards.

---

## The diagnostic classes schema

`schemas/diagnostic_classes.yaml` is the source of truth for the analysis class framework. It is separate from `schemas/diagnostic_criteria.yaml` (which owns criterion semantics) and serves as the normative reference for coordinators and contributors adding new languages or analyses.

Each entry contains:

| Field | Contents |
|---|---|
| `name` | Machine name — matches the `planars/` module and `coded_data/` subfolder |
| `display_name` | Human-readable label used in notebook section headers |
| `domain_type` | `morphosyntactic`, `phonological`, or `indeterminate` |
| `applicability` | `universal` (applies to every language) or `conditional` (applies only when stated conditions hold) |
| `applicability_conditions` | Prose description of when a conditional class applies |
| `specificity` | `general` (one TSV per language) or `construction_specific` (one TSV per construction) |
| `known_constructions` | Non-exhaustive examples for construction-specific classes |
| `required_criteria` | Diagnostic criterion columns that must appear in `diagnostics_{lang_id}.tsv` |
| `qualification_rule` | How the code decides whether a position qualifies — complete vs. partial, blocking conditions, etc. |
| `status` | `stable`, `[NEEDS REVIEW]`, or `[PLACEHOLDER]` |

### Human-editable workflow

To add a new analysis class: edit `schemas/diagnostic_classes.yaml`, then for each applicable language edit `diagnostics_{lang_id}.yaml` and run `sync-diagnostics-yaml --apply --lang {lang_id}` to regenerate the TSV. Ask Claude to scaffold the new `planars/` module. `check-codebook` validates existing diagnostics files against this schema.

---

## The diagnostic criteria schema

`schemas/diagnostic_criteria.yaml` is the definitive reference for diagnostic criterion semantics. One entry per analysis module, each containing:

| Field | Contents |
|---|---|
| `name` | The module name — matches the CLI command and Python module (e.g., `ciscategorial`) |
| `description` | What the analysis tests, its theoretical basis, and its classification (morphosyntactic / phonological / indeterminate). Entries marked `[AUTO-DERIVED: NEEDS REVIEW]` have not been verified by a domain expert. |
| `diagnostic_criteria` | Each criterion's name, allowed values, and what it means in context |

Shared criterion values across all analyses:

| Value | Meaning |
|---|---|
| `y` | Yes — the criterion holds for this element |
| `n` | No — the criterion does not hold |
| `NA` | Not applicable — used only in keystone rows (`v:verbstem`); do not change |
| `?` | Unknown / not yet annotated — treated as missing data; triggers a validation warning on import |

To look up a specific analysis, search for `- name: <analysis>` in `schemas/diagnostic_criteria.yaml`.

### Rendering the schema files

To read the schemas as formatted Markdown rather than raw YAML:

```bash
python render_codebook.py              # print to terminal
python render_codebook.py codebook.md  # write to a file
```

### Status markers

Entries in the `analyses` section may carry one of these markers in their `description`:

- **`[NEEDS REVIEW]`** — the rule was designed by a human but is provisional; specific criteria are flagged as uncertain (currently: aspiration qualification rules; `left-interaction` and `right-interaction` in stress).
- **`[AUTO-DERIVED: NEEDS REVIEW]`** — the diagnostic criterion design was derived by reading Tallman et al. 2024 without reviewing concrete language data for that analysis. Treat as a draft. See the [analyses table](#analysis-modules) below for which modules carry this flag and their data sources.
- **`[PLACEHOLDER]`** — the entry exists but has not been written yet. Do not use for annotation.

---

## Span types

All analyses produce results using a common framework. A **position** qualifies if its elements meet the analysis-specific condition. Two thresholds are defined:

- **Complete**: ALL elements in the position qualify
- **Partial**: AT LEAST ONE element qualifies

Two span geometries are defined, anchored at the **keystone position** (`v:verbstem`):

- **Strict**: Contiguous expansion from the keystone — stops at the first gap
- **Loose**: Extends to the farthest qualifying position on each side, regardless of gaps

This gives four span variants per analysis:

| | Complete positions | Partial positions |
|---|---|---|
| **Strict** (no gaps) | strict complete | strict partial |
| **Loose** (gaps allowed) | loose complete | loose partial |

Some analyses (stress, aspiration) use a **blocked span** instead: expand from the keystone outward, stopping just before the first position where a blocking condition holds. The keystone itself always remains in the domain.

---

## Analysis modules

| Analysis | Criteria | Spans derived | Status |
|---|---|---|---|
| `ciscategorial` | `V-combines`, `N-combines`, `A-combines` | 4 (strict/loose × complete/partial) | stable |
| `subspanrepetition` | `widescope_left`, `widescope_right`, `fillable_botheither_conjunct` | 20 (5 categories × 4) | stable |
| `noninterruption` | `free`, `multiple` | 4 strict spans (2 domain types × complete/partial) | stable |
| `metrical` | `accented`, `obligatory`, `independence`, `left-interaction`, `right-interaction` (blocked-span); `applies` (positive-qual) | 4 (2 domain types × complete/partial) | stable † |
| `nonpermutability` | `permutable`, `scopal` | 4 strict spans (2 domain types × complete/partial) | [AUTO-DERIVED] ‡ |
| `free_occurrence` | `free` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `segmental` | `aspirated` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] ‡ |
| `tonal` | `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `tonosegmental` | `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `intonational` | `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `biuniqueness` | `biunique` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `repair` | `restart` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `pausing` | `pause_domain` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `idiom` | `idiomatic` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `play_language` | `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `proform` | `substitutable` | 4 (strict/loose × complete/partial) | [NEEDS REVIEW] ¶ |

**Status key:** `stable` — confirmed and coordinator-approved. `[AUTO-DERIVED]` — diagnostic criterion design derived from reading Tallman et al. 2024; not yet coordinator-approved. `[NEEDS REVIEW]` — specific known concerns beyond AUTO-DERIVED. Only a coordinator should promote a module out of AUTO-DERIVED status.

† `left-interaction` and `right-interaction` criteria remain provisional — see issue #17.

‡ Likely stable based on cross-language evidence (see `schemas/diagnostic_classes.yaml`), but coordinator sign-off still needed.

¶ Not included in the langsci/291 published database (ch. 17, line 543). Prospective class.

---

## Notes on specific analyses

### Metrical and segmental (blocked-span constructions)

Both support a `blocked_span` path: expand from the keystone outward, stopping just before the first blocking position. Two domain types are defined:

- **Minimal**: blocked by `accented ∈ {y, both} AND independence=y`
- **Maximal**: blocked by `obligatory=y AND independence=y`

Each domain type has a complete/partial distinction, giving 4 spans per analysis. The `left-interaction` and `right-interaction` criteria are marked `[NEEDS REVIEW]` in `schemas/diagnostic_criteria.yaml` — their role in blocking conditions has not been finalized.

### Noninterruption

Two domain types:

- **no-free**: positions where `free=n`
- **single-free**: positions where `free=n` OR (`free=y AND multiple=n`)

Returns 4 strict spans (2 domain types × complete/partial). No loose spans — gaps are not meaningful for interruption domains.

### Nonpermutability

Two domain types:

- **Strict**: absolutely fixed order (`permutable=n`)
- **Flexible**: fixed OR variable-with-scope (`permutable=n` OR (`permutable=y AND scopal=y`))

Each with complete/partial × strict spans = 4 spans total.

### Biuniqueness

The `biunique=n` qualification identifies elements that are pieces of a circumfix or extended exponent. The loose partial span — extending from the prefix piece to the suffix piece — is the primary result.

---

## Charting

`planars.charts` provides functions for visualizing span results across all languages:

```python
from planars.reports import project_spans
from planars.charts import charts_by_language

df, lang_meta = project_spans(source="local", repo_root=repo_root)
for lang_id, fig in charts_by_language(df, lang_meta).items():
    fig.show()
```

`project_spans` runs all analyses over all filled TSVs in `coded_data/` and returns a DataFrame with columns `Language`, `Test_Labels`, `Analysis`, `Left_Edge`, `Right_Edge`, `Size`, plus a `lang_meta` dict keyed by language ID (each holding `keystone_pos` and `pos_to_name`). Use `source="sheets"` with `gc` and `manifest` arguments to read directly from Google Sheets — this is what the Colab notebooks use. `language_spans(lang_id, ...)` does the same for a single language. Both live in `planars.reports`, which is the canonical data layer; `planars.charts` handles visualization only. See the [Notebooks guide](notebooks.md) for how charts appear in practice.
