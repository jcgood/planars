"""Shared gate-matching logic for coding/preconditions.py,
coding/provenance.py's writes_to_drive (Phase 5 units D and E, issue #271),
which the Drive door asks whether an invocation may write at all, and
coding/file_door.py's writes_locally and edits_sources (Phase 10 unit 6a).

All answer the same underlying question against the same
operations.yaml shape -- "is this record's (or mode's) apply_gate satisfied
by the actual args of a real invocation" -- so the matching logic lives
here once. ``active_parts`` is that question asked of a whole record.
"""
from __future__ import annotations

import argparse
from typing import List, Optional


def flag_dest(flag: str) -> str:
    """argparse's own long-option-to-dest rule: '--regen-dependents' -> 'regen_dependents'."""
    return flag.lstrip("-").replace("-", "_")


def gate_satisfied(apply_gate: Optional[str], mode_name: Optional[str],
                    args: argparse.Namespace) -> bool:
    """True if this record/mode's gate is satisfied by the actual invocation.

    apply_gate is normally a space-separated list of long flags that must
    ALL be set (e.g. "--apply", "--check --apply") -- active whenever
    the coordinator passed every one of them. A null apply_gate means no
    --apply concept: for the base record that means "always active"; for a
    mode (which always corresponds to its own named flag, e.g.
    generate-sheets' --regen-dependents) it means "active whenever that
    flag itself is set", since that mode's code path runs independent of
    --apply entirely.

    A gate that is not flags raises: it can't be matched against args, and
    taking it as always or never active would be a guess. (apply-pending's
    gate was prose, "interactive", and was taken as always active until the
    command was retired, 2026-10-24.)
    """
    if apply_gate is None:
        if mode_name is None:
            return True
        return bool(getattr(args, flag_dest(mode_name), False))
    flags = apply_gate.split()
    if not all(f.startswith("--") for f in flags):
        raise ValueError(f"apply_gate {apply_gate!r} is not a list of flags "
                         "(data_dependency_schema/operations.yaml)")
    return all(getattr(args, flag_dest(f), False) for f in flags)


def active_parts(record: dict, args: argparse.Namespace) -> List[dict]:
    """The parts of an operations.yaml record this invocation runs: the
    record itself if its own apply_gate is satisfied, and every mode whose
    gate is. More than one can be active at once (a mode gated on
    "--apply --some-flag" alongside the base "--apply"), so callers take the
    union of what the parts declare."""
    parts = [record] if gate_satisfied(record["apply_gate"], None, args) else []
    return parts + [m for m in record.get("modes", [])
                    if gate_satisfied(m["apply_gate"], m["name"], args)]
