/**
 * Folding a stream of events into a map that is being built.
 *
 * One pure function from (state, event) to state. It draws no pixels, makes no
 * requests, and **does no arithmetic**: every number it holds is a field it was
 * handed. Counting the rows in a list it holds is not arithmetic on the map's
 * numbers, and neither is asking whether a list is empty.
 *
 * Three rules shape everything below.
 *
 * **The likelihoods replace the map wholesale.** Until they arrive, the world
 * here is the browser's drawing of the proposals it has watched go past — the
 * claims, the arrows, and an absence with its reason in every likelihood slot.
 * When the engine's own world arrives it *is* the world, and the drawing is
 * thrown away rather than merged into. A browser keeping its own version beside
 * the engine's would be a second source of truth, and two sources of truth
 * disagree.
 *
 * **Nothing here mints an identifier.** A claim's identifier is minted by the
 * engine and arrives on the event. The one name this file makes is a reserved
 * rectangle's, it names a rectangle rather than a claim, and it is thrown away
 * the moment that claim stops being open.
 *
 * **A wire is drawn only when both of its ends exist.** In practice the engine
 * makes that true by construction — a claim and its incoming arrows arrive in one
 * event — and this file does not rely on it. An arrow whose two ends are not both
 * on the map is held and drawn the moment the second one arrives. A wire with one
 * end nowhere is a picture of something that is not true.
 */

import { absence } from "../world/absence";
import type { WorldSummary } from "../world/apiSource";
import { toWorldView } from "../world/apiSource";
import { toClaim, toLink } from "../world/fromTheServer";
import { inFewWords, NOT_ON_THIS_MAP } from "../world/naming";
import type { Absence, ClaimView, LinkView, WorldView } from "../world/types";
import type {
  Done,
  GenerationStarted,
  Link,
  Proposition,
  PropositionId,
  ReadEvent,
  Receipt,
  Verdict,
} from "./events";

/** One proposal the rules refused, as the strip beside the map lists it. */
export interface Refusal {
  /** Its place in the transcript, counting from 0. The engine's number. */
  readonly at: number;
  /** What the model wrote. Quoted, never drawn as a tile, never given an identifier. */
  readonly claimInWords: string;
  /** The validator's own sentences, one per rule broken, in the order it gave them. */
  readonly reasons: readonly string[];
}

/** One reserved rectangle at the growing edge of the map. Never a claim. */
export interface Skeleton {
  /** `skeleton:<claim id>`, or `skeleton:hypothesis` for the first one. A box's name. */
  readonly id: string;
  /** The one line it carries. The reader's own sentence, or the open claim's words. */
  readonly words: string;
  /** The open claim this one hangs off. Null for the first. */
  readonly after: PropositionId | null;
}

/**
 * Where a generation is. Each is a different thing on screen, and none is a
 * spinner.
 *
 * - `waiting` — the request has gone and the first event has not come back.
 * - `growing` — proposals are arriving.
 * - `settled` — the last line closed properly and the map is finished.
 * - `stopped` — a cap ended the run. The map is finished too, and the strip says
 *   which cap, in the engine's own words for it.
 * - `failed` — something on our side broke. The map that was built stays exactly
 *   where it is.
 * - `ended_early` — the stream stopped without saying anything at all. Not a
 *   failure, because nothing failed that anybody can name: a server was
 *   restarted, a proxy gave up on an idle connection, a laptop went to sleep in
 *   the middle of a ten-minute run.
 */
export type Phase = "waiting" | "growing" | "settled" | "stopped" | "failed" | "ended_early";

/**
 * Has the run stopped, whatever stopped it?
 *
 * Four of the five phases are over and one is not, and every screen that asks
 * asks the same question — so it is asked in one place. A screen listing the
 * four by hand is a screen that will list three of them the day a fifth way to
 * stop is added, and then a map will grow for ever in exactly one case.
 */
export function hasStopped(phase: Phase): boolean {
  return phase !== "waiting" && phase !== "growing";
}

/** Everything the screen knows about a generation. */
export interface Growth {
  readonly phase: Phase;
  /** The engine's name for this run. Null until the run has started. */
  readonly generationId: string | null;
  /**
   * The seed every likelihood in this run was worked out from, exactly as the
   * engine wrote it — its digits, not a number.
   *
   * A seed can be nineteen digits long and JavaScript holds a whole number
   * exactly only up to sixteen, so the parsed value is already rounded. Nothing
   * here computes with a seed; it is printed under the map so a reader can ask
   * for the same one again, and what is printed is what came off the wire.
   * Null until the run has started; never worked out here.
   */
  readonly seed: string | null;
  /** The sentence the reader typed, as the run's first event repeated it back. */
  readonly hypothesis: string;
  /** The destination the reader named, or null on the Explore door. */
  readonly target: string | null;
  /**
   * The map as far as it has been built, in the same view model the canvas
   * already draws. Every number slot the engine has not spoken about reads its
   * absence, so a half-built map is drawn by the components that already exist,
   * unchanged.
   */
  readonly world: WorldView;
  /**
   * One per claim still open to expand. Rebuilt from the frontier on **either**
   * growth event — accepted or refused — and emptied when the likelihoods arrive,
   * where the frontier is empty by definition.
   */
  readonly skeletons: readonly Skeleton[];
  /** Every refusal, in the order they happened. Never trimmed, never summarised away. */
  readonly refusals: readonly Refusal[];
  /** The Verify door's answer, when a destination was named. */
  readonly verdict: Verdict | null;
  /** What the run cost. Null until the receipt arrives; never estimated meanwhile. */
  readonly receipt: Receipt | null;
  /** Why the generation stopped. Null until it does. */
  readonly done: Done | null;
  /** The one sentence a broken run left. Null otherwise. */
  readonly failure: string | null;
  /**
   * Arrows whose two ends are not both on the map yet, held rather than drawn.
   *
   * Expected to stay empty — the engine sends a claim and its incoming arrows in
   * one event — and kept because a wire with one end nowhere is a picture of a
   * thing that is not true.
   */
  readonly waitingWires: readonly Link[];
  /** Event names this build does not know, and how many of each arrived. */
  readonly unknown: ReadonlyMap<string, number>;
}

/**
 * What stands where a likelihood would go while a map is still being built.
 *
 * It is the vocabulary's third row — *nothing has been computed* — because that
 * is exactly what is true: the map is not finished, and every likelihood is
 * worked through the finished map at once, when it is finished.
 */
export const WHILE_IT_GROWS: Absence = absence(
  "no_engine",
  "The map is still being built. Every likelihood is worked through the whole map at once, " +
    "when the map is finished — a number worked out from half a map would be the answer to a " +
    "question about a map that will not exist in a second.",
);

/** The one sentence under a growing map saying where everything on it came from. */
function originWhileGrowing(generationId: string | null, seed: string | null): string {
  const named = generationId === null ? "a generation that has not started yet" : generationId;
  const from = seed === null ? "a seed the engine has not named yet" : `seed ${seed}`;
  return (
    `Every claim and arrow on this map arrived from /api/generate, in generation ${named}, ` +
    `at ${from}. Nothing here was typed in, and no likelihood has been worked out yet: the ` +
    `engine works them through the whole map at once, when the map is finished.`
  );
}

/** An empty map, in the shape the canvas draws, with the reader's sentence as its title. */
function nothingYet(hypothesis: string): WorldView {
  return {
    // Until the run has a name of its own there is nothing to call this map. The
    // moment it has one, the name is the engine's.
    baseId: "",
    title: hypothesis,
    // The day the map is set on is the engine's day zero, and it arrives with the
    // world. Nothing on a growing map reads it — it is what an edit would be
    // dated by, and a map that is still being built cannot be edited.
    today: "",
    hypothesisId: "",
    claims: [],
    links: [],
    origin: originWhileGrowing(null, null),
  };
}

/**
 * Where a generation starts: a request has gone and nothing has come back.
 *
 * @param hypothesis The sentence the reader typed, so the screen has something
 *   to put on the first reserved rectangle before the engine has said anything.
 * @param target The destination they named, or nothing on the Explore door.
 */
export function waitingFor(hypothesis: string, target: string | null = null): Growth {
  return {
    phase: "waiting",
    generationId: null,
    seed: null,
    hypothesis,
    target,
    world: nothingYet(hypothesis),
    skeletons: [],
    refusals: [],
    verdict: null,
    receipt: null,
    done: null,
    failure: null,
    waitingWires: [],
    unknown: new Map(),
  };
}

/** The name of the rectangle held open for the claim a reader's own sentence becomes. */
export const FIRST_RECTANGLE = "skeleton:hypothesis";

/** The name of the rectangle held open at one claim's growing edge. */
export function rectangleFor(claimId: PropositionId): string {
  return `skeleton:${claimId}`;
}

/**
 * The reserved rectangles the frontier asks for, in the frontier's own order.
 *
 * The rectangles on screen are the frontier, drawn. That is a fact the stream
 * states on every growth event, never a guess made here — which is the whole
 * reason both growth events carry it.
 *
 * @param frontier The claims still open to expand, as the event named them.
 * @param claims The claims on the map, so a rectangle can quote the one it hangs
 *   off.
 */
function rectanglesFor(
  frontier: readonly PropositionId[],
  claims: readonly ClaimView[],
): Skeleton[] {
  const words = new Map(claims.map((claim) => [claim.id, claim.claim]));
  return frontier.map((id) => ({
    id: rectangleFor(id),
    words: `one step on from "${inFewWords(words.get(id) ?? NOT_ON_THIS_MAP)}"`,
    after: id,
  }));
}

/**
 * One claim from the stream, as the canvas draws it while the map is still
 * growing.
 *
 * The same reader every other claim on this canvas goes through, with one slot
 * written over: **the model's likelihood reads its absence.** The claim carries
 * the number the model stated for it, and printing that during the growing would
 * put a number on screen that nothing has worked through the map — and then
 * replace it, which is four numbers nobody computed by the time four causes have
 * arrived.
 */
function growingClaim(proposition: Proposition): ClaimView {
  const claim = toClaim(proposition);
  return {
    ...claim,
    beliefs: { ...claim.beliefs, model: { absence: WHILE_IT_GROWS } },
  };
}

/**
 * Every arrow whose two ends are now both on the map, and every one still
 * waiting.
 *
 * @param held The arrows held back so far.
 * @param arriving The arrows this event brought.
 * @param claims Every claim on the map once this event has been folded in.
 */
function wiresThatCanBeDrawn(
  held: readonly Link[],
  arriving: readonly Link[],
  claims: readonly ClaimView[],
): { drawn: LinkView[]; waiting: Link[] } {
  const there = new Set(claims.map((claim) => claim.id));
  const drawn: LinkView[] = [];
  const waiting: Link[] = [];
  for (const link of [...held, ...arriving]) {
    if (there.has(link.source) && there.has(link.target)) {
      drawn.push(toLink(link));
    } else {
      waiting.push(link);
    }
  }
  return { drawn, waiting };
}

/** Which claim the map starts from: the one the engine called the hypothesis. */
function hypothesisAmong(claims: readonly ClaimView[], sofar: string): string {
  if (sofar !== "") {
    return sofar;
  }
  return claims.find((claim) => claim.kind === "hypothesis")?.id ?? "";
}

/**
 * The seed this run drew with, as its digits.
 *
 * The reader puts the digits on the event because JavaScript cannot hold a
 * nineteen-digit whole number exactly. A caller that handed the events over by
 * hand has no digits to give, and the parsed number is then the whole of what is
 * known.
 */
function seedOf(event: GenerationStarted): string {
  return event.seed_as_written ?? String(event.seed);
}

/** The run has started: a name, a seed, and one rectangle carrying the reader's own words. */
function started(was: Growth, event: GenerationStarted): Growth {
  return {
    ...was,
    phase: "growing",
    generationId: event.generation_id,
    seed: seedOf(event),
    hypothesis: event.hypothesis,
    target: event.target,
    world: {
      ...was.world,
      // **The map has no identifier of its own until it is finished**, and the
      // generation's is not it: a generation is a run and a map is a thing it
      // built, and one run can hand its map to any number of later questions.
      // It arrives with `beliefs_propagated`, as the engine's own `base_id`.
      // Putting the run's name here would hand it to the insert route as *the
      // map the new claim is going onto*, which is a different thing that
      // happens to be a string of the same shape — and it would do it on
      // exactly the two screens where the map is half-built.
      title: event.hypothesis,
      origin: originWhileGrowing(event.generation_id, seedOf(event)),
    },
    skeletons: [{ id: FIRST_RECTANGLE, words: event.hypothesis, after: null }],
  };
}

/**
 * Fold one event into what the screen knows.
 *
 * @param was Everything known before this event.
 * @param event The event, with its name already joined onto its payload.
 * @returns Everything known after it, as a new object. Every one of the eight
 *   events changes something — even an unknown name, which changes the count of
 *   how many of it arrived — so there is no event this hands its argument back
 *   for, and a screen that compared the two to decide whether to redraw would be
 *   comparing two things that are never the same.
 */
export function fold(was: Growth, event: ReadEvent): Growth {
  switch (event.event) {
    case "generation_started":
      return started(was, event);

    case "proposal_accepted": {
      const claims =
        event.proposition === null
          ? was.world.claims
          : [...was.world.claims, growingClaim(event.proposition)];
      const { drawn, waiting } = wiresThatCanBeDrawn(was.waitingWires, event.links, claims);
      return {
        ...was,
        phase: "growing",
        world: {
          ...was.world,
          hypothesisId: hypothesisAmong(claims, was.world.hypothesisId),
          claims,
          // The arrows already on the map, and every one that can now be drawn:
          // the ones this event brought, and any that were held back waiting for
          // their second end. A held arrow was never on the map, so nothing is
          // drawn twice.
          links: [...was.world.links, ...drawn],
        },
        skeletons: rectanglesFor(event.frontier, claims),
        waitingWires: waiting,
      };
    }

    case "proposal_rejected":
      return {
        ...was,
        phase: "growing",
        refusals: [
          ...was.refusals,
          {
            at: event.at,
            claimInWords: event.claim_in_words,
            // The validator's own sentences, one per rule broken, with nothing
            // added and nothing dropped. The rule's code is never drawn.
            reasons: event.violations.map((violation) => violation.message),
          },
        ],
        // The same field the accepted event carries. A claim closed by its third
        // refusal in a row is gone from it here, so its rectangle comes down on
        // the refusal rather than waiting for a proposal that may never come.
        skeletons: rectanglesFor(event.frontier, was.world.claims),
      };

    case "beliefs_propagated": {
      const summary: WorldSummary = {
        id: event.world.base_id,
        title: was.hypothesis,
        day: event.world.day_zero,
        // The seed the run reported, not the one on the world: both are the
        // same seed, and only the first was read as its digits.
        origin: originOfTheFinishedMap(
          was,
          was.seed ?? String(event.world.seed),
          event.world.versions,
        ),
      };
      return {
        ...was,
        // The engine's world **is** the world. Whatever was drawn while it grew
        // is thrown away rather than merged into: two versions of one map
        // eventually disagree, and then nobody can say which is right.
        world: toWorldView(event.world, summary),
        // The frontier is empty by definition once the map is finished, so there
        // is nothing left for a reserved rectangle to stand for.
        skeletons: [],
        waitingWires: [],
      };
    }

    case "verdict":
      return { ...was, verdict: event };

    case "receipt":
      return { ...was, receipt: event };

    case "done":
      return {
        ...was,
        done: event,
        phase: event.reason === "reached_terminal" ? "settled" : "stopped",
      };

    case "failed":
      // The map that had been built stays exactly where it is. Nothing is
      // cleared and nothing is greyed: a reader whose run broke after twenty
      // claims keeps the twenty claims.
      //
      // **The rectangles go, and only the rectangles.** A reserved rectangle is
      // a promise that a claim is coming, and after this nothing is: the chapter
      // says no rectangle may ever stand where nothing will arrive, and a broken
      // run is the case it does not name. The claims still open are in the
      // working either way, so nothing is lost by taking the boxes down — what
      // would be lost by leaving them is a reader waiting for a claim for ever.
      return { ...was, phase: "failed", failure: event.message, skeletons: [] };

    case "unknown": {
      const counted = new Map(was.unknown);
      counted.set(event.name, (counted.get(event.name) ?? 0) + 1);
      return { ...was, unknown: counted };
    }
  }
}

/** The one sentence under a finished map, saying where every number on it came from. */
function originOfTheFinishedMap(was: Growth, seed: string, versions: number): string {
  const spelled = versions.toLocaleString("en-GB").replace(/,/g, " ");
  return (
    `Every claim and arrow on this map was proposed at /api/generate and accepted by the map's ` +
    `own rules; every likelihood was worked out by the engine from that map, at seed ${seed}, ` +
    `over ${spelled} versions of the map. The working is generation ` +
    `${was.generationId ?? "this run"}, and the same sentence and seed give the same map again.`
  );
}

/** Fold a whole stream, in order. What a test builds a finished map with. */
export function foldAll(from: Growth, events: readonly ReadEvent[]): Growth {
  return events.reduce(fold, from);
}

/**
 * The body ended, and nothing on it said the run was over.
 *
 * **A dropped stream is a finished generation with no terminator**
 * (`spec/generation/streaming.md`). Every stream a reader stayed for ends in
 * exactly one `done` or one `failed`; a stream that ends without either did not
 * *fail*, it simply stopped being delivered — a server restarted, a proxy gave
 * up on a connection it thought was idle, a laptop slept in the middle of a
 * ten-minute run. None of those is a fault anybody can name, and calling it one
 * would put a sentence on screen blaming something that may be blameless.
 *
 * **The rectangles come down.** They are the other half of the chapter's rule
 * that no rectangle ever stands where nothing is coming: after this, nothing is.
 * A map left growing for ever is the one screen in this product that lies
 * without saying anything — it is drawn exactly as a map that is about to change
 * and it is never going to change again.
 *
 * **The map is kept.** Everything that arrived is what arrived, and the working
 * as far as it got is still readable at the transcript route.
 *
 * It is not a wire event and is never folded as one. The server did not say
 * this; the reader noticed it, by reaching the end of a body.
 *
 * @param was Everything known when the body ended.
 * @returns The same state when a terminator had already arrived — a body that
 *   ends after `done` is a body ending normally — and an ended-early one when
 *   none had.
 */
export function theStreamEnded(was: Growth): Growth {
  if (hasStopped(was.phase)) {
    return was;
  }
  return { ...was, phase: "ended_early", skeletons: [] };
}
