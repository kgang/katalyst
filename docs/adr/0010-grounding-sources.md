---
# ADR-0010: Ground market beliefs with Polymarket and FRED behind a GroundingSource protocol
status: accepted
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md, docs/research/01-landscape-and-competitors.md
informed: future agents working in backend/src/katalyst/grounding
supersedes: none
superseded-by: none
spec-impact: spec/thesis/ (market belief, legs, export), spec/graph/ (Belief.owner = market)
---

# ADR-0010: Ground market beliefs with Polymarket and FRED behind a GroundingSource protocol

## Context and Problem Statement

The thesis card must show a live, read-only `market` belief — what a real venue is pricing — beside the model's and the user's (D6, FR-26, INV-11: the three are never merged), and terminal propositions of kind `market` need real instruments to point at (INV-9). Which outside sources are worth wiring in for v1, under what contract, and how do we keep the three beliefs honest and separate?

## Decision Drivers

* INV-11: `model`, `user`, and `market` beliefs are never averaged into one number.
* FR-26: Polymarket first, FRED second, Kalshi third; disagreement between venues is surfaced, not smoothed away.
* NFR-8: keys are read once through settings, and none of these sources may be called from the browser.
* INV-13 / ADR-0008: every adapter must be testable from recorded responses, so the suite needs no key.
* Taste: two adapters that work beat four that half-work; a note on sources considered and rejected is worth more than a fourth integration.

## Considered Options

* A. **Polymarket's Gamma interface plus FRED in v1; Kalshi if there is time; everything else rejected with a reason.**
* B. Metaculus community forecasts as the primary anchor.
* C. `yfinance` for equities.
* D. No grounding at all; static fixtures only.

## Decision Outcome

Chosen option: "A", because Polymarket and FRED are free or keyless, documented, friendly about rate limits, and between them cover prediction-market contracts and macroeconomic series — the two instrument types the assignment's examples resolve to.

* **Contract.** `GroundingSource` is a `typing.Protocol` — a Python interface any class satisfies by having the right methods — with `search(query) -> list[InstrumentRef]` and `quote(ref) -> MarketBelief` (a probability or level, an interval where the venue gives one, `as_of`, `venue`, `url`). Every adapter caches to disk at `.cache/grounding/<venue>/<key>.json` with a per-venue expiry, so demos and recorded tests stay stable. *(The interval is withdrawn 2026-09-21 by record 0020: a venue's number is a **point**. The gap between its best bid and its best offer is what dealing costs, not how unsure the venue is. See the amendment at the foot of this record; the original sentence stands as written.)*
* **Polymarket.** A prediction market where contracts pay out on real-world events. Its Gamma interface is Polymarket's public, read-only market-data API: no authentication, read-only `/events` and `/markets`, rate limits of roughly 4,000 requests per 10 s overall, 500 for `/events` and 300 for `/markets` (going over is throttled, not rejected). The geographic restrictions apply to placing orders on the exchange, not to reads. A contract's mid-price — halfway between the best bid and the best offer — becomes `MarketBelief.p` with `provenance=market_implied`. *(Two sentences above are withdrawn 2026-09-21. The rate-limit figures, by record 0020: they appear nowhere in the venue's own documentation, and no published limit for keyless market-data reads is known. The mid-price, by record 0018: an edge is set against the price you would actually deal at — the best offer to buy, the best bid to sell — so the midpoint is derived and displayed and never traded against. See the amendment at the foot of this record; the original sentences stand as written.)*
* **FRED.** The St. Louis Federal Reserve's public economic-data service: a free key passed as a query parameter. Its ALFRED archive stores what each series looked like on a past date, which later lets FR-30's pastcasts show only what was knowable then. The line *"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."* is rendered wherever a FRED value appears. The widely repeated 120-requests-per-minute limit is folklore, not documented; the adapter holds itself to 60 per minute. *(Amended 2026-09-21 by record 0020: a FRED figure is a **spot anchor** — a measured historical level, which is an observation about the past — and it never fills the `market` belief. The attribution line stands. ALFRED vintages are deferred with the pastcast, which version one does not build. See the amendment at the foot of this record; the original sentence stands as written.)*
* **Kalshi (third).** A regulated US prediction-market exchange. Its public market-data reads need no authentication; only account and order endpoints need signed requests. Added only if stack 05 has slack; it is strong on Federal Reserve and inflation markets, so it pairs well with FRED. *(Cut 2026-09-21 by record 0020: one venue in version one. See the amendment at the foot of this record; the original sentence stands as written.)*
* **Semantics.** A `market` belief is *displayed beside* the model's and the user's (INV-11) and feeds the thesis card's `edge` column (model probability minus market probability). Where Polymarket and Kalshi both quote a proposition, both are shown and the spread is called out as a signal, never averaged. A proposition with no quote shows an explicit "no market" state rather than a blank. *(Amended 2026-09-21 by records 0018 and 0020: the edge is the model's number read from the world with nothing fixed by an edit, set against the best offer for a buy and the best bid for a sell, less any fee — never a subtraction of two column values; and the `market` belief is filled only by a venue's own quote about this claim, never by a reader's price or an economic level. See the amendment at the foot of this record; the original sentence stands as written.)*
* **Rejected.** Metaculus, a forecasting community: every endpoint now requires a token, and community aggregates were removed from general API access on 2026-03-09. `yfinance`, an unofficial wrapper around Yahoo Finance: undocumented scraping, terms-of-service grey area, and aggressive rate-limiting exactly when demoing. Alpha Vantage: about 25 requests a day on the free tier, unusable. Finnhub (60 per minute, documented) is the equities option if a later stack needs tickers.

### Consequences

* Good, because every terminal proposition can cite a real quote with a link; "auditable" becomes something you can click.
* Good, because two adapters behind one interface make the third (Kalshi) a copy, not a design.
* Bad, because Polymarket's coverage is event-shaped: many hypotheses (photonic-chip adoption, say) have no contract and will show "no market". That honesty is the point — it is INV-9's `not_tradeable` path.
* Bad, because a FRED key is one more `.env` entry; without it the app degrades to "no market" rather than crashing.
* Neutral, because equities are deferred; the assignment's examples resolve mostly to commodities and contracts.

### Confirmation

* `backend/tests/boundary/test_grounding_polymarket.py` and `test_grounding_fred.py` — tests against recorded responses, asserting the `MarketBelief` shape, `provenance=market_implied`, and a cache hit on the second call.
* `test_market_belief_never_merged` — no code path in `domain/` or `api/` combines a `market` belief with a `model` or `user` one: a search-based guard plus a unit test on the thesis-card builder.
* Frontend: the FRED attribution line is present in the rendered Inspector whenever a FRED value is shown (vitest).
* The "sources considered and rejected" list from `docs/research/04-engineering-structure.md` §8 is mirrored in `spec/thesis/`.

## Pros and Cons of the Options

### A. Polymarket + FRED (chosen)

* Good, because keyless or free, documented, cached, and they cover the assignment's instrument types.
* Bad, because no equities in v1.

### B. Metaculus

* Good, because the best-calibrated community numbers available.
* Bad, because the API is locked and the aggregates are no longer exposed (2026-03-09).

### C. yfinance

* Good, because everyone knows it.
* Bad, because unofficial, terms-of-service-adjacent, and brittle exactly when demoing.

### D. Static fixtures only

* Good, because zero external surface.
* Bad, because live read-only prices were an explicit interview choice (D6) and are the credibility differentiator (`docs/research/01-landscape-and-competitors.md` §5c).

## More Information

* Interview D6 (thesis card + live read-only prices + export) and D2 (anchored to a market price wherever one exists).
* `docs/research/04-engineering-structure.md` §8 (authentication, limits, verdicts) and `docs/research/01-landscape-and-competitors.md` §4 (Polymarket and Kalshi market structure) and §5c, ideas 1 and 7.
* Metaculus API change: https://www.metaculus.com/notebooks/42554/changes-to-the-metaculus-api/ · Polymarket docs: https://docs.polymarket.com/

## Amendment (2026-09-21) — five sentences, by records 0018 and 0020

Records 0018 (*like with like: an edge is computed from the world with no supposition in force*) and 0020 (*a quote is recorded first and fetched second; a FRED figure is an observation, not a belief*) were accepted on 2026-09-21. Between them they change five sentences of this record. Each is pointed at inline above and stands as written; this is what replaces it.

**1. The edge, and what fills the `market` belief** *(the Semantics bullet; records 0018 and 0020)*. The edge is the model's number for a claim **read from the world with nothing fixed by an edit**, set against **the best offer for a buy and the best bid for a sell**, less any fee. It is not a column subtracted from another column, and it is never taken from a world where a supposition is in force, because those two numbers answer different questions. The `market` belief is filled **only by a venue's own quote about this claim** — never by a price the reader typed, which is their report of what they could deal at, and never by an economic level, which is an observation about the past.

**2. A venue's number is a point, not a range** *(the Contract bullet's interval; record 0020)*. A venue publishes one price on each side of its book. The gap between them is **what dealing costs**, not a statement of how unsure the venue is, so nothing builds a `lo` and a `hi` out of it. The two sides show up instead as the two edges — one for buying, one for selling — and the midpoint is derived, displayed, and never traded against.

**3. The Polymarket rate-limit figures are withdrawn as uncitable** *(record 0020)*. The numbers in the Polymarket bullet — roughly 4,000 requests per 10 seconds overall, 500 for `/events`, 300 for `/markets` — appear nowhere in the venue's own documentation, and **no published limit for keyless market-data reads is known**. They are withdrawn rather than corrected, because a figure nobody can cite is exactly the kind of state this project refuses. Nothing depends on them: the product reads a committed dated file, and asking the venue again is one function a reader opts into.

**4. A FRED figure is an observation, not a belief** *(record 0020)*. It is a **spot anchor**: a measured historical level with a series name and a vintage date, which anchors the starting price of an ending that names an instrument. It **never fills the `market` belief**, because a level measured in the past is not anybody's price on a future claim. The attribution line — *"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."* — stands exactly as this record wrote it. ALFRED vintages are deferred along with the pastcast, which version one does not build (record 0021).

**5. Kalshi is cut from version one** *(record 0020)*. One venue, not two. Where one venue quotes a claim the card names it and says no other was asked; where two ever do, both are shown and never averaged, which is this record's own rule and is unchanged in kind.

**What has not changed.** The decision itself: outside facts come from named, free or keyless sources behind one contract; every number carries the address it came from and the moment it was read; the three owners of a likelihood are never merged; and a claim with no quote says so rather than showing a blank. What moved is which price the comparison is made against, what a venue's number means, and how many venues version one asks.

**One thing this record could not have said.** Its caching sentence assumed a live read with a disk cache behind it. Record 0020 turns that around: a committed dated file under `backend/recordings/quotes/` is the **first** source, a live read is opt-in and never runs in the build, and a reader-entered price is always available. The recorded file is committed for research and development purposes and says so on its first line.

Amended in place rather than superseded, because the decision is unchanged: these are the same two sources behind one contract, with the arithmetic on top made exact and one optional third venue dropped.
