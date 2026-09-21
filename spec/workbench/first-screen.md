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
`2026-09-21`. Printed the way this product prints things, that is *29 model calls, about 36 minutes,
$4.04 — the recorded run of this example, on 2026-09-21.*

**A duration prints as a numeral, like every other measurement here** *(2026-09-21, as built)*. The
count-in-words rule this product keeps is for counting things a reader is asked to hold in their head
— *one of these four* — while a call count, a duration and a dollar figure are measurements, and the
receipt strip already prints all three as numerals. The screen rounds to whole minutes above a minute
and a half and to whole seconds below it, because *about 95 seconds* is a figure nobody thinks in.

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
| 4 | **Build the map** | `calls a model`, and one note saying its own price is not known in advance | Asks for the reader's own sentence, with the start named `live` |

Ways 3 and 4 carry `calls a model` where ways 1 and 2 carry `free`, so the price of a way is beside
its name before any row under it is read.

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

**Only the sentences this copy can actually do something with get a row under way 2 or way 3.** Today
one example is recorded, so the recording way offers one row. The three unrecorded sentences appear
under way 3 only — a live run needs no recording — and one line under the recording way names them as
having nothing recorded yet: *Nothing is recorded yet for the midterms, export controls and photonic
chips; those can still be run live.* Nothing more is recorded until the prompt freeze, so this is the
shape for now and not a temporary state on the way to four of everything.

**The way itself is always drawn, even with no row under it** *(2026-09-21, as built)*. A copy with
nothing recorded still shows *2 · Watch the recording*, with one sentence under it saying there is no
recording of any of these sentences and who makes one. That is what INV-workbench.82 asks for in so
many words — *the same ways are drawn* — and it is the difference between a reader learning that this
copy has nothing recorded and a reader never learning that the product records anything. The reason
names the missing file, not the missing key: watching a recording never needed one.

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

Row 3 carries one quiet line per recording whose receipt this engine could read, read from the
server:

> The recorded run of the strait made 29 model calls, took about 36 minutes and cost $4.04, on
> 2026-09-21.

and, under them, one note in the same voice:

> That is the recorded run's own receipt, made at the effort a recording is made with. A run started
> here asks the model for less, so it will not take as long — and what it spends is not known until
> it has spent it.

Three rules about those lines. **Every figure in them came from the server's answer about itself** —
not from a constant in a component, not from a design document, not from this chapter. **Each
carries the day it was measured**, because a price with no date is a promise rather than a
measurement. And **each says whose run it describes**, by the example's own short name in the
reader's words — it is that recording's run, at the effort a recording is made with, which is not
the effort a live run asks for today.

**The line belongs to the way, not to a row** *(2026-09-21, answering open question 4 below)*. Today
one example is recorded, so there is one line; four recordings would print four, each naming its own
example. What row 3 does **not** do is print another example's figures beside a sentence that has no
recording, which would be a number nobody computed about the run somebody is actually about to start.
A reader who wants to know what the unrecorded three cost reads the one measurement this product
owns, sees which example it is of, and draws their own conclusion — which is all anybody honestly
can.

If the server has not said — no recording at all, or none whose receipt this engine could read — the
way says so and prints nothing: *No recording here carries a receipt this copy could read, so there
is no measured price to state. Nothing is printed in its place.* An absence with its reason, never a
blank and never a guess.

**Way 4 is a live run too, and says so** *(2026-09-21; the adversarial pass's item 5(e))*. Row 4 was
the door a reader typed into and then waited at with no idea what it would cost, while the way above
it quoted a measured price — and a screen that prices one of two identical actions has told a reader
the other one is cheaper. So way 4 carries a note of its own:

> A sentence of your own calls a model, exactly as **Run it live** does. What it costs is not known
> before it runs, because nobody has run your sentence. The figures under **Run it live** are the
> recorded run of another example — the only measurement this product owns, and not an estimate of
> yours.

Three things it must keep. It **names what it is** — the same kind of run as the way above. It says
its own price **is not known**, rather than leaving the reader to assume the figure above applies. And
it names the measurement that does exist **as another example's**, because the nearest measured thing
labelled as the nearest measured thing is honest, and the same figure offered as a forecast of
somebody's own sentence is a number nobody computed.

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

**Before `GET /api/readyz` has answered**, every way that depends on that answer says that is what is
being waited for, and its rows are drawn and cannot be pressed. Nothing is known about a key or a
recording until the server has spoken, and a screen reading *no model key* in the meantime is
asserting something nobody told it. It is not a spinner: the sentence is on screen and names what is
being waited on.

**The sentence sits once on each way rather than once on each row** *(2026-09-21, as built)*. It is
one fact about this copy, not four facts about four sentences, and four copies of it under four rows
is the same sentence read four times. The two ways ask different questions and so print different
sentences: *Asking the server which of these it has a recording of* on the recording way, and
*Asking the server whether a model key is configured* on the live one — because watching a recording
never needed a key, and printing *no model key* beside it would be the screen blaming the wrong
absence.

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
| **INV-workbench.82** | For every way to start this screen offers, and for both states of `model_key_present`, the same ways are drawn, in the same order, with the same words; a way that cannot be taken is drawn disabled with the reason it cannot, beside itself | `launchpad.test.tsx` › `test_the_same_ways_in_the_same_order_in_the_same_words_for_both_states_of_the_key`, which draws the screen twice over one readiness answer and compares the two lists of ways with each other and with the words themselves; and `test_a_way_that_cannot_be_taken_says_why_beside_itself`. **The keyed run is new**: every browser test in this repository has run keyless, which is why nobody saw what Kent saw |
| **INV-workbench.83** | For every duration and every price this screen prints, the figure came from the server's answer about itself, and is printed with the day it was measured | `launchpad.test.tsx` › `test_a_recording_with_no_readable_receipt_prints_no_figure_at_all` and `test_nothing_is_printed_about_a_price_before_the_server_has_answered`, which render from answers carrying no figures and assert nothing on the screen reads as money or as a length of time; `test_the_live_way_prints_what_the_recorded_receipt_says_and_the_day`, which reads the expected figures off `backend/recordings/hormuz.jsonl` rather than off a number typed into a fixture; and `test_no_file_drawing_the_four_ways_holds_a_price_or_a_duration`, a source check over `Launchpad.tsx` and `launchpad.css` |

**The source check reads the two files that draw the four ways, and not the input bar** *(2026-09-21,
as built)*. `InputBar.tsx`'s destination field carries the placeholder *A Polymarket contract on
Brent below $70*, which is a figure inside an example of a sentence somebody might type rather than a
statement about what anything costs or how long it takes. Widening the check to that file would catch
it, and the fix would be to make the example worse. What covers the input bar instead is the render
half of this invariant: the whole screen is drawn from an answer with no figures in it, and no word
it writes may then read as money or as a length of time.

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
2. ~~**Where do the two unpressable rows go?**~~ **Settled 2026-09-21: deleted.** *Explore* and
   *Verify* were drawn above everything else and could not be pressed, while what actually chooses
   the door is whether the second field has anything in it — which that field's own label already
   says: *Fill this in and the map is graded against it.*
3. **Is there a fifth way — a finished generation reopened by its identifier?** Stack 07 proposes
   it, and the field is designed so that it is a third value rather than a second route. Whether it
   earns a row on this screen, or is only a link somebody was handed, is unsaid.
4. ~~**What does row 3 offer for the three unrecorded sentences?**~~ **Settled 2026-09-21: nothing,
   and the measured line belongs to the way rather than to a row.** Printing the Hormuz run's figures
   beside a sentence with no recording would put a number nobody computed next to the run somebody is
   about to start. B3 above says what is printed instead: one line per recording that has a receipt,
   each naming its own example, with a note saying at what effort it was made. A reader who wants a
   figure for the other three has the one measurement this product owns and can see which example it
   is of.
5. **Does the screen ever say what this copy costs *after* the press?** The receipt says, at the end.
   Whether a live run should carry a running count of calls while it is going is the run strip's
   question (record 0023), not this screen's, and nothing here should grow a second answer to it.
