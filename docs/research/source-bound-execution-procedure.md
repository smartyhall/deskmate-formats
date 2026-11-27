# Source-bound execution — integration and migration guide

**For:** operators and reviewers of the Supervisor's deterministic backend and
S3 checkpoints. **Companions:** the
[campaign report](source-bound-execution-20261127.md), the
[campaign-environment procedure](campaign-environment-procedure.md), and the
[execution-integrity record](execution-integrity-20261126.md).

This guide describes how a production launch is bound to an accepted source,
what must exist before a plan can be prepared, and how to migrate existing
invocations. It does not grant execution authority and does not create a second
task architecture.

## The two identities

| Identity | What it is | Where it is recorded |
| --- | --- | --- |
| Controller | the `deskmate_formats` implementation running the Supervisor, plus the interpreter running it | `plan.implementation`, `plan.execution` with `source: controller` |
| Accepted workspace | the task checkout at its accepted revision, with its package content digest | `plan.execution.workspace`, child report, `source: workspace` |

A task's working directory is *not* evidence about the code. A controller-pinned
procedure may run in a task's working directory; its receipt says
`source: controller` and names no workspace. A workspace-bound procedure runs
the checkout it names, and the child refuses if its import origin or content
digest differs.

## Prerequisites

1. A campaign checkout that is the **root** of its own Git repository, at the
   revision the plan will name.
2. A qualified campaign environment for it:

   ~~~
   deskmate-campaign-env provision --checkout <checkout> --campaign <campaign> [--replace]
   deskmate-campaign-env preflight --checkout <checkout> --campaign <campaign>
   ~~~

   `preflight` must print `qualified` and `measurement_allowed: true`. Both
   commands are #206's mechanism; this change adds no provisioning of its own.
3. For S3, the task's accepted source revision must equal the environment's
   recorded revision. If it does not, requalify rather than reusing the
   environment.

## Deterministic procedures

~~~bash
deskmate-supervisor-deterministic prepare \
  --state <new attempt directory> \
  --campaign <campaign> \
  --procedure repository-audit \
  --working-directory <accepted checkout> \
  --environment-campaign <campaign> \
  --environment-checkout <campaign checkout> \
  [--environment-root <root>]
~~~

`--environment-campaign` and `--environment-checkout` are required for
`repository-audit`, `portable-tests` and `package-build`; omitting them is a
refusal, not a fallback. `hash-files` and `fixture-compare` are controller
scripts and do not need an environment, but may use one for interpreter
selection. `prepare-task` accepts the same three flags.

The plan then contains an `execution` block. Review it before authorizing the
exact digest:

| Field | Meaning |
| --- | --- |
| `source` | `controller`, `workspace` or `external` |
| `workspace.revision` / `workspace.dirty` | the accepted checkout's HEAD and whether it has uncommitted changes |
| `workspace.package.tree_digest` / `python_digest` | the full and Python-only content digests |
| `environment.record_sha256` | the exact environment record that was believed |
| `environment.interpreter` / `interpreter_sha256` / `prefix` | the owned interpreter |
| `environment.checks` | prefix, invocation path, executable digest and site-packages containment |
| `bootstrap.script_sha256` | the reviewed launcher |

`run --authorization <plan digest>` re-establishes all of it before the attempt
fence. If anything moved, the attempt is refused and nothing is dispatched.

## S3 checkpoints

~~~bash
deskmate-supervisor-s3 prepare-synthetic \
  --queue <queue> --state <state> <id> <revision> \
  --accepted-review-token <token> --task-class source-edit-v1 \
  --plan-local-checkpoint \
  --environment-campaign <campaign> \
  --environment-checkout <campaign checkout> \
  [--environment-root <root>]
~~~

`prepare-live` takes the same environment flags. Without them the grant fails
before a workspace is reserved.

At dispatch, the frozen binding is re-verified before the attempt fence. At the
checkpoint — which runs after the authorized edits — the environment, the
interpreter and the base revision are still verified, while the *content* digests
are re-derived from the edited tree. Each validation step is a bound child:
`test-*` and `publication-audit` import the workspace package and prove it; the
`reuse` step is an installed tool and makes no workspace claim. A step passes
only if it exits zero **and** its child report verifies.

## Migration notes

| Before | Now |
| --- | --- |
| `PYTHONPATH` exported to children | not exported; the bound checkout is inserted and verified explicitly |
| `[sys.executable, "-I", "-c", AUDIT]` | `<campaign interpreter> -I -c <bootstrap> ... code <AUDIT>` |
| `[sys.executable, "-m", "unittest", ...]` | `<campaign interpreter> -I -c <bootstrap> ... module unittest ...` |
| `[sys.executable, "-m", "reuse", "lint"]` | unchanged: the controller's installed tool, recorded as `external` |
| Plans without `execution` | refused: `execution-binding-missing` |
| A dirty S3 workspace at checkpoint | content re-bound from the authorized change set; revision and interpreter never relaxed |

Bytecode is not written into the bound checkout: `-I` discards
`PYTHONDONTWRITEBYTECODE`, so the bootstrap sets `sys.dont_write_bytecode`
before importing. A validation run therefore cannot dirty the tree it is
validating.

## Public receipts

`execution_source.public_execution()` replaces every absolute path with
`<path>` and drops the child report path; digests, revisions, prefixes-as-values
and check results remain. The full binding stays in private storage. Published
usage receipts record measurements as absent, never as zero.

## Handoff for issue #204

[#204](https://github.com/smartyhall/deskmate-formats/issues/204) proposes one
harmless deterministic `hash-files` canary over `README.md` from an accepted
exact revision. It is **not** authorized, prepared or executed by this campaign.

Prerequisites, in order:

1. #191 and #206 integrated, and this change integrated after them.
2. A campaign-owned clean checkout at the reviewed commit, plus a qualified
   environment for that exact revision (`provision` then `preflight` →
   `qualified`).
3. A reviewed manifest at `ops/tasks/github-hash-canary.json`, accepted through
   the existing trusted-intake commands. Acceptance does not execute.
4. `prepare-task --environment-campaign --environment-checkout ...` to freeze
   the plan; review `plan.execution` (revision, package digests, interpreter,
   record digest) and the plan digest.
5. A separate operator authorization of that exact digest, plus the registry
   lease and queue revalidation options.
6. One `run`, then inspect the durable outcome: `structured_result.files`
   against an independently computed SHA-256 and byte count from the committed
   bytes, `execution.verified`, `custody`, lease release, and
   `source_revision_after == source_revision_before`.
7. A sanitized result with task id/revision, commit, manifest and plan digests,
   expected and observed hashes, terminal state and evidence limits. Raw
   output, private paths and tokens stay out of Git.

`hash-files` is a controller procedure: the canary proves intake, planning,
binding, lease and result return, but it executes reviewed script text over
accepted bytes rather than importing the checkout. A canary that imports the
workspace should use `repository-audit` or `portable-tests` and therefore
requires the qualified environment described above.

Duplicate dispatch, wrong token, untrusted ref, changed bytes and superseded
revision must be demonstrated with synthetic controls first. Unknown or
interrupted outcomes remain uncertain and are not replayed.
