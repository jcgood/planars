"""Generate a coordinator-facing Claude prompt for modules with stale or missing hashes.

For each module whose qualification_rule_hash is absent or wrong, this script
emits a ready-to-paste prompt that includes:
  - the current qualification_rule text from diagnostic_classes.yaml
  - the current module source (or a note that the module does not exist yet)
  - explicit instructions (update logic, update docstring, run tests)
  - the exact sync-qualification-hashes command to run after Claude is done

Usage:
    python -m coding generate-rule-update-prompt metrical   # one class
    python -m coding generate-rule-update-prompt            # all stale classes
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CLASSES_YAML = ROOT / "schemas" / "diagnostic_classes.yaml"
PLANARS_DIR = ROOT / "planars"


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _compute_hash(qualification_rule: str) -> str:
    return hashlib.sha256(_normalize(qualification_rule).encode()).hexdigest()[:8]


def _load_classes() -> list[dict]:
    data = yaml.safe_load(CLASSES_YAML.read_text(encoding="utf-8"))
    return data.get("classes", [])


def _module_source(name: str) -> str | None:
    """Return source text of planars/{name}.py, or None if it doesn't exist."""
    path = PLANARS_DIR / f"{name}.py"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _stale_classes(target: str | None) -> list[dict]:
    """Return class dicts whose qualification_rule_hash is missing or wrong."""
    stale = []
    for cls in _load_classes():
        name = cls.get("name", "")
        if target and name != target:
            continue
        qr = cls.get("qualification_rule", "")
        if not qr:
            continue
        expected = _compute_hash(qr)
        current = cls.get("qualification_rule_hash")
        if current != expected:
            stale.append(cls)
    return stale


def _generate_prompt(cls: dict) -> str:
    name = cls["name"]
    display = cls.get("display_name", name)
    qr = cls["qualification_rule"].strip()
    source = _module_source(name)
    sync_cmd = f"python -m coding sync-qualification-hashes --apply --class {name}"

    lines = []
    lines.append(f"# Qualification rule update: `{name}` ({display})")
    lines.append("")
    lines.append("## Task")
    lines.append("")

    if source is None:
        lines.append(
            f"The analysis module `planars/{name}.py` does not exist yet. "
            f"Write it from scratch to implement the qualification rule below."
        )
    else:
        lines.append(
            f"The qualification rule for `{name}` in `schemas/diagnostic_classes.yaml` "
            f"has changed. Review and update `planars/{name}.py` to implement the new rule."
        )

    lines.append("")
    lines.append("**What to do:**")
    if source is None:
        lines.append(
            f"1. Write `planars/{name}.py` — expose `derive_{name}_domains()` (or "
            f"equivalent) and `format_result()`, matching the patterns in other modules."
        )
        lines.append(
            "2. Add a `derive` alias pointing to the primary derive function "
            "(see `planars/ciscategorial.py` for the pattern)."
        )
        lines.append(
            "3. Add a `Qualification rule (mirrors diagnostic_classes.yaml)` docstring "
            "section containing the rule text verbatim."
        )
        lines.append("4. Run `pytest` to verify tests pass.")
    else:
        lines.append("1. Update the module logic to match the new qualification rule.")
        lines.append(
            "2. Update the `Qualification rule (mirrors diagnostic_classes.yaml)` "
            "docstring section to contain the new rule text verbatim."
        )
        lines.append("3. Run `pytest` to verify tests pass.")

    final_step = 5 if source is None else 4
    lines.append(
        f"{final_step}. After Claude is done, run:\n"
        f"   ```bash\n"
        f"   {sync_cmd}\n"
        f"   ```\n"
        f"   This stamps the new hash in `diagnostic_classes.yaml`, confirming the code "
        f"was verified against the current rule."
    )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Current qualification rule (from `schemas/diagnostic_classes.yaml`)")
    lines.append("")
    lines.append("```")
    lines.append(qr)
    lines.append("```")

    if source is not None:
        lines.append("")
        lines.append(f"## Current module source (`planars/{name}.py`)")
        lines.append("")
        lines.append("```python")
        lines.append(source.rstrip())
        lines.append("```")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate coordinator-facing Claude prompts for stale qualification rules."
    )
    parser.add_argument(
        "class_name", nargs="?", metavar="CLASS",
        help="Generate prompt for one class only (omit for all stale classes)."
    )
    args = parser.parse_args()

    stale = _stale_classes(args.class_name)

    if not stale:
        if args.class_name:
            print(f"[{args.class_name}] qualification_rule_hash is current — no prompt needed.")
        else:
            print("All qualification_rule_hash fields are current — no prompts needed.")
        sys.exit(0)

    for cls in stale:
        print(_generate_prompt(cls))
        print("\n" + "=" * 72 + "\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
