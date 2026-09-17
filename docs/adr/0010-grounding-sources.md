---
# ADR-0010: Ground market beliefs with Polymarket and FRED behind a GroundingSource protocol
status: proposed
date: 2026-09-16
decision-makers: Kent Gang
consulted: docs/research/04-engineering-structure.md, docs/research/01-landscape-and-competitors.md
informed: future agents working in backend/src/katalyst/grounding
supersedes: none
superseded-by: none
spec-impact: spec/03-thesis.md (market belief, legs, export), spec/01-causal-graph.md (Belief.owner = market)
---

# ADR-0010: Ground market beliefs with Polymarket and FRED behind a GroundingSource protocol

## Context and Problem Statement

The thesis card must show a live, read-only `market` belief beside the model's and the user's (D6, FR-26, INV-11), and terminal `market` propositions need real instruments to point at (INV-9). Which external sources are worth wiring in v1, under what contract, and how do we keep the three beliefs honest and separate?

## Decision Drivers

* INV-11: `model`, `user`, `market` beliefs are never merged.
* FR-26: Polymarket first, FRED second, Kalshi third; cross-venue disagreement surfaced, not averaged.
* NFR-8: keys read once via settings; none of these sources may be called from the browser.
* INV-13 / ADR-0008: adapters must be testable from recorded responses.
* Tasteful: two adapters that work beat four that half-work; a "sources considered and rejected" note is worth more than a fourth integration.

## Considered Options

* A. **Polymarket Gamma + FRED in v1; Kalshi if time; others rejected with reasons**
* B. Metaculus community predictions as the primary anchor
* C. yfinance for equities
* D. No grounding; static fixtures only

## Decision Outcome

Chosen option: "A", because Polymarket and FRED are keyless-or-free, documented, rate-limit-friendly, and together cover prediction-market contracts and macro series — the two instrument types the assignment examples resolve to.

* **Contract.** `GroundingSource` is a `typing.Protocol` with `search(query) -> list[InstrumentRef]` and `quote(ref) -> MarketBelief` (p or level, interval where the venue gives one, `as_of`, `venue`, `url`). All adapters cache to disk (`.cache/grounding/<venue>/<key>.json`, TTL per venue) so demos and cassettes are stable.
* **Polymarket Gamma.** No auth. Read-only `/events` and `/markets`; rate limits ~4,000/10 s general, `/events` 500/10 s, `/markets` 300/10 s (over-limit is throttled, not 429'd). Geo-gating applies to CLOB order placement only, not reads. A contract's mid-price becomes `MarketBelief.p` with `provenance=market_implied`.
* **FRED.** Free API key, query-param auth; ALFRED vintages let us show what was knowable at a date (used by FR-30 pastcasts later). The attribution line *"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."* is rendered wherever a FRED value appears. The widely cited 120 req/min limit is folklore, not documented; the adapter rate-limits itself to 60/min.
* **Kalshi (third).** Public market-data GETs need no auth; only account/order endpoints need RSA-PSS. Added only if 05 has slack; strong on Fed/CPI markets, pairs with FRED.
* **Semantics.** A `market` belief is *displayed beside* the model and user beliefs (INV-11) and feeds the thesis card's `edge` column (model p − market p). When Polymarket and Kalshi both quote a proposition, both are shown with the spread called out as a signal, never averaged. A proposition with no quote shows an explicit "no market" state rather than a blank.
* **Rejected.** Metaculus — all endpoints require a token and community aggregates were removed from general API access on 2026-03-09. yfinance — undocumented scraping, ToS gray area, adversarial 429s; never on a demo path. Alpha Vantage — ~25 req/day free tier, unusable. Finnhub (60/min, documented) is the equities option if a later stack needs tickers.

### Consequences

* Good, because every terminal proposition can cite a real quote with a URL; "auditable" becomes a link.
* Good, because two adapters behind one Protocol make the third (Kalshi) a copy, not a design.
* Bad, because Polymarket coverage is event-shaped; many hypotheses (e.g. photonic-chip adoption) have no contract and will show "no market". That honesty is the point (INV-9's `not_tradeable` path).
* Bad, because a FRED key is one more `.env` entry; the app degrades to "no market" without it, never crashes.
* Neutral, because equities are deferred; the assignment's examples resolve mostly to commodities and contracts.

### Confirmation

* `tests/boundary/test_grounding_polymarket.py`, `test_grounding_fred.py` — contract tests against recorded responses (vcrpy), asserting `MarketBelief` shape, `provenance=market_implied`, and cache hits on the second call.
* `test_market_belief_never_merged` — no code path in `domain/` or `api/` combines `market` with `model` or `user` (a grep-based guard plus a unit test on the thesis-card builder).
* Frontend: FRED attribution string present in the rendered Inspector whenever a FRED value is shown (vitest).
* `docs/research/04-engineering-structure.md` §8's "sources considered and rejected" is mirrored in `spec/03-thesis.md`.

## Pros and Cons of the Options

### A. Polymarket + FRED (chosen)

* Good, because keyless/free, documented, cached, and cover the assignment's instrument types.
* Bad, because no equities in v1.

### B. Metaculus

* Good, because best-calibrated community numbers.
* Bad, because the API is locked and aggregates are no longer exposed (2026-03-09).

### C. yfinance

* Good, because everyone knows it.
* Bad, because unofficial, ToS-adjacent, and brittle exactly when demoing.

### D. Static fixtures only

* Good, because zero external surface.
* Bad, because "live read-only prices" was an explicit interview choice (D6) and the credibility differentiator (`docs/research/01` §5c).

## More Information

* Interview D6 (thesis card + live read-only prices + export) and D2 (market-anchored where possible).
* `docs/research/04-engineering-structure.md` §8 (auth, limits, verdicts) and `docs/research/01-landscape-and-competitors.md` §4 (Polymarket/Kalshi market structure) and §5c ideas 1 and 7.
* Metaculus API change: https://www.metaculus.com/notebooks/42554/changes-to-the-metaculus-api/ · Polymarket docs: https://docs.polymarket.com/
