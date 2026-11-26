"use strict";
const {
  renderSource, pageUrl, roleLabel, sectionFor, breadcrumbsFor,
} = require("../lib/reference.cjs");
module.exports = class Document {
  data() {
    return {
      pagination: { data: "referencePages", size: 1, alias: "entry" },
      permalink: (data) => data.entry.slug + "/index.html",
      layout: "base.njk",
      eleventyComputed: {
        title: (data) => data.entry.title,
        summary: (data) => data.entry.summary,
        currentId: (data) => data.entry.id,
        currentSection: (data) => sectionFor(data.entry),
        // Hubs are navigation; the illustrated introduction is an article, not
        // a reference document, so neither carries an evidence-role badge.
        sourceRoleLabel: (data) => data.entry.id === "history.introduction"
          ? null
          : roleLabel(data.entry),
        breadcrumbs: (data) => breadcrumbsFor(data.entry),
        sourceLink: (data) =>
          "https://github.com/smartyhall/deskmate-formats/blob/main/" + data.entry.source,
      },
    };
  }
  render(data) {
    return renderSource(data.entry);
  }
};
