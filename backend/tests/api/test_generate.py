"""The three routes a generation is asked for, watched and read back through.

Every test here runs with **no key**, which is the point: with none configured
the route plays a recording back, and the recording is written into a throwaway
directory from the fake answers the pipeline's own tests use. So the whole stream
— its grammar, its terminator, its refusals, its receipt — is provable today
without a model, a network or a penny.
"""

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from katalyst.api import generate
from katalyst.api.main import app
from katalyst.engine import replay
from katalyst.engine.grow import grow
from katalyst.engine.outcome import Caps
from katalyst.engine.transcript import HOW_MANY_GENERATIONS_A_PROCESS_KEEPS, held
from katalyst.settings import get_settings
from tests.unit.engine.a_recording import A_MAP, THE_SCRIPTED_INSERT, THE_SENTENCE, written_to
from tests.unit.engine.answers import (
    FROM_THE_QUESTION,
    Scripted,
    Storyteller,
    a_claim,
    a_declined_answer,
    a_link,
    a_starting_claim,
    a_stop,
    an_answer,
)

SMALL: dict[str, int] = {"versions": 16, "worlds": 4}
"""Loop sizes small enough for a test and large enough to produce a spread."""

STARTED_AT = "Something a person expects."
A_STEP = "A step in the middle of the story."
AN_ENDING = "Something you could put money on."


def a_story() -> Storyteller:
    """One short generation, told to the seam instead of asked of a model."""
    return Storyteller(
        {
            STARTED_AT: [
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
        starting=[an_answer(a_starting_claim(STARTED_AT), read_fresh=300, written=700)],
    )


@pytest.fixture(autouse=True)
def a_copy_with_recordings_and_no_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Run every test against a program with recordings on disk and nothing configured."""
    folder = tmp_path / "recordings"
    written_to(folder)
    monkeypatch.setattr(replay, "RECORDINGS", folder)
    monkeypatch.setenv("KATALYST_REPLAY_INSTANT", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    held.forget_everything()
    yield
    get_settings.cache_clear()
    held.forget_everything()


def client() -> TestClient:
    """A client for the whole application, routes mounted as they really are."""
    return TestClient(app)


def stream(**asked: Any) -> list[tuple[str, dict[str, Any]]]:
    """Ask for a generation and read every event off the wire.

    Reads the two lines the way a browser does rather than the way the server
    wrote them, so the framing itself is under test.
    """
    body = {"hypothesis": THE_SENTENCE, **SMALL, **asked}
    with client().stream("POST", "/api/generate", json=body) as answer:
        assert answer.status_code == 200
        assert answer.headers["content-type"].startswith("text/event-stream")
        assert answer.headers["cache-control"] == "no-store"
        read: list[tuple[str, dict[str, Any]]] = []
        name: str | None = None
        for line in answer.iter_lines():
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                assert name is not None
                read.append((name, json.loads(line.removeprefix("data: "))))
                name = None
        return read


def test_generate_needs_no_key_in_replay_mode() -> None:
    """The whole route answers with nothing configured, which is the keyless promise."""
    read = stream()

    assert read
    assert next(name for name, _ in read) == "generation_started"


def test_generate_streams_events_in_order() -> None:
    """The grammar: it starts, it grows, it works the numbers through, it pays, it stops."""
    names = [name for name, _ in stream()]

    assert names[0] == "generation_started"
    growth = [one for one in names if one in ("proposal_accepted", "proposal_rejected")]
    assert growth
    assert names.index("beliefs_propagated") > names.index(growth[-1] if False else growth[0])
    assert names[-2:] == ["receipt", "done"]
    # Nothing grows after the numbers have been worked through.
    after = names[names.index("beliefs_propagated") :]
    assert not [one for one in after if one in ("proposal_accepted", "proposal_rejected")]


def test_the_stream_ends_with_done_or_failed() -> None:
    """Exactly one terminator, and it is last."""
    names = [name for name, _ in stream()]

    assert names.count("done") + names.count("failed") == 1
    assert names[-1] in ("done", "failed")


def test_beliefs_arrive_once_after_the_map_is_built() -> None:
    """A chip that changes as its causes arrive has shown numbers nobody computed."""
    names = [name for name, _ in stream()]

    assert names.count("beliefs_propagated") == 1


def test_a_rejected_proposal_is_an_event_not_an_error() -> None:
    """The answer stays 200 and the run carries on, carrying every reason at once."""
    read = stream()

    refusals = [payload for name, payload in read if name == "proposal_rejected"]
    assert refusals
    assert all(one["violations"] for one in refusals)
    assert all(one["violations"][0]["code"] for one in refusals)
    assert [name for name, _ in read][-1] == "done"


def test_both_growth_events_say_what_is_still_open() -> None:
    """So a claim closed by its third failure loses its reserved rectangle at once."""
    read = stream()

    growth = [
        payload for name, payload in read if name in ("proposal_accepted", "proposal_rejected")
    ]
    assert growth
    assert all("frontier" in one for one in growth)


def test_the_transcript_counter_rises_by_one_across_both_growth_events() -> None:
    """One counter, because a refusal is a thing that was proposed."""
    read = stream()

    counted = [
        payload["at"]
        for name, payload in read
        if name in ("proposal_accepted", "proposal_rejected")
    ]
    assert counted == list(range(len(counted)))


def test_a_sentence_with_no_recording_says_so_rather_than_guessing() -> None:
    """Playing one map back at somebody who asked about something else is worse than no."""
    read = stream(hypothesis="Photonic chips get adopted faster than expected.")

    # The receipt comes before it, as it does before every ending: grammar rule 2
    # puts it second to last in both, and zero is the honest answer here.
    assert [name for name, _ in read] == ["receipt", "failed"]
    assert "no recording of that sentence" in read[-1][1]["message"]


def test_the_receipt_says_the_run_was_a_replay_and_cost_nothing() -> None:
    """Every generation records what it cost. A replay's answer to that is zero."""
    receipt = next(payload for name, payload in stream() if name == "receipt")

    assert receipt["mode"] == "replay"
    assert receipt["dollars"] == 0.0
    assert receipt["calls"] == 0
    assert receipt["searches"] == 0
    assert receipt["recording_date"]


def test_a_run_above_the_loop_ceilings_is_refused_not_clamped() -> None:
    """A caller who asks for one run and gets a smaller one is reading another answer."""
    from katalyst.engine.worlds import MOST_VERSIONS, MOST_WORLDS

    too_many = client().post(
        "/api/generate", json={"hypothesis": THE_SENTENCE, "versions": MOST_VERSIONS + 1}
    )
    too_wide = client().post(
        "/api/generate", json={"hypothesis": THE_SENTENCE, "worlds": MOST_WORLDS + 1}
    )

    assert too_many.status_code == 422
    assert too_wide.status_code == 422
    assert "versions" in json.dumps(too_many.json())
    assert "worlds" in json.dumps(too_wide.json())


def test_the_same_ceilings_hold_on_the_world_routes() -> None:
    """One bound, wherever the loop sizes are asked for."""
    from katalyst.engine.worlds import MOST_VERSIONS

    refused = client().post(
        "/api/worlds",
        json={"base_id": "hormuz", "seed": 1, "versions": MOST_VERSIONS + 1},
    )

    assert refused.status_code == 422


def test_the_transcript_of_a_generation_can_be_read_afterwards() -> None:
    """The working is a product artifact, not a log."""
    read = stream()
    announced = next(
        payload["generation_id"] for name, payload in read if name == "generation_started"
    )

    working = client().get(f"/api/generate/{announced}/transcript")

    assert working.status_code == 200
    assert working.json()["hypothesis"] == THE_SENTENCE
    assert working.json()["mode"] == "replay"
    assert working.json()["lines"]


def test_a_generation_this_process_no_longer_holds_says_so() -> None:
    """A restart is enough to cause it, and an empty transcript would read as a run
    that proposed nothing."""
    missing = client().get("/api/generate/never-ran/transcript")

    assert missing.status_code == 404
    assert "no longer holding" in missing.json()["detail"]


def test_intervention_on_replayed_world_needs_no_model() -> None:
    """Four of the five edits are pure arithmetic, so a keyless reviewer gets the multiverse."""
    stream()

    world = client().post("/api/worlds", json={"base_id": A_MAP, "seed": 20261001, **SMALL})
    supposed = client().post(
        "/api/worlds",
        json={
            "base_id": A_MAP,
            "seed": 20261001,
            **SMALL,
            "branch": {
                "id": "a-supposition",
                "label": "Suppose the strait opens",
                "interventions": [{"kind": "do", "target": "C", "value": True}],
            },
        },
    )

    assert world.status_code == 200
    assert supposed.status_code == 200
    assert supposed.json()["beliefs"] != world.json()["beliefs"]


def test_the_scripted_intervention_is_answered_and_anything_else_is_declined() -> None:
    """The one thing in a replayed flow that genuinely needs a key, said out loud."""
    scripted = client().post(
        "/api/generate/insert",
        json={"base_id": A_MAP, "claim_in_words": THE_SCRIPTED_INSERT, "position": 0},
    )
    anything_else = client().post(
        "/api/generate/insert",
        json={"base_id": A_MAP, "claim_in_words": "…but the moon turns blue", "position": 0},
    )

    stream()  # the map has to exist before anything can be added to it
    scripted = client().post(
        "/api/generate/insert",
        json={"base_id": A_MAP, "claim_in_words": THE_SCRIPTED_INSERT, "position": 0},
    )

    assert scripted.status_code == 200
    assert scripted.json()["insert"]["proposition"]["claim"]
    assert anything_else.status_code in (404, 501)
    assert (
        client()
        .post(
            "/api/generate/insert",
            json={"base_id": A_MAP, "claim_in_words": "…but the moon turns blue", "position": 0},
        )
        .json()["detail"]
        == "drafting a new claim needs a model key."
    )


def test_an_insert_is_validated_like_any_other_proposal() -> None:
    """A claim a person asked for is not held to a lower standard than one the model offered."""
    stream()

    onto_a_map_that_does_not_exist = client().post(
        "/api/generate/insert",
        json={"base_id": "no-such-map", "claim_in_words": THE_SCRIPTED_INSERT, "position": 0},
    )

    assert onto_a_map_that_does_not_exist.status_code == 404


def test_a_generations_identifier_sent_as_a_map_is_told_which_it_wanted() -> None:
    """The commonest wrong answer, answered rather than left to guess (2026-09-20).

    A run and the map it built are two different things, and one run's map
    outlives the question that made it — so an identifier that names the run gets
    a sentence naming both, not a bare 404.
    """
    read = stream()
    a_run = next(payload["generation_id"] for name, payload in read if name == "generation_started")

    refused = client().post(
        "/api/generate/insert",
        json={"base_id": a_run, "claim_in_words": THE_SCRIPTED_INSERT, "position": 0},
    )

    assert refused.status_code == 404
    said = refused.json()["detail"]
    assert "generation" in said
    assert "map" in said


def test_readyz_says_what_can_be_replayed_before_anything_runs() -> None:
    """Which is the only way the first screen can name the day a recording was made."""
    ready = client().get("/api/readyz").json()

    assert ready["model_key_present"] is False
    assert [one["example"] for one in ready["replayable"]] == ["hormuz"]
    assert ready["replayable"][0]["recording_date"]
    # A copy that can replay is not "not ready": it can do almost everything.
    assert ready["status"] == "ready"


# --- The live path, against answers written out by hand ----------------------
#
# The tests above run the replay path, which is what a keyless copy does. These
# run the live one, with the seam handed a script instead of a model: no key, no
# network, no money, and the route exercised exactly as it would be.


def a_scripted_run(monkeypatch: pytest.MonkeyPatch, told: object) -> None:
    """Make the route believe a model is configured, and hand it a script."""
    monkeypatch.setattr(generate, "live_answerer", lambda **_: told)


def test_a_live_run_streams_the_same_grammar_the_replay_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One route, one grammar, whichever side the bytes came from."""
    a_scripted_run(monkeypatch, a_story())

    names = [name for name, _ in stream(hypothesis="Something a person expects.")]

    assert names[0] == "generation_started"
    assert names[-2:] == ["receipt", "done"]
    assert names.count("beliefs_propagated") == 1


def test_a_live_runs_receipt_says_it_was_live_and_what_it_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every generation records what it cost, and a live one costs something."""
    a_scripted_run(monkeypatch, a_story())

    receipt = next(
        payload
        for name, payload in stream(hypothesis="Something a person expects.")
        if name == "receipt"
    )

    assert receipt["mode"] == "live"
    assert receipt["recording_date"] is None
    assert receipt["calls"] > 0
    assert receipt["prompt_hash"]


def test_the_seed_is_minted_when_the_request_leaves_it_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """So the run is reproducible from its first event, and the browser invents nothing."""
    a_scripted_run(monkeypatch, a_story())

    started = next(
        payload
        for name, payload in stream(hypothesis="Something a person expects.")
        if name == "generation_started"
    )

    assert isinstance(started["seed"], int)
    assert started["seed"] > 0


def test_a_seed_that_was_sent_is_the_seed_that_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Which is the one case where a seed means something to whoever sent it."""
    a_scripted_run(monkeypatch, a_story())

    started = next(
        payload
        for name, payload in stream(hypothesis="Something a person expects.", seed=4242)
        if name == "generation_started"
    )

    assert started["seed"] == 4242


def test_the_transcript_records_the_seconds_and_the_thinking_behind_every_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two numbers on no event, kept so the next full run says where its minutes went."""
    told = a_story()
    a_scripted_run(monkeypatch, told)

    read = stream(hypothesis="Something a person expects.")
    generation_id = next(
        payload["generation_id"] for name, payload in read if name == "generation_started"
    )
    working = client().get(f"/api/generate/{generation_id}/transcript").json()

    assert working["lines"]
    assert all("thinking_tokens" in one and "seconds" in one for one in working["lines"])
    assert any(one["thinking_tokens"] > 0 for one in working["lines"])


def test_a_line_the_model_had_nothing_more_to_say_about_makes_no_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing changed on the map, so there is nothing to tell — and the gaps show it."""
    told = a_story()
    a_scripted_run(monkeypatch, told)

    read = stream(hypothesis="Something a person expects.")
    generation_id = next(
        payload["generation_id"] for name, payload in read if name == "generation_started"
    )
    working = client().get(f"/api/generate/{generation_id}/transcript").json()

    stops = [one for one in working["lines"] if one["what"] == "stopped"]
    assert stops
    assert all(one["at"] is None for one in stops)
    on_the_wire = [
        payload["at"]
        for name, payload in read
        if name in ("proposal_accepted", "proposal_rejected")
    ]
    assert len(on_the_wire) == len(working["lines"]) - len(stops)


def test_the_stream_stops_calling_the_model_when_the_client_goes_away(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing in flight is retried, nothing is re-asked, and no further money is spent.

    Read as the walk itself, because that is where the spending happens: the route
    stops reading, the generator is closed, and a closed generator asks nothing
    else. A flag the route had to remember to check would be a flag somebody
    eventually forgets.
    """
    told = a_story()
    walking = grow(
        "Something a person expects.",
        answerer=told,  # type: ignore[arg-type]
        on=date(2026, 9, 17),
        caps=Caps(at_once=1),
    )
    next(walking)
    next(walking)
    asked_before_it_went = len(told.asked)

    walking.close()

    assert len(told.asked) == asked_before_it_went
    assert asked_before_it_went > 0


# --- A live run that breaks still ends in one plain sentence ---------------


def a_live_run(monkeypatch: pytest.MonkeyPatch, answerer: object) -> list[tuple[str, Any]]:
    """Stream one generation against a stand-in answerer rather than a recording."""
    monkeypatch.setattr(generate, "live_answerer", lambda **_: answerer)
    return stream(hypothesis="A sentence with no recording behind it.")


def test_a_live_run_the_model_never_answers_ends_with_one_plain_sentence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kent, 2026-09-20: never a stack trace, and never a lie about whose fault it was.

    The stream used to die where the exception was raised: no receipt, no last
    event, and a browser left waiting on a connection that had already gone.
    """
    from katalyst.engine.client import TheModelDidNotAnswer

    read = a_live_run(
        monkeypatch,
        Scripted(raises=TheModelDidNotAnswer("The model is busy and turned this question away.")),
    )

    names = [name for name, _ in read]
    assert names[-1] == "failed"
    assert "receipt" in names
    said = read[-1][1]["message"]
    assert "busy" in said
    assert "Traceback" not in said
    assert "Error" not in said


def test_a_live_run_that_breaks_some_other_way_still_ends_the_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bug of our own is not a reason to hang up on somebody mid-map."""

    class Exploding:
        """An answerer that fails in a way nobody planned for."""

        effort_used = "default"

        def watching(self, spent: object, cap: float) -> None:
            """Take note of nothing."""

        def starting_claim(self, question: str, *, may_search: bool = True) -> object:
            """Fail in a way the seam does not know about."""
            raise RuntimeError("a bug nobody wrote a sentence for")

        def proposal(self, question: str, *, may_search: bool) -> object:
            """Fail in a way the seam does not know about."""
            raise RuntimeError("a bug nobody wrote a sentence for")

    read = a_live_run(monkeypatch, Exploding())

    names = [name for name, _ in read]
    assert names[-1] == "failed"
    said = read[-1][1]["message"]
    assert "a bug nobody wrote a sentence for" not in said
    assert "RuntimeError" not in said


def test_a_run_that_empties_the_purse_before_it_has_a_map_still_says_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-generation.6, for the case it was written for and did not hold in.

    Stopping because the money ran out is a decision, not a fault, whether it
    runs out on call forty or call one — `events.py` says so in as many words.
    A run that emptied the purse on its first question used to end in `failed`,
    which reads as "something broke" for the one ending nobody should read that
    way (2026-09-20).
    """
    expensive = a_declined_answer("Not this one.", written=400_000)
    monkeypatch.setattr(generate, "live_answerer", lambda **_: Scripted(starting=[expensive]))
    monkeypatch.setattr(generate, "Caps", lambda: Caps(dollars=1.0))

    read = stream(hypothesis="A sentence with no recording behind it.")

    names = [name for name, _ in read]
    assert names[-1] == "done"
    assert "failed" not in names
    assert read[-1][1]["reason"] == "spend_cap"
    assert read[-1][1]["claims"] == 0


# --- Nothing a run paid for is lost, whatever ends it ----------------------


class AnswersThenBreaks:
    """A stand-in that answers a few questions for real money and then the walk breaks.

    What a bug of ours looks like: everything up to the break was asked,
    answered and billed. It breaks where the walk asks what is left in the
    purse, which is outside the part of a round that turns a failure into a
    refusal — so the whole walk stops, which is the case finding 1 is about.
    """

    effort_used = "default"
    """The plain word a receipt shows. A stand-in asks nobody anything."""

    def __init__(self, *, after: int) -> None:
        """Set out how many questions to answer before the walk breaks."""
        self._story = a_story()
        self._after = after
        self.calls = 0

    def watching(self, spent: object, cap: float) -> None:
        """Take note of the purse, or break once enough has been spent on it."""
        if self.calls >= self._after:
            raise RuntimeError("a bug nobody wrote a sentence for")

    def starting_claim(self, question: str, *, may_search: bool = True) -> Any:
        """Answer, and count the call."""
        self.calls += 1
        return self._story.starting_claim(question, may_search=may_search)

    def proposal(self, question: str, *, may_search: bool) -> Any:
        """Answer, and count the call."""
        self.calls += 1
        return self._story.proposal(question, may_search=may_search)


def test_a_run_that_breaks_still_says_what_it_spent(monkeypatch: pytest.MonkeyPatch) -> None:
    """`streaming.md` rule 2: a run that broke after ten calls still cost ten calls.

    The receipt came out of a run that had made four billed calls reading
    `calls: 0, dollars: 0.0, model: ""`, because the only receipt anybody had was
    the one the walk hands back at the end — and a walk that breaks hands nothing
    back. The running total has to leave the walk as it goes (2026-09-20).
    """
    answerer = AnswersThenBreaks(after=2)
    monkeypatch.setattr(generate, "live_answerer", lambda **_: answerer)

    read = stream(hypothesis="A sentence with no recording behind it.")

    names = [name for name, _ in read]
    assert names[-1] == "failed"
    assert names[-2] == "receipt"
    paid = read[-2][1]
    assert paid["calls"] == answerer.calls > 0
    assert paid["dollars"] > 0
    assert paid["model"]


def test_a_run_that_breaks_leaves_its_working_behind_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The transcript is a product artifact and it is read after the fact."""
    answerer = AnswersThenBreaks(after=2)
    monkeypatch.setattr(generate, "live_answerer", lambda **_: answerer)

    read = stream(hypothesis="A sentence with no recording behind it.")
    announced = next(
        payload["generation_id"] for name, payload in read if name == "generation_started"
    )

    working = client().get(f"/api/generate/{announced}/transcript").json()

    assert working["receipt"] is not None
    assert working["receipt"]["calls"] == answerer.calls > 0
    assert working["lines"]


def test_a_replay_with_nothing_to_play_still_says_what_it_spent() -> None:
    """Grammar rule 2 and INV-generation.16: `receipt` is second-to-last in both endings.

    Nothing was spent, and a receipt of zeroes says exactly that. A stream that
    simply has no receipt says nothing at all, and a reader cannot tell it from
    one that forgot.
    """
    read = stream(hypothesis="A sentence nothing was ever recorded for.")

    names = [name for name, _ in read]
    assert names[-1] == "failed"
    assert names[-2] == "receipt"
    assert read[-2][1]["calls"] == 0
    assert read[-2][1]["dollars"] == 0.0


def test_a_reader_who_goes_away_mid_round_still_leaves_the_bill_behind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Through the route, which is where this was never checked (2026-09-20).

    Three questions of a round go out together and are all billed before the
    first of them is folded. A reader who closes the tab stops the **asking**;
    it cannot unspend what is already spent, so everything paid for is on the
    transcript and its receipt before the run is let go of.

    The old test for this asserted on the engine and never touched the route:
    deleting the disconnect check left it green.
    """
    told = a_story()
    monkeypatch.setattr(generate, "live_answerer", lambda **_: told)

    with client().stream(
        "POST", "/api/generate", json={"hypothesis": STARTED_AT, **SMALL}
    ) as answer:
        assert answer.status_code == 200
        announced = None
        for line in answer.iter_lines():
            if line.startswith("data: ") and announced is None:
                announced = json.loads(line.removeprefix("data: "))["generation_id"]
                break
        # And here the reader goes away, mid-run, with the round in flight.

    assert announced is not None
    working = client().get(f"/api/generate/{announced}/transcript").json()

    assert working["receipt"] is not None
    assert working["receipt"]["calls"] == len(told.asked)
    assert len(working["lines"]) == len(told.asked)


# --- One unreadable file never takes the keyless product with it ----------


def a_file_nobody_can_read(tmp_path: Path, written: str) -> None:
    """Put a recording that cannot be read beside the good one."""
    (tmp_path / "recordings" / "broken.jsonl").write_text(written, encoding="utf-8")


BROKEN_RECORDINGS = {
    "a header from an older engine": '{"base_id": "x"}\n',
    "an event nobody knows": (
        '{"base_id":"x","seed":1,"recording_date":"2026-09-17","prompt_hash":"h",'
        '"hypothesis":"Something.","insert":null}\n{"event":"weather_changed","data":{}}\n'
    ),
    "a payload that does not fit its event": (
        '{"base_id":"x","seed":1,"recording_date":"2026-09-17","prompt_hash":"h",'
        '"hypothesis":"Something.","insert":null}\n{"event":"done","data":{"reason":"nonsense"}}\n'
    ),
    "nothing at all": "\n",
}
"""Four ways a recording can be unreadable, and every one of them has happened.

A file from an older engine, a file from a newer one, a file somebody truncated.
None of them is exotic: a recording is a committed file that outlives the code
that wrote it, which is the whole point of having them.
"""


@pytest.mark.parametrize("broken", list(BROKEN_RECORDINGS), ids=list(BROKEN_RECORDINGS))
def test_one_unreadable_recording_never_blanks_the_launchpad(tmp_path: Path, broken: str) -> None:
    """Readiness lists what READS, and says in one sentence per file what did not.

    One malformed file made `GET /api/readyz` answer 500 and the first screen
    show nothing at all, though a perfectly good recording sat beside it — the
    keyless product, blanked by a file it did not need (2026-09-20).
    """
    a_file_nobody_can_read(tmp_path, BROKEN_RECORDINGS[broken])

    ready = client().get("/api/readyz")

    assert ready.status_code == 200
    said = ready.json()
    assert [one["example"] for one in said["replayable"]] == ["hormuz"]
    assert any("broken" in one for one in said["unreadable"])


@pytest.mark.parametrize("broken", list(BROKEN_RECORDINGS), ids=list(BROKEN_RECORDINGS))
def test_an_unreadable_recording_is_never_played_at_somebody(tmp_path: Path, broken: str) -> None:
    """The good one still plays, and the bad one is not reached by matching on a sentence."""
    a_file_nobody_can_read(tmp_path, BROKEN_RECORDINGS[broken])

    names = [name for name, _ in stream()]

    assert names[-1] == "done"
    assert names[0] == "generation_started"


ANOTHER_SENTENCE = "A sentence whose recording goes wrong part way through."
"""A second card's sentence, so this file is the one that matches and plays."""


def test_a_recording_that_stops_being_readable_ends_the_stream_honestly(
    tmp_path: Path,
) -> None:
    """The header reads, the events play, and then the file turns out to be old.

    Built from the good recording so that everything up to the break is real:
    only the sentence and one appended event differ. It used to raise out of the
    route with the response half written — no `failed`, no `receipt`, and a
    browser left holding half a map and an open connection. Now the stream ends
    where it is, with what it spent, and one plain sentence naming the file
    (2026-09-20).
    """
    good = (tmp_path / "recordings" / "hormuz.jsonl").read_text(encoding="utf-8")
    (tmp_path / "recordings" / "half-old.jsonl").write_text(
        good.replace(THE_SENTENCE, ANOTHER_SENTENCE) + '{"event":"weather_changed","data":{}}\n',
        encoding="utf-8",
    )

    read = stream(hypothesis=ANOTHER_SENTENCE)

    names = [name for name, _ in read]
    assert names[0] == "generation_started"
    assert names[-1] == "failed"
    assert names[-2] == "receipt"
    assert "does not know" in read[-1][1]["message"]
    assert "weather_changed" in read[-1][1]["message"]
    assert "Error" not in read[-1][1]["message"]


# --- The insert route reads the map the reader is looking at --------------


def insert_of(**asked: Any) -> Any:
    """Ask the insert route for a drafted claim."""
    return client().post("/api/generate/insert", json=asked)


def test_an_insert_is_judged_against_the_branch_the_reader_is_looking_at() -> None:
    """The reader is looking at the base map **with their branch folded onto it**.

    It was judged against the bare base map, so the same insert could be added
    twice: 200, then 200 again with the branch that already held it — and then
    `POST /api/worlds` refused the branch with `duplicate_id`, which is the first
    the reader heard of it and much too late (2026-09-20).
    """
    stream()
    first = insert_of(base_id=A_MAP, claim_in_words=THE_SCRIPTED_INSERT, position=0)
    assert first.status_code == 200
    already = first.json()["insert"]

    again = insert_of(
        base_id=A_MAP,
        branch={
            "id": "br-1",
            "label": "the branch the reader has built",
            "parent": None,
            "interventions": [already],
        },
        claim_in_words=THE_SCRIPTED_INSERT,
        position=1,
    )

    assert again.status_code == 422
    assert any(one["code"] == "duplicate_id" for one in again.json()["detail"])


def test_an_insert_answers_with_its_own_receipt() -> None:
    """`streaming.md`, settled 2026-09-20: an `Insert` **and** its own small receipt.

    An insert is not one call — a drafting call, then one call per arrow — so it
    spends real money, and NFR-6 has no exception for money spent outside a
    stream. The route answered a bare `Insert` and dropped what it cost on the
    floor.
    """
    stream()

    answered = insert_of(base_id=A_MAP, claim_in_words=THE_SCRIPTED_INSERT, position=0)

    assert answered.status_code == 200
    said = answered.json()
    assert "insert" in said
    assert said["receipt"]["mode"] in ("live", "replay")
    assert said["receipt"]["prompt_hash"]


# --- The reader's own likelihood is carried, or nothing is stamped --------


def test_the_readers_own_likelihood_is_stamped_on_the_hypothesis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-2: it is theirs, never overwritten and never merged with the model's.

    The field was accepted by the route, documented on the request, and thrown
    away: `grep -rn user_belief backend/src` found only its declaration
    (2026-09-20).
    """
    monkeypatch.setattr(generate, "live_answerer", lambda **_: a_story())

    read = stream(
        hypothesis=STARTED_AT,
        user_belief={"p": 0.7, "lo": 0.5, "hi": 0.9, "owner": "user"},
    )

    world = next(payload for name, payload in read if name == "beliefs_propagated")
    started = world["world"]["graph"]["hypothesis_id"]
    its = next(one for one in world["world"]["graph"]["propositions"] if one["id"] == started)
    assert its["beliefs"]["user"] == {"p": 0.7, "lo": 0.5, "hi": 0.9, "owner": "user"}
    # Never overwritten and never merged: the model's own is still beside it.
    assert its["beliefs"]["model"]["owner"] == "model"


def test_saying_nothing_stamps_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """ "I don't know" is an answer, and it is not a likelihood of one half."""
    monkeypatch.setattr(generate, "live_answerer", lambda **_: a_story())

    read = stream(hypothesis=STARTED_AT)

    world = next(payload for name, payload in read if name == "beliefs_propagated")
    started = world["world"]["graph"]["hypothesis_id"]
    its = next(one for one in world["world"]["graph"]["propositions"] if one["id"] == started)
    assert its["beliefs"]["user"] is None


def test_two_viewings_of_one_card_do_not_share_a_transcript() -> None:
    """A recording's own identifier is a constant in a committed file.

    Two people opening the same card were filed under it, so they shared one
    entry in the store and overwrote each other's working — and whichever
    finished last decided what both of them read afterwards. One identifier is
    minted per viewing now, and the recording's own is kept as a field so the
    transcript still says which file it played (2026-09-20).
    """
    first = stream()
    second = stream()

    ids = [
        next(payload["generation_id"] for name, payload in read if name == "generation_started")
        for read in (first, second)
    ]

    assert ids[0] != ids[1]
    for one in ids:
        working = client().get(f"/api/generate/{one}/transcript").json()
        assert working["lines"]
        assert working["played_from"]


def test_the_stand_in_answerer_can_never_reach_the_stream_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The veto, and the fence against it (2026-09-20).

    `KATALYST_ANSWERER` exists so the recorder can be started as a program with
    no key. It used to sit inside `live_answerer`, which this route calls — so a
    deployed server with the setting on would have answered every reader from a
    list in a test file, unlabelled, and the map would have looked generated.

    With the setting on and no key, this route still replays. It does not
    generate, and nothing it shows came from a stand-in.
    """
    monkeypatch.setenv("KATALYST_ANSWERER", "tests.unit.engine.stand_ins:a_whole_story")
    get_settings.cache_clear()

    read = stream()

    assert next(payload for name, payload in read if name == "receipt")["mode"] == "replay"


# --- An insert is not a generation ----------------------------------------

THE_RECORDED_MIDDLE = "War-risk cover for Gulf transits gets cheap again."
"""The claim in the middle of the recorded map, which the reader's branch hangs off."""


def a_drafting_answerer(new_claim: str, arrows: list[tuple[str, str]]) -> Storyteller:
    """Draft one claim and then join it with the arrows a test asks for."""
    return Storyteller(
        starting=[an_answer(a_starting_claim(new_claim))],
        joining=[an_answer(a_link(source, target)) for source, target in arrows]
        + [an_answer(a_stop())],
    )


def test_an_insert_never_evicts_the_map_it_is_being_added_to(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An insert used to take a slot in the same bounded store the map lives in.

    So eight of them evicted the map they were being added to, and the ninth
    answered 404: one replay then ten inserts gave `[200 x8, 404, 404]`. An
    insert is one request and one answer now — nothing is remembered, so there
    is nothing to evict and nothing to find (2026-09-21).
    """
    stream()
    monkeypatch.setattr(
        generate,
        "live_answerer",
        lambda **_: a_drafting_answerer(
            "Something new happens.", [("Something new happens.", THE_RECORDED_MIDDLE)]
        ),
    )

    codes = [
        insert_of(base_id=A_MAP, claim_in_words=f"…but number {at} happens").status_code
        for at in range(10)
    ]

    assert codes == [200] * 10
    assert held.how_many() == 1


def test_an_insert_hands_back_its_own_working(monkeypatch: pytest.MonkeyPatch) -> None:
    """The calls are in the answer, because there is nowhere else they could be.

    Filing them under a freshly minted identifier nobody was told made them
    unfindable by anyone, which is the same as losing them (2026-09-21).
    """
    stream()
    monkeypatch.setattr(
        generate,
        "live_answerer",
        lambda **_: a_drafting_answerer(
            "Something new happens.", [("Something new happens.", THE_RECORDED_MIDDLE)]
        ),
    )

    said = insert_of(base_id=A_MAP, claim_in_words="…but something new happens").json()

    # One call drafts the claim, one joins it, one is told it is joined enough.
    assert said["receipt"]["calls"] == len(said["working"]) == 3
    assert said["receipt"]["seconds"] > 0
    assert [one["what"] for one in said["working"]] == ["accepted", "accepted", "stopped"]
    assert all(one["calls"] == 1 for one in said["working"])


def test_a_drafted_edit_goes_at_the_end_of_the_branch_it_was_drafted_against(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One rule, and the world route agrees with it (2026-09-21).

    `position` was declared, documented and read nowhere, and a reader who sent
    `position: 0` got a 200 for an edit that `POST /api/worlds` then refused with
    `unknown_target` — because the second edit hangs off the first. A branch is
    append-only everywhere else in this product; now it is here too.
    """
    stream()
    monkeypatch.setattr(
        generate,
        "live_answerer",
        lambda **_: a_drafting_answerer(
            "The first thing.", [(THE_RECORDED_MIDDLE, "The first thing.")]
        ),
    )
    first = insert_of(base_id=A_MAP, claim_in_words="…but the first thing happens").json()["insert"]
    branch = {
        "id": "br-1",
        "label": "what the reader has done so far",
        "parent": None,
        "interventions": [first],
    }

    monkeypatch.setattr(
        generate,
        "live_answerer",
        lambda **_: a_drafting_answerer(
            "The second thing.", [("The first thing.", "The second thing.")]
        ),
    )
    second = insert_of(
        base_id=A_MAP, branch=branch, claim_in_words="…but the second thing happens"
    ).json()["insert"]

    at_the_end = dict(branch, id="br-2", interventions=[first, second])
    world = client().post(
        "/api/worlds", json={"base_id": A_MAP, "branch": at_the_end, "seed": 1, **SMALL}
    )

    assert world.status_code == 200, world.text


def test_a_width_overrun_a_branch_introduces_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The width cap counts the arrows leaving a claim **on the map as folded**.

    `add_a_claim`'s own `width` caps the new claim's arrows and says nothing
    about the out-degree of a claim those arrows leave, so three edits could each
    hang one more thing off the same claim (2026-09-21).
    """
    stream()
    edits: list[dict[str, Any]] = []
    for at in range(Caps().width - 1):
        monkeypatch.setattr(
            generate,
            "live_answerer",
            lambda at=at, **_: a_drafting_answerer(  # type: ignore[misc]
                f"Branch claim {at}.", [(THE_RECORDED_MIDDLE, f"Branch claim {at}.")]
            ),
        )
        answered = insert_of(
            base_id=A_MAP,
            branch={"id": "br", "label": "the reader's", "parent": None, "interventions": edits},
            claim_in_words=f"…but branch claim {at}",
        )
        assert answered.status_code == 200, answered.text
        edits.append(answered.json()["insert"])

    monkeypatch.setattr(
        generate,
        "live_answerer",
        lambda **_: a_drafting_answerer("One too many.", [(THE_RECORDED_MIDDLE, "One too many.")]),
    )
    over = insert_of(
        base_id=A_MAP,
        branch={"id": "br", "label": "the reader's", "parent": None, "interventions": edits},
        claim_in_words="…but one arrow too many",
    )

    assert over.status_code == 422, over.text


# --- Nothing is held for ever ---------------------------------------------


@pytest.mark.parametrize(
    "how_it_ends",
    ["read to the end", "abandoned half way", "the file stops being readable"],
)
def test_a_replay_is_always_let_go_of_however_it_ends(tmp_path: Path, how_it_ends: str) -> None:
    """Forty replays against a bound of eight (2026-09-21).

    A run is marked in flight while it streams so a busy process cannot forget
    one somebody is still watching — and the mark was cleared on the last line of
    the `try`. Both `except` arms skipped it, and so did a reader closing the
    tab, which raises `GeneratorExit` and skips every `except` there is. Every
    abandoned replay was then un-evictable for ever, which is the one thing a
    bounded store exists to prevent.
    """
    sentence = THE_SENTENCE
    if how_it_ends == "the file stops being readable":
        sentence = "A sentence whose recording goes wrong part way through."
        good = (tmp_path / "recordings" / "hormuz.jsonl").read_text(encoding="utf-8")
        (tmp_path / "recordings" / "half-old.jsonl").write_text(
            good.replace(THE_SENTENCE, sentence) + '{"event":"weather_changed","data":{}}\n',
            encoding="utf-8",
        )

    for _ in range(40):
        if how_it_ends == "abandoned half way":
            with client().stream(
                "POST", "/api/generate", json={"hypothesis": sentence, **SMALL}
            ) as answer:
                next(iter(answer.iter_lines()))
        else:
            stream(hypothesis=sentence)

    assert held.how_many() <= HOW_MANY_GENERATIONS_A_PROCESS_KEEPS


def test_a_live_run_is_always_let_go_of_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same guard on the same shape of mistake, on the other path."""
    monkeypatch.setattr(generate, "live_answerer", lambda **_: a_story())

    for _ in range(40):
        with client().stream(
            "POST", "/api/generate", json={"hypothesis": STARTED_AT, **SMALL}
        ) as answer:
            next(iter(answer.iter_lines()))

    assert held.how_many() <= HOW_MANY_GENERATIONS_A_PROCESS_KEEPS
