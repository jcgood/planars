"""Crash-recovery journal for restructure_sheets.py's multi-step Drive
sequences: the main per-class restructure loop (unit 1, 2026-08-17) and
`--rename-class`'s separate archive sequence (unit 2, same day).

Phase 7 of the data layer redesign (issue #271) — "close the transaction gap."
`restructure-sheets --apply` archives a class's old sheet, creates and populates
its replacement, and updates the manifest, all live, with no rollback (#248).
Killed mid-sequence, a re-run couldn't tell which of those steps had actually
landed and would blindly retry a non-idempotent one (re-archiving an
already-archived, already-locked sheet; re-creating a sheet that already
exists but was never wired into the manifest).

**Unit of journaling: one (language, class) restructure** — the level the
per-class loop already treats as its own try-point. Each unit's entry records
the last Drive-mutating checkpoint it reached, plus exactly the detail needed
to either finish forward from there or (only when safe — see below) undo it:

    OLD_SHEET_ARCHIVED    -- old sheet renamed, moved to _archived/, locked
    NEW_SHEET_CREATED      -- new sheet exists and is fully populated
    (terminal, not stored) -- manifest updated locally AND uploaded to Drive

A unit's entry is written *before* app state assumes a step succeeded and
removed the moment the terminal state is reached, so **the journal file is
empty exactly when every unit that has ever been recorded finished cleanly,
and anything present in it at the start of a run is evidence of an
interrupted previous run** -- not something the coordinator has to
reconstruct by reading Drive by hand.

**`--rename-class` reuses the same two checkpoints, not a third kind** — a
rename's archive/create steps are physically identical to the main loop's
(same `_lock_archived_sheet`/`create_spreadsheet` calls), so the unit key
stays `(lang_id, class_name)` where `class_name` is the OLD class name (the
one whose live sheet is actually being archived), and `detail` carries an
extra `new_class_name` so recovery code and coordinator-facing reports can
tell a rename apart and name both sides. The rename's own extra steps (local
TSV directory rename, manifest key swap old->new instead of a value update)
are deliberately treated as part of *finishing* NEW_SHEET_CREATED, not
their own checkpoint -- neither is unsafe to redo or skip if a crash lands
between them, unlike archiving or creating a sheet, so giving them a
checkpoint each would add bookkeeping without closing any real risk window.
See `_finish_new_sheet_created_unit` in restructure_sheets.py.

**Rollback scope, decided with Jeff 2026-08-17: only safe pre-recreate.**
`OLD_SHEET_ARCHIVED` with no `NEW_SHEET_CREATED` yet can be undone cleanly --
nothing but the old sheet was touched, so moving it back, renaming it back,
and restoring the annotator's write access returns the class to exactly its
pre-run state. Past `NEW_SHEET_CREATED`, a real spreadsheet with real
carried-over annotation data already exists; "rolling back" would mean
deleting it, which destroys work rather than protecting it. So rollback is
offered only in the first window -- everything past it is resume-forward
only, `--resume` picking up from the next unfinished checkpoint rather than
blindly restarting the whole class. This reasoning is identical for a
rename unit: `_rollback_unit` restores the archived sheet to its OLD name
and folder regardless, since nothing named `new_class` has been created yet
at that checkpoint.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
JOURNAL_PATH = ROOT / "restructure_journal.json"

OLD_SHEET_ARCHIVED = "old_sheet_archived"
NEW_SHEET_CREATED = "new_sheet_created"

_CHECKPOINT_ORDER = [OLD_SHEET_ARCHIVED, NEW_SHEET_CREATED]


def _unit_key(lang_id: str, class_name: str) -> str:
    return f"{lang_id}:{class_name}"


def load_journal(journal_path: Optional[Path] = None) -> Dict[str, dict]:
    """Return the current journal, ``{}`` if none exists or it's empty.

    `journal_path` defaults to the real, repo-root journal every caller in
    restructure_sheets.py uses; tests pass a `tmp_path` file instead of
    monkeypatching the module global (same convention as
    `coding/provenance.py`'s `log_path` parameter -- and for the same reason:
    a `Path = JOURNAL_PATH` default is bound once, at import time, so
    monkeypatching the `JOURNAL_PATH` attribute afterward wouldn't reach a
    caller that never explicitly passes it).
    """
    path = journal_path or JOURNAL_PATH
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)


def _save_journal(journal: Dict[str, dict], journal_path: Path) -> None:
    if journal:
        journal_path.write_text(json.dumps(journal, indent=2), encoding="utf-8")
    elif journal_path.exists():
        # Nothing left to track -- remove the file rather than leave an empty
        # "{}" behind, so "journal file exists" alone is a reliable signal.
        journal_path.unlink()


def record_checkpoint(
    lang_id: str, class_name: str, checkpoint: str,
    journal_path: Optional[Path] = None, **detail,
) -> None:
    """Record that `checkpoint` was just reached for (lang_id, class_name).

    Call this immediately after the Drive mutation for that checkpoint
    succeeds -- e.g. right after `_lock_archived_sheet` returns for
    OLD_SHEET_ARCHIVED, right after the new sheet's tabs/status/reference are
    all written for NEW_SHEET_CREATED. `**detail` is whatever a resume or
    rollback of this unit will need (spreadsheet IDs, version numbers,
    construction params) -- see the callers in restructure_sheets.py for
    exactly what each checkpoint stores.
    """
    path = journal_path or JOURNAL_PATH
    journal = load_journal(path)
    journal[_unit_key(lang_id, class_name)] = {
        "lang_id": lang_id,
        "class_name": class_name,
        "checkpoint": checkpoint,
        "detail": detail,
    }
    _save_journal(journal, path)


def clear_unit(lang_id: str, class_name: str, journal_path: Optional[Path] = None) -> None:
    """Remove a unit's entry -- call once it reaches the terminal state
    (manifest updated locally AND uploaded to Drive) or has been rolled back.
    """
    path = journal_path or JOURNAL_PATH
    journal = load_journal(path)
    journal.pop(_unit_key(lang_id, class_name), None)
    _save_journal(journal, path)


def get_unit(lang_id: str, class_name: str, journal_path: Optional[Path] = None) -> Optional[dict]:
    """Return this unit's journal entry, or None if it isn't mid-flight."""
    return load_journal(journal_path).get(_unit_key(lang_id, class_name))


def is_rollback_safe(entry: dict) -> bool:
    """True if this unit's last checkpoint is OLD_SHEET_ARCHIVED and no
    later checkpoint was reached -- the only window undoing is safe in
    (see module docstring). NEW_SHEET_CREATED units are resume-only.
    """
    return entry.get("checkpoint") == OLD_SHEET_ARCHIVED


def format_incomplete_report(journal: Dict[str, dict]) -> str:
    """Coordinator-facing summary of every unit an interrupted run left
    mid-flight, and what to do about each one.
    """
    lines = [
        "restructure-sheets was interrupted mid-run last time -- "
        f"{len(journal)} class(es) left mid-flight:",
    ]
    for entry in journal.values():
        lang_id = entry["lang_id"]
        class_name = entry["class_name"]
        checkpoint = entry["checkpoint"]
        new_class_name = entry.get("detail", {}).get("new_class_name")
        # For a --rename-class unit, class_name (the journal key) is the OLD
        # name -- name both so the report reads the way the command itself
        # does, not as if the old class still exists under its old name.
        label = f"{class_name} -> {new_class_name}" if new_class_name else class_name
        if checkpoint == OLD_SHEET_ARCHIVED:
            lines.append(
                f"  [{lang_id}] {label}: old sheet archived, new sheet never "
                f"created. The old sheet is locked and annotators can't write to "
                f"it. Run with --rollback to restore it, or --resume to finish "
                f"creating the replacement."
            )
        elif checkpoint == NEW_SHEET_CREATED:
            lines.append(
                f"  [{lang_id}] {label}: new sheet created and populated, "
                f"but the manifest was never updated to point at it -- it's "
                f"currently invisible to every other command. Run with --resume "
                f"to finish (rollback isn't offered here -- the new sheet holds "
                f"real carried-over data)."
            )
        else:
            lines.append(f"  [{lang_id}] {label}: at checkpoint {checkpoint!r}.")
    lines.append(
        "\nNo other class will be processed until every mid-flight class above "
        "is resolved with --resume or (where offered) --rollback."
    )
    return "\n".join(lines)
