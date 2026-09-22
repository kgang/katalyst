"""The exact solve — whether each claim is true, over the map's own yes/no tables.

Every map here is built in this file out of seeded random tables, so nothing below
depends on the rest of the new engine: a table is any array whose last axis adds up
to one, and the solve neither knows nor cares where it came from. **Not one number
the engine computes is typed here.** Every assertion is an identity against the
oracle, an equality between two runs, or arithmetic this file does itself out of
the tables it built.

The oracle is `tests/oracles/by_summing.py`, which multiplies every table into one
array over every claim at once and adds it up — two to the power of the number of
claims, no elimination, no ordering. It is the definition of the thing the solve
computes cleverly, and it is blind to a wrong table, which is exactly why a second
oracle judges the tables themselves elsewhere.

The map shapes below are the ones that break a careless elimination: a chain, a
diamond (two routes from one claim to another), a collider (two causes meeting at
one claim, which are **not** independent once you learn what they caused), a claim
with three causes, and two pieces of map that share nothing at all.
"""

import itertools
from collections.abc import Mapping, Sequence
from typing import Literal

import numpy
import pytest
from numpy.typing import NDArray

from katalyst.domain.forward import Forward
from katalyst.domain.rates import Pin
from katalyst.domain.solving import (
    ImpossibleObservation,
    _eliminate,
    _factors,
    all_marginals,
    all_true,
    elimination_order,
    solve,
)
from tests.oracles.by_summing import Pin as OraclePin
from tests.oracles.by_summing import Tables, by_summing

EXACT = 1e-9
"""How far the solve may sit from adding the whole joint up by brute force.

Record 0016's *Confirmation* names this one: the two programs do the same
double-precision arithmetic in a different order, so they agree to round-off, and
anything wider than round-off is a wrong answer rather than a tolerance.
"""

ROUND_OFF = 1e-12
"""How far two orderings of the same arithmetic in this file may sit apart."""

SEED = 20260922
"""Every table below is drawn from this one seed, so a failure repeats exactly."""

SHAPES: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "a chain of four": {"c0": (), "c1": ("c0",), "c2": ("c1",), "c3": ("c2",)},
    "a diamond": {"c0": (), "c1": ("c0",), "c2": ("c0",), "c3": ("c1", "c2")},
    "a collider": {"c0": (), "c1": (), "c2": ("c0", "c1")},
    "a claim with three causes": {
        "c0": (),
        "c1": (),
        "c2": (),
        "c3": ("c0", "c1", "c2"),
    },
    "two pieces that share nothing": {"c0": (), "c1": ("c0",), "c2": (), "c3": ("c2",)},
    "one claim on its own": {"c0": ()},
}
"""Claim -> its causes, for every shape the tests below run over."""


def a_table(draw: numpy.random.Generator, causes: int, versions: int) -> NDArray[numpy.float64]:
    """One claim's yes/no table: a chance per combination of its causes, per version.

    The last axis is the claim's own and runs `[it did not, it did]`, so it adds up
    to one — which is the only thing the solve asks of a table.
    """
    chance = draw.uniform(0.05, 0.95, size=(versions,) + (2,) * causes)
    return numpy.stack([1.0 - chance, chance], axis=-1)


def a_map(causes: Mapping[str, tuple[str, ...]], *, versions: int = 3, seed: int = SEED) -> Forward:
    """A finished forward pass over one shape, with every table drawn from the seed.

    Only the three fields the solve reads carry anything: the order, each claim's
    causes and each claim's table. The rest of the pass — the times, the shapes, the
    rates and their sums — belongs to the other writers and the solve never looks at
    it.
    """
    draw = numpy.random.default_rng(seed)
    order = tuple(causes)
    return Forward(
        order=order,
        causes=dict(causes),
        times={},
        table={claim: a_table(draw, len(causes[claim]), versions) for claim in order},
        shapes={},
        rates={},
        added={},
    )


def by_brute_force(
    forward: Forward, pinned: Mapping[str, Pin], version: int
) -> Mapping[str, NDArray[numpy.float64]]:
    """The same question put to the oracle, one version at a time.

    The oracle takes a leading version axis of its own, and this hands it one
    version's tables instead: it cannot lay a fixed value out over a version axis
    it did not build, so a map with both a pin and a range of versions is the one
    question it cannot be asked today. Reported to the oracle's author; asking it
    per version costs nothing here and judges exactly the same arithmetic.
    """
    return by_summing(
        Tables(
            order=forward.order,
            causes=forward.causes,
            table={claim: forward.table[claim][version] for claim in forward.order},
        ),
        {claim: OraclePin(value=pin.value, kind=pin.kind) for claim, pin in pinned.items()},
    )


BOTH_VERBS: tuple[Literal["do", "observe"], ...] = ("do", "observe")
"""*Suppose this is true* and *This happened*, by the names the code calls them."""


def every_edit(order: Sequence[str]) -> list[tuple[str, dict[str, Pin]]]:
    """No edit, each verb on each claim at each value, then both verbs at once.

    Both at once is the case a branch really builds — the reader supposes one thing
    and reports another — and it is the one where a solve that applies the two verbs
    in the wrong order, or applies the mask before cutting the supposed claim's
    arrows, comes apart. Each case is named, so a failure says which one.
    """
    out: list[tuple[str, dict[str, Pin]]] = [("no edit", {})]
    for claim, kind, value in itertools.product(order, BOTH_VERBS, (True, False)):
        out.append((f"{kind} {claim}={value}", {claim: Pin(value=value, kind=kind)}))
    for supposed, reported in itertools.permutations(order, 2):
        for one, other in itertools.product((True, False), repeat=2):
            out.append(
                (
                    f"do {supposed}={one} with observe {reported}={other}",
                    {
                        supposed: Pin(value=one, kind="do"),
                        reported: Pin(value=other, kind="observe"),
                    },
                )
            )
    return out


def read_off(values: NDArray[numpy.float64]) -> NDArray[numpy.float64]:
    """Turn a two-wide factor over one claim into that claim's chance of being true."""
    return values[..., 1] / values.sum(axis=-1)


def test_the_elimination_is_exact() -> None:
    """Every shape, every verb, every claim: the same numbers as adding the joint up.

    Run at one version and at several, because the version axis is carried through
    the arithmetic rather than looped over, and an axis carried wrongly shows up as
    a shape error or as the same version's answer in every column.
    """
    for shape, causes in SHAPES.items():
        for versions in (1, 4):
            forward = a_map(causes, versions=versions)
            for name, pinned in every_edit(forward.order):
                mine = solve(forward, pinned)
                for version in range(versions):
                    theirs = by_brute_force(forward, pinned, version)
                    for claim in forward.order:
                        assert mine[claim].shape == (versions,), f"{shape}, {name}, {claim}"
                        numpy.testing.assert_allclose(
                            mine[claim][version],
                            theirs[claim],
                            rtol=0.0,
                            atol=EXACT,
                            err_msg=f"{shape}, {name}, {claim}, version {version}",
                        )


def test_every_claims_number_is_the_one_call_the_assembly_makes() -> None:
    """`all_marginals` is the seam, and today it is exactly the solve behind it."""
    forward = a_map(SHAPES["a diamond"])
    pinned = {"c1": Pin(value=True, kind="observe")}
    seam = all_marginals(forward, pinned)
    straight = solve(forward, pinned)
    for claim in forward.order:
        assert numpy.array_equal(seam[claim], straight[claim])


def test_supposing_redoes_the_forward_pass_rather_than_patching_a_factor() -> None:
    """A supposed claim's own table is never read, and nothing upstream of it moves.

    Two maps identical but for the supposed claim's table, which is redrawn from a
    different seed in the second. If the solve patched the finished table — scaled
    it, or set one row of it — the two would disagree. It replaces it with a
    certainty instead, which is what cuts the arrows into the claim, so the two
    agree to the last bit and the claim's causes sit exactly where no edit left
    them.
    """
    causes = SHAPES["a chain of four"]
    forward = a_map(causes)
    garbled = Forward(
        order=forward.order,
        causes=forward.causes,
        times={},
        table={
            **forward.table,
            "c2": a_table(numpy.random.default_rng(SEED + 1), len(causes["c2"]), 3),
        },
        shapes={},
        rates={},
        added={},
    )
    assert not numpy.array_equal(forward.table["c2"], garbled.table["c2"])

    supposed = {"c2": Pin(value=True, kind="do")}
    mine = solve(forward, supposed)
    ignoring_the_table = solve(garbled, supposed)
    untouched = solve(forward, {})
    for claim in forward.order:
        assert numpy.array_equal(mine[claim], ignoring_the_table[claim]), claim
    assert numpy.array_equal(mine["c2"], numpy.ones(3))
    for cause in ("c0", "c1"):
        assert numpy.array_equal(mine[cause], untouched[cause]), cause
    assert not numpy.allclose(mine["c3"], untouched["c3"])


def test_this_happened_masks_and_renormalises() -> None:
    """On a two-claim map the answer is Bayes' rule, worked out here from the tables.

    The cause's table gives the chance it is true; the effect's table gives the
    chance the effect follows in each case. Keeping only the worlds where the effect
    is true and scaling what is left back up to one is what the solve does, and this
    test does the same arithmetic in two lines of its own.
    """
    forward = a_map({"c0": (), "c1": ("c0",)})
    cause = forward.table["c0"][:, 1]
    follows = forward.table["c1"][:, :, 1]

    happened = solve(forward, {"c1": Pin(value=True, kind="observe")})
    both = cause * follows[:, 1]
    numpy.testing.assert_allclose(
        happened["c0"],
        both / (both + (1.0 - cause) * follows[:, 0]),
        rtol=0.0,
        atol=ROUND_OFF,
    )
    assert numpy.array_equal(happened["c1"], numpy.ones(3))

    did_not = solve(forward, {"c1": Pin(value=False, kind="observe")})
    missed = cause * (1.0 - follows[:, 1])
    numpy.testing.assert_allclose(
        did_not["c0"],
        missed / (missed + (1.0 - cause) * (1.0 - follows[:, 0])),
        rtol=0.0,
        atol=ROUND_OFF,
    )
    assert numpy.array_equal(did_not["c1"], numpy.zeros(3))


def test_a_claim_cut_off_from_the_evidence_is_bit_for_bit() -> None:
    """Learning something moves what it can reach, and leaves the rest untouched exactly.

    Two promises in one test, because either alone is worthless. On a map of two
    pieces that share nothing, reporting news in one piece leaves every claim in the
    other **identical to the last bit** — not close, identical — while the claims in
    its own piece do move. Bit for bit is only possible because the untouched piece
    is never multiplied in and divided back out: a factor that ought to be one is
    not one in floating point.
    """
    forward = a_map(SHAPES["two pieces that share nothing"])
    quiet = solve(forward, {})
    news = solve(forward, {"c3": Pin(value=True, kind="observe")})
    for far in ("c0", "c1"):
        assert numpy.array_equal(quiet[far], news[far]), far
    assert not numpy.allclose(quiet["c2"], news["c2"])


def test_two_causes_meeting_at_one_claim_only_speak_once_it_is_reported() -> None:
    """The collider, which is where a careless pruning goes wrong in the safe direction.

    Two causes of one claim tell you nothing about each other until you learn what
    they caused. So reporting one cause leaves the other bit for bit where it was —
    and reporting the claim they meet at moves it.
    """
    forward = a_map(SHAPES["a collider"])
    quiet = solve(forward, {})
    one_cause = solve(forward, {"c1": Pin(value=True, kind="observe")})
    assert numpy.array_equal(quiet["c0"], one_cause["c0"])
    where_they_meet = solve(forward, {"c2": Pin(value=True, kind="observe")})
    assert not numpy.allclose(quiet["c0"], where_they_meet["c0"])


def test_an_impossible_observation_answers_rather_than_dividing_by_zero() -> None:
    """News no world on the map can produce is refused by name, never divided through.

    Three cases: the plain one; one where a single version of the map rules it out
    and the rest do not, because a range that is right in most of its versions is
    still wrong; and one where the claim being asked about cannot be reached from
    the news at all, which is the case a per-claim check would answer cheerfully
    while the map as a whole said something impossible had happened.
    """
    forward = a_map({"c0": (), "c1": ("c0",)})
    never = forward.table["c1"].copy()
    never[..., 1] = 0.0
    never[..., 0] = 1.0
    impossible = Forward(
        order=forward.order,
        causes=forward.causes,
        times={},
        table={**forward.table, "c1": never},
        shapes={},
        rates={},
        added={},
    )
    with pytest.raises(ImpossibleObservation) as refused:
        solve(impossible, {"c1": Pin(value=True, kind="observe")})
    assert refused.value.claims == ("c1",)
    assert "c1" in str(refused.value)

    one_version = forward.table["c1"].copy()
    one_version[0, :, 1] = 0.0
    one_version[0, :, 0] = 1.0
    with pytest.raises(ImpossibleObservation):
        solve(
            Forward(
                order=forward.order,
                causes=forward.causes,
                times={},
                table={**forward.table, "c1": one_version},
                shapes={},
                rates={},
                added={},
            ),
            {"c1": Pin(value=True, kind="observe")},
        )

    apart = a_map(SHAPES["two pieces that share nothing"])
    with pytest.raises(ImpossibleObservation):
        solve(
            Forward(
                order=apart.order,
                causes=apart.causes,
                times={},
                table={**apart.table, "c3": never},
                shapes={},
                rates={},
                added={},
            ),
            {"c3": Pin(value=True, kind="observe")},
        )


def test_the_elimination_order_does_not_change_the_answer() -> None:
    """Summing claims out in any order at all gives the same numbers.

    The order is what keeps the arrays small; it is not part of the answer. This
    runs the elimination over **every** order of a five-claim map — a diamond with
    a tail, so the orders really do differ in how much work they do — and checks
    each one against the brute-force sum. It also checks that the order the module
    chooses names every claim exactly once.
    """
    causes = {
        "c0": (),
        "c1": ("c0",),
        "c2": ("c0",),
        "c3": ("c1", "c2"),
        "c4": ("c3",),
    }
    forward = a_map(causes)
    chosen = elimination_order(forward)
    assert sorted(chosen) == sorted(forward.order)

    pinned: dict[str, Pin] = {"c4": Pin(value=True, kind="observe")}
    for claim in forward.order:
        others = [other for other in forward.order if other != claim]
        for order in itertools.permutations(others):
            mine = read_off(_eliminate(_factors(forward, pinned, set(forward.order)), order).values)
            for version in range(mine.shape[0]):
                numpy.testing.assert_allclose(
                    mine[version],
                    by_brute_force(forward, pinned, version)[claim],
                    rtol=0.0,
                    atol=ROUND_OFF,
                    err_msg=f"{claim}, {order}, version {version}",
                )


def test_the_versions_are_one_axis_and_each_one_stands_alone() -> None:
    """A range of versions in one pass is bit for bit the same as one version at a time.

    The version axis is carried as the leading axis of every array rather than
    looped over, which is the whole of why two thousand versions cost one pass. If
    anything in the arithmetic reached across versions — a sum over the wrong axis,
    a shared normalisation — this would catch it.
    """
    versions = 5
    causes = SHAPES["a diamond"]
    together = a_map(causes, versions=versions)
    pinned = {"c3": Pin(value=True, kind="observe")}
    many = solve(together, pinned)
    for version in range(versions):
        alone = Forward(
            order=together.order,
            causes=together.causes,
            times={},
            table={claim: together.table[claim][version : version + 1] for claim in together.order},
            shapes={},
            rates={},
            added={},
        )
        one = solve(alone, pinned)
        for claim in together.order:
            assert numpy.array_equal(one[claim], many[claim][version : version + 1]), (
                f"{claim}, version {version}"
            )


# --- The joint: are all of these true at once? ------------------------------


def by_the_chain_rule(
    forward: Forward, pinned: Mapping[str, Pin], claims: Sequence[str]
) -> NDArray[numpy.float64]:
    """The same joint by a different road: each claim's number, then the next given it.

    The chance all of them are true is the chance the first is, times the chance
    the second is once the first is known true, and so on. Every factor is one call
    to the solve, which is itself checked against adding the whole joint up — so
    this is an independent route to the answer rather than a second copy of it.

    A claim an edit already fixed keeps the pin it has: supposing it true and
    learning it happened are not the same thing, and this must not quietly turn one
    into the other.
    """
    so_far = dict(pinned)
    answer = numpy.ones(forward.table[forward.order[0]].shape[0])
    for claim in claims:
        answer = answer * solve(forward, so_far)[claim]
        so_far.setdefault(claim, Pin(value=True, kind="observe"))
    return answer


def test_the_joint_of_one_claim_is_that_claims_own_number() -> None:
    """One claim being true is one claim being true, whichever call asks the question."""
    for shape, causes in SHAPES.items():
        forward = a_map(causes)
        for name, pinned in every_edit(forward.order):
            each = solve(forward, pinned)
            for claim in forward.order:
                numpy.testing.assert_allclose(
                    all_true(forward, pinned, (claim,)),
                    each[claim],
                    rtol=0.0,
                    atol=ROUND_OFF,
                    err_msg=f"{shape}, {name}, {claim}",
                )


def test_the_joint_is_what_working_one_claim_at_a_time_says() -> None:
    """Every shape, every verb: the joint agrees with the chain rule over the same tables.

    The chain rule is the definition of a joint written out claim by claim, and the
    solve it leans on is the one checked against adding the whole thing up. Two
    roads to one number, and they must meet.
    """
    for shape, causes in SHAPES.items():
        forward = a_map(causes, versions=2)
        every = tuple(forward.order)
        asked = [
            every,
            every[::-1],
            *[(one, other) for one, other in itertools.combinations(every, 2)],
        ]
        for name, pinned in every_edit(forward.order):
            for claims in asked:
                numpy.testing.assert_allclose(
                    all_true(forward, pinned, claims),
                    by_the_chain_rule(forward, pinned, claims),
                    rtol=0.0,
                    atol=EXACT,
                    err_msg=f"{shape}, {name}, {claims}",
                )


def test_the_joint_is_never_more_than_any_one_of_its_claims() -> None:
    """Adding a claim to the list can only make everything harder, never easier."""
    for shape, causes in SHAPES.items():
        forward = a_map(causes)
        each = solve(forward, {})
        every = tuple(forward.order)
        together = all_true(forward, {}, every)
        for claim in every:
            assert bool(numpy.all(together <= each[claim] + ROUND_OFF)), f"{shape}, {claim}"


def test_claims_that_share_a_cause_are_not_their_numbers_multiplied() -> None:
    """The whole point: two claims with one cause behind them are not independent.

    On the diamond, two claims are both caused by the same claim. Multiplying their
    own numbers together says they are independent, and they are not, so the two
    answers differ — which is exactly why a route's likelihoods are never
    multiplied along it.
    """
    forward = a_map(SHAPES["a diamond"])
    each = solve(forward, {})
    together = all_true(forward, {}, ("c1", "c2"))
    assert not numpy.allclose(together, each["c1"] * each["c2"])


def test_two_pieces_that_share_nothing_are_their_numbers_multiplied() -> None:
    """And the other side of it: claims with nothing between them do multiply.

    The joint is not "never a product". It is "a product only when the claims are
    really independent", and on a map of two pieces that share no arrow and no
    cause they are — so the joint and the product agree, and this is the case that
    would fail if the elimination quietly dropped a factor.
    """
    forward = a_map(SHAPES["two pieces that share nothing"])
    each = solve(forward, {})
    numpy.testing.assert_allclose(
        all_true(forward, {}, ("c1", "c3")),
        each["c1"] * each["c3"],
        rtol=0.0,
        atol=EXACT,
    )


def test_asking_whether_nothing_is_true_is_refused_rather_than_answered() -> None:
    """An empty list has no answer, so it is said out loud instead of guessed at."""
    forward = a_map(SHAPES["a collider"])
    with pytest.raises(ValueError, match="at least one claim"):
        all_true(forward, {}, ())


def test_a_joint_under_news_no_world_agrees_with_is_refused_by_name() -> None:
    """The same refusal the solve makes, for the same reason and naming the same claims."""
    forward = a_map({"c0": (), "c1": ("c0",)})
    never = forward.table["c1"].copy()
    never[..., 1] = 0.0
    never[..., 0] = 1.0
    impossible = Forward(
        order=forward.order,
        causes=forward.causes,
        times={},
        table={**forward.table, "c1": never},
        shapes={},
        rates={},
        added={},
    )
    with pytest.raises(ImpossibleObservation) as refused:
        all_true(impossible, {"c1": Pin(value=True, kind="observe")}, ("c0",))
    assert refused.value.claims == ("c1",)
