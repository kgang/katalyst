# The card and the export — what the reader carries away

## Purpose

The last step of the walk is a thesis the reader can take with them: what carries it, what is priced in, what takes them out, what to watch, what they typed, and what it does not know. They leave with one declarative document — stamped with the map, the branch and the seed that produced it — that another program could read, and that **carries its own limitations as data** rather than as a footer somebody can strip.

---

## Data model

Two modules in `backend/src/katalyst/thesis/`: `card.py` builds what the panel draws, `export.py` writes the document, the page a person reads, and owns the committed description of the document. Neither is in `domain/`. A third module, `backend/src/katalyst/api/thesis_card.py`, is the only place a card is *served* from: it fetches what a pure function cannot reach and hands it over, and it computes nothing. **B7** below is its whole subject.

### The card assembles; it computes nothing another module owns

Every number on a card was worked out by the module whose subject it is — the edge by `edge.py`, the first-touch shares by `position.py`, the rail by `lift.py`, the greyed ceiling by `ceiling.py`, the shift by whatever owns the map's own verdict — and is either handed to `card_of` or asked of that module by name. One rule, and it is what keeps a card from becoming a second place any of that arithmetic lives. Two things the card does compute, because nobody else does: it ranks the tradeable endings, and it ranks the tails.

**Asking is not computing.** The size the reader's risk budget implies is the one number the card asks for rather than takes: `position.py` owns that sum — the share of capital whose loss from entry to stop is exactly the budget they typed — and the card calls it. The sum still lives in one place, and there is no argument through which a caller could put a size on a card that the reader's own two numbers do not imply. Everything else arrives already worked out, because everything else needs a sample of worlds the card is not given.

### Every number is a figure, and a figure cannot be built without an owner

A card holds no bare numbers. Each one is a **figure** carrying its value, its **owner**, what it is in plain words, where it came from, and the range around it where one was stated. There are exactly four owners and no fifth: **the reader** (they typed it), **the model** (it stated it, and nobody has calibrated it), **a venue** (a market published it), and **computed** (this program worked it out over the drawn worlds or from the numbers above). A price the reader typed is **theirs**, never a venue's: it is their report of what they believe they could deal at, and it never fills the market's slot.

Each figure also says what it **is** — a likelihood, a share, a move, a size, a ratio, a price, a count or a number of days — because this product writes a likelihood one way and everything else another, and a rendering holding a bare number cannot know which rule applies to it. A **likelihood** and a **share** go through the one rule for writing a likelihood: two significant figures, the nought before the point dropped, `<.01` where it rounds below a hundredth and `>.99` where it rounds above ninety-nine, because `1.0` claims a thing cannot fail and `.0` claims it cannot happen and nobody on this map may claim either. A **move** never goes through that rule: a move of `.0090` is a real quantity a reader acts on, so it keeps its two figures however small, and its sign. A price, a count and a number of days are written as they stand.

That is a shape rather than a rule to remember, so no screen and no document can print a number from a card without being handed its owner and its rule at the same time.

### No array reaches a card

The shapes underneath carry one row per drawn world; fifty thousand worlds by twenty claims is a million numbers, and a card is something a person reads. The card reads shares, counts and days off those shapes and carries none of the arrays.

### The sections

| Section | What it holds | Whose numbers |
|---|---|---|
| **The trade** | The ending, the instrument or contract, the side, and the test that settles it | the map's payoff |
| **What carries it** | The claims whose arrows carry most of the hypothesis's effect on this ending, with the shift each accounts for | computed |
| **What is priced in** | The model's number, the venue's bid and offer with their source and day, the fee, both edges and the side to lead with — or the named refusal and the break-even | computed, and the venue's |
| **What takes you out** | The claims over-represented where the stop went first: lift, interval, count, typical days ahead — or the reason there are none | computed |
| **What to watch** | The adverse turn that resolves before the ending and can be seen; and, apart from it, what is adverse but unhedgeable, with the reason | computed |
| **Your exit** | Stop, target, horizon, risk budget, the size those imply, the two first-touch shares with the window they were read to, and a greyed **quartered-Kelly ceiling** under the words *never size to this* | **the reader's**, except the shares and the greyed ceiling, which are computed |
| **Tails and shocks** | Claims that are unlikely and would hurt; and any shock the reader placed | the model's, and the reader's |
| **What else can I trade** | Every tradeable ending on the map, ranked by two rules kept apart | computed |
| **What this does not know** | The refusals in full sentences, the not-advice line, and the one execution sentence | ours |

The card is a **state of the panel, never a dialog**, and the strip above it is the only pinned thing in the product.

Two numbers carry sentences of their own. A **first-touch** number names in the same sentence both the sample its event days came from and **where the market's chance of each claim came from** (record 0019). There are four such sources and the card keeps all four apart: a **venue quote** on that claim; the **share of the drawn worlds** where the claim comes true inside the trade's own window, which is what the price paths read for themselves where nobody quotes it; the claim's **printed likelihood** from the world with nothing fixed by an edit, read on the claim's own resolve-by day; or a chance **the reader typed** over the top. The two readings of the model's own belief are two entries and not one, because only the first leaves the price path carrying no drift, and a card that could not tell them apart could not say whether the number beside it carries any (R41).

A first-touch number also names **the window it was read to** — the reader's own horizon, counted in days from the day the window opened. The paths run as far as the drawn worlds do; the shares stop where the reader says they are out. Two shares over a window nobody named are two numbers nobody can check.

The **greyed ceiling** carries its label *never size to this* as a field on the value; it is a quartered Kelly at the unfavourable end of the model's stated range, reads **zero with a reason** where that range does not agree which side of the price to be, and is **absent with the refusal's sentence** wherever no edge can be built (Kent, R29). Zero and absent are different answers and the card says which.

---

## Behaviour

### B1 — An ending that names an instrument is a first-class trade

The recorded Hormuz map, which the walk opens, has eleven tradeable endings and every one names an instrument rather than a venue contract (`backend/recordings/hormuz.jsonl`). If the card only worked on contracts, the walk's last three steps would have to change maps halfway through. So an instrument ending carries everything: a position, first touch, the two computed lists, a break-even of its own, and the honest line *no contract quotes this claim — edge not calculable*.

**Its break-even is a price, not a likelihood.** A contract's break-even is the number this side pays on, moved by the fee, one step each way. An instrument has no such number: the price at which the position is worth nothing is the reader's **own entry price**, moved by what it costs to get in and out — up for a long, down for a short. **Nobody has stated those costs**, so today the break-even is the entry price itself and the card says so in words, exactly as it says the venue's fee is unknown. A number that looks net and is not is worse than no number.

*Dated 2026-09-22: decision record 0018 says a break-even on an instrument ending "is not a defined quantity in this stack", because the entry price was not available when it was written. The entry price arrives on the reader's own position form, so the quantity is defined now and the card prints it. Nothing else in that record changes.*

### B2 — What else can I trade: ranked endings, each saying which rule ranked it

The reader asks the brief's second question. The card lists every tradeable ending on the map, ranked — and because two kinds of ending cannot be ranked on one number without inventing an exchange rate, **there are two lists and each row says which rule put it there**:

| The ending | The rule | The key |
|---|---|---|
| A venue quotes it and an edge was built | **the size of its edge** | the better of the two edges, whichever side it favours |
| It names an instrument | **the shift times the move** | how far the hypothesis moves it, times the move its payoff names |

Two rules, said out loud, never one blended number. Each list is ordered within itself; **no row is ever ordered against a row in the other list**, which is why they are two fields and not one.

Both of record 0018's thresholds appear here, and they do different things. An edge that is worth taking at one end of the model's own stated range and not at the other is **neither headlined nor ranked**: it is left out of the ranking with that reason, and in *what is priced in* the card leads with neither side and says the model's own range is why. An edge narrower than the venue's smallest price step **is ranked but never led with**, because it cannot be traded. And a row whose better edge is a loss is never led with either — the more a venue prices an ending out of reach, the less worth leading with it is, not the more.

An ending neither rule can rank is listed with its reason rather than dropped: a contract ending whose edge was refused carries the refusal's own sentence; a contract ending nobody priced says so, which is a different fact a reader can act on; an instrument ending nothing has worked out a shift for says that.

**The shift comes from elsewhere.** It is one of the three worked-out quantities that replaced the multiplied-out path likelihood (record 0022): the ending's chance with the hypothesis supposed true, minus its chance with it supposed false. The card takes it as a value, so the card and the exact core that will produce it can be built in either order.

### B3 — Tails, and a shock the reader places

A **tail** is a claim that is unlikely and would hurt a lot. Tails get their own rows with their likelihood, what they would do to the position, and what could be done about them — **never averaged into an expected value**, because an average hides the case that wipes the reader out. On the Hormuz map the OPEC+ claim is the tail: unlikely, and enough to undo the move the whole map was built to catch.

**Ranked by harm alone**, worst first, with the likelihood beside it and never multiplied into it. Likelihood times harm is an expected loss by another name, and an expected loss is precisely what a tail row exists to stop the reader from reading. No row is cut: how many tails a fixed strip can hold is a question about the screen, and the card answers it by ranking rather than by dropping. *This is what the code does and it is **proposed**, not settled: it closes one of this chapter's own open questions, and that is Kent's to take.*

A **shock** is different: the reader adds *"but Iran is struck"* with the mouse and supposes it true. The card re-runs the position on that branch and reports **the change to the position and nothing else — no probability**, because supposing something is not a statement about how likely it is, and the map's number for a claim an edit has just fixed is not one either. On the card the shape has **no field a probability could go in**. In the document the field is written and **fixed at nothing**, and the committed description will not allow anything else there — because an absent field reads as an oversight and a null one reads as an answer.

### B4 — The export

A declarative document — **`legs[]` and `conditions[]`** — with the map, the branch, the seed and the day stamped at the top so it replays exactly. A venue's combination-leg structure is an **order** format; mirroring it would imply this document could be submitted somewhere, and this product is not an execution layer. That settles the standing question about the export's schema.

The whole document, at its top level: `schema` · `map` · `hypothesis` · `legs` · `conditions` · `risk_exit` · `what_else` · `refuses` · `not_advice` · `execution`.

Each **leg** carries the ending, the instrument or contract, the side, the test that settles it, and then the whole of *what is priced in* — the model's number with its range, the mixture terms where the reader was in a supposed world, the quote with its venue, source and day, the fee, both edges, the break-even, or the named refusal that stands where no edge could be built. It also carries **the size the reader's risk budget implies** and **the greyed ceiling as a value with its label attached**, so a program that reads the number reads *never size to this* with it, or reads the reason it is zero or absent. A leg is complete on its own, which is why `risk_exit` does **not** repeat those two. One leg is what this version writes, because one position is what the reader holds; the field is a list so that two positions are two legs rather than a different document.

The **conditions** are the computed lists, each row carrying what it rests on: what carries the leg, what takes you out (lift, interval, count), what to watch (dates, and how each is seen), what is unhedgeable and why, the tails, and any shock the reader placed. First-touch numbers carry the method that produced them: the barrier shift, the window they were read to, the sample the event days came from, and **the market's chance of each claim with the source it came from**.

Every number in the document is a **figure**, exactly as on the card, so the owner survives the trip.

Three fields make it different from an ordinary export. **`refuses`** holds the limits as data — eight sentences:

> This document names no order type and guarantees no fill price. · The stop is the reader's own price rule, never derived by this tool. · No size here is a recommendation, and the greyed ceiling is a limit nobody may size to. · Every probability is the model's, uncalibrated, under the stated map and seed. · Impact sizes are the model's statements, not measured from data. · The path applies only what the market has not already priced, at a market chance whose source is named on each claim. · Quotes are as of the dates shown and were not refreshed. · The map is not exhaustive, and risks outside it are not represented.

**`not_advice`** holds one line: educational, not investment advice, and not a recommendation. **`execution`** holds the one thing this product will say about getting out: *a stop order's trigger is not its fill price* (record 0019). A program that ingests the document ingests the caveats with it — a footer can be stripped, a field has to be read.

### B5 — The committed description of the document

`backend/src/katalyst/thesis/export.schema.json` describes the document, and it is **generated from the shapes and committed beside them**. Three tests hold it there. One regenerates it and compares byte for byte, so a field that changes without the description changing fails. One reads the committed file and checks every document these tests build against it, including documents over maps nobody wrote by hand. And one walks the committed file for any rule of the description language the reader below cannot read, and fails on the first.

That third test is what makes the second honest. The reader understands only the part of the language these shapes use — named types, fixed values, closed lists, required keys, list items and how few a list may hold, references and choices — and **every rule it understands is shown catching a document that breaks it**, so it cannot pass by accepting everything. What it does not understand it passes over, which would otherwise mean that the day a shape grew a lower bound or a pattern, the description would carry a rule nothing checked. The drift test closes that.

Three things the description pins that an ordinary export would leave loose: the document's **own name** is a closed list of one, so a document calling itself something else is not a thesis; **`refuses` may not be empty**, because a document with no limits is a claim nobody here may make; and a shock's **`probability` is required and must be nothing**, because an absent field reads as an oversight where a null one reads as an answer.

### B5a — Where the market's chance came from is the walk's own record, not a caller's word

Record 0019 requires the card to name, beside every first-touch number, where the market's chance of each claim came from. It would be easy to make that a promise: let the caller pass a list of source words and print them. Then a caller that named sources the price paths never used would have them printed, and nothing anywhere would notice.

**It is not a promise; it is the record itself.** The shape the price paths come back in carries, for each claim that moves the price, the chance the walk applied and where that chance came from — including the ones the walk worked out for itself off the drawn worlds, which no caller could have typed because no caller knew them. The card takes that record whole and reads the sources out of it. A card on a contract ending, which is held to resolution and has no paths at all, passes nothing and says nothing.

The test that holds it, `test_the_card_names_the_market_chances_the_price_paths_actually_applied`, takes the whole route rather than a shape built by hand: it draws worlds, walks paths through them where one claim's chance is handed in and another's is not, reads first touch off those paths, builds a card, and checks that the sentence beside the shares names exactly what the walk recorded — and that the second claim's number is the one the walk read off the sample.

### B6 — The page a person reads

The same card written out as text, in the same order as the panel. There is **one place a number is written out**, and it cannot write one without its owner and without the rule its kind names, so a page that showed a number nobody owns, or a likelihood at six figures, could not be produced. A section with nothing in it says so in a sentence rather than printing a blank, because a blank reads as an answer.

**A sentence that belongs to a whole section is said once.** Which sample the drawn worlds came from, and where the market's chance of each claim came from, is one sentence on *what takes you out* and one on *your exit* — while every figure in those sections still carries the sample's short name, so no number read off drawn worlds is ever shown without one. Repeating a forty-word sentence on every line of a rail is how a page stops being one a person reads.

### B7 — Three routes, and the four things only a route can reach

A card is a pure function of five things — a map, a branch, a seed, an ending, and the exit the reader typed — so a route's whole job is to fetch what a pure function cannot and hand it over. Three routes, all under `/api/thesis/`, all needing no key and reaching no network:

| Route | Answers | Content type |
|---|---|---|
| `POST /api/thesis/card` | One card | JSON |
| `POST /api/thesis/export` | The same card as the declarative document | JSON |
| `POST /api/thesis/export/markdown` | The same document as a page of text | `text/markdown` |

All three take the same request, because all three are the same card written three ways: the stored example's name, the edits in force sent whole, the seed, the ending the card leads with, the reader's exit, and any suppositions they placed. Sending the branch whole is the same rule the world routes follow — there is nowhere to keep a branch yet — and it is what makes a card reproducible from what is stamped on it.

**The four things a route fetches.** A **world**, from the engine's own single route, so the numbers on a card and the numbers on the tiles beside it come from one arithmetic. A **sample of drawn worlds**, which is the one thing the trade layer asks of the engine and the only thing a price path can be walked through. A **recorded price**, by the contract identifier the ending's own payoff names — from the committed dated file and from nowhere else, so a card can be built with the machine offline. And a **graded route**, from the Verify door, which is where the shift and the arrow carrying most of it come from.

**What a route may not do.** It may not fetch a price — a route that could would be a route the demo cannot run without a network. It may not assume a fee is nothing, because an edge quietly netted against nothing looks net and is not. And it may not read an edge from the world the reader is looking at: the edge comes from the map as it stands whatever they have supposed, so an edit cannot quietly improve what a venue is charging, and a world that already carries a value fixed by an edit is refused by name (decision record 0018).

**One move, and the map is why.** Walking a price path needs to know which claims move the traded instrument and by how much, and the only thing on a map today that says so is the ending's own payoff. So exactly one claim moves the price — the ending's own — by the fraction of the price that payoff names, turned into a level gap against the price the reader entered at, signed by the payoff's direction. No other claim moves it, because nothing anywhere has stated that it does. That is an assumption said out loud rather than an omission, and it is the one the shape freeze changes when `move` becomes a level gap in its own right.

**The market's chance is not handed in**, so the walk reads it off the drawn worlds for itself, and the card names *the share of the drawn worlds* as the source beside every number built on it. A caller cannot name a source the walk did not use, which is anti-pattern 12 enforced by the route rather than promised by it.

**Every refusal is a list, and every list arrives at once.** A request or a form the reader can fix comes back as `422` carrying every reason together, each with a stable code a screen can switch on, the field at fault as the reader sees it, and one plain sentence. A **branch that does not fit the map** comes back as `422` too, but in the world routes' own shape — a `subject` and a `message` — because that fault is about a claim or an arrow and not about a field anybody can look at; the first entry says which of the two a screen is holding. A name matching no stored example is a `404` naming the ones that exist. Nothing is repaired silently and nothing arrives one fault at a time. **The codes and the sentences are the position route's, character for character**, so a screen switching on a code never meets two spellings of one rule.

**The window is the route's own rule, and the form cannot ask it.** The form's own check compares the reader's horizon with the day the *claim* is judged; whether the horizon leaves any days to walk is a different question, because a map's window runs only as far as its furthest resolve-by date. A horizon on or before the day the window opens is refused by name — `horizon_outside_the_window`, on the field `horizon` — between the drawn worlds and the paths.

**A shock is placed on top of the branch in force, never instead of it.** Its edits are folded after that branch's, so what a shock row reports is what the shock did and not what the branch and the shock did together; a shock's own `parent` is not read when there is a branch, because the branch in force is its parent by construction. And **what the position is worth** is the average price it is closed at under the reader's own exit — the stop's level where the stop went first, the target's where the target did, the price on the horizon where neither was touched. Not the plain average price on the horizon: that is the entry price exactly, in every branch, because the paths carry no drift by construction (`INV-thesis.16`), so a shock measured that way would report nothing at all for ever. The reader's own two levels are what break the symmetry.

**A contract ending has no path to touch.** It is held to its resolution, so first touch refuses by name and the rail comes back empty carrying that refusal, because an empty rail with no reason reads as *nothing takes you out* — a much more flattering sentence than the truth.

**The document is checked before it is served.** The committed description is generated from the shapes, so *the document answers the committed description* is two things together: the committed file is exactly what those shapes produce right now, and the document answers them. A drift between the two is a fault in this repository rather than in the request, and the route says so with a `500` rather than serving a document under a description that no longer describes it.

---

## INVARIANTS

Written *for all inputs drawn from generator S, statement P holds*. This chapter owns `INV-thesis.13`–`INV-thesis.15` and `INV-thesis.17`.

**INV-thesis.13 — The export is valid, and it carries its limits.** For every card built over every map from `graphs()` with a contract ending attached: the document answers the committed description, contains every line of `refuses`, and contains the not-advice line. **Tests:** `test_a_document_over_a_map_nobody_wrote_by_hand_answers_the_description`, `test_the_document_carries_every_refusal_the_not_advice_line_and_the_execution_sentence`, `test_the_reader_of_the_description_bites`, which shows the checking has teeth, and `test_the_description_states_no_rule_the_reader_cannot_read`, which fails the day it stops having them.

**INV-thesis.14 — Every number on the card names its owner.** For every card built as above: every number anywhere inside it belongs to exactly one of four owners — the reader, the model, a venue, or a computation over the drawn worlds — and carries it. The one number that is not a measurement, the seed, is named in the test rather than hidden. Every number also names what kind it is, so the page can write it by the one rule for numbers of that kind. **Tests:** `test_every_card_number_names_its_owner`, `test_a_number_the_reader_typed_is_never_labelled_a_venues`, `test_the_page_names_an_owner_beside_every_number`, and `test_every_likelihood_the_page_can_meet_is_written_by_the_house_rule` with `test_a_move_keeps_its_two_figures_however_small`.

**INV-thesis.15 — It replays.** For every card built as above: the document names the base map, the branch and the seed, and the same card written twice is the same bytes. **Tests:** `test_the_document_names_the_map_the_branch_and_the_seed`, `test_the_same_card_writes_the_same_bytes`. The other half — that rebuilding a world from those three reproduces the same card — belongs with the route that rebuilds one, and is checked there by `test_the_same_request_twice_gives_the_same_card`.

**INV-thesis.17 — A route fetches and never computes.** For every request the card route accepts: the card it answers with is the one `card_of` builds from a world the engine's own route built, a price the committed quote file holds, and a shift the Verify door worked out — and the route adds no arithmetic of its own. Two consequences are checked rather than asserted: the same request twice is the same card, and a card built on a branch shows the same model number against the same quote as a card built on none, so an edit cannot improve what a venue is charging. **Tests:** in `backend/tests/api/test_thesis_card.py` — `test_the_same_request_twice_gives_the_same_card`, `test_an_edit_never_improves_what_a_venue_is_charging`, `test_a_world_that_already_fixes_a_value_prices_nothing_at_all`, `test_the_drawn_worlds_come_from_the_map_the_reader_is_looking_at`, `test_the_level_gap_carries_the_payoff_s_own_direction`, `test_the_fee_is_unknown_and_never_quietly_nothing`, `test_a_shock_is_placed_on_top_of_the_branch_in_force`, `test_a_horizon_outside_the_window_the_map_covers_is_refused_by_name`, and `test_the_document_answers_the_committed_description_before_it_is_returned`.

---

## ANTI-PATTERNS

1. **Do not mirror a venue's order format.** Because a combination leg is an order, and a document shaped like one implies it can be sent. **Instead:** legs and conditions, with references into the map that justify each.

2. **Do not headline an expected value.** Because an average hides the case where the reader is wiped out, and the tails are the rows they most need to see. **Instead:** the two first-touch chances and the tail rows in their own strip, ranked by harm.

3. **Do not put the caveats in a footer.** Because a footer is dropped by whatever reads the document next. **Instead:** `refuses`, `not_advice` and `execution` are fields, and a test asserts they are there.

4. **Do not rank two kinds of ending on one blended number.** Because an edge in cents and a move in per cent are not the same quantity, and there is no honest exchange rate between them. **Instead:** two lists, each under its own named rule, and each row saying which ranked it.

5. **Do not attach a probability to a shock the reader placed.** Because they supposed it; that is not a forecast. **Instead:** report the change to the position, give the shape nowhere to put one, and write the field in the document as nothing at all.

6. **Do not let the walk change maps.** Because *the map you were just shown* is the product's claim to being auditable. **Instead:** make an instrument ending a first-class trade, so the recorded map carries the last three steps on its own.

7. **Do not compute on the card what another module owns.** Because a second place the arithmetic lives is a second place it can disagree with itself. **Instead:** the card is handed the edge, the shares, the rail, the ceiling and the shift, and it arranges them — or it calls the module that owns a sum, which leaves the sum where it is.

8. **Do not carry an array onto a card.** Because the shapes underneath hold one row per drawn world, and no reader and no browser should ever be sent a million numbers. **Instead:** read the share, the count or the day off them, and leave the arrays where they are.

9. **Do not write an absence as a zero.** Because *no drawn world had this claim come on before the stop* and *it came on the day the stop was touched* are opposite facts, and a zero says the second. **Instead:** nothing at all, with a sentence beside it saying why there is nothing.

10. **Do not print a number without saying what kind of number it is.** Because the rule that writes a likelihood turns `.0090` into `<.01`, which is true of a chance and a lie about an edge. **Instead:** every figure names its kind, and one table decides which rule writes it.

11. **Do not maintain the document's description by hand.** Because it drifts, and the drift is silent. **Instead:** generate it from the shapes, commit it beside them, and let a test compare the two byte for byte.

12. **Do not take a caller's word for where a number came from.** Because a source somebody types beside a number is a source nothing checks, and this product's whole claim is that every number can say why. **Instead:** take the record the module that produced the number hands back, and read the source out of that.

---

## Open questions

*Raised 2026-09-21; the second has a proposal, dated 2026-09-22, for Kent to take.*

1. **Does the export carry the whole map, or references into it?** Today: references — the base map's identifier, the branch, the seed, and claim identifiers on each row. A reader with the repository can rebuild everything; a reader without it cannot.
2. ~~**How many tail rows?**~~ **Proposed 2026-09-22, for Kent: none are cut.** Tails are ranked by harm, worst first, with the likelihood beside it. The alternative considered and declined was ranking by likelihood times harm and cutting at a number: that product is an expected loss by another name, and anti-pattern 2 forbids leading with one. How many rows a fixed strip shows is a question for the screen, not for the card.
3. **Is there a second card when the reader holds two positions?** One position is what this stack builds; two is a portfolio, and a portfolio is where the cut risk measures would start to mean something. The document's `legs` is already a list, so a second position is a second leg rather than a different shape.
