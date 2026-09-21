"""The eval harness run the way the coordinator runs it: as a program, in its own process.

**Why this file exists.** Two paid runs of the recorder were lost to bugs that
only exist when a module is *started* rather than imported: importing defines
every name in the file before anything runs, while starting it executes `main()`
from inside the module-level guard, so anything written below that guard does not
exist yet. A `NameError` after the money was spent is the shape of it.

`make eval` is the other program in this repository that spends money, so it gets
the same treatment: started with `python -m evals.run` in a subprocess, against a
stand-in answerer, **with no key and no network**, and read off what lands on
disk. These are the only tests that prove the whole path — the arguments, the
cases, the runs, the scorecard, what is written and the exit code.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from evals.run import ANSWERED_BY_A_STAND_IN

from katalyst.engine.record import KeptRun

BACKEND = Path(__file__).resolve().parents[3]
"""Where to run from, so `src` and `tests` are both importable and `.env` is read as usual."""

REPOSITORY = BACKEND.parent
"""The repository root, which is where `evals/` lives."""


def run_the_evals(
    tmp_path: Path, *arguments: str, answerer: str, **extra: str
) -> subprocess.CompletedProcess[str]:
    """Start the eval harness as a program and wait for it, with nowhere real to write.

    Args:
        tmp_path: A throwaway directory for the kept runs. Nothing here may touch
            `backend/.runs/`, which holds what real money bought.
        *arguments: What to put on its command line.
        answerer: The import path of the stand-in that answers its questions.
        **extra: Anything else to put in its environment.

    Returns:
        The finished process, with whatever it wrote to both streams.
    """
    environment = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(tmp_path),
        "PYTHONPATH": f"{BACKEND / 'src'}:{BACKEND}:{REPOSITORY}",
        "KATALYST_ANSWERER": answerer,
        "KATALYST_RUNS": str(tmp_path / "runs"),
        **extra,
    }
    return subprocess.run(
        [sys.executable, "-m", "evals.run", *arguments],
        capture_output=True,
        text=True,
        cwd=BACKEND,
        env=environment,
        timeout=180,
        check=False,
    )


def the_kept_runs(tmp_path: Path) -> list[KeptRun]:
    """Read every run the program left in its throwaway directory, oldest name first."""
    return [
        KeptRun.model_validate_json(one.read_text(encoding="utf-8"))
        for one in sorted((tmp_path / "runs").glob("*.json"))
    ]


def test_the_harness_runs_end_to_end_as_a_program(tmp_path: Path) -> None:
    """The whole path, in one process, with no key: the bug at the top of this file.

    Nothing here asserts anything clever. It asserts that the program starts, gets
    to the end, prints a scorecard and leaves behind what it says it leaves
    behind.
    """
    finished = run_the_evals(
        tmp_path,
        "--only",
        "hormuz",
        answerer="tests.unit.engine.stand_ins:an_eval_that_holds_every_check",
    )

    assert "Traceback" not in finished.stderr, finished.stderr
    assert "cases held all eight checks" in finished.stdout
    kept = the_kept_runs(tmp_path)
    assert len(kept) == 1
    assert kept[0].receipt is not None
    assert kept[0].graph is not None
    assert kept[0].broke is None


def test_every_case_runs_when_none_is_named(tmp_path: Path) -> None:
    """`make eval` with nothing else on the line is all four of them."""
    finished = run_the_evals(
        tmp_path, answerer="tests.unit.engine.stand_ins:an_eval_that_holds_every_check"
    )

    assert "Traceback" not in finished.stderr, finished.stderr
    assert sorted(one.example for one in the_kept_runs(tmp_path)) == [
        "export-controls",
        "hormuz",
        "midterms",
        "photonics",
    ]


def test_a_run_answered_by_a_stand_in_writes_no_scorecard(tmp_path: Path) -> None:
    """The one thing that makes the seam above safe to ship.

    A row in `evals/runs/` is a measurement of a model, committed as evidence. A
    run answered from a list in a test file is not that, whatever else it is, so
    the table is printed, the reason is said, and nothing is written.
    """
    finished = run_the_evals(
        tmp_path,
        "--only",
        "hormuz",
        answerer="tests.unit.engine.stand_ins:an_eval_that_holds_every_check",
    )

    assert ANSWERED_BY_A_STAND_IN in finished.stderr
    assert "wrote the scorecard" not in finished.stderr
    assert finished.returncode != 0


def test_a_check_that_did_not_hold_is_named_on_the_terminal(tmp_path: Path) -> None:
    """The committed row carries the counts; which check read them is said where somebody looks."""
    finished = run_the_evals(
        tmp_path,
        "--only",
        "photonics",
        answerer="tests.unit.engine.stand_ins:an_eval_whose_map_ends_nowhere",
    )

    assert "of the eight checks did not hold" in finished.stderr
    assert "an ending that names a trade" in finished.stderr
    assert finished.returncode != 0


def test_every_run_is_kept_even_when_the_program_ends_unhappily(tmp_path: Path) -> None:
    """A paid run is never thrown away, and a failed check is no reason to start."""
    run_the_evals(
        tmp_path,
        "--only",
        "photonics",
        answerer="tests.unit.engine.stand_ins:an_eval_whose_map_ends_nowhere",
    )

    kept = the_kept_runs(tmp_path)

    assert len(kept) == 1
    assert kept[0].receipt is not None
    assert kept[0].graph is not None
    assert kept[0].became_a_recording is False


def test_a_run_the_model_stops_answering_is_still_kept_in_full(tmp_path: Path) -> None:
    """A 429 part way through is ordinary, and the money before it was real."""
    run_the_evals(
        tmp_path, "--only", "hormuz", answerer="tests.unit.engine.stand_ins:stops_answering"
    )

    kept = the_kept_runs(tmp_path)

    assert len(kept) == 1
    assert kept[0].receipt is not None
    assert kept[0].receipt.calls > 0


def test_a_run_that_has_spent_its_cap_stops_and_says_so(tmp_path: Path) -> None:
    """`--cap` may lower the figure in code and never lift it, as it does for the recorder."""
    finished = run_the_evals(
        tmp_path,
        "--only",
        "hormuz",
        "--cap",
        "0.5",
        answerer="tests.unit.engine.dear_stand_in:dear",
    )

    kept = the_kept_runs(tmp_path)

    assert "Traceback" not in finished.stderr, finished.stderr
    assert kept[0].done is not None
    assert kept[0].done.reason == "spend_cap"


@pytest.mark.parametrize("named", ["nonesuch", "hormuz,midterms"])
def test_a_case_nobody_ships_is_refused_by_name(tmp_path: Path, named: str) -> None:
    """The argument parsing is part of the program, so it is tested as one."""
    finished = run_the_evals(
        tmp_path,
        "--only",
        named,
        answerer="tests.unit.engine.stand_ins:an_eval_that_holds_every_check",
    )

    assert finished.returncode == 1
    assert "There is no case called" in finished.stderr
    assert not list((tmp_path / "runs").glob("*.json"))


def test_the_harness_refuses_to_start_with_no_key_and_no_stand_in(tmp_path: Path) -> None:
    """It calls a model and spends money. With nothing to call, it says so and runs nothing."""
    finished = run_the_evals(tmp_path, "--only", "hormuz", answerer="")

    assert finished.returncode == 1
    assert "no key is configured" in finished.stderr
    assert not list((tmp_path / "runs").glob("*.json"))
