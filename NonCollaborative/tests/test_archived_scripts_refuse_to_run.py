"""Checks that the archived scripts still refuse to be run directly.

`OlderFiles/planarsviz_superseded/` holds the R scripts the `planarsviz`
package replaced. They are kept because the porting checks run them to prove
the package draws what they drew -- and that is safe, because a check reads a
script's text and evaluates it in memory with `ggsave` replaced by a
do-nothing function, so nothing reaches the disk.

Running the same file with `Rscript` has no such protection. `ggsave` is live,
and the script writes its old output over a chart the package produced, under
the same filename. Nothing in `results/` records which program wrote which
file, so the swap is silent: the chart simply becomes wrong, and stays wrong
until someone notices a figure that does not match the analysis.

`NonCollaborative/.Rprofile` prevents this by refusing to run any file under
`OlderFiles/`. This test exists because that guard is easy to lose by
accident -- `.Rprofile` is infrastructure that gets rewritten for unrelated
reasons (it also sets up renv), and nothing else would notice its disappearance
until a chart had already been overwritten.

The test drives a throwaway file rather than a real archived script, for the
obvious reason: proving the guard works by running a script it is meant to
stop would write the exact files this is protecting.
"""

import os
import shutil
import subprocess

import pytest

from pathlib import Path

NC_ROOT = Path(__file__).parents[1]
ARCHIVE = NC_ROOT / "OlderFiles"

RSCRIPT = shutil.which("Rscript")

pytestmark = [
    pytest.mark.needs_r,
    pytest.mark.skipif(
        RSCRIPT is None, reason="Rscript is not installed on this machine."
    ),
]


@pytest.fixture
def probe():
    """A harmless R file inside the archive, removed afterwards."""
    path = ARCHIVE / ".guard_probe.R"
    path.write_text('cat("probe ran\\n")\n')
    yield path
    path.unlink(missing_ok=True)


def _run(path, extra_env=None):
    env = dict(os.environ)
    env.pop("PLANARS_RUN_ARCHIVED", None)
    env.update(extra_env or {})
    return subprocess.run(
        [RSCRIPT, str(path.relative_to(NC_ROOT))],
        cwd=NC_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def test_running_an_archived_script_is_refused(probe):
    result = _run(probe)

    assert result.returncode != 0, (
        "An R file under OlderFiles/ ran to completion. The guard in "
        "NonCollaborative/.Rprofile is gone or no longer matches that path, "
        "so running an archived chart script would now overwrite a chart the "
        "planarsviz package produced, silently.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "probe ran" not in result.stdout, (
        "The archived file was refused, but only after its code had already "
        "run. The guard has to stop the script before it executes."
    )

    message = result.stdout + result.stderr
    for expected in ("Refusing to run an archived script", "PLANARS_RUN_ARCHIVED"):
        assert expected in message, (
            f"The refusal no longer says {expected!r}. Someone reading it has "
            "to learn what was refused and how to override it deliberately; "
            "a bare non-zero exit sends them looking for a bug instead.\n"
            f"It said:\n{message}"
        )


def test_the_deliberate_override_still_works(probe):
    result = _run(probe, {"PLANARS_RUN_ARCHIVED": "1"})

    assert result.returncode == 0 and "probe ran" in result.stdout, (
        "PLANARS_RUN_ARCHIVED=1 no longer lets an archived script run. The "
        "guard is meant to stop an accident, not to make the archive "
        "unusable -- the scripts are evidence, and someone will occasionally "
        "need to run one on purpose.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_a_script_outside_the_archive_is_untouched(tmp_path):
    outside = NC_ROOT / ".guard_probe_outside.R"
    outside.write_text('cat("probe ran\\n")\n')
    try:
        result = _run(outside)
    finally:
        outside.unlink(missing_ok=True)

    assert result.returncode == 0 and "probe ran" in result.stdout, (
        "An R file outside OlderFiles/ was refused. The guard is matching too "
        "much -- every chart script, check and render run in this directory "
        "would be blocked.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
