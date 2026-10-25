"""A language's contributor charts: two PDFs, by class and by domain type.

docs/laminar-analysis-plan.md decision 6 and Phase 4b. Charts for
contributors checking their own data, drawn after the daily refresh and put
on Drive by ``python -m coding laminar-charts`` (coding/laminar_charts.py,
which decides when to draw and does the uploading; this module only draws).

**What is drawn.** For a planars language, the two datasets with every span
(``CONTRIBUTOR_DATASETS``: ``<lang>_classes_all`` and ``<lang>_types_all``),
exported **without** the four permutation tests (they are for the analysis,
run weekly, and take nearly all the time) and rendered with every chart the
renderer draws from such a bundle. Built from the annotation in a folder the
caller gives (a temporary one): derived and redrawn, so nothing is stored.

**One PDF per dataset.** The renderer writes one file per chart (about 300
for English); a contributor gets them as one PDF instead: a first page
saying what it is and listing the chapters, then the chapters in ``PARTS``
order, each opened by a divider page saying what its charts show and
listing them with their page numbers, and a bookmark for each chapter and
chart. Which chapter a chart is in and its title are the renderer's, set
where it adds the chart (``render_planarsviz.R``'s chart_table(), the
manifest's ``part`` and ``title`` columns); a part ``PARTS`` doesn't list
fails. Each page gets a strip added above it with the chart's title, and
the dataset, the date it was drawn and how complete the annotation was, so
a page printed or shared alone still says what it is. The strip is added to
the page, not drawn into the chart, so the charts themselves are the same
as everywhere else (Chichewa's and CCDB's reference images are unaffected).

**When to redraw** is ``fingerprint()``: the two domains files (the spans,
which is all a chart is drawn from apart from the planar file) plus the
planar file and the chart code (git's record of ``laminar/`` and
``planarsviz/``). Completeness and the planars-data commit are left out, so
annotation that changes no span redraws nothing.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from laminar.charts import export_command, render_command
from laminar.datasets import REPO, dataset_settings
from laminar.planars_language import (
    dataset_name, input_texts, planar_file, span_table, write_inputs,
)
from planars.languages import get_display_name

# grouping -> selection: the two datasets a contributor gets.
CONTRIBUTOR_DATASETS = {"classes": "all", "types": "all"}
GROUPING_WORDS = {"classes": "by class", "types": "by domain type"}

# The renderer's parts (render_planarsviz.R's chart_table()), in the order
# the PDF shows them: (chapter title, what its charts show). A part not
# listed here fails rather than being left out or put at the end unnamed.
# The combined forest comes first: it is the one chart that shows every
# test at once. Every family on its own comes last: there can be hundreds.
PARTS = {
    "overview": ("The combined forest",
                 "Every family of every test drawn as one stacked forest (darker where more "
                 "families share a branch, thicker where more tests give the span), the same "
                 "coloured by domain type, and the single trees that sum it up."),
    "spans": ("Spans",
              "Each test's span over the planar structure: all tests together, grouped, "
              "and one group at a time."),
    "boundaries": ("Boundaries",
                   "Where spans start and stop, and how strongly each position is an edge."),
    "forests": ("Forests by group",
                "The families of one group of tests at a time (a domain type, a class or a "
                "bundle of them), each forest stacked like the combined one."),
    "exemplary": ("Exemplary trees",
                  "A handful of families chosen to differ from each other, each with the "
                  "tests behind its spans."),
    "counts": ("Counts",
               "How many families the tests allow, by group and in all."),
    "tests": ("Statistical tests",
              "Whether the patterns could come about by chance."),
    "families": ("Every family on its own",
                 "Each family of each forest drawn by itself, in the order of the forests above."),
}

STRIP_POINTS = 34          # height of the strip added above a page up to...
STRIP_BASE_WIDTH = 600     # ...this wide (points); wider pages scale it up
DIVIDER_LIST_MAX = 40      # a divider lists at most this many lines
_CODE_FOLDERS = ("laminar", "planarsviz")


class DrawingFailed(RuntimeError):
    """The exporter or the renderer failed; the message has the end of its
    output."""


@dataclass
class Drawn:
    """One dataset drawn: its PDF and how many charts are in it."""
    grouping: str
    dataset: str
    pdf: bytes
    n_charts: int


def contributor_datasets(lang_id: str) -> dict[str, str]:
    """grouping -> dataset name."""
    return {g: dataset_name(lang_id, g, s) for g, s in CONTRIBUTOR_DATASETS.items()}


def code_version() -> str:
    """git's record of the chart code as committed (``laminar/``,
    ``planarsviz/``): changes when either does."""
    done = subprocess.run(["git", "-C", str(REPO), "rev-parse",
                           *(f"HEAD:{f}" for f in _CODE_FOLDERS)],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise DrawingFailed("Could not read the chart code's version from git: "
                            + (done.stderr.strip() or done.stdout.strip()))
    return " ".join(done.stdout.split())


def fingerprint(lang_id: str, table) -> str:
    """What the contributor charts are drawn from, as one hash: the two
    domains files, the planar file and the chart code. `table` is the span
    table (planars_language.span_table)."""
    digest = hashlib.sha256()
    for grouping, selection in CONTRIBUTOR_DATASETS.items():
        domains_text, _record = input_texts(lang_id, table, grouping, selection)
        digest.update(domains_text.encode("utf-8"))
    digest.update(planar_file(lang_id).read_bytes())
    digest.update(code_version().encode("utf-8"))
    return digest.hexdigest()


def _run(cmd: list[str], what: str) -> None:
    done = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if done.returncode != 0:
        tail = "\n".join((done.stdout + done.stderr).rstrip().splitlines()[-15:])
        raise DrawingFailed(f"{what} failed (exit code {done.returncode}):\n{tail}")


def draw(lang_id: str, work: Path, date: str, table=None) -> list[Drawn]:
    """Draw both contributor datasets in `work` and return their PDFs.
    `date` (YYYY-MM-DD) goes on every page."""
    table = span_table(lang_id) if table is None else table
    datasets = contributor_datasets(lang_id)
    domains = work / "domains"
    write_inputs(lang_id, apply=True, out_dir=domains, datasets=list(datasets.values()),
                 table=table)
    drawn = []
    for grouping, dataset in datasets.items():
        bundles, charts = work / "chart_data", work / "charts"
        _run(export_command(dataset, dataset_settings(dataset), 0,
                            domains=domains / f"domains_{dataset}.tsv", output_dir=bundles),
             f"Exporting {dataset}")
        _run(render_command(dataset, None, None, bundle_dir=bundles, output_dir=charts),
             f"Drawing {dataset}")
        source = (domains / f"source_{dataset}.json").read_text(encoding="utf-8")
        pdf, n = combine(charts / dataset, dataset, grouping, lang_id, date, source)
        drawn.append(Drawn(grouping, dataset, pdf, n))
    return drawn


# ── One PDF ─────────────────────────────────────────────────────────────────

def _completeness(source_json: str) -> str:
    import json
    record = json.loads(source_json)
    filled, total = record["annotation_cells_filled"], record["annotation_cells_total"]
    pct = f" ({100 * filled / total:.0f}%)" if total else ""
    return f"{filled} of {total} annotation cells filled{pct}"


def _html_pdf(body: str, width: float, height: float | None, css: str = "") -> bytes:
    from weasyprint import HTML
    size = f"{width:.2f}pt {height:.2f}pt" if height else "A4"
    page_css = (f"@page {{ size: {size}; margin: {'0' if height else '2cm'}; }} "
                "body { font-family: sans-serif; } " + css)
    return HTML(string=f"<html><head><style>{page_css}</style></head>"
                       f"<body>{body}</body></html>").write_pdf()


def _strip_scale(width: float) -> float:
    """Charts run from 7 to over 40 inches wide; the strip grows with the
    page so its title reads at the chart's own scale."""
    return max(1.0, width / STRIP_BASE_WIDTH)


def _strip(width: float, chart_title: str, stamp: str) -> bytes:
    """A strip `width` points wide: the chart's title, and under it the stamp."""
    s = _strip_scale(width)
    css = (f"p {{ margin: 0; padding: 0 {8 * s:.1f}pt; white-space: nowrap; overflow: hidden; }} "
           f"p.t {{ padding-top: {4 * s:.1f}pt; font-size: {11 * s:.1f}pt; font-weight: bold; color: #222; }} "
           f"p.s {{ font-size: {8 * s:.1f}pt; color: #666; }}")
    return _html_pdf(f'<p class="t">{html.escape(chart_title)}</p>'
                     f'<p class="s">{html.escape(stamp)}</p>', width, STRIP_POINTS * s, css)


_PAGE_CSS = ("h1 { font-size: 20pt; } h2 { font-size: 14pt; } p { font-size: 11pt; } "
             "table { border-collapse: collapse; font-size: 9.5pt; width: 100%; } "
             "td { padding: 1pt 4pt; vertical-align: top; } td.n { text-align: right; width: 4em; }")


def _contents(rows: list[tuple[str, int]]) -> str:
    return ("<table>" + "".join(f'<tr><td>{html.escape(text)}</td><td class="n">{page}</td></tr>'
                                for text, page in rows) + "</table>")


def _cover(title: str, stamp: str, parts: list[tuple[str, int, int]]) -> bytes:
    """parts: (chapter title, number of charts, first page)."""
    body = (f"<h1>{html.escape(title)}</h1><p>{html.escape(stamp)}</p>"
            "<p>These charts are drawn from the annotation by the project's tooling "
            "whenever the spans it gives change, to help you check your data: a span "
            "that looks wrong usually means a cell that needs another look. They leave "
            "out the statistical tests, which are run separately for the analysis.</p>"
            "<p>Each chapter starts with a page listing its charts; the bookmarks go to any "
            "chapter or chart.</p><h2>Chapters</h2>"
            + _contents([(f"{i}. {name} ({n} chart{'s' if n != 1 else ''})", page)
                         for i, (name, n, page) in enumerate(parts, start=1)]))
    return _html_pdf(body, 0, None, _PAGE_CSS)


def _divider(number: int, part: str, charts: list[tuple[str, int, int]]) -> bytes:
    """A chapter's first page. charts: (title, first page, last page). Long
    lists (every family on its own) are shown one line per group of titles
    sharing what comes before their colon."""
    name, what = PARTS[part]
    lines = [(t, str(a)) for t, a, _b in charts]
    if len(lines) > DIVIDER_LIST_MAX:
        groups: dict[str, list[tuple[int, int]]] = {}
        for t, a, b in charts:
            groups.setdefault(t.split(":")[0], []).append((a, b))
        lines = [(f"{g} ({len(p)} chart{'s' if len(p) != 1 else ''})",
                  f"{p[0][0]}–{p[-1][1]}" if len(p) > 1 else str(p[0][0]))
                 for g, p in groups.items()]
    body = (f"<h1>{number}. {html.escape(name)}</h1><p>{html.escape(what)}</p>"
            + _contents(lines))
    return _html_pdf(body, 0, None, _PAGE_CSS)


def _manifest(chart_dir: Path, dataset: str) -> list[dict[str, str]]:
    path = chart_dir / f"{dataset}_planarsviz_manifest.tsv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def combine(chart_dir: Path, dataset: str, grouping: str, lang_id: str, date: str,
            source_json: str) -> tuple[bytes, int]:
    """One PDF of every chart the renderer listed in its manifest: a first
    page, a divider opening each chapter, bookmarks, and a strip above each
    chart page. Returns the PDF and the number of charts."""
    from pypdf import PdfReader, PdfWriter, Transformation

    rows = _manifest(chart_dir, dataset)
    by_part: dict[str, list[dict[str, str]]] = {part: [] for part in PARTS}
    for row in rows:
        if not row.get("part") or not row.get("title"):
            raise DrawingFailed(f"The renderer's manifest gives {row['chart']} no part or title; "
                                "set both where render_planarsviz.R's chart_table() adds it.")
        if row["part"] not in PARTS:
            raise DrawingFailed(f"The renderer put {row['chart']} in part {row['part']!r}, which "
                                "laminar/contributor_charts.py's PARTS doesn't list; add it there.")
        by_part[row["part"]].append(row)
    parts = [p for p, r in by_part.items() if r]
    readers = {row["file"]: PdfReader(chart_dir / row["file"]) for row in rows}

    title = f"{get_display_name(lang_id)}: charts {GROUPING_WORDS[grouping]}"
    stamp = f"Drawn {date}; {_completeness(source_json)}"

    # Page numbers depend on how long the first page and the dividers come
    # out, which depends on the numbers: lay out, measure, again until stable.
    lengths = {"cover": 1, **{p: 1 for p in parts}}
    for _ in range(5):
        page = 1 + lengths["cover"]
        part_start, ranges = {}, {}
        for p in parts:
            part_start[p] = page
            page += lengths[p]
            for row in by_part[p]:
                n = len(readers[row["file"]].pages)
                ranges[row["file"]] = (page, page + n - 1)
                page += n
        cover = _cover(title, stamp, [(PARTS[p][0], len(by_part[p]), part_start[p]) for p in parts])
        dividers = {p: _divider(i, p, [(r["title"], *ranges[r["file"]]) for r in by_part[p]])
                    for i, p in enumerate(parts, start=1)}
        measured = {"cover": len(PdfReader(io.BytesIO(cover)).pages),
                    **{p: len(PdfReader(io.BytesIO(d)).pages) for p, d in dividers.items()}}
        if measured == lengths:
            break
        lengths = measured
    else:
        raise DrawingFailed("The contents pages' length would not settle.")

    writer = PdfWriter()
    # Without their own bookmarks: WeasyPrint makes one per heading.
    writer.append(PdfReader(io.BytesIO(cover)), import_outline=False)
    strips: dict[tuple[int, str], object] = {}
    for i, p in enumerate(parts, start=1):
        divider_page = len(writer.pages)
        writer.append(PdfReader(io.BytesIO(dividers[p])), import_outline=False)
        parent = writer.add_outline_item(f"{i}. {PARTS[p][0]}", divider_page)
        for row in by_part[p]:
            first = len(writer.pages)
            for chart_page in readers[row["file"]].pages:
                box = chart_page.mediabox
                width, top = float(box.width), float(box.top)
                key = (round(width), row["title"])
                if key not in strips:
                    strips[key] = PdfReader(io.BytesIO(_strip(width, row["title"], f"{title}  ·  {stamp}"))).pages[0]
                box.upper_right = (float(box.right), top + STRIP_POINTS * _strip_scale(width))
                chart_page.cropbox = box
                added = writer.add_page(chart_page)
                added.merge_transformed_page(strips[key],
                                             Transformation().translate(float(box.left), top))
            writer.add_outline_item(row["title"], first, parent=parent)
    writer.page_mode = "/UseOutlines"
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue(), len(rows)


def main(argv: list[str] | None = None) -> None:
    """Draw a language's contributor charts locally, to look at them:
    ``python -m laminar.contributor_charts stan1293 OUT_DIR``. Writes the two
    PDFs into OUT_DIR; puts nothing on Drive (that is
    ``python -m coding laminar-charts``)."""
    import argparse
    from datetime import date
    parser = argparse.ArgumentParser(prog="python -m laminar.contributor_charts",
                                     description=main.__doc__)
    parser.add_argument("lang_id")
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        for d in draw(args.lang_id, Path(work), date.today().isoformat()):
            path = args.out_dir / f"{d.dataset}.pdf"
            path.write_bytes(d.pdf)
            print(f"{path} ({d.n_charts} charts)")


if __name__ == "__main__":
    main()
