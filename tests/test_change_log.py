"""Tests for unit 17 (docs/change-log-design.md): the logged files and the
check (coding/source_log.py), log-change (coding/log_change.py), the
measured effects (coding/change_effects.py) and the versions read from the
log (coding/versions.py).

The files are a private copy of the frozen data (its change logs carry the
baseline lines), and the schemas' log is in tmp_path (conftest).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coding import change_effects, drive_door, file_door, integrity_check, source_log, versions
from coding.change_effects import Effects
from fake_drive import use_frozen_coded_data

LANG = "stan1293"


@pytest.fixture()
def coded(monkeypatch, tmp_path) -> Path:
    return use_frozen_coded_data(monkeypatch, tmp_path)


@pytest.fixture()
def schemas(monkeypatch, tmp_path) -> Path:
    """A copy of schemas/ with its baseline lines, standing in for the real one."""
    import shutil
    folder = tmp_path / "schemas"
    shutil.copytree(source_log.SCHEMAS_DIR, folder,
                    ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(source_log, "SCHEMAS_DIR", folder)
    monkeypatch.setattr(source_log, "PROJECT_LOG", folder / "changes.tsv")
    monkeypatch.setattr(source_log, "SCHEMA_ARCHIVE", folder / "archive")
    (folder / "changes.tsv").unlink(missing_ok=True)
    source_log.append_project_lines([
        source_log.line(s, what="baseline", by="test", why="start", change="baseline", layer="",
                        mark=file_door.fingerprint(s.path.read_bytes()))
        for s in source_log.sources([source_log.SCHEMAS])])
    # In git, as the real schemas are: where a schema's last logged version is found.
    for step in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "start"]):
        subprocess.run(["git", "-C", str(folder), "-c", "user.email=t@t", "-c", "user.name=t",
                        *step], check=True, capture_output=True)
    return folder


def _log_change(*argv: str):
    from coding import log_change
    args = log_change.build_parser().parse_args(list(argv))
    with drive_door.running("log-change", args):
        log_change.main(args)


# ---------------------------------------------------------------------------
# The file list and the rule
# ---------------------------------------------------------------------------

def test_every_schema_file_is_logged_or_exempt_with_a_reason():
    assert source_log.unplaced() == []
    assert not set(source_log.SCHEMA_SOURCES) & set(source_log.NOT_LOGGED)
    assert all(reason.strip() for reason in
               [*source_log.SCHEMA_SOURCES.values(), *source_log.NOT_LOGGED.values()])


def test_a_new_schema_file_fails_until_it_is_placed(schemas):
    (schemas / "new.yaml").write_text("x: 1\n", encoding="utf-8")
    assert source_log.unplaced() == ["new.yaml"]
    assert any("new.yaml" in p for p in integrity_check.changes_problems([source_log.SCHEMAS]))


def test_an_edit_is_unlogged_until_its_line_is_written(coded, schemas):
    assert source_log.unlogged() == []
    planar = file_door.planar(LANG).path
    planar.write_text(planar.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    (schemas / "terms.yaml").write_text("changed: true\n", encoding="utf-8")
    found = {(u.source.stream, u.source.name) for u in source_log.unlogged()}
    assert found == {(LANG, f"lang_setup/planar_{LANG}.tsv"), ("schemas", "terms.yaml")}
    problems = integrity_check.changes_problems()
    assert any("log-change --lang stan1293" in p for p in problems)
    assert any("log-change --change" in p for p in problems)


def test_check_changes_exits_1_naming_the_command(coded, schemas, capsys):
    (schemas / "terms.yaml").write_text("changed: true\n", encoding="utf-8")
    args = integrity_check.build_parser().parse_args(["--check-changes", "--schemas"])
    with pytest.raises(SystemExit) as exc:
        integrity_check.main(args)
    assert exc.value.code == 1
    assert "python -m coding log-change --change CLASS" in capsys.readouterr().out


def test_the_staged_check_reads_the_commit_not_the_working_copy(tmp_path, monkeypatch):
    """A staged edit with no staged line is refused even when the working
    copy's log has the line; staging the log too lets it through."""
    repo = tmp_path / "repo"
    folder = repo / "schemas"
    folder.mkdir(parents=True)
    for name in source_log.SCHEMA_SOURCES:
        (folder / name).write_text(f"{name}: 1\n", encoding="utf-8")
    monkeypatch.setattr(source_log, "SCHEMAS_DIR", folder)
    monkeypatch.setattr(source_log, "PROJECT_LOG", folder / "changes.tsv")
    source_log.append_project_lines([
        source_log.line(s, what="baseline", by="t", why="t", change="baseline", layer="",
                        mark=file_door.fingerprint(s.path.read_bytes()))
        for s in source_log.sources([source_log.SCHEMAS])])

    def git(*a):
        subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)

    git("init", "-q")
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "start")
    terms = folder / "terms.yaml"
    terms.write_text("terms: 2\n", encoding="utf-8")
    source_log.append_project_lines([source_log.line(
        source_log.schema_source("terms.yaml"), what="1 line(s) changed", by="t", why="t",
        change="change", layer="taxonomy", answers="0",
        mark=file_door.fingerprint(terms.read_bytes()))])
    git("add", "schemas/terms.yaml")
    assert [u.source.name for u in source_log.unlogged(staged_in=repo)] == ["terms.yaml"]
    git("add", "schemas/changes.tsv")
    assert source_log.unlogged(staged_in=repo) == []


# ---------------------------------------------------------------------------
# log-change
# ---------------------------------------------------------------------------

def test_log_change_with_nothing_edited_writes_nothing(coded, capsys):
    _log_change("--lang", LANG, "--change", "change", "--layer", "taxonomy", "--why", "t",
                "--apply")
    assert "nothing to log" in capsys.readouterr().out


def test_log_change_logs_a_hand_edit_to_a_language_source(coded, capsys):
    target = file_door.planar(LANG)
    old = file_door.read(target)
    # The logged version, kept in the archive as the door keeps each one it replaces.
    kept = coded / LANG / "archive" / "lang_setup" / f"planar_{LANG}_20261031_000000.tsv"
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text(old, encoding="utf-8")
    target.path.write_text(old + "\n", encoding="utf-8")
    _log_change("--lang", LANG, "--change", "change", "--layer", "convention",
                "--why", "tidy", "--apply")
    lines = source_log.read_lines(LANG)
    assert lines[-1]["file"] == target.relpath and lines[-1]["by"] == "log-change"
    assert lines[-1]["change"] == "change" and lines[-1]["layer"] == "convention"
    assert lines[-1]["fingerprint"] == file_door.fingerprint(old + "\n")
    assert (coded / LANG / lines[-1]["previous version"]).read_text(encoding="utf-8") == old
    assert source_log.unlogged([LANG]) == []


def test_log_change_logs_a_schema_edit_one_line_per_change(coded, schemas):
    terms = schemas / "terms.yaml"
    old = terms.read_text(encoding="utf-8")
    terms.write_text(old + "# note\n", encoding="utf-8")
    _log_change("--change", "rename", "--layer", "taxonomy", "--change", "add",
                "--layer", "taxonomy", "--why", "t", "--apply")
    *_, first, second = source_log.read_lines(source_log.SCHEMAS)
    assert (first["change"], second["change"]) == ("rename", "add")
    assert first["fingerprint"] == ""
    assert second["fingerprint"] == file_door.fingerprint(terms.read_bytes())
    assert source_log.unlogged([source_log.SCHEMAS]) == []
    # The version it replaced is kept (unit 18), so the schemas rebuild at any position.
    assert (schemas / second["previous version"]).read_text(encoding="utf-8") == old
    rebuilt = schemas.parent / "rebuilt"
    source_log.files_at(source_log.SCHEMAS, len(source_log.read_lines("schemas")) - 2, rebuilt)
    assert (rebuilt / "terms.yaml").read_text(encoding="utf-8") == old


def test_a_breaking_edit_needs_an_issue_and_what_happens_to_the_answers(
        coded, schemas, monkeypatch, capsys):
    monkeypatch.setattr(change_effects, "measure",
                        lambda before, coded_data=None, code_from=None: Effects({LANG: 4}, {}))
    terms = schemas / "terms.yaml"
    terms.write_text(terms.read_text(encoding="utf-8") + "# note\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="must name an issue"):
        _log_change("--change", "remove", "--layer", "taxonomy", "--why", "t", "--apply")
    assert source_log.unlogged([source_log.SCHEMAS])   # nothing logged
    _log_change("--change", "remove", "--layer", "taxonomy", "--why", "#5: dropped",
                "--answers", "#6 asks the annotator to redo them", "--apply")
    last = source_log.read_lines(source_log.SCHEMAS)[-1]
    assert last["answers broken"] == "4 (stan1293 4)"
    assert last["what changed"].endswith("answers: #6 asks the annotator to redo them")


def test_change_and_layer_must_pair(coded, schemas):
    terms = schemas / "terms.yaml"
    terms.write_text("x: 1\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="same number of times"):
        _log_change("--change", "add", "--change", "rename", "--layer", "shape", "--why", "t")


# ---------------------------------------------------------------------------
# Effects, measured for real
# ---------------------------------------------------------------------------

def test_removing_an_answered_criterion_breaks_its_answers(coded, real_measure):
    target = file_door.diagnostics_yaml(LANG)
    old = file_door.read(target)
    assert "      accented: [y, n, both]\n" in old
    target.path.write_text(old.replace("      accented: [y, n, both]\n", "", 1), encoding="utf-8")
    effects = change_effects.measure({target.path: old}, coded_data=coded)
    assert effects.broken.get(LANG, 0) > 0
    assert effects.breaking
    assert "synth0001" not in effects.broken


def test_an_edit_that_changes_nothing_measured_breaks_nothing(coded, real_measure):
    target = file_door.diagnostics_yaml(LANG)
    old = file_door.read(target)
    target.path.write_text(old + "\n# a comment\n", encoding="utf-8")
    effects = change_effects.measure({target.path: old}, coded_data=coded)
    assert effects.answers_cell() == "0" and effects.spans_cell() == ""
    assert not effects.breaking


def test_the_before_copy_can_take_the_code_as_last_committed(tmp_path):
    tree = tmp_path / "tree"
    (tree / "planars").mkdir(parents=True)
    (tree / "planars" / "stray.py").write_text("x = 1\n", encoding="utf-8")
    change_effects._code_at(tree, "HEAD")
    assert not (tree / "planars" / "stray.py").exists()
    assert (tree / "planars" / "__init__.py").exists()


def test_compare_counts_lost_valid_answers_and_moved_spans():
    old = {"valid": {"x": {"c/a": 5, "c/b": 2}}, "spans": {"x": {"c": ["h1"], "d": ["h2"]}}}
    new = {"valid": {"x": {"c/a": 3, "c/b": 4}}, "spans": {"x": {"c": ["h1"], "d": ["h3"]}}}
    effects = change_effects.compare(old, new)
    assert effects.answers_cell() == "2 (x 2)"
    assert effects.spans_cell() == "x: d"


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

def _line(when, change, answers="0", spans="", why="t", by="log-change"):
    return {"when (UTC)": when, "by": by, "why": why, "change": change,
            "answers broken": answers, "spans moved": spans}


def test_the_level_is_read_from_the_lines():
    assert versions.level([_line("t", "rename")]) == versions.REVISION
    assert versions.level([_line("t", "rename"), _line("t", "add")]) == versions.ADDITION
    assert versions.level([_line("t", "add", answers="3 (x 3)")]) == versions.BREAKING
    assert versions.level([_line("t", "reword", spans="x: c")]) == versions.BREAKING
    assert versions.level([_line("t", "change", answers="unknown (no copy)")]) == versions.BREAKING
    assert versions.level([_line("t", "change", answers="")]) == versions.BREAKING


def test_a_version_counts_edits_since_the_baseline(coded, schemas):
    rows = []
    source = source_log.schema_source("terms.yaml")
    for when, change, answers in [("2026-11-02T00:00:00Z", "add", "0"),
                                  ("2026-11-03T00:00:00Z", "rename", "0"),
                                  ("2026-11-03T00:00:00Z", "add", "0"),   # same edit
                                  ("2026-11-04T00:00:00Z", "remove", "2 (x 2)"),
                                  ("2026-11-05T00:00:00Z", "reword", "0")]:
        rows.append(source_log.line(source, what="w", by="log-change", why="t", change=change,
                                    layer="taxonomy", answers=answers, when=when))
    source_log.append_project_lines(rows)
    assert versions.version(source_log.SCHEMAS) == "1.2.1"
    assert versions.version(LANG) == "0.0.0"


def test_a_release_waits_while_a_breaking_change_has_annotation_pending(
        coded, schemas, github):
    number = github.seed_issue("Redo the accented cells", "needs-fixing")
    source_log.append_project_lines([source_log.line(
        source_log.schema_source("terms.yaml"), what="w", by="log-change",
        why=f"#{number}: removed", change="remove", layer="taxonomy", answers="2 (x 2)",
        when="2026-11-02T00:00:00Z")])
    [problem] = versions.release_problems()
    assert f"#{number}" in problem
    github.close_issue(number)
    assert versions.release_problems() == []
