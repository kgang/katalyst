"""Playing a recording back: line for line, the same world twice, and labelled as a replay.

Every test here runs against a recording written into a throwaway directory from
`tests/unit/engine/a_recording.py`. When real recordings land under
`backend/recordings/` the same statements hold of them — the corpus the chapter
names is that folder, and this is a second, smaller corpus of one, so that every
rule about replay is provable today with no key and no money.
"""

import json
from pathlib import Path

import pytest

from katalyst.engine import events, replay
from katalyst.engine.events import BeliefsPropagated, Done, ProposalRejected, Receipt
from katalyst.engine.prompt import prompt_hash
from tests.unit.engine.a_recording import MADE_ON, THE_SENTENCE, written_to

SMALL = (16, 4)
"""Loop sizes small enough for a test and large enough to produce a spread."""


@pytest.fixture
def recorded(tmp_path: Path) -> replay.Recording:
    """One recording, in a directory nobody else can see."""
    return replay.read(written_to(tmp_path / "recordings"))


def test_replay_stream_matches_recording(recorded: replay.Recording) -> None:
    """The events a replay emits are the file's own, name for name and payload for payload.

    Except the two the file does not hold: the receipt, which is rebuilt, and the
    likelihoods, which are recomputed.
    """
    played = list(replay.play(recorded))

    assert [events.name_of(one) for one in played] == [name for name, _ in recorded.lines]
    for (_, written), emitted in zip(recorded.lines, played, strict=True):
        if isinstance(emitted, Receipt):
            continue
        assert json.loads(emitted.model_dump_json()) == written


def test_a_recording_holds_no_world_and_the_replay_computes_one(
    recorded: replay.Recording,
) -> None:
    """The one event a recording never stores, because a stored number goes stale in silence."""
    assert events.NAMES[BeliefsPropagated] not in {name for name, _ in recorded.lines}

    worked_through = replay.beliefs_of(recorded, SMALL)

    assert isinstance(worked_through, BeliefsPropagated)
    assert set(worked_through.world.beliefs) == {
        one.id for one in replay.map_of(recorded).propositions
    }


def test_replay_is_byte_identical_across_runs(recorded: replay.Recording) -> None:
    """Two replays of one file give the same world, down to the bytes."""
    once = replay.beliefs_of(recorded, SMALL).world
    twice = replay.beliefs_of(recorded, SMALL).world

    assert once.model_dump_json() == twice.model_dump_json()


def test_replay_is_labelled_in_receipt(recorded: replay.Recording) -> None:
    """A replay made no calls, and the receipt says exactly that."""
    receipt = next(one for one in replay.play(recorded) if isinstance(one, Receipt))

    assert receipt.mode == "replay"
    assert receipt.dollars == 0.0
    assert (receipt.calls, receipt.input_tokens, receipt.output_tokens) == (0, 0, 0)
    assert (receipt.cache_read_tokens, receipt.searches) == (0, 0)
    assert receipt.recording_date == MADE_ON
    assert receipt.prompt_hash == recorded.header.prompt_hash
    # The model that actually wrote this map is kept: the reader is entitled to it.
    assert receipt.model


def test_every_recording_shows_a_miss(recorded: replay.Recording) -> None:
    """Watching the rules refuse the model is half of what this product is."""
    refusals = [
        payload for name, payload in recorded.lines if name == events.NAMES[ProposalRejected]
    ]

    assert refusals
    assert all(one["violations"] for one in refusals)


def test_every_recording_carries_the_current_prompt_hash(recorded: replay.Recording) -> None:
    """A recording made against different words shows wording this program no longer uses."""
    assert recorded.header.prompt_hash == prompt_hash()
    assert replay.faults_in(recorded, current_prompt_hash=prompt_hash()) == []


def test_a_recording_made_against_another_prompt_is_named_as_stale(
    recorded: replay.Recording,
) -> None:
    """The silence record 0012 feared, turned into a sentence."""
    faults = replay.faults_in(recorded, current_prompt_hash="a-different-prompt")

    assert any("Record it again" in one for one in faults)


def test_a_recording_that_shows_no_miss_is_named(tmp_path: Path) -> None:
    """The fence against recording only the runs that went beautifully."""
    written = written_to(tmp_path / "recordings")
    kept = [
        one
        for one in written.read_text(encoding="utf-8").splitlines()
        if '"proposal_rejected"' not in one
    ]
    written.write_text("\n".join(kept) + "\n", encoding="utf-8")

    faults = replay.faults_in(replay.read(written), current_prompt_hash=prompt_hash())

    assert any("shows no refusal" in one for one in faults)


def test_a_recording_that_stores_likelihoods_is_named(tmp_path: Path) -> None:
    """A stored number could one day disagree with the engine that is running."""
    written = written_to(tmp_path / "recordings")
    with written.open("a", encoding="utf-8") as adding:
        adding.write(json.dumps({"event": "beliefs_propagated", "data": {}}) + "\n")

    faults = replay.faults_in(replay.read(written), current_prompt_hash=prompt_hash())

    assert any("stores likelihoods" in one for one in faults)


def test_which_recording_plays_is_the_sentence_and_never_a_guess(tmp_path: Path) -> None:
    """Playing one map back at somebody who asked about something else is worse than saying no."""
    folder = tmp_path / "recordings"
    written_to(folder)

    assert replay.find(THE_SENTENCE, folder) is not None
    assert replay.find(f"  {THE_SENTENCE}  ", folder) is not None
    assert replay.find("Photonic chips get adopted faster than expected.", folder) is None
    assert replay.find(THE_SENTENCE[:-10], folder) is None


def test_what_can_be_replayed_is_listed_with_the_day_it_was_made(tmp_path: Path) -> None:
    """The first screen names a date before anything runs, which the receipt cannot."""
    folder = tmp_path / "recordings"
    written_to(folder)

    listed = replay.summaries(folder)

    assert [(one.example, one.recording_date) for one in listed] == [("hormuz", MADE_ON)]


def test_an_empty_folder_gives_nothing_and_complains_about_nothing(tmp_path: Path) -> None:
    """Which is what lets the build's own check be green from the commit that adds it."""
    assert replay.every_recording(tmp_path) == ()
    assert replay.summaries(tmp_path) == ()


def test_pacing_is_a_setting_and_never_a_field_on_a_request() -> None:
    """A client that could ask for an instant replay could skip what a recording is for."""
    assert replay.seconds_between(instant=True) == 0.0
    assert replay.seconds_between(instant=False) > 0.0


def test_a_recording_ends_where_a_generation_ends(recorded: replay.Recording) -> None:
    """Every committed file ends in `done`; a run that broke is re-run, not committed."""
    assert recorded.lines[-1][0] == events.NAMES[Done]
