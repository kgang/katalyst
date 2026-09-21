"""The bill: five counters, the price table, and one sentence when the money runs out.

No number below is typed in and then asserted. Each test either compares a total
with the same total worked out a second way, or compares two receipts against
each other.
"""

from katalyst.engine.pricing import (
    CACHE_READ_SHARE_OF_INPUT,
    CACHE_WRITE_SHARE_OF_INPUT,
    DOLLARS_PER_MILLION_INPUT_TOKENS,
    DOLLARS_PER_MILLION_OUTPUT_TOKENS,
    MODEL,
)
from katalyst.engine.receipt import (
    dollars_for,
    fold,
    nothing_spent_yet,
    over_the_cap,
    what_it_spent_and_got,
)
from tests.unit.engine.answers import Scripted, a_claim, an_answer
from tests.unit.engine.test_expand import ask


def a_call(**counters: int) -> object:
    """Make one call's counters, by running one question through the pipeline."""
    return ask(
        Scripted([an_answer(a_claim("Anything at all.", cause="C"), **counters)])  # type: ignore[arg-type]
    )


def test_a_run_that_has_asked_nothing_has_spent_nothing() -> None:
    """Every counter starts at zero, and so does the bill."""
    nothing = nothing_spent_yet()

    assert nothing.model == MODEL
    assert nothing.calls == 0
    assert nothing.dollars == 0.0


def test_folding_a_call_leaves_the_receipt_it_was_given_alone() -> None:
    """A receipt handed to somebody cannot grow behind their back."""
    before = nothing_spent_yet()

    after = fold(before, a_call())  # type: ignore[arg-type]

    assert before.calls == 0
    assert before.dollars == 0.0
    assert after.calls == 1
    assert after.dollars > before.dollars


def test_the_bill_is_always_the_counters_it_sits_beside() -> None:
    """`dollars` is worked out afresh every time the counters change."""
    receipt = fold(fold(nothing_spent_yet(), a_call()), a_call())  # type: ignore[arg-type]

    assert receipt.dollars == dollars_for(receipt)


def test_two_calls_cost_twice_what_one_did() -> None:
    """Nothing is lost between calls, and nothing is counted twice."""
    one = fold(nothing_spent_yet(), a_call())  # type: ignore[arg-type]
    two = fold(one, a_call())  # type: ignore[arg-type]

    assert two.dollars == one.dollars * 2
    assert two.input_tokens == one.input_tokens * 2


def test_a_token_read_back_out_of_the_cache_costs_less_than_a_fresh_one() -> None:
    """The whole reason the standing half of a request never changes."""
    fresh = fold(nothing_spent_yet(), a_call(read_fresh=1000, written=0))  # type: ignore[arg-type]
    cached = fold(
        nothing_spent_yet(),
        a_call(read_fresh=0, written=0, read_from_cache=1000),  # type: ignore[arg-type]
    )

    assert cached.dollars < fresh.dollars
    assert cached.dollars == fresh.dollars * CACHE_READ_SHARE_OF_INPUT


def test_a_token_written_into_the_cache_costs_more_than_a_fresh_one() -> None:
    """Which is why leaving it off the bill would make the ceiling too generous."""
    fresh = fold(nothing_spent_yet(), a_call(read_fresh=1000, written=0))  # type: ignore[arg-type]
    written = fold(
        nothing_spent_yet(),
        a_call(read_fresh=0, written=0, written_to_cache=1000),  # type: ignore[arg-type]
    )

    assert written.dollars > fresh.dollars
    assert written.dollars == fresh.dollars * CACHE_WRITE_SHARE_OF_INPUT


def test_an_answer_costs_more_than_a_question_of_the_same_length() -> None:
    """A direction, not a number: the price table says which way round it goes."""
    assert DOLLARS_PER_MILLION_OUTPUT_TOKENS > DOLLARS_PER_MILLION_INPUT_TOKENS


def test_a_search_is_on_the_bill_as_well_as_the_tokens_it_brought_back() -> None:
    """It is charged per search, so counting only tokens would under-report it."""
    without = fold(nothing_spent_yet(), a_call(searches=0))  # type: ignore[arg-type]
    with_one = fold(nothing_spent_yet(), a_call(searches=1))  # type: ignore[arg-type]

    assert with_one.searches == 1
    assert with_one.dollars > without.dollars


def test_the_ceiling_is_reached_the_moment_the_total_gets_there() -> None:
    """At the cap, not past it: the run stops rather than spending one more."""
    receipt = fold(nothing_spent_yet(), a_call())  # type: ignore[arg-type]

    assert over_the_cap(receipt, receipt.dollars)
    assert not over_the_cap(receipt, receipt.dollars * 2)


def test_the_sentence_names_the_ceiling_what_was_spent_and_what_was_built() -> None:
    """A partial map with a visible reason beats a blank screen with a silent one."""
    receipt = fold(nothing_spent_yet(), a_call())  # type: ignore[arg-type]

    said = what_it_spent_and_got(receipt, 15.0, claims=7, links=6)

    assert "$15.00" in said
    assert f"${receipt.dollars:.2f}" in said
    assert "7 claims and 6 arrows" in said
