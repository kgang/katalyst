# Multiverse — changing one thing

## The idea

The product's central move is *"…but what if this step were different?"* Two rules make that honest.

**The original is never touched.** A change is recorded as an **intervention** — a small, typed patch — and a **branch** is an ordered list of them. Applying a branch to the original graph yields a **world**. Because a branch is just its patches, any world can be replayed exactly, two worlds can be diffed structurally, and branches compose by concatenation.

**Only what is still connected changes.** An intervention changes only what is still connected to its subject in the graph the edit leaves behind. For an assertion, which cuts the claim loose from its causes, that is the claim and everything it causes and nothing else. This is *locality*, the product's central correctness claim, checked by a property test rather than promised.

Two kinds of change are kept distinct because they mean different things. *Asserting* a proposition ("suppose Hormuz opens") cuts it loose from its causes and pushes forward only. *Observing* it ("Hormuz opened, it's news") also updates what we believe about its causes. Most tools silently conflate these; here they are two verbs.

## Terms this part owns

Intervention (`do`, `observe`, `insert`, `retune`, `refine`, `believe`) · Branch · World · Diff · Locality · Propagation.

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-3 | `do` changes no ancestor of the target; `observe` may. They are distinct operations with distinct verbs in the interface |
| INV-4 | Locality: an intervention changes only what is still connected to its subject in the graph the edit leaves behind; every other proposition is byte-identical between base and branch. The per-operation affected set in [`interventions.md`](interventions.md) is the operational form, and the same chapter holds the one rule about feedback arrows: *what can move* is read off the map with feedback arrows set aside, because this engine never works one through |
| INV-5 | The base graph is immutable; a branch is an ordered patch list; applying an empty branch is the identity; applying two branches in sequence equals applying their concatenation; every world replays from (base, branch, seed) |
| INV-10 | After splitting a proposition into finer sub-propositions, their combined likelihood equals the original's within a small tolerance |

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| [`interventions.md`](interventions.md) | The six operations, their preconditions, and what each may touch | stack 02 — written, models built |
| [`branches-and-worlds.md`](branches-and-worlds.md) | Patch algebra, replay, seeds, naming, parent branches | stack 02 — written, models built |
| [`propagation.md`](propagation.md) | How likelihoods flow: adding link strengths on a log-odds scale, trigger vs sustain over time, lags and signal shapes, how a supposition ends, and the two-loop seeded simulation that gives every computed number its range | stack 03a — written |
| [`diff.md`](diff.md) | Per-proposition states (unchanged / shifted / added / killed), agreement, ranked terminal deltas, the one-line summary, the sensitivity sweep | stack 03a — written |

Decision records behind this part: ADR-0004 (branches are patches), ADR-0005 (propagation), ADR-0014 (how a supposition ends; what the range on a computed number means; how a change is ranked and dated).
