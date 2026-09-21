/**
 * **The rule for an edge with more beyond it, written once.**
 *
 * Two boxes on the map screen hold more than they can show: the panel beside the
 * map, which scrolls, and the stage the map sits on, which pans. A reader has to
 * be able to tell a control that is not there from a control that is merely
 * below the fold, and a claim that does not exist from a claim that is off the
 * left edge. A scrollbar cannot tell them either thing: on a Mac it is an
 * overlay that fades in on a gesture, so it speaks only to somebody who is
 * already scrolling, and the map has no scrollbar at all.
 *
 * So: **a two-pixel rule in `--text-muted` sits at whichever edge has more
 * beyond it, and at no edge that has not.** A line rather than a shadow, like
 * every other separation in this product. It is drawn in `app.css` from the
 * `data-more-*` attributes the two boxes write about themselves, and both boxes
 * write them with the words below so that the two cannot drift.
 *
 * The measuring differs because the two boxes are different — one is scrolled
 * and one is panned — and the rule and its drawing do not.
 *
 * **Two hard rules about the measuring, both learned the same way.**
 *
 * *The answer must not change the question.* The rules are drawn on a frame
 * around the panel rather than inside it, so that turning one on cannot change
 * the scroll height it was worked out from. A measurement that changes the thing
 * measured is a loop, and a browser ends a size-observation loop by abandoning
 * the rest of that frame's observations.
 *
 * *And nothing is observed twice.* Asking the browser to watch a box it is
 * already watching makes it re-deliver that box's size, so re-watching the panel
 * and its five sections on every render fills a frame's budget of observations
 * with answers nobody needed. The budget is shared with the drawing library,
 * which uses it to measure tiles — and it draws nothing it has not measured.
 */

import { useCallback, useEffect, useRef, useState } from "react";

/** Which edges of a box have more beyond them. */
export interface Edges {
  readonly above: boolean;
  readonly below: boolean;
  readonly left: boolean;
  readonly right: boolean;
}

/** Nothing beyond any edge: what a box that fits says about itself. */
export const NOTHING_BEYOND: Edges = { above: false, below: false, left: false, right: false };

/**
 * The attributes a box writes about itself, in the spelling `app.css` reads.
 *
 * @param edges Which edges have more beyond them.
 */
export function edgeMarks(edges: Edges): Record<string, string> {
  return {
    "data-more-above": edges.above ? "yes" : "no",
    "data-more-below": edges.below ? "yes" : "no",
    "data-more-left": edges.left ? "yes" : "no",
    "data-more-right": edges.right ? "yes" : "no",
  };
}

/**
 * A scrolling panel, measuring itself.
 *
 * It is watched three ways because the panel changes for three different
 * reasons: the reader scrolls it, a claim arrives and makes a section taller,
 * and the window is resized and makes the panel shorter. Missing any one of them
 * leaves a rule drawn at an edge with nothing beyond it, which is the panel
 * claiming something a reader can check in one gesture.
 *
 * The sections are watched as well as the panel, because a section growing
 * inside a panel that stays exactly the same size is the commonest of the three
 * and the only one the panel's own box does not report.
 *
 * @returns The ref to put on the scrolling panel, and which of its edges have
 *   more beyond them — for the frame around it to draw. A panel scrolls in one
 *   direction here, so the two sideways edges are always false.
 */
export function useTheEdgesOfThePanel(): {
  panel: React.RefObject<HTMLElement | null>;
  edges: Edges;
} {
  const panel = useRef<HTMLElement | null>(null);
  const [edges, setEdges] = useState<Edges>(NOTHING_BEYOND);

  /**
   * Read how far the panel is scrolled and how much it holds.
   *
   * Written once and never rebuilt, so that the one observer below can be built
   * once and never rebuilt either.
   */
  const measure = useCallback((): void => {
    const it = panel.current;
    if (it === null) {
      return;
    }
    // A pixel of slack, because a panel scrolled to its very end lands a
    // fraction short of its own height often enough to matter.
    const above = it.scrollTop > 1;
    const below = it.scrollTop + it.clientHeight < it.scrollHeight - 1;
    setEdges((was) =>
      was.above === above && was.below === below ? was : { ...NOTHING_BEYOND, above, below },
    );
  }, []);

  /**
   * One observer for the life of the screen, **and the list of what it watches
   * lives exactly as long as it does.**
   *
   * The two used to be separate — the observer in state, the list in a ref —
   * and they came apart in the one mode this product is developed and reviewed
   * in. React's strict mode mounts every screen, unmounts it and mounts it
   * again; the unmount really does disconnect the observer, while a ref
   * survives it. The effect below then looked at a list that said every box was
   * already watched, watched none of them, and the panel measured itself once
   * and never again: a section could grow past the fold with no rule to say so.
   * Holding them in one object means the disconnect takes the list with it.
   */
  const [watcher] = useState(() => {
    const watched = new Set<Element>();
    return {
      watched,
      observer: typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => measure()),
    };
  });
  const watching = watcher.observer;

  // Which boxes are being watched is settled after every render, because the
  // panel's sections come and go — but a box already being watched is left
  // exactly as it is.
  useEffect(() => {
    const it = panel.current;
    if (it === null || watching === null) {
      return;
    }
    const wanted = new Set<Element>([it, ...it.children]);
    for (const box of watcher.watched) {
      if (!wanted.has(box)) {
        watching.unobserve(box);
        watcher.watched.delete(box);
      }
    }
    for (const box of wanted) {
      if (!watcher.watched.has(box)) {
        watching.observe(box);
        watcher.watched.add(box);
      }
    }
  });

  // The reader scrolling it, and the first reading of all.
  useEffect(() => {
    const it = panel.current;
    if (it === null) {
      return;
    }
    measure();
    it.addEventListener("scroll", measure, { passive: true });
    return () => it.removeEventListener("scroll", measure);
  }, [measure]);

  // Going away takes the list with it, so a screen that comes back watches
  // everything again from nothing.
  useEffect(
    () => () => {
      watcher.observer?.disconnect();
      watcher.watched.clear();
    },
    [watcher],
  );

  return { panel, edges };
}
