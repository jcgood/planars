"""Who to share a language's Drive files with, by name.

The one place an email address is looked up. Names come from the public
`schemas/languages.yaml` (`meta.annotator`); email addresses come from
`coded_data/people.yaml` in the private planars-data repo, because planars
itself is public (Phase 10 unit 14, 2026-10-12: data is shared with named
people only, and their addresses stay out of public files).

A language with no annotator named has nobody to share with (None). A
language whose annotator has no address on file is an error, not a silent
skip: otherwise a sheet would quietly be shared with nobody.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import yaml

from planars.languages import get_entry

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"


def _load_people() -> Dict[str, dict]:
    path = CODED_DATA / "people.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def email_for(name: str) -> str:
    """The email address of the person called `name`. Raises if none is on file."""
    entry = _load_people().get(name) or {}
    email = (entry.get("email") or "").strip()
    if not email:
        raise ValueError(
            f"No email address for {name!r} in coded_data/people.yaml. Add one "
            f"(the key is the name exactly as schemas/languages.yaml writes it), "
            f"commit it in coded_data/, and re-run.")
    return email


def annotator_email(lang_id: str) -> Optional[str]:
    """The annotator's email for lang_id, or None if languages.yaml names no annotator."""
    entry = get_entry(lang_id) or {}
    name = (entry.get("meta", {}).get("annotator") or "").strip()
    if not name:
        return None
    return email_for(name)
