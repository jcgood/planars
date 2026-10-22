"""One-time migration: take the "anyone with the link" share off English's
coreference sheet.

Motivation: project data is shared with named people only (coding/sheet_spec.py,
sharing_spec). The 2026-10-22 refresh's integrity check found
coreference_stan1293 shared by link (reader) and filed #317. No command added
it (none appears in the provenance log), so it was set by hand in the Drive
window. Adam, its annotator, keeps his access by name. Jeff approved removing
it, 2026-10-22.
Run: 2026-10-22.

Usage:
    python migrations/remove_coreference_stan1293_link_share.py           # dry run
    python migrations/remove_coreference_stan1293_link_share.py --apply   # remove it

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

LANG, CLASS = "stan1293", "coreference"


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
    grants = doorway.list_permissions(sheet["id"], fields="permissions(id,type,role)")
    links = [g for g in grants if g.get("type") == "anyone"]
    print(f"{sheet['name']}: {len(links)} link share(s)")
    if links:
        print(f"  {'removing' if apply else 'would remove'} it")
        if apply:
            remove_anyone_permission(doorway, sheet["id"])


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration remove_coreference_stan1293_link_share",
                            may_write="--apply" in sys.argv):
        main()
