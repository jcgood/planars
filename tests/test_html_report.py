"""Tests for planars/html_report.py — render_language_report."""
from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
import pytest

from planars.html_report import render_language_report

ROOT = Path(__file__).resolve().parent.parent


def _minimal_bundle(
    lang_id: str = "test1234",
    completeness: dict | None = None,
    spans=None,
    lang_meta: dict | None = None,
    status: dict | None = None,
) -> dict:
    """Build a minimal language_report_data-style bundle for testing."""
    return {
        "lang_id": lang_id,
        "display_name": f"Testlang [{lang_id}]",
        "generated_at": datetime.datetime(2026, 3, 25, 12, 0, 0,
                                          tzinfo=datetime.timezone.utc),
        "completeness": completeness or {},
        "status": status,
        "spans": spans,
        "lang_meta": lang_meta,
    }


class TestRenderLanguageReport:
    def test_returns_string(self):
        html = render_language_report(_minimal_bundle())
        assert isinstance(html, str)

    def test_is_valid_html_skeleton(self):
        html = render_language_report(_minimal_bundle())
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_display_name_in_title_and_header(self):
        html = render_language_report(_minimal_bundle(lang_id="arao1248"))
        assert "arao1248" in html

    def test_timestamp_present(self):
        html = render_language_report(_minimal_bundle())
        assert "2026" in html
        assert "UTC" in html

    def test_no_completeness_data_shows_placeholder(self):
        html = render_language_report(_minimal_bundle(completeness={}))
        assert "No annotation data found" in html

    def test_no_spans_shows_no_span_data(self):
        html = render_language_report(_minimal_bundle(spans=None))
        assert "No span data available" in html

    # ------------------------------------------------------------------
    # Completeness table — normal cells
    # ------------------------------------------------------------------

    def test_filled_construction_shows_fraction(self):
        completeness = {"ciscategorial": {"general": {"total": 10, "filled": 10, "blank": 0}}}
        html = render_language_report(_minimal_bundle(completeness=completeness))
        assert "ciscategorial" in html
        assert "general" in html
        assert "10/10" in html

    def test_partial_construction_shows_blank_count(self):
        completeness = {"ciscategorial": {"general": {"total": 10, "filled": 8, "blank": 2}}}
        html = render_language_report(_minimal_bundle(completeness=completeness))
        assert "8/10" in html
        assert "2 blank" in html

    def test_zero_total_shows_no_data(self):
        completeness = {"ciscategorial": {"general": {"total": 0, "filled": 0, "blank": 0}}}
        html = render_language_report(_minimal_bundle(completeness=completeness))
        assert "no data" in html

    def test_error_construction_shows_error(self):
        completeness = {"ciscategorial": {"general": {
            "total": 0, "filled": 0, "blank": 0, "error": "could not load"
        }}}
        html = render_language_report(_minimal_bundle(completeness=completeness))
        assert "Error" in html
        assert "could not load" in html

    # ------------------------------------------------------------------
    # Completeness table — missing constructions (Layer 1)
    # ------------------------------------------------------------------

    def test_missing_construction_shows_not_started(self):
        completeness = {"ciscategorial": {"general": {
            "total": 0, "filled": 0, "blank": 0, "missing": True
        }}}
        html = render_language_report(_minimal_bundle(completeness=completeness))
        assert "not started" in html

    def test_missing_construction_does_not_show_fraction(self):
        completeness = {"ciscategorial": {"general": {
            "total": 0, "filled": 0, "blank": 0, "missing": True
        }}}
        html = render_language_report(_minimal_bundle(completeness=completeness))
        assert "0/0" not in html

    def test_missing_and_filled_in_same_class(self):
        completeness = {"ciscategorial": {
            "general": {"total": 10, "filled": 10, "blank": 0},
            "other":   {"total": 0, "filled": 0, "blank": 0, "missing": True},
        }}
        html = render_language_report(_minimal_bundle(completeness=completeness))
        assert "10/10" in html
        assert "not started" in html

    # ------------------------------------------------------------------
    # Status badges
    # ------------------------------------------------------------------

    def test_ready_for_review_badge(self):
        completeness = {"ciscategorial": {"general": {"total": 5, "filled": 5, "blank": 0}}}
        status = {"ciscategorial": {"general": "ready-for-review"}}
        html = render_language_report(_minimal_bundle(completeness=completeness, status=status))
        assert "ready for review" in html

    def test_in_progress_badge(self):
        completeness = {"ciscategorial": {"general": {"total": 5, "filled": 3, "blank": 2}}}
        status = {"ciscategorial": {"general": "in-progress"}}
        html = render_language_report(_minimal_bundle(completeness=completeness, status=status))
        assert "in progress" in html

    # ------------------------------------------------------------------
    # HTML escaping
    # ------------------------------------------------------------------

    def test_display_name_is_escaped(self):
        bundle = _minimal_bundle()
        bundle["display_name"] = '<script>alert("xss")</script>'
        html = render_language_report(bundle)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_class_name_is_escaped(self):
        completeness = {"<bad>": {"general": {"total": 1, "filled": 1, "blank": 0}}}
        html = render_language_report(_minimal_bundle(completeness=completeness))
        assert "<bad>" not in html.split("<style>")[1]  # not in body
        assert "&lt;bad&gt;" in html


class TestRenderWithRealData:
    """Smoke tests using actual coded_data/ if present."""

    @pytest.fixture(autouse=True)
    def skip_if_no_data(self):
        if not (ROOT / "coded_data").exists():
            pytest.skip("coded_data/ not present")

    def test_arao1248_report_renders(self):
        from planars.reports import language_report_data
        data = language_report_data("arao1248", source="local", repo_root=ROOT)
        html = render_language_report(data)
        assert isinstance(html, str)
        assert "arao1248" in html
        assert "<!DOCTYPE html>" in html

    def test_real_report_contains_analysis_classes(self):
        from planars.reports import language_report_data
        data = language_report_data("arao1248", source="local", repo_root=ROOT)
        html = render_language_report(data)
        assert "ciscategorial" in html
