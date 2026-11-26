"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const {
  ROOT, pages, byId, sections, siteUrl, resolveLink, renderSource, searchRecord,
  roleLabel, breadcrumbsFor,
} = require("../lib/reference.cjs");

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
  assert.match(resolveLink("../research/nonmapped.md", source),
    /^https:\/\/github\.com\/smartyhall\/deskmate-formats\/blob\/main\/docs\/research\//);
  assert.equal(resolveLink("#section", source), "#section");
  assert.equal(resolveLink("https://example.org", source), "https://example.org");
  assert.equal(resolveLink("../../PROJECT_STATUS.md", source),
    "https://github.com/smartyhall/deskmate-formats/blob/main/PROJECT_STATUS.md");
  assert.equal(resolveLink("../../unreviewed-root-secret.md", source), "#unpublished-source");
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
  assert.match(css, /\.document table\s*\{[^}]*overflow-x:\s*auto/);
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
