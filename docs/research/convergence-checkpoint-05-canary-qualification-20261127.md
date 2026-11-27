# Convergence checkpoint 05 — authorized single canary execution

**Status: one authorized, source-bound deterministic execution completed and
returned a result that exactly matched the independently established
expectation. Resource custody was exercised under a registered campaign lease
and released. Process-tree custody after exit was not proven.**

This record continues the [issue #204](https://github.com/smartyhall/deskmate-formats/issues/204)
canary inside [issue #213](https://github.com/smartyhall/deskmate-formats/issues/213).
It reports a completed laboratory run; it is not a convergence declaration and
carries no execution authority.

- Campaign: `convergence-02-trusted` (campaign `convergence-02`)
- Repository: `smartyhall/deskmate-formats`
- Base revision: `e72c97ca47720fe38e32a2b8a37dff6202cda4a3` (merge of PR #218)
- Provider: Freebuff, interactive local desktop session. No model API call, no
  provider endpoint contacted, no emulator used, no unattended dispatch.
- Mechanism: the existing `deskmate_formats.supervisor` trusted-intake queue,
  deterministic plan, execution and campaign-registry components. No parallel
  task format, executor, registry or service was introduced.
- Sanitized usage receipt:
  [freebuff-convergence-checkpoint-05-20261127.json](../../evidence/agent-usage/freebuff-convergence-checkpoint-05-20261127.json)

## 1. Scope and boundary

Performed, once each:

1. Revalidated the frozen plan, the accepted candidate, the trusted checkout,
   the qualified campaign interpreter and the absence of any prior attempt.
2. Initialized a dedicated private campaign registry, established that no other
   registry or campaign claimed the standalone checkout, and registered
   `convergence-02-trusted` with its base commit.
3. Reconciled the execution proposal so that the deterministic mechanism itself
   acquires and releases `worktree:convergence-02-trusted`.
4. Executed the frozen plan exactly once with queue revalidation and a
   900-second lease.
5. Inspected the durable attempt records, the queue and the final registry
   state, and compared the observed result against a value established before
   dispatch.

Not performed: a second execution or replay, another deterministic task, a
workspace-bound procedure, plan regeneration, candidate re-acceptance, any
emulator or model-provider operation, a trusted-branch advance, a manifest
change, or a shared baseline tag.

## 2. Identities

| Field | Value |
| --- | --- |
| Task | `github-hash-canary` |
| Revision | `1` |
| Idempotency key | `github-hash-canary-1` |
| Source commit and trust anchor | `e72c97ca47720fe38e32a2b8a37dff6202cda4a3` |
| Trusted branch | `canary/trusted-source` (direct ref, no upstream) |
| Manifest path | `ops/tasks/github-hash-canary.json` |
| Manifest blob | `369bdc3196b63c6cf84da542bc64b0143a480346` |
| Manifest SHA-256 | `16d17ba48d1f7bcba2192caa4959690a2a30efa4104f5be8f17d420eeafe7ae0` |
| Procedure | `hash-files` (fixed reviewed script; no repository code executed) |
| Arguments | `{"paths": ["README.md"]}` |
| Resources | `["source-read"]` |
| Timeout | 300 seconds (unchanged; the lease is longer than the procedure) |
| Frozen plan SHA-256 | `5681fe8c8fa35d5425651e5fa0e7ee83299f617e6c97b9ab953390d2d3e7b0ba` |
| Controller implementation | `deskmate_formats.supervisor` SHA-256 `b8e4d08237d59cc45e6a0e37bceee50a21452d97a7ef0331ff8d9f5922972e6d` (33 modules) |
| Supervisor Git tree at the pin | `7de95935d6bb1a6a408cfe3526d2f71ed0418523` |
| Interpreter | CPython 3.13.17 in the qualified campaign virtual environment; executable digest recorded privately |
| Attempt | opaque `55d1057917354c3f93a1092ea9322bc4`, frozen plan only |

The **plan SHA-256 is a historical evidence identifier for one consumed
attempt**, as issue #204 requires. It is not an execution grant: replay of this
attempt is refused, and any future execution would need a new plan, a new
authorization and a new operator decision.

## 3. Chronology (UTC)

| Time | Event |
| --- | --- |
| `2026-11-27T22:48:06Z` | Candidate discovered at the frozen tip (checkpoint 03) |
| `2026-11-27T23:20:26Z` | Acceptance recorded: sequence 1, `accepted` |
| `2026-11-27T23:20:37Z` | `prepare-task` froze the plan in a new attempt directory |
| `2026-11-27T23:20:55Z` | Plan digest independently recomputed (checkpoint 04) |
| `2026-11-27T23:31:03Z` | Dedicated registry initialized; campaign registered |
| `2026-11-27T23:31:42Z` | Single authorized dispatch began |
| `2026-11-27T23:31:43Z` | Attempt fenced (`attempt.json`); child spawned |
| `2026-11-27T23:31:44Z` | Child exited 0; outcome `completed`; lease released |
| `2026-11-27T23:31:44Z` | Registry confirmed free of leases and takeovers |

Acceptance and preparation happened in earlier checkpoints; this checkpoint did
not repeat either.

## 4. Procedure and resolved execution

The reviewed `hash-files` procedure assembles its argument vector internally; no
caller-supplied executable, argument vector or shell fragment is accepted. The
resolved vector was:

```
<qualified campaign interpreter> -I -c <reviewed hash script> 67108864 268435456 README.md
```

The script opens the named file with `O_RDONLY|O_BINARY|O_NOFOLLOW`, verifies it
is a regular file with `fstat`, hashes it in 1 MiB chunks, and prints one JSON
line. Review of the resolved script found no write or delete call, no
`subprocess`/exec/spawn, no network module, no workspace, `importlib` or `runpy`
import, and no environment mutation. `-I` isolates the child from
`PYTHONPATH` and user site-packages. The execution source was `controller`, with
no workspace import: the accepted checkout is bound as the working directory and
as hashed input only.

## 5. Expected result, established before dispatch

| Field | Value |
| --- | --- |
| Path | `README.md` |
| Git blob | `b2b3d17a0a70b94b5ae231feba319556bbff6430` |
| Bytes | `22079` |
| SHA-256 | `779b499e3760045f336151fa3910ce3abcba4836f2632e22b88a441583e86773` |

This value was computed from the committed blob at the pinned revision with
`git cat-file`, reconfirmed equal to the working-tree bytes immediately before
dispatch, and recorded in checkpoint 04. It was never read back from the
execution result.

`README.md` carries `text` and `eol=lf` attributes, so its checkout bytes equal
its blob bytes. The manifest file, by contrast, is checked out with CRLF under
`* text=auto` plus the host `core.autocrlf=true`: committed 946 bytes of LF
against 964 worktree bytes. Trusted intake reads the committed manifest blob, so
that conversion does not affect this candidate. Nothing was normalized or
rewritten to make the two agree.

## 6. Observed result

Terminal state `completed`, reason `exit-zero`, exit status `0`, elapsed
`0.345` seconds, no timeout and no cancellation. The child wrote one stdout line
of 129 bytes and no stderr; the bounded stream receipt was not truncated.

| Field | Expected | Observed | Match |
| --- | --- | --- | --- |
| Path | `README.md` | `README.md` | yes |
| Bytes | `22079` | `22079` | yes |
| SHA-256 | `779b499e…6773` | `779b499e…6773` | yes |

Execution receipt summary:

- `source`: `controller`; `executes`: `reviewed-supervisor-script`.
- Controller implementation digest in the receipt: `b8e4d082…2e6d`, equal to
  the plan's binding.
- Package digests: tree `9f733f80…8b34`, `python` `98794053…460e`.
- Child report: none required, because no workspace code was claimed.
- Artifacts: none; the attempt's artifact directory stayed empty.

Durable attempt records: `attempt.json` (plan digest and start time),
`child.json` (process claim), `outcome.json` (the full receipt above),
`progress.jsonl` (started and finished events), `stdout.bin` and `stderr.bin`.

## 7. Queue revalidation and source integrity

- Queue `b34c0fb3f53d4967b67cf4a3196d3c62`, integrity check `ok`, exactly one
  record: sequence 1, `github-hash-canary` revision 1, `accepted`, resolved
  `2026-11-27T23:20:26Z`. Execution does not write to the queue; its digest was
  unchanged by the run.
- The plan's acceptance binding (queue id, sequence, task, revision,
  idempotency key, review token, source provenance) was revalidated from the
  queue before dispatch, and the new composition was accepted only because the
  binding still matched.
- Source revision was `e72c97ca47720fe38e32a2b8a37dff6202cda4a3` before and
  after the run.
- `git status --porcelain --untracked-files=all` was empty before and after, the
  checkout remained clean, no tracked file was modified and no untracked file
  appeared.
- The bound input digest `d41201811b70523eeed45f934aa93f290d3ea9ee02951b5c8427547977837e53`
  was identical before and after.
- The trusted branch tip did not move and no ref was created or changed.

## 8. Registry custody and lease

No registry existed before this checkpoint, so nothing else claimed the
standalone checkout. A dedicated private registry was initialized and one
campaign registered:

| Field | Value |
| --- | --- |
| Campaign | `convergence-02-trusted` |
| Provider | `freebuff` |
| Branch | `canary/trusted-source` |
| Base commit | `e72c97ca47720fe38e32a2b8a37dff6202cda4a3` |
| Resource | `worktree:convergence-02-trusted` |
| Lease identity | `worktree:84635729fdeaa190cbd1f0804e6263b5` |
| Lease duration | 900 seconds (procedure timeout unchanged at 300) |

The lease identity is derived from the canonical path of the registered
worktree, not from a caller-chosen label, so two campaigns naming the same
directory collide instead of holding independent "exclusive" leases. Both a
recomputation made for review and the controller's own identity calculation
produced the same value, and the lease was confirmed free before dispatch.

The executing deterministic process acquired the lease itself and released it
from a `finally` block; no separate process took a lease and no lease was
transferred. Final state: zero leases, zero takeovers, zero competing claims,
campaign still `active`.

**Observed versus inferred.** Continuous custody was not directly observed. The
invocation lasted 1.4 seconds, and the lease record is deleted on release, so no
sample of the transient lease exists. Acquisition is supported by control flow
(the reservation runs before the child is spawned and a conflict would have
raised instead of spawning) and by the zero exit with a child record and a
completed outcome. Release is supported by the same control flow (release runs
in a `finally` block whose failure would have produced a non-zero exit), by the
empty lease map afterwards, and by the registry file's modification time falling
inside the run window. These are conclusions supported by the executed control
flow and the final state, not observations of the lease itself.

## 9. Qualification assessment

Scoped to what this canary actually exercised. The authoritative criterion list
remains the one in issue #204; this table reports the dimensions the campaign
claimed to qualify.

| Dimension | Result | Evidence |
| --- | --- | --- |
| Trusted GitHub-to-laboratory intake | pass | Accepted revision 1 recorded against the exact reviewed blob and commit |
| Source binding to the exact revision | pass | Tip, anchor and ancestry re-verified; blob and digest matched; HEAD unchanged before and after |
| Deterministic execution planning | pass | Frozen plan; digest recomputed; procedure and arguments taken from the accepted manifest, not from the caller |
| Authorization of one attempt only | pass | Digest matched; attempt fenced once; replay refused by design and covered by a published negative control |
| Resource custody: lease acquisition and release | partial | Registration and free final state are directly observed; the transient lease and its acquisition/release are inferred from control flow, not sampled |
| Process-tree custody after exit | unknown | The controller recorded `custody: unobserved`, `no-tree-handle`, `descendants: unknown`; the child exited 0 and its PID no longer exists, but an empty tree was not proven |
| Independently predictable result | pass | Expected digest derived from the source before dispatch and matched exactly |
| Durable result return | pass | Structured result, stdout receipt, outcome record and progress record all persisted and inspected |
| Absence of source mutation | pass | Clean before and after; no tracked modification; branch stationary |
| Sanitized evidence return to GitHub | this pull request | Record plus provider-neutral receipt; private runtime state stays outside Git |

The file hash alone is therefore necessary but not sufficient. Two dimensions —
transient-lease observation and post-exit process-tree emptiness — are reported
as partial or unknown rather than converted into a pass.

## 10. Synthetic controls and existing coverage

No new destructive or duplicate-dispatch test was run against the real attempt.
The negative controls published in
[checkpoint 02](convergence-checkpoint-02-canary-preparation-20261127.md#5-negative-controls)
already cover the refusal paths this run depends on: a wrong review token, a
fabricated token at preparation, discovery at an ancestor instead of the tip, a
foreign origin identity, a symbolic trusted ref, changed manifest bytes at a
recorded revision, a tracked input changed after freezing, a superseded
revision, a second dispatch of the same plan (`attempt already started; replay
is forbidden`), re-preparation into an existing attempt directory, and a run
authorized with a foreign digest.

Portable coverage for the components used here already exists in
`tests/portable/test_supervisor_campaigns.py`,
`test_supervisor_deterministic.py`, `test_supervisor_deterministic_cli.py`,
`test_supervisor_task_queue.py`, `test_supervisor_task_git.py`,
`test_supervisor_process_tree.py` and `test_supervisor_job_object.py`, and runs
in the required CI matrix on the base revision. This checkpoint added
documentation only and did not modify those components.

## 11. Limitations and unresolved findings

1. **Transient lease not sampled.** Duration and identity are recorded, but the
   lease was never read while held. A reviewer wanting direct custody evidence
   would need a longer or instrumented attempt, which this authorization did not
   permit.
2. **Process-tree emptiness unproven.** The termination record reports
   `owner: stopped`, `descendants: unknown`, `enumeration: incomplete`,
   `reason: scope-loses-orphans` and `authority: no-tree-handle`. Operationally
   the child exited 0 and its PID no longer exists, and no new process survives;
   that is weaker than a proven empty tree.
3. **Plan digest is not publicly recomputable.** The plan binds private host
   identities (absolute paths, interpreter and package digests), so only its
   digest is published. A verifier can confirm that the durable outcome records
   the authorized digest and that the attempt record matches it, but cannot
   rebuild the plan from public data.
4. **The trusted inbound path depends on private runtime state.** The accepted
   task, queue and attempt live outside Git by design. The public record is
   sufficient to check the source-side facts and the reported outcome, not to
   replay the laboratory.
5. **No provider usage telemetry.** Token, context and quota measurements were
   not observable and are recorded as absent, never as zero.
6. **Scope.** This qualifies the controller-procedure path. Workspace-bound
   execution, `portable-tests` and `package-build` behaviour were not exercised
   here.

## 12. Independent verification

Anyone can confirm the source-side facts from public data:

```bash
git cat-file blob b2b3d17a0a70b94b5ae231feba319556bbff6430 | wc -c
git cat-file blob b2b3d17a0a70b94b5ae231feba319556bbff6430 | sha256sum
git rev-parse e72c97ca47720fe38e32a2b8a37dff6202cda4a3:ops/tasks/github-hash-canary.json
git cat-file blob 369bdc3196b63c6cf84da542bc64b0143a480346 | sha256sum
```

The controller implementation digest is reproducible from the source tree at the
pinned revision, over the reviewed supervisor modules in sorted order:

```bash
python - <<'PY'
import hashlib
from pathlib import Path
d = hashlib.sha256()
mods = sorted(Path("src/deskmate_formats/supervisor").glob("*.py"))
for p in mods:
    d.update(p.name.encode("utf-8") + b"\0")
    d.update(hashlib.sha256(p.read_bytes()).digest())
print(len(mods), d.hexdigest())
PY
```

## References

- [Issue #204](https://github.com/smartyhall/deskmate-formats/issues/204) — canary scope
- [Issue #213](https://github.com/smartyhall/deskmate-formats/issues/213) — convergence campaign
- [Checkpoint 02 — canary preparation](convergence-checkpoint-02-canary-preparation-20261127.md)
- [`ops/tasks/github-hash-canary.json`](../../ops/tasks/github-hash-canary.json)
- [`src/deskmate_formats/supervisor/deterministic.py`](../../src/deskmate_formats/supervisor/deterministic.py),
  [`procedures.py`](../../src/deskmate_formats/supervisor/procedures.py),
  [`campaigns.py`](../../src/deskmate_formats/supervisor/campaigns.py),
  [`task_queue.py`](../../src/deskmate_formats/supervisor/task_queue.py)
