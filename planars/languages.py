"""Language metadata helpers for planars.

Reads from schemas/languages.yaml, which ships with the package so this
module works both locally and in Colab after pip install.

Typical usage
-------------
    from planars.languages import get_display_name
    title = get_display_name("arao1248")  # "Araona [arao1248]"
"""
from __future__ import annotations

from importlib.resources import files
from typing import Optional

import yaml

_cache: Optional[dict] = None

# Language IDs with this prefix are synthetic test languages (CLAUDE.md): exempt
# from the Glottocode format and Glottolog verification, and with no
# languages.yaml entry. The one statement of the prefix; ask is_synthetic()
# rather than testing it (hidden-facts R-2).
SYNTHETIC_PREFIX = "synth"


def is_synthetic(lang_id: str) -> bool:
    """True for a synthetic test language's ID (not a real Glottocode)."""
    return lang_id.startswith(SYNTHETIC_PREFIX)


def load_languages() -> dict:
    """Return the full languages.yaml as a dict, cached after first read."""
    global _cache
    if _cache is None:
        try:
            text = files("schemas").joinpath("languages.yaml").read_text(encoding="utf-8")
            _cache = yaml.safe_load(text) or {}
        except Exception:
            _cache = {}
    return _cache


def get_entry(glottocode: str) -> Optional[dict]:
    """Return the full languages.yaml entry for glottocode, or None."""
    return load_languages().get(glottocode)


def get_display_name(glottocode: str) -> str:
    """Return 'Name [glottocode]', or bare glottocode if not in languages.yaml."""
    entry = get_entry(glottocode)
    if entry:
        name = entry.get("glottolog", {}).get("name")
        if name:
            return f"{name} [{glottocode}]"
    return glottocode
