"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const { ROOT, pages, sections, siteUrl, resolveLink, renderSource, searchRecord } =
  require("../lib/reference.cjs");

test("source-map entries resolve to existing, uniquely identified Markdown", () => {
  assert.equal(pages.length, 26);
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
