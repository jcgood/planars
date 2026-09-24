# planarsviz tutorial: one language, from nothing to charts

This walks one language through the whole route, in order: getting its data
in, drawing every chart, knowing which charts to look at first, reading the
numbers, and what to do when something looks wrong. The example is
**Chácobo, verbal planar structure** (`chac1251_verbal`), the first language
after Chichewa to go through it; every command below was run, exactly as
written, and what it printed is what you should see.

This is a walk-through, not a reference. For what an option does, see the
[user guide](planarsviz_guide.md); for what a chart shows and how to change
it, the [chart catalogue](planarsviz_charts.md).

**Run everything from `NonCollaborative/`**, with the project's Python
environment active. The bundle records the paths it read, so running from
somewhere else writes a bundle that differs from the committed one.

---

## 1. Get the data

A language needs two files, found by its **dataset name** — for a CCDB
language that is CCDB's `Planar_ID`, here `chac1251_verbal`:

- `domains/domains_<dataset>.tsv` — one row per constituency test: which span
  of positions it picks out and what kind of test it is.
- `planar_tables/planar_<dataset>.tsv` — one row per position of the planar
  structure.

### 1a. A language in CCDB

The import script reads the CCDB clone (`~/gitrepos/Constituency-Database`,
never changed) and writes both files, plus a small settings file,
`planar_tables/ccdb_<dataset>.json`, holding the root position, language name
and planar type. Dry run first:

```sh
python scripts/analysis/import_ccdb.py --planar-id chac1251_verbal
```

It prints, for each file, whether it is new, unchanged, or would change, and
what it noticed about CCDB's own labels (for Chácobo verbal: CCDB gives no
short label for any of its 38 tests, which is why chart labels are built from
CCDB's `Domain_ID` instead). Then write:

```sh
python scripts/analysis/import_ccdb.py --planar-id chac1251_verbal --apply
```

Leave out `--planar-id` to import all 21 CCDB structures that have tests.
Don't edit the files it writes by hand: change the script and re-run it, so
CCDB stays the one owner of those facts.

### 1b. A language not in CCDB

Write the two files by hand, tab-separated. The domains file needs at least
these columns (others are kept but not read):

| Column | What goes in it |
|---|---|
| `Test_Labels` | A short name for the test, **unique** within the file — it is the row label in the pooled charts. A label starting with `#` marks a placeholder row, which is skipped. |
| `Domain_Type` | `morphosyntactic`, `phonological`, `indeterminate`, `tonosegmental`, `intonational` or `length` have colours already; any other value is analysed, with a default colour. |
| `Left_Edge`, `Right_Edge` | First and last position of the span, counting from 1. |
| `Size` | `Right_Edge − Left_Edge + 1`. Checked: a row where it disagrees stops the export. Spans of size 1 are left out of the analysis. |

The planar table needs one row per position, with a `Position` column
numbered 1 to N with no gaps. Two optional columns: `Elements`, where the
value `root` marks the root position (the verb stem, say), and
`Position_Label`, a short name for each position that the charts show beside
its number. Without `Position_Label` the charts show the numbers alone.

If the planar table doesn't mark the root, or you want a display name in the
chart titles, add `planar_tables/chart_settings_<dataset>.json`. Every key is
optional; this one gives the settings Chácobo verbal gets from its CCDB file:

```json
{
  "language_name": "Chácobo (verbal)",
  "root_position": 8,
  "planar_type": "verbal",
  "groupings": "ccdb",
  "forest_axis": "planar"
}
```

`groupings` picks which bundles of domain types are charted together besides
the types themselves: `ccdb` gives one bundle, morphosyntactic +
indeterminate; `chichewa` (the default) is Chichewa's phonology-like and
syntax-like bundles, which assume Chichewa's domain types. For a new language
`ccdb` is usually the right choice. `forest_axis: "planar"` makes each
domain type's forest run over the whole structure rather than stopping at
that type's last position. The [guide](planarsviz_guide.md#5-add-a-new-language)
has the details.

---

## 2. Draw the charts

One command does both halves — export the numbers into a **bundle**, then
draw every chart from it. Without `--apply` it only says what it would do:

```sh
python scripts/planarsviz_language.py chac1251_verbal
```

```
Dataset chac1251_verbal
  language_name  Chácobo (verbal)                 from planar_tables/ccdb_chac1251_verbal.json
  groupings      ccdb                             from planar_tables/ccdb_chac1251_verbal.json
  root_position  8                                from planar_tables/ccdb_chac1251_verbal.json
  planar_type    verbal                           from planar_tables/ccdb_chac1251_verbal.json
  forest_axis    planar                           from planar_tables/ccdb_chac1251_verbal.json
  permutations   5000                             all four tests

Would run, from NonCollaborative/:

  .../python scripts/analysis/export_planarsviz_data.py --domain-file domains/domains_chac1251_verbal.tsv --groupings ccdb --root-position 8 --language-name 'Chácobo (verbal)' --planar-type verbal --forest-axis planar --fragmentation-permutations 5000 --boundary-strength-test-permutations 5000 --span-placement-permutations 5000 --arbitrary-layers-permutations 5000
  Rscript scripts/render_planarsviz.R --bundle results/chart_data/chac1251_verbal --output results

Nothing was run. Add --apply to run both.
```

Read the settings block: each line says where the setting came from, so a
wrong root position or missing name shows up here, before anything runs. Then:

```sh
python scripts/planarsviz_language.py chac1251_verbal --apply
```

For Chácobo verbal this takes about four minutes: nearly three for the export,
almost all of it the four **permutation tests** (§4), and about a minute to
draw 91 charts. It stops at the first failure. Two useful variations:

```sh
python scripts/planarsviz_language.py chac1251_verbal --apply --no-permutations
python scripts/planarsviz_language.py chac1251_verbal --apply --plots pooled_plot,spanchart
```

The first skips the permutation tests — seconds instead of minutes, for a
first look — but the bundle then has none of their tables, and their charts
from any earlier run are removed (the renderer says which), so nothing left
in `results/` is out of date with the bundle. The second redraws only the charts named, from the bundle
already there; it still re-exports first. To redraw charts without
re-exporting, call the renderer directly:

```sh
Rscript scripts/render_planarsviz.R --bundle results/chart_data/chac1251_verbal \
  --output results --plots boundary_strength_overlay
```

`--list` in place of `--plots` prints every chart name the bundle can draw.

To run every CCDB structure at once, four at a time (about seven minutes for
all 21): `python scripts/planarsviz_ccdb_batch.py --apply`. It writes a log
per structure and a summary, `results/ccdb_batch/summary.md`, that lists
failures and anything worth checking before trusting a chart.

---

## 3. Where the charts are, and what to open first

| What | Where |
|---|---|
| The bundle: every number the charts draw, as plain tables | `results/chart_data/chac1251_verbal/data/` |
| The charts, in four topic folders | `results/chac1251_verbal/laminar-families/`, `pooled/`, `boundaries/`, `counts-and-chance/` |
| One line per chart: its name, file and size | `results/chac1251_verbal/chac1251_verbal_planarsviz_manifest.tsv` |

Chart files are named `<dataset>_<chart name>.pdf`. Four to open first:

1. **`pooled/chac1251_verbal_pooled_plot.pdf`** — every test as one line
   across the positions, coloured by domain type. This is the data itself;
   check it against what you know of the language before reading anything
   drawn from it ([catalogue §1](planarsviz_charts.md#1-pooled-plots)).
2. **`counts-and-chance/chac1251_verbal_tree_count_by_class.pdf`** — how many
   different constituency trees (maximal laminar families) the tests allow,
   for each domain type ([§11](planarsviz_charts.md#11-tree-count-bar-charts)).
3. **`laminar-families/chac1251_verbal_laminar_overlay.pdf`** — all those
   trees stacked on one another: branches many trees share come out dark
   ([§5](planarsviz_charts.md#5-stacked-overlays)).
4. **`boundaries/chac1251_verbal_boundary_strength.pdf`** — how strongly each
   position works as a left or right edge of a constituent
   ([§12](planarsviz_charts.md#12-boundary-strength)).

After those, `laminar-families/` holds each domain type's forest (every tree
its tests allow) and the exemplary trees; `counts-and-chance/` and
`boundaries/` hold the permutation-test charts.

---

## 4. What the numbers mean for this language

All of these are in the bundle's `data/` folder, and most are also in a chart.

**Families.** The 38 Chácobo verbal tests pick out 22 different spans over 28
positions. Spans that cross each other can't be in one constituency tree, and
the most spans that can go together without crossing make one **maximal
laminar family** — one candidate tree. The whole set of tests allows 29 such
trees (`metadata.json`: `n_maximal_families`). One tree would mean the tests
agree on a single constituent structure; 29 means they don't.

**Per domain type** (`tree_counts.tsv`): morphosyntactic tests allow 8 trees,
phonological 9, indeterminate 4, and the morphosyntactic + indeterminate
bundle 8. So the disagreement is not just between morphosyntax and phonology:
each kind of test disagrees within itself too.

**Is that more or less than chance?** Four permutation tests ask what family
counts would look like if the tests were arranged at random, each keeping
something different fixed. For the first three, a **small p-value (below
0.05) means fewer families than chance: more tree-like than you'd expect.**

| Test | Keeps fixed | Chácobo verbal |
|---|---|---|
| Fragmentation ([§14](planarsviz_charts.md#14-fragmentation-test)) | the tests; shuffles which domain type each belongs to | nothing small (p from 0.32 to 0.86): no domain type is more tree-like than a same-sized handful of tests of any type |
| Span placement ([§15](planarsviz_charts.md#15-span-placement-test)) | each span's length; moves it to a random place | morphosyntactic + indeterminate p = 0.043; everything else above 0.12 |
| Arbitrary layers ([§16](planarsviz_charts.md#16-arbitrary-layers-test)) | only how many spans there are | morphosyntactic + indeterminate p = 0.035; all tests pooled 0.088 |
| Boundary strength ([§18](planarsviz_charts.md#18-boundary-strength-test)) | as span placement, but asks about each position's edge strength; **small p = a stronger edge than chance** | left edges at positions 6 and 7, just before the verb core at 8 (position 7: p = 0.0004); a weaker right edge at 12 (p = 0.047) |

Read together: morphosyntactic and indeterminate tests pooled are somewhat
more tree-like than randomly placed spans would be, and there is a strong
left edge immediately before the verb core. With 38 tests these are modest
results. The boundary-strength test asks its question once per position and
side, 56 times here, so two or three p-values under 0.05 would turn up by
chance alone; position 7's 0.0004 is the one that stands out. How the charts encode all this, and what they do and don't establish,
is in [CHART_MECHANICS_AND_UNCERTAINTY.md](CHART_MECHANICS_AND_UNCERTAINTY.md).

---

## 5. When something looks wrong

**A chart failed to draw.** The renderer carries on past a failure and ends
with a line such as
`FAILED boundary_strength_overlay: No highlight 'orthographic_word' in this bundle.`
and a non-zero exit. Once the cause is fixed, redraw just that chart with
`--plots` (§2) rather than everything.

**A chart looks wrong.** First check the data: open the pooled plot, and the
bundle's `spans.tsv` and `tests.tsv`. A span in the wrong place is almost
always a wrong `Left_Edge`/`Right_Edge` in the domains file, or the wrong
root position — the dry run's settings block (§2) shows where the root came
from. If the data is right, the chart's own options are in the
[catalogue](planarsviz_charts.md), under the chart's name.

**Known things to check in a new language** (the CCDB batch summary flags
these automatically):

- Very few families (2 or 3): the exemplary-tree and conflict-group charts
  have little to show; that is the data, not a fault.
- Long structures (40+ positions): check the position labels are legible.
- Characters outside ordinary Latin letters in labels (ʔ, ɛ): the renderer
  draws those charts with a different PDF device; check the letters came out,
  not full stops.

**Checks you can run.** Nothing here tests one language's charts against a
right answer — there isn't one to test against. What the checks confirm is
that the package still draws Chichewa exactly as before, so a change you make
to fix one language hasn't broken the charts in general. Before committing a
change to the package or the exporter:

```sh
pytest tests -m "not needs_r"
```

which checks the bundles (about a minute), and, if you changed anything under
`planarsviz/`, the chart checks in the [guide, §6](planarsviz_guide.md#6-check-a-chart).
