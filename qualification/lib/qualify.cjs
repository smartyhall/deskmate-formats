"use strict";
/**
 * Cross-engine qualification runner.
 *
 * A rendering is accepted only when the document answered 200, the requested
 * route is the one that rendered (canonical path and title), the viewport is
 * the requested one, and loading settled. Everything else is a finding.
 *
 * The runner is deliberately backend-neutral: `base` is any HTTP origin, so the
 * same procedure runs against a local build, a GitHub Actions job, or an
 * approved remote browser service that speaks the same contract.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { chromium, firefox, webkit } = require("playwright");
const { ENGINES, parseEngineList, discoverEngines } = require("./engines.cjs");
const { PROFILES, parseProfileList, contextOptions } = require("./profiles.cjs");
const { runChecks } = require("./checks.cjs");

const playwright = { chromium, firefox, webkit };
const DEFAULT_TIMEOUT = 30000;
const SERIOUS = new Set(["serious", "critical"]);

function slug(value) {
  return value.replace(/^\/|\/$/g, "").replace(/[^a-z0-9]+/gi, "-") || "home";
}

function normalizeRoute(value) {
  if (typeof value !== "string") return null;
  let pathname;
  try {
    pathname = new URL(value, "https://example.invalid").pathname;
  } catch {
    return null;
  }
  if (!pathname.startsWith("/")) return null;
  return pathname.endsWith("/") ? pathname : pathname + "/";
}

/** Load routes and titles from a reviewed page map, home and search included. */
function pagesFromMap(mapPath) {
  const map = JSON.parse(fs.readFileSync(mapPath, "utf8"));
  const pages = [{ route: "/", title: "DeskMate Reference" }];
  for (const entry of map.pages) pages.push({ route: `/${entry.slug}/`, title: entry.title, id: entry.id });
  pages.push({ route: "/search/", title: "Search" });
  return pages;
}

function parsePages(value, mapPath) {
  if (!mapPath) throw new Error("qualification needs --page-map");
  const pages = pagesFromMap(mapPath);
  const byRoute = new Map(pages.map((page) => [page.route, page]));
  if (byRoute.size !== pages.length) throw new Error("duplicate page-map route");
  for (const route of byRoute.keys()) validateRoute(route);
  if (!value || value === "all") return pages;
  const routes = String(value).split(",").map((route) => route.trim());
  if (!routes.length || routes.some((route) => !route)) throw new Error("empty route");
  return [...new Set(routes.map(validateRoute))].map((route) => {
    const page = byRoute.get(route);
    if (!page) throw new Error(`unknown page-map route: ${route}`);
    return page;
  });
}

function validateRoute(value) {
  if (typeof value !== "string" || !/^\/(?:[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*\/?)?$/.test(value)) {
    throw new Error("invalid qualification route");
  }
  return value.endsWith("/") ? value : value + "/";
}

function renderingState(result) {
  if (result.problems.length) return "failed";
  if (result.checks?.some((check) => check.inconclusive)) return "inconclusive";
  return "passed";
}

async function qualifyPage(context, page, options, engine, profile) {
  const started = Date.now();
  const consoleMessages = [];
  const failedRequests = [];
  const pageErrors = [];

  const tab = await context.newPage();
  tab.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleMessages.push({ type: message.type(), text: message.text().slice(0, 300) });
    }
  });
  tab.on("pageerror", (error) => pageErrors.push(String(error.message || error).slice(0, 300)));
  tab.on("requestfailed", (request) => {
    failedRequests.push({ url: request.url(), error: request.failure()?.errorText || "failed" });
  });

  if (profile.media) await tab.emulateMedia(profile.media);

  const url = options.base.replace(/\/$/, "") + page.route;
  let response = null;
  try {
    response = await tab.goto(url, { waitUntil: "load", timeout: options.timeout });
    await tab.waitForLoadState("networkidle", { timeout: Math.min(options.timeout, 10000) });
  } catch (error) {
    const result = {
      engine, engineVersion: null, profile: profile.name, page,
      status: response ? response.status() : null,
      problems: [`navigation failed: ${String(error.message || error).split("\n")[0]}`],
      checks: [], console: consoleMessages, failedRequests, pageErrors,
      durationMs: Date.now() - started,
    };
    await tab.close();
    return result;
  }

  const status = response ? response.status() : null;
  const observed = await tab.evaluate(() => ({
    path: location.pathname,
    title: document.title,
    canonical: (document.querySelector('link[rel="canonical"]') || {}).href || null,
    width: window.innerWidth,
    height: window.innerHeight,
    scrollWidth: document.documentElement.scrollWidth,
    devicePixelRatio: window.devicePixelRatio,
  }));

  const problems = [];
  if (status !== 200) problems.push(`document answered ${status}`);
  if (normalizeRoute(observed.path) !== page.route) {
    problems.push(`rendered ${observed.path}, expected ${page.route}`);
  }
  const canonical = normalizeRoute(observed.canonical);
  if (!canonical || canonical !== page.route) problems.push(`canonical ${observed.canonical} does not establish ${page.route}`);
  if (page.title && !observed.title.includes(page.title)) {
    problems.push(`title ${JSON.stringify(observed.title)} lacks ${JSON.stringify(page.title)}`);
  }
  const requested = profile.context.viewport;
  if (requested && (observed.width !== requested.width || observed.height !== requested.height)) {
    problems.push(`viewport ${observed.width}x${observed.height}, requested ${requested.width}x${requested.height}`);
  }
  for (const failure of failedRequests) problems.push(`request failed: ${failure.url} (${failure.error})`);
  for (const error of pageErrors) problems.push(`page error: ${error}`);

  const checks = await runChecks(tab, profile.checks);
  for (const check of checks) if (!check.ok) problems.push(`${check.name}: ${check.detail}`);

  for (const message of consoleMessages) {
    if (message.type === "error") problems.push(`console error: ${message.text}`);
  }

  // axe-core needs scripting; a no-JavaScript profile reports that it could not
  // run rather than recording a silent pass.
  let axe = null;
  if (options.axe && profile.context.javaScriptEnabled === false) {
    axe = { skipped: "axe requires JavaScript; not run for this profile" };
  } else if (options.axe) {
    try {
      const { AxeBuilder } = require("@axe-core/playwright");
      const analysis = await new AxeBuilder({ page: tab }).analyze();
      axe = {
        violations: analysis.violations.map((violation) => ({
          id: violation.id,
          impact: violation.impact,
          help: violation.help,
          nodes: violation.nodes.length,
          targets: violation.nodes.slice(0, 3).map((node) => node.target.join(" ")),
        })),
        passes: analysis.passes.length,
        incomplete: analysis.incomplete.length,
      };
      for (const violation of axe.violations) {
        if (SERIOUS.has(violation.impact)) {
          problems.push(`axe ${violation.impact}: ${violation.id} (${violation.nodes} node(s))`);
        }
      }
    } catch (error) {
      axe = { error: String(error.message || error).split("\n")[0] };
      problems.push(`axe failed: ${axe.error}`);
    }
  }

  const name = `${engine}-${profile.name}-${slug(page.route)}`;
  const file = `${name}.png`;
  await tab.screenshot({ path: path.join(options.out, file), fullPage: true });
  const bytes = fs.readFileSync(path.join(options.out, file));

  await tab.close();
  return {
    engine,
    profile: profile.name,
    page,
    status,
    url,
    observed,
    checks,
    axe,
    console: consoleMessages,
    failedRequests,
    pageErrors,
    screenshot: { file, sha256: crypto.createHash("sha256").update(bytes).digest("hex"), bytes: bytes.length },
    durationMs: Date.now() - started,
    problems,
  };
}

async function qualify(options) {
  fs.mkdirSync(options.out, { recursive: true });
  const engineNames = parseEngineList(options.engines);
  const profileNames = parseProfileList(options.profiles);
  const pages = parsePages(options.pages, options.pageMap);
  const availability = await discoverEngines(playwright, engineNames);

  const results = [];
  const skipped = [];
  for (const engine of availability) {
    if (!engine.available) {
      skipped.push({ engine: engine.name, reason: engine.reason });
      continue;
    }
    const browser = await playwright[ENGINES[engine.name].launch.name].launch(
      ENGINES[engine.name].launch.channel ? { channel: ENGINES[engine.name].launch.channel } : {},
    );
    const version = browser.version();
    try {
      for (const profileName of profileNames) {
        const profile = { ...PROFILES[profileName], name: profileName };
        for (const page of pages) {
          const context = await browser.newContext(contextOptions(profile));
          try {
            const result = await qualifyPage(context, page, options, engine.name, profile);
            result.engineVersion = version;
            results.push(result);
            const state = renderingState(result);
            console.log(`${engine.name} ${profileName} ${page.route}: ${state}`);
          } finally {
            await context.close();
          }
        }
      }
    } finally {
      await browser.close();
    }
  }

  const summary = {
    generated_at: new Date().toISOString(),
    base: options.base,
    revision: process.env.GITHUB_SHA || null,
    engines: availability,
    skipped,
    profiles: profileNames,
    pages: pages.map((page) => page.route),
    totals: {
      requested: engineNames.length * profileNames.length * pages.length,
      renderings: results.length,
      passed: results.filter((result) => renderingState(result) === "passed").length,
      failed: results.filter((result) => renderingState(result) === "failed").length,
      inconclusive: results.filter((result) => renderingState(result) === "inconclusive").length,
      axeViolations: results.reduce((total, result) => total + (result.axe?.violations?.length || 0), 0),
    },
  };
  fs.writeFileSync(path.join(options.out, "qualification-summary.json"),
    JSON.stringify({ summary, results }, null, 2) + "\n", "utf8");
  return { summary, results };
}

module.exports = { qualify, pagesFromMap, normalizeRoute, validateRoute, parsePages, renderingState, slug, DEFAULT_TIMEOUT, SERIOUS };
