"""The worked example, run through the engine: four sentences a person can check.

The Strait of Hormuz map is the product's one complete example, and this is the
test that says it behaves the way the story reads. The user supposes the strait
reopens on the 1st of October; a strike on Iranian territory arrives the next
day; and four things follow that anybody can read aloud and disagree with:

1. The strike makes Brent-below-$68 **less** likely.
2. The strike keeps the war-risk premium **up**, which means the claim *"the
   premium falls below 0.4%"* goes **down**. The wording is the easy thing to get
   backwards, so read it before reading the assertion.
3. The strait's standing is **withdrawn** on the day the strike happens, and the
   push against it does not land until three days later. Those are two different
   days and the gap is the honest shape of the answer.
4. What already fell stays fallen: Brent **rises** between day one and day two,
   because the strike has already hit it and then the strait's own domino arrives
   on its two-day delay and pushes the other way.

**Directions, orderings and named states — never values.** The example map is a
curated one whose illustrative inputs may be tuned, so a test that pinned a
number would break every time somebody made the example more interesting, which
is the opposite of what a golden test is for. Where a number appears below it is
a wide band around a state the story depends on, and the assertion says which.
"""

from datetime import date

from katalyst.domain import World, affected_set, apply, introduced_by, propagate
from katalyst.fixtures.hormuz import FIXTURE_DATE, HORMUZ, HORMUZ_THEN_STRIKE

SEED = 20261001
"""The seed the demo uses. A world is replayable from a map, a branch and this."""


def _base_world() -> World:
    """The world with nothing supposed: the base map and the empty branch."""
    return propagate(HORMUZ, (), as_of=FIXTURE_DATE, seed=SEED)


def _strike_world() -> World:
    """The world of the branch where the strait opens and Iran is struck the next day."""
    folded = apply(HORMUZ, HORMUZ_THEN_STRIKE)
    assert not isinstance(folded, list), folded
    left_behind, fixed = folded
    return propagate(
        left_behind,
        fixed,
        as_of=FIXTURE_DATE,
        seed=SEED,
        introduced_by=introduced_by(HORMUZ_THEN_STRIKE),
    )


def test_hormuz_strike_branch_reads_the_way_the_story_reads() -> None:
    """All four sentences at once, on the shipped example at the seed the demo uses."""
    base, strike = _base_world(), _strike_world()

    # 1. The strike lowers Brent-below-$68, read on the day that claim is judged.
    assert strike.beliefs["B"].p < base.beliefs["B"].p

    # 2. The strike keeps the war-risk premium up — so C, the claim that the
    #    premium *falls*, becomes less likely. S → C is minus 2.0.
    assert strike.beliefs["C"].p < base.beliefs["C"].p

    # 3. The strait's standing is withdrawn on the 2nd; the push lands on the 5th.
    assert strike.states["H"][0] == "supposed"
    assert strike.states["H"][1:4] == ("withdrawn", "withdrawn", "withdrawn")
    assert strike.states["H"][4] == "pushed"
    assert 0.25 < strike.series["H"][2] < 0.45
    assert strike.series["H"][4] < 0.10
    assert len(strike.retractions) == 1
    only = strike.retractions[0]
    assert (only.target, only.at, only.by_link, only.by_claim) == (
        "H",
        date(2026, 10, 2),
        "S->H",
        "S",
    )

    # 4. What already fell stays fallen: B rises between day one and day two.
    assert strike.series["B"][1] < strike.series["B"][2]


def test_the_strike_lowers_brent_below_sixty_eight() -> None:
    """Sentence one on its own, so a failure says which sentence broke."""
    assert _strike_world().beliefs["B"].p < _base_world().beliefs["B"].p


def test_the_strike_keeps_the_war_risk_premium_up() -> None:
    """Sentence two on its own.

    `C` is *"Lloyd's war-risk insurance premium for Gulf transits falls below
    0.4%"*, and `S → C` is a push of minus 2.0. So "the strike keeps the premium up"
    means C goes **down**. Getting this backwards silently inverts the test, which
    is why it has a paragraph of its own.
    """
    assert _strike_world().beliefs["C"].p < _base_world().beliefs["C"].p


def test_the_straits_standing_is_withdrawn_before_the_push_lands() -> None:
    """Sentence three on its own: two different days, and the series says which is which.

    On the 1st the user's word holds and the tile shows a word rather than a
    number. On the 2nd the strike happens, so we stop taking that word — but
    `S → H` carries a three-day delay, so nothing is pushing yet and the strait
    reads its own prior again. From the 5th the push lands.
    """
    strike = _strike_world()

    assert strike.states["H"][:5] == (
        "supposed",
        "withdrawn",
        "withdrawn",
        "withdrawn",
        "pushed",
    )
    assert strike.series["H"][0] == 1.0
    assert 0.25 < strike.series["H"][1] < 0.45
    assert strike.series["H"][1] == strike.series["H"][3]
    assert strike.series["H"][4] < 0.10
    assert strike.retractions[0].at == date(2026, 10, 2)
    assert strike.retractions[0].at != date(2026, 10, 5)


def test_what_already_fell_stays_fallen() -> None:
    """Sentence four on its own: a world in which Brent only ever falls has lost the domino.

    The strike hits Brent the same day, because `S → B` has no delay. Then
    `H → B` — a trigger that fired when the strait was supposed open — arrives on
    its two-day delay and pushes back the other way, even though the strait's
    standing has already been withdrawn. That is the whole domino-and-apple
    distinction in one series.
    """
    brent = _strike_world().series["B"]

    assert brent[1] < brent[0]
    assert brent[1] < brent[2]


def test_the_edit_cannot_reach_opec_and_the_world_shows_it() -> None:
    """OPEC+ restraint is the claim the branch provably cannot move, and it does not move.

    R's only incoming arrow is `B → R`, the market feeding back on the world. A
    feedback arrow is carried as data and not worked through in this version, so
    nothing an edit does can travel along one — and R comes out byte-identical in
    the two worlds. That is the product's central promise with something to point
    at: *here is what your change provably could not reach*.
    """
    base, strike = _base_world(), _strike_world()

    for edit in HORMUZ_THEN_STRIKE.interventions:
        assert "R" not in affected_set(strike.graph, edit)
    assert base.beliefs["R"] == strike.beliefs["R"]
    assert base.series["R"] == strike.series["R"]
    assert base.states["R"] == strike.states["R"]
    # Nothing pushes on it in either world, so it reads its own prior — give or
    # take the hair by which the middle of a lopsided range sits above its point.
    restraint = next(one for one in HORMUZ.propositions if one.id == "R")
    assert abs(base.beliefs["R"].p - restraint.prior.p) < 0.02
