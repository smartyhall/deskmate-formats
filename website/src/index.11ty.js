"use strict";
const { sections, pageUrl, siteUrl } = require("../lib/reference.cjs");
function escapeText(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;");
}
module.exports = class Index {
  data() {
    return { permalink: "index.html", layout: "base.njk", title: "Reference home", currentId: "home" };
  }
  render() {
    const cards = sections.filter((section) => section.pages.length).map((section) => {
      const entries = section.pages.slice(0, 3).map((p) =>
        '<li><a href="' + pageUrl(p) + '">' + escapeText(p.title) + '</a></li>'
      ).join("");
      return '<section class="landing-card"><h2>' + escapeText(section.title) +
        '</h2><ul>' + entries + '</ul></section>';
    }).join("");
    return '<div class="welcome"><p class="eyebrow">Tandy DeskMate preservation reference</p>' +
      '<h1>Recovering the documents, formats and behavior of DeskMate</h1>' +
      '<p>Independent, evidence-bounded documentation of native file structures, ' +
      'original applications, recoverable data and unresolved questions.</p>' +
      '<p>This is an early reference preview, not an official Tandy publication. ' +
      'Dated experiments are preserved separately from maintained capabilities.</p>' +
      '<p><a class="btn btn-primary" href="' + siteUrl("/search/") +
      '">Search the reference</a></p></div><div class="landing-grid">' +
      cards + '</div>';
  }
};
