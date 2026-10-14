"""Provenance capture for the `python -m coding` dispatch chokepoint
(Phase 5 unit E, issue #271).

The design doc's own words for why this exists: "no record of which tool
run produced a given change... the natural place to capture this nearly
free" -- true once unit D's chokepoint existed to hook into. Wired into
coding/__main__.py's dispatch, right before mod.main(args) runs (the same
point unit D's precondition enforcement hooks into), so an entry is written
even if the command's own run fails partway through -- a partial failure
can still have produced a partial Drive write, and "this run may have
changed something" is the useful signal here, not "this run definitely
succeeded."

Scope, per Jeff's decision on the unit E open question: only commands with
real Drive/Sheets/Docs side effects are logged -- not every command, and
not merely reached-but-read-only ones (capture-drive-state, integrity-check
--sheets). "Real Drive side effects" is driven by each command's own
operations.yaml `writes_to_drive` field (added for this unit), gated the
same way coding/preconditions.py gates preconditions: per actual
invocation, not per command -- e.g. sync-diagnostics-yaml --apply (the
default direction, local TSV only) is not logged, but sync-diagnostics-yaml
--to-sheet --apply is, because only the second one actually reaches Drive.
See coding/gating.py's gate_satisfied() for exactly how a record's or
mode's gate is matched against real args.

A write a command makes on every run, a dry run included, is declared in
its record's `always_on_writes` (import-sheets' pink highlighting), and a
run of such a command is always logged (Phase 10 unit 5, design Q5). The
Drive door (coding/drive_door.py) uses the same two answers: it refuses
every write on a run `writes_to_drive` says doesn't write, except the
declared always-made ones.

Retention: append-forever (Jeff's decision on the unit E open question) --
no rotation logic. At this project's scale (one coordinator, well under a
few hundred command runs a day even during a busy `data-refresh`), the log
will not grow large enough to matter.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .gating import gate_satisfied
from .registry import _load_operations

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "provenance_log.jsonl"


def writes_to_drive(op_id: str, args: argparse.Namespace) -> bool:
    """True if this actual invocation of op_id reaches a Drive-writing path.

    Checked against the base record's own writes_to_drive/apply_gate, and
    against every mode whose own gate is satisfied -- true if EITHER says
    so, since a mode is a full override of the parts it names but a real
    invocation can satisfy the base gate and a mode's gate at once (same
    reasoning as coding/preconditions.py's active_preconditions()).
    """
    record = _load_operations().get(op_id)
    if record is None:
        return False
    if record["writes_to_drive"] and gate_satisfied(record["apply_gate"], None, args):
        return True
    for mode in record.get("modes", []):
        if mode["writes_to_drive"] and gate_satisfied(mode["apply_gate"], mode["name"], args):
            return True
    return False


def record(cli_command: str, op_id: str, args: argparse.Namespace,
           log_path: Optional[Path] = None) -> None:
    """Append one line to the provenance log if this invocation writes to Drive.

    No-op otherwise -- most invocations (dry runs, read-only commands) are
    never logged, by design (see module docstring).
    """
    always = (_load_operations().get(op_id) or {}).get("always_on_writes")
    if not writes_to_drive(op_id, args) and not always:
        return
    path = log_path or LOG_PATH
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": cli_command,
        "args": vars(args),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
