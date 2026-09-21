# Evaluation — recorded responses in the build, a scorecard out of band

## Purpose

Two questions get asked about a pipeline that calls a language model, and they want opposite things from a test suite.

**"Does the code still do what it did?"** must be answered on every push, in seconds, with no key, deterministically. So the model boundary is exercised through **cassettes** — real exchanges with the vendor, recorded once and replayed from disk from then on. An unrecorded call fails the test rather than dialling out. That is INV-13: continuous integration runs with no model API key, and the model boundary is exercised only through recorded responses.

**"Is the prompt any good?"** cannot be answered that way. It needs live calls, it costs money, and the same question asked twice gives two different maps. So it is answered **out of the build**, by hand, when we choose to pay: `make eval` runs the four example hypotheses live and prints a scorecard.

Keeping them apart is the whole design. The build never becomes slow, costly or flaky; the prompt stays measurable. This chapter settles both layers, names the scorecard's columns now so stack 07 has a baseline to compare against, and is explicit about the things we deliberately do not measure.

Layers 1, 4 and 5 — the property tests over the rules layer, the browser's tests, and the worked-example tests over the stored maps — are decision record 0008's and are not repeated here.

---

## Data model

### Layer 2 — the cassette layer

Already installed, already configured, and missing only the recordings themselves.

| Piece | Where | State |
|---|---|---|
| The recorder | `pytest-recording`, a wrapper over vcrpy | installed |
| Tests that use it | `backend/tests/boundary/`, each marked `@pytest.mark.vcr` | stack 04 |
| The recordings | `backend/tests/cassettes/`, committed | stack 04 |
| One directory for all of them | `vcr_cassette_dir` in `backend/tests/conftest.py` | done |
| Credentials stripped before writing | `filter_headers=["x-api-key", "authorization"]` in `vcr_config` | done |
| Replay only, never dial out | `--record-mode=none`, on in the build and in `make test` | done |
| Re-recording | `make record-cassettes`, against a real key | stack 04 |

A cassette is raw: the request that went out and the answer that came back. It proves the code still handles the shape the vendor actually sends — which a hand-written stand-in never can, because a stand-in encodes our beliefs about the client library rather than its behaviour, and it rots without saying so.

**`make record-cassettes` takes the same spending-cap argument as `make record-demo` and `make eval`** (*decided here*, on Kent's G5 principle): every command in this repository that can spend money takes the ceiling, checks the running receipt after every call — and between the rounds of research inside one, since a single call may now search twenty-five times — and stops with a plain sentence naming what was spent and what was got. Three commands, one rule, one argument name.

#### Every model call goes to the same URL — so the recorder must match on the body

This is the trap in this layer, and it fails silently.

The recorder's default is to match a request against a recording by **method and URL**. Every call this pipeline makes is a `POST` to the one messages endpoint. The pipeline expands up to three frontier claims at once (the concurrency cap in [`proposals.md`](proposals.md)), so three identical-looking requests are in flight together — and the recorder happily hands the second one the first one's answer. The test passes. It proves nothing, and the thing it fails to prove is the thing it exists for.

**The rule: `vcr_config` matches on the request body as well as the method and the URL.** One line in `backend/tests/conftest.py`, and the pipeline keeps the concurrency it actually ships with.

A boundary test may *additionally* expand one frontier claim at a time, and several should — not for correctness, but because a failure that names one call is a failure somebody can read. That is a convenience, not the guard.

The cost of matching on the body, said out loud: **a change of whitespace in a prompt invalidates every cassette.** That is exactly the fragility decision record 0012 weighed when it refused to reuse cassettes as the demo source, and it is why demo recordings are a separate store keyed on a prompt *hash* rather than on the prompt's exact bytes.

### Layer 3 — the eval harness

```
evals/
  cases/          one YAML file per case — four of them
  run.py          runs the cases, asserts structure, prints and writes the scorecard
  runs/           <date>.tsv, one row per case, committed
```

It sits **outside `backend/`** on purpose. It is not in the build, it calls a
model and it costs money, so putting it inside the package that ships would put a
thing that spends money one import away from the thing that serves requests. Its
own tests live in the suite all the same, under `backend/tests/unit/evals/`,
because they are the only thing that says the eight checks do what this chapter
says they do.

A case is small, because everything interesting about it is what the *model* does with it:

```yaml
id: hormuz
hypothesis: The Strait of Hormuz is going to open next week.
door: verify                  # explore | verify
target: Brent crude settles below $68 for five sessions.   # verify only
unreachable: false            # verify only; true on the one case that must say no
seed: …                       # written in the file, the same every run
```

The seed is written into the case file rather than drawn, so two runs differ only by the model. The fixture's convention — a seed that reads as the date the example is set on — carries over; the value is whatever the builder writes, and no chapter prints one it has not run.

### The four cases

They are the four hypotheses in `ASSIGNMENT.md`, and they are two of each door, because the assignment names two use cases and both have to work.

The case identifiers are the four example names — the same strings the launchpad's cards and the recording files use ([`replay.md`](replay.md)), so one name follows an example through all three.

| # | Case | Hypothesis | Door | Destination | What it is for |
|---|---|---|---|---|---|
| 1 | `hormuz` | *The Strait of Hormuz is going to open next week.* | **Verify** | *Brent crude settles below $68 for five sessions.* | The assignment's own first use case, word for word: does the opening logically lead to oil prices falling? A path should exist, and the eval asserts only that a graded path or an honest refusal comes back — never which path |
| 2 | `midterms` | *Republicans win the House but Democrats take the senate during the Midterm.* | **Explore** | — | A hypothesis in a different domain entirely, with no oil in it. It is here to catch a prompt that has quietly learned one subject |
| 3 | `export-controls` | *Models more capable than Fable get export restricted by the United States.* | **Verify** | *Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%.* | **Deliberately unreachable.** Export controls on frontier models have no mechanism that reaches Gulf shipping insurance. This case exists to prove that no code path invents a bridge (FR-7) |
| 4 | `photonics` | *Photonic chips get adopted faster than expected.* | **Explore** | — | A slow, diffuse, long-horizon hypothesis — the kind that tempts a model into vague claims. Every claim it produces still has to be checkable (INV-1) |

Case 3 is the load-bearing one. It is the answer to "how do you know it is not just making the chain up?": we ask it for a chain that cannot exist, and the honest answer — `no_path`, with the nearest claim it actually reached — is the one the harness demands. `test_verify_returns_no_path_rather_than_a_bridge` pins the same behaviour in the build, against a cassette.

### What the harness asserts — structure, never wording

Eight checks. Every one is a count or a shape; not one is a judgement about a sentence.

| # | Check | Why |
|---|---|---|
| 1 | No loops, once feedback arrows are set aside | INV-6 — a map that causes itself cannot be worked through |
| 2 | At least one `market` or `not_tradeable` ending | INV-9 — a chain ends in an instrument or an explicit statement that there is none, never in prose |
| 3 | A rationale on every arrow, and at least one source on every arrow marked `documented` | INV-2 — a link that claims evidence has to carry it |
| 4 | Resolution criteria, a named judge and a resolve-by date on every claim | INV-1 — a claim that cannot be checked is a vibe |
| 5 | A Verify case answers with a graded **path** or an explicit `no_path` naming the nearest claim reached; case 3 answers `no_path` | FR-7 — never a fabricated bridge |
| 6 | Non-zero cache reads on a run's second call | Decision record 0006 caches the system prompt. **A run whose cache reads stay at zero is a bug, not a slow day** |
| 7 | The run stopped for a named reason, and the receipt's dollars are under the run's cap | NFR-6 and Kent's G5 — a run that cannot say what it cost is a run nobody can budget |
| 8 | Every base rate on the finished map cites a page the research actually returned; `base_rates_dropped` counts the ones that did not, and each carries its note in the transcript | Kent's G7, 2026-09-20 — 8 of 10 claims in the first live run came with a recalled count like "12 of 15" and no source at all. A count with no page behind it is a number nobody computed |

Checks 1 to 4 are `domain.validate` run on the finished map, which is the same rules layer the pipeline already refuses proposals with. The harness adds nothing new to the rules; what it adds is the question *does the model's own output satisfy them, on a map nobody hand-wrote?*

**Five of the eight are about the map and three are about the run**, and the line matters when a run built no map at all: the five say plainly that there is nothing to read, and checks 5, 6 and 7 are still read — because "it could not say why it stopped" is worth knowing about a run that produced nothing.

**Four of the eight can only fail if our own accept step let something past.** A loop, an arrow with no mechanism, a claim with no test and a count of past cases with no page behind it are all refused at the moment the proposal lands, so none of them can reach a finished map through `expand` at all. Checks 1, 3, 4 and 8 are therefore not questions about the model; they are the same question `violations` and `asserted_links` ask — *and if one ever did?* Their tests feed the harness maps damaged on purpose, the same damaged maps the rules layer's own property tests use. The other four can fail on a real run, and are shown failing on one.

### The scorecard, named now

Kent settled on 2026-09-17 (S8) that FR-9's adversarial critique pass stays out of stack 04 — it roughly doubles the calls and its value cannot be read without something to compare it against. **So the scorecard's fields are named here, now, and the first run is the baseline stack 07 compares against.** The same applies to the ensemble that decision record 0015 said *not yet* to.

```python
class CaseScore(BaseModel):
    """One case's row. Every field is counted off the finished map or read off the
    receipt. Nothing here is a judgement about a sentence."""
    case: str                       # the case file's id
    door: Literal["explore", "verify"]

    claims: int                     # claims on the finished map
    links: int                      # arrows on it
    rejected: int                   # proposals the validator refused. May be zero (G9)
    endings: int                    # claims of kind market or not_tradeable (INV-9)
    deepest_layer: int              # how far the map got from the hypothesis

    base_rates_kept: int            # claims whose base rate cites a page research returned
    base_rates_dropped: int         # counts the model recalled with no such page, dropped
                                    # with a note in the transcript (G7, same rule as S1)

    documented_links: int           # arrows backed by an address the search tool returned
    argued_links: int               # arrows with a mechanism and no such address
    asserted_links: int             # arrows with neither. Zero, or an arrow was built
                                    # outside the accept step — see below

    verdict: Literal["reached", "no_path"] | None   # None on an Explore case
    path_length: int | None         # steps in the graded path; None when there is none

    stopped_for: str                # the Done.reason the stream ended with
    violations: int                 # what domain.validate still finds. Zero, or the run is a bug

    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    thinking_tokens: int            # the part of the written tokens that was thinking
    searches: int                   # web searches this run made — off the receipt,
                                    # which carries it because search is billed apart
                                    # from tokens
    searches_per_claim: float       # searches ÷ claims. The column G7's per-claim
                                    # research moves, read without doing arithmetic
    dollars: float
    seconds: float
    seconds_per_call: float         # seconds ÷ calls. Generation is sequential by
                                    # nature, so this is the number that sets how long
                                    # a person waits for a map


class Scorecard(BaseModel):
    """One run of the four cases, and what it cost."""
    run_at: datetime                # when the run started; two runs in a day are told apart by it
    model: str
    prompt_hash: str                # which prompt produced these numbers
    cases: tuple[CaseScore, ...]
    passed: int                     # cases where all eight checks held
    failed: int
```

**Which check did not hold is said on the terminal, not in the file.** The row carries the counts each check was read from, and a column saying "three of eight" would be a ninth number derived from the other twenty-five. So `run.py` prints the failed checks by number, by name and with the rules' own sentence, beneath the table, and exits non-zero. A reader comparing two committed scorecards is comparing counts; a person watching a run is told what went wrong.

**Why these columns and no others.** Each is either a count of something on the finished map or a number the receipt already holds. There is no column that requires an opinion, because a column that requires an opinion moves with whoever is holding it.

**Two columns are derived, and say so:** `searches_per_claim` and `seconds_per_call` are the two columns above them divided. They earn their place because they are what a person actually compares between two runs, and putting the division in one place stops two readers doing it two ways. They are never a *source*: if either disagrees with the columns it came from, it is the derived one that is wrong.

**One column is read from somewhere else, on purpose.** `thinking_tokens` is on `Outcome` and on the transcript's lines, and deliberately **not** on `Receipt`: the receipt's shape is settled and a number shown in two places is two numbers that eventually disagree. So the harness sums it off the transcript's own lines rather than off the bill. It matters because the first measured run spent **61% of its written tokens thinking**, so a prompt change that halves the thinking halves most of the bill and no other column would show it. It is the one column whose source is the working rather than the receipt, and that is written down here so nobody later "fixes" it by adding a field to `Receipt`.

**A scorecard compares runs of the same model** (Kent, G8, 2026-09-20). The model is one named setting, `KATALYST_MODEL`, defaulting to `claude-sonnet-5` for the prototype; nothing else in the pipeline knows which model it is, and the price table is per model. `Scorecard.model` is on every run for exactly this reason: **two rows from two models are not a comparison**, they are two measurements, and reading them as a before-and-after would credit a prompt change with a model change or the reverse. When a run deliberately crosses models — a final recording on a larger model, say — the comparison says so in words beside it.

**The one dated measurement this baseline starts from.** Hormuz, live, on `claude-opus-5` at default effort, 2026-09-17: **10 calls, 9 searches, $1.32, 10 minutes 54 seconds, 61% of written tokens thinking**, 10 claims, 9 arrows of which 8 `documented`, **0 refused**, stopped at `width_cap`. It is quoted here because it is the measurement that named these columns — the searches, the thinking share and the seconds per call were all invisible until somebody paid for a run and looked. No Sonnet number is quoted anywhere in this chapter, because none has been measured yet.

**Two columns are expected to read zero, and that is what they are for.** `violations` reads zero because the pipeline only ever mints what passed the rules. `asserted_links` reads zero because [`grounding.md`](grounding.md)'s rule leaves a generated arrow with only two possible words — `documented` when the search returned an address it cites, `argued` otherwise — and a rationale is required on every arrow (INV-2). A non-zero reading in either column is not a worse map; it is evidence that an arrow or a claim reached the map without going through the accept step, which is a bug of a different order.

**What a later stack is expected to move.** This is the point of naming them early — a change is worth its money only if it moves a column somebody named in advance.

| Candidate | Columns it should move | Columns it must not move |
|---|---|---|
| FR-9's critique pass (stack 07) | `argued_links` down, `documented_links` up, `rejected` up — and `calls`, `dollars`, `seconds` up, which is the price | `violations` and `asserted_links` (both already zero), `endings` (already at least one) |
| An ensemble (decision record 0015 — *not yet*) | **none of them.** An ensemble changes the *numbers on the chips*, and this scorecard deliberately scores none | everything here |

That second row is worth reading twice. An ensemble cannot be justified against this scorecard, because this scorecard does not measure the thing an ensemble changes. The thing that *would* measure it is the pastcast — running a chain on a resolved event and scoring the likelihoods — which is FR-30 and stack 07. Record 0015 says exactly that, and this table is the reason it can.

**There is deliberately no calibration column here**, because nothing in these four cases resolves. A column called "accuracy" that nothing resolved would be a number nobody computed.

### `make eval`

```
make eval                 # all four cases, for the cap written in code between them
make eval ONLY=hormuz     # one of them
make eval CAP=5           # the same, with a lower ceiling over the whole round
make eval EFFORT=medium   # the same, thinking less hard
```

The same three flags as `make record-demo`, meaning the same three things: one name, one ceiling, one effort. There is deliberately **no flag naming a model** — `KATALYST_MODEL` is what the bill is priced against and what the scorecard's own column reports, so a flag could name a third model and nobody would know which one the dollars belonged to.

* Runs **live**, against a real key. **`CAP` is the ceiling on the whole round, across every case it runs — not on each case** *(stated plainly here 2026-09-21; the harness gave every case the whole figure, so a default four-case round could spend four times it)*. The default is the **$15 hard stop written in code** (Kent, G5), and the argument can only lower it. One running total is carried from case to case: each is handed what is left of the ceiling, the running receipt is checked after every call and between the rounds of research inside one, and **a case there is nothing left for is never started**. The scorecard then says in one plain sentence what the round spent, which cases ran and which were left out — four silent columns would otherwise read as four cases with nothing to report — and the program exits non-zero, because a round that stopped short has scored nothing about what it never ran. `test_the_cap_bounds_the_round_and_not_each_case` starts the program with a stand-in whose every answer is dear and holds all of that.
* **Drives the one walk that already exists** — `engine/grow.py` followed by `engine/following.py`, the same loop the stream route and the recorder use. A harness with a walk of its own would eventually score a pipeline nobody ships.
* **Keeps every run under `backend/.runs/`, whatever it scores**, through the recorder's own keeper: every proposal with the seconds and the thinking tokens it took, the receipt, the reason it stopped and the map it built. A run that cost money and left nothing behind is an afternoon nobody can account for. Those files are not committed; the scorecard is.
* Prints the scorecard to the terminal, **turned on its side** — one line per field, one column per case — because a row per case is twenty-five columns wide and nobody reads that. A person comparing two runs reads down a column.
* Writes `evals/runs/<date>.tsv` — tab-separated, one header row, one row per case, `run_at` first, then `model` and `prompt_hash`, then the row. Those three read the same on every row rather than sitting once at the top, because a second run on the same day **appends** to that same file and a heading would then be a heading over somebody else's rows. Tab-separated because it opens in a spreadsheet and still diffs as text in git.
* Exits non-zero if any case failed a check, or if the round ran out of money before it reached every case, so it is usable from a script even though nothing schedules it.
* **Writes no row for a run it did not pay for.** A run answered by the stand-in named in `KATALYST_ANSWERER` prints its table, says in one line that it measured nothing, and writes no file — the same rule the recorder keeps for recordings, for the same reason: a file the repository commits as evidence has to be evidence.
* Is **committed**, results and all. It holds counts and dollars, no prompt text and no model output, so it can neither leak a key nor embarrass anybody. `gitleaks` scans it like everything else.
* **Only the coordinator runs it.** No sub-agent holds a key.
* **All four cases run once through it as soon as the pipeline is green** (Kent, G6) — structure only, no recording written — so a prompt that fails on the midterm or the photonics example is found while it is still cheap to fix. See [`replay.md`](replay.md).

### Evals are not in the build, on purpose

They cost money, they are not deterministic, and the same prompt scores slightly differently twice. Putting them in the build would mean a merge blocked by a model's mood. The build's check on the model boundary is the cassettes, and nothing else (INV-13).

What connects them to the process is a person: the pull-request checklist already carries *"prompt changed? cassettes re-recorded, `make eval` scorecard attached"*.

### There is no ensemble, and the word *agreement* stays free

Decision record 0015 (accepted by Kent, 2026-09-17) ships the range the model states, labelled *model interval, uncalibrated*, and says *not yet* to an ensemble. So there is no `engine/ensemble.py`, no run-to-run number anywhere in the code, and no screen that says *runs agree*.

One source-reading test keeps that door honest rather than trusting anyone to remember: `test_the_word_agreement_means_same_direction_and_nothing_else` reads our own source and fails if any field called `agreement` exists outside the diff's same-direction share. It is the same technique `test_beliefs_never_merged` already uses for INV-11 (model, user and market beliefs are never averaged), and it works for the same reason: an invariant that depends on good intentions is a wish.

*Agreement* means the share of versions of the map in which a change moved the same way, and nothing else. On screen that column is headed **same direction** (Kent, K10), which leaves the word itself free for the day a run-to-run number is earned.

### What is deliberately not measured

| Not measured | Why |
|---|---|
| **Wording, phrasing, how a rationale reads** | It is the fastest way to a test that fails when a prompt is improved |
| **Narrative quality, scored by a model** | A model grading a model's prose is a number nobody computed. It would move with the grader's mood rather than with the product, and it cannot be re-derived |
| **Whether a claim is true** | Nothing in these four cases has resolved. That is the pastcast's job (FR-30, stack 07) |
| **Whether the likelihoods are well calibrated** | Same reason. Stated ranges are known to run narrow — FermiEval measured a nominal 90% range covering 28% of outcomes (decision record 0014's research note; always quote the figure with its source) — which is why the chip says *uncalibrated* |
| **How long a generation takes, as a pass or fail** | `seconds` is recorded because it is useful; it is not a threshold, because model latency is not ours to control and a flaky timing check teaches people to ignore red |
| **Image snapshots of the canvas** | Decision record 0008's list. They fail on font rendering and teach nothing |
| **Coverage outside `domain/`** | Also 0008's. `engine/` and `api/` are orchestration and are lightly tested on purpose; the weight is where the claims are |

---

## Behaviour

### B1 — A pull request changes a prompt

1. The author edits the prompt. `make test` goes red: every cassette was matched on the request body, and the body changed.
2. `make record-cassettes` — coordinator, key loaded into that one command — and the boundary tests are green again.
3. The `recordings` job goes red: every recording's `prompt_hash` now disagrees with the current prompt's. `make record-demo` fixes it ([`replay.md`](replay.md)).
4. `make eval` is run once and the scorecard is pasted into the pull request, beside the previous one. The reviewer reads the columns, not the prose.

Three red checks and one attachment, all from one edit. That is the cost of prompt changes being a real change rather than a text tweak, and it is the cost this repository chose knowingly.

### B2 — The unreachable case earns its keep

`make eval` runs case 3. The map grows out from export controls on frontier models: compute supply, model availability abroad, downstream chip demand. None of it arrives at Gulf war-risk insurance premiums.

The stream's `verdict` reads `kind: "no_path"`, `path` empty, `nearest` naming the closest claim the map actually reached, `why` one plain sentence. The harness asserts `verdict == "no_path"` — and asserts **nothing about which claim `nearest` names**, because that is the model's answer and grading it would be grading wording.

If this case ever comes back `reached`, one of two things is true: a mechanism genuinely exists and somebody should read it, or a bridge was invented. Either one is worth the whole harness.

### B3 — A run that reaches its cap

Case 4 is a diffuse hypothesis and the map keeps growing. The running receipt reaches what is left of the round's ceiling. The generation stops, the stream's `done` carries `reason: "spend_cap"`, and the `Failed` event is **not** used — stopping on budget is a decision, not a fault.

The scorecard row is still written. `stopped_for` reads `spend_cap`, `dollars` reads what that case was allowed, and the structural checks still run against the partial map — a map that stopped early can still be free of loops, still carry resolution criteria on every claim, and still fail check 2 by having no ending yet. That failure is informative, and losing it by refusing to score the row would be the wrong trade.

**A case with nothing left to spend is a different thing and reads differently.** It is never started, so it has no row, no kept run and no checks — there is nothing to score. The sentence beneath the table names it, and that is the only place it appears. Writing an empty row for it would put a case on the scorecard that no model ever answered, which is the same mistake as writing a row for a run a stand-in answered.

---

## INVARIANTS

Each statement holds for every input a named generator can produce, and each names the check that enforces it.

The generators here are **finite corpora, not Hypothesis strategies**: `cassettes()` is every file under `backend/tests/cassettes/`, `cases()` is the four files under `evals/cases/`, and `sources()` is this repository's own Python under `backend/src/`. Nothing can conjure a model's answer, so nothing here pretends to.

**The invariants a proposal must satisfy are numbered in [`proposals.md`](proposals.md), and the ones a recording must satisfy in [`replay.md`](replay.md).** This chapter numbers only what the two testing layers themselves have to guarantee, and **holds `INV-generation.28` through `INV-generation.32`**; the split across all five chapters is on the [landing page](README.md).

**INV-generation.28 — no recorded exchange contains a key.** For all files from `cassettes()`: no header, body or URL in the file contains the value of `ANTHROPIC_API_KEY` or anything matching a key's shape. Enforced twice, because this one is unrecoverable if it fails: `filter_headers` strips the credentials before a file is ever written, and `gitleaks` scans the directory before every commit (NFR-8). Test: `test_no_cassette_contains_a_key`.

**INV-generation.29 — the build never calls anything.** For every test in `backend/tests/boundary/`: with `--record-mode=none` and no key in the environment, a call with no matching recording fails the test rather than reaching the network — the recorder raises rather than dialling out. Checked by the `backend` job itself, which is given no key and needs none (INV-13).

**INV-generation.30 — two calls in flight are never handed each other's answers.** For all files from `cassettes()` recorded from a run that expanded more than one frontier claim at once: each request is matched on its body as well as its method and URL, so a recording replays only to the request that produced it. Enforced by `vcr_config`'s `match_on` in `backend/tests/conftest.py`; a boundary test that wants a legible failure may also expand one claim at a time.

**INV-generation.31 — one word, one meaning.** For all modules from `sources()`: the only field named `agreement` is the diff's same-direction share, and no user-facing string contains the words *runs agree*. Test: `test_the_word_agreement_means_same_direction_and_nothing_else`, which reads the source rather than trusting anybody to remember.

**INV-generation.32 — a finished map from the model is a valid map.** For all cases from `cases()`: `domain.validate` on the map the run finished with returns an empty list, which is the scorecard's `violations` column reading zero. **Checked out of the build, by `make eval`**, and that is deliberate: it needs live calls, and a flaky check in the build is a check people learn to ignore. The in-build counterpart is the boundary layer, where the same rules layer refuses the same recorded proposals.

---

## ANTI-PATTERNS

**1. Do not assert on wording.** *Because* the test then fails when somebody improves the prompt, and passes when somebody makes it worse in the same words. **Do** assert structure: counts, shapes, the presence of a source, the two legal answers to a Verify case.

**2. Do not have a model grade the output.** *Because* the score is then a number nobody computed, it cannot be re-derived, and it moves with the grader rather than with the product — which is the one thing Kent vetoes on sight. **Do** count what is on the map, and leave quality to a human reading a diff of two scorecards.

**3. Do not put the evals in the build.** *Because* they cost money on every push, need a secret in the build, and are not deterministic — so a merge would be blocked by a model's mood, and INV-13 would be gone. **Do** run them by hand, attach the scorecard to the pull request, and keep the build on cassettes.

**4. Do not match cassettes on method and URL alone.** *Because* every call goes to one endpoint and up to three are in flight at once, so the recorder hands the second call the first call's answer and the test passes while proving nothing. **Do** match on the request body.

**5. Do not write a hand-written stand-in for the client library.** *Because* it encodes our assumptions about the vendor rather than the vendor's behaviour, and it rots without ever failing. **Do** record real exchanges.

**6. Do not add a scorecard column that needs an opinion.** *Because* the baseline stack 07 compares against is only worth having if the same run scores the same twice. **Do** add a column only when it is a count off the map or a number off the receipt.

**7. Do not score an ensemble against this scorecard.** *Because* none of these columns measures what an ensemble changes — the numbers on the chips — so a comparison would come back flat and be read as evidence either way. **Do** wait for the pastcast (FR-30), which scores likelihoods against outcomes that actually resolved.

---

## Open questions

Raised 2026-09-17.

1. **The pastcast is stack 07, and it is the missing half of this chapter.** FR-30 wants a chain run on a resolved 2024–25 event against a date-frozen corpus, scored with a Brier score — the standard accuracy score for probability forecasts, where lower is better — and shown *including when it is bad*. It needs three things this stack does not have: resolved events with dates, a way to keep the search tool from seeing anything after the freeze date, and a calibration column on the scorecard above. Decision record 0015 names it as the measurement that would reopen the ensemble question, and S8 names it as the measurement that would justify a critique pass. **Both reopenings depend on it, so it is the first thing stack 07 should cost.**
2. **How many eval rounds the stack's budget actually buys.** Kent's G5 sizes the stack at about $500 and a run at no more than $15, and estimates cassettes, four recordings, two or three re-record rounds and about five eval rounds. Nothing has been measured. The first Hormuz generation's true cost — thinking tokens and web searches included — goes into [`../../docs/measurements.md`](../../docs/measurements.md), and this estimate should be redone against it before a second full round is run.
3. **Should a case carry an expected claim count, as a loose band?** It would catch a prompt that has quietly started producing three-claim maps. It would also be the first number in this harness that somebody typed rather than measured, so it can only come *after* several runs have been scored — a band read off the baseline, dated, and re-read when the prompt changes. Not before.
4. **`evals/` is outside what the build lints and type-checks.** The `backend` job runs `ruff` and `mypy` from `backend/`, so it covers the harness's *tests* and not the harness. They are kept clean by hand today, which is a promise rather than a check. The cheapest fix is one more path on those two commands; it was left out of the pull request that built the harness because the commands belong to the build's own files rather than to this chapter's.
5. **Four cases is the assignment's four, and the assignment's four are all the coverage there is.** They share a shape: a single near-term event with financial consequences. A hypothesis with no plausible market at the end of it — one that *should* produce a `not_tradeable` ending — is not among them, and check 2 would pass either way. Worth one more case when there is budget for a fifth.
