# Colour, motion and type — one channel per meaning

## Purpose

A map with seven claims and eight arrows carries six kinds of information at once, and before this chapter a reader had to click something to learn any of them. After it the picture itself is readable: brightness says how likely a claim is, hue with a glyph and a sign says which way the money moves, a hatch says a tail is involved, the stroke says what kind of push an arrow is, a mark at the arrow's tail says how much is behind it, and a lane colour with a name chip says which branch you are in.

**The organising rule is one channel per meaning.** A *channel* is one thing the eye can vary on its own — brightness, hue, texture, stroke pattern, stroke width, shape, position. Six meanings, six channels, and no channel doing two jobs. Every failure in this area is two meanings fighting over one channel: a wire that is dot-dash for one reason and dashed for another says neither; a tile dimmed because it is unlikely cannot also be dimmed because it belongs to the old world. The test before adding anything: *if I change this meaning, what on screen changes?* If the answer names a channel something else already uses, stop and find another channel — or decide which of the two meanings loses.

This chapter states the law. [`tiles-ports-wires.md`](tiles-ports-wires.md) draws it on a tile and a wire, [`diff-view.md`](diff-view.md) draws it across two worlds, [`layout-and-zoom.md`](layout-and-zoom.md) says what survives when you zoom out, and [`keyboard-and-access.md`](keyboard-and-access.md) says what a reader who is not looking at any of it hears instead.

---

## Data model

For an interface chapter the data model is the tokens. A **token** is one of the named values in `frontend/src/styles/tokens.css` — `--dir-up`, `--text-sm`, `--duration-fast` — which every component reads and which no component is allowed to replace with a raw colour, a raw pixel size or a raw duration of its own.

### The colour law, in one table

| Meaning | Channel | Tokens | The redundant cue, which is never colour | In greyscale |
|---|---|---|---|---|
| **How likely a claim is** | Brightness — a five-step neutral ramp | `--p-0` … `--p-4` *(new in this stack)* | The number itself, at two significant figures with its range | Brightness *is* greyscale |
| **Direction of financial effect** | Hue: blue up, amber down | `--dir-up`, `--dir-down` | A glyph (▲ / ▼) **and** a sign **and** a word — all three, always | The glyph and the sign |
| **Tail risk** — a rare outcome big enough to matter | Texture: a diagonal hatch | `--tail` | The word *tail* beside it | The hatch |
| **What kind of push an arrow is** | Stroke: pattern, width, doubling | none; the stroke takes `--text-muted` | The Inspector's words, and the midpoint chip's | Pattern, width and doubling |
| **Where an arrow came from** | **A mark at the wire's tail**, not a stroke | none | One, two or three dots, with the exact word in the Inspector | The count of dots |
| **Which branch you are in** | Its own small palette, on lanes and chips only | `--branch-violet`, `--branch-teal`, `--branch-rose`, `--branch-slate` *(new)* | A name chip carrying the branch's label | The name chip |

Two rules hold the table together, and both are absolute.

- **Never red and green.** Blue and amber instead. Red-green fails the most common form of colour blindness, and red and green carry loss-and-gain baggage that is wrong half the time — a falling oil price is good news for an airline.
- **Never hue alone.** This is INV-12, the product-level rule that no information is carried by colour by itself: every direction has a glyph, every tail a texture, every provenance a mark.

### Why provenance left the stroke

**Provenance** is where an arrow and its number came from — a receipt our own pipeline writes, never something the model claims about itself. Seven values: `documented`, `historical`, `market_implied`, `argued`, `user`, `asserted`, `simulated`.

It used to ride the wire's stroke. It cannot any more, because the stroke is fully spent. The stroke says what **kind of push** an arrow is — dot-dash for a spike that fades, solid for a switch that holds, a gradient for one that builds — and that job was given to it when the link's data model was written in `spec/graph/link.md`. A wire cannot be dot-dash because it is an `impulse` and dashed because it is `argued` at the same time; it would be neither, legibly.

So provenance moves to **a three-step mark at the wire's tail**, where the arrow leaves its cause: three dots for an arrow with something fetched behind it, two for a stated mechanism, one for a bare assertion. Three steps, because the useful question at a glance is *is there a document behind this, or is it the model talking* — and the seven-way distinction, which nobody reads off a picture anyway, lives in the Inspector where there is room for the word. [`tiles-ports-wires.md`](tiles-ports-wires.md) specifies the mark and the single component that draws it.

**This wording refines two things already written, and the same pull request amends them rather than quietly diverging.** `PRODUCT_REQUIREMENTS.md` UX-6 used to say "provenance → stroke style (`asserted` dashed)", its INV-12 row said "every provenance a stroke style", and `spec/workbench/README.md`'s INV-12 row repeated that wording. All three now say **a mark**, changed together with this chapter. The substance is unchanged: provenance is still visible on every wire, and still without colour.

### The likelihood ramp — `--p-0` … `--p-4`

Five steps of a **neutral** luminance ramp — five brightnesses of the same grey-blue as the surface. Neutral, because any hue in it would be a second voice in the hue channel, and hue belongs to direction.

| Token | The likelihood it paints |
|---|---|
| `--p-0` | 0 to under .2 |
| `--p-1` | .2 to under .4 |
| `--p-2` | .4 to under .6 |
| `--p-3` | .6 to under .8 |
| `--p-4` | .8 to 1 |

It is drawn in exactly two places: the fill of the small bar inside a belief chip, and the fill of the midpoint chip's bar once the engine can supply one. Nowhere else. Three rules on it:

1. **It never carries text.** A number is always drawn in `--text`, so it always clears 4.5 to 1. The ramp paints a bar, which is a meaningful graphic and needs 3 to 1. Each token carries its measured ratio in a comment, as every existing token does.
2. **It never paints a whole tile.** Tile-wide brightness and opacity are already spent: [`diff-view.md`](diff-view.md) paints the old world faint and desaturates a killed claim, and the hover lens dims everything off the path. Three meanings on one channel means none of them reads.
3. **Five steps are a glance, never a reading.** The bar sits behind the chip's number line, and the exact number and its range are printed every time, so nobody is ever asked to tell `--p-2` from `--p-3` by eye.

### Direction — and what is *not* direction

`--dir-up` and `--dir-down` mean exactly one thing: **which way the money moves.** They are drawn by exactly one component, `frontend/src/components/DirectionReadout.tsx` (*proposed here*), so that the glyph, the sign and the word can never be dropped by a component that only wanted the colour.

The trap, and it is a live one on this map: **the sign of a push is not a direction of financial effect.** The arrow from *the strait reopens* to *Brent crude settles below $68* is `+1.6` — positive, because it makes that claim come out **true** more often — and the thing the claim describes is a **falling** price. Colour that arrow amber and you have said the opposite of what it means. A push's sign is carried by its printed sign and by a word (*toward* or *against*), never by a direction hue. The words are in [`tiles-ports-wires.md`](tiles-ports-wires.md).

In this stack the direction channel has almost nothing to paint: there is no thesis card, no world-state strip, no live price, and the delta rail's `.61 → .18 ▼` needs the engine — as do its two columns, which read **how firm** and **same direction** on screen. The law is written now anyway, so that two unused tokens cannot be quietly borrowed for something else in the meantime.

### Tail risk — defined, and deliberately unused here

`--tail` is a diagonal hatch, already in `tokens.css`. A texture survives every form of colour blindness, survives a greyscale screenshot, and survives inverting dark and light.

**Nothing in this stack marks a tail,** and that is not an oversight. Being a tail means *unlikely, and large enough to matter* — and deciding that is arithmetic, which this stack does none of. The Hormuz map has a claim the fixture's own comments call the tail (*OPEC+ announces output restraint*), and the canvas still may not draw a hatch on it, because no field on the map says so. When a later stack computes it, the marking is `--tail` and no hue.

### Branch identity

Four hues, used **only** on a branch's lane and its chips and never on a tile's meaning: **violet, teal, rose, slate.** Proposed token names `--branch-violet`, `--branch-teal`, `--branch-rose`, `--branch-slate` (*proposed here* — the hues are settled, the names are not).

**Not amber.** Amber already means "the money moves down", and one hue cannot mean two things. Every branch also carries a **name chip** with its label, so a branch is readable with no colour at all.

### The motion budget

Three animations, and no more.

| # | The move | What it does | Duration |
|---|---|---|---|
| 1 | **Propagation wave** | Wires draw in causal order, so the eye follows the chain the way the argument runs | about 200 ms each, staggered 60 ms down the map |
| 2 | **Branch creation** | The new lane's colour and name chip arrive, once, with no bounce | about 200 ms *(proposed here)* |
| 3 | **Belief number-roll** | A likelihood that changed rolls from the old figure to the new one | about 200 ms *(proposed here)* |

Everything else is **an opacity change of at most 120 milliseconds** — `--duration-fast`, which already exists. Nothing scales, bounces, springs, loops or idles. Motion here communicates causality and provenance; it is never decoration, and never a way of making a finance tool feel alive.

Two new duration tokens, *proposed here*, since `tokens.css` carries only `--duration-fast`:

```css
--duration-wave: 200ms;    /* one wire drawing itself */
--duration-stagger: 60ms;  /* the gap from one layer to the next */
```

**Under reduced motion the ordering survives and the tweening goes.** *Tweening* is the in-between frames that make a change look like a movement. When the operating system asks for less movement (`prefers-reduced-motion: reduce`), `--duration-fast` and `--duration-wave` go to `0ms` and **`--duration-stagger` stays at 60 ms**. The wave becomes instant per-layer reveals, still in causal order; the number-roll becomes a swap; a ghost transition becomes a hard cut. The ordering *is* the causality, and removing it would remove the one thing the animation was for.

**Never crossfade a diff**, with or without reduced motion. The A ⇄ A′ toggle is a hard switch. A crossfade shows frames in which every number is a blend of two worlds, and no such world exists.

### Typography

| Rule | Token | Value |
|---|---|---|
| One interface face | `--font-interface` | Inter |
| One monospace face for **every** number, with fixed-width digits | `--font-mono` | JetBrains Mono, plus `font-variant-numeric: tabular-nums` |
| Exactly three sizes | `--text-sm` · `--text-md` · `--text-lg` | 13 · 15 · 22 px |
| Exactly three weights | `--weight-regular` · `--weight-medium` · `--weight-semibold` | 400 · 500 · 600 |
| Hierarchy | `--text`, `--text-muted`, and the eight-pixel spacing scale | colour and space, never a fourth size |

Fixed-width digits matter because a number that changes must not make the column beside it jump sideways. A fourth size is not a small addition; it is a new rule that everything afterwards has to obey.

**Nothing renders below 11 pixels.** The smallest size in the scale is 13, so the floor only comes under threat when the canvas is zoomed out — and the answer there is that a tile *changes representation* rather than shrinking. [`layout-and-zoom.md`](layout-and-zoom.md) owns that threshold.

**Contrast is at least 4.5 to 1 for every piece of text and every glyph, in both themes.** Dark ships first and light is verified; every colour token carries its measured ratio in a comment beside it. Amber has to go dark and slightly brown on a white page to clear the bar, and the glyph and the word carry the meaning either way.

---

## Behaviour

Worked on the Hormuz map (the cast is in [`README.md`](README.md)). This chapter uses H the strait reopens, C the war-risk premium falls, B Brent settles below $68, R OPEC+ announces restraint, M1 a Polymarket contract, N1 talks resume, and the branch in which Iran is struck the day after.

### B1 — reading the base map without clicking anything

The map draws. With no clicks at all a reader can tell four things:

- **H is less likely than M1.** H's chip bar is `--p-1` (`.35`), M1's is `--p-3` (`.61`), and each chip prints its owner, its number and its range on three stacked lines over that bar.
- **H → B is a strong one-time shove; C → B is a gentler standing one.** H → B is dot-dash (an `impulse`: a spike that fades) and three steps wide. C → B is solid (a `step`: switched on and held), doubled because it is a `sustain` arrow, and two steps wide.
- **Nothing on this map has a document behind it.** Every arrow's tail mark shows two dots (`argued` — a mechanism was stated, nothing was fetched), except H → N1, which shows one (`asserted` — a story rather than a mechanism).
- **No hue appears anywhere.** There is no financial direction to show yet, no tail is marked, and there is one branch. The base map is deliberately a monochrome picture.

### B2 — the greyscale test

Screenshot the canvas, convert it to greyscale, read it again. Everything in B1 still reads: brightness is brightness, a dot-dash is a dot-dash, three dots are three dots, a doubled stroke is doubled. This is line 3 of the visual review checklist and it runs on **every** screenshot, not once at the end. If anything is lost, the law has been broken somewhere, and the fix is a channel, never a darker colour.

### B3 — the strike branch gets a lane, and it is violet

Open *"Hormuz opens, then Iran is struck"*. The branch takes `--branch-violet` and a name chip carrying that label. The violet appears on the lane and on that chip and **nowhere else**: no tile is tinted violet, no wire is violet, and the claim the branch adds — S, the strike — is an ordinary tile whose *diff state*, not its branch, drives its styling. Had the palette kept research report 03's amber, a reader could not tell a branch chip from a downward move.

### B4 — the propagation wave, and the same thing under reduced motion

A branch is created. The wires redraw in causal order: the arrows out of H first, then the arrows out of C and R, then the arrows out of B — each drawing over about 200 milliseconds, each layer starting 60 milliseconds after the one before. The eye follows the argument.

Turn on reduced motion and run it again. The layers still arrive in that order, 60 milliseconds apart, and each one appears **instantly** instead of drawing. Nothing tweens and nothing is lost: a viewer who cannot take the movement still sees which claim caused which.

### B5 — the light theme

Force the light theme. Every token flips to its light value, every measured ratio still clears 4.5 to 1, and the picture says the same things: the ramp is five steps of neutral grey against white instead of against near-black, the hatch is dark-on-light instead of light-on-dark, and the dot counts do not change at all. A map that only works dark reads as a demo.

---

## INVARIANTS

Each is *for all inputs of this kind, this statement holds*, and each names what checks it. Two kinds of check appear: a **component test** under `frontend/src/**/__tests__/`, and a numbered line of the **visual review checklist** in [`README.md`](README.md) — the things the coordinator looks for on every screenshot before any of this is shown to anyone. A checklist line is a checkable thing; it is checked by a person.

Local numbers in this part are `INV-workbench.<n>`. This chapter holds **13 – 19**; [`tiles-ports-wires.md`](tiles-ports-wires.md) holds 1 – 12.

### INV-workbench.13 — One channel per meaning

For every channel in the colour law table, exactly one meaning is drawn with it. Four of the six are checked automatically, and the other two by eye:

- **Test, the brightness channel:** `frontend/src/styles/__tests__/colourLaw.test.ts` › `test_likelihood_ramp_is_read_only_by_the_two_chips` and `test_no_rule_sets_a_text_colour_to_the_ramp` — a walk over every stylesheet under `frontend/src/`.
- **Test, the hue channel:** `frontend/src/components/__tests__/directionReadout.test.tsx` › `test_no_file_outside_direction_readout_names_a_direction_token` (stated again as INV-workbench.15).
- **Test, the stroke and mark channels:** `frontend/src/graph/wires/__tests__/strokeIsShapeOnly.test.tsx` › `test_two_wires_differing_only_in_provenance_have_identical_strokes` (stated again as INV-workbench.17).
- **By eye, the texture and lane channels:** visual review checklist line 3 — convert the screenshot to greyscale and everything still reads. No automated check covers those two; nothing draws a tail in this stack, and a lane's colour is only ever redundant with its name chip.

### INV-workbench.14 — The greyscale test *(refines INV-12, nothing by hue alone)*

For every screenshot of any screen in this app, in either theme, converted to greyscale: every direction still reads (glyph and sign), every tail still reads (hatch), every kind of push still reads (pattern, width, doubling), every provenance still reads (the count of dots), and every branch still reads (its name chip).

- **Test:** `frontend/src/graph/wires/__tests__/notByColourAlone.test.tsx` › `test_nothing_is_carried_by_hue_alone` — for each of the three signal shapes the rendered stroke pattern differs; for each of the three origin steps the rendered dot count differs; for each direction the rendered glyph and sign differ. Colour values are excluded from every comparison, so a test can never pass on a hue.
- **Also:** visual review checklist line 3, run on every screenshot.

### INV-workbench.15 — A direction is never a hue on its own

For every element that reads `--dir-up` or `--dir-down`, that same element also renders a glyph (▲ or ▼), a sign, and a word.

- **Test:** `frontend/src/components/__tests__/directionReadout.test.tsx` › `test_direction_always_has_its_glyph_sign_and_word` and `test_no_file_outside_direction_readout_names_a_direction_token`.

### INV-workbench.16 — Tail risk is a texture, and is never guessed

For every claim rendered in this stack, no tail marking is drawn, because nothing on the map says which claim is a tail without arithmetic. For every tail marking drawn by any later stack, the marking is `--tail` and no hue token.

- **Test:** `frontend/src/components/__tests__/tile.test.tsx` › `test_no_tail_marking_is_drawn_from_fixture_data_alone`.

### INV-workbench.17 — Provenance is a mark, never the stroke *(refines INV-12 and UX-6)*

For every pair of arrows differing only in `provenance`, the two rendered strokes are identical — same pattern, same width, same doubling — and only the mark at the tail differs.

- **Test:** `frontend/src/graph/wires/__tests__/strokeIsShapeOnly.test.tsx` › `test_two_wires_differing_only_in_provenance_have_identical_strokes`.

### INV-workbench.18 — The motion budget

For every animation in the app: it is one of the three budgeted moves, or it is an opacity change of at most 120 milliseconds. And for every one of them under `prefers-reduced-motion: reduce`: every tween duration is `0ms`, and the ordering is unchanged.

- **Test:** `frontend/src/styles/__tests__/motionBudget.test.ts` › `test_no_duration_above_120ms_outside_the_three_budgeted_moves` and `test_reduced_motion_zeroes_every_tween_and_keeps_the_stagger`.
- **Also:** visual review checklist line 10 — turn on reduced motion: the ordering is still there and the tweening is gone.

### INV-workbench.19 — Three sizes, three weights, one face for words and one for numbers

For every piece of text rendered: its size is one of `--text-sm`, `--text-md`, `--text-lg`; its weight is one of the three weight tokens; its face is `--font-interface`, unless it is a number, in which case it is `--font-mono` with fixed-width digits. No rendered text falls below 11 pixels, and every piece of text and every glyph clears 4.5 to 1 against the surface behind it, in both themes.

- **Test:** `frontend/src/styles/__tests__/typography.test.ts` › `test_no_raw_font_size_no_fourth_size_no_fourth_weight` and `test_every_number_uses_the_monospace_face_with_tabular_digits`.
- **Also:** visual review checklist line 7 — is any text below 11 pixels, or under 4.5 to 1 in either theme?

---

## ANTI-PATTERNS

1. **Do not tint a whole tile by its likelihood**, because tile-wide brightness and opacity already carry the diff's ghosting and the hover lens, and three meanings on one channel means none of them reads. **Instead:** put the ramp on a bounded bar inside the belief chip and print the number beside it.
2. **Do not colour a push by its sign**, because a push's sign says which way a *claim* is pushed and hue says which way *money* moves — see *Direction — and what is not direction* above. **Instead:** print the sign and the word, and leave the hue channel to money.
3. **Do not use red and green for anything**, because red-green fails the most common form of colour blindness and the loss-and-gain reading is wrong half the time. **Instead:** blue up and amber down, always with a glyph and a sign.
4. **Do not put a hue into the likelihood ramp.** A ramp running red to green, or cool to warm, is a second voice in the channel that means money. **Instead:** five neutral brightnesses, and the printed number.
5. **Do not reach for amber when a fourth branch appears**, because amber already means "the money moves down" and a branch chip a reader mistakes for a downward move is worse than no colour at all. **Instead:** violet, teal, rose, slate — and a fifth branch is a question for Kent, not a fifth hue picked on the spot.
6. **Do not add a fourth type size** to make something fit, because size is the channel a reader ranks instantly and a fourth rank is a new rule for every screen afterwards. **Instead:** change the colour or the spacing, or cut the text.
7. **Do not crossfade a diff**, because the frames in between show numbers from a world that does not exist. **Instead:** a hard switch on `Space`, and a transition you can scrub.
8. **Do not animate anything to make the tool feel alive** — no idle loop, no spring, no shimmer. **Instead:** spend the three budgeted moves on showing causality and give everything else 120 milliseconds of opacity.
9. **Do not let a colour be the only difference between two states**, even a state this chapter has not named — a hover, a selection, a control that is not yet live. **Instead:** pair every colour change with a change of shape, weight, texture or position, and check it in greyscale.

---

## Open questions

*Raised 2026-09-17.*

1. **Three teals on one screen.** `--accent` is a teal meaning "this is fine", `--focus` is a brighter teal meaning "the keyboard is here", and the branch palette adds a third. Either they are far enough apart to tell at a glance, or the branch teal is dropped for a fourth hue that is not amber. Needs settling when the branch tokens are written, in pull request 3.
2. **The five `--p-n` values, and the light theme.** Five brightness steps clearly distinguishable against near-black are easy; five against white are harder, because a light surface leaves less room beneath it before a bar reads as flat black. Whether the light ramp runs the same direction or inverts is not settled.
3. **What branch creation actually animates.** The budget spends one of its three moves on it and nothing says which property moves. Proposed above: the lane colour and the name chip arriving over about 200 milliseconds, with no bounce.
4. **Does the hatch survive being zoomed out?** `--tail` repeats every 4 pixels, so at the zoom floor of `11/22 = 0.5` it is a grey smear — a texture that has stopped being one. The thresholds are [`layout-and-zoom.md`](layout-and-zoom.md)'s and are derived rather than chosen: summary tiles below `11/13 ≈ 0.85`, floor at `0.5`, both consequences of "text never below 11 pixels". The hatch may need a coarser variant, or the tail marking may need to become a glyph when zoomed out. Nothing in this stack draws a tail, so it can wait — but not past the stack that does.
5. **The hover lens dims to 15%; the ghost world paints at 20%.** Both are opacity, one channel carrying two meanings. [`diff-view.md`](diff-view.md) owns the ghost's value and the rule that the lens *multiplies* what is already there rather than replacing it, so an off-path ghost lands near 3% and disappears. Both are proposals pending Kent; what is settled here is only that one channel may not carry two meanings without such a rule.
