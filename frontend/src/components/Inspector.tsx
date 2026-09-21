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
 * **Its head carries the one control in it**: *Change this claim* on a claim,
 * *Change this push* on an arrow, both opening the panel of things you can do.
 * Until it was here, that panel opened from the `E` key and the command palette
 * and nowhere else, so somebody working the screen with a mouse could read the
 * whole argument and never find a verb on it.
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
import { GENERATE_ADDRESS } from "../stream/generate";
import type { UnreadLine } from "../stream/growth";
import { NO_LIKELIHOOD_YET, NOTHING_HERE_WAS_TYPED_IN } from "../stream/growth";
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
import { TheWorking } from "./TheWorking";
import "./inspector.css";

/**
 * What stands where a fact about the run will go, before it has arrived.
 *
 * The em dash the rest of this product uses for a slot with nothing in it, so
 * that an empty slot never reads as a value of its own — and never as a zero.
 */
const NOT_YET = "—";

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
   * Open the panel of things you can do to what is selected — the mouse's way
   * to it.
   *
   * **Absent means there is nothing to open, and then no control is drawn.**
   * Two callers leave it out and both are right to: the screen that watches a
   * map build itself has no branch to edit, and the map screen leaves it out
   * while the panel is already open, because a way in that is already in is not
   * a control. That second one is also what keeps *Change this push* from
   * appearing twice on one screen — once here and once as the button inside the
   * panel that actually changes the number.
   */
  readonly onChangeThis?: () => void;
  /**
   * A handle on that control, so the screen can put the keyboard back on it.
   *
   * **The control unmounts the moment it is pressed**, so a reader who tabbed to
   * it and pressed Enter would be left on nothing at all. The panel it opens
   * takes the keyboard; when that closes, the screen puts it back here. Which
   * is the screen's job rather than this panel's, because the screen is the only
   * thing that knows where the reader came from.
   */
  readonly changeRef?: React.Ref<HTMLButtonElement>;
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
  /**
   * The engine's own name for this run, as its twenty-six characters.
   *
   * The one identifier in this product that is printed on screen, and it is
   * deliberate: it is how somebody asks for this answer again — the map, the
   * seed and the working — and the working is asked for by it. Null until the
   * run's first event has arrived.
   */
  readonly generationId: string | null;
  /**
   * The seed every likelihood in this run was worked out from, as its digits.
   *
   * Digits rather than a number because a seed can be nineteen of them and a
   * browser holds a whole number exactly only up to sixteen. Null until the run
   * has started.
   */
  readonly seed: string | null;
  /**
   * Which wording of our instructions produced this run, whole.
   *
   * Null until the receipt arrives, and **never shortened**: a fingerprint cut
   * to its first eight characters is a fingerprint nobody can check against
   * anything, and cutting one is the browser deriving a reading.
   */
  readonly promptFingerprint: string | null;
  /** The working of the run, or the plain reason it could not be read. */
  readonly working: Working;
  /** Every line the reader could not act on, by name, with how many and which kind. */
  readonly unknown: ReadonlyMap<string, UnreadLine>;
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

/**
 * The way from what you are reading to what you can do about it.
 *
 * **The whole of this product's central interaction used to be behind one
 * key.** The panel of operations opened from `E` and from the command palette
 * and from nowhere else, so a reader who works a screen with a mouse could
 * click every tile, read the whole argument, find no verb anywhere on it and
 * conclude the tool is a viewer.
 *
 * It sits in the panel's head rather than on the tile, because a tile's height
 * is reserved before the browser has drawn one (`graph/geometry.ts`), and a new
 * row on a tile lays the whole map out again — which is the one thing the diff
 * view promises never to do.
 *
 * It is a word with a hairline round it, which is what a button is in this
 * product; it is never a filled rounded button, and the words are the shared
 * vocabulary's, never this component's own.
 *
 * @param words What this control is called on the subject it is on.
 * @param onOpen What it opens, or nothing at all — in which case nothing is
 *   drawn, because a control that does nothing is not a control.
 */
function ChangeThis({
  words,
  onOpen,
  handle,
}: {
  words: string;
  onOpen?: (() => void) | undefined;
  handle?: React.Ref<HTMLButtonElement> | undefined;
}) {
  if (onOpen === undefined) {
    return null;
  }
  return (
    <button className="inspector__change" type="button" ref={handle} onClick={onOpen}>
      {words}
    </button>
  );
}

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
          claim whose own prior explains most of the band — on the stored
          example, the Brent claim's band is mostly the Brent claim's own stated
          prior — and it is worked out from `range_shares` on the world, which
          the engine gets out of the same two thousand versions of the map it
          already runs, at no extra cost.

          **No figure is written in this comment.** The two that used to be here
          were the engine's answer copied by hand, and they were wrong within a
          stack: the share is the `B · base · band from B` line of
          `docs/worked-numbers.txt`, and the width is that line's claim read off
          `B · base · reading`. One generated file owns them both, so there is
          one place to look on the day they move again.

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
            {/* Named by its own words, like every other claim on every other
                surface: on a generated map an identifier is twenty-six
                characters of the engine's own bookkeeping (`world/naming.ts`). */}
            <dt className="inspector__step-label">fed back into by</dt>
            <dd className="inspector__step">
              <span className="inspector__words">
                {inFewWords(byId.get(wire.source)?.claim ?? NOT_ON_THIS_MAP)}
              </span>
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
function ClaimDetail({
  world,
  claim,
  onChangeThis,
  changeRef,
}: {
  world: WorldView;
  claim: ClaimView;
  onChangeThis?: (() => void) | undefined;
  changeRef?: React.Ref<HTMLButtonElement> | undefined;
}) {
  const baseRate = claim.baseRate;

  return (
    <>
      <header className="inspector__head">
        <p className="inspector__claim">{claim.claim}</p>
        <p className="inspector__kind">{KIND_WORDS[claim.kind]}</p>
        <ChangeThis words="Change this claim" onOpen={onChangeThis} handle={changeRef} />
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
function WireDetail({
  world,
  wire,
  onChangeThis,
  changeRef,
}: {
  world: WorldView;
  wire: LinkView;
  onChangeThis?: (() => void) | undefined;
  changeRef?: React.Ref<HTMLButtonElement> | undefined;
}) {
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
        {/* The vocabulary's own words for the one thing you can do to an arrow.
            They are the same words as the button inside the panel this opens,
            and the two are never on screen together: the map screen stops
            passing this the moment the panel is open. */}
        <ChangeThis words="Change this push" onOpen={onChangeThis} handle={changeRef} />
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
 * The run that produced this map: **its working**, and what it was run against.
 *
 * **The panel's third subject.** Until now it opened on a claim or an arrow; it
 * also opens on the run behind them, which is neither, and so gets a section of
 * its own rather than being squeezed into one.
 *
 * **What it cost is not here.** The ten readings are drawn once, on the strip
 * beside the map, and this section points at it. They used to be drawn in both
 * places, one above the other in a 320-pixel column, which reads to somebody
 * scrolling past as two costs — and the second copy was the one no number on
 * screen could be traced to, because the strip is what the receipt event fills
 * in.
 *
 * **The section is drawn from the moment there is a generation**, with whatever
 * has arrived in it. The working arrives when the run stops and the fingerprint
 * arrives with the receipt, and each says which of those it is waiting for. A
 * section that appeared only once everything had landed would be a panel that is
 * empty exactly while a reader is most likely to open it.
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
  const { seed, promptFingerprint, working, unknown, openAt } = detail;
  return (
    <>
      <header className="inspector__head">
        <p className="inspector__claim">This generation</p>
        <p className="inspector__kind">the run that built this map</p>
      </header>

      <Section title="What it was run against">
        <dl className="inspector__pairs inspector__pairs--facts">
          <dt>seed</dt>
          {/* The one number every likelihood in this run was worked out from,
              printed as the digits that came off the wire. Ask for the same
              sentence at the same seed and the same map comes back. */}
          <dd className="inspector__mono">{seed ?? NOT_YET}</dd>
          <dt>prompt fingerprint</dt>
          <dd className="inspector__mono">{promptFingerprint ?? NOT_YET}</dd>
        </dl>
        <p className="inspector__reason">
          The prompt fingerprint says which wording of our instructions produced this run: two runs
          with the same fingerprint were asked the same way, and two with different ones were not,
          however alike their maps look. It is printed whole because half a fingerprint cannot be
          compared with anything.
        </p>
        <p className="inspector__reason">
          {/* One cost, in one place. A panel that repeated the ten readings
              would be a second copy of a number nobody could point at. */}
          What this run cost is on the strip beside the map, in ten readings, every one of them a
          field the engine sent.
        </p>
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
          // The same list an insert's working is drawn in, and the same
          // component: a reader who has learned to read one has learned to
          // read the other.
          <TheWorking lines={working.transcript.lines} openAt={openAt} />
        )}
      </Section>

      {unknown.size === 0 ? null : (
        <Section title="Lines this build could not act on">
          {/* Ignored, counted, and said out loud. A browser that crashed on a new
              event would make the server unable to add one; a browser that
              dropped one silently would make a missing feature look like a
              working one.
              **Two kinds, and they are not told as one.** A name this build has
              never heard of means the server has learned a word and the map
              drawn from the rest is a correct map. A name this build knows
              whose payload could not be read means a broken line, and the map
              may be missing what that line carried — which is a different thing
              to be told, and a worse one. Saying "this build has no name for
              these" over a `done` it could not read would be false. */}
          <dl className="inspector__pairs">
            {[...unknown].map(([name, line]) => (
              <Fragment key={name}>
                <dt>{name}</dt>
                <dd className="inspector__mono">{line.howMany}</dd>
              </Fragment>
            ))}
          </dl>
          {[...unknown].some(([, line]) => !line.unreadable) ? (
            <p className="inspector__reason">
              This build has no name for some of these, so it changed nothing when they arrived and
              counted them here instead. The map it drew is a correct map of the lines it did
              understand.
            </p>
          ) : null}
          {[...unknown].some(([, line]) => line.unreadable) ? (
            <p className="inspector__reason">
              And some of these are names this build does know: the stream sent one and what came
              with it could not be read, so the line was counted and nothing was changed. This map
              may be missing whatever that line carried.
            </p>
          ) : null}
        </Section>
      )}
    </>
  );
}

/**
 * Where this map is coming from: the route, the run's own name, and the seed.
 *
 * **It moved here from the foot of the screen** (decision R16, brought forward
 * on 2026-09-21). Where it stood it was an always-on strip of prose reading
 * *"Every claim and arrow on this map arrived from /api/generate, in generation
 * …, at seed …"* — written from the run's first event onward, which is to say
 * **over a map with nothing on it yet**. It asserted arrivals that had not
 * happened, it repeated what the strip now says in words, and it was the third
 * of three stacked strips at the foot of a screen whose reader could not tell
 * whether anything was happening at all.
 *
 * **What it says here is true from the first frame.** Nothing on this map is
 * typed in — that is a fact about how the map is built, not about how much of it
 * has arrived — and the three readings beside it are the three things a reader
 * needs to ask for the same answer again.
 *
 * **A plain section that is always here.** Not a dialog, not a disclosure, not
 * something that opens over the map. Folding the panel's sections behind their
 * summaries is a later stack's work and this is written to be folded.
 */
function RunDetails({
  detail,
  theMapsOwn,
}: {
  detail: GenerationDetail;
  theMapsOwn: string | null;
}) {
  const { generationId, seed } = detail;
  return (
    <Section title="Run details">
      <dl className="inspector__pairs inspector__pairs--facts">
        <dt>route</dt>
        <dd className="inspector__mono">{GENERATE_ADDRESS}</dd>
        <dt>generation</dt>
        <dd className="inspector__mono">{generationId ?? NOT_YET}</dd>
        <dt>seed</dt>
        {/* The digits that came off the wire, never a parsed number: a seed can
            be nineteen digits and a browser holds a whole number exactly only up
            to sixteen. */}
        <dd className="inspector__mono">{seed ?? NOT_YET}</dd>
      </dl>
      {/* While the map is being built these two are the whole of what is true
          about where it came from. The moment the engine hands its own world
          over it also hands over its own origin sentence — which says the same
          thing and more, at the seed and over the versions it really used — so
          that one is printed instead. It is never printed at the foot of the
          screen as well: one account, in one place. */}
      {theMapsOwn === null ? (
        <>
          <p className="inspector__reason">{NOTHING_HERE_WAS_TYPED_IN}</p>
          <p className="inspector__reason">{NO_LIKELIHOOD_YET}</p>
        </>
      ) : (
        <p className="inspector__reason">{theMapsOwn}</p>
      )}
    </Section>
  );
}

/** The panel beside the map. */
export function Inspector({
  world,
  selection,
  generation,
  onChangeThis,
  changeRef,
}: InspectorProps) {
  const claim =
    selection?.kind === "claim" ? world.claims.find((one) => one.id === selection.id) : undefined;
  const wire =
    selection?.kind === "wire" ? world.links.find((one) => one.id === selection.id) : undefined;
  const run = selection?.kind === "generation" ? generation : undefined;

  return (
    <aside className="inspector" aria-label="Why this number is what it is">
      {/* Where this map is coming from, always in the panel while there is a
          run — except while the panel is already reading that run out, which
          says the same three things at more length. */}
      {generation === undefined || run !== undefined ? null : (
        <RunDetails
          detail={generation}
          theMapsOwn={world.versions === undefined ? null : world.origin}
        />
      )}
      {run !== undefined ? (
        <GenerationDetailPanel detail={run} />
      ) : claim !== undefined ? (
        <ClaimDetail
          world={world}
          claim={claim}
          onChangeThis={onChangeThis}
          changeRef={changeRef}
        />
      ) : wire !== undefined ? (
        <WireDetail world={world} wire={wire} onChangeThis={onChangeThis} changeRef={changeRef} />
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
