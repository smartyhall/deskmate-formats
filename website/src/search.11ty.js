"use strict";
const { siteUrl, sections, SITE_ORIGIN } = require("../lib/reference.cjs");
function escape(value) {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
module.exports = class Search {
  data() {
    return { permalink: "search/index.html", layout: "base.njk", title: "Search",
      currentId: "search", canonicalUrl: SITE_ORIGIN + "/search/" };
  }
  render() {
    // The index is fetched in the browser, so without JavaScript the page has to
    // offer the section hubs itself rather than a form that cannot answer.
    const links = sections.map((section) =>
      '<li><a href="' + siteUrl("/" + section.hub.slug + "/") + '">' +
      escape(section.shortTitle) + "</a></li>").join("");
    return '<h1>Search the reference</h1>' +
      '<p>Local browser search across the reviewed page map. No account or external service is required.</p>' +
      '<noscript><p>Search runs in your browser and needs JavaScript. Every section is still ' +
      'readable without it:</p><ul>' + links + '</ul></noscript>' +
      '<form id="reference-search" role="search" data-index="' + siteUrl("/search-index.json") + '">' +
      '<label for="search-query">Keywords</label>' +
      '<input class="form-control" id="search-query" type="search" autocomplete="off" placeholder="e.g. DMDB, Calendar, graphics">' +
      '<button class="btn btn-primary" type="submit">Search</button></form>' +
      '<p id="search-status" role="status" aria-live="polite">Enter a term to search.</p>' +
      '<ol id="search-results"></ol><script defer src="' +
      siteUrl("/assets/search.js") + '"></script>';
  }
};
