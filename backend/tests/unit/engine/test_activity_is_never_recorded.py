"""Activity is live only, and every clause of that sentence has a test here.

One kind of line on the stream is not part of the generation: `activity`, which
says what a model call is doing this second. It is sent while a run is happening
and it is **never written to a recording, a transcript or a kept run, never
replayed, never invented by a replay, never billed and never counted by `at`**
(record 0027, Kent's R44 and R47, 2026-09-22).

That is a promise made in six clauses, so it is kept in six tests. Three of them
are here, about files: what the committed recordings hold, what the recorder
refuses to write, and what a replay refuses to play. The other three are about
the wire and live beside the route's own tests.

Nothing here talks to a network, and nothing here needs a key.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from katalyst.engine import events, record, replay
from katalyst.engine.events import ACTIVITY, BY_NAME, NAMES, Activity, Event
from katalyst.engine.prompt import prompt_hash
from katalyst.engine.record import NotSomethingARecordingHolds, run_one, write_recording
from tests.unit.engine.a_recording import written_to
from tests.unit.engine.answers import (
    FROM_THE_QUESTION,
    Storyteller,
    a_claim,
    a_link,
    a_starting_claim,
    a_stop,
    an_answer,
)

A_DAY = date(2026, 9, 17)
"""The day every run here pretends to be happening on."""

A_STEP = "A step in the middle of the story."
AN_ENDING = "Something you could put money on."

A_SEARCH = Activity(about=None, kind="searching", text="Lloyd's JWC Hormuz premium 2026")
"""One line of the kind this test is about, built the way the route builds them."""


def a_whole_story() -> Storyteller:
    """One short generation, told to the seam instead of asked of a model."""
    hormuz = record.THE_FOUR["hormuz"]
    return Storyteller(
        {
            hormuz: [
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
            an_answer(a_starting_claim(hormuz), read_fresh=300, written=700),
            an_answer(a_starting_claim("Iran is struck the next day."), read_fresh=310),
        ],
        joining=[an_answer(a_link("Iran is struck the next day.", AN_ENDING))],
    )


# --- The eight are one list and the ninth is not on it ----------------------


def test_activity_is_not_one_of_the_eight() -> None:
    """The tables a recording is written and read through do not know the name.

    This is the whole mechanism. A recording is written from `NAMES` and read
    through `BY_NAME`, so a name that is in neither cannot be written by this
    program or read back by it, whatever anybody remembers to check.
    """
    assert Activity not in NAMES
    assert ACTIVITY not in BY_NAME
    assert ACTIVITY not in set(NAMES.values())


def test_the_ninth_still_goes_on_the_wire_the_way_the_eight_do() -> None:
    """Two lines and a blank one, one line of JSON, no second framing to keep in step."""
    written = events.framed(A_SEARCH)

    assert written.startswith(f"event: {ACTIVITY}\ndata: ")
    assert written.endswith("\n\n")
    payload = json.loads(written.splitlines()[1].removeprefix("data: "))
    assert payload == {"about": None, "kind": "searching", "text": A_SEARCH.text}


def test_an_activity_line_carries_no_transcript_counter() -> None:
    """`at` counts what was proposed, and activity proposes nothing."""
    assert "at" not in json.loads(A_SEARCH.model_dump_json())


# --- No recording holds one -------------------------------------------------


def test_no_committed_recording_holds_an_activity_line() -> None:
    """Checked over every file this program ships, not over a fixture of our own."""
    committed = sorted(replay.RECORDINGS.glob("*.jsonl"))

    assert committed, "there are no committed recordings to check"
    for path in committed:
        names = [
            json.loads(line).get("event")
            for line in path.read_text(encoding="utf-8").splitlines()[1:]
        ]
        assert ACTIVITY not in names, f"{path.name} holds an activity line"
        assert replay.faults_in(replay.read(path), current_prompt_hash=prompt_hash()) == []


# --- The recorder refuses to write one --------------------------------------


def test_the_recorder_refuses_to_write_an_activity_line(tmp_path: Path) -> None:
    """A guard, not a thing that happens: activity never reaches a run's events at all.

    It cannot, because a run's events come from the follower that reads the walk
    and activity never goes near it. So the run here is bent by hand into the
    state the guard exists for, which is the only way to reach it.
    """
    run = run_one(
        "hormuz",
        answerer=a_whole_story(),  # type: ignore[arg-type]
        cap=15.0,
        on=A_DAY,
        seed=20261001,
        keep_in=tmp_path,
        say=lambda _: None,
    )
    bent = run.model_copy(update={"events": (*run.events, A_SEARCH)})

    with pytest.raises(NotSomethingARecordingHolds) as refused:
        write_recording(bent, folder=tmp_path)

    assert "never written down" in str(refused.value)
    assert not (tmp_path / "hormuz.jsonl").exists()


def test_a_run_with_no_activity_still_records(tmp_path: Path) -> None:
    """The guard refuses one thing and nothing else — the ordinary run still writes."""
    run = run_one(
        "hormuz",
        answerer=a_whole_story(),  # type: ignore[arg-type]
        cap=15.0,
        on=A_DAY,
        seed=20261001,
        keep_in=tmp_path,
        say=lambda _: None,
    )

    written = write_recording(run, folder=tmp_path)

    assert written.exists()


def test_a_kept_run_holds_no_activity_line(tmp_path: Path) -> None:
    """Not a recording either: the file a paid run leaves behind holds the eight.

    The kept run is the richer file — it carries the seconds and the thinking
    tokens behind every call — and it is still the record of what a generation
    *decided*.
    """
    run_one(
        "hormuz",
        answerer=a_whole_story(),  # type: ignore[arg-type]
        cap=15.0,
        on=A_DAY,
        seed=20261001,
        keep_in=tmp_path,
        say=lambda _: None,
    )

    kept = json.loads(next(tmp_path.glob("hormuz-*.json")).read_text(encoding="utf-8"))

    assert kept["events"]
    assert not [one for one in kept["events"] if set(one) >= {"kind", "text"}]


# --- A replay refuses to play one, and invents none --------------------------


def _a_recording_somebody_put_activity_into(folder: Path) -> Path:
    """Write a recording with one activity line in the middle of it.

    Nothing in this program can produce this file. It is written by hand here
    because the refusal is the thing under test, and a refusal nobody can trigger
    is a refusal nobody has checked.

    Args:
        folder: Where to write it.

    Returns:
        The file.
    """
    path = written_to(folder)
    lines = path.read_text(encoding="utf-8").splitlines()
    doctored = [
        *lines[:3],
        json.dumps({"event": ACTIVITY, "data": json.loads(A_SEARCH.model_dump_json())}),
        *lines[3:],
    ]
    path.write_text("\n".join(doctored) + "\n", encoding="utf-8")
    return path


def test_a_recording_holding_an_activity_line_is_refused_by_name(tmp_path: Path) -> None:
    """Refused, and told why in words that name the thing rather than guessing at an age."""
    recording = replay.read(_a_recording_somebody_put_activity_into(tmp_path))

    why = replay.why_it_cannot_be_played(recording)

    assert why is not None
    assert ACTIVITY in why
    assert "never written down" in why
    assert any(ACTIVITY in one for one in replay.faults_in(recording, current_prompt_hash="any"))


def test_playing_a_recording_with_an_activity_line_stops_rather_than_replaying_it(
    tmp_path: Path,
) -> None:
    """A replay shows what a generation decided. There is nothing of activity to show."""
    recording = replay.read(_a_recording_somebody_put_activity_into(tmp_path))

    with pytest.raises(replay.CannotBeRead) as refused:
        list(replay.play(recording))

    assert ACTIVITY in refused.value.why


def test_a_replay_invents_no_activity(tmp_path: Path) -> None:
    """The ordinary file, played through: the eight and nothing beside them."""
    recording = replay.read(written_to(tmp_path))

    played: list[Event] = list(replay.play(recording))

    assert played
    assert not [one for one in played if isinstance(one, Activity)]
    assert {events.name_of(one) for one in played} <= set(NAMES.values())
