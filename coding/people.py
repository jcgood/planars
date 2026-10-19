"""Who to share a language's Drive files with, and tell about problems, by name.

The one place an email address or GitHub username is looked up. Names come from the public
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
from typing import Dict, List, Optional

import yaml

from planars.languages import get_entry, load_languages

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


def annotator_name(lang_id: str) -> Optional[str]:
    """The annotator languages.yaml names for lang_id, or None."""
    entry = get_entry(lang_id) or {}
    return (entry.get("meta", {}).get("annotator") or "").strip() or None


def annotator_email(lang_id: str) -> Optional[str]:
    """The annotator's email for lang_id, or None if languages.yaml names no annotator."""
    name = annotator_name(lang_id)
    return email_for(name) if name else None


def every_annotator_email() -> List[str]:
    """The address of every annotator languages.yaml names, for a file shared
    with all of them (the Annotation Status folder)."""
    return sorted({annotator_email(lang_id)
                   for lang_id, entry in load_languages().items()
                   if isinstance(entry, dict) and annotator_name(lang_id)})


def coordinator_emails() -> List[str]:
    """The address of every coordinator besides the Drive files' owner
    (``coordinator: true`` in people.yaml), who gets writer on the root folder."""
    emails = []
    for name, entry in _load_people().items():
        flag = (entry or {}).get("coordinator", False)
        if not isinstance(flag, bool):
            raise ValueError(f"coordinator: for {name!r} in coded_data/people.yaml is "
                             f"{flag!r}; write true or false.")
        if flag:
            emails.append(email_for(name))
    return sorted(emails)


def name_for_email(email: Optional[str]) -> Optional[str]:
    """The name people.yaml files this address under, or None. For reports
    that go where addresses must not (GitHub issues: planars is public)."""
    for name, entry in _load_people().items():
        if (entry or {}).get("email", "").strip().lower() == (email or "").strip().lower():
            return name
    return None


def github_for(name: str) -> Optional[str]:
    """The GitHub username of the person called `name`, or None if they have
    none on file (`github:` in people.yaml). Not everyone has one: an
    annotator without one is told about problems by a comment on the
    spreadsheet instead (issue #309)."""
    entry = _load_people().get(name) or {}
    return (entry.get("github") or "").strip().lstrip("@") or None
