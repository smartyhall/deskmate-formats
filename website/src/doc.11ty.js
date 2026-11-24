"use strict";
const { renderSource, topicFor, readingStep } = require("../lib/reference.cjs");
module.exports = class Document {
  data() {
    return {
      pagination: { data: "referencePages", size: 1, alias: "entry" },
      permalink: (data) => data.entry.slug + "/index.html",
      layout: "base.njk",
      eleventyComputed: {
        title: (data) => data.entry.title,
        currentId: (data) => data.entry.id,
        currentTopic: (data) => topicFor(data.entry),
        reading: (data) => readingStep(data.entry),
        sourceRole: (data) => readingStep(data.entry) ? null : data.entry.role,
        sourceLink: (data) =>
          "https://github.com/smartyhall/deskmate-formats/blob/main/" + data.entry.source,
      },
    };
  }
  render(data) {
    return renderSource(data.entry);
  }
};
