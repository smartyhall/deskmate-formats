"use strict";
const { pages, SITE_ORIGIN } = require("../lib/reference.cjs");

// Absolute URLs on the published origin, so a preview build cannot advertise
// itself in place of the site readers are sent to.
function loc(path) {
  return SITE_ORIGIN + path;
}
module.exports = class Sitemap {
  data() {
    return { permalink: "sitemap.xml", eleventyExcludeFromCollections: true };
  }
  render() {
    const paths = ["/", "/search/"].concat(pages.map((page) => "/" + page.slug + "/"));
    const entries = paths.map((path) => "  <url><loc>" + loc(path) + "</loc></url>");
    return '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
      entries.join("\n") + "\n</urlset>\n";
  }
};
