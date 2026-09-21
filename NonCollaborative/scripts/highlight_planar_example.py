"""Generate a matching pair of PDFs for one glossed example: a copy of the
"reduced" planar table with the positions that example uses recolored, and a
standalone card showing the example itself with the same morphemes/position
numbers recolored to match -- so the two can sit side by side and the reader
can see at a glance which table rows the example draws on.

General script, specific example: the example's morphemes, positions, gloss,
translation and citation live in their own small YAML file (see
NonCollaborative/examples/nyan1308_not_just_chairs.yaml for the format), kept
separate from this script so a new example is just a new YAML file, not a
code change.

Usage:
    python highlight_planar_example.py \\
        ../planar_tables/planar_nyan1308.tsv \\
        ../examples/nyan1308_not_just_chairs.yaml

    # override the default highlight color (a dark warm red, #A23E40):
    python highlight_planar_example.py ... --color CC6600

    # override which positions get highlighted (default: every position any
    # morpheme in the example uses):
    python highlight_planar_example.py ... --positions 5,6,10

    # example card background/text color (default: white bg, black text --
    # matches the planar table; for a slide-style dark card, e.g.):
    python highlight_planar_example.py ... --bg-color 000000 --text-color FFFFFF

    # no highlighting at all -- a plain example card, every morpheme in the
    # example's own text/bg color, nothing recolored (the highlighted table is
    # still written, just with nothing highlighted in it either):
    python highlight_planar_example.py ... --no-highlight

    # running the same example twice with different styling? give each run its
    # own --label, or the second run's output silently overwrites the first's
    # (both would otherwise write to the identical filename):
    python highlight_planar_example.py ... --bg-color 000000 --text-color FFFFFF --label basic_black

Both files reuse machinery from make_planar_latex.py (the plain "reduced"
table logic, and the xelatex render/compile-check step) rather than
duplicating it -- run from the same directory, or make sure this directory
is on PYTHONPATH, so the `import make_planar_latex` below resolves.

Output goes to NonCollaborative/results/planar-structure/ as (add --label <x> to get
..._<example_name>_<x>.pdf instead, so a differently-styled run doesn't
overwrite a previous one):
    <lang>_planar_table_<example_name>_highlighted.pdf
    <lang>_example_<example_name>.pdf
"""

import argparse
import os
import re
import subprocess
import tempfile

import yaml

import make_planar_latex as mpl

RESULTS_DIR = mpl.RESULTS_DIR

DEFAULT_COLOR_HEX = "A23E40"
COLOR_NAME = "planarhighlight"

# Gill Sans, matching the coordinator's existing hand-made example slides (as opposed
# to the planar table's Times New Roman, which matches the manuscript specifically --
# these are two different artifacts with two different visual jobs).
GILL_SANS_FONT_SETUP = r"""\usepackage{fontspec}
\setmainfont{Gill Sans}"""

DEFAULT_BG_HEX = "FFFFFF"
DEFAULT_TEXT_HEX = "000000"
BG_COLOR_NAME = "planarbg"
TEXT_COLOR_NAME = "planartext"

# Filled tikz node for the same reason as make_planar_latex's PDF_WRAPPER_CROPPED: a
# plain \pagecolor doesn't reliably survive the standalone class's bounding-box crop.
# Background and text color are both adjustable (see --bg-color/--text-color) --
# `fill`/`text` are node options, so the highlighted morphemes' own \textcolor still
# overrides `text` locally and stays the highlight color regardless of the base text
# color chosen.
EXAMPLE_WRAPPER = r"""\documentclass{standalone}
\usepackage{array}
\usepackage{tikz}
""" + GILL_SANS_FONT_SETUP + r"""
%(colordefs)s
\begin{document}
\begin{tikzpicture}
\node[fill=""" + BG_COLOR_NAME + r""", text=""" + TEXT_COLOR_NAME + r""", inner sep=2pt] {
%(body)s
};
\end{tikzpicture}
\end{document}
"""


def load_example(yaml_path):
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def all_morphemes(example):
    # An example is a sequence of `lines` (each rendered as one bracket-notation row
    # plus one gloss row); each line is a sequence of `chunks` (independent words,
    # space-separated -- e.g. a question particle and a subject NP sitting side by
    # side); each chunk is a sequence of `morphemes` (bound forms within one word,
    # hyphen-chained -- e.g. a verb's SM-TAM-root-FV). A chunk of one morpheme is just
    # a single bracketed word; a "morpheme" can itself be a multi-word phrase under one
    # position (its `text`/`gloss` just contain internal spaces, e.g. a subject NP like
    # "anyaní á mísala" glossed "2.baboon 2.ass 4.madness" under one Su position) --
    # that's not a separate case the renderer needs to know about, it falls out of
    # format_morpheme/format_gloss treating text/gloss as opaque strings.
    for line in example["lines"]:
        for chunk in line["chunks"]:
            for m in chunk["morphemes"]:
                yield m


def escape_latex(text):
    # Applied to free-text fields (translation, citation) before embedding them in
    # generated LaTeX -- these come from the YAML as plain prose, not LaTeX source, so
    # special characters need escaping rather than passing through raw. Found the hard
    # way: an unescaped "&" in a citation ("Downing & Mtenje 2017") broke compilation
    # with a cascading "Missing } inserted" error -- & is the table column-separator
    # character by default, active even inside a \parbox, not just inside a tabular.
    # (morpheme/gloss text isn't run through this -- those are short linguistic tokens
    # the examples so far never need any of these characters in.)
    replacements = [
        ("\\", r"\textbackslash{}"),  # must come first, or it double-escapes the rest
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def format_morpheme(morpheme, highlight_positions, color_name):
    positions_text = "/".join(str(p) for p in morpheme["positions"])
    piece = r"[%s]\textsubscript{%s}" % (morpheme["text"], positions_text)
    if any(p in highlight_positions for p in morpheme["positions"]):
        piece = r"\textcolor{%s}{%s}" % (color_name, piece)
    return piece


def format_gloss(text):
    # Leipzig Glossing Rules convention: grammatical glosses in small caps, lexical
    # glosses (root translations like "break", function-word glosses like "too") left
    # plain. Auto-detected from the gloss's own casing in the YAML -- a gloss written
    # in caps ("NEG", "10OM", "PRS-GO-JUST") is treated as grammatical; one written in
    # lowercase ("break", "too", "4.chairs") is left as-is. To force a specific gloss
    # either way, just write it in the corresponding case in the example YAML.
    #
    # Real \sc doesn't work here -- tested directly: plain Gill Sans has no small-caps
    # glyphs, so {\sc ...} silently falls back to the regular shape under fontspec
    # ("Font shape ... undefined ... using .../n instead"), which would print flat
    # lowercase text, not small caps. (make_planar_latex.py's planar table is fine --
    # it pairs Times New Roman with TeX Gyre Termes specifically for real small-cap
    # glyphs.) Faked here with full caps at the gloss line's own size, not reduced --
    # genuine small-cap glyphs are drawn close to lowercase x-height, so real small caps
    # read as roughly the same size as the surrounding text; a same-size substitute is
    # closer to that than an artificially shrunk one. The case contrast alone (full caps
    # vs. lowercase, e.g. NEG vs. break) carries the grammatical/lexical distinction.
    if text == text.upper():
        return text.upper()
    return text


def measure_widths_pt(fragments, colordefs=""):
    # Compiles a throwaway document that \settowidths each fragment and \typeout's the
    # result, then parses those printed widths back out -- used instead of a \newlength
    # register in the real document. Confirmed by direct testing (see git history/PR
    # notes around this function, or just re-run the isolated case): under the
    # `standalone` class, a box width read from a \newlength register -- even one set
    # with a plain \setlength, no \settowidth involved -- adds stray left-side padding
    # that an identical *literal* width doesn't. Reproduces with no tikz layer at all
    # (plain `\documentclass{standalone}`, a two-row tabular, \makebox[\reg]). So: do
    # the measuring here, in a disposable document, and bake the result into the real
    # one as a literal "12.345pt" string, never as a register.
    #
    # colordefs must be passed in and included here too -- fragments use \textcolor{...}
    # for highlighted morphemes, and an undefined color throws an error mid-measurement
    # that silently corrupts the \typeout log parsing below (found by direct testing:
    # simple uncolored content measured correctly, but the real verb/gloss lines came
    # back with a wildly wrong width until the color was defined here as well).
    doc = [
        r"\documentclass{article}",
        r"\usepackage{xcolor}",
        GILL_SANS_FONT_SETUP,
        colordefs,
        r"\newlength{\w}",
        r"\begin{document}",
    ]
    for i, (size, content) in enumerate(fragments):
        doc.append(r"\settowidth{\w}{%s %s}\typeout{PLANARWIDTH%d:\the\w}" % (size, content, i))
    doc.append(r"\end{document}")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "measure.tex")
        with open(path, "w") as f:
            f.write("\n".join(doc))
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-output-directory", tmpdir, path],
            capture_output=True, text=True,
        )
        widths = []
        for i in range(len(fragments)):
            match = re.search(r"PLANARWIDTH%d:([0-9.]+pt)" % i, result.stdout)
            if not match:
                raise RuntimeError("Couldn't measure width of fragment %d; xelatex output:\n%s" % (i, result.stdout))
            widths.append(match.group(1))
        return widths


def format_line(line, highlight_positions, color_name):
    # Chunks within a line are space-separated (independent words); morphemes within a
    # chunk are hyphen-chained (bound forms of one word). Returns (bracket_row,
    # gloss_row) -- optionally with `trailing_punct` (e.g. "?") appended to the bracket
    # row only, matching how sentence-final punctuation attaches to the last bracketed
    # word in the source, not to its gloss.
    bracket_row = " ".join(
        "-".join(format_morpheme(m, highlight_positions, color_name) for m in chunk["morphemes"])
        for chunk in line["chunks"]
    )
    gloss_row = " ".join(
        "-".join(format_gloss(m["gloss"]) for m in chunk["morphemes"])
        for chunk in line["chunks"]
    )
    bracket_row += line.get("trailing_punct", "")
    return bracket_row, gloss_row


def make_example_tex(example, highlight_positions, color_name, colordefs):
    rows = [format_line(line, highlight_positions, color_name) for line in example["lines"]]

    # Every line except the translation is set at its own natural width and never wraps.
    # The translation is the one line meant to wrap, like the source slide's -- but only
    # within whatever width the other lines already established, not some separately
    # guessed width, so it can't make the card wider than its own content already made it.
    width_candidates = []
    for bracket_row, gloss_row in rows:
        width_candidates.append((r"\Large", bracket_row))
        width_candidates.append((r"\large", gloss_row))
    card_width_pt = max(measure_widths_pt(width_candidates, colordefs), key=lambda w: float(w[:-2]))

    lines = [r"\begin{tabular}{@{}l@{}}"]
    for bracket_row, gloss_row in rows:
        lines.append(r"\Large " + bracket_row + r" \\[4pt]")
        lines.append(r"\large " + gloss_row + r" \\[12pt]")
    lines.append(
        r"\parbox[t]{%s}{\raggedright\Large ``%s'' (%s)} \\"
        % (card_width_pt, escape_latex(example["translation"]), escape_latex(example["citation"]))
    )
    lines.append(r"\end{tabular}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tsv_path", help="Path to a planar_tables/planar_<lang>.tsv file")
    parser.add_argument("example_yaml", help="Path to a NonCollaborative/examples/*.yaml file")
    parser.add_argument(
        "--color", default=DEFAULT_COLOR_HEX, help="Highlight color as a hex code, no # (default: %(default)s)"
    )
    parser.add_argument(
        "--positions",
        help="Comma-separated Position numbers to highlight (default: every position the example's morphemes use)",
    )
    parser.add_argument(
        "--bg-color", default=DEFAULT_BG_HEX,
        help="Example card background, hex no # (default: %(default)s)",
    )
    parser.add_argument(
        "--text-color", default=DEFAULT_TEXT_HEX,
        help="Example card text color, hex no # (default: %(default)s)",
    )
    parser.add_argument(
        "--no-highlight", action="store_true",
        help="No highlighting at all -- a plain example card and a plain (unhighlighted) table",
    )
    parser.add_argument(
        "--label",
        help="Suffix appended to output filenames (e.g. --label basic_black -> "
             "..._basic_black.pdf) -- without this, two runs of the same example with "
             "different styling (e.g. the default white card vs. --bg-color 000000) "
             "silently overwrite each other's output, since both would otherwise write "
             "to the identical filename",
    )
    parser.add_argument(
        "--tex-only", action="store_true", help="Skip PDF rendering, just write the .tex fragments"
    )
    args = parser.parse_args()

    df = mpl.load_planar_table(args.tsv_path)
    lang_id = df["Language_ID"].iloc[0]

    example = load_example(args.example_yaml)
    name = example["name"]
    file_label = "%s_%s" % (name, args.label) if args.label else name

    if args.no_highlight:
        highlight_positions = set()
    elif args.positions:
        highlight_positions = {int(p) for p in args.positions.split(",")}
    else:
        highlight_positions = {p for m in all_morphemes(example) for p in m["positions"]}

    colordefs = "\n".join([
        r"\definecolor{%s}{HTML}{%s}" % (COLOR_NAME, args.color),
        r"\definecolor{%s}{HTML}{%s}" % (BG_COLOR_NAME, args.bg_color),
        r"\definecolor{%s}{HTML}{%s}" % (TEXT_COLOR_NAME, args.text_color),
    ])
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # -- highlighted planar table (unaffected by --bg-color/--text-color, those apply to
    # the example card only; shows nothing highlighted when --no-highlight is passed,
    # same as if --positions matched nothing) --
    table_tex = mpl.make_reduced(df, highlight_positions, COLOR_NAME)
    table_tex_path = os.path.join(RESULTS_DIR, "%s_planar_table_%s_highlighted.tex" % (lang_id, file_label))
    with open(table_tex_path, "w") as f:
        f.write(table_tex)
    print("Wrote %s" % table_tex_path)

    if not args.tex_only:
        table_pdf_path = os.path.join(RESULTS_DIR, "%s_planar_table_%s_highlighted.pdf" % (lang_id, file_label))
        if mpl.render_pdf(table_tex, "", table_pdf_path, mpl.PDF_WRAPPER_CROPPED, colordefs):
            print("Wrote %s" % table_pdf_path)

    # -- example card: one combined card per example --
    example_tex = make_example_tex(example, highlight_positions, COLOR_NAME, colordefs)
    example_tex_path = os.path.join(RESULTS_DIR, "%s_example_%s.tex" % (lang_id, file_label))
    with open(example_tex_path, "w") as f:
        f.write(example_tex)
    print("Wrote %s" % example_tex_path)

    if not args.tex_only:
        example_pdf_path = os.path.join(RESULTS_DIR, "%s_example_%s.pdf" % (lang_id, file_label))
        if mpl.render_pdf(example_tex, "", example_pdf_path, EXAMPLE_WRAPPER, colordefs):
            print("Wrote %s" % example_pdf_path)


if __name__ == "__main__":
    main()
