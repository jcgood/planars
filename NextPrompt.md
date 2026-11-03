# Next session

Standing prompt for resuming work in a fresh Claude session. Open a new session
and say: **"Read NextPrompt.md and carry on."**

**This file holds no state.** What is done, what is next, and why lives in
each plan's progress doc and in the issue tracker, which own those facts. The
table below is a map to them: one line per plan, kept to what fits on a
screen. The one thing here that needs editing between sessions is the *Now*
section. Everything else is standing instruction and should change rarely. If
you find yourself writing a paragraph of status here, it belongs in the
progress doc or issue instead: a second description of the same fact is the
exact defect this project is trying to remove.

**Before telling Jeff where something stands, open the owner the table
names.** The data layer's plan has Phases 0–11 and Phase 10 has its own
units 1–20; don't answer from this table alone.

---

## Now

**Next (2026-11-03):** the laminar plan is done (Phase 5, 2026-11-03); next
there is the legend fix under "To fix" in the progress doc's Findings.
**Check** the first scheduled weekly analysis (Sunday 2026-11-08): it will
re-analyse each language once, because the chart-code fingerprint changed
form on 2026-11-03 (docs no longer count as code); the Sunday after, with no
span change, it should analyse nothing. Tomorrow's contributor charts
likewise redraw once.

| Plan | Owner of its state | Where it stands | Next | Waiting on |
|---|---|---|---|---|
| Laminar analysis on English | `docs/laminar-analysis-plan.md`, `docs/laminar-analysis-progress.md` | Phases 1–5 done (5 on 2026-11-03) | the legend "To fix" in Findings | — |
| Data layer (#271) | `docs/data-layer-implementation-plan.md`, `docs/data-layer-progress.md` | Phases 0–9 done; Phase 10's units 1–20 all built; unlabelled Drive targets refused (2026-11-02) | enforce notes Docs and reports after their first clean real write (the rest are in `drive_door.LIVE_ENFORCED_KINDS`); Q4 (notebooks shared by name only) untested live | Adam: #332 (decision backfill; then `--apply` it and move `decisions.CHECK_FROM` back) |
| Data layer Phase 11 (research logic as a spec) | implementation plan § Phase 11 | not started; worked examples in `tests/span_examples/` | design pause with Jeff | #321 finished (0 of 7 classes) — don't propose starting it |
| Span-rule review with Adam | #321; coordinator guide § "Reviewing a span rule with the domain expert" | 0 of 7 classes | review each `Span rule: {class}` pull request as it arrives | Adam |
| Chapters from the annotation | `docs/chapter-generation-plan.md` | Phases 1–6 built; synced with Overleaf | Phase 7 (Word); one Overleaf project per chapter when a second contributor comes | the plan's "Open with Jeff" |
| Adam's English requests | #318 (and #322, #319, #314) | (a)–(d), (f), item 6 done | build the impossible-pairs plan (point 8) once he agrees | Adam: point 8, the (b) questions, (e) construction descriptions |
| Biuniqueness deviations | #254 (body checklist, 2026-10-11 design comment) | built, on English | — | Adam: span/type review, morphs tab, #298 |
| CCDB charts across languages | `NonCollaborative/docs/CROSS_LANGUAGE_PROGRESS.md` (plan `PLAN_cross_language_charts.md`) | built 2026-09-23 | freeze references for the charts kept; write "what they show" | Jeff's cuts |
| Bundle storage | #333 | full bundles in planars-data for now | move before a third language gets weekly runs | — |

Daily: check the refresh and Sheet validation are green, and any open
`door-violation` issue first (each line is a command bug or a spec gap).

### Settled, don't re-ask

- **Data layer (2026-10-12):** light maintenance beats speed; a registry
  only if the code runs from it; no `[y, n]` default; sharing by name
  only; planar/diagnostics = reviewed source + locked copies + one
  proposal sheet per language, reviewed by issue + `accept-proposal` (not
  git pull requests); the daily refresh is one command. Unit designs'
  § 7 answers (drive-door, ownership, plain-record, change-log,
  result-stamp design docs) are settled too.
- **English phrasal_accent (2026-10-27):** answers Adam's Claude filled are
  marked "Claude draft (Adam, 2026-10-27)" in Source, for Adam to replace as
  he checks; one Example column ("shared: … | independent: …"); `untestable`
  allowed for joint_accent (#232); the three coreference pair tabs have 38
  pairs each at v:obj-R. The repair is `migrations/repair_phrasal_accent_stan1293.py`.
- **Biuniqueness (2026-10-11, #254):** contractions count as allomorphs;
  `members` on a filled `y` row lists its variant forms; open categories
  list known/suspected members only; the Sheet owns these facts; no
  separate import command; `Morpheme` not `Element`; one row per (form,
  position).
- **Laminar:** plan decision 6 (charts to contributors by workflows on
  Drive); Jeff's cross-language cuts go between phases, not during one.
- **Chapters:** the plan's "Decisions" (2026-10-25).
- **Araona (arao1248) is a trial only:** don't propose expanding it.

### Things that will bite

- **A full bundle re-export needs all four permutation tests**, or the tables
  left un-asked-for drop out of the bundle. `python -m laminar charts
  <dataset> --apply` passes all four (5000 draws); nyan1308 takes ~11
  minutes, all 21 CCDB structures (`--ccdb`) ~8.
- **Redrawn PDFs always show as modified**: R stamps the date in each, and
  the Quartz-drawn ones (IPA labels) differ in internal details too. Compare
  as images before committing; if the pictures are identical, restore the
  committed PDFs with `git checkout`.
- **After any re-export, `git status` on `results/chart_data/<dataset>/` is the
  check that matters.** Every committed bundle file should come back
  byte-identical except what you meant to change. That settles in seconds what
  the 9-minute suite samples, because unchanged inputs plus untouched shared
  code means unchanged charts by construction.
- **`R CMD INSTALL` runs once per check**, so the full suite is ~9 minutes and
  the renderer test alone ~2.5. The renderer test compares all 137 charts in
  one pass, so it is usually the one worth running.
- **If the Python suite slows down sharply, profile one slow test first**
  (`python -m cProfile -o out.prof -m pytest <one test>`). On 2026-10-17 it
  had gone from ten minutes to an hour because one schema file was parsed a
  thousand times per test; one cache fixed it (unit 20).
- **Run the *full* suite before pushing, not one test file.** Saved command
  outputs and the warning-print check catch changes far from the file you
  edited.
- **Adam's clone must be pulled before his Claude runs the tooling**, or it
  writes retired files back (the diagnostics TSV). Install the planars-data
  hook in his clone with his next pull (`../.venv/bin/pre-commit install`
  inside `coded_data/`).
- **The tooling's state files are in `coded_data/.state/`** and every
  command commits and pushes them itself. A machine that ran the tooling
  before 2026-10-20 has old copies at the repo root (untracked in
  `git status`): run `python migrations/move_state_into_planars_data.py --apply`
  once there.
- **Tests use a placeholder annotator email** (`tests/conftest.py`); real
  addresses live only in planars-data's `people.yaml`.
- **Jeff runs parallel sessions.** Anything uncommitted you did not write may
  be another one's work in flight: do not commit it and do not revert it, stage
  your own files by name, and ask whose it is.
- **During live Drive work, push each `coded_data/` commit at once.** The
  daily refresh (cron 06:00 UTC; GitHub's delay means it starts ~10–12 UTC)
  runs from what is on GitHub; on
  2026-10-13 it ran mid-session against unpushed YAML edits, pushed the old
  YAMLs back onto two diagnostics Sheets, and filed four false issues (one,
  #305, would have had `prune-manifest` archive a brand-new sheet).
- **The command tests' saved data lives in planars-data**, at
  `coded_data/.test_fixtures/` (moved there 2026-10-10). If `coded_data/` is
  behind, those tests *skip* rather than fail, so a green local run can be
  hollow: pull `coded_data/` first. Change that data only with
  `python -m coding capture-drive-state --apply`, never by hand.
- **An untracked or modified file under `planarsviz/` (now at the repo root) jams the roxygen
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
