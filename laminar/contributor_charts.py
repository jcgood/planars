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
for English); a contributor gets them as one PDF instead, with a first page
saying what it is, the charts in ``SECTIONS`` order, and a bookmark for
each section and chart. Each page gets a strip added above it with the
dataset, the date it was drawn and how complete the annotation was, so a
page printed or shared alone still says so. The strip is added to the page,
not drawn into the chart, so the charts themselves are the same as
everywhere else (Chichewa's and CCDB's reference images are unaffected).

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

# The renderer's topic folders (render_planarsviz.R), in the order the PDF
# shows them, with the section title a contributor reads. A topic not listed
# here fails rather than being left out or put at the end unnamed.
SECTIONS = {
    "pooled": "Spans: every test's span over the planar structure",
    "boundaries": "Boundaries: where spans start and stop",
    "counts-and-chance": "Counts: how many families and trees",
    "laminar-families": "Laminar families: forests and their trees",
}

STRIP_POINTS = 22          # height of the strip added above each page
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


def _strip(width: float, text: str) -> bytes:
    """A strip `width` points wide holding one line of text."""
    css = (f"p {{ margin: 0; padding: 5pt 8pt; font-size: 10pt; white-space: nowrap; "
           f"overflow: hidden; color: #444; }}")
    return _html_pdf(f"<p>{html.escape(text)}</p>", width, STRIP_POINTS, css)


def _cover(title: str, stamp: str, sections: list[tuple[str, int]]) -> bytes:
    rows = "".join(f"<li>{html.escape(name)} ({n} chart{'s' if n != 1 else ''})</li>"
                   for name, n in sections)
    body = (f"<h1>{html.escape(title)}</h1><p>{html.escape(stamp)}</p>"
            "<p>These charts are drawn from the annotation by the project's tooling "
            "whenever the spans it gives change, to help you check your data: a span "
            "that looks wrong usually means a cell that needs another look. They leave "
            "out the statistical tests, which are run separately for the analysis.</p>"
            "<p>Use the bookmarks to go to a section or chart.</p>"
            f"<h2>Sections</h2><ul>{rows}</ul>")
    return _html_pdf(body, 0, None, "h1 { font-size: 18pt; } p, li { font-size: 11pt; }")


def _manifest(chart_dir: Path, dataset: str) -> list[dict[str, str]]:
    path = chart_dir / f"{dataset}_planarsviz_manifest.tsv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def combine(chart_dir: Path, dataset: str, grouping: str, lang_id: str, date: str,
            source_json: str) -> tuple[bytes, int]:
    """One PDF of every chart the renderer listed in its manifest, with a
    first page, bookmarks and a strip above each page. Returns the PDF and
    the number of charts."""
    from pypdf import PdfReader, PdfWriter, Transformation

    rows = _manifest(chart_dir, dataset)
    by_topic: dict[str, list[dict[str, str]]] = {topic: [] for topic in SECTIONS}
    for row in rows:
        topic = row["file"].split("/")[0]
        if topic not in SECTIONS:
            raise DrawingFailed(f"The renderer drew {row['file']} into a folder "
                                f"laminar/contributor_charts.py's SECTIONS doesn't list "
                                f"({topic!r}); add it there.")
        by_topic[topic].append(row)

    title = f"{get_display_name(lang_id)}: charts {GROUPING_WORDS[grouping]}"
    stamp = f"Drawn {date}; {_completeness(source_json)}"
    strip_text = f"{title}  ·  {stamp}"
    writer = PdfWriter()
    sections = [(SECTIONS[t], len(r)) for t, r in by_topic.items() if r]
    writer.append(PdfReader(io.BytesIO(_cover(title, stamp, sections))))
    strips: dict[int, object] = {}
    for topic, topic_rows in by_topic.items():
        if not topic_rows:
            continue
        parent = writer.add_outline_item(SECTIONS[topic], len(writer.pages))
        for row in topic_rows:
            first = len(writer.pages)
            for page in PdfReader(chart_dir / row["file"]).pages:
                box = page.mediabox
                width, top = float(box.width), float(box.top)
                key = round(width)
                if key not in strips:
                    strips[key] = PdfReader(io.BytesIO(_strip(width, strip_text))).pages[0]
                box.upper_right = (float(box.right), top + STRIP_POINTS)
                page.cropbox = box
                page.merge_transformed_page(strips[key],
                                            Transformation().translate(float(box.left), top))
                writer.add_page(page)
            writer.add_outline_item(row["chart"], first, parent=parent)
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
