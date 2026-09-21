"""Playing a recorded generation back, so a reviewer with no key sees the real thing.

Somebody clones this repository, starts it, opens the browser — and has no reason
to spend money on a model key. Everything this prototype is judged on lives past
that point: a map drawing itself claim by claim, the rules refusing the model in
public, a step changed and the trades moving. **Replay puts all of it in front of
them**, through the same route, the same stream and the same canvas the live path
uses. The only substitution is where the bytes came from, and the screen says so.

The file is `backend/recordings/<example>.jsonl`: one JSON object per line, no
array and no commas, so it can be written a line at a time while a run is still
going and read as text in a diff. **Line one is the header; every line after it
is one event**, told apart by the `event` key the header does not have. An event
line carries exactly the two fields the wire carries, which is what makes "a
recording is the stream, line for line" literally true.

Two events are not re-emitted from the file
--------------------------------------------
**The receipt is rebuilt**, because a replay made no calls: zeroes throughout,
the header's date and prompt fingerprint, `mode: "replay"`, and the model copied
from the recorded one — a reader is entitled to know which model wrote this map.
The tally is zeroed all together; a receipt showing tokens with no dollars would
contradict its own price table.

**The likelihoods are recomputed, and therefore never stored.** The header
carries the seed and the accepted proposals carry the map, so the rules layer
does the rest and a recording holds no world at all. Store the numbers instead
and the day propagation changes, the demo shows numbers the engine no longer
produces and nothing goes red.

What this file must never do
----------------------------
- Never write a recording. `make record-demo` is the only writer, and a
  hand-edited file is a piece of state that traces to nobody.
- Never guess which recording to play. The match is the person's own sentence,
  exact after trimming: playing the Hormuz map back at somebody who asked about
  photonic chips is worse than saying no, and afterwards indistinguishable from
  the product working.
- Never let the pacing change an event, an order or a number. It is cosmetic.
- Never honour a seed from the request. The header's is the one the recorded run
  had, and the numbers are recomputed from it.
- Never raise at a file it cannot read. A recording outlives the code that wrote
  it, so meeting an old one is ordinary: it comes back as `CannotBeRead` with a
  sentence, and the good files beside it still play.
"""

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from katalyst.domain import Graph, Insert, Link, Proposition, propagate
from katalyst.engine import events
from katalyst.engine.events import (
    BeliefsPropagated,
    Event,
    GenerationStarted,
    ProposalAccepted,
    ProposalRejected,
    Receipt,
)
from katalyst.engine.outcome import WHAT_THE_SERVICE_DEFAULTS_TO
from katalyst.engine.verify import Verdict
from katalyst.settings import get_settings

RECORDINGS = Path(__file__).resolve().parents[3] / "recordings"
"""Where the committed recordings live when nothing says otherwise.

`backend/recordings/`. The settings can point somewhere else — which is what lets
a test, and the one browser test that drives both halves, run against a folder of
their own without touching the committed one.
"""


def where_they_live() -> Path:
    """Where this running program reads its recordings from.

    Read when asked rather than when this module was written, so that pointing a
    program at another folder is a setting and not a patch.

    Returns:
        The folder, from the settings when they name one and `backend/recordings/`
        when they do not.
    """
    said = get_settings().KATALYST_RECORDINGS
    return Path(said) if said else RECORDINGS


class RecordedInsert(BaseModel):
    """The single scripted "…but X happens" a keyless reviewer can make on this map."""

    model_config = ConfigDict(frozen=True)

    claim_in_words: str = Field(description="What the card offers, word for word.")
    answer: Insert = Field(
        description="The claim and its arrows, drafted live when the recording was made."
    )


class RecordingHeader(BaseModel):
    """The first line of a recording: everything that is true of the whole file.

    It must never carry a likelihood, a range or a world. Numbers are recomputed
    from the seed, and a number stored here could one day disagree with the engine
    that is running.
    """

    model_config = ConfigDict(frozen=True)

    base_id: str = Field(
        description=(
            "The identifier of the map this recording builds, minted when the "
            "recording was made. Emphatically not the word `hormuz`: the file is "
            "named for the launchpad card, and the map inside carries a minted "
            "identifier so it can never be confused with the hand-written stored "
            "example that already answers to that name."
        )
    )
    seed: int = Field(description="The one number the rules layer re-propagates with.")
    recording_date: date = Field(description="The day `make record-demo` wrote this file.")
    prompt_hash: str = Field(description="The fingerprint of the prompt the run was made against.")
    effort: str = Field(
        default=WHAT_THE_SERVICE_DEFAULTS_TO,
        description=(
            "How hard the model was asked to try when this was recorded, as a "
            "plain word. A recording is made **rich** — nothing sent, the "
            "service's own default — while a live run is made fast, so a reader "
            "watching a replay is entitled to know which of the two they are "
            "looking at (Kent, G13, 2026-09-21)."
        ),
    )
    insert: RecordedInsert = Field(
        description="The one scripted intervention this recording can answer."
    )


class RecordingSummary(BaseModel):
    """One recording the first screen can offer, when it was made, and what making it cost.

    The three figures are the **recorded run's own**, read off the receipt line
    inside the file and never worked out here. They are the only measured price
    and the only measured duration this product owns, so they are what the first
    screen prints beside a live run before anybody presses it — with the day they
    were measured, which is `recording_date`.

    They are absent together when the file holds no receipt this engine can read,
    and the screen then prints no figure at all rather than a guess.
    """

    model_config = ConfigDict(frozen=True)

    example: str = Field(description="The short name of the example, matching its file name.")
    recording_date: date = Field(description="The day `make record-demo` wrote it.")
    calls: int | None = Field(
        default=None,
        description=(
            "How many times the recorded run called a model. Absent when the file "
            "holds no receipt this engine can read."
        ),
    )
    seconds: float | None = Field(
        default=None,
        description=(
            "How long the recorded run took, wall clock, in seconds — the "
            "receipt's own field and its own unit, so nothing converts it on the "
            "way here. Absent when the file holds no readable receipt."
        ),
    )
    dollars: float | None = Field(
        default=None,
        description=(
            "What the recorded run cost, in United States dollars — the receipt's "
            "own field and its own unit. Absent when the file holds no readable "
            "receipt."
        ),
    )


class Recording(BaseModel):
    """One whole recorded generation: its header and its events, in order."""

    model_config = ConfigDict(frozen=True)

    example: str = Field(description="The short name of the example, from the file's own name.")
    header: RecordingHeader = Field(description="Everything true of the whole file.")
    lines: tuple[tuple[str, dict[str, Any]], ...] = Field(
        description="Every event after the header, as the name it travels under and its payload."
    )

    @property
    def hypothesis(self) -> str:
        """The sentence this recording was made from, read off its own first event."""
        return self._started("hypothesis")

    @property
    def target(self) -> str | None:
        """The place the run was asked whether it gets to, when it was asked one."""
        return self._started("target") or None

    def _started(self, field: str) -> str:
        """Read one field off this recording's own first event."""
        for name, payload in self.lines:
            if name == events.NAMES[GenerationStarted]:
                said = payload.get(field)
                return "" if said is None else str(said)
        return ""


class CannotBeRead(Exception):
    """This file is not a recording this engine can read, and says so in one sentence.

    A recording is a committed file that outlives the code that wrote it — that
    is the whole point of having them — so a file from an older engine, or from a
    newer one, or one somebody truncated, is an ordinary thing to meet and not an
    exceptional one. Every way of failing to read one stops here and crosses as
    this, with a sentence a person could act on: nothing above this file should
    have to know about JSON, about pydantic, or about which of them complained
    (Kent, 2026-09-20).
    """

    def __init__(self, why: str) -> None:
        """Hold the plain sentence of what could not be read."""
        super().__init__(why)
        self.why = why


def read(path: Path) -> Recording:
    """Read one recording off disk.

    Args:
        path: The file to read.

    Returns:
        Its header and its events, in the order they were written.

    Raises:
        CannotBeRead: If it is not a recording this engine can read, whatever the
            reason. The sentence names the file.
    """
    try:
        written = [one for one in path.read_text(encoding="utf-8").splitlines() if one.strip()]
        if not written:
            raise CannotBeRead(f"{path.name} is empty; a recording is a header and its events.")
        header = RecordingHeader.model_validate_json(written[0])
        lines: list[tuple[str, dict[str, Any]]] = []
        for line in written[1:]:
            said = json.loads(line)
            lines.append((str(said["event"]), dict(said["data"])))
    except CannotBeRead:
        raise
    except Exception as unreadable:
        raise CannotBeRead(
            f"{path.name} could not be read as a recording this engine understands. "
            "It was probably made by an older or a newer one; record it again."
        ) from unreadable
    return Recording(example=path.stem, header=header, lines=tuple(lines))


def why_it_cannot_be_played(recording: Recording) -> str | None:
    """Say, in one sentence, why this recording would not play through. Or nothing.

    **Reading a file and playing it are two different questions**, and readiness
    asks the second. A file whose header parses can still hold an event this
    engine does not know or a payload that does not fit one: it reads perfectly
    well and stops half way through playing. Offering a card for it promises
    something that will not happen (Kent, 2026-09-21).

    Args:
        recording: A recording that read.

    Returns:
        One plain sentence, or nothing at all when every event in it would play.
    """
    for name, payload in recording.lines:
        if name == events.NAMES[Receipt]:
            continue
        shape = events.BY_NAME.get(name)
        if shape is None:
            return (
                f"{recording.example} holds an event this engine does not know "
                f"({name}). It was probably made by a newer one; record it again."
            )
        try:
            shape.model_validate(payload)
        except ValidationError:
            return (
                f"{recording.example} holds a {name} this engine could not read. "
                "It was probably made by an older or a newer one; record it again."
            )
    return None


def readable(folder: Path | None = None) -> tuple[tuple[Recording, ...], tuple[str, ...]]:
    """Read every recording in a folder, and say which ones could not be read.

    **One bad file never takes the others with it.** Before this, a single
    recording from an older engine made the readiness route answer 500 and the
    first screen show nothing at all, though good recordings sat beside it — the
    keyless product blanked by a file it did not need (Kent, 2026-09-20).

    Args:
        folder: Where the recordings live. The committed folder when not said.

    **A file that reads but would not play through is not one of the good
    ones.** Readiness offers a card for each of these, and a card that fails half
    way through is worse than one that is not there (Kent, 2026-09-21).
    `find` is deliberately more forgiving: asked for a sentence it will hand back
    anything that reads, so the stream fails with that file's own precise
    sentence rather than with "no recording of that sentence", which would be a
    lie. Two questions, two answers.

    Returns:
        Every recording that read **and** would play, by file name, and one plain
        sentence per file that would not.
    """
    looking_in = where_they_live() if folder is None else folder
    if not looking_in.is_dir():
        return (), ()
    good: list[Recording] = []
    bad: list[str] = []
    for one in sorted(looking_in.glob("*.jsonl")):
        try:
            found = read(one)
        except CannotBeRead as unreadable:
            bad.append(unreadable.why)
            continue
        unplayable = why_it_cannot_be_played(found)
        if unplayable is None:
            good.append(found)
        else:
            bad.append(unplayable)
    return tuple(good), tuple(bad)


def every_recording(folder: Path | None = None) -> tuple[Recording, ...]:
    """Read every recording in a folder, in a fixed order.

    A folder with nothing in it gives nothing back, which is what lets the build's
    own check be green from the commit that adds it.

    Args:
        folder: Where the recordings live. The committed folder when not said.

    Returns:
        Every recording, by file name.
    """
    # Resolved when asked rather than when this function was written, so that
    # where the recordings live is a fact about the running program.
    #
    # **Everything that reads**, including a file that would stop part way
    # through playing: asked for a sentence, this hands back what it has so the
    # stream can fail with that file's own precise words rather than with "no
    # recording of that sentence", which would be a lie. `readable` answers the
    # other question — what a card may be offered for (Kent, 2026-09-21).
    looking_in = where_they_live() if folder is None else folder
    if not looking_in.is_dir():
        return ()
    found: list[Recording] = []
    for one in sorted(looking_in.glob("*.jsonl")):
        try:
            found.append(read(one))
        except CannotBeRead:
            continue
    return tuple(found)


def summary_of(recording: Recording) -> RecordingSummary:
    """Describe one recording the way the first screen needs it described.

    **One builder, used by everything that lists recordings**, because two of
    them would be two answers to "what does this example cost to run", and the
    difference would show up as a number on somebody's first screen.

    Args:
        recording: A recording that read.

    Returns:
        Its name, the day it was made, and what making it cost.
    """
    calls, seconds, dollars = _what_the_recorded_run_cost(recording)
    return RecordingSummary(
        example=recording.example,
        recording_date=recording.header.recording_date,
        calls=calls,
        seconds=seconds,
        dollars=dollars,
    )


def _what_the_recorded_run_cost(
    recording: Recording,
) -> tuple[int | None, float | None, float | None]:
    """Read the recorded run's own receipt: how many calls, how long, how much.

    **Read off the file, never worked out here.** These are the figures of the
    paid run this recording was made from, in the receipt's own fields and the
    receipt's own units, so a screen printing them is quoting a measurement
    rather than repeating a number somebody typed.

    The receipt is the one event `why_it_cannot_be_played` deliberately does not
    check, because a replay rebuilds it rather than emitting it — so a file that
    plays perfectly well can still carry a receipt this engine cannot read. That
    is an absence, not a fault: the three come back empty together and the screen
    says it was not told.

    Args:
        recording: The recording to read.

    Returns:
        The calls, the seconds and the dollars, or three absences.
    """
    for name, payload in reversed(recording.lines):
        if name != events.NAMES[Receipt]:
            continue
        try:
            said = Receipt.model_validate(payload)
        except ValidationError:
            return None, None, None
        return said.calls, said.seconds, said.dollars
    return None, None, None


def summaries(folder: Path | None = None) -> tuple[RecordingSummary, ...]:
    """List what this copy of the program can play back, and when each was made.

    Read by the first screen before anything runs, which is how the sentence
    record 0012 requires — *"No model key configured — these run from recordings
    made on <date>"* — can name a date at all: the date lives on the receipt, and
    the receipt arrives last. The same reason carries the three figures beside it:
    what a live run of this example costs and how long it takes has to be on
    screen **before** the press, and a receipt arrives long after.

    Args:
        folder: Where the recordings live. The committed folder when not said.

    Returns:
        One summary per recording, by file name.
    """
    good, _ = readable(folder)
    return tuple(summary_of(one) for one in good)


def find(hypothesis: str, folder: Path | None = None) -> Recording | None:
    """Find the recording made from this sentence, or nothing at all.

    **Matched on the sentence, exact after trimming surrounding spaces** — the
    same rule the scripted intervention uses, because one matching rule is easier
    to trust than two. Never a nearest match: playing one map back at somebody who
    asked about something else is worse than saying no, and afterwards it is
    indistinguishable from the product working.

    Args:
        hypothesis: The sentence the person typed.
        folder: Where the recordings live. The committed folder when not said.

    Returns:
        The one recording made from that sentence, or nothing at all.
    """
    wanted = hypothesis.strip()
    for one in every_recording(folder):
        if one.hypothesis.strip() == wanted:
            return one
    return None


def play(recording: Recording) -> Iterator[Event]:
    """Play one recording back as the events a live run would have emitted.

    Every event comes straight out of the file except the receipt, which is
    rebuilt to say that this run made no calls. The likelihoods are not in the
    file at all: `beliefs_of` recomputes them, and whoever writes the bytes out
    puts that event where the grammar requires.

    Args:
        recording: The recording to play.

    Yields:
        The events, in the order the file holds them.
    """
    for name, payload in recording.lines:
        if name == events.NAMES[Receipt]:
            yield _rebuilt(payload, recording)
            continue
        shape = events.BY_NAME.get(name)
        if shape is None:
            raise CannotBeRead(
                f"{recording.example} holds an event this engine does not know "
                f"({name}). It was probably made by a newer one; record it again."
            )
        try:
            yield shape.model_validate(payload)
        except ValidationError as did_not_fit:
            raise CannotBeRead(
                f"{recording.example} holds a {name} this engine could not read. "
                "It was probably made by an older or a newer one; record it again."
            ) from did_not_fit


def seconds_between() -> float:
    """How long to wait between two events of a replay.

    **One setting and no argument beside it.** Pacing is presentation and nothing
    else, which is why it is not a field on the request: a client that could ask
    for an instant replay would let anybody who opened the network tab skip the
    thing the recording exists to show. It is `KATALYST_REPLAY_PACE`, in seconds,
    read here — and a caller who wants no pause at all asks for a pace of zero,
    which is the same question with the same answer rather than a second switch.

    Returns:
        The seconds to wait between events. Zero means no wait at all.
    """
    return get_settings().KATALYST_REPLAY_PACE


def beliefs_of(
    recording: Recording, world_sizes: tuple[int, int], onto: Graph | None = None
) -> BeliefsPropagated:
    """Work every likelihood through the map this recording built.

    The one event a recording never stores. The header carries the seed, the
    accepted proposals carry the map, and the rules layer does the rest — so a
    replay and a live run end up running the identical map, branch and seed
    through the identical arithmetic.

    Args:
        recording: The recording whose map to work through.
        world_sizes: How many versions of the map to try, and how many worlds
            under each.

        onto: The map to work the numbers through, when the caller has one of
            its own — the recording's map with the reader's own likelihood
            stamped on it, which is an input rather than part of the file. The
            recording's own map when not said.

    Returns:
        The event, ready to be written out where the grammar puts it.
    """
    versions, worlds = world_sizes
    world = propagate(
        onto if onto is not None else map_of(recording),
        (),
        as_of=recording.header.recording_date,
        seed=recording.header.seed,
        versions=versions,
        worlds=worlds,
    )
    return BeliefsPropagated(world=world)


def map_of(recording: Recording) -> Graph:
    """Build the map this recording's accepted proposals left behind.

    Nothing is minted here: every identifier in the file was minted when the
    recording was made, and reading them back is what makes a replayed map the
    same map.

    Args:
        recording: The recording to read.

    Returns:
        The finished map, with the header's identifier on it.

    Raises:
        ValueError: If the recording holds no claim at all, which no committed
            file can.
    """
    claims: list[Proposition] = []
    arrows: list[Link] = []
    for name, payload in recording.lines:
        if name != events.NAMES[ProposalAccepted]:
            continue
        landed = ProposalAccepted.model_validate(payload)
        if landed.proposition is not None:
            claims.append(landed.proposition)
        arrows.extend(landed.links)
    if not claims:
        raise ValueError(f"{recording.example} holds no claim; there is no map to rebuild")
    return Graph(
        id=recording.header.base_id,
        propositions=tuple(claims),
        links=tuple(arrows),
        hypothesis_id=claims[0].id,
    )


def _rebuilt(recorded: dict[str, Any], recording: Recording) -> Receipt:
    """Rebuild a recorded receipt as the receipt of the replay that is running now.

    Args:
        recorded: The receipt the original run emitted.
        recording: The recording it came from, for its header.

    Returns:
        A receipt saying this run made no calls and cost nothing.
    """
    return Receipt(
        model=str(recorded.get("model", "")),
        calls=0,
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=0,
        searches=0,
        dollars=0.0,
        seconds=0.0,
        mode="replay",
        recording_date=recording.header.recording_date,
        # The effort the **recorded** run was made with, not this replay's: a
        # replay asks nothing of anybody, and what a reader wants to know is how
        # the map they are watching was made.
        effort=recording.header.effort,
        prompt_hash=recording.header.prompt_hash,
    )


THE_FOUR_EXAMPLES = ("export-controls", "hormuz", "midterms", "photonics")
"""The four names a recording may be called, which are the four cards' own.

A file called anything else is a file no card would ever play, so it is a fault
and not a mystery. `record.py` holds the same four beside the sentences they are
run from; this is the reading end of that list (2026-09-20).
"""


def _grammar_faults(recording: Recording, names: list[str]) -> list[str]:
    """Check the three things about a recording's shape that B9 asks for.

    The receipt second to last, the verdict where the grammar puts it, and the
    growth events numbered in a rising line. All three were written down in
    `replay.md` and checked by nothing (2026-09-20).

    Args:
        recording: The recording to check.
        names: Its event names, in order.

    Returns:
        One sentence per fault, or nothing at all.
    """
    found: list[str] = []
    if len(names) >= 2 and names[-2] != events.NAMES[Receipt]:
        found.append(
            f"{recording.example} does not put its receipt second to last, so a "
            "reader could reach the end without being told what it cost."
        )
    growth = (events.NAMES[ProposalAccepted], events.NAMES[ProposalRejected])
    if events.NAMES[Verdict] in names:
        where = names.index(events.NAMES[Verdict])
        if any(one in growth for one in names[where:]):
            found.append(
                f"{recording.example} goes on growing after its verdict, which "
                "grades a map that has stopped changing."
            )
    numbered: list[int] = []
    for name, payload in recording.lines:
        if name not in growth or "at" not in payload:
            continue
        try:
            numbered.append(int(payload["at"]))
        except (TypeError, ValueError):
            # A bad value is a fault to name. Reading it as a number one line
            # after the check above appended the right sentence turned this
            # whole report — every other file's included — into a traceback
            # (Kent, 2026-09-21).
            found.append(
                f"{recording.example} numbers a proposal {payload['at']!r}, which "
                "is not a number, so a reader cannot tell what order they arrived in."
            )
            return found
    if numbered != sorted(numbered) or len(set(numbered)) != len(numbered):
        found.append(
            f"{recording.example} numbers its proposals {numbered}, which is not a "
            "rising line, so a reader cannot tell what order they arrived in."
        )
    return found


def faults_in(recording: Recording, *, current_prompt_hash: str) -> list[str]:
    """List everything wrong with one recording, in plain sentences.

    What the build's own check reads. Every reason at once, never the first.

    Args:
        recording: The recording to check.
        current_prompt_hash: The fingerprint of the prompt shipping today.

    Returns:
        One sentence per fault, or nothing at all when the file is sound.
    """
    found: list[str] = []
    names = [name for name, _ in recording.lines]

    unknown = sorted({one for one in names if one not in events.BY_NAME})
    if unknown:
        found.append(f"{recording.example} holds events nobody knows: {', '.join(unknown)}.")
    for name, payload in recording.lines:
        shape = events.BY_NAME.get(name)
        if shape is None:
            continue
        try:
            shape.model_validate(payload)
        except ValidationError:
            # Every reason at once, never the first: this function's own
            # docstring says so, and it used to stop here (2026-09-20).
            found.append(f"{recording.example} holds a {name} whose payload does not fit it.")

    if not names or names[0] != events.NAMES[GenerationStarted]:
        found.append(f"{recording.example} does not start where a generation starts.")
    if not names or names[-1] != events.NAMES[events.Done]:
        found.append(f"{recording.example} does not end where a generation ends.")
    if events.NAMES[BeliefsPropagated] in names:
        found.append(
            f"{recording.example} stores likelihoods. They are recomputed from the seed, "
            "so a stored one could disagree with the engine that is running."
        )
    found += _grammar_faults(recording, names)
    # The header's intervention is checked when the file is read, and a file
    # whose header does not fit comes back as unreadable with a sentence of its
    # own rather than as a crash here — which is what B9 asks for (2026-09-20).
    if recording.example not in THE_FOUR_EXAMPLES:
        found.append(
            f"{recording.example} is not one of the four examples this program "
            f"ships with ({', '.join(THE_FOUR_EXAMPLES)}), so no card would ever play it."
        )
    for name, payload in recording.lines:
        if name != events.NAMES[ProposalRejected]:
            continue
        if not payload.get("violations") and not str(payload.get("claim_in_words", "")).strip():
            found.append(
                f"{recording.example} holds a refusal that says nothing at all: no "
                "rule it broke and no words of the model's. A refusal by the vendor "
                "carries no violation and that is legitimate, but it always carries "
                "the sentence the service gave."
            )
    if recording.header.prompt_hash != current_prompt_hash:
        found.append(
            f"{recording.example} was made against a different prompt from the one shipping "
            "today, so it shows wording this program no longer uses. Record it again."
        )
    return found
