"""The edge: which world, which side, which price, and every refusal.

Three mistakes would each make a finance-literate reader stop trusting every
number on the screen, and each has tests here whose only job is to catch it.

* **The wrong world.** *Suppose this is true* changes the question a tile answers,
  and a venue's price answers the old one. The check is exact and it is a *type*
  first: the function that builds an edge takes two worlds and both are required,
  so a caller holding only the world on screen cannot write the mistake down; and
  a world carrying a value fixed by either button is refused by name.
* **The wrong side.** A claim's number is the chance it comes **true**. An ending
  that takes the **no** side of a contract makes money when the claim fails, and
  the venue's no outcome is a separate contract that pays out then, so it is
  priced on one minus the claim's number with its range turned over. Setting a no
  price against the chance the claim comes true does not merely get the size
  wrong: it names the opposite side of the trade.
* **The wrong price.** You buy at the offer and sell at the bid, so there are two
  edges and the midpoint is never traded against.

**No number the engine computed is typed anywhere in this file.** Every quote is
built out of the world it is being compared with — and, on a no-side ending, out
of one minus that number, worked out in the test rather than read off the answer
under test. So the tests state identities, orderings and signs, and every one of
them would survive the engine's numbers all moving tomorrow.
"""

from datetime import UTC, date, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

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
    Retune,
    Source,
    World,
    apply,
    introduced_by,
    propagate,
)
from katalyst.grounding import Quote
from katalyst.thesis import Edge, NotComparable, priced, what_this_side_pays_on
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

Every rule checked here — which world a number is read from, which side it is
read on, the signs of the two edges, how the band moves with the fee, which
refusal comes back — is true at any budget. Only how steady a number is depends on
it, and nothing here reads a number for its own sake.
"""

SOME_INSTANT = datetime(2026, 9, 21, 14, 48, 27, tzinfo=UTC)
"""One instant a price was true. Every quote must carry one; nothing here reads it."""

VENUE = "Polymarket"
MARKET = "3501950"
"""The venue and market every contract ending in this file names, so a quote can match it."""

ADDED_ENDING = "the-contract-ending"
"""What the ending attached to a generated map is called. `graphs()` numbers its own."""


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


def the_payoff(world: World, claim: PropositionId) -> ContractPayoff:
    """The contract one ending on a world's map names."""
    found = next(one for one in world.graph.propositions if one.id == claim)
    assert isinstance(found.payoff, ContractPayoff)
    return found.payoff


def pays_on(world: World, claim: PropositionId) -> Belief:
    """What this ending's side of the contract pays on, worked out in the test.

    Deliberately not read off anything `priced` returns: the flip is the thing
    under test, so it is done here from the claim's own number and compared with
    what came back.
    """
    model = world.beliefs[claim]
    if the_payoff(world, claim).side == "yes":
        return model
    return Belief(p=1.0 - model.p, lo=1.0 - model.hi, hi=1.0 - model.lo, owner=model.owner)


def agreeing_quote(world: World, claim: PropositionId, **changed: object) -> Quote:
    """A venue quote for this ending's own contract, agreeing exactly with the side it pays on.

    Both sides of the book are what this ending's side of the contract pays on, so
    any edge against it is exactly nothing before a test moves a price. **No number
    is typed**: the quote is built out of the world it will be compared with, and
    the venue, the market and the side are read off the ending's own payoff, so it
    is the price of the thing the claim actually names.

    Args:
        world: The world the number is read from.
        claim: The ending being priced.
        **changed: Fields to replace afterwards, such as a moved offer or a flag
            saying no order could be placed.

    Returns:
        One quote, read from a venue.
    """
    payoff = the_payoff(world, claim)
    agrees = pays_on(world, claim).p
    quote = Quote(
        bid=agrees,
        offer=agrees,
        as_of=SOME_INSTANT,
        source="recorded",
        active=True,
        closed=False,
        archived=False,
        accepting_orders=True,
        venue=payoff.venue,
        condition_id="0xthe-contract",
        market_id=payoff.contract_id,
        token_id=f"the-{payoff.side}-outcome",
        side=payoff.side,
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


def a_contract(side: str) -> ContractPayoff:
    """An ending that names a contract somebody sells, on one side of it."""
    return ContractPayoff(
        venue=VENUE,
        contract_id=MARKET,
        title="Does the venue ask the claim's own question?",
        side=side,
    )


AN_INSTRUMENT = PricePayoff(
    instrument="the front-month futures contract", direction="short", move=0.03
)
"""An ending that names something traded, which no venue quotes on this claim's own question."""

WIDE = Belief(p=0.35, lo=0.22, hi=0.5, owner="model")
"""A prior the model is genuinely unsure of, so the world it produces has a range with width."""


def an_arrow(identifier: str, source: str, target: str) -> Link:
    """One arrow on a small hand-built map, carrying a mechanism and nothing surprising."""
    return Link(
        id=identifier,
        source=source,
        target=target,
        mode="trigger",
        strength=0.9,
        lag=1.0,
        shape="step",
        half_life=None,
        rationale="The ending settles on what the claim before it describes.",
        sources=(Source(url="https://example.test/document", title="A document"),),
        provenance="documented",
        reflexive=False,
    )


def every_row_map() -> Graph:
    """One small map carrying every kind of ending the decision table has a row for."""
    return Graph(
        id="every-row",
        hypothesis_id="start",
        propositions=(
            _claim("start", "hypothesis", prior=WIDE),
            _claim("step", "event", prior=WIDE),
            _claim("contract", "market", prior=WIDE, payoff=a_contract("yes")),
            _claim("no_side", "market", prior=WIDE, payoff=a_contract("no")),
            _claim("instrument", "market", prior=WIDE, payoff=AN_INSTRUMENT),
            _claim(
                "untradeable",
                "not_tradeable",
                prior=WIDE,
                reason="Every instrument that would express this settles after the claim resolves.",
            ),
        ),
        links=(
            an_arrow("start-to-step", "start", "step"),
            an_arrow("step-to-contract", "step", "contract"),
            an_arrow("step-to-no-side", "step", "no_side"),
        ),
    )


@composite
def maps_with_a_contract_ending(draw: object, side: str | None = None) -> Graph:
    """A generated map with a contract ending **built onto it**, on one side or the other.

    A drawn map has a contract ending only about four times in ten, so a property
    test that simply skipped the rest would be quietly checking nothing on most of
    its examples. The house rule is that a property test builds its inputs, so one
    is attached here rather than hoped for.

    Generates: a map from `graphs()` with uncertain priors, plus one ending naming
    a contract and an arrow from the map's own starting claim to it.
    Guarantees: the ending is there every time, and both sides of a contract are
    drawn, so no rule below is checked on the yes side alone.

    Args:
        draw: Supplied by the generator library.
        side: Pin which side of the contract the ending takes; otherwise either.
    """
    drawn = draw(graphs(priors=uncertain_beliefs()))  # type: ignore[attr-defined]
    chosen = side if side is not None else draw(st.sampled_from(("yes", "no")))  # type: ignore[attr-defined]
    ending = _claim(
        ADDED_ENDING,
        "market",
        prior=draw(uncertain_beliefs()),  # type: ignore[attr-defined]
        payoff=a_contract(chosen),
    )
    return drawn.model_copy(
        update={
            "propositions": (*drawn.propositions, ending),
            "links": (
                *drawn.links,
                an_arrow(f"arrow-to-{ADDED_ENDING}", drawn.hypothesis_id, ADDED_ENDING),
            ),
        }
    )


# --- Which world the number comes from -------------------------------------


@given(graph=maps_with_a_contract_ending(), seed=seeds())
@a_few
def test_an_edge_reads_the_unsupposed_world(graph: Graph, seed: int) -> None:
    """Whatever the reader is looking at, the number inside an edge is the base world's.

    The edge is built twice — once with the base world shown, once with a branch
    world shown — and the model's likelihood inside it has to be the same numbers
    both times, range and all.
    """
    base = world_of(graph, seed=seed)
    supposed = world_of(
        graph,
        Branch(
            id="supposing",
            label="Suppose the ending itself",
            interventions=(Do(target=ADDED_ENDING, value=True),),
        ),
        seed=seed,
    )
    quote = agreeing_quote(base, ADDED_ENDING)

    plain = priced(base, base, ADDED_ENDING, quote, fee=None)
    with_a_supposition_on_screen = priced(base, supposed, ADDED_ENDING, quote, fee=None)

    assert isinstance(plain, Edge) and isinstance(with_a_supposition_on_screen, Edge)
    assert plain.model == base.beliefs[ADDED_ENDING]
    assert with_a_supposition_on_screen.model == base.beliefs[ADDED_ENDING]
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

    answer = priced(world, world, graph.hypothesis_id, None, fee=None)

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

    answer = priced(world, world, "contract", agreeing_quote(world, "contract"), fee=None)

    assert isinstance(answer, NotComparable)
    assert answer.reason == "conditional_world"
    assert answer.sentence == A_VALUE_IS_FIXED
    assert answer.break_even is None


@given(seed=seeds())
@a_few
def test_an_edge_says_when_its_number_came_from_an_edited_map(seed: int) -> None:
    """Retuning an arrow fixes no value, so it is allowed — and the edge says the map was edited.

    Thirteen points of model number can move under the reader's own hand without a
    single value being pinned, which is a bigger distortion than most of what the
    fixed-value rule refuses. It is allowed because the rule is about *fixed
    values*, and it is carried rather than hidden so that the card has something to
    read when it tells the reader the number came from an edited map.
    """
    graph = every_row_map()
    untouched = world_of(graph, seed=seed)
    retuned = world_of(
        graph,
        Branch(
            id="retuned",
            label="A harder push",
            interventions=(Retune(link="step-to-contract", strength=2.5),),
        ),
        seed=seed,
    )

    plain = priced(
        untouched, untouched, "contract", agreeing_quote(untouched, "contract"), fee=None
    )
    edited = priced(retuned, retuned, "contract", agreeing_quote(retuned, "contract"), fee=None)

    assert isinstance(plain, Edge) and isinstance(edited, Edge)
    assert plain.base_branch is None
    assert edited.base_branch == "retuned"
    # The number really did move, which is why the card has to say the map was edited.
    assert edited.model != plain.model


# --- Which side of the contract --------------------------------------------


@given(graph=maps_with_a_contract_ending(side="no"), seed=seeds())
@a_few
def test_a_no_side_ending_is_priced_on_the_chance_the_claim_fails(graph: Graph, seed: int) -> None:
    """A no contract pays when the claim fails, so it is priced on one minus the claim's number.

    The flip is worked out here, in the test, from the claim's own number; nothing
    is read off the answer under test. The range turns over with it, because the
    low end of *false* is one minus the high end of *true*.
    """
    base = world_of(graph, seed=seed)
    model = base.beliefs[ADDED_ENDING]
    quote = agreeing_quote(base, ADDED_ENDING)

    answer = priced(base, base, ADDED_ENDING, quote, fee=None)

    assert isinstance(answer, Edge)
    assert answer.model == model
    assert answer.pays_on.p == 1.0 - model.p
    assert answer.pays_on.lo == 1.0 - model.hi
    assert answer.pays_on.hi == 1.0 - model.lo
    # The quote agrees with what this side pays on, so both edges are exactly nothing.
    assert answer.buying == 0.0
    assert answer.selling == 0.0
    # And the break-even is that number, not the claim's.
    assert answer.break_even.buy_below == 1.0 - model.p


@given(
    graph=maps_with_a_contract_ending(side="no"),
    seed=seeds(),
    dearer=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
)
@a_few
def test_a_no_side_edge_names_the_side_of_the_trade_a_reader_should_take(
    graph: Graph, seed: int, dearer: float
) -> None:
    """Price the no contract below what it pays on and buying is the positive side.

    This is the sharp half of the defect it exists to catch: setting a no price
    against the chance the claim comes *true* does not merely get the size wrong,
    it points the reader at the opposite side of the trade. Everything below is
    worked out from the world.
    """
    base = world_of(graph, seed=seed)
    worth = pays_on(base, ADDED_ENDING).p
    cheap = max(0.0, worth - dearer)
    quote = agreeing_quote(base, ADDED_ENDING, bid=max(0.0, cheap - 0.01), offer=cheap)

    answer = priced(base, base, ADDED_ENDING, quote, fee=None)

    assert isinstance(answer, Edge)
    assert answer.buying == worth - quote.offer
    assert answer.selling == quote.bid - worth
    assert answer.buying > 0.0 >= answer.selling


@given(model=uncertain_beliefs(), seed=seeds())
@many
def test_the_two_sides_of_one_contract_always_pay_on_one_whole(model: Belief, seed: int) -> None:
    """Whatever the claim's number, the yes side and the no side pay on numbers summing to one."""
    yes = what_this_side_pays_on(model, "yes")
    no = what_this_side_pays_on(model, "no")

    assert yes == model
    assert yes.p + no.p == 1.0
    assert yes.lo + no.hi == 1.0
    assert yes.hi + no.lo == 1.0
    assert no.lo <= no.p <= no.hi


@given(seed=seeds())
@a_few
def test_a_quote_for_another_contract_or_the_other_side_is_said_out_loud(seed: int) -> None:
    """A price only becomes an edge against the contract and the side it was read for.

    Three ways of being the wrong price, all of them a broken promise between our
    own pieces of code rather than anything a reader did — so all three are raised,
    the way a claim that is not on the map already is, and never priced quietly.
    """
    base = world_of(every_row_map(), seed=seed)
    right = agreeing_quote(base, "contract")

    for wrong in (
        right.model_copy(update={"side": "no"}),
        right.model_copy(update={"market_id": "7654321"}),
        right.model_copy(update={"venue": "Another venue"}),
    ):
        with pytest.raises(ValueError, match="only an edge against the contract and the side"):
            priced(base, base, "contract", wrong, fee=None)

    # And the quote that does belong to this ending prices it.
    assert isinstance(priced(base, base, "contract", right, fee=None), Edge)


@given(seed=seeds(), price=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
@a_few
def test_a_price_the_reader_typed_is_taken_for_the_side_they_were_looking_at(
    seed: int, price: float
) -> None:
    """A typed price names no venue and no side, so there is nothing to match it against.

    It is their report of what they can get on the ending they were looking at, so
    it is priced on that ending's own side — one minus the claim's number on a no
    side, exactly as a venue's own price would be.
    """
    base = world_of(every_row_map(), seed=seed)
    typed = Quote(bid=price, offer=price, as_of=SOME_INSTANT, source="user")

    on_the_yes = priced(base, base, "contract", typed, fee=None)
    on_the_no = priced(base, base, "no_side", typed, fee=None)

    assert isinstance(on_the_yes, Edge) and isinstance(on_the_no, Edge)
    assert on_the_yes.buying == base.beliefs["contract"].p - price
    assert on_the_no.buying == (1.0 - base.beliefs["no_side"].p) - price


# --- The arithmetic --------------------------------------------------------


@given(graph=maps_with_a_contract_ending(), seed=seeds())
@a_few
def test_agreeing_with_the_market_reads_exactly_zero(graph: Graph, seed: int) -> None:
    """A venue quoting both sides at what this ending pays on leaves nothing on the table.

    Exactly nothing, not nearly: the quote is built out of the world, so the
    subtraction is a number minus itself — on the no side as much as the yes side,
    because the quote agrees with what *that* side pays on.
    """
    base = world_of(graph, seed=seed)

    answer = priced(base, base, ADDED_ENDING, agreeing_quote(base, ADDED_ENDING), fee=0.0)

    assert isinstance(answer, Edge)
    assert answer.buying == 0.0
    assert answer.selling == 0.0


@given(
    graph=maps_with_a_contract_ending(),
    seed=seeds(),
    move=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
    fee=st.floats(min_value=0.001, max_value=0.05, allow_nan=False),
)
@a_few
def test_buying_and_selling_edges_have_the_right_sign(
    graph: Graph, seed: int, move: float, fee: float
) -> None:
    """Raise the offer and buying is worth less; raise the bid and selling is worth more.

    And a fee takes from both, because it is paid whichever side you take. Every
    comparison is between two edges off the same world, so nothing depends on what
    the engine's numbers happen to be.
    """
    base = world_of(graph, seed=seed)
    worth = pays_on(base, ADDED_ENDING).p
    higher = min(1.0, worth + move)
    lower = max(0.0, worth - move)

    def priced_at(bid: float, offer: float, paying: float) -> Edge:
        answer = priced(
            base,
            base,
            ADDED_ENDING,
            agreeing_quote(base, ADDED_ENDING, bid=bid, offer=offer),
            fee=paying,
        )
        assert isinstance(answer, Edge)
        return answer

    at_the_model = priced_at(worth, worth, 0.0)
    with_a_dearer_offer = priced_at(lower, higher, 0.0)
    with_a_higher_bid = priced_at(min(higher, 1.0), min(higher, 1.0), 0.0)
    paying_a_fee = priced_at(worth, worth, fee)

    assert with_a_dearer_offer.buying <= at_the_model.buying
    assert with_a_higher_bid.selling >= at_the_model.selling
    assert paying_a_fee.buying < at_the_model.buying
    assert paying_a_fee.selling < at_the_model.selling
    # And the two edges are against the two prices, never against the midpoint.
    assert with_a_dearer_offer.buying == worth - with_a_dearer_offer.quote.offer
    assert with_a_dearer_offer.selling == with_a_dearer_offer.quote.bid - worth
    assert with_a_dearer_offer.quote.bid != with_a_dearer_offer.quote.midpoint


@given(
    graph=maps_with_a_contract_ending(),
    seed=seeds(),
    small=st.floats(min_value=0.0, max_value=0.02, allow_nan=False),
    extra=st.floats(min_value=0.001, max_value=0.05, allow_nan=False),
)
@a_few
def test_more_fees_widen_the_no_trade_band(
    graph: Graph, seed: int, small: float, extra: float
) -> None:
    """Paying more to deal lowers what is worth buying and raises what is worth selling."""
    base = world_of(graph, seed=seed)
    quote = agreeing_quote(base, ADDED_ENDING)
    worth = pays_on(base, ADDED_ENDING).p

    cheap = priced(base, base, ADDED_ENDING, quote, fee=small)
    dear = priced(base, base, ADDED_ENDING, quote, fee=small + extra)

    assert isinstance(cheap, Edge) and isinstance(dear, Edge)
    assert dear.break_even.buy_below < cheap.break_even.buy_below
    assert dear.break_even.sell_above > cheap.break_even.sell_above
    width = dear.break_even.sell_above - dear.break_even.buy_below
    assert width > cheap.break_even.sell_above - cheap.break_even.buy_below
    # The band is this side's own number, one step each way, and never the midpoint.
    assert cheap.break_even.buy_below == worth - small
    assert cheap.break_even.sell_above == worth + small


@given(graph=maps_with_a_contract_ending(), seed=seeds())
@a_few
def test_an_unknown_fee_is_said_rather_than_counted_as_nothing(graph: Graph, seed: int) -> None:
    """Nobody has read the venue's schedule, so the answer carries that as a fact.

    The arithmetic then runs before fees — the same numbers a fee of nothing would
    give — and the difference between the two is the only thing that lets a card
    print *fees unknown* instead of a number that looks net of them.
    """
    base = world_of(graph, seed=seed)
    quote = agreeing_quote(base, ADDED_ENDING)

    unknown = priced(base, base, ADDED_ENDING, quote, fee=None)
    nothing = priced(base, base, ADDED_ENDING, quote, fee=0.0)
    no_quote = priced(base, base, ADDED_ENDING, None, fee=None)

    assert isinstance(unknown, Edge) and isinstance(nothing, Edge)
    assert unknown.fee is None
    assert unknown.break_even.fee is None
    assert nothing.fee == 0.0
    assert nothing.break_even.fee == 0.0
    assert (unknown.buying, unknown.selling) == (nothing.buying, nothing.selling)
    assert unknown.break_even.buy_below == nothing.break_even.buy_below
    # A refusal carries it too, so no answer this file builds can lose the caveat.
    assert isinstance(no_quote, NotComparable)
    assert no_quote.fee is None
    assert no_quote.break_even is not None and no_quote.break_even.fee is None


@given(seed=seeds())
@a_few
def test_an_edge_inside_the_model_range_is_not_ranked(seed: int) -> None:
    """An edge worth taking at one end of the model's own range and not the other is marked.

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
    # And that is exactly what "worth taking at one end and not the other" means.
    assert (model.lo - middle_of_the_range > 0.0) != (model.hi - middle_of_the_range > 0.0)


@given(seed=seeds())
@a_few
def test_the_selling_side_alone_can_mark_an_edge_as_inside_the_range(seed: int) -> None:
    """Both sides are checked, so an offer nobody would cross does not hide a straddling bid.

    An offer above the whole range makes buying worth nothing at either end, and a
    bid *inside* the range makes selling worth taking at the bottom of it and not
    at the top. Check only the buying side and this case reads as a clean edge.
    """
    base = world_of(every_row_map(), seed=seed)
    model = base.beliefs["contract"]
    assert model.lo < model.hi
    inside_the_range = (model.lo + model.hi) / 2.0
    above_everything = min(1.0, model.hi + (model.hi - model.lo))

    answer = priced(
        base,
        base,
        "contract",
        agreeing_quote(base, "contract", bid=inside_the_range, offer=above_everything),
        fee=0.0,
    )

    assert isinstance(answer, Edge)
    # Buying is worth nothing at both ends of the range: only selling straddles.
    assert model.lo - above_everything < 0.0
    assert model.hi - above_everything <= 0.0
    assert (inside_the_range - model.lo > 0.0) != (inside_the_range - model.hi > 0.0)
    assert answer.inside_the_model_range is True


@given(seed=seeds())
@a_few
def test_an_edge_of_exactly_nothing_at_one_end_counts_as_not_worth_taking(seed: int) -> None:
    """Worth taking means strictly better than nothing, so an end reading nought is marked.

    A gap of exactly nothing pays for nothing, so it sits with the ends not worth
    crossing the spread for. Putting the price exactly on the top of the range
    makes the buying edge nought there and negative below it.
    """
    base = world_of(every_row_map(), seed=seed)
    model = base.beliefs["contract"]
    assert model.lo < model.hi

    answer = priced(
        base,
        base,
        "contract",
        agreeing_quote(base, "contract", bid=0.0, offer=model.hi),
        fee=0.0,
    )

    assert isinstance(answer, Edge)
    assert model.hi - model.hi == 0.0
    assert model.lo - model.hi < 0.0
    assert answer.inside_the_model_range is False


# --- Every row of the decision table ---------------------------------------


@given(graph=maps_with_a_contract_ending(), seed=seeds())
@a_few
def test_a_missing_quote_still_prints_a_break_even(graph: Graph, seed: int) -> None:
    """A contract nobody has read a price for still says the price at which you would act."""
    base = world_of(graph, seed=seed)
    worth = pays_on(base, ADDED_ENDING).p

    answer = priced(base, base, ADDED_ENDING, None, fee=0.0)

    assert isinstance(answer, NotComparable)
    assert answer.reason == "no_quote"
    assert answer.sentence == NO_PRICE_READ
    assert answer.break_even is not None
    assert answer.break_even.buy_below == worth
    assert answer.break_even.sell_above == worth


@given(seed=seeds(), quote=st.one_of(st.none(), quotes(source="recorded", live=True)))
@a_few
def test_a_price_ending_has_no_break_even_yet(seed: int, quote: Quote | None) -> None:
    """An ending that names something traded refuses, with or without a price beside it.

    No venue asks this claim's own question, so there is nothing to compare the
    model's number with — and the break-even for a trade like that is a **price**,
    which needs the entry price on the reader's own position. The quote handed in
    is for some other market entirely, which is exactly the point: this row is
    reached before any price is looked at.
    """
    base = world_of(every_row_map(), seed=seed)

    answer = priced(base, base, "instrument", quote, fee=None)

    assert isinstance(answer, NotComparable)
    assert answer.reason == "no_contract"
    assert answer.sentence == NO_CONTRACT_QUOTES_IT
    assert answer.break_even is None


@given(seed=seeds(), ending=st.sampled_from(("contract", "no_side")))
@a_few
def test_every_case_has_a_row(seed: int, ending: str) -> None:
    """Each row of the table gives exactly what the table says, and no input is undefined."""
    graph = every_row_map()
    base = world_of(graph, seed=seed)
    live = agreeing_quote(base, ending)
    settled = agreeing_quote(base, ending, accepting_orders=False)

    on_the_start = priced(base, base, "start", None, fee=None)
    on_a_step = priced(base, base, "step", None, fee=None)
    on_an_untradeable_ending = priced(base, base, "untradeable", None, fee=None)
    on_an_instrument = priced(base, base, "instrument", None, fee=None)
    with_no_quote = priced(base, base, ending, None, fee=None)
    on_a_settled_market = priced(base, base, ending, settled, fee=None)
    with_a_live_quote = priced(base, base, ending, live, fee=None)

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
        priced(base, base, "a-claim-nobody-put-on-this-map", None, fee=None)


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
        base,
        one_way,
        "contract",
        agreeing_quote(base, "contract"),
        fee=None,
        otherwise=the_other,
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


@given(seed=seeds(), supposed_true=st.booleans())
@a_few
def test_supposing_the_very_ending_being_priced_builds_no_mixture(
    seed: int, supposed_true: bool
) -> None:
    """A claim a supposition is holding reads exactly 1, and no surface may print that.

    Suppose the ending being priced — an ordinary thing for a reader to do — and the
    two readings become 1 and 0. The terms then weigh to the unsupposed number
    *exactly*, by arithmetic rather than by explanation, which is the one claim
    this shape must never make. So there is no mixture at all, and the edge beside
    it is unchanged.
    """
    graph = every_row_map()
    base = world_of(graph, seed=seed)
    one_way = world_of(
        graph,
        Branch(
            id="one-way",
            label="Suppose the ending",
            interventions=(Do(target="contract", value=supposed_true),),
        ),
        seed=seed,
    )
    the_other = world_of(
        graph,
        Branch(
            id="the-other",
            label="Suppose the ending the other way",
            interventions=(Do(target="contract", value=not supposed_true),),
        ),
        seed=seed,
    )
    # The thing this refusal exists to keep off a card: the stored numbers are the
    # ones the rules layer says are there for arithmetic and for nothing else.
    assert {one_way.beliefs["contract"].p, the_other.beliefs["contract"].p} == {0.0, 1.0}
    assert "supposed" in set(one_way.states["contract"])

    answer = priced(
        base,
        one_way,
        "contract",
        agreeing_quote(base, "contract"),
        fee=None,
        otherwise=the_other,
    )

    assert isinstance(answer, Edge)
    assert answer.mixture is None
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

    answer = priced(base, supposed, "contract", agreeing_quote(base, "contract"), fee=None)

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
        priced(base, supposed, "contract", quote, fee=None, otherwise=elsewhere)

    with pytest.raises(ValueError, match="exactly one value"):
        priced(base, base, "contract", quote, fee=None, otherwise=supposed)
