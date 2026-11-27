"use strict";
/**
 * Individual qualification checks.
 *
 * Each check returns { name, ok, detail } and never throws for a page-level
 * problem: a failing check is a finding, not a harness crash. Checks are
 * assertions about observable page state, not claims about conformance.
 */

const MAX_TAB_STOPS = 40;

function describe(element) {
  return element;
}

async function layout(page) {
  const metrics = await page.evaluate(() => ({
    width: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
  }));
  const overflow = metrics.scrollWidth > metrics.width + 1;
  return {
    name: "layout",
    ok: !overflow,
    detail: overflow
      ? `horizontal overflow: ${metrics.scrollWidth} > ${metrics.width}`
      : `no horizontal overflow at ${metrics.width}px (${metrics.scrollHeight}px tall)`,
    metrics,
  };
}

async function images(page) {
  const result = await page.evaluate(async () => {
    const observed = [...document.querySelectorAll("img")];
    // Bound the wait for outstanding resources, including deferred images.
    // Do not change loading policy merely to force a passing observation.
    const unsettled = observed.filter((image) => !image.complete);
    if (unsettled.length) {
      let timer;
      try {
        await Promise.race([
          Promise.allSettled(unsettled.map((image) => image.decode())),
          new Promise((resolve) => { timer = setTimeout(resolve, 2000); }),
        ]);
      } finally {
        clearTimeout(timer);
      }
    }
    const missingAlt = [];
    const broken = [];
    const pending = [];
    for (const image of document.querySelectorAll("img")) {
      if (!image.hasAttribute("alt")) missingAlt.push(image.getAttribute("src") || "(inline)");
      if (!image.complete) pending.push(image.getAttribute("src") || "(inline)");
      if (image.complete && image.naturalWidth === 0) broken.push(image.getAttribute("src") || "(inline)");
    }
    return { total: document.querySelectorAll("img").length, missingAlt, broken, pending };
  });
  const ok = result.missingAlt.length === 0 && result.broken.length === 0;
  const inconclusive = result.pending.length > 0;
  const detail = ok && !inconclusive
    ? `${result.total} image(s) carry alt text and loaded`
    : `${result.missingAlt.length} without alt, ${result.broken.length} failed to load, ${result.pending.length} not loaded`;
  return { name: "images", ok, inconclusive, detail, ...result };
}

async function navigation(page) {
  const result = await page.evaluate(() => {
    const nav = document.querySelector("nav");
    const links = nav ? nav.querySelectorAll("a[href]").length : 0;
    const noscript = document.querySelector("noscript");
    return { navLinks: links, hasNoscript: Boolean(noscript), bodyText: document.body.innerText.trim().length };
  });
  const ok = result.navLinks > 0 && result.bodyText > 200;
  return {
    name: "navigation",
    ok,
    detail: ok ? `${result.navLinks} navigation link(s), ${result.bodyText} characters of text`
      : `navigation unusable without scripting (${result.navLinks} links, ${result.bodyText} characters)`,
    ...result,
  };
}

async function anchors(page) {
  const result = await page.evaluate(() => {
    const missing = [];
    let checked = 0;
    for (const link of document.querySelectorAll('a[href^="#"]')) {
      const target = link.getAttribute("href").slice(1);
      if (!target) continue;
      checked += 1;
      if (!document.getElementById(target) && !document.getElementsByName(target).length) missing.push(target);
    }
    return { checked, missing };
  });
  const ok = result.missing.length === 0;
  return {
    name: "anchors",
    ok,
    detail: ok ? `${result.checked} in-page link(s) resolve` : `missing targets: ${result.missing.join(", ")}`,
    ...result,
  };
}

async function tables(page) {
  const result = await page.evaluate(() => {
    const regions = [...document.querySelectorAll("table")].map((table) => {
      const container = table.closest(".table-responsive, .table-scroll, figure") || table.parentElement;
      const style = container ? getComputedStyle(container) : null;
      return {
        width: table.scrollWidth,
        container: container ? container.scrollWidth : 0,
        overflowX: style ? style.overflowX : null,
      };
    });
    return { tables: regions.length, regions };
  });
  const bad = result.regions.filter(
    (region) => region.width > region.container + 1 && !["auto", "scroll"].includes(region.overflowX),
  );
  return {
    name: "tables",
    ok: bad.length === 0,
    detail: result.tables === 0
      ? "no tables on this page"
      : bad.length === 0
        ? `${result.tables} table(s) fit or scroll within a container`
        : `${bad.length} table(s) overflow without a scroll container`,
    ...result,
  };
}

async function focusOrder(page) {
  const stops = [];
  await page.evaluate(() => {
    document.body.focus();
    // WeakMap keys identify actual DOM nodes, not their potentially repeated
    // labels or current document position.
    globalThis.__qualificationFocus = { seen: new WeakMap(), next: 0 };
  });
  let ended = false;
  let cycle = false;
  for (let index = 0; index < MAX_TAB_STOPS; index += 1) {
    await page.keyboard.press("Tab");
    const stop = await page.evaluate(() => {
      const element = document.activeElement;
      if (!element || element === document.body) return null;
      const state = globalThis.__qualificationFocus;
      if (!state.seen.has(element)) state.seen.set(element, state.next++);
      const style = getComputedStyle(element);
      return {
        identity: state.seen.get(element),
        tag: element.tagName.toLowerCase(),
        text: (element.innerText || element.getAttribute("aria-label") || element.getAttribute("href") || "")
          .trim().replace(/\s+/g, " ").slice(0, 60),
        outline: `${style.outlineStyle} ${style.outlineWidth}`,
        shadow: style.boxShadow === "none" ? null : style.boxShadow.slice(0, 40),
        visible: style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0 || style.boxShadow !== "none",
      };
    });
    if (!stop) { ended = true; break; }
    if (stops.some((entry) => entry.identity === stop.identity)) {
      // A repeated first control can also be a keyboard trap. Only the
      // body/null sentinel establishes an observed exit from this traversal.
      cycle = true;
      break;
    }
    stops.push(stop);
  }
  if (stops.length === 0) {
    // WebKit (like Safari by default) moves Tab between form controls only, so
    // zero stops means this engine cannot answer the question, not that the
    // page is unreachable by keyboard.
    return {
      name: "focus-order",
      ok: true,
      inconclusive: true,
      detail: "engine did not move focus with Tab; keyboard order not concluded for this engine",
      stops,
      invisible: [],
    };
  }
  const invisible = stops.filter((stop) => !stop.visible);
  const ok = invisible.length === 0;
  const truncated = !ended && !cycle;
  const inconclusive = truncated || cycle;
  return {
    name: "focus-order",
    ok,
    inconclusive,
    truncated,
    detail: `${stops.length} stop(s), ${invisible.length} without a visible indicator` +
      (truncated ? `; traversal capped at ${MAX_TAB_STOPS}` : cycle ? "; focus repeated without an observed exit; possible focus trap" : ""),
    stops,
    invisible: invisible.map((stop) => `${stop.tag}: ${stop.text}`),
  };
}

async function focus(page) {
  const result = await page.evaluate(() => {
    const first = document.querySelector("a[href], button, summary, input");
    if (!first) return { checked: 0, invisible: [] };
    first.focus();
    const style = getComputedStyle(first);
    return {
      checked: 1,
      invisible: style.outlineStyle === "none" && style.boxShadow === "none"
        ? [`${first.tagName.toLowerCase()}: ${first.innerText.trim().slice(0, 40)}`] : [],
    };
  });
  return {
    name: "focus",
    ok: result.invisible.length === 0,
    detail: result.invisible.length === 0 ? "first focusable control shows an indicator" : result.invisible.join("; "),
    ...result,
  };
}

async function print(page) {
  const result = await page.evaluate(() => {
    const article = document.querySelector("article") || document.querySelector("main");
    if (!article) return { article: false, overlay: null };
    const box = article.getBoundingClientRect();
    let overlay = null;
    for (const element of document.querySelectorAll("body *")) {
      const style = getComputedStyle(element);
      if (style.position !== "fixed" || style.display === "none") continue;
      const rect = element.getBoundingClientRect();
      if (rect.height > box.height * 0.3 && rect.width > box.width * 0.5) {
        overlay = `${element.tagName.toLowerCase()} covers ${Math.round(rect.height)}px`;
        break;
      }
    }
    return { article: true, overlay };
  });
  const ok = result.article && !result.overlay;
  return {
    name: "print",
    ok,
    detail: ok ? "article is present with no fixed overlay dominating the page" : result.overlay || "no article element",
    ...result,
  };
}

async function search(page) {
  const field = page.locator('input[type="search"], input[name="q"], #search-input').first();
  if (!(await field.count())) {
    return { name: "search", ok: false, detail: "no search field found" };
  }
  await field.fill("corkboard");
  await field.press("Enter");
  await page.waitForLoadState("load").catch(() => {});
  await page.waitForTimeout(500);
  const result = await page.evaluate(() => {
    const items = document.querySelectorAll("#search-results li, #search-results a, .search-results li, .search-results a");
    return { results: items.length, text: document.body.innerText.slice(0, 200) };
  });
  return {
    name: "search",
    ok: result.results > 0,
    detail: result.results > 0 ? `${result.results} result item(s) for "corkboard"` : "no results rendered",
    ...result,
  };
}

const CHECKS = { layout, images, navigation, anchors, tables, "focus-order": focusOrder, focus, print, search };

async function runChecks(page, names) {
  const results = [];
  for (const name of names) {
    const check = CHECKS[name];
    if (!check) {
      results.push({ name, ok: false, detail: "check is not implemented" });
      continue;
    }
    try {
      results.push(await check(page));
    } catch (error) {
      results.push({ name, ok: false, detail: `check failed: ${String(error.message || error).split("\n")[0]}` });
    }
  }
  return results;
}

module.exports = { runChecks, CHECKS, describe };
