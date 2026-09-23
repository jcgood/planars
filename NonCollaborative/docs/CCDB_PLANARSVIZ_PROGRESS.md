# CCDB languages through planarsviz — progress

Plan: `docs/PLAN_ccdb_planarsviz.md`. This file is the current state; the
plan says what and why. Update it at every step boundary, in the same commit.

## Where things stand (2026-09-22)

- **Step 1, import: done** (`0c483d7`). `scripts/analysis/import_ccdb.py`
  wrote all 21 structures from CCDB commit `e3d5386`. Checked by a separate
  pass that never read the script: 463 tests in both, every value exact,
  built labels unique.
- **Step 2.1, axis from the planar table: done** (`226a4f8`). Details below.
- **Steps 2.2–2.4: done** (this commit; a Sonnet agent from the brief below,
  then reviewed). Details under "Steps 2.2–2.4 as built".
- Steps 3–5: not started. Next is step 3: export and render every CCDB
  structure, starting with `chac1251_verbal` (`--groupings ccdb
  --root-position 8`).

## Decisions made while working (in addition to the plan's §6)

- **Chart labels come from `Domain_ID`**, not CCDB's `Test_Labels` (plan
  §6.3, revised by Jeff 2026-09-22). CCDB's short labels are missing for
  every test in 8 structures and duplicated in 3 (moco1246, sout2991,
  yucu1253 — the duplicates look like CCDB errors). CCDB's label is kept as
  `CCDB_Test_Labels`.
- **The permutation tests place spans across the whole planar structure**,
  including positions no test reaches (Claude's call with step 2.1,
  confirmed by Jeff 2026-09-23). It changes the p-values for the four
  structures with unreached positions: Araona 18 vs 17, Yupik 21 vs 20,
  Mocoví 20 vs 19, Mebengokre 32 vs 22. Reasoning: the positions exist
  whether or not a test reaches them — the same reason the chart axis is the
  planar structure (library question 5).

## Findings worth keeping

- **CCDB's `Convergence` column counts the test itself**, so it equals our
  span convergence for all 463 tests. CCDB's README describes it as "number
  of other tests", which is off by one. Also: CCDB's short labels are
  missing/duplicated as above. Both are worth telling the CCDB project;
  Jeff's call.
- **CCDB planar tables have no `Position_Label` column**, and
  `load_position_labels()` raises `KeyError` on them. Every CCDB export fails
  until step 2 handles it.
- **Standalone runs of the analysis scripts on CCDB files crash or mislead**
  (they use fixed Chichewa group lists; `span_placement_test.py`,
  `arbitrary_layers_test.py` and `boundary_strength_test.py` crash on a
  missing type; several write files named `nyan1308_*` whatever the input).
  Only the exporter path is supported for CCDB; the exporter already builds
  its groups from the types present. Not being fixed in this work.

## Step 2.1 as built

`load_spans()` takes an optional `n_positions` (checked: a span ending past
it is refused). The exporter reads the count from the planar table
(`planar_position_count()`) and passes it to the full analysis, the subset
analyses, the overlay groups, the full boundary-strength table and all four
permutation tests (each `run_test()` gained the same optional argument).
Unchanged on purpose: per-class forests keep their own subset's largest edge
(what the archived forest scripts drew), and subset boundary-strength tables
keep theirs (what keeps `no_tono` equal to its committed file).

Evidence nyan1308 is unchanged: a full export with all four permutation tests
at 5000 draws, compared file by file with the committed bundle — 86 files, 0
differ. `pytest NonCollaborative/tests -m "not needs_r"` passes. On
Mebengokre, `load_spans()` now returns 32 positions (was 22).

## Steps 2.2–2.4 as built

As the brief below, plus:

- **`domain_types.tsv` now lists only the domain types a dataset has.**
  Before, it listed every known type whether observed or not; with
  `indeterminate` known, that would have given nyan1308 a row for a type it
  never uses. Unknown types are still numbered after every known style
  (the agent's first version numbered them after the rows kept, which gave
  the shifted test data's `tonal` the same order numbers as `intonational`
  and `length` — caught in review). The committed `shifted_nyan` bundle was
  re-exported for this: its unused `tonosegmental` row is gone and `tonal`
  moves from 6 to 7. R uses these numbers only as relative order, which is
  unchanged, and `shifted_nyan` has no reference images.
- `metadata.json` gains `groupings` and `root_position_source`. The R bundle
  check does not require either.
- The exporter's `main()` now passes every argument after the first three by
  name, since two new ones went into the middle of the old positional run.
- A planar table with no `Position_Label` column skips the "positions run
  1..N with no gaps" check that the labelled branch makes. All 21 CCDB tables
  are contiguous, so this matters only for a future import.
- **The `ccdb` bundle colour is `#EE4C97`** (Jeff, 2026-09-23), the eighth
  colour of the palette the class colours come from. The seventh, `#FFDC91`,
  was the first placeholder but is too pale for thin lines on white.

Evidence: nyan1308 re-exported in place with all four permutation tests at
5000 draws — only `metadata.json` changes, by the two new keys. The no-R
test suite passes. `chac1251_verbal` exported with `--groupings ccdb
--root-position 8` has 28 positions, 29 families, forests `indet` (4
trees) and `morsyn_indet` (8 trees), root 8, labels 1–28, and exactly
three `domain_types.tsv` rows.

## Brief for steps 2.2–2.4 (one Sonnet agent, then review)

1. **Indeterminate as a known domain type.** The exporter already analyses a
   type it doesn't know (appended after `CLASS_ORDER`); it lacks only styling
   and forests. Add `indeterminate` to `laminar_tree_counts.CLASS_COLORS`
   (`#6F99AD`, the next colour in the palette the other five come from), to
   `export_planarsviz_data._DOMAIN_TYPE_ORDERS` (after the existing five;
   `alt_colour` `#66CCEE`, the unused colour of the second palette), and to
   `laminar_analysis.OVERLAY_GROUPS` as `(["indeterminate"], "#6F99AD",
   "indet")`, appended so existing order is unchanged. Do not reorder any
   list.
2. **Groupings per dataset (plan 2.4).** In `planars_groupings.py`, named
   sets: `"chichewa"` = today's `BUNDLES`/`FILTERS` (keep those names as
   that set, so every current importer is unaffected), and `"ccdb"` = one
   bundle `("morsyn_indet", ["morphosyntactic", "indeterminate"], <colour>,
   "Morphosyntactic + indeterminate")`, no filters. Exporter gains
   `--groupings {chichewa,ccdb}` (default `chichewa`) and uses the chosen
   set everywhere it now uses `BUNDLES`/`FILTERS`; record it in
   `metadata.json`. Bundle colour: propose one distinct from the four class
   colours and flag it for Jeff.
3. **Root position (plan 2.2).** Exporter gains `--root-position N`
   (validated 1..n_positions); when given it replaces the `Elements == root`
   lookup. Record which was used in `metadata.json`.
4. **Position labels.** When the planar table has no `Position_Label`
   column, fall back to plain position numbers — the documented last
   fallback — instead of raising.
5. **Checks:** nyan1308 bundle identical to committed (use the file-by-file
   comparison; permutation tests can be left off for speed if the four
   test tables are compared separately from a 5000-draw run); the no-R test
   suite passes; `chac1251_verbal` exports with `--groupings ccdb
   --root-position 8` into a scratch folder and its bundle has 28 positions,
   an `indet` forest, the `morsyn_indet` bundle, root 8, and numbered
   position labels.

## Likely trouble in step 3 (from a read-only survey of the code, 2026-09-22)

Most likely to show first on Chácobo verbal (28 positions, 29 families):

- **Fixed canvases tuned for 22 positions** — `pooled.R` (width fixed,
  height already scales), `overlays.R` (20 × 14 in), `exemplary.R`
  (`tree_width_cm = 51`), `spanchart.R`, `forestspans.R`,
  `boundary_strength.R`, `boundary_strength_overlay.R` (boxed two-line
  labels at every position — worst). Expect crowding; worst on Chorote (46).
- **`boundary_strength_overlay.R` line 134: y-axis breaks every 50.**
  Structures with few families never reach 50, leaving only a 0 gridline.
  `boundary_strength.R` already uses an adaptive break function for the same
  job.
- **`ghost_trees.R` line 48 and `conflict_groups.R` line 40 name spans with
  `letters[...]`** — a silent limit of 26 spans in one family (nyan1308's
  largest has 13). Check each CCDB bundle's largest family before trusting
  those two charts.
- **`span_placement_test.random_replicate()`** samples left edges without
  replacement; with many same-length spans in a short structure (12
  positions: chac1251_nominal, mart1259_verbal) it can fail outright.
- `forestspans.R`'s inset legend sits where nyan1308 happens to have no
  spans; not guaranteed elsewhere.
- Harmless: the renderer's `syntax_phon` charts are skipped for bundles with
  other names; `null_panels.R`'s three-across grid will have an emptier last
  row; exemplary-k and the conflict-group cap already shrink to the families
  available.
