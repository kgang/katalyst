"""Comparing two worlds claim by claim, for the two locality tests.

One idea lives here because two property tests need it, and one rule written twice
eventually becomes two rules.

**Locality is the product's central correctness claim** — an edit changes only what
is still connected to its subject — and these two tests check it over whole
*worlds* rather than over maps: a claim outside the reach must be answered the same
in both. The sharp way to write that is "identical to the last bit", and that is
exactly what it is.

It was not always, and what put it right is worth knowing.

**The day grid used to depend on the length of the window.** Past 180 days the
engine drew a series at evenly spaced points and worked the whole map out on that
same thinned grid, while a one-off push fired on the day its cause was *settled* —
read off those points, rounded up to the next one along. So the window's length
decided the timing of every push, and the window is a property of the whole map: an
inserted claim judged a year out, stretching a window from 31 days to 365, moved a
claim in a wholly separate piece by `.096`. There is no such grid now. Every claim
is worked out on **its own** window, cut into slices from its own resolve-by day,
and the days a reader is sent decide only where the finished line is read.

**And the worlds an observation threw away used to be pooled across every
observation on the branch**, so a claim that *some* observation was evidence about
was read through *all* of them. On a map in two pieces, observing a claim in one
moved a claim in the other by `.083`. There are no worlds to pool now either:
*This happened* is answered by conditioning an exact solve, and a claim the
evidence cannot reach has a factor that sums to one, so it comes out unchanged
because of what the arithmetic **is** rather than because a sample was large
enough.

So two worlds of one map agree about a claim neither of them touched, **to the
last bit** — the number on its tile and every point of the line drawn beneath it.

**To the last bit and not to the byte, and the difference is named rather than
waved at.** An edit changes the *shape* of the map — a supposition cuts the arrows
into its target, an insert adds a claim — and the exact solve eliminates a map's
claims in an order read off that shape. A different order multiplies the same
factors in a different sequence, and floating-point multiplication is not
associative, so the last bit of a claim outside the reach can move without
anything about it having changed. Measured on the sequence these tests shrank to:
`8.311121790768778e-10` against `8.311121790768779e-10`, one bit of a double, and
`5.2e-26` on a number of `2.4e-10` in the state machine next door.

**The byte-identical promise is about evidence, and it is kept where it is made.**
A claim the evidence cannot reach has a factor that sums to one and is never
touched at all, so it comes back byte for byte;
`test_a_claim_cut_off_from_the_evidence_is_bit_for_bit` is where that is asserted,
and it asks for the byte.
"""

import math
from collections.abc import Iterable

from katalyst.domain import World

TO_THE_LAST_BIT = 1e-12
"""How far two readings of one untouched claim may differ and still be the same reading.

Far below anything a reader could see — the screen shows two significant figures
and the rules layer will not call a claim *shifted* until it has moved by `0.005`
— and far **above** the couple of last bits a change of multiplication order can
move a number by. A tolerance this wide cannot hide a real move and cannot fail on
a rounding one.
"""


def every_version_answered_the_same(first: World, second: World, claims: Iterable[str]) -> None:
    """Check two worlds worked out the same answer for each claim, to the last bit.

    Compares the number on the claim's tile and every point of its series, and asks
    for both to agree to `TO_THE_LAST_BIT`. That is a far stronger thing to ask
    than whether the two tiles round to the same two figures: a claim an edit
    cannot reach must come back untouched, not merely close enough to print the
    same way.

    Only the days both worlds drew are compared, which is every day either of them
    would be shown on: a series is drawn at up to 180 points and a claim an edit
    added brings a resolve-by day of its own, so the two worlds can be *drawn* at
    different days — sometimes at very few of the same ones — even where their
    arithmetic agrees.

    Args:
        first: One world.
        second: The other, built from the same map and the same seed.
        claims: The claims to check — the ones the edit cannot reach.

    Raises:
        AssertionError: Naming the claim and the day, if anything differs.
    """
    where = {day: index for index, day in enumerate(first.series_days)}
    shared = [(index, where[day]) for index, day in enumerate(second.series_days) if day in where]
    assert shared, "the two worlds drew no day in common"

    for claim_id in claims:
        here_is, there_is = second.beliefs[claim_id].p, first.beliefs[claim_id].p
        assert math.isclose(here_is, there_is, rel_tol=TO_THE_LAST_BIT, abs_tol=1e-15), (
            f"{claim_id}: the two worlds read the tile differently — "
            f"{there_is!r} against {here_is!r}"
        )
        for here, there in shared:
            day = second.series_days[here]
            drawn, was = second.series[claim_id][here], first.series[claim_id][there]
            assert math.isclose(drawn, was, rel_tol=TO_THE_LAST_BIT, abs_tol=1e-15), (
                f"{claim_id}: the two worlds' lines differ on day {day} — {was!r} against {drawn!r}"
            )
