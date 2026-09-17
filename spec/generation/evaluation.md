# Evaluation — recorded answers in the build, a scorecard out of band

## Purpose

Two questions get asked about a pipeline that calls a language model, and they want opposite things from a test suite.

**"Does the code still do what it did?"** must be answered on every push, in seconds, with no key, deterministically. So the model boundary is exercised through **cassettes** — real exchanges with the vendor, recorded once and replayed from disk from then on. An unrecorded call fails the test rather than dialling out. That is INV-13: continuous integration runs with no model key.

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

**`make record-cassettes` takes the same spending-cap argument as `make record-demo` and `make eval`** (*decided here*, on Kent's G5 principle): every command in this repository that can spend money takes the ceiling, checks the running receipt after every call, and stops with a plain sentence naming what was spent and what was got. Three commands, one rule, one argument name.

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

| # | Hypothesis | Door | Destination | What it is for |
|---|---|---|---|---|
| 1 | *The Strait of Hormuz is going to open next week.* | **Verify** | *Brent crude settles below $68 for five sessions.* | The assignment's own first use case, word for word: does the opening logically lead to oil prices falling? A route should exist, and the eval asserts only that a graded route or an honest refusal comes back — never which route |
| 2 | *Republicans win the House but Democrats take the Senate during the Midterm.* | **Explore** | — | A hypothesis in a different domain entirely, with no oil in it. It is here to catch a prompt that has quietly learned one subject |
| 3 | *Models more capable than Fable get export restricted by the United States.* | **Verify** | *Lloyd's war-risk insurance premium for Gulf transits falls below 0.4%.* | **Deliberately unreachable.** Export controls on frontier models have no mechanism that reaches Gulf shipping insurance. This case exists to prove that no code path invents a bridge (FR-7) |
| 4 | *Photonic chips get adopted faster than expected.* | **Explore** | — | A slow, diffuse, long-horizon hypothesis — the kind that tempts a model into vague claims. Every claim it produces still has to be checkable (INV-1) |

Case 3 is the load-bearing one. It is the answer to "how do you know it is not just making the chain up?": we ask it for a chain that cannot exist, and the honest answer — `no_path`, with the nearest claim it actually reached — is the one the harness demands. `test_verify_returns_no_path_rather_than_a_bridge` pins the same behaviour in the build, against a cassette.

### What the harness asserts — structure, never wording

Seven checks. Every one is a count or a shape; not one is a judgement about a sentence.

| # | Check | Why |
|---|---|---|
| 1 | No loops, once feedback arrows are set aside | INV-6 — a map that causes itself cannot be worked through |
| 2 | At least one `market` or `not_tradeable` ending | INV-9 — a chain ends in an instrument or an explicit statement that there is none, never in prose |
| 3 | A rationale on every arrow, and at least one source on every arrow marked `documented` | INV-2 — a link that claims evidence has to carry it |
| 4 | Resolution criteria, a named judge and a resolve-by date on every claim | INV-1 — a claim that cannot be checked is a vibe |
| 5 | A Verify case answers with a graded route **or** an explicit `no_path` naming the nearest claim reached; case 3 answers `no_path` | FR-7 — never a fabricated bridge |
| 6 | Non-zero cache reads on a run's second call | Decision record 0006 caches the system prompt. **A run whose cache reads stay at zero is a bug, not a slow day** |
| 7 | The run stopped for a named reason, and the receipt's dollars are under the run's cap | NFR-6 and Kent's G5 — a run that cannot say what it cost is a run nobody can budget |

Checks 1 to 4 are `domain.validate` run on the finished map, which is the same rules layer the pipeline already refuses proposals with. The harness adds nothing new to the rules; what it adds is the question *does the model's own output satisfy them, on a map nobody hand-wrote?*

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
    rejected: int                   # proposals the validator refused
    endings: int                    # claims of kind market or not_tradeable (INV-9)
    deepest_layer: int              # how far the map got from the hypothesis

    documented_links: int           # arrows backed by an address the search tool returned
    argued_links: int               # arrows with a mechanism and no such address
    asserted_links: int             # arrows with neither. Zero, or an arrow was built
                                    # outside the accept step — see below

    verdict: Literal["reached", "no_path"] | None   # None on an Explore case
    path_length: int | None         # steps in the graded route; None when there is none

    stopped_for: str                # the Done.reason the stream ended with
    violations: int                 # what domain.validate still finds. Zero, or the run is a bug

    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    searches: int                   # web searches this run made
    dollars: float
    seconds: float


class Scorecard(BaseModel):
    """One run of the four cases, and what it cost."""
    run_at: datetime                # when the run started; two runs in a day are told apart by it
    model: str
    prompt_hash: str                # which prompt produced these numbers
    cases: tuple[CaseScore, ...]
    passed: int                     # cases where all seven checks held
    failed: int
```

**Why these columns and no others.** Each is either a count of something on the finished map or a number the receipt already holds. There is no column that requires an opinion, because a column that requires an opinion moves with whoever is holding it.

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
make eval               # all four cases, at the cap written in code
make eval CAP=…         # the same, with a lower ceiling
```

* Runs **live**, against a real key. `CAP` is the run's spending ceiling in dollars; the default is the **$15 hard stop written in code** (Kent, G5), and the argument can only lower it. The running receipt is checked after every call.
* Prints the scorecard to the terminal, as a table a person reads.
* Writes `evals/runs/<date>.tsv` — tab-separated, one header row, one row per case, `run_at` first. A second run on the same day **appends**; the rows are told apart by `run_at` and by `prompt_hash`. Tab-separated because it opens in a spreadsheet and still diffs as text in git.
* Exits non-zero if any case failed a check, so it is usable from a script even though nothing schedules it.
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

Case 4 is a diffuse hypothesis and the map keeps growing. The running receipt reaches the ceiling. The generation stops, the stream's `done` carries `reason: "spend_cap"`, and the `Failed` event is **not** used — stopping on budget is a decision, not a fault.

The scorecard row is still written. `stopped_for` reads `spend_cap`, `dollars` reads the cap, and the structural checks still run against the partial map — a map that stopped early can still be free of loops, still carry resolution criteria on every claim, and still fail check 2 by having no ending yet. That failure is informative, and losing it by refusing to score the row would be the wrong trade.

---

## INVARIANTS

Each statement holds for every input a named generator can produce, and each names the check that enforces it.

The generators here are **finite corpora, not Hypothesis strategies**: `cassettes()` is every file under `backend/tests/cassettes/`, `cases()` is the four files under `evals/cases/`, and `sources()` is this repository's own Python under `backend/src/`. Nothing can conjure a model's answer, so nothing here pretends to.

**The invariants a proposal must satisfy are numbered in [`proposals.md`](proposals.md), and the ones a recording must satisfy in [`replay.md`](replay.md).** This chapter numbers only what the two testing layers themselves have to guarantee, and **holds `INV-generation.26` through `INV-generation.30`**; the split across all five chapters is on the [landing page](README.md).

**INV-generation.26 — no recorded exchange contains a key.** For all files from `cassettes()`: no header, body or URL in the file contains the value of `ANTHROPIC_API_KEY` or anything matching a key's shape. Enforced twice, because this one is unrecoverable if it fails: `filter_headers` strips the credentials before a file is ever written, and `gitleaks` scans the directory before every commit (NFR-8). Test: `test_no_cassette_contains_a_key`.

**INV-generation.27 — the build never calls anything.** For every test in `backend/tests/boundary/`: with `--record-mode=none` and no key in the environment, a call with no matching recording fails the test rather than reaching the network — the recorder raises rather than dialling out. Checked by the `backend` job itself, which is given no key and needs none (INV-13).

**INV-generation.28 — two calls in flight are never handed each other's answers.** For all files from `cassettes()` recorded from a run that expanded more than one frontier claim at once: each request is matched on its body as well as its method and URL, so a recording replays only to the request that produced it. Enforced by `vcr_config`'s `match_on` in `backend/tests/conftest.py`; a boundary test that wants a legible failure may also expand one claim at a time.

**INV-generation.29 — one word, one meaning.** For all modules from `sources()`: the only field named `agreement` is the diff's same-direction share, and no user-facing string contains the words *runs agree*. Test: `test_the_word_agreement_means_same_direction_and_nothing_else`, which reads the source rather than trusting anybody to remember.

**INV-generation.30 — a finished map from the model is a valid map.** For all cases from `cases()`: `domain.validate` on the map the run finished with returns an empty list, which is the scorecard's `violations` column reading zero. **Checked out of the build, by `make eval`**, and that is deliberate: it needs live calls, and a flaky check in the build is a check people learn to ignore. The in-build counterpart is the boundary layer, where the same rules layer refuses the same recorded proposals.

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
2. **How many eval rounds the stack's budget actually buys.** Kent's G5 sizes the stack at about $500 and a run at no more than $15, and estimates cassettes, four recordings, two or three re-record rounds and about five eval rounds. Nothing has been measured. The first Hormuz generation's true cost — thinking tokens and web searches included — goes into `STATUS.md`, and this estimate should be redone against it before a second full round is run.
3. **Should a case carry an expected claim count, as a loose band?** It would catch a prompt that has quietly started producing three-claim maps. It would also be the first number in this harness that somebody typed rather than measured, so it can only come *after* several runs have been scored — a band read off the baseline, dated, and re-read when the prompt changes. Not before.
4. **Four cases is the assignment's four, and the assignment's four are all the coverage there is.** They share a shape: a single near-term event with financial consequences. A hypothesis with no plausible market at the end of it — one that *should* produce a `not_tradeable` ending — is not among them, and check 2 would pass either way. Worth one more case when there is budget for a fifth.
