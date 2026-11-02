"""Worked examples of the span rules: small filled tabs and the spans each
rule should give for them, checked against the code.

The examples are written when a span rule is agreed with the domain expert
(coordinator guide § "Reviewing a span rule with the domain expert"), so they
record what the rule means, not what the code happens to do. Their layout is
in tests/span_examples/README.md. Unlike the snapshots they need no
coded_data/, so these tests never skip.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd
import pytest

from planars.reports import _CLASS_HANDLERS, span_constructions

EXAMPLES_DIR = Path(__file__).resolve().parent / "span_examples"
EXPECTED_FILE = "expected_spans.tsv"
# The columns compared; Why is for the reader and is not compared.
KEY_COLUMNS = ["Construction", "Test_Labels", "Span_Key", "Left_Edge", "Right_Edge"]
EXPECTED_COLUMNS = KEY_COLUMNS + ["Why"]


def find_examples(root: Path = EXAMPLES_DIR) -> list[Path]:
    """Every example folder: tests/span_examples/{class}/{example}/."""
    return sorted(p for p in root.glob("*/*") if p.is_dir())


def computed_spans(example: Path) -> pd.DataFrame:
    """The spans the code gives for every span-producing tab in the example."""
    class_name = example.parent.name
    if class_name not in _CLASS_HANDLERS:
        raise ValueError(f"{example}: '{class_name}' is not a class in planars/reports.py")
    module = importlib.import_module(f"planars.{class_name}")
    _derive, row_fn = _CLASS_HANDLERS[class_name]
    wanted = span_constructions(class_name)
    tabs = sorted((example / class_name).glob("*.tsv"))
    tabs = [t for t in tabs if wanted is None or t.stem in wanted]
    if not tabs:
        raise ValueError(f"{example}: no span-producing tab in {example / class_name}")
    rows = []
    for tab in tabs:
        result = module.derive(tab, strict=False)
        for row in row_fn(result, example.name):
            rows.append({"Construction": tab.stem, **row})
    df = pd.DataFrame(rows)
    return df[KEY_COLUMNS].astype(str)


def expected_spans(example: Path) -> pd.DataFrame:
    path = example / EXPECTED_FILE
    if not path.exists():
        raise ValueError(f"{example}: no {EXPECTED_FILE}")
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValueError(f"{path}: columns must be {EXPECTED_COLUMNS}, found {list(df.columns)}")
    return df[KEY_COLUMNS]


def differences(example: Path) -> str:
    """'' when the code gives exactly the expected spans; otherwise what differs,
    with the code's full output as a TSV to compare against."""
    got = computed_spans(example)
    want = expected_spans(example)
    got_set = set(map(tuple, got.values.tolist()))
    want_set = set(map(tuple, want.values.tolist()))
    if got_set == want_set and len(want) == len(want_set):
        return ""
    lines = [f"{example.relative_to(example.parent.parent.parent)}:"]
    if len(want) != len(want_set):
        lines.append("  a span is listed twice in " + EXPECTED_FILE)
    for row in sorted(want_set - got_set):
        lines.append("  expected, not given: " + "\t".join(row))
    for row in sorted(got_set - want_set):
        lines.append("  given, not expected: " + "\t".join(row))
    lines.append("  the code's spans:")
    lines.append("  " + "\t".join(KEY_COLUMNS))
    lines.extend("  " + "\t".join(r) for r in got.values.tolist())
    return "\n".join(lines)


def test_examples_folder_documented():
    assert (EXAMPLES_DIR / "README.md").exists()


@pytest.mark.parametrize("example", find_examples(),
                         ids=lambda p: f"{p.parent.name}/{p.name}")
def test_span_example(example):
    diff = differences(example)
    assert not diff, diff


# --- the checker itself, on an example built here --------------------------

def _make_example(root: Path, edge: str | None) -> Path:
    """A two-position ciscategorial example. Its expected spans are the code's,
    except the first span's right edge when `edge` is given."""
    ex = root / "ciscategorial" / "synthex"
    (ex / "lang_setup").mkdir(parents=True)
    (ex / "ciscategorial").mkdir()
    (ex / "lang_setup" / "planar_synthex.tsv").write_text(
        "Language_ID\tPlanar_Type\tPosition\tPosition_Type\tPosition_Name\tElements\tClass_Type\tExample\tNotes\n"
        "synthex\tverbal\t1\tSlot\tv:verbstem\tV\topen\t\t\n"
        "synthex\tverbal\t2\tSlot\tv:suffix\t-s\tlist\t\t\n", encoding="utf-8")
    (ex / "ciscategorial" / "general.tsv").write_text(
        "Element\tPosition_Name\tPosition_Number\tV-combines\tN-combines\tA-combines\tExample\tSource\tComments\n"
        "V\tv:verbstem\t1\t\t\t\t\t\t\n"
        "-s\tv:suffix\t2\ty\tn\tn\t\t\t\n", encoding="utf-8")
    got = computed_spans(ex)
    want = got.copy()
    want["Why"] = ""
    if edge is not None:
        want.loc[0, "Right_Edge"] = edge
    want.to_csv(ex / EXPECTED_FILE, sep="\t", index=False)
    return ex


def test_checker_passes_matching_example(tmp_path):
    ex = _make_example(tmp_path, edge=None)
    assert differences(ex) == ""


def test_checker_reports_wrong_edge(tmp_path):
    ex = _make_example(tmp_path, edge="99")
    diff = differences(ex)
    assert "expected, not given" in diff and "99" in diff
    assert "given, not expected" in diff
