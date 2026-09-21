# Replay — the four examples, with no key

## Purpose

Someone from the Catalyst team clones this repository, runs `docker compose up`, opens the browser — and has no reason to spend money on a model key. Everything this prototype is judged on lives past that point: a map drawing itself claim by claim, the validator refusing the model in public, a step changed and the trades moving.

**Replay puts all of it in front of them.** With no key, the four example hypotheses from `ASSIGNMENT.md` play from committed recordings, through the same route, the same stream and the same canvas the live path uses. The only substitution anywhere is where the bytes came from, and the screen says so.

This is decision record 0012, accepted by Kent on 2026-09-17, made concrete: the file format, what is stored and what is deliberately not, how a recording is written, the one scripted intervention each one carries, how a run's refusals are shown honestly whether there were any or none, and the build check that keeps them from going stale in silence.

Record 0012 names four event types. **This chapter names all eight** — and one of those four is the single event a recording never stores.

---

## Data model

### The file

`backend/recordings/<example>.jsonl` — one committed file per example, four of them. The extension is JSON Lines: **one JSON object per line, no surrounding array, no commas between lines**, so the file can be written a line at a time while a run is still going, read a line at a time without holding it all in memory, and diffed in git as text.

```
{"base_id":"01J…","seed":…,"recording_date":"2026-09-…","prompt_hash":"…","insert":{…}}
{"event":"generation_started","data":{…}}
{"event":"proposal_accepted","data":{…}}
{"event":"proposal_rejected","data":{…}}
…
{"event":"receipt","data":{…}}
{"event":"done","data":{…}}
```

**Line 1 is the header. Every line after it is one event.** They are told apart by one thing: an event line has an `event` key and the header does not. The event lines carry exactly the two fields the wire carries — the name and the payload — so the replayer writes `event:` and `data:` straight out of the file without re-deriving anything, which is what makes "a recording is the stream, line for line" literally true rather than nearly true.

```python
class RecordingHeader(BaseModel):
    """The first line of a recording: everything that is true of the whole file.

    It must never carry a likelihood, a range, or a World. Numbers are recomputed
    from the seed, and a number stored here could one day disagree with the engine
    that is running.
    """
    base_id: str              # the identifier of the map this recording builds
    seed: int                 # the one number domain/ re-propagates with
    recording_date: date      # the day the run behind this file was made
    prompt_hash: str          # a hash of the prompt the run was made against
    insert: RecordedInsert    # the one "…but X happens" this recording can answer


class RecordedInsert(BaseModel):
    """The single scripted intervention a keyless reviewer can make on this map."""
    claim_in_words: str       # what the card offers, word for word
    answer: Insert            # the claim and its arrows, drafted live and validated
```

**`base_id` is the identifier of the map the recording builds, minted by `engine/ids.py` when the recording was made** — a ULID, twenty-six characters, and emphatically *not* the word `hormuz`. The file is called `hormuz.jsonl` because that is the launchpad card's short name; the map inside carries a minted identifier so it can never be confused with the hand-written stored example that already answers to `hormuz`. Nothing parses meaning out of an identifier (decision record 0003).

`recording_date` and `prompt_hash` have the same names here as on the `Receipt` event, because the receipt's values are copied from here. One name for one fact.

### What a recording stores — six of the eight events

| Event | Stored? | Why |
|---|---|---|
| `generation_started` | yes | The identifier, the seed, the sentence, the destination |
| `proposal_accepted` | yes | The claim and its arrows, with the identifiers minted at record time |
| `proposal_rejected` | yes | Every refusal the run produced, in order. **Zero is a legal count** (Kent, G9, 2026-09-20) |
| `beliefs_propagated` | **no** | Recomputed. See below |
| `verdict` | yes, on a Verify example | Reached, or `no_path` with the nearest claim |
| `receipt` | yes | The original run's tally, which the replay rebuilds from |
| `done` | yes | Every committed recording ends here |
| `failed` | **no** | A run that broke is re-run, not committed |

So a committed file holds five kinds of line on an Explore example and six on a Verify one, plus the header.

### What replay rebuilds — two events, not one

Every event is re-emitted unchanged **except two** (Kent, decision S4, 2026-09-17).

**`receipt` is rebuilt.** A replay made no calls, so the receipt says exactly that:

| Field | On a replayed receipt |
|---|---|
| `mode` | `"replay"` |
| `recording_date` | the header's date |
| `prompt_hash` | the header's hash |
| `effort` | the header's effort: how hard the model was asked to try when the map was **recorded**, not how hard this replay tried — a replay asks nobody anything, and what a reader wants to know is how the map they are watching was made (Kent, G13, 2026-09-21) |
| `dollars` | `0.0` |
| `calls`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `searches` | all zero — this run made no calls, used no tokens and searched for nothing |
| `model` | copied from the recorded receipt: the model that actually wrote this map, which the reader is entitled to know |
| `seconds` | how long *this* replay took to play |

The whole tally is zeroed together rather than dollars alone. A receipt showing tokens with no dollars would be a receipt that contradicts its own price table, and the Inspector would be printing a cost that was paid by somebody else on another day.

`seconds` is the one field that is neither zero nor from the header, and it is the run's own clock. **This does not weaken NFR-2** (the same base map, branch and seed give byte-identical worlds): that promise is about the *world* — the numbers on the map — and the world here is recomputed from the seed, not read from a file. `test_replay_is_byte_identical_across_runs` compares worlds, exactly as decision record 0012 wrote it.

**`beliefs_propagated` is recomputed, and therefore never stored.** The header carries the seed; the accepted proposals carry the map; `domain/propagate` does the rest. The replayer emits the event at the point the grammar in [`streaming.md`](streaming.md) requires, out of its own recomputation.

Three things follow, and the third is the reason:

1. **A recording holds no `World` at all.** Not a likelihood, not a range, not a day-by-day series.
2. The files stay small — record 0012 budgets a few hundred kilobytes for four runs of roughly thirty claims, and the stored numbers would have been most of the weight.
3. **Replay and live agree by construction.** Both end up running the identical `(base map, branch, seed)` through the identical `propagate`, which is INV-5 — every world replays exactly from those three — doing the work. Store the numbers instead and the day propagation changes, the demo shows numbers the engine no longer produces, and nothing goes red.

### Pacing

A fixed delay between events, so the map grows at a speed a person can watch. It is **cosmetic and nothing else**: it never changes an event, an order, or a number.

The delay is an argument with a default the builder picks, and the default is picked against a measurement rather than taste — a live proposal takes a few seconds to come back (decision record 0006), so a replay that races is teaching the reviewer that the product is faster than it is.

**`instant` drops the delay to nothing.** It is a setting, read by `katalyst.settings` like everything else the environment says, and it is **not** a field on the request: pacing is presentation, and a client that could ask for instant replay would let anyone who opened the network tab skip the thing the recording exists to show. The test suite sets it; so does the `recordings` build job; `engine/replay.py` takes it as a keyword argument whose default is the setting.

---

## Behaviour

### B1 — The keyless first screen

The first screen asks `GET /api/readyz` — the one route it reads, and the one place the environment is looked at. It reports whether a model key is configured, never the key itself, and **what can be replayed** (settled 2026-09-17):

```python
class RecordingSummary(BaseModel):
    """One recording the first screen can offer, and when it was made."""
    example: str              # the short name of the example, matching its file name
    recording_date: date      # the day the run behind it was made


class Readiness(BaseModel):
    """The answer to "can this program do its job yet?"."""
    status: Literal["ready", "not_ready"]
    model_key_present: bool
    replayable: tuple[RecordingSummary, ...]
```

**`status` must not read `not_ready` for a program that can replay.** A copy of Katalyst with no key and four recordings can draw four maps, refuse proposals in public, and take every intervention at full fidelity; calling that *not ready* would be the screen lying about itself in the one place it exists to be honest. `status` is `not_ready` only when there is neither a key nor anything to replay.

One name for the day a recording was made — **`recording_date`**, here, on the header, and on the `Receipt` event. Never `recorded_on`, never `made_on`.

With no key, and recordings on disk:

* The four launchpad cards are offered as replays, and the screen says so, **word for word**:

  > **No model key configured — these four run from recordings made on \<date\>.**

  The date comes from `replayable`, and from nowhere else.

* The free-text hypothesis field is **visibly disabled, carrying that same sentence** — never silently inert, which teaches the user that the product is broken rather than that this copy of it is unconfigured.
* A `replay` badge sits on the canvas for the whole session.

Key present, and the same four run live, untouched by any recording. There is no mixed mode and no fallback from live to recorded: a live run that fails is a live run that failed, and it says so.

### B2 — Hormuz, replayed

The reviewer presses the Hormuz card. The browser calls `POST /api/generate` exactly as it would live — same route, same body, same reader — carrying the card's sentence, *"The Strait of Hormuz is going to open next week"*.

**Which recording plays is decided by the sentence, not by the card.** The replayer compares the request's `hypothesis` against each recording's own `generation_started.hypothesis`, **exact after trimming surrounding spaces** — the same rule `RecordedInsert` uses for the scripted intervention, because one matching rule is easier to trust than two. Nothing matches, and the answer is one plain sentence saying this copy has no recording for that sentence. **Never a nearest match**: playing the Hormuz map back at somebody who asked about photonic chips is worse than saying no, and it is indistinguishable afterwards from the product working.

**The recording's seed wins.** The request may carry a seed or leave it out — on this path it makes no difference, because the header's seed is the one the recorded run had, and the numbers are recomputed from it. A replay that honoured a seed from the request would produce a world the recording never showed, under a badge saying *replay*.

The server has no key, so `engine/replay.py` serves the stream: header read, `base_id` and `seed` in hand, then each event line written out as `event:` and `data:`, spaced by the cosmetic delay. Skeleton tiles, claims, wires in causal order, refusals in the strip beside the map, skeletons coming down as each growth event's `frontier` shrinks — the canvas cannot tell, and that is the point.

Where `beliefs_propagated` belongs, the replayer stops, hands `domain/` the map the accepted proposals built plus the header's seed, and emits the world it gets back. Then the rebuilt `receipt` — `mode: "replay"`, zero dollars, zero searches, the recording's date and hash — then `done`.

### B3 — Everything the reviewer does next is live arithmetic

On the replayed map, **Suppose this is true**, **This happened**, **Change this push** and **My own number** all work at full fidelity with no key, because all four are pure arithmetic in `domain/` — no model, no network, no clock. The map identifier from the header, the branch the reviewer is building, and the seed go to the world routes exactly as they would for a stored example.

**The multiverse is not faked at any point.** Only the generation was recorded.

### B4 — The one recorded intervention

Each card offers one scripted "…but X happens" — on Hormuz, *"…but Iran is struck the next day"*. Pressing **Add a claim** fills the field with that sentence.

`POST /api/generate/insert` arrives. With no key, the route compares the sentence against the header's `RecordedInsert.claim_in_words`, **matched on the exact words after trimming surrounding spaces**, and hands back the `Insert` recorded against it — a claim and its arrows, drafted live when the recording was made and validated then exactly as it would be now.

There is no fuzzy matching, and there will not be. Drafting a claim from a sentence is the model's job; a string-similarity score doing it badly would be a piece of state nobody could trace to an input, a rule or a source.

### B5 — Any other insert is declined, in words

The reviewer types a sentence of their own. The route answers, plainly:

> *"drafting a new claim needs a model key."*

Not an error, not a stack trace, not a disabled button with no explanation. It is the one thing in the whole replayed flow that genuinely needs a key, and saying so is more honest than hiding the button.

### B6 — Two commands: one spends, one promotes. **A paid run is never discarded**

The first live runs taught this the expensive way: a run costs real money and takes about a tile a minute, so throwing one away because it failed a check afterwards throws away the measurement as well as the map.

```
make run-demo    ONLY=hormuz CAP=…   # spends money, measures, keeps everything. Writes NO recording
make record-demo ONLY=hormuz CAP=…   # runs the above, then promotes the result if it passes the checks
make run-demo    EFFORT=medium       # the same run, thinking less hard
make run-demo    MODEL=claude-opus-5 # the same run, on the other model
```

* **`make run-demo` always keeps the whole run**, whatever becomes of it, under **`backend/.runs/<example>-<when>-<generation>.json`**, git-ignored and never shipped. Every paid call is on disk before anything decides whether it was any good. This is where the first measured run lives, and it is where the next one's receipt is read from for [`../../docs/measurements.md`](../../docs/measurements.md).
* **A kept run carries more than a recording does, and it is written twice** (*decided here*, 2026-09-20; the chapter first said the two were the same file format). It holds the seconds and the thinking tokens behind every call, which are on no event and in no recording, and it holds the reason a run stopped when nobody chose one. It is written the moment the generation ends and **before** the scripted intervention is drafted, then written again to the same file with the intervention on it — so an exception anywhere after the first paid call still leaves the money on disk. A 26-minute run was lost to a crash between those two points before this existed. The name carries the generation's own identifier as well as the second it started in, so two runs inside one second are still two files.
* **`make record-demo` is still the only way a file lands in `backend/recordings/`.** It runs `make run-demo` and then promotes the result — copying it across **only if it passes every check in B9**. A run that fails a check stays in `.runs/`, legible and re-readable, and the person decides what to do next.
* `CAP` is the run's spending ceiling in dollars (Kent, G5). The default is the **$15 hard stop written in code**, checked against the running receipt after every call and between the rounds of research inside one; a run that reaches it stops with `done.reason = "spend_cap"` and a plain sentence naming what was spent and what was got. **The argument can only lower the ceiling, never raise it above the figure in code** — a cap a caller can raise is not a cap. The cross-run total for the stack, about $500, is a working agreement kept in [`../../docs/measurements.md`](../../docs/measurements.md); nothing is stored between runs until stack 05.
* `ONLY` names one example, because G6 records Hormuz well before the other three. `EFFORT` and `MODEL` are pinned for the whole of one run and read once when it starts (Kent, G8/G10, 2026-09-20). **`EFFORT` unset sends no such field at all** and the run takes the service's own default — *record rich* (Kent, G13, 2026-09-21): a recording is made once and played back by everybody, so it is worth the model's best, and the request stays byte for byte what it was before anybody had an opinion. A live run through the stream route asks for `medium` instead, because a reader is waiting. The header says which, and so does the receipt. `MODEL` unset is the one the settings name, `claude-sonnet-5`. Neither is ever varied between the calls of one run: both sit in the part of a request the service remembers, and changing either mid-run would throw that prefix away at full price.
* With no key both refuse to start and say so. **Only the coordinator runs either**; no sub-agent holds a key.
* **A recording is re-made whenever a prompt changes.** This is the rule the cassettes already carry (decision record 0008), on the same pull-request checklist line: *"prompt changed? cassettes re-recorded, demo recordings re-recorded"*.
* **Nothing else ever writes a recording** — not a test, not a fixture script, not a person with an editor.

### B7 — A recording shows what happened, refusals and all

**Every refusal that occurred is in the file, in the order it occurred. A recording with no refusals in it is a valid recording** (Kent, G9, 2026-09-20; decision record 0012 carries the dated amendment).

The rule used to be that every recording had to hold at least one `proposal_rejected`. It was written before anything had been run, and the first two full live runs settled it: **26 proposals, none refused.** Keeping the old rule would have meant one of two things, and both are the thing this product exists not to do — re-running until the model happened to err, or opening a file and writing a refusal into it by hand.

So the screen says what is true. When a recording holds no refusal, the refusal strip beside the map carries one line:

> **The rules refused nothing in this run.**

Not an empty panel, which reads as *not built*, and not a hidden panel, which reads as *nothing to see*. The wording is shared with the workbench chapter that draws the strip (`spec/workbench/streaming-growth.md`), so the live path and the replayed path say the same sentence.

**The validator is still visibly at work with no key**, and through a better door than a staged refusal: **a refused user edit.** Every intervention on a replayed map goes through `domain.validate` live (B3), so a reviewer who supposes something the map cannot carry — an arrow that touches neither end of a new claim, a branch that names a claim that is not there — sees every violation at once, with the validator's own sentences, on a machine with no key at all. That path is built in the join (stack 04a) and it is exercised by a person rather than waited for.

What is lost, said honestly: the reviewer no longer sees the model being refused on the happy path. What is gained is that nothing on screen was arranged.

### B8 — The prompt hash, and the check that uses it

`engine/prompt.py` hashes the prompt a generation runs against. The hash goes into the header and into the `receipt` event.

The build compares it. This is the mitigation record 0012 names for its own worst consequence: a recording goes stale **less visibly than a cassette** — no test breaks, the demo simply shows old wording — and the hash turns that silence into a red check.

The consequence, said plainly so nobody is surprised by it: **change a prompt and the `recordings` job goes red until the recordings are made again**, and only someone with a key can do that. That is the same bargain the cassettes struck, taken knowingly.

### B9 — The `recordings` build job

A sixth job beside `backend`, `frontend`, `types-fresh`, `docker` and `e2e`. **It has no key and needs none** (INV-13: continuous integration runs with no model API key, and the model boundary is exercised only through recorded responses). `engine/check_recordings.py` holds the checks, so `make record-demo` can run exactly the same ones before promoting a file. For every file in the recordings folder:

1. every line parses as JSON, and line 1 is a header with all its fields;
2. every line after the first is one of the eight events, with a payload that validates against it;
3. the sequence obeys the grammar in [`streaming.md`](streaming.md), ends in `done`, and holds no `beliefs_propagated`;
4. **every refusal the run produced is present, in order** — checked as fidelity to the run it came from, not as a quota. Zero is a legal count;
5. the header carries one recorded intervention, and its `Insert` validates;
6. the header's `prompt_hash` equals the current prompt's;
7. no two files carry the same `generation_started.hypothesis` after trimming, so the match in B2 can never be ambiguous;
8. the file's name is one of the four example names below.

**It passes on an empty folder**, so it is green from the commit that adds it and stays green until the first recording lands. `gitleaks`, the secret scanner that already runs before every commit, scans this folder too (NFR-8: no key in a committed file).

### B10 — The folders are settings

Which folder is read is **`KATALYST_RECORDINGS`**, a setting like everything else the environment says, read once by `katalyst.settings`. The default is `backend/recordings/`. *(The chapter first called it `RECORDINGS_DIR`. Renamed on 2026-09-20 for one reason: every other setting this program added is `KATALYST_`-prefixed, and an unprefixed `RECORDINGS_DIR` in a shared environment is a collision waiting to happen.)* **The writer obeys it as well as the reader** — a writer that ignored a setting the reader obeys wrote into the shipped folder from a test once, which is how that was found.

Two more of the same kind, and both exist so that a paid path can be exercised without paying. **`KATALYST_RUNS`** says where kept runs go; the default is `backend/.runs/`, and a test that starts the recorder points it somewhere throwaway, because that folder holds what real money bought. **`KATALYST_ANSWERER`** names an import path of a factory that builds the answerer, so the recorder can be started **as a program**, end to end, with no key and no network: two paid runs have been lost to bugs that exist only when a module is started rather than imported. A run answered that way is named as a fault and can never be promoted to a recording, so it cannot be mistaken for one.

It is a setting for one reason that is not configurability: **the tests and the browser's end-to-end run need to point at a small recording of their own.** The end-to-end test drives the real launchpad through the real stream with no key, and it should not depend on whichever of the four real recordings happens to be committed today, nor take a real recording's minute of paced playback. One setting gives it a fixture-sized file of its own, through exactly the same code path. Without it the choice is a test that is slow and coupled to real recordings, or a second loading path built only for tests — and a second path is the one that rots.

### B11 — The four examples, named

| File | The sentence, from `ASSIGNMENT.md` |
|---|---|
| `hormuz.jsonl` | *The Strait of Hormuz is going to open next week.* |
| `midterms.jsonl` | *Republicans win the House but Democrats take the Senate during the Midterm.* |
| `export-controls.jsonl` | *Models more capable than Fable get export restricted by the United States.* |
| `photonics.jsonl` | *Photonic chips get adopted faster than expected.* |

The four short names — `hormuz`, `midterms`, `export-controls`, `photonics` — are the launchpad's four cards, the four recording files, and the four eval case identifiers in [`evaluation.md`](evaluation.md). **One name per example, in all three places**, so a person reading a red build knows which card is broken without a lookup table. They name the example, never the map: the map inside carries a minted identifier (see the header above).

**Each example's one scripted insert is drafted live, by the ordinary machinery.** There is no special shape for it and no hand-written claim: when a recording is made, the scripted "…but X happens" sentence goes through the same route a reviewer's insert would — the starting-claim shape drafts the claim, the ordinary walk proposes its arrows — and the validated result is stored in the header. So the thing a keyless reviewer gets is a thing the live pipeline actually produced, on the day the recording was made, and not something anybody typed.

### B12 — The order the four are recorded in

Kent settled this on 2026-09-17 (G6), and it is an order chosen to spend the least money on a prompt that is still moving:

1. **All four run once through the structure-only eval as soon as the pipeline is green** — no recording written. A prompt that fails on the midterm example or the photonics one is found while it is cheap to fix. See [`evaluation.md`](evaluation.md).
2. **Hormuz is recorded as soon as the pipeline runs.** It is the map every chapter in this book works its examples on, so a bad prompt shows up against a map the reader already knows by heart — and it unblocks the browser test and the growing canvas.
3. **All four are recorded once the prompt is frozen**, at the end of the stream pull request.

Every re-record is money, and the first Hormuz generation is also a measurement: its true cost, thinking tokens and web searches included, goes into [`../../docs/measurements.md`](../../docs/measurements.md) before anything larger is run.

---

## INVARIANTS

Each statement holds for every input a named generator can produce, and each names the automated test that checks it.

The generator here is **a finite corpus, not a Hypothesis strategy**, and it has to be: a recording is made by a model, so nothing can conjure one. It is `recordings()` — every file under `backend/recordings/`, the same set the `recordings` build job walks. Tests live in `backend/tests/unit/test_replay.py` and `backend/tests/api/test_generate.py`.

**This chapter holds `INV-generation.22` through `INV-generation.27`**; the split across all five chapters is on the [landing page](README.md).

**INV-generation.22 — a replay emits the recording, line for line.** For all files from `recordings()`: the events a replayed generation emits are, name for name and payload for payload, the events in the file — except the rebuilt `receipt` and the recomputed `beliefs_propagated`, which the file does not hold. Test: `test_replay_stream_matches_recording`.

**INV-generation.23 — a replay gives the same world every time.** For all files from `recordings()`: two independent replays of one file produce worlds that serialize to identical bytes (NFR-2 — the same base map, branch and seed give byte-identical worlds). Test: `test_replay_is_byte_identical_across_runs`.

**INV-generation.24 — a replay says it is a replay.** For all files from `recordings()`: the receipt the replay emits carries `mode: "replay"`, `dollars` of zero, zero calls and zero tokens, and the header's `recording_date` and `prompt_hash`. Test: `test_replay_is_labelled_in_receipt`.

**INV-generation.25 — no recording holds a number the engine did not just compute.** For all files from `recordings()`: no line is a `beliefs_propagated` event, and no line anywhere in the file contains a serialized `World`. Checked by the `recordings` build job, step 3 above, and by `test_replay_stream_matches_recording`, which would have nothing to recompute if one were there.

**INV-generation.26 — a recording holds every refusal that happened, and no others.** For all files from `recordings()`: the `proposal_rejected` lines are exactly the refusals the run that made the file produced, in the order it produced them, each carrying every violation with the validator's own code and sentence. **The count may be zero** — that is a fact about the run, not a fault in the file (Kent, G9, 2026-09-20). Test: `test_a_recording_holds_every_refusal_that_happened`, and the `recordings` build job, step 4. *(Replaces `test_every_recording_shows_a_miss`, which demanded at least one and was never satisfied in 26 live proposals.)*

**INV-generation.27 — every recording matches the prompt that is shipping.** For all files from `recordings()`: the header's `prompt_hash` equals the hash `engine/prompt.py` computes for the current prompt. Test: `test_every_recording_carries_the_current_prompt_hash`, and the `recordings` build job, step 6.

**Two more, stated where the behaviour lives but checked here.** `test_generate_needs_no_key_in_replay_mode` — the whole stream route answers with nothing configured (INV-13). `test_intervention_on_replayed_world_needs_no_model` — *Suppose this is true*, *This happened*, *Change this push* and *My own number* resolve inside `domain/` on a replayed map.

---

## ANTI-PATTERNS

**1. Do not store a `World`, a likelihood or a range in a recording.** *Because* the moment propagation changes, the demo shows numbers the engine no longer produces, and nothing in the build notices. **Do** store the seed and let `domain/` recompute — which also makes replay and live agree by construction rather than by care.

**2. Do not arrange what a recording shows — in either direction.** *Because* re-running until the model finally errs, or quietly keeping only the runs that went beautifully, both make the screen a claim about how often something happens rather than a record of what did. **Do** keep every refusal the run produced, in order, keep none it did not, and say *"The rules refused nothing in this run."* when that is the truth. The validator is shown at work through a refused user edit, which a reviewer can trigger on purpose.

**3. Do not hand-edit a recording, ever — not to fix a typo, not to trim a long rationale.** *Because* an edited file is a piece of state that traces to no input, no rule and no source, and it is indistinguishable from a real one afterwards. **Do** treat `make record-demo` as the only writer, and re-record.

**4. Do not fake the interventions.** *Because* the multiverse is the product, and a recorded "what if" is a film the reviewer watches instead of a tool they steer. **Do** keep all five arithmetic edits live in `domain/`, and record only the one intervention that genuinely needs a model.

**5. Do not fall back from live to recorded when a live run fails.** *Because* the user would be shown a map that answers a question they did not ask, labelled as though it answered theirs. **Do** say the run failed, and keep the two paths apart.

**6. Do not reuse the test cassettes as the demo source.** *Because* cassettes are raw exchanges matched on the request, so a whitespace change in a prompt breaks the demo as a crash rather than as a stale date, they are shaped for assertions rather than for four runs worth watching, and the running app would have to load a test-only library. Record 0012 weighed this as option B and rejected it; **do** keep the two stores apart and pay the second re-recording chore knowingly.

**7. Do not let `instant` be a request field.** *Because* pacing is presentation, and a client that can ask for instant replay lets anyone skip the thing the recording exists to show. **Do** make it a setting, read once by `katalyst.settings`.

---

## Open questions

Raised 2026-09-17.

1. **Nobody has measured a recording yet.** Record 0012 budgets a few hundred kilobytes for four runs and says that past a megabyte we drop the stored reasoning and keep the proposals. Measure the first Hormuz file the day it is written, put the figure in [`../../docs/measurements.md`](../../docs/measurements.md), and decide then — not from an estimate.
2. **Where the identifier of a replayed map is resolved.** A finished replay hands the browser a map with an identifier, and every edit afterwards goes through the world routes, which look up stored examples. Today the answer is "the generations this process is holding, looked up after the stored examples" ([`streaming.md`](streaming.md)). Stack 05's SQLite store (FR-31) may want that lookup instead; revisit there.
3. **One recorded intervention per example, or two?** One is enough to prove the mechanism and it is what record 0012 settled. A second — an insert that the validator *refuses* — would show the reviewer the rejection path on an intervention as well as on a proposal, for the price of one more drafted claim per recording. Worth asking once the cost of a recording is measured.
4. **Whether a recording should carry the wall-clock gaps of the run that made it**, so pacing could follow the real rhythm — a fast proposal, then a slow one that searched — instead of a fixed delay. It would read more like the live product and cost four numbers per file. It would also make "pacing is cosmetic and changes nothing" a longer sentence than it is now, so it needs a reason better than *nicer*. Ask after somebody has watched a live run and a replay back to back.
