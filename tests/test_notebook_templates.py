"""The real notebook templates (notebooks/templates/) run, cell by cell,
against the saved sheets, the way Colab runs them after their Setup cell.

test_generate_notebooks_snapshot.py stubs the templates to keep its record of
Drive writes readable, so this is where a broken cell is caught: before the
daily refresh publishes it to every annotator's notebook. Setup itself
(installing the package, signing in to Google) can only run in Colab; what it
leaves behind (``lang`` or ``langs``) is built here from the offline fake
through the same function (``planars.from_sheets.download_language``).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from coding import generate_notebooks
from planars.from_sheets import download_language, languages
from planars.languages import get_display_name
from planars.reports import _CLASS_HANDLERS
from tests.fake_drive import FakeDriveDoorway

TEMPLATES = ("domains_boilerplate.ipynb", "report_boilerplate.ipynb",
             "all_languages_boilerplate.ipynb")


def _sources(name, tokens=None):
    nb = generate_notebooks._load_template(name)
    if tokens:
        nb = generate_notebooks._substitute_tokens(nb, tokens)
    return [("".join(c["source"]), c["cell_type"]) for c in nb["cells"]]


def _run_after_setup(name, namespace, tokens=None):
    """Run every code cell but Setup in ``namespace``, as Colab would."""
    for source, kind in _sources(name, tokens):
        if kind == "code" and not source.startswith("#@title Setup"):
            exec(compile(source, f"{name} cell", "exec"), namespace)


@pytest.fixture()
def fake():
    return FakeDriveDoorway.from_fixtures()


def _download(fake, lang_id, dest):
    return download_language(
        lang_id, dest,
        list_files=lambda q: fake.list_files(q, fields="files(id, name, properties)"),
        open_spreadsheet=fake.open_spreadsheet)


@pytest.fixture(autouse=True)
def no_windows(monkeypatch):
    """fig.show() would open a browser outside Colab."""
    import plotly.basedatatypes
    monkeypatch.setattr(plotly.basedatatypes.BaseFigure, "show", lambda self, *a, **k: None)


@pytest.mark.parametrize("name", TEMPLATES)
def test_a_notebook_names_no_sheet_and_no_class(name):
    """Sheets are found by label and classes by the tabs found, so a
    notebook never needs regenerating when either changes."""
    text = json.dumps(generate_notebooks._load_template(name))
    assert "manifest" not in text and "CONFIG_FILE_ID" not in text
    for class_name in _CLASS_HANDLERS:
        assert f"from planars import {class_name}" not in text
    assert "open_language(" in text or "open_all_languages(" in text


def test_the_language_notebook_runs(fake, tmp_path, capsys):
    lang = _download(fake, "stan1293", tmp_path)
    _run_after_setup("domains_boilerplate.ipynb", {"LANG_ID": "stan1293", "lang": lang},
                     {"LANG_ID": "stan1293", "LANG_DISPLAY": get_display_name("stan1293")})
    out = capsys.readouterr().out
    assert "spans computed" in out
    assert "No result for this tab yet" not in out


def test_the_report_notebook_runs(fake, tmp_path, capsys):
    lang = _download(fake, "stan1293", tmp_path)
    namespace = {"LANG_ID": "stan1293", "FOLDER_ID": "folder", "lang": lang,
                 "drive_svc": MagicMock()}
    pytest.importorskip("IPython")
    _run_after_setup("report_boilerplate.ipynb", namespace,
                     {"LANG_ID": "stan1293", "LANG_DISPLAY": get_display_name("stan1293"),
                      "FOLDER_ID": "folder"})
    assert "<html" in namespace["html"].lower()
    assert "Report URL" in capsys.readouterr().out


def test_the_all_languages_notebook_runs(fake, tmp_path, capsys):
    ids = languages(lambda q: fake.list_files(q, fields="files(id, name, properties)"))
    langs = {lang_id: _download(fake, lang_id, tmp_path) for lang_id in ids}
    _run_after_setup("all_languages_boilerplate.ipynb",
                     {"langs": langs, "ROOT": tmp_path, "get_display_name": get_display_name})
    out = capsys.readouterr().out
    assert f"/{len(langs)} language(s) fully complete." in out
    for lang_id in langs:
        assert f"[{lang_id}]" in out
