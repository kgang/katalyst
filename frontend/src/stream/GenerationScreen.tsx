/**
 * The screen a map builds itself on.
 *
 * The same canvas, the same panel and the same keyboard as every other map. What
 * is different is where the map comes from: it arrives claim by claim down one
 * request, with a reserved rectangle standing wherever the next one will go, and
 * every proposal the rules refused listed beside it.
 *
 * **There is no spinner here, and no moment where a blank screen turns into a
 * finished picture.** The growing *is* the loading state.
 *
 * **This screen does not ask for the map.** The press that opened it did
 * (`theRun.ts`), and this watches what that press started. It can be mounted,
 * unmounted and mounted again — which React's development mode does on purpose —
 * without a second generation being asked for, because there is no code here
 * that could ask for one.
 */

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { outlineOf } from "../a11y/sentences";
import { AddAClaim } from "../components/AddAClaim";
import { DoneLine } from "../components/DoneLine";
import { IfTheScreenBreaks } from "../components/IfTheScreenBreaks";
import { Inspector } from "../components/Inspector";
import { Outline } from "../components/Outline";
import { ReceiptStrip } from "../components/ReceiptStrip";
import { RefusalStrip } from "../components/RefusalStrip";
import { ReplayBadge, replaySentence } from "../components/ReplayBadge";
import { ShortcutsSheet } from "../components/ShortcutsSheet";
import { edgeMarks, useTheEdgesOfThePanel } from "../components/useTheEdges";
import { VerdictCard } from "../components/VerdictCard";
import { MapCanvas } from "../graph/Canvas";
import type { MapKeys } from "../keyboard/useMapKeys";
import type { Selection } from "../world";
import { hasStopped } from "./growth";
import type { TheRun, WhereItHasGot } from "./theRun";
import type { Working } from "./transcript";
import { readTranscript } from "./transcript";
import "../components/generationDock.css";

/**
 * Watch a run that is already going.
 *
 * `useSyncExternalStore` is React's own way of reading something that lives
 * outside React and changes on its own, and it is the right one here for a
 * reason that matters: subscribing and unsubscribing does nothing to the run.
 * A hook that *started* the generation would start two of them in development,
 * and *"never retry, a generation that ran twice would spend twice"* would be
 * broken on every machine where the app is developed.
 *
 * @param run The generation the press created.
 */
function useTheRun(run: TheRun): WhereItHasGot {
  return useSyncExternalStore(run.watch, run.now, run.now);
}

/** What the screen needs. */
export interface GenerationScreenProps {
  /** The run, already asked for by the press that opened this screen. */
  readonly run: TheRun;
  /**
   * True when this copy has no model key, so the run is a recording being played
   * back. Known before the stream says anything, which is why the badge can be
   * on screen from the first frame — and why the offer to run it again can say
   * truthfully whether pressing it spends money.
   */
  readonly replaying: boolean;
  /** Ask for the same sentence again. A press, like the first one. */
  readonly onRunAgain: () => void;
  /** Let go of this run and go back. A press, and the only way off this screen. */
  readonly onLeave: () => void;
}

/** A map building itself, and the panel beside it. */
export function GenerationScreen({ run, replaying, onRunAgain, onLeave }: GenerationScreenProps) {
  const { growth, saying } = useTheRun(run);
  const [selection, setSelection] = useState<Selection>(null);
  const [focused, setFocused] = useState<string | null>(null);
  const [overlay, setOverlay] = useState<"sheet" | null>(null);
  const [dock, setDock] = useState<"panel" | "outline">("panel");
  const [openAt, setOpenAt] = useState<number | null>(null);
  const [status, setStatus] = useState(
    "Press ? for every key. j and k walk a column; h and l follow the wires.",
  );
  const [working, setWorking] = useState<Working>({ state: "reading" });
  const { panel, edges } = useTheEdgesOfThePanel();

  const { generationId, phase } = growth;
  const finished = hasStopped(phase);

  // The working of the run, read once the run has finished. It is asked for then
  // rather than as it goes, because the server writes it from the same pass that
  // writes the stream and a half-read one would be a second, staler copy.
  //
  // **A run that ended early has a working too**, and it is the one case where
  // reading it back matters most: it is the only record of how far the run got.
  useEffect(() => {
    if (generationId === null || !finished) {
      return;
    }
    let stillWanted = true;
    readTranscript(generationId).then(
      (read) => {
        if (stillWanted) {
          setWorking(read);
        }
      },
      // `readTranscript` answers rather than throws, for every failure it can
      // name. This is for the ones it cannot: a screen that waits for a promise
      // that will never settle says *Reading the working…* until the tab closes.
      () => {
        if (stillWanted) {
          setWorking({
            state: "gone",
            reason: "The working of this run could not be read, and nothing said why.",
          });
        }
      },
    );
    return () => {
      stillWanted = false;
    };
  }, [generationId, finished]);

  const outline = useMemo(() => outlineOf(growth.world), [growth.world]);

  // The keyboard follows the growing edge: a claim that has just arrived takes
  // focus, exactly as a claim a branch adds does. That is what keeps the newest
  // tile on the glass through a run that goes on for minutes — the canvas
  // already brings whatever the keyboard is on into view, so nothing here
  // re-frames the map and nothing re-lays it out. A tile that is already placed
  // stays exactly where it is; what moves is where the reader is looking.
  //
  // A claim that has just **arrived** takes focus, and nothing else does. The
  // count is what says one arrived: when the likelihoods land, the engine's own
  // world replaces the drawing and its claims come back in the map's order
  // rather than the order they were proposed in — which is not an arrival, and
  // moving the view for it would slide the map sideways at the very moment it
  // stopped changing.
  const howManyClaims = growth.world.claims.length;
  const seenSoFar = useRef(0);
  const lastArrived = useRef<string | null>(null);
  useEffect(() => {
    if (howManyClaims <= seenSoFar.current) {
      return;
    }
    seenSoFar.current = howManyClaims;
    const arrived = growth.world.claims[howManyClaims - 1]?.id ?? null;
    lastArrived.current = arrived;
    setFocused(arrived);
  }, [howManyClaims, growth.world.claims]);

  // And it lets go the moment the run stops. Focus is also what the hover lens
  // reads, and a lens left on a claim the machine chose would dim the whole
  // finished map to fifteen per cent at exactly the moment the reader starts
  // reading it. If the reader has moved since, their focus is theirs and stays.
  useEffect(() => {
    if (!finished) {
      return;
    }
    setFocused((was) => (was === lastArrived.current ? null : was));
  }, [finished]);

  const pick = useCallback((id: string) => {
    setFocused(id);
    setSelection({ kind: "claim", id });
  }, []);

  // Nothing on this screen is bound to the map's own six operations yet, so the
  // keys that open them say so rather than doing nothing.
  const keys: MapKeys = useMemo(
    () => ({
      intervene: () => setStatus("a generated map takes edits through Add a claim, beside the map"),
      branch: () => setStatus("a branch is started on a stored map; this one is still being built"),
      flipWorlds: () => setStatus("there is nothing to flip to — no branch is open"),
      outline: () =>
        setDock((was) => {
          const next = was === "outline" ? "panel" : "outline";
          setStatus(next === "outline" ? "the map as a list" : "the panel beside the map");
          return next;
        }),
      panel: () => setStatus("the panel is beside the map"),
      palette: () => setOverlay("sheet"),
    }),
    [],
  );

  const header = (
    <header className="map-bar">
      <button className="map-bar__back" type="button" onClick={onLeave}>
        <span aria-hidden="true">←</span> Back to the launchpad
      </button>
      <h1 className="map-bar__title">{growth.world.title}</h1>
      <p className="map-bar__where">
        {/* Nothing sits over the map: the mark that says this run is a recording
            is a badge up here, and the sentence explaining it is in the line
            under the map with every other sentence about where this map came
            from. */}
        {replaying ? (
          <ReplayBadge
            recordingDate={growth.receipt?.recording_date ?? null}
            receiptMode={growth.receipt?.mode ?? null}
          />
        ) : null}
        {run.asked.target === null ? "Explore" : "Verify"}
        <span className="map-bar__side">
          {run.asked.target === null ? "what your sentence would cause" : run.asked.target}
        </span>
      </p>
      <button className="map-bar__sheet" type="button" onClick={() => setOverlay("sheet")}>
        Every key (?)
      </button>
    </header>
  );

  return (
    <main className="page page--map">
      {/* One boundary, at the screen. A fault while drawing a map that arrived in
          a shape nothing here expected takes the map down and leaves the way
          back to the launchpad standing. */}
      <IfTheScreenBreaks header={header}>
        <div className="map-body">
          <div className="map-stage">
            <MapCanvas
              world={growth.world}
              selection={selection}
              onSelect={setSelection}
              focused={focused}
              onFocused={setFocused}
              mapKey={generationId ?? "a run that has not started"}
              keys={keys}
              onStatus={setStatus}
              onOverflow={() => setStatus("every claim is in the list beside the map")}
              arriving={!finished}
              reserved={growth.skeletons}
              // Framed once when the first rectangle is drawn, and once more when
              // the run stops — the one moment nothing on the map is moving and
              // the reader is about to start reading it.
              frameAgainOn={finished ? "the run stopped" : undefined}
            />
            {overlay === "sheet" ? (
              <ShortcutsSheet open={true} onClose={() => setOverlay(null)} />
            ) : null}
            <p className="map-status">
              <span className="map-status__mark">last key</span>
              {status}
            </p>
          </div>

          <aside
            className="dock dock--generation"
            ref={panel}
            {...edgeMarks(edges)}
            aria-label="The panel beside the map"
          >
            {/* The map as a list, in place of the panel, exactly as it is on a
                stored map: press O for it, press O again for the panel. It grows
                as the map grows, in the same causal order, so a reader who never
                sees the canvas hears the map being built rather than a silence
                followed by a finished list. */}
            {dock === "outline" ? (
              <Outline items={outline} onPick={pick} focused={focused} />
            ) : (
              <>
                {/* The Verify door's answer, at the top, when a destination was named. */}
                {growth.verdict === null || run.asked.target === null ? null : (
                  <VerdictCard
                    verdict={growth.verdict}
                    target={run.asked.target}
                    world={growth.world}
                    onSelect={pick}
                  />
                )}

                <RefusalStrip
                  refusals={growth.refusals}
                  finished={finished}
                  openAt={openAt}
                  onOpen={(at) => {
                    setOpenAt(at);
                    setSelection({ kind: "generation", id: generationId ?? "" });
                  }}
                />

                {growth.receipt === null ? null : (
                  <ReceiptStrip
                    receipt={growth.receipt}
                    onOpen={() => {
                      setOpenAt(null);
                      setSelection({ kind: "generation", id: generationId ?? "" });
                    }}
                  />
                )}

                {finished && growth.world.baseId !== "" ? (
                  // The same control, the same words and the same refusals as the
                  // one on a stored map's six-button panel. What differs is only
                  // what happens next: a generated map has no branch panel on this
                  // screen yet, so the claim is drafted, checked and said, and
                  // putting it on a branch of this map is the next piece of work.
                  // No branch is sent because there is none to send.
                  //
                  // **It waits for the map to have a name of its own**, which is
                  // the engine's `base_id` arriving with the likelihoods. A run
                  // that broke or whose stream was dropped never gets one, and
                  // offering to add a claim to a map that has no identifier
                  // would send the *run's* name to a route that asks for the
                  // map's — a different thing of the same shape.
                  <AddAClaim
                    baseId={growth.world.baseId}
                    andThen="It is checked against this map and ready to go onto a branch of it."
                  />
                ) : null}

                <Inspector
                  world={growth.world}
                  selection={selection}
                  generation={{
                    seed: growth.seed,
                    promptFingerprint: growth.receipt?.prompt_hash ?? null,
                    working,
                    unknown: growth.unknown,
                    openAt,
                  }}
                />
              </>
            )}
          </aside>
        </div>

        {/* Said out loud, and said once — and it says what just **changed**
            rather than re-reading the whole run. On a stored map this line is on
            the page as well; here the same facts are already drawn — the claims
            on the canvas, the refusals in the panel, why the run stopped under
            the map — so printing them again made the foot of the screen three
            strips of prose saying the same thing twice. It stays the spoken
            channel. */}
        <p className="map-live map-live--spoken" aria-live="polite">
          {saying}
        </p>

        <div className="map-origin">
          <p className="map-origin__line">{growth.world.origin}</p>
          {replaying ? (
            <p className="map-origin__line">
              {replaySentence({
                recordingDate: growth.receipt?.recording_date ?? null,
                receiptMode: growth.receipt?.mode ?? null,
              })}
            </p>
          ) : null}
          <DoneLine
            done={growth.done}
            failure={growth.failure}
            endedEarly={phase === "ended_early"}
            // The offer is made only where there is something to offer: a stream
            // that stopped without saying why. A run that finished has its map on
            // screen, and a button asking whether to spend it all again would be
            // a control looking for a reason to exist.
            runAgain={
              phase === "ended_early" ? { costsMoney: !replaying, go: onRunAgain } : undefined
            }
          />
          {(growth.world.warnings ?? []).map((warning) => (
            <p className="map-origin__line" key={warning}>
              {warning}
            </p>
          ))}
        </div>
      </IfTheScreenBreaks>
    </main>
  );
}
