# Probes — spending more compute where it counts

## The idea

Not every step of an argument deserves the same effort. A **probe** attaches extra modeling to one proposition, chosen by the user: split the claim into finer claims (model an election nationally → by state → by county), run thousands of random simulations to get a distribution instead of a point, or convene role-played experts to hunt for missing causes. Whatever a probe produces re-enters the map as a belief with provenance *simulated* and its own rationale — never as an anonymous overwrite.

The tool also says where a probe is worth it: rank propositions by how much the trade depends on them times how uncertain they are (*value of information*).

## Chapters

There are none, and none is planned. Here is where that stands.

**What a probe would have been.** The one place a user could spend more compute on a single claim and get a better number back. Three ways: splitting the claim into finer claims that add back up to it, running a distribution over it instead of a point, or sending role-played experts to look for causes nobody put on the map. Whatever came back would land as a belief that says where it came from.

**Why it was not built.** Nothing in the assignment asks for it, and the walk this product is judged on never wants a finer claim. So on 2026-09-21 the whole part was cut from version one, along with `refine`, the unrolling of feedback loops and the random-simulation probe. What survives in code is the shape and an honest refusal: `Refine` is a typed edit in `backend/src/katalyst/domain/intervention.py`, and folding one onto a map answers *"splitting the claim … into finer claims is not built yet"* rather than half-doing it or dropping it in silence.

**What would have to be true to build it.** A claim on a real map would have to be two things at once: the thing the trade turns on, and too coarse to score. That means one tile a user cannot call true or false, with finer claims underneath it that a named source could actually judge. The first thing to build would then be `refine` and the adding-up check that goes with it, because the other two probes are ways of getting a number and that one is a way of checking one.

## Terms this part owns

Probe · Refine · Value of information · Persona red-team.

## Invariants this part owns

None product-level. `INV-10` — *"Refinement adds up. After a proposition is split into finer sub-propositions, their combined likelihood equals the original's within a small tolerance"* — is owned by `multiverse/` and is met today by the refusal above: the operation that could break it cannot be applied at all.
