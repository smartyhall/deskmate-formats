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
const MONTHS = Object.freeze([
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]);

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
// The published site is root-mounted on its own domain, so canonical URLs are
// independent of the base path used by a preview build.
const SITE_ORIGIN = "https://deskmate.retroconnect.org";
function canonicalFor(entry) {
  return SITE_ORIGIN + (entry ? "/" + entry.slug + "/" : "/");
}
function sourcePath(entry) {
  const absolute = path.resolve(ROOT, entry.source);
  if (!absolute.startsWith(ROOT + path.sep) || !absolute.endsWith(".md"))
    throw new Error("Unapproved document source: " + entry.source);
  return absolute;
}
/** Report dates are recorded only when a source states one; never inferred. */
function formatDate(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(typeof iso === "string" ? iso : "");
  if (!match) return null;
  const month = MONTHS[Number(match[2]) - 1];
  return month ? month + " " + Number(match[3]) + ", " + match[1] : null;
}
const existingPaths = new Map();
/**
 * Whether a repository-relative destination actually exists.
 * Directory names are compared exactly: Windows resolves case-insensitively but
 * GitHub and the Linux build do not, so a link that only works on the author's
 * machine is still a broken link.
 */
function sourceExists(relative) {
  const trimmed = relative.replace(/\/+$/, "");
  if (!trimmed || trimmed === "." || trimmed.startsWith("../")) return false;
  const cached = existingPaths.get(trimmed);
  if (cached !== undefined) return cached;
  let current = ROOT;
  let found = true;
  for (const segment of trimmed.split("/")) {
    let entries;
    try {
      entries = fs.readdirSync(current);
    } catch {
      found = false;
      break;
    }
    if (!entries.includes(segment)) {
      found = false;
      break;
    }
    current = path.join(current, segment);
  }
  if (found) found = fs.existsSync(current);
  existingPaths.set(trimmed, found);
  return found;
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
  // A relative link has to point at something. Falling back to a repository URL
  // for a destination that does not exist turns a typo into a broken external
  // link that no generated-site check can see, so refuse it at build time.
  if (!sourceExists(resolved))
    throw new Error(
      "Broken relative link in " + entry.id + ": " + href +
      " resolves to " + resolved + ", which does not exist"
    );
  // The public root status file is explicitly eligible as an external reference.
  // Do not admit arbitrary root files through the publication boundary.
  if (resolved !== "PROJECT_STATUS.md" &&
      !["docs/", "examples/", "src/", "tools/", "tests/"].some((p) => resolved.startsWith(p)))
    return "#unpublished-source";
  return "https://github.com/smartyhall/deskmate-formats/blob/main/" +
    encodeURI(resolved) + suffix;
}
/**
 * A published fragment is a permanent link. When a heading's wording changes,
 * its former anchor is kept as an alias rather than dropped. Keys are page IDs;
 * each value maps the heading's current anchor to the previously published one.
 */
const LEGACY_ANCHORS = Object.freeze({
  "formats.corkboard": Object.freeze({
    "deskmate-note-pad-and-corkboard-measured-file-format-reference":
      "deskmate-note-pad-and-corkboard-read-only-file-format-reference",
  }),
});
function renderSource(entry) {
  const raw = fs.readFileSync(sourcePath(entry), "utf8");
  const tokens = md.parse(raw, {});
  const headingIds = new Map();
  const contents = [];
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
        // The alias sits inside the heading so the old fragment lands exactly
        // where the old heading did; one element cannot carry two IDs.
        const alias = (LEGACY_ANCHORS[entry.id] || {})[token.attrGet("id")];
        if (alias && Array.isArray(items[i + 1].children))
          items[i + 1].children.unshift({
            type: "html_inline", content: '<span id="' + alias + '"></span>',
          });
        // Long reports are read out of order; offer their section headings.
        if (token.tag === "h2")
          contents.push({ id: token.attrGet("id"), text: heading.replace(/[*_`]/g, "") });
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
  return contentsBlock(contents, entry) + md.renderer.render(tokens, md.options, {});
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
function escapeText(value) {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
/** A contents list is worth the space only when the page has real sections. */
function contentsBlock(contents, entry) {
  // Hubs are short and already ordered; a contents list would only repeat them.
  if (entry.is_hub || contents.length < 4) return "";
  const items = contents.map((item) =>
    '<li><a href="#' + escapeText(item.id) + '">' + escapeText(item.text) + "</a></li>");
  // A report with twenty sections would otherwise push its own first paragraph
  // off the screen, so the longer lists start collapsed.
  const open = contents.length <= 8 ? " open" : "";
  return '<details class="page-contents"' + open + '>' +
    "<summary>On this page</summary><ol>" + items.join("") + "</ol></details>";
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
  SITE_ORIGIN, canonicalFor, formatDate,
  siteUrl, pageUrl, resolveLink, renderSource, searchRecord,
  roleLabel, sectionFor, breadcrumbsFor,
};
