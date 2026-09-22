# Thesis — from map to trade

## The idea

A map of causes is not a trade. This part turns it into one, and is careful about which numbers are ours and which are the reader's.

**We compute** what the hypothesis carries through to each ending; the **edge** — the model's number against the price a venue would actually deal at — when the two answer the same question; which claims are over-represented in the worlds where the reader's stop was touched first; and which single adverse turn would hurt most *and* resolves in time *and* can be seen by anybody.

**The reader types** the stop, the target, the horizon and how much they are prepared to lose. None of those is derivable from a map of claims.

> **Changed 2026-09-21 (decision record 0019).** This page used to say the flip which damages an ending most *"is the stop-loss, and it is derived, not guessed."* Withdrawn. On this product's own worked example the derivation leaves one claim — the step the thesis rests on — so the derived "stop" reads *get out if the thing you are betting on stops being true*; and the sweep behind it computed one direction per claim, never consulting the reader's side. **A stop is a price the reader owns. What we derive is a watchlist, and a list of what takes you out.**

**The honest refusals are load-bearing.** A read of the venue on 2026-09-21 found nothing quoting Brent crude, and that the one Hormuz contract it does quote resolves on a different test from the claim on the map. Kent's decision R30 takes the venue's test as the curated map's own and adds an ending naming that contract, so the **curated** example carries one real venue price and refuses everywhere else; the **recorded** map the walk opens has eleven endings naming instruments and no contract, so it prints *no contract quotes this claim — edge not calculable* eleven times, honestly, until the one paid re-recording after the freeze.

**A path invents nothing.** The simulated price path applies only what the market has not already priced — a claim's **surprise**, not its whole stated move — so it manufactures no advantage of its own (Kent's decision R28, record 0019).

---

## Terms this part owns

**Edge · break-even · no-trade band · not comparable** (`edge.md`) · **quote · spot anchor** (`quotes.md`) · **position · your exit · first touch · draws · surprise · ceiling** (`position.md`) · **lift · what takes you out · what to watch · unhedgeable** (`what-takes-you-out.md`) · **tail · shock · thesis · strategy export** (`card-and-export.md`). Each is defined where it is used, and `spec/vocabulary.md` holds the one-line form.

---

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-14 | **A watchlist you can see.** A claim shown under *what to watch* resolves before the ending it is watched for and is publicly observable; a claim that is adverse but resolves too late, or cannot be observed, is listed as *unhedgeable*. No claim is ever presented as a stop |

*(INV-14 as amended by decision record 0019; the wording in `PRODUCT_REQUIREMENTS.md` §9 follows in the pull request that lands the amendment.)* Local invariants `INV-thesis.1`–`INV-thesis.17` are stated in the chapters, each naming the test that checks it.

---

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| [`edge.md`](edge.md) | The two edges and the break-even; what `priced` returns in every case; the mixture after a *Suppose* | stack 06 |
| [`quotes.md`](quotes.md) | Recorded first, fetched second, reader-entered always; what a quote carries; a market belief is a point; an economic level is an observation | stack 06 |
| [`position.md`](position.md) | The reader's position and exit; the one contract with the engine; daily paths that apply only the surprise; first touch; the greyed ceiling; what is refused | stack 06 |
| [`what-takes-you-out.md`](what-takes-you-out.md) | Lift over the worlds where the stop went first; the two-way sweep and the watchlist | stack 06 |
| [`card-and-export.md`](card-and-export.md) | The card's sections and who owns each number; **tails and reader-placed shocks**; ranked endings; the export that carries its own refusals; and the three routes that serve them — `POST /api/thesis/card`, `/api/thesis/export` and `/api/thesis/export/markdown` | stack 06 |

---

## Routes

Five routes carry this part to the browser, all under the `/api/` prefix. One is built.

| Route | What it answers | |
|---|---|---|
| `POST /api/thesis/position` | The reader's exit, how often each end of it is reached first, the rail of *what takes you out*, and the greyed ceiling | **built** — [`position.md`](position.md) §B6 |
| `POST /api/thesis/quote` | A venue's two prices for a contract, recorded first and fetched second | planned |
| `POST /api/thesis/quote/refresh` | The same prices, read again on request | planned |
| `POST /api/thesis/card` | The whole thesis a reader carries away, in six sections | planned |
| `GET /api/thesis/export` | That card as a document a program can read | planned |

---

Decision records behind this part: **0010** (grounding sources), **0013** (a payoff names the trade, a quote names the price), **0018** (an edge comes from the world with no supposition in force), **0019** (a stop is a price the reader owns), **0020** (a quote is recorded first; an economic figure is an observation).
