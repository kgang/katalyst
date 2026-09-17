/**
 * The little of Node's file reading that the tests need, described here.
 *
 * Two of the checks in this tree read the source tree itself: one walks every
 * stylesheet to prove that the five brightness steps are painted in two places
 * and nowhere else, and one walks every file to prove that only one component
 * ever names a direction colour. Both need to read files off the disk.
 *
 * The app's own type settings deliberately describe a browser and nothing else,
 * so that no component can quietly import a file reader and start depending on a
 * disk that will not be there. Rather than widen that setting for the whole app,
 * the three functions the tests actually call are described here — in the test
 * folder, where only tests can reach them.
 *
 * The build tool's own way of reading a file as text is not an option: this
 * project runs its tests with stylesheets switched off, so a stylesheet imported
 * through the build tool comes back empty.
 */

declare module "node:fs" {
  /** Read a whole file as text. Paths are relative to the project root. */
  export function readFileSync(path: string, encoding: "utf8"): string;
  /** The names of everything directly inside a folder. */
  export function readdirSync(path: string): string[];
  /** What something at a path is. */
  export function statSync(path: string): { isDirectory(): boolean };
}

declare module "node:path" {
  /** Join the parts of a path with the separator this machine uses. */
  export function join(...parts: string[]): string;
}
