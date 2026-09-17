# Link — the arrow that says why

## Purpose

A link is one causal claim: *this proposition makes that proposition more (or less) likely, and here is the mechanism*. Before links, a user could say "Hormuz opening is bullish for oil" and be believed or not. With links, every step of that story is a separate arrow carrying a sentence of mechanism, a signed number for how hard it pushes, a delay for when the push arrives, a shape for what it looks like over time, and a record of where the number came from. The user can click any arrow, read the reason, disagree with the number, and watch what that does downstream. Nothing on the canvas is an opinion without a stated reason — which is the whole product.

---

## Data model

Two frozen shapes, written as pydantic models — pydantic being the Python library we use to define a data shape and check anything claiming to be one. *Frozen* means an instance can never be changed after it is built; a change is a new instance, recorded as an intervention on a branch (see [`../multiverse/interventions.md`](../multiverse/interventions.md)).

**A warning about the word *source*.** It does four different jobs in this part of the spec. `Link.source` is the **cause**, the claim an arrow starts at. `Link.sources` is the **citations** backing that arrow. `Source` is the type of one of those citations. And `Resolution.source` in [`proposition.md`](proposition.md) is the **adjudicator**, whoever decides if a claim came true. Where this chapter means the first it says *cause*; where it means the second or third it says *source* or *citation*; the fourth never appears here.

```python
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.proposition import PropositionId  # a plain `str`; defined in `proposition.md`

LinkId = str

Days = float
"""A span of time measured in days. 1.0 is one day, 0.5 is twelve hours, 14.0 is
a fortnight. A plain number rather than a duration written as text (the style
that writes a fortnight as "P14D"), because such a duration crosses to the
browser as a string, and nobody can do timing arithmetic on a string."""

Provenance = Literal[
    "asserted", "argued", "documented", "market_implied", "user", "historical", "simulated"
]
"""Where a number or a link came from. Set by our pipeline from what actually
happened, never declared by the model. The seven values are defined in the
table below and in `../vocabulary.md`."""


class Source(BaseModel):
    """Something a reader can open to check what we are claiming.

    A source exists because our retrieval step actually fetched a document, or
    because a person typed one in. It is never something the model reports
    having read. A `Source` is never invented to make a link look
    better than it is.
    """

    model_config = ConfigDict(frozen=True)

    url: str = Field(
        description="Where the reader goes to check it. One address that opens, not a search query."
    )
    title: str = Field(
        description="What the reader will see when they get there, in the publisher's words, not ours."
    )
    retrieved: date | None = Field(
        default=None,
        description="The day our retrieval step fetched it. None when a person supplied the source by hand.",
    )


class Link(BaseModel):
    """A causal claim from one proposition to another: A makes B more, or less, likely.

    A link is an argument, not a correlation. It must say why it thinks the
    mechanism is real (`rationale`), how hard it pushes (`strength`), how long
    the push takes to arrive (`lag`), what the push looks like over time
    (`shape`), and whether the push survives its cause going away (`mode`).

    A link must never carry a number without a reason. A link with no
    rationale, or one claiming evidence it does not cite, is rejected with a
    message — never quietly patched up. See `validity.md`.
    """

    model_config = ConfigDict(frozen=True)

    id: LinkId = Field(
        description="Minted by our code, never by the model. See `validity.md`, section Identifiers."
    )
    source: PropositionId = Field(
        description="The cause. The proposition this arrow starts at. Must name a proposition in the same graph."
    )
    target: PropositionId = Field(
        description="The effect. The proposition this arrow ends at. Must name a proposition in the same graph."
    )

    mode: Literal["trigger", "sustain"] = Field(
        description=(
            "How the push behaves when the cause goes away. 'trigger': a one-time shove — once the "
            "cause becomes true the effect is pushed and stays pushed, fading on its own; undoing the "
            "cause later does not undo it (a toppled domino). 'sustain': a continuous hold — the push "
            "exists only while the cause holds, and vanishes the moment it stops (a desk under an apple)."
        )
    )
    strength: float = Field(
        description=(
            "How far this link shifts the target's log-odds while the push is at full size. Signed: "
            "positive makes the target claim more likely to be TRUE, negative less likely. This is not a "
            "probability and is not capped at 1. Roughly: +1 triples the odds, -1 cuts them to a third."
        )
    )
    lag: Days = Field(
        description=(
            "Days from the cause becoming true to the push reaching full size. 0.0 means the same day. "
            "Must be greater than 0 when `reflexive` is true (INV-6)."
        )
    )
    shape: Literal["impulse", "step", "ramp"] = Field(
        description=(
            "What the push does over time. 'impulse': nothing during the lag, then a spike that decays "
            "by `half_life`. 'step': nothing during the lag, then full size, held. 'ramp': climbs from "
            "nothing to full size across the lag, then held."
        )
    )
    half_life: Days | None = Field(
        default=None,
        description=(
            "Days for an 'impulse' push to fall to half its size. Meaningful only when `shape` is "
            "'impulse'; None for 'step' and 'ramp'."
        ),
    )

    rationale: str = Field(
        description=(
            "The mechanism in one to three plain sentences: why this cause moves this effect. Required "
            "on every link. An empty rationale is a violation, not a default (INV-2)."
        )
    )
    sources: tuple[Source, ...] = Field(
        default=(),
        description=(
            "What backs the link. At least one is required when `provenance` claims evidence — "
            "'documented', 'historical' or 'market_implied' (INV-2)."
        ),
    )
    confidence: Literal["speculative", "argued", "documented"] = Field(
        description=(
            "How sure the model is that the mechanism it just described is real. The model's certainty "
            "about its own claim. Never a probability, and never rendered as one."
        )
    )
    provenance: Provenance = Field(
        description=(
            "Where this link and its number came from, as a fact about our pipeline. Set by `engine/` "
            "from what actually happened; the model never fills this in (decision record 0003, rule 5)."
        )
    )
    reflexive: bool = Field(
        default=False,
        description=(
            "True when this arrow is a market feeding back on the world — a price outcome changing what "
            "people do. A reflexive link is allowed to close a loop, and must have `lag > 0` (INV-6)."
        ),
    )
```

### Strength, and what log-odds means

The **odds** of a claim are the chance it is true divided by the chance it is false: a 50% claim is 1-to-1 odds, a 75% claim is 3-to-1. **Log-odds** is the natural logarithm of that ratio, and it is the scale on which independent pushes *add* instead of multiplying — so a proposition with three parents gets three numbers added together, not a table of every combination. A strength of +1 multiplies the odds by about 2.7, which is roughly tripling them; -1 cuts them to about a third.

What a single link does to a claim we thought was a coin flip:

| `strength` | a 50% claim becomes | in words |
|---:|---:|---|
| −3.0 | 5% | close to ruled out |
| −2.0 | 12% | a strong push against |
| −1.0 | 27% | a clear push against |
| −0.5 | 38% | a nudge against |
| 0.0 | 50% | no effect — never draw this link |
| +0.5 | 62% | a nudge toward |
| +1.0 | 73% | a clear push toward |
| +2.0 | 88% | a strong push toward |
| +3.0 | 95% | close to decisive |

The push is relative, not absolute. The same +1.0 applied to a claim we thought was 5% likely takes it to about 13%, not to 73%. That is the property we want: no sum of pushes can ever drive a probability below 0 or above 1.

**The sign is on the claim, not on the world.** `strength` is positive when the cause makes the *target proposition come out TRUE* more often. A proposition reading "Brent crude settles below $68" is made **more** likely by the strait opening, so that arrow is **positive** — even though the thing it describes is the oil price going *down*. Research report 02 writes that arrow as −1.6; it was thinking about the price, not about the claim. The claim wins.

### The two modes: the domino and the apple

This is Kent's idea from `docs/initial-brainstorming.md`, and research report 02 §4 called it the best one in the notes. In his words: two things can depend on each other *sequentially* — toppling dominoes, where "an earlier domino can be reset without changing the overall effect of the chain of dominoes being toppled" — or one can require *the sustained existence* of the other, like an apple sitting on a desk, held up only as long as the desk keeps pushing back against gravity.

| | `trigger` — the domino | `sustain` — the apple on the desk |
|---|---|---|
| When it pushes | Once, when the cause becomes true | Continuously, for as long as the cause holds |
| If the cause is undone later | Nothing happens. The effect stays pushed and keeps fading on its own | The push is withdrawn. The effect retracts |
| Typical shape | `impulse`, sometimes `ramp` | `step` |
| Hormuz example | The war-risk premium priced into crude unwinds once, over weeks | Insurers keep the premium low only while the lane stays open |
| The plain sentence | "It already happened" | "It is still happening" |

```
                   t0                      t1
                   │                       │
trigger (domino)   ▼                       ▼
push on effect ────█████▇▇▆▆▅▅▄▄▃▃▂▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
                   └ fires once, then fades on its own;
                     t1 changes nothing — the domino stays fallen.

sustain (apple on desk)
push on effect ────████████████████████████▁▁▁▁▁▁▁▁▁
                   └ holds while the cause holds …
                                           └ … and is gone at t1.

t0 = the cause becomes true.    t1 = the cause stops being true.
The cause is the link's `source`; the effect is its `target`. Elsewhere
these two are also called the parent and the child.
```

Mode is the field that makes "Hormuz opens, but Iran is struck the next day" behave correctly rather than plausibly. The strike retracts the strait's openness through a `sustain` arrow, while the crude-price shove that already fired through a `trigger` arrow keeps fading on its own schedule. One example, both kinds of causality. The worked branch is in [`../multiverse/branches-and-worlds.md`](../multiverse/branches-and-worlds.md).

### Shapes and timing

`lag` is the delay in days from the cause becoming true to the push reaching **full size**. (The vocabulary puts it as "time from parent-true to link-active"; for `impulse` and `step` those are the same instant. For `ramp` the push is already climbing during the lag, so this chapter pins the definition to the moment it reaches full size, and raises the wording under Open questions.) The three shapes differ in what the push does before and after that moment:

```
                   cause true             lag ends
                   │                      │
impulse  push  ────┴──────────────────────█▇▆▅▄▃▂▁▁▁▁▁   spike, then halves every half_life
step     push  ────┴──────────────────────██████████████   switches on and holds
ramp     push  ────┴▁▁▁▂▂▂▃▃▃▄▄▄▅▅▅▆▆▆▇▇▇▇██████████████   climbs across the lag, then holds
```

- **`impulse`** — the push arrives as a spike and decays; `half_life` is how many days it takes to halve. Use it when the effect is a repricing that happens once: a risk premium unwinding.
- **`step`** — the push switches on at the end of the lag and stays at full size. Use it when the effect is a standing condition: an insurance rate that stays low while the lane is open.
- **`ramp`** — the push climbs from nothing to full size across the lag window, then holds. Use it when the effect accumulates: equity prices grinding toward a new level over weeks.

> **No arithmetic happens in this stack.** Nothing in stack 02 evaluates a shape, adds a strength, or moves a probability. These fields are *defined* now, with their meanings pinned down, so that when the propagation engine arrives it fits shapes that already exist. How a child's likelihood is actually computed from its parents — adding strengths on the log-odds scale, evaluating each shape at a point in time, and running thousands of seeded simulations — is `../multiverse/propagation.md`, written in stack 03a.

### `reflexive` — a market feeding back on the world

Markets are not spectators. A price outcome changes what producers, regulators and traders do next, and that feeds back into the world the price was measuring. Kent's note: "markets are complex adaptive systems that change based on the positions that [are] being taken."

A link marked `reflexive` is that feedback arrow, and it is the **only** kind of arrow allowed to sit on a loop. The rule that makes the loop honest is `lag > 0`: the feedback must take time. Cheap crude today provokes an output cut in a fortnight, not instantly. An instantaneous loop is not a feedback mechanism, it is a contradiction, and it is rejected (INV-6, violation code `reflexive_without_lag`).

**Defined now, computed with in stack 06.** Nothing unrolls a reflexive link over time until then. Until stack 06 a reflexive link is data on the canvas: drawn, readable, and excluded from the loop check. See `validity.md` for how the loop check removes reflexive links before looking for cycles.

### `confidence` versus `provenance`

The two fields answer different questions, and keeping them apart is what lets the canvas draw an honest arrow.

- **`confidence` is about the mechanism.** How sure the model is that the arrow it just drew describes something that really works this way. It is the model's certainty about its own claim, and it travels with the claim. `speculative` — a plausible story the model cannot defend in detail. `argued` — a mechanism it can state step by step. `documented` — a mechanism it believes is written down in the literature. Note the vocabulary's warning: *confidence* here never means a probability, and is never rendered as one.
- **`provenance` is about where the number came from.** A fact about our pipeline, recorded by `engine/` from what actually happened during generation. The model never declares it (decision record 0003, rule 5). This is what the canvas encodes as a stroke style, so a user can see at a glance which arrows have documents behind them and which are the model talking (INV-2, INV-12).

| `provenance` | Set when |
|---|---|
| `asserted` | The model gave a link with no mechanism worth the name and no sources |
| `argued` | The model stated a mechanism; nothing was retrieved to back it |
| `documented` | The retrieval step attached at least one real source |
| `market_implied` | The number was read off a live price |
| `historical` | The number came from a study of past cases |
| `user` | A person typed it — a `retune` of a strength, or a hand-added link |
| `simulated` | A probe produced it (stretch; see [`../probes/`](../probes/)) |

The short version: **confidence is a claim the model makes; provenance is a receipt we write.** A link can be `confidence: documented` and `provenance: argued` — the model believes the mechanism is in the literature, but our retrieval step came back empty-handed, so we do not get to say documented. That combination is legal and informative, and it is exactly the case the two fields exist to distinguish.

The two lists share the words `argued` and `documented`, which is a real collision. It is raised under Open questions, not settled here.

---

## Behaviour

Worked on the assignment's first example: *"The Strait of Hormuz is going to open next week."* The propositions are `H` (the strait open to unrestricted commercial transit for 14 consecutive days, judged by Lloyd's List), `B` (Brent crude settles below $68 for five sessions), `C` (the Lloyd's war-risk premium for Gulf transits falls below 0.4%), `R` (OPEC+ announces output restraint), and `M1` (a Polymarket contract "Brent below $70" resolves YES). Their full shapes are in [`proposition.md`](proposition.md). Numbers below are illustrative, as research report 02's are.

### B1 — one cause, two kinds of arrow

The user types the hypothesis. The map comes back with two arrows out of `H`, and they are not the same kind of arrow:

| Field | `H → B` | `H → C` |
|---|---|---|
| `mode` | `trigger` | `sustain` |
| `strength` | `+1.6` | `+1.1` |
| `lag` | `2.0` | `0.0` |
| `shape` | `impulse` | `step` |
| `half_life` | `30.0` | `None` |
| `rationale` | "The war-risk premium priced into crude unwinds once transit data confirms the lane is open. It is a one-time repricing, not a standing discount." | "Underwriters reprice Gulf hulls only while the lane actually stays open. The low rate is held up by the openness, not caused once by it." |
| `confidence` | `argued` | `argued` |
| `provenance` | `argued` | `argued` |
| `sources` | `()` | `()` |
| `reflexive` | `False` | `False` |

The user clicks the wire from `H` to `B` and the Inspector shows the rationale, the strength as "+1.6 — a strong push toward", and a dashed stroke meaning *argued, not documented*. They can `retune` the strength if they disagree ([`../multiverse/interventions.md`](../multiverse/interventions.md)).

The payoff comes later. In the branch where Iran is struck the day after the strait opens, `H → C` retracts — the desk is gone, the insurance step switches off — while `H → B` keeps fading on its own schedule, because that domino already fell. Same cause, two honest behaviours.

### B2 — a documented link cites its sources

The retrieval step finds a real document behind the insurance mechanism. `C → B` comes back as:

```
C → B   mode=sustain  strength=+0.7  lag=7.0  shape=step  half_life=None
        rationale="Lower war-risk premiums cut the delivered cost of a Gulf
                   cargo, and the saving shows up in the physical differential
                   within about a week."
        confidence=documented
        provenance=documented
        sources=(Source(url="https://lloydslist.com/…",
                        title="War risk rates and voyage economics in the Gulf",
                        retrieved=2026-09-28),)
```

On the canvas the wire is drawn solid, and the Inspector lists the source with its title and the date we fetched it.

Now the failing case. If the same link arrived with `provenance="documented"` and `sources=()`, it does **not** get downgraded to `argued` to make it fit. `validate` returns a `documented_without_source` violation naming the arrow by its two claims, and the proposal is rejected (INV-2; see `validity.md`). Being generous with an unbacked claim is exactly the state a user cannot trace.

In the shipped Hormuz fixture these arrows are marked `argued`, not `documented`, because we have not attached real retrieved sources to them. The fixture is honest about what it is.

### B3 — a reflexive loop, `B → R → B`

Cheap crude provokes producers; producers prop the price back up. That is a loop, and it is legal only because one of the two arrows is marked as feedback and takes time:

| Field | `B → R` | `R → B` |
|---|---|---|
| `mode` | `trigger` | `trigger` |
| `strength` | `+0.6` | `−1.2` |
| `lag` | `14.0` | `5.0` |
| `shape` | `ramp` | `step` |
| `rationale` | "A sustained run of sub-$68 settlements pressures OPEC+ revenue targets and brings forward a restraint announcement." | "Announced restraint tightens expected supply and props the price back above the threshold." |
| `reflexive` | `True` | `False` |

`B → R` is the market feeding back on the world — a price outcome changing what a producer group does — so it carries `reflexive=True` and a fortnight of lag. `R → B` is an ordinary world-to-world arrow, and its strength is **negative** because `B` is the claim "Brent settles *below* $68", which restraint makes *less* likely.

The loop check removes reflexive links first, so what remains is `R → B` alone: no cycle, no violation. Drop the `reflexive` flag on `B → R` and the same graph is rejected with one `cycle` violation. Set `lag=0.0` on it and it is rejected with `reflexive_without_lag`. Both messages are in `validity.md`.

---

## INVARIANTS

`backend/tests/strategies.py::links()` is the generator that produces random **valid** links — valid by construction, so anything it emits should survive every check below. `graphs()` in the same file does it for whole maps, and `broken_graphs(*rules)` produces maps with each named rule broken. Both are built on `hypothesis`, a Python library that runs a statement over hundreds of random inputs and shrinks any failure to the smallest example that still fails; it is unrelated to the user's *hypothesis*.

Local numbers (`INV-graph.<n>`) are unique across the whole of `spec/graph/`. **This chapter holds one of them, `INV-graph.1`.** Every invariant here runs in stack 02.

| ID | Statement | Test | Stack |
|---|---|---|---|
| **INV-2** (link half) | For all links drawn from `links()`: `rationale` is a non-empty string, `provenance` is one of the seven values, and when `provenance` is `documented`, `historical` or `market_implied`, `len(sources) >= 1`. For all graphs drawn from `broken_graphs("documented_without_source")`, `validate` returns exactly one `documented_without_source` violation | `test_validate_rejects_unsourced_documented_link` | 02 |
| **INV-6** (link half) | For all links drawn from `links()`: if `reflexive` is true then `lag > 0`. For all graphs drawn from `broken_graphs("reflexive_without_lag")`, `validate` returns exactly one `reflexive_without_lag` violation | `test_reflexive_links_have_positive_lag` | 02 |
| **INV-graph.1** | For all graphs drawn from `graphs()`: every link's `source` and `target` name a proposition present in `graph.propositions`. For all graphs drawn from `broken_graphs("dangling_link")`, `validate` returns exactly one `dangling_link` violation | `test_validate_rejects_dangling_link` | 02 |

Round-trip and immutability are not repeated here. `test_models_round_trip_json` and `test_models_are_frozen` are stated once for every model in this part — `Link` and `Source` alongside `Graph`, `Proposition`, `Belief` and `Violation` — as `INV-graph.7` and `INV-graph.8` in [`validity.md`](validity.md). Local numbers `INV-graph.2` and `INV-graph.3` are retired; they said the same thing about links alone.

Two things that read like invariants but are **not**, because no rule in `validate` enforces them and so no generator can be pointed at them: that `half_life` is set when and only when `shape` is `impulse`, and that `strength` stays inside any sane range. Both are documented on the field and raised under Open questions.

---

## ANTI-PATTERNS

1. **Do not draw a link with no rationale**, because an arrow with a number and no sentence is a state the user cannot trace, which is a veto condition. Reject the proposal with `missing_rationale` and make the model say why, in one to three sentences, or not draw the arrow.
2. **Do not let the model declare its own provenance**, because `provenance` is a claim about our pipeline, not about the world, and a model that can write `documented` will write it. `engine/` sets the field from what actually happened: `documented` only when retrieval attached at least one source, otherwise `argued` or `asserted` (decision record 0003, rule 5). The shape the model is asked to fill does not contain the field at all.
3. **Do not accept a conditional probability as a link.** "P(oil down | Hormuz open) = 0.7" is a statement about *correlation* — how often the two are seen together, including when a third thing caused both. A link is a claim that one thing *makes* the other happen, which is why it carries a mechanism. Ask for the mechanism and the size of the push; if there is no mechanism, there is no arrow. This is also why the product offers `do` and `observe` as two separate verbs (INV-3, [`../multiverse/interventions.md`](../multiverse/interventions.md)).
4. **Do not ask for one strength per combination of parents.** A proposition with five parents has thirty-two combinations; a model will happily invent thirty-two numbers, and no human can audit past three. One number per arrow, added on the log-odds scale, keeps elicitation and explanation the same size as the picture. The cost — assuming the arrows are independent once their parents are known — is real, and it is paid in the open: correlated causes are split out with `refine`, and every belief is shown with its interval rather than as a point (decision record 0005).
5. **Do not model the map as a repeating process.** A Markov chain settling into a long-run average, or a chaotic system's attractor, needs the same thing to happen over and over. These events happen once: the strait opens or it does not. There is no steady state to find and no distribution to converge on. The legitimate part of that idea is already here — `lag`, `shape` and `reflexive` let a map be unrolled along a timeline, which is how a feedback loop is made to behave without pretending the world repeats (`PRODUCT_REQUIREMENTS.md` §10, anti-pattern 8).
6. **Do not sign `strength` by which way the world moves.** Sign it by whether the *target claim comes out true*. "Brent below $68" is made more likely by the strait opening, so that arrow is positive even though the price is falling. Getting this backwards silently inverts an entire branch, and it is the mistake already sitting in the research report.

---

## Open questions

Raised 2026-09-16. Each needs Kent.

1. **`confidence` and `provenance` share two words.** Both lists contain `argued` and `documented`, so `confidence="documented", provenance="argued"` is legal and reads like a contradiction until you know the rule. Options: rename `confidence` to `mechanism_confidence` and give it its own words (`hunch` / `reasoned` / `textbook`); drop `confidence` and let `provenance` plus the rationale carry it; or keep both and rely on the Inspector labelling them. The two fields do carry different information — one is the model's certainty about a mechanism, the other is a receipt from our pipeline — so the question is naming, not existence.
2. **The shapes sheet names `Source` but not its fields.** The three above (`url`, `title`, `retrieved`) are a proposal. Does a source need a publisher, a quoted snippet, or an access date distinct from the retrieval date?
3. **`sources: list[Source]` versus tuples everywhere.** The shapes sheet's `Link` row writes `list[Source]`, while its immutability row says collections are tuples and its `Graph` row uses tuples. Written here as `tuple[Source, ...]`, which is the rule the rest of the sheet follows. Confirm.
4. **`half_life` on a non-`impulse` link has no violation code.** The twelve codes in the shapes sheet do not cover it, so today a `step` link carrying a half-life is accepted and the field ignored. Add a thirteenth code, make it a pydantic field validator, or leave it documented and ignored?
5. **Does `ramp` need its own duration?** This chapter defines all three shapes as reaching full size at the end of `lag`, with `ramp` climbing across that window. That makes `lag` do two jobs for `ramp` — dead time for the others, build-up time for it. The alternative is a separate `rise_time` field. Settle before propagation is written in stack 03a.
6. **Should `strength` have a sanity ceiling?** It is an unbounded float. A model that writes ±12 has effectively asserted certainty while looking like it gave a number. A soft cap of about ±5 (roughly 1% to 99% on a coin flip) would catch that, at the cost of a rule with no principle behind it.
