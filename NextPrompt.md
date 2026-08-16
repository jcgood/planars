# Next session

Standing prompt for resuming work in a fresh Claude session. Open a new session
and say: **"Read NextPrompt.md and carry on."**

**This file holds no state.** What is done, what is next, and why lives in
`docs/data-layer-progress.md` and the issue tracker, which own those facts. The
one thing here that needs editing between sessions is the *Now* line below.
Everything else is standing instruction and should change rarely. If you find
yourself copying a paragraph of status into this file, it belongs in the
progress doc instead — a second description of the same fact is the exact defect
this project is trying to remove.

---

## Now

**Phase 0b/1 (the doorway migration) and Phase 3 (schema reorganization) are
both complete, nothing outstanding from either.** Phase 0b/1 finished
2026-08-04 (18 of 18 files); Phase 3 finished 2026-08-10. Every bug either
turned up (Findings 13, 15–19, 21) is fixed; #276 is closed. Full detail in
`docs/data-layer-progress.md`'s Current state and Findings sections — no
need to duplicate it here.

**arao1248's diagnostics gap (surfaced by Finding 19) is two-thirds closed.**
`nonpermutability` and `free_occurrence` are onboarded (2026-08-10, no
linguistic judgment needed — both universal with fixed criteria). `proform`
is still open, waiting on Adam via issue #279 (construction-specific; nothing
in the repo says what fills it for Araona). Not blocking anything else — a
missing required class no longer blocks `sync-diagnostics-yaml --apply`'s
local-TSV direction from picking up whichever classes *are* ready (Finding
20), just `--to-sheet`/`import-sheets` for the language as a whole.

**Phase 4 ("Topology declaration") is drafted, traced against code end to
end, and all three of the plan's "done when" items are complete — the one
thing left is Jeff's own final read-through, not more Claude work.**
`data_dependency_schema/operations.yaml` (+ `operation_record.schema.json`)
has one record per `coding/__main__.py` command (24, mechanically checked),
with a `modes` field for the 4 commands whose behavior genuinely diverges by
flag. The 2026-08-11 interactive session re-checked every flagged
idempotency claim against actual code, added 2 new facts to `facts.yaml`,
and found + fixed 2 real `coded_data_clean_tree` guard gaps on the spot
(`prune-manifest`, `sync-diagnostics-yaml` — Findings 23/24); it also found a
cross-cutting batched-write reliability bug across 4 commands (Finding 22,
filed as **issue #280**). Later the same day, a full line-by-line pass
(3 agents tracing every one of the 24 records against `coding/*.py`, not
just the ones flagged) found and fixed several more stale claims (Finding
25 — mostly `operations.yaml`/`facts.yaml` corrections, including a stale
"still open" reference to a gap actually fixed a week earlier) and one more
real bug: `generate_biuniqueness_allomorphy_sheet.py --apply` was silently
wiping annotator-entered `has_allomorphs`/`Members`/`Notes` on every re-run
(Finding 26, fixed — carries annotations over by (Position_Name, Element)
now). Jeff decided to fix #280 immediately rather than defer it; the fix
grew from the originally-filed 4 commands to 6 (`generate_notebooks.py`/
`generate_reports.py` turned out to share the same shape). `CLAUDE.md`'s
narrative topology prose (the "Retiring a class"/"Renaming a class"
paragraphs) is now a pointer to `operations.yaml` instead of a restatement.
2026-08-16: one of the five things Jeff was asked to check is resolved
(Finding 27 — `update_sheets.py`'s header-based pair-row detection is
deliberate, now documented in a code comment; `integrity_check.py`'s
duplicate copy of the same logic consolidated into the shared helper). Four
remain open, no rush — see the list in "Open questions for Jeff" below.

**What's actually left: read `docs/data-layer-progress.md` § "Open questions
for Jeff"** and look over the diff (`operations.yaml`, `facts.yaml`, the six
`#280` fixes, `generate_biuniqueness_allomorphy_sheet.py`) — the plan is
explicit that authority assignments and idempotency claims are the
coordinator's call, and today's pass was Claude tracing code, not Jeff
confirming it.

---

## Read first, in this order

1. `docs/data-layer-progress.md` — the authoritative state: what is done, what
   is next, the migration order, the findings log, the decisions log, and the
   per-file procedure as actually executed. **Start here.**
2. `docs/data-layer-design.md` — the diagnosis and constraints. Read before any
   design call.
3. `coding/drive_doorway.py` — the module docstring explains the doorway and
   the choices behind it.

`docs/data-layer-implementation-plan.md` is the phase spec; consult it when the
progress doc points you there.

## Constraints that matter most

- **No live Drive writes.** `capture-drive-state` (read-only) is the only
  permitted live call before Phase 9.
- **Adam is annotating.** His data must not change. `coded_data/` must be clean
  before you start and clean when you stop.
- **In the throwaway harness, make every unshimmed route to Google raise.**
  Patching `coding.drive._get_clients` is not enough for a command that did
  `from .drive import _get_clients` — that binding lives in the command's own
  module. The harness reached live Drive once for exactly this reason; see the
  2026-08-02 decisions-log entry.
- **Never normalise or hand-edit anything under `tests/fixtures/drive_state/`.**
  Those are recorded responses and their exact shape is load-bearing. Re-run
  the capture instead.
- **Watch for `_save_drive_config` in the file you are migrating.** It must be
  patched in tests — the real `drive_config.json` holds live IDs, and a test
  that clobbers it breaks access to the coordinator's own Drive.

## How to work

*(This section documents the per-file method Phase 0b/1 used, now finished.
Kept as reference — the reasoning about evidence order and where bugs hide
outlives that one phase — not as a live instruction with a next file to
apply it to.)*

- Use the per-file method written up in the progress doc: drive the unmigrated
  code from a stand-in Drive through shims, capture its output and its Drive
  changes, migrate, run the same thing again, and diff. Only then capture
  snapshots. The shims are per-file throwaways and stay in the scratchpad.
- Evidence order: mechanical pre/post diff first, property assertions second,
  human review last and only on a rendered digest
  (`tests/render_mutations.py`). A pre/post diff cannot catch a fake that is
  wrong the same way on both sides — assertions that state the command's
  *promise* are what catch that class.
- Commit at every file boundary, updating `docs/data-layer-progress.md` in the
  same commit. Push after every commit.
- `tests/test_doorway_coverage.py` derives which files are left and checks the
  counts stated in the progress doc. Update its `_REMAINING` list and
  `coding/CLAUDE.md` in the same commit as the migration.
- Run `pytest` with `run_in_background`.
- When a snapshot reveals odd behaviour, record it in the progress doc's
  Findings rather than fixing it in the same change — but **the deferral
  expires when that file's migration is committed**, not when the migration
  ends. Fix it then, as its own commit, with the snapshot diff as the evidence.
  Small fixes otherwise happen on sight.
- Read the language rule in `CLAUDE.md` before writing anything a person will
  read. Plain words; a new term only when the project has no word for the
  concept.

## Scale, so the count does not mislead (Phase 0b/1 reference — now finished at 18 of 18)

The order was smallest-and-safest first, so "N of 18" flattered the progress
for most of the effort. Recompute rather than trusting any written number if
this is ever relevant again: the command is in `tests/test_doorway_coverage.py`
(`_DIRECT_ACCESS` over `coding/*.py`, minus `_EXEMPT`) — it should now report
zero remaining. The largest three files were deliberately last.
