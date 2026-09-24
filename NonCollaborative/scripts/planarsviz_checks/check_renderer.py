"""Compare every PNG the renderer wrote with the frozen reference images.

For docs/PLAN_planarsviz_library.md section 8.3: after
    Rscript scripts/render_planarsviz.R --bundle results/chart_data/nyan1308 --output DIR --formats pdf,png
run
    python scripts/planarsviz_checks/check_renderer.py DIR
Reads DIR/<dataset>/<dataset>_planarsviz_manifest.tsv, pairs each
<dataset>/<folder>/<dataset>_<chart>.png with
results/chart_checks/reference/<dataset>/<folder>/<dataset>_<chart>.png (the
dataset is the folder the manifest sits in, not a fixed name, so this works
for whichever dataset DIR was rendered from), and prints the
differing-pixel share per chart (side-by-side images go to DIR/compare/).
Charts copied from working R code must show 0.0000%; the two matplotlib
ports (tree_count_*, boundary_strength, _no_tono, _distributions) differ by
fonts, as recorded in the progress file. It also lists references with no
render and renders with no reference.

The only name mapping: the renderer names highlight variants after the
highlight id (all_families_labeled_orthographic_word), where the old file
was all_families_labeled_wordhood.
"""

import csv
import subprocess
import sys
from pathlib import Path

NC = Path(__file__).resolve().parents[2]
REFERENCE = NC / "results" / "chart_checks" / "reference"
RENAMED = {"all_families_labeled_orthographic_word": "all_families_labeled_wordhood",
           "all_families_labeled_orthographic_word_legend": "all_families_labeled_wordhood_legend"}
PORTS = ("tree_count_", "boundary_strength", "boundary_strength_no_tono", "boundary_strength_distributions")
# Deliberately changed on 2026-09-15 at Jeff's request, so they no longer
# match the old files: conflict-group panel titles now show; the overlay
# legend's thickness swatch follows the lines' exponent (0.75 here).
CHANGED = {"conflict_groups", "all_families_labeled_legend",
           "all_families_labeled_orthographic_word_legend",
           # 2026-09-16: the ForestSpans legend moved into the panel's empty
           # lower-left corner, in a bordered box.
           "forestspans_plot", "forestspans_plot_no_tono",
           # 2026-09-19: the span chart's axis shows every position, not just
           # the stretch the drawn spans cover.
           "spanchart"}

# Reference images live under reference/<topic folder>/, and the manifest's
# file column now carries that same folder, so a reference is found at the
# address the manifest gives rather than by hunting for its filename.
ref_by_name = {}
for path in REFERENCE.rglob("*.png"):
    ref_by_name[path.relative_to(REFERENCE).as_posix()] = path

out_dir = Path(sys.argv[1])
compare_dir = out_dir / "compare"
compare_dir.mkdir(exist_ok=True)
# Each dataset's manifest sits in that dataset's own folder, and its file
# column is relative to that folder.
manifests = sorted(out_dir.glob("*/*_planarsviz_manifest.tsv"))
if len(manifests) != 1:
    names = ", ".join(m.relative_to(out_dir).as_posix() for m in manifests) or "none"
    sys.exit(f"{out_dir} should hold exactly one <dataset>/*_planarsviz_manifest.tsv; found: {names}")
dataset = manifests[0].parent.name
with manifests[0].open(newline="") as handle:
    rows = [r for r in csv.DictReader(handle, delimiter="\t") if r["file"].endswith(".png")]
for row in rows:
    row["file"] = f"{dataset}/{row['file']}"

seen = set()
datasets = set()
problems = 0
for row in rows:
    chart = row["chart"]
    folder = Path(row["file"]).parent.as_posix()
    dataset = Path(row["file"]).parts[0]
    datasets.add(dataset)
    ref_name = f"{folder}/{dataset}_{RENAMED.get(chart, chart)}.png"
    seen.add(ref_name)
    ref = ref_by_name.get(ref_name)
    if ref is None:
        print(f"{chart:48} no reference")
        continue
    comparison = compare_dir / row["file"]
    comparison.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(NC / "scripts" / "planarsviz_compare.py"), str(ref),
         str(out_dir / row["file"]), str(comparison)],
        capture_output=True, text=True).stdout.strip()
    is_port = chart.startswith(PORTS[0]) or chart in PORTS[1:] and "overlay" not in chart
    exact = "differing_pixels=0.0000%" in result and "size_match=True" in result
    if chart in CHANGED:
        result += "   (deliberate change)"
    flag = "" if exact or is_port or chart in CHANGED else "   <-- NOT EXACT"
    problems += bool(flag)
    print(f"{chart:48} {result}{flag}")

# *_transp.png are not chart references: they are the frozen matplotlib
# transparency measurements check_tree_counts.R compares against, kept here
# because cutover step C3 removed the matplotlib that drew them.
# Restricted to the dataset(s) this run's manifest actually covers, so running
# the renderer for one dataset doesn't report every other dataset's whole
# reference tree as "no render".
missing = sorted(name for name in ref_by_name
                 if Path(name).parts[0] in datasets and name not in seen
                 and not name.endswith("_transp.png"))
# One per line rather than a list on one line: this is the standing list of
# charts still to be absorbed into the package, so it wants to read as a list
# and to shrink a name at a time as each one lands.
if missing:
    print(f"\n{len(rows)} renders compared; {len(missing)} references with no render:")
    for name in missing:
        print(f"  {name}")
else:
    print(f"\n{len(rows)} renders compared; references with no render: none")
print("RENDERER CHECK PASSED" if not problems else f"RENDERER CHECK: {problems} copied chart(s) not exact")
