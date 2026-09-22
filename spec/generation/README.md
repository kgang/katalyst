# Generation — where the map comes from

## The idea

The model is a source of **proposals**, not of truth. It suggests claims and arrows one at a time; code the team wrote checks each proposal against the rules of the map and either accepts it or rejects it with every reason at once. The model never assigns identifiers, never declares its own provenance, and never decides whether a map is legal — the fields for those things do not exist on a proposal, so it is structurally unable to, rather than merely discouraged.

Generation is small calls composed into a pipeline, not one giant prompt: one proposal per call, so each is checkable, streamable, and cheap to retry. **Every accepted and every rejected proposal is an event streamed to the browser, and that stream *is* the loading state** — there is no spinner anywhere in this product.

Evidence is attached at generation time from search, and **provenance is written by us from what actually happened**: an address the search tool itself returned in that call makes an arrow `documented`; a mechanism stated with no such address makes it `argued`. An address the model typed that no search returned is not a source — it is dropped, with a note in the transcript. Because a rationale is required on every arrow, generation produces only those two words; `asserted` survives on hand-written maps, where a person judged their own sentence to be a story rather than a mechanism.

Every generation records what it cost. **Which model wrote it is one named setting** — `KATALYST_MODEL`, defaulting to `claude-sonnet-5` while this is a prototype (Kent, 2026-09-20) — and nothing else in the pipeline knows which model it is; the price table is per model, and a scorecard compares runs of the same one unless it says otherwise.

And with no model key, an example hypothesis plays from a committed recording through the same route, the same stream and the same canvas, so a reviewer who has spent nothing still sees the whole thing. Four sentences are offered — `hormuz`, `midterms`, `export-controls`, `photonics` — and **one of them, `hormuz`, is recorded**; the other three cards say so rather than failing, and each is recorded by `make record-demo ONLY=<example>` when somebody chooses to pay for it. **A recording shows every refusal the run produced and no others**: an early live run refused none in 26 proposals, and a screen that said otherwise would have been arranged.

## Terms this part owns

Proposal · Rejection · Generation receipt · Grounding · Streaming · Transcript · Recording · Replay · Cassette · Eval case · Scorecard.

**All of them are defined in the chapters below, where they are used** — [`../vocabulary.md`](../vocabulary.md) carries the words the interface says out loud, and none of these eleven is one of them. A later sweep may promote the ones that earn a place there.

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-13 | Continuous integration runs with no model API key; the model boundary is exercised only through recorded responses |

**Local invariant numbers (`INV-generation.<n>`) come from one pool shared by all five chapters**, so a reader can cite one without saying which chapter it is in. The blocks:

| Chapter | Holds |
|---|---|
| `proposals.md` | `INV-generation.1` – `.8` |
| `grounding.md` | `.9` – `.15` |
| `streaming.md` | `.16` – `.22` |
| `replay.md` | `.22` – `.27` |
| `evaluation.md` | `.28` – `.32` |

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| [`proposals.md`](proposals.md) | The proposal schema; one proposal per call; what the model may and may not name; accept and mint, or reject with every reason; the caps and the stop rules; the Verify door and `no_path` | stack 04 — written, `engine/` built |
| [`grounding.md`](grounding.md) | Search at generation time; how a search result becomes a source; **how provenance is written by us from what was found**; base rates before the inside view | stack 04 — written, `engine/` built; `grounding/` is stack 05's |
| [`streaming.md`](streaming.md) | The eight events and the one live-only line that is never recorded, their order as a grammar, the transport, the three routes, what a client does with an event name it does not know | stack 04 — written, `api/generate.py` built |
| [`replay.md`](replay.md) | The recording format; what replay rebuilds and what it recomputes; the two recording commands and why a paid run is never discarded; the one recorded intervention; how refusals are shown honestly; the prompt hash; the `recordings` build job | stack 04 — written, `engine/replay.py` built; one recording committed |
| [`evaluation.md`](evaluation.md) | The cassette layer; the four eval cases and their structure-only checks; the scorecard's columns and the one measured run they came from; what is deliberately not measured | stack 04 — written, `evals/` and the cassettes built |

**Three things this part deliberately does not cover.** FR-9's adversarial critique pass is **out of stack 04** (Kent, 2026-09-17): it roughly doubles the calls and its value cannot be read without a scorecard to compare against, so it is revisited in stack 07. There is **no ensemble and no reconciliation of two maps** (decision record 0015): the range a proposal states ships as stated, labelled *uncalibrated*. And **the stream cannot be resumed** — the transport decision rules it out, and there is nothing to resume from until stack 05 stores a transcript. The pastcast self-test (FR-30) is stack 07's, and [`evaluation.md`](evaluation.md) carries the dated question.

Decision records behind this part: ADR-0003 (the model proposes, our code disposes), ADR-0006 (the model boundary — one proposal per call, structured output, search, caching, refusals), ADR-0008 (the testing layers and the recorded responses), ADR-0012 (replay from recorded generations), ADR-0015 (a claim's starting number and range come from what the model stated, labelled — not from an ensemble).
