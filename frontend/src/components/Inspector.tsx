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

import { Fragment, type ReactNode } from "react";
import { NO_CHANGE, noChangeReason } from "../graph/diff/noChange";
import {
  inDays,
  likelihoodStep,
  modeInWords,
  originInWords,
  pushAsNumber,
  pushInWords,
  shapeInWords,
} from "../graph/wires/encodings";
import type { Receipt } from "../stream/events";
import type { Working } from "../stream/transcript";
import type {
  BeliefOwner,
  ClaimKind,
  ClaimView,
  Known,
  LinkView,
  Ranged,
  Selection,
  WorldView,
} from "../world";
import { inFewWords, NOT_ON_THIS_MAP } from "../world/naming";
import { toMovement, toReading, toShare, toTwoFigures } from "./BeliefChip";
import { OriginMark } from "./OriginMark";
import { PathBar } from "./PathBar";
import { ReceiptLines } from "./ReceiptStrip";
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
  /**
   * The run that produced this map, when there was one.
   *
   * Absent on a stored example, which nobody generated. Present on a generated
   * map, and then the panel's third subject is readable: what the run cost, and
   * every proposal it made.
   */
  readonly generation?: GenerationDetail;
}

/** Everything the panel knows about the run that produced this map. */
export interface GenerationDetail {
  /** What the run cost. Null until the receipt arrives; never estimated meanwhile. */
  readonly receipt: Receipt | null;
  /** The working of the run, or the plain reason it could not be read. */
  readonly working: Working;
  /** Event names this build did not know, and how many of each arrived. */
  readonly unknown: ReadonlyMap<string, number>;
  /** Which line of the working the panel was opened at, when it was opened at one. */
  readonly openAt: number | null;
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
function BeliefRow({ owner, slot }: { owner: BeliefOwner; slot: Known<Ranged> }) {
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

/**
 * The whole decomposition: what this claim started from, everything that pushes
 * on it, and what the engine came to.
 *
 * **Every line of it is read, and not one is worked out.** The prior is on the
 * claim, each arrow's push and its receipt are on the arrow, and the result is
 * the engine's own answer for this claim on the day it is judged. The panel
 * lays them out; it never adds them up, and the sentence at the foot says so on
 * screen rather than only in this comment. The moment the canvas did its own
 * arithmetic there would be two engines on the map, they would disagree about
 * half a point, and nobody could say which was right.
 *
 * Before the engine has answered there is no result to print, and the block
 * says that instead of drawing half of itself.
 */
function WhyThisNumber({ world, claim }: { world: WorldView; claim: ClaimView }) {
  // Two kinds of arrow end here, and only one of them made this number.
  //
  // A *feedback arrow* is a market acting back on the world it measures, and
  // `spec/multiverse/interventions.md` sets one rule over the whole product:
  // the map the engine works through is the map with feedback arrows set
  // aside. So a feedback arrow contributed nothing to the number at the foot of
  // this block, and putting it among the pushes would hand the reader a cause
  // the engine never gave. It is still on the map and still worth naming, so it
  // is named below the pushes, in the words the outline already reads it in.
  const into = world.links.filter((wire) => wire.target === claim.id);
  const pushes = into.filter((wire) => !wire.reflexive);
  const fedBackBy = into.filter((wire) => wire.reflexive);
  const result = claim.beliefs.model;
  const byId = new Map(world.claims.map((one) => [one.id, one]));

  return (
    <Section title="Why this number">
      {/* A claim that moved only because some versions started counting more
          says so here, as the first line of this section and above the
          decomposition — because it is a fact about the *reading* of the number,
          and the decomposition is the reading.
          
          Observing one claim reweights the versions of the map: a version under
          which the observation was likely counts for more than one under which
          it was a fluke. A claim with no causes can move by that alone, because
          inside every single version its answer is its own prior in both worlds
          and the paired difference is exactly zero. Without a word about it the
          reader opens the claim and finds a number that moved, a prior, and
          nothing in between to explain it.
          
          It is rendered exactly when the engine's own difference says so, and by
          no other route: no comparison of a share against zero, no check for
          whether a claim has incoming arrows, no inference from an empty
          decomposition. */}
      {claim.moved?.onlyReweighted === true ? (
        <p className="inspector__reweighted">
          this claim moved only because the observation made some versions count more.
        </p>
      ) : null}

      <dl className="inspector__decomposition">
        <dt className="inspector__step-label">it started at</dt>
        <dd className="inspector__step">
          <span className="inspector__mono">
            {toReading(claim.prior.p, claim.prior.lo, claim.prior.hi)}
          </span>
          <span className="inspector__reason">
            the model's likelihood before anything on this map pushes on it
          </span>
        </dd>

        {pushes.length === 0 ? (
          <>
            <dt className="inspector__step-label">pushed on by</dt>
            <dd className="inspector__step">
              <span className="inspector__words">—</span>
              <span className="inspector__reason">
                nothing on this map points at this claim, so its answer is its own starting number
                in every version of the map
              </span>
            </dd>
          </>
        ) : (
          pushes.map((wire) => (
            <Fragment key={wire.id}>
              {/* The cause, named by its own words. Never by its identifier:
                  on a generated map that is twenty-six characters nobody can
                  read (`world/naming.ts`). */}
              <dt className="inspector__step-label">
                {inFewWords(byId.get(wire.source)?.claim ?? NOT_ON_THIS_MAP)} pushes
              </dt>
              <dd className="inspector__step">
                <span className="inspector__mono">{pushAsNumber(wire.strength)}</span>
                <span className="inspector__reason">
                  {`${pushInWords(wire.strength)} · ${modeInWords(wire.mode)} · ${
                    wire.lag === 0 ? "the same day" : inDays(wire.lag)
                  } · ${wire.provenance.replace("_", " ")}`}
                </span>
                {/* What this arrow's target comes to with its cause supposed
                    true. It costs a whole extra run of the map, so it is asked
                    for one arrow at a time — select the arrow on the map and it
                    is fetched and kept. Until then the line is simply not here,
                    because an empty one would look like a number that failed to
                    arrive. */}
                {wire.conditional.reading === undefined ? null : (
                  <span className="inspector__reason">
                    {`with that cause supposed true this claim reads ${toReading(
                      wire.conditional.reading.p,
                      wire.conditional.reading.lo,
                      wire.conditional.reading.hi,
                    )}`}
                  </span>
                )}
              </dd>
            </Fragment>
          ))
        )}

        {/* Every feedback arrow into this claim, apart from the pushes and
            below them, because the engine set them aside before it worked this
            number out. The reader is told that in the line, not left to work it
            out from the fact that the arrow is in a different place. */}
        {fedBackBy.map((wire) => (
          <Fragment key={wire.id}>
            <dt className="inspector__step-label">fed back into by</dt>
            <dd className="inspector__step">
              <span className="inspector__mono">{wire.source}</span>
              <span className="inspector__reason">
                {`a market acting back on the world it measures, ${
                  wire.lag === 0 ? "the same day" : `after ${inDays(wire.lag)}`
                } — the engine works this map through with feedback arrows set aside, so this arrow has not pushed on this number`}
              </span>
            </dd>
          </Fragment>
        ))}

        <dt className="inspector__step-label">it comes to</dt>
        <dd className="inspector__step">
          {result.reading === undefined ? (
            <>
              <span className="inspector__words">{result.absence.words}</span>
              <span className="inspector__reason">{result.absence.reason}</span>
            </>
          ) : (
            <>
              <span className="inspector__mono">
                {toReading(result.reading.p, result.reading.lo, result.reading.hi)}
              </span>
              <span className="inspector__reason">
                {world.versions === undefined
                  ? "the likelihood the map was written with, read on the day this claim is judged"
                  : "the engine's own answer for this claim, read on the day this claim is judged"}
              </span>
            </>
          )}
        </dd>
      </dl>

      <p className="inspector__reason">
        Every line above is a number something else worked out: the starting number and each push
        are on the map, and the result is the engine's. Nothing on this panel adds them up — two
        things that work out one number eventually disagree about it, and then nobody can say which
        is right.
      </p>
    </Section>
  );
}

/**
 * What this edit did to this claim's number, when the engine says it did
 * anything.
 *
 * Both readings are the engine's, and which way it went is the engine's word:
 * this panel prints them and subtracts nothing. Beside them goes the share of
 * the versions of the map that moved the same way, headed in the reader's own
 * words rather than by the field's name.
 */
function WhatYourEditDid({ claim }: { claim: ClaimView }) {
  const moved = claim.moved;
  // A claim whose value an edit fixed has no move to report: it is true — or
  // false — in every version of the map, and the badge that says so is the
  // whole of what happened to it.
  if (moved === undefined || claim.standing !== undefined) {
    return null;
  }
  const agreed = moved.sameDirection.reading;
  // The engine's verdict on the claim, which is not the same thing as the two
  // numbers: a claim can move a hair and still come out unchanged.
  const counted = claim.diff === "shifted";
  // A claim that moved only by reweighting is a third case, and the two
  // sentences below would both be false of it: the versions did not disagree
  // about a direction, because not one version that counts moved at all. The
  // sentence that *is* true of it is printed at the head of the decomposition,
  // where the chapter puts it.
  const reweighted = moved.onlyReweighted === true;

  return (
    <Section title="What your edit did">
      <p className="inspector__moved">
        <span className="inspector__mono">
          {toMovement(moved.from, moved.to, moved.by, moved.way)}
        </span>
        <span className="inspector__moved-word">{counted ? moved.way : NO_CHANGE}</span>
      </p>
      {/* Why the engine says it did not move. The sentence is not written here:
          the tile's line and the rail's greyed row say the same thing, and one
          verdict said three ways is three chances to name a cause the engine
          never gave. A claim that moved only by reweighting is the exception —
          its sentence is at the head of the decomposition, where the chapter
          puts it, and saying it twice on one screen is noise. */}
      {counted || reweighted ? null : <p className="inspector__reason">{noChangeReason(moved)}</p>}
      {reweighted ? null : (
        <>
          <dl className="inspector__pairs">
            <dt>same direction</dt>
            <dd>
              {agreed === undefined ? (
                moved.sameDirection.absence.words
              ) : (
                <span className="inspector__mono">{toShare(agreed)}</span>
              )}
            </dd>
          </dl>
          <p className="inspector__reason">
            {agreed === undefined
              ? moved.sameDirection.absence.reason
              : "The share of the versions of the map — each one a set of numbers this model " +
                "would have stood behind — in which this claim moved the same way. It is a " +
                "column beside the move and never multiplied into it."}
          </p>
        </>
      )}
    </Section>
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

      <WhatYourEditDid claim={claim} />

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

      <WhyThisNumber world={world} claim={claim} />

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
        <p className="inspector__claim">{from?.claim ?? NOT_ON_THIS_MAP}</p>
        <p className="inspector__arrow" aria-hidden="true">
          →
        </p>
        <p className="inspector__claim">{to?.claim ?? NOT_ON_THIS_MAP}</p>
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

      {/* The one number that turns an arrow into something you can argue about:
          what the claim at its head comes to with the claim at its tail
          **supposed** true. Supposed, never observed — "how often do these two
          show up together" is a correlation, and an arrow claims a mechanism.
          It costs a whole extra run of the map, so it is asked for when a reader
          asks about this arrow and kept afterwards. */}
      <Section title="With its cause supposed true">
        {wire.conditional.reading === undefined ? (
          <>
            <p className="inspector__words">{wire.conditional.absence.words}</p>
            <p className="inspector__reason">{wire.conditional.absence.reason}</p>
          </>
        ) : (
          <>
            <p className="inspector__mono inspector__prior">
              {toReading(
                wire.conditional.reading.p,
                wire.conditional.reading.lo,
                wire.conditional.reading.hi,
              )}
              <span className="inspector__owner"> model</span>
            </p>
            <p className="inspector__reason">
              {`What the claim this arrow ends at comes to when the one it starts at is taken ` +
                `as given — supposed, never observed, because an arrow claims a mechanism and ` +
                `how often two things show up together is a different question.`}
            </p>
          </>
        )}
      </Section>

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

/**
 * The run that produced this map: what it cost, and every proposal it made.
 *
 * **The panel's third subject.** Until now it opened on a claim or an arrow; it
 * also opens on the run behind them, which is neither, and so gets a section of
 * its own rather than being squeezed into one.
 *
 * **Every number is a field and this panel adds nothing up.** It does not total
 * the two token counts, does not work a cost out of a token count and a price,
 * and does not time anything — the same rule that already forbids it adding up an
 * arrow's pushes to explain a likelihood.
 *
 * **Every line of the working is in the engine's own words.** An accepted line
 * names the claim it became; a refused line quotes what the model wrote and then
 * carries the validator's own sentence, one per rule broken, with nothing added;
 * a stopped line carries the model's own one-sentence reason. This panel composes
 * no sentence about any of the three, and a refused claim is quoted rather than
 * given an identifier or a tile.
 *
 * **Three kinds of line, not two.** A proposal was accepted, a proposal was
 * refused, or the model answered *Stop* on a line and it closed with nothing
 * added. The third is the one a reader would otherwise never see: it makes no
 * event on the stream, because nothing about the map changed. **A stopped line
 * carries no place in the working** — the count counts what was proposed, and a
 * stop proposed nothing — so the numbers here have gaps in them, and the gaps are
 * the stops.
 */
function GenerationDetailPanel({ detail }: { detail: GenerationDetail }) {
  const { receipt, working, unknown, openAt } = detail;
  return (
    <>
      <header className="inspector__head">
        <p className="inspector__claim">This generation</p>
        <p className="inspector__kind">the run that built this map</p>
      </header>

      <Section title="What it cost">
        {receipt === null ? (
          <>
            {/* Before the receipt arrives the section is not drawn. No running
                estimate, no partial total, no ticking cost: a cost nobody has
                totalled is a number nobody computed. */}
            <p className="inspector__words">no engine yet</p>
            <p className="inspector__reason">
              The run has not sent its receipt. Nothing here estimates what it has spent so far — a
              cost nobody has totalled is a number nobody computed.
            </p>
          </>
        ) : (
          <ReceiptLines receipt={receipt} />
        )}
      </Section>

      <Section title="Every proposal, in order">
        {working.state === "reading" ? (
          <p className="inspector__reason">
            Reading the working of this run back from the server, which holds it for as long as it
            is running.
          </p>
        ) : working.state === "gone" ? (
          <>
            <p className="inspector__words">—</p>
            {/* The route's own sentence, printed as it came. A transcript lives
                for the life of the process that made it; there is no storage in
                this build. */}
            <p className="inspector__reason">{working.reason}</p>
          </>
        ) : (
          <ol className="inspector__transcript">
            {working.transcript.lines.map((line, place) => (
              <li
                className="inspector__line"
                // Two lines can genuinely carry the same words on different
                // claims, and a stopped line has no place of its own, so its
                // position in the list is the only stable name it has.
                // biome-ignore lint/suspicious/noArrayIndexKey: the working arrives as one list from one answer and is never reordered, added to or removed.
                key={`${place}-${line.at ?? "stopped"}`}
                data-what={line.what}
                data-open={line.at !== null && line.at === openAt ? "yes" : "no"}
              >
                <span className="inspector__line-at">{line.at === null ? "—" : line.at}</span>
                <span className="inspector__line-what">{line.what}</span>
                <span className="inspector__line-words">
                  {line.in_words}
                  {line.violations.map((violation) => (
                    <span className="inspector__line-reason" key={violation.message}>
                      {violation.message}
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ol>
        )}
      </Section>

      {unknown.size === 0 ? null : (
        <Section title="Events this build does not know">
          {/* Ignored, counted, and said out loud. A browser that crashed on a new
              event would make the server unable to add one; a browser that
              dropped one silently would make a missing feature look like a
              working one. */}
          <dl className="inspector__pairs">
            {[...unknown].map(([name, count]) => (
              <Fragment key={name}>
                <dt>{name}</dt>
                <dd className="inspector__mono">{count}</dd>
              </Fragment>
            ))}
          </dl>
          <p className="inspector__reason">
            This build has no name for these, so it changed nothing when they arrived and counted
            them here instead.
          </p>
        </Section>
      )}
    </>
  );
}

/** The panel beside the map. */
export function Inspector({ world, selection, generation }: InspectorProps) {
  const claim =
    selection?.kind === "claim" ? world.claims.find((one) => one.id === selection.id) : undefined;
  const wire =
    selection?.kind === "wire" ? world.links.find((one) => one.id === selection.id) : undefined;
  const run = selection?.kind === "generation" ? generation : undefined;

  return (
    <aside className="inspector" aria-label="Why this number is what it is">
      {run !== undefined ? (
        <GenerationDetailPanel detail={run} />
      ) : claim !== undefined ? (
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
