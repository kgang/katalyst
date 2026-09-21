# One live run, kept as an input to a test

`aLiveVerifyRun.ts` is the `events` array of one real generation, and nothing else.

| | |
|---|---|
| **What run** | The Hormuz sentence typed into the **Verify** door, with *Brent crude settles below $68 for five sessions* as the destination |
| **When** | 2026-09-21. It cost $2.17, and that was paid before this file existed |
| **Where it came from** | `backend/.runs/hormuz-2026-09-21T18-24-54Z-01M32HVA1F3SX18H513M6GTNPT.json`, the working file the run wrote for itself. That folder is not in this repository |
| **How big** | Sixteen events: the run starts, eleven proposals are accepted, one is refused, the Verify door answers, the receipt arrives, the run stops. Six claims, nine arrows |

**It is an input to a test, and nothing replays it to a reader.** It is not a
recording: it is not under `backend/recordings/`, no card on the first screen
reaches it, and no route will serve it. Putting it here asks no model anything
and spends nothing.

**Nothing inside an event was changed.** No sentence was shortened, no number
rounded, no field dropped. The one thing added is each event's own name —
`generation_started`, `proposal_accepted` and the rest — which on the wire is the
`event:` line beside the `data:` line, and which the kept file does not repeat.

**What was left out.** Everything in that file that is not an event: the
transcript of what the model was asked and answered, the receipt's working, the
finished graph, and the run's own notes about itself. A test of where a tile goes
reads none of them.

## Why this run and not the one already committed

The repository holds one stream, `backend/recordings/hormuz.jsonl`. It is an
**Explore** run — no destination — and every arrow on it points the way it should,
so the defect decision record 0024 is about cannot be seen on it.

The defect needs the **Verify** door. There the destination claim arrives second,
with nothing pointing at it yet, so it is drawn in the leftmost column beside the
hypothesis. Over the next ten events four arrows arrive into it from claims placed
to its right. On this run that is **three of nine arrows drawn pointing backwards**
— an arrow doubling back is a picture of an argument running the wrong way, and it
is what Kent saw.

`theSettle.test.ts` folds this run event by event through the same layering, the
same layout engine and the same reading-back of its answer that the screen uses,
and asserts after every single event that no arrow points backwards.
