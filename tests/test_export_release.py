"""The data release (coding/export_release.py): where it may write, what it
leaves out, what stops it, and that the spans can be derived again from
the folder it writes (docs/zenodo-report-plan.md, items 5 and 6)."""

import json
import re

import pandas as pd
import pytest
import yaml

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


def test_the_citation_reads_its_authors_from_the_repository(tmp_path):
    record = {"date": "2026-11-25", "stamp": {"code": {"version": "0.1.0a71"},
                                              "languages": {"synth0001": {"version": "1.2", "position": 9}}}}
    repo_cff = tmp_path / "CITATION.cff"
    repo_cff.write_text("authors:\n  - family-names: A\n    given-names: B\n"
                        "  - family-names: C\n    given-names: D\n", encoding="utf-8")
    # The dataset's authors in the language's order; the software's as the file has them.
    cff = yaml.safe_load(er.citation("synth0001", record, "CC-BY-4.0", repo_cff, names=["D C", "B A"]))
    assert [a["family-names"] for a in cff["authors"]] == ["C", "A"]
    assert [a["family-names"] for a in cff["references"][0]["authors"]] == ["A", "C"]
    assert cff["references"][0]["version"] == "0.1.0a71" and "requires attribution" in cff["message"]
    with pytest.raises(er.ReleaseRefused, match="not in CITATION.cff"):
        er.citation("synth0001", record, "CC-BY-4.0", repo_cff, names=["E F"])
    with pytest.raises(er.ReleaseRefused, match="no dataset_authors"):
        er.citation("synth0001", record, "CC-BY-4.0", repo_cff, names=[])
    repo_cff.write_text("title: x\n", encoding="utf-8")
    with pytest.raises(er.ReleaseRefused, match="no authors"):
        er.citation("synth0001", record, "CC-BY-4.0", repo_cff, names=["B A"])


def test_every_language_s_dataset_authors_are_in_the_citation_file():
    from planars.languages import load_languages
    for lang_id, entry in load_languages().items():
        if isinstance(entry, dict) and "meta" in entry:
            authors, _software = er.dataset_authors(lang_id)
            assert authors, lang_id
    english, _ = er.dataset_authors("stan1293")
    assert [a["family-names"] for a in english] == ["Tallman", "Good"]


def test_the_comments_column_is_left_out():
    text = f"Element\ty\t{COMMENTS}\tSource\na\ty\tnote to Adam\tp. 4\n"
    assert er.without_comments(text) == "Element\ty\tSource\na\ty\tp. 4\n"
    assert er.without_comments("Element\ty\na\tn\n") == "Element\ty\na\tn\n"


@needs_english
def test_claude_drafts_are_released_marked(reads_english, tmp_path, monkeypatch):
    monkeypatch.setattr(cd, "claude_drafts", lambda lang_dir: pd.DataFrame(
        [{"Class": "phrasal_accent", "Construction": "general", "Rows": 3}]))
    monkeypatch.setattr(versions, "stamp_problems", lambda stamp: [])  # this checkout may be mid-edit
    # No licence: refused for that, and only that.
    summary = er.build("stan1293", None, tmp_path / "out", apply=False, check_release=False)
    assert [r for r in summary["refusals"] if "No licence named" not in r] == []
    with pytest.raises(er.ReleaseRefused, match="No licence"):
        er.build("stan1293", None, tmp_path / "out", apply=True, check_release=False)
    assert not (tmp_path / "out").exists()
    out = tmp_path / "out"
    er.build("stan1293", None, out, apply=True, check_release=False, licence="CC0-1.0")
    record = json.loads((out / er.RELEASE_RECORD).read_text(encoding="utf-8"))
    assert record["claude_drafts"] == [{"class": "phrasal_accent", "construction": "general", "answers": 3}]
    text = (out / er.README).read_text(encoding="utf-8")
    assert "## Answers drafted with Claude" in text and "`phrasal_accent/general.tsv`: 3" in text


def test_a_release_with_no_drafts_says_nothing_of_them():
    assert er.drafts_section([]) == ""


@needs_english
def test_the_spans_derive_again_from_the_release(reads_english, tmp_path, monkeypatch):
    monkeypatch.setattr(cd, "claude_drafts", lambda lang_dir: pd.DataFrame(
        columns=["Class", "Construction", "Rows"]))
    monkeypatch.setattr(versions, "stamp_problems", lambda stamp: [])  # this checkout may be mid-edit
    out = tmp_path / "out"
    summary = er.build("stan1293", None, out, apply=True, check_release=False, licence="CC0-1.0")
    assert summary["refusals"] == []
    # The dataset's CITATION.cff: English's dataset_authors, with what this
    # repository's file says of each.
    cff = yaml.safe_load((out / er.CITATION).read_text(encoding="utf-8"))
    assert cff["authors"] == er.dataset_authors("stan1293")[0] and cff["license"] == "CC0-1.0"
    assert cff["type"] == "dataset" and "no citation is required" in cff["message"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cff["date-released"]))
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
