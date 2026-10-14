"""One-time migration: bring live Drive sharing in line with "named access only".

Motivation: a read-only check of live Drive on 2026-10-12 (Phase 10 unit
14, issue #271) found the project root folder shared "anyone with the link
can view" (so every language folder inherited it), although Adam already has
named edit access to every sheet he works on; and the English and Araona
notes Docs view-only for Adam, although they are where he writes notes to
the coordinator. Jeff decided: project data is shared with named people
only. The code was changed in the same unit (setup-root-folder removes a
link grant, new notes Docs go to the annotator by name); this script fixes
what already exists. Generated notebooks and PDF reports keep their link
sharing on purpose and are not touched.

What it does:
  - removes every "anyone" grant from the root folder and from each language
    folder recorded in the manifest;
  - gives each language's annotator (coding/people.py) edit access to that
    language's notes Doc.

Run: 2026-10-12.

Usage:
    python migrations/share_by_name_only.py           # dry run
    python migrations/share_by_name_only.py --apply

Post-run checks: re-list the permissions (read-only) — no "anyone" on the
root or language folders; the annotator is a writer on each notes Doc; the
annotation sheets still list the annotator as writer.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.errors import HttpError  # noqa: E402

from coding.drive import (  # noqa: E402
    _load_drive_config, ensure_user_permission, load_manifest,
    remove_anyone_permission,
)
from coding.drive_doorway import get_doorway  # noqa: E402
from coding.people import annotator_email  # noqa: E402


def _anyone(doorway, file_id) -> str:
    """'' if no link sharing, else 'direct' or 'inherited' (from a parent folder)."""
    perms = doorway.list_permissions(
        file_id, fields="permissions(id,type,permissionDetails)")
    kinds = set()
    for p in perms:
        if p.get("type") == "anyone":
            details = p.get("permissionDetails") or []
            kinds.add("inherited" if details and all(d.get("inherited") for d in details)
                      else "direct")
    return "direct" if "direct" in kinds else ("inherited" if kinds else "")


def _role_of(doorway, file_id, email) -> str:
    perms = doorway.list_permissions(
        file_id, fields="permissions(emailAddress,role)")
    roles = [p.get("role") for p in perms
             if (p.get("emailAddress") or "").lower() == email.lower()]
    return ",".join(roles) or "none"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    apply = ap.parse_args().apply

    doorway = get_doorway()
    manifest = load_manifest(doorway)
    root_id = _load_drive_config().get("_root_folder_id")

    manual = []
    folders = [("root folder", root_id)] + [
        (f"{lang} folder", entry.get("folder_id"))
        for lang, entry in sorted(manifest.items())
        if not lang.startswith("_") and isinstance(entry, dict)]
    print(f"{'DRY RUN — ' if not apply else ''}link sharing on folders:")
    for label, fid in folders:
        if not fid:
            print(f"  {label}: no id, skipped")
            continue
        has = _anyone(doorway, fid)
        print(f"  {label}: " + {
            "direct": "anyone with the link → remove",
            "inherited": "anyone with the link, inherited from the root (goes when the root's does)",
            "": "no link sharing"}[has])
        if apply and has == "direct":
            try:
                remove_anyone_permission(doorway, fid)
            except HttpError as exc:
                if "appNotAuthorizedToChild" not in str(exc):
                    raise
                # The tooling's OAuth scope only reaches files it created;
                # Google refuses a sharing change on a folder holding any
                # file made some other way. Only a person can change it.
                manual.append((label, f"https://drive.google.com/drive/folders/{fid}"))
                print(f"    cannot change: the folder holds files this tool didn't create")

    print("notes Docs:")
    for lang, entry in sorted(manifest.items()):
        if lang.startswith("_") or not isinstance(entry, dict):
            continue
        doc_id = entry.get("notes_doc_id")
        email = annotator_email(lang)
        if not doc_id or not email:
            print(f"  {lang}: {'no notes Doc' if not doc_id else 'no annotator named'}, skipped")
            continue
        current = _role_of(doorway, doc_id, email)
        print(f"  {lang}: annotator has {current} → writer")
        if apply:
            ensure_user_permission(doorway, doc_id, email, "writer")
        if _anyone(doorway, doc_id):
            print(f"  {lang}: notes Doc has link sharing → remove")
            if apply:
                remove_anyone_permission(doorway, doc_id)

    if manual:
        print("\nChange these by hand (Share → General access → Restricted):")
        for label, url in manual:
            print(f"  {label}: {url}")
    if not apply:
        print("\nRun with --apply to change sharing.")


if __name__ == "__main__":
    import sys

    from coding import drive_door
    # Runs outside `python -m coding`, so it tells the Drive door itself.
    with drive_door.running("migration share_by_name_only",
                            may_write="--apply" in sys.argv):
        main()
