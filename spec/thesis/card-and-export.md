# The card and the export — what the reader carries away

## Purpose

The last step of the walk is a thesis the reader can take with them: what carries it, what is priced in, what takes them out, what to watch, what they typed, and what it does not know. They leave with one declarative document — stamped with the map, the branch and the seed that produced it — that another program could read, and that **carries its own limitations as data** rather than as a footer somebody can strip.

---

## Data model

Two modules in `backend/src/katalyst/thesis/`: `card.py` builds what the panel draws, `export.py` writes the document and owns its committed schema. Neither is in `domain/`.

The card is a sequence of sections, each saying who owns its numbers:

| Section | What it holds | Whose numbers |
|---|---|---|
| **The trade** | The ending, the instrument or contract, the side | the map's payoff |
| **What carries it** | The claims whose arrows carry most of the hypothesis's effect on this ending, with the shift each accounts for | computed |
| **What is priced in** | The model's number, the venue's bid and offer with their source and day, the fee, the better of the two edges — or the named refusal and the break-even | computed, and the venue's |
| **What takes you out** | The claims over-represented where the stop went first: lift, interval, count, typical days ahead | computed |
| **What to watch** | The adverse turn that resolves before the ending and can be seen; and, apart from it, what is adverse but unhedgeable, with the reason | computed |
| **Your exit** | Stop, target, horizon, risk budget, and the size those imply | **the reader's** |
| **Tails and shocks** | Claims that are unlikely and would hurt; and any shock the reader placed | the map's, and the reader's |
| **What this does not know** | The refusals in full sentences, and the not-advice line | ours |

The card is a **state of the panel, never a dialog**, and the strip above it is the only pinned thing in the product.

---

## Behaviour

### B1 — An ending that names an instrument is a first-class trade

The recorded Hormuz map, which the walk opens, has eleven tradeable endings and every one names an instrument rather than a venue contract (`backend/recordings/hormuz.jsonl`). If the card only worked on contracts, the walk's last three steps would have to change maps halfway through. So an instrument ending carries everything: a position, first touch, the two computed lists, the break-even its entry price makes computable, and the honest line *no contract quotes this claim — edge not calculable*.

### B2 — What else can I trade: ranked endings, each saying which rule ranked it

The reader asks the brief's second question. The card lists every tradeable ending on the map, ranked — and because two kinds of ending cannot be ranked on one number without inventing an exchange rate, **each row says which rule put it there**: an ending a venue quotes is ranked by **the size of its edge, whichever side it favours**; an ending naming an instrument is ranked by **the shift the hypothesis makes to it, times the move its payoff names**. Two rules, said out loud, never one blended number.

### B3 — Tails, and a shock the reader places

A **tail** is a claim that is unlikely and would hurt a lot. Tails get their own rows with their likelihood, what they would do to the position, and what could be done about them — **never averaged into an expected value**, because an average hides the case that wipes the reader out. On the Hormuz map the OPEC+ claim is the tail: unlikely, and enough to undo the move the whole map was built to catch.

A **shock** is different: the reader adds *"but Iran is struck"* with the mouse and supposes it true. The card re-runs the position on that branch and reports **the change to the position and nothing else — no probability**, because supposing something is not a statement about how likely it is, and the map's number for a claim an edit has just fixed is not one either.

### B4 — The export

A declarative document — **`legs[]` and `conditions[]`** — with the map, the branch, the seed and the date stamped at the top so it replays exactly. A venue's combination-leg structure is an **order** format; mirroring it would imply this document could be submitted somewhere, and this product is not an execution layer. That settles the standing question about the export's schema.

Each **leg** carries the ending, the instrument or contract, the side, the model's number with its range, the mixture terms where the reader was in a supposed world, the quote with its venue source and day (or the named refusal), the fee, the two edges, the break-even, and the size the reader's risk budget implies. The **conditions** are the computed lists, each row carrying what it rests on: what carries the leg, what takes you out (lift, interval, count), what to watch (dates, and how each is seen), what is unhedgeable and why, the tails, and any shock the reader placed. First-touch numbers carry the method that produced them: the barrier shift, and the engine's weighted forward sample the event days came from.

Two fields make it different from an ordinary export. **`refuses`** holds the limits as data: *this document names no order type and guarantees no fill price · the stop is the reader's own price rule, never derived by this tool · every probability is the model's, uncalibrated, under the stated map and seed · impact sizes are the model's statements, not measured from data · quotes are as of the dates shown and were not refreshed · the map is not exhaustive, and risks outside it are not represented.* **`not_advice`** holds one line: educational, not investment advice, not a recommendation. A program that ingests the document ingests the caveats with it — a footer can be stripped, a field has to be read.

---

## INVARIANTS

Written *for all inputs drawn from generator S, statement P holds*. This chapter owns `INV-thesis.13`–`INV-thesis.15`.

**INV-thesis.13 — The export is valid, and it carries its limits.** For every card built from every map from `graphs()` with a position from `positions()`: the document validates against the committed schema, contains every line of `refuses`, and contains the not-advice line. **Test:** `test_the_export_validates_and_carries_its_refusals`.

**INV-thesis.14 — Every number on the card can name its owner.** For every card built as above: each rendered number belongs to exactly one of four owners — the reader, the model, a venue, or a computation over the drawn worlds — and the rendering names it. A static check over the card builder in the manner of `test_beliefs_never_merged`, plus a browser test that no card figure is drawn without its owner. **Test:** `test_every_card_number_names_its_owner`.

**INV-thesis.15 — It replays.** For every card built as above: the export names the base map, the branch and the seed, and rebuilding from those three reproduces the same card, byte for byte, given the same recorded quote. **Test:** `test_a_card_replays_from_map_branch_and_seed`.

---

## ANTI-PATTERNS

1. **Do not mirror a venue's order format.** Because a combination leg is an order, and a document shaped like one implies it can be sent. **Instead:** legs and conditions, with references into the map that justify each.

2. **Do not headline an expected value.** Because an average hides the case where the reader is wiped out, and the tails are the rows they most need to see. **Instead:** the percentile outcomes, the two first-touch chances, and the tail rows in their own strip.

3. **Do not put the caveats in a footer.** Because a footer is dropped by whatever reads the document next. **Instead:** `refuses` and `not_advice` are fields, and a test asserts they are there.

4. **Do not rank two kinds of ending on one blended number.** Because an edge in cents and a move in per cent are not the same quantity, and there is no honest exchange rate between them. **Instead:** two rules, each named on its own row.

5. **Do not attach a probability to a shock the reader placed.** Because they supposed it; that is not a forecast. **Instead:** report the change to the position and say the probability is theirs to judge.

6. **Do not let the walk change maps.** Because *the map you were just shown* is the product's claim to being auditable. **Instead:** make an instrument ending a first-class trade, so the recorded map carries the last three steps on its own.

---

## Open questions

*Raised 2026-09-21.*

1. **Does the export carry the whole map, or references into it?** Today: references — the base map's identifier, the branch, the seed, and claim identifiers on each row. A reader with the repository can rebuild everything; a reader without it cannot.
2. **How many tail rows?** A fixed strip has a size: ranked by likelihood times harm and cut at a number, or cut wherever the harm stops mattering?
3. **Is there a second card when the reader holds two positions?** One position is what this stack builds; two is a portfolio, and a portfolio is where the cut risk measures would start to mean something.
