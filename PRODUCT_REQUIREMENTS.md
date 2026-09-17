# PRODUCT_REQUIREMENTS.md — Katalyst

> A causal-chain workbench for finance. You state a hypothesis; it builds an auditable graph of downstream events toward tradeable effects; you bend any link and watch the multiverse re-propagate; it ends in a thesis with a stop-loss you can name.

**Status:** living document (L1.11: there is no shipping, only current state). **Owner:** Kent Gang. **Reader:** the Catalyst team (see §2). **Derived from:** `ASSIGNMENT.md`, `docs/initial-brainstorming.md`, `docs/research/*`, and the 2026-09-16 interview (§3). **Governed by:** `AGENTS.md`. **Companions:** `ARCHITECTURE.md` (how the system is shaped — the technical counterpart to this document), `docs/adr/` (numbered decision records — a journal), `spec/` (the detailed spec, organized as a book by idea).

---

## 1. What this is, in one screen

**The hero use case, in one sentence.** You type an event you think will happen. Katalyst shows what it would cause, step by step, ending in trades — and lets you change any step to see how the trades change.

**Input.** "The Strait of Hormuz is going to open next week." Optionally, a destination: "does that get me to Brent under $70?" Optionally, how likely *you* think it is — or "I don't know."

**Output.** A map of cause and effect. Each box is a claim that can be checked by a date ("Brent closes under $70 by Nov 1, per ICE settlement"). Each box shows how likely it is as three numbers side by side: what the model thinks, what you think, and what the market is pricing. Each arrow states the mechanism, how strongly it pushes, and how long it takes. The map draws itself as the model reasons. It ends in things you can trade: a ticker, a contract, a commodity price.

**The move.** Click any box and change it: "…but Iran is struck the next day." The original map is kept. A new version forks off. Only the boxes downstream of your change update. A faded overlay shows exactly what moved. Do this as often as you like and compare versions.

**The finale.** A thesis card: what to buy or sell, when to enter, the one event that would prove the idea wrong (that is your stop-loss), the event that means take profit, and the rare disasters listed one by one rather than hidden inside an average. Exportable in a form a trading system can read.

**Two doors, one map.** *Explore:* "Hormuz opens — what happens next, and what can I trade?" *Verify:* "Does Hormuz opening actually lead to cheaper oil — and where is that chain weakest?" Same map. Verify adds a destination, so the map grows toward it and grades every step. Explore is the first screen; Verify is one extra field, not a second product.

**What it is not.** Not a chatbot with a diagram attached. Not an oracle: it lays out an argument, and every number can show why. Not a swarm of simulated agents. Not a place to execute trades.

---

## 2. Who reads this, and what "good" means to them

Catalyst (`catalyst.app`) is 4–5 engineers from Jane Street / DRW / Citadel / Jump, seed-funded by Sequoia and Jump, already shipping natural-language → backtest → execution with a custom query language. They sit *downstream* of this tool. They will not be impressed by another front door to an LLM; they will be impressed by a tool that turns a vague belief into something with a venue, a strike, an entry, a stop, and a falsifiability test — and does so honestly.

The brief names three wants: **(a)** how black-swan events affect risk, **(b)** which events trigger stop-loss / take-profit, **(c)** whether a hypothesized event actually leads to the desired financial effect. Each maps to a first-class surface below: the *Tail strip* (a), *Invalidation derivation* (b), *Verify door + conjunctive honesty bar* (c).

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
| **Proposition** (node) | A *resolvable* claim: criteria, adjudicating source, resolve-by date. Kinds: `hypothesis`, `event`, `market` (instrument-bearing terminal) |
| **Link** (edge) | A causal claim from one proposition to another: `mode` (`trigger` — domino, fires once, decays; `sustain` — desk-holds-apple, effect retracts if cause is removed), `strength` (how much it shifts the odds of the next proposition; on a log-odds scale so several links add up), `lag`, `shape` (`impulse` \| `step` \| `ramp`), `half_life`, `rationale`, `sources`, `provenance` |
| **Provenance** | Where a number or link came from: `asserted` (model, no evidence) · `argued` (model + mechanism) · `documented` (cited sources) · `market_implied` (live price) · `historical` (event study) · `user` · `simulated` (probe) |
| **Belief** | A probability with an honest interval `{p, lo, hi}` and an owner: `model` \| `user` \| `market`. The three are never merged |
| **Graph** | Propositions and links with no loops (a directed acyclic graph). Loops are legal only through `reflexive` links — a market feeding back on the world — which must have a delay and unroll over time |
| **Intervention** | One of `do` (assert; cut parents), `observe` (learn; update parents too), `insert` (add a proposition + links), `retune` (change a link), `refine` (expand a proposition into sub-propositions that must marginalize back), `believe` (record the user's own belief on a proposition; shown beside the model's, not propagated in v1) |
| **Branch** | A named, ordered list of interventions over a base graph. A branch *is* a patch; branches compose by concatenation |
| **World** | A base graph with a branch applied and beliefs propagated. The base world is a branch with zero interventions |
| **Diff** | The structural and belief delta between two worlds: `unchanged` / `shifted` / `added` / `killed` per node, plus ranked terminal deltas |
| **Probe** (stretch) | Extra compute attached to one proposition: thousands of random simulations (Monte Carlo), a small probability model (Bayesian sub-net), or role-played experts hunting for gaps (persona red-team). Output re-enters the graph as a `simulated` belief |
| **Thesis** | The compiled trade: legs, entry, invalidation node, take-profit node, distribution, tails, caveats |

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
     │      "falsified if", conjunctive product of the path from the hypothesis
     ▼
 Intervene ─▶ "…but Iran is struck the next day" ⇒ branch forks, downstream re-propagates,
     │        ghost overlay + delta rail + one-line diff.  A ⇄ A′ on one key.
     ▼
 Drill down (stretch) ─▶ attach a probe where the thesis is most sensitive
     │
     ▼
 Thesis ─▶ card + live prices + export.  Invalidation node is derived, not typed.
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
- **FR-8 (P1)** Ensemble: N independent generations reconciled into one graph; run-to-run disagreement surfaces as link confidence.
- **FR-9 (P1)** Adversarial critique pass before beliefs are final. **(P2)** Persona red-teams ("Lloyd's underwriter", "OPEC desk") that propose *missing* propositions and links — hypothesis diversity, not outcome simulation.

### 6.3 Audit
- **FR-10 (P0)** Inspector (a panel, never a modal) for any proposition or link: rationale, sources, base rate and reference class, the three beliefs, "falsified if", resolution criteria.
- **FR-11 (P0)** Conjunctive honesty bar: for any path from the hypothesis to a selected proposition, show the product of link probabilities beside the narrative headline (INV-8).
- **FR-12 (P0)** Provenance is visibly encoded on every link and belief chip (INV-2, UX-6).
- **FR-13 (P0)** Replay: any world is reproducible from `(base graph id, branch, seed)`. Generation transcripts are stored with the graph.

### 6.4 Multiverse
- **FR-14 (P0)** Interventions `do`, `observe`, `insert`, `retune`, `believe` on any proposition; committing one forks a branch implicitly; the base world is immutable (INV-5).
- **FR-15 (P0)** Re-propagation is local: only the intervened proposition and its descendants change; `sustain` links retract, `trigger` links do not (INV-4).
- **FR-16 (P0)** Diff: ghost overlay of A under A′ in a shared union layout; delta rail of terminal changes ranked by |Δ| × confidence; one-line natural-language diff.
- **FR-17 (P1)** Compare ≥3 branches as small multiples; at most 4 branches visible, rest collapsed to a list; branches must be named.
- **FR-18 (P1)** `refine`: expand a proposition into sub-propositions; the children's combined likelihood must equal the parent's — they marginalize back (INV-10). This is the brainstorm's "search deeper lines".

### 6.5 Sensitivity and drill-down
- **FR-19 (P1)** Sensitivity sweep: one-at-a-time flips of every proposition, ranking by adverse Δ on each terminal. Feeds FR-23 and FR-21.
- **FR-20 (P2)** Probes: attach a Monte Carlo, a Bayesian sub-net, or a persona red-team to one proposition; results re-enter as `simulated` beliefs with their own provenance and rationale.
- **FR-21 (P2)** "Where to spend modeling budget": rank propositions by value of information (sensitivity × width of interval) and say so in the UI.

### 6.6 Risk
- **FR-22 (P0)** Tail strip: low-probability / high-magnitude propositions listed in a fixed strip with p, PnL, and a suggested hedge — never averaged into an expected value.
- **FR-23 (P0)** Invalidation derivation: the stop-loss is the proposition whose flip most damages the terminal, filtered to those that resolve *before* the terminal and are *publicly observable*. Take-profit is the symmetric case. Sensitive-but-unobservable propositions are listed as *unhedgeable*.
- **FR-24 (P1)** Payoff distribution from thousands of random simulations: the 10th / 50th / 90th-percentile outcomes, the average loss in the worst 5% of runs (CVaR₅), the largest peak-to-trough loss, and the chance of being wiped out. The actuarial "wiped out" case gets its own row.

### 6.7 Thesis
- **FR-25 (P0)** Thesis card: hypothesis, horizon, legs (instrument, direction, size, driving proposition, model p, market p, edge), entry, invalidation, take-profit, distribution (P1), tails, caveats (weakest links, unhedgeable sensitivities, crowding).
- **FR-26 (P1)** Live read-only prices: Polymarket first, FRED second, Kalshi third. Shown beside model and user beliefs as the `market` belief. Cross-venue disagreement is surfaced, not averaged. FRED data renders the required attribution line ("This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis").
- **FR-27 (P1)** Strategy export: a declarative JSON document (schema in `spec/thesis/`) with legs, conditions, and the graph references that justify each — the shape a downstream trading agent could ingest.

### 6.8 Grounding
- **FR-28 (P1)** Evidence retrieval at generation time (server-side web search); sources attach to links with direction and weight.
- **FR-29 (P2)** Historical-analog panel: for a link, past instances and how prices moved around them, with an uncertainty band (an event study).
- **FR-30 (P2)** Pastcast self-test: run a chain on a resolved 2024–25 event with a date-frozen corpus and show the Brier score (the standard accuracy score for probability forecasts; lower is better), including when it is bad.

### 6.9 Persistence and sharing
- **FR-31 (P0)** Sessions (graph + branches + transcripts) persist to a single SQLite file (a one-file database, no server) and are addressable by URL. No accounts in v1.

---

## 7. UI/UX requirements — the *Workbench*

The direction is D3. The research's "Instrument" craft rules (typography, color, motion) still apply; the *shell* is a workbench, not a terminal.

- **UX-1 Node tiles are rich.** A proposition renders as a card with: claim, kind silhouette, belief chips (model | user | market) as a three-up, a density sparkline when quantitative, evidence clippings (source favicon + one line), and the resolve-by date. Fixed width, clamped height, 8px grid. Detail lives in the Inspector, not the tile.
- **UX-2 Ports and wires are typed.** Propositions have input and output ports; a link is a wire whose *stroke* encodes signal shape (impulse: dot-dash; step: solid; ramp: gradient) and whose *weight* encodes |strength|; `sustain` wires are double-stroked; `reflexive` wires loop with a visible lag chip. The midpoint chip shows the conditional probability in the Metaculus arrow-and-bar idiom.
- **UX-3 World state is visible.** A strip shows the terminal instruments as gauges (Brent, a basket, a contract) with their model | user | market readings, re-ticking on intervention. Time is a scrubbable axis; lags are real distances.
- **UX-4 Level of detail by zoom.** Far: worlds and their terminal deltas. Mid: wiring and belief chips. Near: the full tile with evidence. Text never shrinks below 11px; the tile changes representation instead.
- **UX-5 Organizability.** Users can pin, group, and annotate tiles (mood-board affordance); automatic layered layout (the ELK library, left→right) is the default and re-layout preserves the focused tile's screen position. Dragging is either fully supported or absent — never half.
- **UX-6 Color is law.** Probability → luminance/opacity. Direction of financial effect → blue ▲ / amber ▼, always with glyph and sign, never red/green. Branch identity → a small ordered palette on lanes and chips only. Tail risk → hatch texture, not hue. Provenance → stroke style (`asserted` dashed). No information in hue alone (INV-12).
- **UX-7 Motion budget.** Three animations: propagation wave (wires draw in causal order, ~200ms staggered), branch creation, belief number-roll. Everything else ≤120ms opacity. `prefers-reduced-motion` keeps ordering and drops tweening.
- **UX-8 Streaming is the loading state.** No spinner. Skeleton tiles appear at their layer, claims stream in, wires draw, chips resolve last. Reasoning arrives as it is produced.
- **UX-9 Keyboard first.** `⌘K` palette; `j/k` siblings; `h/l` layers along wires; `E` intervene; `B` branch; `Space` A⇄A′; `?` sheet. Focus is always visible.
- **UX-10 No modals.** One persistent Inspector; confirmations are undoable toasts.
- **UX-11 Typography.** One UI face and one tabular-figures mono for every number; three sizes, three weights; hierarchy by color and spacing. Not the component library's defaults.
- **UX-12 Themes and access.** Dark-first, light verified, semantic tokens. All text and glyphs ≥4.5:1. The graph also exists as an outline (`role="tree"`) with a screen-reader announcement (`aria-live`) when a branch re-propagates.
- **UX-13 Empty and edge states.** Launchpad (FR-3); `no_path` verdict as a first-class card; "not tradeable — because…" terminal as a first-class card.

---

## 8. Non-functional requirements

- **NFR-1 Honesty.** Beliefs render at two significant figures with their interval (`.35 (.2–.5)`), never `.347`. Every number is one click from rationale, sources, base rate.
- **NFR-2 Determinism.** Propagation is pure and seeded; the same `(graph, branch, seed)` yields byte-identical worlds.
- **NFR-3 Tests.** The core graph code is property-tested (the Hypothesis library generates thousands of random graphs and shrinks any failure to a minimal example) against the invariants in §9; the model boundary is tested with recorded API responses ("cassettes") committed to the repo; evals run out-of-band on the four assignment examples. CI is green with no API key (INV-13).
- **NFR-4 Docker.** `docker compose up` yields a working app; `docker compose watch` gives hot reload for both halves; a production-ish compose builds slim images with healthchecks. No database service in v1.
- **NFR-5 Legibility.** Every architectural decision is a numbered decision record; every feature with invariants has a spec; every PR names the invariant it satisfies; conventional commits with `spec:` and `adr:` types.
- **NFR-6 Cost visibility.** Each generation records model, tokens, cache hits, and dollars; shown in the Inspector's transcript view.
- **NFR-7 Performance.** 60 tiles render and re-layout in <100ms on a laptop; streaming first-paint within 1s of the first token.
- **NFR-8 Secrets.** One `.env.example`; keys read once via settings; a secret scanner (`gitleaks`) runs before every commit; recorded API responses are scrubbed of keys.

---

## 9. Invariants

Phrased as checkable statements. Each names the spec that owns it; specs name the property test. If an invariant cannot name a test strategy, it is a wish and belongs in §6.

| ID | Invariant | Owner |
|----|-----------|-------|
| INV-1 | **Checkable.** Every proposition has resolution criteria, a named adjudicating source, and a resolve-by date | `spec/graph/` |
| INV-2 | **Says why.** Every link has a rationale and a provenance; a link that claims evidence (documented, historical, or market-implied) carries at least one source. Every belief has an owner | `spec/graph/` |
| INV-3 | **Assert is not observe.** Asserting a proposition (`do`) changes nothing upstream of it; observing it (`observe`) may. Two operations, two verbs in the interface | `spec/multiverse/` |
| INV-4 | **Locality.** After an intervention on a proposition, everything that is not that proposition or downstream of it is byte-identical between the base and the branch | `spec/multiverse/` |
| INV-5 | **Branches are patches.** The base graph is never modified. A branch is an ordered list of interventions. Applying an empty branch changes nothing; applying two branches in sequence equals applying their concatenation. Every world replays exactly from (base, branch, seed) | `spec/multiverse/` |
| INV-6 | **No loops.** Ignoring *reflexive* links (a market feeding back on the world), the graph has no cycles; every reflexive link carries a delay greater than zero | `spec/graph/` |
| INV-7 | **Honest numbers.** Every belief satisfies 0 ≤ low ≤ p ≤ high ≤ 1 after any sequence of interventions, and is rendered at two significant figures with its range | `spec/graph/`, `spec/workbench/` |
| INV-8 | **Chains multiply.** Any displayed path shows the product of its link probabilities beside the narrative headline | `spec/workbench/` |
| INV-9 | **Ends in a trade.** Every graph has at least one tradeable terminal, or an explicit "not tradeable — because…" terminal | `spec/graph/` |
| INV-10 | **Refinement adds up.** After a proposition is split into finer sub-propositions, their combined likelihood equals the original's within a small tolerance | `spec/multiverse/` |
| INV-11 | **Three voices.** Model, user, and market beliefs are stored and rendered separately; no code path averages them | `spec/graph/`, `spec/workbench/` |
| INV-12 | **Not by color alone.** Every direction has a glyph, every tail a texture, every provenance a stroke style | `spec/workbench/` |
| INV-13 | **Keyless CI.** Continuous integration runs with no model API key; the model boundary is exercised only through recorded responses | `spec/generation/` |
| INV-14 | **A stop you can see.** The invalidation proposition resolves before its terminal and is publicly observable; otherwise it is listed as unhedgeable, never used as a stop | `spec/thesis/` |

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
11. Do not type the stop-loss by hand — derive it from sensitivity (FR-23) and show the derivation.
12. Do not put a database, auth, or multi-tenancy in v1 — three failure modes and zero value to the reader. SQLite file on a volume.
13. Do not implement against a `proposed` decision record (D9).

---

## 11. Non-goals (v1)

Execution and order routing · accounts and multi-user · agent-society simulation · learned link parameters · post-hoc calibration fitting (needs ≥100 resolved propositions) · Kalman tracking of live prices (needs a live feed; future work) · cellular automata and attractor dynamics (decorative) · backtesting with fill assumptions (Catalyst's layer, not ours).

---

## 12. Roadmap as PR stacks

Each stack's bottom PR is docs-only (spec + ADR) and merges first. Branch names carry the stack number: `<type>/<NN>-<slug>`.

| Stack | Name | Proves | Depends on |
|-------|------|--------|-----------|
| 00 | `docs/00-kickoff` | This document, `ARCHITECTURE.md`, decision records 0001–0011, the `spec/` book skeleton (landing page per idea) and vocabulary, research | — |
| 01 | `feat/01-skeleton` | Backend + frontend hello-world, Docker (dev + prod), CI, pre-commit, type generation | ADR-0002 accepted |
| 02 | `feat/02-schema` | Pydantic domain models → OpenAPI → TS types; the Hormuz fixture graph (base + "Iran struck" branch) | ADR-0003/0004/0005 accepted |
| 03a | `feat/03-engine` | Propagation, `do/observe/insert/retune`, patch algebra, locality, sensitivity sweep — pure, property-tested | 02 |
| 03b | `feat/03-canvas` | React Flow canvas: rich tiles, typed ports/wires, ELK layout, streaming from fixture, ghost diff, Inspector | 02, ADR-0007 accepted |
| 04 | `feat/04-generation` | LLM engine: structured outputs, SSE streaming, web-search grounding, cassettes, evals on the four examples | 03a, 03b, ADR-0006/0008 accepted |
| 05 | `feat/05-thesis` | Tail strip, invalidation derivation, thesis card, Polymarket + FRED adapters, strategy export | 04, ADR-0010 accepted |
| 06 | `feat/06-probes` | `refine`, Monte Carlo distribution, probes, value-of-information ranking | 05 |

Stacks 03a and 03b run in parallel (D11).

---

## 13. Open questions

Dated so this section visibly ages.

- **2026-09-16** Product name in the UI: "Katalyst" (repo) or something else? Owner's call.
- **2026-09-16** Does the GitHub native stacked-PR preview work on `kgang/katalyst`? Verify before stack 01; fall back to `git-spice` (ADR-0009).
- **2026-09-16** Strategy export schema (FR-27): mirror Polymarket negative-risk / Kalshi combo leg structure, or a simpler `legs[] + conditions[]`? Decide in the strategy-export chapter of `spec/thesis/`.
- **2026-09-16** Reflexive links (`market → world`, lag > 0): in v1 engine, or documented and deferred to stack 06? Leaning: schema in 02, propagation in 06.
- **2026-09-16** Ensemble size N for FR-8 and its cost per generation. Measure in stack 04.

---

*"The proof IS the decision. The mark IS the witness."* — every number here must be able to say why.
