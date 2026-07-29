# Data Dependency Schema

A small, machine-validatable pair of schemas for documenting planars' data-
dependency graph: the same fact — a language's positional structure, which
elements are in diagnostic scope, a qualification rule's semantics — often
ends up recorded in more than one place: a live Google Sheet, a local TSV, a
YAML schema file, a code comment, a Drive-ID manifest, even a GitHub issue's
comment history. Nothing in the codebase writes down, in one place, which
copy is authoritative and how a change to one should (or shouldn't) reach the
others.

Left undocumented, this surfaces as a bug rather than a design decision. On
2026-07-29, a locally-edited `planar_{lang_id}.tsv` was never pushed back to
its master Google Sheet — because nothing tracked that this was now a
dependency in need of a cascade path. The next scheduled sync treated the
Sheet as authoritative (correctly, by its own contract) and silently
*reverted* the local edit, which cascaded into three more issues before it
was caught (#244, #245, #248). This schema exists to let that relationship be
written down explicitly, once, so it can be checked by inspection — or
validated automatically — instead of rediscovered by incident.

## Two kinds of dependency, two schemas

Investigating that incident surfaced two genuinely different classes of
dependency, and one schema doesn't fit both cleanly:

1. **The same fact, recorded in more than one place** (`fact_record.schema.json`
   / `facts.yaml`). This is the classic case: a planar structure exists as
   both a live Sheet and a local TSV; a diagnostics scope exists as YAML, TSV,
   *and* Sheet. The question is always the same three-part shape: where does
   it live, which copy wins, how does a change cascade.

2. **A shared precondition several commands assume, but which isn't a copy of
   anything** (`precondition_record.schema.json` / `preconditions.yaml`).
   `coded_data/` must be a clean git tree before `update-sheets --apply` (or
   `sync-params`, or `import-sheets`, or `generate-sheets --regen-dependents`)
   touches it. That's not a *fact* duplicated across locations — it's an
   invariant several unrelated commands each independently assume, with no
   single place declaring the dependency. Forcing this into `locations`/
   `authoritative`/`cascade` would misrepresent it (there's no "other copy"
   to cascade to) and bury the actually useful information: which commands
   share the assumption, and what currently checks it.

Both schemas are deliberately small, both are validated against real JSON
Schema files, and both are populated with real, current planars facts and
preconditions — not a smoke-test sample. `facts.yaml`/`preconditions.yaml`
*are* the registry; keep them accurate as the project changes.

## Entity vocabulary (facts only — preconditions don't use one)

Every `locations` entry in a fact record names an **entity** — the kind of
place the fact is recorded. There are fifteen, reusing exactly the names
already established in `CLAUDE.md` and `coding/CLAUDE.md` rather than
inventing new terminology:

| Entity | Description |
|---|---|
| `planar_sheet` | The live Drive spreadsheet defining one language's positions/elements (`planar_spreadsheet_id`). Can be authoritative — hand-edited by the coordinator, or (since #248) receiving an automated push from a locally-edited `planar_tsv`. |
| `diagnostics_sheet` | The live Drive spreadsheet mirroring `diagnostics_{lang_id}.yaml`/`.tsv`. Always derived — never itself authoritative. |
| `annotation_sheet` | A live Drive spreadsheet for one analysis class (one tab per construction), where annotators enter judgments. The primary source for annotation data. |
| `status_sheet` | Locked, read-only per-language completion-status spreadsheet. Always derived — never authoritative for anything. |
| `collaborator_doc` | The per-language Google Doc for free-text collaborator notes; change-tracked via `notes_state.json` content hashes. |
| `planar_tsv` | `coded_data/{lang}/lang_setup/planar_{lang_id}.tsv`. Normally downloaded from `planar_sheet` — but sometimes a direct edit point too (the one entity where the default cascade direction is genuinely ambiguous, not clean). |
| `diagnostics_yaml` | `coded_data/{lang}/lang_setup/diagnostics_{lang_id}.yaml` — the coordinator-facing source of truth for a language's diagnostics scope. |
| `diagnostics_tsv` | `coded_data/{lang}/lang_setup/diagnostics_{lang_id}.tsv` — always regenerated from `diagnostics_yaml`; documented as never hand-edited. |
| `construction_tsv` | `coded_data/{lang}/{class}/{construction}.tsv` — the local mirror of one construction's annotation data, imported from `annotation_sheet`. |
| `schema_yaml` | One of the five project-wide `schemas/*.yaml` files (`diagnostic_classes`, `diagnostic_criteria`, `planar`, `terms`, `languages`) — hand-edited, normative, rarely regenerated. |
| `derived_artifact` | Any regenerated, don't-hand-edit output: notebooks, PDF reports, rendered codebook markdown, `tests/snapshots/` baselines. |
| `manifest` | `sheets_manifest.json` / `drive_config.json` — the Drive-ID bookkeeping registry mapping languages/classes to spreadsheet/folder/doc IDs. |
| `code_comment` | A fact encoded as a docstring or inline comment in a `planars/*.py` or `coding/*.py` module — e.g. a qualification rule's prose description, whose sync with the schema is checked via a hash sentinel. |
| `github_issue` | A GitHub issue used as a durable coordination/state channel — per-language notification issues, `pending-changes` tracking, drift issues. The fact's truth value literally lives in the issue's open/closed state or comment history. |
| `filename_convention` | A fact encoded implicitly in a naming pattern — e.g. a language ID inferred from `planar_{lang_id}.tsv`; an archive file's datestamp suffix encoding when it was superseded. |

### Why some of these are split rather than consolidated

The four Sheet entities (`planar_sheet`, `diagnostics_sheet`,
`annotation_sheet`, `status_sheet`) could have been one generic `drive_sheet`
with a `detail` string distinguishing which. They aren't, because they differ
in whether they can *ever* be authoritative — `planar_sheet`/`annotation_sheet`
sometimes can be; `diagnostics_sheet`/`status_sheet` never can. Naming that
directly in the entity means a reader sees "never authoritative" as a
structural fact of the vocabulary, not something inferred from free text
every time. The same logic splits the three local-TSV entities: `diagnostics_tsv`
has a hard documented rule (never hand-edited), `construction_tsv` is
normally download-only, and `planar_tsv` is the one that's genuinely
ambiguous — which is exactly the distinction that mattered on 2026-07-29.

`manifest`, `code_comment`, and `github_issue` each get their own entity
rather than folding into `derived_artifact`, because none of them are
actually "rebuild-from-source" outputs the way a notebook or snapshot is. The
manifest is a standalone pointer table nothing else can regenerate from
scratch if lost. Code comments are *manually* kept in sync by design (that's
the whole reason the qualification-rule hash sentinel exists). And a GitHub
issue's open/closed state and comment history don't mirror a fact recorded
elsewhere — they *are* the fact, for anything durably tracked via an issue.

## Fact record shape

```yaml
- id: planar_sheet_structure
  description: a language's positional/element structure (Position_Name/Elements columns)
  locations:
    - {entity: planar_sheet, detail: "the live planar spreadsheet for the language"}
    - {entity: planar_tsv, detail: "coded_data/{lang}/lang_setup/planar_{lang_id}.tsv"}
  authoritative: planar_sheet
  cascade:
    direction: bidirectional
    mechanism: import-planar (Sheet -> TSV) / import-planar --to-sheet (TSV -> Sheet), the latter auto-run by restructure-sheets --apply
  drift_risk:
    possible: true
    note: a local structural edit that skips restructure-sheets has no push path back to the Sheet
    caught_by: nothing yet beyond a manual import-planar dry run
```

Field by field — this shape and its semantics are unchanged from the
original `fact_record.schema.json`, only the entity enum is planars-specific:

- **`id`** — short, stable, snake_case; used to reference the fact elsewhere
  (commit messages, comments); should not change once established.
- **`description`** — a one-line, plain-language statement of the fact.
- **`locations`** — every place the fact is recorded, each a
  `{entity, detail}` pair. A fact can list the *same* entity twice (e.g. a
  source `construction_tsv` and a dependent `construction_tsv`) when two
  distinct files play the same structural role — see "Known limitations"
  below for the ambiguity that introduces.
- **`authoritative`** — which entity, among those in this record's own
  `locations`, wins when copies disagree.
- **`cascade.direction`** — `automatic` (a tool regenerates the
  non-authoritative copy), `manual` (a human must notice and propagate by
  hand), or `bidirectional` (edits can legitimately originate at either
  location — the shape most worth writing down, since it's the one that
  produces silent-overwrite bugs like #244 if the cascade path is missing or
  one-directional when it needs to be two).
- **`cascade.mechanism`** — the actual command/function, not a placeholder.
- **`drift_risk.possible`** — can the copies actually disagree in practice?
- **`drift_risk.note`** — how (or, if `possible: false`, why not).
- **`drift_risk.caught_by`** — required whenever `possible: true`. What
  actually catches drift: a named `integrity-check`/`check-codebook` section,
  a GitHub issue label, a human review step, or an honest `nothing yet`.
  Naming the gap explicitly is more useful than leaving it undocumented.

## Precondition record shape

```yaml
- id: coded_data_clean_tree
  description: coded_data/ has no uncommitted changes before a command reads/writes it as ground truth
  required_by:
    - "import_sheets.py (import-sheets --apply)"
    - "update_sheets.py (update-sheets --apply)"
  enforced_by: drive._check_coded_data_clean(), called at the top of each apply path above
  failure_symptom: a command reads a stale/reverted file as current and acts on it
  established: "2026-07-29, after the #248 stray-row incident"
  gap: (optional) a known, still-open weakness in enforcement
```

- **`required_by`** — every command that assumes the precondition holds. If a
  new command starts sharing the assumption, add it here *and* wire in the
  actual check named in `enforced_by` — the list existing is not itself
  protection.
- **`enforced_by`** — the concrete check, or an honest `nothing yet`.
- **`failure_symptom`** — what actually happens on violation, concrete enough
  that a future incident can be matched back to this record by its symptoms.
- **`established`** — optional but encouraged: when and why, so a future
  reader knows this wasn't always true.
- **`gap`** — optional. A known, still-open weakness in how the precondition
  is enforced. Used the same way `drift_risk.caught_by`'s `nothing yet` is
  used in fact records: naming a gap turns it into something trackable
  instead of something silently re-discovered. See `preconditions.yaml`'s
  `coded_data_git_identity_configured` record for a gap that was found and
  closed the same day it was first written down — writing down "only
  enforced by workflow step ordering" made a silently-swallowed commit
  failure inside `drive._autocommit_data()` visible enough to fix
  immediately.

## Known limitations

- Neither JSON Schema can mechanically enforce that a fact record's
  `authoritative` value is actually one of that same record's own
  `locations` entities — draft 2020-12 has no clean way to compare one
  field's value against a computed set derived from a sibling array field.
  Checked by convention/review, and by a belt-and-suspenders test in
  `tests/test_data_dependency_schema.py`.
- When a fact record lists the same entity twice under `locations` (e.g.
  `dependent_construction_element_scope`'s two `construction_tsv` entries),
  `authoritative: construction_tsv` alone doesn't say *which* one — the
  `detail` text has to carry that disambiguation. This is a real soft spot,
  not just a documentation nicety to remember; don't add a fact record with
  a repeated entity without making the `detail` fields say explicitly which
  one is meant.
- The precondition schema has no equivalent of `drift_risk.possible` — a
  precondition is either currently enforced or it isn't; there's no "might
  or might not be violated in practice" middle ground the way two data
  copies might or might not actually drift.

## How to use this for ongoing work

1. **When you find a bug that traces back to an undocumented authority/cascade
   relationship**, write the fact record (or precondition record) as part of
   the fix — not as follow-up. That is exactly the moment the relationship is
   best understood, and exactly the moment this schema is meant to catch.
2. **Don't try to be exhaustive.** `facts.yaml`/`preconditions.yaml` started
   from six and two records respectively, drawn from what the 2026-07-29
   incident and existing `CLAUDE.md` prose already made visible. Add
   incrementally.
3. **For a new fact**: pick (or extend) an entity from the vocabulary above,
   name every location, decide authority, name the real cascade mechanism (or
   admit it's `manual`/nonexistent), and think honestly about whether drift
   is possible and what — if anything — currently catches it.
4. **For a new precondition**: name every command that assumes it, name the
   actual enforcement function (or admit `nothing yet`), and describe the
   concrete failure symptom so a future incident can be matched back to this
   record.
5. **Validate** — `pytest tests/test_data_dependency_schema.py`, or directly
   against the JSON Schemas with any draft-2020-12-compatible validator
   (`jsonschema` in Python works directly against YAML loaded into Python
   objects).
