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

**Every engine-computed figure quoted below is read from one generated file.** [`docs/worked-numbers.txt`](../../docs/worked-numbers.txt) is written by `make numbers` from the shipped engine on the Strait of Hormuz map, at that example's own seed and the shipped loop sizes, and the build fails when it goes stale. Every line in it starts with a name a passage can cite — `B · base · reading` — and the numbers a person typed into the example are kept in a part of their own, apart from the numbers the engine worked out. A figure is quoted here only where it teaches something; the file is where it is kept true, so the day the arithmetic changes, the diff of that one file is the whole list of what moved.

[`keyboard-and-access.md`](keyboard-and-access.md) covers reaching and reading the panel without a
mouse, and owns the rendering rule behind INV-7 — two significant figures on the one number a
belief shows. *(It said "and the range never omitted" until 2026-09-22; Kent's R48 cut the range
from this product.)*

---

## Data model

`ClaimDetail` and `LinkDetail` are **projections of `ClaimView` and `LinkView`**, the per-claim and
per-arrow records on `WorldView`, all defined in [`diff-view.md`](diff-view.md). `BeliefView` — one
likelihood with a name on it *(and no range, 2026-09-22, R48)* — is defined in
[`tiles-ports-wires.md`](tiles-ports-wires.md). This panel takes the fields it draws and adds
nothing of its own:

```ts
interface InspectorProps {
  /** What is selected. Nothing selected is a real state with its own copy, not a blank panel.
      The third kind is the generation itself — not a claim and not an arrow, but the run that
      produced them; see B7. */
  subject:
    | { kind: "claim"; id: string }
    | { kind: "link"; id: string }
    | { kind: "generation"; id: string }
    | null;
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
  // No `decomposition` field: there is none on the world and none on the wire. The block is
  // assembled from fields that are each read — `prior` here, `strength`/`mode`/`lag`/`provenance`
  // and the fetched `conditional` on each incoming arrow, `beliefs.model` as the result — and not
  // one line of it is arithmetic. See B2.
  // `rangeShares` stood here — the reserved band slot, for stack 06. It was each stated range's
  // share of this claim's band, and a band is a range: it went on 2026-09-22 with everything else
  // R48 cut, and nothing had ever read it.
  pathProduct: Known<PathProduct>;     // INV-8; arrives on the world, never multiplied here
}
```

`LinkDetail` is `LinkView` with nothing added and nothing left out: the panel draws `rationale`,
`strength`, `mode`, `lag`, `shape`, `halfLife`, `sources` and `provenance`, in that order — B4 shows
the result. `Known<T>` and `Absence` — a value, or a kind of absence with the sentence that goes
beside it — are defined once in [`diff-view.md`](diff-view.md); every optional value here is one, so
no code path can render an absence as anything but its reason.

**A push**, which the panel shows for every arrow, is a link's `strength`: a signed amount added on
the **log-odds scale** — the scale on which separate influences add up instead of multiplying. A
positive push moves the claim at the arrow's head toward coming true; a negative one moves it away.

**Tokens read:** `--surface-raised` (the panel), `--hairline` (its one edge and its rules), `--text`
and `--text-muted`, `--font-mono` for every number, `--space-1` … `--space-4`, the likelihood ramp
`--p-0` … `--p-4`, `--accent`, `--focus` — all defined in
[`color-motion-type.md`](color-motion-type.md), where a direction is also rendered only through
`DirectionReadout`, which owns those tokens. This chapter defines none.

**Shared components:** `OriginMark` (the three-step provenance mark) and the belief chip. Each is
**one component**, drawn by the wire and the tile as well, so the mark on a wire and the word in
this panel cannot drift apart.

---

## Behaviour

Worked on the Hormuz map (the cast is in [`README.md`](README.md)). This chapter uses **B** *Brent
crude settles below $68 for five sessions* — the busiest claim on the map, three arrows in (**H**,
**C**, **R**) and three out (**M1**, **M2**, and back to R) — and the arrow **H → B**.

### B0 — What is beside the map, and what is allowed to change it

*Kent, 2026-09-22, of the replay: "could you have it so that clicking on a card will expand its details on the right hand side panel? In general, it's a little hard to find/navigate to/know what right hand side panels exist and how to navigate to them."*

**What was wrong.** A click already selected the tile and the panel already read it out — at the bottom of one column that also held, above it, the Verify door's answer, every proposal the rules refused printed in full, the receipt, the way into the working and *Run details*. Nothing scrolled on its own, so the answer arrived off the screen and the click looked dead. The stored map stacked its own sections the same way.

**The panel is a few panels now, and their names are at the head of it.** The names sit above the part that scrolls, so the way to the others can never scroll away, and they are the whole answer to *what is over there*.

| Screen | The panels it has |
|---|---|
| A map building itself | **This claim** / **This arrow** — whatever the reader chose · **The run** — the verdict, every refusal, the receipt, *Run details*, and every call the run made · **Outline** — the map as a list |
| A stored map | **This claim** / **This arrow** — whatever the reader chose, and the six things you can do to it · **Branches and changes** — your branches, the open one's edits, the engine's refusals, and the endings the edit reaches · **Outline** |

**A panel a screen does not have is not offered.** A map still being built has no branches to open; nobody generated a stored map, so there is no run to read out. Three each, never seven. *(Amended 2026-09-22: a **finished** generation does have branches — taking up *Change this claim* on one hands it to the stored map's screen, which is the screen with the branch panel on it, and carries its **Run details** and its working across. See [`streaming-growth.md`](streaming-growth.md) B11.)* A panel that exists and is empty says so in a sentence, as everything else in this product does — *Nothing selected. Choose a claim or an arrow on the map…*

**The name follows the subject.** *This claim* becomes *This arrow* when an arrow is what is selected, because the name is what says what the panel is about.

**One rule about when the panel changes by itself, and it has one clause.** Choosing a tile or an arrow — by mouse, by Tab, or by walking the wires with `h`, `l`, `j` and `k` — turns to the panel that reads it out, at once, at the top, with nothing scrolled. **Nothing else ever does.** A refusal arriving, the verdict landing, the receipt coming back, the engine answering about a branch: each of those changes a panel the reader may not be looking at, and each says so on that panel's own name — a count in the product's own word, *refused 3*, read off state the screen already holds — and in the strip at the foot, which says the same thing in a sentence. Nothing pulses, nothing fades and nothing grows; the motion budget has three movements in it and a panel asking to be looked at is not one of them (`color-motion-type.md`).

**Every name is a word.** Kent asked for *buttons or icons*; an icon with no word beside it is a thing a reader has to learn before they can use it, and this product has no icon set to learn from. Which name is chosen is said three ways — the word goes from the quiet colour to the text colour, a two-pixel rule of the accent runs under it, and `aria-selected` carries it for a reader who hears the screen. Two of the three survive greyscale, which is `VR3`.

**The panel is one press away, and it never opens over the map** *(2026-09-22 — this replaces "this panel is always here")*. It is inside the frame beside the map, 336 pixels wide whichever panel is chosen, and the map's stage does not change width when the reader turns to another one. What it now also does is fold: a chevron at the head of its own names puts it away and gives the map those 336 pixels, `P` does the same from anywhere on either map screen, and while it is away a 26-pixel tab at the edge the panel went behind — a chevron and the word *panel* — brings it back. Kent asked for the control, 2026-09-22: *"can you introduce a button to be able to collapse and open the side bar."* The key already did it and nothing on screen said so, which is a panel a reader can lose. **Pointing at a claim or an arrow while it is folded brings it back**, because pointing at one is the reader asking to read something and the panel is where it is read. **Walking to one does not.** Reaching a claim with the keyboard and pointing at one both fill the panel — that rule is untouched — but they are not the same request: a panel that came back on every selection came back on the reader's first press of `l`, and a fold a reader cannot walk away from is a fold that does not work. So while the panel is folded the map keeps filling it quietly, and `P` or the tab is what puts it back on the glass. It opens on every screen and is not remembered between them. *Nothing in this product opens over the map* is untouched: the folded panel takes its width out of the row rather than sliding over the canvas, and the tab is beside the map, never on it.

### B1 — A claim, top to bottom

Select B's tile. The panel fills, in this order, and nothing opens over the canvas:

```
Brent crude settles below $68 for five sessions.                       event

RESOLVES
  Front-month Brent crude futures settle below $68.00 on five
  sessions, consecutive or not, within the window.
  judged by   ICE Brent front-month settlement prices
  by          2026-10-15

BASE RATE
  —  no reference class recorded for this claim

PRIOR
  .28          model

BELIEFS
  model    .28
  user     —
  market   no market · no venue quotes this claim

EVIDENCE
  —  no clippings attached to this claim

WHY THIS NUMBER
  —  no engine yet
```

Five things to read off that:

* **The resolution triple is never optional.** Criteria, the source that adjudicates, and the date —
  all three, on every claim (INV-1, *checkable*: a claim nobody can score is not a claim).
* **Nothing sits under the model row at all** *(amended 2026-09-22, Kent's R48)*. There were two
  sentences here, and which one showed was decided by whether the world carried a count of versions
  of the map: record 0014's *model interval, uncalibrated · how sure we are of `.40` — not how much
  the world can move* over a computed number, and *stated range · not computed* over one nothing had
  worked out. Both were about the range under the number, there is no range, and both are gone along
  with the reserved band slot that sat under them. What the world still carries is one flag — whether
  the engine worked these likelihoods out — and the only place it changes a word is the last line of
  the decomposition and the sentence in the branch list.
* **The model row here is the prior's own number, and that is not a coincidence.** Every
  `beliefs.model` in the fixture equals its `prior`, because nothing has been computed into it. Run
  the engine over this map and B comes out `.40`.
* **Four things are genuinely absent on B, and each absence says which kind it is.** The **tile**
  shows `no market` and nothing else; **this panel is where the reason is read** — chosen by the
  claim's `kind` and written once in [`../vocabulary.md`](../vocabulary.md). B is an `event`, so it
  reads *"no venue quotes this claim"*; a `market` claim adds *"; what you would trade is on the
  payoff"*; a `not_tradeable` ending has its own stored reason, which is a finding and stays on its
  tile too. The **user** slot is the one absence drawn as a bare dash: an invitation to type your own
  number, where a sentence would read as an error rather than an offer.
* **Three beliefs, three owners, never merged** (INV-11). On B only the model has spoken; on **M1**
  two do. Read from the fixture, as this stack reads it, that is `model .40` — the prior, nothing
  computed — beside `market .48`, eight points apart, with `user —`. Run the engine and the model
  side becomes `.46`, two points apart. **Say which source a number came from before calling the gap
  an edge**: the gap is only worth trading once the engine has written the model's half of it. No
  function anywhere may average the two. The panel writes a belief on one line; the **tile** stacks
  it — owner, then number ([`tiles-ports-wires.md`](tiles-ports-wires.md)).

### B2 — The decomposition: a number that can say why

Under **WHY THIS NUMBER** the panel lays out the argument for the claim's number. The layout is the
one [`../graph/belief.md`](../graph/belief.md) §B4 draws — prior, one line per incoming arrow with
its push and its reason, then the result — and this panel copies it rather than inventing a second.
§B4's numbers are its own illustration and are not B's: B's prior is `.28`, it has no base rate, and
it has three incoming arrows, not two.

**There is no `decomposition` field, and the block is not one thing the world hands over**
*(corrected 2026-09-20, stack 04a, on building it)*. This chapter said the world carried the block
whole and the panel rendered it or rendered nothing. It does not: the engine's world has no such
field, and the wire has none. What the panel does instead is put together lines it each reads —
`prior` from the claim, the push and its reason from each incoming arrow, the arrow's conditional
where one has been fetched, and `beliefs.model` as the result — and the rule the old wording was
protecting survives untouched, because not one of those lines is arithmetic done here.

Four rules about it:

1. **One line per incoming arrow the world carries** — not a selection. B's real block has three,
   the third being R → B at −1.2.
2. **Feedback arrows are not lines of the block.** A market acting back on the world it measures is
   set aside before the engine works the map through ([`../multiverse/interventions.md`](../multiverse/interventions.md)),
   so it contributed nothing to the number at the foot, and listing it among the pushes would hand
   the reader a cause the engine never gave. It is listed below them under the outline's own words,
   **fed back into by**, with a sentence saying it has not pushed on this number and why. A claim
   whose only incoming arrow is a feedback one says nothing points at it — which is what the engine
   did. *(Added 2026-09-20, stack 04a, on building it.)*
3. **No line may be a number whose owner cannot be named** — `belief.md`'s rule, inherited here.
4. **This panel never computes the block.** A canvas that added up its own pushes would be a second
   engine, and two engines disagree. Each line is a field read and printed; the line at the foot
   says on screen that nothing here was added up.

**No line of it is ever merely missing** *(decided 2026-09-17 as "the whole block, or none of it";
restated 2026-09-20 to match what was built)*. The question was whether the panel might draw an
arrow's pushes while leaving out the result line. The answer is that every line is always drawn and
a line with no number says its absence and why, which is the rule the whole panel runs on — so the
result line reads *"no engine yet"*, with its reason, rather than being left off. A block missing
its last line reads as a sum somebody forgot to finish, and the reader cannot tell that from a sum
that went wrong; a last line that says why it is empty cannot be mistaken for either.

**Two passages stood here and both are gone** *(Kent, 2026-09-22, R48)*.

The first said that a claim which moved **only because some versions of the map started counting
for more** said so, in one sentence, at the head of this section: *this claim moved only because the
observation made some versions count more.* Observing one claim reweights the versions — a version
under which the observation was likely counts for more than one under which it was a fluke — and a
claim with no causes of its own can move by that alone. On Hormuz, observing **C** moves **H**, which
nothing on the map causes, and without a word about it the reader opened H and found a number that
moved, a prior, and nothing in between.

The second was **B3, the reserved slot: "why is this band wide?"** — one sentence, for stack 06,
naming the claim whose own prior explained most of a claim's band, worked out from `range_shares`
across the same two thousand versions the engine already ran.

Both were true, and both are about a thing this product no longer has. **The engine still writes
both fields**; `frontend/src/world/apiSource.ts` drops them at the wire and says so in a comment, and
they die when the engine half of R48 lands. What the panel has left for a claim the engine would not
call moved is its two readings and the engine's own reason, where the engine has one this product can
show — see `graph/diff/noChange.ts`, which owns those words.

**What a reader loses, said plainly.** A claim with no causes whose number moved under **This
happened** now shows the move and a decomposition with nothing in the middle of it, and the panel
does not explain the gap. That is the price of the cut, and it is the engine half's to answer: the
explanation that fits a product with no versions of the map in it has not been written yet.

### B4 — An arrow, read back in words

Select the wire from H to B. Same panel, different subject; still no pop-up:

```
The Strait of Hormuz reopens…   →   Brent crude settles below $68…

WHY
  The war-risk premium priced into crude unwinds once transit data confirms
  the lane is open. It is a one-time repricing, not a standing discount.

PUSH      +1.6 — a strong push toward
KIND      fires once. The push lands when the cause becomes true and then
          decays on its own; undoing the cause later does not undo it
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
  before the engine exists. The words come from the **five bands** in
  [`tiles-ports-wires.md`](tiles-ports-wires.md) — [`../graph/link.md`](../graph/link.md)'s four
  anchors with the gaps filled and one band below 0.25 (Kent, 2026-09-17) — and this panel uses
  them: on this map `+0.7` reads *a nudge toward*, `−0.4` *a nudge against*, `−2.4` *a strong push
  against*. The chip writes `+1.6 · a strong push toward` and the panel `+1.6 — a strong push
  toward`; that difference is the plan's.
* **Mode is a sentence, not a word to look up — and a plain one.** `trigger` reads *fires once…*;
  `sustain` reads *holds while the cause holds. The push exists only while the cause is true, and
  goes the moment it stops* — which is the arrow that makes the Hormuz showcase work. The panel
  prints the sentence and no picture of something else (Kent, 2026-09-21: terse and professional,
  no domino and no apple on a desk). [`../graph/link.md`](../graph/link.md) still explains where
  the distinction came from with both pictures; that is a chapter, not the screen.
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

**One mark, two things, and the second is new.** The mark says how well-backed the arrow is, and the
engine now reads the same word as *how unsure we are of its push*: each version of the map draws a
`documented` arrow's push close to what the map states and an `asserted` one's far from it
([`../multiverse/propagation.md`](../multiverse/propagation.md) owns the table). N1's only incoming
arrow is this one, and on the strike branch N1 has the widest band of the eight claims because of it:
`.38 (.17–.61)`. A reader who sees one dot is being told both things at once.

### B5 — The path-product bar (INV-8)

Select a claim and a bar appears beside the story sentence showing the **multiplied-out likelihood
of the steps of one route from the hypothesis to it**, and naming those steps. A chain of four
plausible steps is not a plausible chain, and the product is the number that says so.

**Which route: the best-backed one** — over every route from the hypothesis to the claim, the one
whose *weakest arrow is strongest*. That is the same route the delta rail's ranking uses
([`diff-view.md`](diff-view.md)), so the product has one path-choosing rule in the whole product,
used twice. On Hormuz, M1 is reached by `H → B → M1` and by `H → C → B → M1`; every arrow on both is
`argued`, so their weakest arrows tie, and the tie goes to **the shorter** *(proposed here — the
rule for ties belongs in `spec/multiverse/diff.md`, which stack 03a writes)*. The bar shows
`H → B → M1`:

```
H → B → M1            the strait reopens, Brent settles below $68, and the
                      Polymarket contract resolves YES
path likelihood       —  no engine yet
```

* **The product arrives on the world. This stack renders it and never multiplies anything itself.**
  If it is absent the bar says so with its reason; it does not fall back to computing.
* **Three things the bar can say, and they are not the same thing.** The number, when there is one.
  **"no path shown"** — nothing is selected, or no route was asked for; the absent-number case.
  **"no path from the hypothesis reaches this claim any more"** — a fact about the map after your
  edits, and the place that fact now lives: it stopped being a diff state on the tile (Kent,
  2026-09-17) because it is a property of the *route*, not of the claim. The bar never disappears; a
  missing bar looks like a bar nobody needed.
* **The honest wart, stated beside the number rather than hidden:** the factors are each read on
  their **own resolve-by day** — H by Nov 1, B by Oct 15, M1 by Oct 31 — so the product multiplies
  numbers read on three different days, and not even in order. It is still the most honest single number available for a chain,
  and **it is not a joint probability**. The panel says that in those words (decision record
  0014 §E).

### B6 — Every number is one click from its why

The rule behind the whole panel (NFR-1): **there is no number on this screen whose origin cannot be
named in one click.** A belief chip on a tile opens this panel at that claim, on that belief's row;
a wire's midpoint chip at that arrow; a delta rail row at that terminal; a number in the
decomposition at the arrow its line belongs to.

And the converse: **an absent number always renders its reason**, and the reason is a sentence a
reader can act on. *"no engine yet"* means the engine has not run. *"no market"* means no venue
quotes this, which is a finding about the world. A dash in the user's slot is an invitation, not an
error. None of these opens a window: the panel is always there, and selecting changes what is in it.

### B7 — This generation: the working

*(Decided 2026-09-17, stack 04a; this closes open question 2 below. **Amended 2026-09-21**: the
receipt's ten readings left this section — see below.)*

NFR-6 says every generation records the model, the tokens, the cache reads, the searches and the
dollars, and shows them in the Inspector's transcript view. Nothing generated in the stack that wrote
this chapter, so nothing was specified and nothing was drawn. A generation now exists, and this is
where its **working** is read: what it was run against, and every proposal it made, in order.

**What it cost is not here, and this section points at where it is** *(2026-09-21)*. The ten
readings were drawn twice — on the strip beside the map and again here — one above the other in a
320-pixel column. Two copies of one cost read, to somebody scrolling past, as two costs, and this was
the copy no number on screen could be traced to: the strip is what the `receipt` event fills in. So
the strip keeps them, in one place, and this section carries one sentence saying so.

**The generation is the panel's third subject.** Until now the panel opened on a claim or an arrow.
It also opens on the run that produced them — `{ kind: "generation", id }`, where `id` is the
identifier the engine minted and sent on `generation_started`. It is not a claim and not an arrow, so
it gets its own section rather than being squeezed into one:

```
THIS GENERATION
  the run that built this map

WHAT IT WAS RUN AGAINST
  seed                 <GenerationStarted.seed, as its digits>
  prompt fingerprint   <Receipt.prompt_hash, whole>

  The prompt fingerprint says which wording of our instructions produced this run:
  two runs with the same fingerprint were asked the same way, and two with different
  ones were not, however alike their maps look. It is printed whole because half a
  fingerprint cannot be compared with anything.

  What this run cost is on the strip beside the map, in ten readings, every one of
  them a field the engine sent.

EVERY PROPOSAL, IN ORDER
  0   accepted   The Strait of Hormuz is open to unrestricted commercial transit for
                 14 consecutive days
  …
  6   refused    "cheaper crude reduces the incentive to close the strait"
                 These claims form a loop with no delay in it: … Mark the arrow where a
                 market feeds back on the world as reflexive and give it a delay, or
                 remove one arrow.
  7   accepted   The energy fund XLE underperforms the S&P 500 fund SPY by more than
                 3% over 20 trading days
  —   stopped    Nothing further to add on "Lloyd's war-risk insurance premium for Gulf
                 transits falls below 0.4%"
  —   stopped    Nothing further to add on "Brent crude settles below $68 for five
                 sessions"
```

*(The `→ H` and `→ M2` this sketch used to carry are gone, corrected 2026-09-21: the code has never
drawn them and must not. On a generated map an identifier is twenty-six characters of the engine's
own bookkeeping, and a reader learns nothing from one — INV-workbench.55. An accepted line names the
claim it became by quoting the claim.)*

**Three kinds of line, not two.** A proposal was accepted, a proposal was refused, or the model
answered *Stop* on a line and it closed with nothing added. The third is the one a reader would
otherwise never see: it makes no event on the stream, because nothing about the map changed, and the
transcript is the only place it is recorded. **A stopped line carries no `at`** — `at` counts what was
proposed, and a stop proposed nothing — so the positions in this list have gaps in them, and the gaps
are the stops. Printing them as a dash rather than renumbering is what keeps `at` meaning the same
thing here as it does on the stream and in the refusal strip.

Five rules, and four of them are rules this panel already obeys. *(Two of them have moved with the
readings: what follows about the cost and the mode is now the strip's, in
[`streaming-growth.md`](streaming-growth.md) B6, and is kept here because it is still what a reader
of this chapter needs to know about a number they clicked through from.)*

* **Every number is a field, and the panel adds nothing up.** It does not total the two token counts,
  does not work a cost out of a token count and a price, and does not time anything. Searches have
  their own row because they are billed apart from tokens, so a reader checking `cost` against the
  token counts alone would find it wrong. INV-workbench.54 already forbids the arithmetic for
  likelihoods; the same rule covers a cost.
* **Every line of the transcript is in the engine's own words.** An accepted line names the claim it
  became; a refused line quotes what the model wrote and then carries the validator's own sentence,
  one per rule broken, with nothing added; a stopped line carries the model's own one-sentence reason.
  The panel composes no sentence about any of the three, and a refused claim is quoted rather than
  given an identifier or a tile.
* **The mode is read first.** On the strip, in a replay, the row says `replay` and names the day the
  recording was made — and **nothing else** *(amended 2026-09-21)*: it also carried the first eight
  characters of the prompt's fingerprint, which is a reading the browser derived on a strip whose
  whole promise is that none of them is, and is in any case a fingerprint nobody can check against
  anything. The fingerprint is printed whole here, with the sentence saying what it is for. The cost
  reads what the rebuilt receipt carries — zero, because the recording was played and nothing was
  called. That zero is a computed zero, printed rather than hidden (record 0012).
* **Before the receipt arrives, no cost is drawn anywhere.** No running estimate, no partial total,
  no ticking cost. A cost nobody has totalled is a number nobody computed, which is the same rule as
  the reserved band slot's in B3. **This section, though, is drawn from the moment there is a
  generation** *(corrected 2026-09-21: this said the section is not drawn, and stood above a section
  the code drew anyway, with *no engine yet* in it)*. It holds the working, not the cost, and the
  working is the thing a reader opens the panel for while a run is still going. Each slot that has
  not arrived reads an em dash. A section that appeared only once everything had landed would be a
  panel that is empty exactly while a reader is most likely to open it.
* **The two-significant-figures rule is about likelihoods.** A token count, a call count, a duration
  and a dollar figure are counts and measurements: they are printed whole, in `--font-mono` with
  fixed-width digits. INV-workbench.36 is phrased over beliefs for exactly this reason.

**Where it is read from, and how long it lasts.** `GET /api/generate/{generation_id}/transcript`, and
the server holds it in memory for the life of the process. There is no storage in this stack, so a
transcript does not outlive the server — FR-13's *"transcripts are stored with the graph"* arrives
with the SQLite file in stack 05 (FR-31). Until then, a transcript the process no longer has renders
as an absence with that reason, in the words of the route's own answer, rather than as an empty
section a reader would read as a transcript with nothing in it.

**How you get here.** Selecting a row on the refusal strip opens the panel at that transcript line.
Selecting the receipt strip opens it at the top. Both strips, and the shape of the stream behind
them, are [`streaming-growth.md`](streaming-growth.md)'s; this chapter owns only what the panel does
with them, and INV-workbench.72 there pins the receipt's own fields.

**And one control, in the panel, that appears only once there is a working** *(2026-09-21)*. *Read
the working of this run* used to be drawn from the run's first event. The working itself is read back
from the server **when the run stops** — the server writes it from the same pass that writes the
stream, and a half-read one would be a second, staler copy — so a reader who pressed it during the
two minutes they were most likely to press it was left with *Reading the working of this run…* until
the run ended. A control that cannot do what it says is worse than no control, so it is not drawn
until the run has stopped, whichever way it stopped. A run whose stream was cut has a working and
gets the control.

### B8 — Run details: where this map is coming from

*(Added 2026-09-21, decision record 0023, which brings decision R16 forward from a later stack.)*

**A plain section, always in the panel while there is a run**, carrying three readings and one
sentence: the route the map is arriving on, the run's own name, the seed every likelihood in it will
be worked out from, and *nothing on this map is typed in*.

```
RUN DETAILS
  route        /api/generate
  generation   <GenerationStarted.generation_id>
  seed         <GenerationStarted.seed, as its digits>

  Nothing on this map is typed in: every claim and every arrow on it was proposed by
  the model and accepted by the map's own rules.

  No likelihood has been worked out yet: the engine works them through the whole map
  at once, when the map is finished.          ← until the numbers land, and then it goes
```

**Where it came from, and why it moved.** It was an always-on strip of prose at the foot of the map,
reading *"Every claim and arrow on this map arrived from /api/generate, in generation …, at seed
…"*, and it was written from the run's **first** event — that is, **over a map with nothing on it
yet**. It asserted arrivals that had not happened; it was the third of three stacked strips at the
foot of a screen whose reader could not tell whether anything was happening at all; and Kent asked
for it to be *"hidden, deprioritized in terms of importance"*. Moving it here is what made it safe to
print the run's own sentence at the foot instead, because with this gone nothing down there repeats
it ([`streaming-growth.md`](streaming-growth.md) B11).

**What it says is true from the first frame.** *Nothing here was typed in* is a fact about how the
map is built rather than about how much of it has arrived, so it is true of an empty map and of a
finished one. The second sentence is true only until the numbers land, so it is printed only until
then.

**It is never a dialog.** Nothing in this product opens over the map. The whole panel folds away from
2026-09-22 — a chevron at the head of its names, `P`, and a tab at the edge while it is gone — but
*this section* does not fold behind a summary of itself: that is a later stack's work, and this
section is written to be folded and is not folded yet.

**The run's own name is the one identifier this product prints.** Every other identifier on a
generated map — a claim's, an arrow's — is twenty-six characters of the engine's bookkeeping and a
reader learns nothing from one, so none of them reaches the screen. This one is how somebody asks for
the same answer again, and how the working is asked for, so it is printed here and nowhere else.

---

## INVARIANTS

Each is *for all X, statement P holds*, and each names what checks it: a component test, or a
named line of the **visual review checklist** in [`README.md`](README.md), `VR1` to `VR13`.
Frontend test names are `test_snake_case`. Unless another file is named, the test lives in **inspector** —
`frontend/src/components/__tests__/inspector.test.tsx`. This chapter uses `INV-workbench.50` …
`.59`.

**INV-workbench.50 — one panel, no pop-ups.** For every subject the Inspector can be opened on —
every claim and every arrow on the Hormuz map, a generation, and the empty selection — it renders no
modal, dialog, alert or pop-over, and is a persistent region of the page. That the *whole product* has none
is checked by eye: **visual review checklist `VR2`**. *Test:* inspector ›
`test_renders_no_dialog_for_any_subject`.

**INV-workbench.51 — every number in the panel is one click from its why.** For every number the
panel renders, there is a subject it belongs to and one interaction that opens the panel there. That
the same holds for every number on the *canvas and the delta rail* is **visual review checklist
`VR5`**, checked by eye, plus the tile's and rail's own tests. *Test:* inspector ›
`test_every_rendered_number_resolves_to_a_subject`.

**INV-workbench.52 — three voices, never merged.** For every claim, the panel renders model, user
and market as three separate rows each labelled with its owner, and no function reached from this
panel takes two beliefs of different owners and returns one number (INV-11). *Test:* inspector ›
`test_renders_three_owners_and_never_averages_them`.

**INV-workbench.53 — an absence renders its reason.** For every `Known<T>` slot the panel reads, an
absent value renders its `Absence.reason` as words: no empty string, no zero, no stand-in number.
The single exception is the **user** belief slot, absence kind `not_said`, which renders a dash
inviting a number — the one absence that is an offer rather than a finding. *Test:* inspector ›
`test_renders_a_reason_for_every_absent_value`; **visual review checklist `VR5`**.

**INV-workbench.54 — the panel never computes a number, and never infers a reading.** For every
claim, every arrow and every generation, no number displayed is derived by arithmetic in the browser;
each is a field on the world, on the map or on the `receipt` event. In particular every line of the
decomposition is a field printed as it was read — the claim's prior, each arrow's push and its
fetched conditional, the model's belief as the result — with no line computed here and none left off
when its number is absent, and the receipt's counts are printed one by one and never added together.
*(The clause about the reweighting sentence went with the sentence on 2026-09-22, R48.)* *Tests:*
inspector › `test_never_derives_a_displayed_number`,
`test_no_sentence_about_reweighting_reaches_the_panel`;
`frontend/src/stream/__tests__/strips.test.tsx` ›
`test_the_receipt_strip_prints_every_field_and_adds_nothing_up`, which covers this rendering and the
strip's, because there is one rule and it should not be checked twice under two names.

**INV-workbench.55 — nothing in this panel says anything about a range or about versions of the map**
*(rewritten 2026-09-22, R48)*. It said: for every claim the sentence under the model row is the
stated one when `WorldView.versions` is absent and record 0014's when it is present, and the "why is
this band wide?" slot is drawn only in the second case. There is no range, no band slot and no count
of versions. What it requires now: for every claim and every arrow, no rendering in this panel
contains a range, the words *interval*, *uncalibrated*, *version*, *versions*, *worlds* or *middle
80*, nor a share of anything counted. *Tests:* inspector ›
`test_the_panel_says_nothing_about_a_range_or_about_versions`,
`test_no_sentence_about_reweighting_reaches_the_panel`,
`test_a_moved_claim_shows_the_two_readings_and_the_direction`; and
`frontend/src/graph/__tests__/noRange.test.tsx` › `test_no_panel_draws_a_range`,
`test_nothing_on_screen_mentions_versions_or_worlds`.

**INV-workbench.56 — the mark and the word come from one component.** For every one of the seven
provenance values, the mark beside the word in this panel is produced by the same `OriginMark`
component the wire renders, from the same input. *Test:* inspector ›
`test_the_panels_mark_matches_the_wires_mark`; **visual review checklist `VR3`**.

**INV-workbench.57 — the path bar renders, never multiplies.** For every selected claim the bar
shows the product the world supplied, or `no path shown`, or *no path from the hypothesis reaches
this claim any more* — three distinct readings, never one standing in for another — and there is no
multiplication in the component. *Tests:*
`frontend/src/components/__tests__/pathBar.test.tsx` › `test_renders_the_product_and_never_computes_one`,
`test_tells_no_route_apart_from_no_number`.

**INV-workbench.58 — every claim can be scored.** For every claim the panel opens, the resolution
criteria, the adjudicating source and the resolve-by date all render, none optional and none
abbreviated (INV-1). *Test:* inspector › `test_always_renders_all_three_resolution_fields`.

**INV-workbench.59 — a source says when it was fetched, or says nobody did.** For every source on an
arrow, the panel renders the day our retrieval step fetched it, or the reason there is no day. A
source with no retrieval day is never rendered as though it had one. *Test:* inspector ›
`test_renders_a_fetch_day_or_its_reason`.

**INV-workbench.84 — the only thing that changes which panel is on the glass is the reader** *(2026-09-22; numbered 84 because 60 to 79 are `streaming-growth.md`'s — 60 is *there is no spinner* — 80 and 81 are its two of 2026-09-21, and 82 and 83 are `first-screen.md`'s; a number is never reused, so a citation can never quietly come to mean another statement)*. For every map screen, choosing a claim or an arrow — by pointer or by keyboard — puts that subject's panel on the glass, and no event arriving from the run or from the engine ever changes which panel is showing. What an arrival may do is add a count to a panel's own name. Every name offered is a panel that screen has, and every one of them is a word. *Tests:* `frontend/src/components/__tests__/panelSwitch.test.tsx` ›
`test_a_click_on_a_tile_during_a_replay_shows_that_claim_in_the_panel`,
`test_a_click_on_an_arrow_shows_that_arrow_in_the_panel`,
`test_a_refusal_arriving_does_not_pull_the_reader_off_what_they_are_reading`,
`test_the_switcher_offers_only_the_panels_this_context_has`,
`test_the_stored_map_offers_its_own_panels_and_not_the_runs`,
`test_every_panel_label_is_a_word`,
`test_the_arrow_keys_move_between_the_labels`,
`test_the_one_key_steps_to_the_next_panel_from_anywhere_on_the_screen`,
`test_typing_is_never_a_shortcut`,
`test_the_panel_is_named_by_the_label_that_chose_it`; **visual review checklist `VR1`** (it is not a row of tabs from a component kit) and `VR9`.

---

## ANTI-PATTERNS

1. **Do not open a dialog for anything — not evidence, not a confirmation, not an error.** *Because*
   a modal steals the map you were reading, and the map is what makes the detail mean anything; it
   is also a named veto condition. **Instead:** one persistent panel, and confirmations as undoable
   toasts.

2. **Do not compute the decomposition in the browser from the pushes on the arrows.** *Because* the
   pieces are all there and the temptation is real — prior, three pushes, a result — and the moment
   the canvas does its own arithmetic there are two engines that disagree about half a point, with
   nobody able to say which is right. **Instead:** print the prior, the pushes and the result as
   the fields they each are, and an absence with its reason wherever one of them is not there.

3. **Do not bring a range back, in any form, to explain a number** *(rewritten 2026-09-22, R48)*.
   This anti-pattern was about not putting a plausible sentence in the reserved band slot and not
   printing the uncalibrated label over a number nothing computed. Both are now impossible, because
   both the slot and the label are gone. What is left to forbid is the thing that would bring them
   back: a band, an interval, a spread, a confidence, or a share of versions of the map, printed
   anywhere in this panel. *Because* Kent cut the whole idea rather than one wording of it, and a
   second-hand version of it — *how sure we are*, in some other words — would be the same confusion
   under a new name. **Instead:** one likelihood, and the decomposition that says where it came
   from.

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

8. **Do not let anything but the reader change which panel is on the glass, and do not draw a name
   that only an icon says.** *Because* a panel that jumps when a refusal lands takes a reader off
   the sentence they were halfway through, and a row of unlabelled pictures is a thing to learn
   before it can be used — and a row of filled, rounded pills is the component-library look that is
   a veto condition. **Instead:** the reader's own selection turns the panel, an arrival adds a
   count to a name, and every name is a word.

---

## Open questions

*Raised 2026-09-17. Four questions this chapter opened were settled by Kent the same day and now
read as statements in the body: which words a push reads back as (five bands, B4), which route the
path bar shows (B5), which sentence sits under the model row (B1), and where the "no market" reason
comes from (B1).*

1. **Where does "falsified if" come from?** FR-10 lists it among the panel's contents and no field on
   a claim carries it: the resolution criteria read backwards, or a genuinely missing field on
   `Proposition`. **Owner:** `spec/graph/proposition.md`.

2. **Where do generation cost and the transcript live?**
   **Decided 2026-09-17 (stack 04a): in the panel's own section, on a third subject.** The panel
   opens on a generation as well as on a claim and an arrow; the section prints the `receipt`
   event's fields one by one and the transcript beneath them, and is read from
   `GET /api/generate/{generation_id}/transcript`, which lives in memory for the life of the process
   until stack 05's file. In B7, and pinned by INV-workbench.54 here and INV-workbench.72 in
   [`streaming-growth.md`](streaming-growth.md).

3. **May the panel show an arrow's pushes before the engine, without the result line?**
   **Decided 2026-09-17 (stack 04a), restated 2026-09-20 on building it: the question does not
   arise.** Every line of the block is always drawn, and a line with no number says its absence and
   why — so the result line reads *"no engine yet"* rather than being left off, and there is no
   half block to build. In B2.

4. **"no reference class recorded for this claim"** *(proposed here)* is wording the interface wrote
   rather than a field it read, exactly as the "no market" sentences were before Kent settled them.
   If it is kept, it belongs beside them in [`../vocabulary.md`](../vocabulary.md). **Owner:**
   `vocabulary.md`.
