"""The worked example, run through the engine: the sentences the story rests on.

The Strait of Hormuz map is the product's one complete example, and this is the
test that says it behaves the way the story reads. The user supposes traffic
through the strait comes back on the 1st of October; a strike on Iranian
territory arrives the next day; and the answer has a shape anybody can read
aloud and disagree with:

1. **Both events still stand.** Traffic came back and Iran was struck. Neither of
   those un-happens, nothing is withdrawn, and the world carries no retraction —
   there is no longer any machinery that could produce one.
2. **What falls is the state**, *the strait stays open to commercial transit
   through 1 November*, and with it every claim that state was holding up: the
   war-risk premium stops being low, and the oil price stops falling.
3. **A claim nobody believes cannot end a supposition.** Insert a claim at a
   thousandth with a weak arrow pushing against something the user supposed, and
   the supposed claim stays exactly where the user put it.
4. **A state with nothing that can end it is an event**, in the arithmetic as
   well as in the words: on the base map, where the strike does not exist, the
   two states come out byte-identical to the same claims written as events.
5. **Every claim says which kind of truth it is**, and a map that leaves it out
   is refused by name rather than given a kind we guessed.

Those five are the confirmations decision record 0017 names — *a claim is an
event or a state; nothing retracts itself*. Three more sit beside them: the map
the story runs on breaks no rule; the ending that names a real contract names the
one the committed quote file holds; and every ending the edit can reach still
earns a row on the change list.

**Directions, orderings and named states — never values.** The example map is a
curated one whose illustrative inputs may be tuned, so a test that pinned a
number would break every time somebody made the example more interesting, which
is the opposite of what this test is for. Not one number the engine computes is
written down here.
"""

from katalyst.domain import (
    Belief,
    Beliefs,
    Branch,
    Do,
    Graph,
    Insert,
    Link,
    Proposition,
    Resolution,
    World,
    apply,
    diff,
    introduced_by,
    propagate,
    validate,
)
from katalyst.fixtures.hormuz import (
    FIXTURE_DATE,
    HORMUZ,
    HORMUZ_THEN_STRIKE,
    TRAFFIC_CONTRACT,
    _checked,
    _resolve_by,
)
from katalyst.grounding.recorded import recorded_quote

SEED = 20261001
"""The seed the demo uses. A world is replayable from a map, a branch and this."""

THE_TWO_EVENTS = ("H", "S")
"""The strait's traffic coming back, and the strike. Both supposed; both stand."""

THE_STATE = "O"
"""*The strait stays open to commercial transit through 1 November* — what falls."""

WHAT_THE_STATE_HOLDS_UP = ("C", "B")
"""The war-risk premium, and the oil price it reaches. Both come down with the state."""


def _world_of(branch: Branch | None) -> World:
    """Work the example through the engine, with a branch's edits or with none.

    Args:
        branch: The branch whose edits to apply, or None for the untouched map.

    Returns:
        The world the engine computes.
    """
    if branch is None:
        return propagate(HORMUZ, (), as_of=FIXTURE_DATE, seed=SEED)
    folded = apply(HORMUZ, branch)
    assert not isinstance(folded, list), folded
    left_behind, fixed = folded
    return propagate(
        left_behind,
        fixed,
        as_of=FIXTURE_DATE,
        seed=SEED,
        introduced_by=introduced_by(branch),
    )


def _base_world() -> World:
    """The world with nothing supposed: the base map and no edits."""
    return _world_of(None)


def _strike_world() -> World:
    """The world of the branch where the strait opens and Iran is struck the next day."""
    return _world_of(HORMUZ_THEN_STRIKE)


def test_both_events_stand_through_the_strike() -> None:
    """Neither the reopening nor the strike un-happens, and nothing is retracted.

    This is the sentence the whole record turns on. The old engine answered this
    branch by *withdrawing* the strait's reopening on a date it worked out from
    the map's own shape — a claim the user had typed, deleted by a cause nobody
    had asserted. That machinery is gone. Both events are supposed, both are
    true, and they stay true on every day of the window.
    """
    strike = _strike_world()

    for event in THE_TWO_EVENTS:
        assert strike.beliefs[event].p == 1.0
        assert set(strike.series[event]) == {1.0}
        assert set(strike.states[event]) == {"supposed"}

    # There is no retraction, because there is no longer anything that could
    # produce one. The field is kept, empty, until the browser stops reading it.
    assert strike.retractions == ()


def test_the_state_is_what_falls() -> None:
    """The state comes down, and so does everything it was holding up.

    Read against the **base** world rather than against the world where only the
    reopening was supposed, because that is the honest claim: after a confirmed
    strike, the lane staying open through 1 November is less likely than it was
    before anybody knew anything either way. The strike world carries the
    reopening as well, which pushes this claim hard the other way, so the
    assertion is a real one and not arithmetic that could not fail.
    """
    base, strike = _base_world(), _strike_world()

    assert strike.beliefs[THE_STATE].p < base.beliefs[THE_STATE].p
    for held_up in WHAT_THE_STATE_HOLDS_UP:
        assert strike.beliefs[held_up].p < base.beliefs[held_up].p

    # And the two events it sits between did not move down with it — that is the
    # distinction this example exists to draw.
    for event in THE_TWO_EVENTS:
        assert strike.beliefs[event].p > base.beliefs.get(event, base.beliefs["H"]).p


def test_a_supposition_is_not_ended_by_a_cause_nobody_believes() -> None:
    """A claim at a thousandth, pushing against a supposition, leaves it exactly where it was.

    The defect this replaces: a supposition used to stop holding on the day the
    cause of the first live arrow pushing against it became true — whatever that
    cause's own likelihood was. So inserting something nobody believes could
    delete what the user had typed. Supposing a claim now pins it and cuts the
    arrows into it, and there is no calendar left to get wrong.
    """
    nobody_believes_it = Proposition(
        id="X",
        claim="An unsourced rumour of a second closure circulates.",
        kind="event",
        persistence="event",
        resolution=Resolution(
            criteria="Two newswires report the rumour without attributing it to a source.",
            source="The AP and Reuters newswires.",
            by=_resolve_by(5),
        ),
        prior=Belief(p=0.001, lo=0.001, hi=0.001, owner="model"),
        beliefs=Beliefs(model=Belief(p=0.001, lo=0.001, hi=0.001, owner="model")),
    )
    pushing_back = Link(
        id="X->H",
        source="X",
        target="H",
        mode="trigger",
        strength=-0.3,
        lag=1.0,
        shape="step",
        rationale="A rumour of a second closure would cut against traffic having come back.",
        provenance="asserted",
    )
    rumour_after_the_supposition = Branch(
        id="br_rumour_after_the_supposition",
        label="Hormuz opens, then an unsourced rumour",
        parent=None,
        interventions=(
            Do(target="H", value=True, at=FIXTURE_DATE),
            Insert(proposition=nobody_believes_it, links=(pushing_back,)),
        ),
    )

    supposed = _world_of(rumour_after_the_supposition)

    assert supposed.beliefs["H"].p == 1.0
    assert set(supposed.series["H"]) == {1.0}
    assert set(supposed.states["H"]) == {"supposed"}
    assert supposed.retractions == ()


def test_a_state_with_nothing_to_end_it_is_an_event() -> None:
    """On the base map the two states come out byte-identical to the same claims as events.

    A state's rate of stopping starts at zero and is the sum of its ending
    causes. On the base map the strike does not exist, so nothing can end either
    state, so neither of them can stop — which is exactly what an event is. The
    assertion is equality, not closeness: the arithmetic is the same arithmetic,
    not an approximation of it.

    It is made about the two state claims' own numbers — the one each tile reads,
    on that claim's own resolve-by day. Two things nearby are *not* asserted,
    both for the same reason and neither of them about states: a claim further
    down the map, and the day-by-day series, are each built by a later pass whose
    additions happen in a different order, so their last bit can move. A test
    that demanded byte-identity there would be testing floating-point addition.
    """
    states = tuple(one.id for one in HORMUZ.propositions if one.persistence == "state")
    assert states, "the example has no state claim, so this test would prove nothing"

    written_as_events = HORMUZ.model_copy(
        update={
            "propositions": tuple(
                one.model_copy(update={"persistence": "event"}) if one.id in states else one
                for one in HORMUZ.propositions
            )
        }
    )
    as_states = _base_world()
    as_events = propagate(written_as_events, (), as_of=FIXTURE_DATE, seed=SEED)

    for claim in states:
        assert as_states.beliefs[claim].p == as_events.beliefs[claim].p


def test_a_claim_says_which_kind_of_truth_it_is() -> None:
    """Every claim in the example says which kind it is, both kinds appear, and a gap is refused.

    There is no default. A claim marked an event that is really a state simply
    never stops holding, silently, and the only signal would be somebody reading
    the sentence — so a map that does not say is refused by name rather than
    given a kind we guessed.
    """
    on_the_branch = [
        edit.proposition for edit in HORMUZ_THEN_STRIKE.interventions if isinstance(edit, Insert)
    ]
    every_claim = [*HORMUZ.propositions, *on_the_branch]

    assert {one.persistence for one in every_claim} == {"event", "state"}

    without_it = Proposition.model_construct(
        **{
            name: value
            for name, value in HORMUZ.propositions[0].__dict__.items()
            if name != "persistence"
        }
    )
    silent = Graph.model_construct(
        **{**HORMUZ.__dict__, "propositions": (without_it, *HORMUZ.propositions[1:])}
    )

    refused = validate(silent)

    assert [one.code for one in refused] == ["claim_without_persistence"]
    assert refused[0].subject == HORMUZ.propositions[0].id


def test_the_story_runs_on_a_map_that_breaks_no_rule() -> None:
    """The base map and the map the branch leaves behind both pass every check.

    The base map is checked the moment the example is read, so this half is the
    guard doing its job out loud. The folded map is the one the story actually
    runs on, and nothing else checks it: a branch that left behind a map the
    rules reject would still produce a world, and the world would be wrong with
    nothing to say why.
    """
    assert validate(HORMUZ) == []
    assert _checked(HORMUZ) is HORMUZ

    folded = apply(HORMUZ, HORMUZ_THEN_STRIKE)
    assert not isinstance(folded, list), folded
    left_behind, _ = folded

    assert validate(left_behind) == []


def test_the_market_ending_names_the_contract_the_quote_file_names() -> None:
    """The one real contract on the map is the one the committed quote file holds.

    The fixture names a venue, a market identifier and a side, and nothing else:
    the on-chain condition identifier, both outcome-token identifiers, the
    venue's own rules and its best bid and offer live in the committed file, and
    a copy of them in the fixture would drift the day the file was refreshed.
    What keeps the two ends together is this check rather than a comment.
    """
    payoff = TRAFFIC_CONTRACT.payoff
    assert payoff is not None
    assert payoff.kind == "contract"

    quote = recorded_quote(payoff.contract_id)

    assert quote is not None, f"nothing recorded for market {payoff.contract_id}"
    assert quote.market_id == payoff.contract_id
    assert quote.side == payoff.side
    assert quote.venue is not None and quote.venue.lower() == payoff.venue.lower()
    # The contract and the claim ask the same question, which is the whole reason
    # a model number and a venue's price may be set beside each other at all.
    assert quote.question == payoff.title
    assert quote.ends == TRAFFIC_CONTRACT.resolution.by
    # No price is typed into the map. The market's voice on this claim is built
    # from the file, by the layer that owns prices.
    assert TRAFFIC_CONTRACT.beliefs.market is None


def test_every_ending_the_edit_can_reach_has_a_change_list_row() -> None:
    """Each ending the strike can reach earns a row; the one it cannot reach says so.

    The change list is the product's answer to "what did my edit do?", and an
    ending that moved but is missing from it is worse than a wrong number,
    because the reader has no way to know it is missing. The one claim the edit
    provably cannot reach is OPEC+ restraint: its only incoming arrow is the
    feedback arrow out of Brent, which is carried as data rather than worked
    through, so nothing an edit does can travel along it.
    """
    base, strike = _base_world(), _strike_world()

    changes = diff(base, strike, edit_in_words="Hormuz opens, then Iran is struck")
    assert not isinstance(changes, list), changes

    endings = {one.id for one in HORMUZ.propositions if one.kind in ("market", "not_tradeable")}
    reachable = {one for one in endings if changes.claims[one].state == "shifted"}

    assert reachable == endings
    assert {row.target for row in changes.rows} == endings

    assert changes.claims["R"].state == "unchanged"
    assert base.beliefs["R"] == strike.beliefs["R"]
