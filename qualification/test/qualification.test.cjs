"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { parseEngineList, LINUX_ENGINES, WINDOWS_ENGINES, MACOS_ENGINES } = require("../lib/engines.cjs");
const { parseProfileList, contextOptions, PROFILES } = require("../lib/profiles.cjs");
const { normalizeRoute, pagesFromMap, slug } = require("../lib/qualify.cjs");
const { contactSheet, markdownSummary, escape } = require("../lib/report.cjs");
const { serve, resolveTarget } = require("../lib/serve.cjs");

test("engine lists reject unknown names and remove duplicates", () => {
  assert.deepEqual(parseEngineList("chromium, firefox,chromium"), ["chromium", "firefox"]);
  assert.throws(() => parseEngineList("netscape"), /unknown engine/);
  assert.deepEqual(LINUX_ENGINES, ["chromium", "firefox", "webkit"]);
  assert.ok(WINDOWS_ENGINES.includes("msedge"));
  assert.equal(MACOS_ENGINES[0], "webkit");
});

test("profile lists reject unknown names", () => {
  assert.deepEqual(parseProfileList("desktop,mobile"), ["desktop", "mobile"]);
  assert.throws(() => parseProfileList("television"), /unknown profile/);
  for (const profile of Object.values(PROFILES)) {
    assert.ok(profile.label && profile.description && Array.isArray(profile.checks));
  }
});

test("context options are copied so a profile is never mutated by a run", () => {
  const options = contextOptions(PROFILES.mobile);
  options.viewport.width = 1;
  assert.equal(PROFILES.mobile.context.viewport.width, 390);
});

test("route normalization accepts public route forms", () => {
  assert.equal(normalizeRoute("/research"), "/research/");
  assert.equal(normalizeRoute("https://example.test/a/b/?q=1"), "/a/b/");
  assert.equal(normalizeRoute(""), "/");
  assert.equal(normalizeRoute(undefined), null);
});

test("slug is filename safe", () => {
  assert.equal(slug("/"), "home");
  assert.equal(slug("/research/evidence/"), "research-evidence");
});

test("page map routes include home and search", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "qualification-map-"));
  const mapPath = path.join(directory, "page-map.json");
  fs.writeFileSync(mapPath, JSON.stringify({
    pages: [{ id: "research.hub", slug: "research", title: "Research" }],
  }));
  const pages = pagesFromMap(mapPath);
  assert.deepEqual(pages.map((page) => page.route), ["/", "/research/", "/search/"]);
  fs.rmSync(directory, { recursive: true, force: true });
});

test("contact sheet marks failures and escapes content", () => {
  const results = [{
    engine: "chromium", profile: "desktop", page: { route: "/<script>" },
    observed: { width: 1280, height: 900, devicePixelRatio: 1 }, status: 200,
    screenshot: { file: "a.png", bytes: 2048 }, problems: ["layout: too wide"],
  }];
  const html = contactSheet(results, { base: "http://x", generated_at: "now", totals: { renderings: 1, passed: 0, failed: 1 } });
  assert.match(html, /figure class="fail"/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /layout: too wide/);
  assert.equal(escape("a&b"), "a&amp;b");
});

test("markdown summary counts and reports skips", () => {
  const summary = {
    base: "http://x", generated_at: "now", totals: { renderings: 1, passed: 1, failed: 0, axeViolations: 0 },
    skipped: [{ engine: "webkit", reason: "not installed" }],
  };
  const markdown = markdownSummary(summary, [{
    engine: "chromium", engineVersion: "1", profile: "desktop", page: { route: "/" },
    observed: { width: 1280, height: 900 }, status: 200, problems: [],
  }]);
  assert.match(markdown, /1 passed, 0 failed/);
  assert.match(markdown, /Skipped webkit: not installed/);
});

test("static server serves pages and refuses traversal", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "qualification-serve-"));
  fs.mkdirSync(path.join(directory, "research"));
  fs.writeFileSync(path.join(directory, "index.html"), "<title>home</title>");
  fs.writeFileSync(path.join(directory, "research", "index.html"), "<title>research</title>");
  const server = await serve(directory);
  try {
    const home = await fetch(server.url + "/");
    assert.equal(home.status, 200);
    assert.ok((await home.text()).includes("<title>home"), "home page is served");
    const research = await fetch(server.url + "/research/");
    assert.ok((await research.text()).includes("<title>research"), "nested page is served");
    assert.equal((await fetch(server.url + "/missing/")).status, 404);
    const escaped = resolveTarget(directory, "/../../etc/passwd");
    assert.ok(escaped === null || path.resolve(escaped).startsWith(path.resolve(directory)),
      "traversal must not leave the served root");
  } finally {
    await server.close();
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
