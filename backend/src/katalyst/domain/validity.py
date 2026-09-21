"""What makes a map valid, and why we reject rather than repair.

A language model writes most of the map. Models are useful at *proposing* causal
structure and unreliable at *asserting* it: run to run they disagree with
themselves, draw loops, write claims nobody can ever check, and attach numbers to
nothing. So validity is not something we ask the model for — it is something our
own code decides.

`validate(graph)` takes a map and returns the complete list of everything wrong
with it, each item with a stable machine-readable code and a plain sentence a
user can read. The model proposes; this function disposes.

**Reject; never repair.** Nothing here quietly fixes a map so that it passes. No
dropping the arrow that closes the loop, no downgrading a `documented` link to
`argued` because its sources came back empty, no inventing a resolve-by date, no
adding an ending so the map ends somewhere. A silently corrected map is a map the
user cannot account for: they see six arrows where the model proposed seven, and
nothing anywhere says why.

**Every violation, every time.** The walk does not stop at the first fault. A
person fixing a map one fault per rebuild learns only that the tool is hostile,
and a model given one fault at a time needs one re-prompt per fault.

**Messages are interface text.** A rejected proposal is shown to the user, so a
message names the claim by its words rather than by its identifier, says what is
missing rather than that something "failed validation", and stays one sentence
where the fault is one thing. The identifier is in `subject`, where the interface
can use it to highlight the right tile or wire.
"""

from collections import deque
from collections.abc import Mapping
from typing import Literal

import networkx
from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.belief import Belief
from katalyst.domain.graph import Graph
from katalyst.domain.ids import PropositionId
from katalyst.domain.proposition import Proposition

ViolationCode = Literal[
    "missing_resolution",
    "missing_rationale",
    "documented_without_source",
    "cycle",
    "reflexive_without_lag",
    "half_life_without_impulse",
    "impulse_without_half_life",
    "belief_out_of_range",
    "no_terminal",
    "no_hypothesis",
    "multiple_hypotheses",
    "dangling_link",
    "market_without_payoff",
    "not_tradeable_without_reason",
    "unknown_target",
    "unknown_link",
    "duplicate_id",
    "edit_not_applicable",
    "worlds_not_comparable",
]
"""The nineteen things that can be wrong: fourteen faults in a map, five refusals.

The first fourteen are what `validate` finds in a map. The last five are what our
own code refuses to do, and no map can carry any of them. Four are about an
*edit*, found when a branch is folded onto a map:

* `unknown_target` — the edit names a claim that is not on this map.
* `unknown_link` — the edit names an arrow that is not on this map.
* `duplicate_id` — an edit adds a claim or an arrow under an identifier that is
  already in use.
* `edit_not_applicable` — this edit cannot be folded onto this map as written.
  Everything it names is there; what it asks for is something this version cannot
  do, or something the shapes allow and the map cannot carry out.

The fifth is about a *comparison*, and it is the one refusal that is not about an
edit at all:

* `worlds_not_comparable` — these two worlds were not built from the same base
  map, the same seed and the same two loop sizes, so subtracting one from the
  other would leave noise rather than the change somebody made.

Stable strings: the browser switches on them, tests assert on them, and they are
never renamed without a migration.
"""

PROVENANCE_CLAIMING_EVIDENCE: tuple[str, ...] = ("documented", "historical", "market_implied")
"""The three ways of saying "a document or a price is behind this number".

An arrow whose provenance is one of these has to cite at least one source. The
other four — `asserted`, `argued`, `user` and `simulated` — claim no outside
evidence, so they are asked for none.
"""

FADING_SHAPE = "impulse"
"""The one shape of push that falls away on its own, and so the one that can have a half-life."""

TERMINAL_KINDS: tuple[str, ...] = ("market", "not_tradeable")
"""The two ways a chain is allowed to end: naming an instrument, or naming why there is none."""

LONGEST_QUOTED_CLAIM = 80
"""How much of a claim a message quotes before trimming it, so the sentence stays readable."""


class Violation(BaseModel):
    """One thing wrong with a map, addressed to two different readers at once.

    `code` and `subject` are for the machine: the interface uses them to highlight
    the tile or wire at fault. `message` is for the person: a plain sentence naming
    the claim by its text. A violation must never be the only record of a
    rejection — the list is stored with the generation transcript so a rejected
    proposal stays auditable.
    """

    model_config = ConfigDict(frozen=True)

    code: ViolationCode = Field(
        description="Which rule was broken. One of nineteen stable strings."
    )
    subject: str = Field(
        description=(
            "The identifier of the thing at fault: a proposition id, a link id, the graph's own "
            "id for faults about the map as a whole — including two worlds that cannot be "
            "compared, which names the map they should both have come from — or a branch id "
            "when a chain of branches cannot be put in order. Never shown to the user."
        )
    )
    message: str = Field(
        description=(
            "Interface text. One plain sentence that names the claim or the arrow by its words and "
            "says what is missing. Never contains an identifier."
        )
    )


def validate(graph: Graph) -> list[Violation]:
    """Return everything wrong with this map — all of it, not the first thing found.

    Pure: no clock, no network, no randomness, no logging. Same map in, same list
    out, in the same order, every time. The order is the order of the rules below,
    and within one rule the faults are sorted by the identifier of the thing at
    fault, so the interface can rank them and a test can compare two lists
    directly.

    An empty list means the map satisfies every rule. It does not mean the map is
    *right* — the numbers can still be nonsense. It means the map is well-formed
    enough to be shown to a person and argued with, which is a different and more
    modest claim.

    Args:
        graph: The map to check. It is never changed, and never read for anything
            but the values on it.

    Returns:
        One entry per fault, in rule order, ties broken by subject. Empty when the
        map is well-formed.
    """
    claims = {proposition.id: proposition for proposition in graph.propositions}

    rules_in_order = (
        _claims_say_how_they_are_judged(graph),
        _exactly_one_starting_claim(graph),
        _map_ends_somewhere_actionable(graph),
        _tradeable_claims_name_an_instrument(graph),
        _untradeable_claims_say_why(graph),
        _arrows_say_why(graph, claims),
        _arrows_claiming_evidence_cite_it(graph, claims),
        _arrows_join_claims_on_this_map(graph, claims),
        _no_loops_once_feedback_is_set_aside(graph, claims),
        _feedback_arrows_take_time(graph, claims),
        _half_lives_belong_to_pushes_that_fade(graph, claims),
        _pushes_that_fade_say_how_fast(graph, claims),
        _likelihoods_sit_inside_their_own_range(graph),
    )

    found: list[Violation] = []
    for one_rule in rules_in_order:
        found.extend(sorted(one_rule, key=lambda violation: violation.subject))
    return found


# --- Saying what is wrong, in words a person reads -------------------------


def _quoted(text: str) -> str:
    """Put a claim's own words in quotation marks, trimmed if they run long.

    Args:
        text: The claim as its author wrote it.

    Returns:
        The words in quotation marks, shortened with an ellipsis past about eighty
        characters so the sentence around them stays readable.
    """
    tidied = " ".join(text.split())
    if len(tidied) > LONGEST_QUOTED_CLAIM:
        tidied = tidied[: LONGEST_QUOTED_CLAIM - 1].rstrip() + "…"
    return f'"{tidied}"'


def _name_of(claims: Mapping[PropositionId, Proposition], identifier: PropositionId) -> str:
    """Name a claim by its words, or say plainly that it is not on this map.

    Args:
        claims: Every claim on the map, by identifier.
        identifier: The claim an arrow names.

    Returns:
        The claim's words in quotation marks, or a plain phrase standing in for a
        claim that does not exist. Never an identifier.
    """
    found = claims.get(identifier)
    return _quoted(found.claim) if found is not None else "a claim that is not on this map"


# --- Rule 1 — every claim says how it will be judged, by whom, and by when --


def _claims_say_how_they_are_judged(graph: Graph) -> list[Violation]:
    """Find claims whose resolution is blank where it should say something.

    The resolve-by date cannot be missing — it is a required date on the class —
    so only the test and the judge can be absent here.

    Args:
        graph: The map to read.

    Returns:
        One violation per claim with a blank test or a blank judge.
    """
    found: list[Violation] = []
    for proposition in graph.propositions:
        missing: list[str] = []
        if not proposition.resolution.criteria.strip():
            missing.append("how it will be judged")
        if not proposition.resolution.source.strip():
            missing.append("who judges it")
        if not missing:
            continue
        found.append(
            Violation(
                code="missing_resolution",
                subject=proposition.id,
                message=(
                    f"The claim {_quoted(proposition.claim)} does not say {' or '.join(missing)}."
                ),
            )
        )
    return found


# --- Rule 2 — exactly one claim is the hypothesis the user started from -----


def _exactly_one_starting_claim(graph: Graph) -> list[Violation]:
    """Check that one claim, and only one, is the claim the map started from.

    One rule failing in two directions, which is why it carries two codes: a map
    with none, and a map with several.

    Args:
        graph: The map to read.

    Returns:
        At most one violation, about the map as a whole.
    """
    starters = [p for p in graph.propositions if p.kind == "hypothesis"]

    if len(starters) > 1:
        named = ", ".join(_quoted(p.claim) for p in sorted(starters, key=lambda p: p.id))
        return [
            Violation(
                code="multiple_hypotheses",
                subject=graph.id,
                message=(
                    f"This map has {len(starters)} starting claims: {named}. A map has exactly one."
                ),
            )
        ]
    if not starters:
        return [
            Violation(
                code="no_hypothesis",
                subject=graph.id,
                message=(
                    "This map has no starting claim. Exactly one claim must be the hypothesis."
                ),
            )
        ]
    if starters[0].id != graph.hypothesis_id:
        return [
            Violation(
                code="no_hypothesis",
                subject=graph.id,
                message=(
                    "The claim this map started from is not the one marked as the hypothesis. "
                    "Exactly one claim must be the hypothesis, and it must be that one."
                ),
            )
        ]
    return []


# --- Rule 3 — the map ends somewhere you can act on ------------------------


def _map_ends_somewhere_actionable(graph: Graph) -> list[Violation]:
    """Check that at least one chain ends in something you could put money on, or say why not.

    Args:
        graph: The map to read.

    Returns:
        At most one violation, about the map as a whole.
    """
    if any(proposition.kind in TERMINAL_KINDS for proposition in graph.propositions):
        return []
    return [
        Violation(
            code="no_terminal",
            subject=graph.id,
            message=(
                "This map does not end anywhere you can act on. Add a claim that names an "
                "instrument, or one that says why there is nothing to trade."
            ),
        )
    ]


# --- Rules 4 and 5 — what each of the two endings must carry ---------------


def _tradeable_claims_name_an_instrument(graph: Graph) -> list[Violation]:
    """Find tradeable endings that name nothing to trade.

    This is the commonest thing a model gets wrong, which is why it comes back as
    a sentence the user reads rather than as a refusal to build the object.

    Args:
        graph: The map to read.

    Returns:
        One violation per `market` claim with no payoff.
    """
    return [
        Violation(
            code="market_without_payoff",
            subject=proposition.id,
            message=(
                f"The tradeable claim {_quoted(proposition.claim)} does not say what you "
                "would trade."
            ),
        )
        for proposition in graph.propositions
        if proposition.kind == "market" and proposition.payoff is None
    ]


def _untradeable_claims_say_why(graph: Graph) -> list[Violation]:
    """Find endings marked untradeable that never say why there is nothing to trade.

    Args:
        graph: The map to read.

    Returns:
        One violation per `not_tradeable` claim with a missing or blank reason.
    """
    return [
        Violation(
            code="not_tradeable_without_reason",
            subject=proposition.id,
            message=(
                f"The claim {_quoted(proposition.claim)} is marked not tradeable but does not "
                "say why."
            ),
        )
        for proposition in graph.propositions
        if proposition.kind == "not_tradeable"
        and (
            proposition.not_tradeable_reason is None or not proposition.not_tradeable_reason.strip()
        )
    ]


# --- Rules 6 and 7 — what every arrow must carry ---------------------------


def _arrows_say_why(graph: Graph, claims: dict[PropositionId, Proposition]) -> list[Violation]:
    """Find arrows carrying a number and no reason.

    An arrow with a number and no sentence is a state the user cannot trace, which
    is the one thing this product is not allowed to show.

    Args:
        graph: The map to read.
        claims: Every claim on the map, by identifier, for naming the two ends.

    Returns:
        One violation per arrow with a missing or blank mechanism.
    """
    return [
        Violation(
            code="missing_rationale",
            subject=link.id,
            message=(
                f"The arrow from {_name_of(claims, link.source)} to "
                f"{_name_of(claims, link.target)} does not say why one causes the other."
            ),
        )
        for link in graph.links
        if not link.rationale.strip()
    ]


def _arrows_claiming_evidence_cite_it(
    graph: Graph, claims: dict[PropositionId, Proposition]
) -> list[Violation]:
    """Find arrows that say a document or a price is behind them and then cite nothing.

    Being generous with an unbacked claim — quietly downgrading it to "argued" so
    it fits — is exactly the state a user cannot trace.

    Args:
        graph: The map to read.
        claims: Every claim on the map, by identifier, for naming the two ends.

    Returns:
        One violation per arrow claiming evidence with an empty source list.
    """
    return [
        Violation(
            code="documented_without_source",
            subject=link.id,
            message=(
                f"The arrow from {_name_of(claims, link.source)} to "
                f"{_name_of(claims, link.target)} is marked as {link.provenance} but cites "
                "no source."
            ),
        )
        for link in graph.links
        if link.provenance in PROVENANCE_CLAIMING_EVIDENCE and not link.sources
    ]


# --- Rule 8 — both ends of every arrow are on this map ---------------------


def _arrows_join_claims_on_this_map(
    graph: Graph, claims: dict[PropositionId, Proposition]
) -> list[Violation]:
    """Find arrows pointing at, or coming from, a claim that is not on the map.

    This is the one case where a message cannot name both ends, because one of
    them does not exist. It names the end that does.

    Args:
        graph: The map to read.
        claims: Every claim on the map, by identifier.

    Returns:
        One violation per arrow with a missing end.
    """
    found: list[Violation] = []
    for link in graph.links:
        cause_is_here = link.source in claims
        effect_is_here = link.target in claims
        if cause_is_here and effect_is_here:
            continue
        if cause_is_here:
            message = (
                f"The arrow out of {_name_of(claims, link.source)} points at a claim that is "
                "not on this map."
            )
        elif effect_is_here:
            message = (
                f"The arrow into {_name_of(claims, link.target)} comes from a claim that is "
                "not on this map."
            )
        else:
            message = "This arrow joins two claims, neither of which is on this map."
        found.append(Violation(code="dangling_link", subject=link.id, message=message))
    return found


# --- Rule 9 — no loops, once the feedback arrows are set aside -------------


def _walkable_map(
    graph: Graph, claims: dict[PropositionId, Proposition]
) -> "networkx.DiGraph[PropositionId]":
    """Build the map the loop check actually walks.

    Two kinds of arrow are left out. A **reflexive** arrow — a market feeding back
    on the world — is a real loop in reality, made honest by taking time, so it is
    allowed to close a loop and is set aside here. An arrow with an end that is
    not on the map is left out too, because it already has its own violation and a
    phantom claim would only confuse this one.

    Nodes and arrows are added in sorted order, so the walk below always sees the
    same map in the same shape and reports the same loop.

    Args:
        graph: The map to read.
        claims: Every claim on the map, by identifier.

    Returns:
        A directed graph of claims and the ordinary arrows between them.
    """
    walkable: networkx.DiGraph[PropositionId] = networkx.DiGraph()
    walkable.add_nodes_from(sorted(claims))
    for link in sorted(graph.links, key=lambda one: (one.source, one.target, one.id)):
        if link.reflexive or link.source not in claims or link.target not in claims:
            continue
        walkable.add_edge(link.source, link.target)
    return walkable


def _shortest_paths_within(
    walkable: "networkx.DiGraph[PropositionId]", start: PropositionId, tangle: set[PropositionId]
) -> dict[PropositionId, list[PropositionId]]:
    """Walk outward from one claim, shortest way first, staying inside one tangle.

    Written out rather than taken from the graph library so that the path reported
    to the user depends on nothing but the map itself.

    Args:
        walkable: The map without its feedback arrows.
        start: The claim to walk out from.
        tangle: The claims that can all reach each other, which is where the walk
            is allowed to go.

    Returns:
        For each claim reached, the shortest chain of claims leading to it.
    """
    reached: dict[PropositionId, list[PropositionId]] = {start: [start]}
    waiting = deque([start])
    while waiting:
        here = waiting.popleft()
        for next_claim in sorted(walkable.successors(here)):
            if next_claim in tangle and next_claim not in reached:
                reached[next_claim] = [*reached[here], next_claim]
                waiting.append(next_claim)
    return reached


def _loop_through(
    walkable: "networkx.DiGraph[PropositionId]", tangle: set[PropositionId]
) -> list[PropositionId] | None:
    """Find the shortest loop through the first claim of a tangle of claims.

    "First" means first in alphabetical order of identifier, which is arbitrary but
    always the same — the point is that the same map always reports the same loop.

    Args:
        walkable: The map without its feedback arrows.
        tangle: The claims that can all reach each other.

    Returns:
        The claims on the loop in order, starting at that first claim and ending at
        the claim whose arrow closes it, or nothing if these claims form no loop.
    """
    first = min(tangle)
    if walkable.has_edge(first, first):
        return [first]
    if len(tangle) == 1:
        return None

    reached = _shortest_paths_within(walkable, first, tangle)
    candidates = [
        reached[before]
        for before in sorted(walkable.predecessors(first))
        if before in tangle and before in reached
    ]
    if not candidates:  # pragma: no cover
        # Unreachable: every claim in a tangle can reach every other, so the first
        # claim always has a predecessor inside the tangle that the walk above has
        # already reached. Kept so that a wrong assumption here returns nothing
        # rather than crashing a checker that is meant never to raise.
        return None
    return min(candidates, key=lambda path: (len(path), tuple(path)))


def _no_loops_once_feedback_is_set_aside(
    graph: Graph, claims: dict[PropositionId, Proposition]
) -> list[Violation]:
    """Find loops among the ordinary arrows, and blame the arrow that closes each one.

    A tangle of claims that can all reach each other is one loop as far as the user
    is concerned, however many ways round it there happen to be, so it produces one
    violation rather than one per route. Two loops that share no claim are two
    tangles and two violations. An arrow from a claim to itself is a tangle of one
    and is caught by the same pass, which is why there is no separate code for it.

    Args:
        graph: The map to read.
        claims: Every claim on the map, by identifier.

    Returns:
        One violation per tangle, each naming the claims on the loop in order.
    """
    walkable = _walkable_map(graph, claims)
    found: list[Violation] = []
    for tangle in networkx.strongly_connected_components(walkable):
        loop = _loop_through(walkable, tangle)
        if loop is None:
            continue
        closing = min(
            (
                link
                for link in graph.links
                if not link.reflexive and link.source == loop[-1] and link.target == loop[0]
            ),
            key=lambda link: link.id,
        )
        walked = " → ".join(_name_of(claims, step) for step in [*loop, loop[0]])
        found.append(
            Violation(
                code="cycle",
                subject=closing.id,
                message=(
                    f"These claims form a loop with no delay in it: {walked}. Mark the arrow "
                    "where a market feeds back on the world as reflexive and give it a delay, "
                    "or remove one arrow."
                ),
            )
        )
    return found


# --- Rule 10 — every feedback arrow takes time ----------------------------


def _feedback_arrows_take_time(
    graph: Graph, claims: dict[PropositionId, Proposition]
) -> list[Violation]:
    """Find feedback arrows with no delay on them.

    A market cannot change the world it is measuring in zero time. An instantaneous
    loop is not a feedback mechanism, it is a contradiction — and it is the only
    thing keeping a reflexive arrow's exemption from the loop check honest.

    Args:
        graph: The map to read.
        claims: Every claim on the map, by identifier, for naming the two ends.

    Returns:
        One violation per reflexive arrow whose lag is zero or less.
    """
    return [
        Violation(
            code="reflexive_without_lag",
            subject=link.id,
            message=(
                f"The feedback arrow from {_name_of(claims, link.source)} to "
                f"{_name_of(claims, link.target)} has no delay. A market cannot change the "
                "world it is measuring in zero time."
            ),
        )
        for link in graph.links
        if link.reflexive and link.lag <= 0
    ]


# --- Rules 11 and 12 — a shape and its numbers agree, checked both ways ----


def _half_lives_belong_to_pushes_that_fade(
    graph: Graph, claims: dict[PropositionId, Proposition]
) -> list[Violation]:
    """Find arrows carrying a half-life whose push never fades.

    A half-life is how many days a spike takes to fall to half its size, so it says
    something only about an `impulse`. A `step` switches on and holds, and a `ramp`
    climbs and then holds; neither has anything to fade. A half-life on one of them
    is either a mistake about the shape or a number that will be ignored forever,
    and a field quietly ignored is a state the user cannot trace — so it comes back
    as a fault rather than being dropped.

    Args:
        graph: The map to read.
        claims: Every claim on the map, by identifier, for naming the two ends.

    Returns:
        One violation per arrow whose push does not fade but carries a half-life.
    """
    return [
        Violation(
            code="half_life_without_impulse",
            subject=link.id,
            message=(
                f"The arrow from {_name_of(claims, link.source)} to "
                f"{_name_of(claims, link.target)} gives a half-life, but only a spike fades; "
                "a step or a ramp has nothing to fade."
            ),
        )
        for link in graph.links
        if link.half_life is not None and link.shape != FADING_SHAPE
    ]


def _pushes_that_fade_say_how_fast(
    graph: Graph, claims: dict[PropositionId, Proposition]
) -> list[Violation]:
    """Find arrows whose push is a spike and which never say how fast it fades.

    The mirror of the rule above, and the other half of one idea: a shape and the
    numbers that describe it have to agree, checked both ways. A `step` switches on
    and holds and a `ramp` climbs and then holds, so neither may carry a half-life.
    A spike does nothing but fade, so it must say how fast — without a half-life
    there is no decay to work out at all, and whatever the code that works the
    numbers through did with such an arrow would be a number the author never
    wrote down.

    Reject, never repair: no default half-life is invented here or anywhere else.

    Args:
        graph: The map to read.
        claims: Every claim on the map, by identifier, for naming the two ends.

    Returns:
        One violation per arrow that fades without saying how fast.
    """
    return [
        Violation(
            code="impulse_without_half_life",
            subject=link.id,
            message=(
                f"The arrow from {_name_of(claims, link.source)} to "
                f"{_name_of(claims, link.target)} is a spike that fades, but does not say "
                "how fast; without a half-life there is nothing to fade by."
            ),
        )
        for link in graph.links
        if link.shape == FADING_SHAPE and link.half_life is None
    ]


# --- Rule 13 — every likelihood sits inside its own range ------------------


def _out_of_range(belief: Belief) -> bool:
    """Say whether a likelihood and its range have stopped making sense together."""
    return not (0.0 <= belief.lo <= belief.p <= belief.hi <= 1.0)


def _likelihoods_sit_inside_their_own_range(graph: Graph) -> list[Violation]:
    """Find likelihoods that are not a range around a number between 0 and 1.

    Checked here on purpose even though `Belief` already refuses to be built out of
    range, so this can never fire for a map assembled through our own classes. It
    is the net under maps that arrive some other way: a hand-edited stored example,
    a map read back after the shapes have changed, a future path that builds
    likelihoods from raw numbers.

    Args:
        graph: The map to read.

    Returns:
        One violation per likelihood that has stopped making sense, in a fixed
        order per claim: the prior first, then the model's, the user's and the
        market's.
    """
    found: list[Violation] = []
    for proposition in sorted(graph.propositions, key=lambda one: one.id):
        slots = (
            proposition.prior,
            proposition.beliefs.model,
            proposition.beliefs.user,
            proposition.beliefs.market,
        )
        for belief in slots:
            if belief is None or not _out_of_range(belief):
                continue
            found.append(
                Violation(
                    code="belief_out_of_range",
                    subject=proposition.id,
                    message=(
                        f"The {belief.owner} likelihood on {_quoted(proposition.claim)} is "
                        f"{belief.p}, with a range of {belief.lo} to {belief.hi}, which is not "
                        "a range around that number between 0 and 1."
                    ),
                )
            )
    return found
