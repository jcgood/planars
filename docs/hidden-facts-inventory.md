# Hidden-facts inventory

**Status:** complete (Phase 2 of [data-layer-implementation-plan.md](data-layer-implementation-plan.md)). Written 2026-08-01.
**Rationale:** [data-layer-design.md](data-layer-design.md).

Every file in `coding/` and `planars/` was read or grepped for the fact
categories in scope: hardcoded class/construction names, hardcoded criterion
names, hardcoded column vocabularies, hardcoded file paths encoding
structure, hardcoded value semantics, and magic defaults/fallback lists.
Coverage was exhaustive for the larger, fact-dense files (`generate_sheets.py`,
`validate_coding.py`, `restructure_sheets.py`, `sync_params.py`, every
`planars/` analysis module) and grep-driven for smaller or more mechanical
files (Drive plumbing, one-time setup scripts, notebook/report generation)
where a full read turned up nothing beyond what grep already surfaced. This
inventory does not claim to be the last word — see `data-layer-design.md`'s
own framing: facts have been migrated into schema reactively, one per bug,
for the project's whole history, and this document is the first attempt to
get ahead of that pattern rather than the end of it.

This document inventories schema facts that currently live only inside a tool
body in `coding/` or `planars/`, rather than in an authoritative schema file
(`schemas/*.yaml`) or `data_dependency_schema/facts.yaml`. Per the Phase 2
scope, **this document does not fix anything** — it only records what exists,
where, and whether an authoritative source already exists elsewhere.

For each fact:
1. **What** — the fact, stated plainly
2. **Where** — `file.py:line`
3. **Authoritative source elsewhere?** — yes (name it, this is a *duplication*)
   or no
4. **Classification** — `derivable` (an authoritative source exists or could
   plausibly exist; code should read it) or `must-declare` (genuinely not
   derivable; belongs in a declaration)

Grouped by classification, duplications first (highest-priority — these are
active defects, not just missing declarations).

---

## Summary

**27 distinct facts** catalogued, touching roughly 60 individual hardcoded
locations across some 25 files in `coding/` and `planars/`.

| Classification | Count | Meaning |
|---|---|---|
| Duplications | 13 (`D-1`, `D-1b`, `D-1c`, `D0`, `D1`, `D2`, `D2b`, `D3`–`D8`) | An authoritative source already exists; code holds an independent second (often third, fourth, or fifth) copy that can drift silently. **Highest priority** — these are active defects, not just gaps. |
| Derivable | 8 (`R-1`, `R-2`, `R0`–`R5`) | No authoritative source exists yet, but one plausibly could/should — a schema field or shared helper is the natural fix. |
| Must-declare | 6 (`M0`–`M4`, `M-misc`) | Genuinely not derivable from any plausible schema source (linguistic judgment calls, workflow/state-file conventions, or — in `M0`'s case — a gap in the schema file itself). |

**Confirmed live drift (not hypothetical) found during this inventory,
i.e. cases where the duplication has already produced observably wrong
behavior, not just duplication risk:**
- `D1` / `D2`: four independent hardcoded copies of coreference/
  nonpermutability criterion value-lists omit `untestable`, a value
  `diagnostic_criteria.yaml` explicitly allows for `reflexive_allowed`/
  `pronoun_allowed`/`np_allowed`.
- `D8`: `generate_notebooks.py`'s hardcoded class-display-name dict is
  missing `phrasal_accent` (among others), so its notebook section header
  falls back to `"Phrasal Accent"` instead of the schema's actual
  `"Phrasal (Pitch) Accent Grouping"`.
- `R-1`: `planars/cli.py`'s analysis registry is missing `coreference` and
  `metrical` even though both modules are fully wired per the project's own
  convention — `python -m planars coreference ...` / `metrical ...` simply
  don't work.

**Most-replicated single fact:** the keystone position name `"v:verbstem"`
(`D0`) — hardcoded as a raw literal in at least 15 locations across 9 files,
including two `planars/` analysis modules, despite `planar.yaml` claiming
ownership of it and naming (incorrectly, in `planars/io.py`'s case) its
supposed readers.

**Most-replicated fact family:** per-class `required_criteria` (`D-1`) —
independently hardcoded in fourteen separate `planars/` analysis modules,
one per class, each an exact copy of that class's `required_criteria:`
field in `diagnostic_classes.yaml`.

See the phase brief's requested three most-dangerous items in the final
chat response accompanying this document; in short they are `D-1`
(required-criteria duplication across all analysis modules), `D0` (keystone
name duplication reaching into `planars/`), and `D1`/`D2` combined (the
four-file criterion-value-list duplication with a live missing-value bug).

---

## Duplications (authoritative source exists elsewhere; code holds a second copy)

### D-1. Every `planars/` analysis module hardcodes its own `_REQUIRED_CRITERIA`, independently duplicating `diagnostic_classes.yaml`'s `required_criteria` field, class by class
**What:** Fourteen of the eighteen standard-pattern analysis modules each
declare a module-level `_REQUIRED_CRITERIA` set/dict, byte-for-byte
duplicating that class's `required_criteria:` list in
`schemas/diagnostic_classes.yaml`. Spot-checked and confirmed matching for
`free_occurrence` (`{free, left-edge-of-free-form, right-edge-of-free-form,
dependent-on-left, dependent-on-right}` vs. schema line 400, identical) and
`metrical` (`{accented, obligatory, independence}` vs. schema line 579,
identical) — every other module below follows the identical pattern.
Because `planars/` is installed into Colab via `pip install` from GitHub
(per `pyproject.toml` version-bump convention in `CLAUDE.md`) while
`schemas/` ships as a Python package specifically so its YAML reaches Colab
too, there are now two independently-shipped copies of the same fact
reaching the same runtime by two different mechanisms — a schema edit that
bumps `required_criteria` in the YAML does not, by itself, change what
`load_filled_tsv()` enforces at load time in any of these fourteen modules.
This is the single most widely-replicated *linguistic* fact in the
inventory (as opposed to D0's structural/UI fact) — the criteria a class
requires are exactly the "fast-moving research frontier" tier
`data-layer-design.md` names as the most bug-prone to freeze into code.
**Where:**
  `planars/biuniqueness_exponence.py:9` (`{biunique}`),
  `planars/free_occurrence.py:11-17`,
  `planars/intonational.py:9` (`{applies}`),
  `planars/idiom.py:9` (`{idiomatic}`),
  `planars/noninterruption.py:9` (`{free, multiple}`),
  `planars/nonpermutability.py:10` (`{scopal}`),
  `planars/proform.py:9` (`{shareable_proform_replace}`),
  `planars/metrical.py:11` (`{accented, obligatory, independence}`),
  `planars/repair.py:9` (`{restart}`),
  `planars/pausing.py:9` (`{pause_domain}`),
  `planars/play_language.py:9` (`{applies}`),
  `planars/tonal.py:9` (`{applies}`),
  `planars/tonosegmental.py:9` (`{applies}`),
  `planars/subspanrepetition.py:9` (`{widescope_left, widescope_right,
  fillable_botheither_conjunct}`).
  `planars/ciscategorial.py` and `planars/coreference.py` are the two
  exceptions — `ciscategorial` uses inline `required_criteria` per call
  (confirmed by `check_codebook.py`'s own comment, see R0-adjacent note
  below) rather than a module constant, and `coreference` uses
  `_PAIR_CRITERIA` (see D-1b) instead of the standard shape since its
  criteria are construction-specific.
**Authoritative source:** `schemas/diagnostic_classes.yaml` — each class's
`required_criteria:` field.
**Classification:** derivable — `load_filled_tsv()`/`load_filled_sheet()`
already take `required_criteria` as a parameter (per `planars/CLAUDE.md`),
so the fix is each module reading its own class's `required_criteria` from
`load_diagnostic_classes()` at import/call time instead of restating it.

### D-1b. `coreference._PAIR_CRITERIA` and `_SNAPSHOT_CONSTRUCTIONS`/`nonpermutability._SNAPSHOT_CONSTRUCTIONS` duplicate `constructions:`/`known_constructions:` entries
**What:** `planars/coreference.py` hardcodes `_PAIR_CRITERIA =
{"reflexive_allowed", "pronoun_allowed", "np_allowed"}`, duplicating the
`criterion:` field already present on each of `diagnostic_classes.yaml`'s
three coreference pair constructions (lines 325, 330, 335). Separately,
`_SNAPSHOT_CONSTRUCTIONS = frozenset({"reflexivization", "pronominalization",
"np_reference"})` (coreference) and `_SNAPSHOT_CONSTRUCTIONS =
frozenset({"general"})` (nonpermutability) re-list construction names the
schema's `constructions:`/`known_constructions:` fields already enumerate,
apparently to scope which constructions `tests/test_snapshots.py` exercises.
**Where:** `planars/coreference.py:14,16`; `planars/nonpermutability.py:17`
**Authoritative source:** `schemas/diagnostic_classes.yaml` — `constructions:`
list per class (criterion fields for D-1b's first fact; construction names
for the snapshot-scoping fact)
**Classification:** derivable.

### D-1c. `_STRUCTURAL_COLS`/`_TRAILING_COLS`/`_STATUS_TAB`/`_KEYSTONE_NAME` re-declared again in `planars/reports.py` and `planars/coreference.py`/`nonpermutability.py` — no schema read at all, unlike the `coding/` copies
**What:** Unlike the `coding/` copies catalogued in D0/D3/D5 (which at least
attempt `load_planar_schema().get(...)` with a fallback), the `planars/`
copies are bare literals with no schema read whatsoever:
`planars/reports.py:440` (`_STRUCTURAL_COLS`), `:471` (`_TRAILING_COLS`),
`:474` (`_STATUS_TAB = "Status"`); `planars/coreference.py:10-11`
(`_KEYSTONE_NAME`, `_TRAILING_COLS`); `planars/nonpermutability.py:11-12`
(same). This raises the fallback-copy count from D0/D3/D5 to a fifth and
sixth independent declaration for several of these facts, now spanning both
packages (`coding/` and `planars/`) rather than just one.
**Where:** `planars/reports.py:440,471,474`; `planars/coreference.py:10-11`;
`planars/nonpermutability.py:11-12`
**Authoritative source:** `schemas/planar.yaml` — `structural_columns`,
`trailing_columns`, `keystone_position_name`; tab-name convention has no
schema source at all (see R3).
**Classification:** derivable (for the planar.yaml-backed facts); the
`_STATUS_TAB` copy inherits R3's must-declare status since no schema owns
it yet.

### D0. The keystone position name `"v:verbstem"` is hardcoded as a raw literal in at least 15 places across 9 files — including two `planars/` analysis modules
**What:** `schemas/planar.yaml` declares `keystone_position_name: "v:verbstem"`
as authoritative and states in its own comment that it is "Used by
`validate_planar.py`, `validate_coding.py`, and `planars/io.py`" — implying
those are the readers. In fact: `validate_coding.py` and several spots in
`generate_sheets.py` *do* read it via `load_planar_schema().get(
"keystone_position_name", "v:verbstem")` (see D5), but the literal string
`"v:verbstem"` is *also* hardcoded directly, bypassing the schema read
entirely, in:
  - `coding/check_codebook.py:138,278,305,312` (test/fixture construction)
  - `coding/generate_sheets.py:284,356` — in the **same file** that reads the
    schema value elsewhere (an internal inconsistency, not just a cross-file
    one)
  - `coding/import_sheets.py:565,572,998`
  - `coding/make_forms.py:281` (`keystone_name = "v:verbstem"`)
  - `coding/restructure_sheets.py:299`
  - `coding/update_sheets.py:132,263`
  - `coding/sync_params.py:245`
  - `planars/coreference.py:10` (`_KEYSTONE_NAME = "v:verbstem"`, a
    module-level constant)
  - `planars/io.py:78` — **the file `planar.yaml`'s own comment names as a
    reader of the schema value does not actually read it** at this call site;
    it compares directly against the literal.
  - `planars/nonpermutability.py:11` (`_KEYSTONE_NAME = "v:verbstem"`, a
    module-level constant)
This is the single most widely-replicated fact found in this inventory. It
sits at the center of the entire analysis pipeline — "keystone row anchors
every span computation" is bedrock per `data-layer-design.md`'s own rate-of-
change taxonomy — yet the value that names it is duplicated further than any
faster-moving fact in this codebase, including inside two `planars/`
analysis modules that would need independent, manual updates if the
keystone convention ever changed for a new language shape.
**Where:** see list above.
**Authoritative source:** `schemas/planar.yaml:76` (`keystone_position_name`)
**Classification:** derivable — every one of these should read
`load_planar_schema().get("keystone_position_name")` (via `coding/schemas.py`
for `coding/`, and via `planars/io.py`'s existing schema-loading machinery
for `planars/`) instead of restating the literal.

### D2b. Nonpermutability's Zone/Slot pair-candidacy algorithm is implemented twice, in two packages
**What:** Unlike the rest of this inventory (a data *value* duplicated),
this is the same *algorithm* implemented independently twice: "two elements
are nonpermutability pair candidates if they share a Zone position, or are
not in strict fixed order, or are not both confined to identical Slot-only
positions" is written once in `coding/generate_sheets.py`'s
`_build_nonperm_pairs` (used to generate the Sheet's candidate pair rows)
and again in `planars/nonpermutability.py`'s
`structurally_expected_pair_elements` (used by `integrity_check.py` to
detect pair-row staleness). The second function's own docstring states the
relationship explicitly: *"An element is expected if it would be included
in at least one pair by `_build_nonperm_pairs`"* — i.e. the duplication is
self-aware, not accidental, exactly like D1's `restructure_sheets.py`
comment. A future change to the qualification logic (e.g. how Zone/Slot
adjacency is defined) requires editing both, in both packages, or the
staleness checker and the sheet generator silently disagree about which
pairs should exist.
**Where:** `coding/generate_sheets.py:409-473` (`_build_nonperm_pairs`);
`planars/nonpermutability.py:96-124` (`structurally_expected_pair_elements`)
**Authoritative source:** `schemas/diagnostic_classes.yaml`'s
`nonpermutability` `qualification_rule` describes the Slot/Zone logic in
prose (lines 253-283) but the pair-*candidacy* rule specifically (as
opposed to the qualifying-span rule) is not separately codified there —
both code copies derive it independently from the same prose.
**Classification:** must-declare in the sense that the algorithm itself
needs a single home (a shared function in `planars/nonpermutability.py`
that `coding/generate_sheets.py` imports, rather than two schema-reading
call sites) rather than a new YAML field — flagged here because it is a
duplication of logic, not just of a value, and the fix path differs from
the rest of this document's items accordingly.

### D1. The same coreference/nonpermutability criterion-override logic is independently re-implemented in THREE files, one copy already stale
**What:** The override "prescreening construction X uses hardcoded criterion Y
with hardcoded values Z" logic exists as three separate, independently
maintained implementations:
  - `coding/validate_coding.py:53-62` — `_build_coreference_params()`
  - `coding/generate_sheets.py:1489-1494,1823-1838,1921` (three call sites)
  - `coding/restructure_sheets.py:1081-1105` — whose own comment reads
    *"Mirror the special-case criterion overrides from generate_sheets.py so
    that restructure produces the same param_names/param_values as initial
    generation"* — i.e. the duplication is not accidental, it is
    **acknowledged in-line** as a manually-maintained mirror, which is
    exactly the failure mode `data-layer-design.md` identifies as structural
    rather than incidental.
All three hardcode `{"referential": ["y","n"]}` for coreference's
`prescreening`, and `{crit: ["y","n"]}` (or a `pv.get(crit, ["y","n"])`
fallback) for `reflexive_allowed`/`pronoun_allowed`/`np_allowed` — but
`schemas/diagnostic_criteria.yaml` defines those three criteria as
`[y, n, untestable]`, not `[y, n]`. None of the three copies read that value
list; all three would independently reject (or silently mis-validate)
`untestable`, a value the schema explicitly permits. Because there are three
copies, fixing one (e.g. `validate_coding.py`) would not fix the others —
exactly the scenario the design doc's `_get_pair_row_constructions()`
precedent was meant to replace project-wide.
**A fourth copy makes this actively dangerous rather than just untidy:**
`coding/refresh_dropdowns.py`'s `_fresh_param_values()` — whose docstring is
literally *"Use this when criterion allowed-value lists change... existing
sheets need their dropdowns updated"* — has the identical override branches
(`{"scopal": ["y","n","both"]}`, `{"referential": ["y","n"]}`, and
`class_criteria.get(crit, ["y","n"])` for the pair criteria). This is the
one tool in the entire project whose sole purpose is propagating a
criterion's updated allowed-value list to live Sheets, and it is one of the
four places that would need a coordinator to remember to hand-edit if
`reflexive_allowed`'s value list ever changed — the override branches
shadow the "standard case" a few lines below that *does* read
`class_criteria` correctly.
**Where:** `coding/validate_coding.py:53-62`; `coding/generate_sheets.py:1489-1494,1823-1838,1921,1955`; `coding/restructure_sheets.py:1081-1105`; `coding/refresh_dropdowns.py:27-57`
**Authoritative source:** `schemas/diagnostic_criteria.yaml` — `referential`
(line 536, `[y, n]`), `reflexive_allowed`/`pronoun_allowed`/`np_allowed`
(lines 544-560, all `[y, n, untestable]`), `scopal` (`[y,n,both]`)
**Classification:** derivable — should call `load_diagnostic_criteria()` and
look up each criterion's `values` list once, in one place, instead of being
hand-copied into four files.

### D2. Coreference/phrasal_accent/element_prescreening default value-list overrides re-encode schema values as literals
**What:** Multiple call sites build `param_values` dicts with inline literal
value lists instead of reading them: `{"scopal": ["y","n"]}` (nonpermutability
pairs), `{"accented": ["y","n","both"]}` (three call sites), `{"joint_accent":
["always","sometimes","never"]}`. These happen to currently match the schema,
but are a second, independent statement of the same fact with no mechanism
tying them together.
**Where:** `coding/generate_sheets.py:1489-1494`, `:1539`, `:1834-1835`,
`:1921`, `:1955`; `coding/validate_coding.py` (see D1)
**Authoritative source:** `schemas/diagnostic_criteria.yaml` — `scopal`
(`[y,n,both]`), `accented` (`[y,n,both]`), `joint_accent`
(`[always,sometimes,never]`)
**Classification:** derivable.

### D3. `_STRUCTURAL_COLS` re-lists a subset of `planar.yaml`'s structural columns
**What:** `_STRUCTURAL_COLS = {"Element", "Position_Name", "Position_Number"}`
is a hardcoded set duplicating three of the five entries in
`structural_columns` (the other two, `Element_Types` and `Biuniqueness_Scope`,
are newer and not yet part of every filled TSV — see planar.yaml's own
"NOT YET BACKFILLED" notes). Because this is a hand-picked subset rather than
a derived one, a newly-backfilled structural column added to real TSVs would
need this set edited by hand to avoid being misclassified as a criterion
column.
**Where:** `coding/validate_coding.py:46`; independently re-declared,
byte-identical, at `coding/restructure_sheets.py:115`; folded into a combined
structural+pair-structural set at `coding/sync_params.py:64-65`
(`_STRUCTURAL_SET`, which merges this fact with D4's fact into one set,
making it a fourth independent copy of the union); also `planars/io.py:15` —
notable because this is the shared loader every `planars/` analysis module
calls (`load_filled_tsv`/`load_filled_sheet`), and it sits **one line above**
`_TRAILING_COLS = set(_planar_schema.get("trailing_columns", ...))` (line
16), which *does* read the schema it already loaded into `_planar_schema` at
line 14 — i.e. the correct pattern and the hardcoded copy are adjacent
lines in the same file, one of them just wasn't updated to match.
**Authoritative source:** `schemas/planar.yaml` `structural_columns` (lines 23-72)
**Classification:** derivable.

### D4. Pair-row structural columns declared independently in two files, two different shapes
**What:** `validate_coding.py` declares `_PAIR_STRUCTURAL_COLS = {"Element_A",
"Element_B", "Position_A", "Position_B", "Direction"}` (a single set covering
both nonpermutability-style and coreference-style pair rows). `generate_sheets.py`
separately declares the coreference-style header as an ordered list,
`_REFLEX_STRUCT = ["Element_A", "Position_A", "Position_B", "Direction"]`
(line 961), and inlines the nonpermutability-style header as a literal
`["Element_A", "Element_B"]` (line 929). None of these three are read from a
shared source; `schemas/planar.yaml` documents only the non-pair-row
structural columns and is silent on pair-row shape entirely (see M-series
below for the "no authoritative source at all" angle on this same fact).
**Where:** `coding/validate_coding.py:47`; `coding/generate_sheets.py:929,961`;
a *third* independent declaration in `coding/restructure_sheets.py:395,459`
(`_PAIR_POS_COLS = ("Position_A", "Position_B")`, `_PAIR_ELEMENT_COLS =
("Element_A", "Element_B")`); a fourth copy folded into the combined
`_STRUCTURAL_SET` at `coding/sync_params.py:64-65`; `_format_annotated_drop`
in `generate_sheets.py:1739-1746` and the `is_reflex_fmt` header sniff at
`generate_sheets.py:1809` both re-derive the same two-vs-four-column shape
distinction ad hoc from `class_name` rather than from any of the above.
`coding/import_sheets.py:55` is the one well-behaved case — it imports
`validate_coding._PAIR_STRUCTURAL_COLS` rather than re-declaring it.
**Authoritative source:** none yet — `planar.yaml`'s `structural_columns`
covers only Element/Position_Name/Position_Number-style tabs, not pair-row
tabs. This is the "no source exists, but four independent hardcodings
already disagree in shape/type (set vs. tuple vs. list) and duplicate each
other's content" case — flagged here rather than under Must-declare because
the risk is active (three copies), even though the fix is to *create* rather
than *point at* an authoritative source.
**Classification:** must-declare (new field needed in `planar.yaml`, e.g. a
`pair_row_structural_columns` entry per row shape), but the current
duplication across two files should be resolved as part of that.

### D5. `_TRAILING_COLS` / `_DEFAULT_EXPECTED` / `_KEYSTONE_NAME` fallback defaults re-embed the schema value they fall back from
**What:** Three separate constants read a schema value via
`load_planar_schema()`/`load_diagnostic_criteria()` but supply a **hardcoded
literal fallback** that duplicates the current schema value: `_TRAILING_COLS
= load_planar_schema().get("trailing_columns", ["Source", "Comments"])`,
`_DEFAULT_EXPECTED = set(load_diagnostic_criteria().get("default_allowed_values",
["y", "n", "na", "?"]))`, `_KEYSTONE_NAME = load_planar_schema().get(
"keystone_position_name", "v:verbstem")`. If the schema value ever changes,
these fallbacks silently keep the *old* value alive for any caller that hits
the fallback path (e.g. a schema load failure), rather than failing loudly.
**Where:** `coding/validate_coding.py:48-49,70`; `coding/generate_sheets.py:114`
and repeated inline at `:433,600,748,826` (`load_planar_schema().get(
"keystone_position_name", "v:verbstem")`, four separate call sites each with
its own copy of the same fallback literal)
**Authoritative source:** `schemas/planar.yaml` — `trailing_columns` (line 81),
`keystone_position_name` (line 76); `schemas/diagnostic_criteria.yaml` —
`default_allowed_values`
**Classification:** derivable — the read-with-fallback pattern is reasonable,
but the fallback literal should be eliminated (raise/error if the schema key
is missing) rather than silently re-asserting the current value as a second
copy.

### D6. `_POSITION_NUMBER_PLACEHOLDER` string literal must match a value embedded in `diagnostic_criteria.yaml`
**What:** `_POSITION_NUMBER_PLACEHOLDER = "<position_number>"` is a Python
string that must stay byte-identical to the placeholder value used inside
`diagnostic_criteria.yaml`'s `dependent-on-left`/`dependent-on-right` `values:
[na, "<position_number>"]` entries (confirmed at
`schemas/diagnostic_criteria.yaml:287-299`). Nothing ties the two together —
a rename of the placeholder convention in the YAML silently breaks the
`accepts_pos_num` check in `validate_coding.py` with no error, just silently
wrong validation.
**Where:** `coding/validate_coding.py:65`
**Authoritative source:** `schemas/diagnostic_criteria.yaml` (the placeholder
string appears as a literal value inside `dependent-on-left`/`dependent-on-right`)
**Classification:** derivable — should be a named constant defined once
(e.g. in `schemas/__init__.py` or read structurally rather than compared as
a magic string) and imported, not re-typed.

---

### D7. `_ADAM_EMAIL` hardcoded independently in two files, duplicating `languages.yaml`'s `annotator_email`
**What:** `generate_biuniqueness_stage1_sheet.py` and `generate_status_sheet.py`
each declare their own `_ADAM_EMAIL = "adamjamesrosstallman@gmail.com"`
constant to share/permission generated sheets. `schemas/languages.yaml`
already stores this exact value structurally, per-language, as
`annotator_email` (confirmed for `arao1248` and `stan1293`, lines 37 and 54).
Both scripts' own docstrings acknowledge they're bypassing the normal lookup
(`_annotator_email()`) because the sheets they generate are project-wide
(status sheet) or `synth0001`-only (biuniqueness stage 1, a synthetic
language with no `languages.yaml` entry at all) rather than tied to one
onboarded language — so this may be a deliberate exception rather than an
oversight, but it is still two independent copies of a value one schema file
already owns for every other consumer in the project.
**Where:** `coding/generate_biuniqueness_stage1_sheet.py:73`;
`coding/generate_status_sheet.py:78`
**Authoritative source:** `schemas/languages.yaml` — `annotator_email`
(e.g. lines 37, 54)
**Classification:** derivable, with a caveat — a clean derivation needs a
"default reviewer" concept distinct from "this language's annotator" (since
neither of these two sheets is scoped to a single onboarded language), which
doesn't exist in `languages.yaml` today. Worth a schema field (e.g. a
top-level `default_reviewer_email`) rather than two more hardcoded copies.

### D8. `_CLASS_DISPLAY_NAMES` re-encodes `diagnostic_classes.yaml`'s `display_name` field, already stale for two classes
**What:** `generate_notebooks.py` hardcodes a 15-entry `{class_name:
display_name}` dict for notebook section headers, with a comment stating it
"Covers all classes in diagnostic_classes.yaml." It does not: `coreference`
and `phrasal_accent` (and `metrical`, `tonal`, `tonosegmental`,
`intonational`) are absent. For most of the missing classes the
title-case fallback happens to reproduce the schema's `display_name` by
coincidence (`"metrical"` → `"Metrical"` matches), but not for
`phrasal_accent`: the fallback produces `"Phrasal Accent"`, while
`diagnostic_classes.yaml`'s actual `display_name` for that class is
`"Phrasal (Pitch) Accent Grouping"` (line 613). This is a live, observable
drift caused directly by the duplication, not a hypothetical one.
**Where:** `coding/generate_notebooks.py:58-77`
**Authoritative source:** `schemas/diagnostic_classes.yaml` — every class
entry's `display_name:` field (e.g. line 613 for `phrasal_accent`, line 295
for `coreference`)
**Classification:** derivable — should read `display_name` from
`load_diagnostic_classes()` per class, with the title-case logic kept only
as the true last-resort fallback for a class that somehow has no
`display_name` at all.

## Derivable (no authoritative source yet, but one could plausibly own this fact)

### R-1. `planars/cli.py`'s `_ANALYSES` registry is hand-maintained and already stale — two fully-wired modules are unreachable via the CLI
**What:** `_ANALYSES` hardcodes fifteen `{name: (derive_fn, format_result)}`
entries. `planars/coreference.py` and `planars/metrical.py` both follow the
project's own documented convention exactly (a `derive = derive_X_domains`
alias plus `format_result`, per `planars/CLAUDE.md`) and are actively used
elsewhere (e.g. `check_codebook.py`'s chart-key self-test imports and runs
`metrical` directly) — but neither appears in `_ANALYSES`, so `python -m
planars coreference <tsv>` and `python -m planars metrical <tsv>` are simply
unavailable, silently, with no error pointing at why. `tonal`,
`tonosegmental`, `intonational`, and `phrasal_accent`'s eventual module are
likewise absent (the first three exist as files; `phrasal_accent` has none
yet by design, see `diagnostic_classes.yaml:682-684`).
**Where:** `planars/cli.py:33-65`
**Authoritative source:** none structural today — the fact "which modules
expose `derive`/`format_result`" is discoverable by introspection (every
module already follows the convention), which is exactly what
`data-layer-implementation-plan.md`'s Phase 5 ("Generate the mechanical
registry from signatures... never hand-authored") is scoped to build.
**Classification:** derivable — flagged here explicitly as a concrete,
already-broken instance of the general problem Phase 5 is designed to solve,
not a new category of fact.

### R-2. The `synth` reserved-prefix convention is hardcoded as a literal four times, with no schema declaration
**What:** `CLAUDE.md` documents that "Language IDs starting with `synth` are
a reserved prefix for synthetic test languages: they are exempt from
Glottocode format validation and Glottolog verification checks throughout
the tooling." The check itself — `lang_id.startswith("synth")` — is
re-typed as a literal in four call sites across two files rather than
defined once.
**Where:** `coding/glottolog.py:117`; `coding/validate_diagnostics.py:346,501,507`
**Authoritative source:** none structured — prose only, in `CLAUDE.md`.
**Classification:** derivable (a named constant/helper, e.g. `is_synthetic_lang_id(lang_id)`,
belongs in a shared module such as `coding/schemas.py` or `planars/languages.py`;
whether it further belongs in `schemas/languages.yaml` as a declared prefix
is a smaller question than simply not re-typing the string four times).

### R0. `diagnostics_{lang_id}.tsv`'s own required-column vocabulary is hardcoded, not schema-derived
**What:** `_REQUIRED_COLS = {"Class", "Language", "Constructions", "Criteria"}`
in `validate_diagnostics.py` declares the column shape of the derived
`diagnostics_{lang_id}.tsv` artifact. Nothing in `schemas/` declares this —
understandably, since this is the TSV format's own shape rather than a
per-language or per-class fact — but it is exactly the kind of "bedrock,
rarely-changes" structural fact `data-layer-design.md` says belongs in a
schema file rather than sitting only in the one validator that checks it.
**Where:** `coding/validate_diagnostics.py:61`
**Authoritative source:** none — closest candidate is `schemas/planar.yaml`,
which already owns the sibling fact `trailing_columns` for annotation TSVs;
`diagnostics_{lang_id}.tsv`'s own column shape has no equivalent entry.
**Classification:** derivable (once written).

### R1. "prescreening"-stage constructions never carry a structured `criterion` field
**What:** Every two-stage class (`nonpermutability`, `coreference`,
`phrasal_accent`) has a `constructions:` list where the *downstream* pair
construction has a structured `criterion:` field (e.g. `criterion: scopal`),
but the upstream prescreening-stage construction (`element_prescreening`,
`prescreening`) never does — its criterion name (`scopal`, `referential`,
`accented` respectively) exists only in prose (`sheet_instructions`,
inline `#` comments). Code recovers the name by hardcoding it per class:
`"scopal"` (nonpermutability), `"referential"` (coreference), `"accented"`
(phrasal_accent). This is a systematic gap, not three independent ones — the
same field is simply missing from the same construction shape three times.
**Where:** `coding/generate_sheets.py:500` (`group["scopal"]`), `:577`
(`row.get("scopal", "")`); `:672,676` (`row.get("referential", "")`); `:840`
(`row.get("accented", "")`); `coding/validate_coding.py:55` (hardcoded
`"referential"` key in `_build_coreference_params`); a fifth site,
`coding/integrity_check.py:656-662`, whose own comment states the problem
exactly: *"For coreference, prescreening uses 'referential', not the
class-level required_criteria (reflexive_allowed etc.)"* — i.e. the code
comment is independently re-deriving, in prose, the exact schema gap this
entry documents.
**Authoritative source:** partial — `schemas/diagnostic_criteria.yaml`
already defines the *value lists* for `scopal`/`referential`/`accented` (see
D1/D2), but `schemas/diagnostic_classes.yaml`'s `constructions:` entries for
`element_prescreening`/`prescreening` (nonpermutability line 228-229,
coreference line 319, phrasal_accent line 644-645) have no `criterion:`
field naming which criterion the prescreening stage uses.
**Classification:** derivable — add `criterion:` to each prescreening-stage
construction entry, matching the pattern already used one level down.

### R2. Two undocumented cross-class dependencies mirror the one pattern `facts.yaml` tracks, but aren't in it
**What:** `data_dependency_schema/facts.yaml`'s `dependent_construction_element_scope`
record documents the "prescreening → pair construction" dependency shape
(nonpermutability, coreference) but two more cross-*class* dependencies of the
same general kind exist in code and are undocumented in the registry:
  - `free_occurrence`'s `free` criterion is pre-filled at sheet-generation time
    by reading `coded_data/{lang}/noninterruption/general.tsv`'s `free`
    column (`free=y` rows get every free_occurrence annotation column forced
    to `na`; `free=n` rows are left blank for annotation).
  - `phrasal_accent`'s pair candidate list is gated by reading
    `coded_data/{lang}/free_occurrence/general.tsv`'s keystone row (`free`,
    `dependent-on-left`, `dependent-on-right`) to compute an "obligatory
    core" of positions that always block adjacency.
Both are documented in prose (a `diagnostic_classes.yaml` comment for the
first; a long docstring for the second) but neither is in the structured
registry that exists specifically to catalog this class of fact, so nothing
would flag it if e.g. `noninterruption`'s `general.tsv` path or `free`
column name changed.
**Where:** `coding/generate_sheets.py:295-336` (`_prefill_free_occurrence_rows`,
path at line 312); `:718-763` (`_phrasal_accent_obligatory_core`, path at
line 736)
**Authoritative source:** prose only — `schemas/diagnostic_classes.yaml:401`
(one-line comment) for the first; nothing for the second beyond the
docstring in `generate_sheets.py` itself.
**Classification:** derivable — same shape as the existing
`dependent_construction_element_scope` record; should be added to
`data_dependency_schema/facts.yaml` as sibling records (or a generalized
single record covering all three "construction X reads construction Y's
TSV at generation time" cases: nonpermutability, coreference, free_occurrence,
phrasal_accent).

### R3. Status tab values and "Status" tab/column naming
**What:** The two valid values a construction's workflow status can take
(`in-progress`, `ready-for-review`) are hardcoded as `_STATUS_VALUES` and as
inline literal defaults (`"in-progress"` appears as a literal twice more at
sheet-creation time). The same two values are referenced constantly in prose
throughout `diagnostic_classes.yaml`'s `sheet_instructions` fields ("mark
prescreening as 'ready-for-review' in the Status tab") and are checked
against in `import_sheets.py`'s import-behavior-by-status logic (see that
file's section below), but no schema file declares them as a value set.
**Where:** `coding/generate_sheets.py:116` (`_STATUS_VALUES`), `:1194,1200`
(literal `"in-progress"`); tab-name constants `_STATUS_TAB="Status"`,
`_INSTRUCTIONS_TAB="Instructions"`, `_PLANAR_REF_TAB="Planar Structure"`,
`_SYSTEM_TAB_ORDER` at `:115-120`, re-imported into
`coding/validate_coding.py:29` and compared against there
**Authoritative source:** none structured — only recoverable from reading
prose across `diagnostic_classes.yaml`'s `sheet_instructions` strings.
**Classification:** derivable — belongs in `schemas/planar.yaml` (or a new
small "sheet workflow" schema) alongside `trailing_columns` and
`keystone_position_name`, which already play this role for other sheet-shape
facts.

### R5. Per-class pair-row dispatch table hardcoded as a 3-way `if class_name == ...` chain
**What:** `_regen_construction` (and its helpers `_format_annotated_drop`,
`_populate_tab_pairs`/`_populate_tab_reflex_pairs` selection,
`_remap_coreference_prefill` gating) determines, purely from `class_name ==
"coreference"` / `== "phrasal_accent"` / else-nonpermutability: which pair-row
shape to use (2-col `Element_A,Element_B` vs 4-col
`Element_A,Position_A,Position_B,Direction`), which default criterion name
and default value list to fall back to if the manifest lacks
`construction_params`, and which pair-generation function to call
(`_build_reflex_pairs`/`_build_phrasal_accent_pairs`/`_build_nonperm_pairs`).
This is a hardcoded `{class_name: (row_shape, default_criterion,
default_values, builder_fn)}` table expressed as control flow rather than
data — a fourth two-stage class would require editing this function (and
`_format_annotated_drop`, and `validate_coding.py`'s parallel
`_COREFERENCE_CONSTRUCTION_PARAMS`/`class_name == "coreference"` check) rather
than being picked up from `row_type: pair_rows` in the schema the way
`_get_pair_row_constructions()` already does for the simpler "is this a
pair-row tab at all" question.
**Where:** `coding/generate_sheets.py:1809` (`is_reflex_fmt` header sniff),
`:1823-1838` (the 3-way param default dispatch, including the further magic
default `_pair_crit.get(construction_name, "reflexive_allowed")` at line
1830), `:1846-1853` (builder dispatch), `:1857,1860-1864` (key-shape
dispatch), `:1739-1746` (`_format_annotated_drop`'s identical dispatch);
`coding/validate_coding.py:54-59,565` (the same class-name special-casing,
independently re-derived)
**Authoritative source:** partial — `schemas/diagnostic_classes.yaml`'s
`row_type: pair_rows` per construction already distinguishes pair-row from
element-row tabs generically (this is what `_get_pair_row_constructions()`
reads), but nothing distinguishes the *2-column* pair-row shape
(nonpermutability) from the *4-column position-keyed* shape (coreference) —
that finer distinction is exactly what's hardcoded here.
**Classification:** derivable — the finer row-shape distinction belongs in
`diagnostic_classes.yaml` as a field on each pair-row construction (e.g.
`pair_row_shape: element_pair | position_pair`), from which every one of
these call sites could dispatch generically instead of naming classes.

### R4. Hardcoded pair-row prescreening file paths (`{lang}/{class}/{construction}.tsv`)
**What:** Each two-stage class's prescreening TSV path is built as a raw
f-string/`Path` join rather than through any shared path-builder:
`CODED_DATA / lang_id / "nonpermutability" / "element_prescreening.tsv"`,
`CODED_DATA / lang_id / "coreference" / "prescreening.tsv"`,
`CODED_DATA / lang_id / "phrasal_accent" / "prescreening.tsv"`,
`CODED_DATA / lang_id / "free_occurrence" / "general.tsv"`,
`CODED_DATA / lang_id / "noninterruption" / "general.tsv"`. The
`{lang}/{class}/{construction}.tsv` convention itself is documented in
`CLAUDE.md` prose ("File naming...") but there is no single function in the
codebase that builds this path from a `(lang_id, class_name, construction)`
triple — every call site re-derives it, and the class/construction name
segments are literal strings at each site rather than read from
`diagnostic_classes.yaml`'s own `name:` fields.
**Where:** `coding/generate_sheets.py:488,659,736,828` (this cluster alone);
the same `CODED_DATA / lang_id / class_name / f"{construction}.tsv"` shape
recurs roughly 50+ times across `coding/*.py` (`validate_coding.py`,
`import_sheets.py`, `restructure_sheets.py`, `sync_params.py`,
`integrity_check.py`, `refresh_dropdowns.py`, `generate_status_sheet.py`,
`check_codebook.py`, `generate_notebooks.py`) — not itemized individually
here since the pattern, not any single occurrence, is the fact.
**Authoritative source:** none — a path-builder function does not exist.
**Classification:** derivable — a single `coded_tsv_path(lang_id, class_name,
construction)` helper (e.g. in `coding/schemas.py` or `make_forms.py`) would
let every call site derive the path instead of restating the convention.

---

## Must-declare (genuinely not derivable from any plausible schema source)

### M1. `_OBLIGATORY_POSITIONS_DEFAULT` — a linguistic judgment call hardcoded as a global constant
**What:** `_OBLIGATORY_POSITIONS_DEFAULT = {"v:verbstem", "v:npsubj1"}` is
"tier 2" of phrasal_accent's obligatory-position algorithm: positions treated
as always-present (never elidable) when deciding candidate accent pairs. The
code's own comment calls this out explicitly: "THIS IS A FIRST GUESS, NOT A
VALIDATED COORDINATOR DECISION... lifted directly from issue #237's original
tentative example set... expected to need per-language correction." This is
a real linguistic claim about specific languages, is not derivable from any
existing structural fact, is currently **global** (one constant for every
language) despite the comment's own admission that it should vary per
language, and directly determines what pairs get generated for annotation.
**Where:** `coding/generate_sheets.py:700-715`
**Authoritative source:** none.
**Classification:** must-declare — and should be per-language, not global.
The comment already flags this as the most fragile fact in the file; it is
the clearest candidate in this inventory for "authority nobody has assigned
yet," on par with the incidents in `data-layer-design.md`'s table.

### M-misc. Archive timestamp format hardcoded identically (and inconsistently) in three files
**What:** The archive-filename timestamp format `"%Y%m%d_%H%M%S"` is a
hardcoded literal independently repeated in three files, each also calling a
*different* time source: `datetime.now(timezone.utc)` (aware UTC),
`datetime.now()` (naive local), and `datetime.utcnow()` (naive UTC,
deprecated in current Python). Not itself a schema fact, but the same
"nobody owns this" shape as the rest of the inventory, so recorded here for
completeness rather than fixed.
**Where:** `coding/import_planar.py:153`; `coding/import_sheets.py:835`;
`coding/prune_manifest.py:222`
**Authoritative source:** none.
**Classification:** must-declare (or, more precisely, "should be a shared
helper function," which is a lighter-weight fix than a schema field —
flagged for Phase 3/5's attention rather than treated as a schema gap).

### M0. `Position_Type` (`Zone`/`Slot`) is a load-bearing structural column entirely absent from `planar.yaml`'s own `structural_columns`
**What:** Every filled planar TSV carries a `Position_Type` column whose only
valid values are `Zone`/`Slot` (`_VALID_POSITION_TYPES = {"Zone", "Slot"}` in
`validate_planar.py`). This column is not a minor detail — it is directly
load-bearing for the nonpermutability qualification rule's structural (no-
annotation-required) span ("A position qualifies iff: (1) It is a Slot
(Zones are always excluded)...", `diagnostic_classes.yaml:257-264`) and for
`generate_sheets.py`'s pair-candidate generation (`_build_nonperm_pairs`,
`_build_phrasal_accent_pairs` both branch on `pos_type.get(p) == "Zone"`).
Yet `schemas/planar.yaml`'s `structural_columns` section — which documents
itself as covering every column "present in every filled TSV" and
explicitly lists `Element`, `Position_Name`, `Position_Number`,
`Element_Types`, `Biuniqueness_Scope` — has no entry for `Position_Type` at
all. This is the one finding in this inventory where the gap is in the
*authoritative source itself*, not just in code that fails to read it: even
a maximally schema-driven rewrite of every caller would still have nowhere
to point, because `planar.yaml` doesn't yet claim this fact.
**Where:** `coding/validate_planar.py:20` (closest thing to an authoritative
definition, and it's in code); consumed throughout
`coding/generate_sheets.py` (`_read_position_types`, `_build_nonperm_pairs`,
`_build_phrasal_accent_pairs`) and implicitly by
`planars/nonpermutability.py`'s qualification logic.
**Authoritative source:** none — this is the gap, not a duplication.
**Classification:** must-declare — `schemas/planar.yaml`'s
`structural_columns` list should gain a `Position_Type` entry alongside
`Element`/`Position_Name`/`Position_Number`. Recorded first in this section
as the highest-priority must-declare item: everything else in this document
at least has *somewhere* to point a fixer at; this one requires writing the
schema fact for the first time.

### M4. `import-sheets`' 10%-decrease `collaborator-check` threshold
**What:** `decrease > 0.10` is the hardcoded threshold at which an
in-progress tab's annotated-cell decrease triggers a `collaborator-check`
GitHub issue rather than being silently accepted. Documented in `CLAUDE.md`
prose (the `collaborator-check` label table entry) and matches the code, but
is a bare literal with no named constant, let alone a schema source — a
policy threshold, not a linguistic fact, so there is no plausible schema
file for it; recorded here as the "policy constant with no home at all"
case.
**Where:** `coding/import_sheets.py:592` (`_STATUS_VALUES`-adjacent status
default fallback `"in-progress"` also appears here at line 894, the same
fact as R3)
**Authoritative source:** none — prose only (`CLAUDE.md`'s label table).
**Classification:** must-declare (as a named constant at minimum; a genuine
schema field only if the threshold should ever vary by class/language).

### M3. Biuniqueness Stage 1 sheet column vocabulary and value semantics
**What:** `_HEADER = ["Position_Name", "Element", "Biuniqueness_Scope",
"has_allomorphs", "Members", "Notes"]` and the value semantics "scope ==
'filled' → fill `has_allomorphs`; scope == 'open_category' → fill `Members`"
are hardcoded in one file. This is by design, per the module's own
docstring: it is "Deliberately NOT routed through the standard
`diagnostics_{lang_id}.yaml` / `generate_sheets.py` class/construction
pipeline" because its rows are Element-keyed lexicon facts, not
Position-keyed criteria with a `qualification_rule`. So there genuinely is
no natural home in `diagnostic_classes.yaml` for this shape today — flagged
as must-declare rather than derivable specifically because forcing it into
the existing per-class schema would misrepresent what kind of fact it is
(exactly the "resistant field" pattern Phase 3 is told to watch for, one
level up: an entire *sheet*, not just a field, that doesn't fit the existing
taxonomy).
**Where:** `coding/generate_biuniqueness_stage1_sheet.py:74-75,107-109`
**Authoritative source:** `Biuniqueness_Scope`'s three values
(`filled`/`open_category`/`excluded`) are defined in `schemas/planar.yaml`
(lines 56-72) — so the *scope* vocabulary is already owned there. Only the
Stage 1 sheet's own column names and the scope→column-to-fill mapping are
undeclared.
**Classification:** must-declare — but note it for Phase 3's "resistant
field" catalog as a candidate for a future non-diagnostic-class schema
section (e.g. a `lexicon_screening` shape), not a fix to shoehorn into
`diagnostic_classes.yaml`.

### M2. `pending_changes.json` path and semantics
**What:** `ROOT / "pending_changes.json"` — the repo-root state file that
`import-sheets` writes destructive changes to and `apply-pending` reads —
is a hardcoded path/filename. Its shape (what counts as "destructive," what
`apply-pending` expects to find in it) is documented only in code and
`CLAUDE.md` prose.
**Where:** `coding/validate_coding.py:646` (one read site among several
across the codebase — `apply_pending.py`, `import_sheets.py` own the
read/write pair)
**Authoritative source:** none — this is a workflow/state-file convention,
not a linguistic or structural fact. Lower priority than the criterion/
class-name items above precisely because it is inherently a file-path
convention rather than a fact with a plausible YAML home.
**Classification:** must-declare (if declared anywhere, belongs in
`data_dependency_schema/` as a precondition/state-file record, not in
`schemas/`).
