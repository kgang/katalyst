# The Inspector — why is this number what it is

## Purpose

Every number on this canvas has to be able to say where it came from. The Inspector is where it says
it.

Select a claim and the panel gives you the whole of it: the full wording, how it will be judged and
by whom, the outside view it started from, all three beliefs with their owners kept apart, the
evidence, and — once the engine runs — the decomposition that turns the number into an argument you
can disagree with line by line. Select an arrow and it gives you the mechanism in a sentence, how
hard it pushes read back in words, what kind of push it is, how long it takes, what it does over
time, its sources with the day each was fetched, and where it came from.

It is **one persistent side panel, and there are no pop-ups anywhere in this product** (UX-10). A
dialog you must dismiss is a veto condition; so is a number whose origin cannot be named in one
click (NFR-1). Where a value does not exist the panel says so **in words, with a reason** — never a
blank, never a zero, never a stand-in. In this stack that reason is usually *"no engine yet"*, which
is an honest sentence rather than a hole.

[`keyboard-and-access.md`](keyboard-and-access.md) covers reaching and reading the panel without a
mouse, and owns the rendering rule behind INV-7 — two significant figures, and the range never
omitted.

---

## Data model

`ClaimDetail` and `LinkDetail` are **projections of `ClaimView` and `LinkView`**, the per-claim and
per-arrow records on `WorldView`, all defined in [`diff-view.md`](diff-view.md). `BeliefView` — one
likelihood with its range and a name on it — is defined in
[`tiles-ports-wires.md`](tiles-ports-wires.md). This panel takes the fields it draws and adds
nothing of its own:

```ts
interface InspectorProps {
  /** What is selected. Nothing selected is a real state with its own copy, not a blank panel. */
  subject: { kind: "claim"; id: string } | { kind: "link"; id: string } | null;
  world: WorldView;          // frontend/src/world/types.ts
  onSelect: (subject: InspectorProps["subject"]) => void;
}

/** The claim half, drawn top to bottom in this order. */
interface ClaimDetail {
  claim: string;                       // the full wording, never ellipsized here
  kind: "hypothesis" | "event" | "market" | "not_tradeable";
  resolution: { criteria: string; source: string; by: string };   // all three required (INV-1)
  prior: BeliefView;
  baseRate: Known<{ referenceClass: string; k: number; n: number; sources: SourceView[] }>;
  beliefs: { model: Known<BeliefView>; user: Known<BeliefView>; market: Known<BeliefView> };
  evidence: readonly EvidenceView[];   // claim, address, direction, weight
  decomposition: Known<Decomposition>; // prior, a line per incoming arrow, the result
  rangeShares?: Record<string, number>;// the reserved band slot; stack 06, nothing reads it here
  pathProduct: Known<PathProduct>;     // INV-8; arrives on the world, never multiplied here
}

/** The arrow half. See "a push", below, for what `strength` is. */
interface LinkDetail {
  rationale: string;                   // the mechanism, one to three sentences
  strength: number;
  mode: "trigger" | "sustain";
  lag: number;                         // days
  shape: "impulse" | "step" | "ramp";
  halfLife: number | null;             // impulse only
  reflexive: boolean;
  sources: readonly { url: string; title: string; retrieved: Known<string> }[];
  provenance: "documented" | "historical" | "market_implied"
            | "argued" | "user" | "asserted" | "simulated";
}
```

`Known<T>` and `Absence` — a value, or a kind of absence with the sentence that goes beside it — are
defined once in [`diff-view.md`](diff-view.md). Every optional value on this panel is one, so no
code path can render an absence as anything but its reason.

**A push**, which the panel shows for every arrow, is a link's `strength`: a signed amount added on
the **log-odds scale** — the scale on which separate influences add up instead of multiplying. A
positive push moves the claim at the arrow's head toward coming true; a negative one moves it away.

**Tokens read:** `--surface-raised` (the panel), `--hairline` (its one edge and its rules), `--text`
and `--text-muted`, `--font-mono` for every number, `--space-1` … `--space-4`, the likelihood ramp
`--p-0` … `--p-4`, `--accent`, `--focus`. All are defined in
[`color-motion-type.md`](color-motion-type.md); this chapter defines none. A direction is rendered
only through `DirectionReadout`, which owns those tokens
([`color-motion-type.md`](color-motion-type.md)).

**Shared components:** `OriginMark` (the three-step provenance mark) and the belief chip. Each is
**one component**, drawn by the wire and the tile as well, so the mark on a wire and the word in
this panel cannot drift apart.

---

## Behaviour

Worked on the Hormuz map (the cast is in [`README.md`](README.md)). This chapter uses **B** *Brent
crude settles below $68 for five sessions* — the busiest claim on the map, three arrows in (**H**,
**C**, **R**) and three out (**M1**, **M2**, and back to R) — and the arrow **H → B**.

**One note on B's numbers.** The `.46 (.30–.63)` below is the fixture's stored illustrative value
today. Stack 03a is changing the fixture so every `beliefs.model` equals its own `prior` — *nothing
computed yet* — after which this row reads the prior's numbers. Nothing in this chapter rests on
`.46`.

### B1 — A claim, top to bottom

Select B's tile. The panel fills, in this order, and nothing opens over the canvas:

```
Brent crude settles below $68 for five sessions.                       event

RESOLVES
  Front-month Brent crude futures settle below $68.00 on five
  sessions, consecutive or not, within the window.
  judged by   ICE Brent front-month settlement prices
  by          2026-11-15

BASE RATE
  —  no reference class recorded for this claim

PRIOR
  .28 (.15–.42)          model
  the prior's range is stated, not computed — it says how sure the
  elicitation was

BELIEFS
  model    .46 (.30–.63)
  model interval, uncalibrated · how sure we are of .46 — not how much
  the world can move
  ┌ why is this band wide? ────────────────────────────────┐
  │  (reserved — ships in stack 06)                        │
  └────────────────────────────────────────────────────────┘
  user     —
  market   no market · no venue quotes this claim

EVIDENCE
  —  no clippings attached to this claim

WHY THIS NUMBER
  —  no engine yet
```

Four things to read off that:

* **The resolution triple is never optional.** Criteria, the source that adjudicates, and the date —
  all three, on every claim (INV-1, *checkable*: a claim nobody can score is not a claim).
* **Four things are genuinely absent on B, and each absence says which kind it is.** "No venue
  quotes this" is a *finding* — it drives a chain toward an ending nobody can trade — not a missing
  field. The **user** slot is the one absence drawn as a bare dash: an invitation to type your own
  number, where a sentence would read as an error rather than an offer.
* **Three beliefs, three owners, never merged** (INV-11). On B only the model has spoken; on **M1**
  all three do — `model .61 (.45–.74)`, `market .48 (.45–.52)`, `user —` — and the thirteen points
  between the first two is the edge somebody would be trading. That gap is the product's output, and
  no function anywhere may average it away.
* **The uncalibrated label belongs to the *computed* number, not the prior.** Decision record 0014
  defines it for a likelihood the engine worked out, so it sits under the model row and substitutes
  that row's number. A wide range never means the event is more volatile; it means more homework
  would move our number. The chip and its hover sentence are
  [`tiles-ports-wires.md`](tiles-ports-wires.md)'s; the panel repeats the label because the reserved
  slot sits directly under it.

### B2 — The decomposition: a number that can say why

When the world carries one, the panel replaces *"no engine yet"* under **WHY THIS NUMBER** with the
decomposition. The layout is the one [`../graph/belief.md`](../graph/belief.md) §B4 draws — prior,
one line per incoming arrow with its push and its reason, then the result — and this panel copies it
rather than inventing a second. §B4's numbers are its own illustration and are not B's: B's prior is
`.28 (.15–.42)`, it has no base rate, and it has three incoming arrows, not two. This stack renders
no such block, because no engine has computed one.

Three rules about it:

1. **One line per incoming arrow the world carries** — not a selection. B's real block has three,
   the third being R → B at −1.2.
2. **No line may be a number whose owner cannot be named** — `belief.md`'s rule, inherited here.
3. **This panel never computes the block.** A canvas that added up its own pushes would be a second
   engine, and two engines disagree.

### B3 — The reserved slot: "why is this band wide?"

Directly under the model belief's range there is a slot, and **in this stack it is empty**. What it
will hold, in stack 06, is one sentence naming the claim whose own starting number explains most of
the band:

> **92% of this band is B's own starting number; pin that down and the band goes from 29 points
> to 8.**

That sentence is computed from `World.range_shares` — each stated range's share of this claim's
band, which the engine gets out of the same two thousand versions of the map it already runs, at no
extra cost. It is the honest answer to *where should I spend the next hour of research*, and it
replaces the older sensitivity-times-width ranking (FR-21, decision record 0014 §C).

**It ships in stack 06, not here.** In this stack the panel leaves the slot in place, leaves a
comment in the component naming `range_shares` and pointing at this paragraph, and **renders
nothing** — not a placeholder sentence, not a spinner, not a greyed-out example. The slot is
reserved so the layout does not jump when the sentence arrives, and so the reason it is missing sits
where the next person will find it.

### B4 — An arrow, read back in words

Select the wire from H to B. Same panel, different subject; still no pop-up:

```
The Strait of Hormuz reopens…   →   Brent crude settles below $68…

WHY
  The war-risk premium priced into crude unwinds once transit data confirms
  the lane is open. It is a one-time repricing, not a standing discount.

PUSH      +1.6 — a strong push toward
KIND      trigger — a domino: it fires once when the strait opens, and the
          effect stays put and fades on its own. Standing the first domino
          back up does not stand this one back up
DELAY     2 days from the strait opening
OVER TIME impulse — a one-time spike, half gone after 30 days

SOURCES
  The Strait of Hormuz is the world's most important oil transit chokepoint
  eia.gov · fetched: —  nobody fetched this; a person put the address in

WHERE IT CAME FROM
  ●● argued — the model stated a mechanism, and no retrieval step has run
     for this arrow
```

* **The push is read back in words as well as a number.** `+1.6 — a strong push toward` is data
  already on the link and needs no arithmetic, which is why the wire's midpoint chip can show it
  before the engine exists. The five bands the words come from are proposed in
  [`tiles-ports-wires.md`](tiles-ports-wires.md) and this panel uses them: on this map `+0.7` reads
  *a nudge toward*, `−0.4` *a nudge against*, `−2.4` *a strong push against*. The chip writes
  `+1.6 · a strong push toward` and the panel `+1.6 — a strong push toward`; that difference is the
  plan's.
* **Mode is a sentence, not a word to look up.** `trigger` is the domino; `sustain` is the desk
  holding the apple — remove the desk and the apple falls, which is the arrow that makes the Hormuz
  showcase work.
* **`fetched` is the day our own retrieval step pulled the page down.** On this fixture nothing was
  fetched — a person put the address in by hand — so the field renders its reason rather than a
  date. An arrow claiming `documented` with nothing behind it is rejected by the map's rules.
* **Provenance is the word beside the same `OriginMark` the wire draws**, so mark and word are one
  component and cannot disagree. Three steps: **●●●** for `documented`, `historical`,
  `market_implied` · **●●** for `argued`, `user` · **●** for `asserted`, `simulated`. The mark is
  what you read at a glance — *is there a document behind this, or is it the model talking* — and
  the exact word of the seven lives here, where there is room for it. That is INV-12 doing its job:
  provenance visible on every wire with no hue involved.

The weakest arrow on the map is H → N1, and it says so: **●** `asserted`, with a rationale admitting
it cannot tell which way the causality runs. It is kept rather than deleted, because the ending it
reaches — a real outcome nobody can trade — is worth saying out loud.

### B5 — The path-product bar (INV-8)

Select a claim and a bar appears beside the story sentence showing the **multiplied-out likelihood
of the steps in the path from the hypothesis to it**. A chain of four plausible steps is not a
plausible chain, and the product is the number that says so. Selecting **M1**:

```
H → C → B → M1        the strait reopens, insurers reprice, Brent settles
                      below $68, and the Polymarket contract resolves YES
path likelihood       —  no engine yet
```

* **The product arrives on the world. This stack renders it and never multiplies anything itself.**
  If it is absent the bar says so with its reason; it does not fall back to computing.
* **When no path is shown the bar reads "no path shown".** It never disappears, because a missing
  bar looks like a bar nobody needed.
* **The honest wart, stated beside the number rather than hidden:** the factors are each read on
  their **own resolve-by day** — H by Nov 1, C by Oct 31, B by Nov 15, M1 by Oct 31 — so the product
  multiplies numbers read on different days. It is still the most honest single number available for
  a chain, and **it is not a joint probability**. The panel says that in those words (decision
  record 0014 §E).

### B6 — Every number is one click from its why

The rule behind the whole panel (NFR-1): **there is no number on this screen whose origin cannot be
named in one click.** A belief chip on a tile opens this panel at that claim, on that belief's row;
a wire's midpoint chip at that arrow; a delta rail row at that terminal; a number in the
decomposition at the arrow its line belongs to.

And the converse: **an absent number always renders its reason**, and the reason is a sentence a
reader can act on. *"no engine yet"* means the engine has not run. *"no market"* means no venue
quotes this, which is a finding about the world. A dash in the user's slot is an invitation, not an
error. None of these opens a window: the panel is always there, and selecting changes what is in it.

---

## INVARIANTS

Each is *for all X, statement P holds*, and each names what checks it: a component test, or a
numbered line of the **visual review checklist** in [`README.md`](README.md). Frontend test names
are `test_snake_case`. Unless another file is named, the test lives in **inspector** —
`frontend/src/components/__tests__/inspector.test.tsx`. This chapter uses `INV-workbench.50` …
`.59`.

**INV-workbench.50 — one panel, no pop-ups.** For every subject the Inspector can be opened on —
every claim and every arrow on the Hormuz map, and the empty selection — it renders no modal,
dialog, alert or pop-over, and is a persistent region of the page. That the *whole product* has none
is checked by eye: **visual review checklist line 2**. *Test:* inspector ›
`test_renders_no_dialog_for_any_subject`.

**INV-workbench.51 — every number in the panel is one click from its why.** For every number the
panel renders, there is a subject it belongs to and one interaction that opens the panel there. That
the same holds for every number on the *canvas and the delta rail* is **visual review checklist line
5**, checked by eye, plus the tile's and rail's own tests. *Test:* inspector ›
`test_every_rendered_number_resolves_to_a_subject`.

**INV-workbench.52 — three voices, never merged.** For every claim, the panel renders model, user
and market as three separate rows each labelled with its owner, and no function reached from this
panel takes two beliefs of different owners and returns one number (INV-11). *Test:* inspector ›
`test_renders_three_owners_and_never_averages_them`.

**INV-workbench.53 — an absence renders its reason.** For every `Known<T>` slot the panel reads, an
absent value renders its `Absence.reason` as words: no empty string, no zero, no stand-in number.
The single exception is the **user** belief slot, absence kind `not_said`, which renders a dash
inviting a number — the one absence that is an offer rather than a finding. *Test:* inspector ›
`test_renders_a_reason_for_every_absent_value`; **visual review checklist line 5**.

**INV-workbench.54 — the panel never computes a likelihood.** For every claim and every arrow, no
number displayed is derived by arithmetic in the browser; each is a field on the world or on the
map. In particular the decomposition renders only when `decomposition` is present, and no line of it
is computed here. *Test:* inspector › `test_never_derives_a_displayed_number`.

**INV-workbench.55 — the reserved band slot renders nothing in this stack.** For every claim, the
"why is this band wide?" slot renders no text, and no component reads `range_shares`. *Test:*
inspector › `test_the_band_slot_is_empty`.

**INV-workbench.56 — the mark and the word come from one component.** For every one of the seven
provenance values, the mark beside the word in this panel is produced by the same `OriginMark`
component the wire renders, from the same input. *Test:* inspector ›
`test_the_panels_mark_matches_the_wires_mark`; **visual review checklist line 3**.

**INV-workbench.57 — the path bar renders, never multiplies.** For every selected claim the bar
either shows the product the world supplied or says `no path shown`; there is no multiplication in
the component. *Test:* `frontend/src/components/__tests__/pathBar.test.tsx` ›
`test_renders_the_product_and_never_computes_one`.

**INV-workbench.58 — every claim can be scored.** For every claim the panel opens, the resolution
criteria, the adjudicating source and the resolve-by date all render, none optional and none
abbreviated (INV-1). *Test:* inspector › `test_always_renders_all_three_resolution_fields`.

**INV-workbench.59 — a source says when it was fetched, or says nobody did.** For every source on an
arrow, the panel renders the day our retrieval step fetched it, or the reason there is no day. A
source with no retrieval day is never rendered as though it had one. *Test:* inspector ›
`test_renders_a_fetch_day_or_its_reason`.

---

## ANTI-PATTERNS

1. **Do not open a dialog for anything — not evidence, not a confirmation, not an error.** *Because*
   a modal steals the map you were reading, and the map is what makes the detail mean anything; it
   is also a named veto condition. **Instead:** one persistent panel, and confirmations as undoable
   toasts.

2. **Do not compute the decomposition in the browser from the pushes on the arrows.** *Because* the
   pieces are all there and the temptation is real — prior, three pushes, a result — and the moment
   the canvas does its own arithmetic there are two engines that disagree about half a point, with
   nobody able to say which is right. **Instead:** render the block the world carries, and an
   absence with its reason until it does.

3. **Do not put a plausible sentence in the reserved band slot to show what it will look like.**
   *Because* a sentence naming a percentage nobody computed is a number nobody computed wearing
   words — the exact state a reader cannot trace. **Instead:** leave the slot, leave the comment
   naming `range_shares`, render nothing, and let stack 06 fill it.

4. **Do not average, blend or reconcile the three owners** — stated as an anti-pattern in
   [`tiles-ports-wires.md`](tiles-ports-wires.md), which owns the belief chip. Here it means three
   rows, three owners, and a difference computed outside and labelled one.

5. **Do not let the Inspector spell provenance one way while the wire draws it another.** *Because*
   two renderings of one field drift within a week, and then the canvas and the panel tell a reader
   two different things about the same arrow. **Instead:** one `OriginMark`, used by both, with the
   word only ever here.

6. **Do not print the path product as a joint probability.** *Because* its factors are read on
   different days and it is not the chance of the whole chain happening together; claiming that
   would be a fabrication in the place the honesty bar exists to prevent one. **Instead:** the
   number, the story beside it, and the wart said out loud.

7. **Do not truncate the claim's wording here.** *Because* the tile already ellipsizes to three
   lines and this is where the full text lives; a claim you cannot read in full cannot be argued
   with. **Instead:** the whole sentence, wrapping as far as it needs.

---

## Open questions

*Raised 2026-09-17.*

1. **What do pushes other than `+1.6` read back as?** The five bands are proposed in
   [`tiles-ports-wires.md`](tiles-ports-wires.md); this panel uses them. Whether five bands or
   [`../graph/link.md`](../graph/link.md)'s four anchors is the rule needs one answer.

2. **Which path does the path-product bar show when several reach the claim?** M1 is reached by
   H → B → M1 and by H → C → B → M1. Shortest, strongest, weakest-link, or all of them stacked?
   INV-8 settles the honesty rule, not the choice.

3. **Does the Inspector print the uncalibrated sentence in full?** The chip's hover gives the whole
   paragraph — *"Across 2 000 versions of this map … Nobody has checked whether that 8-in-10 holds
   up"*. The panel has room without a hover, and hover-only text is unreachable by keyboard; but on
   every claim it may be four lines of noise.

4. **Where does the "no market" reason come from on an ordinary claim?** A `not_tradeable` ending
   carries `not_tradeable_reason` and can quote it. An `event` claim such as B carries nothing, so
   the panel supplies the words itself — a sentence the interface wrote rather than a field it read.
   Either every claim gains somewhere to put the reason, or the wording is written down once in the
   vocabulary.

5. **Where does "falsified if" come from?** FR-10 lists it among the panel's contents and no field on
   a claim carries it. The resolution criteria read backwards, or a genuinely missing field on
   `Proposition`.

6. **Where do generation cost and the transcript live?** NFR-6 says the Inspector shows model,
   tokens, cache hits and dollars per generation. Nothing generates in this stack, so no section is
   specified and none is drawn.

7. **May the panel show an arrow's pushes before the engine, without the result line?** The
   per-arrow lines are data on the links; only prior-plus-pushes-equals-result needs the engine. A
   half block might be useful, or might read as a sum somebody forgot to finish. Left as an absence
   with a reason for now.
