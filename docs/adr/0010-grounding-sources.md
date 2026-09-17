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

* **Contract.** `GroundingSource` is a `typing.Protocol` — a Python interface any class satisfies by having the right methods — with `search(query) -> list[InstrumentRef]` and `quote(ref) -> MarketBelief` (a probability or level, an interval where the venue gives one, `as_of`, `venue`, `url`). Every adapter caches to disk at `.cache/grounding/<venue>/<key>.json` with a per-venue expiry, so demos and recorded tests stay stable.
* **Polymarket.** A prediction market where contracts pay out on real-world events. Its Gamma interface is Polymarket's public, read-only market-data API: no authentication, read-only `/events` and `/markets`, rate limits of roughly 4,000 requests per 10 s overall, 500 for `/events` and 300 for `/markets` (going over is throttled, not rejected). The geographic restrictions apply to placing orders on the exchange, not to reads. A contract's mid-price — halfway between the best bid and the best offer — becomes `MarketBelief.p` with `provenance=market_implied`.
* **FRED.** The St. Louis Federal Reserve's public economic-data service: a free key passed as a query parameter. Its ALFRED archive stores what each series looked like on a past date, which later lets FR-30's pastcasts show only what was knowable then. The line *"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."* is rendered wherever a FRED value appears. The widely repeated 120-requests-per-minute limit is folklore, not documented; the adapter holds itself to 60 per minute.
* **Kalshi (third).** A regulated US prediction-market exchange. Its public market-data reads need no authentication; only account and order endpoints need signed requests. Added only if stack 05 has slack; it is strong on Federal Reserve and inflation markets, so it pairs well with FRED.
* **Semantics.** A `market` belief is *displayed beside* the model's and the user's (INV-11) and feeds the thesis card's `edge` column (model probability minus market probability). Where Polymarket and Kalshi both quote a proposition, both are shown and the spread is called out as a signal, never averaged. A proposition with no quote shows an explicit "no market" state rather than a blank.
* **Rejected.** Metaculus, a forecasting community: every endpoint now requires a token, and community aggregates were removed from general API access on 2026-03-09. `yfinance`, an unofficial wrapper around Yahoo Finance: undocumented scraping, terms-of-service grey area, and aggressive rate-limiting exactly when demoing. Alpha Vantage: about 25 requests a day on the free tier, unusable. Finnhub (60 per minute, documented) is the equities option if a later stack needs tickers.

### Consequences

* Good, because every terminal proposition can cite a real quote with a link; "auditable" becomes something you can click.
* Good, because two adapters behind one interface make the third (Kalshi) a copy, not a design.
* Bad, because Polymarket's coverage is event-shaped: many hypotheses (photonic-chip adoption, say) have no contract and will show "no market". That honesty is the point — it is INV-9's `not_tradeable` path.
* Bad, because a FRED key is one more `.env` entry; without it the app degrades to "no market" rather than crashing.
* Neutral, because equities are deferred; the assignment's examples resolve mostly to commodities and contracts.

### Confirmation

* `tests/boundary/test_grounding_polymarket.py` and `test_grounding_fred.py` — tests against recorded responses, asserting the `MarketBelief` shape, `provenance=market_implied`, and a cache hit on the second call.
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
