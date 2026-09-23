"""Check the bundle's boundary-strength tables equal boundary_strength.py's.

For charts 17-18 (docs/PLAN_planarsviz_library.md section 4.3, step 1): the
exporter calls compute_boundary_strength() for the full data and for each
subset analysis. This checks data/boundary_strength.tsv against
results/nyan1308/boundaries/nyan1308_boundary_strength.tsv, and
data/subsets/no_tono/boundary_strength.tsv against
results/nyan1308/boundaries/nyan1308_boundary_strength_no_tono.tsv, row for row.

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_boundary_strength_export.py
"""

import csv
from pathlib import Path

NC = Path(__file__).resolve().parents[2]
DATA = NC / "results" / "chart_data" / "nyan1308" / "data"
COLUMNS = ["position", "left_summed", "left_capped", "right_summed", "right_capped"]
ok = True


def read(path):
    with path.open(newline="") as handle:
        return [[row[c] for c in COLUMNS] for row in csv.DictReader(handle, delimiter="\t")]


for script_table, bundle_table in [
    ("nyan1308_boundary_strength.tsv", DATA / "boundary_strength.tsv"),
    ("nyan1308_boundary_strength_no_tono.tsv", DATA / "subsets" / "no_tono" / "boundary_strength.tsv"),
]:
    a, b = read(NC / "results" / "nyan1308" / "boundaries" / script_table), read(bundle_table)
    same = a == b
    ok = ok and same
    print(f"{script_table}: {len(a)} rows vs bundle {len(b)}: {'identical' if same else 'MISMATCH'}")
print("BOUNDARY STRENGTH EXPORT CHECKS PASSED" if ok else "SOME CHECKS FAILED")
