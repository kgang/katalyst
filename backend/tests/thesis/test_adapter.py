"""The two adapters, checked against the real engine rather than against a description of it.

`draws_of` claims to **rename and never compute**, and `moves_on` claims to turn
the map's own statement — a move as a share of a price — into the level gap in
price units a path takes. Both claims are about shapes somebody else builds, so
both are checked here against worlds the engine actually drew and against a map
this file writes down, never against a copy of either written by hand.

Two things are asserted and no number is typed into either. The sample's fields
cross **untouched**, which is an identity between two objects and not a value. And
every day in the two day tables is the middle of one of that claim's **own** time
slices, rounded to a whole day — the contract `draws.py` states and everything
above it relies on, because a daily price path steps sixty times and may take a
surprise on at most two dozen of them.
"""

from datetime import date, timedelta

import numpy
import pytest

from katalyst.domain import (
    Belief,
    Beliefs,
    ContractPayoff,
    Graph,
    Link,
    PricePayoff,
    Proposition,
    PropositionId,
    Resolution,
    Sample,
)
from katalyst.domain.rates import SLICES
from katalyst.engine import worlds as engine
from katalyst.engine.transcript import Transcript, held
from katalyst.thesis.adapter import draws_of, moves_on
from katalyst.thesis.draws import NEVER, STILL_HOLDING, effective_draws

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""

DAY_ZERO = date(2026, 10, 1)
"""The day the map this file builds opens on. The stored example opens on it too."""

DRAWN = 2_000
"""How many worlds these tests draw: enough for every claim's grid to show itself."""


def a_claim(
    name: str, *, days: int, payoff: PricePayoff | ContractPayoff | None = None
) -> Proposition:
    """One plain claim, judged a stated number of days after the window opens.

    The day it is judged is what cuts its own grid of time slices, so two claims
    judged on different days land their arrivals on different days — which is the
    thing the second test here is about.

    Args:
        name: What the claim is called.
        days: How many days after day zero it is judged.
        payoff: What it names as a trade, where it names one.

    Returns:
        The claim.
    """
    stated = Belief(p=0.4, lo=0.3, hi=0.5, owner="model")
    return Proposition(
        id=PropositionId(name),
        claim=f"The claim written down under the name {name}.",
        kind="market" if payoff is not None else "event",
        resolution=Resolution(
            criteria="A check two readers of it would agree on.",
            source="The publication that would carry it.",
            by=DAY_ZERO + timedelta(days=days),
        ),
        prior=stated,
        beliefs=Beliefs(model=stated),
        payoff=payoff,
    )


LONG_ENDING = a_claim(
    "up", days=40, payoff=PricePayoff(instrument="a widget", direction="long", move=0.05)
)
"""An ending whose instrument stands **higher** in a world where its claim is true."""

SHORT_ENDING = a_claim(
    "down", days=40, payoff=PricePayoff(instrument="a widget", direction="short", move=0.05)
)
"""The same move, the other way: the instrument stands lower where the claim is true."""

CONTRACT_ENDING = a_claim(
    "asked",
    days=40,
    payoff=ContractPayoff(
        venue="Polymarket",
        contract_id="a-contract",
        title="The contract's own question, in the venue's words.",
        side="yes",
    ),
)
"""An ending a venue quotes, which gets no price path at all."""

A_SMALL_MAP = Graph(
    id="two-deadlines",
    propositions=(a_claim("H", days=12), a_claim("A", days=30), LONG_ENDING),
    links=(
        Link(
            id="H->A",
            source="H",
            target="A",
            mode="trigger",
            strength=1.5,
            lag=0.0,
            shape="step",
            rationale="The first claim moves the second one, for a stated reason.",
            provenance="argued",
        ),
    ),
    hypothesis_id="H",
)
"""Three claims judged twelve, thirty and forty days out, so three grids differ."""


def middles_of(days: int) -> set[int]:
    """The days an arrival may land on for a claim judged this many days out.

    The engine cuts a claim's own window into a fixed number of equal slices and
    takes an arrival at the middle of its slice, rounded to a whole day. Worked out
    here from the one number the engine states — how many slices — rather than
    listed, so nothing in this file is a day somebody typed.

    Args:
        days: How long that claim's own window runs for.

    Returns:
        Every day an arrival may land on.
    """
    return {round((half + 0.5) * days / SLICES) for half in range(SLICES)}


def a_sample(graph: Graph | None = None) -> Sample:
    """Draw worlds forward on a map, through the engine's own route and nothing else.

    Args:
        graph: The map to draw on, or nothing at all for the stored worked example.

    Returns:
        The worlds the engine drew.
    """
    if graph is None:
        drawn = engine.sample_of("hormuz", None, SEED, versions=8, drawn=DRAWN)
        assert isinstance(drawn, Sample), drawn
        return drawn
    held.remember(
        Transcript(
            generation_id=f"for-{graph.id}",
            hypothesis="A map this test wrote down.",
            seed=SEED,
            on=DAY_ZERO,
            mode="replay",
        ),
        graph,
    )
    drawn = engine.sample_of(graph.id, None, SEED, versions=8, drawn=DRAWN)
    assert isinstance(drawn, Sample), drawn
    return drawn


def test_every_field_of_the_engine_s_sample_crosses_untouched() -> None:
    """The adapter renames; it does not compute. Field for field, both sides agree.

    Asserted as an identity between the two objects rather than against numbers
    written down here: a test that compared values would still pass if the adapter
    quietly rounded, and would have to be rewritten every time the engine's numbers
    moved.
    """
    sample = a_sample()

    draws = draws_of(sample)

    assert draws.day_zero == sample.day_zero
    assert draws.days == sample.days
    assert draws.claims == sample.claims
    assert draws.on_day is sample.on_day
    assert draws.off_day is sample.off_day
    assert draws.weight is sample.weight
    assert draws.effective == sample.effective
    assert draws.worlds == sample.worlds


def test_the_draws_name_the_sampler_their_days_came_from() -> None:
    """No first-touch number may be reported without saying which sample it rests on."""
    draws = draws_of(a_sample())

    assert draws.sample == "weighted_forward_sample"


def test_the_effective_count_is_the_one_those_weights_imply() -> None:
    """A count from some other sample would make every floor above it meaningless."""
    draws = draws_of(a_sample())

    assert draws.effective == pytest.approx(effective_draws(draws.weight))


def test_every_day_is_the_middle_of_one_of_that_claim_s_own_slices() -> None:
    """A claim judged in a fortnight and one judged in six weeks do not share slice boundaries.

    The contract everything above `Draws` rests on: arrivals are coarse, they land
    on the middles of the engine's time slices, and the grid belongs to the claim
    rather than to the map. This walks all three claims of a map whose deadlines are
    twelve, thirty and forty days out, so a grid read off the wrong claim would show.
    """
    sample = a_sample(A_SMALL_MAP)
    judged = {one.id: (one.resolution.by - DAY_ZERO).days for one in A_SMALL_MAP.propositions}

    for column, name in enumerate(sample.claims):
        allowed = middles_of(judged[name])
        came = set(numpy.unique(sample.on_day[:, column]).tolist()) - {NEVER}
        went = set(numpy.unique(sample.off_day[:, column]).tolist()) - {NEVER, STILL_HOLDING}
        assert came <= allowed, name
        assert went <= allowed, name
        assert came, f"'{name}' never came on in any drawn world, so this checks nothing"


def test_the_days_stay_inside_the_map_s_own_window() -> None:
    """The window a set of draws carries is the map's, and no day may fall outside it."""
    sample = a_sample(A_SMALL_MAP)

    draws = draws_of(sample)

    assert draws.days == max(
        (one.resolution.by - DAY_ZERO).days for one in A_SMALL_MAP.propositions
    )
    assert int(draws.on_day.max()) <= draws.days
    assert int(draws.off_day.max()) <= draws.days


def test_a_move_is_the_map_s_stated_share_times_the_price_you_entered_at() -> None:
    """A map states a move as a share of a price; a path takes a level gap in price units."""
    entry = 40.0

    moved = moves_on(LONG_ENDING, entry=entry)

    assert len(moved) == 1
    assert moved[0].claim == LONG_ENDING.id
    assert moved[0].move == pytest.approx(0.05 * entry)


def test_a_short_payoff_is_the_same_move_pointing_the_other_way() -> None:
    """A stated share is never negative, so the side the payoff names is what carries the sign."""
    entry = 40.0

    up = moves_on(LONG_ENDING, entry=entry)
    down = moves_on(SHORT_ENDING, entry=entry)

    assert down[0].move == pytest.approx(-up[0].move)


def test_the_market_s_chance_is_left_for_the_path_to_read_off_the_drawn_worlds() -> None:
    """Handing one in here would be a chance nobody could trace; the neutral one is computed."""
    moved = moves_on(LONG_ENDING, entry=40.0)

    assert moved[0].market_chance is None
    assert moved[0].market_chance_from == "sample_share"


def test_a_contract_ending_and_a_claim_that_names_no_trade_move_no_price() -> None:
    """Neither gets a price path: one is held to resolution, and the other names nothing."""
    assert moves_on(CONTRACT_ENDING, entry=0.4) == ()
    assert moves_on(a_claim("plain", days=10), entry=40.0) == ()
