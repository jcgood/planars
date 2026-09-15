"""Check the exporter's numpy density against scipy itself.

The exporter rebuilds boundary_strength.py's
gaussian_kde(positions, weights=summed, bw_method=0.15) in numpy
(export_planarsviz_data.weighted_gaussian_kde) because scipy was once
missing. This recomputes the curves with scipy on the same grid and reports
the largest difference from data/boundary_strength_density.tsv, for the
full analysis and every subset.

Run from NonCollaborative/:
    python scripts/planarsviz_checks/verify_boundary_density.py
"""

import csv
from pathlib import Path

import numpy as np
from scipy.stats import gaussian_kde

NC = Path(__file__).resolve().parents[2]
DATA = NC / "results" / "planarsviz" / "nyan1308" / "data"
TOLERANCE = 1e-12
ok = True


def read(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


for analysis in [DATA] + sorted(p for p in (DATA / "subsets").iterdir() if p.is_dir()):
    strength = read(analysis / "boundary_strength.tsv")
    density = read(analysis / "boundary_strength_density.tsv")
    positions = np.array([float(r["position"]) for r in strength])
    grid = np.array([float(r["x"]) for r in density])
    worst = 0.0
    for side in ("left", "right"):
        weights = np.array([float(r[f"{side}_summed"]) for r in strength])
        exported = [r[side] for r in density]
        if np.count_nonzero(weights) < 2:
            assert all(v == "" for v in exported), f"{analysis.name} {side}: expected empty"
            continue
        reference = gaussian_kde(positions, weights=weights, bw_method=0.15)(grid)
        worst = max(worst, float(np.max(np.abs(np.array(exported, dtype=float) - reference))))
    same = worst <= TOLERANCE
    ok = ok and same
    print(f"{analysis.name:16} largest difference from scipy {worst:.3e}: {'identical' if same else 'DIFFERENT'}")
print("DENSITY MATCHES SCIPY" if ok else "DENSITY DIFFERS FROM SCIPY")
