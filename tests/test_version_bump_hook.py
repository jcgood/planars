"""The pre-commit hook's version bump (bump_version_hook.py).

Every result records the code version (Phase 10 unit 18), and Colab
installs planars from GitHub, so every change to code that produces results
needs a new version; the hook does it instead of a person remembering to
(Phase 10 unit 7, 2026-10-12).
"""
import pytest

from bump_version_hook import bump_version, changes_result_code


def test_alpha_number_goes_up_by_one():
    text = '[project]\nname = "planars"\nversion = "0.1.0a33"\n'
    assert bump_version(text) == '[project]\nname = "planars"\nversion = "0.1.0a34"\n'


def test_only_the_version_line_changes():
    text = 'x = 1\nversion = "0.1.0a9"\ny = "version = 2"\n'
    assert bump_version(text) == 'x = 1\nversion = "0.1.0a10"\ny = "version = 2"\n'


def test_a_file_without_a_version_line_stops_the_commit():
    with pytest.raises(SystemExit):
        bump_version('[project]\nname = "planars"\n')


@pytest.mark.parametrize("path", ["planars/spans.py", "laminar/charts.py",
                                  "chapters/templates/chapter.tex.j2", "planarsviz/R/plot.R"])
def test_result_code_raises_the_version(path):
    assert changes_result_code([path])


@pytest.mark.parametrize("path", ["docs/testing.md", "coding/issues.py", "planars_notes.md",
                                  "schemas/terms.yaml"])
def test_other_files_do_not(path):
    assert not changes_result_code([path])
