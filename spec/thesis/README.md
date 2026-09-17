# Thesis — from map to trade

## The idea

A map of causes is not a trade. This part turns it into one, and does so by *derivation* rather than by asking the user to type numbers.

**Sensitivity.** Flip each proposition one at a time and record how much each tradeable terminal moves. The proposition whose flip hurts most — *and* resolves before the terminal *and* can be observed publicly — is the **invalidation**: the event that proves the idea wrong. That is the stop-loss, and it is derived, not guessed. The mirror case is the take-profit. Propositions that matter but cannot be observed in time are listed as *unhedgeable*, never used as a stop.

**Tails.** Rare, large outcomes get their own rows with a suggested hedge. They are never folded into an average, because an average hides the case where you are wiped out.

**The card.** Everything above compiles into a thesis card — legs, entry, invalidation, take-profit, the distribution of outcomes, tails, caveats — and exports as a plain declarative document a downstream trading system could read.

## Terms this part owns

Sensitivity sweep · Invalidation · Take-profit · Unhedgeable · Tail · Thesis · Strategy export.

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-14 | The invalidation proposition resolves before its terminal and is publicly observable; otherwise it is listed as unhedgeable, never as a stop |

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| `sensitivity.md` | One-at-a-time flips, ranking, the observability and timing filters | stack 05 |
| `tails.md` | What counts as a tail, hedging suggestions, the "wiped out" row | stack 05 |
| `thesis-card.md` | Fields, how each is derived from the graph, what the user may edit | stack 05 |
| `strategy-export.md` | The export schema and how each leg cites the propositions that justify it | stack 05 |
| `market-beliefs.md` | Live prices as the `market` belief: sources, caching, attribution, cross-venue disagreement | stack 05 |

Decision records behind this part: ADR-0010 (grounding sources).
