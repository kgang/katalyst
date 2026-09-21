/**
 * The two ports the end-to-end run uses, and the check that they are free.
 *
 * **Several worktrees of this repository are often open on one machine**, and
 * every one of them wants to start a server and a browser app. They cannot all
 * have the same two numbers. Playwright's own answer — `reuseExistingServer` —
 * is worse than a collision: it quietly attaches to whatever happens to be
 * answering on that port, so a run in one worktree tests the branch checked out
 * in another and reports it as green. That has already happened here, in both
 * directions, and neither side could tell from the output.
 *
 * So: the ports come from the environment, they default to the numbers
 * continuous integration has always used, nothing is ever reused, and a port
 * that is taken stops the run **before anything is started**, with a sentence
 * that says which port and what to do about it.
 *
 * **The check is made when the configuration is read**, which is the only
 * moment early enough. Playwright starts its servers before it runs anything
 * else it offers, and its own message for a taken port ends by suggesting
 * `reuseExistingServer: true` — which is the fault, recommended as the cure.
 * Being first is the whole point, so the check is synchronous, which asking a
 * socket is not: it is made in a child process that does the asking and exits
 * with the answer.
 */

import { execFileSync } from "node:child_process";

/** Where the Python half answers during a run. */
export const BACKEND_PORT = Number(process.env.KATALYST_E2E_BACKEND_PORT ?? 8015);

/** Where the browser app is served during a run. */
export const FRONTEND_PORT = Number(process.env.KATALYST_E2E_FRONTEND_PORT ?? 5187);

/**
 * Can this machine still open that port?
 *
 * By asking for it and letting it go, which is the only answer that is about
 * the port rather than about what somebody believes is running. A machine that
 * will not run the check at all is given the benefit of the doubt: Playwright
 * still refuses to start on a taken port, and a check that cannot run must not
 * be a check that fails.
 *
 * @param port The port to try.
 */
function free(port: number): boolean {
  const asking =
    "const s=require('node:net').createServer();" +
    "s.once('error',()=>process.exit(1));" +
    `s.once('listening',()=>s.close(()=>process.exit(0)));s.listen(${port},'127.0.0.1');`;
  try {
    execFileSync(process.execPath, ["-e", asking], { stdio: "ignore" });
    return true;
  } catch (whatever) {
    return (whatever as { status?: number }).status === 1 ? false : true;
  }
}

/**
 * Stop, before anything is started, if either port is taken.
 *
 * The sentence names the port, names the thing that is probably holding it, and
 * gives the one line that fixes it — because the person reading it is usually
 * somebody who did not know another worktree was running at all.
 */
export function assertPortsAreFree(): void {
  // **Only in the process that starts the servers.** Playwright reads this
  // configuration again in every worker it forks, and by then the ports are in
  // use — by the very servers it started, which is the one case that is not a
  // collision. A worker names itself in the environment; the first process does
  // not.
  if (process.env.TEST_WORKER_INDEX !== undefined) {
    return;
  }
  for (const [port, half, variable] of [
    [BACKEND_PORT, "the server", "KATALYST_E2E_BACKEND_PORT"],
    [FRONTEND_PORT, "the browser app", "KATALYST_E2E_FRONTEND_PORT"],
  ] as const) {
    if (free(port)) {
      continue;
    }
    throw new Error(
      `\n\nPort ${port}, where ${half} would be started, is already in use — most likely ` +
        `another worktree of this repository running its own end-to-end tests.\n\n` +
        `Nothing is reused here on purpose: a run that attached to it would test whichever ` +
        `branch that is and call the result yours.\n\n` +
        `Stop the other run, or give this one a port of its own:\n\n` +
        `    ${variable}=${port + 40} npm run e2e\n`,
    );
  }
}
