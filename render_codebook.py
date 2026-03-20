#!/usr/bin/env python3
"""Render codebook.yaml as human-readable Markdown.

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
CODEBOOK = ROOT / "schemas" / "codebook.yaml"


def _wrap(text: str, indent: int = 0) -> str:
    prefix = " " * indent
    return textwrap.fill(text.strip(), width=88, initial_indent=prefix, subsequent_indent=prefix)


def render(cb: dict) -> str:
    lines = []

    lines.append("# Planars Codebook\n")
    lines.append(
        "_Source of truth for parameters, values, and analytical terms. "
        "Generated from `codebook.yaml`._\n"
    )

    # -----------------------------------------------------------------------
    # Structural columns
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Structural Columns\n")
    lines.append("Present in every filled TSV.\n")
    for col in cb.get("structural_columns", []):
        lines.append(f"### `{col['name']}`\n")
        lines.append(_wrap(col["description"]) + "\n")

    # -----------------------------------------------------------------------
    # Analyses
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Analyses\n")

    for analysis in cb.get("analyses", []):
        name = analysis["name"]
        status = ""
        desc = analysis.get("description", "").strip()
        if "[NEEDS REVIEW]" in desc:
            status = " ⚠️ NEEDS REVIEW"
            desc = desc.replace("[NEEDS REVIEW]", "").strip()

        lines.append(f"### {name}{status}\n")
        lines.append(_wrap(desc) + "\n")

        params = analysis.get("parameters", [])
        if params:
            lines.append("**Parameters:**\n")
            for p in params:
                pname = p["name"]
                vals = ", ".join(f"`{v}`" for v in p.get("values", []))
                pdesc = p.get("description", "").strip()
                needs_review = "[NEEDS REVIEW]" in pdesc or "[PLACEHOLDER]" in pdesc
                tag = " _(needs review)_" if "[NEEDS REVIEW]" in pdesc else (" _(placeholder)_" if "[PLACEHOLDER]" in pdesc else "")
                pdesc = pdesc.replace("[NEEDS REVIEW]", "").replace("[PLACEHOLDER]", "").strip()
                lines.append(f"- **`{pname}`** ({vals}){tag}  \n  {_wrap(pdesc, indent=2).lstrip()}\n")

        rule = analysis.get("qualification_rule", "").strip()
        if rule:
            lines.append("**Qualification rule:**\n")
            lines.append("```\n" + rule + "\n```\n")

    # -----------------------------------------------------------------------
    # Shared values
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Shared Parameter Values\n")
    lines.append("| Value | Meaning |\n|---|---|\n")
    for sv in cb.get("shared_values", []):
        meaning = sv["meaning"].strip().replace("\n", " ")
        lines.append(f"| `{sv['value']}` | {meaning} |\n")
    lines.append("\n")

    # -----------------------------------------------------------------------
    # Terms / Glossary
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Glossary\n")
    for t in cb.get("terms", []):
        lines.append(f"**{t['term']}**  \n")
        lines.append(_wrap(t["definition"], indent=0) + "\n")

    # -----------------------------------------------------------------------
    # Chart labels
    # -----------------------------------------------------------------------
    lines.append("---\n")
    lines.append("## Chart Labels\n")
    lines.append(
        "Short labels used in `domain_chart()` output. "
        "Subject to revision pending collaborator input (see issue #8).\n"
    )

    cl = cb.get("chart_labels", {})

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
    with open(CODEBOOK) as f:
        cb = yaml.safe_load(f)

    output = render(cb)

    if len(sys.argv) > 1:
        out_path = Path(sys.argv[1])
        out_path.write_text(output, encoding="utf-8")
        print(f"Written to {out_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
