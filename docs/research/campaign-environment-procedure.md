# Campaign environment procedure and migration guide

Reusable procedure for giving a campaign its own Python environment and for
proving that its parent and isolated child processes run the intended source
revision. Written for the Windows 10 laboratory; POSIX equivalents are noted
where they differ.

This is procedure, not authorization: it does not permit emulator use, model
dispatch, publication or any other gated action. See `AGENTS.md`.

## When to use it

Use a campaign environment when a worker will *write* to a checkout — running the
portable suite, the repository audit, one of the demonstrations, or any tool that
launches `deskmate_formats` children — and more than one campaign may be active
on the host. A read-only question about a file does not need one.

The rule that replaces "export `PYTHONPATH` and hope": **an isolated child
(`python -I`) runs whatever the interpreter that launched it has installed.**
`-I` discards `PYTHONPATH`, the user site directory and `PYTHON*` variables, so
the only way to steer an isolated child is to choose its interpreter.

## One-time host setup

### Shared, read-only tools environment

Campaign environments hold this project only. Ruff, REUSE and build tooling are
large and immutable, so one shared environment serves every campaign and keeps
`pip` able to build offline:

```powershell
cd C:\DeskMateLab\sources\deskmate-formats
py -3.13 -m venv local-results\tools-venv
local-results\tools-venv\Scripts\python.exe -m pip install --upgrade pip
local-results\tools-venv\Scripts\python.exe -m pip install "ruff>=0.11" "reuse[charset-normalizer]>=6.0" build "setuptools>=77" wheel
```

`local-results\` is Git-ignored and excluded from the publication audit. On
POSIX the same commands use `python3 -m venv local-results/tools-venv` and
`local-results/tools-venv/bin/python`.

Why `setuptools` matters: this project's `pyproject.toml` declares a build
backend, and the system interpreter on this host has no `setuptools`. Without it,
`pip install --no-build-isolation` fails and the installer must reach the
network for a build environment. The tools environment above removes that
dependency for every campaign provision.

### Confirm the inventory

```powershell
$env:PYTHONPATH = 'src'
python -m deskmate_formats.campaign_env.cli inventory --out local-results\inventory.json
```

Record, from the receipt: which interpreters exist, which package each resolves,
which environments already exist, and every `-I` launch site. Do not modify
anything you find — another campaign owns it.

## Per-campaign provisioning

```powershell
cd C:\DeskMateLab\sources\deskmate-formats-campaigns\<campaign>   # your checkout
$tools = 'C:\DeskMateLab\sources\deskmate-formats\local-results\tools-venv\Scripts\python.exe'
$env:PYTHONPATH = 'src'
python -m deskmate_formats.campaign_env.cli provision `
  --campaign <campaign> `
  --python $tools `
  --out local-results\campaign-envs\<campaign>-provision.json
```

This creates `local-results\campaign-envs\<campaign>\venv`, installs **this
checkout** into it, runs the isolated probe inside the new environment, and
writes `environment.json`. It refuses to run unless the checkout is the root of
its own Git repository with a readable revision, and refuses to replace an
existing environment without `--replace`.

**Installation is offline by default.** `setuptools` and `wheel` are absent from
this host's system interpreter, so a provision of this project fails with
`installation-failed` unless the build backend is available. Install the tools
environment above, or opt into the network-capable fallback explicitly:

```powershell
python -m deskmate_formats.campaign_env.cli provision --campaign <campaign> --python $tools --allow-build-isolation
```

`--allow-build-isolation` is recorded in the receipt
(`installation.install_mode`, `installation.index_access`,
`build_isolation_explicitly_enabled`), and it is never implied. The offline mode
passes `--no-index` as well as `--no-build-isolation`, so it cannot contact a
package index even indirectly. Try the offline mode first; a network fetch should
be a decision, not a surprise.

**Ownership is checked before anything is written.** An existing directory at
the target path is used only if it holds an `environment.json` that binds to
this campaign, checkout, package and layout, with an interpreter and a `venv`
inside. Otherwise the provision refuses with one of
`existing-directory-without-valid-record`, `existing-directory-with-foreign-record`,
`existing-record-without-interpreter` or `existing-redirect-at-target` — a
symbolic link or Windows junction is never followed, and a redirected
environment root (or a redirect anywhere between the checkout and that root) is
refused as `redirected-environment-root`.

Only one provision per campaign may run: an exclusive `.lock-<campaign>` file in
the environment root makes a second one fail with `provisioning-in-progress`.
The lock is deliberately not self-expiring. If a provision crashed, confirm that
nothing is running and delete that one lock file.

Replacing an owned environment builds a complete new one under
`.staging-<campaign>-<uuid>`, revalidates ownership under the lock immediately
before the swap (refusing `target-changed-during-provisioning` if the target or
its record changed), moves the previous environment aside, and deletes it only
after the new installation has passed final verification and its receipt is
durable. If either fails, the previous environment is restored and the old
receipt is untouched. If the restore itself cannot be established, the command
fails with `replacement-recovery-uncertain`, whose detail names the retired
environment: nothing is deleted, and the operator decides what to do next.

The swap itself is three renames, and each way one of them can fail has its own
answer:

| Failure | What is left | Code |
| --- | --- | --- |
| the previous environment cannot be moved aside | nothing moved; target intact; staging removed | `environment-retirement-failed` |
| the staged environment cannot be moved in, and the restore succeeds | previous environment back in place; staging removed | `environment-swap-failed` |
| the staged environment cannot be moved in, and the restore fails too | both copies kept; private recovery receipt written | `replacement-recovery-uncertain` |

On the third, `.recovery-<campaign>-<uuid>.json` in the environment root records
what the retired path, the staged path and the target's `venv` path are *now*,
the two failed operations, the record digest that was expected, and four
recovery steps. The error's `detail` carries the same paths, so the evidence
does not depend on that one file. Nothing is deleted on that path: inspect both
copies, move the one you intend to keep to `venv`, or delete the environment
deliberately. A target whose `venv` is missing is refused by design, so a
half-recovered directory is not silently adopted by the next provision.

Re-provision after any source change you intend to measure; a stale installation
is reported, not silently used.

## Preflight before a measured run

```powershell
$env:PYTHONPATH = $null
$py = 'local-results\campaign-envs\<campaign>\venv\Scripts\python.exe'
& $py -m deskmate_formats.campaign_env.cli preflight --campaign <campaign> --out local-results\preflight.json
"exit: $LASTEXITCODE"
```

| Exit | Verdict | Meaning | Action |
| --- | --- | --- | --- |
| 0 | `qualified` | parent, child and checkout agree with the provisioning receipt | proceed |
| 1 | `unqualified` | a definite mismatch: look at `reasons` | do not report a measurement |
| 2 | `unknown` | identity could not be established (no record, unreadable Git) | do not report a measurement |

`reasons` names the failing checks. The common ones:

| Reason | Cause | Fix |
| --- | --- | --- |
| `environment-record` | no record, or a record bound to another campaign, checkout, package or layout | provision this checkout and campaign; do not adopt the directory |
| `checkout-root` | the checkout is a subdirectory of another repository | provision from the repository root |
| `parent-interpreter` | the parent's prefix, invocation path or executable digest does not match the record | run the tool with `& $py -m …`; `--interpreter` does **not** fix this |
| `requested-interpreter` | `--interpreter` names an interpreter whose own prefix, path or digest differs, or one that cannot be described | pass the campaign interpreter, or omit the option |
| `parent-package` | the parent imported different code (usually another campaign's wheel via `PYTHONPATH`) | clear `PYTHONPATH`, or point it at this checkout |
| `source-content` | the checkout changed after provisioning | re-provision |
| `source-revision` | `HEAD` moved (or could not be read) | re-provision, or fix the Git metadata |
| `child-interpreter` | the child ran a different environment or executable than the record | launch with the recorded interpreter |
| `observed-origin` | the isolated child imported package content that does not match the receipt | the child was launched with another interpreter, or the installation is stale |
| `observed-content` | the installed copy changed after provisioning | re-provision |
| `child-isolation` | the child ran without `-I` | use `deskmate-campaign-env launch` |

`--interpreter` records a **selection** for the child. It is a separate check
from `parent-interpreter`, which reads the running process's own prefix,
invocation path and executable digest. Naming the campaign interpreter from a
shared parent therefore still fails: the request is not evidence about the
parent, and a requested interpreter is described in its own process before its
prefix, path and digest are compared. To qualify, run the preflight *with* the
campaign interpreter:

```powershell
& $py -m deskmate_formats.campaign_env.cli preflight --campaign <campaign>
```

Keep `preflight.json` with the run's other receipts. It is the artifact that
makes a later measurement attributable.

## Launching children

Never pass `sys.executable` to an isolated child and assume the campaign's code
ran. Build the vector from the campaign interpreter:

```powershell
& $py -m deskmate_formats.campaign_env.cli launch `
  --interpreter $py --module deskmate_formats.supervisor.task_cli --argument --help
```

In code:

```python
from deskmate_formats.campaign_env import launch
receipt = launch.run_isolated(campaign_interpreter, "deskmate_formats.some_cli", arguments=["--json"])
```

`launch.isolated_argv` requires an absolute interpreter path, keeps `-I`, and
refuses a vector whose identity cannot be attributed. `launch.probe` runs the
campaign probe in that child and returns its own resolution as JSON.

## Adoption contract for issue #207

#207 adopts campaign environments in production Supervisor procedures. This is
the interface those callers may depend on; implementing the adoption is #207's
work, not this procedure's.

### Invocation

* `python -m deskmate_formats.campaign_env.cli <command>` and the installed
  `deskmate-campaign-env` console script are one entry point.
* Commands: `inventory`, `provision`, `preflight`, `probe`, `identity`,
  `launch`. Exit status is part of the contract: `preflight` returns 0, 1 or 2
  for `qualified`, `unqualified` and `unknown`; `provision` returns 0 only for a
  `qualified` receipt, and 1 with a JSON `{"verdict": "failed", "reason": …}`
  document otherwise.
* A failure the mechanism understands is a short publishable `reason` code, not
  an exception text. Treat an unrecognised code as a hard stop.
* The module is standard-library only and takes the package name as a parameter,
  so a Supervisor can import it without the campaign's own dependencies.

### Ownership

* One campaign owns each environment directory, its `environment.json`, its
  `venv` and the `.lock-<campaign>` beside it. A directory this campaign cannot
  prove it owns is refused, never adopted: `existing-directory-without-valid-record`,
  `existing-directory-with-foreign-record`, `existing-record-without-interpreter`,
  `existing-directory-with-unreadable-record`, `existing-redirect-at-target`,
  `unexpected-entry-at-target`, `redirected-environment-root`.
* Provisioning holds the lock for the whole run; a second provision of the same
  campaign fails `provisioning-in-progress`. A Supervisor must not remove that
  lock while a provision could be running, and must not write into the
  environment root, rename its contents, or edit a record or receipt in place.

### Identity

* An interpreter is identified by `sys.prefix`, its **invocation path**, and the
  SHA-256 of its executable. `identity.same_invocation_path()` compares named
  paths without resolving; `identity.same_environment()` compares prefixes.
  Neither `resolve` nor `samefile` may be substituted: on POSIX two environments
  share one executable through symbolic links.
* Each receipt records `bootstrap_interpreter` and `bootstrap_identity` for the
  interpreter that built the environment, and `environment_identity` for the
  environment's own interpreter.
* A Supervisor launching a child passes the environment interpreter explicitly
  and keeps `-I`. `sys.executable` is the parent's interpreter, which is exactly
  the fact a preflight is meant to disprove.

### Provisioning

* `provision(checkout, campaign, root=…, python=…)` returns a receipt whose
  `verdict` is `qualified`; any other outcome is a failed provision. It is
  offline by default (`--no-index --no-build-isolation`, `install_mode:
  "offline"`, `index_access: false`); only an explicit `--allow-build-isolation`
  may reach an index, and every attempt records which mode ran.
* It refuses a checkout that is not the root of its own Git repository
  (`source-identity-not-established`) and one that changes while it installs
  (`source-changed-during-provisioning`).
* The replacement is built and validated under `.staging-<campaign>-<uuid>`; the
  previous environment is deleted only after final verification and a durable
  receipt write.
* The environment holds this project and nothing else. Shared immutable tools
  stay in one read-only tools environment; a dependency a campaign installs into
  its environment is not reproduced by another campaign's provision.

### Preflight

* `preflight(checkout, campaign=…, interpreter=…)` evaluates eleven checks and
  sets `measurement_allowed` only when all of them pass. `verdict` is
  `qualified`, `unqualified` or `unknown`, and `reasons` names the failing
  checks.
* Run it *with* the campaign interpreter. `--interpreter` is a child selection;
  it is never evidence about the parent.
* Run it before each measured or published step, keep the receipt beside the
  numbers, and publish only the redacted projection (`--public`).

### Remaining limitations for #207

* The mechanism proves identity, not isolation: it is not an OS sandbox.
* A preflight is point-in-time evidence. A long procedure must re-run it at its
  checkpoint.
* `--replace` requires a complete owned environment. A directory whose `venv` is
  missing — including one left by an uncertain swap — must be repaired or
  deleted deliberately.
* The lock is not self-expiring, and staging must share a filesystem with the
  target.
* `pip --target` installs no console scripts inside the environment, so children
  are launched as `-I -m module`, which is what the Supervisor already does.
* The Supervisor still passes `sys.executable` in `workspace.command()` and
  resolves its own interpreter in `procedures._interpreter()`; binding those to
  the campaign interpreter, refusing a campaign lease granted under a stale
  environment, and adding `environment_verdict` to the Observatory projection
  are #207's changes.

## Migration checklist

For a Codex or Freebuff campaign starting on this host:

1. Work in your own branch and your own worktree; do not switch another
   campaign's checkout or reuse its environment.
2. Run `inventory` once and record the interpreter you intend to use.
3. Provision a campaign environment under your checkout's `local-results/`.
4. Replace `[sys.executable, …]` with the campaign interpreter for every child
   that must run your code, keeping `-I`.
5. Run `preflight` before each measured or published step and keep the receipt.
6. Re-provision after source changes; do not delete or replace an environment
   you do not own.
7. Put the preflight verdict in the report next to the numbers, with `reasons`
   when it is not `qualified`.

## What to publish

Publish the redacted projection only:

```powershell
& $py -m deskmate_formats.campaign_env.cli preflight --campaign <campaign> --public
```

`receipts.public()` replaces absolute paths with placeholders, reduces search
paths to counts, and drops keys it does not know instead of publishing them by
default. A receipt can still contain ordinary prose; read it before publishing.
Raw receipts, pip logs and the synthetic checkouts stay private.

## Maintenance

* The mechanism is standard-library only. Its tests are portable: they build two
  `venv`s without `pip` and link a synthetic package with a `.pth` entry, so they
  cost a few seconds and need no network, ROMs or emulator.
* Fail closed on purpose: if a check cannot be evaluated, the verdict is
  `unknown`. Do not add a "trusted" override; fix the identity instead.
* The preflight has eleven checks, and `measurement_allowed` is true only when
  all of them pass. Unavailable evidence (`unknown`) and disagreement
  (`unqualified`) are deliberately different verdicts with different exit
  statuses.
* Ownership beats convenience: a lost `environment.json` means the environment
  is not adoptable. Delete that directory deliberately and provision again.
* Do not clean up a `replacement-recovery-uncertain` state by hand until you have
  read its recovery receipt: the copy at `.retired-…` is the previous
  environment and the copy at `.staging-…` is the new, never-verified one, and
  neither is known to be usable in place.
* On POSIX, two virtual environments share one executable inode through
  symbolic links; identify environments by `sys.prefix`, and compare
  interpreter paths as they were *named* (`same_invocation_path`), never after
  resolving them.
* Do not edit an environment, its record or its lock by hand while a provision
  could be running; the lock exists because that overlap produces exactly the
  mixed state the mechanism now refuses.
* If a future campaign needs a different package name, pass `--package`.
* The procedure owns no production behaviour: Supervisor and Observatory changes
  that consume these receipts need their own reviewed PRs (see the
  [campaign report](campaign-python-environment-isolation-20261127.md#integration-recommendations)).
