"""Warning-shaped print() calls in commands the CI workflows run unattended,
tracked against a maintained allowlist so a new one can't silently join the
pile issue #283 found.

The pattern issue #283 traced: `.github/workflows/*.yml` only escalates a
problem to a GitHub issue by checking a command's **exit code** (and, for a
few commands, matching specific line prefixes like `ERROR:`/`✗` out of its
output) — never by looking for the literal word "WARNING". A
`print("WARNING: ...")` that doesn't also make its command exit non-zero has
nowhere to go but `$GITHUB_STEP_SUMMARY` (a page nobody routinely opens) or,
for several commands, nowhere at all. Four confirmed real gaps came out of
that sweep (see issue #283); recommended fixes are written up there but not
yet applied, since they're changes to the workflow that's supposed to be the
safety net for missed problems, and couldn't be verified against a live run.

This test doesn't re-decide whether a given warning IS a gap — issue #283
did that manual tracing once, for the sites that existed then. What it does
is notice when a NEW warning-shaped print appears in a command one of these
workflows runs without a human watching, and refuse to pass until someone
adds it to _KNOWN_SITES with a one-line disposition: escalated elsewhere,
deliberately silent (with the reason), or a new gap (link the issue).
Without this, the next new print("WARNING: ...") added to import_sheets.py
or sync_diagnostics_yaml.py joins the same silent pile with nobody
noticing — the same way the sites below did before the sweep found them.

A site is identified by its module, the print line's own text (stripped),
and which occurrence of that exact text it is in the file — not by line
number. Until 2026-10-12 it was keyed by line number, so any unrelated edit
above a warning broke this test (three times in two days); now only a
change to the warning itself, or a new identical copy of it, does.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
CODING = ROOT / "coding"
WORKFLOWS = ROOT / ".github" / "workflows"

_WARNING_PRINT = re.compile(r'print\(\s*f?["\'].*?[Ww][Aa][Rr][Nn][Ii][Nn][Gg]')

# `python -m coding <command>` invocations inside the workflow YAML files.
# Heredoc Python blocks (`python3 << 'PYEOF' ... PYEOF`) are stripped first —
# those generate markdown issue-body *text* that happens to mention a command
# name as a coordinator recommendation (e.g. "run `python -m coding
# update-sheets --apply`"), not an actual unattended invocation.
_HEREDOC_BLOCK = re.compile(r"<<\s*'PYEOF'.*?^\s*PYEOF\s*$", re.DOTALL | re.MULTILINE)
_INVOCATION = re.compile(r"python -m coding ([a-z][a-z-]*)")

Site = Tuple[str, str, int]  # (module, print line text, occurrence of that text)


def _unattended_commands() -> Set[str]:
    commands: Set[str] = set()
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        text = _HEREDOC_BLOCK.sub("", wf.read_text(encoding="utf-8"))
        commands |= set(_INVOCATION.findall(text))
    return commands


def _unattended_modules() -> Set[str]:
    from coding.__main__ import _COMMANDS
    modules = {
        _COMMANDS[cmd].replace("coding.", "") + ".py"
        for cmd in _unattended_commands()
        if cmd in _COMMANDS
    }
    # drive.py (manifest upload, autocommit, load_manifest) and __main__.py's
    # _warn_pending (runs on every single invocation) are both common code
    # every command above passes through, but neither is itself a value in
    # _COMMANDS, so they'd otherwise never be scanned.
    modules.add("drive.py")
    modules.add("__main__.py")
    return modules


def _warning_sites(module_name: str) -> Set[Site]:
    path = CODING / module_name
    if not path.exists():
        return set()
    seen: Dict[str, int] = {}
    sites: Set[Site] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if _WARNING_PRINT.search(line):
            text = line.strip()
            seen[text] = seen.get(text, 0) + 1
            sites.add((module_name, text, seen[text]))
    return sites


def _all_warning_sites() -> Set[Site]:
    found: Set[Site] = set()
    for mod in _unattended_modules():
        found |= _warning_sites(mod)
    return found


# Every warning-shaped print() known to exist, as of issue #283's sweep
# (2026-08-17), in a module an unattended workflow command reaches.
_KNOWN_SITES: Dict[Site, str] = {
    ("import_sheets.py", 'print(f"  [planar] WARNING: {i}")', 1):
        "advisory-only ([planar] validation issue -- e.g. "
        "'consider type open instead of list', a Class_Type style nudge); reaches "
        "$GITHUB_STEP_SUMMARY only, never affects exit code. Deliberately left "
        "this way (issue #283, decided 2026-08-19 after reading the actual "
        "message content): these are genuine style suggestions, nothing is "
        "wrong, and filing an issue for 'consider a different Class_Type' risks "
        "the exact warning-fatigue failure mode #260 already taught this "
        "project to avoid (a routine, non-actionable warning holding an issue "
        "open for days).",
    ("import_sheets.py", 'print(f"  [diagnostics] WARNING: {i}")', 1):
        "advisory-only ([diagnostics] validation issue -- e.g. a "
        "Glottolog-verification reminder); same reasoning and same 2026-08-19 "
        "decision as the [planar] warning above.",
    ("import_sheets.py", 'print(f"    WARNING: {msg}")', 1):
        "fixed 2026-08-19 (issue #283): a spreadsheet that can't be opened at "
        "all now counts toward total_blocking_warnings, making the command exit "
        "non-zero and reach the existing import-error issue -- previously "
        "accumulated into lang_warning_lines/import_errors/*.txt (a gitignored "
        "file, never read in CI) with no effect on exit code",
    ("import_sheets.py", 'print(f"    WARNING: {msg}")', 2):
        "fixed 2026-08-19 (issue #283), same mechanism as the first occurrence "
        "of this line: a missing tab now counts toward total_blocking_warnings too",
    ("import_sheets.py", 'print(f"    WARNING: could not highlight cells: {e}")', 1):
        "the one warning in this group NOT accumulated into "
        "lang_warning_lines/total_warnings at all (a failed pink-highlight "
        "attempt after the underlying data write already succeeded) -- stays "
        "advisory-only and out of scope for issue #283's exit-code fix: purely "
        "cosmetic, no data loss if missed.",
    ("import_sheets.py", 'print(f"    WARNING: {w}")', 1):
        "fixed 2026-08-19 (issue #283): this is blocking_warnings, an "
        "invalid-value/structural problem on a ready-for-review tab -- already "
        "named 'blocking' in the code, now actually gates the exit code and "
        "reaches the existing import-error issue",
    ("sync_diagnostics_yaml.py", 'print(f"  [{lang_id}] WARNING {w.location}: {w.message}")', 1):
        "advisory-only (non-blocking WARNING-level validate_diagnostics_yaml "
        "issue); fixed 2026-08-19 alongside issue #283's worse ERROR-level gap "
        "on the next line -- the workflow step now captures this command's "
        "output to $GITHUB_STEP_SUMMARY unconditionally, and a blocking error "
        "two lines down now makes the command exit non-zero, which files a "
        "diagnostics-yaml-error issue with the same captured output attached",
    ("sync_params.py", 'print(f"WARNING: --split requires old:new1:new2, got: {args[i + 1]!r}")', 1):
        "only reachable via --split, never passed by the automated workflow "
        "invocation (plain `sync-params --apply`)",
    ("sync_params.py", 'print(f"WARNING: --merge requires old1:old2:new, got: {args[i + 1]!r}")', 1):
        "only reachable via --merge, same reasoning as --split above",
    ("generate_sheets.py", 'print(f"    [WARNING] {ni_label} exists but \'{crit}\' column is blank.")', 1):
        "inside _prefill_free_occurrence_rows (the noninterruption tab its "
        "reads_from.prefill_free names) -- only reachable via the "
        "interactive --apply sheet-creation path, not --regen-dependents (the "
        "only generate-sheets invocation the workflow runs)",
    ("generate_sheets.py", 'print(f"    [WARNING] {ni_label} is missing \'{crit}\' or \'Element\' column.")', 1):
        "same function/reasoning as the 'free column is blank' warning",
    ("generate_sheets.py", 'print(f"    [WARNING] Could not read {ni_label}: {exc}")', 1):
        "same function/reasoning as the 'free column is blank' warning",
    ("generate_sheets.py", 'print(f"    [WARNING] {ni_label} not found.")', 1):
        "same function/reasoning as the 'free column is blank' warning",
    ("generate_sheets.py", 'print(f"    [WARNING] Elements not found in noninterruption TSV: {missing}")', 1):
        "same reasoning as the 'free column is blank' warning (same "
        "sheet-creation path)",
    ("generate_sheets.py", 'print(f"    [WARNING] No {_keystone} position found for {lang_id}; "', 1):
        "inside _build_phrasal_accent_pairs, called by _regen_construction -- "
        "possibly reachable via --regen-dependents if a phrasal_accent "
        "construction is ever a depends_on target; not fully traced, treat "
        "conservatively rather than assumed safe",
    ("generate_sheets.py", 'print(f"  [WARNING] Could not share folder for {lang_id}: {_share_err}")', 1):
        "inside the interactive language-onboarding path (folder sharing) -- "
        "not --regen-dependents",
    ("generate_sheets.py", 'print(f"  [WARNING] Could not create notes doc for {lang_id}: {_notes_err}")', 1):
        "inside the interactive language-onboarding path (notes doc creation) "
        "-- not --regen-dependents",
    ("generate_sheets.py", 'print(f"  [{lid}] WARNING: Could not fetch Glottolog metadata: {exc}")', 1):
        "inside the interactive language-onboarding path (Glottolog fetch) -- "
        "not --regen-dependents",
    ("integrity_check.py", 'print(f"WARNING: Could not load manifest ({exc}) — skipping stale manifest check.")', 1):
        "deliberately silent by design -- see the code comment: defers to "
        "import-sheets' own import-error issue if Drive is genuinely down",
    ("validate_coding.py", 'print(f"  [{class_name}/{construction}] WARNING: keystone_active unresolved — treating as False")', 1):
        "advisory warning under sheet-validation.yml, whose documented "
        "convention (CLAUDE.md's sheet-validation label entry) is that advisory "
        "warnings are context only, never file/hold an issue",
    ("update_sheets.py", 'print(f"    [{construction}] WARNING: planar structure has changed:")', 1):
        "correctly escalated: sets any_drift, which drives exit 1, which the "
        "sheet-drift issue mechanism dumps in full -- not a gap",
    ("apply_pending.py", 'print(f"    WARNING: --force archives ALL existing annotations for \'{cls}\'")', 1):
        "apply-pending is coordinator-only, never actually run unattended -- "
        "it's in _unattended_commands() only because the workflow recommends it "
        "inside a `gh issue comment --body` string, which the heredoc stripper "
        "doesn't catch since it isn't a Python heredoc. Harmless "
        "over-inclusion, kept classified for honesty.",
    ("__main__.py", 'print("WARNING: Pending destructive changes require coordinator approval.")', 1):
        "redundant with the pending-changes issue import-sheets already files "
        "for the same underlying fact",
    ("drive.py", 'print(f"  WARNING: manifest being written doesn\'t match the expected shape ({len(problems)} issue(s)):")', 1):
        "Phase 6 boundary 4 (issue #271) -- upload_manifest()'s own "
        "non-blocking manifest_contract.check() warning. Deliberately never "
        "blocks the write (see manifest_contract.py's module docstring); real "
        "tracking happens separately via integrity-check's MANIFEST SHAPE "
        "section, which does drive a trackable integrity-error -- this print is "
        "only the in-the-moment signal, by design, not a gap",
    ("drive.py", 'print(f"  WARNING: could not update existing manifest.json ({e}); creating new file.")', 1):
        "self-healing -- every upload_manifest() caller updates "
        "drive_config.json's _planars_config_file_id to the new file. Leaves the "
        "old manifest.json orphaned in Drive; low severity, not addressed",
    ("drive.py", 'print(f"  Warning: could not load merged config ({exc}), falling back.")', 1):
        "found by this test's own regex, not the original manual sweep (issue "
        "#283 predates this entry) -- load_manifest()'s merged-config parse "
        "failure, falls back to the old per-language format silently. Never "
        "affects exit code, no capture in the workflow. Arguably the most "
        "consequential site in this whole file, since load_manifest() runs first "
        "in nearly every command -- filed as a follow-up to #283",
    ("drive.py", 'print(f"  WARNING: git push failed: {push.stderr.strip()}")', 1):
        "deliberately non-raising by design -- see the code comment on "
        "_autocommit_data: the commit already succeeded locally, only the "
        "remote lags until a manual `git push` retry",
    ("import_sheets.py", 'print(f"\\nDone. {total_files} file(s) written{backup_part}, {total_warnings} warning(s).")', 1):
        "summary count ('N warning(s)'), not an independent site -- reflects "
        "warnings already tracked above",
    ("import_sheets.py", 'print(f"\\n{total_blocking_warnings} blocking warning(s) found — see WARNING lines above.")', 1):
        "the exit-non-zero summary line added by issue #283's own fix "
        "(2026-08-19) -- reflects total_blocking_warnings, itself reflecting "
        "warnings already tracked above. Printed right before sys.exit(1), so "
        "unlike the 'Done.' summary it's the thing that actually makes this "
        "run's outcome reach the import-error issue, not just a count for a "
        "human reading the log.",
    ("integrity_check.py", 'print(f"  ✗  {total_e} error(s)  ·  {total_w} warning(s)")', 1):
        "footer summary line; its leading ✗ is exactly what the integrity-error "
        "issue-filing step scans for -- part of the escalation mechanism, not a gap",
    ("integrity_check.py", 'print(f"  ✓  All checks passed  ·  {total_w} warning(s)")', 1):
        "footer summary line, the all-clear case (total_e == 0) -- not a gap",
    ("validation_report.py", 'print(f"Errors: {len(report.errors)}; warnings: {len(report.warnings)}; "', 1):
        "summary count only; the same run's --apply files or updates the "
        "sheet-validation issue for any error, and lists the warnings in it as "
        "advisory context (warnings alone deliberately file nothing, #260)",
}


def test_every_unattended_warning_print_is_classified():
    unclassified = _all_warning_sites() - set(_KNOWN_SITES)
    assert not unclassified, (
        "New warning-shaped print() found in a command a CI workflow runs "
        "unattended, with no disposition recorded in _KNOWN_SITES. A plain "
        "print() here is invisible to every issue-filing mechanism in "
        ".github/workflows/*.yml unless it also makes the command exit "
        "non-zero -- see this file's module docstring and issue #283. Add an "
        "entry explaining what happens to it (escalated elsewhere / "
        f"deliberately silent, with why / a new gap, link an issue): {sorted(unclassified)}"
    )


def test_known_sites_have_not_gone_stale():
    # The inverse check: an entry whose text no longer appears as a warning
    # print is stale (the warning was reworded or removed) or was never real.
    # Keeps _KNOWN_SITES honest instead of growing forever.
    stale = set(_KNOWN_SITES) - _all_warning_sites()
    assert not stale, (
        "These _KNOWN_SITES entries no longer match a warning print -- the "
        f"warning was reworded or removed. Update or delete: {sorted(stale)}"
    )
