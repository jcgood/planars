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

Two are enforced here: coded_data_clean_tree — the one precondition that was
actually a scattered manual _check_coded_data_clean() call per file — and
coded_data_up_to_date (Phase 10 unit 12: a command acting on state another
machine wrote into planars-data runs only on an up-to-date copy). The
other two registered preconditions are deliberately left where they were:
coded_data_git_identity_configured is enforced downstream, where the
local-file door commits what a command wrote (file_door.finish; it raises on
a failed git commit, regardless of cause — see preconditions.yaml), and
check_notes_documents_scope_authorized has no automated check at all today
(a one-time manual OAuth re-authorization step). Neither was a
"_check_coded_data_clean()-style call, scattered per command" — the shape
this unit was scoped to replace, see docs/data-layer-progress.md's Open
questions entry for unit D — so centralizing them here would be a different,
un-scoped change, not this one.
"""
from __future__ import annotations

import argparse
from typing import Dict, List

from .drive import _check_coded_data_clean
from .gating import active_parts
from .registry import _load_operations

# coded_data_clean_tree defaults to checking only *.tsv (preconditions.yaml's
# documented default). The exceptions: sync_diagnostics_yaml reads
# coded_data/*.yaml as well as writing *.tsv; proposal_sheets and accept_proposal read and write the
# diagnostics YAML, the planar and the proposal base (*.json, unit 11a).
# operations.yaml's preconditions field is a plain list of ids with no
# per-command parameters (see operation_record.schema.json); three
# exceptions sharing two tuples still don't warrant a schema change, so the
# lookup stays here.
_CODED_DATA_CLEAN_EXTENSIONS: Dict[str, tuple] = {
    "sync_diagnostics_yaml": (".yaml", ".tsv"),
    "proposal_sheets": (".yaml", ".tsv", ".json"),
    "accept_proposal": (".yaml", ".tsv", ".json"),
}

def _check_coded_data_up_to_date(op_id: str) -> None:
    """Stop unless coded_data/ has every commit GitHub's planars-data has
    (preconditions.yaml: coded_data_up_to_date). Skipped when coded_data/ is
    not a git repository."""
    from . import state_files
    if not (state_files.CODED_DATA / ".git").exists():
        return
    behind = state_files.behind_remote()
    command = op_id.replace("_", "-")
    if behind is None:
        raise SystemExit(
            f"ERROR: could not check that coded_data/ is up to date with GitHub "
            f"(no network, or the clone has no upstream branch). {command} acts "
            f"on state the daily refresh writes there, so it does not run on a "
            f"copy it can't check. Fix the connection, then re-run.")
    if behind:
        raise SystemExit(
            f"ERROR: coded_data/ is {behind} commit(s) behind GitHub, which may "
            f"hold the daily refresh's work or another machine's state. Run:"
            f"\n\n    git -C coded_data pull\n\nthen re-run {command}.")


_ENFORCERS = {
    "coded_data_clean_tree": lambda op_id: _check_coded_data_clean(
        extensions=_CODED_DATA_CLEAN_EXTENSIONS.get(op_id, (".tsv",))
    ),
    "coded_data_up_to_date": _check_coded_data_up_to_date,
}


def active_preconditions(op_id: str, args: argparse.Namespace) -> List[str]:
    """Which precondition ids apply to this actual invocation of op_id.

    Unions the base record's preconditions (if its own apply_gate is
    satisfied) with every mode's preconditions whose own apply_gate/flag is
    satisfied. Modes are self-contained overrides of the base record (see
    operation_record.schema.json), but more than one can be active in the
    same real invocation (a mode gated on "--apply --some-flag" is active
    alongside the base record's "--apply" gate), so this collects the union
    rather than picking one.
    """
    record = _load_operations().get(op_id)
    if record is None:
        return []
    active = [p for part in active_parts(record, args) for p in part["preconditions"]]
    seen = set()
    return [p for p in active if not (p in seen or seen.add(p))]


def enforce(op_id: str, args: argparse.Namespace) -> None:
    """Run every centrally-enforceable precondition active for this invocation.

    Silently skips any active precondition id with no registered enforcer
    in _ENFORCERS — by design, only coded_data_clean_tree and
    coded_data_up_to_date are centrally enforced today (see module docstring).
    """
    for precondition_id in active_preconditions(op_id, args):
        enforcer = _ENFORCERS.get(precondition_id)
        if enforcer is not None:
            enforcer(op_id)
