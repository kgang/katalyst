"""Folding a branch onto a map: what each edit does, and what it must never do.

A branch is a named, ordered list of edits sitting beside a map nobody touches.
This file is where that list is folded onto the map. It hands back two things:
the map the edits leave behind, and an ordered list of every value an edit fixed.

**Why two things rather than one.** A `do` or an `observe` fixes a claim's value,
and a claim has nowhere to record one. It deliberately never will: a fixed value
is a fact about a *world*, not about a claim, and writing it onto the claim would
make the same claim mean different things in different branches. So the fixed
values travel beside the map as `Assignment` records, and the pair — map plus
assignments — is also what a further fold takes, which is what keeps "apply two
branches in a row" and "apply the two joined" the same operation.

Four functions live here.

* `apply` folds one branch's edits onto a map, in order.
* `flatten` puts a chain of branches — a child, its parent, its parent's parent —
  into one ordered list of edits, the parent's first.
* `introduced_by` says which edit added each arrow, so a claim pushed back down
  can name the edit responsible.
* `affected_set` says which claims an edit is allowed to move, read from the
  shape of the map alone.

What this file must never do
----------------------------
- Never change the map it was given. Every model here is frozen and every edit
  builds a new map, so the original is still there for the next branch to use.
- Never raise because an edit does not fit the map. A claim that is not there, an
  identifier already in use, an arrow that does not exist, an edit this version
  cannot carry out: each comes back as a `Violation` with a plain sentence,
  exactly as a rejected proposal does.
- Never half-apply a branch. If one edit cannot be applied, the whole fold comes
  back as violations and no map at all.
- Never repair. Nothing here drops the arrow that would close a loop, renames an
  identifier that is taken, or quietly skips an edit it cannot make sense of.
- No clock, no network, no randomness. The same map and branch give the same
  answer every time.
"""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Literal

import networkx
from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.belief import Beliefs
from katalyst.domain.branch import Branch
from katalyst.domain.graph import Graph
from katalyst.domain.ids import BranchId, LinkId, PropositionId
from katalyst.domain.intervention import (
    Believe,
    Do,
    Insert,
    Intervention,
    Observe,
    Refine,
    Retune,
)
from katalyst.domain.proposition import Proposition

# `_quoted` and `_name_of` are borrowed from the file that decides whether a map
# is valid, so that a rejected *edit* names a claim in exactly the words a
# rejected *map* does. Two copies of that wording would drift apart, and the
# user would be reading two slightly different voices from one product.
from katalyst.domain.validity import Violation, _name_of, _quoted, validate


class Assignment(BaseModel):
    """One value an edit fixed: which claim, to what, from which day, and which edit did it.

    A `do` and an `observe` both fix a claim's value, and this is where that fact
    lives. It is never written onto the claim itself, because the same claim has
    to mean the same thing in every branch — a fixed value belongs to the world
    the branch builds, not to the map the branch was built from.

    Frozen, like everything in this layer. A later assignment on the same claim is
    appended rather than replacing the earlier one, so the record still reads
    "supposed on the 1st, then reported on the 3rd" instead of silently showing
    only the last word on the subject.
    """

    model_config = ConfigDict(frozen=True)

    target: PropositionId = Field(description="The claim whose value this edit fixed.")
    value: bool = Field(
        description="What it was fixed to: true if the claim holds, false if it does not."
    )
    at: date | None = Field(
        default=None,
        description=(
            "The day the value holds from. Arrows out of the claim measure their delay "
            "from this day. None means the first day of the window the map is worked "
            "through on — an `observe` always says None, because it carries no date."
        ),
    )
    by: int = Field(
        ge=0,
        description=(
            "Which edit fixed it, as its position in the branch, counting from 0. This is "
            "what lets a claim say which edit moved it."
        ),
    )
    kind: Literal["do", "observe"] = Field(
        description=(
            "Which verb the user chose. 'do' is supposing a claim true and cutting it "
            "loose from its causes; 'observe' is reporting that it happened and leaving "
            "its causes connected. The two are never merged."
        )
    )


Applied = tuple[Graph, tuple[Assignment, ...]]
"""What a fold gives back when every edit applied: the map, and the values fixed.

Written down once because several functions here return it. The map is the one
the edits leave behind; the assignments are in the order the edits were made.
"""


def apply(
    graph: Graph,
    branch: Branch,
    assignments: tuple[Assignment, ...] = (),
) -> tuple[Graph, tuple[Assignment, ...]] | list[Violation]:
    """Fold a branch's edits onto a map, in order, and say what they left behind.

    Pure: no clock, no network, no randomness. The same map and branch give the
    same answer every time, which is what makes a world replayable.

    What each of the six edits does. `do` removes every arrow that points at the
    claim **and is on the map at this moment** — a supposition that starts on a
    day, never a seal against whatever is added afterwards — and records the value
    it fixed. `observe` removes nothing and records the value it fixed. `insert`
    adds a claim and the arrows that attach it. `retune` replaces one arrow's
    push and nothing else about it. `believe` writes the user's own likelihood on
    one claim and nothing else, anywhere. `refine` — splitting a claim into finer
    claims — is not built yet and comes back as a violation saying so.

    This function folds the edits of the branch it is given and never follows that
    branch's parent. Put a chain of branches in order with `flatten` first.

    An edit that does not fit the map ends the fold: everything wrong with that
    one edit comes back as a list of violations, and no map comes back at all.
    The edits after it are not checked, because they would be checked against a
    map that never existed, and a complaint about a map nobody made is a complaint
    the user cannot act on.

    Args:
        graph: The map to fold onto. It is never changed.
        branch: The branch whose edits are folded, in the order they were made.
        assignments: What an earlier fold fixed, when this fold continues from
            one. The values come back out at the front of the returned list, and
            the positions of the new edits carry on from one past the largest
            position already recorded — see `_next_position` for exactly what that
            means and where it is and is not the same as folding the whole branch
            at once.

    Returns:
        The map the edits left behind and every value they fixed, or a list of
        violations saying why the branch was refused. Never both, and never a map
        with only some of the edits on it.
    """
    folded = graph
    fixed: list[Assignment] = list(assignments)
    first_position = _next_position(assignments)

    for step, edit in enumerate(branch.interventions):
        outcome = _one_edit(folded, edit, first_position + step)
        if isinstance(outcome, list):
            return outcome
        folded, made = outcome
        fixed.extend(made)

    return folded, tuple(fixed)


def flatten(
    branches: Mapping[BranchId, Branch],
    branch_id: BranchId,
) -> tuple[Intervention, ...] | list[Violation]:
    """Put a chain of branches into one ordered list of edits, the parent's first.

    A child branch continues from its parent, so its world is built from the
    parent's edits followed by its own. This layer sees one branch at a time and
    never the collection, so the collection is handed in here and the chain is
    walked from the child up to the branch that forks off the untouched map.

    A chain that loops back on itself comes back as a violation rather than
    hanging. Storing branches so that a loop cannot be made in the first place
    belongs to whatever keeps them; this function only refuses to walk one.

    Args:
        branches: Every branch that might be on the chain, by identifier.
        branch_id: The branch whose edits are wanted, child end first.

    Returns:
        Every edit on the chain, the oldest ancestor's first and the named
        branch's last, or a list of one violation saying why the chain could not
        be put in order.
    """
    chain: list[Branch] = []
    walked: set[BranchId] = set()
    here: BranchId | None = branch_id

    while here is not None:
        if here in walked:
            return [
                Violation(
                    code="edit_not_applicable",
                    subject=here,
                    message=(
                        f"The branch {_quoted(branches[here].label)} continues from itself, "
                        "round its own chain of parents, so there is no order to put its "
                        "edits in."
                    ),
                )
            ]
        found = branches.get(here)
        if found is None:
            return [_no_such_branch(here, chain)]
        walked.add(here)
        chain.append(found)
        here = found.parent

    edits: tuple[Intervention, ...] = ()
    for branch in reversed(chain):
        edits = (*edits, *branch.interventions)
    return edits


def introduced_by(edits: Branch | Sequence[Intervention]) -> Mapping[LinkId, int]:
    """Say which edit added each arrow, by that edit's position in the run of edits.

    Only an `insert` adds an arrow, so this reads the positions straight off the
    list. It exists because a claim that was supposed true and has since been
    pushed back down has to name the edit responsible — the badge reads *Retracted
    · Oct 2 · by "…"* — and the map the fold leaves behind does not record which
    edit put which arrow on it.

    It is a fact about a branch, not about a map, so it is computed here and
    handed to whatever needs it rather than being stored on an arrow. An arrow
    that was on the base map all along is simply absent from the answer: nothing
    added it during this branch.

    Args:
        edits: A branch, or the ordered run of edits `flatten` returns.

    Returns:
        The position, counting from zero, of the edit that added each arrow.
    """
    run = edits.interventions if isinstance(edits, Branch) else tuple(edits)
    return {
        arrow.id: position
        for position, edit in enumerate(run)
        if isinstance(edit, Insert)
        for arrow in edit.links
    }


def affected_set(graph: Graph, intervention: Intervention) -> frozenset[PropositionId]:
    """Say which claims an edit is allowed to move, from the shape of the map alone.

    One principle: an edit changes only what is still connected to its subject in
    the map the edit leaves behind. The six operations come out differently
    because they leave behind different maps — `do` cuts the arrows into its
    target, so only the target and what it causes are still connected to it, while
    `observe` cuts nothing, so what we learn travels back up into the causes and
    out again along everything they lead to.

    | Edit | The claims it may move |
    |---|---|
    | `do` | the target and its descendants |
    | `observe` | the target, its descendants, its ancestors, and those ancestors' descendants |
    | `insert` | the new claim and its descendants |
    | `retune` | the claim the arrow points at, and that claim's descendants |
    | `refine` | the finer claims that stand in for the target |
    | `believe` | the target alone — the user's own number is not pushed through the map |

    **Feedback arrows are set aside**, exactly as the map's loop check sets them
    aside. In this version a feedback arrow is carried as data and never worked
    through, so nothing an edit does can travel along one, and a claim reachable
    only through one provably cannot move. The two rules change together: the day
    the arithmetic unrolls a feedback arrow over time, it belongs back in here.

    This is a permission, not a prediction: it says what an edit is allowed to
    move, never what it did move. Asking the engine what it touched and calling
    that the answer would make the locality tests agree with the code they check.

    Args:
        graph: **The map the edit leaves behind** — what `apply` returned, not the
            map it started from. An `insert`'s new claim is only on the second of
            those, and its descendants cannot be read off the first.
        intervention: The edit.

    Returns:
        The identifiers of every claim the edit may move. Empty when the edit's
        subject is not on the map at all, because an edit that cannot be applied
        moves nothing.
    """
    if isinstance(intervention, Refine):
        return frozenset(one.id for one in intervention.into)

    walkable = _walkable(graph)
    subject = _subject_of(graph, intervention)
    if subject is None or subject not in walkable:
        return frozenset()
    if isinstance(intervention, Believe):
        return frozenset({subject})

    reached = {subject} | networkx.descendants(walkable, subject)
    if isinstance(intervention, Observe):
        for cause in networkx.ancestors(walkable, subject):
            reached |= {cause} | networkx.descendants(walkable, cause)
    return frozenset(reached)


# --- Counting the edits, so an assignment can name the one that fixed it ---


def _next_position(assignments: tuple[Assignment, ...]) -> int:
    """Say which position the next edit folded counts as.

    An assignment's `by` is the position of the edit that fixed it, counting from
    zero along the run of edits the fold has seen. Fold a whole branch in one call
    and those are exactly the positions the user sees in the branch panel, which
    is the only form the interface ever uses: `flatten` hands the whole chain over
    at once, precisely so that this is true.

    Feeding an earlier fold's assignments back in continues the count from one
    past the largest position already recorded. That is the most a list of
    assignments can say about how many edits came before it, because only `do` and
    `observe` record one. So splitting a fold in two continues the numbering
    exactly when the first half ended on a `do` or an `observe`, and otherwise the
    second half's positions count from the last value fixed rather than from the
    join. The map is the same either way; only the positions differ, which is why
    a branch is folded in one call wherever the numbers are shown to anybody.

    Args:
        assignments: What an earlier fold fixed, in order.

    Returns:
        The position the next edit is recorded under. Zero when nothing has been
        fixed yet.
    """
    return max((one.by for one in assignments), default=-1) + 1


# --- One edit at a time ----------------------------------------------------


def _one_edit(graph: Graph, edit: Intervention, position: int) -> Applied | list[Violation]:
    """Apply one edit to a map, or say why it cannot be applied.

    Args:
        graph: The map as the edits before this one left it.
        edit: The one edit to apply.
        position: Where this edit sits in the branch, counting from zero.

    Returns:
        The map this edit leaves behind and any value it fixed, or the list of
        everything wrong with this one edit.
    """
    if isinstance(edit, Do):
        return _suppose(graph, edit, position)
    if isinstance(edit, Observe):
        return _report(graph, edit, position)
    if isinstance(edit, Insert):
        return _add_claim(graph, edit)
    if isinstance(edit, Retune):
        return _change_push(graph, edit)
    if isinstance(edit, Refine):
        return _split_claim(graph, edit)
    return _record_user_number(graph, edit)


def _suppose(graph: Graph, edit: Do, position: int) -> Applied | list[Violation]:
    """Suppose a claim true or false, and cut it loose from whatever would have caused it.

    The cut reaches only the arrows pointing at the claim **at this moment**. An
    arrow added by a later edit is live and can push the claim back the other way:
    supposing a claim is a timed assertion — "this holds from the 1st" — and never
    a seal that lets the user's first edit silently veto their third.

    Args:
        graph: The map as the edits before this one left it.
        edit: The supposition.
        position: Where this edit sits in the branch, counting from zero.

    Returns:
        The map without the arrows that pointed at the claim, and the value fixed,
        or one violation if the claim is not on the map.
    """
    if not _has_claim(graph, edit.target):
        return [
            Violation(
                code="unknown_target",
                subject=edit.target,
                message=(
                    "This edit supposes a claim that is not on this map, so there is "
                    "nothing here to suppose."
                ),
            )
        ]
    kept = tuple(link for link in graph.links if link.target != edit.target)
    fixed = Assignment(target=edit.target, value=edit.value, at=edit.at, by=position, kind="do")
    return graph.model_copy(update={"links": kept}), (fixed,)


def _report(graph: Graph, edit: Observe, position: int) -> Applied | list[Violation]:
    """Record that a claim actually came true, or false, and change no arrow at all.

    This is news rather than a lever, so the claim's causes stay connected and what
    is learned may travel back up into them. Nothing about the map changes: the
    whole of an observation is the value it fixed.

    Args:
        graph: The map as the edits before this one left it.
        edit: The observation.
        position: Where this edit sits in the branch, counting from zero.

    Returns:
        The same map and the value fixed, or one violation if the claim is not on
        the map.
    """
    if not _has_claim(graph, edit.target):
        return [
            Violation(
                code="unknown_target",
                subject=edit.target,
                message="This edit reports a claim that is not on this map as having happened.",
            )
        ]
    fixed = Assignment(target=edit.target, value=edit.value, at=None, by=position, kind="observe")
    return graph, (fixed,)


def _add_claim(graph: Graph, edit: Insert) -> Applied | list[Violation]:
    """Add one claim and the arrows that attach it, or say why it cannot be added.

    Four things are checked, and every one of them that fails is reported, so a
    badly attached claim is not fixed one arrow per attempt. The claim's
    identifier must be free and each arrow's identifier must be free, including of
    the other arrows arriving with it — anything else is a `duplicate_id`. Each
    arrow must reach a claim that is on the map — otherwise `unknown_target` — and
    must name the new claim at one of its two ends, because an arrow between two
    claims that are already there is not part of adding this one and would move
    claims nowhere near it. And the map that results must
    still have no loops once the feedback arrows are set aside. A map that was
    already running round in circles refuses the edit too, because a map like that
    has no order to work its claims through and so no world to build.

    Nothing else about the resulting map is checked here. A newly added claim that
    forgets to say what you would trade is a fault in the *map*, reported when the
    map is checked, and rejecting it here would answer the user's edit with a
    complaint about something they can still fix in place.

    Args:
        graph: The map as the edits before this one left it.
        edit: The claim and its arrows.

    Returns:
        The map with the claim and its arrows added, and no value fixed, or every
        reason the claim could not be added.
    """
    known = {one.id: one for one in graph.propositions}
    faults: list[Violation] = []

    if edit.proposition.id in known:
        faults.append(
            Violation(
                code="duplicate_id",
                subject=edit.proposition.id,
                message=(
                    f"The claim {_quoted(edit.proposition.claim)} cannot be added: this map "
                    "already has a claim under that identifier."
                ),
            )
        )
    known[edit.proposition.id] = edit.proposition

    taken = {one.id for one in graph.links}
    for arrow in edit.links:
        ends = f"from {_name_of(known, arrow.source)} to {_name_of(known, arrow.target)}"
        if arrow.id in taken:
            faults.append(
                Violation(
                    code="duplicate_id",
                    subject=arrow.id,
                    message=(
                        f"The arrow {ends} cannot be added: this map already has an arrow "
                        "under that identifier."
                    ),
                )
            )
        taken.add(arrow.id)
        for end in (arrow.source, arrow.target):
            if end not in known:
                faults.append(
                    Violation(
                        code="unknown_target",
                        subject=end,
                        message=f"The arrow {ends} joins a claim that is not on this map.",
                    )
                )
        if edit.proposition.id not in (arrow.source, arrow.target):
            faults.append(
                Violation(
                    code="edit_not_applicable",
                    subject=edit.proposition.id,
                    message=(
                        f"The arrow {ends} does not name the claim this edit adds, so there "
                        "is nothing here to attach it to."
                    ),
                )
            )

    if faults:
        return faults

    added = graph.model_copy(
        update={
            "propositions": (*graph.propositions, edit.proposition),
            "links": (*graph.links, *edit.links),
        }
    )
    loops = [one for one in validate(added) if one.code == "cycle"]
    if loops:
        return loops
    return added, ()


def _change_push(graph: Graph, edit: Retune) -> Applied | list[Violation]:
    """Replace one arrow's push and nothing else about it.

    The arrow's mechanism, its delay, its shape, its half-life, its sources, its
    receipt and the two claims it joins are all untouched, and so is every other
    arrow and every claim. An arrow an earlier edit in the same branch added can
    be retuned like any other.

    Args:
        graph: The map as the edits before this one left it.
        edit: Which arrow, and its new push.

    Returns:
        The map with that one number changed and no value fixed, or one violation
        if the arrow is not on the map.
    """
    if not any(link.id == edit.link for link in graph.links):
        return [
            Violation(
                code="unknown_link",
                subject=edit.link,
                message="This edit changes the push on an arrow that is not on this map.",
            )
        ]
    changed = tuple(
        link.model_copy(update={"strength": edit.strength}) if link.id == edit.link else link
        for link in graph.links
    )
    return graph.model_copy(update={"links": changed}), ()


def _split_claim(graph: Graph, edit: Refine) -> list[Violation]:
    """Refuse to split a claim into finer claims, because splitting is not built yet.

    The shape of the edit exists so that nothing has to be retrofitted when the
    operation arrives, and the operation arrives with the stack that also decides
    what happens to the split claim's own arrows. Until then this is a refusal
    with a sentence, never a half-done split and never a silently dropped edit.

    Args:
        graph: The map as the edits before this one left it.
        edit: The claim to split, and the finer claims it would be split into.

    Returns:
        One violation, saying either that the claim is not on this map or that the
        finer claims it names cannot be put on one yet.
    """
    found = _claim(graph, edit.target)
    if found is None:
        return [
            Violation(
                code="unknown_target",
                subject=edit.target,
                message="This edit splits a claim that is not on this map.",
            )
        ]
    return [
        Violation(
            code="edit_not_applicable",
            subject=edit.target,
            message=(
                f"Splitting the claim {_quoted(found.claim)} into finer claims is not built "
                "yet, so this edit cannot be folded onto this map."
            ),
        )
    ]


def _record_user_number(graph: Graph, edit: Believe) -> Applied | list[Violation]:
    """Write the user's own likelihood on one claim, and touch nothing else anywhere.

    The model's number and the market's price on that claim stay exactly where
    they were, and no number downstream moves: the user's number sits beside the
    other two rather than being pushed through the map. The gap between the three
    is the thing the user is here to look at, so nothing ever averages them.

    Args:
        graph: The map as the edits before this one left it.
        edit: Which claim, and the user's likelihood for it.

    Returns:
        The map with one slot on one claim written, and no value fixed, or one
        violation if the claim is not on the map.
    """
    found = _claim(graph, edit.target)
    if found is None:
        return [
            Violation(
                code="unknown_target",
                subject=edit.target,
                message="This edit puts your own number on a claim that is not on this map.",
            )
        ]
    three = Beliefs(model=found.beliefs.model, user=edit.belief, market=found.beliefs.market)
    changed = found.model_copy(update={"beliefs": three})
    return (
        graph.model_copy(
            update={
                "propositions": tuple(
                    changed if one.id == edit.target else one for one in graph.propositions
                )
            }
        ),
        (),
    )


# --- Small things the six edits and the affected set both need -------------


def _claim(graph: Graph, identifier: PropositionId) -> Proposition | None:
    """Find one claim on a map by its identifier, or nothing if it is not there."""
    return next((one for one in graph.propositions if one.id == identifier), None)


def _has_claim(graph: Graph, identifier: PropositionId) -> bool:
    """Say whether a map has a claim under this identifier."""
    return any(one.id == identifier for one in graph.propositions)


def _no_such_branch(missing: BranchId, walked: list[Branch]) -> Violation:
    """Say that a chain of branches names one that is not here.

    Args:
        missing: The branch that could not be found.
        walked: The branches already walked, child end first. Empty when it was
            the branch originally asked for that is missing.

    Returns:
        One violation naming the branch that pointed at the missing one, by the
        name the user gave it.
    """
    if not walked:
        return Violation(
            code="edit_not_applicable",
            subject=missing,
            message=(
                "There is no branch stored under the name this world was asked for, so "
                "there are no edits to put in order."
            ),
        )
    return Violation(
        code="edit_not_applicable",
        subject=missing,
        message=(
            f"The branch {_quoted(walked[-1].label)} continues from a branch that is not "
            "here, so its edits cannot be put in order."
        ),
    )


def _walkable(graph: Graph) -> "networkx.DiGraph[PropositionId]":
    """Build the map as a plain directed graph, for asking what leads to what.

    Two kinds of arrow are left out, and they are exactly the two the loop check
    leaves out. A **feedback** arrow — a market changing the world it is measuring
    — is carried as data in this version and never worked through: nothing an edit
    does travels along one until a later stack unrolls them over time, so a claim
    reachable only through one provably cannot move, and saying otherwise would
    leave the product with nothing it can call untouched. An arrow with an end
    that is not on the map is left out too, because a claim that does not exist
    cannot move and inventing one here would widen the answer for no reason.

    This rule and the arithmetic change together: the day a feedback arrow is
    worked through, it belongs back in here.

    Args:
        graph: The map to read.

    Returns:
        A directed graph of the claims and the ordinary arrows between them.
    """
    walkable: networkx.DiGraph[PropositionId] = networkx.DiGraph()
    walkable.add_nodes_from(one.id for one in graph.propositions)
    present = {one.id for one in graph.propositions}
    for link in graph.links:
        if not link.reflexive and link.source in present and link.target in present:
            walkable.add_edge(link.source, link.target)
    return walkable


def _head_of(graph: Graph, link_id: LinkId) -> PropositionId | None:
    """Name the claim one arrow points at, or nothing if the arrow is not on the map."""
    return next((one.target for one in graph.links if one.id == link_id), None)


def _subject_of(graph: Graph, intervention: Intervention) -> PropositionId | None:
    """Name the claim an edit works from — the first claim that could possibly move.

    For four of the six that is the claim the edit names. For an `insert` it is
    the claim being added. For a `retune`, whose subject is an arrow rather than a
    claim, it is the claim that arrow points at, because that is the earliest
    thing a change to the arrow can reach.

    Args:
        graph: The map the edit leaves behind.
        intervention: The edit.

    Returns:
        The claim the edit works from, or nothing when the edit names an arrow
        that is not on the map.
    """
    if isinstance(intervention, Insert):
        return intervention.proposition.id
    if isinstance(intervention, Retune):
        return _head_of(graph, intervention.link)
    return intervention.target
