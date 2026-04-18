"""Regression tests for treeTraversal.py.

These tests capture stdout from main() and compare it against snapshot files
in tests/snapshots/. The goal is change detection: when a bug fix alters
analytical output, the diff surfaces it for review rather than silently
accepting or rejecting it.

To update snapshots after a deliberate change:
    pytest --update-snapshots

Domain files that hang in the current code are marked xfail; once the
underlying bugs are fixed they should be promoted to normal test cases.
"""

import io
import os
import sys
import pytest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
DOMAINS_DIR = Path(__file__).parent.parent / "domains"

sys.path.insert(0, str(SCRIPTS_DIR))
import treeTraversal


# ── Test cases ──────────────────────────────────────────────────────────────
# Each entry: (domain_file, expected_to_hang)
# known_hang=True marks the test xfail so it's reported but doesn't block CI.

CASES = [
    ("domains_nyan1308.tsv", False,  None),
    ("domains_yupik.tsv",    False,  None),
    ("domains_mart.tsv",     False,  "data error: Size=28 but Right-Left+1=27 in row 12"),
    ("domains_chac.tsv",     True,   "known hang: getEnclosingParent bug"),
    ("catalanPlus.tsv",      True,   "known hang: cause not yet confirmed"),
]


def run_main(domain_file, tmp_path):
    """Call main() and return its stdout as a string."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        treeTraversal.main(
            domain_file=domain_file,
            domains_dir=str(DOMAINS_DIR),
            output_dir=str(tmp_path),
        )
    return buf.getvalue()


def snapshot_path(domain_file):
    stem = domain_file.replace(".tsv", "")
    return SNAPSHOTS_DIR / f"{stem}.txt"


# ── Parametrized test ────────────────────────────────────────────────────────

@pytest.mark.parametrize("domain_file,known_hang,xfail_reason", CASES)
def test_output_matches_snapshot(domain_file, known_hang, xfail_reason, tmp_path, request):
    if known_hang:
        pytest.xfail(f"{domain_file}: known hang — fix bugs before enabling")
    if xfail_reason:
        pytest.xfail(f"{domain_file}: {xfail_reason}")

    snap = snapshot_path(domain_file)

    update = request.config.getoption("--update-snapshots", default=False)

    actual = run_main(domain_file, tmp_path)

    if update:
        snap.write_text(actual)
        pytest.skip(f"Snapshot updated: {snap.name}")

    if not snap.exists():
        pytest.fail(
            f"No snapshot for {domain_file}. "
            f"Run with --update-snapshots to create one."
        )

    expected = snap.read_text()

    # If they differ, show a readable summary rather than dumping thousands of lines.
    if actual != expected:
        actual_lines = actual.splitlines()
        expected_lines = expected.splitlines()
        first_diff = next(
            (i for i, (a, e) in enumerate(zip(actual_lines, expected_lines)) if a != e),
            min(len(actual_lines), len(expected_lines)),
        )
        pytest.fail(
            f"Output changed for {domain_file}.\n"
            f"  Expected {len(expected_lines)} lines, got {len(actual_lines)} lines.\n"
            f"  First difference at line {first_diff + 1}:\n"
            f"    expected: {expected_lines[first_diff] if first_diff < len(expected_lines) else '<missing>'}\n"
            f"    actual:   {actual_lines[first_diff] if first_diff < len(actual_lines) else '<missing>'}\n"
            f"Re-run with --update-snapshots if this change is intentional."
        )
