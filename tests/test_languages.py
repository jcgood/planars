"""Tests for planars/languages.py."""
from __future__ import annotations

import pytest

from planars.languages import get_display_name, get_entry, load_languages

# Languages that must be registered in schemas/languages.yaml
_KNOWN = ["stan1293", "arao1248"]


class TestLoadLanguages:
    def test_returns_dict(self):
        result = load_languages()
        assert isinstance(result, dict)

    def test_contains_known_glottocodes(self):
        langs = load_languages()
        for code in _KNOWN:
            assert code in langs, f"{code} missing from languages.yaml"

    def test_cached_on_repeated_calls(self):
        a = load_languages()
        b = load_languages()
        assert a is b  # same object (cached)


class TestGetEntry:
    @pytest.mark.parametrize("code", _KNOWN)
    def test_known_glottocode_returns_dict(self, code):
        entry = get_entry(code)
        assert isinstance(entry, dict)

    def test_unknown_glottocode_returns_none(self):
        assert get_entry("unkn0000") is None

    def test_entry_has_glottolog_block(self):
        entry = get_entry("stan1293")
        assert entry is not None
        assert "glottolog" in entry

    def test_entry_glottolog_has_name(self):
        entry = get_entry("stan1293")
        assert entry is not None
        assert "name" in entry.get("glottolog", {})


class TestGetDisplayName:
    @pytest.mark.parametrize("code", _KNOWN)
    def test_known_code_includes_glottocode(self, code):
        result = get_display_name(code)
        assert code in result

    @pytest.mark.parametrize("code", _KNOWN)
    def test_known_code_returns_name_bracket_format(self, code):
        result = get_display_name(code)
        # Expected format: "Some Name [glottocode]"
        assert "[" in result and "]" in result
        assert result.endswith(f"[{code}]")

    def test_unknown_code_returns_bare_code(self):
        result = get_display_name("unkn0000")
        assert result == "unkn0000"

    def test_stan1293_display_name(self):
        # Sanity check: Swahili (Kiswahili) should appear in the name
        result = get_display_name("stan1293")
        assert isinstance(result, str)
        assert "stan1293" in result

    def test_arao1248_display_name(self):
        result = get_display_name("arao1248")
        assert "arao1248" in result
        assert "Araona" in result or "[arao1248]" in result
