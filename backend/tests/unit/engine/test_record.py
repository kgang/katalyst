"""A paid run is kept whatever becomes of it, and only a good one becomes a recording.

The rule that started this: a nine-minute run that showed no refusal was correctly
refused a recording, and then thrown away — its receipt, its stop reason, its
per-call seconds and thinking tokens, and the map itself, all gone, with the money
already spent. **The checks decide whether a run becomes a recording. They never
decide whether it is kept.**

Every run here is told a story instead of asked of a model: no key, no network,
no money.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from katalyst.engine import record
from katalyst.engine.record import (
    THE_FOUR,
    KeptRun,
    faults_of,
    keep,
    run_one,
    what_it_cost,
    write_recording,
)
from tests.unit.engine.answers import (
    FROM_THE_QUESTION,
    Storyteller,
    a_claim,
    a_declined_answer,
    a_link,
    a_starting_claim,
    a_stop,
    an_answer,
)

HORMUZ = THE_FOUR["hormuz"]
A_STEP = "A step in the middle of the story."
AN_ENDING = "Something you could put money on."
A_DAY = date(2026, 9, 17)


def a_run_that_shows_a_refusal() -> Storyteller:
    """A story where one proposal is refused, which is what a recording must show."""
    return Storyteller(
        {
            HORMUZ: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION), read_fresh=400, written=900),
                a_declined_answer("It looked like something I should not help with."),
                an_answer(a_stop()),
            ],
            A_STEP: [
                an_answer(
                    a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"),
                    read_fresh=420,
                    written=1100,
                ),
                an_answer(a_stop()),
            ],
        },
        starting=[
            an_answer(a_starting_claim(HORMUZ), read_fresh=300, written=700),
            an_answer(a_starting_claim("Iran is struck the next day."), read_fresh=310),
        ],
        joining=[an_answer(a_link("Iran is struck the next day.", AN_ENDING))],
    )


def a_run_that_shows_none() -> Storyteller:
    """A story where everything was accepted — exactly the nine minutes that was lost."""
    return Storyteller(
        {
            HORMUZ: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION), read_fresh=400, written=900),
                an_answer(a_stop()),
            ],
            A_STEP: [
                an_answer(
                    a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"),
                    read_fresh=420,
                    written=1100,
                ),
                an_answer(a_stop()),
            ],
        },
        starting=[
            an_answer(a_starting_claim(HORMUZ), read_fresh=300, written=700),
            an_answer(a_starting_claim("Iran is struck the next day."), read_fresh=310),
        ],
        joining=[an_answer(a_link("Iran is struck the next day.", AN_ENDING))],
    )


def a_run(told: Storyteller) -> object:
    """Run one story through the recorder, saying nothing to the terminal."""
    return run_one("hormuz", answerer=told, cap=15.0, on=A_DAY, seed=20261001, say=lambda _: None)  # type: ignore[arg-type]


def test_a_run_that_shows_no_refusal_is_a_perfectly_good_recording() -> None:
    """Kent, 2026-09-20: show what happened, honestly.

    In twenty-six live proposals across two runs the model never once gave the
    map's rules something to refuse. Re-running until it errs is waiting for a
    mistake and calling it evidence — the one thing on the list that would have
    been staged.
    """
    run = a_run(a_run_that_shows_none())

    assert faults_of(run) == ()  # type: ignore[arg-type]


def test_a_run_is_kept_in_full_whatever_becomes_of_it(tmp_path: Path) -> None:
    """The money is spent either way, and the measurements are on no event."""
    run = a_run(a_run_that_shows_none())
    faults = ("kept for a reason of somebody's own",)

    where = keep(run, faults, folder=tmp_path)  # type: ignore[arg-type]

    kept = KeptRun.model_validate_json(where.read_text(encoding="utf-8"))
    assert kept.became_a_recording is False
    assert kept.faults == faults
    assert kept.receipt is not None
    assert kept.receipt.calls > 0
    assert kept.done is not None
    assert kept.done.reason
    assert kept.graph is not None
    assert kept.prompt_hash
    # The two numbers that are on no event and in no recording.
    assert kept.transcript.lines
    assert all(one.seconds >= 0 for one in kept.transcript.lines)
    assert any(one.thinking_tokens > 0 for one in kept.transcript.lines)
    # And the events themselves, so a run nobody can afford to repeat can be read.
    assert kept.events


def test_the_running_total_is_the_money_actually_spent_so_far(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bug this is a fence against: every progress line read $0.00.

    A run that spent $1.32 printed a running total of nothing on every line of it,
    because the figure was read off the transcript's own receipt, which is filled
    in only at the very end. It is folded as the run goes now (2026-09-20).
    """
    monkeypatch.setattr(record, "DOLLARS_EVERY", 1)
    said: list[str] = []
    run_one(
        "hormuz",
        answerer=a_run_that_shows_none(),  # type: ignore[arg-type]
        cap=15.0,
        on=A_DAY,
        seed=20261001,
        say=said.append,
    )

    totals = [one for one in said if "so far:" in one]
    assert totals
    assert not any("$0.00" in one for one in totals)
    assert all("calls" in one and "searches" in one for one in totals)


def test_what_a_run_cost_is_said_out_loud_whatever_becomes_of_it() -> None:
    """A figure nobody wrote down is a figure somebody pays for twice."""
    said = what_it_cost(a_run(a_run_that_shows_none()))  # type: ignore[arg-type]

    printed = "\n".join(said)
    assert "dollars" in printed
    assert "calls" in printed
    assert "searches" in printed
    assert "thinking" in printed
    assert "it stopped" in printed
    assert "it built" in printed


def test_a_run_that_shows_a_refusal_becomes_a_recording(tmp_path: Path) -> None:
    """And the header names the map's own minted identifier, never the example's name."""
    run = a_run(a_run_that_shows_a_refusal())

    assert faults_of(run) == ()  # type: ignore[arg-type]

    written = write_recording(run, folder=tmp_path)  # type: ignore[arg-type]
    lines = written.read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])

    assert header["base_id"] not in ("hormuz", "")
    assert header["seed"] == 20261001
    assert header["recording_date"] == A_DAY.isoformat()
    on_the_wire = [json.loads(one)["event"] for one in lines[1:]]
    assert on_the_wire[0] == "generation_started"
    assert on_the_wire[-1] == "done"
    assert any(json.loads(one)["event"] == "proposal_rejected" for one in lines[1:])
    assert not any(json.loads(one)["event"] == "beliefs_propagated" for one in lines[1:])


def test_a_measurement_run_is_kept_and_writes_no_recording(tmp_path: Path) -> None:
    """One code path, one flag: a run meant as a measurement is not a failed recording."""
    run = a_run(a_run_that_shows_a_refusal())
    as_a_measurement = ("This was a measurement run, so no recording was written.",)

    where = keep(run, as_a_measurement, folder=tmp_path)  # type: ignore[arg-type]

    kept = KeptRun.model_validate_json(where.read_text(encoding="utf-8"))
    assert kept.became_a_recording is False
    assert kept.faults == as_a_measurement
    assert kept.receipt is not None
    assert list(tmp_path.glob("*.jsonl")) == []


def test_every_kept_run_gets_its_own_file(tmp_path: Path) -> None:
    """Two runs of one example are two measurements, and neither overwrites the other."""
    keep(a_run(a_run_that_shows_none()), (), folder=tmp_path)  # type: ignore[arg-type]
    keep(a_run(a_run_that_shows_none()), (), folder=tmp_path)  # type: ignore[arg-type]

    assert len(list(tmp_path.glob("hormuz-*.json"))) >= 1
    assert all(one.stat().st_size > 0 for one in tmp_path.glob("*.json"))
