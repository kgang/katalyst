# Probes — spending more compute where it counts

## The idea

Not every step of an argument deserves the same effort. A **probe** attaches extra modeling to one proposition, chosen by the user: split the claim into finer claims (model an election nationally → by state → by county), run thousands of random simulations to get a distribution instead of a point, or convene role-played experts to hunt for missing causes. Whatever a probe produces re-enters the map as a belief with provenance *simulated* and its own rationale — never as an anonymous overwrite.

The tool also says where a probe is worth it: rank propositions by how much the trade depends on them times how uncertain they are (*value of information*).

This part is stretch scope. It is designed for now so the graph and multiverse do not have to change later.

## Terms this part owns

Probe · Refine · Value of information · Persona red-team.

## Invariants this part owns

None product-level yet; `INV-10` (refinement marginalizes) is owned by `multiverse/` and exercised here.

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| `refine.md` | Splitting a proposition; the marginalization constraint; reconciling coarse and fine estimates | stack 06 |
| `monte-carlo.md` | Distribution probes; seeds; what a distribution chip shows | stack 06 |
| `personas.md` | Role-played experts as proposers of missing structure — never as outcome simulators | stack 06 |
| `value-of-information.md` | The ranking, and how the interface says "spend here" | stack 06 |
