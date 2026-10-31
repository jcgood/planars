# Next session

Standing prompt for resuming work in a fresh Claude session. Open a new session
and say: **"Read NextPrompt.md and carry on."**

**This file holds no state.** What is done, what is next, and why lives in the
progress doc for whichever work is live — `NonCollaborative/docs/PLANARSVIZ_LIBRARY_PROGRESS.md`
for the chart package, `docs/data-layer-progress.md` for the data layer,
`docs/laminar-analysis-progress.md` for the analysis on English — and
in the issue tracker, which own those facts. The
one thing here that needs editing between sessions is the *Now* section below.
Everything else is standing instruction and should change rarely. If you find
yourself copying a paragraph of status into this file, it belongs in the
progress doc instead — a second description of the same fact is the exact defect
this project is trying to remove.

---

## Now

Eight live threads. Read whichever matches what you're picking up.

**2026-10-27, English phrasal_accent:** Adam's Claude filled the
2,268-row pair tab (1,415 answers) and left the sheet reshaped; repaired
the same day with Jeff's go-ahead (`migrations/repair_phrasal_accent_stan1293.py`
says what was done) and imported. Jeff's decisions the same day (don't
re-ask): answers marked "Claude draft (Adam, 2026-10-27)" in Source, Adam
asked to replace it as he checks; one Example column ("shared: … |
independent: …", in the class's instructions); `untestable` allowed for
English joint_accent (#232); the three coreference pair tabs rebuilt (38
pairs each at v:obj-R). **Waiting on Adam (#318):** his OK on the
impossible-pairs plan (point 8: a "can host" prescreening column for
coreference; for phrasal accent, whether the 704 blank both×y pairs are
impossible and whether v:npsubj1 is the only always-filled position),
then build it; and how his Claude opens the Sheets (three link shares so
far), then point it at signing in as him.

### Thread: tabs marked ready-for-review (2026-10-26)

Jeff's rule: a tab with every cell answered and no errors is ready for
review. The daily check marks it (`validate_coding.looks_finished`), the
Status tab's Marked by column records who marked each ready tab
(annotator, coordinator, check), and a comment on the language's
`needs-fixing` issue @-mentions the coordinators and the owner
(`people.yaml`). `set-tab-status` is for any other case. **Next action:**
check the next Sheet validation run (09:00 UTC) and refresh are green and
that the coordinators' comment appears when a tab is marked. Adam's
request (ii), relayed by Jeff, was the biuniqueness morphs tab: built
2026-10-26, done.

### Thread: generating the chapters' data-driven parts (2026-10-25)

Jeff wants chapters written from the annotation (an introduction, one
chapter per language, results), with what can be generated generated and
kept current as the annotation changes; LaTeX now, Word authors later.
**Plan: `docs/chapter-generation-plan.md`** (nothing built). Jeff answered
its five decisions (2026-10-25; the plan's "Decisions" — don't re-ask): De
Gruyter, class-neutral fragments; a private GitHub repo; a sentence per
test plus tables; structured examples for every language but English (a
per-language field, not a coded exception); mixed authorship.
Phases 1–6 are built (2026-10-25; the plan's "as built" sections):
`python -m coding build-chapters` writes the volume into
`coded_data/.papers/` through the local-file door (outline, fragments,
values, prose stubs the door never overwrites), pins each language
chapter (`data.lock`; `--update` moves it and reports) and checks
`\claim`s; `--check` runs in the daily refresh and files a
`chapter-behind` issue per chapter (Phase 5); examples are structured per
language (`examples: glossed|unglossed` in languages.yaml; Araona's sheets
got Gloss and Translation live 2026-10-25, Adam told on #326) and printed
through the venue file `chapters/venues/book.sty` (Phase 6). `.papers/`
is built and pushed, and synced both ways with Jeff's Overleaf project
by `sync-overleaf` (the plan's "Overleaf" section; first sync
2026-10-25; the `OVERLEAF_TOKEN` secret is set). One shared project is a
stopgap while it is only Adam and English: one project per chapter is
planned (the plan's "Overleaf" section). **Next action:** Phase 7 (Word),
or the per-chapter projects when a second contributor comes. Open
with Jeff: where annotators' drafts live, and @-mentioning a chapter's
annotator on `chapter-behind`. (The 2026-10-26 refresh's `chapters` and
`overleaf` steps were clean.) Still waiting on
#318 (e) (construction descriptions), laminar plan 4d (the permutation
tests) and #321 (span rules).

### Thread: the laminar analysis on English, for a paper (2026-10-24)

The Chichewa/CCDB analysis and charts move out of `NonCollaborative/` into
the main repo and run on any planars language, English first. **Plan and
Jeff's decisions: `docs/laminar-analysis-plan.md`** (don't re-ask them);
**state: `docs/laminar-analysis-progress.md`**. Phases 1–3 done
(2026-10-24): the analysis is `laminar/` at the repo root
(`python -m laminar charts <dataset>`), with `planarsviz/` and renv beside
it; `laminar/planars_language.py` builds English's eight datasets
(`stan1293_<types|classes>_<all|complete|partial|distinct>`) with *k of n*
weights. Phase 4 was revised (2026-10-24, Jeff): charts reach contributors
through Drive by workflows (daily reality checks without permutation
tests, by class and by domain type; weekly full analysis with them; R on
the runner) — plan decision 6. 4a (local) is built; English is drawn
locally in `coded_data/.analysis/stan1293/charts/` (not committed).
4b, `python -m coding laminar-charts`, is built (2026-10-24; progress doc
"4b as built"). 4c, the workflow `laminar-charts.yml`, is built and
live (2026-10-25; "4c as built"): the first run drew all three languages,
put the PDFs on Drive and linked them on each status sheet. The `charts`
Drive kind is enforced since 2026-10-27 (clean writes on 2026-10-26).
A daily run draws nothing when no span changed (checked 2026-10-27: all
three "up to date"). **Next action:** 4d, the weekly full analysis.
Don't re-ask decision 6's choices. Jeff's cuts to the cross-language
charts (CCDB thread below) come after Phase 2 (his call, 2026-10-24), so
they can go in now or between later phases, not in the middle of one.

### Thread: reviewing the span rules with Adam (Jeff told Adam, 2026-10-22)

Adam and his Claude agree each class's span rule. His Claude writes it into
the YAML on a branch and opens a pull request. Our side then makes the code
match, stamps the hash and merges. The procedure is coordinator guide
§ "Reviewing a span rule with the domain expert". The order, the checkboxes
and the known questions for each class are in the tracking issue #321. Jeff sent Adam the
prompt for his Claude (2026-10-22). **Next action:** review each `Span rule: {class}`
pull request as it arrives, following the 7-step workflow on its branch.
Unblocking the later classes: #318 (b), (c) and (d) are done (2026-10-23).

### Thread: Adam's English coding requests (#318)

**State lives in #318** (his 13 points, and the comment with Jeff's
decisions, 2026-10-22). Approved, in order:
(a) shorten the text the tooling writes for annotators — done
2026-10-22 (needs-fixing issue and sheet comment, proposal issue, Last
review, sheet-updates issue and comment; the live proposal_stan1293's
Last review tab keeps the old text until its next review or a rewrite);
(b) dependent-on-left/right take a `|`-separated list meaning "any one of
these" — done 2026-10-23 (a comma is refused with "write 3|4", per his
§ 5; `planars/position_cells.position_numbers`). Adam told on #318
(2026-10-23), with three questions: 31 vs 30 in his pronoun rows, the
object pronouns' free value (noninterruption n, free_occurrence y), and
whether "any one" is per side or across both columns (left for the
free_occurrence span-rule review, #321);
(c) pre-fill referential=y for `NP{…}` rows in coreference prescreening
(not pronouns) — done 2026-10-23 (`prefill_by_label` in
diagnostic_classes.yaml; English's five NP rows were already y, so
nothing changed live);
(d) rename the coreference constructions to `reflexive_coreference`,
`pronoun_coreference`, `np_coreference` — done live 2026-10-23 by the new
`rename-construction` command (tabs renamed in place, so the links did
not change); Adam told on #318. The 2026-10-24 refresh should refresh
each coreference sheet's Instructions tab (its text names the
constructions): check it did, and that no empty tab appeared;
(e) a description per construction, shown on its sheet (none exist; Adam's
point 10 is that `vp_ellipsis` doesn't say its proform is Ø). The text
for `vp_ellipsis` is Jeff's call; what the ellipsis tests should be
(point 11, frames A/B, renaming; generic ellipsis; an English V-bar
deletion test) is #319;
(f) Comments cells reach nobody: the collaborator guide invites
questions there, import-sheets copies them, nothing reports them (and the
guide never mentions the notes Doc, the channel check-notes watches).
Done 2026-10-22 (Jeff's decisions: column `Example`, before Source; no
confirmation from Adam): every class sheet has an `Example` column
(`schemas/planar.yaml` `trailing_columns`); the tooling never writes in
Comments (restructure-sheets quotes a split element's old answers in a
cell note); `check-comments` runs in the daily refresh and files one
`collaborator-comments` issue per language with a Claude prompt; and
`migrations/sort_comments_into_example.py` cleared the 284 tooling notes
and moved 86 examples, leaving Adam's 32 questions and notes. The first
`collaborator-comments` issue is #322 (2026-10-23). Sorted that day:
several comments came from the sheets' dropdowns still offering the y/n
list removed 2026-10-12 (no both/na/unclear; a typed position number
shown as invalid). Fixed in code the same day: `refresh-dropdowns` now
compares each sheet's real dropdowns with the codebook and runs daily.
Applied live the same day (every language's sheets now match). **Next:**
(2) Adam's answers on #318 to the (b) questions, and his retyped rows;
(3) reply posted on #322, 2026-10-23 (asks which elements QWORDS
splits into); (4) definitions to
tighten: vp_ellipsis's test (#319), flapping and `multiple` (#321);
(5) QWORDS split, his OK on the new elements;
(6) a pink cell says nothing about what is wrong (warnings on in-progress
tabs reach the annotator only as pink; 2026-10-24, Jeff asked): put the
issue's message in a note on the cell (`validate_coding.highlight_cells`).
Mind that restructure-sheets already writes cell notes (a split element's
old answers), so clearing must remove only validate-coding's own notes, and
the class-sheet spec in `sheet_spec.py` (enforced live) must allow them.
Asked of Adam on #319 (2026-10-24): what the four `vp_ellipsis` cells
with two values (`y/unclear`, `both/unclear`) mean.
Also open, linguistic: displacement, the one standard constituency test
with no class (#56; English is its data, Adam to write the frames).
Not now: 8 (drop impossible pairs), 10–12 (proform frames, the
host-only inflection); 13 is Jeff's to answer. (Audit
#313 and #315, sync-params editing the YAML, are closed, 2026-10-18.)

### Thread: data layer Phase 10 — ownership and chokepoints (`coding/`, `schemas/`, #271)

**State lives in `docs/data-layer-progress.md`** (Status by unit, Phase 10
row); the spec, ground rules, units and order are the Phase 10 section of
`docs/data-layer-implementation-plan.md`. Approved to run unattended
**except at the pauses and live steps the spec names.** Designs: unit 5 in `docs/drive-door-design.md`, units 6 + 15 + 11 in
`docs/ownership-design.md` (both answered by Jeff in their § 7 — don't
re-ask).

**2026-10-24 (Jeff): 11b's first part is done and live** (progress doc,
Phase 10 row; ownership-design § 6 step 6): the planar and diagnostics
Sheets are read-only, protected copies; `import-planar` is now
`sync-planar`; apply-pending, `--from-tsv` and their issues are retired.
Jeff dropped the wait for Adam to use a proposal sheet and the issue to
him — don't re-ask. Check the 2026-10-25 refresh: green, its `planar`
step says "up to date" for all three languages, and no step protects a
Sheet again. **11b's second part is done (2026-10-27):** the diagnostics
TSV is deleted and every reader reads the YAML; `sync-diagnostics-yaml`
pushes to the Sheet only (`--to-sheet` retired). Check the 2026-10-28
refresh: green, its "diagnostics sheet" step clean, and no
`diagnostics_*.tsv` back in planars-data (check-codebook check 7). Adam's
clone must be pulled before his Claude runs the tooling, or it writes the
TSV again (the 2026-10-28 refresh was green and no TSV came back).
**11d is done (2026-10-28):** the Instructions sentences are in planar.yaml's
`sheet_text`. **11c is done (2026-10-29;** as-built in
`docs/ownership-design.md` § 6 item 7): Jeff's two live tests passed, the
notebooks find their sheets by label, the manifest is gone. The 2026-10-30
refresh was green, its `notebooks` step clean, no `door-violation`; its
#331 (the test share on synth0001) was fixed after it ran and closes at
the next refresh. The "manifest" names are renamed (2026-10-30;
progress doc, Phase 10 row). **Next:** check the 2026-10-31 refresh
(its `labels` step creates `stale-class-sheets`; its `stale sheets` step
clean; no `label-drift`). **Unit 16 is designed** (2026-10-30,
`docs/plain-record-design.md`; Jeff answered its § 7 the same day, don't
re-ask). 16a, 16b (2026-10-30) and 16c (2026-10-31: the change log's
*edited by* column) are built; the 2026-10-31 refresh made the records
files. **Next:** check the 2026-11-01 refresh is green and its change-log
lines for imported files fill *edited by* (Adam's name when he edited;
empty when only the tooling did); then build 16d (Drive comment threads:
`list_comments` already returns authors and replies, nothing calls it
yet), then 16e. Where it stands is the progress doc's Phase 10 row. Then 17–18. The live tests' share to Jeff's
second account came off the synth0001 folder and synth0001 was recaptured
(2026-10-30, `migrations/remove_synth0001_test_share.py`). Q4 (notebooks shared
by name only) is still open: test 1 ran with the link share on. Adam's
clone must be pulled before his Claude runs the tooling.

**Where it stands:** class sheets are enforced live (2026-10-19, Jeff;
`drive_door.LIVE_ENFORCED_KINDS`); every other kind now has its spec and is
in watch (5f's last two steps, notes Docs and files, done 2026-10-19;
design doc § 8). The 2026-10-19 refresh (11:59 UTC) ran before all of
that, so the **2026-10-20 refresh is the first to check**: green, and a
write the door now refuses shows as a failed step and its issue, not a
`door-violation`. A `door-violation` from it on a watched kind (the new
rule 8 especially) is a command bug or a spec gap to fix.

**Next action:** check each day's refresh (green, no `door-violation`,
the `overwrite` step now says how many changes it checked) and enforce
each kind in watch once it has had a clean real write (below). The
2026-10-23 refresh was the first with the proposal step and the local-file
door enforcing: both clean. Unit 9 is done (2026-10-23). 11c is done
(2026-10-29), the "manifest" renames (2026-10-30); next 16–18.

**Waits on watching:** enforce for each kind still in watch (planar
Sheet, notes Docs, notebooks, reports, folders: its own first
clean real write, then added to `LIVE_ENFORCED_KINDS`; class sheets,
status sheets, the diagnostics Sheet and charts are enforced), and refusing
unlabelled targets (last). Notebooks now get a real write every day (the
refresh's `notebooks` step), so they can be enforced after a clean week.
**11a is live** (2026-10-22); 11b done (2026-10-24, 2026-10-27); 11d done
(2026-10-28); 11c done (2026-10-29).

Check for an open `door-violation` issue first: each line is a command bug
or a spec gap to fix.

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
(2) filling the morphs tab (built 2026-10-26, 132 rows, after morphemes
was marked ready-for-review for him with `set-tab-status`). Adam was told
on #318 (2026-10-22). Positions may be typed as numbers since 2026-10-22
(`planars/position_cells.py`; sync-planar renumbers them when the
planar's numbers shift); (3) #298 (what `-n` at
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

**The analysis and charts now run from anywhere** (`python -m laminar ...`;
the renderer from the repo root). A bundle records its inputs relative to
the repo root, so where you run it no longer changes the bundle. The porting
checks still run from `NonCollaborative/`.

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
