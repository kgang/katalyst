---
# ADR-0023: What the run says while it waits — one sentence at the foot of the map, and a count of seconds
status: proposed
date: 2026-09-21
decision-makers: Kent Gang
consulted: Kent's own walk of the app with his model key, 2026-09-21 (`plans/notes/2026-09-21-kent-m4-feedback.md`); analyst UA's read-only pass over the generating screen, the same day (`plans/ux-round/A-live-status.md`); the red team's re-run of it (`plans/ux-round/RT-red-team.md`, items 1, 5 and 7); ADR-0012 (a replay is the real stream played back); ADR-0008 (how much browser testing a change needs)
informed: agents working in `frontend/src/stream/`, `frontend/src/components/`, `frontend/src/a11y/` and `frontend/e2e/`; the stack-06-4 dock lane, which owned the *Run details* move until this record pulled it forward
supersedes: none
superseded-by: none
spec-impact: spec/workbench/streaming-growth.md (B1, B3, a new B11, INV-workbench.60, .73, .78, a new .80, anti-pattern 8, open question 1); PRODUCT_REQUIREMENTS.md UX-8 and §10 anti-pattern 9; ARCHITECTURE.md §1 and §10
---

# ADR-0023: What the run says while it waits

## Context and Problem Statement

On 2026-09-21 Kent ran the app with his own model key for the first time, pressed **Watch it build**, and said: *"i don't see anything happening after pressing watch it build"*. He tried the Explore door and said the same thing again — *"I filled in the info I tried the explore door, but I don't see anything happening. I typed in what the example text stated"* — and then, about half a minute later, *"Oh I saw an event come through"*.

**Nothing was broken.** The run was working exactly as designed, and the screen had no way to say so.

**How long the silences are.** Measured by the coordinator session the same evening, on Kent's own keyed run, and written down in `plans/notes/2026-09-21-kent-m4-feedback.md`: the first event arrives **about 23 seconds** after the press and later ones **50 to 110 seconds** apart; in between, the screen shows one dim dashed *HELD OPEN* rectangle and nothing else. The pictures are in `plans/logs/m4-look/`. Analyst UA measured one model call at **51.98 seconds** at `medium` effort and **109.65 seconds** at the effort the recorder uses, read off the two evaluation logs of that day (`plans/logs/eval-hormuz-medium.log`, `plans/logs/eval-hormuz.log`; `plans/ux-round/A-live-status.md` §1). A round asks about three claims at once, so events land in bursts and the screen is then still for about a minute.

**The sentence that would have told him already exists, and is clipped to one pixel.** `frontend/src/stream/GenerationScreen.tsx` passes `spokenOnly={true}` to the map frame, and `frontend/src/components/generationDock.css` gives `.map-live--spoken` a one-pixel box with its content clipped away. So *"Asked for a map of … A rectangle is held open where the first claim will go"* (`frontend/src/a11y/growth.ts`, `theOpeningLine`) is **spoken to a screen reader and never printed**. A browser test asserts that clipping — `frontend/e2e/generate.spec.ts:230` — which is why no test in the suite could have caught what Kent saw.

**What is at the foot of the screen instead.** Three stacked strips of prose, none of them about the run: *last key*, the invisible live region, and a provenance line reading *"Every claim and arrow on this map arrived from /api/generate, in generation …, at seed …. Nothing here was typed in…"* (`frontend/src/stream/growth.ts:196`). That line is written from `generation_started` onward — that is, **it asserts arrivals while the map is still empty**.

**What Kent asked for, in his words:** *"There needs to be better feedback/interactivity to show that the backend is running and to show what its doing while the user is waiting so they know it's working. Let's use the bottom bar to communicate real time statuses to the user and have spinners/animations to show what it's doing."*

And that meets a veto he set himself. D5(i) — the disgust veto — names *"spinner-then-dump"* as its own example of a template interface; `PRODUCT_REQUIREMENTS.md` §10 anti-pattern 9 repeats it; `INV-workbench.60` says there is no spinner anywhere in the product and a test walks every component and every stylesheet to keep it that way; `INV-workbench.73` holds the animation budget to three.

So: **what may the foot of a growing map show, while nothing has come back for a minute, without lying, without spinning, and without leaving the reader to guess whether the tool is alive?**

## Decision Drivers

* **The veto and the request are both Kent's, and both must survive.** The distinction that has to be drawn is between *motion instead of information* — which is vetoed — and *a reading that changes because time passed*, which is information.
* **Every string already exists.** The opening line, the what-changed line, the reason a run stopped, the replay sentence, the stored map's origin: all are written and all are spoken. Nothing here has to be invented, only shown.
* **No server change.** `api/generate.py` says it in its own comment: *never send a heartbeat, a comment line or anything that is not one of the eight events. A recording is this stream line for line.* R5 holds every change to what the model is asked, and to what a recording carries, for one freeze after the engine's flip. A ninth event would break both.
* **The browser may count only what it can honestly count.** Measured off `backend/recordings/hormuz.jsonl` by analyst UA (`plans/analysis/scripts/ux-round/A/what_the_wire_already_says.py`, 2026-09-21): the recording holds **26 events**; the transcript counter runs 0 → 22; claims 0 → 18; places held open 0 → 5; refusals 0 → 3. The receipt's **29 calls against 23 growth events** is the gap — so the browser can honestly count *proposals* and can never count *calls*.
* **Never an estimate.** `spec/workbench/streaming-growth.md` anti-pattern 8 forbids estimating the cost, the progress or the remaining claims: the caps that would have to be divided by are the server's and are not on the wire.
* **A replay is paced by us.** `KATALYST_REPLAY_PACE` is 0.6 seconds in the shipped product and 0.4 seconds under the browser suite (`frontend/playwright.config.ts:209`). A seconds counter on a replay would reset twice a second and would be measuring our own pacing rather than any wait.
* **A counter inside a live region speaks.** The polite region says what changed (INV-workbench.78). A number that ticks inside it would be announced every second.

## Considered Options

The first three were put to Kent on 2026-09-21 with sketches, in this order, the first recommended.

* **M1 — a sentence, and a measuring hairline beside it.** *This is Kent's own request built at full strength.* The strip says what is being worked on, in words, taken from the `frontier` the stream already carries on both growth events. Beside it, a hairline **whose length is the seconds since the last claim**, measured against the longest gap this run has already had. It resets when a claim lands, it never repeats, it stops when the run stops, and under reduced motion it steps once a second instead of sliding. On Hormuz: `live · Working on what follows from "war-risk premiums fall below 0.4%" and two others.  ▁▃▅ nothing new for 47 s`.
* **M2 — a true spinner beside the sentence.** The thing the words *"spinners/animations"* literally name: an indeterminate rotating mark, next to a sentence saying what is happening.
* **M3 — the sentence and counting seconds only. Nothing else moves.** The foot reads `live · One place is held open where the first claim will go.  nothing new for 23 s`, and the only thing that changes between events is the number of seconds.

Two more were considered by the analysis and not put to him, because both were recommended against on measurement:

* **M4 — a ninth stream event, `asking`.** The server names the claims it is about to ask about before each round, and those rectangles read `ASKING` rather than `HELD OPEN`.
* **M5 — poll the transcript while the run is open.** The route already answers in flight.

## Decision Outcome

Chosen option: **"M3 — a sentence and counting seconds, and nothing else moves"**, because it answers *is this alive?* and *what is it doing?* out of strings and a clock the browser already has, leaves every standing rule about motion exactly as written, and needs nothing from the server.

**Kent's decision, 2026-09-21 (R35).** He had asked for *"spinners/animations"*. Shown the three options with sketches, **he chose the quietest.** The strip says what the run is doing and *nothing new for 23 s*; nothing else moves. *Nothing may spin, pulse or sweep* stands.

### What ships

**One strip at the foot of both map screens, in place of three.** Left, the state as one word in the mono mark box the foot already uses; then one human sentence; then, only while a live run is open, the count of seconds since the last event.

Every sentence in this table is a string that exists today. The strip is only where they land.

| State | The word | The one sentence | Seconds |
|---|---|---|---|
| stored map | `stored` | the map's own origin — *this map was built earlier and is drawn as it was written* | no |
| stored map, engine asked | `asking` | the reason the map screen already prints while `/api/worlds` runs | yes |
| replay | `replay` | the replay sentence, plus what has arrived so far | **no** |
| live, waiting | `live` | the opening line, or the last thing that changed | yes |
| live, arriving | `live` | what just changed, in its own words | yes |
| finished | `finished` | why it stopped, with the run's own counts | no |
| failed | `stopped` | the one plain sentence the run left | no |
| ended early | `ended early` | the stream ended before the run said it had finished | no |

**The seconds are a measurement of silence, never an estimate of what is left.** The reading is *how long since the last event*, from the browser's own clock. There is no percentage, no bar, no "about a minute left", and no count of calls — the browser cannot know how many calls are in flight and must not guess.

**A replay shows no seconds.** At 0.6 seconds an event the number would reset twice a second for no reason, and it would be measuring our own pacing rather than a wait. This is the one place where a replay and a live run legitimately differ on screen, and the reason is that the thing being measured does not exist in a replay.

**The spoken sentence becomes the printed sentence.** `spokenOnly` is deleted rather than guarded, and the browser test that asserts the clipping is inverted. The live region keeps saying what *changed*; the strip prints the same sentence; the seconds sit **beside** the region, not inside it and not hidden from a screen reader — plain text, reachable, never announced.

**Provenance moves into a *Run details* section of the panel — R16, pulled forward.** The line naming the route, the generation identifier and the seed leaves the always-on foot for a *Run details* section of the panel beside the map. **Never a dialog.** This is decision R16 word for word; all this record changes is *when* — it was stack 06-4's and is now this stack's, dated 2026-09-21 — and the reason for moving it now is that it is what makes un-hiding the run's sentence safe. With the provenance line gone, nothing else at the foot repeats it, and the foot is one strip instead of three.

**No server change. The stream stays exactly the eight events.** Nothing here is folded from a new event, nothing polls, and no recording changes. That is what keeps this clear of R5's one shape freeze.

### The line between the veto and the request, written so a test can hold it

> **Motion may carry information; it may never stand in for it.** A thing on screen may change over time only when what changes is a **measurement** — a value the screen would print anyway — and the sentence beside it is complete without the change. Nothing loops, spins, pulses or sweeps: a repeat is motion with no measurement behind it. Under reduced motion the measurement still updates, because it is information and not a tween.

**No standing rule is weakened and no architectural test's assertions change.** `motionBudget.test.ts` needs no edit at all: the elapsed reading is a number redrawn by a timer in JavaScript, it spends no stylesheet duration, so the three budgeted moves and the reduced-motion assertions stand exactly as written. `noSpinner.test.ts` keeps its three checks untouched — nothing rotates, nothing is an indeterminate progress indicator, nothing is called a loader. INV-workbench.60, .18 and .73 are unchanged, and are named here so the record says what it did **not** move.

One check is **added**, because this decision creates the first timer in product code that redraws something: a walk for `setInterval` and `setTimeout` across `frontend/src/` against a named allowlist, in the manner `colourLaw.test.ts` already uses. That is an addition, not an amendment; if Kent reads R35's *"no architectural test changes"* as forbidding even the addition, say so and the line is held by review instead.

### What this does not build

* **No ninth event.** Open question 1 of `spec/workbench/streaming-growth.md` is answered: not in version one. Everything the strip says is already on the eight events or on the browser's own clock. A ninth event would be the first to carry *activity* rather than a *decision*, and no committed recording holds it — so a replay would be visibly less alive than a live run, which is the one thing ADR-0012 cannot allow. If it is ever wanted it rides the one shape freeze, where all four recordings are made together.
* **No progress bar, no percentage, no time remaining.**
* **No count of calls in flight.** The browser can count proposals; it cannot count calls; it should say *proposals*.
* **No faster replay.** A replay that races teaches a reviewer the product is faster than it is.

### Consequences

* Good, because a reader who presses the button and waits 23 seconds is told, in ink, what the tool is doing and how long it has been doing it — which is the whole of what Kent could not see.
* Good, because it costs no server change, no new event, no recording, and nothing from R5's freeze.
* Good, because the sentence a screen reader hears and the sentence a reader sees become the same sentence, so the two can never drift apart again.
* Good, because the foot goes from three strips of prose to one, and the provenance line stops asserting arrivals on an empty map.
* Bad, because a reader gets less than Kent first asked for: nothing on the screen moves except a number, and on a slow call the screen is still a mostly-still picture for a minute.
* Bad, because a replay and a live run now differ in one visible way — the replay has no seconds — and that difference has to be explained wherever somebody notices it.
* Neutral, because the hairline of option M1 remains buildable later: it needs the same strip, the same clock and no new data, so choosing M3 now forecloses nothing.

### Confirmation

* `frontend/src/stream/__tests__/theRunStrip.test.tsx` › `test_the_visible_strip_says_what_the_run_is_waiting_for` — no browser, fake timers: fold `generation_started`, advance 23 seconds, assert the **visible** strip names what is held open and reads the wait; fold an accepted proposal and assert the count resets. **This is the test that would have caught what Kent saw**, and it is tier 2 of ADR-0008 (a change whose correctness is about timing gets a no-browser twin that injects the bad timing).
* `test_a_replay_shows_no_seconds`.
* One end-to-end test with `KATALYST_REPLAY_PACE` set long — the suite's first meeting with a real silence, with no key and no cost.
* `frontend/e2e/generate.spec.ts:230`'s assertion that the live region carries `map-live--spoken` is **deleted and inverted**: at the gap the suite already brackets, the strip must be visible and must name what is being waited for.
* `noSpinner.test.ts` › `test_the_only_thing_that_changes_on_a_timer_is_a_measured_reading`.
* Visual review checklist `VR2` (no spinner, no pop-up, no dialog) is checked on a picture of a live run, not only of a replay.

## Pros and Cons of the Options

### M1. A sentence and a measuring hairline (Kent's request at full strength)

* Good, because it is what he asked for: something visibly moves, and it moves because a real quantity changed.
* Good, because the hairline's length is a measurement — seconds since the last claim against the longest gap this run has had — so it is information, not decoration, and survives the rule above.
* Good, because the frontier sentence it carries is free: both growth events already name which claims are open.
* Bad, because the longest-gap-so-far it is measured against is a fact about *this run so far*, which means the same wait draws a different length at minute one and at minute ten — a reading that is honest and hard to read.
* Bad, because it is a fourth moving thing on a screen whose motion budget is three, and every honest non-textual mark needs a number the server does not send.

### M2. A true spinner

* Good, because it is unambiguous, universally understood, and half an hour of work.
* Bad, because it is the disgust veto's own named example: *a spinner followed by a dump of results*. D5(i), PRD anti-pattern 9, INV-workbench.60 and `test_there_is_no_spinner_anywhere` all forbid it by name.
* Bad, because it says *wait* without saying what for — and the thing being waited for has a shape, which is the argument the whole chapter rests on.

### M3. The sentence and counting seconds (chosen)

* Good, because every string exists and the only new thing is a number from the browser's own clock.
* Good, because it removes a special case — the invisible sentence — rather than adding a channel, and leaves every motion rule and architectural test standing.
* Good, because "is anything happening?" and "what did it just do?" are answered by the same sentence, so they cannot drift apart.
* Bad, because it is the least alive of the three, and on a 110-second call the only thing that changes on screen for two minutes is a two-digit number.

### M4. A ninth event, `asking`

* Good, because it is the only option that could honestly say *which three claims are being asked about right now* and whether a search is running.
* Bad, because none of the committed recordings carries it, so a replay would be visibly less alive than a live run — and *the same events, the same canvas, the same refusals* is the sentence ADR-0012 rests on.
* Bad, because it would be the first event on the stream carrying activity rather than a decision, and it touches `events.py`, `grow.py`, `following.py`, `replay.py`, the grammar tests and the browser reducer.
* Bad, because it is a change to what a recording holds, so it belongs to the one shape freeze (R5) and to nothing before it.

### M5. Poll the transcript while the run is open

* Good, because the route already answers in flight, so it costs nothing to try.
* Bad, because it was measured and it tells the browser nothing the stream has not: the transcript gains a line only when a call *returns*, and every returning call that changes the map has already made an event.
* Bad, because it is two copies of one state for one fact.

## More Information

* **Kent's decision, 2026-09-21 (R35)**, taken with the question tool after the three sketches above: *"a sentence and counting seconds only"*. Recorded in `plans/notes/2026-09-21-decisions-after-review.md`, row R35, with his original words from `plans/notes/2026-09-21-kent-m4-feedback.md`.
* **R16, pulled forward the same day** — *Run details* moves routes, seed and loop counts off the always-on strip into a section of the panel, never a dialog, and the strip keeps one human sentence. Decided for stack 06-4; dated into this stack by this record.
* **The analysis:** `plans/ux-round/A-live-status.md` (analyst UA, 2026-09-21) — §1 for what is true today with file and line for each claim, §2 for the three designs, §3 for the rule about motion, §5 for the questions put to Kent. Its scripts are under `plans/analysis/scripts/ux-round/A/`.
* **The adversarial pass:** `plans/ux-round/RT-red-team.md`, 2026-09-21 — item 1 (the plan is sound after changes), item 5(c) (a replay must show no seconds), item 7 (the suite has never seen a live run, and one end-to-end test with the pace set long is the cheap way to fix that).
* **ADR-0012** — a replay is the real stream played back, which is why no ninth event is built before the recordings can carry it.
* **ADR-0008**, amended 2026-09-21 — three tiers of browser testing; this is tier 2, so a no-browser test that injects the adverse timing is required.
* **ADR-0006** — one whole proposal per call, which is why there is no token to stream and no progress to divide.
* `spec/workbench/streaming-growth.md` (B1, B3, B11, anti-pattern 8, open question 1) · `PRODUCT_REQUIREMENTS.md` UX-8, §10 anti-pattern 9, D5 · `spec/workbench/keyboard-and-access.md` (the polite region).
