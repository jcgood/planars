#!/usr/bin/env python3
"""Generate Graphviz diagrams of planars schema structure and analysis taxonomy.

Two diagram types are available:

  taxonomy (default)
    All analysis classes grouped by domain type, with diagnostic criteria
    listed inside each node, and language instances connected on the right
    with construction names on edges for construction-specific classes.

  schema-map
    The four YAML schema files, their roles, cross-references, and how the
    per-language diagnostics files derive from them.

Run from the repo root:
    python generate_diagram.py                          # taxonomy → stdout
    python generate_diagram.py out.svg                  # taxonomy → SVG (requires dot)
    python generate_diagram.py out.pdf                  # taxonomy → PDF
    python generate_diagram.py out.dot                  # taxonomy → DOT source
    python generate_diagram.py --diagram schema-map out.svg   # schema map → SVG
    python generate_diagram.py --diagram schema-map           # schema map → stdout
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
# Schema-map diagram (diagram 2)
# ---------------------------------------------------------------------------

def build_schema_map_dot() -> str:
    """Return DOT source for the schema file relationships diagram.

    Shows the four YAML schema files, their source-of-truth roles,
    cross-references between them, and how the per-language diagnostics
    files derive from / are validated against them.
    """
    _SCHEMA_BG     = "#e8f4f8"
    _SCHEMA_BORDER = "#2a6496"
    _LANG_BG       = "#fff8e1"
    _LANG_BORDER   = "#c07800"
    _DERIVED_BG    = "#f3f3f3"
    _DERIVED_BORDER = "#888888"

    def _schema_node(node_id: str, title: str, items: list[str]) -> str:
        rows = [
            f'<TR><TD BGCOLOR="{_SCHEMA_BORDER}" ALIGN="CENTER" CELLPADDING="5">'
            f'<FONT COLOR="white"><B>{title}</B></FONT></TD></TR>',
        ]
        for item in items:
            rows.append(
                f'<TR><TD ALIGN="LEFT" CELLPADDING="4" BGCOLOR="{_SCHEMA_BG}">'
                f'<FONT POINT-SIZE="10">{item}</FONT></TD></TR>'
            )
        inner = "".join(rows)
        label = f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">{inner}</TABLE>>'
        return f'    {node_id} [shape=none, margin=0, label={label}];'

    def _lang_node(node_id: str, title: str, subtitle: str, bg: str, border: str) -> str:
        label = (
            f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">'
            f'<TR><TD BGCOLOR="{border}" ALIGN="CENTER" CELLPADDING="5">'
            f'<FONT COLOR="white"><B>{title}</B></FONT></TD></TR>'
            f'<TR><TD ALIGN="CENTER" CELLPADDING="4" BGCOLOR="{bg}">'
            f'<FONT POINT-SIZE="10"><I>{subtitle}</I></FONT></TD></TR>'
            f'</TABLE>>'
        )
        return f'    {node_id} [shape=none, margin=0, label={label}];'

    lines: list[str] = []
    lines.append("digraph schema_map {")
    lines.append('    graph [rankdir=LR, ranksep=1.8, nodesep=0.5, pad=0.5,')
    lines.append('           fontname="Helvetica",')
    lines.append('           label="Planars Schema File Relationships",')
    lines.append('           labelloc=t, fontsize=15];')
    lines.append('    node  [fontname="Helvetica", fontsize=11];')
    lines.append('    edge  [fontname="Helvetica", fontsize=9];')
    lines.append("")

    # ---- Schema file cluster ------------------------------------------------
    lines.append("    subgraph cluster_schemas {")
    lines.append('        label="schemas/"; style=filled;')
    lines.append(f'        fillcolor="{_SCHEMA_BG}"; color="{_SCHEMA_BORDER}"; penwidth=2.0;')
    lines.append('        fontname="Helvetica-Bold"; fontsize=12; margin=20;')
    lines.append("")
    lines.append(_schema_node("dc_classes", "diagnostic_classes.yaml", [
        "source of truth for:",
        "· class taxonomy (name, domain_type)",
        "· applicability (universal / conditional)",
        "· required + optional criteria per class",
        "· qualification rules",
        "· collection_required flag",
    ]))
    lines.append(_schema_node("dc_criteria", "diagnostic_criteria.yaml", [
        "source of truth for:",
        "· criterion definitions",
        "· valid values per criterion",
        "· linguistic descriptions",
    ]))
    lines.append(_schema_node("planar_yaml", "planar.yaml", [
        "source of truth for:",
        "· structural column definitions",
        "· element conventions",
        "· trailing_columns list",
    ]))
    lines.append(_schema_node("terms_yaml", "terms.yaml", [
        "source of truth for:",
        "· analytical term definitions",
        "· chart label glossary",
    ]))
    lines.append("    }")
    lines.append("")

    # ---- Per-language files cluster -----------------------------------------
    lines.append("    subgraph cluster_lang {")
    lines.append('        label="coded_data/{lang_id}/planar_input/";')
    lines.append(f'        style=filled; fillcolor="{_LANG_BG}";')
    lines.append(f'        color="{_LANG_BORDER}"; penwidth=2.0;')
    lines.append('        fontname="Helvetica-Bold"; fontsize=12; margin=20;')
    lines.append("")
    lines.append(_lang_node("diag_yaml", "diagnostics_{lang}.yaml",
                            "coordinator-edited source of truth", _LANG_BG, _LANG_BORDER))
    lines.append(_lang_node("diag_tsv", "diagnostics_{lang}.tsv",
                            "derived artifact (never hand-edited)", _DERIVED_BG, _DERIVED_BORDER))
    lines.append("    }")
    lines.append("")

    # ---- Cross-references within schemas ------------------------------------
    lines.append("    // Cross-references between schema files")
    lines.append(
        '    dc_classes -> dc_criteria [label="required_criteria\\nreferences", '
        'color="#2a6496", fontcolor="#2a6496", style=dashed];'
    )
    lines.append("")

    # ---- Schema → language derivation / validation --------------------------
    lines.append("    // Schema files → per-language diagnostics")
    lines.append(
        '    diag_yaml -> diag_tsv [label="sync-diagnostics-yaml\\n--apply", '
        'color="#c07800", fontcolor="#c07800", penwidth=1.5];'
    )
    lines.append(
        '    dc_classes -> diag_tsv [label="check-codebook\\nvalidates", '
        'color="#888888", fontcolor="#888888", style=dashed];'
    )
    lines.append(
        '    dc_criteria -> diag_tsv [label="check-codebook\\nvalidates", '
        'color="#888888", fontcolor="#888888", style=dashed];'
    )
    lines.append(
        '    dc_classes -> diag_yaml [label="class names\\nmust exist here", '
        'color="#888888", fontcolor="#888888", style=dotted];'
    )
    lines.append("")

    # ---- Legend -------------------------------------------------------------
    lines.append("    subgraph cluster_legend {")
    lines.append('        label="Legend"; style=filled; fillcolor="#f8f8f8";')
    lines.append('        color="#cccccc"; penwidth=1.0; fontsize=10; margin=10; rank=sink;')
    lines.append(f'        _leg_s [shape=box, style=filled, fillcolor="{_SCHEMA_BG}", '
                 f'color="{_SCHEMA_BORDER}", label="Schema file", fontsize=9];')
    lines.append(f'        _leg_l [shape=box, style=filled, fillcolor="{_LANG_BG}", '
                 f'color="{_LANG_BORDER}", label="Per-language file\\n(coordinator-edited)", fontsize=9];')
    lines.append(f'        _leg_d [shape=box, style=filled, fillcolor="{_DERIVED_BG}", '
                 f'color="{_DERIVED_BORDER}", label="Per-language file\\n(derived artifact)", fontsize=9];')
    lines.append('        _leg_sync  [shape=point, width=0]; _leg_val  [shape=point, width=0];')
    lines.append('        _leg_s -> _leg_l -> _leg_d [style=invis];')
    lines.append('        _leg_sync -> _leg_val [label="generates", color="#c07800", fontcolor="#c07800", fontsize=8];')
    lines.append('        _leg_sync2 -> _leg_val2 [label="validates", color="#888888", '
                 'fontcolor="#888888", style=dashed, fontsize=8];')
    lines.append('        _leg_sync [shape=point, width=0]; _leg_val [shape=point, width=0];')
    lines.append('        _leg_sync2 [shape=point, width=0]; _leg_val2 [shape=point, width=0];')
    lines.append("    }")

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared render helper
# ---------------------------------------------------------------------------

def _render(dot_source: str, out_path: Path | None) -> None:
    if out_path is None:
        print(dot_source)
        return

    suffix = out_path.suffix.lower()
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    # Parse --diagram flag
    diagram = "taxonomy"
    if "--diagram" in args:
        idx = args.index("--diagram")
        if idx + 1 >= len(args):
            raise SystemExit("--diagram requires an argument: taxonomy | schema-map")
        diagram = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if diagram not in {"taxonomy", "schema-map"}:
        raise SystemExit(f"Unknown diagram '{diagram}'. Choose: taxonomy | schema-map")

    out_path = Path(args[0]) if args else None

    if diagram == "taxonomy":
        classes    = _load_classes()
        instances  = _load_language_instances()
        dot_source = build_dot(classes, instances)
    else:
        dot_source = build_schema_map_dot()

    _render(dot_source, out_path)


if __name__ == "__main__":
    main()
