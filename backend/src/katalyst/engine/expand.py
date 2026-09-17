"""One call, one proposal, and the three things that can happen to it.

Ask the model for the one next piece of a map, read the answer, build the map
that answer would leave behind, and hand it to the map's own rules. Nothing else.
Which claim to ask about next, and when a run should stop, are the walk's
business and live in `grow.py`.

Two rules shape all of it
-------------------------
**The model proposes; our code disposes.** Nothing a model says is ever written
onto the map until `katalyst.domain` has looked at the map that answer would
leave behind and returned nothing wrong with it. And **reject, never repair**: a
proposal that breaks a rule comes back with every reason, in the rules' own
words, and is dropped. No arrow is quietly removed to break a loop, no date is
invented, no word is softened to make an arrow fit.

**Nothing here changes the map it was given.** A proposal is a candidate map that
either wins or loses, so a refusal leaves the map a person is looking at exactly
as it was.

Four things our code adds that the model could not have
--------------------------------------------------------
The new claim's identifier, the arrow's identifier, whose the likelihood is, and
the word for where the arrow came from. All four are stamped before the map is
checked. The likelihood itself stands exactly as the model wrote it: there is no
ensemble here, no widening because stated ranges are known to run narrow, and no
second opinion averaged in.

What this file must never do
----------------------------
- Never write a claim or an arrow the model did not propose.
- Never talk over the network. It takes an answerer as an argument; `client.py`
  is the only thing that dials out, and the only place the library's own types
  are named.
- Never read a clock. The day a run happened is passed in, which is what lets a
  recorded run and a live one be compared.
- Never put a violation's words into a prompt.
"""

from collections.abc import Sequence
from datetime import date

from katalyst.domain import (
    Belief,
    Beliefs,
    Graph,
    Link,
    Proposition,
    PropositionId,
    Source,
    Violation,
    validate,
)
from katalyst.engine.client import Answerer, AnswerWeCouldNotRead
from katalyst.engine.grounding import found_in, keep_cited, provenance_of, same_address
from katalyst.engine.ids import mint_id
from katalyst.engine.outcome import Accepted, Outcome, Refused, Stopped, costing
from katalyst.engine.prompt import expanding_question, starting_question
from katalyst.engine.proposal import (
    ClaimProposal,
    LinkDraft,
    LinkProposal,
    Proposal,
    StartingClaim,
    Stop,
)


def expand(
    graph: Graph,
    frontier: PropositionId,
    *,
    target: str | None,
    answerer: Answerer,
    on: date,
    may_search: bool = True,
    ending_only: bool = False,
) -> Outcome:
    """Ask for one next piece of the map, and say what happened to it.

    One question, one answer, then the map's own rules on the map that answer
    would leave behind — not on the answer, on the **map**, because most of the
    rules are about a whole map.

    Args:
        graph: The map as it stands. It is never changed.
        frontier: The claim to ask about.
        target: The place the person asked whether the story gets to, in their own
            words, or nothing at all on the Explore door.
        answerer: Whatever this run asks its questions of.
        on: The day this run is happening, written onto anything the search finds.
        may_search: Whether this run still has searches left to spend.
        ending_only: True on the one last call a run makes when it has run out of
            room and the map still ends nowhere anybody could act on.

    Returns:
        What happened, and what the call cost. Never raises for anything the model
        did or failed to do.
    """
    question = expanding_question(graph, frontier, target=target, ending_only=ending_only, today=on)
    try:
        said = answerer.proposal(question, may_search=may_search)
    except AnswerWeCouldNotRead as did_not_fit:
        # The answer never got as far as being read, so its counters never
        # reached us. The round trip is counted because it happened and it was
        # charged; its tokens are left at nothing, because nothing is what we
        # know. This is the one place the receipt is knowingly short, and it is
        # short by one call in a run of dozens.
        return Outcome(result=Refused(claim_in_words=did_not_fit.why), about=frontier, calls=1)

    if said.declined is not None:
        return costing(Refused(claim_in_words=said.declined), frontier, said)

    proposed = said.answered
    if proposed is None or isinstance(proposed, StartingClaim):
        return costing(
            Refused(claim_in_words="The model gave no answer to this question."), frontier, said
        )
    if isinstance(proposed, Stop):
        return costing(Stopped(why=proposed.why), frontier, said)
    return costing(_judge(graph, proposed, found_in(said, on=on)), frontier, said)


def start_the_map(
    sentence: str,
    *,
    is_the_hypothesis: bool,
    answerer: Answerer,
    on: date,
) -> Outcome:
    """Turn one sentence a person typed into a claim anybody could settle.

    Asked once for the sentence the map starts from, and once more for the place
    the person asked whether it gets to. It is a different question from expanding
    a map — what did they mean, rather than what happens next — so it has its own
    small shape and its own call, and searching is forbidden on it: the web has
    nothing to say about what somebody meant.

    **Both starting claims enter as what they are, and the model is not asked
    which.** A map has exactly one claim it started from, so that one is stamped
    as the starting claim. The destination is stamped as a step in the middle,
    because a destination is where a person wants the story to *get to* and not
    where it *ends*: an ending that names a trade names a venue and a contract,
    which is a fact about a venue nobody has looked up yet, and the map must still
    run on to an ending of its own.

    Args:
        sentence: What the person typed, unchanged.
        is_the_hypothesis: True for the sentence the map starts from.
        answerer: Whatever this run asks its questions of.
        on: The day this run is happening, so a claim can be given a date.

    Returns:
        The minted claim, or the reason there is not one, and what the call cost.
    """
    question = starting_question(sentence, is_the_hypothesis=is_the_hypothesis, today=on)
    try:
        said = answerer.starting_claim(question)
    except AnswerWeCouldNotRead as did_not_fit:
        return Outcome(result=Refused(claim_in_words=did_not_fit.why), calls=1)

    if said.declined is not None:
        return costing(Refused(claim_in_words=said.declined), None, said)

    drafted = said.answered
    if not isinstance(drafted, StartingClaim):
        return costing(
            Refused(claim_in_words="The model gave no answer to this question."), None, said
        )
    return costing(Accepted(proposition=_starting_claim(drafted, is_the_hypothesis)), None, said)


# --- Minting what only we can mint ------------------------------------------


def _starting_claim(drafted: StartingClaim, is_the_hypothesis: bool) -> Proposition:
    """Mint one of the two claims a person's own sentence becomes.

    Args:
        drafted: The claim as the model wrote it.
        is_the_hypothesis: True for the sentence the map started from.

    Returns:
        The claim, with an identifier and a kind that are ours to give.
    """
    stated = Belief(p=drafted.prior.p, lo=drafted.prior.lo, hi=drafted.prior.hi, owner="model")
    return Proposition(
        id=mint_id(),
        claim=drafted.claim,
        kind="hypothesis" if is_the_hypothesis else "event",
        resolution=drafted.resolution,
        prior=stated,
        beliefs=Beliefs(model=stated),
        base_rate=drafted.base_rate,
        evidence=(),
    )


def _judge(
    graph: Graph, proposal: ClaimProposal | LinkProposal, found: tuple[Source, ...]
) -> Accepted | Refused:
    """Build the map this proposal would leave behind, and let the map's rules speak.

    Only faults the proposal **introduced** count. A map half built has no ending
    yet and says so every time it is checked; blaming a proposal for a fault that
    was there before it would refuse every proposal until the last one.

    Args:
        graph: The map as it stands.
        proposal: What the model answered with.
        found: What the search tool returned in that call.

    Returns:
        The accepted claim and arrows, or every reason the map's rules gave.
    """
    candidate, claim, arrows, dropped = _candidate_map(graph, proposal, found)
    introduced = _newly_wrong(validate(graph), validate(candidate))
    if introduced:
        return Refused(claim_in_words=_in_the_models_words(proposal), violations=introduced)
    return Accepted(proposition=claim, links=arrows, sources_dropped=dropped)


def _candidate_map(
    graph: Graph, proposal: ClaimProposal | LinkProposal, found: tuple[Source, ...]
) -> tuple[Graph, Proposition | None, tuple[Link, ...], tuple[str, ...]]:
    """Put the proposal onto a copy of the map, minting what only we can mint.

    Args:
        graph: The map as it stands. It is never changed.
        proposal: A new claim with its arrow, or an arrow on its own.
        found: What the search tool returned in that call.

    Returns:
        The map the proposal would leave behind, the new claim if there is one,
        the arrows that arrived, and the addresses that were dropped.
    """
    if isinstance(proposal, LinkProposal):
        arrow, dropped = _arrow(proposal.link, proposal.source, proposal.target, found)
        return graph.model_copy(update={"links": (*graph.links, arrow)}), None, (arrow,), dropped

    claim = _claim(proposal, found)
    arrow, dropped = _arrow(proposal.link, proposal.cause, claim.id, found)
    return (
        graph.model_copy(
            update={
                "propositions": (*graph.propositions, claim),
                "links": (*graph.links, arrow),
            }
        ),
        claim,
        (arrow,),
        dropped,
    )


def _claim(proposal: ClaimProposal, found: tuple[Source, ...]) -> Proposition:
    """Mint a claim from a proposal, stamping the two things the model may not say.

    The identifier is ours, and so is the name on the likelihood.

    A base rate's addresses are kept by the same rule as an arrow's — only what
    the search returned survives — because an empty list there already means the
    count is the model's own recollection, and nothing downstream of it may claim
    to be documented.

    Args:
        proposal: The claim as the model wrote it.
        found: What the search tool returned in that call.

    Returns:
        The claim, with an identifier nobody else could have given it.
    """
    stated = Belief(p=proposal.prior.p, lo=proposal.prior.lo, hi=proposal.prior.hi, owner="model")
    base_rate = proposal.base_rate
    if base_rate is not None:
        returned = {same_address(source.url) for source in found}
        base_rate = base_rate.model_copy(
            update={
                "sources": tuple(url for url in base_rate.sources if same_address(url) in returned)
            }
        )
    return Proposition(
        id=mint_id(),
        claim=proposal.claim,
        kind=proposal.claim_kind,
        resolution=proposal.resolution,
        prior=stated,
        beliefs=Beliefs(model=stated),
        base_rate=base_rate,
        evidence=(),
        payoff=proposal.payoff,
        not_tradeable_reason=proposal.not_tradeable_reason,
    )


def _arrow(
    draft: LinkDraft, source: PropositionId, target: PropositionId, found: tuple[Source, ...]
) -> tuple[Link, tuple[str, ...]]:
    """Mint an arrow from a draft, writing the word for where it came from ourselves.

    The two spans of time widen here from whole days to days as a number, which is
    the only shape change between a draft and the arrow it becomes: a model is
    asked for two days, and arithmetic on a timeline needs the half day.

    **The one place in this layer that builds an arrow.** A test reads the source
    to keep it so, which is what makes "no code path invents a bridge" a fact
    rather than a promise.

    Args:
        draft: The arrow as the model wrote it.
        source: The claim it starts at.
        target: The claim it ends at.
        found: What the search tool returned in that call.

    Returns:
        The arrow, and the addresses it cited that the search never returned.
    """
    kept, dropped = keep_cited(draft, found)
    arrow = Link(
        id=mint_id(),
        source=source,
        target=target,
        mode=draft.mode,
        strength=draft.strength,
        lag=float(draft.lag),
        shape=draft.shape,
        half_life=None if draft.half_life is None else float(draft.half_life),
        rationale=draft.rationale,
        sources=kept,
        provenance=provenance_of(draft, kept),
        reflexive=False,
    )
    return arrow, dropped


def _newly_wrong(before: Sequence[Violation], after: Sequence[Violation]) -> tuple[Violation, ...]:
    """Keep only the faults this proposal introduced, in the rules' own order.

    Args:
        before: What was wrong with the map already.
        after: What is wrong with the map the proposal would leave behind.

    Returns:
        The faults that are new, in the order the rules found them.
    """
    already = set(before)
    return tuple(fault for fault in after if fault not in already)


def _in_the_models_words(proposal: Proposal) -> str:
    """Quote what the model wrote, so a refusal names a claim rather than a code.

    Args:
        proposal: The proposal that was refused.

    Returns:
        The claim's own sentence, or an arrow's own reason.
    """
    if isinstance(proposal, ClaimProposal):
        return proposal.claim
    if isinstance(proposal, LinkProposal):
        return proposal.link.rationale
    return proposal.why
