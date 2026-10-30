"""planars/from_sheets.py: a language read from its sheets by their labels
gives the same spans as its imported TSVs (Phase 10 unit 11c). The saved
sheets and the saved TSVs were captured together (capture-drive-state), so
they hold the same answers."""
from __future__ import annotations

import shutil

import pandas as pd
import pytest

from planars import reports
from planars.from_sheets import download_language, languages
from tests.fake_drive import FROZEN_CODED_DATA, FakeDriveDoorway

LANGS = ["stan1293", "arao1248", "synth0001"]
LANGS_SORTED = sorted(LANGS)


def _download(lang_id, dest):
    fake = FakeDriveDoorway.from_fixtures()
    return download_language(
        lang_id, dest,
        list_files=lambda q: fake.list_files(q, fields="files(id, name, properties)"),
        open_spreadsheet=fake.open_spreadsheet)


def _sorted(df):
    if df.empty:
        return df
    cols = list(df.columns)
    return df.astype(str).sort_values(cols).reset_index(drop=True)


@pytest.mark.parametrize("lang_id", LANGS)
def test_spans_from_sheets_match_spans_from_tsvs(lang_id, tmp_path):
    got = _download(lang_id, tmp_path / "sheets")
    local_root = tmp_path / "local"
    shutil.copytree(FROZEN_CODED_DATA / lang_id, local_root / "coded_data" / lang_id)
    want_df, want_meta = reports.language_spans(lang_id, local_root)
    got_df, got_meta = reports.language_spans(lang_id, got.root)
    assert not want_df.empty
    pd.testing.assert_frame_equal(_sorted(got_df), _sorted(want_df))
    assert got_meta == want_meta


def test_languages_are_those_with_a_planar_sheet():
    fake = FakeDriveDoorway.from_fixtures()
    assert languages(lambda q: fake.list_files(q, fields="files(id, name, properties)")) == LANGS_SORTED


def test_a_busy_google_is_waited_out(tmp_path, monkeypatch):
    """Google's per-minute read limit (429) is retried, as the Drive door
    retries it, rather than failing the annotator's notebook."""
    from planars import google_retry
    from tests.fake_drive import api_error
    monkeypatch.setattr(google_retry, "WAITS", (0,))
    fake = FakeDriveDoorway.from_fixtures()
    busy = {"left": 1}

    def open_spreadsheet(sid):
        if busy["left"]:
            busy["left"] -= 1
            raise api_error(429, "Quota exceeded for quota metric 'Read requests'")
        return fake.open_spreadsheet(sid)

    got = download_language(
        "synth0001", tmp_path,
        list_files=lambda q: fake.list_files(q, fields="files(id, name, properties)"),
        open_spreadsheet=open_spreadsheet)
    assert busy["left"] == 0
    assert (got.root / "coded_data" / "synth0001" / "lang_setup" / "planar_synth0001.tsv").exists()


def test_planar_and_status_are_read(tmp_path):
    got = _download("stan1293", tmp_path)
    planar = got.root / "coded_data" / "stan1293" / "lang_setup" / "planar_stan1293.tsv"
    assert planar.read_text(encoding="utf-8") == (
        FROZEN_CODED_DATA / "stan1293" / "lang_setup" / "planar_stan1293.tsv"
    ).read_text(encoding="utf-8")
    assert got.status and all(got.status.values())
