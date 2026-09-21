"""The export: the card as a document a program reads, and a page a person reads.

A card is a state of a panel. This file turns one into something the reader keeps:
a declarative document stamped with the map, the branch, the seed and the day, so
it can be replayed; and the same thing written out as plain text.

**Legs and conditions, never an order.** The document is `legs[]` and
`conditions[]`. A venue's combination-leg structure is an **order** format, and a
document shaped like one would imply it could be submitted somewhere. This product
is not an execution layer, it names no order type and it guarantees no fill, so it
does not borrow the shape of something that does.

**It carries its own limits as data.** `refuses` holds eight sentences, `not_advice`
holds one, and `execution` holds the single thing this product will say about
getting out. They are fields rather than a footer because a footer is dropped by
whatever reads the document next, and a field has to be read. A program that
ingests the document ingests the caveats with it.

**A shock the reader placed carries `probability: null`, and the schema will not
allow anything else.** They supposed it; that is not a forecast. Writing the field
and fixing it at nothing says so more loudly than leaving it out, because an
absent field reads as an oversight and a null one reads as an answer.

**The schema is generated from these shapes and committed beside them.** The file
`export.schema.json` is exactly what this module produces, and a test compares the
two byte for byte — so the committed description of the document can never drift
from the document.

What this file must never do
----------------------------
- Never mirror a venue's order format, and never name an order type or promise a
  fill.
- Never drop the refusals, the not-advice line or the execution sentence, and
  never move them into a footer.
- Never write a number without its owner. Every number in the document is a
  figure carrying who it belongs to and where it came from.
- Never attach a probability to a shock the reader placed.
- Never headline an average outcome.
- Never compute anything. It re-shapes a card and renders it, and a number that
  is not already on the card is not in the document.
"""

import json
from collections.abc import Callable, Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain import BranchId, PropositionId, two_figures
from katalyst.thesis.card import (
    OWNER_SAYS,
    Card,
    CeilingShown,
    Figure,
    Kind,
    NotPriced,
    PricedIn,
    ShockRow,
    TailRow,
    UnhedgeableShown,
    WhatCarriesIt,
    WhatElseCanITrade,
    WhatIsPricedIn,
    WhatTakesYouOutShown,
    WhatToWatch,
)
from katalyst.thesis.position import Side, Trades

SchemaName = Literal["katalyst.thesis/1"]
"""The one name a document of this shape may call itself.

Written as a closed list of one so that the committed description **pins** it: a
document calling itself something else is refused by any program checking against
that description, rather than passing as a thesis it is not.
"""

SCHEMA_NAME: SchemaName = "katalyst.thesis/1"
"""What this document calls itself, so a program reading one knows what it has.

The number changes when a field is removed or its meaning changes, and never when
a field is added: a reader of version one must go on being able to read a document
that has grown.
"""

EXPORT_SCHEMA_FILE = Path(__file__).with_name("export.schema.json")
"""Where the committed description of this document lives.

Beside the code that generates it, because the two must be read together and a
description that lives somewhere else is a description that drifts. A test
regenerates it and compares byte for byte.
"""


class Stamp(BaseModel):
    """The three things a card can be rebuilt from, plus the day it was worked out for.

    A world is a computed result and never a source of truth: it can always be
    thrown away and rebuilt from the base map, the branch and the seed. Stamping
    them here is what makes the document replayable rather than merely readable.
    """

    model_config = ConfigDict(frozen=True)

    base_id: str = Field(description="The map this was built from.")
    branch_id: BranchId | None = Field(
        description="The branch folded on, or nothing at all for the untouched map."
    )
    seed: int = Field(description="The one number every random draw behind this came from.")
    as_of: date = Field(description="The first day of the window the numbers were worked out over.")


class Hypothesis(BaseModel):
    """The claim the map starts from."""

    model_config = ConfigDict(frozen=True)

    id: PropositionId = Field(description="Its identifier on the map.")
    claim: str = Field(description="The claim, in one sentence.")


class Leg(BaseModel):
    """One position, with everything a reader of this document needs about it.

    A leg is complete on its own: what is traded, which way, what the model says,
    what a venue charges, the two edges or the named refusal, the break-even, the
    size the reader's own risk budget implies, and the greyed ceiling with its
    label attached. A program that reads a leg should not have to look anywhere
    else to know what it may and may not do with the numbers in it.

    One leg is what this version builds, because one position is what the reader
    holds. The field is a list so that two positions are two legs rather than a
    different document.
    """

    model_config = ConfigDict(frozen=True)

    ending: PropositionId = Field(description="The ending this leg is on.")
    claim: str = Field(description="That ending's claim, in one sentence.")
    trades: Trades = Field(
        description="Whether it names something traded whose price moves, or a contract."
    )
    instrument: str = Field(description="What is bought or sold, named the way its venue names it.")
    side: Side = Field(description="Which way the trade is pointed.")
    venue: str | None = Field(description="The venue, where the ending names a contract.")
    contract_id: str | None = Field(description="The venue's own identifier for that contract.")
    contract_side: Literal["yes", "no"] | None = Field(
        description="Which outcome of the contract the ending takes."
    )
    resolves: date = Field(description="The day the ending's own claim is judged.")
    resolution_test: str = Field(description="The test that settles it, word for word.")
    resolved_by: str = Field(description="Who applies that test.")
    priced_in: WhatIsPricedIn = Field(
        description=(
            "The model's number, a venue's two prices and the two edges — or the named "
            "refusal and the break-even that stands where no edge could be built."
        )
    )
    size: Figure = Field(
        description=(
            "The share of capital the reader's own risk budget implies. Their rule's "
            "arithmetic, and never a recommendation."
        )
    )
    ceiling: CeilingShown = Field(
        description=(
            "The greyed quartered-Kelly ceiling, carried as a value with its label attached, "
            "so a program that reads the number reads *never size to this* with it."
        )
    )


class ShockExported(BaseModel):
    """A shock the reader placed, with its probability written down as nothing at all.

    The field exists and is fixed at nothing. An absent field reads as an
    oversight; a field that says *null* says that nobody claims to know, which is
    the truth: the reader supposed this, and supposing something is not a statement
    about how likely it is.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="What they supposed, in their own words.")
    placed_by: Literal["reader"] = Field(description="Who placed it. Always the reader.")
    probability: None = Field(
        description=(
            "Always nothing at all. A shock is supposed, not forecast, and this document "
            "will not carry a number here."
        ),
    )
    change_to_the_position: Figure = Field(
        description="What the position is worth on that branch less what it is worth without it."
    )
    says: str = Field(description="Why there is no probability here.")


class Conditions(BaseModel):
    """The computed lists, each row carrying what it rests on.

    These are the conditions the legs above hold under: what carries them, what
    takes the reader out, what to watch and by when, what cannot be watched for,
    the tails, and any shock the reader placed.
    """

    model_config = ConfigDict(frozen=True)

    carried_by: tuple[WhatCarriesIt, ...] = Field(
        description="The claims whose arrows carry most of the hypothesis's effect on the ending."
    )
    takes_you_out: WhatTakesYouOutShown = Field(
        description="The claims over-represented in the worlds where the stop went first."
    )
    watch: tuple[WhatToWatch, ...] = Field(
        description="What is adverse, resolves before the ending, and can be seen by anybody."
    )
    unhedgeable: tuple[UnhedgeableShown, ...] = Field(
        description="What is adverse and cannot be watched for, each with its reason."
    )
    tails: tuple[TailRow, ...] = Field(
        description="Claims that are unlikely and would hurt, ranked by harm and never averaged."
    )
    shocks: tuple[ShockExported, ...] = Field(
        description="Suppositions the reader placed, each with no probability."
    )


class RiskExit(BaseModel):
    """What the reader typed about getting out, and how often each end is reached first.

    The size their risk budget implies and the greyed ceiling are **not** here:
    they are on the leg, because a leg has to be complete on its own.
    """

    model_config = ConfigDict(frozen=True)

    entry: Figure = Field(description="The price they entered at.")
    # Declared, never set — see the same three fields on the card's own exit for
    # why they are written as an annotation with no value beside it.
    stop: Annotated[
        Figure, Field(description="The price at which they get out for a loss. Never derived.")
    ]
    target: Annotated[
        Figure, Field(description="The price at which they get out for a gain. Never derived.")
    ]
    horizon: Annotated[date, Field(description="The day by which they expect to be out.")]
    risk_budget: Figure = Field(description="The share of capital they are prepared to lose here.")
    stop_first: Figure | None = Field(
        description="How often the stop is touched before the target, over the drawn worlds."
    )
    target_first: Figure | None = Field(description="How often the target is touched first.")
    neither: Figure | None = Field(
        description="How often the window closes with neither touched. The three sum to one."
    )
    stop_at: Figure | None = Field(
        description="The level actually checked for the stop, after the barrier shift."
    )
    target_at: Figure | None = Field(description="The same, for the target.")
    through: Figure | None = Field(
        description=(
            "How many days of the window the shares were read to: the reader's own horizon, "
            "counted from the day the window opened. Shares over a window nobody named are "
            "numbers nobody can check."
        )
    )
    first_touch_refused: str | None = Field(
        description="Why there is no first touch here. Nothing where the shares were worked out."
    )
    method: str | None = Field(description="How the shares were arrived at.")


class Export(BaseModel):
    """The whole document: legs, conditions, the exit, and the limits carried as data."""

    model_config = ConfigDict(frozen=True)

    schema_name: SchemaName = Field(
        alias="schema",
        serialization_alias="schema",
        description="What this document calls itself, so a program knows what it has.",
    )
    map: Stamp = Field(description="The map, the branch, the seed and the day, so it replays.")
    hypothesis: Hypothesis = Field(description="The claim the map starts from.")
    legs: tuple[Leg, ...] = Field(description="One position, complete on its own.")
    conditions: Conditions = Field(description="The computed lists the legs hold under.")
    risk_exit: RiskExit = Field(description="What the reader typed about getting out.")
    what_else: WhatElseCanITrade = Field(
        description="Every tradeable ending on the map, ranked by two rules kept apart."
    )
    refuses: tuple[str, ...] = Field(
        min_length=1,
        description=(
            "What this document does not know, in full sentences, carried as data. Never "
            "empty: a document with no limits is a claim nobody on this map may make."
        ),
    )
    not_advice: str = Field(description="What this document is not, in one line.")
    execution: str = Field(
        description="The one thing this product says about getting out, and nothing else."
    )


def export_of(card: Card) -> Export:
    """Re-shape one card into the document a program reads.

    Nothing is computed here and nothing is dropped: every number in the document
    is a figure already on the card, carrying the owner the card gave it.

    Args:
        card: The card to write out.

    Returns:
        The document, stamped with the map, the branch, the seed and the day.
    """
    exit_ = card.your_exit
    leg = Leg(
        ending=card.the_trade.ending,
        claim=card.the_trade.says,
        trades=card.the_trade.trades,
        instrument=card.the_trade.instrument,
        side=card.the_trade.side,
        venue=card.the_trade.venue,
        contract_id=card.the_trade.contract_id,
        contract_side=card.the_trade.contract_side,
        resolves=card.the_trade.resolves,
        resolution_test=card.the_trade.resolution_test,
        resolved_by=card.the_trade.resolved_by,
        priced_in=card.priced_in,
        size=exit_.implied_size,
        ceiling=exit_.ceiling,
    )
    return Export(
        schema=SCHEMA_NAME,
        map=Stamp(
            base_id=card.base_id,
            branch_id=card.branch_id,
            seed=card.seed,
            as_of=card.as_of,
        ),
        hypothesis=Hypothesis(id=card.hypothesis, claim=card.hypothesis_says),
        legs=(leg,),
        conditions=Conditions(
            carried_by=card.carried_by,
            takes_you_out=card.takes_you_out,
            watch=card.watch,
            unhedgeable=card.unhedgeable,
            tails=card.tails,
            shocks=tuple(_shock(one) for one in card.shocks),
        ),
        risk_exit=RiskExit(
            entry=exit_.entry,
            stop=exit_.stop,
            target=exit_.target,
            horizon=exit_.horizon,
            risk_budget=exit_.risk_budget,
            stop_first=exit_.stop_first,
            target_first=exit_.target_first,
            neither=exit_.neither,
            stop_at=exit_.stop_at,
            target_at=exit_.target_at,
            through=exit_.through,
            first_touch_refused=exit_.first_touch_refused,
            method=exit_.method,
        ),
        what_else=card.what_else,
        refuses=card.does_not_know.refuses,
        not_advice=card.does_not_know.not_advice,
        execution=card.does_not_know.execution,
    )


def _shock(row: ShockRow) -> ShockExported:
    """Write one shock out with its probability fixed at nothing at all.

    Args:
        row: The shock as the card carries it, which has no field a probability
            could go in.

    Returns:
        The exported row, whose `probability` is written and is nothing.
    """
    return ShockExported(
        name=row.name,
        placed_by=row.placed_by,
        probability=None,
        change_to_the_position=row.change_to_the_position,
        says=row.says,
    )


def as_json(export: Export) -> str:
    """Write the document out as text, the same way every time.

    Keys are sorted and the indentation is fixed, so two runs over the same card
    produce the same bytes and a difference between two documents is a difference
    in what they say.

    Args:
        export: The document.

    Returns:
        The document as text, ending in a newline.
    """
    written = export.model_dump(mode="json", by_alias=True)
    return json.dumps(written, indent=2, sort_keys=True) + "\n"


def schema_json() -> str:
    """Write the description of this document out as text, the same way every time.

    Args:
        None.

    Returns:
        The document's description as text, ending in a newline. This is exactly
        what the file beside this module holds, and a test says so.
    """
    return json.dumps(Export.model_json_schema(by_alias=True), indent=2, sort_keys=True) + "\n"


# --- The page a person reads -------------------------------------------------


def two_significant(value: float) -> str:
    """Write a number that is not a likelihood: two significant figures, sign and all.

    **A move is not a likelihood.** The rule that writes a likelihood turns
    anything under a hundredth into `<.01` and anything over ninety-nine
    hundredths into `>.99`, because a likelihood of `.0090` is one this product
    declines to state that precisely. A **move** of `.0090` is a different thing
    entirely: it is a real quantity a reader acts on, and guarding it would be a
    lie about an edge. So a move, a share of capital and a ratio come through here
    instead — two significant figures, the sign kept, the nought before the point
    dropped, and no guard at either end.

    Both figures are always printed, so `.0090` and not `.009`: dropping a trailing
    nought would claim less precision than we have.

    **Never scientific notation.** Asking Python for two significant figures
    directly gives `9.0e-03` below a hundredth, which is not a sentence anybody can
    read aloud. The rounding is done on the number's own decimal digits instead —
    the shortest decimal that reads back as this exact number, its point shifted by
    counting rather than by multiplying — which is how the likelihood rule does it
    too.

    Args:
        value: The number.

    Returns:
        It, written out. Exactly `0` where it is nothing at all, because two
        significant figures of nothing is still nothing.
    """
    exact = Decimal(repr(value))
    if exact == 0:
        return "0"
    rounded = exact.quantize(Decimal(1).scaleb(exact.adjusted() - 1), rounding=ROUND_HALF_UP)
    return _without_the_leading_nought(format(rounded, "f"))


def as_it_is(value: float) -> str:
    """Write a price, a count or a number of days as it stands.

    None of the three is a likelihood and none is a move: a price is money in the
    instrument's or the contract's own units, a count is how many worlds, a day is
    a day. Rounding any of them would be this file inventing precision it was not
    given, so the shortest decimal that reads back as the number is what is
    written, with a trailing `.0` dropped because `70.0` worlds is not a thing.

    Args:
        value: The number.

    Returns:
        It, written out, never in scientific notation.
    """
    exact = Decimal(repr(value)).normalize()
    return format(exact, "f")


HOW_A_NUMBER_IS_WRITTEN: dict[Kind, Callable[[float], str]] = {
    "likelihood": two_figures,
    "share": two_figures,
    "move": two_significant,
    "size": two_significant,
    "ratio": two_significant,
    "price": as_it_is,
    "count": as_it_is,
    "days": as_it_is,
}
"""Which rule writes each kind of number, as a closed table.

One entry per kind, so that adding a kind without deciding how it is written is a
failure the type checker points at rather than a number that quietly prints six
figures.
"""


def _without_the_leading_nought(written: str) -> str:
    """Drop the nought before the point, keeping the sign where there is one.

    Args:
        written: A number already written out, such as `0.0090` or `-0.0040`.

    Returns:
        The same without its leading nought — `.0090`, `-.0040` — and unchanged
        where there is none.
    """
    if written.startswith("0."):
        return written[1:]
    if written.startswith("-0."):
        return "-" + written[2:]
    return written


def say(figure: Figure) -> str:
    """Write one number out, by the rule its kind names, with its owner beside it.

    Every number this program shows a reader names who it belongs to in the same
    breath, and is written by the one rule for numbers of its kind. Both live here,
    once, so the page below cannot show a number without an owner or write a
    likelihood at six significant figures.

    Args:
        figure: The number.

    Returns:
        One line: what it is, what it is, whose it is, and where it came from.
    """
    write = HOW_A_NUMBER_IS_WRITTEN[figure.kind]
    said = write(figure.value)
    if figure.lo is not None and figure.hi is not None:
        said += f" (range {write(figure.lo)} to {write(figure.hi)})"
    said += f" — {OWNER_SAYS[figure.owner]}"
    if figure.source is not None:
        said += f", {figure.source}"
    return f"{figure.about}: {said}"


def _lines(figures: Sequence[Figure | None]) -> list[str]:
    """Write a run of numbers out as list items, skipping the ones that are not there.

    An absent number is not written as a blank line and never as a zero: whatever
    section holds it says in words why it is absent, which is a different sentence
    from any number.

    Args:
        figures: The numbers, in the order they should be read. An entry that is
            nothing at all is left out.

    Returns:
        One list item per number that is there.
    """
    return [f"- {say(one)}" for one in figures if one is not None]


def as_markdown(card: Card) -> str:
    """Write the card out as a page a person reads, with an owner on every number.

    The nine sections the panel shows, in the same order, ending with what this
    card does not know. Every number carries its owner on its own line; there
    is no way to write one that does not, because the one place a number is written
    is `say`.

    Args:
        card: The card to write out.

    Returns:
        The page, as text.
    """
    out: list[str] = [
        f"# {card.hypothesis_says}",
        "",
        f"Map `{card.base_id}` · branch `{card.branch_id or 'none'}` · seed `{card.seed}` · "
        f"window opens {card.as_of.isoformat()}",
        "",
    ]
    out += _the_trade(card)
    out += _carried_by(card)
    out += _priced_in(card.priced_in)
    out += _takes_you_out(card.takes_you_out)
    out += _watch(card)
    out += _your_exit(card)
    out += _tails_and_shocks(card)
    out += _what_else(card.what_else)
    out += _does_not_know(card)
    return "\n".join(out)


def _the_trade(card: Card) -> list[str]:
    """Write the trade section.

    Args:
        card: The card.

    Returns:
        The lines.
    """
    trade = card.the_trade
    named = f"contract {trade.contract_id} at {trade.venue}, {trade.contract_side} side"
    return [
        "## The trade",
        "",
        f"{trade.says}",
        "",
        f"- {trade.side} {trade.instrument}"
        + (f" ({named})" if trade.contract_id is not None else ""),
        f"- Judged {trade.resolves.isoformat()} by {trade.resolved_by}: {trade.resolution_test}",
        "",
    ]


def _carried_by(card: Card) -> list[str]:
    """Write the *what carries it* section.

    Args:
        card: The card.

    Returns:
        The lines.
    """
    out = ["## What carries it", ""]
    if not card.carried_by:
        out += ["Nothing has been worked out about which claims carry the effect.", ""]
        return out
    for one in card.carried_by:
        out += [f"**{one.claim}** — {one.says}", ""]
        out += _lines((one.points, one.share))
        out += [""]
    return out


def _priced_in(priced: WhatIsPricedIn) -> list[str]:
    """Write the *what is priced in* section, whichever of the two answers it is.

    Args:
        priced: The edge against a venue's prices, or the named refusal.

    Returns:
        The lines.
    """
    out = ["## What is priced in", ""]
    if isinstance(priced, NotPriced):
        return out + _refused(priced)
    return out + _an_edge(priced)


def _an_edge(priced: PricedIn) -> list[str]:
    """Write an edge out, with the side it favours and the break-even beside it.

    Args:
        priced: The edge.

    Returns:
        The lines.
    """
    read_on = priced.quote.read_on.isoformat()
    out = [f"{priced.quote.venue}, read {read_on} ({priced.quote.how}).", ""]
    out += _lines(
        (
            priced.model,
            priced.pays_on,
            priced.quote.bid,
            priced.quote.offer,
            priced.quote.midpoint,
            priced.buying,
            priced.selling,
            priced.buy_below,
            priced.sell_above,
        )
    )
    if priced.fee is not None:
        out += _lines((priced.fee,))
    if priced.fee_is_unknown is not None:
        out += [f"- {priced.fee_is_unknown}"]
    out += ["", f"Leads with: {priced.headline.replace('_', ' ')}."]
    if priced.not_headlined_because is not None:
        out += [f"{priced.not_headlined_because}"]
    out += [""]
    if priced.mixture is not None:
        out += [f"You supposed **{priced.mixture.supposed}**. {priced.mixture.says}", ""]
        out += _lines(
            (
                priced.mixture.weight_supposed,
                priced.mixture.weight_otherwise,
                priced.mixture.reading_supposed,
                priced.mixture.reading_otherwise,
            )
        )
        out += [""]
    return out


def _refused(priced: NotPriced) -> list[str]:
    """Write a refusal out, with the break-even that stands where the edge would be.

    Args:
        priced: The refusal.

    Returns:
        The lines.
    """
    out = [priced.sentence, ""]
    standing = tuple(
        one
        for one in (priced.buy_below, priced.sell_above, priced.price_break_even, priced.fee)
        if one is not None
    )
    out += _lines(standing)
    if priced.fee_is_unknown is not None:
        out += [f"- {priced.fee_is_unknown}"]
    if priced.costs_are_unknown is not None:
        out += [f"- {priced.costs_are_unknown}"]
    out += [""]
    return out


def _takes_you_out(rail: WhatTakesYouOutShown) -> list[str]:
    """Write the rail of claims over-represented where the stop went first.

    Args:
        rail: The rail.

    Returns:
        The lines.
    """
    out = ["## What takes you out", "", rail.sample_says + ".", ""]
    out += _lines((rail.draws, rail.stop_first_worlds, rail.floor))
    out += [""]
    if rail.too_few_draws is not None:
        out += [rail.too_few_draws, ""]
    for row in rail.rows:
        out += [f"**{row.claim}** — {row.says}", ""]
        out += _lines(
            (
                row.lift,
                row.came_on_first,
                row.coverage,
                row.came_on,
                row.draws,
                row.days_before_the_stop,
            )
        )
        if row.no_days_because is not None:
            out += [f"- {row.no_days_because}"]
        out += [""]
    for left in rail.left_off:
        out += [f"- Left off — {left}"]
    if rail.left_off:
        out += [""]
    return out


def _watch(card: Card) -> list[str]:
    """Write the watchlist and what cannot be watched for.

    Args:
        card: The card.

    Returns:
        The lines.
    """
    out = ["## What to watch", ""]
    if not card.watch:
        out += ["Nothing on this map is adverse, resolves in time, and can be seen.", ""]
    for one in card.watch:
        out += [
            f"**{one.claim}** — {one.says}",
            "",
            f"- Judged {one.resolves.isoformat()}, published by {one.observed_by}",
        ]
        out += _lines((one.hurts_by,))
        out += [""]
    if card.unhedgeable:
        out += ["### Unhedgeable", ""]
        out += [
            f"- **{one.claim}** — {one.why} Judged {one.resolves.isoformat()}; "
            + ("the answer is published." if one.can_be_seen else "nobody publishes the answer.")
            for one in card.unhedgeable
        ]
        out += [""]
    return out


def _your_exit(card: Card) -> list[str]:
    """Write the reader's own exit, the size it implies and the greyed ceiling.

    Args:
        card: The card.

    Returns:
        The lines.
    """
    exit_ = card.your_exit
    out = ["## Your exit", ""]
    out += _lines((exit_.entry, exit_.stop, exit_.target, exit_.risk_budget, exit_.implied_size))
    out += [f"- Horizon: {exit_.horizon.isoformat()} — {OWNER_SAYS['reader']}", ""]
    touches = tuple(
        one
        for one in (
            exit_.stop_first,
            exit_.target_first,
            exit_.neither,
            exit_.stop_at,
            exit_.target_at,
            exit_.through,
        )
        if one is not None
    )
    if touches:
        out += _lines(touches)
        out += [""]
    if exit_.sample_says is not None:
        out += [exit_.sample_says + ".", ""]
    if exit_.method is not None:
        out += [exit_.method, ""]
    if exit_.first_touch_refused is not None:
        out += [exit_.first_touch_refused, ""]
    out += [f"### Ceiling — {exit_.ceiling.warning}", ""]
    ceiling = tuple(one for one in (exit_.ceiling.fraction, exit_.ceiling.at) if one is not None)
    if ceiling:
        out += _lines(ceiling)
    if exit_.ceiling.taken_by is not None:
        out += [f"- Worked out for {exit_.ceiling.taken_by}"]
    if exit_.ceiling.sentence is not None:
        out += [f"- {exit_.ceiling.sentence}"]
    out += [""]
    return out


def _tails_and_shocks(card: Card) -> list[str]:
    """Write the tails, worst harm first, and any shock the reader placed.

    Args:
        card: The card.

    Returns:
        The lines.
    """
    out = ["## Tails and shocks", ""]
    if not card.tails:
        out += ["No claim on this map is both unlikely and enough to hurt.", ""]
    for one in card.tails:
        out += [f"**{one.claim}** — {one.says}", ""]
        out += _lines((one.likelihood, one.harm))
        out += [f"- {one.what_could_be_done}", ""]
    for shock in card.shocks:
        out += [f"**{shock.name}** — placed by {shock.placed_by}", ""]
        out += _lines((shock.change_to_the_position,))
        out += [f"- {shock.says}", ""]
    return out


def _what_else(what_else: WhatElseCanITrade) -> list[str]:
    """Write the two rankings, each under the name of the rule that made it.

    Args:
        what_else: The two lists and everything neither could rank.

    Returns:
        The lines.
    """
    out = ["## What else can I trade", "", what_else.two_rules, ""]
    for title, rows in (
        ("Ranked by the size of its edge", what_else.by_the_size_of_its_edge),
        ("Ranked by the shift times the move", what_else.by_the_shift_times_the_move),
    ):
        out += [f"### {title}", ""]
        if not rows:
            out += ["Nothing on this map is ranked by this rule.", ""]
        for row in rows:
            out += [f"**{row.ending}** — {row.says} ({row.trades}: {row.instrument})", ""]
            out += _lines((row.key, *row.made_of))
            if row.not_headlined_because is not None:
                out += [f"- Not led with: {row.not_headlined_because}"]
            out += [""]
    if what_else.not_ranked:
        out += ["### Not ranked", ""]
        out += [f"- **{one.ending}** — {one.sentence}" for one in what_else.not_ranked]
        out += [""]
    return out


def _does_not_know(card: Card) -> list[str]:
    """Write the limits, in full sentences, at the end and never as a footer.

    Args:
        card: The card.

    Returns:
        The lines.
    """
    out = ["## What this does not know", ""]
    out += [f"- {one}" for one in card.does_not_know.refuses]
    out += ["", card.does_not_know.execution, "", card.does_not_know.not_advice, ""]
    return out
