# Branches and worlds — a branch is a patch, a world is a result

## Purpose

The user asks "…but what if Iran is struck the next day?" and expects two things at once: the new answer, and the old one still sitting there to compare it against. That only works if changing the map never *changes the map*. So a **branch** is not a copy of the map with edits made to it — it is the ordered list of edits themselves, sitting beside an original nobody touches. A **world** is what you get when you fold a branch onto the original and work the likelihoods through. The branch is the durable thing; the world is a result you can always throw away and rebuild. Everything the product promises downstream — showing only what moved, replaying a session later, comparing four versions side by side, reproducing a screenshot from three days ago — follows from that one choice.

---

## Data model

A branch carries four things and nothing else. Two words are used interchangeably below: a **map** is a **graph** — the claims and the arrows between them — and `Graph` is the name the type goes by in code.

```python
from pydantic import BaseModel, ConfigDict, Field

BranchId = str
"""The identifier of a branch. A plain string; our code mints it (decision record 0003)."""


class Branch(BaseModel):
    """A named, ordered list of edits over a base map. A branch *is* a patch.

    It holds no propositions, no links, no likelihoods and no results — only the edits.
    Everything a branch shows on screen is computed from the base map plus this list,
    which is what makes a branch cheap to create, exact to replay, and impossible to
    drift from the original it forked out of.
    """

    model_config = ConfigDict(frozen=True)

    id: BranchId = Field(description="This branch's identifier.")
    label: str = Field(
        description=(
            "The name the user reads: 'Hormuz opens, then Iran is struck'. "
            "Required — an unnamed branch is unusable once there are three of them."
        )
    )
    parent: BranchId | None = Field(
        default=None,
        description=(
            "The branch this one continues from, whose edits are applied first. "
            "None means this branch forks directly off the untouched base map."
        ),
    )
    interventions: tuple[Intervention, ...] = Field(
        default=(),
        description=(
            "The edits, in the order the user made them. Order matters: an edit can "
            "act on what an earlier edit added. An empty list is the base world."
        ),
    )
```

`Intervention` is the six-way union defined in [`interventions.md`](interventions.md). `model_config = ConfigDict(frozen=True)` means an instance cannot be altered after it is built, and the edits are a tuple rather than a list for the same reason: a branch is a record of what happened, not a working buffer.

**A world is not defined here.** `propagation.md` (stack 03a) defines it as `propagate(apply(base, branch), seed)` — fold the branch onto the base map, then work the likelihoods through with an explicit random seed. A world is a cached result, never a source of truth: if it disagrees with what those three inputs produce, the world is wrong.

### Patch algebra — the three laws

*Algebra* here just means: these are the rules edits obey when you put them together, and they hold for every map and every list of edits, not just the ones we tried. `apply(base, branch)` is the pure function that folds a branch's edits onto a base map, in order. Pure means it reads no clock, makes no network call, and uses no randomness — the same inputs always give the same output.

**Law 1 — applying nothing changes nothing.** `apply(g, empty)` is `g`, byte for byte, where `empty` is any branch whose edit list is `()` — its identifier and label make no difference. The base world is exactly this: the empty branch. This is what makes "the original is always there" true by construction rather than by care.

**Law 2 — two branches in a row equal the two joined.** Applying branch `x` and then branch `y` gives the same map as applying the single branch whose edit list is `x`'s followed by `y`'s. In one line: `apply(apply(g, x), y) == apply(g, x + y)`. This is why a child branch needs no machinery of its own — continuing from a parent is just concatenation — and why a diff is free: the patch *is* the difference.

**Law 3 — every world replays exactly.** The same base map, the same branch and the same seed give a byte-identical world, today or next week, on your laptop or in the container. Nothing else is needed and nothing else is allowed to matter (INV-5, NFR-2). A screenshot taken three days ago is reproducible from three values.

Laws 1 and 2 together are what make the base map safe to share: because edits compose by concatenation rather than by rewriting, no branch ever needs write access to the original, and four live branches cost the base plus four small lists.

#### A child branch applies its parent's edits first

`hormuz-then-strike` holds three edits. Suppose the user, looking at that branch, decides the strike's push against the insurance premium is overdone — the model puts that arrow at −2.0, and the user halves it to −1.0 — and puts their own number on the Polymarket contract. Those two new edits go into a **child branch** whose `parent` is `hormuz-then-strike`:

```python
Branch(
    id="br_strike_insurance_doubt",
    label="Strike, but underwriters shrug",
    parent="br_hormuz_then_strike",
    interventions=(
        Retune(link="S->C", strength=-1.0),
        Believe(target="M1", belief=Belief(p=0.30, lo=0.20, hi=0.45, owner="user")),
    ),
)
```

Its world is built from the base map and this full ordered list — the parent's three edits first, then the child's two:

| # | From | Edit | What it does |
|---|---|---|---|
| 1 | parent | `Do(target="H", value=True, at=2026-10-01)` | Suppose the strait opens; cut H loose from its causes |
| 2 | parent | `Insert(proposition=S, links=(S→B, S→C, S→H))` | Add the strike claim and its three arrows |
| 3 | parent | `Do(target="S", value=True, at=2026-10-02)` | Suppose the strike happens, one day later |
| 4 | child | `Retune(link="S->C", strength=-1.0)` | Halve the strike's push against the insurance premium, −2.0 → −1.0 |
| 5 | child | `Believe(target="M1", belief=Belief(p=0.30, lo=0.20, hi=0.45, owner="user"))` | Record the user's own number on the Polymarket contract |

Read it top to bottom and the order is load-bearing twice over. Edit 4 names an arrow that did not exist until edit 2, so it could not have come first. Edit 3 supposes a claim that edit 2 introduced. Concatenation is the whole mechanism: there is no merge, no rebase, no three-way anything.

### Naming, and where randomness comes from

**Every branch is named.** `label` is required and written by the user — "Hormuz opens, then Iran is struck" — because the moment there are three versions on screen, "Branch 3" is useless. The interface shows at most four branches at once and collapses the rest to a list, so the names carry the comparison.

**Identifiers are minted by our code**, never by the model and never by the browser: a ULID, an identifier that is unique and sorts by when it was made. Minting needs a clock and randomness, so it happens at the system's outer boundary, in `engine/ids.py`, and the identifier is passed into the pure core — which is why `domain/` can promise it reads no clock (decision record 0003).

**The base world is the empty branch.** Not a special case in the code, not a null, not a flag: a `Branch` whose `interventions` is `()`. Law 1 then makes it identical to the base map, which is the point.

**Seeds are passed in, explicitly, every time.** Working the likelihoods through involves random simulation, and the seed that drives it is an argument to `propagate` — never a module-level random generator, never the system clock, never a global seeded once at start-up. A global source of randomness would make a world depend on how many other worlds had been computed before it, which quietly destroys law 3 and with it replay. The seed is not a field on `Branch`: it is the third member of the replay triple `(base map identifier, branch, seed)` and travels with the request that asked for the world (NFR-2, FR-13).

---

## Behaviour

Worked on the Strait of Hormuz map. Its claims, in the wording the fixture uses: **H** *Strait of Hormuz open to unrestricted commercial transit for 14 consecutive days* (the hypothesis) · **C** *Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%* · **B** *Brent crude settles below $68 for five sessions* · **R** *OPEC+ announces output restraint* · **M1** and **M2**, two tradeable terminals. "Today" is 2026-10-01.

### B1 — Committing one edit forks a branch

The user is looking at the base world, clicks the box for H and chooses **Suppose this is true**. On commit:

1. A `Branch` is created — a new identifier, a label (the user's words, or one suggested from the edit, such as "Hormuz opens"), `parent=None` because this forked off the base, and one intervention in the list.
2. The base map is not read for writing, not copied, and not locked. It is not touched at all.
3. The world is computed from the base map, this branch and a seed, and drawn.

Forking costs the size of the patch — one small object — and nothing else. There is no moment at which the original and the fork are the same object and could be confused; there is no moment at which a failed edit could leave the original half-changed.

### B2 — A child branch of a branch

From the `hormuz-then-strike` world, the user retunes the S → C arrow and records their own number on M1. A new branch is created with `parent="br_hormuz_then_strike"` and those two edits, exactly as set out in the table above. Its world is built from all five edits in order.

The parent is unchanged and still on screen. Both branches still point at the same untouched base map. Nothing was copied.

### B3 — Replay gives back the identical world

The user closes the laptop. Three days later they reopen the session, or a reviewer opens the shared link, or the test suite rebuilds it in the container.

The stored record is `(base map identifier, branch, seed)` — three values, no picture of the graph, no cached likelihoods that could have drifted. Feeding them back through `apply` and then `propagate` yields a world byte-identical to the one on the screenshot: same likelihoods, same intervals, same ranking in the delta rail (the ranked list of terminal changes shown beside a diff). If it ever does not, exactly one of three things is at fault — the base map changed (forbidden), the branch changed (it is frozen), or propagation read something other than its seed (a bug, and the property test catches it).

---

## INVARIANTS

Each statement is true for every input a named generator can produce, and each names the test that checks it. Generators live in `backend/tests/strategies.py`: `graphs()` yields random **valid** maps, `interventions(graph)` yields edits whose subjects exist in that map, `branches(graph)` yields branches of such edits, and `seeds()` draws integer seeds. Tests live in `backend/tests/unit/domain/test_patches.py` unless noted.

Everything here needs `apply`, which arrives in **stack 03a**; stack 02 ships the `Branch` shape, so only the round trip below runs now.

Product invariant INV-5 makes three separate claims — identity, concatenation, replay — so it appears three times below under its own number; the test names tell them apart. This chapter uses the local numbers `INV-multiverse.6` onward; `.1` through `.5` belong to [`interventions.md`](interventions.md).

**INV-5 — applying an empty branch is the identity.** For all maps `g` from `graphs()` and every branch whose edit list is `()`: applying it to `g` serializes to bytes identical to `g`. Test: `test_apply_empty_is_identity`. **Stack 03a.**

**INV-5 — concatenation equals sequential application.** For all maps `g` from `graphs()` and all pairs of branches `x`, `y` from `branches(g)`: applying `x` then `y` to `g` gives a map byte-identical to applying the single branch whose edit list is `x.interventions + y.interventions`. Test: `test_patch_concat_equals_sequential_apply`. **Stack 03a.**

**INV-5, with NFR-2 — every world replays from base, branch and seed.** For all maps `g` from `graphs()`, all branches `b` from `branches(g)` and all seeds `s` from `seeds()`: two independently computed worlds from `(g, b, s)` serialize to identical bytes. Test: `test_world_replays_from_base_branch_seed`. **Stack 03a.**

**INV-multiverse.6 — the base is never written.** For all maps `g` from `graphs()` and all branches `b` from `branches(g)`: after `apply(g, b)` returns, `g` serializes to exactly the bytes it did before the call. The models are frozen, so this cannot fail quietly — it fails loudly, which is the point of keeping the test. Test: `test_base_graph_unchanged_after_apply`. **Stack 03a.**

**INV-multiverse.7 — a child applies its parent first.** For all maps `g` from `graphs()` and all parent/child branch pairs from `branches(g)`: the child's world is byte-identical to the world of a single branch whose edit list is the parent's followed by the child's. Test: `test_child_branch_applies_parent_first`. **Stack 03a.**

**INV-multiverse.8 — a branch survives a round trip.** For all branches `b` from `branches(g)` for `g` from `graphs()`: parsing `b`'s JSON back as a `Branch` yields an object equal to `b`, with every edit restored to its own class by its `kind` field. Test: `test_branch_round_trip`. **Stack 02.**

**The state-machine test — `GraphEditMachine`.** Rather than one random input, this generates a random *sequence* of edits and applies them one after another to a generated map, the way a user actually works. After **every** step it re-checks:

* the map still has no loops once reflexive links are set aside (INV-6);
* every likelihood still satisfies `0 ≤ low ≤ p ≤ high ≤ 1` (INV-7);
* the locality rule still holds for the step just taken (INV-4).

Any failing sequence is shrunk to the shortest one that still breaks, so a failure reads as "these two edits, in this order". It lives in `backend/tests/unit/domain/test_patches.py` and lands in **stack 03a** with `apply` (decision record 0008).

---

## ANTI-PATTERNS

**1. Do not copy the map when a branch is created.** *Because* two full maps have to be matched claim by claim to say what differs, which turns a free structural diff into a guess; the copies drift as one is edited and the other is regenerated; the user's edits and the model's numbers blur into the same fields with no way to tell them apart; and storage grows with every "what if". **Do** store the edits and share the base outright — creating a branch costs one small object.

**2. Do not mutate the base map, ever — not even "just to mark it".** *Because* the base is what every branch is computed against and what every replay starts from; change it and every stored world becomes a lie, silently. **Do** keep every model frozen, make `apply` a pure function that returns a new map, and let the property test above fail loudly if anyone tries.

**3. Do not store a world as the truth.** *Because* a world is a computed result — save it as the source and you now have two answers to "what is true", and the saved one will eventually be the older. **Do** persist `(base map identifier, branch, seed)` and treat any stored world as a cache that can be thrown away and rebuilt. Caching a world for speed is fine; *believing* it over the three inputs is not.

**4. Do not derive a branch by diffing two maps.** *Because* it inverts the direction the whole design runs in: the patch is the primary record, and a difference computed after the fact is a reconstruction that cannot tell "the user supposed this" from "the model happened to number it differently this run", and cannot recover the *order* the edits were made in — which, as the table above shows, is load-bearing. **Do** derive the difference from the branch. `diff.md` (stack 03a) renders it; it never has to infer it.

---

## Open questions

Raised 2026-09-16. Each needs Kent.

1. **`apply` must return something `apply` can take again.** Otherwise law 2 does not type-check. But `do` fixes a claim's value and `Proposition` has nowhere to record one — the shapes sheet gives it no such field. So `apply` either returns a map plus the fixed values alongside it, or `Proposition` grows a field that only a branch's world ever uses. `propagation.md` (stack 03a) settles it; this chapter states the laws and deliberately does not pick.
   **Decided 2026-09-17:** the first. `apply` returns the map **together with an ordered list of assignments**, one entry per value an edit fixed: which claim, to what value, from which date, and which edit did it. That pair — map and assignments — is also what a further `apply` takes, so law 2 still type-checks and folding a child branch on top is still concatenation. `Proposition` grows no "fixed value" field, because a fixed value is a fact about a **world**, not about a claim: written onto the claim it would make the same claim mean different things in different worlds, and the base map would stop being the one thing every branch agrees on. Keeping the list ordered is what lets a later assignment be shown as overriding an earlier one rather than silently replacing it — the tile's *Supposed · Oct 1 → Retracted · Oct 2* line (UX-14 in `PRODUCT_REQUIREMENTS.md` §7). Stack 03a writes it.
2. **Where the seed is stored.** The replay triple needs it, but `Branch` carries nothing but its four fields. Per world, per session, or per request? Stack 05 (persistence) decides; until then it travels with the request that asks for the world.
3. **Nothing forbids a branch from being its own ancestor.** The `parent` chain could loop, and the domain cannot catch it because it sees one branch at a time, never the collection. This looks like a rule for whatever stores branches (stack 05), and it wants a violation code so the failure is legible rather than a hang.
   **Decided 2026-09-17:** the code is **`edit_not_applicable`** — "this edit cannot be folded onto this map as written" — and the walk that catches it is `flatten`, which resolves a branch's parent chain and concatenates the edits, parent first. `flatten` is handed the whole collection of branches, so it *can* see the loop: it walks the chain remembering where it has been, and returns a violation rather than hanging the moment it arrives somewhere twice or names a parent that is not there. The same code covers both faults, because from the user's side they are one thing — this chain cannot be followed. Storing branches so the loop cannot be created in the first place is still stack 05's; this is the walk's own net, and it ships with `apply` in stack 03a. See [`interventions.md`](interventions.md), open question 5, decided the same day.
4. **Can a branch be re-parented?** "Show me these two edits, but on top of the base instead." Law 2 makes it trivial to compute and the interface has no verb for it. Not needed for the hero flow; cheap to add later.
5. **`label` is required, but committing an edit should not stop to ask for a name.** This chapter assumes a name suggested from the first edit ("Hormuz opens") that the user can overwrite. `spec/workbench/` owns that interaction.
6. **Link identifiers have no fixture convention.** Proposition identifiers are fixed (`H`, `C`, `B`, `R`, `S`, `M1`, `M2`, `N1`); link identifiers are not. This chapter writes them `S->C`, meaning the arrow from S to C. Pull request 4 of this stack should settle it so the spec and the fixture agree.
   **Decided 2026-09-17:** the convention this chapter already writes. In the fixture a link identifier is `SOURCE->TARGET` — the identifier of the claim the arrow starts at, then `->`, then the identifier of the claim it ends at, as in `H->B`. A test pins it, so the fixture and the spec cannot drift apart. It is a fixture convention only: outside the fixture our code mints identifiers and nothing may parse meaning out of one (decision record 0003).
