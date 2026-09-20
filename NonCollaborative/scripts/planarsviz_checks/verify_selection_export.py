"""Check the exporter's selections against the trees drawn by the scripts
whose generator was never committed.

For charts 10 and 12-14 (docs/PLAN_planarsviz_library.md section 4.1): the
archived nyan1308_exemplary_trees.r, laminar_freqtree.r, laminar_four_trees.r
and laminar_conflict_groups.r (see superseded.py) each paste in the Newick string of every tree they draw. This checks that the
bundle's families.tsv newick for the families named in selections.tsv
(exemplary ranks, consensus_all, consensus_<group>) and in
conflict_groups.tsv (all families, then each group's drawn members in
draw_rank order) reproduces those strings in drawing order.

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_selection_export.py
"""

import csv
import re
from pathlib import Path

from superseded import superseded

NC = Path(__file__).resolve().parents[2]
DATA = NC / "results" / "planarsviz" / "nyan1308" / "data"
ok = True


def read(name):
    with (DATA / name).open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def check(label, drawn, expected):
    global ok
    same = drawn == expected
    ok = ok and same
    print(f"{label}: {len(drawn)} drawn, {len(expected)} from bundle, {'identical' if same else 'MISMATCH'}")


newick = {row["family_id"]: row["newick"] for row in read("families.tsv")}
selection_rows = read("selections.tsv")
selection = {row["selection"]: row["family_id"] for row in selection_rows if row["rank"] == "1"}

exemplary = sorted((r for r in selection_rows if r["selection"] == "exemplary"), key=lambda r: int(r["rank"]))
trees = re.findall(r'ex_tree\d+ <- read\.tree\(text="([^"]+)"\)', superseded("results", "nyan1308_exemplary_trees.r").read_text())
check("exemplary trees", trees, [newick[r["family_id"]] for r in exemplary])
groups = read("conflict_groups.tsv")
group_ids = list(dict.fromkeys(row["group_id"] for row in groups))

trees = re.findall(r'read\.tree\(text="([^"]+)"\)', superseded("results", "laminar_freqtree.r").read_text())
check("freqtree", trees, [newick[selection["consensus_all"]]])

trees = re.findall(r'read\.tree\(text="([^"]+)"\)', superseded("results", "laminar_four_trees.r").read_text())
check("four trees", trees, [newick[selection[f"consensus_{g}"]] for g in ["all"] + group_ids])

text = superseded("results", "laminar_conflict_groups.r").read_text()
check("conflict groups: all", re.findall(r'all_tree\d+ <- read\.tree\(text="([^"]+)"\)', text),
      [newick[row["family_id"]] for row in read("families.tsv")])
for group_id in group_ids:
    ranked = sorted((r for r in groups if r["group_id"] == group_id and r["draw_rank"]),
                    key=lambda r: int(r["draw_rank"]))
    prefix = "g" + group_id.lower()
    check(f"conflict groups: {group_id}",
          re.findall(prefix + r'_tree\d+ <- read\.tree\(text="([^"]+)"\)', text),
          [newick[r["family_id"]] for r in ranked])
print("ALL SELECTION EXPORT CHECKS PASSED" if ok else "SOME CHECKS FAILED")
