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

**Phase 7 ("recoverability for multi-step operations") is in progress —
both `restructure-sheets` units done, as of 2026-08-17.** `restructure-sheets
--apply`'s main per-class loop (unit 1) and its separate `--rename-class`
archive sequence (unit 2, same day) both journal their progress
(`coding/restructure_journal.py`) and refuse to start new work while a
class is left mid-flight from an interrupted run, from either sequence;
`--resume`/`--rollback` recover it, with rollback offered only where it's
actually safe (a class archived but not yet replaced — past that point
recovery is resume-forward only, never delete). This closes the plan's own
named #248 example completely for `restructure-sheets`. One open question
for Jeff: whether Phase 7 continues to `generate-sheets`/`import-sheets`
next or moves to Phase 8 (fault-injection stress testing) — see
`docs/data-layer-progress.md`'s Open questions section. Nothing else
blocked.

**Phase 5 is done, all five units, as of 2026-08-17.** No open questions,
nothing blocked. Full detail in `docs/data-layer-progress.md`'s Current
state / Next action / Decisions log / Findings sections.

**Phase 6 ("data contracts at boundaries") is done, all four boundaries, as
of 2026-08-17.** `planars/contracts.py` declares pandera schemas for two
`planars/`-package DataFrame boundaries. Section 1: `planars/io.py`'s
filled-TSV/sheet loader (`_parse_filled_df`, shared by
`load_filled_tsv`/`load_filled_sheet` and all fifteen `planars/*.py` analysis
modules) — the boundary Jeff picked to start with, out of the plan's four
candidates, for its reuse. `pandera` is now a runtime dependency of
`planars/` (in `pyproject.toml`'s `dependencies`, since this loader is
imported by Colab notebooks, not just `requirements.in`). Section 2:
`planars/coreference.py`'s pair-row loader — a thinner fit than section 1
and its coordinator-side sibling below (most bad *values* there are
deliberate warnings, not failures), but real column-presence gaps
(`row.get(col, "")`'s silent `""` fallback on a genuinely missing column)
turned up anyway. `coding/contracts.py` declares one for
`coding/make_forms.py`'s `build_element_index` (planar load) —
coordinator-only, so no Colab dependency question there. Boundary 4,
`coding/manifest_contract.py` (pydantic, not pandera — dict/JSON), is the
one that took real back-and-forth: `load_manifest()` is the
highest-blast-radius function in the project, checkable only against one
static fixture with no live Drive access before Phase 9, so the model is
deliberately far more permissive than the other three and non-blocking on
write — but *does* drive a real, trackable `integrity-error` GitHub issue
via a new `integrity-check` section, resolving "how would I ever find out"
without reintroducing the outage risk. See the 2026-08-17 decisions-log
entry for the full path to that design.

**A side effect of boundary 4's risk discussion: issue #283 and a new
durable test.** Tracing "how would a warning ever get tracked" led to
finding that `.github/workflows/*.yml` only escalates a problem to a
GitHub issue via exit code (never the literal word "WARNING") — a sweep
found five warning-shaped `print()` calls across `coding/` that are
currently invisible in automation, filed as issue #283 with recommended
fixes (not applied — those are workflow changes affecting the safety net
itself, better reviewed than shipped solo). The durable half:
`tests/test_unattended_warning_escalation.py` derives the unattended-command
list straight from the workflow YAML and fails if a *new* orphaned warning
joins the pile unclassified — the actual answer to "how do I stop missing
this", not a periodic manual re-sweep.

**Phase 7 has both `restructure-sheets` units scoped and done (see above);
whether it continues to another command and Phases 8–9 remain unscoped in
session-level detail** — see `docs/data-layer-implementation-plan.md` for
the phase spec.

**Phase 0b/1 (the doorway migration), Phase 3 (schema reorganization), and
Phase 4 (topology declaration) are all complete, nothing outstanding from
any of them.** Phase 0b/1 finished 2026-08-04 (18 of 18 files); Phase 3
finished 2026-08-10; Phase 4 finished 2026-08-16. Every bug either turned up
is fixed; #276 and #280 are closed.

**arao1248's diagnostics gap (surfaced by Finding 19) is two-thirds closed.**
`nonpermutability` and `free_occurrence` are onboarded (2026-08-10, no
linguistic judgment needed — both universal with fixed criteria). `proform`
is still open, waiting on Adam via issue #279 (construction-specific; nothing
in the repo says what fills it for Araona). Not blocking anything else — a
missing required class no longer blocks `sync-diagnostics-yaml --apply`'s
local-TSV direction from picking up whichever classes *are* ready (Finding
20), just `--to-sheet`/`import-sheets` for the language as a whole.

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
