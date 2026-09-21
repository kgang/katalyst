"""Cards, and everything a card is handed, built by hand for the tests beside this file.

Nothing here computes anything. Every number in this file is one a test chose so
that a rule can be stated about it — an ordering, an identity, a refusal — and no
number an engine produced is typed anywhere. The shapes a card is handed are
built directly rather than by calling the modules that will produce them, because
those modules are being written beside this one.

The map, the worlds and the quotes come from `test_edge.py`, which already builds
them the way this repository builds them, so there is one set of these and not
two.
"""

from datetime import date

import numpy
from numpy.typing import NDArray

from katalyst.domain import (
    Belief,
    Beliefs,
    ContractPayoff,
    Graph,
    Payoff,
    PricePayoff,
    Proposition,
    PropositionId,
    Resolution,
    World,
)
from katalyst.grounding import Quote
from katalyst.thesis import (
    Card,
    Carried,
    Ceiling,
    Dropped,
    Edge,
    FirstTouch,
    LiftRow,
    MarketChanceFrom,
    NotComparable,
    Position,
    Refusal,
    SampleFrom,
    Shift,
    Shocked,
    Tail,
    Unhedgeable,
    Watched,
    WhatTakesYouOut,
    card_of,
    priced,
)
from katalyst.thesis.ceiling import NEVER_SIZE_TO_THIS
from katalyst.thesis.ceiling import TakenBy as TakenBy
from katalyst.thesis.position import Side, Trades
from tests.thesis.test_edge import VENUE, a_contract, an_arrow, world_of

WIDE = Belief(p=0.35, lo=0.22, hi=0.5, owner="model")
"""A prior the model is genuinely unsure of, so the world it produces has a range with width."""

OTHER_MARKET = "7654321"
"""A second market at the same venue, so two contract endings can be ranked against each other."""


def a_claim(
    identifier: str,
    kind: str,
    *,
    payoff: Payoff | None = None,
    reason: str | None = None,
) -> Proposition:
    """One claim on a small hand-built map."""
    return Proposition(
        id=identifier,
        claim=f"The claim called {identifier} comes out true.",
        kind=kind,
        resolution=Resolution(
            criteria="A counted threshold over a named window, as the venue states it.",
            source="The publication that actually publishes this number.",
            by=date(2026, 11, 1),
        ),
        prior=WIDE,
        beliefs=Beliefs(model=WIDE),
        payoff=payoff,
        not_tradeable_reason=reason,
    )


def an_instrument(name: str, move: float) -> PricePayoff:
    """An ending naming something traded, which no venue quotes on this claim's own question."""
    return PricePayoff(instrument=name, direction="short", move=move)


def a_card_map() -> Graph:
    """A map with two contract endings, two instrument endings and one that names neither."""
    return Graph(
        id="a-card-map",
        hypothesis_id="start",
        propositions=(
            a_claim("start", "hypothesis"),
            a_claim("step", "event"),
            a_claim("contract", "market", payoff=a_contract("yes")),
            a_claim(
                "other-contract",
                "market",
                payoff=ContractPayoff(
                    venue=VENUE,
                    contract_id=OTHER_MARKET,
                    title="A second question the same venue asks.",
                    side="yes",
                ),
            ),
            a_claim("instrument", "market", payoff=an_instrument("the front-month future", 0.03)),
            a_claim("other-instrument", "market", payoff=an_instrument("the fund pair", 0.05)),
            a_claim(
                "untradeable",
                "not_tradeable",
                reason="Every instrument that would express this settles after the claim resolves.",
            ),
        ),
        links=(
            an_arrow("start-to-step", "start", "step"),
            an_arrow("step-to-contract", "step", "contract"),
            an_arrow("step-to-other-contract", "step", "other-contract"),
            an_arrow("step-to-instrument", "step", "instrument"),
        ),
    )


def a_world(seed: int = 1) -> World:
    """The world with nothing fixed by an edit, over the map above."""
    return world_of(a_card_map(), seed=seed)


def a_position(
    ending: PropositionId = "instrument",
    *,
    trades: Trades = "instrument",
    side: Side = "long",
    entry: float = 70.0,
    stop: float = 67.0,
    target: float = 76.0,
) -> Position:
    """What the reader typed, on one ending of the map above."""
    return Position(
        ending=ending,
        instrument="the front-month future",
        side=side,
        trades=trades,
        entry=entry,
        stop=stop,
        target=target,
        horizon=date(2026, 10, 31),
        risk_budget=0.01,
        daily_move=1.2,
    )


def days(*each: int) -> NDArray[numpy.int32]:
    """A run of whole days, one per drawn world, as the shapes underneath carry them."""
    return numpy.array(each, dtype=numpy.int32)


def a_first_touch(
    *,
    stop_first: float = 0.4,
    target_first: float = 0.35,
    neither: float = 0.25,
    sample: SampleFrom = "built_by_hand",
) -> FirstTouch:
    """How often each end of the exit was reached first, on worlds the test chose."""
    return FirstTouch(
        stop_first=stop_first,
        target_first=target_first,
        neither=neither,
        stop_touched=0.45,
        finished_beyond_the_stop=0.3,
        stop_at=67.5,
        target_at=75.5,
        shift=0.5,
        effective_draws=940.0,
        stop_first_on=days(3, -1, 7, -1),
        sample=sample,
    )


def a_lift_row(claim: PropositionId, lift: float) -> LiftRow:
    """One row of the rail, with numbers the test chose so an ordering can be stated."""
    return LiftRow(
        claim=claim,
        lift=lift,
        came_on_first=0.6,
        came_on_first_lo=0.52,
        came_on_first_hi=0.68,
        came_on=0.6 / lift,
        effective_draws=410.0,
        days_before_the_stop=2.0,
        coverage=0.95,
    )


def a_rail(
    *,
    rows: tuple[LiftRow, ...] = (),
    dropped: tuple[Dropped, ...] = (),
    too_few_draws: str | None = None,
    sample: SampleFrom = "built_by_hand",
) -> WhatTakesYouOut:
    """The rail of claims over-represented where the stop went first."""
    return WhatTakesYouOut(
        rows=rows,
        dropped=dropped,
        effective_draws=940.0,
        stop_first_worlds=1000,
        floor=200,
        sample=sample,
        too_few_draws=too_few_draws,
    )


def a_ceiling(
    *,
    fraction: float | None = 0.08,
    taken_by: TakenBy | None = "buying",
    at: float | None = 0.22,
    sentence: str | None = None,
) -> Ceiling:
    """The greyed ceiling, in whichever of its three states a test wants."""
    return Ceiling(
        fraction=fraction,
        taken_by=taken_by,
        at=at,
        warning=NEVER_SIZE_TO_THIS,
        sentence=sentence,
    )


def a_shift(ending: PropositionId, points: float) -> Shift:
    """How far the hypothesis moves one ending, at a size the test chose."""
    return Shift(ending=ending, points=points, worked_out_by="a set of worlds built by hand")


def what_was_priced(
    world: World,
    ending: PropositionId,
    quote: Quote | None = None,
    *,
    fee: float | None = None,
) -> Edge | NotComparable:
    """What `edge.py` returns for one ending, built by the one function allowed to build it."""
    return priced(world, world, ending, quote, fee=fee)


def a_card(
    world: World,
    *,
    position: Position | None = None,
    answers: dict[PropositionId, Edge | NotComparable] | None = None,
    shifts: dict[PropositionId, Shift] | None = None,
    carried_by: tuple[Carried, ...] = (),
    ceiling: Ceiling | None = None,
    touch: FirstTouch | Refusal | None = None,
    rail: WhatTakesYouOut | None = None,
    market_chance_from: dict[PropositionId, MarketChanceFrom] | None = None,
    watch: tuple[Watched, ...] = (),
    unhedgeable: tuple[Unhedgeable, ...] = (),
    tails: tuple[Tail, ...] = (),
    shocks: tuple[Shocked, ...] = (),
    implied_size: float = 0.33,
    costs: float | None = None,
) -> Card:
    """One card, with everything not under test left at a plain default."""
    held = position if position is not None else a_position()
    known = answers if answers is not None else {held.ending: what_was_priced(world, held.ending)}
    return card_of(
        world,
        position=held,
        priced=known,
        shifts=shifts if shifts is not None else {},
        carried_by=carried_by,
        ceiling=ceiling if ceiling is not None else a_ceiling(),
        touch=touch if touch is not None else a_first_touch(),
        takes_you_out=rail if rail is not None else a_rail(),
        market_chance_from=market_chance_from if market_chance_from is not None else {},
        watch=watch,
        unhedgeable=unhedgeable,
        tails=tails,
        shocks=shocks,
        implied_size=implied_size,
        costs=costs,
    )
