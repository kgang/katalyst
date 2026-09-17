/**
 * Small maps to test against, built the way the real one is built.
 *
 * A test that writes out a whole claim or a whole arrow by hand spends most of
 * its lines on fields it does not care about, and the day the view model grows
 * a field every such test stops compiling at once. So the three builders below
 * hand back something complete and ordinary, and a test says only what it is
 * actually about:
 *
 *     aWire({ shape: "ramp", strength: -2.4 })
 *
 * Nothing here is a fixture of the stored example. These are plain shapes with
 * plausible contents, and no test should read a number out of one and expect it
 * to mean anything: the stored example is served by the server and read through
 * the world source, which is what the app itself does.
 */

import type { ClaimView, LinkView, WorldView } from "../world";

/** One claim, complete, with anything the test cares about written over the top. */
export function aClaim(over: Partial<ClaimView> = {}): ClaimView {
  return {
    id: "X",
    claim: "A claim that will be true or false by a date.",
    kind: "event",
    resolvesBy: "2026-11-01",
    resolutionSource: "A named source.",
    resolutionCriteria: "The test, written so that two people reading it would agree.",
    prior: { p: 0.28, lo: 0.15, hi: 0.42 },
    baseRate: { absence: { words: "—", reason: "no reference class recorded for this claim" } },
    beliefs: {
      model: { reading: { p: 0.35, lo: 0.22, hi: 0.5 } },
      user: { absence: { words: "—", reason: "You have not said." } },
      market: { absence: { words: "no market", reason: "no venue quotes this claim" } },
    },
    evidence: [],
    evidenceInFull: [],
    pathProduct: { absence: { words: "no engine yet", reason: "Nothing has worked it out." } },
    ...over,
  };
}

/** One arrow, complete, with anything the test cares about written over the top. */
export function aWire(over: Partial<LinkView> = {}): LinkView {
  const source = over.source ?? "H";
  const target = over.target ?? "B";
  return {
    id: `${source}->${target}`,
    source,
    target,
    mode: "trigger",
    strength: 1.6,
    lag: 2,
    shape: "impulse",
    halfLife: 30,
    rationale: "Why this cause moves this effect.",
    sources: [],
    provenance: "argued",
    conditional: { absence: { words: "no engine yet", reason: "Nothing has worked it out." } },
    reflexive: false,
    ...over,
  };
}

/** One world, complete, with anything the test cares about written over the top. */
export function aWorld(over: Partial<WorldView> = {}): WorldView {
  return {
    baseId: "example",
    title: "An example map",
    hypothesisId: "H",
    claims: [aClaim({ id: "H", kind: "hypothesis" }), aClaim({ id: "B" })],
    links: [aWire()],
    origin: "Every claim on this map was read from the server.",
    ...over,
  };
}
