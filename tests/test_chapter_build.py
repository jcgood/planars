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
from chapters.data import ChapterDataError, chapter_data, commit_of, split_examples
from coding import drive_door, file_door, state_files
from laminar import planars_language as pl

needs_english = pytest.mark.skipif(not pl.planar_file("stan1293").exists(),
                                   reason="coded_data/ (planars-data) is not cloned")
needs_latex = pytest.mark.skipif(shutil.which("pdflatex") is None, reason="no pdflatex")

PV = re.compile(r"\\pv\{([^}]*)\}")
VOLUME = "title: A test volume\nvenue: book\nparts: [intro, stan1293]\n"


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
    built, stubs, _said, _values = build.part_files(build.INTRO)
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


@needs_english
def test_every_english_example_is_printed_plain(english):
    fragments = build.language_fragments(english)
    text = "".join(t for name, t in fragments.items() if name.startswith("examples_"))
    expected = sum(len(split_examples(r, False)[0])
                   for _i, r in english.tables["examples"].iterrows())
    assert text.count(r"\planarsplainex{") == expected and r"\planarsex{" not in text


def test_a_glossed_row_pairs_each_example_with_its_gloss_or_with_neither():
    row = {"Example": "a b; c", "Gloss": "A B; C", "Translation": "ab; c;"}
    assert split_examples(row, True) == ([{"form": "a b", "gloss": "A B", "translation": "ab"},
                                          {"form": "c", "gloss": "C", "translation": "c"}], True)
    items, paired = split_examples({**row, "Gloss": "A B"}, True)
    assert not paired and all(e["gloss"] == "" for e in items)


def test_an_example_uses_its_style_macro_and_falls_back_to_plain():
    assert tex.example("a_b", "A", "ab", "p. 3", True) == r"\planarsex{a\_b}{A}{ab}{p. 3}"
    assert tex.example("a_b", "", "", "", True) == r"\planarsplainex{a\_b}{}"
    assert tex.example("a b", "", "", "", False) == r"\planarsplainex{a b}{}"


def test_every_venue_file_defines_both_example_macros():
    assert "book" in tex.venues()
    for venue in tex.venues():
        sty = tex.venue_sty(venue)
        assert r"\newcommand{\planarsex}[4]" in sty and r"\newcommand{\planarsplainex}[2]" in sty
    with pytest.raises(ValueError, match="chapters/venues"):
        tex.venue_sty("nosuchvenue")


def test_the_volume_must_name_a_venue():
    with drive_door.running("t", may_write=True):
        file_door.write_paper(file_door.paper_stub(build.VOLUME),
                              "title: T\nvenue: nosuchvenue\nparts: [intro]\n")
    with pytest.raises(ChapterDataError, match="venue"):
        build.read_volume()


def test_the_volume_must_name_parts_the_build_knows():
    with drive_door.running("t", may_write=True):
        file_door.write_paper(file_door.paper_stub(build.VOLUME),
                              "title: T\nvenue: book\nparts: [intro, nosuchlang]\n")
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


def test_value_changes_says_each_span_once_and_counts_the_analysis():
    base = "L.span.c.general.strict_complete_span"
    old = {f"{base}.left": "9", f"{base}.right": "20", f"{base}.range": "9--20",
           "L.analysis.types.all.families": "4", "L.data.commit": "a", "L.planar.positions": "38"}
    new = {f"{base}.left": "9", f"{base}.right": "21", f"{base}.range": "9--21",
           "L.analysis.types.all.families": "5", "L.data.commit": "b", "L.planar.positions": "39"}
    lines, changed = build.value_changes(old, new, "L")
    assert lines == ["  L.planar.positions: 38 -> 39",
                     "  c general, strict complete span: 9--20 -> 9--21",
                     "  L.analysis.types.all: 1 values changed"]
    assert "L.data.commit" not in changed


def _prose(part, name, text):
    folder = state_files.PAPERS_DIR / part / "prose"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text, encoding="utf-8")


def test_claims_that_no_longer_hold_are_listed_with_file_and_line():
    _prose("intro", "argument.tex",
           "% \\claim{L.x}{1} in a comment is not a claim\n"
           "It holds: \\claim{L.x}{1}.\n"
           "It fails: \\claim{L.y}{NP\\{S\\}}, \\claim{L.gone}{2} and \\claim{M.z}{3}.\n")
    lines = build.broken_claims({"L.x": 1, "L.y": "v:x"}, ["L"], ["intro"])
    assert lines == ["Claims that no longer hold:",
                     "  .papers/intro/prose/argument.tex:3: \\claim{L.y} says NP\\{S\\}, the data now say v:x",
                     "  .papers/intro/prose/argument.tex:3: \\claim{L.gone} names no value"]


@needs_english
def test_a_chapter_is_pinned_and_moving_the_pin_reports_by_cause(capsys):
    old = commit_of("HEAD~3")
    _run("--lang", "stan1293", "--version", old, "--apply")
    lock = build.read_lock("stan1293")
    assert lock["planars_data"] == old
    with pytest.raises(SystemExit, match="--update"):
        _run("--lang", "stan1293", "--version", "HEAD")
    capsys.readouterr()
    _run("--lang", "stan1293", "--apply")
    out = capsys.readouterr().out
    assert "(its pin)" in out and "Changes from the code" in out
    _run("--lang", "stan1293", "--update")
    out = capsys.readouterr().out
    assert "Changes from the code" in out and "Changes from the annotation" in out
    assert build.read_lock("stan1293")["planars_data"] == old, "a dry run moved the pin"


def test_the_check_with_no_volume_says_so(capsys):
    _run("--check", "--apply")
    assert "No chapters yet" in capsys.readouterr().out
    assert not state_files.PAPERS_DIR.exists()


def test_the_check_takes_only_lang_and_apply():
    with pytest.raises(SystemExit, match="only --lang"):
        _run("--check", "--update")


def test_every_value_group_says_whether_it_puts_a_chapter_behind():
    with pytest.raises(ChapterDataError, match="VALUE_GROUPS"):
        build._group("L.newgroup.x")


def test_the_check_leaves_out_an_analysis_not_drawn_on_both_sides():
    class Drawn:
        def __init__(self, *bundles):
            self.bundles = dict.fromkeys(bundles)
    L = "stan1293"
    values = {f"{L}.analysis.types.all.families": "4", f"{L}.analysis.classes.all.families": "2",
              f"{L}.planar.positions": "38"}
    assert build._comparable(values, L, [Drawn(f"{L}_types_all", f"{L}_classes_all"),
                                         Drawn(f"{L}_types_all")]) \
        == {f"{L}.analysis.types.all.families": "4", f"{L}.planar.positions": "38"}


@needs_english
def test_the_check_files_a_chapter_behind_and_closes_it_when_caught_up(capsys, github):
    _run("--lang", "stan1293", "--version", "HEAD", "--apply")
    volume = state_files.PAPERS_DIR / "volume.yaml"
    volume.write_text(VOLUME, encoding="utf-8")
    values = state_files.PAPERS_DIR / "stan1293" / "values.tex"
    text = values.read_text(encoding="utf-8")
    name = next(m for m in re.findall(r"\\pvset\{([^}]*\.left)\}", text))
    stale = re.sub(r"(\\pvset\{" + re.escape(name) + r"\}\{)[^}]*", r"\g<1>1--99", text)
    values.write_text(stale, encoding="utf-8")
    capsys.readouterr()
    _run("--check")
    assert "Dry run" in capsys.readouterr().out and not github.issues
    _run("--check", "--apply")
    [issue] = github.issues
    assert issue["title"] == build.check_title("stan1293") and issue["labels"] == [build.CHECK_LABEL]
    assert "1 span" in issue["body"] and "--lang stan1293 --update" in issue["body"]
    assert re.search(r"- `\.papers/stan1293/prose/class_\w+\.tex`\n", issue["body"])
    assert "1--99" not in issue["body"] and name not in issue["body"], "annotation in a public issue"
    _run("--check", "--apply")
    assert len(github.issues) == 1 and github.calls_of("edit"), "a second run filed again"
    _run("--lang", "stan1293", "--apply")
    _run("--check", "--apply")
    assert github.issue(issue["number"])["state"] == "CLOSED"


def _compile(folder, file="main.tex"):
    stem = file.removesuffix(".tex")
    run = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", file],
                         cwd=folder, capture_output=True, text=True)
    log = (folder / f"{stem}.log").read_text(encoding="utf-8", errors="replace")
    assert run.returncode == 0, log[-3000:]
    assert "No value named" not in log
    assert not re.search(rf"No file (?!{re.escape(stem)}\.)", log), \
        "an \\input or \\include found no file"
    return log


@needs_latex
@needs_english
def test_the_volume_compiles(english):
    _run("--intro", "--apply")
    volume = state_files.PAPERS_DIR / "volume.yaml"
    volume.write_text(VOLUME, encoding="utf-8")
    _run("--apply")
    total = english.values["stan1293.planar.positions"]
    _prose("intro", "argument.tex", f"English has \\claim{{stan1293.planar.positions}}{{{total}}} "
                                    f"positions, not \\claim{{stan1293.planar.positions}}{{{total + 1}}}.\n"
                                    + tex.example("ema=ja kweti", "1SG=ERG go.PST", "I went", "p. 3",
                                                  True) + "\n")
    for chapter in ("intro", "stan1293"):
        _compile(state_files.PAPERS_DIR, f"{chapter}.tex")
    log = _compile(state_files.PAPERS_DIR)
    # TeX breaks log lines at 79 characters.
    assert log.replace("\n", "").count("Claim stan1293.planar.positions no longer holds") == 1
