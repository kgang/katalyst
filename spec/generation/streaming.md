# Streaming — eight events, one request, no spinner

## Purpose

The user types *"The Strait of Hormuz is going to open next week"* and, within a second, sees the map start to exist: a reserved rectangle where the first claim will go, then the claim itself, then the arrow that caused it, then the next. Every proposal the validator refused scrolls past beside it. At the end the likelihoods resolve, the bill is shown, and the stream says why it stopped.

That is one HTTP request. **The stream is the loading state** (FR-5, and UX-8 in `PRODUCT_REQUIREMENTS.md` §7: no spinner anywhere). A generation takes minutes and returns one whole proposal every few seconds (decision record 0006), so there is no honest way to show it as a single answer that arrives at the end — and a spinner followed by a finished map is a veto condition, not a design choice.

This chapter settles what travels down that request: **eight named events**, the order they are allowed to come in, how they are framed on the wire, what a client does with an event name it has never heard of, what the server does when the client closes the tab, and the two other routes that sit beside the stream.

It does **not** settle what the model is asked or what a proposal may contain — that is [`proposals.md`](proposals.md) — nor how evidence is attached — [`grounding.md`](grounding.md) — nor where the bytes come from when there is no key — [`replay.md`](replay.md).

---

## Data model

### The eight events

One file defines them: `backend/src/katalyst/engine/events.py`. The browser mirrors the same eight by hand in `frontend/src/stream/events.ts`, exactly as stack 03b hand-typed its view of a world, and a type-level test (`frontend/src/stream/__tests__/eventsMatchSchema.test-d.ts`) fails the build if the two ever drift.

Each event is one name and one payload. The name is what the wire's `event:` line carries; the payload is what its `data:` line carries.

```python
class GenerationStarted(BaseModel):     # event: generation_started
    """The generation has an identifier and a seed. Nothing has been proposed yet."""
    generation_id: str                  # minted by engine/ids.py, never by the model
    seed: int                           # the one number domain/ will propagate with
    hypothesis: str                     # the sentence the user typed, unaltered
    target: str | None                  # the Verify door's destination, in their words


class ProposalAccepted(BaseModel):      # event: proposal_accepted
    """One proposal passed the rules. The map is now bigger by this much."""
    at: int                             # position in the transcript, counting from 0
    proposition: Proposition | None     # the new claim; identifier minted here
    links: tuple[Link, ...]             # its incoming arrows; identifiers minted here
    frontier: tuple[PropositionId, ...] # claims still open to expand


class ProposalRejected(BaseModel):      # event: proposal_rejected
    """One proposal was refused. Every reason at once, never the first one only."""
    at: int
    claim_in_words: str                 # what the model wrote. Never minted, never a tile
    violations: tuple[Violation, ...]   # domain/validity.py's own codes and sentences
    frontier: tuple[PropositionId, ...] # claims still open. BOTH growth events say it, so a
                                        # claim closed by its third refusal loses its
                                        # skeleton at once


class BeliefsPropagated(BaseModel):     # event: beliefs_propagated
    """Every likelihood, worked through the finished map. Exactly once, at the end."""
    world: World                        # the whole thing, from domain/propagate


class Verdict(BaseModel):               # event: verdict — the Verify door only
    """Whether a path from the hypothesis to the destination exists, and how good it is."""
    kind: Literal["reached", "no_path"]
    path: tuple[PropositionId, ...]     # empty on no_path
    product: float | None               # the multiplied-out likelihood of that path (INV-8)
    nearest: PropositionId | None       # on no_path: the closest claim the map did reach
    why: str                            # one plain sentence


class Receipt(BaseModel):               # event: receipt  (NFR-6)
    """What this run cost. The second-to-last event of every stream."""
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    searches: int                       # web searches this run made. Billed apart from
                                        # tokens, so `dollars` cannot be re-derived without it
    dollars: float
    seconds: float
    mode: Literal["live", "replay"]
    recording_date: date | None         # the day the recording was made; None when live
    prompt_hash: str


class Done(BaseModel):                  # event: done
    """The generation finished. One reason, and the size of what was built."""
    reason: Literal["reached_terminal", "depth_cap", "width_cap", "claim_cap",
                    "spend_cap", "refusal_cap", "no_terminal"]
    claims: int
    links: int
    rejected: int


class Failed(BaseModel):                # event: failed
    """Something on our side broke. One plain sentence, never a stack trace."""
    message: str
```

`Proposition`, `Link`, `Violation`, `World` and `PropositionId` are the rules layer's own types, defined in [`../graph/`](../graph/) and [`../multiverse/`](../multiverse/). Nothing here redefines them; the stream carries them whole, so what the browser draws is what `domain/` computed.

### Four things worth saying about the shapes

**`GenerationStarted.seed` is always a number, even though the request's seed is optional.** A request may leave `seed` out, and then `engine/ids.py` mints one and this event says which — so the run is reproducible from the moment it starts, by the same `(base map, branch, seed)` triple as everything else (INV-5: every world replays from those three). **The browser never invents a seed.** It sends one only to reproduce a run it was handed, which is the one case where a seed means something to the person sending it; a browser that made one up would be putting a number nobody computed into the reproducibility triple. On replay, neither is used: the recording's header carries the seed the recorded run had, and that one wins ([`replay.md`](replay.md)).

**Both growth events carry `frontier`.** `proposal_rejected` says which claims are still open for the same reason `proposal_accepted` does — so the browser can take a skeleton down the instant a claim closes, rather than leaving a rectangle standing where nothing will ever arrive. See "Where the first tile comes from" below for the two closures that make no event of their own.

**`ProposalAccepted.proposition` is optional because two different proposals are accepted through it.** A proposal that adds a claim carries the claim and its one incoming arrow. A proposal that only joins two claims already on the map carries no claim at all — `proposition` is `None` and `links` holds the one new arrow. One event covers both, because from the browser's side both are "the map got bigger"; splitting them would be a ninth event whose only difference is a field that is already nullable.

**`at` is the transcript position, not a timestamp.** It counts from 0 and rises by exactly one on every `proposal_accepted` and every `proposal_rejected` — those two share one counter, because the transcript is the ordered record of what was proposed, and a refusal is a thing that was proposed. It is the key the Inspector uses to point at one line of the transcript, and it survives a replay unchanged. No other event carries it.

**No field is written twice in one stream** (Kent, decision S3, 2026-09-17). `no_path` appears on `Verdict` and nowhere else — `Done.reason` says why the *generation* stopped, which is a different question from whether a route was found, and a generation that reaches every cap can still find its route. `mode`, `recording_date` and `prompt_hash` appear on `Receipt` and nowhere else — `GenerationStarted` used to carry them, and two places to read one fact eventually disagree. The same rule already governs the retraction badge in [`../multiverse/diff.md`](../multiverse/diff.md).

> **Then how does the replay badge appear at the start, when `mode` arrives at the end?**
> It does not come from the stream. The first screen already asked `GET /api/readyz`, which reports `model_key_present`, never the key itself, and — settled 2026-09-17 — **`replayable`, the examples that can be played and the day each was recorded**. So before the first keystroke the screen knows whether anything it runs will be a replay, and knows the date record 0012's sentence has to print. The receipt's `mode` is the *stored* record of what happened, read afterwards in the Inspector. The badge is a fact about the session; the receipt is a fact about the run. The shape is in [`replay.md`](replay.md).

### The seven reasons a generation stops

`Done.reason` has seven values and each says a different true thing. **One rule picks it, and [`proposals.md`](proposals.md) B4 owns that rule: the reason names what closed the last claim that was still open**, with `spend_cap` and `no_terminal` as overrides above it. This is the vocabulary.

| Reason | What happened |
|---|---|
| `reached_terminal` | The last open claim closed on an ending or on the model answering `Stop`, and the map ends in at least one `market` or `not_tradeable` claim (INV-9 — every map ends in something you could trade, or an explicit statement that you could not). The ordinary, good ending |
| `depth_cap` | The last open claim sat as many layers from the hypothesis as the run allowed |
| `width_cap` | The last open claim already had as many children as the run allowed |
| `claim_cap` | The last open claim closed because the map held as many claims in total as the run allowed |
| `spend_cap` | The running receipt reached the run's spending cap (Kent, G5). `Failed` is not used: stopping on budget is a decision, not a fault |
| `refusal_cap` | The last open claim closed because three proposals in a row for it were refused — one line was abandoned rather than ended. Not called `model_stopped`: the model did not stop, our rules refused it |
| `no_terminal` | The map ends nowhere anybody could act on, even after the one last ending-seeking call per open claim, and the stream says so rather than inventing one |

**There is deliberately no `search_cap`.** The searches-per-generation cap (Kent, S2) stops the *searching*, not the generation: past the cap, calls stop declaring the search tool and later arrows come back `argued` instead of `documented`, and the run carries on to a proper ending. A complete map with some unbacked arrows is a better answer than a truncated one, and the origin marks on the wires say which arrows are which. [`grounding.md`](grounding.md) holds the rule. A reason nobody can choose is a reason a reader would one day trust, so the value is not in the literal at all.

**One reason is reported, not a list**, and there is one rule rather than a precedence list to memorise: the reason names **what closed the last claim that was still open**, with `spend_cap` and `no_terminal` as the two overrides above it. [`proposals.md`](proposals.md) B4 owns that rule and works it on the Hormuz map. This chapter owns the seven names; that chapter owns which one a given run gets.

### Where the first tile comes from

The hypothesis is a sentence a person typed, not yet a claim anybody can check, and the same is true of the Verify door's destination. [`proposals.md`](proposals.md) turns each into a checkable claim with one `StartingClaim` call before expansion starts — a shape that is deliberately *not* a proposal, because it has no cause and no arrow.

On the stream they still arrive as **`proposal_accepted` events with an empty `links` tuple** — the hypothesis at `at: 0`, the destination at `at: 1` when there is one. There is no ninth event for them, and there should not be: from the browser's side the fact is the same fact — *a claim joined the map* — and a second way to say one thing is two things that eventually disagree. They are counted in `at` because they belong in the transcript: turning a person's sentence into a checkable claim is exactly the step a reader wants to audit.

A starting claim the rules layer refuses is a `proposal_rejected` like any other, carrying the person's own sentence in `claim_in_words`. If the hypothesis itself cannot be made checkable there is no map to build, and the stream ends in `failed` with one plain sentence — the grammar below allows `failed` to cut in after any event, including the first.

#### And where a tile that never arrives goes away

Two things close a claim without adding anything to the map, and **neither makes an event of its own**: the model answering `Stop` on that claim, and its third refusal in a row. Both are still recorded — a `Stop` leaves a line in the transcript, and each refusal is already a `proposal_rejected` — but neither gets a ninth event name, because the browser does not need to be *told* a claim closed. It reads it:

* **the next growth event's `frontier` no longer names that claim**, which is why both growth events carry `frontier` and not just the accepted one; and
* **on `beliefs_propagated`, every skeleton goes** — the frontier is empty by definition once the map is finished.

So no rectangle ever stands on the canvas waiting for something that is not coming, and no event exists whose only job is to say that nothing happened.

### The grammar

A legal stream is exactly this, read left to right:

```
stream   :=  generation_started  growth  finish
growth   :=  ( proposal_accepted | proposal_rejected )*
finish   :=  beliefs_propagated  verdict?  receipt  done
```

with five rules the grammar cannot carry on its own:

1. **`failed` cuts.** After any event, `failed` may replace everything that was still expected. A stream that ends in `failed` is legal at any length; nothing follows it.
2. **`receipt` is always the second-to-last event**, in both endings — before `done` and before `failed`. A run that broke after ten calls still cost ten calls, and NFR-6 (every generation records model, tokens, cache reads, searches and dollars) does not have an exception for runs that went wrong. A run that broke before its first call emits a receipt of zeroes, which is also true.
3. **`verdict` appears exactly when the request named a `target`**, and never otherwise. It comes after `beliefs_propagated` because `product` — the multiplied-out likelihood of the path (INV-8: any displayed path shows the product of its steps) — is read off the propagated world.
4. **`at` starts at 0 and rises by one** across `proposal_accepted` and `proposal_rejected` together.
5. **A claim that has left `frontier` never returns to it**, and the frontier is empty by the time `beliefs_propagated` arrives. The frontier grows when an accepted claim joins it and shrinks when one closes; it never re-opens a claim, which is what lets the browser take a skeleton down and leave it down.

Three consequences fall straight out, and each is a named test.

* **Beliefs resolve once, at the end.** `beliefs_propagated` cannot appear inside `growth`, so no chip can change four times as its causes arrive. A number that is recomputed on every tile's arrival is four numbers nobody computed. Test: `test_beliefs_arrive_once_after_the_map_is_built`.
* **A refusal is an event, not an error.** `proposal_rejected` sits in `growth` beside `proposal_accepted`. It never becomes a non-200 answer and never becomes `failed`. A generation that hides its misses has deleted half the product. Test: `test_a_rejected_proposal_is_an_event_not_an_error`.
* **Every stream that the client stayed for ends in exactly one terminator.** Test: `test_the_stream_ends_with_done_or_failed`.

A stream that the client *abandoned* has no terminator at all, and that is not a fault — see B4 below.

### The wire

The framing is server-sent events: the format every browser already understands, readable in a terminal with `curl`, and two lines per event.

```
event: proposal_accepted
data: {"at":3,"proposition":{"id":"01J…","claim":"Brent crude settles below $68 …"},"links":[…],"frontier":["01J…"]}

event: done
data: {"reason":"reached_terminal","claims":…,"links":…,"rejected":…}

```

The three counts on `done` are written here as gaps on purpose: they are whatever the run built, and no chapter in this book prints a number it has not measured.

* One event is `event:` then `data:` then a blank line. **The payload is one line of JSON** — never pretty-printed, never wrapped — so a reader never has to join two `data:` lines back together, and a recording can be one event per line ([`replay.md`](replay.md)).
* The answer's media type is `text/event-stream` and it is sent with `Cache-Control: no-store`.
* **The response is a plain `StreamingResponse`** (Kent, S5). Not `sse-starlette`: one fewer runtime dependency, and — the reason that decided it — a library that sends a periodic heartbeat comment line would put a line into every recording that means nothing, and a line in a file that means nothing is a line somebody eventually parses. The generator writes the two lines itself.
* **There is no heartbeat, and no keep-alive line.** A generation emits something every few seconds by its nature, so there is nothing to keep alive.
* **Nothing between the server and the browser may buffer the body — a requirement on the packaged build, not just on the code.** A proxy that buffers holds every event until the last one is written and then delivers them all at once: the growing map becomes a spinner-then-dump, which is the exact thing FR-5 and UX-8 forbid, and it does it *silently in the packaged image while working perfectly in development*. `docker/nginx.conf` forwards `/api/` to the server and, as written today, buffers it. Switching buffering off on that location is part of the stream pull request, which owns the file.

  **The test that proves it is a timing one, and it is the only one in this chapter:** drive `POST /api/generate` through the packaged image and assert that **the first event is received before the last one is written**. It needs no fixed number of milliseconds — it is an ordering claim, not a latency claim — and it fails loudly on a buffering proxy, which no unit test can.

### The transport: `POST`, read as a stream — not `EventSource`

The browser opens the stream with `fetch` and reads the response body as it arrives. It does **not** use `EventSource`, the browser's built-in server-sent-event client. Two reasons, both hard — neither is a preference and neither has a workaround:

1. **The request has a body.** A generation is asked for with a hypothesis, an optional destination, an optional belief of the user's own, a seed and the two loop sizes. `EventSource` can only issue a `GET` with no body. Packing all of that into a query string would put the user's sentence in every server log and every browser history entry, and would cap it at whatever the longest URL that survives a proxy happens to be.
2. **`EventSource` reconnects by itself.** When a connection drops it retries, automatically and invisibly, and our server would answer by *starting a new generation* — a second run, a second map, and a second bill, with nobody having asked for either. There is no way to turn that behaviour off.

The wire format stays server-sent events regardless, because the format costs nothing and it is the one that reads plainly in a terminal.

### There is no resumption

A dropped stream is not resumed. Reconnecting in the middle would need the events so far to be replayable from the server, keyed and outliving the request — and a transcript lives in memory for the life of the process only (below), so after a restart there would be nothing to resume from and the browser would silently get a shorter map than it asked for.

What exists instead is honest and smaller: **a dropped stream is a finished generation with no terminator.** The browser says the stream ended early and offers to run it again, and `GET /api/generate/{generation_id}/transcript` gives back everything that was produced before the connection went — as far as it got, labelled as far as it got. Storage is stack 05's (FR-31: sessions persist to a single SQLite file), and resumption is a question to ask again on top of it.

### Unknown names, and unknown fields

**A client that meets an event name it does not know ignores the event and says so.** It does not throw, does not stop reading, does not guess from the payload's shape. The same holds one level down: a client ignores a field it does not know on an event it does know.

*Says so* means reported once per stream, not once per event: a count and the unknown names, written where a developer sees them. The point is not to recover — there is nothing to recover — it is that the browser's hand-written `events.ts` drifting from the server's `events.py` must show up as a visible number rather than as tiles that quietly never appear. The build's real guard is the type-level test named above; this is the guard for the running app. Test: `test_an_unknown_event_name_is_ignored_and_reported` (browser, stack 04a).

This is what lets a ninth event be added later without a version number on the wire: old clients skip it and keep drawing.

### The three routes

All under `/api/`, like everything else, in `backend/src/katalyst/api/generate.py`.

| Route | Body | Answer |
|---|---|---|
| `POST /api/generate` | `{hypothesis, target?, user_belief?, seed?, versions?, worlds?}` | `text/event-stream` — the eight events, in the grammar above, ending in `done` or `failed` |
| `POST /api/generate/insert` | `{base_id, branch, claim_in_words, position}` | A `DraftedInsert`: one `Insert` intervention — a claim and its arrows, drafted and already validated — **and its own small receipt** |
| `GET /api/generate/{generation_id}/transcript` | — | The transcript of a generation this process still holds; `404` with a plain sentence when it does not |

**`seed` is the one optional field with a rule behind it.** Left out, `engine/ids.py` mints one and `generation_started` says which; sent, it reproduces a run the browser was handed. **The browser never invents a seed** — the three world routes still *require* one, because by then the run has a seed and asking for a world under a different one is asking a different question. On replay the recording's header seed wins over anything in the request.

**A seed is bounded to the whole numbers a browser can hold exactly: at most 2^53 − 1** (coordinator, 2026-09-20). JavaScript has one number type and it stops counting in ones above that, so a larger seed would arrive back at the server as a *different* seed and the run would not replay — silently, and only sometimes. The bound goes on every route that takes a seed, here and on the three world routes, and **`engine/ids.py` mints inside it**: the first live run minted `4803646386380448080`, which is about a thousand times too large. As with the loop sizes, a seed outside the range is refused with a `422`, never reduced to fit.

**`position` is the place in the branch the new edit goes — and it is `position`, not `at`.** `at` is already two things: a transcript position on a stream event, and a date on an edit. A third meaning on a third shape is how a field stops meaning what it says.

**`base_id` here is the generated map's own identifier, exactly as `World.base_id` carries it.** Not the generation's identifier, and not the short name of a stored example: the map a generation produced *is* the base map every branch on it is computed against, so the word means on this route what it means on the three world routes, and the browser passes through the value it already has.

**`insert` is the one intervention that calls the model.** Anti-pattern 2 in `PRODUCT_REQUIREMENTS.md` §10 forbids re-prompting for a whole map after an edit, and names one exception: `insert`, over the affected subtree only. The other five edits — *Suppose this is true*, *This happened*, *Change this push*, *Split this claim*, *My own number* — are pure arithmetic in `domain/`, which is why a reviewer with no key still gets the whole multiverse at full fidelity.

The drafted claim is validated exactly like any other proposal, by the same `domain.validate`, with the same refusal codes. A draft that does not fit comes back `422` with **every** reason at once — the shape `backend/src/katalyst/api/worlds.py` already uses for a refused branch. Test: `test_an_insert_is_validated_like_any_other_proposal`.

**An insert answers with its own receipt** (settled 2026-09-20; the open question below records how). An insert is not one call: [`proposals.md`](proposals.md) drafts the user's claim with the same starting-claim shape the hypothesis uses, and then the ordinary walk proposes its arrows one per call. So it spends real money, and NFR-6 (every generation records model, tokens, cache reads, searches and dollars) has no exception for money spent outside a stream.

```python
class DraftedInsert(BaseModel):
    """What the insert route answers with: the edit, and what drafting it cost."""
    insert: Insert       # the claim and its arrows, already validated
    receipt: Receipt     # the same shape the stream's receipt event carries
```

One shape for a cost, used twice — a second, smaller "insert cost" shape would be the same fact with a second set of field names. On replay the receipt is rebuilt exactly as a replayed stream's is: `mode: "replay"`, zeros, and the recording's date and hash ([`replay.md`](replay.md)).

With no key, this route declines in plain words rather than failing: *"drafting a new claim needs a model key."* The one exception is the scripted intervention each recording carries — [`replay.md`](replay.md).

### Upper bounds on `versions` and `worlds`

`versions` — how many versions of the map to try — and `worlds` — how many worlds to run under each — are today bounded **below** only: `versions > 0` and `worlds > 1` on the three world routes. That is one guard short. A request for a hundred million versions is not refused; it is accepted and the server works on it until something else gives out.

**Both get an upper bound, on this route and on the three world routes** (Kent, S2). Two named constants live in `backend/src/katalyst/engine/worlds.py` beside `VERSIONS` and `WORLDS`, the defaults they already sit next to.

**The budget they are measured against is the server's own, not the browser's.** NFR-7's hundred milliseconds is a *rendering* budget — sixty tiles drawn and laid out again — and it has nothing to say about how long `propagate` may run. The quantity that matters here is the one [`../multiverse/propagation.md`](../multiverse/propagation.md) already times: how long one world takes to work through, at the shipped loop sizes, on the machine those timings were taken on. The ceiling is **the largest pair of loop sizes that keeps one request inside the time a person will wait for a world before assuming the app has stopped**, measured the same way and written down with the measurement and the date beside it, in that chapter's units.

The values are **measured, not invented**, and the ceiling is never below the shipped default. Until they are measured, nothing may quote one.

**A request above the ceiling is refused, never clamped.** Clamping is a repair: the caller asks for one run and silently gets a different one, and every number that comes back is answering a question nobody asked. Refusal is a `422` naming the field and the ceiling, which pydantic's `le=` produces for free. Test: `test_a_run_above_the_loop_ceilings_is_refused_not_clamped`.

### Where a transcript lives

**In memory, keyed by the `generation_id` the stream announced, for the life of the process** — and streamed to the browser as it is produced, so the stream and the store are filled from one pass, never from two. Nothing is written to disk except by the recording commands ([`replay.md`](replay.md)).

**The key is the generation's identifier and nothing else — on a replayed run exactly as on a live one.** The first build filed a replayed run's transcript under the *map's* identifier, so the browser asked for the transcript with the identifier `generation_started` had just handed it and got a `404`. The only identifier a client has ever seen for a run is the one the stream announced; anything else is a second way to name one thing, and the second way is the one that breaks.

The map a generation produced is held alongside it, because a reviewer who has just watched a map draw itself then wants to *suppose* something on it, and the world routes need a map to fold a branch onto. That map is found by **its own** identifier — `World.base_id` — so `engine/worlds.py`'s lookup answers from two places, the stored examples first and then the generations this process is holding, and `(base map identifier, branch, seed)` keeps meaning exactly what it means everywhere else (INV-5: every world replays from those three). Two identifiers, two questions: *which run was that* and *which map is this*.

Two things bound it. A process holds the most recent generations and drops the oldest; how many is an argument with a default the builder picks. And a restart empties it, at which point the transcript route answers `404` with a sentence saying the generation is no longer held, rather than an empty transcript that reads like a generation which proposed nothing.

Writing a second on-disk store now would be a store to migrate in stack 05 for no gain today. FR-31 puts sessions, graphs, branches and transcripts in one SQLite file, and that is where this goes.

---

## Behaviour

Worked on the assignment's own examples. The map's cast — **H** the hypothesis, **C** the Lloyd's war-risk premium, **B** Brent settling below $68, **M1** and **M2** the tradeable endings — is the Strait of Hormuz map written out in `backend/src/katalyst/fixtures/hormuz.py` and tabulated in [`../workbench/README.md`](../workbench/README.md).

### B1 — Explore: a sentence becomes a map

The user types *"Photonic chips get adopted faster than expected"*, leaves the destination field empty, and presses **Build the map**.

1. `POST /api/generate` with the sentence, no `target`, and **no seed** — the browser has not been handed a run to reproduce, so it does not invent one.
2. `generation_started` arrives at once — before any model call has returned — carrying the generation's identifier and **the seed the server just minted**, so the run is reproducible from its first event. The canvas puts a reserved rectangle on screen. **This is what NFR-7's "first paint within a second" means for a pipeline that returns whole proposals**: the first thing the user sees is the map beginning, not a word of the model's.
3. The first `proposal_accepted` at `at: 0` carries the **hypothesis itself**, turned into a checkable claim, with an empty `links` tuple — it has no cause. The reserved rectangle becomes a real tile.
4. More `proposal_accepted` events arrive, one every few seconds, each with one claim, its incoming arrow, and the claims still open. Tiles fill their reserved space; a wire draws only once both of its ends exist.
5. `proposal_rejected` events are mixed in among them — the same counter, the same stream — each with the validator's own sentence. They go in the strip beside the map, never on the canvas: a refused claim was never minted and has no identifier to draw.
6. The frontier empties. `beliefs_propagated` arrives with the whole world; every chip resolves, once.
7. `receipt`, then `done` with `reason: "reached_terminal"` and the three counts.

No `verdict`: there was no destination to grade.

### B2 — Verify: a destination, reached

The user types *"The Strait of Hormuz is going to open next week"* and, in the destination field, *"Brent crude settles below $68 for five sessions"*.

Same as B1, with `target` set, and one more event: after `beliefs_propagated`, a `verdict` with `kind: "reached"`, the graded **path** as a list of claim identifiers, `product` — the multiplied-out likelihood of that path — and one plain sentence. `nearest` is `None`, because the destination itself was reached.

### B3 — Verify: no path, and no bridge

The user types *"Models more capable than Fable get export restricted by the United States"* and asks for *"Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%"*.

The map grows. Nothing it grows connects export controls on frontier models to Gulf shipping insurance. The caps run out and `verdict` arrives with `kind: "no_path"`, `path` empty, `product` `None`, `nearest` naming the closest claim the map actually reached, and `why` saying so in one sentence. `done` follows with whichever cap ended the run.

**`Done.reason` is not `no_path`**, and it never can be: the generation stopped because it hit a cap, and `no_path` is the answer to a different question (Kent, S3). The browser draws the `no_path` card from the verdict (UX-13: the `no_path` verdict is a first-class card, not an error state).

Nothing in the code can produce a path here. There is no code path that adds an arrow to make one, which is what the deliberately unreachable eval case exists to prove — [`evaluation.md`](evaluation.md).

### B4 — The user closes the tab

The generation is part-way through. The browser goes away.

The generator notices the client has gone and **stops before the next model call**. Nothing already in flight is retried, nothing is re-asked, and no further money is spent — which is the whole reason this behaviour is specified rather than left to chance. The partial transcript and the partial map stay in memory under the generation's identifier, and `GET /api/generate/{generation_id}/transcript` gives them back, as far as they got.

The stream has no terminator. That is the honest record of what happened: nobody was there when it would have been sent. Test: `test_the_stream_stops_calling_the_model_when_the_client_goes_away`.

### B5 — An event the browser has never heard of

A server is deployed with a ninth event. An older browser tab is still open.

It reads the `event:` line, does not recognise the name, skips to the blank line, and carries on. At the end of the stream it reports once: how many it skipped and what they were called. The map it drew is a correct map made of the events it did understand.

### B6 — "…but Iran is struck the next day"

On a finished Hormuz map the user presses **Add a claim** and types the sentence. The browser calls `POST /api/generate/insert` with the map's identifier, the branch built so far, the sentence, and `position` — where in the branch the new edit goes.

The answer is one `Insert` — the claim, complete with how and when it will be checked, and the arrows attaching it to the map — already run through `domain.validate`. The browser appends it to the branch and asks the world routes for a new world and a new diff. Nothing about the rest of the map is re-prompted: anti-pattern 2 allows the subtree the insert touches and not one claim more.

---

## INVARIANTS

Each statement holds for every input a named generator can produce, and each names the automated test that checks it.

Two of the generators here are **finite corpora rather than Hypothesis strategies**, and deliberately: a stream needs either a model or a recording to exist at all, so there is no way to conjure one from nothing. They are `recordings()` — every file under `backend/recordings/` — and `cassettes()` — every recorded exchange under `backend/tests/cassettes/`. The third, `event_streams()`, is an ordinary Hypothesis strategy in `backend/tests/strategies.py`: it **builds** sequences by the grammar above rather than generating noise and discarding most of it, and `broken_streams(rule)` builds the same sequences with exactly one grammar rule broken — the shape `broken_graphs(rule)` already uses in [`../graph/validity.md`](../graph/validity.md).

Local numbers in `spec/generation/` come from one shared pool. **This chapter holds `INV-generation.16` through `INV-generation.21`**; the split across all five chapters is on the [landing page](README.md).

**INV-generation.16 — the grammar holds.** For all streams from `event_streams()` and all generations replayed from `recordings()`: the sequence of event names matches the grammar, `generation_started` is first and appears once, `beliefs_propagated` appears at most once and never before the last growth event, `verdict` appears exactly when the request named a target, and `receipt` is the second-to-last event. For all streams from `broken_streams(rule)`, the reader rejects the stream and names that rule. Test: `test_generate_streams_events_in_order`.

**INV-generation.17 — one terminator, and it is last.** For all generations replayed from `recordings()` and all streams from `event_streams()`: exactly one `done` or `failed` appears, it is the final event, and nothing follows it. A stream abandoned by its client has none, which is the one legal exception and is tested as itself. Test: `test_the_stream_ends_with_done_or_failed`.

**INV-generation.18 — a refusal never becomes an error.** For all cassettes from `cassettes()` that hold a proposal the rules layer refuses: the request's status stays `200`, the refusal arrives as a `proposal_rejected` event carrying every violation the validator returned, and the stream continues. Test: `test_a_rejected_proposal_is_an_event_not_an_error`.

**INV-generation.19 — beliefs resolve once, at the end.** For all generations replayed from `recordings()`: exactly one `beliefs_propagated` event appears, and no `proposal_accepted` or `proposal_rejected` follows it. Test: `test_beliefs_arrive_once_after_the_map_is_built`.

**INV-generation.20 — the client going away stops the spending.** For a generation whose client disconnects after the *n*th event: no model call is made after the disconnection, and the receipt held in memory names exactly the calls made before it. Test: `test_the_stream_stops_calling_the_model_when_the_client_goes_away`.

**INV-generation.21 — every number a request can give is bounded at both ends.** For all integers outside `[1, MOST_VERSIONS]` given as `versions`, outside `[2, MOST_WORLDS]` given as `worlds`, and outside `[0, 2^53 − 1]` given as `seed`, on `POST /api/generate` and on the three world routes: the answer is `422` naming the field and the bound, and no run starts. No value is silently reduced to fit. And for all seeds `engine/ids.py` mints: the value is inside that same range, so a minted seed can always be sent back. Test: `test_a_run_above_the_loop_ceilings_is_refused_not_clamped`.

**Checked in the browser, listed here so the two halves agree.** `test_an_unknown_event_name_is_ignored_and_reported` (an unknown name is skipped and counted, never thrown) and `test_there_is_no_spinner_anywhere`, both in stack 04a's `../workbench/streaming-growth.md`.

---

## ANTI-PATTERNS

**1. Do not use `EventSource`.** *Because* it can only send a `GET` with no body, so the user's sentence would have to travel in a URL, and *because* it reconnects on its own — a dropped connection would start a second generation and pay for it, with nobody having asked. **Do** use `fetch`, read the body as it arrives, and keep the server-sent-event framing for the readability it costs nothing to have.

**2. Do not add a heartbeat or any comment line to the stream.** *Because* a recording is this stream line for line, and a line that carries no event is a line that will eventually be parsed as one, filtered out by hand, or quietly counted. **Do** rely on the fact that a generation emits a real event every few seconds. If a proxy in front ever needs traffic to stay open, fix the proxy.

**3. Do not emit a belief when a claim arrives.** *Because* a chip that changes four times as its causes arrive has shown four numbers nobody computed, and only the last of them is the engine's answer. **Do** emit `beliefs_propagated` once, after the map is finished, as the grammar requires.

**4. Do not turn a refused proposal into an error.** *Because* watching the validator refuse the model is half of what this product is for, and a non-200 answer ends the stream and deletes it. **Do** stream `proposal_rejected` with every violation, and let the run carry on.

**5. Do not put `mode`, the recording date or the prompt hash on `GenerationStarted`.** *Because* they are already on `Receipt`, and two places to read one fact eventually disagree — the identical argument that moved the retraction badge onto the world. **Do** read the session's replay state from `GET /api/readyz` before the stream starts, and the run's record from the receipt afterwards.

**6. Do not clamp `versions` or `worlds` to the ceiling.** *Because* the caller then gets numbers computed for a run they did not ask for, with nothing on screen saying so. **Do** refuse with `422`, naming the field and the bound.

**7. Do not put a stack trace, an exception class or an identifier in `Failed.message`.** *Because* it is interface text and the person reading it cannot act on any of the three. **Do** write one plain sentence, and keep the detail in the server's own log.

**8. Do not resume a stream.** *Because* it needs a server-side store of events that outlives the request, which does not exist until stack 05, and a half-built resumption silently hands the browser a shorter map than the one that ran. **Do** say the stream ended early, and offer the transcript route and a fresh run.

---

## Open questions

Raised 2026-09-17.

1. **What an `insert` costs, and where that cost shows.** NFR-6 says every generation records model, tokens, cache reads, searches and dollars — and the insert route answers once, with no `receipt` event, because it is not a stream. So the money it spends had nowhere to be seen. Raised by the workbench chapter and assigned here.
   **Decided 2026-09-20: the route answers with a `DraftedInsert` — the edit and its own `Receipt`.** What made it answerable was learning that an insert is *several* calls, not one ([`proposals.md`](proposals.md): the starting-claim shape drafts the user's claim, then the ordinary walk proposes its arrows one per call). A single cheap call might have been fair to fold into the map's own transcript; several are not, and the person pressing the button is the person who should see the bill. The alternatives both lost on the same ground: folding it into the generation's transcript files this run's cost under a different run, and a running total in the browser is a number that vanishes on a page reload.
2. **How many generations a process should hold before it drops the oldest.** It is an argument with a default, and the default wants one measurement: the size of a finished thirty-claim map and its transcript in memory. Measure it with the first Hormuz generation, alongside the cost measurement that is already going into `STATUS.md`.
3. **Should `Failed` carry a stable code beside its sentence?** Every other refusal in this codebase does — `Violation` has a code the browser switches on and a sentence the person reads. `Failed` has only the sentence today, which is enough for "say something honest" and not enough for "offer the right next step". Decide when there is a second thing the browser would do differently.
4. **Whether a generation should be resumable once stack 05's store exists.** FR-31 puts transcripts in SQLite; at that point the events so far are on disk and resumption becomes cheap. It is still not obviously *wanted*: a reviewer whose connection dropped would rather start again than join a run half-finished. Ask on top of stack 05, not before.
