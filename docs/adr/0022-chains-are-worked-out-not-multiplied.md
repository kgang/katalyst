---
# ADR-0022: Chains are worked out, not multiplied
status: proposed
date: 2026-09-21
decision-makers: Kent Gang
consulted:
  - the engine digest of 2026-09-21 §5.2, and the adversarial pass over the design that followed it, kept locally under `plans/analysis/`
  - both midpoint reviews and three analysts, which independently call the multiplied-out path invalid
informed: agents working on the Verify door, the path bar, and stack 05
supersedes: none
superseded-by: none
spec-impact: PRODUCT_REQUIREMENTS.md INV-8 and FR-11; spec/workbench/ (the path bar and the Verify door); ARCHITECTURE.md §5 (the INV-8 row) and §10 (the path-product bullet)
---

# ADR-0022: Chains are worked out, not multiplied

> **`proposed`.** It needs proposed record 0016's exact core to exist before the replacement can be computed, and it lands after that record's flip — a different pull request. Written separately so it can be accepted, or not, on its own.

> **In short.** The multiplied-out path likelihood goes. Multiplying along a route is not the chance of anything once two claims share a cause: if a second claim is true exactly when the first is and both stand at `.5`, the product says `.25` where the chance every step goes right is `.5`. Three worked-out quantities replace it (Kent, R3): **the shift** the hypothesis makes to its destination, **the joint** — the chance every step on the named route goes right — and **the weakest arrow**, which single arrow carries most of that shift. INV-8 becomes *chains are worked out, not multiplied*, and FR-11 is rewritten to ask for the three.
>
> **On screen.** The Verify door says three true things where it said one number that was not a probability.
>
> **What it costs.** One or two extra solves each on record 0016's core — where one exact solve of a twenty-claim map measures `12.4 ms` at 200 versions and `80.4 ms` at 2 000 — and the first is the number stack 06's card needs anyway. **Server only:** the browser never read the product and already renders its absence. One browser test goes with the sentence it checked.
>
> **Open for Kent.** Nothing. It lands after record 0016's flip, in a pull request of its own.

## Context and Problem Statement

INV-8 says *"Chains multiply. Any displayed path shows the product of its link probabilities beside the narrative headline"*, and FR-11 (P0) requires that product on screen. It answers the brief's first use case — *is there a reasonable chain from A to B?* — and it is the one number the Verify door puts beside a route.

**It is not the probability of anything.** Multiplying likelihoods along a route assumes the steps are independent, and on a map where two claims share a cause they are not. Check it in one line: if a second claim is true exactly when the first is, and both stand at `.5`, the product of the route says `.25` while the chance that every step goes right is `.5`. Both midpoint reviews and three read-only analysts reached this independently. Record 0014 already admitted a second fault in the same number — its factors are each read on a **different day** — and called it *"a known wart, stated rather than hidden"*.

So: **what does the Verify door say beside a route, if not a product?**

## Decision Drivers

* **The traceability veto** (Kent): a number labelled as a probability that is not one is exactly the untraceable state he vetoes.
* **INV-8 and FR-11 are both P0.** Deleting the number without replacing it leaves the brief's first use case with no verdict at all.
* **The trade needs the first replacement quantity anyway** — stack 06's card is built on how much the hypothesis moves its destination — and each quantity is one or two extra solves on record 0016's exact core.

## Considered Options

**A.** Replace it with three worked-out quantities (below). · **B.** Keep it, labelled as what it is. · **C.** Delete it and print nothing.

## Decision Outcome

Chosen option: **A**, Kent's decision of 2026-09-21. Three quantities, each a probability or a difference of probabilities:

| | What it is |
|---|---|
| **the shift** | how much the hypothesis moves the destination: the destination's chance with the hypothesis supposed true, minus its chance with it supposed false |
| **the joint** | the chance every step on the named route goes right — a real joint, from one elimination that keeps the route |
| **the weakest arrow** | which single arrow carries most of the shift, and how much of the shift goes with it |

**Each is one or two extra solves** on record 0016's exact core. The spike measured that solve — all marginals, twenty claims, 24 slices — at **`12.4 ms` at 200 versions and `80.4 ms` at 2 000** (`timing_add.py`). *(The engine digest's `0.5 ms` for the same thing excluded the table build, which is the correction record 0016 makes of it.)* Three quantities at one or two solves each is therefore a real fraction of that record's budget, not a rounding error.

What the Verify door then says, *in an illustrative shape only — the real numbers come from the engine at the flip and are owned by the generated numbers file, and they print in the form Kent settled on 2026-09-21, `36%` for a likelihood and `8.1 pts` for a move*:

> *"Reopening moves the Brent claim by 32 pts, from 24% to 56%. Every step on the best-backed route goes right in 19% of worlds. The arrow carrying most of that shift is 'reopening → shipping recovers'; delete it and 71% of the effect goes."*

**INV-8 becomes:** *"Chains are worked out, not multiplied. Any displayed path shows the shift the hypothesis makes to its destination, the chance every step on it goes right computed as a joint, and which single arrow carries most of the shift."* **FR-11** is rewritten to ask for those three numbers. Both edits are listed for the pull request that carries this record.

### What happens in the code

The multiplication is deleted from `backend/src/katalyst/engine/verify.py:139-167` (`_multiplied_out`) and `Verdict.product` becomes always empty. **That is a server-only change**: the browser never reads the server's product and already renders the absence (`frontend/src/world/apiSource.ts:272` and `frontend/src/world/fromTheServer.ts:251`, both hard-coding `NO_PATH_PRODUCT`). The path bar's route-walking, its best-backed rule and its tie-breaks are untouched.

`ARCHITECTURE.md` §10 today says the fix for the missing product is *"one function in `domain/` beside the best-backed route"*. That item is dropped: there is no multiplication to move.

### Consequences

* Good, because the Verify door states three things that are each true where it stated one that was not; the shift is the number stack 06's card needs, so it is built once and read twice; and record 0014's admitted wart — factors read on different days — goes with the number that had it.
* Bad, because the path bar's *"the wart is said out loud rather than hidden"* test (`frontend/src/components/__tests__/pathBar.test.tsx`, named in `ARCHITECTURE.md` §5) is deleted with the sentence it checks, and the bar must be re-taught what to draw.
* Neutral, because no wire shape is added or removed — `Verdict` gains three optional numbers and its `product` stops being filled.

### Confirmation

* `test_the_shift_is_the_difference_between_two_supposed_worlds` — the shift equals the destination's number with the hypothesis supposed true minus its number with the hypothesis supposed false, computed two ways.
* `test_the_joint_is_not_the_product` — on a map where two claims on a route share a cause, the joint and the product of the same route differ; the product is not computed anywhere.
* `test_deleting_the_weakest_arrow_costs_the_share_it_claims` — remove the named arrow, re-solve, and the shift falls by the share the verdict reported, within the tolerance record 0016 states.
* `grep -rn "_multiplied_out" backend/src` finds nothing.
* The canvas keeps `test_canvas_never_combines_two_model_numbers`, which walks the syntax tree of every file that draws one of the map's numbers and fails on any multiplication of one.

## Pros and Cons of the Options

The *Decision Drivers* and *Decision Outcome* above carry each option's case; in one line, **A** is chosen because it is the only one that leaves the brief's first use case with a verdict, **B** keeps a number that is not a probability behind a caveat no reader will weigh correctly, and **C** shows nothing at all.

## More Information

* **Kent's decision, 2026-09-21**, recorded as row R3 of the dated decisions note kept locally under `plans/notes/`: replace the path product with three real quantities — the shift the hypothesis makes to the destination, the chance every step on the route goes right as a true joint, and which arrow carries most of the shift; INV-8 becomes *chains are worked out, not multiplied*, and FR-11 is rewritten. *(Those are the decisions note's words for his choice, not a transcript of his own.)*
* **The evidence.** The engine digest §5.2 of 2026-09-21, which located the multiplication, priced its deletion and its replacement, and confirmed the browser does not read it; and the adversarial pass of the same date, which independently confirmed that `Verdict.product → None` is backend-only.
* **Related records.** Proposed ADR-0016 (the exact core these three quantities are computed on) · ADR-0014 (whose section E wart this removes) · ADR-0005 (the arrows these routes walk).
