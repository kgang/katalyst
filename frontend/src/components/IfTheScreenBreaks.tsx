/**
 * The one place this app catches a fault in its own drawing.
 *
 * Every screen in this product is drawn from data that came over a wire, and a
 * wire can hand back a shape nothing here expected — a body that answered 200
 * and was not the thing it said it was, a field that used to be there and is
 * not. React's answer to a component that throws while rendering is to unmount
 * the **whole tree**: a white page, with the browser console holding the only
 * evidence that anything was ever there. A reader who was three minutes into a
 * generation is left with nothing to read, nothing to press and nothing to say
 * to whoever they report it to.
 *
 * So one boundary, at the screen, and it keeps two things.
 *
 * **The header stays**, which is the way back to the launchpad. A dead end with
 * no way out of it is the one failure that makes a person reload the page and
 * lose the run.
 *
 * **One plain sentence**, the thrower's own where it wrote one. Never a stack
 * trace on the page — that is the console's job, and this hands it there
 * untouched — and never a reassuring sentence about trying again, because
 * nothing here knows whether trying again would work.
 *
 * It is a class because React has no other way to catch a render: the two
 * methods below are the whole interface, and there is no hook for them.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";

/** What the boundary needs. */
export interface IfTheScreenBreaksProps {
  /**
   * The part of the screen that survives a fault — the bar with the way back on
   * it. It is drawn by the caller and outside the part being guarded, so a fault
   * in the map cannot take the way out with it.
   */
  readonly header: ReactNode;
  /** What is being guarded. */
  readonly children: ReactNode;
}

/** What it knows once something has broken. */
interface Broke {
  /** The one sentence, or null while nothing has broken. */
  readonly sentence: string | null;
}

/** Keep the way out, and say what happened, in one sentence. */
export class IfTheScreenBreaks extends Component<IfTheScreenBreaksProps, Broke> {
  override state: Broke = { sentence: null };

  /**
   * Turn whatever was thrown into the one sentence this draws.
   *
   * @param thrown Whatever a component threw while rendering.
   */
  static getDerivedStateFromError(thrown: unknown): Broke {
    return {
      sentence:
        thrown instanceof Error && thrown.message !== ""
          ? thrown.message
          : "Nothing was written down about what went wrong.",
    };
  }

  /**
   * Put the whole of it where a developer will find it.
   *
   * The page gets a sentence; the console gets the stack and the component that
   * threw. Printing a stack on the page teaches a reader that this product talks
   * to them in a language they are not expected to read.
   *
   * @param thrown Whatever was thrown.
   * @param where Which component was being drawn.
   */
  override componentDidCatch(thrown: unknown, where: ErrorInfo): void {
    console.error("This screen could not be drawn.", thrown, where.componentStack);
  }

  override render(): ReactNode {
    const { sentence } = this.state;
    if (sentence === null) {
      return (
        <>
          {this.props.header}
          {this.props.children}
        </>
      );
    }
    return (
      <>
        {this.props.header}
        <div className="map-waiting">
          <p className="map-waiting__line">
            This screen could not be drawn. Nothing you did caused it and nothing has been lost on
            the server — the way back to the launchpad is above, and the run's own working is still
            readable there.
          </p>
          {/* The thrower's own words, printed as they came. */}
          <p className="map-waiting__line">{sentence}</p>
        </div>
      </>
    );
  }
}
