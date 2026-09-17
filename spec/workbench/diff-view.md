# The diff view — two worlds in one picture

## Purpose

You supposed the strait reopens. Then you added a strike the next day. Two maps now exist, and one
question matters: **what did my edit reach, and what did it provably leave alone?**

The diff view answers it in one picture. Both maps are laid out **once**, together, then painted
twice in the same coordinates — the new world solid, the old world faint behind it. Nothing moves
between them, so every difference you see is a real difference and not a re-layout.

Before the engine exists that answer is **structural** — *here is what your edit can reach, and here
is what it cannot* — and where a number will later sit, this stack draws **an absence with its
reason**: never a blank, never a zero, never a stand-in.

This chapter owns the ghost overlay, the delta rail, the A ⇄ A′ toggle and the branch panel — and,
because every number slot on the world uses them, the `Known<T>` and `Absence` shapes the whole of
`spec/workbench/` reads.

---

## Data model

### The seam — `WorldSource`

The engine (stack 03a) and the canvas (this stack) are built at the same time. One interface keeps
them apart, and it is the only place the canvas learns anything:

```ts
export interface WorldSource {
  /** The base map and its branches, as the fixture route already serves them. */
  readBundle(id: string): Promise<FixtureBundle>;
  /** One world. Its numbers are OPTIONAL — see `Known<T>` below. */
  readWorld(request: WorldRequest): Promise<WorldView>;
}
```

Two implementations, and the screen cannot tell which it has. `FixtureWorldSource` reads
`GET /api/fixtures/hormuz` and uses the fixture's stored `beliefs.model` for the **base** world —
honest, because the fixture says in its own comments that those are illustrative. `ApiWorldSource`
calls `POST /api/worlds` and `POST /api/worlds/diff` once they exist.

**For the second world, before the engine, there is no second set of numbers at all.** No committed
illustrative world, no hand-written likelihoods, no "illustrative numbers" chip. A number nobody
computed is exactly the state a reader cannot trace.

### `WorldView` — this stack's own view model

`WorldView` lives in `frontend/src/world/types.ts` and is **written by hand**, not generated from
`frontend/src/api/schema.ts`, which belongs to stack 03a this cycle. Three kinds of absence need
three different sentences, so an absence carries both its kind and its sentence:

```ts
/** A value we may not have. Never a blank, never a zero, never a placeholder. */
export type Known<T> =
  | { known: true; value: T }
  | { known: false; absence: Absence };

export interface Absence {
  /** Which absence this is; it picks the words. */
  kind: "no_engine" | "no_market" | "not_said";
  /** The sentence shown beside the words. Always present, never empty. */
  reason: string;
}

/** `killed` is forced false, full stop. `shifted` needs two numbers, so it arrives with the
    engine and is never produced here. */
export type DiffState = "added" | "killed" | "downstream" | "untouched" | "shifted";

/** `branchId: null` is the base world, the empty branch; the seed makes a world replay. */
export interface WorldRequest { baseId: string; branchId: string | null; seed?: number }

export interface WorldView {
  baseId: string;
  branchId: string | null;
  claims: ClaimView[];
  links: LinkView[];
  terminals: DeltaRow[];        // what the delta rail draws
  headline: Known<string>;      // the one-line plain-English diff (FR-16)
  /** How many versions of the map the engine ran to produce these numbers.
      Absent when nothing was computed — which is what picks the chip's sentence. */
  versions?: number;
}

/** One claim as this stack reads it. `TileProps` and `ClaimDetail` are projections of it. */
export interface ClaimView {
  id: string;
  claim: string;                                                  // the full sentence
  kind: "hypothesis" | "event" | "market" | "not_tradeable";
  resolution: { criteria: string; source: string; by: string };   // all three required (INV-1)
  prior: BeliefView;
  baseRate: Known<BaseRateView>;
  beliefs: { model: Known<BeliefView>; user: Known<BeliefView>; market: Known<BeliefView> };
  evidence: readonly EvidenceView[];
  diff: DiffState;
  badges: readonly Badge[];              // Supposed · date, Added, Retracted · date · by "…"
  states: Known<readonly SeriesState[]>; // supposed → withdrawn → pushed, with dates
  decomposition: Known<Decomposition>;   // prior, a line per incoming arrow, the result
  pathProduct: Known<PathProduct>;       // INV-8; computed on the world, never here
  rangeShares?: Record<string, number>;  // stack 06 — nothing reads it yet
}

/** One arrow as this stack reads it. `WireProps` and `LinkDetail` are projections of it. */
export interface LinkView {
  id: string; source: string; target: string;
  mode: "trigger" | "sustain";
  strength: number;                      // signed; on the log-odds scale
  lag: number;                           // days
  shape: "impulse" | "step" | "ramp";
  halfLife: number | null;               // impulse only
  reflexive: boolean;                    // a feedback arrow: a market acting back on the world
  rationale: string;
  sources: readonly { url: string; title: string; retrieved: Known<string> }[];
  provenance: "documented" | "historical" | "market_implied"
            | "argued" | "user" | "asserted" | "simulated";
  conditional: Known<BeliefView>;        // the midpoint chip; fetched one arrow at a time
}

export interface DeltaRow {
  claimId: string;
  label: string;                                     // the terminal's own words
  move: Known<{ from: number; to: number; largestOn: string }>;
  rangeWidth: Known<number>;   // "how firm": the width of the new world's own range on this claim
  agreement: Known<number>;    // "same direction": the share of versions that moved the same way
}
```

Every number slot is `Known<T>`, so an absent number **cannot** be rendered as anything but its
reason — a type-level guarantee, not a convention.

**`BeliefView`** — one likelihood with its range and a name on it — is defined once in
[`tiles-ports-wires.md`](tiles-ports-wires.md), because the belief chip is the only component that
takes one. `TileProps` and `WireProps` there, and `ClaimDetail` and `LinkDetail` in
[`inspector.md`](inspector.md), are projections of `ClaimView` and `LinkView` above.

**One field, two spellings, said once here.** The server's wire name is `range_width`; the view
model's is `rangeWidth`. Same number, and neither is ever shown — the rail's column is headed **how
firm**. Likewise the field `agreement`, whose column reads **same direction**: the bare word
*agreement* is left free on screen for stack 04's run-to-run number.

### Component props

```ts
interface GhostOverlayProps {
  now: WorldView; before: WorldView;   // A′ painted solid; A painted faint and dashed
  positions: PositionMap;              // the union layout, computed once
  showing: "now" | "before";           // which one Space last selected
}
interface DeltaRailProps  { rows: DeltaRow[]; ranked: boolean }   // ranked is false in this stack
interface BranchPanelProps { branch: BranchView; onEdit: (edit: Intervention) => void }  // appends
```

`PositionMap` is defined in [`layout-and-zoom.md`](layout-and-zoom.md), which owns layout.

**Tokens read:** `--surface`, `--surface-raised`, `--hairline`, `--text`, `--text-muted`,
`--accent`, `--focus`, `--font-mono` for every number, `--space-1` … `--space-4`, the likelihood
ramp `--p-0` … `--p-4`, and the branch palette — violet, teal, rose, slate. All are defined in
[`color-motion-type.md`](color-motion-type.md); this chapter defines no token and changes none. A
direction, once the engine lands, is rendered through `DirectionReadout`, which owns those tokens.

---

## Behaviour

Worked on the Hormuz map (the cast is in [`README.md`](README.md)). This chapter uses all seven base
claims, and the branch `br_hormuz_then_strike`: suppose **H** true on Oct 1; add **S** *a confirmed
military strike on Iranian territory* with three arrows (S → B, S → C, S → H); suppose S true on
Oct 2. The map's "today" is 2026-10-01.

### B1 — One layout, two paintings

Lay out the union of both worlds **once**. Every claim in both gets one position. Then paint twice
into that one coordinate space: **A′** at full opacity and solid, **A** at **20%** opacity, dashed,
behind it. Nothing shifts and nothing fades into anything, so a tile in the same place in both
paintings really is the same claim. On Hormuz the union is eight tiles — the seven base claims plus
S, the only one with nothing behind it.

The hover lens *multiplies* that 20% rather than replacing it
([`tiles-ports-wires.md`](tiles-ports-wires.md)), so a tile that is both off the hovered path and
old lands near 3% and disappears — which is correct: you asked to see one path in one world.

### B2 — The four structural states, computed from the branch

Each tile carries a diff state and the state drives how it is drawn. In this stack there are four,
and **every one is computed from the branch alone**:

| State | Computed from the branch by | Drawn as |
|---|---|---|
| `added` | The claim arrives in an `insert` | Solid, with an accent ring |
| `killed` | The claim is the target of a **Suppose this is false** — full stop | Ghosted, struck through, desaturated |
| `downstream` | The claim is in the affected set of at least one edit — a claim your change **can** move | Drawn live, its number slot reading *"no engine yet"* |
| `untouched` | Everything else. Byte-identical, and the canvas can say so without hedging | Neutral |

**`killed` means forced false and nothing else** (Kent, 2026-09-17). "No path from the hypothesis
reaches this claim any more" is a fact about a *route*, not a state of a claim, and the Inspector's
path bar reports it in those words. No claim is ever **only in A**, either, because no edit removes
one. Nothing in the Hormuz bundle supposes a claim false, so `killed` is drawn but not exercised by
the worked example; a unit test over a hand-built branch covers it.

**Following arrows is reachability, not arithmetic** — no strength is added, no likelihood is
moved, no shape is evaluated. Which claims each operation reaches, and which arrows count, are both
settled in [`../multiverse/interventions.md`](../multiverse/interventions.md): the affected-set
table, and one named rule — *the map the engine works through is the map with feedback arrows set
aside*. Anything asking **what can move** reads that map, these diff states included; anything
asking **what can I walk to** reads the whole map — the hover lens, `h`/`l`, the outline.

On the strike branch: **S** is `added`; **H** is `downstream`, because S → H was inserted *after*
the supposition on H and so is live; **C** and **B** are `downstream` from H and again directly from
S; **N1** through H → N1; **M1** and **M2** from B. And, as a consequence of that rule:

> **R — *OPEC+ announces output restraint* — is `untouched`. Nothing on this branch can reach it.**

R's only incoming arrow is B → R, the **feedback** arrow — a price outcome acting back on what
producers do. Set aside, R has no incoming arrow at all: an ancestor of B, never a descendant of
anything this branch touches. So the screen can say out loud: *your strike moves the oil price, the
insurance premium, both contracts and the diplomatic ending — and it cannot move OPEC's
announcement.* That sentence is the product, and `INV-workbench.41` and `.42` below pin it.

### B3 — The fifth state arrives with the engine, and nothing is deleted

`shifted` — `.61 → .18` with a directional chevron — needs two numbers to compare, so it cannot
exist here. When `ApiWorldSource` is switched on in stack 04 the empty slots fill and `shifted`
appears. **Nothing written in this stack is deleted then, because nothing false was written.** The
authority changes hands: the server's `affected_set` becomes the truth and the browser's structural
states become a **hint that must agree with it**, pinned by a component test on the Hormuz branch. A
browser quietly disagreeing with the engine about what an edit reached is the traceability veto
wearing a disguise.

### B4 — A ⇄ A′ is a hard switch, never a crossfade

`Space` swaps which world is solid — an instant switch, not a fade. Two half-drawn worlds on top of
each other is a picture of nothing, and a crossfade invites the eye to read the blur as a number
moving. The transition is **scrubbable**: sit on either side, go back and forth, and the map never
re-lays-out. Under `prefers-reduced-motion: reduce` there is nothing to remove, because there was
never a tween.

### B5 — The delta rail, before the engine and after

The rail sits beside the canvas and lists what changed at the **endings** — the claims that name an
instrument, or name why there is none. **With the engine** it is the terminal changes, ranked, one
line each, in the order the engine gave them:

> the Polymarket Brent contract · `.61 → .18` ▼ · largest on Oct 9

That order is the size of the move times the **weakest arrow on the best-backed route** from any of
the branch's edits to that ending — the route whose weakest arrow is strongest. Two factors and no
more; the engine computes it, the rail renders it in the order given, and beside it sit **two
columns that are never folded into the rank**:

| Column on screen | The question it answers | Field |
|---|---|---|
| **how firm** | *How firm is this number?* The width of the new world's own range on that claim — the same quantity the tile shows, so the rail and the tile cannot disagree | `rangeWidth` |
| **same direction** | *Did it point the same way whatever numbers we started from?* The share of the 2 000 versions of the map that moved in the same direction | `agreement` |

Different questions, weighed separately by a trader, which is why they are columns and not one
score. Folding width into the rank would sink exactly the claims that most deserve attention.

**Before the engine — this stack — the rail does not rank and does not compute.** It lists the
terminals the edit can reach, in **map order**, each with an absence and a reason where the number
will go:

```
                                                   change          how firm   same direction
M1  Polymarket "Brent below $70 on 2026-10-31"     no engine yet   —          —
M2  XLE underperforms SPY by more than 3%          no engine yet   —          —
N1  Omani-mediated talks resume                    no engine yet   —          —
```

Each dash carries the same reason as the change beside it: no engine yet. All three endings are
reachable here, so all three are listed; R is not a terminal and never appears. **A rail that
invented an ordering would be inventing the one thing the rail exists to tell you** — map order is
visibly arbitrary and says so; a fabricated ranking looks like an answer.

**The one-line summary above the rail** (FR-16) has a fixed second form for the case where the rail
has nothing to report: *"<edit> moves no ending and leaves <n> claims untouched."* Both forms are
sentences the world carries. Before the engine the summary is an absence with its reason, like every
other computed thing on this screen.

### B6 — UX-14: an assertion a later edit overrode says so

A claim the user supposed true, and that a later edit in the same branch pushed back down, is
**never drawn as plainly true**. H's tile carries both states in order, word for word:

> **Supposed · Oct 1 → Retracted · Oct 2 · by "a confirmed military strike on Iranian territory"**

**While a claim is supposed, its tile shows the word where a likelihood would go** — *Supposed ·
Oct 1*, not `1.0` and not `.98`. A supposition is a hard fact in every simulated world while it
holds, so there is no number to show, and inventing one answers a question nobody asked.

After the retraction the claim passes through three named states. **Every part of the line and the
series is data, never inference** — and this stack has some of it and not the rest:

| Part | On Hormuz | Comes from | Needs the world? |
|---|---|---|---|
| **Supposed · Oct 1** | Oct 1; H shows the word, not a number | The assignment itself: an earlier supposition on H, with its date | **No** — the branch carries it |
| **Retracted · Oct 2 · by "…"** | Oct 2 | A `sustain` arrow into H inserted afterwards, and the later edit that makes its source true; the quoted words are S's own `claim` field | **No** — structure and dates, the same reachability the four states use |
| **withdrawn** | Oct 2 – Oct 4, `.35`, labelled *"withdrawn — no live push yet"* | The `states` series: the cause of the opposing arrow became true on the 2nd, so we stop taking the user's word; S → H's three-day delay has not run | **Yes** |
| **pushed** | Oct 5 onward, about `.070` | The `states` series: the delay has run and S → H's −1.9 push lands on the prior | **Yes** |

So in this stack H's tile carries the badge pair and its order, its number slot reads *"no engine
yet"*, and the series is absent with its reason. As with the affected set, the browser's derived
badge becomes a hint the world must agree with once the engine lands. (`.070`, not `.07`: two
significant figures on every number, the rule [`keyboard-and-access.md`](keyboard-and-access.md)
owns.)

**The three-day gap between the badge's date and the day the number moves is honest, not something
to smooth away.** A supposition ends the day its undermining *cause* becomes true, not the day that
arrow's push arrives — otherwise "do I still take your word for this" would hang on a delay
parameter, and changing a lag from three days to thirty would let the supposition outlive the news
(decision record 0014).

### B7 — The branch panel: a sequence, not a surprise

The panel lists that branch's edits **in the order they were made**, each with the badge its
operation earns. Read as a sequence, the rule that a later addition outranks an earlier supposition
is obvious; met as a number that moved on its own, it reads as a bug.

```
Hormuz opens, then Iran is struck                        ● violet
 1  The Strait of Hormuz reopens…                        Supposed · Oct 1
 2  A confirmed military strike on Iranian territory.    Added
 3  A confirmed military strike on Iranian territory.    Supposed · Oct 2
```

**The six buttons and their badges**, copied word for word from
[`../vocabulary.md`](../vocabulary.md)'s *Interface words* table — copy, never paraphrase:

| Code name (never on screen) | The button | The badge afterwards |
|---|---|---|
| `do` | **Suppose this is true** (and **Suppose this is false**) | **Supposed · date** |
| `observe` | **This happened** | **Happened · date** |
| `insert` | **Add a claim**, hinted as "…but this also happens" | **Added** |
| `retune` | **Change this push** | **Retuned** |
| `refine` | **Split this claim** | **Split** |
| `believe` | **My own number** | none — the three-up belief chip is the badge |

And one derived badge no button produces: **Retracted · date · by "…"**. The six code names live in
the code, the wire format and the spec, and **none of them ever appears on screen**.

Three rules in this stack:

1. **The buttons build a branch and show it. They do not move a number.** **My own number** and
   **Change this push** append an edit and the panel shows it immediately; the likelihood slots stay
   as they were, reading their absence.
2. **Split this claim** is **visibly not yet live** and says so (stack 06). Never silently inert.
3. **Edits are appended, never edited in place.** The branch is the audit trail, and an audit trail
   you can edit is not one.

---

## INVARIANTS

Each is *for all X, statement P holds*, and each names what checks it: a component test, or a
numbered line of the **visual review checklist** in [`README.md`](README.md). Frontend test names
are `test_snake_case`. Short file names below: **diffState** is
`frontend/src/graph/__tests__/diffState.test.ts`, **deltaRail**
`frontend/src/components/__tests__/deltaRail.test.tsx`, **ghostOverlay**
`frontend/src/components/__tests__/ghostOverlay.test.tsx`. This chapter uses `INV-workbench.40` …
`.49`.

**INV-workbench.40 — one layout, two paintings.** For every claim present in both worlds, its
position in the A painting equals its position in the A′ painting, and toggling A ⇄ A′ changes no
position anywhere. That the union layout is itself stable is
[`layout-and-zoom.md`](layout-and-zoom.md)'s. *Tests:* ghostOverlay ›
`test_paints_both_worlds_from_one_position_map`, `test_space_changes_no_position`.

**INV-workbench.41 — every diff state is derived, never assigned.** For every claim in a branch
world, its `DiffState` is a function of the base map and the branch's edits alone: no component sets
a state and no state is read from a number. *Test:* diffState ›
`test_computes_the_four_structural_states_for_the_strike_branch`.

**INV-workbench.42 — what an edit cannot reach is said so.** For every claim outside the affected
set of every edit in the branch, the state is `untouched`. On the Hormuz strike branch that set is
exactly `{R}`. *Tests:* diffState › `test_r_comes_out_untouched`; `frontend/e2e/hormuz.spec.ts` ›
`test_the_fully_separated_claim_does_not_change`.

**INV-workbench.43 — the browser never out-votes the engine.** For the Hormuz branch, every state
the browser computed equals the state derived from the server's `affected_set`. Both read the map
with feedback arrows set aside, which is why they can agree at all; the day stack 06 unrolls them,
`test_a_feedback_arrow_never_carries_a_change` in the domain fails loudly and points at the one
sentence to change. Until stack 03a lands this test is skipped with its reason written in it, never
deleted. *Test:* diffState › `test_agrees_with_the_servers_affected_set`.

**INV-workbench.44 — `shifted` is never produced without two numbers.** For every pair of worlds in
which either side's likelihood is absent, no claim is `shifted`. *Test:* diffState ›
`test_never_shifts_on_an_absent_number`.

**INV-workbench.45 — no number slot is ever blank.** For every claim and every delta row in this
view, a slot without a value renders its `Absence.reason` as words — no empty string, no zero, no
dash-without-meaning (the one dash with a meaning is the empty user belief, absence kind
`not_said`). *Test:* deltaRail › `test_renders_a_reason_for_every_absent_number`; **visual review
checklist line 5**.

**INV-workbench.46 — the rail invents no order.** For every branch, while `ranked` is false the rail
renders the reachable terminals in the order the base map stores them, independent of every number
on the world. *Test:* deltaRail › `test_lists_reachable_terminals_in_map_order`.

**INV-workbench.47 — how firm and same direction are never folded into the rank.** For every rail
row the two are rendered as their own columns, and no ordering function reads either. *Test:*
deltaRail › `test_never_sorts_by_width_or_agreement`.

**INV-workbench.48 — a supposed claim shows the word.** For every claim under a live supposition,
the tile renders **Supposed · date** where a likelihood would go and renders no likelihood for it at
all; where a later edit undermined the supposition, both states render in order with the arrow
between them. *Test:* `frontend/src/components/__tests__/beliefChip.test.tsx` ›
`test_a_supposed_claim_renders_the_word_not_a_number`; **visual review checklist line 12**.

**INV-workbench.49 — the branch is append-only and reads in vocabulary words.** For every sequence
of button presses, the branch is the edits in the order they were made with no earlier edit altered,
and every badge on screen is one of the six — the five in the *Interface words* table plus the
derived **Retracted · date · by "…"** — with no code name anywhere. *Tests:*
`frontend/src/world/__tests__/branchReducer.test.ts` ›
`test_appends_edits_in_order_and_never_rewrites_one`, `test_renders_only_interface_words`; **visual
review checklist line 11**.

---

## ANTI-PATTERNS

1. **Do not commit a second set of numbers to make the diff look finished.** *Because* a number
   nobody computed cannot be traced to an input, a rule or a source — a veto condition — and once an
   illustrative world is in the tree everything downstream quietly believes it. **Instead:** ship the
   structure, which is real, and let every number slot render its absence with a reason.

2. **Do not crossfade A into A′** — stated as an anti-pattern in
   [`color-motion-type.md`](color-motion-type.md), which owns motion. Here it means a hard switch on
   `Space`, scrubbable, both worlds always in the same coordinates.

3. **Do not lay out A and A′ separately and place them side by side.** *Because* two layouts mean
   every tile moves a little, and a reader cannot tell a real change from a layout change.
   **Instead:** lay out the union once and paint into it twice.

4. **Do not rank the delta rail before something has ranked it.** *Because* a ranking is a claim
   about which change matters most, and an invented one is a lie in the exact place the reader came
   for the truth. **Instead:** map order, visibly arbitrary, until the engine supplies its own.

5. **Do not render a supposed claim as `1.0`, `.98`, `>.99` or a full bar.** *Because* a number
   invites the reader to wonder about the missing two per cent, and there is no such uncertainty.
   **Instead:** the word, and its date.

6. **Do not let a button move a number in this stack, and do not rewrite an edit in place.**
   *Because* a canvas that computes its own likelihoods is a second engine, and two engines
   disagree; and because an edited history explains nothing. **Instead:** append an edit and let the
   number wait for the engine, saying so meanwhile.

---

## Open questions

*Raised 2026-09-17. Four questions this chapter opened were settled by Kent the same day and now
read as statements in the body: which arrows carry a change (B2), what `killed` means (B2), which
columns the rail shows (B5), and what the one-line summary says when nothing moved (B5).*

1. **Does the retraction badge need the world, or is the branch enough for good?** This stack derives
   it from the branch. Once the world carries the retraction, two derivations of one line exist, and
   one should become the only one — probably the world's. **Owner:** stack 04, when
   `ApiWorldSource` is switched on.
