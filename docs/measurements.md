# Measurements — a dated journal

**What this file is.** Every number here is something a run actually did, on a named day, under a named model and named settings. It is a **journal, not a page**: entries are added, never rewritten. When a later run says something different, that is a new entry — the old one still says what happened on its own day, which is the only thing a measurement can ever say.

**Why it exists.** Chapters and decision records quote costs and timings. A quoted number needs one committed home a reader can open, rather than a working file on somebody's laptop. This is that home. Nothing in this file was typed by hand from an estimate; where a number is an estimate it says so, and where a receipt was lost it says that too.

**What each entry carries.** The date, what was run, the model and the settings it ran under, the numbers themselves, and **where the raw record is kept**. A whole-map run leaves a file under `backend/.runs/` — receipt, reason for stopping, every proposal with the seconds and the thinking tokens it took, and the map it built — written by `make run-demo` and `make record-demo`. That directory is deliberately **not committed**: it is the record of one afternoon's spending, not something the product plays back. Recorded model answers that tests replay are committed, under `backend/tests/cassettes/`, with the keys stripped out.

**Engine timings are not restated here.** How long it takes to work the likelihoods through a map — a world, a sixty-claim map, a year-long window — is measured in `spec/multiverse/propagation.md`, which owns those numbers. Go there rather than copying them.

**Nor are the evaluation scorecards.** `make eval` writes its own rows into `evals/runs/<date>.tsv`, committed, one file per day it is run. Those say how well the prompt did; this file says what a run cost. Nothing here restates a scorecard, and no scorecard restates a receipt.

---

<!-- NEXT ENTRY GOES HERE — newest first. Add above the rule below; change nothing beneath it. -->

## 2026-09-22 — the by-deadline engine, first timings

**Why an engine timing is in this file at all.** The note at the top says engine timings live in `spec/multiverse/propagation.md`, and they do — for the engine that is still the default. This entry is the **other** one: decision record 0016's core, landed beside the old engine behind a flag that still says `today`, so the chapter cannot own its numbers yet without describing an engine no screen runs. They move into that chapter when it is rewritten, at the flip. Until then they live here, dated.

**What was run.** `backend/benchmarks/by_deadline.py`, which is recorded and never gated: no test fails because a reading here is large. Code at `a5551f7`, before the performance work on `domain/forward.py` and `domain/states.py` that started the same day — **so the states rows below will be re-measured and this entry will get a successor**. Machine: Apple M3 Max, 14 cores, 38.65 GB, macOS 26.6.2, Python 3.12.4, numpy 2.5.3, nothing else of ours running. Raw output under `plans/analysis/scripts/stack-05-core/E/` (`bench-states.log`, `bench-events.log`, `bench-hormuz.log`, `the-strike-branch.log`), kept locally.

**What each clock covers.** *The forward pass* is working out when every claim happens — one pass over the whole map, causes before effects, rates and shapes and all — at every version. *The exact solve* is one elimination per claim over the yes/no tables that pass leaves, at every version. *The weighted sample* is fifty thousand worlds drawn forward at **one** version, with one claim reported to have happened, and the correction it hands back. Nothing here times the drawing of the versions, which both engines share. *The whole world* is the sum of the three.

### The generated map, twenty claims

Every row: twenty claims, up to three causes each, 2 000 versions, 24 slices, seed 7, two repeats, one claim reported to have happened. The three arrows that hold a claim back sit on **three different claims**, which is the arrangement record 0016 measured.

| | forward pass | exact solve | weighted sample | the whole world | peak memory |
|---|---|---|---|---|---|
| no states, nothing holding a claim back | 261.9 ms | 32.5 ms | 189.3 ms | **483.7 ms** | 0.92 GB |
| no states, three arrows holding a claim back | 752.4 ms | 31.7 ms | 194.1 ms | **978.2 ms** | 2.77 GB |
| five states with a `sustain` arrow leaving each, three arrows holding a claim back | 7 226.0 ms | 33.8 ms | 231.0 ms | **7 490.8 ms** | 8.03 GB |

Each figure is the fastest of the two repeats; the slowest were 280.2 / 823.2 / 7 759.0 ms on the forward pass and 505.6 / 1 056.7 / 8 024.9 ms on the whole world.

**Read against the target**, which is thirty milliseconds a claim at 2 000 versions — a target somebody chose, proportional to the map, and not a gate: **600 ms for twenty claims**. The all-event map with nothing holding a claim back meets it. Three arrows holding a claim back is 1.6× over. **Five states is 12.5× over**, and that row is the one the performance work exists for; record 0017 measured the same shape at 644 ms in the stack-05 spike, so the gap is this implementation's and not the design's.

**The solve is not the problem.** Thirty-two milliseconds whatever the map is, against record 0016's 80.4 ms — which is why the two-pass solve was cut (R40 (2)) and why the seam, `all_marginals`, is all that was kept.

### The committed worked example

The base map, seven claims, end to end through `propagate(engine="by_deadline")` at 2 000 versions and 24 slices, three repeats: **380.1 ms** fastest, 443.6 ms slowest, 1.36 GB. The target for seven claims is 210 ms, so it is 1.8× over.

**The strike branch does not run at the shipped budget, and this is the finding of the day.** Folding *Hormuz opens, then Iran is struck* puts a **second** arrow that holds a claim back onto Brent — the base map's `R->B` and the branch's `S->B` — and the work multiplies out over every *combination* of the two arrivals. Two such arrows cost twenty-five times one rather than twice it:

| | claims | the widest claim's combinations | numbers the added-up rates need at 2 000 versions |
|---|---|---|---|
| the base map | 7 | 25 | 66.3 million, **0.53 GB** |
| the strike branch | 8 | **625** | 1 566.2 million, **12.53 GB** |

Measured, at version counts small enough to finish: 0.15 s at 25 versions, 0.31 s at 50, 0.56 s at 100, **1.28 s at 200**, with the process's high-water memory climbing 0.51 → 6.00 GB across those four runs. Every array is linear in the versions, so 2 000 is about thirteen seconds and well past what this machine has. **The engine's own tests therefore run the strike branch at a handful of versions and say so.** Three ways out exist and none is decided here: keep the added-up rates factored, so the version axis multiplies in only where a version is read; run the pass in blocks of versions; or take record 0017's fixture item 7 and re-examine whether `S->B` should be a holding-back arrow at all.

### The oracles

Not a timing, but measured the same day and on the same code, because a cost is only worth reading beside what it buys. Sixteen seeded maps from `tests/oracles/maps.py`, 24 slices of each claim's own window, eight points inside each slice, an arrival taken at the middle of its slice, one version whose stated range is a point, and *This happened* answered by a seeded sample of 50 000 worlds — judged by `tests/oracles/by_integrating.py`, which is forbidden the engine's tables and is built from the arrow parameters alone. **Every one of 1 030 numbers sat within `.005`**: worst `.0015` with no edit over 62 numbers, `.0014` under *Suppose this is true* over 484, `.0049` under *This happened* over 484.

**And the sample earns its place only where something was reported.** With the correction applied in every world instead, the same maps at the same seed and the same grid move the other way — worst `.0018` with no edit and `.0031` under *Suppose this is true* — so the correction is applied only where *This happened* is in force. Logs: `agreement.log` and `agreement-correction-always.log`, same directory.

## 2026-09-21 — `make eval ONLY=hormuz`, twice: once at each effort

The first two rounds the scorecard ever ran against a real key, side by side on one sentence, one model, one prompt and one evening. **They are the measurement behind Kent's decision that development runs at `medium`** (2026-09-21): only the recorder sends no effort; a live run and `make eval` ask for `medium`. What each scored is in [`evals/runs/2026-09-21.tsv`](../evals/runs/2026-09-21.tsv), which owns those figures; this entry is what each cost.

| | Effort left to the service (`EFFORT=as-recorded` today) | `medium` (the default today) |
|---|---|---|
| Model | `claude-sonnet-5` | `claude-sonnet-5` |
| Code | `dacd6da` | `dacd6da` plus the uncommitted change of default |
| Started (UTC) | 17:57:30 | 18:19:46 |
| Calls | 15 | 13 |
| Searches | 55 | 24 |
| Dollars | $2.17 | $0.94 |
| Wall clock | 27 m 25 s | 11 m 16 s |
| Seconds a call | 110 | 52 |
| Written tokens, of which thinking | 92 949, 74 421 | 32 823, 22 385 |
| Map reached | 6 claims, 9 arrows, 1 ending | 4 claims, 5 arrows, no ending |
| Refused by the rules | 1 | 3 — two `duplicate_link`, one `market_without_payoff` |
| Stopped because | `reached_terminal` | `no_terminal` |
| The eight checks | all eight held | seven held; *an ending that names a trade, or says why there is none* did not |
| Raw record | `backend/.runs/hormuz-2026-09-21T18-24-54Z-01M32HVA1F3SX18H513M6GTNPT.json` | `backend/.runs/hormuz-2026-09-21T18-31-02Z-01M32K42Z4036436TG96Q46RN0.json` |

**What the pair buys, and what it gives up.** `medium` was 2.4 times faster and 2.3 times cheaper, which is the whole reason for it: a scorecard that takes the best part of an hour is not run while a prompt is being worked on. It also drew the smaller map, and **its one tradeable ending was refused by our own rules** — the model proposed a market claim and named no payoff — so the map ended nowhere a reader can act. Kent saw these numbers and kept the decision. **One round each proves a direction, not a rate**: the evaluation chapter says plainly that one prompt scores slightly differently twice. The refusal itself is a known gap, not a new one — requiring a payoff in the shape the model fills is already written and is held for the one change of shape at the end of the engine work, because it moves the prompt's fingerprint and every recording would have to be paid for again.

**The two rounds ran at once**, the second starting 22 minutes into the first, so neither wall clock is a clean solo timing; the first had the key to itself for most of its length.

---

## 2026-09-21 — the committed Strait of Hormuz recording

The generation a keyless clone plays back, made by `make record-demo ONLY=hormuz`. It is the only
committed recording; the other three example sentences have none, and each would cost about the same
again.

| | |
|---|---|
| Model and effort | claude-sonnet-5, effort left at the service's default |
| Calls | 29 |
| Searches | 93 |
| Dollars | $4.04 |
| Wall clock | 36 m 19 s |
| Map reached | 18 claims, 19 arrows |
| Refusals | 3 proposals refused by the rules, each kept in the recording in the validator's own words |
| Claims with a sourced base rate | 5 of 18 |
| Stopped because | `width_cap` — the last open claim already had as many children as the run allowed |
| Committed as | `backend/recordings/hormuz.jsonl` |
| Raw record | not on disk. The run was kept under `backend/.runs/` in the working copy that made it, and that copy has since been removed; the two Hormuz runs kept in the main copy carry other identifiers. The committed recording is complete — every event, and the receipt these figures were read from — so nothing on this table rests on the missing file |

**Why this entry carries no figure from an earlier attempt.** A recording is re-made whenever the
words this program sends the model change, and the shapes it asks the model to fill changed after the
first Hormuz recording was made. The run above is the one that is committed; the one before it cost
real money and is a different measurement, not a correction of this one.

---

## 2026-09-21 — two whole-map runs on `claude-sonnet-5`, one per effort

Both Hormuz, both from the code at commit `0a77256`, both finished. The pair is
the measurement behind Kent's G13 decision — *record rich, run live fast*.

| | Service's own default | `EFFORT=medium` |
|---|---|---|
| Calls | 34 | 17 |
| Searches | 108 | 38 |
| Dollars | **$4.89** | **$1.31** |
| Wall clock | 44 m 33 s | 7 m 46 s |
| **Per call** | **79 s** | **27 s** |
| Thinking share of written tokens | 79% | 63% |
| Claims | 20 | 9 |
| Arrows | 26, of which 24 `documented` | 10, of which 8 `documented` |
| Claims with a sourced base rate | 10 of 20 | 2 of 9 |
| Refused | 1 (`market_without_payoff`) | 1 |
| Depth reached | 5 | 3 |
| Stopped | `width_cap` | — |
| Raw record | `backend/.runs/hormuz-2026-09-21T04-46-29Z-01M312DSCSXJG5DDJE5B324GXR.json` | `backend/.runs/hormuz-2026-09-21T05-00-38Z-01M3150SA04DSVBE1X05CWTMPA.json` |

**What the pair buys.** Three times the money and nearly six times the wall
clock, for a map twice as deep with more than twice the claims and five times
the sourced base rates. Neither is the right answer everywhere, which is why
there are two defaults rather than one: a recording is made once and watched by
everybody, and a person waiting for a map to arrive is waiting.

**The layer-one prompt preference worked.** The default-effort run reached depth
5 and proposed cross-links, where the run that prompted the change had stopped
at four claims and one layer with three trades straight off the hypothesis.

**One thing checked and found not to be a defect.** The default-effort run's
transcript carries no `base_rate_dropped` note, though 10 of its 20 claims have
no base rate. Reading the kept file: every base rate that *is* on the map cites
between one and three pages, and none was dropped — so the ten without one were
proposed without one, which is the prompt working rather than a note going
missing. The note's plumbing is proved separately by
`test_a_base_rate_nobody_sourced_is_dropped_and_noted`, which asserts it reaches
the transcript line.

---

## 2026-09-21 — a whole-map run on `claude-sonnet-5` that crashed in the recorder

The generation itself finished; the **recorder** then crashed, and the receipt went with it. What follows is the **last state the run printed before the crash**, and it is quoted as that rather than as a receipt:

| | |
|---|---|
| Model | `claude-sonnet-5` |
| Calls | 4 |
| Searches | 21 |
| Written tokens | **19,710 of 26,749 were thinking** — about three quarters |
| Dollars | $0.73 |
| Wall-clock | 10 minutes 51 seconds |
| Map reached | 4 claims, one layer deep |
| Receipt | **Lost to the crash.** There is no final receipt for this run |

**What was changed because of it.** The recorder now keeps a run through a crash: what the generation produced is written down before anything that can fail runs over it, so a paid run can never again be lost by the step that was meant to save it. A crash after the money is spent is the one failure that cannot be re-run for free.

## 2026-09-21 — five boundary cassettes on `claude-sonnet-5`, with base rates researched

Recorded through `make record-cassettes`, which is the only thing that writes a real cassette. These are the answers the boundary tests replay, so the suite needs no key.

| | |
|---|---|
| Model | `claude-sonnet-5`, base rates researched (the model searches for its reference class) |
| Calls | 5 |
| Searches | **25 in all — between 2 and 8 a call** |
| Output | 3,500 to 12,000 tokens a call |
| Dollars | **$0.94 in all — about $0.19 a call** |
| Wall-clock | about **200 seconds a call** |
| Kept in | `backend/tests/cassettes/`, committed, keys stripped |

## 2026-09-17 — five boundary cassettes on `claude-opus-5`

The same five calls, before either change — the earlier model, and one search a call rather than a researched reference class.

| | |
|---|---|
| Model | `claude-opus-5` |
| Calls | 5 |
| Dollars | **$0.64 in all — about $0.13 a call** |
| Wall-clock | about **a minute a call** |

## 2026-09-17 — the first whole-map run, `claude-opus-5`

The first time this repository asked a model to build a map: the Strait of Hormuz hypothesis, end to end.

| | |
|---|---|
| Model | `claude-opus-5`, default thinking effort, one search a call |
| Calls | 10 |
| Searches | 9 |
| Dollars | **$1.32** |
| Wall-clock | **10 minutes 54 seconds** — about a claim a minute |
| Written tokens | **61 per cent were thinking** |
| Map reached | 10 claims, 9 arrows, 8 of them `documented` |
| Refusals | **0** — the validator refused nothing the model proposed |
| Stopped because | `width_cap` — the width cap, not an error |
| Kept in | `backend/.runs/hormuz-2026-09-17T15-20-12Z.json` (not committed) |

This is the run that decision records 0006 and 0012 quote: it is why the model became a setting and why a recording is no longer required to contain a refusal.

## 2026-09-17 — an earlier whole-map run the same day

The same example, earlier the same day, before the receipt was written down properly.

| | |
|---|---|
| Model | `claude-opus-5` |
| Proposals accepted | 16 |
| Refusals | 0 |
| Wall-clock | 9 minutes 7 seconds |
| Dollars | **Receipt lost.** It was booked into the stack's running total at an estimated **$3** — an estimate, never a measurement, and it is written here as one |

---

## Reading the entries together

One honest observation, and it is a reading of the table above rather than a measurement of its own: **searching is what a call now costs.** Between 2026-09-17 and 2026-09-21 the model got cheaper per token and a call got dearer — about $0.13 to about $0.19, and about a minute to about three — because a call that researches its reference class makes between two and eight searches and writes several thousand more tokens than one that recalls a number. That is the price of a base rate that cites a page somebody can open, and it is paid deliberately.

**A generation is sequential by nature**: each call must see the map as it stands, so wall-clock time is calls times the time a call takes, and neither a faster model nor a bigger machine changes that shape.
