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
5. **Where English results live.** Bundles in planars-data
   (`coded_data/stan1293/analysis/…`), since they derive from unpublished
   annotation. Charts are not committed: they are drawn into a folder git
   ignores. English is opt-in for the cross-language bundle, so the public
   one is unchanged.
6. **Adam can draw his own charts.** Now: one command his Claude runs,
   which checks its own prerequisites. Later: charts delivered to his
   language's Drive folder by a workflow (needs R on a GitHub runner for
   drawing only, and a new kind of Drive file in the door's rules; both
   decided when that phase starts).
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

**Phase 4: run English.** Every selection × both groupings; bundles to
planars-data; charts to an ignored folder. The one command (decision 6)
checks R, the restored packages and that `coded_data/` is current, and says
what to do when one is missing. Setup for Adam's Claude goes in
`docs/coordinator-guide.md`. Cross-language with English, opt-in.

**Phase 5: documentation and tests.** Move `scripts/INDEX.md`,
`README_laminar_analysis.md`, the planarsviz guide, tutorial and chart
catalogue to where the code is; update the three CLAUDE.md files
(`NonCollaborative/CLAUDE.md` says nothing there is imported by the main
code, and its pointers move) and the README. The analysis tests that need no
R join the main suite; keep an eye on its run time.

**Later, not in this plan:**
- charts delivered to Drive (decision 6);
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
