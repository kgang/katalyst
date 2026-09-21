# Measurements — a dated journal

**What this file is.** Every number here is something a run actually did, on a named day, under a named model and named settings. It is a **journal, not a page**: entries are added, never rewritten. When a later run says something different, that is a new entry — the old one still says what happened on its own day, which is the only thing a measurement can ever say.

**Why it exists.** Chapters and decision records quote costs and timings. A quoted number needs one committed home a reader can open, rather than a working file on somebody's laptop. This is that home. Nothing in this file was typed by hand from an estimate; where a number is an estimate it says so, and where a receipt was lost it says that too.

**What each entry carries.** The date, what was run, the model and the settings it ran under, the numbers themselves, and **where the raw record is kept**. A whole-map run leaves a file under `backend/.runs/` — receipt, reason for stopping, every proposal with the seconds and the thinking tokens it took, and the map it built — written by `make run-demo` and `make record-demo`. That directory is deliberately **not committed**: it is the record of one afternoon's spending, not something the product plays back. Recorded model answers that tests replay are committed, under `backend/tests/cassettes/`, with the keys stripped out.

**Engine timings are not restated here.** How long it takes to work the likelihoods through a map — a world, a sixty-claim map, a year-long window — is measured in `spec/multiverse/propagation.md`, which owns those numbers. Go there rather than copying them.

**Nor are the evaluation scorecards.** `make eval` writes its own rows into `evals/runs/<date>.tsv`, committed, one file per day it is run. Those say how well the prompt did; this file says what a run cost. Nothing here restates a scorecard, and no scorecard restates a receipt.

---

<!-- NEXT ENTRY GOES HERE — newest first. Add above the rule below; change nothing beneath it. -->

## `<<HORMUZ RECORDING: the day it was made>>` — the committed Strait of Hormuz recording

The generation a keyless clone plays back, made by `make record-demo ONLY=hormuz`. It is the only
committed recording; the other three example sentences have none, and each would cost about the same
again.

| | |
|---|---|
| Model and effort | `<<HORMUZ RECORDING: model and effort>>` |
| Calls | `<<HORMUZ RECORDING: calls>>` |
| Searches | `<<HORMUZ RECORDING: searches>>` |
| Dollars | `<<HORMUZ RECORDING: dollars>>` |
| Wall clock | `<<HORMUZ RECORDING: minutes>>` |
| Map reached | `<<HORMUZ RECORDING: claims and arrows>>` |
| Refusals | `<<HORMUZ RECORDING: refusals>>` |
| Claims with a sourced base rate | `<<HORMUZ RECORDING: sourced base rates>>` |
| Stopped because | `<<HORMUZ RECORDING: stop reason>>` |
| Committed as | `backend/recordings/hormuz.jsonl` |
| Raw record | `<<HORMUZ RECORDING: the kept run under backend/.runs/>>` |

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
