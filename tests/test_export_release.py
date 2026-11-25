"""The data release (coding/export_release.py): where it may write, what it
leaves out, what stops it, and that the spans can be derived again from
the folder it writes (docs/zenodo-report-plan.md, items 5 and 6)."""

import json

import pandas as pd
import pytest

from chapters import data as cd
from coding import export_release as er
from coding import file_door, versions
from coding.check_comments import COMMENTS
from laminar import planars_language as pl
from planars.reports import language_spans

needs_english = pytest.mark.skipif(not pl.planar_file("stan1293").exists(),
                                   reason="coded_data/ (planars-data) is not cloned")


def test_it_writes_only_outside_both_repositories(tmp_path):
    assert er.out_problems(tmp_path / "new") == []
    empty = tmp_path / "empty"
    empty.mkdir()
    assert er.out_problems(empty) == []
    assert any("public repository" in p for p in er.out_problems(er.ROOT / "release"))
    assert any("planars-data" in p for p in er.out_problems(file_door.CODED_DATA / "x"))
    (empty / "f").write_text("x")
    assert any("not an empty folder" in p for p in er.out_problems(empty))


def test_the_comments_column_is_left_out():
    text = f"Element\ty\t{COMMENTS}\tSource\na\ty\tnote to Adam\tp. 4\n"
    assert er.without_comments(text) == "Element\ty\tSource\na\ty\tp. 4\n"
    assert er.without_comments("Element\ty\na\tn\n") == "Element\ty\na\tn\n"


@needs_english
def test_claude_drafts_stop_a_release(reads_english, tmp_path, monkeypatch):
    monkeypatch.setattr(cd, "claude_drafts", lambda lang_dir: pd.DataFrame(
        [{"Class": "phrasal_accent", "Construction": "general", "Rows": 3}]))
    summary = er.build("stan1293", None, tmp_path / "out", apply=False, check_release=False)
    assert any("3 answer(s) still marked as Claude drafts" in r for r in summary["refusals"])
    with pytest.raises(er.ReleaseRefused, match="Claude drafts"):
        er.build("stan1293", None, tmp_path / "out", apply=True, check_release=False)
    assert not (tmp_path / "out").exists()


@needs_english
def test_the_spans_derive_again_from_the_release(reads_english, tmp_path, monkeypatch):
    monkeypatch.setattr(cd, "claude_drafts", lambda lang_dir: pd.DataFrame(
        columns=["Class", "Construction", "Rows"]))
    monkeypatch.setattr(versions, "stamp_problems", lambda stamp: [])  # this checkout may be mid-edit
    out = tmp_path / "out"
    summary = er.build("stan1293", None, out, apply=True, check_release=False)
    assert summary["refusals"] == []
    lang_dir = out / "coded_data" / "stan1293"
    # Only what the release holds: no records, no proposal base, no archive.
    assert not (lang_dir / "records").exists() and not (lang_dir / "archive").exists()
    assert (lang_dir / "lang_setup" / "planar_stan1293.tsv").is_file()
    assert (lang_dir / "changes.tsv").is_file()
    for tsv in lang_dir.glob("*/*.tsv"):
        assert COMMENTS not in tsv.read_text(encoding="utf-8").split("\n", 1)[0].split("\t")
    assert (out / "schemas" / "diagnostic_classes.yaml").is_file()
    assert (out / er.CODEBOOK).read_text(encoding="utf-8").startswith("# Planars Schema Reference")
    # Every file is listed with its hash.
    record = json.loads((out / er.RELEASE_RECORD).read_text(encoding="utf-8"))
    listed = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()} - {er.RELEASE_RECORD}
    assert set(record["files"]) == listed
    # The rebuild check: the spans the code derives from the released files
    # are the ones the release says it derived.
    again, _meta = language_spans("stan1293", out)
    saved = pd.read_csv(out / er.DERIVED / "spans.tsv", sep="\t")
    assert again.to_csv(sep="\t", index=False) == saved.to_csv(sep="\t", index=False)
