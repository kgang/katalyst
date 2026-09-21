"""A belief: a likelihood with an honest range and a name on it.

A bare number on a box is a claim from nowhere. A belief is a likelihood that
says whose it is and how sure it is: a value between 0 and 1, a range around it,
and an owner — the model, the user, or a market. Every claim on the map carries
up to three of them side by side, and they are never combined into one.

That is the product in one design choice. The model's .61, the market's .48 and
your own .30 on the same claim are not three attempts at one true number to be
averaged away. They are the disagreement you are about to trade: model minus
market is the edge, user minus model is the argument you are having with the
tool.

Both classes here are frozen — once built, an instance cannot be changed. A
change is a new instance, recorded as an intervention on a branch.
"""

import math
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OUT_OF_RANGE = "outside 0 to 1"
"""What is written where a number that is not a likelihood at all would go.

A `Belief` cannot hold such a number — its fields refuse one — but the rule in
`domain/validity.py` that re-checks a map which arrived some other way can meet
one, and it reports the fault in words `Belief.as_written` writes.
"""


def two_figures(likelihood: float) -> str:
    """Write a likelihood the way this product writes every likelihood.

    **This is the one rule for writing a likelihood, and it lives here** — beside
    the class that holds one — so that every sentence in this program that puts a
    likelihood in front of a reader writes it the same way: a chip on the canvas,
    a violation that comes back in a refused request, the sentence beside a change
    list, the generated file of the worked example's numbers. One rule in one
    place is the whole point; a second copy is how the same number starts reading
    two ways on one screen.

    Two significant figures, with the nought before the point dropped, so `.50`
    and `.42` and `.060` — both figures always printed, because dropping a
    trailing nought would claim less precision than we have.

    **The whole rule, in one sentence: round to two significant figures, then use
    a guard word exactly when it is true of the rounded number.** `<.01` when the
    rounded number is less than a hundredth, `>.99` when it is more than
    ninety-nine hundredths, and the figures themselves otherwise. That is all of
    it, and it is stated this way because *the guard's words have to mean what
    they say*: a chip reading `<.01` beside a number that was `.0035` is telling
    the reader something true, and one reading `<.01` beside `.010` would not be
    (Kent, 2026-09-20).

    Two things fall out of that sentence rather than being decided beside it.
    `.010` and `.99` print, because neither is below or above its own guard.
    And the two figures always land in the first two places after the point —
    `.99` down to `.010` — because anything further down rounds to less than a
    hundredth and anything further up rounds to one.

    **Never a certainty, and never a nothing.** Rounding to two figures turns
    `.995` into `1.0` and `.0004` into `.0`, and both are claims nobody on this
    map is entitled to make: one says the thing cannot fail, the other that it
    cannot happen. The guards are what stand in their place.

    **A move is not a likelihood**, and must never come through here. `.36 · up
    by .0090` is the honest way to write a small move, because a move of `.0090`
    is a real quantity a reader acts on, while a likelihood of `.0090` is one the
    product declines to state that precisely. Nothing in the rules layer writes a
    move as text today; the day something does, it gets its own function, not a
    flag on this one. `domain/propagation.py`'s `_push_as_written` is the
    precedent: how hard an arrow pushes is not a likelihood either, and it has a
    rule of its own.

    **Never scientific notation.** A sentence that reads *"moves this claim from
    `>.99` to `1.0e-09`"* is not a sentence anybody can read aloud, and asking
    Python for two significant figures directly produces exactly that below a ten
    thousandth. So the rounding is done on the number's own decimal digits: the
    shortest decimal that reads back as this exact number, its point shifted by
    counting rather than by multiplying, and rounded half-up. That is also what
    stops `.995` printing `.99` — a computer stores it as `0.99499999999999999556`,
    so asking for two figures directly gives a number under the guard, and the
    sentence would print the one thing this rule forbids.

    **This rule is written twice and the two must move together.** The browser
    writes it as `toTwoFigures` in `frontend/src/components/BeliefChip.tsx`, and
    this function says the same thing for every input it can be given, carry cases
    included. Change one and change the other in the same pull request, or the
    same number reads two ways on one screen, and cross-check the two against each
    other wherever the two stacks meet.

    **A number that is not a number is refused, not written.** "Not a number" and
    the infinities cannot be rounded to two figures, and printing a modest `<.01`
    for one would put a likelihood on screen that nothing computed — the one state
    this product refuses to show. They cannot arrive from a world, because a
    likelihood that is not a real number between 0 and 1 cannot be built into a
    `Belief` at all; so one reaching here is a broken promise between two pieces of
    our own code, and it is said out loud rather than quietly made to look
    reasonable. Reject, never repair.

    Args:
        likelihood: The number, between 0 and 1.

    Returns:
        The number as it is written on screen: `.35`, or `<.01`, or `>.99`.

    Raises:
        ValueError: If the number is not a real number — "not a number" itself, or
            either infinity.
    """
    if not math.isfinite(likelihood):
        raise ValueError(
            "a likelihood to be written on screen must be a real number between 0 and 1; "
            f"got {likelihood!r}, which cannot be rounded to two significant figures"
        )
    if likelihood <= 0.0:
        return "<.01"
    if likelihood >= 1.0:
        return ">.99"
    # The shortest decimal that reads back as this exact number, and where its
    # point sits: `.995` becomes the digits 995 with its leading digit at the
    # first place after the point.
    shortest = Decimal(repr(likelihood))
    place = shortest.adjusted()
    # The two figures, as a whole number from 10 to 99. Shifting the point by
    # counting places rather than by multiplying is what keeps `.995` at exactly
    # 99.5 rather than a hair under it, so it rounds up the way a reader would.
    figures = int(shortest.scaleb(1 - place).to_integral_value(rounding=ROUND_HALF_UP))
    if figures >= 100:
        # Rounding up carried into the next place: `.0999` is `.10`, not `.100`.
        figures, place = 10, place + 1
    # Where the rounded number's first figure landed is the whole guard. The
    # first place after the point holds `.10` to `.99`, and the second holds
    # `.010` to `.099`; one place further up is a rounded number of 1 or more,
    # which is past `>.99`, and one further down is `.0099` or less, which is
    # under `<.01`.
    if place >= 0:
        return ">.99"
    if place <= -3:
        return "<.01"
    return f".{'0' * (-place - 1)}{figures}"


class Belief(BaseModel):
    """A likelihood with an honest range and a name on it.

    `p` is the likelihood, `lo` and `hi` are the range around it, and `owner`
    says whose number this is. There are exactly three owners and no code path
    ever combines two of them into one number.

    A belief is a number, never text. This layer does not round it and does not
    store it as a string; rounding happens once, at the moment of display.
    """

    model_config = ConfigDict(frozen=True)

    # Open question 1 in spec/graph/belief.md: a belief records no provenance,
    # so a model number anchored on a documented count and one asserted from
    # nothing look alike. Owner is not yet the whole answer.
    p: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How likely the claim is to come out true, from 0 (certainly not) to 1 (certainly yes)."
        ),
    )
    lo: float = Field(
        ge=0.0,
        le=1.0,
        description="The bottom of the honest range around `p`. Never above `p`.",
    )
    hi: float = Field(
        ge=0.0,
        le=1.0,
        description="The top of the honest range around `p`. Never below `p`.",
    )
    owner: Literal["model", "user", "market"] = Field(
        description=(
            "Whose number this is: the model's estimate, the user's own, or a live "
            "price at a venue."
        ),
    )

    def as_written(self) -> tuple[str, str, str]:
        """Give this belief's three numbers the way the product writes a likelihood.

        Two significant figures through `two_figures` above, in the order low,
        likelihood, high. Nothing that reaches a reader — a chip on the canvas, a
        sentence in a refusal, the body of a rejected request — quotes a likelihood
        at the precision a computer happens to hold it at, because
        `0.30000000000000004` is not a number anybody wrote or could act on.

        **A number outside 0 to 1 is said to be outside 0 to 1**, and is not put
        through the likelihood rule. The fields on this class cannot hold such a
        number, but the rule in `domain/validity.py` that re-checks a map which
        arrived some other way can meet one, and it reports the fault in words
        this method writes. The likelihood rule answers `>.99` for 1.4 and `<.01`
        for -0.3, and either word inside a sentence saying the number is out of
        range would tell the reader the opposite of the truth.

        Returns:
            The low, the likelihood and the high, each as text.
        """

        def written(number: float) -> str:
            return two_figures(number) if 0.0 <= number <= 1.0 else OUT_OF_RANGE

        return written(self.lo), written(self.p), written(self.hi)

    @model_validator(mode="after")
    def _range_is_ordered(self) -> "Belief":
        """Check that low is at most the likelihood, which is at most high.

        The field bounds above already cover 0 and 1; this covers the order. So by
        the time this runs all three numbers are real likelihoods, and the sentence
        it raises can write them the way the product writes every likelihood.

        Returns:
            This same belief, once the order has been checked.

        Raises:
            ValueError: If the three numbers are not in order.
        """
        if not (self.lo <= self.p <= self.hi):
            low, likelihood, high = self.as_written()
            raise ValueError(
                "a belief must satisfy low <= likelihood <= high; got "
                f"low={low}, likelihood={likelihood}, high={high}"
            )
        return self


class Beliefs(BaseModel):
    """The three voices on one claim: the model's, the user's, and a market's.

    Three named slots, deliberately not a dictionary, so that nothing can loop
    over them and average them by accident. `model` is always present. `user` is
    absent until the user says what they think. `market` is absent when no venue
    quotes this claim — and absent means the words "no market", never a blank and
    never a stand-in number.

    The field named `model` is legal. Pydantic protects names beginning with
    `model_`, so `model_config` and `model_dump` are reserved; plain `model` is
    not one of them. It stays `model` because that is the word the shared
    vocabulary uses, on the canvas and in the code alike.
    """

    model_config = ConfigDict(frozen=True)

    model: Belief = Field(
        description=(
            "What the model thinks, with this claim's causes taken into account. Always present."
        ),
    )
    user: Belief | None = Field(
        default=None,
        description=(
            "What the user thinks. Written only by the `believe` intervention. None means "
            "the user has not said."
        ),
    )
    market: Belief | None = Field(
        default=None,
        description=(
            "What a venue is currently pricing, read live and read-only. None means no "
            "venue quotes this claim."
        ),
    )

    @model_validator(mode="after")
    def _owners_match_slots(self) -> "Beliefs":
        """Check that each slot holds a belief owned by the voice the slot is named for.

        A belief sitting in the wrong slot would make the never-merge rule
        unenforceable: a user's number could sit in the model's chip and nothing
        would notice.

        Returns:
            This same set of beliefs, once every slot has been checked.

        Raises:
            ValueError: If any slot holds a belief owned by someone else.
        """
        for slot, belief in (("model", self.model), ("user", self.user), ("market", self.market)):
            if belief is not None and belief.owner != slot:
                raise ValueError(f"the '{slot}' slot holds a belief owned by '{belief.owner}'")
        return self
