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
(`installation.install_mode`, `build_isolation_explicitly_enabled`), and it is
never implied. Try the offline mode first; a network fetch should be a decision,
not a surprise.

**Ownership is checked before anything is written.** An existing directory at
the target path is used only if it holds an `environment.json` that binds to
this campaign, checkout, package and layout, with an interpreter and a `venv`
inside. Otherwise the provision refuses with one of
`existing-directory-without-valid-record`, `existing-directory-with-foreign-record`,
`existing-record-without-interpreter` or `existing-redirect-at-target` — a
symbolic link or Windows junction is never followed. Replacing an owned
environment builds a complete new one under `.staging-<campaign>-<uuid>` and
swaps it in, so no file from the old installation survives; the previous
environment is renamed aside and then deleted.

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
| `parent-interpreter` | the parent is not the campaign interpreter | run the tool with `& $py -m …`; `--interpreter` does **not** fix this |
| `requested-interpreter` | `--interpreter` names something other than the recorded interpreter | pass the campaign interpreter, or omit the option |
| `parent-package` | the parent imported different code (usually another campaign's wheel via `PYTHONPATH`) | clear `PYTHONPATH`, or point it at this checkout |
| `source-content` | the checkout changed after provisioning | re-provision |
| `source-revision` | `HEAD` moved (or could not be read) | re-provision, or fix the Git metadata |
| `child-interpreter` | the child ran a different environment or executable than the record | launch with the recorded interpreter |
| `observed-origin` | the isolated child imported package content that does not match the receipt | the child was launched with another interpreter, or the installation is stale |
| `observed-content` | the installed copy changed after provisioning | re-provision |
| `child-isolation` | the child ran without `-I` | use `deskmate-campaign-env launch` |

`--interpreter` records a **selection** for the child. It is a separate check
from `parent-interpreter`, which reads the running process's own prefix and
invocation path. Naming the campaign interpreter from a shared parent therefore
still fails: the request is not evidence about the parent. To qualify, run the
preflight *with* the campaign interpreter:

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
* On POSIX, two virtual environments share one executable inode through
  symbolic links; identify environments by `sys.prefix`, never by executable.
* If a future campaign needs a different package name, pass `--package`.
* The procedure owns no production behaviour: Supervisor and Observatory changes
  that consume these receipts need their own reviewed PRs (see the
  [campaign report](campaign-python-environment-isolation-20261127.md#integration-recommendations)).
