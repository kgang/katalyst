---
# ADR-0024: A tile moves only when an arrow would otherwise point backwards, and once when the run stops
status: proposed
date: 2026-09-21
decision-makers: Kent Gang
consulted: Kent's own walk of the app with his model key, 2026-09-21 (`plans/notes/2026-09-21-kent-m4-feedback.md`); analyst UB's measurement of three real streams through the app's own layout code (`plans/ux-round/B-layout.md`, scripts under `plans/analysis/scripts/ux-round/B/`); the red team's re-run of those measurements (`plans/ux-round/RT-red-team.md`, items 1 and 2 of *what must change*, and its question 4 to Kent); ADR-0007 (the canvas and its layered layout)
informed: agents working in `frontend/src/graph/` — `layoutRunner.ts`, `elkGraph.ts`, `layers.ts`, `Canvas.tsx`, `geometry.ts` — and in `frontend/e2e/`
supersedes: none
superseded-by: none
spec-impact: spec/workbench/streaming-growth.md (B3 rewritten, INV-workbench.64 rewritten, .79 given a dated clause, anti-pattern 7 rewritten, anti-pattern 12 reworded, open question 2 reopened and answered); spec/workbench/layout-and-zoom.md (B3, INV-workbench.22 and .23); spec/workbench/README.md visual review checklist VR13; ARCHITECTURE.md §1 and §10 — and spec/workbench/diff-view.md INV-workbench.40 explicitly untouched
---

# ADR-0024: When a tile may move

## Context and Problem Statement

Kent typed the Hormuz and Brent example into the **Verify** door — a live run with his own key, naming *Brent crude settles below $68* as the destination — and said: *"the boxes are a little chaotic and hard to read. Can we apply a heuristic to allow the graph/nodes to be redrawn so that it avoid arrows that loop back around? as much as possible, it should be oriented to be legible left to right and top to bottom."*

He was looking at a real defect, and it has one cause.

**A claim's column is frozen the moment it is first drawn, and a claim can only move right as later arrows arrive — so the pin holds it left of where it belongs and the arrow into it doubles back.** Measured by analyst UB on 2026-09-21, by bundling the app's **own** `elkGraph.ts`, `layers.ts` and `geometry.ts` and feeding three real streams through them; nothing was reimplemented, and the red team re-ran the same scripts the same day.

* `assignLayers` (`frontend/src/graph/layers.ts`) puts a claim one column right of the furthest-right claim pointing at it. That is **depth, not arrival order** — the brief's arrival-order hypothesis was measured false.
* `readPositions` (`frontend/src/graph/elkGraph.ts`) says in its own words: *a tile that had a position keeps that position, to the pixel*. The pin holds **x as well as y**. The layout engine re-lays the map out correctly underneath, and we put every placed tile back where it was.
* `pinsFor` (same file) drops the pins only when a box changes height. Measured: **zero pin drops in 25, 14 and 12 layout passes** across the three runs. A tile reserves its belief rail from the first frame (`BELIEF_RAIL = 69` in `frontend/src/graph/geometry.ts`), so when the likelihoods land and every chip fills, no tile changes height and no pin is dropped. INV-workbench.64's note that *every tile gains a chip and so every tile can change height* does not describe what happens: the whole run is one unbroken chain of pins.

**The Verify door makes it acute.** The destination claim arrives second, with **no incoming arrows at all** — nothing points at it yet — so it lands in column 0 beside the hypothesis and is pinned there. On one of Kent's kept live runs it ends in column **3**, with four arrows into it — three of them from claims placed to its right, which is where that run's three backwards arrows come from, and one from a claim in its own column.

| Map | As drawn today | Backwards arrows | Wire length | Height |
|---|---|---|---|---|
| The committed recording — 18 claims, Explore | incremental, pinned | **none** | 11 264 px | 2 640 px |
| Kent's live Verify run `18-24-54Z` — 6 claims | incremental, pinned | **3 of 9** | 5 729 px | 824 px |
| Kent's live Verify run `18-31-02Z` — 4 claims | incremental, pinned | **2 of 5** | 2 930 px | 824 px |

*(Analyst UB, 2026-09-21. "Backwards" means the target sits strictly left of the source. The feedback rule is not involved: `reflexive` is false on every arrow in all three streams, and a proposal has no `reflexive` field to set — every backwards arrow is an ordinary one.)*

**Why nobody had seen it.** `spec/workbench/streaming-growth.md` open question 2 — *"Does the map re-lay out once when the run finishes? Answered 2026-09-21: no"* — was measured on a **ten-claim Explore run**, where no arrow points backwards, so the thing a re-layout would have tidied did not happen. The Verify door has no end-to-end test, and every end-to-end test plays the committed recording, which is an Explore run. The answer was true of the map it was measured on and false of the map Kent typed.

**And the promise it collides with is the loudest one this part makes:** *nothing already placed moves* (INV-workbench.64), *a placed tile never moves* as the visual checklist says it (VR13). That promise is what makes a growing map feel like it is arriving rather than reshuffling, and it is the reason the pin is absolute in the first place.

So: **may a tile that is already on screen move, and if so, when?**

## Decision Drivers

* **An arrow that points backwards is a picture of an argument running the wrong way.** The whole point of the layered layout is that cause-before-effect is a fact of the picture rather than a hope.
* **Losing your place is the worse failure.** `layout-and-zoom.md` exists to prevent a map rearranging under the reader's eye; the whole chapter's purpose is that the tile you were reading stays where your eye left it.
* **Whatever is chosen must be one rule, not a heuristic.** Kent's word was *heuristic*; a heuristic is a thing that is right most of the time and cannot be stated. A rule can be tested.
* **It must not be a fourth animation.** The motion budget is three (INV-workbench.18, .73).
* **It must be measurable on evidence the repository holds.** The defect exists only on a live Verify map, and `backend/.runs/` is git-ignored, so the measurement above rests on two files no fresh clone has.
* **The diff view must not be disturbed.** *Nothing re-positions when you toggle between two worlds* (INV-workbench.40) is a different promise, resting on the union being laid out once, and the branch panel and the dock rely on it.

## Considered Options

The first three were put to Kent on 2026-09-21, with the measurements beside them.

* **L1 — keep the row, take the column from the layering on every pass.** *This is Kent's request at full strength: no arrow points backwards at any moment, during the run or after it.* A tile's vertical place is pinned exactly as today; its column is re-read from the arrows each time the map grows. When a later arrow proves a claim belongs further right, the claim goes there.
* **L2 — the map settles once, when the run stops.** Nothing moves while the map grows, exactly as today. Whatever takes the run past *growing* — the likelihoods landing, a break, a stream that ends early — clears the pins and lays the map out once, whole, at the same moment the canvas already re-frames it.
* **L3 — do not draw the Verify destination until an arrow reaches it.** The cheapest fix: the claim exists, and no box is drawn for it until something points at it.
* **L4 — leave it.** The map Kent saw is the map a reviewer sees.
* **L1 + L2 — both.**

### What each one costs, measured

Analyst UB ran all four policies over the same three streams through the app's own layout code, 2026-09-21. A *tile-move* is one tile changing place on one arrival; *arrivals* is how many of the run's events moved anything at all.

| Policy | Tile-moves (recording / `18-24-54Z` / `18-31-02Z`) | On how many arrivals | Furthest single move | Backwards arrows left |
|---|---|---|---|---|
| Today | 0 / 0 / 0 | 0 | — | 3 · 2, and one same-column on each |
| **L2 — settle once at the end** | 18 / 4 / 4 | **1** | 1 968 px | 0 |
| **L1 — keep the row, free the column** | 44 / 5 / 3 | 14 / 3 / 2 | 800 px | 0 |
| Never pin anything | 159 / 45 / 25 | 18 / 10 / 7 | 1 066 px | 0 |

**The red team's correction, and it is the one that decided this.** The analysis argued L1 down on its headline figure of *"44 tile-moves across 14 arrivals"* — but that figure is the **eighteen-claim Explore recording, the map Kent did not complain about.** Re-run and split by map (`plans/ux-round/RT-red-team.md`, item 2, 2026-09-21): on the two Verify runs he actually typed, L1 costs **5 tile-moves across 3 arrivals** and **3 across 2**. On the maps where the defect exists, the cure is nearly free.

One whole layout at the end also shortens the picture a great deal: wire length **11 264 → 5 567 px** on the recording, **5 729 → 2 973** and **2 930 → 1 773** on the two Verify runs; height **2 640 → 2 010**, **824 → 491** and **824 → 298**. L1 on its own does not do that — on the recording it ends **longer**, 7 853 px of wire against the 5 567 one whole layout gives, because a column freed one arrival at a time settles into a worse arrangement than one worked out all at once.

## Decision Outcome

Chosen option: **"L1 + L2 — both"**, because L1 alone leaves the finished picture longer than it needs to be, L2 alone leaves the map wrong for the ten minutes a reader is actually watching it, and together they cost, on the maps where the defect exists, five tile-moves and one settle.

**Kent's decision, 2026-09-21 (R37):** *"Both: during the run and once at the end."*

### The promise, rewritten

The old promise, in the three places it is written — INV-workbench.64 (*nothing already placed moves*), the visual review checklist VR13 (*no tile that was already placed moved when a later one arrived*), and `readPositions`' own comment (*a tile that had a position keeps that position, to the pixel*) — becomes:

> **A tile moves only when an arrow would otherwise point backwards, and once when the run stops.**

In full, as three clauses a test can hold:

1. **A tile keeps its row.** Its vertical place, and its order within its column, are pinned from the moment it is first drawn and are never taken from it while the map grows. This is INV-workbench.23 and it is unchanged — it is now the half of the pin that does all the work.
2. **A tile's column is re-read from the arrows on every pass.** When a later arrow proves a claim belongs further right, the claim goes there, on that arrival, rather than staying put and being drawn with an arrow doubling back into it. **No arrow points backwards at any moment**, except a feedback arrow, which is set aside before columns are assigned and is *meant* to point backwards.
3. **The map settles once, when the run stops.** Whatever takes the run past *growing* — the likelihoods landing, a break, a stream that ends early — clears every pin and lays the map out once, whole, and it never moves again. **This is the one moment a tile may change row**, and it is why clause 1 is scoped to the growing map: on the eighteen-claim recording the settle takes the map's height from 2 640 to 2 010 pixels, which no rule holding every row could allow.

### The settle happens at a moment that already exists

This is not a new event and not a new frame. `GenerationScreen.tsx` already passes `frameAgainOn={finished ? "the run stopped" : undefined}`, `Canvas.tsx` already re-frames the whole map at that moment, and there is already a browser assertion for it (*the map is framed once more when it stops*). `layoutRunner.ts` already clears the pins and re-lays the map out when the map key changes. The settle is that same flag dropping the pins as well — so the settle and the re-frame are **one moment and cannot come apart.** Every tile takes its new place in the same frame the chips fill.

**It is a cut, not an animation.** Tiles are in their new places in one frame, under the opacity change already budgeted for everything else. No fourth animation; under reduced motion it is already a hard cut. INV-workbench.18 and .73 are untouched.

**The focused tile keeps the screen.** Every layout after the first calls `setCenter` on the focused tile (INV-workbench.25), which is what makes one moment where eighteen tiles move bearable: the tile the reader is on does not go anywhere on the glass.

### What is explicitly untouched, and why it matters

* **The diff view's promise stands, word for word.** *Nothing re-positions when a branch is opened*: the union of the base map and the branch is laid out **once**, together, and painted twice in those same coordinates, so toggling between the two worlds changes no position anywhere (INV-workbench.40; `layout-and-zoom.md` B7). Opening a branch already drops every pin and lays out a different map — that has always been true, it is not what this record changes, and the branch panel, the delta rail and the ghost overlay can go on relying on it exactly as they do today.
* **INV-workbench.22 stands.** It is about *a claim added strictly downstream of the tiles already placed* — the case where no earlier claim's column can change. It remains true, and it remains the thing the layout machinery guarantees.
* **INV-workbench.23 stands**, and is now load-bearing: keeping the row **is** keeping the order within the column.
* **INV-workbench.79 stands in substance** — a box is drawn where the layout put it and at no other place, and a reserved rectangle goes on standing until the claim it held a place for is drawn. A tile taking a new column is a **new place the layout gave it**, not a place the map invented; anti-pattern 12 (*do not give a box a place because the layout has not answered yet*) is unchanged.
* **The feedback arrow keeps its exemption.** Reflexive arrows are removed before columns are assigned and put back for drawing, so `B → R` points backwards and is supposed to. No generated map has one yet, because a proposal has no `reflexive` field.
* **The zoom-button and panel-edge framing faults are not this record's.** They were measured the same day and handed on: they are one 16-pixel margin in `Canvas.tsx` and `geometry.ts`, and they belong to whoever owns the stage.

### The honest cost

* **A reader will see tiles move.** On the two Verify runs, five moves and three moves; on the eighteen-claim recording, forty-four across fourteen arrivals. The furthest single move during a run is 800 pixels. That is a real cost against the promise that made the growing map calm, and it is paid on purpose, because an arrow pointing the wrong way is a lie about the argument and a tile sliding right is not.
* **One moment where everything moves.** At the settle, every tile takes a new place — on the recording, 18 of 18, the furthest 1 968 pixels. `setCenter` on the focused tile is what keeps that from being disorienting.
* **Shorter is not always fewer crossings.** Measured on the same three maps: laying the eighteen-claim recording out whole takes its wire crossings from **2 to 5** while halving its wire and cutting 630 pixels of height; on the two Verify runs crossings fall, 8 → 2 and 2 → 1. The layout minimises total arrow length, not crossings, so a map that is much shorter can cross itself slightly more. That is the trade, said out loud rather than discovered later.
* **The pinned evidence is thin.** The defect exists only on a live Verify map. The one stream committed to this repository is an Explore run with zero backwards arrows, and `backend/.runs/` is git-ignored — so on the repository's own evidence the defect is invisible, and `test_no_arrow_points_backwards_at_any_moment` cannot be written as the analysis first specified. One kept live Verify run should be committed as a test fixture (the events only, a few kilobytes, from a run already paid for on 2026-09-21). It is not a launchpad recording, nothing replays it to a reader, and it costs nothing — R9 forbids making new recordings, not committing an old run as an input to a test. **If Kent would rather not, the test falls back to a hand-built map of the same shape, which proves the rule and not the case.**

### Consequences

* Good, because no arrow on any map points backwards at any moment, which is what Kent asked for and what the layered layout was chosen for.
* Good, because the finished picture is half the wire and, on the Verify runs, a third to two-thirds of the height it is today.
* Good, because the settle rides a moment that already exists and is already asserted, so there is no second layout policy and no new event.
* Good, because it is one rule with three clauses rather than the heuristic that was asked for, so it can be tested rather than reviewed.
* Bad, because tiles now move while a reader watches, on the screen whose promise was that they never do — five moves on the run Kent typed, forty-four on the longest committed one.
* Bad, because one moment near the end moves every tile at once, and the furthest travels nearly two thousand pixels.
* Bad, because the evidence rests on two files the repository does not hold, until a live Verify run is committed as a fixture.
* Neutral, because none of it touches the server, a fixture, a prompt or a recording, so R5's one shape freeze is untouched.

### Confirmation

* `test_no_arrow_points_backwards_at_any_moment` — no browser: replays a live Verify stream and the committed recording through the real `assignLayers`, `toElkGraph` and `readPositions`, and asserts that after **every** event, every non-feedback arrow's target sits strictly right of its source. It fails on `main` today, three times on one run and twice on the other.
* `test_no_arrow_points_backwards_once_the_run_has_stopped` — the same statement taken after the settle.
* `test_a_tile_keeps_its_row_while_the_map_grows` — the other half of the rule, and the one that stops this becoming *never pin anything*.
* `test_nothing_moves_except_a_column_until_the_run_stops` — the existing growth test split at the settle.
* `frontend/e2e/generate.spec.ts` and `frontend/e2e/lateLayout.spec.ts` both read the first tile's place **after** the run has stopped and assert it has not moved. Both must take that reading **earlier**, or they fail by design — and that, not a bug, is what will make them fail.
* Visual review checklist **VR13**, reworded, checked on a picture of a live Verify run rather than of a replay.
* ADR-0008 tier 2 applies: this is timing-sensitive code, so a no-browser test that injects the bad timing is required alongside one cold browser run and the build.

## Pros and Cons of the Options

### L1. Keep the row, free the column every pass (Kent's request at full strength)

* Good, because no arrow points backwards at any moment — during the run, which is when a reader is actually reading it, as well as at the end.
* Good, because it is cheap exactly where the problem is: 5 tile-moves across 3 arrivals and 3 across 2 on the two Verify runs.
* Good, because a tile never changes row, so the reader's vertical scan of the map is undisturbed and `setCenter` keeps the focused tile still.
* Bad, because on a long Explore run it is 44 moves across 14 arrivals, which is movement on a screen that promised none.
* Bad, because on its own it ends with a **longer** map than one whole layout gives — 7 853 px of wire against 5 567 — since a column freed one arrival at a time settles worse than one worked out all at once.

### L2. The map settles once, when the run stops

* Good, because nothing moves while the map grows, so the growing map's promise survives word for word.
* Good, because it is the tidiest finished picture: zero backwards arrows, zero same-column arrows, and the wire halved.
* Good, because the path and the moment both already exist in the code, and the moment is already asserted by a browser test.
* Bad, because for the ten minutes a live run takes — which is all the time the reader spends watching — the destination still sits in column 0 with arrows doubling back into it. It fixes the picture after the reader has finished forming an opinion of it.
* Bad, because it costs one moment where every tile moves, the furthest by 1 968 pixels.

### L3. Do not draw the Verify destination until an arrow reaches it

* Good, because it is the cheapest of all and kills every backwards arrow on both live runs.
* Bad, because it invents a rule about which claim is a destination, which is a heuristic and not a rule about the map.
* Bad, because it leaves the recording's doubled wire and 630 pixels of dead height untouched.
* Bad, because a rectangle standing where a claim already exists breaks INV-workbench.79 outright.

### L4. Leave it

* Good, because nothing moves and nothing is spent.
* Bad, because the map Kent saw is the map a reviewer sees, and three of nine arrows on it point the wrong way.

### Never pin anything

* Good, because it is the simplest thing that could possibly work.
* Bad, because it was measured at 159 tile-moves on the recording, across every one of its arrivals. It is the hairball problem wearing a different hat.

## More Information

* **Kent's decision, 2026-09-21 (R37)**, taken with the question tool: *both — during the run and once at the end.* Recorded in `plans/notes/2026-09-21-decisions-after-review.md`, row R37, with his original words in `plans/notes/2026-09-21-kent-m4-feedback.md`.
* **The measurement:** `plans/ux-round/B-layout.md` (analyst UB, 2026-09-21) — §1 for the mechanism with file and line for each step and the three-map table, §2 for the candidates, §3 for the amendment each decision needs. Scripts under `plans/analysis/scripts/ux-round/B/`, which bundle the app's own layout modules rather than reimplementing them.
* **The correction that changed the answer:** `plans/ux-round/RT-red-team.md`, 2026-09-21 — item 2 of *what must change* (the analysis argued Kent's own option down using the one map where the problem does not occur; split by map it costs 5 and 3 moves), item 1 of the same list (the evidence files are git-ignored), and **question 4** of its five questions to Kent (may one live Verify run be committed as a test fixture).
* **ADR-0007** — React Flow with the layered layout, `semiInteractive` crossing minimisation, and already-placed tiles pinned by `elk.position` so a newly streamed tile never reshuffles an existing layer. This record is the dated amendment to that last clause: the pin holds the row, not the column. *(Turning `semiInteractive` off was measured and changes nothing on any of the three maps — the options are not the problem; the pin is.)*
* **ADR-0008**, amended 2026-09-21 — three tiers of browser testing; this is tier 2.
* `spec/workbench/streaming-growth.md` B3, INV-workbench.64, anti-pattern 7, open question 2 · `spec/workbench/layout-and-zoom.md` B3, B7, INV-workbench.22, .23, .25 · `spec/workbench/diff-view.md` INV-workbench.40 (untouched) · `spec/workbench/README.md` visual review checklist VR13.
