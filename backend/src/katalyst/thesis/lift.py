"""What takes you out: the claims over-represented in the worlds where the stop went first.

The brief's most distinctive question is *what events could lead to a stop-loss?*
This file answers it by arithmetic rather than by prose.

**Lift is one division.** Among the worlds where the reader's stop was touched
before their target, how often had this claim **already come on before the stop
was touched**? Divide by how often it came on across all the drawn worlds. Three
means three times as often; one means it tells you nothing; below one means the
claim kept company with the trade working.

**"Before the stop" is load-bearing.** A claim that came on afterwards cannot have
contributed, counting it inflates every row in the direction that makes the rail
look useful, and it is what keeps a row's *days before the stop* from coming out
negative.

**Both shares are weighted**, because the worlds are drawn with weights, so a
weighted sampler changes nothing here.

**The interval is on the numerator only.** A Wilson interval — the standard
interval for a share, which stays sensible when counts are small — on how often the
claim came on first among the stop-first worlds. The denominator is taken from all
the draws. **No coverage is claimed for the ratio**, because a ratio of two shares
over overlapping sets is not a share. A row's interval says how firmly the
numerator is pinned down and nothing more.

**Three rules keep the rail honest.** No row rests on fewer than two hundred
**effective** drawn worlds — effective meaning how many equally-weighted worlds
the weighted sample is worth, which for the engine's sampler is most of them but
by no means all. The floor is **chosen, not measured**, carried over from the
finance analysis because some floor is needed; what would replace it is the draw
count at which the top rows stop changing order between seeds. A claim an edit
holds true in every drawn world has lift one by construction, so it is dropped
rather than printed. And a claim whose numerator interval covers its own base
share is indistinguishable from telling you nothing, so it is dropped too, with
its reason.

**Lift is company, not cause.** A claim can be over-represented in the worlds that
stopped you out because it shares a cause with whatever did. The word is
*over-represented*, and the map beside it is where the mechanism lives.

What this file must never do
----------------------------
- Never count a claim that came on after the stop was touched.
- Never claim coverage for the ratio, and never print a lift without its interval
  and the count it rests on.
- Never return a row below the floor, and never report one without naming the
  sample its days came from.
- Never read lift as a cause, or name it anything that suggests one.
"""

from dataclasses import dataclass
from typing import Final, Literal

from katalyst.domain import PropositionId
from katalyst.thesis.draws import Draws, SampleFrom
from katalyst.thesis.position import FirstTouch

THE_FLOOR: Final = 200
"""The fewest effective drawn worlds a row may rest on.

**Chosen, not measured.** Some floor is needed, because a lift of four over six
worlds and a lift of one over two thousand are different claims and only one of
them is a claim. What would replace this number with a measured one is the draw
count at which the top rows stop changing order between seeds, which nobody has
measured yet.

It counts **effective** worlds, not drawn ones: two hundred worlds of which one
carries nine tenths of the weight is not two hundred worlds.
"""

COVERAGE: Final = 0.95
"""How often the interval on a numerator is meant to cover the true share.

Ninety-five per cent, the ordinary choice. The number of standard deviations that
goes with it is worked out from it rather than typed, so the two can never drift
apart.
"""

TOO_FEW_DRAWS = (
    "Fewer than {floor} effective drawn worlds ended with the stop touched first, so nothing "
    "here would be worth reading. {effective} of the {drawn} drawn worlds count."
)
"""What the rail prints instead of rows, when the draws behind it are too few.

An empty rail with a reason is a fact about the sample. An empty rail without one
reads as *nothing takes you out*, which is a different and much more flattering
sentence.
"""

DroppedBecause = Literal["held_true_everywhere", "never_came_on", "tells_you_nothing"]
"""Every reason a claim is left off the rail, as a closed list.

`held_true_everywhere` — an edit holds it true in every drawn world, so its lift is
one by construction and the rail is about what varies. `never_came_on` — it came on
in no drawn world, so there is nothing to divide by. `tells_you_nothing` — its
numerator interval covers its own base share, so the rail cannot tell it apart from
a claim that keeps no company with losing at all.
"""

DROPPED: Final[dict[str, str]] = {
    "held_true_everywhere": (
        "You are holding this true, so it happened in every drawn world and tells you "
        "nothing about which of them stopped you out."
    ),
    "never_came_on": "This never came on in any drawn world, so there is nothing to compare.",
    "tells_you_nothing": (
        "This came on about as often where the stop went first as it did everywhere else."
    ),
}
"""What is said about each claim left off the rail, in plain words."""


@dataclass(frozen=True)
class LiftRow:
    """One claim on the rail: how much company it keeps with losing, and what that rests on.

    Attributes:
        claim: The claim this row is about.
        lift: The numerator share divided by the denominator share. Three means the
            claim had already happened three times as often in the worlds where the
            stop went first as it happened across all the drawn worlds.
        came_on_first: The numerator: the weighted share of the stop-first worlds
            in which this claim had already come on **before** the stop was
            touched.
        came_on_first_lo: The bottom of the interval on that share.
        came_on_first_hi: The top of it.
        came_on: The denominator: the weighted share of **all** drawn worlds in
            which this claim came on at all.
        effective_draws: How many equally-weighted worlds the numerator rests on.
        days_before_the_stop: The typical number of days between this claim coming
            on and the stop being touched, over the worlds the numerator counted.
            Never negative, because the numerator counts only claims that came on
            first.
        coverage: How often the interval above is meant to cover the numerator's
            true share. Carried so a screen can say which interval it is showing.
    """

    claim: PropositionId
    lift: float
    came_on_first: float
    came_on_first_lo: float
    came_on_first_hi: float
    came_on: float
    effective_draws: float
    days_before_the_stop: float
    coverage: float


@dataclass(frozen=True)
class Dropped:
    """One claim the rail leaves off, and why.

    A dropped claim is said out loud rather than quietly missing, because *this
    claim is not on the rail* and *this claim was never considered* are different
    facts and a reader can act on only one of them.

    Attributes:
        claim: The claim left off.
        because: Which of the three reasons it was.
        sentence: What a screen prints beside it.
    """

    claim: PropositionId
    because: DroppedBecause
    sentence: str


@dataclass(frozen=True)
class WhatTakesYouOut:
    """The whole rail: the rows, what was left off it, and what the numbers rest on.

    Attributes:
        rows: The claims over-represented in the worlds where the stop went first,
            ranked by lift, highest first. Empty where the draws are too few.
        dropped: Every claim left off, with its reason.
        effective_draws: How many equally-weighted worlds the stop-first set is
            worth. The same for every row, because every row's numerator is taken
            over the same set of worlds.
        stop_first_worlds: How many drawn worlds ended with the stop touched first,
            before weighting. Carried beside the effective count so the two can be
            compared.
        floor: The fewest effective worlds a row may rest on, carried so a screen
            can say what it was.
        sample: Which sampler the days came from.
        too_few_draws: The sentence the rail prints when it is empty because the
            draws behind it are too few. Nothing at all when it is not.
    """

    rows: tuple[LiftRow, ...]
    dropped: tuple[Dropped, ...]
    effective_draws: float
    stop_first_worlds: int
    floor: int
    sample: SampleFrom
    too_few_draws: str | None


def wilson(share: float, count: float, coverage: float) -> tuple[float, float]:
    """The Wilson interval around a share: the standard one, and sensible at small counts.

    The obvious interval — the share plus or minus so many standard errors — runs
    off the end of the scale at a share near nothing or near one, and at a share of
    exactly nothing it has no width at all, which says a thing nobody measured.
    Wilson's interval is the set of true shares that would not have been rejected
    by the observed one, and it stays inside nothing and one at every count.

    The number of standard deviations is worked out from the coverage asked for,
    rather than typed beside it, so the two cannot drift apart.

    Args:
        share: The observed share, between nothing and one.
        count: How many draws it rests on. May be fractional, because a weighted
            sample is worth a fractional number of equally-weighted draws.
        coverage: How often the interval is meant to cover the true share.

    Returns:
        The bottom and the top of the interval, both between nothing and one.

    Raises:
        ValueError: If the share is outside nothing to one, if the count is not
            above nothing, or if the coverage is not strictly between nothing and
            one.
    """
    raise NotImplementedError


def what_takes_you_out(draws: Draws, touch: FirstTouch) -> WhatTakesYouOut:
    """Rank the claims over-represented in the worlds where the stop was touched first.

    One division per claim, over two sets of worlds: the stop-first worlds, and all
    of them. A claim counts in the numerator only where it came on **strictly
    before** the day the stop was touched.

    Three claims never reach the rail, each with its reason: one an edit holds true
    in every drawn world, one that came on in no world at all, and one whose
    interval covers its own base share. Where fewer than the floor of effective
    worlds ended with the stop first, no rows come back at all and the reason does.

    Args:
        draws: The drawn worlds and the day each claim came on in each.
        touch: The first-touch answer over those same worlds, which carries the day
            the stop was touched in each world where it went first.

    Returns:
        The rail, ranked by lift, with everything it left off and what it rests on.

    Raises:
        ValueError: If the first-touch answer was not computed over these drawn
            worlds — a different number of worlds, or a different sampler. Dividing
            one sample's numerator by another's denominator is the kind of
            comparison this whole layer exists to refuse.
    """
    raise NotImplementedError
