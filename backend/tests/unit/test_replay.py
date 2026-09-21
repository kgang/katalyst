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
from katalyst.settings import get_settings
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


def test_a_recording_holds_every_refusal_that_happened(
    recorded: replay.Recording,
) -> None:
    """Kent, 2026-09-20: a recording shows the refusals that happened, and no others.

    The rule used to be that every recording must show at least one. It made the
    only staged thing on the disk: a run re-run until the model erred. So the rule
    is now about honesty rather than quantity — a refusal in the file must name the
    rules it broke, and a run where the model never erred is a recording too.
    """
    refusals = [
        payload for name, payload in recorded.lines if name == events.NAMES[ProposalRejected]
    ]

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


def test_a_recording_that_shows_no_miss_is_sound(tmp_path: Path) -> None:
    """The other half of the same decision, from the reading end.

    A run in which the rules never had to refuse anything is a true run, and its
    recording plays back like any other.
    """
    written = written_to(tmp_path / "recordings")
    kept = [
        one
        for one in written.read_text(encoding="utf-8").splitlines()
        if '"proposal_rejected"' not in one
    ]
    written.write_text("\n".join(kept) + "\n", encoding="utf-8")

    faults = replay.faults_in(replay.read(written), current_prompt_hash=prompt_hash())

    assert faults == []


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


def test_where_recordings_are_read_from_is_a_setting_and_not_a_patch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recording is checked by playing it, and that needs somewhere else to play it from.

    Before this there was no way to point a running program at a folder of its
    own: the path was decided when the module was written, so trying a recording
    before committing it meant editing the code that reads it (2026-09-20).
    """
    somewhere_else = tmp_path / "somewhere-else"
    written_to(somewhere_else)
    monkeypatch.setenv("KATALYST_RECORDINGS", str(somewhere_else))
    get_settings.cache_clear()

    try:
        assert replay.where_they_live() == somewhere_else
        assert replay.find(THE_SENTENCE) is not None
    finally:
        get_settings.cache_clear()


def test_with_no_setting_the_folder_is_the_one_that_ships() -> None:
    """Empty means the committed folder, which is what a fresh clone has."""
    get_settings.cache_clear()

    assert replay.where_they_live() == replay.RECORDINGS


# --- The three checks `replay.md` B9 names and nothing ran ---------------


def broken_into(tmp_path: Path, mend: object) -> replay.Recording:
    """Write the good recording with one line changed, and read it back."""
    written = written_to(tmp_path / "recordings")
    lines = written.read_text(encoding="utf-8").splitlines()
    written.write_text("\n".join(mend(lines)) + "\n", encoding="utf-8")  # type: ignore[operator]
    return replay.read(written)


def test_a_recording_that_hides_its_receipt_at_the_end_is_named(tmp_path: Path) -> None:
    """Grammar rule 2: the receipt is second to last, so nobody reaches the end untold."""
    moved = broken_into(tmp_path, lambda lines: [*lines[:-2], lines[-1], lines[-2]])

    faults = replay.faults_in(moved, current_prompt_hash=prompt_hash())

    assert any("second to last" in one for one in faults)


def test_a_recording_that_numbers_its_proposals_out_of_order_is_named(
    tmp_path: Path,
) -> None:
    """A reader cannot tell what order they arrived in, which is what `at` is for."""
    jumbled = broken_into(
        tmp_path, lambda lines: [one.replace('"at": 0', '"at": 9') for one in lines]
    )

    faults = replay.faults_in(jumbled, current_prompt_hash=prompt_hash())

    assert any("rising line" in one for one in faults)


def test_a_recording_no_card_would_ever_play_is_named(tmp_path: Path) -> None:
    """The file's name is one of the four, or no card reaches it."""
    written = written_to(tmp_path / "recordings")
    renamed = written.rename(written.with_name("something-else.jsonl"))

    faults = replay.faults_in(replay.read(renamed), current_prompt_hash=prompt_hash())

    assert any("no card would ever play it" in one for one in faults)


def test_every_reason_at_once_and_never_the_first(tmp_path: Path) -> None:
    """The docstring has always said so, and a `break` in the middle said otherwise."""
    wrong = broken_into(
        tmp_path,
        lambda lines: [
            lines[0],
            *[one.replace('"reason"', '"nonsense"') for one in lines[1:]],
        ],
    )

    faults = replay.faults_in(wrong, current_prompt_hash="a-different-prompt")

    assert len(faults) > 1
    assert any("Record it again" in one for one in faults)
