/**
 * Whatever a request threw, as one sentence a reader can act on.
 *
 * One module, because three screens print it and a fourth speaks it, and a
 * sentence written four times is four sentences the day one of them is improved.
 *
 * **Never a stack trace, never a status code on its own, never a class name.**
 * Those belong in the browser's own console. What reaches the page is the one
 * sentence the thrower wrote, and — when it wrote none — a plain admission that
 * there is nothing to pass on, which is better than a reader being shown
 * `[object Object]` and told it is a reason.
 */

/**
 * Say what went wrong, in words.
 *
 * @param reason Whatever was thrown or rejected with.
 */
export function asOneSentence(reason: unknown): string {
  return reason instanceof Error ? reason.message : "The reason was not recorded.";
}
