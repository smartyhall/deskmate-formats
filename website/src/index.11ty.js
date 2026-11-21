"use strict";
const { pages, pageUrl, siteUrl } = require("../lib/reference.cjs");
const { escapeHtml, readFigures } = require("../lib/figures.cjs");

function urlFor(id) {
  const entry = pages.find((item) => item.id === id);
  if (!entry) throw new Error("Home destination missing from page map: " + id);
  return pageUrl(entry);
}
function featuredDesktop() {
  const image = readFigures().find((item) => item.id === "ui.desktop.launcher");
  if (!image || image.width !== 640 || image.height !== 480)
    throw new Error("Approved DeskMate desktop capture is unavailable");
  const url = siteUrl("/assets/reference/" + image.path);
  return '<figure class="home-hero-image"><a href="' + escapeHtml(url) +
    '" aria-label="View full-size DeskMate 3.05 desktop screenshot">' +
    '<img src="' + escapeHtml(url) + '" alt="' + escapeHtml(image.alt) +
    '" width="640" height="480" decoding="async"></a>' +
    '<figcaption>Original DeskMate 3.05 desktop, captured in our research lab. ' +
    'Other versions looked different.</figcaption></figure>';
}
function pathCard(title, description, id, linkText) {
  return '<section class="home-path"><h3>' + escapeHtml(title) + '</h3>' +
    '<p>' + escapeHtml(description) + '</p><p><a href="' + urlFor(id) + '">' +
    escapeHtml(linkText) + '</a></p></section>';
}
module.exports = class Index {
  data() {
    return { permalink: "index.html", layout: "base.njk",
      title: "Discover Tandy DeskMate", currentId: "home" };
  }
  render() {
    const cards = [
      pathCard("Discover DeskMate",
        "A friendly history of the software, the original desktop and the applications people used.",
        "history.introduction", "Read the illustrated introduction"),
      pathCard("Explore the technical reference",
        "Native formats, original manufacturer documentation, verified behaviors and unresolved questions.",
        "system.manufacturer-crosswalk", "Explore the format crosswalk"),
      pathCard("Preserve and recover your files",
        "Practical recovery tools, supported exports, limitations and guidance for preserving originals.",
        "recovery.workbench", "Visit the Preservation Workbench"),
    ].join("");
    return '<section class="home-hero" aria-labelledby="home-title">' +
      '<div class="home-hero-copy">' +
      '<p class="eyebrow">Tandy DeskMate · History and preservation</p>' +
      '<h1 id="home-title">Meet the other desktop of the PC era.</h1>' +
      '<p>Before the graphical desktop became familiar, Tandy offered an ' +
      'approachable collection of programs for writing, planning, drawing ' +
      'and keeping records. Explore the original software, the documents ' +
      'its users created, and the work of recovering them today.</p>' +
      '<p><a class="btn btn-primary" href="' + urlFor("history.introduction") +
      '">Discover DeskMate</a> <a class="home-search-link" href="' +
      siteUrl("/search/") + '">Search the reference</a></p>' +
      '</div>' + featuredDesktop() + '</section>' +
      '<section class="home-paths" aria-labelledby="paths-heading">' +
      '<h2 id="paths-heading">Where would you like to begin?</h2>' +
      '<div class="home-path-grid">' + cards + '</div></section>' +
      '<section class="home-context" aria-labelledby="about-heading">' +
      '<h2 id="about-heading">Historical software. Independently tested evidence.</h2>' +
      '<p>Our illustrations depict original software, chiefly one controlled ' +
      'DeskMate 3.05 installation. We distinguish historical claims, manufacturer ' +
      'documentation and observed behavior. Recovery capabilities are explicitly ' +
      'bounded; one version is never assumed to represent every DeskMate release.</p>' +
      '<p>Continue with the <a href="' + urlFor("applications.inventory") +
      '">application inventory</a>, <a href="' + urlFor("applications.ecosystem") +
      '">wider software ecosystem</a> or <a href="' + urlFor("project.roadmap") +
      '">preservation roadmap</a>.</p></section>';
  }
};
