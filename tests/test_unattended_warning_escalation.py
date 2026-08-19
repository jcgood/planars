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

A line-number shift from an unrelated edit will make an entry in
_KNOWN_SITES stop matching — expected, not a bug in this test. Re-locate the
print and update the entry; same one-line effort as classifying a genuinely
new one, and test_known_sites_have_not_gone_stale below catches it.
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


def _warning_sites(module_name: str) -> Set[Tuple[str, int]]:
    path = CODING / module_name
    if not path.exists():
        return set()
    return {
        (module_name, i)
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if _WARNING_PRINT.search(line)
    }


def _all_warning_sites() -> Set[Tuple[str, int]]:
    found: Set[Tuple[str, int]] = set()
    for mod in _unattended_modules():
        found |= _warning_sites(mod)
    return found


# Every warning-shaped print() known to exist, as of issue #283's sweep
# (2026-08-17), in a module an unattended workflow command reaches.
_KNOWN_SITES: Dict[Tuple[str, int], str] = {
    ("import_sheets.py", 699): "advisory-only ([planar] validation issue); reaches "
        "$GITHUB_STEP_SUMMARY only, never affects exit code -- gap in issue #283",
    ("import_sheets.py", 752): "advisory-only ([diagnostics] validation issue); "
        "same as above -- gap in issue #283",
    ("import_sheets.py", 917): "accumulated into lang_warning_lines, written to "
        "import_errors/*.txt -- gitignored, never read in CI -- gap in issue #283",
    ("import_sheets.py", 931): "same mechanism as 917 -- gap in issue #283",
    ("import_sheets.py", 989): "same mechanism as 917 -- gap in issue #283",
    ("import_sheets.py", 997): "same mechanism as 917 (this one IS a blocking "
        "warning on a ready-for-review tab) -- gap in issue #283",
    ("sync_diagnostics_yaml.py", 100): "never affects exit code, and the workflow "
        "step doesn't capture this command's output at all -- worst gap in issue "
        "#283 (the ERROR case on the next line is equally invisible)",
    ("sync_params.py", 440): "only reachable via --split, never passed by the "
        "automated workflow invocation (plain `sync-params --apply`)",
    ("sync_params.py", 461): "only reachable via --merge, same reasoning as 440",
    ("generate_sheets.py", 326): "inside _prefill_free_occurrence_rows -- only "
        "reachable via the interactive --apply sheet-creation path, not "
        "--regen-dependents (the only generate-sheets invocation the workflow runs)",
    ("generate_sheets.py", 329): "same function/reasoning as 326",
    ("generate_sheets.py", 332): "same function/reasoning as 326",
    ("generate_sheets.py", 335): "same function/reasoning as 326",
    ("generate_sheets.py", 389): "same reasoning as 326 (Elements not found check, "
        "same sheet-creation path)",
    ("generate_sheets.py", 921): "inside _build_phrasal_accent_pairs, called by "
        "_regen_construction -- possibly reachable via --regen-dependents if a "
        "phrasal_accent construction is ever a depends_on target; not fully traced, "
        "treat conservatively rather than assumed safe",
    ("generate_sheets.py", 2545): "inside the interactive language-onboarding path "
        "(folder sharing) -- not --regen-dependents",
    ("generate_sheets.py", 2558): "inside the interactive language-onboarding path "
        "(notes doc creation) -- not --regen-dependents",
    ("generate_sheets.py", 2634): "inside the interactive language-onboarding path "
        "(Glottolog fetch) -- not --regen-dependents",
    ("integrity_check.py", 945): "deliberately silent by design -- see the code "
        "comment: defers to import-sheets' own import-error issue if Drive is "
        "genuinely down",
    ("validate_coding.py", 664): "advisory warning under sheet-validation.yml, "
        "whose documented convention (CLAUDE.md's sheet-validation label entry) is "
        "that advisory warnings are context only, never file/hold an issue",
    ("validate_coding.py", 745): "redundant with the pending-changes issue "
        "import-sheets already files for the same underlying fact",
    ("update_sheets.py", 433): "correctly escalated: sets any_drift, which drives "
        "exit 1, which the sheet-drift issue mechanism dumps in full -- not a gap",
    ("apply_pending.py", 193): "apply-pending is coordinator-only, never actually "
        "run unattended -- it's in _unattended_commands() only because the workflow "
        "recommends it inside a `gh issue comment --body` string (data-refresh.yml "
        "line ~239), which the heredoc stripper doesn't catch since it isn't a "
        "Python heredoc. Harmless over-inclusion, kept classified for honesty.",
    ("__main__.py", 54): "redundant with the pending-changes issue import-sheets "
        "already files for the same underlying fact",
    ("drive.py", 199): "Phase 6 boundary 4 (issue #271) -- upload_manifest()'s "
        "own non-blocking manifest_contract.check() warning. Deliberately never "
        "blocks the write (see manifest_contract.py's module docstring); real "
        "tracking happens separately via integrity-check's MANIFEST SHAPE "
        "section, which does drive a trackable integrity-error -- this print is "
        "only the in-the-moment signal, by design, not a gap",
    ("drive.py", 225): "self-healing -- every upload_manifest() caller updates "
        "drive_config.json's _planars_config_file_id to the new file. Leaves the "
        "old manifest.json orphaned in Drive; low severity, not addressed",
    ("drive.py", 270): "found by this test's own regex, not the original manual "
        "sweep (issue #283 predates this entry) -- load_manifest()'s merged-config "
        "parse failure, falls back to the old per-language format silently. Never "
        "affects exit code, no capture in the workflow. Arguably the most "
        "consequential site in this whole file, since load_manifest() runs first "
        "in nearly every command -- filed as a follow-up to #283",
    ("drive.py", 595): "deliberately non-raising by design -- see the code comment "
        "on _autocommit_data: the commit already succeeded locally, only the "
        "remote lags until a manual `git push` retry",
    ("import_sheets.py", 1069): "summary count ('N warning(s)'), not an "
        "independent site -- reflects warnings already tracked at 917/931/989/997",
    ("integrity_check.py", 1011): "footer summary line; its leading ✗ is exactly "
        "what the integrity-error issue-filing step scans for -- part of the "
        "escalation mechanism, not a gap",
    ("integrity_check.py", 1013): "footer summary line, the all-clear case (total_e "
        "== 0) -- not a gap",
    ("validation_report.py", 319): "diagnostic key=value dump (this file's own "
        "--debug-style output), not a runtime warning alert -- 'warnings' here is "
        "a variable name/count being printed",
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
    # The inverse check: an entry whose (file, line) no longer matches a
    # warning print is either stale (the print moved or was removed) or was
    # never real. Keeps _KNOWN_SITES honest instead of growing forever.
    stale = set(_KNOWN_SITES) - _all_warning_sites()
    assert not stale, (
        "These _KNOWN_SITES entries no longer match a warning print at that "
        f"location -- the line moved or was removed. Update or delete: {sorted(stale)}"
    )
