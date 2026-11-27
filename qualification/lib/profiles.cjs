"use strict";
/**
 * Qualification profiles.
 *
 * A profile is a named set of browser-context options plus the checks that
 * matter for it. Profiles describe simulated conditions: a 390x844 context is
 * an emulated phone viewport, not a physical device, and a forced-colors
 * context is a simulated preference, not a real high-contrast user's setup.
 */
const PROFILES = Object.freeze({
  desktop: {
    label: "Desktop",
    description: "Wide desktop layout at 1280x900 with a 1x device pixel ratio.",
    context: { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
    checks: ["layout", "images"],
  },
  tablet: {
    label: "Tablet portrait",
    description: "Tablet portrait at 834x1112 with a 2x device pixel ratio and touch.",
    context: { viewport: { width: 834, height: 1112 }, deviceScaleFactor: 2, isMobile: false, hasTouch: true },
    checks: ["layout", "images"],
  },
  mobile: {
    label: "Phone portrait",
    description: "Phone portrait at 390x844 with a 3x device pixel ratio and touch.",
    context: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true },
    checks: ["layout", "images"],
  },
  landscape: {
    label: "Phone landscape",
    description: "Phone landscape at 844x390 with a 3x device pixel ratio and touch.",
    context: { viewport: { width: 844, height: 390 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true },
    checks: ["layout"],
  },
  reflow: {
    label: "Reflow at 320 CSS pixels",
    description: "320x640 equivalent to a 400 percent zoom reflow check; content must not require sideways scrolling.",
    context: { viewport: { width: 320, height: 640 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
    checks: ["layout", "tables"],
  },
  "no-js": {
    label: "JavaScript disabled",
    description: "Desktop viewport with scripting disabled; navigation and content must remain usable.",
    context: {
      viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1, isMobile: false, javaScriptEnabled: false,
    },
    checks: ["layout", "navigation"],
  },
  "forced-colors": {
    label: "Forced colors",
    description: "Simulated forced-colors mode, approximating a Windows high-contrast preference.",
    context: { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1, forcedColors: "active" },
    checks: ["layout", "focus"],
  },
  "reduced-motion": {
    label: "Reduced motion",
    description: "Simulated prefers-reduced-motion: reduce.",
    context: { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1, reducedMotion: "reduce" },
    checks: ["layout"],
  },
  print: {
    label: "Print",
    description: "Print media emulation at A4 width; navigation chrome should not dominate the page.",
    context: { viewport: { width: 794, height: 1123 }, deviceScaleFactor: 1 },
    media: { media: "print" },
    checks: ["layout", "print"],
  },
  keyboard: {
    label: "Keyboard navigation",
    description: "Tab through the page and record focus order, focus visibility, and the skip link.",
    context: { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 },
    checks: ["focus-order", "focus"],
  },
  "deep-link": {
    label: "Deep links",
    description: "Every anchor on the page must resolve to a target inside the document.",
    context: { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 },
    checks: ["anchors"],
  },
  search: {
    label: "Search",
    description: "Submit a query on the search page and confirm results are rendered.",
    context: { viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 },
    checks: ["search"],
  },
});

const DEFAULT_PROFILES = Object.freeze(["desktop", "mobile"]);
/** Profiles that need a page to answer before they mean anything. */
const ALL_PROFILE_NAMES = Object.freeze(Object.keys(PROFILES));

function parseProfileList(value) {
  const names = (Array.isArray(value) ? value : String(value).split(","))
    .map((name) => name.trim().toLowerCase())
    .filter(Boolean);
  if (!names.length) throw new Error("at least one profile is required");
  const unknown = names.filter((name) => !PROFILES[name]);
  if (unknown.length) {
    throw new Error(`unknown profile(s): ${unknown.join(", ")}; known: ${ALL_PROFILE_NAMES.join(", ")}`);
  }
  return [...new Set(names)];
}

/** Context options for Playwright; the profile's own object is never mutated. */
function contextOptions(profile) {
  const options = { ...profile.context };
  if (profile.context.viewport) options.viewport = { ...profile.context.viewport };
  return options;
}

module.exports = {
  PROFILES,
  DEFAULT_PROFILES,
  ALL_PROFILE_NAMES,
  parseProfileList,
  contextOptions,
};
