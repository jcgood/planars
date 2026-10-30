"""One-time migration: take the test share to jcgood@buffalo.edu off the
synth0001 folder.

Motivation: unit 11c-5's live tests (2026-10-29) shared the synth0001 folder
with Jeff's second Google account, to open a notebook and find the sheets by
label as someone who doesn't own them. people.yaml lists that address as Jeff
Good, the owner, whom the sharing rule (coding/sheet_spec.py, sharing_spec)
gives no grant, so integrity-check's SHARING section reported it as an error
in the 2026-10-30 refresh. Jeff approved removing it, 2026-10-30.
Run: 2026-10-30.

Usage:
    python migrations/remove_synth0001_test_share.py           # dry run
    python migrations/remove_synth0001_test_share.py --apply   # remove it

Post-run checks:
    python -m coding integrity-check --lang synth0001   # SHARING: no error
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coding.drive_doorway import get_doorway  # noqa: E402
from coding.drive import _load_drive_config  # noqa: E402

LANG, EMAIL = "synth0001", "jcgood@buffalo.edu"


def main() -> None:
    apply = "--apply" in sys.argv
    doorway = get_doorway()
    folder_id = _load_drive_config()[LANG]["folder_id"]
    grants = doorway.list_permissions(
        folder_id, fields="permissions(id,type,role,emailAddress)")
    test = [g for g in grants if g.get("type") == "user"
            and (g.get("emailAddress") or "").lower() == EMAIL]
    print(f"{LANG} folder: {len(test)} grant(s) to {EMAIL}")
    for g in test:
        print(f"  {'removing' if apply else 'would remove'} a {g['role']} grant")
        if apply:
            doorway.delete_permission(folder_id, g["id"])


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration remove_synth0001_test_share",
                            may_write="--apply" in sys.argv):
        main()
