"""Compare every PNG the renderer wrote with the frozen reference images.

For docs/PLAN_planarsviz_library.md section 8.3: after
    Rscript scripts/render_planarsviz.R --bundle results/planarsviz/nyan1308 --output DIR --formats pdf,png
run
    python scripts/planarsviz_checks/check_renderer.py DIR
Reads DIR's <dataset>_planarsviz_manifest.tsv, pairs each nyan1308_<chart>.png with
results/planarsviz/reference/nyan1308_<chart>.png, and prints the
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
REFERENCE = NC / "results" / "planarsviz" / "reference"
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

out_dir = Path(sys.argv[1])
compare_dir = out_dir / "compare"
compare_dir.mkdir(exist_ok=True)
manifests = sorted(out_dir.glob("*_planarsviz_manifest.tsv"))
if len(manifests) != 1:
    names = ", ".join(m.name for m in manifests) or "none"
    sys.exit(f"{out_dir} should hold exactly one *_planarsviz_manifest.tsv; found: {names}")
with manifests[0].open(newline="") as handle:
    rows = [r for r in csv.DictReader(handle, delimiter="\t") if r["file"].endswith(".png")]

seen = set()
problems = 0
for row in rows:
    chart = row["chart"]
    ref_name = f"nyan1308_{RENAMED.get(chart, chart)}.png"
    seen.add(ref_name)
    ref = REFERENCE / ref_name
    if not ref.exists():
        print(f"{chart:48} no reference")
        continue
    result = subprocess.run(
        [sys.executable, str(NC / "scripts" / "planarsviz_compare.py"), str(ref),
         str(out_dir / row["file"]), str(compare_dir / row["file"])],
        capture_output=True, text=True).stdout.strip()
    is_port = chart.startswith(PORTS[0]) or chart in PORTS[1:] and "overlay" not in chart
    exact = "differing_pixels=0.0000%" in result and "size_match=True" in result
    if chart in CHANGED:
        result += "   (deliberate change)"
    flag = "" if exact or is_port or chart in CHANGED else "   <-- NOT EXACT"
    problems += bool(flag)
    print(f"{chart:48} {result}{flag}")

missing = sorted(p.name for p in REFERENCE.glob("nyan1308_*.png") if p.name not in seen)
print(f"\n{len(rows)} renders compared; references with no render: {missing or 'none'}")
print("RENDERER CHECK PASSED" if not problems else f"RENDERER CHECK: {problems} copied chart(s) not exact")
