"""Check the exporter's per-class forests against the generated forest scripts.

For chart 6 (docs/PLAN_planarsviz_library.md): every archived
nyan1308_<id>_laminar_forest.r (see superseded.py) was written by
laminar_analysis.generate_r_script(). This checks
that data/forests/<id>.tsv reproduces, tree by tree, the Newick string, the
groupOTU span list, the thickness values, and that forests.json has the same
alpha, colour and tree count. It also checks that moving BUNDLES into
planars_groupings.py changed nothing: laminar_tree_counts' bundle counts
still equal results/nyan1308_tree_counts.tsv, and laminar_analysis.main()
still writes byte-identical forest scripts for the bundles (ignoring the
ggsave line, which embeds the output path).

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_forest_export.py
"""

import contextlib
import csv
import io
import json
import re
import sys
import tempfile
from pathlib import Path

from superseded import superseded

NC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(NC / "scripts" / "analysis"))
DATA = NC / "results" / "planarsviz" / "nyan1308" / "data"
ok = True


def fail(msg):
    global ok
    ok = False
    print("  MISMATCH:", msg)


index = json.loads((DATA / "forests.json").read_text())
for meta in index:
    fid = meta["forest_id"]
    text = superseded("results", f"nyan1308_{fid}_laminar_forest.r").read_text()
    alpha = float(re.search(r"alphaval <- ([0-9.]+) / 2", text).group(1))
    colour = re.search(r'color="(#[0-9A-Fa-f]{6})"', text).group(1)
    newicks = re.findall(r'read\.tree\(text="([^"]+)"\)', text)
    groups = [
        ";".join(f"{a}-{b}" for a, b in re.findall(r"[a-z] = c\((\d+), (\d+)\)", g))
        for g in re.findall(r"groupOTU\([^,]+, list\(([^)]*\)[^\n]*)\)\n", text)
    ]
    strengths = [s.split(", ")[1:] for s in re.findall(r"strengthMap\d+ <- c\(([^)]*)\)", text)]
    rows = list(csv.DictReader((DATA / "forests" / f"{fid}.tsv").open(), delimiter="\t"))
    print(f"{fid}: {len(rows)} trees, alpha {meta['alpha']}, colour {meta['colour']}, n_positions {meta['n_positions']}")
    if abs(alpha - meta["alpha"]) > 1e-9:
        fail(f"{fid}: alpha {alpha} vs {meta['alpha']}")
    if colour != meta["colour"]:
        fail(f"{fid}: colour {colour} vs {meta['colour']}")
    if not (len(newicks) == len(groups) == len(strengths) == len(rows) == meta["n_trees"]):
        fail(f"{fid}: counts script {len(newicks)}/{len(groups)}/{len(strengths)} vs export {len(rows)}/{meta['n_trees']}")
        continue
    for i, row in enumerate(rows):
        if row["newick"] != newicks[i]:
            fail(f"{fid} tree {i + 1}: newick differs")
        if row["group_spans"] != groups[i]:
            fail(f"{fid} tree {i + 1}: groups {row['group_spans']} vs {groups[i]}")
        if [float(v) for v in row["strengths"].split(";")] != [float(v) for v in strengths[i]]:
            fail(f"{fid} tree {i + 1}: strengths differ")

# BUNDLES refactor checks
import laminar_analysis as la  # noqa: E402
import laminar_tree_counts as ltc  # noqa: E402
from planars_groupings import BUNDLES  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    bundle_rows = ltc.collect_bundle_counts("domains_nyan1308.tsv", NC / "domains")
committed = {(r["condition"], r["class"]): r for r in csv.DictReader(
    (NC / "results" / "nyan1308_tree_counts.tsv").open(), delimiter="\t")}
for r in bundle_rows:
    c = committed.get((r["condition"], r["class"]))
    if c is None or int(c["n_maximal_laminar_families"]) != r["n_maximal_laminar_families"] \
            or int(c["n_unique_spans"]) != r["n_unique_spans"]:
        fail(f"tree counts for {r['class']} differ from nyan1308_tree_counts.tsv")
print(f"tree-count bundles checked: {len(bundle_rows)}")

with tempfile.TemporaryDirectory() as tmp:
    for name, subset, colour, _ in BUNDLES:
        with contextlib.redirect_stdout(io.StringIO()):
            la.main(subset=subset, color=colour, tpfx=f"nyan1308_{name}_", output_dir=tmp,
                    domains_dir=str(NC / "domains"), show_trees=False)
        new = [l for l in (Path(tmp) / f"nyan1308_{name}_laminar_forest.r").read_text().splitlines() if not l.startswith("ggsave(")]
        old = [l for l in superseded("results", f"nyan1308_{name}_laminar_forest.r").read_text().splitlines() if not l.startswith("ggsave(")]
        if new != old:
            fail(f"laminar_analysis.main() output for bundle {name} differs from the committed script")
print("bundle forest scripts regenerated and compared:", len(BUNDLES))
print("ALL FOREST EXPORT CHECKS PASSED" if ok else "SOME CHECKS FAILED")
