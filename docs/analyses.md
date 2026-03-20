# Analyses

This document describes the span types computed by planars, the available analysis modules, and their status. `codebook.yaml` is the authoritative reference for all parameters and qualification rules — see [The codebook](#the-codebook) below for a guide to reading it.

---

## The codebook

`codebook.yaml` (repo root) is the definitive reference for everything that governs annotation and computation. It is a YAML file with five top-level sections:

### structural_columns

Columns present in every filled TSV regardless of analysis: `Element`, `Position_Name`, `Position_Number`. Described once here rather than repeated per-analysis.

### analyses

One entry per analysis module. Each entry contains:

| Field | Contents |
|---|---|
| `name` | The module name — matches the CLI command and Python module (e.g., `ciscategorial`) |
| `description` | What the analysis tests, its theoretical basis, and its classification (morphosyntactic / phonological / indeterminate). Entries marked `[AUTO-DERIVED: NEEDS REVIEW]` have not been verified by a domain expert. |
| `parameters` | Each parameter's name, allowed values, and what it means in context |
| `qualification_rule` | Exactly how the code decides whether a position qualifies — complete vs. partial, which parameters are checked, and (for blocked-span analyses) what constitutes a domain boundary |

To look up a specific analysis, search for `- name: <analysis>` in the file, or render it as Markdown (see [Rendering](#rendering-the-codebook) below).

### shared_values

The four values accepted by all parameters across all analyses:

| Value | Meaning |
|---|---|
| `y` | Yes — the parameter holds for this element |
| `n` | No — the parameter does not hold |
| `NA` | Not applicable — used only in keystone rows (`v:verbstem`); do not change |
| `?` | Unknown / not yet annotated — treated as missing data; triggers a validation warning on import |

### terms

A glossary of analytical terms used throughout the project: *planar structure*, *position*, *element*, *keystone*, *partial position*, *complete position*, *strict span*, *loose span*, *ciscategorial*, *transcategorial*, *subspan repetition*, *wide scope*, *narrow scope*, *non-interruption domain*. If you encounter an unfamiliar term, check here first.

### chart_labels

Short labels used in `domain_chart()` output. Useful when reading the domain chart in a Colab notebook and you want to know exactly what a label like `"ws-L loose partial"` means. See the [Notebooks guide](notebooks.md) for how charts are displayed.

### Rendering the codebook

To read the codebook as formatted Markdown rather than raw YAML:

```bash
python render_codebook.py              # print to terminal
python render_codebook.py codebook.md  # write to a file
```

### Status markers

Entries in the `analyses` section may carry one of these markers in their `description`:

- **`[NEEDS REVIEW]`** — the rule was designed by a human but is provisional; specific parameters are flagged as uncertain (currently: aspiration qualification rules; `left-interaction` and `right-interaction` in stress).
- **`[AUTO-DERIVED: NEEDS REVIEW]`** — the parameter design was derived by reading Tallman et al. 2024 without reviewing concrete language data for that analysis. Treat as a draft. See the [analyses table](#analysis-modules) below for which modules carry this flag and their data sources.
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

| Analysis | Parameters | Spans derived | Status |
|---|---|---|---|
| `ciscategorial` | `V-combines`, `N-combines`, `A-combines` | 4 (strict/loose × complete/partial) | — |
| `subspanrepetition` | `widescope_left`, `widescope_right`, `fillable_botheither_conjunct` | 20 (5 categories × 4) | — |
| `noninterruption` | `free`, `multiple` | 4 strict spans (2 domain types × complete/partial) | — |
| `stress` | `stressed`, `obligatory`, `independence`, `left-interaction`, `right-interaction` | 4 (2 domain types × complete/partial) | — |
| `aspiration` | `stressed`, `obligatory`, `independence`, `left-interaction`, `right-interaction` | 4 (2 domain types × complete/partial) | [NEEDS REVIEW] |
| `nonpermutability` †| `permutable`, `scopal` | 4 strict spans (2 domain types × complete/partial) | [AUTO-DERIVED] |
| `free_occurrence` †| `free` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `biuniqueness` †| `biunique` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `repair` †| `restart` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `segmental` †| `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `suprasegmental` †| `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `pausing` ‡| `pause_domain` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `proform` ‡| `substitutable` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `play_language` ‡| `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `idiom` ‡| `idiomatic` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |

**Status key:**

- `[NEEDS REVIEW]` — rule is human-designed but provisional; specific parameters are under review (see `codebook.yaml`).
- `[AUTO-DERIVED]` — parameter design and qualification rules were derived by reading Tallman et al. 2024 and have not been verified by a domain expert. Treat these as drafts: check `codebook.yaml` for details before using them for annotation or analysis.

† Derived from specific language chapters in Tallman et al. 2024 (Araona ch. 13, Cup'ik ch. 2) — has concrete data support but still needs expert sign-off.

‡ Derived from the Discussion chapter (ch. 17) description only — no concrete language data was reviewed; parameter design is more speculative.

---

## Notes on specific analyses

### Stress and aspiration

Both use `blocked_span`: expand from the keystone outward, stopping just before the first blocking position. Two domain types are defined:

- **Minimal** (stress): blocked by `stressed ∈ {y, both} AND independence=y`
- **Maximal** (stress): blocked by `obligatory=y AND independence=y`

Each domain type has a complete/partial distinction, giving 4 spans per analysis. The `left-interaction` and `right-interaction` parameters are marked `[NEEDS REVIEW]` in `codebook.yaml` — their role in blocking conditions has not been finalized. Aspiration mirrors the stress structure but its qualification rules are also `[NEEDS REVIEW]`.

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
from planars.charts import collect_all_spans, charts_by_language

df, lang_meta = collect_all_spans(repo_root)
for lang_id, fig in charts_by_language(df, lang_meta).items():
    fig.show()
```

`collect_all_spans` runs all analyses over all filled TSVs in `coded_data/` and returns a DataFrame with columns `Language`, `Test_Labels`, `Analysis`, `Left_Edge`, `Right_Edge`, `Size`, plus a `lang_meta` dict keyed by language ID (each holding `keystone_pos` and `pos_to_name`). `collect_all_spans_from_sheets(gc, manifest)` does the same but reads directly from Google Sheets — this is what the Colab notebooks use. See the [Notebooks guide](notebooks.md) for how charts appear in practice.
