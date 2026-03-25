#!/usr/bin/env python3
"""Generate a Graphviz diagram of the planars analysis class taxonomy.

Shows all analysis classes grouped by domain type, with their diagnostic
criteria listed inside each node, and the languages that instantiate each
class (with construction names for construction-specific classes).

Run from the repo root:
    python generate_diagram.py              # print DOT source to stdout
    python generate_diagram.py out.dot      # write DOT source
    python generate_diagram.py out.svg      # render to SVG  (requires dot)
    python generate_diagram.py out.pdf      # render to PDF  (requires dot)
    python generate_diagram.py out.png      # render to PNG  (requires dot)
"""
from __future__ import annotations

import csv
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT    = Path(__file__).resolve().parent
SCHEMAS = ROOT / "schemas"
CODED   = ROOT / "coded_data"

# ---------------------------------------------------------------------------
# Visual style
# ---------------------------------------------------------------------------

_DOMAIN_HEADER_BG = {
    "morphosyntactic": "#4a90d9",
    "phonological":    "#d9714a",
    "indeterminate":   "#5aa64a",
}
_DOMAIN_CLUSTER_BG = {
    "morphosyntactic": "#eaf3fb",
    "phonological":    "#fef3ec",
    "indeterminate":   "#edfbe9",
}
_DOMAIN_BORDER = {
    "morphosyntactic": "#4a90d9",
    "phonological":    "#d9714a",
    "indeterminate":   "#5aa64a",
}
_DOMAIN_LABEL = {
    "morphosyntactic": "Morphosyntactic",
    "phonological":    "Phonological",
    "indeterminate":   "Indeterminate",
}
_DOMAIN_ORDER = ["morphosyntactic", "phonological", "indeterminate"]

_LANG_FILL    = "#fffde7"
_LANG_BORDER  = "#f0a500"
_SYNTH_FILL   = "#f5f5f5"
_SYNTH_BORDER = "#aaaaaa"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_classes() -> list[dict]:
    with open(SCHEMAS / "diagnostic_classes.yaml") as f:
        return yaml.safe_load(f)["classes"]


def _load_language_instances() -> dict[str, list[dict]]:
    """Return {class_name: [{lang, constructions}]} from all diagnostics_*.tsv files.

    Skips synth0001 language unless it adds unique information (it mirrors
    stan1293 constructions exactly so we keep it to show multiple instances).
    """
    # class_name → list of {lang, constructions (list[str])}
    instances: dict[str, list[dict]] = defaultdict(list)

    lang_dirs = sorted(d for d in CODED.iterdir() if d.is_dir())
    for lang_dir in lang_dirs:
        lang_id = lang_dir.name
        diag_files = sorted((lang_dir / "planar_input").glob("diagnostics_*.tsv"))
        if not diag_files:
            continue
        with open(diag_files[0]) as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        for row in rows:
            cls = row.get("Class", "").strip()
            if not cls:
                continue
            raw = row.get("Constructions", row.get("Construction", "")).strip()
            constructions = [c.strip() for c in raw.split(",") if c.strip()] if raw else []
            instances[cls].append({"lang": lang_id, "constructions": constructions})

    return dict(instances)


def _display_name(lang_id: str) -> str:
    try:
        from planars.languages import get_display_name
        return get_display_name(lang_id)
    except Exception:
        return lang_id


# ---------------------------------------------------------------------------
# HTML-like label builder for class nodes
# ---------------------------------------------------------------------------

def _class_label(cls: dict) -> str:
    """Build an HTML-like label showing class name, applicability, and criteria."""
    name        = cls.get("display_name", cls["name"])
    applicability = cls["applicability"]
    domain      = cls["domain_type"]
    hdr_bg      = _DOMAIN_HEADER_BG[domain]
    req         = cls.get("required_criteria", [])
    opt         = cls.get("optional_criteria", [])

    app_marker = "" if applicability == "universal" else " <I>(conditional)</I>"

    # Header row
    rows = [
        f'<TR><TD BGCOLOR="{hdr_bg}" ALIGN="CENTER" CELLPADDING="5">'
        f'<FONT COLOR="white"><B>{name}</B>{app_marker}</FONT></TD></TR>'
    ]

    # Criteria rows
    if req or opt:
        crit_lines = []
        for c in req:
            crit_lines.append(f'<FONT POINT-SIZE="10">{c}</FONT>')
        for c in opt:
            crit_lines.append(f'<FONT POINT-SIZE="9" COLOR="#888888"><I>[{c}]</I></FONT>')
        crit_html = "<BR/>".join(crit_lines)
        rows.append(
            f'<TR><TD ALIGN="LEFT" CELLPADDING="5" BGCOLOR="#ffffff">{crit_html}</TD></TR>'
        )

    inner = "".join(rows)
    return f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">{inner}</TABLE>>'


def _node_id(name: str) -> str:
    return name.replace("-", "_")


# ---------------------------------------------------------------------------
# DOT generation
# ---------------------------------------------------------------------------

def build_dot(classes: list[dict], instances: dict[str, list[dict]]) -> str:
    by_domain: dict[str, list[dict]] = defaultdict(list)
    for cls in classes:
        by_domain[cls["domain_type"]].append(cls)

    lines: list[str] = []
    lines.append("digraph planars {")
    lines.append('    graph [rankdir=LR, ranksep=1.5, nodesep=0.4, pad=0.5,')
    lines.append('           fontname="Helvetica",')
    lines.append('           label="Planars Analysis Class Taxonomy",')
    lines.append('           labelloc=t, fontsize=15];')
    lines.append('    node  [fontname="Helvetica", fontsize=11];')
    lines.append('    edge  [fontname="Helvetica", fontsize=9, color="#888888"];')
    lines.append("")

    # ---- Class nodes in domain-type clusters --------------------------------
    for domain in _DOMAIN_ORDER:
        if domain not in by_domain:
            continue
        bg     = _DOMAIN_CLUSTER_BG[domain]
        border = _DOMAIN_BORDER[domain]
        label  = _DOMAIN_LABEL[domain]

        lines.append(f"    subgraph cluster_{domain} {{")
        lines.append(f'        label="{label}";')
        lines.append(f'        style=filled; fillcolor="{bg}"; color="{border}"; penwidth=2.0;')
        lines.append(f'        fontname="Helvetica-Bold"; fontsize=12; margin=16;')
        lines.append("")

        sorted_classes = sorted(
            by_domain[domain],
            key=lambda c: (0 if c["applicability"] == "universal" else 1,
                           c.get("display_name", c["name"]).lower()),
        )
        for cls in sorted_classes:
            nid   = _node_id(cls["name"])
            label_html = _class_label(cls)
            lines.append(f"        {nid} [shape=none, margin=0, label={label_html}];")

        lines.append("    }")
        lines.append("")

    # ---- Language nodes ------------------------------------------------------
    all_langs: list[str] = sorted({
        inst["lang"]
        for inst_list in instances.values()
        for inst in inst_list
    })

    lines.append("    // Language nodes")
    for lang_id in all_langs:
        nid      = _node_id(lang_id)
        disp     = _display_name(lang_id)
        # Escape brackets for DOT
        disp_dot = disp.replace("[", "\\[").replace("]", "\\]")
        is_synth = lang_id.startswith("synth")
        fill     = _SYNTH_FILL   if is_synth else _LANG_FILL
        border   = _SYNTH_BORDER if is_synth else _LANG_BORDER
        style    = "filled,dashed" if is_synth else "filled"
        lines.append(
            f'    {nid} [shape=ellipse, style="{style}", fillcolor="{fill}", '
            f'color="{border}", label="{disp_dot}"];'
        )
    lines.append("")

    # ---- Edges: class → language --------------------------------------------
    lines.append("    // Class → language instance edges")
    for cls in classes:
        cls_nid   = _node_id(cls["name"])
        cls_insts = instances.get(cls["name"], [])
        is_specific = cls.get("specificity") == "construction_specific"

        for inst in cls_insts:
            lang_nid = _node_id(inst["lang"])
            if is_specific and inst["constructions"]:
                edge_label = "\\n".join(inst["constructions"])
                lines.append(
                    f'    {cls_nid} -> {lang_nid} [label="{edge_label}", '
                    f'fontsize=8, fontcolor="#555555"];'
                )
            else:
                lines.append(f"    {cls_nid} -> {lang_nid};")

    lines.append("")

    # ---- Legend --------------------------------------------------------------
    lines.append("    subgraph cluster_legend {")
    lines.append('        label="Legend"; style=filled; fillcolor="#f8f8f8";')
    lines.append('        color="#cccccc"; penwidth=1.0; fontsize=10; margin=10; rank=sink;')
    lines.append('        _leg_u  [shape=box,     style=filled,         fillcolor="#ffffff",')
    lines.append(f'                 label="Universal class",   fontsize=9, color="{_DOMAIN_BORDER["morphosyntactic"]}"];')
    lines.append('        _leg_c  [shape=box,     style="filled",       fillcolor="#ffffff",')
    lines.append(f'                 label="Conditional class\\n(italic in header)", fontsize=9, color="{_DOMAIN_BORDER["phonological"]}"];')
    lines.append(f'        _leg_rl [shape=ellipse, style="filled",       fillcolor="{_LANG_FILL}",  color="{_LANG_BORDER}",   label="Real language",      fontsize=9];')
    lines.append(f'        _leg_sl [shape=ellipse, style="filled,dashed",fillcolor="{_SYNTH_FILL}", color="{_SYNTH_BORDER}", label="Synthetic language", fontsize=9];')
    lines.append('        _leg_u -> _leg_c -> _leg_rl -> _leg_sl [style=invis];')
    lines.append("    }")

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    classes   = _load_classes()
    instances = _load_language_instances()
    dot_source = build_dot(classes, instances)

    if len(sys.argv) < 2:
        print(dot_source)
        return

    out_path = Path(sys.argv[1])
    suffix   = out_path.suffix.lower()

    if suffix == ".dot":
        out_path.write_text(dot_source, encoding="utf-8")
        print(f"DOT source written to {out_path}")
        return

    if suffix in {".svg", ".pdf", ".png"}:
        fmt    = suffix.lstrip(".")
        result = subprocess.run(
            ["dot", f"-T{fmt}", "-o", str(out_path)],
            input=dot_source.encode(),
            capture_output=True,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stderr.decode())
            raise SystemExit(f"dot failed (exit {result.returncode})")
        print(f"Diagram written to {out_path}")
        return

    raise SystemExit(
        f"Unsupported output format '{suffix}'. Use .dot, .svg, .pdf, or .png."
    )


if __name__ == "__main__":
    main()
