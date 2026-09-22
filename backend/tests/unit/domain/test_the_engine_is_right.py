"""The three things record 0016 says today's engine gets wrong, written as tests.

Every test here is **expected to fail**, strictly, and names the row of decision
record 0016 it comes from. That is the point of the file: a defect nobody can run
is a paragraph, and a paragraph does not go red when somebody quietly reintroduces
it. Each one fails today, each one passes the day record 0016's new core becomes
the default, and the marks come off in the same pull request that makes them pass.

**What a claim's number means, before and after.** Today a claim's number is a
likelihood read on one day. Record 0016 makes it *the chance the claim comes out
true by its own deadline* — which is what every tile on screen already says
underneath it — solves whether each claim happens exactly, and samples when it
happens. The three defects below all fall out of the difference.

1. **Telling the map something happened never reaches what caused it**, and the
   two verbs — *Suppose this is true* and *This happened* — come out as one
   behaviour. Record 0016's defect row 1.
2. **The tradeable endings are deaf to half their causes**, because an arrow
   reads its source on the day that source's *earliest* incoming arrow lands.
   Defect row 2.
3. **A claim nobody believes deletes the reader's own supposition.** Defect row 3.

**Not one number is typed in here.** Every assertion is a direction, an ordering
or a named state, on a map the test builds from stated inputs. An engine number
moves once, at the flip, and a test carrying one would have to move with it.
"""

from datetime import date, timedelta

import pytest

from katalyst.domain import (
    Belief,
    Beliefs,
    Branch,
    ContractPayoff,
    Do,
    Graph,
    Insert,
    Link,
    Observe,
    Proposition,
    Resolution,
    World,
    apply,
    introduced_by,
    propagate,
)

DAY_ZERO = date(2026, 1, 1)
"""Day zero for the maps below, which carry resolve-by dates from 2026 onwards."""

SEED = 20261001
"""The seed the worked example's demo uses, so a test and a screenshot agree."""

BUDGET = {"versions": 2_000, "worlds": 8}
"""The shipped budget.

These tests are about which way a number moves rather than how steady it is, and
they would hold at any budget — but a direction read off sixty-four draws can be
read off the dice instead of off the map, and there are only four of these maps,
so they are run at what the product runs at.
"""


# --- Small maps these tests build by hand -----------------------------------


def _claim(
    identifier: str,
    kind: str = "event",
    prior: tuple[float, float, float] = (0.3, 0.2, 0.45),
    days: int = 30,
) -> Proposition:
    """One plain claim: what it says, when it is judged, and how likely it is thought.

    The three numbers are the stated likelihood and the two ends of its stated
    range, in that order. They are inputs, the way a person's own number is an
    input; nothing here is read off an engine.
    """
    middle, low, high = prior
    belief = Belief(p=middle, lo=low, hi=high, owner="model")
    return Proposition(
        id=identifier,
        claim=f"The claim written down under the name {identifier}.",
        kind=kind,  # type: ignore[arg-type]
        resolution=Resolution(
            criteria="A check two readers of it would agree on.",
            source="The publication that would carry it.",
            by=DAY_ZERO + timedelta(days=days),
        ),
        prior=belief,
        beliefs=Beliefs(model=belief),
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


def _arrow(source: str, target: str, *, strength: float = 1.0, lag: float = 0.0) -> Link:
    """One plain arrow: how hard it pushes, and how many days pass before it does."""
    return Link(
        id=f"{source}->{target}",
        source=source,
        target=target,
        mode="trigger",
        strength=strength,
        lag=lag,
        shape="step",
        half_life=None,
        rationale="The first claim makes the second one more likely, for a stated reason.",
        provenance="argued",
        reflexive=False,
    )


def _map(claims: tuple[Proposition, ...], arrows: tuple[Link, ...], identifier: str) -> Graph:
    """A whole small map, with the first claim as the one it started from."""
    return Graph(id=identifier, propositions=claims, links=arrows, hypothesis_id=claims[0].id)


def _folded(graph: Graph, *edits: object) -> World:
    """Fold a branch onto a map and work the numbers through, in one line."""
    branch = Branch(id="branch-under-test", label="A branch a test wrote", interventions=edits)  # type: ignore[arg-type]
    result = apply(graph, branch)
    assert not isinstance(result, list), result
    left_behind, fixed = result
    return propagate(
        left_behind,
        fixed,
        as_of=DAY_ZERO,
        seed=SEED,
        introduced_by=introduced_by(branch),
        # THE ONE LINE THE FLIP TOUCHES IN THIS FILE. `propagate` already takes
        # an `engine` argument and it already defaults to `"today"`; these tests
        # take that default on purpose and name no engine at all, so they pass
        # unchanged the day the default becomes `"by_deadline"` and the three
        # `xfail` marks come off in that same pull request. To run them against
        # the new core before then, add `engine="by_deadline"` here and nowhere
        # else in this file.
        **BUDGET,
    )


# --- Record 0016, defect 1 --------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Record 0016, defect 1: telling the map something happened never reaches what "
        "caused it. Each claim's worked-out likelihood is kept and the coin flip thrown "
        "away, so for a claim whose versions all agree, discarding worlds cannot move it "
        "— and *Suppose this is true* and *This happened* come out as one behaviour."
    ),
)
def test_this_happened_moves_what_caused_it() -> None:
    """Learning that an effect happened has to raise the odds on its cause.

    The map is two claims and one arrow: the cause makes the effect more likely.
    Both stated ranges are **points** — the same number at both ends — so every
    version of the map draws the same prior and nothing can move through how the
    versions are counted. Then the only thing that can move the cause is the news
    itself, travelling back up the arrow, which is what *This happened* is for.

    Two assertions, and the second is invariant INV-3, *assert is not observe*:
    *Suppose this is true* is a lever and may not move anything upstream, while
    *This happened* is news and is the one verb that may.
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

    base = _folded(graph)
    learned = _folded(graph, Observe(target="effect", value=True))
    levered = _folded(graph, Do(target="effect", value=True))

    assert learned.beliefs["cause"].p > base.beliefs["cause"].p, (
        "learning the effect happened left its cause exactly where it was: "
        f"{base.beliefs['cause'].p} before, {learned.beliefs['cause'].p} after"
    )
    assert learned.beliefs["cause"].p > levered.beliefs["cause"].p, (
        "*This happened* and *Suppose this is true* moved the cause by the same amount, "
        "so the two verbs are one behaviour: "
        f"{learned.beliefs['cause'].p} against {levered.beliefs['cause'].p}"
    )


# --- Record 0016, defect 2 --------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Record 0016, defect 2: the tradeable endings are deaf to half their causes. An "
        "arrow reads its source on the day that source's EARLIEST incoming arrow lands — "
        "one integer doing two jobs — so a cause whose push arrives later moves the "
        "middle of the chain and moves the ending by exactly nothing."
    ),
)
def test_an_ending_moves_when_a_cause_of_it_is_supposed() -> None:
    """Supposing a cause true has to move the ending it leads to, whatever the delays.

    The map is a chain with two ways into its middle: one push that lands at once,
    and one that lands ten days later. The middle then pushes the ending. Supposing
    the **late** cause true plainly raises the middle — the first assertion checks
    that much, and it holds today — so it must raise the ending too, because the
    ending's only route to anything is through the middle.

    Today it does not, and the reason is the delay: the arrow out of the middle
    reads the middle on the day the middle's *earliest* incoming arrow lands, which
    is day zero, and on day zero the late cause's push has not arrived. An ending
    that cannot hear half of what moves it is a thesis card resting on nothing,
    which is why this is the defect record 0016 says has no repair inside today's
    engine.
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

    base = _folded(graph)
    supposed = _folded(graph, Do(target="late", value=True))

    assert supposed.beliefs["middle"].p > base.beliefs["middle"].p, (
        "supposing the late cause true did not even move the claim it points at, so this "
        "map is not testing what it was built to test"
    )
    assert supposed.beliefs["ending"].p > base.beliefs["ending"].p, (
        "supposing a cause of the ending true moved the middle of the chain and left the "
        "ending exactly where it was: "
        f"{base.beliefs['ending'].p} before, {supposed.beliefs['ending'].p} after"
    )


# --- Record 0016, defect 3 --------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Record 0016, defect 3: a claim nobody believes deletes the reader's own "
        "assertion. A supposition ends on a calendar read off the map's shape, and the "
        "test for which arrows oppose it reads only the sign of the push — so neither "
        "the opposing claim's likelihood nor the size of its push ever enters."
    ),
)
def test_a_supposition_survives_a_claim_nobody_believes() -> None:
    """Supposing a claim true has to survive a claim the map gives no credence to.

    Suppose a claim true, then add the weakest thing a map can hold: a claim the
    model gives one chance in a thousand, pushing against the supposition with an
    arrow a hundredth of a point strong. The supposition must still read
    *Supposed* on every day of the window, because what the reader typed is a hard
    fact in every world while it holds, and nothing on this map is remotely strong
    enough to be an argument against it.

    Today the tile reads *Supposed* on no day at all. The assertions are named
    states and an empty list — never a number — so they read the same before and
    after record 0016 deletes the calendar that causes this.
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

    world = _folded(
        graph,
        Do(target="supposed", value=True),
        Insert(proposition=nobody_believes_it, links=(a_whisper_against,)),
    )

    days = world.states["supposed"]
    assert set(days) == {"supposed"}, (
        "a claim the map gives one chance in a thousand ended the reader's own "
        f"supposition: its days read {sorted(set(days))}"
    )
    assert world.retractions == (), (
        "a claim nobody believes was recorded as having undermined a supposition: "
        f"{world.retractions}"
    )
