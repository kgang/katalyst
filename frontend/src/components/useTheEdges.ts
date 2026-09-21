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
 */

import { useEffect, useRef, useState } from "react";

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
 * reasons: the reader scrolls it, a claim arrives and makes it taller, and the
 * window is resized and makes it shorter. Missing any one of them leaves a rule
 * drawn at an edge with nothing beyond it, which is the panel claiming something
 * a reader can check in one gesture.
 *
 * @returns The ref to put on the panel, and which of its edges have more beyond
 *   them. A panel scrolls in one direction here, so the two sideways edges are
 *   always false.
 */
export function useTheEdgesOfThePanel(): {
  panel: React.RefObject<HTMLElement | null>;
  edges: Edges;
} {
  const panel = useRef<HTMLElement | null>(null);
  const [edges, setEdges] = useState<Edges>(NOTHING_BEYOND);

  useEffect(() => {
    const it = panel.current;
    if (it === null) {
      return;
    }
    const measure = (): void => {
      // A pixel of slack, because a panel scrolled to its very end lands a
      // fraction short of its own height often enough to matter.
      const above = it.scrollTop > 1;
      const below = it.scrollTop + it.clientHeight < it.scrollHeight - 1;
      setEdges((was) =>
        was.above === above && was.below === below ? was : { ...NOTHING_BEYOND, above, below },
      );
    };
    measure();
    it.addEventListener("scroll", measure, { passive: true });
    // Watching a box change size is the browser's own job, and a page that
    // cannot do it — a simulated one in a test — still gets the scrolling half
    // rather than nothing at all.
    const watching =
      typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(measure);
    watching?.observe(it);
    for (const child of it.children) {
      watching?.observe(child);
    }
    return () => {
      it.removeEventListener("scroll", measure);
      watching?.disconnect();
    };
  });

  return { panel, edges };
}
