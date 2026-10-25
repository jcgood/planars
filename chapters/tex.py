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
``lines(text)`` for schema prose whose indented lines must stay lines;
``comment(text)`` for plain text as ``%`` lines (a prose stub's
instructions); ``path(text)`` for a file path in ``\\input``.

The output is plain LaTeX tied to no document class (decision 1 of
docs/chapter-generation-plan.md): ``booktabs`` and ``longtable`` tables,
and the macros in ``planarschapter.sty`` (``STY``: ``\\pv``, ``\\claim``
for a checked statement in prose, and ``\\proseslot`` for a slot nobody
has written yet), which the build writes
at the top of ``.papers/``. **Examples** go through two macros of our
own, ``\\planarsex{form}{gloss}{translation}{source}`` and
``\\planarsplainex{sentence}{source}`` (a language whose examples need no
gloss), defined per venue in ``chapters/venues/<venue>.sty`` on top of the
venue's glossing package and written as ``.papers/planarsvenue.sty``; so
when the publisher's template arrives, a new venue file is all that
changes. ``example(...)`` in a template writes the right call for the
language's example style.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import jinja2

TEMPLATES = Path(__file__).resolve().parent / "templates"
# One file per venue (``venues/<venue>.sty``), copied to .papers/ as
# planarsvenue.sty: the example macros on top of the venue's glossing package.
VENUES = Path(__file__).resolve().parent / "venues"
VENUE_STY = "planarsvenue.sty"


def venues() -> list:
    """The venues there is a file for, by name."""
    return sorted(p.stem for p in VENUES.glob("*.sty"))


def venue_sty(venue: str) -> str:
    """The text of `venue`'s planarsvenue.sty. Fails on a venue with no file."""
    if venue not in venues():
        raise ValueError(f"No venue {venue!r}: there is a file in chapters/venues/ for "
                         f"{', '.join(venues())}. Write chapters/venues/{venue}.sty "
                         f"(defining \\planarsex and \\planarsplainex) to add one.")
    return (VENUES / f"{venue}.sty").read_text(encoding="utf-8")

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


_PATH = re.compile(r"[A-Za-z0-9_\-]+(/[A-Za-z0-9_\-]+)*")


def path(text: str) -> Tex:
    """A file path for ``\\input`` or ``\\include``, as it is (escaping would
    break it); only letters, digits, _ - and / are allowed."""
    if not _PATH.fullmatch(text):
        raise ValueError(f"Path {text!r} has characters \\input can't take; only letters, "
                         f"digits, _ - and / are allowed.")
    return Tex(text)


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


def comment(text) -> Tex:
    """Plain text as LaTeX comment lines (``% ...``), wrapped at 72
    columns. Not escaped: a comment is never typeset."""
    wrapped = textwrap.wrap(" ".join(str(text).split()), width=70) or [""]
    return Tex("\n".join(f"% {line}" for line in wrapped))


def example(form, gloss, translation, source, glossed: bool) -> Tex:
    """One example as the venue macro for its language's style: a glossed
    one through ``\\planarsex``, one needing no gloss (or a glossed
    language's example that came without one) through ``\\planarsplainex``."""
    if glossed and gloss and translation:
        return Tex(rf"\planarsex{{{escape(form)}}}{{{escape(gloss)}}}"
                   rf"{{{escape(translation)}}}{{{escape(source)}}}")
    return Tex(rf"\planarsplainex{{{escape(form)}}}{{{escape(source)}}}")


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
    env.globals.update(pv=pv, lines=lines, Tex=Tex, comment=comment, path=path, example=example)
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


_PVSET = re.compile(r"\\pvset\{([^}]*)\}\{(.*)\}$")


def read_values_tex(text: str) -> dict:
    """{name: value as values.tex writes it} from a values.tex values_tex wrote."""
    return {m.group(1): m.group(2) for m in map(_PVSET.match, text.splitlines()) if m}


STY =r"""% planarschapter.sty: macros the generated fragments use.
% Written by `python -m coding build-chapters`; never edit it by hand.
% Plain LaTeX, tied to no document class.
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{planarschapter}[2026/10/25 planars chapter fragments]
\RequirePackage{booktabs}
\RequirePackage{longtable}
\RequirePackage{array}
% \pvset{name}{value} stores a value (values.tex); \pv{name} prints it.
% A name with no value prints in bold and warns, so it is seen, not skipped.
% Robust, so a value can sit in a heading that goes into the contents.
\newcommand{\pvset}[2]{\expandafter\def\csname pv@#1\endcsname{#2}}
\DeclareRobustCommand{\pv}[1]{%
  \ifcsname pv@#1\endcsname\csname pv@#1\endcsname
  \else\textbf{[\detokenize{#1}?]}%
    \PackageWarning{planarschapter}{No value named #1}\fi}
% Running heads are upper-cased (\MakeUppercase), which would upper-case
% the value's name too; its argument is kept as written.
\ifdefined\AddToNoCaseChangeList\AddToNoCaseChangeList{\pv}\fi
% \claim{name}{text} prints text, a statement the prose argues from, and
% checks it against the named value: one that no longer holds is boxed
% with the value now, and warns. The build lists every such claim too.
\DeclareRobustCommand{\claim}[2]{%
  \ifcsname pv@#1\endcsname
    \expandafter\let\expandafter\planars@value\csname pv@#1\endcsname
    \edef\planars@now{\expandafter\detokenize\expandafter{\planars@value}}%
    \edef\planars@said{\detokenize{#2}}%
    \ifx\planars@now\planars@said#2%
    \else\fbox{#2}\textsuperscript{\textbf{[now \pv{#1}]}}%
      \PackageWarning{planarschapter}{Claim #1 no longer holds}\fi
  \else\textbf{[\detokenize{#1}?]}%
    \PackageWarning{planarschapter}{No value named #1}\fi}
\ifdefined\AddToNoCaseChangeList\AddToNoCaseChangeList{\claim}\fi
% \proseslot{name} stands in a prose slot nobody has written yet, so the
% gap shows in the PDF.
\newcommand{\proseslot}[1]{\par\noindent\fbox{\textit{Still to write: #1}}\par}
"""
