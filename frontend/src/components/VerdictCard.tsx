/**
 * The Verify door's answer: a graded route to the place a reader asked about, or
 * an honest statement that nothing on the map reaches it.
 *
 * The two are not a success and a failure. **"No path reaches this" is the most
 * valuable thing this door can tell you**, so it is drawn as a finding, in the
 * engine's own sentence, with the nearest claim the map did reach named and one
 * control that selects it.
 *
 * **No bridge is drawn. Ever.** No dotted arrow from the nearest claim to the
 * destination, no ghost tile for it, no "probably connects" wording. Drawing a
 * faint one would be a fabrication in the exact place the honesty bar exists to
 * prevent one.
 *
 * **Nothing here multiplies anything, and nothing here counts anything either.**
 * The route's likelihood arrives on the verdict, worked out where the map's
 * numbers are worked out, and this card prints it; when there is none the slot
 * says so with its reason. How long the route is arrives the same way — inside
 * the engine's own sentence — and is printed rather than derived a second time
 * from the length of the path.
 */

import type { Verdict } from "../stream/events";
import type { WorldView } from "../world";
import { NOT_ON_THIS_MAP } from "../world/naming";
import { toTwoFigures } from "./BeliefChip";
import { PATH_PRODUCT_WART } from "./PathBar";
import "./verdictCard.css";

/** What the card needs to draw itself. */
export interface VerdictCardProps {
  /** The engine's answer, exactly as it arrived. */
  readonly verdict: Verdict;
  /** The destination in the reader's own words, as they typed it. */
  readonly target: string;
  /** The map, so a step can be named by its claim rather than by its identifier. */
  readonly world: WorldView;
  /** Put the panel and the map on one claim. */
  readonly onSelect?: (claimId: string) => void;
}

/** The Verify door's answer, in whichever of its two shapes arrived. */
export function VerdictCard({ verdict, target, world, onSelect }: VerdictCardProps) {
  const words = new Map(world.claims.map((claim) => [claim.id, claim.claim]));

  if (verdict.kind === "no_path") {
    const nearest = verdict.nearest;
    return (
      <section className="verdict-card" data-kind="no_path" aria-label="Where you said it ends">
        <h3 className="verdict-card__heading">No path reaches this</h3>
        <p className="verdict-card__target">{target}</p>
        {/* The engine's own plain sentence, printed as it came. This file
            composes no sentence about a verdict. */}
        <p className="verdict-card__why">{verdict.why}</p>
        {nearest === null ? null : (
          <p className="verdict-card__nearest">
            <span className="verdict-card__label">nearest claim reached</span>
            {/* Named by its words, never by its identifier — the same rule the
                validator's own sentences obey. A claim this map does not hold is
                a claim this card has nothing to point at, and it says so rather
                than printing a name nobody reads. */}
            {words.has(nearest) ? (
              <button
                className="verdict-card__pick"
                type="button"
                onClick={() => onSelect?.(nearest)}
              >
                {words.get(nearest)}
              </button>
            ) : (
              <span className="verdict-card__note">
                The engine named a claim this screen is not drawing, so there is nothing here to
                point at.
              </span>
            )}
          </p>
        )}
        <p className="verdict-card__note">
          Nothing is drawn between that claim and where you said it ends, because nothing on this
          map joins them. A faint arrow suggesting one might would be exactly the invention this
          product exists to refuse.
        </p>
      </section>
    );
  }

  return (
    <section className="verdict-card" data-kind="reached" aria-label="Where you said it ends">
      <h3 className="verdict-card__heading">The story reaches this</h3>
      <p className="verdict-card__target">{target}</p>
      <p className="verdict-card__why">{verdict.why}</p>

      {/* The route itself — one claim per row, named by its own words and
          numbered by where it sits. **No identifier is printed**: on a generated
          map they are twenty-six characters of the engine's own bookkeeping, and
          a reader learns nothing from one.
          **How long the route is is not worked out here.** The engine's own
          sentence above already says it — *"…reaches it in 2 steps"* — and this
          card used to say it again from a subtraction of its own, one fewer than
          the claims on the path. Two derivations of one fact agree until the day
          the engine counts a step differently, and then the card contradicts
          itself in two adjacent paragraphs with nothing to say which is right. */}
      <p className="verdict-card__route">the route, in order</p>
      <ol className="verdict-card__steps">
        {verdict.path.map((id, place) => (
          <li className="verdict-card__step" key={id}>
            <button className="verdict-card__pick" type="button" onClick={() => onSelect?.(id)}>
              <span className="verdict-card__step-id">{place === 0 ? "start" : place}</span>
              <span className="verdict-card__step-claim">{words.get(id) ?? NOT_ON_THIS_MAP}</span>
            </button>
          </li>
        ))}
      </ol>

      <p className="verdict-card__label">path likelihood</p>
      {verdict.product === null ? (
        <>
          <p className="verdict-card__reading" data-reading="no-number">
            no engine yet
          </p>
          <p className="verdict-card__note">
            The steps of this route have not been worked through the map, so there is no number to
            multiply out. Nothing here would work one out.
          </p>
        </>
      ) : (
        <p className="verdict-card__reading" data-reading="number">
          {toTwoFigures(verdict.product)}
        </p>
      )}
      {/* One wording, written where the path bar writes it. */}
      <p className="verdict-card__note">{PATH_PRODUCT_WART}</p>
    </section>
  );
}
