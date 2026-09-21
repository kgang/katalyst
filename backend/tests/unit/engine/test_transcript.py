"""What a process holds between requests, and what it is allowed to forget.

Nothing here is written to disk and a restart empties it. What matters is that
forgetting one generation never damages another, and that a generation somebody
is still watching is never forgotten at all.
"""

from datetime import date

import pytest

from katalyst.domain import Graph, Proposition, Resolution
from katalyst.domain.belief import Belief, Beliefs
from katalyst.engine.transcript import Generations, Transcript

TODAY = date(2026, 9, 17)
"""One day, so no test here is about a date."""


def a_map(identifier: str) -> Graph:
    """One map of one claim, with an identifier a test can point at."""
    started = Proposition(
        id=f"{identifier}-claim",
        claim="Something somebody expects.",
        kind="hypothesis",
        resolution=Resolution(
            criteria="A test two people reading it would agree on.",
            source="A named judge.",
            by=date(2026, 11, 1),
        ),
        prior=Belief(p=0.4, lo=0.2, hi=0.6, owner="model"),
        beliefs=Beliefs(model=Belief(p=0.4, lo=0.2, hi=0.6, owner="model")),
    )
    return Graph(id=identifier, propositions=(started,), links=(), hypothesis_id=started.id)


def a_working(generation_id: str) -> Transcript:
    """One transcript, of a generation that has done nothing yet."""
    return Transcript(
        generation_id=generation_id,
        hypothesis="Something somebody expects.",
        target=None,
        seed=1,
        on=TODAY,
        mode="live",
    )


def test_forgetting_one_generation_never_takes_another_ones_map_with_it() -> None:
    """Two runs of one stored example share a `base_id`, and only one owns it.

    Evicting the older popped the map's name without checking the evicted run
    still owned it, so the newer run's map became unreachable while its own
    transcript was still held — a map that outlives nothing, reachable by nobody
    (2026-09-20).
    """
    holding = Generations(keep=2)
    shared = a_map("hormuz")
    holding.remember(a_working("first"), shared)
    holding.remember(a_working("second"), shared)

    holding.remember(a_working("third"), a_map("another"))

    # "first" is gone, and it took nothing of "second"'s with it.
    assert holding.working("first") is None
    assert holding.working("second") is not None
    assert holding.map_of("hormuz") is not None


def test_a_generation_somebody_is_still_watching_is_never_forgotten() -> None:
    """A run streaming its map is the one run nobody may drop.

    It was evictable like any other, so a busy process could forget a generation
    while it was still writing into it: the reader's own transcript answered 404
    halfway through their map arriving (2026-09-20).
    """
    holding = Generations(keep=1)
    holding.remember(a_working("watching"), None, in_flight=True)

    holding.remember(a_working("a-later-one"), a_map("later"))
    holding.remember(a_working("a-later-one-still"), a_map("later-still"))

    assert holding.working("watching") is not None


def test_a_generation_that_has_finished_is_evictable_again() -> None:
    """Otherwise a long-lived process fills up with runs nobody is watching."""
    holding = Generations(keep=1)
    holding.remember(a_working("watching"), None, in_flight=True)
    holding.remember(a_working("watching"), None, in_flight=False)

    holding.remember(a_working("a-later-one"), a_map("later"))

    assert holding.working("watching") is None


@pytest.mark.parametrize("keep", [1, 3])
def test_a_process_never_holds_more_than_it_said_it_would(keep: int) -> None:
    """The bound is the whole reason this exists."""
    holding = Generations(keep=keep)
    for index in range(keep + 4):
        holding.remember(a_working(f"run-{index}"), a_map(f"map-{index}"))

    assert holding.how_many() == keep
