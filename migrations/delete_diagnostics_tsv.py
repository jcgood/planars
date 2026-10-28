"""One-time migration: delete each language's diagnostics_{lang_id}.tsv.

What it does: removes coded_data/{lang}/lang_setup/diagnostics_{lang}.tsv
for every language through the local-file door, which keeps each file's
last version in coded_data/{lang}/archive/lang_setup/, logs the removal in
the language's changes.tsv and commits it in planars-data.

Why: the TSV was a copy of diagnostics_{lang}.yaml, regenerated from it
every day; every reader now reads the YAML (ownership-design Q5, Phase 10
unit 11b's second part), so the copy only invited someone to edit or read
the wrong file. check-codebook's check 7 now reports a TSV that comes back.

Run: 2026-10-27, with the commit that removed the TSV's readers and writer.
That commit also removed the local-file door's diagnostics_tsv kind this
script uses, once it had run, so it no longer runs as it stands.

Usage:
    python migrations/delete_diagnostics_tsv.py           # dry run
    python migrations/delete_diagnostics_tsv.py --apply   # delete, archive, log, commit

Post-run checks:
    python -m coding check-codebook      # check 7: no TSV copy left
    python -m coding integrity-check
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coding import file_door  # noqa: E402

WHY = ("the diagnostics YAML is the one diagnostics file; every reader reads it "
       "(ownership-design Q5)")


def main() -> None:
    apply = "--apply" in sys.argv
    found = sorted(file_door.CODED_DATA.glob("*/lang_setup/diagnostics_*.tsv"))
    if not found:
        print("No diagnostics TSV left; nothing to do.")
        return
    for path in found:
        lang_id = path.parent.parent.name
        target = file_door.diagnostics_tsv(lang_id)
        if target.path != path:
            raise SystemExit(f"ERROR: {path} is not where the door expects "
                             f"{lang_id}'s diagnostics TSV ({target.path})")
        if not file_door.diagnostics_yaml(lang_id).path.exists():
            raise SystemExit(f"ERROR: {lang_id} has a diagnostics TSV but no YAML; "
                             f"restore the YAML before deleting its only copy")
        print(f"  {lang_id}: {'removing' if apply else 'would remove'} {target.relpath}")
        if apply:
            file_door.remove(target, why=WHY)
    if not apply:
        print("\nDry run. Re-run with --apply.")


if __name__ == "__main__":
    from coding import drive_door
    with drive_door.running("migration delete_diagnostics_tsv", may_write="--apply" in sys.argv):
        main()
