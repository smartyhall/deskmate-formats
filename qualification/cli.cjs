#!/usr/bin/env node
"use strict";
/**
 * Run cross-engine qualification and write review artifacts.
 *
 * Examples:
 *   node cli.cjs --serve-dir ../website/_site --axe
 *   node cli.cjs --base https://deskmate.retroconnect.org --engines chromium,firefox,webkit \
 *     --profiles desktop,mobile --pages /,/research/
 */
const path = require("node:path");
const { qualify, DEFAULT_TIMEOUT } = require("./lib/qualify.cjs");
const { writeReports } = require("./lib/report.cjs");
const { serve } = require("./lib/serve.cjs");
const { DEFAULT_ENGINES } = require("./lib/engines.cjs");
const { DEFAULT_PROFILES } = require("./lib/profiles.cjs");

function parseArgs(argv) {
  const options = {
    base: null,
    serveDir: null,
    pages: "all",
    pageMap: path.join(__dirname, "..", "docs", "site", "page-map.json"),
    engines: DEFAULT_ENGINES.join(","),
    profiles: DEFAULT_PROFILES.join(","),
    out: "local-results/qualification",
    axe: false,
    timeout: DEFAULT_TIMEOUT,
    allowFindings: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    const value = () => {
      const next = argv[++index];
      if (next === undefined) throw new Error(`${flag} needs a value`);
      return next;
    };
    if (flag === "--base") options.base = value();
    else if (flag === "--serve-dir") options.serveDir = value();
    else if (flag === "--pages") options.pages = value();
    else if (flag === "--page-map") options.pageMap = value();
    else if (flag === "--engines") options.engines = value();
    else if (flag === "--profiles") options.profiles = value();
    else if (flag === "--out") options.out = value();
    else if (flag === "--axe") options.axe = true;
    else if (flag === "--allow-findings") options.allowFindings = true;
    else if (flag === "--timeout") options.timeout = Number(value());
    else throw new Error(`Unknown argument: ${flag}`);
  }
  if (!options.base && !options.serveDir) {
    throw new Error("pass --base <url> or --serve-dir <built site>");
  }
  if (options.base && options.serveDir) throw new Error("pass only one of --base and --serve-dir");
  if (!Number.isFinite(options.timeout) || options.timeout <= 0) throw new Error("--timeout must be positive");
  return options;
}

async function main(argv) {
  const options = parseArgs(argv);
  let server = null;
  if (options.serveDir) {
    server = await serve(options.serveDir);
    options.base = server.url;
    console.log(`serving ${path.resolve(options.serveDir)} at ${server.url}`);
  }
  try {
    const report = await qualify(options);
    writeReports(options, report);
    console.log(`\n${report.summary.totals.passed}/${report.summary.totals.renderings} renderings passed`);
    if (report.summary.totals.axeViolations) {
      console.log(`axe reported ${report.summary.totals.axeViolations} violation type(s)`);
    }
    console.log(`artifacts: ${path.resolve(options.out)}`);
    if (report.summary.totals.failed && !options.allowFindings) return 1;
    return 0;
  } finally {
    if (server) await server.close();
  }
}

if (require.main === module) {
  main(process.argv.slice(2)).then(
    (status) => process.exit(status),
    (error) => {
      console.error(error.message);
      process.exit(2);
    },
  );
}

module.exports = { parseArgs, main };
