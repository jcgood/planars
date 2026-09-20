"""Check the bundle reproduces the ForestSpans charts' pasted span tables.

For chart 11 (docs/PLAN_planarsviz_library.md): the archived
nyan1308_forestspans_plot.r and nyan1308_forestspans_plot_no_tono.r (see
superseded.py) paste in one row per span --
Layer, Left, Right, Count, Color -- and the tree count. This rebuilds those
rows from the bundle the way plot_forestspans() does: observed spans only
(synthetic root dropped), Layer = size rank inverted (sort by size then left
edge; the largest span is 1), rows by Count descending then Layer, Color =
spans.tsv blend_colour; tree count = rows of families.tsv. The full chart
reads data/, the no-tono chart data/subsets/no_tono/.

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_forestspans_export.py
"""

import csv
import re
from pathlib import Path

from superseded import superseded

NC = Path(__file__).resolve().parents[2]
DATA = NC / "results" / "planarsviz" / "nyan1308" / "data"
ok = True

for script, data_dir in [("nyan1308_forestspans_plot.r", DATA),
                         ("nyan1308_forestspans_plot_no_tono.r", DATA / "subsets" / "no_tono")]:
    text = superseded("results", script).read_text()
    pasted = [(int(a), int(b), int(c), int(d), e) for a, b, c, d, e in
              re.findall(r'^  (\d+), (\d+), (\d+), (\d+), "(#[0-9A-F]{6})",$', text, flags=re.M)]
    n_trees = int(re.search(r'Trees\\n\(n = (\d+)\)', text).group(1))

    with (data_dir / "spans.tsv").open(newline="") as handle:
        spans = [r for r in csv.DictReader(handle, delimiter="\t") if r["synthetic"] != "True"]
    with (data_dir / "families.tsv").open(newline="") as handle:
        n_families = sum(1 for _ in csv.DictReader(handle, delimiter="\t"))
    ordered = sorted(spans, key=lambda r: (int(r["size"]), int(r["left"])))
    layer = {r["span_id"]: len(ordered) + 1 - i for i, r in enumerate(ordered, start=1)}
    rebuilt = sorted(
        ((layer[r["span_id"]], int(r["left"]), int(r["right"]), int(r["family_frequency"]), r["blend_colour"])
         for r in spans),
        key=lambda row: (-row[3], row[0]))

    same = pasted == rebuilt and n_trees == n_families
    ok = ok and same
    print(f"{script}: {len(pasted)} pasted rows, {len(rebuilt)} from bundle; "
          f"trees {n_trees} vs {n_families}: {'identical' if same else 'MISMATCH'}")
    if not same:
        for p, b in zip(pasted, rebuilt):
            if p != b:
                print("   pasted", p, "bundle", b)
print("ALL FORESTSPANS EXPORT CHECKS PASSED" if ok else "SOME CHECKS FAILED")
