---
# ADR-0018: Like with like — an edge is computed from the world with no supposition in force, against the price you would actually trade at
status: accepted
date: 2026-09-21
decision-makers: Kent Gang
consulted: plans/analysis/2026-09-21-digest-finance.md §2.1; the two independent midpoint reviews, which found this trap separately; plans/design-after-midpoint-review.md §3; plans/analysis/2026-09-21-polymarket-look.md (what the venue quotes); plans/analysis/2026-09-21-review-adr-06.md (the arithmetic review of this record's first draft)
informed: agents working in backend/src/katalyst/thesis and backend/src/katalyst/grounding; whoever writes the thesis card and the export
supersedes: none
superseded-by: none
spec-impact: spec/thesis/edge.md (new), spec/thesis/card-and-export.md (new), spec/graph/belief.md (the sentence that teaches *model minus market is the edge*), ADR-0010's *Semantics* bullet
---

# ADR-0018: Like with like — an edge is computed from the world with no supposition in force, against the price you would actually trade at

> **Accepted by Kent on 2026-09-21** (decisions note, row R32). The one question it held open he answered the same day (R20).

> **In short.** An **edge** — the model's number for a claim against what a venue charges for the same claim — is read only from the world with **nothing fixed by an edit**, and one function with two required world arguments makes any other reading impossible to write. There are **two** edges, because you buy at the offer and sell at the bid, and the only cost term is the venue's fee: the spread is already inside the two prices. Where an edge cannot be built, the card prints a **named refusal and a break-even**, which is a value and never a blank.
>
> **On screen.** After *Suppose this is true* the edge does not move, and the supposed reading appears beside it as a **mixture** — an explanation with a measured residual, never the number compared against a price.
>
> **What it costs.** Every caller must have the base world in hand, about one extra solve per card, and every reader of an edge branches on two shapes.
>
> **Open for Kent.** Nothing.

## Context and Problem Statement

The reader's first finance question is *what is already priced in?* The product answers it by putting the model's number for a claim beside what a venue charges for the same claim and calling the difference the **edge** — the only thing that word means here.

The trap is that the product's central gesture changes the question. **Suppose this is true** pins a claim and re-works the map, so the number on the ending's tile becomes *the chance of that ending in a world where the strait has been made to open*. A venue's price is not that; it is the price in the world as it stands. Subtract one from the other and you have the difference between two questions, printed as money.

A second trap sits beside it: *which* price. A venue publishes a best bid and a best offer. You buy at the offer and sell at the bid, and an edge computed against the midpoint between them flatters one side of every trade.

Nothing computes an edge today — `backend/src/katalyst/grounding/` is an empty package — so both are settled before the first line. But record 0010's *Semantics* bullet already defines the card's edge as "model probability minus market probability", with no rule about which world or which price. So: **what makes it impossible to difference a supposed number against a quote, which price is the comparison against, and what does the card say when it cannot compare?**

## Decision Drivers

* **The audience checks this first.** A finance-literate reader who catches one conditional-versus-unconditional comparison, or one edge computed against a midpoint, stops trusting every number on the screen.
* **The disgust veto (D5-ii):** no state that cannot be traced to an input, a rule or a cited source. *Which world, and which price* must be answerable from the face of the code — and a rule a caller must remember will be forgotten, so this repository prefers a shape that cannot be misused to a check that can be skipped.
* **INV-11 — three voices, never merged.** The model's, the reader's and a venue's numbers are stored and rendered apart; an edge is a *difference*, computed outside `domain/` and labelled as one.
* **The supposed world must still produce something.** A rule that blanks the card after *Suppose this is true* deletes the demo.

## Considered Options

| | Option | What it costs | Verdict |
|---|---|---|---|
| **A** | **A signature that cannot take a supposed world alone** — one function, two world arguments, both required | About twenty lines, and every caller must fetch the base world | **Chosen.** The rule is checked by the type checker on every path, including the ones no test walks |
| B | A guard inside the edge function that refuses when a supposition is in force | Five lines | The mistake stays expressible; it is reported only where a test goes |
| C | A label on the card: *conditional edge* | One line of copy | The number beside the label is still the wrong number |

## Decision Outcome

Chosen option: **A**, because it answers *which world* by the type rather than by the caller's care.

### The shape

```python
# backend/src/katalyst/thesis/edge.py — outside domain/, because it touches a quote
def priced(
    base: World,      # the world with nothing fixed by an edit
    shown: World,     # the world the reader is looking at; may be a branch world
    claim: PropositionId,
    quote: Quote | None,
) -> Edge | NotComparable: ...
```

1. **Both worlds are required, and `Edge` has no other construction path.** A caller holding only a branch world cannot produce one; it has to work out the base world first.
2. **The compared number is always read from `base`** — never from `shown`, never reconstructed.
3. **The type and the check do different jobs.** The signature fixes *which world is read*; a check fixes *whether the caller handed in the right one*. The check is exact: `base.assignments` — the list of values fixed by **Suppose this is true** or **This happened** — must be empty. It is what option B was rejected for as a *substitute* for the type, and it is fine as a companion to it. A branch that only *adds* a claim fixes no value, so it passes: nothing is pinned, the map is merely larger, and the card says the number comes from an edited map.

   **Either button refuses the edge — decided by Kent, 2026-09-21 (R20).** One rule, not two: any fixed value in `base`, whether it came from *Suppose this is true* or from **This happened**, makes the world unfit to price against. **The cost he accepted, in one sentence:** a reader who records a real, public fact loses the edge on that map until they start again from one without it, even though a quote taken afterwards already reflects that fact. **The alternative he declined:** allow an observation through when the quote is dated on or after it — one more rule, one more date comparison, and a second way for a conditional number to reach a price.
4. **A refusal is a value, not an exception.** `NotComparable` carries a reason from a closed list and the sentence the card prints. Every case `priced` can meet has a row in the decision table in `spec/thesis/edge.md`; there is no undefined input.

### The arithmetic, said out loud

A venue publishes a best bid and a best offer. **You buy at the offer and sell at the bid.** So there are two edges, and the fee — anything the venue charges on a filled trade — works against both:

> **edge of buying = model − offer − fee**
> **edge of selling = bid − model − fee**

There is **no half-the-spread term anywhere**: the spread is already inside the two prices, and subtracting it again double-counts. The midpoint is displayed, because it is the one number a reader recognises, and it is never traded against.

The card shows the side with the positive edge. **When neither is positive, that is a complete answer, not a gap:** the model's number sits inside the venue's own bid–offer, fees included — *no edge at this price*.

### The break-even, and the no-trade band

The **break-even** is the model's own number moved by the fee, one step each way:

> worth **buying below** *model − fee* · worth **selling above** *model + fee*

Said once, explicitly: **these bound the price you would actually pay or receive — the offer and the bid — not the midpoint.** The stretch between them has one name, the **no-trade band**, used in the record, the chapters, the card and the export. More fee makes the band **wider**, not narrower.

The break-even needs no quote, which is why it is what the card prints when there is none. Nobody has read the venue's fee schedule, so the fee is zero today and the card says the fee is unknown — which makes the band zero-width and the break-even the model's number itself. That is honest and it is one line of work away from being better.

**A break-even on an ending that names an instrument rather than a venue contract is not a defined quantity in this stack.** The price at which such a position is worth nothing is the entry price adjusted for costs, and the entry is on the reader's position form, which arrives in 06-2. Until then a price ending returns a refusal, not a number.

### Two thresholds stop a headline, and the card says which one bit

* **One tick.** A *tick* is the smallest price step the venue trades in — one cent on the Hormuz market (`event-hormuz-oct31.json`, `orderPriceMinTickSize`). A gap narrower than one tick cannot be traded, so it is not headlined.
* **The model's own range.** Every claim carries the range the model stated (record 0015). The edge is computed at **both ends** of that range; if its sign differs between them, the edge is *inside the model's own range* and the card neither headlines nor ranks it. A product that policed one cent and ignored a twenty-point band would be policing what was easy.

### The mixture explains; it never computes

After *Suppose this is true*, the card shows the supposed reading and the two terms that relate it to the priced number:

> the map's own chance of the supposition **×** the ending's number where it is supposed true, **plus** one minus that chance **×** the ending's number where it is supposed false.

**The terms are an explanation with a measured residual, not an identity, and the card never claims they add up to the base number.** Two things break the equality, and the record states both because a reader needs to know when the explanation is safe:

* **Another route.** The equality survives when every path from the supposed claim's causes to the ending runs *through* that claim. It fails when one of its causes reaches the ending another way. *Having causes is not the criterion* — a claim with many causes can still weigh back.
* **A supposition pins a date, not just a truth.** `Suppose this is true` fixes the claim on a day; the unsupposed world averages over the days it might have happened, and the arrows have lags and half-lives.

Measured on today's engine (`plans/analysis/scripts/finance/review/mixture_seeds.py`, three seeds, shipped loop sizes): supposing the **hypothesis**, the gap is about six ten-thousandths and **changes sign with the seed** — sampling noise. Supposing **B**, whose causes reach the endings only through B, the gap is `−0.0028` to `−0.0044` with **the same sign at every seed** — systematic, and caused by the pinned date, not by another route.

**No test asserts the terms equal the base number.** The test that exists asserts what is always true: the two weights sum to one, and each term is read from the named world. The engine's own tolerance is a separate matter and belongs to the record that owns the engine.

### Consequences

* Good, because *which world* and *which price* are both answerable from four arguments and two formulas, and the missing-quote and no-contract cases become the most useful thing the tool can say rather than an empty row.
* Bad, because every caller must have the base world in hand — about one extra solve per card — and every reader of an edge branches on two shapes, in Python and in the generated browser types alike. That is the cost record 0013 accepted for the two payoff shapes, for the same reason.
* Bad, because the fee is zero until somebody reads the venue's schedule, so today's band is zero-width and says so.
* Neutral, because nothing in `domain/` changes.

### Confirmation

* `test_agreeing_with_the_market_reads_exactly_zero` — build a quote whose **bid and offer are both** the base world's own number for that claim, with a zero fee; both edges read `0.0` exactly. No typed-in number: the quote is built from the world.
* `test_an_edge_reads_the_unsupposed_world` — over generated maps and branches, the model belief inside any `Edge` is byte-identical to the base world's, whatever `shown` carries.
* `test_a_supposed_base_world_is_refused` — a `base` with any assignment yields `NotComparable(conditional_world)`.
* `test_buying_and_selling_edges_have_the_right_sign` — raising the offer lowers the buying edge; raising the bid raises the selling edge; a fee lowers both.
* `test_more_fees_widen_the_no_trade_band` — a larger fee lowers *buy below* and raises *sell above*.
* `test_an_edge_inside_the_model_range_is_not_ranked` — where the edge's sign differs at the two ends of the model's stated range, the result is marked and not headlined.
* `test_the_mixture_terms_weigh_to_one` — the two weights sum to one, and each term names the world it came from. **No equality with the base number is asserted.**
* `mypy --strict`: no overload of `priced` takes one world.
* `test_no_call_site_prices_a_branch_world` — a walk over our own source, in the manner of `test_beliefs_never_merged`.

### Open for Kent

**Nothing open.** The one question this record held — whether **This happened** should be treated more leniently than *Suppose this is true* — was closed by **R20**: refuse both, one conservative rule, written above with the cost he accepted and the leniency he declined. The choices the venue forced are in record 0020; the greyed size ceiling that reuses this record's model-range threshold is in record 0019 (**R29**).

### What this record does not decide

Where a quote comes from and what it carries (record 0020) · what a position is and who owns the stop (record 0019) · how the card ranks endings (`spec/thesis/card-and-export.md`).

## More Information

* **Accepted by Kent on 2026-09-21** (decisions note, row R32), with records 0016–0022.
* **Amends record 0010's *Semantics* bullet**, which defined the card's edge as the model's probability minus the market's. It now carries this record's rules: the model number is read from the world with nothing fixed by an edit; the comparison is against the offer for a buy and the bid for a sell, never the midpoint; the difference is built only by `priced`; and where it cannot be built, the card prints a named refusal and a break-even.
* **Amends `spec/graph/belief.md`**, whose sentence *"model minus market is the edge you might trade"* gains the conditioning rule in the same pull request.
* **Records 0016 and 0017** belong to stack 05 and are accepted too; nothing here depends on a number either of them states.
* Related: **0013** (the domain names the trade, the quote names the price), **0015** (a claim carries the range the model stated — the second threshold above), **0003** (`domain/` is pure), **0010** (grounding sources), **0020** (what a quote carries).
* `plans/analysis/2026-09-21-digest-finance.md` §2.1 · `plans/analysis/2026-09-21-polymarket-look.md` · `plans/analysis/2026-09-21-review-adr-06.md`, whose measurements of the mixture are quoted above.

## Amendment, 2026-09-22 — the second of the two thresholds is void, because there is no range

**Decision record 0028** — *one likelihood per claim, computed once; no range anywhere*, Kent's decisions-note row R48 — removed the range from this product. Every number the engine computes now has the same value at its low end, its likelihood and its high end.

So the second of the two thresholds in *Two thresholds stop a headline, and the card says which one bit* **can never fire again**. It asks whether an edge is worth taking at one end of the model's stated range and not at the other; with both ends the same number, no sign can change between them. As of today:

* `inside_the_model_range` on an `Edge` is **always false**, set to that constant in `backend/src/katalyst/thesis/edge.py` with the same dated note. The two helpers that worked the edge out at each end of the range are deleted.
* **The rule itself is not withdrawn, and every reader of the flag still obeys it.** A card neither headlines nor ranks an edge carrying the mark, and the size ceiling still refuses one. That is deliberate: if a range with width ever returns — a reader's own stated uncertainty is the obvious candidate — the refusals are already written down. Two tests in `backend/tests/thesis/test_card.py` set the mark by hand, exactly as `test_ceiling.py` already did, and say in their own words that nothing computes it.
* `test_an_edge_inside_the_model_range_is_not_ranked`, named in *Confirmation* above, **is deleted**, with two more beside it in `backend/tests/thesis/test_edge.py` that checked the same rule from other angles. They asserted that `priced` derives the mark from a range with width, which is now an input nobody can build.

**The first threshold — one tick — is untouched**, and it is now the only thing besides a negative edge that stops a headline.

**Not settled here.** The greyed size ceiling of record 0019 also reads the model's range: it works its fraction out at the end of the range that flatters the trade least. With both ends the same number it now works it out at the likelihood itself, which is a quieter change than this one but a change all the same, and it belongs to that record to write down.
