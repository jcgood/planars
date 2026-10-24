# Analyses

This document describes the span types computed by planars, the available analysis modules, and their status. Five YAML files in `schemas/` govern the analysis framework:

- **`schemas/diagnostic_classes.yaml`** — the normative schema for analysis classes: which classes exist, when each applies (universal vs. conditional), construction-specific variants, required diagnostic criteria, span rules, and known construction types. See [The diagnostic classes schema](#the-diagnostic-classes-schema) below.
- **`schemas/diagnostic_classes_status.yaml`** — process/tracking state for the same classes (review status, whether collection is required, sheet instructions, the span-rule integrity hash), split out from `diagnostic_classes.yaml` in Phase 3 of the data layer redesign (issue #271) because the two move at different rates. `coding/schemas.py`'s `load_diagnostic_classes()` merges the two back into one dict per class at read time.
- **`schemas/diagnostic_criteria.yaml`** — the authoritative reference for diagnostic criterion semantics, allowed values, and linguistic definitions. See [The diagnostic criteria schema](#the-diagnostic-criteria-schema) below.
- **`schemas/terms.yaml`** — definitions of analytical terms (strict/loose span, partial/complete position, keystone, etc.) and chart label glossary.
- **`schemas/planar.yaml`** — planar structure ontology: structural columns, element conventions, and label standards.

---

## The diagnostic classes schema

`schemas/diagnostic_classes.yaml` is the source of truth for the linguistic content of the analysis class framework. It is separate from `schemas/diagnostic_criteria.yaml` (which owns criterion semantics) and from `schemas/diagnostic_classes_status.yaml` (which owns process/tracking state for the same classes — see below), and serves as the normative reference for coordinators and contributors adding new languages or analyses.

Each entry contains:

| Field | Contents |
|---|---|
| `name` | Machine name — matches the `planars/` module and `coded_data/` subfolder; also the join key into `diagnostic_classes_status.yaml` |
| `display_name` | Human-readable label used in notebook section headers |
| `domain_type` | `morphosyntactic`, `phonological`, or `indeterminate` |
| `applicability` | `universal` (applies to every language) or `conditional` (applies only when stated conditions hold) |
| `applicability_conditions` | Prose description of when a conditional class applies |
| `specificity` | `general` (one TSV per language) or `construction_specific` (one TSV per construction) |
| `known_constructions` | Non-exhaustive examples for construction-specific classes |
| `required_criteria` | Diagnostic criterion columns that must appear in `diagnostics_{lang_id}.tsv` |
| `span_rule` | How the code decides which positions are inside the span — complete vs. partial, blocking conditions, etc. |

`schemas/diagnostic_classes_status.yaml` carries each class's `status` (`stable`, `[NEEDS REVIEW]`, `[PLACEHOLDER]`, or `[AUTO-DERIVED]`), `criterion_set_status`, `collection_required`, `span_rule_hash`, `sheet_instructions`, and `include_planar_reference_tab` — see that file's own header for field docs.

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

- **`[NEEDS REVIEW]`** — the rule was designed by a human but is provisional; specific criteria are flagged as uncertain (currently: aspiration span rules; `left-interaction` and `right-interaction` in stress).
- **`[AUTO-DERIVED: NEEDS REVIEW]`** — the diagnostic criterion design was derived by reading Tallman et al. 2024 without reviewing concrete language data for that analysis. Treat as a draft. See the [analyses table](#analysis-modules) below for which modules carry this flag and their data sources.
- **`[PLACEHOLDER]`** — the entry exists but has not been written yet. Do not use for annotation.

---

## Span types

All analyses produce results using a common framework. A **position** counts toward the span if its elements meet the analysis-specific condition. Two thresholds are defined:

- **Complete**: ALL elements in the position meet the condition
- **Partial**: AT LEAST ONE element meets the condition

Two span geometries are defined, anchored at the **keystone position** (`v:verbstem`):

- **Strict**: Contiguous expansion from the keystone — stops at the first gap
- **Loose**: Extends to the farthest in-span position on each side, regardless of gaps

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
| `metrical` | `accented`, `obligatory`, `independence`, `left-interaction`, `right-interaction` (blocked-span); `applies` (positive-evidence) | 4 (2 domain types × complete/partial) | stable † |
| `nonpermutability` | `scopal` (pair-level) | 3 spans (strict, minimal flexible, maximal flexible) | [AUTO-DERIVED] ‡ |
| `coreference` | `referential` (prescreening); `reflexive_allowed`, `pronoun_allowed`, `np_allowed` (pair-level, per construction) | 4 spans per construction (binder strict/loose + bindee strict/loose) | [AUTO-DERIVED: NEEDS REVIEW] § |
| `free_occurrence` | `free`, `left-edge-of-free-form`, `right-edge-of-free-form`, `dependent-on-left`, `dependent-on-right` | 2 spans (minimal, maximal) | [AUTO-DERIVED] |
| `segmental` | `aspirated` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] ‡ |
| `tonal` | `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `tonosegmental` | `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `intonational` | `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `biuniqueness_deviations` | `forms_relation` (morphemes tab); `occurs_here`, `conditioning_type`, `conditioning_features`, `conditioned_by`, `trigger_filled` (morphs tab) | 2 per domain (raw, keystone-anchored); one domain per deviating morpheme at a position | [AUTO-DERIVED] |
| `repair` | `restart` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `pausing` | `pause_domain` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `idiom` | `idiomatic` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `play_language` | `applies` | 4 (strict/loose × complete/partial) | [AUTO-DERIVED] |
| `proform` | `shareable_proform_replace` | 4 (strict/loose × complete/partial) | [NEEDS REVIEW] ¶ |

**Status key:** `stable` — confirmed and coordinator-approved. `[AUTO-DERIVED]` — diagnostic criterion design derived from reading Tallman et al. 2024; not yet coordinator-approved. `[NEEDS REVIEW]` — specific known concerns beyond AUTO-DERIVED. Only a coordinator should promote a module out of AUTO-DERIVED status.

† `left-interaction` and `right-interaction` criteria remain provisional — see issue #17.

‡ Likely stable based on cross-language evidence (see `schemas/diagnostic_classes_status.yaml`), but coordinator sign-off still needed.

¶ Not included in the langsci/291 published database (ch. 17, line 543). Prospective class.

§ Span rules proposed Apr 2026 (issue #163). Coordinator linguistic sign-off required before promoting to stable.

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

- **Minimal**: if keystone `free=y`, the keystone position alone; if `free=n`, the span from the nearest position in the keystone's `dependent-on-left` to the nearest in its `dependent-on-right`.
- **Maximal**: from the leftmost to rightmost free-occurrence-internal position. A position is internal if any element has `left-edge-of-free-form=y` (left of keystone), `right-edge-of-free-form=y` (right of keystone), or the keystone position number among its `dependent-on-left`/`dependent-on-right` positions.

All four annotation columns (`left-edge-of-free-form`, `right-edge-of-free-form`, `dependent-on-left`, `dependent-on-right`) apply to **bound elements only** (`free=n`). Free elements (`free=y`) receive `na` in all annotation columns — they are filtered out of additional annotation at sheet generation time.

`free` is **pre-filled from the noninterruption sheet** at generation time — annotate noninterruption before generating the free_occurrence sheet. `integrity-check` warns when `free` values differ across sheets (e.g. after a noninterruption edit).

`dependent-on-left` and `dependent-on-right` hold one or more position numbers separated by `|`, meaning any one of them is enough for the element to surface (`8|12|30`; #318), or `na`. A comma is refused, so it stays free to mean "all of these" if that is ever needed. `validate-coding` checks every number against the planar. *(Toolkit extension: the list form goes beyond Tallman et al. 2024.)*

### Coreference

Three-stage annotation workflow corresponding to Principles A, B, and C:

**Stage 1 — prescreening sheet** (`prescreening` construction, element rows, `referential={y,n}`): identifies which elements can participate as binder or bindee. Only `referential=y` elements generate pair rows in Stages 2–4. `NP{…}` rows start as `y` (the construction's `prefill_by_label` in `diagnostic_classes.yaml`, #318); pronouns are left to the annotator.

**Stages 2–4 — pair sheets** (one per construction):

- `reflexive_coreference` (Principle A) — criterion `reflexive_allowed={y,n}`
- `pronoun_coreference` (Principle B; non-reflexive pronouns) — criterion `pronoun_allowed={y,n}`
- `np_coreference` (Principle C) — criterion `np_allowed={y,n}`

(Named `reflexivization`, `pronominalization`, `np_reference` until 2026-10-23, #318.)

Each pair sheet has rows `(Element_A, Position_A, Position_B, Direction, <criterion>)`. `Element_A` is the antecedent (binder) at `Position_A`; `Position_B` is the structural position of the anaphor (bindee). The annotator marks the criterion `=y` if the construction is allowed for that pair, `=n` if not.

Four spans are derived per construction:

- **Binder domain (strict)**: contiguous expansion from keystone through binder positions (positions of `Element_A` where criterion=y).
- **Binder domain (loose)**: leftmost to rightmost binder position (gaps allowed).
- **Bindee domain (strict)**: contiguous expansion from keystone through bindee positions (`Position_B` values where criterion=y).
- **Bindee domain (loose)**: leftmost to rightmost bindee position (gaps allowed).

Asymmetry outputs (binder-only, bindee-only, shared positions) approximate c-command without presupposing tree structure.

Annotate `prescreening` before generating pair sheets; `--regen-construction coreference:<construction>` regenerates any pair sheet filtered to referential elements.

### Proform

Tests which spans can be replaced by a proform (pro-verb/pro-VP, e.g. "do so"). Two constructions: `do_so_substitution` and `vp_ellipsis` (same logic, same criterion `shareable_proform_replace`).

**Two-tier span rule** — `shareable_proform_replace` takes three values:

- `y` — element is always inside the proform span (counts toward the strict span)
- `both` — element is optionally inside the span (adjunct-style; counts toward the loose span)
- `n` — element is never inside the span

A position is **strictly in span** (complete) when ALL elements = `y`. A position is **loosely in span** (partial) when ANY element = `y` or `both`. Standard strict/loose × complete/partial span computation then applies on top:

- **Strict complete span** — contiguous from keystone through positions where all elements = `y` (Adam's "strict replaceable" span)
- **Loose partial span** — farthest position on each side where any element = `y` or `both` (Adam's "loose replaceable" span)

**Known limitation:** the "do so" test cannot detect discontinuous constituencies (e.g. "John drank tea in Leipzig on Tuesday and Balthasar did so too in Zurich" — the discontinuous span in brackets is not captured). This is a recognized limitation of the test in the constituency literature and does not affect how planars records results.

### Biuniqueness deviations

One class for four of Tallman & Auderset's (2023) ways form and meaning can fail to match one-to-one (issue #254, designed 2026-10-11): **extended exponence** (one meaning, several pieces at once: *be … -ing*), **allomorphy** (one meaning, different forms by context: *do/does*, *will/'ll*), **cumulative exponence** (two meanings fused in one form: *went*, *won't*) and **zero morphs** (a meaning with no form: past-tense *cut*). Syncretism and empty morphs are registered in the schema but deferred.

Three-stage annotation, each tab generated from the one before:

1. **elements** (element rows): `has_allomorphs`, `members` (the variant forms, or known members of an open category), `co_exponents` (positions expressing the same meaning at once, by number or name; the morphemes tab names them).
2. **morphemes** (one row per morpheme): `morpheme_class`, `forms_relation` (`alternate` | `co-occur`).
3. **morphs** (one row per form at a position, pre-filled): `occurs_here`, `conditioning_type`, `conditioning_features`, `conditioned_by` (positions, by number or name), `trigger_filled`.

The deviation type of each form is **derived, never annotated**: co-occurring forms → extended exponence; phonologically conditioned forms and the elsewhere form carry no deviation; `trigger_filled=y` → allomorphy; `trigger_filled=n` → zero morph if the form equals the elsewhere form, otherwise cumulative exponence. A row the rules can't place is an error.

A **domain** is one morpheme at one position for one type (extended exponence: one morpheme across all its pieces). It covers that position plus every `conditioned_by` position of those forms. Two spans per domain: the **raw** span (contains the keystone only if the keystone falls inside — *does*, conditioned by the subject, spans `v:frontedauxiliary`–`v:npsubj1`) and the **keystone-anchored** span, for comparison with every other class.

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
