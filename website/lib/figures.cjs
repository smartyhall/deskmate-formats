"use strict";
// Website-only illustrated-reference adapter. Historical Markdown remains canonical.
const fs = require("node:fs");
const path = require("node:path");
const manifestPath = path.join(__dirname, "..", "reference-images.json");
const assetRoot = path.join(__dirname, "..", "src", "assets", "reference");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}
function readFigures() {
  if (!fs.existsSync(manifestPath)) return [];
  const document = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  if (document.schema_version !== 1 || !Array.isArray(document.images))
    throw new Error("Invalid reference image manifest");
  return document.images.filter((image) => image.page_id && image.section_heading);
}
function renderFigureSet(items, siteUrl) {
  const figures = items.map((item) => {
    if (!/^[a-z0-9][a-z0-9_.\/-]*\.png$/.test(item.path) ||
        item.path.split("/").includes("..") ||
        !Number.isInteger(item.width) || !Number.isInteger(item.height) ||
        item.width <= 0 || item.height <= 0 ||
        typeof item.alt !== "string" || !item.alt.trim() ||
        typeof item.caption !== "string" || !item.caption.trim())
      throw new Error("Invalid illustrated-reference entry " + item.id);
    const filename = path.join(assetRoot, item.path);
    if (!fs.existsSync(filename))
      throw new Error("Missing approved illustrated-reference PNG " + item.path);
    const url = siteUrl("/assets/reference/" + item.path);
    return '<figure class="reference-figure">' +
      '<a href="' + escapeHtml(url) + '" aria-label="View full-size screenshot">' +
      '<img src="' + escapeHtml(url) + '" alt="' + escapeHtml(item.alt) +
      '" width="' + item.width + '" height="' + item.height +
      '" loading="lazy" decoding="async"></a>' +
      '<figcaption>' + escapeHtml(item.caption) +
      ' <small class="reference-figure-credit">Documentary capture of original software; ' +
      'publisher interface rights retained.</small></figcaption></figure>';
  }).join("");
  return '<div class="reference-figures" aria-label="Illustrated interface evidence">' +
    figures + '</div>';
}
function injectFigures(tokens, pageId, items, siteUrl) {
  const groups = new Map();
  for (const item of items) {
    if (item.page_id !== pageId) continue;
    const name = item.section_heading;
    if (!name || typeof name !== "string")
      throw new Error("Missing screenshot section heading: " + item.id);
    if (!groups.has(name)) groups.set(name, []);
    groups.get(name).push(item);
  }
  const seen = new Set();
  for (let index = 0; index < tokens.length - 2; index++) {
    if (tokens[index].type !== "heading_open" ||
        tokens[index + 1].type !== "inline" ||
        tokens[index + 2].type !== "heading_close")
      continue;
    const heading = tokens[index + 1].content.trim();
    if (!groups.has(heading)) continue;
    if (seen.has(heading)) throw new Error("Ambiguous illustrated-reference heading: " + heading);
    seen.add(heading);
    let insertAt = index + 3;
    // Keep the explanatory paragraph before a figure group when available.
    if (tokens[insertAt]?.type === "paragraph_open") {
      const closing = tokens.findIndex((t, j) => j > insertAt && t.type === "paragraph_close");
      if (closing >= 0) insertAt = closing + 1;
    }
    const block = {
      type: "reference_figure_block", tag: "", nesting: 0,
      block: true, hidden: false, content: renderFigureSet(groups.get(heading), siteUrl)
    };
    tokens.splice(insertAt, 0, block);
    index = insertAt;
  }
  for (const heading of groups.keys()) {
    if (!seen.has(heading)) throw new Error(
      "Approved screenshot section not found for " + pageId + ": " + heading
    );
  }
}
module.exports = { escapeHtml, readFigures, renderFigureSet, injectFigures };
