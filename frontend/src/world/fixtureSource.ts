/**
 * The world source that reads the stored example the server ships with.
 *
 * Everything the canvas draws in this build comes through here, from
 * `GET /api/fixtures/hormuz`. Not one claim, likelihood, arrow or date is typed
 * into the browser. If the server's copy of the example changes, the picture
 * changes with it and nothing here needs editing.
 *
 * **What the numbers are, said plainly.** The stored example's likelihoods were
 * written by hand, and the file that holds them says so in its own comments:
 * they are illustrative, so the machinery has something honest-shaped to run
 * on. They are not computed and this half of the product computes nothing. The
 * sentence in `origin` below is what the screen prints under the map, so a
 * reader never has to take that on trust.
 *
 * There is no arithmetic in this file. A likelihood is read from the server and
 * carried, untouched and at full precision, to the component that prints it.
 */

import { readExample } from "../api/client";
import type { components } from "../api/schema";
import type { FixtureBundle, WorldSource } from "./source";
import type {
  Absence,
  ClaimView,
  EvidenceClipping,
  LinkView,
  Slot,
  WorldRequest,
  WorldView,
} from "./types";

type Proposition = components["schemas"]["Proposition"];
type Belief = components["schemas"]["Belief"];
type Evidence = components["schemas"]["Evidence"];

/**
 * Turn a likelihood from the server into a filled slot, unchanged.
 *
 * The three numbers are copied across at full precision. Rounding is a display
 * decision and is made once, in the chip that prints them.
 */
function filled(belief: Belief): Slot {
  return { reading: { p: belief.p, lo: belief.lo, hi: belief.hi } };
}

/** Turn "there is no number here" into the words and the reason for them. */
function missing(words: string, reason: string): Slot {
  const absence: Absence = { words, reason };
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
  return { line: evidence.claim, monogram, host, direction: evidence.direction };
}

/**
 * Why a claim has no market number.
 *
 * A claim that ends the map without an instrument carries its own reason, in
 * the map's own words, and that is the one worth showing. Everything else falls
 * back to what an absent market slot means on the server: no venue quotes this
 * claim.
 */
function marketAbsence(proposition: Proposition): Slot {
  if (proposition.kind === "not_tradeable" && proposition.not_tradeable_reason) {
    return missing("no market", proposition.not_tradeable_reason);
  }
  return missing("no market", "No venue quotes this claim, so there is no price to read.");
}

/** Turn one claim from the server into the claim a tile draws. */
function toClaim(proposition: Proposition): ClaimView {
  const beliefs = proposition.beliefs;
  return {
    id: proposition.id,
    claim: proposition.claim,
    kind: proposition.kind,
    resolvesBy: proposition.resolution.by,
    resolutionSource: proposition.resolution.source,
    beliefs: {
      model: filled(beliefs.model),
      user: beliefs.user
        ? filled(beliefs.user)
        : missing("—", "You have not put your own number on this claim yet."),
      market: beliefs.market ? filled(beliefs.market) : marketAbsence(proposition),
    },
    // At most two clippings on a tile. The rest live in the panel beside the
    // map, which is built in the pull request after this one.
    evidence: proposition.evidence.slice(0, 2).map(clipping),
  };
}

/** Turn one arrow from the server into the arrow a wire draws. */
function toLink(link: components["schemas"]["Link"]): LinkView {
  return {
    id: link.id,
    source: link.source,
    target: link.target,
    mode: link.mode,
    reflexive: link.reflexive,
  };
}

/**
 * Reads the stored example the server ships with, and builds the base world
 * out of the likelihoods stored on it.
 *
 * This is honest rather than a stopgap: the stored example says in its own
 * comments that its numbers are illustrative, and the map prints that sentence
 * under itself. What it is not is computed — and the moment the engine can
 * compute one, `ApiWorldSource` takes over and the same components draw it.
 */
export class FixtureWorldSource implements WorldSource {
  /** The base map and its branches, exactly as the route serves them. */
  async readBundle(id: string): Promise<FixtureBundle> {
    return readExample(id);
  }

  /**
   * The base world of a stored example.
   *
   * A branch cannot be asked for here, and saying so is the point: applying a
   * branch means re-propagating the map, which is the engine's work and not
   * this half's. Asking for one gets a sentence rather than a guess.
   */
  async readWorld(request: WorldRequest): Promise<WorldView> {
    if (request.branchId !== undefined) {
      throw new Error(
        "A branch cannot be worked out here yet. Applying a branch means re-running the " +
          "map's numbers, which the engine does; this build reads the stored example as it " +
          "was written.",
      );
    }
    const bundle = await this.readBundle(request.baseId);
    return {
      baseId: bundle.id,
      title: bundle.title,
      hypothesisId: bundle.graph.hypothesis_id,
      claims: bundle.graph.propositions.map(toClaim),
      links: bundle.graph.links.map(toLink),
      origin:
        `Every claim, arrow, likelihood and date on this map was read from ` +
        `/api/fixtures/${bundle.id}. They are the stored example's own numbers, written by ` +
        `hand to show the shape of an answer; nothing on this screen was computed here.`,
    };
  }
}
