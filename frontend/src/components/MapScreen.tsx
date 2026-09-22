/**
 * The screen a stored map is read and edited on.
 *
 * The map fills it, the panel beside it answers *why is this number what it
 * is*, and every edit a reader makes goes onto a branch of their own rather
 * than onto the map. Nothing here works a number out: the engine is asked for
 * the map with the branch folded on, and while it is being asked the slot says
 * so in words rather than showing a stale figure or a spinner.
 *
 * **The screen around the map is not here.** It is `MapFrame`, shared with the
 * map that builds itself: a bar with the way back, the stage, the panel in its
 * frame, one polite line said out loud and the origin strip at the foot. The
 * two screens were written twice and drifted the moment either was improved —
 * the panel's frame landed on one a round before the other, the error boundary
 * on one and never on the other.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { branchAnnouncement } from "../a11y/announcement";
import { outlineOf } from "../a11y/sentences";
import { RefusedBranch } from "../api/client";
import { MapCanvas } from "../graph/Canvas";
import { bothPaintings, type Engine, railRows } from "../graph/diff/branchWorld";
import { endings, NO_SUMMARY_YET } from "../graph/diff/endings";
import { roomFor } from "../graph/geometry";
import { useEveryKey } from "../keyboard/everyKey";
import type { MapKeys } from "../keyboard/useMapKeys";
import {
  type Absence,
  appendEdit,
  type BranchView,
  type DiffView,
  type Edit,
  forkBranch,
  type Known,
  type LinkView,
  openBranch,
  type Ranged,
  type Reason,
  type Selection,
  type WorldSource,
  type WorldView,
  workshopOf,
} from "../world";
import { absence } from "../world/absence";
import { asOneSentence } from "../world/failures";
import { BranchPanel, InterventionPanel } from "./BranchPanel";
import { type Command, CommandPalette } from "./CommandPalette";
import { DeltaRail } from "./DeltaRail";
import { Inspector } from "./Inspector";
import { MapFrame } from "./MapFrame";
import { Outline } from "./Outline";
import { type PanelChoice, PanelSwitch, theLabelFor } from "./PanelSwitch";
import { Refusal } from "./Refusal";
import { RunStrip } from "./RunStrip";
import { ShortcutsSheet } from "./ShortcutsSheet";

/** How long the wires take to arrive, column by column, before the map settles. */
const WAVE_SETTLES_AFTER = 1200;

/**
 * The three panels this screen has, by the name it keeps them under.
 *
 * **Three, because there are three things beside this map to read**: whatever
 * the reader has pointed at and the six things they can do to it, their
 * branches with everything the open one moved, and the map as a list. There is
 * no run here — nobody generated a stored map — so no panel offers one.
 *
 * All three used to be one column, with the branches and the change list
 * stacked above the answer to *why is this number what it is*. That is the
 * clutter Kent read as *"the side bar is pretty cluttered"*, and it is why a
 * click on a tile filled a box below the fold.
 */
type PanelName = "subject" | "branches" | "outline";

/** What the line under the map says when the reader turns to each panel. */
const PANEL_IN_WORDS: Record<PanelName, string> = {
  subject: "the claim or arrow you are on, in the panel beside the map",
  branches: "your branches and what the open one moved",
  outline: "the map as a list",
};

/**
 * What stands where a likelihood would go while the engine is being asked for
 * one.
 *
 * The shared vocabulary has three ways of saying a number is not there, and
 * this is the third of them — *nothing has been computed* — because that is
 * exactly what is true while a question is in flight: the engine has been asked
 * and has not answered, so nothing has worked this number through the map
 * **yet**. It is not a fourth kind of absence and it is not a spinner: the map
 * on screen keeps its shape, the slots that will move say why they are empty,
 * and the line under the map says what has been asked for and where.
 */
const WHILE_ASKING: Absence = absence(
  "no_engine",
  "The engine has been asked at /api/worlds for the map with this branch folded onto it, and " +
    "has not answered. Nothing has worked this number through the map yet.",
);

/**
 * What stands where a likelihood would go when the engine **refused** the
 * branch.
 *
 * Not "no engine yet": the engine is there and it answered — it said the branch
 * does not fit the map, and it said why. The words have to be true of that, and
 * the vocabulary's first three rows are all about a number nobody has worked out
 * rather than one that could not be. So there is a **fourth row** — *the engine
 * refused the branch these numbers would come from* → **not worked out** — and a
 * kind of its own to go with it, because "nothing has run yet" invites waiting
 * and "the engine turned this down" invites repairing what it turned down.
 */
const REFUSED: Absence = absence(
  "refused",
  "The engine would not work this map out from this branch: the branch does not fit the map. " +
    "Every reason is beside the map, and nothing on the map has changed.",
);

/**
 * What stands there when the engine could not be reached at all.
 *
 * **Not a refusal**, and the difference is the whole of why the two are separate
 * kinds. A refusal is an answer: the engine looked, said no, and said why, and
 * it will say the same thing until the branch is repaired. This is one attempt
 * that did not come back — the engine is there and it was asked — and it stops
 * being true the moment the reader asks again. So it takes the kind that is
 * never kept, and its reason says what to do about it.
 */
function unreachable(reason: string): Absence {
  return absence(
    "ask_failed",
    `${reason} Nothing on the map has changed; opening the branch again asks once more.`,
  );
}

/**
 * Everything the engine has said about the branch that is open, and whether it
 * has said it yet.
 */
type Answered =
  | { at: "asking" }
  | { at: "answered"; computed: { now: WorldView; change: DiffView } }
  | { at: "refused"; reasons: readonly Reason[] }
  | { at: "failed"; reason: string }
  | { at: "nothing-open" };

/**
 * Where the engine has got to, in the one shape the picture reads.
 *
 * Every state but *nothing is open* reserves the room an answer will take and
 * says why it is not there yet, so the map is the same size before and after the
 * answer lands and nothing on it jumps.
 */
function engineState(answer: Answered): Engine | undefined {
  switch (answer.at) {
    case "answered":
      return { at: "answered", now: answer.computed.now, change: answer.computed.change };
    case "asking":
      return { at: "waiting", absence: WHILE_ASKING };
    case "refused":
      return { at: "waiting", absence: REFUSED };
    case "failed":
      return { at: "waiting", absence: unreachable(answer.reason) };
    case "nothing-open":
      return undefined;
  }
}

/** Turn whatever the engine threw into either a list of reasons or one sentence. */
function asAnswer(reason: unknown): Answered {
  if (reason instanceof RefusedBranch) {
    return { at: "refused", reasons: reason.reasons };
  }
  return { at: "failed", reason: asOneSentence(reason) };
}

/**
 * The map, the panel beside it, and everything you can do to both.
 *
 * Three things live here rather than inside the map, because all three are about
 * the whole screen rather than about the picture: which branch is open, which of
 * the two worlds is painted, and what the keyboard is on.
 */
export function MapScreen({
  base,
  branches,
  source,
  insteadOfTheEngine,
  onLeave,
}: {
  base: WorldView;
  branches: readonly BranchView[];
  /** Where a branch's world, its difference and an arrow's number are asked for. */
  source: WorldSource;
  /** Why this map is the stored example rather than the engine's, or nothing. */
  insteadOfTheEngine: string | null;
  onLeave: () => void;
}) {
  const [shop, setShop] = useState(() => workshopOf(branches));
  const [showing, setShowing] = useState<"now" | "before">("now");
  const [selection, setSelection] = useState<Selection>(null);
  const [focused, setFocused] = useState<string | null>(null);
  // Which of this screen's three panels is on the glass. It opens on the one
  // that says what to do next — *choose a claim or an arrow on the map* — which
  // is the sentence a reader who has never seen this screen needs first.
  const [dock, setDock] = useState<PanelName>("subject");
  // And whether the panel is there at all. `P` puts it away and gives the map
  // the whole width; it is a fact about the panel rather than about which of
  // them is showing, so it is kept apart from the three.
  const [away, setAway] = useState(false);
  const [onlyColumn, setOnlyColumn] = useState<{
    layer: number;
    claims: readonly string[];
  } | null>(null);
  const [overlay, setOverlay] = useState<"palette" | "sheet" | null>(null);
  const [intervening, setIntervening] = useState(false);
  const [naming, setNaming] = useState(false);
  const [status, setStatus] = useState(
    "Press ? for every key. j and k walk a column; h and l follow the wires.",
  );
  const [arriving, setArriving] = useState(true);
  const lastBranch = useRef<string | null>(null);

  const open = shop.branches.find((branch) => branch.id === shop.openId);

  // What the engine says about the branch that is open. It is asked again
  // whenever the branch changes — which is what makes the six buttons move
  // numbers: pressing one appends an edit, and the whole branch goes back.
  const [answer, setAnswer] = useState<Answered>({ at: "nothing-open" });
  // How many times the engine has been asked, so that the strip's reading of
  // how long this question has been out starts again with each one.
  const [asks, setAsks] = useState(0);
  useEffect(() => {
    if (open === undefined) {
      setAnswer({ at: "nothing-open" });
      return;
    }
    let stillWanted = true;
    setAnswer({ at: "asking" });
    // One more question has gone out. The strip at the foot starts its count of
    // seconds again from here — this is the only thing that count is for, and it
    // is a count of questions asked, never of anything on the map.
    setAsks((many) => many + 1);
    Promise.all([
      source.readWorld({ baseId: base.baseId, branch: open }),
      source.readDiff({ baseId: base.baseId, branch: open }),
    ]).then(
      ([now, change]) => {
        if (stillWanted) {
          setAnswer({ at: "answered", computed: { now, change } });
        }
      },
      (failure: unknown) => {
        if (stillWanted) {
          setAnswer(asAnswer(failure));
        }
      },
    );
    return () => {
      // An answer to a question the reader has moved on from is thrown away
      // rather than drawn: a map that flickers back to an older branch because
      // a slower request finished last is a map nobody can trust.
      stillWanted = false;
    };
    // The branch itself is what this hangs on, and that is enough: appending an
    // edit hands back a new branch rather than changing the one that was there
    // — a branch is an audit trail and nothing rewrites one — so every press of
    // a button is a new question here, and nothing else is.
  }, [source, base.baseId, open]);

  // Held still between renders, because both paintings of the map hang on it: a
  // fresh object every render would lay the whole map out again on every keypress
  // for an answer that has not changed.
  const engine = useMemo(() => engineState(answer), [answer]);
  const computed = answer.at === "answered" ? answer.computed : undefined;

  // The numbers on the arrows, one at a time, kept once they arrive. Each one
  // costs a whole extra run of the map, so it is asked for when a reader selects
  // that arrow and never again for the same branch, seed and arrow.
  const [wireNumbers, setWireNumbers] = useState<ReadonlyMap<string, Known<Ranged>>>(new Map());
  // The last ask that did not come back, which is shown and never kept. A
  // failure is a fact about one attempt, not about the number: keeping it would
  // mean the reader who selects the arrow again after the server comes back is
  // told for the rest of the session that it cannot be worked out.
  const [wireFailed, setWireFailed] = useState<{ key: string; absence: Absence } | undefined>();
  const paintings = useMemo(
    () => (open === undefined ? null : bothPaintings(base, open, engine)),
    [base, open, engine],
  );

  const painted = paintings === null ? base : showing === "now" ? paintings.now : paintings.before;
  const seed = painted.seed;

  /**
   * The branch the map in front is drawn from — nothing, when the map in front
   * is the one as it was written.
   *
   * Flipping to "as it was written" puts the base map on screen, and an arrow's
   * number worked out under a branch is not a number about that map. This is the
   * branch every arrow number on this screen is asked for and named by, so the
   * question asked and the map drawn can never come apart.
   */
  const shownBranch = paintings === null || showing === "before" ? undefined : open;

  /**
   * What names one arrow's number: which branch, how far that branch has got,
   * which seed, which arrow.
   *
   * The edit count is in the name because a branch's `id` outlives its edits: an
   * edit appends to the branch and hands back a new one with the same id, so a
   * name without the count would hand a reader the number worked out before
   * their edit. Counting is enough to tell two branches apart because edits are
   * only ever appended — `appendEdit` is the one function that touches them, and
   * there is no undo (INV-workbench.49).
   */
  const wireKey = useCallback(
    (linkId: string) => {
      const whose =
        shownBranch === undefined ? "as-written" : `${shownBranch.id}@${shownBranch.edits.length}`;
      return `${whose}:${seed ?? "no-seed"}:${linkId}`;
    },
    [shownBranch, seed],
  );

  // The map as it is drawn: the world above, with any arrow number already
  // fetched put back on its own arrow.
  const world = useMemo((): WorldView => {
    if (wireNumbers.size === 0 && wireFailed === undefined) {
      return painted;
    }
    return {
      ...painted,
      links: painted.links.map((link): LinkView => {
        const key = wireKey(link.id);
        const asked = wireNumbers.get(key);
        if (asked !== undefined) {
          return { ...link, conditional: asked };
        }
        return wireFailed?.key === key
          ? { ...link, conditional: { absence: wireFailed.absence } }
          : link;
      }),
    };
  }, [painted, wireNumbers, wireFailed, wireKey]);

  /**
   * One box per claim, tall enough for whichever of the two paintings needs more
   * room — a claim grows badges when an edit touched it. Reserving the taller box
   * is what lets the union be laid out once and painted twice with nothing
   * moving.
   */
  const heights = useMemo(() => {
    if (paintings === null) {
      return undefined;
    }
    const reserved = new Map<string, number>();
    for (const side of [paintings.now, paintings.before]) {
      for (const claim of side.claims) {
        reserved.set(claim.id, Math.max(reserved.get(claim.id) ?? 0, roomFor(claim)));
      }
    }
    return reserved;
  }, [paintings]);

  // The endings the edit reaches. With the engine, its own ranked rows, in its
  // own order; without it, the reachable endings in map order, and the rail
  // says on its own face which of the two it is showing.
  const rows = useMemo(
    () =>
      computed !== undefined
        ? railRows(paintings?.now ?? base, computed.change)
        : paintings === null
          ? []
          : endings(paintings.now),
    [computed, paintings, base],
  );
  const outline = useMemo(() => outlineOf(world), [world]);

  // What the branch did, said out loud for a reader who is not looking at the
  // picture. It is said twice, because the two halves arrive at different
  // moments: the shape the instant the branch opens, and the counts when the
  // engine answers. The live region is polite, so the second line waits for a
  // pause rather than cutting across the first.
  const announcement = useMemo(
    () => (paintings === null ? "" : branchAnnouncement(paintings.now, computed?.change)),
    [paintings, computed],
  );

  // One arrow's own number, asked for when the reader selects that arrow and
  // kept afterwards. It is fetched here rather than by the wire because no
  // component in this product talks to the network, and because the answer
  // belongs to the whole screen: the panel and the plate on the wire read the
  // same one.
  useEffect(() => {
    if (selection?.kind !== "wire") {
      return;
    }
    const key = wireKey(selection.id);
    if (wireNumbers.has(key)) {
      return;
    }
    let stillWanted = true;
    source.readConditional({ baseId: base.baseId, branch: shownBranch, linkId: selection.id }).then(
      (slot) => {
        if (stillWanted) {
          setWireNumbers((was) => new Map(was).set(key, slot));
          setWireFailed((was) => (was?.key === key ? undefined : was));
        }
      },
      (failure: unknown) => {
        // Shown, and not filed with the answers. The engine is there and it was
        // asked — what is missing is this one attempt's reply, which is a
        // different thing from "nothing has worked this number out", and which
        // stops being true the moment the reader asks again.
        if (stillWanted) {
          setWireFailed({
            key,
            absence: absence(
              "ask_failed",
              `${asOneSentence(failure)} Select this arrow again to ask once more.`,
            ),
          });
        }
      },
    );
    return () => {
      stillWanted = false;
    };
  }, [selection, source, base.baseId, shownBranch, wireKey, wireNumbers]);

  // A branch has just been opened or made. Three things follow, in this order:
  // the map says out loud what the branch did, the wires arrive again in causal
  // order, and — because creating a claim moves focus to it — the keyboard lands
  // on the claim the branch added, so the view frames the thing you just made
  // rather than leaving you to hunt for it.
  useEffect(() => {
    if (shop.openId === lastBranch.current) {
      return;
    }
    lastBranch.current = shop.openId;
    setShowing("now");
    setArriving(true);
    if (paintings === null) {
      return;
    }
    const arrived = paintings.now.claims.find((claim) => claim.diff === "added");
    if (arrived !== undefined) {
      setFocused(arrived.id);
      setSelection({ kind: "claim", id: arrived.id });
      setStatus(`your edit added this claim · ${arrived.claim}`);
    }
  }, [shop.openId, paintings]);

  // The wave settles on its own clock, and on nothing else.
  //
  // **It has to be its own effect.** The one above runs again whenever the
  // picture changes — and the picture changes when the engine answers, which is
  // a moment or two after a branch is opened. A timer started up there would be
  // cleared by that second run and never started again, and the map would stay
  // mid-arrival for ever, which is to say invisible.
  useEffect(() => {
    if (!arriving) {
      return;
    }
    const settles = window.setTimeout(() => setArriving(false), WAVE_SETTLES_AFTER);
    return () => window.clearTimeout(settles);
  }, [arriving]);

  const edit = useCallback((made: Edit) => {
    setShop((was) =>
      appendEdit(was.openId === null ? forkBranch(was, "Your own branch") : was, made),
    );
  }, []);

  /**
   * Where the keyboard was when the operations were opened, so it can be put
   * back when they close.
   *
   * **The way in from the panel's head is the case this exists for.** That
   * control unmounts the instant it is pressed — a way in that is already in is
   * not a control — so a reader who tabbed to it and pressed Enter would be
   * left standing on nothing, and the next Tab would start again at the top of
   * the page. The panel takes the keyboard when it opens, which is the reader's
   * own act rather than a theft (`graph/theKeyboard.ts` is about who decided,
   * and here the reader did), and this is the other half of it.
   *
   * Two cases, and they are one rule: put it back where it came from, and where
   * that no longer exists put it on the control that has taken its place. `E`
   * pressed on a tile comes back to the tile, because the tile is still there.
   */
  const cameFrom = useRef<HTMLElement | null>(null);
  const theWayIn = useRef<HTMLButtonElement | null>(null);
  const wasOpen = useRef(false);
  useEffect(() => {
    if (wasOpen.current && !intervening) {
      const back = cameFrom.current;
      if (back?.isConnected) {
        back.focus();
      } else {
        theWayIn.current?.focus();
      }
    }
    wasOpen.current = intervening;
  }, [intervening]);

  const keys: MapKeys = useMemo(
    () => ({
      intervene: () => {
        cameFrom.current = document.activeElement as HTMLElement | null;
        // The six things you can do are about the claim you are on, so they open
        // on the panel that claim is read out on.
        setAway(false);
        setDock("subject");
        setIntervening(true);
      },
      branch: () => {
        setAway(false);
        setDock("branches");
        setNaming(true);
      },
      flipWorlds: () => {
        if (paintings === null) {
          setStatus("there is nothing to flip to — no branch is open");
          return;
        }
        setShowing((was) => {
          const next = was === "now" ? "before" : "now";
          setStatus(
            next === "now"
              ? "the map with your edits"
              : "the map as it was written, with what your branch adds drawn faint",
          );
          return next;
        });
      },
      outline: () => {
        setAway(false);
        setDock((was) => {
          setOnlyColumn(null);
          const next: PanelName = was === "outline" ? "subject" : "outline";
          setStatus(PANEL_IN_WORDS[next]);
          return next;
        });
      },
      panel: () =>
        setAway((was) => {
          setStatus(
            was
              ? "the panel is beside the map · press N for the next one"
              : "the panel is away · press P to bring it back",
          );
          return !was;
        }),
      palette: () => setOverlay("palette"),
    }),
    [paintings],
  );

  // ⌘K, ? and Escape work wherever you are on the screen, not only on the map,
  // because two of them are how you find out what the others do. They are bound
  // by `keyboard/everyKey.ts`, which every screen in the app calls — this one
  // held them alone once, and they were dead on the other two.
  useEveryKey({
    everyKey: () => setOverlay((was) => (was === "sheet" ? null : "sheet")),
    palette: () => setOverlay((was) => (was === "palette" ? null : "palette")),
    escape: () => {
      setOverlay(null);
      setIntervening(false);
      setNaming(false);
    },
  });

  const commands: Command[] = useMemo(() => {
    const made: Command[] = [
      {
        name: "The map as it was written",
        does: "Close the branch. Also the first row of the branch panel.",
        run: () => setShop((was) => openBranch(was, null)),
      },
      ...shop.branches.map((branch) => ({
        name: `Open the branch: ${branch.label}`,
        does: `${branch.edits.length} edits. Also a row in the branch panel.`,
        run: () => setShop((was) => openBranch(was, branch.id)),
      })),
      {
        name: "Flip between the two maps",
        does: "The same as pressing Space on the map. A hard switch, never a fade.",
        run: keys.flipWorlds,
      },
      {
        name: "Change this claim",
        does: "The six things you can do to it. The same as pressing E on the map.",
        run: keys.intervene,
      },
      {
        name: "Start a branch",
        does: "The same as pressing B on the map, and as the button in the branch panel.",
        run: keys.branch,
      },
      {
        name: "Read the map as a list",
        does: "The same as pressing O. Every claim, one sentence each.",
        run: () => {
          setOnlyColumn(null);
          setAway(false);
          setDock("outline");
        },
      },
      {
        name: "Read your branches and what they moved",
        does: "Every branch, the open one's edits, and the endings it reaches. Also a name at the head of the panel.",
        run: () => {
          setAway(false);
          setDock("branches");
        },
      },
      {
        name: "Show or hide the panel beside the map",
        does: "The same as pressing P, when you want the whole width for the map.",
        run: keys.panel,
      },
      {
        name: "Every key, on one sheet",
        does: "The same as pressing the question mark.",
        run: () => setOverlay("sheet"),
      },
      {
        name: "Back to the launchpad",
        does: "The same as the link at the top left.",
        run: onLeave,
      },
    ];
    return made;
  }, [shop.branches, keys, onLeave]);

  const pick = useCallback((id: string) => {
    setFocused(id);
    setSelection({ kind: "claim", id });
  }, []);

  // **Choosing something is the one thing that moves the panel on its own.**
  //
  // Pointing at a tile or an arrow, or reaching one with the keyboard, puts what
  // you chose at the top of the panel at once. It follows the selection
  // **object** rather than what is in it, because a second press on the same
  // tile is a second act of the reader's and must land them back on what they
  // asked for. Nothing else calls for a panel: an engine answer landing and a
  // branch gaining an edit both change a panel the reader may not be looking at,
  // and each says so on that panel's own label and in the strip at the foot.
  const lastChosen = useRef(selection);
  useEffect(() => {
    if (selection === lastChosen.current) {
      return;
    }
    lastChosen.current = selection;
    if (selection === null) {
      return;
    }
    // **And it brings the panel back if it was folded away.** Choosing a claim
    // is the reader asking to read something, and the place it is read is the
    // panel; leaving it folded would answer the question off screen, which is
    // the defect the panels were split up to fix.
    setAway(false);
    setDock("subject");
  }, [selection]);

  /**
   * The three panels, and what each one's name carries beside it.
   *
   * **The name follows the subject** — *This claim* or *This arrow* — because
   * the name says what the panel is about, and an arrow is not a claim.
   *
   * **The count is the engine's own list of reasons**, read off the answer the
   * panel itself prints. A branch the engine turned down is the one thing that
   * happens on this screen while the reader is elsewhere and that they must not
   * miss: nothing on the map changed, and the reason it did not is on that
   * panel.
   */
  const panels: readonly PanelChoice[] = useMemo(
    () => [
      { name: "subject", label: selection?.kind === "wire" ? "This arrow" : "This claim" },
      {
        name: "branches",
        label: "Branches and changes",
        ...(answer.at === "refused" ? { mark: `refused ${answer.reasons.length}` } : {}),
      },
      { name: "outline", label: "Outline" },
    ],
    [selection, answer],
  );

  const turnTo = useCallback((name: string) => {
    const to = name as PanelName;
    setDock(to);
    setStatus(PANEL_IN_WORDS[to]);
  }, []);

  const THE_PANEL = (
    <>
      {dock === "outline" ? (
        <Outline
          items={outline}
          onPick={pick}
          focused={focused}
          {...(onlyColumn === null
            ? {}
            : {
                only: new Set(onlyColumn.claims),
                filter:
                  `Only the claims in column ${onlyColumn.layer}, which is what the ` +
                  `collapsed tile on the map stands for. Press O for all of them.`,
              })}
        />
      ) : dock === "subject" ? (
        /* Whatever the reader pointed at, and the six things they can do to it.
           **The operations moved here from the head of the column**, where they
           opened above the branches, the change list and the answer they were
           about. They are about the claim you are on, so they belong on the
           panel that claim is read out on — and pressing `E` turns to it. */
        <>
          {intervening ? (
            <InterventionPanel
              world={world}
              // The open branch in the engine's own shape, so that a
              // claim the reader asks for is drafted and judged against
              // the map they are looking at rather than against the one
              // underneath it. Absent when the branch cannot be written
              // down in full, which is exactly when there is nothing
              // honest to send.
              {...(open?.wire === undefined ? {} : { branch: open.wire })}
              selection={selection}
              onEdit={edit}
              onClose={() => setIntervening(false)}
            />
          ) : null}
          {/* The mouse's way to the six things you can do. The keyboard has
              `E` and the palette has a command; without this a reader working
              the screen with a mouse could click every tile, read the whole
              argument and never find a verb on it.

              **It is handed over only while the panel is shut.** A way in that
              is already in is not a control, and on an arrow it would put two
              buttons reading *Change this push* on one screen — this one, and
              the one inside the panel that changes the number. */}
          <Inspector
            world={world}
            selection={selection}
            changeRef={theWayIn}
            {...(intervening ? {} : { onChangeThis: keys.intervene })}
          />
        </>
      ) : (
        <>
          <BranchPanel
            branches={shop.branches}
            openId={shop.openId}
            world={world}
            onOpen={(id) => setShop((was) => openBranch(was, id))}
            onFork={(label) => setShop((was) => forkBranch(was, label))}
            naming={naming}
            onNaming={setNaming}
          />
          {answer.at === "refused" ? <Refusal asking="this map" reasons={answer.reasons} /> : null}
          {open === undefined ? null : (
            <DeltaRail
              rows={rows}
              ranked={computed !== undefined}
              summary={computed === undefined ? NO_SUMMARY_YET : computed.change.summary}
            />
          )}
        </>
      )}
    </>
  );

  return (
    <MapFrame
      title={base.title}
      onLeave={onLeave}
      onEveryKey={() => setOverlay("sheet")}
      where={
        open === undefined ? (
          <p className="map-bar__where">The map as it was written</p>
        ) : (
          <p className="map-bar__where">
            {/* A branch's hue rides on its name chip and its lane and nowhere
                else, and the chip always carries the branch's name — so which
                branch you are in is readable with no colour at all. */}
            <span className="map-bar__chip" data-hue={open.hue} aria-hidden="true" />
            {open.label}
            <span className="map-bar__side">
              {showing === "now" ? "with your edits" : "as it was written"}
            </span>
          </p>
        )
      }
      map={
        <MapCanvas
          world={world}
          selection={selection}
          onSelect={setSelection}
          focused={focused}
          onFocused={setFocused}
          heights={heights}
          mapKey={`${base.baseId}:${shop.openId ?? "as-written"}`}
          keys={keys}
          onStatus={setStatus}
          onOverflow={(column) => {
            setOnlyColumn(column);
            // Pressing a collapsed tile is the reader asking for the claims
            // behind it, so the panel comes back if it was put away and turns
            // to the list those claims are on.
            setAway(false);
            setDock("outline");
            setStatus(PANEL_IN_WORDS.outline);
          }}
          arriving={arriving}
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
      // The same one strip the generating screen has, in the same place, with
      // the same polite line inside it — so a reader who has learned one of
      // these screens has learned the other.
      //
      // **The seconds count while this screen is waiting on the server, and only
      // then.** Here that is the state where a branch's world has been asked for
      // and has not come back — usually a fraction of a second, occasionally
      // not, and already the one state this screen says something about under
      // the map. When the answer lands there is nothing left to measure and the
      // reading goes; a stored map at rest is not waiting for anything.
      //
      // **The sentence is the one this screen already said**, word for word. A
      // second sentence swapped in while the engine is being asked would be a
      // second thing announced to a screen reader for one edit, and the line
      // already says the numbers are on their way.
      strip={
        announcement === "" ? null : (
          <RunStrip
            word={answer.at === "asking" ? "asking" : "stored"}
            saying={announcement}
            arrivals={answer.at === "asking" ? asks : null}
          />
        )
      }
      // The names of the three panels, at the head of the panel and outside the
      // part of it that scrolls, so the way to the other two is always on the
      // glass. This is the whole answer to *how do I know what panels exist*.
      panelHead={<PanelSwitch panels={panels} showing={dock} onShow={turnTo} onHide={keys.panel} />}
      panelNamedBy={theLabelFor(dock)}
      panel={away ? null : THE_PANEL}
      onShowPanel={keys.panel}
      origin={
        <>
          <p className="map-origin__line">{world.origin}</p>
          {answer.at === "asking" ? (
            <p className="map-origin__line">{WHILE_ASKING.reason}</p>
          ) : null}
          {answer.at === "failed" ? (
            <p className="map-origin__line">
              {`The engine did not answer, so this is the map's shape with an absence wherever a ` +
                `likelihood would have moved. ${answer.reason}`}
            </p>
          ) : null}
          {insteadOfTheEngine === null ? null : (
            <p className="map-origin__line">{insteadOfTheEngine}</p>
          )}
          {(world.warnings ?? []).map((warning) => (
            <p className="map-origin__line" key={warning}>
              {warning}
            </p>
          ))}
        </>
      }
    />
  );
}
