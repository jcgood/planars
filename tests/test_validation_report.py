"""Tests for coding/validation_report.py — the sheet-validation issue builder.

This logic decides what lands in the coordinator's GitHub inbox every morning,
which is why it lives in a tested module rather than in a shell heredoc inside
the workflow. Each behaviour below traces to something issue #260 got wrong:
a crash line that wasn't the crash, three unrelated problems accumulating on
one issue, and an advisory warning holding that issue open for days after the
problem it was named for had been fixed.
"""
from __future__ import annotations

from coding.validation_report import (
    ValidationReport,
    build_issue_body,
    issue_title,
    parse_report,
    read_fingerprint,
)

# A crash as the workflow actually captures it: the traceback arrives on stderr
# and lands at the TOP, while ordinary stdout keeps going below it. Walking
# backwards from the end — what the old extractor did — finds the last line of
# normal output and reports it as the exception.
CRASH_LOG = """Traceback (most recent call last):
  File "<frozen runpy>", line 203, in _run_module_as_main
  File "coding/validate_coding.py", line 95, in highlight_cells
    _with_retry(lambda: ws.spreadsheet.batch_update({"requests": requests}))
gspread.exceptions.APIError: APIError: [400]: Invalid requests[21].updateCells: \
Range (flapping!D131) exceeds grid limits. Max rows: 111, max columns: 8
Connecting to Google APIs...

stan1293
  [segmental/aspiration_prominence] 108 blank cell(s) — annotation in progress
"""

ERROR_LOG = """Connecting to Google APIs...

stan1293
  Diagnostics validation (1 issue(s)):
    [WARNING] row 12: Class 'phrasal_accent' has no corresponding planars/ analysis module
  [phrasal_accent/general] 3 issue(s):
    [ERROR] general: missing structural column 'Element_A'
    [ERROR] general: missing structural column 'Element_B'
    [WARNING] general row 2 '? × ?': unexpected value 'also' in 'Element'
    [WARNING] general row 3 '? × ?': unexpected value 'and' in 'Element'
"""

WARNINGS_ONLY_LOG = """Connecting to Google APIs...

stan1293
  Diagnostics validation (1 issue(s)):
    [WARNING] row 12: Class 'phrasal_accent' has no corresponding planars/ analysis module
"""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def test_crash_line_is_the_exception_not_the_last_line_of_output():
    """#260's body said "crashed" and then showed a routine blank-cell count."""
    report = parse_report(CRASH_LOG)
    assert report.crash is not None
    assert report.crash.startswith("gspread.exceptions.APIError")
    assert "exceeds grid limits" in report.crash
    assert "blank cell" not in report.crash


def test_issues_are_attributed_to_language_and_section():
    report = parse_report(ERROR_LOG)
    assert len(report.errors) == 2
    assert len(report.warnings) == 3
    assert {i.section for i in report.errors} == {"phrasal_accent/general"}
    assert {i.lang for i in report.issues} == {"stan1293"}
    assert any(i.section == "diagnostics" for i in report.warnings)


# ---------------------------------------------------------------------------
# What warrants an issue
# ---------------------------------------------------------------------------

def test_warnings_alone_do_not_warrant_an_issue():
    """The change that would have let #260 close on its second day.

    'phrasal_accent has no analysis module' is a deliberate, tracked gap
    (#237). It recurs daily and would hold an issue open indefinitely.
    """
    assert parse_report(WARNINGS_ONLY_LOG).should_file() is False


def test_errors_and_crashes_do_warrant_an_issue():
    assert parse_report(ERROR_LOG).should_file() is True
    assert parse_report(CRASH_LOG).should_file() is True


# ---------------------------------------------------------------------------
# Fingerprinting — is this the same problem or a different one?
# ---------------------------------------------------------------------------

def test_same_problem_more_occurrences_is_the_same_fingerprint():
    """Row numbers and counts change daily; the problem is the same."""
    more = ERROR_LOG.replace("general row 2", "general row 47")
    assert parse_report(ERROR_LOG).fingerprint() == parse_report(more).fingerprint()


def test_a_different_problem_gets_a_different_fingerprint():
    """The reason #260 should have been superseded rather than commented on."""
    other = ERROR_LOG.replace("missing structural column 'Element_A'",
                              "header differs from local TSV")
    assert parse_report(ERROR_LOG).fingerprint() != parse_report(other).fingerprint()


def test_warning_churn_does_not_change_the_fingerprint():
    """Only errors identify the problem — warnings ride along as context."""
    noisier = ERROR_LOG + "    [WARNING] general row 9 '? × ?': unexpected value 'x' in 'Element'\n"
    assert parse_report(ERROR_LOG).fingerprint() == parse_report(noisier).fingerprint()


def test_a_crash_is_fingerprinted_by_its_exception_not_its_line_numbers():
    moved = CRASH_LOG.replace('line 95', 'line 132').replace("D131", "D145")
    assert parse_report(CRASH_LOG).fingerprint() == parse_report(moved).fingerprint()


def test_fingerprint_round_trips_through_the_issue_body():
    report = parse_report(ERROR_LOG)
    assert read_fingerprint(build_issue_body(report, "2026-08-02")) == report.fingerprint()


def test_read_fingerprint_tolerates_an_old_issue_without_one():
    assert read_fingerprint("## What's wrong\n\nsomething") is None
    assert read_fingerprint("") is None


# ---------------------------------------------------------------------------
# The body a person reads
# ---------------------------------------------------------------------------

def test_title_names_the_problem_not_just_the_date():
    """#260 was titled for a crash that had been fixed two days earlier."""
    assert issue_title(parse_report(ERROR_LOG), "2026-08-02") == (
        "Sheet validation: 2 errors in stan1293 phrasal_accent/general — 2026-08-02")
    assert issue_title(parse_report(CRASH_LOG), "2026-08-02") == (
        "Sheet validation crashed — 2026-08-02")


def test_repeated_warnings_are_collapsed_with_a_count():
    """A real run produced 429 near-identical lines. Nobody reads that."""
    many = ERROR_LOG + "".join(
        f"    [WARNING] general row {i} '? × ?': unexpected value 'w{i}' in 'Element'\n"
        for i in range(10, 200))
    body = build_issue_body(parse_report(many), "2026-08-02")
    assert "and 191 more like it" in body
    # Count only the summary; the full log below deliberately keeps every line.
    summary = body.split("## Full log")[0]
    assert summary.count("unexpected value") < 5


def test_errors_come_first_and_warnings_are_marked_non_blocking(  ):
    body = build_issue_body(parse_report(ERROR_LOG), "2026-08-02")
    assert body.index("What's wrong") < body.index("Advisory warnings")
    assert "not blocking" in body
    assert "missing structural column" in body


def test_structural_errors_get_structural_advice(  ):
    """Not 'correct the pink cells' — no cell edit fixes a wrong row shape."""
    body = build_issue_body(parse_report(ERROR_LOG), "2026-08-02")
    assert "Wrong row structure" in body
    assert "Do not fix this by editing cells" in body


def test_crash_body_says_no_data_needs_correcting():
    body = build_issue_body(parse_report(CRASH_LOG), "2026-08-02")
    assert "infrastructure error" in body
    assert "_No annotation data needs to be corrected._" in body
    assert "exceeds grid limits" in body


def test_full_log_is_always_included():
    for log in (CRASH_LOG, ERROR_LOG):
        body = build_issue_body(parse_report(log), "2026-08-02")
        assert "<details><summary>Show full validation output</summary>" in body
        assert log.strip().splitlines()[-1] in body


def test_empty_report_is_clean():
    report = parse_report("Connecting to Google APIs...\n\nstan1293\n  no issues\n")
    assert report.issues == [] and report.crash is None
    assert report.should_file() is False


def test_section_prefix_is_not_repeated_in_the_message():
    body = build_issue_body(parse_report(ERROR_LOG), "2026-08-02")
    assert "`phrasal_accent/general`: missing structural column" in body
    assert "general: general:" not in body
