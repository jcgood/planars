#!/usr/bin/env python3
"""Render the planars schema files as human-readable Markdown.

Reads from schemas/diagnostic_criteria.yaml (criteria and analyses),
schemas/diagnostic_classes.yaml (qualification rules), schemas/terms.yaml
(glossary and chart labels), and schemas/planar.yaml (structural columns).

Run from the repo root:
    python render_codebook.py              # print to stdout
    python render_codebook.py codebook.md  # write to file
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SCHEMAS = ROOT / "schemas"


def _wrap(text: str, indent: int = 0) -> str:
    prefix = " " * indent
    return textwrap.fill(text.strip(), width=88, initial_indent=prefix, subsequent_indent=prefix)


def render(
    dc: dict,    # diagnostic_criteria.yaml
    classes: dict,  # diagnostic_classes.yaml (for qualification_rule lookup)
    terms: dict,    # terms.yaml
    planar: dict,   # planar.yaml
) -> str:
    lines = []

    lines.append("# Planars Schema Reference\n")
    lines.append(
        "_Source of truth for diagnostic criteria, analytical terms, and planar structure. "
        "Generated from `schemas/diagnostic_criteria.yaml`, `schemas/diagnostic_classes.yaml`, "
        "`schemas/terms.yaml`, and `schemas/planar.yaml`._\n"
    )

    # -----------------------------------------------------------------------
    # Structural columns (from planar.yaml)
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Structural Columns\n")
    lines.append("Present in every filled TSV.\n")
    for col in planar.get("structural_columns", []):
        lines.append(f"### `{col['name']}`\n")
        lines.append(_wrap(col["description"]) + "\n")

    # -----------------------------------------------------------------------
    # Analyses (from diagnostic_criteria.yaml, with qualification_rule from
    # diagnostic_classes.yaml)
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Analyses\n")

    # Build a quick lookup for qualification_rule by class name
    classes_by_name = {
        cls["name"]: cls
        for cls in classes.get("classes", [])
    }

    for analysis in dc.get("analyses", []):
        name = analysis["name"]
        desc = analysis.get("description", "").strip()
        status = ""
        if "[NEEDS REVIEW]" in desc:
            status = " ⚠️ NEEDS REVIEW"
            desc = desc.replace("[NEEDS REVIEW]", "").strip()

        lines.append(f"### {name}{status}\n")
        lines.append(_wrap(desc) + "\n")

        criteria = analysis.get("diagnostic_criteria", [])
        if criteria:
            lines.append("**Diagnostic criteria:**\n")
            for p in criteria:
                pname = p["name"]
                vals = ", ".join(f"`{v}`" for v in p.get("values", []))
                pdesc = p.get("description", "").strip()
                needs_review = "[NEEDS REVIEW]" in pdesc or "[PLACEHOLDER]" in pdesc
                tag = " _(needs review)_" if "[NEEDS REVIEW]" in pdesc else (" _(placeholder)_" if "[PLACEHOLDER]" in pdesc else "")
                pdesc = pdesc.replace("[NEEDS REVIEW]", "").replace("[PLACEHOLDER]", "").strip()
                lines.append(f"- **`{pname}`** ({vals}){tag}  \n  {_wrap(pdesc, indent=2).lstrip()}\n")

        rule = classes_by_name.get(name, {}).get("qualification_rule", "").strip()
        if rule:
            lines.append("**Qualification rule:**\n")
            lines.append("```\n" + rule + "\n```\n")

    # -----------------------------------------------------------------------
    # Shared values (from diagnostic_criteria.yaml)
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Shared Criterion Values\n")
    lines.append("| Value | Meaning |\n|---|---|\n")
    for sv in dc.get("shared_values", []):
        meaning = sv["meaning"].strip().replace("\n", " ")
        lines.append(f"| `{sv['value']}` | {meaning} |\n")
    lines.append("\n")

    # -----------------------------------------------------------------------
    # Terms / Glossary (from terms.yaml)
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Glossary\n")
    for t in terms.get("terms", []):
        lines.append(f"**{t['term']}**  \n")
        lines.append(_wrap(t["definition"], indent=0) + "\n")

    # -----------------------------------------------------------------------
    # Chart labels (from terms.yaml)
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Chart Labels\n")
    lines.append(
        "Short labels used in `domain_chart()` output. "
        "Subject to revision pending collaborator input (see issue #8).\n"
    )

    cl = terms.get("chart_labels", {})

    for section, data in cl.items():
        lines.append(f"### {section}\n")
        if isinstance(data, list):
            lines.append("| Label | Meaning |\n|---|---|\n")
            for entry in data:
                meaning = entry.get("meaning", "").strip().replace("\n", " ")
                lines.append(f"| `{entry['label']}` | {meaning} |\n")
            lines.append("\n")
        elif isinstance(data, dict):
            note = data.get("note", "")
            if note:
                lines.append(f"_{note.strip()}_\n")
            label_list = data.get("labels", [])
            if label_list:
                lines.append("| Label | Meaning |\n|---|---|\n")
                for entry in label_list:
                    meaning = entry.get("meaning", "").strip().replace("\n", " ")
                    lines.append(f"| `{entry['label']}` | {meaning} |\n")
                lines.append("\n")
            prefixes = data.get("prefixes")
            suffixes = data.get("suffixes")
            if prefixes:
                lines.append("**Prefixes:**\n")
                for k, v in prefixes.items():
                    lines.append(f"- `{k}`: {v}\n")
                lines.append("\n")
            if suffixes:
                lines.append("**Suffixes:** `strict complete`, `loose complete`, `strict partial`, `loose partial`\n")

    return "".join(lines)


def main():
    with open(SCHEMAS / "diagnostic_criteria.yaml") as f:
        dc = yaml.safe_load(f)
    with open(SCHEMAS / "diagnostic_classes.yaml") as f:
        classes = yaml.safe_load(f)
    with open(SCHEMAS / "terms.yaml") as f:
        terms = yaml.safe_load(f)
    with open(SCHEMAS / "planar.yaml") as f:
        planar = yaml.safe_load(f)

    output = render(dc, classes, terms, planar)

    if len(sys.argv) > 1:
        out_path = Path(sys.argv[1])
        out_path.write_text(output, encoding="utf-8")
        print(f"Written to {out_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
