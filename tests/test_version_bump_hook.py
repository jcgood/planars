"""The pre-commit hook's version bump (regenerate_snapshots_hook.bump_version).

Colab installs planars from GitHub, so every library change needs a new
version; the hook does it instead of a person remembering to (Phase 10 unit
7, 2026-10-12).
"""
import pytest

from regenerate_snapshots_hook import bump_version


def test_alpha_number_goes_up_by_one():
    text = '[project]\nname = "planars"\nversion = "0.1.0a33"\n'
    assert bump_version(text) == '[project]\nname = "planars"\nversion = "0.1.0a34"\n'


def test_only_the_version_line_changes():
    text = 'x = 1\nversion = "0.1.0a9"\ny = "version = 2"\n'
    assert bump_version(text) == 'x = 1\nversion = "0.1.0a10"\ny = "version = 2"\n'


def test_a_file_without_a_version_line_stops_the_commit():
    with pytest.raises(SystemExit):
        bump_version('[project]\nname = "planars"\n')
