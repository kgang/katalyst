# Quotes — where a price comes from, and what it has to say about itself

## Purpose

A price on this screen must say where it came from, when it was true, and how we got it. A reader can now see what a real venue is charging for a claim on the map, open the market to check, and know at a glance whether the number was read a moment ago, read from a committed file, or typed in by themselves.

It also fixes a boundary: **a market price is a venue's number about a future claim; a measured economic level is an observation about the past.** They do not go in the same slot.

---

## Data model

`backend/src/katalyst/grounding/quote.py` holds **`Quote`**, the only shape allowed to carry a price. `recorded.py` loads one from the committed file, `polymarket.py` reads one from the venue when the reader asks, `fred.py` reads a spot level. Nothing in `domain/` gains a field.

It stores **what the venue returned** and derives the rest:

* **the venue and its three identifiers** — the on-chain condition identifier, the venue's market identifier, and the **outcome token identifier**, because only the token identifier buys a price: a contract's yes and no are two separate order books — and **the side** quoted, since the same contract can read `.07` on one side and `.93` on the other;
* **the best bid and best offer, as read.** The **midpoint** — halfway between them — and the cost of dealing are derived from these, never the other way round;
* **the instant it was true**, because the book moves within the day and the venue returns milliseconds. Store the instant, print the day;
* **resting size and traded volume**, because a midpoint over an empty book is a different claim from one over a hundred thousand dollars of resting orders; and **closed** and **accepting orders**, because a settled market keeps serving a book and live-or-settled is read from these, never from the price;
* **the venue's own question, resolution rules and end date**, so a reader can check the venue asks the same question with no network; and its **minimum price increment**, because a gap smaller than that is not tradeable;
* **a web address** that opens the market, and **`source`** — `fetched`, `recorded` or `user`, which the sentence on screen and the caveat in the export both need.

**A reader's own price carries almost none of that** — a price, a date, free text for where they got it — and the absent fields stay absent rather than being invented. It is their *report of a price they could deal at*, which is not what they think the claim is worth: that is a `user` belief and it lives on the tile.

A **spot anchor** is a separate, smaller shape in `fred.py`: a series name, a level, the date it is for, and the vintage. An observation, not a belief and not a quote.

---

## Behaviour

### B1 — Recorded first, fetched second

A committed, dated file under `backend/recordings/quotes/`, named by the venue's market identifier, holds the quotes the worked example needs; continuous integration, the Docker build and the keyless walk read it and nothing else, and no test makes a network call. It is written by a command only the coordinator runs, and **its first line says why it is in the repository**: a dated quote kept for research and development (Kent's decision R23 of 2026-09-21).

One route refreshes a quote — never on page load, never in a test, never in the build. **When it fails, the recorded quote stays and the card says the refresh failed**; the date on screen is still true. On the machine this was written on the refresh *will* fail, because the local resolver returns no address for the venue's hosts, which is why recorded-first is the rule rather than a fallback.

### B2 — A price you typed

A reader can type a price on any claim, on any map, with no venue and no key: *the best I can get is 41 cents* (**illustrative**). It is stamped `user`, dated, and printed as theirs; any edge against it carries *against a price you entered* on the same line. It does **not** fill the market chip on the tile, which says what a venue is charging (INV-11, three voices never merged).

### B3 — What the venue quotes, on the worked maps

Read from the venue on 2026-09-21 and saved raw; record 0020 has the detail. **Nothing quotes Brent crude**, so the curated map's Brent ending — and all eleven endings on the **recorded** map the walk opens — run on *no contract quotes this claim*, permanently.

The venue does quote the curated map's **hypothesis**, with the same deadline and a different resolution test. Kent's decision R30 takes that test as the map's own and adds one ending of kind `market` naming the contract, so the **curated** fixture carries exactly one comparable venue price. The **recorded** map is untouched until the one paid re-recording after the freeze.

### B4 — A market belief is a point, and the spread is a cost

Where a venue quotes a claim, the midpoint becomes the `market` belief on the tile. It has **no range**: the venue publishes no interval, so the low and high ends equal the number, and the chip says in words that no interval was published rather than implying certainty. What the two sides of the book differ by is what dealing costs, and it shows up in the buying and selling edges. Turning a spread into a range, as an earlier draft of this product did, produces a number nobody can trace to an input, a rule or a source.

### B5 — How a quote prints

Never as a bare number. The venue, the value, how we got it and the day are one unit, in one type size:

```
Polymarket · .07 · recorded 2026-09-21
```

That value is real — the midpoint of the Hormuz contract, read at 14:48 UTC on 2026-09-21. When likelihoods move to a percentage form a contract price will print the same way, and the card keeps saying which it is: **a price is not a probability**, even where the two read the same. One card line carries the caveat for all of them: *prices are as of the dates shown and were not refreshed; an edge against a stale quote is a stale edge.*

### B6 — A FRED figure is an observation

The Federal Reserve Bank of St. Louis's economic-data service publishes measured historical levels — what a barrel actually settled at. That is a **spot anchor** for an ending that names an instrument, rendered with its series, its date, and the required line *"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."* It **never** fills the `market` belief slot.

---

## INVARIANTS

Written *for all inputs drawn from generator S, statement P holds*. This chapter owns `INV-thesis.4`–`INV-thesis.6`.

**INV-thesis.4 — No price arrives over a network in a test.** Over every test module in `backend/tests/`, run with outbound connections refused, the suite passes: the recorded loader reads the committed file, and the live adapter is exercised only against saved responses. **Tests:** `test_no_quote_test_touches_the_network`, `test_the_best_bid_is_the_last_bid`, `test_a_settled_market_is_read_from_its_flags`.

**INV-thesis.5 — Every rendered price says its venue, its source and its day.** For every quote from `quotes()`: the rendering used by the card, the tile chip and the export contains the venue (or, for a reader's own price, the words saying it is theirs), the source and the date. There is no path that renders a price alone. **Test:** `test_a_quote_prints_its_venue_source_and_day`, landing with the card, which is the first thing that renders.

**INV-thesis.6 — Only a venue's own number fills the market slot.** A new rule, not a refinement of INV-11. Over our own source, no function builds a `market` belief from a spot anchor or a `user` quote — a syntax-tree walk in the manner of `test_beliefs_never_merged`. Over generated data, for every `user` quote from `quotes()` and every anchor from `anchors()`, building the card leaves `beliefs.market` exactly as it was; and a belief built from a venue quote has its low and high ends equal to its midpoint. **Tests:** `test_a_fred_figure_never_fills_a_market_belief`, `test_a_reader_entered_price_is_not_a_market_belief`, `test_a_market_belief_has_no_invented_range`.

---

## ANTI-PATTERNS

1. **Do not fill an absent quote with a stand-in** — not a half, not the model's own number, not a blank chip. Because *no venue prices this* is a finding, and it drives a chain to an ending nobody can trade. **Instead:** the words *no market*, the reason beside them, and a break-even where one is defined.

2. **Do not read the price off the venue's display figure, or off the first line of the book.** Because the display figure is rounded and snaps to one and zero on a settled market, and bids come back ascending and offers descending, so the first is the *worst* — in the response saved for this chapter, `.01` against a best bid of `.06`. **Instead:** take the last of each side, derive the midpoint, and keep a saved response where the two differ as a test.

3. **Do not decide a market is live from its price**, because a settled market keeps serving a plausible book: read the closed and accepting-orders flags.

4. **Do not turn the spread into a range, and do not average two venues.** Because a bid–offer spread is what dealing costs rather than how unsure the venue is — and the venue publishes no interval at all — while two venues disagreeing is a signal the average destroys. **Instead:** a point belief with the cost in the edges, and one row per venue.

---

## Open questions

*Raised 2026-09-21.*

1. **What does dealing actually cost?** The fee schedule has not been read, so the fee is zero and the card says so.
2. **How stale is too stale?** The committed quote carries its day and the card says so, but nothing refuses a quote for being old.

*(Two questions this chapter used to raise were answered on 2026-09-21. Whether a dated quote file may be committed: it may, for research and development — Kent's decision R23; nobody has read the venue's terms of use, which is context and not a blocker. Which map carries a venue price: the curated one, under R30, written into B3 above.)*
