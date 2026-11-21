"use strict";
const { siteUrl } = require("./lib/reference.cjs");
module.exports = function (eleventyConfig) {
  eleventyConfig.addFilter("siteurl", siteUrl);
  // The pinned theme is intentionally Git-ignored, but must be copied into the output.
  // All source templates are restricted to src/ and only explicit assets pass through.
  eleventyConfig.setUseGitIgnore(false);
  // Copy only explicitly authored assets: never copy private screenshot roots.
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  return {
    dir: { input: "src", includes: "_includes", data: "_data", output: "_site" },
    templateFormats: ["njk", "11ty.js"],
    htmlTemplateEngine: "njk",
  };
};
