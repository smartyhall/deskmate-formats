"use strict";
const { siteUrl } = require("./lib/reference.cjs");
module.exports = function (eleventyConfig) {
  eleventyConfig.addFilter("siteurl", siteUrl);
  // Copy only explicitly authored assets: never copy private screenshot roots.
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  return {
    dir: { input: "src", includes: "_includes", data: "_data", output: "_site" },
    templateFormats: ["njk", "11ty.js"],
    htmlTemplateEngine: "njk",
  };
};
