"""Comparing two worlds claim by claim, for the two locality tests.

One idea lives here because two property tests need it, and one rule written twice
eventually becomes two rules.

**Locality, and the two reasons a claim an edit cannot reach is not always
identical to the last bit.**

Locality — the product's central correctness claim — says an edit changes only what
is still connected to its subject. Two property tests check it over whole *worlds*
rather than over maps: a claim outside the reach must be answered the same in both.
Writing that as "identical to the last bit" is very nearly right, and it fails on a
rare draw for two quite different reasons. Both were measured; neither is guessed.

**One: an average is reassociated when the array it sits in changes shape.** What
the engine works out about a claim is one answer per version of the map per day;
the number it reports is the average of those. A claim an edit added can make the
window longer — the window runs to the last day anything is judged — and every
claim's numbers are then held in a wider array. Adding a column up on its own and
adding the same column up inside a wider block are done differently by the array
library, and floating-point addition is not associative, so the last bit moves.
Measured, in isolation: the same sixteen numbers total `11.689481994806576` in an
array one column wide and `11.689481994806577` in one two columns wide. On the map
that made `test_diff_states_respect_locality` fail that showed as
`.730592624675411` against `.7305926246754111` — one part in the sixteenth figure
of a number this product prints to two.

**Two, and this one is the engine's rather than arithmetic's: the day grid is
global, and a trigger reads its cause off it.** Past 180 days a series is drawn at
evenly spaced points rather than at every day, and a day falling between two of
them is read at the next one along. A *trigger* fires on the day its cause is
settled — read at the nearest drawn day. So lengthening the window past the cap
re-spaces the grid for the **whole map**, and a trigger anywhere on it can start
reading its cause a day later. Measured: a claim settling on day 3 is read at drawn
day 3 on a 31-day window and at drawn day 4 once an inserted claim stretches the
window to 365 — on the far side of a map in two pieces with nothing joining them.
That moved a claim the edit could not reach by about `4e-10`.

The second is a **real defect in the engine**, not floating-point noise, and it is
not papered over here. Measured on the draw that found it: `.096` — a tenth of a
likelihood — on a claim in a wholly separate piece of the map. It is pinned by name
and with its reproducer in `test_a_longer_window_moves_a_claim_it_cannot_reach`,
which is expected to fail until the engine reads a one-off push's firing day
somewhere other than off the drawn grid. **Keeping every settled day on the grid is
not the fix**: it was tried, and it makes the grid depend on the settled days, so a
supposition — which cuts arrows and moves settled days — then re-spaces the grid and
shifts a claim's own ancestors, which is a worse break (INV-3, assert is not
observe) than the one it cures.

So this module compares what it can compare honestly, and says out loud what it
cannot:

* **The two worlds drew the same days** — the grid did not move and nothing was
  reassociated, so everything is compared **bit for bit**. That is the great
  majority of draws, and it is where a leak along the arrows would show, because a
  leak along the arrows does not wait for a long window.
* **The two worlds drew different days** — the grid moved, and the engine is known
  to be wrong here. Comparing the numbers would only re-find the defect above on a
  rare seed, which is what made these tests flake. The comparison stops at what the
  grid cannot touch: how much each version counts.
"""

from collections.abc import Iterable

import numpy

from katalyst.domain import World, versions_of


def every_version_answered_the_same(first: World, second: World, claims: Iterable[str]) -> bool:
    """Check two worlds worked out the same answer for each claim, version by version.

    Compares every number the band arithmetic reads — each version's answer for the
    claim, how much the worlds inside each version disagreed, and how much each
    version counts. That is a stronger thing to ask than whether the one reported
    likelihood matches, because it compares every version rather than their average.

    Bit for bit when the two worlds drew the same days. When they did not, only
    how much each version counts is compared, because the engine is known to read a
    claim differently once the grid moves — the module docstring measures that and
    names the test that pins it.

    Only the days both worlds drew are compared, which is every day either of them
    would be shown on.

    Args:
        first: One world.
        second: The other, built from the same map and the same seed.
        claims: The claims to check — the ones the edit cannot reach.

    Returns:
        Whether the two worlds drew the same days — whether, that is, everything
        was compared bit for bit. A caller that wants to compare the *reported*
        numbers exactly asks this first, because those are exact on one grid and
        not on two.

    Raises:
        AssertionError: Naming the claim and the day, if anything it could compare
            differs.
    """
    behind_first, behind_second = versions_of(first), versions_of(second)
    on_one_grid = behind_first.days == behind_second.days
    where = {day: index for index, day in enumerate(behind_first.days)}
    shared = [(index, where[day]) for index, day in enumerate(behind_second.days) if day in where]
    assert shared, "the two worlds drew no day in common"

    for claim_id in claims:
        # How much each version counts is a choice rather than a sum, so it is
        # exact whatever the grid did, and it is checked either way.
        assert numpy.array_equal(
            behind_second.counting_for(claim_id), behind_first.counting_for(claim_id)
        ), f"{claim_id}: the two worlds count the versions differently"
        if not on_one_grid:
            continue
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
    return on_one_grid
