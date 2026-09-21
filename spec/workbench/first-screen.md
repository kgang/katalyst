# The first screen — one screen, four ways to start

## Purpose

Somebody opens this product for the first time. Before this chapter, what they saw depended on
something they had not been told about: whether a model key was set in the environment. With a key,
all four example cards called a model — the committed recording was unreachable, the first claim
arrived about twenty-three seconds after the press, and the screen said nothing in between. With no
key, one card played a recording and the other three were not drawn at all. Two readers, two
different screens, and no way to get from one to the other except by editing a file.

**After this chapter there is one first screen.** It reads the same with a key and without one; it
offers the same four ways to start, in the same order, in the same words. What changes between the
two readers is only **what is enabled, and the reason printed beside what is not**. Nothing is
silently inert and nothing is silently swapped: a reader who wants the recording can have it with a
key in place, and a reader who asks for a live run with no key is told so in a sentence rather than
handed a recording wearing the answer's clothes.

This chapter owns the first screen: the four ways to start, the words on them, where every figure on
them comes from, and what each one does when it cannot be taken. It does **not** own the input bar's
two doors (Explore and Verify — `streaming-growth.md`), the map that grows afterwards
(`streaming-growth.md`), or the keyboard (`keyboard-and-access.md`).

Decision records behind it: **ADR-0012** and its amendment of 2026-09-21 — *a generation is asked
for as a live run or as a recording, and the request says which; the server does what it was asked,
or says plainly why it cannot, and never substitutes one for the other.*

---

## Data model

### What the screen reads about this copy — `Readiness`

Defined in `backend/src/katalyst/api/health.py`, served by `GET /api/readyz`, and read once before
anything else happens. Four fields matter here:

| Field | What it is for |
|---|---|
| `status` | Whether this copy can build a map at all — by calling a model, or by playing a recording |
| `model_key_present` | Whether a key is configured. **Never the key itself.** It is the reason printed beside a disabled way to start, and nothing else: it does not decide what the screen draws |
| `replayable` | One `RecordingSummary` per recording this copy can play, each with the day it was made |
| `unreadable` | One plain sentence per file in the recordings folder this engine could not read. A bad file never hides the good ones, and never hides itself either |

`RecordingSummary` is defined in `backend/src/katalyst/engine/replay.py`.

### What the screen sends — the field that names a start

`GenerateRequest` in `backend/src/katalyst/api/generate.py` carries one field that says how a run
starts:

| Value | What it means |
|---|---|
| `replay` | Play the committed recording of this sentence, through the same route, the same eight events and the same canvas. Costs nothing, calls nobody, and the key is not read |
| `live` | Call a model. Refused in one sentence when no key is configured, and nothing is played in its place |

**A request that says nothing plays a recording.** The reason is one sentence: *a request that did
not ask to spend money must never spend it.* A default is not the server choosing — it is a property
of the request shape, published in the server's own description of itself, identical on every copy
of this program; it reads no key, no environment and no folder.

**A third value is reserved, not built.** Stack 07's *a finished generation served back by its
identifier* is a third value of this one field rather than a second route: three ways a run can
start, one field naming which, one place that reads it.

### Where a figure on this screen comes from

The live row states what a live run costs and how long it takes **before** the press. There is
exactly one measured source for those numbers in this product: **the receipt of the run the
committed recording was made from**, which is a line of `backend/recordings/hormuz.jsonl`. Read on
2026-09-21 it says: `calls: 29`, `seconds: 2179.02`, `dollars: 4.044…`, `effort: "default"`, made on
`2026-09-21`. Printed the way this product prints things, that is *29 model calls, about
thirty-six minutes, $4.04 — the recorded run of this example, on 2026-09-21.*

**Those figures are quoted here to show the shape of the sentence, never to be typed into the
screen.** They are one run's measurement and they move: record 0012's own amendment of 2026-09-20
measures $1.32 and 10 minutes 54 seconds for a Hormuz run on 2026-09-17, and Kent's run of
2026-09-21 was smaller again. A figure typed into a component is a number nobody computed sitting on
the first thing a reviewer reads. **The screen reads them from the server and prints the day they
were measured** — which is INV-workbench.83 below.

**How they reach the screen.** `RecordingSummary` carries them: `calls`, `seconds` and `dollars`
beside `example` and `recording_date`, in the receipt's own field names and the receipt's own units,
read off the file's own receipt line by one builder in `backend/src/katalyst/engine/replay.py` and
served on `GET /api/readyz`. **They are absent together** when a file holds no receipt this engine
can read — a replay rebuilds the receipt rather than emitting the recorded one, so such a file still
plays — and the live row then prints no figure at all. The screen must not reach for them any other
way, and must not print a figure it was not given.

---

## Behaviour

Every example below is the Strait of Hormuz, the one sentence this copy has a committed recording
of: *"The Strait of Hormuz reopens to unrestricted commercial transit."*

### B1 — Four ways to start, always the same four

The screen names itself, says what the product does, and then offers four ways to start, in this
order:

| # | The way | What it says beside it | What the press does |
|---|---|---|---|
| 1 | **Open the map** | `free · instant` | Opens the stored worked example. No request, no model, no recording |
| 2 | **Watch the recording** | `free` · a **replay** badge · `recorded <date>` | Asks for this sentence with the start named `replay` |
| 3 | **Run it live** | What the recorded run cost and how long it took, with the day it was measured | Asks for the same sentence with the start named `live` |
| 4 | **Build the map** | The input bar's own field, and the second field that names where you think it ends | Asks for the reader's own sentence, live |

The words on the screen, as drafted for this chapter:

> **Katalyst.** Type an event you think will happen. Katalyst builds a map of what it would cause,
> step by step, out to things you could trade.
>
> **Four ways to start.** The first two are free and need no key. The other two call a model, and
> say what that costs before you press.

**Ways 1 and 2 never change**, with a key or without one. They are the two that cost nothing, and
they are first for that reason: the most persuasive minute of this prototype should not sit behind a
decision about money.

**Row 4 is `Build the map` word for word**, which is the label the Interface words table in
[`../vocabulary.md`](../vocabulary.md) already gives the input bar's one button. Rows 1 to 3 start a
run rather than edit a map, so they take no row in that table and no code name.

**Only the sentences this copy can actually do something with get a row 2 or a row 3.** Today one
example is recorded, so the recording row offers one. The three unrecorded sentences appear on row 3
only — a live run needs no recording — and one line under the rows names them as having nothing
recorded yet. Nothing more is recorded until the prompt freeze, so this is the shape for now and not
a temporary state on the way to four of everything.

### B2 — The same screen, with a key and without one

Everything in B1 is drawn both times, in the same order, in the same words. The difference is one
thing: **rows 3 and 4 are enabled by the key, and when they are not, the reason is printed in
place.**

With no key, under rows 3 and 4:

> No model key is configured, so this copy cannot call a model. The first two ways need none.

That sentence sits on the rows it disables, not in a banner over the screen, because a reader
looking at a control they cannot press is owed the reason there rather than somewhere above. **A
control that is drawn and cannot be pressed always says why, beside itself** — the rule
`streaming-growth.md` already keeps for the disabled free-text field.

With a key, all four rows are live and nothing is greyed. Rows 1 and 2 are unchanged: **the
recording is still reachable**, which is the case that could not happen before this chapter.

### B3 — The live row says what it costs, before the press

Row 3 carries one quiet line, read from the server:

> The recorded run of this example made 29 model calls, took about thirty-six minutes and cost
> $4.04, on 2026-09-21.

Three rules about that line. **Every figure in it came from the server's answer about itself** — not
from a constant in a component, not from a design document, not from this chapter. **It carries the
day it was measured**, because a price with no date is a promise rather than a measurement. And
**it says whose run it describes**: it is the recorded run, at the effort a recording is made with,
which is not the effort a live run asks for today — a run started from this row asks for less and
will not take as long.

If the server has not said, the row says so and prints nothing: an absence with its reason, never a
blank and never a guess.

### B4 — The recording plays when it is asked for, key or no key

A reader with a key presses **Watch the recording**. The request names `replay`. The recording
plays: the same route, the same eight events, the same canvas, at the pace this copy is set to, with
the replay badge on the canvas and a receipt saying `replay`, zero dollars, and the day the
recording was made. The key is not read, nothing is spent, and nothing about the screen pretended a
model was called.

This is how a reviewer with a key tests the keyless half of the product — Kent's own question on
2026-09-21: *"How can i test out all the functionality if I run it with a valid anthropic key?"*

### B5 — A live run with no key is refused in words, and nothing is played instead

A reader with no key reaches row 3 or row 4 anyway — by keyboard, by an old tab, by a `curl`. The
request names `live`. The server does not play a recording. It answers with a receipt of zeroes and
one plain sentence naming what is missing and what can be asked for instead, and the screen prints
that sentence.

**Nothing is substituted.** Handing back a recorded map as the answer to a question somebody asked a
model is the one change that would make this product lie, and it is what record 0012 has forbidden
from the day it was written.

A recording that was asked for and does not exist keeps the sentence it already has: this copy has
no key and no recording of that sentence, so there is nothing it can honestly show.

### B6 — Before the answer arrives, and when a file will not read

**Before `GET /api/readyz` has answered**, every sentence on the screen says that is what is being
waited for. Nothing is known about a key or a recording until the server has spoken, and a screen
reading *no model key* in the meantime is asserting something nobody told it. It is not a spinner:
the sentence is on screen and names the two things being waited on.

**When a file in the recordings folder will not read**, the server's own sentence for it is printed,
quietly, under the rows. The good recordings still play. A reviewer who dropped a file in that
folder and then counts one recording row where they expected two is owed the reason rather than left
to wonder.

---

## INVARIANTS

Each is *for all X, statement P holds*, and each names what checks it.

**Why this chapter starts at 82.** `INV-workbench.80` and `.81` are taken by
[`streaming-growth.md`](streaming-growth.md) — the foot of the map saying what the run is doing in
ink, and the rule that the only thing changing on a timer is a measured reading — both added
2026-09-21 under decision record 0023. A number is never reused, because a citation written against
one statement must not quietly come to mean another.

| ID | Statement | Checked by |
|---|---|---|
| **INV-workbench.82** | For every way to start this screen offers, and for both states of `model_key_present`, the same ways are drawn, in the same order, with the same words; a way that cannot be taken is drawn disabled with the reason it cannot, beside itself | The first-screen component tests, run twice over one rendering — once with `model_key_present: false` and once with `true` — comparing the ways drawn and their order, and asserting a reason beside every disabled one. **The second of those two runs is new**: every browser test in this repository has run keyless, which is why nobody saw what Kent saw |
| **INV-workbench.83** | For every duration and every price this screen prints, the figure came from the server's answer about itself, and is printed with the day it was measured | A first-screen component test that renders the screen from a readiness answer carrying no figures and asserts no figure is printed; and a source check that no file drawing this screen holds a number of dollars or of minutes |

**INV-workbench.82 is the invariant Kent's walk broke.** The four cards were not the same four with
a key and without one: with a key all four ran live and the recording was unreachable; with none,
three were not drawn at all.

---

## ANTI-PATTERNS

1. **Do not let the server read the key to decide what a reader gets**, because that is the reader
   having no say in either direction — with a key the recording is unreachable, and with none a live
   run cannot be asked for, so the only control anybody has is deleting a line from a file. The
   request names the start; the server does what it was asked or says why it cannot.
2. **Do not fall back from a live run to a recording when anything goes wrong**, because a recorded
   map handed back as the answer to somebody's own question is the one change that would make this
   product lie. A live run that failed is a live run that failed, and it says so.
3. **Do not type a price or a duration into the screen**, because it is one run's measurement, it
   moves every time the prompt or the effort changes, and it would be a number nobody computed on
   the first thing a reviewer reads. Read it from the server and print the day it was measured.
4. **Do not print a figure with no date**, because a price without one is a promise rather than a
   measurement, and the two readings this product has of the same example differ by a factor of
   three.
5. **Do not draw a way to start that cannot be taken and say nothing**, because a control a reader
   counted and cannot use is worse than one that is not there. Either do not draw it, or draw it
   disabled with the reason beside it.
6. **Do not put a mode switch at the top of the screen**, because a control that silently changes
   what four other controls do is a hidden mode, and it gives the screen two states to learn. Each
   way to start says what it is.
7. **Do not solve "the first-time reader is lost" with a product tour, coach marks or first-run
   hints that retire**, because that is the template look the disgust veto names, and state in
   browser storage traces to nobody — two readers on two machines see two different screens with no
   way to say why.
8. **Do not let the request ask for the replay pace**, because a client that could skip the pacing
   could skip the thing a recording exists to show. Pacing is one server setting
   (`KATALYST_REPLAY_PACE`) and is never a field on a request.

---

## Open questions

*Dated 2026-09-21. Each is something this chapter does not settle.*

1. **Does the recording row print how long a replay takes?** It can be worked out — the events in
   the file, times the pace this copy is set to — but neither the count nor the pace is served
   today, and a duration this screen worked out itself would break INV-workbench.83. Until then the
   row says `free` and names the day, and no duration.
2. **Where do the two unpressable rows go?** *Explore* and *Verify* are drawn above everything else
   today and cannot be pressed; what actually chooses the door is whether the second field has
   anything in it. The recommendation is to delete them and let that field's label carry it.
3. **Is there a fifth way — a finished generation reopened by its identifier?** Stack 07 proposes
   it, and the field is designed so that it is a third value rather than a second route. Whether it
   earns a row on this screen, or is only a link somebody was handed, is unsaid.
4. **What does row 3 offer for the three unrecorded sentences?** They have no recording, so they
   have no measured price. Whether row 3 prints the Hormuz run's figures as the nearest measurement
   this product owns, labelled as another example's, or prints nothing at all, is unsaid — and the
   first of those is close enough to a typed-in number to be worth deciding on purpose.
