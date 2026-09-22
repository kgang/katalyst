"""The three routes that turn a map, a branch and what the reader typed into a thesis card.

The point of these tests is the crossing and the fetching. A card leaves the
program as JSON — every number carrying its owner, its kind and where it came
from — and has to arrive as the same card; a document has to answer the committed
description of itself; a refused form has to arrive as a list of sentences, each
naming the field the reader should look at, and never as a stack trace.

**Two maps are used and each for a reason.** The curated example, `hormuz`, is
what the walk actually opens, and every test about what a reader sees runs on it.
A second map is built here because the curated one carries two tradeable endings
and the ranking has three outcomes to show: `main`'s fixture names no contract a
committed price file holds, and the ending that names the real Polymarket market
`3501950` arrives with the engine lane's fixture edit. Until then the map below
carries that ending so the route can be shown pricing against the recorded quote.

**No number the engine computed is typed anywhere in this file.** Every assertion
is an identity, an ordering, a sign, a presence or an absence, and every venue
number is read out of the committed quote file rather than written down here. So
each of these tests would survive the engine's numbers all moving tomorrow.

These run at a **small budget** unless the test is about the budget itself: the
shipped run is two thousand versions of the map, and a card works a verdict out
for every ending that names an instrument. Nothing the routes answer changes with
the budget, only how steady a number is, and nothing here reads a number for its
own sake.
"""

import json
from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from katalyst.api.main import app
from katalyst.api.thesis_card import (
    NO_PATH_TO_RANK,
    REFUSES,
    CardRequest,
    ExitAsked,
    _built,
    _drawn_worlds,
    _every_answer,
    _the_ending,
    _the_position,
    _what_moves_the_price,
    _worth_of,
)
from katalyst.domain import (
    Belief,
    Beliefs,
    Branch,
    ContractPayoff,
    Do,
    Graph,
    Link,
    PricePayoff,
    Proposition,
    Resolution,
    Retune,
    Source,
    World,
)
from katalyst.engine import worlds as engine
from katalyst.engine.transcript import Transcript, held
from katalyst.grounding import recorded_quote
from katalyst.thesis import (
    SCHEMA_NAME,
    Card,
    Export,
    NotComparable,
    Refusal,
    as_json,
    first_touch,
    schema_json,
    walk,
)
from katalyst.thesis.edge import A_VALUE_IS_FIXED, NO_PRICE_READ
from katalyst.thesis.export import EXPORT_SCHEMA_FILE
from katalyst.thesis.position import REFUSALS

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""

SMALL: dict[str, int] = {"versions": 16, "worlds": 4}
"""Sixty-four draws of the outer and inner loops rather than sixteen thousand."""

DAY_ZERO = date(2026, 10, 1)
"""The day both maps here open their window on: the curated example's own date."""

MARKET = "3501950"
"""The Polymarket market the committed quote file holds a price for.

The venue's own question is *Strait of Hormuz traffic returns to normal by
October 31?* — the map's own hypothesis, asked by somebody who sells the answer.
"""

FOUR_ENDINGS = "four-tradeable-endings"
"""What the map built below is called while this process holds it."""

HORMUZ_PAIR = "M2"
"""The curated example's ending that names an instrument: the XLE-against-SPY pair."""

A_CONTRACTS_PRICES: dict[str, float] = {"entry": 0.5, "stop": 0.3, "target": 0.8}
"""What a reader types on the **yes** side of a contract: a price is between nothing and one.

The yes side makes money when the claim comes true, so the position is long: the
stop sits below the entry price and the target above it.
"""


def an_exit(**changed: Any) -> dict[str, Any]:
    """The exit a reader types on a short position in the pair, with anything replaced.

    Short, so the stop sits above the entry price and the target below it. Every
    number here is one this file chose, the way a reader chooses them.
    """
    return {
        "entry": 70.0,
        "stop": 73.0,
        "target": 64.0,
        "horizon": "2026-11-10",
        "risk_budget": 0.01,
        "daily_move": 1.2,
        **changed,
    }


def asked(**body: Any) -> dict[str, Any]:
    """One request for a card on the curated example's instrument ending."""
    return {
        "base_id": "hormuz",
        "seed": SEED,
        "ending": HORMUZ_PAIR,
        "exit": an_exit(),
        **SMALL,
        **body,
    }


def a_card(client: TestClient, **body: Any) -> Card:
    """Ask for a card and give back the card, failing loudly on anything else."""
    answer = client.post("/api/thesis/card", json=asked(**body))
    assert answer.status_code == 200, answer.text
    return Card.model_validate(answer.json())


# --- A second map, for the three outcomes of the ranking ---------------------


def _resolution(by: date) -> Resolution:
    """How every claim on the map below gets settled."""
    return Resolution(
        criteria="A counted threshold over a named window, as the venue states it.",
        source="The publication that actually publishes this number.",
        by=by,
    )


def _claim(
    identifier: str,
    kind: str,
    *,
    payoff: object = None,
    reason: str | None = None,
    by: date = date(2026, 11, 20),
) -> Proposition:
    """One claim on the hand-built map below."""
    unsure = Belief(p=0.35, lo=0.22, hi=0.5, owner="model")
    return Proposition(
        id=identifier,
        claim=f"The claim called {identifier} comes out true.",
        kind=kind,
        resolution=_resolution(by),
        prior=unsure,
        beliefs=Beliefs(model=unsure),
        payoff=payoff,
        not_tradeable_reason=reason,
    )


def _arrow(identifier: str, source: str, target: str) -> Link:
    """One arrow on the hand-built map, carrying a mechanism and nothing surprising."""
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


def four_endings() -> Graph:
    """A map with four tradeable endings, one for each way the ranking can go.

    A contract a committed file holds a price for; a contract no file prices; and
    two endings naming something traded, which no venue quotes on their own
    question. The fifth claim names nothing that can be bought or sold at all.
    """
    return Graph(
        id=FOUR_ENDINGS,
        hypothesis_id="start",
        propositions=(
            _claim("start", "hypothesis"),
            _claim("step", "event"),
            _claim(
                "quoted",
                "market",
                payoff=ContractPayoff(
                    venue="Polymarket",
                    contract_id=MARKET,
                    title="Strait of Hormuz traffic returns to normal by October 31?",
                    side="yes",
                ),
            ),
            _claim(
                "unquoted",
                "market",
                payoff=ContractPayoff(
                    venue="Polymarket",
                    contract_id="no-committed-file-holds-this-one",
                    title="A second question the same venue asks.",
                    side="yes",
                ),
            ),
            _claim(
                "pair",
                "market",
                payoff=PricePayoff(instrument="the fund pair", direction="short", move=0.03),
            ),
            _claim(
                "future",
                "market",
                payoff=PricePayoff(
                    instrument="the front-month future", direction="long", move=0.05
                ),
            ),
            _claim(
                "untradeable",
                "not_tradeable",
                reason="Every instrument that would express this settles after the claim resolves.",
            ),
        ),
        links=(
            _arrow("start-to-step", "start", "step"),
            _arrow("step-to-quoted", "step", "quoted"),
            _arrow("step-to-unquoted", "step", "unquoted"),
            _arrow("step-to-pair", "step", "pair"),
            _arrow("step-to-future", "step", "future"),
        ),
    )


def hold(graph: Graph) -> None:
    """Put a map into the process's own held generations, where the routes can find it.

    A map this process generated answers under the identifier it was minted with,
    for as long as the process holds it, which is the same door a reviewer's
    freshly generated map comes through.
    """
    held.remember(
        Transcript(
            generation_id=f"generated-{graph.id}",
            hypothesis="A map this test built so the ranking has every outcome to show.",
            seed=SEED,
            on=DAY_ZERO,
            mode="replay",
        ),
        graph,
    )


def on_the_built_map(client: TestClient, ending: str, **changed: Any) -> Card:
    """Ask for a card on one ending of the map above."""
    hold(four_endings())
    answer = client.post(
        "/api/thesis/card",
        json={
            "base_id": FOUR_ENDINGS,
            "seed": SEED,
            "ending": ending,
            "exit": an_exit(**changed),
            **SMALL,
        },
    )
    assert answer.status_code == 200, answer.text
    return Card.model_validate(answer.json())


# --- What the card says ------------------------------------------------------


def test_every_tradeable_ending_is_ranked_or_left_out_and_each_names_its_rule() -> None:
    """Four endings, three outcomes, and not one of them arrives without saying which.

    Two lists and never one blended number: an edge in cents and a move in per
    cent are not the same quantity and there is no honest exchange rate between
    them. So each ranked row says which of the two rules put it there, and each
    ending neither rule could rank says why instead.
    """
    with TestClient(app) as client:
        card = on_the_built_map(client, "pair")

    what_else = card.what_else
    by_edge = {one.ending: one for one in what_else.by_the_size_of_its_edge}
    by_shift = {one.ending: one for one in what_else.by_the_shift_times_the_move}
    quiet = {one.ending: one for one in what_else.not_ranked}

    named = [*by_edge, *by_shift, *quiet]
    assert sorted(named) == ["future", "pair", "quoted", "unquoted"]
    assert len(named) == len(set(named)), "an ending may stand in exactly one of the three lists"
    assert all(one.ranked_by == "the_size_of_its_edge" for one in by_edge.values())
    assert all(one.ranked_by == "the_shift_times_the_move" for one in by_shift.values())
    assert all(one.because and one.sentence for one in quiet.values())
    assert what_else.two_rules, "the card says out loud why there are two lists"


def test_the_contract_ending_names_the_recorded_quote_and_the_market_it_came_from() -> None:
    """The ending naming market 3501950 is priced against the price in the committed file.

    Recorded first and fetched second (decision record 0020): no route makes a
    fetch, so the two prices on the card are the ones the committed dated file
    holds and the day beside them is the day it was read. Both are read out of
    that file here rather than typed, so this test cannot drift from it.
    """
    recorded = recorded_quote(MARKET)
    assert recorded is not None, "the committed quote file is what this test is about"

    with TestClient(app) as client:
        card = on_the_built_map(client, "quoted", **A_CONTRACTS_PRICES)

    assert card.the_trade.venue == "Polymarket"
    assert card.the_trade.contract_id == MARKET
    assert card.the_trade.contract_side == "yes"

    priced_in = card.priced_in
    assert priced_in.kind == "priced", "a recorded price is a price, so an edge is buildable"
    assert priced_in.quote.bid.value == recorded.bid
    assert priced_in.quote.offer.value == recorded.offer
    assert priced_in.quote.bid.owner == "venue"
    assert priced_in.quote.read_on == recorded.as_of.date()
    assert priced_in.quote.venue == "Polymarket"


def test_a_contract_nothing_prices_says_so_rather_than_being_dropped() -> None:
    """*No price has been read* is a fact a reader can act on, so it is carried, not hidden."""
    with TestClient(app) as client:
        card = on_the_built_map(client, "pair")

    quiet = {one.ending: one for one in card.what_else.not_ranked}
    assert quiet["unquoted"].because == "no_edge"
    assert quiet["unquoted"].sentence == NO_PRICE_READ


def test_an_ending_naming_an_instrument_is_a_whole_trade_with_a_break_even() -> None:
    """The curated map's endings name instruments, so an instrument ending carries everything.

    A position, first touch, the rail, and a break-even of its own — **a price, not
    a likelihood**: the price at which the position is worth nothing is the
    reader's own entry price, moved by what it costs to get in and out. Nobody has
    stated those costs, so the break-even is the entry price and the card says so
    in words rather than showing a number that looks net and is not.
    """
    with TestClient(app) as client:
        card = a_card(client)

    assert card.the_trade.trades == "instrument"
    assert card.the_trade.venue is None
    priced_in = card.priced_in
    assert priced_in.kind == "not_priced"
    assert priced_in.because == "no_contract"
    break_even = priced_in.price_break_even
    assert break_even is not None
    assert break_even.kind == "price"
    assert break_even.value == card.your_exit.entry.value
    assert priced_in.costs_are_unknown, "an unknown cost is said, never assumed to be nothing"
    assert card.your_exit.stop_first is not None, "an instrument ending has a path to touch"
    assert card.takes_you_out.sample_says, "every share names the sample it was read over"


def test_a_contract_ending_refuses_first_touch_and_its_rail_says_why_it_is_empty() -> None:
    """A contract is held to its resolution: there is no path, so there is nothing to touch.

    And an empty rail with no reason reads as *nothing takes you out*, which is a
    much more flattering sentence than the truth, so the refusal is written on it.
    """
    with TestClient(app) as client:
        card = on_the_built_map(client, "quoted", **A_CONTRACTS_PRICES)

    assert card.your_exit.first_touch_refused == REFUSALS["first_touch_on_a_contract"]
    assert card.your_exit.stop_first is None
    assert card.takes_you_out.rows == ()
    assert card.takes_you_out.too_few_draws == NO_PATH_TO_RANK


def test_a_shock_the_reader_placed_carries_no_probability_anywhere() -> None:
    """They supposed it. Supposing something is not a statement about how likely it is.

    The card's shape has no field a probability could go in, and the document
    writes the field down as nothing at all — because an absent field reads as an
    oversight where a null one reads as an answer.
    """
    shock = Branch(
        id="br_a_shock",
        label="but Iran is struck",
        interventions=(Do(kind="do", target="B", value=True, at=DAY_ZERO),),
    )
    body = asked(shocks=[shock.model_dump(mode="json")])
    with TestClient(app) as client:
        answer = client.post("/api/thesis/card", json=body)
        assert answer.status_code == 200, answer.text
        document = client.post("/api/thesis/export", json=body)
        assert document.status_code == 200, document.text

    row = answer.json()["shocks"][0]
    assert row["name"] == "but Iran is struck"
    assert row["placed_by"] == "reader"
    assert "probability" not in row, "the card's shape gives a probability nowhere to go"
    assert row["says"], "the card says why there is no probability, in the reader's own terms"

    written = document.json()["conditions"]["shocks"][0]
    assert "probability" in written and written["probability"] is None


def test_the_card_carries_its_limits_as_data_and_never_as_a_footer() -> None:
    """A footer is dropped by whatever reads the card next; a field has to be read."""
    with TestClient(app) as client:
        card = a_card(client)

    assert len(card.does_not_know.refuses) > 1
    assert all(one.endswith(".") for one in card.does_not_know.refuses)
    assert card.does_not_know.not_advice
    assert card.does_not_know.execution


def test_the_card_names_the_map_the_branch_and_the_seed_it_came_from() -> None:
    """Three values rebuild it, so a card somebody read three days ago is reproducible."""
    strike = engine.example_named("hormuz")
    assert strike is not None
    branch = strike.branches[0]

    with TestClient(app) as client:
        plain = a_card(client)
        edited = a_card(client, branch=branch.model_dump(mode="json"))

    assert (plain.base_id, plain.branch_id, plain.seed) == ("hormuz", None, SEED)
    assert (edited.base_id, edited.branch_id, edited.seed) == ("hormuz", branch.id, SEED)
    assert plain.as_of == DAY_ZERO


def test_the_same_request_twice_gives_the_same_card() -> None:
    """A card is a pure function of the map, the branch, the seed and what was typed."""
    with TestClient(app) as client:
        once = client.post("/api/thesis/card", json=asked())
        twice = client.post("/api/thesis/card", json=asked())

    assert once.json() == twice.json()


# --- The document and its committed description ------------------------------


def test_the_document_answers_the_committed_description_before_it_is_returned() -> None:
    """The description is generated from the shapes and committed beside them.

    So *the document answers the committed description* is two things together:
    the committed file is exactly what these shapes produce right now, and the
    document answers those shapes. The first half is what catches a shape that
    changed while the file did not, and the route checks both before serving.
    """
    assert EXPORT_SCHEMA_FILE.read_text(encoding="utf-8") == schema_json()

    with TestClient(app) as client:
        answer = client.post("/api/thesis/export", json=asked())

    assert answer.status_code == 200, answer.text
    document = Export.model_validate(answer.json())
    assert json.loads(as_json(document)) == answer.json()


def test_the_document_is_legs_and_conditions_and_carries_its_limits() -> None:
    """Never an order format: a document shaped like one implies it could be submitted."""
    with TestClient(app) as client:
        answer = client.post("/api/thesis/export", json=asked())

    written = answer.json()
    assert written["schema"] == SCHEMA_NAME
    assert list(written["legs"]) and "conditions" in written
    assert written["refuses"] and written["not_advice"] and written["execution"]
    assert written["map"] == {
        "base_id": "hormuz",
        "branch_id": None,
        "seed": SEED,
        "as_of": DAY_ZERO.isoformat(),
    }


def test_the_page_is_markdown_and_names_an_owner_beside_every_number() -> None:
    """The page a person reads, in the same order as the panel, served as markdown."""
    with TestClient(app) as client:
        answer = client.post("/api/thesis/export/markdown", json=asked())

    assert answer.status_code == 200
    assert answer.headers["content-type"].startswith("text/markdown")
    page = answer.text
    assert page.startswith("# ")
    assert "## The trade" in page
    assert "## What this does not know" in page
    assert "computed" in page and "you typed" in page


# --- What the routes refuse --------------------------------------------------


def test_a_name_that_matches_no_stored_example_is_a_404_naming_the_ones_that_are() -> None:
    """A caller asking for something that is not here is told what is."""
    with TestClient(app) as client:
        answer = client.post("/api/thesis/card", json=asked(base_id="not-an-example"))

    assert answer.status_code == 404
    assert "hormuz" in answer.json()["detail"]


def test_a_branch_that_does_not_fit_the_map_comes_back_with_every_reason_at_once() -> None:
    """Never a server error, never a half-applied branch, never a silent repair."""
    nowhere = Branch(
        id="br_nowhere",
        label="A supposition about a claim this map does not carry",
        interventions=(Do(kind="do", target="NOPE", value=True, at=DAY_ZERO),),
    )
    with TestClient(app) as client:
        answer = client.post("/api/thesis/card", json=asked(branch=nowhere.model_dump(mode="json")))

    assert answer.status_code == 422
    reasons = answer.json()["detail"]
    assert [one["subject"] for one in reasons] == ["NOPE"]
    assert all(one["code"] and one["message"] for one in reasons)


def test_a_form_that_cannot_be_accepted_comes_back_naming_every_field_at_fault() -> None:
    """A form that reveals one mistake at a time is a form nobody finishes.

    Three rules broken at once on a short position: a stop below the entry price
    is a stop where the trade works, a target above it is one the reader is
    already past, and a horizon after the day the claim is judged is a day the
    trade cannot still be open on.
    """
    with TestClient(app) as client:
        answer = client.post(
            "/api/thesis/card",
            json=asked(exit=an_exit(stop=64.0, target=73.0, horizon="2027-01-01")),
        )

    assert answer.status_code == 422
    reasons = answer.json()["detail"]
    assert [one["code"] for one in reasons] == [
        "stop_on_the_wrong_side",
        "target_not_beyond_entry",
        "horizon_after_the_claim",
    ]
    assert [one["field"] for one in reasons] == ["stop", "target", "horizon"]
    assert [one["sentence"] for one in reasons] == [
        REFUSALS["stop_on_the_wrong_side"],
        REFUSALS["target_not_beyond_entry"],
        REFUSALS["horizon_after_the_claim"],
    ]


def test_an_ending_the_map_does_not_carry_is_refused_by_name() -> None:
    """Whatever offered this claim as tradeable offered a claim that is not here."""
    with TestClient(app) as client:
        answer = client.post("/api/thesis/card", json=asked(ending="NOT-ON-THIS-MAP"))

    assert answer.status_code == 422
    reasons = answer.json()["detail"]
    assert [one["code"] for one in reasons] == ["unknown_ending"]
    assert reasons[0]["field"] == "ending"


def test_a_claim_that_names_no_trade_is_refused_by_name() -> None:
    """The map's own starting claim carries no payoff, so there is no position to take on it."""
    with TestClient(app) as client:
        answer = client.post("/api/thesis/card", json=asked(ending="H"))

    assert answer.status_code == 422
    reasons = answer.json()["detail"]
    assert [one["code"] for one in reasons] == ["the_ending_names_no_trade"]
    assert reasons[0]["field"] == "ending"
    assert reasons[0]["sentence"] == REFUSES["the_ending_names_no_trade"]


def test_a_contract_price_outside_its_own_range_is_refused_on_the_field_at_fault() -> None:
    """A contract cannot trade outside nothing to one, and the refusal names which price."""
    with TestClient(app) as client:
        hold(four_endings())
        answer = client.post(
            "/api/thesis/card",
            json={
                "base_id": FOUR_ENDINGS,
                "seed": SEED,
                "ending": "quoted",
                # A long position on a contract, priced where no contract trades.
                "exit": an_exit(entry=2.0, stop=0.3, target=3.0),
                **SMALL,
            },
        )

    assert answer.status_code == 422
    reasons = answer.json()["detail"]
    assert {one["code"] for one in reasons} == {"price_outside_the_contract"}
    assert [one["field"] for one in reasons] == ["entry", "target"]


# --- The world an edge is read from ------------------------------------------


def test_an_edit_never_improves_what_a_venue_is_charging() -> None:
    """The edge is read from the map as it stands, whatever the reader has supposed.

    A supposition changes the question a tile answers, and a venue's price answers
    the old one. So a card built on a branch shows the same model number against
    the same quote as a card built on none — and says which branch it was built
    on, so the reader knows the map was edited.
    """
    supposing = Branch(
        id="br_supposing",
        label="Suppose the step happens",
        interventions=(Do(kind="do", target="step", value=True, at=DAY_ZERO),),
    )
    with TestClient(app) as client:
        hold(four_endings())
        plain = on_the_built_map(client, "quoted", **A_CONTRACTS_PRICES)
        answer = client.post(
            "/api/thesis/card",
            json={
                "base_id": FOUR_ENDINGS,
                "seed": SEED,
                "ending": "quoted",
                "branch": supposing.model_dump(mode="json"),
                "exit": an_exit(**A_CONTRACTS_PRICES),
                **SMALL,
            },
        )

    assert answer.status_code == 200, answer.text
    edited = Card.model_validate(answer.json())
    assert edited.branch_id == supposing.id
    assert plain.priced_in.kind == "priced" and edited.priced_in.kind == "priced"
    assert edited.priced_in.model.value == plain.priced_in.model.value
    assert edited.priced_in.buying.value == plain.priced_in.buying.value


def test_a_world_that_already_fixes_a_value_prices_nothing_at_all() -> None:
    """One conservative rule: any fixed value in the world an edge is read from refuses it.

    *Suppose this is true* and *This happened* both change the question the number
    answers, and a venue's price answers the unsupposed one. The route always
    reads its edges from the map as it stands, so this is the seam rather than the
    whole route: handed a world that already carries a fixed value, it prices
    nothing and says why for every ending at once.

    **The refusal is unreachable through the route, and deliberately so**, which is
    why this test reaches the route's own pricing helper with a world built here.
    A base map can only come from a stored example or from a map this process
    generated, and neither carries a fixed value: an assignment exists only where
    a branch has been folded. The guard inside `priced` is defence in depth
    against a future caller handing the world on screen in twice — which is the
    one mutation this test is here to catch.
    """
    supposing = Branch(
        id="br_supposing",
        label="Suppose the step happens",
        interventions=(Do(kind="do", target="step", value=True, at=DAY_ZERO),),
    )
    graph = four_endings()
    hold(graph)
    edited = engine.build_world(FOUR_ENDINGS, supposing, SEED, **SMALL)
    assert isinstance(edited, World), edited
    assert edited.assignments, "this branch is the one that fixes a value"

    answers = _every_answer(edited, edited)

    assert sorted(answers) == ["future", "pair", "quoted", "unquoted"]
    for one in answers.values():
        assert isinstance(one, NotComparable)
        assert one.reason == "conditional_world"
        assert one.sentence == A_VALUE_IS_FIXED


# --- The two faults the assembly review found --------------------------------


def test_a_horizon_outside_the_window_the_map_covers_is_refused_by_name() -> None:
    """The day the reader expects to be out has to leave at least one day to walk.

    The form cannot ask this: its own rule compares the horizon with the day the
    *claim* is judged, which is a different question. A horizon on the day the
    window opens leaves no days at all, and a date picker defaulting to today is
    the obvious way a reader reaches it — so without a guard here the paths are
    walked, `first_touch` raises, and the reader is shown a 500.
    """
    on_the_first_day = an_exit(horizon=DAY_ZERO.isoformat())
    with TestClient(app) as client:
        for route in ("card", "export", "export/markdown"):
            answer = client.post(f"/api/thesis/{route}", json=asked(exit=on_the_first_day))

            assert answer.status_code == 422, route
            reasons = answer.json()["detail"]
            assert [one["code"] for one in reasons] == ["horizon_outside_the_window"]
            assert reasons[0]["field"] == "horizon"
            assert reasons[0]["sentence"] == REFUSES["horizon_outside_the_window"]


def a_retuned_branch() -> Branch:
    """A branch that only changes how hard the step pushes the ending it is traded on.

    A retune fixes no value, so nothing on the map is cut loose — which is what
    makes it the right branch for the test below: a shock supposing the step true
    cannot wash it out, so a shocked world that has lost it is a different world
    and says so.
    """
    return Branch(
        id="br_tuned",
        label="Suppose Brent pushes the fund pair harder",
        interventions=(Retune(kind="retune", link="B->M2", strength=3.0),),
    )


def a_shock() -> Branch:
    """A supposition the reader places with the mouse: Brent falls."""
    return Branch(
        id="br_shock",
        label="but suppose Brent falls",
        interventions=(Do(kind="do", target="B", value=True, at=DAY_ZERO),),
    )


def _the_worth(branch: Branch | None) -> float:
    """What the position is worth on one branch, recomputed here from the pure functions.

    Nothing is read off the answer under test: the world, the drawn worlds, the
    paths and the first-touch shares are all worked out again here, so the number
    this file compares against is one it computed rather than one it was handed.
    """
    request = CardRequest(
        base_id="hormuz",
        seed=SEED,
        ending=HORMUZ_PAIR,
        branch=branch,
        exit=ExitAsked.model_validate(an_exit()),
        **SMALL,
    )
    world = _built("hormuz", branch, request)
    ending = _the_ending(world, HORMUZ_PAIR)
    position = _the_position(ending, request.exit)
    paths = walk(
        _drawn_worlds(world),
        _what_moves_the_price(ending, position),
        entry=position.entry,
        daily_move=position.daily_move,
        seed=SEED,
    )
    touch = first_touch(paths, position)
    assert not isinstance(touch, Refusal)
    return _worth_of(touch, paths, position)


def test_a_shock_is_placed_on_top_of_the_branch_in_force() -> None:
    """A shock supposes something *as well as* the branch, never instead of it.

    Two things follow and both are checked. The change it reports is the
    position's worth with the branch **and** the shock, less its worth with the
    branch alone — recomputed here from a branch written out with both sets of
    edits in it, so the comparison rests on nothing the route did. And a shock
    that names the branch in force as its parent is accepted rather than refused,
    because that branch is its parent by construction: it gives the same number to
    the last digit.
    """
    branch, shock = a_retuned_branch(), a_shock()
    together = Branch(
        id="br_together",
        label="Both, written out by hand",
        interventions=(*branch.interventions, *shock.interventions),
    )
    expected = _the_worth(together) - _the_worth(branch)

    body = asked(branch=branch.model_dump(mode="json"), shocks=[shock.model_dump(mode="json")])
    parented = asked(
        branch=branch.model_dump(mode="json"),
        shocks=[shock.model_copy(update={"parent": branch.id}).model_dump(mode="json")],
    )
    with TestClient(app) as client:
        answer = client.post("/api/thesis/card", json=body)
        named = client.post("/api/thesis/card", json=parented)

    assert answer.status_code == 200, answer.text
    assert named.status_code == 200, named.text
    row = answer.json()["shocks"][0]
    assert row["name"] == shock.label
    assert row["change_to_the_position"]["value"] == expected
    assert named.json()["shocks"][0] == row


# --- The three holes the mutation run found ----------------------------------


def test_the_drawn_worlds_come_from_the_map_the_reader_is_looking_at() -> None:
    """Same seed, same map, same **branch** as the world shown — the sample's one rule.

    An edit changes which worlds are drawn and when each claim comes on in them,
    so it changes how often the reader's stop is reached first. A sample drawn on
    the map with the reader's edits stripped out would answer a question nobody
    asked, and would do it silently: every other number on the card would still
    move.
    """
    supposing = Branch(
        id="br_supposing_brent",
        label="Suppose Brent falls",
        interventions=(Do(kind="do", target="B", value=True, at=DAY_ZERO),),
    )
    with TestClient(app) as client:
        plain = a_card(client)
        edited = a_card(client, branch=supposing.model_dump(mode="json"))

    assert plain.your_exit.stop_first is not None
    assert edited.your_exit.stop_first is not None
    assert plain.your_exit.stop_first.value != edited.your_exit.stop_first.value


def test_the_fee_is_unknown_and_never_quietly_nothing() -> None:
    """Nobody has read this venue's schedule, so the card says so rather than netting to zero.

    An edge quietly netted against a fee of nothing prints a number that looks net
    and is not, which is worse than no number at all.
    """
    with TestClient(app) as client:
        card = on_the_built_map(client, "quoted", **A_CONTRACTS_PRICES)

    priced_in = card.priced_in
    assert priced_in.kind == "priced"
    assert priced_in.fee is None
    assert priced_in.fee_is_unknown, "an unknown fee is said in words, beside the two edges"


def test_the_level_gap_carries_the_payoff_s_own_direction() -> None:
    """A claim pushes the instrument the way its payoff says, and the sign is the whole point.

    The level gap is the move the map states, converted against the price the
    reader entered at, signed by which side of the instrument pays when the claim
    comes true. Drop the sign and a short ending is walked as a long one: the stop
    and the target swap. Both numbers here are worked out in this test from the
    map's own stated move and the reader's own entry price.
    """
    hold(four_endings())
    # A short ending's stop sits above the entry price and its target below;
    # a long ending's the other way about. Both are the reader's own numbers.
    shorting = an_exit()
    going_long = an_exit(stop=67.0, target=76.0)

    for name, direction, typed in (("pair", -1.0, shorting), ("future", 1.0, going_long)):
        request = CardRequest(
            base_id=FOUR_ENDINGS,
            seed=SEED,
            ending=name,
            exit=ExitAsked.model_validate(typed),
            **SMALL,
        )
        ending = _the_ending(_built(FOUR_ENDINGS, None, request), name)
        payoff = ending.payoff
        assert isinstance(payoff, PricePayoff)
        position = _the_position(ending, request.exit)
        (move,) = _what_moves_the_price(ending, position)

        assert position.side == ("short" if direction < 0 else "long")

        assert move.claim == name
        assert move.move == direction * position.entry * payoff.move
        assert move.market_chance is None, "the walk reads the market's chance for itself"
        assert move.market_chance_from == "sample_share"


def test_a_risk_budget_outside_its_own_range_is_refused_in_the_form_s_own_words() -> None:
    """A reader who types a hundred instead of a hundredth is told what a risk budget is.

    The bound lives in the position form rather than on the request shape, so the
    answer is the form's own sentence beside every other fault at once, and never
    a validation error naming a field path.
    """
    with TestClient(app) as client:
        answer = client.post("/api/thesis/card", json=asked(exit=an_exit(risk_budget=100.0)))

    assert answer.status_code == 422
    reasons = answer.json()["detail"]
    assert [one["code"] for one in reasons] == ["risk_budget_out_of_range"]
    assert reasons[0]["field"] == "risk budget"
    assert reasons[0]["sentence"] == REFUSALS["risk_budget_out_of_range"]
