"""The chapters' data layer (chapters/data.py): every value named under its
language, the planars-data version read as asked, and an analysis bundle
used only when it was drawn from the same spans."""

import json

import pytest

from chapters import data as cd
from laminar import planars_language as pl
from planars.reports import completeness_summary
from planars.schema_values import class_domain_types

needs_english = pytest.mark.skipif(not pl.planar_file("stan1293").exists(),
                                   reason="coded_data/ (planars-data) is not cloned")


@pytest.fixture(scope="module")
def english():
    return cd.chapter_data("stan1293")


def test_completeness_summary():
    summary = completeness_summary({
        "ciscategorial": {"general": {"total": 10, "filled": 7, "blank": 3}},
        "proform": {"vp_ellipsis": {"total": 0, "filled": 0, "blank": 0, "missing": True},
                    "do_so": {"total": 0, "filled": 0, "blank": 0, "error": "bad"}},
    })
    assert summary == {"filled": 7, "total": 10, "by_construction": {
        "ciscategorial/general": "7/10 cells", "proform/vp_ellipsis": "not yet imported",
        "proform/do_so": "unreadable: bad"}}


@needs_english
def test_values_are_named_under_the_language(english):
    assert english.values and all(k.startswith("stan1293.") for k in english.values)
    v = english.values
    assert v["stan1293.language.glottocode"] == "stan1293"
    assert v["stan1293.data.commit"] == english.version["planars_data_commit"]
    planar = english.tables["planar"]
    assert v["stan1293.planar.positions"] == len(planar)
    assert v["stan1293.planar.zones"] + v["stan1293.planar.slots"] == len(planar)
    assert v["stan1293.spans.total"] == len(english.tables["spans"])
    assert v["stan1293.diagnostics.constructions"] == len(english.tables["diagnostics"])


@needs_english
def test_every_span_has_its_edges(english):
    spans = english.tables["spans"]
    row = spans.iloc[0]
    base = f"stan1293.span.{row['Analysis']}.{row['Construction']}.{row['Span_Key']}"
    assert english.values[f"{base}.left"] == row["Left_Edge"]
    assert english.values[f"{base}.right"] == row["Right_Edge"]
    assert english.values[f"{base}.left_name"]
    # Five values per span: span keys never collide across classes or constructions.
    assert sum(k.startswith("stan1293.span.") for k in english.values) == 5 * len(spans)


@needs_english
def test_diagnostics_follow_the_schemas_class_order(english):
    order = list(class_domain_types())
    classes = list(dict.fromkeys(english.tables["diagnostics"]["Class"]))
    assert classes == sorted(classes, key=order.index)


@needs_english
def test_a_pinned_version_reads_that_commit(english):
    if english.version["uncommitted_changes"]:
        pytest.skip("coded_data/stan1293 has uncommitted changes")
    pinned = cd.chapter_data("stan1293", version=english.version["planars_data_commit"])
    assert pinned.values == english.values
    assert pinned.missing == english.missing


def test_an_unknown_version_says_so():
    with pytest.raises(cd.ChapterDataError, match="no version"):
        with cd.data_at("no-such-commit-xyz"):
            pass


def _bundle(tmp_path, dataset, domain_sha, planar_sha, tests=()):
    folder = tmp_path / dataset / "data"
    folder.mkdir(parents=True)
    metadata = {"source_domain_sha256": domain_sha, "source_planar_sha256": planar_sha,
                "planars_source": {"planars_data_commit": "abcdef1234567890"}}
    metadata.update({field: 1 for field in cd.BUNDLE_COUNTS})
    (folder / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    for stem in tests:
        (folder / f"{stem}.tsv").write_text(
            "group\tobserved_families\tnull_mean\tp_value_le_observed\nall\t3\t4.5\t0.25\n",
            encoding="utf-8")


@needs_english
def test_a_bundle_is_used_only_when_drawn_from_these_spans(tmp_path, monkeypatch):
    monkeypatch.setattr(cd, "bundle_root", lambda dataset: tmp_path)
    table = pl.span_table("stan1293")
    planar_sha = cd._sha256(pl.planar_file("stan1293").read_text(encoding="utf-8"))
    right = cd._sha256(pl.domains_frame(pl.select(table, "all"), "types").to_csv(sep="\t", index=False))
    _bundle(tmp_path, "stan1293_types_all", right, planar_sha, tests=["fragmentation_test"])
    _bundle(tmp_path, "stan1293_classes_all", "0" * 64, planar_sha)

    chapter = cd.ChapterData(lang_id="stan1293", version={})
    cd._analysis("stan1293", cd.REPO, chapter)

    assert list(chapter.bundles) == ["stan1293_types_all"]
    assert chapter.values["stan1293.analysis.types.all.families"] == 1
    assert chapter.values["stan1293.analysis.types.all.fragmentation.all.p_value"] == 0.25
    assert not any(".classes.all." in k for k in chapter.values)
    missing = "\n".join(chapter.missing)
    assert "stan1293_classes_all was drawn from other spans" in missing
    assert "planars-data abcdef123456" in missing
    assert "stan1293_types_all analysis has no permutation tests (span_placement, arbitrary_layers)" in missing
    assert "No analysis drawn for stan1293_types_complete" in missing
