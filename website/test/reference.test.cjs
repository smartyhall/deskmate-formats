"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const {
  ROOT, pages, byId, sections, siteUrl, resolveLink, renderSource, searchRecord,
  roleLabel, breadcrumbsFor, canonicalFor, formatDate, SITE_ORIGIN,
} = require("../lib/reference.cjs");
const Sitemap = require("../src/sitemap.11ty.js");
const Robots = require("../src/robots.11ty.js");

test("source-map entries resolve to existing, uniquely identified Markdown", () => {
  assert.ok(pages.length >= 27);
  const ids = new Set(), slugs = new Set();
  for (const entry of pages) {
    assert.equal(ids.has(entry.id), false);
    assert.equal(slugs.has(entry.slug), false);
    ids.add(entry.id); slugs.add(entry.slug);
    assert.match(entry.source, /^docs\/.+\.md$/);
    assert.equal(fs.existsSync(path.join(ROOT, entry.source)), true);
  }
  assert.equal(sections.reduce((total, group) => total + group.pages.length, 0), pages.length);
  assert.equal(pages.find((entry) => entry.id === "history.chronology").slug, "history/chronology");
});

test("installation references remain mapped with distinct IDs", () => {
  assert.ok(pages.some((entry) => entry.id === "applications.installations"));
  assert.ok(pages.some((entry) => entry.id === "applications.installation-305"));
});

test("both GitHub subdirectory and self-hosted root paths work", () => {
  const previous = process.env.SITE_BASE_PATH;
  try {
    process.env.SITE_BASE_PATH = "/";
    assert.equal(siteUrl("/search/"), "/search/");
    process.env.SITE_BASE_PATH = "/deskmate-formats/";
    assert.equal(siteUrl("/search/"), "/deskmate-formats/search/");
    assert.throws(() => siteUrl("search"), /root-relative/);
    process.env.SITE_BASE_PATH = "//bad/";
    assert.throws(() => siteUrl("/search/"), /SITE_BASE_PATH/);
  } finally {
    if (previous === undefined) delete process.env.SITE_BASE_PATH;
    else process.env.SITE_BASE_PATH = previous;
  }
});

test("mapped Markdown links are routed internally", () => {
  const source = pages.find((entry) => entry.id === "system.manufacturer-crosswalk");
  const target = pages.find((entry) => entry.id === "system.page-setup");
  assert.equal(resolveLink("tandy-common-headers.md#header-layout", source),
    "/" + target.slug + "/#header-layout");
  assert.throws(() => resolveLink("../research/nonmapped.md", source), /does not exist/);
  assert.equal(resolveLink("#section", source), "#section");
  assert.equal(resolveLink("https://example.org", source), "https://example.org");
  assert.equal(resolveLink("../../PROJECT_STATUS.md", source),
    "https://github.com/smartyhall/deskmate-formats/blob/main/PROJECT_STATUS.md");
  // A root file that exists but is outside the publication boundary is named,
  // not linked; a root path that does not exist at all is an authoring error.
  assert.equal(resolveLink("../../LICENSING.md", source), "#unpublished-source");
  assert.throws(() => resolveLink("../../unreviewed-root-secret.md", source), /does not exist/);
});

test("historical Markdown renders and is indexed without copying originals", () => {
  const source = pages.find((entry) => entry.id === "system.page-setup");
  assert.match(renderSource(source), /<h1[^>]*>/);
  const record = searchRecord(source);
  assert.equal(record.url, "/" + source.slug + "/");
  assert.ok(record.text.includes("PGSETUP"));
});

test("only explicitly authored assets may be copied to the site", () => {
  const config = fs.readFileSync(path.join(ROOT, "website/eleventy.config.cjs"), "utf8");
  assert.match(config, /src\/assets/);
  assert.doesNotMatch(config, /DOSLAB_ROOT|addPassthroughCopy\(\s*["']docs/);
});

test("unmodified upstream BOOTSTRA.386 replaces the independent demo theme", () => {
  const template = fs.readFileSync(
    path.join(ROOT, "website/src/_includes/base.njk"), "utf8"
  );
  const adapter = fs.readFileSync(
    path.join(ROOT, "website/src/assets/site-layout.css"), "utf8"
  );
  const installer = fs.readFileSync(
    path.join(ROOT, "website/scripts/vendor_bootstra.py"), "utf8"
  );
  assert.match(template, /bootstra386\/css\/bootstrap\.min\.css/);
  assert.match(template, /bootstra386\/js\/bootstrap-386\.js/);
  assert.doesNotMatch(template, /assets\/site\.css/);
  assert.match(adapter, /SPDX-License-Identifier: Apache-2\.0/);
  assert.match(installer, /ZIP_BLOB = "[0-9a-f]{40}"/);
  assert.match(installer, /sha1\(/);
});

test("bare .md filenames do not become Internet links", () => {
  const visual = pages.find((entry) => entry.slug === "evidence/visual-policy");
  const calendar = pages.find((entry) => entry.slug === "formats/calendar");
  assert.ok(visual && calendar);
  assert.doesNotMatch(renderSource(visual), /https?:\/\/AGENTS\.md/i);
  assert.doesNotMatch(renderSource(calendar), /https?:\/\/compatibility\.md/i);
});

test("combined archival report retains a single top-level heading", () => {
  const calendar = pages.find((entry) => entry.slug === "formats/calendar");
  assert.ok(calendar);
  const html = renderSource(calendar);
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
  assert.match(html, /<h2[^>]*id="phase-iii-a-bounded-multi-record-generation-and-deskmate-validation"/);
});

test("site layout preserves independently scrollable technical tables on phones", () => {
  const css = fs.readFileSync(path.join(ROOT, "website/src/assets/site-layout.css"), "utf8");
  assert.match(css, /\.document\s*\{[^}]*overflow-x:\s*clip/);
  assert.match(css, /\.document pre\s*\{[^}]*overflow-x:\s*auto/);
  assert.match(css, /\.document \.table-scroll\s*\{[^}]*overflow-x:\s*auto/);
  // A region that scrolls has to be reachable without a pointing device.
  assert.match(css, /\.document \.table-scroll:focus[^{]*\{[^}]*outline:/);
  const calendar = pages.find((entry) => entry.slug === "formats/calendar");
  assert.match(renderSource(calendar), /<div class="table-scroll" tabindex="0"><table>/);
  assert.match(renderSource(calendar), /<pre tabindex="0"><code/);
});


test("newcomer introduction leads the reference and search index", () => {
  const entry = pages.find((item) => item.id === "history.introduction");
  assert.equal(entry.slug, "start");
  assert.equal(sections[0].id, "deskmate");
  assert.equal(sections[0].hub.id, "deskmate.overview");
  assert.equal(sections[0].subsections[0].pages[0].id, entry.id);
  const record = searchRecord(entry);
  assert.equal(record.url, "/start/");
  assert.match(record.text, /approachable/);
  const rendered = renderSource(entry);
  assert.match(rendered, /Discover DeskMate/);
  assert.match(rendered, /original software/i);
  for (const name of [
    "ui.desktop.launcher.png", "ui.desktop.desktop-menu.png",
    "ui.calendar.day-view.png", "ui.express-publisher.workspace.png",
  ]) {
    assert.ok(rendered.includes(name), "Introduction does not show " + name);
  }
  assert.equal((rendered.match(/class="reference-figure"/g) || []).length, 4);
});

test("homepage prioritizes illustrated discovery, technical reference and recovery", () => {
  const Home = require("../src/index.11ty.js");
  const html = new Home().render();
  assert.match(html, /Meet the other desktop of the PC era/);
  assert.match(html, /Where would you like to begin/);
  assert.match(html, /href="\/start\/"/);
  assert.match(html, /href="\/deskmate\/"/);
  assert.match(html, /href="\/formats\/"/);
  assert.match(html, /href="\/recovery\/"/);
  assert.match(html, /assets\/reference\/collection-01\/ui.desktop.launcher.png/);
  assert.match(html, /width="640" height="480"/);
  assert.doesNotMatch(html, /Private evidence paths|raw ROMs/);
});

test("discovery page and homepage honor non-root path deployment", () => {
  const previous = process.env.SITE_BASE_PATH;
  try {
    process.env.SITE_BASE_PATH = "/deskmate-formats/";
    const Home = require("../src/index.11ty.js");
    const html = new Home().render();
    assert.match(html, /href="\/deskmate-formats\/start\/"/);
    assert.match(html, /src="\/deskmate-formats\/assets\/reference\//);
    const entry = pages.find((item) => item.id === "history.introduction");
    const intro = renderSource(entry);
    assert.match(intro, /src="\/deskmate-formats\/assets\/reference\//);
  } finally {
    if (previous === undefined) delete process.env.SITE_BASE_PATH;
    else process.env.SITE_BASE_PATH = previous;
  }
});

test("baseline page IDs retain their published routes", () => {
  const baseline = JSON.parse(fs.readFileSync(
    path.join(ROOT, "docs/site/published-route-baseline.json"), "utf8"
  ));
  assert.equal(baseline.schema_version, 1);
  const byId = new Map(pages.map((page) => [page.id, "/" + page.slug + "/"]));
  for (const entry of baseline.routes) {
    if (entry.page_id !== null) {
      assert.equal(byId.get(entry.page_id), entry.route, "Changed baseline route: " + entry.page_id);
    }
  }
});

test("navigation uses five reader sections with one hub each", () => {
  assert.deepEqual(sections.map((section) => section.id),
    ["deskmate", "formats", "recovery", "research", "project"]);
  for (const section of sections) {
    assert.equal(section.pages.filter((page) => page.is_hub).length, 1);
    assert.equal(section.hub.slug, section.id);
    assert.equal(section.hub.subsection, null);
    assert.ok(section.subsections.length >= 1);
    for (const group of section.subsections) assert.ok(group.pages.length);
  }
  assert.equal(sections.reduce((total, section) => total + section.pages.length, 0),
    pages.length);
});

test("every mapped page belongs to exactly one section listing", () => {
  for (const page of pages) {
    const section = sections.find((item) => item.id === page.section);
    assert.ok(section, "no section for " + page.id);
    assert.equal(section.pages.filter((item) => item.id === page.id).length, 1);
  }
});

test("section membership does not follow URL prefixes", () => {
  assert.equal(byId.get("formats.sound-research").section, "research");
  assert.equal(byId.get("applications.automatic-house-x10").section, "research");
  assert.equal(byId.get("evidence.visual-policy").section, "project");
  assert.equal(byId.get("system.architecture").section, "formats");
  assert.equal(byId.get("applications.ecosystem").section, "deskmate");
});

test("hubs carry no evidence-role badge and documents get readable labels", () => {
  assert.equal(roleLabel(byId.get("deskmate.overview")), null);
  assert.equal(roleLabel(byId.get("formats.calendar")), "Dated snapshot");
  assert.equal(roleLabel(byId.get("formats.filer")), "Manufacturer reference");
  assert.equal(roleLabel(byId.get("research.draw")), "Dated experiment report");
  assert.equal(roleLabel(byId.get("site.authoring")), "Project planning document");
});

test("breadcrumbs lead from home through the section to the page", () => {
  const crumbs = breadcrumbsFor(byId.get("research.draw"));
  assert.deepEqual(crumbs.map((crumb) => crumb.label),
    ["Home", "Research", "Format experiments", "Native graphics experiments"]);
  assert.equal(crumbs[1].href, "/research/");
  const hubCrumbs = breadcrumbsFor(byId.get("formats.overview"));
  assert.deepEqual(hubCrumbs.map((crumb) => crumb.label), ["Home", "File formats"]);
  assert.equal(hubCrumbs[1].href, undefined);
});

test("hub pages render as prose-led landing pages with working links", () => {
  for (const section of sections) {
    const html = renderSource(section.hub);
    assert.match(html, /<h2[^>]*>Start here<\/h2>/, section.id + " lacks a start-here list");
    assert.match(html, /<h2[^>]*>Continue<\/h2>/, section.id + " lacks onward links");
    assert.doesNotMatch(html, /#unpublished-source/);
  }
});

test("links to unpublished repository files keep their wording without an anchor", () => {
  const html = renderSource(byId.get("research.evidence"));
  assert.doesNotMatch(html, /unpublished-source/);
  assert.match(html, /LICENSING\.md/);
  assert.doesNotMatch(html, /href="[^"]*LICENSING\.md"/);
  assert.match(html, /href="https:\/\/github\.com\/smartyhall\/deskmate-formats\/blob\/main\/tests\//);
});

test("canonical URLs name the published origin, not the preview path", () => {
  assert.equal(SITE_ORIGIN, "https://deskmate.retroconnect.org");
  assert.equal(canonicalFor(byId.get("formats.calendar")),
    "https://deskmate.retroconnect.org/formats/calendar/");
  assert.equal(canonicalFor(byId.get("deskmate.overview")),
    "https://deskmate.retroconnect.org/deskmate/");
  assert.equal(canonicalFor(null), "https://deskmate.retroconnect.org/");
});

test("the sitemap lists every published page on the canonical origin", () => {
  const xml = new Sitemap().render();
  assert.match(xml, /^<\?xml version="1\.0" encoding="UTF-8"\?>/);
  for (const page of pages)
    assert.ok(xml.includes("<loc>" + SITE_ORIGIN + "/" + page.slug + "/</loc>"), page.id);
  assert.ok(xml.includes("<loc>" + SITE_ORIGIN + "/</loc>"));
  assert.ok(xml.includes("<loc>" + SITE_ORIGIN + "/search/</loc>"));
  assert.equal((xml.match(/<url>/g) || []).length, pages.length + 2);
});

test("robots.txt allows crawling and names the sitemap", () => {
  const text = new Robots().render();
  assert.match(text, /^User-agent: \*$/m);
  assert.match(text, /^Allow: \/$/m);
  assert.match(text, /Sitemap: https:\/\/deskmate\.retroconnect\.org\/sitemap\.xml/);
});

test("contents lists appear exactly on long, non-hub pages", () => {
  for (const page of pages) {
    const html = renderSource(page);
    const headings = (html.match(/<h2[ >]/g) || []).length;
    const hasContents = html.includes('class="page-contents"');
    assert.equal(hasContents, !page.is_hub && headings >= 4, page.id);
    if (!hasContents) continue;
    const ids = [...html.matchAll(/<a href="#([a-z0-9-]+)">/g)].map((match) => match[1]);
    assert.ok(ids.length >= 4, page.id);
    for (const id of ids) assert.ok(html.includes('id="' + id + '"'), page.id + " missing " + id);
    const collapsed = !/<details class="page-contents" open>/.test(html);
    assert.equal(collapsed, ids.length > 8, page.id + " collapse rule");
  }
});

const HUB_SEQUENCE = ["deskmate", "formats", "recovery", "research", "project"];

function hubLinks(entry) {
  const raw = fs.readFileSync(path.join(ROOT, entry.source), "utf8");
  return [...raw.matchAll(/\[([^\]]+)\]\(([^)\s]+)\)/g)]
    .map((match) => ({ text: match[1], href: match[2], url: resolveLink(match[2], entry) }));
}

test("every hub link resolves to a mapped site page", () => {
  const routes = new Set(pages.map((page) => "/" + page.slug + "/"));
  for (const section of sections) {
    const links = hubLinks(section.hub);
    assert.ok(links.length >= 8, section.id + " has too few links");
    for (const link of links) {
      assert.match(link.url, /^\//, section.id + ": " + link.href + " -> " + link.url);
      assert.equal(routes.has(link.url.split("#")[0]), true,
        section.id + ": " + link.href + " -> " + link.url);
    }
  }
});

test("the five hubs form one sequential reading path", () => {
  HUB_SEQUENCE.forEach((id, index) => {
    const hub = byId.get(id + ".overview");
    const raw = fs.readFileSync(path.join(ROOT, hub.source), "utf8");
    const next = /^- Next: \[[^\]]+\]\(([^)]+)\)/m.exec(raw);
    const previous = /^- Previous: \[[^\]]+\]\(([^)]+)\)/m.exec(raw);
    if (index < HUB_SEQUENCE.length - 1) {
      assert.ok(next, id + " has no onward link");
      assert.equal(resolveLink(next[1], hub), "/" + HUB_SEQUENCE[index + 1] + "/");
    } else {
      assert.equal(next, null, "the last hub must not link onward");
    }
    if (index > 0) {
      assert.ok(previous, id + " has no previous link");
      assert.equal(resolveLink(previous[1], hub), "/" + HUB_SEQUENCE[index - 1] + "/");
    } else {
      assert.equal(previous, null, "the first hub must not link back");
    }
  });
});

test("relative links to nonexistent destinations fail the build", () => {
  const hub = byId.get("formats.overview");
  assert.throws(() => resolveLink("../recovery.md", hub), /Broken relative link/);
  assert.throws(() => resolveLink("../research/no-such-report.md", hub), /does not exist/);
  // An existing repository document that is not mapped stays a source link.
  assert.equal(fs.existsSync(path.join(ROOT, "docs/research/86box-client.md")), true);
  assert.equal(resolveLink("../research/86box-client.md", hub),
    "https://github.com/smartyhall/deskmate-formats/blob/main/docs/research/86box-client.md");
  // Case is part of the path even on a case-insensitive filesystem.
  assert.throws(() => resolveLink("../research/86Box-client.md", hub), /does not exist/);
});

test("the research chronology agrees with the recorded report dates", () => {
  const hub = byId.get("research.overview");
  const raw = fs.readFileSync(path.join(ROOT, hub.source), "utf8");
  const listed = [...raw.matchAll(/^- \*\*([^*]+)\*\* — \[[^\]]+\]\(([^)]+)\)/gm)]
    .map((match) => ({ date: match[1], url: resolveLink(match[2], hub) }));
  const reports = pages.filter((page) => page.section === "research" && !page.is_hub);
  const dated = reports.filter((page) => page.date)
    .sort((left, right) => left.date.localeCompare(right.date) || left.order - right.order)
    .map((page) => ({ date: formatDate(page.date), url: "/" + page.slug + "/" }));
  assert.deepEqual(listed, dated);
  const undatedNote = /carry no run date\.([\s\S]*?)## Sources/.exec(raw);
  assert.ok(undatedNote, "the hub must say which reports are undated");
  for (const page of reports.filter((item) => !item.date))
    assert.ok(undatedNote[1].includes(page.source.replace(/^docs\//, "../")), page.id);
});

test("recorded dates render as American long dates", () => {
  assert.equal(formatDate("2026-11-01"), "November 1, 2026");
  assert.equal(formatDate("2026-11-17"), "November 17, 2026");
  assert.equal(formatDate(null), null);
  assert.equal(formatDate("2026-13-01"), null);
  assert.equal(formatDate("17-11-2026"), null);
});

test("the search page keeps the section hubs reachable without JavaScript", () => {
  const Search = require("../src/search.11ty.js");
  const html = new Search().render();
  assert.match(html, /<noscript>/);
  for (const section of sections)
    assert.ok(html.includes('href="' + siteUrl("/" + section.hub.slug + "/") + '"'),
      section.id + " is missing from the no-script fallback");
});

test("review capture targets follow the reviewed page map", () => {
  const { captureTargets, VIEWPORTS } = require("../scripts/capture_review.cjs");
  assert.deepEqual(captureTargets().map((target) => target.route),
    ["/"].concat(sections.map((section) => "/" + section.hub.slug + "/")));
  assert.deepEqual(VIEWPORTS.map((viewport) => viewport.name), ["desktop", "phone"]);
  assert.equal(VIEWPORTS[1].width, 390);
});

test("capture route normalization accepts public forms only", () => {
  const { normalizeRoute } = require("../scripts/capture_review.cjs");
  assert.equal(normalizeRoute("/research"), "/research/");
  assert.equal(normalizeRoute("https://deskmate.retroconnect.org/research/?q=1#top"), "/research/");
  assert.equal(normalizeRoute("research/"), "/research/");
  assert.equal(normalizeRoute(null), null);
  assert.equal(normalizeRoute(42), null);
});

test("capture reads PNG dimensions from the header", () => {
  const { parsePngSize } = require("../scripts/capture_review.cjs");
  const header = Buffer.alloc(24);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(header, 0);
  header.write("IHDR", 12, "ascii");
  header.writeUInt32BE(390, 16);
  header.writeUInt32BE(844, 20);
  assert.deepEqual(parsePngSize(header), { width: 390, height: 844 });
  assert.throws(() => parsePngSize(Buffer.from("not a png")), /not a PNG/);
});

test("keyboard focus stays visible where the theme removes outlines", () => {
  const css = fs.readFileSync(path.join(ROOT, "website/src/assets/site-layout.css"), "utf8");
  assert.match(css, /a:focus-visible[\s\S]{0,300}?outline:\s*2px solid/);
  assert.match(css, /summary:focus-visible/);
});

test("the primary navigation keeps a focus indicator the theme would remove", () => {
  const css = fs.readFileSync(path.join(ROOT, "website/src/assets/site-layout.css"), "utf8");
  assert.match(css, /nav\.navbar a\.nav-link:focus-visible\s*\{[^}]*outline:\s*2px solid/);
});
