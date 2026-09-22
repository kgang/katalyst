"""Three routes that turn a map, a branch and what the reader typed into a thesis card.

The last step of the walk. Everything before these routes hands back a map, a
world, or a difference between two worlds; these hand back **the thesis the reader
carries away**: what is traded, what carries it, what a venue is charging for the
same question, what takes them out, what they typed, and what none of it knows.

Three questions, three routes:

* **What is the trade, and what does it rest on?** One card: the ending, the
  venue's two prices against the map's own number, the claims over-represented in
  the worlds where the reader's stop went first, their own exit with the greyed
  ceiling beside it, and every refusal in full sentences.
* **What can a program read?** The same card as one declarative document — legs
  and conditions, stamped with the map, the branch and the seed so it replays,
  and carrying its limits as fields rather than as a footer somebody can strip.
* **What can a person read?** The same document as a page of text.

**A card is not an edit.** Nothing here moves on the canvas and nothing appears on
a branch: the position is what the reader typed, held beside the map rather than
written into it.

**Nothing here computes what another module owns.** The edge comes from
`thesis/edge.py`, the first-touch shares from `thesis/position.py`, the rail from
`thesis/lift.py`, the greyed ceiling from `thesis/ceiling.py`, the shift from the
Verify door, and the arrangement from `thesis/card.py`. What this file does is
fetch the four things a route can reach that a pure function cannot — a world, a
sample of drawn worlds, a recorded price, and a graded route — and hand them over.

**No price is ever fetched here.** A quote comes from the committed dated file and
from nowhere else (decision record 0020), so these routes need no key and reach no
network. Where no file holds a price for a contract, the card says *no price has
been read for this contract* and prints a break-even instead; it does not go
looking.

Nothing here asks a language model anything.
"""

import json
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, Final

import numpy
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from katalyst.domain import (
    Assignment,
    Branch,
    ContractPayoff,
    Graph,
    PricePayoff,
    Proposition,
    PropositionId,
    Sample,
    Violation,
    World,
    all_marginals,
    sample_forward,
)

# Dated 2026-09-22. `_worked_out_by_deadline` is the by-deadline core's own single
# route — the arithmetic of decision record 0016, reached directly. The Verify door
# reaches it exactly this way and for exactly this reason: what a caller needs and a
# finished world does not carry is the working underneath, and building a second
# assembly here would be a second chance for this file and the tiles beside it to
# disagree about the same map. `katalyst.domain.propagation` belongs to another lane
# this week, so the name is reached as it stands; the one-line change that makes it a
# public seam is recorded with this pull request. Until the flip lands, the drawn
# worlds below come from the new core while the likelihood on the tile beside them
# still comes from the old one; after the flip both are the same arithmetic. That is
# the same state the Verify door's three numbers are already in, and it is said here
# rather than left for a reader to discover.
from katalyst.domain.propagation import SAMPLED_WORLDS, _worked_out_by_deadline
from katalyst.domain.rates import SLICES
from katalyst.engine import worlds as engine
from katalyst.engine.ids import BIGGEST_SEED
from katalyst.engine.verify import Verdict, verdict
from katalyst.grounding import recorded_quote
from katalyst.thesis import (
    EXPORT_SCHEMA_FILE,
    Card,
    Carried,
    Ceiling,
    ClaimMove,
    Draws,
    Edge,
    Export,
    FirstTouch,
    NotComparable,
    Paths,
    Position,
    Refusal,
    Shift,
    Shocked,
    WhatTakesYouOut,
    as_json,
    as_markdown,
    card_of,
    ceiling_of,
    export_of,
    first_touch,
    position_on,
    priced,
    schema_json,
    walk,
    what_takes_you_out,
)
from katalyst.thesis.lift import THE_FLOOR
from katalyst.thesis.position import REFUSALS

router = APIRouter(tags=["thesis"])

DRAWN_WORLDS: Final = SAMPLED_WORLDS
"""How many worlds the price paths are walked through.

The same number the engine draws when something has been observed — fifty
thousand, decision record 0016's figure — so the days a path steps over and the
days the engine's own answers rest on are one sample and not two.
"""

WORKED_OUT_BY_THE_VERDICT: Final = (
    "the map's own verdict: the ending's chance with the hypothesis supposed true, "
    "less its chance with it supposed false"
)
"""Where a shift on this card came from, in the words the card prints beside it."""

NO_PATH_TO_RANK: Final = (
    f"{REFUSALS['first_touch_on_a_contract']} No drawn world stopped out, so there is "
    "nothing here for the rail to rank."
)
"""Why the rail is empty on a contract ending.

A contract is held to its resolution: there is no price path, so no world touched a
stop, so no claim can keep company with one. An empty rail with no reason reads as
*nothing takes you out*, which is a much more flattering sentence than the truth.
"""

NOBODY_HAS_STATED_THE_COSTS: Final = None
"""What it costs to get in and out of an instrument, in its own price units.

**Nothing at all**, because nobody has read a schedule and written one down. The
card prints that in words beside the break-even rather than showing a number that
looks net and is not. Named here so the absence is a decision a reader can find
rather than a `None` somebody may later fill in by accident.
"""


class Refused(BaseModel):
    """One reason a card could not be built: a stable code, the thing at fault, a sentence.

    Two different kinds of fault arrive here and both are shaped the same way, so a
    screen has one thing to read. A **branch that does not fit the map** names the
    claim or arrow at fault. A **form the reader filled in** names the field they
    should look at. Neither is ever repaired silently and neither arrives one at a
    time: every reason comes back together.
    """

    code: str = Field(description="Which rule this is, as a stable string a screen can switch on.")
    subject: str = Field(
        description=(
            "What is at fault: the identifier of a claim or an arrow for a branch that "
            "does not fit, or the name of a form field as the reader sees it."
        )
    )
    message: str = Field(description="One plain sentence the person reads.")


class RefusedCard(BaseModel):
    """Every reason a card was refused, in a settled order, never just the first."""

    detail: tuple[Refused, ...] = Field(
        description="Every reason the card could not be built, in a settled order."
    )


REFUSED: dict[int | str, dict[str, Any]] = {
    422: {
        "model": RefusedCard,
        "description": (
            "The request cannot be carried out as written — either the branch does not fit "
            "the map, or the exit the reader typed is not one a position can be taken on. "
            "The answer lists every reason at once, each with a stable code a screen can "
            "switch on, the thing at fault, and one plain sentence."
        ),
    }
}
"""How a refused card is described to whatever generates the browser's types."""


class ExitAsked(BaseModel):
    """What the reader types about getting out. Every number here is theirs.

    A stop is a price the reader owns and this product never derives one (decision
    record 0019). What it derives beside these numbers is what takes them out and
    what to watch.
    """

    entry: float = Field(description="The price they entered at, in the instrument's own units.")
    stop: float = Field(description="The price at which they get out for a loss. Theirs.")
    target: float = Field(description="The price at which they get out for a gain. Theirs.")
    horizon: date = Field(
        description=(
            "The day by which they expect to be out. The two first-touch shares are read "
            "to this day and no further: shares over a window nobody named are two numbers "
            "nobody can check."
        )
    )
    risk_budget: float = Field(
        gt=0.0,
        le=1.0,
        description=(
            "The share of their capital they are prepared to lose here. The size it "
            "implies is worked out from it and the distance to their stop, and is never a "
            "recommendation."
        ),
    )
    daily_move: float = Field(
        gt=0.0,
        description=(
            "How far the instrument moves in a day, in price units — one standard "
            "deviation of a day's change. The reader's own number today."
        ),
    )


class CardRequest(BaseModel):
    """What it takes to build one card: a map, a branch, a seed, an ending, and an exit.

    The same five give a byte-identical card on any machine and at any time, which
    is what makes a card somebody read three days ago reproducible from what is
    stamped on it.
    """

    base_id: str = Field(description='The short name of the stored example, such as "hormuz".')
    branch: Branch | None = Field(
        default=None,
        description=(
            "The edits in force, sent whole because there is nowhere to keep one yet. "
            "Leave it out for the map with nothing done to it. **The edge is always read "
            "from the map as it stands**, never from the edited world, so an edit cannot "
            "quietly improve what a venue is charging."
        ),
    )
    seed: int = Field(
        ge=0,
        le=BIGGEST_SEED,
        description=(
            "The one number every random draw behind this card comes from. Bounded by "
            "what a browser can hold exactly."
        ),
    )
    ending: PropositionId = Field(
        description=(
            "The ending the card leads with — the one the reader has taken a position "
            "on. Every other tradeable ending on the map is ranked beside it."
        )
    )
    exit: ExitAsked = Field(description="The stop, the target, the horizon and the risk budget.")
    shocks: tuple[Branch, ...] = Field(
        default=(),
        description=(
            "Suppositions the reader placed on top of the branch above, each named in "
            "their own words. The card reports what each did to the position and **no "
            "probability**: supposing something is not a forecast."
        ),
    )
    versions: int = Field(
        default=engine.VERSIONS,
        gt=0,
        le=engine.MOST_VERSIONS,
        description="The outer loop: how many versions of the map to try.",
    )
    worlds: int = Field(
        default=engine.WORLDS,
        gt=1,
        le=engine.MOST_WORLDS,
        description="The inner loop: how many worlds to run under each version.",
    )


@router.post("/thesis/card", responses=REFUSED)
def build_card(request: CardRequest) -> Card:
    """Build one thesis card on one ending of a map.

    What the route fetches and what it hands to the card:

    | Part of the card | Where it comes from |
    |---|---|
    | The trade | the ending's own payoff |
    | What is priced in | `thesis/edge.py`, against the **recorded** quote |
    | What carries it | the Verify door's weakest arrow and its share of the shift |
    | What takes you out | `thesis/lift.py`, over the drawn worlds |
    | Your exit | what the reader typed, with `thesis/ceiling.py` beside it |
    | What else can I trade | `thesis/card.py`, ranked by two rules kept apart |
    | What this does not know | the fixed refusals, carried as data |

    Args:
        request: Which example, which branch, which seed, which ending, and the
            exit the reader typed.

    Returns:
        One card, stamped with the map, the branch and the seed it came from.

    Raises:
        HTTPException: With status 404 and a sentence naming the examples that do
            exist, when nothing is stored under that name. With status 422 and
            every reason at once, when the branch does not fit the map, when the
            ending is not a tradeable claim on it, or when the exit the reader
            typed is not one a position can be taken on.
    """
    return _card_for(request)


@router.post("/thesis/export", responses=REFUSED)
def export_card(request: CardRequest) -> Export:
    """Write the same card out as the declarative document a program reads.

    **Legs and conditions, never an order.** A venue's combination-leg structure is
    an order format, and a document shaped like one implies it could be submitted
    somewhere; this product is not an execution layer.

    The document is checked against the committed description of itself before it
    leaves: the description is generated from these very shapes and committed
    beside them, so the check is that the committed file still says what the code
    says, and that the document answers it.

    Args:
        request: The same five things a card takes.

    Returns:
        The document: the stamp, the leg, the conditions, the exit, the ranked
        endings, and the limits as fields.

    Raises:
        HTTPException: With status 404 or 422 exactly as the card route, or 500
            when the committed description of the document has drifted from the
            shapes — which is a fault in this repository rather than in the
            request, and is said out loud rather than served.
    """
    return _checked(export_of(_card_for(request)))


@router.post(
    "/thesis/export/markdown",
    responses={
        **REFUSED,
        200: {
            "content": {"text/markdown": {"schema": {"type": "string"}}},
            "description": "The same document as a page of text, in the panel's own order.",
        },
    },
)
def export_page(request: CardRequest) -> Response:
    """Write the same card out as the page a person reads.

    One place writes a number out, and it cannot write one without its owner and
    without the rule its kind names — so a page showing a number nobody owns, or a
    likelihood at six figures, cannot be produced here.

    Args:
        request: The same five things a card takes.

    Returns:
        The page as `text/markdown`, in the same order as the panel.

    Raises:
        HTTPException: With status 404 or 422 exactly as the card route.
    """
    return Response(content=as_markdown(_card_for(request)), media_type="text/markdown")


# --- Assembling one card ---------------------------------------------------


def _card_for(request: CardRequest) -> Card:
    """Fetch everything a card needs and hand it to the one function that arranges it.

    Args:
        request: What was asked for.

    Returns:
        The card.

    Raises:
        HTTPException: 404 for an unknown example, 422 for a branch that does not
            fit or a form that cannot be accepted.
    """
    plain = _built(request.base_id, None, request)
    shown = plain if request.branch is None else _built(request.base_id, request.branch, request)
    ending = _the_ending(plain, request.ending)
    position = _the_position(ending, request.exit)

    answers = _every_answer(plain, shown)
    drawn = _drawn_worlds(shown)
    touch, rail, paths = _position_of(shown, ending, position, drawn)
    return card_of(
        shown,
        position=position,
        priced=answers,
        shifts=_every_shift(plain),
        carried_by=_carried_by(plain, ending.id),
        ceiling=_the_ceiling(answers, ending.id),
        touch=touch,
        takes_you_out=rail,
        market_chance={} if paths is None else dict(paths.market_chance),
        # T2b: the two-way sweep in `domain/diff.py` is what computes the watchlist,
        # the rows nobody can watch for and the tails (FR-19). It belongs to the lane
        # building the position route and is not written yet, so the card carries
        # none of them rather than carrying rows nobody worked out.
        watch=(),
        unhedgeable=(),
        tails=(),
        shocks=_every_shock(request, ending, position, paths),
        costs=NOBODY_HAS_STATED_THE_COSTS,
    )


def _built(base_id: str, branch: Branch | None, request: CardRequest) -> World:
    """Build one world, turning the engine's two refusals into the statuses that say so.

    Args:
        base_id: The short name of the stored example.
        branch: The branch to fold, or nothing at all for the map as it stands.
        request: The request, read for its seed and its two loop sizes.

    Returns:
        The world.

    Raises:
        HTTPException: 404 when no example is stored under that name, 422 with
            every reason at once when the branch does not fit the map.
    """
    built = engine.build_world(
        base_id, branch, request.seed, versions=request.versions, worlds=request.worlds
    )
    if built is None:
        raise HTTPException(status_code=404, detail=engine.no_such_example(base_id))
    if isinstance(built, list):
        raise _refusing(_from_violations(built))
    return built


def _the_ending(base: World, ending: PropositionId) -> Proposition:
    """Find the ending the card leads with, or say plainly that the map does not carry it.

    Args:
        base: The world whose map to look in.
        ending: The claim the reader took a position on.

    Returns:
        The claim.

    Raises:
        HTTPException: 422 naming the claim, when the map does not carry it.
    """
    found = next((one for one in base.graph.propositions if one.id == ending), None)
    if found is None:
        raise _refusing(
            (
                Refused(
                    code="unknown_ending",
                    subject=ending,
                    message=(
                        "This map has no claim by that name, so there is no position to take on it."
                    ),
                ),
            )
        )
    return found


def _the_position(ending: Proposition, asked: ExitAsked) -> Position:
    """Build the reader's position, or hand back everything wrong with their form at once.

    Args:
        ending: The claim they took a position on, whose payoff says what is traded
            and which way.
        asked: What they typed.

    Returns:
        The position.

    Raises:
        HTTPException: 422 with every refusal the form has, each naming the field
            the reader should look at; or with the one refusal that stands where
            the claim names no trade at all.
    """
    if ending.payoff is None:
        raise _refusing(
            (
                Refused(
                    code="ending_names_no_trade",
                    subject=ending.id,
                    message=(
                        "This claim names nothing that can be bought or sold, so there is "
                        "no position to take on it."
                    ),
                ),
            )
        )
    built = position_on(
        ending,
        entry=asked.entry,
        stop=asked.stop,
        target=asked.target,
        horizon=asked.horizon,
        risk_budget=asked.risk_budget,
        daily_move=asked.daily_move,
    )
    if isinstance(built, tuple):
        raise _refusing(
            tuple(Refused(code=one.code, subject=one.field, message=one.sentence) for one in built)
        )
    return built


def _every_answer(plain: World, shown: World) -> dict[PropositionId, Edge | NotComparable]:
    """Price every claim on the map that names a trade, against the recorded quote.

    **The map as it stands is what an edge is read from**, whatever the reader has
    supposed — the second world is read only for the mixture that explains a
    supposed reading. A world that already carries a value fixed by an edit is
    refused outright with *conditional world*, which is decision record 0018's one
    conservative rule and is enforced inside `priced` rather than here.

    **A quote is recorded, never fetched.** The committed dated file is the only
    place a price comes from on this route: where it holds none for a contract, the
    answer that comes back says *no price has been read for this contract* and
    carries the break-even, and nothing goes looking.

    Args:
        plain: The world with nothing fixed by an edit.
        shown: The world the reader is looking at, which may carry a branch.

    Returns:
        Claim -> the edge, or the named refusal that stands where none could be
        built, for every claim on the map that names a trade.
    """
    answers: dict[PropositionId, Edge | NotComparable] = {}
    for claim in plain.graph.propositions:
        payoff = claim.payoff
        if payoff is None:
            continue
        quote = recorded_quote(payoff.contract_id) if isinstance(payoff, ContractPayoff) else None
        answers[claim.id] = priced(
            plain,
            shown,
            claim.id,
            quote,
            # Nobody has read this venue's fee schedule and written it down, so the
            # fee is unknown rather than nought. An edge quietly netted against a
            # fee of nothing is an edge that looks net and is not.
            fee=None,
        )
    return answers


def _every_shift(plain: World) -> dict[PropositionId, Shift]:
    """Work out how far the hypothesis moves each ending a venue does not quote.

    Only an ending naming an **instrument** is ranked by its shift, so only those
    are worked out: a verdict costs two passes over the map for the shift and two
    more for every arrow on the route, and a number nothing reads is a number
    nobody should pay for.

    Args:
        plain: The world with nothing fixed by an edit.

    Returns:
        Ending -> its shift, for every ending naming an instrument.
    """
    shifts: dict[PropositionId, Shift] = {}
    for claim in plain.graph.propositions:
        if not isinstance(claim.payoff, PricePayoff):
            continue
        graded = verdict(plain.graph, claim.id, world=plain)
        if graded.shift is None:  # pragma: no cover - a world is always handed in above
            continue
        shifts[claim.id] = Shift(
            ending=claim.id, points=graded.shift, worked_out_by=WORKED_OUT_BY_THE_VERDICT
        )
    return shifts


def _carried_by(plain: World, ending: PropositionId) -> tuple[Carried, ...]:
    """Name the claim whose arrow carries most of the hypothesis's effect on this ending.

    The Verify door works out which single arrow on the best-backed route carries
    most of the shift, and how much of the shift goes with it. The claim that arrow
    leaves is the claim this row is about.

    Args:
        plain: The world with nothing fixed by an edit.
        ending: The ending the card leads with.

    Returns:
        One row, or none at all where the story does not reach the ending, where
        the shift is nought, or where the ending is the hypothesis itself.
    """
    graded = verdict(plain.graph, ending, world=plain)
    carried = _the_arrow_that_carries_it(plain.graph, graded)
    return () if carried is None else (carried,)


def _the_arrow_that_carries_it(graph: Graph, graded: Verdict) -> Carried | None:
    """Turn a verdict's weakest arrow into the one row the card shows for it.

    Args:
        graph: The map, for the claim the arrow leaves.
        graded: What the Verify door said about the route to this ending.

    Returns:
        The row, or nothing at all when the verdict named no arrow.
    """
    if graded.weakest_arrow is None or graded.share_of_the_shift is None:
        return None
    if graded.shift is None:  # pragma: no cover - an arrow is named only when a shift is
        return None
    arrow = next(one for one in graph.links if one.id == graded.weakest_arrow)
    return Carried(
        claim=arrow.source,
        points=graded.shift * graded.share_of_the_shift,
        share=graded.share_of_the_shift,
    )


def _the_ceiling(
    answers: Mapping[PropositionId, Edge | NotComparable], ending: PropositionId
) -> Ceiling:
    """The greyed quartered-Kelly ceiling for the ending the card leads with.

    Args:
        answers: What was priced for every tradeable ending.
        ending: The ending the card leads with.

    Returns:
        The ceiling, or the reason there is none, as `thesis/ceiling.py` worked it
        out. Zero and absent are different answers and it keeps them apart.
    """
    return ceiling_of(answers[ending])


# --- The drawn worlds, and what the reader's exit does in them ---------------


def _drawn_worlds(world: World) -> Draws:
    """Draw worlds forward through this map and hand them over as the trade layer's contract.

    `Draws` is the one thing the trade layer reads from the engine: for each drawn
    world and each claim, the day it came on and the day it went off, with a weight
    per world. Everything above it — the price paths, first touch, the rail — is
    pure arithmetic over that table.

    Args:
        world: The world the card is about, read for its map, the values its edits
            fixed, its first day, its seed and how many versions it tried.

    Returns:
        The drawn worlds.
    """
    # T2b: replace with the shared builder at the rebase. The lane building
    # `POST /api/thesis/position` owns `thesis/adapter.py`, which is where this
    # conversion belongs; it is written here so the card route does not wait on it,
    # and it is deleted the moment that adapter lands.
    sample = _the_sample(world.graph, world.assignments, world)
    return Draws(
        day_zero=sample.day_zero,
        days=sample.days,
        claims=sample.claims,
        on_day=sample.on_day,
        off_day=sample.off_day,
        weight=sample.weight,
        effective=sample.effective,
        sample="weighted_forward_sample",
    )


def _the_sample(graph: Graph, fixed: tuple[Assignment, ...], world: World) -> Sample:
    """Work the map through the exact core and draw worlds forward from what it built.

    **The engine's own route, reached rather than copied.** The sample needs the
    tables the forward pass built, which a finished world does not carry, so this
    asks the assembly for its working rather than for its result — the same way the
    Verify door does, and for the same reason: a second assembly here would be a
    second chance for this file and the tiles beside it to disagree about one map.

    Args:
        graph: The map the fold left behind.
        fixed: Every value that fold fixed.
        world: The world whose first day, seed and version count this matches.

    Returns:
        The drawn worlds, their weights and the day every claim came on and went
        off.
    """
    worked = _worked_out_by_deadline(
        graph,
        fixed,
        as_of=world.day_zero,
        seed=world.seed,
        versions=world.versions,
        slices=SLICES,
        sampled_worlds=SAMPLED_WORLDS,
    )
    return sample_forward(
        worked.forward,
        worked.pinned,
        window=worked.window,
        version=0,
        seed=world.seed,
        worlds=DRAWN_WORLDS,
        exact=all_marginals(worked.forward, worked.pinned),
    )


def _position_of(
    world: World, ending: Proposition, position: Position, drawn: Draws
) -> tuple[FirstTouch | Refusal, WhatTakesYouOut, Paths | None]:
    """Walk price paths through the drawn worlds, then read the exit and the rail off them.

    A **contract** ending is held to its resolution, so there is no path to touch:
    first touch refuses by name and the rail comes back empty with that refusal
    written on it. An **instrument** ending gets the whole of it.

    Args:
        world: The world the card is about, read for its day zero.
        ending: The ending the card leads with, whose payoff says how far the claim
            moves the instrument.
        position: What the reader typed.
        drawn: The drawn worlds.

    Returns:
        The two first-touch shares or the refusal that stands instead, the rail,
        and the paths — or nothing at all where there are none.
    """
    if position.trades == "contract":
        return (
            Refusal(
                code="first_touch_on_a_contract",
                field="ending",
                sentence=REFUSALS["first_touch_on_a_contract"],
            ),
            WhatTakesYouOut(
                rows=(),
                dropped=(),
                effective_draws=0.0,
                stop_first_worlds=0,
                floor=THE_FLOOR,
                sample=drawn.sample,
                too_few_draws=NO_PATH_TO_RANK,
            ),
            None,
        )
    paths = walk(
        drawn,
        _what_moves_the_price(ending, position),
        entry=position.entry,
        daily_move=position.daily_move,
        seed=world.seed,
    )
    touch = first_touch(paths, position)
    if isinstance(touch, Refusal):  # pragma: no cover - a contract is the only refusal
        return touch, _no_rail(drawn), paths
    return touch, what_takes_you_out(drawn, touch), paths


def _what_moves_the_price(ending: Proposition, position: Position) -> tuple[ClaimMove, ...]:
    """Say which claims move the traded instrument, and by how much.

    **One claim, and the map is why.** The only thing on a map today that says what
    a claim does to a price is the ending's own payoff, which names how far the
    instrument moves when that claim comes true. No arrow and no other claim carries
    a price move, so no other claim moves the price here — an assumption stated
    rather than an omission.

    The payoff's move is a **fraction of the instrument's own price** today, so it
    is turned into a level gap against the price the reader entered at. Its sign is
    the payoff's direction: a payoff whose long side pays when the claim comes true
    is a claim that pushes the instrument up, and a short one pushes it down.

    **The market's chance is not handed in**, so the walk reads it off the drawn
    worlds themselves — the share of them in which the claim comes true inside the
    trade's own window. That is the neutral assumption that leaves the path carrying
    no drift of its own, and the card names it as the source beside every share
    built on it.

    Args:
        ending: The ending the card leads with.
        position: What the reader typed, read for the price they entered at.

    Returns:
        One move, for the ending's own claim.
    """
    payoff = ending.payoff
    if not isinstance(payoff, PricePayoff):  # pragma: no cover - a contract never reaches here
        raise ValueError(
            f"'{ending.id}' names a contract rather than an instrument, and a contract is "
            "held to its resolution: there is no price path for a claim to move"
        )
    upwards = 1.0 if payoff.direction == "long" else -1.0
    return (
        ClaimMove(
            claim=ending.id,
            move=position.entry * payoff.move * upwards,
            market_chance=None,
            market_chance_from="sample_share",
        ),
    )


def _no_rail(drawn: Draws) -> WhatTakesYouOut:
    """An empty rail carrying the reason it is empty.

    Args:
        drawn: The drawn worlds, for the sampler's own name.

    Returns:
        The rail with no rows and the contract's refusal written on it.
    """
    return WhatTakesYouOut(
        rows=(),
        dropped=(),
        effective_draws=0.0,
        stop_first_worlds=0,
        floor=THE_FLOOR,
        sample=drawn.sample,
        too_few_draws=NO_PATH_TO_RANK,
    )


# --- Shocks ------------------------------------------------------------------


def _every_shock(
    request: CardRequest, ending: Proposition, position: Position, paths: Paths | None
) -> tuple[Shocked, ...]:
    """Re-run the position on each supposition the reader placed, and say what it did.

    **What the position is worth** is the weighted average price at the reader's
    own horizon, over the drawn worlds. The change a shock makes is that number on
    the shocked branch less the same number without it, in the instrument's own
    price units — two computed quantities and their difference, and nothing else.
    The paths either side are walked from the same seed and the same entry price,
    so the difference is the supposition and not the dice.

    **No probability, ever.** They supposed it; that is not a forecast, and the
    map's own number for a claim an edit has just fixed is not one either.

    Args:
        request: The request, read for the map, the seed and the loop sizes.
        ending: The ending the card leads with.
        position: What the reader typed.
        paths: The paths without the shock, or nothing at all on a contract ending,
            which has no paths and therefore no shock rows.

    Returns:
        One row per supposition, in the order the reader placed them.
    """
    if paths is None or not request.shocks:
        return ()
    without = _worth_at(paths, position.horizon)
    placed: list[Shocked] = []
    for branch in request.shocks:
        shocked = _built(request.base_id, branch, request)
        walked = walk(
            _drawn_worlds(shocked),
            _what_moves_the_price(ending, position),
            entry=position.entry,
            daily_move=position.daily_move,
            seed=request.seed,
        )
        placed.append(
            Shocked(
                name=branch.label,
                change_to_the_position=_worth_at(walked, position.horizon) - without,
            )
        )
    return tuple(placed)


def _worth_at(paths: Paths, horizon: date) -> float:
    """What the position is worth on the reader's own horizon: the weighted average price.

    Args:
        paths: The daily price path through every drawn world.
        horizon: The day the reader expects to be out by.

    Returns:
        The average price on that day, each drawn world counting for its own
        weight.
    """
    day = (horizon - paths.day_zero).days
    return float(numpy.average(paths.level[:, day], weights=paths.weight))


# --- Refusing, and the committed description of the document -----------------


def _from_violations(found: Sequence[Violation]) -> tuple[Refused, ...]:
    """Turn the rules layer's complaints about a branch into this route's own shape.

    Args:
        found: Every reason the branch could not be folded.

    Returns:
        The same reasons, each with its code, its subject and its sentence.
    """
    return tuple(Refused(code=one.code, subject=one.subject, message=one.message) for one in found)


def _refusing(reasons: tuple[Refused, ...]) -> HTTPException:
    """Build the 422 that carries every reason at once.

    Args:
        reasons: Every reason, in a settled order.

    Returns:
        The exception to raise. Built and returned rather than raised here so the
        caller's own line says `raise`, and a reader following the flow never has
        to guess whether a helper returns.
    """
    return HTTPException(status_code=422, detail=[one.model_dump() for one in reasons])


def _checked(document: Export) -> Export:
    """Check the document against the committed description of itself before it leaves.

    Two things, together: the committed description is exactly what these shapes
    produce right now, and the document answers those shapes. The description is
    **generated** from the shapes and committed beside them, so the pair is the
    whole of what *the document answers the committed description* means — and the
    first half is what catches a shape that changed while the file did not.

    Args:
        document: The document about to be returned.

    Returns:
        The same document.

    Raises:
        HTTPException: With status 500 when the committed description has drifted
            from the shapes. That is a fault in this repository rather than in the
            request, and serving a document under a description that no longer
            describes it is the one thing this check exists to stop.
    """
    if EXPORT_SCHEMA_FILE.read_text(encoding="utf-8") != schema_json():
        raise HTTPException(
            status_code=500,
            detail=(
                "The committed description of this document is not what the shapes now "
                "produce, so nothing here can be served under it. Regenerate it and "
                "commit it beside them."
            ),
        )
    return Export.model_validate(json.loads(as_json(document)))
