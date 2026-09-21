# Proposals — one claim at a time, accepted or refused

## Purpose

Before this chapter, a map had to be written by hand. After it, a person types one sentence — *"The Strait of Hormuz is going to open next week"* — and watches a map build itself, one claim at a time, with every refusal visible on the way past.

The rule that makes that safe is old and is not reopened here: **the model proposes; our code disposes** (decision record 0003). This chapter is what that rule looks like as a data shape. The model is asked one question at a time and hands back **one proposal**: a claim with the arrow that put it there, or an arrow between two claims already on the map, or a stop. It cannot mint an identifier, cannot say where its own numbers came from, and cannot return a list — not because we ask it not to, but because **the fields do not exist**. Our code then checks the map that proposal would leave behind, and either mints it or refuses it with every reason at once. A refusal is an event the user sees, not an error the user is spared.

*Map* and *graph* are the same thing throughout: `Graph` is the type's name, *map* is what a person sees.

---

## Data model

All of these are pydantic models — pydantic being the Python library we use to define a data shape and check anything claiming to be one. They live in `backend/src/katalyst/engine/proposal.py`, beside the pipeline, **not** in `domain/`: they are the shape of a question we ask a model, and the domain layer knows nothing about models.

Three types are imported from the domain layer unchanged, because a proposal that fills them wrongly should fail in one place rather than two: `Resolution` (how a claim gets settled — the test, who applies it, by when), `BaseRate` (how often this kind of thing has happened before: `k` out of `n`, with a named reference class), and the two payoff shapes, `ContractPayoff` and `PricePayoff`. They are defined in [`../graph/proposition.md`](../graph/proposition.md).

### What the model may return

```python
# engine/proposal.py — what the model is allowed to return. One of three.
class ClaimProposal(BaseModel):
    kind: Literal["claim"]
    claim: str                       # the sentence, as a person would say it
    claim_kind: Literal["event", "market", "not_tradeable"]
    resolution: Resolution           # criteria, judge, resolve-by (INV-1)
    prior: Ranged                    # p, lo, hi. No owner field: we stamp "model"
    base_rate: BaseRate | None
    payoff: ContractPayoff | PricePayoff | None   # required when claim_kind == "market"
    not_tradeable_reason: str | None              # required when claim_kind == "not_tradeable"
    cause: str                       # the identifier of a claim ALREADY on the map
    link: LinkDraft                  # the arrow from that cause into this new claim

class LinkProposal(BaseModel):
    kind: Literal["link"]
    source: str                      # both ends already on the map
    target: str
    link: LinkDraft

class Stop(BaseModel):
    kind: Literal["stop"]
    why: str                         # one sentence, shown in the transcript

class LinkDraft(BaseModel):
    mode: Literal["trigger", "sustain"]
    strength: float
    lag: int
    shape: Literal["impulse", "step", "ramp"]
    half_life: int | None
    rationale: str
    sources: tuple[SourceDraft, ...] # NO provenance field, and no identifier field

Proposal = Annotated[ClaimProposal | LinkProposal | Stop, Field(discriminator="kind")]
```

**`Proposal` is a discriminated union**: a reader — and the TypeScript types generated for the browser — tells the three shapes apart from the single `kind` field rather than guessing from which other fields happen to be present. It is the same pattern the six interventions and the two payoffs already use.

**A draft's `lag` and `half_life` are whole days; the domain's are days as a number.** A model is asked for *two days*, not for *two and a half*; `Link` allows the half day because arithmetic on a timeline needs it. The widening happens on the way in, beside the other four things we stamp, and it is the only shape change between a draft and the arrow it becomes.

Two small shapes the block above names and does not define:

```python
class Ranged(BaseModel):
    """A likelihood and the range around it, with nobody's name on it.

    The model gives three numbers and no owner, because whose number this is
    is a fact about our pipeline: every likelihood a proposal carries is
    stamped `owner="model"` by us on the way in. `lo` and `hi` are the 10th
    and 90th percentiles of the likelihood itself — how sure we are of the
    number, not how much the world can move (decision record 0014).

    This shape must never grow an `owner` field. The moment it has one, a
    model can hand us a number wearing the user's name on it.
    """

    model_config = ConfigDict(frozen=True)

    p: float = Field(ge=0.0, le=1.0, description="How likely the claim is to come out true.")
    lo: float = Field(ge=0.0, le=1.0, description="The bottom of the range. Never above `p`.")
    hi: float = Field(ge=0.0, le=1.0, description="The top of the range. Never below `p`.")

    @model_validator(mode="after")
    def _range_is_ordered(self) -> "Ranged":
        """Low at most the likelihood, the likelihood at most high."""
        if not (self.lo <= self.p <= self.hi):
            raise ValueError(
                "a range must satisfy low <= likelihood <= high; got "
                f"low={self.lo}, likelihood={self.p}, high={self.hi}"
            )
        return self


class SourceDraft(BaseModel):
    """An address the model says backs an arrow, before we have checked it.

    It is a *claim about a document*, not a document. Our code decides whether
    it becomes a real `Source`, and it becomes one only if the search tool
    itself returned that address in the same call ([`grounding.md`](grounding.md)).

    There is deliberately no `retrieved` field. That day is the day *our*
    retrieval step fetched something, which is a fact about us, so a model
    must have no way to write it.
    """

    model_config = ConfigDict(frozen=True)

    url: str = Field(description="One address that opens, not a search query.")
    # No title either: the title a reader sees is the one the search tool itself
    # returned for that address, which is the honest source of it. A title the model
    # typed would be a second copy that nothing reads (dropped 2026-09-17).
```

### The three things the model is structurally unable to do

1. **Mint an identifier.** There is no `id` on `ClaimProposal` and none on `LinkDraft`. A new claim's identifier is minted by `engine/ids.py`'s `mint_id()`, which needs a clock and randomness and therefore cannot live in the pure domain layer. An arrow's identifier is minted the same way.
2. **Declare its own provenance.** There is no `provenance` on `LinkDraft`. Where an arrow came from is a receipt we write from what actually happened — [`grounding.md`](grounding.md) owns the rule, and `grep -rn "provenance" backend/src/katalyst/engine/proposal.py` finding nothing is a line on the done-list.
3. **Return more than one thing.** There is no list anywhere in the union. One call asks one question and gets one answer.

**If you ever find yourself writing a check that the model did not do one of these, the schema is wrong.** A validator for a field that does not exist is a sign the field crept back.

Three more absences follow from the same principle and are worth saying out loud. `LinkDraft` has **no `reflexive` field**, so a generated map holds no feedback arrow — nothing unrolls one until stack 06, and an arrow that closes a loop is refused rather than legalised (Open questions 4). `ClaimProposal` has **no `evidence` field**, so a generated claim carries no published items for and against; what a search result can become is a `Source` on an arrow, and nothing else ([`grounding.md`](grounding.md) B7). And no proposal names `owner`, so the three voices — model, user, market — stay ours to keep apart (INV-11).

### Naming: how a proposal points at a claim

**An existing claim is named by the identifier the prompt handed it.** The prompt lists the map so far, one line per claim: the identifier and the sentence. `ClaimProposal.cause`, `LinkProposal.source` and `LinkProposal.target` are those identifiers, copied back.

**A new claim is not named at all.** One call returns one claim plus the one arrow into it, so there is nothing else for that claim to be joined to and nothing to name it with.

Naming an identifier that is not on the map needs no special check: the candidate map then holds an arrow with an end that does not exist, and `validate` refuses it with `dangling_link` — *"The arrow out of '…' points at a claim that is not on this map."* One rule, already tested, doing a second job.

### The one shape that is not a proposal

The hypothesis and the Verify destination arrive as **sentences a person typed**, not as claims that can be checked. Turning a sentence into a claim is a different question from expanding a map, so it has its own small shape and is asked once, before expansion starts.

```python
class StartingClaim(BaseModel):
    """One sentence a person typed, turned into a claim that can be checked.

    Used wherever a person's own words become a claim: the hypothesis, the
    Verify door's destination, and the claim a person adds to a finished map
    with **Add a claim** (B8). It carries no cause and no arrow, because in
    all three the arrows are somebody else's question; and it carries no
    `claim_kind`, because none of the three is an ending — see the paragraph
    below.

    It must never carry an identifier, a provenance or an owner, for the same
    reasons a proposal must not.
    """

    model_config = ConfigDict(frozen=True)

    claim: str = Field(description="The claim in one sentence, as a person would say it.")
    resolution: Resolution = Field(description="How and when this claim gets settled, and by whom.")
    prior: Ranged = Field(description="The likelihood before anything causes it.")
    base_rate: BaseRate | None = Field(
        default=None, description="How often this kind of thing has happened before, if there is an honest count."
    )
```

**Both starting claims enter as what they are.** The hypothesis is stamped `kind="hypothesis"` — a map has exactly one and the model is not asked which. The destination is stamped `kind="event"`, because a destination is where a person wants the story to *get to*, not where it *ends*: an ending of kind `market` must name a venue and a contract, which is a fact about a venue nobody has looked up yet (stack 05), and the map must still run on to an ending of its own (INV-9). The user's own likelihood from the input bar, when they gave one, is stamped onto the hypothesis as a `user` belief and is never overwritten (FR-2).

### What one call leaves behind

```python
# engine/expand.py
def expand(graph: Graph, frontier: PropositionId, *, target: str | None) -> Outcome
```

One call, one proposal, then `domain.validate` on the map that proposal would leave behind. The caps below are further arguments on the same function, with the defaults in the table; the signature above is the shape of the question — one map, one claim to expand, one destination or none.

```python
class Accepted(BaseModel):
    """A proposal that passed every rule, with the identifiers we minted for it."""

    kind: Literal["accepted"]
    proposition: Proposition | None   # the new claim; None when an arrow alone was proposed
    links: tuple[Link, ...]           # its incoming arrows, provenance written by us
    sources_dropped: tuple[str, ...]  # addresses the model cited that the search never returned
    base_rate_dropped: str | None     # the reference class of a count nothing the search returned backed


class Refused(BaseModel):
    """A proposal the map's own rules turned down, with every reason at once."""

    kind: Literal["refused"]
    claim_in_words: str               # what the model wrote. Never minted, never drawn as a tile
    violations: tuple[Violation, ...] # domain/validity.py's own codes and sentences


class Stopped(BaseModel):
    """The model has nothing more to add on this line.

    A `Stopped` makes **no event**. It leaves a line in the transcript, and
    the claim it closed is simply missing from the `frontier` of the next
    growth event. It must never be turned into an event of its own: a stop is
    the absence of a proposal, and an event announcing an absence is one more
    thing a reader has to reconcile with the picture in front of them.
    """

    kind: Literal["stopped"]
    why: str                          # one plain sentence, shown in the transcript


class Outcome(BaseModel):
    """What one call to the model left behind: what happened, and what it cost.

    The four counters are what `engine/receipt.py` folds into the run's one
    receipt, and what the spending cap is checked against after every call.
    An `Outcome` must never be discarded: a call that cost money and is not
    counted is money the receipt cannot account for.
    """

    result: Accepted | Refused | Stopped = Field(discriminator="kind")
    searches: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
```

**The four counters fold one-for-one onto the `receipt` event**: `input_tokens`, `output_tokens`, `cache_read_tokens` and **`searches`**. Searches are billed apart from tokens, so a reader handed only the three token counts could not re-derive `dollars` — which is why `searches` is on the receipt and not only in this chapter (cross-chapter review, 2026-09-17).

`Accepted` and `Refused` carry what the `proposal_accepted` and `proposal_rejected` events carry, and the stream adds the same two fields to both: `at`, the position in the transcript, and **`frontier`, the claims still open to expand**. Both growth events say what is still open, so a claim closed by its third refusal drops out of the frontier on the very event that refused it, and the browser can take its skeleton away at once rather than leaving a rectangle where nothing will arrive. The event shapes themselves, and their order, belong to [`streaming.md`](streaming.md).

**`at` counts transcript lines, not events**, so a client will see gaps: a `Stopped` takes a line and emits nothing. A gap in the numbers means a line stopped growing, and the `frontier` on the next growth event says which.

### The caps, and what each one does

Every cap is an argument with a default. Nothing here is a constant buried in a function.

| Cap | Default | What it limits |
|---|---|---|
| depth | 5 layers | How far a line may run from the hypothesis |
| width | 3 children | How many claims one claim may cause |
| claims | 30 | How large the map may get |
| refusals in a row | 3 | How many proposals for **one** frontier claim may be refused before that claim is closed |
| frontier claims at once | 3 | How many lines are expanded concurrently |
| searches per call | 25 | How much research one claim may do — the reference class first, then the mechanism (Kent, 2026-09-20) |
| research rounds per call | 5 | How many times the model may search, read and decide to search again |
| searches per generation | 750 | The floor, not a guess: the two above over a full map, 30 × 25. Picked at the floor ([`grounding.md`](grounding.md) B6) |
| spending per run | $15 | What one generation may cost before it stops (Kent, 2026-09-17) |

The searches cap adds no new number to the product: its floor is the claims cap times one call's research budget, and set any lower it would bind before the research caps do and starve the base rates it exists to pay for. It is deliberately loose, because **the spending cap is what protects the bill** — and with research inside a call, that cap is checked between rounds as well as between calls. The two research caps and what happens when they bind are [`grounding.md`](grounding.md)'s.

**A round holds back one call's worth of searches so the generation cap is never passed** (*decided here*, 2026-09-20). A call is told once whether it may search and can then spend up to its own budget; nothing can stop it at search twelve. So the calls of a round are allowed the tool one at a time, in frontier order, and a call is allowed only while a whole call's budget still fits in what is left. The last call's worth therefore goes unspent — the price of never passing a ceiling, and a cheap one against a number that is a floor rather than a target. The same shape of reservation is why the claims cap sizes a round to the room the map has left, rather than being read once a round and stepped over by the three answers already in flight.

Decision record 0006 *estimates* a 30-claim map at about 40 calls. The first real measurement, quoted in B5, is smaller and slower than the estimate; the rest go in the pull request and `STATUS.md`, never guessed here.

### What a prompt may and may not contain

A prompt is product text. The coordinator reads `engine/prompt.py` end to end before the pull request opens, the way any other copy on screen is read.

**May contain:** the words in [`../vocabulary.md`](../vocabulary.md), used exactly; what a claim is and what an arrow is, in the same plain words this spec uses; the map so far, one line per claim — identifier and sentence — and the arrows already drawn; which claim is being expanded, and which of its children already exist; the hypothesis; the Verify destination in the person's own words.

**May not contain:**

- **Jargon, or a word the interface does not use.** A prompt that says *node* teaches the model to answer in a word we do not print.
- **A number nobody computed.** No example strength, no example likelihood, no example lag. An example number in a prompt is an anchor the model copies, and a copied number cannot say where it came from — which is the state this product refuses to show.
- **The text of a violation.** Never, on any call (see B3). Violation text never enters a prompt.
- **An instruction asking the model to do what our code should do.** No *"do not create a loop"*, no *"do not reuse an identifier"*, no *"mark the arrow documented if you cite a source"*. An instruction that duplicates a check teaches the model to aim at passing the check instead of being right, and when the two disagree nobody can tell which was obeyed.
- **Anything that changes between calls, in the cached block.** The stable first block is marked for caching (decision record 0006), so the map so far, the frontier claim and the date belong *after* it. A run whose cache reads stay at zero is a bug, not a slow day (`test_generation_receipt_records_cache_reads`).
- **An example drawn from the map being built.** The first live run's schema descriptions used Hormuz phrasing, on a Hormuz run; an example that echoes the question is an answer handed over in advance.

### Three rules the prompt must carry, because the first live run broke all three

These are not house style. Each is a fault that was **measured** on 2026-09-17, in the first live Hormuz run; each rule was settled on 2026-09-20 on principles this spec already carried; and each is stated in the prompt in the plain words this spec uses.

1. **A claim is one standalone checkable statement, not a narrative.** The run wrote claims like *"With the strait open again, the war premium comes out of crude…"* — a sentence that carries its own cause inside it. A `claim` is what a tile can hold and a person can score on its own: *"Brent crude settles below $68 for five sessions."* **The *because* belongs on the arrow**, in its `rationale`, which is the field that exists for it. A claim that argues for itself cannot be reused by a second arrow, and it double-counts its cause — the cause is drawn on the canvas and written in the box as well.
2. **`market` means the claim's own resolution is a price or a contract outcome somebody could trade.** A step on the way to one is an `event`, however tradeable the thing at the end is. The test is mechanical: *would a venue settle this exact sentence, or would you have to translate it first?* A `market` claim carries a payoff naming what you would trade; an `event` carries none. Getting this wrong puts a payoff on a step and leaves the real ending unmarked, which is how a map stops ending anywhere you can act on.
3. **The hypothesis is a claim like any other and gets the same test, judge and date.** The run's own hypothesis came back with resolution criteria of `"Res "` and a judge of `"x "`. Both are the kind of fault nothing downstream can catch: they fit the shape, and `validate`'s rule only asks that the two are not blank — *"Res"* is not blank. Deciding that a sentence is a real test and not a placeholder is grading prose, which is the one thing we refuse to ask code to do. **So the prompt is the only place this can be got right**, and the starting call asks the same three questions, in the same words, as every other call. It is also why this rule is written down here rather than left to whoever writes the prompt.

---

## Behaviour

Worked on the assignment's first example, *"The Strait of Hormuz is going to open next week."* The claims are the ones the shipped example uses: `H` the strait open to unrestricted commercial transit for 14 consecutive days, `C` the Lloyd's war-risk premium below 0.4%, `B` Brent settling below $68 for five sessions, `R` OPEC+ announcing output restraint, `M1` a Polymarket contract on Brent below $70, `M2` the energy fund XLE against SPY, `N1` Omani-mediated talks resuming. Readable identifiers stand in for the minted ones throughout, exactly as the fixture does.

### B1 — one call, one proposal, then mint

The frontier claim is `C`. The prompt carries the map so far — `H` and `C`, with the arrow between them — and asks for one claim `C` causes, or a stop. The answer:

```
ClaimProposal(
  kind="claim",
  claim="Brent crude settles below $68 for five sessions.",
  claim_kind="event",
  resolution=Resolution(
    criteria="Front-month Brent crude futures settle below $68.00 on five sessions, "
             "consecutive or not, within the window.",
    source="ICE Brent front-month settlement prices.",
    by=date(2026, 10, 15)),
  prior=Ranged(p=…, lo=…, hi=…),
  base_rate=None,
  payoff=None,
  not_tradeable_reason=None,
  cause="C",
  link=LinkDraft(mode="sustain", strength=…, lag=7, shape="step", half_life=None,
                 rationale="Lower war-risk premiums cut the delivered cost of a Gulf cargo, "
                           "and the saving shows up in the physical differential within about a week.",
                 sources=(…,)),
)
```

Four things our code adds, and the model could not have:

| What | Where it comes from |
|---|---|
| The claim's identifier | `engine/ids.py`, `mint_id()` |
| The arrow's identifier | the same |
| `owner="model"` on the likelihood | stamped by us; `Ranged` has no owner field |
| `provenance` on the arrow | written from what the search actually returned ([`grounding.md`](grounding.md)) |

Then `domain.validate` runs on the map the proposal would leave behind — not on the proposal, on the **map**, because most of the rules are about a whole map. It comes back empty, the claim and the arrow are minted, and `proposal_accepted` goes out. `B` joins the frontier; `C` stays on it until it stops or runs out of width.

**One proposal is one thing.** A claim arrives with the arrow that put it there, because a claim with nothing causing it is not a step in a story. That is still one thing: one question, one answer (`test_expand_returns_one_proposal_per_call`).

### B2 — a refusal is an event, and every reason comes back at once

Expanding `B`, the model proposes an arrow instead of a claim: `B → H`, *"cheaper crude reduces the incentive to close the strait."* Read on its own it is a reasonable sentence. Added to the map it closes `H → B → H`, because `H → B` is already drawn.

```
Refused(
  kind="refused",
  claim_in_words="cheaper crude reduces the incentive to close the strait",
  violations=(Violation(code="cycle", subject="<the arrow that closes the loop>",
                        message='These claims form a loop with no delay in it: …'),),
)
```

The message is quoted in full in B4's worked run, step 6, because it is interface copy and the browser chapter draws it word for word.

The arrow is **not** added. The map the person is looking at is untouched, because nothing was mutated — the proposal was a candidate map, and it lost. `proposal_rejected` goes out carrying the validator's own sentence, and the browser shows it beside the map. A generation that hides its misses has deleted half the product (`test_expand_rejects_cycle`, `test_expand_surfaces_a_refusal_as_a_rejected_proposal`).

**Every reason, never the first.** A proposal with three faults comes back with three violations, in the rule table's order, because a model told one fault at a time needs one call per fault and a person told one fault at a time learns only that the tool is hostile. **And never a repair.** No dropping the arrow that closes the loop, no inventing a resolve-by date, no downgrading an arrow to make it fit ([`../graph/validity.md`](../graph/validity.md), *Reject; never repair*).

Two kinds of failure are not the validator's and arrive the same way. **A model refusal** — the vendor's safety check declines the call, and the answer comes back with a refusal stop reason and its own explanation (decision record 0006) — and **an answer that does not fit the shape**. Both become a `Refused` whose `claim_in_words` holds the plain sentence of what happened and whose `violations` is **empty**: there is no fault in a map to name, because no map was proposed. Nothing crashes and no stack trace reaches a screen (`test_expand_reports_a_malformed_answer_and_does_not_crash`). Whether those two deserve codes of their own is Open questions 3.

### B3 — after a refusal, ask again and say nothing (Kent, 2026-09-17)

Decision record 0003 originally allowed *one targeted re-prompt naming those violations*. Kent chose otherwise, and the record carries a dated amendment saying so.

**The rule: up to three fresh proposals in a row for one frontier claim, and the next call is never told what was wrong.** Three in a row closes that frontier claim; the line simply stops growing there. Each attempt is its own event, and all three are shown.

**Anything that is not an accepted proposal counts toward the three** — a rejection by the validator, a refusal by the vendor, an answer that did not fit the shape. **One rule, not three.** The cap is on attempts, because what has run out is our willingness to keep paying for this line, and that is the same whichever way the attempt failed. *Settled by the coordinator on 2026-09-17, as the one-rule reading of Kent's G4:* record 0003's amendment speaks only of proposals the validator turned down, and three separate counters would mean a line could be asked nine times while every count stayed under three.

Worked: expanding `B`, the model proposes `B → H` and is refused for the loop. The next call is the *same* call — the same map, the same frontier claim, the same prompt — with no mention of the loop, no mention of the refusal, and nothing new to read. It proposes `M2`, the pair trade, and that is accepted, which puts `B`'s count back to zero.

**Why the silence.** Violation text in a prompt steers the model toward *passing the validator* rather than toward being right, and the two are not the same target. It is the same argument that keeps the model's hands off `provenance`: the moment a check is described to the thing being checked, the check stops measuring anything (`test_a_refused_claim_is_asked_again_without_being_told_why`).

**And never for a whole map.** No code path re-prompts for the map as a whole after an edit — it breaks locality and auditability (anti-pattern 2). The single exception is drafting a claim a person asked for, over the affected subtree only, which is [`streaming.md`](streaming.md)'s `insert` route. A test reads our own source rather than trusting good intentions (`test_the_pipeline_never_reprompts_for_a_whole_map`).

### B4 — how a generation ends, and the one reason it gives

A claim of kind `market` or `not_tradeable` is an **ending**: there is nothing downstream of a trade, so an ending never joins the frontier. A generation stops when the frontier is **empty** — every line closed, whether by an ending, by a `Stop`, by a cap, or by three refusals in a row.

The stream ends with one `done` event carrying **one** of seven reasons. **The rule: the reason names what closed the last claim that was still open**, with two overrides above it. One rule, so two readers cannot get two answers.

| # | `done.reason` | Chosen when |
|---|---|---|
| 1 | `spend_cap` | **Override.** The running receipt reached the run's spending cap. Checked after every call, so nothing further is asked |
| 2 | `no_terminal` | **Override.** The map ends nowhere you can act on, even after the last ending-seeking call (B6) |
| 3 | `depth_cap` · `width_cap` · `claim_cap` | The last open claim was closed by that cap: it sat at the depth cap, it already had its full width of children, or the map was full |
| 4 | `refusal_cap` | The last open claim was closed by the refusals cap — three proposals in a row for it were refused. The map is finished, and one line was abandoned rather than ended. *(Named `model_stopped` until 2026-09-17; renamed because the model did not stop — our rules refused it — and a value must mean what it says. A model that answers `Stop` is the row below.)* |
| 5 | `reached_terminal` | None of the above: the last open claim closed because the model answered `Stop` for it. (An ending never joins the frontier, so producing one closes nothing; a line that reaches an ending is closed by the `Stop` that follows it.) The ordinary, good ending |

There is no `search_cap`. Reaching the searches cap stops **searching**, not the generation ([`grounding.md`](grounding.md) B6), so it can never be what closed a claim.

`done.reason` never carries `no_path` either. Whether a Verify run found a path is a fact about the *path*, reported once on the `verdict` event and nowhere else — two derivations of one line eventually disagree (Kent, 2026-09-17).

#### The worked run, step by step

One Hormuz generation through the Explore door, at the default caps: depth 5, width 3, 30 claims. `at` is the position in the transcript, from 0. The browser chapter draws this exact run, so nothing here is approximate.

0. **`proposal_accepted`** — the hypothesis `H`, *"The Strait of Hormuz is open to unrestricted commercial transit for 14 consecutive days"*, from the one `StartingClaim` call. `proposition=H`, `links=()` — a hypothesis has nothing causing it. `frontier=(H,)`. *Every claim the canvas draws arrives on a `proposal_accepted`, and this is the first.*
1. **`proposal_accepted`** — expanding `H`: a `ClaimProposal` for `C`, *"Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%"*, with the arrow `H → C`. `frontier=(H, C)`.
2. **`proposal_accepted`** — expanding `H`: a `ClaimProposal` for `N1`, *"Omani-mediated United States-Iran talks resume publicly"*, kind `not_tradeable` with its own stored reason, and the arrow `H → N1`. `N1` is an ending, so it never joins the frontier. `frontier=(H, C)`.
3. **`proposal_accepted`** — expanding `C`: a `ClaimProposal` for `B`, *"Brent crude settles below $68 for five sessions"*, with the arrow `C → B`. This is the call worked in full in B1, and the arrow whose source is worked in [`grounding.md`](grounding.md) B1. `frontier=(H, C, B)`.
4. **`proposal_accepted`** — expanding `H`: a **`LinkProposal`**, `H → B` — both ends are already on the map, so no claim is minted and `proposition` is `None`. `H` now causes three claims and the width cap closes it: **`frontier=(C, B)`**, and `H`'s skeleton goes on this event. *B's second incoming arrow can only arrive this way: one `ClaimProposal` brings one claim with one incoming arrow.*
5. **`proposal_accepted`** — expanding `B`: a `ClaimProposal` for `M1`, *"A Polymarket contract 'Brent below $70 on 2026-10-31' resolves YES"*, kind `market` with a contract payoff, and the arrow `B → M1`. An ending. `frontier=(C, B)`.
6. **`proposal_rejected`** — expanding `B`: a `LinkProposal`, `B → H`, *"cheaper crude reduces the incentive to close the strait"*. It closes `H → B → H`. One violation, code `cycle`, and the message word for word:

   > These claims form a loop with no delay in it: "The Strait of Hormuz is open to unrestricted commercial transit for 14 consecutive days" → "Brent crude settles below $68 for five sessions" → "The Strait of Hormuz is open to unrestricted commercial transit for 14 consecutive days". Mark the arrow where a market feeds back on the world as reflexive and give it a delay, or remove one arrow.

   `frontier=(C, B)` — unchanged, because this is only `B`'s first refusal.
7. **`proposal_accepted`** — expanding `B` again, with a prompt byte-identical to step 6's: a `ClaimProposal` for `M2`, *"The energy fund XLE underperforms the S&P 500 fund SPY by more than 3% over 20 trading days"*, kind `market` with a price payoff, and the arrow `B → M2`. An ending. `B`'s refusal count goes back to zero. `frontier=(C, B)`.
8. **no event** — expanding `C`: a `Stop`. A transcript line, and nothing on the wire.
9. **no event** — expanding `B`: a `Stop`. `B` was the last open claim, and it answered `Stop`.

Then the closing events, which carry no `at`: **`beliefs_propagated`** with the whole world, **`receipt`**, and **`done`** with `reason="reached_terminal"`, `claims=6`, `links=6`, `rejected=1`.

Two things a reader should notice. **Steps 8 and 9 leave gaps in the numbering** — a client sees 7 then the closing events, and the missing positions are the two stops. And **no event ever says "this claim is closed"**: the frontier on step 4 stopped naming `H`, and the frontier after step 7 is the last one anyone sees. When `beliefs_propagated` arrives the frontier is empty by definition, so every skeleton still on screen goes at once.

The generated map is not the shipped fixture and does not pretend to be: it has six claims where the fixture has seven, and no `B → R` feedback arrow, because `LinkDraft` carries no `reflexive` field and nothing can propose one.

### B5 — the spending cap stops the run and says what it bought

`engine/receipt.py` folds every `Outcome`'s counters into the run's one receipt, and **the running receipt is checked against the spending cap after every call — and, once a call can research, between the rounds inside a call too** ([`grounding.md`](grounding.md)). Over the cap, the generation stops where it is: `done.reason = "spend_cap"`, and one plain sentence naming what was spent and what was got — *"This run reached its spending limit of <cap>. It spent <spent> and built <n> claims and <n> arrows."* No figure is written into that sentence, because every one of its slots is filled from the receipt at run time.

What was built is kept, not thrown away: a partial map with a visible reason beats a blank screen with a silent one. The price table lives in `engine/pricing.py` and nothing else, per model, with the day it was read beside it and the `claude-api` skill named — prices change, and memory is unreliable (`test_a_run_stops_at_its_spending_cap_and_says_so`).

**The model is one setting** (Kent, 2026-09-20). The prototype runs on `claude-sonnet-5`; `claude-opus-5` is one setting away for a final recording if quality asks for it. **Nothing else in the pipeline knows which model it is** — not `expand`, not the caps, not the provenance rule — and **`Receipt.model` names the one that actually ran**, so no reader has to guess what a map came from.

**How long a call waits, and how often it tries again, are decisions** (*decided here*, 2026-09-20; both read from the `claude-api` reference bundle that day). The library's own defaults are ten minutes and two retries, over 408, 409, 429, every 5xx and every connection failure. Two retries is kept and written down — a failed request is not billed, so trying again is free, and what it costs is time. Ten minutes is not: a whole question measures about two hundred seconds and one round of it far less, so ten minutes is a hang rather than a timeout, and three attempts of it is half an hour of somebody watching a stream that will never move. **Five minutes**, which is comfortably above anything measured and bounds a whole question, retries and all, at fifteen.

**Every failure of the service is a sentence, not a crash.** A 429 or a 529 on call twenty of forty is ordinary; it used to take the whole run with it, leaving no partial map, no receipt and no `Finished` — and dropping the round's other two paid answers unread. Every error the library raises now stops at the seam and crosses it as one of ours, carrying one plain sentence a person could act on: the model is busy, the model did not answer in time, this run asked too much too quickly, this key is not allowed to ask this model. Never a class name, never a status code, never a stack trace. `expand` folds it exactly as it folds an answer it could not read — a refusal, counted toward the three in a row, shown, never repaired.

**One measurement, and it is a fact rather than an estimate.** The first live Hormuz run, 2026-09-17, on `claude-opus-5` at the default effort: **10 calls, 9 searches, $1.32, 10 minutes 54 seconds, 61% of the written tokens spent on thinking, 10 claims, 0 refused.** About one tile a minute, and sequential by nature — every call has to see the map as it stands. No figure is quoted here for `claude-sonnet-5`, on cost or on time, because none has been measured yet; both go in the pull request when they are.

The ceiling *across* runs is a working agreement kept in `STATUS.md`; nothing is stored between requests until stack 05. **Only the coordinator runs a command that spends money.**

### B6 — no ending reached: one last call, then an honest card

When expansion has stopped — the frontier empty, or every open claim capped — and the map ends nowhere you can act on, the engine makes **one last call per open claim, asking only for an ending**: a claim of kind `market` or `not_tradeable`, with no further expansion behind it. It is the same `ClaimProposal` shape and the same validation; only the question changes.

Worked: a run whose deepest claims all sit at the depth cap and are all `event`s. The last call on each open claim asks for the ending it leads to. One comes back as `N1` — *"Omani-mediated United States-Iran talks resume publicly"*, kind `not_tradeable`, with its own stored reason: no venue quotes a diplomatic round. The map now satisfies INV-9, the `no_terminal` override no longer applies, and the run reports what actually closed its last open claim — here `depth_cap`.

If that still fails, the stream ends `done.reason = "no_terminal"` and the browser says so in plain words. **The engine never writes a claim the model did not propose.** Adding a terminal ourselves to make the map legal would be a claim with no author, which is the one state this product refuses to show (`test_a_generation_that_reaches_no_ending_says_so`).

### B7 — the Verify door: a graded path, or an honest `no_path`

A Verify run carries a destination in the person's own words. It is turned into a claim by one `StartingClaim` call and added to the map **up front**, as an ordinary `event`. Every expansion call is told what it is, and expansion is steered toward it.

**Reached.** The person asks: *does the strait opening reach a Polymarket contract on Brent below $70?* The map runs `H` → `C` → `B` → `M1`. The `verdict` event carries `kind="reached"`, the path `(H, C, B, M1)`, and `product` — the multiplied-out likelihood of that path. **It is multiplied out in `engine/verify.py` today, over the likelihoods the world carries**, which is not where it belongs: reading numbers off a world is the rules layer's work, and this one sits in the pipeline only because the engine is the first thing that needed it. It moves to `domain/` in the last pull request of this stack, where the engine is gaining the path product anyway; until then the honest sentence is that the engine multiplies the world's own numbers rather than that the world hands the product over (2026-09-20). The path shown is the **best-backed path**: over every path from the hypothesis to the destination, the one whose weakest arrow is strongest. That is the same rule the delta rail's ranking and the Inspector's path bar already use (Kent, 2026-09-17) — one path-choosing rule, used three times. Record 0014 states the honest caveat beside it: a path's multiplied-out likelihood multiplies numbers each read on a different day, and it is not a joint probability. Say so next to it.

**Not reached.** The person asks instead: *does the strait opening reach Iranian crude exports returning to pre-sanction levels?* Nothing the model proposed gets there. The `verdict` event carries `kind="no_path"`, an empty path, `nearest="B"` — the claim the map did reach that sits closest to the destination — and one plain sentence saying so.

**A bridge is never invented.** There is no code path that adds an arrow to make a path exist. The temptation is real and the answer is structural: the engine only ever mints what a proposal contained, and no proposal was made for that arrow. The eval case whose destination is deliberately unreachable is what proves it (`test_verify_returns_no_path_rather_than_a_bridge`).

### B8 — **Add a claim** needs no new shape *(settled 2026-09-20)*

A person looking at a finished map types *"…but Iran is struck the next day."* That claim is not like the hypothesis or the Verify destination: **its arrows point outwards**. A strike *causes* things — it pushes the oil price, it pushes the insurance premium, it withdraws what was holding the strait open — and `ClaimProposal` cannot say that, because its one arrow points *into* the claim being proposed.

The answer is not a fourth proposal shape. It is the two shapes we have, used in the order the map itself is built in:

1. **One call drafts the sentence into a claim**, with the existing `StartingClaim` shape. The person's words in, a claim with a test, a judge, a date and a likelihood out. Nothing about arrows is asked, because nothing about arrows is known yet. It is stamped `kind="event"` and its identifier is minted here.
2. **Then the ordinary machinery proposes its arrows, one per call**, as `LinkProposal`s with the new claim as one end — both ends already on the map, which is exactly what a `LinkProposal` is for. Each is validated like any other proposal: a loop is refused, a `documented` arrow with nothing kept is impossible, every arrow needs a rationale.
3. **It stops the way everything stops**: on `Stop`, on the width cap, or on three refusals in a row. No new stop rule, no new cap.
4. **The answer is one `Insert` intervention** — the claim and its arrows together — for the browser to append to its branch. A map is never left holding a claim that causes nothing.

**One proposal per call still holds.** Nothing here asks for a list; a person's one sentence simply takes one drafting call plus one call per arrow.

Worked, Hormuz. The person types *"…but Iran is struck the next day"* on the finished map.

- The drafting call returns `S`: *"A confirmed military strike on Iranian territory"*, judged by the AP, Reuters and AFP newswires, with a date and a likelihood.
- `S → B` is proposed and accepted: a `trigger`, an `impulse`, against the oil price — a strike puts the war-risk premium back into crude faster than transit data takes it out.
- `S → C` is proposed and accepted: a `sustain`, a `step`, against the insurance premium — underwriters price the threat they can see, not the transit counts.
- `S → H` is proposed and accepted: a `sustain` against the strait being open. **This is the arrow the whole product exists to draw**, and it is an ordinary `LinkProposal` like the other two.
- The next call answers `Stop`. Three arrows, at the width cap anyway.

The result is one `Insert` carrying `S` and its three arrows, and from there it is arithmetic: the browser appends it to the branch and `domain/` works the change through. **This is the single exception to "never re-prompt after an edit"** (anti-pattern 2) — one claim, its own arrows, and nothing else re-asked. The route that carries it and the field names on its request belong to [`streaming.md`](streaming.md); `test_an_insert_is_validated_like_any_other_proposal` is where it is pinned.

### B9 — the stated range ships as stated, and is labelled

`ClaimProposal.prior` is three numbers the model wrote. They are stamped `owner="model"` and stored **unchanged**. There is no ensemble: no second, third or fourth generation, no re-asking the same question to see how far the answers spread, no run-to-run number anywhere in this stack (Kent, 2026-09-17; decision record 0015).

The one-sentence reason, with the record to read for the rest: decision record 0014 defines `lo` and `hi` as the 10th and 90th percentiles of **the likelihood itself**, and a spread measured across re-asks is a different quantity — how much one model wobbles when asked the same question twice — so one field would be carrying two meanings. **Decision record 0015** has the other three reasons, the known cost said honestly, and what would reopen it.

Nothing new appears on screen. The chip keeps record 0014's label — *model interval, uncalibrated* — and the two sentences the workbench already owns. The honest cost is stated where the label is: stated ranges from language models are reliably too narrow, and the figure always travels with its source (FermiEval: a nominal 90% range covered the truth 28% of the time, cited in record 0014's research note). The label says *uncalibrated* for exactly that reason.

---

## INVARIANTS

Each is written *for all inputs drawn from generator S, statement P holds*, and names the test that checks it. The boundary tests live in `backend/tests/boundary/test_expand_cassettes.py` and run against **cassettes** — real exchanges with the vendor recorded to disk and replayed, so the suite needs no key (INV-13). The suite already runs with recording off, so an unrecorded call fails rather than dialling out.

Local numbers come from one pool shared by the five chapters of this part. **This chapter holds `INV-generation.1` through `INV-generation.8`**; [`grounding.md`](grounding.md) holds `.9` through `.13`.

| ID | Statement | Test |
|---|---|---|
| **INV-generation.1** | For every recorded answer in `backend/tests/cassettes/`, `expand` returns exactly one `Outcome`, and that outcome names at most one new claim. No call returns a list | `test_expand_returns_one_proposal_per_call` |
| **INV-generation.2** | For every recorded proposal that would close a loop, `expand` returns a `Refused` whose violations contain exactly one `cycle`, and the map is unchanged. Likewise for a claim with no resolution criteria: exactly one `missing_resolution` | `test_expand_rejects_cycle`, `test_expand_rejects_a_claim_with_no_resolution_criteria` |
| **INV-generation.3** | For every recorded answer that is a vendor refusal, for every recorded answer that does not fit the proposal shape, and for **every failure of the service itself** — a rate limit, an overload, a timeout, a connection that dropped — `expand` returns a `Refused` with a plain sentence and raises nothing. Nothing the model or the network can do escapes `grow` | `test_expand_surfaces_a_refusal_as_a_rejected_proposal`, `test_expand_reports_a_malformed_answer_and_does_not_crash`, `test_a_service_that_would_not_answer_is_a_refusal_and_not_a_crash`, `test_a_service_that_would_not_answer_one_call_never_takes_the_round_with_it` |
| **INV-generation.4** | Read over our own source: no model in `engine/proposal.py` has a field named `id`, `provenance` or `owner`, and no proposal type is or contains a list of proposals | `test_the_model_never_names_an_identifier` |
| **INV-generation.5** | For every sequence of recorded refusals on one frontier claim, **no violation code and no violation message appears anywhere in any of their prompts** — never, on any run. After the third refusal in a row for one claim, that claim is closed; an accepted answer for it starts the count again. The prompts of calls *n* and *n+1* are byte-identical when nothing else landed on the map in between, which is every run at `at_once = 1` and most re-asks above it; a round that accepts another claim while this one is being re-asked changes the map the next prompt shows, and that is the map arriving rather than a hint about the refusal | `test_a_refused_claim_is_asked_again_without_being_told_why`, `test_a_claims_run_of_refusals_starts_again_the_moment_it_is_answered` |
| **INV-generation.6** | For every recorded run whose folded counters exceed the run's spending cap, the stream ends with `done.reason == "spend_cap"`, the sentence names what was spent, and no further call is made | `test_a_run_stops_at_its_spending_cap_and_says_so` |
| **INV-generation.7** | For every recorded run in which no proposal ever names a `market` or `not_tradeable` claim, the stream ends with `done.reason == "no_terminal"`, and the map contains no claim that no proposal contained | `test_a_generation_that_reaches_no_ending_says_so` |
| **INV-generation.8** | For every recorded Verify run whose destination is not reached, the `verdict` event has `kind == "no_path"`, names a nearest claim that is on the map, and the map holds no arrow that no proposal contained. Read over our own source: no code path in `engine/` builds a `Link` outside the accept step | `test_verify_returns_no_path_rather_than_a_bridge` |

Two more tests belong to this pull request and are stated where they are owned: `test_generation_receipt_records_cache_reads` and `test_the_pipeline_never_reprompts_for_a_whole_map` — the receipt in [`streaming.md`](streaming.md), the source-reading guard here in B3. `engine/` and `api/` keep no coverage threshold, on purpose (decision record 0008).

---

## ANTI-PATTERNS

1. **Do not add a field to a proposal for something we can write ourselves** — an identifier, a provenance, an owner, a validity flag — *because* a field a model can fill is a field a model will fill, and the whole design rests on those four being facts about our pipeline. **Instead:** leave the field off the shape, and stamp it on the way in. If you are writing a check that the model did not do it, the field has crept back.
2. **Do not repair a proposal to make it pass** — *because* a silently corrected map is a state nobody can trace back to anything, which is a veto condition, and a repaired map's provenance describes a pipeline that eventually stopped violating things, which is not a source. **Instead:** return every violation and show it. If an automatic fix ever looks irresistible, the rule is wrong; change the rule in the open.
3. **Do not tell the next call what was wrong** — *because* a prompt that names a violation steers the model at the validator instead of at the truth, and a check described to the thing it checks stops measuring anything. **Instead:** ask the same question again, up to three times, and close the claim after the third.
4. **Do not re-prompt for a whole map** — *because* it breaks locality, throws away the identifiers a replay needs, and turns a small correction into a different map. **Instead:** re-propagate arithmetically in `domain/`, and re-prompt only for a claim a person asked to add, over the affected subtree.
5. **Do not invent a bridge so a Verify run has an answer** — *because* an arrow nobody proposed is exactly the unaccountable state the product exists to refuse, and it makes the one honest answer — *there is no path* — unreachable. **Instead:** name the nearest claim the map did reach and say so in one sentence.
6. **Do not write a claim the model did not propose**, including a terminal added to satisfy INV-9 — *because* a map that ends somewhere only because we put the ending there is an essay with our handwriting in it. **Instead:** ask for an ending, once per open claim, and end at `no_terminal` if the answer does not come.
7. **Do not ask for a list** — no *"give me the next three claims"*, no *"return the whole subtree"* — *because* a list cannot be streamed one refusal at a time, one bad member invalidates the whole answer, and it records as one large cassette instead of several small stable ones. **Instead:** one call, one proposal, composed by our pipeline.
8. **Do not put a number in a prompt** — not an example strength, not an example likelihood — *because* the model will copy it and the copy cannot say where it came from. **Instead:** describe the scale in words and let the answer be the model's.
9. **Do not widen the stated range because the research says stated ranges are too narrow** — *because* the field would then hold a number nobody stated and nobody measured, and record 0014 defines it as the model's own 10th and 90th percentiles. **Instead:** ship what was stated, label it *uncalibrated*, and quote the coverage figure with its source.
10. **Do not let a claim narrate its own cause** — *"With the strait open again, the war premium comes out of crude…"* — *because* the cause is already drawn as an arrow and written in that arrow's rationale, so the box says it twice; because a claim that argues for itself cannot be reused by a second arrow; and because nobody can score it. Measured in the first live run. **Instead:** one standalone statement in `claim`, and the *because* on the arrow, where the field for it already exists.
11. **Do not mark a step `market` because the chain ends in something tradeable** — *because* a payoff on a step names a trade the claim cannot settle, and it leaves the real ending unmarked, so the map stops ending anywhere a person can act. **Instead:** ask whether a venue would settle this exact sentence. If it would not, it is an `event` and carries no payoff.
12. **Do not add a proposal shape for a claim whose arrows point outwards** — the temptation is real the first time **Add a claim** is built. *Because* a fourth shape means a fourth thing to validate, a fourth thing to record, and a second way to say what `LinkProposal` already says. **Instead:** draft the claim once with the starting shape, then propose its arrows one call at a time (B8).

---

## Open questions

*Raised 2026-09-17, when this chapter was written.*

1. **Should `done.reason` carry `search_cap`?** As first asked: the shapes sheet listed the value, and under [`grounding.md`](grounding.md)'s rule nothing could ever choose it — reaching the searches cap turns searching off and the generation carries on.
   **Decided 2026-09-17, in the cross-chapter review: no. The value is gone**, and `Done.reason` has seven. A reason nobody can produce is a reason a reader will one day trust. [`streaming.md`](streaming.md) carries the seven.
2. **Does the vendor's structured-output call take a discriminated union directly?**
   **Answered 2026-09-17, by the first live call: no.** The service refuses a union at the top of a schema — *"For 'anyOf', '$defs' is not supported"* — so the union travels inside a **one-field envelope, on the wire only**. The envelope is built and unwrapped in `engine/client.py`; **the pipeline still asks for and receives a plain `Proposal`**, and no shape in this chapter changed. A reader of `expand` never meets the envelope, which is the point of putting it at the boundary.
3. **Should a vendor refusal and a malformed answer carry codes of their own?** Today both arrive as a `Refused` with an empty violation list and a plain sentence, so a reader cannot tell *the model declined* from *the answer did not parse* except by reading the sentence. Such a code would live in `engine/`, not in `domain/validity.py`, because neither is a fault in a map — the twenty codes there stay twenty.
4. **A generated map can hold no feedback arrow.** `LinkDraft` has no `reflexive` field, so the one kind of arrow allowed to close a loop cannot be proposed, and a proposal that closes a loop is always refused. The shipped example has one such arrow, hand-written. Add the field in stack 06, when unrolling a feedback arrow over time actually does something?
5. **Is the same claim, proposed twice, a fault?** *(Raised 2026-09-20.)* Two proposals can say the same thing in the same words and both be accepted: identifiers are minted by us, so the second is a different claim as far as every rule is concerned, and the map ends up carrying one sentence twice with two sets of arrows. A concurrent round makes it easy — the calls of a round cannot see each other's answers — and re-validating each answer at the fold, which now catches a duplicate *arrow*, does not catch this. **Not a violation for now, and deliberately not:** "the same claim" is a judgement about words, and the map's rules are mechanical by design. A rule anybody can re-run would have to be exact sentence equality, which is easy to slip past and would refuse two genuinely different claims that happen to be worded alike. It is written down here rather than guessed at.
6. **Which day a generated claim's resolve-by date is checked against.** `validate` reads no clock, so a model that writes a date already past is not caught by the map's rules. `engine/` can see today. Is a stale date a violation, a warning on the world, or nothing? This is [`../graph/proposition.md`](../graph/proposition.md) Open questions 4, still open, and generation is the first caller that could answer it.
