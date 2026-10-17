"""python -m planars: its list of analyses is derived from the schema, so it
offers every analysis the reports run (hidden-facts R-1)."""
import pytest

from planars import cli
from planars.reports import _CLASS_HANDLERS


def test_cli_offers_every_analysis_the_reports_run():
    assert set(cli._analyses()) == set(_CLASS_HANDLERS)


def test_cli_with_no_arguments_lists_the_analyses(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code == 1
    assert "metrical" in capsys.readouterr().err
