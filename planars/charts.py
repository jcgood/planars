"""Domain chart functions for span visualization.

Span collection (collect_all_spans, collect_all_spans_from_sheets, project_spans,
language_spans, _CLASS_HANDLERS) lives in planars.reports, which is the data layer.
This module imports from reports and adds chart rendering on top.

Span label constants (_CISC_SPANS, _NONINT_SPANS, etc.) are re-exported here for
backward compatibility with callers such as coding/check_codebook.py.
"""

import pandas as pd
import plotly.graph_objects as go

from planars.reports import (
    # Span collection — canonical home is reports.py
    _CLASS_HANDLERS,
    collect_all_spans,
    collect_all_spans_from_sheets,
    # Span label constants — re-exported for backward compat
    _CISC_SPANS,
    _SUBSPAN_CATS,
    _SUBSPAN_VARIANTS,
    _NONINT_SPANS,
    _STRESS_SPANS,
    _ASPIRATION_SPANS,
    _SIMPLE_SPANS,
    _NONPERM_SPANS,
)


# --- Colors (one per analysis type) ---
#
# Colorblind-friendly palette drawn from Paul Tol's Bright and Muted schemes
# plus two Okabe-Ito colors to reach 15.
# Reference: https://personal.sron.nl/~pault/
# Colors are auto-assigned in _CLASS_HANDLERS registration order so new
# analyses get a color automatically without manual editing here.

_PALETTE = [
    "#4477AA",  # blue        (Tol Bright)
    "#EE6677",  # red         (Tol Bright)
    "#228833",  # green       (Tol Bright)
    "#CCBB44",  # yellow      (Tol Bright)
    "#66CCEE",  # cyan        (Tol Bright)
    "#AA3377",  # purple      (Tol Bright)
    "#BBBBBB",  # grey        (Tol Bright)
    "#332288",  # indigo      (Tol Muted)
    "#CC6677",  # rose        (Tol Muted)
    "#DDCC77",  # sand        (Tol Muted)
    "#44AA99",  # teal        (Tol Muted)
    "#882255",  # wine        (Tol Muted)
    "#AA4499",  # mauve       (Tol Muted)
    "#E69F00",  # orange      (Okabe-Ito)
    "#0072B2",  # dark blue   (Okabe-Ito)
]

# Auto-assign colors from _PALETTE in registration order.
# Cycles if more analyses are registered than palette entries.
_COLORS = {
    name: _PALETTE[i % len(_PALETTE)]
    for i, name in enumerate(_CLASS_HANDLERS)
}


# --- Chart ---

def domain_chart(df, keystone_pos, pos_to_name, title=None):
    """Horizontal segment chart of spans for one language.

    df must already be filtered to a single language.
    keystone_pos and pos_to_name come from lang_meta[lang_id].
    title, if given, is shown as the chart title (use "Name [glottocode]" format).
    """
    # Sort largest spans to the top so shorter spans are visually distinct below.
    df = df.copy().sort_values(["Size", "Left_Edge"], ascending=[False, True])
    df = df.reset_index(drop=True)

    fig = go.Figure()
    seen = set()

    for i, row in df.iterrows():
        analysis = row["Analysis"]
        color = _COLORS.get(analysis, "#888888")
        # Show a legend entry only the first time each analysis type appears.
        show_legend = analysis not in seen
        seen.add(analysis)

        fig.add_trace(go.Scatter(
            x=[row["Left_Edge"], row["Right_Edge"]],
            y=[i, i],
            mode="lines+markers",
            name=analysis,
            legendgroup=analysis,
            showlegend=show_legend,
            line=dict(color=color, width=5),
            marker=dict(color=color, size=8),
            hovertemplate=(
                f"<b>{row['Test_Labels']}</b><br>"
                f"Left: {row['Left_Edge']} ({pos_to_name.get(row['Left_Edge'], '?')})<br>"
                f"Right: {row['Right_Edge']} ({pos_to_name.get(row['Right_Edge'], '?')})<br>"
                f"Size: {row['Size']}<extra></extra>"
            ),
        ))

    # Dotted vertical line marks the keystone position for quick visual reference.
    fig.add_vline(x=keystone_pos, line_dash="dot", line_color="gray", line_width=1)

    positions = sorted(pos_to_name.keys())
    labels = list(df["Test_Labels"])

    fig.update_layout(
        xaxis=dict(
            title="Position",
            tickmode="array",
            tickvals=positions,
            ticktext=[str(p) for p in positions],
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(len(labels))),
            ticktext=labels,
            autorange="reversed",
        ),
        legend=dict(
            title="Analysis:",
            orientation="h",
            yanchor="bottom",
            y=1.10 if title else 1.02,
            xanchor="right",
            x=1,
        ),
        # Scale height so every span label has ~22px of vertical space.
        height=max(400, len(labels) * 22),
        margin=dict(l=180, r=20, t=110 if title else 60, b=60),
        template="simple_white",
        **({"title": dict(text=title, x=0.5, xanchor="center")} if title else {}),
    )

    return fig


def charts_by_language(df, lang_meta, lang_names=None):
    """Produce one domain_chart per language.

    Returns dict[lang_id, Figure]. Each chart uses that language's own
    position numbering and pos_to_name — languages are never mixed.
    lang_names, if given, is a dict mapping lang_id to a display string
    used as the chart title (e.g. {"arao1248": "Araona [arao1248]"}).
    """
    return {
        lang_id: domain_chart(
            df[df["Language"] == lang_id],
            meta["keystone_pos"],
            meta["pos_to_name"],
            title=(lang_names or {}).get(lang_id),
        )
        for lang_id, meta in lang_meta.items()
    }
