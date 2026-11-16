# S3 bounded source editing and local checkpoint

Implementation and synthetic validation only, based on reviewed main
`9f3e38ee0fa93c6776d2d57d6a51a04c18596e7c` (merged S2 result PR #98).
No real supervisor-dispatched model turn, emulator operation or remote action by
the supervisor is authorized or performed. See the [validation receipt](../evidence/supervisor-s3-20261116.json).

## Contracts reused

S3 reuses S1 trusted Git discovery and immutable acceptance, the private queue,
S2 receipt binding/claim/state lock, S0 installed-code/native/schema pins,
owned AppServer/Operations ledger, permanent attempt fence, terminal/full-history
verification, final response preservation, direct-child teardown and Observatory
journal. There is no scheduler, approval sender, restart, corrective turn or
remote Git publisher. S2 explicitly refuses source-edit-v1; version-1 manifests
and the text-analysis-v1 policy retain their original behavior.

`deskmate-supervisor-s3` explicitly selects source-edit-v1 and requires a
version-2 manifest. Version 2 retains all version-1 common fields, `offline`
request label, document references, size/path/expiry/revision rules and adds
exactly one required `development` object:

| Field | Contract |
| --- | --- |
| `source_revision` | Full 40-character reviewed Git commit; must be an ancestor of the accepted task commit. It is the workspace/checkpoint parent. The accepted task commit separately binds the manifest and instruction documents, avoiding a self-referential commit hash. |
| `modify` | Up to 16 exact existing regular, non-executable file paths. |
| `create` | Up to 16 exact absent file paths; no wildcard/directory expansion. All scoped paths are distinct ignoring case. |
| `acceptance` | 1–8 nonblank criteria, at most 512 characters each; the description supplies the development objective. |
| `test_profiles` | Distinct named profiles: `portable-full` and `synthetic-unit`; an empty list explicitly requests no project tests. |
| `deliverables` | Exactly `["final-response", "local-checkpoint"]`; no push, PR or merge. |

File scopes allow only `src/**/*.py`, `tests/portable/**/*.py`, and `docs/**/*.md`.
New files must carry eligible inline SPDX declarations because sidecar creation
is outside this initial scope. Resources are exactly `source-read`, `source-edit`,
plus `portable-tests` iff test profiles are requested. These are requests, not
execution grants. Version 2 initially refuses dependencies at S3 preparation.
Unknown keys, shell commands, config, executables, environment, sandbox overrides,
credentials, network permissions and approval rules have no manifest fields.
Prose cannot select execution settings. An operator selects native image,
model, effort, experimental-lab policy and exact-plan grants independently.

## Workspace and custody

Preparation rechecks acceptance and source material under the existing locks.
Before cloning it writes a permanent workspace reservation. It creates one
UUID-named standalone execution clone with `git clone --no-local --no-checkout`,
checks out exactly source_revision on `s3/<uuid>`, removes other local/remote
refs and the origin. Objects are copied, with no hardlinks or alternates.
It never edits the trusted clone's main ref or decision metadata. An initial
status must be clean; it never repairs or replaces an existing workspace.
A partial preparation retains its reservation/clone and requires inspection.

The immutable private plan contains task/revision/acceptance sequence, original
commit/blob/SHA-256/review token, source commit, source text/blob/hash, workspace
UUID/path/branch/initial HEAD, all initial file identities and tracked index,
all initial Git metadata hashes, execution generation, evidence/output paths,
model/policy/environment/native/schema/installed-code pins and deadlines.
Source and document context is bounded to 32,768 UTF-8 bytes; oversized tasks
are refused. Original bytes stay in the trusted Git object store.

Before dispatch, acceptance, exact task tip, source content, dependencies policy,
installed-code pins and a pristine workspace are rechecked. Git metadata,
including config/index/refs/objects, must remain identical until supervisor
staging. Filesystem redirects, special files and hardlinks are refused. New
ignored files are included in the full filesystem inventory. There is no reuse,
automatic cleanup or discard command. Retain the whole private root and clone;
after review/archive and verified worker exit an operator may explicitly remove
the named disposable clone. Preserve queue, reservation, attempts and receipts.
Deleting custody records or choosing a new state root defeats cooperating-owner
deduplication; this is not a hostile-principal security boundary.

The worker's cwd is the disposable clone; the existing sanitized S0 environment
places its home/auth/output outside it. S1 queue and S2 grants are never supplied
in the task prompt. The same Windows account can still access VM-local files.
This arrangement reduces ordinary Git coupling, **not** OS access rights. The
[accepted experimental posture](experimental-lab-operating-posture.md) applies;
no alternative VM, restricted-user campaign or confinement claim is added.

## Version-pinned native editing profile

Inspected native schema remains Codex **0.166.0**, profile SHA-256
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`;
no protocol parameter allowlist or schema upgrade was needed. Thread cwd comes
from the owned child's launch directory and config supplies `workspace-write`.
Pinned source is [OpenAI Codex 6ff1e1ca](https://github.com/openai/codex/tree/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856).

- `core/src/tools/spec_plan.rs:1243` registers shell tools only with
  `Feature::ShellTool`; line 1426 registers ApplyPatchHandler separately when
  model metadata has `apply_patch_tool_type`. `features/src/lib.rs` declares
  `shell_tool`, `js_repl`, `code_mode`, `multi_agent`, `multi_agent_v2` and
  `codex_git_commit`. These six features are explicitly disabled in S3 config.
- `core/src/tools/handlers/apply_patch.rs` verifies patches and routes them to
  the selected environment filesystem/runtime and policy path. This supports
  native apply_patch editing; it is not an RPC for arbitrary source writes.
- The pinned SandboxPolicy schema supports `workspaceWrite`, `writableRoots`,
  `networkAccess`, `excludeTmpdirEnvVar`, `excludeSlashTmp`.

S3 retains `approval_policy="never"`, reviewer `user`, disabled web search,
empty MCP table, staged single auth file and provider/model/effort pins. Its
workspace-write config disables network access and excludes temporary roots.
Before turn submission the reported policy must match workspace cwd, model,
effort, provider, approval/reviewer, persistent empty thread, workspaceWrite,
no additional writable roots, network false and both tmp exclusions true.
No new RPC field is silently admitted. Source contents are supplied in context,
so the worker needs no shell read/test capability. Fixed developer instructions
permit apply_patch only on the exact file scopes; tests/Git are supervisor-owned.

Observed/returned/history items accept user/agent/reasoning and scoped fileChange
only, with update/add kinds and no moves/deletes. Completed persisted history
must include completed editing activity, exact input and final response, one
completed turn and idle thread. Evidence retains actual item notifications and
history separately from the final answer. Approvals are never answered;
unexpected commands/tools, failures, ambiguous acknowledgments or unsupported
activity stop execution and retain evidence. The existing ledger/attempt fences
prohibit replay. Native editing has **not** been executed: model-specific
apply_patch availability, effective feature settings and Windows sandbox behavior
remain runtime assumptions for separately authorized review. Post-event checks
cannot prevent a side effect that already happened. OS confinement, cancellation,
spending caps, descendants and power-loss durability remain unproved.

## Validation and checkpoint

After verified owned-worker completion/teardown, the supervisor inventories the
actual filesystem and Git diff against source_revision. It refuses unauthorized,
unexpected, missing, executable, binary, non-UTF-8 or oversized changed files and
Git metadata mutation. Tests run in that workspace using the selected absolute
Python interpreter, with workspace `src` on PYTHONPATH, bytecode disabled and a
small environment that omits inherited credentials/Git overrides. Commands are
fixed by installed code, never parsed from task prose:

- `portable-full`: Python `-m unittest discover -s tests/portable -v`.
- `synthetic-unit`: Python `-m unittest discover -s tests/portable -p test_s3_sample.py -v` (offline fixture rehearsal).
- Always: installed, byte-identical project publication audit under `-I`, pointed
  at the workspace; Python `-m reuse lint`.

The packaged audit is an exact copy of tools/audit_repository.py, checked by a
regression test; it includes existing proprietary/binary/credential/fixture
checks. Worker changes cannot replace the installed auditor. Each step retains
argv, absolute interpreter/hash, cwd, exit status or timeout and output/hash
privately, with a 600-second per-command deadline. All requested steps receive
outcomes even if an earlier step fails. Arbitrary Python tests inherently run
code with VM permissions; operator review/test-profile selection is meaningful.
A failure retains diagnostics without discard or corrective model turn.

Checkpointing requires a separate exact-plan grant, recorded with the dispatch
attempt. A permanent checkpoint intent precedes tests/staging. It rechecks file
identities after validation, stages sorted exact paths, verifies each staged blob
hash/mode and file set, records the tree, creates an object with `commit-tree`
and exactly the reviewed source parent, records that object, then compare-and-
swaps only the task ref. It verifies parent and final clean status before claiming
success. Durable metadata binds task/revision/source, parent/tree/commit and file
hashes. Partial staging/object/ref update, interruption or lost acknowledgment
retains an incomplete receipt, never permission to retry. Operator review may
recover an already-created object without another automatic commit attempt.
No supervisor code pushes, creates a PR, merges or changes main.

Observatory receives fixed sanitized S3 outcome notes only, after the durable
checkpoint outcome. Publication failure cannot reopen dispatch/checkpoint.
The existing HTTP viewer has no S3 control routes.

## First proposed development assignment

[calendar-listing-alarm](../../ops/tasks/calendar-listing-alarm.json) proposes
showing decoded alarm state in the Calendar text listing, with regression tests
for True/False/None and internal-record exclusion. It touches only calendar/cli.py
and the existing test_calendar.py, uses synthetic builders and the full portable
profile, and needs no dependencies, network or proprietary inputs. The source
commit is the reviewed S2-result main above. The manifest is **proposed only**:
not discovered into a real queue, accepted, prepared or dispatched. Review its
source revision again after merge; changing it requires a newly reviewed task
revision if the original has been accepted. The old reviewed source is a valid
explicit parent and intentionally excludes this later supervisor implementation.

## Eventual manual commands and independent grants

Install the independently reviewed implementation wheel using the existing
[operator guide](codex-supervisor-operator-driver.md). Keep the existing queue
and trusted standalone clone; manually fetch/update its protected source after
review. Never edit a frozen plan. All output/paths below are private.

```powershell
$task = 'calendar-listing-alarm'
$path = "ops/tasks/$task.json"
$tip = git -C $checkout rev-parse refs/heads/main
$candidate = deskmate-supervisor-task --queue $queue discover $tip $path | ConvertFrom-Json
# Independently review exact task commit/blob/hash, source_revision, source files,
# optional documents, scopes, acceptance criteria and selected tests.
'Reviewed exact source-editing task and inputs' | deskmate-supervisor-task --queue $queue accept $tip $path --review-token $candidate.review_token --reason-stdin
# Explicit operator selections, not values from Git prose:
$grant = deskmate-supervisor-s3 --state $state prepare-live --queue $queue $task 1 --accepted-review-token $candidate.review_token --task-class source-edit-v1 --plan-local-checkpoint --executable $native --profile experimental-lab --auth-file $auth --model $operatorModel --effort $operatorEffort | ConvertFrom-Json
deskmate-supervisor-s3 --state $state inspect $grant.claim
deskmate-supervisor-s3 --state $state validate --queue $queue $grant.claim
# STOP for independent exact-plan review and separate operator authorization.
$digest = $grant.plan_sha256
deskmate-supervisor-s3 --state $state dispatch-live --queue $queue $grant.claim --authorize-dispatch $digest --authorize-checkpoint $digest --authorize-live-plan $digest --accept-lab-risk $digest
deskmate-supervisor-s3 --state $state inspect $grant.claim
```

The operator must separately approve S1 acceptance, exact-plan dispatch, one
selected-model/effort invocation, experimental VM-local risk and a scoped local
checkpoint. The four digest arguments are intent confirmations, not signatures
or authority conveyed by learning a hash. The final dispatch command is **not
authorized by this implementation assignment**. No S0 canary is repeated.
For offline rehearsal, use the installed synthetic demo and a fresh disposable
queue/task, never the proposed real task's permanent claim.

```powershell
python tools/experimental/supervisor_editing_demo.py --private-root $uniquePrivateDemo
python -m unittest discover -s tests/portable -p 'test_supervisor*.py' -v
python -m unittest discover -s tests/portable -v
python -m unittest discover -s deployment/windows10/tests -v
python -m ruff check src tests/portable tools
python -m reuse lint
python -m build
python tools/install_wheel.py
python tools/check_install.py
python tools/audit_repository.py
```
