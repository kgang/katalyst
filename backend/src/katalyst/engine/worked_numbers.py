"""One file owns every number the worked example quotes, and this program writes it.

What this is for
----------------
The Strait of Hormuz map is the product's one worked example, and dozens of
numbers computed from it are quoted across the book in `spec/`, in
`ARCHITECTURE.md` and in `README.md`. Until now each of those numbers was
re-measured by hand whenever the engine changed, and some were always missed. So
there is one generated file — `docs/worked-numbers.txt` — that holds every one of
them with a stable name, and a chapter quotes a number only where that file is one
link away. The build regenerates it and fails when what is committed differs,
which is exactly what `types-fresh` already does for the browser's types.

The payoff arrives when the engine's arithmetic is replaced: every number moves at
once, and the diff of this one file is the complete, reviewable statement of what
moved.

How to read the file it writes
------------------------------
Two parts, labelled apart, and the distinction is the point:

* **INPUTS** — every number a person typed into
  `backend/src/katalyst/fixtures/hormuz.py`: each claim's stated prior and range,
  each arrow's strength, delay, shape, half-life and receipt, every date. These
  are stable. Quoting one in a chapter is safe, and a sweep that rewrites them is
  a sweep touching numbers that never needed touching.
* **COMPUTED** — every number the engine worked out from those inputs. Nobody
  typed one. These all move together the day the arithmetic changes.

Every line starts with a stable name — `B · base · reading` — so a chapter can
cite one line rather than restating a figure. A line holds one thing somebody
would quote: a whole arrow, or a whole belief chip, or one number. Computed
numbers print twice, once as the screen prints them and once at five decimal
places, and the section preamble says why five.

What this program must never do
-------------------------------
- Never work out an engine number of its own. Every likelihood, move, share and
  rank here is read off a world, a difference or the fixture. What this file does
  work out is bookkeeping a reader could do with a calendar: how many days after
  day zero a date falls, and what position a row sits at in a list.
- Never write its own copy of the two-figures rule. It imports the one the rules
  layer uses, so a number cannot read one way here and another way on screen.
- Never print a supposition's 1. A claim the branch supposed true reads exactly 1
  so that a chain multiplied together has a factor for it; the word *supposed*
  goes where the number would, here as everywhere else.
- Never print the date, the machine, the package versions or anything else about
  the run. The file has to be byte-identical on every machine that runs it, or
  the build check is noise.
- Never reach the network, and never need a key.
"""

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from katalyst.domain import (
    Belief,
    Branch,
    ClaimDiff,
    DeltaRow,
    Diff,
    Do,
    Insert,
    Intervention,
    Link,
    Observe,
    Proposition,
    World,
)

# The one rule for writing a likelihood on screen, imported rather than copied.
# It is a private name in the rules layer because nothing outside that layer had
# needed it before, and borrowing it is much the lesser evil: a second copy of
# the rule is how the same number starts reading two ways in one product. The day
# `diff.py` is touched for another reason, this is the line that asks for it to
# be made public.
from katalyst.domain.diff import _two_figures

# The one rule for writing how hard an arrow pushes, borrowed for the same reason
# and from the layer that owns the number.
from katalyst.domain.propagation import _push_as_written
from katalyst.engine.worlds import VERSIONS, WORLDS, build_world, conditional, difference
from katalyst.fixtures.hormuz import FIXTURE_DATE, HORMUZ, HORMUZ_THEN_STRIKE

SEED = 20261001
"""The seed the worked example is read at, everywhere it is read.

The same number the golden test and the `curl` example in `README.md` use. A
world is replayable from a map, a branch and this, so writing it down once here is
what makes every figure below reproducible.
"""

CHECKOUT = Path(__file__).resolve().parents[4]
"""The checkout this file was read out of: four directories up from here.

`src/katalyst/engine/…` sits inside `backend/`, which sits in the checkout. That
holds because the server is installed so that it runs from its own source rather
than from a copy — which is how `uv run` installs it and how every other task in
the `Makefile` already depends on it working. `main` says so out loud rather than
trusting it, because the way this would fail otherwise is by quietly writing the
file somewhere nobody looks, and then the build saying it is stale while
regenerating it changes nothing.
"""

WHERE = CHECKOUT / "docs" / "worked-numbers.txt"
"""The one file this writes: `docs/worked-numbers.txt`."""

DIGITS = 5
"""How many decimal places the full-precision column prints.

**This is a choice about reading, not about reproducibility.** Five places is
fine enough that nothing a reader could act on is hidden — the screen never shows
more than two significant figures, and the rules layer will not call a claim
*shifted* until it has moved by 0.005 — and coarse enough that a diff of this file
stays readable. Sixteen would be a promise to a reader that the seventeenth digit
matched too, which it does not.

**No number of digits makes a file reproducible, and it was a mistake to think so.**
An earlier version of this program printed six places and argued that six was far
enough from what two machines can disagree by. That measured the wrong thing. What
decides whether a printed digit survives is how close the number sits to a
**rounding boundary**, the halfway point where one more hair of movement tips the
last digit — and with a few hundred numbers and a boundary every hundred-thousandth,
some number will sit on a knife edge on some machine whatever digit count is
chosen. Printing fewer digits only moves the knife. The build proved it: five
places produced a byte-identical file on Linux and on a Mac on 2026-09-21, and the
check that went with it still went red, correctly, over a number that differed in
its eighth decimal place.

**So reproducibility comes from `--check`, which compares numbers as numbers.**
See `TOLERANCE`. What is measured and worth writing down: one step of the float32
grid the engine samples on is 5.96e-08, replacing `numpy.exp` with one returning
the next representable number up moves no number here further than that, and
nothing amplifies along the way. None of that depends on the two platforms
continuing to agree, and the check does not assume they will.
"""

NAME_WIDTH = 46
"""How wide the stable name at the start of a line is padded to.

Wide enough for the longest name this file writes, with room to spare. Generous
on purpose: a name that outgrew the column would push every other line's columns
along with it, and a diff of this file is supposed to be a list of numbers that
moved rather than a reformatting.
"""

SCREEN_WIDTH = 22
"""How wide the as-the-screen-prints-it column is padded to."""

NOTHING = "—"
"""What stands where a number would, when there is honestly no number to put there."""

BETWEEN = "–"  # noqa: RUF001 — an en dash, deliberately; see below.
"""What sits between the two ends of a range, so a band reads `.22` then this then `.50`.

An en dash rather than a hyphen, because an en dash is what the browser prints:
`printRange` in `frontend/src/components/BeliefChip.tsx`. A file whose whole job
is to hold the same number the screen shows may not spell it differently. The
linter flags the character as one a reader can mistake for a hyphen, which is
true, and is why it is named once here rather than typed wherever a range is
built.
"""


# --- Writing one line ------------------------------------------------------


def _line(name: str, printed: str, value: str) -> str:
    """Lay one fact out as a line, in the three fields every fact line has.

    The grammar, written down once because a program reads these lines back:
    a name, then two or more spaces, then the printed field, then two or more
    spaces, then the value field. No field is ever empty — `—` stands in — and no
    field ever contains two spaces in a row, so the three are always recoverable.
    `_read_line` is the other half of this, and a round-trip test holds them
    together over every line of the real file.

    Args:
        name: The stable name a chapter cites, such as `B · base · reading`.
        printed: What the product would put on screen for this fact — a belief
            chip, a `was → is` pair, the word *supposed*, the sentence beside a
            change list — or `—` when this fact is not something the product
            renders.
        value: The fact itself: the number at full precision, the date, the word,
            the state. This is the field a check compares.

    Returns:
        One line, with no trailing spaces, so that no editor can produce a diff by
        tidying the file, and never with two fields run together: a name longer
        than its column still keeps two spaces after it.
    """
    padded = f"{name:<{NAME_WIDTH}}" if len(name) < NAME_WIDTH else f"{name}  "
    printed_field = f"{printed:<{SCREEN_WIDTH}}" if len(printed) < SCREEN_WIDTH else f"{printed}  "
    return f"{padded}{printed_field}{value}".rstrip()


@dataclass(frozen=True)
class Fact:
    """One line of the file, pulled back apart into the three fields it was written from."""

    name: str
    """The stable name a chapter cites."""

    printed: str
    """What the product would show on screen, or `—`."""

    value: str
    """The fact itself — the number, the date, the word — which is what a check compares."""


def _read_line(text: str) -> Fact | None:
    """Pull one line of the file back apart, or say it is not a fact line at all.

    Args:
        text: One line of the file.

    Returns:
        The three fields, or nothing at all when the line is a heading, a blank, a
        rule, or a sentence of the explanation at the top.
    """
    if not text or text.startswith((" ", "-", "=", "*")):
        return None
    fields = re.split(r"  +", text.strip())
    if len(fields) != 3 or " · " not in fields[0]:
        return None
    return Fact(name=fields[0], printed=fields[1], value=fields[2])


def facts_in(text: str) -> list[Fact]:
    """Pull every fact line out of a whole file, in the order they appear.

    Args:
        text: The whole file.

    Returns:
        Every fact, in file order.
    """
    found = (_read_line(one) for one in text.splitlines())
    return [one for one in found if one is not None]


def _block(heading: str, lines: Sequence[str]) -> list[str]:
    """Put a run of lines under a heading, sorted by their names.

    Sorted, always, and by the line's own text: two runs of this program lay the
    same facts out in the same order whatever order they were worked out in, and
    whatever order this machine happens to iterate a mapping in.

    Args:
        heading: One line naming what the block holds.
        lines: The lines, in any order.

    Returns:
        The heading, a blank line, and the lines in order.
    """
    return [heading, "", *sorted(lines), ""]


def _digits(value: float | None) -> str:
    """Write a number at the file's own precision, or say there is none.

    Args:
        value: The number, or nothing at all.

    Returns:
        The number to `DIGITS` decimal places, or `—`.
    """
    return NOTHING if value is None else f"{value:.{DIGITS}f}"


def _chip(belief: Belief) -> tuple[str, str]:
    """Write a belief both ways: as the tile shows it, and at full precision.

    Args:
        belief: The likelihood with the range around it.

    Returns:
        The chip as a reader sees it, and its three numbers at full precision.
    """
    band = f"{_two_figures(belief.lo)}{BETWEEN}{_two_figures(belief.hi)}"
    return (
        f"{_two_figures(belief.p)} ({band})",
        f"{_digits(belief.p)} {_digits(belief.lo)} {_digits(belief.hi)}",
    )


def _in_days(count: float) -> str:
    """Write a number of days the way a person says it.

    Args:
        count: How many days.

    Returns:
        `1 day`, or `30 days`, with no trailing nought on a whole number.
    """
    return f"{count:g} day{'' if count == 1 else 's'}"


def _days_out(day: date) -> int:
    """Say how many days after the day the example is set on a date falls.

    Args:
        day: The date.

    Returns:
        The number of days from the example's own day zero.
    """
    return (day - FIXTURE_DATE).days


# --- Reading a world, without ever printing a supposition's 1 ---------------


def _reading_day(world: World, claim: Proposition) -> int:
    """Find where a claim's own resolve-by day sits among the days a world drew.

    Args:
        world: The world.
        claim: The claim, for the date it is judged on.

    Returns:
        The position of that day in the world's series.

    Raises:
        ValueError: If that day is not among them. A claim's own resolve-by day is
            always kept when a series is thinned, so this cannot happen — and if it
            ever does, it is a broken promise between two pieces of our own code
            and is said out loud rather than quietly rounded to the day next door.
    """
    day = min(max(0, (claim.resolution.by - world.day_zero).days), world.days)
    if day not in world.series_days:
        raise ValueError(
            f"the world drew no point for {claim.id} on day {day}, the day it is judged, "
            "so there is no reading to write down"
        )
    return world.series_days.index(day)


def _supposed(world: World, claim: Proposition) -> bool:
    """Say whether a supposition is holding on the day this claim is read.

    A claim somebody supposed true reads exactly 1, range and all. That 1 is there
    so a chain of claims multiplied together has a factor for it, and for nothing
    else: no surface may print it, and this file is a surface.

    Args:
        world: The world.
        claim: The claim.

    Returns:
        True when the claim's own resolve-by day falls inside a supposition.
    """
    return world.states[claim.id][_reading_day(world, claim)] == "supposed"


def _reading(world: World, claim: Proposition) -> tuple[str, str]:
    """Write what a claim reads in one world, on the day that claim is judged.

    Args:
        world: The world.
        claim: The claim.

    Returns:
        The chip and its digits — or the word *supposed* and no digits at all.
    """
    if _supposed(world, claim):
        return "supposed", NOTHING
    return _chip(world.beliefs[claim.id])


def _likelihood(world: World, claim_id: str, value: float | None) -> tuple[str, str]:
    """Write one likelihood a difference reported, honouring the supposition rule.

    Args:
        world: The world the number was read from.
        claim_id: Which claim.
        value: The likelihood, or nothing at all when there is none to report.

    Returns:
        How it prints and its digits.

    Raises:
        ValueError: If that claim is not on that world's map. A difference only
            reports claims from the two worlds it compared, so this is a broken
            promise between two pieces of our own code rather than a possibility.
    """
    if value is None:
        return NOTHING, NOTHING
    claim = next((one for one in world.graph.propositions if one.id == claim_id), None)
    if claim is None:
        raise ValueError(
            f"a difference reported a number for {claim_id}, which is not a claim on the "
            f"{world.branch_id or 'base'} world it was read from, so there is no day to read it on"
        )
    if _supposed(world, claim):
        return "supposed", NOTHING
    return _two_figures(value), _digits(value)


# --- The worlds this file is about -----------------------------------------


def _world(branch: Branch | None) -> World:
    """Build one world of the worked example at the seed and the shipped loop sizes.

    Args:
        branch: The branch to fold on, or nothing at all for the untouched map.

    Returns:
        The world.

    Raises:
        ValueError: If the branch was refused, or the example could not be found.
            Either means this program is asking for something that is not there,
            and it stops rather than writing a file with a hole in it.
    """
    built = build_world("hormuz", branch, SEED, versions=VERSIONS, worlds=WORLDS)
    if not isinstance(built, World):
        raise ValueError(f"the worked example could not be built from this branch: {built}")
    return built


def _difference(branch: Branch) -> Diff:
    """Compare the untouched map with one branch of it, both at the same seed.

    Args:
        branch: The branch to compare against the untouched map.

    Returns:
        What moved between the two worlds.

    Raises:
        ValueError: If either world could not be built.
    """
    answered = difference("hormuz", None, branch, SEED, versions=VERSIONS, worlds=WORLDS)
    if not isinstance(answered, Diff):
        raise ValueError(f"the two worlds could not be compared: {answered}")
    return answered


def _conditional(branch: Branch | None, arrow: Link) -> Belief:
    """Work out one arrow's own number: its target, with its source supposed true.

    Args:
        branch: The branch the arrow lives on, or nothing at all for the base map.
        arrow: The arrow.

    Returns:
        The likelihood of its target under that supposition.

    Raises:
        ValueError: If it could not be worked out.
    """
    answered = conditional("hormuz", branch, SEED, arrow.id, versions=VERSIONS, worlds=WORLDS)
    if not isinstance(answered, Belief):
        raise ValueError(f"the number on {arrow.id} could not be worked out: {answered}")
    return answered


OBSERVED_B = Branch(
    id="obs_b",
    label="Brent settled below $68",
    interventions=(Observe(target="B", value=True),),
)
"""*This happened* on Brent: the first of the two observations the chapters discuss.

Written here rather than in the fixture because the fixture ships the branches the
product offers, and this is a branch the book argues about rather than one a user
can press. It is an input all the same, and the file says so.
"""

OBSERVED_C = Branch(
    id="obs_c",
    label="the war-risk premium printed below 0.4%",
    interventions=(Observe(target="C", value=True),),
)
"""*This happened* on the insurance premium: the second observation the chapters discuss."""


BRANCHES = (HORMUZ_THEN_STRIKE, OBSERVED_B, OBSERVED_C)
"""Every branch this file reports on, in the order it reports on them."""

WORLD_NAMES = {
    None: "base",
    HORMUZ_THEN_STRIKE.id: "strike",
    OBSERVED_B.id: "observed B",
    OBSERVED_C.id: "observed C",
}
"""What each world is called in a line's stable name. Short, because it is cited."""


# --- The inputs -------------------------------------------------------------


def _edit_in_words(edit: Intervention) -> str:
    """Say what one edit of a branch does, in a few plain words.

    Args:
        edit: The edit.

    Returns:
        One short phrase.

    Raises:
        ValueError: If it is a kind of edit no branch in this file uses. Better to
            stop than to write a line that describes the wrong thing.
    """
    if isinstance(edit, Do):
        when = "from the day the example is set" if edit.at is None else f"from {edit.at}"
        return f"suppose {edit.target} {'true' if edit.value else 'false'} · {when}"
    if isinstance(edit, Observe):
        return f"observe {edit.target} {'true' if edit.value else 'false'}"
    if isinstance(edit, Insert):
        arrows = ", ".join(one.id for one in edit.links)
        return f"insert {edit.proposition.id} · with arrows {arrows}"
    raise ValueError(
        f"this file has no words for an edit of kind {type(edit).__name__}; "
        "add them rather than letting it go unreported"
    )


def _claims_in(worlds: Sequence[World]) -> list[Proposition]:
    """List every claim that appears on any of these worlds, once each, in name order.

    Args:
        worlds: The worlds.

    Returns:
        Every claim, sorted by its identifier.
    """
    found: dict[str, Proposition] = {}
    for world in worlds:
        for claim in world.graph.propositions:
            found.setdefault(claim.id, claim)
    return [found[one] for one in sorted(found)]


def _input_lines(claims: Sequence[Proposition], arrows: Sequence[Link]) -> list[str]:
    """Write down every number a person typed into the worked example.

    Args:
        claims: Every claim on the example, the branch's own included.
        arrows: Every arrow on it, the branch's own included.

    Returns:
        The whole INPUTS part of the file.
    """
    run = [
        _line("run · seed", NOTHING, str(SEED)),
        _line("run · versions of the map", NOTHING, f"{VERSIONS:,}"),
        _line("run · worlds per version", NOTHING, str(WORLDS)),
        _line("run · day zero", NOTHING, str(FIXTURE_DATE)),
    ]

    stated: list[str] = []
    for claim in claims:
        stated.append(_line(f"{claim.id} · kind", NOTHING, claim.kind))
        stated.append(_line(f"{claim.id} · prior", *_chip(claim.prior)))
        stated.append(
            _line(
                f"{claim.id} · resolve by",
                NOTHING,
                f"{claim.resolution.by} · day {_days_out(claim.resolution.by)}",
            )
        )
        if claim.beliefs.user is not None:
            stated.append(_line(f"{claim.id} · what the user thinks", *_chip(claim.beliefs.user)))
        if claim.beliefs.market is not None:
            stated.append(
                _line(f"{claim.id} · what the market prices", *_chip(claim.beliefs.market))
            )
        if claim.base_rate is not None:
            stated.append(
                _line(
                    f"{claim.id} · base rate",
                    NOTHING,
                    f"{claim.base_rate.k} of {claim.base_rate.n}",
                )
            )

    # `reflexive` is written only on the one arrow that carries it — the market
    # feeding back on the world it is measuring — because that is how the fixture
    # reads and because ten lines saying "not reflexive" are ten lines of noise in
    # a file whose whole job is to make a difference easy to see.
    drawn = [
        _line(
            f"{arrow.id} · arrow",
            NOTHING,
            " · ".join(
                (
                    f"{arrow.source} → {arrow.target}",
                    arrow.mode,
                    arrow.shape,
                    f"strength {_push_as_written(arrow.strength)}",
                    f"delay {_in_days(arrow.lag)}",
                    "half-life " + (_in_days(arrow.half_life) if arrow.half_life else NOTHING),
                    arrow.provenance,
                    *(("reflexive",) if arrow.reflexive else ()),
                )
            ),
        )
        for arrow in arrows
    ]

    edits: list[str] = []
    for branch in BRANCHES:
        edits.append(_line(f"{branch.id} · what it is called", NOTHING, branch.label))
        for position, edit in enumerate(branch.interventions, start=1):
            edits.append(_line(f"{branch.id} · edit {position}", NOTHING, _edit_in_words(edit)))

    return [
        *_block(
            "How the example is run. A world is replayable from a map, a branch and a seed.",
            run,
        ),
        *_block("What each claim was given before anything pushed on it.", stated),
        *_block(
            "What each arrow was given. A strength's sign says which way the arrow pushes\n"
            "the claim at its head toward coming true, never which way the world moves.",
            drawn,
        ),
        *_block(
            "The branches, and the edits each makes, in the order they are made. The\n"
            "strike branch ships with the example; the two observations are written in\n"
            "the program that wrote this file, because the book argues about them and no\n"
            "button offers them.",
            edits,
        ),
    ]


# --- The computed numbers ---------------------------------------------------


def _reading_lines(worlds: Sequence[tuple[str, World]]) -> list[str]:
    """Write every claim's reading in every world, on the day that claim is judged.

    Args:
        worlds: Each world with the short name its lines are filed under.

    Returns:
        One line per claim per world.
    """
    return [
        _line(f"{claim.id} · {name} · reading", *_reading(world, claim))
        for name, world in worlds
        for claim in sorted(world.graph.propositions, key=lambda one: one.id)
    ]


def _change_lines(name: str, answer: Diff, before: World, after: World) -> list[str]:
    """Write what one edit did to each claim: the word for it, the move, and how sure.

    Args:
        name: The short name this world's lines are filed under.
        answer: The difference between the untouched map and this branch.
        before: The untouched world, for the supposition rule.
        after: This branch's world, for the same.

    Returns:
        Five lines per claim.
    """
    lines: list[str] = []
    for claim_id in sorted(answer.claims):
        row: ClaimDiff = answer.claims[claim_id]
        was_screen, was_full = _likelihood(before, claim_id, row.before)
        now_screen, now_full = _likelihood(after, claim_id, row.after)
        lines.append(_line(f"{claim_id} · {name} · what happened", NOTHING, row.state))
        lines.append(
            _line(
                f"{claim_id} · {name} · was → is",
                f"{was_screen} → {now_screen}",
                f"{was_full} → {now_full}",
            )
        )
        lines.append(_line(f"{claim_id} · {name} · move", NOTHING, _digits(row.delta)))
        lines.append(
            _line(f"{claim_id} · {name} · same direction", NOTHING, _digits(row.agreement))
        )
        lines.append(
            _line(
                f"{claim_id} · {name} · moved only by reweighting",
                NOTHING,
                "yes" if row.moved_only_by_reweighting else "no",
            )
        )
    return lines


def _change_list_lines(name: str, rows: Sequence[DeltaRow]) -> list[str]:
    """Write the ranked list of endings the edit reached, keeping its order in the names.

    The place is part of each line's name rather than being the order the lines sit
    in, so that a claim's numbers stay findable under its own name when the ranking
    moves — and so that a ranking moving shows up in the diff as the number it is.

    Args:
        name: The short name this world's lines are filed under.
        rows: The change list, already in the order the product shows it.

    Returns:
        Seven lines per row.
    """
    lines: list[str] = []
    for place, row in enumerate(rows, start=1):
        under = f"{row.target} · {name} · change list"
        lines.append(_line(f"{under} place", NOTHING, str(place)))
        lines.append(_line(f"{under} day", NOTHING, f"{row.at_day} · day {_days_out(row.at_day)}"))
        lines.append(
            _line(
                f"{under} was → is",
                f"{_two_figures(row.before)} → {_two_figures(row.after)}",
                f"{_digits(row.before)} → {_digits(row.after)}",
            )
        )
        lines.append(_line(f"{under} biggest move", NOTHING, _digits(row.peak_delta)))
        lines.append(_line(f"{under} band width", NOTHING, _digits(row.range_width)))
        lines.append(_line(f"{under} same direction", NOTHING, _digits(row.agreement)))
        lines.append(_line(f"{under} rank", NOTHING, _digits(row.rank)))
    return lines


def _retraction_lines(name: str, world: World) -> list[str]:
    """Write every supposition a later edit undermined, and what undermined it.

    Args:
        name: The short name this world's lines are filed under.
        world: The world.

    Returns:
        A line saying how many there were, always, and then one line per
        retraction. The counting line is there even when the count is none, so
        that a chapter citing it keeps its link whichever way the number goes —
        a name that exists only in one of two cases is a name that breaks.
    """
    return [
        _line(f"{name} · suppositions that ended", NOTHING, str(len(world.retractions))),
        *(
            _line(
                f"{one.target} · {name} · supposition ended",
                NOTHING,
                f"{one.at} · by {one.by_claim} · along {one.by_link} · edit {one.by + 1}",
            )
            for one in world.retractions
        ),
    ]


def _computed_lines(
    worlds: Sequence[tuple[str, World]],
    answers: Sequence[tuple[str, Diff, World]],
    conditionals: Sequence[tuple[str, Link, Belief]],
    base: World,
) -> list[str]:
    """Write down every number the engine worked out from the inputs above.

    Args:
        worlds: Each world with the short name its lines are filed under.
        answers: Each difference from the untouched map, with its name and its world.
        conditionals: Each arrow with the world it lives on and its own number.
        base: The untouched world, whose bands the last block takes apart.

    Returns:
        The whole COMPUTED part of the file.
    """
    summaries: list[str] = []
    changes: list[str] = []
    ranked: list[str] = []
    ended: list[str] = []
    for name, answer, after in answers:
        # The sentence is a rendering, so it goes in the printed field: a check
        # reads its words and leaves its two-figure numbers alone, because those
        # are rounded and a machine that disagrees in the last bit may round one
        # the other way. Every quantity it mentions is owned in full precision by
        # a line of its own — the before and after and the day by this world's
        # change list, and the count of untouched claims by the line below, which
        # is here so that nothing the sentence says goes unchecked.
        summaries.append(_line(f"{name} · the sentence beside the list", answer.summary, NOTHING))
        untouched = sum(1 for one in answer.claims.values() if one.state == "unchanged")
        summaries.append(_line(f"{name} · claims the edit left unchanged", NOTHING, str(untouched)))
        said = " ".join(answer.warnings) if answer.warnings else "none"
        summaries.append(_line(f"{name} · warnings", NOTHING, said))
        changes += _change_lines(name, answer, base, after)
        ranked += _change_list_lines(name, answer.rows)
        ended += _retraction_lines(name, after)

    arrows = [
        _line(f"{arrow.id} · {name} · conditional", *_chip(belief))
        for name, arrow, belief in conditionals
    ]

    bands = [
        _line(f"{target} · base · band from {source}", NOTHING, _digits(share))
        for target in sorted(base.range_shares)
        for source, share in sorted(base.range_shares[target].items())
    ]

    return [
        *_block(
            "What each claim reads, in each world, on the day that claim is judged. A\n"
            "claim a branch supposed true reads the word, never the 1 behind it.",
            _reading_lines(worlds),
        ),
        *_block("What each edit did to each claim, against the untouched map.", changes),
        *_block(
            "The endings each edit reached, ranked the way the product ranks them. The\n"
            "place is part of the name, so a ranking that moves shows up as a number\n"
            "rather than as a block of lines shuffling.",
            ranked,
        ),
        *_block("The one sentence the product writes beside each list.", summaries),
        *_block(
            "Suppositions a later edit undermined: the day the cause became true, never\n"
            "that day plus the arrow's delay.",
            ended,
        ),
        *_block(
            "The number on each arrow: its target, with its source supposed true — never\n"
            "how often the two show up together. Each arrow appears once, on the world\n"
            "where it exists.",
            arrows,
        ),
        *_block(
            "Where each claim's band comes from, on the untouched map: the share of it\n"
            "owed to not being sure of each claim's own stated prior. A claim's shares\n"
            "do not add up to one, and are not meant to — they are the engine's own\n"
            "quantity, and it reports them near one rather than at it.",
            bands,
        ),
    ]


# --- Comparing a fresh run with the file that is committed ------------------


TOLERANCE = 2e-5
"""How far two numbers may differ and still count as the same number.

**Stale must mean a number moved, not that a machine's last bit differed.** The
first version of this check compared the file character for character, and the
build went red on Linux for a number that differs from the one this machine
computes in its eighth decimal place. With around 280 numbers and a rounding
boundary every hundred-thousandth, some number will always sit on a knife edge on
some machine; printing fewer digits only moves the knife. So numbers are compared
as numbers, with room, and everything else is compared exactly.

**Why this size.** It has to clear two things and stay under a third.

* It must clear the rounding in the file itself. The file stores five decimal
  places and this check compares what it stores against a freshly computed number
  at full precision, so the two honestly differ by up to half a printed step,
  5e-06. Anything at or below that would fail on every run.
* It must clear what two machines disagree by. Measured: replacing `numpy.exp`
  with one that returns the next representable number up moved no number here by
  more than one step of the engine's float32 grid, 5.96e-08, and nothing
  amplified along the way. This is 336 times that.
* It must stay well under any difference a reader could act on. The rules layer
  will not even call a claim *shifted* until it has moved by 0.005, which is 250
  times this; the finest step this product ever shows on screen is 0.001, which is
  50 times it. Nothing a person could see can hide underneath.

Two printed steps is the round number in that window, and it is the one the file
uses.
"""

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
"""A date, matched before any number so that it is compared as one exact thing."""

_NUMBER = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
"""A number, with the thousands commas the file writes into the loop sizes."""

_ANY_FIGURE = re.compile(r"\d[\d,.:-]*")
"""Any run of figures, for blanking out the numbers inside something rounded."""


def _pieces(text: str) -> list[str | float]:
    """Split one field into the words it is made of and the numbers inside it.

    Args:
        text: One field of a line.

    Returns:
        Its pieces in order: text as text, numbers as numbers. A date stays part
        of the text around it, because a date is exact and there is no such thing
        as a date being nearly right.
    """
    out: list[str | float] = []
    literal = ""
    at = 0
    while at < len(text):
        found_date = _DATE.match(text, at)
        if found_date:
            literal += found_date.group()
            at = found_date.end()
            continue
        found_number = _NUMBER.match(text, at)
        if found_number:
            if literal:
                out.append(literal)
                literal = ""
            out.append(float(found_number.group().replace(",", "")))
            at = found_number.end()
            continue
        literal += text[at]
        at += 1
    if literal:
        out.append(literal)
    return out


def _without_figures(text: str) -> str:
    """Blank out every figure, leaving the words around them.

    What the printed field is compared on. That field holds a rounded rendering —
    a belief chip, a `was → is` pair, the sentence beside a change list — and a
    rounded rendering is not a fact about the world, it is a fact about the
    rounding. Two machines that agree about a number to eight decimal places can
    still round it two ways, and neither is wrong. So the words are compared and
    the figures are not; the numbers behind them are compared, at full precision,
    on the lines that own them.

    Args:
        text: The printed field.

    Returns:
        The same text with every run of figures replaced by a hash.
    """
    return _ANY_FIGURE.sub("#", text)


def _value_differences(name: str, fresh: str, committed: str) -> list[str]:
    """Compare one fact's value, exactly on its words and with room on its numbers.

    Args:
        name: The line's stable name, for saying which line moved.
        fresh: The value this run worked out.
        committed: The value the committed file holds.

    Returns:
        One plain sentence per difference, or nothing at all.
    """
    mine, theirs = _pieces(fresh), _pieces(committed)
    if len(mine) != len(theirs) or any(
        isinstance(one, float) != isinstance(two, float)
        for one, two in zip(mine, theirs, strict=True)
    ):
        return [f"{name} reads '{committed}' in the file and '{fresh}' now — a different shape."]

    said: list[str] = []
    for one, two in zip(mine, theirs, strict=True):
        if isinstance(one, float) and isinstance(two, float):
            if abs(one - two) > TOLERANCE:
                said.append(
                    f"{name} moved by {abs(one - two):.3g}: the file says {two:g}, "
                    f"this run says {one:g}."
                )
        elif one != two:
            said.append(f"{name} says '{two}' in the file and '{one}' now.")
    return said


def differences(fresh: Sequence[Fact], committed: Sequence[Fact]) -> list[str]:
    """Say, in plain sentences, every way a fresh run disagrees with the committed file.

    Three things are checked, and the third is the one that took a broken build to
    get right. The set of line names and their order must be identical. Every
    value must match word for word and number for number, numbers within
    `TOLERANCE`. The printed field is compared on its words alone, because it is
    a rounded rendering of a number that is checked elsewhere.

    Args:
        fresh: The facts this run worked out.
        committed: The facts the committed file holds.

    Returns:
        One sentence per disagreement, in file order, or nothing at all when the
        two agree.
    """
    mine = {one.name: one for one in fresh}
    theirs = {one.name: one for one in committed}

    said: list[str] = []
    for gone in [one.name for one in committed if one.name not in mine]:
        said.append(f"{gone} is in the file and this run does not produce it.")
    for added in [one.name for one in fresh if one.name not in theirs]:
        said.append(f"{added} is new: this run produces it and the file does not have it.")
    if not said and [one.name for one in fresh] != [one.name for one in committed]:
        said.append(
            "The lines are the same but their order is not, which would make every "
            "later diff of this file unreadable."
        )
    if said:
        return said

    for one in fresh:
        other = theirs[one.name]
        if _without_figures(one.printed) != _without_figures(other.printed):
            said.append(
                f"{one.name} is shown as '{other.printed}' in the file and '{one.printed}' "
                "now, and the difference is not just rounding."
            )
        said += _value_differences(one.name, one.value, other.value)
    return said


def faults_against(committed: str) -> list[str]:
    """Work every number out afresh and say how it disagrees with a file already written.

    Args:
        committed: The whole of the file to check against.

    Returns:
        One plain sentence per disagreement, or nothing at all.
    """
    return differences(facts_in(text()), facts_in(committed))


# --- Putting the file together ----------------------------------------------


HEADER = """\
Every number the Strait of Hormuz example quotes
================================================

Generated. Do not edit this file by hand — `make numbers` writes it, and the
build fails when what is committed differs from what the program prints. The
program is `backend/src/katalyst/engine/worked_numbers.py`; it runs the shipped
engine on the stored example at the example's own seed and the shipped loop
sizes, and reads nothing but what comes back.

**A chapter quotes a number only where this file is one link away.** Cite a line
by the name at its start — `B · base · reading` — rather than restating the
figure, so that the day the arithmetic changes there is one place to look and one
diff to review.

Two parts, and the difference between them matters:

  INPUTS     numbers a person typed, in backend/src/katalyst/fixtures/hormuz.py.
             Stable. Safe to quote. A sweep that rewrites these is touching
             numbers that never needed touching.
  COMPUTED   numbers the engine worked out from those. Nobody typed one. These
             all move together the day the arithmetic changes.

Every line has three fields: the name, then what the product would show on screen
for this fact, then the fact itself. A `—` in the middle field means the product
does not render this fact at all — a move, a share of a band and how often the
versions agreed are real quantities, and none of them is a likelihood.

Five decimal places is a choice about reading. The screen never shows more than
two significant figures, and the rules layer will not call a claim *shifted*
until it has moved by 0.005, so five places hides nothing anybody could act on
while keeping a diff of this file readable.

**The digits are not what makes this file reproducible.** `make numbers-check`
is. It works every number out afresh and compares numbers **as numbers**, with
room for the last-bit disagreement between one machine's maths library and
another's, and compares every word, date and state character for character. That
is why the middle field is not compared as text: a number two machines agree
about to eight decimal places can still round two ways, and neither is wrong.
Each such number is checked at full precision on the line that owns it.

A `—` in the printed column means the product has no way of writing that kind of
number yet: a move, a share of a band, and how often the versions agreed are all
real quantities, and none of them is a likelihood.
"""


def text() -> str:
    """Run the engine over the worked example and lay the whole file out.

    Returns:
        The file, ending in a newline.
    """
    base = _world(None)
    built = [(WORLD_NAMES[branch.id], _world(branch)) for branch in BRANCHES]
    worlds = [("base", base), *built]

    answers = [
        (WORLD_NAMES[branch.id], _difference(branch), world)
        for branch, (_, world) in zip(BRANCHES, built, strict=True)
    ]

    # Each arrow once, on the world where it exists: the base map's eight on the
    # untouched world, and the three the strike branch brings with it on that
    # branch. Working every arrow out in every world would be four numbers for
    # each one, and no chapter asks which.
    strike = next(one for one in BRANCHES if one.id == HORMUZ_THEN_STRIKE.id)
    strike_world = next(world for name, world in built if name == WORLD_NAMES[strike.id])
    base_arrows = {one.id for one in HORMUZ.links}
    conditionals = [("base", one, _conditional(None, one)) for one in HORMUZ.links]
    conditionals += [
        ("strike", one, _conditional(strike, one))
        for one in strike_world.graph.links
        if one.id not in base_arrows
    ]

    claims = _claims_in([world for _, world in worlds])
    arrows = [one for _, one, _ in conditionals]

    lines = [
        HEADER,
        "--- INPUTS: typed by a person, in backend/src/katalyst/fixtures/hormuz.py ---",
        "",
        *_input_lines(claims, arrows),
        "--- COMPUTED: worked out by the engine. Nobody typed one. ---",
        "",
        *_computed_lines(worlds, answers, conditionals, base),
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


def main(arguments: Sequence[str]) -> int:
    """Write the file, or check a written one against a fresh run.

    Two jobs, because they are two halves of one bargain: `make numbers` writes
    the file and a person reviews the diff, and `make numbers-check` is what the
    build runs to say the committed file still matches what the engine produces.

    Args:
        arguments: What was on the command line. `--check` compares instead of
            writing. A path names the file to write or to check, which is how a
            test works on a throwaway copy instead of the committed one; without
            one, both jobs use `docs/worked-numbers.txt`.

    Returns:
        0 when the file is written, or when a check finds nothing wrong. 1 when a
        check finds something.

    Raises:
        ValueError: If the committed file's place cannot be found. Working on some
            other file would leave the build calling this one stale for ever while
            regenerating it changed nothing.
    """
    checking = "--check" in arguments
    named = [one for one in arguments if one != "--check"]
    if named:
        where = Path(named[0])
    else:
        where = WHERE
        if not (CHECKOUT / "backend" / "src" / "katalyst").is_dir():
            raise ValueError(
                f"this file was read from {Path(__file__).resolve()}, which is not inside a "
                "checkout of Katalyst, so there is nowhere to put docs/worked-numbers.txt. "
                "Run it from the checkout, or name a path to write to."
            )

    if not checking:
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(text(), encoding="utf-8", newline="\n")
        print(f"worked-numbers: wrote {where}")
        return 0

    faults = faults_against(where.read_text(encoding="utf-8"))
    if not faults:
        print(f"worked-numbers: {where.name} still says what the engine says.")
        return 0
    print(f"worked-numbers: {where.name} is out of date. {len(faults)} things have moved:")
    for one in faults:
        print(f"  {one}")
    print(
        "\nRun `make numbers` and commit the result — the diff of that one file is "
        "the whole list of numbers that moved, and it is meant to be reviewed."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
