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
* `tests/portable/test_campaign_env.py` — 60 portable tests, including a
  controlled two-checkout experiment, POSIX symlink-environment identity,
  ownership and replacement controls, and package-content matching that does
  not depend on where the package was found;
* `tools/campaign_environment_experiment.py` — the laboratory experiment whose
  receipts this report quotes;
* [campaign environment procedure](campaign-environment-procedure.md) — the
  reusable procedure and the Codex/Freebuff migration guide.

**Measured result (one run, 174.6 s host wall, at revision `4446276…` from a
clean worktree):** a campaign environment's isolated child imports the
campaign's own installation (source code digest identical to the checkout) even
when `PYTHONPATH` names a conflicting implementation; a preflight inside the
campaign returns `qualified` with exit status 0 and eleven passing checks. Every refusal below returns a
non-zero status and never `qualified`: a shared parent that merely *names* the
campaign interpreter, a conflicting `PYTHONPATH`, the shared interpreter as
parent, a checkout whose Git metadata cannot be read (`unknown`, exit 2), and a
target directory this campaign cannot prove it owns.

## Review corrections and what changed

The independent review of this PR found five reliability defects in the first
version of the mechanism. Each is corrected in code, covered by a regression
test, and re-measured in the laboratory experiment.

### 1. Interpreter identity

The first version let an explicitly supplied interpreter stand in for the
parent's identity: `preflight --interpreter` could make a shared parent look
like a campaign interpreter. It also compared executables, which cannot
distinguish environments on POSIX because every virtual environment's
`bin/python` is a link to the base interpreter.

* the running parent is now described by `identity.describe_running_interpreter()`
  from its own `sys.executable` (unresolved), `sys.prefix` and the digest of the
  path it was invoked as;
* `--interpreter` is recorded as a **selection** in its own check. It can pass or
  fail that check and can still be refused on the parent check;
* environment identity is `sys.prefix` equality (`same_environment`); executable
  path identity is only ever used to compare paths (`same_path`);
* the child's own report carries its invocation path, its resolved path, its
  prefix and the digest of the invoked executable, and all four are compared
  with the record.

Measured: with the shared interpreter as parent and `--interpreter` naming the
campaign interpreter, `requested-interpreter` passes while `parent-interpreter`
fails with `parent_prefix` equal to the shared prefix, and the verdict is
`unqualified`. Two symlink-based POSIX environments share one executable inode
and one real path, and are still distinguished by prefix and site-packages
(`SymlinkedEnvironmentIdentityTest`); that test runs on the Ubuntu CI legs and
skips where the host refuses to create symbolic links, as this Windows guest
does.

### 2. Package and source identity

`parent-origin` and `observed-origin` used to accept a package merely because it
was found inside the expected `site-packages`. They now require a positive
content match: the parent's and the child's Python digest must equal the digest
the provisioning receipt recorded, whatever the location. Location is still
recorded, as an observation.

A receipt is now bound to its `schema_version`, `kind`, campaign, checkout,
package, target layout and site-packages containment before any of it is
believed; a bound record that was not `qualified` is refused outright. The
checkout must be the root of its own Git repository: `source_identity` reports
`enclosing-repository` for a subdirectory of another checkout and the
`checkout-root` check fails, instead of silently inheriting the enclosing
repository's `HEAD`. Provisioning compares the source revision and tree digest
before and after installation and refuses if either changed, and
`source_drift` distinguishes "changed" from "could not be established", so an
unavailable digest can never be read as equality.

Measured: an edited (uncommitted) campaign package is reported as
`source-content`; committing it adds `source-revision`; hiding `.git` yields
`unknown` with exit status 2, never `qualified`.

### 3. Environment ownership and replacement

The first version treated an existing directory without a record as scratch
space. A missing record proves nothing about ownership, so the target path is now
classified without following redirects: `absent`, `directory`, `symlink`,
`junction`, `file` or `other`. An existing directory is used only when it holds
an `environment.json` that binds to this campaign, checkout, package and layout,
an interpreter file, and a `venv` directory; anything else is refused with a
specific code (`existing-directory-without-valid-record`,
`existing-directory-with-foreign-record`, `existing-record-without-interpreter`,
`existing-redirect-at-target`). On Windows a junction is not reported by
`os.path.islink`, so `FILE_ATTRIBUTE_REPARSE_POINT` and the reparse tag are read
directly.

Replacement is staged, never in place: the new environment is built under
`.staging-<campaign>-<uuid>` inside the owned root, validated, and swapped in
only after the previous environment has been renamed aside; the retired
environment is deleted afterwards. An existing installation is never edited, so
stale installed modules cannot survive a replacement. The site-packages of the
new environment must lie inside it, in the staged copy and after the swap.

Measured, on disposable synthetic directories only: the unowned directory is
refused (`existing-directory-without-valid-record`) and its content is
preserved intact; the Windows junction is refused
(`existing-redirect-at-target`); an owned replacement reports `replaced-owned`
and the stale file planted in the old environment is absent from the new one,
which itself qualifies.

### 4. Installation boundaries

Build isolation downloads a build backend, so it is now opt-in:
`install_source(..., allow_build_isolation=False)` makes exactly one attempt with
`--no-build-isolation` and records the failure; only
`provision --allow-build-isolation` reaches the network, and every attempt
records its mode plus `build_isolation_explicitly_enabled`. The historical run's
`install_mode: build-isolation` was produced that way deliberately and is
reproduced explicitly in the new experiment; it is not presented as the default.
The default provision on this host is measured as refusing
(`installation-failed`) with nothing created at the target path, while both
campaign provisions carry `install_mode: build-isolation` and
`build_isolation_explicitly_enabled: true`. The mechanism still writes only
below its own root: never the bootstrap interpreter's site-packages, and never
another campaign's environment.

### 5. Evidence and licensing

`docs/evidence/agent-usage/` (provider-neutral) now carries this campaign's
Freebuff receipts. Nothing is invented: the desktop agent exposes no model
identity, context size or quota, so every such field is `null` with an explicit
note and `measurements` is an empty list rather than a zero. Licensing was
checked against [LICENSING.md](../../LICENSING.md): the new source and tests are
`GPL-3.0-or-later`, the reports, procedure and evidence JSON are
`GPL-3.0-or-later OR CC-BY-SA-4.0`, and every new file has a matching REUSE
sidecar.

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
| `.git` hidden from the checkout | `unknown` | `checkout-root`, `source-revision` | 2 |

With the metadata hidden, `source_identity` returned `state: not-a-repository`,
`failure: rev-parse-failed` and `revision: null`; the verdict was `unknown`,
`measurement_allowed` was false, and the two unavailable-evidence checks were
reported as `unknown` rather than as mismatches. Restoring `.git` restored
`state: git`. An unreadable identity is never reported as a clean measurement,
and it is not reported as a contradiction either: the exit statuses 1 and 2 mean
different things to a caller.

A subdirectory of this repository is refused the same way a second, independent
campaign checkout is accepted: `state: enclosing-repository`,
`failure: checkout-not-repository-root`, `revision: null`. `--accept-enclosing`
exists only for a documented synthetic layout, and every synthetic checkout in
the experiment therefore gets its own repository.

## End-to-end qualification of this repository

| Preflight | Verdict | Reasons | Exit |
| --- | --- | --- | --- |
| Inside the campaign environment | `qualified` | — (11 checks pass) | 0 |
| Campaign interpreter, `PYTHONPATH` = conflicting copy | `unqualified` | `parent-package` | 1 |
| Shared interpreter as parent | `unqualified` | `parent-interpreter` | 1 |
| Shared parent naming the campaign interpreter | `unqualified` | `parent-interpreter` (the selection passes) | 1 |

The eleven checks are `environment-record`, `checkout-root`,
`parent-interpreter`, `requested-interpreter`, `parent-package`,
`source-revision`, `source-content`, `child-interpreter`, `observed-origin`,
`observed-content` and `child-isolation`; all eleven passed inside the campaign
environment. Observed content matched the provisioning receipt exactly:
`python_digest` and bundle digest identical for source and install.

Two rules changed because of a measurement. `parent-package` and
`observed-origin` compare **code content**, not only location: a parent running
with `PYTHONPATH` pointing at the same checkout is running the campaign's bytes
and is accepted, and a parent importing the shared wheel is refused even when
its interpreter is right. And a requested interpreter is a selection: the last
table row shows the exact case the review raised, where the shared parent names
the campaign interpreter and is still refused on its own identity.

The child checks are strict about the observed child as well: its prefix, its
invocation path and its executable digest must all match the receipt, and its
package content must match the digest the provisioning probe recorded. A child
that quietly ran the base interpreter, or another environment's interpreter,
cannot pass them.

## Limitations

* **Not an OS sandbox.** The campaign environment is a `venv` owned by the
  campaign, on the same account and filesystem. It changes which code a process
  imports; it does not confine what it can touch. The laboratory posture of
  2026-11-11 still governs risk.
* **Point-in-time proof.** A preflight describes the parent, the child and the
  checkout when it runs. A long campaign must re-run it at its checkpoint; it
  cannot prove what an earlier step executed.
* **Build backend availability.** `setuptools` and `wheel` are absent from the
  shared interpreter, so the default offline provision fails here and the
  network-capable mode has to be requested explicitly
  (`provision --allow-build-isolation`). The measured cost of one real provision
  on this host was 25.4 s cold. Every attempt records its mode (`install_mode`)
  and whether the opt-in was given, so a receipt can never suggest that a
  network fetch was the default. A shared tools environment makes provisioning
  offline; see the procedure.
* **Ownership is refused, not guessed.** An existing directory without a valid,
  bound record is never reused or overwritten, and neither is a symbolic link or
  a Windows junction at the target path. A replacement builds a complete new
  environment under a staging path and swaps it in; the previous environment is
  renamed aside and deleted. Recovering a campaign whose record was lost means
  deleting that environment deliberately, not letting a provision adopt it.
* **Staging needs the same filesystem.** The swap is a directory rename inside
  the campaign root, so `--root` must not span filesystems; otherwise the
  replacement fails and the previous environment is restored.
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
  only on the Windows guest. The symlinked-environment identity test is the
  exception in kind: it exercises real POSIX environments, on the Ubuntu legs.
* **`local-results` inheritance.** A synthetic checkout created inside a Git
  checkout inherits the enclosing repository's `HEAD`; that was found here and
  is why each synthetic checkout gets its own repository. The mechanism now
  refuses such a checkout (`enclosing-repository`) instead of attributing the
  enclosing revision to it.

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

The experiment writes `01-inventory.json`,
`02-installation-boundary.json`, `03-isolation.json`, `04-qualification.json`,
`05-ownership.json`, `06-drift.json`, `07-metadata-failure.json`,
`08-inventory-after.json`, `09-summary.json` and a redacted
`public-summary.json` under `local-results/` (Git-ignored). Only the redacted
projection is published, as
[`docs/evidence/campaign-python-environment-20261127-corrections.json`](../evidence/campaign-python-environment-20261127-corrections.json).

## Evidence and provenance

* [Redacted corrected-run receipt](../evidence/campaign-python-environment-20261127-corrections.json) —
  inventory counts, launch-site audit, launch matrix, the installation boundary,
  ownership refusals and replacement, drift, metadata failure, and the four
  qualification verdicts.
* [Redacted first-run receipt](../evidence/campaign-python-environment-20261127.json) —
  preserved unchanged: it is the measurement that demonstrated the
  source-attribution defect and the historical
  `install_mode: build-isolation`. Its field names describe that earlier version
  of the mechanism.
* Private raw receipts (absolute paths, pip logs) remain under the campaign
  checkout's `local-results/experiment-20261127/` and
  `local-results/experiment-corrections/`, outside Git.
* Usage: [Freebuff receipts](../evidence/agent-usage/) in the provider-neutral
  ledger — unknown model, context and quota are recorded as `null`, not zero.
* Method: `tools/campaign_environment_experiment.py` on 2026-11-27, one run,
  CPython 3.13.17 on the Windows 10 laboratory guest; no emulator, model turn or
  unattended dispatch.

**Visual exemplars: not applicable.** The entire result set is terminal output
and JSON receipts; there is no meaningful visual state in this work, and no
image was fabricated to satisfy the guideline.
