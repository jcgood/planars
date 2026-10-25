"""The chapters' build (chapters/tex.py, chapters/build.py, the templates):
escaping, every cited value defined, the outline and its prose stubs, the
volume, rebuilds that change nothing, and the volume compiling under plain
LaTeX. Builds go into the temporary .papers/ that tests/conftest.py points
the door at."""

import argparse
import re
import shutil
import subprocess
import unicodedata

import pytest

from chapters import build, tex
from chapters.data import ChapterDataError, chapter_data
from coding import drive_door, file_door, state_files
from laminar import planars_language as pl

needs_english = pytest.mark.skipif(not pl.planar_file("stan1293").exists(),
                                   reason="coded_data/ (planars-data) is not cloned")
needs_latex = pytest.mark.skipif(shutil.which("pdflatex") is None, reason="no pdflatex")

PV = re.compile(r"\\pv\{([^}]*)\}")


@pytest.fixture(scope="module")
def english():
    return chapter_data("stan1293")


def _run(*argv):
    """build-chapters as the dispatcher runs it, inside the doors."""
    args = build.build_parser().parse_args(list(argv))
    with drive_door.running("build-chapters", args):
        build.main(args)


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


def test_comment_wraps_plain_text_as_comment_lines():
    out = tex.comment("word " * 30)
    assert all(line.startswith("% ") and len(line) <= 72 for line in out.split("\n"))


def test_intro_has_every_class_and_no_bare_math_symbols():
    fragments = build.intro_fragments()
    assert set(fragments) == {"terms.tex"} | {f"class_{c}.tex" for c in build._class_entries()}
    bare = {ch for text in fragments.values() for ch in text
            if unicodedata.category(ch) == "Sm" and ord(ch) > 127}
    assert not bare, (f"The schemas use math symbols chapters.tex doesn't escape: {sorted(bare)}; "
                      f"add them to tex._SPECIALS.")


def test_the_intro_outline_places_every_fragment_and_has_a_stub_per_slot():
    built, stubs, _said = build.part_files(build.INTRO)
    outline = built["intro/chapter.tex"]
    for rel in built:
        if rel.startswith("intro/fragments/"):
            assert f"\\input{{{rel[:-4]}}}" in outline
    for rel in stubs:
        assert f"\\input{{{rel[:-4]}}}" in outline
        assert build.SLOT_MARK in stubs[rel]
    domain_sections = re.findall(r"\\section\{(\w+) diagnostics\}", outline)
    assert domain_sections and len(domain_sections) == len(set(domain_sections))


def test_an_outline_section_with_a_slot_needs_its_instructions(monkeypatch):
    monkeypatch.setattr(build, "_outline", lambda kind: [{"heading": "X", "slot": "x"}])
    with pytest.raises(ChapterDataError, match="who"):
        build.outline_items(build.INTRO, [])


@needs_english
def test_every_value_a_fragment_cites_exists(english):
    cited = {m for text in build.language_fragments(english).values() for m in PV.findall(text)}
    assert cited and not cited - set(english.values)


@needs_english
def test_the_language_wide_span_table_has_every_span(english):
    text = build.language_fragments(english)["spans_table.tex"]
    rows = {m for m in PV.findall(text) if m.endswith(".size")}
    assert len(rows) == english.values["stan1293.spans.total"]


def test_the_volume_must_name_parts_the_build_knows():
    with drive_door.running("t", may_write=True):
        file_door.write_paper(file_door.paper_stub(build.VOLUME),
                              "title: T\nparts: [intro, nosuchlang]\n")
    with pytest.raises(ChapterDataError, match="nosuchlang"):
        build.read_volume()


def test_the_intro_builds_once_and_a_rebuild_changes_nothing(capsys):
    _run("--intro", "--apply")
    papers = state_files.PAPERS_DIR
    assert (papers / "volume.yaml").exists() and (papers / "intro" / "chapter.tex").exists()
    capsys.readouterr()
    _run("--intro", "--apply")
    out = capsys.readouterr().out
    assert "Nothing to change." in out and "slots written" in out


def test_written_prose_is_kept_and_a_retired_slot_or_fragment_is_handled(capsys):
    _run("--intro", "--apply")
    papers = state_files.PAPERS_DIR
    written = papers / "intro" / "prose" / "argument.tex"
    written.write_text("My argument.\n", encoding="utf-8")
    (papers / "intro" / "prose" / "retired.tex").write_text("Old text.\n", encoding="utf-8")
    (papers / "intro" / "fragments" / "class_retired.tex").write_text("x", encoding="utf-8")
    capsys.readouterr()
    _run("--intro", "--apply")
    out = capsys.readouterr().out
    assert written.read_text(encoding="utf-8") == "My argument.\n"
    assert "deleted intro/fragments/class_retired.tex (no longer made)" in out
    assert "intro/prose/retired.tex: its section is no longer in the outline" in out
    assert (papers / "intro" / "prose" / "retired.tex").exists()
    assert "Prose: 1 of" in out


def test_a_dry_run_writes_nothing(capsys):
    _run("--intro")
    assert not state_files.PAPERS_DIR.exists()
    assert "Dry run" in capsys.readouterr().out


def test_version_needs_a_language():
    with pytest.raises(SystemExit, match="--lang"):
        _run("--version", "HEAD")


def _compile(folder):
    run = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                         cwd=folder, capture_output=True, text=True)
    log = (folder / "main.log").read_text(encoding="utf-8", errors="replace")
    assert run.returncode == 0, log[-3000:]
    assert "No value named" not in log
    assert not re.search(r"No file (?!main\.)", log), "an \\input or \\include found no file"


@needs_latex
@needs_english
def test_the_volume_compiles():
    _run("--intro", "--apply")
    volume = state_files.PAPERS_DIR / "volume.yaml"
    volume.write_text("title: A test volume\nparts: [intro, stan1293]\n", encoding="utf-8")
    _run("--apply")
    _compile(state_files.PAPERS_DIR)
