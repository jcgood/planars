"""One-time migration: make each language's planar and diagnostics Sheets
read-only copies (Phase 10 unit 11b, docs/ownership-design.md § 3.1).

Motivation: until 2026-10-24 the daily refresh read both Sheets back into
planars-data (import-planar, import-sheets), so each was a second editable
copy of its source, and an annotator's edit to the diagnostics Sheet was
undone the same day without an issue. The intakes are retired in the same
change as this migration; changes are proposed on the proposal sheet. This
lowers each annotator's own grant on the two Sheets from writer to reader (the
sharing rule, sheet_spec._SHARING, now says reader) and protects the one tab,
so the coordinators, who are writers on the root folder, cannot edit it by
mistake either. sync-planar and sync-diagnostics-yaml protect the tab on
every run too; this does it now rather than at the next refresh.
Jeff asked for unit 11b to go ahead without waiting for a proposal, 2026-10-24.

Usage:
    python migrations/lock_planar_and_diagnostics_sheets.py           # dry run
    python migrations/lock_planar_and_diagnostics_sheets.py --apply   # change them

Post-run checks:
    python -m coding integrity-check     # SHARING: no differences
    python migrations/lock_planar_and_diagnostics_sheets.py   # nothing left to do
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding.drive import set_user_role  # noqa: E402
from coding.drive_door import ARCHIVED, COPY_SHEETS, STATE_LABEL, Identity  # noqa: E402
from coding.drive_doorway import get_doorway  # noqa: E402
from coding.locked_tabs import protect  # noqa: E402
from coding.sheet_spec import is_own_grant, sharing_spec  # noqa: E402


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    todo = 0
    for kind in sorted(COPY_SHEETS):
        found = doorway.list_files(
            q=f"properties has {{ key='planars_kind' and value='{kind}' }} and trashed=false",
            fields="files(id,name,properties)")
        for sheet in sorted(found, key=lambda f: f["name"]):
            props = sheet.get("properties") or {}
            identity = Identity.from_labels(props)
            spec = sharing_spec(identity, archived=props.get(STATE_LABEL) == ARCHIVED)
            grants = doorway.list_permissions(
                sheet["id"], fields="permissions(id,type,role,emailAddress,permissionDetails)")
            for g in grants:
                if not (is_own_grant(g) and g.get("type") == "user"):
                    continue
                wanted = spec.role_for(g.get("emailAddress"))
                if wanted and g.get("role") != wanted:
                    todo += 1
                    print(f"{sheet['name']}: {'lowering' if apply else 'would lower'} "
                          f"a {g['role']} grant to {wanted}")
                    if apply:
                        set_user_role(doorway, sheet["id"], g["emailAddress"], wanted)
            ss = doorway.open_spreadsheet(sheet["id"])
            if protect(ss, ss.sheet1, apply):
                todo += 1
                print(f"{sheet['name']}: {'protected' if apply else 'would protect'} its tab")
    if not todo:
        print("Nothing left to do.")


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration lock_planar_and_diagnostics_sheets",
                            may_write="--apply" in sys.argv):
        main()
