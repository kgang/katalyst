---
# ADR-0028: One likelihood per claim, computed once; no range anywhere
status: accepted
date: 2026-09-22
decision-makers: Kent Gang
consulted: the 2026-09-22 batch Kent tried on screen, which is what raised it; ADR-0014 (whose range this reverses); ADR-0016 (whose exact core makes the versions removable in one place); ADR-0005 and ADR-0015
informed: agents in `backend/src/katalyst/domain` and `engine/`, on the canvas, and on stack 05's flip
supersedes: none
superseded-by: none
spec-impact: spec/multiverse/propagation.md, spec/multiverse/diff.md, spec/graph/belief.md, spec/vocabulary.md, spec/workbench/ (the screen half), PRODUCT_REQUIREMENTS.md NFR-1 and FR-21
---

# ADR-0028: One likelihood per claim, computed once; no range anywhere

> **In short.** The engine stops running two thousand versions of the map, and **no number on this product carries a range** — not on a tile, not in the panel, not on the change list, not in a footer or a hover. One likelihood per claim, computed once. The *same direction 95%* share goes with the versions, because it was a share **of** them, so a change-list row now needs one thing: a move of `.005` or more.
>
> **Why.** Kent, having tried it: *"The 2,000 runs thing is confusing. Can we cut that from the scope of this project completely for the sake of defending its design…?"* He was told first that the engine pass is a fraction of a millisecond and the model calls are the time, so **this buys simplicity, not speed**, and chose it anyway.
>
> **What it reverses.** Record 0014's range and record 0005's *two significant figures with an interval*. **Two significant figures and both guards stay.**

## Context and Problem Statement

Record 0014 gave every computed number a **range** — `lo` and `hi`, the 10th and 90th percentiles of the likelihood itself — meaning *how sure we are of the number we put in*, never *how much the world can move*. It was produced by running the whole map two thousand times over, each run taking every claim's likelihood from that claim's own stated range. Record 0016 kept the two thousand and made each one exact.

The idea is defensible and the arithmetic is sound. **It is also the one thing on the screen that nobody could read.** Kent tried the built product on 2026-09-22 and said so. A range that is uncalibrated, that is about our own numbers rather than about the world, and that needs a paragraph of hover copy to stop a trader reading it as volatility, is a second number per claim that costs a reader attention on every tile and gives back a caveat.

So: **does version one carry a range at all?**

## Decision Drivers

* **Defending the design.** Kent's own word. Every number must be explainable in a sentence, and this one was not.
* **One rule over two.** Two numbers per claim, two columns on the change list, two formatting rules, two labels — against one likelihood.
* **The traceability veto is not at stake either way.** A single computed likelihood still traces to an input, a rule and a source. Nothing honest is lost by dropping the second number; what is lost is a statement we were making about our own uncertainty.
* **Remove it once, in one place.** The exact core is being rewritten now, so the versions can come out of one rewrite rather than being stripped from a shipped engine later.

## Considered Options

* **A. Keep the range, explain it better.** More copy, the same two numbers.
* **B. Keep the versions in the engine, stop drawing the range.** The screen gets simpler; the engine keeps the cost and the machinery.
* **C. Cut it from the engine too.** One likelihood per claim, computed once; no range anywhere.

## Decision Outcome

Chosen option: **C**, because a number the reader cannot use is not made usable by a hover note, and leaving the machinery in place to feed nothing would be the untraceable half of B — an engine doing work no screen can account for.

**What is cut.**

| | Gone |
|---|---|
| The versions | the two thousand versions of the map, the spread that draws each claim's likelihood from its stated range, the even spreading of those draws, and the `versions` argument as anything but a historical field |
| The range | `lo` and `hi` as a *range*; the split fitting of a stated `{p, lo, hi}`; the *model interval, uncalibrated* label and its hover |
| The agreement share | *same direction N%*, the 90% bar, and the `agreement` field's meaning. It was a share **of versions** |
| The width columns | `range_width` on a change-list row, and `range_shares` — whose stated number explains whose width (FR-21's *where to spend modeling budget*) |
| The arrows' spread | record 0014's decision G, *how well-backed an arrow is becomes how wide it is drawn*. It existed only to make versions differ |

**What stays.** One likelihood per claim, from record 0016's exact core, still the chance the claim comes out true by its own deadline. **Two significant figures, and both guards** — `<.01` below a hundredth, `>.99` above ninety-nine hundredths, and a **move** still written at two figures however small. The three owners, never merged. The seed and byte-identical replay. The `.005` floor. The change list's ranking on two factors — the size of the move times the weakest backing on the best-backed route — untouched, because neither factor was ever a version.

**What a change-list row now needs: a move of `.005` or more, and nothing else.** `unchanged` keeps one reason where it had two: `under_the_floor`. The value `versions_disagree` becomes unreachable the day this lands.

**Record 0015 is not reversed and loses its reader.** The model still states a range in a proposal, because what the model is asked for moves the prompt fingerprint and every recording with it; nothing in version one reads it. Whether to stop asking rides stack 05's shape freeze.

### Consequences

* Good, because every claim on screen carries one number that answers one question, and the sentence explaining it is the claim's own sentence.
* Good, because a large amount of machinery leaves the core in one rewrite rather than in two: the version axis, the drawing of likelihoods and of arrow numbers, the even spreading, the width shares, the weighting that was already gone.
* **Neutral on speed, and this record does not claim otherwise.** Kent was told before he chose that the engine pass is a fraction of a millisecond beside the model calls. The version axis simply runs at **length one**; every array keeps its shape, and a version enters as a scalar multiplying arrays built once, exactly as before.
* Bad, because the product can no longer say *this number would move with more homework* or rank where that homework would pay. FR-21 has no number behind it and is not built in version one.
* Bad, because `lo` and `hi` stay on the wire for a while carrying nothing: **they are set equal to `p` and every reader ignores them**, until one follow-up pull request after the browser round removes the two fields, `agreement`, `range_width`, `range_shares` and `unchanged_because`'s second value together. A field that is always equal to another field is a field somebody will eventually believe.
* Bad, because a stated range that no longer reaches a reader is still being elicited, and paid for, until the shape freeze.

**Replacement words owed outside this record**, because `PRODUCT_REQUIREMENTS.md` is edited by several lanes and the coordinator places this:

* **NFR-1**, whose first clause reads *"Beliefs render at two significant figures — the number and both ends of its range — with their interval (`.35 (.22–.50)`), never `.347`"*, becomes:
  > **NFR-1 Honesty.** Beliefs render at **two significant figures and nothing else** — `.35`, never `.347`, and **never a range** *(amended 2026-09-22; decision record 0028: one likelihood per claim, computed once)* — and never as a certainty: a likelihood below `.01` prints `<.01`, and one above `.99` prints `>.99`.

  The rest of NFR-1 — the two guards, *a move is not a likelihood*, and *every number is one click from rationale, sources, base rate* — is untouched.
* **FR-21** gains the line: *Not built in version one — decision record 0028: the quantity it ranks is a share of a range, and there is no range.*
* **Anti-pattern 5 of `spec/graph/belief.md`'s list**, *"Do not ship a bare point with no range"*, is **deleted**: a bare point is what this product ships.

### Confirmation

* `test_a_computed_belief_has_no_range` — every belief a world carries satisfies `lo == p == hi`, on generated maps, until the fields go.
* `test_nothing_draws_a_version` — a source check over `backend/src/katalyst/domain/`: no Latin hypercube, no per-version drawing of a claim's likelihood or an arrow's number, and the version axis is length one.
* `test_shifted_is_the_floor_alone` — a claim is `shifted` exactly when it moved by `.005` or more; no second condition.
* **Deleted with the thing they checked:** `test_band_is_not_sampling_noise`, `test_freezing_the_priors_alone_leaves_the_arrows_talking`, `test_range_matches_analytic_first_order_on_fixture`, `test_link_spread_comes_only_from_provenance`, `test_a_documented_arrow_gives_a_narrower_band_than_an_asserted_one`, `test_adding_an_arrow_does_not_move_another_arrows_draws`, `test_shifted_needs_agreement`, `test_versions_do_not_depend_on_the_branch`.
* `make numbers-check` green on a numbers file with no `lo`, no `hi`, no *band from* line and no *same direction* line.

## Pros and Cons of the Options

### A. Keep the range, explain it better

* Good, because the honest statement *we are not sure what number to give you* is a true and useful one.
* Bad, because it had already been explained as well as anyone could, in a label and a hover paragraph, and it still read as volatility. Kent tried it.

### B. Keep the versions in the engine, stop drawing the range

* Good, because it is reversible in an afternoon if he changes his mind.
* Bad, because the engine would then compute two thousand versions of every map to produce a number nothing reads — work that cannot be traced to anything on screen, which is the state this product refuses.

## More Information

* **Kent's decision, 2026-09-22**, decisions note row **R48**, in his words: *"The 2,000 runs thing is confusing. Can we cut that from the scope of this project completely for the sake of defending its design and also potentially to make the speed of the real time map construction a lot snappier and quicker?"* He was shown three options and told that the engine pass is a fraction of a millisecond against the model calls, so the cut buys simplicity rather than speed. **Split in two:** the screen half lands in the browser round; the engine half, the API and these chapters ride stack 05's flip, so the machinery leaves in one place.
* **Related.** ADR-0014 (the range it reverses; a dated amendment at that record's foot) · ADR-0005 (*two significant figures and the interval on the canvas*; a dated amendment at its foot) · ADR-0016 (the exact core, whose version axis now runs at length one) · ADR-0015 (unreversed; the range it ships has no reader) · ADR-0020 (which had already found that a market belief has no range).
