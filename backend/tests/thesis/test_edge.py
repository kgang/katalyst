"""The edge: which world it is read from, which price it is set against, and every refusal.

Two mistakes would each make a finance-literate reader stop trusting every number
on the screen, and each has tests here whose only job is to catch it.

* **The wrong world.** *Suppose this is true* changes the question a tile answers,
  and a venue's price answers the old one. The check is exact and it is a *type*
  first: the function that builds an edge takes two worlds and both are required,
  so a caller holding only the world on screen cannot write the mistake down; and
  a world carrying a value fixed by either button is refused by name.
* **The wrong price.** You buy at the offer and sell at the bid, so there are two
  edges and the midpoint is never traded against.

**No number the engine computed is typed anywhere in this file.** Every quote is
built out of the world it is being compared with, so the tests state identities —
*agree with the market and the edge is exactly nothing* — orderings, and signs.
Every one of them would survive the engine's numbers all moving tomorrow.
"""

from datetime import UTC, date, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from katalyst.domain import (
    Belief,
    Beliefs,
    Branch,
    ContractPayoff,
    Do,
    Graph,
    Link,
    Observe,
    PricePayoff,
    Proposition,
    PropositionId,
    Resolution,
    Source,
    World,
    apply,
    introduced_by,
    propagate,
)
from katalyst.grounding import Quote
from katalyst.thesis import Edge, NotComparable, priced
from katalyst.thesis.edge import (
    A_VALUE_IS_FIXED,
    MARKET_HAS_SETTLED,
    NO_CONTRACT_QUOTES_IT,
    NO_PRICE_READ,
    NO_TRADE_NAMED,
)
from tests.strategies import graphs, interventions, quotes, seeds, uncertain_beliefs

a_few = settings(max_examples=12, deadline=None)
many = settings(max_examples=40, deadline=None)

DAY_ZERO = date(2026, 1, 1)
"""Day zero for these maps, which carry resolve-by dates from 2026 onwards."""

SMALL = {"versions": 16, "worlds": 4}
"""The budget these tests run at: sixty-four draws rather than sixteen thousand.

Every rule checked here — which world a number is read from, the signs of the two
edges, how the band moves with the fee, which refusal comes back — is true at any
budget. Only how steady a number is depends on it, and nothing here reads a number
for its own sake.
"""

SOME_INSTANT = datetime(2026, 9, 21, 14, 48, 27, tzinfo=UTC)
"""One instant a price was true. Every quote must carry one; nothing here reads it."""


# --- Building worlds and maps to price against -----------------------------


def world_of(graph: Graph, branch: Branch | None = None, *, seed: int = 1) -> World:
    """Fold a branch onto a map and work every likelihood through time.

    Args:
        graph: The map. Never changed.
        branch: The branch to fold. Nothing at all means the world with nothing
            fixed by an edit.
        seed: The one number every draw comes from.

    Returns:
        One world, naming the branch it came from.
    """
    folded = apply(graph, branch) if branch is not None else (graph, ())
    assert not isinstance(folded, list), f"this branch would not fold: {folded}"
    left, fixed = folded
    world = propagate(
        left,
        fixed,
        as_of=DAY_ZERO,
        seed=seed,
        introduced_by=introduced_by(branch) if branch is not None else {},
        **SMALL,
    )
    return world.model_copy(update={"branch_id": branch.id if branch is not None else None})


def agreeing_quote(world: World, claim: PropositionId, **changed: object) -> Quote:
    """Build a venue quote that agrees exactly with the model, then change what a test asks.

    Both sides of the book are the base world's own number for this claim, so any
    edge computed against it is exactly nothing before the test moves a price. **No
    number is typed**: the quote is built out of the world it will be compared
    with.

    Args:
        world: The world the number is read from.
        claim: The claim being priced.
        **changed: Fields to replace afterwards, such as a moved offer or a flag
            saying the market has finished.

    Returns:
        One quote, read from a venue.
    """
    agrees = world.beliefs[claim].p
    quote = Quote(
        bid=agrees,
        offer=agrees,
        as_of=SOME_INSTANT,
        source="recorded",
        closed=False,
        accepting_orders=True,
        venue="Polymarket",
        condition_id="0xthe-contract",
        market_id="3501950",
        token_id="the-yes-outcome",
        side="yes",
        question="Does the venue ask the claim's own question?",
        rules="The venue's own resolution rules, word for word.",
        ends=date(2026, 11, 1),
        tick=0.01,
        minimum_order=5.0,
        resting=119_187.28,
        traded=754_974.31,
        url="https://example.test/event/a-question-somebody-quotes",
    )
    return quote.model_copy(update=changed) if changed else quote


def _resolution() -> Resolution:
    """How every claim on the small maps below gets settled."""
    return Resolution(
        criteria="A counted threshold over a named window, as the venue states it.",
        source="The publication that actually publishes this number.",
        by=date(2026, 11, 1),
    )


def _claim(
    identifier: str,
    kind: str,
    *,
    prior: Belief,
    payoff: object = None,
    reason: str | None = None,
) -> Proposition:
    """One claim on a small hand-built map."""
    return Proposition(
        id=identifier,
        claim=f"The claim called {identifier} comes out true.",
        kind=kind,
        resolution=_resolution(),
        prior=prior,
        beliefs=Beliefs(model=prior),
        payoff=payoff,
        not_tradeable_reason=reason,
    )


A_CONTRACT = ContractPayoff(
    venue="Polymarket",
    contract_id="3501950",
    title="Does the venue ask the claim's own question?",
    side="yes",
)
"""An ending that names a contract somebody sells: the row that can produce an edge."""

AN_INSTRUMENT = PricePayoff(
    instrument="the front-month futures contract", direction="short", move=0.03
)
"""An ending that names something traded, which no venue quotes on this claim's own question."""

WIDE = Belief(p=0.35, lo=0.22, hi=0.5, owner="model")
"""A prior the model is genuinely unsure of, so the world it produces has a range with width."""


def every_row_map() -> Graph:
    """One small map carrying every kind of ending the decision table has a row for."""
    return Graph(
        id="every-row",
        hypothesis_id="start",
        propositions=(
            _claim("start", "hypothesis", prior=WIDE),
            _claim("step", "event", prior=WIDE),
            _claim("contract", "market", prior=WIDE, payoff=A_CONTRACT),
            _claim("instrument", "market", prior=WIDE, payoff=AN_INSTRUMENT),
            _claim(
                "untradeable",
                "not_tradeable",
                prior=WIDE,
                reason="Every instrument that would express this settles after the claim resolves.",
            ),
        ),
        links=(
            Link(
                id="start-to-step",
                source="start",
                target="step",
                mode="trigger",
                strength=1.2,
                lag=3.0,
                shape="step",
                half_life=None,
                rationale="The step follows from the claim the map starts from.",
                sources=(Source(url="https://example.test/document", title="A document"),),
                provenance="documented",
                reflexive=False,
            ),
            Link(
                id="step-to-contract",
                source="step",
                target="contract",
                mode="trigger",
                strength=0.9,
                lag=1.0,
                shape="step",
                half_life=None,
                rationale="The contract settles on what the step describes.",
                sources=(),
                provenance="argued",
                reflexive=False,
            ),
        ),
    )


# --- Which world the number comes from -------------------------------------


@given(graph=graphs(priors=uncertain_beliefs()), seed=seeds())
@a_few
def test_an_edge_reads_the_unsupposed_world(graph: Graph, seed: int) -> None:
    """Whatever the reader is looking at, the number inside an edge is the base world's.

    The edge is built twice — once with the base world shown, once with a branch
    world shown — and the model's likelihood inside it has to be the same object's
    worth of numbers both times, range and all.
    """
    tradeable = [one.id for one in graph.propositions if isinstance(one.payoff, ContractPayoff)]
    if not tradeable:
        return
    claim = tradeable[0]
    base = world_of(graph, seed=seed)
    supposed = world_of(
        graph,
        Branch(
            id="supposing",
            label="Suppose the ending itself",
            interventions=(Do(target=claim, value=True),),
        ),
        seed=seed,
    )
    quote = agreeing_quote(base, claim)

    plain = priced(base, base, claim, quote)
    with_a_supposition_on_screen = priced(base, supposed, claim, quote)

    assert isinstance(plain, Edge) and isinstance(with_a_supposition_on_screen, Edge)
    assert plain.model == base.beliefs[claim]
    assert with_a_supposition_on_screen.model == base.beliefs[claim]
    assert plain.buying == with_a_supposition_on_screen.buying
    assert plain.selling == with_a_supposition_on_screen.selling


@given(
    graph=graphs(priors=uncertain_beliefs()),
    drawn=st.data(),
    kind=st.sampled_from(("do", "observe", "insert")),
    seed=seeds(),
)
@a_few
def test_a_supposed_base_world_is_refused(
    graph: Graph, drawn: st.DataObject, kind: str, seed: int
) -> None:
    """Any value fixed on the base world refuses the edge, whichever button fixed it.

    One rule, not two: *Suppose this is true* and *This happened* are both refused,
    because both make the number on a tile answer a question a venue's price does
    not. A branch that only **adds** a claim fixes nothing, so it is accepted:
    nothing is pinned and the map is merely larger.
    """
    branch = Branch(
        id="edited",
        label="One edit on this map",
        interventions=(drawn.draw(interventions(graph, kind=kind)),),
    )
    folded = apply(graph, branch)
    assert not isinstance(folded, list), f"this one edit would not fold: {folded}"
    _, fixed = folded
    world = world_of(graph, branch, seed=seed)

    answer = priced(world, world, graph.hypothesis_id, None)

    assert isinstance(answer, NotComparable)
    if kind == "insert":
        assert not fixed
        assert answer.reason == "no_contract"
    else:
        assert fixed
        assert answer.reason == "conditional_world"
        assert answer.sentence == A_VALUE_IS_FIXED
        assert answer.break_even is None


@given(value=st.booleans(), supposing=st.booleans(), seed=seeds())
@a_few
def test_either_button_refuses_the_edge(value: bool, supposing: bool, seed: int) -> None:
    """Supposing a claim and reporting that it happened are refused in exactly the same words.

    The cost of that one conservative rule, said out loud: a reader who records a
    real, public fact loses the edge on that map until they start again from one
    without it, even though a price read afterwards already reflects the fact.
    """
    edit = Do(target="step", value=value) if supposing else Observe(target="step", value=value)
    world = world_of(
        every_row_map(),
        Branch(id="edited", label="One edit on this map", interventions=(edit,)),
        seed=seed,
    )

    answer = priced(world, world, "contract", agreeing_quote(world, "contract"))

    assert isinstance(answer, NotComparable)
    assert answer.reason == "conditional_world"
    assert answer.sentence == A_VALUE_IS_FIXED
    assert answer.break_even is None


# --- The arithmetic --------------------------------------------------------


@given(graph=graphs(priors=uncertain_beliefs()), seed=seeds())
@a_few
def test_agreeing_with_the_market_reads_exactly_zero(graph: Graph, seed: int) -> None:
    """A venue quoting both sides at the model's own number leaves nothing on the table.

    Exactly nothing, not nearly: the quote is built out of the world, so the
    subtraction is a number minus itself.
    """
    tradeable = [one.id for one in graph.propositions if isinstance(one.payoff, ContractPayoff)]
    if not tradeable:
        return
    claim = tradeable[0]
    base = world_of(graph, seed=seed)

    answer = priced(base, base, claim, agreeing_quote(base, claim), fee=0.0)

    assert isinstance(answer, Edge)
    assert answer.buying == 0.0
    assert answer.selling == 0.0


@given(
    seed=seeds(),
    move=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
    fee=st.floats(min_value=0.001, max_value=0.05, allow_nan=False),
)
@a_few
def test_buying_and_selling_edges_have_the_right_sign(seed: int, move: float, fee: float) -> None:
    """Raise the offer and buying is worth less; raise the bid and selling is worth more.

    And a fee takes from both, because it is paid whichever side you take. Every
    comparison here is between two edges off the same world, so nothing depends on
    what the engine's numbers happen to be.
    """
    base = world_of(every_row_map(), seed=seed)
    agrees = base.beliefs["contract"].p
    dearer = min(1.0, agrees + move)
    richer = max(0.0, agrees - move)

    at_the_model = priced(base, base, "contract", agreeing_quote(base, "contract"), fee=0.0)
    with_a_dearer_offer = priced(
        base, base, "contract", agreeing_quote(base, "contract", offer=dearer), fee=0.0
    )
    with_a_richer_bid = priced(
        base, base, "contract", agreeing_quote(base, "contract", bid=richer, offer=dearer), fee=0.0
    )
    paying_a_fee = priced(base, base, "contract", agreeing_quote(base, "contract"), fee=fee)

    assert isinstance(at_the_model, Edge)
    assert isinstance(with_a_dearer_offer, Edge)
    assert isinstance(with_a_richer_bid, Edge)
    assert isinstance(paying_a_fee, Edge)
    assert with_a_dearer_offer.buying <= at_the_model.buying
    assert with_a_richer_bid.selling <= at_the_model.selling
    assert paying_a_fee.buying < at_the_model.buying
    assert paying_a_fee.selling < at_the_model.selling
    # And the two edges are against the two prices, never against the midpoint.
    assert with_a_dearer_offer.buying == at_the_model.model.p - with_a_dearer_offer.quote.offer
    assert with_a_dearer_offer.selling == with_a_dearer_offer.quote.bid - at_the_model.model.p


@given(
    seed=seeds(),
    small=st.floats(min_value=0.0, max_value=0.02, allow_nan=False),
    extra=st.floats(min_value=0.001, max_value=0.05, allow_nan=False),
)
@a_few
def test_more_fees_widen_the_no_trade_band(seed: int, small: float, extra: float) -> None:
    """Paying more to deal lowers what is worth buying and raises what is worth selling."""
    base = world_of(every_row_map(), seed=seed)
    quote = agreeing_quote(base, "contract")

    cheap = priced(base, base, "contract", quote, fee=small)
    dear = priced(base, base, "contract", quote, fee=small + extra)

    assert isinstance(cheap, Edge) and isinstance(dear, Edge)
    assert dear.break_even.buy_below < cheap.break_even.buy_below
    assert dear.break_even.sell_above > cheap.break_even.sell_above
    width = dear.break_even.sell_above - dear.break_even.buy_below
    assert width > cheap.break_even.sell_above - cheap.break_even.buy_below
    # The band is the model's own number, one step each way, and never the midpoint.
    assert cheap.break_even.buy_below == cheap.model.p - small
    assert cheap.break_even.sell_above == cheap.model.p + small


@given(seed=seeds())
@a_few
def test_an_edge_inside_the_model_range_is_not_ranked(seed: int) -> None:
    """An edge that changes sign across the model's own range is marked, and not headlined.

    The price is put in the middle of the model's stated range, so buying is worth
    it if the model's number is at the top of its range and not if it is at the
    bottom. A gap smaller than how unsure the model is of its own number is not
    something to lead with.
    """
    base = world_of(every_row_map(), seed=seed)
    model = base.beliefs["contract"]
    assert model.lo < model.hi, (
        "this map's claim was built with a prior the model is unsure of, so the world "
        "it produces must carry a range with width for there to be a case here at all"
    )
    middle_of_the_range = (model.lo + model.hi) / 2.0

    inside = priced(
        base,
        base,
        "contract",
        agreeing_quote(base, "contract", bid=middle_of_the_range, offer=middle_of_the_range),
        fee=0.0,
    )
    outside = priced(
        base, base, "contract", agreeing_quote(base, "contract", bid=0.0, offer=0.0), fee=0.0
    )

    assert isinstance(inside, Edge) and isinstance(outside, Edge)
    assert inside.inside_the_model_range is True
    assert outside.inside_the_model_range is False
    # And that is exactly what "changes sign across the range" means, worked out here.
    assert (model.lo - middle_of_the_range < 0.0) != (model.hi - middle_of_the_range < 0.0)


# --- Every row of the decision table ---------------------------------------


@given(seed=seeds())
@a_few
def test_a_missing_quote_still_prints_a_break_even(seed: int) -> None:
    """A contract nobody has read a price for still says the price at which you would act."""
    base = world_of(every_row_map(), seed=seed)

    answer = priced(base, base, "contract", None, fee=0.0)

    assert isinstance(answer, NotComparable)
    assert answer.reason == "no_quote"
    assert answer.sentence == NO_PRICE_READ
    assert answer.break_even is not None
    assert answer.break_even.buy_below == base.beliefs["contract"].p
    assert answer.break_even.sell_above == base.beliefs["contract"].p


@given(seed=seeds(), quote=st.one_of(st.none(), quotes(source="recorded", live=True)))
@a_few
def test_a_price_ending_has_no_break_even_yet(seed: int, quote: Quote | None) -> None:
    """An ending that names something traded refuses, with or without a price beside it.

    No venue asks this claim's own question, so there is nothing to compare the
    model's number with — and the break-even for a trade like that is a **price**,
    which needs the entry price on the reader's own position.
    """
    base = world_of(every_row_map(), seed=seed)

    answer = priced(base, base, "instrument", quote)

    assert isinstance(answer, NotComparable)
    assert answer.reason == "no_contract"
    assert answer.sentence == NO_CONTRACT_QUOTES_IT
    assert answer.break_even is None


@given(seed=seeds(), quote=quotes(source="recorded", live=False))
@a_few
def test_every_case_has_a_row(seed: int, quote: Quote) -> None:
    """Each row of the table gives exactly what the table says, and no input is undefined."""
    graph = every_row_map()
    base = world_of(graph, seed=seed)
    live = agreeing_quote(base, "contract")

    on_the_start = priced(base, base, "start", live)
    on_a_step = priced(base, base, "step", live)
    on_an_untradeable_ending = priced(base, base, "untradeable", live)
    on_an_instrument = priced(base, base, "instrument", live)
    with_no_quote = priced(base, base, "contract", None)
    on_a_settled_market = priced(base, base, "contract", quote)
    with_a_live_quote = priced(base, base, "contract", live)

    assert isinstance(on_the_start, NotComparable)
    assert (on_the_start.reason, on_the_start.sentence) == ("no_contract", NO_TRADE_NAMED)
    assert on_the_start.break_even is None

    assert isinstance(on_a_step, NotComparable)
    assert (on_a_step.reason, on_a_step.sentence) == ("no_contract", NO_TRADE_NAMED)

    assert isinstance(on_an_untradeable_ending, NotComparable)
    assert on_an_untradeable_ending.reason == "no_contract"
    stored = next(one for one in graph.propositions if one.id == "untradeable")
    assert on_an_untradeable_ending.sentence == stored.not_tradeable_reason
    assert on_an_untradeable_ending.break_even is None

    assert isinstance(on_an_instrument, NotComparable)
    assert on_an_instrument.reason == "no_contract"

    assert isinstance(with_no_quote, NotComparable)
    assert with_no_quote.reason == "no_quote"
    assert with_no_quote.break_even is not None

    assert isinstance(on_a_settled_market, NotComparable)
    assert (on_a_settled_market.reason, on_a_settled_market.sentence) == (
        "settled_market",
        MARKET_HAS_SETTLED,
    )
    assert on_a_settled_market.break_even is not None

    assert isinstance(with_a_live_quote, Edge)
    assert with_a_live_quote.tick == live.tick


def test_a_claim_that_is_not_on_the_map_is_said_out_loud() -> None:
    """Pricing a claim the map does not have is our own bug, so it is not dressed as a refusal."""
    base = world_of(every_row_map())

    with pytest.raises(ValueError, match="is not on this map"):
        priced(base, base, "a-claim-nobody-put-on-this-map", None)


# --- The mixture, which explains and never computes -------------------------


@given(seed=seeds(), supposed_true=st.booleans())
@a_few
def test_the_mixture_terms_weigh_to_one(seed: int, supposed_true: bool) -> None:
    """The two weights sum to one and each reading names the world it came from.

    **Nothing here asserts the two terms add up to the unsupposed number**, because
    they measurably do not: a cause of the supposed claim may reach the ending
    another way, and supposing a claim pins a date as well as a truth. The mixture
    is an explanation shown beside the edge, never the thing the edge is built from.
    """
    graph = every_row_map()
    base = world_of(graph, seed=seed)
    one_way = world_of(
        graph,
        Branch(
            id="one-way",
            label="Suppose it",
            interventions=(Do(target="step", value=supposed_true),),
        ),
        seed=seed,
    )
    the_other = world_of(
        graph,
        Branch(
            id="the-other",
            label="Suppose it the other way",
            interventions=(Do(target="step", value=not supposed_true),),
        ),
        seed=seed,
    )

    answer = priced(
        base, one_way, "contract", agreeing_quote(base, "contract"), otherwise=the_other
    )

    assert isinstance(answer, Edge)
    mixture = answer.mixture
    assert mixture is not None
    assert mixture.supposed == "step"
    assert mixture.weight_supposed + mixture.weight_otherwise == 1.0
    chance = base.beliefs["step"].p
    assert mixture.weight_supposed == (chance if supposed_true else 1.0 - chance)
    assert mixture.reading_supposed == one_way.beliefs["contract"].p
    assert mixture.reading_otherwise == the_other.beliefs["contract"].p
    assert mixture.world_supposed == "one-way"
    assert mixture.world_otherwise == "the-other"
    # The edge itself is untouched by any of it.
    assert answer.model == base.beliefs["contract"]


@given(seed=seeds())
@a_few
def test_no_other_world_means_no_mixture(seed: int) -> None:
    """The mixture is shown only when the world where the supposition goes the other way is known.

    There is no honest way to read that number off the two worlds an edge already
    has: working it back out of the unsupposed number would assume the very
    equality this explanation does not claim.
    """
    graph = every_row_map()
    base = world_of(graph, seed=seed)
    supposed = world_of(
        graph,
        Branch(id="one-way", label="Suppose it", interventions=(Do(target="step", value=True),)),
        seed=seed,
    )

    answer = priced(base, supposed, "contract", agreeing_quote(base, "contract"))

    assert isinstance(answer, Edge)
    assert answer.mixture is None


@given(seed=seeds())
@a_few
def test_two_worlds_that_are_not_a_pair_are_refused(seed: int) -> None:
    """A mixture explains one supposition going both ways, and anything else is said out loud."""
    graph = every_row_map()
    base = world_of(graph, seed=seed)
    supposed = world_of(
        graph,
        Branch(id="one-way", label="Suppose it", interventions=(Do(target="step", value=True),)),
        seed=seed,
    )
    elsewhere = world_of(
        graph,
        Branch(
            id="elsewhere",
            label="Suppose something else",
            interventions=(Do(target="start", value=False),),
        ),
        seed=seed,
    )

    quote = agreeing_quote(base, "contract")

    with pytest.raises(ValueError, match="opposite directions"):
        priced(base, supposed, "contract", quote, otherwise=elsewhere)

    with pytest.raises(ValueError, match="exactly one value"):
        priced(base, base, "contract", quote, otherwise=supposed)
