"use strict";
/**
 * Capture desktop and phone renders of the reviewed page map for review.
 *
 * Review images are never committed: this writes PNGs and a capture manifest to
 * a scratch directory that is gitignored locally and uploaded as a GitHub
 * Actions artifact in CI. The device metrics are set explicitly through the
 * DevTools protocol because a browser window has a minimum width on some
 * platforms, and a window-size flag therefore cannot produce a true phone
 * viewport.
 *
 * This is deliberately an independent Chromium check that shares no code with
 * the Playwright qualification harness, so a defect in one is unlikely to be
 * reproduced silently by the other.
 *
 * Ownership rules:
 *   - The browser is spawned by this process with a private, temporary
 *     user-data-dir and `--remote-debugging-port=0`, so the operating system
 *     assigns the port and the browser records it in DevToolsActivePort inside
 *     that private profile. A fixed port could silently attach to an unrelated
 *     browser that already owns it.
 *   - The recorded port is only accepted when the endpoint reports a debugging
 *     URL on that same port and the child process is still alive.
 *   - Every accepted render must show the requested route (canonical path and
 *     title), answer 200 for the document, report the requested viewport, and
 *     finish loading before the screenshot is taken.
 */
const { spawn, spawnSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");
const { pages, SECTION_IDS } = require("../lib/reference.cjs");

const VIEWPORTS = Object.freeze([
  { name: "desktop", width: 1280, height: 900, deviceScaleFactor: 1, mobile: false },
  { name: "phone", width: 390, height: 844, deviceScaleFactor: 3, mobile: true },
]);
const BROWSERS = Object.freeze([
  "google-chrome", "chromium", "chromium-browser", "chrome",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]);
const PUBLIC_ORIGIN = "https://deskmate.retroconnect.org";
const DEFAULT_TIMEOUT = 30000;
const IDLE_QUIET_MS = 300;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** One page per reader section plus the home page, in reading order. */
function captureTargets() {
  const targets = [{ name: "home", route: "/", title: "DeskMate Reference" }];
  for (const id of SECTION_IDS) {
    const hub = pages.find((page) => page.is_hub && page.section === id);
    if (!hub) throw new Error("Missing hub for section " + id);
    targets.push({ name: hub.slug, route: "/" + hub.slug + "/", title: hub.title });
  }
  return targets;
}

/** Compare routes ignoring a trailing slash and any query or fragment. */
function normalizeRoute(value) {
  if (typeof value !== "string") return null;
  let pathname = value;
  try {
    pathname = new URL(value, PUBLIC_ORIGIN).pathname;
  } catch {
    return null;
  }
  if (!pathname.startsWith("/")) return null;
  return pathname.endsWith("/") ? pathname : pathname + "/";
}

/** Read width and height from a PNG IHDR header without decoding the image. */
function parsePngSize(buffer) {
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (!Buffer.isBuffer(buffer) || buffer.length < 24 || !buffer.subarray(0, 8).equals(signature)) {
    throw new Error("not a PNG image");
  }
  if (buffer.subarray(12, 16).toString("ascii") !== "IHDR") throw new Error("PNG lacks IHDR");
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function parseArgs(argv) {
  const options = {
    base: "http://127.0.0.1:8088",
    out: "local-results/review-captures",
    browser: null,
    timeout: DEFAULT_TIMEOUT,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === "--base") options.base = argv[++index];
    else if (flag === "--out") options.out = argv[++index];
    else if (flag === "--browser") options.browser = argv[++index];
    else if (flag === "--timeout") options.timeout = Number(argv[++index]);
    else throw new Error("Unknown argument: " + flag);
  }
  if (!/^https?:\/\/[^/]+/.test(options.base)) throw new Error("--base must be an http(s) URL");
  if (!Number.isFinite(options.timeout) || options.timeout <= 0) {
    throw new Error("--timeout must be a positive number of milliseconds");
  }
  return options;
}

function findBrowser(explicit) {
  if (explicit) {
    if (!fs.existsSync(explicit) && !spawnSync(explicit, ["--version"], { stdio: "ignore" }).status) {
      throw new Error("--browser does not name a usable browser: " + explicit);
    }
    return explicit;
  }
  for (const candidate of BROWSERS) {
    if (candidate.includes("/") || candidate.includes("\\")) {
      if (fs.existsSync(candidate)) return candidate;
      continue;
    }
    const probe = spawnSync(candidate, ["--version"], { stdio: "ignore" });
    if (!probe.error && probe.status === 0) return candidate;
  }
  throw new Error("No Chrome or Chromium found; pass --browser <path>");
}

function withTimeout(promise, milliseconds, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} timed out after ${milliseconds} ms`)), milliseconds);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

/** Wait for the browser to record the port it was actually given. */
async function readDevToolsPort(profile, child, timeoutMs) {
  const file = path.join(profile, "DevToolsActivePort");
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`browser exited before exposing a debugging port (code ${child.exitCode})`);
    }
    if (fs.existsSync(file)) {
      const [portLine, browserPath] = fs.readFileSync(file, "utf8").split("\n");
      const port = Number(portLine);
      if (Number.isInteger(port) && port > 0) return { port, browserPath };
    }
    await sleep(100);
  }
  throw new Error("browser did not record a DevTools port in its private profile");
}

/**
 * Confirm the debugging endpoint belongs to the browser we started.
 * The port came from our private profile, so an endpoint answering on it that
 * reports a debugging URL for the same port cannot be an unrelated session.
 */
async function verifyOwnership(port, timeoutMs) {
  const response = await fetch(`http://127.0.0.1:${port}/json/version`, {
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) throw new Error(`debugging endpoint answered ${response.status}`);
  const version = await response.json();
  const advertised = new URL(version.webSocketDebuggerUrl);
  if (Number(advertised.port) !== port) {
    throw new Error(`debugging endpoint advertises port ${advertised.port}, expected ${port}`);
  }
  if (!version.Browser) throw new Error("debugging endpoint did not report a browser version");
  return version;
}

async function waitForPageTarget(port, child, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error("browser exited before exposing a page target");
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`, {
        signal: AbortSignal.timeout(2000),
      });
      const targets = (await response.json()).filter((target) => target.type === "page");
      if (targets.length === 1) return targets[0];
      if (targets.length > 1) throw new Error(`expected one page target, found ${targets.length}`);
    } catch (error) {
      if (error.message.startsWith("expected one page target")) throw error;
    }
    await sleep(100);
  }
  throw new Error("browser did not expose a page target");
}

class Session {
  constructor(socket, timeoutMs) {
    this.socket = socket;
    this.timeout = timeoutMs;
    this.sequence = 0;
    this.pending = new Map();
    this.listeners = new Map();
    this.closed = false;
    socket.addEventListener("message", (event) => this.receive(event.data));
    socket.addEventListener("close", () => {
      this.closed = true;
      for (const { reject } of this.pending.values()) reject(new Error("DevTools session closed"));
      this.pending.clear();
    });
  }

  receive(raw) {
    const message = JSON.parse(raw);
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject, timer } = this.pending.get(message.id);
      this.pending.delete(message.id);
      clearTimeout(timer);
      if (message.error) reject(new Error(`${message.method || "command"}: ${JSON.stringify(message.error)}`));
      else resolve(message.result);
      return;
    }
    const handlers = this.listeners.get(message.method) || [];
    for (const handler of handlers) handler(message.params);
  }

  on(method, handler) {
    const handlers = this.listeners.get(method) || [];
    handlers.push(handler);
    this.listeners.set(method, handlers);
  }

  send(method, params = {}) {
    if (this.closed) return Promise.reject(new Error(`cannot send ${method}: session closed`));
    const id = (this.sequence += 1);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`${method} timed out after ${this.timeout} ms`));
      }, this.timeout);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    try {
      this.socket.close();
    } catch {
      // Already closed.
    }
  }
}

function connect(url, timeoutMs) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    const timer = setTimeout(() => reject(new Error("DevTools connection timed out")), timeoutMs);
    socket.addEventListener("open", () => {
      clearTimeout(timer);
      resolve(new Session(socket, timeoutMs));
    }, { once: true });
    socket.addEventListener("error", () => {
      clearTimeout(timer);
      reject(new Error("DevTools connection failed"));
    }, { once: true });
  });
}

/**
 * Navigate, then wait for the load event and a quiet network before accepting
 * the render. Returns the observations the caller needs to judge identity and
 * completeness instead of trusting a fixed sleep.
 */
async function navigateAndSettle(session, url, timeoutMs) {
  const state = {
    mainFrameId: null,
    documentStatus: null,
    documentUrl: null,
    failures: [],
    inflight: new Set(),
    documents: [],
  };

  session.on("Network.requestWillBeSent", ({ requestId, type }) => {
    if (["Document", "Script", "Stylesheet", "Image", "Font"].includes(type)) {
      state.inflight.add(requestId);
    }
  });
  session.on("Network.loadingFinished", ({ requestId }) => {
    state.inflight.delete(requestId);
  });
  session.on("Network.loadingFailed", ({ requestId, errorText, canceled }) => {
    state.inflight.delete(requestId);
    if (!canceled) state.failures.push(errorText);
  });
  // The document response can arrive before Page.navigate resolves, so collect
  // every document response and match it to the navigation frame afterwards.
  session.on("Network.responseReceived", ({ response, type, frameId }) => {
    if (type === "Document") {
      state.documents.push({ frameId, status: response.status, url: response.url });
    }
  });

  const loaded = new Promise((resolve) => session.on("Page.loadEventFired", resolve));
  const navigation = await session.send("Page.navigate", { url });
  if (navigation.errorText) throw new Error(`navigation failed: ${navigation.errorText}`);
  state.mainFrameId = navigation.frameId || null;

  await withTimeout(loaded, timeoutMs, "page load");
  await waitForQuiet(state, timeoutMs);
  const document = state.documents.filter((entry) => entry.frameId === state.mainFrameId).pop()
    || state.documents.pop();
  state.documentStatus = document ? document.status : null;
  state.documentUrl = document ? document.url : null;
  return state;
}

/** Wait until no tracked resource request has been in flight for a short while. */
async function waitForQuiet(state, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let quietSince = null;
  while (Date.now() < deadline) {
    if (state.inflight.size === 0) {
      quietSince = quietSince ?? Date.now();
      if (Date.now() - quietSince >= IDLE_QUIET_MS) return;
    } else {
      quietSince = null;
    }
    await sleep(50);
  }
  throw new Error(`network did not settle within ${timeoutMs} ms`);
}

async function readIdentity(session, expected) {
  const probe = await session.send("Runtime.evaluate", {
    expression: `JSON.stringify({
      path: location.pathname,
      title: document.title,
      canonical: (document.querySelector('link[rel="canonical"]') || {}).href || null,
      readyState: document.readyState,
      width: window.innerWidth,
      height: window.innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight
    })`,
    returnByValue: true,
  });
  const identity = JSON.parse(probe.result.value);
  const problems = [];
  if (normalizeRoute(identity.path) !== expected.route) {
    problems.push(`rendered ${identity.path}, expected ${expected.route}`);
  }
  const canonical = normalizeRoute(identity.canonical);
  if (canonical !== expected.route) {
    problems.push(`canonical ${identity.canonical} does not name ${expected.route}`);
  }
  if (identity.readyState !== "complete") problems.push(`readyState ${identity.readyState}`);
  if (expected.title && !identity.title.includes(expected.title)) {
    problems.push(`title ${JSON.stringify(identity.title)} lacks ${JSON.stringify(expected.title)}`);
  }
  return { identity, problems };
}

async function captureAll(options) {
  const output = path.resolve(options.out);
  fs.mkdirSync(output, { recursive: true });
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "review-capture-"));
  const browserPath = findBrowser(options.browser);
  const child = spawn(browserPath, [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
    "--no-default-browser-check", "--disable-extensions", "--disable-background-networking",
    "--disable-sync", "--metrics-recording-only", "--mute-audio",
    "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank",
  ], { stdio: "ignore", detached: process.platform !== "win32" });

  let session = null;
  let browserSession = null;
  let aborted = false;
  const onSignal = (signal) => {
    aborted = true;
    console.error(`received ${signal}; stopping after the current step`);
  };
  process.once("SIGINT", onSignal);
  process.once("SIGTERM", onSignal);

  try {
    const { port } = await readDevToolsPort(profile, child, options.timeout);
    const version = await verifyOwnership(port, options.timeout);
    const target = await waitForPageTarget(port, child, options.timeout);
    browserSession = await connect(version.webSocketDebuggerUrl, options.timeout);
    session = await connect(target.webSocketDebuggerUrl, options.timeout);
    await session.send("Page.enable");
    await session.send("Network.enable");
    await session.send("Runtime.enable");

    const captures = [];
    const problems = [];
    for (const page of captureTargets()) {
      for (const viewport of VIEWPORTS) {
        if (aborted) throw new Error("cancelled");
        const started = Date.now();
        await session.send("Emulation.setDeviceMetricsOverride", {
          width: viewport.width,
          height: viewport.height,
          deviceScaleFactor: viewport.deviceScaleFactor,
          mobile: viewport.mobile,
        });
        const url = options.base + page.route;
        const network = await navigateAndSettle(session, url, options.timeout);
        const { identity, problems: identityProblems } = await readIdentity(session, page);

        const entryProblems = [...identityProblems];
        if (network.documentStatus !== 200) {
          entryProblems.push(`document answered ${network.documentStatus}`);
        }
        if (identity.width !== viewport.width || identity.height !== viewport.height) {
          entryProblems.push(
            `viewport ${identity.width}x${identity.height}, requested ${viewport.width}x${viewport.height}`,
          );
        }
        for (const failure of network.failures) entryProblems.push(`resource failed: ${failure}`);

        const metrics = await session.send("Page.getLayoutMetrics");
        const content = metrics.cssContentSize;
        const clip = {
          x: 0,
          y: 0,
          width: Math.ceil(content.width),
          height: Math.max(Math.ceil(content.height), viewport.height),
          scale: 1,
        };
        const shot = await session.send("Page.captureScreenshot", {
          format: "png",
          captureBeyondViewport: true,
          fromSurface: true,
          clip,
        });
        const bytes = Buffer.from(shot.data, "base64");
        // Screenshot pixels are device pixels: the clip is expressed in CSS
        // pixels, so the expected image is the clip scaled by the DPR.
        const size = parsePngSize(bytes);
        const expectedWidth = Math.round(clip.width * viewport.deviceScaleFactor);
        const expectedHeight = Math.round(clip.height * viewport.deviceScaleFactor);
        if (size.width !== expectedWidth || size.height !== expectedHeight) {
          entryProblems.push(
            `screenshot ${size.width}x${size.height}, expected ${expectedWidth}x${expectedHeight}`,
          );
        }

        const file = `${page.name}-${viewport.name}-${viewport.width}.png`;
        fs.writeFileSync(path.join(output, file), bytes);
        const overflow = identity.scrollWidth > identity.width;
        if (overflow) entryProblems.push(`horizontal overflow: ${identity.scrollWidth} > ${identity.width}`);

        captures.push({
          page: page.name,
          route: page.route,
          viewport: viewport.name,
          requested: { width: viewport.width, height: viewport.height, dpr: viewport.deviceScaleFactor },
          measured: { width: identity.width, height: identity.height },
          scroll_width: identity.scrollWidth,
          scroll_height: identity.scrollHeight,
          overflow,
          status: network.documentStatus,
          title: identity.title,
          canonical: identity.canonical,
          file,
          sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
          bytes: bytes.length,
          image: size,
          duration_ms: Date.now() - started,
          problems: entryProblems,
        });
        for (const problem of entryProblems) problems.push(`${file}: ${problem}`);
        console.log(
          `${file}: ${identity.width}x${identity.height}, status ${network.documentStatus}, ` +
          `${identity.scrollWidth}px wide${overflow ? " (OVERFLOW)" : ""}` +
          (entryProblems.length ? ` — ${entryProblems.join("; ")}` : ""),
        );
      }
    }

    const manifest = {
      generated_at: new Date().toISOString(),
      base: options.base,
      revision: spawnSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).stdout?.trim() || null,
      browser: { path: browserPath, product: version.Browser },
      platform: `${os.platform()} ${os.release()} ${os.arch()}`,
      node: process.version,
      viewports: VIEWPORTS,
      captures,
      problems,
    };
    fs.writeFileSync(path.join(output, "capture-manifest.json"),
      JSON.stringify(manifest, null, 2) + "\n", "utf8");
    return manifest;
  } finally {
    process.removeListener("SIGINT", onSignal);
    process.removeListener("SIGTERM", onSignal);
    try {
      if (browserSession) await withTimeout(browserSession.send("Browser.close"), 3000, "browser close");
    } catch {
      // Falling back to terminating the process tree below.
    }
    browserSession?.close();
    session?.close();
    await terminate(child);
    removeProfile(profile);
  }
}

async function terminate(child) {
  if (child.exitCode !== null) return;
  const exited = new Promise((resolve) => child.once("exit", resolve));
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  } else {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch {
      child.kill("SIGTERM");
    }
  }
  await Promise.race([exited, sleep(5000)]);
  if (child.exitCode === null) child.kill("SIGKILL");
}

/** Windows keeps profile files locked briefly after exit. */
function removeProfile(profile) {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    try {
      fs.rmSync(profile, { recursive: true, force: true });
      return;
    } catch {
      spawnSync(process.execPath, ["-e", `setTimeout(() => {}, ${100 * (attempt + 1)})`]);
    }
  }
  console.error(`could not remove temporary browser profile ${profile}`);
}

async function main(argv) {
  const manifest = await captureAll(parseArgs(argv));
  if (manifest.problems.length) {
    for (const problem of manifest.problems) console.error(problem);
    return 1;
  }
  console.log(`Captured ${manifest.captures.length} verified renders.`);
  return 0;
}

module.exports = {
  captureTargets,
  captureAll,
  normalizeRoute,
  parsePngSize,
  VIEWPORTS,
};

if (require.main === module) {
  main(process.argv.slice(2)).then(
    (status) => process.exit(status),
    (error) => {
      console.error(error.message);
      process.exit(1);
    },
  );
}
