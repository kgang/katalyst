"""One recording, written from the fake answers, so replay can be proved with no key.

A real recording is made by `make record-demo` against a real key, and nothing
else may ever write one — a hand-edited file under `backend/recordings/` is a
piece of state that traces to nobody. **This is not one of those.** It lives under
`backend/tests/`, it is built here in memory from the same hand-written answers
the pipeline's own tests use, and it exists so that every rule about replay can be
shown to hold today, before anybody has spent a penny.

When the first real recording lands, these same tests run against it too: the
corpus the chapter names is every file under `backend/recordings/`, and this one
is simply a second, smaller corpus of one.
"""

import json
from datetime import date
from pathlib import Path

from katalyst.domain import (
    Belief,
    Beliefs,
    ContractPayoff,
    Insert,
    Link,
    Proposition,
    Resolution,
    Violation,
)
from katalyst.engine import events
from katalyst.engine.events import (
    Done,
    GenerationStarted,
    ProposalAccepted,
    ProposalRejected,
    Receipt,
)
from katalyst.engine.prompt import prompt_hash

THE_SENTENCE = "The Strait of Hormuz is going to open next week."
"""The sentence this recording was made from, and the only one it answers to."""

THE_SCRIPTED_INSERT = "…but Iran is struck the next day"
"""The one "…but X happens" a keyless reviewer can make on this map."""

MADE_ON = date(2026, 9, 17)
"""The day this recording pretends to have been written."""

A_MAP = "01AAAAAAAAAAAAAAAAAAAAAAAA"
"""The identifier of the map inside — minted, never the word `hormuz`."""

SETTLED_BY = date(2026, 11, 1)
"""One resolve-by date, so no test here is about a date."""


def a_claim(claim_id: str, claim: str, kind: str = "event") -> Proposition:
    """Build one claim of the recorded map."""
    stated = Belief(p=0.4, lo=0.2, hi=0.6, owner="model")
    return Proposition(
        id=claim_id,
        claim=claim,
        kind=kind,  # type: ignore[arg-type]
        persistence="event",
        resolution=Resolution(
            criteria="A test two people reading it would agree on.",
            source="A named judge.",
            by=SETTLED_BY,
        ),
        prior=stated,
        beliefs=Beliefs(model=stated),
        payoff=(
            ContractPayoff(venue="Somewhere", contract_id="c-1", title="Does it?", side="yes")
            if kind == "market"
            else None
        ),
    )


def an_arrow(arrow_id: str, source: str, target: str) -> Link:
    """Build one arrow of the recorded map."""
    return Link(
        id=arrow_id,
        source=source,
        target=target,
        mode="sustain",
        strength=0.5,
        lag=1.0,
        shape="step",
        rationale="The cause moves the effect, and here is how.",
        provenance="argued",
    )


def written_to(folder: Path) -> Path:
    """Write the recording into a folder and hand back its path.

    Args:
        folder: Where to write it. A throwaway directory in every test.

    Returns:
        The file that was written.
    """
    started = a_claim("H", THE_SENTENCE, kind="hypothesis")
    middle = a_claim("C", "War-risk cover for Gulf transits gets cheap again.")
    ending = a_claim("M1", "A contract on Brent below $70 resolves yes.", kind="market")

    lines: list[tuple[str, object]] = [
        (
            events.NAMES[GenerationStarted],
            GenerationStarted(
                generation_id="a-recorded-run", seed=20261001, hypothesis=THE_SENTENCE
            ),
        ),
        (
            events.NAMES[ProposalAccepted],
            ProposalAccepted(at=0, proposition=started, frontier=("H",)),
        ),
        (
            events.NAMES[ProposalAccepted],
            ProposalAccepted(
                at=1,
                proposition=middle,
                links=(an_arrow("H->C", "H", "C"),),
                frontier=("H", "C"),
            ),
        ),
        (
            events.NAMES[ProposalRejected],
            ProposalRejected(
                at=2,
                claim_in_words="cheaper crude reduces the incentive to close the strait",
                violations=(
                    Violation(
                        code="cycle",
                        subject="C->H",
                        message=(
                            "These claims form a loop with no delay in it. Mark the arrow "
                            "where a market feeds back on the world as reflexive and give "
                            "it a delay, or remove one arrow."
                        ),
                    ),
                ),
                frontier=("H", "C"),
            ),
        ),
        (
            events.NAMES[ProposalAccepted],
            ProposalAccepted(
                at=3,
                proposition=ending,
                links=(an_arrow("C->M1", "C", "M1"),),
                frontier=("H", "C"),
            ),
        ),
        (
            events.NAMES[Receipt],
            Receipt(
                model="claude-opus-5",
                calls=5,
                input_tokens=2_500,
                output_tokens=13_000,
                cache_read_tokens=118_000,
                searches=5,
                dollars=0.64,
                seconds=300.0,
                mode="live",
                prompt_hash=prompt_hash(),
            ),
        ),
        (events.NAMES[Done], Done(reason="reached_terminal", claims=3, links=2, rejected=1)),
    ]

    header = {
        "base_id": A_MAP,
        "seed": 20261001,
        "recording_date": MADE_ON.isoformat(),
        "prompt_hash": prompt_hash(),
        "insert": {
            "claim_in_words": THE_SCRIPTED_INSERT,
            "answer": json.loads(
                Insert(
                    proposition=a_claim("S", "Iran is struck the next day."),
                    links=(an_arrow("S->C", "S", "C"),),
                ).model_dump_json()
            ),
        },
    }

    folder.mkdir(parents=True, exist_ok=True)
    written = folder / "hormuz.jsonl"
    written.write_text(
        "\n".join(
            [json.dumps(header)]
            + [
                json.dumps({"event": name, "data": json.loads(event.model_dump_json())})  # type: ignore[attr-defined]
                for name, event in lines
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return written
