/**
 * Fail the build if the canvas library's own look is ever imported.
 *
 * The drawing library behind the map ships two stylesheets. The bare one is the
 * handful of rules without which panning and zooming do not work, and this app
 * imports it. The full one carries the library's own look — its blue handles,
 * its white boxes, its rounded buttons — and importing it anywhere would make
 * this product look like a demo of somebody else's library, which is a stopping
 * condition for this project rather than a matter of taste.
 *
 * Why a script and not a rule in the linter's configuration: the linter reads
 * code, and a stylesheet can also be pulled in from another stylesheet with an
 * `@import` line, which is not code. This reads every file either way.
 *
 * It runs as part of `npm run lint`, so it fails the same job that formatting
 * and type errors fail.
 *
 *   node scripts/no-library-stylesheet.mjs
 *
 * Nothing is printed when it is happy. When it is not, it names every file and
 * line and exits with a failure.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

/** The frontend directory, whatever the working directory happens to be. */
const ROOT = fileURLToPath(new URL("..", import.meta.url));

/**
 * What may not appear.
 *
 * Both spellings, with and without the extension, because a bundler resolves
 * either one to the same file.
 */
const FORBIDDEN = /@xyflow\/react\/dist\/style(\.css)?/;

/**
 * Directories this never looks in.
 *
 * `scripts` is skipped because this file lives there and has to be able to name
 * the thing it forbids; the others hold code nobody here wrote.
 */
const SKIP = new Set(["node_modules", "dist", "scripts", ".git"]);

/** Every file worth reading, under one directory. */
function filesUnder(directory) {
  const found = [];
  for (const entry of readdirSync(directory)) {
    if (SKIP.has(entry)) {
      continue;
    }
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) {
      found.push(...filesUnder(path));
      continue;
    }
    if (/\.(ts|tsx|js|jsx|mjs|cjs|css|html|json)$/.test(entry)) {
      found.push(path);
    }
  }
  return found;
}

const offences = [];
for (const path of filesUnder(ROOT)) {
  const lines = readFileSync(path, "utf8").split("\n");
  lines.forEach((line, index) => {
    if (FORBIDDEN.test(line)) {
      offences.push({ path: relative(ROOT, path).split(sep).join("/"), line: index + 1 });
    }
  });
}

if (offences.length > 0) {
  console.error(
    "The canvas library's own stylesheet is imported. Only its bare stylesheet,\n" +
      '"@xyflow/react/dist/base.css", may be imported: the other one carries the\n' +
      "library's own look, and every pixel of this product is meant to be ours.\n",
  );
  for (const offence of offences) {
    console.error(`  ${offence.path}:${offence.line}`);
  }
  process.exit(1);
}
