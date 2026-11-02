"""laminar/contributor_charts.combine(): one PDF from the renderer's charts.

No R: the "charts" are blank pages and the manifest is written here. What is
checked: chapters in PARTS order, each opened by a divider listing its
charts with the right page numbers, a bookmark per chapter and chart named
by its title, the title above each chart page, and a hard failure on a part
PARTS doesn't list or a chart with no title.
"""
from __future__ import annotations

import io
import json

import pytest
from pypdf import PdfReader, PdfWriter

from laminar import contributor_charts as cc

STAMP = {"code": {"version": "0.1.0a61", "uncommitted_changes": False},
         "schemas": {"version": "0.0.0", "position": 5, "drifted": []},
         "languages": {"stan1293": {"version": "1.2.3", "position": 58, "drifted": []}}}
SOURCE = json.dumps({"annotation_cells_filled": 5, "annotation_cells_total": 10, "stamp": STAMP})
DATASET = "stan1293_types_all"


def _chart(path, pages=1):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=400, height=300)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        writer.write(f)


def _setup(tmp_path, rows):
    """rows: (chart, part, title, pages)."""
    lines = ["chart\tfile\twidth\theight\tunits\ttitle\tpart"]
    for chart, part, title, pages in rows:
        _chart(tmp_path / f"{chart}.pdf", pages)
        lines.append(f"{chart}\t{chart}.pdf\t1\t1\tin\t{title}\t{part}")
    (tmp_path / f"{DATASET}_planarsviz_manifest.tsv").write_text("\n".join(lines) + "\n")


def _combine(tmp_path):
    pdf, n = cc.combine(tmp_path, DATASET, "types", "stan1293", "2026-10-25", SOURCE)
    return PdfReader(io.BytesIO(pdf)), n


def _outline(reader):
    out, top = [], None
    for item in reader.outline:
        if isinstance(item, list):
            out += [(top, i.title, reader.get_destination_page_number(i) + 1) for i in item]
        else:
            top = item.title
            out.append((None, top, reader.get_destination_page_number(item) + 1))
    return out


def test_chapters_dividers_titles_and_page_numbers(tmp_path):
    # Given out of PARTS order: the PDF puts them in PARTS order.
    _setup(tmp_path, [("pooled_plot", "spans", "Every test's span", 1),
                      ("all_families_labeled", "overview", "Combined constituency forest", 2),
                      ("boundary_skyline", "boundaries", "Where spans start and stop", 1)])
    reader, n = _combine(tmp_path)
    assert n == 3
    # cover 1; overview divider 2, chart 3-4; spans divider 5, chart 6;
    # boundaries divider 7, chart 8.
    assert len(reader.pages) == 8
    assert _outline(reader) == [
        (None, "1. The combined forest", 2), ("1. The combined forest", "Combined constituency forest", 3),
        (None, "2. Spans", 5), ("2. Spans", "Every test's span", 6),
        (None, "3. Boundaries", 7), ("3. Boundaries", "Where spans start and stop", 8)]
    cover = reader.pages[0].extract_text()
    assert "1. The combined forest (1 chart)" in cover and "2. Spans (1 chart)" in cover
    divider = reader.pages[1].extract_text()
    assert "1. The combined forest" in divider and "Combined constituency forest" in divider
    assert "3" in divider.split("Combined constituency forest")[1]
    assert "Combined constituency forest" in reader.pages[2].extract_text()
    assert "5 of 10 annotation cells filled" in reader.pages[3].extract_text()
    # What it was drawn from (unit 18): short on each page, in full on the first.
    assert "code 0.1.0a61, data line 58" in reader.pages[3].extract_text()
    assert "English [stan1293] 1.2.3 (line 58)" in cover


def test_a_long_chapter_is_listed_by_group(tmp_path):
    rows = [(f"morsyn_tree_{k:03d}", "families", f"Morphosyntactic: family {k} of 45", 1)
            for k in range(1, 46)]
    _setup(tmp_path, rows)
    reader, _ = _combine(tmp_path)
    divider = reader.pages[1].extract_text()
    assert "Morphosyntactic (45 charts)" in divider
    assert "3–47" in divider


def test_the_weekly_analysis_pdf_says_what_it_is(tmp_path):
    _setup(tmp_path, [("fragmentation_test", "tests", "Fragmentation against chance", 1)])
    pdf, _n = cc.combine(tmp_path, DATASET, "types", "stan1293", "2026-10-25", SOURCE,
                         analysis=("complete", 5000))
    cover = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert "analysis by domain" in cover and "spans over complete positions" in cover
    assert "5000 random draws" in cover and "Statistical tests" in cover


def test_draw_dataset_runs_the_exporter_with_the_tests_then_the_renderer(tmp_path, monkeypatch):
    """No R: the two commands are recorded and the renderer's output faked."""
    run: list[list[str]] = []

    def fake_run(cmd, what):
        run.append(cmd)
        if what.startswith("Drawing"):
            _setup(tmp_path / "charts" / DATASET, [("pooled_plot", "spans", "Every test's span", 1)])

    def write_inputs(lang_id, apply, out_dir, datasets, table):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"source_{datasets[0]}.json").write_text(SOURCE)
        return datasets

    monkeypatch.setattr(cc, "_run", fake_run)
    monkeypatch.setattr(cc, "write_inputs", write_inputs)
    monkeypatch.setattr(cc, "parse_dataset", lambda d: ("stan1293", "types", "all"))
    drawn = cc.draw_dataset("stan1293", DATASET, tmp_path, "2026-10-25", table=None,
                            permutations=5000)
    assert drawn.n_charts == 1 and drawn.pdf.startswith(b"%PDF-")
    export, render = run
    assert export.count("5000") == 4, "all four permutation tests"
    assert "laminar/render_planarsviz.R" in render


@pytest.mark.parametrize("part, title, message", [
    ("nowhere", "A title", "PARTS doesn't list"),
    ("spans", "", "no part or title"),
])
def test_a_chart_the_pdf_cant_place_fails(tmp_path, part, title, message):
    _setup(tmp_path, [("pooled_plot", part, title, 1)])
    with pytest.raises(cc.DrawingFailed, match=message):
        _combine(tmp_path)
