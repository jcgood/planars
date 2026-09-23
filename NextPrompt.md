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

### Next action: the CCDB plan's step 4

All 21 CCDB structures, as a loop over the one-language command
(`python scripts/planarsviz_language.py <Planar_ID> --apply`, step 3a),
writing one summary of what failed, was skipped, or looks odd (plan §3
"Step 4").

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
- **Jeff runs parallel sessions.** Anything uncommitted you did not write may
  be another one's work in flight: do not commit it and do not revert it, stage
  your own files by name, and ask whose it is.
- **An untracked or modified file under `planarsviz/` jams the roxygen
  pre-push guard.** Check the guard passes on its own rather than reaching for
  `--no-verify`, which has silently disarmed it before.
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
