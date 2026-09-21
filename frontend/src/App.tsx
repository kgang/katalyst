/**
 * The whole screen: the launchpad, and the map you open from it.
 *
 * Two states and nothing in between. The launchpad names the two ways into the
 * tool and offers the four examples from the brief; opening the one that is
 * built swaps the page for the map. Everything on the map came over the wire
 * from the server, and the line under it says which address it came from — this
 * product does not put a number on screen that a reader cannot trace to an
 * input, a rule or a source, and that includes numbers a stored example happens
 * to carry.
 *
 * There is no spinner anywhere, and there never will be. A spinner says "wait"
 * without saying what for. While something is on its way the screen says what
 * it is waiting for and where it asked.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { branchAnnouncement } from "./a11y/announcement";
import { growthAnnouncement } from "./a11y/growth";
import { outlineOf } from "./a11y/sentences";
import type { About, FixtureSummary, Health } from "./api/client";
import { RefusedBranch, readAbout, readExampleList, readHealth, readReadiness } from "./api/client";
import { AddAClaim } from "./components/AddAClaim";
import { BranchPanel, InterventionPanel } from "./components/BranchPanel";
import { type Command, CommandPalette } from "./components/CommandPalette";
import { DeltaRail } from "./components/DeltaRail";
import { DoneLine } from "./components/DoneLine";
import type { Asked } from "./components/InputBar";
import { Inspector } from "./components/Inspector";
import { Launchpad } from "./components/Launchpad";
import { Outline } from "./components/Outline";
import { ReceiptStrip } from "./components/ReceiptStrip";
import { Refusal } from "./components/Refusal";
import { RefusalStrip } from "./components/RefusalStrip";
import { ReplayBadge, replaySentence } from "./components/ReplayBadge";
import { ShortcutsSheet } from "./components/ShortcutsSheet";
import { VerdictCard } from "./components/VerdictCard";
import "./components/generationDock.css";
import { MapCanvas } from "./graph/Canvas";
import { bothPaintings, type Engine, railRows } from "./graph/diff/branchWorld";
import { endings, NO_SUMMARY_YET } from "./graph/diff/endings";
import { roomFor } from "./graph/geometry";
import type { MapKeys } from "./keyboard/useMapKeys";
import { generate } from "./stream/generate";
import type { Growth } from "./stream/growth";
import { fold, waitingFor } from "./stream/growth";
import type { Readiness } from "./stream/readiness";
import { withRecordings } from "./stream/readiness";
import type { Working } from "./stream/transcript";
import { readTranscript } from "./stream/transcript";
import {
  type Absence,
  ApiWorldSource,
  appendEdit,
  type BranchView,
  branchesOf,
  type DiffView,
  type Edit,
  FixtureWorldSource,
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
} from "./world";

/**
 * Everything the screen can know about one thing it asked for. Three states and
 * no others, which is what makes every pixel below traceable to a cause.
 */
type Answer<Reading> =
  | { state: "asking" }
  | { state: "answered"; value: Reading }
  | { state: "failed"; reason: string };

/** How loud a row's words are. Emphasis only — the words carry the meaning. */
type Tone = "good" | "quiet" | "loud";

/** One row of the strip at the foot of the launchpad. */
interface Reading {
  /** What is being reported, such as "server". */
  label: string;
  /** The value from the server, or null while the request is still in flight. */
  value: string | null;
  /** A mark beside the words. Never the only carrier of meaning. */
  glyph: string;
  /** What the value means, in plain words. On a failure, this is the failure. */
  state: string;
  tone: Tone;
}

/**
 * Whether the panel beside the map has more above and more below what it is
 * showing.
 *
 * **The panel measures itself.** It is the one scrolling thing on this screen,
 * and a reader has to be able to tell a control that is not there from a control
 * that is merely below the fold. A scrollbar cannot tell them: on a Mac it is an
 * overlay that fades in on a gesture, so it speaks only to somebody who is
 * already scrolling.
 *
 * It is watched three ways because the panel changes for three different
 * reasons: the reader scrolls it, a claim arrives and makes it taller, and the
 * window is resized and makes it shorter. Missing any one of them leaves a rule
 * drawn at an edge with nothing beyond it, which is the panel claiming something
 * a reader can check in one gesture.
 */
function useTheEdgesOfThePanel(): {
  panel: React.RefObject<HTMLElement | null>;
  above: boolean;
  below: boolean;
} {
  const panel = useRef<HTMLElement | null>(null);
  const [edges, setEdges] = useState({ above: false, below: false });

  useEffect(() => {
    const it = panel.current;
    if (it === null) {
      return;
    }
    const measure = (): void => {
      // A pixel of slack, because a panel scrolled to its very end lands a
      // fraction short of its own height often enough to matter.
      const above = it.scrollTop > 1;
      const below = it.scrollTop + it.clientHeight < it.scrollHeight - 1;
      setEdges((was) => (was.above === above && was.below === below ? was : { above, below }));
    };
    measure();
    it.addEventListener("scroll", measure, { passive: true });
    // Watching a box change size is the browser's own job, and a page that
    // cannot do it — a simulated one in a test — still gets the scrolling half
    // rather than nothing at all.
    const watching =
      typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(measure);
    watching?.observe(it);
    for (const child of it.children) {
      watching?.observe(child);
    }
    return () => {
      it.removeEventListener("scroll", measure);
      watching?.disconnect();
    };
  });

  return { panel, above: edges.above, below: edges.below };
}

/** Turn whatever a failed request threw into one sentence. */
function inWords(reason: unknown): string {
  return reason instanceof Error ? reason.message : "The reason was not recorded.";
}

/**
 * Ask what this copy can do, and read the list of recordings off the answer.
 *
 * Defined at module level because the hook below runs it once and needs the same
 * function on every render.
 */
function askReadiness(): Promise<Readiness> {
  return readReadiness().then(withRecordings);
}

/**
 * Make one request when the screen first appears and report where it got to.
 *
 * @param ask The request to make. It must be the same function on every render,
 *   so pass one defined at module level rather than one written inline.
 */
function useAnswer<Reading>(ask: () => Promise<Reading>): Answer<Reading> {
  const [answer, setAnswer] = useState<Answer<Reading>>({ state: "asking" });

  useEffect(() => {
    let stillOnScreen = true;
    ask().then(
      (value) => {
        if (stillOnScreen) {
          setAnswer({ state: "answered", value });
        }
      },
      (reason: unknown) => {
        if (stillOnScreen) {
          setAnswer({ state: "failed", reason: inWords(reason) });
        }
      },
    );
    return () => {
      stillOnScreen = false;
    };
  }, [ask]);

  return answer;
}

/** The row that says whether the server answered at all. */
function serverReading(answer: Answer<Health>): Reading {
  switch (answer.state) {
    case "asking":
      return {
        label: "server",
        value: null,
        glyph: "○",
        state: "asking the server",
        tone: "quiet",
      };
    case "answered":
      return {
        label: "server",
        value: answer.value.status,
        glyph: "●",
        state: "reachable",
        tone: "good",
      };
    case "failed":
      return { label: "server", value: "—", glyph: "○", state: answer.reason, tone: "loud" };
  }
}

/** The row that says whether a key for the language model is configured. */
function modelKeyReading(answer: Answer<Readiness>): Reading {
  switch (answer.state) {
    case "asking":
      return {
        label: "model key",
        value: null,
        glyph: "○",
        state: "asking the server",
        tone: "quiet",
      };
    case "answered":
      return answer.value.model_key_present
        ? {
            label: "model key",
            value: "present",
            glyph: "●",
            state: "ready to generate",
            tone: "good",
          }
        : {
            label: "model key",
            value: "absent",
            glyph: "○",
            state:
              answer.value.replayable.length === 0
                ? "no key configured, and nothing recorded to play instead"
                : `no key configured — ${answer.value.replayable.length} example(s) play from recordings`,
            tone: "quiet",
          };
    case "failed":
      return { label: "model key", value: "—", glyph: "○", state: answer.reason, tone: "loud" };
  }
}

/** The row that says which build answered. */
function versionReading(answer: Answer<About>): Reading {
  switch (answer.state) {
    case "asking":
      return {
        label: "version",
        value: null,
        glyph: "○",
        state: "asking the server",
        tone: "quiet",
      };
    case "answered":
      return {
        label: "version",
        value: answer.value.version,
        glyph: "●",
        state: `reported by ${answer.value.name}`,
        tone: "good",
      };
    case "failed":
      return { label: "version", value: "—", glyph: "○", state: answer.reason, tone: "loud" };
  }
}

/**
 * One row: a label, the value the server gave, and what that value means.
 *
 * While the value is missing the cell holds a bar of the same height, so the
 * row does not change size when the answer arrives. There is no spinner: a bar
 * where the value will land says the same thing without pretending to spin.
 */
function StatusRow({ reading }: { reading: Reading }) {
  const waiting = reading.value === null;
  return (
    <div className="status-row">
      <dt className="status-label">{reading.label}</dt>
      <dd className="status-value" data-settled={waiting ? "no" : "yes"}>
        {waiting ? <span className="placeholder" aria-hidden="true" /> : reading.value}
      </dd>
      <dd className="status-state" data-tone={reading.tone}>
        <span className="glyph" aria-hidden="true">
          {reading.glyph}
        </span>
        <span className="state-words">{reading.state}</span>
      </dd>
    </div>
  );
}

/** Which of the screens is showing. */
type Screen =
  | { at: "launchpad" }
  | { at: "opening"; id: string }
  /** A map being built in front of the reader, from a sentence they typed. */
  | { at: "growing"; asked: Asked }
  | {
      at: "map";
      world: WorldView;
      branches: readonly BranchView[];
      /**
       * Why the map on screen was read from the stored example rather than
       * worked out by the engine, or nothing when the engine answered.
       */
      insteadOfTheEngine: string | null;
    }
  | { at: "failed"; id: string; reason: string };

/** How long the wires take to arrive, column by column, before the map settles. */
const WAVE_SETTLES_AFTER = 1200;

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
const WHILE_ASKING: Absence = {
  kind: "no_engine",
  words: "no engine yet",
  reason:
    "The engine has been asked at /api/worlds for the map with this branch folded onto it, and " +
    "has not answered. Nothing has worked this number through the map yet.",
};

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
const REFUSED: Absence = {
  kind: "refused",
  words: "not worked out",
  reason:
    "The engine would not work this map out from this branch: the branch does not fit the map. " +
    "Every reason is beside the map, and nothing on the map has changed.",
};

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
  return {
    kind: "ask_failed",
    words: "the ask did not come back",
    reason: `${reason} Nothing on the map has changed; opening the branch again asks once more.`,
  };
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
  return { at: "failed", reason: inWords(reason) };
}

/**
 * The map, the panel beside it, and everything you can do to both.
 *
 * Three things live here rather than inside the map, because all three are about
 * the whole screen rather than about the picture: which branch is open, which of
 * the two worlds is painted, and what the keyboard is on.
 */
function MapScreen({
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
  const [dock, setDock] = useState<"panel" | "outline" | "away">("panel");
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
  const { panel, above: moreAbove, below: moreBelow } = useTheEdgesOfThePanel();

  const open = shop.branches.find((branch) => branch.id === shop.openId);

  // What the engine says about the branch that is open. It is asked again
  // whenever the branch changes — which is what makes the six buttons move
  // numbers: pressing one appends an edit, and the whole branch goes back.
  const [answer, setAnswer] = useState<Answered>({ at: "nothing-open" });
  useEffect(() => {
    if (open === undefined) {
      setAnswer({ at: "nothing-open" });
      return;
    }
    let stillWanted = true;
    setAnswer({ at: "asking" });
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
            absence: {
              kind: "ask_failed",
              words: "the ask did not come back",
              reason: `${inWords(failure)} Select this arrow again to ask once more.`,
            },
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

  const keys: MapKeys = useMemo(
    () => ({
      intervene: () => {
        setDock("panel");
        setIntervening(true);
      },
      branch: () => {
        setDock("panel");
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
      outline: () =>
        setDock((was) => {
          setOnlyColumn(null);
          return was === "outline" ? "panel" : "outline";
        }),
      panel: () => setDock((was) => (was === "away" ? "panel" : "away")),
      palette: () => setOverlay("palette"),
    }),
    [paintings],
  );

  // ⌘K, ? and Escape work wherever you are on the screen, not only on the map,
  // because two of them are how you find out what the others do.
  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable === true;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOverlay((was) => (was === "palette" ? null : "palette"));
        return;
      }
      if (event.key === "Escape") {
        setOverlay(null);
        setIntervening(false);
        setNaming(false);
        return;
      }
      if (event.key === "?" && !typing) {
        event.preventDefault();
        setOverlay((was) => (was === "sheet" ? null : "sheet"));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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
          setDock("outline");
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

  return (
    <main className="page page--map">
      <header className="map-bar">
        <button className="map-bar__back" type="button" onClick={onLeave}>
          <span aria-hidden="true">←</span> Back to the launchpad
        </button>
        <h1 className="map-bar__title">{base.title}</h1>
        {open === undefined ? (
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
        )}
        <button className="map-bar__sheet" type="button" onClick={() => setOverlay("sheet")}>
          Every key (?)
        </button>
      </header>

      {/* The map and the panel, side by side. The panel is part of the screen
          rather than something that appears over it: there are no pop-ups
          anywhere in this product, and a dialog you have to dismiss would steal
          the map that makes the detail mean anything. */}
      <div className="map-body">
        <div className="map-stage">
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
              setDock("outline");
            }}
            arriving={arriving}
          />
          {overlay === "palette" ? (
            <CommandPalette open={true} onClose={() => setOverlay(null)} commands={commands} />
          ) : null}
          {overlay === "sheet" ? (
            <ShortcutsSheet open={true} onClose={() => setOverlay(null)} />
          ) : null}
          <p className="map-status">
            <span className="map-status__mark">last key</span>
            {status}
          </p>
        </div>

        {dock === "away" ? null : (
          <aside
            className="dock"
            ref={panel}
            data-more-above={moreAbove ? "yes" : "no"}
            data-more-below={moreBelow ? "yes" : "no"}
            aria-label="The panel beside the map"
          >
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
            ) : (
              <>
                {intervening ? (
                  <InterventionPanel
                    world={world}
                    selection={selection}
                    onEdit={edit}
                    onClose={() => setIntervening(false)}
                  />
                ) : null}
                <BranchPanel
                  branches={shop.branches}
                  openId={shop.openId}
                  world={world}
                  onOpen={(id) => setShop((was) => openBranch(was, id))}
                  onFork={(label) => setShop((was) => forkBranch(was, label))}
                  naming={naming}
                  onNaming={setNaming}
                />
                {answer.at === "refused" ? (
                  <Refusal asking="this map" reasons={answer.reasons} />
                ) : null}
                {open === undefined ? null : (
                  <DeltaRail
                    rows={rows}
                    ranked={computed !== undefined}
                    summary={computed === undefined ? NO_SUMMARY_YET : computed.change.summary}
                  />
                )}
                <Inspector world={world} selection={selection} />
              </>
            )}
          </aside>
        )}
      </div>

      {/* What a branch did, said out loud for a reader who is not looking at the
          picture. Polite: it waits for a pause rather than cutting across
          whatever is being read. */}
      <p className="map-live" aria-live="polite">
        {announcement}
      </p>

      {/* Where every number on this map came from, and anything that is still on
          its way. There is no spinner here and never will be: a spinner says
          "wait" without saying what for, so the line says what has been asked
          and at which address, and the map keeps drawing the last answer while
          it waits. */}
      <div className="map-origin">
        <p className="map-origin__line">{world.origin}</p>
        {answer.at === "asking" ? <p className="map-origin__line">{WHILE_ASKING.reason}</p> : null}
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
      </div>
    </main>
  );
}

/* ---- A map being built in front of you ----------------------------------- */

/**
 * Run one generation and fold what comes back into what the screen knows.
 *
 * **No component talks to the network**: this hook holds the one request, and
 * everything on screen is drawn from the state it folds. The run stops when the
 * reader leaves the page, which is what stops the spending — the route checks
 * whether the client is still there before its next model call.
 *
 * @param asked The sentence, the destination if there was one, and the reader's
 *   own likelihood if they gave one.
 */
function useGeneration(asked: Asked): Growth {
  const [growth, setGrowth] = useState<Growth>(() => waitingFor(asked.hypothesis, asked.target));

  useEffect(() => {
    const stop = new AbortController();
    let stillOnScreen = true;
    setGrowth(waitingFor(asked.hypothesis, asked.target));

    const run = async (): Promise<void> => {
      const stream = generate(
        {
          hypothesis: asked.hypothesis,
          ...(asked.target === null ? {} : { target: asked.target }),
          // "I don't know" sends nothing at all. Not a half, not a wide band.
          ...(asked.belief === null ? {} : { user_belief: asked.belief }),
        },
        { signal: stop.signal },
      );
      for await (const event of stream) {
        if (!stillOnScreen) {
          return;
        }
        setGrowth((was) => fold(was, event));
      }
    };

    run().catch((failure: unknown) => {
      if (!stillOnScreen) {
        return;
      }
      // Never reaching the route at all is the one thing that is not an event:
      // there is no stream to read and nothing to draw, so it is folded in by
      // hand as the sentence the failure arrived with.
      setGrowth((was) => fold(was, { event: "failed", message: inWords(failure) }));
    });

    return () => {
      stillOnScreen = false;
      stop.abort();
    };
  }, [asked.hypothesis, asked.target, asked.belief]);

  return growth;
}

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
 */
function GenerationScreen({
  asked,
  replaying,
  onLeave,
}: {
  asked: Asked;
  /**
   * True when this copy has no model key, so the run is a recording being played
   * back. Known before the stream says anything, which is why the badge can be
   * on screen from the first frame.
   */
  replaying: boolean;
  onLeave: () => void;
}) {
  const growth = useGeneration(asked);
  const [selection, setSelection] = useState<Selection>(null);
  const [focused, setFocused] = useState<string | null>(null);
  const [overlay, setOverlay] = useState<"sheet" | null>(null);
  const [dock, setDock] = useState<"panel" | "outline">("panel");
  const [openAt, setOpenAt] = useState<number | null>(null);
  const [status, setStatus] = useState(
    "Press ? for every key. j and k walk a column; h and l follow the wires.",
  );
  const [working, setWorking] = useState<Working>({ state: "reading" });
  const { panel, above: moreAbove, below: moreBelow } = useTheEdgesOfThePanel();

  const { generationId, phase } = growth;
  const finished = phase === "settled" || phase === "stopped" || phase === "failed";

  // The working of the run, read once the run has finished. It is asked for then
  // rather than as it goes, because the server writes it from the same pass that
  // writes the stream and a half-read one would be a second, staler copy.
  useEffect(() => {
    if (generationId === null || !finished) {
      return;
    }
    let stillWanted = true;
    readTranscript(generationId).then((read) => {
      if (stillWanted) {
        setWorking(read);
      }
    });
    return () => {
      stillWanted = false;
    };
  }, [generationId, finished]);

  const outline = useMemo(() => outlineOf(growth.world), [growth.world]);
  const announcement = useMemo(() => growthAnnouncement(growth), [growth]);

  // The keyboard follows the growing edge: a claim that has just arrived takes
  // focus, exactly as a claim a branch adds does. That is what keeps the newest
  // tile on the glass through a run that goes on for minutes — the canvas
  // already brings whatever the keyboard is on into view, so nothing here
  // re-frames the map and nothing re-lays it out. A tile that is already placed
  // stays exactly where it is; what moves is where the reader is looking.
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

  return (
    <main className="page page--map">
      <header className="map-bar">
        <button className="map-bar__back" type="button" onClick={onLeave}>
          <span aria-hidden="true">←</span> Back to the launchpad
        </button>
        <h1 className="map-bar__title">{growth.world.title}</h1>
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
          {asked.target === null ? "Explore" : "Verify"}
          <span className="map-bar__side">
            {asked.target === null ? "what your sentence would cause" : asked.target}
          </span>
        </p>
        <button className="map-bar__sheet" type="button" onClick={() => setOverlay("sheet")}>
          Every key (?)
        </button>
      </header>

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
          data-more-above={moreAbove ? "yes" : "no"}
          data-more-below={moreBelow ? "yes" : "no"}
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
              {growth.verdict === null || asked.target === null ? null : (
                <VerdictCard
                  verdict={growth.verdict}
                  target={asked.target}
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
                <AddAClaim
                  baseId={growth.world.baseId}
                  andThen="It is checked against this map and ready to go onto a branch of it."
                />
              ) : null}

              <Inspector
                world={growth.world}
                selection={selection}
                generation={{
                  receipt: growth.receipt,
                  working,
                  unknown: growth.unknown,
                  openAt,
                }}
              />
            </>
          )}
        </aside>
      </div>

      {/* Said out loud, and said once. On a stored map this line is on the page
          as well; here the same facts are already drawn — the claims on the
          canvas, the refusals in the panel, why the run stopped under the map —
          so printing them again made the foot of the screen three strips of
          prose saying the same thing twice. It stays the spoken channel. */}
      <p className="map-live map-live--spoken" aria-live="polite">
        {announcement}
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
        <DoneLine done={growth.done} failure={growth.failure} />
        {(growth.world.warnings ?? []).map((warning) => (
          <p className="map-origin__line" key={warning}>
            {warning}
          </p>
        ))}
      </div>
    </main>
  );
}

/**
 * Where maps come from: the engine.
 *
 * Every number on the map is worked out by it, from the stored map, the branch
 * and one seed. Nothing on this screen computes a likelihood, and nothing on
 * this screen shows one the engine did not produce.
 */
const DEFAULT_SOURCE: WorldSource = new ApiWorldSource();

/**
 * Where maps come from when the engine cannot be reached.
 *
 * A map you can still read beats a blank screen. The stored example's claims,
 * arrows, dates and sources are all real and all still worth reading — what is
 * missing is the working-out, and the screen says so in a line under the map
 * rather than letting a hand-written likelihood pass for a computed one.
 */
const FALLBACK_SOURCE: WorldSource = new FixtureWorldSource();

/**
 * The line under the map when the stored example is standing in for the engine.
 *
 * @param reason What went wrong, in the sentence the failure arrived with.
 */
function insteadOfTheEngine(reason: string): string {
  return (
    `The engine did not answer, so this map is the stored example exactly as it was written: ` +
    `its claims, arrows, dates and sources are real, and its likelihoods are the illustrative ` +
    `ones somebody wrote down rather than anything worked out. ${reason}`
  );
}

/** What the screen needs. All three have defaults; all three exist so they can be swapped. */
export interface AppProps {
  /** Where maps and worlds come from. */
  readonly source?: WorldSource;
  /** Where they come from when the first one cannot answer. */
  readonly fallback?: WorldSource;
  /** How the list of stored examples is read. */
  readonly listExamples?: () => Promise<FixtureSummary[]>;
}

/** The screen. */
export function App({
  source = DEFAULT_SOURCE,
  fallback = FALLBACK_SOURCE,
  listExamples = readExampleList,
}: AppProps = {}) {
  const health = useAnswer(readHealth);
  const readiness = useAnswer(askReadiness);
  const about = useAnswer(readAbout);
  const examples = useAnswer(listExamples);

  const [screen, setScreen] = useState<Screen>({ at: "launchpad" });
  const [using, setUsing] = useState<WorldSource>(source);

  const open = useCallback(
    (id: string) => {
      setScreen({ at: "opening", id });
      /**
       * The world and the map's own branches, together: the world is what gets
       * drawn, and the branches are the edits somebody already made to it, which
       * the panel lists and the diff view folds on.
       *
       * @param from Where to ask.
       */
      const ask = (from: WorldSource) =>
        Promise.all([from.readWorld({ baseId: id }), from.readBundle(id)]);

      ask(source).then(
        ([world, bundle]) => {
          setUsing(source);
          setScreen({ at: "map", world, branches: branchesOf(bundle), insteadOfTheEngine: null });
        },
        (failure: unknown) => {
          // The engine could not answer. Rather than a blank screen, the stored
          // example — and a line under the map saying, in the failure's own
          // words, that these are not computed numbers.
          ask(fallback).then(
            ([world, bundle]) => {
              setUsing(fallback);
              setScreen({
                at: "map",
                world,
                branches: branchesOf(bundle),
                insteadOfTheEngine: insteadOfTheEngine(inWords(failure)),
              });
            },
            // Neither answered, which means the server itself is not there. That
            // is one sentence on the page, and a way back to the launchpad.
            (alsoFailed: unknown) => setScreen({ at: "failed", id, reason: inWords(alsoFailed) }),
          );
        },
      );
    },
    [source, fallback],
  );

  const toLaunchpad = useCallback(() => setScreen({ at: "launchpad" }), []);

  /** Build a map from a sentence, and watch it arrive. */
  const build = useCallback((asked: Asked) => setScreen({ at: "growing", asked }), []);

  const readings = useMemo(
    () => [serverReading(health), modelKeyReading(readiness), versionReading(about)],
    [health, readiness, about],
  );

  if (screen.at === "growing") {
    return (
      <GenerationScreen
        asked={screen.asked}
        // Known before the stream has said anything, which is the whole reason
        // the badge can be on screen from the first frame. When the receipt
        // arrives it is the authority, and the badge takes its word.
        replaying={readiness.state === "answered" && !readiness.value.model_key_present}
        onLeave={toLaunchpad}
      />
    );
  }

  if (screen.at === "map") {
    return (
      <MapScreen
        base={screen.world}
        branches={screen.branches}
        source={using}
        insteadOfTheEngine={screen.insteadOfTheEngine}
        onLeave={toLaunchpad}
      />
    );
  }

  if (screen.at !== "launchpad") {
    return (
      <main className="page page--map">
        <header className="map-bar">
          <button className="map-bar__back" type="button" onClick={toLaunchpad}>
            <span aria-hidden="true">←</span> Back to the launchpad
          </button>
          <h1 className="map-bar__title">Strait of Hormuz</h1>
        </header>

        <div className="map-waiting">
          <p className="map-waiting__line">
            {screen.at === "opening"
              ? `Reading the map from /api/fixtures/${screen.id} and asking /api/worlds to work ` +
                `its likelihoods through.`
              : screen.reason}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      {/* The first screen is the one wide column in this product: it holds the
          two doors, a map that is already drawn, the four sentences from the
          brief and the field you type your own into, and stacking all of that
          in the 660-pixel measure the rest of the page reads at pushes the
          field below the fold. `launchpad.css` owns the width. */}
      <div className="column column--launchpad">
        <header className="masthead">
          <h1 className="wordmark">Katalyst</h1>
          <p className="purpose">
            Type an event you think will happen. See what it would cause, step by step, ending in
            trades.
          </p>
        </header>

        <Launchpad
          examples={examples.state === "answered" ? examples.value : null}
          failure={examples.state === "failed" ? examples.reason : null}
          readiness={readiness.state === "answered" ? readiness.value : null}
          onOpen={open}
          onBuild={build}
        />

        <section aria-labelledby="status-heading">
          <h2 className="section-heading" id="status-heading">
            What this build can do right now
          </h2>
          <dl className="status-strip">
            {readings.map((reading) => (
              <StatusRow key={reading.label} reading={reading} />
            ))}
          </dl>
          <p className="provenance">
            Every reading above came from the server, at <code>/api/healthz</code>,{" "}
            <code>/api/readyz</code> and <code>/api/about</code>. The examples came from{" "}
            <code>/api/fixtures</code>. Nothing on this screen is written into the page.
          </p>
        </section>
      </div>
    </main>
  );
}
