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


def _flag(name: str, entry: Optional[dict], key: str) -> bool:
    flag = (entry or {}).get(key, False)
    if not isinstance(flag, bool):
        raise ValueError(f"{key}: for {name!r} in coded_data/people.yaml is "
                         f"{flag!r}; write true or false.")
    return flag


def coordinator_emails() -> List[str]:
    """The address of every coordinator besides the Drive files' owner
    (``coordinator: true`` in people.yaml), who gets writer on the root folder."""
    return sorted(email_for(name) for name, entry in _load_people().items()
                  if _flag(name, entry, "coordinator"))


def coordinator_githubs() -> List[str]:
    """The GitHub username of every coordinator and of the owner
    (``coordinator: true`` or ``owner: true`` in people.yaml) who has one,
    for notices meant for the coordinators."""
    return sorted(github_for(name) for name, entry in _load_people().items()
                  if (_flag(name, entry, "coordinator") or _flag(name, entry, "owner"))
                  and github_for(name))


def known_names() -> List[str]:
    """Every name people.yaml lists, in file order: who may be named as
    having decided something (coding/decisions.py)."""
    return list(_load_people())


def name_for_email(email: Optional[str]) -> Optional[str]:
    """The name people.yaml files this address under, or None. For reports
    that go where addresses must not (GitHub issues: planars is public)."""
    for name, entry in _load_people().items():
        if (entry or {}).get("email", "").strip().lower() == (email or "").strip().lower():
            return name
    return None


UNLISTED_EDITOR = "someone not in people.yaml"


def editors(revisions: List[dict], since: Optional[str] = None) -> List[str]:
    """Who edited a Drive file after ``since`` (an ISO UTC time; all of its
    history if None), by name, in the order they first appear. ``revisions``
    is the doorway's ``list_revisions``.

    The account the tooling runs as (``me``) is left out: every write the
    tooling makes is a revision by it, so it can't be told apart from a hand
    edit from the same account (docs/plain-record-design.md § 3.3). A name
    comes from people.yaml by address, never from the name Drive shows,
    which anyone can set to anything. Anyone else is UNLISTED_EDITOR:
    the files are shared only with people in people.yaml, so an edit by
    someone else means a file is open wider than it should be, and their
    own name doesn't belong in a public issue. No address is ever returned,
    so the result may go in a file or an issue."""
    from datetime import datetime

    def when(text: str) -> datetime:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))

    after = when(since) if since else None
    names: List[str] = []
    for r in revisions:
        user = r.get("lastModifyingUser") or {}
        if user.get("me") or (after and when(r["modifiedTime"]) <= after):
            continue
        name = (name_for_email(user.get("emailAddress")) if user.get("emailAddress") else None) \
            or UNLISTED_EDITOR
        if name not in names:
            names.append(name)
    return names


# How a Drive comment by the account the tooling runs as is named. Its
# comments are the tooling's notices, or the owner's own from the same
# account; the two can't be told apart (as for revisions, § 3.3).
TOOLING_ACCOUNT = "the tooling's account"
# What list_permissions must ask for, for ``commenter``.
SHARED_WITH_FIELDS = "permissions(id,type,displayName,emailAddress)"


def commenter(author: dict, shared_with: List[dict]) -> str:
    """Who wrote a Drive comment or reply, by name (docs/plain-record-design.md
    § 3.4). ``author`` is the comment's, from the doorway's ``list_comments``;
    ``shared_with`` is the file's ``list_permissions`` with
    ``SHARED_WITH_FIELDS``.

    Drive gives a comment's author no address, only the name they show. Only
    someone the file is shared with can comment, and the file's sharing
    list does carry addresses, so the author is the one person on that list
    showing that name, then named from people.yaml by address. No match, or
    two people on the list showing the same name, is UNLISTED_EDITOR: never
    the name Drive shows, and never an address."""
    if author.get("me"):
        return TOOLING_ACCOUNT
    shown = (author.get("displayName") or "").strip()
    addresses = {p["emailAddress"].strip().lower() for p in shared_with
                 if shown and (p.get("displayName") or "").strip() == shown
                 and p.get("emailAddress")}
    if len(addresses) != 1:
        return UNLISTED_EDITOR
    return name_for_email(addresses.pop()) or UNLISTED_EDITOR


def github_for(name: str) -> Optional[str]:
    """The GitHub username of the person called `name`, or None if they have
    none on file (`github:` in people.yaml). Not everyone has one: an
    annotator without one is told about problems by a comment on the
    spreadsheet instead (issue #309)."""
    entry = _load_people().get(name) or {}
    return (entry.get("github") or "").strip().lstrip("@") or None
