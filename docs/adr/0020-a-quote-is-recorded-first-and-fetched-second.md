---
# ADR-0020: A quote is recorded first and fetched second; a FRED figure is an observation, not a belief
status: proposed
date: 2026-09-21
decision-makers: Kent Gang
consulted: Kent's decisions of 2026-09-21 (rows R11, R23 and R30 of plans/notes/2026-09-21-decisions-after-review.md); plans/analysis/2026-09-21-polymarket-look.md and its saved raw responses under plans/analysis/scripts/polymarket-look/; plans/analysis/2026-09-21-digest-finance.md §2.4 and finding A13; plans/analysis/2026-09-21-review-adr-06.md; ADR-0010, which this record amends; ADR-0012
informed: agents working in backend/src/katalyst/grounding and backend/src/katalyst/thesis; whoever writes the Inspector's market chip; the engine lane, which owns the fixture edits this record implies and makes them at the one shape freeze
supersedes: none
superseded-by: none
spec-impact: spec/thesis/quotes.md (new), spec/thesis/edge.md (new), spec/thesis/README.md, spec/graph/belief.md (*The market voice*), backend/src/katalyst/fixtures/hormuz.py (the engine lane's, at the freeze — wording on the owed list), ADR-0010 (Semantics, rate limits, the spread, FRED, Kalshi), PRODUCT_REQUIREMENTS.md FR-26
---

# ADR-0020: A quote is recorded first and fetched second; a FRED figure is an observation, not a belief

> **`proposed`.** Kent's decision R11 settles what this record is about; R23 and R30, taken the same day, are written into it below.

> **In short.** A price comes from a **committed dated file** first, an opt-in live read second, and the reader's own typing always — so the demo and the build run with no key and no network. A quote carries its venue, its three identifiers, both sides of the book, the venue's own question and rules, and where it came from. A **venue's number is a point, never a range**: the gap between bid and offer is what dealing costs. A measured economic level is an **observation**, not a belief. **A dated quote file may be committed, for research and development** (R23). The curated Hormuz hypothesis is **rewritten to the venue's own test and gains a `market` ending naming the real contract** (R30).
>
> **On screen.** `Polymarket · .07 · recorded 2026-09-21`, in one type size. Where nothing quotes a claim: *no contract quotes this claim — edge not calculable*, and a break-even.
>
> **What it costs.** The committed quote ages, and the card says so for ever. Kalshi is cut. The fee is unknown until somebody reads the schedule.
>
> **Open for Kent.** Nothing.

## Context and Problem Statement

*What is already priced in?* is the question this product exists to answer, and today it has no honest answer. Checked on `main` at `48eb562`: a `market` belief is written in exactly one place — the stored Hormuz example, in a comment labelling itself *"Illustrative, not a live quote"*; generation cannot write one, because both places that mint a claim build `Beliefs(model=stated)` (`backend/src/katalyst/engine/expand.py`); `FRED_API_KEY` is declared in `backend/src/katalyst/settings.py` and read by no code; and `backend/src/katalyst/grounding/` is an empty package whose docstring says so.

Two constraints shape the answer. The demo and the build must run **with no key and no network**, because that is how a reviewer walks the flow (record 0012). And record 0010 put a venue's probability and an economic series behind one shape carrying *"a probability or level"*, which lets a measured historical oil price fill the same slot as a venue's price on a future claim. A half-hour read of the venue on 2026-09-21 (`plans/analysis/2026-09-21-polymarket-look.md`, raw responses saved beside it) settled what is out there and corrected this repository's own description of the interface.

So: **where does a price come from, what does it carry, what may fill the `market` belief — and what does the screen show when there is none?**

## Decision Drivers

* **The keyless build.** No test and no continuous-integration job may make a network call. INV-13 says this of the *model* boundary; the rule for venues is new here, and the owed list widens INV-13 to say so. On this machine a live read would fail anyway — the local resolver returns no address for the venue's hosts.
* **INV-11 — three voices, never merged**, so whatever fills the `market` slot must be a venue's own number about *this* claim; and the **disgust veto**, so a price with no venue, no date and no source — or a range built by an arithmetic nobody can state — is not shown at all.
* **Record 0012's rule:** a replay is the real thing played back, so the recorded and live paths produce one shape. And two sources that work beat four that half-work — record 0010's own driver, applied to itself.

## Considered Options

| | Option | Verdict |
|---|---|---|
| **A** | **Recorded first, fetched second**: a committed dated quote file the demo and the build run on, an opt-in live read that falls back to it, a reader-entered price always available | **Chosen.** The keyless path is the *normal* path, and the live read can fail without taking anything with it |
| B | Live-first with a disk cache, as record 0010 described | The demo depends on a venue being reachable — here it is not — and the build either calls the network or tests a path nobody runs |
| C | Recorded only, no live read | Always works, but the product never touches a real market and *auditable* stops being clickable |

## Decision Outcome

Chosen option: **A**.

### The shape: store what was read, derive the rest

`backend/src/katalyst/grounding/quote.py` holds **`Quote`**, the only shape allowed to carry a price. Its field list, with the reason for each, is in `spec/thesis/quotes.md`; four rules govern it:

1. **Store what the venue returned, derive everything else.** The best bid and best offer are stored as read; the midpoint and the edges are derived. A number you can re-derive can say why.
2. **Identity takes three identifiers and a side** — an on-chain condition identifier, the venue's market identifier, and one **outcome token identifier per side**, of which only the token identifier buys a price. The committed file is named by the market identifier, the one a person can paste into the site.
3. **Carry the venue's own question, rules and end date**, so a reader can check the venue asks the same question with no network.
4. **Carry the state and the size** — closed, accepting orders, resting size, traded volume, minimum price increment — because a settled market keeps serving a plausible book, and a midpoint over an empty book is a different claim from one over a hundred thousand dollars of resting orders.

**`source` is `fetched`, `recorded` or `user`.** A reader's own price is *their report of a venue price they could trade at* — not what they think the claim is worth, which is a `user` **belief** and a different quantity. An edge against it prints *against a price you entered* on the same line, and it never fills the `market` slot.

### The four rules

**Recorded first:** a committed, dated file under `backend/recordings/quotes/` holds what the worked example needs, and the demo and the build read it and nothing else; it is written by a command only the coordinator runs, in the manner of the generation recordings. **Fetched second, and opt-in:** one route refreshes a quote — never on page load, never in a test, never in the build — and when it fails, **the recorded quote stays and the card says the refresh failed**. **A reader-entered price is always available**, so the card works on any map. **Only a venue's own number fills the `market` belief** — `fetched` or `recorded`, never `user`, never an economic level.

### A market belief is a point, and the spread is a cost

Record 0010 put *"an interval where the venue gives one"* on a quote. The chapter that teaches beliefs read that as the spread — *"where the venue publishes a spread, that becomes `lo` and `hi`"* (`spec/graph/belief.md`) — and the fixture did it: `Belief(p=0.48, lo=0.45, hi=0.52)` (`backend/src/katalyst/fixtures/hormuz.py:309`), a range built by an arithmetic nobody can state, beside a comment saying the spread became it.

**A bid–offer spread is what it costs to cross, not how unsure the venue is**, and the venue publishes no interval at all. So the `market` belief is a **point** — `lo` and `hi` equal the midpoint — and the chip says in words that no interval was published rather than implying certainty. What the two sides of the book differ by shows up where it belongs: you buy at the offer and sell at the bid (record 0018). A settled market, incidentally, reads `.999` against `1.00`, so every edge against one is smaller than a tick and is refused twice over — once as settled, once by the tick rule.

### A contract may be named only if it asks the claim's question

The venue quotes the map's hypothesis with the same deadline but a different test — a moving average of transit calls, where the claim asks for a fortnight of unrestricted transit. Rather than a run-time refusal for a case no input can carry today, this is a **curation rule**: *an ending may name a venue contract only when the ending's resolution test is the venue's own.* It binds whoever writes a fixture, and the freeze's prompt, which asks the model to name a real venue contract where one exists.

### FRED supplies a spot anchor, and never a belief

The Federal Reserve Bank of St. Louis's economic-data service publishes **measured historical levels** — an observation about the past, not a price on a future claim. So a FRED figure is the **spot anchor** for an ending that names an instrument, carried with its series and vintage date, rendered with the required line *"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."* — and it **never** fills the `market` slot. The committed anchor is a dated file like the quotes, so the keyless path needs no FRED key. It arrives with the position work, because nothing before that has a use for a level. Archived vintages stay out of version one.

### What the venue quotes, for this map

Read 2026-09-21 at 14:48 UTC, saved raw. **Nothing quotes Brent** — the venue's only crude contracts are on WTI, in *did it touch a level* form — so the curated example's Brent ending names a contract that cannot be made real, and the **recorded** map, the one the walk opens, has no contract ending at all: eleven tradeable endings, every one naming an instrument (`backend/recordings/hormuz.jsonl`). Nothing quotes the fund pair, the insurance premium or OPEC+ output either.

**The hypothesis has a real, liquid contract**: *"Strait of Hormuz traffic returns to normal by October 31?"*, market id `3501950`, best bid `.06`, best offer `.08`, resting size about $119k and traded volume about $755k (`liquidityNum`, `volumeNum`), ending on the claim's own resolve-by day. As the fixture stands the hypothesis is not a tradeable ending and carries no payoff, so nothing on the card prices it — which is what R30 changes.

### The curated map takes the venue's own question

**Kent's decision R30:** rewrite the curated Hormuz hypothesis to Polymarket's own test, and give the map a `market` ending naming the real contract.

So in `backend/src/katalyst/fixtures/hormuz.py`: the hypothesis's resolution test becomes **the venue's, word for word** — a seven-day moving average of transit calls at or above sixty on any date up to 31 October 2026, as IMF PortWatch publishes it — which is what record 0018's curation rule demands before an ending may name a contract. Beside it the map gains one ending of kind `market`, carrying that same test and a payoff naming contract `3501950`, because a hypothesis carries no payoff and no card row can reach one. The arrow between them is **elicited in the one shape freeze, not typed by hand.**

**Be exact about what this buys.** The **curated** fixture then carries **one** comparable venue price, so the card's *what is priced in* row has something real on one ending: the model's number against `.06` bid and `.08` offer, read 2026-09-21 at 14:48 UTC. It does **not** change the **recorded** map — the one the walk opens — which still has eleven endings naming instruments, no contract, and therefore eleven honest refusals. That changes only at the one paid re-recording after the freeze (Kent's decision R5), whose prompt already asks the model to name a real venue contract where one exists.

**The fixture edit is the engine lane's, at the flip**, and its exact wording, identifiers and dates are on the owed list in `plans/notes/2026-09-21-stack-06-docs-owed.md`. **One knock-on goes with it:** the hypothesis's prior, its base rate and its two pieces of evidence were all written for the **old** test — fourteen consecutive days of unrestricted transit — and the venue's test is a different and easier one, so whoever makes the edit re-examines them rather than carrying them across. The gap they would leave is not small: the fixture's own comment says the prior sits below its base rate *because* the old test was harder.

### The committed quote file, and why it may be committed

**Kent's decision R23, in his words:** *"On the terms of service, we can commit a dated quote for research and development purposes."* The committed file and this record both state that purpose in one line, and nothing else about the file changes: it is named by the venue's market identifier, it carries the instant it was read, and the card goes on printing *recorded 2026-09-21*.

The context stays on the record, because it is a fact and not a blocker: **nobody has read the venue's terms of use.** The page is served as an empty shell and rendered in the browser, so it could not be read and was not guessed; no required attribution line was found either, and an absence is not permission. Kent took this decision with that in front of him.

### Kalshi is cut from version one

One venue that works beats two that half-work, and FR-26's cross-venue line is honestly answered by naming which venue quoted the claim and saying no other was asked. The shape does not change if a second venue is added: a quote names its venue, and two quotes are two rows, never an average.

### Open for Kent

**Nothing open.** **R30** answered which map carries a venue price — the curated one, rewritten to the venue's question, while the recorded map stays what the model drew until the freeze re-records it. Declined: adding a contract ending to the recorded map by hand, which would cost the walk its claim to showing what the model actually drew. **R23** answered whether a dated quote file may be committed — it may, for research and development. Declined: waiting on a reading of the terms before committing, and shipping with a reader-entered price only.

### Consequences

* Good, because the keyless path is the normal path — the demo, the build and the reviewer see the same quote — and every price carries a venue, a source and a day, with the slot that could have laundered a measured level, or an invented range, into a belief closed and tested.
* Bad, because the committed quote ages and the card carries that caveat for ever; and a reader-entered price cannot fill the market chip, so a map with no venue coverage shows *no market* even when the reader has typed a price into the card.
* Neutral, because the live adapter is one file behind the same shape.

### Confirmation

* `test_no_quote_test_touches_the_network` — the suite passes with outbound connections refused; the recorded loader reads only the committed file.
* `test_the_best_bid_is_the_last_bid`, `test_a_settled_market_is_read_from_its_flags` — over saved responses where the first bid and the best bid differ, and where a settled market still serves a plausible book.
* `test_a_market_belief_has_no_invented_range` — a belief built from a quote has `lo` and `hi` equal to its midpoint; the two sides of the book appear only in the buying and selling edges.
* `test_a_fred_figure_never_fills_a_market_belief`, `test_a_reader_entered_price_is_not_a_market_belief` — source walks in the manner of `test_beliefs_never_merged` (the test that exists; record 0010's planned twin is not written), landing with the spot anchor and the card. `test_a_failed_refresh_keeps_the_recorded_quote` lands with the route, in the card pull request.
* `test_a_contract_ending_asks_the_venues_question` — for every ending on a committed fixture that names a venue contract, the ending's own resolution test is the venue's stored question and rules, compared against the committed quote file rather than against anything typed. The curation rule, checked where it can be.
* Review item: the FRED attribution line is present wherever a FRED value is rendered (record 0010's check, kept). And the committed quote file's first line states the purpose R23 gives it — research and development — so the file says why it is in the repository.

## More Information

**Amends ADR-0010** in five places, dated 2026-09-21; the pointer sentences for that record are held in `plans/notes/2026-09-21-stack-06-docs-owed.md`:

1. ***Semantics*** — the `market` belief is filled only by a venue's own quote about this claim.
2. ***"An interval where the venue gives one"*** — withdrawn, along with the reading it invited in `spec/graph/belief.md` and the fixture. The venue gives no interval; the spread is a cost and the belief is a point.
3. ***Rate limits*** — that record's figures appear nowhere in the venue's current documentation, whose only rate-limit pages are about order actions. Withdrawn as uncitable, the same defect its FRED paragraph calls *folklore*.
4. ***FRED*** — a spot anchor with its attribution, not a belief; archived vintages deferred.
5. ***Kalshi*** — cut from version one.

* **Kent's decisions, 2026-09-21. Row R11:** look at the venue, and name a real contract if one exists; if none does, the card says *no contract quotes this claim — edge not calculable* and prints a break-even. The look was done: no Brent contract exists, and a contract on the hypothesis does. **Row R23:** a dated quote file may be committed, for research and development. **Row R30:** the curated hypothesis takes the venue's test and the map gains a `market` ending naming the contract.
* Related: **0018** (the two edges, the break-even, the tick rule), **0019** (the market's chance of a claim also sets what the price path gives back, and it reads a quote from here first), **0013**, **0012**, **0008**. **Records 0016 and 0017 are forthcoming.**
* **Not established, and named rather than guessed:** the venue's terms of use — read by nobody, and no longer a blocker under R23 — and its fee schedule, so the fee in an edge is zero today and the card says it is unknown.
