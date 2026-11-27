"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const { candidates, resolvePython } = require("../scripts/run_python.cjs");

function fakeRun(table) {
  return (command, args) => {
    // The probe program itself is irrelevant; key on the interpreter invocation.
    const prefix = args.slice(0, -2).join(" ");
    const key = prefix ? command + " " + prefix : command;
    const reply = table[key];
    if (reply === undefined) return { error: new Error("not found"), status: null, stdout: "" };
    return { error: null, status: reply.status, stdout: reply.stdout };
  };
}

test("honors an explicit PYTHON override before probing names", () => {
  const list = candidates({ PYTHON: "/opt/py/bin/python3" }, "linux");
  assert.deepEqual(list[0], { command: "/opt/py/bin/python3", prefix: [] });
});

test("prefers the Windows py launcher, then python, then python3", () => {
  assert.deepEqual(
    candidates({}, "win32").map((item) => item.command),
    ["py", "python", "python3"]
  );
  assert.deepEqual(
    candidates({}, "linux").map((item) => item.command),
    ["python3", "python"]
  );
});

test("uses the py launcher with -3 on Windows", () => {
  const resolved = resolvePython({
    env: {},
    platform: "win32",
    run: fakeRun({ "py -3": { status: 0, stdout: "3\n" } }),
  });
  assert.equal(resolved.command, "py");
  assert.deepEqual(resolved.prefix, ["-3"]);
});

test("skips interpreters that fail the probe, including Store stubs", () => {
  const resolved = resolvePython({
    env: {},
    platform: "win32",
    run: fakeRun({
      "py -3": { status: 1, stdout: "" },
      python: { status: 9009, stdout: "" },
      python3: { status: 0, stdout: "3\n" },
    }),
  });
  assert.equal(resolved.command, "python3");
  assert.deepEqual(resolved.attempts, ["py", "python"]);
});

test("rejects Python 2 and reports attempts when nothing works", () => {
  const resolved = resolvePython({
    env: {},
    platform: "linux",
    run: fakeRun({
      python3: { status: 0, stdout: "2\n" },
      python: { status: 0, stdout: "2\n" },
    }),
  });
  assert.equal(resolved.command, null);
  assert.deepEqual(resolved.attempts, ["python3", "python"]);
});
