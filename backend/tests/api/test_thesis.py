"""The route that turns a map, a branch and the reader's own exit into a position.

The point of these tests is the crossing, and the promises the crossing has to
keep. A position leaves the program as JSON — the reader's four numbers with an
owner on each, two first-touch shares read off worlds nobody sent, a ranked rail
of what takes them out, and a greyed ceiling — and has to arrive as the same
answer. A request the reader can fix has to arrive as a list of sentences and a
status that says whose fault it was, never as a stack trace.

**No engine number is written down here.** Every assertion is an identity, an
ordering, a state, or one answer compared with another: the three shares sum to
one, the rail is ranked, the same three inputs give the same answer, the level gap
is the map's own stated share times the price the test typed. The engine's numbers
move; nothing in this file moves with them.

These run at a **small budget** unless the test is about the budget itself — a
position builds two worlds and draws a sample, and nothing about what the route
answers changes with the budget, only how steady the numbers are.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from katalyst.api.main import app
from katalyst.api.thesis import OWNS_THE_CHANCE, REFUSES
from katalyst.domain import (
    Belief,
    Beliefs,
    Branch,
    ContractPayoff,
    Do,
    Graph,
    ImpossibleObservation,
    Link,
    Observe,
    PricePayoff,
    Proposition,
    PropositionId,
    Resolution,
)
from katalyst.engine.transcript import Transcript, held
from katalyst.fixtures import HORMUZ_THEN_STRIKE
from katalyst.thesis.card import THE_CHANCE_CAME_FROM
from katalyst.thesis.ceiling import A_CEILING_NEEDS_AN_EDGE, NEVER_SIZE_TO_THIS
from katalyst.thesis.edge import A_VALUE_IS_FIXED, NO_CONTRACT_QUOTES_IT
from katalyst.thesis.lift import THE_FLOOR
from katalyst.thesis.position import REFUSALS
from tests.thesis.test_the_readers_own_numbers import find_stops_worked_out

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""

DAY_ZERO = date(2026, 10, 1)
"""The day the stored example's window opens on, and the map this file builds too."""

SMALL: dict[str, Any] = {"versions": 16, "worlds": 4, "drawn_worlds": 4_000}
"""A small run. See this file's own note: nothing the route answers depends on it."""

STRIKE: dict[str, Any] = HORMUZ_THEN_STRIKE.model_dump(mode="json")
"""The shipped branch as the browser would send it: a whole branch, not a name."""

AN_INSTRUMENT_ENDING = "M2"
"""The stored example's ending that names something traded, whose price moves."""

A_CONTRACT_ENDING = "M1"
"""The stored example's ending that names a contract a venue asks the same question."""

THE_MAP_THIS_FILE_BUILDS = "a-map-this-test-built"
"""What the map written down below answers to, so a request can name it."""

THE_RECORDED_CONTRACT = "3501950"
"""What the map written down below answers to, so a request can name it."""


def an_exit(**over: Any) -> dict[str, Any]:
    """One filled-in form on the stored example's instrument ending.

    The four numbers are the test's own, in round figures nobody worked out, and
    every assertion below is about what the engine did with them rather than about
    the numbers themselves.

    Args:
        over: Anything to change about the request.

    Returns:
        The body to post.
    """
    body: dict[str, Any] = {
        "base_id": "hormuz",
        "seed": SEED,
        "ending": AN_INSTRUMENT_ENDING,
        "entry": 100.0,
        "stop": 103.0,
        "target": 94.0,
        "horizon": "2026-11-01",
        "risk_budget": 0.02,
        "daily_move": 1.0,
        **SMALL,
    }
    body.update(over)
    return body


def asked(**over: Any) -> Any:
    """Post one position and give back the answer, whatever the status."""
    with TestClient(app) as client:
        return client.post("/api/thesis/position", json=an_exit(**over))


def a_claim(
    name: str, *, days: int, payoff: PricePayoff | ContractPayoff | None = None, prior: float = 0.4
) -> Proposition:
    """One plain claim, judged a stated number of days after the window opens."""
    stated = Belief(p=prior, lo=max(0.01, prior - 0.1), hi=min(0.99, prior + 0.1), owner="model")
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


A_BUILT_MAP = Graph(
    id=THE_MAP_THIS_FILE_BUILDS,
    propositions=(
        a_claim("H", days=12),
        a_claim("A", days=30),
        a_claim(
            "E",
            days=40,
            payoff=PricePayoff(instrument="a widget", direction="long", move=0.05),
        ),
    ),
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
        Link(
            id="A->E",
            source="A",
            target="E",
            mode="trigger",
            strength=1.5,
            lag=0.0,
            shape="step",
            rationale="The step moves the ending, for a stated reason.",
            provenance="argued",
        ),
    ),
    hypothesis_id="H",
)
"""A map of three claims ending in something traded, so nothing here rests on the fixture."""


A_MAP_A_VENUE_PRICES = Graph(
    id="a-map-a-venue-prices",
    propositions=(
        a_claim("H", days=12),
        a_claim(
            "Q",
            days=30,
            prior=0.5,
            payoff=ContractPayoff(
                venue="Polymarket",
                contract_id=THE_RECORDED_CONTRACT,
                title="Strait of Hormuz traffic returns to normal by October 31?",
                side="yes",
            ),
        ),
    ),
    links=(
        Link(
            id="H->Q",
            source="H",
            target="Q",
            mode="trigger",
            strength=1.5,
            lag=0.0,
            shape="step",
            rationale="The first claim moves the contract's own question, for a stated reason.",
            provenance="argued",
        ),
    ),
    hypothesis_id="H",
)
"""A map whose ending names the one contract this repository has a committed price for.

The stored worked example names a contract nobody has recorded a price for, so on
it a route that reads the file and a route that never looks agree by accident.
This map is the one that tells them apart.
"""


@pytest.fixture
def the_priced_map() -> Graph:
    """Hold the map whose ending a committed quote prices, under its own name.

    Returns:
        That map.
    """
    held.remember(
        Transcript(
            generation_id="for-a-map-a-venue-prices",
            hypothesis="A map whose ending a venue prices.",
            seed=SEED,
            on=DAY_ZERO,
            mode="replay",
        ),
        A_MAP_A_VENUE_PRICES,
    )
    return A_MAP_A_VENUE_PRICES


@pytest.fixture
def the_built_map() -> Graph:
    """Hold the map this file builds for the life of one test, under its own name.

    A map this process generated answers by its identifier exactly as a stored
    example does, which is what lets a test ask about a map nobody committed.

    Returns:
        That map.
    """
    held.remember(
        Transcript(
            generation_id=f"for-{THE_MAP_THIS_FILE_BUILDS}",
            hypothesis="A map this test wrote down.",
            seed=SEED,
            on=DAY_ZERO,
            mode="replay",
        ),
        A_BUILT_MAP,
    )
    return A_BUILT_MAP


# --- What the route answers -------------------------------------------------


def test_a_position_answers_with_the_reader_s_own_numbers_and_the_engine_s_shares() -> None:
    """The four numbers come back owned by the reader; the shares come back owned by nobody else.

    The whole rule of this layer in one assertion: what the reader typed is theirs,
    what was worked out over drawn worlds says so, and the three shares of an exit
    add up to the one thing they have to add up to.
    """
    answer = asked()

    assert answer.status_code == 200
    body = answer.json()
    exit_shown = body["your_exit"]
    assert [exit_shown[one]["owner"] for one in ("entry", "stop", "target", "risk_budget")] == [
        "reader"
    ] * 4
    assert exit_shown["implied_size"]["owner"] == "reader"
    assert {exit_shown[one]["owner"] for one in ("stop_first", "target_first", "neither")} == {
        "computed"
    }
    assert sum(exit_shown[one]["value"] for one in ("stop_first", "target_first", "neither")) == (
        pytest.approx(1.0)
    )


def test_the_shares_are_read_to_the_reader_s_own_horizon_and_no_further() -> None:
    """Two shares over a window nobody named are two numbers nobody can check."""
    body = asked(horizon="2026-10-21").json()

    assert body["as_of"] == DAY_ZERO.isoformat()
    assert body["your_exit"]["through"]["value"] == (date(2026, 10, 21) - DAY_ZERO).days


def test_a_shorter_horizon_leaves_fewer_worlds_with_either_end_reached() -> None:
    """Being out sooner cannot touch a level that a longer walk would not also have touched.

    One answer against another on the same map, branch and seed, so the comparison
    is the horizon and nothing else.
    """
    sooner = asked(horizon="2026-10-16").json()["your_exit"]
    later = asked(horizon="2026-11-01").json()["your_exit"]

    assert sooner["neither"]["value"] >= later["neither"]["value"]
    assert sooner["stop_first"]["value"] <= later["stop_first"]["value"]
    assert sooner["target_first"]["value"] <= later["target_first"]["value"]


def test_the_stop_is_at_least_as_likely_as_finishing_beyond_it() -> None:
    """A level touched on day three is touched even if the price finishes above it."""
    body = asked().json()["your_exit"]

    assert body["stop_first"]["value"] + body["target_first"]["value"] <= 1.0
    assert body["stop_at"]["value"] < body["stop"]["value"], (
        "the barrier shift moves the stop toward the price you entered at"
    )
    assert body["target_at"]["value"] > body["target"]["value"]


def test_every_number_that_came_off_the_drawn_worlds_names_the_sample() -> None:
    """Under *This happened* those days rest on a weighted sample with a measured error."""
    body = asked().json()
    exit_shown = body["your_exit"]

    assert "weighted forward sample" in exit_shown["sample_says"]
    assert "weighted forward sample" in exit_shown["stop_first"]["source"]
    assert exit_shown["method"], "how the shares were arrived at is printed wherever they are"
    assert "weighted forward sample" in body["takes_you_out"]["sample_says"]


def test_the_same_map_branch_and_seed_give_the_same_answer() -> None:
    """A position is a state of the panel that can always be thrown away and rebuilt."""
    assert asked().json() == asked().json()


def test_the_answer_says_which_map_branch_and_seed_it_was_built_from() -> None:
    """Four things produce it, and all four are on it."""
    body = asked(branch=STRIKE).json()

    assert body["base_id"] == "hormuz"
    assert body["branch_id"] == HORMUZ_THEN_STRIKE.id
    assert body["seed"] == SEED
    assert body["drawn_worlds"]["value"] == SMALL["drawn_worlds"]
    assert 0.0 < body["effective_draws"]["value"] <= body["drawn_worlds"]["value"]


# --- What takes you out -----------------------------------------------------


def test_the_rail_is_ranked_from_most_company_with_losing_to_least() -> None:
    """Lift measures company in both directions, and the rail runs from one end to the other."""
    rail = asked().json()["takes_you_out"]

    lifts = [one["lift"]["value"] for one in rail["rows"]]
    assert lifts == sorted(lifts, reverse=True)
    assert lifts, "this map's rail has rows, or the rest of this test checks nothing"


def test_every_rail_row_says_what_it_rests_on_and_claims_no_coverage_for_the_ratio() -> None:
    """A lift without its interval and its count is a ratio nobody can weigh."""
    rail = asked().json()["takes_you_out"]

    for row in rail["rows"]:
        assert row["says"], "a row names its claim in words, not by identifier alone"
        assert row["lift"]["lo"] is None and row["lift"]["hi"] is None
        assert row["came_on_first"]["lo"] <= row["came_on_first"]["value"]
        assert row["came_on_first"]["value"] <= row["came_on_first"]["hi"]
        assert row["draws"]["value"] >= rail["floor"]["value"]
        assert row["coverage"]["value"] > 0.0


def test_the_floor_under_a_row_is_the_effective_count_and_is_said_out_loud() -> None:
    """Two hundred worlds of which one carries nine tenths of the weight is not two hundred."""
    rail = asked().json()["takes_you_out"]

    assert rail["floor"]["value"] == THE_FLOOR
    assert "not measured" in (rail["floor"]["source"] or "")


def test_an_empty_rail_says_why_it_is_empty() -> None:
    """An empty rail without a reason reads as *nothing takes you out*, which is flattering."""
    rail = asked(drawn_worlds=8).json()["takes_you_out"]

    assert rail["rows"] == []
    assert rail["too_few_draws"] is not None
    assert str(THE_FLOOR) in rail["too_few_draws"]


def test_a_claim_an_edit_holds_true_everywhere_is_left_off_the_rail_with_its_reason() -> None:
    """The rail is about what varies, and a supposed claim varies in no drawn world."""
    rail = asked(branch=STRIKE).json()["takes_you_out"]

    left_off = " ".join(rail["left_off"])
    assert "H:" in left_off
    assert "came on in every drawn world" in left_off


# --- What the path applied --------------------------------------------------


def test_the_path_applies_the_map_s_own_move_converted_against_the_price_you_entered_at() -> None:
    """A map states a move as a share of a price; a path takes a level gap in price units."""
    body = asked(entry=200.0, stop=206.0, target=188.0).json()
    applied = body["path_applied"]

    assert [one["claim"] for one in applied] == [AN_INSTRUMENT_ENDING]
    only = applied[0]
    assert only["level_gap"]["value"] == pytest.approx(-only["stated_move"]["value"] * 200.0), (
        "this ending's payoff is short, so its instrument stands lower where the claim is true"
    )
    assert only["stated_move"]["owner"] == "model"
    assert only["level_gap"]["owner"] == "computed"
    assert "share" in only["converted"]


def test_the_market_s_chance_says_where_it_came_from_in_the_same_breath() -> None:
    """Record 0019 requires the source beside the number, and R41 says which number it is."""
    only = asked().json()["path_applied"][0]

    assert only["came_from"] == "sample_share"
    assert only["market_chance"]["owner"] == OWNS_THE_CHANCE["sample_share"]
    assert only["market_chance"]["source"] == THE_CHANCE_CAME_FROM["sample_share"]
    assert 0.0 <= only["market_chance"]["value"] <= 1.0


def test_the_shape_the_giveback_followed_is_named_because_it_is_an_assumption() -> None:
    """Four to five points of *the stop is reached first* ride on that choice."""
    only = asked().json()["path_applied"][0]

    assert only["decay_shape"] in ("arrival_days", "straight_line", "nothing_given_back")
    assert only["decay_says"]


# --- The greyed ceiling -----------------------------------------------------


def test_the_ceiling_is_absent_with_its_reason_and_never_without_its_words() -> None:
    """Zero and absent are different answers, and neither is ever a blank."""
    ceiling = asked().json()["your_exit"]["ceiling"]

    assert ceiling["fraction"] is None
    assert ceiling["warning"] == NEVER_SIZE_TO_THIS
    assert ceiling["sentence"] == f"{A_CEILING_NEEDS_AN_EDGE} {NO_CONTRACT_QUOTES_IT}"


def test_the_ceiling_is_a_number_where_a_committed_file_prices_the_contract(
    the_priced_map: Graph,
) -> None:
    """The greyed ceiling has a reachable path to a fraction, and it is the recorded price.

    A quote is **recorded first and fetched second** (record 0020), so the route
    reads the committed file by the contract's own identifier and never dials out.
    Without that read the ceiling would be absent on every request this route can
    be given, and the feature would be unreachable rather than merely rare.

    No number is written down here: the fraction is checked for being a fraction,
    for being owned by a computation, and for carrying the words it is never shown
    without.
    """
    with TestClient(app) as client:
        answer = client.post(
            "/api/thesis/position",
            json={
                "base_id": the_priced_map.id,
                "seed": SEED,
                "ending": "Q",
                "entry": 0.5,
                "stop": 0.4,
                "target": 0.7,
                "horizon": (DAY_ZERO + timedelta(days=20)).isoformat(),
                "risk_budget": 0.05,
                "daily_move": 0.02,
                **SMALL,
            },
        )

    assert answer.status_code == 200
    ceiling = answer.json()["your_exit"]["ceiling"]
    assert ceiling["fraction"] is not None, "a ceiling that can never be a number is not a feature"
    assert 0.0 < ceiling["fraction"]["value"] < 1.0
    assert ceiling["fraction"]["owner"] == "computed"
    assert ceiling["taken_by"] in ("buying", "selling")
    assert ceiling["at"]["owner"] == "computed"
    assert ceiling["warning"] == NEVER_SIZE_TO_THIS
    assert ceiling["sentence"] is None, "a fraction came out, so there is nothing to explain"


def test_the_ceiling_is_the_absence_with_its_reason_where_no_contract_quotes_the_claim() -> None:
    """The other half of the rule: zero and absent are different answers, and neither is blank."""
    ceiling = asked().json()["your_exit"]["ceiling"]

    assert ceiling["fraction"] is None
    assert ceiling["taken_by"] is None and ceiling["at"] is None
    assert ceiling["warning"] == NEVER_SIZE_TO_THIS
    assert ceiling["sentence"] == f"{A_CEILING_NEEDS_AN_EDGE} {NO_CONTRACT_QUOTES_IT}"


def test_the_edge_behind_the_ceiling_is_read_from_the_map_with_nothing_fixed() -> None:
    """A supposed world answers a different question from a venue's price (record 0018, R20).

    The discriminating assertion: had the route priced against the world on screen,
    a branch that supposes something would come back *a value on this map has been
    fixed*. It comes back with this ending's own refusal instead, so the world the
    edge was read from is the one with nothing fixed.
    """
    ceiling = asked(branch=STRIKE).json()["your_exit"]["ceiling"]

    assert A_VALUE_IS_FIXED not in (ceiling["sentence"] or "")
    assert NO_CONTRACT_QUOTES_IT in (ceiling["sentence"] or "")


# --- A contract ending ------------------------------------------------------


def test_a_contract_ending_refuses_first_touch_by_name() -> None:
    """A probability follows no price path, so the question is refused rather than answered."""
    answer = asked(ending=A_CONTRACT_ENDING, entry=0.4, stop=0.3, target=0.6, horizon="2026-10-31")

    assert answer.status_code == 200
    body = answer.json()
    assert body["your_exit"]["first_touch_refused"] == REFUSALS["first_touch_on_a_contract"]
    assert body["your_exit"]["stop_first"] is None
    assert body["takes_you_out"] is None, "there is no first touch to rank a rail over"
    assert body["path_applied"] == []


def test_a_contract_ending_still_carries_the_reader_s_own_numbers_and_the_ceiling() -> None:
    """What it refuses is one question, not the whole answer."""
    body = asked(
        ending=A_CONTRACT_ENDING, entry=0.4, stop=0.3, target=0.6, horizon="2026-10-31"
    ).json()

    assert body["the_trade"]["trades"] == "contract"
    assert body["the_trade"]["venue"] and body["the_trade"]["contract_id"]
    assert body["your_exit"]["implied_size"]["owner"] == "reader"
    assert body["your_exit"]["ceiling"]["warning"] == NEVER_SIZE_TO_THIS


def test_a_contract_price_outside_its_own_range_is_refused_field_by_field() -> None:
    """A contract trades between nothing and one, and the refusal names the field at fault.

    The target alone is out of range here, and the refusal says so: a refusal that
    always named the entry would send the reader to a field that is perfectly good.
    """
    answer = asked(ending=A_CONTRACT_ENDING, entry=0.4, stop=0.3, target=1.4, horizon="2026-10-31")

    assert answer.status_code == 422
    assert [one["field"] for one in answer.json()["detail"]] == ["target"]
    assert answer.json()["detail"][0]["code"] == "price_outside_the_contract"


# --- What the route refuses -------------------------------------------------


def test_every_fault_on_the_form_comes_back_at_once() -> None:
    """A form that reveals one mistake at a time is a form nobody finishes."""
    answer = asked(stop=97.0, target=106.0, risk_budget=40.0)

    assert answer.status_code == 422
    faults = answer.json()["detail"]
    assert [one["code"] for one in faults] == [
        "stop_on_the_wrong_side",
        "target_not_beyond_entry",
        "risk_budget_out_of_range",
    ]
    assert [one["sentence"] for one in faults] == [REFUSALS[one["code"]] for one in faults]


def test_an_ending_that_is_not_on_the_map_is_refused_by_name() -> None:
    """A position on a claim nobody drew is a number nobody could trace."""
    answer = asked(ending="nowhere")

    assert answer.status_code == 422
    assert answer.json()["detail"] == [
        {
            "code": "unknown_ending",
            "field": "ending",
            "sentence": REFUSES["unknown_ending"],
        }
    ]


def test_an_ending_that_names_no_trade_is_refused_by_name() -> None:
    """The map's own starting claim names nothing anybody could buy or sell."""
    answer = asked(ending="H")

    assert answer.status_code == 422
    assert answer.json()["detail"][0]["code"] == "the_ending_names_no_trade"


def test_a_horizon_outside_the_map_s_window_is_refused_by_name() -> None:
    """There is no path to walk to a day the map does not cover."""
    answer = asked(horizon=DAY_ZERO.isoformat())

    assert answer.status_code == 422
    assert answer.json()["detail"][0]["code"] == "horizon_outside_the_window"
    assert answer.json()["detail"][0]["field"] == "horizon"


def test_a_horizon_after_the_claim_is_settled_is_the_form_s_own_refusal() -> None:
    """The trade cannot still be open after the thing it is about has been judged."""
    answer = asked(horizon="2026-11-20")

    assert answer.status_code == 422
    assert answer.json()["detail"][0]["code"] == "horizon_after_the_claim"


def test_a_branch_that_does_not_fit_the_map_comes_back_with_every_reason() -> None:
    """The world routes' own answer, reached by the same door and worded the same way."""
    answer = asked(
        branch=Branch(
            id="br_nonsense",
            label="An edit naming a claim nobody drew",
            interventions=(Do(target="nowhere", value=True, at=None),),
        ).model_dump(mode="json")
    )

    assert answer.status_code == 422
    assert answer.json()["detail"][0]["subject"] == "nowhere"
    assert answer.json()["detail"][0]["message"]


def test_a_name_that_matches_no_stored_example_is_a_404_naming_the_ones_there_are() -> None:
    """A caller asking for something that is not here is told what is."""
    answer = asked(base_id="not-a-map")

    assert answer.status_code == 404
    assert "hormuz" in answer.json()["detail"]


def test_a_map_nothing_agrees_with_is_a_sentence_rather_than_a_stack_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A *This happened* nothing on the map can produce leaves no world to read days off.

    The engine says so by name and this route turns it into words. The condition is
    forced here rather than drawn, because a map that contradicts its own recorded
    fact takes a likelihood of exactly nothing, which no map this program ships or
    generates states.
    """

    def nothing_agrees(*_: Any, **__: Any) -> None:
        raise ImpossibleObservation((PropositionId("B"),))

    monkeypatch.setattr("katalyst.api.thesis.engine.sample_of", nothing_agrees)

    answer = asked()

    assert answer.status_code == 422
    assert answer.json()["detail"][0]["code"] == "nothing_agrees_with_what_happened"


def test_a_run_above_the_drawn_ceiling_is_refused_rather_than_quietly_made_smaller() -> None:
    """A caller who asks for one run and silently gets another is reading the wrong numbers."""
    answer = asked(drawn_worlds=500_000)

    assert answer.status_code == 422


# --- A map this file built, and our own source ------------------------------


def test_a_position_works_on_a_map_this_test_built(the_built_map: Graph) -> None:
    """Nothing here rests on the stored example: the whole answer comes back on a map written above.

    The ending this map names is **long**, where the stored example's is short, so
    the sign the payoff carries is read rather than assumed.
    """
    with TestClient(app) as client:
        answer = client.post(
            "/api/thesis/position",
            json={
                "base_id": the_built_map.id,
                "seed": SEED,
                "ending": "E",
                "entry": 50.0,
                "stop": 47.0,
                "target": 56.0,
                "horizon": (DAY_ZERO + timedelta(days=30)).isoformat(),
                "risk_budget": 0.05,
                "daily_move": 0.5,
                **SMALL,
            },
        )

    assert answer.status_code == 200
    body = answer.json()
    assert body["the_trade"]["side"] == "long"
    assert body["the_trade"]["instrument"] == "a widget"
    only = body["path_applied"][0]
    assert only["level_gap"]["value"] == pytest.approx(only["stated_move"]["value"] * 50.0)
    assert (
        sorted(one["claim"] for one in body["takes_you_out"]["rows"])
        or (body["takes_you_out"]["left_off"])
    ), "every claim is either on the rail or left off it with a reason"


def test_a_position_on_a_branch_that_records_something_is_weighted(
    the_built_map: Graph,
) -> None:
    """*This happened* makes the drawn worlds unequally likely, and every count is weighted.

    The effective count is what every floor in the answer is measured against, and
    on a weighted sample it is strictly fewer worlds than were drawn — which is the
    whole reason `Draws` carries it.
    """
    recorded = Branch(
        id="br_recorded",
        label="A claim recorded as having happened",
        # Recorded on the **caused** claim rather than on the starting one: a claim
        # nothing on the map causes takes the same weight in every drawn world, so
        # observing it leaves the worlds equally likely and there is nothing to see.
        interventions=(Observe(target="A", value=True, at=None),),
    ).model_dump(mode="json")

    with TestClient(app) as client:
        answer = client.post(
            "/api/thesis/position",
            json={
                "base_id": the_built_map.id,
                "branch": recorded,
                "seed": SEED,
                "ending": "E",
                "entry": 50.0,
                "stop": 47.0,
                "target": 56.0,
                "horizon": (DAY_ZERO + timedelta(days=30)).isoformat(),
                "risk_budget": 0.05,
                "daily_move": 0.5,
                **SMALL,
            },
        )

    assert answer.status_code == 200
    body = answer.json()
    assert body["effective_draws"]["value"] < body["drawn_worlds"]["value"]


def test_the_route_never_works_out_a_stop_a_target_or_a_horizon() -> None:
    """The check that reads the trade layer's own source, pointed at the routes as well.

    A stop is a price the reader owns, and the promise decays into a convention
    unless something checks it. The trade layer is walked by its own test; the route
    that takes the form is walked here, because it is the one other place the three
    names appear.
    """
    routes = Path(__file__).resolve().parents[2] / "src" / "katalyst" / "api"

    # The checker reads names rather than meanings, and one other route declares a
    # field called `target`: the place a generated story is graded against reaching.
    # That is a different word wearing the same spelling, so this test is about the
    # file that takes the reader's exit.
    offenders = [one for one in find_stops_worked_out(routes) if one.file.name == "thesis.py"]

    assert not offenders, "\n".join(one.describe() for one in offenders)
    assert (routes / "thesis.py").exists(), (
        "a checker pointed at nothing passes for the wrong reason"
    )


def test_the_map_this_file_built_is_not_the_stored_example_under_another_name() -> None:
    """A test that quietly fell back to the stored example would check the fixture twice."""
    assert A_BUILT_MAP.id != "hormuz"
    assert {one.id for one in A_BUILT_MAP.propositions} == {"H", "A", "E"}
    assert A_BUILT_MAP.hypothesis_id == "H"
