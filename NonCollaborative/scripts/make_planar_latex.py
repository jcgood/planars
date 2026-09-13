"""Generate a LaTeX planar structure table from a planar_tables/*.tsv file.

Two variants:

- "exact": reproduces the manuscript's own table (see ChichewaWordhood.tex,
  \\tref{ChichPlan}, lines 420-452) -- macro-based position labels (\\QM,
  \\Su, ...; the manuscript already has \\def's for these, so this output is
  meant to be pasted in as a straight replacement for the existing
  \\begin{table}...\\end{table} block, not to redefine the macros itself),
  small-caps Elements column, a Description column, and a rotated
  "Orthographic word" side-label bracketing the positions that fall inside
  the orthographic word, set off with \\hdashline rules (arydshln).

- "reduced": a narrower table for slides -- Position / Type / Elements only,
  small-caps headings and small-caps Elements values, plain text position
  labels (no macros, no orthographic-word decoration, no caption), so it
  doesn't depend on anything from the manuscript's preamble. Its PDF is
  cropped to the table's own bounding box (via the `standalone` class)
  rather than sitting on a full page, so it can be pasted straight into a
  slide without a border to crop out first.

Also renders each variant to a standalone PDF (white page background, not the
transparent default) by wrapping the fragment in a throwaway document with
the packages/macros it needs -- this is a preview render, not a claim to
reproduce the manuscript's exact class. Needs xelatex on PATH (required for
fontspec/Times New Roman, matching the manuscript's own font setup); pass
--tex-only to skip this and just write the .tex fragments.

Usage:
    python make_planar_latex.py planar_nyan1308.tsv
    python make_planar_latex.py planar_nyan1308.tsv --variant exact
    python make_planar_latex.py planar_nyan1308.tsv --variant reduced
    python make_planar_latex.py planar_nyan1308.tsv --tex-only

With no --variant, both are written. Output goes to NonCollaborative/results/
as <lang>_planar_table_<variant>.tex (+ .pdf), matching where the other
generated charts in this project land (see results/visualizations.md).
"""

import argparse
import os
import shutil
import subprocess
import tempfile

import pandas as pd

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

# Font setup lifted verbatim from ChichewaWordhood.tex:15-20 -- Times New Roman as the
# main font, with small caps (\sc / {\sc ...}) routed through TeX Gyre Termes's real
# small-cap glyphs rather than a synthetically-scaled substitute. Requires xelatex (or
# lualatex), not pdflatex -- fontspec + a system font name doesn't work under pdflatex.
FONT_SETUP = r"""\usepackage{fontspec}
\setmainfont[
  Ligatures=TeX,
  SmallCapsFont={TeX Gyre Termes},
  SmallCapsFeatures={Letters=SmallCaps},
]{Times New Roman}"""

# Preview-only wrapper for standalone PDF rendering. \Hline here is a plain
# thick rule standing in for the manuscript's own \Hline (defined in its
# langsci document class, not reproduced here) -- fine for previewing the
# table's layout, not a claim to match the manuscript's exact typesetting.
PDF_WRAPPER = r"""\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage{array}
\usepackage{arydshln}
\usepackage{multirow}
\usepackage{graphicx}
\usepackage{xspace}
\usepackage{xcolor}
""" + FONT_SETUP + r"""
\pagecolor{white}
\def\Hline{\noalign{\hrule height 1pt}}
%(macros)s
%(colordefs)s
\pagestyle{empty}
\begin{document}
%(body)s
\end{document}
"""

# Cropped preview wrapper for "reduced" -- the standalone class sizes the page to
# the content's own bounding box instead of a full page, so the PDF can be pasted
# straight into a slide with no margin to crop. \pagecolor doesn't reliably survive
# that bounding-box crop (its fill sits outside what standalone measures as content,
# so it can get cropped away with it -- confirmed empirically: pdftoppm's flattened
# render looked white, but pdftocairo -transp showed alpha 0, i.e. actually
# transparent). Fix: put the white fill *inside* the measured content instead, as a
# filled tikz node wrapping the table, so it's part of what standalone crops to.
PDF_WRAPPER_CROPPED = r"""\documentclass{standalone}
\usepackage{array}
\usepackage{tikz}
""" + FONT_SETUP + r"""
%(colordefs)s
\begin{document}
\begin{tikzpicture}
\node[fill=white, inner sep=4pt] {
%(body)s
};
\end{tikzpicture}
\end{document}
"""

# Positions that fall inside the orthographic word, per the dashed lines in
# ChichewaWordhood.tex's \tref{ChichPlan} (Position \Neg through Position
# \En). Specific to nyan1308's table -- not stored in the TSV itself since
# it's presentation, not data, and there's currently only ever one language
# this script runs on. If a second language table needs this, promote it to
# a per-language lookup (or a TSV column) instead of a second hardcoded pair.
ORTHOGRAPHIC_WORD_RANGE = (5, 19)


def load_planar_table(tsv_path):
    df = pd.read_csv(tsv_path, sep="\t")
    return df.sort_values("Position")


def row_line(cells):
    return " & ".join(cells) + r" \\"


def make_exact(df, lang_id):
    word_start, word_end = ORTHOGRAPHIC_WORD_RANGE
    word_row_count = word_end - word_start + 1

    lines = [
        r"\begin{table}",
        r"\centering",
        r"\begin{tabular}{lll>{\sc}ll}",
        r"\Hline",
        row_line(["", r"{\sc position}", r"{\sc type}", r"{\sc elements}", r"{\sc description}"]),
        r"\Hline",
    ]

    for _, row in df.iterrows():
        pos = row["Position"]
        first_cell = "&"
        if pos == word_start:
            first_cell = (
                r"\multirow{%d}{*}{\rotatebox[origin=c]{90}{\em Orthographic word}} &"
                % word_row_count
            )
        lines.append(
            row_line(
                [
                    first_cell + r"\%s" % row["Position_Label"],
                    row["Position_Type"],
                    row["Elements"],
                    row["Description"],
                ]
            )
        )
        if pos in (word_start - 1, word_end):
            lines.append(r"\hdashline")

    lines += [
        r"\Hline",
        r"\end{tabular}",
        r"\caption{Planar structure for %s \label{ChichPlan}}" % lang_id,
        r"\end{table}",
    ]
    return "\n".join(lines) + "\n"


def make_macro_defs(df):
    # Derived from the TSV's Position_Label/Position columns rather than a second
    # hardcoded copy of the manuscript's \def list -- so this can't drift out of
    # sync with planar_<lang>.tsv the way a duplicate literal list could.
    return "\n".join(
        r"\def\%s{%d\xspace}" % (row["Position_Label"], int(row["Position"]))
        for _, row in df.iterrows()
    )


def render_pdf(tex_fragment, macros, out_pdf_path, wrapper_template=PDF_WRAPPER, colordefs=""):
    wrapper = wrapper_template % {"macros": macros, "body": tex_fragment, "colordefs": colordefs}
    with tempfile.TemporaryDirectory() as tmpdir:
        wrapper_path = os.path.join(tmpdir, "wrapper.tex")
        with open(wrapper_path, "w") as f:
            f.write(wrapper)
        try:
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
                 "-output-directory", tmpdir, wrapper_path],
                capture_output=True, text=True,
            )
        except FileNotFoundError:
            print("xelatex not found on PATH -- skipping PDF render for %s" % out_pdf_path)
            return False
        if result.returncode != 0:
            print("xelatex failed for %s; last lines of output:" % out_pdf_path)
            print("\n".join(result.stdout.splitlines()[-20:]))
            return False
        shutil.copy(os.path.join(tmpdir, "wrapper.pdf"), out_pdf_path)
        return True


def make_reduced(df, highlight_positions=None, highlight_color_name=None):
    # No \begin{table}/\caption -- this is meant to be pasted straight into a slide as
    # a cropped image, not to float in a document. Elements column is small-caps via
    # the >{\sc} column-type prefix (auto-applies to every body cell in that column);
    # the header row is wrapped in {\sc ...} by hand since the column-type prefix
    # doesn't reach the Position/Type header cells. Position is the plain integer, not
    # the Position_Label abbreviation (QM, PrS, NegT, 2P, ...) -- those mix upper- and
    # lower-case letters within a single label, which reads as genuinely mixed case
    # sitting next to a column that's actually small caps, not a second small-caps style.
    #
    # highlight_positions/highlight_color_name: optionally recolor the rows for those
    # Position numbers (see highlight_planar_example.py, which ties this to specific
    # morphemes in a glossed example) -- e.g. {\color{name}...} around each cell.
    # Defaults to None/None, i.e. every row plain black, same as before this was added.
    highlight_positions = set(highlight_positions or ())
    lines = [
        r"\begin{tabular}{ll>{\sc}l}",
        r"\hline",
        # Lowercase source text -- \sc only shrinks lowercase letters to small-cap
        # glyphs; a capitalized first letter ("Position") stays a full-size regular
        # capital, giving a mixed big-cap-plus-small-caps look instead of true small caps.
        row_line([r"{\sc position}", r"{\sc type}", r"{\sc elements}"]),
        r"\hline",
    ]
    for _, row in df.iterrows():
        pos = int(row["Position"])
        cells = [str(pos), row["Position_Type"], row["Elements"]]
        if pos in highlight_positions:
            cells = [r"\textcolor{%s}{%s}" % (highlight_color_name, c) for c in cells]
        lines.append(row_line(cells))
    lines += [
        r"\hline",
        r"\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tsv_path", help="Path to a planar_tables/planar_<lang>.tsv file")
    parser.add_argument(
        "--variant", choices=["exact", "reduced"], help="Generate only this variant (default: both)"
    )
    parser.add_argument(
        "--tex-only", action="store_true", help="Skip PDF rendering, just write the .tex fragments"
    )
    args = parser.parse_args()

    df = load_planar_table(args.tsv_path)
    lang_id = df["Language_ID"].iloc[0]
    macros = make_macro_defs(df)

    variants = [args.variant] if args.variant else ["exact", "reduced"]
    os.makedirs(RESULTS_DIR, exist_ok=True)

    for variant in variants:
        tex = make_exact(df, lang_id) if variant == "exact" else make_reduced(df)
        tex_path = os.path.join(RESULTS_DIR, "%s_planar_table_%s.tex" % (lang_id, variant))
        with open(tex_path, "w") as f:
            f.write(tex)
        print("Wrote %s" % tex_path)

        if not args.tex_only:
            pdf_path = os.path.join(RESULTS_DIR, "%s_planar_table_%s.pdf" % (lang_id, variant))
            wrapper = PDF_WRAPPER if variant == "exact" else PDF_WRAPPER_CROPPED
            if render_pdf(tex, macros, pdf_path, wrapper):
                print("Wrote %s" % pdf_path)


if __name__ == "__main__":
    main()
