# Graph — the language of cause and effect

## The idea

A hypothesis is only useful if it can be checked. So the map is built from **propositions**: claims that will be true or false by a date, judged by a named source. "Tensions ease" is not a proposition. "At least 14 consecutive days of unrestricted commercial transit through Hormuz per Lloyd's List by 2026-11-01" is.

Propositions are joined by **links**: a link says *A makes B more (or less) likely*, states the mechanism in a sentence, how strongly it pushes, how long it takes, and whether the push is a one-time shove (a domino: once it falls it stays fallen) or a continuous hold (a desk holding an apple: remove the desk and the apple falls).

Every likelihood on the map is a **belief** with an owner — the model, the user, or a market — and an honest range, never a bare point. The three owners are shown side by side and never averaged, because the product's value lives in the gap between them.

## Terms this part owns

Proposition · Link · Provenance · Belief · Graph · Hypothesis · Terminal (market / not-tradeable). Definitions in [`../vocabulary.md`](../vocabulary.md).

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-1 | Every proposition has resolution criteria, an adjudicating source, and a resolve-by date |
| INV-2 | Every link has a rationale and a provenance; links claiming evidence carry sources; every belief has an owner |
| INV-6 | The graph has no loops, except through explicitly *reflexive* links (a market feeding back on the world), which must carry a delay |
| INV-7 | Every belief satisfies `0 ≤ low ≤ p ≤ high ≤ 1`; rendered at two significant figures with its range |
| INV-9 | Every graph ends in at least one tradeable terminal, or an explicit "not tradeable — because…" |
| INV-11 | Model, user, and market beliefs are stored and rendered separately; no code path averages them |

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| [`proposition.md`](proposition.md) | Fields, kinds, resolution, base rates, evidence, payoff | stack 02 — written, models built |
| [`link.md`](link.md) | Mode (trigger/sustain), strength, lag, shape, half-life, provenance, reflexive links | stack 02 — written, models built |
| [`belief.md`](belief.md) | Owner, range, rendering rules, why never merged | stack 02 — written, models built |
| [`validity.md`](validity.md) | What makes a graph valid; rejection over repair; server-minted identifiers | stack 02 — written, models built |

Decision records behind this part: ADR-0003 (the domain layer owns validity; the model only proposes), ADR-0005 (link semantics).
