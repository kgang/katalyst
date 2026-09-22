# Layout and zoom — a map that never becomes a hairball

## Purpose

A causal map drawn by a physics simulation is a hairball: every run looks different, nothing lines up, and crossings hide the one arrow you were looking for. This chapter makes the map **arrive already arranged** — left to right, cause before effect, one claim per box, in an order that does not change under your feet. You open the Hormuz map and it is legible in the first second, without touching anything. You zoom out and the tiles turn into summaries rather than into unreadable specks. You add a claim, or open a branch, and the tile you were reading stays where your eye left it.

Three chapters sit next to this one and are not repeated here: `tiles-ports-wires.md` says what is inside a tile and how a wire is drawn, `color-motion-type.md` carries the colour law and the motion budget, and `diff-view.md` says how two worlds are painted once they share a coordinate space. This chapter owns only **where things go and how big they are**.

## Data model

### The layout options — the whole list, and nothing else

The automatic layout is ELK, an open-source graph-layout engine compiled to JavaScript. Five options, and no others:

```ts
const ELK_OPTIONS = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  "elk.layered.crossingMinimization.semiInteractive": "true",
  "elk.layered.spacing.nodeNodeBetweenLayers": "120",
} as const;
```

These five are set once, for the whole graph. One further ELK property, `elk.position`, is set **per tile** rather than here — it is how an already-placed tile says where it wants to stay (B3) — so "no others" stays true of this list.

In plain words:

ELK's word is *layer*; the code and the test names use it. On screen and in this chapter the word is **column**, because that is what a reader sees.

| Option | What it buys |
|---|---|
| `layered` | Claims are assigned to columns; every arrow points from a lower column to a higher one. This is what makes cause-before-effect a fact of the picture rather than a hope |
| `direction: RIGHT` | The columns run left to right. Time and causality read the way English reads |
| `nodePlacement.strategy: NETWORK_SIMPLEX` | Decides each tile's position **within** its column so that wires come out as straight as possible. Straight wires are short wires; short wires cross less |
| `crossingMinimization.semiInteractive: true` | When ordering a column, the crossing minimiser treats a tile's existing position as where that tile *wants* to sit. This is the switch that makes pinning work at all |
| `spacing.nodeNodeBetweenLayers: 120` | 120 pixels of gutter between one column and the next — enough room for a midpoint chip and an origin mark on the wire without the chip touching a tile |

One thing the list does not say out loud: **which column a claim lands in** is decided by ELK's *layering* strategy, which is a separate setting from `nodePlacement.strategy` above. We do not set it, so it is ELK's default — also network simplex — which picks the column assignment with the smallest total arrow length. The worked examples below are that assignment, and they are the unique minimum, so the picture is reproducible rather than merely likely.

### The worker seam

Decision record 0007 measures ELK at 50–150 milliseconds on sixty tiles. On the main thread that is a frozen page, a dropped keystroke, and a scroll that stutters. So it runs in a **Web Worker** — a second browser thread with no access to the page — and the main thread only posts and listens. (That upper figure is already over NFR-7's budget; see B9 and Open questions.)

```ts
/** What the page sends the layout worker. */
interface LayoutRequest {
  /** Every tile to place. Width is always 280. Height varies per tile: content-fit,
   *  clamped to 152–320 pixels, on the 8-pixel grid, **computed from the content** and
   *  never measured off the screen — so layout stays a pure function of the map
   *  (`tiles-ports-wires.md` owns the height rule, and the ceiling's reason). */
  tiles: { id: string; width: 280; height: number; pinnedAt?: { x: number; y: number } }[];
  /** Every wire. `reflexive` wires are marked here and set aside before layering. */
  wires: { id: string; from: string; to: string; reflexive: boolean }[];
}

/** One coordinate per tile, plus which column it landed in and where in that column.
 *  This is the type other chapters read: `diff-view.md` takes a `positions: PositionMap`
 *  and paints two worlds into it. */
type PositionMap = Record<string, { x: number; y: number; layer: number; orderInLayer: number }>;

/** What comes back. */
interface LayoutResult {
  tiles: PositionMap;
  /** For each column that overflowed seven tiles, the claims behind its "+n more" tile. */
  collapsed: Record<number, string[]>;
  /** How long ELK took. NFR-7's 100-millisecond budget is measured, not hoped for. */
  elapsedMs: number;
}
```

The page never imports ELK. The worker file is the only place `elkjs` appears in `frontend/src/`, and a test says so.

### What a tile tells the layout

```ts
interface TileLayoutProps {
  /** Set by the zoom watcher, never by the tile itself. */
  detail: "summary" | "full";
  /** Always false, on every tile, forever in this stack. */
  draggable: false;
  /** Drives `setCenter` and the focus ring. One tile at a time. */
  focused: boolean;
}
```

### Tokens this chapter reads

From `frontend/src/styles/tokens.css`: `--space-1` (8 px, the grid everything sits on), `--space-2` (16 px), `--hairline` (the 1-pixel border at 10% of the text colour), `--surface` and `--surface-raised`, `--focus` (the keyboard ring), and the type scale `--text-sm` / `--text-md` / `--text-lg` (13 / 15 / 22 px).

**Two numbers in this chapter are not tokens yet:** the 280-pixel tile width and the 120-pixel gutter between columns. See Open questions.

## Behaviour

Worked on the Hormuz map (the cast is in [`README.md`](README.md)). This chapter uses all seven base claims — H, C, B, R, M1, M2, N1 — the reflexive arrow `B → R`, and the claim **S** that the strike branch adds.

### B1 — The base map lands in four columns

Reflexive arrows are set aside before columns are assigned (B4). What is left is seven claims and seven arrows, and the minimum-total-length assignment is:

| Column | Tiles |
|---|---|
| 0 | H |
| 1 | C · N1 · R |
| 2 | B |
| 3 | M1 · M2 |

R sits in column 1, tight against B, because its only live arrow is `R → B`. Nothing pulls it further left, and network simplex does not leave a wire longer than it has to be.

The widest column holds three tiles. The cap is seven, so nothing collapses (B5).

### B2 — Opening the map frames it once

On the first layout of a map, and only then, `fitView` frames the whole thing. Every layout after that calls `setCenter` on the focused tile instead, so the tile you were reading stays under your eye.

Losing your place after a re-layout is anti-pattern 8 in `docs/research/03-ui-ux-directions.md`.

### B3 — A later tile does not reshuffle an earlier column

Every tile that already has a place is handed back to ELK carrying `elk.position`. With `crossingMinimization.semiInteractive` on, the crossing minimiser treats that as where the tile wants to sit and orders the column around it.

So when a claim arrives downstream of what is already drawn — a second market ending hanging off B, say — M1 and M2 keep their exact coordinates and the newcomer finds a gap. Nothing above it moves. This is what keeps streaming growth calm (`streaming-growth.md`, stack 04) and what keeps a branch from scrambling the map you were reading.

**Pinning holds positions inside a column. It does not hold column assignment** — see B7 and Open questions.

### B4 — The reflexive arrow is set aside, then drawn as a loop

`B → R` is the one feedback arrow on the map: a run of sub-$68 settlements pressures OPEC+ revenue and brings a restraint announcement forward, fourteen days later. Together with `R → B` it is the map's only loop.

A layered layout cannot assign columns to a graph with a loop in it. So the layout pass removes every arrow marked `reflexive` before it starts, assigns columns to what is left, and puts the reflexive arrow back for drawing. The loop is real, it is on screen, and it takes no part in deciding who sits where.

It therefore points *backwards*: B is in column 2, R is in column 1. That is correct and it is the honest shape of feedback.

Setting feedback arrows aside is not this chapter's invention. It is one rule, written once in `spec/multiverse/interventions.md` (Kent, 2026-09-17):

> *The map the engine works through is the map with feedback arrows set aside. Anything that asks **what can move** reads that map — the affected set, diff states, propagation's ordering, layering. Anything that asks **what can I walk to** reads the whole map — the hover lens, `h`/`l`, the outline.*

Layering asks what can move, so it reads the map with `B → R` removed. That is also why R comes out `untouched` on the strike branch. `test_a_feedback_arrow_never_carries_a_change` fails loudly the day stack 06 unrolls feedback arrows in time, and points at the one sentence to change. **How that wire looks — the loop, the lag chip reading "14 days" — is `tiles-ports-wires.md`.** This chapter only guarantees that the wire exists, that it never decides a column, and that removing it can never fail: INV-6 (no loops except through reflexive arrows, each with a delay greater than zero) is already enforced in the engine, so a map that reaches the canvas is one the loop check has passed.

### B5 — Seven tiles per column, then "+n more"

No column paints more than seven tiles. The eighth and beyond collapse into one **"+n more"** tile, where n is exactly how many are behind it — `+4 more` for eleven claims in a column.

Hormuz never reaches the cap; a generated map does. The rule exists because a column of eighteen tiles is a wall, and a wall is the hairball problem wearing a different hat.

**Which seven survive, and what "+n more" does** (Kent, 2026-09-17): the seven that survive are the **first seven in the layout's own within-column order** — the order ELK already produced, so nothing new has to be ranked and the answer is the same every run. Activating the "+n more" tile **opens the outline view filtered to that column** (`keyboard-and-access.md`), which is a list that already exists, already reads each claim as a sentence, and already works on the keyboard. Nothing expands in place, so the cap is never briefly broken.

**A collapsed claim's wires do not disappear.** A wire that vanishes is a state a user cannot trace, which is the second veto. The wires of the hidden claims attach to the "+n more" tile. *How they bundle is still open — see Open questions.*

### B6 — Level of detail: the tile changes representation, it does not shrink

**There is one rule, and the two thresholds are consequences of it** (Kent, 2026-09-17). The rule: **no text ever lands below 11 pixels on the glass.** There is no counter-scaling anywhere — a tile at 0.7 zoom really is drawn at 0.7, text and all — so the thresholds are arithmetic, not taste:

| Consequence | Sum | Why |
|---|---|---|
| **Summary below ≈ 0.85 zoom** | 11 ÷ 13 = 0.846… | A full tile's smallest type is `--text-sm`, 13 px. Below 0.846 that text lands under 11 px on the glass, so the tile must change representation first |
| **Silhouette below 0.5 zoom** | 11 ÷ 22 = 0.5 | A summary tile's type is `--text-lg`, 22 px. At 0.5 it lands at exactly 11 px, and there is no larger size to fall back to — so below 0.5 the tile stops drawing words at all *(added 2026-09-22; this sum used to be the floor)* |
| **Zoom floor ≈ 0.158** | 24 ÷ 152 = 0.1578… | Below the silhouette threshold there is no word left to hold above 11 px, so the next rule down decides: a tile's box must stay big enough to point at. 24 × 24 px is the smallest target anything may be drawn at — Web Content Accessibility Guidelines 2.2, success criterion 2.5.8 *Target Size (Minimum)*, level AA — and the shortest box this map draws is a tile at the floor of its clamped height, 152 px *(2026-09-22, Kent: "Can we make it so it's possible to zoom out a lot more?")* |

**This supersedes the 0.6 threshold in the plan and in decision record 0007, dated 2026-09-17.** 0.6 was a chosen number; 0.846 is a derived one, and deriving it is what makes the 11-pixel promise true rather than approximately true.

**The third row's other side comes out of it for free.** At 0.158 a tile's 280-px width lands at 44.2, clear of the 44 × 44 of the same guidelines' stricter rule (2.5.5 *Target Size*, level AAA, which Apple's interface guidelines name as well). So the smallest box on the map is 44 across and 24 down: a target in both directions, and nothing like the 1-px stroke of a wire. Measured on the replayed generated map at 1600 × 1000 and 1280 × 800 on 2026-09-22: all eighteen claims inside the stage, box 44.2 × 30.3.

Below the summary threshold a tile paints its **summary**: the claim and the three belief chips inside the same kind silhouette, nothing else. The outline never goes — it is the tile's shape, and dropping it would lose the claim's kind at exactly the zoom where you are scanning for one. Above it the tile paints in full — claim, chips, evidence clippings, resolve-by date (`tiles-ports-wires.md`).

Below the silhouette threshold the outline is **all** that is painted. No claim, no chips, no heading, no ports drawn as ink — and the plate in the middle of a wire goes too, because a plate is words. What stays: the four shapes, the hue two of them take, the arrows, the dashed outline of a rectangle held open or of a "+n more", and both rings, so a reader can still see which shape the panel is reading. The shapes are drawn with their one distinguishing mark grown to about 48 px in the map's own coordinates — 6 px on the glass at the floor — because a corner cut 18 px is under 3 px out there, and a kind told apart by hue alone is INV-12 broken.

**Why the floor moved, in one line.** The reader is at the far end of a map they made: the question out there is *what shape did my argument come out*, and the answer is the whole picture at once. The old floor was the point at which the last word became unreadable, which is the right floor for reading and the wrong one for looking.

**The honest cost.** Measured on the Hormuz map: on a 1440-pixel-wide window the first frame is summary tiles, because `fitView` cannot fit the map any larger. At 1600 wide it is full tiles, at about 11.4 pixels — legible, and only just. A narrow window therefore opens on summaries and you zoom in to read. That is the price of the promise, and it is cheaper than the alternative, which is text nobody can read at a zoom the interface offered them.

UX-4 (level of detail by zoom) names three rungs. This stack builds two of them:

| UX-4 rung | What it shows | Where |
|---|---|---|
| **Near** | The full tile, with evidence | This stack — at or above 0.85 zoom |
| **Mid** | Wiring and belief chips | This stack — between 0.5 and 0.85, the summary tile |
| **Far** | Worlds and their terminal deltas | **Not this stack.** It needs several worlds side by side (FR-17, three or more branches as small multiples), which arrives later. The silhouette below 0.5 is not this rung: it is one world seen whole, not several side by side *(2026-09-22)* |

### B7 — The union of two worlds is laid out once

A diff shows the base map and the branch at the same time. Both are laid out **once, together, as one graph** — every claim in either world, every wire in either world — and then painted twice in those same coordinates. One layout, two paintings. **How they are painted is `diff-view.md`.**

The Hormuz strike branch adds **S**, a confirmed military strike on Iranian territory, with three arrows: `S → B`, `S → C`, and `S → H`. That last one points at the hypothesis itself. The union is five columns:

| Column | Tiles |
|---|---|
| 0 | S |
| 1 | H |
| 2 | C · N1 · R |
| 3 | B |
| 4 | M1 · M2 |

**Read that against B1 and notice what happened: every base claim moved one column right.** It had to. S causes H, so S must sit before H, and everything H causes shifts with it. Pinning cannot prevent this, because pinning orders tiles *inside* a column and does not decide which column a tile is in.

**Following focus is enough, and columns are not pinned** (Kent, 2026-09-17). Two reasons. The shift is a **rigid translation** — every base tile moves the same 400 pixels, so relative to any other base tile nothing has moved at all, and `setCenter` on the focused tile makes even that invisible. And pinning the columns would be worse than the shift it prevents: S would have to stay where the base map had nothing, which puts a cause to the right of its effect and breaks the one promise the layout exists to make.

One rule makes it land well: **creating a claim moves focus to it.** So the moment the strike branch is made, focus is on S and `setCenter` frames S — you are looking at the thing you just added, not hunting for it.

A claim present in both worlds has exactly one coordinate. That is the property that makes a ghost overlay readable at all: if the two worlds were laid out separately, every tile would appear to have moved and nothing would stand out.

### B8 — Tiles do not move, and the interface says so

No tile is draggable. Not "mostly", not "except the ones you pinned" — none, anywhere, in this stack.

Half-supported dragging looks broken (anti-pattern 13 in the research). Pinning, grouping and annotating arrive later as **explicit buttons**, not as free drag.

Nobody should have to discover this by failing, so the shortcuts sheet says it out loud. That line is written in `keyboard-and-access.md`, which owns the sheet.

### B9 — Sixty tiles in under 100 milliseconds

NFR-7 (performance: sixty tiles render and re-layout in under 100 milliseconds on a laptop) is measured, not assumed. The worker returns `elapsedMs` on every layout, and INV-workbench.30 fails if a sixty-tile map crosses the budget.

**What the budget covers is not settled.** `elapsedMs` is ELK's own time and nothing else; NFR-7's words are "render and re-layout", which is ELK plus React Flow's paint. And decision record 0007 already puts ELK alone at up to 150 milliseconds on sixty tiles — over the budget before a single pixel is drawn. So the test may land as a **known-red pin** that records the real figure rather than as a passing check. Which of the two the budget means, and what to do when it is missed, is under Open questions.

## INVARIANTS

Each is *for all X, statement P holds*, and each names what checks it. "Visual review checklist line *n*" is line *n* of the visual review checklist in [`README.md`](README.md) — a checklist line is a checkable thing; it is checked by a person.

| ID | Statement | Checked by |
|---|---|---|
| **INV-workbench.20** | For every layout call, the options passed to ELK are exactly the five in `ELK_OPTIONS` and no others; `elk.position` is set per tile and nowhere else | `test_layout_options_are_the_five_named` in `frontend/src/graph/__tests__/layout.test.ts` |
| **INV-workbench.21** | For every module under `frontend/src/`, `elkjs` is imported by the worker file and by nothing else — layout never runs on the thread that draws | `test_elk_is_imported_only_by_the_worker` in `layout.test.ts` |
| **INV-workbench.22** | For every map and every claim added strictly downstream of the tiles already placed, every already-placed tile's coordinates are identical before and after | `test_pinned_tiles_keep_their_positions` in `layout.test.ts` |
| **INV-workbench.23** | For every map and every re-layout of it, no already-placed tile changes its order within its column | `test_within_layer_order_is_stable` in `layout.test.ts` |
| **INV-workbench.24** | For every base map and branch, layout runs once over their union, and every claim present in both worlds has exactly one coordinate | `test_union_layout_is_stable` in `layout.test.ts` |
| **INV-workbench.25** | For every map opened, `fitView` is called exactly once; every later layout calls `setCenter` on the focused tile and the focused tile stays in the viewport; and every newly created claim takes focus | `test_fit_view_runs_once_then_set_center` in `layout.test.ts`; `frontend/e2e/hormuz.spec.ts` |
| **INV-workbench.26** | For every map, no column paints more than seven tiles; where one would, the first seven in the layout's within-column order are painted and the rest sit behind a single "+n more" tile whose n equals the number hidden | `test_layer_cap_collapses_the_rest` in `layout.test.ts`; visual review checklist line 6 (is the map layered left to right, or a hairball?) |
| **INV-workbench.27** | **At every zoom at which a word is drawn at all**, the smallest rendered type size × the zoom is at least 11 — below ≈0.85 because the tile has switched to its summary, above it because 13 × 0.85 already clears 11, and below 0.5 because no word is drawn there at all *(reworded 2026-09-22, when the floor moved below the zoom at which the last word leaves)* | `test_no_text_lands_under_eleven_pixels_at_any_zoom` and `test_no_word_is_drawn_below_the_silhouette_threshold` in `layout.test.ts`, two sweeps covering the whole zoom range between them; `test_a_tile_at_the_furthest_zoom_draws_its_shape_and_not_one_word` in `components/__tests__/tile.test.tsx`; `e2e/zoomedOut.spec.ts`; visual review checklist line 7 (is any text below 11 pixels?) |
| **INV-workbench.31** | For every zoom the map allows, every tile's box is at least 24 pixels on its shortest side — which is what makes the floor a derived number rather than a chosen one, and what makes a tile at the floor something a pointer can land on | `test_the_zoom_floor_is_worked_out_and_not_written_down` in `layout.test.ts` |
| **INV-workbench.28** | For every tile in every state, `draggable` is false | `test_no_tile_is_draggable` in `layout.test.ts` |
| **INV-workbench.29** | For every map, column assignment is computed on the graph with reflexive arrows removed, and every reflexive arrow is still drawn | `test_reflexive_links_are_set_aside_for_layering` in `layout.test.ts` |
| **INV-workbench.30** | For every map of sixty tiles, the worker's `elapsedMs` is under 100 milliseconds (NFR-7) — see B9 on what the budget covers | `test_sixty_tiles_lay_out_under_100ms` in `layout.test.ts` |

## ANTI-PATTERNS

1. **Do not run ELK on the main thread**, because a 150-millisecond freeze eats keystrokes and stutters the scroll, and the user reads that as a slow product rather than as a busy layout. Post to the worker and render the previous coordinates until the new ones arrive.
2. **Do not call `fitView` after every layout**, because the map jumps to a new framing each time and the user loses the tile they were reading. Frame once on open; `setCenter` on the focused tile thereafter.
3. **Do not let text land under 11 pixels on the glass**, because an unreadable label is worse than no label. Switch the tile to its summary at 0.85, drop its words altogether at 0.5, and stop the zoom where a tile's box stops being a target — and do not counter-scale the text to dodge the rule, because a tile whose contents ignore the zoom stops being a picture of the map.
4. **Do not make tiles "a bit" draggable**, because a tile that moves and then snaps back reads as a bug. Offer no drag at all and say so in the shortcuts sheet.
5. **Do not hide a wire when its tile collapses into "+n more"**, because a wire that vanishes is a state nobody can trace — the second veto. Attach it to the "+n more" tile.
6. **Do not feed reflexive arrows into the layering pass**, because a layered algorithm has no answer for a loop and will either fail or invent an order. Remove them, assign columns, put them back for drawing.
7. **Do not re-layout on hover or selection**, because nothing about the graph changed and the map should be still while you read it. Hover dims; selection opens the Inspector; neither moves a tile.
8. **Do not lay out two worlds separately and overlay them**, because every tile will appear to have moved and the diff will say nothing. Lay out the union once and paint it twice.

## Open questions

*Dated 2026-09-17. Each is something the plan does not settle; none is decided here.*

1. **How do a collapsed claim's wires bundle?** One thick wire to the "+n more" tile with a count on it, or n thin wires all landing on the same socket? The first is legible; the second is literal. The chapter requires only that no wire disappears. *(Which seven survive, and what activating "+n more" does, were* **Decided 2026-09-17** *— both are in B5.)*
2. **Should 280 and 120 become tokens?** Every other pixel number in the product lives in `frontend/src/styles/tokens.css`. The tile width and the column gutter currently would not. Adding them touches a file this stack's wire agent owns (the new colour block), so it is a coordination question, not a design one.
3. **Does UX-4's "far" rung need its own zoom threshold?** This stack has a floor, one threshold and two renderings. When several worlds appear side by side, "far" will need a third number — and probably a different interaction altogether, since at that scale you are choosing a world rather than reading a map.
4. **What does NFR-7's 100 milliseconds actually cover, and what happens when it is missed?** "Render and re-layout" reads as ELK plus paint; `elapsedMs` measures ELK alone. Decision record 0007 already puts ELK alone at up to 150 milliseconds on sixty tiles, so on the pessimistic reading the budget is missed before anything is drawn. Either the invariant measures `elapsedMs` and the budget is a layout budget, or it measures both and the number needs revisiting. Until Kent says, INV-workbench.30 measures `elapsedMs` and the test records the real figure so the gap is visible rather than hidden.

**Decided 2026-09-17 and now in the body:** which seven tiles survive the cap and what "+n more" opens (B5) · the two zoom numbers and the removal of counter-scaling (B6) · whether following focus is enough when the union layout shifts every column, and the rule that creating a claim moves focus to it (B7) · the minimum zoom, which was 0.5 and fell out of the 11-pixel rule (B6). **Amended 2026-09-22:** 0.5 is now the zoom at which the last word leaves a tile, and the minimum zoom is ≈0.158, which falls out of the 24-pixel minimum target size (B6).
