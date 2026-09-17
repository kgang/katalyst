/**
 * How this product writes a day: `Oct 1`.
 *
 * Read in the map's own reckoning rather than in the reader's time zone,
 * because a claim settled on the first of November is settled on the first of
 * November wherever the reader happens to be sitting — and because a supposition
 * dated by the reader's clock would make the same map read differently in two
 * places.
 */

/**
 * Print a day the way the map prints one.
 *
 * @param isoDate A day as the server writes one: `2026-10-01`.
 * @returns The day in words, such as `Oct 1`. A day it cannot read comes back
 *   exactly as it arrived, rather than as a guess.
 */
export function toDay(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return isoDate;
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

/**
 * A claim's own words, ready to be quoted inside a sentence.
 *
 * Two changes and no others. The full stop at the end goes, because the quote
 * sits inside a line rather than ending one. And an article at the front — *A*,
 * *An*, *The* — is lowercased, because that is the one word whose capital letter
 * belongs to the claim's own sentence rather than to the words themselves.
 * Everything else keeps the case the map gave it, so *Brent*, *OPEC+* and
 * *Hormuz* stay as they are.
 *
 * @param claim The claim in the map's own words.
 */
export function asQuoted(claim: string): string {
  const withoutStop = claim.replace(/\.$/, "");
  const [first = "", ...rest] = withoutStop.split(" ");
  if (["A", "An", "The"].includes(first)) {
    return [first.toLowerCase(), ...rest].join(" ");
  }
  return withoutStop;
}
