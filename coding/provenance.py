"""The provenance log: what each command wrote to Drive (issue #271).

Phase 5 unit E logged one line per command run, at the dispatcher, before
the command ran. Since Phase 10 unit 5c the Drive door (coding/drive_door.py)
writes the log instead, from the writes themselves: at the end of a command,
one line per tab or Drive file it wrote -- the command and its arguments,
what was written, which sheet it is, how many calls and cells, and the
``replacing`` reason if annotations were replaced on purpose. A run that
wrote nothing leaves no line, whatever its flags; a run that failed partway
still logs what it wrote before failing (the door logs when the command
ends, however it ends).

``writes_to_drive`` stays here: the door asks it whether an invocation may
write at all. It is driven by each command's operations.yaml
`writes_to_drive` field, gated per actual invocation, not per command --
e.g. sync-diagnostics-yaml --apply (the default direction, local TSV only)
may not write to Drive, but sync-diagnostics-yaml --to-sheet --apply may.
See coding/gating.py's gate_satisfied() for how a record's or mode's gate
is matched against real args. A write a command makes on every run, a dry
run included, is declared in its record's `always_on_writes` (import-sheets'
pink highlighting; design Q5), and the door allows and logs it.

Retention: append-forever (Jeff's decision on the unit E open question) --
no rotation logic. The log is ``state_files.PROVENANCE_LOG``, in planars-data
since Phase 10 unit 12 (it had stayed on the machine that ran the command, so
every daily refresh's lines were lost with its GitHub machine).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

from . import state_files
from .gating import gate_satisfied
from .registry import _load_operations


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


def append_writes(entries: List[Dict], log_path: Optional[Path] = None) -> None:
    """Append one line per entry (one tab or Drive file a command wrote)."""
    if not entries:
        return
    path = log_path or state_files.PROVENANCE_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, default=str) + "\n")
