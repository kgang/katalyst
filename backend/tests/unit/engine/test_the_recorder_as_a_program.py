"""The recorder run the way the coordinator runs it: as a program, in its own process.

**Why this file exists.** Two bugs reached paid runs because every test imported
the recorder as a module instead of starting it as a program. Importing defines
every name in the file before anything runs; starting it executes `main()` from
inside the module-level guard, so anything written below that guard does not
exist yet. On 2026-09-20 that cost a 26-minute run:

    File ".../engine/record.py", line 263, in run_one
      update={"receipt": _with_the_insert(finished.receipt, its_calls)}
    NameError: name '_with_the_insert' is not defined

An earlier round cost another run the same way — a flag removed from the argument
parser while the line that read it stayed. Neither is findable by reading, by
linting or by any test that imports.

So these run `python -m katalyst.engine.record` and `python -m
katalyst.engine.check_recordings` in a subprocess, against a stand-in answerer,
with **no key and no network**, and read what lands on disk. They are the only
tests in the suite that prove the whole path: the arguments, the generation, the
scripted insert, the kept run, the recording and the exit code.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from katalyst.engine.record import KeptRun

BACKEND = Path(__file__).resolve().parents[3]
"""Where to run from, so `src` and `tests` are both importable."""


def run_the_recorder(
    tmp_path: Path, *arguments: str, answerer: str, **extra: str
) -> subprocess.CompletedProcess[str]:
    """Start the recorder as a program and wait for it, with nowhere real to write.

    Args:
        tmp_path: A throwaway directory, used for both the kept runs and any
            recording — nothing here may touch `backend/.runs/`, which holds what
            real money bought.
        *arguments: What to put on its command line.
        answerer: The import path of the stand-in that answers its questions.
        **extra: Anything else to put in its environment.

    Returns:
        The finished process, with whatever it wrote to both streams.
    """
    environment = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(tmp_path),
        "PYTHONPATH": f"{BACKEND / 'src'}:{BACKEND}",
        "KATALYST_ANSWERER": answerer,
        "KATALYST_RUNS": str(tmp_path / "runs"),
        "KATALYST_RECORDINGS": str(tmp_path / "recordings"),
        **extra,
    }
    return subprocess.run(
        [sys.executable, "-m", "katalyst.engine.record", *arguments],
        capture_output=True,
        text=True,
        cwd=BACKEND,
        env=environment,
        timeout=120,
        check=False,
    )


def the_kept_run(tmp_path: Path) -> KeptRun:
    """Read the one file the run left in its throwaway directory."""
    kept = sorted((tmp_path / "runs").glob("*.json"))
    assert len(kept) == 1, f"expected one kept run, found {[one.name for one in kept]}"
    return KeptRun.model_validate_json(kept[0].read_text(encoding="utf-8"))


def test_the_recorder_runs_end_to_end_as_a_program(tmp_path: Path) -> None:
    """The whole path, in one process, with no key: the bug at the top of this file.

    Nothing here asserts anything clever. It asserts that the program starts, gets
    to the end, and leaves behind what it says it leaves behind — which is exactly
    what two paid runs found out the expensive way.
    """
    finished = run_the_recorder(
        tmp_path,
        "--only",
        "hormuz",
        answerer="tests.unit.engine.stand_ins:a_whole_story",
    )

    assert "Traceback" not in finished.stderr, finished.stderr
    kept = the_kept_run(tmp_path)
    assert kept.receipt is not None
    assert kept.receipt.calls > 0
    assert kept.graph is not None
    assert kept.done is not None
    assert kept.transcript.lines
    assert kept.broke is None


def test_a_run_answered_by_a_stand_in_never_becomes_a_recording(tmp_path: Path) -> None:
    """The one thing that makes the seam above safe to ship.

    A recording is a file the product plays back to somebody with no key, as a
    record of what a real model really said. A run answered from a list in a test
    file is not that, whatever else it is, so it is kept and named and never
    written to the recordings folder.
    """
    finished = run_the_recorder(
        tmp_path,
        "--only",
        "hormuz",
        answerer="tests.unit.engine.stand_ins:a_whole_story",
    )

    kept = the_kept_run(tmp_path)
    assert kept.became_a_recording is False
    assert any("stand-in" in one for one in kept.faults)
    assert not list((tmp_path / "recordings").glob("*.jsonl"))
    assert finished.returncode != 0


def test_a_run_the_model_stops_answering_is_still_kept_in_full(tmp_path: Path) -> None:
    """A 429 part way through is ordinary, and the money before it was real."""
    run_the_recorder(
        tmp_path,
        "--only",
        "hormuz",
        answerer="tests.unit.engine.stand_ins:stops_answering",
    )

    kept = the_kept_run(tmp_path)
    assert kept.receipt is not None
    assert kept.receipt.calls > 0
    assert kept.done is not None
    assert kept.broke is None


def test_a_run_that_crashes_after_the_generation_still_leaves_its_receipt(
    tmp_path: Path,
) -> None:
    """Kent, 2026-09-20: a paid run is never discarded, and a crash is no exception.

    The generation is written to disk the moment it ends and **before** the
    scripted insert is drafted, then written again with the insert on it. A bug
    anywhere after the first paid call therefore still leaves a file saying what
    was spent and what went wrong, in one plain sentence.
    """
    finished = run_the_recorder(
        tmp_path,
        "--only",
        "hormuz",
        answerer="tests.unit.engine.stand_ins:breaks_after_the_generation",
    )

    kept = the_kept_run(tmp_path)
    assert kept.receipt is not None
    assert kept.receipt.calls == 5
    assert kept.graph is not None
    assert kept.broke is not None
    assert "something nobody wrote a sentence for" not in kept.broke
    assert finished.returncode != 0


def test_a_recording_is_promoted_only_after_it_passes_the_builds_own_checks(
    tmp_path: Path,
) -> None:
    """`replay.md` B6: copied across **only if** it passes every check in B9.

    Read back off the written file rather than off the run in memory, because the
    file is what a keyless reviewer plays and what continuous integration reads.
    A run answered by a stand-in never gets this far, so the check is proved here
    by the one thing that does reach it: the folder stays empty and the program
    says why (2026-09-20).
    """
    finished = run_the_recorder(
        tmp_path,
        "--only",
        "hormuz",
        answerer="tests.unit.engine.stand_ins:a_whole_story",
    )

    assert not list((tmp_path / "recordings").glob("*.jsonl"))
    assert finished.returncode != 0
    assert "no recording was written" in finished.stderr


def test_the_recording_checker_runs_as_a_program_too(tmp_path: Path) -> None:
    """The other module with a guard in it, checked the same way and for the same reason."""
    (tmp_path / "recordings").mkdir(parents=True)

    finished = subprocess.run(
        [sys.executable, "-m", "katalyst.engine.check_recordings"],
        capture_output=True,
        text=True,
        cwd=BACKEND,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "PYTHONPATH": f"{BACKEND / 'src'}:{BACKEND}",
            "KATALYST_RECORDINGS": str(tmp_path / "recordings"),
        },
        timeout=60,
        check=False,
    )

    assert "Traceback" not in finished.stderr, finished.stderr
    # It passes on an empty folder, which is what lets it be green from the commit
    # that adds it.
    assert finished.returncode == 0


@pytest.mark.parametrize("named", ["nonesuch", "hormuz,midterms"])
def test_an_example_nobody_ships_is_refused_by_name(tmp_path: Path, named: str) -> None:
    """The argument parsing is part of the program, so it is tested as one."""
    finished = run_the_recorder(
        tmp_path,
        "--only",
        named,
        answerer="tests.unit.engine.stand_ins:a_whole_story",
    )

    assert finished.returncode == 1
    assert "There is no example called" in finished.stderr
    assert not list((tmp_path / "runs").glob("*.json"))


def test_the_kept_run_is_readable_json_a_person_could_open(tmp_path: Path) -> None:
    """It is the record of an afternoon's spending, so it has to be readable."""
    run_the_recorder(
        tmp_path,
        "--only",
        "hormuz",
        answerer="tests.unit.engine.stand_ins:a_whole_story",
    )

    written = sorted((tmp_path / "runs").glob("*.json"))[0]
    read = json.loads(written.read_text(encoding="utf-8"))

    assert read["example"] == "hormuz"
    assert read["prompt_hash"]
    assert "\n" in written.read_text(encoding="utf-8")


# --- What `--cap` actually buys -------------------------------------------


def test_a_run_that_has_spent_its_cap_makes_no_further_paid_call(tmp_path: Path) -> None:
    """`--cap 0.5` bought $1.60 of model calls (2026-09-21).

    The generation stopped for money, as it should — and the recorder then went
    on to draft the scripted intervention anyway, because `add_a_claim` checked
    the ceiling between its arrows and not before its first call. Two dear calls
    later the run had spent three times its cap.

    A run that ended for money drafts nothing, and says so in its own verdict:
    a recording whose card's button does nothing is worse than no recording.
    """
    finished = run_the_recorder(
        tmp_path,
        "--only",
        "hormuz",
        "--cap",
        "0.5",
        answerer="tests.unit.engine.dear_stand_in:dear",
    )

    kept = the_kept_run(tmp_path)
    assert kept.done is not None
    assert kept.done.reason == "spend_cap"
    assert kept.receipt is not None
    # A round's calls are all in flight before the first is folded, so the bound
    # is the cap plus what was already in the air — never another whole insert.
    assert kept.receipt.dollars < 0.5 + A_WHOLE_ROUND_IN_FLIGHT
    assert any("money ran out" in one for one in kept.faults)
    assert finished.returncode != 0


A_WHOLE_ROUND_IN_FLIGHT = 4.0
"""What a round of dear calls can add after the ceiling is read, in dollars.

Three calls at about a dollar each, and each of those may take its own rounds of
research. The real bound is stated in `receipt.py` and in the chapters; this is
a figure a test can compare against, generous enough not to be about arithmetic.
"""
