"""The card: who owns every number, how two kinds of ending are ranked, and what it refuses.

Four mistakes would each undo the card, and each has tests here whose only job is
to catch it.

* **A number nobody owns.** Every figure on a card says whether it is the
  reader's, the model's, a venue's or something this program worked out. The check
  walks a whole built card and fails on any bare number it finds.
* **One blended ranking.** An edge in cents and a move in per cent are not the
  same quantity, so the card ranks two kinds of ending by two rules and keeps the
  lists apart. The check is that every row names the rule that placed it and that
  neither list is ever ordered against the other.
* **A probability on a shock.** The reader supposed it; that is not a forecast.
  The check is that the shape carries no field one could go in.
* **An average where the tails belong.** Tails are ranked by what they would do to
  the position, never by how likely they are times how much they would cost, which
  is an expected loss by another name.

**No number an engine computed is typed anywhere in this file.** Every number is
either one a test chose so a rule can be stated about it, or one read out of the
world the test built and compared with itself.
"""

from datetime import date
from inspect import signature

import numpy
import pytest
from pydantic import BaseModel

from katalyst.domain import Belief, Branch, Do, PropositionId, World
from katalyst.grounding import Quote
from katalyst.thesis import (
    NEVER,
    Card,
    Carried,
    ClaimMove,
    Dropped,
    Edge,
    Figure,
    FirstTouch,
    LiftRow,
    NotPriced,
    PricedIn,
    Refusal,
    Shocked,
    Tail,
    Unhedgeable,
    Watched,
    card_of,
    first_touch,
    priced,
    walk,
    what_else_can_i_trade,
    what_your_risk_budget_implies,
    where_the_numbers_came_from,
)
from katalyst.thesis.card import (
    A_PRICE_YOU_ENTERED,
    INSIDE_THE_MODEL_RANGE,
    NARROWER_THAN_A_TICK,
    NO_DAYS_TO_COUNT,
    NO_EDGE_AT_THIS_PRICE,
    NO_SHIFT_WAS_WORKED_OUT,
    NOT_ADVICE,
    NOTHING_WAS_PRICED,
    OWNER_SAYS,
    REFUSES,
    THE_BARRIER_SHIFT,
    THE_CHANCE_CAME_FROM,
    ShockRow,
    models,
)
from katalyst.thesis.draws import THE_SAMPLE_SAYS
from katalyst.thesis.edge import NO_CONTRACT_QUOTES_IT, NO_PRICE_READ
from katalyst.thesis.paths import the_sample_s_own_chance
from katalyst.thesis.position import REFUSALS
from tests.thesis.cards import (
    OTHER_MARKET,
    a_card,
    a_card_map,
    a_ceiling,
    a_chance,
    a_first_touch,
    a_lift_row,
    a_no_side_map,
    a_position,
    a_rail,
    a_shift,
    a_world,
    what_was_priced,
)
from tests.thesis.synthetic import worlds_of
from tests.thesis.test_edge import MARKET, agreeing_quote, pays_on, world_of

SOME_DAY = date(2026, 10, 15)
"""One day before the endings on this map are judged. Nothing reads it as a number."""


def quote_at(
    world: World, claim: PropositionId, *, bid: float, offer: float, **rest: object
) -> Quote:
    """A venue quote for this ending's own contract, at two prices the test chose.

    Built out of the world it will be compared with, so the venue, the market and
    the side are the ending's own and nothing about the contract is typed.
    """
    return agreeing_quote(world, claim).model_copy(update={"bid": bid, "offer": offer, **rest})


def every_number(thing: object, at: str = "card") -> list[tuple[str, object]]:
    """Every value anywhere inside a built card that is a number and not a figure.

    Walks the whole card, stepping into every model, list and dictionary. A figure
    is the one place a number is allowed to live, so it is not stepped into: what
    comes back is everything a rendering could print without being handed an owner.
    """
    if isinstance(thing, Figure):
        return []
    if isinstance(thing, BaseModel):
        found: list[tuple[str, object]] = []
        for name in type(thing).model_fields:
            found += every_number(getattr(thing, name), f"{at}.{name}")
        return found
    if isinstance(thing, list | tuple):
        found = []
        for index, one in enumerate(thing):
            found += every_number(one, f"{at}[{index}]")
        return found
    if isinstance(thing, bool):
        return []
    if isinstance(thing, int | float):
        return [(at, thing)]
    return []


def every_figure(thing: object) -> list[Figure]:
    """Every figure anywhere inside a built card, in the order they are reached."""
    if isinstance(thing, Figure):
        return [thing]
    if isinstance(thing, BaseModel):
        found: list[Figure] = []
        for name in type(thing).model_fields:
            found += every_figure(getattr(thing, name))
        return found
    if isinstance(thing, list | tuple):
        found = []
        for one in thing:
            found += every_figure(one)
        return found
    return []


def a_rich_card() -> Card:
    """One card with something in every section, so a whole card can be read at once."""
    world = a_world()
    contract = what_was_priced(world, "contract", agreeing_quote(world, "contract"), fee=0.01)
    return a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={
            "contract": contract,
            "other-contract": what_was_priced(world, "other-contract", None),
            "instrument": what_was_priced(world, "instrument", None),
        },
        shifts={"instrument": a_shift("instrument", 0.2)},
        carried_by=(Carried(claim="step", points=0.12, share=0.7),),
        rail=a_rail(rows=(a_lift_row("step", 3.1),), too_few_draws=None),
        market_chance={"step": a_chance("venue_quote"), "instrument": a_chance("sample_share")},
        watch=(
            Watched(
                claim="step",
                resolves=SOME_DAY,
                observed_by="the publication that settles it",
                hurts_by=-0.06,
            ),
        ),
        unhedgeable=(
            Unhedgeable(
                claim="other-contract",
                why="It is judged on the same day as the ending, so nothing warns you in time.",
                resolves=date(2026, 11, 1),
                can_be_seen=True,
            ),
        ),
        tails=(
            Tail(
                claim="step",
                likelihood=Belief(p=0.08, lo=0.04, hi=0.15, owner="model"),
                harm=9.0,
                what_could_be_done="Nothing on this map hedges it.",
            ),
        ),
        shocks=(Shocked(name="Iran is struck", change_to_the_position=-4.1),),
        costs=0.02,
    )


# --- Every number says who it belongs to -------------------------------------


def test_every_card_number_names_its_owner() -> None:
    """A whole built card holds no bare numbers: every one of them is a figure with an owner.

    The one exception is named rather than hidden — the seed, which is not a
    measurement of anything and is printed as an identifier.
    """
    card = a_rich_card()

    bare = [where for where, _ in every_number(card) if where != "card.seed"]

    assert bare == []
    assert all(one.owner in OWNER_SAYS for one in every_figure(card))
    assert every_figure(card), "a card with something in every section has figures in it"


def test_a_number_the_reader_typed_is_never_labelled_a_venues() -> None:
    """A price the reader entered is theirs. A price a venue published is the venue's.

    Record 0020's rule made mechanical: a reader knows a price, not a venue's
    bookkeeping, and their own report never fills the market's slot.
    """
    world = a_world()
    agrees = pays_on(world, "contract").p
    read_on = agreeing_quote(world, "contract").as_of
    typed = Quote(bid=agrees, offer=agrees, as_of=read_on, source="user")

    from_a_venue = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": what_was_priced(world, "contract", agreeing_quote(world, "contract"))},
    ).priced_in
    from_the_reader = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": what_was_priced(world, "contract", typed)},
    ).priced_in

    assert isinstance(from_a_venue, PricedIn) and isinstance(from_the_reader, PricedIn)
    assert from_a_venue.quote.bid.owner == "venue"
    assert from_the_reader.quote.bid.owner == "reader"
    assert from_the_reader.quote.offer.owner == "reader"
    assert from_the_reader.quote.midpoint.owner == "reader"
    assert from_the_reader.quote.venue == A_PRICE_YOU_ENTERED
    assert from_the_reader.quote.bid.source is None


def test_a_card_reads_a_likelihood_only_from_the_model() -> None:
    """A belief that is not the model's is refused rather than relabelled.

    Three voices are never merged, and the merge that would be easiest to make by
    accident is labelling somebody else's number as the model's.
    """
    with pytest.raises(ValueError, match="owned by 'user'"):
        models(Belief(p=0.4, lo=0.3, hi=0.5, owner="user"), "a number that is not the model's")


def test_the_model_keeps_its_own_range() -> None:
    """The figure built from a belief carries that belief's own range, and does not invent one."""
    world = a_world()
    stated = world.beliefs["contract"]

    figure = models(stated, "the chance this claim comes true")

    assert (figure.value, figure.lo, figure.hi) == (stated.p, stated.lo, stated.hi)


def test_no_array_reaches_the_card() -> None:
    """The shapes underneath carry one row per drawn world; none of it reaches a card.

    A card is something a person reads. Fifty thousand worlds by twenty claims is a
    million numbers, and the way that stays out is that this layer reads shares,
    counts and days off those arrays and never carries the arrays themselves.
    """
    card = a_rich_card()

    def arrays(thing: object) -> list[object]:
        if isinstance(thing, numpy.ndarray):
            return [thing]
        if isinstance(thing, BaseModel):
            return [
                found for name in type(thing).model_fields for found in arrays(getattr(thing, name))
            ]
        if isinstance(thing, list | tuple):
            return [found for one in thing for found in arrays(one)]
        return []

    assert arrays(card) == []


# --- A price ending is a first-class trade -----------------------------------


def test_a_price_ending_carries_the_refusal_and_a_break_even_of_its_own() -> None:
    """An ending naming an instrument says no contract quotes it, and prices its own break-even.

    The recorded map the walk opens has eleven endings and every one names an
    instrument. If the card only worked on contracts the walk would have to change
    maps halfway through.
    """
    world = a_world()

    card = a_card(world, position=a_position("instrument"), costs=0.02)

    priced_in = card.priced_in
    assert isinstance(priced_in, NotPriced)
    assert priced_in.because == "no_contract"
    assert priced_in.sentence == NO_CONTRACT_QUOTES_IT
    assert priced_in.buy_below is None and priced_in.sell_above is None
    assert priced_in.price_break_even is not None
    assert priced_in.costs_are_unknown is None


def test_an_instrument_break_even_moves_the_entry_and_the_side_says_which_way() -> None:
    """Getting out of a long costs you upwards; getting out of a short costs you downwards.

    Stated as two comparisons against the reader's own entry price, so nothing here
    depends on what the costs happen to be.
    """
    world = a_world()
    entry = a_position().entry

    long_ = a_card(world, position=a_position("instrument", side="long"), costs=0.02).priced_in
    short = a_card(world, position=a_position("instrument", side="short"), costs=0.02).priced_in

    assert isinstance(long_, NotPriced) and isinstance(short, NotPriced)
    assert long_.price_break_even is not None and short.price_break_even is not None
    assert long_.price_break_even.value > entry
    assert short.price_break_even.value < entry
    assert entry - short.price_break_even.value == long_.price_break_even.value - entry


def test_unknown_costs_are_said_and_the_break_even_is_the_entry_itself() -> None:
    """Nobody has stated what it costs to get in and out, so the card says so in words.

    An unknown cost treated quietly as nothing would print a number that looks net
    when it is not. And **no venue's fee is mentioned at all** on an ending no
    venue quotes: a sentence about this venue's schedule, on a claim whose whole
    refusal is that no contract quotes it, names something that is not there.
    """
    world = a_world()

    card = a_card(world, position=a_position("instrument"), costs=None)

    priced_in = card.priced_in
    assert isinstance(priced_in, NotPriced)
    assert priced_in.price_break_even is not None
    assert priced_in.price_break_even.value == a_position().entry
    assert priced_in.costs_are_unknown is not None
    assert priced_in.fee_is_unknown is None


def test_a_contract_ending_with_no_quote_keeps_its_break_even_in_likelihoods() -> None:
    """A contract's break-even is a likelihood, and it needs no quote at all.

    An instrument's is a price and needs the reader's entry, so the two never
    appear together.
    """
    world = a_world()

    card = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": what_was_priced(world, "contract", None, fee=0.01)},
    )

    priced_in = card.priced_in
    assert isinstance(priced_in, NotPriced)
    assert priced_in.because == "no_quote"
    assert priced_in.sentence == NO_PRICE_READ
    assert priced_in.buy_below is not None and priced_in.sell_above is not None
    assert priced_in.price_break_even is None
    assert priced_in.fee is not None and priced_in.fee.owner == "venue"
    assert priced_in.fee_is_unknown is None


# --- Two rules, kept apart ---------------------------------------------------


def test_the_two_rankings_are_never_blended() -> None:
    """Every ranked row names the rule that placed it, and no ending is in both lists."""
    world = a_world()
    cheap = pays_on(world, "contract")
    also = pays_on(world, "other-contract")

    ranked = what_else_can_i_trade(
        world,
        {
            "contract": what_was_priced(
                world,
                "contract",
                quote_at(world, "contract", bid=cheap.lo - 0.03, offer=cheap.lo - 0.02),
            ),
            "other-contract": what_was_priced(
                world,
                "other-contract",
                quote_at(world, "other-contract", bid=also.lo - 0.06, offer=also.lo - 0.05),
            ),
        },
        {
            "instrument": a_shift("instrument", 0.2),
            "other-instrument": a_shift("other-instrument", 0.1),
        },
    )

    by_edge = ranked.by_the_size_of_its_edge
    by_shift = ranked.by_the_shift_times_the_move
    assert len(by_edge) == 2 and len(by_shift) == 2
    assert ranked.not_ranked == ()
    assert [one.ranked_by for one in by_edge] == ["the_size_of_its_edge"] * len(by_edge)
    assert [one.ranked_by for one in by_shift] == ["the_shift_times_the_move"] * len(by_shift)
    assert {one.ending for one in by_edge}.isdisjoint({one.ending for one in by_shift})
    assert [one.key.value for one in by_edge] == sorted(
        (one.key.value for one in by_edge), reverse=True
    )
    assert [one.key.value for one in by_shift] == sorted(
        (one.key.value for one in by_shift), reverse=True
    )
    assert "untradeable" not in {one.ending for one in (*by_edge, *by_shift, *ranked.not_ranked)}


def test_the_better_edge_ranks_the_row_and_names_its_side() -> None:
    """The key is the better of the two edges, whichever side it favours, and it says which.

    Compared against the same edge's own two numbers rather than against anything
    typed: the key has to be one of them, and the larger one.
    """
    world = a_world()
    pays = pays_on(world, "contract")
    buying = what_was_priced(
        world, "contract", quote_at(world, "contract", bid=pays.lo - 0.03, offer=pays.lo - 0.02)
    )
    selling = what_was_priced(
        world, "contract", quote_at(world, "contract", bid=pays.hi + 0.02, offer=pays.hi + 0.03)
    )

    assert isinstance(buying, Edge) and isinstance(selling, Edge)
    one = what_else_can_i_trade(world, {"contract": buying}, {}).by_the_size_of_its_edge[0]
    other = what_else_can_i_trade(world, {"contract": selling}, {}).by_the_size_of_its_edge[0]

    assert one.key.value == buying.buying > buying.selling
    assert "buying" in one.key.about
    assert other.key.value == selling.selling > selling.buying
    assert "selling" in other.key.about
    assert {figure.value for figure in one.made_of} == {buying.buying, buying.selling}
    # The row names the venue's own contract, never the claim's identifier: a
    # reader-typed quote carries no market identifier, and a claim is not a trade.
    assert one.instrument == MARKET != one.ending


def test_the_shift_rule_is_the_shift_times_the_move_and_shows_both() -> None:
    """A bigger shift on the same payoff ranks higher, and the row carries both numbers.

    The shift is a synthetic value the test chose, because the exact core that will
    work one out is a separate piece of work; what is asserted is the ordering and
    the identity, which hold at any value.
    """
    world = a_world()
    payoff_move = next(
        one.payoff.move  # type: ignore[union-attr]
        for one in a_card_map().propositions
        if one.id == "instrument"
    )

    ranked = what_else_can_i_trade(
        world,
        {},
        {
            "instrument": a_shift("instrument", 0.2),
            "other-instrument": a_shift("other-instrument", 0.02),
        },
    ).by_the_shift_times_the_move

    assert [one.ending for one in ranked] == ["instrument", "other-instrument"]
    assert ranked[0].key.value == 0.2 * payoff_move
    assert {figure.value for figure in ranked[0].made_of} == {0.2, payoff_move}
    assert ranked[0].made_of[1].owner == "model"


def test_a_shift_that_points_the_other_way_ranks_on_its_size() -> None:
    """A hypothesis that lowers an ending moves it as far as one that raises it."""
    world = a_world()

    up = what_else_can_i_trade(world, {}, {"instrument": a_shift("instrument", 0.2)})
    down = what_else_can_i_trade(world, {}, {"instrument": a_shift("instrument", -0.2)})

    assert up.by_the_shift_times_the_move[0].key.value == (
        down.by_the_shift_times_the_move[0].key.value
    )
    assert down.by_the_shift_times_the_move[0].made_of[0].value < 0


def test_an_edge_inside_the_model_range_is_not_ranked_and_says_so() -> None:
    """An edge smaller than the model's own uncertainty is neither led with nor ranked."""
    world = a_world()
    pays = pays_on(world, "contract")
    straddling = what_was_priced(
        world, "contract", quote_at(world, "contract", bid=pays.p, offer=pays.p)
    )

    ranked = what_else_can_i_trade(world, {"contract": straddling}, {})

    assert isinstance(straddling, Edge) and straddling.inside_the_model_range
    assert ranked.by_the_size_of_its_edge == ()
    left_out = next(one for one in ranked.not_ranked if one.ending == "contract")
    assert left_out.because == "inside_the_model_range"
    assert left_out.sentence == INSIDE_THE_MODEL_RANGE


def test_a_gap_narrower_than_a_tick_is_ranked_but_never_led_with() -> None:
    """A gap smaller than the venue's smallest price step is listed, and not headlined.

    The tick here is made wide enough to bite rather than realistic, and it is
    worked out from the world's own numbers rather than typed: the rule under test
    is the comparison between a gap and a step, not the size of either.
    """
    world = a_world()
    pays = pays_on(world, "contract")
    offer = pays.lo - 0.01
    wide_step = (pays.p - offer) + 0.01
    narrow = what_was_priced(
        world,
        "contract",
        quote_at(world, "contract", bid=offer - 0.01, offer=offer, tick=wide_step),
    )
    ordinary = what_was_priced(
        world, "contract", quote_at(world, "contract", bid=offer - 0.01, offer=offer)
    )

    thin = what_else_can_i_trade(world, {"contract": narrow}, {}).by_the_size_of_its_edge[0]
    thick = what_else_can_i_trade(world, {"contract": ordinary}, {}).by_the_size_of_its_edge[0]

    assert thin.headline is False
    assert thin.not_headlined_because == NARROWER_THAN_A_TICK
    assert thick.headline is True
    assert thick.not_headlined_because is None


def test_an_ending_neither_rule_can_rank_is_listed_with_its_reason() -> None:
    """Three ways an ending misses the ranking, each said out loud rather than dropped."""
    world = a_world()

    ranked = what_else_can_i_trade(
        world, {"contract": what_was_priced(world, "contract", None)}, {}
    )

    reasons = {one.ending: (one.because, one.sentence) for one in ranked.not_ranked}
    assert reasons["contract"] == ("no_edge", NO_PRICE_READ)
    assert reasons["other-contract"] == ("no_edge", NOTHING_WAS_PRICED)
    assert reasons["instrument"] == ("no_shift", NO_SHIFT_WAS_WORKED_OUT)
    assert reasons["other-instrument"] == ("no_shift", NO_SHIFT_WAS_WORKED_OUT)


def test_a_priced_answer_about_another_map_is_said_out_loud() -> None:
    """Mixing two maps is a broken promise between our own pieces of code, not a card state."""
    world = a_world()

    with pytest.raises(ValueError, match="is not on this map"):
        what_else_can_i_trade(
            world, {"a-claim-from-elsewhere": what_was_priced(world, "step", None)}, {}
        )


# --- The headline, and what it refuses to lead with --------------------------


def test_agreeing_with_the_market_leads_with_no_edge_at_this_price() -> None:
    """When neither side is worth taking, that is a complete answer and not a gap.

    The quote is built out of the world it is compared with, so the two agree
    exactly and neither edge is positive without a number being typed.
    """
    world = a_world()

    card = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": what_was_priced(world, "contract", agreeing_quote(world, "contract"))},
    )

    priced_in = card.priced_in
    assert isinstance(priced_in, PricedIn)
    assert priced_in.headline == "no_edge_at_this_price"
    assert priced_in.not_headlined_because == NO_EDGE_AT_THIS_PRICE
    assert priced_in.buying.value == 0.0 and priced_in.selling.value == 0.0


def test_the_headline_names_the_side_that_is_worth_taking() -> None:
    """Buying below what this side pays on leads with buying; selling above it with selling."""
    world = a_world()
    pays = pays_on(world, "contract")

    def headline(bid: float, offer: float) -> str:
        card = a_card(
            world,
            position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
            answers={
                "contract": what_was_priced(
                    world, "contract", quote_at(world, "contract", bid=bid, offer=offer)
                )
            },
        )
        assert isinstance(card.priced_in, PricedIn)
        return card.priced_in.headline

    assert headline(pays.lo - 0.03, pays.lo - 0.02) == "buying"
    assert headline(pays.hi + 0.02, pays.hi + 0.03) == "selling"


def test_a_narrow_headline_says_why_it_is_not_led_with() -> None:
    """A positive edge narrower than one price step is shown with the reason it is not led with."""
    world = a_world()
    pays = pays_on(world, "contract")
    offer = pays.lo - 0.01
    step = (pays.p - offer) + 0.01

    card = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={
            "contract": what_was_priced(
                world,
                "contract",
                quote_at(world, "contract", bid=offer - 0.01, offer=offer, tick=step),
            )
        },
    )

    assert isinstance(card.priced_in, PricedIn)
    assert card.priced_in.headline == "buying"
    assert card.priced_in.not_headlined_because == NARROWER_THAN_A_TICK


def test_the_mixture_explains_and_never_adds_up() -> None:
    """The four terms are shown with their weights summing to one, and nothing more is claimed."""
    graph = a_card_map()
    base = world_of(graph)
    supposed = world_of(
        graph, Branch(id="yes", label="Suppose", interventions=(Do(target="step", value=True),))
    )
    otherwise = world_of(
        graph, Branch(id="no", label="Suppose not", interventions=(Do(target="step", value=False),))
    )
    answer = priced(
        base, supposed, "contract", agreeing_quote(base, "contract"), fee=None, otherwise=otherwise
    )

    card = a_card(
        base,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": answer},
    )

    assert isinstance(card.priced_in, PricedIn)
    mixture = card.priced_in.mixture
    assert mixture is not None
    assert mixture.supposed == "step"
    assert mixture.weight_supposed.value + mixture.weight_otherwise.value == 1.0
    assert {mixture.reading_supposed.owner, mixture.weight_supposed.owner} == {"model"}


def test_no_supposition_leaves_no_mixture() -> None:
    """A card built on the untouched map has nothing to explain, so it explains nothing."""
    world = a_world()

    card = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": what_was_priced(world, "contract", agreeing_quote(world, "contract"))},
    )

    assert isinstance(card.priced_in, PricedIn)
    assert card.priced_in.mixture is None


# --- A shock, a tail, and what the card refuses to average --------------------


def test_a_shock_has_nowhere_to_put_a_probability() -> None:
    """The shape carries no field a probability could go in, so none can be attached.

    A rule enforced by a shape is a rule nobody has to remember.
    """
    card = a_rich_card()

    assert "probability" not in ShockRow.model_fields
    assert "probability" not in Shocked.model_fields
    assert card.shocks[0].placed_by == "reader"
    assert "supposing something is not a statement about how likely it is" in card.shocks[0].says


def test_the_tails_are_ranked_by_harm_and_never_by_harm_times_likelihood() -> None:
    """The worst case comes first, whatever its chance, because an average hides it.

    The two tails here are chosen so the two rules disagree: the second is likelier
    and its harm times its chance is larger, and it still ranks second.
    """
    world = a_world()
    worse = Tail(
        claim="step",
        likelihood=Belief(p=0.02, lo=0.01, hi=0.05, owner="model"),
        harm=40.0,
        what_could_be_done="Nothing on this map hedges it.",
    )
    likelier = Tail(
        claim="contract",
        likelihood=Belief(p=0.5, lo=0.4, hi=0.6, owner="model"),
        harm=10.0,
        what_could_be_done="The watchlist would warn you.",
    )

    card = a_card(world, tails=(likelier, worse))

    assert worse.likelihood.p * worse.harm < likelier.likelihood.p * likelier.harm
    assert [one.claim for one in card.tails] == ["step", "contract"]
    assert card.tails[0].likelihood.owner == "model"
    assert card.tails[0].harm.owner == "computed"


# --- What the numbers rest on ------------------------------------------------


def test_a_first_touch_number_names_its_sample_and_every_market_chance() -> None:
    """Record 0019's rule: both things are said in the same sentence as the number."""
    world = a_world()

    card = a_card(
        world,
        touch=a_first_touch(),
        market_chance={"step": a_chance("venue_quote"), "instrument": a_chance("sample_share")},
    )

    share = card.your_exit.stop_first
    said = card.your_exit.sample_says
    assert share is not None and share.source == THE_SAMPLE_SAYS["built_by_hand"]
    assert said is not None
    assert THE_SAMPLE_SAYS["built_by_hand"] in said
    assert THE_CHANCE_CAME_FROM["venue_quote"] in said
    assert THE_CHANCE_CAME_FROM["sample_share"] in said
    assert "step" in said and "instrument" in said


def test_a_map_where_nothing_moves_the_price_says_that_instead() -> None:
    """No claim moves the price, so there was no market chance to name, and the sentence says so."""
    said = where_the_numbers_came_from("built_by_hand", {})

    assert THE_SAMPLE_SAYS["built_by_hand"] in said
    assert "no market chance was needed" in said


def test_the_card_names_the_market_chances_the_price_paths_actually_applied() -> None:
    """The one promise about the market's chance is kept by the shape, not by a convention.

    The card takes the record the **walk itself** hands back, so what it names
    cannot be a list of sources somebody wrote out beside the paths. This test
    takes the whole route rather than a hand-built first touch: it draws worlds,
    walks paths through them, reads first touch off those paths, and builds a card
    on the result.

    The second move hands in **no** chance at all, so the walk works one out from
    the drawn worlds and records it as the sample's own share. Nothing a caller
    could have typed would produce that entry, which is the point: the sentence
    beside the shares names what was used.
    """
    drawn = worlds_of(claims=["step", "contract"], on=[[2, 5], [NEVER, 9], [7, NEVER]])
    typed = a_position()
    moves = (
        ClaimMove(claim="step", move=1.5, market_chance=0.3, market_chance_from="venue_quote"),
        ClaimMove(
            claim="contract", move=-0.8, market_chance=None, market_chance_from="sample_share"
        ),
    )
    paths = walk(drawn, moves, entry=typed.entry, daily_move=typed.daily_move, seed=11)
    touch = first_touch(paths, typed)
    assert isinstance(touch, FirstTouch)

    card = a_card(a_world(), position=typed, touch=touch, market_chance=paths.market_chance)

    said = card.your_exit.sample_says
    assert said is not None
    assert {claim: one.came_from for claim, one in paths.market_chance.items()} == {
        "step": "venue_quote",
        "contract": "sample_share",
    }
    for claim, one in paths.market_chance.items():
        assert claim in said and THE_CHANCE_CAME_FROM[one.came_from] in said
    assert moves[1].market_chance is None
    assert paths.market_chance["contract"].value == the_sample_s_own_chance(drawn, "contract")


def test_the_shares_name_the_window_they_were_read_to() -> None:
    """Two shares over a window nobody named are two numbers nobody can check."""
    typed = a_position()
    touch = a_first_touch()

    card = a_card(a_world(), position=typed, touch=touch)

    through = card.your_exit.through
    assert through is not None
    assert through.value == float(touch.through)
    assert through.kind == "days"
    assert card.your_exit.horizon == typed.horizon
    assert "you expect to be out" in THE_BARRIER_SHIFT


def test_the_rail_says_what_every_share_rests_on_and_what_it_left_off() -> None:
    """Each row carries its interval and its count, and a dropped claim is said out loud."""
    world = a_world()
    dropped = Dropped(
        claim="contract",
        because="tells_you_nothing",
        sentence="This came on about as often where the stop went first as it did everywhere else.",
    )

    card = a_card(
        world,
        rail=a_rail(rows=(a_lift_row("step", 3.1),), dropped=(dropped,)),
        market_chance={"step": a_chance("base_world")},
    )

    row = card.takes_you_out.rows[0]
    assert row.came_on_first.lo is not None and row.came_on_first.hi is not None
    assert row.lift.lo is None and row.lift.hi is None
    assert row.draws.value == 410.0
    assert row.coverage.value == 0.95
    assert card.takes_you_out.left_off == ("contract: " + dropped.sentence,)
    assert card.takes_you_out.floor.value == 200.0
    assert card.takes_you_out.stop_first_worlds.value == 1000.0
    assert THE_SAMPLE_SAYS["built_by_hand"] in card.takes_you_out.sample_says


def test_an_empty_rail_says_why_it_is_empty() -> None:
    """A rail with no rows and no reason reads as *nothing takes you out*, which is flattering."""
    world = a_world()

    card = a_card(world, rail=a_rail(too_few_draws="Fewer than 200 effective drawn worlds."))

    assert card.takes_you_out.rows == ()
    assert card.takes_you_out.too_few_draws is not None


def test_a_contract_refuses_first_touch_by_name() -> None:
    """A contract is held to resolution, so there is no path to touch and the card says so."""
    world = a_world()
    refusal = Refusal(
        code="first_touch_on_a_contract",
        field="stop",
        sentence=REFUSALS["first_touch_on_a_contract"],
    )

    card = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": what_was_priced(world, "contract", None)},
        touch=refusal,
    )

    assert card.your_exit.stop_first is None
    assert card.your_exit.target_first is None
    assert card.your_exit.neither is None
    assert card.your_exit.stop_at is None and card.your_exit.target_at is None
    assert card.your_exit.through is None, "no shares were read, so there is no window to name"
    assert card.your_exit.first_touch_refused == REFUSALS["first_touch_on_a_contract"]
    assert card.your_exit.method is None


# --- The exit, the ceiling and what the card does not know -------------------


def test_the_exit_is_the_readers_and_the_shares_are_not() -> None:
    """Everything the reader typed is theirs; everything read off drawn worlds is computed."""
    world = a_world()
    typed = a_position()

    card = a_card(world, position=typed)

    assert card.your_exit.stop.value == typed.stop
    assert card.your_exit.stop.owner == "reader"
    assert card.your_exit.target.owner == "reader"
    assert card.your_exit.entry.owner == "reader"
    assert card.your_exit.risk_budget.owner == "reader"
    assert card.your_exit.implied_size.owner == "reader"
    assert card.your_exit.horizon == typed.horizon
    assert card.your_exit.stop_first is not None
    assert card.your_exit.stop_first.owner == "computed"


def test_the_size_on_the_card_is_the_one_the_risk_budget_implies_and_not_a_number_handed_in() -> (
    None
):
    """The card asks the module that owns the arithmetic; it is not a number a caller passes.

    There is no argument for it, so a caller cannot put a size on the card that
    the reader's own two numbers do not imply. The card still computes nothing:
    asking `position.py` for the answer leaves the sum in one place.
    """
    typed = a_position()

    card = a_card(a_world(), position=typed)

    assert card.your_exit.implied_size.value == what_your_risk_budget_implies(typed)
    assert "implied_size" not in signature(card_of).parameters


def test_the_ceiling_keeps_zero_and_absent_apart() -> None:
    """Zero means the arithmetic ran; absent means there was none to run. Neither is a blank."""
    world = a_world()

    nothing_to_put_on = a_card(
        world, ceiling=a_ceiling(fraction=0.0, at=0.22, sentence="The range disagrees.")
    ).your_exit.ceiling
    none_at_all = a_card(
        world,
        ceiling=a_ceiling(
            fraction=None, taken_by=None, at=None, sentence="A ceiling needs an edge."
        ),
    ).your_exit.ceiling
    a_number = a_card(world).your_exit.ceiling

    assert nothing_to_put_on.fraction is not None and nothing_to_put_on.fraction.value == 0.0
    assert none_at_all.fraction is None and none_at_all.at is None
    assert none_at_all.sentence is not None
    assert a_number.fraction is not None and a_number.sentence is None
    assert a_number.warning == none_at_all.warning != ""


def test_a_card_carries_every_refusal_the_not_advice_line_and_the_execution_sentence() -> None:
    """The limits are data on the card, not a footer somebody can strip."""
    card = a_rich_card()

    assert card.does_not_know.refuses == REFUSES
    assert len(REFUSES) == 8
    assert card.does_not_know.not_advice == NOT_ADVICE
    assert "trigger is not its fill price" in card.does_not_know.execution


# --- Broken promises between our own pieces of code --------------------------


def test_a_card_needs_what_was_priced_for_the_ending_it_trades() -> None:
    """A card whose traded ending was never priced has no *what is priced in* to show."""
    world = a_world()

    with pytest.raises(ValueError, match="nothing was handed in"):
        a_card(world, position=a_position("instrument"), answers={})


def test_a_row_naming_a_claim_the_map_does_not_carry_is_said_out_loud() -> None:
    """Every row on a card points into the map beside it, or the card is not built at all."""
    world = a_world()

    with pytest.raises(ValueError, match="is not on this map"):
        a_card(world, carried_by=(Carried(claim="not-on-this-map", points=0.1, share=0.5),))
    with pytest.raises(ValueError, match="is not on this map"):
        a_card(world, position=a_position("not-on-this-map"))


def test_the_trade_reads_the_venue_and_the_side_off_the_map() -> None:
    """A position cannot name a trade the map does not: the facts come from the payoff."""
    world = a_world()

    contract = a_card(
        world,
        position=a_position("other-contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"other-contract": what_was_priced(world, "other-contract", None)},
    ).the_trade
    instrument = a_card(world, position=a_position("instrument")).the_trade

    assert contract.contract_id == OTHER_MARKET
    assert contract.venue is not None and contract.contract_side == "yes"
    assert instrument.contract_id is None
    assert instrument.venue is None and instrument.contract_side is None
    assert instrument.resolution_test and instrument.resolved_by


def test_a_card_names_the_map_the_branch_and_the_seed_it_came_from() -> None:
    """A card can always be thrown away and rebuilt, and it says from what."""
    world = a_world(seed=7)

    card = a_card(world)

    assert (card.base_id, card.branch_id, card.seed) == (world.base_id, world.branch_id, world.seed)
    assert card.as_of == world.day_zero
    assert card.hypothesis == world.graph.hypothesis_id


def test_the_watchlist_and_the_unhedgeable_rows_carry_their_reasons() -> None:
    """What is watched says when and who publishes it; what is not says why not."""
    card = a_rich_card()

    watched = card.watch[0]
    assert watched.resolves == SOME_DAY
    assert watched.observed_by
    assert watched.hurts_by.owner == "computed"
    assert card.unhedgeable[0].can_be_seen is True
    assert card.unhedgeable[0].why
    assert card.carried_by[0].points.owner == "computed"


# --- The fix round: the reviewer's failing inputs, reproduced ----------------


def a_contract_card(**rest: object) -> Card:
    """One card on the yes-side contract ending, with whatever a test wants changed."""
    world = a_world()
    answers = rest.pop("answers", None) or {
        "contract": what_was_priced(world, "contract", agreeing_quote(world, "contract"), fee=0.01)
    }
    return a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers=answers,  # type: ignore[arg-type]
        **rest,  # type: ignore[arg-type]
    )


def test_an_edge_inside_the_model_range_is_not_led_with_either() -> None:
    """Record 0018: such an edge is neither headlined nor ranked. Today only the ranking obeys.

    The reviewer's input: a quote five points under the claim's own number, so
    buying is worth something at the middle of the model's stated range and
    nothing at its bottom end.
    """
    world = a_world()
    pays = pays_on(world, "contract")
    straddling = what_was_priced(
        world,
        "contract",
        quote_at(world, "contract", bid=pays.lo - 0.05, offer=pays.p - 0.05),
    )

    card = a_contract_card(answers={"contract": straddling})

    assert isinstance(straddling, Edge) and straddling.inside_the_model_range
    assert isinstance(card.priced_in, PricedIn)
    assert card.priced_in.buying.value > 0.0
    assert card.priced_in.headline == "no_edge_at_this_price"
    assert card.priced_in.not_headlined_because == INSIDE_THE_MODEL_RANGE


def test_a_ranked_row_whose_best_edge_is_a_loss_is_never_led_with() -> None:
    """A venue pricing an ending out of reach makes it less worth leading with, not more.

    The reviewer's input: a quote four tenths either side of the claim's own
    number, so neither side is worth taking by a wide margin.
    """
    world = a_world()
    pays = pays_on(world, "contract")
    hopeless = what_was_priced(
        world, "contract", quote_at(world, "contract", bid=pays.p - 0.4, offer=pays.p + 0.4)
    )

    unticked = what_was_priced(
        world,
        "contract",
        quote_at(world, "contract", bid=pays.p - 0.4, offer=pays.p + 0.4, tick=None),
    )

    row = what_else_can_i_trade(world, {"contract": hopeless}, {}).by_the_size_of_its_edge[0]
    no_step = what_else_can_i_trade(world, {"contract": unticked}, {}).by_the_size_of_its_edge[0]

    assert row.key.value < 0.0
    assert row.headline is False
    assert row.not_headlined_because == NO_EDGE_AT_THIS_PRICE
    # And with no price step published there is no tick rule to lean on, so the
    # only thing keeping this row from being led with is that it is a loss.
    assert no_step.key.value < 0.0
    assert no_step.headline is False
    assert no_step.not_headlined_because == NO_EDGE_AT_THIS_PRICE


def test_an_answer_filed_under_the_wrong_claim_is_refused_by_name() -> None:
    """A card that printed one claim's numbers under another's name is untraceable state."""
    world = a_world()
    elsewhere = what_was_priced(world, "other-contract", None)

    with pytest.raises(ValueError, match="is the answer for"):
        what_else_can_i_trade(world, {"contract": elsewhere}, {})
    with pytest.raises(ValueError, match="is the answer for"):
        a_contract_card(answers={"contract": elsewhere})


def test_a_rail_row_with_no_day_count_says_why_rather_than_reading_nothing() -> None:
    """A claim that kept company with the trade working has no days to count, and says so."""
    world = a_world()
    row = a_lift_row("step", 3.1)
    without = LiftRow(**{**row.__dict__, "days_before_the_stop": None})

    card = a_card(world, rail=a_rail(rows=(without,)))

    shown = card.takes_you_out.rows[0]
    assert shown.days_before_the_stop is None
    assert shown.no_days_because == NO_DAYS_TO_COUNT


def test_a_no_side_contract_card_prices_the_side_that_pays_when_the_claim_fails() -> None:
    """An ending taking the no side pays when the claim fails, and the card reads it that way.

    Worked by hand on this map. The claim's own number is `p`; the no outcome is a
    separate order book that pays one when the claim fails, so what this side pays
    on is `1 - p`, with its range turned over: the low end of *false* is one minus
    the high end of *true*. The quote below is built out of that flipped number, so
    both edges are exactly nothing and neither is the claim's own number.

    Three things nothing else on this branch guards: the claim's own number and
    what the side pays on are **different** figures here; the model figure is the
    claim's own number and not the flipped one; and the trade says `no`.
    """
    world = world_of(a_no_side_map())
    claim = world.beliefs["no-side"]
    answer = what_was_priced(world, "no-side", agreeing_quote(world, "no-side"))

    card = a_card(
        world,
        position=a_position("no-side", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"no-side": answer},
    )

    priced_in = card.priced_in
    assert isinstance(priced_in, PricedIn)
    assert card.the_trade.contract_side == "no"
    assert priced_in.model.value == claim.p
    assert priced_in.pays_on.value == 1.0 - claim.p
    assert (priced_in.pays_on.lo, priced_in.pays_on.hi) == (1.0 - claim.hi, 1.0 - claim.lo)
    assert priced_in.model.value != priced_in.pays_on.value
    assert priced_in.quote.bid.value == 1.0 - claim.p
    assert priced_in.buying.value == 0.0 and priced_in.selling.value == 0.0


def test_the_two_break_even_prices_are_not_written_out_the_wrong_way_round() -> None:
    """Worth buying below, worth selling above — and the card carries each where it belongs."""
    world = a_world()
    answer = what_was_priced(world, "contract", agreeing_quote(world, "contract"), fee=0.01)

    card = a_contract_card(answers={"contract": answer})

    assert isinstance(answer, Edge) and isinstance(card.priced_in, PricedIn)
    assert card.priced_in.buy_below.value == answer.break_even.buy_below
    assert card.priced_in.sell_above.value == answer.break_even.sell_above
    assert card.priced_in.buy_below.value < card.priced_in.sell_above.value


def test_the_two_first_touch_levels_are_not_written_out_the_wrong_way_round() -> None:
    """The stop is checked below the entry and the target above it, and they stay apart."""
    world = a_world()
    touch = a_first_touch()
    typed = a_position()

    card = a_card(world, position=typed, touch=touch)

    assert card.your_exit.stop_at is not None and card.your_exit.target_at is not None
    assert card.your_exit.stop_at.value == touch.stop_at
    assert card.your_exit.target_at.value == touch.target_at
    assert card.your_exit.stop_at.value < typed.entry < card.your_exit.target_at.value
