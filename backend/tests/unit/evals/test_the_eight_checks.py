"""The eight structural checks, each shown holding and each shown not holding.

**Four of the eight can only fail if our own pipeline let something past.** The
map's own rules judge every proposal at the moment it is accepted, so a loop, an
arrow with no reason, a claim with no test and a count with no page behind it
cannot reach a finished map through `expand` at all. Those four are therefore
fed maps damaged on purpose — the same damaged maps the rules layer's own tests
use — because the question they answer is *"and if one ever did?"*

The other four can fail on a real run, and they are shown failing on one, through
the harness itself with a stand-in answering: a map that ends nowhere, a Verify
answer that claims a route nothing reaches, a run whose cache is never read back,
and a run that spends past its ceiling.
"""

from datetime import date

from evals.run import Case, checks_on
from hypothesis import given
from hypothesis import strategies as st

from katalyst.domain import BaseRate, Graph
from katalyst.engine.grow import Finished
from katalyst.engine.receipt import Receipt, nothing_spent_yet
from katalyst.engine.record import Run
from katalyst.engine.transcript import Transcript, TranscriptLine
from katalyst.engine.verify import Verdict
from tests import strategies

A_DAY = date(2026, 9, 17)
"""The day these runs pretend to have happened on. Nothing here is about a date."""

AN_EXPLORE_CASE = Case(id="a-case", hypothesis="Something happens.", door="explore", seed=1)
AN_UNREACHABLE_CASE = Case(
    id="unreachable",
    hypothesis="Something happens.",
    door="verify",
    target="Something unrelated happens.",
    unreachable=True,
    seed=1,
)
A_REACHABLE_CASE = AN_UNREACHABLE_CASE.model_copy(update={"id": "reachable", "unreachable": False})


def a_run(
    graph: Graph | None,
    *,
    reason: str = "reached_terminal",
    lines: tuple[TranscriptLine, ...] = (),
) -> Run:
    """Build what one run produced, around a map somebody hands in.

    Everything the checks read and nothing else: the finished map, the reason the
    walk gave for stopping, and the transcript's own lines.
    """
    finished = (
        None
        if reason == ""
        else Finished(
            reason=reason,  # type: ignore[arg-type]
            why="Because.",
            graph=graph,
            receipt=nothing_spent_yet(),
        )
    )
    return Run(
        example="a-case",
        hypothesis="Something happens.",
        seed=1,
        on=A_DAY,
        seconds=1.0,
        events=(),
        transcript=Transcript(
            generation_id="a-generation",
            hypothesis="Something happens.",
            seed=1,
            on=A_DAY,
            mode="live",
            lines=lines,
        ),
        finished=finished,
    )


def a_call(*, read_back: int = 0) -> TranscriptLine:
    """One line of a transcript, saying only what this file cares about."""
    return TranscriptLine(what="accepted", in_words="Something.", cache_read_tokens=read_back)


TWO_CALLS = (a_call(), a_call(read_back=1_800))
"""A run that made two calls and read the second one's standing half back out of the cache."""


def held(case: Case, run: Run, *, spent: Receipt | None = None, ceiling: float = 15.0) -> set[int]:
    """Which of the eight checks held, by number."""
    checked = checks_on(case, run, spent or nothing_spent_yet(), ceiling, None)
    return {one.number for one in checked if one.held}


# --- The four that only fail if the accept step let something past ----------


@given(strategies.broken_graphs("cycle"))
def test_a_map_that_causes_itself_fails_the_loop_check(graph: Graph) -> None:
    """Check 1. A map that runs round in circles cannot be worked through at all.

    `expand` refuses such a proposal at the moment it lands, so this map could
    only exist if something had bypassed that — which is exactly what the check
    is watching for.
    """
    assert 1 not in held(AN_EXPLORE_CASE, a_run(graph, lines=TWO_CALLS))


@given(strategies.broken_graphs("no_terminal"))
def test_a_map_that_ends_in_prose_fails_the_ending_check(graph: Graph) -> None:
    """Check 2. A chain has to end in an instrument, or in a plain statement there is none."""
    assert 2 not in held(AN_EXPLORE_CASE, a_run(graph, lines=TWO_CALLS))


@given(
    st.one_of(
        strategies.broken_graphs("missing_rationale"),
        strategies.broken_graphs("documented_without_source"),
    )
)
def test_an_arrow_with_no_reason_or_no_page_fails_the_arrow_check(graph: Graph) -> None:
    """Check 3. An arrow is an argument; one claiming evidence has to carry it."""
    assert 3 not in held(AN_EXPLORE_CASE, a_run(graph, lines=TWO_CALLS))


@given(strategies.broken_graphs("missing_resolution"))
def test_a_claim_nobody_could_settle_fails_the_claim_check(graph: Graph) -> None:
    """Check 4. A claim nobody can check is a vibe, and a likelihood on a vibe scores nothing."""
    assert 4 not in held(AN_EXPLORE_CASE, a_run(graph, lines=TWO_CALLS))


@given(strategies.graphs())
def test_a_whole_map_the_rules_accept_holds_all_four_of_them(graph: Graph) -> None:
    """The other side of the same four: a map nobody damaged gives them nothing to find.

    Built rather than assumed away — every map this draws already satisfies every
    rule — so the four checks are shown holding on maps nobody wrote by hand.
    """
    assert {1, 2, 3, 4} <= held(AN_EXPLORE_CASE, a_run(graph, lines=TWO_CALLS))


@given(strategies.graphs())
def test_a_count_of_past_cases_with_no_page_behind_it_fails_the_count_check(
    graph: Graph,
) -> None:
    """Check 8. A count with no page behind it reads as measured however it is marked.

    The accept step drops one and leaves its note in the transcript, so a count
    that reached the map without a page is not a worse map — it is a claim that
    got past the accept step, which is a fault of a different order.
    """
    recalled = BaseRate(reference_class="Things like this, since 1990", k=12, n=15)
    looked_up = recalled.model_copy(update={"sources": ("https://example.test/counted",)})
    every_count_sourced = _counting(graph, looked_up)
    one_count_recalled = _counting(graph, looked_up, first=recalled)

    assert 8 in held(AN_EXPLORE_CASE, a_run(every_count_sourced, lines=TWO_CALLS))
    assert 8 not in held(AN_EXPLORE_CASE, a_run(one_count_recalled, lines=TWO_CALLS))


def _counting(graph: Graph, every: BaseRate, first: BaseRate | None = None) -> Graph:
    """Put the same count of past cases on every claim, and another on the first.

    Built rather than assumed away: a drawn map already carries counts of its own,
    some with a page behind them and some without, so a test that read them as
    they came would be about whichever ones were drawn.
    """
    counted = [one.model_copy(update={"base_rate": every}) for one in graph.propositions]
    if first is not None:
        counted[0] = counted[0].model_copy(update={"base_rate": first})
    return graph.model_copy(update={"propositions": tuple(counted)})


# --- The Verify door --------------------------------------------------------


def test_an_explore_case_holds_the_door_check_by_having_no_door() -> None:
    """Check 5 on a case that asked no such question. There is nothing to answer."""
    checked = checks_on(
        AN_EXPLORE_CASE, a_run(None, reason="reached_terminal"), nothing_spent_yet(), 15.0, None
    )

    assert next(one for one in checked if one.number == 5).held


def test_a_verify_case_that_came_back_with_no_answer_at_all_fails_the_door_check() -> None:
    """A person who asked whether the story gets somewhere is owed one of two answers."""
    checked = checks_on(A_REACHABLE_CASE, a_run(None), nothing_spent_yet(), 15.0, None)

    assert not next(one for one in checked if one.number == 5).held


def test_a_route_that_is_claimed_and_not_named_fails_the_door_check() -> None:
    """*Reached* with no route is the shape of an answer with nothing behind it."""
    claimed = Verdict(kind="reached", path=(), why="It gets there.")
    checked = checks_on(A_REACHABLE_CASE, a_run(None), nothing_spent_yet(), 15.0, claimed)

    assert not next(one for one in checked if one.number == 5).held


def test_the_unreachable_case_saying_it_got_there_fails_the_door_check() -> None:
    """The whole reason that case is in the set: a mechanism exists, or a bridge was invented.

    Nothing here reads *which* claim the answer named. That is the model's answer,
    and grading it would be grading wording.
    """
    claimed = Verdict(kind="reached", path=("a", "b"), why="It gets there.")
    checked = checks_on(AN_UNREACHABLE_CASE, a_run(None), nothing_spent_yet(), 15.0, claimed)

    assert not next(one for one in checked if one.number == 5).held


def test_an_honest_refusal_holds_the_door_check_on_either_kind_of_case() -> None:
    """*No route* is one of the two honest answers, whether or not one was expected."""
    refused = Verdict(kind="no_path", nearest="a", why="Nothing on this map reaches it.")
    for case in (A_REACHABLE_CASE, AN_UNREACHABLE_CASE):
        checked = checks_on(case, a_run(None), nothing_spent_yet(), 15.0, refused)

        assert next(one for one in checked if one.number == 5).held, case.id


# --- The cache, and the ceiling ---------------------------------------------


def test_a_run_whose_cache_is_never_read_back_fails_that_check() -> None:
    """Check 6. Zero cache reads is a bug in how the request is put together, not a slow day."""
    never = (a_call(), a_call(), a_call())

    assert 6 not in held(AN_EXPLORE_CASE, a_run(None, lines=never))
    assert 6 in held(AN_EXPLORE_CASE, a_run(None, lines=TWO_CALLS))


def test_a_run_of_one_call_has_no_second_call_to_read_the_cache_on() -> None:
    """The standing half is written on the first call and read back from the second.

    A run that only ever made one call cannot be said to have read it back, and
    saying the check held would be saying something nobody measured.
    """
    assert 6 not in held(AN_EXPLORE_CASE, a_run(None, lines=(a_call(),)))


def test_a_run_that_cannot_say_why_it_stopped_fails_the_stopping_check() -> None:
    """Check 7. A run nobody can account for is a run nobody can budget."""
    assert 7 not in held(AN_EXPLORE_CASE, a_run(None, reason=""))


def test_a_run_that_spent_past_its_ceiling_fails_the_stopping_check() -> None:
    """The other half of check 7: a ceiling that was passed is a ceiling that did not hold."""
    over = nothing_spent_yet().model_copy(update={"dollars": 15.40})

    assert 7 not in held(AN_EXPLORE_CASE, a_run(None), spent=over, ceiling=15.0)


def test_stopping_because_the_money_ran_out_is_a_decision_and_holds_the_check() -> None:
    """Kent, G5: a run that reaches its ceiling stops and says what it spent.

    That is a named reason like any other. Failing the check for it would be
    marking the cap working as the cap failing.
    """
    at_the_cap = nothing_spent_yet().model_copy(update={"dollars": 15.0})

    assert 7 in held(
        AN_EXPLORE_CASE, a_run(None, reason="spend_cap"), spent=at_the_cap, ceiling=15.0
    )


# --- A run that never built a map at all ------------------------------------


def test_a_run_that_built_no_map_fails_every_structural_check_and_says_so() -> None:
    """Its row is still written, because a row saying no map was built is worth having.

    Checks 5, 6 and 7 are about the run rather than about the map, so they are
    still read; the five that are about the map have nothing to read.
    """
    checked = checks_on(AN_EXPLORE_CASE, a_run(None), nothing_spent_yet(), 15.0, None)
    structural = [one for one in checked if one.number in (1, 2, 3, 4, 8)]

    assert len(checked) == 8
    assert not any(one.held for one in structural)
    assert all("built no map" in one.why for one in structural)
