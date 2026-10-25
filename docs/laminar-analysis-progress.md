# Progress: the laminar analysis for any language

The plan and its decisions are `docs/laminar-analysis-plan.md`. This file is
the current state; update it at every phase boundary, in the same commit.

| Phase | Status |
|---|---|
| 1. Take out the Chichewa assumptions, in place | done 2026-10-24 |
| 2. Move the code (`laminar/`, `planarsviz/` to the root) | done 2026-10-24 |
| 3. Connect a planars language (adapter, *k of n*, metadata) | done 2026-10-24 |
| 4. Run English; charts to contributors through Drive (revised) | 4a built 2026-10-24; 4b–e not started |
| 5. Documentation and tests | not started |

## Phase 1 as built (2026-10-24)

- **Groups are built in one place.** `planars_groupings.py` holds
  `CLASS_ORDER` (was copied in four scripts) and `observed_groups()` /
  `permutation_groups()`: a dataset's own domain types and the bundles of
  its grouping that it has data for, in a fixed order. The exporter (five
  copies of that code before) and every standalone script use them.
- **`datasets.py` (new) says what a dataset name means:** its domains file,
  planar table and position count, and its settings (`dataset_settings()`,
  moved from `planarsviz_language.py`), plus the command-line options the
  standalone scripts share. A script run on its own now picks the
  dataset's groupings (`ccdb` for a CCDB structure), uses the planar
  table's position count where the exporter does, and writes
  `results/<dataset>/<topic>/<dataset>_*`.
- **Checked:** all 22 bundles re-exported with all four permutation tests,
  and the seven standalone scripts re-run on nyan1308 into their committed
  paths: every file came back byte-identical. The three tests that crashed
  on CCDB data run on chac1251_verbal. Renderer check and the no-R analysis
  tests pass.

## Phase 2 as built (2026-10-24)

- **`laminar/` is a package at the repo root**, installed by `pip install -e .`
  (`pyproject.toml` lists it). The fourteen analysis modules kept their names
  and import each other as `laminar.*`; `catalan.py` came along from
  `scripts/exploratory/` because the illustrations exporter and
  `refinement_counts.py` use it. Each module runs on its own from anywhere
  (`python -m laminar.<module>`). `datasets.py` owns the two paths, `REPO`
  and `NC` (`NonCollaborative/`, where Chichewa's and the CCDB structures'
  inputs and outputs stay, decision 8); nothing else works out a path from
  its own location.
- **One command**, `python -m laminar charts <dataset>` (or `--ccdb` for all
  21 structures, with the batch summary), replaces `planarsviz_language.py`
  and `planarsviz_ccdb_batch.py`, both deleted. `laminar/render_planarsviz.R`
  is the renderer, run from the repo root.
- **`planarsviz/` and renv are at the root**: `renv.lock`, `renv/`,
  `_dependencies.R`, `lint_and_style_planarsviz.R`, a new `.renvignore` (renv
  reads only the folders with R code: 72 files, not 4,009) and the root
  `.Rprofile`, which holds the archive guard (now pointed at
  `NonCollaborative/OlderFiles/`) and starts renv. `NonCollaborative/.Rprofile`
  hands over to it, so the porting checks, which stay in `NonCollaborative/`,
  get the same packages and guard; the guard test now runs from both folders.
- **A bundle records its input files relative to the repo root**
  (`NonCollaborative/domains/...`), so it no longer depends on where the
  exporter ran; `producer` and `analysis_source` name `laminar/`. That covers
  the planar, labels and conflict-group paths as well as the domain file the
  plan mentioned.
- **Checked:** nyan1308, the 21 CCDB structures and the shifted test bundle
  re-exported with their permutation tests: every data table byte-identical;
  in metadata only those path and producer fields changed (checked by
  script). The illustrations bundle came back byte-identical. All charts were
  redrawn: 1,404 PDFs differ from the committed ones only in their date
  stamp, and the 24 drawn with Quartz (IPA labels in ayau1235_verbal and
  moco1246_verbal) are pixel-identical, so the committed PDFs were kept.
  Roxygen, lintr, styler, guard and no-R NonCollaborative tests pass;
  `tests/test_no_leftovers.py` now covers `laminar/`.
- **Side fixes:** `matplotlib` dropped from `requirements.in` (nothing imports
  it since the charts moved to R); the shifted bundle's documented export
  command now includes the `--fragmentation-permutations 5000` it was made
  with.

## Phase 3 as built (2026-10-24)

- ***k of n* in the library.** `planars.spans.position_sets_from_element_mask`
  now also returns each position's `(k, n)`; every module with partial
  spans puts it in its result (`position_counts`, or per category/domain:
  subspanrepetition, noninterruption, metrical). ciscategorial now uses the
  shared helper instead of its own copy. `gained_position_counts` gives the
  positions a partial span covers beyond its complete counterpart.
  nonpermutability, coreference, free_occurrence and biuniqueness_deviations
  have no complete/partial distinction, so no weights. Span snapshots
  unchanged.
- **Span rows say which test they are.** `language_spans` rows now carry
  `Construction`, `Span_Key`, `Position_Basis` (complete / partial / none)
  and `Gained_Positions`. Which counts weigh which span is
  `reports._WEIGHTED_SPANS`: every class must be listed, or import fails.
  **metrical is the reverse of the rest:** its "complete" span is the
  wider one (it stops only where every element blocks), so that is its
  weighted span, and its k counts elements that do *not* block.
- **Side fix:** labels `nonpermutability nonperm strict` and `coreference
  reflex binder strict` carried the class twice. Now `nonperm strict` (what
  terms.yaml's glossary already said) and `coref binder strict` ("reflex"
  dropped: the class now covers pronoun and NP coreference too; glossary
  entries added).
- **The adapter is `laminar/planars_language.py`.** For each grouping ×
  selection it writes one domains file, named `<lang>_<grouping>_<selection>`
  (8 for English). The groupings (`planars_types`, `planars_classes` in
  `planars_groupings.py`) are built from the schema's domain types
  (`schema_values.class_domain_types()`). Labels get their construction in
  brackets when a class has several; a repeated label fails. Each row has
  the three weights and its `Gained_Positions` (`28:9/10 29:21/30`), and the
  exporter copies them into the bundle's `tests.tsv`.
- **Selections, provisional readings of decision 2:** `complete` and
  `partial` keep the spans from that kind of position, plus every span of a
  class without the distinction. `distinct` counts once any of a
  construction's spans that coincide (strict = loose, or partial =
  complete), listing the others in `Same_Span_As`. On English, `all` and
  `distinct` give the same families (families are built from distinct
  spans); they differ only in convergence.
- **Weights, provisional reading of decision 3:** a loose partial span's
  gap is gained with k = 0. That pulls `vp_ellipsis`'s loose partial mean
  ratio down: it gains 27 positions with no passing element. The
  per-position counts are kept, so another rule can be computed without a
  re-run.
- **Where (changed from decision 5's wording):** `coded_data/.analysis/<lang>/`
  (domains/, chart_data/, charts/), not `coded_data/<lang>/analysis/`. A
  folder inside a language's folder is read as a class by
  `language_completeness`, check-comments and others. Dot-folders are
  skipped, as `.state` and `.test_fixtures` are. All of `.analysis/` is
  in planars-data's `.gitignore` (Phase 4a): local working files.
- **datasets.py** knows a planars dataset: domains file and bundle in
  planars-data, the live planar file (the exporter now reads
  `Position_Name` as the label), the keystone as root, and the display name
  "English [stan1293], by class, distinct spans". `python -m laminar charts
  stan1293_types_all` rebuilds the domains files from the annotation before
  every export. The exporter's default output folder is now the dataset's,
  so English can't land in NonCollaborative/ by accident.
- **Each bundle records its source:** `planars_source` in metadata.json
  (from `source_<dataset>.json`): planars-data commit, uncommitted changes
  or not, cells filled (5637 of 6029 on 2026-10-24), each construction's
  state, and the annotated classes that give no spans yet
  (biuniqueness_deviations, waiting on morphemes; phrasal_accent, no module,
  #237).
- `CLASS_COLORS` moved to `planars_groupings.py` (the planars groupings
  need it, and the old home imported that module). The old
  `NonCollaborative/planar_tables/planar_stan1293.tsv` is deleted.
- **Checked:** English exports, without the permutation tests, to the
  scratchpad (38 positions, 125 tests, 35 distinct spans, 171 families);
  nyan1308 re-exported byte-identical except the skipped permutation
  tables; the CCDB `arao1248_verbal` (whose name starts with a planars
  language's code) still resolves to its CCDB files. check-codebook,
  integrity-check, full suite, NonCollaborative no-R tests pass.

**Left for Phase 4:** colours for English's domain types (done in 4a).

## Phase 4 (revised 2026-10-24)

Phase 4 was "run English locally and commit its bundles". Jeff asked how
Adam would see the charts. Checked against CLAUDE.md's foundations
(terminal output reaches no collaborator; design for John; nothing to
remember; 30–40 languages; Drive through the doorway; only the local-file
door commits to planars-data), charts now reach contributors through Drive
by workflows. Plan decision 6 and Phase 4a–e have the design.

| Unit | Status |
|---|---|
| 4a. Local: colours, `--lang`, English drawn, cross-language `--with` | built 2026-10-24 (below) |
| 4b. `laminar-charts` command: contributor charts to Drive | not started |
| 4c. Workflow after the daily refresh, R on the runner | not started |
| 4d. Weekly full analysis with permutation tests | not started |
| 4e. Documentation | not started |

### 4a as built (2026-10-24)

- **Colours and forests per grouping.** A grouping in `planars_groupings.GROUPINGS`
  can carry its own `styles` (colour, second colour, display order and forest
  id per domain type); the exporter's `grouping_style()` uses them in place
  of its own table, for every colour it writes and for the per-type forests
  and overlays. English's types and each of the 18 classes now have colours
  (provisional, `_CLASS_COLOURS`; fixed per class, so a class looks the same
  in every language). Without this English drew grey and got no per-type
  forests at all, since those came from a third copy of the colours
  (`laminar_analysis.OVERLAY_GROUPS`), which knows only Chichewa's and CCDB's
  types. Chichewa, CCDB and the shifted test bundle keep their tables, so
  their bundles are unchanged (re-exported nyan1308 and chac1251_verbal:
  byte-identical apart from the skipped permutation tables).
- **Found by a test:** in the by-class grouping the subtype bundles were
  named `segmental`/`tonal`, the same as those classes, and forest files are
  named by id, so one would have overwritten the other. Now `phon_segmental`
  etc.
- **One command for a language:** `python -m laminar charts --lang stan1293
  [--apply]`. It checks R, the packages `planarsviz/DESCRIPTION` lists (less
  the style tools) and that coded_data/ has everything on GitHub, and says
  what to run about each; rebuilds the domains files once; draws the eight
  datasets four at a time (logs in the charts folder). It commits nothing:
  a first version committed and pushed the bundles itself, against "only
  the local-file door commits to planars-data"; removed, and planars-data
  ignores `.analysis/`. Machine setup: coordinator guide § "5. Laminar
  charts for a language".
- **English drawn locally, all eight datasets with the tests:** about 45–50
  minutes per dataset with four running at once, ~100 minutes for the
  language, nearly all of it the permutation tests (Chichewa: 1.6 s
  without, ~11 min with). Hence decision 6: contributors get charts
  without the tests, daily; the tests run weekly.
- **Found by the English run, fixed:** in the `complete` selection every
  proform span is one position (the verb stem's), which the analysis
  drops, so proform was a group with no spans and the boundary-strength
  test crashed. A group is now made only of spans the analysis keeps
  (`observed_domain_types`), and `load_spans` returns no spans for such a
  group, so every caller's existing skip works.
- **Cross-language, opt-in:** `python -m laminar.export_cross_language --with
  stan1293_types_all --apply` adds English and writes the result into
  the clone's working folder (`.analysis/stan1293/chart_data/cross_language/`,
  not committed). Its divide
  is `morsyn_indet` against every phonological type or class. Without
  `--with` the public bundle is byte-identical (re-exported and checked).
- Side fix: `planarsviz/DESCRIPTION` pointed to the exporter's and guides'
  old paths.

## Findings

- `check_forestspans.R` had failed since 2026-09-23 without anyone seeing it
  (the R checks run only locally): `expand_limits(x = 1)`, added then so the
  axis always starts at 1, gives the library's chart an extra, invisible
  layer, and the check compared layer counts. The check now leaves blank
  layers out of the comparison; its output matches the snapshot again
  (2026-10-24). Lesson: after a chart change, run
  `pytest NonCollaborative/tests` (the R checks), not only the renderer check.

- `laminar_analysis.py`'s printed report now lists domain types in
  `CLASS_ORDER` rather than the forest order; it writes no file, so nothing
  committed changed.
