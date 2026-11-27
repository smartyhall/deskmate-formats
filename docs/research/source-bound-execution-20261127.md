# Source-bound Supervisor execution — 2026-11-27

**Issue:** [#207](https://github.com/smartyhall/deskmate-formats/issues/207).
**Depends on:** [#191](https://github.com/smartyhall/deskmate-formats/pull/191)
(integrated) and [#206](https://github.com/smartyhall/deskmate-formats/pull/206)
(merged into this branch as the environment foundation).
**Scope:** the Supervisor's production child launches, the publication-audit
defect #206 measured, and the binding that closes it.

The acceptance question is not "can an isolated child import a package". It is:
can a production Supervisor procedure obtain a *qualified* result while
executing an implementation other than the one its accepted source and plan are
bound to? Before this change, yes — through two launch sites. After it, every
workspace-bound launch refuses or reports failure instead.

## 1. The defect

`supervisor/workspace.py::command()` built

~~~python
argv = [str(Path(sys.executable).resolve()), *args]
env["PYTHONPATH"] = str(Path(workspace) / "src")
~~~

and the checkpoint passed `["-I", "-c", AUDIT]`. `-I` implies `-E` and `-P`, so
`PYTHONPATH` was ignored *and* the working directory was not on `sys.path`. The
audit imported `deskmate_formats.supervisor.repository_audit` from whatever the
launching interpreter had installed — the shared laboratory wheel — while the
receipt named the accepted workspace and the workspace's directory.

The same shape existed in `procedures.py`: `repository-audit`,
`portable-tests` and `package-build` were assembled as `[interpreter, ...]`
with `PYTHONPATH` in the environment, so their "repository code" was whichever
installation the interpreter resolved.

Removing `-I` would have been the wrong correction: the child would then read
`PYTHONPATH` and the user site directory from the ambient environment, which is
a weaker guarantee than the one we want. The corrected launch keeps `-I` and
makes the source explicit instead.

## 2. Production subprocess inventory

`python -m deskmate_formats.supervisor.execution_source` prints the same table
as JSON. Classes: **A** controller-pinned implementation, **B** accepted task
workspace, **C** immutable external tool, **D** unresolved.

| Site | Caller | Intended | Resolution | Receipt | Failure behaviour |
| --- | --- | --- | --- | --- | --- |
| `procedures.hash-files` | `_build_hash` | A | reviewed `-c` script text; reads checkout files as data | `plan.execution` (implementation digest, interpreter identity) | refused if a named input cannot be bound |
| `procedures.fixture-compare` | `_build_compare` | A | same, two files | same | same |
| `procedures.repository-audit` | `_build_audit` | B | bootstrap inserts and verifies the bound `src`, then imports the checkout's audit | `plan.execution` + child report | refused without a qualified environment; exit 78 on mismatch |
| `procedures.portable-tests` | `_build_portable_tests` | B | bootstrap verifies the checkout, then `runpy` runs `unittest` | same | exit 78 before any test runs |
| `procedures.package-build` | `_build_package` | B | bootstrap verifies the checkout, then the installed build frontend imports it | same + artifact hashes | non-zero build is a failed outcome |
| `procedures.reuse-lint` | `_build_reuse` | C | installed REUSE; reads files only | interpreter identity; no repository code | missing tool is a non-zero exit |
| `workspace.test-step` | `_step_argv` | B | bootstrap verifies the disposable S3 workspace | step receipt + child report | failed step blocks the checkpoint |
| `workspace.publication-audit` | `_step_argv` | B | bootstrap, then the audit runs against `Path.cwd()` | step receipt | exit 78 is a failed step |
| `workspace.reuse-step` | `_step_argv` | C | controller's installed REUSE | step receipt | non-zero blocks the checkpoint |
| `driver.synthetic-peer` | `driver.prepare` | A | controller's installed package, bound by driver hashes | `plan.argv`, executable and implementation digests | refused if a digest changed |
| `driver.codex-app-server` | `driver.prepare` / `protocol.AppServer` | C | hash-pinned native executable | `plan.executable_sha256` | refused on any pin or version mismatch |
| console entry points | operator shell | D | the operator's PATH decides; no plan binds the console script | the plan binds its own interpreter and implementation after it starts | source-bound operations refuse until an environment is selected |

Not production execution, and deliberately not "fixed": `campaign_env`'s
identity, provisioning, launch and probe helpers (they *are* the measurement),
pinned Git invocations, test fixtures, and
`tools/campaign_environment_experiment.py`. `PROCEDURES` now carries an
`execution_source` on every procedure and `catalog()` publishes it, so a new
procedure cannot be added without choosing a class.

## 3. The correction

`supervisor/execution_source.py` separates two facts that were conflated:

* `select_environment(campaign, checkout, root=..., revision=...)` reads a
  campaign environment record and *proves* it describes this interpreter: the
  record binds to the campaign, checkout, package and layout; the verdict is
  `qualified`; the described interpreter's prefix, invocation path and
  executable digest equal the record; `site-packages` is inside the environment;
  and the recorded source revision is the revision the plan is for. It uses
  #206's layout, record validation, interpreter description and receipt digests
  rather than a second provisioning mechanism. It never creates or repairs an
  environment.
* `bind_workspace(checkout, revision=...)` records the checkout revision, the
  `src/deskmate_formats` tree digest and the Python-only digest. A checkout at a
  different revision, or without a package tree, is refused.

`workspace_execution(...)` combines them and freezes a reviewed, stdlib-only
bootstrap into the plan. The child is launched as

~~~
<environment interpreter> -I -c <bootstrap> <src> <python digest> <report> <mode> <target> [arguments]
~~~

The bootstrap inserts the bound `src` at `sys.path[0]` and the checkout root at
`sys.path[1]` (so a repository test's `from src.x import y` resolves as it does
for a non-isolated `-m`), imports `deskmate_formats`, and checks the import
origin and the Python content digest **before** the reviewed target runs. A
mismatch writes its report and exits `78`; the target never runs. `-I` is
preserved, and because `-I` also discards `PYTHONDONTWRITEBYTECODE` the
bootstrap sets `sys.dont_write_bytecode` itself — otherwise validation would
dirty the tree it is validating.

`deterministic.prepare` now requires an `environment` for a workspace procedure,
binds the execution block into the plan, and refuses a plan whose vector does
not launch the bound workspace. `_verify_plan` re-establishes the environment
record digest, the interpreter identity, the checkout revision and the content
digests before the attempt fence. The outcome gains an `execution` block: the
binding, the child's own report, and `verified`. A zero exit with an unverified
report is recorded as `failed`/`bound-source-not-verified`, never as a completed
measurement.

For S3, `editing.grant` selects the environment and freezes the binding in the
plan; `driver._validate_plan` re-verifies it before the attempt fence, so a
failed environment check dispatches no task; and `workspace.checkpoint`
re-verifies it with `allow_workspace_change=True`, which relaxes *content only*
because the checkpoint runs after authorized edits. It then re-derives the
content digests from the edited tree and requires every step's child report to
be verified before a step can pass.

## 4. Reproduction

`tests/portable/test_supervisor_execution_source.py` builds two synthetic
checkouts whose `repository_audit` prints `audit:alpha` and `audit:beta`, and two
disposable virtual environments whose site-packages hold a **third**
implementation printing `audit:shared-preinstalled`. The shared laboratory
interpreter is not touched.

The reproduction runs the pre-correction vector directly:

~~~python
subprocess.run([env_python, "-I", "-c", workspace.AUDIT], cwd=checkout,
               env={**os.environ, "PYTHONPATH": str(checkout / "src")})
~~~

It prints `audit:shared-preinstalled`: the accepted workspace is neither
imported nor mentioned. The same contention through the production path prints
`audit:alpha`, with the child report showing `isolated: true`,
`pythonpath_present: true` (a deliberately hostile `PYTHONPATH` was set) and
`origin_inside_root: true`.

## 5. Lifecycle boundaries

| Situation | Behaviour |
| --- | --- |
| No environment record | plan refused: `environment-record-missing` |
| Record not `qualified`, or bound to another campaign/checkout/package/layout | refused: `environment-not-qualified` / `environment-record-mismatch` |
| Interpreter prefix, invocation path or digest differs | refused: `environment-interpreter-mismatch` |
| Environment revision differs from the accepted source revision | refused: `environment-source-mismatch` |
| Checkout content changed after preparation | dispatch refused: `workspace-changed-after-preparation`; an S3 checkpoint re-derives content but never the revision or interpreter |
| Record rewritten after preparation | dispatch refused: `environment-changed-after-preparation` (record digest) |
| Child cannot prove its import | outcome `failed`, reason `bound-source-not-verified` |
| Concurrent provisioning | the campaign environment's own lock and record digest refuse the second writer |
| Replacement | explicit `--replace`; the Supervisor never provisions, upgrades or repairs an environment during an attempt |

An environment is requalified by provisioning it again at the new revision.
Source drift invalidates qualification; it never silently re-binds. These are
cooperating-worker boundaries, not an operating-system sandbox.

## 6. Verification

Local, at the head that adds this document:

| Check | Result |
| --- | --- |
| `tests/portable/test_supervisor_execution_source.py` | 14 tests OK |
| `test_supervisor_procedures.py` / `test_supervisor_procedure_limits.py` | 6 / 9 tests OK |
| `test_supervisor_deterministic.py` | 25 tests OK (2 Windows skips) |
| `test_supervisor_task_deterministic.py` | 7 tests OK |
| `test_supervisor_editing.py` | 13 tests OK (364 s) |
| `test_supervisor_timeouts.py` | 7 tests OK (89 s) |
| `ruff check src tests/portable tools` | clean |
| `reuse lint` | 2005/2005 files |
| `tools/audit_repository.py` | exit 0 |
| `python -m build --wheel` | wheel built; contains `execution_source.py` and its license |

The POSIX-only paths (symlinked environments, `pidfd`) are exercised by the
Ubuntu legs of exact-head CI; this host is Windows. CI results for this head are
recorded in the pull request, not asserted here. The wheel index was reached
once, by the standard isolated `build` frontend; no global interpreter was
modified.

## 7. Limitations

* The child's report is evidence about *its own* launch. It is not proof that no
  other code ran, and the bootstrap is controller code that a compromised
  interpreter could ignore.
* Content binding covers `src/deskmate_formats`; tests, fixtures and data are
  bound by the plan's input digests and, for S3, by the authorized change set.
* An environment qualified at revision R and a workspace at revision R can hold
  different content (S3 edits). That difference is authorized by the change set,
  not by the environment.
* Console entry points remain class D: the operator's interpreter decides what
  starts the process. The plan binds from that point on.
* No live task, native experiment, emulator or provider call was performed.

## 8. Authorization observed

No global Python installation was modified; the conflicting installation exists
only inside disposable test environments. No #206 branch was changed. No
credential, private path, emulator or model turn was involved, no unattended
execution was authorized, and this branch is not self-merged.
