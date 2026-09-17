# Multiverse — changing one thing

## The idea

The product's central move is *"…but what if this step were different?"* Two rules make that honest.

**The original is never touched.** A change is recorded as an **intervention** — a small, typed patch — and a **branch** is an ordered list of them. Applying a branch to the original graph yields a **world**. Because a branch is just its patches, any world can be replayed exactly, two worlds can be diffed structurally, and branches compose by concatenation.

**Only what is downstream changes.** An intervention on one proposition may change that proposition and everything it causes — nothing else. This is *locality*, and it is the product's central correctness claim, checked by a property test rather than promised.

Two kinds of change are kept distinct because they mean different things. *Asserting* a proposition ("suppose Hormuz opens") cuts it loose from its causes and pushes forward only. *Observing* it ("Hormuz opened, it's news") also updates what we believe about its causes. Most tools silently conflate these; here they are two verbs.

## Terms this part owns

Intervention (`do`, `observe`, `insert`, `retune`, `refine`, `believe`) · Branch · World · Diff · Locality · Propagation.

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-3 | `do` changes no ancestor of the target; `observe` may. They are distinct operations with distinct verbs in the interface |
| INV-4 | Locality: after an intervention on `n`, every proposition outside `n` and its descendants is byte-identical between base and branch |
| INV-5 | The base graph is immutable; a branch is an ordered patch list; applying an empty branch is the identity; applying two branches in sequence equals applying their concatenation; every world replays from (base, branch, seed) |
| INV-10 | After splitting a proposition into finer sub-propositions, their combined likelihood equals the original's within a small tolerance |

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| `interventions.md` | The six operations, their preconditions, and what each may touch | stack 02 |
| `branches-and-worlds.md` | Patch algebra, replay, seeds, naming, parent branches | stack 02 |
| `propagation.md` | How likelihoods flow: adding link strengths on a log-odds scale, trigger vs sustain over time, lags and signal shapes, the seeded random-simulation engine | stack 03a |
| `diff.md` | Per-proposition states (unchanged / shifted / added / killed), ranked terminal deltas, the one-line summary | stack 03a |

Decision records behind this part: ADR-0004 (branches are patches), ADR-0005 (propagation).
