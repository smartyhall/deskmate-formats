# Windows 10 synthetic Git-to-Codex dispatch validation

**Synthetic S2 vertical slice passed. Real S2 remains unverified and was not
executed.** The implementation checkpoint is
`77f1dca289cf2d0647b9027d17f8b1f97e180cb6`, based on fetched `origin/main`
`3f5622d534f800312e1a55a6dac47ba8522cc36c`. The latter contains the independently
reported [real S0 success](codex-supervisor-s0-second-live-result-20261116.md).
This assignment made zero real app-server launches, model turns or emulator
connections. It did not repeat the native S0 experiment.

The [runbook](codex-supervisor-s2-live-dispatch.md) describes the manual commands,
scope, proposed first task and separate authorization handoff. The
[structured evidence](../evidence/supervisor-s2-text-dispatch-20261116.json)
records command results, hashes, runtime, complete synthetic summary and selected
private receipt sizes/hashes. Original command/stdout/stderr and HTTP evidence
remain in the protected archive named `s2-git-dispatch-20261116` outside Git.

## Installed implementation and checks

Runtime: Windows 10 build 19045, Python 3.13.17, SQLite 3.50.4, jsonschema 4.26.0,
Git 2.56.0.windows.4. All **55 installed project Python modules**, and the pinned
schema, independently byte-matched their Git blobs at the checkpoint. Tests use
the installed wheel, including isolated Python subprocesses; no source-path
injection supplies the worker. The schema pin remains
`c28048281174969346b83cfc30bd05523da1d608a73375abfcc86040309b5bb9`.
The native executable pin is inherited unchanged; no real executable/version
preflight or runtime credential test was repeated in this synthetic assignment.

| Validation | Actual result |
| --- | --- |
| Full portable suite | **412 passed**, 536.305 unittest seconds; 537.4069275000365 command host seconds. Includes all **95 Supervisor tests**. |
| New S2 tests | All 13 pass in the full suite, including the production live CLI with only native identity/image substituted by the installed synthetic peer. |
| Focused run and correction | Initial 95-test run had one test error: an already-prepared claim correctly refused before the test's expected stale-source error. The test now uses a fresh claim. Targeted rerun passed in 8.238 unittest seconds, then the complete 412-test run passed. No production code changed for this correction. |
| Windows deployment checks | 31 tests, 4.961 unittest seconds; 2 existing Windows symlink-permission skips. |
| Ruff / REUSE | Passed; per-file notices cover new code, task metadata and documentation. |
| Build / installation | Wheel and sdist built; installed imports, assets and every CLI entry point passed. Binary research fixtures remain excluded from both distributions. |
| Repository audit | Passed; no private evidence, commercial software or unlisted binary inputs committed. |
| Git integrity / whitespace | `git fsck --full` and diff checks passed. Existing dangling objects were reported without integrity failure. |

The wheel used for execution was 215,491 bytes, SHA-256
`a8ef831f3baef5618b82155202b7556311ded256408c210212e044afcb89eb66`.
Its module bytes match the checkpoint. The original build and development logs
are retained, including the earlier synthetic protocol allowlist omission fixed
before this checkpoint. Subsequent documentation/evidence packaging does not
change the verified Python implementation.

## Actual installed CLI demonstration

`tools/experimental/supervisor_offline_demo.py` was run against the installed
package and a newly created private repository/queue/state. Command UTC interval:
**2026-11-16T06:36:42.606323Z to 06:36:58.589983Z**, measured command elapsed
**15.982902600080706 host seconds**. The owner's separate lifecycle interval was
**0.4685420000459999 host seconds**. These measure different intervals.
Attributable emulated time was **0 ms**; no guest counter was measured.

The deterministic trust anchor was `d7b89a38b670b71df6d75e0a70781b1006418b29`,
task commit `4253541a8a33fa52c31591f90c1ed5bb4196943d`, manifest blob
`3f9edd86ac4196de4fe3d2885070edf0b7ffc3e3`. The 429 manifest bytes had SHA-256
`1e7321668d403fdd0664999bb3cf4b2e11551d8febc372d35e0848cda76b8008`.
The reviewed synthetic document's SHA-256 was
`90936bf93861b8a0dbfabe7c349a3449874de438fb54268d28c160bb7e4433a7`.
It describes blue records with seven fields and green records with nine.

Observed sequence:

1. Git commit, trusted discovery and explicit S1 acceptance; no worker started.
2. S2 preparation and complete offline inspection/validation; zero model turns.
3. Mismatched dispatch digest refused before an attempt.
4. Separate correct dispatch digest started one owned synthetic child. Exactly
   `thread/start` and `turn/start` were recorded, both completed. The exact reviewed
   task/document context appeared in the peer's saved user message. The response
   processed that content, including the document's line count, hash and excerpt.
5. Terminal/full-history/response checks passed; the durable outcome was completed,
   marked for operator answer review, and the direct child was verified stopped.
6. A second dispatch was refused. Private data hashes did not change.
7. Actual loopback HTTP returned 200 for events/agents, 405 for event POST, and
   404 for dispatch/operations. Queue, ledger, outcome and peer hashes remained
   unchanged. Public events excluded prompt, answer, native IDs and private paths.

The frozen prompt SHA-256 was
`532e13daf9eecfb9a4e5b5d70c602bfda109e6a2abd3e8efbd9298299ae33100`;
the response SHA-256 was
`426517d811d91862ce12c22f5a0380c4ad401d9d7c3b13d3da153607672045a1`.
The structured evidence publishes the eligible synthetic response and private
record hashes. This is deterministic synthetic context processing, not a research
answer from a real model.

## Limits and real experiment handoff

The regression matrices cover unaccepted/rejected tasks, stale/superseded sources,
expiry, incomplete dependencies, wrong/missing grants, changed plan/model/prompt/
implementation, lost acknowledgments, interruption/child exit, unexpected tools/
approvals, terminal/history mismatch and duplicate attempts. Read-only HTTP tests
cannot accept or dispatch. No synthetic pass establishes native S2 acceptance,
factual correctness, confinement, descendant cleanup, provider cancellation or
power-loss durability. Uncertain operations remain fenced, without replay.

No implementation blocker was found in the synthetic path. A real run still
needs independent PR review, a matching reviewed installation/source tip, explicit
S1 acceptance, native/auth preflight and the exact-plan dispatch/model/lab grants.
The proposed `s2-canary-evidence-analysis` revision 1 is committed for review,
with no acceptance or dispatch. Its two existing eligible documents render to
17,802 prompt bytes, below the 32 KiB limit. The runbook supplies its answer
criteria and manual handoff. Issue #86 remains open until an actual Git-delivered
model result has completed and been independently reviewed. No producing-worker
merge or real demonstration is part of this assignment.
