"""The greyed size ceiling: a quartered Kelly at the unfavourable end of the model's range.

The **Kelly rule** is the bet size that makes capital grow fastest in the long run
given a stated edge. It is notoriously aggressive — it assumes the stated edge is
right — so dividing it by four is a common working limit among the people who use
it at all.

This file works one out, and it is shown **greyed, beside the arithmetic on the
reader's own risk budget, under the words *never size to this***. It is a ceiling,
not a size. The only number that sets a size is the reader's own risk budget.

**At the unfavourable end of the model's range**, always: the end that makes the
edge smallest, never the middle and never the flattering end. A range is the
model's own statement of how unsure it is, and a ceiling built at the middle of it
is a ceiling that ignores the statement.

**When it appears at all.** A ceiling needs an edge, and an edge exists only for an
ending naming a venue contract, with a live quote, read from the world with nothing
fixed by an edit. So:

| The case | The ceiling |
|---|---|
| A contract ending, a live quote, nothing fixed by an edit | the number, greyed, labelled |
| Worth taking at one end of the model's range and not the other | **zero**, with its reason |
| Any refusal from the edge: a fixed value, no quote, no contract, settled | **absent** |

**Zero and absent are different answers and this file says which.** Zero means the
arithmetic ran and came out at nothing to put on; absent means there was no
arithmetic to run. Neither is ever a blank.

**The cost, taken knowingly.** The ceiling rests on a probability nobody has
calibrated, and a reader who ignores the label has been handed a size. The
unfavourable end and the greying are what make that bearable.

What this file must never do
----------------------------
- Never build a ceiling at the middle or the flattering end of the model's range.
- Never return a number where an edge was refused, and never return nothing where
  the arithmetic ran. A blank is neither answer.
- Never call it a size, and never print it without the words it carries.
- Never size anything. It is a ceiling beside the reader's own arithmetic, and
  the reader's risk budget is the only thing that sets a size.
"""

from dataclasses import dataclass
from typing import Final, Literal

from katalyst.thesis.edge import Edge, NotComparable

NEVER_SIZE_TO_THIS = "never size to this"
"""The words the ceiling is always shown under, carried as data rather than as copy.

A warning written into a screen is a warning one screen has. Carried on the value,
every screen and the export have the same one and none of them can print the
number without it.
"""

QUARTER: Final = 4.0
"""What the Kelly fraction is divided by.

The full Kelly rule assumes the stated edge is exactly right, and a model's number
is not. Quartering it is the common working limit among people who use the rule at
all, and it is a stated choice rather than a measured one.
"""

THE_RANGE_DISAGREES = (
    "The model's own range does not agree which side of this price to be, so there is no "
    "size to put a ceiling on."
)
"""What is printed when the edge changes sign across the model's stated range."""

A_CEILING_NEEDS_AN_EDGE = "A ceiling needs an edge."
"""What every absent ceiling says first, before the refusal's own sentence.

One sentence, not four: whichever way an edge was refused, the consequence for the
ceiling is the same, and the refusal already carries the reason in its own words.
"""

TakenBy = Literal["buying", "selling"]
"""Which side of the venue's book the ceiling was worked out for.

You buy at the offer and sell at the bid, and the two give different fractions, so
the answer says which one it is about.
"""


@dataclass(frozen=True)
class Ceiling:
    """The most of their capital the Kelly rule would put on, quartered — and never a size.

    Attributes:
        fraction: The share of capital, quartered, at the unfavourable end of the
            model's range. **Nothing at all** where there was no edge to work it
            out from — which is a different answer from a fraction of zero.
        taken_by: Which side the fraction is about, or nothing where there is no
            fraction.
        at: The likelihood the fraction was worked out at: the unfavourable end of
            the model's range for the side of the trade. Nothing where there is no
            fraction.
        warning: The words the number is always shown under.
        sentence: Why the answer is zero, or why it is absent. Nothing at all where
            a fraction came out above nothing and needs no explaining.
    """

    fraction: float | None
    taken_by: TakenBy | None
    at: float | None
    warning: str
    sentence: str | None


def ceiling_of(priced: Edge | NotComparable) -> Ceiling:
    """Work out the greyed ceiling from an edge, or say why there is none.

    The Kelly fraction for a contract that pays one when it comes good:

    > **buying** at cost `c` — the offer plus the fee — with likelihood `p`:
    > `(p - c) / (1 - c)`
    >
    > **selling** at proceeds `r` — the bid less the fee — with likelihood `p`:
    > `(r - p) / r`

    Both are worked out at the **unfavourable** end of the model's range for that
    side: the bottom of the range when buying, because a lower likelihood makes
    buying worth less, and the top when selling. Whichever of the two comes out
    higher is the one shown, and it is quartered.

    Args:
        priced: The edge, or the refusal that stands where one could not be built.

    Returns:
        A ceiling: a quartered fraction, or zero with its reason, or nothing at all
        with the refusal's own sentence.
    """
    raise NotImplementedError
