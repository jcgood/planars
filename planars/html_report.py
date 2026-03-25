"""HTML and PDF report rendering for planars.

Produces self-contained reports from language_report_data bundles for
non-technical collaborators. Reports show annotation completeness, review
status, and the domain chart.

- ``render_language_report(data)`` — HTML string with interactive Plotly chart
  (CDN). Open in any browser or display inline in Colab.
- ``render_language_report_pdf(data)`` — PDF bytes with a static PNG chart
  (requires ``weasyprint`` and ``kaleido``). Upload to Google Drive for a
  shareable URL that renders natively in the Drive viewer.

Typical usage
-------------
    from planars.reports import language_report_data
    from planars.html_report import render_language_report, render_language_report_pdf
    from pathlib import Path

    data = language_report_data("arao1248", source="local", repo_root=Path("."))

    # HTML — browser / Colab
    Path("arao1248_report.html").write_text(render_language_report(data), encoding="utf-8")

    # PDF — Drive sharing
    Path("arao1248_report.pdf").write_bytes(render_language_report_pdf(data))
"""

from __future__ import annotations

import base64
import html as _html
from typing import Optional

_CSS = """
@page { size: A4; margin: 2cm 2.5cm; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 Helvetica, Arial, sans-serif;
    font-size: 15px;
    line-height: 1.55;
    color: #1a1a1a;
    background: #f7f7f8;
    padding: 0 0 3rem;
}
header {
    background: #fff;
    border-bottom: 1px solid #e0e0e0;
    padding: 1.5rem 2rem 1.2rem;
    margin-bottom: 2rem;
}
header h1 { font-size: 1.6rem; font-weight: 600; }
header .timestamp {
    margin-top: 0.3rem;
    font-size: 0.85rem;
    color: #666;
}
main { max-width: 960px; margin: 0 auto; padding: 0 1.5rem; }
section { margin-bottom: 2.5rem; }
.completeness-section { break-inside: avoid; }
h2 {
    font-size: 1.1rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #444;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}
table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
}
thead th {
    background: #f0f0f1;
    text-align: left;
    padding: 0.55rem 0.9rem;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #555;
    border-bottom: 1px solid #e0e0e0;
}
tbody td { padding: 0.5rem 0.9rem; border-bottom: 1px solid #f0f0f0; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #fafafa; }
.ok      { color: #1a7f3c; font-weight: 600; }
.blank   { color: #b45300; font-weight: 600; }
.error   { color: #c0392b; font-weight: 600; }
.missing { color: #888; font-style: italic; }
.badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 3px;
    font-size: 0.78rem;
    font-weight: 500;
    white-space: nowrap;
}
.badge-ready   { background: #d4edda; color: #155724; }
.badge-progress { background: #fff3cd; color: #856404; }
.badge-none    { background: #f0f0f0; color: #888; }
.chart-wrap {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 1rem;
    overflow-x: auto;
}
.no-data { color: #888; font-style: italic; padding: 1rem 0; }
"""


def _badge(status: str) -> str:
    if status == "ready-for-review":
        return '<span class="badge badge-ready">ready for review</span>'
    if status == "in-progress":
        return '<span class="badge badge-progress">in progress</span>'
    if status:
        return f'<span class="badge badge-none">{_html.escape(status)}</span>'
    return '<span class="badge badge-none">—</span>'


def _completeness_table(completeness: dict, status: Optional[dict]) -> str:
    rows = []
    for class_name in sorted(completeness):
        constructions = completeness[class_name]
        if isinstance(constructions, dict) and "_error" in constructions:
            rows.append(
                f"<tr><td>{_html.escape(class_name)}</td><td>—</td>"
                f"<td colspan='3' class='error'>Error: {_html.escape(str(constructions['_error']))}</td></tr>"
            )
            continue
        for construction in sorted(constructions):
            stats = constructions[construction]
            label_class = _html.escape(class_name)
            label_con   = _html.escape(construction)
            con_status  = (status or {}).get(class_name, {}).get(construction, "")

            if stats.get("missing"):
                rows.append(
                    f"<tr><td>{label_class}</td><td>{label_con}</td>"
                    f'<td><span class="missing">not started</span></td>'
                    f"<td>{_badge(con_status)}</td></tr>"
                )
            elif "error" in stats:
                rows.append(
                    f"<tr><td>{label_class}</td><td>{label_con}</td>"
                    f"<td colspan='2' class='error'>Error: {_html.escape(str(stats['error']))}</td>"
                    f"<td>{_badge(con_status)}</td></tr>"
                )
            else:
                total  = stats["total"]
                filled = stats["filled"]
                blank  = stats["blank"]
                pct    = f"{100 * filled // total}%" if total else "—"
                if blank == 0 and total > 0:
                    fill_cell = f'<span class="ok">{filled}/{total} ({pct})</span>'
                elif total == 0:
                    fill_cell = '<span class="no-data">no data</span>'
                else:
                    fill_cell = (
                        f'<span class="blank">{filled}/{total} ({pct})</span>'
                        f' <small style="color:#b45300">— {blank} blank</small>'
                    )
                rows.append(
                    f"<tr><td>{label_class}</td><td>{label_con}</td>"
                    f"<td>{fill_cell}</td>"
                    f"<td>{_badge(con_status)}</td></tr>"
                )

    header = (
        "<thead><tr>"
        "<th>Class</th><th>Construction</th>"
        "<th>Filled</th><th>Status</th>"
        "</tr></thead>"
    )
    return f"<table>{header}<tbody>{''.join(rows)}</tbody></table>"


def _chart_html(data: dict, static: bool = False) -> str:
    spans     = data.get("spans")
    lang_meta = data.get("lang_meta")

    if spans is None or spans.empty or lang_meta is None:
        return '<p class="no-data">No span data available yet.</p>'

    try:
        from planars.charts import domain_chart

        if static:
            all_labels = (list(spans["Test_Labels"].unique())
                          if "Test_Labels" in spans.columns else [])
            rows_per_chunk = 14
            chunks = ([all_labels[i:i + rows_per_chunk]
                       for i in range(0, len(all_labels), rows_per_chunk)]
                      if all_labels else [None])
            parts = []
            for i, chunk_labels in enumerate(chunks):
                if chunk_labels is not None:
                    chunk_spans = spans[spans["Test_Labels"].isin(chunk_labels)]
                    n_rows = len(chunk_labels)
                else:
                    chunk_spans = spans
                    n_rows = max(1, len(spans))
                chunk_fig = domain_chart(
                    chunk_spans,
                    lang_meta["keystone_pos"],
                    lang_meta["pos_to_name"],
                    title=data.get("display_name") if i == 0 else None,
                )
                height = max(400, 200 + n_rows * 45)
                png_bytes = chunk_fig.to_image(format="png", width=640, height=height, scale=2)
                b64 = base64.b64encode(png_bytes).decode()
                parts.append(
                    f'<img src="data:image/png;base64,{b64}"'
                    f' style="max-width:100%;height:auto;display:block;">'
                )
            return '<div class="chart-wrap">' + "".join(parts) + "</div>"

        fig = domain_chart(
            spans,
            lang_meta["keystone_pos"],
            lang_meta["pos_to_name"],
            title=data.get("display_name"),
        )
        chart_div = fig.to_html(full_html=False, include_plotlyjs="cdn")
        return f'<div class="chart-wrap">{chart_div}</div>'
    except Exception as e:
        return f'<p class="error">Chart error: {_html.escape(str(e))}</p>'


def render_language_report(data: dict, static: bool = False) -> str:
    """Render a language_report_data bundle as a self-contained HTML string.

    data:   the dict returned by planars.reports.language_report_data().
    static: if True, embed the chart as a static PNG (base64 data URI) instead
            of the interactive Plotly CDN chart. Used internally by
            render_language_report_pdf(); not normally needed for direct HTML use.

    The returned HTML string can be written directly to a .html file or
    displayed inline in Colab. It embeds the Plotly chart via CDN by default
    (requires an internet connection to display the chart).
    """
    display_name = _html.escape(data.get("display_name") or data.get("lang_id", ""))
    generated_at = data.get("generated_at")
    timestamp_str = (
        generated_at.strftime("%B %-d, %Y at %H:%M UTC")
        if generated_at else "unknown"
    )

    completeness_html = ""
    if data.get("completeness"):
        completeness_html = (
            '<section class="completeness-section">'
            "<h2>Annotation Completeness</h2>"
            + _completeness_table(data["completeness"], data.get("status"))
            + "</section>"
        )
    else:
        completeness_html = (
            '<section class="completeness-section">'
            "<h2>Annotation Completeness</h2>"
            '<p class="no-data">No annotation data found.</p>'
            "</section>"
        )

    chart_section = (
        "<section>"
        "<h2>Domain Chart</h2>"
        + _chart_html(data, static=static)
        + "</section>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{display_name} — Planars Report</title>
  <style>{_CSS}</style>
</head>
<body>
  <header>
    <h1>{display_name}</h1>
    <p class="timestamp">Generated {_html.escape(timestamp_str)}</p>
  </header>
  <main>
    {completeness_html}
    {chart_section}
  </main>
</body>
</html>"""


def render_language_report_pdf(data: dict) -> bytes:
    """Render a language_report_data bundle as a PDF byte string.

    Requires ``weasyprint`` (HTML→PDF) and ``kaleido`` (Plotly static export).
    The chart is embedded as a static PNG rather than interactive JavaScript.

    The returned bytes can be written directly to a .pdf file or uploaded to
    Google Drive, where PDFs render natively in the Drive viewer.
    """
    html = render_language_report(data, static=True)
    from weasyprint import HTML  # noqa: PLC0415
    return HTML(string=html).write_pdf()
