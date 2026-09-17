# Validity — what makes a map valid, and why we reject rather than repair

## Purpose

A language model writes most of the map. *Map* and *graph* mean the same thing throughout: `Graph` is the type's name, *map* is what the user sees. Models are useful at *proposing* causal structure and unreliable at *asserting* it: run to run they disagree with themselves, draw loops, write claims nobody can ever check, and attach numbers to nothing. So validity is not something we ask the model for — it is something our own code decides. `validate(graph)` is a pure function in `domain/` that takes a map and returns the complete list of everything wrong with it, each item with a stable machine-readable code and a plain sentence a user can read. The model proposes; this function disposes (decision record 0003). Because of it, a user can trust that every map on the canvas has been checked by tested code rather than asked for politely in a prompt.

---

## Data model

All three shapes are pydantic models — pydantic being the Python library we use to define a data shape and check anything claiming to be one.

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from katalyst.domain.link import Link  # defined in `link.md`
from katalyst.domain.proposition import Proposition, PropositionId  # defined in `proposition.md`


class Graph(BaseModel):
    """A whole cause-and-effect map: claims, the arrows between them, and which claim started it.

    A graph is immutable. Nothing edits one in place — a change is an
    intervention recorded on a branch, and applying a branch produces a new
    graph (`../multiverse/branches-and-worlds.md`). A graph is a *proposal*
    until `validate` has returned an empty list for it; nothing reaches the
    canvas before that.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        description="Minted by our code, never by the model. See Identifiers below."
    )
    propositions: tuple[Proposition, ...] = Field(
        description="Every claim on the map, in no particular order. A tuple, so it cannot be appended to."
    )
    links: tuple[Link, ...] = Field(
        description="Every arrow on the map. Each names a source and a target that must be present above."
    )
    hypothesis_id: PropositionId = Field(
        description=(
            "The claim the user started from. Must name a proposition present in `propositions` — that "
            "much is checked when the object is built. That the named claim is actually of kind "
            "'hypothesis', and that no second one exists, is checked by `validate`."
        )
    )


ViolationCode = Literal[
    # Fourteen faults in a map — what `validate` finds.
    "missing_resolution",
    "missing_rationale",
    "documented_without_source",
    "cycle",
    "reflexive_without_lag",
    "half_life_without_impulse",
    "impulse_without_half_life",
    "belief_out_of_range",
    "no_terminal",
    "no_hypothesis",
    "multiple_hypotheses",
    "dangling_link",
    "market_without_payoff",
    "not_tradeable_without_reason",
    # Four refused edits — what `apply` finds. See *Refusing an edit* below.
    "unknown_target",
    "unknown_link",
    "duplicate_id",
    "edit_not_applicable",
]
"""Eighteen stable strings: fourteen things that can be wrong with a **map**, and
four reasons an **edit** cannot be folded onto one. The browser switches on them,
tests assert on them, and they are never renamed without a migration."""


class Violation(BaseModel):
    """One thing wrong with a map, addressed to two different readers at once.

    `code` and `subject` are for the machine: the interface uses them to
    highlight the tile or wire at fault. `message` is for the person: a plain
    sentence naming the claim by its text. A violation must never be the only
    record of a rejection — the list is stored with the generation transcript
    so a rejected proposal stays auditable.
    """

    model_config = ConfigDict(frozen=True)

    code: ViolationCode = Field(
        description="Which rule was broken. One of eighteen stable strings."
    )
    subject: str = Field(
        description=(
            "The identifier of the thing at fault: a proposition id, a link id, the graph's own id "
            "for faults about the map as a whole, or — for a refused edit — the branch's id. "
            "Never shown to the user."
        )
    )
    message: str = Field(
        description=(
            "Interface text. One plain sentence that names the claim or the arrow by its words and says "
            "what is missing. Never contains an identifier."
        )
    )


def validate(graph: Graph) -> list[Violation]:
    """Return everything wrong with this map — all of it, not the first thing found.

    Pure: no clock, no network, no randomness, no logging. Same map in, same
    list out, in the same order, every time.

    An empty list means the map satisfies every rule in the table below. It
    does not mean the map is *right* — the numbers can still be nonsense. It
    means the map is well-formed enough to be shown to a person and argued
    with, which is a different and more modest claim.
    """
```

`Proposition`, `Link` and `Belief` — and the identifier alias `PropositionId`, which is a plain `str` — are defined in [`proposition.md`](proposition.md), [`link.md`](link.md) and [`belief.md`](belief.md).

### Messages are interface text

A rejected proposal is shown to the user, so the message is not a log line. Two real ones:

> These claims form a loop with no delay in it: "Brent crude settles below $68 for five sessions" → "OPEC+ announces an output restraint" → "Brent crude settles below $68 for five sessions". Mark the arrow where a market feeds back on the world as reflexive and give it a delay, or remove one arrow.

> The arrow from "The Strait of Hormuz is open to unrestricted commercial transit for 14 consecutive days" to "The Lloyd's war-risk premium for Gulf transits falls below 0.4%" is marked as documented but cites no source.

Rules for messages: name the claim by its words, never by its identifier; say what is missing, not that something "failed validation"; stay one sentence where the fault is one thing; where a claim's text runs past about eighty characters, trim it with an ellipsis so the sentence stays readable.

### The rules

Thirteen rules, fourteen codes — "exactly one hypothesis" fails in two different directions. The table is split in two so it fits on a screen; the `code` column joins them. These are the faults in a **map**; the four reasons an **edit** is refused are a separate list, below.

| # | Rule, in plain words | Serves | Code | Test |
|---|---|---|---|---|
| 1 | Every claim says how it will be judged, by whom, and by when | INV-1 | `missing_resolution` | `test_validate_rejects_unresolvable_proposition` | 02 |
| 2 | Exactly one claim is the hypothesis the user started from | INV-graph.4 | `no_hypothesis`, `multiple_hypotheses` | `test_validate_requires_exactly_one_hypothesis` | 02 |
| 3 | The map ends somewhere you can act on: at least one `market` or `not_tradeable` claim | INV-9 | `no_terminal` | `test_validate_requires_terminal` |
| 4 | A `market` claim says what you would trade | INV-9 | `market_without_payoff` | `test_validate_requires_payoff_on_market` |
| 5 | A `not_tradeable` claim says why there is nothing to trade | INV-9 | `not_tradeable_without_reason` | `test_validate_requires_reason_on_not_tradeable` |
| 6 | Every arrow says why one claim moves the other | INV-2 | `missing_rationale` | `test_validate_rejects_link_without_rationale` |
| 7 | An arrow whose provenance claims evidence — `documented`, `historical` or `market_implied` — cites at least one source | INV-2 | `documented_without_source` | `test_validate_rejects_unsourced_documented_link` |
| 8 | Both ends of every arrow name a claim that is on this map | INV-graph.1 | `dangling_link` | `test_validate_rejects_dangling_link` | 02 |
| 9 | Once the reflexive arrows are set aside, there are no loops | INV-6 | `cycle` | `test_validate_rejects_cycles`, `test_apply_preserves_dag` |
| 10 | Every reflexive arrow takes time: `lag > 0` | INV-6 | `reflexive_without_lag` | `test_reflexive_links_have_positive_lag` |
| 11 | A half-life appears only on an arrow whose push fades: `shape` is `impulse` | INV-graph.15 | `half_life_without_impulse` | `test_validate_rejects_half_life_without_impulse` | 02 |
| 12 | Every likelihood sits between 0 and 1 with low ≤ p ≤ high | INV-7 | `belief_out_of_range` | `test_validate_rejects_belief_out_of_range` | 02 |
| 13 | A push that fades says how fast: `shape` is `impulse` only with a `half_life` | INV-graph.16 | `impulse_without_half_life` | `test_validate_rejects_impulse_without_half_life` | 03a |

| Code | Message pattern |
|---|---|
| `missing_resolution` | The claim "…" does not say `<how it will be judged / who judges it / by when>`. |
| `no_hypothesis` | This map has no starting claim. Exactly one claim must be the hypothesis. |
| `multiple_hypotheses` | This map has `<n>` starting claims: "…", "…". A map has exactly one. |
| `no_terminal` | This map does not end anywhere you can act on. Add a claim that names an instrument, or one that says why there is nothing to trade. |
| `market_without_payoff` | The tradeable claim "…" does not say what you would trade. |
| `not_tradeable_without_reason` | The claim "…" is marked not tradeable but does not say why. |
| `missing_rationale` | The arrow from "…" to "…" does not say why one causes the other. |
| `documented_without_source` | The arrow from "…" to "…" is marked as `<provenance>` but cites no source. |
| `dangling_link` | The arrow out of "…" points at a claim that is not on this map. (Or: the arrow into "…" comes from a claim that is not on this map.) |
| `cycle` | These claims form a loop with no delay in it: "…" → "…" → "…". Mark the arrow where a market feeds back on the world as reflexive and give it a delay, or remove one arrow. |
| `reflexive_without_lag` | The feedback arrow from "…" to "…" has no delay. A market cannot change the world it is measuring in zero time. |
| `half_life_without_impulse` | The arrow from "…" to "…" gives a half-life, but only a spike fades; a step or a ramp has nothing to fade. |
| `impulse_without_half_life` | The arrow from "…" to "…" is a spike that fades, but does not say how fast. Give it a half-life in days, or make it a step. |
| `belief_out_of_range` | The `<owner>` likelihood on "…" is `<p>`, with a range of `<lo>` to `<hi>`, which is not a range around that number between 0 and 1. |

**`dangling_link` is the one case where a message cannot name both ends**, because one of them does not exist. It names the end that does.

#### Notes on three of the rules

**Rule 9, loops.** The check builds a directed graph with `networkx` — a standard Python library for graph algorithms — from every link whose `reflexive` flag is false, and asks it for the cycles. A self-link (an arrow from a claim to itself) is a cycle of length one and is caught by the same pass, which is why there is no separate code for it. A map that passes this rule is what the literature calls a *directed acyclic graph* — a graph whose arrows all point one way and never come back round. The abbreviation *DAG* survives in this repo only inside the test name `test_apply_preserves_dag`. Reflexive arrows are excluded because a market feeding back on the world is a real loop in reality, made honest by taking time; how it unrolls over that time is stack 06's work. See [`link.md`](link.md), section *`reflexive` — a market feeding back on the world*.

**Rule 12, likelihoods, is checked twice on purpose.** `Belief` already refuses to be built with `lo > p` or `hi > 1` — that is a field check on the model itself, so a `Graph` assembled through our own models can never contain a bad one, and `belief_out_of_range` will never fire from that direction. The rule exists here anyway as the net under maps that arrive some other way: a hand-edited fixture file, a stored map read back after the shapes have changed, a future path that builds beliefs from raw numbers. Belief construction is [`belief.md`](belief.md); the after-any-intervention version of the same guarantee is `test_belief_bounds_after_any_sequence`, owned by [`belief.md`](belief.md). Whether a code that is currently unreachable from inside the models should exist at all is under Open questions.

**Rules 11 and 13 reject rather than ignore — the same rule, checked both ways.** A half-life is how many days a spike takes to fall to half its size, so it says something only about an `impulse`; a `step` switches on and holds and a `ramp` climbs and then holds, and neither has anything to fade. The field could have been quietly ignored on those two shapes, and for a while it was. It is refused instead, because a number we accept and then ignore forever is a number the user cannot account for — the same argument as *Reject; never repair* below. Decided 2026-09-17; see [`link.md`](link.md), Open questions 4.

**Decided 2026-09-17, the other direction too.** An `impulse` with no half-life used to be legal, on the reasoning that it wanted a sensible default and that choosing one belonged to propagation. It is now rule 13 and code `impulse_without_half_life`. Propagation has no honest default to choose: reading a missing half-life as "no decay" turns the arrow into a `step` and silently overrides the author's choice of shape, and any other number would be invented by us and attributed to the model. So the shape and its parameters must **agree, checked both ways** — a spike says how fast it fades, and only a spike says it. Reject, never repair. The consequence for `propagate` is that it never meets one: [`../multiverse/propagation.md`](../multiverse/propagation.md) evaluates `impulse` with the half-life it is guaranteed to have. Every `impulse` in the Hormuz fixture already names one, so nothing shipped changes.

**Rules 4 and 5 are validity rules, not field rules.** `Proposition.payoff` and `Proposition.not_tradeable_reason` are optional fields on one class, so a `market` claim with no payoff can be *built*. It just cannot be *valid*. That is deliberate: a model proposal with the wrong combination comes back as a `Violation` carrying a sentence the user can read, not as a pydantic exception carrying a stack trace.

#### The order of the list

Violations come back in the order of the rule table above, and within a rule sorted by `subject`. The list is therefore deterministic: the same map always produces the same list, which is what lets the interface rank them and the tests compare them directly.

### Refusing an edit — four more codes *(decided 2026-09-17)*

The fourteen rules above describe a **map**. An **edit** can fail for reasons that have nothing to do with the map being malformed — it can simply not fit the map it was handed. Those come back through the same `Violation` shape, from `apply` rather than from `validate`, and they carry four codes of their own. They arrive with `apply` in **stack 03a**; [`../multiverse/interventions.md`](../multiverse/interventions.md) owns which edit produces which.

| Code | Raised when | Message pattern |
|---|---|---|
| `unknown_target` | The edit names a claim this map does not have | This map has no claim "…". |
| `unknown_link` | It names an arrow this map does not have | This map has no arrow from "…" to "…". |
| `duplicate_id` | An `insert` reuses an identifier already on the map | The claim "…" is already on this map. |
| `edit_not_applicable` | The edit cannot be folded onto this map as written | Splitting a claim is not built yet — it arrives in stack 06. (Or: the arrow "…" does not touch the claim being added. Or: this branch's chain of parents loops back on itself.) |

`edit_not_applicable` is the one that covers more than one case, and it is deliberately not a bin for everything: it means *the edit is well-formed and names things that exist, and still cannot be applied*. Keeping it separate is what lets `unknown_target` go on meaning exactly what it says.

**`apply` stops at the first edit that does not fit**, and reports every violation *that edit* produced. That is different from `validate`, which walks every rule over the whole map. The reason is ordering: a branch's edits build on each other, so an edit after the failure may name a claim or arrow the failed edit would have added, and reporting its faults would blame the user for an artefact of the stop. One broken edit, all of its reasons.

### Reject; never repair

**The rule: when a proposal breaks a rule, `validate` reports it and the proposal is refused. Nothing in `domain/` ever quietly fixes a map so that it passes.** No dropping the arrow that closes the loop. No downgrading a `documented` link to `argued` because its sources came back empty. No inventing a resolve-by date. No adding a `not_tradeable` terminal so the map ends somewhere.

The reason is the product's first principle. A silently dropped arrow is a map the user cannot account for: they see six arrows where the model proposed seven, and nothing anywhere says why. That is precisely "not knowing why it did that", which is a veto condition (`PRODUCT_REQUIREMENTS.md` §3, D5-ii), and it is worse than a visible failure, because the user now trusts a map that has been edited by something with no name.

Repair is also a lie about provenance. The whole point of `provenance` is that it records what actually happened during generation ([`link.md`](link.md)). A repaired map's provenance describes a pipeline that eventually stopped violating things — which is not a source.

What the model-facing pipeline is allowed to do about a rejection is a different question, and not this chapter's: `engine/` may issue **one** targeted re-prompt that names the violations and asks for a corrected proposal, bounded and logged; a second failure surfaces as a proper error state, not a spinner (decision record 0003, rule 2). That loop, its bounds, and what the user sees while it runs belong to [`../generation/`](../generation/) and are written in stack 04. `domain/` knows nothing about it. `validate` returns a list and has no opinion about what anyone does next.

### Identifiers

**Identifiers are minted by our code. The model never assigns one.** A model asked for identifiers reuses them across calls, collides when two branches fork from the same map, and refers to claims that were never created. Instead the model refers to a claim by its text and by a position inside its own proposal, and `engine/` maps those to real identifiers when the proposal is accepted (decision record 0003, rule 3).

- **What they are.** ULIDs — universally unique lexicographically sortable identifiers: 26 characters, unique without coordination, and sorting them puts them in the order they were created, which makes a log of them readable.
- **Where they are made.** `engine/ids.py`, function `mint_id()`. Minting one needs the current time and a source of randomness. `domain/` reads no clock and draws no randomness — that is what makes it pure, deterministic and property-testable (decision record 0003, rule 1) — so minting happens outside the domain, in `engine/`, and identifiers are passed **into** domain models as ordinary values.
- **What the domain believes about them.** Almost nothing. `PropositionId = str`, `LinkId = str`, `BranchId = str`. `domain/` never checks that a string is a well-formed ULID. It checks only what it can check honestly: that the identifiers an arrow names are present on the same map (rule 8), and that `hypothesis_id` names a proposition that exists.
- **Fixtures use readable identifiers.** The Hormuz fixture's claims are `H`, `C`, `B`, `R`, `S`, `M1`, `M2`, `N1`. A 26-character string in a test failure teaches nobody anything; `H → B` does. This is possible precisely because the domain does not check the format, and it is the main reason not to.

---

## Behaviour

Worked on the assignment's first example, *"The Strait of Hormuz is going to open next week."* The base map is `H` (the strait open for 14 consecutive days, judged by Lloyd's List), `C` (the Lloyd's war-risk premium below 0.4%), `B` (Brent settles below $68 for five sessions), `R` (OPEC+ announces output restraint), `M1` and `M2` (two tradeable terminals), and `N1` (a terminal that says why one downstream effect is not tradeable).

### B1 — a proposal that would close a loop comes back as one violation

The model, expanding the map, proposes one more arrow: `B → H`, "cheaper crude reduces the incentive to close the strait." Read on its own it is a reasonable sentence. Added to the map it closes `H → B → H`.

`validate` returns exactly **one** violation, not one per arrow on the loop:

```
Violation(
  code="cycle",
  subject="<the id of the arrow that closes the loop>",
  message='These claims form a loop with no delay in it: "The Strait of Hormuz is '
          'open to unrestricted commercial transit for 14 consecutive days" → '
          '"Brent crude settles below $68 for five sessions" → "The '
          'Strait of Hormuz is open to unrestricted commercial transit for 14 '
          'consecutive days". Mark the arrow where a market feeds back on the '
          'world as reflexive and give it a delay, or remove one arrow.',
)
```

The arrow is not added. The map the user was already looking at is untouched, because nothing mutated it — the proposal was a candidate map, and it lost. What `engine/` does next is [`../generation/`](../generation/).

Note what the message does: it names the claims on the loop in order, and it says the one thing that would make the loop legal — mark the market-to-world arrow reflexive and give it a delay. That is the difference between a rejection and an insult.

### B2 — three problems come back as three violations

A hand-written map, perhaps a fixture mid-edit, has three separate faults: claim `C` has criteria and a source but no resolve-by date; the arrow `C → B` is marked `documented` with an empty `sources`; and nobody has added `M1`, `M2` or `N1` yet, so the map ends at `B`.

```python
>>> [v.code for v in validate(draft)]
['missing_resolution', 'no_terminal', 'documented_without_source']
```

Three faults in, three violations out, in rule-table order, every one of them reported on the first pass. The interface lists all three at once, so the user fixes three things in one sitting instead of discovering them one rebuild at a time. A validator that stopped at the first fault would turn one edit into three round trips and would teach the user that the map is a minefield.

### B3 — the Hormuz base map passes

```python
>>> validate(hormuz_base_graph())
[]
```

Every claim has criteria, a named judge and a date. Every arrow has a rationale. The arrows marked `argued` cite nothing and are not asked to. `B → R` is reflexive with a fourteen-day lag, so removing the reflexive arrows leaves `R → B` standing alone and there is no loop. `M1` and `M2` carry payoffs; `N1` carries its reason. The fixture ships with a test asserting exactly this, so the example in the product is held to the rules the product enforces.

---

## INVARIANTS

The generators live in `backend/tests/strategies.py`, built on `hypothesis`, a Python library that runs each statement over many randomly generated inputs and, on failure, shrinks the input to the smallest example that still fails. It shares its name with the user's *hypothesis* and has nothing to do with it.

- `graphs()` — random maps that are **valid by construction**.
- `broken_graphs(*rules)` — random maps built the same way, then damaged in each named way. One name damages one rule; three names damage three.
- `branches(graph)` — random branches for a given map, owned by [`../multiverse/branches-and-worlds.md`](../multiverse/branches-and-worlds.md).

Every invariant below is therefore two-sided: valid maps must pass clean, and a specific damage must produce a specific code. The **Stack** column says when the invariant starts running: everything about `validate` is stack 02; anything about applying a branch waits for stack 03a.

Local numbers (`INV-graph.<n>`) are unique across the whole of `spec/graph/`. **This chapter holds `INV-graph.4` through `INV-graph.8`, and `INV-graph.15` and `INV-graph.16`**, and restates `INV-graph.1` from [`link.md`](link.md) because the rule that enforces it lives here.

| ID | Statement | Test | Stack |
|---|---|---|---|
| **INV-1** | For all graphs drawn from `graphs()`, `validate` returns `[]`. For all graphs drawn from `broken_graphs("missing_resolution")`, `validate` returns exactly one violation and its code is `missing_resolution` | `test_validate_rejects_unresolvable_proposition` | 02 |
| **INV-2** | For all graphs from `graphs()`, `[]`. For all from `broken_graphs("missing_rationale")`, exactly one `missing_rationale`; for all from `broken_graphs("documented_without_source")`, exactly one `documented_without_source` | `test_validate_rejects_link_without_rationale`, `test_validate_rejects_unsourced_documented_link` | 02 |
| **INV-6** | For all graphs from `graphs()`, `[]`. For all from `broken_graphs("cycle")`, exactly one `cycle`; for all from `broken_graphs("reflexive_without_lag")`, exactly one `reflexive_without_lag`. For all graphs from `graphs()` and all branches from `branches(graph)`, `apply(graph, branch)` still has no loops once reflexive arrows are removed | `test_validate_rejects_cycles`, `test_reflexive_links_have_positive_lag`, `test_apply_preserves_dag` | 02; 03a for `test_apply_preserves_dag` |
| **INV-7** | For all graphs from `graphs()`, `[]`. For all from `broken_graphs("belief_out_of_range")` — built by bypassing the model constructors — exactly one `belief_out_of_range` | `test_validate_rejects_belief_out_of_range` | 02 |
| **INV-9** | For all graphs from `graphs()`, `[]`. For all from `broken_graphs("no_terminal")`, exactly one `no_terminal`; likewise `market_without_payoff` and `not_tradeable_without_reason` | `test_validate_requires_terminal`, `test_validate_requires_payoff_on_market`, `test_validate_requires_reason_on_not_tradeable` | 02 |
| **INV-graph.1** | Stated in [`link.md`](link.md): both ends of every arrow name a claim on the same map. For all graphs from `broken_graphs("dangling_link")`, exactly one `dangling_link` | `test_validate_rejects_dangling_link` | 02 |
| **INV-graph.15** | For all links drawn from `links()`: `half_life` is `None` unless `shape` is `impulse`. For all graphs from `broken_graphs("half_life_without_impulse")`, `validate` returns exactly one `half_life_without_impulse` violation | `test_validate_rejects_half_life_without_impulse` | 02 |
| **INV-graph.16** | The mirror, decided 2026-09-17. For all links drawn from `links()`: `half_life` is a number whenever `shape` is `impulse`. For all graphs from `broken_graphs("impulse_without_half_life")`, `validate` returns exactly one `impulse_without_half_life` violation. Read with the row above: the shape and its parameters must agree, both ways, so `propagate` never meets a spike with no decay to evaluate. This replaces `test_an_impulse_without_a_half_life_is_still_legal`, which asserted the opposite | `test_validate_rejects_impulse_without_half_life` | 03a |
| **INV-graph.4** | For all graphs from `graphs()`, exactly one proposition has `kind == "hypothesis"` and it is the one named by `hypothesis_id`. For all from `broken_graphs("no_hypothesis")`, exactly one `no_hypothesis`; for all from `broken_graphs("multiple_hypotheses")`, exactly one `multiple_hypotheses` | `test_validate_requires_exactly_one_hypothesis` | 02 |
| **INV-graph.5** | For all graphs drawn from `broken_graphs(r1, r2, r3)` with three distinct rule names, `validate` returns exactly three violations and their codes are exactly `{r1, r2, r3}` — it never stops at the first | `test_validate_reports_every_violation` | 02 |
| **INV-graph.6** | For all graphs from `broken_graphs(*rules)`, calling `validate` twice returns two equal lists, and the codes appear in the order of the rule table above, ties broken by `subject` | `test_violations_are_ordered_stably` | 02 |
| **INV-graph.7** | Stated once for every model in `spec/graph/`. For all graphs from `graphs()`, `Graph.model_validate_json(g.model_dump_json()) == g`, and the same holds for every `Proposition`, `Link`, `Source` and `Belief` inside it and for every `Violation` `validate` returns | `test_models_round_trip_json` | 02 |
| **INV-graph.8** | Stated once for every model in `spec/graph/`. For all graphs from `graphs()`, assigning to any field of the graph, of any proposition, link, source or belief inside it, or of any `Violation`, raises `ValidationError`; `propositions`, `links` and `Link.sources` are tuples, not lists | `test_models_are_frozen` | 02 |

Target coverage for `domain/` is 85% or more (decision record 0008).

---

## ANTI-PATTERNS

1. **Do not repair a map to make it pass**, because a silently corrected map is a state the user cannot trace back to anything, and that is a veto condition. Return the violation and let the pipeline ask once for a better proposal. If an automatic fix ever looks irresistible, it is a sign the rule is wrong — change the rule in the open, in this chapter, rather than routing around it in code.
2. **Do not stop at the first violation**, because a person fixing a map one fault per rebuild learns only that the tool is hostile, and a model given one fault at a time needs one re-prompt per fault. `validate` walks every rule every time; the map is small and the walk is microseconds.
3. **Do not put identifiers in messages.** "Violation on link 01J8Z…" tells the user nothing; "The arrow from 'Hormuz is open…' to 'Brent settles below $68…' does not say why one causes the other" tells them exactly what to look at. The identifier is already in `subject`, where the interface can use it to highlight the right wire. A message is interface copy and is read as carefully as any other interface copy.
4. **Do not put validity logic in the web-request layer or in a prompt.** In an `api/` route handler it is invisible to the property tests and is skipped by every other caller — the fixture loader, the branch applier, the evaluation harness. In a prompt it is a polite request that a model will honour most of the time, which is the same as not having it. One function, in `domain/`, called by everything that builds a map.
5. **Do not let `validate` learn anything about the outside world.** No clock, no network, no reading of configuration, no logging. The moment it does, "the same map always produces the same violations" stops being true, replay (INV-5) stops being exact, and the property tests start flickering.

---

## Open questions

Raised 2026-09-16. Each needs Kent.

1. **Should `belief_out_of_range` exist?** The `Belief` model already refuses to be built out of range, so through our own constructors the code is unreachable. Keeping it costs one rule and buys a net under hand-edited fixture files and stored maps read back after the shapes have changed. Keeping it also means a test that has to bypass the models to produce the input, which is a small smell. Keep as defence in depth, or delete and rely on construction?
2. **`Graph.id` has no type alias.** The shapes sheet names `PropositionId`, `LinkId` and `BranchId` but not `GraphId`, so `Graph.id` is written here as a bare `str`. Add `GraphId = str` for symmetry, or leave it?
3. **Is "exactly one hypothesis" a product invariant?** It is in the vocabulary's definition of a graph and in the shapes sheet, but it is not one of `INV-1` … `INV-14`, so it is carried here as a local invariant, `INV-graph.4`. Promote it to the product list, or leave it local?
4. **Are `no_hypothesis` and `multiple_hypotheses` two codes or one?** They are one rule failing in two directions. Two codes let the interface say something different in each case; one code with a fuller message would also do. The shapes sheet says two, and that is what is written here.
5. **What is `subject` for a `cycle`?** Written here as the identifier of the arrow that closes the loop, which is the wire the interface should highlight. The alternative is the graph's identifier plus the loop in the message. If a map ever contains two separate loops, the current answer gives two violations, one per closing arrow — confirm that is what we want.
6. **Local invariant numbers come from one pool shared by four chapters.** `link.md`, `proposition.md`, `belief.md` and this chapter all number local invariants `INV-graph.<n>` from it. `link.md` holds 1; this chapter holds 4 through 8; 2 and 3 were retired when round-trip and immutability moved here. The reviewer should confirm nothing collides once all four chapters exist.
