# Data Dependency Schema

A small, machine-validatable pair of schemas for documenting planars' data-
dependency graph: the same fact — a language's positional structure, which
elements are in diagnostic scope, a span rule's semantics — often
ends up recorded in more than one place: a live Google Sheet, a local TSV, a
YAML schema file, a code comment, the file of Drive IDs, even a GitHub issue's
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

## Three kinds of dependency, three schemas

Investigating that incident surfaced two genuinely different classes of
dependency, and a third — command-level topology — was added later (Phase 4
of the data layer plan, issue #271) once the first two made clear how much
of `CLAUDE.md`'s narrative prose was really the same handful of relational
facts, restated per-file rather than declared once. One schema doesn't fit
all three cleanly:

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

3. **Per-command topology: what a command does, whether it's safe to repeat,
   and what it depends on running before or after** (`operation_record.schema.json`
   / `operations.yaml`). Neither of the first two shapes fits "run
   `restructure-sheets --split-element` before `--regen-construction`" or "a
   false idempotency claim here corrupts what Phase 7/8 build on top of it" —
   this is about one *command*, not one fact or one shared invariant. See
   "Operation record shape" below.

All three schemas are deliberately small, all three are validated against
real JSON Schema files, and all three are populated with real, current
planars facts, preconditions, and commands — not a smoke-test sample.
`facts.yaml`/`preconditions.yaml`/`operations.yaml` *are* the registry; keep
them accurate as the project changes.

## Entity vocabulary (facts only — preconditions don't use one)

Every `locations` entry in a fact record names an **entity** — the kind of
place the fact is recorded. There are fifteen, reusing exactly the names
already established in `CLAUDE.md` and `coding/CLAUDE.md` rather than
inventing new terminology:

| Entity | Description |
|---|---|
| `planar_sheet` | The Drive spreadsheet showing one language's positions/elements (`planar_spreadsheet_id`): a read-only copy of `planar_tsv`, rebuilt by `sync-planar`. Always derived since Phase 10 unit 11b (2026-10-24); until then it was a second editable copy, imported daily. |
| `diagnostics_sheet` | The Drive spreadsheet mirroring `diagnostics_{lang_id}.yaml`: a read-only copy. Always derived — never itself authoritative. |
| `annotation_sheet` | A live Drive spreadsheet for one analysis class (one tab per construction), where annotators enter judgments. The primary source for annotation data. |
| `status_sheet` | Locked, read-only per-language completion-status spreadsheet. Always derived — never authoritative for anything. |
| `collaborator_doc` | The per-language Google Doc for free-text collaborator notes; its text is kept in `records/notes.txt` (a `record_file`), and what is new is the Doc's difference from it (until 2026-10-30, a content hash in `notes_state.json`). |
| `planar_tsv` | `coded_data/{lang}/lang_setup/planar_{lang_id}.tsv` — the source for a language's planar structure, edited by the coordinator (by hand or through `accept-proposal`). Until unit 11b it was also downloaded from `planar_sheet`, the one entity whose cascade direction was ambiguous. |
| `diagnostics_yaml` | `coded_data/{lang}/lang_setup/diagnostics_{lang_id}.yaml` — the coordinator-facing source of truth for a language's diagnostics scope. |
| `construction_tsv` | `coded_data/{lang}/{class}/{construction}.tsv` — the local mirror of one construction's annotation data, imported from `annotation_sheet`. |
| `schema_yaml` | One of the five project-wide `schemas/*.yaml` files (`diagnostic_classes`, `diagnostic_criteria`, `planar`, `terms`, `languages`) — hand-edited, normative, rarely regenerated. |
| `derived_artifact` | Any regenerated, don't-hand-edit output: notebooks, PDF reports, rendered codebook markdown, `tests/snapshots/` baselines. |
| `id_file` | `drive_config.json` (the ID file, read through `coding/drive_ids.py`) — the Drive-ID registry mapping languages/classes to spreadsheet/folder/doc IDs, the one home of those IDs. (Called `manifest` until 2026-10-30: until unit 11c-5, 2026-10-29, a copy of these IDs, `manifest.json`, also sat on Drive for the Colab notebooks, which now find their sheets by label.) |
| `code_comment` | A fact encoded as a docstring or inline comment in a `planars/*.py` or `coding/*.py` module — e.g. a span rule's prose description, whose sync with the schema is checked via a hash sentinel. |
| `github_issue` | A GitHub issue used as a durable coordination/state channel — per-language notification issues, proposal issues, drift issues. The fact's truth value literally lives in the issue's open/closed state or comment history. |
| `filename_convention` | A fact encoded implicitly in a naming pattern — e.g. a language ID inferred from `planar_{lang_id}.tsv`; an archive file's datestamp suffix encoding when it was superseded. |
| `record_file` | A file in `coded_data/{lang}/records/` (Phase 10 unit 16, `docs/plain-record-design.md`): a copy of what people write in Google that no other file holds (each tab's status, an unreviewed proposal sheet), made daily through the local-file door with archive and change log. Never authoritative and never read back: Google stays where it is typed; the file is the record that outlives Google. |
| `test_fixture` | A recorded copy of live state committed under `coded_data/.test_fixtures/` (in planars-data, private) for offline testing — e.g. `coded_data/.test_fixtures/drive_state/`, the raw capture of every annotation spreadsheet and the ID file's entries for them. Never authoritative: it is a snapshot, and its whole job is to be a faithful *stale* copy. Listed as an entity because a test asserting against a fixture that no longer resembles production is a silent failure of exactly the kind this registry exists to name. |

### Why some of these are split rather than consolidated

The four Sheet entities (`planar_sheet`, `diagnostics_sheet`,
`annotation_sheet`, `status_sheet`) could have been one generic `drive_sheet`
with a `detail` string distinguishing which. They aren't, because they differ
in whether they can *ever* be authoritative — `annotation_sheet` is;
`planar_sheet`/`diagnostics_sheet`/`status_sheet` never are (the planar Sheet
was, sometimes, until unit 11b). Naming that
directly in the entity means a reader sees "never authoritative" as a
structural fact of the vocabulary, not something inferred from free text
every time. The same logic splits the local-TSV entities: `construction_tsv`
is download-only, and `planar_tsv` is a source a person edits — the
distinction that mattered on 2026-07-29, when it was also a download. (A
third, `diagnostics_tsv`, a copy regenerated from `diagnostics_yaml`, was
removed with the file on 2026-10-27.)

`id_file`, `code_comment`, and `github_issue` each get their own entity
rather than folding into `derived_artifact`, because none of them are
actually "rebuild-from-source" outputs the way a notebook or snapshot is. The
ID file is a standalone pointer table nothing else can regenerate from
scratch if lost. Code comments are *manually* kept in sync by design (that's
the whole reason the span-rule hash sentinel exists). And a GitHub
issue's open/closed state and comment history don't mirror a fact recorded
elsewhere — they *are* the fact, for anything durably tracked via an issue.

## Fact record shape

```yaml
- id: planar_sheet_structure
  description: a language's positional/element structure (Position_Name/Elements columns)
  locations:
    - {entity: planar_sheet, detail: "the planar spreadsheet for the language, a read-only copy"}
    - {entity: planar_tsv, detail: "coded_data/{lang}/lang_setup/planar_{lang_id}.tsv"}
  authoritative: planar_tsv
  cascade:
    direction: automatic
    mechanism: sync-planar --apply rewrites planar_sheet from planar_tsv, daily and after restructure-sheets --apply
  drift_risk:
    possible: true
    note: a coordinator editing planar_sheet by hand is overwritten at the next sync
    caught_by: the daily sync-planar, which compares the two and files planar-changed
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

## Operation record shape

```yaml
- id: restructure_sheets
  cli_command: restructure-sheets
  description: Archives and regenerates sheets after structural changes to the planar.
  side_effects:
    - "archives the old sheet, creates/regenerates the new one, carries annotations over"
  idempotent: false
  idempotency_note: >-
    Each run archives the current sheet and creates a new one -- running it
    twice with the same flags archives twice, not a no-op.
  apply_gate: "--apply"
  preconditions: [coded_data_clean_tree, coded_data_git_identity_configured]
  writes_to_drive: true
  writes_locally: true
  facts_touched:
    - {fact: planar_sheet_structure, role: writes}
  cascades_triggered:
    - "sync_planars() (sync-planar --apply) runs automatically after --apply"
```

- **`id`** — snake_case form of the CLI command name (`cli_command` with
  hyphens turned to underscores). Chosen so it can be checked mechanically
  against `coding/__main__.py`'s `_COMMANDS` table — see
  `test_every_coding_command_has_an_operation_record` in
  `tests/test_data_dependency_schema.py`, the "a new command cannot be added
  without declaring itself" test the plan asks for.
- **`side_effects`** — what the command creates, writes, or changes. A pure
  reader still gets an entry: `"none (read-only)"` — an empty list would be
  indistinguishable from "not yet documented."
- **`idempotent`** / **`idempotency_note`** — the two fields the plan singles
  out for coordinator review, not just the authority assignments below.
  `idempotent` is a claim Phases 7 and 8 build recovery logic on top of; a
  wrong `true` produces recovery that corrupts rather than repairs. The note
  is required on every record, `true` or `false`, because an unreasoned
  `true` is the more dangerous of the two to get wrong silently.
- **`apply_gate`** — what actually gates a live write: the flags that must
  all be set (`"--apply"`, `"--check --apply"`), or `null` for a command
  with no live-write concept (a mode with `null` is active whenever its own
  flag is set: `generate-sheets`' `--regen-construction` is never gated by
  `--apply` at all). Anything else is an error (`coding/gating.py`).
- **`preconditions`** — ids from `preconditions.yaml` this command's apply
  path assumes hold. Reuses the existing registry rather than restating
  `enforced_by`/`failure_symptom` per command.
- **`writes_to_drive`** — whether this command's default invocation, when its
  `apply_gate` is satisfied, actually writes to Drive/Sheets/Docs (create,
  update, share, delete — not merely read). Added for Phase 5 unit E (issue
  #271) for provenance logging; since Phase 10 unit 5 the Drive door
  (`coding/drive_door.py`) reads it (through `coding/provenance.py`'s
  `writes_to_drive`) to refuse every write on a run where it is `false` for
  the gate that was actually satisfied, and the provenance log records the
  writes themselves. Several commands' Drive-write status
  genuinely diverges by mode the same way `apply_gate`/`preconditions` can —
  `generate-sheets`' `--regen-dependents` writes to Drive with no `--apply`
  at all — so a mode restates it
  per the same "full override" rule as every other mode field. `false` for a
  command with no live-write concept at all (pure read-only) and for one
  whose writes are entirely local, never Drive itself.
- **`writes_locally`** — the same question for the files the local-file door
  keeps (`coding/file_door.py`'s `KINDS`: annotation TSVs and each language's
  set-up files; Phase 10 unit 6a). The door refuses every local write on a
  run where it is `false` for the gates actually satisfied, so a dry run
  writes nothing. Required on every record and mode, like `writes_to_drive`.
- **`edits_sources`** (optional) — the sources (`file_door.SOURCES`: the
  planar, the diagnostics YAML — files a person edits) the command may
  write. The door refuses a write to any other source, and stops on a name
  that is not a source. Only `accept-proposal` and the commands that edit the
  YAML (`sync-params`, `rename-construction`) list any. (The Sheet intakes,
  import-planar and import-sheets, did until unit 11b retired them.)
- **`facts_touched`** — `{fact, role}` pairs, `fact` an id from `facts.yaml`
  and `role` one of `reads`/`writes`/`both`. Reuses the existing registry the
  same way `preconditions` does — a reader who wants to know "who's
  authoritative for this fact" already has that answer in `facts.yaml`
  itself; this field only needs to say which commands are in the picture at
  all.
- **`cascades_triggered`** — what this command's own run sets off
  automatically as a side effect (another command's regeneration step, a
  notification).
- *(There was an `ordering_constraints` field — plain-language "run X before
  Y" statements. Removed 2026-10-12, Phase 10 unit 7: nothing executed it, so
  nothing kept it true, and most entries had become history notes. A
  sequencing rule now lives where it is enforced: `--regen-construction`
  refuses to drop annotated rows (run `--split-element` first, or pass
  `--confirm-drop`); `retire-classes` warns that a rename needs
  `restructure-sheets --rename-class`.)*
- **`modes`** — some commands genuinely behave differently by flag:
  `generate-sheets`' `--regen-construction` has no `--apply` gate at all and
  touches different facts than the base command; `build-chapters`' `--check`
  writes no chapter file and has different preconditions. Flattening these onto one set of top-level fields would
  either overstate what the base command does or understate what the mode
  does. A `modes` entry is a **full, self-contained override** — it restates
  its own `side_effects`/`idempotent`/`idempotency_note`/`apply_gate`/
  `preconditions`/`facts_touched` completely rather than adding to or
  inheriting from the parent record's top-level fields, even where a value
  happens to match. Most commands have no divergent modes and get
  `modes: []`; the parent's own top-level fields always describe the
  command's default invocation, never a merge across modes.
- **`always_on_writes`** (optional) — Drive writes the command makes on every
  run, a dry run included, by name. Only `import-sheets` has one
  (`highlighting`: pink on invalid cells). The Drive door
  (`coding/drive_door.py`) refuses every write on a run whose `apply_gate`
  isn't met, except those made inside `with drive_door.always_on(name)` for a
  name listed here, and logs them like any other write. Code runs
  from this field: a name missing here makes the write fail, not drift.

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
- Neither JSON Schema can mechanically cross-check an operation record's
  `facts_touched[].fact` against `facts.yaml`'s real ids, or its
  `preconditions[]` against `preconditions.yaml`'s — same class of
  limitation as the `authoritative`-in-`locations` check above, and checked
  the same way, by a belt-and-suspenders test.
- `operations.yaml` was drafted 2026-08-10 as a first pass, not yet reviewed
  against the two things the plan requires the coordinator to check
  specifically: every authority assignment (`facts_touched`/`preconditions`)
  and every `idempotent` claim. Until that review, treat it as a draft. See
  the file's own header comment.

## How to use this for ongoing work

1. **When you find a bug that traces back to an undocumented authority/cascade
   relationship**, write the fact record (or precondition record) as part of
   the fix — not as follow-up. That is exactly the moment the relationship is
   best understood, and exactly the moment this schema is meant to catch.
2. **Don't try to be exhaustive.** `facts.yaml`/`preconditions.yaml` started
   from six and two records respectively (later grown to nine and three by a
   deliberate sweep of `CLAUDE.md` and `coding/*.py` for dependencies with
   real, existing evidence — a dedicated check already catching drift, or a
   documented gotcha — rather than speculative ones), drawn from what the
   2026-07-29 incident and existing `CLAUDE.md` prose already made visible. Add
   incrementally.
3. **For a new fact**: pick (or extend) an entity from the vocabulary above,
   name every location, decide authority, name the real cascade mechanism (or
   admit it's `manual`/nonexistent), and think honestly about whether drift
   is possible and what — if anything — currently catches it.
4. **For a new precondition**: name every command that assumes it, name the
   actual enforcement function (or admit `nothing yet`), and describe the
   concrete failure symptom so a future incident can be matched back to this
   record.
5. **For a new command**: add an `operations.yaml` record in the same commit
   that registers it in `coding/__main__.py`'s `_COMMANDS` —
   `test_every_coding_command_has_an_operation_record` fails otherwise.
   Reference existing `facts.yaml`/`preconditions.yaml` ids where the command
   genuinely reads or writes a registered fact or assumes a registered
   precondition, rather than restating their content; name every other
   command this one has to run before or after, and why.
6. **Validate** — `pytest tests/test_data_dependency_schema.py`, or directly
   against the JSON Schemas with any draft-2020-12-compatible validator
   (`jsonschema` in Python works directly against YAML loaded into Python
   objects).
