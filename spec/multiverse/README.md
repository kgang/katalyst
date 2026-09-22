# Multiverse — changing one thing

## The idea

The product's central move is *"…but what if this step were different?"* Two rules make that honest.

**The original is never touched.** A change is recorded as an **intervention** — a small, typed patch — and a **branch** is an ordered list of them. Applying a branch to the original graph yields a **world**. Because a branch is just its patches, any world can be replayed exactly, two worlds can be diffed structurally, and branches compose by concatenation.

**Only what is still connected changes.** An intervention changes only what is still connected to its subject in the graph the edit leaves behind. For an assertion, which cuts the claim loose from its causes, that is the claim and everything it causes and nothing else. This is *locality*, the product's central correctness claim, checked by a property test rather than promised.

Two kinds of change are kept distinct because they mean different things. *Asserting* a proposition ("suppose Hormuz opens") cuts it loose from its causes and pushes forward only. *Observing* it ("Hormuz opened, it's news") also updates what we believe about its causes. Most tools silently conflate these; here they are two verbs.

**And nothing the reader typed is ever taken back.** A supposition holds until another edit changes it — no calendar ends it, and no arrow un-trues it (decision record 0017). What can stop holding is a **state**: a claim that holds over a stretch of time rather than happening once, such as *the strait stays open to commercial transit through 1 November*. An **event** happens once and stays happened. Every claim says which it is.

## Terms this part owns

Intervention (`do`, `observe`, `insert`, `retune`, `refine`, `believe`) · Branch · World · Diff · Locality · Propagation.

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-3 | `do` changes no ancestor of the target; `observe` may. They are distinct operations with distinct verbs in the interface |
| INV-4 | Locality: an intervention changes only what is still connected to its subject in the graph the edit leaves behind; every other proposition is byte-identical between base and branch. The per-operation affected set in [`interventions.md`](interventions.md) is the operational form, and the same chapter holds the one rule about feedback arrows: *what can move* is read off the map with feedback arrows set aside, because this engine never works one through |
| INV-5 | The base graph is immutable; a branch is an ordered patch list; applying an empty branch is the identity; applying two branches in sequence equals applying their concatenation; every world replays from (base, branch, seed) |
| INV-10 | After splitting a proposition into finer sub-propositions, their combined likelihood equals the original's within a small tolerance. **Met by a named refusal rather than a feature** (2026-09-21, decision record 0021): splitting a claim is not built in version one, so `refine` returns one violation, `edit_not_applicable`, in our own sentence |

## Try the routes from a terminal

With the app running (`make dev`), the three routes that do the arithmetic can be called directly. The server's own interactive page for every route is <http://localhost:8000/docs>.

`/api/fixtures` lists the stored examples; <http://localhost:8000/api/fixtures/hormuz> returns the Strait of Hormuz map together with the branch in which Iran is struck the next day, every claim and arrow with its own source beside it. That is written by hand. The three routes below are not — they fold a branch onto a map, work every likelihood through time, and hand back numbers nobody typed.

**One world.** A map, a branch and a seed are the whole of it; the same three give a byte-identical answer on any machine. **None of the three routes changed shape on 2026-09-22** — same paths, same bodies, same answers, field for field. What changed is every number inside them, once: a claim's number now answers *by its deadline* rather than *on this day*; `lo` and `hi` come back equal to `p`, because there is no range (decision record 0028); and the request fields `worlds` and `versions` are ignored and come back `0` and `1`, because there is neither an inner loop nor a second reading.

```sh
curl -s localhost:8000/api/worlds \
  -H 'content-type: application/json' \
  -d '{"base_id":"hormuz","seed":20261001}' | jq '.beliefs.M1'
```

```text
the shape of the answer:  { "p": …, "lo": …, "hi": …, "owner": "model" }
```

That is the Polymarket contract's likelihood — **the chance the claim comes out true by its own deadline** — worked out once, from what the map states. `lo` and `hi` come back equal to it: **no number in this product carries a range** (decision record 0028). **The four figures are not printed here**, and that is deliberate: the route answers at full precision, and the sixteenth digit of a number that came out of a floating-point sum is not the same on every machine, so printing it would promise a reader something this program cannot deliver. They are in [`docs/worked-numbers.txt`](../../docs/worked-numbers.txt) instead, on the line named `M1 · base · reading`, along with every other number the worked example quotes. That file is generated by `make numbers` and the build fails when it goes stale, so it is the one place in this repository where an engine-computed number is written down and kept true.

Leave the branch out for the map as written; send one, whole, to fold it on first. (`jq` above only pretty-prints one field of the answer. The route itself needs nothing but `curl`.)

**What a change did.** One map, two branches, one seed — one seed for the pair, so every difference is the edit rather than a wash of sampling noise. A branch is sent whole rather than by name, because there is nowhere to keep one yet, so this uses `jq` to lift the stored branch out of the example and pipe it straight into the request:

```sh
curl -s localhost:8000/api/fixtures/hormuz \
  | jq '{base_id: "hormuz", seed: 20261001, branch_b: .branches[0]}' \
  | curl -s localhost:8000/api/worlds/diff \
      -H 'content-type: application/json' --data @- \
  | jq -r '.summary'
```

```text
the shape of the answer:  "<the branch>" moves <the ending, in its own words> from
                          <what it read> to <what it reads now> by <the day it
                          moved> and leaves <how many> claims untouched.
```

**The sentence with its numbers in it is not printed here**, for the same reason the four figures above are not: it is worked out, so it moves the day the arithmetic does, and a copy in a second place is a copy that goes stale. It is in [`docs/worked-numbers.txt`](../../docs/worked-numbers.txt) on the line named `strike · the sentence beside the list`, word for word. Its two likelihoods are written the way every likelihood in this product is written — two significant figures, with `<.01` and `>.99` standing in for the two claims nobody here is entitled to make.

The whole answer also carries a word per claim (`unchanged`, `shifted`, `added`, `killed`) and the endings that moved in ranked order. A third route, `POST /api/worlds/conditional`, gives the number on one arrow: its target, with its source **supposed** true — never how often the two happen to show up together.

A branch that does not fit the map comes back as `422` with **every** reason at once, each a stable code and one plain sentence naming the claim or the arrow by its words. Never a half-applied branch, never a silent repair.

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| [`interventions.md`](interventions.md) | The six operations, their preconditions, and what each may touch | stack 02 — written, models built |
| [`branches-and-worlds.md`](branches-and-worlds.md) | Patch algebra, replay, seeds, naming, parent branches | stack 02 — written, models built |
| [`propagation.md`](propagation.md) | What a claim's number means — the chance it comes out true by its own deadline; how an arrow bends a rate and how two causes add; events and states; the exact solve and the weighted sample | stack 05 — rewritten whole, engine built and flipped |
| [`diff.md`](diff.md) | Per-proposition states (unchanged / shifted / added / killed), ranked terminal deltas, the one-line summary, the sensitivity sweep | stack 03a — written, engine built; **amended in stack 05** where the new engine made it false |

Decision records behind this part: ADR-0004 (branches are patches), ADR-0005 (propagation), ADR-0014 (how a change is ranked and dated), **ADR-0016** (a claim's number is the chance it happens by its deadline; *whether* is solved exactly, *when* is sampled), **ADR-0017** (a claim is an event or a state; nothing retracts itself, which reverses record 0014's decision A) and **ADR-0028** (one likelihood per claim, computed once; no range anywhere, which reverses what record 0014 said a range meant).
