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
2. **Data model** — the **shape**: the fields, what each one means, any constraint the type itself cannot carry, and the name of the module that defines it — never the class body, and a diagram where a picture shows a mechanism. A chapter that pastes the code in goes stale the first time a field is renamed and says nothing the code did not already say; a chapter that says what a field is *for* is the only place that says it at all. (Decided 2026-09-21. Each chapter is brought into line in the pull request that next touches it, never as a sweep of its own.)
3. **Behaviour** — numbered user-visible flows (`B1`, `B2`, …), each with a worked example on a real event from the assignment.
4. **INVARIANTS** — numbered statements that must always hold, each written as *for all inputs drawn from generator S, statement P holds*, and each naming the automated test that checks it. If no generator can be named, it is a wish, not an invariant, and belongs under Behaviour.
5. **ANTI-PATTERNS** — *do not X, because Y; do Z instead*, each traceable to a real temptation.
6. **Open questions** — dated, so the chapter visibly ages.

Product-level invariants (`INV-1` … `INV-14`) are stated in `PRODUCT_REQUIREMENTS.md` §9. A part *owns* the invariants listed on its landing page and refines them into testable form; a part may add local invariants numbered `INV-<part>.<n>`, for example `INV-multiverse.3`.

## Writing rules

Every page stands alone: explain a term where it is used, or link to `vocabulary.md`. No unexplained abbreviations or symbols. Concise and punchy; formatting is a legibility aid, not decoration.

**A number the engine computes appears in a chapter only where the numbers file is one link away.** That file is [`docs/worked-numbers.txt`](../docs/worked-numbers.txt): `make numbers` writes it from the shipped engine on the Strait of Hormuz map, the build fails when it goes stale, and every line starts with a name a chapter can cite — `B · base · reading`. Quote the figure if quoting it teaches something, and link to the line; the day the arithmetic changes, the diff of that one file is the whole list of what moved. Numbers a person typed into the example — a stated prior, an arrow's strength, a date — are in a part of their own in that file, are stable, and need no link.
