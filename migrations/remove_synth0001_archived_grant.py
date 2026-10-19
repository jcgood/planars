"""One-time migration: take Adam's reader grant off synth0001's archived
biuniqueness_deviations sheet.

Motivation: the sharing rule (coding/sheet_spec.py, sharing_spec) gives a
class sheet's access to the language's annotator, and synth0001, a test
language, names none. The grant was left when the class moved to English
(migrations/move_biuniqueness_to_stan1293.py, 2026-10-13), whose sheet holds
the 18 answers now, so nothing is lost. integrity-check's SHARING section
reported it. Jeff approved removing it, 2026-10-18.
Run: 2026-10-19.

Usage:
    python migrations/remove_synth0001_archived_grant.py           # dry run
    python migrations/remove_synth0001_archived_grant.py --apply   # remove it

Post-run checks:
    python -m coding integrity-check     # SHARING: no differences
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding.drive_door import ARCHIVED, STATE_LABEL, Identity  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402
from coding.sheet_spec import is_own_grant, sharing_spec  # noqa: E402

LANG, CLASS = "synth0001", "biuniqueness_deviations"


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    found = doorway.list_files(
        q=f"properties has {{ key='planars_lang' and value='{LANG}' }} and "
          f"properties has {{ key='planars_class' and value='{CLASS}' }} and trashed=false",
        fields="files(id,name,properties)")
    if len(found) != 1:
        raise SystemExit(f"expected one {CLASS}_{LANG} sheet, found {len(found)}")
    sheet = found[0]
    props = sheet.get("properties") or {}
    spec = sharing_spec(Identity.from_labels(props), archived=props.get(STATE_LABEL) == ARCHIVED)
    grants = doorway.list_permissions(
        sheet["id"], fields="permissions(id,type,role,emailAddress,permissionDetails)")
    extra = [g for g in grants if is_own_grant(g) and g.get("type") == "user"
             and spec.role_for(g.get("emailAddress")) is None]
    print(f"{sheet['name']}: {len(extra)} grant(s) the sharing rule doesn't give")
    for g in extra:
        print(f"  {'removing' if apply else 'would remove'} a {g['role']} grant")
        if apply:
            doorway.delete_permission(sheet["id"], g["id"])


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration remove_synth0001_archived_grant",
                            may_write="--apply" in sys.argv):
        main()
