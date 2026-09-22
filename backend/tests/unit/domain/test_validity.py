"""What `validate` says about a map, over hundreds of maps nobody wrote by hand.

Every test here is two-sided, and that is the whole design. A map built correctly
must come back with nothing wrong with it; a map with exactly one thing broken
must come back with exactly that one complaint and no others. Either half alone
would pass for a long time while being useless — a checker that complains about
everything satisfies the second half, and one that complains about nothing
satisfies the first.

The maps come from `tests/strategies.py`. `graphs()` builds them valid by
construction; `broken_graphs(*rules)` takes one of those and damages exactly the
rules it is named.
"""

from itertools import pairwise

from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, TypeAdapter, ValidationError

from katalyst.domain import (
    Belief,
    Graph,
    Intervention,
    Violation,
    validate,
)
from tests.strategies import (
    INDEPENDENTLY_BREAKABLE,
    branches,
    broken_graphs,
    graphs,
    interventions,
    raw_belief_fields,
    seeds,
)

# Enough examples to be worth running, and no time limit per example: building a
# whole random map is slow enough that a per-example deadline would flake on a
# loaded machine without telling us anything true.
many = settings(max_examples=40, deadline=None)
a_great_many = settings(max_examples=120, deadline=None)

RULE_ORDER: tuple[tuple[str, ...], ...] = (
    ("missing_resolution",),
    ("claim_without_persistence",),
    ("no_hypothesis", "multiple_hypotheses"),
    ("no_terminal",),
    ("market_without_payoff",),
    ("not_tradeable_without_reason",),
    ("missing_rationale",),
    ("documented_without_source",),
    ("dangling_link",),
    ("duplicate_link",),
    ("cycle",),
    ("reflexive_without_lag",),
    ("half_life_without_impulse",),
    ("impulse_without_half_life",),
    ("belief_out_of_range",),
)
"""The rules in the order the chapter lists them, which is the order faults come back in.

One entry per rule. The second holds two codes because one rule — exactly one
starting claim — fails in two directions.
"""


def _rank_of(code: str) -> int:
    """Say which rule a code belongs to, counting from the top of the table."""
    return next(index for index, codes in enumerate(RULE_ORDER) if code in codes)


# --- The valid side --------------------------------------------------------


@given(graphs())
@a_great_many
def test_valid_graphs_have_no_violations(graph: Graph) -> None:
    """A map built correctly has nothing wrong with it.

    If this ever fails, either the checker or the generator is wrong, and the
    shrunken example says which.
    """
    assert validate(graph) == []


# --- One test per rule -----------------------------------------------------


@given(broken_graphs("missing_resolution"))
@many
def test_validate_rejects_unresolvable_proposition(graph: Graph) -> None:
    """A claim with no test, or no judge, is named and refused."""
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["missing_resolution"]
    assert faults[0].subject in {one.id for one in graph.propositions}
    assert "does not say" in faults[0].message


@given(st.data())
@many
def test_validate_requires_exactly_one_hypothesis(data: st.DataObject) -> None:
    """One rule failing in two directions: a map with no starting claim, and one with several."""
    with_none = data.draw(broken_graphs("no_hypothesis"))
    faults = validate(with_none)
    assert [fault.code for fault in faults] == ["no_hypothesis"]
    assert faults[0].subject == with_none.id

    with_several = data.draw(broken_graphs("multiple_hypotheses"))
    faults = validate(with_several)
    assert [fault.code for fault in faults] == ["multiple_hypotheses"]
    assert faults[0].subject == with_several.id
    assert "exactly one" in faults[0].message


@given(broken_graphs("no_terminal"))
@many
def test_validate_requires_terminal(graph: Graph) -> None:
    """A map that stops at "and so oil is cheaper" is an essay, and is refused as one."""
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["no_terminal"]
    assert faults[0].subject == graph.id


@given(broken_graphs("market_without_payoff"))
@many
def test_validate_requires_payoff_on_market(graph: Graph) -> None:
    """An ending that says it is tradeable has to say what you would trade.

    Either a contract somebody already sells, or an instrument and which way you
    would take it. This is the commonest thing a model gets wrong.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["market_without_payoff"]
    assert "does not say what you would trade" in faults[0].message


@given(broken_graphs("not_tradeable_without_reason"))
@many
def test_validate_requires_reason_on_not_tradeable(graph: Graph) -> None:
    """An ending that says there is nothing to trade has to say why."""
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["not_tradeable_without_reason"]
    assert "does not say why" in faults[0].message


@given(broken_graphs("missing_rationale"))
@many
def test_validate_rejects_link_without_rationale(graph: Graph) -> None:
    """An arrow with a number and no sentence is a state the user cannot trace."""
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["missing_rationale"]
    assert faults[0].subject in {one.id for one in graph.links}


@given(broken_graphs("documented_without_source"))
@many
def test_validate_rejects_unsourced_documented_link(graph: Graph) -> None:
    """An arrow claiming a document or a price behind it must cite one.

    It is not quietly downgraded to "argued" to make it fit. Being generous with an
    unbacked claim is exactly the state a user cannot trace.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["documented_without_source"]
    assert "cites no source" in faults[0].message


@given(broken_graphs("dangling_link"))
@many
def test_validate_rejects_dangling_link(graph: Graph) -> None:
    """Both ends of every arrow name a claim that is on this map.

    The message names the end that exists, because the other one does not.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["dangling_link"]
    assert "not on this map" in faults[0].message


@given(broken_graphs("duplicate_link"))
@many
def test_validate_rejects_a_second_arrow_between_the_same_two_claims(graph: Graph) -> None:
    """One ordered pair of claims, one arrow (2026-09-20).

    Propagation sums every incoming arrow, so two arrows from A to B push B twice
    as hard as either of them says — and the canvas draws two wires where a reader
    sees one relationship. There is no way in these shapes to say "two separate
    channels": strength, lag and shape are per arrow and they simply add. Two
    genuinely different mechanisms want the claim in between them, which is a
    third claim, not a second arrow.

    The two *directions* of a pair are a different thing and stay legal: A -> B
    with B -> A is the feedback loop a reflexive arrow is for.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["duplicate_link"]
    assert "already joined" in faults[0].message


@given(broken_graphs("cycle"))
@many
def test_validate_rejects_cycles(graph: Graph) -> None:
    """Once the feedback arrows are set aside, there are no loops.

    One loop is one complaint, however many ways round it there happen to be, and
    the complaint names the arrow the interface should highlight.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["cycle"]
    assert faults[0].subject in {one.id for one in graph.links}
    assert "form a loop with no delay in it" in faults[0].message


@given(broken_graphs("reflexive_without_lag"))
@many
def test_reflexive_links_have_positive_lag(graph: Graph) -> None:
    """A market cannot change the world it is measuring in zero time."""
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["reflexive_without_lag"]
    assert "has no delay" in faults[0].message


@given(broken_graphs("half_life_without_impulse"))
@many
def test_validate_rejects_half_life_without_impulse(graph: Graph) -> None:
    """A half-life on a push that holds is refused, not quietly ignored.

    Only a spike fades, so only a spike can say how fast. A field we accept and
    then ignore forever is a number the user cannot account for, which is the one
    thing this product is not allowed to show.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["half_life_without_impulse"]
    assert faults[0].subject in {one.id for one in graph.links}
    assert "only a spike fades" in faults[0].message


@given(broken_graphs("impulse_without_half_life"))
@many
def test_validate_rejects_impulse_without_half_life(graph: Graph) -> None:
    """A spike that never says how fast it fades is refused, the same way round as its mirror.

    One idea checked from both sides: a shape and the numbers describing it have to
    agree. A push that holds may not carry a half-life, and a push that does
    nothing but fade must say how fast. Without one there is no decay to work out,
    and whatever the engine did with such an arrow would be a number nobody wrote.

    Reject, never repair — no default half-life is invented anywhere.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["impulse_without_half_life"]
    assert faults[0].subject in {one.id for one in graph.links}
    assert "does not say how fast" in faults[0].message


@given(broken_graphs("belief_out_of_range"))
@many
def test_validate_rejects_belief_out_of_range(graph: Graph) -> None:
    """A likelihood that is not a range around a number between zero and one is refused.

    The bad likelihood has to be built with `model_construct`, the one way of making
    a model without running its checks, because `Belief` itself would refuse it.
    That is the point of the rule: it is the net under maps that arrive some other
    way than through our own classes.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["belief_out_of_range"]
    assert faults[0].subject in {one.id for one in graph.propositions}
    assert "not a range around that number between 0 and 1" in faults[0].message


@given(broken_graphs("claim_without_persistence"))
@many
def test_validate_rejects_a_claim_that_does_not_say_which_kind_of_truth_it_is(
    graph: Graph,
) -> None:
    """A claim that does not say whether it happens once or holds for a while is refused.

    **Always required, and a map without it is refused by name** (Kent, decisions
    note row R48's neighbour R27; decision record 0017). The claim's own class
    requires the field, so the broken claim has to be built with `model_construct`,
    the one way of making a model without running its checks. That is the point of
    the rule: it is the net under maps that arrive some other way than through our
    own classes — a hand-written stored example, or a recording made before the
    field existed. Reject, never repair: nothing guesses `event` on the reader's
    behalf.
    """
    faults = validate(graph)

    assert [fault.code for fault in faults] == ["claim_without_persistence"]
    assert faults[0].subject in {one.id for one in graph.propositions}
    assert "happens once and stays happened" in faults[0].message


@given(graphs())
@settings(max_examples=5, deadline=None)
def test_a_refused_likelihood_is_quoted_the_way_the_product_writes_one(graph: Graph) -> None:
    """This sentence reaches the browser, so it quotes two figures and never sixteen.

    A refused request comes back with this message in its body and the refusal
    strip shows it word for word. A computer holds a tenth plus two tenths as
    0.30000000000000004, and a number nobody wrote and nobody could act on is
    exactly the kind of state this product refuses to put in front of a reader.

    The second half is the other way the same sentence could lie. A number outside
    0 and 1 is not a likelihood at all — that is the fault being reported — so it
    is named as what it is. Writing it the way a likelihood is written would answer
    `>.99` for 1.4, inside a sentence saying the number is out of range.
    """
    awkward = 0.1 + 0.2
    assert repr(awkward) == "0.30000000000000004"

    out_of_order = _with_one_belief(
        graph, Belief.model_construct(p=0.1, lo=awkward, hi=0.9, owner="model")
    )
    said = validate(out_of_order)[0].message
    assert "0.30000000000000004" not in said, said
    assert "is .10, with a range of .30 to .90" in said, said

    past_one = _with_one_belief(graph, Belief.model_construct(p=1.4, lo=0.2, hi=0.5, owner="model"))
    said = validate(past_one)[0].message
    assert ">.99" not in said, said
    assert "is outside 0 to 1, with a range of .20 to .50" in said, said


def _with_one_belief(graph: Graph, belief: Belief) -> Graph:
    """Put one model belief on the map's first claim, leaving everything else alone."""
    victim = graph.propositions[0]
    spoiled = victim.beliefs.model_copy(update={"model": belief})
    return graph.model_copy(
        update={
            "propositions": (
                victim.model_copy(update={"beliefs": spoiled}),
                *graph.propositions[1:],
            )
        }
    )


# --- Every fault at once, in an order that never moves ---------------------


@given(
    rules=st.lists(st.sampled_from(INDEPENDENTLY_BREAKABLE), min_size=3, max_size=3, unique=True),
    data=st.data(),
)
@many
def test_validate_reports_every_violation(rules: list[str], data: st.DataObject) -> None:
    """Three faults in, three faults out. The walk never stops at the first.

    A person fixing a map one fault per rebuild learns only that the tool is
    hostile, and a model given one fault at a time needs one re-prompt per fault.
    """
    graph = data.draw(broken_graphs(*rules))

    assert sorted(fault.code for fault in validate(graph)) == sorted(rules)


@given(broken_graphs(*INDEPENDENTLY_BREAKABLE))
@many
def test_violations_are_ordered_stably(graph: Graph) -> None:
    """The same map always produces the same list, in the order of the rule table.

    Within one rule the faults are sorted by the identifier of the thing at fault.
    That is what lets the interface rank them and a test compare two lists directly.
    """
    first_reading = validate(graph)
    second_reading = validate(graph)

    assert first_reading == second_reading

    ranks = [_rank_of(fault.code) for fault in first_reading]
    assert ranks == sorted(ranks)
    for earlier, later in pairwise(first_reading):
        if _rank_of(earlier.code) == _rank_of(later.code):
            assert earlier.subject <= later.subject


@given(broken_graphs(*INDEPENDENTLY_BREAKABLE))
@many
def test_messages_never_contain_identifiers(graph: Graph) -> None:
    """A message names the claim by its words, never by its identifier.

    "Violation on link 01J8Z…" tells the user nothing. The identifier is already in
    `subject`, where the interface uses it to highlight the right wire.
    """
    identifiers = (
        {one.id for one in graph.propositions} | {one.id for one in graph.links} | {graph.id}
    )
    for fault in validate(graph):
        for identifier in identifiers:
            assert identifier not in fault.message


# --- A few faults that random maps will not produce on their own -----------


def test_a_map_whose_starting_claim_is_not_the_marked_one_is_refused(
    a_small_valid_graph: Graph,
) -> None:
    """The claim the map says it started from has to be the claim marked as the hypothesis."""
    other = next(one for one in a_small_valid_graph.propositions if one.kind != "hypothesis")
    mismatched = a_small_valid_graph.model_copy(update={"hypothesis_id": other.id})

    faults = validate(mismatched)

    assert [fault.code for fault in faults] == ["no_hypothesis"]
    assert "is not the one marked as the hypothesis" in faults[0].message


def test_an_arrow_with_neither_end_on_the_map_says_so(a_small_valid_graph: Graph) -> None:
    """An arrow joining two claims that do not exist cannot name either of them."""
    lost = a_small_valid_graph.links[0].model_copy(
        update={"id": "arrow-lost", "source": "nowhere-a", "target": "nowhere-b"}
    )
    with_lost_arrow = a_small_valid_graph.model_copy(
        update={"links": (*a_small_valid_graph.links, lost)}
    )

    faults = validate(with_lost_arrow)

    assert [fault.code for fault in faults] == ["dangling_link"]
    assert faults[0].message == "This arrow joins two claims, neither of which is on this map."


def test_an_arrow_from_a_claim_to_itself_is_a_loop(a_small_valid_graph: Graph) -> None:
    """A self-link is a loop of one, caught by the same pass.

    Which is why there is no separate code for it.
    """
    itself = a_small_valid_graph.links[0].model_copy(
        update={"id": "arrow-itself", "source": "claim-0", "target": "claim-0"}
    )
    with_self_link = a_small_valid_graph.model_copy(
        update={"links": (*a_small_valid_graph.links, itself)}
    )

    faults = validate(with_self_link)

    assert [fault.code for fault in faults] == ["cycle"]
    assert faults[0].subject == "arrow-itself"


def test_a_long_claim_is_trimmed_in_the_message(a_small_valid_graph: Graph) -> None:
    """A claim running past about eighty characters is trimmed, so the sentence stays readable."""
    wordy = a_small_valid_graph.propositions[0].model_copy(
        update={
            "claim": "A very long claim indeed, " * 10,
            "resolution": a_small_valid_graph.propositions[0].resolution.model_copy(
                update={"criteria": "  "}
            ),
        }
    )
    with_wordy_claim = a_small_valid_graph.model_copy(
        update={
            "propositions": tuple(
                wordy if one.id == wordy.id else one for one in a_small_valid_graph.propositions
            )
        }
    )

    faults = validate(with_wordy_claim)

    assert [fault.code for fault in faults] == ["missing_resolution"]
    assert "…" in faults[0].message
    assert len(faults[0].message) < 200


# --- The three guarantees, over generated things rather than examples ------


def _every_model_inside(graph: Graph) -> list[BaseModel]:
    """List every object on a map, so a test can walk all of them."""
    found: list[BaseModel] = [graph]
    for proposition in graph.propositions:
        found.extend([proposition, proposition.resolution, proposition.prior, proposition.beliefs])
        found.extend(one for one in (proposition.beliefs.model,) if one is not None)
        found.extend(one for one in (proposition.beliefs.user, proposition.beliefs.market) if one)
        if proposition.base_rate is not None:
            found.append(proposition.base_rate)
        if proposition.payoff is not None:
            found.append(proposition.payoff)
        found.extend(proposition.evidence)
    for link in graph.links:
        found.append(link)
        found.extend(link.sources)
    return found


@given(st.data())
@many
def test_generated_models_round_trip_json(data: st.DataObject) -> None:
    """Every object on a generated map, and every fault about a broken one, survives a round trip.

    The objects come from a valid map, because a map damaged by bypassing the
    classes holds a likelihood those classes would refuse to read back — which is
    the rule working, not a round trip failing. The faults come from a damaged map,
    because a valid one produces none.
    """
    for one in _every_model_inside(data.draw(graphs())):
        assert type(one).model_validate_json(one.model_dump_json()) == one

    damaged = data.draw(broken_graphs(*INDEPENDENTLY_BREAKABLE))
    faults = validate(damaged)
    assert faults
    for fault in faults:
        assert Violation.model_validate_json(fault.model_dump_json()) == fault


@given(graphs())
@many
def test_generated_models_are_frozen(graph: Graph) -> None:
    """Nothing on a generated map can be changed after it is built.

    Collections are tuples for the same reason: a frozen object holding a list is
    only half frozen.
    """
    for one in _every_model_inside(graph):
        first_field = next(iter(type(one).model_fields))
        try:
            setattr(one, first_field, "anything at all")
        except ValidationError:
            continue
        raise AssertionError(f"{type(one).__name__} let a field be written to")

    assert isinstance(graph.propositions, tuple)
    assert isinstance(graph.links, tuple)


@given(st.data())
@many
def test_intervention_round_trip(data: st.DataObject) -> None:
    """An edit survives a round trip and comes back as its own class, not a near neighbour."""
    graph = data.draw(graphs())
    edit = data.draw(interventions(graph))
    reader: TypeAdapter[Intervention] = TypeAdapter(Intervention)

    read_back = reader.validate_json(reader.dump_json(edit))

    assert read_back == edit
    assert type(read_back) is type(edit)


@given(st.data())
@many
def test_branch_round_trip(data: st.DataObject) -> None:
    """A branch survives a round trip, with every edit restored to its own class by its `kind`."""
    graph = data.draw(graphs())
    branch = data.draw(branches(graph))

    read_back = type(branch).model_validate_json(branch.model_dump_json())

    assert read_back == branch
    assert [type(one) for one in read_back.interventions] == [
        type(one) for one in branch.interventions
    ]


@given(raw_belief_fields())
@a_great_many
def test_belief_bounds_at_construction_over_raw_fields(
    raw: tuple[float, float, float, str],
) -> None:
    """Three arbitrary numbers either make a sensible likelihood or make none at all.

    There is no third outcome, and nothing is quietly clamped to fit. The numbers
    drawn here include the ones that are not numbers at all — "not a number" and the
    infinities — which is exactly the case a silent clamp would swallow.
    """
    likelihood, bottom, top, owner = raw
    try:
        built = Belief(p=likelihood, lo=bottom, hi=top, owner=owner)  # type: ignore[arg-type]
    except ValidationError:
        return
    assert 0.0 <= built.lo <= built.p <= built.hi <= 1.0


@given(seeds())
@many
def test_seeds_are_whole_numbers(seed: int) -> None:
    """A seed is a plain whole number; what matters is that the same one replays the same world."""
    assert isinstance(seed, int)
    assert seed >= 0
