/**
 * One generation, asked for once, watched by whoever is on screen.
 *
 * **The press is what asks.** Not a hook, not an effect, not a render: the
 * reader pressing a card or a button is what makes the request, and this module
 * is what that press creates. The reason is hard rather than stylistic — React's
 * development mode deliberately mounts every screen, unmounts it and mounts it
 * again, so an effect that asks for a map asks for two, and *"never retry, a
 * generation that ran twice would spend twice"* is broken before the first
 * reviewer ever opens the app. An event fires once. There is nothing to guard,
 * nothing to de-duplicate and no window in which a second request can be made,
 * because the only code that makes one runs inside a click.
 *
 * So the shape is: a press builds a run; the run reads the stream and folds it;
 * the screen watches the run. The screen can mount, unmount and mount again as
 * often as React likes and the run neither notices nor cares.
 *
 * **Letting go is an event too.** The reader pressing *Back to the launchpad* is
 * what stops the spending — the route checks whether the client is still there
 * before its next model call — and it is the only way off this screen. An
 * unmount is not used for it, for the same reason a mount is not used to start:
 * a development-mode unmount would stop a run nobody left.
 *
 * **The stream ending is not the run ending.** A body that stops without a
 * terminator is a dropped connection, and this is where that is noticed, because
 * this is the only thing that can notice it — the events themselves never
 * mention it.
 */

import { theOpeningLine, whatChanged } from "../a11y/growth";
import type { Asked } from "../components/InputBar";
import { asOneSentence } from "../world/failures";
import type { HowToAsk } from "./generate";
import { generate } from "./generate";
import type { Growth } from "./growth";
import { fold, theStreamEnded, waitingFor } from "./growth";

/** Everything a screen watching a run needs, in one object that is replaced whole. */
export interface WhereItHasGot {
  /** The map as far as it has been built, and everything else known about the run. */
  readonly growth: Growth;
  /**
   * The one line a reader who cannot see the map hears, about whatever just
   * changed.
   *
   * It is held here rather than worked out while rendering because it is a fact
   * about an *event* — what the last one did — and a render has no way of
   * knowing what the state before it was.
   */
  readonly saying: string;
}

/** One generation, running or finished, and the ways to watch it and to stop it. */
export interface TheRun {
  /** What the reader asked for, kept so the same question can be asked again. */
  readonly asked: Asked;
  /**
   * A name for this run on this screen, so that asking again draws a new screen
   * rather than a new map inside the old one's selection and focus.
   *
   * It names a press, not a generation: the engine's own name for the run
   * arrives on the first event and is what everything else uses.
   */
  readonly press: string;
  /** Where it has got to, right now. */
  now(): WhereItHasGot;
  /** Be told whenever that changes. Returns the way to stop being told. */
  watch(told: () => void): () => void;
  /** The reader walked away. Stop reading, which is what stops the spending. */
  letGo(): void;
}

/**
 * How many presses this page has answered.
 *
 * It names presses so two of them can be told apart. Nothing on the map is
 * counted here and nothing derived from it is ever drawn.
 */
let presses = 0;

/**
 * Turn what the reader asked for into what the route takes.
 *
 * *"I don't know"* sends no likelihood at all — not a half, not a wide band, not
 * a null — because a reader who has not said what they think has not said what
 * they think.
 *
 * @param asked The sentence, the destination and the reader's own likelihood.
 */
function theRequest(asked: Asked) {
  return {
    hypothesis: asked.hypothesis,
    ...(asked.target === null ? {} : { target: asked.target }),
    ...(asked.belief === null ? {} : { user_belief: asked.belief }),
  };
}

/**
 * Ask for a map, starting now.
 *
 * The request goes the moment this is called, which is inside the press that
 * called it. Nothing waits for a render.
 *
 * @param asked What the reader typed.
 * @param how Where to make the request. A test hands in its own.
 */
export function askForAMap(asked: Asked, how: HowToAsk = {}): TheRun {
  presses += 1;
  const opening = waitingFor(asked.hypothesis, asked.target);
  let where: WhereItHasGot = { growth: opening, saying: theOpeningLine(opening) };
  const watchers = new Set<() => void>();
  const stop = new AbortController();
  let letGone = false;

  /** Move to a new state and tell everybody watching. */
  const moveTo = (growth: Growth): void => {
    const said = whatChanged(where.growth, growth);
    where = { growth, saying: said === "" ? where.saying : said };
    for (const told of watchers) {
      told();
    }
  };

  const read = async (): Promise<void> => {
    for await (const event of generate(theRequest(asked), { ...how, signal: stop.signal })) {
      moveTo(fold(where.growth, event));
    }
    // The body ended. If nothing on it said the run was over, the connection
    // went rather than the run finishing, and the rectangles come down.
    moveTo(theStreamEnded(where.growth));
  };

  read().catch((failure: unknown) => {
    if (letGone) {
      // The reader walked away and this is the abort they caused. Nothing broke.
      return;
    }
    // Never reaching the route at all is the one thing that is not an event:
    // there is no stream to read and nothing to draw, so it is folded in by hand
    // as the sentence the failure arrived with.
    moveTo(fold(where.growth, { event: "failed", message: asOneSentence(failure) }));
  });

  return {
    asked,
    press: `press ${presses}`,
    now: () => where,
    watch: (told: () => void) => {
      watchers.add(told);
      return () => {
        watchers.delete(told);
      };
    },
    letGo: () => {
      letGone = true;
      stop.abort();
    },
  };
}
