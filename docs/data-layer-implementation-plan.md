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

## Phase 3 — Schema reorganization *(coordinator decides)*

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

## Phase 6 — Data contracts at boundaries

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
