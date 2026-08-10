"""Stamp qualification_rule_hash in diagnostic_classes_status.yaml.

The hash is SHA-256[:8] of the whitespace-normalised qualification_rule text.
Running this after Claude has updated a module records that the code has been
verified against the current rule text. qualification_rule itself lives in
diagnostic_classes.yaml (research); qualification_rule_hash lives in
diagnostic_classes_status.yaml (process/tracking) — split in Phase 3 of the
data layer redesign (issue #271). This script reads the rule from one file
and stamps the hash into the other.

Usage:
    python -m coding sync-qualification-hashes                       # dry run: show what would change
    python -m coding sync-qualification-hashes --apply               # stamp all stale/missing hashes
    python -m coding sync-qualification-hashes --apply --class metrical   # one class only
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CLASSES_YAML = ROOT / "schemas" / "diagnostic_classes.yaml"
STATUS_YAML = ROOT / "schemas" / "diagnostic_classes_status.yaml"


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _compute_hash(qualification_rule: str) -> str:
    return hashlib.sha256(_normalize(qualification_rule).encode()).hexdigest()[:8]


def _collect_wanted(target_class: str | None) -> dict[str, str]:
    """Return {class_name: expected_hash} for all classes with a qualification_rule."""
    data = yaml.safe_load(CLASSES_YAML.read_text(encoding="utf-8"))
    wanted: dict[str, str] = {}
    for cls in data.get("classes", []):
        name = cls.get("name", "")
        if target_class and name != target_class:
            continue
        qr = cls.get("qualification_rule", "")
        if qr:
            wanted[name] = _compute_hash(qr)
    return wanted


def _current_hashes(target_class: str | None, wanted: dict[str, str]) -> dict[str, str | None]:
    """Return {class_name: current_hash_or_None} for classes in `wanted`."""
    data = yaml.safe_load(STATUS_YAML.read_text(encoding="utf-8"))
    by_name = {cls.get("name", ""): cls for cls in data.get("classes", [])}
    result: dict[str, str | None] = {}
    for name in wanted:
        result[name] = by_name.get(name, {}).get("qualification_rule_hash")
    return result


def _apply_hashes(wanted: dict[str, str]) -> None:
    """Write hash updates to STATUS_YAML using text-level manipulation to preserve comments.

    Unlike diagnostic_classes.yaml's old qualification_rule field,
    qualification_rule_hash here is always a plain single-line scalar (never a
    multi-line block). An existing `qualification_rule_hash:` line is updated
    in place wherever it already sits in the class's field order; only a
    class missing the field entirely gets a new line, appended at the end of
    its block (just before the next class starts).
    """
    lines = STATUS_YAML.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []

    current_class: str | None = None
    hash_written = False

    def _flush_missing_hash():
        if current_class in wanted and not hash_written:
            out.append(f'    qualification_rule_hash: "{wanted[current_class]}"\n')

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip("\n")
        line_indent = len(stripped) - len(stripped.lstrip())

        if stripped.lstrip().startswith("- name:") and line_indent == 2:
            _flush_missing_hash()
            current_class = stripped.split("- name:", 1)[1].strip()
            hash_written = False
            out.append(line)
            i += 1
            continue

        if current_class and current_class in wanted:
            key = stripped.lstrip()
            if key.startswith("qualification_rule_hash:") and line_indent == 4:
                out.append(f'    qualification_rule_hash: "{wanted[current_class]}"\n')
                hash_written = True
                i += 1
                continue

        out.append(line)
        i += 1

    _flush_missing_hash()
    STATUS_YAML.write_text("".join(out), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stamp qualification_rule_hash in diagnostic_classes_status.yaml."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write updated hashes to diagnostic_classes_status.yaml (dry run by default)."
    )
    parser.add_argument(
        "--class", dest="target_class", metavar="CLASS",
        help="Restrict to one analysis class (e.g. --class metrical)."
    )
    args = parser.parse_args()

    wanted = _collect_wanted(args.target_class)
    current = _current_hashes(args.target_class, wanted)

    stale = [(name, wanted[name], current.get(name)) for name in wanted if current.get(name) != wanted[name]]

    if not stale:
        print("All qualification_rule_hash fields are up to date.")
        sys.exit(0)

    for name, expected, cur in stale:
        if cur is None:
            print(f"  + [{name}] missing → will stamp {expected!r}")
        else:
            print(f"  ~ [{name}] {cur!r} → {expected!r}")

    if not args.apply:
        print(f"\n{len(stale)} hash(es) need updating. Re-run with --apply to write.")
        sys.exit(1)

    _apply_hashes(wanted)
    print(f"\nStamped {len(stale)} hash(es) in {STATUS_YAML.relative_to(ROOT)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
