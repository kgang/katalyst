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
    title: str = Field(description="What a reader sees on arriving, in the publisher's words.")
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

    Used twice at most per generation: for the hypothesis, and for the Verify
    door's destination. It carries no cause and no arrow, because neither
    claim has anything before it yet; and it carries no `claim_kind`, because
    neither is an ending — see the paragraph below.

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


class Refused(BaseModel):
    """A proposal the map's own rules turned down, with every reason at once."""

    kind: Literal["refused"]
    claim_in_words: str               # what the model wrote. Never minted, never drawn as a tile
    violations: tuple[Violation, ...] # domain/validity.py's own codes and sentences


class Stopped(BaseModel):
    """The model has nothing more to add on this line, or gave us nothing to check."""

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

`Accepted` and `Refused` carry exactly what the `proposal_accepted` and `proposal_rejected` events carry; the stream's own shapes, their order, and the position field `at` belong to [`streaming.md`](streaming.md).

### The caps, and what each one does

Every cap is an argument with a default. Nothing here is a constant buried in a function.

| Cap | Default | What it limits |
|---|---|---|
| depth | 5 layers | How far a line may run from the hypothesis |
| width | 3 children | How many claims one claim may cause |
| claims | 30 | How large the map may get |
| refusals in a row | 3 | How many proposals for **one** frontier claim may be refused before that claim is closed |
| frontier claims at once | 3 | How many lines are expanded concurrently |
| searches per generation | 30 | How many web searches the whole run may make ([`grounding.md`](grounding.md)) |
| spending per run | $15 | What one generation may cost before it stops (Kent, 2026-09-17) |

The searches cap is set to the claims cap — **one search's worth of budget for each claim the map is allowed to hold** — so it adds no new number to the product. Its reasoning and its behaviour at the limit are in [`grounding.md`](grounding.md). Decision record 0006 *estimates* a 30-claim map at about 40 calls; the first real measurement is taken in stack 04 and written into the pull request and `STATUS.md`, never guessed here.

### What a prompt may and may not contain

A prompt is product text. The coordinator reads `engine/prompt.py` end to end before the pull request opens, the way any other copy on screen is read.

**May contain:** the words in [`../vocabulary.md`](../vocabulary.md), used exactly; what a claim is and what an arrow is, in the same plain words this spec uses; the map so far, one line per claim — identifier and sentence — and the arrows already drawn; which claim is being expanded, and which of its children already exist; the hypothesis; the Verify destination in the person's own words.

**May not contain:**

- **Jargon, or a word the interface does not use.** A prompt that says *node* teaches the model to answer in a word we do not print.
- **A number nobody computed.** No example strength, no example likelihood, no example lag. An example number in a prompt is an anchor the model copies, and a copied number cannot say where it came from — which is the state this product refuses to show.
- **The text of a violation.** Never, on any call (see B3). Violation text never enters a prompt.
- **An instruction asking the model to do what our code should do.** No *"do not create a loop"*, no *"do not reuse an identifier"*, no *"mark the arrow documented if you cite a source"*. An instruction that duplicates a check teaches the model to aim at passing the check instead of being right, and when the two disagree nobody can tell which was obeyed.
- **Anything that changes between calls, in the cached block.** The stable first block is marked for caching (decision record 0006), so the map so far, the frontier claim and the date belong *after* it. A run whose cache reads stay at zero is a bug, not a slow day (`test_generation_receipt_records_cache_reads`).

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

Expanding `B`, the model proposes an arrow instead of a claim: `B → H`, *"cheaper crude reduces the incentive to close the strait."* Read on its own it is a reasonable sentence. Added to the map it closes `H → C → B → H`.

```
Refused(
  kind="refused",
  claim_in_words="cheaper crude reduces the incentive to close the strait",
  violations=(Violation(code="cycle", subject="<the arrow that closes the loop>",
                        message='These claims form a loop with no delay in it: …'),),
)
```

The arrow is **not** added. The map the person is looking at is untouched, because nothing was mutated — the proposal was a candidate map, and it lost. `proposal_rejected` goes out carrying the validator's own sentence, and the browser shows it beside the map. A generation that hides its misses has deleted half the product (`test_expand_rejects_cycle`, `test_expand_surfaces_a_refusal_as_a_rejected_proposal`).

**Every reason, never the first.** A proposal with three faults comes back with three violations, in the rule table's order, because a model told one fault at a time needs one call per fault and a person told one fault at a time learns only that the tool is hostile. **And never a repair.** No dropping the arrow that closes the loop, no inventing a resolve-by date, no downgrading an arrow to make it fit ([`../graph/validity.md`](../graph/validity.md), *Reject; never repair*).

Two kinds of failure are not the validator's and arrive the same way. **A model refusal** — the vendor's safety check declines the call, and the answer comes back with a refusal stop reason and its own explanation (decision record 0006) — and **an answer that does not fit the shape**. Both become a `Refused` whose `claim_in_words` holds the plain sentence of what happened and whose `violations` is **empty**: there is no fault in a map to name, because no map was proposed. Nothing crashes and no stack trace reaches a screen (`test_expand_reports_a_malformed_answer_and_does_not_crash`). Whether those two deserve codes of their own is Open questions 3.

### B3 — after a refusal, ask again and say nothing (Kent, 2026-09-17)

Decision record 0003 originally allowed *one targeted re-prompt naming those violations*. Kent chose otherwise, and the record carries a dated amendment saying so.

**The rule: up to three fresh proposals in a row for one frontier claim, and the next call is never told what was wrong.** Every attempt that does not end in an accepted proposal counts — a validator refusal, a model refusal, or an answer that did not fit the shape — because the cap is on attempts, not on kinds of failure. Three in a row closes that frontier claim; the line simply stops growing there. Each attempt is its own event, and all three are shown.

Worked: expanding `B`, the model proposes `B → H` and is refused for the loop. The next call is the *same* call — the same map, the same frontier claim, the same prompt — with no mention of the loop, no mention of the refusal, and nothing new to read. It proposes `B → M1`, the Polymarket contract, and that is accepted.

**Why the silence.** Violation text in a prompt steers the model toward *passing the validator* rather than toward being right, and the two are not the same target. It is the same argument that keeps the model's hands off `provenance`: the moment a check is described to the thing being checked, the check stops measuring anything (`test_a_refused_claim_is_asked_again_without_being_told_why`).

**And never for a whole map.** No code path re-prompts for the map as a whole after an edit — it breaks locality and auditability (anti-pattern 2). The single exception is drafting a claim a person asked for, over the affected subtree only, which is [`streaming.md`](streaming.md)'s `insert` route. A test reads our own source rather than trusting good intentions (`test_the_pipeline_never_reprompts_for_a_whole_map`).

### B4 — how a generation ends, and the one reason it gives

A claim of kind `market` or `not_tradeable` is an **ending**: there is nothing downstream of a trade, so an ending never joins the frontier. A generation therefore stops when the frontier empties, or when a cap trips.

The stream ends with one `done` event carrying **one** reason, chosen by this order — the first that applies wins:

| # | `done.reason` | Chosen when |
|---|---|---|
| 1 | `spend_cap` | The running receipt reached the run's spending cap. Checked after every call, before anything else |
| 2 | `no_terminal` | The map ends nowhere you can act on, even after the last ending-seeking call (B6) |
| 3 | `depth_cap` · `width_cap` · `claim_cap` | A cap stopped a line that was still open. Our limit, so the person hears about it before the model's judgement |
| 4 | `model_stopped` | At least one line closed short — the model answered `Stop`, or three proposals in a row were refused — and no cap tripped |
| 5 | `reached_terminal` | Every line ran to an ending. The ordinary, good ending |

Worked, Hormuz: `H` → `C` → `B`, then `B` proposes `M1`, `M2` and `N1`; `H` also proposes `N1`'s line. Every open claim either reaches an ending or answers `Stop`; three of the map's claims are endings, two tradeable and one not. The frontier empties with every line at an ending, no cap tripped: `done.reason = "reached_terminal"`, with the tallies of claims, arrows and refusals beside it.

`done.reason` never carries `no_path`. Whether a Verify run found a route is a fact about the *route*, reported once on the `verdict` event and nowhere else — two derivations of one line eventually disagree (Kent, 2026-09-17).

### B5 — the spending cap stops the run and says what it bought

`engine/receipt.py` folds every `Outcome`'s counters into the run's one receipt, and **the running receipt is checked against the spending cap after every call.** Over the cap, the generation stops where it is: `done.reason = "spend_cap"`, and one plain sentence naming what was spent and what was got — *"This run reached its spending limit of <cap>. It spent <spent> and built <n> claims and <n> arrows."* No dollar figure is written into this chapter, because every one of those slots is filled by the receipt at run time.

What was built is kept, not thrown away: a partial map with a visible reason beats a blank screen with a silent one. The price table lives in `engine/pricing.py` and nothing else, with the day it was read beside it and the `claude-api` skill named — prices change, and memory is unreliable (`test_a_run_stops_at_its_spending_cap_and_says_so`).

The ceiling *across* runs is a working agreement kept in `STATUS.md`; nothing is stored between requests until stack 05. **Only the coordinator runs a command that spends money.**

### B6 — no ending reached: one last call, then an honest card

If the caps are hit and the map ends nowhere you can act on, the engine makes **one last call per open claim, asking only for an ending** — a claim of kind `market` or `not_tradeable`, with no further expansion behind it. It is the same `ClaimProposal` shape and the same validation; only the question changes.

Worked: a run capped at depth 5 whose deepest claims are all `event`s. The last call on each open claim asks for the ending it leads to. One comes back as `N1` — *"Omani-mediated United States-Iran talks resume publicly"*, kind `not_tradeable`, with its own stored reason: no venue quotes a diplomatic round. The map now satisfies INV-9 and the run ends on its cap's own name.

If that still fails, the stream ends `done.reason = "no_terminal"` and the browser says so in plain words. **The engine never writes a claim the model did not propose.** Adding a terminal ourselves to make the map legal would be a claim with no author, which is the one state this product refuses to show (`test_a_generation_that_reaches_no_ending_says_so`).

### B7 — the Verify door: a graded path, or an honest `no_path`

A Verify run carries a destination in the person's own words. It is turned into a claim by one `StartingClaim` call and added to the map **up front**, as an ordinary `event`. Every expansion call is told what it is, and expansion is steered toward it.

**Reached.** The person asks: *does the strait opening reach a Polymarket contract on Brent below $70?* The map runs `H` → `C` → `B` → `M1`. The `verdict` event carries `kind="reached"`, the path `(H, C, B, M1)`, and `product` — the multiplied-out likelihood of that path, read off the world, never multiplied here. The route shown is the **best-backed route**: over every route from the hypothesis to the destination, the one whose weakest arrow is strongest. That is the same rule the delta rail's ranking and the Inspector's path bar already use (Kent, 2026-09-17) — one path-choosing rule, used three times. Record 0014 states the honest caveat beside it: a path's multiplied-out likelihood multiplies numbers each read on a different day, and it is not a joint probability. Say so next to it.

**Not reached.** The person asks instead: *does the strait opening reach Iranian crude exports returning to pre-sanction levels?* Nothing the model proposed gets there. The `verdict` event carries `kind="no_path"`, an empty path, `nearest="B"` — the claim the map did reach that sits closest to the destination — and one plain sentence saying so.

**A bridge is never invented.** There is no code path that adds an arrow to make a path exist. The temptation is real and the answer is structural: the engine only ever mints what a proposal contained, and no proposal was made for that arrow. The eval case whose destination is deliberately unreachable is what proves it (`test_verify_returns_no_path_rather_than_a_bridge`).

### B8 — the stated range ships as stated, and is labelled

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
| **INV-generation.3** | For every recorded answer that is a vendor refusal, and for every recorded answer that does not fit the proposal shape, `expand` returns a `Refused` with a plain sentence and raises nothing | `test_expand_surfaces_a_refusal_as_a_rejected_proposal`, `test_expand_reports_a_malformed_answer_and_does_not_crash` |
| **INV-generation.4** | Read over our own source: no model in `engine/proposal.py` has a field named `id`, `provenance` or `owner`, and no proposal type is or contains a list of proposals | `test_the_model_never_names_an_identifier` |
| **INV-generation.5** | For every sequence of recorded refusals on one frontier claim, the prompt of call *n+1* is byte-identical to the prompt of call *n*, and no violation code or violation message appears anywhere in it. After the third, that claim is closed | `test_a_refused_claim_is_asked_again_without_being_told_why` |
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

---

## Open questions

*Raised 2026-09-17, when this chapter was written.*

1. ~~**`done.reason` carried `search_cap`, and nothing could choose it.**~~ **Closed 2026-09-17: the value is gone.** Under [`grounding.md`](grounding.md)'s rule, reaching the searches cap turns searching off and the generation carries on, so no run can end for that reason — and a reason nobody can produce is a reason a reader will one day trust. [`streaming.md`](streaming.md) carries the seven reasons that remain.
2. **Does the vendor's structured-output call take a discriminated union directly?** `Proposal` is a union of three shapes, and a structured-output format may want a single object at the top. If it does, the union is wrapped in a one-field object and nothing else changes — no field is renamed and no behaviour moves. Verified against the `claude-api` skill in the pipeline pull request, not guessed here.
3. **Should a vendor refusal and a malformed answer carry codes of their own?** Today both arrive as a `Refused` with an empty violation list and a plain sentence, so a reader cannot tell *the model declined* from *the answer did not parse* except by reading the sentence. Such a code would live in `engine/`, not in `domain/validity.py`, because neither is a fault in a map — the nineteen codes there stay nineteen.
4. **A generated map can hold no feedback arrow.** `LinkDraft` has no `reflexive` field, so the one kind of arrow allowed to close a loop cannot be proposed, and a proposal that closes a loop is always refused. The shipped example has one such arrow, hand-written. Add the field in stack 06, when unrolling a feedback arrow over time actually does something?
5. **Which day a generated claim's resolve-by date is checked against.** `validate` reads no clock, so a model that writes a date already past is not caught by the map's rules. `engine/` can see today. Is a stale date a violation, a warning on the world, or nothing? This is [`../graph/proposition.md`](../graph/proposition.md) Open questions 4, still open, and generation is the first caller that could answer it.
