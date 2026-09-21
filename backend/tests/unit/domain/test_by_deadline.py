"""The new engine, end to end, behind its flag.

Decision record 0016 makes a claim's number **the chance it happens by its
deadline**: one pass works out *when* every claim happens, an exact solve answers
*whether*, and where something was reported to have happened a weighted sample of
worlds corrects the answer for the timing the news moved. This file is that whole
thing, assembled behind `engine="by_deadline"`, judged against two enumerators that
were written without seeing it.

**Not one number the engine computes is typed in here.** Every assertion is an
identity, a direction, an ordering or a named state, on a map the test builds or on
the seeded maps the oracle lane committed. An engine number moves once, at the flip,
and a test carrying one would have to move with it.

**The two enumerators, and what each proves.**

* `tests/oracles/by_summing.py` is handed the core's **own** yes/no tables, and
  multiplies and adds up the whole joint by brute force. It proves the elimination,
  the supposition surgery and the conditioning, and it is blind to a wrong table.
* `tests/oracles/by_integrating.py` is **forbidden** the core's tables. It is given
  the arrow parameters alone and enumerates the full joint of event *times*. It is
  what catches a wrong table, and it is why one oracle was never enough.
"""

import math
from datetime import date, timedelta

import numpy
import pytest

from katalyst.domain import (
    Belief,
    Beliefs,
    Branch,
    ContractPayoff,
    Do,
    Drawn,
    Graph,
    Insert,
    Link,
    Observe,
    Pin,
    Proposition,
    Resolution,
    World,
    apply,
    diff,
    forward_pass,
    introduced_by,
    propagate,
    sample_forward,
    solve,
    stated_chance_with,
    versions_of,
    window_of,
)
from katalyst.fixtures.hormuz import FIXTURE_DATE, HORMUZ, HORMUZ_THEN_STRIKE
from tests.oracles import by_integrating, by_summing, maps
from tests.oracles_adapter import a_graph_the_engine_reads, a_map_the_oracle_reads
from tests.unit.domain.test_the_engine_is_right import _arrow, _claim, _map

DAY_ZERO = date(2026, 1, 1)
"""Day zero for every map this file builds."""

SEED = 20260922
"""The one number every draw in this file comes from. Seeded, so every run agrees."""

WITHIN = 0.005
"""How far the whole engine may sit from the time-enumerating oracle, per number.

Decision record 0016's own tolerance, and it is the distance to an enumerator
**on the same grid** rather than the distance to the truth: both run twenty-four
slices of each claim's own window with an arrival taken at the middle of its slice,
so the error the grid itself carries — larger than this — cancels between them.
"""

AT_LEAST = 0.99
"""What share of the numbers compared must sit inside that distance."""

WORLDS_DRAWN = 50_000
"""How many worlds the sample draws where something was reported. Record 0016's number."""

EXACTLY = 1e-9
"""How far the elimination may sit from adding the whole joint up by hand.

Decision record 0016 calls the solve exact, and this is what exact means when two
programs add the same numbers up in a different order.
"""


# --- Small maps these tests build by hand -----------------------------------


def _at(chance: float) -> Belief:
    """One stated likelihood with no range at all: the same number at both ends."""
    return Belief(p=chance, lo=chance, hi=chance, owner="model")


def _plain(identifier: str, chance: float, days: int, kind: str = "event") -> Proposition:
    """One claim with a stated chance that no version can move, judged after so many days."""
    return Proposition(
        id=identifier,
        claim=f"The claim written down under the name {identifier}.",
        kind=kind,  # type: ignore[arg-type]
        resolution=Resolution(
            criteria="A check two readers of it would agree on.",
            source="The publication that would carry it.",
            by=DAY_ZERO + timedelta(days=days),
        ),
        prior=_at(chance),
        beliefs=Beliefs(model=_at(chance)),
        payoff=(
            ContractPayoff(
                venue="Polymarket",
                contract_id="something-tradeable",
                title="Will the claim under this name come true?",
                side="yes",
            )
            if kind == "market"
            else None
        ),
    )


def _push(
    source: str,
    target: str,
    *,
    strength: float,
    lag: float = 0.0,
    shape: str = "step",
    half_life: float | None = None,
) -> Link:
    """One arrow, with the push a person stated and the curve it follows over time."""
    return Link(
        id=f"{source}->{target}",
        source=source,
        target=target,
        mode="trigger",
        strength=strength,
        lag=lag,
        shape=shape,  # type: ignore[arg-type]
        half_life=half_life,
        rationale="The first claim changes the chance of the second, for a stated reason.",
        provenance="argued",
        reflexive=False,
    )


def _stated(graph: Graph) -> Drawn:
    """One version of a map holding exactly the numbers it states.

    Every stated range on the maps this file builds is a point, so one version is
    the map itself and the engine's answer is the map's own answer — which is what
    lets it be set beside an enumerator that was never told about versions.
    """
    own = {one.id: numpy.array([float(one.prior.p)]) for one in graph.propositions}
    return Drawn(
        versions=1,
        own_chance=own,
        with_this_cause={
            arrow.id: stated_chance_with(own[arrow.target], numpy.array([float(arrow.strength)]))
            for arrow in graph.links
        },
    )


def _worked_through(graph: Graph, pinned: dict[str, Pin], states=None) -> dict[str, float]:
    """Run the whole core over one map at one version, and give back every claim's number.

    The forward pass, the exact solve, and — where something was reported — the
    weighted sample whose correction is added to that exact answer. This is what
    `propagate(engine="by_deadline")` does, called a layer down so that a map
    carrying states can be worked through before the field that says so exists on a
    claim.
    """
    window = window_of(graph, DAY_ZERO)
    forward = forward_pass(graph, window, _stated(graph), pinned=pinned, persistence=states or {})
    exact = solve(forward, pinned)
    if not any(pin.kind == "observe" for pin in pinned.values()):
        return {one: float(row[0]) for one, row in exact.items()}
    drawn = sample_forward(
        forward,
        pinned,
        window=window,
        version=0,
        seed=SEED,
        worlds=WORLDS_DRAWN,
        exact=exact,
    )
    return {
        one: float(numpy.clip(row[0] + drawn.correction[one], 0.0, 1.0))
        for one, row in exact.items()
    }


def _by_deadline(graph: Graph, *edits: object, versions: int = 8, seed: int = SEED) -> World:
    """Fold a branch onto a map and work the numbers through with the **new** engine."""
    branch = Branch(id="branch-under-test", label="A branch a test wrote", interventions=edits)  # type: ignore[arg-type]
    folded = apply(graph, branch)
    assert not isinstance(folded, list), folded
    left_behind, fixed = folded
    return propagate(
        left_behind,
        fixed,
        as_of=DAY_ZERO,
        seed=seed,
        versions=versions,
        introduced_by=introduced_by(branch),
        engine="by_deadline",
    )


# --- The two oracles --------------------------------------------------------


def test_the_tables_agree_with_integrating_over_time() -> None:
    """The whole core, judged by an enumerator that never sees a table it built.

    **Both conditions of this comparison, in one sentence:** every map is worked
    through at twenty-four slices of each claim's own window, eight points inside
    each slice, an arrival taken at the middle of its slice, and one version whose
    stated range is a point; and the very same map is handed to the enumerator
    through `tests/oracles_adapter.py` at that same number of slices and that same
    within-slice convention, with *This happened* answered by a seeded sample of
    fifty thousand worlds. Judged at a different number of slices, or with an
    arrival taken at the end of its slice rather than the middle, the grid alone
    moves a number by six times this tolerance and the comparison would say nothing.

    **The set:** the sixteen seeded maps `tests/oracles/maps.py` hands out — the red
    team's four-claim event maps, the same skeletons with and without states, and
    the maps built to break a state — and every question the product can ask of
    each: no edit, *Suppose this is true* both ways on every claim, *This happened*
    both ways on every claim. The set is asserted below to carry a decaying impulse,
    a diamond and states, so it is adversarial by check rather than by claim.

    Nine hundred and ninety numbers in all, and at least ninety-nine in every
    hundred must sit within five thousandths of the enumerator, **per verb**. Any
    that does not is named.
    """
    drawn = maps.a_few_of_each()
    assert any(maps.has_an_impulse(one) for _name, one in drawn), (
        "the set carries no decaying impulse, so it cannot catch an arrow whose push fades"
    )
    assert any(maps.has_a_diamond(one) for _name, one in drawn), (
        "the set carries no diamond, so it cannot catch a claim reached two ways at once"
    )
    assert any(maps.has_a_state(one) for _name, one in drawn), (
        "the set carries no state, so it cannot catch a claim that comes on and stops"
    )

    missed: dict[str, list[str]] = {"no edit": [], "suppose": [], "this happened": []}
    counted = dict.fromkeys(missed, 0)
    for name, oracle_map in drawn:
        graph, states = a_graph_the_engine_reads(name, oracle_map, DAY_ZERO)
        judged_map = a_map_the_oracle_reads(graph, DAY_ZERO, states)
        ready = by_integrating.prepare(judged_map, maps.GRID)
        for asked, supposed, observed in maps.all_the_questions(sorted(oracle_map)):
            verb = "no edit" if asked == "no edit" else ("suppose" if supposed else "this happened")
            judged = by_integrating.by_integrating(
                judged_map, maps.GRID, supposed=supposed, observed=observed, ready=ready
            )
            if judged is None:
                continue
            pinned = {one: Pin(value=value, kind="do") for one, value in supposed.items()}
            pinned |= {one: Pin(value=value, kind="observe") for one, value in observed.items()}
            ours = _worked_through(graph, pinned, states)
            for who, answer in ours.items():
                counted[verb] += 1
                if abs(answer - judged[who]) > WITHIN:
                    missed[verb].append(f"{name} / {asked} / {who} by {answer - judged[who]:+.4f}")

    for verb, wrong in missed.items():
        within = 1.0 - len(wrong) / counted[verb]
        assert within >= AT_LEAST, (
            f"under *{verb}*, {len(wrong)} of {counted[verb]} numbers sat further than "
            f"{WITHIN} from the enumerator, which is {within:.2%} inside it: {wrong}"
        )


def test_the_elimination_is_exact() -> None:
    """The solve, set against adding the whole joint up by hand over the core's own tables.

    The same tables, so this says nothing about whether a table is right — that is
    the other oracle's job. What it says is that summing one claim out at a time
    over the claims that can reach it gives the number that multiplying every table
    together and adding the whole thing up gives, for every claim and under every
    question: no edit, *Suppose this is true*, and *This happened*.

    A supposition is surgery on the map rather than a patch on a finished table, so
    each one is worked through by a fresh pass with the claim pinned and the oracle
    is told the same thing; *This happened* keeps every table where it is and
    multiplies in a mask. The comparison is exact to a billionth, which is what two
    programs adding the same numbers up in a different order can manage.
    """
    graph = _map_with_a_diamond()
    window = window_of(graph, DAY_ZERO)
    asked: list[dict[str, Pin]] = [{}]
    for who in sorted(one.id for one in graph.propositions):
        asked.append({who: Pin(value=True, kind="do")})
        asked.append({who: Pin(value=False, kind="do")})
        asked.append({who: Pin(value=True, kind="observe")})
        asked.append({who: Pin(value=False, kind="observe")})

    for pinned in asked:
        forward = forward_pass(graph, window, _stated(graph), pinned=pinned)
        ours = solve(forward, pinned)
        theirs = by_summing.by_summing(
            by_summing.Tables(
                order=forward.order,
                causes=forward.causes,
                table=forward.table,
            ),
            {one: by_summing.Pin(value=pin.value, kind=pin.kind) for one, pin in pinned.items()},
        )
        for who, answer in ours.items():
            assert float(answer[0]) == pytest.approx(float(theirs[who][0]), abs=EXACTLY), (
                f"summing one claim out at a time and adding the whole joint up disagree "
                f"about {who} under {pinned or 'no edit'}"
            )


def _map_with_a_diamond() -> Graph:
    """Four claims where one reaches another both straight in and round through a third.

    A diamond is where the red team's worst cases all were, because a claim reached
    two ways at once is where an elimination order can go wrong without the answer
    looking odd. One arrow is stated below its target's own chance, so the map also
    carries an arrow that holds a claim back.
    """
    return _map(
        (
            _plain("root", 0.35, 8, kind="hypothesis"),
            _plain("left", 0.30, 20),
            _plain("right", 0.25, 22),
            _plain("end", 0.20, 40, kind="market"),
        ),
        (
            _push("root", "left", strength=1.1),
            _push("root", "right", strength=-0.8, lag=3.0),
            _push("left", "end", strength=0.9, lag=2.0, shape="impulse", half_life=6.0),
            _push("right", "end", strength=1.4, shape="ramp", lag=5.0),
        ),
        "a diamond with one arrow holding a claim back",
    )


# --- The three defects record 0016 exists to fix ----------------------------


def test_this_happened_moves_what_caused_it() -> None:
    """Learning that an effect happened raises the odds on its cause, where supposing does not.

    Record 0016's first defect, and the map is the one
    `test_the_engine_is_right.py` builds for it: two claims, one arrow, and both
    stated ranges points, so nothing can move through how the versions are counted
    and the only route left is the news travelling up the arrow.

    The second assertion is invariant INV-3, *assert is not observe*: *Suppose this
    is true* is a lever and may not move anything upstream, while *This happened* is
    news and is the one verb that may.

    The `xfail` marks on that file stay where they are; they come off in the same
    pull request that makes `by_deadline` the default.
    """
    certain = (0.3, 0.3, 0.3)
    graph = _map(
        (
            _claim("cause", kind="hypothesis", prior=certain),
            _claim("effect", kind="market", prior=certain, days=40),
        ),
        (_arrow("cause", "effect", strength=1.5),),
        "a cause and its effect",
    )

    base = _by_deadline(graph)
    learned = _by_deadline(graph, Observe(target="effect", value=True))
    levered = _by_deadline(graph, Do(target="effect", value=True))

    assert learned.beliefs["cause"].p > base.beliefs["cause"].p, (
        "learning the effect happened left its cause where it was"
    )
    assert learned.beliefs["cause"].p > levered.beliefs["cause"].p, (
        "*This happened* and *Suppose this is true* moved the cause by the same amount, "
        "so the two verbs are one behaviour"
    )
    assert levered.beliefs["cause"].p == base.beliefs["cause"].p, (
        "supposing the effect true moved its cause, which is a lever reaching upstream"
    )


def test_an_ending_moves_when_a_cause_of_it_is_supposed() -> None:
    """Supposing a cause true moves the ending it leads to, whatever the delays.

    Record 0016's second defect: today an arrow reads its source on the day that
    source's **earliest** incoming arrow lands, so a cause whose push arrives ten
    days later moves the middle of a chain and moves the ending by exactly nothing.
    Under this engine an arrow reads *when* its source happened, so the late cause
    reaches the ending like any other.
    """
    graph = _map(
        (
            _claim("early", kind="hypothesis", days=5),
            _claim("late", days=5),
            _claim("middle", days=30),
            _claim("ending", kind="market", days=40),
        ),
        (
            _arrow("early", "middle", strength=1.0, lag=0.0),
            _arrow("late", "middle", strength=2.0, lag=10.0),
            _arrow("middle", "ending", strength=1.5, lag=0.0),
        ),
        "two ways into one middle",
    )

    base = _by_deadline(graph)
    supposed = _by_deadline(graph, Do(target="late", value=True))

    assert supposed.beliefs["middle"].p > base.beliefs["middle"].p, (
        "supposing the late cause true did not even move the claim it points at, so this "
        "map is not testing what it was built to test"
    )
    assert supposed.beliefs["ending"].p > base.beliefs["ending"].p, (
        "supposing a cause of the ending true moved the middle of the chain and left the "
        "ending where it was"
    )


def test_a_supposition_survives_a_claim_nobody_believes() -> None:
    """A supposition holds against a claim the map gives one chance in a thousand.

    Record 0016's third defect. Today a supposition ends on a calendar read off the
    map's shape, and the test for which arrows oppose it reads only the sign of the
    push — so a claim nobody believes, pushing by a hundredth of a point, deletes
    the reader's own assertion. Nothing retracts itself under this engine, so the
    tile reads *Supposed* on every day and the world records no retraction at all.
    """
    graph = _map(
        (
            _claim("supposed", kind="hypothesis"),
            _claim("ending", kind="market", days=40),
        ),
        (_arrow("supposed", "ending", strength=1.2),),
        "one supposition and one ending",
    )
    nobody_believes_it = _claim("nobody", prior=(0.001, 0.0005, 0.002), days=20)
    a_whisper_against = _arrow("nobody", "supposed", strength=-0.01)

    world = _by_deadline(
        graph,
        Do(target="supposed", value=True),
        Insert(proposition=nobody_believes_it, links=(a_whisper_against,)),
    )

    assert set(world.states["supposed"]) == {"supposed"}, (
        "a claim the map gives one chance in a thousand ended the reader's own supposition: "
        f"its days read {sorted(set(world.states['supposed']))}"
    )
    assert world.retractions == (), (
        f"something was recorded as having undermined a supposition: {world.retractions}"
    )
    assert set(world.series["supposed"]) == {1.0}, (
        "a claim held true by a supposition read something other than true on some day of "
        "the window"
    )


# --- The flag, and what it must not touch -----------------------------------


def test_todays_engine_is_byte_identical_under_the_flag() -> None:
    """The arguments the new engine needs leave the old one exactly where it was.

    Three worlds: the default, the same thing with `engine="today"` written out, and
    the same thing again with both of the new engine's own arguments handed in.
    Every number of all three is the same number, bit for bit — not close — which is
    what *the new core beside the old, behind a flag, default unchanged* has to mean.
    """
    graph = _map_with_a_diamond()
    plain = propagate(graph, (), as_of=DAY_ZERO, seed=SEED, versions=64, worlds=8)
    named = propagate(graph, (), as_of=DAY_ZERO, seed=SEED, versions=64, worlds=8, engine="today")
    ignored = propagate(
        graph,
        (),
        as_of=DAY_ZERO,
        seed=SEED,
        versions=64,
        worlds=8,
        engine="today",
        slices=6,
        sampled_worlds=17,
    )
    assert named.model_dump_json() == plain.model_dump_json(), (
        "naming today's engine changed what today's engine answered"
    )
    assert ignored.model_dump_json() == plain.model_dump_json(), (
        "the by-deadline engine's own arguments reached today's engine, which ignores them"
    )


def test_a_longer_window_moves_nothing_it_cannot_reach() -> None:
    """Inserting a claim judged a year out leaves a separate piece of the map bit for bit.

    A map in two pieces that share no arrow and no cause. One insert lands in the
    second piece and carries a resolve-by day nearly a year later, which stretches
    the window and moves every day the series is drawn at.

    **Every claim is cut into slices from its own resolve-by day and from nothing
    else**, so a piece the insertion cannot reach comes out identical — not close,
    identical, on the number, on the range, and on every day of the series the two
    worlds share. This repository has been bitten once by the other arrangement,
    where a claim at one end of a map re-timed a claim at the other.
    """
    graph = _two_pieces()
    far_off = _plain("z_far", 0.25, 360)
    reaching_in = _push("z_far", "b_leaf", strength=1.1, lag=4.0)

    before = _by_deadline(graph)
    after = _by_deadline(graph, Insert(proposition=far_off, links=(reaching_in,)))

    assert after.days > before.days, (
        "the insert did not make the window longer, so this map is not testing what it was "
        "built to test"
    )
    for who in ("a_root", "a_leaf"):
        assert after.beliefs[who].model_dump() == before.beliefs[who].model_dump(), (
            f"{who} is in a piece of the map the insert has no arrow to, and its number or "
            "its range moved"
        )
        shared = set(before.series_days) & set(after.series_days)
        was = dict(zip(before.series_days, before.series[who], strict=True))
        now = dict(zip(after.series_days, after.series[who], strict=True))
        assert [was[day] for day in sorted(shared)] == [now[day] for day in sorted(shared)], (
            f"{who}'s line moved on a day both worlds draw, so the window's length re-timed "
            "a claim nothing connects to the insert"
        )


def _two_pieces() -> Graph:
    """Four claims in two pieces that share no arrow and no cause.

    Two chains standing beside one another. Nothing done to one of them can reach
    the other by any chain of arrows or any shared cause, which is what makes it the
    map locality is tested on.
    """
    return _map(
        (
            _plain("a_root", 0.4, 10, kind="hypothesis"),
            _plain("a_leaf", 0.3, 25, kind="market"),
            _plain("b_root", 0.35, 12),
            _plain("b_leaf", 0.2, 30, kind="market"),
        ),
        (_push("a_root", "a_leaf", strength=1.3), _push("b_root", "b_leaf", strength=0.7)),
        "two pieces that share nothing",
    )


def test_a_claim_cut_off_from_the_evidence_is_bit_for_bit() -> None:
    """News in one piece of a map leaves the other piece byte-identical, correction and all.

    The strictest promise in this stack. A claim joined to what was reported by no
    chain of arrows and sharing no cause with it has a factor that already adds to
    one, so the exact solve never multiplies it in at all and its answer is the
    arithmetic it would have been given no news whatever — **bit for bit, not merely
    close**.

    The sample is where that promise is easy to lose: it hands back one correction
    per claim, and a correction of a ten-thousandth on a claim nothing touched is
    still a claim that moved. So a correction is added only where the exact answer
    itself moved, and this is the test that says so — on the number, on both ends of
    the range, and on every day of the line.
    """
    graph = _two_pieces()
    untouched = _by_deadline(graph)
    reported = _by_deadline(graph, Observe(target="b_leaf", value=True))

    assert reported.beliefs["b_root"].p != untouched.beliefs["b_root"].p, (
        "the news did not even move the claim that caused it, so this map is not testing "
        "what it was built to test"
    )
    for who in ("a_root", "a_leaf"):
        assert reported.beliefs[who].model_dump() == untouched.beliefs[who].model_dump(), (
            f"{who} is in a piece of the map the news cannot reach, and it moved"
        )
        assert reported.series[who] == untouched.series[who], (
            f"{who}'s line moved on news that cannot reach it"
        )


def test_an_arrow_that_cannot_hold_a_claim_back_says_so() -> None:
    """An arrow that cannot hold its claim back as far as its number asks is named out loud.

    An arrow whose push covers only part of a claim's window cannot hold that claim
    to the number stated for it, even with the claim's rate suppressed entirely
    while the cause is on — so the claim comes out **above** the stated number. The
    reader is told which arrow it was, what it asked for and what it delivered,
    rather than being shown a number that quietly disagrees with the arrow beside it.

    The map below is built to do it: a decaying push, most of it spent within days,
    asked to hold a claim well below its own chance over a window ten times as long.
    """
    graph = _map(
        (
            _plain("brief", 0.5, 4, kind="hypothesis"),
            _plain("held_back", 0.6, 60, kind="market"),
        ),
        (_push("brief", "held_back", strength=-4.0, shape="impulse", half_life=1.0),),
        "an arrow asked for more than its push can deliver",
    )
    world = _by_deadline(graph)
    about_the_arrow = [one for one in world.warnings if "brief->held_back" in one]
    assert len(about_the_arrow) == 1, (
        f"the clamped arrow was named {len(about_the_arrow)} times, not once: {world.warnings}"
    )
    said = about_the_arrow[0]
    assert "hold that claim to" in said and "the most it can hold it to is" in said, (
        f"the warning does not say both what was asked and what was delivered: {said}"
    )

    quiet = _by_deadline(
        _map(
            (
                _plain("brief", 0.5, 4, kind="hypothesis"),
                _plain("helped", 0.2, 60, kind="market"),
            ),
            (_push("brief", "helped", strength=2.0),),
            "an arrow that only helps",
        )
    )
    assert not any("hold that claim" in one for one in quiet.warnings), (
        f"an arrow that helps was reported as having fallen short: {quiet.warnings}"
    )


def test_an_impossible_observation_answers_rather_than_dividing_by_nothing() -> None:
    """News no world on the map can produce is answered with the map, and said out loud.

    **The map that does it:** a claim judged on the very day the window starts. Its
    number is the chance it happens *by its deadline*, and it has no window to
    happen in, so the chance is nought and no world this map can produce has it
    true. Reporting that it happened leaves nothing to condition on.

    Today's engine keeps none of its worlds, reads the claims the news reaches off
    an empty set, and warns the reader loudly. This one has no worlds to keep, so it
    answers with the map's own numbers, says so in a sentence naming the claim, and
    never shows a number that is not a number. **The numbers beside the warning are
    not today's:** today reports nought for every claim the news reaches, and this
    reports what the map says with the report set aside. That difference is
    deliberate, and it is why the sentence says which numbers the reader is looking
    at.
    """
    graph = _map(
        (
            _plain("judged_at_once", 0.4, 0, kind="hypothesis"),
            _plain("ending", 0.3, 30, kind="market"),
        ),
        (_push("judged_at_once", "ending", strength=1.5),),
        "a claim judged on the day the window starts",
    )
    untouched = _by_deadline(graph)
    reported = _by_deadline(graph, Observe(target="judged_at_once", value=True))

    named = [one for one in reported.warnings if "judged_at_once" in one]
    assert len(named) == 1, (
        f"nothing told the reader the news cannot have happened: {reported.warnings}"
    )
    assert "no world left to read a number off" in named[0], named[0]
    for who, belief in reported.beliefs.items():
        assert math.isfinite(belief.p) and math.isfinite(belief.lo) and math.isfinite(belief.hi)
        assert belief.model_dump() == untouched.beliefs[who].model_dump(), (
            f"{who} moved on news no world agrees with"
        )


# --- Everything a world is read by ------------------------------------------


def test_the_worked_example_runs_and_every_reader_of_a_world_accepts_it() -> None:
    """The committed example, both branches, through the new engine and through the change list.

    **The one condition worth stating:** this runs at a handful of versions rather
    than the shipped two thousand, because the strike branch puts two arrows that
    hold one claim back on the same claim and the work those multiply out is linear
    in the versions. The engine's report says what that costs; nothing here is a
    measurement, and every assertion below is a shape, a direction or a named state.
    """
    folded = apply(HORMUZ, HORMUZ_THEN_STRIKE)
    assert not isinstance(folded, list), folded
    struck, fixed = folded

    base = propagate(HORMUZ, (), as_of=FIXTURE_DATE, seed=SEED, versions=8, engine="by_deadline")
    branch = propagate(
        struck,
        fixed,
        as_of=FIXTURE_DATE,
        seed=SEED,
        versions=8,
        introduced_by=introduced_by(HORMUZ_THEN_STRIKE),
        engine="by_deadline",
    )

    assert base.worlds == 0 and branch.worlds == 0, "a world with no inner loop said it had one"
    assert base.retractions == () and branch.retractions == ()
    assert set(base.beliefs) == {one.id for one in HORMUZ.propositions}
    assert set(base.range_shares) == set(base.beliefs)
    for who, line in base.series.items():
        assert len(line) == len(base.series_days) == len(base.states[who])
        assert list(line) == sorted(line), (
            f"{who}'s line fell, where a chance by a day can only rise"
        )
    assert set(branch.states["H"]) == {"supposed"}, branch.states["H"]
    assert set(branch.states["B"]) == {"sampled"}, branch.states["B"]

    behind = versions_of(base)
    assert set(behind.priors) == set(base.beliefs)
    assert behind.days == base.series_days
    assert behind.reweighted == frozenset()

    changed = diff(base, branch, edit_in_words=HORMUZ_THEN_STRIKE.label)
    assert not isinstance(changed, list), changed
    assert changed.claims["H"].state == "shifted", changed.claims["H"]
    assert changed.claims["S"].state == "added", changed.claims["S"]
    assert changed.summary
    for row in changed.rows:
        assert math.isfinite(row.range_width) and math.isfinite(row.peak_delta)
        assert math.isfinite(row.agreement)


def test_a_state_is_worked_through_when_a_map_says_which_claims_hold() -> None:
    """The arithmetic for a claim that holds and can stop is reached before the field exists.

    Which kind of truth a claim is becomes a field on the claim at the flip
    (decision record 0017). Until then every claim a map mints is an event, and the
    pass takes a mapping instead — which is how the oracle comparison above runs
    over maps carrying states, and how this one does.

    Three assertions, and every one is an identity or an ordering rather than a
    number. A state nothing on the map can end is **the same claim** as the event it
    was written as, bit for bit, because its stopping rate starts at nought and
    nothing adds to it. A state something can end is worth strictly less than that,
    because some of the worlds it came on in have stopped again by its deadline. And
    the same arrow bends a different rate depending on which kind of truth it points
    at — it scales an **event's** rate of happening down, and it adds to a
    **state's** rate of stopping — so the two answers are not the same answer, which
    is the whole of what decision record 0017 decides.
    """
    graph = _map(
        (
            _plain("ender", 0.5, 10, kind="hypothesis"),
            _plain("holds", 0.4, 40, kind="market"),
        ),
        (_push("ender", "holds", strength=-1.5),),
        "one claim that can stop and one thing that stops it",
    )
    lonely = _map(
        (
            _plain("ender", 0.5, 10, kind="hypothesis"),
            _plain("holds", 0.4, 40, kind="market"),
        ),
        (_push("ender", "holds", strength=0.0),),
        "one claim that can stop and nothing that stops it",
    )

    as_an_event = _worked_through(lonely, {})["holds"]
    never_ends = _worked_through(lonely, {}, {"holds": "state"})["holds"]
    assert never_ends == as_an_event, (
        "a state nothing on the map can end came out different from the same claim written "
        "as an event"
    )
    can_end = _worked_through(graph, {}, {"holds": "state"})["holds"]
    assert can_end < never_ends, (
        "a state something on the map can end was not worth less than the same state with "
        "nothing to end it"
    )
    held_back_instead = _worked_through(graph, {})["holds"]
    assert held_back_instead != can_end, (
        "the same arrow gave the same answer on an event and on a state, so the sign of an "
        "arrow is not picking which rate it bends"
    )
