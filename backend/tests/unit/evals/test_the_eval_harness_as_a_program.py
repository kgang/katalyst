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
from evals.run import ANSWERED_BY_A_STAND_IN, CAP_IS_NOT_MONEY

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


def test_the_cap_bounds_the_round_and_not_each_case(tmp_path: Path) -> None:
    """A four-case round may spend the figure on the command line, and not four times it.

    **This is the bug it was written for.** The ceiling used to be worked out
    inside the run of one case, so every case got the whole of it: `CAP=15` over
    the four shipped cases bought a round of up to sixty dollars, and the word
    `cap` meant a quarter of what a reader would take it to mean.

    Every answer this stand-in gives costs about a dollar, so a ceiling of two
    is reached inside the first case. What the test asks is not how many cases
    ran — that depends on what a call costs — but the two things that are true
    however the arithmetic lands: **every case that started, started with money
    left**, and **it did not run all four**. The first of those is exactly what a
    round-wide ceiling promises, and it is asserted in that exact form: add the
    receipts up in the order the cases ran, and what had gone before the last one
    began was still under the ceiling. A case may finish over the line — the
    ceiling is checked between cases, and no case can be stopped mid-call for
    money it has already spent — but none may be begun past it. And, because a
    round that stopped short has scored nothing about what it never started, it
    says which cases those were and it does not come back saying all is well.
    """
    finished = run_the_evals(
        tmp_path, "--cap", "2.0", answerer="tests.unit.engine.dear_stand_in:dear"
    )

    assert "Traceback" not in finished.stderr, finished.stderr
    ran = [one.example for one in the_kept_runs(tmp_path)]
    every_case = ["export-controls", "hormuz", "midterms", "photonics"]
    assert ran, "the round was meant to afford at least one case"
    assert sorted(ran) != every_case, "the round paid for every case out of one case's ceiling"

    # What the round really spent, case by case, in the order they ran — off the
    # receipts the runs kept, not off the sentence, which is the thing being
    # checked. A case with no receipt counts as nothing and keeps its place, so
    # the running total stays aligned with the order.
    paid = [0.0 if one.receipt is None else one.receipt.dollars for one in the_kept_runs(tmp_path)]
    assert sum(paid) > 2.0, "this stand-in was meant to be dear enough to reach the ceiling"
    assert sum(paid[:-1]) < 2.0, (
        "the last case was started after the whole ceiling had already gone, "
        "so the ceiling did not bound the round"
    )

    # And the scorecard says so, in one sentence, naming both halves.
    assert "The round spent" in finished.stdout
    assert "never started" in finished.stdout
    for missed in set(every_case) - set(ran):
        assert missed in finished.stdout
    assert finished.returncode != 0


@pytest.mark.parametrize("figure", ["0", "0.0", "-1", "0.0001", "0.004"])
def test_a_ceiling_that_is_not_money_is_refused_before_anything_runs(
    tmp_path: Path, figure: str
) -> None:
    """A spending rule is worth nothing once the spending has started, so it is checked first.

    Three nonsenses, one sentence. A ceiling **below zero** asks for a round that
    may spend less than nothing. A ceiling of **exactly zero** asks for a round
    that may never start a case, which is not a round. And a ceiling **under half
    a penny** prints `$0.00`, so the round would have reported spending a penny
    out of a ceiling of nothing — the harness really did say *"The round spent
    $0.01 of its $0.00 ceiling"*, which is a sentence that cannot be true.

    Refused on the way in, before the key is looked for and before a case is
    started, and it writes nothing: an empty runs directory is the whole proof
    that no model was asked anything.
    """
    finished = run_the_evals(
        tmp_path,
        "--cap",
        figure,
        answerer="tests.unit.engine.stand_ins:an_eval_that_holds_every_check",
    )

    assert finished.returncode == 1
    assert "Traceback" not in finished.stderr, finished.stderr
    assert CAP_IS_NOT_MONEY in finished.stderr
    assert "The round spent" not in finished.stdout
    assert not list((tmp_path / "runs").glob("*.json"))


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
