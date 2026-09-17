"""The walk: which claim is asked about next, and what makes a run stop.

Every run here is told a story — for each claim, what the model would answer if
asked about it — and the test checks the map that came out and the one reason the
run gives for stopping.
"""

from katalyst.engine.expand import Accepted, Caps, Finished, Outcome, Refused, grow
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
    told = Storyteller({STARTED_AT: [expensive]}, starting=[expensive])
    steps = walk(told, at_once=1, dollars=1.0)
    finished = ending(steps)

    assert finished.reason == "spend_cap"
    assert finished.receipt.dollars >= 1.0
    assert "reached its spending limit of $1.00" in finished.why
    assert f"${finished.receipt.dollars:.2f}" in finished.why
    assert f"built {finished.claims} claims and {finished.links} arrows" in finished.why


def test_a_run_makes_no_further_call_once_it_has_spent_its_ceiling() -> None:
    """Stopping late is not stopping."""
    expensive = an_answer(
        a_claim(A_STEP, cause=FROM_THE_QUESTION), read_fresh=400_000, written=200_000
    )
    told = Storyteller({STARTED_AT: [expensive]}, starting=[expensive])
    walk(told, at_once=1, dollars=1.0)
    stopped_after = len(told.asked)

    told_again = Storyteller({STARTED_AT: [expensive]}, starting=[expensive])
    walk(told_again, at_once=1, dollars=1.0)

    assert len(told_again.asked) == stopped_after


def test_a_run_stops_searching_at_its_search_cap() -> None:
    """The map keeps building; the arrows added afterwards say they argued."""
    searching = an_answer(a_claim(A_STEP, cause=FROM_THE_QUESTION), searches=1)
    told = Storyteller(
        {
            STARTED_AT: [searching, an_answer(a_claim(ANOTHER_STEP, cause=FROM_THE_QUESTION))],
            A_STEP: [an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market"))],
        }
    )
    finished = ending(walk(told, at_once=1, searches=1))

    assert finished.receipt.searches <= 1
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
                an_answer(a_claim(AN_ENDING, cause=FROM_THE_QUESTION, kind="market")),
                an_answer(a_link(FROM_THE_QUESTION, AN_ENDING)),
                an_answer(a_stop()),
            ],
            A_STEP: [an_answer(a_stop())],
        }
    )
    steps = walk(told, at_once=1, width=3)
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
