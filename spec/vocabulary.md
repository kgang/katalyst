# Vocabulary

Every document, identifier, and UI label uses these words exactly. If a better word appears, change it here first and then everywhere else (L2.21: understanding enables composition; shared words are the interface).

## Propositions and links

**Hypothesis.** The user's root input. A proposition asserted by `do()`, carrying the user's prior as a `user` belief. There is exactly one per graph.

**Proposition.** A node. A *resolvable* claim — something that will be true or false by a date, judged by a named source. Never a vibe ("tensions ease"); always a check ("≥14 consecutive days of unrestricted commercial transit per Lloyd's List by 2026-11-01").
- `kind`: `hypothesis` · `event` · `market` (terminal; names an instrument) · `not_tradeable` (terminal; names the reason). **Planned, and not in the build yet** (decision record 0017, stack 05): the in-between value `event` is renamed **`step`**, so the four kinds read `hypothesis · step · market · not_tradeable`. An arrow's `shape` also has a value called `step`; different field, different object, so no claim reads as a contradiction.
- `persistence`: **planned, and not in the build yet** (decision record 0017, stack 05). Which of the two kinds of truth this claim is — an **event**, which happens once and stays happened, or a **state**, which holds over a stretch of time and can stop. Written `persistence: event | state`. It is always required: a claim without it is refused by name rather than given a default.
- `resolution`: `{criteria, source, by}` — all required (INV-1).
- `prior`: the model's marginal belief before parents are considered.
- `base_rate` (optional): `{reference_class, k, n, sources}`.
- `evidence[]`: `{claim, url, direction ∈ {+1, −1}, weight}`.
- `payoff` (market only): one of two shapes, told apart by a `kind` field. A **contract payoff** — `kind: contract` — names a venue, the venue's own identifier for the contract, its title, and the side you would take (`yes` or `no`). A **price payoff** — `kind: price` — names an instrument, a direction (`long` or `short`), and `move`, how far the price is expected to move if the claim comes out true, as a fraction (0.03 is three per cent). The rule behind both: the domain names *what you would trade*; what it costs — price, spread, and when we looked — is a market belief, fetched live.

**Link.** An edge. A causal claim from one proposition to another.
- `mode`: `trigger` — horizontal/sequential causality (dominoes): fires once when the parent becomes true, effect persists and decays; removing the parent later does not undo it. `sustain` — vertical causality (the desk holds the apple): the effect exists only while the parent holds. **Planned, and not in the build yet** (decision record 0017, stack 05): a `sustain` arrow may leave only a claim that can stop holding — a **state** — and an arrow leaving anything else is refused by name; nothing retracts itself, so the words *"removing the parent retracts the effect"*, which stood here until 2026-09-21, are gone. The **sign** of an arrow's number decides which of a state's two rates it bends, so no field is added to an arrow.
- `strength`: how much the link shifts the child's odds while active, on a log-odds scale (so several links add up instead of multiplying).
- `lag`: time from parent-true to link-active. `shape`: `impulse` (a one-time spike that fades with `half_life`) · `step` (switches on and holds) · `ramp` (builds up over `lag`).
- `rationale`: the mechanism in one to three sentences. `sources[]`. There is no field for how sure the model is about its own mechanism; `provenance` and the rationale carry that.
- `provenance`: see below. `reflexive`: market → world feedback; requires `lag > 0` (INV-6).

**Provenance.** Where a number or link came from. `asserted` (model, no evidence) · `argued` (model, mechanism stated) · `documented` (cited sources) · `market_implied` (a live price) · `historical` (event study) · `user` · `simulated` (a probe). Encoded on every chip and wire (INV-2, INV-12). **Two of those seven words cannot be written by anything in version one** (2026-09-21, decision record 0021): `historical` needed the historical-analog panel (FR-29) and `simulated` needed probes (FR-20), and both are cut. The values stay on the wire so nothing has to be retrofitted; nothing produces them.

**Belief.** `{p, lo, hi, owner}` with `owner ∈ {model, user, market}` and `0 ≤ lo ≤ p ≤ hi ≤ 1` (INV-7). The three owners are stored and rendered separately and never averaged (INV-11). Rendered at two significant figures with the interval. `lo` and `hi` are the 10th and 90th percentiles of the likelihood itself — how sure we are of the number, not how much the world can move. **That does not change** when the engine's arithmetic changes under it (2026-09-21, decision records 0016 and 0017, which move nearly everything around this entry): `lo` and `hi` mean the same thing before and after.

**Graph.** Propositions + links. A DAG after removing `reflexive` links; reflexive links unroll in time (INV-6). Has exactly one hypothesis and ≥1 terminal (INV-9). Immutable once created; changes are branches.

## The multiverse

**Intervention.** One operation on a graph:
- `do(n, value, at?)` — assert. Cuts the incoming links `n` has **at the moment the edit is applied**; a link inserted later is live. A timed assertion — `do(H, at=Oct 1)` says H holds from the 1st, not that H is sealed for ever. Ancestors unchanged (INV-3). This is what a hypothesis is.
- `observe(n, value)` — learn. Updates ancestors as well as descendants. Distinct verb in the UI.
- `insert(node, links[])` — "…but X happens." Adds a proposition and its links.
- `retune(link, strength)` — the user disagrees with a number.
- `refine(n → children[])` — split a proposition into finer sub-propositions; their combined likelihood must equal the original's (they *marginalize* back to `n`, INV-10). The brainstorm's "search deeper lines". **Not built in version one** (decision record 0021, 2026-09-21): the shape exists so nothing has to be retrofitted, and asking for it returns one violation in our own sentence rather than half-doing it.
- `believe(n, belief)` — record the user's own belief on `n`. Lives in the branch so it replays and diffs; never alters `model` or `market` beliefs; not propagated in v1 (D8, INV-11). Propagating a user's world is a stretch (see `probes/`).

**Branch.** A named, ordered list of interventions over a base graph. A branch *is* a patch. Branches compose by concatenation; `apply(g, [])` is `g` (INV-5). Branches may have a parent branch.

**World.** A base graph with a branch applied and beliefs propagated. Replayable from `(base_id, branch, seed)` (INV-5, NFR-2). The base world is the empty branch. **Planned, and not in the build yet** (decision record 0016, stack 05): a claim's number becomes the chance it comes out true by its own deadline, and its series is how that chance stands on each day — rising for an event, able to fall for a state.

**Diff.** Between two worlds: per proposition, `unchanged` · `shifted` (with before → after) · `added` · `killed`; plus a ranked list of terminal deltas and a one-line natural-language summary. **`killed` means forced false, and nothing else** (decided 2026-09-17) — never "its number got small", and never "no path reaches it from the hypothesis any more", which is a fact about the *path* and is reported by the Inspector's path bar in those words. The ranking is the size of the move times the weakest provenance weight on the **best-backed route** from a differing edit's subject to that ending: over every such route, the one whose weakest arrow is strongest. Two factors; range width and agreement are columns beside it and are never multiplied in.

**Version of the map.** One coherent set of numbers this model would have stood behind: every claim's likelihood drawn from its own stated range at once, never every low end together. The engine runs two thousand versions, and today eight worlds under each. The range on a computed number is the spread across versions; a change is read version by version, never by whether two ranges overlap. **Planned, and not in the build yet** (decision record 0016, stack 05): the inner eight worlds go, because the answer inside a version is worked out exactly rather than sampled. **The count of versions stays two thousand** — the spike measured 2 000 as enough to hold a narrow range's two ends to two significant figures, where at 200 a range's end wanders a tenth of the range's own width.

**Agreement.** The share of versions of the map in which a change moved the same way. Computed, never self-reported. *(Until 2026-09-21 this entry added "each version counted by as much as it counted for the two numbers — so a version an observation left with no surviving world does not vote". That weighting is history: under the exact core of decision record 0016 no version is ever left with nothing, so every version counts the same under every edit. It is written here rather than deleted because a reader who knew the old rule must be told it is gone.)* A claim counts as `shifted` when it moved by .005 or more **and** agreement is at least 90%; agreement is then shown as its own column beside the change, never multiplied into the ranking. **On screen that column is headed *same direction*** (decided 2026-09-17), and the width column beside it is headed *how firm*; the field names stay `agreement` and `range_width`. Keeping the word *agreement* off this screen leaves it free for a run-to-run number — how far several independent generation runs agreed on a claim's likelihood — if one is ever earned. Stack 04 computes no such number: decision record 0015 ships the range the model stated and says *not yet* to an ensemble. If a second number ever exists: same idea, same rule, and wherever both could be meant, say which.

**Locality.** An intervention changes only what is still connected to its subject in the graph the edit leaves behind (INV-4). Which claims those are depends on the operation, because the operations leave behind different graphs: `do` cuts the target's incoming arrows, so only the target and its descendants remain connected to it; `observe` cuts nothing, so its ancestors — and what those ancestors cause — are connected too. The per-operation **affected set** table in `multiverse/interventions.md` is the operational form, and the property test computes the set from the shape of the graph. The product's central correctness claim.

## Sensitivity and drill-down

**Sensitivity sweep.** One-at-a-time flip of every proposition; record Δ on each terminal. **Planned, and not in the build yet** (decision record 0019, stack 06): each claim is flipped **both ways**, because which direction hurts depends on which side of the trade the reader is on, and the sweep today flips each claim only to the opposite of whichever way it more often comes out.

**What to watch.** The claim whose adverse flip most damages an ending *and* resolves before it *and* is publicly observable (INV-14). It is a **watchlist, never a stop** (decision record 0019); the word *invalidation* is retired. **Unhedgeable**: adverse but resolving too late or not observable; listed with the reason, never used as a stop.

**Tail.** A low-probability, high-magnitude proposition. Listed in its own strip with a suggested hedge; never averaged into an expected value.

**Probe** (stretch). A modeling resource attached to one proposition: `monte_carlo` · `bayes_subnet` · `persona_redteam`. Output re-enters the graph as a `simulated` belief with its own rationale. **Not built in version one** (FR-20; decision record 0021, 2026-09-21): a probe is a second engine with a second set of answers to reconcile. The word is kept here because the honest part of the idea — a persona that argues with one step of the map — is scheduled for stack 07 under a different name.

**Value of information.** How much the trade depends on a proposition × how uncertain it is; ranks where a probe is worth its cost. **Not built in version one**, because it ranks probes and probes are cut (decision record 0021, 2026-09-21).

## The trade

The words stack 06 adds, from decision records 0018 (like with like), 0019 (a stop is a price the reader owns) and 0020 (a quote is recorded first). **None of this is in the build yet**; the words are settled here first, as this document's own rule asks.

**Edge.** The model's **unconditional** number for a claim against a price somebody will actually deal at: *buying* = model − the best offer − any fee; *selling* = the best bid − model − any fee. Computed only from the world with nothing fixed by an edit, by one function that takes that world and the world on screen as two separate arguments (decision record 0018). Signed, and a negative edge is a complete answer. Never used for an arrow on the map, and never for the gap between the model and a reader's own belief.

**Break-even.** The price at which a trade is worth exactly nothing: worth **buying below** *model − fee*, worth **selling above** *model + fee*. It bounds the price you would actually pay or receive, not the midpoint, and it needs **no quote** — which is why it prints when there is none. Undefined on an ending that names an instrument until the reader has typed an entry price.

**No-trade band.** The stretch between those two bounds, where neither side is worth doing. A larger fee makes it **wider**.

**Fee.** What the venue charges on a filled trade. The only cost term in an edge: the spread is already inside the bid and the offer, so it is never subtracted again.

**Tick.** The smallest price step a venue trades in. A gap narrower than one tick is not headlined as an edge.

**Not comparable.** What the card prints instead of an edge, with the reason from a closed list: *a supposed world where the unsupposed one belongs · no quote right now · no contract quotes this claim · the market is settled.* A refusal is a value, not a blank.

**Quote.** What a venue is charging for a contract: the venue; its condition, market and outcome-token identifiers; the side; the best bid and best offer as read; the instant; resting size and traded volume; whether it is closed and accepting orders; the venue's own question, rules and end date; the minimum price increment; a web address; and `source` — `fetched`, `recorded` or `user`. The midpoint is derived, never asserted. A `user` quote is the reader's **report of a price they could deal at**, which is not a `user` belief about the claim.

**Spot anchor.** A measured historical level from an economic-data service — an **observation** with a series name and a vintage date. It anchors a price ending; it never fills the `market` belief (decision record 0020).

**Position.** The reader's trade on one ending: instrument or contract, side, entry, stop, target, horizon, **risk budget** — the share of their capital they are prepared to lose on this trade. Every field theirs; none derived.

**Your exit.** The stop, the target and the horizon on that form. Typed, never derived.

**First touch.** Walking a daily path through each drawn world and recording which of the stop and the target is reached first — with the **barrier shift**, the standard correction for checking only once a day: the stop is moved a little way toward the starting price, because a daily check misses touches between closes. The stop is taken as first when a day crosses both.

**Surprise.** The part of a claim's stated move that today's price does **not** already reflect: the stated move less the market's own chance of the claim times that move. It is what the path applies on the day the claim comes true; the rest is given back, day by day, while the claim has not happened. The market's chance comes from a venue quote on that claim where one exists, otherwise from the model's own number in the world with no fixed value in force, and the reader may override it. The screen names which (decision record 0019).

**Ceiling.** A quartered Kelly — a quarter of the bet size that would make capital grow fastest given a stated edge — worked out at the unfavourable end of the model's stated range, shown greyed and labelled *never size to this*. It is never a recommended size; the reader's risk budget is the only number that sets one.

**Draws.** The one thing the trade layer asks of the engine: for each drawn world, the day each claim came on and the day it went off, and how much that world counts.

**Lift.** How much more often a claim had already happened **before the stop was touched**, among the worlds where the stop went first, than across all drawn worlds. Three means three times as often; one means it tells you nothing. Shown with a Wilson interval on the numerator share and the number of effective drawn worlds behind it, never below two hundred.

**What takes you out.** The list of claims ranked by lift. Company, not cause.

**Watchlist.** The rows under *what to watch*. The word *invalidation* is retired.

**Mixture.** The two terms shown after a *Suppose* — the map's own chance of the supposition times the supposed reading, plus one minus that chance times the reading with it supposed false. An **explanation with a measured residual**, never the number compared against a price.

**Shock.** A claim the reader inserts and supposes true, reported as the change to their position with no probability attached.

## The finale

**Thesis.** The compiled trade: `hypothesis`, `horizon`, `legs[]` (instrument or contract, direction, size, driving claim, model p, quote, fee, the gain from buying and from selling — or a named refusal — and the break-even), `carried_by`, `takes_you_out`, `watch`, `unhedgeable`, `your_exit` (stop, target, horizon — the reader's), `distribution` (p10/p50/p90, the chance of the stop first, of the target first, of neither), `tails[]`, `stresses[]`, `refuses[]`, `not_advice`.

**Strategy export.** A declarative JSON rendering of a thesis with graph references justifying each leg; the shape a downstream trading agent could ingest.

## Surfaces

**Workbench.** The main screen: canvas + world-state strip + Inspector + tail strip + thesis dock.
**Tile.** A proposition's on-canvas card. **Port.** A typed input/output on a tile. **Wire.** A link's on-canvas rendering. **Inspector.** The persistent side panel; never a modal. **Delta rail.** The ranked terminal-delta list beside a diff; its two side columns are headed **how firm** (the width of the new number's range) and **same direction** (the share of versions of the map that moved the same way — the field called `agreement`; on screen the word *agreement* is kept free for a run-to-run number, if one is ever earned; decision record 0015 says not in stack 04). **Launchpad.** The empty state with the four seeded examples.

## Interface words

The six operations keep their code names in code, in the wire format and in this document — `do`, `observe`, `insert`, `retune`, `refine`, `believe` — and none of those words appears on screen. These are the words the user reads. Change a button here first, then everywhere else.

| Code name | The button | The badge afterwards | What the interface says it means |
|---|---|---|---|
| `do` | **Suppose this is true** (and **Suppose this is false**) | **Supposed · date** | "Take this as given, and do not tell me what caused it" |
| `observe` | **This happened** | **Happened · date**, and **Did not happen · date** where the news is that it did not (Kent, 2026-09-21, G12) | "This is news — update what came before it too" |
| `insert` | **Add a claim**, hinted as "…but this also happens" | **Added** | A claim and its arrows arrive together |
| `retune` | **Change this push** | **Retuned** | "You moved this arrow from +0.7 to +0.3" |
| `refine` | **Split this claim** | **Split** | The finer claims add back up to the one they replace |
| `believe` | **My own number** | none — the three-up belief chip is the badge | Your number sits beside the model's and the market's |
| none | **Build the map** | none — the map is the answer | "Turn what I typed into a map of what it would cause" |
| none | **Change this claim** (and **Change this push**, on an arrow) | none — it opens the buttons above, and they earn the badges | "Show me what I can do to this" |

**One of these rows has no control on screen in this build.** **Split this claim** is not implemented, and an operation that does nothing is not offered — a control that takes a press and then explains that it cannot act is still a control a reader counted and cannot use. Its words are settled here for the day it arrives.

**Suppose this is false** is implemented and is offered, beside **Suppose this is true**; the two share one row because they are one operation with one badge. The panel carries, under each of the two easiest to confuse, that operation's own line from the last column of this table, so the difference is read before the press rather than after it.

**Change this claim** is the second of that table's two labels with no code name behind it, because it opens the operations rather than being one. It is the way in for somebody working the screen with a mouse, and it sits in the head of the panel that says why a number is what it is: on a claim it reads **Change this claim**, on an arrow **Change this push** — the same words as the button inside that changes the arrow's number, because it is the same thing asked for, and the two are never on screen at once. It is drawn only while the operations are shut, since a way in that is already in is not a control. The keyboard's way in is `E` and the command palette's is a command of the same name; where a screen has to name the way in rather than draw it — the change list with nothing on it yet — it uses these words too.

One more badge is **derived**: no button produces it. **Retracted · date · by "…"** appears on a claim that was supposed true and has since been pushed back down by a later edit — what was holding this up was removed. It names the edit responsible and the day it landed (the mechanism is in `multiverse/interventions.md`). **It is on its way out** (2026-09-21, decision record 0017): automatic retraction is deleted with stack 05's engine work, and afterwards nothing produces this badge at all. What takes its place is the **state** — a claim that holds over a stretch of time and can stop — whose tile says the day it stopped holding and names the claim that ended it (UX-14). A claim the user supposed true will simply stay supposed until another edit changes it.

**Build the map** is the one button in that table with no code name behind it, because it starts a generation rather than editing a map: there is no intervention called *build*. It is the only button on the input bar, and it is the same button on both doors — Explore and Verify differ by whether the destination field has anything in it, and a button whose label changed as you typed would be a control moving under you. Not *Generate*, which is the pipeline's word rather than the reader's.

### Words the growing map uses

Four things a reader sees only while a map is being generated. What each is, and what it is never allowed to become, is in `workbench/streaming-growth.md`.

**Skeleton tile.** A reserved rectangle standing where a claim is about to arrive: the tile's own box, one line of words, and nothing else. Never a number, never an identifier on the map, and never a shimmer — it is a space held open, not a thing pretending to load.

**Refusal strip.** The list beside a growing map of every proposal the map's own rules turned down: one row each, carrying what the model wrote and the validator's own sentence for each rule it broke. Nothing is trimmed, merged or summarised away.

**Receipt strip.** The lines beneath it saying what the run cost — the model, the calls, the tokens in and out, the tokens read from cache, the web searches, the dollars, how long it took, and whether it ran live or from a recording. Every one of them is a number the engine sent; the screen adds nothing up.

**Replay badge.** The mark on the canvas saying this session is playing a recording rather than calling a model, with the day the recording was made. It is a fact about the session, not a badge on a claim, and no button produces it.

## Words for a number that is not there

An empty slot never shows a blank, a zero or a placeholder: it shows words and, one hover or one click away, a reason. These are the words; change them here first. The code carries **five** kinds of absence, and two of them — a number the engine refused to work out, and an ask that did not come back — are kinds of their own rather than shades of *no engine yet*. **The last two rows below are the trade card's rather than a tile's** and are not new kinds (2026-09-21, decision records 0018 and 0020): they say what the card prints where a venue publishes one price and no range, and where no venue quotes the claim at all.

| Where | On the tile or the card | The reason, read in the Inspector and on the chip's hover |
|---|---|---|
| No market price, on a `market` claim | **no market** | "No venue quotes this claim; what you would trade is on the payoff." |
| No market price, on an `event` or the `hypothesis` | **no market** | "No venue quotes this claim." |
| No market price, on a `not_tradeable` ending | **no market**, with the claim's own stored reason **on the tile** — that reason is a finding, not boilerplate | the same stored reason |
| No number of your own yet | **—** and *add yours* | "You have not given a number for this claim." |
| Nothing has been computed | **no engine yet** | "Nothing has worked this number through the map yet." |
| The engine **refused** to work it out | **not worked out** | the refusal's own reason, naming what was refused — for a branch that does not fit the map: "The engine would not work this map out from this branch: the branch does not fit the map. Every reason is beside the map, and nothing on the map has changed." |
| The **ask did not come back** | **the ask did not come back** | the failure's own sentence, and what to do about it: "… Select this arrow again to ask once more." |
| A venue quotes this claim but publishes no interval | the number, with **no range** | "The venue publishes one price, not a range. What the two sides of its book differ by is what dealing costs, and it is shown there." |
| Nothing quotes this claim | **no contract quotes this claim — edge not calculable** | "No venue asks this question; here is the break-even instead, where one is defined." |

**Why *no engine yet*, *not worked out* and *the ask did not come back* are three rows and not one.** *No engine yet* says nothing has run and invites waiting. *Not worked out* says the engine was asked, answered, and would not — which invites repairing the thing it turned down, and which will say the same thing every time until somebody does. *The ask did not come back* says the engine is there, it was asked, and one attempt got no reply — which invites asking again, and which may well be gone by the time you do. Three different facts about the same empty slot, and a reader who cannot tell them apart will wait for an answer that is never coming, or repair something that was never broken.

The code carries the difference as three kinds — `no_engine`, `refused` and `ask_failed`, beside `no_market` and `not_said` — rather than as a difference in the words, because words are not something code can read back. **`ask_failed` is the only absence that is never kept**: it is not a fact about the map, so nothing files it with the answers.

## Words we do not use

*Prediction* (we model arguments, not oracles) · *scenario* (ambiguous between branch and world) · *edge* when we mean a link (reserve *edge* for the model-against-venue difference defined under *The trade* above) · *invalidation*, retired 2026-09-21 (decision record 0019) — say *what to watch* for the computed list and *your exit* for the price the reader types, and never call either a stop-loss · *node* in UI copy (say tile or proposition) · *confidence*, at all — there is no confidence field on anything. A link's standing is its `provenance` (a receipt we write), its rationale, and the range on the belief; a number for how much things computed independently agreed is called *agreement* — defined under *The multiverse* above — and is computed, never self-reported.
