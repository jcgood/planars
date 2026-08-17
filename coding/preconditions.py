"""Centralized precondition enforcement for the `python -m coding` dispatch
chokepoint (Phase 5 unit D, issue #271).

Before this, each command's own main() called drive._check_coded_data_clean()
by hand at the top of its --apply path — a separate, hand-written call per
file, easy to add for one mode and forget for the next. That exact gap
happened twice (Findings 23/24 in docs/data-layer-progress.md): a command's
operations.yaml record already declared coded_data_clean_tree as a
precondition while the code never actually checked it, for prune-manifest
and sync-diagnostics-yaml respectively — caught only because Phase 4's
review traced every claim against the code by hand.

Centralizing here forecloses that bug class instead of just documenting it:
enforcement is driven directly off each command's own operations.yaml
record (already the source of truth for what preconditions a command
declares), so a declared-but-unchecked precondition is no longer possible —
the declaration IS what runs. Wired into coding/__main__.py's dispatch,
after the parser builds args and before mod.main(args) runs, keyed by the
command name.

Only coded_data_clean_tree is enforced here — the one precondition that was
actually a scattered manual _check_coded_data_clean() call per file. The
other two registered preconditions are deliberately left where they were:
coded_data_git_identity_configured is enforced downstream, inside
drive._autocommit_data() itself (it raises on a failed git commit,
regardless of cause — see preconditions.yaml), and
check_notes_documents_scope_authorized has no automated check at all today
(a one-time manual OAuth re-authorization step). Neither was a
"_check_coded_data_clean()-style call, scattered per command" — the shape
this unit was scoped to replace, see docs/data-layer-progress.md's Open
questions entry for unit D — so centralizing them here would be a different,
un-scoped change, not this one.
"""
from __future__ import annotations

import argparse
from typing import Dict, List, Optional

from .drive import _check_coded_data_clean
from .registry import _load_operations

# coded_data_clean_tree defaults to checking only *.tsv (preconditions.yaml's
# documented default). sync_diagnostics_yaml is the one command that reads
# AND writes coded_data/*.yaml as well as *.tsv across all three of its
# directions, so it needs both extensions checked — the same (".yaml",
# ".tsv") tuple its own manual call passed before centralization.
# operations.yaml's preconditions field is a plain list of ids with no
# per-command parameters (see operation_record.schema.json) — deliberately,
# so a schema change isn't warranted for a single documented exception; this
# lookup lives here instead. Revisit if a second exception ever shows up.
_CODED_DATA_CLEAN_EXTENSIONS: Dict[str, tuple] = {
    "sync_diagnostics_yaml": (".yaml", ".tsv"),
}

_ENFORCERS = {
    "coded_data_clean_tree": lambda op_id: _check_coded_data_clean(
        extensions=_CODED_DATA_CLEAN_EXTENSIONS.get(op_id, (".tsv",))
    ),
}


def _flag_dest(flag: str) -> str:
    """argparse's own long-option-to-dest rule: '--regen-dependents' -> 'regen_dependents'."""
    return flag.lstrip("-").replace("-", "_")


def _gate_satisfied(apply_gate: Optional[str], mode_name: Optional[str],
                     args: argparse.Namespace) -> bool:
    """True if this record/mode's gate is satisfied by the actual invocation.

    apply_gate is a space-separated list of long flags that must ALL be set
    (e.g. "--apply", "--to-sheet --apply") — active whenever the coordinator
    passed every one of them. A null apply_gate means no --apply concept:
    for the base record that means "always active"; for a mode (which
    always corresponds to its own named flag, e.g. generate-sheets'
    --regen-dependents) it means "active whenever that flag itself is set",
    since that mode's code path runs independent of --apply entirely.
    """
    if apply_gate is None:
        if mode_name is None:
            return True
        return bool(getattr(args, _flag_dest(mode_name), False))
    return all(getattr(args, _flag_dest(flag), False) for flag in apply_gate.split())


def active_preconditions(op_id: str, args: argparse.Namespace) -> List[str]:
    """Which precondition ids apply to this actual invocation of op_id.

    Unions the base record's preconditions (if its own apply_gate is
    satisfied) with every mode's preconditions whose own apply_gate/flag is
    satisfied. Modes are self-contained overrides of the base record (see
    operation_record.schema.json), but more than one can be active in the
    same real invocation — e.g. `sync-params --apply --refresh-dropdowns`
    satisfies both the base record's "--apply" gate and the
    "--refresh-dropdowns" mode's "--apply --refresh-dropdowns" gate — so
    this collects the union rather than picking one.
    """
    record = _load_operations().get(op_id)
    if record is None:
        return []
    active: List[str] = []
    if _gate_satisfied(record["apply_gate"], None, args):
        active.extend(record["preconditions"])
    for mode in record.get("modes", []):
        if _gate_satisfied(mode["apply_gate"], mode["name"], args):
            active.extend(mode["preconditions"])
    seen = set()
    return [p for p in active if not (p in seen or seen.add(p))]


def enforce(op_id: str, args: argparse.Namespace) -> None:
    """Run every centrally-enforceable precondition active for this invocation.

    Silently skips any active precondition id with no registered enforcer
    in _ENFORCERS — by design, only coded_data_clean_tree is centrally
    enforced today (see module docstring).
    """
    for precondition_id in active_preconditions(op_id, args):
        enforcer = _ENFORCERS.get(precondition_id)
        if enforcer is not None:
            enforcer(op_id)
