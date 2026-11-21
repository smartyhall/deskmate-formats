"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const { ROOT, pages, sections, siteUrl, resolveLink, renderSource, searchRecord } =
  require("../lib/reference.cjs");

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
