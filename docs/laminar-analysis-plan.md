# Plan: the laminar analysis for any language (English first)

Jeff, 2026-10-24. The analysis and charts built for Chichewa (nyan1308) and
the 21 CCDB structures, now in `NonCollaborative/`, become part of the main
repository and run on any language annotated through planars, starting with
English (stan1293). The aim is a paper on English comparable to the Chichewa
draft, started while Adam is still annotating. **Current state:
`docs/laminar-analysis-progress.md`.**

## Decisions (Jeff, 2026-10-24; don't re-ask)

1. **Run maximal by default.** This is exploratory work: every variant
   selection and every grouping below is computed on every run.
2. **Which spans count as tests: all of them, as named selections.**
   - Selections at least: all variants; strict + loose on complete
     positions (the closest to Chichewa's Minimal/Maximal); the same on
     partial positions; one row where strict and loose coincide.
   - Subspanrepetition's five categories (fill, ws-L, ws-R, ns-L, ns-R) are
     **provisionally five separate tests**, each row tagged with its
     construction: they can give different spans for one construction, so
     merging them would mean choosing a span, a linguistic call. Whether
     they are one test or five goes to Adam once the first English charts
     show whether their weight distorts anything.
3. **Partial spans carry a weight.** Each span records, for each position it
   gains beyond the complete span, *k of n*: how many of that position's
   elements satisfy the rule. Complete and strict spans have weight 1.
   **Provisionally all three metrics are computed, in every bundle:**
   - *mean ratio* (the default, used wherever a chart shows one weight):
     the average *k/n* over the gained positions, each position counting
     equally, since positions are the unit spans are built from;
   - *weakest position*: the lowest *k/n*, a conservative check;
   - *element share*: satisfying elements over all elements in the gained
     positions, which lets large open classes count for more.
   The analysis carries the weights without using them until a weighted
   method is chosen. Stored in the bundle, never in annotation files.
4. **Groupings from the schema, both on:**
   - (a) by domain type and subtype from `schemas/diagnostic_classes.yaml`
     (morphosyntactic / indeterminate / phonological; segmental / prosodic),
     plus the CCDB-style bundle, morphosyntactic + indeterminate against
     phonological;
   - (b) by class, each class as its own group.
   Hand-set bundles like Chichewa's stay possible later as a named grouping.
5. **Where English results live.** Never in the public repo, since they
   derive from unpublished annotation. A local run writes to the
   planars-data clone's `coded_data/.analysis/stan1293/…` (first planned as
   `coded_data/stan1293/analysis/`, moved in Phase 3 because the tooling
   reads any folder inside a language's folder as a class), which
   planars-data's `.gitignore` leaves out. The weekly analysis's bundles
   are committed to planars-data through the local-file door (Phase 4d);
   charts reach people through Drive (decision 6). English is opt-in for
   the cross-language bundle, so the public one is unchanged.
6. **Charts reach contributors through Drive, by themselves** (revised
   2026-10-24, replacing "Adam can draw his own charts" with delivery
   later). The first use is contributors checking their own data, not
   analysis: charts that live on whoever ran a command reach nobody (CLAUDE.md:
   terminal output reaches no collaborator; design for John; nothing to
   remember; 30–40 languages). So:
   - **Contributor charts, after each daily refresh:** for each language
     whose spans changed, two datasets, by class and by domain type, all
     spans (`<lang>_classes_all`, `<lang>_types_all`), **without** the
     permutation tests (they are for analysis, and cost nearly all the
     time), drawn and put in the language's Drive folder through the
     doorway. Each chart's title carries the date and how complete the
     annotation was.
   - **Full analysis, weekly:** every dataset with all four permutation
     tests, for each language whose spans changed since its last run;
     bundles into planars-data through the local-file door, charts into an
     analysis folder beside the contributor charts. A failed run files an
     issue. Nobody has to remember the tests exist or run them.
   - **R on the GitHub runner, for drawing only (Jeff, 2026-10-24).** Not
     the porting checks: those pixel-compare against Mac renders and stay
     local, as before.
   - The local command (`python -m laminar charts`) stays, for whoever is
     working on the analysis; it is not how charts reach people.
7. **`planarsviz/` moves to the repo root** with the Python. The archived
   scripts (`NonCollaborative/OlderFiles/planarsviz_superseded/`) and the
   porting checks that compare against them stay in `NonCollaborative/`.
8. **Chichewa's paths are frozen.** Its inputs and its outputs
   (`NonCollaborative/domains/`, `planar_tables/`, `results/`) keep their
   paths and filenames; only the commands change. Fix anything else as it
   comes up (Jeff: "we can fix as needed later").

## Phases

**Phase 1: take out the Chichewa assumptions, in place.** The standalone
analysis scripts read their groups, position counts and output names from
the data and a named grouping, not from code (`span_placement_test.py`,
`arbitrary_layers_test.py` and `boundary_strength_test.py` crash on CCDB
data; several write `nyan1308_*` names whatever they were given). Done when
all 22 bundles re-export byte-identical (all four permutation flags, see
NextPrompt) and the renderer check passes.

**Phase 2: move the code.**
- The Python analysis (`NonCollaborative/scripts/analysis/`, the exporters,
  the groupings) becomes a top-level package beside `planars/`, working name
  `laminar/`, installed by `pip install -e .`. A sibling, not part of
  `planars/`, so analysis changes don't bump the version Colab installs.
- `planarsviz/` and its renv setup move to the repo root. The archive guard
  (`NonCollaborative/.Rprofile`) keeps protecting the archived scripts.
  `superseded.R`/`.py` point the porting checks at them.
- One command does export + render for a dataset, replacing
  `planarsviz_language.py` and `planarsviz_ccdb_batch.py` (deleted, not
  kept as wrappers).
- Done when all 22 bundles match again, except the recorded domain-file
  path, which changes once.

**Phase 3: connect a planars language.** An adapter in `laminar/` builds the
span table in memory from `planars.reports.language_spans`:
- `Domain_Type` and subtype read from the schema; a construction column
  (labels collide across constructions today: `fill strict complete` appears
  once per subspanrepetition construction); a variant column;
- the planar table and root from the live planar file (root = the keystone);
  the out-of-date `NonCollaborative/planar_tables/planar_stan1293.tsv`
  (49 positions; the live one has 38) is deleted;
- *k of n* per position (decision 3): returned by
  `planars/spans.py:position_sets_from_element_mask`, and brought onto the
  same footing in the modules that work out partial/complete themselves
  (ciscategorial, coreference; check nonpermutability, free_occurrence,
  biuniqueness_deviations). Span snapshots must come back unchanged;
  version bump for Colab;
- each bundle records the planars-data commit and the annotation's
  completeness (`language_completeness`), so a chart drawn mid-annotation
  says so.

**Phase 4: run English, and deliver charts** (revised 2026-10-24; decision 6).
- **4a, local (built 2026-10-24):** colours and per-type forests for the
  planars groupings; `python -m laminar charts --lang <lang>` with its
  checks (R, packages, coded_data/ current); English drawn locally;
  cross-language with English, opt-in (`--with`). Bring into line: the
  local command must not commit to planars-data itself (only the local-file
  door commits there); it writes locally and says so.
- **4b, contributor charts:** a `coding` command (`laminar-charts`, with
  its `operations.yaml` record) that, for each language whose span table
  changed since it last drew (a state file, through the local-file door),
  builds the two contributor datasets in a temporary folder (derived and
  regenerated, so not stored), exports them without permutation tests,
  draws them, and replaces the previous charts in the language's Drive
  folder through the doorway: a new Drive kind with its own sharing rule
  in `sheet_spec.py`, in watch mode until its first clean real write. The
  date and completeness go into each chart's title.
- **4c, the workflow:** `laminar-charts.yml`, started when the data refresh
  finishes (as `generate-reports.yml` is), with R and the pinned packages
  (cached). Nothing from the private annotation goes into its logs or
  downloadable files.
- **4d, weekly full analysis:** `laminar-analysis.yml`, one job per
  (language, dataset) for the languages whose spans changed since their
  last run, all four permutation tests; bundles written to planars-data as
  new local-file door kinds; charts to the analysis folder on Drive; a
  failure files an issue (a new label in `schemas/issue_labels.yaml`).
- **4e, documentation:** the coordinator guide (both kinds of chart, the
  weekly run in "What happens automatically"), the collaborator guide (where
  the charts are and what they are for), a note in the Drive folder.
- **Live steps, each named to Jeff first:** the first upload to a language's
  Drive folder; the first write to planars-data by a workflow; the new label.

**Phase 5: documentation and tests.** Move `scripts/INDEX.md`,
`README_laminar_analysis.md`, the planarsviz guide, tutorial and chart
catalogue to where the code is; update the three CLAUDE.md files
(`NonCollaborative/CLAUDE.md` says nothing there is imported by the main
code, and its pointers move) and the README. The analysis tests that need no
R join the main suite; keep an eye on its run time.

**Later, not in this plan:**
- Chichewa through the adapter once `tonosegmental` and `intonational`
  exist (#72), retiring its hand-coded domains table;
- `planars/charts.py` (matplotlib) overlaps planarsviz's span chart; one
  should go.

## Things to watch

- **Jeff's pending cuts to the cross-language charts** (CCDB thread) would
  muddy the before/after comparison if made during Phase 2. Make them before
  Phase 2 starts or after it ends.
- **Where the Chichewa draft gets its figures** is not known (not in
  `~/gitrepos`). Provisionally it includes charts from
  `NonCollaborative/results/` by path; those paths are frozen (decision 8),
  so no action. If it breaks, fix it then.
