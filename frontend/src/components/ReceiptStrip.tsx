/**
 * What a generation cost, printed exactly as the engine sent it.
 *
 * **Every line is a field.** This file does not add the two token counts
 * together, does not work a cost out of a token count and a price, and does not
 * time anything. The price table lives in one module on the server with the day
 * it was read beside it, and the dollars here came from there.
 *
 * **Web searches are a row of their own** because they are billed apart from
 * tokens: without that row, the cost is a number a reader could check against the
 * token counts and find wrong.
 *
 * **Before the receipt arrives there is no strip.** No running estimate, no
 * ticking cost, no progress bar. A cost nobody has totalled is a number nobody
 * computed, and a percentage nobody computed is a number nobody computed wearing
 * a progress bar.
 *
 * **The two-significant-figures rule is about likelihoods.** A token count, a
 * call count, a duration and a dollar figure are counts and measurements: they
 * are printed whole, in the number face with fixed-width digits, and they carry
 * no range because nothing sampled them.
 *
 * **The way into the working is not on this strip.** It was — a link at the
 * foot of it — and that left a run whose stream was cut with no way in at all,
 * because a cut run never gets a receipt and so never got the link. The control
 * is a row of its own in the panel now, there from the moment there is a
 * generation. Every number here is still one press from its why; the press is
 * the row under them rather than a link inside them, and it is there before the
 * numbers are.
 *
 * **The ten lines are drawn in exactly one place, and this is it.** They used
 * to be drawn twice, one above the other in a 320-pixel column: here, and again
 * in the panel's section for the run. Two copies of one cost is two costs to a
 * reader scrolling past them, and the second was the one nobody could point at.
 * The panel's section now holds the *working* — the transcript, the prompt's
 * fingerprint, the seed — and points here for what it cost.
 */

import type { Receipt } from "../stream/events";
import "./receiptStrip.css";

/** A whole count, spaced in threes so a six-figure token count can be read. */
function asCount(value: number): string {
  return value.toLocaleString("en-GB").replace(/,/g, " ");
}

/**
 * A measurement, rounded for the page and never for the arithmetic.
 *
 * Rounding here is a display decision made at the moment of printing, the same
 * decision a belief chip makes — the value itself is carried at whatever
 * precision it arrived with and nothing downstream reads this string.
 */
function asMeasurement(value: number, least: number, most: number): string {
  return value.toLocaleString("en-GB", {
    minimumFractionDigits: least,
    maximumFractionDigits: most,
  });
}

/**
 * **Money, in the two places money has.**
 *
 * It printed up to four — `$0.6132` — which is the same mistake the two
 * significant figures rule exists to stop, in the one place a reader is most
 * likely to compare two runs: four places read as a measured figure when the
 * fourth of them is a rounding of a price table. Dollars are dollars, and
 * dollars have two places.
 *
 * **And a guard word exactly when it is true** (K2). A run that spent nothing
 * prints `$0.00`, which is a computed zero and reads as one. A run that spent
 * something and less than a penny prints `<$0.01`, because `$0.00` there would
 * be the strip saying a run was free when it was not — and the `<` is the whole
 * of the difference between a figure and a bound.
 *
 * One function, used by both strips, so a generation's cost and an insert's
 * cannot come to be written two ways.
 *
 * @param dollars What the run spent, at the price table the server shipped.
 */
export function asMoney(dollars: number): string {
  if (dollars > 0 && dollars < 0.01) {
    return "<$0.01";
  }
  return `$${asMeasurement(dollars, 2, 2)}`;
}

/** One labelled reading off the receipt. */
interface Line {
  /** What it is, in the reader's words. */
  readonly label: string;
  /** The reading, already turned into the characters that go on screen. */
  readonly reading: string;
  /** The name of the field it came from, for a reader asking where it is from. */
  readonly field: string;
}

/**
 * The ten readings a receipt carries, in the order they are printed.
 *
 * Ten, always, and none of them derived. A receipt with a field left out is a
 * receipt somebody would have to reconstruct.
 *
 * @param receipt The receipt event, exactly as it arrived.
 */
export function receiptLines(receipt: Receipt): readonly Line[] {
  return [
    { label: "model", reading: receipt.model, field: "model" },
    { label: "calls", reading: asCount(receipt.calls), field: "calls" },
    { label: "tokens in", reading: asCount(receipt.input_tokens), field: "input_tokens" },
    { label: "tokens out", reading: asCount(receipt.output_tokens), field: "output_tokens" },
    {
      label: "read from cache",
      reading: asCount(receipt.cache_read_tokens),
      field: "cache_read_tokens",
    },
    { label: "web searches", reading: asCount(receipt.searches), field: "searches" },
    // Money prints as money: two places, always, with `<$0.01` for an amount
    // above nothing and below a cent — a guard word used exactly when it is
    // true, and never in place of a figure that exists.
    { label: "cost", reading: asMoney(receipt.dollars), field: "dollars" },
    { label: "took", reading: `${asMeasurement(receipt.seconds, 1, 1)}s`, field: "seconds" },
    // How hard the model was asked to try, in the word the service takes.
    // **Two maps of the same sentence can differ because of this and for no
    // other reason**, so it is a reading rather than a footnote: a recording is
    // made rich and a live run is made fast, and a reader comparing one with
    // the other has to be able to see which they are looking at.
    { label: "how hard the model tried", reading: receipt.effort, field: "effort" },
    { label: "mode", reading: modeLine(receipt), field: "mode" },
  ];
}

/**
 * What the mode line says: whether the run was live or a replay, and on a replay
 * the day the recording was made. Nothing else.
 *
 * **The prompt's fingerprint used to be here and is not any more.** It read
 * `prompt 93f85980` — eight characters of hex on a strip whose whole promise is
 * that every reading is a field, with no label a reader could act on and, worse,
 * cut here from the whole the engine sent. A browser that trims an identifier
 * has derived something (INV-workbench.72: none of the ten readings is
 * derived), and eight characters of a hash are not a fingerprint — they are a
 * fingerprint somebody could not check. It is printed whole, with a sentence
 * saying what it is for, in the panel's view of the run.
 */
function modeLine(receipt: Receipt): string {
  if (receipt.mode === "live") {
    return "live";
  }
  const day = receipt.recording_date;
  return day === null ? "replay" : `replay · recorded ${day}`;
}

/** What the strip needs to draw itself. */
export interface ReceiptStripProps {
  /** The receipt event, exactly as it arrived. */
  readonly receipt: Receipt;
  /** What this heading is called, so the panel and the strip can title it their own way. */
  readonly heading?: string;
}

/** The ten labelled readings, and nothing else. */
function ReceiptLines({ receipt }: { receipt: Receipt }) {
  return (
    <dl className="receipt-strip__lines">
      {receiptLines(receipt).map((line) => (
        <div className="receipt-strip__line" key={line.field} data-field={line.field}>
          <dt className="receipt-strip__label">{line.label}</dt>
          <dd className="receipt-strip__reading">{line.reading}</dd>
        </div>
      ))}
    </dl>
  );
}

/** What the run cost, beside the map it produced. */
export function ReceiptStrip({ receipt, heading = "This generation" }: ReceiptStripProps) {
  return (
    <section className="receipt-strip" aria-label="What this generation cost">
      <h3 className="receipt-strip__heading">{heading}</h3>
      <ReceiptLines receipt={receipt} />
      {receipt.mode === "replay" ? (
        <p className="receipt-strip__note">
          This run played a recording back, so nothing was called and nothing was spent. That zero
          is a zero somebody worked out, printed rather than hidden.
        </p>
      ) : null}
    </section>
  );
}
