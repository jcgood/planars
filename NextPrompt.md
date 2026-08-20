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

**A CI/workflow-ordering bug traced and fixed 2026-08-20, same session as
#283/#284 below — worth reading before trusting a green local test run
again.** Local `coded_data/` had gone unpulled for 10 days mid-session;
CI always checks out fresh, so it caught real annotation progress
(arao1248's `free_occurrence`/`nonpermutability` data landing for real)
that local runs didn't see, producing 5 CI-only test failures. Pulled,
regenerated those 5 snapshots (all genuine, reviewed, not bugs). Separately,
diagnosing that also traced #289/#290 (both auto-filed by #283's own new
issue-filing, ironically) to a real, pre-existing `data-refresh.yml`
ordering gap — the same shape as #245's already-documented
`coded_data_git_identity_configured` precedent, just on commit-timing
instead of git-identity: `import-sheets` writes to `coded_data/` but
doesn't self-commit, and the workflow's only commit step ran once, near
the very end of the job — so every `coded_data_clean_tree`-gated command in
between (`sync-diagnostics-yaml`, `sync-params`, `generate-sheets
--regen-dependents`) was silently aborting whenever import actually
changed a file, invisible until #283 gave two of those three real
issue-filing. Fixed with a second, earlier commit step right after
`check-notes`; recorded in `data_dependency_schema/preconditions.yaml`.
**Lesson for next time: pull `coded_data/` at the start of a session, not
just when a command complains about it being dirty** — a stale local
checkout won't show as an error, it'll just quietly diverge from what CI
sees.

**#284 and #283, both flagged 2026-08-19 as loose ends, are now closed
(2026-08-19/20, same session that flagged them).**

- **#284** — all 19 unretried structural Drive calls (the issue's own
  grep-based count of 18 undercounted `setup_root_folder.py` by one) across
  `generate_sheets.py`, `generate_status_sheet.py`,
  `generate_biuniqueness_allomorphy_sheet.py`, `setup_root_folder.py`, and
  `prune_manifest.py` are now wrapped in `_with_retry`, each with a
  fault-injection test proving the retry recovers — matching
  `restructure_sheets.py`'s existing Phase 8 treatment.
- **#283** — all four gaps closed, one at a time with Jeff's sign-off on
  each: `sync-diagnostics-yaml`, `generate-sheets --regen-dependents`, and
  `import-sheets` all now exit non-zero on a real (blocking) problem and
  reach a GitHub issue — two via a new `diagnostics-yaml-error`/
  `regen-dependents-error` label, one by reusing the existing `import-error`
  mechanism once its trigger condition was fixed. The two genuinely-cosmetic
  warnings (gap 4) were deliberately left quiet after reading their actual
  content — filing an issue for a style nudge risks the exact warning-fatigue
  failure #260 already taught this project to avoid.
- **Three real, previously-unknown bugs came out of implementing this, all
  fixed in the same passes**: (1) `sync_diagnostics_yaml.py`'s `--to-sheet`
  direction ignored `ValidationIssue.blocking` entirely, so a non-blocking
  gap (a required class not yet drafted) was silently withholding pushes
  that should have gone through — confirmed live: arao1248's diagnostics
  Sheet has been stale (missing `free_occurrence`/`nonpermutability`) this
  whole time as a result. **The next `data-refresh.yml` run will push a real
  change to arao1248's live diagnostics Sheet** to fix this — a live-Drive
  consequence worth watching for, not something run manually this session.
  (2) `validate_diagnostics_df` (the TSV-form validator `import-sheets`
  uses) had the identical `.blocking` gap on its own copy of the same
  required-class check — arao1248's diagnostics Sheet *download* was being
  silently skipped in full every run because of it, confirmed live before
  fixing. Fixed to match. (3) Neither was one of #283's four originally-named
  gaps — both found by tracing the actual code while answering "why," not by
  the original sweep.
- **Still open, not touched this session:** GitHub's Dependabot flagged 1
  moderate vulnerability (WeasyPrint CSS injection,
  [GHSA-jhhc-3hcp-qhm5](https://github.com/jcgood/planars/security/dependabot/13)) —
  already mitigated in code (`planars/html_report.py` pins
  `presentational_hints=False`, the setting the advisory's injection path
  requires), Dependabot just can't see that. Jeff was offered a dismiss with
  reason "tolerable risk"; no answer yet — ask again or just do it next
  session if it's still sitting open.

**A tangent this session (2026-08-18/19) worth knowing about even though it's
unrelated to #271: issue #285, found, fixed, and closed.** Investigating what
looked like leftover #241 fallout on `synth0001` turned up a real, separate
bug: `coreference`'s `referential` filter had the same element-vs-position
exclusion shape issue #228 found for `nonpermutability` back in May — #228's
own closing text had incorrectly claimed coreference was unaffected. Fixed:
coreference's filter now shares #228's divergence guard (abort and file a
`diagnostics` issue instead of silently resolving the ambiguity), and
`integrity-check`'s own coreference staleness check — which had an
independently-wrong approximation, the thing that actually surfaced this —
now matches the real filter instead of a separately-invented one.
`stan1293` has zero divergent elements right now, so no real annotation was
affected; this was only visible in `synth0001`'s synthetic data. Also closed
while cleaning up: **#241** (the original split-cascade problem — done since
2026-08-01, just never closed after the final confirming comment) and two
accidental duplicate issues (**#286**/**#287**) a test run filed against the
real repo before a fixture-neutralization fix landed later the same session.

**Phase 9 ("staged cutover") started 2026-08-18 and is in progress — the
first phase permitted to write to live Drive, after every prior phase
built and tested against a fake.** Step 1 (shadow reads) is done: every
coordinator-only command was run live, read-only, and reviewed — clean
throughout, including two real 429s that recovered on their own (Phase
8's retry fix, confirmed working outside the test suite). That review
surfaced something worth knowing before resuming this: most of the
project already runs live continuously via `data-refresh.yml`/
`sheet-validation.yml`'s daily automation, which has been exercising every
phase of this whole redesign against real Drive the moment each merged —
there was never a separate "old path" to shadow against the way the plan's
generic wording assumes. Step 2 (write cutover) has begun: four real
writes done, each named to Jeff and approved individually first
(`synth0001`'s stale coreference columns removed; `arao1248`'s two
still-missing class sheets created; the orphaned `biuniqueness_stage1_
synth0001` sheet trashed and its replacement `biuniqueness_allomorphy_
synth0001` created). `restructure-sheets`/`prune-manifest` reported nothing
to do, so haven't been cut over to a real write yet — that happens whenever
real project work next calls for either. Full account, including why the
daily-automation finding reframes what "shadow reads" means for this
project specifically: `docs/data-layer-progress.md`'s Phase 9 entries
(Current state, Next action, Decisions log).

**Phases 7 and 8 are both done in full** (2026-08-17–18, same session run
that led into Phase 9). Phase 7: `restructure-sheets` gained real
crash-recovery (`coding/restructure_journal.py`, `--resume`/`--rollback`)
for both its main loop and `--rename-class`'s sequence. Phase 8: real
fault injection proved that recovery survives an actual crash (not just a
hand-set state) and found two real bugs in the process (a permission-loss
bug on rollback, missing retry protection on 429/500/503); a full audit of
every command's idempotency claim in `operations.yaml` found and fixed one
more (`registry.py` caching what it claims is never cached). See
`docs/data-layer-progress.md` for the complete account — not repeated here
per this file's own rule against duplicating status.

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

**Phases 7 and 8 are both done in full (see above). Phase 9 is in progress
(see above) — step 1 done, step 2 ongoing opportunistically, not on a
fixed schedule** — see `docs/data-layer-implementation-plan.md` for the
phase spec.

**Phase 0b/1 (the doorway migration), Phase 3 (schema reorganization), and
Phase 4 (topology declaration) are all complete, nothing outstanding from
any of them.** Phase 0b/1 finished 2026-08-04 (18 of 18 files); Phase 3
finished 2026-08-10; Phase 4 finished 2026-08-16. Every bug either turned up
is fixed; #276 and #280 are closed.

**arao1248's diagnostics gap (surfaced by Finding 19) is two-thirds closed.**
`nonpermutability` and `free_occurrence` are onboarded (2026-08-10, no
linguistic judgment needed — both universal with fixed criteria) and their
Drive sheets went live 2026-08-18 as part of Phase 9's write cutover
(`generate-sheets --lang arao1248 --apply`). `proform`
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

- **Live Drive writes are permitted now (Phase 9, started 2026-08-18), but
  not casually.** Every prior phase's "no live writes, `capture-drive-state`
  is the only permitted call" rule is lifted — but the plan's own Phase 9
  discipline replaces it, not a blank check: read-only checks (dry runs,
  `capture-drive-state`) need no sign-off, same as always; an actual write
  gets named to Jeff individually — which command, which target, why it's
  low-risk — before running, the same way the first two real writes were
  handled. Never batch multiple real writes under one approval.
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
