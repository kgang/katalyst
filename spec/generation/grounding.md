# Grounding — evidence at generation time

## Purpose

An arrow that says *why* is worth more than an arrow that says *how much*, and an arrow with a document behind it is worth more than either. This chapter is how a document gets behind an arrow while the map is being built (FR-28, evidence retrieval at generation time): the model is given a web search tool on the calls that need evidence, and whatever the search **actually returned** becomes the arrow's sources. It is what makes INV-2 — *every arrow says why and where from, and an arrow claiming evidence carries at least one source* — true of a generated map rather than of a hand-written one.

The point is not the searching. It is the receipt. **Provenance — where an arrow and its number came from — is written by us, from what happened, and never by the model** (decision record 0003, rule 5). A model that can write the word *documented* will write it. So the field is not on the shape it fills, and our code decides between three words by asking one question with a checkable answer: *did the search tool itself hand us at least one of the addresses this arrow cites?*

What a person gets that they did not have before: they can look at a wire's tail, see a three-dot origin mark, click it, and read the document. And when there is no document, they see a two-dot mark and the word *argued*, which is the truth rather than a blank.

---

## Data model

Two shapes and three small functions. The shapes are pydantic models — pydantic being the Python library we use to define a data shape and check anything claiming to be one.

### What a source is, and what a draft of one is

`Source` is a domain shape, defined in [`../graph/link.md`](../graph/link.md) and repeated here because this chapter is where one gets made:

```python
class Source(BaseModel):
    """Something a reader can open to check what we are claiming.

    A source exists because our retrieval step actually fetched a document, or
    because a person typed one in. It is never something the model reports
    having read. A `Source` is never invented to make a link look better than
    it is.
    """

    model_config = ConfigDict(frozen=True)

    url: str        # where the reader goes. One address that opens, not a search query
    title: str      # what the reader sees on arriving, in the publisher's words
    retrieved: date | None   # the day our retrieval step fetched it
```

`SourceDraft` — `url` and `title`, and deliberately no `retrieved` — is what a **model** may hand back, and it is defined in [`proposals.md`](proposals.md). The difference between the two shapes is the whole chapter: a draft is a claim about a document; a `Source` is a document our own search returned. The `retrieved` day is a fact about us, so there is nowhere for a model to write it.

### The search tool, as it is declared

Decision record 0006 settled the tool, and the specifics were re-verified against the `claude-api` skill on 2026-09-17:

```python
{"type": "web_search_20260209", "name": "web_search", "max_uses": 1}
```

- **`max_uses` is 1**, by the same rule that sets the run's budget: one proposal per call, one search per proposal. It is an argument, not a constant, and it is raised only once a measurement says it should be.
- **`code_execution` is not declared beside it.** This variant of the search tool already runs code for dynamic filtering; a second execution environment confuses the model (decision record 0006, and the skill's own note).
- **The web fetch tool is not declared at all.** Fetching a page ourselves would produce a document the search never offered, which is exactly the thing this chapter refuses to call a source.
- **A search error does not raise.** The answer comes back with a normal status and a result block whose content is a single error object — `max_uses_exceeded` is the one we expect. It is read as *no results*, never as a crash.

### The three functions that write a receipt

```python
def found_in(answer: Message, *, on: date) -> tuple[Source, ...]:
    """Every address the search tool itself returned during this one call.

    One `Source` per search result the vendor's answer carries, with
    `retrieved` set to the day the call ran. This is the only place a `Source`
    is built during generation.

    It must never include an address that came from the model's own text. The
    whole rule rests on this function reading the tool's results and nothing
    else.
    """


def keep_cited(draft: LinkDraft, found: tuple[Source, ...]) -> tuple[tuple[Source, ...], tuple[str, ...]]:
    """Split what the arrow cites into what we can stand behind, and what we drop.

    Returns the sources the search actually returned, in the order the model
    cited them, and the addresses it cited that the search never returned.

    Matching is an exact comparison of the address, after trimming surrounding
    whitespace and one trailing slash. Nothing cleverer: deciding that two
    slightly different addresses are 'the same page' is a judgement, and a
    judgement is how a dropped citation quietly comes back. A dropped address
    is never repaired, guessed at, or fetched to see whether it was real.
    """


def provenance_of(draft: LinkDraft, kept: tuple[Source, ...]) -> Provenance:
    """Which of the seven words this arrow has earned, from what actually happened.

    `documented` when at least one cited source survived `keep_cited`;
    otherwise `argued` when the arrow states a mechanism; otherwise `asserted`.

    It must never read anything the model said about its own confidence, and
    it must never return `historical`, `market_implied`, `user` or
    `simulated` — those four are written elsewhere, by whoever earns them.
    """
```

### The rule, in one table

| `provenance` | Written when |
|---|---|
| `documented` | At least one address the arrow cites is one **the search tool itself returned in that call** |
| `argued` | The arrow states a mechanism, and no cited address survived |
| `asserted` | Neither — no mechanism and nothing kept |
| `historical` · `market_implied` | **Never from a proposal.** Stack 05's adapters write these, from an event study or a live price |
| `user` | A person typed it — a retuned strength, or an arrow they added |
| `simulated` | A probe produced it (stack 06) |

**An address the model typed that the tool never returned is not a source** (Kent, 2026-09-17). It is dropped, and a note goes in the transcript naming the address and saying it was not returned by the search. It does not become a source with a warning beside it, and it does not quietly count toward `documented` — a word must mean what it says.

**Provenance is written before the map is validated**, because it is one of the four things we stamp on the way in, beside the two identifiers and the owner. That ordering has a visible consequence, and B4 below is it.

### What the model may say about a base rate

`BaseRate` is a domain shape ([`../graph/proposition.md`](../graph/proposition.md)), and `ClaimProposal` carries it optionally:

| Field | What it holds |
|---|---|
| `reference_class` | The set of past cases being counted, stated precisely enough that someone else could recount them |
| `k` | How many of those cases came out true |
| `n` | How many cases are in the set. `k` may never exceed `n`, checked when the shape is built |
| `sources` | Addresses where the count can be checked |

`sources` on a base rate is filled by the same rule as an arrow's: only addresses the search tool returned in that call survive. **An empty `sources` means the count is the model's own recollection, and nothing downstream of it may claim to be documented** — that sentence is already on the field, and this chapter is what enforces it.

`base_rate` is `None` when there is no honest reference class. Absent is better than invented, and the Inspector shows *no reference class* rather than a blank.

---

## Behaviour

Worked on the assignment's first example, *"The Strait of Hormuz is going to open next week."* The claims are the shipped example's: `H` the strait open for 14 consecutive days, `C` the Lloyd's war-risk premium below 0.4%, `B` Brent settling below $68 for five sessions, `R` OPEC+ announcing output restraint, `M1` the Polymarket contract, `M2` XLE against SPY, `N1` Omani-mediated talks resuming.

### B1 — a search runs, and one result becomes a source

The frontier claim is `C`. The call declares the search tool. The model searches for how war-risk premiums reach the delivered cost of a Gulf cargo, and the tool returns results — among them a Lloyd's List page titled *"War risk rates and voyage economics in the Gulf"*.

The proposal comes back naming `B` as a new claim, with the arrow `C → B`: mode `sustain`, shape `step`, a rationale saying that lower premiums cut the delivered cost of a cargo and the saving shows up in the physical differential within about a week, and one `SourceDraft` pointing at that Lloyd's List page.

Our code then does three things in order:

1. `found_in` reads the **tool's own results** out of the answer and turns each into a `Source`, stamping `retrieved` with the day the call ran.
2. `keep_cited` finds the Lloyd's List address among them. It survives.
3. `provenance_of` writes `documented`.

The arrow is minted with that one source and that word. On the canvas the wire carries a three-dot origin mark at its tail, and the Inspector lists the source with its title and the day we fetched it. This is exactly the arrow [`../graph/link.md`](../graph/link.md) B2 already describes; the difference is that the document is now real.

### B2 — an address the search never returned is dropped, and the transcript says so

Same call, but the model cites **two** addresses: the Lloyd's List page the tool returned, and a second address it wrote from memory that appears nowhere in the tool's results.

- The Lloyd's List page survives and becomes a `Source`.
- The second address is **dropped**. It is not fetched to see whether it is real, not kept with a caveat, not turned into a source with an empty title.
- `sources_dropped` on the accepted outcome carries that address, and the transcript gets a note: the arrow cited it, the search did not return it, so it is not behind this arrow.
- `provenance_of` still writes `documented`, because one cited source survived. The word is earned by the survivor, not lost to the impostor.

The whole rule fits in a sentence a reader can check: **citations come from the search tool's own results.** Anything else is the model reporting what it remembers reading, which is the thing `Source`'s own docstring already refuses (`test_a_cited_url_the_search_never_returned_is_not_a_source`, `test_provenance_is_written_from_what_was_found`).

### B3 — nothing was found, so the arrow says *argued*

The frontier claim is `H`. The model proposes `C` with the arrow `H → C`: mode `sustain`, shape `step`, and the rationale that underwriters reprice Gulf hulls only while the lane actually stays open — the low rate is held up by the openness, not caused once by it. The search returns nothing usable and the model cites nothing.

`provenance_of` writes **`argued`**: a mechanism was stated, and nothing was fetched to back it. The wire draws with a two-dot origin mark and the Inspector says *argued*. This is the honest, common case, and it is what the shipped example's arrows already say — that fixture is marked `argued` throughout precisely because no retrieval step ever ran for it.

Nothing is downgraded and nothing is upgraded. There is no path where an arrow that failed to find a document is quietly marked `documented`, and none where an arrow that found one is marked down to look modest.

### B4 — why no arrow this pipeline accepts is ever *asserted*

`asserted` means no mechanism and nothing kept. But **every arrow must carry a rationale** — that is rule 6 of the map's own rules, code `missing_rationale`, and it is checked on the map the proposal would leave behind. Provenance is written *before* validation, so an arrow with an empty rationale is stamped `asserted` and then refused a moment later, and never reaches the map.

So in this stack, **every accepted arrow is `documented` or `argued`**, and `asserted` survives only where it always has: on hand-written maps and, later, on a probe's output. The shipped example's `H → N1` is the one `asserted` arrow anywhere in the repository, marked that way by a person who judged its own sentence to be a story rather than a mechanism. **Our code does not make that judgement**, and must not: grading prose is exactly what we refuse to ask code to do, and exactly what we refuse to let a model do about itself.

Two consequences worth writing down. First, a **`documented` arrow that cites nothing cannot come out of this pipeline** — and is refused anyway, by rule 7, whoever wrote it: a fixture typed by hand, a stored map read back after the shapes changed, a future path that builds arrows some other way. `test_expand_rejects_a_documented_arrow_that_cites_nothing` pins both halves of that seam: a recorded answer whose every citation the search never returned is accepted as `argued` and never as `documented`, and the same arrow marked `documented` with an empty source list comes back with exactly one `documented_without_source` violation. Two rules pointing the same way.

Second, the **provenance-derived spread** on arrow strengths (stack 04's top pull request) meets only two of its seven widths on a generated map: `documented` and `argued`. The widest entries in that table are reached by hand-written and probe-produced arrows, not by generation.

### B5 — the outside view before the inside view

Before asking what the model thinks, ask what usually happens. The prompt asks, in plain words and in this order: *what set of past cases is this claim one of, how many of them came out true, and out of how many* — and only then *how likely is this one*.

Worked on `H`: the reference class is *"closure or disruption episodes in the Strait of Hormuz since 1980 that ended within 90 days"*, and the count is 7 out of 9. The likelihood the model then states sits well below 7-in-9, because this claim asks for 14 *consecutive* days inside one month, which is a harder test than an episode merely ending. The Inspector shows the class, the count and the sources, so a person who disputes the number can dispute the **class** instead of arguing with a feeling. That is the whole value of asking in this order.

If the search returned an address where the count can be checked, it lands in `sources` by the rule in B2. If it did not, `sources` is empty and the count is the model's recollection — visibly so, and nothing downstream of it may call itself documented.

**An honest caveat about the ordering.** The order the prompt asks in is not the order the answer's fields are written in: in the shape, `prior` sits above `base_rate`. Adaptive thinking means the model reasons before it writes anything at all (decision record 0006), so the field order may not matter — but nobody has measured it here, and Open questions 3 says how it would be measured.

### B6 — the searches cap is reached, and the map keeps building

The run's searches cap is the claims cap: thirty. Every call that declares the tool and uses it spends one, including the calls that follow a refusal — a retry costs what the first attempt cost, because it is a fresh question with a fresh search.

When the budget is gone, **searching stops and the generation carries on.** Later calls declare no search tool at all, so there is nothing for the model to try and nothing to half-use. Those calls still propose claims and arrows; their arrows come back **`argued`**, and an arrow whose rationale is empty is refused as it always is.

This is said out loud rather than hidden, because it is visible on screen anyway: the arrows added late in a large map carry two-dot origin marks where the early ones carry three. **Nothing in the interface disguises that, and nothing in the pipeline compensates for it.** The receipt records how many searches ran, so a reader can see which runs hit the ceiling.

Reaching the cap is **not** a reason for a generation to end. A complete map with some unbacked arrows is a better answer than a truncated map, and the origin marks say which arrows are which (`test_a_run_stops_searching_at_its_search_cap`).

### B7 — what a search result can and cannot become

A search result becomes **a `Source` on an arrow**, and nothing else.

It does not become an `Evidence` item on a claim. `Evidence` — a sentence, an address, a direction for or against, and a weight — is what the Inspector draws as two bars under a claim, and two of its four fields are numbers nobody has elicited: `ClaimProposal` has no `evidence` field, so generation writes none, and a generated claim carries an empty evidence list. The shipped example's two evidence items on `H` were typed by a person. Turning search results into evidence needs a direction and a weight from somewhere, and inventing either is the one thing this product refuses to do. Open questions 2 carries the wording repair this implies.

It does not become a market number. `market_implied` is read off a live price by stack 05's adapters, with a venue, a moment and a link; `historical` comes from a study of past cases. **Neither ever comes from a proposal**, and no code path in `engine/` writes either word.

---

## INVARIANTS

Each is written *for all inputs drawn from generator S, statement P holds*, and names the test that checks it. These run in `backend/tests/boundary/test_expand_cassettes.py`, against **cassettes** — real exchanges with the vendor recorded to disk and replayed, so the suite needs no key (INV-13).

Local numbers come from one pool shared by the five chapters of this part. **This chapter holds `INV-generation.9` through `INV-generation.13`**; [`proposals.md`](proposals.md) holds `.1` through `.8`.

| ID | Statement | Test |
|---|---|---|
| **INV-generation.9** | For every recorded call in `backend/tests/cassettes/`, the `provenance` on every accepted arrow equals what the rule table gives when applied to that call's own search results — compared against the tool's result set read out of the same cassette, never against what the model said | `test_provenance_is_written_from_what_was_found` |
| **INV-generation.10** | For every recorded call, every `Source` on every accepted arrow has an address the search tool returned in that same call, and every cited address it did not return appears in `sources_dropped` and in the transcript's note. No accepted arrow carries a source the tool never returned | `test_a_cited_url_the_search_never_returned_is_not_a_source` |
| **INV-generation.11** | For a recorded call whose every citation the search never returned, the accepted arrow reads `argued`. For any map holding an arrow marked `documented`, `historical` or `market_implied` with an empty source list, `validate` returns exactly one `documented_without_source` | `test_expand_rejects_a_documented_arrow_that_cites_nothing` |
| **INV-generation.12** | For every recorded run, the number of searches counted across its outcomes is at most the run's searches cap; every call made after the cap is reached declares no search tool; and the run still ends on one of the reasons in [`proposals.md`](proposals.md) B4, never on the cap itself | `test_a_run_stops_searching_at_its_search_cap` |
| **INV-generation.13** | Read over our own source: no code path under `backend/src/katalyst/engine/` writes `historical` or `market_implied`. The companion check — that `engine/proposal.py` contains no field named `provenance` — is a line on the pull request's own done-list, run as a plain search | `test_provenance_is_written_from_what_was_found` (its source-reading half) |

---

## ANTI-PATTERNS

1. **Do not trust an address because the model typed it** — *because* a model asked for citations will produce citations, and an address that opens nothing, or opens something else, is worse than no address at all: it invites a reader to check us and then embarrasses them. **Instead:** keep only what the search tool returned in that same call, and drop the rest with a note.
2. **Do not let the model declare its own provenance** — *because* provenance is a claim about our pipeline, not about the world, and a model that can write `documented` will write it. **Instead:** leave the field off the shape it fills, and write the word from what happened.
3. **Do not downgrade or upgrade a provenance after the fact** — no marking a `documented` arrow down to `argued` because its sources came back empty, no marking an `argued` arrow up because the rationale reads well — *because* that is repair wearing a different hat, and it makes the word describe our tidying rather than our retrieval. **Instead:** write the word once, from the facts, before the map is checked.
4. **Do not fetch a page yourself and call it a source** — *because* a document the search never offered is a document we went looking for to support a conclusion we already had. **Instead:** declare the search tool, keep what it returns, and declare nothing else.
5. **Do not ask for a likelihood before a reference class** — *because* a number stated first becomes the anchor and the class is then written to justify it, which is the opposite of the outside view. **Instead:** ask what usually happens, then ask about this case.
6. **Do not invent a direction or a weight to turn a search result into evidence** — *because* both are elicited numbers, and a number nobody gave is a number nobody can argue with. **Instead:** leave the claim's evidence list empty, which is honest, and say so in the Inspector.
7. **Do not treat a spent search budget as a reason to soften a word** — not `documented` "because it would have found something", not a silent stop — *because* the cap is a fact about the bill, not about the world. **Instead:** let the later arrows say `argued`, and let the origin marks show where the evidence thins out.

---

## Open questions

*Raised 2026-09-17, when this chapter was written.*

1. **FR-9's critique pass is out of stack 04, and Kent has been told why** (decided 2026-09-17). An adversarial pass over the map before the numbers are final would roughly **double the calls**, and its value cannot be read without something to read it against: until the evaluation scorecard exists there is no baseline that would show whether a critique pass made the maps better or merely more expensive. It is revisited in stack 07, with the scorecard from [`evaluation.md`](evaluation.md) as the comparison. Nothing about the proposal shape changes when it arrives — a critique is another question asked over the same call shape.
2. **FR-28 says sources attach to links "with direction and weight", and two different things are being named.** A `Source` on an arrow has no direction and no weight; an `Evidence` item on a claim has both, and generation produces none (B7). The requirement's wording should say which it means. The repair belongs in `PRODUCT_REQUIREMENTS.md`, not here.
3. **Does the field order in the answer change the number?** The prompt asks for the reference class before the likelihood, but the shape writes `prior` above `base_rate`. Moving `base_rate` above `prior` is a one-line change that renames nothing. Measurable with the evaluation harness: run the four examples both ways and compare how often a stated likelihood falls outside its own base rate's range. Worth one round of measurement in stack 07, not a guess now.
4. **Should `BaseRate.sources` become `Source` records rather than plain addresses?** A base rate's sources are bare strings, while an arrow's are records with a title and a retrieval day — so the same search result is kept in two shapes depending on where it lands. This is [`../graph/proposition.md`](../graph/proposition.md) Open questions 3, and generation is the first caller that has felt it.
5. **What counts as the same address?** Matching is exact, after trimming whitespace and one trailing slash. A model that writes the same page with a tracking parameter on the end loses the citation and the arrow falls back to `argued`. That is the safe direction to be wrong in, and it may still be too strict; the cassettes will show how often it happens.
