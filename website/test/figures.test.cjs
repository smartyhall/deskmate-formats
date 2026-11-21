"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { readFigures, renderFigureSet, injectFigures } = require("../lib/figures.cjs");

function oneImage() {
  return {
    id: "ui.calendar.day-view",
    page_id: "formats.calendar",
    section_heading: "Evidence and provenance",
    path: "calendar.png",
    width: 640, height: 480,
    alt: 'Calendar with a yellow "selected" event <test>',
    caption: "Synthetic appointment and controls",
  };
}
function withAsset(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "deskmate-figures-"));
  fs.writeFileSync(path.join(dir, "calendar.png"), "test image stub");
  try { fn(dir); } finally { fs.rmSync(dir, {recursive: true, force: true}); }
}

test("manifest reader accepts absent or valid published image manifest", () => {
  assert.ok(Array.isArray(readFigures()));
});

test("figure renderer escapes alt/caption and honors hosting path", () => withAsset((dir) => {
  const image = oneImage();
  const html = renderFigureSet([image], (x) => "/deskmate-formats" + x, dir);
  assert.match(html, /src="\/deskmate-formats\/assets\/reference\/calendar.png"/);
  assert.match(html, /selected&quot; event &lt;test&gt;/);
  assert.match(html, /loading="lazy"/);
  assert.match(html, /width="640" height="480"/);
  assert.doesNotMatch(html, /<test>/);
}));

test("injection follows first explanatory paragraph at matching heading", () => withAsset((dir) => {
  const tokens = [
    {type: "heading_open"},
    {type: "inline", content: "Evidence and provenance"},
    {type: "heading_close"},
    {type: "paragraph_open"},
    {type: "inline", content: "Explains evidence."},
    {type: "paragraph_close"},
  ];
  injectFigures(tokens, "formats.calendar", [oneImage()], (x) => x, dir);
  assert.equal(tokens[6].type, "reference_figure_block");
  assert.match(tokens[6].content, /Synthetic appointment/);
  assert.equal(tokens.length, 7);
}));

test("missing/ambiguous placement is rejected instead of silently dropping images", () => withAsset((dir) => {
  assert.throws(() => injectFigures([], "formats.calendar", [oneImage()], (x) => x, dir),
    /section not found/);
  const tokens = [
    {type:"heading_open"}, {type:"inline", content:"Evidence and provenance"}, {type:"heading_close"},
    {type:"heading_open"}, {type:"inline", content:"Evidence and provenance"}, {type:"heading_close"}
  ];
  assert.throws(() => injectFigures(tokens, "formats.calendar", [oneImage()], (x) => x, dir),
    /Ambiguous/);
}));

test("unlisted path traversal and missing files do not render", () => withAsset((dir) => {
  assert.throws(() => renderFigureSet([{...oneImage(), path:"../escape.png"}], (x)=>x, dir));
}));
