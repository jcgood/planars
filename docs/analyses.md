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
| `nonpermutability` | `scopal` (pair-level) | 3 spans (strict, minimal flexible, maximal flexible) | [AUTO-DERIVED] ‡ |
| `free_occurrence` | `free`, `left-edge-of-free-form`, `right-edge-of-free-form`, `dependent-on-left`, `dependent-on-right` | 2 spans (minimal, maximal) | [AUTO-DERIVED] |
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

Two-stage annotation workflow:

**Stage 1 — element_prescreening sheet** (element rows, `scopal={y,n,both}`): identifies which elements participate in any meaningful variable ordering. Elements with `scopal=n` are filtered out of Stage 2. Elements with `scopal=both` have mixed orderings (some scopal, some freely variable) and are included in Stage 2. Annotate Stage 1 before generating Stage 2.

**Stage 2 — pairs sheet** (`general` construction, pair rows): each row is a (Element_A, Element_B) pair with `scopal={y,n}`. Generated from the Option C structural enumeration, filtered to exclude pairs where either element has `scopal=n` from Stage 1. Three spans:

- **Strict**: structurally derived (no annotation needed) — contiguous Slots from keystone where all elements appear in exactly one position.
- **Minimal flexible**: extends the strict span through positions with no free-permutable elements (no element in a `scopal=n` pair).
- **Maximal flexible**: extends through free-permutable interior positions as long as the outermost edge positions are not free-permutable.

### Free occurrence

Five criteria: `free`, `left-edge-of-free-form`, `right-edge-of-free-form`, `dependent-on-left`, `dependent-on-right`. The keystone row carries a real `free` value (`keystone_active_default: true`), but all annotation columns are always `na` on the keystone (it is the anchor, not a dependent). Two spans:

- **Minimal**: if keystone `free=y`, the keystone position alone; if `free=n`, the span from the keystone's `dependent-on-left` to `dependent-on-right` positions.
- **Maximal**: from the leftmost to rightmost free-occurrence-internal position. A position is internal if any element has `left-edge-of-free-form=y` (left of keystone), `right-edge-of-free-form=y` (right of keystone), or a `dependent-on-left`/`dependent-on-right` value equal to the keystone position number.

All four annotation columns (`left-edge-of-free-form`, `right-edge-of-free-form`, `dependent-on-left`, `dependent-on-right`) apply to **bound elements only** (`free=n`). Free elements (`free=y`) receive `na` in all annotation columns — they are filtered out of additional annotation at sheet generation time.

`free` is **pre-filled from the noninterruption sheet** at generation time — annotate noninterruption before generating the free_occurrence sheet. `integrity-check` warns when `free` values differ across sheets (e.g. after a noninterruption edit).

`dependent-on-left` and `dependent-on-right` hold a position number as a string, or `na`. These are position references, not fixed criterion values — `validate-coding` does not currently validate them against the planar structure.

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
