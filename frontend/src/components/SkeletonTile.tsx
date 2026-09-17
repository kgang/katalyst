/**
 * A reserved rectangle standing where a claim is about to arrive.
 *
 * **Not a shimmer, not a pulse, not a grey bar sliding across a card.** A space
 * held open, at the size and in the place the thing being waited for will take.
 * An animated placeholder is a tool performing busyness at a reader who is
 * waiting on a model call that takes half a minute; a held rectangle is a tool
 * saying where the next thing goes.
 *
 * **It is never a claim.** It has no identifier on the map — its name is a box's
 * name — it never reaches the network, it carries no likelihood, and there is no
 * number on it to be a number nobody computed, because there is no number on it
 * at all. The only thing it prints is one line the stream carried: the reader's
 * own sentence, or the words of the open claim it hangs off.
 *
 * Its box is a tile's box: 280 pixels wide and 152 tall, which is the floor of a
 * tile's own clamped height — so when the claim lands, it lands at least as tall
 * as the rectangle that was held for it and nothing above it moves.
 */

import { TILE_MIN_HEIGHT, TILE_WIDTH } from "../graph/geometry";
import "./skeletonTile.css";

/** What a reserved rectangle needs to draw itself. */
export interface SkeletonTileProps {
  /**
   * The one line it carries — the reader's own sentence, or *one step on from
   * "…"*, quoting the open claim this rectangle hangs off.
   *
   * Every character of it came off the stream or out of the reader's own typing.
   * Nothing here composes a sentence.
   */
  readonly words: string;
}

/** One reserved rectangle. */
export function SkeletonTile({ words }: SkeletonTileProps) {
  return (
    <div
      className="skeleton-tile"
      style={{ width: `${TILE_WIDTH}px`, height: `${TILE_MIN_HEIGHT}px` }}
    >
      {/* What the box is, in real words rather than in a label written for a
          reader who cannot see it — so the two readings are the same reading,
          and neither can drift from the other. */}
      <span className="skeleton-tile__mark">held open</span>
      <p className="skeleton-tile__words">{words}</p>
    </div>
  );
}
