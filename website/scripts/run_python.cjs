"use strict";
/**
 * Select a working Python 3 interpreter and forward the command.
 *
 * The website build scripts must work on Windows and Linux. `python3` is not
 * always present (Windows ships `py`/`python`), and on Windows it can resolve
 * to the Microsoft Store alias, which is a stub that fails on execution.
 * Probe candidates instead of guessing, and allow PYTHON to override.
 *
 * SPDX-FileCopyrightText: Copyright (c) 2026 Michael A. Hall
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
const { spawnSync } = require("node:child_process");

const PROBE = "import sys; print(sys.version_info[0])";

function candidates(env = process.env, platform = process.platform) {
  const list = [];
  if (env.PYTHON) list.push({ command: env.PYTHON, prefix: [] });
  if (platform === "win32") {
    list.push({ command: "py", prefix: ["-3"] });
    list.push({ command: "python", prefix: [] });
    list.push({ command: "python3", prefix: [] });
  } else {
    list.push({ command: "python3", prefix: [] });
    list.push({ command: "python", prefix: [] });
  }
  return list;
}

function resolvePython(options = {}) {
  const env = options.env || process.env;
  const platform = options.platform || process.platform;
  const run = options.run || ((command, args) => spawnSync(command, args, { encoding: "utf8" }));
  const attempts = [];
  for (const candidate of candidates(env, platform)) {
    const probe = run(candidate.command, [...candidate.prefix, "-c", PROBE]);
    const output = (probe.stdout || "").trim();
    if (!probe.error && probe.status === 0 && output === "3") {
      return { ...candidate, attempts };
    }
    attempts.push(candidate.command);
  }
  return { command: null, prefix: [], attempts };
}

function main(argv) {
  if (!argv.length) {
    console.error("Usage: node scripts/run_python.cjs SCRIPT [ARGS...]");
    return 2;
  }
  const resolved = resolvePython();
  if (!resolved.command) {
    console.error(
      "No working Python 3 interpreter found (tried: " +
      (resolved.attempts.join(", ") || "none") + "). Set PYTHON to its path."
    );
    return 1;
  }
  const result = spawnSync(
    resolved.command,
    [...resolved.prefix, ...argv],
    { stdio: "inherit" }
  );
  if (result.error) {
    console.error("Unable to run " + resolved.command + ": " + result.error.message);
    return 1;
  }
  return result.status === null ? 1 : result.status;
}

module.exports = { candidates, resolvePython, main };

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}
