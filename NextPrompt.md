# Next session

Standing prompt for resuming work in a fresh Claude session. Open a new session
and say: **"Read NextPrompt.md and carry on."**

**This file holds no state.** What is done, what is next, and why lives in the
progress doc for whichever work is live — `NonCollaborative/docs/PLANARSVIZ_LIBRARY_PROGRESS.md`
for the chart package, `docs/data-layer-progress.md` for the data layer — and
in the issue tracker, which own those facts. The
one thing here that needs editing between sessions is the *Now* section below.
Everything else is standing instruction and should change rarely. If you find
yourself copying a paragraph of status into this file, it belongs in the
progress doc instead — a second description of the same fact is the exact defect
this project is trying to remove.

---

## Now

Three live threads. Read whichever matches what you're picking up.

### Thread: data layer Phase 10 — ownership and chokepoints (`coding/`, `schemas/`, #271)

**State lives in `docs/data-layer-progress.md`** (Status by unit, Phase 10
row); the spec, ground rules, units and order are the Phase 10 section of
`docs/data-layer-implementation-plan.md`. Planned with Jeff 2026-10-12 and
approved to run unattended **except at the pauses the spec names** (unit 5
design; units 6+15+11 design). Units 14 (but one by-hand step), 4, 7, 3's
first group, 1 and 2 are done; next is unit 10 (one GitHub issue path), then
the unit 5 design pause.

**Don't re-litigate (decided 2026-10-12):** light maintenance beats speed; a
registry only if the code runs from it; no `[y, n]` default; close the
hidden-facts inventory rather than track it; sharing by name only;
planar/diagnostics = reviewed source + locked copies + one proposal sheet per
language, reviewed by issue + `accept-proposal` (not git pull requests —
versioning must not depend on git); the daily refresh becomes one command.

### Thread: biuniqueness deviations (`coding/`, `planars/`, issue #254)

**State lives in issue #254** — read its body checklist and the 2026-10-11
design comment first. On 2026-10-11 allomorphy became part of one class,
`biuniqueness_deviations` (extended exponence, allomorphy, cumulative
exponence, zero morphs; type derived, never annotated), run through the
ordinary pipeline. Built and live: `planars/biuniqueness_deviations.py`,
`coding/biuniqueness_rows.py` (the three-tab chain and `keyed_rows`). On
2026-10-13 the class moved to English (Phase 10 unit 1): the class sheet is
https://docs.google.com/spreadsheets/d/1Xz8_4aMFr4xfkNrlomiURODtbUuFFEmkMTr9WO6_5aI
with Adam's 18 answers, its first tab is `elements` (was `prescreening`),
and synth0001's copy is archived read-only.

**Next action:** waiting on Adam — (1) review of the span definition and type
rules (#254 design comment; the class stays `[AUTO-DERIVED]` until he does);
(2) finishing the elements tab and marking it ready-for-review; the daily
refresh then fills the empty morphemes tab by itself (and morphs, once
morphemes is marked) — check it did; (3) #298 (what `-n` at
`v:frontedauxiliaryinflection` is — fronted *won't* waits on it).

**Don't re-litigate (settled 2026-10-11, see #254):** contractions count as
allomorphs; `members` on a filled `y` row lists its variant forms; open
categories list known/suspected members only; the Sheet owns these facts
(not coordinator-edited tables); no separate import command; `Morpheme` not
`Element`; one row per (form, position).

**Don't re-litigate:** Araona (arao1248) is a trial only, not a priority —
this thread stays scoped to English (stan1293). Don't propose expanding
arao1248's coverage as part of this work.

### Thread: CCDB charts across languages (`NonCollaborative/`)

**Current work: `NonCollaborative/`, putting the CCDB languages through the
planarsviz charts.** State lives in
`NonCollaborative/docs/CCDB_PLANARSVIZ_PROGRESS.md` — read it first; the plan
it follows is `NonCollaborative/docs/PLAN_ccdb_planarsviz.md` (§6 holds Jeff's
decisions, §7 which parts go to Sonnet subagents). The chart package itself
is finished; its record is `PLANARSVIZ_LIBRARY_PROGRESS.md`, and how to use
it is `planarsviz_guide.md` and `planarsviz_charts.md`.

**Everything under `NonCollaborative/` runs from `NonCollaborative/`.** This
matters for the exporter specifically: it records the domain file's path as
given, so running it from the repo root writes a bundle that differs from the
committed one in that field.

### Next action: charts and summaries across languages

The CCDB plan's steps 1–5 are done (see "Step 5 as built" in
`CCDB_PLANARSVIZ_PROGRESS.md`). Jeff has asked for charts and summaries that
set all 22 structures side by side (2026-09-23). The plan is
`NonCollaborative/docs/PLAN_cross_language_charts.md` (six proposed charts
and a summary table, each tied to one of the three hypotheses); state is
`NonCollaborative/docs/CROSS_LANGUAGE_PROGRESS.md`. Jeff has answered the
plan's four questions, and the bundle, charts and summary table are built
(2026-09-23). **Next: Jeff's cuts to the charts in
`results/cross_language/`**, then freeze reference images for the ones he
keeps and write the "what they show" page. The progress file has the first
reading of results and the decisions made while building.
A bug with one obviously right fix is not a question: fix it and report it.

### Things that will bite

- **A full bundle re-export needs all four permutation flags together** —
  `--fragmentation-permutations 5000 --boundary-strength-test-permutations 5000
  --span-placement-permutations 5000 --arbitrary-layers-permutations 5000` —
  or the tables left un-asked-for drop out of the bundle. It takes ~11 minutes.
- **After any re-export, `git status` on `results/chart_data/<dataset>/` is the
  check that matters.** Every committed bundle file should come back
  byte-identical except what you meant to change. That settles in seconds what
  the 9-minute suite samples, because unchanged inputs plus untouched shared
  code means unchanged charts by construction.
- **`R CMD INSTALL` runs once per check**, so the full suite is ~9 minutes and
  the renderer test alone ~2.5. The renderer test compares all 137 charts in
  one pass, so it is usually the one worth running.
- **Run the *full* suite before pushing, not one test file.** Saved command
  outputs and the warning-print check catch changes far from the file you
  edited.
- **Tests use a placeholder annotator email** (`tests/conftest.py`); real
  addresses live only in planars-data's `people.yaml`.
- **Jeff runs parallel sessions.** Anything uncommitted you did not write may
  be another one's work in flight: do not commit it and do not revert it, stage
  your own files by name, and ask whose it is.
- **During live Drive work, push each `coded_data/` commit at once.** The
  daily refresh (scheduled ~13:28 UTC) runs from what is on GitHub; on
  2026-10-13 it ran mid-session against unpushed YAML edits, pushed the old
  YAMLs back onto two diagnostics Sheets, and filed four false issues (one,
  #305, would have had `prune-manifest` archive a brand-new sheet).
- **The command tests' saved data lives in planars-data**, at
  `coded_data/.test_fixtures/` (moved there 2026-10-10). If `coded_data/` is
  behind, those tests *skip* rather than fail, so a green local run can be
  hollow: pull `coded_data/` first. Change that data only with
  `python -m coding capture-drive-state --apply`, never by hand.
- **An untracked or modified file under `planarsviz/` jams the roxygen
  pre-push guard.** Check the guard passes on its own rather than reaching for
  `--no-verify`, which has silently disarmed it before.
- **R's cairo devices don't work on this Mac** (they need XQuartz, and fail
  with only a warning). The renderer uses Quartz for charts with IPA; don't
  reach for `cairo_pdf` here.
- **R does not go into the CI image.** The porting checks pixel-compare against
  Mac-rendered references and Linux fonts differ, so they stay a local gate.
  Don't reopen this.

### Recently finished, so don't redo it

The `results/` restructure and all of absorption (2026-09-20/22). Nothing under
`NonCollaborative/` writes a chart into `results/` except
`render_planarsviz.R`; the renderer check reports "references with no render:
none". Four permutation tests now exist — fragmentation, span placement,
boundary strength, arbitrary layers — each integrated the same way: a
`run_test()`, an exporter flag, bundle tables, a chart, a contract entry and a
bundle invariant test. Three superseded scripts are archived behind the
`OlderFiles/` run guard and must not be deleted or run.

Two numbers worth not misquoting: the arbitrary-layers test's pooled result is
`P(chance <= 69) = 0.2866`, not the scratch's 0.4380, which asked about 25
layers where nyan1308 has 26. And its per-group breakdown is the interesting
part — syntax-like p=0.014, morphosyntactic p=0.044. Separately,
`scripts/exploratory/max_fragmentation_search.py`'s 1238-family figure is still
at the old 25-layer count and has not been re-derived.
