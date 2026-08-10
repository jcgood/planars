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

**Data layer migration (#271), Phase 0b/1 is complete** (finished 2026-08-04,
`restructure_sheets.py` — file 18 of 18 — was last). Every command in
`coding/` that reaches Google now goes through the doorway;
`tests/test_doorway_coverage.py` confirms this with an empty `_REMAINING`.
There is no next file to migrate.

The migration also left three specific bugs behind (Findings 13, 15, 17) and
one blocked cleanup issue (#276, collapsing the duplicated Drive helpers).
All four are now fixed/closed too (2026-08-05) — see the decisions log and
Findings section in `docs/data-layer-progress.md` for what changed. Nothing
outstanding from Phase 0b/1 remains.

**Phase 3 ("Schema reorganization") is also complete** (2026-08-10):
`schemas/diagnostic_classes.yaml` now holds linguistic content only; a new
`schemas/diagnostic_classes_status.yaml` holds process/tracking state,
joined by class `name` and merged transparently by
`coding/schemas.py`'s `load_diagnostic_classes()`. `Class_Type`
(`schemas/planar.yaml`) is catalogued as the resistant field the plan
anticipated, not split. See `docs/data-layer-progress.md`'s 2026-08-10
Current state and decisions-log entries for what changed, and issue #271's
2026-08-10 comment for the coordinator-facing summary.

**Findings 18 and 19 (found while verifying the split) are also fixed**,
same day, in their own commits after Phase 3's. 19 was the consequential
one: a required-class check had never fired since it was written (compared
`collection_required` against the Python bool `True`, but the field is
always a string), and fixing it surfaced that **`arao1248` was genuinely
missing three required classes** — `nonpermutability`, `free_occurrence`,
`proform`. Two of those three are now onboarded (2026-08-10):
`nonpermutability` and `free_occurrence` are both universal classes with
fixed, language-independent criteria, so no linguistic judgment call was
needed. **`proform` is still outstanding** — it's construction-specific,
and nothing in the repo says what construction (if any) fills it for
Araona; that's now issue #279, addressed to Adam. `integrity-check` keeps
reporting `proform` missing until it's answered, and `import-sheets` /
`sync-diagnostics-yaml --to-sheet` still skip arao1248's diagnostics until
then — but a missing required class no longer blocks the local TSV
(`sync-diagnostics-yaml --apply` with no `--to-sheet`) from picking up
whichever classes *are* ready, which is what let the first two go in
without waiting on #279. See `docs/data-layer-progress.md`'s Finding 19
entry for the full account, and its Findings 20/21 for the two bugs this
onboarding pass found and fixed along the way.

**Next up is Phase 4 of `docs/data-layer-implementation-plan.md`** ("Topology
declaration"), which the plan marks **"(coordinator decides authority)"** —
starting it requires a decision from Jeff first, not an agent's guess at
what the authority assignments should look like. Read
`docs/data-layer-progress.md` § "Next action" for the current state of that
gate before doing anything else on this effort.

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
