"""Random maps, edits and likelihoods for the property tests.

A property test states something that should be true of *every* map — "a map we
built correctly has nothing wrong with it", "breaking exactly this rule produces
exactly this complaint" — and then checks it against hundreds of maps nobody
wrote by hand. The library underneath is `hypothesis`, which generates the inputs
and, when one fails, shrinks it to the smallest example that still fails. It
shares its name with the user's *hypothesis* — the claim a map starts from — and
has nothing to do with it.

Everything here lives in the tests, never in the shipped code, so the rules layer
gains no dependency on it.

Two families of generator, and the difference between them is the whole design.

**Valid by construction.** `graphs()`, `propositions()`, `links()` and `beliefs()`
build things that already satisfy every rule: a map from `graphs()` has exactly
one starting claim, at least one ending you can act on, arrows whose two ends are
both present, no loops among the ordinary arrows, a source behind every arrow
that claims one, and a delay on every feedback arrow. If `validate` ever
complains about one of these, either `validate` or this file is wrong, and the
failing example says which.

**Broken on purpose.** `broken_graphs(*rules)` takes a map built that way and
damages exactly the rules it is named, one damage per name. That is what lets a
test say "break this one thing and you get this one complaint, and no others".

Identifiers are readable on purpose — `claim-0`, `arrow-3`, `map-7` — because a
twenty-six character identifier in a failing example teaches nobody anything. The
rules layer never checks the format, which is what makes this possible.
"""

from datetime import date
from typing import Any

import networkx
from hypothesis import assume
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy, composite

from katalyst.domain import (
    BaseRate,
    Belief,
    Beliefs,
    Believe,
    Branch,
    ContractPayoff,
    Do,
    Evidence,
    Graph,
    Insert,
    Intervention,
    Link,
    Observe,
    Payoff,
    PricePayoff,
    Proposition,
    Refine,
    Resolution,
    Retune,
    Source,
)

# --- Words, so a failing example reads like a map and not like noise -------

CLAIM_SENTENCES: tuple[str, ...] = (
    "The Strait of Hormuz reopens to unrestricted commercial transit.",
    "Brent crude settles below sixty-eight dollars for five sessions.",
    "The Lloyd's war-risk premium for Gulf transits falls under half a per cent.",
    "OPEC+ announces an output restraint.",
    "A confirmed military strike on Iranian territory is reported.",
    "Datacentre photonic transceiver share crosses a tenth of shipments.",
    "The Federal Reserve cuts its policy rate at its next meeting.",
    "A ceasefire holds for a full calendar month.",
)

CRITERIA_SENTENCES: tuple[str, ...] = (
    "At least fourteen consecutive days of unrestricted commercial transit.",
    "Five consecutive settlement prices under the stated level.",
    "The published rate is under the stated level on the last business day.",
    "A formal announcement carried by the organisation's own newsroom.",
)

ADJUDICATORS: tuple[str, ...] = (
    "Lloyd's List transit counts",
    "ICE Futures settlement prices",
    "the Federal Reserve's own release",
    "at least two of AP, Reuters and AFP",
)

RATIONALE_SENTENCES: tuple[str, ...] = (
    "The war-risk premium in the price unwinds once transit data confirms the lane is open.",
    "Underwriters reprice Gulf hulls only while the lane actually stays open.",
    "Cheaper insurance cuts the delivered cost of a cargo, and the saving shows up in the price.",
    "A sustained run of low settlements pressures revenue targets and brings forward a decision.",
)

INSTRUMENTS: tuple[str, ...] = (
    "the front-month futures contract",
    "the energy-sector fund against the broad-market fund",
    "the exchange-traded fund that tracks the sector",
)

CONTRACT_VENUES: tuple[str, ...] = ("Polymarket", "Kalshi")

CONTRACT_TITLES: tuple[str, ...] = (
    "Will the strait be open to unrestricted transit for a fortnight?",
    "Will the price settle below the stated level before the year ends?",
)

NO_INSTRUMENT_REASONS: tuple[str, ...] = (
    "No venue quotes this, and the listed pure-plays are too thin to trade honestly.",
    "Every instrument that would express this settles long after the claim resolves.",
)

REFERENCE_CLASSES: tuple[str, ...] = (
    "Disruption episodes since nineteen eighty that ended within ninety days.",
    "Months since the start of the decade in which the price settled under the level.",
)

PROVENANCE_WITHOUT_EVIDENCE: tuple[str, ...] = ("asserted", "argued", "user", "simulated")
"""The four ways of recording a number that claims no document and no price behind it."""

PROVENANCE_CLAIMING_EVIDENCE: tuple[str, ...] = ("documented", "historical", "market_implied")
"""The three ways of recording a number that does claim one, and so must cite a source."""

TERMINAL_KINDS: tuple[str, ...] = ("market", "not_tradeable")
"""The two ways a chain is allowed to end."""

BREAKABLE_RULES: tuple[str, ...] = (
    "missing_resolution",
    "belief_out_of_range",
    "no_hypothesis",
    "no_terminal",
    "missing_rationale",
    "documented_without_source",
    "half_life_without_impulse",
    "impulse_without_half_life",
    "cycle",
    "reflexive_without_lag",
    "dangling_link",
    "duplicate_link",
    "multiple_hypotheses",
    "market_without_payoff",
    "not_tradeable_without_reason",
)
"""Every rule `broken_graphs` knows how to break, in the order it applies them.

The order matters only because some damages change a claim or an arrow and others
add one: the changes are made first, so a later damage never lands on something an
earlier damage invented.
"""

INDEPENDENTLY_BREAKABLE: tuple[str, ...] = (
    "missing_resolution",
    "belief_out_of_range",
    "missing_rationale",
    "documented_without_source",
    "half_life_without_impulse",
    "impulse_without_half_life",
    "cycle",
    "reflexive_without_lag",
    "dangling_link",
    "duplicate_link",
    "multiple_hypotheses",
    "market_without_payoff",
    "not_tradeable_without_reason",
)
"""The rules that can be broken together, any of them alongside any other.

Two pairs are left out because breaking both is not possible at once, not because
the code cannot do it. A map with **no ending you can act on** cannot also hold a
tradeable ending that names no instrument, or an untradeable ending that gives no
reason — those two damages work by adding an ending, which is the thing
`no_terminal` has just taken away. And a map with **no starting claim** cannot
also have several. Each of those four rules has its own single-rule test.
"""

MISSING_CLAIM_ID = "claim-not-on-this-map"
"""An identifier deliberately belonging to nothing, for making an arrow dangle."""


# --- The small pieces ------------------------------------------------------


def seeds() -> SearchStrategy[int]:
    """Whole numbers used to drive a random simulation.

    Generates: a number between zero and four billion.
    Guarantees: nothing but the range. A seed carries no meaning of its own; what
    matters is that the same one always produces the same world, which is what the
    replay tests check once there is something to replay.
    """
    return st.integers(min_value=0, max_value=2**32 - 1)


def raw_belief_fields() -> SearchStrategy[tuple[float, float, float, str]]:
    """Four raw values to try building a likelihood out of, most of which will not work.

    Generates: three arbitrary floating-point numbers — including the ones that are
    not numbers at all, such as "not a number" and the infinities — paired with one
    of the three owners.
    Guarantees: nothing whatever about the values. That is the point: feeding these
    to `Belief` must either produce a likelihood that sits inside its own range, or
    raise. There is no third outcome and no silent clamping to fit.
    """
    return st.tuples(
        st.floats(),
        st.floats(),
        st.floats(),
        st.sampled_from(("model", "user", "market")),
    )


@composite
def beliefs(draw: Any, owner: str | None = None) -> Belief:
    """One likelihood with an honest range and a name on it.

    Generates: a likelihood, a bottom and a top, and an owner.
    Guarantees: zero is at most the bottom, the bottom at most the likelihood, the
    likelihood at most the top, and the top at most one. Valid by construction, so
    anything drawn here can be built without raising.

    Args:
        draw: Supplied by the generator library.
        owner: Pin the owner when the caller needs a particular voice; otherwise
            one of the three is chosen at random.
    """
    edges = sorted(
        draw(
            st.lists(
                st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
                min_size=3,
                max_size=3,
            )
        )
    )
    chosen = owner if owner is not None else draw(st.sampled_from(("model", "user", "market")))
    return Belief(lo=edges[0], p=edges[1], hi=edges[2], owner=chosen)


PRINTABLE_FLOOR = 0.01
"""The smallest likelihood this product will write as a number rather than as words.

Every likelihood on screen is written to two significant figures, and one that
rounds to nothing or to everything is written `<.01` or `>.99` instead, because
printing `1.0` claims a certainty nobody asserted (`spec/graph/belief.md`, and
`two_figures` in `katalyst/domain/belief.py`). So `.01` to `.99` is the band in
which this product is willing to state a likelihood at all, and a claim outside it
is one the product itself treats as already settled. That makes it the floor for a
generator asked for a claim that could still come out either way: **the margin is
the product's own printing rule, not a number chosen here.**
"""


@composite
def uncertain_beliefs(draw: Any, owner: str = "model") -> Belief:
    """One likelihood for a claim that could genuinely still come out either way.

    Generates: a range at least `.01` wide with both ends inside the band this
    product is willing to print, and a likelihood strictly between those two ends.
    Guarantees, all three from the one printing rule above:

    * the likelihood is at least `.01` and at most `.99`, so the engine cannot
      settle the claim in every world before anything else happens;
    * the bottom is below the likelihood and the top is above it, so both halves of
      the fitted curve have width and every version of the map draws a different
      number for this claim rather than the same number two thousand times;
    * the bottom and the top are at least `.01` apart — the smallest difference this
      product will write down at all — so the range is one it could actually show,
      and not two ends that print as the same number.

    Built, never filtered: nothing drawn here is discarded.

    `beliefs()` above is the right generator for testing the *shape* of a
    likelihood, and it produces the degenerate ones on purpose — nought, one, and a
    range of no width. A claim with no stated range is what
    `test_band_is_not_sampling_noise` deliberately builds, and it is a different
    test. This generator is for the ones that need a claim the engine can still
    move.

    Args:
        draw: Supplied by the generator library.
        owner: Whose number it is. The model's, unless a caller says otherwise.
    """
    ceiling = 1.0 - PRINTABLE_FLOOR
    # The bottom stops a whole floor short of the ceiling, so there is always room
    # above it for a range at least that wide, and the draw below can never be
    # asked for a number above the one under it.
    bottom = draw(
        st.floats(
            min_value=PRINTABLE_FLOOR,
            max_value=ceiling - PRINTABLE_FLOOR,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    top = draw(
        st.floats(
            min_value=bottom + PRINTABLE_FLOOR,
            max_value=ceiling,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    return Belief(
        lo=bottom,
        p=draw(
            st.floats(
                min_value=bottom,
                max_value=top,
                exclude_min=True,
                exclude_max=True,
                allow_nan=False,
                allow_infinity=False,
            )
        ),
        hi=top,
        owner=owner,
    )


@composite
def belief_sets(draw: Any) -> Beliefs:
    """The three slots on one claim, each holding a number owned by the right voice.

    Generates: the model's number always, the user's and the market's sometimes.
    Guarantees: every slot holds a likelihood owned by the voice the slot is named
    for, so the set can be built without raising.
    """
    return Beliefs(
        model=draw(beliefs(owner="model")),
        user=draw(st.one_of(st.none(), beliefs(owner="user"))),
        market=draw(st.one_of(st.none(), beliefs(owner="market"))),
    )


@composite
def resolutions(draw: Any) -> Resolution:
    """How one claim gets settled: the test, the judge, and the date.

    Generates: a test and a judge drawn from short lists of realistic wordings, and
    a date.
    Guarantees: neither the test nor the judge is blank, which is what rule one asks
    for.
    """
    return Resolution(
        criteria=draw(st.sampled_from(CRITERIA_SENTENCES)),
        source=draw(st.sampled_from(ADJUDICATORS)),
        by=draw(st.dates(min_value=date(2026, 1, 1), max_value=date(2030, 12, 31))),
    )


@composite
def payoffs(draw: Any) -> Payoff:
    """What one tradeable ending is worth, either way round.

    Generates: half the time a named contract at a named venue and the side you
    would take; the other half an instrument, which way you would take it, and how
    far its price is expected to move.
    Guarantees: both arms are built, so anything reading a payoff is made to cope
    with both. A price move is never negative — the side carries the direction —
    and a contract always names the venue and the contract, so a reader can look it
    up. Neither arm says what the position costs; that is not this layer's business.
    """
    if draw(st.booleans()):
        return ContractPayoff(
            venue=draw(st.sampled_from(CONTRACT_VENUES)),
            contract_id=draw(st.sampled_from(("brent-below-seventy", "strait-open-fortnight"))),
            title=draw(st.sampled_from(CONTRACT_TITLES)),
            side=draw(st.sampled_from(("yes", "no"))),
        )
    return PricePayoff(
        instrument=draw(st.sampled_from(INSTRUMENTS)),
        direction=draw(st.sampled_from(("long", "short"))),
        move=draw(st.floats(min_value=0.0, max_value=3.0, allow_nan=False)),
    )


@composite
def base_rates(draw: Any) -> BaseRate:
    """How often this kind of thing has happened before: so many cases out of so many.

    Generates: a reference class, two counts, and sometimes a web address.
    Guarantees: the count of true cases never exceeds the size of the set, and the
    set is never empty.
    """
    total = draw(st.integers(min_value=1, max_value=200))
    return BaseRate(
        reference_class=draw(st.sampled_from(REFERENCE_CLASSES)),
        k=draw(st.integers(min_value=0, max_value=total)),
        n=total,
        sources=tuple(draw(st.lists(st.just("https://example.test/count"), max_size=2))),
    )


@composite
def evidence_items(draw: Any) -> Evidence:
    """One published item for or against a claim.

    Generates: what it says, where to read it, which way it points, and how much it
    counts.
    Guarantees: it points one way or the other and never neither, and it counts
    somewhere between nothing and everything.
    """
    return Evidence(
        claim=draw(st.sampled_from(CLAIM_SENTENCES)),
        url="https://example.test/item",
        direction=draw(st.sampled_from((1, -1))),
        weight=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
    )


@composite
def sources(draw: Any) -> Source:
    """One thing a reader can open to check what we are claiming.

    Generates: an address, a title, and sometimes the day it was fetched.
    Guarantees: both the address and the title are present, since a citation a
    reader cannot open is not a citation.
    """
    return Source(
        url="https://example.test/document",
        title=draw(st.sampled_from(("Voyage economics in the Gulf", "Transit counts, monthly"))),
        retrieved=draw(
            st.one_of(st.none(), st.dates(min_value=date(2020, 1, 1), max_value=date(2026, 9, 17)))
        ),
    )


@composite
def propositions(
    draw: Any,
    identifier: str | None = None,
    kind: str | None = None,
    priors: SearchStrategy[Belief] | None = None,
) -> Proposition:
    """One claim that will be true or false by a date, judged by a named source.

    Generates: an identifier, the claim in a sentence, one of the four kinds, how it
    will be settled, the model's number before and after its causes, and sometimes a
    reference class and some published items.
    Guarantees: the test and the judge are not blank; the prior is owned by the
    model and every slot's number is owned by the voice the slot is named for; a
    tradeable ending always names an instrument and an untradeable one always says
    why. Valid by construction.

    Args:
        draw: Supplied by the generator library.
        identifier: Pin the identifier when the caller is assembling a whole map.
        kind: Pin the kind for the same reason; otherwise one of the four is chosen.
        priors: Where the claim's `prior` comes from. The default covers every
            likelihood the rules allow, degenerate ones included. Hand in
            `uncertain_beliefs()` when the test needs a claim the engine can still
            move — that is the number the engine actually reads, so it is the one
            worth choosing.
    """
    chosen_id = (
        identifier
        if identifier is not None
        else draw(st.sampled_from(tuple(f"claim-{index}" for index in range(8))))
    )
    chosen_kind = (
        kind
        if kind is not None
        else draw(st.sampled_from(("hypothesis", "event", "market", "not_tradeable")))
    )
    return Proposition(
        id=chosen_id,
        claim=draw(st.sampled_from(CLAIM_SENTENCES)),
        kind=chosen_kind,
        resolution=draw(resolutions()),
        prior=draw(priors if priors is not None else beliefs(owner="model")),
        beliefs=draw(belief_sets()),
        base_rate=draw(st.one_of(st.none(), base_rates())),
        evidence=tuple(draw(st.lists(evidence_items(), max_size=2))),
        payoff=draw(payoffs()) if chosen_kind == "market" else None,
        not_tradeable_reason=(
            draw(st.sampled_from(NO_INSTRUMENT_REASONS)) if chosen_kind == "not_tradeable" else None
        ),
    )


@composite
def links(
    draw: Any,
    identifier: str | None = None,
    source: str | None = None,
    target: str | None = None,
    reflexive: bool | None = None,
) -> Link:
    """One arrow: a causal claim from one proposition to another.

    Generates: an identifier, the two ends, whether the push is a one-time shove or
    a continuous hold, how hard it pushes, how long it takes, its shape over time,
    the mechanism in a sentence, sometimes citations, and where the number came
    from. There is no field for how sure the model is of its own mechanism; the
    sentence is the argument and the provenance is our receipt for it.
    Guarantees: the mechanism is never blank; an arrow whose provenance claims a
    document or a price cites at least one source; a feedback arrow always has a
    delay greater than zero; a half-life appears only on a push that fades, which
    is the spike. Valid by construction.

    Args:
        draw: Supplied by the generator library.
        identifier: Pin the arrow's identifier when assembling a whole map.
        source: Pin the cause — the claim the arrow starts at.
        target: Pin the effect — the claim the arrow ends at.
        reflexive: Pin whether this is a market feeding back on the world.
    """
    is_feedback = reflexive if reflexive is not None else draw(st.booleans())
    claims_evidence = draw(st.booleans())
    shape = draw(st.sampled_from(("impulse", "step", "ramp")))
    return Link(
        id=identifier if identifier is not None else "arrow-0",
        source=source if source is not None else "claim-0",
        target=target if target is not None else "claim-1",
        mode=draw(st.sampled_from(("trigger", "sustain"))),
        strength=draw(st.floats(min_value=-4.0, max_value=4.0, allow_nan=False)),
        lag=(
            draw(st.floats(min_value=0.5, max_value=30.0, allow_nan=False))
            if is_feedback
            else draw(st.floats(min_value=0.0, max_value=30.0, allow_nan=False))
        ),
        shape=shape,
        half_life=(
            draw(st.floats(min_value=0.5, max_value=90.0, allow_nan=False))
            if shape == "impulse"
            else None
        ),
        rationale=draw(st.sampled_from(RATIONALE_SENTENCES)),
        sources=(
            (draw(sources()),) if claims_evidence else tuple(draw(st.lists(sources(), max_size=1)))
        ),
        provenance=draw(
            st.sampled_from(
                PROVENANCE_CLAIMING_EVIDENCE if claims_evidence else PROVENANCE_WITHOUT_EVIDENCE
            )
        ),
        reflexive=is_feedback,
    )


# --- A whole map, valid by construction ------------------------------------


@composite
def graphs(
    draw: Any, separated: bool = False, priors: SearchStrategy[Belief] | None = None
) -> Graph:
    """A whole cause-and-effect map that already satisfies every rule.

    Generates: between two and eight claims — four and eight when a map in two
    pieces is asked for — the arrows between them, and the claim the map started
    from. Claims are numbered, and an arrow only ever runs from a
    lower-numbered claim to a higher-numbered one, which is what keeps the map free
    of loops without having to check for them afterwards. Sometimes one extra arrow
    runs backwards, and that one is always marked as a market feeding back on the
    world and always carries a delay — the one legal way to close a loop.

    Guarantees: exactly one claim of kind hypothesis, and it is the one the map
    names as its starting claim; at least one ending you can act on; every arrow's
    two ends present on the map; every arrow carrying a mechanism, and a source
    wherever it claims one; every feedback arrow carrying a delay; every likelihood
    inside its own range. `validate` returns an empty list for anything drawn here.

    Args:
        draw: Supplied by the generator library.
        separated: Ask for a map in **two pieces** with no arrow running between
            them. Nothing about validity requires a map to be all of a piece, and
            the locality tests need two claims with nothing joining them: on a map
            that is all of a piece the first claim is an ancestor of every other,
            so every pair of claims shares a cause and the test would have nothing
            to pin. Each piece gets at least two claims, so each has at least one
            arrow in it. The default is a single piece, which is what every test
            written before this option expects.
        priors: Where each claim's `prior` comes from, handed straight to
            `propositions()`. The default covers every likelihood the rules allow.
            Hand in `uncertain_beliefs()` for a map on which nothing is settled
            before the engine starts.
    """
    size = draw(st.integers(min_value=4 if separated else 2, max_value=8))
    identifiers = [f"claim-{index}" for index in range(size)]

    # Where the second piece begins, when one was asked for. Past the end of the
    # map when it was not, which is what makes every claim below fall in the
    # first piece and the map come out all of one piece.
    second_piece = draw(st.integers(min_value=2, max_value=size - 2)) if separated else size

    # The first claim is what the user started from. The last claim of each piece
    # is an ending you can act on, so the map always ends somewhere. The ones in
    # between are steps, or endings of their own.
    kinds = ["hypothesis"]
    for index in range(1, size):
        if index in (second_piece - 1, size - 1):
            kinds.append(draw(st.sampled_from(TERMINAL_KINDS)))
        else:
            kinds.append(draw(st.sampled_from(("event", "event", "market", "not_tradeable"))))

    claims = [
        draw(propositions(identifier=identifiers[index], kind=kinds[index], priors=priors))
        for index in range(size)
    ]

    arrows: list[Link] = []
    for index in range(1, size):
        # A cause always comes from the same piece of the map, so no arrow ever
        # joins the two. The first claim of the second piece has no earlier claim
        # in its own piece, so it has no causes at all.
        earlier = identifiers[second_piece:index] if index >= second_piece else identifiers[:index]
        if not earlier:
            continue
        causes = draw(
            st.lists(
                st.sampled_from(earlier),
                min_size=1,
                max_size=min(len(earlier), 3),
                unique=True,
            )
        )
        for cause in causes:
            arrows.append(
                draw(
                    links(
                        identifier=f"arrow-{len(arrows)}",
                        source=cause,
                        target=identifiers[index],
                        reflexive=False,
                    )
                )
            )

    # One arrow may run backwards. It is legal only because it is marked as a
    # market feeding back on the world, which takes it out of the loop check, and
    # only because it takes time.
    if draw(st.booleans()):
        turned = draw(st.sampled_from(arrows))
        arrows.append(
            draw(
                links(
                    identifier=f"arrow-{len(arrows)}",
                    source=turned.target,
                    target=turned.source,
                    reflexive=True,
                )
            )
        )

    return Graph(
        id=f"map-{draw(st.integers(min_value=0, max_value=999))}",
        propositions=tuple(claims),
        links=tuple(arrows),
        hypothesis_id=identifiers[0],
    )


def fully_separated_pairs(graph: Graph) -> list[tuple[str, str]]:
    """Every pair of claims on a map with nothing at all joining them.

    "Nothing joining them" means three things at once: no chain of arrows runs
    from the first to the second, none runs from the second to the first, and no
    claim anywhere is a cause of both. Those three are exactly what it takes for
    the second claim to sit outside the *widest* of the six affected sets — the
    one `observe` has, which reaches the target, everything it causes, its own
    causes, and everything those causes lead to.

    Args:
        graph: The map to read.

    Returns:
        Each such pair, both ways round, in a settled order so that a failing
        example reads the same twice.
    """
    present = {one.id for one in graph.propositions}
    walk: networkx.DiGraph = networkx.DiGraph()
    walk.add_nodes_from(sorted(present))
    walk.add_edges_from(
        (one.source, one.target)
        for one in graph.links
        if one.source in present and one.target in present
    )
    leads_to = {claim: networkx.descendants(walk, claim) for claim in walk}
    caused_by = {claim: networkx.ancestors(walk, claim) for claim in walk}
    return [
        (subject, other)
        for subject in sorted(walk)
        for other in sorted(walk)
        if other != subject
        and other not in leads_to[subject]
        and subject not in leads_to[other]
        and not (caused_by[subject] & caused_by[other])
    ]


@composite
def separated_pair(draw: Any, graph: Graph) -> tuple[str, str]:
    """Two claims on one map with nothing joining them: a subject, and a claim to pin.

    Generates: a pair of claim identifiers drawn from `fully_separated_pairs`.
    Guarantees: the second claim is outside the affected set of any edit made on
    the first, whichever of the six operations it is. That is what makes it worth
    pinning — an assertion over an empty set is always true, and without a claim
    that is certainly outside, the locality test for `observe` would pass while
    checking nothing.

    A map that offers no such pair is discarded rather than quietly passed. Ask
    `graphs(separated=True)` for a map in two pieces and there are always plenty.

    Args:
        draw: Supplied by the generator library.
        graph: The map the two claims are on.
    """
    pairs = fully_separated_pairs(graph)
    assume(pairs)
    return draw(st.sampled_from(pairs))


# --- The same maps, damaged on purpose -------------------------------------


def _with_claim(graph: Graph, changed: Proposition) -> Graph:
    """Put a changed claim back on the map in place of the one it replaces.

    The replacement is made without re-checking the map, because the whole point of
    these helpers is to produce a map that would not pass.
    """
    return graph.model_copy(
        update={
            "propositions": tuple(
                changed if one.id == changed.id else one for one in graph.propositions
            )
        }
    )


def _with_arrow(graph: Graph, changed: Link) -> Graph:
    """Put a changed arrow back on the map in place of the one it replaces."""
    return graph.model_copy(
        update={"links": tuple(changed if one.id == changed.id else one for one in graph.links)}
    )


def _added_arrow_id(graph: Graph) -> str:
    """Name an arrow that is certainly not already on the map."""
    return f"arrow-added-{len(graph.links)}"


def _break_missing_resolution(draw: Any, graph: Graph) -> Graph:
    """Blank one claim's test, its judge, or both."""
    victim = draw(st.sampled_from(graph.propositions))
    blank_test, blank_judge = draw(st.sampled_from(((True, False), (False, True), (True, True))))
    resolution = victim.resolution.model_copy(
        update={
            "criteria": "   " if blank_test else victim.resolution.criteria,
            "source": "" if blank_judge else victim.resolution.source,
        }
    )
    return _with_claim(graph, victim.model_copy(update={"resolution": resolution}))


def _break_belief_out_of_range(draw: Any, graph: Graph) -> Graph:
    """Put a likelihood on one claim that its own class would have refused.

    Built with `model_construct`, the one way of making a model without running its
    checks, because there is no other way to produce the thing this rule exists to
    catch.
    """
    victim = draw(st.sampled_from(graph.propositions))
    impossible = draw(
        st.sampled_from(
            (
                Belief.model_construct(p=1.4, lo=0.2, hi=0.5, owner="model"),
                Belief.model_construct(p=0.1, lo=0.6, hi=0.9, owner="model"),
                Belief.model_construct(p=-0.3, lo=-0.5, hi=0.5, owner="model"),
            )
        )
    )
    spoiled = victim.beliefs.model_copy(update={"model": impossible})
    return _with_claim(graph, victim.model_copy(update={"beliefs": spoiled}))


def _break_no_hypothesis(draw: Any, graph: Graph) -> Graph:
    """Turn the claim the map started from into an ordinary step."""
    starter = next(one for one in graph.propositions if one.kind == "hypothesis")
    return _with_claim(graph, starter.model_copy(update={"kind": "event"}))


def _break_no_terminal(draw: Any, graph: Graph) -> Graph:
    """Turn every ending into an ordinary step, so the map stops nowhere in particular."""
    demoted = tuple(
        one.model_copy(update={"kind": "event", "payoff": None, "not_tradeable_reason": None})
        if one.kind in TERMINAL_KINDS
        else one
        for one in graph.propositions
    )
    return graph.model_copy(update={"propositions": demoted})


def _break_missing_rationale(draw: Any, graph: Graph) -> Graph:
    """Blank one arrow's mechanism, leaving a number with no reason behind it."""
    victim = draw(st.sampled_from(graph.links))
    return _with_arrow(
        graph, victim.model_copy(update={"rationale": draw(st.sampled_from(("", "  ")))})
    )


def _break_documented_without_source(draw: Any, graph: Graph) -> Graph:
    """Make one arrow claim a document or a price is behind it, and cite nothing."""
    victim = draw(st.sampled_from(graph.links))
    return _with_arrow(
        graph,
        victim.model_copy(
            update={
                "provenance": draw(st.sampled_from(PROVENANCE_CLAIMING_EVIDENCE)),
                "sources": (),
            }
        ),
    )


def _break_half_life_without_impulse(draw: Any, graph: Graph) -> Graph:
    """Put a half-life on one arrow whose push holds instead of fading.

    Both fields are set together, so the arrow is unambiguously wrong in one way:
    a shape that never falls away, carrying a number that says how fast it falls
    away.
    """
    victim = draw(st.sampled_from(graph.links))
    return _with_arrow(
        graph,
        victim.model_copy(
            update={
                "shape": draw(st.sampled_from(("step", "ramp"))),
                "half_life": draw(st.floats(min_value=0.5, max_value=90.0, allow_nan=False)),
            }
        ),
    )


def _break_impulse_without_half_life(draw: Any, graph: Graph) -> Graph:
    """Make one arrow's push a spike and take away the number saying how fast it fades.

    Added rather than changed, so this damage and the one above it — a half-life
    on a push that holds — can be done to the same map at once without landing on
    the same arrow and cancelling out. The added arrow runs **forwards between two
    claims nothing joins yet**, so it closes no loop, dangles from nothing, and is
    not a second arrow between a pair that already has one (2026-09-20).
    """
    source, target = _a_pair_nothing_joins_yet(draw, graph)
    fading = draw(
        links(
            identifier=_added_arrow_id(graph),
            source=source,
            target=target,
            reflexive=False,
        )
    )
    return graph.model_copy(
        update={
            "links": (
                *graph.links,
                fading.model_copy(update={"shape": "impulse", "half_life": None}),
            ),
        }
    )


def _break_cycle(draw: Any, graph: Graph) -> Graph:
    """Add an ordinary arrow running back the way an existing one came.

    Ordinary, not feedback: a feedback arrow is set aside before the loop check, so
    it would close nothing. One added arrow makes exactly one tangle of claims, and
    so exactly one complaint.
    """
    joined = {(one.source, one.target) for one in graph.links}
    turnable = [
        one for one in graph.links if not one.reflexive and (one.target, one.source) not in joined
    ]
    assume(turnable)
    turned = draw(st.sampled_from(turnable))
    closing = draw(
        links(
            identifier=_added_arrow_id(graph),
            source=turned.target,
            target=turned.source,
            reflexive=False,
        )
    )
    return graph.model_copy(update={"links": (*graph.links, closing)})


def _break_reflexive_without_lag(draw: Any, graph: Graph) -> Graph:
    """Add a feedback arrow that takes no time, which is a contradiction rather than a loop.

    Added rather than changed, so that this damage never interferes with the loop
    check: a feedback arrow is set aside there whatever its delay.
    """
    joined = {(one.source, one.target) for one in graph.links}
    turnable = [one for one in graph.links if (one.target, one.source) not in joined]
    assume(turnable)
    turned = draw(st.sampled_from(turnable))
    instant = draw(
        links(
            identifier=_added_arrow_id(graph),
            source=turned.target,
            target=turned.source,
            reflexive=True,
        )
    )
    return graph.model_copy(
        update={"links": (*graph.links, instant.model_copy(update={"lag": 0.0}))}
    )


def _break_dangling_link(draw: Any, graph: Graph) -> Graph:
    """Add an arrow with one end on a claim that is not on the map."""
    anchor = draw(st.sampled_from(graph.propositions))
    points_outward = draw(st.booleans())
    dangling = draw(
        links(
            identifier=_added_arrow_id(graph),
            source=anchor.id if points_outward else MISSING_CLAIM_ID,
            target=MISSING_CLAIM_ID if points_outward else anchor.id,
            reflexive=False,
        )
    )
    return graph.model_copy(update={"links": (*graph.links, dangling)})


def _a_pair_nothing_joins_yet(draw: Any, graph: Graph) -> tuple[str, str]:
    """Pick two claims, in order, that no arrow joins that way round yet.

    Numbered order is kept — a lower-numbered claim causes a higher-numbered one —
    so an arrow drawn between them closes no loop. Added on 2026-09-20 with the
    rule that one ordered pair of claims takes one arrow: before it, a breaker
    could quietly draw a second arrow between a pair and produce a fault it was
    not asking for.
    """
    joined = {(one.source, one.target) for one in graph.links}
    names = [one.id for one in graph.propositions]
    free = [
        (earlier, later)
        for index, earlier in enumerate(names)
        for later in names[index + 1 :]
        if (earlier, later) not in joined
    ]
    assume(free)
    pair: tuple[str, str] = draw(st.sampled_from(free))
    return pair


def _break_duplicate_link(draw: Any, graph: Graph) -> Graph:
    """Draw a second arrow between a pair of claims one arrow already joins.

    Only over an arrow whose two ends are both on the map: doubling a dangling
    one would double its own complaint as well, and each breaker here damages a
    map in exactly one way.
    """
    on_the_map = {one.id for one in graph.propositions}
    joining = [one for one in graph.links if one.source in on_the_map and one.target in on_the_map]
    assume(joining)
    already = draw(st.sampled_from(joining))
    again = draw(
        links(
            identifier=_added_arrow_id(graph),
            source=already.source,
            target=already.target,
            reflexive=already.reflexive,
        )
    )
    return graph.model_copy(update={"links": (*graph.links, again)})


def _break_multiple_hypotheses(draw: Any, graph: Graph) -> Graph:
    """Add a second claim marked as the one the map started from."""
    intruder = draw(propositions(identifier="claim-second-starter", kind="hypothesis"))
    return graph.model_copy(update={"propositions": (*graph.propositions, intruder)})


def _break_market_without_payoff(draw: Any, graph: Graph) -> Graph:
    """Add a tradeable ending that names nothing to trade."""
    empty = draw(propositions(identifier="claim-unpriced-ending", kind="market"))
    return graph.model_copy(
        update={"propositions": (*graph.propositions, empty.model_copy(update={"payoff": None}))}
    )


def _break_not_tradeable_without_reason(draw: Any, graph: Graph) -> Graph:
    """Add an untradeable ending that never says why there is nothing to trade."""
    silent = draw(propositions(identifier="claim-silent-ending", kind="not_tradeable"))
    return graph.model_copy(
        update={
            "propositions": (
                *graph.propositions,
                silent.model_copy(
                    update={"not_tradeable_reason": draw(st.sampled_from((None, " ")))}
                ),
            )
        }
    )


BREAKERS = {
    "missing_resolution": _break_missing_resolution,
    "belief_out_of_range": _break_belief_out_of_range,
    "no_hypothesis": _break_no_hypothesis,
    "no_terminal": _break_no_terminal,
    "missing_rationale": _break_missing_rationale,
    "documented_without_source": _break_documented_without_source,
    "half_life_without_impulse": _break_half_life_without_impulse,
    "impulse_without_half_life": _break_impulse_without_half_life,
    "cycle": _break_cycle,
    "reflexive_without_lag": _break_reflexive_without_lag,
    "dangling_link": _break_dangling_link,
    "duplicate_link": _break_duplicate_link,
    "multiple_hypotheses": _break_multiple_hypotheses,
    "market_without_payoff": _break_market_without_payoff,
    "not_tradeable_without_reason": _break_not_tradeable_without_reason,
}
"""One way of breaking each rule, looked up by the code that rule produces."""


@composite
def broken_graphs(draw: Any, *rules: str) -> Graph:
    """A map that was valid, damaged in exactly the ways named and no others.

    Generates: a map from `graphs()`, then one deliberate act of damage per rule
    named. Each name is the code that rule produces, so `broken_graphs("cycle")`
    yields maps whose only complaint is `cycle`.

    Guarantees: `validate` returns exactly one complaint per name, with exactly
    those codes and no others. Rules that cannot be broken together are listed and
    explained in `INDEPENDENTLY_BREAKABLE` above.

    Args:
        draw: Supplied by the generator library.
        *rules: The codes of the rules to break. Naming none gives an undamaged map.

    Raises:
        KeyError: If a name is not one of the fifteen.
    """
    graph = draw(graphs())
    for rule in BREAKABLE_RULES:
        if rule in rules:
            graph = BREAKERS[rule](draw, graph)
    unknown = set(rules) - set(BREAKABLE_RULES)
    if unknown:
        raise KeyError(f"no way of breaking these rules is written down: {sorted(unknown)}")
    return graph


# --- Edits, and the branches that hold them --------------------------------


@composite
def interventions(draw: Any, graph: Graph, kind: str | None = None) -> Intervention:
    """One typed edit whose subject is actually on the given map.

    Generates: one of the six edits, at random. Anything it names — a claim, an
    arrow — is drawn from the map it was given, and anything it introduces carries
    an identifier the map does not already use.
    Guarantees: the edit can be built without raising, and every identifier it
    names exists. It does *not* guarantee the edit applies cleanly: `refine` never
    does, because splitting a claim is not built yet.

    Args:
        draw: Supplied by the generator library.
        graph: The map the edit is about.
        kind: Pin which of the six operations to make, when a test is about one of
            them; otherwise one of the six is chosen at random.
    """
    claim_ids = [one.id for one in graph.propositions]
    link_ids = [one.id for one in graph.links]
    if kind is None:
        kind = draw(st.sampled_from(("do", "observe", "insert", "retune", "refine", "believe")))

    if kind == "do":
        return Do(
            target=draw(st.sampled_from(claim_ids)),
            value=draw(st.booleans()),
            at=draw(
                st.one_of(
                    st.none(), st.dates(min_value=date(2026, 1, 1), max_value=date(2030, 12, 31))
                )
            ),
        )
    if kind == "observe":
        return Observe(target=draw(st.sampled_from(claim_ids)), value=draw(st.booleans()))
    if kind == "insert":
        newcomer = draw(propositions(identifier="claim-newcomer", kind="event"))
        anchor = draw(st.sampled_from(claim_ids))
        attachment = draw(
            links(
                identifier="arrow-newcomer",
                source=anchor,
                target=newcomer.id,
                reflexive=False,
            )
        )
        return Insert(proposition=newcomer, links=(attachment,))
    if kind == "retune":
        return Retune(
            link=draw(st.sampled_from(link_ids)),
            strength=draw(st.floats(min_value=-4.0, max_value=4.0, allow_nan=False)),
        )
    if kind == "refine":
        finer = tuple(
            draw(propositions(identifier=f"claim-finer-{index}", kind="event"))
            for index in range(draw(st.integers(min_value=2, max_value=3)))
        )
        return Refine(target=draw(st.sampled_from(claim_ids)), into=finer)
    return Believe(target=draw(st.sampled_from(claim_ids)), belief=draw(beliefs(owner="user")))


@composite
def branches(draw: Any, graph: Graph) -> Branch:
    """A named, ordered list of edits over the given map.

    Generates: an identifier, a name a person would read, sometimes a parent branch
    it continues from, and up to three edits about the given map.
    Guarantees: the name is never blank, and every edit names something on the map.
    An empty list of edits is allowed on purpose — that is the base world.

    Args:
        draw: Supplied by the generator library.
        graph: The map the branch's edits are about.
    """
    return Branch(
        id=f"branch-{draw(st.integers(min_value=0, max_value=999))}",
        label=draw(
            st.sampled_from(
                (
                    "Hormuz opens, then Iran is struck",
                    "Strike, but underwriters shrug",
                    "My own numbers",
                )
            )
        ),
        parent=draw(st.one_of(st.none(), st.just("branch-parent"))),
        interventions=tuple(draw(st.lists(interventions(graph), max_size=3))),
    )
