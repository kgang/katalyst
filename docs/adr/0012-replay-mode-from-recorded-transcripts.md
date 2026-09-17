---
# ADR-0012: Replay mode — a reviewer with no API key walks the hero flow from recorded generation transcripts
status: proposed
date: 2026-09-17
decision-makers: Kent Gang
consulted: ADR-0006 (model boundary), ADR-0008 (testing layers and cassettes); the roadmap for stack 04 (generation), where replay would be built
informed: future agents working in backend/src/katalyst/engine and on the launchpad
supersedes: none
superseded-by: none
spec-impact: spec/generation/ (recording and replaying a generation — a new chapter beside `streaming.md`), spec/workbench/ (the launchpad's "replaying a recording" state)
---

# ADR-0012: Replay mode — a reviewer with no API key walks the hero flow from recorded generation transcripts

## Context and Problem Statement

The people reading this prototype are the Catalyst team. The likely path is: clone, `docker compose up`, open the browser — and stop, because the app wants an `ANTHROPIC_API_KEY` they have no reason to spend. Everything the prototype is judged on lives past that point: the map drawing itself step by step, a step changed, two worlds compared, a thesis with a derived stop-loss.

INV-13 already guarantees that *continuous integration* — the automated build that runs on every push — passes with no key, because the model boundary is exercised through **cassettes**: raw HTTP exchanges with the vendor recorded to disk and replayed in tests (ADR-0008). That is a guarantee about the test suite, not about the product. A green build proves the code is exercised; it does not let a stranger type "The Strait of Hormuz is going to open next week" and watch a map grow.

`ASSIGNMENT.md` names four example hypotheses — Hormuz opening, a split midterm, export restrictions on frontier models, faster-than-expected photonic chips — and FR-3 already puts them on the launchpad (the empty first screen) as cards. Should a keyless clone be able to run those four, and what does it play back from?

## Decision Drivers

* The hero flow (§5) is the deliverable. A reviewer stopped at a credential prompt has reviewed nothing.
* FR-5 and UX-8: the map growing **is** the loading state; a replay that hands over a finished graph demonstrates the wrong product. D5(ii), the "not knowing why it did that" veto: a replay must announce itself, on screen and in the stored record.
* FR-13: every generation already stores a **transcript** — what was proposed, accepted, or rejected and why, in order — plus the generation **receipt**, the tally of model, tokens, cache hits and dollars. Both are product artifacts shown in the Inspector, not test fixtures.
* NFR-2: the same `(base graph, branch, seed)` yields byte-identical worlds. NFR-8: nothing committed may contain a key.
* Solo developer, fixed deadline: this must be near-free at stack 04, where transcripts already exist.

## Considered Options

* A. **Replay from stored generation transcripts** — one committed transcript per example, played through the same server-sent event stream (a one-way stream from server to browser) the live path uses, at a paced cadence.
* B. Reuse the test cassettes as the demo source.
* C. A static pre-built graph per example, loaded as a fixture; no streaming.
* D. No replay mode; the README says "needs a key".

## Decision Outcome

Chosen option: "A", because the transcript is already something the product stores and shows (FR-13), playing it drives the real stream and the real canvas rather than a stand-in, and it can label itself honestly everywhere a reviewer looks.

If accepted, the rules are:

| Rule | What it means |
|---|---|
| **Where recordings live** | `backend/recordings/<example>.jsonl` — one committed file per example, one JSON object per line, in stream order, each line one event of the live stream: `proposal_accepted`, `proposal_rejected`, `beliefs_propagated`, `done`. A header line carries the base graph identifier, the seed, the date, and a hash of the prompt recorded against |
| **How they are made** | `make record-demo` runs the four examples live against a real key. A recording is re-made whenever a prompt changes — the rule cassettes already carry (ADR-0008), on the same checklist item: *"prompt changed? cassettes re-recorded, demo recordings re-recorded"* |
| **How the app chooses** | `settings.py` is the only place the environment is read. No key → the launchpad offers the four as replays and **says so on screen**: "No model key configured — these four run from recordings made on \<date\>." The free-text field is visibly disabled with that same sentence, never silently inert. Key present → the same four run live, untouched by any recording |
| **A replay says it is a replay** | A `replay` badge on the canvas for the session; the receipt stores `mode: "replay"`, the recording's date and hash, and zero dollars rather than the original run's cost. Any number still clicks through to that transcript, marked replayed |
| **Byte-identical every run** (NFR-2) | Pacing is cosmetic — a fixed delay between events so growth reads at human speed — and never changes content or order; an `instant` flag drops it for tests. Beliefs are not replayed as numbers: the recording carries the seed and `domain/` re-propagates, so replay and live agree by construction (INV-5) |
| **Interventions are computed live** | `do`, `observe`, `retune` and `believe` are pure arithmetic in `domain/` — no model, no key, full fidelity. `insert` is the exception: a typed "…but Iran is struck the next day" drafts a claim through the model, so **each recording also carries one recorded intervention**, the scripted "…but X" its card offers. Any other insert is plainly declined: "drafting a new claim needs a model key" |
| **The recording must show a miss** | Each of the four holds at least one `proposal_rejected` event — a proposal that would close a loop, or a claim with no resolution criteria — so the reviewer watches the validator refuse the model, not only the happy path |

### Consequences

* Good, because the keyless path exercises the real route, stream and canvas; the only substitution is where the bytes came from. Interventions stay live, so the multiverse is not faked at all.
* Good, because the transcript is stored and rendered anyway (FR-13), so replay mode is mostly a reader for it.
* Bad, because recordings go stale when prompts change, less visibly than a cassette: no test fails, the demo just shows old wording. Mitigated by the recorded prompt hash, which the build compares against the current prompt.
* Bad, because four transcripts of roughly 30 claims each are committed text — a few hundred kilobytes; past a megabyte, drop the stored reasoning and keep the proposals. And there is a standing temptation to record only the runs that went well, which the one-rejection rule takes away.
* Neutral, because replay is presentation, not architecture: no new layer, no new dependency, and removing it would cost the live path nothing.

### Confirmation

* `test_replay_stream_matches_recording` — the events a replayed generation emits equal, line for line, the recording played from.
* `test_replay_is_byte_identical_across_runs` — two replays of one file give the same world (NFR-2).
* `test_replay_is_labelled_in_receipt` — the receipt carries `mode: "replay"`, the recording's date and hash, and zero dollars.
* `test_intervention_on_replayed_world_needs_no_model` — `do`, `observe`, `retune`, `believe` on a replayed map resolve inside `domain/`.
* Frontend rendering test: with no key configured, the launchpad shows the four cards **and** the "these run from recordings" sentence, and the replay badge is on the canvas.
* `make record-demo` exists, is in the README, and is the only way recordings are written. Continuous-integration job `recordings`: every file under `backend/recordings/` parses, holds at least one `proposal_rejected` event, and carries a prompt hash equal to the current prompt's. `gitleaks` already scans them for keys (NFR-8).

## Pros and Cons of the Options

### A. Replay from stored transcripts (chosen)

* Good, because it plays through the real stream at the real granularity — one proposal at a time, rejections included — in a format we must design and render regardless (FR-13).
* Good, because it records *what was decided*, not what was said over the wire, so a reworded prompt leaves a recording dated rather than broken.
* Bad, because it is a second recorded store beside the cassettes, with a second re-recording chore.

### B. Reuse the test cassettes

* Good, because nothing new is committed and one store serves both purposes.
* Bad, because cassettes are raw HTTP matched on request shape and prompt wording; a whitespace change in a prompt breaks the demo, and breaks it as a crash rather than a stale date.
* Bad, because they cover what the tests cover and are shaped for assertions, not four polished runs worth watching — and the app would load a test-only library at runtime.

### C. A static pre-built graph

* Good, because it is the least code and cannot drift into an error.
* Bad, because it deletes what the flow is judged on: a graph that simply appears is the "spinner then dump" the anti-patterns list vetoes (FR-5, UX-8), and there are no rejections to see, so the validator is invisible.

### D. No replay

* Good, because zero work and zero staleness.
* Bad, because it makes the reviewer's first act a decision about spending money, and the most persuasive minute of the prototype sits behind it.
* Neutral, because a README screen capture (proposed stack 07) helps, but a recording someone can steer is not a film they watch.

## More Information

* Kent's answer, 2026-09-16: yes to replay mode in principle; recorded as `proposed`, and nothing is built against it until he accepts (AGENTS.md; anti-pattern 13).
* `plans/roadmap-03-to-06.md`, stack 04 ("Propose replay mode here") and the Definition of done: *"With no API key, replay mode still demonstrates the full flow"*.
* FR-13 (replay from base graph, branch and seed; transcripts stored) · INV-13 (keyless continuous integration) · NFR-2 (determinism) · NFR-8 (no key in a committed file) · FR-3 and UX-13 (the launchpad's four cards) · FR-5 and UX-8 (streaming is the loading state).
* ADR-0006 (one proposal per call over server-sent events; the receipt; the transcript) and ADR-0008 (cassettes, and the re-recording rule this decision copies).
