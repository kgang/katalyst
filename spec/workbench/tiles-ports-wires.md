# Tiles, ports and wires — what a claim and an arrow look like

## Purpose

A claim and an arrow are the two things the whole product is made of, and until now they have only existed as data shapes. This chapter turns them into objects you can look at. A **tile** is a claim you can read without opening anything: what it says, who thinks it is how likely, what is behind it, and by when we will know. A **wire** is one arrow whose picture already tells you what kind of push it is, how hard it pushes, whether it holds or fires once, and whether anybody fetched a document before drawing it. A **port** is where a wire attaches, and it is typed, so what a wire means is visible at the socket before you follow it anywhere.

What a user can do that they could not before: glance at a map and see which step is weakly supported, which arrows are the model talking and which have something behind them, and which claim is being taken as given rather than computed — all without a click, and all without a single colour doing two jobs.

Three things this chapter deliberately does **not** own. Where the tiles go and what happens when you zoom out is [`layout-and-zoom.md`](layout-and-zoom.md). What the panel says when you click a tile or a wire is [`inspector.md`](inspector.md). What a tile looks like when two worlds are laid over each other is [`diff-view.md`](diff-view.md). The colour law and the motion budget that everything here obeys are [`color-motion-type.md`](color-motion-type.md).

---

## Data model

For an interface chapter, the data model is the props a component takes and the tokens it reads. `TileProps` below is a projection of `ClaimView`, and `WireProps` a projection of `LinkView` — the per-claim and per-arrow records on `WorldView`, this stack's own hand-written view model in `frontend/src/world/types.ts`, whose full shape is defined in [`diff-view.md`](diff-view.md).

### A number we have, or a reason we do not

Every number slot in this stack is optional, because the engine that computes them is being built in parallel. **An absent number renders as an absence with a reason** — never a blank, never a zero, never a placeholder. A number nobody computed is exactly the state a user cannot trace, which is a veto condition.

`Known<T>` and `Absence` are the shapes that carry that, and they are **defined once, in [`diff-view.md`](diff-view.md)**, because every number slot on the world uses them. This chapter only reads them. `Absence.kind` is one of `no_engine`, `no_market` or `not_said`, and each picks the words a chip shows.

`BeliefView` is defined here, because the belief chip is the only component that takes one:

```ts
/** One likelihood with its range and a name on it. Full precision; rounded once, at display. */
interface BeliefView {
  p: number;
  lo: number;
  hi: number;
  owner: "model" | "user" | "market";
}
```

### The tile

```ts
interface TileProps {
  id: string;                    // "H", "C", "B", "R", "M1", "M2", "N1"
  claim: string;                 // the full sentence; the tile draws at most three lines of it
  kind: "hypothesis" | "event" | "market" | "not_tradeable";
  beliefs: {
    model: Known<BeliefView>;
    user: Known<BeliefView>;    // absent with kind "not_said" until you say what you think
    market: Known<BeliefView>;
  };
  /** Set while a supposition holds. The tile then shows the word where a likelihood would go. */
  supposed?: { since: string };
  evidence: readonly EvidenceClip[];   // the tile draws at most two of them
  resolveBy: string;
  badges: readonly Badge[];
  focused: boolean;
  /** True when the hover lens has put this tile off the path. */
  dimmed: boolean;
}

interface EvidenceClip {
  line: string;                  // one line, from the evidence item's own claim
  host: string;                  // where it was published; the monogram is its first letter
  direction: 1 | -1;             // supports the claim, or cuts against it
}

/** The six words a badge may carry. "Supposed", "Happened" and "Retracted" carry a date;
 *  "Retracted" also names the edit responsible. "Added", "Retuned" and "Split" stand alone. */
type Badge =
  | { word: "Supposed" | "Happened"; date: string }
  | { word: "Added" | "Retuned" | "Split" }
  | { word: "Retracted"; date: string; by: string };
```

The badge words are copied from the **Interface words** table in [`../vocabulary.md`](../vocabulary.md) and are never paraphrased. The operations' code names — `do`, `observe`, `insert`, `retune`, `refine`, `believe` — never appear on screen. The buttons that produce these badges, and the branch panel that lists them in order, are pull request 4's; the tile only draws the badge.

### The tile, measured

| What | Value |
|---|---|
| Width | **280 px**, fixed, so the layout engine can place a tile before the browser has finished measuring its text |
| Height | Clamped: at least 96 px, at most 216 px *(proposed here)*, both multiples of 8 |
| Internal padding | **12 px** — `--space-1` plus `--space-hair`, the one half-step the spacing scale allows |
| Every other margin and gap | From the eight-pixel scale: `--space-1`, `--space-2`, `--space-3` |
| Border | One hairline at `--hairline`, which is 10% of the text colour |
| Shadow | **None.** Not a soft one, not a small one |
| Corner | `--radius` (6 px), except where the kind silhouette changes the outline |

### The six things a tile shows, and no more

| # | Region | How it is drawn |
|---|---|---|
| 1 | **The claim** | `--font-interface`, `--text-md` (15 px), `--weight-medium`, `--text`. Wraps to at most **three lines**, then ellipsized — **never truncated mid-word**. The full sentence lives in the Inspector |
| 2 | **Three belief chips** — model, user, market | A three-up row, always three, always in that order. Numbers in `--font-mono` with fixed-width digits, `--text-sm`, `--weight-medium`, `--text`; labels in `--text-muted` |
| 3 | **Evidence clippings** | At most two. Each is a **letter monogram** plus one line: monogram in `--font-mono`, `--weight-semibold`, `--text-muted`; line in `--font-interface`, `--text-sm`, `--text-muted`, one line, ellipsized. A leading `+` or `−` says whether the item supports the claim or cuts against it |
| 4 | **The resolve-by date** | `--font-mono`, `--text-sm`, `--text-muted`. The day we will know |
| 5 | **A kind silhouette** | The tile's own outline, four of them. **Shape carries the kind; hue never does** |
| 6 | **Badges**, when it has any | `--font-interface`, `--text-sm`, `--weight-medium`, with any date in `--font-mono` |

**Six things and no more, in this stack.** Anything else a reader wants is one click away in the Inspector. Two things are missing on purpose. There is **no density sparkline** yet: a sparkline draws a day-by-day series, and nothing here computes one — a curve shaped by hand would be a picture of numbers nobody worked out. UX-1 keeps the sparkline, and it arrives with the engine's world, which carries a `series` of one likelihood per day. And an evidence item's `weight` is not drawn, because a weight that moves nothing is a number pretending to be an input; it is listed in the Inspector, where it can be labelled for what it is.

**The monogram is a letter, never a fetched favicon.** The packaged demo must draw its first frame with no request to anything outside it, and a favicon is such a request. The monogram is the first letter of the publisher's host name, with any leading `www.` dropped: `lloydslist.com` gives **L**, `bbc.com` gives **B**, `eia.gov` gives **E**.

### The four kind silhouettes *(proposed here — decision record 0007 settles that there are four, not what they look like)*

| `kind` | Silhouette | Why that shape |
|---|---|---|
| `hypothesis` | The top-left corner is cut off at 45°, like a flag | The map starts here; there is exactly one per map |
| `event` | The plain rectangle | The ordinary claim, and the commonest |
| `market` | The bottom edge is nicked by two small semicircles, like a ticket stub | Something you could actually hold |
| `not_tradeable` | The right edge is open and hairline-dashed | The map stops here, and nothing leaves |

All four differ in outline alone, so all four survive a greyscale screenshot and survive the summary rendering that [`layout-and-zoom.md`](layout-and-zoom.md) switches to when you zoom out.

### The belief chips

The three voices are stored and drawn separately and **never averaged** — INV-11, the product rule that says no code path merges them. If the model says `.61` and the market says `.48`, the gap is the thing worth trading, and `.545` is a number nobody holds.

**The format is two significant figures and the range, always:** `.61 (.45–.74)`. Never `.6134`, never a bare `.61`. The rendering rule itself — how two significant figures is computed for awkward numbers like `.035`, and the fact that the range is never dropped — belongs to [`keyboard-and-access.md`](keyboard-and-access.md), which owns it for the whole part.

**The model chip's label is, word for word:**

> **model interval, uncalibrated** · how sure we are of `.35` — not how much the world can move

**and hovering it gives the sentence in full, word for word:**

> "Across 2 000 versions of this map — each one a set of numbers this model would have stood behind — the answer landed between .20 and .49 eight times in ten. Nobody has checked whether that 8-in-10 holds up; no claim on this map has resolved yet."

Only the numerals are substituted — `.35`, `.20` and `.49` are that chip's own `p`, `lo` and `hi`, rendered by the same two-significant-figure rule. Every other word is fixed. Two things that sentence does on purpose: it says *eight times in ten* rather than naming a percentile, and its last clause admits that nothing is calibrated. Neither is optional. The reason both matter is decision record 0014: the range says **how sure we are of the number**, not how much the world can move — the second is already inside the likelihood, and a reader who mixes them up will read a wide band as a volatile event.

**The four states of a chip:**

| State | What the chip shows | Where its reason is |
|---|---|---|
| A number | `.61 (.45–.74)`, with a small bar behind it painted from the likelihood ramp | — |
| An empty `user` slot — `kind: "not_said"` | **—**, an em dash, and it is a control: it invites your own number | On the control: *"no number from you yet — say what you think"* |
| An empty `market` slot — `kind: "no_market"` | **no market** | Beside the words, on the tile |
| No number yet — `kind: "no_engine"` | **no engine yet** | Beside the words, on the tile |

An absence is never silent. Two of the three print their reason on the tile; the empty user slot keeps the tile quiet and carries its reason as the control's own label, which is what a hover shows and what a screen reader reads.

And one state that replaces the number entirely: **while a claim is supposed, the chip shows the word** — *Supposed · Oct 1* — never `1.0` and never `.98`. A supposition is treated as a hard fact in every simulated world, so there is no number to show, and inventing one would answer a question the user did not ask.

### Typed ports

One **input group** and one **output group** per tile, drawn as small sockets on the left and right edges. Within each group, `trigger` and `sustain` attach to **distinct handle identifiers** — `in-trigger`, `in-sustain`, `out-trigger`, `out-sustain` *(names proposed here; that the identifiers are distinct is settled, what they are called is not)* — so a wire's meaning is visible at the socket before you follow it. `trigger` is a domino — it fires once when its cause becomes true and the effect stays pushed, fading on its own. `sustain` is an apple on a desk — the push exists only while its cause holds, and vanishes the moment it stops.

### The wire, and its five encodings

```ts
interface WireProps {
  id: string;                    // "H->B" — the two ends joined by an arrow drawn in text
  shape: "impulse" | "step" | "ramp";
  strength: number;              // signed, full precision
  mode: "trigger" | "sustain";
  reflexive: boolean;
  lagDays: number;
  provenance: "asserted" | "argued" | "documented" | "market_implied"
            | "user" | "historical" | "simulated";
  /** The conditional likelihood, when the engine has been asked for one. Absent in this stack. */
  conditional: Known<BeliefView>;
  dimmed: boolean;
}
```

A wire is a custom *edge type* — React Flow's own word for the component that draws a connection between two tiles — built on `getSmoothStepPath`, with a midpoint chip placed through `EdgeLabelRenderer`. Our word for it on screen is always **wire**. **The stroke says one thing and one thing only: what kind of push this is.**

| What | How it is drawn | Reads in greyscale |
|---|---|---|
| **Signal shape** | Stroke pattern: `impulse` dot-dash · `step` solid · `ramp` a gradient along the stroke | Pattern |
| **Strength** | Stroke width, from the size of `strength` regardless of its sign. **Four steps, not a continuous ramp** | Width |
| **`sustain` versus `trigger`** | A `sustain` wire is **double-stroked**; a `trigger` wire is single | Doubling |
| **`reflexive`** | The wire loops back on itself and carries a **lag chip** reading the delay in days | The loop |
| **Provenance** | **An origin mark at the wire's tail**, where the arrow leaves its cause — never the stroke | The count of dots |

Nothing in that table is a colour. Every wire takes `--text-muted` for its stroke, and a wire's hue says nothing at all.

Three drawing details are left to whoever builds it: whether a `ramp`'s gradient survives a path with rounded right-angle corners or reads as a lighting effect (a dash pattern that grows along the stroke is the fallback), whether a doubled four-pixel wire reads as a pipe, and where a midpoint chip goes when two wires run close together. Nothing on the Hormuz map forces any of the three.

### Strength, in two granularities

Strength is how far an arrow shifts its target's odds, on a scale where several arrows add up instead of multiplying. Roughly: `+1` triples the odds and `−1` cuts them to a third.

**It is signed on the claim, not on the world.** The arrow into *Brent settles below $68* is `+1.6` — positive, because it makes that claim come out **true** more often — and the thing the claim describes is a **falling** price. So a push's sign is *not* a direction of financial effect, it never takes `--dir-up` or `--dir-down`, and it is carried by the printed sign and the word instead. This is the definition; everything later in this chapter points back here.

**Width — four steps**, because a fifth is not distinguishable at a hairline:

| Size of `strength` | Stroke width |
|---|---|
| under 0.5 | 1 px |
| 0.5 to under 1.25 | 2 px |
| 1.25 to under 2.25 | 3 px |
| 2.25 and over | 4 px |

**Words — five bands** *(proposed here — [`../graph/link.md`](../graph/link.md) anchors ±0.5, ±1.0, ±2.0 and ±3.0; this table fills the gaps between them and adds a band below 0.25)*, because prose can carry a distinction a hairline cannot.

| Size of `strength` | Positive | Negative |
|---|---|---|
| under 0.25 | a faint push toward | a faint push against |
| 0.25 to under 0.75 | a nudge toward | a nudge against |
| 0.75 to under 1.5 | a clear push toward | a clear push against |
| 1.5 to under 2.5 | a strong push toward | a strong push against |
| 2.5 and over | close to decisive | close to ruled out |

The two granularities differ on purpose and nothing is lost by it, because **the signed number is printed beside the words every time**: `+1.6 · a strong push toward`. The stroke is a glance; the words and the number are the reading.

### `OriginMark` — provenance at the wire's tail

One small component, `frontend/src/components/OriginMark.tsx`, drawn by the wire **and** by the Inspector, so the mark and the word can never drift apart.

| Mark | `provenance` | What it means in one line |
|---|---|---|
| **●●●** | `documented`, `historical`, `market_implied` | Something was fetched, studied or priced |
| **●●** | `argued`, `user` | A mechanism was stated, or a person typed it |
| **●** | `asserted`, `simulated` | The model talking, or a probe |

Three steps, not seven, because the question a picture can answer is *is there a document behind this, or is it the model talking*. **The exact word is in the Inspector**, drawn by this same component with the word beside it. The mark also carries the exact word as its accessible name, so the seven-way distinction is never lost to a reader who is not looking at the picture.

The mark sits at the **tail**, where the arrow leaves its cause, and not at the head — the head already carries the arrowhead, and a receipt belongs at the point where the claim was made.

### The midpoint chip

The chip at the middle of a wire shows the **conditional likelihood**: the target's likelihood with this arrow's source **supposed** true, in the arrow-and-bar idiom of the forecasting site Metaculus.

That number is **not computed here and is not on the world.** It is computed lazily by the engine, one arrow at a time, because computing every one of them costs a whole extra propagation per arrow. The canvas asks for it when a wire is hovered or selected, and caches the answer.

**Until it has one — and always, in this stack, because the route does not exist yet — the chip reads the arrow's push back in words**, from data already on the link:

```
+1.6 · a strong push toward
```

**Never a guessed number.** Not the strength converted into a likelihood, not the target's current number, not a dash that looks like a number that failed to load.

### The hover lens

Hover a tile and everything **not** on its ancestor-or-descendant path dims to 15%. It costs about four lines of state and it is the single highest-value interaction for legibility on a map of this size, because it answers *what does this claim have to do with anything* instantly.

The lens **multiplies** the opacity already in place rather than replacing it. That matters when two worlds are laid over each other: a tile that is both off the path and part of the old world lands near 3% and disappears, which is correct — off-path and old is the least interesting thing on screen. [`diff-view.md`](diff-view.md) owns the old world's own opacity and states the multiplying rule.

The lens is transient — it follows the pointer and leaves nothing behind. Which tiles are on the path is **reachability**: follow arrows up and down from the hovered tile. Following arrows is not arithmetic.

**The lens follows every wire, reflexive ones included.** A reflexive arrow is a market feeding back on the world, and it is still a wire you can walk, so a claim reached only through one is on the path and stays lit. That is deliberately not how the diff states are computed — those set reflexive arrows aside — because the lens is *navigation* and a diff state is a *claim about what an edit moved*. [`diff-view.md`](diff-view.md) states that rule once and says why.

### The canvas does no arithmetic

Not one line of this chapter's components adds a strength, evaluates a shape, multiplies a likelihood or averages anything. Every number drawn arrives from the fixture route or from the world source. Three things that are *not* arithmetic and are allowed: comparing a strength against the four width thresholds, following arrows to find what is reachable, and laying out pixels.

### Tokens these components read

`--surface-raised` and `--hairline` for the tile · `--text`, `--text-muted` for every word · `--font-interface`, `--font-mono` and the three sizes and three weights · `--space-hair` through `--space-3` and `--radius` for the geometry · `--p-0` … `--p-4` for a chip's likelihood bar · `--focus` for the keyboard ring · `--duration-fast` for every opacity change. No component here reads `--dir-up`, `--dir-down` or `--tail`: a tile has no financial direction to report in this stack, and nothing on the map says which claim is a tail without arithmetic.

---

## Behaviour

Worked on the Hormuz map (the cast is in [`README.md`](README.md)), which is what `GET /api/fixtures/hormuz` already serves. This chapter uses all seven claims and all eight arrows, plus S, the strike the branch inserts. Every number in that fixture is illustrative and the fixture says so in its own comments.

### B1 — the hypothesis tile

H draws at 280 px with its top-left corner cut. The claim, *"The Strait of Hormuz reopens to unrestricted commercial transit."*, fits on two lines. Below it, three chips:

```
model   .35 (.22–.50)      user   .55 (.40–.70)      market   no market · no venue quotes this claim
```

Two evidence clippings, each a monogram and a line: **B** `+ An Omani-mediated round is reported, with both sides attending.` and **L** `− Three tankers remain held and no release has been announced.` Then the resolve-by date, 1 November 2026 — the day we will know. No badges, because nothing has been done to this tile yet.

The chips are the whole argument in one row: the model says `.35`, the user said `.55`, and that 20-point gap is the disagreement the user is having with the tool. Nothing averages them, and there is no fourth chip.

### B2 — a tradeable ending, and the edge

M1 draws with a ticket-stub bottom edge. Its chips read `model .61 (.45–.74)` and `market .48 (.45–.52)`, with the user slot an em dash inviting a number. The 13 points between the model and the market is the edge somebody would trade — shown as two chips side by side and never as one number, because the moment they are merged the reason for the screen is gone. The difference itself is named and computed on the thesis card, in a much later stack, and labelled a difference rather than a belief.

### B3 — three kinds of absence, in one screenshot

N1, the ending that cannot be traded, draws with an open dashed right edge and a market chip reading **no market** with the reason the fixture stores: *"No venue quotes a contract on a diplomatic round…"*. C's user chip is an em dash, and hovering it reads *"no number from you yet — say what you think"*. And on the second world of the diff, where this stack has no numbers at all, every model chip reads **no engine yet** with that as its reason.

Three absences, three different sentences, and not one blank, zero or placeholder anywhere. That last one is the point of the design rather than an apology for it: numbers nobody computed are exactly the state a user cannot trace, so this stack ships none, and the slot says why it is empty instead.

### B4 — a claim that was supposed, then pushed back down

Open the branch. H's tile now shows, in order:

> **Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"**

and **where its likelihood would be, the word** *Supposed · Oct 1* — not `1.0`, not `.98`. Every part of that line is data, not inference: the supposition gives the word and its date, the retraction gives the date and the arrow and the claim to name. The tile draws it; the branch panel that lists the three edits in the order they were made is pull request 4's, and [`diff-view.md`](diff-view.md) covers what else changes on the tile when two worlds are shown at once.

### B5 — all eight arrows at once

| Arrow | Stroke pattern | Width | Doubled? | Mark | Midpoint chip |
|---|---|---|---|---|---|
| H → B | dot-dash (`impulse`) | 3 px (1.6) | no (`trigger`) | ●● `argued` | `+1.6 · a strong push toward` |
| H → C | solid (`step`) | 2 px (1.1) | **yes** (`sustain`) | ●● | `+1.1 · a clear push toward` |
| H → N1 | gradient (`ramp`) | 2 px (0.7) | no | **●** `asserted` | `+0.7 · a nudge toward` |
| C → B | solid (`step`) | 2 px (0.7) | **yes** | ●● | `+0.7 · a nudge toward` |
| B → M1 | dot-dash | 2 px (0.9) | no | ●● | `+0.9 · a clear push toward` |
| B → M2 | gradient | 2 px (0.8) | no | ●● | `+0.8 · a clear push toward` |
| B → R | gradient, **looping**, lag chip "14 days" | 2 px (0.6) | no | ●● | `+0.6 · a nudge toward` |
| R → B | solid | 2 px (1.2) | no | ●● | `−1.2 · a clear push against` |

Two readings fall straight out of that table.

**H → N1 is the weakest-supported arrow on the map**, and its single dot says so before anybody reads a word — the fixture marks it `asserted` because its sentence is a story rather than a mechanism.

**C → B and R → B share a stroke width while saying different things in words** (`0.7` is a nudge, `1.2` is a clear push): the width is a four-step glance, the words and the printed number are the reading. R → B is also the map's one negative arrow, and it is drawn exactly like any other solid two-pixel wire — see *Strength, in two granularities* above for why a sign is never a hue.

### B6 — hovering B

Hover the Brent tile. Its ancestors are H, C and R; its descendants are M1, M2 and R. Everything on that path stays at full opacity and **N1 alone dims to 15%** — the one claim on this map that has nothing to do with the oil price. That is the answer to *what does this claim reach*, delivered in one hover and with no arithmetic: it is reachability, computed by following arrows.

### B7 — ports say what a wire means before you follow it

H has three arrows leaving it. Two of them — to B and to N1 — leave from `out-trigger`; one — to C — leaves from `out-sustain`. On the branch, the strike's arrow into H arrives at H's `in-sustain`. A reader who knows nothing else can see at the socket that the strait's openness is *held up* by something rather than *caused once* by it, which is the entire reason the branch behaves the way it does.

---

## INVARIANTS

Each is *for all inputs of this kind, this statement holds*, and each names what checks it: a **component test** under `frontend/src/**/__tests__/`, or a numbered line of the **visual review checklist** — the twelve things the coordinator looks for on every screenshot. A checklist line is a checkable thing; it is checked by a person.

Local numbers in this part are `INV-workbench.<n>`. This chapter holds **1 – 12**; [`color-motion-type.md`](color-motion-type.md) holds 13 – 19.

### INV-workbench.1 — The tile's geometry

For every tile rendered from any map: its width is exactly 280 px, its height is between 96 and 216 px, every margin and gap is a value from the spacing scale, its border is one hairline at `--hairline`, and it casts no shadow.

- **Test:** `frontend/src/components/__tests__/tile.test.tsx` › `test_tile_is_280_wide_and_on_the_eight_pixel_grid`.
- **Also:** visual review checklist line 8 — measure the tile, do not eyeball it.

### INV-workbench.2 — The claim is never cut mid-word

For every claim string, of any length: the tile renders at most three lines, and the rendered text either equals the claim or is a prefix of it ending at a word boundary followed by an ellipsis.

- **Test:** `frontend/src/components/__tests__/tile.test.tsx` › `test_claim_wraps_to_three_lines_and_never_cuts_mid_word`.

### INV-workbench.3 — Six things, and no seventh

For every tile: the rendered regions are exactly those in the six-things table, and no other content region is present.

- **Test:** `frontend/src/components/__tests__/tile.test.tsx` › `test_tile_draws_the_six_regions_and_no_seventh`.

### INV-workbench.4 — Two significant figures, and the range, always *(refines INV-7)*

For every belief rendered in a chip: the likelihood shows at most two significant figures, and the range is present.

- **Test:** `frontend/src/components/__tests__/beliefChip.test.tsx` › `test_chip_never_shows_more_than_two_significant_figures` and `test_chip_never_omits_the_range`. This is decision record 0005's promised frontend rendering test, and it is the one test that holds the honesty requirement up — NFR-1: *every belief renders at two significant figures with its interval, never `.347`.*
- **Also:** visual review checklist line 4 — is any number on screen showing more than two significant figures, or missing its range?

### INV-workbench.5 — An absent number is an absence with a reason

For every chip whose number is absent: the chip renders that absence's words, or its dash-with-invitation, **and** a non-empty reason — on the tile, or as the element's own accessible name — and renders no digit at all. There is no input for which the chip renders blank, `0`, or a stand-in value.

- **Test:** `frontend/src/components/__tests__/beliefChip.test.tsx` › `test_every_absence_renders_words_and_a_reason`.
- **Also:** visual review checklist line 5 — is there a number nobody computed, an empty slot filled in rather than left as an absence with a reason?

### INV-workbench.6 — Three voices, never merged *(refines INV-11)*

For every tile: exactly three chips are rendered, labelled model, user and market, in that order, and no rendered element shows a value derived from more than one of them.

- **Test:** `frontend/src/components/__tests__/tile.test.tsx` › `test_tile_draws_three_chips_and_never_a_fourth`.

### INV-workbench.7 — A supposed claim shows the word

For every tile whose claim is supposed: the chip renders the word and the date, and renders no likelihood at all.

- **Test:** `frontend/src/components/__tests__/beliefChip.test.tsx` › `test_a_supposed_claim_renders_the_word_not_a_number`.
- **Also:** visual review checklist line 12 — does a claim that was supposed and then overridden say so on its tile?

### INV-workbench.8 — Kind rides shape, never hue

For all four kinds: the four rendered outlines differ from one another, and the four renderings are identical in every colour value.

- **Test:** `frontend/src/components/__tests__/tile.test.tsx` › `test_four_kinds_four_silhouettes_one_palette`.
- **Also:** visual review checklist line 3 — the greyscale conversion.

### INV-workbench.9 — A clipping never reaches the network

For every evidence clipping rendered: its monogram is derived from the host name in the clipping's own data, and the rendered output contains no element that would fetch a resource from outside the app.

- **Test:** `frontend/src/components/__tests__/tile.test.tsx` › `test_clipping_draws_a_monogram_and_requests_nothing_outside`.

### INV-workbench.10 — A wire carries all five encodings, and provenance is not one of the strokes

For every link: the rendered wire carries a stroke pattern determined by `shape` alone, a width determined by the size of `strength` alone, a doubling determined by `mode` alone, a loop and a lag chip when `reflexive`, and an `OriginMark` at its tail determined by `provenance` alone. The same `OriginMark` component renders the mark in the Inspector.

- **Test:** `frontend/src/graph/wires/__tests__/causalWire.test.tsx` › `test_wire_carries_all_five_encodings` and `test_wire_and_inspector_draw_the_same_origin_mark`.

### INV-workbench.11 — The midpoint chip never invents a number

For every wire whose conditional likelihood is absent: the chip renders the signed strength and its words, and renders no likelihood.

- **Test:** `frontend/src/graph/wires/__tests__/midpointChip.test.tsx` › `test_midpoint_chip_reads_the_push_in_words_until_the_engine_answers`.

### INV-workbench.12 — The canvas does no arithmetic

For every module under `frontend/src/graph/` and for the tile and chip components: no expression combines two values read from a belief or a link's `strength` with `+`, `−`, `×` or `÷`. Comparing a strength against a threshold, walking the graph to find what is reachable, and computing pixel geometry are excluded by name.

- **Test:** `frontend/src/graph/__tests__/noArithmetic.test.ts` › `test_canvas_never_combines_two_model_numbers` — a walk over the syntax tree of every module in those folders, the same technique the backend uses to prove that nothing averages two beliefs.

---

## ANTI-PATTERNS

1. **Do not add a seventh thing to the tile**, because a tile that answers everything is a tile nobody reads, and the map stops being scannable at the exact moment it gets interesting. **Instead:** put it in the Inspector, one click away.
2. **Do not truncate a claim mid-word** to fit the clamp, because the half-word that is left reads as a rendering bug and costs the reader more than the missing line. **Instead:** wrap to three lines, ellipsize at a word boundary, and keep the full text in the Inspector.
3. **Do not fetch a favicon for an evidence clipping**, because the packaged demo must draw its first frame with no outside request, and a missing favicon leaves a hole where a receipt should be. **Instead:** a letter monogram from the host name, drawn from data we already have.
4. **Do not fill an empty slot with anything at all** — not `0.5`, not the model's number, not a blank, not a spinner. Because "no venue prices this" and "the engine has not run" are *findings*, and one of them is the finding that drives a chain to a not-tradeable ending. **Instead:** the words, and the reason beside them.
5. **Do not show `1.0` or `.98` for a supposed claim.** A supposition is a hard fact in every simulated world, so there is no number, and a `.98` invites the reader to wonder about the other two per cent. **Instead:** the word and the date.
6. **Do not put provenance back on the stroke**, because the stroke already says what kind of push the arrow is, and a wire that is dot-dash and dashed at once says neither. **Instead:** the three-step mark at the tail, and the exact word in the Inspector.
7. **Do not compute the conditional likelihood in the browser**, because it is a whole extra propagation per arrow and the browser has no propagation engine. **Instead:** ask the engine for it lazily on hover, cache the answer, and read the push in words until it arrives.
8. **Do not colour a wire**, because hue means "the money moves this way" and an arrow's sign does not — see *Strength, in two granularities*. **Instead:** the printed sign and the word.
9. **Do not add a fourth chip** showing a consensus, a blend or an average, because the gaps between the three are the output of the product. **Instead:** three chips, and a difference computed elsewhere and labelled a difference.
10. **Do not scale a tile's text with the zoom.** Below 11 pixels a tile is a smudge that looks like a loading state. **Instead:** change what the tile renders — [`layout-and-zoom.md`](layout-and-zoom.md) owns that threshold, and it also owns the rule that tiles do not drag.

---

## Open questions

*Raised 2026-09-17.*

1. **The model chip's hover sentence names two thousand versions of the map — and in this stack the number came from the fixture.** The sentence is word for word what a *computed* number can say about itself. A number read from `beliefs.model` in the stored example was not computed by anybody, and the fixture says so in its own comments. As written, a hover over H would claim an arithmetic that has not run, which is precisely the state a user cannot trace. Two candidate fixes, neither decided here: the version count and the band come from the world and render as an absence with a reason when the world is a fixture; or the chip gains one extra sentence naming where its number came from. **Needs Kent.**
2. **Two significant figures for an awkward number.** The table is in [`keyboard-and-access.md`](keyboard-and-access.md) B6; `.995` and `.06` are still open there.
3. **The "no market" reason when the world carries none.** The fixture stores a reason only on the one not-tradeable ending. For H, C, B and R the chip falls back to the plain fact — *"no venue quotes this claim"* — which is true but generic. Should an unpriced claim carry its own sentence, and if so, who writes it?
4. **How many badges fit.** The overridden-assertion badge is long — *Supposed · Oct 1 → Retracted · Oct 2 · by "…"* — and a 280-pixel tile with a three-line claim and a height clamp has room for roughly one such line. What happens to a tile carrying three badges is not settled.
5. **Two clippings from the same publisher** give the same monogram twice, and a host name that starts with a digit gives a monogram that reads as a number. A two-letter monogram fixes both and is harder to read at a glance.
