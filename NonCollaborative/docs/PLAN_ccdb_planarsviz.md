# Plan: drawing the CCDB languages with `planarsviz`

Written 2026-09-22 by Claude (Opus). Not started. The four open questions
were settled by Jeff the same day; see §6.

---

## 1. What we are doing, in one paragraph

The Constituency and Convergence Database (CCDB,
<https://github.com/Constituency-and-Convergence/Constituency-Database>) holds
planar structures and constituency test results for 16 languages of the
Americas. The goal is to give every CCDB planar structure the same analysis and
the same charts nyan1308 gets today: export a bundle with
`scripts/analysis/export_planarsviz_data.py`, draw it with
`scripts/render_planarsviz.R`. Nothing in the analysis or in the R package
should need to know which language it is drawing; where something does, that
is a leak to fix, as the shifted test dataset found before.

## 2. What was established before writing this

Checked 2026-09-22 against the local clone at
`~/gitrepos/Constituency-Database` (commit `e3d5386`).

- **The data files are current.** The clone is behind GitHub by three 2024
  commits (`58587db`, `b489aeb`, `9624ca7`), but those change only analysis
  scripts; `domains.tsv`, `planar.tsv` and `input/` are identical. The clone
  also carries one unpushed commit of Jeff's (`e3d5386` "test update", which
  adds an 8 MB `scripts/Rplots.pdf`). Neither affects this work.
- **463 tests across 21 planar structures** (16 verbal, 5 nominal) from 16
  languages. `planar.tsv` lists 24 structures; only these 21 have tests. Every
  structure with tests has a planar table.
- **Three domain types only:** morphosyntactic (173), phonological (176),
  indeterminate (114). nyan1308 splits these finer (tonosegmental,
  intonational, length), and `indeterminate` is not in `DOMAIN_TYPE_STYLE`.
- **The columns already fit.** CCDB's `domains.tsv` has the `Left_Edge`,
  `Right_Edge`, `Size`, `Domain_Type` and `Test_Labels` columns the exporter
  reads, and every `Size` agrees with its edges.
- **Family enumeration finishes, fast, for all 21.** A throwaway probe split
  `domains.tsv` by `Planar_ID` and ran `count_families()` on each: pooled
  counts from 2 (Araona, Hup nominal) to 40 (San Martín Duraznos Mixtec
  verbal), none taking more than 0.1 s. Nothing was truncated.
- **The root position lives in `input/overlaps.tsv`** (`Overlap_Verbal`,
  `Overlap_Nominal`), not in the planar table's `Elements`. It is missing for
  the one adjective structure; what `Overlap_Verbal_Extended` means (Yupik
  only) is marked "?" in CCDB's own README.
- **Structures run from 12 to 46 positions** (nyan1308: 22).

| Planar_ID | Tests | Positions | Families (pooled) |
|---|---|---|---|
| arao1248_verbal | 19 | 18 | 2 |
| ayau1235_verbal | 30 | 31 | 8 |
| cent2127_verbal | 19 | 21 | 3 |
| chac1251_nominal | 26 | 12 | 4 |
| chac1251_verbal | 38 | 28 | 29 |
| cher1273_verbal | 21 | 24 | 8 |
| dura0000_nominal | 19 | 13 | 5 |
| dura0000_verbal | 27 | 29 | 40 |
| hupd1244_nominal | 12 | 15 | 2 |
| hupd1244_verbal | 15 | 32 | 3 |
| iyoj1235_verbal | 28 | 46 | 22 |
| kaya1330_verbal | 15 | 32 | 7 |
| kiow1266_verbal | 17 | 39 | 5 |
| mart1259_verbal | 12 | 27 | 4 |
| moco1246_verbal | 22 | 20 | 7 |
| siks1238_verbal | 32 | 14 | 31 |
| sout2991_verbal | 20 | 42 | 3 |
| teot1238_nominal | 18 | 20 | 9 |
| teot1238_verbal | 21 | 28 | 12 |
| yucu1253_verbal | 24 | 21 | 7 |
| zenz1235_verbal | 28 | 21 | 5 |

The four structures where the counts are provisional are the ones affected by
step 2.1 below: their position count was taken from the furthest span edge,
not the planar table. Their family counts should not change once the axis is
fixed, since unreached positions add no spans, but recheck.

## 3. The steps

### Step 1: an import script

`scripts/analysis/import_ccdb.py` reads the local CCDB clone and, per
`Planar_ID`, writes (dataset names are the `Planar_ID`, §6.1):

- `domains/domains_<Planar_ID>.tsv` — the rows for that structure, keeping
  CCDB's columns (the exporter ignores the ones it doesn't use). The
  `Test_Labels` column the exporter reads is CCDB's own short plotting label
  (§6.3), copied as written — including CCDB's spellings, e.g. "Free
  Ocurr." The script checks that labels are unique within a structure and
  stops if not.
- `planar_tables/planar_<Planar_ID>.tsv` — the planar rows, unchanged.
- the root position from `overlaps.tsv`, somewhere the exporter can read it
  (see step 2.2).

It records the CCDB commit it read from, refuses to run on a clone with
uncommitted changes to the data files, and gives identical output when re-run.
Dry run by default; `--apply` to write.

The older hand-extracted files (`domains_chac.tsv`, `domains_yupik.tsv`,
`domains_mart.tsv`, `domains_quech.tsv`, `domains.tsv`) stay as they are: the
tree-traversal snapshot tests read them, and the new names don't collide.

### Step 2: four exporter fixes

1. **The chart axis comes from the planar table.** Today `load_spans()` takes
   the position count from the largest `Right_Edge`. Four structures have
   final positions no test reaches — Araona 17 of 18, Yupik 20 of 21, Mocoví
   19 of 20, Mebengokre 22 of 32 — and `load_position_labels()` would refuse
   them outright because the planar table has more rows. When a planar table
   is given, use its position count. nyan1308's output is unchanged (its
   `[1-22]` span is observed); confirm with the porting checks.
2. **Root position.** Add `--root-position N`, filled from `overlaps.tsv`.
   The planar tables' `Elements` text stays as CCDB wrote it rather than being
   overwritten with `root`. `--root-element` keeps working for nyan1308.
3. **A colour for `indeterminate`** in `DOMAIN_TYPE_STYLE` (and
   `CLASS_COLORS`, which it is built from), instead of the fallback grey.
4. **Groupings per dataset.** `planars_groupings.py`'s `BUNDLES` and
   `FILTERS` are defined in Chichewa's types ("Syntax-like", "no Tono"). For
   CCDB they either match nothing or only repeat the morphosyntactic chart.
   Groupings need to belong to a dataset (or a family of datasets such as
   "all of CCDB"), not be global. For CCDB there is one bundle,
   morphosyntactic + indeterminate (§6.2), set against phonological on its
   own; no filters. Its colour and display label are picked when it is
   added. nyan1308 keeps its current bundles and filters unchanged.

### Step 3: one language, end to end

Chácobo verbal (`chac1251_verbal`): 28 positions and 29 families, the closest
to nyan1308. Export, render, and Jeff looks at every chart. Expected trouble:

- label crowding on long structures (worse in step 4: Chorote, 46 positions);
- charts that pick 6 exemplary families, or cap conflict groups at 12, in
  languages with 2–3 families;
- chart canvases tuned for 22 positions.

Fixes go in the R package as options whose defaults leave nyan1308 unchanged,
as in the library rebuild.

**Keep a log of every command run in this step, exactly as typed, with what
it printed and roughly how long it took.** Chácobo is the first language to
go through the pipeline from nothing, so this log is the raw material for the
tutorial in step 5. Write it down as it happens (in the progress file), not
afterwards from memory: a tutorial rebuilt from memory is the imagined route,
not the real one.

### Step 3a: one command for one language

Today, drawing a language means running the exporter, then the renderer,
with up to eight options between them that have to agree (dataset name,
domains file, planar file, root position, the four permutation-test
options). Once step 3 has shown which options actually matter, wrap them in
one command:

```sh
python scripts/planarsviz_language.py chac1251_verbal            # dry run: print what would run
python scripts/planarsviz_language.py chac1251_verbal --apply    # export, then render
```

- It finds the domains file, planar table and settings files by the dataset
  name, using the same naming conventions the exporter already uses, and
  prints the full exporter and renderer commands it will run, so nothing is
  hidden.
- Flags: `--apply`; `--permutations N` (default 5000, all four tests, per
  §6.4) and `--no-permutations`; `--formats`; `--plots` passed through to the
  renderer.
- It only calls the two existing scripts; it holds no analysis or drawing
  code of its own and adds no settings the exporter and renderer don't
  already have.
- A `make` alias in the repo's `Makefile` (e.g. `make charts LANG=...`) is
  worth adding only if the main project's aliases are what Jeff actually
  reaches for; ask before adding it.

nyan1308 must produce exactly the same bundle through this command as
through the two scripts run by hand. Check that by comparing the two
bundles' files, not by looking at the charts.

Step 4's batch driver then becomes a loop over this command.

### Step 4: all 21

A small driver exports and renders every structure, with all four
permutation tests on (§6.4), and writes one summary:
which charts failed, which were skipped, and anything worth looking at (e.g.
a structure with a single family). Then fix what it finds.

### Step 5: documentation

`results/visualizations.md`, `docs/planarsviz_guide.md` §5 (adding a
language: point to the import script and the one-language command),
`scripts/INDEX.md`, `CLAUDE.md` in this folder, and a progress file for this
work in the same style as `PLANARSVIZ_LIBRARY_PROGRESS.md`.

**A tutorial: `docs/planarsviz_tutorial.md`.** There is none today. The guide
is a reference: it says what each option does, not what to run in what
order, and every example in it is nyan1308. The tutorial walks one language
from nothing to finished charts, in order, built from step 3's command log:

1. Get the data (import from CCDB, or write the two TSVs by hand for a
   language that isn't in CCDB).
2. Dry run, then run, the one-language command.
3. Where the charts are, and which three or four to open first.
4. What the numbers mean for this language: families, tree counts, the
   permutation-test p-values, briefly, with links to
   `CHART_MECHANICS_AND_UNCERTAINTY.md` for the fuller account.
5. What to do when something looks wrong: the checks, and where a chart's
   options are documented.

Every command in it is copied from the log and run again, exactly as
written, before the tutorial is committed. It links to the guide and
catalogue for detail rather than repeating them. Add it to the
`NonCollaborative/CLAUDE.md` docs list and to `README.md`'s annotated table of
contents.

### Later, optional: charts across languages

Nothing today compares languages — family counts for all 21 side by side,
fragmentation by structure size, and so on. That would be new charts reading
many bundles at once, and is out of scope until steps 1–5 are done.

## 4. What not to do

- Don't edit the CCDB clone or push to it. It belongs to the CCDB
  project; this work only reads it.
- Don't change nyan1308's output. Every fix must leave the 21 porting checks
  passing.
- Don't hand-edit the imported `domains_*`/`planar_*` files; change the import
  script and re-run it, so the CCDB commit stays the one owner of those facts.

## 5. Not in scope

- Comparing CCDB's Araona with the Araona annotations in `coded_data/arao1248`
  (the main pipeline). Interesting, but a separate question.
- The three CCDB structures with no tests.

## 6. Decisions (settled by Jeff, 2026-09-22)

1. **Dataset names: CCDB's `Planar_ID`** (`chac1251_verbal`,
   `chac1251_nominal`). One bundle and one `results/<Planar_ID>/` folder per
   structure, so a language's two structures sort side by side; chart files
   are `<Planar_ID>_<chart>.pdf`. No change to the per-language folder layer
   is needed.
2. **Groupings: one bundle, morphosyntactic + indeterminate**, set against
   phonological on its own. No filters. Alternatives considered: no bundles
   (Claude's recommendation), pooling indeterminate both ways, and a
   no-indeterminate filter.
3. **Chart labels: built from CCDB's `Domain_ID`, for all 21 structures**
   (revised 2026-09-22; first choice was CCDB's short `Test_Labels`). The
   language prefix is dropped and `_`/`.` become spaces:
   `arao1248_v_ciscategorial.selection_maximal_broad` →
   "ciscategorial selection maximal broad". Why the first choice failed, found
   by the import script: 8 structures have no short labels at all (every row
   `NA`, Chácobo verbal among them), and 3 have duplicates that look like
   CCDB errors (e.g. Yukuna's minimal tone-dissimilation test labelled "Tone
   Diss. Max."). Labels must be unique because the pooled plots use them as
   row names and would merge two tests onto one row, and the exemplary charts
   look tests up by label. Built labels are always unique and the same style
   in every language; median 37 characters, the same as Chichewa's longest,
   with a few much longer (97 in Chorote). CCDB's own label is kept beside it
   as `CCDB_Test_Labels`. The missing and duplicated CCDB labels are worth
   reporting to the CCDB project; that is Jeff's call, not part of this work.
4. **Permutation tests: run for all 21.** Weak results per structure are
   still results, and a view across languages may show a pattern no single
   one does. Claude had recommended off by default. Cost: nyan1308's
   fragmentation test takes about four minutes at 5000 draws; the CCDB
   structures have fewer spans and families, so each should be quicker, but
   time the first one in step 3 before running the batch.

## 7. Who does what: Opus and Sonnet subagents

The main session (Opus) owns the design choices, anything that could change
nyan1308's output, and the final say on whether something is right. Sonnet
subagents take work that is fully specified, can be checked by a test or by
comparison with a known answer, or splits cleanly into independent pieces.
Every subagent result is checked by the main session before it is committed.

**Before step 1: a map of what assumes Chichewa (1 read-only agent).** One
agent searches the exporter, `laminar_analysis.py`, the permutation-test
scripts and `r/planarsviz/R/` for anything that quietly assumes nyan1308:
22 positions, 69 families, fixed canvas sizes, label widths, the "6
exemplary / 12 per conflict group" caps, type names. It returns a list with
file and line, and nothing is changed. This turns step 3's "expected
trouble" from a guess into a checklist.

**Step 1: import script (1 agent, then 1 checker).** The spec in §3 is
complete enough to hand over whole. A *second*, independent agent then
checks the output against CCDB's raw files without reading the script: row
counts per structure, edges, planar rows, root positions, and whether our
convergence count for each span matches CCDB's own `Convergence` column.
That last check is free evidence that we read the data the way CCDB means
it; a mismatch goes to Jeff, not into a fix.

**Step 2: split by how much judgement it needs.**
- 2.1 (axis from the planar table) — **Opus.** `load_spans()` feeds every
  analysis and every permutation test; deciding what `n_positions` means for
  each caller is design work.
- 2.4 (groupings per dataset) — **Opus designs** where groupings live and how
  a dataset finds its own; **one Sonnet agent implements** it.
- 2.2 (root position option) and 2.3 (indeterminate colour) — **one Sonnet
  agent, together**: both small, both in the same file, so one agent avoids
  edits colliding.
- The 21 porting checks (about 6 minutes) run after each change as a
  **background agent** that reports pass/fail, so the main session keeps
  working meanwhile.

**Step 3: Chácobo.** The main session does the export and render. A Sonnet
agent then **pre-screens** the PNGs against a fixed list — clipped or
overlapping labels, empty panels, legends missing a type, axes that stop
early — and returns what it found per chart. This is to point Jeff's look,
not replace it: judging whether a chart is right stays with Jeff.

**Step 4: the batch — the biggest gain.**
- Running the 21 exports and renders is **one script, not 21 agents**; it is
  machine work.
- **Reviewing** the output is where parallel agents pay: about 60 charts per
  structure, over 1,200 in all. Split the 21 structures across **7 Sonnet
  agents, 3 each**, all using step 3's checklist and returning results in one
  shared format (structure, chart, problem, severity). The main session
  merges them into one list grouped by chart function, since one fix to a
  chart function usually fixes it for every language.
- **Fixes** to separate chart functions are independent, so each can go to
  its own Sonnet agent in its **own worktree**, each required to leave the
  porting checks passing and to add its change as an option whose default
  leaves nyan1308 unchanged. The main session reviews and merges them one at
  a time.

**Step 3a: the one-language command (1 Sonnet agent).** Fully specified by
step 3a once step 3 has settled which options matter; the "same bundle for
nyan1308" comparison is the test it must pass.

**Step 5: documentation (parallel drafts, Opus review).** The files are
independent, so one Sonnet agent per file drafts the update. The tutorial is
the exception: the main session writes it from the step 3 log, since
deciding what a first-time reader needs to see is the judgement it rests on. The main session
checks every command and path in the drafts actually works before committing:
a wrong doc is a bug here, and Sonnet drafts are where one would slip in.

**Not given to subagents:** the choices in §6, the design of 2.1 and 2.4,
deciding whether a chart is correct, and anything touching CCDB's clone.

**Scale.** At most 7 agents at once (the step 4 review), under this
project's usual limit of 10. If it's easier to run step 4's review as one
workflow rather than separate agents, that needs Jeff's go-ahead first.
