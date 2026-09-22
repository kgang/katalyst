"""The route that turns a map, a branch and the reader's own exit into a position.

One question, one route: **I am trading this ending, I get out here, how often does
that happen, and what takes me out?** Everything it answers is worked out from the
map the request names, the branch it sends, one seed, and the four numbers the
reader typed.

**The stop, the target and the horizon are the reader's.** Nothing here derives
one, and nothing here recommends a size. What is computed beside them is how often
each end of the exit is reached first, which claims kept company with being
stopped out, and a greyed ceiling the reader is told in as many words never to
size to.

**Every number says whose it is.** The answer holds no bare numbers: each one
carries its value, whether it belongs to the reader, to the model, to a venue or
to a computation over the drawn worlds, what it is in plain words, and where it
came from. That is the same shape the thesis card uses, built by the same code, so
the two can never print one number two ways.

**The days come from the engine's own weighted forward sample**, asked for from
the same map, branch and seed a world is built from — and the answer names that
sample in the same sentence as every share read off it, because under *This
happened* those days carry a measured error and this is the number a reader acts
on.

**A refusal is a value or a status, never a stack trace.** A name that matches no
stored example is a 404 saying which examples exist. A branch that does not fit
the map is a 422 carrying every reason at once. A form the reader can fix is a 422
carrying every fault at once, each with a stable code, the field at fault and one
plain sentence. And two things that are not mistakes at all come back inside a
perfectly good answer: a **contract** ending has no price path, so its first touch
is refused by name; and where no edge could be built the greyed ceiling is absent,
carrying the reason it could not.

Nothing here asks a language model anything, and none of it needs a key.
"""

from datetime import date
from typing import Annotated, Any, Final, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from katalyst.api.worlds import RefusedEdit
from katalyst.domain import (
    Branch,
    BranchId,
    ImpossibleObservation,
    PricePayoff,
    Proposition,
    PropositionId,
    Sample,
    Violation,
    World,
)
from katalyst.engine import worlds as engine
from katalyst.engine.ids import BIGGEST_SEED
from katalyst.thesis.adapter import A_MOVE_IS_A_SHARE_OF_THE_PRICE, draws_of, moves_on
from katalyst.thesis.card import (
    THE_CHANCE_CAME_FROM,
    THE_GIVEBACK_FOLLOWED,
    Figure,
    Owner,
    TheTrade,
    WhatTakesYouOutShown,
    YourExit,
    computed,
    the_exit,
    the_rail,
    the_trade,
)
from katalyst.thesis.ceiling import ceiling_of
from katalyst.thesis.edge import priced
from katalyst.thesis.lift import what_takes_you_out
from katalyst.thesis.paths import ClaimMove, MarketChanceFrom, Paths, walk
from katalyst.thesis.position import Refusal, RefusalCode, first_touch, position_on

router = APIRouter(tags=["thesis"])

AskedWrongHere = Literal[
    "unknown_ending",
    "the_ending_names_no_trade",
    "horizon_outside_the_window",
    "nothing_agrees_with_what_happened",
]
"""The four refusals this route owns, as a closed list.

They are about the **request** rather than about the form: an ending that is not
on the map or names no trade, a horizon outside the window the map covers, and a
map on which nothing agrees with what *This happened* recorded.
"""

AskedWrong = RefusalCode | AskedWrongHere
"""Every reason this route will not answer, as one closed list of ten.

Six of them are the position form's own, written once in `thesis/position.py` and
reprinted here rather than reworded; four are this route's. A screen switches on
any of the ten the same way.
"""

REFUSES: Final[dict[AskedWrongHere, str]] = {
    "unknown_ending": ("That claim is not on this map, so there is no position to take on it."),
    "the_ending_names_no_trade": (
        "This claim names nothing you could buy or sell, so there is no position to take on it."
    ),
    "horizon_outside_the_window": (
        "The day you expect to be out is outside the window this map covers, so there is no "
        "path to walk to it."
    ),
    "nothing_agrees_with_what_happened": (
        "Nothing this map can produce agrees with what This happened was used to record, so "
        "there are no worlds left to read days off."
    ),
}
"""What each of the route's own refusals says, in plain words the reader can act on.

Written here, once, so the route, a screen and a test all print the same sentence
and nobody writes a second wording of the same rule.
"""

OWNS_THE_CHANCE: Final[dict[MarketChanceFrom, Owner]] = {
    "venue_quote": "venue",
    "sample_share": "computed",
    "base_world": "model",
    "reader": "reader",
}
"""Who owns the market's chance of a claim, by where that chance came from.

The four sources are four different voices and this product never merges them: a
venue published one, this program worked one out over the drawn worlds, the model
stated one, and the reader typed one. A screen holding the number is handed the
owner with it.
"""


class PositionRefused(BaseModel):
    """One thing this route will not do, the field at fault, and what it says.

    A refusal is never a blank: it names a stable code a screen can switch on, the
    field the reader should look at, and one plain sentence. Nothing is silently
    repaired, and every fault the request has comes back together — a form that
    reveals one mistake at a time is a form nobody finishes.
    """

    model_config = ConfigDict(frozen=True)

    code: AskedWrong = Field(description="Which rule this is, from the closed list of ten.")
    field: str = Field(description="The field at fault, named as the reader sees it.")
    sentence: str = Field(description="What the screen prints.")


class RefusedPosition(BaseModel):
    """Every reason a position could not be worked out, in a settled order."""

    detail: tuple[PositionRefused, ...] = Field(
        description="Every reason at once, never just the first one found."
    )


REFUSED: dict[int | str, dict[str, Any]] = {
    404: {
        "description": (
            "No example is stored under that name. The answer is one sentence naming the "
            "examples this program does ship with."
        )
    },
    422: {
        "model": RefusedEdit | RefusedPosition,
        "description": (
            "The request cannot be carried out as written, and there are two ways it can be. "
            "A branch that does not fit the map comes back as the list of violations the "
            "world routes give. A position the reader can fix comes back as the list of "
            "refusals — each with a stable code, the field at fault and one plain sentence. "
            "Read the first entry to know which: a violation names a `subject` and a "
            "`message`, a refusal names a `field` and a `sentence`. A body the server cannot "
            "read at all is also a 422, and says so in its own words."
        ),
    },
}
"""How a refused position is described to whatever generates the browser's types."""


class PositionRequest(BaseModel):
    """What it takes to work out a position: a map, a branch, a seed, an ending, and an exit.

    The first three are what every computed answer in this program is built from,
    and the same three give the same answer on any machine and at any time. The
    ending says which trade. The rest is the reader's own, and none of it is
    derived from anything: a map of claims cannot say where somebody should get
    out.
    """

    base_id: str = Field(description='The short name of the stored example, such as "hormuz".')
    branch: Branch | None = Field(
        default=None,
        description=(
            "The branch in force, sent whole because there is nowhere to keep one yet. Leave "
            "it out for the map with nothing done to it. A position is **not** an edit: it "
            "appears on no branch and moves nothing on the map."
        ),
    )
    seed: int = Field(
        ge=0,
        le=BIGGEST_SEED,
        description=(
            "The one number every random draw in the answer comes from — the drawn worlds and "
            "the price paths alike. Bounded by what a browser can hold exactly, so a browser "
            "can always send back a seed the server used."
        ),
    )
    ending: PropositionId = Field(
        description="The ending being traded. What it names and which way is read off its payoff."
    )
    entry: float = Field(
        gt=0.0,
        description="The price you entered at, in the instrument's own units. Yours.",
    )
    # The reader's three own numbers are **declared** here and never set, exactly
    # as they are on the card's own exit: written as an annotation with no value
    # beside it, so that the check which reads our own source and fails on anything
    # that sets a name called `stop`, `target` or `horizon` can tell a field a
    # reader fills in from a number somebody worked out. Required all the same — a
    # field with no default is one every caller has to send.
    stop: Annotated[
        float,
        Field(description="The price at which you get out for a loss. Yours, and never derived."),
    ]
    target: Annotated[
        float,
        Field(description="The price at which you get out for a gain. Yours, and never derived."),
    ]
    horizon: Annotated[
        date,
        Field(
            description=(
                "The day you expect to be out. The two first-touch shares are read to this day "
                "and no further, because reading to the end of whatever window the drawn "
                "worlds carry answers a question nobody asked."
            )
        ),
    ]
    risk_budget: float = Field(
        description=(
            "The share of your capital you are prepared to lose on this trade. What it "
            "implies about size is arithmetic on it and your stop, and is never a "
            "recommendation. Bounded by the position form rather than here, so that a "
            "reader who types a hundred instead of a hundredth is told what a risk budget "
            "is in the form's own words, beside every other fault at once."
        )
    )
    daily_move: float = Field(
        ge=0.0,
        description=(
            "How far the instrument moves in a day, in price units — one standard deviation "
            "of a day's change. Yours today: nothing in this program measures it."
        ),
    )
    versions: int = Field(
        default=engine.VERSIONS,
        gt=0,
        le=engine.MOST_VERSIONS,
        description="The outer loop the worlds beside this position are built at.",
    )
    worlds: int = Field(
        default=engine.WORLDS,
        gt=1,
        le=engine.MOST_WORLDS,
        description="The inner loop those worlds run.",
    )
    drawn_worlds: int = Field(
        default=engine.DRAWN_WORLDS,
        gt=0,
        le=engine.DRAWN_WORLDS,
        description=(
            "How many worlds to draw the event days from. A request above the ceiling is "
            "refused rather than quietly made smaller; the ceiling is the count the engine "
            "draws for itself, so the days a trade reads and the days a claim's own number "
            "was corrected by are one sample and not two."
        ),
    )


class WhatThePathApplied(BaseModel):
    """What one claim did to the price on the walk, and what the market had already priced.

    A price path that applied a claim's **whole** stated move on top of today's
    price would count that move twice, because today's price already reflects the
    market's own chance of the claim. So the path applies the **surprise** — the
    move scaled by one minus that chance — and gives the priced-in part back day by
    day while the claim has not happened. Which chance was used, where it came from,
    and what shape the giving back followed are all here, because every one of them
    moves the first-touch shares.
    """

    model_config = ConfigDict(frozen=True)

    claim: PropositionId = Field(description="The claim whose coming true moves the price.")
    says: str = Field(description="Its claim, in one sentence.")
    market_chance: Figure = Field(
        description="The market's own chance of the claim, which is what the path did not apply."
    )
    came_from: MarketChanceFrom = Field(
        description="Which of the four sources that chance came from, as a stable word."
    )
    stated_move: Figure = Field(
        description="How far the instrument moves if the claim comes true, as the model stated it."
    )
    level_gap: Figure = Field(
        description=(
            "That same move in the instrument's own price units, which is what a path takes."
        )
    )
    converted: str = Field(
        description="What turning a share of the price into price units costs, in plain words."
    )
    decay_shape: Literal["arrival_days", "straight_line", "nothing_given_back"] = Field(
        description="Which shape the giving back followed, as a stable word."
    )
    decay_says: str = Field(description="What that shape is, in plain words.")


class PositionAnswer(BaseModel):
    """The reader's exit, how often each end of it is reached first, and what takes them out.

    A state of the panel that can always be thrown away and rebuilt: the map, the
    branch, the seed and the number of worlds drawn are all on it, and the same
    four produce the same answer.
    """

    model_config = ConfigDict(frozen=True)

    base_id: str = Field(description="The map this position was worked out on.")
    branch_id: BranchId | None = Field(
        description="The branch in force, or nothing at all for the untouched map."
    )
    seed: int = Field(description="The one number every random draw behind this answer came from.")
    as_of: date = Field(description="The first day of the window the numbers were worked out over.")
    drawn_worlds: Figure = Field(description="How many worlds the event days were read off.")
    effective_draws: Figure = Field(
        description=(
            "How many equally-weighted worlds those worlds' weights are worth, which is what "
            "every floor in this answer is measured against."
        )
    )
    the_trade: TheTrade = Field(description="What is being traded, where, and which way.")
    your_exit: YourExit = Field(
        description=(
            "What you typed, what your own risk budget implies, how often each end is reached "
            "first, and the greyed ceiling that is never a size."
        )
    )
    takes_you_out: WhatTakesYouOutShown | None = Field(
        description=(
            "The claims over-represented in the worlds where your stop went first, ranked. "
            "Nothing at all where there was no first touch to rank them over, which is a "
            "contract ending — the reason is on the exit above."
        )
    )
    path_applied: tuple[WhatThePathApplied, ...] = Field(
        description=(
            "What each claim did to the price on the walk, and what the market had already "
            "priced of it. Empty where no claim on this map moves this instrument."
        )
    )


@router.post("/thesis/position", responses=REFUSED)
def take_a_position(request: PositionRequest) -> PositionAnswer:
    """Say how often each end of the reader's exit is reached first, and what takes them out.

    Six steps, and every one of them can be read off the answer afterwards. The
    branch is folded onto the map and the ending's payoff says what is traded and
    which way. The reader's four numbers are checked, all faults at once. Worlds are
    drawn forward from the same map, branch and seed, carrying the day each claim
    came on. A daily price path is walked through every one of them, applying only
    what the market has not already priced. The two first-touch shares are read to
    the reader's own horizon and no further. And the claims over-represented in the
    worlds where the stop went first are ranked beside them.

    **The greyed ceiling is read from the map with nothing fixed by an edit**, never
    from the branch the reader is looking at: a world in which something has been
    supposed or recorded answers a different question from a venue's price, so an
    edge read off it would be an edge against a question nobody asked.

    Args:
        request: Which map, which branch, which seed, which ending, and the
            reader's own entry, exit and risk budget.

    Returns:
        The trade, the exit with its two first-touch shares and its greyed ceiling,
        the rail of what takes the reader out, and what the path applied.

    Raises:
        HTTPException: With status 404 and a sentence naming the examples that do
            exist, when nothing is stored under that name. With status 422 and
            every reason at once, when the branch does not fit the map or the form
            has faults.
    """
    shown = _answered(
        engine.build_world(
            request.base_id,
            request.branch,
            request.seed,
            versions=request.versions,
            worlds=request.worlds,
        ),
        request.base_id,
    )
    ending = _the_ending(shown, request.ending)
    wanted = position_on(
        ending,
        entry=request.entry,
        stop=request.stop,
        target=request.target,
        horizon=request.horizon,
        risk_budget=request.risk_budget,
        daily_move=request.daily_move,
    )
    if isinstance(wanted, tuple):
        raise HTTPException(
            status_code=422, detail=[_reprinted(one).model_dump() for one in wanted]
        )

    draws = draws_of(_drawn(request))
    through = (wanted.horizon - draws.day_zero).days
    if not 1 <= through <= draws.days:
        raise HTTPException(
            status_code=422,
            detail=[_refusing("horizon_outside_the_window", "horizon").model_dump()],
        )

    moves = moves_on(ending, entry=wanted.entry)
    # A contract ending is walked and then refused, rather than never walked. The
    # sentence that refuses it lives in `position.py`, with the other five, and
    # asking there is what keeps it in one place; a branch here would be a second
    # place the rule had to be remembered. What it costs is one throwaway walk.
    paths = walk(draws, moves, entry=wanted.entry, daily_move=wanted.daily_move, seed=request.seed)
    touch = first_touch(paths, wanted)
    # The second world, and the reason there are two: an edge is read from the map
    # with **nothing** fixed by an edit, so this one is built with no branch at all
    # however much the reader has supposed on the one above.
    base = _answered(
        engine.build_world(
            request.base_id,
            None,
            request.seed,
            versions=request.versions,
            worlds=request.worlds,
        ),
        request.base_id,
    )
    ceiling = ceiling_of(priced(base, shown, wanted.ending, None, fee=None))
    return PositionAnswer(
        base_id=shown.base_id,
        branch_id=shown.branch_id,
        seed=request.seed,
        as_of=draws.day_zero,
        drawn_worlds=computed(
            float(draws.worlds), "how many worlds the event days were read off", kind="count"
        ),
        effective_draws=computed(
            draws.effective,
            "how many equally-weighted worlds those worlds' weights are worth",
            kind="count",
        ),
        the_trade=the_trade(ending, wanted),
        your_exit=the_exit(wanted, ceiling, touch, paths.market_chance),
        takes_you_out=(
            None
            if isinstance(touch, Refusal)
            else the_rail(shown, what_takes_you_out(draws, touch), paths.market_chance)
        ),
        path_applied=tuple(_applied(shown, paths, one, wanted.entry) for one in moves),
    )


def _drawn(request: PositionRequest) -> Sample:
    """Draw the worlds the event days are read off, or refuse in words when there are none.

    One thing a map can honestly do is contradict what was recorded on it: a *This
    happened* edit on a claim nothing this map produces agrees with leaves no
    weighted world to read days off at all. The engine says so by name, and this
    turns that into a sentence the reader can act on rather than a server error.

    Args:
        request: The map, the branch, the seed and how many worlds to draw.

    Returns:
        The drawn worlds.

    Raises:
        HTTPException: With status 404 when nothing is stored under that name, or
            422 when the branch does not fit the map, or when nothing on the map
            agrees with what was recorded.
    """
    try:
        drawn = engine.sample_of(
            request.base_id,
            request.branch,
            request.seed,
            versions=request.versions,
            drawn=request.drawn_worlds,
        )
    except ImpossibleObservation:
        raise HTTPException(
            status_code=422,
            detail=[_refusing("nothing_agrees_with_what_happened", "branch").model_dump()],
        ) from None
    return _answered(drawn, request.base_id)


def _the_ending(shown: World, wanted: PropositionId) -> Proposition:
    """Find the claim being traded on the map, and refuse in words when there is no trade on it.

    Args:
        shown: The world the reader is looking at, whose map holds the claim.
        wanted: The claim the request named.

    Returns:
        That claim.

    Raises:
        HTTPException: With status 422 when the map does not carry it, or when it
            names nothing anybody could buy or sell. Both are things the reader can
            act on — ask for a different ending — so neither is a server error.
    """
    found = next((one for one in shown.graph.propositions if one.id == wanted), None)
    if found is None:
        raise HTTPException(
            status_code=422, detail=[_refusing("unknown_ending", "ending").model_dump()]
        )
    if found.payoff is None:
        raise HTTPException(
            status_code=422,
            detail=[_refusing("the_ending_names_no_trade", "ending").model_dump()],
        )
    return found


def _applied(shown: World, paths: Paths, move: ClaimMove, entry: float) -> WhatThePathApplied:
    """Say what one claim did to the price, and what the market had already priced of it.

    Args:
        shown: The world whose map names the claim.
        paths: The walked paths, which carry the chance actually applied to each
            claim and the shape its giving back followed — read from the walk's own
            record rather than from what was handed in, so nothing here can name a
            chance the path did not use.
        move: The level gap this claim was walked with.
        entry: The price the reader entered at, which the stated share was
            converted against.

    Returns:
        One row, with an owner on every number.
    """
    claim = next(one for one in shown.graph.propositions if one.id == move.claim)
    chance = paths.market_chance[move.claim]
    shape = paths.decay_shape[move.claim]
    payoff = claim.payoff
    stated = payoff.move if isinstance(payoff, PricePayoff) else 0.0
    return WhatThePathApplied(
        claim=claim.id,
        says=claim.claim,
        market_chance=Figure(
            value=chance.value,
            kind="likelihood",
            owner=OWNS_THE_CHANCE[chance.came_from],
            about="the market's own chance of this claim, which the path did not apply again",
            source=THE_CHANCE_CAME_FROM[chance.came_from],
        ),
        came_from=chance.came_from,
        stated_move=Figure(
            value=stated,
            kind="move",
            owner="model",
            about=(
                "how far the instrument moves if this claim comes true, as a share of its "
                "price, as the model stated it"
            ),
        ),
        level_gap=computed(
            move.move,
            "that same move in the instrument's own price units, which is what a path takes",
            f"the model's stated share, times the price you entered at, {entry}",
            kind="price",
        ),
        converted=A_MOVE_IS_A_SHARE_OF_THE_PRICE,
        decay_shape=shape,
        decay_says=THE_GIVEBACK_FOLLOWED[shape],
    )


def _refusing(code: AskedWrongHere, field: str) -> PositionRefused:
    """One of the route's own refusals, with its sentence written once for every screen."""
    return PositionRefused(code=code, field=field, sentence=REFUSES[code])


def _reprinted(one: Refusal) -> PositionRefused:
    """Reprint the form's own refusal on the wire, keeping its code, its field and its words.

    The sentence is `thesis/position.py`'s, unchanged. A second wording of the same
    rule is exactly what a shared list of sentences exists to prevent.

    Args:
        one: What the form refused.

    Returns:
        The same refusal, as the shape this route answers with.
    """
    return PositionRefused(code=one.code, field=one.field, sentence=one.sentence)


def _answered[Answer](outcome: Answer | list[Violation] | None, base_id: str) -> Answer:
    """Hand back what the engine gave, or turn its refusal into the status that says what happened.

    Three outcomes, each somebody's fault in a different place. Nothing at all
    means the name matches no stored example: 404. A list of violations means the
    branch does not fit the map, which the reader can still repair: 422, with every
    reason at once. Anything else is the answer.

    Args:
        outcome: What the engine gave back.
        base_id: The name that was asked for, for the sentence when it matches
            nothing.

    Returns:
        The answer, when there is one.

    Raises:
        HTTPException: With status 404 or 422, carrying text a person can read.
    """
    if outcome is None:
        raise HTTPException(status_code=404, detail=engine.no_such_example(base_id))
    if isinstance(outcome, list):
        raise HTTPException(status_code=422, detail=[one.model_dump() for one in outcome])
    return outcome
