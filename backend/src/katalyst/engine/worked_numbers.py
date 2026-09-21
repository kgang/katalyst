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
numbers print twice, once as the screen prints them and once at six decimal
places, and the section preamble says why six.

What this program must never do
-------------------------------
- Never write a number of its own. Every figure here is read off a world, a
  difference or the fixture; none is worked out in this file.
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

import sys
from collections.abc import Sequence
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

DIGITS = 6
"""How many decimal places the full-precision column prints.

**Not sixteen, and that is a decision rather than a shortcut.** The engine's
arithmetic runs through `numpy`, whose exponential and logarithm are accurate to
well under one unit in the last place but are *not* promised to be identical
across processor families — and the build runs on Linux on Intel while this is
often written on a Mac on Arm. Sixteen digits would therefore make the build fail
for a reason nobody changed. Six decimal places is finer than anything this
product shows by four orders of magnitude, and it is coarser than any difference
those two machines can produce by ten, so it is both useful and stable.

It is also the honest answer to what `README.md` used to print. Sixteen digits is
a promise to a reader that the seventeenth would match too, and it would not.
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


def _line(name: str, screen: str, full: str = "") -> str:
    """Lay one fact out as a line: its stable name, how it prints, and its digits.

    Args:
        name: The stable name a chapter cites, such as `B · base · reading`.
        screen: The value as a reader would see it, or a word, or `—` when the
            product has no way of printing this kind of number yet.
        full: The same value to six decimal places, where it is a number.

    Returns:
        One line, with no trailing spaces so that no editor can produce a diff by
        tidying the file, and never with two columns run together: a name longer
        than the column still keeps two spaces after it.
    """
    padded = f"{name:<{NAME_WIDTH}}" if len(name) < NAME_WIDTH else f"{name}  "
    return f"{padded}{screen:<{SCREEN_WIDTH}}{full}".rstrip()


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
        The number to six decimal places, or `—`.
    """
    return NOTHING if value is None else f"{value:.{DIGITS}f}"


def _chip(belief: Belief) -> tuple[str, str]:
    """Write a belief both ways: as the tile shows it, and at full precision.

    Args:
        belief: The likelihood with the range around it.

    Returns:
        The chip as a reader sees it, and its three numbers at six decimal places.
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
    """
    if value is None:
        return NOTHING, NOTHING
    claim = next(one for one in world.graph.propositions if one.id == claim_id)
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
        _line("run · seed", str(SEED)),
        _line("run · versions of the map", f"{VERSIONS:,}"),
        _line("run · worlds per version", str(WORLDS)),
        _line("run · day zero", str(FIXTURE_DATE)),
    ]

    stated: list[str] = []
    for claim in claims:
        stated.append(_line(f"{claim.id} · kind", claim.kind))
        stated.append(_line(f"{claim.id} · prior", *_chip(claim.prior)))
        stated.append(
            _line(
                f"{claim.id} · resolve by",
                str(claim.resolution.by),
                f"day {_days_out(claim.resolution.by)}",
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
                _line(f"{claim.id} · base rate", f"{claim.base_rate.k} of {claim.base_rate.n}")
            )

    # `reflexive` is written only on the one arrow that carries it — the market
    # feeding back on the world it is measuring — because that is how the fixture
    # reads and because ten lines saying "not reflexive" are ten lines of noise in
    # a file whose whole job is to make a difference easy to see.
    drawn = [
        _line(
            f"{arrow.id} · arrow",
            f"{arrow.source} → {arrow.target}",
            " · ".join(
                (
                    arrow.mode,
                    arrow.shape,
                    f"strength {arrow.strength:+.1f}",
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
        edits.append(_line(f"{branch.id} · what it is called", branch.label))
        for position, edit in enumerate(branch.interventions, start=1):
            edits.append(_line(f"{branch.id} · edit {position}", _edit_in_words(edit)))

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
        lines.append(_line(f"{claim_id} · {name} · what happened", row.state))
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
        lines.append(_line(f"{under} place", str(place)))
        lines.append(_line(f"{under} day", str(row.at_day), f"day {_days_out(row.at_day)}"))
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
        One line per retraction, or one line saying there were none.
    """
    if not world.retractions:
        return [_line(f"{name} · suppositions that ended", "none")]
    return [
        _line(
            f"{one.target} · {name} · supposition ended",
            str(one.at),
            f"by {one.by_claim} · along {one.by_link} · edit {one.by + 1}",
        )
        for one in world.retractions
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
        summaries.append(_line(f"{name} · the sentence beside the list", answer.summary))
        said = " ".join(answer.warnings) if answer.warnings else "none"
        summaries.append(_line(f"{name} · warnings", said))
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
            "owed to not being sure of each claim's own stated prior.",
            bands,
        ),
    ]


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

Each line is one thing somebody would quote: a whole arrow, a whole belief chip,
or one number. A computed number is written twice — first as the product prints
it (two significant figures, with `<.01` and `>.99` standing in for the two claims
nobody here is entitled to make), then at six decimal places. Six, not sixteen,
because the arithmetic runs through numpy, whose exponential is accurate to well
under one unit in the last place but is not promised to be identical on an Intel
build machine and an Arm laptop. Sixteen digits would fail the build for a reason
nobody changed, and would promise a reader a seventeenth digit that does not
exist.

A `—` in the printed column means the product has no way of writing that kind of
number yet: a move, a share of a band, and how often the versions agreed are all
real quantities, and none of them is a likelihood.
"""


def text() -> str:
    """Work out every number and lay the whole file out, ready to be written.

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
    """Write the file, and say where it went.

    Args:
        arguments: What was on the command line. One path writes somewhere else,
            which is how a test reads what this program produces without touching
            the committed file. Nothing at all writes the committed file.

    Returns:
        0 when the file is written.

    Raises:
        ValueError: If the committed file's place cannot be found. Writing it
            somewhere else would leave the build calling it stale for ever while
            regenerating it changed nothing.
    """
    if arguments:
        where = Path(arguments[0])
    else:
        where = WHERE
        if not (CHECKOUT / "backend" / "src" / "katalyst").is_dir():
            raise ValueError(
                f"this file was read from {Path(__file__).resolve()}, which is not inside a "
                "checkout of Katalyst, so there is nowhere to put docs/worked-numbers.txt. "
                "Run it from the checkout, or name a path to write to."
            )
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(text(), encoding="utf-8", newline="\n")
    print(f"worked-numbers: wrote {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
