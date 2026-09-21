"""The walk: which claim is asked about next, and what makes a run stop.

Every run here is told a story — for each claim, what the model would answer if
asked about it — and the test checks the map that came out and the one reason the
run gives for stopping.
"""

from katalyst.domain import validate
from katalyst.engine.client import SEARCHES_INSIDE_ONE_CALL, TheModelDidNotAnswer
from katalyst.engine.grow import Finished, grow
from katalyst.engine.outcome import Accepted, Caps, Outcome, Refused
from katalyst.engine.receipt import dollars_for
from tests.unit.engine.answers import (
    FROM_THE_QUESTION,
    THE_DAY_THE_RUN_HAPPENED,
    Scripted,
    Storyteller,
    a_claim,
    a_declined_answer,
    a_link,
    a_starting_claim,
    a_stop,
    an_answer,
)

STARTED_AT = "The thing the person expects happens."
A_STEP = "A step in the middle of the story."
ANOTHER_STEP = "A second step in the middle."
AN_ENDING = "Something you could put money on."


def walk(answerer: object, **caps: object) -> list[object]:
    """Run one whole walk and collect everything it handed back."""
    return list(
        grow(
            "The thing the person expects happens.",
            answerer=answerer,  # type: ignore[arg-type]
            on=THE_DAY_THE_RUN_HAPPENED,
            caps=Caps(**caps),  # type: ignore[arg-type]
        )
    )


def ending(steps: list[object]) -> Finished:
    """Take the one `Finished` a walk always hands back last."""
    assert isinstance(steps[-1], Finished)
    assert not any(isinstance(one, Finished) for one in steps[:-1])
    return steps[-1]


def test_a_walk_hands_back_every_outcome_and_then_exactly_one_finished() -> None:
    """Nothing is buffered, so a caller can draw the map as it arrives."""
    steps = walk(Storyteller())

    assert all(isinstance(one, Outcome) for one in steps[:-1])
    assert isinstance(steps[-1], Finished)


def test_a_line_that_runs_to_an_ending_says_it_reached_one() -> None:
    """The ordinary, good ending."""
    told = Storyteller(
        {
            STARTED_AT: [an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION))],
            A_STEP: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))],
        }
    )
    finished = ending(walk(told, at_once=1))

    assert finished.reason == "reached_terminal"
    assert finished.why == "Every line ran to an ending."
    assert finished.graph is not None
    assert {one.claim for one in finished.graph.propositions} == {STARTED_AT, A_STEP, AN_ENDING}


def test_an_ending_never_joins_the_frontier() -> None:
    """There is nothing downstream of a trade."""
    told = Storyteller(
        {
            STARTED_AT: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))],
        }
    )
    walk(told, at_once=1)

    assert AN_ENDING not in told.asked_about


def test_the_cause_a_proposal_names_is_the_claim_the_question_was_about() -> None:
    """The prompt hands out the names, and an answer points back at one of them."""
    told = Storyteller(
        {STARTED_AT: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))]}
    )
    finished = ending(walk(told, at_once=1))

    assert finished.graph is not None
    started = finished.graph.hypothesis_id
    assert [one.source for one in finished.graph.links] == [started]


def test_a_generation_that_reaches_no_ending_says_so() -> None:
    """One last call per open line, and then an honest card."""
    told = Storyteller({STARTED_AT: [an_answer(a_stop("Nothing more here."))]})
    finished = ending(walk(told, at_once=1))

    assert finished.reason == "no_terminal"
    assert "does not end anywhere you can act on" in finished.why
    assert told.asked_about.count(STARTED_AT) > 1
    assert "answer only with an ending" in told.asked[-1]


def test_the_engine_never_writes_a_claim_the_model_did_not_propose() -> None:
    """Adding an ending ourselves to make the map legal would be a claim with no author."""
    told = Storyteller({STARTED_AT: [an_answer(a_stop())]})
    finished = ending(walk(told, at_once=1))

    assert finished.graph is not None
    assert [one.claim for one in finished.graph.propositions] == [STARTED_AT]
    assert finished.graph.links == ()


def test_three_refusals_in_a_row_close_a_claim() -> None:
    """The cap is on attempts, whatever kind of failure each one was."""
    told = Storyteller({STARTED_AT: [a_declined_answer()] * 4})
    steps = walk(told, at_once=1, refusals_in_a_row=3)
    finished = ending(steps)

    refusals = [one for one in steps[:-1] if isinstance(getattr(one, "result", None), Refused)]
    # Three on the claim itself, then one more on the last ending-seeking call.
    assert len(refusals) == 4
    assert finished.refused == 4
    assert finished.reason == "no_terminal"


def test_the_claim_cap_stops_the_map_growing() -> None:
    """A whole-map limit, reported under its own name."""
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION)),
            ],
            A_STEP: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))],
        }
    )
    cap = 3
    finished = ending(walk(told, at_once=1, claims=cap))

    assert finished.reason == "claim_cap"
    assert f"limit of {cap} claims" in finished.why
    assert finished.graph is not None
    # Growing stopped at the cap. The one claim past it is the ending the last
    # call asked for, which is what stops the map ending nowhere.
    steps = [
        one for one in finished.graph.propositions if one.kind not in ("market", "not_tradeable")
    ]
    assert len(steps) == cap
    assert any(one.kind == "market" for one in finished.graph.propositions)


def test_the_depth_cap_closes_a_line_and_the_run_says_which_cap_it_was() -> None:
    """One line runs to an ending; another is cut short by our own limit."""
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
            ],
            A_STEP: [an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION))],
        }
    )
    finished = ending(walk(told, at_once=1, depth=1, width=2))

    assert finished.reason == "depth_cap"
    assert "limit of 1 layers" in finished.why
    assert A_STEP not in told.asked_about


def test_the_width_cap_closes_a_claim() -> None:
    """How many pieces one claim may hang off itself."""
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION)),
            ]
        }
    )
    finished = ending(walk(told, at_once=1, width=1))

    assert finished.graph is not None
    caused_by_the_start = [
        one for one in finished.graph.links if one.source == finished.graph.hypothesis_id
    ]
    assert len(caused_by_the_start) == 1


def test_a_run_stops_at_its_spending_cap_and_says_so() -> None:
    """Checked after every call, and it names what it spent and what it got."""
    expensive = an_answer(
        a_claim(A_STEP, cause=FROM_THE_QUESTION), read_fresh=400_000, written=200_000
    )
    an_expensive_start = an_answer(
        a_starting_claim(STARTED_AT), read_fresh=400_000, written=200_000
    )
    told = Storyteller({STARTED_AT: [expensive]}, starting=[an_expensive_start])
    steps = walk(told, at_once=1, dollars=1.0)
    finished = ending(steps)

    assert finished.reason == "spend_cap"
    assert finished.receipt.dollars >= 1.0
    assert "reached its spending limit of $1.00" in finished.why
    assert f"${finished.receipt.dollars:.2f}" in finished.why
    assert f"built {finished.claims} claims and {finished.links} arrows" in finished.why


def test_a_run_makes_no_further_call_once_it_has_spent_its_ceiling() -> None:
    """Stopping late is not stopping."""
    expensive = an_answer(a_starting_claim(STARTED_AT), read_fresh=400_000, written=200_000)
    told = Storyteller(starting=[expensive])
    walk(told, at_once=1, dollars=1.0)
    stopped_after = len(told.asked)

    told_again = Storyteller(starting=[expensive])
    walk(told_again, at_once=1, dollars=1.0)

    assert len(told_again.asked) == stopped_after


def test_a_run_stops_searching_at_its_search_cap() -> None:
    """The map keeps building; the arrows added afterwards say they argued.

    The cap is a whole call's worth, because a call is told once whether it may
    search and can then spend up to its own ceiling: a budget smaller than that
    ceiling can never be handed to anybody (2026-09-20).
    """
    searching = an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION), searches=1)
    told = Storyteller(
        {
            STARTED_AT: [searching, an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION))],
            A_STEP: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))],
        }
    )
    finished = ending(walk(told, at_once=1, searches=SEARCHES_INSIDE_ONE_CALL))

    assert finished.receipt.searches <= SEARCHES_INSIDE_ONE_CALL
    assert told.searched[0] is True
    assert told.searched[-1] is False
    assert finished.reason != "no_terminal"
    assert finished.graph is not None
    assert len(finished.graph.propositions) > 2


def test_a_walk_gives_the_same_map_twice_from_the_same_answers() -> None:
    """Three lines are asked about at once, and the fold order is the frontier's."""
    story = {
        STARTED_AT: [
            an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
            an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION)),
            an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
        ],
        A_STEP: [an_answer(a_stop())],
        ANOTHER_STEP: [an_answer(a_stop())],
    }
    first = ending(walk(Storyteller({one: list(said) for one, said in story.items()})))
    second = ending(walk(Storyteller({one: list(said) for one, said in story.items()})))

    assert first.graph is not None and second.graph is not None
    assert [one.claim for one in first.graph.propositions] == [
        one.claim for one in second.graph.propositions
    ]
    assert first.reason == second.reason


def test_a_run_that_never_gets_started_says_so_and_builds_no_map() -> None:
    """Three tries at turning the sentence into a claim, then an honest sentence."""
    steps = walk(Scripted(starting=[a_declined_answer()]), at_once=1)
    finished = ending(steps)

    assert finished.graph is None
    assert finished.claims == 0
    assert "never got started" in finished.why
    assert len(steps) - 1 == 3


def test_the_receipt_counts_every_call_the_run_made() -> None:
    """A call that cost money and is not counted is money the receipt cannot account for."""
    told = Storyteller(
        {STARTED_AT: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))]}
    )
    steps = walk(told, at_once=1)
    finished = ending(steps)

    outcomes = [one for one in steps[:-1] if isinstance(one, Outcome)]
    assert finished.receipt.calls == sum(one.calls for one in outcomes)
    assert finished.receipt.input_tokens == sum(one.input_tokens for one in outcomes)
    assert finished.receipt.dollars == dollars_for(finished.receipt)
    assert finished.receipt.calls == len(told.asked)


def test_the_destination_is_added_up_front_as_an_ordinary_step() -> None:
    """A destination is where a person wants the story to get to, not where it ends."""
    told = Storyteller(
        starting=[
            an_answer(a_starting_claim(STARTED_AT)),
            an_answer(a_starting_claim("Does it get here?")),
        ],
    )
    steps = list(
        grow(
            STARTED_AT,
            target="Does it get here?",
            answerer=told,  # type: ignore[arg-type]
            on=THE_DAY_THE_RUN_HAPPENED,
            caps=Caps(at_once=1),
        )
    )
    finished = ending(steps)

    assert finished.graph is not None
    wanted = next(one for one in finished.graph.propositions if one.claim == "Does it get here?")
    assert wanted.kind == "event"
    assert finished.destination == wanted.id
    assert finished.graph.propositions[0].kind == "hypothesis"


def test_every_question_after_the_first_carries_the_destination() -> None:
    """Expansion is steered toward it, and told not to bend a step to get there."""
    told = Storyteller(
        starting=[
            an_answer(a_starting_claim(STARTED_AT)),
            an_answer(a_starting_claim("Does it get here?")),
        ],
    )
    list(
        grow(
            STARTED_AT,
            target="Does it get here?",
            answerer=told,  # type: ignore[arg-type]
            on=THE_DAY_THE_RUN_HAPPENED,
            caps=Caps(at_once=1),
        )
    )

    expanding = [one for one in told.asked if "We are asking about this claim: " in one]
    assert expanding
    assert all("Does it get here?" in one for one in expanding)
    assert all("do not bend a step to get there" in one for one in expanding)


def test_an_accepted_claim_arrives_as_its_own_outcome() -> None:
    """A caller draws each claim as it lands, which is what the loading state is."""
    told = Storyteller(
        {STARTED_AT: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))]}
    )
    steps = walk(told, at_once=1)

    landed = [
        one.result.proposition.claim
        for one in steps[:-1]
        if isinstance(one, Outcome)
        and isinstance(one.result, Accepted)
        and one.result.proposition is not None
    ]
    assert landed == [STARTED_AT, AN_ENDING]


def test_the_reason_names_what_closed_the_last_line_that_was_still_open() -> None:
    """One line ends at a trade; the other is abandoned after three refusals."""
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_stop()),
            ],
            A_STEP: [a_declined_answer()] * 4,
        }
    )
    finished = ending(walk(told, at_once=1, refusals_in_a_row=3))

    assert finished.reason == "refusal_cap"
    assert "abandoned after 3 proposals" in finished.why


def test_every_outcome_carries_the_frontier_as_it_stands_after_it() -> None:
    """No answer ever says "this claim is closed"; a claim leaving the list is how you learn."""
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_stop()),
            ],
            A_STEP: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))],
        }
    )
    steps = walk(told, at_once=1)
    outcomes = [one for one in steps[:-1] if isinstance(one, Outcome)]
    finished = ending(steps)

    assert finished.graph is not None
    started = finished.graph.hypothesis_id
    # The claim the map starts from arrives first, and is open the moment it does.
    assert outcomes[0].frontier == (started,)
    # The last answer leaves nothing open, which is what empties the canvas of
    # skeletons all at once.
    assert outcomes[-1].frontier == ()
    # An ending never joins the list.
    landed = {
        one.result.proposition.id
        for one in outcomes
        if isinstance(one.result, Accepted) and one.result.proposition is not None
    }
    endings = {
        one.id for one in finished.graph.propositions if one.kind in ("market", "not_tradeable")
    }
    assert endings <= landed
    assert all(not (set(one.frontier) & endings) for one in outcomes)


def test_the_claim_the_map_starts_from_arrives_as_an_accepted_answer_with_no_arrows() -> None:
    """A claim with nothing causing it is exactly what a hypothesis is."""
    told = Storyteller(
        {STARTED_AT: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))]}
    )
    steps = walk(told, at_once=1)

    first = steps[0]
    assert isinstance(first, Outcome)
    assert isinstance(first.result, Accepted)
    assert first.result.proposition is not None
    assert first.result.proposition.kind == "hypothesis"
    assert first.result.links == ()
    assert first.about is None


def test_a_refusal_that_is_not_the_third_leaves_the_frontier_where_it_was() -> None:
    """The count is what changes, not the map and not what is open."""
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                a_declined_answer(),
                an_answer(a_stop()),
            ]
        }
    )
    steps = walk(told, at_once=1, refusals_in_a_row=3)
    outcomes = [one for one in steps[:-1] if isinstance(one, Outcome)]

    refused_at = next(i for i, one in enumerate(outcomes) if isinstance(one.result, Refused))
    assert outcomes[refused_at].frontier == outcomes[refused_at - 1].frontier


def test_an_arrow_between_two_claims_counts_toward_the_room_beside_its_cause() -> None:
    """The width cap counts what leaves a claim, whether or not a claim came with it.

    A cap that counted only the claims one claim caused could be walked past for
    ever by proposing arrows instead. This is the step the generation chapter
    works in full: a claim's third arrow closes it, and the arrow that closed it
    brought no claim with it.
    """
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_link(FROM_THE_QUESTION, AN_ENDING)),
                an_answer(a_stop()),
            ],
            # The ending is reached from the step, so the arrow the starting claim
            # draws to it is the first between that pair — a second arrow the same
            # way round is a fault of its own since 2026-09-20, and this test is
            # about the width cap rather than that rule.
            A_STEP: [
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_stop()),
            ],
            ANOTHER_STEP: [an_answer(a_stop())],
        }
    )
    steps = walk(told, at_once=2, width=3)
    finished = ending(steps)

    assert finished.graph is not None
    started = finished.graph.hypothesis_id
    assert sum(1 for one in finished.graph.links if one.source == started) == 3
    # The arrow that closed it brought no claim with it.
    arrow_only = [
        one
        for one in steps[:-1]
        if isinstance(one, Outcome)
        and isinstance(one.result, Accepted)
        and one.result.proposition is None
        and one.result.links
    ]
    assert len(arrow_only) == 1
    assert started not in arrow_only[0].frontier
    assert told.asked_about.count(STARTED_AT) == 3


# --- A round of answers is judged where the map actually changes -----------
#
# Found by a read-only review of the pipeline, 2026-09-20, and confirmed by
# running it. A round hands one snapshot of the map to all three calls and each
# answer is judged against that snapshot, then all three are appended with no
# further check. Two answers, each perfectly legal on its own, could between them
# leave a map the rules refuse — and nothing was shown, counted or refused.


def refusals_in(steps: list[object]) -> list[Outcome]:
    """Every refused outcome a walk handed back, in order."""
    return [one for one in steps if isinstance(one, Outcome) and isinstance(one.result, Refused)]


def a_round_that_closes_a_loop() -> Storyteller:
    """Two answers in one round which are legal apart and a loop together."""
    return Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_stop()),
            ],
            A_STEP: [
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_link(A_STEP, ANOTHER_STEP)),
                an_answer(a_stop()),
            ],
            ANOTHER_STEP: [
                an_answer(a_link(ANOTHER_STEP, A_STEP)),
                an_answer(a_stop()),
            ],
        }
    )


def test_a_round_never_leaves_behind_a_map_the_rules_refuse() -> None:
    """The map that comes out of a concurrent walk is a map `validate` accepts.

    The two answers in the last round draw an arrow each way round between the
    same two claims. Each is legal against the map as it stood when the round
    started; together they are a loop. The one folded second is the one that
    breaks it, and it is refused there — where the map actually changes.
    """
    steps = walk(a_round_that_closes_a_loop(), at_once=3, width=3)
    finished = ending(steps)

    assert finished.graph is not None
    assert validate(finished.graph) == []


def test_an_answer_that_stops_being_legal_before_it_lands_is_refused_like_any_other() -> None:
    """Shown, counted, never quietly dropped and never repaired."""
    steps = walk(a_round_that_closes_a_loop(), at_once=3, width=3)
    finished = ending(steps)

    refused = refusals_in(steps[:-1])
    assert len(refused) == 1
    assert [one.code for one in refused[0].result.violations] == ["cycle"]  # type: ignore[union-attr]
    assert finished.refused == 1
    # The money it cost is still on the bill: it was a real call.
    assert refused[0].calls == 1


def test_two_answers_in_one_round_cannot_draw_the_same_arrow_twice() -> None:
    """The other half of the same hole, and the reason `duplicate_link` exists."""
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_stop()),
            ],
            A_STEP: [
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_link(A_STEP, ANOTHER_STEP)),
                an_answer(a_stop()),
            ],
            ANOTHER_STEP: [
                an_answer(a_link(A_STEP, ANOTHER_STEP)),
                an_answer(a_stop()),
            ],
        }
    )

    steps = walk(told, at_once=3, width=3)
    finished = ending(steps)

    assert finished.graph is not None
    assert validate(finished.graph) == []
    refused = refusals_in(steps[:-1])
    assert [one.code for one in refused[0].result.violations] == ["duplicate_link"]  # type: ignore[union-attr]


def test_the_width_cap_counts_the_room_beside_the_arrows_own_cause() -> None:
    """An arrow naming somebody else's claim as its cause spends that claim's width.

    Before this, the cap was checked only against the claim the call was about, so
    an arrow proposed while expanding one claim could add a fourth, fifth and
    sixth arrow to another (2026-09-20).
    """
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_stop()),
            ],
            A_STEP: [
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                # Its own width is spent; this arrow spends the starting claim's.
                an_answer(a_link(STARTED_AT, AN_ENDING)),
                an_answer(a_stop()),
            ],
            ANOTHER_STEP: [an_answer(a_stop())],
        }
    )

    steps = walk(told, at_once=1, width=2)
    finished = ending(steps)

    assert finished.graph is not None
    started = finished.graph.hypothesis_id
    assert sum(1 for one in finished.graph.links if one.source == started) == 2
    refused = refusals_in(steps[:-1])
    assert len(refused) == 1
    assert "room beside" in refused[0].result.claim_in_words  # type: ignore[union-attr]


# --- Caps that were checked in the wrong place -----------------------------


def an_expensive_round() -> Storyteller:
    """A story whose second round costs more than the run is allowed to spend."""
    return Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION), written=200_000),
                an_answer(a_stop()),
            ],
            A_STEP: [
                an_answer(
                    a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"), written=200_000
                ),
                an_answer(a_stop()),
            ],
            ANOTHER_STEP: [an_answer(a_stop())],
        }
    )


def test_every_question_a_run_pays_for_is_handed_back_and_counted() -> None:
    """Nothing already paid for is thrown away because the money ran out (2026-09-20).

    A round's calls are all in flight before the first of them is folded. The
    walk used to stop folding the moment the ceiling was passed, so the answers
    behind it were never yielded, never put on the map and never put on the bill —
    a call that cost money and is not counted is money the receipt cannot account
    for, which `outcome.py` forbids in as many words.
    """
    told = an_expensive_round()

    steps = walk(told, at_once=3, dollars=1.0)
    finished = ending(steps)

    outcomes = [one for one in steps[:-1] if isinstance(one, Outcome)]
    assert finished.reason == "spend_cap"
    assert len(outcomes) == len(told.asked)
    assert finished.receipt.calls == len(told.asked)


def test_a_round_never_carries_the_map_past_the_claim_cap() -> None:
    """The cap used to be read once a round, so a round could step over it.

    Three questions in flight can bring three claims back, and the map was only
    measured between rounds: a run allowed three claims could finish with five.
    The round is sized to the room that is left instead (2026-09-20).
    """
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_stop()),
            ],
            # Asked in the same round as the starting claim before the fix, which
            # is how a run allowed three claims came back with four.
            A_STEP: [
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_stop()),
            ],
            ANOTHER_STEP: [an_answer(a_stop())],
        }
    )

    finished = ending(walk(told, at_once=3, claims=3))

    assert finished.graph is not None
    assert len(finished.graph.propositions) == 3
    assert finished.reason == "claim_cap"


def test_a_round_never_carries_the_run_past_the_searches_cap() -> None:
    """The same shape of mistake, and the same fix, on the other cap.

    One call may now run twenty-five searches, so a round of three could carry a
    run seventy-five past its ceiling. Each call in a round is allowed or refused
    the tool in turn, and a call is allowed only while the whole of what it could
    still spend fits — so the ceiling is never passed (2026-09-20).
    """
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION), searches=8),
                an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION), searches=8),
                an_answer(a_stop(), searches=8),
            ],
            A_STEP: [
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"), searches=8),
                an_answer(a_stop(), searches=8),
            ],
            ANOTHER_STEP: [an_answer(a_stop(), searches=8)],
        }
    )

    finished = ending(walk(told, at_once=3, searches=30))

    assert finished.receipt.searches <= 30
    # And the run carried on to a proper ending: a spent budget stops searching,
    # never the generation.
    assert finished.reason != "spend_cap"


def test_a_run_that_runs_out_of_money_on_the_first_question_says_so() -> None:
    """`spend_cap` is an override, and it overrides this too (2026-09-20).

    A run whose very first question emptied the purse used to report `refusal_cap`
    and "the sentence could not be written as a claim anybody could settle" —
    which blames the person's sentence for the ceiling being low.
    """
    told = Scripted(
        starting=[a_declined_answer("Not this one.", written=200_000)],
    )

    finished = ending(walk(told, dollars=1.0))

    assert finished.reason == "spend_cap"
    assert finished.graph is None
    assert "spending limit" in finished.why


def test_a_service_that_would_not_answer_one_call_never_takes_the_round_with_it() -> None:
    """The other two answers of that round were paid for and are still folded.

    Before this, a 429 escaped `expand`, escaped `grow`, and left no partial map,
    no receipt and no `Finished` at all (2026-09-20).
    """
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_stop()),
            ],
            A_STEP: [
                # Asked in the same round as the starting claim's second answer.
                TheModelDidNotAnswer("The model is busy and turned this question away."),
                an_answer(a_stop()),
            ],
        }
    )

    steps = walk(told, at_once=3)
    finished = ending(steps)

    assert finished.graph is not None
    assert len(finished.graph.propositions) == 3
    refused = refusals_in(steps[:-1])
    assert [one.result.claim_in_words for one in refused] == [  # type: ignore[union-attr]
        "The model is busy and turned this question away."
    ]
    assert finished.refused == 1
    assert finished.reason == "reached_terminal"


def test_a_service_that_never_answers_ends_the_run_saying_which_it_was() -> None:
    """Three failures in a row on the first question is a run that cannot start.

    It must not say "the sentence could not be written as a claim anybody could
    settle" — the sentence was never the problem, and a person reading that would
    go and rewrite a perfectly good one (2026-09-20).
    """
    told = Scripted(raises=TheModelDidNotAnswer("The model could not be reached."))

    finished = ending(walk(told))

    assert finished.reason == "refusal_cap"
    assert finished.graph is None
    assert "could not be reached" in finished.why


def test_a_claims_run_of_refusals_starts_again_the_moment_it_is_answered() -> None:
    """Three **in a row**, not three in all — and nothing pinned that until now.

    A line that is refused twice, answered, and then refused twice more has had
    four refusals and is still open, because none of its runs reached three. The
    counter is reset where the acceptance is folded; a counter that only ever
    went up would close a productive line on its fourth mistake of the afternoon
    (2026-09-20).
    """
    refused = an_answer(a_link(STARTED_AT, STARTED_AT))
    told = Storyteller(
        {
            STARTED_AT: [
                refused,
                refused,
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                refused,
                refused,
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_stop()),
            ],
            A_STEP: [an_answer(a_stop())],
        }
    )

    steps = walk(told, at_once=1, width=3)
    finished = ending(steps)

    assert finished.graph is not None
    assert finished.refused == 4
    assert len(finished.graph.propositions) == 3
    # Four refusals and the line was never closed for refusing.
    assert finished.reason != "refusal_cap"


def test_one_question_that_fails_never_discards_its_rounds_other_answers() -> None:
    """The calls of a round go out together and are all billed together.

    Reading them back with a comprehension meant the first exception the seam
    had not converted threw away every other answer of that round — asked,
    answered and paid for, and then on no receipt and in no transcript. Only a
    bug of ours can reach this, since the seam converts everything the service
    can do; a bug is not a reason to lose an afternoon's money (2026-09-20).
    """
    told = Storyteller(
        {
            STARTED_AT: [
                an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION)),
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_stop()),
            ],
            # Asked in the same round as the starting claim's second answer, and
            # it fails in a way nothing downstream has a sentence for.
            A_STEP: [RuntimeError("a bug nobody wrote a sentence for"), an_answer(a_stop())],
        }
    )

    steps = walk(told, at_once=3)
    finished = ending(steps)

    outcomes = [one for one in steps[:-1] if isinstance(one, Outcome)]
    # Every question asked is an outcome handed back and a call on the receipt,
    # the one that failed included.
    assert len(outcomes) == len(told.asked)
    assert finished.receipt.calls == len(told.asked)
    broke = [one for one in outcomes if "nobody chose" in getattr(one.result, "claim_in_words", "")]
    assert len(broke) == 1
    assert "a bug nobody wrote a sentence for" not in broke[0].result.claim_in_words  # type: ignore[union-attr]
