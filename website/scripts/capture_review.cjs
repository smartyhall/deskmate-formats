"use strict";
/**
 * Capture desktop and phone renders of the reviewed page map for review.
 *
 * Review images are never committed: this writes PNGs and a capture report to a
 * scratch directory that is gitignored locally and uploaded as a GitHub Actions
 * artifact in CI. The device metrics are set explicitly through the DevTools
 * protocol because a browser window has a minimum width on some platforms, and
 * a window-size flag therefore cannot produce a true phone viewport.
 */
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { pages, SECTION_IDS } = require("../lib/reference.cjs");

const VIEWPORTS = Object.freeze([
  { name: "desktop", width: 1280, height: 900 },
  { name: "phone", width: 390, height: 844 },
]);
const BROWSERS = Object.freeze([
  "google-chrome", "chromium", "chromium-browser", "chrome",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
]);
const DEBUG_PORT = 9333;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** One page per reader section plus the home page, in reading order. */
function captureTargets() {
  const targets = [{ name: "home", route: "/" }];
  for (const id of SECTION_IDS) {
    const hub = pages.find((page) => page.is_hub && page.section === id);
    if (!hub) throw new Error("Missing hub for section " + id);
    targets.push({ name: hub.slug, route: "/" + hub.slug + "/" });
  }
  return targets;
}

function parseArgs(argv) {
  const options = {
    base: "http://127.0.0.1:8088",
    out: "local-results/review-captures",
    browser: null,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === "--base") options.base = argv[++index];
    else if (flag === "--out") options.out = argv[++index];
    else if (flag === "--browser") options.browser = argv[++index];
    else throw new Error("Unknown argument: " + flag);
  }
  if (!/^https?:\/\/[^/]+/.test(options.base)) throw new Error("--base must be an http(s) URL");
  return options;
}

function findBrowser(explicit) {
  if (explicit) return explicit;
  for (const candidate of BROWSERS) {
    if (candidate.includes("/")) {
      if (fs.existsSync(candidate)) return candidate;
      continue;
    }
    const probe = spawnSync(candidate, ["--version"], { stdio: "ignore" });
    if (!probe.error && probe.status === 0) return candidate;
  }
  throw new Error("No Chrome or Chromium found; pass --browser <path>");
}

async function debuggingTarget() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/list`);
      const page = (await response.json()).find((target) => target.type === "page");
      if (page) return page;
    } catch {
      // The browser is still starting.
    }
    await sleep(200);
  }
  throw new Error("Browser did not expose a debugging target");
}

function session(socket) {
  let sequence = 0;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      pending.get(message.id)(message);
      pending.delete(message.id);
    }
  });
  return (method, params = {}) => new Promise((resolve, reject) => {
    const id = (sequence += 1);
    pending.set(id, (message) => (message.error
      ? reject(new Error(method + ": " + JSON.stringify(message.error)))
      : resolve(message.result)));
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function captureAll(options) {
  const output = path.resolve(options.out);
  fs.mkdirSync(output, { recursive: true });
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "review-capture-"));
  const browser = spawn(findBrowser(options.browser), [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
    "--remote-debugging-port=" + DEBUG_PORT, "--user-data-dir=" + profile, "about:blank",
  ], { stdio: "ignore" });

  try {
    const target = await debuggingTarget();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    const send = session(socket);
    await send("Page.enable");
    const report = [];
    for (const page of captureTargets()) {
      for (const viewport of VIEWPORTS) {
        await send("Emulation.setDeviceMetricsOverride", {
          width: viewport.width, height: viewport.height,
          deviceScaleFactor: 1, mobile: viewport.name === "phone",
        });
        await send("Page.navigate", { url: options.base + page.route });
        for (let attempt = 0; attempt < 40; attempt += 1) {
          const state = await send("Runtime.evaluate", {
            expression: "document.readyState", returnByValue: true,
          });
          if (state.result.value === "complete") break;
          await sleep(100);
        }
        const measured = await send("Runtime.evaluate", {
          expression: "JSON.stringify({w: innerWidth, s: document.documentElement.scrollWidth})",
          returnByValue: true,
        });
        const { w, s } = JSON.parse(measured.result.value);
        const file = `${page.name}-${viewport.name}-${viewport.width}.png`;
        const shot = await send("Page.captureScreenshot", {
          format: "png", captureBeyondViewport: true,
        });
        fs.writeFileSync(path.join(output, file), Buffer.from(shot.data, "base64"));
        report.push({
          page: page.name, route: page.route, viewport: viewport.name,
          width: w, scroll_width: s, overflow: s > w, file,
        });
        console.log(`${file}: viewport ${w}px, scroll ${s}px${s > w ? " (OVERFLOW)" : ""}`);
      }
    }
    fs.writeFileSync(path.join(output, "capture-report.json"),
      JSON.stringify({ captures: report }, null, 2) + "\n", "utf8");
    socket.close();
    return report;
  } finally {
    browser.kill();
  }
}

async function main(argv) {
  const report = await captureAll(parseArgs(argv));
  const overflowing = report.filter((entry) => entry.overflow);
  if (overflowing.length) {
    for (const entry of overflowing)
      console.error(`${entry.file}: horizontal overflow (${entry.scroll_width} > ${entry.width})`);
    return 1;
  }
  console.log(`Captured ${report.length} renders; no horizontal overflow.`);
  return 0;
}

module.exports = { captureTargets, captureAll, VIEWPORTS };

if (require.main === module) {
  main(process.argv.slice(2)).then((status) => process.exit(status),
    (error) => { console.error(error.message); process.exit(1); });
}
