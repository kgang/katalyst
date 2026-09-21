"""The export: legs and conditions, a committed description, and limits carried as data.

Three things are checked here that nothing else can check.

* **The committed description is the document's own.** `export.schema.json` is
  regenerated from the shapes and compared byte for byte, so a field that changes
  without the description changing fails.
* **Every document answers that description.** A small reader of the committed
  file, written below and shown biting, is run over every export these tests
  build — including exports over maps nobody wrote by hand.
* **The limits travel with the document.** Every refusal, the not-advice line and
  the one execution sentence are fields, and the page a person reads carries an
  owner beside every number in it.

The reader of the description below understands only the small part of the
description language these shapes use — which types, which required keys, which
fixed values, which lists — and says so, and every rule it does understand is
shown catching a document that breaks it.
"""

import json
from datetime import date
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from katalyst.domain import Belief, Branch, Do, Graph
from katalyst.thesis import (
    EXPORT_SCHEMA_FILE,
    SCHEMA_NAME,
    Card,
    Carried,
    Dropped,
    Export,
    Figure,
    Leg,
    LiftRow,
    RiskExit,
    Shocked,
    Tail,
    Unhedgeable,
    Watched,
    as_json,
    as_markdown,
    export_of,
    priced,
    say,
    schema_json,
)
from katalyst.thesis.card import NO_DAYS_TO_COUNT, NOT_ADVICE, REFUSES
from katalyst.thesis.export import two_figures
from katalyst.thesis.position import REFUSALS, Refusal
from tests.strategies import seeds
from tests.thesis.cards import (
    a_card,
    a_card_map,
    a_ceiling,
    a_first_touch,
    a_lift_row,
    a_position,
    a_rail,
    a_shift,
    a_world,
    what_was_priced,
)
from tests.thesis.test_card import SOME_DAY, a_rich_card, every_figure, quote_at
from tests.thesis.test_edge import (
    ADDED_ENDING,
    agreeing_quote,
    maps_with_a_contract_ending,
    pays_on,
    world_of,
)

a_few = settings(max_examples=12, deadline=None)

THE_TOP_LEVEL = {
    "schema",
    "map",
    "hypothesis",
    "legs",
    "conditions",
    "risk_exit",
    "what_else",
    "refuses",
    "not_advice",
    "execution",
}
"""Everything a document has at its top level. Legs and conditions, and never an order."""


# --- A reader of the committed description ------------------------------------


def complaints(written: Any, against: dict[str, Any], defs: dict[str, Any], at: str) -> list[str]:
    """Every way one document fails the part of its description this reader understands.

    Understood: a named type, a fixed value, a closed list of values, an object's
    required keys and the description of each key it has, a list's item
    description and its shortest allowed length, a reference to a shape described
    elsewhere, and a choice between several descriptions. Everything else —
    titles, prose, formats, defaults — is read past, because it constrains
    nothing, and a test below fails the day the description grows a rule that is
    neither.

    Args:
        written: The part of the document being read.
        against: The description it must answer.
        defs: The shapes the description refers to by name.
        at: Where in the document this is, for the complaint.

    Returns:
        One sentence per failure, empty when the document answers the description.
    """
    if "$ref" in against:
        named = against["$ref"].rsplit("/", 1)[-1]
        return complaints(written, defs[named], defs, at)
    for either in ("anyOf", "oneOf"):
        if either in against:
            tried = [complaints(written, one, defs, at) for one in against[either]]
            if any(not one for one in tried):
                return []
            return [f"{at} answers none of the {len(tried)} descriptions it is offered"]
    found: list[str] = []
    if "const" in against and written != against["const"]:
        found.append(f"{at} is {written!r} where the description fixes it at {against['const']!r}")
    if "enum" in against and written not in against["enum"]:
        found.append(f"{at} is {written!r}, which is not one of {against['enum']}")
    kind = against.get("type")
    if kind is not None and not _is_a(written, kind):
        return [*found, f"{at} is {type(written).__name__} where the description says {kind}"]
    if kind == "object":
        for name in against.get("required", ()):
            if name not in written:
                found.append(f"{at} is missing {name!r}, which the description requires")
        for name, description in against.get("properties", {}).items():
            if name in written:
                found += complaints(written[name], description, defs, f"{at}.{name}")
    if kind == "array":
        least = against.get("minItems")
        if least is not None and len(written) < least:
            found.append(f"{at} holds {len(written)} where the description requires {least}")
        if "items" in against:
            for index, one in enumerate(written):
                found += complaints(one, against["items"], defs, f"{at}[{index}]")
    return found


def _is_a(written: object, kind: str) -> bool:
    """Whether one value is of the kind the description names."""
    if kind == "null":
        return written is None
    if kind == "boolean":
        return isinstance(written, bool)
    if kind == "integer":
        return isinstance(written, int) and not isinstance(written, bool)
    if kind == "number":
        return isinstance(written, int | float) and not isinstance(written, bool)
    if kind == "string":
        return isinstance(written, str)
    if kind == "array":
        return isinstance(written, list)
    return isinstance(written, dict)


def the_committed_description() -> dict[str, Any]:
    """The description of this document as it is committed beside the code, read from disk."""
    read: dict[str, Any] = json.loads(EXPORT_SCHEMA_FILE.read_text(encoding="utf-8"))
    return read


def fails(card: Card) -> list[str]:
    """Every way one card's document fails the committed description."""
    description = the_committed_description()
    written = json.loads(as_json(export_of(card)))
    return complaints(written, description, description.get("$defs", {}), "the document")


# --- The committed description, and that it is the document's own --------------


def test_the_committed_description_is_what_the_code_writes() -> None:
    """The file beside the code is exactly what the code produces, byte for byte.

    A description that is maintained by hand drifts from the thing it describes,
    and the drift is silent. This one cannot: the test regenerates it.
    """
    assert EXPORT_SCHEMA_FILE.read_text(encoding="utf-8") == schema_json()


def test_the_reader_of_the_description_bites() -> None:
    """Every rule the reader understands is shown catching a document that breaks it.

    A reader that accepted everything would make the test above it worthless, so
    each rule is broken on purpose here and the complaint is checked.
    """
    description = the_committed_description()
    defs = description.get("$defs", {})
    whole = json.loads(as_json(export_of(a_rich_card())))

    assert complaints(whole, description, defs, "the document") == []

    missing = {name: value for name, value in whole.items() if name != "legs"}
    numbered = {**whole, "not_advice": 7}
    a_shock = whole["conditions"]["shocks"][0]
    guessed = {
        **whole,
        "conditions": {
            **whole["conditions"],
            "shocks": [{**a_shock, "probability": 0.2}],
        },
    }
    renamed = {**whole, "schema": "something.else/9"}
    emptied = {**whole, "refuses": []}
    a_third_word = {
        **whole,
        "legs": [{**whole["legs"][0], "priced_in": {**whole["legs"][0]["priced_in"], "kind": "x"}}],
    }
    unowned = {
        **whole,
        "risk_exit": {
            **whole["risk_exit"],
            "stop": {**whole["risk_exit"]["stop"], "owner": "somebody else"},
        },
    }

    assert any("missing 'legs'" in one for one in complaints(missing, description, defs, "the"))
    assert complaints(numbered, description, defs, "the")
    assert complaints(guessed, description, defs, "the")
    assert complaints(renamed, description, defs, "the")
    assert complaints(unowned, description, defs, "the")
    assert complaints(emptied, description, defs, "the")
    assert any(
        "answers none of the" in one for one in complaints(a_third_word, description, defs, "the")
    )


def test_every_export_answers_the_committed_description() -> None:
    """Every card these tests can build writes a document the committed description accepts."""
    world = a_world()
    bare = a_card(world)
    refused = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": what_was_priced(world, "contract", None)},
        touch=Refusal(
            code="first_touch_on_a_contract",
            field="stop",
            sentence=REFUSALS["first_touch_on_a_contract"],
        ),
        ceiling=a_ceiling(
            fraction=None, taken_by=None, at=None, sentence="A ceiling needs an edge."
        ),
    )

    for card in (a_rich_card(), bare, refused, everything_ranked()):
        assert fails(card) == [], card.the_trade.ending


@given(graph=maps_with_a_contract_ending(side="yes"), seed=seeds())
@a_few
def test_a_document_over_a_map_nobody_wrote_by_hand_answers_the_description(
    graph: Graph, seed: int
) -> None:
    """The same holds on maps the test did not write: every export answers its description.

    A contract ending is built onto every drawn map rather than hoped for, so the
    priced half of a card is exercised on every example rather than on the four in
    ten that happen to have one.
    """
    world = world_of(graph, seed=seed)
    card = a_card(
        world,
        position=a_position(ADDED_ENDING, trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={
            ADDED_ENDING: what_was_priced(world, ADDED_ENDING, agreeing_quote(world, ADDED_ENDING))
        },
    )

    assert fails(card) == []


# --- What the document is, and what it carries --------------------------------


def everything_ranked() -> Card:
    """One card where both ranking rules have rows and nothing is left unranked."""
    world = a_world()
    one = pays_on(world, "contract")
    other = pays_on(world, "other-contract")
    return a_card(
        world,
        answers={
            "instrument": what_was_priced(world, "instrument", None),
            "contract": what_was_priced(
                world,
                "contract",
                quote_at(world, "contract", bid=one.lo - 0.03, offer=one.lo - 0.02),
            ),
            "other-contract": what_was_priced(
                world,
                "other-contract",
                quote_at(world, "other-contract", bid=other.lo - 0.06, offer=other.lo - 0.05),
            ),
        },
        shifts={
            "instrument": a_shift("instrument", 0.2),
            "other-instrument": a_shift("other-instrument", 0.1),
        },
    )


def test_the_document_is_legs_and_conditions_and_names_no_order() -> None:
    """A venue's combination leg is an order format, and this document does not borrow its shape."""
    written = json.loads(as_json(export_of(a_rich_card())))

    assert set(written) == THE_TOP_LEVEL
    assert written["schema"] == SCHEMA_NAME
    assert isinstance(written["legs"], list) and len(written["legs"]) == 1
    assert set(written["conditions"]) == {
        "carried_by",
        "takes_you_out",
        "watch",
        "unhedgeable",
        "tails",
        "shocks",
    }


def test_the_document_names_the_map_the_branch_and_the_seed() -> None:
    """The three things a card can be rebuilt from are stamped on the document."""
    world = a_world(seed=11)

    written = export_of(a_card(world)).map

    assert (written.base_id, written.branch_id, written.seed) == (
        world.base_id,
        world.branch_id,
        world.seed,
    )
    assert written.as_of == world.day_zero


def test_a_shock_is_written_down_with_nothing_where_a_probability_would_go() -> None:
    """The field is written and fixed at nothing, because an absent field reads as an oversight."""
    written = json.loads(as_json(export_of(a_rich_card())))

    shock = written["conditions"]["shocks"][0]
    assert "probability" in shock
    assert shock["probability"] is None
    assert shock["placed_by"] == "reader"
    description = the_committed_description()["$defs"]["ShockExported"]["properties"]["probability"]
    assert description["type"] == "null"


def test_the_document_carries_every_refusal_the_not_advice_line_and_the_execution_sentence() -> (
    None
):
    """The limits are fields. A footer is dropped by whatever reads the document next."""
    written = json.loads(as_json(export_of(a_rich_card())))

    assert tuple(written["refuses"]) == REFUSES
    assert written["not_advice"] == NOT_ADVICE
    assert "trigger is not its fill price" in written["execution"]


def test_a_leg_is_complete_on_its_own_and_the_exit_does_not_repeat_it() -> None:
    """The size and the ceiling are on the leg, so a program reading one looks nowhere else.

    And they are the card's own two, not some other number that happens to be to
    hand: the size is what the reader's risk budget implies, and the ceiling is
    the greyed one with its label.
    """
    card = a_rich_card()

    export = export_of(card)

    assert {"size", "ceiling"} <= set(Leg.model_fields)
    assert {"size", "ceiling", "implied_size"}.isdisjoint(set(RiskExit.model_fields))
    assert export.legs[0].size == card.your_exit.implied_size
    assert export.legs[0].ceiling == card.your_exit.ceiling
    assert export.legs[0].ceiling.warning
    assert export.risk_exit.entry == card.your_exit.entry
    assert export.legs[0].priced_in == card.priced_in


def test_the_same_card_writes_the_same_bytes() -> None:
    """Two runs over one card produce one document, so a difference means a difference in it."""
    card = a_rich_card()

    assert as_json(export_of(card)) == as_json(export_of(card))
    assert as_json(export_of(a_rich_card())) == as_json(export_of(a_rich_card()))


def test_a_document_reads_back_into_itself() -> None:
    """Every number written survives the round trip, so nothing is lost on the way out."""
    export = export_of(a_rich_card())

    assert Export.model_validate_json(as_json(export)) == export


# --- The page a person reads ---------------------------------------------------


def test_the_page_names_an_owner_beside_every_number() -> None:
    """There is one place a number is written out, and it cannot write one without its owner."""
    card = a_rich_card()

    page = as_markdown(card)

    missing = [one.about for one in every_figure(card) if say(one) not in page]
    assert missing == []
    assert every_figure(card)


def test_the_page_carries_the_limits_and_never_as_a_footer() -> None:
    """Every refusal is on the page in full, with the not-advice line and the execution sentence."""
    page = as_markdown(a_rich_card())

    for refusal in REFUSES:
        assert refusal in page
    assert NOT_ADVICE in page
    assert "## What this does not know" in page


def test_the_page_says_which_rule_ranked_each_list() -> None:
    """Two lists under two named rules, never one blended ranking."""
    page = as_markdown(everything_ranked())

    assert "### Ranked by the size of its edge" in page
    assert "### Ranked by the shift times the move" in page
    assert "Not ranked" not in page


def test_a_page_with_nothing_in_a_section_says_so_rather_than_leaving_it_blank() -> None:
    """An empty section with no words reads as an answer. It is not one."""
    page = as_markdown(a_card(a_world()))

    assert "Nothing has been worked out about which claims carry the effect." in page
    assert "Nothing on this map is adverse, resolves in time, and can be seen." in page
    assert "No claim on this map is both unlikely and enough to hurt." in page
    assert "Nothing on this map is ranked by this rule." in page
    assert "### Not ranked" in page


def test_a_page_says_why_a_rail_is_empty_and_what_it_left_off() -> None:
    """An empty rail without a reason reads as *nothing takes you out*, which is flattering.

    And a claim left off the rail is said out loud, because *not on the rail* and
    *never considered* are different facts.
    """
    world = a_world()
    dropped = Dropped(
        claim="contract",
        because="tells_you_nothing",
        sentence="This came on about as often where the stop went first as it did everywhere else.",
    )

    page = as_markdown(
        a_card(
            world,
            rail=a_rail(
                rows=(a_lift_row("step", 3.1),),
                dropped=(dropped,),
                too_few_draws="Fewer than 200 effective drawn worlds ended with the stop first.",
            ),
        )
    )

    assert "Fewer than 200 effective drawn worlds" in page
    assert f"Left off — contract: {dropped.sentence}" in page


def test_a_page_says_a_contract_has_no_first_touch_and_no_ceiling() -> None:
    """A contract is held to resolution, and a ceiling needs an edge. Both are said in words."""
    world = a_world()

    page = as_markdown(
        a_card(
            world,
            position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
            answers={"contract": what_was_priced(world, "contract", None, fee=0.01)},
            touch=Refusal(
                code="first_touch_on_a_contract",
                field="stop",
                sentence=REFUSALS["first_touch_on_a_contract"],
            ),
            ceiling=a_ceiling(
                fraction=None, taken_by=None, at=None, sentence="A ceiling needs an edge."
            ),
        )
    )

    assert REFUSALS["first_touch_on_a_contract"] in page
    assert "A ceiling needs an edge." in page
    assert "never size to this" in page


def test_a_page_shows_an_edge_with_the_side_it_favours_and_the_mixture_when_there_is_one() -> None:
    """The priced section names the venue, the day, the two edges and what is not led with.

    And where the reader supposed something, the four terms that explain the
    supposed reading are printed under the sentence saying they explain and never
    add up.
    """
    graph = a_card_map()
    world = world_of(graph)
    supposed = world_of(
        graph, Branch(id="yes", label="Suppose", interventions=(Do(target="step", value=True),))
    )
    otherwise = world_of(
        graph, Branch(id="no", label="Suppose not", interventions=(Do(target="step", value=False),))
    )
    pays = pays_on(world, "contract")
    offer = pays.lo - 0.01
    step = (pays.p - offer) + 0.01
    answer = priced(
        world,
        supposed,
        "contract",
        quote_at(world, "contract", bid=offer - 0.01, offer=offer, tick=step),
        fee=None,
        otherwise=otherwise,
    )

    page = as_markdown(
        a_card(
            world,
            position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
            answers={"contract": answer},
        )
    )

    assert "Leads with: buying." in page
    assert "smallest price step" in page
    assert "recorded" in page
    assert "You supposed **step**." in page
    assert "they do not add up to the unsupposed number" in page
    assert "Nobody has read this venue's fee schedule" in page


def test_a_page_leads_with_an_edge_worth_taking_and_gives_no_reason_not_to() -> None:
    """An edge wider than a price step and outside the model's own range is simply led with."""
    world = a_world()
    pays = pays_on(world, "contract")

    page = as_markdown(
        a_card(
            world,
            position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
            answers={
                "contract": what_was_priced(
                    world,
                    "contract",
                    quote_at(world, "contract", bid=pays.lo - 0.03, offer=pays.lo - 0.02),
                    fee=0.01,
                )
            },
        )
    )

    assert "Leads with: buying." in page
    assert "smallest price step" not in page
    assert "no edge at this price" not in page.lower()


def test_a_page_says_when_a_fee_and_a_cost_are_unknown() -> None:
    """A fee nobody has read is not a fee of nothing, and the page says which it is.

    Each sentence appears only where it is about something: the venue's fee on an
    ending a venue quotes, the cost of getting in and out on one naming an
    instrument. Neither page carries the other's.
    """
    world = a_world()

    an_instrument = as_markdown(a_card(world, position=a_position("instrument"), costs=None))
    a_contract = as_markdown(
        a_card(
            world,
            position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
            answers={"contract": what_was_priced(world, "contract", None)},
        )
    )

    assert "Nobody has stated what it costs to get in and out" in an_instrument
    assert "Nobody has read this venue's fee schedule" not in an_instrument
    assert "Nobody has read this venue's fee schedule" in a_contract


def test_a_number_with_a_range_says_so_and_one_without_does_not() -> None:
    """A range is the model's own statement about its number, and it travels with it."""
    card = a_card(
        a_world(),
        carried_by=(Carried(claim="step", points=0.12, share=0.7),),
        tails=(
            Tail(
                claim="step",
                likelihood=Belief(p=0.08, lo=0.04, hi=0.15, owner="model"),
                harm=9.0,
                what_could_be_done="Nothing on this map hedges it.",
            ),
        ),
    )

    ranged = say(card.tails[0].likelihood)
    plain = say(card.carried_by[0].points)

    assert "range" in ranged and "the model's" in ranged
    assert "range" not in plain and "computed" in plain
    assert ranged in as_markdown(card) and plain in as_markdown(card)


def test_a_page_carries_the_watchlist_the_unhedgeable_rows_and_the_shocks() -> None:
    """The three lists a reader acts on are on the page with their dates and their reasons."""
    page = as_markdown(a_rich_card())

    assert "### Unhedgeable" in page
    assert SOME_DAY.isoformat() in page
    assert "Iran is struck" in page
    assert "supposing something is not a statement about how likely it is" in page


def test_a_page_names_an_instrument_trade_without_a_contract() -> None:
    """An ending naming an instrument has no contract line, and the page does not invent one."""
    page = as_markdown(a_card(a_world(), position=a_position("instrument")))

    assert "long the front-month future" in page
    assert "contract None" not in page


def test_an_unhedgeable_row_that_nobody_publishes_says_so() -> None:
    """*Adverse and nobody publishes the answer* is one of the most useful sentences here."""
    world = a_world()

    page = as_markdown(
        a_card(
            world,
            unhedgeable=(
                Unhedgeable(
                    claim="step",
                    why="Nobody publishes the number this claim turns on.",
                    resolves=date(2026, 11, 1),
                    can_be_seen=False,
                ),
            ),
        )
    )

    assert "nobody publishes the answer" in page


def test_a_ceiling_that_came_out_at_a_number_says_which_side_it_is_about() -> None:
    """Buying and selling give different fractions, so the answer says which one it is."""
    page = as_markdown(a_card(a_world(), ceiling=a_ceiling(taken_by="selling")))

    assert "Worked out for selling" in page


@pytest.mark.parametrize("sample", ["built_by_hand", "weighted_forward_sample"])
def test_a_page_names_the_sample_every_share_came_from(sample: str) -> None:
    """No share read off drawn worlds is printed without saying which worlds those were."""
    world = a_world()

    page = as_markdown(
        a_card(
            world,
            touch=a_first_touch(sample=sample),  # type: ignore[arg-type]
            rail=a_rail(sample=sample),  # type: ignore[arg-type]
            market_chance_from={"step": "venue_quote"},
        )
    )

    assert "a venue's quote on that claim" in page
    assert ("weighted forward sample" in page) == (sample == "weighted_forward_sample")


def test_the_watchlist_and_shocks_reach_the_document_as_conditions() -> None:
    """The computed lists are the conditions the legs hold under, and they arrive whole."""
    export = export_of(a_rich_card())

    assert [one.claim for one in export.conditions.carried_by] == ["step"]
    assert [one.claim for one in export.conditions.watch] == ["step"]
    assert [one.claim for one in export.conditions.unhedgeable] == ["other-contract"]
    assert [one.claim for one in export.conditions.tails] == ["step"]
    assert [one.name for one in export.conditions.shocks] == ["Iran is struck"]
    assert export.conditions.takes_you_out.rows[0].claim == "step"


def test_a_watched_row_keeps_the_day_and_the_publisher_the_caller_gave_it() -> None:
    """Nothing is re-derived on the way into the document."""
    world = a_world()
    watched = Watched(
        claim="step", resolves=SOME_DAY, observed_by="a named publication", hurts_by=-0.06
    )

    export = export_of(
        a_card(world, watch=(watched,), shocks=(Shocked(name="x", change_to_the_position=-1.0),))
    )

    assert export.conditions.watch[0].resolves == watched.resolves
    assert export.conditions.watch[0].observed_by == watched.observed_by
    assert export.conditions.watch[0].hurts_by.value == watched.hurts_by
    assert export.conditions.shocks[0].probability is None


@given(bid=st.floats(min_value=0.05, max_value=0.4))
@a_few
def test_a_document_written_at_any_price_still_answers_its_description(bid: float) -> None:
    """The description holds whatever the venue happens to be showing."""
    world = a_world()
    card = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={
            "contract": what_was_priced(
                world, "contract", quote_at(world, "contract", bid=bid, offer=bid + 0.01)
            )
        },
    )

    assert fails(card) == []


# --- The fix round: the page writes a likelihood the way this product writes one ---


THE_HOUSE_RULE = (
    (0.462076, ".46"),
    (0.297995, ".30"),
    (0.193548, ".19"),
    (0.9999, ">.99"),
    (4e-07, "<.01"),
    (1.0, ">.99"),
    (0.0, "<.01"),
)
"""Every likelihood the reviewer showed the page could meet, and what the house rule prints."""


@pytest.mark.parametrize(("value", "printed"), THE_HOUSE_RULE)
def test_every_likelihood_the_page_can_meet_is_written_by_the_house_rule(
    value: float, printed: str
) -> None:
    """Two significant figures, the nought dropped, never a certainty and never scientific."""
    line = say(Figure(value=value, owner="model", about="a chance", kind="likelihood"))

    assert line == f"a chance: {printed} — the model's"


def test_a_move_keeps_its_two_figures_however_small() -> None:
    """A move of nine thousandths is a real quantity a reader acts on. It is not a likelihood.

    The rule that writes a likelihood turns anything under a hundredth into `<.01`,
    which would be a lie about an edge. A move gets its own two figures, keeps its
    sign, and is never guarded.
    """
    small = say(Figure(value=0.009, owner="computed", about="what buying is worth", kind="move"))
    against = say(
        Figure(value=-0.004, owner="computed", about="what selling is worth", kind="move")
    )

    assert small == "what buying is worth: .0090 — computed"
    assert against == "what selling is worth: -.0040 — computed"


def test_a_price_a_count_and_a_day_are_written_as_they_are() -> None:
    """A price is not a likelihood, and neither is a number of worlds or a number of days."""
    assert say(
        Figure(value=70.0, owner="reader", about="the price you entered at", kind="price")
    ) == ("the price you entered at: 70 — yours")
    assert say(Figure(value=940.0, owner="computed", about="worlds", kind="count")) == (
        "worlds: 940 — computed"
    )
    assert say(Figure(value=2.0, owner="computed", about="days", kind="days")) == (
        "days: 2 — computed"
    )


def test_the_page_writes_the_model_number_at_two_significant_figures() -> None:
    """The builder's own sample page printed `0.462076 (range 0.297995 to 0.6541)`."""
    world = a_world()
    card = a_card(
        world,
        position=a_position("contract", trades="contract", entry=0.4, stop=0.3, target=0.7),
        answers={"contract": what_was_priced(world, "contract", agreeing_quote(world, "contract"))},
    )

    page = as_markdown(card)

    model = card.priced_in.model  # type: ignore[union-attr]
    assert model.lo is not None and model.hi is not None
    band = f"{two_figures(model.lo)} to {two_figures(model.hi)}"
    assert f"the chance this claim comes true: {two_figures(model.value)} (range {band})" in page
    assert "0.462076" not in page


UNDERSTOOD = {
    "$ref",
    "anyOf",
    "oneOf",
    "const",
    "enum",
    "type",
    "required",
    "properties",
    "items",
    "minItems",
}
"""Every rule of the description language the reader above can read."""

CONSTRAINS_NOTHING = {"$defs", "title", "description", "default", "discriminator", "format"}
"""Everything in the description that a reader may pass over without missing a rule.

`format` is here because it is advisory: the reference implementation ignores it
too unless format checking is asked for, so neither reader is weaker than the
other by passing over it.
"""


def every_description(node: dict[str, Any]) -> list[dict[str, Any]]:
    """Every place in the committed file that describes a value, and nowhere else.

    Walks into the shapes named under `$defs`, the description of each key, each
    branch of a choice and a list's items — and never into a name, which is why
    a shape called `items` would not be mistaken for the rule of that name.
    """
    found = [node]
    for one in node.get("$defs", {}).values():
        found += every_description(one)
    for one in node.get("properties", {}).values():
        found += every_description(one)
    for either in ("anyOf", "oneOf"):
        for one in node.get(either, ()):
            found += every_description(one)
    if "items" in node:
        found += every_description(node["items"])
    return found


def test_the_description_states_no_rule_the_reader_cannot_read() -> None:
    """The reader passes over what it does not understand, so this fails the day one appears.

    That is the one real risk in reading a description with something smaller than
    a full implementation: the day a shape grows a lower bound, a fixed length or a
    pattern, the committed file would carry a rule nothing checks and every test
    would still pass. This test is what stops that being silent.
    """
    beyond = {
        rule
        for described in every_description(the_committed_description())
        for rule in described
        if rule not in UNDERSTOOD and rule not in CONSTRAINS_NOTHING
    }

    assert beyond == set(), (
        f"the committed description states {sorted(beyond)}, which the reader in this file "
        "passes over; teach it those rules or stop stating them"
    )


def test_a_page_says_why_a_rail_row_has_no_day_count() -> None:
    """An absence is written as a sentence, never as a day count of nothing."""
    world = a_world()
    row = a_lift_row("step", 3.1)
    without = LiftRow(**{**row.__dict__, "days_before_the_stop": None})

    page = as_markdown(a_card(world, rail=a_rail(rows=(without,))))

    assert NO_DAYS_TO_COUNT in page
    assert "the typical days between this claim coming on" not in page
