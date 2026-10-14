"""Shared test setup.

Email addresses live only in private planars-data (`coded_data/people.yaml`,
read by `coding/people.py`). Tests run against a placeholder address instead,
so sharing behaviour is still exercised and no real address is written into
the saved test outputs, which are in this public repo.

The Drive door's provenance log and tab snapshots go to each test's
tmp_path.

Every test also gets an in-memory GitHub (`tests/fake_github.py`) in place of
the real one, so no test can file, comment on or close a real issue. A test
that wants to look at what was filed takes the `github` fixture.
"""
import pytest

from fake_github import FakeGitHub

PLACEHOLDER_PEOPLE = {"Adam Tallman": {"email": "annotator@example.org"}}


@pytest.fixture(autouse=True)
def _placeholder_people(monkeypatch):
    import coding.people
    monkeypatch.setattr(coding.people, "_load_people", lambda: PLACEHOLDER_PEOPLE)


@pytest.fixture(autouse=True)
def _door_writes_stay_in_tmp(monkeypatch, tmp_path):
    """The Drive door logs every write to the provenance log and saves a tab
    before replacing its answers; in a test both go to the test's tmp_path,
    never the repo's own provenance_log.jsonl and regen_snapshots/."""
    from coding import drive_door, provenance
    monkeypatch.setattr(provenance, "LOG_PATH", tmp_path / "provenance_log.jsonl")
    monkeypatch.setattr(drive_door, "SNAPSHOT_DIR", tmp_path / "regen_snapshots")


@pytest.fixture(autouse=True)
def github():
    from coding import issues
    fake = FakeGitHub()
    issues.set_github(fake)
    yield fake
    issues.reset_github()
