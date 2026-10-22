"""One-time migration: take the "anyone with the link" share off English's
biuniqueness_deviations sheet.

Motivation: project data is shared with named people only (coding/sheet_spec.py,
sharing_spec). After remove_coreference_stan1293_link_share.py, the second
2026-10-22 refresh's integrity check found biuniqueness_deviations_stan1293
shared by link (reader) too and updated #317. Like the coreference sheet, it was
set by hand in the Drive window. Its annotator keeps their access by name
(the dry run lists who keeps access). Jeff approved removing it, 2026-10-22.
Run: 2026-10-22.

Usage:
    python migrations/remove_biuniqueness_deviations_stan1293_link_share.py           # dry run
    python migrations/remove_biuniqueness_deviations_stan1293_link_share.py --apply   # remove it

Post-run checks:
    python -m coding integrity-check     # SHARING: no differences
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding.drive import remove_anyone_permission  # noqa: E402
from coding.drive_door import ARCHIVED, STATE_LABEL  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402

LANG, CLASS = "stan1293", "biuniqueness_deviations"


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    found = doorway.list_files(
        q=f"properties has {{ key='planars_lang' and value='{LANG}' }} and "
          f"properties has {{ key='planars_class' and value='{CLASS}' }} and trashed=false",
        fields="files(id,name,properties)")
    found = [f for f in found if (f.get("properties") or {}).get(STATE_LABEL) != ARCHIVED]
    if len(found) != 1:
        raise SystemExit(f"expected one {CLASS}_{LANG} sheet, found {len(found)}")
    sheet = found[0]
    grants = doorway.list_permissions(sheet["id"], fields="permissions(id,type,role,emailAddress)")
    for g in grants:
        if g.get("type") != "anyone":
            print(f"  keeps: {g.get('emailAddress', g.get('type'))} ({g.get('role')})")
    links = [g for g in grants if g.get("type") == "anyone"]
    print(f"{sheet['name']}: {len(links)} link share(s)")
    if links:
        print(f"  {'removing' if apply else 'would remove'} it")
        if apply:
            remove_anyone_permission(doorway, sheet["id"])


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration remove_biuniqueness_deviations_stan1293_link_share",
                            may_write="--apply" in sys.argv):
        main()
