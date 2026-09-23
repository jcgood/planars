"""Build the shifted copy of nyan1308 used to catch hard-coded nyan1308 facts.

See docs/PLAN_planarsviz_library.md section 10. The analytical structure is
unchanged; only facts a chart might have typed in are changed:

- every Left_Edge/Right_Edge + SHIFT, so the data covers positions 3-24 and
  positions 1-2 are empty (breaks "22 positions", "the full span starts at 1");
- the planar table gets SHIFT new leading positions, so the root is at 12
  (breaks "root at 10");
- every display label is renamed (breaks hard-coded position names);
- tonosegmental is renamed tonal (breaks hard-coded domain-type names and
  colours; tonal gets the exporter's fallback colour);
- the position highlights and the conflict groups' defining spans move with
  the positions (breaks hard-coded ranges such as the orthographic word at
  5-19 or the [5-13]/[6-17] conflict).

Not to be confused with domains/domains_nyan1293_test.tsv, an older,
unrelated test file.

Usage (from NonCollaborative/):
    python tests/fixtures/make_shifted_nyan.py

Writes tests/fixtures/domains_shifted_nyan.tsv, planar_shifted_nyan.tsv,
display_labels_shifted_nyan.tsv, highlights_shifted_nyan.tsv and
conflict_groups_shifted_nyan.tsv. Export its bundle with:
    python scripts/analysis/export_planarsviz_data.py \\
        --domain-file tests/fixtures/domains_shifted_nyan.tsv \\
        --planar-file tests/fixtures/planar_shifted_nyan.tsv \\
        --labels-file tests/fixtures/display_labels_shifted_nyan.tsv \\
        --highlights-file tests/fixtures/highlights_shifted_nyan.tsv \\
        --conflict-groups-file tests/fixtures/conflict_groups_shifted_nyan.tsv \\
        --language-name "Shifted test data" \\
        --output-dir results/chart_data
"""

import csv
from pathlib import Path

SHIFT = 2
RENAMED_TYPES = {"tonosegmental": "tonal"}

NC = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent


def main():
    src_domains = NC / "domains" / "domains_nyan1308.tsv"
    lines = src_domains.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    li, ri, ti = header.index("Left_Edge"), header.index("Right_Edge"), header.index("Domain_Type")
    out = [lines[0]]
    for line in lines[1:]:
        if not line.strip():
            out.append(line)
            continue
        cells = line.split("\t")
        cells[li] = str(int(cells[li]) + SHIFT)
        cells[ri] = str(int(cells[ri]) + SHIFT)
        cells[ti] = RENAMED_TYPES.get(cells[ti].strip(), cells[ti])
        out.append("\t".join(cells))
    (FIXTURES / "domains_shifted_nyan.tsv").write_text("\n".join(out) + "\n", encoding="utf-8")

    with (NC / "planar_tables" / "planar_nyan1308.tsv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        rows = list(reader)
    new_rows = []
    for i in range(1, SHIFT + 1):
        new_rows.append({f: "" for f in fields} | {
            "Language_ID": "shifted_nyan", "Planar_Type": "verbal", "Position": str(i),
            "Position_Label": f"N{i}", "Position_Type": "Slot", "Elements": f"new{i}",
            "Description": f"added position {i} (test fixture)",
        })
    for row in rows:
        new_rows.append(dict(row, Language_ID="shifted_nyan",
                             Position=str(int(row["Position"]) + SHIFT),
                             Position_Label="s" + row["Position_Label"]))
    with (FIXTURES / "planar_shifted_nyan.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(new_rows)

    with (NC / "planar_tables" / "display_labels_nyan1308.tsv").open(encoding="utf-8", newline="") as handle:
        labels = list(csv.DictReader(handle, delimiter="\t"))
    display = [{"position": i, "label": f"New{i}"} for i in range(1, SHIFT + 1)]
    display += [{"position": int(r["position"]) + SHIFT, "label": "x" + r["label"]} for r in labels]
    with (FIXTURES / "display_labels_shifted_nyan.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["position", "label"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(display)
    with (NC / "planar_tables" / "highlights_nyan1308.tsv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        hl_fields = reader.fieldnames
        highlights = list(reader)
    with (FIXTURES / "highlights_shifted_nyan.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=hl_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(dict(row, left=str(int(row["left"]) + SHIFT), right=str(int(row["right"]) + SHIFT))
                         for row in highlights)
    with (NC / "planar_tables" / "conflict_groups_nyan1308.tsv").open(encoding="utf-8", newline="") as handle:
        groups = list(csv.DictReader(handle, delimiter="\t"))
    with (FIXTURES / "conflict_groups_shifted_nyan.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["group_id", "defining_span_id"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in groups:
            span = (row["defining_span_id"] or "").strip()
            if span:
                left, right = map(int, span.split("-"))
                span = f"{left + SHIFT}-{right + SHIFT}"
            writer.writerow({"group_id": row["group_id"], "defining_span_id": span})
    print("wrote", ", ".join(p.name for p in sorted(FIXTURES.glob("*shifted_nyan.tsv"))))


if __name__ == "__main__":
    main()
