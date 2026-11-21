"use strict";
const fs = require("node:fs");
const path = require("node:path");
const MarkdownIt = require("markdown-it");
const { readFigures, injectFigures } = require("./figures.cjs");
const ROOT = path.resolve(__dirname, "../..");
const pages = Object.freeze(JSON.parse(
  fs.readFileSync(path.join(ROOT, "docs/site/page-map.json"), "utf8")
).pages);
const bySource = new Map(pages.map((p) => [p.source, p]));
const names = Object.freeze({
  planning: "Project and planning",
  system: "System architecture",
  formats: "Native formats",
  applications: "Applications and ecosystem",
  recovery: "Recovery tools",
  research: "Native experiments",
  evidence: "Evidence and verification",
});
const sections = Object.freeze(
  Object.entries(names).map(([id, title]) => ({
    id, title, pages: pages.filter((page) => page.section === id),
  }))
);
const md = new MarkdownIt({ html: false, linkify: true, typographer: false });
// Avoid treating bare Markdown filenames such as AGENTS.md as Internet domains.
md.linkify.set({ fuzzyLink: false });
// Render only figure blocks generated from the vetted site image manifest.
md.renderer.rules.reference_figure_block = (tokens, idx) => tokens[idx].content + "\n";

function siteUrl(pathname) {
  if (typeof pathname !== "string" || !pathname.startsWith("/") ||
      pathname.startsWith("//")) throw new Error("Site URL must be root-relative");
  const base = process.env.SITE_BASE_PATH || "/";
  if (!/^\/(?:[A-Za-z0-9_-]+\/)*$/.test(base)) {
    throw new Error("SITE_BASE_PATH must be a slash-delimited directory path");
  }
  return base === "/" ? pathname : base.slice(0, -1) + pathname;
}
function pageUrl(entry) {
  return siteUrl("/" + entry.slug + "/");
}
function sourcePath(entry) {
  const absolute = path.resolve(ROOT, entry.source);
  if (!absolute.startsWith(ROOT + path.sep) || !absolute.endsWith(".md"))
    throw new Error("Unapproved document source: " + entry.source);
  return absolute;
}
function resolveLink(href, entry) {
  if (!href || href[0] === "#") return href;
  if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith("//")) return href;
  if (href.startsWith("/")) return siteUrl(href);
  const bare = href.split(/[?#]/, 1)[0];
  if (!bare) return href;
  const suffix = href.slice(bare.length);
  let resolved;
  try {
    resolved = path.posix.normalize(
      path.posix.join(path.posix.dirname(entry.source), decodeURIComponent(bare))
    );
  } catch {
    return href;
  }
  const mapped = bySource.get(resolved);
  if (mapped) return pageUrl(mapped) + suffix;
  // The public root status file is explicitly eligible as an external reference.
  // Do not admit arbitrary root files through the publication boundary.
  if (resolved !== "PROJECT_STATUS.md" &&
      !["docs/", "examples/", "src/", "tools/", "tests/"].some((p) => resolved.startsWith(p)))
    return "#unpublished-source";
  return "https://github.com/smartyhall/deskmate-formats/blob/main/" +
    encodeURI(resolved) + suffix;
}
function renderSource(entry) {
  const raw = fs.readFileSync(sourcePath(entry), "utf8");
  const tokens = md.parse(raw, {});
  const headingIds = new Map();
  let foundPageTitle = false;
  function walk(items) {
    for (let i = 0; i < items.length; i++) {
      const token = items[i];
      if (token.type === "heading_open" && items[i + 1]) {
        // Some archived laboratory reports contain multiple Markdown H1s.
        // Keep their wording/anchors, but expose a single page H1 to readers.
        if (token.tag === "h1") {
          if (foundPageTitle) {
            token.tag = "h2";
            const closing = items[i + 2];
            if (closing?.type === "heading_close" && closing.tag === "h1")
              closing.tag = "h2";
          } else {
            foundPageTitle = true;
          }
        }
        const heading = items[i + 1].content;
        const base = heading.toLowerCase().replace(/[^a-z0-9 -]/g, "")
          .trim().replace(/\s+/g, "-") || "section";
        const count = headingIds.get(base) || 0;
        headingIds.set(base, count + 1);
        token.attrSet("id", count ? base + "-" + count : base);
      }
      if (token.type === "link_open") {
        const idx = token.attrIndex("href");
        if (idx >= 0) token.attrs[idx][1] = resolveLink(token.attrs[idx][1], entry);
      }
      if (token.type === "image") {
        token.type = "text";
        token.tag = "";
        token.attrs = null;
        token.children = null;
        token.content = "[Image withheld pending publication review]";
      }
      if (token.children) walk(token.children);
    }
  }
  walk(tokens);
  injectFigures(tokens, entry.id, readFigures(), siteUrl);
  return md.renderer.render(tokens, md.options, {});
}
function searchRecord(entry) {
  const raw = fs.readFileSync(sourcePath(entry), "utf8");
  return {
    id: entry.id, title: entry.title, role: entry.role,
    section: entry.section, url: pageUrl(entry),
    text: raw.replace(/\x60\x60\x60[\s\S]*?\x60\x60\x60/g, " ")
      .replace(/!\[[^\]]*\]\([^)]+\)/g, " ")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/[#>*_\x60|]/g, " ").replace(/\s+/g, " ").trim().slice(0, 15000),
  };
}
module.exports = { ROOT, pages, sections, siteUrl, pageUrl, resolveLink, renderSource, searchRecord };
