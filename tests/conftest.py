"""Shared test setup.

Email addresses live only in private planars-data (`coded_data/people.yaml`,
read by `coding/people.py`). Tests run against a placeholder address instead,
so sharing behaviour is still exercised and no real address is written into
the saved test outputs, which are in this public repo.

The tooling's state files (pending changes, provenance log, tab snapshots,
restructure journal) go to each test's tmp_path, and so does everything the
local-file door writes; the door enforces its rules in every test.

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
def _state_files_stay_in_tmp(monkeypatch, tmp_path):
    """The tooling's own files (coding/state_files.py: pending changes, the
    provenance log, tab snapshots, the restructure journal, the notes state
    and the ID file) go to the test's tmp_path, never planars-data.
    planars-data itself is pointed there too, so no test fetches from GitHub
    (coded_data_up_to_date): tmp_path is no git repository."""
    point_state_files_at(monkeypatch, tmp_path)


def point_state_files_at(monkeypatch, coded) -> None:
    """Every state_files path, under ``coded`` as if it were planars-data."""
    from coding import state_files
    state = coded / ".state"
    monkeypatch.setattr(state_files, "CODED_DATA", coded)
    monkeypatch.setattr(state_files, "STATE_DIR", state)
    monkeypatch.setattr(state_files, "PENDING_PATH", state / "pending_changes.json")
    monkeypatch.setattr(state_files, "PROVENANCE_LOG", state / "provenance_log.jsonl")
    monkeypatch.setattr(state_files, "SNAPSHOT_DIR", state / "regen_snapshots")
    monkeypatch.setattr(state_files, "JOURNAL_PATH", state / "restructure_journal.json")
    monkeypatch.setattr(state_files, "NOTES_STATE_PATH", state / "notes_state.json")
    monkeypatch.setattr(state_files, "ID_FILE", coded / "drive_config.json")


@pytest.fixture(autouse=True)
def _file_door_enforces_in_tmp(monkeypatch, tmp_path):
    """The local-file door (coding/file_door.py) enforces its rules in every
    test, and writes under an empty folder in tmp_path unless the test
    points it at its own copy of the data (fake_drive.point_coded_data_at,
    or the command module's CODED_DATA through command_runner). So no test
    writes, archives into or commits the real planars-data."""
    from coding import file_door
    monkeypatch.setattr(file_door, "MODE", file_door.ENFORCE)
    monkeypatch.setattr(file_door, "CODED_DATA", tmp_path / "file_door_coded_data")
    monkeypatch.setattr(file_door, "_runs", [])


@pytest.fixture(autouse=True)
def github():
    from coding import issues
    fake = FakeGitHub()
    issues.set_github(fake)
    yield fake
    issues.reset_github()
