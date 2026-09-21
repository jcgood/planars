"""Check the bundle's tree counts equal laminar_tree_counts.py's own table.

For chart 16 (docs/PLAN_planarsviz_library.md section 4.3, step 1): the
exporter calls collect_counts() and collect_bundle_counts(); this checks
data/tree_counts.tsv has exactly the rows of
results/counts-and-chance/nyan1308_tree_counts.tsv
(condition, class, n_unique_spans, n_maximal_laminar_families), in order.

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_tree_counts_export.py
"""

import csv
from pathlib import Path

NC = Path(__file__).resolve().parents[2]
COLUMNS = ["condition", "class", "n_unique_spans", "n_maximal_laminar_families"]


def read(path):
    with path.open(newline="") as handle:
        return [[row[c] for c in COLUMNS] for row in csv.DictReader(handle, delimiter="\t")]


script_rows = read(NC / "results" / "counts-and-chance" / "nyan1308_tree_counts.tsv")
bundle_rows = read(NC / "results" / "planarsviz" / "nyan1308" / "data" / "tree_counts.tsv")
same = script_rows == bundle_rows
print(f"script table {len(script_rows)} rows, bundle {len(bundle_rows)} rows: {'identical' if same else 'MISMATCH'}")
if not same:
    for a, b in zip(script_rows, bundle_rows):
        if a != b:
            print("   script", a, "bundle", b)
print("TREE COUNT EXPORT CHECK PASSED" if same else "TREE COUNT EXPORT CHECK FAILED")
