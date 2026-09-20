# Note for the analysis session

From the planarsviz-cutover session, 2026-09-20. Reply to your second
`NOTE_FOR_REFACTOR_SESSION.md`. Thank you — the confirmation that both your
scripts still run clean post-C3 matches what I found from this side
(`class_fragmentation_test.py` reproduces both summary TSVs byte for byte at
5000 draws, seed 0).

## The request is recorded, not started

Chart 19 is written up in `docs/PLANARSVIZ_LIBRARY_PROGRESS.md`, at the end,
as its own section: the bundle table, the null-draws sizing question, the
`data-contract.md` section it needs, and — the part worth not losing — that
this is the one port with no matplotlib original, so
`results/nyan1308_fragmentation_test_plot.pdf` is itself the reference. Your
open question about whether the test should also run per subset is recorded
there as an open question for Jeff, not decided by me.

I have not started it. C4 finished the cutover and that is where I stopped;
Jeff decides what comes next between chart 19 and phase E.

## One change I made to your R script

`fragmentation_test_plot.r` resolved `results/` as `"../../results"` against
the working directory, so it only ran from `scripts/analysis/`. Both
`scripts/INDEX.md` and `results/visualizations.md` told a reader to run it
from elsewhere, so the documented command failed. It now resolves from its own
file location, the way `render_planarsviz.R` does, and runs from anywhere.

The chart is unchanged — I rendered it before and after and pixel-compared:
0.0000% differing. Nothing else in the file was touched beyond two comments
naming scripts that C2 archived and C3 deleted.

## What moved under you

- The generated R scripts and the Python that wrote them are gone from the
  working tree. Archived in `OlderFiles/planarsviz_superseded/`; the porting
  checks still run them.
- `laminar_analysis.py` is 865 lines, down from 1808. `main()` lost
  `output_dir`, `color`, `tpfx` and `pos_labels` and now writes nothing.
  `load_domain_dataframe()`, `aggregate_spans()`, `load_spans()`,
  `select_representative_families()` and `OVERLAY_GROUPS` are all intact.
- `laminar_tree_counts.py` and `boundary_strength.py` kept their counting and
  lost their matplotlib. `CLASS_COLORS` survived and is now the only place
  those five colours are written down — the exporter's `DOMAIN_TYPE_STYLE`
  reads them from it.
- `make_forestspans_table_no_tono.py` is deleted; the library draws that chart
  from the bundle's `subsets/no_tono/`.

## Working directory

Everything under `NonCollaborative/` is now documented as running from
`NonCollaborative/`, which is where the porting checks already ran. This
matters for the exporter specifically: it records the domain file's path as
you give it, so running it from the repo root writes a bundle that differs
from the committed one in that field. `results/visualizations.md` and
`scripts/INDEX.md` both say so now.

## No collision

Nothing of mine is mid-edit. If you pick up chart 19, `class_fragmentation_
test.py`, `fragmentation_test_plot.r`, `export_planarsviz_data.py` and
`data-contract.md` are all yours — tell me in a note and I will stay out of
them.
