/**
 * The panel beside the map: why is this number what it is.
 *
 * Every number on this canvas has to be able to say where it came from. This is
 * where it says it.
 *
 * Select a claim and the panel gives you the whole of it: the full wording, how
 * it will be judged and by whom, the outside view it started from, all three
 * beliefs with their owners kept apart, the evidence, and — once there is an
 * engine — the decomposition that turns the number into an argument you can
 * disagree with line by line. Select an arrow and it gives you the mechanism in
 * a sentence, how hard it pushes read back in words, what kind of push it is,
 * how long it takes, what it does over time, its sources with the day each was
 * fetched, and where it came from.
 *
 * **It is one persistent side panel, and there are no pop-ups anywhere in this
 * product.** A dialog you have to dismiss steals the map you were reading, and
 * the map is what makes the detail mean anything. Selecting changes what is in
 * the panel; nothing ever opens over the canvas.
 *
 * **Where a value does not exist the panel says so in words, with a reason** —
 * never a blank, never a zero, never a stand-in. In this build that reason is
 * usually *"no engine yet"*, which is an honest sentence rather than a hole.
 *
 * **The panel never works a number out.** In particular it never adds up an
 * arrow's pushes to explain a likelihood, however tempting: the pieces are all
 * there — a prior, three pushes, a result — and the moment the canvas does its
 * own arithmetic there are two engines that disagree about half a point with
 * nobody able to say which is right.
 */

import type { ReactNode } from "react";
import {
  inDays,
  likelihoodStep,
  modeInWords,
  originInWords,
  pushAsNumber,
  pushInWords,
  shapeInWords,
} from "../graph/wires/encodings";
import type {
  BeliefOwner,
  ClaimKind,
  ClaimView,
  LinkView,
  Selection,
  Slot,
  WorldView,
} from "../world";
import { toReading, toTwoFigures } from "./BeliefChip";
import { OriginMark } from "./OriginMark";
import { PathBar } from "./PathBar";
import "./inspector.css";

/**
 * What the panel needs to draw itself.
 *
 * What it is open on is a `Selection` — the same shape, under the same name, as
 * what the map draws a ring around and what the keyboard is on. One thing with
 * one name: the panel, the map and the keyboard cannot disagree about what is
 * selected if there is only one word for it.
 */
export interface InspectorProps {
  /** The map and its numbers. */
  readonly world: WorldView;
  /** What is selected. */
  readonly selection: Selection;
}

/** What each kind of claim is called on screen. No underscores and no code names. */
const KIND_WORDS: Record<ClaimKind, string> = {
  hypothesis: "hypothesis",
  event: "event",
  market: "market",
  not_tradeable: "not tradeable",
};

/** The word each owner is called by. */
const OWNER_WORDS: Record<BeliefOwner, string> = {
  model: "model",
  user: "user",
  market: "market",
};

/** A heading inside the panel: small, spaced out, and never a border of its own. */
function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="inspector__section">
      <h3 className="inspector__heading">{title}</h3>
      {children}
    </section>
  );
}

/**
 * One belief, on one line: the owner, the reading, and a bounded bar behind the
 * number painted from the five-step brightness ramp.
 *
 * The bar is a glance and never a reading. The number and its range are printed
 * beside it every time, in the text colour, so nobody is ever asked to tell one
 * step of the ramp from the next by eye — and the number always clears four and
 * a half to one while the bar only has to clear three.
 *
 * The panel writes a belief on one line; the tile stacks it over three. Same
 * number, same rounding, same guard against printing a certainty; two shapes.
 */
function BeliefRow({ owner, slot }: { owner: BeliefOwner; slot: Slot }) {
  const reading = slot.reading;
  if (reading === undefined) {
    return (
      <div className="inspector__belief" data-owner={owner}>
        <span className="inspector__owner">{OWNER_WORDS[owner]}</span>
        <span className="inspector__words">{slot.absence.words}</span>
        <span className="inspector__reason inspector__belief-reason">{slot.absence.reason}</span>
      </div>
    );
  }
  return (
    <div className="inspector__belief" data-owner={owner}>
      <span className="inspector__owner">{OWNER_WORDS[owner]}</span>
      <span className="inspector__number">
        {/* A bounded bar — always the same size — whose brightness is one of
            five steps. The bar's *length* says nothing at all, deliberately:
            length would be a second channel carrying the meaning brightness
            already carries, and the number beside it is the reading anyway. */}
        <span className="inspector__bar" data-step={likelihoodStep(reading.p)} aria-hidden="true" />
        <span className="inspector__reading">{toReading(reading.p, reading.lo, reading.hi)}</span>
      </span>
    </div>
  );
}

/**
 * What the model's range is, and which of two sentences says so.
 *
 * The range means *how sure we are of the number*, not how much the world can
 * move — the second is already inside the likelihood, and a reader who confuses
 * them reads a wide band as a volatile event.
 *
 * Which sentence sits here is decided by one field and nothing else: whether the
 * world says how many versions of the map were run. **Present**, something
 * computed this number and the range is the spread across those versions.
 * **Absent** — as here, and everywhere in this build — nothing computed it, and
 * the range is what whoever wrote the number down said about how sure they were.
 * Printing "uncalibrated" over a stated range would claim an arithmetic that
 * never ran.
 *
 * The two sentences are the belief chip's, word for word, so the tile and the
 * panel cannot drift apart.
 */
function RangeNote({ world, claim }: { world: WorldView; claim: ClaimView }) {
  const model = claim.beliefs.model.reading;
  if (model === undefined) {
    return null;
  }
  if (world.versions === undefined) {
    return (
      <>
        <p className="inspector__label">stated range · not computed</p>
        <p className="inspector__reason">
          This range is stated, not computed — it says how sure the elicitation was. Nothing has
          worked this number through the map yet.
        </p>
      </>
    );
  }
  return (
    <>
      <p className="inspector__label">
        {`model interval, uncalibrated · how sure we are of ${toTwoFigures(model.p)} — not how much the world can move`}
      </p>
      <p className="inspector__reason">
        {`Across ${world.versions.toLocaleString("en-GB").replace(/,/g, " ")} versions of this map — each one a set of numbers this model would have stood behind — the answer landed between ${toTwoFigures(model.lo)} and ${toTwoFigures(model.hi)} eight times in ten. Nobody has checked whether that 8-in-10 holds up; no claim on this map has resolved yet.`}
      </p>

      {/* ---- The reserved band slot: "why is this band wide?" -------------
          Drawn only where the range above is a *computed* one, which is what
          the test just above asks. What goes in it is one sentence naming the
          claim whose own prior explains most of the band — "92% of this band is
          B's own prior; pin that down and the band goes from 29 points to 8" —
          and it is worked out from `range_shares` on the world, which the
          engine gets out of the same two thousand versions of the map it
          already runs, at no extra cost.

          **It ships in stack 06 and nothing draws it here.** Not a placeholder
          sentence, not a greyed-out example: a sentence naming a percentage
          nobody computed is a number nobody computed wearing words. The slot is
          left in place so the layout does not jump the day the sentence
          arrives, and this comment is where the next person finds out why it is
          empty. */}
      <div className="inspector__band-slot" />
    </>
  );
}

/** A claim, top to bottom. */
function ClaimDetail({ world, claim }: { world: WorldView; claim: ClaimView }) {
  const baseRate = claim.baseRate;

  return (
    <>
      <header className="inspector__head">
        <p className="inspector__claim">{claim.claim}</p>
        <p className="inspector__kind">{KIND_WORDS[claim.kind]}</p>
      </header>

      {/* Criteria, the source that adjudicates, and the date — all three, on
          every claim. A claim nobody can score is not a claim. */}
      <Section title="Resolves">
        <p className="inspector__body">{claim.resolutionCriteria}</p>
        <dl className="inspector__pairs">
          <dt>judged by</dt>
          <dd>{claim.resolutionSource}</dd>
          <dt>by</dt>
          <dd className="inspector__mono">{claim.resolvesBy}</dd>
        </dl>
      </Section>

      <Section title="Base rate">
        {"reading" in baseRate ? (
          <>
            <p className="inspector__count">
              <span className="inspector__mono">{`${baseRate.reading.k} of ${baseRate.reading.n}`}</span>
            </p>
            <p className="inspector__body">{baseRate.reading.referenceClass}</p>
            {baseRate.reading.sources.length === 0 ? (
              <p className="inspector__reason">
                Nobody has checked this count, so nothing downstream of it may call itself
                documented.
              </p>
            ) : (
              <ul className="inspector__sources">
                {baseRate.reading.sources.map((item) => (
                  <li key={item.url} className="inspector__source">
                    <span className="inspector__source-host">{item.host}</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <>
            <p className="inspector__words">{baseRate.absence.words}</p>
            <p className="inspector__reason">{baseRate.absence.reason}</p>
          </>
        )}
      </Section>

      {/* The model's likelihood before this claim's causes are taken into
          account. It is here rather than on the tile because a second number
          beside the model's, on a card the size of a tile, reads as a fourth
          voice. */}
      <Section title="Prior">
        <p className="inspector__mono inspector__prior">
          {toReading(claim.prior.p, claim.prior.lo, claim.prior.hi)}
          <span className="inspector__owner"> model</span>
        </p>
      </Section>

      {/* Three voices, three owners, never merged. If the model says .61 and
          the market says .48, the gap is the thing worth trading, and .545 is a
          number nobody holds. */}
      <Section title="Beliefs">
        <BeliefRow owner="model" slot={claim.beliefs.model} />
        <RangeNote world={world} claim={claim} />
        <BeliefRow owner="user" slot={claim.beliefs.user} />
        <BeliefRow owner="market" slot={claim.beliefs.market} />
      </Section>

      <Section title="Evidence">
        {claim.evidenceInFull.length === 0 ? (
          <>
            <p className="inspector__words">—</p>
            <p className="inspector__reason">no clippings attached to this claim</p>
          </>
        ) : (
          <ul className="inspector__clippings">
            {claim.evidenceInFull.map((item) => (
              <li className="inspector__clipping" key={item.url + item.line}>
                <span className="inspector__monogram" aria-hidden="true">
                  {item.monogram}
                </span>
                <span className="inspector__sign" aria-hidden="true">
                  {item.direction === 1 ? "+" : "−"}
                </span>
                <span className="inspector__clipping-body">
                  <span className="inspector__hidden">
                    {`${item.host}, ${item.direction === 1 ? "supports this claim" : "cuts against this claim"}: `}
                  </span>
                  {item.line}
                  <span className="inspector__source-host">{item.host}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* Where the decomposition goes: the prior, one line per incoming arrow
          with its push and its reason, then the result. It is drawn only when
          the world carries one, and no line of it is ever worked out here. */}
      <Section title="Why this number">
        <p className="inspector__words">no engine yet</p>
        <p className="inspector__reason">
          Nothing has worked this number through the map. When something has, this is where the
          prior, one line for each arrow that pushes on this claim, and the result they come to are
          printed — as the world carries them, never added up here.
        </p>
      </Section>

      <PathBar world={world} claimId={claim.id} />
    </>
  );
}

/** An arrow, read back in words. */
function WireDetail({ world, wire }: { world: WorldView; wire: LinkView }) {
  const from = world.claims.find((claim) => claim.id === wire.source);
  const to = world.claims.find((claim) => claim.id === wire.target);

  return (
    <>
      <header className="inspector__head">
        <p className="inspector__claim">
          <span className="inspector__mono">{wire.source}</span> {from?.claim ?? wire.source}
        </p>
        <p className="inspector__arrow" aria-hidden="true">
          →
        </p>
        <p className="inspector__claim">
          <span className="inspector__mono">{wire.target}</span> {to?.claim ?? wire.target}
        </p>
      </header>

      <Section title="Why">
        <p className="inspector__body">{wire.rationale}</p>
      </Section>

      <dl className="inspector__pairs inspector__pairs--wide">
        <dt>push</dt>
        <dd>
          {/* The push read back as a number and as words. Which way it pushes is
              in the last word — toward, or against — so it survives a picture
              with no colour in it. A push's sign is not a direction of financial
              effect and never takes one of those two hues. */}
          <span className="inspector__mono">{pushAsNumber(wire.strength)}</span>
          {` — ${pushInWords(wire.strength)}`}
        </dd>

        <dt>kind</dt>
        <dd>{modeInWords(wire.mode)}</dd>

        <dt>delay</dt>
        <dd>
          {wire.lag === 0
            ? "the same day its cause becomes true"
            : `${inDays(wire.lag)} after its cause becomes true`}
        </dd>

        <dt>over time</dt>
        <dd>{shapeInWords(wire.shape, wire.halfLife)}</dd>
      </dl>

      <Section title="Sources">
        {wire.sources.length === 0 ? (
          <>
            <p className="inspector__words">—</p>
            <p className="inspector__reason">
              nothing is cited for this arrow; what stands behind it is the mechanism below
            </p>
          </>
        ) : (
          <ul className="inspector__sources">
            {wire.sources.map((item) => (
              <li className="inspector__source" key={item.url}>
                <span className="inspector__source-title">{item.title}</span>
                <span className="inspector__source-host">{item.host}</span>
                <span className="inspector__source-fetched">
                  {"day" in item.retrieved ? (
                    <>
                      <span>fetched </span>
                      <span className="inspector__mono">{item.retrieved.day}</span>
                    </>
                  ) : (
                    `fetched ${item.retrieved.absence.words} ${item.retrieved.absence.reason}`
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* The same mark the wire draws, with the word beside it. One component,
          so the picture and the panel can never say two different things about
          the same arrow. */}
      <Section title="Where it came from">
        <p className="inspector__origin">
          <OriginMark provenance={wire.provenance} use="beside-the-word" />
          <span className="inspector__origin-word">{wire.provenance.replace("_", " ")}</span>
        </p>
        <p className="inspector__reason">{originInWords(wire.provenance)}</p>
      </Section>

      <Section title="Where it sits">
        <p className="inspector__reason">
          {wire.reflexive
            ? "This is a market acting back on the world it measures — the one kind of arrow " +
              "allowed to close a loop, which is why it must take time. It is set aside when " +
              "the map is sorted into columns and when an edit is asked what it can move; you " +
              "can still walk along it."
            : wire.mode === "sustain"
              ? "An ordinary arrow, drawn as two parallel strokes because the push only exists " +
                "while its cause holds — take the cause away and the effect goes with it."
              : "An ordinary arrow, drawn as a single stroke because the push fires once and " +
                "then fades on its own."}
        </p>
      </Section>

      {/* A path is a thing a claim has, not a thing an arrow has. The bar says
          so rather than disappearing: a missing bar looks like a bar nobody
          needed. */}
      <PathBar world={world} claimId={null} />
    </>
  );
}

/** The panel beside the map. */
export function Inspector({ world, selection }: InspectorProps) {
  const claim =
    selection?.kind === "claim" ? world.claims.find((one) => one.id === selection.id) : undefined;
  const wire =
    selection?.kind === "wire" ? world.links.find((one) => one.id === selection.id) : undefined;

  return (
    <aside className="inspector" aria-label="Why this number is what it is">
      {claim !== undefined ? (
        <ClaimDetail world={world} claim={claim} />
      ) : wire !== undefined ? (
        <WireDetail world={world} wire={wire} />
      ) : (
        <div className="inspector__empty">
          <h2 className="inspector__empty-heading">Nothing selected</h2>
          <p className="inspector__body">
            Choose a claim or an arrow on the map — click it, or reach it with the keyboard — and
            everything behind it is read out here: how it will be judged, whose numbers those are,
            what is cited for it, and where it came from.
          </p>
          <p className="inspector__reason">
            This panel is always here. Nothing in this product opens over the map.
          </p>
        </div>
      )}
    </aside>
  );
}
