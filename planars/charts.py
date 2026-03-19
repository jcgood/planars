"""Domain chart functions for span visualization."""

import pandas as pd
import plotly.graph_objects as go

from planars import ciscategorial as _cisc
from planars import subspanrepetition as _subspan
from planars import noninterruption as _nonint
from planars import stress as _stress
from planars import aspiration as _aspiration


# --- Colors (one per analysis type) ---

_COLORS = {
    "ciscategorial":    "#BC3C29",
    "subspanrepetition": "#0072B5",
    "noninterruption":  "#20845E",
    "stress":           "#E18727",
    "aspiration":       "#7876B1",
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

_STRESS_SPANS = [
    ("minimal_partial_span",  "stress minimal partial"),
    ("minimal_complete_span", "stress minimal complete"),
    ("maximal_partial_span",  "stress maximal partial"),
    ("maximal_complete_span", "stress maximal complete"),
]

_ASPIRATION_SPANS = [
    ("minimal_partial_span",  "asp minimal partial"),
    ("minimal_complete_span", "asp minimal complete"),
    ("maximal_partial_span",  "asp maximal partial"),
    ("maximal_complete_span", "asp maximal complete"),
]

# --- Span extraction ---

def _rows_from_cisc(result, lang_id):
    """Convert a ciscategorial result dict into chart row dicts."""
    rows = []
    for key, label in _CISC_SPANS:
        l, r = result[key]
        rows.append({"Language": lang_id, "Test_Labels": label,
                     "Analysis": "ciscategorial",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_subspan(result, lang_id):
    """Convert a subspanrepetition result dict into chart row dicts."""
    rows = []
    for cat, short in _SUBSPAN_CATS.items():
        for variant, vlabel in _SUBSPAN_VARIANTS:
            l, r = result[f"{variant}_{cat}_span"]
            rows.append({"Language": lang_id, "Test_Labels": f"{short} {vlabel}",
                         "Analysis": "subspanrepetition",
                         "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_nonint(result, lang_id):
    """Convert a noninterruption result dict into chart row dicts."""
    rows = []
    for key, label in _NONINT_SPANS:
        l, r = result[key]
        rows.append({"Language": lang_id, "Test_Labels": label,
                     "Analysis": "noninterruption",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_stress(result, lang_id):
    """Convert a stress result dict into chart row dicts."""
    rows = []
    for key, label in _STRESS_SPANS:
        l, r = result[key]
        rows.append({"Language": lang_id, "Test_Labels": label,
                     "Analysis": "stress",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


def _rows_from_aspiration(result, lang_id):
    """Convert an aspiration result dict into chart row dicts."""
    rows = []
    for key, label in _ASPIRATION_SPANS:
        l, r = result[key]
        rows.append({"Language": lang_id, "Test_Labels": label,
                     "Analysis": "aspiration",
                     "Left_Edge": l, "Right_Edge": r, "Size": r - l + 1})
    return rows


# --- Analysis class registry ---

_CLASS_HANDLERS = {
    "ciscategorial":     (_cisc.derive_v_ciscategorial_fractures,  _rows_from_cisc),
    "subspanrepetition": (_subspan.derive_subspanrepetition_spans, _rows_from_subspan),
    "noninterruption":   (_nonint.derive_noninterruption_domains,  _rows_from_nonint),
    "stress":            (_stress.derive_stress_domains,           _rows_from_stress),
    "aspiration":        (_aspiration.derive_aspiration_domains,   _rows_from_aspiration),
}


# --- Main collection ---

def collect_all_spans(repo_root):
    """Run all analyses over coded_data/ and return (DataFrame, lang_meta).

    DataFrame columns: Language, Test_Labels, Analysis, Left_Edge, Right_Edge, Size.

    lang_meta is a dict keyed by language ID:
        {lang_id: {"keystone_pos": int, "pos_to_name": {int: str}}}

    Each language has its own planar structure and position numbering.
    """
    rows = []
    lang_meta = {}

    coded_data = repo_root / "coded_data"
    for lang_dir in sorted(coded_data.iterdir()):
        if not lang_dir.is_dir():
            continue
        lang_id = lang_dir.name
        for class_name, (derive_fn, row_fn) in _CLASS_HANDLERS.items():
            class_dir = lang_dir / class_name
            if not class_dir.exists():
                continue
            for tsv in sorted(class_dir.glob("*_filled.tsv")):
                # strict=False so partially-filled sheets still yield spans.
                result = derive_fn(tsv, strict=False)
                rows.extend(row_fn(result, lang_id))
                # Record keystone and position map once per language; all TSVs
                # for the same language share the same planar structure.
                if lang_id not in lang_meta:
                    lang_meta[lang_id] = {
                        "keystone_pos": result["keystone_position"],
                        "pos_to_name":  result["position_number_to_name"],
                    }

    return pd.DataFrame(rows), lang_meta


def collect_all_spans_from_sheets(gc, manifest):
    """Run all analyses directly from Google Sheets (no local TSVs).

    gc:       authenticated gspread.Client
    manifest: dict in the same format as sheets_manifest.json

    Returns (DataFrame, lang_meta) — same structure as collect_all_spans.
    Each language in the manifest has its own entry in lang_meta with its
    own keystone_pos and pos_to_name. Intended for Colab workflows.
    """
    from planars.io import load_filled_sheet

    rows = []
    lang_meta = {}

    for lang_id, lang_data in manifest.items():
        for class_name, (derive_fn, row_fn) in _CLASS_HANDLERS.items():
            sheet_info = lang_data.get("sheets", {}).get(class_name)
            if not sheet_info:
                continue
            try:
                ss = gc.open_by_key(sheet_info["spreadsheet_id"])
            except Exception as e:
                print(f"  WARNING: could not open {class_name} sheet for {lang_id}: {e}")
                continue
            construction_params = sheet_info.get("construction_params", {})
            for construction in sheet_info["constructions"]:
                try:
                    ws = ss.worksheet(construction)
                except Exception:
                    print(f"  WARNING: tab '{construction}' not found in {class_name} sheet")
                    continue
                required = set(
                    construction_params.get(construction, {}).get("param_names", [])
                )
                loaded = load_filled_sheet(ws, required_params=required, strict=False)
                result = derive_fn(_data=loaded, strict=False)
                rows.extend(row_fn(result, lang_id))
                if lang_id not in lang_meta:
                    lang_meta[lang_id] = {
                        "keystone_pos": result["keystone_position"],
                        "pos_to_name":  result["position_number_to_name"],
                    }

    return pd.DataFrame(rows), lang_meta


# --- Chart ---

def domain_chart(df, keystone_pos, pos_to_name):
    """Horizontal segment chart of spans for one language.

    df must already be filtered to a single language.
    keystone_pos and pos_to_name come from lang_meta[lang_id].
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
            y=1.02,
            xanchor="right",
            x=1,
        ),
        # Scale height so every span label has ~22px of vertical space.
        height=max(400, len(labels) * 22),
        margin=dict(l=180, r=20, t=60, b=60),
        template="simple_white",
    )

    return fig


def charts_by_language(df, lang_meta):
    """Produce one domain_chart per language.

    Returns dict[lang_id, Figure]. Each chart uses that language's own
    position numbering and pos_to_name — languages are never mixed.
    """
    return {
        lang_id: domain_chart(
            df[df["Language"] == lang_id],
            meta["keystone_pos"],
            meta["pos_to_name"],
        )
        for lang_id, meta in lang_meta.items()
    }
