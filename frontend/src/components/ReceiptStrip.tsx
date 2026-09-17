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
 * The same nine lines are drawn in two places — here, beside a growing map, and
 * in the panel's own section for the run that produced the map. They are one
 * component so the two cannot drift.
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
function asMeasurement(value: number, most: number): string {
  return value.toLocaleString("en-GB", { minimumFractionDigits: 1, maximumFractionDigits: most });
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
 * The nine readings a receipt carries, in the order they are printed.
 *
 * Nine, always, and none of them derived. A receipt with a field left out is a
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
    { label: "cost", reading: `$${asMeasurement(receipt.dollars, 4)}`, field: "dollars" },
    { label: "took", reading: `${asMeasurement(receipt.seconds, 1)}s`, field: "seconds" },
    { label: "mode", reading: modeLine(receipt), field: "mode" },
  ];
}

/**
 * What the mode line says.
 *
 * In a replay it names the day the recording was made and the prompt it was made
 * against, because those are the two things that say which run this is a picture
 * of. Live, there is no recording and no day, so it says only what it is.
 */
function modeLine(receipt: Receipt): string {
  if (receipt.mode === "live") {
    return `live · prompt ${receipt.prompt_hash.slice(0, 8)}`;
  }
  const day = receipt.recording_date;
  return day === null
    ? `replay · prompt ${receipt.prompt_hash.slice(0, 8)}`
    : `replay · recorded ${day} · prompt ${receipt.prompt_hash.slice(0, 8)}`;
}

/** What the strip needs to draw itself. */
export interface ReceiptStripProps {
  /** The receipt event, exactly as it arrived. */
  readonly receipt: Receipt;
  /** What this heading is called, so the panel and the strip can title it their own way. */
  readonly heading?: string;
  /** Open the working of the run. Left out, the strip is read-only. */
  readonly onOpen?: () => void;
}

/** The nine labelled readings, and nothing else. */
export function ReceiptLines({ receipt }: { receipt: Receipt }) {
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
export function ReceiptStrip({ receipt, heading = "This generation", onOpen }: ReceiptStripProps) {
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
      {onOpen === undefined ? null : (
        <button className="receipt-strip__open" type="button" onClick={onOpen}>
          Read the working of this run
        </button>
      )}
    </section>
  );
}
