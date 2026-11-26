"use strict";
const fs = require("node:fs");
const path = require("node:path");
const MarkdownIt = require("markdown-it");
const { readFigures, injectFigures } = require("./figures.cjs");
const ROOT = path.resolve(__dirname, "../..");
const map = JSON.parse(
  fs.readFileSync(path.join(ROOT, "docs/site/page-map.json"), "utf8")
);
if (map.schema_version !== 2) {
  throw new Error(
    "The renderer requires page-map schema_version 2; found " + map.schema_version
  );
}
const pages = Object.freeze(map.pages);
const byId = new Map(pages.map((page) => [page.id, page]));
const bySource = new Map(pages.map((page) => [page.source, page]));
/** Reader-question sections, in reading order. Membership is independent of slug. */
const SECTION_IDS = Object.freeze([
  "deskmate", "formats", "recovery", "research", "project",
]);
const SECTION_LABELS = Object.freeze({
  deskmate: "DeskMate",
  formats: "File formats",
  recovery: "Recovery",
  research: "Research",
  project: "Project",
});
const ROLE_LABELS = Object.freeze({
  "current-guide": "Maintained guide",
  "manufacturer-reference": "Manufacturer reference",
  "dated-research": "Dated experiment report",
  "dated-snapshot": "Dated snapshot",
  "site-plan": "Project planning document",
});

function compareEntries(left, right) {
  return left.order - right.order || left.id.localeCompare(right.id);
}

const sections = Object.freeze(SECTION_IDS.map((id) => {
  const sectionPages = pages.filter((page) => page.section === id).sort(compareEntries);
  const hub = sectionPages.find((page) => page.is_hub);
  if (!hub) throw new Error("Navigation section without a hub: " + id);
  const titles = [];
  for (const page of sectionPages) {
    if (!page.is_hub && !titles.includes(page.subsection)) titles.push(page.subsection);
  }
  return {
    id,
    title: hub.title,
    shortTitle: SECTION_LABELS[id] || hub.title,
    hub,
    pages: sectionPages,
    subsections: titles.map((title) => ({
      title,
      pages: sectionPages.filter((page) => !page.is_hub && page.subsection === title),
    })),
  };
}));

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
        if (idx >= 0) {
          const href = resolveLink(token.attrs[idx][1], entry);
          if (href === "#unpublished-source") {
            // A link to something the site does not publish is not a link: keep
            // the wording, drop the anchor rather than emit a dead fragment.
            for (let j = i + 1; j < items.length; j++) {
              if (items[j].type === "link_close") {
                items[j].type = "text";
                items[j].tag = "";
                items[j].attrs = null;
                items[j].content = "";
                break;
              }
            }
            token.type = "text";
            token.tag = "";
            token.attrs = null;
            token.content = "";
          } else {
            token.attrs[idx][1] = href;
          }
        }
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
  const figures = readFigures();
  if (entry.id === "history.introduction") {
    // Reuse verified Collection 01 captures in the orientation article without
    // duplicating binary files or altering their original evidence placements.
    const guided = [
      ["ui.desktop.launcher", "A desktop instead of a command prompt"],
      ["ui.desktop.desktop-menu", "A desktop instead of a command prompt"],
      ["ui.calendar.day-view", "What could you do with it?"],
      ["ui.express-publisher.workspace", "Beyond the bundled suite"],
    ];
    for (const [id, heading] of guided) {
      const asset = figures.find((figure) => figure.id === id);
      if (!asset) throw new Error("Missing approved introduction figure: " + id);
      figures.push({ ...asset, page_id: entry.id, section_heading: heading });
    }
  }
  injectFigures(tokens, entry.id, figures, siteUrl);
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
/** Readable role label; hubs are navigation, not evidence, so they carry none. */
function roleLabel(entry) {
  if (entry.is_hub) return null;
  return ROLE_LABELS[entry.role] || entry.role;
}
function sectionFor(entry) {
  return sections.find((section) => section.id === entry.section) || null;
}
function breadcrumbsFor(entry) {
  const section = sectionFor(entry);
  if (!section) return null;
  const trail = [{ label: "Home", href: siteUrl("/") },
    { label: section.shortTitle, href: pageUrl(section.hub) }];
  if (!entry.is_hub) {
    if (entry.subsection) trail.push({ label: entry.subsection });
    trail.push({ label: entry.title });
  } else {
    trail[1] = { label: section.shortTitle };
  }
  return trail;
}
module.exports = {
  ROOT, pages, byId, sections, SECTION_IDS, SECTION_LABELS, ROLE_LABELS,
  siteUrl, pageUrl, resolveLink, renderSource, searchRecord,
  roleLabel, sectionFor, breadcrumbsFor,
};
