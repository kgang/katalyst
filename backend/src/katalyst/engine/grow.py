"""The walk: which claim is asked about next, and what makes a run stop.

`expand.py` answers one question. This walks the whole map: it turns the person's
sentence into the claim the map starts from, keeps asking about whichever lines
are still open, folds every answer in, and stops with **one** reason a person can
read.

Reading order
-------------
`grow` first, because it is the story. `_Walk` under it, because it is the
bookkeeping that story leans on: which claims are still open, how far each sits
from the start, how many proposals in a row have failed for each, what closed the
last one to close, and what the run has spent. Then the one rule that picks the
reason.

Three things worth knowing before reading it
---------------------------------------------
**The order is fixed even though three lines are asked about at once.** A round
takes the first few open claims in frontier order and asks about them at the same
time; their answers are folded **in that same frontier order**, whichever came
back first. The map depends on the answers and never on the weather.

**An answer is judged twice: when it comes back, and where the map changes.** A
round hands one snapshot of the map to all its calls, so two answers can each be
legal against that snapshot and illegal together — a loop, or the same arrow
drawn twice. Every accepted answer is checked again against the map as it stands
at the moment it is folded, and one that has stopped being legal is refused there
like any other: shown, counted, never repaired (2026-09-20).

**No answer ever says "this claim is closed".** Every outcome carries the
frontier as it stands once it was folded in, and a claim leaving that list is how
a reader learns it has closed.

**The spending cap is checked after every call, and inside one.** A question is
told what is left in the purse before it is put, so `client.py` can stop between
its own rounds of research rather than only at the end (Kent, 2026-09-20).
**The spending cap is checked after every call.** A round's calls are already in
flight when the first of them is folded, so a run can pass its ceiling by at most
the calls that were in the air with it.

What this file must never do
----------------------------
- Never write a claim or an arrow the model did not propose — not to make a map
  end somewhere, and not to make a Verify run reach its destination.
- Never talk over the network, and never name a type from the library we call the
  model with.
- Never read a clock. The day a run happened is passed in.
- Never give two reasons for stopping, or a reason nothing can produce.
"""

from collections.abc import Callable, Generator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import Graph, Proposition, PropositionId
from katalyst.domain.validity import TERMINAL_KINDS
from katalyst.engine.client import SEARCHES_INSIDE_ONE_CALL, Answerer
from katalyst.engine.expand import expand, map_with, start_the_map, still_legal_on
from katalyst.engine.ids import mint_id
from katalyst.engine.outcome import Accepted, Caps, Outcome, Refused, Stopped
from katalyst.engine.receipt import (
    Receipt,
    fold,
    nothing_spent_yet,
    over_the_cap,
    what_it_spent_and_got,
)

StoppingReason = Literal[
    "spend_cap",
    "no_terminal",
    "claim_cap",
    "depth_cap",
    "width_cap",
    "refusal_cap",
    "reached_terminal",
]
"""The seven reasons a walk can give for stopping. `_why_it_stopped` holds the rule.

Reaching the cap on searches is deliberately not one of them. Running out of
searches turns searching off and the map keeps building; the arrows added
afterwards say they argued rather than documented, and the origin marks on screen
show where the evidence thins out. A limit on the bill is not a fact about the
world, so it can never be what closed a claim.
"""

CLOSED_BY_HAVING_NOTHING_MORE_TO_SAY = "ended"
"""Why a claim closed when the model answered that this part of the story is finished.

Not a cap and not a failure. It is the ordinary way a line ends, and it is what
`reached_terminal` is read off.
"""


class Finished(BaseModel):
    """The last thing a walk hands back: what was built, why it stopped, what it cost.

    Exactly one of these comes out of every walk, and it always comes last.
    """

    model_config = ConfigDict(frozen=True)

    reason: StoppingReason = Field(
        description="Why the walk stopped. One reason, chosen by the rule in `_why_it_stopped`."
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


def grow(
    hypothesis: str,
    *,
    target: str | None = None,
    answerer: Answerer,
    on: date,
    caps: Caps | None = None,
) -> Generator[Outcome | Finished, None, None]:
    """Walk the frontier, one round at a time, until every line has closed.

    Hands back every outcome as it is folded in, oldest first, and then exactly
    one `Finished`, always last. Nothing is buffered: a caller can draw the map as
    it arrives.

    The first round asks about one claim — the one the map started from — which is
    also what lets the standing half of the request be written into the service's
    cache before anything is asked in parallel. Calls sent at the same moment
    cannot read what each other are still writing.

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

    It is a generator rather than a list on purpose, and the caller may stop
    reading it at any point: abandoning it is what makes "the run stops calling
    the model when the client goes away" true without a flag to check. Close it
    when you stop, so the round of calls in flight is let go of at once.
    """
    caps = caps or Caps()
    walk = _Walk(caps)

    # The claim the map starts from, and the destination when there is one.
    started = yield from _keep_asking(
        lambda: start_the_map(
            hypothesis,
            is_the_hypothesis=True,
            answerer=answerer,
            on=on,
            may_search=_still_room_to_search(caps.searches - walk.receipt.searches),
        ),
        walk,
        answerer,
    )
    if started is None:
        # The money is an override wherever it runs out, this question included:
        # blaming the person's sentence for a ceiling being low is a lie a reader
        # would act on (2026-09-20).
        why_it_ended: StoppingReason = "spend_cap" if walk.spent else "refusal_cap"
        yield Finished(
            reason=why_it_ended,
            why=(
                _in_one_sentence(why_it_ended, walk.receipt, caps, None)
                if walk.spent
                else _never_got_started(walk.last_refusal)
            ),
            receipt=walk.receipt,
            refused=walk.refused,
        )
        return
    first, opening = started
    graph = Graph(id=mint_id(), propositions=(first,), links=(), hypothesis_id=first.id)
    walk.open_a_line(first.id, layer=0)
    yield opening.model_copy(update={"frontier": tuple(walk.frontier)})

    destination: PropositionId | None = None
    if target is not None and not walk.spent:
        asked_for = yield from _keep_asking(
            lambda: start_the_map(
                target,
                is_the_hypothesis=False,
                answerer=answerer,
                on=on,
                may_search=_still_room_to_search(caps.searches - walk.receipt.searches),
            ),
            walk,
            answerer,
        )
        if asked_for is not None:
            wanted, its_outcome = asked_for
            graph = graph.model_copy(update={"propositions": (*graph.propositions, wanted)})
            destination = wanted.id
            # A destination is where a person wants the story to get to, not
            # somewhere to grow from, so it never joins the frontier.
            yield its_outcome.model_copy(update={"frontier": tuple(walk.frontier)})

    with ThreadPoolExecutor(max_workers=caps.at_once) as pool:
        while not walk.stopped and walk.frontier:
            if len(graph.propositions) >= caps.claims:
                walk.the_map_is_full()
                break

            # A round is sized to the room the map has left, not only to how many
            # lines may be asked about at once: three questions in flight bring
            # three claims back, and a cap read once a round is a cap a round
            # steps over (2026-09-20).
            room = caps.claims - len(graph.propositions)
            asking = list(walk.frontier[: min(caps.at_once, room)])
            walk.watch(answerer)
            answers = _ask_about_each(
                pool,
                graph,
                asking,
                target=target,
                answerer=answerer,
                on=on,
                searches_left=caps.searches - walk.receipt.searches,
            )
            for claim_id, answer in zip(asking, answers, strict=True):
                graph, outcome = walk.fold(graph, claim_id, answer)
                yield outcome.model_copy(update={"frontier": tuple(walk.frontier)})

        # One last call per open line, asking only for an ending. A cap that
        # stopped the walk is exactly when this is wanted; only the money running
        # out stops it, because there is nothing left to pay with.
        if not walk.spent and not _ends_somewhere(graph):
            for claim_id in _lines_with_no_ending(graph):
                if walk.spent:
                    break
                walk.watch(answerer)
                outcome = expand(
                    graph,
                    claim_id,
                    target=target,
                    answerer=answerer,
                    on=on,
                    may_search=_still_room_to_search(caps.searches - walk.receipt.searches),
                    ending_only=True,
                )
                graph, outcome = walk.fold(graph, claim_id, outcome, growing=False)
                yield outcome.model_copy(update={"frontier": ()})

    reason = _why_it_stopped(walk, graph)
    yield Finished(
        reason=reason,
        why=_in_one_sentence(reason, walk.receipt, caps, graph),
        graph=graph,
        receipt=walk.receipt,
        claims=len(graph.propositions),
        links=len(graph.links),
        refused=walk.refused,
        destination=destination,
    )


class _Walk:
    """Everything one walk has to remember, and the rules that change it.

    Kept as one object rather than as seven names threaded through five
    functions, so that `grow` above reads as the story it is.
    """

    def __init__(self, caps: Caps) -> None:
        """Start a walk with nothing open and nothing spent."""
        self.caps = caps
        self.receipt = nothing_spent_yet()
        self.frontier: list[PropositionId] = []
        self.layer: dict[PropositionId, int] = {}
        self.failures_here: dict[PropositionId, int] = {}
        self.refused = 0
        self.closed_last: str | None = None
        self.spent = False
        self.filled_up = False
        self.last_refusal: str | None = None

    def watch(self, answerer: Answerer) -> None:
        """Say what has been spent and what may be, before a question is put.

        A question can now run twenty-five searches over five rounds, so one call
        can cost a dollar by itself and a ceiling checked only between calls is a
        ceiling the dearest thing in the program steps over. Saying it here means
        the answerer can stop between rounds of its own (Kent, 2026-09-20).

        Args:
            answerer: Whatever this run asks its questions of.
        """
        answerer.watching(self.receipt, self.caps.dollars)

    @property
    def stopped(self) -> bool:
        """Say whether a whole-run limit has ended the growing.

        The two that can: the money, and the map filling up. Neither stops the one
        last round that asks each open line for an ending — only the money does
        that, because there is nothing left to pay with.
        """
        return self.spent or self.filled_up

    def the_map_is_full(self) -> None:
        """Close every open line at once, because the map has all the claims it may."""
        self.filled_up = True
        self.frontier.clear()
        self.closed_last = "claim_cap"

    def open_a_line(self, claim_id: PropositionId, *, layer: int) -> None:
        """Put one claim on the frontier, at a known distance from the start."""
        self.layer[claim_id] = layer
        self.frontier.append(claim_id)

    def close_a_line(self, claim_id: PropositionId, why: str) -> None:
        """Take one claim off the frontier and remember what closed it.

        What closed the **last** claim to close is the whole of how a run's one
        reason is chosen, so this is the only place that is written.
        """
        if claim_id in self.frontier:
            self.frontier.remove(claim_id)
        self.closed_last = why

    def fold(
        self, graph: Graph, claim_id: PropositionId, outcome: Outcome, *, growing: bool = True
    ) -> tuple[Graph, Outcome]:
        """Put one answer onto the map, and decide whether its claim stays open.

        **This is where an accepted answer is judged for the second time.** It was
        judged when it came back, against the map as it stood at the start of its
        round; here it is judged against the map as it stands now, with whatever
        the answers folded before it added. An answer that has stopped being legal
        in between becomes a refusal — carrying its own counters, because the call
        was made and the money was spent.

        Args:
            graph: The map as it stands.
            claim_id: The claim this answer was about.
            outcome: What happened to it.
            growing: False on the last, ending-seeking pass. Every line has already
                closed by then, so nothing there opens a line, closes one, or
                changes what closed the last one — only the map and the bill grow.

        Returns:
            The map with whatever the answer added, and the answer as it now
            stands — the one that came in, or a refusal in its place.
        """
        self.receipt = fold(self.receipt, outcome)
        outcome = self._judged_again(graph, outcome)
        result = outcome.result

        if isinstance(result, Stopped):
            if growing:
                self.close_a_line(claim_id, CLOSED_BY_HAVING_NOTHING_MORE_TO_SAY)
        elif isinstance(result, Refused):
            self.last_refusal = result.claim_in_words
            # Anything that is not an accepted proposal counts toward the three:
            # a rejection by the map's rules, a refusal by the vendor, an answer
            # that did not fit the shape. One rule, not three — what has run out
            # is our willingness to keep paying for this line, and that is the
            # same whichever way the attempt failed.
            self.refused += 1
            if growing:
                self.failures_here[claim_id] = self.failures_here.get(claim_id, 0) + 1
                if self.failures_here[claim_id] >= self.caps.refusals_in_a_row:
                    self.close_a_line(claim_id, "refusal_cap")
        else:
            if growing:
                self.failures_here[claim_id] = 0
            graph = map_with(graph, result)
            # An ending never joins the frontier: there is nothing downstream of
            # a trade.
            arrived = result.proposition
            if growing and arrived is not None and arrived.kind not in TERMINAL_KINDS:
                self.open_a_line(arrived.id, layer=self.layer[claim_id] + 1)
            if growing:
                # The claim we asked about first, then the one that just arrived:
                # a claim born at the depth cap has no room from the moment it
                # exists, and never gets asked about.
                self._close_if_out_of_room(graph, claim_id)
                if arrived is not None and arrived.id in self.frontier:
                    self._close_if_out_of_room(graph, arrived.id)

        self.spent = self.spent or over_the_cap(self.receipt, self.caps.dollars)
        return graph, outcome

    def _judged_again(self, graph: Graph, outcome: Outcome) -> Outcome:
        """Check an accepted answer against the map as it now stands, and refuse it if need be.

        Two questions, in this order. First the map's own rules, through the very
        same function that judged it the first time — so a loop or a second arrow
        between one pair is refused with the rules' own code and sentence. Then
        this run's own width cap, counted against **each arrow's own cause**
        rather than only against the claim the call was about: an arrow may name
        any claim on the map as its source, and a cap checked only on the claim
        being expanded is a cap that arrow walks straight past.

        Args:
            graph: The map as it stands, before this answer lands.
            outcome: What came back.

        Returns:
            The same outcome, or a refusal carrying its counters.
        """
        accepted = outcome.result
        if not isinstance(accepted, Accepted):
            return outcome
        introduced = still_legal_on(graph, accepted)
        if introduced:
            return outcome.model_copy(
                update={
                    "result": Refused(
                        claim_in_words=_what_arrived(accepted),
                        violations=introduced,
                    )
                }
            )
        crowded = self._out_of_room_beside(graph, accepted)
        if crowded is not None:
            return outcome.model_copy(
                update={
                    "result": Refused(
                        claim_in_words=(
                            f"There is no room beside {crowded} for another arrow: it "
                            f"already has the {self.caps.width} this run allows it."
                        )
                    )
                }
            )
        return outcome

    def _out_of_room_beside(self, graph: Graph, accepted: Accepted) -> PropositionId | None:
        """Name the first claim an arrow would give more children than this run allows.

        Args:
            graph: The map as it stands.
            accepted: The claim and arrows that arrived.

        Returns:
            The crowded claim, or nothing at all when every arrow has room.
        """
        leaving: dict[PropositionId, int] = {}
        for arrow in graph.links:
            leaving[arrow.source] = leaving.get(arrow.source, 0) + 1
        for arrow in accepted.links:
            if leaving.get(arrow.source, 0) >= self.caps.width:
                return arrow.source
            leaving[arrow.source] = leaving.get(arrow.source, 0) + 1
        return None

    def _close_if_out_of_room(self, graph: Graph, claim_id: PropositionId) -> None:
        """Close a claim that has run out of layers below it, or of room beside it.

        Checked the moment an answer lands rather than at the start of the next
        round, so that the frontier a reader is shown is already true.

        The width cap counts the arrows leaving that claim, whether they arrived
        with a new claim or on their own. A cap that counted only the first could
        be walked past for ever by proposing the second.
        """
        if self.layer[claim_id] >= self.caps.depth:
            self.close_a_line(claim_id, "depth_cap")
            return
        leaving = sum(1 for arrow in graph.links if arrow.source == claim_id)
        if leaving >= self.caps.width:
            self.close_a_line(claim_id, "width_cap")


def _keep_asking(
    ask: Callable[[], Outcome], walk: _Walk, answerer: Answerer
) -> Generator[Outcome, None, tuple[Proposition, Outcome] | None]:
    """Ask for a starting claim until one comes back, or until the tries run out.

    The same rule as everywhere else: up to three attempts, none of them told what
    was wrong with the last.

    Refused attempts are handed back as they happen. The one that succeeds is
    **not**, because the frontier it opens does not exist until the caller has put
    it on the map — and every answer carries the frontier as it stands after it.

    Args:
        ask: The question to put, as something that can be called again.
        walk: What this walk has spent and refused so far. Changed as it goes.
        answerer: Whatever this run asks its questions of. Told what is left in
            the purse before each attempt.

    Yields:
        Each refused attempt's outcome.

    Returns:
        The claim and the answer it came in, or nothing at all when three attempts
        came back with none.
    """
    for _ in range(walk.caps.refusals_in_a_row):
        walk.watch(answerer)
        outcome = ask()
        walk.receipt = fold(walk.receipt, outcome)
        walk.spent = walk.spent or over_the_cap(walk.receipt, walk.caps.dollars)
        result = outcome.result
        if isinstance(result, Accepted) and result.proposition is not None:
            return result.proposition, outcome
        if isinstance(result, Refused):
            walk.last_refusal = result.claim_in_words
        yield outcome
        walk.refused += 1
        if walk.spent:
            return None
    return None


def _never_got_started(last_refusal: str | None) -> str:
    """Say why the very first question never came back with a claim.

    It used to say the sentence could not be written as a claim anybody could
    settle, whatever had actually happened — so a run the model never answered at
    all told the person to go and rewrite a perfectly good sentence. The last
    refusal's own words are carried instead (Kent, 2026-09-20).

    Args:
        last_refusal: What the last attempt said, if anything did.

    Returns:
        One plain sentence.
    """
    if last_refusal:
        return f"This run never got started. {last_refusal}"
    return (
        "This run never got started: the sentence could not be written as a claim "
        "anybody could settle."
    )


def _what_arrived(accepted: Accepted) -> str:
    """Quote what an answer brought, so a late refusal names a claim rather than a code."""
    if accepted.proposition is not None:
        return accepted.proposition.claim
    return "This arrow, on the map as it stood once the rest of its round had landed."


def _ask_about_each(
    pool: ThreadPoolExecutor,
    graph: Graph,
    asking: Sequence[PropositionId],
    *,
    target: str | None,
    answerer: Answerer,
    on: date,
    searches_left: int,
) -> list[Outcome]:
    """Ask about several claims at the same time, and hand the answers back in order.

    The answers are read out in the order the questions were asked, not in the
    order they came back, which is what makes a run's shape depend on its answers
    rather than on how fast each one arrived.

    **The searches are handed out one call at a time, in that same order.** Every
    call in a round goes out before any of them comes back, so a round that read
    the budget once could carry a run a whole round's worth past it — twenty-five
    searches a call, three calls. Each call is allowed the tool only while the
    whole of what it could still spend fits in what is left, and what it is
    allowed is set aside for it, so the ceiling is never passed (2026-09-20).

    Args:
        pool: Where the questions are run.
        graph: The map as it stood at the start of this round.
        asking: The claims to ask about, in frontier order.
        target: The destination in the person's own words, or nothing at all.
        answerer: Whatever this run asks its questions of.
        on: The day this run is happening.
        searches_left: How much of the run's budget of searches is unspent.

    Returns:
        One outcome per claim, in the same order.
    """
    allowed: list[bool] = []
    left = searches_left
    for _ in asking:
        may = _still_room_to_search(left)
        allowed.append(may)
        if may:
            left -= SEARCHES_INSIDE_ONE_CALL
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
        for claim_id, may_search in zip(asking, allowed, strict=True)
    ]
    return [one.result() for one in in_flight]


def _still_room_to_search(left: int) -> bool:
    """Say whether a call may use the search tool with this much budget unspent.

    The whole of what one call could spend has to fit: a call is told once, before
    it goes out, and nothing can stop it at search twelve. So the last searches of
    a run's budget go unspent — which is the price of never passing the ceiling,
    and a cheap one, since the figure itself is a first guess the first run under
    it resets.

    Args:
        left: How many searches of the run's budget are unspent and unreserved.

    Returns:
        True when a whole call's worth still fits.
    """
    return left >= SEARCHES_INSIDE_ONE_CALL


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
    onward = _arrows_out_of(graph)
    reached = _walk_onward(onward, graph.hypothesis_id)
    return sorted(
        claim.id
        for claim in graph.propositions
        if claim.id in reached and claim.kind not in TERMINAL_KINDS and not onward.get(claim.id)
    )


def _arrows_out_of(graph: Graph) -> dict[PropositionId, list[PropositionId]]:
    """List, for each claim, the claims its arrows lead to."""
    onward: dict[PropositionId, list[PropositionId]] = {}
    for arrow in graph.links:
        onward.setdefault(arrow.source, []).append(arrow.target)
    return onward


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


def _why_it_stopped(walk: _Walk, graph: Graph) -> StoppingReason:
    """Pick the one reason a run gives for stopping.

    **The rule: the reason names what closed the last claim that was still open**,
    with two overrides above it. One rule, so two readers cannot get two answers.

    1. **The money ran out.** An override, because it stops the run wherever it
       happens to be and nothing further is asked.
    2. **The map ends nowhere you can act on**, even after the last ending-seeking
       call. An override, because it is the most important thing a reader can be
       told about a finished map.
    3. **A cap closed the last open claim** — the map was full, it sat at the
       depth cap, it already had its full width of arrows, or three proposals in a
       row for it failed. Our limit, under its own name.
    4. **The last open claim had nothing more to say.** The model answered that
       this part of the story was finished, which is the ordinary, good ending,
       and it is the fall-through.

    Reaching the cap on searches can never appear: it stops searching rather than
    closing a claim.

    Args:
        walk: What this walk remembers, including what closed the last claim.
        graph: The finished map.

    Returns:
        One reason.
    """
    if walk.spent:
        return "spend_cap"
    if not _ends_somewhere(graph):
        return "no_terminal"
    for cap in ("claim_cap", "depth_cap", "width_cap", "refusal_cap"):
        if walk.closed_last == cap:
            return cast(StoppingReason, cap)
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
    said = {
        "spend_cap": lambda: what_it_spent_and_got(receipt, caps.dollars, claims, links),
        "no_terminal": lambda: (
            "This map does not end anywhere you can act on. Every line that was "
            "still open was asked for an ending, and none came back."
        ),
        "claim_cap": lambda: (
            f"This map reached its limit of {caps.claims} claims and stopped growing."
        ),
        "depth_cap": lambda: (
            f"The last line still open reached its limit of {caps.depth} layers "
            "from the claim this started at."
        ),
        "width_cap": lambda: (
            f"The last line still open reached its limit of {caps.width} arrows out of one claim."
        ),
        "refusal_cap": lambda: (
            f"The last line still open was abandoned after {caps.refusals_in_a_row} "
            "proposals for it in a row were refused."
        ),
        "reached_terminal": lambda: "Every line ran to an ending.",
    }
    return said[reason]()
