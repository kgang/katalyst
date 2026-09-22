# PRODUCT_REQUIREMENTS.md — Katalyst

> A causal-chain workbench for finance. You state a hypothesis; it builds an auditable graph of downstream events toward tradeable effects; you bend any link and watch the multiverse re-propagate; it ends in a thesis that says what carries it, what takes you out, and what it does not know.

**Status:** living document (L1.11: there is no shipping, only current state). **Owner:** Kent Gang. **Reader:** the Catalyst team (see §2). **Derived from:** `ASSIGNMENT.md`, `docs/initial-brainstorming.md`, `docs/research/*`, and the 2026-09-16 interview (§3). **Governed by:** `AGENTS.md`. **Companions:** `ARCHITECTURE.md` (how the system is shaped — the technical counterpart to this document), `docs/adr/` (numbered decision records — a journal), `spec/` (the detailed spec, organized as a book by idea).

---

## 1. What this is, in one screen

**The hero use case, in one sentence.** You type an event you think will happen. Katalyst shows what it would cause, step by step, ending in trades — and lets you change any step to see how the trades change.

**Input.** "The Strait of Hormuz is going to open next week." Optionally, a destination: "does that get me to Brent under $70?" Optionally, how likely *you* think it is — or "I don't know."

**Output.** A map of cause and effect. Each box is a claim that can be checked by a date ("Brent closes under $70 by Nov 1, per ICE settlement"). Each box shows how likely it is as three numbers side by side: what the model thinks, what you think, and what the market is pricing. Each arrow states the mechanism, how strongly it pushes, and how long it takes. The map draws itself as the model reasons. It ends in things you can trade: a ticker, a contract, a commodity price.

**The move.** Click any box and change it: "…but Iran is struck the next day." The original map is kept. A new version forks off. Only the boxes downstream of your change update. A faded overlay shows exactly what moved. Do this as often as you like and compare versions.

**The finale.** A thesis card: what to buy or sell, when to enter, your own exit — the stop and the target you type — the claims that show up in the worlds where that stop went first, the one adverse turn you could see coming in time, and the rare disasters listed one by one rather than hidden inside an average. Exportable in a form a trading system can read.

**Two doors, one map.** *Explore:* "Hormuz opens — what happens next, and what can I trade?" *Verify:* "Does Hormuz opening actually lead to cheaper oil — and where is that chain weakest?" Same map. Verify adds a destination, so the map grows toward it and grades every step. Explore is the first screen; Verify is one extra field, not a second product.

**What it is not.** Not a chatbot with a diagram attached. Not an oracle: it lays out an argument, and every number can show why. Not a swarm of simulated agents. Not a place to execute trades.

---

## 2. Who reads this, and what "good" means to them

Catalyst (`catalyst.app`) is 4–5 engineers from Jane Street / DRW / Citadel / Jump, seed-funded by Sequoia and Jump, already shipping natural-language → backtest → execution with a custom query language. They sit *downstream* of this tool. They will not be impressed by another front door to an LLM; they will be impressed by a tool that turns a vague belief into something with a venue, a strike, an entry, a stop, and a falsifiability test — and does so honestly.

The brief names three wants: **(a)** how black-swan events affect risk, **(b)** which events lead to being stopped out, **(c)** whether a hypothesized event actually leads to the desired financial effect. Each maps to a first-class surface below: the *Tail strip* (a), *What takes you out* — the claims that had already happened in the worlds where the reader's stop was touched first, ranked by how much more often they show up there — with *what to watch* beside it (b), *Verify door + conjunctive honesty bar* (c). *(Want (b) was worded as "which events trigger stop-loss / take-profit" until 2026-09-21; decision record 0019 makes the stop a price the reader types and the two lists the thing the map computes.)*

Craft is part of the requirement. The brief says "balance form and function"; the owner's kernel says "impeccable style." A template-looking UI is a disgust-veto condition (§3).

---

## 3. Decisions taken (interview, 2026-09-16)

Settled by the owner; recorded here so no agent re-litigates them. Reasoning and rejected alternatives live in the numbered decision records under `docs/adr/`.

| # | Question | Decision | ADR |
|---|----------|----------|-----|
| D1 | Hero use case | Type an event; see what it causes, step by step, ending in trades; change any step and watch the trades change. **Explore** ("what happens next?") is the first screen. **Verify** ("does A really lead to B?") is the same map with a destination added — one extra field, not a second mode | — |
| D2 | Truth source | The model reasons out loud: every arrow states its mechanism, a base rate (how often this kind of thing has happened before), and a likelihood *range*, not a point. Where a real market prices the same event, that price sits beside the model's number. **Stretch:** pick any box and spend extra compute on it — thousands of random simulations, a small probability model, or role-played experts hunting for gaps — so the user decides where precision matters | 0003, 0005 |
| D3 | Look and feel | *Workbench*: the rigor of a visual-programming tool (boxes with typed sockets, wires that show the signal's shape) × cards rich with evidence you can pin and arrange like a mood board × a simulation game's sense of world state and time. Not minimalist; not a game | 0007 |
| D4 | Stack | Python backend (FastAPI web framework, pydantic data models, uv package manager); React + TypeScript frontend (Vite build tool). Frontend types are generated from the backend's API description so the two never drift | 0002 |
| D5 | Disgust veto | (i) **Template UI** — default component-library look, spinner-then-dump, modals, hairball. (ii) **Not knowing why it did that** — any state not traceable to an input, a rule, or a cited source | all |
| D6 | Thesis finale | Thesis card + live read-only market prices + declarative strategy export | 0010 |
| D7 | Budget | Open-ended garden. Structure for continuous iteration; PR stacks tell the story | 0009 |
| D8 | Whose judgment | Your own likelihood estimates are stored as first-class inputs and shown beside the model's and the market's. The tool sharpens your view and shows where it differs; it never replaces it | 0004 |
| D9 | Cadence | Decision-gated. Draft the decision record and spec → owner accepts → implement. Nothing lands against a `proposed` decision | 0001 |
| D10 | PR stacks | GitHub native stacked PRs (public preview); verify on repo, fall back to `git-spice` | 0009 |
| D11 | First slice | Engine and canvas in parallel on a shared schema stack | 0009 |

---

## 4. Vocabulary

Every doc, identifier, and UI label uses these words exactly. Full definitions in `spec/vocabulary.md`.

| Term | Meaning |
|------|---------|
| **Hypothesis** | The user's root input: a proposition asserted as true (the `do` intervention below), carrying the user's own likelihood estimate |
| **Proposition** (node) | A *resolvable* claim: criteria, adjudicating source, resolve-by date. Kinds: `hypothesis`, `event`, `market` (instrument-bearing terminal). **Planned, in stack 05** (decision record 0017): the in-between kind is renamed `step`, and every claim also says which kind of truth it is — an **event**, which happens once and stays happened, or a **state**, which holds over a stretch of time and can stop — in a field called `persistence` |
| **Link** (edge) | A causal claim from one proposition to another: `mode` (`trigger` — domino, fires once, decays; `sustain` — desk-holds-apple, the effect holds only while the cause holds), `strength` (how much it shifts the odds of the next proposition; on a log-odds scale so several links add up), `lag`, `shape` (`impulse` \| `step` \| `ramp`), `half_life`, `rationale`, `sources`, `provenance`. **Planned, in stack 05** (decision record 0017): a `sustain` arrow may leave only a state, and nothing retracts itself — the words *"effect retracts if cause is removed"* stood here until 2026-09-21 |
| **Provenance** | Where a number or link came from: `asserted` (model, no evidence) · `argued` (model + mechanism) · `documented` (cited sources) · `market_implied` (live price) · `historical` (event study) · `user` · `simulated` (probe). **Two of those seven cannot be written by anything in version one** (decision record 0021): `historical` needed FR-29 and `simulated` needed FR-20, and both are cut. The values stay on the wire; nothing produces them |
| **Belief** | A probability with an honest interval `{p, lo, hi}` and an owner: `model` \| `user` \| `market`. The three are never merged |
| **Graph** | Propositions and links with no loops (a directed acyclic graph). Loops are legal only through `reflexive` links — a market feeding back on the world — which must have a delay and unroll over time |
| **Intervention** | One of `do` (assert; cut parents; the button reads **Suppose this is true**), `observe` (learn; update parents too; the button reads **This happened**), `insert` (add a proposition + links), `retune` (change a link), `refine` (expand a proposition into sub-propositions that must marginalize back — **not built in version one**, decision record 0021: the shape exists and asking for it returns one violation in our own sentence), `believe` (record the user's own belief on a proposition; shown beside the model's, not propagated in v1) |
| **Branch** | A named, ordered list of interventions over a base graph. A branch *is* a patch; branches compose by concatenation |
| **World** | A base graph with a branch applied and beliefs propagated. The base world is a branch with zero interventions |
| **Diff** | The structural and belief delta between two worlds: `unchanged` / `shifted` / `added` / `killed` per node, plus ranked terminal deltas |
| **Probe** (stretch) | Extra compute attached to one proposition: thousands of random simulations (Monte Carlo), a small probability model (Bayesian sub-net), or role-played experts hunting for gaps (persona red-team). Output re-enters the graph as a `simulated` belief. **Not built in version one** (FR-20; decision record 0021), so nothing writes a `simulated` belief |
| **Thesis** | The compiled trade: what carries it, what is priced in, legs, **your exit** — the stop, target and horizon the reader types — **what takes you out**, **what to watch** with *unhedgeable* beside it, the outcome distribution, tails and reader-placed shocks, caveats, and the limits it refuses to exceed carried as data. *(Rewritten 2026-09-21; decision records 0018 and 0019, which retire the word* invalidation *— a stop is a price the reader owns, not a claim the map derives.)* |

---

## 5. The hero flow

```
 Launchpad ─▶ Hypothesis (+ optional target, + optional prior)
     │
     ▼
 Streaming generation ─▶ Graph grows layer by layer; wires draw in propagation order;
     │                   belief chips resolve last. Reasoning arrives as it is produced.
     ▼
 Inspect ─▶ any node/link: rationale, sources, base rate, model|user|market beliefs,
     │      "falsified if", and the path from the hypothesis worked out (FR-11)
     ▼
 Intervene ─▶ "…but Iran is struck the next day" ⇒ branch forks, downstream re-propagates,
     │        ghost overlay + delta rail + one-line diff.  A ⇄ A′ on one key.
     ▼
 Drill down ─▶ attach a probe where the thesis is most sensitive
     │         (not built in v1 — FR-20, decision record 0021)
     ▼
 Thesis ─▶ card + recorded prices + export.  Your exit is typed;
           what takes you out and what to watch are computed.
```

---

## 6. Functional requirements

Priority: **P0** — the hero flow does not exist without it. **P1** — the tool is not credible without it. **P2** — stretch; documented, designed for, not built first.

### 6.1 Input and doors
- **FR-1 (P0)** Natural-language hypothesis input. Explore door (no target) or Verify door (target proposition B).
- **FR-2 (P0)** Ask for the user's own likelihood estimate at input as a range slider with an explicit "I don't know" state. Stored as a `user` belief on the hypothesis; never overwritten by the model.
- **FR-3 (P0)** Launchpad empty state seeds the four `ASSIGNMENT.md` examples as one-click cards. No illustration.

### 6.2 Generation
- **FR-4 (P0)** The engine produces a graph in which every proposition is resolvable (INV-1) and every link carries mechanism, strength, lag, shape, provenance, and ≥1 source or an explicit `asserted` mark (INV-2).
- **FR-5 (P0)** Generation streams. Propositions and links arrive one at a time over server-sent events (a one-way stream from server to browser) and render as they arrive; layout reserves space so the graph grows without reflowing violently.
- **FR-6 (P0)** Every graph terminates in ≥1 `market` proposition, or in an explicit "not tradeable — because…" terminal (INV-9).
- **FR-7 (P0)** Verify door returns a graded path A→B or an explicit `no_path` verdict with the nearest reachable proposition. Never a fabricated bridge.
- **FR-8 (P1)** Where a claim's starting number and range come from: **the likelihood and range the model stated in its proposal**, stamped as a `model` belief by us, shown under the label *model interval, uncalibrated*, and never merged with a user's or a market's number (amended 2026-09-17; decision record 0015). **No ensemble in v1**: no claim is asked about twice, no map is generated several times over, and **two maps are never reconciled into one** — `spec/multiverse/diff.md` anti-pattern 4, *do not infer a difference by matching two maps*, is the warrant. A **measured run-to-run number** — how far independent generations differed about a claim, computed and never self-reported — is deferred, and the word *agreement* is kept free on screen for the day one exists. One condition reopens it and no other: if FR-30's pastcast shows stated ranges missing badly against the evaluation scorecard, measure whether re-asking widens them *toward the truth* — the **median** of several answers, never a "trimmed mean" of three, which is only the middle one — and decide then. *(2026-09-21, decision record 0021: FR-30 is not built in version one, so this condition cannot be met within version one and no ensemble is built. Record 0015 is unchanged; what it loses is its escape hatch.)*
- **FR-9 (P1)** Adversarial critique pass before beliefs are final. **(P2)** Persona red-teams ("Lloyd's underwriter", "OPEC desk") that propose *missing* propositions and links — hypothesis diversity, not outcome simulation.

### 6.3 Audit
- **FR-10 (P0)** Inspector (a panel, never a modal) for any proposition or link: rationale, sources, base rate and reference class, the three beliefs, "falsified if", resolution criteria.
- **FR-11 (P0)** Conjunctive honesty bar: for any path from the hypothesis to a selected proposition, show three worked-out numbers beside the narrative headline — the **shift** the hypothesis makes to that proposition, the **chance every step on the route goes right** as a true joint, and **which single arrow carries most of the shift**, with how much of the shift goes with it (INV-8). *(Rewritten 2026-09-21, decision record 0022: multiplying likelihoods along a route is not the chance of anything once two claims on the map share a cause, and the factors were each read on a different day.)*
- **FR-12 (P0)** Provenance is visibly encoded on every link and belief chip (INV-2, UX-6). It also **sets how wide that arrow's push is drawn** when the engine works the map through: narrow where a page the search returned backs the arrow, widest where nothing does. *How well-backed is this* and *how sure are we of this number* are one question asked once, and the width is derived from the word every time rather than stored beside it (added 2026-09-21; decision record 0014).
- **FR-13 (P0)** Replay: any world is reproducible from `(base graph id, branch, seed)`. Generation transcripts are stored with the graph.

### 6.4 Multiverse
- **FR-14 (P0)** Interventions `do`, `observe`, `insert`, `retune`, `believe` on any proposition; committing one forks a branch implicitly; the base world is immutable (INV-5).
- **FR-15 (P0)** Re-propagation is local: only the intervened proposition and its descendants change (INV-4). A `trigger` arrow's effect persists once its cause has happened; a `sustain` arrow's effect holds only while its cause holds, and such an arrow may leave only a claim that can stop holding — a state *(rewritten 2026-09-21; decision record 0017, which also deletes automatic retraction)*.
- **FR-16 (P0)** Diff: ghost overlay of A under A′ in a shared union layout; delta rail of terminal changes ranked by **the size of the move × the weakest backing on the best-backed route** from a differing edit's subject to that terminal — over every such route, the one whose weakest arrow is strongest (amended 2026-09-17; "shortest path" and "which edit" both leave the rule). Range width and **agreement** are shown beside as their own columns, never multiplied in — multiplying width in would sink exactly the claims FR-21 floats. A claim counts as **shifted** when it moved by .005 or more **and** moved in the same direction in at least 90% of versions of the map; that share is the agreement. A claim that is not `shifted` **says which of those two it failed** — it barely moved, or it moved and the versions did not agree which way — because those are two different findings and a screen that reports only "no change" hides the more interesting one (added 2026-09-21). The floor and the 90% bar stay inside the engine and are on no wire, so nothing outside it can re-run the test and disagree. One-line natural-language diff.
- **FR-17 (P1)** Compare ≥3 branches as small multiples; at most 4 branches visible, rest collapsed to a list; branches must be named. *Not built in version one — **Kent's decision R31**, recorded in decision record 0021 (2026-09-21), which is where the cut is first written down: three or more branches side by side is a dashboard, and the ranked change list already answers the question two worlds at a time. It goes on the* what I would do next *page.*
- **FR-18 (P1)** `refine`: expand a proposition into sub-propositions; the children's combined likelihood must equal the parent's — they marginalize back (INV-10). This is the brainstorm's "search deeper lines". *Not built in version one — decision record 0021: making finer claims add back up means re-deriving the parent's number by summing the children out of the joint, and nothing in the brief asks for it. The `refine` operation exists as a shape and is refused by name.*

### 6.5 Sensitivity and drill-down
- **FR-19 (P1)** Sensitivity sweep: one-at-a-time flips of every proposition, **each flipped both ways**, ranking by adverse Δ on each terminal — because which direction is adverse depends on which side of the trade the reader is on, and flipping a claim only to the opposite of whichever way it more often comes out never consults that side (decision record 0019). Feeds FR-23 and FR-21.
- **FR-20 (P2)** Probes: attach a Monte Carlo, a Bayesian sub-net, or a persona red-team to one proposition; results re-enter as `simulated` beliefs with their own provenance and rationale. *Not built in version one — decision record 0021: a probe is a second engine with a second set of answers to reconcile; the honest part of the idea lands in stack 07 as* challenge this arrow.
- **FR-21 (P2)** "Where to spend modeling budget": rank propositions by **each stated range's share of the terminal's band** — how much of the width on the number you care about comes from not being sure of *this* claim — and say so in the UI. On the Hormuz example most of the Brent claim's band is its own `prior`; pin that down and the band narrows by roughly that share. **The figures are not repeated here.** They are worked out by the engine, so they move whenever its arithmetic does, and they live in one generated file — [`docs/worked-numbers.txt`](docs/worked-numbers.txt) — on the lines named `B · base · band from B` (the share) and `B · base · reading` (the band it is a share of). *(Corrected 2026-09-17: this requirement used to say "base rate", which the Brent claim does not have — the number that varies between versions of the map is its `prior`. Until 2026-09-21 it also carried figures typed into this document; they went stale twice and now live only in the generated file, which the build checks.)*

### 6.6 Risk
- **FR-22 (P0)** Tail strip: low-probability / high-magnitude propositions listed in a fixed strip with p, what they would do to the reader's position, and what could be done about it — never averaged into an expected value. **A shock the reader places themselves** — a claim they insert and suppose true — is reported as the change to their position with **no probability attached**, because supposing something is not a statement about how likely it is (decision record 0019).
- **FR-23 (P0)** The exit is the reader's; the lists are computed. **Your exit** — stop, target, horizon — is typed on the position form and never derived. Beside it: **what takes you out**, the claims that had already happened in the worlds where the reader's stop was touched first, ranked by lift, each row carrying its interval and the number of drawn worlds behind it; and **what to watch**, the adverse flip that damages the ending most *and* resolves before it *and* is publicly observable. A claim that is adverse but resolves too late or cannot be observed is listed as *unhedgeable* (INV-14, decision record 0019).
- **FR-24 (P1)** Outcome distribution for the reader's position, over many drawn worlds walked day by day: the 10th / 50th / 90th-percentile outcomes, the chance the stop is touched first, the chance the target is touched first, and the chance of neither by the horizon — each printed in the same sentence as the name of the distribution the event times came from, and computed with the standard correction for checking only once a day, the **barrier shift**, because a daily check misses touches between closes. **The path applies only what the market has not already priced** — a claim's stated move less the part today's price already reflects — at a market chance taken from a venue quote on that claim where one exists and from the model's own unsupposed number otherwise, **named on screen either way** (decision record 0019). A contract ending is held to resolution and has no first-touch answer. **Cut from version one** (decision records 0019 and 0021): the average loss in the worst 5% of runs, the largest peak-to-trough loss and the chance of being wiped out — each needs a capital base and a portfolio this product does not ask for. The percentile outcomes stay and are built in stack 06 from the reader's own position.

### 6.7 Thesis
- **FR-25 (P0)** Thesis card, in six sections: **what carries it** · **what is priced in** (the model's number, the venue's bid and offer with their source and day, the fee, the gain from buying and from selling — or the named refusal and the break-even) · **what takes you out** · **what to watch**, with *unhedgeable* beside it · **your exit** (stop, target, horizon, risk budget — the reader's — and beside them a **greyed quartered-Kelly ceiling** at the unfavourable end of the model's stated range, labelled *never size to this*, which reads zero where that range does not agree which side of the price to be and is absent with a reason wherever no edge can be built) · **tails and reader-placed shocks**; plus the distribution (P1), the caveats (weakest arrows, unhedgeable claims, crowding), and one line of execution: *a stop order's trigger is not its fill price* (decision records 0018 and 0019).
- **FR-26 (P1)** Read-only prices, **recorded first**: a committed dated quote file the demo and the build run on, an opt-in live Polymarket read that falls back to it and never runs in continuous integration, and a reader-entered price always available. A venue's quote is shown beside the model's and the reader's numbers as the `market` belief — a **point**, never a range, because the difference between the best bid and the best offer is what dealing costs and the venue publishes no interval — and never as a bare number: venue, value, source and date are one unit. **A FRED figure is an observation, not a belief**: it anchors the spot level of a price ending, renders the required attribution line ("This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis"), and never fills the `market` slot. **Kalshi is cut from version one** (decision record 0020); where one venue quotes a claim the card names it and says no other was asked, and where two ever do, both are shown and never averaged.
- **FR-27 (P1)** Strategy export: a declarative JSON document (schema in `spec/thesis/`) with legs, conditions, and the graph references that justify each — the shape a downstream trading agent could ingest, **carrying its own limits as data — a `refuses` list and a `not_advice` line — rather than as a footer** (`spec/thesis/card-and-export.md`).

### 6.8 Grounding
- **FR-28 (P1)** Retrieval at generation time (server-side web search). **A search result becomes a `Source` on an arrow and nothing else** — an address that opens, the page's own title, and the day it was fetched; a source carries **no direction and no weight** (amended 2026-09-20: the old wording, "sources attach to links with direction and weight", named two different things at once). Direction and weight belong to an **`Evidence`** item on a *claim* — what the Inspector draws as bars for and against — and **generation writes none**, because both of those numbers would have to be invented; a generated claim's evidence list is empty and the panel says so. A base rate is kept only when it cites a page the search returned, on the same rule.
- **FR-29 (P2)** Historical-analog panel: for a link, past instances and how prices moved around them, with an uncertainty band (an event study). *Not built in version one — **Kent's decision R31**, recorded in decision record 0021 (2026-09-21), which is where the cut is first written down: it needs dated past instances and the price history around them, and record 0010's grounding has neither. It goes on the* what I would do next *page.*
- **FR-30 (P2)** Pastcast self-test: run a chain on a resolved 2024–25 event with a date-frozen corpus and show the Brier score (the standard accuracy score for probability forecasts; lower is better), including when it is bad. *Not built in version one — decision record 0021: it needs the evidence frozen as it stood before each event, which the pipeline cannot do, and one resolved event is not a track record. One sentence about it goes on the* what I would do next *page.*

### 6.9 Persistence and sharing
- **FR-31 (P0)** A finished generation is served back by its id from the same line-by-line file a recording is: one format, one loader, no database. Sessions are addressable by that id in the URL. No accounts in v1. *(Shrunk 2026-09-21 — Kent; decision record 0021. A kept run already writes that file and the replay path already reads it.)*

---

## 7. UI/UX requirements — the *Workbench*

The direction is D3. The research's "Instrument" craft rules (typography, color, motion) still apply; the *shell* is a workbench, not a terminal.

- **UX-1 Node tiles are rich.** A proposition renders as a card with: claim, kind silhouette, belief chips (model | user | market) as a three-up, a density sparkline when quantitative, evidence clippings (a letter monogram taken from the source's host name — never a fetched favicon, so the first frame makes no outside request — plus one line), and the resolve-by date. Fixed width, clamped height, 8px grid. Detail lives in the Inspector, not the tile.
- **UX-2 Ports and wires are typed.** Propositions have input and output ports; a link is a wire whose *stroke* encodes signal shape (impulse: dot-dash; step: solid; ramp: gradient) and whose *weight* encodes |strength|; `sustain` wires are double-stroked; `reflexive` wires loop with a visible lag chip. The midpoint chip shows the conditional probability in the Metaculus arrow-and-bar idiom.
- **UX-3 World state is visible.** A strip shows the terminal instruments as gauges (Brent, a basket, a contract) with their model | user | market readings, re-ticking on intervention. Time is a scrubbable axis; lags are real distances.
- **UX-4 Level of detail by zoom.** Far: worlds and their terminal deltas. Mid: wiring and belief chips. Near: the full tile with evidence. Text never shrinks below 11px; the tile changes representation instead.
- **UX-5 Organizability.** Users can pin, group, and annotate tiles (mood-board affordance); automatic layered layout (the ELK library, left→right) is the default and re-layout preserves the focused tile's screen position. Dragging is either fully supported or absent — never half.
- **UX-6 Color is law.** Probability → luminance/opacity. Direction of financial effect → blue ▲ / amber ▼, always with glyph and sign, never red/green. Branch identity → a small ordered palette on lanes and chips only. Tail risk → hatch texture, not hue. The kind of push → the wire's stroke (UX-2). Provenance → a three-step origin mark at the wire's tail, where the arrow leaves its cause (●●● documented, historical, market-implied · ●● argued, user · ● asserted, simulated), with the exact word in the Inspector — a mark, not a stroke style, because the stroke is already spent on the kind of push and one channel cannot carry two meanings. No information in hue alone (INV-12).
- **UX-7 Motion budget.** Three animations: propagation wave (wires draw in causal order, ~200ms staggered), branch creation, belief number-roll. Everything else ≤120ms opacity. `prefers-reduced-motion` keeps ordering and drops tweening.
- **UX-8 Streaming is the loading state.** No spinner. Skeleton tiles appear at their layer, claims stream in, wires draw, chips resolve last. Reasoning arrives as it is produced.
- **UX-9 Keyboard first.** `⌘K` palette; `j/k` siblings; `h/l` layers along wires; `E` intervene; `B` branch; `Space` A⇄A′; `?` sheet. Focus is always visible.
- **UX-10 No modals.** One persistent Inspector; confirmations are undoable toasts.
- **UX-11 Typography.** One UI face and one tabular-figures mono for every number; three sizes, three weights; hierarchy by color and spacing. Not the component library's defaults.
- **UX-12 Themes and access.** Dark-first, light verified, semantic tokens. All text and glyphs ≥4.5:1. The graph also exists as an outline (`role="tree"`) with a screen-reader announcement (`aria-live`) when a branch re-propagates.
- **UX-13 Empty and edge states.** Launchpad (FR-3); `no_path` verdict as a first-class card; "not tradeable — because…" terminal as a first-class card.
- **UX-14 A claim that stops holding says when, and what stopped it.** A **state** — a claim that holds over a stretch of time rather than happening once — never renders as plainly true after the thing sustaining it is gone. Its tile says the day it stopped holding and names the claim that ended it, and the branch panel lists that branch's edits in the order they were made. A claim the user supposed true stays supposed until another edit changes it; nothing withdraws it on a schedule. **The rule that a later `insert` outranks an earlier assertion still holds in the patch algebra and is still readable in the branch panel's ordered list of edits — it is simply no longer rendered as a badge on a tile, because there is no longer anything for that badge to report** *(rewritten 2026-09-21; decision record 0017)*.

---

## 8. Non-functional requirements

- **NFR-1 Honesty.** Beliefs render at two significant figures — **one number, and no range anywhere on the screen** (`.35`) *(amended 2026-09-22; Kent's R48 cut the range and the two thousand versions of the map behind it. This line read "the number and both ends of its range — with their interval (`.35 (.22–.50)`)". The screen half has landed; the engine half, INV-7's own wording and records 0005 and 0014 are the stack 05 session's)* — never `.347`, and never as a certainty: **a likelihood below `.01` prints `<.01`, and one above `.99` prints `>.99`** (amended 2026-09-20: that is where the guard begins, rather than wherever rounding happens to reach `.0` or `1.0`). **A move is not a likelihood**: the size of a change keeps two significant figures however small — a claim reading `.36` that moved up by nine thousandths reads `.36 · up by .0090`, never `.36 · up by .0` — because a move rounded away reads as no move at all, and the engine and the browser round by the same rule, pinned by a test that compares them. Every number is one click from rationale, sources, base rate.
- **NFR-2 Determinism.** Propagation is pure and seeded; the same `(graph, branch, seed)` yields byte-identical worlds.
- **NFR-3 Tests.** The core graph code is property-tested (the Hypothesis library generates thousands of random graphs and shrinks any failure to a minimal example) against the invariants in §9; the model boundary is tested with recorded API responses ("cassettes") committed to the repo; evals run out-of-band on the four assignment examples. CI is green with no API key (INV-13).
- **NFR-4 Docker.** `docker compose up` yields a working app; `docker compose watch` gives hot reload for both halves; a production-ish compose builds slim images with healthchecks. No database service in v1.
- **NFR-5 Legibility.** Every architectural decision is a numbered decision record; every feature with invariants has a spec; every PR names the invariant it satisfies; conventional commits with `spec:` and `adr:` types.
- **NFR-6 Cost visibility.** Each generation records model, tokens, cache hits, and dollars; shown in the Inspector's transcript view.
- **NFR-7 Performance.** 60 tiles render and re-layout in <100ms on a laptop; **streaming first paint within 1 s of the request being accepted — a reserved rectangle at its column; this pipeline returns whole proposals, not tokens** (amended 2026-09-20: the old wording read "within 1s of the first token", and there are no tokens to paint — a call comes back with a finished proposal, seconds later, so what must appear inside the second is the space the first claim will land in). **Recalculating a branch is targeted proportional to the size of the map, not to a fixed number** — the reference point is **600 ms** for one world with its range on a **twenty-claim** map at 2 000 versions, which is **30 ms a claim** by plain division, and what it protects is that an edit feels responsive. It is a target and not a gate: the engine's measured figures are recorded beside it in `ARCHITECTURE.md` §10, and no pull request is refused for missing it *(added 2026-09-21; Kent, R24, which supersedes the fixed 600 ms of R19; decision record 0016)*.
- **NFR-8 Secrets.** One `.env.example`; keys read once via settings; a secret scanner (`gitleaks`) runs before every commit; recorded API responses are scrubbed of keys.

---

## 9. Invariants

Phrased as checkable statements. Each names the spec that owns it; specs name the property test. If an invariant cannot name a test strategy, it is a wish and belongs in §6.

| ID | Invariant | Owner |
|----|-----------|-------|
| INV-1 | **Checkable.** Every proposition has resolution criteria, a named adjudicating source, and a resolve-by date | `spec/graph/` |
| INV-2 | **Says why.** Every link has a rationale and a provenance; a link that claims evidence (documented, historical, or market-implied) carries at least one source. Every belief has an owner | `spec/graph/` |
| INV-3 | **Assert is not observe.** Asserting a proposition (`do`) changes nothing upstream of it; observing it (`observe`) may. Two operations, two verbs in the interface | `spec/multiverse/` |
| INV-4 | **Locality.** An intervention changes only what is still connected to its subject in the graph the edit leaves behind; every other proposition is byte-identical between the base and the branch. Operational form: the affected-set table in `spec/multiverse/interventions.md`, which names the set for each of the six operations | `spec/multiverse/` |
| INV-5 | **Branches are patches.** The base graph is never modified. A branch is an ordered list of interventions. Applying an empty branch changes nothing; applying two branches in sequence equals applying their concatenation. Every world replays exactly from (base, branch, seed) | `spec/multiverse/` |
| INV-6 | **No loops.** Ignoring *reflexive* links (a market feeding back on the world), the graph has no cycles; every reflexive link carries a delay greater than zero | `spec/graph/` |
| INV-7 | **Honest numbers.** Every belief satisfies 0 ≤ low ≤ p ≤ high ≤ 1 after any sequence of interventions, and is rendered at two significant figures with its range | `spec/graph/`, `spec/workbench/` |
| INV-8 | **Chains are worked out, not multiplied.** Any displayed path shows the shift the hypothesis makes to its destination, the chance every step on it goes right computed as a joint, and which single arrow carries most of the shift *(rewritten 2026-09-21; decision record 0022)* | `spec/workbench/` |
| INV-9 | **Ends in a trade.** Every graph has at least one tradeable terminal, or an explicit "not tradeable — because…" terminal | `spec/graph/` |
| INV-10 | **Refinement adds up.** After a proposition is split into finer sub-propositions, their combined likelihood equals the original's within a small tolerance. *Met by a named refusal rather than a feature — decision record 0021: `refine` returns one violation, `edit_not_applicable`, in our own sentence, pinned by `test_splitting_a_claim_says_it_is_not_built_yet`* | `spec/multiverse/` |
| INV-11 | **Three voices.** Model, user, and market beliefs are stored and rendered separately; no code path averages them | `spec/graph/`, `spec/workbench/` |
| INV-12 | **Not by color alone.** Every direction has a glyph, every tail a texture, every provenance a mark | `spec/workbench/` |
| INV-13 | **Keyless CI.** Continuous integration runs with no model API key and **no outbound network call of any kind**; the model boundary and every outside price are exercised only through recorded responses (decision record 0020) | `spec/generation/`, `spec/thesis/` |
| INV-14 | **A watchlist you can see.** A claim shown under *what to watch* resolves before the ending it is watched for and is publicly observable; a claim that is adverse but resolves too late, or cannot be observed, is listed as *unhedgeable*. No claim is ever presented as a stop: a stop is a price the reader types (decision record 0019) | `spec/thesis/` |

---

## 10. Anti-patterns

Phrased as *do not X, because Y; do Z instead.*

1. Do not let the LLM assign IDs or own graph validity — it collides across branches and invents cycles. Mint IDs server-side; validate in the domain layer; reject, don't repair silently.
2. Do not re-prompt for the whole graph after an edit — it breaks locality (INV-4) and auditability. Re-propagate mathematically; re-prompt only for `insert` on the affected subtree.
3. Do not conflate conditioning with intervention — "P(oil ↓ | Hormuz open)" is correlational. Offer `do` and `observe` as separate verbs and say which one the user is doing.
4. Do not average model, user, and market beliefs into one number — the product's value is the gap between them (INV-11).
5. Do not render `.347` — precision beyond two significant figures on an elicited number is a lie (NFR-1).
6. Do not headline an expected value — tails get their own rows (FR-22). EV hides the wipe-out.
7. Do not simulate an agent society to produce outcomes — unvalidated and the audience pattern-matches it as theater. Use personas only to propose missing structure (FR-9).
8. Do not use Markov steady states or chaotic dynamics as the engine — these events are one-shot and non-ergodic. Time-unroll lagged links instead.
9. Do not ship a force-directed hairball, a spinner-then-dump, a modal, or the component library's default look — each is a D5 veto condition.
10. Do not let a chain end in prose — every terminal is an instrument or an explicit "not tradeable" (INV-9).
11. Do not derive the reader's stop — on this product's own worked example the derivation names the claim the trade rests on, which restates the trade rather than warning about it, and the sweep behind it computed only one direction (decision record 0019). **Instead:** take the stop, the target and the horizon as numbers the reader types, and compute *what takes you out* and *what to watch* beside them.
12. Do not put a database, auth, or multi-tenancy in v1 — three failure modes and zero value to the reader. Serve a finished generation back from the line-by-line file the run already wrote (FR-31, decision record 0021) — there is no database in version one at all.
13. Do not implement against a `proposed` decision record (D9).

---

## 11. Non-goals (v1)

Execution and order routing · accounts and multi-user · agent-society simulation · learned link parameters · post-hoc calibration fitting (needs ≥100 resolved propositions) · Kalman tracking of live prices (needs a live feed; future work) · cellular automata and attractor dynamics (decorative) · backtesting with fill assumptions (Catalyst's layer, not ours).

---

## 12. Roadmap as PR stacks

Each stack's bottom PR is docs-only (spec + ADR) and merges first. Branch names carry the stack number: `<type>/<NN>-<slug>`.

| Stack | Branches (`<type>/<NN>-<slug>`; one per pull request) | Proves | Depends on | Status |
|-------|------|--------|-----------|--------|
| 00 | `docs/00-kickoff` | This document, `ARCHITECTURE.md`, decision records 0001–0011, the `spec/` book skeleton (landing page per idea) and vocabulary, research | — | **merged** — #1 |
| 01 | `docs/01-*`, `feat/01-*`, `chore/01-*` | Backend + frontend hello-world, Docker (dev + prod), CI, pre-commit, type generation | ADR-0002 accepted | **merged** — #2, #3, #6, #11 |
| 02 | `spec/02-*`, `feat/02-*` | Pydantic domain models → OpenAPI → TS types; the Hormuz fixture graph (base + "Iran struck" branch) | ADR-0003/0004/0005 accepted | **merged** — #5, #7, #10, #12 |
| 03a | `spec/03a-propagation-and-diff`, `feat/03a-apply`, `feat/03a-propagate`, `feat/03a-diff-and-routes` | Propagation, `do/observe/insert/retune`, patch algebra, locality, the diff, the sensitivity sweep, and the three world routes — pure, property-tested | 02 | **merged** — #18, #19, #24, #25 |
| 03b | `spec/03b-workbench`, `feat/03b-canvas`, `feat/03b-wires`, `feat/03b-diff-and-keys` | React Flow canvas: rich tiles, typed ports and wires, ELK layout, the stored example drawn whole, two worlds in one set of coordinates, the Inspector, the six edits, the keyboard | 02, ADR-0007 accepted | **merged** — #21, #22, #26, #27 |
| 04a | `*/04a-*` | The browser side: join the canvas to the engine — switch `ApiWorldSource` on, so every number that read as an absence fills in — then the map drawing itself claim by claim from a stream, with every refusal on screen and no spinner anywhere | 03a, 03b | **merged** |
| 04b | `*/04b-*` | The server side: the model pipeline (structured outputs, one proposal per call), the event stream, replay from a recorded generation, web-search grounding, recorded model answers, the provenance-derived spread on arrow strengths, evals on the four examples | 03a, ADR-0006/0008/0012 accepted | **merged** |
| 05 | `*/05-*` | **Sound numbers, then settled shapes.** A claim's number becomes the chance it happens by its deadline, solved exactly with the timing sampled; events and states in place of automatic retraction; the path product replaced by the shift, the joint and the weakest arrow; then one freeze of everything the model is asked, and one paid re-recording of all four examples | 04a, 04b, ADR-0016/0017/0021/0022 accepted | not started |
| 06 | `*/06-*` | **The trade.** Quotes recorded first and the edge read from the unsupposed world; the reader's position and the outcome distribution; *what takes you out* and *what to watch*; the thesis card, the export and the dock | 05, ADR-0010/0018/0019/0020 accepted | not started |
| 07 | `*/07-*` | **A map you can argue with, shown to be good.** Challenge an arrow; sessions served back by id (FR-31); the evidence a source actually carries | 06 | not started |

Stacks 03a and 03b ran in parallel on a shared schema, and both are merged (D11). **Stack 04 splits the same way, and for a plain reason: decision record 0009 capped a stack at four pull requests — "never deeper than four"** — and joining the canvas to the engine, streaming the map as it grows, the model pipeline, the event stream, replay and the evals do not fit in four. So 04a is the browser and 04b is the server, they share the event-stream shape the way 03a and 03b shared the schema, and neither waits on the other to start. *(The cap became **two** on 2026-09-21 — a docs-only pull request at the bottom and one code pull request on it, otherwise straight onto `main`; see the second amendment to decision record 0009. The history above is why stack 04 split, and is kept as written.)*

Status as of 2026-09-21; the numbers are pull requests on `kgang/katalyst`. A stack's branches carry its number, so one stack is several branches: stack 02 was `spec/02-graph-and-multiverse`, `feat/02-domain-models`, `feat/02-validity` and `feat/02-hormuz-fixture`, and each half of stack 03 carries its own letter. Four numbers need a word:

* **#11** — Docker (development and packaged), continuous integration, pre-commit and the Makefile — sat at the top of stack 01 and was merged into its parent branch rather than into `main`, so its work reached `main` inside **#6**'s squashed commit. `git log` on `main` shows no #11, and that is why.
* **#9** carried decision record 0012 on the branch `adr/02-replay-mode`. Accepted 2026-09-17; built in stack 04b (§13).
* **#17** carried decision record 0014 on the branch `adr/03-engine-rules` — how a supposition ends, and what the range on a computed number means. It is the gate stack 03a was written against rather than a member of either half, which is why it is in neither row above.
* **#20 and #23 do not exist.** Neither number resolves on GitHub and nothing was merged under either. Pull requests and issues share one counter, so a gap in the numbering is not a missing pull request.

---

## 13. Open questions

Dated so this section visibly ages. An answered question moves to the list below rather than disappearing, so the change stays visible.

*None open today.*

### Answered

- **2026-09-16, answered 2026-09-21:** Strategy export schema (FR-27) is `legs[] + conditions[]`. A venue's combination leg is an **order** format, and mirroring it would imply this document could be submitted somewhere; this product is not an execution layer. See `spec/thesis/card-and-export.md`.
- **Asked 2026-09-16, answered 2026-09-17.** Product name in the interface: **Katalyst**, the repository's own name. `/api/about` returns it and the status screen prints it.
- **Asked 2026-09-16, answered 2026-09-17.** Does the GitHub native stacked-PR preview work on `kgang/katalyst`? **Yes**, and stacks 01 and 02 were merged that way; `git-spice` was not needed. The command-line tool `gh` refuses to merge a stacked pull request and points at an asynchronous merge route instead; that route, and the one trap in it, are written down under *More Information* in decision record 0009.
- **Asked 2026-09-16, answered 2026-09-17.** Reflexive links (`market → world`, lag > 0): **schema in stack 02, propagation unscheduled.** The schema is built, and the stored Hormuz example carries such a link with a delay on it. *(Propagation was deferred to the old stack 06; the roadmap was renumbered on 2026-09-21 and nothing schedules it now.)*
- **Asked 2026-09-17, answered 2026-09-17.** Replay mode (FR-13) — a reviewer with no model key walks the hero flow on an example hypothesis, played from a committed generation transcript through the live event stream. Written down as decision record 0012 and accepted the same day; built in stack 04. **One recording is committed**, the Strait of Hormuz, and it is the whole hero flow: the map grows claim by claim, the refusals show, the receipt says it was a replay and cost nothing, and every intervention works afterwards at full fidelity. The other three example sentences say plainly that nothing is recorded for them; each is written by `make record-demo ONLY=<example>` when the owner chooses to pay for it.
- **Asked 2026-09-16, answered 2026-09-17 — and the question changed.** Ensemble size N for FR-8 — how many independent generations to reconcile into one map, and the cost of each — has no answer, because no map is reconciled against another and no generation is run twice. Decision record 0015 ships the range the model stated, labelled as stated, and refuses whole-map reconciliation outright: `spec/multiverse/diff.md` anti-pattern 4, *do not infer a difference by matching two maps*, is the warrant. What remains open is a different question, and it is asked of a measurement rather than of a number: **would re-asking a claim widen its range toward the truth?** FR-30's pastcast, read against the evaluation scorecard built in stack 04, is the test, and it is the one thing that reopens this. FR-8 is amended to match. *(2026-09-21, decision record 0021: FR-30 is not built in version one, so this condition cannot be met within version one and no ensemble is built. Record 0015 is unchanged; what it loses is its escape hatch.)*

---

*"The proof IS the decision. The mark IS the witness."* — every number here must be able to say why.
