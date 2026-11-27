# Campaign Python environments and proven execution identity

Campaign report, 2026-11-27. Addresses
[issue #201](https://github.com/smartyhall/deskmate-formats/issues/201), following
the subprocess finding in PR #199 and the installed wheel left in the shared
interpreter by PR #191. Related: issue #147 (host-contention baselines).

## Summary

Several campaigns share this Windows 10 laboratory VM. Each has a checkout and a
mutable Python environment, and every one of them can resolve
`deskmate_formats` through the **same globally installed wheel**: the
distribution in `…\Programs\Python\Python313\Lib\site-packages` is a build of
another branch (it contains `supervisor/procedures.py` and
`supervisor/campaigns.py` from PR #191). A child launched as
`[sys.executable, "-I", "-m", "deskmate_formats.…"]` therefore runs that wheel,
not the checkout named in the report, and `PYTHONPATH` cannot change the answer
because `-I` discards it.

This campaign adds a reusable mechanism rather than a document:

* `deskmate_formats.campaign_env` — inventory, campaign-owned environment,
  explicit-interpreter isolated launch, child probe, fail-closed preflight and
  durable receipts, with a redacted publication projection;
* `deskmate-campaign-env` — `inventory`, `provision`, `preflight`, `probe`,
  `identity` and `launch`;
* `tests/portable/test_campaign_env.py` — 29 portable tests, including a
  controlled two-checkout experiment;
* `tools/campaign_environment_experiment.py` — the laboratory experiment whose
  receipts this report quotes;
* [campaign environment procedure](campaign-environment-procedure.md) — the
  reusable procedure and the Codex/Freebuff migration guide.

**Measured result (one run, 108.6 s host wall):** a campaign environment's
isolated child imports the campaign's own installation (source code digest
identical to the checkout) even when `PYTHONPATH` names a conflicting
implementation; a preflight inside the campaign returns `qualified` with exit
status 0; a preflight from the shared interpreter, from a conflicting
`PYTHONPATH`, and from a checkout with unreadable Git metadata all return a
non-zero status and never `qualified`.

## Host inventory (measured, 2026-11-27)

Read-only, via `python -m deskmate_formats.campaign_env.cli inventory`.

| Quantity | Observed | Note |
| --- | --- | --- |
| Usable interpreters | **1** — CPython 3.13.17, `…\Programs\Python\Python313\python.exe` | reported `state: described` |
| Unusable candidate | `…\Microsoft\WindowsApps\python3.exe` | App Execution Alias; `unreadable`, child exit 9009 |
| Visible distributions | 49 | `deskmate-formats 0.1.0.dev0` present, plus `pip 26.2.2`, `ruff 0.17.3`, `reuse 6.3.0`, `build 1.6.1`, `jsonschema`, `mcp`, `anyio`, `pillow`, `fonttools` |
| `setuptools`, `wheel` | **absent** | an offline `pip --no-build-isolation` install cannot build this project here |
| Registered worktrees | **41** | from `git worktree list`; only paths are stored privately |
| Virtual environments before this campaign | **0** | a one-level scan first reported 0 *after* an environment existed, a scan defect fixed during the campaign |
| Virtual environments after the experiment | **3** | the campaign environment plus the two synthetic ones |

The single interpreter is the constraint that makes this campaign necessary:
"use a separate environment" cannot mean "use a different interpreter", so the
campaign environment must be a `venv` created and owned by the campaign.

## The defect as measured

`inventory` scans `src/`, `tools/` and `tests/` for a literal `-I` argument and
records the interpreter expression and target module in the same call. It is a
lexical audit: a site assembled from variables is reported as `unresolved`
rather than omitted, and text that merely looks like a launch is reported too.

| Quantity | Observed |
| --- | --- |
| `-I` occurrences found | 30 |
| Sites naming `sys.executable` | 14 |
| Sites whose interpreter expression could not be resolved statically | 16 |
| Distinct target modules | 9 |

Every supervisor module reached through `-I` resolved to the **shared
installation**, not to any checkout:

| Module launched under `-I` | Resolved origin (shared interpreter) |
| --- | --- |
| `deskmate_formats.supervisor.task_cli` | `…\Python313\Lib\site-packages\deskmate_formats\supervisor\task_cli.py` |
| `deskmate_formats.supervisor.bridge_cli` | `…\site-packages\deskmate_formats\supervisor\bridge_cli.py` |
| `deskmate_formats.supervisor.editing_cli` | `…\site-packages\deskmate_formats\supervisor\editing_cli.py` |
| `deskmate_formats.supervisor.driver_cli` | `…\site-packages\deskmate_formats\supervisor\driver_cli.py` |
| `deskmate_formats.supervisor.synthetic_peer` | `…\site-packages\deskmate_formats\supervisor\synthetic_peer.py` |

The launch sites themselves are not wrong about isolation — they use `-I`
deliberately — but they attribute the parent's interpreter to the child. In
`supervisor/workspace.py:172-192`, `command()` builds
`[sys.executable, *args]` and sets `PYTHONPATH` to the workspace `src`; the
`publication-audit` step is `["-I", "-c", AUDIT]`, so the `PYTHONPATH` is
discarded and the audit imports the shared wheel while the receipt records the
parent interpreter's digest. That is the #201 defect, still present on `main`,
and this campaign documents it rather than changing production Supervisor
behaviour without review.

## Controlled experiment

Two synthetic source checkouts were made from this repository's package tree,
each in its own Git repository with a different revision, a different
`pyproject.toml` version and an appended marker, plus a third marked copy
standing in for another campaign's installation.

| Campaign | Marker | Recorded revision | Recorded source tree digest |
| --- | --- | --- | --- |
| alpha | `alpha-checkout-2` | `1be19d3…` | `55a0bd13…` |
| beta | `beta-checkout-7` | `bcb4cfc…` | `9b218f2c…` |
| "shared" conflict | `shared-preinstalled-0` | (its own repository) | not provisioned |

Each campaign was provisioned with the shipped mechanism (a `venv` plus a real
`pip` install of its own checkout). The launch matrix, as measured:

| Probe | alpha | beta |
| --- | --- | --- |
| Isolated child, `PYTHONPATH` = shared conflict | `alpha-checkout-2` | `beta-checkout-7` |
| Isolated child, `PYTHONPATH` = the **other** checkout | `alpha-checkout-2` | `beta-checkout-7` |
| Unisolated control, `PYTHONPATH` = shared conflict | `shared-preinstalled-0` | `shared-preinstalled-0` |
| Parent process marker | `alpha-checkout-2` | `beta-checkout-7` |
| Parent's isolated child marker | `alpha-checkout-2` | `beta-checkout-7` |

The unisolated control is the important row: it shows the conflict is real, so
the isolated rows show that `-I` plus the campaign interpreter is what keeps the
child on its own code. Each isolated child also reported `isolated: true` and
`pythonpath_present: true` in the same receipt, and its origin was inside its own
campaign's `site-packages`. The bootstrap interpreter could not import the
synthetic campaign at all (`ModuleNotFoundError`), which is what "separate
environment" means rather than "a second copy that happens to work".

## Source drift and unreadable metadata

Both refusals were measured on a provisioned campaign environment:

| Condition | Verdict | Reasons | Exit |
| --- | --- | --- | --- |
| Source file edited, not committed | `unqualified` | `source-content` | 1 |
| Same edit committed | `unqualified` | `source-revision`, `source-content` | 1 |
| `.git` hidden from the checkout | `unknown` | `source-revision` | 2 |

With the metadata hidden, `source_identity` returned `state: not-a-repository`,
`failure: rev-parse-failed` and `revision: null`, the verdict was `unknown`, and
`measurement_allowed` was false. Restoring `.git` restored `state: git`. An
unreadable identity is never reported as a clean measurement.

## End-to-end qualification of this repository

| Preflight | Verdict | Reasons | Exit |
| --- | --- | --- | --- |
| Inside the campaign environment, clean environment | `qualified` | — (7 checks pass) | 0 |
| Campaign interpreter, `PYTHONPATH` = conflicting copy | `unqualified` | `parent-origin` | 1 |
| Shared interpreter | `unqualified` | `interpreter` | 1 |

The eight checks are `environment-record`, `interpreter`, `parent-origin`,
`source-revision`, `source-content`, `observed-origin`, `observed-content` and
`child-isolation`; all eight passed inside the campaign environment. Observed
content matched the provisioning receipt exactly: `python_digest` and bundle
digest identical for source and install.

One rule changed because of a measurement: `parent-origin` compares **code
content**, not only location. A parent running with `PYTHONPATH` pointing at the
same checkout is running the campaign's bytes and is accepted; a parent
importing the shared wheel is refused even when its interpreter is right.

## Limitations

* **Not an OS sandbox.** The campaign environment is a `venv` owned by the
  campaign, on the same account and filesystem. It changes which code a process
  imports; it does not confine what it can touch. The laboratory posture of
  2026-11-11 still governs risk.
* **Point-in-time proof.** A preflight describes the parent, the child and the
  checkout when it runs. A long campaign must re-run it at its checkpoint; it
  cannot prove what an earlier step executed.
* **Build backend availability.** `setuptools` and `wheel` are absent from the
  shared interpreter, so the first provision falls back to build isolation,
  which needs network for the declared backend. The measured cost of one real
  provision on this host was 25.4 s cold; the mechanism records which mode was
  used (`install_mode`) instead of hiding the difference. A shared tools
  environment makes this offline; see the procedure.
* **`pip --target` installation.** The environment is created without
  `ensurepip` and populated through the bootstrap interpreter's `pip`. That is
  fast and deterministic but does not create console scripts inside the
  environment; children are launched with `-I -m module`, which the campaign
  probe and the Supervisor already do.
* **Lexical launch-site audit.** It reports what the source text says. Docstring
  text and test fixtures can appear as sites, and a computed interpreter
  expression is `unresolved` rather than guessed.
* **Single host, single run.** Timings come from one loaded shared VM
  (`41` worktrees, other campaigns active). No claim is made about a quiet-host
  baseline; that belongs to issue #147.
* **Linux coverage comes from CI.** The portable tests run on Windows and
  Ubuntu, Python 3.13 and 3.14, but the laboratory experiment above was executed
  only on the Windows guest.
* **`local-results` inheritance.** A synthetic checkout created inside a Git
  checkout inherits the enclosing repository's `HEAD`; that was found here and
  is why each synthetic checkout gets its own repository. Any campaign that
  copies a tree into a worktree should expect the same.

## Integration recommendations

Reuse, not a parallel system:

1. **PR #199 `perf` harness.** Its `sanitize.public_projection`/`redact_text` and
   its `meta.package` / `meta.source_before` / `meta.source_after` fields already
   carry the same facts this module records. The receipts here are shaped to drop
   in: `parent.package.{origin, tree_digest, python_digest, distribution_version}`
   and `source.{revision, branch, dirty, state, failure}`. Recommended: run
   `campaign_env.preflight` before a timed suite and embed
   `{"verdict", "reasons"}` in `meta`, so a report cannot be published as a
   measurement of this checkout while its children ran another.
2. **PR #191 `procedures.py`.** Procedure `argv()` already takes the interpreter
   as a parameter and `_interpreter()` resolves the running one. Binding that
   interpreter to the campaign environment record is a small, reviewable change
   and makes the deterministic backend's children attributable.
3. **PR #191 `workspace.py`.** `command()` should pass the campaign interpreter
   rather than `sys.executable`, or run its `-I` steps with the environment's
   interpreter explicitly. Until then its `publication-audit` receipt attributes
   a shared-wheel run to the task's checkout.
4. **PR #191 `campaigns.py`.** A lease could record the environment digest it was
   granted under; a lease with a stale environment would then be refused instead
   of silently granted.
5. **Observatory projection.** `observer/campaigns.py` already separates measured
   from unknown state; an `environment_verdict` field would let the read-only
   campaign page show "unqualified identity" without any new authority.
6. **Project separation roadmap.** `campaign_env` uses only the standard library
   and takes the package name as a parameter, so it can move to the standalone
   automation/observer tooling without this repository's package.
7. **Issue #147.** A future quiet-host baseline should record the preflight
   receipt alongside the timing receipt; a run whose identity is unqualified
   should not enter a performance comparison at all.

## Reproduction

```powershell
# from the campaign checkout
$env:PYTHONPATH = 'src'
python -m deskmate_formats.campaign_env.cli inventory --out local-results/inventory.json
python tools/campaign_environment_experiment.py --output local-results/experiment-20261127
```

The experiment writes `01-inventory.json`, `02-isolation.json`,
`03-qualification.json`, `04-summary.json`, `05-drift.json`,
`06-metadata-failure.json`, `07-inventory-after.json` and a redacted
`public-summary.json` under `local-results/` (Git-ignored). Only the redacted
projection is published, as
[`docs/evidence/campaign-python-environment-20261127.json`](../evidence/campaign-python-environment-20261127.json).

## Evidence and provenance

* [Redacted experiment receipt](../evidence/campaign-python-environment-20261127.json) —
  inventory counts, launch-site audit, launch matrix, drift, metadata failure and
  the three qualification verdicts.
* Private raw receipts (absolute paths, pip logs) remain under the campaign
  checkout's `local-results/experiment-20261127/`, outside Git.
* Method: `tools/campaign_environment_experiment.py` on 2026-11-27, one run,
  CPython 3.13.17 on the Windows 10 laboratory guest; no emulator, model turn or
  unattended dispatch.

**Visual exemplars: not applicable.** The entire result set is terminal output
and JSON receipts; there is no meaningful visual state in this work, and no
image was fabricated to satisfy the guideline.
