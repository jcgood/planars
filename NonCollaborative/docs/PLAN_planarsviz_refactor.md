# Plan: `planarsviz` Visualization Refactor

## Status

Planning only. No implementation or presentation cutover is authorized by this
document.

The first release should be behavior-preserving and versioned as `0.1.0`.
Visual redesign is a later project.

## Decisions

- Create a local R package at `NonCollaborative/r/planarsviz/`.
- Keep Python as the source of truth for laminar-family enumeration.
- Add a small Python export layer for a documented Python-to-R data contract.
- Use readable TSV files plus one JSON metadata file.
- Make the R API generic across compatible domain files, with `nyan1308` as
  the first complete regression fixture.
- Refactor all current visualization families, including pooled plots.
- Preserve current visual appearance before attempting redesign.
- Use `renv` and explicit dependency management, with the heavier release
  checks staged so they do not block initial utility extraction.
- Stage new outputs under `results/planarsviz/` in an organized hierarchy.
- Support PDF and PNG outputs, with optional SVG support.
- Use validated R configuration objects for rendering options.
- Keep old scripts and outputs available during migration.
- Work on a separate `refactor/planarsviz` branch/worktree so presentation
  work can continue without waiting.
- Run analytical, rendering, visual, package, and integration tests before
  cutover.

## Goals

1. Replace duplicated hand-written/generated R scripts with reusable package
   functions.
2. Preserve the existing numerical interpretation and visual output during the
   first migration.
3. Make labels, palettes, tree placement, alpha/width scaling, themes, and
   patchwork layouts single-source utilities.
4. Make every plot reproducible from validated input data and explicit
   configuration.
5. Allow presentation work to continue independently throughout the refactor.
6. Make future visualization additions require data and configuration rather
   than another large generated R script.

## Non-goals for `0.1.0`

- Changing the Python family-enumeration algorithm.
- Reinterpreting conflicts, maximality, or family frequencies.
- Redesigning the visual language of the existing plots.
- Migrating historical `OlderFiles/` scripts into the active package.
- Making the entire repository an R package.

## Current-state findings

The active visualization code repeats several concerns across files such as:

- `results/laminar_conflict_groups.r`
- `results/laminar_four_trees.r`
- `results/laminar_freqtree.r`
- `results/laminar_spanchart.r`
- `scripts/laminar_forest.r`
- `results/nyan1308_laminar_overlay.r`
- `results/nyan1308_all_families_labeled.r`
- `scripts/domain_charts-cgpt.r`
- `scripts/nyan_boundary_skyline.r`

Repeated material includes position labels, `groupOTU()` annotations, tree
placement, tip-label placement, palettes, alpha/width scaling, themes,
patchwork overlays, legends, and output paths. Several large `.r` files are
generated artifacts rather than maintainable source.

The current Nyan baseline is:

- 26 unique spans
- 65 conflict pairs
- 69 maximal laminar families
- five spans in all 69 families
- 95 active raw tests for the pooled/boundary-test visualizations

## Architecture

Separate the system into three layers.

### 1. Data and analytical metadata

Python continues to calculate:

- active tests and unique spans
- span relationships and conflict pairs
- maximal laminar families
- family membership
- span frequency across families
- conflict groups
- source and analysis metadata

R must not independently re-enumerate the families for production plots.

### 2. `planarsviz` package

The package consumes either the validated export bundle or, for exploratory
use, a raw domain TSV through a clearly labeled adapter.

Likely public functions include:

```r
read_planars_bundle()
read_domain_tsv()
validate_planars_data()
planarsviz_config()
plot_laminar_tree()
plot_laminar_forest()
plot_frequency_tree()
plot_four_trees()
plot_conflict_groups()
plot_domain_overlay()
plot_pooled_domains()
plot_span_chart()
plot_boundary_skyline()
save_planars_plot()
```

The package should return plot objects and structured data. It should not write
files or print plots merely because package code was sourced.

### 3. Rendering orchestration

Create `scripts/render_planarsviz.R` as the explicit command-line entry point.
It selects datasets, configurations, plots, formats, dimensions, and output
locations. It owns file writing and produces a manifest of generated outputs.

## Python-to-R data contract

Add a small export layer without changing the enumeration algorithm. A typical
bundle should contain:

```text
results/planarsviz/nyan1308/data/
├── spans.tsv
├── tests.tsv
├── families.tsv
├── family_membership.tsv
├── span_frequency.tsv
├── conflict_pairs.tsv
├── position_labels.tsv
└── metadata.json
```

`metadata.json` should record the source file, input checksum, active-test
count, unique-span count, conflict count, family count, truncation status,
analysis version, and export version.

The package must validate the bundle before rendering and fail clearly if
counts, references, spans, family IDs, or metadata are inconsistent.

The contract must be documented in package documentation and a vignette. It
must explicitly state which operations happen in Python and which happen in R,
how to regenerate the bundle, and which validation checks R performs.

## Package and R best practices

- Use `DESCRIPTION`, `NAMESPACE`, `R/`, `tests/testthat/`, and package docs.
- Use `roxygen2`, `testthat`, `styler`, and `lintr`.
- Use `renv` to lock R and Bioconductor dependencies.
- Keep core data validation independent of `ggtree` where practical.
- Treat `ggtree` and other heavy rendering dependencies explicitly.
- Avoid `setwd()` and absolute paths in reusable functions.
- Avoid global variables such as `posLabel`, `alphaval`, and `n_families`.
- Validate arguments and configuration values at public function boundaries.
- Use deterministic ordering for labels, families, and output names.
- Keep rendering choices in validated configuration objects; keep dataset facts
  in the data bundle.
- Make output format, dimensions, device, and background explicit.

## Output structure

During migration, write only to:

```text
results/planarsviz/
└── nyan1308/
    ├── data/
    ├── manifests/
    ├── reports/
    └── plots/
        ├── laminar/
        ├── pooled/
        ├── overlays/
        ├── conflicts/
        └── diagnostics/
```

The structure should remain extensible for additional datasets and plot
families. The package should not assume that all outputs belong in one flat
directory.

## Migration phases

### Phase 0: Freeze the corrected baseline

- First incorporate and review all currently identified rendering fixes,
  including label placement, legend gating, and background/colour behavior.
- Freeze the baseline only after those fixes have landed; do not encode known
  bugs into regression fixtures.
- Record corrected current Nyan analytical counts and family-size distribution.
- Record position labels, conflict-group definitions, output names, and plot
  dimensions.
- Preserve representative PDFs and PNGs as baseline artifacts.
- Identify authoritative source scripts versus generated outputs.

### Phase 1: Scaffold the package

- Create `r/planarsviz/` and package metadata.
- Add dependency declarations and the initial package test infrastructure.
- Add `renv` early enough to record the working environment, but defer strict
  lockfile/clean-install enforcement until the package API and dependency set
  have stabilized.
- Add package-level documentation.
- Add configuration and data-class conventions.

### Phase 2: Add and document the export contract

- Add Python bundle export only; do not alter family enumeration.
- Add bundle validation in R.
- Add a raw-TSV adapter for exploratory and pooled workflows.
- Test that Python output reproduces the known Nyan baseline.

### Phase 3: Extract shared utilities

- Centralize labels, palettes, themes, dimensions, and scaling.
- Centralize tree parsing, span annotation, `groupOTU()`, and tip labels.
- Centralize patchwork layout and legend behavior.
- Add unit tests before migrating every plot.

### Phase 4: Migrate plots incrementally

Migrate in this order:

1. span-frequency chart and boundary skyline
2. frequency-weighted tree
3. single-family and forest plots
4. four-tree summary
5. conflict-group plots
6. domain-type overlays
7. all-family labeled overlays
8. pooled constituency plots and global-layer variants

Each migration should render into a new staging directory and compare against
the corresponding baseline before the next visualization family is migrated.

### Phase 5: Add the renderer and manifest

- Implement `scripts/render_planarsviz.R`.
- Support dataset, plot selection, output directory, format, and configuration
  arguments.
- Write a manifest containing inputs, configuration, package versions, output
  paths, and validation results.

### Phase 6: Reconcile presentation-side changes

Because presentation scripts will continue to evolve during the refactor:

- after every presentation-side commit, diff the refactor worktree against the
  presentation worktree
- identify intentional presentation changes
- port those changes into package functions or configuration
- rerun all regressions after porting
- regenerate presentation outputs only after reconciliation

### Phase 7: Cut over

- Render old and new outputs side by side.
- Review presentation-critical PDFs manually.
- Run package, Python, integration, and rendering checks.
- Switch the presentation workflow in one small final change.
- Keep old scripts and baseline outputs archived until the new workflow has
  been used successfully.

## Regression testing

### Analytical tests

For the Nyan fixture, assert exact values for:

- 26 unique spans
- 65 conflict pairs
- 69 maximal families
- no enumeration truncation
- five universal spans: `[1–22]`, `[2–22]`, `[3–21]`, `[5–19]`, `[5–21]`
- family-size distribution
- active-test counts for pooled plots

Also assert that every family is laminar, contains the root, is maximal, and
references only known spans.

### Unit fixtures

Include small fixtures covering:

- no conflicts
- nested spans
- disjoint siblings
- one crossing pair
- shared-endpoint spans
- duplicate diagnostic rows
- synthetic roots
- uncovered positions
- commented-out rows

### Visualization tests

- Render smoke-test every visualization.
- Assert files exist, are non-empty, and have expected dimensions.
- Use `vdiffr` or equivalent snapshots for representative plots.
- Prefer SVG/PNG snapshots or plot-object structure over bytewise PDF tests.
- Compare all presentation-critical plots side by side before cutover.

### Quality gates

- `R CMD check`
- `testthat`
- `lintr`
- `styler` check
- Python export validation
- integration test from domain TSV to data bundle to rendered plot
- clean `renv` installation test in CI once the dependency set has stabilized

The first extraction phase should not be blocked by every release-quality gate.
The package must have working tests and documented dependencies early; strict
`R CMD check`, lint/style enforcement, clean-environment installation, and CI
should become mandatory before `0.1.0` cutover.

## Parallel-work protocol

Use a dedicated `refactor/planarsviz` branch and worktree. Continue working on
presentation scripts in the existing worktree without waiting for the refactor.

The refactor must:

- never overwrite presentation outputs during development
- write to `results/planarsviz/`
- treat presentation-side edits as user-owned changes
- reconcile and port those edits before final cutover
- rerun the complete regression suite after every ported change

Suggested parallel lanes are package utilities, Python export/data contract,
regression tests, and visualization migration. The lanes should converge only
at the side-by-side review and cutover phases.

## Acceptance criteria for `0.1.0`

The refactor is ready for release when:

- the documented Python/R boundary is implemented
- Nyan reproduces the analytical baseline exactly
- every current visualization has a package-backed renderer
- pooled plots and their variants are included
- output files are organized and manifest-backed
- tests pass in a clean `renv` environment
- representative visual snapshots pass review
- presentation-side changes have been reconciled
- old and new outputs have been compared
- the presentation workflow can switch with one explicit change
- the old workflow remains recoverable until the new workflow is accepted

---

## Review: Claude (Sonnet 5), 2026-09-13

*The comments below are Claude's, added at Jeff's request for a second opinion before Codex reviews the same plan. Not part of the plan itself.*

The actionable recommendations below have been incorporated into the plan:
tooling gates are staged, presentation changes are reconciled after every
presentation-side commit, and Phase 0 freezes corrected post-fix behavior.

**Overall:** the architecture is right and the non-goals are the right non-goals. Python
stays the analytical source of truth, R never re-enumerates families, and "no algorithm
changes / no visual redesign / no `OlderFiles/` migration" keeps this from becoming a
bigger project than it needs to be. This also directly addresses something concrete I ran
into while auditing `NonCollaborative/`: `generate_r_overlay_script()`'s legend logic was
briefly wrong for the single-group case (a domain-type legend that made no sense on an
all-black chart) precisely because the same rendering logic is duplicated instead of
centralized. A `planarsviz` package with one legend function instead of N generated `.r`
variants removes that whole bug class.

**Where I'd push back:**

1. **Scope is heavy for the audience.** `renv`, Bioconductor pinning, `R CMD check`,
   `lintr`/`styler` enforcement, CI, `roxygen2` + `NAMESPACE`, `vdiffr` snapshots — that's
   professional package-release infrastructure for a folder this same repo's own docs
   describe as "personal working area, not part of the main pipeline." Worth asking
   directly: is `planarsviz` ever meant to leave this machine (shared with Adam, reused
   across languages beyond nyan1308), or is it purely to stop copy-pasting ggplot
   boilerplate for yourself? If the latter, a `scripts/lib/` of sourced R functions gets
   most of the de-duplication benefit without the packaging tax — extract first, package
   later once the API has actually stabilized under real use.

2. **Phase 6's reconciliation risk is not hypothetical.** In the few hours of the session
   where this plan was drafted, two new presentation scripts landed
   (`laminar_tree_counts.py`, the all-families-labeled overlay) and the tip-label/legend
   logic in `laminar_analysis.py` was edited at least three times. At that iteration rate,
   an 8-phase migration risks permanently chasing a moving target unless "periodically
   diff the refactor worktree against the presentation worktree" happens much more often
   than "periodically" implies — closer to after every presentation-side commit than on a
   calendar cadence.

3. **Baseline ambiguity.** The legend-gating fix and the tip-label `colour=NA`/`fill=NA`
   fix both landed in `laminar_analysis.py` on the same day as this plan. Phase 0 says
   "record current Nyan analytical counts" and "preserve representative PDFs... as
   baseline artifacts" but doesn't say whether that baseline is pre-fix or post-fix
   behavior. Worth pinning down explicitly so Phase 0's regression fixtures don't
   accidentally enshrine a bug that was already found and fixed.

**Recommendation:** keep the architecture and phase order, but trim Phase 1's tooling
(skip CI/`renv`/`R CMD check` until there's a second consumer of the package), and tighten
Phase 6 from a periodic check to a rule triggered by every presentation-side commit.
