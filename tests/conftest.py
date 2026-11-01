"""Shared test setup.

Email addresses live only in private planars-data (`coded_data/people.yaml`,
read by `coding/people.py`). Tests run against a placeholder address instead,
so sharing behaviour is still exercised and no real address is written into
the saved test outputs, which are in this public repo.

The tooling's state files (provenance log, tab snapshots, restructure
journal) go to each test's tmp_path, and so does everything the
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
    """The tooling's own files (every path coding/state_files.py names)
    go to the test's tmp_path, never planars-data.
    planars-data itself is pointed there too, so no test fetches from GitHub
    (coded_data_up_to_date): tmp_path is no git repository."""
    point_state_files_at(monkeypatch, tmp_path)


def point_state_files_at(monkeypatch, coded) -> None:
    """Every state_files path, under ``coded`` as if it were planars-data:
    each Path the module names inside planars-data is moved, so a new state
    file is covered without being listed here."""
    from coding import state_files
    for name, relative in _STATE_PATHS.items():
        monkeypatch.setattr(state_files, name, coded / relative)


def _state_paths() -> dict:
    """Each Path coding/state_files.py names inside planars-data, relative to
    it, as the module defines them (read once, before any test moves them)."""
    from pathlib import Path
    from coding import state_files
    base = state_files.CODED_DATA
    return {name: value.relative_to(base) for name, value in vars(state_files).items()
            if isinstance(value, Path) and value.is_relative_to(base)}


_STATE_PATHS = _state_paths()


@pytest.fixture(scope="session")
def english_files(tmp_path_factory):
    """A private copy of English's real folder (its files, change log and
    archive) in a ``coded_data/`` of its own, for tests that read a
    chapter's data (chapters/data.py reads the files where the local-file
    door keeps them, ``file_door.CODED_DATA``). Never the real clone: the
    door commits there. Empty when planars-data isn't cloned."""
    import shutil
    from pathlib import Path
    real = Path(__file__).resolve().parent.parent / "coded_data" / "stan1293"
    coded = tmp_path_factory.mktemp("english") / "coded_data"
    if real.is_dir():
        shutil.copytree(real, coded / "stan1293")
    else:
        coded.mkdir()
    return coded


@pytest.fixture()
def reads_english(english_files, monkeypatch):
    """The local-file door's planars-data is the copy of English (read only)."""
    from coding import file_door
    monkeypatch.setattr(file_door, "CODED_DATA", english_files)
    return english_files


@pytest.fixture(autouse=True)
def _file_door_in_tmp(monkeypatch, tmp_path):
    """The local-file door (coding/file_door.py) writes under an empty folder
    in tmp_path unless the test points it at its own copy of the data
    (fake_drive.point_coded_data_at, or the command module's CODED_DATA
    through command_runner). So no test writes, archives into or commits the
    real planars-data."""
    from coding import file_door
    monkeypatch.setattr(file_door, "CODED_DATA", tmp_path / "file_door_coded_data")
    monkeypatch.setattr(file_door, "_runs", [])


@pytest.fixture(autouse=True)
def _source_logs_in_tmp(monkeypatch, tmp_path):
    """The schemas' change log (coding/source_log.py) is a copy in tmp_path,
    their archive of previous versions an empty folder there, and
    measuring a source change's effects (coding/change_effects.py: two copies
    of the project, about ten seconds) reports none. A test of the
    measurement itself takes the ``real_measure`` fixture."""
    import shutil
    from coding import change_effects, source_log
    log = tmp_path / "schemas_changes.tsv"
    if source_log.PROJECT_LOG.exists():   # start from the real log, so the real schemas match
        shutil.copy2(source_log.PROJECT_LOG, log)
    monkeypatch.setattr(source_log, "PROJECT_LOG", log)
    monkeypatch.setattr(source_log, "SCHEMA_ARCHIVE", tmp_path / "schemas_archive")
    monkeypatch.setattr(change_effects, "measure",
                        lambda before, coded_data=None, code_from=None: change_effects.Effects())


@pytest.fixture
def real_measure(monkeypatch):
    """Undo the fake measurement above, for tests of change_effects."""
    from coding import change_effects
    monkeypatch.setattr(change_effects, "measure", _REAL_MEASURE)


def _real_measure():
    from coding import change_effects
    return change_effects.measure


_REAL_MEASURE = _real_measure()


@pytest.fixture(autouse=True)
def github():
    from coding import issues
    fake = FakeGitHub()
    issues.set_github(fake)
    yield fake
    issues.reset_github()
