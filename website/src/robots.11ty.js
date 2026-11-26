"use strict";
const { SITE_ORIGIN } = require("../lib/reference.cjs");
module.exports = class Robots {
  data() {
    return { permalink: "robots.txt", eleventyExcludeFromCollections: true };
  }
  render() {
    return "User-agent: *\nAllow: /\n\nSitemap: " + SITE_ORIGIN + "/sitemap.xml\n";
  }
};
