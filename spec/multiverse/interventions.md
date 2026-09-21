# Interventions — the six ways to change a map

## Purpose

A user reads the map, gets to the third box, and disagrees with it. *"Fine, but Iran is struck the next day."* Before this chapter, the only honest answer was to start over and lose the comparison. After it, the disagreement is a **typed edit**: one of exactly six operations, recorded in a branch (a named, ordered list of edits over an untouched original — see [`branches-and-worlds.md`](branches-and-worlds.md)), each saying up front which part of the map it is allowed to touch. Six operations, each with a stated blast radius, is what makes the rest of the product possible: only what is downstream can move, the change can be replayed later, and every number that shifted can name the edit that shifted it.

---

## Data model

An **intervention** is one typed edit to a cause-and-effect map. *Map* and **graph** mean the same thing throughout — propositions (claims that can be checked) joined by links (arrows that say why) — and `Graph` is what the type is called in code. There are six kinds of edit and no more. Each is a small frozen pydantic model — *pydantic* is the Python library that defines and checks our data shapes; *frozen* means an instance cannot be altered after it is built, so an edit is a fact, not a mutable object.

The six are told apart by a field named `kind`. That makes them a **discriminated union**: a reader — or the TypeScript types generated for the browser — can look at `kind` alone and know which of the six shapes the rest of the object has. No guessing from which fields happen to be present.

Two identifier types appear below and neither is defined here. `PropositionId` — the identifier of a claim — is defined in [`../graph/proposition.md`](../graph/proposition.md), and `LinkId` — the identifier of one arrow — in [`../graph/link.md`](../graph/link.md). Both are plain strings; our code mints them and the model never invents one (decision record 0003). The Hormuz fixture uses readable ones, and so does this chapter: `H`, `C`, `B`, `R`, `S`, `M1`, `M2`, `N1`.

`Proposition`, `Link` and `Belief` are defined in [`../graph/proposition.md`](../graph/proposition.md), [`../graph/link.md`](../graph/link.md) and [`../graph/belief.md`](../graph/belief.md). Throughout this chapter `S → H` is shorthand for "the link that runs from proposition S to proposition H".

### The six classes

```python
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Proposition, Link, Belief, PropositionId and LinkId are defined in ../graph/.


class Do(BaseModel):
    """Suppose a claim is true — and cut it loose from whatever would have caused it.

    This is what a hypothesis is. The user is pulling a lever, not reporting news, so
    nothing upstream of the claim may move: supposing the strait opens must not quietly
    raise the odds that a diplomatic deal happened (INV-3). To record something that
    actually happened, use `Observe` instead.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["do"] = "do"
    target: PropositionId = Field(
        description="The claim being supposed true or false."
    )
    value: bool = Field(
        description="True to suppose the claim holds; False to suppose it does not."
    )
    at: date | None = Field(
        default=None,
        description=(
            "The day the supposition takes effect. Links out of the target measure "
            "their delay from this day. None means the map's own start date."
        ),
    )


class Observe(BaseModel):
    """Record that a claim actually came true (or false) — this is news, not a lever.

    Unlike `Do`, the claim's causes are left connected, so learning it may also revise
    what we believe about what caused it, and therefore about everything those causes
    lead to. This is the one operation allowed to move things upstream (INV-3).
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["observe"] = "observe"
    target: PropositionId = Field(
        description="The claim that has been observed to be true or false."
    )
    value: bool = Field(
        description="True if the claim came out true; False if it came out false."
    )


class Insert(BaseModel):
    """Add a new claim to the map, together with the arrows that connect it.

    This is the '…but X also happens' move. The new claim and its arrows arrive as one
    edit, so the map is never left holding a claim that causes nothing and is caused by
    nothing.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["insert"] = "insert"
    proposition: Proposition = Field(
        description="The new claim, complete with how and when it will be checked."
    )
    links: tuple[Link, ...] = Field(
        description=(
            "The arrows that attach the new claim to the map. Each one has the new "
            "claim at one end and an existing claim at the other."
        )
    )


class Retune(BaseModel):
    """Change how hard one arrow pushes — and change nothing else about it.

    The user disagrees with the model's number on a single link. This edit reaches
    exactly one field of exactly one link: its `strength`. It cannot touch the arrow's
    mechanism, its delay, its shape, which two claims it joins, or any belief anywhere.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["retune"] = "retune"
    link: LinkId = Field(description="The one arrow whose push is being changed.")
    strength: float = Field(
        description=(
            "The new push, on a log-odds scale — the scale on which separate "
            "influences add together instead of multiplying. Signed: a negative "
            "number pushes the downstream claim toward false."
        )
    )


class Refine(BaseModel):
    """Split one claim into finer claims that must add back up to it.

    'US election goes this way' becomes a claim per state. The finer claims replace the
    original as the thing the map reasons about, and their combined likelihood has to
    equal the original's (INV-10) — otherwise splitting a claim would quietly change the
    map's answer. The type exists from stack 02; the operation is applied in stack 06.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["refine"] = "refine"
    target: PropositionId = Field(description="The claim being split.")
    into: tuple[Proposition, ...] = Field(
        description="The finer claims that replace it. At least two."
    )
    reconcile: Literal["marginalize"] = Field(
        default="marginalize",
        description=(
            "How the finer claims are made to agree with the original. "
            "'marginalize' means their combined likelihood must equal the "
            "original's, within a small tolerance."
        ),
    )


class Believe(BaseModel):
    """Record what the *user* thinks the likelihood of one claim is.

    The user's number is a first-class input, not a correction. It is written to the
    user's own slot and sits beside the model's and the market's; it never overwrites
    either of them and they are never averaged together (INV-11). In this version it is
    not pushed through the map — see Behaviour B4.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["believe"] = "believe"
    target: PropositionId = Field(description="The claim the user is putting a number on.")
    belief: Belief = Field(
        description=(
            "The user's likelihood with its honest range. Its owner must be 'user'; "
            "a belief owned by the model or by a market is rejected."
        )
    )

    @field_validator("belief")
    @classmethod
    def owner_must_be_user(cls, value: Belief) -> Belief:
        """A `believe` edit may only ever carry the user's own number."""
        if value.owner != "user":
            raise ValueError(
                "a believe intervention carries the user's own belief; "
                f"this one is owned by '{value.owner}'"
            )
        return value


Intervention = Annotated[
    Do | Observe | Insert | Retune | Refine | Believe,
    Field(discriminator="kind"),
]
"""One typed edit to a map. Read the `kind` field to know which of the six it is."""
```

The `owner_must_be_user` check above is a **field validator** — a rule pydantic runs while building the object, so a `Believe` carrying the model's number cannot be constructed at all. It is not a later validity check; there is no valid map in which it is acceptable, so it fails at the door.

### The table of six

Two of the columns below mix two different things, so they say which:

* **Structure** — fields of the map itself: which claims and arrows exist, and what is written on them.
* **State** — which likelihoods may come out different from the base world once beliefs have been propagated. *How* they come out different is arithmetic, and arithmetic belongs to `propagation.md` (stack 03a).

| Operation | What the user sees | Plain meaning | May change | Must never change |
|---|---|---|---|---|
| `do` | Button **Suppose this is true** (or **Suppose this is false**); badge **Supposed · date** | Pull a lever. Fix the claim's value and cut it loose from its causes | *Structure:* removes the target's incoming arrows. *State:* the target and everything downstream of it | Any ancestor of the target — anything that could have caused it (INV-3). Anything that is neither the target nor downstream of it (INV-4). The target's wording, resolution criteria or evidence |
| `observe` | Button **This happened**; badge **Happened · date** | Report news. Fix the claim's value and leave its causes connected | *Structure:* nothing — it adds, removes and rewrites nothing. *State:* the target, everything downstream of it, **and** what we believe about its causes, and therefore anything downstream of those causes | Any claim outside `observe`'s affected set: anything that is not the target, one of its descendants, one of its ancestors, or a descendant of one of those ancestors (INV-4, read with INV-3). Every field of every claim and every arrow |
| `insert` | Button **Add a claim**, hinted as "…but this also happens"; badge **Added** | Add a claim and the arrows that attach it | *Structure:* adds one proposition and its links. *State:* the new claim and everything it causes | Any existing proposition's fields. Any existing link's fields. Anything not downstream of the new claim |
| `retune` | Button **Change this push**; badge **Retuned**, read back as "you moved this arrow from +0.7 to +0.3" | Disagree with one number on one arrow | *Structure:* the `strength` field of one link. *State:* everything downstream of that link, and — where an observation is in force — everything that observation is evidence about (the rule under the affected-set table) | Every other field of that link — mode, lag, shape, half-life, rationale, sources, provenance, and which two claims it joins. Every other link. Every proposition. Every belief |
| `refine` | Button **Split this claim**; badge **Split** | Replace one claim with finer claims that add back up to it | *Structure:* the target and the finer claims that stand in for it. *State:* the finer claims, and the target's combined likelihood only within tolerance | The target's combined likelihood beyond that tolerance (INV-10). Anything not downstream of the target. *Applied in stack 06; the type exists now, and no control on screen offers it* |
| `believe` | Button **My own number**; no badge — the three-up belief chip is the badge | Record the user's own likelihood on one claim | *Structure:* `beliefs.user` on one proposition — nothing else, anywhere | `beliefs.model` and `beliefs.market` on that claim or any other (INV-11). Every other field. Every downstream likelihood — it is not propagated in this version |

The code names — `do`, `observe`, `insert`, `retune`, `refine`, `believe` — are what the data and this document call the six operations, and none of them is ever shown to a user. The buttons and badges above are the interface's words; they are listed together, and changed first, in [`../vocabulary.md`](../vocabulary.md) under *Interface words*.

### Preconditions — what must be true of the map before each edit applies

| Operation | Preconditions |
|---|---|
| `do` | `target` names a proposition present in the map |
| `observe` | `target` names a proposition present in the map |
| `insert` | `proposition.id` is **not** already present. Every link in `links` has the new proposition at one end and a present proposition at the other, and carries an identifier not already in use. The resulting map still has no loops once reflexive links (a market feeding back on the world) are set aside — INV-6, owned by [`../graph/validity.md`](../graph/validity.md) |
| `retune` | `link` names a link present in the map — including one added by an earlier `insert` in the same branch |
| `refine` | `target` names a present proposition; `into` holds at least two propositions whose identifiers are not already in use; `reconcile` is `marginalize` |
| `believe` | `target` names a present proposition. The belief's owner is `user` and its numbers satisfy `0 ≤ low ≤ p ≤ high ≤ 1` — both checked by the classes themselves, before any map is consulted |

**Where these are checked, and what failure looks like.** Preconditions are properties of a *map*, so no pydantic class can check them; they are checked by `apply`, the function that folds a branch onto a base map, which arrives in **stack 03a**. A failed precondition returns a `Violation` — a stable machine-readable code, the subject's identifier, and a plain sentence naming the claim or arrow by its words — exactly as a rejected proposal does (see [`../graph/validity.md`](../graph/validity.md)). It is never a silently dropped edit and never a half-applied branch. Reject, never repair: a silently dropped arrow is precisely "not knowing why it did that". In **stack 02** only the six shapes exist, so only the shape-level checks above run.

**Decided 2026-09-17 — four codes for a refused edit, and `apply` stops at the first edit that does not fit.**

| Code | What it means |
|---|---|
| `unknown_target` | The edit names a claim this map does not have |
| `unknown_link` | It names an arrow this map does not have |
| `duplicate_id` | An `insert` reuses an identifier already on the map |
| `edit_not_applicable` | This edit cannot be folded onto this map as written: splitting a claim (`refine`, which is not built until stack 06); an `insert` whose arrow touches neither end of the new claim; a chain of parent branches that loops or names a branch that is not there |

`apply` folds edits in order and **stops at the first edit that does not fit**, reporting **every** violation *that edit* produced — not the first fault, and not the faults of the edits after it. The reason is ordering: a later edit may name a claim or an arrow the failed edit would have added, so everything after the failure would report faults that are artefacts of the stop rather than the user's mistakes. One broken edit, all of its reasons, nothing invented. The four codes join the map faults in `ViolationCode`; [`../graph/validity.md`](../graph/validity.md) lists them.

### Trigger links and sustain links when an edit lands

Every arrow is one of two kinds, and an intervention treats them differently. A **trigger** link is a domino: it fires once when its cause becomes true, and the effect stays put and fades on its own — standing the earlier domino back up does not stand the later one back up. A **sustain** link is a desk holding an apple: the effect exists only while the cause holds, so remove the cause and the effect **retracts**. In the Hormuz branch, `do(S, true)` makes the strike true on 2026-10-02, and three arrows out of S go live: S → B and S → C and S → H, the last two of them sustain. Because S → H is a sustain link pushing against H, the user's supposition is **withdrawn** from that day — even though they asserted it with `do(H)` the day before; the desk was removed. Withdrawn is not the same as pushed down: S → H carries a three-day delay, so from 2026-10-02 H simply reads its own prior again, and the push itself lands on 2026-10-05. H → C is also a sustain link, so it retracts with H, while S → C now holds C down directly. H → B, by contrast, is a trigger that already fired on 2026-10-01: that domino stays fallen, and retracting H does not stand it back up; it fades on its own half-life while S → B pushes B the other way. Which arrows stay live and which retract is settled here; by how much each one moves a number is `propagation.md`'s business (stack 03a).

---

## Behaviour

Worked on the Strait of Hormuz map. Its claims, in the wording the fixture uses: **H** *Strait of Hormuz open to unrestricted commercial transit for 14 consecutive days* (the hypothesis) · **C** *Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%* · **B** *Brent crude settles below $68 for five sessions* · **R** *OPEC+ announces output restraint* · **M1** a Polymarket contract on Brent resolving YES · **M2** the energy fund XLE underperforming the S&P 500 fund SPY by more than 3% over 20 days. The map's "today" is 2026-10-01.

### B1 — "Suppose Hormuz opens"

The user types the hypothesis. The tool records one edit:

```python
Do(target="H", value=True, at=date(2026, 10, 1))
```

`do` cuts H loose from its causes. In the base map H is the hypothesis and has no causes, so the cut removes nothing. That is not a technicality — it is why B2 can hang a new arrow onto H at all, and why the order of the edits in B2 matters.

Everything downstream of H may now move: C through the sustain arrow, B through the trigger arrow and again through C, then M1, M2 and R through B. Nothing upstream of H moves, because there is nothing upstream of H. The user sees the verb **Suppose this is true** on the box, not "this happened".

### B2 — "…but Iran is struck the next day"

This is the branch `hormuz-then-strike`, three edits in this order.

**Step 1 — `Do(target="H", value=True, at=2026-10-01)`.** As B1.

**Step 2 — `Insert(...)`.** A new claim **S**: *a confirmed military strike on Iranian territory, reported by at least two of AP, Reuters and AFP*, with its own resolution criteria and date like every other claim. It arrives with three arrows:

| Arrow | Mode | Strength | Why |
|---|---|---|---|
| S → B | trigger, a spike that fades | −2.4 | A strike restores the war-risk premium in the oil price faster than transit data removes it |
| S → C | sustain, a step | −2.0 | Underwriters reprice on the threat, not on transit counts |
| S → H | sustain, a step | −1.9 | A reopening is sustained by the *absence* of hostilities, not by the opening event |

**Read the signs.** Strength is signed, on a log-odds scale — the scale on which separate pushes add together instead of multiplying — and the sign always says which way the arrow pushes the claim at its head *toward coming out true*. All three are negative, and each against a different claim: the strike pushes against "Brent settles below $68", against "the premium falls below 0.4%", and against "the strait is open". The numbers are illustrative, carried over from `docs/research/02-causal-modeling-formalisms.md` §3, and the fixture marks them `argued`, not `documented`.

The precondition holds: S is not already on the map, each arrow has S at one end and an existing claim at the other, and none of them closes a loop. Note what `insert` did *not* do: it did not touch a single field of H, B or C. It only added.

**Step 3 — `Do(target="S", value=True, at=2026-10-02)`.** The strike is supposed true, one day later.

**The showcase — S → H.** `do(H)` in step 1 cut the arrows that were coming into H *at that moment*. S → H did not exist yet; it was inserted afterwards, so it is live. Because S → H is a **sustain** arrow — the reopening needs the absence of hostilities the way an apple needs the desk — the supposition is **withdrawn** the day the strike becomes true, even though the user asserted it. This is the ordering rule in one sentence: *`do` cuts the arrows that exist when it is applied; an arrow inserted later is live.* It is why the branch lists `do(H)` first.

**Two different days, and the difference is the point.** H passes through three named states, and the day the supposition ends is not the day the push arrives (decision record 0014):

| State | When | H reads | Why |
|---|---|---|---|
| **supposed** | 2026-10-01 | true in every simulated world; the tile shows the words, not a number | The user pulled a lever and nothing live pushes back |
| **withdrawn** | 2026-10-02 to 10-04 | `.36` — its own prior, `.35`, read back — labelled *withdrawn — no live push yet* | The **cause** of the opposing arrow became true on the 2nd, so we stop taking the user's word. S → H carries a three-day delay, so nothing has pushed yet |
| **pushed** | from 2026-10-05 | about `.08` | The delay has run and S → H's −1.9 push lands on the prior |

A supposition ends on the day its undermining **cause** becomes true, not on the day that arrow's push arrives. Tying it to the arrival would tie *do I still take your word for this* to a delay parameter — change the lag from three days to thirty and the supposition would silently outlive the news.

**Why that is the right rule: a `do` is a timed assertion.** `Do(target="H", value=True, at=2026-10-01)` says *H holds from the 1st*. It does not say *H is sealed for ever, whatever you tell me next*. That reading is the one the rest of the engine already assumes: every arrow carries a delay, a shape and, for a spike, a half-life, so the map is worked through along a timeline and a claim's value is something that holds over a stretch of days rather than a constant (decision record 0005). An arrow that arrives on the 2nd is then simply a later event acting on a later day. The alternative — sealing the target against everything inserted afterwards — would let the user's first edit silently veto their third, which is the opposite of what they asked for, and it would delete the showcase.

**INV-3 is untouched by this.** `do(H)` still moves nothing upstream of H; its own reach is H and what H causes. H's movement on the 2nd is not attributed to `do(H)` at all. It belongs to the two edits that produced it — `Insert(S, …)` and `Do(S, …)` — whose affected set includes H, because the insert made H a descendant of S. Every claim that moved can still name the edit that moved it, which is the property the whole branch mechanism exists to keep.

**And the override is visible (UX-14).** A claim that was supposed true and has since been pushed back down is never drawn as plainly true. H's tile reads **Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"**, naming the edit responsible, and the branch panel lists the three edits in the order they were made. On the 2nd to the 4th the badge sits beside `.36` and the words *withdrawn — no live push yet*; from the 5th it sits beside `.08`. (Those are the engine's own numbers at the fixture's seed. H's prior is `.35`; a reported likelihood sits a hair above its prior below `.5`, for the reason [`propagation.md`](propagation.md) gives.) The rule above is surprising if you meet it in a number and obvious if you can read the sequence, so the sequence is on the screen.

**The other half of the showcase — H → B.** H → B is a **trigger**: on 2026-10-01 it fired, B fell, and that domino stays fallen. Retracting H on 2026-10-02 does not un-fall B; the spike simply fades on its own half-life from then on, while S → B pushes B back the other way. One branch, both kinds of causality — the sustaining kind and the sequential kind — which is exactly the distinction in `docs/initial-brainstorming.md`.

Meanwhile H → C, a sustain arrow, retracts along with H, and S → C holds C down on its own account. The arrows out of B — to M1, M2 and R — are triggers that already fired on B's first move and likewise do not un-fire.

### B3 — "I think the model is wrong about this arrow"

The user opens the arrow C → B — *cheaper insurance lowers delivered cost, a week behind* — and thinks the model has made too much of it. The model puts that push at **+0.7**: B is the claim "Brent settles below $68", and cheaper insurance makes it *more* likely, so the sign is positive. The user moves it to **+0.3** — from +0.7 to +0.3, a softening, not a reversal.

```python
Retune(link="C->B", strength=0.3)
```

One number on one arrow changes. Its mechanism sentence, its delay, its step shape, its sources, its provenance and the two claims it joins are all untouched, and so is every other arrow and every claim. Everything downstream of that arrow — B, then M1, M2 and R — may move; nothing upstream of it may.

Watch the sign. Going to −0.4 would not be a weaker version of the same claim; it would assert the opposite mechanism — that cheaper insurance makes cheap oil *less* likely — which is a different argument and needs a different rationale, not a slider. See [`../graph/link.md`](../graph/link.md).

`retune` is not "edit this arrow" and it is not "change a belief". It reaches one field. If the user wants a different mechanism, that is an `insert` of a different arrow and a conversation about the old one; if the user wants a different likelihood on a *claim*, that is `believe`.

Note what stays honest here. The arrow's `provenance` field still says where the model's number came from; it is the **branch** that records that the user changed it, and that is what the workbench reads to mark the arrow as yours. The patch is the audit trail — see Open questions.

### B4 — "My own number"

The model puts M1 — the Polymarket contract resolving YES — at a likelihood the user thinks is too generous.

```python
Believe(target="M1", belief=Belief(p=0.30, lo=0.20, hi=0.45, owner="user"))
```

This writes `beliefs.user` on M1 and nothing else, anywhere. The model's number and the market's price stay exactly where they were, and the box now shows three numbers side by side rather than one blended one — the gap between them is the point of the product (INV-11). The edit lives in the branch like any other, so it replays and it diffs.

In this version it is **not propagated**: the user's number does not flow on to anything downstream of M1. That is decision record 0004's choice, taken deliberately — propagating the user's whole worldview is a real feature with its own design, and it is scheduled for stack 06. Until then the honest thing is to show the user's number beside the model's rather than half-mixing the two.

### B5 — "This happened" is not "suppose"

Take C — *Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%*. Unlike the hypothesis, C has a cause on the map: H holds it up through a sustain arrow.

| | `Do(target="C", value=True)` | `Observe(target="C", value=True)` |
|---|---|---|
| What the user means | "Assume insurers have repriced, whatever the reason" | "The premium printed below 0.4% this morning" |
| C's incoming arrows | Cut for this branch | Left connected |
| H, upstream | Unchanged. We assumed a fact about insurance; we learned nothing about the strait | May rise — a cheap premium is evidence the lane really is open |
| B, downstream of C | May move, through C → B | May move, through C → B **and** again through H's own arrows, because H moved |
| The map's honesty | A lever the user pulled | Evidence the world supplied |

They differ because one is an act and the other is information. Supposing the strait opens must not quietly raise the odds that a diplomatic settlement happened; *learning* that the strait opened should. Most tools blur these two into one "set this value" control, and the blur is invisible in the result — which is why the two are separate verbs on the box here and never merged (INV-3, anti-pattern 3 in `PRODUCT_REQUIREMENTS.md` §10).

---

## INVARIANTS

Each is a statement true for every input a named generator can produce, and each names the automated test that checks it. Generators live in `backend/tests/strategies.py`: `graphs()` yields random **valid** maps, `interventions(graph)` yields interventions whose subjects exist in that map, `beliefs()` yields likelihoods with their ranges. Tests live in `backend/tests/unit/domain/test_patches.py` unless noted.

Anything that needs `apply` — the function that folds a branch onto a base map — lands in **stack 03a**, because `apply` does not exist in stack 02. Stack 02's tests are the shape-level ones: round trip, discriminator, and the `Believe` owner rule.

This chapter uses the local numbers `INV-multiverse.1` through `.5`; [`branches-and-worlds.md`](branches-and-worlds.md) continues at `.6`.

**INV-3 — assert is not observe (product invariant).**

* For all maps `g` from `graphs()` and all `Do` interventions `d` from `interventions(g)` with target `n`: in the world built from `g` and the branch `[d]`, every ancestor of `n` — every claim from which a path of arrows reaches `n` — serializes to bytes identical to its counterpart in the base world. Test: `test_do_leaves_ancestors_unchanged`. **Stack 03a.**
* For all maps `g` from `graphs()` that contain a claim `n` having at least one parent whose likelihood is strictly between 0 and 1: the world built from `[Observe(target=n, value=True)]` differs from the base world on at least one ancestor of `n`. This is a *capability* claim — `observe` is the one operation permitted to move things upstream — so the generator is filtered to maps where an ancestor can move at all. Test: `test_observe_may_update_ancestors`. **Stack 03a.**

**INV-4 — locality (product invariant).** One principle: *an intervention changes only what is still connected to its subject in the graph the edit leaves behind.* The subject is the claim or the arrow the edit names. The phrase *the graph the edit leaves behind* is what does the work: some operations cut arrows, and once an arrow is cut, what was on the far side of it is no longer connected to anything.

**Decided 2026-09-17 — the map the engine works through is the map with feedback arrows set aside.** This rule is written here once and every other chapter cites it rather than deciding it again.

A feedback (`reflexive`) arrow — a market changing the world it is measuring — is carried as **data** and is never worked through in this version; stack 06 unrolls them in time. So:

* Anything that asks **what can move** reads the map with feedback arrows set aside: the affected set below, the diff's states, the order likelihoods are worked through in, the columns of the layout.
* Anything that asks **what can I walk to** reads the whole map, feedback arrows included: the hover lens, the keyboard's `h` and `l`, the outline.

On the Hormuz map this is why **R** — *OPEC+ announces output restraint*, reached only by the feedback arrow `B → R` — is provably **untouched** by the strike branch, while a user can still hover the wire and walk to it.

The test is `test_a_feedback_arrow_never_carries_a_change`, in `backend/tests/unit/domain/test_patches.py`: for all maps from `graphs()` that contain a feedback arrow, and all edits from `interventions(g)` whose subject reaches a claim *only* through that arrow, the claim is byte-identical in the two worlds. It exists to fail loudly the day stack 06 unrolls feedback arrows — and **this paragraph is the one sentence to change** when it does.

Stated for the test: for all maps `g` from `graphs()` and all interventions `i` from `interventions(g)`, every proposition outside `i`'s **affected set** serializes to identical bytes in the base world and in the branch world. The affected set is the operational form of the principle — one row per operation, each row a consequence of what that operation does to the graph:

| Operation | Affected set | Why that set, and no wider |
|---|---|---|
| `do` | The target and its descendants | Cutting the target's incoming arrows separates it from every claim that is not downstream of it, so nothing else is still connected to it |
| `observe` | The target, its descendants, its **ancestors**, and the descendants of those ancestors | Nothing is cut: the structure is left whole, so what is learned travels back up the arrows into the causes and out again along everything they lead to |
| `insert` | The new claim and its descendants | The edit only adds; no existing claim's fields are touched, and nothing upstream of the new claim can feel it |
| `retune` | The claim at the arrow's head, and that claim's descendants — **and, where an observation is in force, everything it is evidence about** (see below) | The edit reaches one field of one arrow, so the earliest thing that can move is the claim that arrow points at |
| `refine` | The target's internals — the finer claims that stand in for it | Their combined likelihood equals the original's within tolerance (INV-10), so the map outside the target sees the same number it saw before |
| `believe` | One slot on one claim: `beliefs.user` on the target | The user's number is written beside the model's and the market's and is not pushed through the map in this version (INV-11) |

**The table covers one edit on an untouched map. One rule reaches further than any row can say, and it is the principle applied twice rather than an exception to it** *(amended 2026-09-21)*:

> **An edit that can move a claim some observation was made about can move everything that observation is evidence about** — and that applies again to any further observation whose own claim has just been brought in.

An observation is not a number stored once. It is a filter re-read through the map every time the map changes: what survives is decided by the observed claim's value, and every number the observation touches is read off the survivors. So changing anything that can move the observed claim changes what the report says about all of them.

Three quite different edits reach it, and the first was missed for a whole stack.

* **Changing what the news says.** Report that a claim did not happen, then change how hard its one cause pushes it. The **cause** moves — measured on the map `test_a_retune_under_an_observation_moves_the_arrows_source` builds, `.5020` to `.4317` — because how much news about an effect says about a cause depends on how hard that cause was pushing. Nothing structural joins the edit to the cause: no arrow added, none removed, the observation's reach the same set of claims as before. The `retune` row used to permit only the arrow's head and its descendants, which would have let a tile read *untouched* over a number that had moved by `.070`.
* **Widening what the news is about.** Attach a new claim to one that was reported, and the new arrows carry the evidence further.
* **Withdrawing the news.** Suppose the very claim that was reported. A later edit on a claim overrides an earlier one, so the observation stops holding, the worlds it was throwing away come back, and everything it was evidence about moves again. **The reach of a standing observation is therefore read off the map the edit started from**, not the one it left behind: a `do` cuts the arrows into its target, so on the map afterwards the causes it has just stopped speaking about are no longer even connected to it.

A `believe` never triggers it, and that is the reason it has its own row: the user's number is not pushed through the map, so it cannot change which worlds survive.

`affected_set` takes the values already fixed and the map the edit started from, and grows the set until it stops growing. `GraphEditMachine` re-checks locality after every step against `_evidence_moved`, which works the same rule out from the shape of the map and never asks `affected_set` — a test that agreed with the code it checks would pass by agreeing with itself.

`observe` is the wide one, and it is wide for a stated mechanical reason rather than as an exception carved out to keep two invariants from fighting: learning something is done by keeping only the simulated worlds consistent with what was learned, and discarding worlds changes what the survivors say about the target's causes just as much as about what it causes (decision record 0005, amended 2026-09-17).

**How the test computes the affected set.** From the shape of the graph alone — `networkx`'s ancestor and descendant functions, a standard Python library for graph algorithms — over the map the edit leaves behind **with its feedback arrows set aside**, by the rule above, and **never** from the engine's own record of what it touched. A test that asked the engine which claims it had changed would pass by agreeing with itself, which is not a test.

**Every operation must name a fully separated claim.** For each of the six, `test_intervention_locality` picks at least one proposition **fully separated** from the subject — not a descendant of it, and sharing no ancestor with it, so no path of arrows and no common cause joins them — and asserts that this claim is byte-identical in the two worlds. (For `retune`, whose subject is an arrow rather than a claim, the subject is read as the claim at that arrow's head.) Without that rule the `observe` case could pass while checking nothing: its affected set is wide enough that on a small map there may be no proposition outside it at all, and an assertion over an empty set is always true. Generated maps that offer no such claim for a drawn intervention are discarded, not quietly passed.

Read with `test_observe_may_update_ancestors` (INV-3), which requires an ancestor to move, the two tests bracket `observe` from both sides: one says how far it is allowed to reach, the other says it must actually reach. Test: `test_intervention_locality`. Also re-checked after every step of the `GraphEditMachine` state-machine test described in [`branches-and-worlds.md`](branches-and-worlds.md). **Stack 03a.**

**INV-10 — refinement adds back up (product invariant).** For all maps `g` from `graphs()` and all `Refine` interventions from `interventions(g)`: the combined likelihood of the finer claims equals the original claim's likelihood within the stated tolerance. Test: `test_refine_marginalizes_to_parent`. **Stack 06**, with the operation itself.

**INV-11 for `believe` — three voices (product invariant).** For all maps `g` from `graphs()` and all `Believe` interventions `b` from `interventions(g)`: in the result of applying `[b]` to `g`, the target's `beliefs.user` equals `b.belief`, and every other field of every proposition and every link — including that target's `beliefs.model` and `beliefs.market` — is byte-identical to `g`. Test: `test_believe_touches_only_user_belief`. **Stack 03a.** (The wider INV-11 rule that no function anywhere derives one number from two owners is `test_beliefs_never_merged`, owned by [`../graph/belief.md`](../graph/belief.md).)

**INV-multiverse.1 — no edit lands on a claim that is not there.** For all maps `g` from `graphs()` and all interventions `i` from `interventions(g2)` where `g2` is an independently drawn map (so subjects usually do not match): applying `[i]` to `g` either succeeds or returns at least one `Violation` naming the missing subject. It never raises, never partially applies, and never returns a map in which the subject is absent. Test: `test_apply_rejects_unknown_subject`. **Stack 03a.**

**INV-multiverse.2 — `retune` reaches one number.** For all maps `g` from `graphs()` and all `Retune` interventions from `interventions(g)`: in the result, the named link's `strength` equals the new value, and every other field of that link, every other link, and every proposition serialize to bytes identical to `g`. Test: `test_retune_changes_only_strength`. **Stack 03a.**

**INV-multiverse.3 — an edit survives a round trip.** For all interventions `i` from `interventions(g)` for `g` from `graphs()`: parsing `i`'s JSON back as an `Intervention` yields an object equal to `i`, of the same class. Test: `test_intervention_round_trip`. **Stack 02.**

**INV-multiverse.4 — the discriminator does the work.** For all interventions from `interventions(g)`: parsing the JSON as the `Intervention` union yields the class named by its `kind`. A payload whose `kind` is not one of the six is rejected with an error naming `kind`, not silently coerced into whichever class happens to fit. Test: `test_intervention_discriminator`. **Stack 02.**

**INV-multiverse.5 — `believe` carries only the user's number.** For all beliefs from `beliefs()` whose owner is not `user`, constructing a `Believe` with that belief raises a validation error. Test: `test_believe_requires_user_owner`. **Stack 02.**

---

## ANTI-PATTERNS

**1. Do not offer one control that both supposes and reports.** *Because* "suppose the strait opens" and "the strait opened" imply different maps — the second should raise the odds of a diplomatic settlement upstream, the first must not — and once they are merged, no one can tell from the result which was meant. **Do** ship two operations with two verbs on the box, **Suppose this is true** and **This happened**, and say in the branch's record which one the user chose (INV-3).

**2. Do not re-prompt the model for a fresh map after an edit.** *Because* nothing is held fixed between the two versions, so the difference is the user's change plus a wash of model noise, with no way to separate them; it breaks locality (INV-4) and it breaks replay. **Do** recompute mathematically from the patch, and call the model only for `insert` — and then only to propose arrows for the one new claim, scoped to the affected part of the map and recorded in the branch.

**3. Do not use `retune` to edit anything but a strength.** *Because* an operation whose blast radius is "one field of one arrow" is the only reason the tool can promise that an arrow's mechanism, delay and sources still say what they said. A `retune` that also rewrote the rationale, or the mode, or a belief, would make every diff ambiguous. **Do** reach for `insert` when the mechanism itself is wrong, and `believe` when the disputed number is a claim's likelihood rather than an arrow's push.

**4. Do not let a user's number overwrite the model's.** *Because* the product's value is the gap between what the model thinks, what you think and what the market is pricing; average them or overwrite one with another and the gap — the entire signal — disappears (INV-11). **Do** write the user's number to its own slot with `believe`, and render all three side by side.

**5. Do not add a "delete this claim" operation.** *Because* deleting from the base map would make the base mutable, break replay, and leave every earlier branch pointing at a claim that no longer exists. There are six operations and removal is not among them. **Do** express "this is out of the picture" as `do(n, false)`, which forces the claim false. A claim shown as **killed** in a diff means exactly that — forced false — never erased from the record. *(Decided 2026-09-17: `killed` is forced false, full stop. Being cut off from the hypothesis used to count too; it is now a fact about the **path**, reported by the Inspector's path bar — "no path from the hypothesis reaches this claim any more" — rather than a state on the claim.)*

---

## Open questions

Raised 2026-09-16. Each needs Kent.

1. **Does `do` cut an arrow inserted after it?** This chapter says `do` cuts the arrows that exist *when it is applied*, so an arrow inserted afterwards is live and the strait can retract (B2). The alternative reading — that `do` seals its target against every later incoming arrow — kills the showcase. Confirm the first reading, and `propagation.md` (stack 03a) encodes it.
   **Decided 2026-09-17:** the first reading. `do` cuts only the arrows present at the moment it is applied; an arrow inserted later is live. The warrant is that a `do` is a **timed assertion** — "H holds from the 1st", not "H is sealed for ever" — which is the same reading of time the engine already uses for delays, shapes and half-lives (decision record 0005). INV-3 is unaffected: `do(H)` still moves no ancestor of H, and H's own later movement is attributed to `insert(S)` and `do(S)`, whose affected set includes H because H is now downstream of S. The consequence for the interface is UX-14 in `PRODUCT_REQUIREMENTS.md` §7: an assertion a later edit has overridden says so on the tile, and the branch shows its edits in order. See B2 and decision record 0004's amendment of the same date.
   **Extended 2026-09-17 (decision record 0014):** *which day* the supposition ends on is now settled too. It ends the day the **cause** of the first live opposing arrow becomes true — 2026-10-02 — and not the day that arrow's push lands — 2026-10-05, after S → H's three-day delay. Three named states, tabled in B2: supposed, withdrawn, pushed. While a supposition holds, the claim is true in *every* simulated world and the tile shows words rather than a number.
2. **Locality and `observe` pull in different directions.** `PRODUCT_REQUIREMENTS.md` §9 states INV-4 flatly — "everything that is not that proposition or downstream of it is byte-identical" — while INV-3 says `observe` may move things upstream. Both cannot be literally true. This chapter resolves it with a per-operation affected set (see INVARIANTS), which keeps both invariants testable. Either the product requirements' sentence gains "except for `observe`, whose affected set also includes its ancestors", or the resolution is stated somewhere Kent is happy with. **Widened 2026-09-21:** the sentence needs more than `observe`'s own row, because an observation *already in force* widens the reach of a later `do`, `insert` or `retune` as well — see the rule under the table. The shortest true form is *an edit changes only what is still connected to its subject, and — where an observation is in force — what that observation is evidence about*.
   **Decided 2026-09-17:** neither an exception nor a list of cases. INV-4 in `PRODUCT_REQUIREMENTS.md` §9 is restated as one principle — *an intervention changes only what is still connected to its subject in the graph the edit leaves behind* — under which `do` and `observe` come out differently for a reason rather than by decree, because `do` cuts arrows and `observe` does not. The per-operation table above is named there as this principle's operational form, and it is where the six sets are settled.
3. **`Do` carries an `at` date and `Observe` does not.** Deliberate? "The premium printed below 0.4% *on the 3rd*" seems to want a date as much as a supposition does. Kept as the shapes sheet has it; raising rather than settling.
   **Decided 2026-09-17: leave it.** You can only observe the past, and the window starts today — so no date means day zero, which is exactly right: whatever day the premium actually printed, we know it by the time the window opens. `Do` needs a date because a supposition can be about the **future**: "suppose the strait opens on the 1st" is a statement about a day that has not happened, and the arrows out of it measure their delays from that day.
4. **A user's retune leaves the arrow's `provenance` crediting the model.** `retune` reaches one field, so `provenance` still reads `argued` after the user types a number. This chapter's answer is that the branch records authorship and the workbench reads it from there. If Kent would rather see `provenance: "user"` on the field itself, `retune` becomes a two-field operation and the table of six must change.
   **One fact that was not available when this was asked, added 2026-09-21.** Provenance now does a second job: it sets how wide each version of the map draws that arrow's push ([`propagation.md`](propagation.md)). That might have made this question expensive to get wrong — except that `argued` and `user` are given **the same width**, deliberately, because a person's own judgement and a stated mechanism are backed the same amount by nothing. So whichever way this is settled, not one number moves. It stays a question about who gets the credit on screen.
5. **No violation codes exist for a rejected edit.** The fifteen codes in [`../graph/validity.md`](../graph/validity.md) describe invalid *maps*, not rejected *edits*: nothing covers "the target is not on this map", "that identifier is already in use", or "no such arrow". Three codes — `unknown_target`, `duplicate_id`, `unknown_link` — look needed before `apply` ships in stack 03a. **None of them exists today**; they are a proposal, and nothing in this chapter assumes them.
   **Decided 2026-09-17: four, not three.** The three above, plus **`edit_not_applicable`** — "this edit cannot be folded onto this map as written" — which carries the three cases that are not a missing name: `refine`, which is not built until stack 06; an `insert` whose arrow touches neither end of the new claim; and a chain of parent branches that loops or names a branch that is not there ([`branches-and-worlds.md`](branches-and-worlds.md), open question 3, decided the same day). A fourth code keeps `unknown_target` meaning exactly what it says rather than becoming the bin for everything else. The four are tabled under *Where these are checked* above and land with `apply` in stack 03a.
6. **What happens to a split claim's own arrows?** `Refine.into` carries whole propositions, which means identifiers, which our code mints and the model does not (decision record 0003). When a claim is split, are its existing arrows rewired to every finer claim, or must the split restate them? Stack 06 owns the answer; the type ships now, so the answer changes nothing already built.
7. **Interface wording for the first two verbs.** Decision record 0004 calls them "assume" and "learn"; this chapter writes **Suppose this is true** and **This happened**, which read better on a box. `spec/workbench/` owns the final copy; whichever wins, `spec/vocabulary.md` should carry it.
   **Decided 2026-09-17:** this chapter's pair wins, for all six operations and their badges, and `spec/vocabulary.md` now carries the full list under *Interface words*. The two headline verbs are **Suppose this is true** (badge **Supposed · date**) and **This happened** (badge **Happened · date**). Record 0004's "assume" and "learn" are corrected in place, dated. One badge has no button behind it: **Retracted · date · by "…"**, which is derived, and which UX-14 requires wherever a later edit has overridden an assertion.
8. **Test-name drift between two decision records.** Record 0004's Confirmation lists `test_observe_may_change_ancestors` and `test_refine_marginalizes`; record 0008's table lists `test_observe_may_update_ancestors` and `test_refine_marginalizes_to_parent`. The higher-numbered record wins, so this chapter uses 0008's names; record 0004 should be corrected in place.
   **Decided 2026-09-17:** corrected in place. Record 0004's Confirmation now names record 0008's four tests — `test_apply_empty_is_identity`, `test_patch_concat_equals_sequential_apply`, `test_observe_may_update_ancestors` and `test_refine_marginalizes_to_parent` — and its amendment section says so. Nothing in this chapter changes.
