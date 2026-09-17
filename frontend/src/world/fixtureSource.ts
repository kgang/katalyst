/**
 * The world source that reads the stored example the server ships with, and
 * computes nothing.
 *
 * It is the fallback. When the engine cannot be reached, a map you can still
 * read beats a blank screen — so this source hands back the stored example's own
 * claims, arrows and dates, with the likelihoods the example was written with,
 * and the screen says plainly that these are not computed numbers.
 *
 * **What the numbers are, said plainly.** The stored example's likelihoods were
 * written by hand, and the file that holds them says so in its own comments:
 * they are illustrative, so the machinery has something honest-shaped to run
 * on. They are not computed. The sentence in `origin` below is what the screen
 * prints under the map, so a reader never has to take that on trust.
 *
 * **What it cannot do, and says so rather than guessing.** Folding a branch,
 * comparing two worlds and working out one arrow's number all mean running the
 * map's numbers again, which is the engine's work. Each of the three asks here
 * gets a sentence saying that the engine could not be reached — never a
 * likelihood nobody computed.
 *
 * There is no arithmetic in this file. A likelihood is read from the server and
 * carried, untouched and at full precision, to the component that prints it.
 */

import { readExample } from "../api/client";
import type { components } from "../api/schema";
import { toClaim, toLink } from "./fromTheServer";
import type { FixtureBundle, WorldSource } from "./source";
import type {
  BranchHue,
  BranchView,
  ClaimView,
  ConditionalRequest,
  DiffRequest,
  DiffView,
  Edit,
  Known,
  LinkView,
  Ranged,
  WorldRequest,
  WorldView,
} from "./types";

type Branch = components["schemas"]["Branch"];
type Graph = components["schemas"]["Graph"];

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
 * that claim and its arrows, so the map has something to draw. It also carries
 * the branch exactly as the server wrote it, because that is what goes back
 * over the wire when a world is asked for: a claim the reader can see on screen
 * is a tile's worth of a claim, and folding a branch needs the whole of one.
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
  return { id: branch.id, label: branch.label, hue, edits, claims, links, wire: branch };
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
 * The sentence that stands where an engine's answer would be, when the engine
 * could not be reached.
 *
 * @param what What was being asked for, in the reader's words.
 */
function noEngineHere(what: string): Error {
  return new Error(
    `${what} means running the map's numbers again, which the engine does. The engine could ` +
      `not be reached, so this is the stored example as it was written — and nothing on screen ` +
      `has been worked out.`,
  );
}

/**
 * Reads the stored example the server ships with, and builds the base world
 * out of the likelihoods stored on it.
 *
 * This is honest rather than a stopgap: the stored example says in its own
 * comments that its numbers are illustrative, and the map prints that sentence
 * under itself. What it is not is computed — and when the engine can be reached,
 * `ApiWorldSource` takes over and the same components draw its answers.
 */
export class FixtureWorldSource implements WorldSource {
  /** The base map and its branches, exactly as the route serves them. */
  async readBundle(id: string): Promise<FixtureBundle> {
    return readExample(id);
  }

  /**
   * The base world of a stored example.
   *
   * A branch cannot be worked out here, and saying so is the point: applying a
   * branch means re-propagating the map, which is the engine's work and not this
   * one's. Asking for one gets a sentence rather than a guess.
   */
  async readWorld(request: WorldRequest): Promise<WorldView> {
    if (request.branch !== undefined) {
      throw noEngineHere("Folding a branch onto the map");
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

  /**
   * What moved between two worlds — which nothing here can say.
   *
   * Comparing two worlds needs both of them worked through, and this source
   * works nothing through.
   */
  async readDiff(_request: DiffRequest): Promise<DiffView> {
    throw noEngineHere("Saying what your edit moved");
  }

  /**
   * One arrow's own number — which nothing here can say either.
   *
   * The likelihood of an arrow's target with its cause supposed true costs a
   * whole extra run of the map.
   */
  async readConditional(_request: ConditionalRequest): Promise<Known<Ranged>> {
    throw noEngineHere("Working out the number on one arrow");
  }
}
