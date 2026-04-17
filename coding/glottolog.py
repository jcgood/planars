"""Glottolog lookup and caching utilities.

Fetches language metadata from the Glottolog REST API and caches it locally
at glottolog_cache.json in the repo root (gitignored).

Usage — command line:
    python -m coding lookup-lang arao1248           # fetch + display + cache
    python -m coding lookup-lang --refresh arao1248 # force re-fetch
    python -m coding lookup-lang --all              # list all cached languages

Usage — programmatic:
    from coding.glottolog import get_metadata, validate_glottocode
    meta = get_metadata("arao1248")   # returns cached entry; fetches if needed
    print(meta["name"])               # "Araona"

Cached fields per Glottocode:
    id             Glottocode (e.g., "arao1248")
    name           Human-readable name (e.g., "Araona")
    level          "language", "dialect", or "family"
    iso639_3       ISO 639-3 code if available (e.g., "aro")
    latitude       Decimal latitude or null
    longitude      Decimal longitude or null
    classification List of {name, id} dicts from top family to immediate parent
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "glottolog_cache.json"
# Not loaded via coding.schemas cached loader: this module *writes* to
# languages.yaml, so it must always read the current on-disk state.
_LANGUAGES_YAML = ROOT / "schemas" / "languages.yaml"
_API_URL = "https://glottolog.org/resource/languoid/id/{glottocode}.json"

# Glottocodes: exactly 4 lowercase ASCII letters followed by 4 digits.
_GLOTTOCODE_RE = re.compile(r"^[a-z]{4}\d{4}$")


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _update_languages_yaml(glottocode: str, meta: dict) -> None:
    """Write/refresh the entry for glottocode in schemas/languages.yaml.

    Always updates the glottolog block (name, iso639_3, family, coordinates).
    Scaffolds an empty meta block only if one does not already exist, so
    hand-edited coordinator fields (source, author, etc.) are never overwritten.

    Note: this function uses PyYAML to rewrite the file, which strips any YAML
    comments present in languages.yaml.  Essential documentation lives in
    schemas/__init__.py rather than in the file header for this reason.
    """
    if _LANGUAGES_YAML.exists():
        with open(_LANGUAGES_YAML, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    entry = data.setdefault(glottocode, {})

    entry["glottolog"] = {
        "name":      meta["name"],
        "iso639_3":  meta["iso639_3"],
        "family":    meta["classification"][0]["name"] if meta["classification"] else None,
        "latitude":  meta["latitude"],
        "longitude": meta["longitude"],
    }

    if "meta" not in entry:
        entry["meta"] = {
            "language":          meta["name"],
            "glottocode":        glottocode,
            "source":            "",
            "author":            "",
            "annotator":         "",
            "annotation_status": "planned",
            "notes":             "",
        }

    with open(_LANGUAGES_YAML, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=True, default_flow_style=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_valid_format(glottocode: str) -> bool:
    """Return True if glottocode matches the 4-letter + 4-digit Glottocode format.

    IDs starting with 'synth' are reserved for synthetic test languages and are
    considered valid even though they don't match the standard Glottocode pattern.
    """
    if glottocode.startswith("synth"):
        return True
    return bool(_GLOTTOCODE_RE.match(glottocode))


def get_metadata(glottocode: str, *, refresh: bool = False) -> dict:
    """Return Glottolog metadata for glottocode, fetching from the API if needed.

    On first call (or with refresh=True) makes an HTTP request to the Glottolog
    REST API and writes the result to glottolog_cache.json. Subsequent calls for
    the same Glottocode are served from cache with no network access.

    Raises
    ------
    ValueError   if glottocode does not match the expected format.
    RuntimeError if the API request fails (404 = Glottocode not found).
    """
    if not is_valid_format(glottocode):
        raise ValueError(
            f"'{glottocode}' is not a valid Glottocode format "
            f"(expected 4 lowercase letters + 4 digits, e.g. 'arao1248')"
        )

    cache = _load_cache()
    if not refresh and glottocode in cache:
        return cache[glottocode]

    url = _API_URL.format(glottocode=glottocode)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(
                f"Glottocode '{glottocode}' was not found in Glottolog. "
                f"Check that it is a valid, current Glottocode."
            ) from e
        raise RuntimeError(
            f"Glottolog API returned HTTP {e.code} for '{glottocode}'"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch Glottolog data for '{glottocode}': {e}"
        ) from e

    meta = {
        "id":             data["id"],
        "name":           data["name"],
        "level":          data["level"],
        "iso639_3":       data.get("iso639-3") or data.get("hid") or None,
        "latitude":       data.get("latitude"),
        "longitude":      data.get("longitude"),
        "classification": data.get("classification", []),
    }

    cache[glottocode] = meta
    _save_cache(cache)
    _update_languages_yaml(glottocode, meta)
    return meta


def validate_glottocode(glottocode: str) -> tuple[bool, Optional[str]]:
    """Validate a Glottocode: check format and existence in Glottolog.

    Does NOT raise — returns (is_valid, error_message_or_None).
    Side effect: caches metadata on successful lookup.
    """
    if not is_valid_format(glottocode):
        return False, (
            f"'{glottocode}' is not a valid Glottocode format "
            f"(expected 4 lowercase letters + 4 digits)"
        )
    try:
        get_metadata(glottocode)
        return True, None
    except RuntimeError as e:
        return False, str(e)


def cached_entry(glottocode: str) -> Optional[dict]:
    """Return the cached metadata for glottocode, or None if not cached."""
    return _load_cache().get(glottocode)


# ---------------------------------------------------------------------------
# CLI (lookup-lang command)
# ---------------------------------------------------------------------------

def _print_meta(meta: dict) -> None:
    family = meta["classification"][0]["name"] if meta["classification"] else "—"
    iso    = meta["iso639_3"] or "—"
    lat    = f"{meta['latitude']:.4f}" if meta["latitude"] is not None else "—"
    lon    = f"{meta['longitude']:.4f}" if meta["longitude"] is not None else "—"
    print(f"  Glottocode : {meta['id']}")
    print(f"  Name       : {meta['name']}")
    print(f"  Level      : {meta['level']}")
    print(f"  ISO 639-3  : {iso}")
    print(f"  Family     : {family}")
    print(f"  Coordinates: {lat}, {lon}")
    if meta["classification"]:
        path = " > ".join(c["name"] for c in meta["classification"])
        print(f"  Class. path: {path}")


def main() -> None:
    """Entry point for `python -m coding lookup-lang`."""
    args = sys.argv[1:]

    # --all: list every cached entry
    if args == ["--all"] or args == []:
        cache = _load_cache()
        if not cache:
            print("No languages cached yet. Run: python -m coding lookup-lang <glottocode>")
            return
        print(f"{len(cache)} cached language(s):\n")
        for code, meta in sorted(cache.items()):
            family = meta["classification"][0]["name"] if meta["classification"] else "—"
            print(f"  {code}  {meta['name']}  ({meta['level']}, {family})")
        return

    refresh = False
    if "--refresh" in args:
        refresh = True
        args = [a for a in args if a != "--refresh"]

    if not args:
        print("Usage: python -m coding lookup-lang [--refresh] <glottocode>")
        print("       python -m coding lookup-lang --all")
        sys.exit(1)

    glottocode = args[0]

    was_cached = not refresh and cached_entry(glottocode) is not None
    try:
        meta = get_metadata(glottocode, refresh=refresh)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    action = "Cached" if was_cached else "Fetched"
    print(f"{action}: {glottocode}\n")
    _print_meta(meta)


if __name__ == "__main__":
    main()
