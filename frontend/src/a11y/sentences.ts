/**
 * The map, read rather than drawn.
 *
 * Every claim gets one sentence saying what it is, what the numbers on it are,
 * what causes it and what it causes. Nothing in a sentence depends on seeing
 * anything: the kind of push arrives as words, the direction of a push arrives
 * as words, and a number that is not there arrives as the reason it is not.
 *
 * This is not a fallback. It is the same world, and it is the strictest test the
 * colour law has — a rendering with no colour at all that still says everything.
 *
 * **A map is not a tree**, so the outline is a spanning tree: start at the claims
 * nothing causes, walk out along the wires in the order the map lists them, and
 * give every claim exactly one item, at its first arrival. A claim with several
 * causes does not appear twice; instead its own sentence names every wire coming
 * into it. Nothing is lost and the tree stays a tree.
 *
 * **It is built from the world, never from what happens to be painted.** A claim
 * sitting behind a "+4 more" tile still gets its item here — which is also why
 * activating one of those tiles opens this view, filtered to that column.
 */

import { toTwoFigures } from "../components/BeliefChip";
import { asQuoted } from "../graph/diff/days";
import type { ClaimView, LinkView, Slot, WorldView } from "../world";

/** One claim in the outline, with the claims it causes under it. */
export interface OutlineItem {
  /** The claim's identifier on the map. */
  readonly id: string;
  /** The whole claim, read aloud, in one line. */
  readonly sentence: string;
  /** How deep it sits, counting from one at the roots. */
  readonly level: number;
  /** The claims this one causes, in the order the map lists the wires. */
  readonly children: readonly OutlineItem[];
}

/** The first twelve counts in words. Past that a numeral is clearer than a word. */
const COUNTS = [
  "no",
  "one",
  "two",
  "three",
  "four",
  "five",
  "six",
  "seven",
  "eight",
  "nine",
  "ten",
  "eleven",
  "twelve",
];

/** A count, in the words a sentence would use. */
export function inWords(count: number): string {
  return COUNTS[count] ?? `${count}`;
}

/** A number of days, in the words a sentence would use. */
function daysInWords(lag: number): string {
  if (lag === 0) {
    return "the same day";
  }
  if (lag === 1) {
    return "one day later";
  }
  return `${inWords(Math.round(lag))} days later`;
}

/** One belief, read out: `Model .46, range .30 to .63`, or the reason there is none. */
function beliefInWords(owner: string, slot: Slot): string {
  if (slot.reading === undefined) {
    return `${owner} ${slot.absence.words} — ${slot.absence.reason}`;
  }
  const { p, lo, hi } = slot.reading;
  return `${owner} ${toTwoFigures(p)}, range ${toTwoFigures(lo)} to ${toTwoFigures(hi)}`;
}

/** How one arrow into this claim reads. */
function incomingInWords(wire: LinkView, from: ClaimView | undefined): string {
  const source = asQuoted(from?.claim ?? wire.source);
  const when = daysInWords(wire.lag);
  if (wire.reflexive) {
    return `Fed back into by ${source}, ${when}`;
  }
  if (wire.strength < 0) {
    return `Pushed the other way by ${source}`;
  }
  if (wire.mode === "sustain") {
    return `Held up by ${source}`;
  }
  return `Caused by ${source}, ${when}`;
}

/** What each kind of claim is, said plainly. */
function kindInWords(claim: ClaimView): string | null {
  switch (claim.kind) {
    case "hypothesis":
      return "The hypothesis — nothing on this map causes it";
    case "market":
      return "A tradeable ending";
    case "not_tradeable":
      return `Not tradeable — ${claim.beliefs.market.absence?.reason ?? "no venue quotes this claim"}`;
    case "event":
      return null;
  }
}

/**
 * One claim, read aloud, in one line.
 *
 * @param world The world this claim is in.
 * @param claim The claim itself.
 * @param under Which of the claims this one causes sit under it in the outline.
 *   The rest already have an item further up, so this sentence points at them
 *   rather than repeating them. Left out, every claim it causes counts as its
 *   own, which is what a sentence read on its own wants.
 */
export function claimSentence(
  world: WorldView,
  claim: ClaimView,
  under?: ReadonlySet<string>,
): string {
  const byId = new Map(world.claims.map((one) => [one.id, one]));
  const parts: string[] = [claim.claim.replace(/\.?$/, ".")];

  if (claim.diff !== undefined && claim.diff !== "untouched") {
    parts.push(
      claim.diff === "added"
        ? "Your edit added this claim."
        : claim.diff === "killed"
          ? "You supposed this is false."
          : "Your edit can reach this claim.",
    );
  } else if (claim.diff === "untouched") {
    parts.push("Your edit cannot reach this claim.");
  }

  if (claim.standing !== undefined) {
    parts.push(`${claim.standing.words}.`);
  } else {
    parts.push(`${beliefInWords("Model", claim.beliefs.model)}.`);
  }
  if (claim.beliefs.user.reading !== undefined) {
    parts.push(`${beliefInWords("Your own number", claim.beliefs.user)}.`);
  }
  parts.push(`${beliefInWords("Market", claim.beliefs.market)}.`);

  const kind = kindInWords(claim);
  if (kind !== null) {
    parts.push(`${kind}.`);
  }

  for (const wire of world.links.filter((one) => one.target === claim.id)) {
    parts.push(`${incomingInWords(wire, byId.get(wire.source))}.`);
  }

  const outgoing = world.links.filter((one) => one.source === claim.id);
  const repeats = under === undefined ? [] : outgoing.filter((one) => !under.has(one.target));
  const follows = outgoing.length - repeats.length;
  if (follows > 0) {
    parts.push(`${inWords(follows)} ${follows === 1 ? "claim follows" : "claims follow"}.`);
  }
  for (const wire of repeats) {
    parts.push(
      `It reaches ${asQuoted(byId.get(wire.target)?.claim ?? wire.target)}, already listed above.`,
    );
  }

  parts.push(`Settled by ${claim.resolvesBy}.`);
  return parts.join(" ");
}

/**
 * The whole map as a nested list.
 *
 * @param world The world to read out.
 */
export function outlineOf(world: WorldView): OutlineItem[] {
  const hasCause = new Set(world.links.map((wire) => wire.target));
  const roots = world.claims
    .filter((claim) => !hasCause.has(claim.id))
    .sort((a, b) => (a.id === world.hypothesisId ? -1 : b.id === world.hypothesisId ? 1 : 0));

  const said = new Set<string>();
  const under = new Map<string, Set<string>>();
  const byId = new Map(world.claims.map((claim) => [claim.id, claim]));

  const build = (id: string, level: number): OutlineItem | null => {
    const claim = byId.get(id);
    if (claim === undefined || said.has(id)) {
      return null;
    }
    said.add(id);
    const children = world.links
      .filter((wire) => wire.source === id)
      .map((wire) => build(wire.target, level + 1))
      .filter((item): item is OutlineItem => item !== null);
    under.set(id, new Set(children.map((child) => child.id)));
    return { id, sentence: "", level, children };
  };

  const skeleton = roots
    .map((claim) => build(claim.id, 1))
    .filter((item): item is OutlineItem => item !== null);

  // The sentences are written in a second pass, once every claim's place in the
  // tree is settled, so that "already listed above" means what it says.
  const fill = (item: OutlineItem): OutlineItem => ({
    ...item,
    sentence: claimSentence(
      world,
      byId.get(item.id) as ClaimView,
      under.get(item.id) ?? new Set<string>(),
    ),
    children: item.children.map(fill),
  });
  return skeleton.map(fill);
}

/** Every item in the outline, flattened, in reading order. */
export function flatten(items: readonly OutlineItem[]): OutlineItem[] {
  return items.flatMap((item) => [item, ...flatten(item.children)]);
}
