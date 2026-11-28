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
function historicalImage() {
  return {
    id: "history.hx-1988-offer",
    page_id: "history.chronology",
    section_heading: "The 1988 HX catalog offer",
    path: "calendar.png",
    width: 742, height: 745,
    origin: "historical-advertising-excerpt",
    source_url: "https://example.org/catalog.pdf#page=9",
    publisher: "Tandy Corporation / Radio Shack",
    publication_title: "1988 Tandy Computer Catalog",
    publication_date: "1988",
    page_reference: "printed p. 9",
    provenance: "Synthetic test provenance",
    attribution: "Tandy Corporation, 1988 catalog, printed p. 9.",
    alt: 'Catalog listing with a "$699" price <test>',
    caption: "The catalog advertised the 1000 HX with Personal DeskMate 2 included.",
    rights_note: "Third-party historical advertising; publisher rights retained.",
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

test("the Fil2dbf evidence figure loads eagerly", () => {
  const figure = readFigures().find((item) => item.id === "ui.historical-utilities.fil2dbf-field-name");
  assert.ok(figure);
  assert.match(renderFigureSet([figure], (url) => url), /loading="eager"/);
});

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

test("historical advertising renders attribution, source link and rights note", () => withAsset((dir) => {
  const html = renderFigureSet([historicalImage()], (x) => x, dir);
  assert.match(html, /Tandy Corporation, 1988 catalog, printed p\. 9\./);
  assert.match(html, /aria-label="View full-size historical excerpt"/);
  assert.match(html, /class="reference-figure reference-figure-historical"/);
  assert.match(html, /href="https:\/\/example\.org\/catalog\.pdf#page=9"/);
  assert.match(html, /Source: Tandy Corporation \/ Radio Shack, 1988 Tandy Computer Catalog, printed p\. 9/);
  assert.match(html, /Third-party historical advertising; publisher rights retained\./);
  assert.match(html, /\$699&quot; price &lt;test&gt;/);
}));

test("incomplete or misclassified historical advertising is rejected", () => withAsset((dir) => {
  const missing = historicalImage();
  delete missing.publisher;
  assert.throws(() => renderFigureSet([missing], (x) => x, dir), /Invalid historical advertising entry/);
  assert.throws(() => renderFigureSet([{...historicalImage(), id: "ui.hx-1988-offer"}], (x) => x, dir),
    /Invalid historical advertising entry/);
  assert.throws(() => renderFigureSet([{...historicalImage(), origin: "documentary-software-ui-capture"}],
    (x) => x, dir), /Invalid documentary capture entry/);
}));

test("unlisted path traversal and missing files do not render", () => withAsset((dir) => {
  assert.throws(() => renderFigureSet([{...oneImage(), path:"../escape.png"}], (x)=>x, dir));
}));
