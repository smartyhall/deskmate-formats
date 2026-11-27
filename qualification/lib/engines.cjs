"use strict";
/**
 * Browser engine catalog and availability discovery.
 *
 * Playwright's WebKit build is not Apple Safari and Playwright's branded
 * channels are not the same binaries a user's machine runs. Each engine
 * therefore records what it actually is, so a result can never be reported as
 * "Safari" when it was WebKit for Windows, or as a physical device when it was
 * an emulated viewport.
 */
const ENGINES = Object.freeze({
  chromium: {
    label: "Chromium",
    family: "chromium",
    kind: "bundled",
    launch: { name: "chromium" },
    notes: "Playwright's bundled Chromium; not branded Chrome.",
  },
  firefox: {
    label: "Firefox",
    family: "gecko",
    kind: "bundled",
    launch: { name: "firefox" },
    notes: "Playwright's patched Firefox build.",
  },
  webkit: {
    label: "WebKit",
    family: "webkit",
    kind: "bundled",
    launch: { name: "webkit" },
    notes: "Playwright's WebKit build; not Apple Safari.",
  },
  chrome: {
    label: "Google Chrome",
    family: "chromium",
    kind: "channel",
    launch: { channel: "chrome" },
    notes: "Branded Google Chrome installed on the runner or workstation.",
  },
  msedge: {
    label: "Microsoft Edge",
    family: "chromium",
    kind: "channel",
    launch: { channel: "msedge" },
    notes: "Branded Microsoft Edge installed on the runner or workstation.",
  },
});

const DEFAULT_ENGINES = Object.freeze(["chromium"]);

/** Engines that a Linux runner can run without a branded browser install. */
const LINUX_ENGINES = Object.freeze(["chromium", "firefox", "webkit"]);
/** Engines worth checking on Windows runners. */
const WINDOWS_ENGINES = Object.freeze(["chromium", "firefox", "msedge"]);
/** Engines worth checking on macOS runners. */
const MACOS_ENGINES = Object.freeze(["webkit", "chromium", "firefox"]);

function parseEngineList(value) {
  const names = (Array.isArray(value) ? value : String(value).split(","))
    .map((name) => name.trim().toLowerCase())
    .filter(Boolean);
  if (!names.length) throw new Error("at least one engine is required");
  const unknown = names.filter((name) => !ENGINES[name]);
  if (unknown.length) {
    throw new Error(`unknown engine(s): ${unknown.join(", ")}; known: ${Object.keys(ENGINES).join(", ")}`);
  }
  return [...new Set(names)];
}

/**
 * Report whether each engine can start here, with the reason when it cannot.
 * Availability is proven by launching, not by assuming an install.
 */
async function discoverEngines(playwright, names) {
  const discovered = [];
  for (const name of names) {
    const engine = ENGINES[name];
    const record = { name, label: engine.label, family: engine.family, kind: engine.kind, notes: engine.notes };
    let browser = null;
    try {
      browser = await playwright[engine.launch.name].launch(
        engine.launch.channel ? { channel: engine.launch.channel } : {},
      );
      record.version = browser.version();
      record.available = true;
    } catch (error) {
      record.available = false;
      record.reason = String(error.message || error).split("\n")[0];
    } finally {
      await browser?.close();
    }
    discovered.push(record);
  }
  return discovered;
}

module.exports = {
  ENGINES,
  DEFAULT_ENGINES,
  LINUX_ENGINES,
  WINDOWS_ENGINES,
  MACOS_ENGINES,
  parseEngineList,
  discoverEngines,
};
