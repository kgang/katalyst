# The Spec — a book, not a log

Decision records (`docs/adr/`) are a **journal**: numbered because they happen in order. This directory is a **book**: organized by idea, so a reader can open the part they care about and find everything about it in one place. Parts are unnumbered; read them in the order below if you are new.

## Reading order

| Part | The idea in one line |
|------|----------------------|
| [`vocabulary.md`](vocabulary.md) | The words everything else uses, defined once |
| [`graph/`](graph/) | **The language of cause and effect.** Claims that can be checked, arrows that say why, likelihoods that say who thinks so |
| [`multiverse/`](multiverse/) | **Changing one thing.** Interventions, branches, worlds, how a change ripples downstream, and how two worlds are compared |
| [`thesis/`](thesis/) | **From map to trade.** Which step matters most, what would prove you wrong, the rare disasters, and the card you act on |
| [`generation/`](generation/) | **Where the map comes from.** How the model proposes, how proposals are checked, how evidence is attached, how it streams |
| [`workbench/`](workbench/) | **What you see and touch.** Tiles, wires, layout, the diff view, the inspector, color, motion, keyboard |
| [`probes/`](probes/) | **Spending more compute where it counts.** Splitting a claim into finer claims, simulations, role-played experts |

Each part is a directory with a `README.md` landing page (the idea, the terms and invariants it owns, its chapters) and one file per chapter. A chapter is written as the bottom pull request of the stack that implements it, and merges before any code in that stack.

## Shape of a chapter

1. **Purpose** — one paragraph: what a user can do that they could not before.
2. **Data model** — the pydantic models verbatim (pydantic is the Python library that defines and validates our data shapes), plus a diagram where a picture shows a mechanism.
3. **Behaviour** — numbered user-visible flows (`B1`, `B2`, …), each with a worked example on a real event from the assignment.
4. **INVARIANTS** — numbered statements that must always hold, each written as *for all inputs drawn from generator S, statement P holds*, and each naming the automated test that checks it. If no generator can be named, it is a wish, not an invariant, and belongs under Behaviour.
5. **ANTI-PATTERNS** — *do not X, because Y; do Z instead*, each traceable to a real temptation.
6. **Open questions** — dated, so the chapter visibly ages.

Product-level invariants (`INV-1` … `INV-14`) are stated in `PRODUCT_REQUIREMENTS.md` §9. A part *owns* the invariants listed on its landing page and refines them into testable form; a part may add local invariants numbered `INV-<part>.<n>`, for example `INV-multiverse.3`.

## Writing rules

Every page stands alone: explain a term where it is used, or link to `vocabulary.md`. No unexplained abbreviations or symbols. Concise and punchy; formatting is a legibility aid, not decoration.
