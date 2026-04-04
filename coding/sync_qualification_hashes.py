"""Stamp qualification_rule_hash in diagnostic_classes.yaml.

The hash is SHA-256[:8] of the whitespace-normalised qualification_rule text.
Running this after Claude has updated a module records that the code has been
verified against the current rule text.

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


def _current_hashes(target_class: str | None) -> dict[str, str | None]:
    """Return {class_name: current_hash_or_None} for all classes with a qualification_rule."""
    data = yaml.safe_load(CLASSES_YAML.read_text(encoding="utf-8"))
    result: dict[str, str | None] = {}
    for cls in data.get("classes", []):
        name = cls.get("name", "")
        if target_class and name != target_class:
            continue
        if cls.get("qualification_rule", ""):
            result[name] = cls.get("qualification_rule_hash")
    return result


def _apply_hashes(wanted: dict[str, str], current: dict[str, str | None]) -> None:
    """Write hash updates to CLASSES_YAML using text-level manipulation to preserve comments."""
    lines = CLASSES_YAML.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []

    current_class: str | None = None
    in_qr_block = False      # currently consuming qualification_rule scalar lines
    qr_block_indent = 0      # indentation of qualification_rule: key
    hash_inserted = False    # whether we already wrote hash for current_class
    pending_insert: str | None = None   # hash line to insert at end of qr block

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip("\n")

        # Detect class boundaries (lines like "  - name: classname")
        if stripped.lstrip().startswith("- name:"):
            # Flush any pending insert before moving to a new class
            if pending_insert is not None:
                out.append(pending_insert)
                pending_insert = None
            current_class = stripped.split("- name:", 1)[1].strip()
            in_qr_block = False
            hash_inserted = False
            out.append(line)
            i += 1
            continue

        if current_class and current_class in wanted:
            key = stripped.lstrip()

            # Detect start of qualification_rule block
            if key.startswith("qualification_rule:") and not key.startswith("qualification_rule_hash:"):
                qr_block_indent = len(stripped) - len(stripped.lstrip())
                in_qr_block = True
                out.append(line)
                i += 1
                continue

            if in_qr_block:
                # A line that is blank OR indented more than qr_block_indent is part of the block
                stripped_content = stripped.lstrip()
                line_indent = len(stripped) - len(stripped_content) if stripped_content else 999
                if not stripped_content or line_indent > qr_block_indent:
                    out.append(line)
                    i += 1
                    continue
                else:
                    # End of qr block: this line is the next field at same indent
                    in_qr_block = False
                    expected = wanted[current_class]

                    if key.startswith("qualification_rule_hash:"):
                        # Replace the existing hash value
                        hash_inserted = True
                        out.append(f"{'  ' * (qr_block_indent // 2)}    qualification_rule_hash: \"{expected}\"\n")
                        i += 1
                        continue
                    else:
                        # No existing hash — insert before this line
                        if not hash_inserted:
                            out.append(f"{' ' * qr_block_indent}qualification_rule_hash: \"{expected}\"\n")
                            hash_inserted = True
                        out.append(line)
                        i += 1
                        continue

            # Handle qualification_rule_hash that appears after the qr block
            # (e.g. already exists; we may need to update it)
            if key.startswith("qualification_rule_hash:"):
                expected = wanted[current_class]
                hash_inserted = True
                out.append(f"{' ' * qr_block_indent}qualification_rule_hash: \"{expected}\"\n")
                i += 1
                continue

        out.append(line)
        i += 1

    # Flush any trailing pending insert (shouldn't happen but be safe)
    if pending_insert is not None:
        out.append(pending_insert)

    CLASSES_YAML.write_text("".join(out), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stamp qualification_rule_hash in diagnostic_classes.yaml."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write updated hashes to diagnostic_classes.yaml (dry run by default)."
    )
    parser.add_argument(
        "--class", dest="target_class", metavar="CLASS",
        help="Restrict to one analysis class (e.g. --class metrical)."
    )
    args = parser.parse_args()

    wanted = _collect_wanted(args.target_class)
    current = _current_hashes(args.target_class)

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

    _apply_hashes(wanted, current)
    print(f"\nStamped {len(stale)} hash(es) in {CLASSES_YAML.relative_to(ROOT)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
