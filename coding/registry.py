"""`python -m coding registry` -- the derived command inventory (Phase 5 unit C, issue #271).

Joins two things that used to only exist separately, each already
authoritative for its own half: `coding/__main__.py`'s `_COMMANDS` table plus
every command module's `build_parser()` (Phase 5 unit A/B -- what flags a
command takes) with `data_dependency_schema/operations.yaml` (Phase 4 --
what a command does, its side effects, idempotency, preconditions, and
ordering relative to other commands). Neither of those has ever been
duplicated into this file: build_registry() calls build_parser() and reads
operations.yaml fresh on every invocation, so there is nothing here to go
stale. This is the "must be derived, never hand-authored" registry the plan
(docs/data-layer-implementation-plan.md, Phase 5) asks for -- a hand-authored
inventory is worse than none, because a stale map gets trusted.

Run:
    python -m coding registry                    # one line per command
    python -m coding registry --command CMD       # full detail on one command
"""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
OPERATIONS_PATH = ROOT / "data_dependency_schema" / "operations.yaml"


def _load_operations() -> Dict[str, Dict]:
    """Return operations.yaml records keyed by id, read fresh every call.

    Deliberately uncached (Phase 8, issue #271, found by the idempotency
    audit) -- an earlier version cached the parsed file in a module-level
    global after its first read, which directly contradicted this file's
    own repeated claim that nothing here can go stale within a process.
    Harmless for the ordinary `python -m coding registry` invocation (a
    fresh process every time, so the cache started empty regardless), but a
    real gap for anything importing this module and calling
    `build_registry()` more than once in the same process -- exactly the
    shape a test suite has. The file is small; re-reading it every call
    costs nothing worth trading freshness for.
    """
    with open(OPERATIONS_PATH, encoding="utf-8") as f:
        records = yaml.safe_load(f) or []
    return {r["id"]: r for r in records}


def _flags_from_parser(parser: argparse.ArgumentParser) -> List[Dict]:
    """Describe a parser's non-help arguments: flags/dest/help/required/default."""
    flags = []
    for action in parser._actions:
        if action.dest == "help":
            continue
        flags.append({
            "option_strings": list(action.option_strings),  # [] for a positional
            "dest": action.dest,
            "help": action.help or "",
            "required": bool(action.required),
            "default": None if action.default is argparse.SUPPRESS else action.default,
        })
    return flags


def build_registry() -> List[Dict]:
    """One entry per `coding/__main__.py` command, joining its live argparse
    spec with its operations.yaml record. Recomputed fresh every call --
    nothing here is cached, so it cannot drift from either source.
    """
    from coding.__main__ import _COMMANDS

    operations = _load_operations()
    entries = []
    for cli_command, module_name in sorted(_COMMANDS.items()):
        op_id = cli_command.replace("-", "_")
        mod = importlib.import_module(module_name)
        parser = mod.build_parser()
        record = operations.get(op_id)
        entries.append({
            "cli_command": cli_command,
            "module": module_name,
            "flags": _flags_from_parser(parser),
            "operation": record,  # None if no matching record -- reported, not hidden
        })
    return entries


def _format_summary(entries: List[Dict]) -> str:
    lines = []
    for entry in entries:
        record = entry["operation"]
        description = record["description"] if record else "[no operations.yaml record]"
        lines.append(f"{entry['cli_command']:<40} {description}")
    return "\n".join(lines)


def _format_detail(entry: Dict) -> str:
    record = entry["operation"]
    lines = [f"{entry['cli_command']}  ({entry['module']})", ""]

    if entry["flags"]:
        lines.append("Flags:")
        for flag in entry["flags"]:
            name = ", ".join(flag["option_strings"]) or f"<{flag['dest']}>"
            req = " (required)" if flag["required"] else ""
            lines.append(f"  {name}{req}")
            if flag["help"]:
                lines.append(f"      {flag['help']}")
        lines.append("")
    else:
        lines.append("Flags: none\n")

    if record is None:
        lines.append("[no operations.yaml record for this command]")
        return "\n".join(lines)

    lines.append(f"Description: {record['description']}")
    lines.append(f"Apply gate: {record['apply_gate']}")
    lines.append(f"Writes to Drive: {record['writes_to_drive']}")
    lines.append(f"Idempotent: {record['idempotent']}")
    lines.append(f"  {record['idempotency_note']}")
    lines.append("Side effects:")
    for effect in record["side_effects"]:
        lines.append(f"  - {effect}")
    if record["preconditions"]:
        lines.append(f"Preconditions: {', '.join(record['preconditions'])}")
    if record["facts_touched"]:
        lines.append("Facts touched:")
        for ft in record["facts_touched"]:
            lines.append(f"  - {ft['fact']} ({ft['role']})")
    if record["cascades_triggered"]:
        lines.append("Cascades triggered:")
        for cascade in record["cascades_triggered"]:
            lines.append(f"  - {cascade}")
    if record["ordering_constraints"]:
        lines.append("Ordering constraints:")
        for constraint in record["ordering_constraints"]:
            lines.append(f"  - {constraint}")
    if record["modes"]:
        lines.append(f"Modes: {', '.join(m['name'] for m in record['modes'])}")
        lines.append("  (run with a mode-specific command to see its own overrides;")
        lines.append("   see data_dependency_schema/operations.yaml directly for now)")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for `python -m coding registry`."""
    ap = argparse.ArgumentParser(
        description="Show the derived command inventory (flags joined with operations.yaml)."
    )
    ap.add_argument(
        "--command", metavar="CLI_COMMAND",
        help="show full detail for one command, e.g. --command generate-sheets",
    )
    return ap


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_parser().parse_args()

    entries = build_registry()

    if args.command:
        matches = [e for e in entries if e["cli_command"] == args.command]
        if not matches:
            available = ", ".join(e["cli_command"] for e in entries)
            raise SystemExit(
                f"Unknown command {args.command!r}. Available: {available}"
            )
        print(_format_detail(matches[0]))
        return

    print(_format_summary(entries))
    print(f"\n{len(entries)} command(s). Use --command CLI_COMMAND for full detail.")
