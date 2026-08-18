"""Tests for coding/glottolog.py (`python -m coding lookup-lang`).

No dedicated test file existed for this module before Phase 8 of the data
layer redesign (issue #271) turned up the gap while auditing every command's
idempotency claim in operations.yaml. `get_metadata`'s own docstring already
states the contract precisely: fetch once, cache, serve from cache on
repeat calls unless `refresh=True`. These tests prove it against a mocked
Glottolog response rather than the live API (the one thing this module
cannot be exercised against offline).
"""
from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from coding import glottolog


def _fake_response(glottocode: str, name: str = "Araona") -> bytes:
    return json.dumps({
        "id": glottocode,
        "name": name,
        "level": "language",
        "iso639-3": "aro",
        "latitude": -11.5,
        "longitude": -68.0,
        "classification": [{"name": "Tacanan", "id": "taca1257"}],
    }).encode("utf-8")


def _urlopen_stub(monkeypatch, calls: list, glottocode: str = "arao1248", name: str = "Araona"):
    """Patch urlopen to record each call and return a fake Glottolog response."""
    @contextmanager
    def fake_urlopen(url, timeout=15):
        calls.append(url)
        class _Resp:
            def read(self_inner):
                return _fake_response(glottocode, name)
        yield _Resp()

    monkeypatch.setattr(glottolog.urllib.request, "urlopen", fake_urlopen)


@pytest.fixture(autouse=True)
def _isolated_paths(tmp_path, monkeypatch):
    """Never touch the real glottolog_cache.json or schemas/languages.yaml."""
    monkeypatch.setattr(glottolog, "CACHE_PATH", tmp_path / "glottolog_cache.json")
    monkeypatch.setattr(glottolog, "_LANGUAGES_YAML", tmp_path / "languages.yaml")


# ---------------------------------------------------------------------------
# Idempotency (Phase 8 of the data layer redesign, issue #271) --
# operations.yaml's own claim: "the default reads the cache when present,
# and coding/glottolog.py:140-142's early return for an already-cached
# Glottocode makes zero writes at all."
# ---------------------------------------------------------------------------

def test_a_second_call_for_an_already_cached_glottocode_makes_no_second_fetch(monkeypatch):
    calls: list = []
    _urlopen_stub(monkeypatch, calls)

    first = glottolog.get_metadata("arao1248")
    second = glottolog.get_metadata("arao1248")

    assert len(calls) == 1  # only the first call reached the network
    assert second == first


def test_refresh_forces_a_second_fetch_even_when_cached(monkeypatch):
    calls: list = []
    _urlopen_stub(monkeypatch, calls)

    glottolog.get_metadata("arao1248")
    glottolog.get_metadata("arao1248", refresh=True)

    assert len(calls) == 2


def test_a_cache_hit_writes_neither_the_cache_file_nor_languages_yaml(monkeypatch):
    calls: list = []
    _urlopen_stub(monkeypatch, calls)

    glottolog.get_metadata("arao1248")  # first call: fetches, writes both files
    cache_mtime = glottolog.CACHE_PATH.stat().st_mtime_ns
    languages_yaml_mtime = glottolog._LANGUAGES_YAML.stat().st_mtime_ns

    glottolog.get_metadata("arao1248")  # second call: cache hit, must write nothing

    assert glottolog.CACHE_PATH.stat().st_mtime_ns == cache_mtime
    assert glottolog._LANGUAGES_YAML.stat().st_mtime_ns == languages_yaml_mtime


def test_two_different_glottocodes_each_get_their_own_fetch(monkeypatch):
    """Not globally short-circuited -- caching is per-Glottocode."""
    calls: list = []
    _urlopen_stub(monkeypatch, calls, glottocode="stan1293", name="English")

    glottolog.get_metadata("arao1248")
    glottolog.get_metadata("stan1293")

    assert len(calls) == 2
