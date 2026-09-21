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
    Insert,
    Link,
    Proposition,
    PropositionId,
    Source,
    Violation,
    validate,
)
from katalyst.engine.client import Answerer, AnswerWeCouldNotRead, TheModelDidNotAnswer
from katalyst.engine.grounding import found_in, keep_cited, provenance_of
from katalyst.engine.ids import mint_id
from katalyst.engine.outcome import Accepted, Caps, Outcome, Refused, Stopped, costing
from katalyst.engine.prompt import (
    adding_question,
    expanding_question,
    joining_question,
    starting_question,
)
from katalyst.engine.proposal import (
    ClaimProposal,
    LinkDraft,
    LinkProposal,
    Proposal,
    StartingClaim,
    Stop,
)
from katalyst.engine.receipt import fold, nothing_spent_yet, over_the_cap


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
    except (AnswerWeCouldNotRead, TheModelDidNotAnswer) as did_not_fit:
        # Two failures, one treatment: an answer we could not read and an answer
        # that never came are the same thing to a walk — a sentence to show and
        # count, never an exception to escape with (Kent, 2026-09-20).
        #
        # The answer never got as far as being read, so its counters never
        # reached us. The round trip is counted because it happened and it may
        # have been charged; its tokens are left at nothing, because nothing is
        # what we know. This is the one place the receipt is knowingly short, and
        # it is short by one call in a run of dozens.
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
    may_search: bool = True,
) -> Outcome:
    """Turn one sentence a person typed into a claim anybody could settle.

    Asked once for the sentence the map starts from, and once more for the place
    the person asked whether it gets to. It is a different question from expanding
    a map — what did they mean, rather than what happens next — so it has its own
    small shape and its own call. **Searching is allowed on it**, and spends from
    the same budget every other call spends from: what a person meant is not a
    thing to look up, but how often this kind of thing has happened before is
    exactly that, and this is the claim every number below it hangs off.

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
        may_search: Whether this run still has a whole call's worth of searches
            left to spend.

    Returns:
        The minted claim, or the reason there is not one, and what the call cost.
    """
    question = starting_question(sentence, is_the_hypothesis=is_the_hypothesis, today=on)
    try:
        said = answerer.starting_claim(question, may_search=may_search)
    except (AnswerWeCouldNotRead, TheModelDidNotAnswer) as did_not_fit:
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
    candidate, claim, arrows, dropped, no_class = _candidate_map(graph, proposal, found)
    introduced = newly_wrong(validate(graph), validate(candidate))
    if introduced:
        return Refused(claim_in_words=_in_the_models_words(proposal), violations=introduced)
    return Accepted(
        proposition=claim, links=arrows, sources_dropped=dropped, base_rate_dropped=no_class
    )


def _candidate_map(
    graph: Graph, proposal: ClaimProposal | LinkProposal, found: tuple[Source, ...]
) -> tuple[Graph, Proposition | None, tuple[Link, ...], tuple[str, ...], str | None]:
    """Put the proposal onto a copy of the map, minting what only we can mint.

    Args:
        graph: The map as it stands. It is never changed.
        proposal: A new claim with its arrow, or an arrow on its own.
        found: What the search tool returned in that call.

    Returns:
        The map the proposal would leave behind, the new claim if there is one,
        the arrows that arrived, the addresses that were dropped, and the
        reference class of a count that was thrown away, if one was.
    """
    if isinstance(proposal, LinkProposal):
        arrow, dropped = _arrow(proposal.link, proposal.source, proposal.target, found)
        return (
            graph.model_copy(update={"links": (*graph.links, arrow)}),
            None,
            (arrow,),
            dropped,
            None,
        )

    claim, no_class = _claim(proposal, found)
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
        no_class,
    )


def _claim(proposal: ClaimProposal, found: tuple[Source, ...]) -> tuple[Proposition, str | None]:
    """Mint a claim from a proposal, stamping the two things the model may not say.

    The identifier is ours, and so is the name on the likelihood.

    A base rate's addresses are kept by the same rule as an arrow's — only what
    the search returned survives — because an empty list there already means the
    count is the model's own recollection, and nothing downstream of it may claim
    to be documented.

    Args:
        proposal: The claim as the model wrote it.
        found: What the search tool returned in that call.

    **A count nothing backs is thrown away**, and the claim is accepted without
    it. The first measured run, on 2026-09-17, came back with eight counts like
    "12 of 15" and not one source behind any of them: a number that looks measured
    and is remembered is the state this product refuses to show, and an honest
    "no reference class" on the screen beats a precise-looking lie. Kent settled
    it on 2026-09-20. It is the same rule an arrow's citations are kept by, over
    the bare addresses a count carries.

    Returns:
        The claim, with an identifier nobody else could have given it, and the
        reference class of a count that was thrown away, if one was.
    """
    stated = Belief(p=proposal.prior.p, lo=proposal.prior.lo, hi=proposal.prior.hi, owner="model")
    base_rate = proposal.base_rate
    thrown_away: str | None = None
    if base_rate is not None:
        survived, _ = keep_cited(base_rate.sources, found)
        if survived:
            # A base rate keeps the addresses of what survived; an arrow keeps
            # the `Source` records. One rule, two shapes of answer.
            base_rate = base_rate.model_copy(update={"sources": tuple(one.url for one in survived)})
        else:
            thrown_away = base_rate.reference_class
            base_rate = None
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
    ), thrown_away


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
    kept, dropped = keep_cited(tuple(one.url for one in draft.sources), found)
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


def map_with(graph: Graph, accepted: Accepted) -> Graph:
    """Put what one accepted answer brought onto the map.

    Here rather than in `grow.py` because the walk now needs the map an answer
    *would* leave behind before it commits to it: an answer judged against the
    map as it stood at the start of a round has to be judged again against the
    map as it stands when it lands (2026-09-20).

    Args:
        graph: The map as it stands. It is never changed.
        accepted: The claim and arrows that were accepted.

    Returns:
        A new map with them on it.
    """
    claims = graph.propositions
    if accepted.proposition is not None:
        claims = (*claims, accepted.proposition)
    return graph.model_copy(
        update={"propositions": claims, "links": (*graph.links, *accepted.links)}
    )


def still_legal_on(graph: Graph, accepted: Accepted) -> tuple[Violation, ...]:
    """Say what the map's rules object to if this answer lands on the map as it now stands.

    The same question `_judge` asked when the answer came back, asked again at the
    moment the map actually changes. A round of three calls is judged against one
    snapshot, so two answers can each be legal against that snapshot and illegal
    together — a loop, or the same arrow twice. This is where that is caught.

    Args:
        graph: The map as it now stands.
        accepted: The claim and arrows that were accepted earlier.

    Returns:
        Every fault landing this answer would introduce, or nothing at all.
    """
    return newly_wrong(validate(graph), validate(map_with(graph, accepted)))


def newly_wrong(before: Sequence[Violation], after: Sequence[Violation]) -> tuple[Violation, ...]:
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


# --- Adding a claim somebody asked for --------------------------------------


def add_a_claim(
    graph: Graph,
    sentence: str,
    *,
    answerer: Answerer,
    on: date,
    width: int,
    may_search: bool = True,
    dollars: float | None = None,
) -> tuple[Insert | None, tuple[Outcome, ...]]:
    """Draft a claim somebody typed, join it to the map, and hand back one edit.

    **The one edit that needs a model**, and it needs no shape of its own. One
    call writes the sentence as a claim, using the same starting-claim shape the
    first claim of any map uses, with the map shown beside it. Then the ordinary
    machinery asks for its arrows **one per call**, each an ordinary arrow between
    two claims already on the map, each checked by the map's own rules exactly as
    any other proposal is, until the model says it is joined well enough or the
    width cap says enough.

    Nothing about the rest of the map is re-prompted: the one exception to "never
    re-prompt for a whole map" is this, over the claim it touches and not one
    claim more.

    Args:
        graph: The map the claim is going onto. It is never changed.
        sentence: What the person typed.
        answerer: Whatever this run asks its questions of.
        on: The day this is happening.
        width: How many arrows the new claim may have.
        may_search: Whether there are searches left to spend.
        dollars: What this edit may spend, in dollars. The same ceiling a whole
            run gets when not said, which is the right one: an edit is asked for
            by hand, one at a time, and there is no second loop above it.

    Returns:
        The edit, or nothing at all when the claim could not be written; and every
        call it took, so the money is counted whatever the answer was.
    """
    cap = Caps().dollars if dollars is None else dollars
    spent: list[Outcome] = []
    running = nothing_spent_yet()
    answerer.watching(running, cap)
    drafting = _drafted(graph, sentence, answerer=answerer, on=on, may_search=may_search)
    spent.append(drafting)
    running = fold(running, drafting)
    written = drafting.result
    if not isinstance(written, Accepted) or written.proposition is None:
        return None, tuple(spent)

    added = written.proposition
    joined: list[Link] = []
    so_far = graph.model_copy(update={"propositions": (*graph.propositions, added)})
    refused_in_a_row = 0
    for _ in range(width):
        if over_the_cap(running, cap):
            break
        answerer.watching(running, cap)
        outcome = expand_toward(so_far, added.id, answerer=answerer, on=on, may_search=may_search)
        spent.append(outcome)
        running = fold(running, outcome)
        result = outcome.result
        if isinstance(result, Stopped):
            break
        if not isinstance(result, Accepted):
            refused_in_a_row += 1
            if refused_in_a_row >= Caps().refusals_in_a_row:
                # It stops the way everything else stops. Three proposals in a
                # row refused for one claim is our willingness to keep paying for
                # that claim running out, and an edit is no different.
                break
            continue
        refused_in_a_row = 0
        joined.extend(result.links)
        so_far = so_far.model_copy(update={"links": (*so_far.links, *result.links)})

    if not joined:
        # A claim joined to nothing is not part of the story, and the map's own
        # rules would refuse it anyway. Say so by handing back nothing.
        return None, tuple(spent)
    return Insert(proposition=added, links=tuple(joined)), tuple(spent)


def expand_toward(
    graph: Graph,
    added: PropositionId,
    *,
    answerer: Answerer,
    on: date,
    may_search: bool = True,
) -> Outcome:
    """Ask for one arrow with a named claim at one end, and judge it like any other.

    The claim is named in the question rather than pinned by a field on a shape,
    because a shape is forever and a sentence is not.

    Args:
        graph: The map, with the new claim already on it.
        added: The claim the arrow must touch.
        answerer: Whatever this run asks its questions of.
        on: The day this is happening.
        may_search: Whether there are searches left to spend.

    Returns:
        What happened, and what the call cost.
    """
    question = joining_question(graph, added, today=on)
    try:
        said = answerer.proposal(question, may_search=may_search)
    except (AnswerWeCouldNotRead, TheModelDidNotAnswer) as did_not_fit:
        return Outcome(result=Refused(claim_in_words=did_not_fit.why), about=added, calls=1)
    if said.declined is not None:
        return costing(Refused(claim_in_words=said.declined), added, said)
    proposed = said.answered
    if isinstance(proposed, Stop):
        return costing(Stopped(why=proposed.why), added, said)
    if not isinstance(proposed, LinkProposal):
        return costing(
            Refused(
                claim_in_words=(
                    "This call asked for one arrow between two claims already on the "
                    "map, and the answer was something else."
                )
            ),
            added,
            said,
        )
    if added not in (proposed.source, proposed.target):
        return costing(
            Refused(
                claim_in_words=(
                    "This arrow does not touch the claim that was just added, so it "
                    "is not part of adding it."
                )
            ),
            added,
            said,
        )
    return costing(_judge(graph, proposed, found_in(said, on=on)), added, said)


def _drafted(
    graph: Graph, sentence: str, *, answerer: Answerer, on: date, may_search: bool
) -> Outcome:
    """Write one sentence somebody typed as a claim, with the map shown beside it."""
    question = adding_question(graph, sentence, today=on)
    try:
        said = answerer.starting_claim(question, may_search=may_search)
    except (AnswerWeCouldNotRead, TheModelDidNotAnswer) as did_not_fit:
        return Outcome(result=Refused(claim_in_words=did_not_fit.why), calls=1)
    if said.declined is not None:
        return costing(Refused(claim_in_words=said.declined), None, said)
    drafted = said.answered
    if not isinstance(drafted, StartingClaim):
        return costing(
            Refused(claim_in_words="The model gave no answer to this question."), None, said
        )
    return costing(
        Accepted(proposition=_starting_claim(drafted, is_the_hypothesis=False)), None, said
    )
