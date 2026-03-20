# Analyses

This document describes the span types computed by planars, the available analysis modules, and their status. For parameter definitions and qualification rules, see `codebook.yaml`.

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
