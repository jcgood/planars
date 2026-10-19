# Data layer: implementation plan

**Status:** in progress — see [data-layer-progress.md](data-layer-progress.md)
for what is done, what is in flight, and what to do next. That file is the
authoritative state record; this one is the spec.
**Rationale:** [data-layer-design.md](data-layer-design.md) — read that first.
**Tracking issue:** #271

This plan is written to be handed to agents one phase at a time. Each phase is
scoped, has explicit done-criteria, and states what it must *not* do.

---

## Ground rules — apply to every phase

1. **No writes to live Google Drive until Phase 9.** Phases 0–8 are entirely
   local. An agent that finds itself needing `--apply` against real Drive has
   misread its scope and should stop.
2. **Adam's annotation data must not change.** Any phase that could alter
   generated sheet content is gated behind the Phase 1 snapshot tests.
3. **`coded_data/` is never modified** except where a phase says so explicitly.
4. **Derive, don't duplicate.** If a phase would create a second copy of a fact
   that already exists somewhere, stop and raise it — that is the exact defect
   this work exists to remove.
5. **Prefer extending `data_dependency_schema/` over inventing a new registry.**
   Its records already carry `locations` / `authoritative` / `cascade` /
   `drift_risk` and are the right shape.
6. Every phase ends with `pytest` green and the work committed and pushed.
   Run test suites with `run_in_background`.

**Decision ownership.** Phases marked *coordinator decides* contain judgment
calls about linguistics or authority that an agent must not resolve alone — the
agent drafts and presents options; Jeff decides. All others are fully delegable.

---

## Phases 0 and 1 — doorway, fake, and characterization tests (interleaved)

> **Ordering note.** These two phases cannot be run in sequence. Snapshot tests
> require the doorway (so commands can run offline); safely migrating callers to
> the doorway requires snapshot tests (to prove behavior didn't change). The
> resolution is to build the infrastructure once, then migrate callers **one
> file at a time, capturing that file's snapshots immediately after each
> migration**, so each file is locked before the next is touched. Do not
> attempt "migrate all eleven, then write tests."

### Phase 0a — protocol, capture, and fake *(no caller changes)*

**Goal.** Build the offline infrastructure without modifying any command.

**Why.** Eleven files in `coding/` call gspread directly (`generate_sheets`,
`import_sheets`, `update_sheets`, `sync_params`, `restructure_sheets`,
`validate_coding`, `refresh_dropdowns`, `generate_status_sheet`,
`generate_biuniqueness_allomorphy_sheet`, `generate_notebooks`,
`generate_reports`). There are no end-to-end tests for any command that touches
Drive — exactly where every serious incident has occurred. Nothing else in this
plan is verifiable until this exists.

**Scope.**
- Define a narrow doorway protocol covering only the operations actually used
  (open spreadsheet, list/add/delete worksheets, get values, update range,
  batch_update, set validation, format cells, reorder tabs, Drive file
  create/move/list/permissions). Derive the list by reading the eleven files —
  do not design it speculatively.
- Add `python -m coding capture-drive-state` — **read-only** — dumping live
  structure and content for all languages to versioned fixtures.
- Implement an in-memory fake serving those fixtures and recording all
  mutations for assertion.

**Build the fake from recorded real responses, not from the gspread docs.**
Capture actual return values during a read-only run and have the fake replay
them. Its subtleties — 1-indexing, `get_all_values` padding, `update` range
semantics, what `worksheets()` returns — are exactly what gets guessed wrong,
and a wrong fake silently invalidates every test built on top of it.

**Done when.** Fixtures are captured and committed; the fake serves them; a
smoke test exercises every protocol operation against the fake. No command has
been modified.

**Non-goals.** No caller changes. The fake need not be a faithful Google
emulator — only faithful for operations actually used.

### Phase 0b/1 — migrate callers and capture snapshots, one file at a time

**Goal.** Route each file through the doorway and lock its behavior, incrementally.

**Per-file procedure — repeat for each of the eleven:**

1. **Before migrating**, run that file's dry-run/read-only paths against real
   Drive and save the output.
2. Migrate the file to the doorway. Preserve `_with_retry` semantics exactly.
3. Run the same dry-run paths against the fake (serving fixtures captured from
   the same Drive state) and assert the output matches step 1. This is the
   check that the migration didn't change read behavior.
4. Capture snapshots for all of that file's commands, including `--apply` paths:
   generated sheet structures (headers, row contents, dropdown validation, tab
   order), TSV outputs, manifest states, and the fake's full mutation log.
5. Have a human review the mutation log for `--apply` paths once, before it
   becomes a snapshot. Write paths have no pre-migration baseline to diff
   against, so this review is the only thing standing between a migration bug
   and it being enshrined as "correct."

**Done when.** Every file that reaches Drive routes through the doorway; every
command runs end-to-end against the fake with no network; each command has
snapshots; and deliberately perturbing any generator makes a snapshot test fail.

**Note on "eleven".** The count above was hand-written into this plan and then
taken as given by the Phase 0a survey, rather than derived from the code. A
scan on 2026-08-02 first reported **seventeen** files in `coding/` reaching
Drive directly, not eleven — the seven missed were `setup_root_folder`,
`apply_pending`, `prune_manifest`, `check_notes`, `sync_diagnostics_yaml`,
`import_planar`, and `integrity_check`. Two of those mattered more than their
size suggested: `import_planar` is the command at the centre of #248, and
`check_notes` is the only user of Google Docs. That "seventeen" was itself
briefly wrong — the real total was **eighteen** (`restructure_sheets.py` was
the eighteenth) — the same hand-copied-derived-number defect one level up,
caught by simple arithmetic not adding up (see `docs/data-layer-progress.md`'s
2026-08-02 decisions-log entry). `tests/test_doorway_coverage.py` derived the
list from that point on, so this whole phase's file count stopped being
something to read off a sentence and became something to run a test for.
Phase 0b/1 finished 2026-08-04 with all eighteen migrated —
`tests/test_doorway_coverage.py`'s `_REMAINING` is now empty.

**Non-goals.** No behavior changes. No refactoring of command logic beyond the
call-site substitution. Do not fix anything a snapshot reveals as odd — record
current behavior including behavior that looks wrong, and note oddities in the
tracking issue for separate triage.

---

## Phase 2 — Hidden-fact inventory

**Goal.** Produce the inventory nobody currently has: every schema fact that
lives only in a tool body.

**Why.** Facts have been migrated into YAML reactively, one per bug. Without an
inventory there is no way to know how many remain, so there is no way to know
when this work is done.

**Scope.** Read every file in `coding/` and `planars/` and record each instance
of: hardcoded class or construction names; hardcoded criterion names; hardcoded
column vocabularies; hardcoded file paths encoding structure; hardcoded value
semantics (e.g. "`scopal=n` means exclude"); magic defaults and fallback lists.

Known starting points: `_STRUCTURAL_COLS` / `_PAIR_STRUCTURAL_COLS` in
`validate_coding.py`; the `prescreening` entry in
`_build_coreference_params`; `_filter_nonperm_pairs_by_prescreening`'s
`scopal` handling and path; `_OBLIGATORY_POSITIONS_DEFAULT`;
`_COREFERENCE_CONSTRUCTION_PARAMS`.

**Done when.** `docs/hidden-facts-inventory.md` exists, listing each fact with
its location, whether an authoritative source already exists elsewhere, and a
derivable / must-declare classification.

**Non-goals.** Do not fix anything. This phase only inventories.

---

## Phase 3 — Schema reorganization *(coordinator decides)* — done 2026-08-10

**Goal.** Split `schemas/` into research-facing and administrative sections, and
relocate inventoried facts into it.

**Why.** Addresses the differential-rate problem directly. Fast-moving research
content and slow-moving conventions currently share fields; that shearing is
what generates bugs.

**Scope.** Apply the research / administrative split. Move Phase 2's derivable
facts into schema files and make the tools read them.

**The most valuable output is not the tidiness.** It is the list of fields that
*resist* classification — a field that won't go cleanly into either section is
one where a research fact and an administrative fact are welded together.
`Class_Type` is the known example. Treat every such field as a defect site and
report it; do not silently force a classification.

**Done when.** Every Phase 1 snapshot test still passes **byte-identical**, the
split is applied, and resistant fields are catalogued in the tracking issue.

**Non-goals.** No intended behavior changes whatsoever. If the split implies a
desirable behavior change, that is a *separate, later, deliberate* step — not
part of this phase.

Done 2026-08-10: `diagnostic_classes.yaml` split into that file (linguistic
content) and `diagnostic_classes_status.yaml` (process/tracking state),
joined by class `name`; `coding/schemas.py`'s `load_diagnostic_classes()`
merges both at read time so existing callers needed no changes. Scope turned
out narrower than "all of `schemas/`" — only `diagnostic_classes.yaml` had
fields moving at genuinely different rates within the same record;
`diagnostic_criteria.yaml`, `terms.yaml`, and `languages.yaml` were already
single-purpose. `Class_Type` (`schemas/planar.yaml`) — the resistant field
named above — is catalogued on issue #271, not split: its two welded jobs
(ontological open/closed-class claim vs. typographic-rule selector) can't be
separated without changing validator behavior, which this phase's non-goal
rules out. See `docs/data-layer-progress.md`'s 2026-08-10 decisions-log entry
for the split-mechanism choice and Findings 18/19 for two pre-existing bugs
found (and left unfixed, same reason) while verifying it.

---

## Phase 4 — Topology declaration *(coordinator decides authority)*

**Goal.** Make the relational knowledge currently narrated in `CLAUDE.md`
explicit, machine-readable, and inspectable.

**Why.** This is where comprehension load actually lives, and it is the highest-
value half of the registry.

**Scope.** Extend `data_dependency_schema/` (10 facts, 3 preconditions today) to
cover, for every command: side effects; idempotency; preconditions; authoritative
store per fact touched; cascade triggered; and required ordering relative to
other commands.

Absorb the operational knowledge currently in `CLAUDE.md` and
`coding/CLAUDE.md` — e.g. `--regen-construction` bypassing `--apply`;
`restructure-sheets --split-element` before `--regen-construction`;
`prune-manifest` for retirement but never for rename.

**Done when.** Every `coding/` command has a record; a test asserts every
command has one (so a new command cannot be added without declaring itself);
and the narrative topology in `CLAUDE.md` is replaced by a pointer to generated
output.

**Coordinator reviews two things, not one:** authority assignments *and every
idempotency claim*. A false "this operation is idempotent" is load-bearing —
Phases 7 and 8 build recovery logic on top of those claims, so a wrong one
produces recovery that corrupts rather than repairs. Every idempotency claim
must either be reviewed or have a Phase 8 test proving it.

**Non-goals.** Do not yet *enforce* preconditions at runtime — that is Phase 5.

---

## Phase 5 — Derived registry, argparse, and call validation

**Goal.** A generated, always-accurate operation inventory, plus validated calls.

**Why.** The succession artifact. Must be *derived*: a hand-authored registry is
worse than none, because a stale map gets trusted.

**Scope.**
- Standardize on `argparse` everywhere. `generate_sheets.py` currently scans
  `sys.argv` by hand, which is the source of the silent-unknown-flag failure
  mode; `import_planar.py` already uses argparse and is the model.
- Generate the mechanical registry from signatures, type hints, and docstrings,
  joined with Phase 4's declarations. Never hand-authored.
- Enforce Phase 4's preconditions at call time.

**Done when.** `python -m coding registry` emits the full inventory; a test
asserts it is regenerable and current; unknown flags are hard errors everywhere;
declared preconditions are checked before execution.

---

## Phase 6 — Data contracts at boundaries — done 2026-08-17

**Goal.** Declare expected input/output shapes on the highest-traffic functions.

**Why.** Local documentation that cannot go stale, plus real bug-catching. Be
realistic about reach: contracts catch structural and cross-row invariants
(they would have caught the scopal divergence, and would have turned the
phrasal_accent failure into a clear error). They do **not** catch ontological
errors like the pronoun bug, nor authority/ordering failures, nor idempotency
failures.

**Scope.** Introduce `pandera` (DataFrames) and/or `pydantic` (dicts/JSON) on
the boundaries that matter first: planar load, filled-TSV load, pair-row load,
manifest read/write. Do not attempt full coverage in one pass.

**Done when.** The chosen boundaries have contracts, tests prove violations
raise clearly, and every Phase 1 snapshot test still passes.

---

## Phase 7 — Recoverability for multi-step operations

**Goal.** Close the transaction gap.

**Why.** `restructure-sheets --apply` performs roughly seven sequential side
effects — archive sheet, create sheet, carry annotations, rename local TSV
directory, update manifest, push planar to Drive, notify GitHub issue — with no
rollback. Failure at step five leaves steps one to four applied to live data.
#248 is exactly this story.

**Scope.** Journal each step of a multi-step operation before performing it;
support resume and rollback; make each step individually idempotent where
possible (using Phase 4's idempotency declarations).

**Done when.** Multi-step operations can be interrupted at any step and either
resumed or rolled back to a consistent state, proven by Phase 8's tests.

---

## Phase 8 — Fault-injection stress testing

**Goal.** Prove the system survives partial failure before it goes near real data.

**Scope.** Using the Phase 0 fake: inject failure at every step of every
multi-step operation and assert consistent recovery. Inject API failures (429,
500, timeout, partial writes). Assert idempotency claims by running every
idempotent operation twice. Simulate concurrent human edits during a
programmatic operation — Adam editing a sheet mid-`restructure` is a real
scenario. Simulate the `coded_data`-dirty and stale-replica conditions behind
#245 and #248.

**Done when.** Every multi-step operation has fault-injection coverage at every
step, and every idempotency claim in Phase 4 has a test proving it.

---

## Phase 9 — Staged cutover *(coordinator decides; only phase touching live Drive)*

**Goal.** Go live without risking annotation data.

**Scope, strictly in order:**

1. **Shadow reads.** New path reads real Drive, compares against the old path's
   results, writes nothing. Run for several days; investigate every divergence.
2. **Write cutover, one command at a time**, lowest-risk first. Suggested order:
   read-only/reporting commands → additive commands (`update-sheets`,
   `sync-params`) → generative (`generate-sheets`) → destructive
   (`restructure-sheets`, `prune-manifest`) last.
3. **Confirm with Adam before any step that could touch sheets he is actively
   annotating**, and prefer a window when he is not mid-pass.

**Done when.** All commands run through the new path in production, the old
path is removed, and a full daily refresh cycle completes clean.

---

## Phase 10 — Ownership and chokepoints *(coordinator decides at three pauses)*

**Why.** Planned 2026-10-12, after small requests about the synth0001
biuniqueness sheet kept uncovering the same disease one level down. The
Planar Structure tab claimed to be "read-only" and was never locked, and only
some commands refreshed it. A `[y, n]` default hid missing criterion values.
Hidden facts kept accumulating, three of them added by Claude in two days.
And the doorway turned out to check nothing it writes: `open_spreadsheet`
returns the raw gspread object, so every content write bypasses it. The
design doc asked for a chokepoint *that knows the topology*; Phases 0–9 built
the chokepoint's plumbing but never scoped what it should know (Phase 6
covered four *read* boundaries; the write side was never picked up). This
phase finishes that, and applies the same rule everywhere a fact can live.

**Ground rules (in addition to the plan-wide ones above):**
- **Light maintenance beats speed and elegance.** Before adding any registry,
  declaration, document or check, ask who updates it when the code changes
  and what happens if they don't. A registry is right only if it is the one
  source the code *runs from* (a wrong entry gives visibly wrong output);
  never one that *describes* the code (it needs a test to stay true, and
  drifts). A list moved into a function body is a hidden fact, not a fix.
- **One editable home per fact;** every other copy is locked and
  regenerated (compare daily, write only what differs).
- **Every write passes a door that runs from the schemas:** Drive, local
  files, GitHub issues, and hand edits to sources.
- **The record outlives its tools.** Versions and decisions live in plain
  files; git, GitHub and Google are transport, notification and editing
  surfaces. The project may outlive any of them.
- **No half-finished transitions.** Each unit removes what it replaces in the
  same commit; every step leaves a complete, working system.
- **Before saying "done", ask what kinds of thing could exist,** not only
  what has been seen.

**Units** (numbering is the planning session's; state lives in
[data-layer-progress.md](data-layer-progress.md)):

| # | Unit | Done when |
|---|---|---|
| 1 | biuniqueness `prescreening` tab renamed `elements`; the class's tab names read from the schema, never typed. **Revised 2026-10-13 (Jeff): the class moves to English at the same time.** English's planar gets `Biuniqueness_Scope` (same classifier as synth0001's backfill, pushed to the Planar Sheet); class added to `diagnostics_stan1293.yaml`; `generate-sheets` creates the English sheet with `elements` already; a one-time migration copies Adam's synth0001 `prescreening` answers (Comments, Status too) into it, matched by position + element (the two planars are identical); synth0001's class is retired (removed from its YAML, sheet archived via `prune-manifest`), so no live tab rename; fixtures refrozen; #254 comment with the new link | rename is a schema edit only; English sheet live with Adam's 18 answers intact; synth0001 class retired; nothing still says `prescreening` for this class |
| 2 | `locked_tabs` registry in `schemas/planar.yaml` (Planar Structure, Instructions); one `rebuild_locked_tabs` applied by create/restructure and daily by `update-sheets --apply` | every sheet's locked tabs current and protected after one daily run; adding a locked tab = one registry entry |
| 3 | Close every open entry of `docs/hidden-facts-inventory.md` (fix the code to read its one source, delete copies); first group D1+D2+R1 with `criteria_for` and **removal of the `[y, n]` default** | inventory marked finished, every entry "Closed by <commit>" or declared |
| 4 | Which tabs produce spans: `produces_spans: false` on feeder constructions; one reader in `planars/reports.py`; module `_SNAPSHOT_CONSTRUCTIONS` deleted; check-codebook checks the field | snapshots unchanged; no module lists span tabs |
| 5 | **The Drive door knows the topology.** `coding/sheet_spec.py` built only from schemas; doorway wraps handles and checks every write; safeguards move into the door (retry, dry-run, refuse to drop annotations, snapshot before destroy, per-write provenance, read-only door for non-writing commands, concurrent-edit check); sheets carry their own identity (developer metadata); every kind of Drive write specified (class sheets → sharing → planar → diagnostics → status → notes Docs → files) | fake in enforce mode from the start; ≥1 week live watch mode with every violation resolved; then enforce; no kind left unchecked |
| 6 | **The local-file door**: every write to `coded_data/` and state files through one door, same specs, archive-before-overwrite and change log enforced; `drive_config.json` reduced to bootstrap IDs | as unit 5 |
| 7 | Detectors the code runs: string literals matching schema-owned values (start narrow); `python -m coding …` strings parse with the real parser; `_KNOWN_SITES` keyed by message; `operations.yaml` fields nothing executes either enforced or deleted; version bump automated | detectors in the suite; first hits fed into unit 3 |
| 8 | The daily refresh becomes one command, `daily-refresh` (to be added to `coding/__main__.py`); the workflow only sets up and calls it | steps moved group by group; tested end to end against the fake |
| 9 | `coding/CLAUDE.md` (and planars/, root behaviour paragraphs) cut to pointers; history to the decisions log | each moved fact confirmed in its module docstring |
| 10 | One GitHub issue path (`coding/issues.py`) and a label registry; CLAUDE.md label table generated | five find-or-create copies gone; unknown label hard-fails |
| 11 | One editable home per fact. **Planar and diagnostics:** source in planars-data, locked copies, one editable *proposal sheet* per language with a "What changed?" column; daily diff → notification issue; `accept-proposal` applies accepted parts, rebuilds copies, resets the sheet, writes a "Last review" note; automatic intakes (`import-planar --apply`, diagnostics `--from-tsv` merge) retired. Manifest shrunk to IDs; Colab reads real Sheets through one package function; notebook logic moved into the package; notebooks and status sheets rebuilt daily; Instructions rules generated | no fact has two editable copies |
| 12 | Durable state (`pending_changes.json`, provenance log, regen snapshots) kept in planars-data, not on the machine that ran the command | a daily-refresh import's pending changes are visible to local `apply-pending` |
| 13 | One home per kind of knowledge: project rules move from Claude's private memory into the repo; decisions into schema comments / decisions log, issues for discussion only; plans transcribed into the repo when work starts | no project rule exists only in memory |
| 14 | Sharing: named access only (no "anyone" on folders; notes Docs editable by the language's annotator by name); `drive_config.json` and emails out of the public repo | live sharing matches the sharing spec; door enforces it |
| 15 | One version history in plain files: dated archive of every previous version (one date format) + a per-language change log; git/GitHub only transport, backup, notification; `data-overwrite` reads the log | no alarm or command depends on git history |
| 16 | Nothing only in Google or GitHub: Status values, notes Doc text and last-edited-by imported into plain files; a `diagnostics` issue closes only by recording its decision in a file | — |
| 17 | The hand-edit door: a change log for `schemas/` and per-language sources; pre-commit hook (and CI) refuses a source change without a change-log line | — |
| 18 | Every exported result carries the package version and each language's change-log position | results reproducible from their record |
| 19 | **Leftovers: nothing kept that no starting point reaches.** Added 2026-10-17 (Jeff), after `python -m planars` turned out to have been broken since March with nothing using it, and five snapshots of retired classes were still in `tests/snapshots/`. The starting points are the `coding` commands, the workflows, the notebook templates, the reports' list of analyses and the root scripts. One sweep (`vulture` plus a check of which files nothing imports), each hit reviewed and deleted or explained; then a test that fails when a file in `coding/` or `planars/` is reached from no starting point. Not a log of calls: that needs someone to read it and calls rarely-run code dead | sweep's list handled; the test in the suite |
| 20 | **The suite back to minutes.** CI took 8–13 minutes until 2026-10-14 and 75–100 since c6da07d (unit 5d's rule 6, the end-of-command sheet check); command tests that run update-sheets or generate-sheets went to 1–2 minutes each. The live daily refresh did not slow (about 20 minutes, as before), so the cost is in how the check runs against the fake. Time one slow test, fix what it spends the time on, without weakening the check. **Also, found 2026-10-17:** no live command has written a provenance line since 2026-10-13, when the door took over the log — today's `--regen-construction` for #307 wrote a tab and left none. Find why and fix it, with a test that a live-mode write leaves its line | full suite and CI back near their 2026-10-14 times; every live write logged |
| — | Optional, Jeff decides: a second Drive owner or shared drive; narrow the refresh token's Sheets and Docs scopes (Drive is already `drive.file` — only files the tooling created — found 2026-10-12 when Google refused a sharing change; `spreadsheets` and `documents` still reach all of Jeff's files) | — |

**Order:** memories and this transcription → 14 (sharing, live) → 4 → 7 →
3's first group → 1 → 2 → 10 → **pause: unit 5 design** → 5 for class
sheets (watch ≥1 week; meanwhile rest of 3, then 20, 19, 9's first half
and 8, added 2026-10-17; 20 first because a slow suite taxes every other
unit) → 5's other kinds →
**pause: units 6 + 15 + 11's proposal sheets, designed together**
(moved forward by Jeff 2026-10-18 to run during 5e's wait; draft in
[ownership-design.md](ownership-design.md), which also renames 6's steps
6a–6c and 11's 11a–11d) → 12 →
6 B–D → 9's second half → proposal sheets → rest of 11 → 16–18. **Unit 9
split (Jeff, 2026-10-17):** the root CLAUDE.md (and planars/CLAUDE.md) is
cut to rules and pointers right after 19, because a long file full of
history buries its working rules (the "a bug is never a question" rule
kept slipping); `coding/CLAUDE.md` waits until after unit 6, which changes
the modules it describes. A third pause: the
transcript diff from removing `[y, n]` is shown to Jeff before it lands.

---

## Phase 11 — The research logic as a spec *(deferred; not before Phase 10's doors and version history)*

Raised by Jeff 2026-10-13. **The worry:** key project logic exists only
inside Python scripts. If Python, or these scripts, stop being maintained,
the logic has to be dug back out of the code. Same principle as Phase 10's
"the record outlives its tools", applied to the logic instead of the data.

**Direction (agreed, not designed):**
- **The spec owns the research logic:** the data model, criteria and their
  values, how rows and tabs are built, what makes a position qualify, how
  spans are computed, and the daily refresh's step order and preconditions.
  The code *runs from* the spec (Phase 10's registry rule) — a spec that only
  describes the code would drift like every description before it.
- **The plumbing stays ordinary code:** talking to Google and GitHub,
  retrying, writing files. It has no linguistic content and is easy to
  rewrite in any language. Do not try to compile all behaviour from a spec —
  a spec able to do that is a programming language with worse tools.
- **Worked examples in plain files** (filled TSV + rules → expected spans,
  and the like) go with the spec. Any implementation, in any language, is
  correct if it reproduces them. The saved span outputs in
  `tests/snapshots/` are most of the way there.

**First candidate:** qualification rules and span computation — the core of
the three hypotheses, and the logic most buried in code today (each
`planars/` module implements its rule; the schema holds a prose
description and a hash check). Unit 8's single daily-refresh command is
the step that makes the refresh order movable into the spec later.

Done when: designed with Jeff (a pause, like Phase 10's); out of scope until then.

---

## Working with agents

**Phases are not work units.** Phase 0b/1 is eleven files; Phase 2 is the whole
of `coding/` and `planars/`. Decompose into units of roughly one to three files
before handing anything off. Each unit needs its own scope, done-criteria, and
non-goals — a unit that can't state its own done-criteria isn't ready to
delegate.

**Delegate in proportion to machine-verifiability, not to how routine the work
feels.** The cost of delegation is review, and review only gets cheap when the
done-criteria are checkable by running something rather than by reading a diff.
Phase 8 (does the test exist, does it pass, does removing the guard make it
fail) is close to free to verify. Phase 0a is not — a subtly wrong fake looks
correct on inspection and invalidates everything downstream. Supervise where
correctness is only visible by reading.

**This inverts the usual instinct.** Rather than delegating the boring
foundation and supervising the interesting parts, invest supervision *early* —
0a and the first two or three file migrations — because that is what buys
cheap, aggressive delegation for phases 2, 5, 6, and 8 afterward. Verification
machinery is the thing that makes delegation pay.

**Every agent starts cold.** Point briefs at specific files, not at "the docs" —
this repo's `CLAUDE.md` files are large and an agent that reads everything
spends its budget before starting. A useful brief names: the one phase section
it implements, `docs/data-layer-design.md` for rationale, the specific source
files in scope, and the non-goals.

**Constrain writes.** Agents on phases 0–8 should not push to `main`, commit to
`coded_data/`, or make any live Drive call other than the read-only
`capture-drive-state`. Worktree isolation is a good default so work can be
reviewed before it lands. Note that `coded_data/` is a separate nested repo that
the outer repo ignores, so a worktree may not have it — and much of the existing
test suite reads it. Verify how that behaves on the first agent run before
assuming a green suite means anything.

**Require incremental commits in the brief.** Instruct agents to commit each
unit of output as it is produced, not once at the end, and to ensure any stop
leaves work committed rather than sitting in the working tree. Agents can pause
or fail mid-task with substantial analysis done and nothing durable — this
happened on the very first agent run of this plan, which stalled several files
into an eleven-file enumeration with everything uncommitted. "Write
incrementally" is not sufficient on its own; unstaged files are not recoverable
work.

**A stalled agent should be resumed, not relaunched.** Its context is intact,
so resuming costs a fraction of starting over and avoids re-doing completed
analysis.

---

## Sequencing notes

- Phases 0–2 are pure infrastructure and zero risk to real data, and can start
  immediately. Note that "zero risk" is not the same as "fully delegable" —
  see *Working with agents* above; 0a in particular warrants close review.
- Phase 2 is independent of 0 and 1 and can run concurrently with them.
- Phase 3 is the highest-value and highest-risk phase; it is deliberately gated
  behind the snapshots from 0b/1.
- Phases 4 and 6 can proceed in parallel once 0–2 are done.
- Phase 9 must not begin until 8 is complete.
- Provenance capture (a stated top-tier value with no current mechanism) should
  be folded into Phase 5 — every registered call recording what it did is
  nearly free once the chokepoint exists.
