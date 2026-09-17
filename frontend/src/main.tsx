/**
 * Where the browser app starts.
 *
 * Three things happen here and nothing else: the two typefaces are loaded from
 * packages installed alongside the code (so the first frame needs no request to
 * any outside service and the app works with no network at all), the design
 * tokens and the screen's styles are loaded, and the screen is attached to the
 * page.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./styles/tokens.css";
import "./styles/app.css";

import { App } from "./App";

const root = document.getElementById("root");
if (root === null) {
  throw new Error('The page is missing the element with id "root" that the app attaches to.');
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
