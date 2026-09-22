"""The Strait of Hormuz: one worked map, and the branch where Iran is struck the next day.

This is the product's one complete example, written as Python rather than as a
data file so that every number can carry a comment saying where it came from.
The engine works the likelihoods through this map in its story test and the
canvas draws it, so it is built to exercise every shape the model layer defines:
all four kinds of claim, **both kinds of truth** — something that happens once
and something that holds for a while and can stop — both modes of arrow, all
three signal shapes, a feedback arrow, all three belief slots, evidence, both
shapes of payoff — a named contract and a move in a price — and a stated reason
for the one ending that cannot be traded.

**Every number here is an input, and most of them are illustrative.** Not one
strength, lag or half-life was measured. They come from the sketch in
`docs/research/02-causal-modeling-formalisms.md` §3 and from the worked chapters
in `spec/graph/` and `spec/multiverse/`, and they are written down so the
machinery has something honest-shaped to run on — not because anyone has
established them. The two exceptions say so where they sit: the contract on the
strait's traffic is a real, live contract whose own words and identifiers are in
a committed file under `backend/recordings/quotes/`, and the expected move on the
energy-shares ending is arithmetic written out in full beside it.

**And this map is a curated example**, so its inputs may be tuned to make the
worked example rich and interesting rather than flat. Every tuned value carries
a comment saying what it was, what it is now and why, and the word **Tuned**, so
that searching this file for it finds every one of them. What is never tuned is
a **computed** number: `beliefs.model` equals `prior` on every claim here, which
is the truthful statement "nothing has been computed yet", and the engine's own
world is served beside this map. A number typed in by hand cannot say where it
came from, and that is the one state this product refuses to show.

That is also why no arrow claims a provenance of `documented`: no retrieval step
ran for this file. Arrows say `argued` (a mechanism was stated and nothing was
fetched to back it) or, in the one weak case, `asserted` (the sentence is a story
rather than a mechanism).

**No likelihood here carries a range** *(changed 2026-09-22; decision record
0028, "one likelihood per claim, computed once; no range anywhere")*. Every
belief below is a point: its low end, its likelihood and its high end are the
same number. The two extra numbers stay on the shape for a little while because
the browser and the wire still carry the fields; nothing reads them, and one
later pull request removes all three fields together.

**The sign convention, which is easy to get backwards.** A strength's sign says
which way the arrow pushes the claim *at its head* toward coming out true — not
which way the world moves. "Brent crude settles below $68" is made **more**
likely by the strait opening, so H → B is **+1.6**, even though the thing being
described is a falling oil price. The research report writes that arrow as -1.6
because it was thinking about the price; `spec/graph/link.md` settles it the
other way and the claim wins.

**And the sign does a second job on a claim that can stop holding.** An arrow
whose number sits *above* the claim's own number makes it start; one *below* it
makes it stop. So the strike's arrow into *the strait stays open* is what ends
that claim, and no separate field says so — decision record 0017, "a claim is an
event or a state; nothing retracts itself".

**Identifiers.** Claims use the short readable names the spec uses throughout:
H, O, C, B, R, M1, M2, M3, N1, and S on the branch. An arrow's identifier is its
two ends joined by an arrow drawn in text — `H->B` is the arrow from H to B. That
convention is settled here, and it is the one
`spec/multiverse/branches-and-worlds.md` already writes in its worked example.

The claims, with which kind of truth each one is::

    H   traffic through the strait returns to normal       (event; the hypothesis)
    O   the strait stays open to commercial transit through 1 November   (STATE)
    C   the Lloyd's war-risk premium for Gulf transits is under 0.4%     (STATE)
    B   Brent crude settles below $68 for five sessions                  (event)
    R   OPEC+ announces a new output cut          (event; the tail: unlikely, heavy)
    M1  a Polymarket contract on Brent below $70 resolves YES  (event; tradeable)
    M2  the energy fund XLE underperforms the S&P 500 fund SPY (event; tradeable)
    M3  Polymarket's own contract on the strait's traffic resolves YES
                                             (event; tradeable, and really quoted)
    N1  Omani-mediated talks resume publicly    (event; real, and no venue prices it)

The arrows, with their sign, mode, signal shape and delay::

    H --( +1.6  trigger  impulse   2 days, half-life 30 )--> B
    H --( +2.2  trigger  step      same day             )--> O
    H --( +4.0  trigger  step      same day             )--> M3
    H --( +0.7  trigger  ramp     10 days               )--> N1
    O --( +1.1  sustain  step      same day             )--> C
    C --( +0.7  sustain  step      7 days               )--> B
    B --( +0.9  trigger  impulse   1 day,  half-life 30 )--> M1
    B --( +0.8  trigger  ramp      3 days               )--> M2
    B --( +0.6  trigger  ramp     14 days, REFLEXIVE    )--> R
    R --( -1.2  trigger  step      1 day                )--> B   closes the loop

B and R form the one loop on the map. It is legal only because the arrow into R
is the market feeding back on the world — marked reflexive, and made honest by
taking a fortnight to arrive.

The branch adds S, a strike on Iranian territory, with three arrows::

    S --( -2.4  trigger  step      same day             )--> B
    S --( -2.0  trigger  step      1 day                )--> C   ends it
    S --( -3.2  trigger  step      3 days               )--> O   ends it; the showcase

The long comment on that last arrow is the one to read: it is where the two
kinds of causality part company. **Both events stand through the strike** — the
strait's traffic returned to normal and Iran was struck, and neither of those
un-happens. What falls is the state: the strait does not *stay* open, and
everything the openness was holding up comes down with it.
"""

from datetime import date, timedelta
from typing import Literal

from katalyst.domain import (
    Belief,
    Beliefs,
    Branch,
    ContractPayoff,
    Do,
    Evidence,
    Graph,
    Insert,
    Link,
    PricePayoff,
    Proposition,
    Resolution,
    Source,
    validate,
)

FIXTURE_DATE = date(2026, 10, 1)
"""The day this example is set on. Every date below is written as a span from it.

Nothing in this file asks what today's date is. The example is meant to read the
same in a year's time as it does now, which it cannot do if its dates move.
"""


def _resolve_by(days: int) -> date:
    """Give the date that many days after the day this example is set on.

    Written as a span rather than as a date typed out in full so that a reader
    can see how long a claim has to run without counting on their fingers.

    Args:
        days: How many days after `FIXTURE_DATE` the claim is settled by.

    Returns:
        The date the claim is settled by.
    """
    return FIXTURE_DATE + timedelta(days=days)


def _point(p: float, owner: Literal["model", "user", "market"] = "model") -> Belief:
    """Give a likelihood with no range around it: low, likelihood and high all equal.

    Decision record 0028 removed the range from this product altogether — no
    number on a tile, in the panel or on the change list carries one, because a
    second number per claim cost a reader attention on every tile and gave back a
    caveat. The `lo` and `hi` fields have not been deleted yet, because the
    browser and the wire still carry them, so every belief written here sets both
    equal to the likelihood and nothing reads them. One later pull request
    removes the fields, and this helper goes with them.

    Args:
        p: The likelihood.
        owner: Whose number it is — the model's, the user's, or a market's.

    Returns:
        That likelihood as a point.
    """
    return Belief(p=p, lo=p, hi=p, owner=owner)


# --- The claims ------------------------------------------------------------
#
# Each one is a claim that will be true or false by a date, judged by a named
# source. `prior` is what the model thinks about the claim on its own, before
# anything causes it. `beliefs.model` is what it thinks once its causes have
# pushed on it — and in this file it is **equal to the prior on every claim**,
# which is the truthful statement "nothing has been computed yet". The engine
# computes the real number and the world it produces is served beside this map.
# No computed number is ever typed in by hand here: a number that cannot say
# where it came from is exactly the state this product refuses to show.
#
# Every claim also says **which kind of truth it is**. `persistence="event"`
# means it happens once and stays happened; `persistence="state"` means it holds
# over a stretch of time and can stop holding, so it has two times — the day it
# switches on and the day it switches off — and its number is the chance it is
# still holding on its resolve-by day. There is no default: a map that leaves it
# out is refused by name (decision record 0017).


# H — the hypothesis. The user typed "the Strait of Hormuz is going to open
# next week"; this is that topic turned into something anyone could score.
#
# H carries the **user's own belief** as well as the model's. That is where a
# hypothesis gets one from: the likelihood slider on the input screen, stored
# untouched in its own slot. The user here is far more bullish than the model —
# .55 against .20 — and that gap is the argument the user is having with the
# tool, which is the reason the two numbers are never averaged.
HORMUZ_OPEN = Proposition(
    id="H",
    claim="The Strait of Hormuz reopens to normal commercial traffic.",
    kind="hypothesis",
    # It happens once and stays happened: the test below is met on some date or
    # it is not, and a date on which it was met does not stop having been met.
    persistence="event",
    # **Tuned.** The test used to be "at least 14 consecutive days of unrestricted
    # commercial transit through the Strait of Hormuz", judged by Lloyd's List
    # transit counts. It is now the test a real venue settles a real contract on,
    # word for word from that venue's own rules, which are kept in full in
    # `backend/recordings/quotes/3501950-2026-09-21.json`. Why: the map's whole
    # claim is that its numbers can be compared with a price somebody is dealing
    # at, and two questions that are not the same question cannot be compared.
    # The deadline did not have to move — the venue's contract ends at 23:59 New
    # York time on 31 October 2026, which is the day this claim already ran to.
    resolution=Resolution(
        criteria=(
            'IMF PortWatch publishes a 7-day moving average of transit calls ("Arrivals '
            'of Ships") for the Strait of Hormuz equal to or above 60 for any date '
            "between market creation and October 31, 2026."
        ),
        source="IMF PortWatch, as used by Polymarket market 3501950.",
        by=_resolve_by(31),
    ),
    # **Tuned.** Was .35. That number was built from the base rate below it —
    # seven of nine disruption episodes ending within ninety days — discounted
    # because the old test asked for fourteen *consecutive* days. Both halves of
    # that construction have gone: the reference class was the wrong population
    # (see the comment where the base rate used to sit), and the test is no
    # longer a test of duration.
    #
    # The venue's test is **easier on duration and harder on volume**: it is met
    # by a single date rather than by a fortnight of them, but it asks for
    # arrivals back at a normal level rather than for transit merely being
    # permitted. A full recovery of traffic inside the six weeks this claim has
    # left to run, with a live military tail sitting on the same map, is a
    # minority outcome, and that judgement — not a counted reference class — is
    # all that is behind .20.
    #
    # The venue prices this same test far lower still. Its price is in the
    # committed quote file, it reaches the map through the contract ending M3
    # below, and it is never merged with this number: the whole point of keeping
    # three slots is that the model and the market are allowed to disagree out
    # loud.
    prior=_point(0.20),
    # `beliefs.model` equals `prior`, here and on every claim below, and that is
    # the truthful statement "nothing has been computed yet". The engine writes
    # the computed number, and the world it produces is served beside this map;
    # a number typed in by hand could not say where it came from, which is the
    # one thing this product must never show.
    beliefs=Beliefs(model=_point(0.20), user=_point(0.55, owner="user")),
    # **No base rate.** There used to be one here: "of the Hormuz disruption
    # episodes since 1980, 7 of 9 ended within 90 days", taken from research
    # report 02 §3, which cites nothing for it. It is gone, and it is not
    # replaced. The class was the wrong population: the Strait has never been
    # closed, and a disruption — the Tanker War, the 2019 seizures, the 2024 MSC
    # Aries, the June 2025 episode — is a different kind of event from a closure,
    # so a count over the one says nothing about the other. `base_rate` is
    # allowed to be absent for exactly this case, and nobody has counted an
    # honest class for this claim. An absent count is a true statement; an
    # invented one is the single thing on this map a reader would catch first.
    #
    # Two published items, one each way, both re-pointed at the test this claim
    # now asks. Both are illustrative items for a worked example set in October
    # 2026, so neither address is a specific article — inventing an article
    # address that resolves to nothing is the one thing this product must never
    # do. Each points instead at the place that publishes this kind of report,
    # and the first is the very page the venue's own rules name as the source of
    # truth. Nothing here moves a number: evidence is the audit trail beside the
    # likelihood, not an input to it.
    evidence=(
        Evidence(
            claim=(
                "Weekly transit calls through the strait have risen three weeks running, "
                "though the seven-day average is still short of sixty."
            ),
            url="https://portwatch.imf.org/pages/cb5856222a5b4105adc6ee7e880a1730",
            direction=1,
            weight=0.3,
        ),
        Evidence(
            claim=(
                "Three tankers remain held, no release has been announced, and war-risk "
                "quotes for Gulf transits have not come down."
            ),
            url="https://www.lloydslist.com/",
            direction=-1,
            weight=0.4,
        ),
    ),
)


# O — **the state**, and the claim the whole branch turns on. Added 2026-09-22.
#
# H is an event: on some date the traffic test is met, and a date on which it was
# met stays met. That is not what the rest of the map depends on. Underwriters,
# charterers and the crude price care whether the lane **stays** open, and that
# is a different claim: it holds over a stretch of time and it can stop.
#
# Why it had to exist: before it, the strike's arrow pointed at the hypothesis
# itself and the map said the reopening *un-happened* — a claim the user typed
# being deleted by a cause nobody had asserted. Decision record 0017 removed that
# machinery outright ("nothing retracts itself") and gave the map a place to put
# the thing that really does stop: the state. Without this claim the inserted
# strike would move almost nothing, and the example's central sentence — "the
# strait opened, but Iran was struck the next day" — would have nowhere to land.
#
# Its number means "the chance this is still holding on 1 November", where an
# event's means "the chance this happens by 1 November". Two words differ, and
# the browser composes the sentence.
HORMUZ_STAYS_OPEN = Proposition(
    id="O",
    claim="The Strait of Hormuz stays open to commercial transit through 1 November.",
    kind="event",
    # The one state in the base map: it switches on when traffic comes back and
    # switches off if something closes the lane again.
    persistence="state",
    resolution=Resolution(
        criteria=(
            'IMF PortWatch\'s 7-day moving average of transit calls ("Arrivals of Ships") '
            "for the Strait of Hormuz is at or above 60 on 1 November 2026, and has not "
            "fallen below 60 on any date since it first reached it."
        ),
        source="IMF PortWatch transit-call data for the Strait of Hormuz.",
        by=_resolve_by(31),
    ),
    # Illustrative, and new with this claim. It is H's own question with "and it
    # does not lapse before 1 November" added, so it has to sit below H's .20;
    # how far below is a judgement and nothing more. No reference class has been
    # counted for it, and none is invented.
    prior=_point(0.12),
    # Nothing computed yet: the same number as the prior, until the engine runs.
    beliefs=Beliefs(model=_point(0.12)),
)


# C — the insurance step, and the map's second state. It sits between the strait
# and the oil price: the lane staying open is what lets underwriters hold the
# rate down, and the cheaper cargo is what reaches the crude price.
#
# **Tuned.** It used to be written as an event — "the premium *falls* below 0.4%
# on any day in the window" — while the arrow out of it was a `sustain`, which
# only a state may have. A war-risk rate is the plainest state on this map: it is
# a level, it can go back up, and the arrow into Brent depends on it being low
# *now* rather than on its having been low once. So the claim is restated as the
# level holding, and the arrow out of it is legal for the first time.
WAR_RISK_PREMIUM_LOW = Proposition(
    id="C",
    claim="Lloyd's war-risk insurance premium for Gulf transits is under 0.4%.",
    kind="event",
    persistence="state",
    resolution=Resolution(
        criteria=(
            "The quoted war-risk premium for a Gulf transit, as a percentage of hull "
            "value, is below 0.40% on the resolve-by date and has not printed at or "
            "above 0.40% since it first went under."
        ),
        source="Lloyd's List war-risk rate reporting.",
        by=_resolve_by(30),
    ),
    prior=_point(0.30),
    # Nothing computed yet: the same number as the prior, until the engine runs.
    # Was .44, a hand-written guess at what H's push would do to C.
    beliefs=Beliefs(model=_point(0.30)),
)


# B — the oil price. The busiest claim on the map: two arrows in from the world
# (H and C), one back in from OPEC+ (R), and three arrows out to the endings.
#
# **Owed, and said out loud because the alternative is a number nobody can
# check.** This claim names a level — $68 — and nothing in this repository
# records where Brent actually is, so its .28 cannot be argued with: the same
# claim is worth about .15 with Brent at $72 and about .85 with Brent at $66. The
# fix is a committed, dated spot observation from the Federal Reserve's own
# series (`DCOILBRENTEU`), which the grounding layer already has a shape for and
# which nobody has recorded yet. It is not typed here, because a level typed by
# hand is exactly the untraceable number this product refuses.
BRENT_BELOW_68 = Proposition(
    id="B",
    claim="Brent crude settles below $68 for five sessions.",
    kind="event",
    persistence="event",
    resolution=Resolution(
        criteria=(
            "Front-month Brent crude futures settle below $68.00 on five sessions, "
            "consecutive or not, within the window."
        ),
        source="ICE Brent front-month settlement prices.",
        # **Tuned.** Was `_resolve_by(45)`, 2026-11-15; now 2026-10-15, a
        # fortnight. Five settlements below $68 is about a fortnight of sessions,
        # so a fortnight is the honest window for this claim — and at forty-five
        # days both pushes on B had faded to nothing much (H → B to 0.37 of full
        # size, S → B to 0.04), so the tile read almost exactly B's own prior and
        # the example taught nobody anything. A tile is read on the claim's own
        # resolve-by day; this is the claim's date moving to where the claim
        # actually is, not the reading rule bending to flatter the demo.
        by=_resolve_by(14),
    ),
    prior=_point(0.28),
    # Nothing computed yet. Was .46, a hand-written guess.
    beliefs=Beliefs(model=_point(0.28)),
)


# R — the tail in the base map. Unlikely, and enormous if it happens: a new cut
# pushes back on B at -1.2, which is more than enough to undo the move the whole
# map was built to catch. This is the claim the tail strip will show later, and
# it is deliberately in the base map rather than only on the branch so that the
# strip has something to draw before any branch exists.
OPEC_RESTRAINT = Proposition(
    id="R",
    claim="OPEC+ announces a new output cut.",
    kind="event",
    persistence="event",
    resolution=Resolution(
        # **Tuned.** The test used to accept "a production cut, **or an extension
        # of existing cuts**, of at least 500,000 barrels a day". That made the
        # claim almost a certainty rather than a tail: the OPEC+ eight have met
        # roughly monthly since 2023 and have extended existing cuts at nearly
        # every one of those meetings, which over sixty days is worth far more
        # than the .18 below. Two ways out: raise the number three or fourfold,
        # or tighten the test to the thing the tail strip is actually for — an
        # announcement that would genuinely hurt a short-oil position. Tightening
        # the test keeps the elicited number and removes the contradiction, so
        # the criteria now ask for a **new** cut beyond what is already in force.
        criteria=(
            "OPEC+ publishes a communiqué announcing a production cut of at least "
            "500,000 barrels a day beyond the cuts already in force."
        ),
        source="The OPEC secretariat's published communiqué.",
        by=_resolve_by(60),
    ),
    prior=_point(0.18),
    # Nothing computed yet. Was .24, a hand-written guess. R's one incoming arrow
    # is the feedback arrow out of B, and a feedback arrow is carried as data
    # rather than worked through, so the engine leaves R at its prior too.
    beliefs=Beliefs(model=_point(0.18)),
)


# M1 — a tradeable ending, and the one place on this map where the three belief
# slots sit side by side. The gap between whatever the engine computes and the
# market's number is the edge somebody would be trading, and the two are never
# averaged into one.
#
# **This contract is a stand-in, and the map says so twice.** A read of the venue
# on 2026-09-21 found nothing quoting Brent crude at all — not this contract, not
# a near miss — so there is no identifier to put here and no price to record.
# What is kept is the *shape*: an ending that names a contract and carries a
# market voice, so the map still shows what a priced ending looks like. The one
# ending on this map with a real, live, recorded price is M3 below.
BRENT_CONTRACT = Proposition(
    id="M1",
    claim='A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.',
    kind="market",
    persistence="event",
    resolution=Resolution(
        criteria="The contract's published resolution is YES.",
        source="Polymarket's own resolution of the contract.",
        by=_resolve_by(30),
    ),
    prior=_point(0.40),
    beliefs=Beliefs(
        # **Tuned.** Was .61, the number research report 02 §3 gives for the base
        # world — a figure from a sketch rather than from this engine, and the
        # prose that grew around it ("the model says .61, the market says .48, so
        # there are thirteen points of edge") was a conclusion nobody had
        # computed. The engine's own answer is what goes on the screen, and until
        # it has run the honest statement is the prior repeated.
        model=_point(0.40),
        # **Illustrative, not a live quote, and a point rather than a range.**
        # Two things changed here on 2026-09-22. It used to read .48 with a range
        # of .45 to .52, and the comment said the venue's quoted spread became
        # that range: a venue's spread is what it costs to deal, not how unsure
        # the venue is, so decision record 0020 makes a market belief a point.
        # And decision record 0028 removed the range from every belief anyway.
        # The number itself stays a stand-in: nothing on the venue quotes Brent,
        # so no file can be committed for it and nothing can fetch it. It is here
        # so the map shows three voices; it is not a price anyone could deal at.
        market=_point(0.48, owner="market"),
    ),
    # A contract payoff, because this is the shape an ending takes when somebody
    # sells the question. It names the venue, the contract and the side, and it
    # names no price at all: what a contract costs is a live quote, and a number
    # typed here would be stale the moment it was written.
    payoff=ContractPayoff(
        venue="Polymarket",
        # A readable stand-in, not an identifier. Polymarket names a contract by
        # a numeric market identifier and an on-chain condition identifier, and
        # M3 below carries real ones; this claim has neither, because the
        # contract it describes does not exist.
        contract_id="brent-below-70-2026-10-31",
        title="Brent below $70 on 2026-10-31",
        # You make money when the claim comes true, so the side is the yes side.
        side="yes",
    ),
)


# M2 — the second tradeable ending, and a different sort of trade: a pair, held
# on both sides at once, rather than an outright position.
ENERGY_SHARES_LAG = Proposition(
    id="M2",
    claim=(
        "The energy fund XLE underperforms the S&P 500 fund SPY by more than 3% "
        "over 20 trading days."
    ),
    kind="market",
    persistence="event",
    resolution=Resolution(
        criteria=(
            "XLE's total return minus SPY's total return, over the 20 trading days "
            "ending on the resolve-by date, is below -3.0%."
        ),
        source="Published closing prices and distributions for XLE and SPY.",
        by=_resolve_by(45),
    ),
    prior=_point(0.35),
    # Nothing computed yet. Was .54, the number research report 02 §3 gives for
    # the base world — a figure from a sketch, not from this engine.
    beliefs=Beliefs(model=_point(0.35)),
    # A price payoff, because no venue asks this question, but two funds anybody
    # can trade move when the answer changes. The other half of the pair the map
    # shows: a contract at one ending, an instrument at the other.
    payoff=PricePayoff(
        # The pair, held on both sides at once: XLE (Energy Select Sector SPDR)
        # against SPY (SPDR S&P 500 ETF), dollar for dollar.
        instrument="XLE vs SPY",
        # `direction` says which side of the named instrument makes money when
        # the claim comes true. Holding the pair long — long XLE, short SPY —
        # loses if energy shares lag, so the position that pays here is the
        # short side: short XLE, long SPY.
        direction="short",
        # **Tuned.** Was 0.03, read straight off the claim. That was the wrong
        # number for this field twice over: 3% is where the claim *starts* being
        # true, not the size of the move when it is true, and the error ran about
        # two to one in the flattering direction, because it is the number a
        # position's profit and loss is scaled by.
        #
        # The arithmetic, which anybody can redo. XLE's volatility is 22% to 28%
        # a year and SPY's is 14% to 17%, correlated somewhere between 0.60 and
        # 0.70. The volatility of the difference is then 17.6% to 20.2% a year,
        # which over twenty trading days is 4.96% to 5.68%. For a difference with
        # no drift, the average gap given the gap is already past a threshold t
        # is sigma times density(z) over share-below(z), with z = minus t over
        # sigma, where density and share-below are the standard bell curve's
        # height and the share of it lying below a point. At a threshold of 3%
        # that is 6.05% at the narrow end and 6.60% at the wide one. The middle
        # is 6.3%, and that is what this field now says. (The same arithmetic
        # puts the chance of the claim itself at .27 to .30, which is why the
        # prior of .35 above is called slightly generous rather than wrong.)
        #
        # The three volatility inputs are illustrative like everything else here;
        # the step from them to 6.3% is not a judgement, it is arithmetic.
        move=0.063,
    ),
)


# M3 — the one ending on this map that a real venue really prices. Added
# 2026-09-22, Kent's decision: the curated map carries a real venue contract
# where one exists.
#
# It asks the venue's own question, word for word, and it is the same question H
# asks — which is the point. A model number and a market price can only be
# compared when they answer the same question, and on this map they now do. The
# venue's answers — its rules, its identifiers, its best bid and best offer and
# the instant they were read — are committed under
# `backend/recordings/quotes/`, in a file named by the market identifier below.
# **No price is typed here.** The market's voice on this claim is built from that
# file by the layer that owns prices; a number copied into this file could not
# say where it came from, and would drift away from the file the day the file was
# refreshed.
#
# Its public address, for a reader who wants to open it:
# https://polymarket.com/event/strait-of-hormuz-traffic-returns-to-normal-by-october-31-20260810151043583
TRAFFIC_CONTRACT = Proposition(
    id="M3",
    claim=(
        'A Polymarket contract "Strait of Hormuz traffic returns to normal by '
        'October 31?" resolves YES.'
    ),
    kind="market",
    persistence="event",
    resolution=Resolution(
        criteria=(
            'IMF PortWatch publishes a 7-day moving average of transit calls ("Arrivals '
            'of Ships") for the Strait of Hormuz equal to or above 60 for any date '
            "between market creation and October 31, 2026."
        ),
        source="Polymarket's own resolution of market 3501950, on IMF PortWatch data.",
        # The venue's contract ends at 03:59 UTC on 1 November 2026, which is
        # 23:59 on 31 October in New York. The same day this claim already ran to.
        by=_resolve_by(31),
    ),
    # Illustrative, and deliberately the same number as H's. This claim asks the
    # venue's contract the question H asks the world, so before H's own arrow is
    # taken into account the model has no reason to hold a different view of it.
    prior=_point(0.20),
    # Nothing computed yet. And **no market belief**: the venue's price for this
    # contract exists and is committed, but it reaches the map from the quote
    # file rather than from a number typed here.
    beliefs=Beliefs(model=_point(0.20)),
    payoff=ContractPayoff(
        venue="Polymarket",
        # The venue's own market identifier, and the name of the committed quote
        # file. The on-chain condition identifier and both outcome-token
        # identifiers are in that file; they are not copied here, because a copy
        # drifts and no test can check prose. The test
        # `test_the_market_ending_names_the_contract_the_quote_file_names` checks
        # this identifier and the side against the file itself.
        contract_id="3501950",
        title="Strait of Hormuz traffic returns to normal by October 31?",
        # The claim asks the same direction as the venue's "Yes" outcome, and the
        # committed book is the yes token's.
        side="yes",
    ),
)


# N1 — the ending that is real and cannot be traded. A map is allowed to finish
# here as long as it says why, out loud, rather than quietly stopping or
# inventing an instrument that does not exist. Saying "there is nothing to trade
# and here is the reason" is an answer, not a failure.
TALKS_RESUME = Proposition(
    id="N1",
    claim="Omani-mediated United States-Iran talks resume publicly.",
    kind="not_tradeable",
    persistence="event",
    resolution=Resolution(
        criteria=(
            "Both governments confirm, on the record, that a mediated round has taken "
            "place in Oman."
        ),
        source="The Omani foreign ministry's statement, confirmed by both governments.",
        by=_resolve_by(60),
    ),
    prior=_point(0.22),
    # Nothing computed yet. Was .29, a hand-written guess.
    beliefs=Beliefs(model=_point(0.22)),
    # **Tuned.** It used to read "No venue quotes a contract on a diplomatic
    # round, and the nearest traded proxies are sanctioned Iranian assets that
    # cannot be bought at all." The first half was simply false, and cheaply
    # falsified by anyone who looked: a read of the venue on 2026-09-21 found a
    # liquid contract on a United States-Iran diplomatic meeting by 31 October,
    # and another on an Iran-Oman agreement. A reason that is wrong is worse than
    # no ending at all, because the reason is the only thing this ending offers.
    #
    # Why this claim stays not-tradeable rather than becoming a priced ending:
    # the contracts that exist ask about **any** mediated round, and one of them
    # about an agreement rather than a round of talks. Neither settles the claim
    # this map makes, which is specifically about an Omani-mediated round with
    # both governments confirming. Naming a contract that answers a neighbouring
    # question would be the exact mistake this product exists to avoid.
    not_tradeable_reason=(
        "The contracts a venue does quote ask about any mediated United States-Iran "
        "round, or about an Iran-Oman agreement, rather than about an Omani-mediated "
        "round both governments confirm, so none of them settles this claim; and the "
        "nearest traded proxies are sanctioned Iranian assets that cannot be bought at "
        "all."
    ),
)


# --- The arrows ------------------------------------------------------------
#
# Every arrow says why it exists, how hard it pushes, how long the push takes to
# arrive, what the push does over time, and which of its cause's times it reads.
# The sentence in `rationale` is the argument for the arrow; `provenance` is the
# only receipt, and it is ours to write rather than the model's to claim. An
# arrow does not get to say how sure it is of itself.
#
# **What `mode` now means** (decision record 0017). A `trigger` arrow reads its
# cause's **on** time alone and keeps pushing afterwards — the toppled domino. A
# `sustain` arrow reads its cause's **whole interval**, from the moment it comes
# on until the moment it stops, and is dead after that — the apple on the desk.
# A `sustain` arrow therefore only makes sense out of a claim that can stop, so
# both of them on this map leave a state.


# H → B — the trigger, and the other half of the showcase the branch sets up.
# A one-time repricing: once the transit data confirms traffic is back the risk
# premium comes out of the price, and it comes out once. What happens to the
# strait afterwards does not put it back — that is what `trigger` means, and it
# is why both events still stand at the end of the branch while the state falls.
#
# **Tuned — the citation, not the number.** The comment here used to say "a fifth
# of the world's traded oil goes through this strait", citing the page below.
# Two things were wrong with that. The page is from 2012, and a fourteen-year-old
# citation on a live geopolitical claim is the first thing this audience pokes
# at. And the share it supports is of world petroleum *liquids consumption*; as a
# share of *seaborne* oil trade the figure is nearer a quarter to a third, and
# the sentence ran the two together. The arrow does not rest on the size of the
# share in any case — it rests on the strait being a chokepoint at all, which is
# what the page is cited for and what it says.
#
# The address is real and was opened by hand on 2026-09-17. The receipt still
# says `argued`, because no retrieval step ran for this fixture — a person put
# the address in. `retrieved` is left empty for the same reason; it is the day
# our own retrieval step fetched something.
HORMUZ_TO_BRENT = Link(
    id="H->B",
    source="H",
    target="B",
    mode="trigger",
    strength=1.6,
    lag=2.0,
    shape="impulse",
    half_life=30.0,
    rationale=(
        "The war-risk premium priced into crude unwinds once transit data confirms the "
        "lane is carrying normal traffic. It is a one-time repricing, not a standing "
        "discount."
    ),
    sources=(
        Source(
            url="https://www.eia.gov/todayinenergy/detail.php?id=4430",
            title=(
                "The Strait of Hormuz is the world's most important oil transit "
                "chokepoint (US Energy Information Administration, 2012)"
            ),
            retrieved=None,
        ),
    ),
    provenance="argued",
)


# H → O — **new, 2026-09-22**, and the arrow that makes the state exist at all.
# Traffic coming back is what switches the standing-open claim on; nothing else
# on this map can.
#
# The arithmetic of this arrow, said plainly: its number is above O's own number,
# so it bends the rate at which O comes **on** rather than the rate at which it
# stops. Taken together with O's .12, a strength of +2.2 says "if traffic returns
# to normal at the start of the window, the chance the lane is still open on 1
# November is a little over half" — short of certain, because coming back once is
# not the same as staying back for six weeks, which is the entire reason this
# claim is separate from H.
HORMUZ_TO_OPENNESS = Link(
    id="H->O",
    source="H",
    target="O",
    mode="trigger",
    strength=2.2,
    lag=0.0,
    shape="step",
    rationale=(
        "Traffic returning to a normal level is what puts the lane back in service; "
        "whether it stays in service is a separate question this arrow does not answer."
    ),
    provenance="argued",
)


# H → M3 — **new, 2026-09-22.** The claim and the contract ask the same question,
# so this is the strongest arrow on the map by some way, and that is right rather
# than alarming: two claims that are very nearly the same event should be joined
# by a very strong arrow, and the previous version of this map was criticised for
# the opposite — a contract ending pinned on at +0.9 when it was written on
# almost exactly the claim above it.
#
# It is not certainty, and the gap is the venue's own doing: the rules kept in
# the committed quote file allow revisions to published data, a fourteen-day
# grace period if the final date's data is late, and a pause of up to three days
# for data-integrity corrections. So the contract can settle differently from the
# world for reasons that have nothing to do with the strait.
HORMUZ_TO_TRAFFIC_CONTRACT = Link(
    id="H->M3",
    source="H",
    target="M3",
    mode="trigger",
    strength=4.0,
    lag=0.0,
    shape="step",
    rationale=(
        "The contract is written on this claim's own test, word for word, so it settles "
        "yes when the claim is true — short of certainty only because the venue's rules "
        "allow revisions, a grace period and a pause for data-integrity corrections."
    ),
    provenance="argued",
)


# H → N1 — the weakest arrow on the map, and marked as such. The sentence below
# is a story rather than a mechanism: it cannot say which way the causality
# runs, because quiet diplomacy is at least as likely to have reopened the lane
# as the other way round. So the receipt is `asserted`, the weakest on the map,
# and that is how the canvas will draw it. An arrow like this is kept rather than
# deleted because the ending it reaches is worth saying out loud.
HORMUZ_TO_TALKS = Link(
    id="H->N1",
    source="H",
    target="N1",
    mode="trigger",
    strength=0.7,
    lag=10.0,
    shape="ramp",
    rationale=(
        "A lane carrying normal traffic is the confidence-building step mediators point "
        "to, so a public round becomes easier to announce. Which way this runs is "
        "arguable: quiet talks may be what reopened the lane in the first place."
    ),
    provenance="asserted",
)


# O → C — the sustain, and the first of the two arrows that now leave a state.
#
# **Tuned.** This used to be `H->C`, out of the hypothesis. Its own rationale
# gave the game away: underwriters hold the rate down "only while the lane
# actually stays open", which is the state, not the event. Out of an event it was
# also illegal under the rule that only a claim which can stop may have a
# `sustain` arrow leaving it. Lag 0: a rate sheet moves the same day, not two
# days later.
OPENNESS_TO_PREMIUM = Link(
    id="O->C",
    source="O",
    target="C",
    mode="sustain",
    strength=1.1,
    lag=0.0,
    shape="step",
    rationale=(
        "Underwriters reprice Gulf hulls only while the lane actually stays open. The "
        "low rate is held up by the openness, not caused once by it."
    ),
    provenance="argued",
)


# C → B — the insurance step reaching the oil price, about a week later, and the
# second arrow leaving a state. It is a `sustain` because what reaches the crude
# price is the rate being low now, not its having dipped once; restating C as a
# level that holds is what makes this arrow legal.
#
# The mechanism is the sort of thing that is written down somewhere, and the
# arrow still says `argued`, because provenance is the only receipt and it
# records what our pipeline actually did: nothing was fetched for this file. An
# arrow does not get to grade its own mechanism, and marking this one
# `documented` with nothing behind it would be rejected outright by the map's
# rules.
PREMIUM_TO_BRENT = Link(
    id="C->B",
    source="C",
    target="B",
    mode="sustain",
    strength=0.7,
    lag=7.0,
    shape="step",
    rationale=(
        "Lower war-risk premiums cut the delivered cost of a Gulf cargo, and the saving "
        "shows up in the physical differential within about a week."
    ),
    provenance="argued",
)


# B → M1 — the most direct arrow into the stand-in contract. A contract on "Brent
# below $70" reprices within a day of settlements printing below $68.
#
# The half-life is not in the plan's table. An `impulse` with no half-life has
# no decay to evaluate, and the engine has to evaluate this arrow, so a number is
# supplied here, illustrative like the rest.
#
# **Tuned.** Was 14 days, chosen because the contract settles a month out. Now 30.
# The contract is written on very nearly the event B measures, so the repricing
# lasts about as long as the move does rather than unwinding inside a fortnight —
# and at fourteen days the push had faded to a quarter of full size by the day
# the contract is judged, so M1's tile read its own prior and the clearest chain
# on the map showed nothing.
BRENT_TO_CONTRACT = Link(
    id="B->M1",
    source="B",
    target="M1",
    mode="trigger",
    strength=0.9,
    lag=1.0,
    shape="impulse",
    half_life=30.0,
    rationale=(
        "The contract is written on almost the same thing the claim measures, so a run "
        "of settlements below $68 reprices it within a day."
    ),
    provenance="argued",
)


# B → M2 — equities follow crude, but slowly, which is what `ramp` is for: the
# push climbs across the three days rather than arriving all at once.
BRENT_TO_ENERGY_SHARES = Link(
    id="B->M2",
    source="B",
    target="M2",
    mode="trigger",
    strength=0.8,
    lag=3.0,
    shape="ramp",
    rationale=(
        "Energy earnings track the crude price with a lag, and the shares grind toward "
        "the new level over days rather than repricing in one session."
    ),
    provenance="argued",
)


# B → R — the feedback arrow: a price outcome changing what producers do. It is
# the only kind of arrow allowed to sit on a loop, and what keeps that honest is
# that it takes time — a fortnight here. An instantaneous loop is not feedback,
# it is a contradiction, and the map's rules reject it. Nothing computes with
# `reflexive` in this version; it is data on the canvas that the loop check sets
# aside.
BRENT_TO_OPEC = Link(
    id="B->R",
    source="B",
    target="R",
    mode="trigger",
    strength=0.6,
    lag=14.0,
    shape="ramp",
    rationale=(
        "A sustained run of sub-$68 settlements pressures OPEC+ revenue targets and "
        "brings forward a new cut."
    ),
    provenance="argued",
    reflexive=True,
)


# R → B — the arrow back, and one of the two arrows on this map that hold a claim
# back rather than push it along. It is negative because B is the claim "Brent
# settles *below* $68", which an announced cut makes less likely. This is an
# ordinary world-to-world arrow, not feedback, so it is not marked reflexive:
# once the loop's feedback arrow is set aside, this one closes nothing.
#
# **Tuned.** The lag was 5 days and is now 1. Two reasons, and the second is the
# one that forced it. A communiqué moves the futures curve in the session it
# lands in, not a working week later, so five days was never the honest number.
# And an arrow that holds a claim back can only do so while it is actually
# pushing: across B's fortnight, an arrow that does not start until day five has
# nine days to work in, and the engine reported that it could not hold Brent as
# far down as this arrow's own number asks. The engine says so out loud rather
# than quietly delivering something else, which is how this was found.
OPEC_TO_BRENT = Link(
    id="R->B",
    source="R",
    target="B",
    mode="trigger",
    strength=-1.2,
    lag=1.0,
    shape="step",
    rationale=(
        "An announced cut tightens expected supply and props the price back above the "
        "threshold within a session."
    ),
    provenance="argued",
)


def _checked(graph: Graph) -> Graph:
    """Give back the map, or refuse to load this file at all if any rule is broken.

    A stored example that quietly stops being valid is worse than one that never
    loaded: everything downstream — the story test, the canvas, the generated
    browser types — would go on using it and nothing would say why the answers
    had changed. So the check runs when this file is first read, and a failure
    names every fault at once, in the same words a user would be shown.

    Args:
        graph: The map to check before anything else is allowed to see it.

    Returns:
        That same map, once every rule has been checked.

    Raises:
        ValueError: If the map breaks any of the rules, listing all of them.
    """
    violations = validate(graph)
    if violations:
        listed = "\n".join(f"  - {one.code}: {one.message}" for one in violations)
        raise ValueError(f"The Hormuz example is not a valid map:\n{listed}")
    return graph


HORMUZ: Graph = _checked(
    Graph(
        id="hormuz",
        propositions=(
            HORMUZ_OPEN,
            HORMUZ_STAYS_OPEN,
            WAR_RISK_PREMIUM_LOW,
            BRENT_BELOW_68,
            OPEC_RESTRAINT,
            BRENT_CONTRACT,
            ENERGY_SHARES_LAG,
            TRAFFIC_CONTRACT,
            TALKS_RESUME,
        ),
        links=(
            HORMUZ_TO_BRENT,
            HORMUZ_TO_OPENNESS,
            HORMUZ_TO_TRAFFIC_CONTRACT,
            HORMUZ_TO_TALKS,
            OPENNESS_TO_PREMIUM,
            PREMIUM_TO_BRENT,
            BRENT_TO_CONTRACT,
            BRENT_TO_ENERGY_SHARES,
            BRENT_TO_OPEC,
            OPEC_TO_BRENT,
        ),
        hypothesis_id="H",
    )
)
"""The base map: nine claims, ten arrows, checked the moment this file loads."""


# --- The branch: "…but Iran is struck the next day" ------------------------


# S — the strike. It exists only on the branch; the base map has never heard of
# it. A tail in the plainest sense: unlikely, and it changes everything if it
# happens. The resolve-by date is the day after this example is set on, because
# the branch supposes the strike lands on 2026-10-02.
STRIKE_ON_IRAN = Proposition(
    id="S",
    claim="A confirmed military strike on Iranian territory.",
    kind="event",
    # An event, and the map's point: a strike does not un-happen. Both this claim
    # and the strait's reopening stand at the end of the branch; what falls is
    # the state between them.
    persistence="event",
    resolution=Resolution(
        criteria=("A strike on Iranian territory reported by at least two of AP, Reuters and AFP."),
        source="The AP, Reuters and AFP newswires.",
        by=_resolve_by(1),
    ),
    # Illustrative, from research report 02 §3. S has no causes on this map, so
    # its computed number would be its prior anyway.
    prior=_point(0.06),
    beliefs=Beliefs(model=_point(0.06)),
)


# S → B — the strike against the oil price, and the second of the two arrows on
# this map that hold a claim back.
#
# **Tuned.** It was an `impulse` with a ten-day half-life; it is now a `step`
# with no decay, and the strength is unchanged at -2.4. The shape was the thing
# that was wrong. An impulse at half-life ten has faded most of the way before
# Brent's fortnight is out, so across that window the arrow is only pushing for
# part of the time — and an arrow that is only pushing for part of the time
# cannot hold a claim as far down as this one's number asks. The engine reported
# exactly that, naming the arrow and both numbers, which is how it was found: it
# was asking Brent for a number the arithmetic could not deliver, and delivering
# something else quietly is precisely what this engine refuses to do.
#
# Either the shape or the number had to change, and the shape is the one that was
# never argued for. A strike on Iranian territory does not stop mattering to
# crude after ten days; the risk premium goes back into the price the same day
# and stays there while the threat stands. That is a step. The claim it is
# fighting, H → B, keeps its impulse, because a premium coming *out* of a price
# on confirmed transit data really is a one-off that decays.
STRIKE_TO_BRENT = Link(
    id="S->B",
    source="S",
    target="B",
    mode="trigger",
    strength=-2.4,
    lag=0.0,
    shape="step",
    rationale=(
        "A strike puts the war-risk premium straight back into the oil price, the same "
        "day, and it stays in while the threat stands."
    ),
    provenance="argued",
)


# S → C — the strike ending the low-premium state.
#
# **Tuned.** It was a `sustain` arrow, which only a claim that can stop may have
# leaving it, and S cannot stop: a strike stays a strike. It is now a `trigger`,
# which reads the strike's day alone and keeps pushing afterwards. The strength
# is unchanged at -2.0, and because that number sits below C's own number the
# arrow bends the rate at which C **stops** rather than the rate at which it
# starts: underwriters do not un-price a threat they can see.
STRIKE_TO_PREMIUM = Link(
    id="S->C",
    source="S",
    target="C",
    mode="trigger",
    strength=-2.0,
    lag=1.0,
    shape="step",
    rationale="Underwriters reprice on the threat, not on transit counts.",
    provenance="argued",
)


# S → O — **the showcase.** Read this one slowly, because it is the whole idea of
# the product in a single arrow.
#
# **Tuned, and this is the largest change in this file.** The arrow used to be
# `S->H`: it pointed at the hypothesis the user had supposed true, and the
# engine's answer was that the strait's reopening was *withdrawn* — a claim the
# user typed being deleted on a date computed from the map's own shape. Decision
# record 0017 removed that outright. Nothing on this map retracts anything: the
# user's word stands until the user takes it back.
#
# What actually stops is not the reopening. Traffic came back; that happened, and
# a strike the next day does not make it un-happen. What stops is the lane
# **staying** open, which is why this map now has a claim for exactly that, and
# why this arrow points at it. Because the number sits below O's own number, the
# arrow bends the rate at which O stops holding rather than the rate at which it
# starts — it is an *ending* arrow, and no field says so, the sign does.
#
# **Tuned, and the number moved: -1.9 became -3.2.** The story this example tells
# is that after a strike the lane staying open through 1 November is less likely
# than it was before anybody knew anything either way. At -1.9 the map said the
# opposite: the strike world sits on top of the supposition that traffic came
# back, which pushes this claim hard the other way, and the old number did not
# undo it — the claim came out *above* its base number, which would have meant a
# confirmed strike was good news for the lane. The sweep behind the change is
# kept beside this work; -2.8 is where it crosses and -3.2 is the first value
# clear of the crossing.
#
# **And the number reads stronger than the story sounds, for a reason that is
# temporary.** Every arrow on this map states its number the same way — the
# chance the claim at its head comes out true if this cause happens at the start
# of the window and nothing else does — and that question is a poor fit for an
# arrow whose job is to *end* something: the answer is not steady as the claim's
# own number changes, so the same story needs a different-looking number on a
# different map. Decision record 0017 settles that an ending arrow will be asked
# for *the chance it stops* instead, which is a question a person can answer, and
# that change rides the one pass where everything the model is asked changes at
# once. This number is restated then.
#
# Now look at H → B in the base map above. That one is a `trigger` out of an
# event: it fired when the traffic test was met, the risk premium came out of the
# price, and that domino stays fallen. The strike does not stand it back up; the
# push simply keeps fading on its own half-life while S → B shoves the price the
# other way. And O → C is a `sustain` out of the state: the moment the lane stops
# being open, the thing holding the insurance rate down is gone, and the rate
# goes back up with nothing else needing to happen.
#
# One branch, both kinds of causality: the sustaining kind, where the effect
# needs its cause to keep holding, and the sequential kind, where the effect
# outlives its cause. Getting this pair right is the difference between a map
# that behaves correctly and one that merely behaves plausibly.
#
# The lag of three days is unchanged and now carries a plainer meaning than it
# used to. Shipowners do not turn around the hour a strike lands; charters in
# progress run, and the transit count takes a few days to fall through the
# seven-day average the test reads.
STRIKE_ENDS_THE_OPENNESS = Link(
    id="S->O",
    source="S",
    target="O",
    mode="trigger",
    strength=-3.2,
    lag=3.0,
    shape="step",
    rationale=(
        "A strike ends the conditions under which owners will keep sending ships "
        "through, so within a few days the lane stops being open in the sense the "
        "transit count measures."
    ),
    provenance="argued",
)


HORMUZ_THEN_STRIKE = Branch(
    # The identifier the spec's own worked example already points at: a child
    # branch in `spec/multiverse/branches-and-worlds.md` names this one as its
    # parent.
    id="br_hormuz_then_strike",
    label="Hormuz opens, then Iran is struck",
    # No parent: this branch forks straight off the untouched base map.
    parent=None,
    interventions=(
        # 1. Suppose the traffic comes back, from the day this example is set.
        #    The cut reaches only the arrows into H that exist right now; H is the
        #    hypothesis and has none, so it removes nothing.
        Do(target="H", value=True, at=FIXTURE_DATE),
        # 2. …but a strike happens. The claim and its three arrows arrive as one
        #    edit, so the map is never left holding a claim that causes nothing.
        #    Nothing about H, O, C or B is touched: this edit only adds.
        Insert(
            proposition=STRIKE_ON_IRAN,
            links=(STRIKE_TO_BRENT, STRIKE_TO_PREMIUM, STRIKE_ENDS_THE_OPENNESS),
        ),
        # 3. Suppose the strike lands, one day after the traffic came back. From
        #    here the two kinds of arrow part company — see the comment on
        #    S → O above.
        Do(target="S", value=True, at=_resolve_by(1)),
    ),
)
"""The branch where the strait opens and Iran is struck the next day: three edits, in order.

A branch holds no claims and no numbers of its own — only the edits. Everything
it shows is computed from the base map plus this list, which is what makes the
original safe to leave untouched.
"""


TITLE = "Strait of Hormuz"
"""What this example is called on screen."""

ONE_LINE = (
    "If the Strait of Hormuz reopens, what happens to crude — and what happens if "
    "Iran is struck the next day?"
)
"""The example in one sentence, for the list of stored examples."""
