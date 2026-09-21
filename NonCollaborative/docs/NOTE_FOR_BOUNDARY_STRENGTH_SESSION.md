# Note for the boundary-strength session

From the `results/` restructure session, 2026-09-20. **Your next push will be
refused by the roxygen guard, and committing your work is what clears it —
for both of us.** Everything else here is context you will want before you
touch `r/planarsviz/` again.

## Your files, and what I did with them

Jeff confirmed this work is yours, so I left all of it alone — not committed,
not reverted, not moved:

- `r/planarsviz/R/boundary_strength_test.R` (untracked)
- `r/planarsviz/man/plot_boundary_strength_test.Rd` and
  `read_planars_boundary_strength_test.Rd` (untracked)
- `r/planarsviz/NAMESPACE` (modified — now exports `plot_boundary_strength_test`)
- `scripts/analysis/boundary_strength.py` (modified — `strength_from_families()`
  split out of `compute_boundary_strength()`)
- `scripts/analysis/boundary_strength_test.py` (untracked)
- `scripts/analysis/export_planarsviz_data.py` (modified)
- `results/nyan1308_boundary_strength_test.tsv` (untracked)

I staged my own commit by naming each file rather than with a blanket `add`,
so none of the above is in it.

## Why the push fails

`.pre-commit-config.yaml` runs the `roxygen-up-to-date` check before every
push where anything under `r/planarsviz/` changed. It regenerates `NAMESPACE`
from the R sources **as they sit in the working tree** and compares it with
the committed one.

It stashes *unstaged* changes first — but an *untracked* file is not stashed.
So roxygen reads `boundary_strength_test.R`, writes
`export(plot_boundary_strength_test)`, and the comparison fails. My push died
on exactly this. Yours will too, and for a slightly meaner reason: your
`NAMESPACE` edit *is* unstaged, so it gets stashed away while the untracked
`.R` file stays — the guard compares a NAMESPACE without your export against a
regeneration with it.

**The fix is to commit the work as one unit**: `boundary_strength_test.R`,
both new `man/` pages, the regenerated `NAMESPACE`, `boundary_strength.py`,
`boundary_strength_test.py`, and the results TSV if you want it tracked. Once
the sources and `NAMESPACE` agree inside one commit, the guard passes.

**Please don't reach for `--no-verify`.** That guard has already been
disarmed once without anyone noticing — `renv` turned it from a pass into a
skip, and a skip reads as a pass. It is worth keeping honest.

## What changed under you in `r/planarsviz/`

I have a commit ready (`064952d`, local only until the push clears) that adds
a `planarsviz_folder` attribute to every chart function, set right beside the
`planarsviz_size` attribute that was already there. It names which subfolder
of `results/planarsviz/` that chart's images live in.

`results/planarsviz/reference/` and `comparisons/` are no longer flat. They
are grouped into `laminar-families/`, `pooled/`, `boundaries/` and
`counts-and-chance/`, and the 14 porting checks now read the attribute to find
the right one. The same commit regenerated all 15 existing `man/` pages to
document the new attribute — so your roxygen run and mine both write to
`man/`.

**Two things this asks of you:**

1. **Set the attribute on your chart.** Next to wherever
   `plot_boundary_strength_test()` sets `planarsviz_size`, add
   `attr(p, "planarsviz_folder") <- "boundaries"`, matching the other boundary
   charts. Without it, a porting check for your chart will not know where its
   reference image lives.
2. **Whichever of us lands first, build on it.** Regenerate `NAMESPACE` and
   `man/` on top of the other's commit rather than resolving a conflict in
   those generated files by hand.

## The one step that cannot be undone

If your chart writes a PDF into `results/`, **freeze a reference image for it
before the package ever draws that file**:

```
pdftoppm -png -r 100 -singlefile results/nyan1308_<name>.pdf \
  results/planarsviz/reference/boundaries/nyan1308_<name>
```

Run it from `NonCollaborative/`. Once the package overwrites a chart that a
script drew, the evidence that the port was faithful is gone, and no later
check can recover it. This is why the restructure's first step was freezing 26
of them (`e3ae9c8`) before anything else moved.

## Two red tests you may trip over, neither yours

- `test_namespace_and_man_match_roxygen2_output` — the one above. Clears when
  you commit.
- `test_renderer_check_reports_what_it_did` — its snapshot says "references
  with no render: none", recorded before those 26 references existed. The
  check now correctly lists all 26. It fails the same way on a clean checkout.
  Mine to fix; don't re-record it.

## Where the restructure is

Step 1 (freeze 26 references) pushed as `e3ae9c8`. Step 2 (group the
check-side images, add the attribute) committed as `064952d`, waiting on the
push. Still to come: moving `results/` itself into six folders, then absorbing
the last four chart producers into the package. Full account in
`docs/PLANARSVIZ_LIBRARY_PROGRESS.md`, last three entries.
