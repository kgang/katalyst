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
import { outlineOf } from "./a11y/sentences";
import type { About, FixtureSummary, Health, Readiness } from "./api/client";
import { readAbout, readExampleList, readHealth, readReadiness } from "./api/client";
import { BranchPanel, InterventionPanel } from "./components/BranchPanel";
import { type Command, CommandPalette } from "./components/CommandPalette";
import { DeltaRail } from "./components/DeltaRail";
import { Inspector } from "./components/Inspector";
import { Launchpad } from "./components/Launchpad";
import { Outline } from "./components/Outline";
import { ShortcutsSheet } from "./components/ShortcutsSheet";
import { MapCanvas } from "./graph/Canvas";
import { bothPaintings } from "./graph/diff/branchWorld";
import { endings, NO_SUMMARY_YET } from "./graph/diff/endings";
import { tileHeight } from "./graph/geometry";
import type { MapKeys } from "./keyboard/useMapKeys";
import {
  appendEdit,
  type BranchView,
  branchesOf,
  type Edit,
  FixtureWorldSource,
  forkBranch,
  openBranch,
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

/** Turn whatever a failed request threw into one sentence. */
function inWords(reason: unknown): string {
  return reason instanceof Error ? reason.message : "The reason was not recorded.";
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
            state: "no key configured — generating a map is not built yet",
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
 * Why the three examples that need the model are not live, in one sentence.
 *
 * Read from the server's own answer rather than written into the page, so that
 * the reason on screen is the real one.
 */
function notLiveReason(answer: Answer<Readiness>): string {
  if (answer.state === "answered" && !answer.value.model_key_present) {
    return "Turning your own words into a map needs the model, and this server has no key for one.";
  }
  return "Turning your own words into a map is not built yet.";
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

/** Which of the two screens is showing. */
type Screen =
  | { at: "launchpad" }
  | { at: "opening"; id: string }
  | { at: "map"; world: WorldView; branches: readonly BranchView[] }
  | { at: "failed"; id: string; reason: string };

/** How long the wires take to arrive, column by column, before the map settles. */
const WAVE_SETTLES_AFTER = 1200;

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
  onLeave,
}: {
  base: WorldView;
  branches: readonly BranchView[];
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
  const [announcement, setAnnouncement] = useState("");
  const [arriving, setArriving] = useState(true);
  const lastBranch = useRef<string | null>(null);

  const open = shop.branches.find((branch) => branch.id === shop.openId);
  const paintings = useMemo(
    () => (open === undefined ? null : bothPaintings(base, open)),
    [base, open],
  );
  const world = paintings === null ? base : showing === "now" ? paintings.now : paintings.before;

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
        reserved.set(claim.id, Math.max(reserved.get(claim.id) ?? 0, tileHeight(claim)));
      }
    }
    return reserved;
  }, [paintings]);

  const rows = useMemo(() => (paintings === null ? [] : endings(paintings.now)), [paintings]);
  const outline = useMemo(() => outlineOf(world), [world]);

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
    const settles = window.setTimeout(() => setArriving(false), WAVE_SETTLES_AFTER);
    if (paintings === null) {
      setAnnouncement("");
      return () => window.clearTimeout(settles);
    }
    setAnnouncement(branchAnnouncement(paintings.now));
    const arrived = paintings.now.claims.find((claim) => claim.diff === "added");
    if (arrived !== undefined) {
      setFocused(arrived.id);
      setSelection({ kind: "claim", id: arrived.id });
      setStatus(`your edit added this claim · ${arrived.claim}`);
    }
    return () => window.clearTimeout(settles);
  }, [shop.openId, paintings]);

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
          <aside className="dock" aria-label="The panel beside the map">
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
                {open === undefined ? null : (
                  <DeltaRail rows={rows} ranked={false} summary={NO_SUMMARY_YET} />
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
      <p className="map-origin">{world.origin}</p>
    </main>
  );
}

/**
 * Where maps come from.
 *
 * Today this reads the stored example the server ships with. When the engine's
 * world route lands, this one line becomes `new ApiWorldSource()` and every
 * number slot that reads as an absence today fills in. Nothing else on this
 * screen changes, which is the whole reason there is a seam here at all.
 */
const DEFAULT_SOURCE: WorldSource = new FixtureWorldSource();

/** What the screen needs. Both have defaults; both exist so they can be swapped. */
export interface AppProps {
  /** Where maps and worlds come from. */
  readonly source?: WorldSource;
  /** How the list of stored examples is read. */
  readonly listExamples?: () => Promise<FixtureSummary[]>;
}

/** The screen. */
export function App({ source = DEFAULT_SOURCE, listExamples = readExampleList }: AppProps = {}) {
  const health = useAnswer(readHealth);
  const readiness = useAnswer(readReadiness);
  const about = useAnswer(readAbout);
  const examples = useAnswer(listExamples);

  const [screen, setScreen] = useState<Screen>({ at: "launchpad" });

  const open = useCallback(
    (id: string) => {
      setScreen({ at: "opening", id });
      // The world and the map's own branches, together: the world is what gets
      // drawn, and the branches are the edits somebody already made to it, which
      // the panel lists and the diff view folds on. Both come from the same
      // stored example through the same seam.
      Promise.all([source.readWorld({ baseId: id }), source.readBundle(id)]).then(
        ([world, bundle]) => setScreen({ at: "map", world, branches: branchesOf(bundle) }),
        (reason: unknown) => setScreen({ at: "failed", id, reason: inWords(reason) }),
      );
    },
    [source],
  );

  const toLaunchpad = useCallback(() => setScreen({ at: "launchpad" }), []);

  const readings = useMemo(
    () => [serverReading(health), modelKeyReading(readiness), versionReading(about)],
    [health, readiness, about],
  );

  if (screen.at === "map") {
    return <MapScreen base={screen.world} branches={screen.branches} onLeave={toLaunchpad} />;
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
              ? `Reading the stored map from /api/fixtures/${screen.id}.`
              : screen.reason}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="column">
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
          notLiveReason={notLiveReason(readiness)}
          onOpen={open}
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
