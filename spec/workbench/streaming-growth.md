# Streaming growth — the map drawing itself

## Purpose

Until now a map arrived finished. You opened the stored example and seven tiles were already
there. This chapter is about the other way in: you type a sentence, and the map **builds itself in
front of you** — a reserved rectangle first, then a claim, then the arrow that justifies it, then
the next one, out to the things you could trade — with every proposal the rules refused visible on
the way past, and a receipt at the end saying what it cost.

The growing is not a decoration wrapped around a wait. **The growing is the loading state** (UX-8,
FR-5). There is no spinner in this product, and there is no moment where a blank screen turns into
a finished picture — because that moment is the "spinner then dump" the anti-patterns list vetoes
(PRD §10 anti-pattern 9), and because a map that simply appears hides the half of the work worth
watching: our own rules turning the model down.

Three things a reader can do after this chapter that they could not before. **Type any sentence and
watch what it would cause.** **Name a destination and get a graded path to it, or an honest "no path
reaches this" naming the nearest claim that was reached** (FR-7, UX-13). And, **with no model key at
all, watch the same four examples run from recordings** (record 0012) — the same stream, the same
canvas, the same refusals, labelled as a replay everywhere a reader looks.

This chapter owns the eight stream events as the browser types them, the `growth` reducer that folds
them into a world, the skeleton tile, the refusal strip, the receipt strip, the Verify door's two
cards, the input bar, and the replay badge. It owns no arithmetic: every number on every one of
those surfaces is a field on an event.

---

## Data model

### The transport, in one paragraph

The browser sends `POST /api/generate` and **reads the reply as a stream** rather than opening an
`EventSource`. Two reasons, both hard. The request carries a body — the sentence, an optional
destination, the reader's own likelihood, a seed — and an `EventSource` can only send a GET with no
body. And an `EventSource` reconnects by itself, which would silently re-run a generation and spend
the money twice. The wire format is still server-sent events — an `event:` line naming the event and
a `data:` line carrying one JSON object — so the whole thing stays readable in a terminal with
`curl`. The route, the eight events and their order are `spec/generation/streaming.md`'s, written in
this stack's server half; this chapter says what the browser does with them.

### The eight events, hand-typed

```ts
// frontend/src/stream/events.ts
//
// Written by hand, exactly as `WorldView` was, because the server's description of
// itself and this canvas are built at the same time. The server's own copy is
// `backend/src/katalyst/engine/events.py`. A type-level test,
// `frontend/src/stream/__tests__/eventsMatchSchema.test-d.ts`, fails the build when
// the two drift. It cannot pin the eight envelopes — server-sent events have no body
// OpenAPI can describe — so it pins every piece they are built from, which are
// aliased to the generated types below rather than retyped, and the four shapes that
// do travel as JSON: the receipt, the request, the drafted insert and the working.

import type { components } from "../api/schema";

/** An identifier the engine minted for a claim. Nothing in the browser ever makes one. */
export type PropositionId = string;

type Proposition = components["schemas"]["Proposition"];
type Link = components["schemas"]["Link"];
type Violation = components["schemas"]["Violation"];
type World = components["schemas"]["World"];

/** The run has started. The first thing that arrives, and it arrives at once. */
export interface GenerationStarted {
  readonly event: "generation_started";
  /** The engine's name for this run. What the transcript is asked for by. */
  readonly generation_id: string;
  /**
   * The seed every random draw in this run came from — always a number here, even
   * when the request left it out. Whoever chose it, this event is where the browser
   * reads it: the one the request sent, or the one `engine/ids.py` minted when it
   * sent none, or, on a replay, the one in the recording's header, which wins over
   * both. The browser prints what this says and never works out which case it was.
   *
   * **And by the time it is a number here it may already be wrong.** A seed is
   * up to nineteen digits and a browser holds a whole number exactly only up to
   * sixteen, so `JSON.parse` has rounded it before any of our code sees it.
   * Nothing computes with a seed — it is printed under the map so a reader can
   * ask for the same one again — and a rounded seed printed there is a number
   * on screen that is simply wrong, in the one place that exists so an answer
   * can be had twice.
   */
  readonly seed: number;
  /**
   * The same seed, exactly as it was written on the wire: its digits, not a
   * number.
   *
   * Read off the raw text of the `data:` line by the reader, because that is
   * the last moment the digits exist. Absent only when a caller handed the
   * events over by hand, and then the parsed number is the whole of what is
   * known.
   */
  readonly seed_as_written?: string;
  /** The sentence the reader typed, in their own words. */
  readonly hypothesis: string;
  /** The Verify door's destination, in their words. Null when they used the Explore door. */
  readonly target: string | null;
}

/** One proposal the rules accepted. A claim, its incoming arrows, or both. */
export interface ProposalAccepted {
  readonly event: "proposal_accepted";
  /** Where this sits in the transcript, counting from 0. */
  readonly at: number;
  /** The new claim, with its identifier minted by the engine. Null for an arrows-only proposal. */
  readonly proposition: Proposition | null;
  /** Its incoming arrows, identifiers minted by the engine. */
  readonly links: readonly Link[];
  /** The claims still open to expand. What the skeletons are drawn from. */
  readonly frontier: readonly PropositionId[];
}

/** One proposal the rules refused. An event, never an error. */
export interface ProposalRejected {
  readonly event: "proposal_rejected";
  readonly at: number;
  /** What the model wrote. Never minted, never drawn as a tile, only ever quoted. */
  readonly claim_in_words: string;
  /** The validator's own codes and its own sentences. One per rule broken. */
  readonly violations: readonly Violation[];
  /**
   * The claims still open to expand — the same field the accepted event carries, and
   * for the same reason. A claim closed by its third refusal in a row leaves the
   * frontier on this event, so its rectangle comes down at once instead of standing
   * there waiting for something that is not coming.
   */
  readonly frontier: readonly PropositionId[];
}

/** Every number, worked through the finished map, once. */
export interface BeliefsPropagated {
  readonly event: "beliefs_propagated";
  readonly world: World;
}

/** The Verify door's answer. Emitted only when the reader named a destination. */
export interface Verdict {
  readonly event: "verdict";
  readonly kind: "reached" | "no_path";
  /** The steps of the path, in order. Empty on `no_path`. */
  readonly path: readonly PropositionId[];
  /** The multiplied-out likelihood of those steps (INV-8). Null on `no_path`. */
  readonly product: number | null;
  /** On `no_path`: the closest claim the map did reach. */
  readonly nearest: PropositionId | null;
  /** One plain sentence, the engine's own. */
  readonly why: string;
}

/** What the run cost (NFR-6). */
export interface Receipt {
  readonly event: "receipt";
  readonly model: string;
  readonly calls: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly cache_read_tokens: number;
  /**
   * How many web searches this run made. Billed apart from tokens, so `dollars`
   * cannot be accounted for without it — which is why it is a field of its own
   * rather than something a reader is expected to infer.
   */
  readonly searches: number;
  readonly dollars: number;
  readonly seconds: number;
  /** Live, or played from a recording. The only place in the stream this is said. */
  readonly mode: "live" | "replay";
  /**
   * How hard the model was asked to try, as a plain word: `default` when
   * nothing was asked for and the service's own applied, otherwise `low`,
   * `medium`, `high`, `xhigh` or `max`. A recording is made rich and a live run
   * is made fast (Kent, G13), so two maps of the same sentence at the same seed
   * can differ for a reason that has nothing to do with the sentence.
   */
  readonly effort: string;
  /** The day the recording was made, as the map writes a day: `2026-09-18`. Null when live. */
  readonly recording_date: string | null;
  /** A hash of the prompt this run was made against. Null never; it is always known. */
  readonly prompt_hash: string;
}

/** Why the generation stopped. Not whether the Verify door found anything — that is `verdict`. */
export interface Done {
  readonly event: "done";
  readonly reason:
    | "reached_terminal"
    | "depth_cap"
    | "width_cap"
    | "claim_cap"
    | "spend_cap"
    | "refusal_cap"
    | "no_terminal";
  readonly claims: number;
  readonly links: number;
  readonly rejected: number;
}

/** The run broke. One plain sentence, never a stack trace. */
export interface Failed {
  readonly event: "failed";
  readonly message: string;
}

export type StreamEvent =
  | GenerationStarted
  | ProposalAccepted
  | ProposalRejected
  | BeliefsPropagated
  | Verdict
  | Receipt
  | Done
  | Failed;
```

**The `event` field is put there by the reader, not by the server.** On the wire the name is the
`event:` line and the payload is the `data:` line, so the payload itself carries no name. The reader
joins them — `{ event: name, ...JSON.parse(data) }` — which is what makes `StreamEvent` a union a
`switch` can walk. It is also the one place a name the browser does not know can be caught; what
happens to one is B6.

**Field names are the wire's, in full.** `input_tokens`, not `inputTokens`. A second spelling of a
field is a second thing that can drift, and these come straight off the stream and are printed
straight onto the screen. The browser's own view model, `WorldView`, keeps its own spellings because
it is a different thing with a different life
([`diff-view.md`](diff-view.md), *One field, two spellings*).

**Two fields the shapes sheet deliberately does not have twice.** `no_path` is on `Verdict` and
nowhere else — `Done.reason` says why the *generation* stopped and has no `no_path` among its seven.
And `mode`, the recording's date and the prompt hash are on `Receipt` and nowhere else —
`GenerationStarted` carries none of them. Two derivations of one line eventually disagree, which is
the same rule that moved the retraction badge onto the world ([`diff-view.md`](diff-view.md) B6).

**One field the shapes sheet deliberately does have twice, and why that is not the same mistake.**
`frontier` rides both growth events. It is not one fact derived two ways; it is one fact restated
after every change to it, so that whichever event arrives is enough on its own to redraw the set of
open claims. That is what lets a claim closed by its third refusal lose its rectangle immediately
rather than at the next accepted proposal, which might never come.

### What the browser asks for

```ts
export interface GenerateRequest {
  /**
   * The sentence the reader typed — and, with no key, the whole of how the server
   * knows which recording to play. See below. Required, and never empty.
   */
  readonly hypothesis: string;
  /** The Verify door's destination, in the reader's words. Absent is the Explore door. */
  readonly target?: string;
  /** The reader's own likelihood on the hypothesis. Absent when they chose "I don't know". */
  readonly user_belief?: Ranged;
  /** Only when reproducing a run we were given a seed for. See below. */
  readonly seed?: number;
}

// The route takes `versions` and `worlds` too, both upper-bounded on it, and the
// browser sends neither: the engine's own are what every map in this product is
// worked out with, and a screen that could ask for fewer would be a screen that
// could quietly make one answer cheaper and less certain than the one beside it.
// If a reason to send them ever appears it will be a control a reader can see,
// not a default they cannot.

/** One async generator over the stream. No component talks to the network. */
export async function* generate(request: GenerateRequest): AsyncGenerator<StreamEvent>;
```

**The browser does not invent a seed.** `seed` is optional and the browser sends one only when it is
reproducing a run it was handed a seed for — a shared address, a re-run from the transcript. With
none, `engine/ids.py` mints one and `generation_started` says which, so the run is reproducible from
the moment it starts and the number on screen is still the engine's. On a replay neither matters: the
recording's header carries the seed the recorded run used, and that one wins. A seed is not a claim
about the world, but it is still a number, and the rule that no number on screen was made up by the
browser is easier to keep than to keep checking.

**There is no field naming which recording to play, and there will not be.** With no key the server
matches the request's `hypothesis` against each recording's own `generation_started.hypothesis` —
exactly, after trimming surrounding spaces — and plays the one that matches; nothing matches, and it
says so in one plain sentence rather than guessing. So a launchpad card does the one thing any other
caller does: it sends its sentence. Nothing in the browser holds a table of file names, nothing
numbers the cards, and the live path and the replayed path send byte-identical requests — which is
what makes the reviewer's replay evidence about the live route rather than about a second one.

`Ranged` — a likelihood with its two range ends, at full precision — is
`frontend/src/world/types.ts`'s, the same shape a belief chip takes
([`tiles-ports-wires.md`](tiles-ports-wires.md)).

### The `growth` reducer

```ts
// frontend/src/stream/growth.ts
//
// One pure function from (state, event) to state. It draws no pixels, makes no
// requests, and does no arithmetic: every number it holds is a field it was
// handed.

/** One proposal the rules refused, as the strip beside the map lists it. */
export interface Refusal {
  /** Its place in the transcript, counting from 0. The engine's number. */
  readonly at: number;
  /** What the model wrote. Quoted, never drawn as a tile, never given an identifier. */
  readonly claimInWords: string;
  /** The validator's own sentences, one per rule broken, in the order it gave them. */
  readonly reasons: readonly string[];
}

/** One reserved rectangle at the growing edge of the map. Never a claim. */
export interface Skeleton {
  /** `skeleton:<claim id>`, or `skeleton:hypothesis` for the first one. A box's name. */
  readonly id: string;
  /** The one line it carries. The reader's own sentence, or the open claim's words. */
  readonly words: string;
  /** The open claim this one hangs off. Null for the first. */
  readonly after: PropositionId | null;
}

/** Where a generation is. Each is a different thing on screen, and none is a spinner. */
export type Phase = "waiting" | "growing" | "settled" | "stopped" | "failed" | "ended_early";

export interface Growth {
  readonly phase: Phase;
  /** The engine's name for this run. Null until `generation_started`. */
  readonly generationId: string | null;
  /**
   * The seed every likelihood in this run was worked out from, as its digits.
   * Null until the run has started, and never worked out here.
   */
  readonly seed: string | null;
  /** The sentence the reader typed, as the run's first event repeated it back. */
  readonly hypothesis: string;
  /** The destination the reader named, or null on the Explore door. */
  readonly target: string | null;
  /**
   * The map as far as it has been built, in the same view model the canvas already
   * draws. Every number slot the engine has not spoken about reads its absence, so
   * a half-built map is drawn by the components that already exist, unchanged.
   */
  readonly world: WorldView;
  /**
   * One per claim still open to expand. Rebuilt from `frontier` on **either** growth
   * event — accepted or refused — and emptied on `beliefs_propagated`, where the
   * frontier is empty by definition.
   */
  readonly skeletons: readonly Skeleton[];
  /** Every refusal, in the order they happened. Never trimmed, never summarised away. */
  readonly refusals: readonly Refusal[];
  /** The Verify door's answer, when a destination was named. */
  readonly verdict: Verdict | null;
  /** What the run cost. Null until the receipt arrives; never estimated meanwhile. */
  readonly receipt: Receipt | null;
  /** Why the generation stopped. Null until it does. */
  readonly done: Done | null;
  /** The one sentence a `failed` event left. Null otherwise. */
  readonly failure: string | null;
  /**
   * Arrows whose two ends are not both on the map yet, held rather than drawn.
   * Expected to stay empty — the engine sends a claim and its incoming arrows in
   * one event — and kept because a wire with one end nowhere is a picture of a
   * thing that is not true.
   */
  readonly waitingWires: readonly Link[];
  /** Event names this build does not know, and how many of each arrived. */
  readonly unknown: ReadonlyMap<string, number>;
}
```

**`beliefs_propagated` replaces the world wholesale.** Until it arrives, `world` is the browser's
drawing of the proposals it has watched go past — the claims, the arrows, and an absence in every
number slot. When the engine's own world arrives it *is* the world, and the drawing is thrown away
rather than merged into. A browser that kept its own version beside the engine's would be a second
source of truth, and two sources of truth disagree; this way there is nothing to disagree about.

**Who turns the engine's `World` into a `WorldView`, and why it is not a second anybody.** The event
carries the server's `World` — the shape in `frontend/src/api/schema.ts`, with the day-by-day series,
the retractions and the `Mapping`s the engine writes. The reducer's state holds a `WorldView`, the
browser's own hand-written view model, where every number slot is a `Known<T>` carrying either a
reading or the reason there is none. Between them sits **exactly one function, the one
`ApiWorldSource` already calls** on the answer from `POST /api/worlds`
([`diff-view.md`](diff-view.md), *The seam — `WorldSource`*). The reducer calls that same function on
`world` and nothing else: no second reader, no "just for the stream" variant, no partial conversion
that fills a few fields and leaves the rest. Two functions turning one shape into another would drift
inside a week and then a generated map and a fetched map would disagree about a number neither of
them computed — the exact failure the whole seam exists to prevent.

**Nothing in this reducer mints an identifier.** A claim's identifier is minted by
`backend/src/katalyst/engine/ids.py` and arrives on the event. The one name the browser makes is a
skeleton's, it names a rectangle rather than a claim, and it is thrown away the moment that claim
stops being open. That is the shape of PRD §10 anti-pattern 1 on this side of the wire: not a check
that nothing minted an identifier, but nowhere for one to be minted.

### What a generation looks like on screen

Nothing new is added to the page. The screen is the one
[`layout-and-zoom.md`](layout-and-zoom.md) and [`diff-view.md`](diff-view.md) already describe: the
canvas, and the **dock** beside it that holds the branch panel, the delta rail and the Inspector.
A generation puts three sections into that same dock, above the Inspector, in this order:

| Section | When it is there | What it holds |
|---|---|---|
| **The verdict card** | Only when the reader used the Verify door | The graded path, or the honest *no path reaches this* (B7) |
| **The refusal strip** | From the first refusal, for the rest of the run | One row per refused proposal, in the validator's own words (B5) |
| **The receipt strip** | From the `receipt` event onward | What the run cost, and the mode it ran in (B6) |

The delta rail and these three are never on screen together: a generation is running or a difference
is being read, never both. When the run is over, the refusals do not vanish — they move into the
Inspector's own **this generation** section with the whole transcript, which is where
[`inspector.md`](inspector.md) open question 2 is answered.

### Tokens and measurements this chapter reads

Every one of these is defined elsewhere and none is invented here.

| What | Where it comes from |
|---|---|
| A skeleton is **280 px** wide | `TILE_WIDTH` in `frontend/src/graph/geometry.ts` — the same width as every tile |
| A skeleton is **152 px** tall | `TILE_MIN_HEIGHT` in the same file: what `tileHeight` returns for a box with one line in it, which is the clamp's floor |
| The gap between two tiles in a column | `elk.spacing.nodeNode`, 48 px, in `frontend/src/graph/elkGraph.ts` |
| The gap between one column and the next | `elk.layered.spacing.nodeNodeBetweenLayers`, 120 px, same file |
| A wire arriving | `--duration-wave` (200 ms), staggered by `--duration-stagger` (60 ms) per column — the propagation wave already built as `.canvas[data-arriving="yes"]` in `frontend/src/graph/canvas.css` |
| Everything else that appears or goes | `--duration-fast`, 120 ms of opacity and nothing else |
| The skeleton's outline, its surface, its words | `--hairline`, `--surface`, `--text-muted`, `--font-interface`, `--text-sm` |
| Every number on the receipt strip | `--font-mono` with fixed-width digits, `--text-sm` |

All are in `frontend/src/styles/tokens.css` unless another file is named. This chapter defines no
token and changes none.

---

## Behaviour

Worked on the assignment's first example, the same run `spec/generation/proposals.md` works. A
reader types, into the Explore door, the sentence as a person actually types it:

> *The Strait of Hormuz is going to open next week.*

**That sentence is not a claim yet, and the difference matters on this screen.** It says nothing
about how anybody would settle it or by when, so nothing can score it (INV-1, the rule that a claim
nobody can check is not a claim). The first thing the engine does is turn it into one — *"The Strait
of Hormuz is open to unrestricted commercial transit for 14 consecutive days"*, with its criteria,
its judge and its date — and **that** is the claim **H** that lands on the map. So two strings are in
play from the first second and the chapter keeps them apart: the **typed sentence**, which is what
the skeleton carries and what the request sends, and the **claim**, which is what the tile carries
once it arrives. A reader watching their own words become a checkable claim is watching the most
auditable step in the whole pipeline, and collapsing the two would hide it.

The map that grows is the one the rest of this part works on — the cast is in
[`README.md`](README.md): **H** the strait open, **C** the war-risk premium falls, **B** Brent
settles below $68, **R** OPEC+ announces restraint, **M1** a Polymarket contract, **M2** an
energy-fund claim, **N1** talks resume. B7 uses the Verify door instead, with M1 as the destination.

**No number in this chapter is a measurement of a generation, because no generation has been run
yet.** The recordings are made in this stack's server half. Where a run's own number would go — a
token count, a cost, how long it took, a likelihood — this chapter says which field it comes from
and prints nothing.

### B1 — The first second: a rectangle, never a spinner

The reader presses **Build the map**. Three things happen before any model call has returned.

1. The request goes. `generate()` posts and starts reading.
2. `generation_started` comes back at once — the engine emits it before its first call, so it costs
   nothing to wait for — carrying the generation's identifier, the seed, the sentence as typed, and
   the destination if there was one.
3. **One skeleton tile is drawn**, in the leftmost column, carrying the reader's own sentence.

That third step is the first paint, and it is on screen in the time one round trip to our own server
takes. It carries no likelihood, because nothing has computed one; it carries the reader's words,
because the reader typed them.

**What that first rectangle is standing in for.** One call — the one that turns the typed sentence
into a checkable claim. It arrives as an ordinary `proposal_accepted` at `at: 0` with an **empty**
`links`, because the hypothesis has nothing before it, and the rectangle becomes H's tile. On the
Verify door a second such call follows at `at: 1` for the destination, and it too is an ordinary
claim with no arrows in. There is no separate event for either, and the browser needs none: from this
side both are the same fact the rest of the run keeps repeating — *the map got bigger*.

**NFR-7's wording is corrected here.** It reads *"streaming first-paint within 1s of the first
token"*, and this pipeline has no first token to be within a second of: the model boundary returns
**one whole proposal per call** (record 0006), and one proposal takes seconds to come back. A budget
measured from the first token would be a budget nothing could ever miss, because the thing it starts
timing from arrives at the same moment as the thing it times. So the budget is measured from the
request being accepted, and what has to be on screen within the second is a skeleton at its column —
which is the honest reading of what UX-8 promises anyway. The sentence `PRODUCT_REQUIREMENTS.md`
should carry instead is in this pull request's report; the requirement itself is not this chapter's
to edit.

**There is no spinner anywhere in this product** — not here, not on the launchpad, not on the
`insert` route, not while a lazily fetched midpoint chip is in flight. Waiting is always shown as the
shape of the thing being waited for: a reserved rectangle where a claim will go, an absence with its
reason where a number will go. Checklist line 2 is the standing check and
`test_there_is_no_spinner_anywhere` is the automated one.

### B2 — What a skeleton is, and what it never becomes

A skeleton tile is **a reserved rectangle**. Not a shimmer, not a pulse, not a grey bar sliding
across a card.

* **Its box is a tile's box.** 280 pixels wide (`TILE_WIDTH`), 152 tall (`TILE_MIN_HEIGHT`, the floor
  of the tile's own clamp), on the eight-pixel grid, with one border at `--hairline`. It is drawn on
  `--surface`, not on `--surface-raised`, so it reads as a space held open rather than as a card with
  nothing in it. **The border is dashed** — a solid hairline is what a claim's tile has, and a box
  the same weight as a tile beside a tile reads as a tile whose text has not loaded.
* **It carries two things and nothing else** *(amended 2026-09-21: this said "one line", and the code
  draws two)*. A mark reading **held open**, in the smallest type this product allows and no smaller,
  so that what the box is is readable rather than inferred — a reader meeting an empty dashed box for
  the first time has no way to know it is a promise rather than a fault. And one line: the first
  rectangle carries the reader's own sentence, every later one carries *one step on from "…"*,
  quoting the open claim it hangs off — so the reader can see not just that more is coming but *where
  from*. No chips, no dates, no clippings, no kind silhouette, no badge, and no number of any kind.
* **Its only movement is opacity, at most `--duration-fast`.** Nothing scales, pulses, sweeps or
  loops. An animated placeholder is a tool pretending to be busy; a held rectangle is a tool saying
  where the next thing goes.
* **It is not draggable**, like every other tile (INV-workbench.28).

**Where skeletons come from — three events, and nothing else.**

| Event | What it leaves on screen |
|---|---|
| `generation_started` | Exactly one skeleton, for the hypothesis, carrying the sentence as typed |
| `proposal_accepted` | One skeleton per claim named in `frontier`, each hanging off that claim. The set is **rebuilt**, so a claim that has left the frontier loses its rectangle in the same frame |
| `proposal_rejected` | The same, from the same field. A claim closed by its third refusal in a row is gone from `frontier` here, so its rectangle comes down on the refusal rather than waiting for an accepted proposal that may never come |
| `beliefs_propagated` | **Every skeleton goes.** The frontier is empty by definition once the map is finished, so there is nothing left for one to stand for |
| `failed` | **Every skeleton goes** *(added 2026-09-21)*. A rectangle is a promise that a claim is coming, and after a run breaks nothing is. The claims that were still open are in the working either way, so nothing is lost by taking the boxes down; what is lost by leaving them up is a reader waiting for a claim for ever |
| *the body ending with no terminator at all* | **Every skeleton goes** *(added 2026-09-21)*. The same rule, for the case that is not an event: see B3's *a stream that simply stops*, below |

So the skeletons on screen are the **frontier, drawn** — rebuilt from whichever growth event arrived
last, and emptied when the world lands. That is a fact the stream states, never a guess the browser
makes, and it is the whole reason both growth events carry `frontier` rather than only the accepted
one.

**Two things close a claim and neither makes an event of its own**: the model answering *Stop* on
that line, and its third refusal in a row. Both are recorded — a *Stop* leaves a transcript line, and
every refusal is already a `proposal_rejected` — and the browser is never *told* a claim closed,
because it can read it: the next growth event's `frontier` simply no longer names it. **So no
rectangle ever stands where nothing is coming**, and no event exists whose only job is to announce
that nothing happened.

It is worth saying what the browser therefore *cannot* say. The stream has no "a call has gone out"
event, so **one skeleton stands for one claim still open, not for one model call in flight.** Three
calls may be out against one open claim and there is still one rectangle. If a later stack wants the
count of calls on screen, the stream has to say it; the browser must not count for itself. (Open
question 1.)

**A skeleton is never a claim.** It has no identifier on the map — its name, `skeleton:<claim id>`,
names a rectangle. It never enters `WorldView.claims`, never reaches the network, never appears in
the outline view, cannot be selected, cannot open the Inspector, and has no belief chip to leave
empty. There is no number on it to be a number nobody computed, because there is no number on it at
all.

**On Hormuz, three rectangles and then two.** Walking the run in B3's table: after step 3 — the
proposal that brings **B**, caused by **C**, with the single arrow `C → B` — the frontier names H, C
and B, so three rectangles stand at the growing edge, reading *one step on from "The Strait of Hormuz
is open to unrestricted commercial transit for 14 consecutive days"*, *…from "Lloyd's war-risk
insurance premium for Gulf transits falls below 0.4%"* and *…from "Brent crude settles below $68 for
five sessions"*.

**Step 4 takes one of them down, and it is an accepted proposal that does it.** That step adds the
arrow `H → B` and no claim at all; H now causes three claims, which is its full width, so H closes
and step 4's `frontier` names only C and B. H's rectangle goes on that event — not because anything
announced it, but because the frontier stopped naming it. **N1 never had one:** it arrived at step 2
as a `not_tradeable` ending, and an ending has nothing downstream of it, so it never joined the
frontier in the first place. The map is honest that the chain stops there, and it is honest about it
by drawing nothing rather than by drawing something that then disappears.

### B3 — The whole run, as the canvas sees it

The same generation `spec/generation/proposals.md` B4 writes out call by call, read from this side of
the wire. `at` is the transcript position; the last column is what stands at the growing edge **after**
that event has been folded in.

| `at` | Event | What lands on the canvas | Rectangles standing |
|---|---|---|---|
| 0 | `proposal_accepted` | **H** — *"The Strait of Hormuz is open to unrestricted commercial transit for 14 consecutive days"*. `links` is empty; the first rectangle becomes this tile | H |
| 1 | `proposal_accepted` | **C** and the wire `H → C` | H · C |
| 2 | `proposal_accepted` | **N1** and the wire `H → N1`. An ending, so it never joins the frontier and never gets a rectangle | H · C |
| 3 | `proposal_accepted` | **B** and the wire `C → B` — one claim, one incoming arrow | H · C · B |
| 4 | `proposal_accepted` | **No claim at all**: `proposition` is null and `links` holds the one new wire `H → B`. H reaches its full width here and closes | C · B |
| 5 | `proposal_accepted` | **M1** and the wire `B → M1`. A tradeable ending | C · B |
| 6 | `proposal_rejected` | Nothing on the canvas; one row on the refusal strip (B5). The frontier is unchanged — this is B's first refusal, not its third | C · B |
| 7 | `proposal_accepted` | **M2** and the wire `B → M2`. A tradeable ending | C · B |
| — | nothing on the wire | C answers *Stop*; a transcript line and no event | B |
| — | nothing on the wire | B answers *Stop*; the last open claim closes | — |
| — | `beliefs_propagated` | Every chip fills, at once (B4). Every rectangle goes | — |
| — | `receipt` · `done` | The receipt strip; the stop reason, `reached_terminal`, because the last open claim answered *Stop* (B7). `claims=6`, `links=6`, `rejected=1` — count them off the rows above | — |

Two things worth reading off that table. **The transcript's numbering has gaps** — a client sees 7
and then the closing events, and the two missing positions are the two stops, which make no event
because nothing about the map changed. And **no event ever says a claim closed**: the rectangle for H
comes down at step 4 because step 4's `frontier` stopped naming it, and the last two come down on
`beliefs_propagated`, where the frontier is empty by definition.

The map that grows is **not the shipped fixture and does not pretend to be**: six claims where the
fixture has seven, and no feedback arrow `B → R`, because a proposal has no `reflexive` field and
nothing can propose one. Every chapter in this part works the fixture; this one works the run, and
the difference is a fact about generation rather than a discrepancy to smooth over.

**Where a claim lands is decided by its causes, not by when it arrived.** The layout is the layered
one [`layout-and-zoom.md`](layout-and-zoom.md) owns: a claim sits in a column to the right of
everything that causes it. N1 arrives third and lands in column 1; B arrives fourth and lands in
column 2. The picture reads causality, and arrival order leaves no trace in it.

**Nothing that is already on screen moves.** This is not new machinery and growth adds none. The
rule already lives in `readPositions` in `frontend/src/graph/elkGraph.ts`, in those words: *a tile
that had a position keeps that position, to the pixel, and only a tile that had none takes a new
one.* Growth is the case that rule was written for. Every claim the engine sends is strictly
downstream of the map so far — a `ClaimProposal` brings one claim and the one arrow into it, so that
arrow's source is always a claim that already exists — which is exactly the precondition
INV-workbench.22 names. A late arrival finds a gap; nothing above it, beside it or before it shifts.

**The layout answers later, and a box waits for its place rather than borrowing one** *(added
2026-09-21)*. The layout runs on a background thread, so between a claim arriving on the stream and
that claim being drawn there is always a gap — a frame on this machine, most of a second on a tired
one. What the map does in that gap is the whole of `frontend/src/graph/onTheGlass.ts`, and it is one
rule: **a box is drawn where the layout put it, and a reserved rectangle stands until the claim it
was holding a place for is drawn.** Not until the event carrying that claim arrived — those are two
different moments, and everything between them would otherwise be a map with a claim on its way and
no rectangle anywhere, which is a growing map that has stopped saying where it is going. It is not a
corner case: a generated map's frontier is usually one claim wide, so it turns over completely every
few proposals, and each turnover is one of these moments.

The rectangle goes the instant the map is whole again, so this can never become a way of leaving one
up: a rectangle whose claim closed with nothing coming after it — a third refusal, a broken run, the
likelihoods landing — goes at once, because then nothing on the map is waiting for a place.

**The one box the map places itself is a rectangle, and it is the first.** Before the layout has
answered even once the origin is nobody's place: there is nothing to be drawn on top of, and a
generation's first paint may not be an empty stage (B1). So the map puts the rectangle held open for
the reader's own sentence there itself. It was *the first box* rather than *the first rectangle*
until 2026-09-21, and on a machine where the first answer lost its race to the first proposal that
box was the claim. Two promises broke at once. The growing edge went quiet, which is what continuous
integration read. And the claim was drawn at the origin, which is not where the layout puts the first
box of a map — the layout leaves a margin of its own around what it lays out, so the tile then moved
by that margin, and *nothing already drawn moves* is the loudest promise this part makes. How far it
moved was read off the page by the end-to-end test itself, which is what caught it: it holds the
first tile's place and compares it with itself at the end of the run.

**A wire draws only after both of its ends exist.** In practice the engine makes this true by
construction, twice over: a `ClaimProposal` brings the claim and the arrow into it in one event, and
an arrows-only proposal names two claims that are already on the map. The reducer does not rely on
either. An arrow whose two ends are not both on the map goes into `waitingWires` and is drawn the
moment the second end arrives. The list is expected to stay empty for ever, and the test that proves
the rule **builds** a stream that fills it rather than assuming one cannot exist. A wire with one end
nowhere is a picture of something that is not true, and half a wire is worse than no wire.

**The wave is the one already budgeted.** Each wire arrives with the propagation wave
[`color-motion-type.md`](color-motion-type.md) spends: about 200 milliseconds (`--duration-wave`),
its column 60 milliseconds (`--duration-stagger`) after the column before. It is already built —
`.canvas[data-arriving="yes"]` in `frontend/src/graph/canvas.css`, with a `wave-<n>` class per
column. Growth switches it on per arrival instead of once per map, and adds no fourth animation to
the budget of three.

**The honest wart, and the one event that could cause it.** An arrows-only proposal — step 4 above —
joins two tiles that are already placed, and because the pin is absolute the wire is drawn where they
sit rather than re-laying out the map to suit it. On this run that costs nothing: H is in column 0
and B in column 2, so `H → B` points rightwards like every other wire and no column would have moved
anyway. But an arrows-only proposal whose source happens to sit *right* of its target would be drawn
pointing backwards, which is honest about where the tiles are and misleading about the argument. The
trade is the one [`layout-and-zoom.md`](layout-and-zoom.md) anti-pattern 7 makes: the map should be
still while you read it, and losing your place is the worse failure. Whether the map re-lays out once
when the run finishes is Open question 2, **answered below**.

**A stream that simply stops** *(added 2026-09-21)*. Every stream a reader stayed for ends in exactly
one `done` or one `failed`. A body that ends with neither is a dropped connection —
[`spec/generation/streaming.md`](../generation/streaming.md): *"a dropped stream is a finished
generation with no terminator. The browser says the stream ended early and offers to run it again."*
A server restarted, a proxy gave up on a connection it thought was idle, a laptop slept during a
ten-minute run: none of those is a fault anybody on this side can name, and none is a `failed` event,
because none of them is the run saying anything at all.

What the browser does is three things and no more. **The rectangles come down**, which is the other
half of *no rectangle ever stands where nothing is coming* — after this, nothing is, and a map left
growing for ever is the one screen in this product that lies without saying a word: it is drawn
exactly as a map about to change and it is never going to change again. **The map is kept**, every
claim and arrow that arrived, with nothing invented to fill the gap and nothing greyed. And **one
plain sentence**, in the same line under the map that says why any other run ended, with **the offer
to run the same sentence again beside it** — an offer that says on its face what pressing it costs:
*run it again — this asks the model again, and spends again* on a copy with a key, and *play it again
— this plays the recording again, and spends nothing* on one without. A control that quietly spends
money the second time it is pressed is the one control in this product that must say so before it is
pressed.

It is not folded from an event, because there is no event: the reader of the stream is the only thing
that can notice a body ending, and it hands the reducer that fact by name (`theStreamEnded`) rather
than by inventing a ninth event the server never sent. The working as far as it got is still readable
at `GET /api/generate/{generation_id}/transcript`, which is the whole reason this state keeps the map
rather than clearing it.

### B4 — Chips resolve last, and they resolve once

**While the map grows, every model chip reads *no engine yet*.** The claims that arrive carry their
stated `prior`, and the tile never draws a prior — a second number beside the model's would be a
fourth voice ([`tiles-ports-wires.md`](tiles-ports-wires.md)). So a growing map is the same picture
this part already ships: real claims, real arrows, real provenance marks, and an absence with its
reason in every likelihood slot.

**When `beliefs_propagated` arrives, they all fill at once.** One event, one world, every number.
The chip's own sentence switches from the *stated* pair to record 0014's *computed* pair with no
change to the component, because `WorldView.versions` arrives on the same world and that is the one
field the chip reads to choose (Kent, K3; `tiles-ports-wires.md`, *What the model chip says about its
own range*).

**Never per tile, and never twice.** A likelihood that changed four times as its causes arrived would
be four numbers nobody computed: the first three would each be the answer to a question about a map
that no longer exists. There is exactly one propagation per generation and exactly one
`beliefs_propagated` event, so a chip goes from its absence to its number once and stays.

**The reveal is not the number-roll.** The third budgeted animation rolls a likelihood from an old
figure to a new one, and here there is no old figure — there is an absence. So the chips appear with
an opacity change at `--duration-fast` and nothing rolls. The number-roll still has nothing to roll
until an edit moves a number, which is this stack's second pull request.

### B5 — Every refusal is on screen, in the validator's own words

**A rejected proposal is an event, not an error.** Nothing is retried quietly out of sight and
nothing is swallowed. The engine may try again — up to three fresh proposals for one open claim,
none of them told why the last was refused (Kent, G4; record 0003's dated amendment) — and **every
one of those attempts that was refused is on screen.**

The refusal strip is one row per refusal, in the order they happened, newest last. A row carries the
model's own words on its first line, ellipsized at a word boundary, and beneath them the validator's
own sentence — **one per rule broken**, because a proposal that broke three rules and shows one is a
refusal the reader has half seen. The rows are short and there are few of them; a run with a strip
long enough to need trimming has a prompt problem, not a layout problem.

Two rules the strip obeys, both inherited rather than invented. **The sentence is the validator's, as
it wrote it** — `spec/graph/validity.md` owns that copy, and its rules for it are that a message
names the claim by its words, never by its identifier, and says what is missing rather than that
something failed. The browser never composes a sentence about a refusal. And **a refused claim is
never drawn as a tile and never given an identifier** — `claim_in_words` is quoted and nothing else
is done with it, which is the same rule as B2's.

**On Hormuz, at step 6.** Every recording must hold at least one refusal (record 0012), and the map's
own shape supplies it. Expanding B, the model proposes an arrow rather than a claim — `B → H`,
*cheaper crude reduces the incentive to close the strait*. Read on its own it is a reasonable
sentence; added to the map it closes `H → B → H`, because step 4 has already drawn `H → B`. The rules
refuse it with exactly one violation, and its message is the validator's, word for word:

```
proposal 6   refused
   "cheaper crude reduces the incentive to close the strait"
   These claims form a loop with no delay in it: "The Strait of Hormuz is open to
   unrestricted commercial transit for 14 consecutive days" → "Brent crude settles
   below $68 for five sessions" → "The Strait of Hormuz is open to unrestricted
   commercial transit for 14 consecutive days". Mark the arrow where a market feeds
   back on the world as reflexive and give it a delay, or remove one arrow.
```

Nothing moves on the canvas when that row appears. B is on its **first** refusal, not its third, so
step 6's `frontier` still names C and B and both rectangles stay exactly where they were. Step 7 is
the same call asked again with a byte-identical prompt — the next call is never told what was wrong
— and it comes back with M2.

That row is half the product. It is the moment a reader can see that our own code, not the model,
decides what the map is allowed to contain — and it says the one thing that would have made the
arrow legal, which is the difference between a rejection and an insult.

`proposal 6` is `at`, the engine's own position in the transcript, printed so the row can be found
again in the Inspector. Selecting the row opens the Inspector's **this generation** section at that
line.

### B6 — The receipt strip, and where a transcript is read

**This answers [`inspector.md`](inspector.md) open question 2.**

When `receipt` arrives, the strip beneath the refusals fills in. It prints what the engine sent and
adds nothing up:

```
THIS GENERATION
  model            <Receipt.model>
  calls            <Receipt.calls>
  tokens in        <Receipt.input_tokens>
  tokens out       <Receipt.output_tokens>
  read from cache  <Receipt.cache_read_tokens>
  web searches     <Receipt.searches>
  cost             <Receipt.dollars>, in the two places money has
  took             <Receipt.seconds> — "the replay took", on a replay
  how hard the
    model tried    <Receipt.effort>
  mode             live
```

**Money has two places** *(coordinator, 2026-09-21)*. It printed up to four — `$0.6132` — which is
the same fake precision checklist line 4 exists to stop, in the place a reader is most likely to
compare two runs: the fourth place is a rounding of a price table, and four places read as a
measurement. **And a guard word exactly when it is true** (K2): a run that spent nothing prints
`$0.00`, which is a computed zero and reads as one, and a run that spent something and less than a
cent prints `<$0.01`, because `$0.00` there would say a run was free when it was not. One function,
used by the generation's strip and the insert's alike, so the two cannot come to write a cost two
ways.

**And `took` says whose clock it is.** On a live run it is how long the run took. On a replay it is
how long the **replay** took — a few seconds of paced playback beside a map that took eleven minutes
to make — so the row reads *the replay took*. A reader comparing the two figures without that word
would conclude this product is two hundred times faster than it is. The recorded run's own duration
is not on the wire; when it is, this row can carry it and say which is which.

**Amended 2026-09-21 — there are ten readings, and the tenth is how hard the model tried.** A plain
word: `default` when nothing was asked for and the service's own applied, otherwise `low`, `medium`,
`high`, `xhigh` or `max`. One setting with two pinned defaults behind it — **a recording is made rich
and a live run is made fast** (Kent, G13) — so two maps of the same sentence at the same seed can
differ for a reason that has nothing to do with the sentence, and a reader comparing one with the
other is entitled to see which they are looking at. It is the word the service takes rather than a
number, because a number would be this browser translating one thing into another and printing the
translation.

Four things about it.

* **Every one of those is a field.** The browser does not add the two token counts together, does not
  work out a cost from a token count and a price, and does not time anything itself. A price table
  lives in exactly one module on the server (`engine/pricing.py`) with the day it was read beside it,
  and the dollars on this strip came from there. **Searches are a row of their own** because they are
  billed apart from tokens: without that row, `dollars` is a number a reader could check against the
  token counts and find wrong.
* **Checklist line 4 is about likelihoods.** *"No number shows more than two significant figures, and
  none is missing its range"* is the rule that stops a fake-precise `.347` reaching the screen
  (NFR-1). A token count, a call count, a duration and a dollar figure are counts and measurements:
  they are printed whole, in `--font-mono` with fixed-width digits, and they have no range because
  nothing sampled them. The same reading already lets a lag chip say *14 days* and a tile be 280
  pixels wide.
* **In replay the mode reads `replay`**, the recording's date sits beside it, and `cost` reads what
  the rebuilt receipt carries, which is zero. That zero is a computed zero — the recording was played,
  nothing was called, so nothing was spent — not an empty slot, and it is printed rather than hidden.
* **Before the receipt arrives the strip is not there.** No running estimate, no ticking cost, no
  progress bar. A cost nobody has totalled is a number nobody computed.

**The working lives in the Inspector, and it is the panel's third subject.** Until now the Inspector
opened on a claim or an arrow. It now also opens on the generation itself, and that section holds
*(amended 2026-09-21)*: the seed the run drew with and the prompt's fingerprint, whole, each with the
sentence saying what it is for; the whole transcript, one line per proposal in order, accepted or
refused, each accepted one naming the claim it became and each refused one carrying every sentence
the validator wrote; a line per event name this build did not know, with how many of each arrived;
and one sentence pointing at the strip for what the run cost. **It carries no copy of the receipt's
ten readings.** It is drawn from the moment there is a generation, with whatever has arrived in it
and an em dash in each slot that has not — a section that appeared only once everything had landed
would be a panel that is empty exactly while a reader is most likely to open it. The transcript is
read from `GET /api/generate/{generation_id}/transcript`, which the server holds
in memory for the life of the process — there is no storage in this stack, and a transcript outliving
the process is stack 05's question (FR-31).

**An event this build does not know is ignored, and said out loud.** The reader folds it in as a name
and a count and changes nothing else: it does not throw, because a browser that crashes on a new
event makes the server unable to add one; and it does not disappear, because a dropped event makes a
missing feature look like a working one. The line is the only place it shows, and one line in the
transcript is the right size for *"this build saw two events it has no name for"*.

Every number on the strip is therefore one click from its why in the strictest sense
[`inspector.md`](inspector.md) INV-workbench.51 asks for: the click opens the panel at the transcript
that produced the count.

### B7 — The Verify door: a graded path, or an honest *no path reaches this*

The Verify door is **one extra field on the same input bar**, not a second screen: the reader names
where they think it ends. On Hormuz: *the Polymarket contract "Brent below $70 on 2026-10-31"*. The
generation runs exactly as before, and one more event arrives.

**`kind: "reached"` — the graded path.** A card at the top of the dock, naming the steps of
`Verdict.path` in order in the claims' own words, with the multiplied-out likelihood of those steps
beside it (INV-8), the number taken from `Verdict.product` and multiplied by nobody here. Under it,
word for word, the same wart the Inspector's path bar prints, because there is one wording and one
place it is written ([`inspector.md`](inspector.md) B5): the factors are each read on their own
resolve-by day, so the product multiplies numbers read on different days, and **it is not a joint
probability**. The card and the path bar share the sentence, not the component *(corrected
2026-09-21)*: one exported constant, `PATH_PRODUCT_WART`, which the card prints and the bar prints.
They are two different components — the bar is a claim's own route with its chips, the card is the
Verify door's answer with its steps and its control — and saying they are one would have somebody
look for a shared component that does not exist. What must not drift is the wording, and a constant
is what stops wording drifting.

**How long the route is is printed, never counted** *(added 2026-09-21)*. `Verdict.why` is the
engine's own sentence and it already says it — *"…reaches it in 2 steps"*. The card used to say it
again underneath, worked out as one fewer than the claims on `Verdict.path`: two derivations of one
fact, agreeing exactly until the day the engine counts a step differently, and then the card
contradicts itself in two adjacent paragraphs with nothing on screen to say which is right.

**`kind: "no_path"` — a finding, drawn as a finding.** This is not a failure state and it does not
look like one. The card carries `Verdict.why` — the engine's own plain sentence — and names
`Verdict.nearest`, the closest claim the map did reach, with one control that selects that claim on
the map so the reader can see where the path stopped.

**No bridge is drawn. Ever.** No dotted arrow from the nearest claim to the destination, no ghost
tile for the destination, no "probably connects" wording. A path that does not exist is the most
valuable thing this door can tell you, and drawing a faint one would be the traceability veto with a
dashed stroke.

**`no_path` is on the verdict and nowhere else.** `Done.reason` has seven values and none of them is
`no_path`; it says why the *generation* stopped, which is a different question with a different
answer. A run can reach its claim cap and still have found a path, and a run can end cleanly and
have found none.

**And when the generation itself stops, the strip says why, in the engine's words for it.** One
reason arrives, never a list, and it names **what closed the last claim that was still open** — with
the spending limit and the no-ending case overriding everything above them. `spec/generation/proposals.md`
B4 owns that rule; this table owns the words.

| `Done.reason` | What the strip says |
|---|---|
| `reached_terminal` | The last line closed properly: it reached something you could trade, or a stated reason there is nothing to trade, or the model had nothing more to add. |
| `depth_cap` | The last line still open ran as far from your sentence as one generation goes, and stopped there. |
| `width_cap` | The last line still open was closed because that claim already has every effect one generation draws from it. |
| `claim_cap` | The last line still open was closed because the map was full. |
| `spend_cap` | The run reached its spending limit and stopped where it was. The receipt says what it spent. |
| `refusal_cap` | One line was abandoned: three proposals in a row for it were refused. |
| `no_terminal` | One last call asked every open claim where it ends, and none of them ends in something you could trade. |

Two things those seven sentences do on purpose. **No sentence blames the model for our own rules.**
Three refusals in a row is our validator turning proposals down and our cap deciding that three is
enough; a sentence reading *"the model stopped answering"* would be a screen accusing a third party
of a decision we took, which is the reverse of the receipt this product writes everywhere else. And
**each one names the cap and not its value**, because the stream carries no value. A limit the browser
printed from memory would be a number nobody on this screen computed, and a limit that had quietly
changed on the server would then be a number that was wrong. The values and their justifications are
`spec/generation/proposals.md`'s.

**`failed` is the eighth thing that can happen, and it is not one of the seven.** The map that had
been built stays exactly where it is — nothing is cleared, nothing is greyed — and one line appears
under it carrying `Failed.message`, which is one plain sentence and never a stack trace. A reader
whose run broke after twenty claims keeps the twenty claims.

### B8 — The input bar, and **Add a claim**

**Three fields, one button, and no more** (FR-1, FR-2).

1. **The sentence.** One line, the hypothesis, in the reader's own words.
2. **Where it ends**, optional. The Verify door. One field, hinted with what it is for.
3. **Your own likelihood.** A range with an explicit **I don't know** state (FR-2). Three handles on
   one track — the number and the two ends of its range — spelled beside the track in exactly the
   one-line form the chip uses, `.55 (.40–.70)`, under the same two-significant-figure rule and the
   same certainty guard ([`keyboard-and-access.md`](keyboard-and-access.md) B6), so the control
   cannot post a `1.0`.

**The button is `Build the map`**, word for word, and it is the same button on both doors. Not
*Generate*, which is the pipeline's word rather than the reader's, and not *Explore* or *Verify*,
which are the two doors and are already named by whether the second field has anything in it — a
button whose label changed as the reader typed would be a control that moved under them. It is
written once, beside the six operation buttons, in the Interface words table in
[`../vocabulary.md`](../vocabulary.md); this chapter copies it and never paraphrases it.

**"I don't know" is a state of the control, not a value.** It is where the control starts, and while
it holds, the request carries **no** `user_belief` at all — not a `.5`, not a wide band, not a null
that something downstream treats as a half. A reader who has not said what they think has not said
what they think, and a tool that fills that in for them has invented the one number it had no
business inventing.

**The reader's number is stored as a `user` belief on the hypothesis and is never overwritten.** The
model's belief and the reader's are two slots that are never merged (INV-11), and a generation
writes the model's.

**With no model key, the bar is visibly disabled and says why** — record 0012's sentence, the same
one the launchpad carries, word for word. Never silently inert: a field that takes typing and then
does nothing reads as a broken tool, where a field that says why reads as an unfinished one, and only
one of those is true.

**Add a claim** — *"…but this also happens"* — is the one intervention that calls the model (PRD §10
anti-pattern 2's single exception: re-prompt only for an insert, and only over the affected subtree).
It posts to `POST /api/generate/insert` — `{base_id, branch, claim_in_words}` — and gets back **one**
intervention: a claim and its arrows, already drafted and already validated by the same rules
everything else passes. The browser appends the intervention to the branch like any other edit, and
the branch panel shows it immediately ([`diff-view.md`](diff-view.md) B7).

**The branch is one of the three fields and it is sent** *(2026-09-21)*: the claim is drafted and
checked against the map the reader is actually looking at, which is the base map with the branch
folded onto it. Leaving it out asks the rules about a map nobody has in front of them, and a claim
that contradicts an edit made two minutes ago comes back accepted and then breaks the branch it is
added to.

**And there is no `position`** *(Kent, 2026-09-21; this paragraph used to argue for the name)*. **A
drafted edit goes at the end of the branch**, which is the only place this product ever puts one — a
branch is append-only everywhere else in it. The field was read by nothing, and while it was there a
reader who sent something other than the end got a 200 for an edit the world route then refused: a
field that changes the answer's shape and not its content is worse than no field, because it makes a
promise the next route breaks.

It is not a generation — no stream and no reserved rectangle — but **it is several model calls, so it
carries a receipt of its own**: the route answers a `DraftedInsert`, the edit and its `Receipt`
together, and the cost is drawn by the same strip a generation's receipt is drawn by, with the same
ten readings.

**It carries its working too, and the working is in the answer because there is nowhere else it
could be** *(2026-09-21)*. An insert is one request and one answer: nothing about it is remembered on
the server, so there is no identifier to ask by and no route to ask at — and filing it in the
generation store instead made every insert unfindable, because nobody was ever told the identifier,
while eight of them evicted the map they were being added to. So `DraftedInsert` carries
`working`: one line per call, in the same shape a generation's transcript lines take, drawn by the
**same component** the generation's working is drawn by. A reader who has learned to read one has
learned to read the other, and the two cannot come to disagree about what a refusal looks like. Two
things a line says that a generation's rarely does are drawn when they are there: an address the
model cited that the search never returned, named rather than silently dropped — otherwise an arrow
that says it *argued* looks like one that says it *documented* — and a reference class offered with
nothing behind it, said as a class **with no number beside it**, because a figure with no page behind
it reads as measured however it is marked. **That closes Open question 3** (settled 2026-09-20 in
[`spec/generation/streaming.md`](../generation/streaming.md), drawn 2026-09-21 here). What made it
answerable was learning that an insert is *several* calls rather than one — the starting-claim shape
drafts the reader's sentence, then the ordinary walk proposes its arrows, one call each. A single
cheap call might fairly have been folded into the map's own transcript; several are not, and the
person pressing the button is the person who should see the bill. The two alternatives lost on the
same ground: folding it into the generation's transcript files this spend under a different run, and
a running total in the browser is a number added up by something other than the engine, which also
vanishes on a page reload.

The other five operations — **Suppose this is true**, **This happened**, **Change this push**,
**Split this claim**, **My own number** — call no model at all and never have. They are arithmetic in
the engine's pure core, which is why a reader with no key still gets the whole multiverse at full
fidelity.

### B9 — With no key: the replay badge, and the four cards

**The launchpad's four cards all open a map**, and the three that today read *not yet live* stop
doing so. With a key they run live. With no key they run from recordings, through the same route, the
same eight events, the same canvas, at a fixed pacing that is cosmetic and never changes content or
order (record 0012).

**The launchpad says so, word for word:**

> No model key configured — these four run from recordings made on \<date\>.

The sentence sits under the cards and again beneath the free-text field, which is visibly
disabled with it.

**A card is only ever something a reader can take up** *(2026-09-21)*. It runs live or it runs from
a recording — and a sentence this copy can do neither with gets **no card at all**. With one
recording committed, the four cards were one door and three headstones taking the whole of the
right-hand column, which is what a reviewer with thirty minutes met first; and *not yet live* on a
row that cannot be pressed is a control a reader counted and cannot use. What is left of those
sentences is the line above, which already named them — *…the other three have nothing recorded
yet*. With nothing at all to offer there is no list either, because an empty list under a heading
reading *or watch one build itself* is worse than a sentence saying so, and that sentence points at
the map that is already drawn, which needs neither a key nor a recording.

**Before the readiness answer arrives, every sentence says that is what is being waited for.**
Nothing is known about a key or a recording until the server has spoken, and a screen reading *no
model key* in the meantime is asserting something nobody told it. It is not a spinner: the sentence
is on screen and the line under it names the two things being waited on.

**With a key, all four are live and all four are offered.** The rule is one rule — *a card for
everything this copy can do* — and with a key that is everything.

**A recording that would not play is named, quietly, under the cards** *(2026-09-21)*. The readiness
answer lists only the recordings that would actually play, and carries beside them one plain sentence
per file in the folder this engine could not read. Both halves matter. **A bad file never hides the
good ones** — the cards with recordings still run, because a recording is a committed file that
outlives the code that wrote it and meeting an old one is ordinary rather than exceptional. And **it
never hides itself either**: a reviewer who put a file in the recordings folder and then counts three
cards where they expected four is owed the reason rather than left to wonder whether they put it in
the wrong place. The sentence is the server's own, printed word for word, quieter than the line
above it that says what this copy can play — it is a fact about one file rather than about any map,
so it sits under the cards and touches none of them.

**Where the date comes from.** Not from the stream: S3 put the recording's date on `Receipt`, and the
receipt arrives at the *end* of a run, long after the launchpad needs to print this sentence. So the
readiness answer carries it. `GET /api/readyz` says `status` and `model_key_present` today, and gains
one field — settled in the stream pull request, which owns the route:

```ts
/** One example this build can play without a key. */
interface RecordingSummary {
  /** Which stored example it is, matching the launchpad's card. */
  readonly example: string;
  /** The day it was made, as the map writes a day: `2026-09-18`. */
  readonly recording_date: string;
}

interface Readiness {
  readonly status: "ready" | "not_ready";
  readonly model_key_present: boolean;
  /** Only the ones that would actually play. Empty when nothing has been recorded. */
  readonly replayable: readonly RecordingSummary[];
  /** One plain sentence per file in the folder this engine could not read. */
  readonly unreadable: readonly string[];
}
```

**`recording_date`, and never `recorded_on`.** It is the same day the recording's header carries and
the same day the `receipt` event carries, so it keeps one name in all three places: one fact, one
word, nothing to translate between.

The browser reads the day from that field and never from a file name, a build date or its own clock.
When the four were not all recorded on one day — G6 records them together once the prompt is frozen,
so they normally are — the shared sentence prints the **oldest** day in the set and each card carries
its own beneath, so the sentence is never more current than the oldest thing it describes.

**The launchpad reads `replayable` and `model_key_present`, and ignores `status`.** A program with no
key but four recordings can do everything a reviewer came to see, and a card greyed out because the
whole server called itself `not_ready` would be the most misleading screen in the product.

**A replay says it is a replay, twice, from two sources.** The badge is in the bar for the whole
session, from the moment the run starts, set from `model_key_present` — the browser knows before the
stream does. When `receipt` arrives it carries `mode` and the recording's date, and it **names the
day**, because the day is a fact only the receipt has. Two derivations again, and this is the one
place both are needed — the badge has to be there before the receipt exists — so the rule is written
down rather than left to luck.

**When the two disagree, neither wins: the disagreement is the finding** *(corrected 2026-09-21;
this said the badge takes the receipt's word, and the code has never done that — rightly)*. A
session with no key that gets a receipt saying `live` is a copy that has done something nobody can
account for, and the honest screen shows both readings and says they differ, in the line under the
map where every other sentence about where this map came from lives. The badge stays, marked as
disagreed, because it is still true that this session had no key; the receipt stays, because it is
still true that the run reported itself live. Resolving it in favour of either would be the screen
deciding which of two things it was told to believe, which is the one decision it must not make on a
reader's behalf. The reasoning lives beside the code that does it, in `ReplayBadge.tsx`.

**One recorded intervention per recording.** Each file carries the scripted *"…but Iran is struck
the next day"* its card offers, so **Add a claim** works once on a replayed map — the route matches
the sentence against the recording's own, exactly after trimming surrounding spaces, the same rule
that chose which recording to play. There is no fuzzy matching and there will not be: a similarity
score doing the model's job badly is a piece of state nobody could trace to an input, a rule or a
source. Any other insert is declined in plain words — *"drafting a new claim needs a model key."* —
and the control says so rather than disappearing.

### B10 — The same growth, under reduced motion

Turn on reduced motion and run it again. **The ordering survives and the tweening goes**, which is
the rule [`color-motion-type.md`](color-motion-type.md) owns and `tokens.css` already implements:
`--duration-wave` goes to `0ms` and `--duration-stagger` stays at 60 milliseconds.

So: the skeleton still appears first. Each claim still appears when it arrives. Each column of wires
still arrives 60 milliseconds after the column before it, so the eye still follows the chain the way
the argument runs — it just arrives instantly instead of drawing. The chips still fill in exactly
once, as a swap rather than a fade. Nothing is lost, because the only thing removed was the
in-between frames.

**The ordering is the causality.** It is not the decoration, and a reduced-motion setting that
revealed the whole map at once would have thrown away the meaning and kept the pretty part
([`keyboard-and-access.md`](keyboard-and-access.md) B5).

And the outline view grows too. Each accepted claim gets its item at the moment it arrives, in the
same causal order — a reader who never sees the canvas hears the map being built, not a silence
followed by a finished list.

---

## INVARIANTS

Each is *for all X, statement P holds*, and each names what checks it: a **component test** under
`frontend/src/**/__tests__/`, the end-to-end browser test `frontend/e2e/generate.spec.ts`, or a
numbered line of the **visual review checklist** in [`README.md`](README.md) — a checklist line is a
checkable thing; it is checked by a person. Frontend test names are `test_snake_case`. Short file
names below: **growth** is `frontend/src/stream/__tests__/growth.test.ts`, **reader**
`frontend/src/stream/__tests__/generate.test.ts`, **noSpinner**
`frontend/src/stream/__tests__/noSpinner.test.ts`, **strip**
`frontend/src/stream/__tests__/strips.test.tsx`.

Local numbers in this part are `INV-workbench.<n>`. This chapter holds **60 – 79**;
[`tiles-ports-wires.md`](tiles-ports-wires.md) holds 1 – 12,
[`color-motion-type.md`](color-motion-type.md) 13 – 19, [`layout-and-zoom.md`](layout-and-zoom.md)
20 – 30, [`keyboard-and-access.md`](keyboard-and-access.md) 31 – 39,
[`diff-view.md`](diff-view.md) 40 – 49 and [`inspector.md`](inspector.md) 50 – 59.

**INV-workbench.60 — there is no spinner anywhere.** For every module under `frontend/src/` and every
state of the app, no element is rendered whose only content is an indeterminate progress indicator:
no `role="progressbar"` without a value, no spinning or pulsing element, no stylesheet rule that
rotates or sweeps anything. Waiting is rendered as the shape of the thing waited for. *Test:*
noSpinner › `test_there_is_no_spinner_anywhere` — a walk over every component and every stylesheet,
the same technique `colourLaw.test.ts` uses. **Also: visual review checklist line 2.**

**INV-workbench.61 — something is on screen before the first proposal returns.** For every
generation, a skeleton tile is rendered on the `generation_started` event, before any
`proposal_accepted` has arrived, and it carries the hypothesis as the reader typed it. *Tests:*
growth › `test_a_skeleton_tile_appears_before_the_first_claim`; `frontend/e2e/generate.spec.ts`.
**Also: visual review checklist line 13.**

**INV-workbench.62 — a skeleton is a box, never a claim.** For every skeleton rendered: it carries no
digit anywhere, has no belief chip, is absent from `WorldView.claims`, is absent from the outline
view, cannot be selected, and its identifier appears in no request the browser makes. *Test:*
growth › `test_a_skeleton_carries_no_number_and_no_identifier`. **Also: visual review checklist line
5** (is there a number nobody computed?).

**INV-workbench.63 — the skeletons are the frontier, and nothing else.** For every stream and after
every event in it, the set of skeletons on screen is exactly the set named by the most recent
`frontier` the stream carried — from `proposal_accepted` or from `proposal_rejected`, whichever came
last — and is empty from `beliefs_propagated` onward. In particular a claim closed by its third
refusal loses its rectangle on that refusal, not on the next accepted proposal. **And the set is
empty from `failed` onward, and from the moment a body ends with no terminator at all** *(added
2026-09-21)*: a rectangle is a promise that a claim is coming, and in both of those nothing is.
*Tests:* growth › `test_a_closed_claim_loses_its_skeleton_on_the_event_that_closed_it`,
`test_every_skeleton_goes_when_the_beliefs_arrive`, `test_every_skeleton_goes_when_a_run_breaks`; the
run › `test_a_stream_that_just_stops_takes_the_rectangles_down`.

**INV-workbench.64 — nothing already placed moves.** For every stream and every event in it, every
tile that had a position before the event has the identical position after it. That the layout
machinery guarantees this is [`layout-and-zoom.md`](layout-and-zoom.md)'s INV-workbench.22; this is
the same promise stated over a stream rather than over one added claim. **`beliefs_propagated` is an
event in it** *(2026-09-21)*: it replaces the world wholesale, every claim comes back carrying its
likelihood, every tile gains a chip and so every tile can change height — and a box whose height
changed drops its pin. It is the one event that could move a tile a reader is already looking at, and
it was the one event the walks stopped short of. *Tests:* growth ›
`test_a_tile_keeps_its_place_when_a_later_tile_arrives`; layout ›
`test_no_two_tiles_in_a_column_collide`; `frontend/e2e/generate.spec.ts`. **Also: visual review
checklist line 13.**

**INV-workbench.65 — a wire draws only after both ends exist.** For every stream, including one built
so that an arrow arrives before one of its ends, no wire is rendered unless both of the claims it
joins are on the map; an arrow whose ends are not both present is held and drawn when the second
arrives. The generator behind the test **builds** such a stream rather than assuming one cannot
occur. *Test:* growth › `test_a_wire_draws_only_after_both_ends_exist`.

**INV-workbench.66 — chips resolve last, and once.** For every stream, no claim's `beliefs.model`
holds a number at any point before `beliefs_propagated` arrives, and the world the reducer holds
afterwards is the world that event carried and nothing else. For every stream carrying more than one
such event — which the engine does not produce, and the test builds anyway — folding the whole stream
gives the same world as folding only the last of them, so no number is ever blended with an earlier
one or rolled through a value in between. *Test:* growth › `test_chips_resolve_last_and_only_once`.

**INV-workbench.67 — every refusal is on screen, in the validator's words.** For every
`proposal_rejected` event, a row appears in the refusal strip carrying `claim_in_words` and one line
per entry in `violations`, each line being that violation's own `message` with no text added, and no
refusal is dropped, merged or summarised. No rendered element derives its text from a `Violation`'s
`code`. *Tests:* strip › `test_a_rejected_proposal_is_shown_not_hidden`;
`frontend/e2e/generate.spec.ts`, which requires at least one refusal on screen. **Also: visual review
checklist line 13.**

**INV-workbench.68 — the reducer computes nothing.** For every module under `frontend/src/stream/`,
no expression combines two values read from an event with `+`, `−`, `×` or `÷`, and every number
rendered from a generation is a field on an event. Counting the rows in a list the reducer holds, and
comparing a value with a fixed threshold, are excluded by name. *Tests:*
`frontend/src/graph/__tests__/noArithmetic.test.ts` › `test_canvas_never_combines_two_model_numbers`,
extended to `frontend/src/stream/`; strip ›
`test_the_receipt_strip_prints_every_field_and_adds_nothing_up`. **Also: visual review checklist line
5.**

**INV-workbench.69 — an unknown event is ignored and reported.** For every event name the build does
not know, the reducer leaves its state otherwise unchanged, counts the name, and the Inspector's
generation section renders the name and the count. No unknown event throws, and none is silently
discarded. *Test:* reader › `test_an_unknown_event_name_is_ignored_and_reported`.

**INV-workbench.70 — the Verify door's two answers are two cards, and no bridge is drawn.** For every
`verdict` event: `reached` renders the steps of `path` in order with the product from `product` and
no multiplication in the component; `no_path` renders `why` and names `nearest`; and in neither case
is any wire, tile or dashed element rendered between the nearest claim and a destination that was not
reached. *Test:* strip › `test_no_path_renders_its_own_card`.

**INV-workbench.71 — a replay says it is a replay, and names the day.** For every session where no
model key is configured, the replay badge is on the canvas from the moment the run starts; for every
`receipt` event carrying `mode: "replay"`, the badge names `recording_date`; and the launchpad
renders record 0012's sentence word for word with the day taken from the readiness answer. Where the
receipt's mode and the badge's source disagree, the receipt wins and the disagreement is rendered.
*Tests:* strip › `test_the_replay_badge_names_the_recording_date`;
`frontend/src/components/__tests__/launchpad.test.tsx` › `test_the_keyless_sentence_is_word_for_word`.

**INV-workbench.72 — the receipt is the engine's, whole, and drawn once (NFR-6).** For every
`receipt` event, the strip renders `model`, `calls`, `input_tokens`, `output_tokens`,
`cache_read_tokens`, `searches`, `dollars`, `seconds`, `effort` and `mode` — **ten** fields *(amended
2026-09-21: `effort` is the tenth)*, each labelled, none omitted and **none derived, which includes
none shortened** — and before the event arrives no cost, token count, search count or elapsed time is
rendered anywhere. **None derived** means none worked out from the others and none shortened to
something a reader cannot check: a fingerprint is printed whole. The two roundings that do happen
are roundings of one field for the page — dollars to the two places money has, seconds to one — with
the value itself untouched and nothing downstream reading the string; and an amount above nothing
and below a cent prints `<$0.01`, a bound stated where there is a bound to state and never in place
of a figure that exists. The same ten are drawn for an insert's own receipt, by the same strip.
**The ten are rendered in exactly one place on any screen** *(amended 2026-09-21)*: the Inspector's
view of the generation holds the working and points at the strip, and renders no copy of them. *Tests:* strip ›
`test_the_receipt_strip_prints_every_field_and_adds_nothing_up`,
`test_the_cost_is_drawn_in_one_place_and_the_panel_points_at_it`,
`test_the_mode_row_says_the_mode_and_the_day_and_nothing_else`,
`test_the_strip_says_how_hard_the_model_tried`,
`test_the_panel_prints_the_prompt_fingerprint_whole`; canvas ›
`test_canvas_never_combines_two_model_numbers`, which walks every module under
`frontend/src/stream/` for arithmetic on any of the receipt's own field names.

**INV-workbench.73 — growth spends the animations already budgeted.** For every animation a
generation causes, it is the propagation wave or an opacity change of at most 120 milliseconds, and
under `prefers-reduced-motion: reduce` every tween is `0ms` while the 60-millisecond stagger between
columns remains. This is [`color-motion-type.md`](color-motion-type.md)'s INV-workbench.18 with
nothing added to it. *Test:* `frontend/src/styles/__tests__/motionBudget.test.ts` ›
`test_no_duration_above_120ms_outside_the_three_budgeted_moves`,
`test_reduced_motion_zeroes_every_tween_and_keeps_the_stagger`. **Also: visual review checklist line
10.**

**INV-workbench.74 — nothing is silently inert without a key.** For every control a generation needs
— the hypothesis field, the destination field, the likelihood slider, **Add a claim** — whenever the
thing it would do cannot be done (no key, for anything the reader typed; no key and no recorded
intervention, for **Add a claim**) the
control is visibly disabled and carries a sentence saying why. There is no control anywhere that
accepts an interaction and does nothing. **A launchpad card is not on that list, because it is never
disabled** *(amended 2026-09-21)*: no key **and** no recording means there is nothing the card could
do, so there is no card at all, and one line under the ones that remain names the examples it stands
for. A control a reader counted and cannot use is the same fault as one that does nothing when
pressed. **A control that has been pressed and whose request comes
back a rejection comes back to life and says so** *(added 2026-09-21)*: **Add a claim** leaving its
button disabled and reading *Drafting the claim* for as long as the tab is open is the same fault
with a different first frame. *Tests:*
`frontend/src/components/__tests__/launchpad.test.tsx` ›
`test_nothing_is_silently_inert_without_a_key`; `frontend/e2e/generate.spec.ts` ›
*add a claim on a generated map declines in the server's own words*.

**INV-workbench.75 — one press asks for one generation** *(added 2026-09-21)*. For every press of a
launchpad card or of **Build the map**, exactly one `POST /api/generate` is made — including under
React's strict mode, which mounts every screen, unmounts it and mounts it again on purpose. The
request is therefore made **inside the press**, which is an event and fires once, and never from a
render or an effect, which do not. There is nothing to guard and no window in which a second request
can be made, because the only code that makes one runs inside a click. Letting go of a run is a press
for the same reason: a development-mode unmount must not stop a run nobody left. *Test:* the run ›
`test_one_press_makes_one_request_under_strict_mode`.

**INV-workbench.76 — a stream that ends without a terminator says so, and offers to run it again**
*(added 2026-09-21)*. For every generation whose body ends with neither `done` nor `failed`: every
reserved rectangle comes down, every claim and arrow that arrived stays exactly where it is, nothing
is invented in the gap, one plain sentence says the stream ended before the run said it had finished,
and one control offers the same sentence again **with what pressing it costs written on its face** —
spending on a copy with a key, spending nothing on a copy playing recordings. It is not drawn as a
failure, because nothing on this side failed. *Tests:* the run ›
`test_a_stream_that_just_stops_takes_the_rectangles_down`,
`test_a_body_that_ends_after_done_is_a_body_ending_normally`,
`test_the_screen_says_the_stream_ended_and_offers_to_run_it_again`.

**INV-workbench.77 — a box that holds more than it shows says which edge** *(added 2026-09-21)*. For
the panel beside the map and for the stage the map sits on, a two-pixel rule in `--text-muted` is
drawn at each edge that has content beyond it and at no edge that has not. The two measure themselves
differently — one is scrolled, one is panned — and draw the same rule, because *there is more this
way* is one fact. A scrollbar does not discharge this: on a Mac it is an overlay that appears on a
gesture, so it speaks only to somebody already scrolling, and a panned map has none at all. *Test:*
`frontend/e2e/generate.spec.ts`, which compares what the stage says about its edges with where the
tiles actually are.

**INV-workbench.78 — the live region says what changed** *(added 2026-09-21)*. For every event folded
into a generation, the polite line a screen reader speaks is about **that event** — a claim arrived,
a proposal was refused with the rule's own sentence, the likelihoods landed, this is why it stopped —
said once, at the moment it became true, and never repeated on a later event. A region that re-reads
the whole run announces every refusal again on every arrival, so a listener hears the thing that just
happened last, after a minute of things they already knew. *Tests:*
`frontend/src/a11y/__tests__/growth.test.ts` › `test_a_refusal_is_read_out_once_and_not_again`,
`test_every_claim_that_arrives_is_announced_by_its_own_words`.

**INV-workbench.79 — a box waits for its place, and a rectangle waits for its claim** *(added
2026-09-21)*. For every stream and every moment in it, including the moments between an event
arriving and the layout answering for it: every box on the map is drawn at the place the layout gave
it and at no other place; no claim is drawn that the layout has not placed; while any box on the map
is still waiting for a place, every reserved rectangle that was standing goes on standing where it
stood; and once no box is waiting, the rectangles are exactly the ones the frontier asks for — so a
map that is still growing always has one, and a map that is finished, broken or ended early has none.
The one box the map places itself is the rectangle held open for the reader's own sentence, at the
origin, before the layout has answered anything at all; it is never a claim. *Test:*
`frontend/src/graph/__tests__/onTheGlass.test.ts` ›
`test_a_rectangle_stands_at_every_moment_the_map_is_still_growing`,
`test_no_rectangle_stands_once_nothing_more_is_coming`,
`test_a_claim_is_only_ever_drawn_where_the_layout_put_it`,
`test_the_first_rectangle_keeps_the_readers_own_words_until_the_layout_answers`,
`test_no_two_boxes_are_ever_drawn_in_one_place`, each walked over two runs with the layout answering
late; `frontend/e2e/generate.spec.ts`, whose `heldWhenEachClaimArrived` is the same statement read off
a real browser; and `frontend/e2e/lateLayout.spec.ts`, which is that browser reading with the layout's
background thread held back nine hundred milliseconds on purpose *(added 2026-09-21)*. Both browser
tests make the statement through one helper, `frontend/e2e/watching.ts` › `theMapArrivedInSteps`.

**What this invariant does not say, and why it matters.** It says a rectangle stood at every
*arrival* — every moment the screen changed to show a new claim — and not at every *claim*. Those are
different: a browser gathers whatever has landed since the last frame into one render, so two events
arriving close together paint once and the two claims they carried appear together. A test that
demanded one arrival per claim would be demanding that the browser never batch, which no browser
promises and nothing here needs; that the events leave the server one at a time is a promise about
the stream (FR-5), tested on the server's own clock by
`backend/tests/api/test_the_stream_is_not_buffered.py` ›
`test_the_events_of_a_replay_are_let_go_of_one_at_a_time`. *(Written down 2026-09-21, after the
browser test asked for the stronger thing for a while and was quietly held up by the replay's pace.)*

---

## ANTI-PATTERNS

1. **Do not put a spinner anywhere, not even for a moment, not even a small one.** *Because* a
   spinner says only "wait", and the thing being waited for has a shape — a claim at a column, a
   number in a slot — which says "wait" *and* what for *and* where it will land. It is also a named
   veto condition (PRD §10 anti-pattern 9). **Instead:** a reserved rectangle where the claim goes,
   and an absence with its reason where the number goes.

2. **Do not animate a skeleton.** *Because* a shimmer is a tool performing busyness at a reader who
   is waiting on a model call that takes seconds, and the fourth animation would be the one that
   turns a motion budget into a suggestion. **Instead:** a still rectangle, appearing and going with
   an opacity change of at most 120 milliseconds.

3. **Do not let a belief chip fill in as its causes arrive.** *Because* a likelihood computed from
   half a map is the answer to a question about a map that will not exist in a second, and a number
   that changes four times is four numbers nobody computed. **Instead:** every chip reads *no engine
   yet* until `beliefs_propagated`, and then they all resolve at once, once.

4. **Do not hide, merge or summarise a refusal.** *Because* watching our own rules turn the model
   down is the evidence that the model is not in charge of the map, and a run that shows only its
   successes is a demo rather than a tool. **Instead:** one row per refusal, every sentence the
   validator wrote, kept on screen for the run and in the transcript afterwards.

5. **Do not draw a refused claim as a faint tile, a ghost or a struck-through box.** *Because* the
   moment it has a box it needs an identifier, and the model would then have caused an identifier to
   exist — which the schema is shaped to make impossible. **Instead:** quote its words in the strip
   and give it nothing else.

6. **Do not draw a bridge to a destination the map did not reach.** *Because* "no path reaches this"
   is the most valuable answer the Verify door has, and a dotted arrow suggesting one might is a
   fabrication in the exact place the honesty bar exists to prevent one (FR-7). **Instead:** the
   engine's sentence, the nearest claim named, and nothing drawn between them.

7. **Do not re-layout the map while it grows to make the picture tidier.** *Because* a map that
   rearranges itself under the reader's eye costs them the tile they were reading, which is the
   failure the whole layout chapter exists to prevent. **Instead:** pin absolutely, let a late arrival
   find a gap, and say out loud what that costs (B3).

8. **Do not estimate the cost, the progress or the remaining claims while a run is going.** *Because*
   a percentage nobody computed is a number nobody computed wearing a progress bar, and the caps that
   would have to be divided by are the server's and are not on the stream. **Instead:** show what has
   arrived, and the receipt when the receipt arrives.

9. **Do not throw on an event name the build does not know, and do not swallow it either.** *Because*
   a browser that crashes on a new event makes the server unable to add one, and a browser that
   drops it silently makes a missing feature look like a working one. **Instead:** ignore it, count
   it, and say so in the transcript.

10. **Do not let the browser build a second version of the world beside the engine's.** *Because* the
    growing map and the propagated world would then be two answers to one question, and the day they
    differ by half a point nobody can say which is right. **Instead:** the drawing is thrown away
    when `beliefs_propagated` arrives, and the engine's world is the world.

11. **Do not fill in "I don't know".** *Because* a `.5` posted on the reader's behalf is the one
    number in the request that nobody elicited, and it would sit on the hypothesis as a `user` belief
    for the rest of the session. **Instead:** send no user belief at all, and let the slot read its
    own absence.

12. **Do not give a box a place because the layout has not answered yet** *(added 2026-09-21)*.
    *Because* the only place available to give is the map's origin, which either belongs to a box
    already standing there or is about to belong to this one at coordinates the layout chose — so the
    box lands where it does not belong and then moves, on the one screen whose whole promise is that
    nothing already drawn moves. **Instead:** draw nothing that has no place, and let the rectangle
    already standing go on saying where the claim is going until the claim itself is drawn.

---

## Open questions

*Raised 2026-09-17.*

1. **Should the stream say when a call goes out?** The eight events say what came back, so the
   browser can draw the frontier but cannot honestly say how many proposals are in flight — three
   calls against one open claim show one rectangle (B2). A ninth event would fix it and would also be
   the first event that carries no decision, only activity, which is a different kind of thing to put
   on a stream. **Owner:** `spec/generation/streaming.md`, if anyone ever wants the count on screen.

2. **Does the map re-lay out once when the run finishes?** **Answered 2026-09-21: no — and the real
   question turned out to be a different one.**

   The measurement, taken on the coordinator's ten-claim run at 1600 × 1000, the size the whole
   interface is designed against: the stage is **1264 × 801**, the map is framed at **0.85** — the
   floor below which a tile would have to become a summary — and at that framing **six of the ten
   tiles are whole on the glass, four are wholly below it and none is cut**. No arrow points
   backwards, on this run or on the chapter's own, so the thing a re-layout would have tidied did not
   happen; what did happen is that **a third of the map was off the screen with nothing saying so**,
   which is far worse and is not a layout problem at all. A map that is cut with nothing saying so is
   read as a map that ends there, and for a causal map that is the worst thing it can be read as: the
   reader concludes the argument stops where the window does.

   So the answer is the one that costs the reader nothing: **the map is never re-laid out, and the
   stage says where it is cut.** A two-pixel rule in `--text-muted` sits at whichever edge has map
   beyond it and at no edge that has not — the same rule, the same weight and the same colour the
   panel beside it already uses for the same fact, drawn as the four sides of one box so a corner
   reads as a corner. The stage measures it about itself, because the two boxes are measured
   differently: a panel is scrolled and a stage is panned.

   Re-laying out would still move every tile once at the moment the reader starts reading, and it
   would still not put the four tiles on the glass — there is no zoom that fits ten tiles in 1264 ×
   801 and keeps them readable, which is exactly why the zoom floor exists. **Owner:** closed.

3. **What does an `insert` cost, and where does that show?** **Answered 2026-09-20 by
   [`spec/generation/streaming.md`](../generation/streaming.md), drawn 2026-09-21, and nothing is
   open.** The route answers a `DraftedInsert` — the edit and its own `Receipt` — and the cost is
   drawn beside the drafted claim by the same strip, with the same ten readings, that a generation's
   receipt is drawn by. What made it answerable was learning that an insert is **several** calls
   rather than one: the starting-claim shape drafts the reader's sentence, and then the ordinary walk
   proposes its arrows, one call each. A running total in the browser lost on two counts — it is a
   number added up by something other than the engine, and it vanishes on a page reload. **Owner:**
   closed. See B8.

4. **Where does a replayed run's pacing come from, and is it the same on every machine?**
   **Answered 2026-09-17 by `spec/generation/replay.md`, and nothing is open.** The delay is fixed on
   the **server** — an argument with a default the builder picks against a measurement, because a
   replay that races teaches a reviewer that the product is faster than it is — so two readers' replays
   are the same length. It is **one setting**, `KATALYST_REPLAY_PACE` in seconds, read once by
   `katalyst.settings` and never a field on the request: a client that could ask for a replay with no
   pause would let anyone with the network tab open skip the thing the recording exists to show. A
   pace of zero means no pause at all, which is the same question answered with a smaller number
   rather than a second switch beside it *(2026-09-21; it was a length and an `instant` flag)*. **The browser
   therefore paces nothing, waits on nothing, and has no pacing code at all** — it reads events as
   they arrive, which is the same thing it does live.

5. **How long is a refusal strip allowed to get?** Three refusals close an open claim and the caps
   bound the whole run, so the strip is bounded — but nothing says by what, and a run that refused
   twenty proposals would fill the dock and push the Inspector off the screen. Scrolling the strip is
   the obvious answer and it is also the answer that lets a reader miss a refusal. **Owner:** this
   chapter, once a real run has been watched.
