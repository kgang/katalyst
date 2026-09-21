/**
 * How a claim or an arrow is named on screen, which is never by its identifier.
 *
 * **The rule.** A claim's identifier is minted by the engine and is a
 * twenty-six-character string nobody can read, remember or say out loud. On the
 * stored example the identifiers happen to be `H`, `C` and `M1`, which read like
 * names — and that accident let them onto the screen in a dozen places. On a
 * generated map the same code prints `01M2QYMMJYA27CAZ91N8VPA6NK`, which is not a
 * name but a piece of plumbing, and a reader who sees it learns nothing and
 * trusts the tool less.
 *
 * So every surface names a claim by its **words**, and where a surface needs
 * something short — a column of handles beside a list, a route read at a glance —
 * it uses the thing's **place in that list**, which is a fact about the list and
 * is readable.
 *
 * The same rule is already the validator's: its sentences name the claim by its
 * words, never by its identifier. This file is that rule on our side of the wire.
 */

/** What is said where a claim would be named and this map does not hold it. */
export const NOT_ON_THIS_MAP = "a claim this map is not drawing";

/** The first twelve counts in words. Past that a numeral reads more clearly. */
const COUNTS = [
  "no",
  "one",
  "two",
  "three",
  "four",
  "five",
  "six",
  "seven",
  "eight",
  "nine",
  "ten",
  "eleven",
  "twelve",
];

/** A count, in the words a sentence would use. */
export function countInWords(count: number): string {
  return COUNTS[count] ?? `${count}`;
}

/**
 * How many characters of a claim are enough to know which claim it is.
 *
 * Long enough that two claims on one map are told apart — the real run's ten
 * claims differ inside their first forty characters — and short enough to sit on
 * one line beside a label.
 */
const ENOUGH_TO_KNOW_IT_BY = 44;

/**
 * A claim in the fewest words that still say which claim it is.
 *
 * Cut at a word boundary and closed with an ellipsis, never mid-word, which is
 * the same rule a tile's own wrapping obeys. A claim short enough already is
 * handed back whole.
 *
 * @param claim The claim in its own words.
 */
export function inFewWords(claim: string): string {
  const tidy = claim.trim();
  if (tidy.length <= ENOUGH_TO_KNOW_IT_BY) {
    return tidy;
  }
  const cut = tidy.slice(0, ENOUGH_TO_KNOW_IT_BY);
  const lastSpace = cut.lastIndexOf(" ");
  return `${(lastSpace > 0 ? cut.slice(0, lastSpace) : cut).replace(/[,;:.]$/, "")}…`;
}
