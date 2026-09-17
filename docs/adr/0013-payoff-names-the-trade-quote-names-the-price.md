---
# ADR-0013: Split Payoff into a contract shape and a price shape; the domain names the trade, the grounding layer names the price
status: accepted
date: 2026-09-17
decision-makers: Kent Gang
consulted: spec/graph/proposition.md (open questions 1 and 2), docs/research/01-landscape-and-competitors.md, docs/research/04-engineering-structure.md
informed: agents working in backend/src/katalyst/domain, backend/src/katalyst/grounding, and the thesis stack
supersedes: none
superseded-by: none
spec-impact: spec/graph/proposition.md (Payoff), spec/thesis/ (legs, export)
---

# ADR-0013: Split Payoff into a contract shape and a price shape; the domain names the trade, the grounding layer names the price

## Context and Problem Statement

A `market` terminal is the point of the whole map: the claim at the end of the chain that names something you could actually put money on (INV-9). Until now it carried one `Payoff` shape — instrument, direction, magnitude — and `magnitude` was never pinned down. The Hormuz fixture shows why that could not hold: one of its two endings is a Polymarket contract that settles on the claim itself, where the honest number is what the contract is trading at right now; the other is an exchange-traded fund sold against another, where the honest number is how far a price moves. The spec had to read the same field two different ways to describe two ordinary terminals, and the contract reading quietly assumed an entry price that no field ever held. So: what belongs on the claim, and what belongs on the live quote?

## Decision Drivers

* INV-11 — the model's, the user's and the market's numbers are stored separately and never merged. A market price written into a proposition is a market number frozen inside the claim, where nothing can keep it apart from the model's.
* D5-ii, the disgust veto — no state that cannot be traced to an input, a rule or a cited source. A price with no venue, no timestamp and no link is exactly that state; a quote fetched from a venue carries all three.
* ADR-0010 — venue, `as_of`, interval and link already live on the grounding layer's `MarketBelief`. A second, staler copy of the price in the domain would make one of them wrong.
* FR-25 — the thesis card's legs need instrument, direction, size and the model-versus-market edge. They need a number they can trust at the moment the card is built, not at the moment the map was generated.
* ADR-0003 — `domain/` is pure: no clock, no network. Anything that goes stale cannot live there, because nothing in there can tell that it has.

## Considered Options

* A. **Two shapes told apart by a `kind` field: `ContractPayoff` and `PricePayoff`.**
* B. One shape, keeping the fractional move, plus an `entry_price` field so a return can be computed.
* C. One shape, redefining `magnitude` as a return on the position.
* D. One shape with `magnitude` dropped: name the instrument and the direction and nothing else.

## Decision Outcome

Chosen option: "A", because the two ordinary kinds of ending want different facts about *identity* and neither wants a price, which leaves one rule to remember: **the domain names what you would trade; the grounding layer names what it costs.**

* **`ContractPayoff`** — `kind: "contract"`, `venue`, `contract_id`, `title`, `side` (`yes` or `no`). Used when a real venue quotes this exact claim. It records which contract, not what it costs, and `contract_id` is what lets the grounding layer fetch a quote later without guessing from the title.
* **`PricePayoff`** — `kind: "price"`, `instrument`, `direction` (`long` or `short`), `move`. Used when nothing quotes the claim but something whose price the claim moves can be bought or sold. `move` is a fractional move in the instrument's price if the claim comes out true: `0.03` is three per cent. It is not a return, because a return needs an entry price.
* **Discriminated on `kind`**, the same pattern as the six interventions: a reader, and the TypeScript types generated for the browser, tell the two apart from one field rather than guessing from which others are present.
* **Amends ADR-0010's *Semantics* bullet.** That record put venue, `as_of` and a link on the quote. Venue and contract identifier now also appear in the domain, as identity — a stable name for the thing being traded. What remains exclusive to the quote is the price, the spread and the moment we looked. Where the two disagree about identity, the domain is what we meant and the quote is what we found.
* **The Hormuz fixture re-reads under one rule.** M1 becomes a contract payoff (Polymarket, side `yes`); its old `1.08` — a return in disguise — is gone. M2 becomes a price payoff (short XLE against SPY, `move` of `0.03`).

### Consequences

* Good, because every number on a `market` terminal can now say why: identity is asserted by the map and auditable against the venue, and price is fetched with a source and a timestamp.
* Good, because a contract leg no longer needs an invented entry price. The thesis card reads the live mid-price at the moment it is built, which is the number a trader would act on.
* Good, because the two shapes make the generation step easier to grade: a proposal that names a venue and a contract is checkable against that venue, and one that names a fund pair and a move is not pretending to be.
* Bad, because two shapes are more surface than one — every consumer of `payoff` now branches on `kind`, and the export schema (FR-27) carries both forms.
* Bad, because the model must choose between them while proposing, and choosing wrongly (a price payoff where a contract exists) is a new way to be almost right. It is caught by the grounding step, which finds the contract the payoff failed to name.
* Neutral, because nothing is lost: everything the old single shape could say, the two shapes say, and each says it without a second reading.

### Confirmation

* `test_validate_requires_payoff_on_market` covers **both** shapes: a `market` claim carrying either a contract payoff or a price payoff passes rule 4, and one carrying neither fails with exactly one `market_without_payoff` violation. The generators in `backend/tests/strategies.py` produce both shapes, so every property test over maps sees both.
* `test_intervention_round_trip`-style round-trip and discriminator checks apply here too: parsing a payoff's JSON yields the class named by its `kind`, and an unknown `kind` is refused rather than coerced.
* A stack 05 test on the thesis-card builder: a leg built from a contract payoff takes its `edge` from the venue's live mid-price, and a leg built from a price payoff takes its size from `move`. Neither reads a price out of `domain/`.
* Review item: no field named `price`, `entry`, `spread` or `as_of` ever appears on a model in `domain/`. A search-based guard in the test suite, beside `test_market_belief_never_merged` from ADR-0010.

## Pros and Cons of the Options

### A. Two shapes, discriminated on `kind` (chosen)

* Good, because each shape holds only facts that are true without a clock, and the boundary with the grounding layer states itself.
* Bad, because consumers branch, and the union has to be handled in the browser types as well as in Python.

### B. One shape plus an entry price

* Good, because a return on the position becomes computable inside the domain.
* Bad, because the entry price is a market number with no venue and no timestamp sitting inside a claim — the disgust veto, D5-ii, and it goes stale the moment it is written.

### C. One shape, `magnitude` as a return on the position

* Good, because the thesis card could read one number for every leg.
* Bad, because a return is not a property of the claim at all: it depends on what you paid, which depends on when you asked. It also hides the entry price rather than removing it.

### D. Drop `magnitude`, keep instrument and direction

* Good, because it is the smallest shape and never wrong.
* Bad, because a price leg then carries no size at all, and FR-25's legs and FR-22's tail rows have nothing to scale. "Short XLE against SPY" without a move is a direction, not a trade.

## More Information

* Kent's decision, 2026-09-17, settling open questions 1 and 2 in `spec/graph/proposition.md` (the units of `magnitude`, and whether a payoff names its venue).
* Related: ADR-0010 (grounding sources; this record amends its semantics), ADR-0003 (the domain is pure and owns validity), ADR-0005 (payoffs are computed per simulated world, which is what needs a size).
* `docs/research/01-landscape-and-competitors.md` §4 (how prediction-market contracts are identified and quoted) and `docs/research/04-engineering-structure.md` §8 (venue interfaces, caching, what a quote carries).
