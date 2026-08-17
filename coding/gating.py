"""Shared gate-matching logic for coding/preconditions.py and
coding/provenance.py (Phase 5 units D and E, issue #271).

Both modules answer the same underlying question against the same
operations.yaml shape -- "is this record's (or mode's) apply_gate satisfied
by the actual args of a real invocation" -- so the matching logic lives
here once rather than twice.
"""
from __future__ import annotations

import argparse
from typing import Optional


def flag_dest(flag: str) -> str:
    """argparse's own long-option-to-dest rule: '--regen-dependents' -> 'regen_dependents'."""
    return flag.lstrip("-").replace("-", "_")


def gate_satisfied(apply_gate: Optional[str], mode_name: Optional[str],
                    args: argparse.Namespace) -> bool:
    """True if this record/mode's gate is satisfied by the actual invocation.

    apply_gate is normally a space-separated list of long flags that must
    ALL be set (e.g. "--apply", "--to-sheet --apply") -- active whenever
    the coordinator passed every one of them. A null apply_gate means no
    --apply concept: for the base record that means "always active"; for a
    mode (which always corresponds to its own named flag, e.g.
    generate-sheets' --regen-dependents) it means "active whenever that
    flag itself is set", since that mode's code path runs independent of
    --apply entirely.

    A handful of records describe their gate in prose instead of real flag
    syntax -- apply_pending's is "interactive (per-entry approval, not a
    single --apply flag)", since which entries get applied is decided by
    runtime input() prompts, not by anything present in args. That can't be
    derived from args alone, so such a gate is treated as always active
    rather than silently parsed into nonsense dests that never match --
    the safer failure mode for a caller like provenance.py, where "always
    active" over-logs a run that touched nothing rather than silently
    missing one that did.
    """
    if apply_gate is None:
        if mode_name is None:
            return True
        return bool(getattr(args, flag_dest(mode_name), False))
    flags = apply_gate.split()
    if not all(f.startswith("--") for f in flags):
        return True
    return all(getattr(args, flag_dest(f), False) for f in flags)
