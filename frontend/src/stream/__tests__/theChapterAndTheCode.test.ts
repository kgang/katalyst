/**
 * The chapter's hand-typed shapes and the code's are the same shapes.
 *
 * `streaming-growth.md` carries the eight events, the request and the reducer's
 * state as TypeScript, because a chapter that shows the shape is a chapter
 * somebody can read instead of the code. That is only worth anything while the
 * two agree — and they had come apart in five places at once: the receipt
 * listed nine fields where the chapter's own B6 and INV-workbench.72 said ten,
 * `Phase` listed five values where the code had six, `GenerationStarted` was
 * missing the field that keeps a nineteen-digit seed from being printed rounded,
 * `Growth` was missing three, and the request still offered two the browser had
 * stopped sending.
 *
 * Each of those is a reader told something false about the product by the
 * document whose whole job is to say what is true of it.
 *
 * **It compares field names and nothing else.** The prose around them is the
 * point of the chapter and no test should have an opinion about it; what a test
 * can hold is that every field in the code is in the chapter and every field in
 * the chapter is in the code. A doc comment can be improved freely, and a field
 * cannot be added or dropped quietly on either side.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/** The chapter, read as text — the same document a person reads. */
const CHAPTER = readFileSync("../spec/workbench/streaming-growth.md", "utf8");

/** One of this half's own files, read as text for the same reason. */
function source(path: string): string {
  return readFileSync(path, "utf8");
}

/**
 * Every `readonly <name>` in one declaration, in the order it is written.
 *
 * Found by walking from the declaration's opening brace to its matching close,
 * so a doc comment holding the word `readonly` in prose cannot be mistaken for
 * a field. Nested shapes are not walked: none of the five has one.
 *
 * @param text The file or chapter to look in.
 * @param declaration The line the shape starts on, as it is written.
 */
function fieldsOf(text: string, declaration: string): string[] {
  const at = text.indexOf(declaration);
  expect(at, `${declaration} is not in this text at all`).toBeGreaterThan(-1);
  const opens = text.indexOf("{", at);
  let depth = 0;
  let end = opens;
  for (let i = opens; i < text.length; i += 1) {
    if (text[i] === "{") {
      depth += 1;
    } else if (text[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }
  const body = text.slice(opens, end);
  return [...body.matchAll(/^\s*readonly\s+([A-Za-z_]\w*)\??:/gm)].map((one) => one[1] as string);
}

/** The five shapes the chapter writes out, and where each lives in the code. */
const BOTH: { shape: string; file: string }[] = [
  { shape: "export interface GenerationStarted {", file: "src/stream/events.ts" },
  { shape: "export interface Receipt {", file: "src/stream/events.ts" },
  { shape: "export interface GenerateRequest {", file: "src/stream/events.ts" },
  { shape: "export interface Growth {", file: "src/stream/growth.ts" },
];

/**
 * One allowance, for one field, dated — and it is spent, never banked.
 *
 * *2026-09-22, branch `feat/04d-the-strip-says-it`.* The ninth event is being
 * built in two halves at once against one written sheet, and the chapter is the
 * other lane's to write: the server half carries decision record 0027 and the
 * two or three sentences `spec/workbench/streaming-growth.md` needs about what
 * the strip shows. So for as long as the two branches are apart, the code holds
 * one field the chapter has not described yet.
 *
 * **It is not a skipped check.** The test below holds the allowance to exactly
 * this one field, and it also holds that the chapter does **not** describe it —
 * so the moment the chapter gains `activity`, this test fails, says so in as
 * many words, and whoever is at the join deletes this list and the two lines
 * that read it. A field slipped into the code that is not on this list still
 * fails exactly as it did before.
 */
const NOT_IN_THE_CHAPTER_YET: Record<string, readonly string[]> = {
  "export interface Growth {": ["activity"],
};

describe("the chapter says what the code does", () => {
  for (const { shape, file } of BOTH) {
    it(`test_${shape.split(" ")[2]}_holds_the_same_fields_in_the_chapter_and_in_the_code`, () => {
      const written = fieldsOf(CHAPTER, shape);
      const built = fieldsOf(source(file), shape);
      expect(written.length).toBeGreaterThan(0);
      const allowed = NOT_IN_THE_CHAPTER_YET[shape] ?? [];
      // The allowance is spent the day it is no longer needed. A chapter that
      // has caught up is a chapter this list must stop excusing.
      expect(
        written.filter((one) => allowed.includes(one)),
        `The chapter now describes ${allowed.join(", ")} in ${shape.split(" ")[2]}. ` +
          "Delete that entry from NOT_IN_THE_CHAPTER_YET — the two halves have met.",
      ).toEqual([]);
      // Sorted, because the order a shape is written in is a matter of reading
      // rather than of truth, and a test that held the order would fail on an
      // improvement to the chapter rather than on a drift from the code.
      expect([...written].sort()).toEqual(
        [...built].filter((one) => !allowed.includes(one)).sort(),
      );
    });
  }

  it("test_the_phases_are_the_same_six_in_both", () => {
    const written = /export type Phase =([^;]+);/.exec(CHAPTER)?.[1] ?? "";
    const built = /export type Phase =([^;]+);/.exec(source("src/stream/growth.ts"))?.[1] ?? "";
    const names = (one: string) => [...one.matchAll(/"(\w+)"/g)].map((m) => m[1] as string).sort();
    expect(names(written).length).toBeGreaterThan(0);
    expect(names(written)).toEqual(names(built));
  });
});
