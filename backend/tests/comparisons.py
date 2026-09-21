"""Comparing two worlds claim by claim, for the two locality tests.

One idea lives here because two property tests need it, and one rule written twice
eventually becomes two rules.

**Locality is the product's central correctness claim** — an edit changes only what
is still connected to its subject — and these two tests check it over whole
*worlds* rather than over maps: a claim outside the reach must be answered the same
in both. The sharp way to write that is "identical to the last bit", and that is
now exactly what it is.

It was not always. Two things had to be put right first, and both are worth
knowing, because both were found by a test failing on a rare seed and being
believed rather than re-run.

**The day grid used to depend on the length of the window.** Past 180 days the
engine drew a series at evenly spaced points and worked the whole map out on that
same thinned grid, while a one-off push fires on the day its cause is *settled* —
read off those points, rounded up to the next one along. So the window's length
decided the timing of every push, and the window is a property of the whole map: an
inserted claim judged a year out, stretching a window from 31 days to 365, moved a
claim in a wholly separate piece by `.096`. The rule that fixed it is in
`spec/multiverse/propagation.md` B5 — *the day cap decides where a series is
drawn, never when a push fires; every day the arithmetic reads by name is on the
grid exactly* — and `test_a_longer_window_moves_nothing_it_cannot_reach` pins it.

**And the worlds an observation threw away used to be pooled across every
observation on the branch**, so a claim that *some* observation was evidence about
was read through *all* of them. On a map in two pieces, observing a claim in one
moved a claim in the other by `.083`. Each observation now keeps its own worlds;
`propagation.md` B6 states it, and the test that pins it is
`test_an_observation_in_one_piece_moves_nothing_in_another`.

With both put right, two worlds of one map agree **bit for bit** about a claim
neither of them touched — every version's answer, the spread inside each version,
how much each version counts, and the single number they average to. That is what
this helper asks for, and there is no case left in which it asks for less.
"""

from collections.abc import Iterable

import numpy

from katalyst.domain import World, versions_of


def every_version_answered_the_same(first: World, second: World, claims: Iterable[str]) -> None:
    """Check two worlds worked out the same answer for each claim, version by version.

    Compares every number the band arithmetic reads — each version's answer for the
    claim, how much the worlds inside each version disagreed, and how much each
    version counts — and asks for all three bit for bit. That is a stronger thing to
    ask than whether the one reported likelihood matches, because it compares every
    version rather than their average; the callers ask for the reported number too.

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
    behind_first, behind_second = versions_of(first), versions_of(second)
    where = {day: index for index, day in enumerate(behind_first.days)}
    shared = [(index, where[day]) for index, day in enumerate(behind_second.days) if day in where]
    assert shared, "the two worlds drew no day in common"

    for claim_id in claims:
        assert numpy.array_equal(
            behind_second.counting_for(claim_id), behind_first.counting_for(claim_id)
        ), f"{claim_id}: the two worlds count the versions differently"
        for here, there in shared:
            day = behind_second.days[here]
            assert numpy.array_equal(
                behind_second.likelihood[claim_id][:, here],
                behind_first.likelihood[claim_id][:, there],
            ), f"{claim_id}: the versions answer differently on day {day}"
            assert numpy.array_equal(
                behind_second.inner_spread[claim_id][:, here],
                behind_first.inner_spread[claim_id][:, there],
            ), f"{claim_id}: the worlds inside a version disagree differently on day {day}"
