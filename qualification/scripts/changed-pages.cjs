#!/usr/bin/env node
"use strict";
/**
 * Print the routes whose source documents changed, for focused qualification.
 *
 * Falls back to the five hubs and the home page when nothing maps, so a run
 * always exercises the site's primary navigation.
 */
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

function changedFiles(base, cwd) {
  const args = base ? ["diff", "--name-only", `${base}...HEAD`] : ["diff", "--name-only", "HEAD~1"];
  return execFileSync("git", args, { cwd, encoding: "utf8" }).split("\n").filter(Boolean);
}

function routesFor(files, map) {
  const routes = new Set();
  for (const entry of map.pages) {
    if (files.includes(entry.source)) routes.add(`/${entry.slug}/`);
  }
  if (files.some((file) => file.startsWith("website/src/") || file.startsWith("website/lib/"))) {
    // Template or stylesheet changes affect every page; select the hubs.
    for (const entry of map.pages.filter((page) => page.is_hub)) routes.add(`/${entry.slug}/`);
  }
  return [...routes].sort();
}

function main(argv) {
  const cwd = path.resolve(__dirname, "..", "..");
  const mapPath = path.join(cwd, "docs", "site", "page-map.json");
  const map = JSON.parse(fs.readFileSync(mapPath, "utf8"));
  const files = changedFiles(argv[0], cwd);
  let routes = routesFor(files, map);
  if (!routes.length) {
    routes = ["/"].concat(map.pages.filter((page) => page.is_hub).map((page) => `/${page.slug}/`));
  }
  process.stdout.write(routes.join(","));
}

if (require.main === module) main(process.argv.slice(2));

module.exports = { routesFor, changedFiles };
