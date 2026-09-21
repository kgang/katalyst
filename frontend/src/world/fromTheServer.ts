/**
 * Turning the server's own shapes into the shapes the canvas draws.
 *
 * Two sources read the server: the one that reads the stored example as it was
 * written, and the one that asks the engine to work a branch through. Both of
 * them turn the same claims, the same arrows and the same published items into
 * the same tiles and wires, so that work is written once, here, and neither can
 * drift from the other.
 *
 * **There is no arithmetic anywhere in this file.** A likelihood is read from
 * the server and carried, untouched and at full precision, to the component that
 * prints it. Rounding is a display decision and is made once, in the chip.
 *
 * **Nothing here invents a number.** Every slot that has no likelihood in it
 * gets an absence and the sentence saying why, and there is no path through any
 * function below that hands back a blank, a zero or a stand-in.
 */

import type { components } from "../api/schema";
import type {
  Absence,
  AbsenceKind,
  BaseRateView,
  ClaimView,
  EvidenceClipping,
  Known,
  LinkView,
  Ranged,
  SourceView,
} from "./types";

type FixtureBundle = components["schemas"]["FixtureBundle"];
type Proposition = components["schemas"]["Proposition"];
type Belief = components["schemas"]["Belief"];
type Evidence = components["schemas"]["Evidence"];
type Source = components["schemas"]["Source"];
type Link = components["schemas"]["Link"];

/**
 * The seed every question about one map is asked with.
 *
 * A world can always be rebuilt from three things — the map, the branch and the
 * seed — so the seed has to be the same on every visit, or the same map would
 * read differently twice in a row. It is read off the map's own date rather than
 * picked: the stored example is set on 2026-10-01, so the seed is 20261001. It
 * is printed under the map, beside the map's address, so that anybody can ask
 * the engine the same question and get the same answer.
 *
 * A seed is an input, not a reading. Nothing on screen is a number this
 * produced; it decides which of two thousand versions of the map get tried.
 *
 * @param bundle The stored example in full.
 * @returns The map's own date with its dashes taken out, as a whole number.
 */
export function seedFor(bundle: FixtureBundle): number {
  return Number(bundle.fixture_date.replaceAll("-", ""));
}

/**
 * Turn a likelihood from the server into a filled slot, unchanged.
 *
 * The three numbers are copied across at full precision. Rounding is a display
 * decision and is made once, in the chip that prints them.
 */
export function filled(belief: Belief): Known<Ranged> {
  return { reading: { p: belief.p, lo: belief.lo, hi: belief.hi } };
}

/** Turn "there is no number here" into the words and the reason for them. */
export function missing(kind: AbsenceKind, words: string, reason: string): Known<Ranged> {
  const absence: Absence = { kind, words, reason };
  return { absence };
}

/**
 * The single letter that stands for a publication, taken from the host name in
 * its own web address.
 *
 * `https://www.bbc.com/news/...` gives `B`. A leading `www.` is dropped first,
 * because every publication has one and it would make every monogram a `W`.
 *
 * A letter rather than the publication's own icon, deliberately: an icon is a
 * request to somebody else's server, and this app draws its first frame without
 * making one.
 */
export function monogramFor(url: string): { monogram: string; host: string } {
  let host: string;
  try {
    host = new URL(url).hostname;
  } catch {
    // An address we cannot read is not a crash. The clipping still has a line
    // to show, and the mark beside it says plainly that there is no host name.
    return { monogram: "?", host: "an address we could not read" };
  }
  const withoutWww = host.startsWith("www.") ? host.slice(4) : host;
  const first = withoutWww.slice(0, 1).toUpperCase();
  return { monogram: first === "" ? "?" : first, host: withoutWww };
}

/** Turn one published item into the clipping a tile shows. */
function clipping(evidence: Evidence): EvidenceClipping {
  const { monogram, host } = monogramFor(evidence.url);
  return {
    line: evidence.claim,
    monogram,
    host,
    direction: evidence.direction,
    url: evidence.url,
  };
}

/**
 * Turn one item behind an arrow into the source the panel prints.
 *
 * `retrieved` is the day *our own retrieval step* pulled the page down. It is
 * absent whenever a person typed the address in by hand, which is the case for
 * every source in the stored example — and the panel says that in words rather
 * than printing a day nobody fetched anything on.
 */
function source(item: Source): SourceView {
  const { host } = monogramFor(item.url);
  return {
    url: item.url,
    title: item.title,
    host,
    retrieved:
      item.retrieved === null || item.retrieved === undefined
        ? {
            absence: {
              kind: "not_said",
              words: "—",
              reason: "nobody fetched this; a person put the address in by hand",
            },
          }
        : { day: item.retrieved },
  };
}

/**
 * How often this kind of thing has happened before — or, when the map records
 * no such count, the sentence saying so.
 *
 * The count is printed as `7 of 9` and never as a rate. Dividing one by the
 * other would be this half of the product doing arithmetic on the map's
 * numbers, and it would also quietly claim that seven-in-nine is the answer,
 * which is exactly what a prior is for and exactly what it is not.
 */
function baseRate(
  proposition: Proposition,
): { readonly reading: BaseRateView } | { readonly absence: Absence } {
  const stored = proposition.base_rate;
  if (stored === null || stored === undefined) {
    return {
      absence: {
        kind: "not_said",
        words: "—",
        reason: "no reference class recorded for this claim",
      },
    };
  }
  return {
    reading: {
      referenceClass: stored.reference_class,
      k: stored.k,
      n: stored.n,
      sources: stored.sources.map((url) => source({ url, title: url, retrieved: null })),
    },
  };
}

/**
 * Why a claim has no market number, in the words the shared vocabulary settles.
 *
 * These three sentences are written here and nowhere else, so that the chip,
 * the tile and the panel beside the map cannot drift apart about what "no
 * market" means. `spec/vocabulary.md` is their source; change it there first
 * and then here.
 *
 * A claim that *ends* the map without an instrument is the exception, and it is
 * handled below: that one has a reason of its own, written down when the map
 * was made, and it is a finding rather than a fact about our plumbing.
 */
const NO_MARKET_REASON: Record<"market" | "event" | "hypothesis", string> = {
  market: "no venue quotes this claim; what you would trade is on the payoff",
  event: "no venue quotes this claim",
  hypothesis: "no venue quotes this claim",
};

/** Why this claim has no market number. */
function marketAbsence(proposition: Proposition): Known<Ranged> {
  if (proposition.kind === "not_tradeable") {
    // A dead end says why it is a dead end, in the map's own words. This is the
    // one reason a tile prints for itself, because it is an answer rather than
    // an apology.
    return missing(
      "no_market",
      "no market",
      proposition.not_tradeable_reason ?? NO_MARKET_REASON.event,
    );
  }
  return missing("no_market", "no market", NO_MARKET_REASON[proposition.kind]);
}

/**
 * What stands where a chain's multiplied-out likelihood would go.
 *
 * **A world does not carry one yet.** It holds a likelihood for every claim and
 * a series for every day, and nothing anywhere multiplies a route's steps
 * together. The engine will carry it; until it does the slot says so, because
 * working it out here would put a second answer on the map beside the engine's.
 */
export const NO_PATH_PRODUCT: Absence = {
  kind: "no_engine",
  words: "no engine yet",
  reason:
    "Nothing has multiplied this chain out. The likelihood of a whole route is worked out " +
    "where the map's numbers are, and the engine does not carry one yet.",
};

/**
 * Turn one claim from the server into the claim a tile draws.
 *
 * Every likelihood on it is the server's own. What the *model* thinks may be
 * replaced afterwards by a computed world's answer for the same claim; nothing
 * else is ever replaced.
 *
 * @param proposition The claim exactly as the server serves it.
 */
export function toClaim(proposition: Proposition): ClaimView {
  const beliefs = proposition.beliefs;
  return {
    id: proposition.id,
    claim: proposition.claim,
    kind: proposition.kind,
    resolvesBy: proposition.resolution.by,
    resolutionSource: proposition.resolution.source,
    resolutionCriteria: proposition.resolution.criteria,
    prior: { p: proposition.prior.p, lo: proposition.prior.lo, hi: proposition.prior.hi },
    baseRate: baseRate(proposition),
    beliefs: {
      model: filled(beliefs.model),
      user: beliefs.user
        ? filled(beliefs.user)
        : missing("not_said", "—", "You have not put your own number on this claim yet."),
      market: beliefs.market ? filled(beliefs.market) : marketAbsence(proposition),
    },
    // At most two clippings on a tile; every one of them in the panel beside
    // the map, where there is room to read them.
    evidence: proposition.evidence.slice(0, 2).map(clipping),
    evidenceInFull: proposition.evidence.map(clipping),
    pathProduct: { absence: NO_PATH_PRODUCT },
  };
}

/**
 * What stands where an arrow's own number would go before anything has asked
 * for it.
 *
 * The likelihood of this arrow's target with its cause supposed true costs a
 * whole extra run of the map, so it is worked out one arrow at a time, when a
 * reader asks about that arrow and not before.
 */
export const NOT_ASKED_FOR_YET: Absence = {
  kind: "no_engine",
  words: "no engine yet",
  reason:
    "Nothing has worked this number through the map yet. The likelihood with this arrow's " +
    "cause supposed true costs a whole extra run of the map, so it is worked out one arrow " +
    "at a time — select this arrow and it is asked for.",
};

/** Turn one arrow from the server into the arrow a wire draws. */
export function toLink(link: Link): LinkView {
  return {
    id: link.id,
    source: link.source,
    target: link.target,
    mode: link.mode,
    // Carried across at full precision and never touched. The wire compares it
    // against four fixed widths and five fixed bands of words; nothing adds it
    // to anything.
    strength: link.strength,
    lag: link.lag,
    shape: link.shape,
    halfLife: link.half_life ?? null,
    rationale: link.rationale,
    sources: link.sources.map(source),
    provenance: link.provenance,
    conditional: { absence: NOT_ASKED_FOR_YET },
    reflexive: link.reflexive,
  };
}
