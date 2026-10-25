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

SOURCE = json.dumps({"annotation_cells_filled": 5, "annotation_cells_total": 10})
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


def test_a_long_chapter_is_listed_by_group(tmp_path):
    rows = [(f"morsyn_tree_{k:03d}", "families", f"Morphosyntactic: family {k} of 45", 1)
            for k in range(1, 46)]
    _setup(tmp_path, rows)
    reader, _ = _combine(tmp_path)
    divider = reader.pages[1].extract_text()
    assert "Morphosyntactic (45 charts)" in divider
    assert "3–47" in divider


@pytest.mark.parametrize("part, title, message", [
    ("nowhere", "A title", "PARTS doesn't list"),
    ("spans", "", "no part or title"),
])
def test_a_chart_the_pdf_cant_place_fails(tmp_path, part, title, message):
    _setup(tmp_path, [("pooled_plot", part, title, 1)])
    with pytest.raises(cc.DrawingFailed, match=message):
        _combine(tmp_path)
