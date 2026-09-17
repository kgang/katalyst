/**
 * The path bar: how likely the whole chain is, and which chain that was.
 *
 * A chain of four plausible steps is not a plausible chain. Every step in a map
 * like this one is something somebody found believable on its own, and the
 * number that says what the four of them come to together is the number the map
 * exists to produce. So whenever a claim is selected, the panel shows one route
 * from the hypothesis to it and the multiplied-out likelihood of that route's
 * steps beside the story.
 *
 * **This bar renders. It never multiplies.** The product arrives on the world,
 * computed where the map's numbers are computed. A canvas that multiplied its
 * own would be a second engine, and two engines disagree about half a point with
 * nobody able to say which is right. There is no multiplication anywhere in this
 * file; when the number is missing, the bar says so and stops.
 *
 * **Three things the bar can say, and they are not the same thing.**
 *
 *   1. **The number**, when the world carries one.
 *   2. **"no path shown"** — nothing is selected, or no route was asked for.
 *      This is the absent-number case, and it says which absence it is.
 *   3. **"no path from the hypothesis reaches this claim any more"** — a fact
 *      about the map rather than about our plumbing. It used to be a state on
 *      the tile and it is not one: it is a property of the *route*, so it lives
 *      here, where routes live.
 *
 * The bar never disappears. A missing bar looks like a bar nobody needed.
 *
 * **The honest wart, said beside the number rather than hidden.** The factors of
 * the product are each read on their own resolve-by day, so the product
 * multiplies numbers read on different days. It is still the most honest single
 * number available for a chain, and **it is not the chance of the whole chain
 * happening together.** The bar says that in those words.
 */

import { originStep } from "../graph/wires/encodings";
import type { ClaimView, LinkView, WorldView } from "../world";
import { toTwoFigures } from "./BeliefChip";
import "./pathBar.css";

/**
 * The honest wart, written once and printed wherever a multiplied-out route
 * likelihood is shown.
 *
 * Two surfaces print it: this bar, and the Verify door's card for a destination
 * the map reached. One wording, one place it is written — a caveat paraphrased on
 * a second screen is a second caveat, and one of them is eventually wrong.
 */
export const PATH_PRODUCT_WART =
  "Each step of this route is read on its own resolve-by day, so the number multiplies " +
  "likelihoods read on different days. It is the most honest single number there is for a " +
  "chain, and it is not the chance of the whole chain happening together.";

/** One step of a route: the arrow taken, and the claim it lands on. */
export interface RouteStep {
  /** The arrow walked along. */
  readonly wire: LinkView;
  /** The claim it lands on. */
  readonly claim: ClaimView;
}

/** A route from the hypothesis to a claim, and how well backed its weakest arrow is. */
export interface Route {
  /** Where the route starts. */
  readonly from: ClaimView;
  /** Each arrow taken and the claim it lands on, in order. */
  readonly steps: readonly RouteStep[];
}

/** How a route being looked for turned out. */
type Search =
  | { readonly found: true; readonly route: Route }
  | { readonly found: false; readonly why: "is-the-hypothesis" | "nothing-reaches-it" };

/** What one claim's best route so far looks like while the search is running. */
interface Best {
  /** How well backed the weakest arrow on this route is: three dots, two or one. */
  readonly bottleneck: number;
  /** How many arrows it takes. */
  readonly length: number;
  /** The arrows, in order. */
  readonly wires: readonly LinkView[];
}

/**
 * Is this route better than the one we had?
 *
 * **The best-backed route**: over every route from the hypothesis to the claim,
 * the one whose *weakest arrow is strongest* — the widest bottleneck. A chain is
 * only as well backed as its flimsiest step, so the route worth showing is the
 * one whose flimsiest step is the least flimsy. Where two routes tie, the
 * shorter one wins, and where they tie on that too, the one the map lists first.
 *
 * "Best backed" is measured by the receipt on each arrow — whether something was
 * fetched, whether a mechanism was stated, or whether it is the model talking —
 * which is a rank of three, not a number. Comparing two ranks is not arithmetic
 * on the map's numbers, and no push or likelihood is read anywhere in this
 * search.
 *
 * @param candidate The route just found.
 * @param incumbent The best route found so far, if any.
 */
function isBetter(candidate: Best, incumbent: Best | undefined): boolean {
  if (incumbent === undefined) {
    return true;
  }
  if (candidate.bottleneck !== incumbent.bottleneck) {
    return candidate.bottleneck > incumbent.bottleneck;
  }
  return candidate.length < incumbent.length;
}

/**
 * The best-backed route from the hypothesis to this claim.
 *
 * **Feedback arrows are set aside.** The rule is written once, in the chapter on
 * interventions: the map the engine works through is the map with feedback
 * arrows set aside, and anything asking *what can move* reads that map. A
 * likelihood flowing along a chain is exactly that question, so a claim reached
 * only through a feedback arrow has no route here — and the bar says so in
 * words rather than leaving a hole.
 *
 * @param world The map and its numbers.
 * @param claimId The claim the panel is open on.
 */
export function bestBackedRoute(world: WorldView, claimId: string): Search {
  if (claimId === world.hypothesisId) {
    return { found: false, why: "is-the-hypothesis" };
  }
  const claims = new Map(world.claims.map((claim) => [claim.id, claim]));
  const walkable = world.links.filter((link) => !link.reflexive);

  const best = new Map<string, Best>();
  best.set(world.hypothesisId, { bottleneck: Number.POSITIVE_INFINITY, length: 0, wires: [] });

  // Relax every arrow until nothing improves. The maps this runs on have a
  // handful of claims, so the simplest correct search is the right one.
  let changed = true;
  let rounds = 0;
  while (changed && rounds <= walkable.length) {
    changed = false;
    rounds += 1;
    for (const wire of walkable) {
      const upTo = best.get(wire.source);
      if (upTo === undefined) {
        continue;
      }
      const step = originStep(wire.provenance);
      const candidate: Best = {
        bottleneck: Math.min(upTo.bottleneck, step),
        length: upTo.length + 1,
        wires: [...upTo.wires, wire],
      };
      if (isBetter(candidate, best.get(wire.target))) {
        best.set(wire.target, candidate);
        changed = true;
      }
    }
  }

  const found = best.get(claimId);
  const from = claims.get(world.hypothesisId);
  if (found === undefined || from === undefined) {
    return { found: false, why: "nothing-reaches-it" };
  }
  const steps: RouteStep[] = [];
  for (const wire of found.wires) {
    const landed = claims.get(wire.target);
    if (landed === undefined) {
      return { found: false, why: "nothing-reaches-it" };
    }
    steps.push({ wire, claim: landed });
  }
  return { found: true, route: { from, steps } };
}

/** What the bar needs to draw itself. */
export interface PathBarProps {
  /** The map and its numbers. */
  readonly world: WorldView;
  /** The claim the panel is open on, or `null` when it is open on an arrow or on nothing. */
  readonly claimId: string | null;
}

/** The line of identifiers a route reads as: `H → B → M1`. */
function routeLine(route: Route): string {
  return [route.from.id, ...route.steps.map((step) => step.claim.id)].join(" → ");
}

/** The bar beside the story: one route, and what its steps come to together. */
export function PathBar({ world, claimId }: PathBarProps) {
  if (claimId === null) {
    return (
      <section className="path-bar" aria-label="How likely the whole chain is">
        <h3 className="path-bar__heading">Path from the hypothesis</h3>
        <p className="path-bar__reading" data-reading="no-path-shown">
          no path shown
        </p>
        <p className="path-bar__why">
          A path is shown for a claim. Select one on the map and this bar names the route from the
          hypothesis to it.
        </p>
      </section>
    );
  }

  const claim = world.claims.find((one) => one.id === claimId);
  const search = bestBackedRoute(world, claimId);

  if (!search.found) {
    return (
      <section className="path-bar" aria-label="How likely the whole chain is">
        <h3 className="path-bar__heading">Path from the hypothesis</h3>
        <p className="path-bar__reading" data-reading="no-route">
          {search.why === "is-the-hypothesis"
            ? "no path shown"
            : "no path from the hypothesis reaches this claim any more"}
        </p>
        <p className="path-bar__why">
          {search.why === "is-the-hypothesis"
            ? "This is the claim the map starts from. There is no route into it, because " +
              "nothing on the map comes before it."
            : "Every arrow that could carry the hypothesis to this claim is a feedback " +
              "arrow — a market acting back on the world it measures — and a chain's " +
              "likelihood is read on the map with those set aside. You can still walk to " +
              "this claim along the wires; nothing can push it."}
        </p>
      </section>
    );
  }

  const { route } = search;
  // The absence and its reason come from the world, and the bar prints them. It
  // does not fall back to working the number out; there is nothing here that
  // could.
  const product = claim?.pathProduct;
  const reading = product?.reading;

  return (
    <section className="path-bar" aria-label="How likely the whole chain is">
      <h3 className="path-bar__heading">Path from the hypothesis</h3>

      <p className="path-bar__route">{routeLine(route)}</p>

      <ol className="path-bar__steps">
        <li className="path-bar__step">
          <span className="path-bar__step-id">{route.from.id}</span>
          <span className="path-bar__step-claim">{route.from.claim}</span>
        </li>
        {route.steps.map((step) => (
          <li className="path-bar__step" key={step.wire.id}>
            <span className="path-bar__step-id">{step.claim.id}</span>
            <span className="path-bar__step-claim">{step.claim.claim}</span>
          </li>
        ))}
      </ol>

      <p className="path-bar__label">path likelihood</p>
      {reading === undefined ? (
        <>
          <p className="path-bar__reading" data-reading="no-number">
            {product?.absence.words ?? "no engine yet"}
          </p>
          <p className="path-bar__why">
            {product?.absence.reason ?? "Nothing has worked this number through the map yet."}
          </p>
        </>
      ) : (
        <p className="path-bar__reading" data-reading="number">
          {toTwoFigures(reading.p)}
        </p>
      )}

      <p className="path-bar__wart">{PATH_PRODUCT_WART}</p>
    </section>
  );
}
