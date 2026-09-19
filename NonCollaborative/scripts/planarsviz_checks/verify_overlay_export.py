"""Check the exporter's overlay groups against the generated overlay scripts.

For charts 7-9 (docs/PLAN_planarsviz_library.md): results/nyan1308_laminar_overlay.r
(five coloured groups, thickness exponent 0.5, alpha divisor 2) and
results/nyan1308_all_families_labeled.r (one black "all" group, exponent 0.75,
divisor 1) were written by laminar_analysis.generate_r_overlay_script(). This
checks data/overlay_groups/<id>.tsv reproduces, tree by tree, each script's
Newick strings, groupOTU span lists, colours, and thickness values once the
script's exponent is applied to the exported convergence, and that alpha
follows (1 - 0.01^(1/total trees)) / divisor. The wordhood script differs from
the all-families script only in its label lines (checked separately by diff).

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_overlay_export.py
"""

import csv
import json
import re
import sys
from pathlib import Path

NC = Path(__file__).resolve().parents[2]
DATA = NC / "results" / "planarsviz" / "nyan1308" / "data"
ok = True


def fail(msg):
    global ok
    ok = False
    print("  MISMATCH:", msg)


index = {g["group_id"]: g for g in json.loads((DATA / "overlay_groups.json").read_text())}

CASES = [
    ("nyan1308_laminar_overlay.r", 0.5, 2.0),
    ("nyan1308_all_families_labeled.r", 0.75, 1.0),
]
for script_name, exponent, divisor in CASES:
    text = (NC / "results" / script_name).read_text()
    sections = re.split(r"^# ── (\w+): (\d+) families ──$", text, flags=re.M)
    alpha = float(re.search(r"^alphaval <- ([0-9.]+)$", text, flags=re.M).group(1))
    total = 0
    print(script_name)
    for j in range(1, len(sections), 3):
        gid, n, body = sections[j], int(sections[j + 1]), sections[j + 2]
        total += n
        meta = index.get(gid)
        if meta is None:
            fail(f"group {gid} not exported")
            continue
        colour = re.search(r'color="([^"]+)"', body).group(1)
        newicks = re.findall(r'read\.tree\(text="([^"]+)"\)', body)
        groups = [";".join(f"{a}-{b}" for a, b in re.findall(r"[a-z] = c\((\d+), (\d+)\)", g))
                  for g in re.findall(r"groupOTU\([^,]+, list\((.*)\)\)\n", body)]
        smaps = [[float(v) for v in s.split(", ")[1:]] for s in re.findall(r"smap\d+ <- c\(([^)]*)\)", body)]
        rows = list(csv.DictReader((DATA / "overlay_groups" / f"{gid}.tsv").open(), delimiter="\t"))
        print(f"  {gid}: script {n} trees, export {len(rows)} trees, colour {colour}")
        if colour != meta["colour"]:
            fail(f"{gid}: colour {colour} vs {meta['colour']}")
        if not (n == len(newicks) == len(groups) == len(smaps) == len(rows) == meta["n_trees"]):
            fail(f"{gid}: tree counts differ")
            continue
        for i, row in enumerate(rows):
            if row["newick"] != newicks[i]:
                fail(f"{gid} tree {i + 1}: newick")
            if row["group_spans"] != groups[i]:
                fail(f"{gid} tree {i + 1}: groups")
            thick = [round(max(int(c), 1) ** exponent, 4) for c in row["group_convergence"].split(";")]
            if thick != smaps[i]:
                fail(f"{gid} tree {i + 1}: thickness {thick} vs {smaps[i]}")
    expected_alpha = round((1 - 0.01 ** (1 / total)) / divisor, 6)
    if abs(expected_alpha - alpha) > 1e-9:
        fail(f"{script_name}: alpha {alpha} vs formula {expected_alpha} over {total} trees")
    else:
        print(f"  alpha {alpha} = formula over {total} trees")

plain = (NC / "results" / "nyan1308_all_families_labeled.r").read_text().splitlines()
word = (NC / "results" / "nyan1308_all_families_labeled_wordhood.r").read_text().splitlines()
extra = [l for l in word if l not in set(plain)]
print(f"wordhood script lines not in the all-families script: {len(extra)}")
print("ALL OVERLAY EXPORT CHECKS PASSED" if ok else "SOME CHECKS FAILED")
