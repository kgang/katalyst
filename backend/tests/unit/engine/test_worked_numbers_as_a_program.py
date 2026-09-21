"""The worked example's numbers, checked the way the build checks them: as a program.

`docs/worked-numbers.txt` is generated and committed, and the build works every
number out again and fails when one has moved. This file is what makes a
developer find that out on their own machine in a second rather than on a pull
request ten minutes later.

**Stale means a number moved — not that a machine's last bit differed.** The
first version of this compared the file character for character and went red on
Linux over a number that differs from this machine's in its eighth decimal place.
So the comparison is tolerant on numbers and exact on everything else, and the
three tests at the bottom are the whole contract: a last bit of disagreement is
forgiven, a real move is caught and named, and a word that changed is caught.

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
import re
import subprocess
import sys
from pathlib import Path

from katalyst.domain.diff import MOVED_AT_LEAST
from katalyst.engine.worked_numbers import (
    BRANCHES,
    TOLERANCE,
    WHERE,
    WORLD_NAMES,
    _line,
    _read_line,
    facts_in,
    faults_against,
)
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


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Start the program the way the build starts it, with no key of any kind.

    Args:
        *arguments: What to put on its command line.

    Returns:
        The finished process, with whatever it wrote to both streams.
    """
    environment = {
        **{
            key: value
            for key, value in os.environ.items()
            if key not in {"ANTHROPIC_API_KEY", "FRED_API_KEY"}
        },
        "PYTHONHASHSEED": "7919",
    }
    return subprocess.run(
        [sys.executable, "-m", "katalyst.engine.worked_numbers", *arguments],
        capture_output=True,
        text=True,
        cwd=BACKEND,
        env=environment,
        check=False,
    )


def test_the_committed_file_still_says_what_the_engine_says() -> None:
    """Run the check the way the build runs it, as a program, and expect nothing wrong.

    Under a hash seed it has never seen, because a file whose lines depend on how
    this machine happens to order a mapping is a file that goes red on somebody
    else's machine for no reason anybody changed.
    """
    finished = _run("--check")

    assert finished.returncode == 0, finished.stdout + finished.stderr
    assert "still says what the engine says" in finished.stdout


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


def test_a_last_bit_of_disagreement_between_machines_is_not_a_number_moving() -> None:
    """Nudge every number by one float32 step and the check still passes.

    This is the test the broken version of this check would have failed, and the
    reason the check was rebuilt. One step of the grid the engine samples on is
    the most two maths libraries were measured to disagree by, and nothing
    amplifies it. The *text* of the file does change — some number always sits
    near enough to a rounding boundary for that — and that is exactly the point:
    a file that reads differently is not the same as a number that moved.
    """
    step = 2.0**-24
    flip = [0]

    def nudged(found: re.Match[str]) -> str:
        flip[0] += 1
        return f"{float(found.group()) + (step if flip[0] % 2 else -step):.5f}"

    committed = WHERE.read_text(encoding="utf-8")
    perturbed = re.sub(r"(?<![\d.])-?\d\.\d{5}(?![\d])", nudged, committed)

    assert perturbed != committed, "the perturbation must actually change the file's text"
    assert faults_against(perturbed) == []


def test_a_number_that_really_moved_fails_the_check_and_names_its_line(tmp_path: Path) -> None:
    """Move one number by a fifth of what the screen can show, and the program says which.

    Run as a program, because the exit code is what the build reads, and the
    sentence is what a developer reads.
    """
    committed = WHERE.read_text(encoding="utf-8")
    line = next(
        one for one in committed.splitlines() if one.startswith("M1 · strike · change list rank")
    )
    moved = line.replace("0.04746", "0.04756")
    assert moved != line, "the committed rank is no longer the number this test moves"
    written = tmp_path / "worked-numbers.txt"
    written.write_text(committed.replace(line, moved), encoding="utf-8")

    finished = _run("--check", str(written))

    assert finished.returncode == 1
    assert "M1 · strike · change list rank moved by 0.0001" in finished.stdout
    assert "Run `make numbers` and commit the result" in finished.stdout


def test_a_fact_in_words_that_changed_fails_the_check() -> None:
    """A state word, and the words of the sentence beside a change list, are exact.

    Numbers get room; words get none. The sentence is the interesting case: its
    own two-figure numbers are rounded, so they are left alone and checked in full
    precision on the lines that own them — but if the sentence starts saying
    something else, that is a real change and it is caught.
    """
    committed = WHERE.read_text(encoding="utf-8")

    state = next(
        one for one in committed.splitlines() if one.startswith("B · strike · what happened")
    )
    assert faults_against(committed.replace(state, state.replace("shifted", "unchanged"))) == [
        "B · strike · what happened says 'unchanged' in the file and 'shifted' now."
    ]

    sentence = next(
        one for one in committed.splitlines() if one.startswith("strike · the sentence beside")
    )
    reworded = sentence.replace("moves A Polymarket", "shifts A Polymarket")
    assert len(faults_against(committed.replace(sentence, reworded))) == 1

    # …and a two-figure number inside it rounding the other way is not a change.
    rounded = sentence.replace("from .50 to .42", "from .51 to .42")
    assert faults_against(committed.replace(sentence, rounded)) == []


def test_every_line_of_the_file_reads_back_into_what_wrote_it() -> None:
    """One function writes a line and one reads it back, and they agree on every real line.

    A comparison of a parsed file is only as good as its parser, so the parser is
    held to the writer over the whole of the real file rather than over an example
    somebody made up.
    """
    committed = WHERE.read_text(encoding="utf-8")

    facts = 0
    for line in committed.splitlines():
        read_back = _read_line(line)
        if read_back is None:
            continue
        facts += 1
        assert _line(read_back.name, read_back.printed, read_back.value) == line, (
            f"this line does not write back to itself: {line!r}"
        )

    assert facts == len(facts_in(committed))
    assert facts > 200, "the parser found almost nothing, so it is not reading the file"


def test_the_tolerance_sits_between_what_machines_differ_by_and_what_a_reader_can_see() -> None:
    """The three sizes the tolerance has to live between, asserted rather than described.

    Above half a printed step, because the file stores five places and the check
    compares that against a full-precision number. Above what two machines were
    measured to disagree by. And well below the smallest move the rules layer will
    call a shift, which is the smallest difference anybody acts on.
    """
    half_a_printed_step = 0.5 * 10.0**-5
    one_float32_step = 2.0**-24

    assert half_a_printed_step < TOLERANCE
    assert one_float32_step * 100 < TOLERANCE
    assert TOLERANCE < MOVED_AT_LEAST / 100
