/**
 * Runs once before every test file.
 *
 * Two things happen here. First, the readable checks that Testing Library
 * provides — `toBeInTheDocument` and its relatives — are added to the test
 * runner's expectation syntax, so a failing test says what was wrong with the
 * page rather than what was wrong with an object. Second, the page is emptied
 * after each test, so one test's screen can never be found by the next one.
 */

import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);
