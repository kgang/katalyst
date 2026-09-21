"""The worked example's numbers, checked the way the build checks them: as a program.

`docs/worked-numbers.txt` is generated and committed, and the build regenerates it
and fails on any difference — the same bargain `types-fresh` already strikes for
the browser's types. This file is what makes a developer find that out on their
own machine in a second rather than on a pull request ten minutes later.

**Started as a program, in its own process, on purpose.** A `__main__` guard sits
below everything it calls, so importing the module defines every name before
anything runs and hides exactly the mistakes that reach a build: a name used
above where it is defined, a flag read after it was removed. On 2026-09-20 that
cost a 26-minute paid run. So these run `python -m katalyst.engine.worked_numbers`
and read what lands on disk.

**Directions, names and states — never values.** Not one number is typed in here.
The numbers are compared with the engine's own output, and everything else
asserted is a name, a word or an ordering.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from katalyst.engine.worked_numbers import BRANCHES, WHERE, WORLD_NAMES
from katalyst.fixtures.hormuz import HORMUZ

BACKEND = Path(__file__).resolve().parents[3]
"""Where to run from, so `src` and `tests` are both importable."""

INPUTS = "--- INPUTS"
"""How the part holding numbers a person typed announces itself."""

COMPUTED = "--- COMPUTED"
"""How the part holding numbers the engine worked out announces itself."""


def _committed() -> str:
    """Read the file as it is committed."""
    return WHERE.read_text(encoding="utf-8")


def _halves() -> tuple[list[str], list[str]]:
    """Split the committed file where it says it splits.

    Returns:
        The lines of the inputs part and the lines of the computed part.
    """
    lines = _committed().splitlines()
    starts = [one for one, text in enumerate(lines) if text.startswith(INPUTS)]
    divides = [one for one, text in enumerate(lines) if text.startswith(COMPUTED)]
    assert len(starts) == 1, "the inputs part must be announced exactly once"
    assert len(divides) == 1, "the computed part must be announced exactly once"
    assert starts[0] < divides[0], "the inputs come first, so a reader meets them first"
    return lines[starts[0] + 1 : divides[0]], lines[divides[0] + 1 :]


def _named(lines: list[str]) -> list[str]:
    """Pick out the fact lines and give back the stable name each starts with.

    A fact line is one that starts hard against the margin and carries a name made
    of parts joined by a middle dot. Everything else in the file is a heading or a
    sentence of explanation.

    Args:
        lines: The lines of one part of the file.

    Returns:
        Every name, in the order they appear.
    """
    names: list[str] = []
    for line in lines:
        if not line or line.startswith(" ") or "  " not in line:
            continue
        name = line.split("  ")[0]
        if " · " in name:
            names.append(name)
    return names


def test_the_file_on_disk_is_what_the_program_prints_now(tmp_path: Path) -> None:
    """Run the program and compare it with what is committed, byte for byte.

    With no key of any kind in its environment, because it needs none, and under a
    hash seed it has never seen, because a file whose lines depend on how this
    machine happens to order a set is a file that goes red on somebody else's
    machine for no reason anybody changed. It writes into a throwaway directory:
    a test that rewrote the committed file would pass by repairing what it is
    supposed to be checking.
    """
    written = tmp_path / "worked-numbers.txt"
    environment = {
        **{
            key: value
            for key, value in os.environ.items()
            if key not in {"ANTHROPIC_API_KEY", "FRED_API_KEY"}
        },
        "PYTHONHASHSEED": "7919",
    }
    finished = subprocess.run(
        [sys.executable, "-m", "katalyst.engine.worked_numbers", str(written)],
        capture_output=True,
        text=True,
        cwd=BACKEND,
        env=environment,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr
    printed = written.read_text(encoding="utf-8")

    if printed != _committed():
        pytest.fail(
            f"{WHERE.name} is stale: the engine no longer prints what is committed. "
            "Run `make numbers` and commit the result — the diff of that one file is "
            "the whole list of numbers that moved, and it is meant to be reviewed."
        )


def test_inputs_and_computed_numbers_are_labelled_apart() -> None:
    """The two parts are told apart by one rule, and every line obeys it.

    A computed number is read off a world, so its name says which world: `base`,
    `strike`, `observed B` or `observed C`. A number a person typed belongs to no
    world at all. That is the whole distinction, and it is what stops a sweep
    rewriting a stated prior that never needed touching.
    """
    stated, worked_out = _halves()
    worlds = set(WORLD_NAMES.values())

    assert stated and worked_out, "both parts must hold something"

    for name in _named(stated):
        assert not (worlds & set(name.split(" · "))), (
            f"'{name}' is in the inputs part but names a world, so it is a computed number"
        )
    for name in _named(worked_out):
        assert worlds & set(name.split(" · ")), (
            f"'{name}' is in the computed part but names no world, so nothing says where "
            "it was read from"
        )

    names = _named(stated) + _named(worked_out)
    assert len(names) == len(set(names)), "a name a chapter cites must point at one line"


def test_every_claim_and_every_arrow_of_the_example_is_written_down() -> None:
    """Nothing on the map is left out, and the list comes from the map rather than from here."""
    stated, worked_out = _halves()
    stated_names, computed_names = _named(stated), _named(worked_out)

    for claim in HORMUZ.propositions:
        assert f"{claim.id} · prior" in stated_names
        assert f"{claim.id} · resolve by" in stated_names
        assert f"{claim.id} · base · reading" in computed_names
    for arrow in HORMUZ.links:
        assert f"{arrow.id} · arrow" in stated_names
        assert f"{arrow.id} · base · conditional" in computed_names
    for branch in BRANCHES:
        assert f"{branch.id} · what it is called" in stated_names
        for position in range(1, len(branch.interventions) + 1):
            assert f"{branch.id} · edit {position}" in stated_names


def test_a_supposed_claim_reads_the_word_and_never_the_one_behind_it() -> None:
    """The strike's own claim is supposed true on the day it is judged, and the file says so.

    A claim a branch supposed true reads exactly 1 so that a chain of claims
    multiplied together has a factor for it. No surface may print that 1, and this
    file is a surface.
    """
    _, worked_out = _halves()
    reading = next(one for one in worked_out if one.startswith("S · strike · reading"))

    assert "supposed" in reading
    assert "1.0" not in reading
    assert ".99" not in reading
