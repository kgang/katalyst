# Generation — where the map comes from

## The idea

The model is a source of **proposals**, not of truth. It suggests propositions and links one at a time; code the team wrote checks each proposal against the rules of the graph and either accepts it or rejects it with a reason. The model never assigns identifiers, never decides validity, and never edits the graph directly.

Generation is small calls composed into a pipeline, not one giant prompt: one proposal per call, so each is checkable, streamable, and cheap to retry. Every accepted or rejected proposal is an event streamed to the browser, so the user watches the map grow as the model reasons — that stream *is* the loading state.

Evidence is attached at generation time from web search; a link without evidence is marked *asserted* and looks different on the canvas. Every generation records what it cost.

## Terms this part owns

Proposal · Rejection · Generation receipt · Grounding · Streaming.

## Invariants this part owns

| ID | Statement |
|----|-----------|
| INV-13 | Continuous integration runs with no API key; the model boundary is exercised only through recorded responses |

## Chapters

| Chapter | Covers | Written in |
|---------|--------|-----------|
| `proposals.md` | The proposal schema, the one-proposal-per-call pipeline, acceptance and rejection | stack 04 |
| `grounding.md` | Web search at generation time, evidence attachment, base-rate elicitation before the inside view, critique pass | stack 04 |
| `streaming.md` | Event types over the server-to-browser stream, ordering, resumption | stack 04 |
| `evaluation.md` | Recorded-response tests, the out-of-band evaluation set on the four assignment examples, pastcast self-test | stack 04 |

Decision records behind this part: ADR-0006 (model boundary), ADR-0008 (testing layers).
