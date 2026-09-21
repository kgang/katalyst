# Edge — the model's number against the price you would actually trade at

## Purpose

The reader's first finance question is *what is already priced in?* This chapter answers it, or says exactly why it cannot: the model's number for a claim, the two prices a venue is really showing, the gain from buying and from selling, and a **break-even** to price their own view against when there is no quote.

**Edge** means one thing here — the model's number against a price you could deal at. Never an arrow on the map, and never the gap between the model and what the reader *believes*.

---

## Data model

`backend/src/katalyst/thesis/edge.py`, outside `domain/`: it touches a live price, and an edge is a difference between two owners' numbers, which no function in `domain/` may return (INV-11).

One function builds an edge and nothing else does: `priced(base, shown, claim, quote)`. Both worlds are required — `base` is the world with nothing fixed by an edit, `shown` is what the reader is looking at — so a caller holding only a branch world must go and work out the base world first. Decision record 0018 carries the signature and the reasoning. Two further things may be named, and neither can be handed in instead of a world: the **fee**, which a caller passes because nobody has read the venue's schedule and the answer is nothing until somebody does; and the **other world**, for the mixture below.

**`Edge`** holds the model's belief read from `base`; the quote; the **fee**, anything the venue charges on a filled trade; the two edges below; the no-trade band; the venue's minimum price increment; whether the edge changes sign across the model's own range; and the mixture terms when a supposition is in force. **`NotComparable`** holds a reason from a closed list, the sentence the card prints, and a break-even where one exists.

*Built 2026-09-21 (06-1). Two details the chapter did not settle, decided at the keyboard and written back here. **A break-even goes with a contract, and with nothing else**: `no_quote` and `settled_market` always carry one, `no_contract` never does — one rule rather than a row-by-row answer, and it agrees with every row of the table below. And **the mixture needs a third world**, so it appears only when the caller hands in the world where the supposition goes the other way; there is no honest way to read that reading off `base` and `shown`, because working it back out of the unsupposed number would assume the very equality the mixture does not claim.*

### The arithmetic

A venue shows a **best bid** (what someone will pay you) and a **best offer** (what someone will sell to you for); the **midpoint** halfway between is the number a reader recognises and nobody trades at. **You buy at the offer and sell at the bid**, so there are two edges:

> **edge of buying = model − offer − fee** · **edge of selling = bid − model − fee**

No half-the-spread term anywhere: the spread is already inside the two prices. The card shows whichever side is positive. **When neither is, that is a result** — the model's number sits inside the venue's own bid–offer, fees included: *no edge at this price.*

The **break-even** is the model's number moved by the fee, one step each way: worth **buying below** *model − fee*, worth **selling above** *model + fee*. These bound **the price you would actually pay or receive**, not the midpoint. The stretch between them is the **no-trade band**, and more fee makes it **wider**. Nobody has read the venue's fee schedule, so the fee is zero today, the band has zero width, and the card says the fee is unknown.

### What `priced` does in every case

| The case | What comes back |
|---|---|
| `base` carries any value fixed by **Suppose this is true** or **This happened** | `conditional_world` — the wrong world was handed in. The check is exact: `base` must have no fixed values |
| The claim names no trade — the hypothesis, an intermediate step | `no_contract`: *nothing on this claim names a trade* |
| An ending that says it cannot be traded | `no_contract`, printing the claim's own stored reason |
| An ending naming an **instrument**, with or without a quote | `no_contract`: *no contract quotes this claim — edge not calculable*, and **no break-even**, because the price at which such a position is worth nothing needs an entry price, which arrives with the reader's position |
| An ending naming a **contract**, no quote in hand | `no_quote`, **and the break-even anyway** |
| The same, but the quote is closed or not accepting orders | `settled_market`, and the break-even. Live or settled is read from the venue's flags, never from the price |
| An ending naming a contract, a live quote, `base` clean | an **`Edge`** |

A branch that only *adds* a claim fixes no value, so it passes the first row: nothing is pinned, the map is merely larger, and the card says the number comes from an edited map.

---

## Behaviour

### B1 — A quote, and nothing supposed

The reader selects an ending a venue quotes on the curated Hormuz map — the one ending there is, added by Kent's decision R30, which names the real Polymarket contract on the map's own hypothesis and takes that contract's resolution test as the claim's. The card shows the model's number, the venue's bid and offer with their date, the fee, and the better of the two edges. Two things stop it being headlined, and the card says which bit: a gap narrower than one **tick** — the smallest price step the venue trades in, one cent on its Hormuz market — and a gap whose sign changes between the two ends of the model's own stated range.

### B2 — After *Suppose this is true*

The reader supposes the strait opens; every number on the map re-works, and the ending's tile now reads *the chance of this ending in a world where the strait has been made to open*. **The edge does not move**, because it is still the base world's number against the venue's prices. Beside it the card shows the **mixture**: the map's own chance of the supposition times the supposed reading, plus one minus that chance times the reading with the supposition made false.

The two terms are an **explanation**, not an identity, and the card never claims they add up to the base number. They do not, for two reasons a reader needs: a cause of the supposed claim may reach the ending by another route, and *Suppose this is true* pins a **date** as well as a truth while the base world averages over the days the claim might have happened. Record 0018 quotes the measured residual and names the script.

Reading the second term costs a third world — the same map with the same claim supposed the other way — so the card works that world out and hands it in. Without it the card shows the supposed reading and the edge, and no mixture at all. That is deliberate: the alternative is to recover the second reading from the base number by arithmetic, and the arithmetic that does it is exactly the equality this passage says does not hold.

### B3 — No contract quotes this claim

The curated map's Brent ending, and every ending on the recorded map. Nothing on the venue quotes Brent crude. The card prints *no contract quotes this claim — edge not calculable*, names the instrument the payoff does name, and stops. The break-even for that kind of trade arrives with the reader's position, in the next chapter.

### B4 — A price the reader typed

*Photonic chips get adopted faster than expected* produces a map nothing quotes. The reader types the price they can actually get; it is treated as their report of a venue price, the edge is computed against it and printed with *against a price you entered* on the same line, and it never fills the market chip on the tile.

---

## INVARIANTS

Written *for all inputs drawn from generator S, statement P holds*. Generators live in `backend/tests/strategies.py`; `quotes()` is added by the pull request that builds this chapter. This chapter owns `INV-thesis.1`–`INV-thesis.3`.

**INV-thesis.1 — An edge is read from the unsupposed world** *(refines INV-11)*. For every map from `graphs()`, every branch from `branches(graph)` and every quote from `quotes()`: the model belief inside any `Edge` is byte-identical to the base world's for that claim, whatever `shown` carries; and a `base` with any fixed value yields `conditional_world`. **Tests:** `test_an_edge_reads_the_unsupposed_world`, `test_a_supposed_base_world_is_refused`, and a source walk in the manner of `test_beliefs_never_merged`, `test_no_call_site_prices_a_branch_world`.

**INV-thesis.2 — Agreeing with the market reads exactly zero.** For every map from `graphs()`: a quote whose **bid and offer are both** the base world's own number for that claim, with a zero fee, makes both edges read `0.0` exactly — not within a tolerance, and with no number typed in, because the quote is built from the world. **Test:** `test_agreeing_with_the_market_reads_exactly_zero`.

**INV-thesis.3 — A contract with no quote still says something useful.** For every map from `graphs()` and every ending on it naming a **contract**: `priced(..., quote=None)` returns `no_quote` with a non-empty sentence and a break-even. An ending naming an instrument returns `no_contract` with no break-even, and this invariant does not ask for one. **Test:** `test_a_missing_quote_still_prints_a_break_even`.

---

## ANTI-PATTERNS

1. **Do not compare a number from a supposed world, or reconstruct one from the mixture.** Because a supposed number answers *what if this were made true* and a price answers *what is*, and the mixture is an explanation with a measured residual. **Instead:** read the model's number from the base world, and show the supposed reading and the two terms beside it.

2. **Do not compute an edge against the midpoint, and do not subtract the spread twice.** Because nobody deals at the midpoint, and the spread is already inside the bid and the offer. **Instead:** two edges, each against the price that side would pay, with the venue's fee as the only cost term.

3. **Do not blank or zero the card when there is no quote, and do not treat a negative edge as a failure.** Because a blank says nothing, a zero says the model agrees with a price that does not exist, and *the venue is paying more for this than we think it is worth* is a complete answer whose other side is a trade. **Instead:** name the reason, print the sentence and the break-even, and print the sign.

4. **Do not call the gap between the model and a reader's belief an edge.** Because that is the argument the reader is having with the tool. **Instead:** reserve *edge* for the model against a price somebody will actually deal at.

---

## Open questions

*Raised 2026-09-21.*

1. **What does dealing cost besides the spread?** The venue's fee schedule has not been read, so the fee is zero and the card says so.
2. **Who checks that a contract asks the claim's question?** Record 0020's answer is a **curation rule** — an ending may name a contract only when its resolution test is the venue's own — binding whoever writes a fixture and the generation prompt. Whether a run-time check ever replaces it is open.
