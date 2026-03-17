"""Domain chart functions for span visualization."""

import pandas as pd
import plotly.graph_objects as go

from planars import ciscategorial as _cisc
from planars import subspanrepetition as _subspan
from planars import noninterruption as _nonint


# --- Colors (one per analysis type) ---

_COLORS = {
    "ciscategorial":    "#BC3C29",
    "subspanrepetition": "#0072B5",
    "noninterruption":  "#20845E",
}

# --- Span label mappings ---

_CISC_SPANS = [
    ("strict_complete_span", "cisc strict complete"),
    ("loose_complete_span",  "cisc loose complete"),
    ("strict_partial_span",  "cisc strict partial"),
    ("loose_partial_span",   "cisc loose partial"),
]

_SUBSPAN_CATS = {
    "maximum_fillable":          "fill",
    "maximum_widescope_left":    "ws-L",
    "maximum_widescope_right":   "ws-R",
    "maximum_narrowscope_left":  "ns-L",
    "maximum_narrowscope_right": "ns-R",
}
_SUBSPAN_VARIANTS = [
    ("strict_complete", "strict complete"),
    ("loose_complete",  "loose complete"),
    ("strict_partial",  "strict partial"),
    ("loose_partial",   "loose partial"),
]

_NONINT_SPANS = [
    ("no_free_complete_span",    "no-free complete"),
    ("no_free_partial_span",     "no-free partial"),
    ("single_free_complete_span","1-free complete"),
    ("single_free_partial_span", "1-free partial"),
]

# --- Span extraction ---

def _rows_from_cisc(result):
    rows = []
    for key, label in _CISC_SPANS:
        l, r = result[key]
        rows.append({"Test_Labels": label, "Analysis": "ciscategorial",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_subspan(result):
    rows = []
    for cat, short in _SUBSPAN_CATS.items():
        for variant, vlabel in _SUBSPAN_VARIANTS:
            l, r = result[f"{variant}_{cat}_span"]
            rows.append({"Test_Labels": f"{short} {vlabel}", "Analysis": "subspanrepetition",
                         "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_nonint(result):
    rows = []
    for key, label in _NONINT_SPANS:
        l, r = result[key]
        rows.append({"Test_Labels": label, "Analysis": "noninterruption",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


# --- Analysis class registry ---

_CLASS_HANDLERS = {
    "ciscategorial":     (_cisc.derive_v_ciscategorial_fractures,  _rows_from_cisc),
    "subspanrepetition": (_subspan.derive_subspanrepetition_spans, _rows_from_subspan),
    "noninterruption":   (_nonint.derive_noninterruption_domains,  _rows_from_nonint),
}


# --- Main collection ---

def collect_all_spans(repo_root):
    """Run all analyses over coded_data/ and return (DataFrame, keystone_pos, pos_to_name)."""
    rows = []
    keystone_pos = None
    pos_to_name = None

    coded_data = repo_root / "coded_data"
    for lang_dir in sorted(coded_data.iterdir()):
        if not lang_dir.is_dir():
            continue
        for class_name, (derive_fn, row_fn) in _CLASS_HANDLERS.items():
            class_dir = lang_dir / class_name
            if not class_dir.exists():
                continue
            for tsv in sorted(class_dir.glob("*_filled.tsv")):
                result = derive_fn(tsv, strict=False)
                rows.extend(row_fn(result))
                if keystone_pos is None:
                    keystone_pos = result["keystone_position"]
                    pos_to_name = result["position_number_to_name"]

    return pd.DataFrame(rows), keystone_pos, pos_to_name


# --- Chart ---

def domain_chart(df, keystone_pos, pos_to_name):
    """Horizontal segment chart of all spans, ordered by size then left edge."""
    df = df.copy().sort_values(["Size", "Left_Edge"], ascending=[False, True])
    df = df.reset_index(drop=True)

    fig = go.Figure()
    seen = set()

    for i, row in df.iterrows():
        analysis = row["Analysis"]
        color = _COLORS.get(analysis, "#888888")
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

    # Dotted vertical line at keystone
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
            y=1.02,
            xanchor="right",
            x=1,
        ),
        height=max(400, len(labels) * 22),
        margin=dict(l=180, r=20, t=60, b=60),
        template="simple_white",
    )

    return fig
