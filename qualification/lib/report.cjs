"use strict";
/** Review presentations for qualification results: contact sheet and summary. */
const fs = require("node:fs");
const path = require("node:path");

function escape(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
}

/** Group renderings by engine and profile so a reviewer compares like with like. */
function groupResults(results) {
  const groups = new Map();
  for (const result of results) {
    const key = `${result.engine} · ${result.profile}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(result);
  }
  return groups;
}

function contactSheet(results, summary) {
  const sections = [];
  for (const [key, group] of groupResults(results)) {
    const cards = group.map((result) => {
      const state = result.problems.length ? "fail" : result.checks?.some((check) => check.inconclusive) ? "inconclusive" : "pass";
      const details = [
        `${result.observed?.width || "?"}x${result.observed?.height || "?"} @${result.observed?.devicePixelRatio || "?"}x`,
        `status ${result.status}`,
        result.screenshot ? `${Math.round(result.screenshot.bytes / 1024)} KB` : "no screenshot",
      ].join(" · ");
      const notes = [
        ...result.problems,
        ...(result.checks || []).filter((check) => check.inconclusive)
          .map((check) => `Inconclusive: ${check.name}: ${check.detail || "no further detail"}`),
      ];
      const findings = notes.length
        ? `<ul>${notes.map((note) => `<li>${escape(note)}</li>`).join("")}</ul>`
        : "";
      return `<figure class="${state}">
  ${result.screenshot ? `<a href="${escape(result.screenshot.file)}"><img src="${escape(result.screenshot.file)}" alt="${escape(result.page.route)} rendered in ${escape(result.engine)} at ${escape(result.profile)}"></a>` : "<p>No screenshot available</p>"}
  <figcaption><strong>${escape(result.page.route)} — ${escape(state === "fail" ? "Failed" : state === "inconclusive" ? "Inconclusive" : "Passed")}</strong><br>${escape(details)}${findings}</figcaption>
</figure>`;
    }).join("\n");
    sections.push(`<section><h2>${escape(key)}</h2><div class="grid">${cards}</div></section>`);
  }
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Qualification contact sheet</title>
<style>
body{font-family:system-ui,sans-serif;margin:2rem;background:#111;color:#eee}
h1{margin:0 0 .25rem}h2{margin:2rem 0 .75rem;font-size:1.05rem;color:#9cf}
.meta{color:#aaa;margin-bottom:1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem}
figure{margin:0;background:#1b1b1b;border:1px solid #333;border-radius:6px;overflow:hidden}
figure.fail{border-color:#a33}
figure.inconclusive{border-color:#bb8}
figure img{display:block;width:100%;height:auto;background:#fff}
figcaption{padding:.6rem;font-size:.8rem;color:#bbb}
figcaption ul{margin:.4rem 0 0;padding-left:1rem;color:#f88}
</style></head><body>
<h1>Qualification contact sheet</h1>
<p class="meta">${escape(summary.base)} · ${summary.totals.renderings} rendering(s) · ${summary.totals.passed} passed · ${summary.totals.failed} failed · ${summary.totals.inconclusive || 0} inconclusive · ${escape(summary.generated_at)}</p>
${sections.join("\n")}
</body></html>
`;
}

function markdownSummary(summary, results) {
  const lines = [
    `# Qualification summary`,
    ``,
    `- Base: ${summary.base}`,
    `- Generated: ${summary.generated_at}`,
    `- Renderings: ${summary.totals.renderings} (${summary.totals.passed} passed, ${summary.totals.failed} failed, ${summary.totals.inconclusive || 0} inconclusive)`,
    `- Requested renderings: ${summary.totals.requested ?? "unknown"}`,
    `- axe violations: ${summary.totals.axeViolations}`,
    ``,
    `| Engine | Version | Profile | Route | Viewport | Status | Result |`,
    `| --- | --- | --- | --- | --- | --- | --- |`,
  ];
  for (const result of results) {
    lines.push(`| ${result.engine} | ${result.engineVersion || "?"} | ${result.profile} | ${result.page.route} | ` +
      `${result.observed?.width || "?"}x${result.observed?.height || "?"} | ${result.status} | ` +
      `${result.problems.length ? `${result.problems.length} finding(s)` : result.checks?.some((check) => check.inconclusive) ? "inconclusive" : "pass"} |`);
  }
  for (const skip of summary.skipped) lines.push(``, `- Skipped ${skip.engine}: ${skip.reason}`);
  return lines.join("\n") + "\n";
}

function writeReports(options, { summary, results }) {
  fs.writeFileSync(path.join(options.out, "contact-sheet.html"), contactSheet(results, summary), "utf8");
  fs.writeFileSync(path.join(options.out, "summary.md"), markdownSummary(summary, results), "utf8");
}

module.exports = { contactSheet, markdownSummary, writeReports, groupResults, escape };
