---
# ADR-0017: A claim is an event or a state; nothing retracts itself
status: proposed
date: 2026-09-21
decision-makers: Kent Gang
consulted:
  - the stack-05 states spike, both rounds, 2026-09-21 — what a state is in the arithmetic, what it costs, and the re-measurement under the additive rate; scripts and logs kept locally under `plans/analysis/scripts/spike-05/states/` and `…/states/round2/`
  - the adversarial pass over the 2026-09-21 design (M3, which proved `sustain` does not survive proposed record 0016)
  - ADR-0005 (which calls trigger-versus-sustain the best idea in the brainstorm); ADR-0014 (whose decision A this reverses)
informed: agents in `backend/src/katalyst/domain`, on the canvas, and on stack 05's shape freeze
supersedes: none
superseded-by: none
spec-impact: spec/graph/proposition.md, spec/graph/link.md, spec/graph/validity.md, spec/multiverse/propagation.md (B3, B4), spec/multiverse/interventions.md, spec/vocabulary.md, spec/workbench/tiles-ports-wires.md, PRODUCT_REQUIREMENTS.md UX-14 and FR-15
---

# ADR-0017: A claim is an event or a state; nothing retracts itself

> **`proposed`.** It depends on proposed record 0016 being accepted — it exists because that record deletes something. Its measurements were re-run under that record's **additive** rate and the middle-of-the-slice convention, so no caveat about a superseded rate model remains; every number below is the re-run's. Kent has answered both questions it left open (R26, R27).

> **In short.** A claim is an **event** — it happens once and stays happened — or a **state**, which holds over a stretch of time and can stop. A `sustain` arrow may leave only a state, and **automatic retraction is deleted** (Kent, R2). The in-between `kind` is renamed `event` → **`step`** (R21), so the four kinds read `hypothesis · step · market · not_tradeable`, and the new field is `persistence: event | state`.
>
> **On screen.** *"Hormuz opens, then Iran is struck"* leaves **both events at `1.0000`**. What falls is the state: `.6219 → .1661`, taking the ending from `.2991` to `.2613`. The *Retracted* badge and two day-states go.
>
> **What it costs.** Mostly deletion — about **65** lines of server code, **85** of browser code and eleven named tests. A state costs **nothing** in the exact solve (the same 64, 150 and **2 ms** as a map with no state) but its on–off joint is the one expensive piece: on a twenty-claim map five states take the forward pass from `224.4` to **`508.9 ms`** at 2 000 versions, which is what puts record 0016's hard case over its time target. About **1.3 sessions**, riding the one shape freeze with the re-recording.
>
> **Open for Kent.** Nothing. An arrow that ends a state is asked for **the chance it stops** (R26), and **`persistence` is always required** — a map without it is refused by name (R27).

## Context and Problem Statement

Record 0005 gives every arrow a `mode`, the pair it calls *"the best idea in the brainstorm"*. A **`trigger`** arrow is a domino: it fires when its cause becomes true, and standing the cause back up later does not undo it. A **`sustain`** arrow is a desk holding an apple: the effect holds only while the cause holds.

Proposed record 0016 deletes the distinction as a side effect. Under that record a claim's number is *the chance it has happened by day t* — a **first passage** probability, the first day something crosses a line — and what has happened never un-happens. The moment that is true, the quantity a `sustain` arrow reads (its cause's truth on each day) and the one a `trigger` arrow reads (whether its cause has fired) become the same array. **Measured:** not close, the same number — `0.442471` against `0.442471` — so `mode` becomes dead data fully determined by `shape` (adversarial pass, `attack3.py` §B; re-run 2026-09-21 by this record's author).

The only mechanism that can make a true claim untrue is **automatic retraction** — record 0014's rule, which ends a supposition on a calendar read off the map's shape. That rule is itself one of the three defects record 0016 exists to fix, so it cannot be what saves `sustain`. **And the brief's own sentence is modelled wrong:** *"The Strait of Hormuz opened but Iran was struck the next day"* asks for a world in which **both things happened**, where today the strike retracts the opening, so Monday's event un-happens because of Tuesday's news.

## Decision Drivers

* **Record 0005's best idea, and Kent's instruction to keep it** — whatever ships either keeps the distinction or says plainly that it is gone, and the brief's own sentence must come out with both events standing.
* **The traceability veto** (Kent): a supposition deleted by a cause nobody believes is exactly the untraceable state he vetoes.
* **Pay once**: everything that changes what we ask the model lands in one freeze. And the canvas is settling down, so a change here earns its place only if it is mostly *deletion*.

## Considered Options

Three, from which **Kent chose (i)** on 2026-09-21 (dated decisions note, row R2):

* **(i) Events and states.** A `sustain` arrow may leave only a state; automatic retraction is deleted.
* **(ii) Events only; a sustained push is two arrows** — one from the event that starts it, an inhibiting arrow from the event that ends it. No new field. Cheapest, and `mode` and the word *sustain* leave the vocabulary; the reader must know to draw two arrows for one mechanism, and the six recorded sentences below show the model already writing states it could not then say.
* **(iii) Keep today's snapshot meaning for states only** — two meanings of a number on one map.

## Decision Outcome

Chosen option: **(i)**, because it is the only one of the three under which the brief's own example sentence comes out right — both events stand, and what falls is the thing everything downstream depended on.

### What a state is

A claim is an **event** — permanent once it happens, *the strait reopens* — or a **state** — it holds over an interval and can stop, *the strait stays open to commercial transit through 1 November*. **An event has one time, the day it happens; a state has two, the day it switches on and the day it switches off.** Both come out of the same arithmetic: a rate, integrated over the claim's own window. A state's **on-rate** is bent by its causes exactly as an event's rate is; its **off-rate starts at zero** and is the sum of its ending causes' pushes, so with nothing on the map that can end it, it does not end — and **no second number is elicited**. Measured: a state with no ending cause is identical to the same claim written as an event, to **`1.4 × 10⁻¹⁶`** (`round2/check2.py`). *(How each rate is calibrated, step by step, is written out for the `propagation.md` rewrite in the owed-edits note.)*

**Which rate an arrow bends: the sign decides, and no field is added.** An arrow whose elicited number is *above* the claim's own number **helps** and bends the on-rate; one *below* it **ends** and bends the off-rate. The alternative sends it to the on-rate instead, scaled down while the cause is on, which is record 0016's rule for an arrow that holds a claim back. On the map where the lane is already open, with the strike landing on day 20 (`round2/hormuz2.py` §D):

| the strike arrow bends | the state, no strike | after the strike | the fall |
|---|---|---|---|
| **the off-rate (chosen)** | `.8309` | **`.0577`** | **`−.7732`** |
| the on-rate, by scaling it | `.9317` | `.7475` | `−.1842` |

Scaling a rate that has already done its work leaves almost nothing to scale: a strike that plainly closes the strait would move the claim everything hangs on by **18 points instead of 77** — the same shape as the defect this record exists to remove. **What the rule gives up:** a cause can make a state *start*, never make it *last longer*. Nothing in the Hormuz story wants to say that; the spike prices the alternative at about a session if Kent ever does.

**One interval.** A state switches on at most once and off at most once; a thing that comes back is a second claim.

**What the number means: the chance it is holding on its deadline** — on by the deadline, and not yet off. The tile reads *"17% — the chance this still holds on 1 November"* where an event's reads *"35% — the chance this happens by 1 November"*; two words differ, and under Kent's R17 the sentence is composed in the browser, so it is a one-file change. Three readings were rejected: *ever held*, which cannot fall; *holds through its whole window*, almost never true; and *share of the window it held*, which is not a probability.

**What the two modes now mean.** A `trigger` arrow reads its source's **on time alone** and keeps pushing afterwards — the domino. A `sustain` arrow reads its source's **whole interval**, from the on time plus its lag until the off time, dead after — the apple on the desk. Measured on one map, changing nothing but the mode: the ending reads `.3182` under `trigger` and **`.3026`** under `sustain`, where before this record the two were identical to six decimal places (`round2/check2.py` §C).

**The two verbs.** *Suppose this is true* pins a state **on from its date and never off**; *This happened*, read on a date, says it **was holding on that date**. Both are the surgery an event already gets — pin the time, cut the incoming arrows.

**The per-day series.** A state's series is the chance it is **holding** on day *t*: it rises and it can fall, where an event's can only rise. `World.series` keeps its type and carries two meanings, told apart by the claim's persistence, which answers the adversarial pass's M4. `DeltaRow.peak_delta` and `at_day`, whose rationale is *"shows up for a fortnight and then unwinds"*, describe **states** and are restated for events.

### How an ending arrow is asked about — Kent's decision R26

**An arrow that *ends* a state is asked for the chance it stops.** Every other arrow keeps R6's wording — *the chance the target happens by its deadline if this cause happens at the start of the window and no other cause does* — and the change is one sentence in the one shape freeze, amending record 0006 there. R6's wording, applied to an ending arrow, asks for a number about the target while stripping away the very cause that turned the target on, and the answer is not monotone. Sweeping only the strike arrow's half-life (`round2/hormuz2.py` §B):

| the strike arrow | R6's wording as it stands | asked as *the chance it stops* |
|---|---|---|
| step, no decay | state `.1613` | state `.3994` |
| impulse, half-life 2 | state `.4929` *(the fit gave up)* | state `.6941` |
| impulse, half-life 6 | state `.1037` | state `.6547` |
| impulse, half-life 20 | state `.1375` | state `.4993` |

Under R6's wording the same elicited number gives `.4929, .1037, .1375, .1613` as the spike lengthens, so a six-day spike bites harder than a permanent step. **The additive rate repaired half of this:** the fit giving up fell from **14.8%** of ending arrows to **1.3%** (108 of 8 082, `round2/sweep2.py`), the additive off-rate having no ceiling where the multiplicative one did. What did not move is the question itself. *The chance it stops* is **closed form** — `−ln(1 − it stops) / (its shape added up over the window)`, the helping arrow's own formula, reproducing the old bisection to `8.0 × 10⁻¹⁶` — so on the named and hard families it fits **2 106 arrows with 0 root finds and 0 clamps**, where R6's wording needs **2 106 root finds and clamps 54** (2.6%). Accuracy is the same either way, so the question was what a reader can honestly answer. **The bisection is deleted with it.**

### How a state is carried, and what it costs

The forward timing pass carries a state's full joint over its two times; the small table the exact solve runs on carries **one bit**, *holding on its deadline* — the same question the tile asks. **The exact solve does not move at all:** on a twenty-claim map with five states the largest factor, the entries built and the elimination time are **64, 150 and 2 ms**, identical to the same maps with no state. **And a state is no less accurate than an event** — over 82 map skeletons run once with states and once with every claim an event, the worst gap is `.00835` with the states on against `.00794` with them off, both at 99.8% of numbers within `.005` (`round2/sweep2.py`).

**The on–off joint is the one expensive piece, and only a `sustain` child needs it:** five states take the twenty-claim forward pass from `224.4` to **`508.9 ms`** at 2 000 versions and from `26.9` to `55.7 ms` at 200 (`round2/cost2.py`, `cost2.log`). **That is what puts record 0016's hard case over its time target**, and the speed-up that skips this joint for a state no `sustain` arrow leaves is built into that record's core pull request.

*How a state is carried, step by step and at what accuracy, is held for the `spec/multiverse/propagation.md` rewrite — which cannot be edited until stack 04 has landed — in §11 of the owed-edits note.*

### The Hormuz strike, worked

**Every number fed in is an illustrative input** — no prior, arrow number, lag or half-life below was measured, exactly as the committed fixture says of its own — and every number printed is computed from them (`round2/hormuz2.py`, `hormuz2.log`; 30 slices over 60 days, day 60 being 1 November).

| | base | *Suppose the strait reopens* | *…and Iran is struck* | move |
|---|---|---|---|---|
| the strait reopens (event) | `.3500` | **`1.0000`** | **`1.0000`** | `+.0000` |
| Iran is struck (event) | `.1800` | `.1800` | **`1.0000`** | `+.8200` |
| the strait stays open through 1 Nov (**state**) | `.2354` | `.6219` | **`.1661`** | **`−.4558`** |
| Brent settles below the threshold (the ending) | `.2718` | `.2991` | **`.2613`** | `−.0377` |

**Both events stand at `1.0000`** — neither withdrawn, retracted nor dated out — and **no retraction machinery is involved anywhere**: nothing consults a calendar and nothing un-trues a claim. **The third defect cannot recur:** on the same map, inserting the claim nobody believes — prior `.001`, a weak arrow pushing against a supposed claim — leaves the supposed claim at **`1.0000` on every one of the thirty days**, written as an event and as a state alike, because a *Suppose* pins the claim's time and cuts its incoming arrows, so there is no calendar to get wrong.

*The worked series day by day, and the four claims it runs on, are held for the `spec/multiverse/propagation.md` rewrite — which cannot be edited until stack 04 has landed — in §11 of the owed-edits note.*

### What is deleted

The `Retracted · date · by "…"` badge — `spec/vocabulary.md` calls it the one *derived* badge, the only one no button produces — and its entry. Two of the four day-states: `SeriesState` is `sampled · supposed · withdrawn · pushed` (`propagation.py:90`) and the last two go. **Retraction by calendar, entirely**: `_opposing`, the undermining block inside `_spells_on`, `_retractions`, `_states`, the `Retraction` model on the wire, the sensitivity sweep's rebuild of which edit introduced a claim (`diff.py:436-441`), the browser's client-side retraction detector (`graph/diff/badges.ts`) and the badge's two readers. **About 65 executable lines of server code, 85 of browser code, and eleven named tests** — the spike's read-only inventory cites file and line for each. And **UX-14, and FR-15's retraction clause** (*"`sustain` links retract, `trigger` links do not"*, P0), whose replacement wording is in the owed-edits note travelling with this record.

**One caution, found by reading rather than assumed:** `_Spell.undermined_on` is read in **three** places, the third being `_fixed_days` (`propagation.py:1566`) — the arithmetic that decides when a supposed value stops being held. This touches the core loop, not only a label.

**This reverses decision A of record 0014** — *"it **stops holding** on the day the **cause** of the first live arrow pushing against it becomes true"* — with its three-state table and its two confirmation tests. **What stands:** a supposition is a hard fact in every world *while it holds*, and the tile shows **Supposed · date**, never a number. What changes is that nothing ends it but another edit. **It also amends ADR-0005's `mode` table**, whose two modes are restated as *which of the source's times the arrow reads*.

### The two new rules, the rename, and the freeze they ride in

**A `sustain` arrow may only leave a claim whose `persistence` is `state`** — a twenty-first violation code, named **`sustain_without_state`** because six of the twenty existing codes are already `<subject>_without_<required thing>` and all twenty are article-free (the spike proposed `sustain_from_an_event`). A refusal with a sentence, never a repair.

**And `persistence` is always required** (Kent, R27): no default, every claim says which kind of truth it is, and a map without it is refused by name — a twenty-second code, **`claim_without_persistence`**, in the same article-free pattern. Reject, never repair: a default of `event` would mean the first hand-written state someone forgets to mark never stops holding, silently. It costs one line in each of the seven Hormuz claims and in the property-test builders.

The spike considered six further rules and added none; two are worth naming. A state with nothing that can end it is **not** a fault — it behaves exactly like an event, measured — but is a good candidate for a warning. And an arrow that ends a state may point at an event, because an arrow pushing an event down is already legal.

**The in-between kind is renamed `step` (Kent, R21)**, because `kind: event, persistence: state` — the commonest claim of all, a step in the middle of a chain that can stop holding — parses as a contradiction until you know the rule. **The four kinds become `hypothesis · step · market · not_tradeable`, and `persistence: event | state` keeps Kent's words**; he rejected `middle` as unintuitive. An arrow's `shape` also has a value `step`, but that is a field on an arrow and this one is on a claim, so no claim reads as a contradiction. The rename is **46 lines of code and 21 of spec and records** where `kind` and the word *event* meet (re-measured after stack 04 landed; it was 42 and 17 before), plus the recording, the fixture, the generated browser types and the validator's messages. *Everywhere below that describes today's code or quotes a file that exists, the word is still `event`, because that is what is written there today.*

**Every claim says which kind of truth it is.** No code in the pure core can read a claim's sentence and decide; that is the model's judgement, which is why this field moves the **prompt fingerprint** — `1c224cc3…` on `main` against `1e80b47b…` with `persistence` added (adversarial pass). And measured against `backend/recordings/hormuz.jsonl`, now on `main`: **the recording states no `persistence` at all**, on any of its 18 accepted claims, so under R27 every claim on it is refused — as its **six `sustain` arrows** would be under a default of `event`, all six leaving claims the recording marks `kind: event`. Either way it is stale until the freeze re-records it, so **`persistence`, its two rules, the rename and the re-recording land in one pull request — stack 05's shape freeze — and this record is accepted before that freeze is written.**

The field is wanted rather than imposed: the six claims those `sustain` arrows leave each name a level that can move back — a war-risk premium, a Baltic freight assessment, the Japan–Korea LNG marker — or say outright that something *"holds for at least 30 consecutive days"*. The model has been writing states with no field in which to say so. *(What a model would answer if asked directly has not been measured, because nothing has asked it.)*

### Consequences

* Good, because the brief's own sentence comes out right, the product stops deleting things the reader typed, record 0005's best idea keeps its meaning instead of becoming a synonym, and it is mostly deletion — a state being no less accurate than an event, and record 0016's third defect dying with the calendar that caused it.
* Bad, because the model must make a judgement nothing in our code can check: a claim marked an event that is really a state simply never stops holding, and the only signal is a reader reading the sentence.
* Bad, because it adds a claim to the Hormuz map, so everything downstream of the strait moves again.
* Bad, because a `sustain` child's reading of the on–off joint is what takes record 0016's hard case over its time target at 2 000 versions.
* Bad, because **nobody has measured what a state does to the range**, under either rate. Every version of the map draws each claim's likelihood from its stated range; a state has two rates and the second is fitted rather than drawn, and nothing says what varies. The spike names this as a real gap, closed before this record is accepted.
* Neutral, because the canvas loses a badge and two colours and gains nothing to draw.

### Confirmation

* `test_a_sustain_arrow_must_leave_a_state` — the validator refuses a `sustain` arrow out of an event, in its own sentence, repairing nothing.
* `test_a_claim_says_which_kind_of_truth_it_is` — a claim with no `persistence` is refused as `claim_without_persistence`, with no default applied and nothing repaired.
* `test_both_events_stand_through_the_strike` — on the strike branch both events read `1.0000` on every day, neither is withdrawn, and the world carries no retraction because the model no longer exists.
* `test_the_state_is_what_falls` — the state's number and every claim it sustains are lower than in the base world. Directions and orderings, never typed-in values.
* `test_a_supposition_is_not_ended_by_a_cause_nobody_believes` — inserting a claim at `.001` with a weak opposing arrow leaves the supposed claim at `1.0000` on every day.
* `test_a_state_with_nothing_to_end_it_is_an_event` — the same claim written both ways, byte-identical.
* A source check naming the symbols rather than the English words: no `Retraction`, no `_retractions`, no `_opposing`, no undermining branch in `_spells_on`, no `"withdrawn"` or `"pushed"` in `SeriesState`.
* **The second oracle's tolerance, measured under the additive rate at 12 slices** — the grid the states sweep runs at, where record 0016's core runs at 24, so it is re-measured at 24 before it is written into the test. Over 240 adversarial maps of four claims or fewer, 3 322 numbers, no edit and every *Suppose*: mean `.00008`, 99th percentile `.00198`, worst `.00835`, **99.8% within `.005`** and 99.9% on endings (`round2/sweep2.py`). The *ever held* coding the adversarial pass ruled out stays ruled out — 97.0% of numbers and **93.3%** of endings within `.005`, worst `.07066`, worse at a finer grid. So `test_the_tables_agree_with_integrating_over_time` runs over maps carrying states as well as events at **`.005`, expected on at least 99% of the generated set**, failing cases named. Its enumerator exists as `round2/st2_core.py`, which reproduces record 0016's own additive judge to `4.4 × 10⁻¹⁶` on maps with no state — so the two halves are provably one engine — and record 0016's landing step 1 commits it under `backend/tests/`.

## Open for Kent

**Nothing.** The two questions this record carried are decided: **R26** asks an arrow that ends a state for *the chance it stops*, every other arrow keeping R6's wording; **R27** makes `persistence` always required, a map without it refused by name.

## More Information

* **Kent's decisions, 2026-09-21**, in the dated decisions note kept locally under `plans/notes/`: **R2** — events and states, automatic retraction deleted, both events left standing through the strike, record 0014's decision A reversed, and the model saying which kind each claim is, so the field rides the one shape freeze; **R21** — the in-between `kind` renamed `event` → `step`, `persistence: event | state` keeping his words, `middle` rejected as unintuitive; **R26** — an ending arrow asked for *the chance it stops*, one sentence in the freeze, amending record 0006; **R27** — `persistence` always required, refused by name. *(Those are the decisions note's words for his choices, not a transcript of his own.)*
* **The measurements.** The states spike's two rounds, 2026-09-21, scripts and logs kept locally under `plans/analysis/scripts/spike-05/states/`; round two re-measured every number here under record 0016's additive rate and middle-of-the-slice convention, on the same maps and seeds. The `sustain`-equals-`trigger` identity and the fingerprint pair are the adversarial pass's; the recording's counts were measured independently from `main`.
* **Related.** Proposed ADR-0016 (which this record exists because of) · ADR-0005 (its `mode` table amended here) · ADR-0014 (decision A reversed) · ADR-0003, ADR-0006, ADR-0012.
