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
import { type Command, CommandPalette } from "../components/CommandPalette";
import { DoneLine } from "../components/DoneLine";
import { type GenerationDetail, Inspector } from "../components/Inspector";
import { MapFrame } from "../components/MapFrame";
import { Outline } from "../components/Outline";
import { type PanelChoice, PanelSwitch, theLabelFor } from "../components/PanelSwitch";
import { ReceiptStrip } from "../components/ReceiptStrip";
import { RefusalStrip } from "../components/RefusalStrip";
import { ReplayBadge, replaySentence } from "../components/ReplayBadge";
import { RunStrip } from "../components/RunStrip";
import { ShortcutsSheet } from "../components/ShortcutsSheet";
import { VerdictCard } from "../components/VerdictCard";
import { MapCanvas } from "../graph/Canvas";
import { useEveryKey } from "../keyboard/everyKey";
import type { MapKeys } from "../keyboard/useMapKeys";
import type { Selection } from "../world";
import type { Growth, Phase } from "./growth";
import { hasStopped, onlyTheStripChanged } from "./growth";
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

/**
 * The state of the run, as the one word the strip puts in front of its
 * sentence.
 *
 * Six phases and seven words, because *live* and *replay* are the same phase
 * seen two ways and the difference matters to a reader: one is spending money
 * and taking a minute a call, the other is a recording being played back.
 *
 * @param phase Where the run has got to.
 * @param replaying True when this copy has no model key and is playing a
 *   recording back.
 */
export function theWordFor(phase: Phase, replaying: boolean): string {
  switch (phase) {
    case "waiting":
    case "growing":
      return replaying ? "replay" : "live";
    // A cap stopping a run and a run reaching its own end are both a finished
    // map: the map is on screen, nothing more is coming, and *why* is the
    // sentence beside the word rather than the word itself.
    case "settled":
    case "stopped":
      return "finished";
    case "failed":
      return "stopped";
    case "ended_early":
      return "ended early";
  }
}

/**
 * The three panels this screen has, by the name it keeps them under.
 *
 * **Three, because there are three things beside this map to read**: whatever
 * the reader has pointed at, the run that is building it, and the map as a list.
 * There is no fourth: a generated map has no branches to open, so no panel
 * offers any. What this screen used to do was stack the first two in one column
 * with the run's half on top, so a click on a tile filled the bottom of a panel
 * nobody could see the bottom of.
 */
type PanelName = "subject" | "run" | "outline";

/** What the line under the map says when the reader turns to each panel. */
const PANEL_IN_WORDS: Record<PanelName, string> = {
  subject: "the claim or arrow you are on, in the panel beside the map",
  run: "what this run is doing, in the panel beside the map",
  outline: "the map as a list",
};

/** What the screen needs. */
export interface GenerationScreenProps {
  /** The run, already asked for by the press that opened this screen. */
  readonly run: TheRun;
  /**
   * True when the reader asked for the recording, so the run is one being played
   * back — whether or not this copy has a model key. Known before the stream
   * says anything, which is why the badge can be
   * on screen from the first frame — and why the offer to run it again can say
   * truthfully whether pressing it spends money.
   */
  readonly replaying: boolean;
  /** Ask for the same sentence again. A press, like the first one. */
  readonly onRunAgain: () => void;
  /** Let go of this run and go back. A press, and the only way off this screen. */
  readonly onLeave: () => void;
  /**
   * Take up *Change this claim* on the finished map, on whatever the reader is
   * pointing at.
   *
   * **A finished generation is a map like any other**, and the screen a map is
   * edited on already exists. So the six things a reader can do to a claim are
   * not built again here: this hands the finished map over to that screen, with
   * the claim they pressed it about, and that screen opens on it.
   *
   * Absent means there is nowhere to hand it to, and then nothing offers it.
   */
  readonly onChangeAClaim?: (selection: Selection, run: GenerationDetail) => void;
}

/** A map building itself, and the panel beside it. */
export function GenerationScreen({
  run,
  replaying,
  onRunAgain,
  onLeave,
  onChangeAClaim,
}: GenerationScreenProps) {
  const { growth, saying } = useTheRun(run);
  const [selection, setSelection] = useState<Selection>(null);
  const [focused, setFocused] = useState<string | null>(null);
  const [overlay, setOverlay] = useState<"sheet" | "palette" | null>(null);
  // Which of this screen's three panels is on the glass. It opens on the run,
  // because at that moment the run is the only thing there is to read: nothing
  // is selected and there is no map yet.
  const [dock, setDock] = useState<PanelName>("run");
  // And whether the panel is there at all. It folds away and gives the map the
  // width, from `P` and from the control at the head of its own names — a fact
  // about the panel rather than about which of them is showing, so it is kept
  // apart from the three. It starts open on every screen and is not remembered:
  // a reader who comes back to a run they left is shown the run.
  const [away, setAway] = useState(false);
  const [openAt, setOpenAt] = useState<number | null>(null);
  const [status, setStatus] = useState(
    "Press ? for every key. j and k walk a column; h and l follow the wires.",
  );
  const [working, setWorking] = useState<Working>({ state: "reading" });

  const { generationId, phase } = growth;
  const finished = hasStopped(phase);

  // **Whether the foot's second row belongs to the model.** A recording holds no
  // line about what a model was doing, so a replay has none to show; a run that
  // has stopped has nothing out. Only a live run that is still open has, and
  // then the room for both lines is held open whether or not either has anything
  // in it yet. Worked out once, because two things read it: the lines
  // themselves, and the quiet row at the foot that stands down for them.
  const theModelSaysWhatItIsDoing = !replaying && !finished;

  // **How many events have arrived**, so the strip at the foot knows when to
  // start counting the silence again.
  //
  // It counts the run's own state being replaced, which is one for one with an
  // event arriving: `fold` hands back a new state for every one of the eight
  // events a recording holds, so a new object here is something having landed.
  //
  // **The ninth is not an arrival, and that is a decision rather than an
  // oversight** *(2026-09-22)*. An `activity` line is the model saying what it
  // is doing inside a call that has not come back; it reaches the strip and
  // nothing else. A counter that started again on each of them would read
  // *nothing new on the map for 1 s* for three solid minutes while nothing
  // whatever reached the map. The lines say the tool is alive by changing in
  // front of the reader; the number says how long this call has been out.
  //
  // **It is a count of arrivals and nothing else, and it is never drawn.**
  // The browser can count what it was sent; it cannot count the model's calls,
  // and must never print a number as if it could.
  const [arrivals, setArrivals] = useState(0);
  const lastSeen = useRef<Growth | null>(null);
  useEffect(() => {
    const before = lastSeen.current;
    lastSeen.current = growth;
    if (before === growth || onlyTheStripChanged(before, growth)) {
      return;
    }
    setArrivals((many) => many + 1);
  }, [growth]);

  // The same three keys as every other screen, from the one module that binds
  // them — this screen prints *Press ? for every key* under the map, and until
  // that module existed the press did nothing here.
  useEveryKey({
    everyKey: () => setOverlay((was) => (was === "sheet" ? null : "sheet")),
    palette: () => setOverlay((was) => (was === "palette" ? null : "palette")),
    escape: () => setOverlay(null),
  });

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

  /**
   * Fold the panel away, or bring it back — the same act however it is asked
   * for.
   *
   * `P`, the control at the head of the panel, the tab at the edge of the map
   * and the command by name are four ways of asking for one thing, so they are
   * one function: four copies of this would be four chances for one of them to
   * stop saying what the other three say.
   */
  const foldThePanel = useCallback(() => {
    setAway((was) => {
      setStatus(
        was
          ? "the panel is beside the map · press N for the next one"
          : "the panel is away · press P to bring it back",
      );
      return !was;
    });
  }, []);

  // **Choosing something is the one thing that moves the panel on its own.**
  //
  // Pointing at a tile or an arrow, or reaching one with the keyboard, puts what
  // you chose at the top of the panel at once — which is the whole of what was
  // wrong before: the click did select the tile, and the answer arrived at the
  // bottom of a column nothing scrolled.
  //
  // It follows the selection **object** rather than what is in it, because a
  // second press on the same tile is a second act of the reader's and must land
  // them back on what they asked for. Nothing else here ever calls for a panel:
  // a refusal arriving, the verdict landing and the receipt coming back all
  // change a panel the reader may not be looking at, and each of them says so on
  // that panel's own label and in the strip at the foot.
  const lastChosen = useRef(selection);
  useEffect(() => {
    if (selection === lastChosen.current) {
      return;
    }
    lastChosen.current = selection;
    if (selection === null) {
      return;
    }
    setDock(selection.kind === "generation" ? "run" : "subject");
  }, [selection]);

  /**
   * Whether this run has left a map somebody can edit.
   *
   * Two things have to be true, and they are two different facts. The run has
   * **stopped** — however it stopped, a cap or its own ending, because either
   * way nothing more is coming. And the map has a **name of its own**, which is
   * the engine's `base_id` arriving with the likelihoods: a run that broke or
   * whose stream was dropped never gets one, and there is nothing for the
   * engine to fold a branch onto.
   *
   * It is the same pair *Add a claim* waits for, and for the same reasons.
   */
  const aMapToEdit = finished && growth.world.baseId !== "";

  /**
   * Everything the panel says about the run that is building this map.
   *
   * It is held in one place because it is read in two: this screen's own panel,
   * and — when the reader takes the finished map away to edit it — the panel on
   * the screen it goes to. One object, so the two can never say different things
   * about one run.
   */
  const theRun: GenerationDetail = useMemo(
    () => ({
      generationId,
      seed: growth.seed,
      promptFingerprint: growth.receipt?.prompt_hash ?? null,
      working,
      unknown: growth.unknown,
      openAt,
    }),
    [generationId, growth.seed, growth.receipt, working, growth.unknown, openAt],
  );

  /**
   * Take up *Change this claim* on whatever the reader is pointing at.
   *
   * It hands the finished map to the screen maps are edited on, rather than
   * building the six things here. What comes back if nothing can be handed over
   * is a sentence saying which of the two reasons it was, in the one line under
   * the map that already says what the last press did.
   */
  const changeThis = useCallback(() => {
    if (!aMapToEdit) {
      setStatus(
        finished
          ? "this run left no map to edit — the engine never named one"
          : "the map is still being built · the six edits open when it is finished",
      );
      return;
    }
    if (selection === null || selection.kind === "generation") {
      setStatus("choose a claim or an arrow on the map first, then E opens the six edits");
      return;
    }
    onChangeAClaim?.(selection, theRun);
  }, [aMapToEdit, finished, selection, onChangeAClaim, theRun]);

  /**
   * Every command this screen has, by name.
   *
   * **It is a screen's own list, not a copy of the stored map's.** A generated
   * map has no branches to open and none of the six things you can do to a
   * claim, so offering them here would be a palette full of commands that
   * explain why they cannot run. What it does have is the four ways around it
   * and the two things it can do, and each one is also a key or a control on
   * the screen — which is the palette's whole promise.
   *
   * Before this, ⌘K on this screen opened the shortcuts sheet: a key that
   * silently does something else is the one thing this product's keyboard is
   * not allowed to do.
   */
  const commands: Command[] = useMemo(
    () => [
      {
        name: "Read the map as a list",
        does: "The same as pressing O. Every claim, one sentence each, in the order they arrived.",
        run: () => {
          setAway(false);
          setDock("outline");
          setStatus(PANEL_IN_WORDS.outline);
        },
      },
      {
        name: "Read what this run is doing",
        does: "What it refused, what it cost, and where it came from. Also a name at the head of the panel.",
        run: () => {
          setAway(false);
          setDock("run");
          setStatus(PANEL_IN_WORDS.run);
        },
      },
      {
        name: "Show or hide the panel beside the map",
        does: "The same as pressing P, and as the control at the head of the panel, when you want the whole width for the map.",
        run: foldThePanel,
      },
      // **Only once there is a working.** It is read back from the server when
      // the run stops, so a press before then leaves the panel saying *Reading
      // the working of this run…* until the run ends — a command that appears to
      // do nothing for two minutes.
      ...(generationId === null || !finished
        ? []
        : [
            {
              name: "Read the working of this run",
              does: "Every call it made, in order. The same as the control in the panel.",
              run: () => {
                setOpenAt(null);
                setSelection({ kind: "generation", id: generationId });
              },
            },
          ]),
      // **Only once the run has left a map.** Before that there is nothing to
      // change, and a command that explains why it cannot run is a command that
      // should not be on the list.
      ...(aMapToEdit
        ? [
            {
              name: "Change this claim",
              does: "The six things you can do to it. The same as pressing E on the map.",
              run: changeThis,
            },
          ]
        : []),
      {
        name: "Every key",
        does: "The sheet of every key on this map. The same as pressing ?.",
        run: () => setOverlay("sheet"),
      },
      {
        name: "Back to the launchpad",
        does: "Let this run go and start again. The same as the control at the top left.",
        run: onLeave,
      },
    ],
    [generationId, finished, onLeave, aMapToEdit, changeThis, foldThePanel],
  );

  const keys: MapKeys = useMemo(
    () => ({
      // The same key, on the same map, doing the same thing it does everywhere
      // else — once there is a finished map for it to do it to.
      intervene: changeThis,
      branch: () =>
        setStatus(
          aMapToEdit
            ? "press E to change a claim; a branch is started on the screen that opens"
            : "a branch is started on a finished map; this one is still being built",
        ),
      flipWorlds: () => setStatus("there is nothing to flip to — no branch is open"),
      outline: () => {
        setAway(false);
        setDock((was) => {
          const next: PanelName = was === "outline" ? "subject" : "outline";
          setStatus(PANEL_IN_WORDS[next]);
          return next;
        });
      },
      panel: foldThePanel,
      palette: () => setOverlay("palette"),
    }),
    [changeThis, aMapToEdit, foldThePanel],
  );

  /**
   * The three panels, and what each one's name carries beside it.
   *
   * **The name follows the subject** — *This claim* or *This arrow* — because
   * the name is what says what the panel is about, and an arrow is not a claim.
   *
   * **The count is read off the run, never written down.** It is how many
   * proposals the rules refused, which is the length of the list the panel
   * itself prints — so a reader who is on another panel is told the same number
   * they would count by hand, and told it without being pulled off what they
   * were reading.
   */
  const panels: readonly PanelChoice[] = useMemo(
    () => [
      { name: "subject", label: selection?.kind === "wire" ? "This arrow" : "This claim" },
      {
        name: "run",
        label: "The run",
        ...(growth.refusals.length === 0 ? {} : { mark: `refused ${growth.refusals.length}` }),
      },
      { name: "outline", label: "Outline" },
    ],
    [selection, growth.refusals.length],
  );

  const turnTo = useCallback((name: string) => {
    const to = name as PanelName;
    setDock(to);
    setStatus(PANEL_IN_WORDS[to]);
  }, []);

  return (
    <MapFrame
      title={growth.world.title}
      onLeave={onLeave}
      onEveryKey={() => setOverlay("sheet")}
      where={
        <p className="map-bar__where">
          {/* Nothing sits over the map: the mark that says this run is a
              recording is a badge up here, and the sentence explaining it is in
              the line under the map with every other sentence about where this
              map came from. */}
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
      }
      map={
        <MapCanvas
          world={growth.world}
          selection={selection}
          onSelect={setSelection}
          // **Pointing at a claim brings a folded panel back; walking to one
          // does not.** Pointing at one is the reader asking to read it, and the
          // panel is where it is read. Walking the map is walking the map.
          onPointedAt={() => setAway(false)}
          focused={focused}
          onFocused={setFocused}
          mapKey={generationId ?? "a run that has not started"}
          keys={keys}
          onStatus={setStatus}
          onOverflow={() => setStatus("every claim is in the list beside the map")}
          arriving={!finished}
          reserved={growth.skeletons}
          // Framed once when the first rectangle is drawn, and once more when
          // the run stops — the one moment nothing on the map is moving and the
          // reader is about to start reading it.
          frameAgainOn={finished ? "the run stopped" : undefined}
          // **And once more whenever the panel folds or comes back**, which
          // changes the stage's width by 310 pixels without the window moving.
          // It is a second word rather than part of the one above because that
          // one also settles the map — drops every pin and lays the whole thing
          // out again — and settling a map mid-run would move tiles that are
          // already placed. The two compose in the frame's key and nowhere else.
          frameAgainWhen={away ? "the panel folded" : "the panel returned"}
        />
      }
      overlay={
        <>
          {overlay === "palette" ? (
            <CommandPalette open={true} onClose={() => setOverlay(null)} commands={commands} />
          ) : null}
          {overlay === "sheet" ? (
            <ShortcutsSheet open={true} onClose={() => setOverlay(null)} />
          ) : null}
        </>
      }
      status={status}
      // The one strip that says what this run is doing: the state as a word,
      // the run's own sentence — said out loud and printed, one element so the
      // two cannot drift — and, only on a live run that is still open, how long
      // it has been since anything arrived.
      strip={
        <RunStrip
          word={theWordFor(phase, replaying)}
          saying={saying}
          // **A replay counts no seconds, and neither does a run that has
          // stopped.** A replay is paced by the server at six tenths of a
          // second an event, so the reading would reset twice a second and
          // would be measuring our own pacing rather than any wait.
          arrivals={replaying || finished ? null : arrivals}
          // **And the same rule for what the model is doing.** A recording
          // holds no such line, so a replay has none to show; a run that has
          // stopped has nothing out. Only a live run that is still open is
          // given them, and then the room for both is held open whether or not
          // either has anything in it yet.
          doing={theModelSaysWhatItIsDoing ? growth.activity : null}
          after={
            <DoneLine
              done={growth.done}
              failure={growth.failure}
              endedEarly={phase === "ended_early"}
              // The offer is made only where there is something to offer: a
              // stream that stopped without saying why. A run that finished has
              // its map on screen, and a button asking whether to spend it all
              // again would be a control looking for a reason to exist.
              runAgain={
                phase === "ended_early" ? { costsMoney: !replaying, go: onRunAgain } : undefined
              }
            />
          }
        />
      }
      // The names of the three panels, at the head of the panel and outside the
      // part of it that scrolls, so the way to the other two is always on the
      // glass. This is the whole answer to *how do I know what panels exist*.
      panelHead={
        <PanelSwitch panels={panels} showing={dock} onShow={turnTo} onHide={foldThePanel} />
      }
      panelNamedBy={theLabelFor(dock)}
      onShowPanel={foldThePanel}
      // The band at the foot has two rows, and on a live run the second of them
      // is what the model is doing this second. The quiet row — the last key
      // pressed, and where this map came from — stands down for exactly as long
      // as that, which is the same condition the lines themselves are drawn on.
      activityShowing={theModelSaysWhatItIsDoing}
      panel={
        away ? null : /* The map as a list, in place of the panel, exactly as it
           is on a stored map: press O for it, press O again for the panel. It
           grows as the map grows, in the same causal order, so a reader who
           never sees the canvas hears the map being built rather than a silence
           followed by a finished list. */
        dock === "outline" ? (
          <Outline items={outline} onPick={pick} focused={focused} />
        ) : dock === "subject" ? (
          /* Whatever the reader pointed at, and nothing else in front of it.
             **This is the fix.** The panel used to be one column with the run's
             own sections stacked above this one, so a click on a tile filled the
             bottom of a box nothing scrolled — the answer arrived and the click
             looked dead. The run is a panel of its own now, one name away.

             **And once the run has stopped, the way in to the six things you
             can do to this claim** — the same control, in the same place, with
             the same words as on a stored map. What is behind it is the same
             screen too: pressing it hands this map over to it. Kent read the
             map he had just watched build itself and found no verb on it
             (2026-09-22). */
          <Inspector
            world={growth.world}
            selection={selection}
            {...(aMapToEdit ? { onChangeThis: changeThis } : {})}
          />
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

            {growth.receipt === null ? null : <ReceiptStrip receipt={growth.receipt} />}

            {/* **One way into the working that is always there.**
                The panel's view of the run used to be reachable only from a
                refusal row or from the receipt strip's link — so a run that
                refused nothing had one way in, and only at the end, and a run
                whose stream was cut had none at all. That last one is the worst
                of the three: the working is the only record of how far a cut
                run got, the screen fetches it for exactly that reason, and then
                offered the reader no way to read it.

                **And it appears only once there is a working.** It used to be
                drawn from the run's first event, while the thing it opens is
                read back from the server only when the run stops — so pressing
                it during the two minutes a reader is most likely to press it
                left the panel saying *Reading the working of this run…* until
                the run ended. A control that cannot do what it says is worse
                than no control. */}
            {generationId === null || !finished ? null : (
              <section className="generation-working" aria-label="The working of this run">
                <button
                  className="generation-working__open"
                  type="button"
                  onClick={() => {
                    setOpenAt(null);
                    setSelection({ kind: "generation", id: generationId });
                  }}
                >
                  Read the working of this run <span aria-hidden="true">→</span>
                </button>
              </section>
            )}

            {finished && growth.world.baseId !== "" ? (
              // The same control, the same words and the same refusals as the
              // one on a stored map's six-button panel. What differs is only
              // what happens next: a generated map has no branch panel on this
              // screen yet, so the claim is drafted, checked and said, and
              // putting it on a branch of this map is the next piece of work.
              // No branch is sent because there is none to send.
              //
              // **It waits for the map to have a name of its own**, which is the
              // engine's `base_id` arriving with the likelihoods. A run that
              // broke or whose stream was dropped never gets one, and offering
              // to add a claim to a map that has no identifier would send the
              // *run's* name to a route that asks for the map's.
              //
              // **It is on this panel rather than on a name of its own**, at the
              // end of what the run did, because a panel is a place and this is
              // an act. It is the one thing here judged rather than derived, and
              // it is the first thing to move if Kent reads it the other way.
              <AddAClaim
                baseId={growth.world.baseId}
                andThen="It is checked against this map and ready to go onto a branch of it."
              />
            ) : null}

            {/* Where this map is coming from, and — once the reader asks for it
                — every call the run made. **This panel is only ever about the
                run**, so it is handed the run's own selection and nothing else:
                a claim the reader chose is read out on its own panel, one name
                away, and reading it here as well would be one answer printed in
                two places. */}
            <Inspector
              world={growth.world}
              about="the run"
              selection={selection?.kind === "generation" ? selection : null}
              generation={theRun}
            />
          </>
        )
      }
      origin={
        <>
          {/* **Where this map came from is not here any more.** The route, the
              run's own name, the seed and the map's own origin sentence are all
              read in *Run details*, in the panel — R16, brought forward. The
              line that stood here said *"Every claim and arrow on this map
              arrived from…"* from the run's first event, which is to say over a
              map with nothing on it yet, and it was the third of three stacked
              strips of prose at the foot of a screen that could not say whether
              anything was happening at all. */}
          {replaying ? (
            <p className="map-origin__line">
              {replaySentence({
                recordingDate: growth.receipt?.recording_date ?? null,
                receiptMode: growth.receipt?.mode ?? null,
              })}
            </p>
          ) : null}
          {(growth.world.warnings ?? []).map((warning) => (
            <p className="map-origin__line" key={warning}>
              {warning}
            </p>
          ))}
        </>
      }
    />
  );
}
