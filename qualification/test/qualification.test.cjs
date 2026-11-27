"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { parseEngineList, LINUX_ENGINES, WINDOWS_ENGINES, MACOS_ENGINES } = require("../lib/engines.cjs");
const { parseProfileList, contextOptions, PROFILES } = require("../lib/profiles.cjs");
const { canonicalMatches, normalizeRoute, pagesFromMap, validateRoute, parsePages, renderingState, slug } = require("../lib/qualify.cjs");
const { contactSheet, markdownSummary, escape } = require("../lib/report.cjs");
const { serve, resolveTarget } = require("../lib/serve.cjs");
const { CHECKS } = require("../lib/checks.cjs");
const { qualificationExitCode } = require("../cli.cjs");

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
  assert.ok(!html.toLowerCase().includes("<script>"), "raw script tags are escaped");
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

test("focused routes use reviewed titles and reject untrusted route syntax", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "qualification-map-"));
  try {
    const mapPath = path.join(directory, "map.json");
    fs.writeFileSync(mapPath, JSON.stringify({
      pages: [{ id: "research.hub", slug: "research", title: "Research" }],
    }));
    assert.deepEqual(parsePages("/research,/research/", mapPath), [
      { route: "/research/", title: "Research", id: "research.hub" },
    ]);
    assert.equal(validateRoute("/"), "/");
    for (const value of ["//example.test/", "/../", "/foo?query=1", "/foo#bar", "/foo;id", "/foo\nbar", "https://example.test/"]) {
      assert.throws(() => validateRoute(value), /invalid qualification route/);
    }
    assert.throws(() => parsePages("/unknown/", mapPath), /unknown page-map route/);
    assert.throws(() => parsePages("/research/,", mapPath), /empty route/);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("inconclusive checks are not successful renderings", () => {
  assert.equal(renderingState({ problems: [], checks: [] }), "passed");
  assert.equal(renderingState({ problems: [], checks: [{ inconclusive: true }] }), "inconclusive");
  assert.equal(renderingState({ problems: ["failure"], checks: [{ inconclusive: true }] }), "failed");
});

test("navigation failures without screenshots remain reportable", () => {
  const result = { engine: "webkit", profile: "desktop", page: { route: "/" }, status: null,
    problems: ["navigation failed"], checks: [] };
  const summary = { base: "http://x", generated_at: "now", totals: { renderings: 1, passed: 0, failed: 1 } };
  assert.match(contactSheet([result], summary), /No screenshot available/);
});

test("qualification status distinguishes incomplete and inconclusive results", () => {
  const strict = { requireMatrix: true, allowFindings: false };
  const exploratory = { requireMatrix: true, allowFindings: true };
  assert.equal(qualificationExitCode({ requested: 2, renderings: 2, passed: 2 }, strict), 0);
  assert.equal(qualificationExitCode({ requested: 2, renderings: 2, passed: 1, inconclusive: 1 }, strict), 1);
  assert.equal(qualificationExitCode({ requested: 2, renderings: 2, passed: 1, inconclusive: 1 }, exploratory), 0);
  assert.equal(qualificationExitCode({ requested: 2, renderings: 1, passed: 1 }, exploratory), 1);
  assert.equal(qualificationExitCode({ requested: 2, renderings: 0, passed: 0 }, { allowFindings: true }), 1);
});

test("inconclusive rendering has visible outcome and escaped reason", () => {
  const result = { engine: "webkit", profile: "keyboard", page: { route: "/" }, status: 200,
    problems: [], checks: [{ name: "keyboard", inconclusive: true, detail: "<focus unknown>" }] };
  const summary = { base: "http://x", generated_at: "now", totals: { renderings: 1, passed: 0, failed: 0, inconclusive: 1 } };
  const html = contactSheet([result], summary);
  assert.match(html, /figure class="inconclusive"/);
  assert.match(html, / — Inconclusive<\/strong>/);
  assert.match(html, /Inconclusive: keyboard: &lt;focus unknown&gt;/);
});

test("canonical origin is checked independently of normalized route", () => {
  assert.equal(canonicalMatches("https://deskmate.retroconnect.org/research/", "https://deskmate.retroconnect.org", "/research/"), true);
  assert.equal(canonicalMatches("https://mirror.example/research/", "https://deskmate.retroconnect.org", "/research/"), false);
  assert.equal(canonicalMatches("https://deskmate.retroconnect.org/research/?x=1", "https://deskmate.retroconnect.org", "/research/"), false);
  assert.equal(canonicalMatches(null, "https://deskmate.retroconnect.org", "/research/"), false);
});

function focusPage(sequence) {
  let position = -1;
  return {
    keyboard: { press: async () => { position += 1; } },
    evaluate: async () => position < 0 ? undefined : sequence[position] || null,
  };
}

test("duplicate focus labels do not hide later invisible controls", async () => {
  const sequence = [
    { identity: 0, tag: "a", text: "Read more", visible: true },
    { identity: 1, tag: "a", text: "Read more", visible: true },
    { identity: 2, tag: "button", text: "Invisible", visible: false },
  ];
  const result = await CHECKS["focus-order"](focusPage(sequence));
  assert.equal(result.ok, false);
  assert.equal(result.stops.length, 3);
  assert.deepEqual(result.invisible, ["button: Invisible"]);
});

test("bounded traversal is inconclusive rather than a pass", async () => {
  const sequence = Array.from({ length: 40 }, (_, identity) => ({ identity, tag: "a", text: "Next", visible: true }));
  const result = await CHECKS["focus-order"](focusPage(sequence));
  assert.equal(result.truncated, true);
  assert.equal(result.inconclusive, true);
  assert.equal(renderingState({ problems: [], checks: [result] }), "inconclusive");
});

test("pending images are inconclusive, broken or missing-alt images fail", async () => {
  const check = (data) => CHECKS.images({ evaluate: async () => data });
  const pending = await check({ total: 1, missingAlt: [], broken: [], pending: ["lazy.png"] });
  assert.equal(pending.ok, true);
  assert.equal(pending.inconclusive, true);
  const broken = await check({ total: 1, missingAlt: [], broken: ["bad.png"], pending: [] });
  assert.equal(broken.ok, false);
});
