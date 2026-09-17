/**
 * The branch panel: your edits, in the order you made them — and the six things
 * you can do to a claim.
 *
 * **A sequence, not a surprise.** Read as a list, the rule that a later edit
 * outranks an earlier supposition is obvious: you supposed the strait reopens,
 * then you added a strike, then you supposed the strike lands, and the strike's
 * arrow was added *after* the supposition, so it is live. Met instead as a number
 * that moved on its own, the same rule reads as a bug. So the sequence is on the
 * screen.
 *
 * **Edits are appended, never rewritten.** There is no way to edit an edit here,
 * and that is deliberate: the branch is the audit trail, and an audit trail you
 * can edit is not one.
 *
 * **The buttons build a branch, and the engine moves the numbers.** Pressing one
 * appends an edit and the panel shows it immediately; the whole branch is then
 * handed to the engine, which works the map's likelihoods through again and says
 * what moved. Nothing on this side works out a number — appending an edit is the
 * whole of what a button does.
 *
 * **Two of the six say what they cannot do rather than doing it quietly.**
 * *Split this claim* is not built. *Add a claim* needs the part of this product
 * that drafts a whole claim — the wording, the test that settles it, its judge
 * and its date — and that is not connected. Neither is greyed out: a disabled
 * control says "not for you" and nothing else, and cannot even be asked about
 * with the keyboard.
 *
 * **Nothing here opens over the map.** No dialog, no scrim, nothing to dismiss:
 * the fields below appear inside this panel, beside the map, which stays live.
 */

import { useState } from "react";
import { toDay } from "../graph/diff/days";
import { pushAsNumber, pushInWords } from "../graph/wires/encodings";
import type { BranchView, Edit, Selection, WorldView } from "../world";
import "./branchPanel.css";

/**
 * The six buttons, word for word from the shared vocabulary's *Interface words*
 * table, and the badge each one earns.
 *
 * Copied, never paraphrased. The six operations keep their code names in the
 * code, in the wire format and in the spec, and **not one of those names ever
 * appears on screen.**
 */
const BUTTONS = {
  supposeTrue: "Suppose this is true",
  supposeFalse: "Suppose this is false",
  happened: "This happened",
  addClaim: "Add a claim",
  changePush: "Change this push",
  splitClaim: "Split this claim",
  ownNumber: "My own number",
} as const;

/** How one edit reads in the list: which button made it, and what it was about. */
function editLine(edit: Edit, world: WorldView): { button: string; about: string; badge: string } {
  const words = (id: string): string => world.claims.find((claim) => claim.id === id)?.claim ?? id;
  switch (edit.op) {
    case "do":
      return {
        button: edit.value ? BUTTONS.supposeTrue : BUTTONS.supposeFalse,
        about: words(edit.target),
        badge: `Supposed · ${toDay(edit.at)}`,
      };
    case "observe":
      return {
        button: BUTTONS.happened,
        about: words(edit.target),
        badge: `Happened · ${toDay(edit.at)}`,
      };
    case "insert":
      return { button: BUTTONS.addClaim, about: edit.words, badge: "Added" };
    case "retune":
      return {
        button: BUTTONS.changePush,
        about:
          `You moved this arrow from ${pushAsNumber(edit.wasStrength)} to ` +
          `${pushAsNumber(edit.strength)} — ${pushInWords(edit.strength)}.`,
        badge: "Retuned",
      };
    case "refine":
      return { button: BUTTONS.splitClaim, about: words(edit.target), badge: "Split" };
    case "believe":
      return {
        button: BUTTONS.ownNumber,
        about: words(edit.target),
        badge: "",
      };
  }
}

/** What the branch panel needs. */
export interface BranchPanelProps {
  /** Every branch on this map, in the order they arrived. */
  readonly branches: readonly BranchView[];
  /** Which branch is open, or `null` for the map as it was written. */
  readonly openId: string | null;
  /** The world on screen, so an edit can be read back in the claim's own words. */
  readonly world: WorldView;
  /** Open a branch, or go back to the map as it was written. */
  readonly onOpen: (id: string | null) => void;
  /** Start a new branch with this name. */
  readonly onFork: (label: string) => void;
  /** Whether the name field is open, because `B` opens it from the map. */
  readonly naming: boolean;
  /** Open or close the name field. */
  readonly onNaming: (open: boolean) => void;
}

/** The branch panel. */
export function BranchPanel({
  branches,
  openId,
  world,
  onOpen,
  onFork,
  naming,
  onNaming,
}: BranchPanelProps) {
  const [name, setName] = useState("");
  const open = branches.find((branch) => branch.id === openId);

  return (
    <section className="branch-panel" aria-label="Your branches">
      <h2 className="branch-panel__heading">Branches</h2>

      <ul className="branch-panel__list">
        <li>
          <button
            className="branch-panel__branch"
            type="button"
            data-open={openId === null ? "yes" : "no"}
            onClick={() => onOpen(null)}
          >
            <span className="branch-panel__chip" data-hue="base" aria-hidden="true" />
            <span className="branch-panel__name">The map as it was written</span>
          </button>
        </li>
        {branches.map((branch) => (
          <li key={branch.id}>
            <button
              className="branch-panel__branch"
              type="button"
              data-open={openId === branch.id ? "yes" : "no"}
              onClick={() => onOpen(branch.id)}
            >
              {/* A branch's hue is on its chip and its lane and nowhere else, and
                  the chip always carries the branch's name — so which branch you
                  are in is readable with no colour at all. */}
              <span className="branch-panel__chip" data-hue={branch.hue} aria-hidden="true" />
              <span className="branch-panel__name">{branch.label}</span>
              <span className="branch-panel__count">
                {branch.edits.length === 1 ? "1 edit" : `${branch.edits.length} edits`}
              </span>
            </button>
          </li>
        ))}
      </ul>

      {naming ? (
        <form
          className="branch-panel__naming"
          onSubmit={(event) => {
            event.preventDefault();
            const label = name.trim();
            if (label !== "") {
              onFork(label);
              setName("");
              onNaming(false);
            }
          }}
        >
          <label className="branch-panel__field-label" htmlFor="branch-name">
            What is this branch called? An unnamed branch is unusable once there are three.
          </label>
          <input
            className="branch-panel__field"
            id="branch-name"
            value={name}
            // biome-ignore lint/a11y/noAutofocus: the reader pressed B to open this field and the next thing they will do is type into it; sending focus anywhere else is a keystroke thrown away.
            autoFocus
            onChange={(event) => setName(event.target.value)}
          />
          <div className="branch-panel__field-actions">
            <button className="branch-panel__go" type="submit">
              Start this branch
            </button>
            <button
              className="branch-panel__cancel"
              type="button"
              onClick={() => {
                setName("");
                onNaming(false);
              }}
            >
              Not now
            </button>
          </div>
        </form>
      ) : (
        <button className="branch-panel__fork" type="button" onClick={() => onNaming(true)}>
          Start a branch
        </button>
      )}

      {open === undefined ? (
        // Where the numbers on the unedited map came from — and there are two
        // answers, told apart by the one thing that says whether anything was
        // worked out: whether the world reports how many versions of the map
        // were run. The engine's answer and the stored example's own numbers are
        // different claims about the world, and a screen that said the same
        // sentence over both would be making the weaker one silently.
        <p className="branch-panel__none">
          {world.versions === undefined
            ? "Nothing has been edited. The map above is exactly as it was written, and every " +
              "number on it is the one the stored example carries — nothing has worked one out."
            : "Nothing has been edited. The map above is exactly as it was written, and every " +
              "number on it was worked out by the engine from that map with nothing done to it."}
        </p>
      ) : (
        <ol className="branch-panel__edits">
          {open.edits.map((edit, index) => {
            const line = editLine(edit, world);
            return (
              // biome-ignore lint/suspicious/noArrayIndexKey: a branch is append-only — no edit is ever rewritten, removed or reordered — so an edit's place in the list is a stable name for it, and it is the name the panel prints beside it.
              <li className="branch-panel__edit" key={`${index}-${line.button}`}>
                <span className="branch-panel__number">{index + 1}</span>
                <span className="branch-panel__about">
                  <span className="branch-panel__button-name">{line.button}</span>
                  <span className="branch-panel__subject">{line.about}</span>
                </span>
                {line.badge === "" ? (
                  <span className="branch-panel__no-badge">
                    no badge — the three-up belief chip is the badge
                  </span>
                ) : (
                  <span className="branch-panel__badge">{line.badge}</span>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

/** What the six-button panel needs. */
export interface InterventionPanelProps {
  /** The world on screen. */
  readonly world: WorldView;
  /** What the map is open on: the claim or the arrow the buttons act on. */
  readonly selection: Selection;
  /** Append an edit to the open branch. */
  readonly onEdit: (edit: Edit) => void;
  /** Close the panel. */
  readonly onClose: () => void;
}

/**
 * The six things you can do to a claim, in a panel beside the map.
 *
 * Never a pop-up: it appears in the panel, the map keeps drawing beside it, and
 * closing it loses nothing because nothing is left half-done.
 */
export function InterventionPanel({ world, selection, onEdit, onClose }: InterventionPanelProps) {
  const [ownNumber, setOwnNumber] = useState(false);
  const [reading, setReading] = useState({ p: "", lo: "", hi: "" });
  const [pushing, setPushing] = useState(false);
  const [push, setPush] = useState("");
  const [said, setSaid] = useState<string | null>(null);

  const claim =
    selection?.kind === "claim" ? world.claims.find((one) => one.id === selection.id) : undefined;
  const wire =
    selection?.kind === "wire" ? world.links.find((one) => one.id === selection.id) : undefined;

  const say = (line: string) => setSaid(line);

  /**
   * Nothing here is ever disabled. A greyed-out button says "not for you" and
   * nothing else — and it is unreachable by keyboard, which makes it a control a
   * reader cannot even ask about. So a button with nothing to act on says what it
   * needs instead.
   */
  const needsAClaim = (): boolean => {
    if (claim !== undefined) {
      return false;
    }
    say(
      "Choose a claim on the map first — click it, or reach it with the keyboard and the panel " +
        "opens on it.",
    );
    return true;
  };

  return (
    <section className="intervene" aria-label="Change this claim">
      <header className="intervene__head">
        <h2 className="intervene__heading">Change this</h2>
        <button className="intervene__close" type="button" onClick={onClose}>
          Done
        </button>
      </header>

      <p className="intervene__subject">
        {claim !== undefined
          ? claim.claim
          : wire !== undefined
            ? `The arrow from ${wire.source} to ${wire.target}.`
            : "Choose a claim or an arrow on the map first — click it, or reach it with the keyboard."}
      </p>

      <div className="intervene__buttons">
        <button
          className="intervene__button"
          type="button"
          onClick={() => {
            if (needsAClaim() || claim === undefined) {
              return;
            }
            onEdit({ op: "do", target: claim.id, value: true, at: world.today });
            say("Take this as given, and do not tell me what caused it.");
          }}
        >
          {BUTTONS.supposeTrue}
        </button>
        <button
          className="intervene__button"
          type="button"
          onClick={() => {
            if (needsAClaim() || claim === undefined) {
              return;
            }
            onEdit({ op: "do", target: claim.id, value: false, at: world.today });
            say("Take this as given, and do not tell me what caused it.");
          }}
        >
          {BUTTONS.supposeFalse}
        </button>
        <button
          className="intervene__button"
          type="button"
          onClick={() => {
            if (needsAClaim() || claim === undefined) {
              return;
            }
            onEdit({ op: "observe", target: claim.id, value: true, at: world.today });
            say("This is news — what came before it is read again, not only what comes after.");
          }}
        >
          {BUTTONS.happened}
        </button>
        {/* **Add a claim** is the one edit this build cannot hand to the
            engine, and it says so rather than half-doing it. A claim is not its
            wording: it is the wording plus how it will be judged, by whom, by
            when, and what it started from. Drafting those needs the part of
            this product that writes a claim, and that is the next pull request.
            A branch holding a half-written claim could not be folded onto the
            map at all, so nothing is recorded. */}
        <button
          className="intervene__button"
          type="button"
          data-live="no"
          onClick={() =>
            say(
              "Adding a claim of your own needs the part of this product that drafts one — the " +
                "wording, the test that settles it, who judges it and by when. That is not " +
                "connected yet, so no edit was recorded and nothing on the map has changed.",
            )
          }
        >
          {BUTTONS.addClaim}
          <span className="intervene__hint">needs the part that drafts a claim</span>
        </button>
        <button
          className="intervene__button"
          type="button"
          onClick={() => {
            if (wire === undefined) {
              say(
                "Choose an arrow on the map first. This changes one number on one arrow, and " +
                  "nothing else about it.",
              );
              return;
            }
            setPush(`${wire.strength}`);
            setPushing((was) => !was);
          }}
        >
          {BUTTONS.changePush}
        </button>
        <button
          className="intervene__button"
          type="button"
          data-live="no"
          onClick={() =>
            say(
              "Splitting a claim into finer claims that add back up to it is not built yet. " +
                "Nothing here pretends otherwise, and no edit was recorded.",
            )
          }
        >
          {BUTTONS.splitClaim}
          <span className="intervene__hint">not yet built</span>
        </button>
        <button
          className="intervene__button"
          type="button"
          onClick={() => {
            if (needsAClaim()) {
              return;
            }
            setOwnNumber((was) => !was);
          }}
        >
          {BUTTONS.ownNumber}
          <span className="intervene__hint">beside the model's, never averaged with it</span>
        </button>
      </div>

      {pushing && wire !== undefined ? (
        <form
          className="intervene__form"
          onSubmit={(event) => {
            event.preventDefault();
            const moved = Number(push);
            if (!Number.isFinite(moved)) {
              return;
            }
            onEdit({
              op: "retune",
              link: wire.id,
              strength: moved,
              wasStrength: wire.strength,
            });
            setPushing(false);
            say(
              `You moved this arrow from ${pushAsNumber(wire.strength)} to ` +
                `${pushAsNumber(moved)} — ${pushInWords(moved)}. Nothing else about the arrow ` +
                `changed.`,
            );
          }}
        >
          <label className="intervene__label" htmlFor="new-push">
            {`How hard does this arrow push? It is ${pushAsNumber(wire.strength)} — ` +
              `${pushInWords(wire.strength)}. A negative number pushes the other way.`}
          </label>
          <input
            className="intervene__field"
            id="new-push"
            inputMode="decimal"
            value={push}
            onChange={(event) => setPush(event.target.value)}
          />
          {/* Not the button's own words again: two things called *Change this
              push* on one panel is two things a reader has to tell apart. */}
          <button className="intervene__go" type="submit">
            Change it to that
          </button>
        </form>
      ) : null}

      {ownNumber && claim !== undefined ? (
        <form
          className="intervene__form"
          onSubmit={(event) => {
            event.preventDefault();
            const p = Number(reading.p);
            const lo = Number(reading.lo);
            const hi = Number(reading.hi);
            if (!(lo >= 0 && lo <= p && p <= hi && hi <= 1)) {
              say(
                "A likelihood runs from 0 to 1, and the range has to hold the number: the bottom " +
                  "at or below it, the top at or above it.",
              );
              return;
            }
            onEdit({ op: "believe", target: claim.id, belief: { p, lo, hi } });
            setOwnNumber(false);
            setReading({ p: "", lo: "", hi: "" });
            say(
              "Your number now sits beside the model's and the market's on that tile. It is never " +
                "averaged with either of them, and it is not pushed through the map.",
            );
          }}
        >
          <label className="intervene__label" htmlFor="own-p">
            Your likelihood, and the range that says how sure you are of it. Between 0 and 1.
          </label>
          <div className="intervene__three">
            <input
              className="intervene__field"
              id="own-p"
              inputMode="decimal"
              placeholder="likelihood"
              value={reading.p}
              onChange={(event) => setReading((was) => ({ ...was, p: event.target.value }))}
            />
            <input
              className="intervene__field"
              aria-label="the bottom of your range"
              inputMode="decimal"
              placeholder="bottom"
              value={reading.lo}
              onChange={(event) => setReading((was) => ({ ...was, lo: event.target.value }))}
            />
            <input
              className="intervene__field"
              aria-label="the top of your range"
              inputMode="decimal"
              placeholder="top"
              value={reading.hi}
              onChange={(event) => setReading((was) => ({ ...was, hi: event.target.value }))}
            />
          </div>
          <button className="intervene__go" type="submit">
            Put this number on the claim
          </button>
        </form>
      ) : null}

      <p className="intervene__said">
        {said ??
          "Every button here appends an edit to a branch and shows it. The branch then goes to " +
            "the engine, which works the map's numbers through again and says what moved — " +
            "nothing on this side of the screen works one out."}
      </p>
    </section>
  );
}
