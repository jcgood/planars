"""Turning chapter data into LaTeX: escaping, value names, and the templates.

The wording of every generated sentence and table is in the Jinja2
templates in ``chapters/templates/`` (one per fragment), never in code, so
changing a sentence means editing a template. The templates use LaTeX-safe
delimiters: ``\\VAR{x}`` prints a value, ``\\BLOCK{for ...}`` is a statement,
``\\#{...}`` a comment.

**Everything a template prints is escaped** for LaTeX unless it is a
``Tex`` (already LaTeX): ``pv(key)`` gives ``\\pv{key}``, the macro that
prints a named value from ``values.tex``. So a position name such as
``NP{S,A,P}`` or ``v:ad_VP`` can never break the document, and a template
that forgets to escape is impossible. Filters: ``|name`` for an identifier
set in typewriter (escaped, with line breaks allowed after _ : -);
``lines(text)`` for schema prose whose indented lines must stay lines.

The output is plain LaTeX tied to no document class (decision 1 of
docs/chapter-generation-plan.md): ``booktabs`` and ``longtable`` tables,
and the macros in ``planarschapter.sty`` (``STY``), which the build writes
beside the fragments.
"""

from __future__ import annotations

import re
from pathlib import Path

import jinja2

TEMPLATES = Path(__file__).resolve().parent / "templates"

_SPECIALS = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
    "#": r"\#", "^": r"\textasciicircum{}", "_": r"\_", "%": r"\%", "~": r"\textasciitilde{}",
    "<": r"\textless{}", ">": r"\textgreater{}",
    # Mathematical symbols in schema prose, which a text font may lack
    # (pdflatex stops on them). tests/test_chapter_build.py fails when the
    # schemas use one not listed here.
    "∈": r"\ensuremath{\in}", "∉": r"\ensuremath{\notin}", "→": r"\ensuremath{\rightarrow}",
    "←": r"\ensuremath{\leftarrow}", "×": r"\ensuremath{\times}", "≥": r"\ensuremath{\geq}",
    "≤": r"\ensuremath{\leq}", "≠": r"\ensuremath{\neq}",
}
_SPECIAL_RE = re.compile("|".join(re.escape(c) for c in _SPECIALS))

# A value name may hold letters, digits and . _ - (stan1293.span.ciscategorial.
# general.strict_complete_span.left); anything else could break \csname.
VALUE_NAME = re.compile(r"[A-Za-z0-9._\-]+")


class Tex(str):
    """A string that is already LaTeX and is printed as it is."""


def escape(text) -> str:
    """`text` with LaTeX's special characters made literal."""
    return _SPECIAL_RE.sub(lambda m: _SPECIALS[m.group()], str(text))


def name(text) -> Tex:
    """An identifier (a position, construction or criterion name), escaped,
    with a line break allowed after each _ : - so a long one can't run into
    the margin (typewriter text is never hyphenated)."""
    return Tex(re.sub(r"(\\_|:|-)", r"\1\\allowbreak{}", escape(text)))


def check_value_name(name: str) -> str:
    if not VALUE_NAME.fullmatch(name):
        raise ValueError(f"Value name {name!r} has characters LaTeX can't take in \\pv; "
                         f"only letters, digits and . _ - are allowed.")
    return name


def pv(name: str) -> Tex:
    """``\\pv{name}``: prints the named value from values.tex."""
    return Tex(rf"\pv{{{check_value_name(name)}}}")


def lines(text) -> Tex:
    """Schema prose with its line breaks kept: a YAML folded block keeps a
    newline only where the author indented a line (a list inside a span
    rule), so each such line starts a new line, indented as written."""
    out = []
    for i, line in enumerate(str(text).strip().split("\n")):
        indent = len(line) - len(line.lstrip(" "))
        body = (rf"\hspace*{{{indent / 2:g}em}}" if indent else "") + escape(line.strip())
        out.append(body if i == 0 else r"\newline " + body)
    return Tex("\n".join(out))


def _finalize(value):
    if isinstance(value, Tex):
        return value
    return escape("" if value is None else value)


def environment() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES),
        block_start_string=r"\BLOCK{", block_end_string="}",
        variable_start_string=r"\VAR{", variable_end_string="}",
        comment_start_string=r"\#{", comment_end_string="}",
        trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined, autoescape=False, finalize=_finalize,
    )
    env.globals.update(pv=pv, lines=lines, Tex=Tex)
    env.filters["tex"] = escape
    env.filters["name"] = name
    return env


def render(template: str, **context) -> str:
    return environment().get_template(template).render(**context)


def value_text(value) -> str:
    """How a value is written into values.tex."""
    if isinstance(value, float):
        return f"{value:g}"
    return escape(value)


def values_tex(values: dict, header: str) -> str:
    """values.tex: one ``\\pvset{name}{value}`` per value, sorted by name."""
    body = "".join(rf"\pvset{{{check_value_name(k)}}}{{{value_text(values[k])}}}" + "\n"
                   for k in sorted(values))
    return header + body


STY = r"""% planarschapter.sty: macros the generated fragments use.
% Written by `python -m chapters build`; never edit it by hand.
% Plain LaTeX, tied to no document class.
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{planarschapter}[2026/10/25 planars chapter fragments]
\RequirePackage{booktabs}
\RequirePackage{longtable}
\RequirePackage{array}
% \pvset{name}{value} stores a value (values.tex); \pv{name} prints it.
% A name with no value prints in bold and warns, so it is seen, not skipped.
\newcommand{\pvset}[2]{\expandafter\def\csname pv@#1\endcsname{#2}}
\newcommand{\pv}[1]{%
  \ifcsname pv@#1\endcsname\csname pv@#1\endcsname
  \else\textbf{[\detokenize{#1}?]}%
    \PackageWarning{planarschapter}{No value named #1}\fi}
"""
