# planarsviz user guide

How to go from a domains file to finished charts, how to add a new
language, and how to check that a chart is right. For what each chart shows
and its options, see the [chart catalogue](planarsviz_charts.md). For the
package overview, see [`r/planarsviz/README.md`](../r/planarsviz/README.md).

All commands run from `NonCollaborative/`, using the project's Python
environment.

---

## 1. How the pieces fit

| Step | Tool | Output |
|---|---|---|
| Analyse and export | `scripts/analysis/export_planarsviz_data.py` (Python) | a bundle: `results/planarsviz/<dataset>/data/` |
| Draw | the `planarsviz` R package, `plot_*()` functions | ggplot / patchwork objects |
| Save everything | `scripts/render_planarsviz.R` | PDFs and PNGs, plus `manifest.tsv` |
| Check | `scripts/planarsviz_checks/` | comparison images and pass/fail messages |

The exporter does all analysis by calling the existing, verified Python
functions (`laminar_analysis.py`, `laminar_tree_counts.py`,
`boundary_strength.py`, and `class_fragmentation_test.py` when asked); it
never reimplements them. R never enumerates
families, builds tree shapes or chooses families: it reads those from the
bundle. So a change to the analysis is made once, in Python, and every chart
follows.

---

## 2. Export a bundle

```sh
python scripts/analysis/export_planarsviz_data.py \
    --domain-file domains/domains_nyan1308.tsv \
    --planar-file planar_tables/planar_nyan1308.tsv \
    --language-name Chichewa
```

The dataset name comes from the domains file name: `domains_nyan1308.tsv`
gives `nyan1308`, and the bundle goes to `results/planarsviz/nyan1308/`.

| Option | Default | What it does |
|---|---|---|
| `--domain-file` | (required) | The domains TSV: one row per test, with `Left_Edge`, `Right_Edge`, `Size`, `Domain_Type`, `Test_Labels`. Rows whose label starts with `#` are ignored. |
| `--planar-file` | `planar_tables/planar_<dataset>.tsv` if present | The planar table; supplies position labels and the root position. |
| `--labels-file` | `planar_tables/display_labels_<dataset>.tsv` if present | Chart labels for positions, when they differ from the planar table's `Position_Label` codes. |
| `--root-element` | `root` | The `Elements` value marking the root position in the planar table. |
| `--language-name` | none (titles use the dataset id) | Name used in chart titles, e.g. "Chichewa (nyan1308)". |
| `--highlights-file` | `planar_tables/highlights_<dataset>.tsv` if present | Named position ranges, e.g. the orthographic word. |
| `--conflict-groups-file` | `planar_tables/conflict_groups_<dataset>.tsv` if present | The spans that split families into conflict groups. |
| `--conflict-group-cap` | 12 | Most trees the conflict-groups chart draws per group. |
| `--exemplary-k` | 6 | How many representative families the exemplary charts pick by coverage. |
| `--no-exemplary-sparsest` | off | Don't add the family with the least evidence to the exemplary selection. |
| `--output-dir` | `results/planarsviz` | Where bundles go. |
| `--fragmentation-permutations` | 0 (off) | Also run the class-fragmentation permutation test with this many draws and put its two tables in the bundle. Off by default because it is slow — about four minutes at 5000 draws, against 1.6 seconds for everything else. Use 5000 to match the committed files. |
| `--fragmentation-seed` | 0 | Seed for the above. 0 is what made the committed files. |

The export refuses to write a bundle if family enumeration was cut short,
and the R package refuses to draw from one.

---

## 3. Draw charts in R

Install the package once (or after changing its code):

```sh
R CMD INSTALL r/planarsviz
```

Then:

```r
library(planarsviz)
bundle <- read_planars_bundle("results/planarsviz/nyan1308")

p <- plot_laminar_overlay(bundle, groups = "all", alpha_divisor = 1,
                          thickness_exponent = 0.75, highlight = "orthographic_word")
size <- attr(p, "planarsviz_size")
ggplot2::ggsave("overlay.pdf", p, width = size[["width"]], height = size[["height"]],
                units = attr(p, "planarsviz_units"))
```

Points to know:

- **Chart functions return plots; they never write files.** The canvas size
  each chart was designed for is attached as `planarsviz_size` (width,
  height) and `planarsviz_units` (`"in"` or `"cm"`). Tree charts in
  particular were tuned for their canvas — label placement is measured
  against it — so use it unless you have a reason not to.
- **Variants are options, not separate functions.** A chart restricted to
  some domain types, with a highlighted word, or with a legend is the same
  function with an argument (see the catalogue).
- **Two kinds of restriction.** Some charts can be drawn from a *subset*
  analysis (`subset = "no_tono"`): a fresh analysis of part of the data,
  with its own spans, families, counts and layer numbers. The pooled plot's
  `layers = "global"` is different: a filtered *view* of the full analysis
  that keeps the full chart's layer numbers. Each function's description
  says which it uses.

---

## 4. Render everything

```sh
Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 --formats pdf,png
```

| Option | Default | What it does |
|---|---|---|
| `--bundle` | (required) | The bundle folder. |
| `--output` | `<bundle>/plots` | Where files go. |
| `--plots` | `all` | Comma-separated chart names; `--list` prints the names a bundle supports. |
| `--formats` | `pdf` | `pdf`, `png`, or both (PNG via `pdftoppm` at 100 dpi). |
| `--list` | — | Print the chart names and stop. |

The renderer works out which charts exist from the bundle: one pooled pair
per domain type present, one forest per class, filtered variants only when
there is something to filter, conflict-group charts only when groups are
defined, and so on. Files are named `<dataset>_<chart>.pdf`. It installs
the package into a temporary library itself, reports every chart that
fails, exits with an error if any did, and writes `manifest.tsv` listing
what it wrote.

---

## 5. Add a new language

1. **Domains file** — `domains/domains_<dataset>.tsv`, in the CCDB column
   format.
2. **Planar table** — `planar_tables/planar_<dataset>.tsv`, one row per
   position, with the root position's `Elements` set to `root` (or pass
   `--root-element`).
3. **Optional settings files** in `planar_tables/`, each picked up
   automatically by name:
   - `display_labels_<dataset>.tsv` — columns `position`, `label`; every
     position from 1 to the last.
   - `highlights_<dataset>.tsv` — columns `highlight_id`, `name`, `left`,
     `right`, `colour`, `layer`; later layers win where ranges overlap.
     nyan1308's `orthographic_word` highlight colours positions 5–19 red
     and 17 blue.
   - `conflict_groups_<dataset>.tsv` — columns `group_id`,
     `defining_span_id`; one row may leave the span empty to collect every
     other family. nyan1308's: A `5-13`, B `6-17`, C the rest.
4. **Domain types** — colours and orders for known types are in
   `DOMAIN_TYPE_STYLE` at the top of `export_planarsviz_data.py`. A type not
   listed there still works: it gets grey and sorts after the known types.
   Add a row there to give it a proper colour.
5. **Groupings** — class bundles (`BUNDLES`) and filters that leave out
   domain types (`FILTERS`, e.g. `no_tono`) are defined once in
   `scripts/analysis/planars_groupings.py`.
6. Export, then render. Look at the charts; nothing about nyan1308 is
   assumed in the R code, but a new language is the real test.

---

## 6. Check a chart

Every chart was checked against the working script it replaces, and the
checks are kept so any change can be re-checked. One exception, worth knowing
before reading a check's output: **chart 19, the fragmentation test, never had
a matplotlib original.** It was written in R from the start, so the chart that
script drew is itself the reference —
`results/planarsviz/reference/nyan1308_fragmentation_test_plot.png`, frozen
before the package could overwrite it — and `check_fragmentation.R` compares
against that rather than running an older script.

- `scripts/planarsviz_checks/check_*.R` — runs the old script in memory
  (files untouched), draws the same chart with the library, compares the
  underlying plot data number by number, renders both and reports the
  share of differing pixels. Given another bundle and `library-only`, it
  renders that bundle beside nyan1308 instead. Each script's header gives
  its exact arguments (the pooled and skyline checks also take a domains
  file).
- `scripts/planarsviz_checks/verify_*_export.py` — checks the exporter's
  numbers, trees and selections against the old scripts' own output.
- `scripts/planarsviz_checks/check_renderer.py <render folder>` — compares a
  full nyan1308 render with the frozen reference images.
- `pytest tests/test_planarsviz_checks.py` — runs all 21 checks above and
  compares each one's output against a snapshot, so a drifted chart fails
  instead of printing a number nobody reads. About six or seven minutes.
- `pytest tests/test_planarsviz_bundle.py tests/test_planarsviz_shifted_bundle.py`
  — bundle contents for nyan1308 and for the shifted test data.

Comparison images (reference | new | differences) are in
`results/planarsviz/comparisons/`, and `comparisons/shifted/` holds each
chart drawn from nyan1308 beside the same chart from the **shifted test
data**: nyan1308 with every position moved by two, labels renamed and one
domain type renamed (`tests/fixtures/make_shifted_nyan.py`). A chart that
draws that data correctly has no nyan1308 facts built in.

---

## 7. Package versions

Section 6 compares a chart the package draws against the chart the old script
drew. That comparison is only worth something if both were drawn by the same
R packages — and ggplot2 4.x changed several defaults against 3.x, so "the
same packages" is not a given across machines or across time.

`renv.lock` in `NonCollaborative/` records the exact version of every R
package these charts were drawn with: 130 of them, including ggplot2 4.0.3,
ape 5.8.1 and ggtree 4.2.0, on R 4.6.1. `.Rprofile` makes R use them
automatically whenever it starts in `NonCollaborative/`, so nothing in the
guide above needs a different command.

On a machine that has never run this project:

```sh
Rscript -e 'install.packages("renv")'
Rscript -e 'renv::restore()'
```

`renv::restore()` installs every package at its recorded version into
`NonCollaborative/renv/library/`, which is not in version control. It takes a
while the first time. After that, `renv::status()` reports whether the
installed packages still match the lockfile.

Two things worth knowing:

- **The lockfile covers more than the package's own `DESCRIPTION`.** Three of
  the archived scripts in `OlderFiles/planarsviz_superseded/` load `pacman`,
  `here` and `tidyverse`, and one loads `ggsci`; `render_supercatalan_rows.r`
  loads `cowplot`. The checks run those scripts, so those versions matter as
  much as the package's own and are pinned too.
- **`.renvignore` lists the scripts renv does not read.** They are
  hand-written files nothing runs any more, and they load packages that are
  not installed here, which renv cannot record a version for. The file says
  which and why.

After changing what a script or the package loads, run `renv::snapshot()` to
bring the lockfile back in line, and commit it with the change.

---

## 8. Where things are

| Path | Contents |
|---|---|
| `r/planarsviz/` | The R package (`R/` one file per chart family). |
| `r/planarsviz/inst/data-contract.md` | Every bundle file and column. |
| `scripts/analysis/export_planarsviz_data.py` | The exporter. |
| `scripts/analysis/planars_groupings.py` | Class bundles and filters. |
| `scripts/render_planarsviz.R` | The renderer. |
| `scripts/planarsviz_checks/` | Porting checks. |
| `results/planarsviz/<dataset>/` | Bundles (`data/`) and rendered charts (`plots/`). |
| `results/planarsviz/reference/` | Frozen images of the old charts. |
| `docs/PLAN_planarsviz_library.md` | Why the library is built this way. |
| `docs/PLANARSVIZ_LIBRARY_PROGRESS.md` | What was checked, chart by chart, and open questions. |
