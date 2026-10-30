"""Tests for planars/reports.py — the span collection and report data layer.

All tests read the checked-out coded_data/ directory (or one built in a
temporary folder). Reading the sheets into that layout is planars.from_sheets,
tested in tests/test_from_sheets.py.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
CODED_DATA = ROOT / "coded_data"

# Skip the whole module if coded_data is absent (e.g. CI without planars-data).
pytestmark = pytest.mark.skipif(
    not CODED_DATA.exists(),
    reason="coded_data/ not present",
)


# ---------------------------------------------------------------------------
# Imports — deferred so the skipif mark fires before import errors
# ---------------------------------------------------------------------------

from planars.reports import (
    _tab_completeness,
    _read_expected_constructions,
    language_completeness,
    language_report_data,
    language_spans,
    project_completeness,
    project_spans,
)

_SPAN_COLS = {"Language", "Test_Labels", "Analysis", "Left_Edge", "Right_Edge", "Size"}

# Languages that must be present for most tests to be meaningful.
_REQUIRED_LANGS = {"stan1293", "arao1248", "synth0001"}


# ---------------------------------------------------------------------------
# _tab_completeness unit tests (pure DataFrame logic, no file I/O)
# ---------------------------------------------------------------------------

class TestTabCompleteness:
    def test_empty_dataframe(self):
        result = _tab_completeness(pd.DataFrame(), ["crit1"])
        assert result == {"total": 0, "filled": 0, "blank": 0}

    def test_no_criterion_cols(self):
        df = pd.DataFrame({"crit1": ["y", "n"]})
        result = _tab_completeness(df, [])
        assert result == {"total": 0, "filled": 0, "blank": 0}

    def test_comments_col_excluded(self):
        df = pd.DataFrame({"crit1": ["y", "n"], "Comments": ["", "note"]})
        result = _tab_completeness(df, ["crit1", "Comments"])
        assert result["total"] == 2   # 2 rows × 1 criterion (Comments excluded)
        assert result["filled"] == 2
        assert result["blank"] == 0

    def test_fully_filled(self):
        df = pd.DataFrame({"crit1": ["y", "n"], "crit2": ["n", "y"]})
        result = _tab_completeness(df, ["crit1", "crit2"])
        assert result["total"] == 4
        assert result["filled"] == 4
        assert result["blank"] == 0

    def test_partially_filled(self):
        df = pd.DataFrame({"crit1": ["y", ""], "crit2": ["", "y"]})
        result = _tab_completeness(df, ["crit1", "crit2"])
        assert result["total"] == 4
        assert result["blank"] == 2
        assert result["filled"] == 2

    def test_all_blank(self):
        df = pd.DataFrame({"crit1": ["", ""], "crit2": ["", ""]})
        result = _tab_completeness(df, ["crit1", "crit2"])
        assert result["total"] == 4
        assert result["filled"] == 0
        assert result["blank"] == 4

    def test_invariant_total_eq_filled_plus_blank(self):
        df = pd.DataFrame({"c1": ["y", "", "n"], "c2": ["", "y", ""]})
        result = _tab_completeness(df, ["c1", "c2"])
        assert result["total"] == result["filled"] + result["blank"]


# ---------------------------------------------------------------------------
# project_spans
# ---------------------------------------------------------------------------

class TestProjectSpans:
    def test_returns_dataframe_and_meta(self):
        df, meta = project_spans(ROOT)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(meta, dict)

    def test_dataframe_columns(self):
        df, _ = project_spans(ROOT)
        assert _SPAN_COLS.issubset(df.columns)

    def test_contains_known_languages(self):
        df, meta = project_spans(ROOT)
        langs_in_df = set(df["Language"].unique())
        # All languages with annotation TSVs must appear
        for lang in _REQUIRED_LANGS - {"synth0001"}:  # synth0001 has data too
            assert lang in langs_in_df or not (CODED_DATA / lang / "ciscategorial").exists()

    def test_lang_meta_structure(self):
        _, meta = project_spans(ROOT)
        for lang_id, entry in meta.items():
            assert "keystone_pos" in entry
            assert "pos_to_name" in entry
            assert isinstance(entry["keystone_pos"], int)
            assert isinstance(entry["pos_to_name"], dict)

    def test_size_column_consistent(self):
        df, _ = project_spans(ROOT)
        # Size == Right_Edge - Left_Edge + 1 for every row
        computed = df["Right_Edge"] - df["Left_Edge"] + 1
        assert (df["Size"] == computed).all()


# ---------------------------------------------------------------------------
# language_spans
# ---------------------------------------------------------------------------

class TestLanguageSpans:
    @pytest.fixture(params=list(_REQUIRED_LANGS))
    def lang_id(self, request):
        lang = request.param
        if not (CODED_DATA / lang).exists():
            pytest.skip(f"coded_data/{lang} not present")
        # Must have at least one non-lang_setup class dir with a TSV
        has_data = any(
            d.is_dir() and d.name not in {"lang_setup", "archive"}
            and any(d.glob("*.tsv"))
            for d in (CODED_DATA / lang).iterdir()
        )
        if not has_data:
            pytest.skip(f"coded_data/{lang} has no annotation TSVs")
        return lang

    def test_returns_subset_of_project_spans(self, lang_id):
        df_all, _ = project_spans(ROOT)
        df_lang, _ = language_spans(lang_id, ROOT)
        # Every row in df_lang must appear in df_all
        lang_rows = df_all[df_all["Language"] == lang_id].reset_index(drop=True)
        assert len(df_lang) == len(lang_rows)

    def test_only_one_language_in_result(self, lang_id):
        df, _ = language_spans(lang_id, ROOT)
        if not df.empty:
            assert set(df["Language"].unique()) == {lang_id}

    def test_lang_meta_keyed_by_lang_id(self, lang_id):
        _, meta = language_spans(lang_id, ROOT)
        assert lang_id in meta
        assert "keystone_pos" in meta[lang_id]
        assert "pos_to_name" in meta[lang_id]


# ---------------------------------------------------------------------------
# language_completeness
# ---------------------------------------------------------------------------

class TestLanguageCompleteness:
    def test_returns_nested_dict(self):
        result = language_completeness("stan1293", ROOT)
        assert isinstance(result, dict)
        for class_name, constructions in result.items():
            assert isinstance(constructions, dict)
            for construction, stats in constructions.items():
                assert "total" in stats
                assert "filled" in stats
                assert "blank" in stats

    def test_invariant_total_eq_filled_plus_blank(self):
        result = language_completeness("stan1293", ROOT)
        for class_name, constructions in result.items():
            for construction, stats in constructions.items():
                if "error" not in stats:
                    assert stats["total"] == stats["filled"] + stats["blank"], \
                        f"{class_name}/{construction}: total != filled + blank"

    def test_ciscategorial_has_annotations(self):
        # stan1293/ciscategorial/general.tsv is a reference file — should have real data.
        result = language_completeness("stan1293", ROOT)
        cisc = result.get("ciscategorial", {}).get("general", {})
        assert cisc.get("total", 0) > 0, "ciscategorial/general should have annotation cells"
        assert cisc.get("filled", 0) > 0, "ciscategorial/general should have filled cells"

    def test_lang_setup_excluded(self):
        result = language_completeness("stan1293", ROOT)
        assert "lang_setup" not in result

    def test_archive_excluded(self):
        result = language_completeness("stan1293", ROOT)
        assert "archive" not in result

    def test_invariant_skips_missing_constructions(self):
        # missing=True constructions have total=filled=blank=0 — invariant still holds.
        result = language_completeness("arao1248", ROOT)
        for class_name, constructions in result.items():
            for construction, stats in constructions.items():
                if not stats.get("missing") and "error" not in stats:
                    assert stats["total"] == stats["filled"] + stats["blank"]


# ---------------------------------------------------------------------------
# Layer 1 completeness (_read_expected_constructions + missing constructions)
# ---------------------------------------------------------------------------

class TestLayer1Completeness:
    def _make_lang_dir(self, tmp_path, diagnostics_rows: list[dict],
                       tsv_files: dict | None = None) -> Path:
        """Create a minimal synthetic lang dir with diagnostics and optional TSVs."""
        lang_id = "test1234"
        lang_dir = tmp_path / "coded_data" / lang_id
        lang_setup = lang_dir / "lang_setup"
        lang_setup.mkdir(parents=True)

        import yaml
        rows = diagnostics_rows
        if rows:
            classes = {row["Class"]: {
                "constructions": [c.strip() for c in row["Constructions"].split(",")],
                "criteria": {"crit": ["y", "n"]}} for row in rows}
            (lang_setup / f"diagnostics_{lang_id}.yaml").write_text(
                yaml.safe_dump({"language": lang_id, "classes": classes}, sort_keys=False),
                encoding="utf-8")

        if tsv_files:
            for (class_name, construction), content in tsv_files.items():
                class_dir = lang_dir / class_name
                class_dir.mkdir(parents=True, exist_ok=True)
                tsv_path = class_dir / f"{construction}.tsv"
                tsv_path.write_text(content, encoding="utf-8")

        return lang_dir

    def _minimal_tsv(self) -> str:
        return (
            "Element\tPosition_Name\tPosition_Number\tcrit\n"
            "elem-L\tv:left\t3\ty\n"
            "ks\tv:verbstem\t5\tNA\n"
            "elem-R\tv:right\t7\tn\n"
        )

    def test_read_expected_constructions_basic(self, tmp_path):
        lang_dir = self._make_lang_dir(tmp_path, [
            {"Class": "ciscategorial", "Constructions": "general"},
            {"Class": "subspanrepetition", "Constructions": "aux, main"},
        ])
        result = _read_expected_constructions(lang_dir)
        assert result["ciscategorial"] == ["general"]
        assert result["subspanrepetition"] == ["aux", "main"]

    def test_read_expected_constructions_missing_file(self, tmp_path):
        lang_dir = tmp_path / "coded_data" / "nofile1234"
        lang_dir.mkdir(parents=True)
        assert _read_expected_constructions(lang_dir) == {}

    def test_missing_construction_appears_in_completeness(self, tmp_path):
        # diagnostics declares two constructions; only one has a TSV
        self._make_lang_dir(
            tmp_path,
            [{"Class": "ciscategorial", "Constructions": "general, other_construction"}],
            tsv_files={("ciscategorial", "general"): self._minimal_tsv()},
        )
        repo_root = tmp_path
        result = language_completeness("test1234", repo_root)
        assert "ciscategorial" in result
        # 'general' should have real stats (TSV present)
        assert result["ciscategorial"]["general"].get("missing") is None
        assert result["ciscategorial"]["general"]["total"] > 0
        # 'other_construction' should be flagged as missing
        assert result["ciscategorial"]["other_construction"]["missing"] is True
        assert result["ciscategorial"]["other_construction"]["total"] == 0

    def test_all_constructions_present_no_missing_flag(self, tmp_path):
        self._make_lang_dir(
            tmp_path,
            [{"Class": "ciscategorial", "Constructions": "general"}],
            tsv_files={("ciscategorial", "general"): self._minimal_tsv()},
        )
        result = language_completeness("test1234", tmp_path)
        assert "missing" not in result["ciscategorial"]["general"]

    def test_extra_tsv_not_in_diagnostics_still_included(self, tmp_path):
        # TSV exists but class isn't in diagnostics — should appear without missing flag
        self._make_lang_dir(
            tmp_path,
            [],  # no diagnostics rows
            tsv_files={("ciscategorial", "general"): self._minimal_tsv()},
        )
        result = language_completeness("test1234", tmp_path)
        assert "ciscategorial" in result
        assert "missing" not in result["ciscategorial"]["general"]

    def test_missing_construction_ordering(self, tmp_path):
        # Diagnostics order should be preserved: expected constructions come first
        self._make_lang_dir(
            tmp_path,
            [{"Class": "ciscategorial", "Constructions": "alpha, beta, gamma"}],
            tsv_files={("ciscategorial", "beta"): self._minimal_tsv()},
        )
        result = language_completeness("test1234", tmp_path)
        constructions = list(result["ciscategorial"].keys())
        assert constructions == ["alpha", "beta", "gamma"]

    def test_whole_class_missing(self, tmp_path):
        # diagnostics declares a class but no TSVs exist at all for it
        self._make_lang_dir(tmp_path, [
            {"Class": "ciscategorial", "Constructions": "general"},
        ])
        result = language_completeness("test1234", tmp_path)
        assert result["ciscategorial"]["general"]["missing"] is True


# ---------------------------------------------------------------------------
# project_completeness
# ---------------------------------------------------------------------------

class TestProjectCompleteness:
    def test_returns_all_lang_dirs(self):
        result = project_completeness(ROOT)
        lang_dirs = {
            d.name for d in CODED_DATA.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        }
        assert set(result.keys()) == lang_dirs

    def test_each_entry_matches_language_completeness(self):
        result = project_completeness(ROOT)
        for lang_id, entry in result.items():
            expected = language_completeness(lang_id, ROOT)
            assert entry == expected


# ---------------------------------------------------------------------------
# language_report_data
# ---------------------------------------------------------------------------

class TestLanguageReportData:
    _REQUIRED_KEYS = {
        "lang_id", "display_name", "generated_at",
        "completeness", "status", "spans", "lang_meta",
    }

    def test_bundle_has_all_keys(self):
        data = language_report_data("stan1293", ROOT)
        assert self._REQUIRED_KEYS.issubset(data.keys())

    def test_lang_id_echoed(self):
        data = language_report_data("stan1293", ROOT)
        assert data["lang_id"] == "stan1293"

    def test_display_name_is_string(self):
        data = language_report_data("stan1293", ROOT)
        assert isinstance(data["display_name"], str)
        assert "stan1293" in data["display_name"]

    def test_generated_at_is_utc_datetime(self):
        data = language_report_data("stan1293", ROOT)
        assert isinstance(data["generated_at"], datetime.datetime)
        assert data["generated_at"].tzinfo is not None

    def test_completeness_is_dict(self):
        data = language_report_data("stan1293", ROOT)
        assert isinstance(data["completeness"], dict)

    def test_status_is_none_unless_given(self):
        # The local files hold no Status tabs; from_sheets reads them in Colab.
        data = language_report_data("stan1293", ROOT)
        assert data["status"] is None
        status = {"ciscategorial": {"general": "ready-for-review"}}
        assert language_report_data("stan1293", ROOT, status=status)["status"] == status

    def test_spans_is_dataframe_when_data_present(self):
        data = language_report_data("stan1293", ROOT)
        assert isinstance(data["spans"], pd.DataFrame)
        assert _SPAN_COLS.issubset(data["spans"].columns)

    def test_lang_meta_structure_when_data_present(self):
        data = language_report_data("stan1293", ROOT)
        assert isinstance(data["lang_meta"], dict)
        assert "keystone_pos" in data["lang_meta"]
        assert "pos_to_name" in data["lang_meta"]

    def test_arao1248_bundle(self):
        if not (CODED_DATA / "arao1248").exists():
            pytest.skip("arao1248 not present")
        data = language_report_data("arao1248", ROOT)
        assert data["lang_id"] == "arao1248"
        assert isinstance(data["completeness"], dict)


# ---------------------------------------------------------------------------
# What the Colab notebooks print
# ---------------------------------------------------------------------------

class TestNotebookPrinting:
    def test_class_reports_cover_every_span_tab(self, capsys):
        """Every tab that produces spans gets a section with a result, not an
        error: the notebooks' "Results by test" names no class itself."""
        from planars.reports import _span_tabs, print_class_reports
        print_class_reports(ROOT, "stan1293")
        out = capsys.readouterr().out
        tabs = list(_span_tabs(CODED_DATA / "stan1293"))
        assert tabs
        for _cls, construction, _tsv in tabs:
            assert f"[stan1293]  —  {construction}\n" in out
        assert "No result for this tab yet" not in out

    def test_class_reports_with_no_tabs(self, tmp_path, capsys):
        from planars.reports import print_class_reports
        (tmp_path / "coded_data" / "test1234" / "lang_setup").mkdir(parents=True)
        print_class_reports(tmp_path, "test1234")
        assert "No annotation tabs found." in capsys.readouterr().out

    def test_completeness_lines(self, capsys):
        from planars.reports import print_completeness
        done = print_completeness(
            {"ciscategorial": {"general": {"total": 4, "filled": 4, "blank": 0}},
             "metrical": {"stress": {"total": 4, "filled": 3, "blank": 1},
                          "other": {"total": 0, "filled": 0, "blank": 0, "missing": True}}},
            {"ciscategorial": {"general": "ready-for-review"}})
        out = capsys.readouterr().out
        assert done is False
        assert "4/4 filled  ✓  [ready-for-review]" in out
        assert "3/4 filled  ⚠  1 blank" in out
        assert "metrical / other" in out and "no tab yet" in out
