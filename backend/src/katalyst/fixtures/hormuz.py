"""The Strait of Hormuz: one worked map, and the branch where Iran is struck the next day.

This is the product's one complete example, written as Python rather than as a
data file so that every number can carry a comment saying where it came from.
Stack 03a works the likelihoods through this map in its golden test, and stack
03b draws it, so it is built to exercise every shape the model layer defines:
all four kinds of claim, both modes of arrow, all three signal shapes, a
feedback arrow, all three belief slots, a base rate, evidence, a payoff, and a
reason for the one ending that cannot be traded.

**Every number here is illustrative.** Not one strength, likelihood, lag or
half-life was measured. They come from the sketch in
`docs/research/02-causal-modeling-formalisms.md` §3 and from the worked chapters
in `spec/graph/` and `spec/multiverse/`, and they are written down so the
machinery has something honest-shaped to run on — not because anyone has
established them. That is why no arrow claims a provenance of `documented`: no
retrieval step ran for this file. Arrows say `argued` (a mechanism was stated
and nothing was fetched to back it) or, in the one weak case, `asserted` (the
sentence is a story rather than a mechanism). Every belief is a range, never a
point, for the same reason.

**The sign convention, which is easy to get backwards.** A strength's sign says
which way the arrow pushes the claim *at its head* toward coming out true — not
which way the world moves. "Brent crude settles below $68" is made **more**
likely by the strait opening, so H → B is **+1.6**, even though the thing being
described is a falling oil price. The research report writes that arrow as -1.6
because it was thinking about the price; `spec/graph/link.md` settles it the
other way and the claim wins.

**Identifiers.** Claims use the short readable names the spec uses throughout:
H, C, B, R, M1, M2, N1, and S on the branch. An arrow's identifier is its two
ends joined by an arrow drawn in text — `H->B` is the arrow from H to B. That
convention is settled here, and it is the one
`spec/multiverse/branches-and-worlds.md` already writes in its worked example.

The claims::

    H   the strait is open to unrestricted transit for 14 straight days  (the hypothesis)
    C   the Lloyd's war-risk premium for Gulf transits falls below 0.4%
    B   Brent crude settles below $68 for five sessions
    R   OPEC+ announces output restraint                        (the tail: unlikely, heavy)
    M1  a Polymarket contract on Brent below $70 resolves YES              (tradeable)
    M2  the energy fund XLE underperforms the S&P 500 fund SPY             (tradeable)
    N1  Omani-mediated talks resume publicly       (real, and no venue prices it)

The arrows, with their sign, mode, signal shape and delay::

    H --( +1.6  trigger  impulse   2 days, half-life 30 )--> B
    H --( +1.1  sustain  step      same day             )--> C
    H --( +0.7  trigger  ramp     10 days               )--> N1
    C --( +0.7  sustain  step      7 days               )--> B
    B --( +0.9  trigger  impulse   1 day,  half-life 14 )--> M1
    B --( +0.8  trigger  ramp      3 days               )--> M2
    B --( +0.6  trigger  ramp     14 days, REFLEXIVE    )--> R
    R --( -1.2  trigger  step      5 days               )--> B   closes the loop

B and R form the one loop on the map. It is legal only because the arrow into R
is the market feeding back on the world — marked reflexive, and made honest by
taking a fortnight to arrive.

The branch adds S, a strike on Iranian territory, with three arrows::

    S --( -2.4  trigger  impulse   same day, half-life 10 )--> B
    S --( -2.0  sustain  step      1 day                  )--> C
    S --( -1.9  sustain  step      3 days                 )--> H   the showcase

The long comment on that last arrow is the one to read: it is where the two
kinds of causality part company.
"""

from datetime import date, timedelta

from katalyst.domain import (
    BaseRate,
    Belief,
    Beliefs,
    Branch,
    Do,
    Evidence,
    Graph,
    Insert,
    Link,
    Payoff,
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


# --- The claims ------------------------------------------------------------
#
# Each one is a claim that will be true or false by a date, judged by a named
# source. `prior` is what the model thinks about the claim on its own, before
# anything causes it. `beliefs.model` is what it thinks once its causes have
# pushed on it — which is arithmetic this stack does not do, so the numbers in
# that slot are illustrative stand-ins, and stack 03a will compute them for
# real. The two are the same number on the hypothesis, because the hypothesis
# has no causes and so there is nothing to add.


# H — the hypothesis. The user typed "the Strait of Hormuz is going to open
# next week"; this is that topic turned into something anyone could score.
#
# H carries the **user's own belief** as well as the model's. That is where a
# hypothesis gets one from: the likelihood slider on the input screen, stored
# untouched in its own slot. The user here is more bullish than the model —
# .55 against .35 — and that gap is the argument the user is having with the
# tool, which is the reason the two numbers are never averaged.
HORMUZ_OPEN = Proposition(
    id="H",
    claim="The Strait of Hormuz reopens to unrestricted commercial transit.",
    kind="hypothesis",
    resolution=Resolution(
        criteria=(
            "At least 14 consecutive days of unrestricted commercial transit through "
            "the Strait of Hormuz."
        ),
        source="Lloyd's List transit counts.",
        by=_resolve_by(31),
    ),
    prior=Belief(p=0.35, lo=0.22, hi=0.50, owner="model"),
    beliefs=Beliefs(
        model=Belief(p=0.35, lo=0.22, hi=0.50, owner="model"),
        user=Belief(p=0.55, lo=0.40, hi=0.70, owner="user"),
    ),
    # The outside view the prior starts from: of the Hormuz disruption episodes
    # since 1980, 7 of 9 ended within 90 days. The count comes from research
    # report 02 §3, which cites nothing for it, so `sources` is empty — and an
    # empty source list means exactly that nobody has checked the count, which
    # is why nothing downstream of it may call itself documented. The prior sits
    # well below 7-in-9 because this claim asks for 14 *consecutive* days inside
    # one month, which is a harder test than an episode merely ending.
    base_rate=BaseRate(
        reference_class=(
            "Closure or disruption episodes in the Strait of Hormuz since 1980 that "
            "ended within 90 days."
        ),
        k=7,
        n=9,
        sources=(),
    ),
    # Two published items, one each way. Both are illustrative items for a
    # worked example set in October 2026, so neither address is a specific
    # article — inventing an article address that resolves to nothing is the one
    # thing this product must never do. Each points instead at the publication
    # that would carry such a report, and both addresses were opened by hand on
    # 2026-09-17. Nothing here moves a number: evidence is the audit trail
    # beside the likelihood, not an input to it.
    evidence=(
        Evidence(
            claim="An Omani-mediated round is reported, with both sides attending.",
            url="https://www.bbc.com/news/world/middle_east",
            direction=1,
            weight=0.3,
        ),
        Evidence(
            claim="Three tankers remain held and no release has been announced.",
            url="https://www.lloydslist.com/",
            direction=-1,
            weight=0.4,
        ),
    ),
)


# C — the insurance step. It sits between the strait and the oil price: the lane
# opening is what lets underwriters reprice, and the cheaper cargo is what
# reaches the crude price.
WAR_RISK_PREMIUM_FALLS = Proposition(
    id="C",
    claim="Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%.",
    kind="event",
    resolution=Resolution(
        criteria=(
            "The quoted war-risk premium for a Gulf transit, as a percentage of hull "
            "value, prints below 0.40% on any day in the window."
        ),
        source="Lloyd's List war-risk rate reporting.",
        by=_resolve_by(30),
    ),
    prior=Belief(p=0.30, lo=0.18, hi=0.45, owner="model"),
    # Illustrative: two arrows push on C (H directly, and S once the branch is
    # applied), and adding those pushes up is stack 03a's job.
    beliefs=Beliefs(model=Belief(p=0.44, lo=0.30, hi=0.60, owner="model")),
)


# B — the oil price. The busiest claim on the map: two arrows in from the world
# (H and C), one back in from OPEC+ (R), and three arrows out to the endings.
BRENT_BELOW_68 = Proposition(
    id="B",
    claim="Brent crude settles below $68 for five sessions.",
    kind="event",
    resolution=Resolution(
        criteria=(
            "Front-month Brent crude futures settle below $68.00 on five sessions, "
            "consecutive or not, within the window."
        ),
        source="ICE Brent front-month settlement prices.",
        by=_resolve_by(45),
    ),
    prior=Belief(p=0.28, lo=0.15, hi=0.42, owner="model"),
    # Illustrative, as above: B has three incoming arrows and no arithmetic here.
    beliefs=Beliefs(model=Belief(p=0.46, lo=0.30, hi=0.63, owner="model")),
)


# R — the tail in the base map. Unlikely, and enormous if it happens: restraint
# pushes back on B at -1.2, which is more than enough to undo the move the whole
# map was built to catch. This is the claim the tail strip will show later, and
# it is deliberately in the base map rather than only on the branch so that the
# strip has something to draw before any branch exists.
OPEC_RESTRAINT = Proposition(
    id="R",
    claim="OPEC+ announces output restraint.",
    kind="event",
    resolution=Resolution(
        criteria=(
            "OPEC+ publishes a communiqué announcing a production cut, or an extension "
            "of existing cuts, of at least 500,000 barrels a day."
        ),
        source="The OPEC secretariat's published communiqué.",
        by=_resolve_by(60),
    ),
    prior=Belief(p=0.18, lo=0.08, hi=0.32, owner="model"),
    # Illustrative: R's one incoming arrow is the feedback arrow out of B, and
    # nothing unrolls a feedback arrow over time until stack 06.
    beliefs=Beliefs(model=Belief(p=0.24, lo=0.12, hi=0.40, owner="model")),
)


# M1 — a tradeable ending, and the one claim on the map a venue actually quotes.
# It carries all three belief slots' worth of interest: the model's .61 and the
# market's .48 sit side by side, and the 13 points between them is the edge
# somebody would be trading. They are never averaged into one number.
BRENT_CONTRACT = Proposition(
    id="M1",
    claim='A Polymarket contract "Brent below $70 on 2026-10-31" resolves YES.',
    kind="market",
    resolution=Resolution(
        criteria="The contract's published resolution is YES.",
        source="Polymarket's own resolution of the contract.",
        by=_resolve_by(30),
    ),
    prior=Belief(p=0.40, lo=0.28, hi=0.55, owner="model"),
    beliefs=Beliefs(
        # Illustrative, and the number research report 02 §3 gives for the base
        # world before any branch is applied.
        model=Belief(p=0.61, lo=0.45, hi=0.74, owner="model"),
        # **Illustrative, not a live quote.** A real market belief is read off a
        # venue: the mid-price between the best bid and the best offer becomes
        # the likelihood, and the quoted spread becomes the range. Nothing in
        # this file talks to Polymarket; a price is fetched at run time in a
        # later stack, and this stands in for one until then.
        market=Belief(p=0.48, lo=0.45, hi=0.52, owner="market"),
    ),
    payoff=Payoff(
        instrument='Polymarket contract "Brent below $70 on 2026-10-31"',
        direction="long",
        # 1.08 reads as a 108% move in the contract's own price: bought at the
        # .48 mid above, it pays 1.00 if the claim resolves YES. Open question 1
        # in `spec/graph/proposition.md` asks whether this field is a move in the
        # instrument's price or a return on the position; here the two readings
        # give the same number, because the contract is bought outright at the
        # mid with no borrowing. On a leveraged instrument they would not agree,
        # which is why the question is still open.
        magnitude=1.08,
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
    resolution=Resolution(
        criteria=(
            "XLE's total return minus SPY's total return, over the 20 trading days "
            "ending on the resolve-by date, is below -3.0%."
        ),
        source="Published closing prices and distributions for XLE and SPY.",
        by=_resolve_by(45),
    ),
    prior=Belief(p=0.35, lo=0.22, hi=0.50, owner="model"),
    # Illustrative, and again the number research report 02 §3 gives for the
    # base world.
    beliefs=Beliefs(model=Belief(p=0.54, lo=0.38, hi=0.68, owner="model")),
    payoff=Payoff(
        instrument=(
            "A dollar-neutral pair: XLE (Energy Select Sector SPDR) against SPY (SPDR S&P 500 ETF)"
        ),
        # `direction` says which side of the named instrument makes money when
        # the claim comes true. Holding the pair long — long XLE, short SPY —
        # loses if energy shares lag, so the position that pays here is the
        # short side: short XLE, long SPY.
        direction="short",
        # Three per cent, read straight from the claim: the size of the
        # underperformance the claim asks for. This is the reading the field's
        # own description takes — a fractional move in the instrument — and it
        # needs no assumption about an entry price, which is why it is the
        # cleaner of the two magnitudes on this map.
        magnitude=0.03,
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
    resolution=Resolution(
        criteria=(
            "Both governments confirm, on the record, that a mediated round has taken "
            "place in Oman."
        ),
        source="The Omani foreign ministry's statement, confirmed by both governments.",
        by=_resolve_by(60),
    ),
    prior=Belief(p=0.22, lo=0.12, hi=0.36, owner="model"),
    # Illustrative, as with every other propagated number here.
    beliefs=Beliefs(model=Belief(p=0.29, lo=0.15, hi=0.45, owner="model")),
    not_tradeable_reason=(
        "No venue quotes a contract on a diplomatic round, and the nearest traded "
        "proxies are sanctioned Iranian assets that cannot be bought at all, so there "
        "is nothing to price this with."
    ),
)


# --- The arrows ------------------------------------------------------------
#
# Every arrow says why it exists, how hard it pushes, how long the push takes to
# arrive, what the push does over time, and whether the push survives its cause
# going away. `confidence` is how sure the model is that the mechanism it just
# described is real; `provenance` is our own receipt for where the arrow came
# from. They are different questions, and the fixture keeps them apart.


# H → B — the trigger, and the other half of the showcase the branch sets up.
# A one-time repricing: once the transit data confirms the lane is open the
# risk premium comes out of the price, and it comes out once. Retracting H
# later does not put it back — that is what `trigger` means.
#
# The source attached here is real and was opened by hand on 2026-09-17. It
# backs the arrow's premise rather than its number: a fifth of the world's
# traded oil goes through this strait, which is why the strait has a price in
# crude at all. The receipt still says `argued`, because no retrieval step ran
# for this fixture — a person put the address in. `retrieved` is left empty for
# the same reason; it is the day our own retrieval step fetched something.
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
        "lane is open. It is a one-time repricing, not a standing discount."
    ),
    sources=(
        Source(
            url="https://www.eia.gov/todayinenergy/detail.php?id=4430",
            title="The Strait of Hormuz is the world's most important oil transit chokepoint",
            retrieved=None,
        ),
    ),
    confidence="argued",
    provenance="argued",
)


# H → C — the sustain. Underwriters hold the rate down only while the lane
# actually stays open; the openness is the desk and the low rate is the apple on
# it. Lag 0: a rate sheet moves the same day, not two days later.
HORMUZ_TO_PREMIUM = Link(
    id="H->C",
    source="H",
    target="C",
    mode="sustain",
    strength=1.1,
    lag=0.0,
    shape="step",
    rationale=(
        "Underwriters reprice Gulf hulls only while the lane actually stays open. The "
        "low rate is held up by the openness, not caused once by it."
    ),
    confidence="argued",
    provenance="argued",
)


# H → N1 — the weakest arrow on the map, and marked as such. The sentence below
# is a story rather than a mechanism: it cannot say which way the causality
# runs, because quiet diplomacy is at least as likely to have reopened the lane
# as the other way round. So the model's own certainty is `speculative` and our
# receipt is `asserted` — the weakest pair there is, which is how the canvas
# will draw it. An arrow like this is kept rather than deleted because the
# ending it reaches is worth saying out loud.
HORMUZ_TO_TALKS = Link(
    id="H->N1",
    source="H",
    target="N1",
    mode="trigger",
    strength=0.7,
    lag=10.0,
    shape="ramp",
    rationale=(
        "A lane that stays open is the confidence-building step mediators point to, so "
        "a public round becomes easier to announce. Which way this runs is arguable: "
        "quiet talks may be what reopened the lane in the first place."
    ),
    confidence="speculative",
    provenance="asserted",
)


# C → B — the insurance step reaching the oil price, about a week later. This is
# the one arrow where the model believes the mechanism is written down in the
# literature, so `confidence` is `documented`. Our receipt still says `argued`,
# because no retrieval step ran and nothing was fetched. That pair reads like a
# contradiction and is not one: confidence is a claim the model makes about a
# mechanism, provenance is a receipt we write about our own pipeline. Marking it
# `documented` with nothing behind it would be rejected outright by the map's
# rules, which is the point.
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
    confidence="documented",
    provenance="argued",
)


# B → M1 — the most direct arrow on the map. A contract on "Brent below $70"
# reprices within a day of settlements printing below $68.
#
# The half-life is not in the plan's table. An `impulse` with no half-life has
# no decay to evaluate, and stack 03a has to evaluate this arrow, so a number is
# supplied here: a fortnight, illustrative like the rest, and short because the
# contract itself settles a month out.
BRENT_TO_CONTRACT = Link(
    id="B->M1",
    source="B",
    target="M1",
    mode="trigger",
    strength=0.9,
    lag=1.0,
    shape="impulse",
    half_life=14.0,
    rationale=(
        "The contract is written on almost the same thing the claim measures, so a run "
        "of settlements below $68 reprices it within a day."
    ),
    confidence="argued",
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
    confidence="argued",
    provenance="argued",
)


# B → R — the feedback arrow: a price outcome changing what producers do. It is
# the only kind of arrow allowed to sit on a loop, and what keeps that honest is
# that it takes time — a fortnight here. An instantaneous loop is not feedback,
# it is a contradiction, and the map's rules reject it. Nothing computes with
# `reflexive` until stack 06; until then it is data on the canvas that the loop
# check sets aside.
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
        "brings forward a restraint announcement."
    ),
    confidence="argued",
    provenance="argued",
    reflexive=True,
)


# R → B — the arrow back, and the one negative strength in the base map. It is
# negative because B is the claim "Brent settles *below* $68", which announced
# restraint makes less likely. This is an ordinary world-to-world arrow, not
# feedback, so it is not marked reflexive: once the loop's feedback arrow is set
# aside, this one closes nothing.
OPEC_TO_BRENT = Link(
    id="R->B",
    source="R",
    target="B",
    mode="trigger",
    strength=-1.2,
    lag=5.0,
    shape="step",
    rationale=(
        "Announced restraint tightens expected supply and props the price back above the threshold."
    ),
    confidence="argued",
    provenance="argued",
)


def _checked(graph: Graph) -> Graph:
    """Give back the map, or refuse to load this file at all if any rule is broken.

    A stored example that quietly stops being valid is worse than one that never
    loaded: everything downstream — the golden test, the canvas, the generated
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
            WAR_RISK_PREMIUM_FALLS,
            BRENT_BELOW_68,
            OPEC_RESTRAINT,
            BRENT_CONTRACT,
            ENERGY_SHARES_LAG,
            TALKS_RESUME,
        ),
        links=(
            HORMUZ_TO_BRENT,
            HORMUZ_TO_PREMIUM,
            HORMUZ_TO_TALKS,
            PREMIUM_TO_BRENT,
            BRENT_TO_CONTRACT,
            BRENT_TO_ENERGY_SHARES,
            BRENT_TO_OPEC,
            OPEC_TO_BRENT,
        ),
        hypothesis_id="H",
    )
)
"""The base map: seven claims, eight arrows, checked the moment this file loads."""


# --- The branch: "…but Iran is struck the next day" ------------------------


# S — the strike. It exists only on the branch; the base map has never heard of
# it. A tail in the plainest sense: unlikely, and it changes everything if it
# happens. The resolve-by date is the day after this example is set on, because
# the branch supposes the strike lands on 2026-10-02.
STRIKE_ON_IRAN = Proposition(
    id="S",
    claim="A confirmed military strike on Iranian territory.",
    kind="event",
    resolution=Resolution(
        criteria=("A strike on Iranian territory reported by at least two of AP, Reuters and AFP."),
        source="The AP, Reuters and AFP newswires.",
        by=_resolve_by(1),
    ),
    # Illustrative, from research report 02 §3. S has no causes on this map, so
    # the two numbers are the same, exactly as on the hypothesis.
    prior=Belief(p=0.06, lo=0.02, hi=0.14, owner="model"),
    beliefs=Beliefs(model=Belief(p=0.06, lo=0.02, hi=0.14, owner="model")),
)


# S → B — a trigger against the oil price, sharper than the arrow it is fighting
# and quicker to fade: a strike puts the risk premium back in the price within
# hours, which is why the lag is zero and the half-life is ten days rather than
# thirty.
STRIKE_TO_BRENT = Link(
    id="S->B",
    source="S",
    target="B",
    mode="trigger",
    strength=-2.4,
    lag=0.0,
    shape="impulse",
    half_life=10.0,
    rationale=(
        "A strike restores the war-risk premium in the oil price faster than transit "
        "data removes it."
    ),
    confidence="argued",
    provenance="argued",
)


# S → C — a sustain against the insurance premium. Underwriters price the threat
# they can see today, so the rate stays up for as long as the strike stands,
# whatever the transit counts say.
STRIKE_TO_PREMIUM = Link(
    id="S->C",
    source="S",
    target="C",
    mode="sustain",
    strength=-2.0,
    lag=1.0,
    shape="step",
    rationale="Underwriters reprice on the threat, not on transit counts.",
    confidence="argued",
    provenance="argued",
)


# S → H — **the showcase.** Read this one slowly, because it is the whole idea
# of the product in a single arrow.
#
# It is a `sustain` arrow, and it points at the claim the user asserted. A
# reopening is held up by the *absence* of hostilities the way an apple is held
# up by a desk, not caused once by the opening event. So from the day the strike
# lands, the strait's openness **retracts** — even though the user supposed it
# true the day before with `do(H)`. Supposing a claim cuts the arrows that exist
# at that moment; this arrow was inserted afterwards, so it is live, and that is
# why the branch lists `do(H)` first.
#
# Now look at H → B in the base map above. That one is a `trigger`: it fired on
# 2026-10-01, the risk premium came out of the price, and that domino stays
# fallen. Retracting H on 2026-10-02 does not stand it back up — the push simply
# keeps fading on its own half-life while S → B shoves the price the other way.
#
# One branch, both kinds of causality: the sustaining kind, where the effect
# needs its cause to keep holding, and the sequential kind, where the effect
# outlives its cause. Getting this pair right is the difference between a map
# that behaves correctly and one that merely behaves plausibly.
STRIKE_TO_HORMUZ = Link(
    id="S->H",
    source="S",
    target="H",
    mode="sustain",
    strength=-1.9,
    lag=3.0,
    shape="step",
    rationale=(
        "A reopening is sustained by the absence of hostilities, not by the opening "
        "event, so a strike withdraws what was holding the lane open."
    ),
    confidence="argued",
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
        # 1. Suppose the strait opens, on the day this example is set. `do` cuts
        #    H loose from its causes; H is the hypothesis and has none, so the
        #    cut removes nothing — which is precisely what lets step 2 hang a new
        #    arrow onto H at all, and why this edit comes first.
        Do(target="H", value=True, at=FIXTURE_DATE),
        # 2. …but a strike happens. The claim and its three arrows arrive as one
        #    edit, so the map is never left holding a claim that causes nothing.
        #    Nothing about H, C or B is touched: this edit only adds.
        Insert(
            proposition=STRIKE_ON_IRAN,
            links=(STRIKE_TO_BRENT, STRIKE_TO_PREMIUM, STRIKE_TO_HORMUZ),
        ),
        # 3. Suppose the strike lands, one day after the strait opened. From
        #    here the two kinds of arrow part company — see the comment on
        #    S → H above.
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
