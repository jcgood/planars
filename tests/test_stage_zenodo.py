"""Staging a volume's Zenodo records (coding/stage_zenodo.py): the metadata
each record's fields are read from, and the reserved DOIs a volume names
(chapters/build.py's `records`)."""

import pytest

from chapters import build as cb
from chapters.data import ChapterDataError
from coding import drive_door, file_door
from coding import stage_zenodo as sz


def test_a_licence_is_given_per_language():
    assert sz.parse_licences(["stan1293=CC0-1.0"]) == {"stan1293": "CC0-1.0"}
    assert sz.parse_licences(None) == {}
    with pytest.raises(sz.StagingRefused, match="glottocode"):
        sz.parse_licences(["CC0-1.0"])


def test_creators_carry_orcid_and_affiliation():
    people = [{"family-names": "Good", "given-names": "Jeff", "affiliation": "University at Buffalo",
               "orcid": "https://orcid.org/0000-0001-8679-4654"}]
    assert sz.creators(people) == [{"name": "Good, Jeff", "affiliation": "University at Buffalo",
                                    "orcid": "0000-0001-8679-4654"}]


def test_the_works_built_on_are_read_from_the_citation_file():
    refs = sz.builds_on(sz._cff(sz.ROOT / "CITATION.cff"))
    assert {"identifier": "10.5281/zenodo.10559861", "relation": "references", "scheme": "doi",
            "resource_type": "publication"} in refs
    assert any(r["scheme"] == "url" and "Constituency-Database" in r["identifier"] for r in refs)
    with pytest.raises(sz.StagingRefused, match="no doi or url"):
        sz.builds_on({"references": [{"title": "X"}]})


def test_every_licence_has_zenodo_s_name():
    from coding import export_release as er
    assert set(er.LICENCES) | {"MIT", sz.REPORT_LICENCE} <= set(sz.ZENODO_LICENCE)


def _volume(text, vol="zen"):
    with drive_door.running("t", may_write=True):
        file_door.write_paper(file_door.paper_stub(f"{vol}/{cb.VOLUME}"), text)


BASE = "title: R\nvenue: report\nparts: [intro, stan1293]\n"


def test_records_are_reserved_dois_for_the_volume_s_records():
    _volume(BASE + "records: {report: 10.5281/zenodo.1, stan1293: 10.5281/zenodo.2}\n")
    volume, _ = cb.read_volume("zen")
    assert cb.record_lines(volume)[0] == ("This report", "10.5281/zenodo.1")
    assert cb.record_lines(volume)[1][1] == "10.5281/zenodo.2"
    for i, bad in enumerate(("records: {report: https://doi.org/10.5281/zenodo.1}\n",
                             "records: {book: 10.5281/zenodo.1}\n", "records: [10.5281/zenodo.1]\n")):
        _volume(BASE + bad, f"zen{i}")
        with pytest.raises(ChapterDataError, match="records"):
            cb.read_volume(f"zen{i}")


def test_the_staging_readme_says_which_dois_are_still_to_reserve():
    text = sz.staging_readme("report", ["1-software"], ["the report"])
    assert "not yet reserved" in text and "Reserve DOI" in text
    assert "rebuild-check" in sz.staging_readme("report", ["1-software"], [])
