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

> **`proposed`.** It depends on proposed record 0016 being accepted — it exists because that record deletes something. Its measurements were re-run under that record's **additive** rate and the middle-of-the-slice convention, so no caveat about a superseded rate model remains; every number below is the re-run's.

> **In short.** A claim is an **event** — it happens once and stays happened — or a **state**, which holds over a stretch of time and can stop. A `sustain` arrow may leave only a state, and **automatic retraction is deleted** (Kent, R2). The in-between `kind` is renamed `event` → **`step`** (R21), so the four kinds read `hypothesis · step · market · not_tradeable`, and the new field is `persistence: event | state`.
>
> **On screen.** *"Hormuz opens, then Iran is struck"* leaves **both events at `1.0000`**. What falls is the state: `.6219 → .1661`, taking the ending from `.2991` to `.2613`. The *Retracted* badge and two day-states go.
>
> **What it costs.** Mostly deletion — about **65** lines of server code, **85** of browser code and eleven named tests. A state costs **nothing** in the exact solve (the same 64, 150 and **2 ms** as a map with no state) but its on–off joint is the one expensive piece: on a twenty-claim map five states take the forward pass from `224.4` to **`508.9 ms`** at 2 000 versions, which is what puts record 0016's budget item open. About **1.3 sessions**, riding the one shape freeze with the re-recording.
>
> **Open for Kent.** How an arrow that *ends* a state is asked about — R6's wording still gives a non-monotone answer and still clamps, where *the chance it stops* is closed form and clamps nothing; and whether a hand-written map may leave `persistence` out.

## Context and Problem Statement

Record 0005 gives every arrow a `mode`. A **`trigger`** arrow is a domino: it fires when its cause becomes true, and standing the cause back up later does not undo it. A **`sustain`** arrow is a desk holding an apple: the effect holds only while the cause holds. Record 0005 calls that pair *"the best idea in the brainstorm"*, and Kent asked to keep it.

Proposed record 0016 deletes it as a side effect. Under that record a claim's number is *the chance it has happened by day t* — a **first passage** probability, the first day something crosses a line — and what has happened never un-happens. The moment that is true, the quantity a `sustain` arrow reads (its cause's truth on each day) and the one a `trigger` arrow reads (whether its cause has fired) become the same array. **Measured:** not close, the same number — `0.442471` against `0.442471` — so `mode` becomes dead data fully determined by `shape` (adversarial pass, `attack3.py` §B; re-run 2026-09-21 by this record's author).

The only mechanism that can make a true claim untrue is **automatic retraction** — record 0014's rule, which ends a supposition on a calendar read off the map's shape. That rule is itself one of the three defects record 0016 exists to fix, reproduced in full in its Context. It cannot be what saves `sustain`.

**And the brief's own sentence is modelled wrong.** *"The Strait of Hormuz opened but Iran was struck the next day"* asks for a world in which **both things happened**; today the strike retracts the opening, so Monday's event un-happens because of Tuesday's news.

## Decision Drivers

* **Record 0005's best idea, and Kent's instruction to keep it** — whatever ships either keeps the distinction or says plainly that it is gone.
* **The brief's own sentence must come out right.** Both events stand.
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

A claim is an **event** — permanent once it happens, *the strait reopens* — or a **state** — it holds over an interval and can stop, *the strait stays open to commercial transit through 1 November*. **An event has one time, the day it happens; a state has two, the day it switches on and the day it switches off.** Both come out of the same arithmetic: a rate, integrated over the claim's own window.

**Where the two rates come from.** A state's **on-rate** is bent by its causes exactly as an event's rate is — under record 0016's additive rate, *bent* means each cause **adds its own rate**, calibrated in closed form: `added rate × (the arrow's shape added up over the window) = ln(1 − q0) − ln(1 − q1)`. Its **off-rate starts at zero** and is the sum of its ending causes' pushes, so with nothing on the map that can end it, it does not end — and **no second number is elicited**. Measured: a state with no ending cause is identical to the same claim written as an event, to **`1.4 × 10⁻¹⁶`** (`round2/check2.py`).

**Which rate an arrow bends: the sign decides, and no field is added.** An arrow whose elicited number is *above* the claim's own number **helps** and bends the on-rate; one *below* it **ends** and bends the off-rate. The alternative — sending it to the on-rate, where record 0016's own rule for an arrow that holds a claim back is to *scale the rate down while the cause is on* — cannot tell this record's story. On the map where the lane is already open, the strike landing on day 20 (`round2/hormuz2.py` §D):

| the strike arrow bends | the state, no strike | after the strike | the fall |
|---|---|---|---|
| **the off-rate (chosen)** | `.8309` | **`.0577`** | **`−.7732`** |
| the on-rate, by scaling it | `.9317` | `.7475` | `−.1842` |

Scaling a rate that has already done its work leaves almost nothing to scale: a strike that plainly closes the strait would move the claim everything hangs on by **18 points instead of 77** — the same shape as the defect this record exists to remove. **What the rule gives up:** a cause can make a state *start*, never make it *last longer*. Nothing in the Hormuz story wants to say that; the spike prices the alternative at about a session if Kent ever does.

**One interval.** A state switches on at most once and off at most once; a thing that comes back is a second claim.

**What the number means: the chance it is holding on its deadline** — on by the deadline, and not yet off. The tile reads *"17% — the chance this still holds on 1 November"* where an event's reads *"35% — the chance this happens by 1 November"*; two words differ, and under Kent's R17 the sentence is composed in the browser, so it is a one-file change. Three other readings were considered and rejected — *ever held*, which cannot fall; *holds through its whole window*, almost never true of a state that must be caused to start; and *share of the window it held*, which is not the probability of anything.

**What the two modes now mean.** A `trigger` arrow reads its source's **on time alone** and keeps pushing afterwards — the domino. A `sustain` arrow reads its source's **whole interval**: from the on time plus its lag until the off time, dead after — the apple on the desk. Measured on one map, changing nothing but the mode: the ending reads `.3182` under `trigger` and **`.3026`** under `sustain`, where before this record the two were identical to six decimal places (`round2/check2.py` §C).

**The two verbs.** *Suppose this is true* pins a state **on from its date and never off**; *This happened*, read on a date, says it **was holding on that date**. Both are the surgery an event already gets — pin the time, cut the incoming arrows.

**The per-day series.** A state's series is the chance it is **holding** on day *t*: it rises and it can fall. An event's can only rise. `World.series` keeps its type and carries two meanings, told apart by the claim's persistence — which answers the adversarial pass's M4. `DeltaRow.peak_delta` and `at_day`, whose rationale is *"shows up for a fortnight and then unwinds"*, describe **states** and are restated for events.

### How a state is carried, and what it costs

The forward timing pass carries a state's full joint over its two times; the small table the exact solve runs on carries **one bit** — *holding on its deadline*, the same question the tile asks. **A state is no less accurate than an event**, measured two ways on the same 82 map skeletons run once with states and once with every claim an event: worst gap `.00835` with the states on against `.00794` with them off, both at 99.8% of numbers within `.005` (`round2/sweep2.py`). **The exact solve does not move at all**: on a twenty-claim map with five states the largest factor, the entries built and the elimination time are **64, 150 and 2 ms**, identical to the same maps with no state.

**The on–off joint is the one expensive piece, and only a `sustain` child needs it.** A state's own number needs its holding curve, at versions × slices squared — `3.6 ms` per state at 2 000 versions. A `sustain` child reads the whole interval, which needs the joint, at versions × slices **cubed** — `78.9 ms` per state. So five states take the twenty-claim forward pass from `224.4` to **`508.9 ms`** at 2 000 versions and from `26.9` to `55.7 ms` at 200 (`round2/cost2.py`, `cost2.log`). **That is what puts record 0016's budget open for Kent**, and three unmeasured ways down are named there.

### The Hormuz strike, worked

**Every number fed in is an illustrative input** — no prior, arrow number, lag or half-life below was measured, exactly as the committed fixture says of its own. Every number printed is computed from them (`round2/hormuz2.py`, `hormuz2.log`; 30 slices over 60 days, day 60 being 1 November). Four claims: *the strait reopens* (event) helps *the strait stays open through 1 November* (state), *Iran is struck* (event) ends it, and the state sustains *Brent settles below the threshold* (the ending).

| | base | *Suppose the strait reopens* | *…and Iran is struck* | move |
|---|---|---|---|---|
| the strait reopens (event) | `.3500` | **`1.0000`** | **`1.0000`** | `+.0000` |
| Iran is struck (event) | `.1800` | `.1800` | **`1.0000`** | `+.8200` |
| the strait stays open through 1 Nov (**state**) | `.2354` | `.6219` | **`.1661`** | **`−.4558`** |
| Brent settles below the threshold (the ending) | `.2718` | `.2991` | **`.2613`** | `−.0377` |

**Both events stand at `1.0000`** — neither withdrawn, retracted nor dated out — and **no retraction machinery is involved anywhere**: nothing consults a calendar, nothing un-trues a claim, and the word *retracted* does not appear. The state's series rises and falls, peaking at `.2352` on day 42, while the supposed event reads `1.0000` on every day from day 30, so there is no middle state to draw and no badge to write.

**The third defect cannot recur.** Re-measured on the same map: insert the claim nobody believes — prior `.001`, a weak arrow pushing against a supposed claim — and the supposed claim reads **`1.0000` on every one of the thirty days**, written as an event and as a state alike. A *Suppose* pins the claim's time and cuts its incoming arrows, so no calendar is consulted and there is none to get wrong.

### What is deleted

The `Retracted · date · by "…"` badge — `spec/vocabulary.md` calls it the one *derived* badge, the only one no button produces — and its entry. Two of the four day-states: `SeriesState` is `sampled · supposed · withdrawn · pushed` (`propagation.py:90`) and the last two go. **Retraction by calendar, entirely**: `_opposing`, the undermining block inside `_spells_on`, `_retractions`, `_states`, the `Retraction` model on the wire, the sensitivity sweep's rebuild of which edit introduced a claim (`diff.py:436-441`), the browser's client-side retraction detector (`graph/diff/badges.ts`) and the badge's two readers. **About 65 executable lines of server code, 85 of browser code, and eleven named tests** — the spike's read-only inventory cites file and line for each. And **UX-14, and FR-15's retraction clause** (*"`sustain` links retract, `trigger` links do not"*, P0), whose replacement wording is in the owed-edits list travelling with this record.

**One caution, found by reading rather than assumed:** `_Spell.undermined_on` is read in **three** places, the third being `_fixed_days` (`propagation.py:1566`) — the arithmetic that decides when a supposed value stops being held. This touches the core loop, not only a label.

**This reverses decision A of record 0014** — *"it **stops holding** on the day the **cause** of the first live arrow pushing against it becomes true"* — with its three-state table and its two confirmation tests. **What stands:** a supposition is a hard fact in every world *while it holds*, and the tile shows **Supposed · date**, never a number. What changes is that nothing ends it but another edit. **It also amends ADR-0005's `mode` table**, whose two modes are restated as *which of the source's times the arrow reads*.

### The one new rule, the rename, and the freeze they ride in

**A `sustain` arrow may only leave a claim whose `persistence` is `state`** — a twenty-first violation code, named **`sustain_without_state`** because six of the twenty existing codes are already `<subject>_without_<required thing>` and all twenty are article-free (the spike proposed `sustain_from_an_event`). A refusal with a sentence, never a repair. The spike considered six further rules and added none; two are worth naming. A state with nothing that can end it is **not** a fault — it behaves exactly like an event, measured — but is a good candidate for a warning. And an arrow that ends a state may point at an event, because an arrow pushing an event down is already legal.

**The in-between kind is renamed `step` (Kent, R21).** A claim's `kind` says what the claim is *for* in the map, and its in-between value was called `event` — so the commonest claim of all, a step in the middle of a chain that can stop holding, would have read `kind: event, persistence: state`, which parses as a contradiction until you know the rule. **The four kinds become `hypothesis · step · market · not_tradeable`, and `persistence: event | state` keeps Kent's words**; he rejected `middle` as unintuitive. An arrow's `shape` also has a value `step`, but that is a field on an arrow and this one is on a claim, so no claim ever reads as a contradiction. The rename is **46 lines of code and 21 of spec and records** where `kind` and the word *event* meet (re-measured after stack 04 landed; it was 42 and 17 before), plus the recording, the fixture, the generated browser types and the validator's messages. *Everywhere below that describes today's code or quotes a file that exists, the word is still `event`, because that is what is written there today.*

**Every claim says which kind of truth it is.** No code in the pure core can read a claim's sentence and decide; that is the model's judgement, which is why this field moves the **prompt fingerprint** — `1c224cc3…` on `main` against `1e80b47b…` with `persistence` added (adversarial pass). And measured against `backend/recordings/hormuz.jsonl`, now on `main`: **the recording states no `persistence` at all**, on any of its 18 accepted claims. Under the recommended rule below (no default) every claim on it is refused; under a default of `event`, its **six `sustain` arrows** are. Either way it is stale until the freeze re-records it, so **`persistence`, the rename, the new rule and the re-recording land in one pull request — stack 05's shape freeze — and this record is accepted before that freeze is written.**

The field is wanted rather than imposed: the six claims those `sustain` arrows leave each name a level that can move back — a war-risk premium, a Baltic freight assessment, the Japan–Korea LNG marker — or say outright that something *"holds for at least 30 consecutive days"*. The model has been writing states with no field in which to say so. *(What a model would answer if asked directly has not been measured, because nothing has asked it.)*

### Consequences

* Good, because the brief's own sentence comes out right, the product stops deleting things the reader typed, and record 0005's best idea keeps its meaning instead of becoming a synonym.
* Good, because it is mostly deletion, a state is no less accurate than an event, and record 0016's third defect dies with the calendar that caused it.
* Bad, because the model must make a judgement nothing in our code can check: a claim marked an event that is really a state simply never stops holding, and the only signal is a reader reading the sentence.
* Bad, because it adds a claim to the Hormuz map, so everything downstream of the strait moves again; and a cause cannot make a state last longer, only start — the price of deriving which rate an arrow bends from its sign.
* Bad, because a `sustain` child's reading of the on–off joint is what takes record 0016's benchmark over its budget at 2 000 versions.
* Bad, because **nobody has measured what a state does to the range**, under either rate. Every version of the map draws each claim's likelihood from its stated range; a state has two rates and the second is fitted rather than drawn, and nothing says what varies. The spike names this as a real gap, closed before this record is accepted.
* Neutral, because the canvas loses a badge and two colours and gains nothing to draw.

### Confirmation

* `test_a_sustain_arrow_must_leave_a_state` — the validator refuses a `sustain` arrow out of an event, in its own sentence, repairing nothing.
* `test_both_events_stand_through_the_strike` — on the strike branch both events read `1.0000` on every day, neither is withdrawn, and the world carries no retraction because the model no longer exists.
* `test_the_state_is_what_falls` — the state's number and every claim it sustains are lower than in the base world. Directions and orderings, never typed-in values.
* `test_a_supposition_is_not_ended_by_a_cause_nobody_believes` — inserting a claim at `.001` with a weak opposing arrow leaves the supposed claim at `1.0000` on every day.
* `test_a_state_with_nothing_to_end_it_is_an_event` — the same claim written both ways, byte-identical.
* A source check naming the symbols rather than the English words: no `Retraction`, no `_retractions`, no `_opposing`, no undermining branch in `_spells_on`, no `"withdrawn"` or `"pushed"` in `SeriesState`.
* **The second oracle's tolerance, measured under the additive rate at 12 slices** — the grid the states sweep runs at, where record 0016's core runs at 24, so it is re-measured at 24 before it is written into the test. Over 240 adversarial maps of four claims or fewer, 3 322 numbers, no edit and every *Suppose*: mean `.00008`, 99th percentile `.00198`, worst `.00835`, **99.8% within `.005`** and 99.9% on endings (`round2/sweep2.py`). The *ever held* coding the adversarial pass ruled out stays ruled out — 97.0% of numbers and **93.3%** of endings within `.005`, worst `.07066`, worse at a finer grid. So `test_the_tables_agree_with_integrating_over_time` runs over maps carrying states as well as events at **`.005`, expected on at least 99% of the generated set**, failing cases named. Its enumerator exists as `round2/st2_core.py`, which reproduces record 0016's own additive judge to `4.4 × 10⁻¹⁶` on maps with no state — so the two halves are provably one engine — and record 0016's landing step 1 commits it under `backend/tests/`.

## Open for Kent

**1. How an arrow that *ends* a state is asked about.** This touches decision R6 and belongs to the shape freeze; it is not this record's to take. R6 asks every arrow *the chance the target happens by its deadline if this cause happens at the start of the window and no other cause does*, and for an ending arrow that strips away the very thing that turned the state on. Measured under the additive rate, sweeping only the strike arrow's half-life (`round2/hormuz2.py` §B):

| the strike arrow | R6's wording as it stands | asked as *the chance it stops* |
|---|---|---|
| step, no decay | state `.1613` | state `.3994` |
| impulse, half-life 2 | state `.4929` *(the fit gave up)* | state `.6941` |
| impulse, half-life 6 | state `.1037` | state `.6547` |
| impulse, half-life 20 | state `.1375` | state `.4993` |

Under R6's wording the same elicited number gives `.4929, .1037, .1375, .1613` as the spike lengthens — not monotone, and a six-day spike still bites harder than a permanent step. **The additive rate repaired half of this and not the other half.** The fit giving up fell from **14.8%** of ending arrows to **1.3%** (108 of 8 082, `round2/sweep2.py`), because the additive off-rate has no ceiling where the multiplicative one did. What did not move is the question: R6 asks for a number about the target while stripping away the cause that turned the target on. And *the chance it stops* is **closed form** — `−ln(1 − it stops) / (its shape added up over the window)`, the helping arrow's own formula, reproducing the old bisection to `8.0 × 10⁻¹⁶` — so on the named and hard families it fits **2 106 arrows with 0 root finds and 0 clamps**, where R6's wording needs **2 106 root finds and clamps 54** (2.6%). Accuracy is the same either way, so this is a question about what a reader can honestly answer.

* *Recommended:* one extra prompt sentence inside the one freeze, asking an ending arrow for **the chance the state stops** — ending arrows only, R6's wording untouched everywhere else. Cost: one sentence, in a freeze that is happening anyway, and the bisection can be deleted.
* Alternative: keep R6's single wording for every arrow. Cost: free, and a root find per ending arrow, 1.3% of them clamped, and a non-monotone answer as a spike lengthens.

**2. Whether a hand-written map may leave `persistence` out.** *Recommended:* no default — every claim says which it is, one line in each of the seven Hormuz claims and in the property-test builders, matching *reject, never repair*. Alternative: default to `event`, which costs nothing today and means the first hand-written state someone forgets to mark never stops holding, silently.

## More Information

* **Kent's decisions, 2026-09-21**, recorded in the dated decisions note kept locally under `plans/notes/`: **R2** — events and states, automatic retraction deleted, both events left standing through the strike, record 0014's decision A reversed, and the model saying which kind each claim is, so the field rides the one shape freeze; and **R21** — the in-between `kind` is renamed `event` → `step`, `persistence: event | state` keeps his words, and `middle` was rejected as unintuitive. *(Those are the decisions note's words for his choices, not a transcript of his own.)*
* **The measurements.** The states spike's two rounds, 2026-09-21, scripts and logs kept locally under `plans/analysis/scripts/spike-05/states/`; round two re-measured every number here under record 0016's additive rate and middle-of-the-slice convention, on the same maps and seeds. The `sustain`-equals-`trigger` identity and the fingerprint pair are the adversarial pass's; the recording's counts were measured independently from `main`.
* **Related.** Proposed ADR-0016 (which this record exists because of) · ADR-0005 (its `mode` table amended here) · ADR-0014 (decision A reversed) · ADR-0003, ADR-0006, ADR-0012.
