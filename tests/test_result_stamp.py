"""Tests for unit 18 (docs/result-stamp-design.md): every change-log line's
fingerprint, rebuilding a language's files at a log position
(``source_log.files_at``), and the stamp a result carries
(``versions.stamp``).

The files are a private copy of the frozen data with empty change logs, so
each test's log holds only its own writes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import pytest

from coding import drive_door, file_door, source_log, versions
from fake_drive import use_frozen_coded_data

LANG = "synth0001"


@pytest.fixture()
def coded(monkeypatch, tmp_path) -> Path:
    coded = use_frozen_coded_data(monkeypatch, tmp_path)
    for log in coded.glob("*/changes.tsv"):
        log.unlink()
    return coded


def _state(folder: Path) -> Dict[str, bytes]:
    """Every file a rebuild covers, as it is in ``folder``."""
    return {str(p.relative_to(folder)): p.read_bytes() for p in sorted(folder.rglob("*"))
            if p.is_file() and not source_log._not_rebuilt(LANG, p.relative_to(folder))}


def _writes(coded: Path):
    """A run of changes of every kind, yielding the language's state after each."""
    notes = file_door.notes_text(LANG)
    with drive_door.running("t", may_write=True):
        file_door.write(notes, "first\n", why="t")             # created
        yield _state(coded / LANG)
        file_door.write(notes, "second\n", why="t")            # overwritten
        yield _state(coded / LANG)
        file_door.write(notes, "second\n", why="t")            # unchanged: no line
        decisions = file_door.decisions(LANG)
        file_door.write(decisions, (file_door.read(decisions) or "") + "x\n", why="t")
        yield _state(coded / LANG)
        file_door.remove(notes, why="t")                       # removed
        yield _state(coded / LANG)


def test_every_line_records_the_fingerprint_it_leaves(coded):
    states = list(_writes(coded))
    lines = source_log.read_lines(LANG)
    assert len(lines) == len(states)
    assert lines[0]["fingerprint"] == file_door.fingerprint("first\n")
    assert lines[1]["fingerprint"] == file_door.fingerprint("second\n")
    assert lines[-1]["fingerprint"] == ""          # a removal leaves no file


def test_every_position_rebuilds_exactly_the_files_that_stood_then(coded, tmp_path):
    start = _state(coded / LANG)
    states = [start, *_writes(coded)]
    assert source_log.position(LANG) == len(states) - 1
    for at, expected in enumerate(states):
        dest = tmp_path / f"at{at}"
        source_log.files_at(LANG, at, dest)
        assert _state(dest) == expected, f"position {at}"
        assert len(source_log.read_rows((dest / "changes.tsv").read_text(encoding="utf-8"))) == at


def test_a_file_edited_outside_the_tooling_is_found_and_not_rebuilt(coded, tmp_path):
    list(_writes(coded))
    target = file_door.decisions(LANG)
    target.path.write_text(file_door.read(target) + "y\n", encoding="utf-8")
    assert source_log.drifted(LANG) == [target.relpath]
    with pytest.raises(source_log.RebuildError, match="outside the tooling"):
        source_log.files_at(LANG, source_log.position(LANG), tmp_path / "out")


def test_a_missing_archive_copy_is_reported(coded, tmp_path):
    list(_writes(coded))
    previous = source_log.read_lines(LANG)[1]["previous version"]
    (coded / LANG / previous).unlink()
    with pytest.raises(source_log.RebuildError, match="not in the archive"):
        source_log.files_at(LANG, 1, tmp_path / "out")


def test_a_position_before_a_files_record_starts_is_refused(coded, tmp_path):
    source = source_log.language_sources(LANG)[0]
    file_door._log(None, source.target, "baseline", "start", None, source.path,
                   changes=[(file_door.BASELINE, "")],
                   new_text=source_log.read_text(source.path))
    with pytest.raises(source_log.RebuildError, match="not kept"):
        source_log.files_at(LANG, 0, tmp_path / "out")
    source_log.files_at(LANG, 1, tmp_path / "out")   # from the baseline on, it can


def test_no_such_position(coded, tmp_path):
    with pytest.raises(source_log.RebuildError, match="no position 5"):
        source_log.files_at(LANG, 5, tmp_path / "out")


# ---------------------------------------------------------------------------
# The stamp
# ---------------------------------------------------------------------------

def test_the_stamp_names_each_streams_version_and_position(coded, monkeypatch):
    monkeypatch.setattr(versions, "code_changed", lambda: False)
    list(_writes(coded))
    s = versions.stamp([LANG])
    assert s["code"]["version"] == versions.code_version()
    assert s["languages"][LANG] == {"version": versions.version(LANG),
                                    "position": source_log.position(LANG), "drifted": []}
    assert s["schemas"]["position"] == source_log.position(source_log.SCHEMAS)
    assert versions.stamp_problems(s) == []
    text = versions.stamp_text(s)
    assert f"code {versions.code_version()}" in text and "not reproducible" not in text


def test_a_stamp_says_why_it_cannot_be_rebuilt(coded, monkeypatch):
    monkeypatch.setattr(versions, "code_changed", lambda: True)
    list(_writes(coded))
    target = file_door.decisions(LANG)
    target.path.write_text(file_door.read(target) + "y\n", encoding="utf-8")
    problems = versions.stamp_problems(versions.stamp([LANG]))
    assert any("uncommitted changes" in p for p in problems)
    assert any(target.relpath in p for p in problems)


def test_same_data_compares_positions_not_the_code(coded, monkeypatch):
    monkeypatch.setattr(versions, "code_changed", lambda: False)
    a = versions.stamp([LANG])
    b = dict(a, code={"version": "other", "uncommitted_changes": False})
    assert versions.same_data(a, b)
    list(_writes(coded))
    assert not versions.same_data(a, versions.stamp([LANG]))


def test_rebuild_writes_the_schemas_and_each_language(coded, monkeypatch, tmp_path):
    monkeypatch.setattr(versions, "code_changed", lambda: False)
    monkeypatch.setattr(source_log, "position", lambda stream: 0 if stream == source_log.SCHEMAS
                        else len(source_log.read_lines(stream)))
    monkeypatch.setattr(source_log, "drifted", lambda stream: [])
    list(_writes(coded))
    s = versions.stamp([LANG])
    calls = []
    real = source_log.files_at
    monkeypatch.setattr(source_log, "files_at",
                        lambda stream, at, dest: calls.append((stream, at, dest)) or
                        (real(stream, at, dest) if stream != source_log.SCHEMAS else []))
    versions.rebuild(s, tmp_path / "out")
    assert calls[0] == (source_log.SCHEMAS, 0, tmp_path / "out" / "schemas")
    assert calls[1][0] == LANG and calls[1][2] == tmp_path / "out" / "coded_data" / LANG
    assert (tmp_path / "out" / "coded_data" / LANG / "changes.tsv").exists()
