/**
 * The map as a nested list.
 *
 * Not a fallback — the same world, read rather than drawn. It is marked up as a
 * tree, which is what a screen reader needs to announce levels and let you walk
 * them with the arrow keys, and every item is one sentence that says everything
 * the picture says: the claim, its numbers or the reason there are none, what
 * causes it, what it causes, and how it will be settled.
 *
 * It is built **from the world, never from what is painted**. A claim sitting
 * behind a "+4 more" tile still has an item here — which is exactly why
 * activating one of those tiles opens this view, filtered to that column: the
 * claims are already listed, and the tile just points at them.
 *
 * **And when there is nothing to list, it says so** *(2026-09-22)*. On a map
 * that is still being built the list drew its heading and then stopped, which
 * reads as a list that is broken rather than as a map that has not started. An
 * empty list is a fact about the run, and this one states it.
 */

import { flatten, type OutlineItem } from "../a11y/sentences";
import "./outline.css";

/**
 * What the list says when it has nothing to list.
 *
 * One sentence, and it says *yet*, because on the one screen this happens on
 * the claims are on their way. It promises nothing about how long: a map being
 * built waits on a model call, and this view has no way to know how long that
 * is and must not guess.
 */
export const NOTHING_YET = "Nothing has arrived yet. Each claim takes its place here as it does.";

/** What the outline needs to draw itself. */
export interface OutlineProps {
  /** The map, as a tree. */
  readonly items: readonly OutlineItem[];
  /** Which claims to show. Left out, all of them. */
  readonly only?: ReadonlySet<string>;
  /** What the filter is, in words, when there is one. */
  readonly filter?: string;
  /** Called when the reader picks a claim, so the map can follow. */
  readonly onPick: (id: string) => void;
  /** Which claim the map is on, so the list and the picture agree. */
  readonly focused: string | null;
}

/** The map, read rather than drawn. */
export function Outline({ items, only, filter, onPick, focused }: OutlineProps) {
  const shown = flatten(items).filter((item) => only === undefined || only.has(item.id));

  return (
    <section className="outline" aria-label="The map as a list">
      <h2 className="outline__heading">The map as a list</h2>
      <p className="outline__note">
        {filter ?? "Every claim on the map, each one caused by the one above it."}
      </p>
      {/* Nothing to list is said in words rather than drawn as an empty box.
          An empty tree announces itself to a screen reader as a list with no
          items in it, which is the one reading this view must never give: on a
          map being built there is nothing here *yet*, and that is a fact about
          the run rather than about the list. */}
      {shown.length === 0 ? (
        <p className="outline__empty">{NOTHING_YET}</p>
      ) : (
        /* A flat list of items carrying their own depth. `role="tree"` with
           `aria-level` is the markup a screen reader reads as a hierarchy, and it
           keeps working when the list is filtered to one column — a nested list
           filtered to one column would lose its own nesting. No HTML element
           means a tree, so the roles are spelled out on a list, which is what this
           honestly is. */
        /* biome-ignore lint/a11y/noNoninteractiveElementToInteractiveRole: a tree of claims is a list of claims, and the list element is the honest thing to hang the role on — the alternative is a bare div pretending to be a list. */
        <ul className="outline__list" role="tree">
          {shown.map((item) => (
            <li
              className="outline__item"
              key={item.id}
              role="treeitem"
              tabIndex={-1}
              aria-level={item.level}
              aria-selected={focused === item.id}
              data-level={Math.min(item.level, 5)}
            >
              <button className="outline__line" type="button" onClick={() => onPick(item.id)}>
                <span className="outline__sentence">{item.sentence}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
