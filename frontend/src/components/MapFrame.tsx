/**
 * The frame both map screens are drawn in, written once.
 *
 * A stored map and a map building itself are two different things — one is read
 * and edited, the other arrives claim by claim — but the screen around them is
 * the same screen, and it was written twice. A bar with the way back and the
 * map's name; the map filling everything under it, with whatever opens over the
 * stage; the panel beside it in the frame that carries the *there is more this
 * way* rules; and **one band at the foot** that says what is happening to the
 * map, what the last keystroke did, and where this map came from.
 *
 * Two copies of that drifted the moment either was improved. The panel's frame
 * landed on one screen a round before the other; the error boundary landed on
 * one and not the other at all. **A reader who has learned one of these screens
 * has learned the other**, and that is a promise about the code as much as
 * about the picture: there is one screen here, and two things put into it.
 *
 * **One band at the foot, never three** *(2026-09-22, Kent: the foot was "the
 * triple nested bottom bar … somewhat garish")*. The foot used to be three boxes
 * stacked on one another, each with its own hairline and its own raised
 * background: the last-key line, the run strip, and the provenance sentence. Two
 * of the three were about the map rather than about the run, and none of them
 * said which of the three a reader should be looking at. They are one band now,
 * with at most two rows in every state:
 *
 * 1. **the run's line** — the state as one word, the run's own sentence, and the
 *    seconds since anything last arrived;
 * 2. **under it, one row and one row only** — while a live run is open, the two
 *    quiet lines saying what the model is doing this second; otherwise the quiet
 *    grey row that carries the last key pressed and where this map came from.
 *
 * What a reader needs at the foot, at a glance, is four things: what the run is
 * doing, how long it has been since anything happened, what the last key they
 * pressed did, and where this map came from. Three of the four are quiet and one
 * is not, which is what the two rows are for.
 *
 * **And the panel is one press away.** It folds, from a control at the head of
 * its own names and from `P`, and when it is folded a tab at the edge of the map
 * brings it back. It still never opens over the map.
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
import { Chevron, THE_PANEL_BESIDE_THE_MAP } from "./PanelSwitch";
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
  /** What the last keystroke did, in the quiet row at the foot. */
  readonly status: string;
  /** The panel beside the map, or nothing when the reader has folded it away. */
  readonly panel: ReactNode;
  /**
   * Bring the folded panel back.
   *
   * It is the tab at the edge of the map, which is the only control on screen
   * while the panel is away — and it is the same act as pressing `P`.
   */
  readonly onShowPanel: () => void;
  /**
   * What stands at the head of the panel and never scrolls: the row of names
   * saying which panels this screen has and which one is on the glass.
   *
   * It is **outside** the box that scrolls, and that is the whole point of it
   * being a slot of its own: a way back to the other panels that scrolls off the
   * top is a way back a reader cannot find. It is also outside the frame that
   * draws the *there is more this way* rules, so the rule that says *more above*
   * still marks the top of what scrolls rather than the top of the names.
   */
  readonly panelHead?: ReactNode;
  /**
   * The thing on screen that names what is in the panel right now, by its
   * identifier.
   *
   * Given, the panel is one of several and says so: it takes the part a screen
   * reader reads as the panel of a chosen name, and the name is read from that
   * label rather than written twice. Left out, the panel is the only one there
   * is and carries its own plain name.
   */
  readonly panelNamedBy?: string;
  /**
   * The one strip that says what is happening to this map, or nothing when
   * there is nothing to say.
   *
   * Each screen builds its own, because only the screen knows what state the
   * map is in — but both build it out of the same component, and inside it is
   * the one polite region this frame used to own. There is no state in which
   * the only account of what a run is doing is spoken.
   */
  readonly strip: ReactNode;
  /** Where every number on this map came from, and anything still on its way. */
  readonly origin: ReactNode;
  /**
   * True while the strip is printing what the model is doing this second.
   *
   * Those two lines are the band's second row, and the band has two rows. So the
   * quiet grey row — the last key pressed, and where this map came from — stands
   * down for as long as a live run has something to say, and comes back the
   * moment it stops. **Only the screen knows**: the frame is handed the strip
   * already built and cannot see inside it.
   */
  readonly activityShowing?: boolean;
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
  onShowPanel,
  panelHead,
  panelNamedBy,
  strip,
  origin,
  activityShowing = false,
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
          </div>

          {panel === null ? (
            // **The way back to a folded panel, at the edge it went behind.**
            // A panel that can be put away with no visible way to bring it back
            // is a panel a reader loses; `P` is a key you have to have read the
            // sheet to know. So the column leaves a tab of its own width behind
            // it, carrying the panel's own word and a chevron pointing the way
            // it will come from.
            <button
              className="dock-tab"
              type="button"
              aria-label="Show the panel beside the map"
              aria-expanded={false}
              aria-controls={THE_PANEL_BESIDE_THE_MAP}
              onClick={onShowPanel}
            >
              <Chevron pointing="left" />
              <span className="dock-tab__word">panel</span>
            </button>
          ) : (
            // The names at the head, then the panel itself. The head is a box
            // of its own outside the scroller so that it cannot scroll away,
            // and outside the frame below so that the frame's rules still mark
            // the edges of the thing that scrolls.
            <div className="dock-column">
              {panelHead}
              {/* The frame holds the two rules that say there is more above or
                  more below. They are drawn on it rather than inside the panel
                  so that turning one on cannot change the scroll height it was
                  worked out from — see `useTheEdges.ts`. */}
              <div className="dock-frame" {...edgeMarks(edges)}>
                <aside
                  className="dock"
                  id={THE_PANEL_BESIDE_THE_MAP}
                  ref={scroller}
                  {...(panelNamedBy === undefined
                    ? { "aria-label": "The panel beside the map" }
                    : { role: "tabpanel", "aria-labelledby": panelNamedBy })}
                >
                  {panel}
                </aside>
              </div>
            </div>
          )}
        </div>

        {/* **The one band at the foot.** What is happening to this map, with
            the polite line inside it, and under it exactly one quiet row.
            There is no spinner here and never will be: a spinner says "wait"
            without saying what for, and this says what is being waited for and
            how long it has been waited for. */}
        <div className="map-foot">
          {strip}

          {/* The quiet row: what the last keystroke did, and where every number
              on this map came from. It stands down while a live run is saying
              what the model is doing, because that is the same row. */}
          {activityShowing ? null : (
            <div className="map-foot__row map-foot__quiet">
              <p className="map-status">
                <span className="map-status__mark">last key</span>
                {/* One line, cut with an ellipsis when it runs past its share of
                    the row. It is a glance rather than a read — the useful words
                    are the first ones, and a keystroke's account wrapping four
                    times beside the provenance would make the quiet row the
                    tallest thing at the foot. */}
                <span className="map-status__said">{status}</span>
              </p>
              <div className="map-origin">{origin}</div>
            </div>
          )}
        </div>
      </IfTheScreenBreaks>
    </main>
  );
}
