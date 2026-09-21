/**
 * The frame both map screens are drawn in, written once.
 *
 * A stored map and a map building itself are two different things — one is read
 * and edited, the other arrives claim by claim — but the screen around them is
 * the same screen, and it was written twice. A bar with the way back and the
 * map's name; the map filling everything under it, with whatever opens over the
 * stage and one line saying what the last keystroke did; the panel beside it in
 * the frame that carries the *there is more this way* rules; one polite line
 * said out loud; and, at the foot, where every number on this map came from.
 *
 * Two copies of that drifted the moment either was improved. The panel's frame
 * landed on one screen a round before the other; the error boundary landed on
 * one and not the other at all. **A reader who has learned one of these screens
 * has learned the other**, and that is a promise about the code as much as
 * about the picture: there is one screen here, and two things put into it.
 *
 * **It owns the panel's own measuring**, because the rules it draws are a fact
 * about the frame rather than about what either screen put in the panel — see
 * `useTheEdges.ts` for why they are drawn on the frame and never inside the box
 * they measure.
 *
 * **And it owns the one error boundary.** A fault while drawing a map that
 * arrived in a shape nothing expected takes the map down and leaves the bar
 * standing, which is the way back to the launchpad. React's own answer is to
 * unmount the whole tree, and a reader three minutes into a generation would be
 * left with a white page.
 */

import type { ReactNode } from "react";
import { IfTheScreenBreaks } from "./IfTheScreenBreaks";
import { edgeMarks, useTheEdgesOfThePanel } from "./useTheEdges";

/** What the frame needs. Every slot is a thing one of the two screens fills. */
export interface MapFrameProps {
  /** The map's name, in the bar. */
  readonly title: string;
  /**
   * What sits between the name and *Every key* — which branch you are in, or
   * which door this generation came through.
   */
  readonly where: ReactNode;
  /** Let this map go. On a generation it is also what stops the spending. */
  readonly onLeave: () => void;
  /** Open the sheet of every key. */
  readonly onEveryKey: () => void;
  /** The map itself. */
  readonly map: ReactNode;
  /**
   * Whatever is open over the stage: the palette, the sheet.
   *
   * Over the **stage** and never over the panel, and never over the whole
   * screen: there are no pop-ups anywhere in this product, and the panel is
   * what makes the map mean anything.
   */
  readonly overlay?: ReactNode;
  /** What the last keystroke did, under the map. */
  readonly status: string;
  /** The panel beside the map, or nothing when the reader has put it away. */
  readonly panel: ReactNode;
  /** The one line said out loud. Empty says nothing rather than saying nothing loudly. */
  readonly saying: string;
  /**
   * True when that line is spoken only.
   *
   * A generated map draws the same facts on the canvas, in the panel and under
   * the map, so printing them again made the foot of the screen three strips of
   * prose saying one thing three times. A stored map prints it, because nothing
   * else on that screen says what an edit just did.
   */
  readonly spokenOnly?: boolean;
  /** Where every number on this map came from, and anything still on its way. */
  readonly origin: ReactNode;
}

/** A map, and the screen around it. */
export function MapFrame({
  title,
  where,
  onLeave,
  onEveryKey,
  map,
  overlay,
  status,
  panel,
  saying,
  spokenOnly = false,
  origin,
}: MapFrameProps) {
  const { panel: scroller, edges } = useTheEdgesOfThePanel();

  const bar = (
    <header className="map-bar">
      <button className="map-bar__back" type="button" onClick={onLeave}>
        <span aria-hidden="true">←</span> Back to the launchpad
      </button>
      <h1 className="map-bar__title">{title}</h1>
      {where}
      <button className="map-bar__sheet" type="button" onClick={onEveryKey}>
        Every key (?)
      </button>
    </header>
  );

  return (
    <main className="page page--map">
      <IfTheScreenBreaks header={bar}>
        {/* The map and the panel, side by side. The panel is part of the screen
            rather than something that appears over it: there are no pop-ups
            anywhere in this product, and a dialog you have to dismiss would
            steal the map that makes the detail mean anything. */}
        <div className="map-body">
          <div className="map-stage">
            {map}
            {overlay}
            <p className="map-status">
              <span className="map-status__mark">last key</span>
              {status}
            </p>
          </div>

          {panel === null ? null : (
            // The frame holds the two rules that say there is more above or
            // more below. They are drawn on it rather than inside the panel so
            // that turning one on cannot change the scroll height it was worked
            // out from — see `useTheEdges.ts`.
            <div className="dock-frame" {...edgeMarks(edges)}>
              <aside className="dock" ref={scroller} aria-label="The panel beside the map">
                {panel}
              </aside>
            </div>
          )}
        </div>

        {/* Said out loud for a reader who is not looking at the picture.
            Polite: it waits for a pause rather than cutting across whatever is
            being read. */}
        <p className={spokenOnly ? "map-live map-live--spoken" : "map-live"} aria-live="polite">
          {saying}
        </p>

        {/* Where every number on this map came from, and anything that is still
            on its way. There is no spinner here and never will be: a spinner
            says "wait" without saying what for, so the line says what has been
            asked and at which address, and the map keeps drawing the last
            answer while it waits. */}
        <div className="map-origin">{origin}</div>
      </IfTheScreenBreaks>
    </main>
  );
}
