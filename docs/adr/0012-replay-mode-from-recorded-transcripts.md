---
# ADR-0012: Replay mode — a reviewer with no API key walks the hero flow from recorded generation transcripts
status: accepted
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
| **The recording must show a miss** | Each of the four holds at least one `proposal_rejected` event — a proposal that would close a loop, or a claim with no resolution criteria — so the reviewer watches the validator refuse the model, not only the happy path. *(Amended 2026-09-20, after the live runs of 2026-09-17: a recording shows **every** refusal that occurred, and when there were none the screen says so in one line. Nothing is re-run to manufacture a miss. See the amendment at the foot of this record; the original rule stands as written.)* |

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
* `make record-demo` exists, is in the README, and is the only way recordings are written. Continuous-integration job `recordings`: every file under `backend/recordings/` parses, holds at least one `proposal_rejected` event, and carries a prompt hash equal to the current prompt's. `gitleaks` already scans them for keys (NFR-8). *(Amended 2026-09-20: the job keeps the parse check and the prompt-hash check and loses the refusal check — see the amendment at the foot.)*

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
* Accepted by Kent on 2026-09-17. Built in stack 04.
* `plans/roadmap-03-to-06.md`, stack 04 ("Propose replay mode here") and the Definition of done: *"With no API key, replay mode still demonstrates the full flow"*.
* FR-13 (replay from base graph, branch and seed; transcripts stored) · INV-13 (keyless continuous integration) · NFR-2 (determinism) · NFR-8 (no key in a committed file) · FR-3 and UX-13 (the launchpad's four cards) · FR-5 and UX-8 (streaming is the loading state).
* ADR-0006 (one proposal per call over server-sent events; the receipt; the transcript) and ADR-0008 (cassettes, and the re-recording rule this decision copies).

## Amendment (2026-09-20) — a recording shows what happened, refusals or none

**The rule "each of the four holds at least one `proposal_rejected` event" is replaced by: a recording holds *every* refusal that occurred, and when there were none, the screen says so in one line.** Kent decided this on 2026-09-20, after the first live runs were measured, and it is the honest form of what the original rule was reaching for.

**The evidence, plainly.** Two full live generations of the Hormuz example, made on **2026-09-17**, produced **twenty-six proposals and not one refusal**. The measured run — the one whose receipt survived — made 10 model calls and 9 searches, cost **$1.32**, took **10 minutes 54 seconds**, and ended at the width cap with 10 claims and 9 arrows; the earlier run accepted 16 proposals in about 9 minutes. The validator was working the whole time; the model simply did not break a rule. Re-running until it errs costs a **full generation each time — about a dollar and a third, and about eleven minutes, at the rate measured** — with no guarantee that any given run produces one. The original rule therefore could not be satisfied except by staging a miss, and a staged miss is a number nobody computed wearing a different hat.

**What a reviewer with no key still sees the validator do.** A **refused edit of their own** shows every reason at once, in the validator's own sentences — built in stack 04a's join and pinned by `test_a_refused_branch_shows_every_reason_at_once`. Interventions are live arithmetic on a replayed map (the rule above), so this path needs no key and no luck. The validator refusing *the model* is shown whenever it happened; the validator refusing *the user* is shown on demand.

**Nothing is staged and nothing is re-run to improve a recording.** No hand-written refusal is dropped into a file, no recording is thrown away for being too clean, and `make record-demo` remains the only way a recording is written. A recording says what happened on the day it was made.

**What this changes elsewhere in this record.** The `recordings` job keeps two of its three checks — every file parses, and every prompt hash equals the current prompt's — and **loses the refusal check**; a recording with no refusal in it is green. The *Consequences* bullet that says the one-rejection rule takes away "a standing temptation to record only the runs that went well" now rests on two different rules: a recording is exactly what `make record-demo` wrote, and the screen states what the recording contains, including the one-line sentence when nothing was refused. The *Pros and Cons* line "rejections included" reads as *every rejection that occurred, included*.

Amended in place rather than superseded, because nothing in the decision changed: replay still plays the real stream through the real canvas, and the one rule that moved was a rule about what a recording must contain, which measurement showed we cannot honestly require.

## Amendment (2026-09-21)

The `instant` flag named in *Decision Outcome* above is now one setting, `KATALYST_REPLAY_PACE`, the pause between two events in seconds, where `0` means no pause at all — a length and a switch that means *none* are two answers to one question. Pacing is otherwise exactly as decided: cosmetic, fixed on the server, never a field on the request.

## Amendment (2026-09-21, later the same day) — the request names what it wants, and the server never substitutes

**Status: `accepted` — 2026-09-22, Kent, by merging the round (decisions note, row R43).** It was written `proposed` on 2026-09-21; the first screen that depends on it landed in the same batch. Everything above stands unless this section says otherwise.

### What changes

The rule **How the app chooses** in the table above — *"No key → the launchpad offers the four as replays… Key present → the same four run live, untouched by any recording"* — is replaced by:

> **A generation is asked for as a live run or as a recording, and the request says which.** The server does what it was asked, or says plainly why it cannot. **It never substitutes one for the other**, in either direction.

`settings.py` is still the only place the environment is read, and the key is still what decides whether a live run is *possible*. What the key no longer decides is what a reader gets.

### Why this is not a retreat from the no-fallback rule

**A reader choosing a recording, labelled a replay, is not a fallback.** A fallback is the server quietly handing back one thing when another was asked for, and that is still forbidden here — a live run that fails is a live run that failed and says so. What this record has always been against is *the server choosing on the reader's behalf*, and reading the key to make that choice is exactly that. It leaves the reader with no say in either direction: with a key the committed recording is unreachable, and with none a live run cannot even be asked for, so the only control anybody has over which path runs is deleting a line from a file.

Kent found that by hand on 2026-09-21 and asked the two questions this amendment answers: *"Why do i need to blank out the anthropic key?"* and *"How can i test out all the functionality if I run it with a valid anthropic key?"* The answer to the first was *because blanking it is the only control there is*, and to the second, *you cannot*. Both stop being true here.

### The four cases, all honest

| Asked for | Key configured | What happens |
|---|---|---|
| A recording | yes | **The recording plays**, badged a replay, receipt saying `replay` and zero dollars. The key is not read. This is the case that could not happen before |
| A recording | no | The recording plays, exactly as it does today |
| A live run | yes | A model is called, exactly as it does today |
| A live run | no | **Refused in one sentence** naming what is missing and what can be asked for instead. Nothing is played in its place. This is the case that could not happen before |

A recording that was asked for and does not exist keeps the sentence it already has: *"…no recording of that sentence, so there is nothing it can honestly show you."* Four cases, four answers, and no path where the server picks for you.

### What a request that says nothing gets, and why

**A request that does not name a start plays a recording.** The reasoning is one sentence: *a request that did not ask to spend money must never spend it.* The recorded Hormuz run's own receipt, in `backend/recordings/hormuz.jsonl`, says what the other reading would cost — **29 model calls, 2,179 seconds (about thirty-six minutes) and $4.04, on 2026-09-21**, at the recorder's effort. Between two readings of a silent request, the one that cannot surprise anybody with a bill is the only defensible one, and it is also the one that keeps every keyless caller working unchanged: the browser's end-to-end tests, the `curl` recipes, the committed recording.

**A default is not the server choosing.** It is a property of the request shape, published in the server's own description of itself, the same on every copy of this program; it reads no key, no environment and no folder. What this record forbids is the server reading the situation and deciding — and a default reads nothing.

### What this does not change

* **Pacing** stays cosmetic, fixed on the server, never a field on the request (amendment above). Naming *which* start a run has is a different question from naming how fast it is shown.
* **What a recording contains** is untouched: `make record-demo` is still the only writer, a recording still shows every refusal that occurred, and nothing is re-run to improve one.
* **Nothing that changes what is recorded.** The field is a field of this product's own HTTP body. It never reaches the vendor, so it is not in the prompt's fingerprint — which covers the standing text and the shapes an answer must fit (`engine/prompt.py`) — and it is not in the cassettes, which record vendor HTTP (`backend/tests/conftest.py`). The committed recording stays playable and the freeze on prompt changes is untouched.
* **Interventions** are unchanged: live arithmetic on a replayed map, with the one scripted insert each recording carries.

### What it leaves room for

A finished generation served back by its identifier — planned for stack 07 — is **a third value of the same field**, not a second route: three ways a run can start, one field that names which, one place that reads it.

Amended in place rather than superseded, because the decision is unchanged. Replay still plays the real stream through the real canvas; the only rule that moved is *who* says which of the two a reader is watching.
