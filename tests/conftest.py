"""Shared test setup.

Email addresses live only in private planars-data (`coded_data/people.yaml`,
read by `coding/people.py`). Tests run against a placeholder address instead,
so sharing behaviour is still exercised and no real address is written into
the saved test outputs, which are in this public repo.
"""
import pytest

PLACEHOLDER_PEOPLE = {"Adam Tallman": {"email": "annotator@example.org"}}


@pytest.fixture(autouse=True)
def _placeholder_people(monkeypatch):
    import coding.people
    monkeypatch.setattr(coding.people, "_load_people", lambda: PLACEHOLDER_PEOPLE)
