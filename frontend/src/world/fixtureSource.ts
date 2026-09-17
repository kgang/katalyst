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
  AbsenceKind,
  BaseRateView,
  BranchHue,
  BranchView,
  ClaimView,
  Edit,
  EvidenceClipping,
  LinkView,
  Slot,
  SourceView,
  WorldRequest,
  WorldView,
} from "./types";

type Proposition = components["schemas"]["Proposition"];
type Belief = components["schemas"]["Belief"];
type Evidence = components["schemas"]["Evidence"];
type Source = components["schemas"]["Source"];
type Branch = components["schemas"]["Branch"];
type Graph = components["schemas"]["Graph"];

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
function missing(kind: AbsenceKind, words: string, reason: string): Slot {
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
 * the tile and — later — the panel beside the map cannot drift apart about what
 * "no market" means. `spec/vocabulary.md` is their source; change it there
 * first and then here.
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
function marketAbsence(proposition: Proposition): Slot {
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

/** Turn one claim from the server into the claim a tile draws. */
function toClaim(proposition: Proposition): ClaimView {
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
    // The multiplied-out likelihood of a route from the hypothesis to this
    // claim. It is computed on the world and this half of the product renders
    // it; there is no world yet, so there is no number, and the bar says which
    // route it would have been for and that nothing has worked it out.
    pathProduct: missing(
      "no_engine",
      "no engine yet",
      "Nothing has worked this number through the map yet. The likelihood of a whole " +
        "chain is multiplied out where the map's numbers are computed, and never here.",
    ),
  };
}

/** Turn one arrow from the server into the arrow a wire draws. */
function toLink(link: components["schemas"]["Link"]): LinkView {
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
    // The likelihood of this arrow's target with its source supposed true. The
    // engine works one out on request, one arrow at a time, and that route does
    // not exist yet — so every arrow in this build carries the absence and the
    // wire reads its push back in words instead.
    conditional: missing(
      "no_engine",
      "no engine yet",
      "Nothing has worked this number through the map yet. The likelihood with this " +
        "arrow's cause supposed true costs a whole extra run of the map, so it is " +
        "worked out one arrow at a time, and there is nothing to ask yet.",
    ),
    reflexive: link.reflexive,
  };
}

/**
 * The four hues a branch's lane and name chip may take, in the order they are
 * handed out. Never amber: amber already means "the money moves down".
 */
const HUES: readonly BranchHue[] = ["violet", "teal", "rose", "slate"];

/**
 * Turn one of the map's own branches into the branch the panel lists and the
 * diff view folds on.
 *
 * A branch holds no claims and no numbers of its own — only the edits. What it
 * does carry, when an **Add a claim** edit brought a whole claim with it, is
 * that claim and its arrows, so the map has something to draw. A claim the
 * reader types has only its words, and the branch panel shows it rather than the
 * map.
 *
 * @param branch The branch as the server serves it.
 * @param graph The base map, so that a **Change this push** edit can say what
 *   the push was before it moved.
 * @param hue Which of the four hues this branch takes.
 * @param today The day the map is set on, for an edit that names no day of its
 *   own.
 */
function toBranch(branch: Branch, graph: Graph, hue: BranchHue, today: string): BranchView {
  const claims: ClaimView[] = [];
  const links: LinkView[] = [];
  // biome-ignore lint/suspicious/useIterableCallbackReturn: the six operations are the whole of what a branch can hold — the server's own description of itself says so — so every branch of the switch below returns and the type checker proves it. There is no path out of it without a value, and a default case would be a branch no input can reach.
  const edits: Edit[] = branch.interventions.map((made): Edit => {
    switch (made.kind) {
      case "do":
        return { op: "do", target: made.target, value: made.value, at: made.at ?? today };
      case "observe":
        // Observing carries no day of its own: you can only report what has
        // already happened, and the map's window starts on its own first day.
        return { op: "observe", target: made.target, value: made.value, at: today };
      case "insert":
        claims.push(toClaim(made.proposition));
        links.push(...made.links.map(toLink));
        return {
          op: "insert",
          claimId: made.proposition.id,
          words: made.proposition.claim,
          arrows: made.links.map((link) => ({
            id: link.id,
            source: link.source,
            target: link.target,
          })),
        };
      case "retune":
        return {
          op: "retune",
          link: made.link,
          strength: made.strength,
          wasStrength: graph.links.find((link) => link.id === made.link)?.strength ?? made.strength,
        };
      case "refine":
        return { op: "refine", target: made.target };
      case "believe":
        return {
          op: "believe",
          target: made.target,
          belief: { p: made.belief.p, lo: made.belief.lo, hi: made.belief.hi },
        };
    }
  });
  return { id: branch.id, label: branch.label, hue, edits, claims, links };
}

/**
 * The branches a stored example carries, ready to be folded onto its map.
 *
 * @param bundle The stored example in full, as the route serves it.
 */
export function branchesOf(bundle: FixtureBundle): BranchView[] {
  return bundle.branches.map((branch, index) =>
    toBranch(branch, bundle.graph, HUES[index % HUES.length] ?? "violet", bundle.fixture_date),
  );
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
      today: bundle.fixture_date,
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
