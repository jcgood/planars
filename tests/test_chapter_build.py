"""The chapters' fragments (chapters/tex.py, chapters/build.py, the
templates): escaping, every cited value defined, rebuilds that change
nothing, and the fragments compiling under plain LaTeX."""

import re
import shutil
import subprocess
import unicodedata

import pytest

from chapters import build, tex
from chapters.data import chapter_data
from laminar import planars_language as pl

needs_english = pytest.mark.skipif(not pl.planar_file("stan1293").exists(),
                                   reason="coded_data/ (planars-data) is not cloned")
needs_latex = pytest.mark.skipif(shutil.which("pdflatex") is None, reason="no pdflatex")

PV = re.compile(r"\\pv\{([^}]*)\}")


@pytest.fixture(scope="module")
def english():
    return chapter_data("stan1293")


def test_escape_makes_specials_literal():
    assert tex.escape("NP{S,A,P} 50% a_b #1 $ & ~ ^ \\ <x>") == (
        r"NP\{S,A,P\} 50\% a\_b \#1 \$ \& \textasciitilde{} \textasciicircum{} "
        r"\textbackslash{} \textless{}x\textgreater{}")


def test_template_output_is_escaped_unless_tex():
    env = tex.environment()
    assert env.from_string(r"\VAR{x}").render(x="a_b") == r"a\_b"
    assert env.from_string(r"\VAR{pv('k.a_b')}").render() == r"\pv{k.a_b}"
    assert env.from_string(r"\VAR{x|name}").render(x="v:obj_R") == \
        r"v:\allowbreak{}obj\_\allowbreak{}R"


def test_a_value_name_latex_cannot_take_fails():
    with pytest.raises(ValueError):
        tex.pv("stan1293.span{x}")
    with pytest.raises(ValueError):
        tex.values_tex({"a b": 1}, "")


def test_values_tex():
    assert tex.values_tex({"b.x": 0.25, "a.y": "v:obj_R"}, "% h\n") == (
        "% h\n\\pvset{a.y}{v:obj\\_R}\n\\pvset{b.x}{0.25}\n")


def test_lines_keeps_indented_lines():
    out = tex.lines("Five categories:\n  fillable: y\n  left: n")
    assert out == "Five categories:\n\\newline \\hspace*{1em}fillable: y\n\\newline \\hspace*{1em}left: n"


def test_intro_has_every_class_and_no_bare_math_symbols():
    fragments = build.intro_fragments()
    assert set(fragments) == {"terms.tex"} | {f"class_{c}.tex" for c in build._class_entries()}
    bare = {ch for text in fragments.values() for ch in text
            if unicodedata.category(ch) == "Sm" and ord(ch) > 127}
    assert not bare, (f"The schemas use math symbols chapters.tex doesn't escape: {sorted(bare)}; "
                      f"add them to tex._SPECIALS.")


@needs_english
def test_every_value_a_fragment_cites_exists(english):
    files = build.language_files(english)
    cited = {m for name, text in files.items() if name.startswith("fragments/")
             for m in PV.findall(text)}
    assert cited and not cited - set(english.values)


@needs_english
def test_a_rebuild_changes_nothing_and_drops_retired_fragments(english, tmp_path):
    files = build.language_files(english)
    assert build.write(tmp_path, files, apply=False) and not (tmp_path / "values.tex").exists()
    assert len(build.write(tmp_path, files, apply=True)) == len(files)
    assert build.write(tmp_path, files, apply=True) == []
    (tmp_path / "fragments" / "class_retired.tex").write_text("x", encoding="utf-8")
    assert build.write(tmp_path, files, apply=True) == [
        "deleted fragments/class_retired.tex (no longer made)"]


def test_a_language_chapter_may_not_go_in_the_public_repository():
    with pytest.raises(SystemExit, match="public planars repository"):
        build._check_out(build.REPO / "docs" / "chapter")


def _compile(folder, files):
    for rel, text in files.items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(text, encoding="utf-8")
    body = "\n".join(rf"\input{{{rel[:-4]}}}" for rel in sorted(files) if rel.startswith("fragments/"))
    values = r"\input{values}" if "values.tex" in files else ""
    (folder / "main.tex").write_text(
        "\\documentclass{book}\n\\usepackage[T1]{fontenc}\n\\usepackage{planarschapter}\n"
        f"\\begin{{document}}\n{values}\n{body}\n\\end{{document}}\n", encoding="utf-8")
    run = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                         cwd=folder, capture_output=True, text=True)
    log = (folder / "main.log").read_text(encoding="utf-8", errors="replace")
    assert run.returncode == 0, log[-3000:]
    assert "No value named" not in log


@needs_latex
def test_the_intro_compiles(tmp_path):
    _compile(tmp_path, build.intro_files())


@needs_latex
@needs_english
def test_the_english_chapter_compiles(english, tmp_path):
    _compile(tmp_path, build.language_files(english))
