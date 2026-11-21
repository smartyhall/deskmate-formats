"use strict";
const { pages, searchRecord } = require("../lib/reference.cjs");
module.exports = class SearchIndex {
  data() {
    return { permalink: "search-index.json", eleventyExcludeFromCollections: true };
  }
  render() {
    return JSON.stringify({ schema_version: 1, documents: pages.map(searchRecord) });
  }
};
