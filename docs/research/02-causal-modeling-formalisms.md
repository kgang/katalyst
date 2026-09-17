# Causal-Chain Forecasting: Formalism Survey + Recommended Build

*Research report. No files written. All literature claims linked.*

---

## 1. Formalisms for causal chains with intervention semantics

The requirement "modify one node, re-propagate downstream" is exactly Pearl's rung 2 (`do(X=x)`: sever incoming edges, propagate to descendants only). Rung 3 (counterfactuals: "what would have happened") needs a *fully specified* SCM with exogenous noise terms you will not have. Build for rung 2; be honest that rung 3 is out of reach ([Pearl's causal hierarchy](https://www.emergentmind.com/topics/pearl-s-causal-hierarchy-pch)).

| Formalism | "Modify a node" | Tractable for LLM prototype? | Auditable | Fake-precision risk |
|---|---|---|---|---|
| **Pearl SCM + do-calculus** | Native: `do()` cuts parent edges | Semantics yes, identification math no (no data to identify from) | Very — graph *is* the argument | Low, if you don't claim identification |
| **Discrete Bayes net (full CPTs)** | Set evidence, re-infer | ✗ — 2^k elicitation per node; LLM invents numbers | Table is unreadable at k>3 | **High** |
| **Bayes net w/ noisy-OR / log-odds aggregation** | Recompute child logit | ✓✓ **Best fit** — O(parents) numbers | Each edge = one number + one rationale | Medium, manageable |
| **Influence diagrams** | Add decision + utility nodes | ✓ as a thin layer on the above (terminal payoff nodes) | ✓ | Low |
| **Scenario/decision trees** | Prune/regraft a subtree | ✓ but explodes; no shared downstream nodes | Very readable | Low, but coverage is a lie (branches never sum to reality) |
| **Monte Carlo over distributions (Squiggle/Guesstimate)** | Change a distribution, resample | ✓✓ — this is your *execution engine* ([Squiggle](https://www.squiggle-language.com/), [Squiggle AI](https://www.lesswrong.com/posts/7worWgggeHL3Eb7wq/introducing-squiggle-ai)) | ✓ if every distribution has a source | Medium — pretty histograms from invented parameters |
| **Markov chains / steady state** | Change transition matrix | Steady states are the **wrong question** — these events are one-shot and non-ergodic | — | **High** (stationarity is a fiction here) |
| **Dynamic Bayes net (time-unrolled DAG)** | Same as BN, per time slice | ✓ — the *legitimate* form of the founder's Markov idea; also how you legalize feedback loops | ✓ | Low |
| **Agent-based / LLM role-play sim** | Change an agent's beliefs | ✗ for v1 — no validation story, high variance, expensive | ✗ (black box) | **Very high** |
| **"LLM-as-simulator" (freeform narration)** | Re-prompt | ✓ trivially, but nothing is held fixed between branches | ✗ | **Very high** |

**Recommendation: a DAG of resolvable propositions with logistic/noisy-OR edge aggregation, executed by forward Monte Carlo, with `do()` semantics for interventions.** It is a Bayesian network you *sample* rather than solve — which means conditioning ("observe" rather than "intervene") comes free via rejection sampling, and every number stays attached to one edge a human can argue with.

The single most honest feature you can ship: **distinguish `do()` from `observe()` in the UI.** "Hormuz opens" asserted as a hypothesis is `do()` — don't update its parents. "Hormuz opened" as news is `observe()` — it *should* update "a US–Iran deal happened," which changes other downstream nodes. Most competing tools silently conflate these.

---

## 2. LLM forecasting literature: what actually works

**Halawi et al. 2024, "Approaching Human-Level Forecasting with LMs"** ([arXiv:2402.18563](https://arxiv.org/abs/2402.18563), [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2024/file/5a5acfd0876c940d81619c1dc60e7748-Paper-Conference.pdf)) — retrieval (LM query expansion → relevance ranking → summarization) + reasoning + ensembling. System Brier-competitive with the crowd on a post-cutoff test set; RMS calibration error .42 vs crowd .38. It *approaches*, not beats. The retrieval pipeline is the load-bearing part.

**AIA Forecaster (Nov 2025)** ([arXiv:2511.07678](https://arxiv.org/pdf/2511.07678)) — the current recipe: news retrieval → multiple base-model forecasts → **adversarial critique** (generate counterarguments to reduce overconfidence) → **ensembling** → **statistical calibration** (Platt scaling). Reports performance statistically indistinguishable from superforecasters on ForecastBench. Its own finding: *single-run performance is noisier and worse than simple averaging over a few independent generations.* Ensembling is not optional.

**Metaculus AI Benchmark** ([tournament](https://www.metaculus.com/aib/), [Q2 2025 results](https://www.lesswrong.com/posts/Surnjh8A4WjgtQTkZ/q2-ai-benchmark-results-pros-maintain-clear-lead)) — Pro forecasters still beat the top-10 bot team at p≈1e-5; bots beat the median member of the public. Recent bots land top ~3–5% of human field in Metaculus Cups ([2026 roundup](https://forum.effectivealtruism.org/posts/Spyz3wESZu2eeqhDj/ai-forecasting-in-2026-what-11-analyses-say)). Naive extrapolation puts bots past Pros ~2027. Translation: **your edge is not raw probability accuracy — it's structure, auditability, and instrument mapping.**

**Paleka et al., ICLR 2025, "Consistency Checks for LM Forecasters"** ([arXiv:2412.18544](https://arxiv.org/abs/2412.18544)) — LLM forecasters are *logically incoherent* (P(A) and P(¬A) both high; violations of Cond, AndOr, ExpEvidence). Their arbitrage-based consistency metric correlates with ground-truth Brier. **This is free QA for your product**: your graph gives you consistency constraints for nothing, and you can score a chain before any event resolves.

**LLM causal discovery** ([IJCAI 2025 survey](https://www.ijcai.org/proceedings/2025/1186.pdf)) — LLMs are decent at *proposing* edges from domain knowledge, unstable at *asserting* them: run-to-run inconsistency, no grounding/attribution, and results plausibly reflect memorization of documented relationships. There's a 2025 paper literally titled ["LLM Cannot Discover Causality, and Should Be Restricted to Non-Decisional Support in Causal Discovery"](https://arxiv.org/pdf/2506.00844). Design accordingly: **LLM proposes, human disposes, evidence adjudicates.**

**Known hype:** LLM agent societies as forecasters. [AgentSociety](https://arxiv.org/abs/2502.08691) and commercial voter-sim products (Aaru Dynamo) are impressive engineering with thin public validation ([survey of the space](https://arxiv.org/pdf/2507.19364) flags inconsistency and authoritative-sounding hallucination as unresolved). Don't build a simulated society in two weeks.

**Verdict on what improves calibration, ranked by ROI:** (1) retrieval of recent news, (2) ensembling ≥5 independent runs, (3) explicit reference-class/base-rate elicitation before the inside view, (4) adversarial critique pass, (5) post-hoc Platt/isotonic calibration *once you have ≥100 resolved questions* (not on day one — it's fitting noise), (6) decomposition into sub-questions — helps comprehension and auditability more than measured accuracy; treat as UX, not magic.

---

## 3. Recommended data model

```ts
type Prob = { p: number; lo?: number; hi?: number };   // subjective, with an honest interval
type Shape = "impulse" | "step" | "ramp";              // Dirac vs Heaviside vs gradual

interface EventNode {
  id: string;
  claim: string;                  // a RESOLVABLE proposition, not a vibe
  resolution: { criteria: string; source: string; by: ISODate };
  kind: "hypothesis" | "event" | "market";
  prior: Prob;                                        // marginal, before parents
  baseRate?: { refClass: string; k: number; n: number; sources: Url[] };
  evidence: { claim: string; url: Url; direction: +1|-1; weight: number }[];
  payoff?: PayoffSpec;                                // market nodes only
}

interface CausalEdge {
  from: string; to: string;
  mode: "trigger" | "sustain";    // horizontal (domino) vs vertical (desk holds apple)
  strength: number;               // Δ log-odds on child when parent is TRUE
  lag: Duration; shape: Shape; halfLife?: Duration;   // impulse decay
  rationale: string; sources: Url[];
  confidence: "speculative" | "argued" | "documented";
  reflexive?: boolean;            // market → world feedback; must have lag > 0
}

// child aggregation, O(parents) to elicit, O(parents) to explain:
// logit P(child @ t) = logit(prior) + Σ_active edge.strength · shape(t − t_parent)

type Intervention =
  | { op: "do";      node: string; value: boolean; at?: ISODate }   // cuts in-edges
  | { op: "observe"; node: string; value: boolean }                 // updates parents too
  | { op: "insert";  node: EventNode; edges: CausalEdge[] }         // "...BUT X happens"
  | { op: "retune";  edge: string; strength: number }
  | { op: "refine";  node: string; into: EventNode[];               // resolution refinement
                     reconcile: "must-marginalize-to-parent" };

interface Branch { id: string; parent?: string; label: string;
                   interventions: Intervention[]; }   // a branch IS a diff; compose by concat
```

**Why this shape:** a branch is an ordered patch list, so branches compose, replay, diff, and share the base graph. Every probability is either (a) a prior with a base rate and sources, or (b) derived from edges each carrying one number plus a rationale. There is no place to hide an unsourced number.

### Worked example: Hormuz

```
H  "Strait of Hormuz reopens to unrestricted commercial transit for ≥14 consecutive days"
   resolves: IMO/Lloyd's List transit counts, by 2026-11-01 | prior .35
   baseRate: "closure/disruption episodes ending within 90d", 7/9 historically
   evidence: [Omani mediation reported (+, .3, url), 3 tankers still held (−, .4, url)]

H →(trigger, Δlogit −1.6, lag 2d, impulse, halfLife 30d, "war-risk premium unwinds")→ B  "Brent < $68 for 5 sessions"
H →(sustain, Δlogit −1.1, lag 0, step, "insurers reprice only while lane stays open")→ C  "Lloyd's war-risk premium for Gulf transits < 0.4%"
C →(sustain, Δlogit −0.7, lag 7d, step)→ B
B →(trigger, Δlogit +0.9, lag 1d, impulse)→ M1 "Polymarket 'Brent<$70 on Oct 31' resolves YES"
B →(trigger, Δlogit −0.8, lag 3d, ramp)→ M2 "XLE underperforms SPY by >3% over 20d"
B →(trigger, Δlogit +0.6, lag 14d, ramp, reflexive)→ R  "OPEC+ announces output restraint"   // market reacts back
R →(trigger, Δlogit +1.2, lag 5d, step)→ ¬B                                                  // closes the loop, legal because lag>0
```

**Intervention: "Hormuz opens BUT Iran is struck the next day."**

```ts
branch("hormuz-then-strike", [
  { op: "do", node: "H", value: true, at: "2026-10-01" },
  { op: "insert",
    node: { id:"S", claim:"Confirmed kinetic strike on Iranian territory by US or Israel",
            resolution:{criteria:"≥2 of AP/Reuters/AFP", source:"newswire", by:"2026-10-02"},
            kind:"event", prior:{p:0.06} },
    edges: [
      { from:"S", to:"B", mode:"trigger", strength:+2.4, lag:"0d", shape:"impulse", halfLife:"10d",
        rationale:"strike restores risk premium faster than transit data removes it", confidence:"argued" },
      { from:"S", to:"C", mode:"sustain",  strength:+2.0, lag:"1d", shape:"step",
        rationale:"underwriters reprice on threat, not on transit counts" },
      { from:"S", to:"H", mode:"sustain",  strength:−1.9, lag:"3d", shape:"step",
        rationale:"reopening is sustained by absence of hostilities, not by the opening event" } ]},
  { op:"do", node:"S", value:true, at:"2026-10-02" }
]);
```

The `mode` field does real work here. `S → H` is `sustain`: knocking it out **retracts** H going forward even though `do(H)` fired — the apple falls when the desk is removed. `H → B` is `trigger` with an impulse that already fired and decays — the domino stays fallen; removing H later does *not* un-fall B. This is precisely the founder's "an earlier cause can be undone without changing the effect," and it's ~30 lines of propagation code.

Output: `P(M1)` drops from .61 → .18; `P(M2)` .54 → .09; and a new terminal appears where the *original* thesis is maximally wrong — which is the stop-loss (§5).

---

## 4. Founder's ideas: build, bend, or bin

| Idea | Verdict | Implementable form |
|---|---|---|
| **Vertical vs horizontal causality** | **Build — best idea in the notes** | `mode: trigger \| sustain`; changes retraction semantics on intervention |
| **Heaviside/Dirac vs continuous** | **Build, cheap** | `shape` + `lag` + `halfLife` on every edge; makes timing errors visible |
| **Actuarial / "getting wiped out"** | **Build** | Report payoff *distribution*: CVaR₅, max drawdown, P(ruin) — **never** an EV headline alone |
| **Resolution refinement (compositionality)** | **Build** | `refine` op: expand node → sub-nodes; enforce that children marginalize back to the parent (this is Paleka's consistency check, internalized) |
| **Iterative refinement (Newton)** | **Build** | Generate → adversarial critique → re-estimate, loop until Δp < ε or consistency violations clear. Literally the AIA Forecaster loop |
| **Markets react to positions (reflexivity)** | **Build, constrained** | `reflexive: true` edges with mandatory `lag > 0`; time-unroll the graph so cycles become a DBN |
| **Markov matrices** | **Bend** | Yes as time-unrolled DBN; **no** as steady-state/stationary distribution — these events are one-shot and non-ergodic |
| **LLM agents role-playing entities** | **Bend — narrow use** | Not as outcome simulators. As *red-team personas* ("Iranian regime", "Lloyd's underwriter", "OPEC desk") that propose **missing nodes and edges** the graph lacks. Hypothesis diversity, not simulation |
| **Category theory** | **Bend** | Keep the content (refinement must reconcile with the coarse estimate); drop the vocabulary — it buys nothing in code |
| **Kalman filters** | **Future work** | Real use: tracking your live node probability against the market price as a noisy measurement. Needs a live feed you won't have in week 1 |
| **Chaotic attractors** | **Decorative** | No estimable dynamical system here. Useful only as narrative framing for "regimes." Cut |
| **Cellular automata** | **Decorative** | No mapping from simple local rules to Brent. Cut |

---

## 5. Terminal nodes → tradeable thesis

The chain must end in a **market node** whose claim is an instrument, not a story: a ticker + direction + horizon, a Polymarket/Kalshi contract ID, or a commodity level.

**Derive the stop-loss mechanically.** Run one-at-a-time flips (`do(n=¬n)`) across every node; record Δ in terminal payoff. The **invalidation node** is the one with the largest adverse swing *subject to two filters*: (a) it resolves **before** the terminal node, (b) it is **publicly observable** (a newswire, a price, a filing). A sensitive-but-unobservable node is a risk you cannot trade against — surface it separately as "unhedgeable."

**Price it against the crowd.** Pull the live prediction-market price for every market node. Your thesis exists only in the gap between your model's implied probability and the quoted price. This also buys you a free calibration harness — every node you create is a question that later resolves, so you can score yourself on Brier/ECE without building a benchmark.

```ts
interface ThesisCard {
  hypothesis: string; horizon: ISODate;
  legs: { instrument: string; direction: "long"|"short"; size: "core"|"satellite";
          drivenBy: NodeId; modelP: number; marketP: number; edgeBps: number }[];
  entry:       { whenNodesTrue: NodeId[]; priceCondition?: string };
  invalidation:{ node: NodeId; flipsTo: boolean; observableVia: string;
                 expectedBy: ISODate; deltaPnL: number };   // ← the stop-loss
  takeProfit:  { node: NodeId; observableVia: string };
  distribution:{ ev: number; p10: number; p50: number; p90: number;
                 cvar5: number; maxDrawdown: number; pRuin: number };
  tails:       { node: NodeId; p: number; pnl: number; hedge?: string }[];  // black swans, listed not averaged
  caveats:     { unhedgeableSensitivities: NodeId[]; crowding: string;
                 weakestEdges: EdgeId[] };                  // lowest-confidence, highest-|strength|
}
```

The **tails** field is the actuarial idea earning its keep: low-probability, high-magnitude branches get their own row with a suggested hedge, instead of being averaged into an EV that hides them.

---

## 6. What I'd actually build in 1–2 weeks

**Week 1 — the engine.** Schema above in TypeScript + Zod. Graph generation with Claude Opus 5 (`claude-opus-5`) using **structured outputs** — `output_config: { format: {...} }`, and `strict: true` on any tool definitions; not the deprecated `output_format`. `thinking: { type: "adaptive" }` (no `budget_tokens` — it's a 400 on Opus 5), `output_config.effort: "high"`, and **prompt caching** on the stable system prompt + retrieved evidence corpus (keep timestamps *after* the last breakpoint or you'll silently never cache; verify via `usage.cache_read_input_tokens`). Forward Monte Carlo, 10k samples, in plain TS — no PGM library. `do`/`observe`/`insert`/`retune` ops. Rejection sampling for `observe` (warn loudly below ~2% acceptance). One-at-a-time sensitivity sweep — send it through the **Batch API at 50% cost**.

**Week 2 — the judgment.** Evidence retrieval via the `web_search_20260209` server tool (don't also declare `code_execution`; it's built in). Ensemble of 5 independent graph generations, reconciled into one graph with disagreement surfaced as edge confidence. Adversarial-critique pass. Base-rate elicitation forced *before* the inside view. Market-price anchoring on terminal nodes. Thesis card + branch-tree UI.

**Explicitly deferred:** agent societies, Kalman filters, learned edge parameters, full CPTs, post-hoc calibration fitting (you won't have the ≥100 resolved questions it needs), chaotic dynamics, cellular automata.

**The two things that will make or break the demo** are not modeling choices: every node must be a *resolvable* proposition with a named adjudicator (otherwise the graph is unfalsifiable poetry), and every probability must be one click from its rationale, sources, and base rate. Precision beyond two significant figures on any elicited number is a lie — render `.35`, never `.347`, and render the interval next to it.
