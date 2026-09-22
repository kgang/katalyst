---
# ADR-0027: A live run says what it is doing, in the model's own words, on a line that is never recorded
status: accepted
date: 2026-09-22
decision-makers: Kent Gang
consulted: Kent's own run of the app against the batch of changes, 2026-09-22, in his own words below; analyst LIVE's read-only pass over the generating path the same day (`plans/ux-round/E-live-activity.md`, with its script `plans/analysis/scripts/live/where_the_time_goes.py` and the five kept runs under `backend/.runs/`); the `claude-api` reference bundle, read 2026-09-22, for what a streamed structured-output call looks like and what a streamed web search and summarised thinking are; ADR-0023 (what the run says while it waits, and its *no ninth event*); ADR-0012 (a replay is the real stream played back); ADR-0006 (one whole proposal per call); ADR-0008 (how much browser testing a change needs)
informed: agents working in `backend/src/katalyst/engine/`, `backend/src/katalyst/api/`, `frontend/src/stream/`, `frontend/src/components/RunStrip.tsx` and `frontend/src/a11y/`; whoever next runs `make record-demo`, because nothing here changes what it sends
supersedes: none
superseded-by: none
spec-impact: spec/generation/streaming.md (the chapter title, the event list, the grammar, the route table, a new anti-pattern 9 and INV-generation.22); spec/workbench/streaming-growth.md (a new B12 and open question 1 re-answered — written out in the handover, placed by the coordinator because that chapter is being rewritten on another branch); ARCHITECTURE.md §3; ADR-0023's *What this does not build* (dated amendment, below); `backend/src/katalyst/api/generate.py`'s own docstring (amended in this pull request)
---

# ADR-0027: A live run says what it is doing

## Context and Problem Statement

On 2026-09-22 Kent ran the app against the whole batch of this round's changes and said what he wanted next, in his own words:

> *"Generally, the user should get instant feedback that something is happening, like a timer ticking up, and mirroring back explanations to the user what's happening. Generally, there should only be a few seconds between things happening for real on the UI if possible. For example, if we could see the different things that the llm is proposing even if the events are rejected, that'd be helpful."*

**Nothing of ours is slow, and the wait is real.** Measured by analyst LIVE on 2026-09-22 over `try/04c-next`: building a world from the largest kept map — twenty claims, twenty-six links, the whole belief pass — takes **0.1 ms** over twenty passes, and a whole replay of `hormuz.jsonl` is twenty-seven events at 0.6 s each, **sixteen seconds end to end**. Every second anybody has waited was spent waiting on the model.

**How long that is.** Across the five kept runs under `backend/.runs/`, the **first** model call took **7, 67, 135, 152 and 223 seconds**. The `medium`-effort run behind decision R34 took **223 seconds to put anything at all on the screen**. Record 0023's "about 23 seconds" came off a keyed run nobody kept, and it is the more optimistic number by an order of magnitude.

**And the call is opaque by construction.** `engine/client.py` asks with `messages.parse`, which is not streamed, and one question is up to five whole request-and-answer trips. The query the model ran, the pages it found and the proposal it wrote all arrive together, at the end. Of the `medium` run's 32,823 output tokens, **22,385 — 68 per cent — were thinking**; across all five runs the share is 61 to 80 per cent. **Most of the wait is silent thinking.**

**The strip that says so already exists.** Record 0023 shipped it the day before: one strip at the foot of the map, the state as a word, the run's own sentence naming what is open, and the seconds since anything last arrived. It says *something is happening*. What it cannot say is *what*, because nothing on the wire knows: the eight events are the map's decisions, and between two of them the server itself has nothing new to report.

So: **may one line travel down the stream that is not a decision — that says what a call is doing this second and is never written down — or is the eight-event stream the whole of what a client may ever see?**

## Decision Drivers

* **The measurement, not the impression.** A round asks three questions at once and hands over nothing until its slowest returns: **48 seconds of still screen a round at `medium`, 88 at worst; 144 and 288 at the effort the recordings are made at.** No arrangement of the eight events reaches *a few seconds*, because every one of them is bounded below by a whole model call.
* **A recording is the real stream, line for line** (record 0012). That sentence is what makes a keyless reviewer's walk honest, and it is the sentence record 0023 protected by refusing a ninth event.
* **Nothing invented.** Kent's second veto is any state that cannot be traced to an input, a rule or a cited source. A progress bar, a percentage, an estimate of what is left, or a sentence of ours about how the run is going would all be exactly that.
* **Nothing spins** (D5(i), `PRODUCT_REQUIREMENTS.md` §10 anti-pattern 9, INV-workbench.60, INV-workbench.73). Record 0023 drew the line and this record does not move it: what may change on screen is a reading, not a motion.
* **The recorder's request may not move.** `tests/boundary/conftest.py` matches a recorded exchange on the **whole request body**, so any change reaching the recorder breaks nine cassettes and costs a paid re-record. R5 holds every change to what the model is asked for one freeze after the engine's flip. **R34 is the precedent and the limit**: the live path already sends `medium` where the recorder sends nothing, and it leaves `record-cassettes`, `record-demo` and `run-demo` alone.
* **The prompt's fingerprint must not move.** `engine/prompt.py`'s `prompt_hash()` is the standing text plus the shapes of the answers, and nothing else — so streaming, effort, `max_tokens` and how thinking is displayed cannot move it, and every recording keeps matching the prompt shipping today.

## Considered Options

The three were put to Kent on 2026-09-22 with the measurements above, the first recommended.

* **E1 — a ninth kind of line, ephemeral by rule, carrying the model's own words.** The live call is streamed and one new kind of line, `activity`, says what is happening as it happens: the search just issued, one thing it returned, the sentence the model is thinking. Sent live, never recorded, never replayed, never invented.
* **E2 — one `asking` event per round, nothing streamed.** Before each round the server names the claims it is about to ask about, and those reserved rectangles read `ASKING`. No change to the request at all. **Measured ceiling:** one new thing per round and per call return — the median gap falls from 76 seconds to 44 at `medium`. Not *a few seconds*, and never will be.
* **E3 — nothing new on the wire: hand each answer over as its own call returns.** The walk stops holding a round's answers for its slowest call. Same map, same order, same seed; only timing moves. Measured: the median gap falls 76 → 44 seconds at `medium` and 152 → 117 at the recorder's effort, taking **193 and 601 seconds of still screen off the two runs we hold**.

And one question of its own, put separately:

* **Whether the model's summarised thinking is shown too.** A third line, in the model's own words, saying what it is weighing. It needs the thinking on the live request set to summarised. **The recommendation was against it in this round** — it is the one line here about the model's *mind* rather than about a fact with a source.

## Decision Outcome

Chosen option: **"E1 — a ninth kind of line, ephemeral by rule"**, together with the thinking line, because it is the only option that reaches the few seconds Kent asked for, it invents nothing — every word on it is the model's own or the search tool's own — and it costs record 0012 nothing, by the argument record 0023 itself made for the seconds counter: *a replay shows no activity because the thing being reported does not exist in a replay.*

**Kent's decisions, 2026-09-22 (R44 and R47).**

* **R44 — yes, shown live only.** *"A ninth kind of event, `activity`, ephemeral by rule: sent on a live run, never written to a recording or a transcript, never replayed and never invented by a replay; shown in the strip and never on the map. Its words are the model's own search queries and the titles of what it found — nothing invented, no progress estimate."*
* **R47 — yes, show the thinking too. He overrode the recommendation.** *"A line in the model's own summarised words, on the same ephemeral channel as R44, from thinking set to summarised on the live request only. It is labelled as the model's own words, never paraphrased by us, and never recorded."*

E3 was accepted separately as **R45** and belongs to the walk, not to this record.

### What ships

**One shape, agreed with the browser before either half was built.**

```
event: activity
data: {"about": "<claim identifier>" | null, "kind": "searching" | "found" | "thinking", "text": "<words>"}
```

* `about` — the open claim this call is working on, one of the identifiers the latest `frontier` names, or nothing at all when the call is not about one claim, which is what the opening call is.
* `kind: "searching"` — `text` is the model's own web-search query, **verbatim**.
* `kind: "found"` — `text` is the title of one thing the search returned, verbatim, followed by ` · <host>` when the address has one.
* `kind: "thinking"` — `text` is the model's own summarised thinking, verbatim: its most recent whole sentence, or the last of it cut at a word once a sentence has been shown to be all there is.

**Ephemeral is six clauses, and each one is a test.** Sent only on a live run · never written to a recording, a transcript or a kept run · never sent by a replay and never invented by one · never billed · never counted by the `at` counter · never folded into the map. A browser that does not know the name ignores it, which is the rule `spec/generation/streaming.md` already sets for a name nobody knows.

**At most about one line a second per call, and the newest wins.** A call searching hard has something new to say several times a second and the strip shows one line, so the newest of each call's lines goes and the rest are dropped where they were made. Nothing queues, nothing arrives late, and a reader who is slow costs the run nothing. There is no minimum: the first line of a call goes the moment it exists.

**Where it shows, and where it does not.** Only in the run strip, at most two extra lines while a live run is open — the latest `searching`/`found` line and the latest `thinking` line, labelled as the model's own words. Never on the map, never in the panel. **Both sit outside the polite live region**: they change every few seconds and must not be announced. Neither animates: `noSpinner` and the animation budget keep every line they have, because a line of text replaced by another line of text is a reading and not a motion — the rule record 0023 wrote down. The words on screen are fixed: `searching the web: "<query>"` · `found: <title> · <host>` · `the model, in its own words: <text>`.

**Nothing of the recorder's moves.** The live call is the only one that is streamed and the only one that asks for summarised thinking; the recorder and every recorded exchange pass no listener and send the request they have always sent. Proved rather than asserted: `tests/boundary/test_expand_cassettes.py`, `tests/unit/engine/test_client.py`, `test_prompt.py` and `test_wire_schema.py` pass **unedited**, and the prompt's fingerprint is the same string as the one in `backend/recordings/hormuz.jsonl`'s header.

### What this amends, and what it leaves whole

**Record 0023's *no ninth event* is amended, not overturned.** Its reasoning held for an event carrying a **decision**, which a recording must hold. It does not hold for one carrying **activity**, which a recording must not. The dated amendment is in that record.

**`api/generate.py`'s own rule is amended in the same pull request**: *never send a heartbeat, a comment line or anything that is not one of the eight events* becomes *…that is not one of the eight events or `activity`*, with the six clauses written beside it.

**Record 0012 stays whole, and this is the argument.** A recording is still the real stream of **decisions**, line for line: activity is not a decision, it is never written down, and a replay shows none — so there is no line in any recording that this record makes untrue, and no line a replay must invent to keep up. It is the same kind of difference record 0023 accepted for the seconds counter, for the same reason: *the thing being reported does not exist in a replay.* A replayed run says what it is showing and never pretends to be working.

**Record 0006 stays whole.** It is the reason there is no *map* to stream — one whole proposal per call, validated before it is drawn — which is a different question from whether the vendor's own response streams. Structured output survives streaming unchanged; the shape still goes on `output_format` and the answer that comes back is the same validated shape.

**R5 and R9 are untouched.** Nothing here changes what the model is asked, what a recording carries, or when the other three recordings are made.

### The cost of R47, said plainly

The recommendation was against showing the thinking, and Kent overrode it. The cost is real and is written down here so nobody has to rediscover it: **it is the one line in this product about the model's mind rather than about a fact with a source.** A search query is a fact — the model ran that search. A title is a fact — the tool returned that page. A sentence of summarised thinking is the model's account of its own reasoning, and it is neither checkable nor citable.

Three things keep it inside Kent's own second veto rather than outside it. It is **shown verbatim**, never rewritten, never summarised again by us. It is **labelled as the model's own words** on screen, in those words, so nobody can read it as the product's claim. And it is **never recorded**, so it can never end up in a file somebody later reads as evidence. It is a line about the run, not a line about the world, and nothing downstream may ever read it.

### Consequences

* Good, because the thing Kent asked for is the thing that ships: something real on screen every few seconds during a wait that has measured as long as 223 seconds, and every word of it the model's own.
* Good, because it invents nothing. There is no percentage, no count of what is left, no estimate of time — the caps that would have to be divided by are the server's and are not on the wire, and record 0023's anti-pattern against estimating still stands.
* Good, because it costs the recorder, the cassettes, the prompt's fingerprint and R5's freeze exactly nothing, and the tests that would have shown otherwise pass unedited.
* Good, because the rule is one sentence: **the map is eight events and is recorded; activity is one line and never is.**
* Bad, because a live run and a replay now differ in a second visible way — the replay has no activity lines, as it has no seconds — and that difference has to be explained wherever somebody notices it.
* Bad, because the shape a streamed answer arrives in has **never met the service from this program**. The blocks are documented and the reading is written to shrug at anything it does not recognise, but the first live call is what settles it, and until then this is the one part of the product proved only against a reference bundle.
* Bad, because one line on screen is the model's account of its own reasoning, which is the cost R47 carries and the paragraph above is about.
* Neutral, because the claim a line is about is found by reading the question the call was put with, which is a prompt the route does not own. It is the smallest reading that works, it is held by its own test, and the day the prompt is reworded that test fails rather than every line quietly losing its claim.

### Confirmation

* `backend/tests/api/test_generate_live_pace.py` › **`test_something_reaches_the_reader_inside_five_seconds`** — **the test that would have caught what Kent saw.** Through the real route, with a stand-in answerer that says what it is doing and then goes quiet on a latch, released only when a line of what it said has been written out. Activity reaches the reader before the proposal does, and the run finishes well inside five seconds; take the writing-out away and it sits on the stand-in's own give-up timer and fails on the clock. It is tier 2 of record 0008 — a change whose correctness is about timing gets a test that injects the adverse timing, with no browser and no key.
* `test_the_newest_line_of_a_call_wins_and_at_most_one_a_second_leaves_it`, `test_two_calls_at_once_are_paced_apart_from_each_other`, `test_nothing_is_said_once_the_run_has_started_ending`.
* `backend/tests/unit/engine/test_activity_is_never_recorded.py` — the six clauses: `test_activity_is_not_one_of_the_eight`, `test_no_committed_recording_holds_an_activity_line` (over every committed file), `test_the_recorder_refuses_to_write_an_activity_line`, `test_a_kept_run_holds_no_activity_line`, `test_a_recording_holding_an_activity_line_is_refused_by_name`, `test_playing_a_recording_with_an_activity_line_stops_rather_than_replaying_it`, `test_a_replay_invents_no_activity`, `test_an_activity_line_carries_no_transcript_counter`.
* `backend/tests/unit/engine/test_the_seam_says_what_it_is_doing.py` — `test_a_call_with_nobody_listening_is_the_request_it_has_always_been`, `test_a_call_somebody_is_listening_to_is_streamed_and_thinks_out_loud`, `test_a_listener_that_throws_never_stops_a_call`, and the reading of each kind of block from the library's own types.
* `backend/tests/boundary/test_expand_cassettes.py` and `backend/tests/unit/engine/test_prompt.py` pass **unedited**, which is the proof the recorder's request did not move.
* In the browser: `theRunStrip.test.tsx` › `test_the_strip_prints_the_search_the_model_just_ran`, with `noSpinner.test.ts` and `motionBudget.test.ts` unchanged.

## Pros and Cons of the Options

### E1. A ninth kind of line, ephemeral by rule (chosen)

* Good, because it is the only candidate that reaches *a few seconds*: a query lands seconds into a call and again at every round of research, where everything else is bounded below by one whole call.
* Good, because every word on it is somebody else's — the model's query, the tool's title, the model's own sentence — so there is nothing on it for the second veto to catch.
* Good, because it leaves record 0012 whole by an argument record 0023 has already made and Kent has already accepted.
* Bad, because it is the first line on the wire that is not a decision, and that distinction has to be kept true by rule rather than by shape: the name is deliberately absent from the tables a recording is written and read through, so a recording cannot hold one even by accident.
* Bad, because the wire shape of a streamed server-tool block is a hypothesis until one live call settles it.

### E2. One `asking` event per round

* Good, because it changes nothing about the request: no cassette, no fingerprint, no question for the vendor.
* Good, because it would honestly say which three claims are being asked about right now.
* Bad, because **measured**, it moves the median gap from 76 seconds to 44 and can never do better: it fires once a round and once per call return, and those are the moments an event already fires.
* Bad, because it carries a decision-shaped name with no decision behind it, so a recording would have to hold it — which is E1's whole problem without E1's benefit.

### E3. Hand each answer over as its own call returns

* Good, because it is free, changes no shape, amends no decision, and takes 193 and 601 seconds of still screen off the two runs we hold.
* Good, because it ships whatever else ships.
* Bad, because it is still bounded below by one whole model call: on the run behind R34 the first thing on screen still arrives at 223 seconds.
* Neutral, because it is not an alternative at all — Kent took it as R45, in its own lane.

### Showing the summarised thinking

* Good, because it is where most of the wait actually goes: 68 per cent of what the model writes at `medium` is thinking, so a strip that says nothing about it is silent for most of the silence.
* Good, because it needs nothing new — the same ephemeral channel, one extra field on the live request — and it moves neither the fingerprint nor the recorder.
* Bad, because it is the one line here about the model's mind rather than about a fact with a source, which is why it is shown verbatim, labelled as the model's own, and never written down.
* Bad, because the raw chain of thought is never returned at any setting, so what is shown is the service's summary of it — a second-hand account, presented as exactly that.

## More Information

* **Kent's decisions, 2026-09-22**, rows **R44** and **R47** of `plans/notes/2026-09-21-decisions-after-review.md`, taken with the question tool against the three options above, with his original words from the same day quoted at the head of this record. **R45** (a round's answers reach the screen as each call returns) and **R46** (a paid measurement of `low` effort, about a dollar, not yet run) were taken in the same sitting and belong to other lanes.
* **The analysis:** `plans/ux-round/E-live-activity.md` (analyst LIVE, 2026-09-22) — §1 for what is true today with a file and a line for each claim, §2 for the three designs and their measured ceilings, §4 for every earlier decision this touches, §5 for the four questions put to Kent. Its script is `plans/analysis/scripts/live/where_the_time_goes.py` and its measurements come off the five kept runs under `backend/.runs/`.
* **Record 0023** (2026-09-21, R35) — what the run says while it waits: the strip this record puts two more lines on, the rule separating a reading from a motion, and the *no ninth event* this record amends.
* **Record 0012** — a replay is the real stream played back, which is the sentence this record is careful not to break.
* **Record 0006** — one whole proposal per call, which is why there is no map to stream; and its instruction, still standing, to verify every model name, parameter and price against the `claude-api` reference bundle and never from memory.
* **Record 0008**, amended 2026-09-21 — three tiers of browser testing; this is tier 2, so the correctness-about-timing test above is required.
* **What rests on documentation alone.** Three specifics were taken from the `claude-api` reference bundle on 2026-09-22 and **have never met the service from this program**, because no live call may be made from this work: that a streamed structured-output call is `messages.stream(..., output_format=…)` with the validated answer read off the finished message; that a web search arrives as a `server_tool_use` block whose input carries the query and a `web_search_tool_result` block whose content is the list of results; and that this model returns its thinking with the text emptied out unless the thinking is asked to be summarised. The reference bundle and the client library disagree on the last one — the library's own docstring says a summary is the default, and the bundle says it is not for this model at this effort, which is exactly the trap lesson 15 of the handover names. The request asks for the summary explicitly, so both readings give the same behaviour. The reading of an arriving answer is written to say nothing at all about a piece it does not recognise, so the failure mode if any of this is wrong is a strip with fewer lines on it, never a broken run.
