"use strict";
const { siteUrl, SITE_ORIGIN } = require("../lib/reference.cjs");
module.exports = class Search {
  data() {
    return { permalink: "search/index.html", layout: "base.njk", title: "Search",
      currentId: "search", canonicalUrl: SITE_ORIGIN + "/search/" };
  }
  render() {
    return '<h1>Search the reference</h1>' +
      '<p>Local browser search across the reviewed page map. No account or external service is required.</p>' +
      '<form id="reference-search" role="search" data-index="' + siteUrl("/search-index.json") + '">' +
      '<label for="search-query">Keywords</label>' +
      '<input class="form-control" id="search-query" type="search" autocomplete="off" placeholder="e.g. DMDB, Calendar, graphics">' +
      '<button class="btn btn-primary" type="submit">Search</button></form>' +
      '<p id="search-status" role="status" aria-live="polite">Enter a term to search.</p>' +
      '<ol id="search-results"></ol><script defer src="' +
      siteUrl("/assets/search.js") + '"></script>';
  }
};
