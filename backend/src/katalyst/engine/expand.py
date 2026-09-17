"""Growing a map one claim at a time, and being able to say why each one landed.

A person types a sentence. This file turns it into a map of claims and arrows by
asking a model the same small question over and over — *here is the map, here is
one claim on it, what is the one next piece?* — and deciding, in our own code,
what happens to each answer.

Read it top to bottom and every outcome has a reason:

1. **What one call leaves behind.** Three things can happen to a proposal, and
   nothing else can: it is accepted and minted, it is refused with every reason
   at once, or the model says this part of the story is finished.
2. **The caps.** Every limit a run has, as one set of arguments with defaults.
   Nothing here is a number buried in a function.
3. **Writing the receipt for an arrow.** Three small pure functions decide, from
   what the search tool actually returned, which of three words an arrow has
   earned. The model has no say in it, because the field is not on its shape.
4. **One call, one proposal.** `expand` — ask, read, build the map the answer
   would leave behind, and hand it to the map's own rules.
5. **The walk.** `grow` — which claim to ask about next, when to stop, and the
   one reason it gives for stopping.
6. **The Verify door.** `verdict` — a graded route to the place the person asked
   about, or an honest statement that there is none.

Two rules shape all of it
-------------------------
**The model proposes; our code disposes.** Nothing a model says is ever written
onto the map until `katalyst.domain` has looked at the map that answer would
leave behind and returned nothing wrong with it. And **reject, never repair**:
a proposal that breaks a rule comes back with every reason, in the rules' own
words, and is dropped. No arrow is quietly removed to break a loop, no date is
invented, no word is softened to make an arrow fit.

**After a refusal we ask again and say nothing.** Up to three fresh proposals for
one claim, and not one of them is told what was wrong with the last. Violation
text in a prompt would steer the model at our checks instead of at the truth, and
a check described to the thing it checks has stopped measuring anything.

What this file must never do
----------------------------
- Never write a claim or an arrow the model did not propose — not to make a map
  end somewhere, and not to make a Verify run reach its destination.
- Never talk over the network. It takes an answerer as an argument; `client.py`
  is the only thing that dials out.
- Never read a clock. The day a run happened is passed in, which is what lets a
  recorded run and a live one be compared.
- Never put a violation's words into a prompt.
"""

from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any, Literal, cast

from anthropic.types import ParsedMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from katalyst.domain import (
    Belief,
    Beliefs,
    Graph,
    Link,
    Proposition,
    PropositionId,
    Provenance,
    Source,
    Violation,
    validate,
)
from katalyst.domain.diff import PROVENANCE_WEIGHT
from katalyst.domain.validity import TERMINAL_KINDS
from katalyst.engine.client import Answerer
from katalyst.engine.ids import mint_id
from katalyst.engine.prompt import expanding_question, starting_question
from katalyst.engine.proposal import (
    ClaimProposal,
    LinkDraft,
    LinkProposal,
    Proposal,
    StartingClaim,
    Stop,
)
from katalyst.engine.receipt import (
    Receipt,
    fold,
    nothing_spent_yet,
    over_the_cap,
    what_it_spent_and_got,
)

# --- 1. What one call leaves behind ----------------------------------------


class Accepted(BaseModel):
    """A proposal that passed every rule, with the identifiers we minted for it."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["accepted"] = "accepted"
    proposition: Proposition | None = Field(
        default=None,
        description=(
            "The new claim, with the identifier we minted for it. Nothing at all "
            "when the answer was an arrow between two claims already on the map."
        ),
    )
    links: tuple[Link, ...] = Field(
        default=(),
        description=(
            "The arrows that arrived with it, each with an identifier we minted "
            "and a word for where it came from that we wrote."
        ),
    )
    sources_dropped: tuple[str, ...] = Field(
        default=(),
        description=(
            "Addresses the answer cited that the search tool never returned in "
            "that call. They are not behind anything, and this is where a reader "
            "is told so."
        ),
    )


class Refused(BaseModel):
    """A proposal that did not become part of the map, and every reason why.

    Three different things arrive this way, and the list of violations tells them
    apart. A proposal the map's own rules turned down carries those rules' own
    sentences. A call the model declined to answer, and an answer that did not fit
    the shape we asked for, carry **no** violations — there is no fault in a map to
    name, because no map was proposed — and the plain sentence of what happened is
    in `claim_in_words` instead.

    A refusal is an event a person sees, not an error they are spared. A
    generation that hides its misses has deleted half the product.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["refused"] = "refused"
    claim_in_words: str = Field(
        description=(
            "What the model wrote, or the plain sentence of what happened when it "
            "wrote nothing we could read. Never minted, never drawn as a tile."
        )
    )
    violations: tuple[Violation, ...] = Field(
        default=(),
        description=(
            "Everything the map's own rules found wrong with the map this answer "
            "would have left behind, in their words. Empty when no map was "
            "proposed at all."
        ),
    )


class Stopped(BaseModel):
    """The model has nothing more to add on this line."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["stopped"] = "stopped"
    why: str = Field(
        description="One plain sentence saying why this part of the story is finished."
    )


class Outcome(BaseModel):
    """What one call to the model left behind: what happened, and what it cost.

    The counters are what `receipt.py` folds into the run's one receipt, and what
    the spending cap is checked against after every call. **An outcome must never
    be thrown away**: a call that cost money and is not counted is money the
    receipt cannot account for.

    `calls` counts round trips rather than questions. A question whose answer came
    back part finished is sent straight back to be continued, and each trip is on
    the bill.
    """

    model_config = ConfigDict(frozen=True)

    result: Accepted | Refused | Stopped = Field(discriminator="kind")
    frontier: PropositionId | None = Field(
        default=None,
        description=(
            "The claim this call was asking about, so a reader can follow a "
            "refusal back to the question that produced it. Nothing at all on the "
            "two calls that turn a person's own sentences into claims."
        ),
    )
    calls: int = Field(default=1, description="How many round trips this question took.")
    searches: int = Field(default=0, description="How many web searches it ran.")
    input_tokens: int = Field(default=0, description="Tokens of question read fresh.")
    output_tokens: int = Field(default=0, description="Tokens of answer written.")
    cache_read_tokens: int = Field(default=0, description="Tokens recognised from an earlier call.")
    cache_write_tokens: int = Field(default=0, description="Tokens written into the cache.")


StoppingReason = Literal[
    "spend_cap",
    "no_terminal",
    "claim_cap",
    "depth_cap",
    "width_cap",
    "model_stopped",
    "reached_terminal",
]
"""The seven reasons a walk can give for stopping, in the order `_why_it_stopped` tries them.

Reaching the cap on searches is deliberately not one of them. Running out of
searches turns searching off and the map keeps building; the arrows added
afterwards say they argued rather than documented, and the origin marks on screen
show where the evidence thins out. A limit on the bill is not a fact about the
world, so it is not a reason a story ended.
"""


class Finished(BaseModel):
    """The last thing a walk hands back: what was built, why it stopped, what it cost.

    Exactly one of these comes out of every walk, and it always comes last.
    """

    model_config = ConfigDict(frozen=True)

    reason: StoppingReason = Field(
        description="Why the walk stopped. One reason, chosen by the order in `_why_it_stopped`."
    )
    why: str = Field(description="That reason in one plain sentence, for a person to read.")
    graph: Graph | None = Field(
        default=None,
        description=(
            "The map that was built. Nothing at all when the very first question — "
            "turning the person's own sentence into a claim — never came back with "
            "something we could use."
        ),
    )
    receipt: Receipt = Field(description="What the whole run spent.")
    claims: int = Field(default=0, description="How many claims the map ended up with.")
    links: int = Field(default=0, description="How many arrows.")
    refused: int = Field(default=0, description="How many proposals were refused along the way.")
    destination: PropositionId | None = Field(
        default=None,
        description=(
            "The claim the person asked whether the story reaches, when they named "
            "one. Handed back so the caller can grade the route once the numbers "
            "have been worked through the map. Whether the route exists is said "
            "once, on the verdict, and nowhere else."
        ),
    )


# --- 2. The caps ------------------------------------------------------------


class Caps(BaseModel):
    """Every limit a run has, in one place, each with a default and a reason.

    They are arguments rather than constants so that a test can set them low, an
    evaluation can set them where the measurement wants them, and nobody has to
    read a function body to find out what stopped a run.
    """

    model_config = ConfigDict(frozen=True)

    depth: int = Field(default=5, description="How many layers a line may run from the hypothesis.")
    width: int = Field(default=3, description="How many claims one claim may cause.")
    claims: int = Field(default=30, description="How large the map may get.")
    refusals_in_a_row: int = Field(
        default=3,
        description=(
            "How many proposals for one claim may be refused before that claim is "
            "closed. Every attempt that did not end in an accepted proposal counts."
        ),
    )
    at_once: int = Field(default=3, description="How many lines are expanded at the same time.")
    searches: int = Field(
        default=30,
        description=(
            "How many web searches the whole run may make. It is the claims cap: "
            "one search's worth of budget for each claim the map is allowed to "
            "hold, so it adds no new number to the product. Reaching it turns "
            "searching off; it never ends the run."
        ),
    )
    dollars: float = Field(
        default=15.0, description="What one run may spend before it stops (Kent, 2026-09-17)."
    )


# --- 3. Writing the receipt for an arrow ------------------------------------


def found_in(answer: ParsedMessage[Any], *, on: date) -> tuple[Source, ...]:
    """Every address the search tool itself returned during this one call.

    One source per search result the answer carries, with the day the call ran
    written onto it. This is the only place a source is built during generation.

    It must never include an address that came from the model's own text. The
    whole rule rests on this function reading the tool's results and nothing else.

    A search that failed comes back as one error object where a list of results
    would be, which reads here as nothing found.

    Args:
        answer: One round trip's answer, as the service returned it.
        on: The day the call ran, which is the day these were fetched.

    Returns:
        One source per result, in the order the tool returned them.
    """
    found: list[Source] = []
    for block in answer.content:
        if block.type != "web_search_tool_result":
            continue
        results = block.content
        if not isinstance(results, list):
            continue  # The tool reported an error instead of results.
        found.extend(
            Source(url=result.url, title=result.title, retrieved=on)
            for result in results
            if result.type == "web_search_result"
        )
    return tuple(found)


def keep_cited(
    draft: LinkDraft, found: tuple[Source, ...]
) -> tuple[tuple[Source, ...], tuple[str, ...]]:
    """Split what an arrow cites into what we can stand behind, and what we drop.

    Matching is an exact comparison of the address, after trimming surrounding
    whitespace and one trailing slash. Nothing cleverer: deciding that two
    slightly different addresses are "the same page" is a judgement, and a
    judgement is how a dropped citation quietly comes back.

    A dropped address is never repaired, guessed at, or fetched to see whether it
    was real. It is dropped, and a reader is told which one.

    Args:
        draft: The arrow as the model wrote it, with the addresses it cited.
        found: What the search tool returned in that same call.

    Returns:
        The sources the search actually returned, in the order the model cited
        them, and the addresses it cited that the search never returned.
    """
    by_address = {_same_address(source.url): source for source in found}
    kept: list[Source] = []
    dropped: list[str] = []
    for cited in draft.sources:
        match = by_address.get(_same_address(cited.url))
        if match is None:
            dropped.append(cited.url)
        elif match not in kept:
            kept.append(match)
    return tuple(kept), tuple(dropped)


def provenance_of(draft: LinkDraft, kept: tuple[Source, ...]) -> Provenance:
    """Say which word this arrow has earned, from what actually happened.

    Three words and one question with a checkable answer: did the search tool
    itself hand us at least one of the addresses this arrow cites?

    `documented` when at least one cited source survived; otherwise `argued` when
    the arrow states a mechanism; otherwise `asserted`.

    It never reads anything the model said about its own confidence, and it never
    returns the four words that belong to somebody else: a study of past cases, a
    live price, a person, and a probe each write their own.

    In practice no arrow this pipeline accepts is ever `asserted`, because every
    arrow must carry a mechanism and the map's own rules refuse one that does not.
    The word is written here anyway, a moment before that refusal, because the
    alternative is a judgement about whether a sentence is a good enough
    mechanism — and grading prose is exactly what we refuse to ask code to do.

    Args:
        draft: The arrow as the model wrote it.
        kept: The sources that survived `keep_cited`.

    Returns:
        One of three words.
    """
    if kept:
        return "documented"
    if draft.rationale.strip():
        return "argued"
    return "asserted"


def _same_address(url: str) -> str:
    """Put one address into the form two addresses are compared in.

    Surrounding whitespace and one trailing slash come off, and nothing else. A
    page written with something extra on the end — a tracking parameter, say —
    loses its citation and the arrow falls back to saying it argued rather than
    documented. That is the safe direction to be wrong in.

    Args:
        url: The address as it was written.

    Returns:
        The form used for comparison. Never shown to anybody.
    """
    return url.strip().rstrip("/")


# --- 4. One call, one proposal ---------------------------------------------


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

    Nothing here changes the map it was given. A proposal is a candidate map that
    either wins or loses, so a refusal leaves the map a person is looking at
    exactly as it was.

    Args:
        graph: The map as it stands.
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
    question = expanding_question(graph, frontier, target=target, ending_only=ending_only)
    try:
        rounds = answerer.proposal(question, may_search=may_search)
    except ValidationError as did_not_fit:
        return Outcome(
            result=Refused(claim_in_words=_did_not_fit_the_shape(did_not_fit)),
            frontier=frontier,
            # The answer never got as far as being read, so its counters never
            # reached us. The round trip is counted because it happened and it was
            # charged; its tokens are left at nothing, because nothing is what we
            # know. This is the one place the receipt is knowingly short, and it
            # is short by one call in a run of dozens.
            calls=1,
        )

    answer = rounds[-1]
    counted = _what_it_cost(rounds)
    declined = _declined(answer)
    if declined is not None:
        return _outcome(Refused(claim_in_words=declined), frontier, counted)

    proposal = answer.parsed_output
    if proposal is None:
        return _outcome(
            Refused(claim_in_words="The model gave no answer to this question."), frontier, counted
        )
    if isinstance(proposal, Stop):
        return _outcome(Stopped(why=proposal.why), frontier, counted)

    found = _everything_the_search_returned(rounds, on=on)
    return _outcome(_judge(graph, proposal, found), frontier, counted)


def start_the_map(
    sentence: str,
    *,
    is_the_hypothesis: bool,
    answerer: Answerer,
) -> Outcome:
    """Turn one sentence a person typed into a claim anybody could settle.

    Asked once for the sentence the map starts from, and once more for the place
    the person asked whether it gets to. It is a different question from expanding
    a map — what did they mean, rather than what happens next — so it has its own
    small shape and its own call, and the search tool is not declared: the web has
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

    Returns:
        The minted claim, or the reason there is not one, and what the call cost.
    """
    question = starting_question(sentence, is_the_hypothesis=is_the_hypothesis)
    try:
        rounds = answerer.starting_claim(question)
    except ValidationError as did_not_fit:
        return Outcome(result=Refused(claim_in_words=_did_not_fit_the_shape(did_not_fit)), calls=1)

    answer = rounds[-1]
    counted = _what_it_cost(rounds)
    declined = _declined(answer)
    if declined is not None:
        return _outcome(Refused(claim_in_words=declined), None, counted)

    drafted = answer.parsed_output
    if drafted is None:
        return _outcome(
            Refused(claim_in_words="The model gave no answer to this question."), None, counted
        )
    minted = _starting_claim(drafted, is_the_hypothesis)
    return _outcome(Accepted(proposition=minted), None, counted)


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

    Four things our code adds that the model could not have: the new claim's
    identifier, the arrow's identifier, whose the likelihood is, and the word for
    where the arrow came from. All four are stamped before the map is checked.

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
        return (
            graph.model_copy(update={"links": (*graph.links, arrow)}),
            None,
            (arrow,),
            dropped,
        )

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

    The identifier is ours, and so is the name on the likelihood. The likelihood
    itself stands exactly as the model wrote it: there is no ensemble here, no
    widening because stated ranges are known to run narrow, and no second opinion
    averaged in. What is on the chip is what was said, labelled as what it is.

    A base rate's addresses are kept by the same rule as an arrow's — only what
    the search returned survives — because an empty list there already means the
    count is the model's own recollection.

    Args:
        proposal: The claim as the model wrote it.
        found: What the search tool returned in that call.

    Returns:
        The claim, with an identifier nobody else could have given it.
    """
    stated = Belief(p=proposal.prior.p, lo=proposal.prior.lo, hi=proposal.prior.hi, owner="model")
    base_rate = proposal.base_rate
    if base_rate is not None:
        by_address = {_same_address(source.url) for source in found}
        base_rate = base_rate.model_copy(
            update={
                "sources": tuple(
                    url for url in base_rate.sources if _same_address(url) in by_address
                )
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


def _declined(answer: ParsedMessage[Any]) -> str | None:
    """Say, in plain words, that the model declined the question — or that it did not.

    The vendor's own safety check can turn a call down. That comes back as an
    ordinary answer with a stop reason saying so, and sometimes with an
    explanation. It is surfaced as a refusal a person sees, never hidden and never
    quietly re-routed to a different model.

    Args:
        answer: The last round trip's answer.

    Returns:
        One plain sentence, or nothing at all when the model did not decline.
    """
    if answer.stop_reason != "refusal":
        return None
    details = answer.stop_details
    if details is not None and details.explanation:
        return f"The model declined to answer this question. It said: {details.explanation}"
    return "The model declined to answer this question."


def _did_not_fit_the_shape(problem: ValidationError) -> str:
    """Say, in plain words, that the answer did not fit the shape we asked for.

    Nothing technical reaches a screen. The field names are the same words this
    spec uses for those fields, so naming them helps rather than mystifies.

    Args:
        problem: What the shape check objected to.

    Returns:
        One plain sentence.
    """
    fields = sorted(
        {
            ".".join(str(step) for step in fault["loc"] if not str(step).startswith("function-"))
            for fault in problem.errors()
        }
    )
    named = ", ".join(field for field in fields if field)
    if not named:
        return "The model's answer did not fit the shape this call asked for."
    return f"The model's answer did not fit the shape this call asked for, at: {named}."


def _everything_the_search_returned(
    rounds: Sequence[ParsedMessage[Any]], *, on: date
) -> tuple[Source, ...]:
    """Gather the tool's results across every round trip one question took.

    A question sent back to be continued can search on either trip, so the result
    set is the whole question's, not the last trip's.

    Args:
        rounds: Every round trip, oldest first.
        on: The day the call ran.

    Returns:
        One source per result, in the order the tool returned them, with any
        address that came back twice kept once.
    """
    found: list[Source] = []
    seen: set[str] = set()
    for one in rounds:
        for source in found_in(one, on=on):
            if _same_address(source.url) in seen:
                continue
            seen.add(_same_address(source.url))
            found.append(source)
    return tuple(found)


class _WhatItCost(BaseModel):
    """The counters of one question, before they are put on an outcome."""

    model_config = ConfigDict(frozen=True)

    calls: int
    searches: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int


def _what_it_cost(rounds: Sequence[ParsedMessage[Any]]) -> _WhatItCost:
    """Add up what every round trip of one question cost.

    Args:
        rounds: Every round trip, oldest first.

    Returns:
        The counters for the whole question.
    """
    return _WhatItCost(
        calls=len(rounds),
        searches=sum(
            one.usage.server_tool_use.web_search_requests if one.usage.server_tool_use else 0
            for one in rounds
        ),
        input_tokens=sum(one.usage.input_tokens for one in rounds),
        output_tokens=sum(one.usage.output_tokens for one in rounds),
        cache_read_tokens=sum(one.usage.cache_read_input_tokens or 0 for one in rounds),
        cache_write_tokens=sum(one.usage.cache_creation_input_tokens or 0 for one in rounds),
    )


def _outcome(
    result: Accepted | Refused | Stopped, frontier: PropositionId | None, cost: _WhatItCost
) -> Outcome:
    """Put what happened and what it cost together into one outcome."""
    return Outcome(
        result=result,
        frontier=frontier,
        calls=cost.calls,
        searches=cost.searches,
        input_tokens=cost.input_tokens,
        output_tokens=cost.output_tokens,
        cache_read_tokens=cost.cache_read_tokens,
        cache_write_tokens=cost.cache_write_tokens,
    )


# --- 5. The walk ------------------------------------------------------------


def grow(
    hypothesis: str,
    *,
    target: str | None = None,
    answerer: Answerer,
    on: date,
    caps: Caps | None = None,
) -> Iterator[Outcome | Finished]:
    """Walk the frontier, one round at a time, until something stops it.

    Hands back every outcome as it is folded in, oldest first, and then exactly
    one `Finished`, always last. Nothing is buffered: a caller can draw the map as
    it arrives.

    **How the order is fixed, even though three claims are asked at once.** A
    round takes the first few open claims in frontier order and asks about them at
    the same time. Their answers are then folded **in that same frontier order**,
    whichever came back first, so the map that results depends on the answers and
    never on the weather. New claims join the end of the frontier as their parents
    are folded, so the frontier's order is fixed too.

    The first round asks about one claim — the one the map started from — which is
    also what lets the standing half of the request be written into the service's
    cache before anything is asked in parallel. Calls sent at the same moment
    cannot read what each other are still writing.

    **The spending cap is checked after every call.** Because a round's calls are
    already in flight when the first of them is folded, a run can pass its ceiling
    by at most the calls that were in the air with it. The check is after every
    folded answer, and no further round is started once it trips.

    Args:
        hypothesis: The sentence the person typed.
        target: The place they asked whether it gets to, in their own words, or
            nothing at all on the Explore door.
        answerer: Whatever this run asks its questions of.
        on: The day this run is happening. Passed in rather than read, which is
            what lets a recorded run and a live one be compared.
        caps: Every limit this run has. The defaults are in `Caps`.

    Yields:
        Each call's outcome in the order it was folded, then one `Finished`.
    """
    caps = caps or Caps()
    receipt = nothing_spent_yet()
    refused = 0

    # The claim the map starts from, and the destination when there is one.
    first, receipt, refused, spent = yield from _keep_asking(
        lambda: start_the_map(hypothesis, is_the_hypothesis=True, answerer=answerer),
        receipt,
        refused,
        caps,
    )
    if first is None:
        yield Finished(
            reason="model_stopped",
            why=(
                "This run never got started: the sentence could not be written as "
                "a claim anybody could settle."
            ),
            receipt=receipt,
            refused=refused,
        )
        return
    graph = Graph(id=mint_id(), propositions=(first,), links=(), hypothesis_id=first.id)

    destination: PropositionId | None = None
    if target is not None and not spent:
        wanted, receipt, refused, spent = yield from _keep_asking(
            lambda: start_the_map(target, is_the_hypothesis=False, answerer=answerer),
            receipt,
            refused,
            caps,
        )
        if wanted is not None:
            graph = graph.model_copy(update={"propositions": (*graph.propositions, wanted)})
            destination = wanted.id

    # The walk itself.
    frontier: list[PropositionId] = [first.id]
    layer: dict[PropositionId, int] = {first.id: 0}
    pieces: dict[PropositionId, int] = {}
    refusals_here: dict[PropositionId, int] = {}
    closed_by: dict[PropositionId, str] = {}
    stopped_for: str | None = "spend_cap" if spent else None

    with ThreadPoolExecutor(max_workers=caps.at_once) as pool:
        while stopped_for is None:
            frontier = _still_has_room(frontier, layer, pieces, closed_by, caps)
            if not frontier:
                break
            if len(graph.propositions) >= caps.claims:
                for claim_id in frontier:
                    closed_by[claim_id] = "claim_cap"
                stopped_for = "claim_cap"
                break

            asking = frontier[: caps.at_once]
            answers = _ask_about_each(
                pool,
                graph,
                asking,
                target=target,
                answerer=answerer,
                on=on,
                may_search=receipt.searches < caps.searches,
            )
            for claim_id, outcome in zip(asking, answers, strict=True):
                receipt = fold(receipt, outcome)
                yield outcome
                graph, refused = _fold_in(
                    graph,
                    claim_id,
                    outcome,
                    frontier,
                    layer,
                    pieces,
                    refusals_here,
                    closed_by,
                    caps,
                    refused,
                )
                if over_the_cap(receipt, caps.dollars):
                    stopped_for = "spend_cap"
                    break

        # One last call per open line, asking only for an ending.
        if stopped_for != "spend_cap" and not _ends_somewhere(graph):
            for claim_id in _lines_with_no_ending(graph):
                if over_the_cap(receipt, caps.dollars):
                    stopped_for = "spend_cap"
                    break
                outcome = expand(
                    graph,
                    claim_id,
                    target=target,
                    answerer=answerer,
                    on=on,
                    may_search=receipt.searches < caps.searches,
                    ending_only=True,
                )
                receipt = fold(receipt, outcome)
                yield outcome
                graph, refused = _fold_in(
                    graph,
                    claim_id,
                    outcome,
                    [],
                    layer,
                    pieces,
                    refusals_here,
                    closed_by,
                    caps,
                    refused,
                )

    reason = _why_it_stopped(stopped_for, _lines_that_ended_short(graph, closed_by), graph)
    yield Finished(
        reason=reason,
        why=_in_one_sentence(reason, receipt, caps, graph),
        graph=graph,
        receipt=receipt,
        claims=len(graph.propositions),
        links=len(graph.links),
        refused=refused,
        destination=destination,
    )


def _keep_asking(ask: Any, receipt: Receipt, refused: int, caps: Caps) -> Any:
    """Ask for a starting claim until one comes back, or until the tries run out.

    The same rule as everywhere else: up to three attempts, none of them told what
    was wrong with the last.

    Args:
        ask: The question to put, as something that can be called again.
        receipt: What the run has spent so far.
        refused: How many proposals have been refused so far.
        caps: This run's limits.

    Yields:
        Each attempt's outcome.

    Returns:
        The claim or nothing at all, the receipt, the refusal tally, and whether
        the run has already spent its ceiling.
    """
    for _ in range(caps.refusals_in_a_row):
        outcome = ask()
        receipt = fold(receipt, outcome)
        yield outcome
        spent = over_the_cap(receipt, caps.dollars)
        result = outcome.result
        if isinstance(result, Accepted) and result.proposition is not None:
            return result.proposition, receipt, refused, spent
        refused += 1
        if spent:
            return None, receipt, refused, True
    return None, receipt, refused, False


def _still_has_room(
    frontier: list[PropositionId],
    layer: dict[PropositionId, int],
    pieces: dict[PropositionId, int],
    closed_by: dict[PropositionId, str],
    caps: Caps,
) -> list[PropositionId]:
    """Close every open claim that has run out of layers or out of room beside it.

    Both are our limits rather than the model's judgement, so the person hears
    about them under their own names.

    The width cap counts every piece a claim has been allowed to add — a claim it
    caused, or an arrow proposed while we were asking about it — because a cap
    that counted only one of the two could be walked past for ever by proposing
    the other.

    Args:
        frontier: The claims still open, in order.
        layer: How far each claim sits from the one the map started at.
        pieces: How many pieces each claim has added.
        closed_by: Which cap closed each claim that is closed. Written to here.
        caps: This run's limits.

    Returns:
        The claims still open, in the same order.
    """
    open_still: list[PropositionId] = []
    for claim_id in frontier:
        if layer[claim_id] >= caps.depth:
            closed_by[claim_id] = "depth_cap"
        elif pieces.get(claim_id, 0) >= caps.width:
            closed_by[claim_id] = "width_cap"
        else:
            open_still.append(claim_id)
    return open_still


def _ask_about_each(
    pool: ThreadPoolExecutor,
    graph: Graph,
    asking: Sequence[PropositionId],
    *,
    target: str | None,
    answerer: Answerer,
    on: date,
    may_search: bool,
) -> list[Outcome]:
    """Ask about several claims at the same time, and hand the answers back in order.

    The answers are read out in the order the questions were asked, not in the
    order they came back, which is what makes a run's shape depend on its answers
    rather than on how fast each one arrived.

    Args:
        pool: Where the questions are run.
        graph: The map as it stood at the start of this round.
        asking: The claims to ask about, in frontier order.
        target: The destination in the person's own words, or nothing at all.
        answerer: Whatever this run asks its questions of.
        on: The day this run is happening.
        may_search: Whether this run still has searches left to spend.

    Returns:
        One outcome per claim, in the same order.
    """
    in_flight = [
        pool.submit(
            expand,
            graph,
            claim_id,
            target=target,
            answerer=answerer,
            on=on,
            may_search=may_search,
        )
        for claim_id in asking
    ]
    return [one.result() for one in in_flight]


def _fold_in(
    graph: Graph,
    claim_id: PropositionId,
    outcome: Outcome,
    frontier: list[PropositionId],
    layer: dict[PropositionId, int],
    pieces: dict[PropositionId, int],
    refusals_here: dict[PropositionId, int],
    closed_by: dict[PropositionId, str],
    caps: Caps,
    refused: int,
) -> tuple[Graph, int]:
    """Put one answer onto the map, and decide whether its claim stays open.

    Args:
        graph: The map as it stands.
        claim_id: The claim this answer was about.
        outcome: What happened to it.
        frontier: The claims still open. Changed in place.
        layer: How far each claim sits from the one the map started at.
        pieces: How many pieces each claim has added.
        refusals_here: How many proposals in a row have been refused for a claim.
        closed_by: Why each closed claim closed.
        caps: This run's limits.
        refused: How many proposals have been refused so far.

    Returns:
        The map, and the refusal tally.
    """
    result = outcome.result

    if isinstance(result, Stopped):
        closed_by[claim_id] = "model_stopped"
        _close(frontier, claim_id)
        return graph, refused

    if isinstance(result, Refused):
        refused += 1
        refusals_here[claim_id] = refusals_here.get(claim_id, 0) + 1
        if refusals_here[claim_id] >= caps.refusals_in_a_row:
            closed_by[claim_id] = "model_stopped"
            _close(frontier, claim_id)
        return graph, refused

    refusals_here[claim_id] = 0
    pieces[claim_id] = pieces.get(claim_id, 0) + 1
    claims = graph.propositions
    if result.proposition is not None:
        claims = (*claims, result.proposition)
        layer[result.proposition.id] = layer[claim_id] + 1
        if result.proposition.kind not in TERMINAL_KINDS:
            # An ending never joins the frontier: there is nothing downstream of
            # a trade.
            frontier.append(result.proposition.id)
    return (
        graph.model_copy(update={"propositions": claims, "links": (*graph.links, *result.links)}),
        refused,
    )


def _close(frontier: list[PropositionId], claim_id: PropositionId) -> None:
    """Take one claim off the frontier, if it is still on it."""
    if claim_id in frontier:
        frontier.remove(claim_id)


def _ends_somewhere(graph: Graph) -> bool:
    """Say whether this map ends anywhere a person could act on."""
    return any(claim.kind in TERMINAL_KINDS for claim in graph.propositions)


def _lines_with_no_ending(graph: Graph) -> list[PropositionId]:
    """List the claims a last, ending-seeking call should be made about.

    A line that could still end somewhere is one the story actually reaches, that
    is not itself an ending, and that nothing follows on from. A destination the
    story never reached is deliberately not one of these: it is not part of the
    story, and growing an ending off it would answer a question nobody asked.

    Args:
        graph: The map as it stands.

    Returns:
        Those claims, in a fixed order.
    """
    onward: dict[PropositionId, list[PropositionId]] = {}
    for arrow in graph.links:
        onward.setdefault(arrow.source, []).append(arrow.target)

    reached = {graph.hypothesis_id}
    waiting = [graph.hypothesis_id]
    while waiting:
        here = waiting.pop()
        for next_claim in onward.get(here, []):
            if next_claim not in reached:
                reached.add(next_claim)
                waiting.append(next_claim)

    return sorted(
        claim.id
        for claim in graph.propositions
        if claim.id in reached and claim.kind not in TERMINAL_KINDS and not onward.get(claim.id)
    )


def _lines_that_ended_short(graph: Graph, closed_by: Mapping[PropositionId, str]) -> set[str]:
    """List the ways a line closed **without** ever reaching an ending.

    A claim that closed while something further down it still ran on to an ending
    did not end the story short — the story got where it was going, and which
    claim happened to close last is not what a reader wants told. So a closing
    counts here only when nothing downstream of that claim ends anywhere a person
    could act on.

    Args:
        graph: The finished map.
        closed_by: Why each closed claim closed.

    Returns:
        The set of reasons that closed a line short. Empty when every line ran to
        an ending.
    """
    onward: dict[PropositionId, list[PropositionId]] = {}
    for arrow in graph.links:
        onward.setdefault(arrow.source, []).append(arrow.target)
    kinds = {claim.id: claim.kind for claim in graph.propositions}

    short: set[str] = set()
    for claim_id, closing in closed_by.items():
        reached = _walk_onward(onward, claim_id)
        if not any(kinds.get(one) in TERMINAL_KINDS for one in reached):
            short.add(closing)
    return short


def _walk_onward(
    onward: Mapping[PropositionId, list[PropositionId]], start: PropositionId
) -> set[PropositionId]:
    """List every claim reached by following arrows out of one claim, itself included."""
    reached = {start}
    waiting = [start]
    while waiting:
        here = waiting.pop()
        for next_claim in onward.get(here, []):
            if next_claim not in reached:
                reached.add(next_claim)
                waiting.append(next_claim)
    return reached


def _why_it_stopped(stopped_for: str | None, ended_short: set[str], graph: Graph) -> StoppingReason:
    """Pick the one reason a run gives for stopping.

    The first of these that applies wins, and the order is the whole rule:

    1. **The money ran out.** Checked before anything else, because it is the one
       limit that stops the run wherever it happens to be.
    2. **The map ends nowhere you can act on**, even after the last
       ending-seeking call. It is the most important thing a reader can be told
       about a finished map.
    3. **The map filled up.** The claim cap stopped the whole walk, the way the
       money running out does, so it is read off what stopped the walk rather
       than off any one claim.
    4. **One of our caps cut a line short** — the depth cap, then the width cap.
       Our limit, so the person hears about it before the model's judgement.
    5. **A line stopped short by itself** — the model had nothing more to add
       there, or three proposals in a row were refused.
    6. **Every line ran to an ending.** The ordinary, good ending.

    Every line-level reason above counts only where that line never reached an
    ending. A claim that closed while something further down it ran on to a trade
    did not end the story short, and which claim happened to close last is not
    what a reader wants told.

    Reaching the cap on searches is not in the list. It turns searching off and
    the map keeps building, so it never ends a run.

    Args:
        stopped_for: The run-wide limit that ended the walk, if one did.
        ended_short: The ways a line closed without reaching an ending.
        graph: The finished map.

    Returns:
        One reason.
    """
    if stopped_for == "spend_cap":
        return "spend_cap"
    if not _ends_somewhere(graph):
        return "no_terminal"
    if stopped_for == "claim_cap":
        return "claim_cap"
    for cap in ("depth_cap", "width_cap"):
        if cap in ended_short:
            return cast(StoppingReason, cap)
    if "model_stopped" in ended_short:
        return "model_stopped"
    return "reached_terminal"


def _in_one_sentence(
    reason: StoppingReason, receipt: Receipt, caps: Caps, graph: Graph | None
) -> str:
    """Say why the run stopped, in words a person reads.

    Args:
        reason: The reason chosen by `_why_it_stopped`.
        receipt: What the run spent.
        caps: This run's limits, so a sentence can name the one it reached.
        graph: The map that was built.

    Returns:
        One plain sentence. Never a code and never a stack trace.
    """
    claims = 0 if graph is None else len(graph.propositions)
    links = 0 if graph is None else len(graph.links)
    if reason == "spend_cap":
        return what_it_spent_and_got(receipt, caps.dollars, claims, links)
    if reason == "no_terminal":
        return (
            "This map does not end anywhere you can act on. Every line that was "
            "still open was asked for an ending, and none came back."
        )
    if reason == "claim_cap":
        return f"This map reached its limit of {caps.claims} claims and stopped growing."
    if reason == "depth_cap":
        return (
            f"At least one line reached its limit of {caps.depth} layers from the "
            "claim this started at."
        )
    if reason == "width_cap":
        return f"At least one claim reached its limit of {caps.width} pieces hanging off it."
    if reason == "model_stopped":
        return (
            "At least one line stopped short: the model had nothing more to add "
            "there, or three proposals in a row were refused."
        )
    return "Every line ran to an ending."


# --- 6. The Verify door -----------------------------------------------------


class Verdict(BaseModel):
    """Whether the story reached the place the person asked about.

    One of two answers, and never a third. There is no code path anywhere in this
    file that adds an arrow to make a route exist: the map only ever holds what a
    proposal contained, so an honest "there is no route" is the only other thing
    this can say.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["reached", "no_path"] = Field(
        description="Whether a route from the starting claim to the destination exists."
    )
    path: tuple[PropositionId, ...] = Field(
        default=(), description="The route, claim by claim. Empty when there is none."
    )
    product: float | None = Field(
        default=None,
        description=(
            "The likelihoods along that route multiplied together. Nothing at all "
            "until the numbers have been worked through the map."
        ),
    )
    nearest: PropositionId | None = Field(
        default=None,
        description=(
            "When there is no route: the claim the story did reach that sits "
            "closest to the destination, or — when nothing on the map touches the "
            "destination at all — the furthest the story got. The sentence beside "
            "it says which of the two it is."
        ),
    )
    why: str = Field(description="The answer in one plain sentence, for a person to read.")


def verdict(
    graph: Graph,
    destination: PropositionId,
    *,
    beliefs: Mapping[PropositionId, Belief] | None = None,
) -> Verdict:
    """Grade the route from the claim the map started at to the destination.

    The route shown is the **best-backed** one: over every route, the one whose
    weakest arrow is strongest. That is the same rule the change list's ranking
    and the Inspector's path bar already use — one way of choosing a route, used
    three times — and it means the route a reader is shown is the best case they
    are entitled to, rather than the shortest.

    An honest caveat belongs beside the multiplied-out number wherever it is
    shown: it multiplies likelihoods each read on a different day, so it is not a
    joint probability.

    Args:
        graph: The finished map.
        destination: The claim the person asked whether the story reaches.
        beliefs: The worked-through likelihood of every claim, when the numbers
            have been run. Without them the route is still graded structurally and
            the multiplied-out number is absent rather than invented.

    Returns:
        A route and its number, or an honest statement that there is none.
    """
    route = _best_backed_route(graph, graph.hypothesis_id, destination)
    claims = {claim.id: claim for claim in graph.propositions}
    wanted = claims[destination].claim

    if route:
        return Verdict(
            kind="reached",
            path=route,
            product=_multiplied_out(route, beliefs),
            why=(
                f"The story reaches {wanted} in {len(route) - 1} steps, along the "
                "best-backed route on this map."
            ),
        )

    touching, hops = _nearest_to(graph, destination)
    if touching is not None:
        return Verdict(
            kind="no_path",
            nearest=touching,
            why=(
                f"Nothing on this map reaches {wanted}. The closest claim the "
                f"story does reach is {claims[touching].claim}, {hops} arrows away "
                "from it."
            ),
        )
    furthest = _furthest_reached(graph)
    if furthest is None:
        return Verdict(
            kind="no_path",
            why=f"Nothing on this map reaches {wanted}. The story never left where it started.",
        )
    return Verdict(
        kind="no_path",
        nearest=furthest,
        why=(
            f"Nothing on this map reaches {wanted}, and no arrow on it touches "
            f"that claim at all. The story got as far as {claims[furthest].claim}."
        ),
    )


def _best_backed_route(
    graph: Graph, start: PropositionId, goal: PropositionId
) -> tuple[PropositionId, ...]:
    """Find the route from one claim to another whose weakest arrow is strongest.

    The widest bottleneck: the road with the highest low bridge, rather than the
    shortest one. How well-backed each arrow is comes from the word our own
    pipeline wrote on it, which is the same table the change list ranks with.

    Feedback arrows — a market changing the world it is measuring — are set aside,
    which is the rule the whole engine reads a map by. Two routes that are equally
    well-backed are separated by taking the shorter one, and then the one whose
    first differing arrow comes earlier in the map's own list.

    Args:
        graph: The map to walk.
        start: The claim to walk from.
        goal: The claim to walk to.

    Returns:
        The route, claim by claim, starting at `start`. Empty when there is none.
    """
    arrows = [
        (position, arrow) for position, arrow in enumerate(graph.links) if not arrow.reflexive
    ]
    widest: dict[PropositionId, float] = {start: 1.0}
    route: dict[PropositionId, tuple[PropositionId, ...]] = {start: (start,)}
    steps: dict[PropositionId, tuple[int, ...]] = {start: ()}

    # One pass can only push a route one arrow further, so as many passes as there
    # are claims is always enough, and the bound also means a map that somehow
    # held a loop could not spin here.
    for _ in range(len(graph.propositions)):
        settled = True
        for position, arrow in arrows:
            if arrow.source not in widest:
                continue
            reaching = min(widest[arrow.source], PROVENANCE_WEIGHT[arrow.provenance])
            walked = (*route[arrow.source], arrow.target)
            taken = (*steps[arrow.source], position)
            if arrow.target in widest:
                so_far = (widest[arrow.target], -len(route[arrow.target]))
                now = (reaching, -len(walked))
                if now < so_far or (now == so_far and taken >= steps[arrow.target]):
                    continue
            widest[arrow.target] = reaching
            route[arrow.target] = walked
            steps[arrow.target] = taken
            settled = False
        if settled:
            break
    return route.get(goal, ())


def _multiplied_out(
    route: Sequence[PropositionId], beliefs: Mapping[PropositionId, Belief] | None
) -> float | None:
    """Multiply the likelihoods along a route together.

    The claim the map started from is left out: it is what the person is supposing
    happens, so it is not one of the steps that has to go right.

    Args:
        route: The route, claim by claim, starting at the claim the map started
            from.
        beliefs: The worked-through likelihood of every claim, or nothing at all.

    Returns:
        The product, or nothing at all when the numbers have not been run.
    """
    if beliefs is None:
        return None
    product = 1.0
    for claim_id in route[1:]:
        found = beliefs.get(claim_id)
        if found is None:
            return None
        product *= found.p
    return product


def _reachable_from(graph: Graph, start: PropositionId) -> set[PropositionId]:
    """List every claim the story gets to by following arrows out of one claim."""
    onward: dict[PropositionId, list[PropositionId]] = {}
    for arrow in graph.links:
        onward.setdefault(arrow.source, []).append(arrow.target)
    reached = {start}
    waiting = [start]
    while waiting:
        here = waiting.pop()
        for next_claim in sorted(onward.get(here, [])):
            if next_claim not in reached:
                reached.add(next_claim)
                waiting.append(next_claim)
    return reached


def _nearest_to(graph: Graph, destination: PropositionId) -> tuple[PropositionId | None, int]:
    """Find the claim the story reached that is fewest arrows from the destination.

    Arrows are walked in either direction here, because the question is how close
    the map came and not which way the causing ran. The destination itself does
    not count.

    When nothing on the map touches the destination, there is no such distance,
    and we do not guess at one: nothing comes back, and the caller says so in
    plain words instead.

    Args:
        graph: The finished map.
        destination: The claim the person asked about.

    Returns:
        That claim and how many arrows away it is, or nothing at all and zero.
    """
    beside: dict[PropositionId, list[PropositionId]] = {}
    for arrow in graph.links:
        beside.setdefault(arrow.source, []).append(arrow.target)
        beside.setdefault(arrow.target, []).append(arrow.source)

    reached = _reachable_from(graph, graph.hypothesis_id) - {destination}
    hops = {destination: 0}
    waiting = [destination]
    while waiting:
        here = waiting.pop(0)
        for neighbour in sorted(beside.get(here, [])):
            if neighbour not in hops:
                hops[neighbour] = hops[here] + 1
                waiting.append(neighbour)
                if neighbour in reached:
                    return neighbour, hops[neighbour]
    return None, 0


def _furthest_reached(graph: Graph) -> PropositionId | None:
    """Find how far the story actually got: the best-backed route that runs longest.

    Used only when nothing on the map touches the destination at all, so "closest"
    has no meaning there. Saying how far the story did get is still a computed
    answer to a real question, and it is what the sentence beside it says.

    Args:
        graph: The finished map.

    Returns:
        That claim, or nothing at all when the story never left where it started.
    """
    best: tuple[float, int, PropositionId] | None = None
    for claim_id in sorted(_reachable_from(graph, graph.hypothesis_id)):
        if claim_id == graph.hypothesis_id:
            continue
        route = _best_backed_route(graph, graph.hypothesis_id, claim_id)
        if not route:
            continue
        weakest = min(
            (
                PROVENANCE_WEIGHT[arrow.provenance]
                for arrow in graph.links
                if arrow.source in route and arrow.target in route
            ),
            default=1.0,
        )
        here = (weakest, len(route), claim_id)
        if best is None or here > best:
            best = here
    return None if best is None else best[2]
