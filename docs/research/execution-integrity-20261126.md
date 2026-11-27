# Execution and lease integrity — review corrections, 2026-11-26

**Scope:** the independent review of PR #191 at `573f479` raised nineteen
findings against the deterministic backend, the campaign registry and the CLI.
This document records, for each one, what the code actually did, why that was
insufficient, what it does now, and the test that demonstrates the difference.

**Method:** read every changed module, reproduced each defect with a focused
test before changing anything where the defect was behavioural, and ran the full
Supervisor suite afterwards. No model turn, provider call, emulator or network
service was used.

**Status vocabulary:** *confirmed* means the finding describes the code as
committed; *partly confirmed* means the claim holds in some paths only;
*not reproduced* is stated plainly where the code already refused the case.

## Summary

| # | Finding | Status | Correction |
| --- | --- | --- | --- |
| 1 | Requested revision may be unestablished | Confirmed | `prepare` refuses when a requested commit cannot be read |
| 2 | HEAD alone does not bind the working tree | Confirmed | Content manifest of procedure inputs frozen in the plan |
| 3 | Interpreter and imported implementation unvalidated | Partly confirmed | Package digest plus resolved module origins, verified before dispatch |
| 4 | Fixed argv conflated with repository execution | Confirmed | `executes` classification on every procedure |
| 5 | Filesystem boundaries not canonical | Confirmed | Link components refused, canonical cwd, artifact tree walked without links |
| 6 | File-size limits not applied | Confirmed | Streaming bounded hash/compare with the declared cap passed as arguments |
| 7 | Package build may reach the network | Confirmed | `--no-isolation` plus index-off environment variables |
| 8 | Resource identity is only a name | Confirmed | Path resources resolve to a canonical identity hash |
| 9 | Reservation rollback can drop pre-existing leases | Confirmed | Two-phase validate-then-commit reservation |
| 10 | Reclaim invents a placeholder owner | Confirmed | Reclaim requires a live new owner identity |
| 11 | Renew/release check only the campaign name | Confirmed | Both require the recorded `(pid, identity)` |
| 12 | Owner termination conflated with descendant termination | Confirmed | Separate owner and descendant probes |
| 13 | Recovery may close a live attempt | Confirmed | Recovery refuses while owner or descendant is alive |
| 14 | Tree termination unqualified | Confirmed | Real parent/child termination tests on Windows and Linux |
| 15 | Trusted-intake binding not in the plan | Confirmed | Acceptance block frozen in the plan and in the outcome |
| 16 | Authorization may be superseded after prepare | Confirmed | Required revalidation immediately before dispatch |
| 17 | CLI exit states collide | Confirmed | Distinct codes for all five outcomes |
| 18 | Output/artifact/durability bounds untested | Confirmed | Bounds enforced and qualification added |
| 19 | Test-harness synchronization | Partly confirmed | Explicit conditions preferred; guards documented |

## 1. Requested source revisions fail closed

The planner accepted `source_commit` and then wrote the plan even when
`git rev-parse HEAD` returned nothing:

~~~python
if source_commit is not None and observed is not None and observed != source_commit:
    raise DeterministicError(...)          # observed is None -> silently accepted
~~~

An unavailable Git identity therefore produced a plan that *claimed* a revision
nobody had checked. `prepare` now refuses:

~~~python
if source_commit is not None and observed is None:
    raise DeterministicError("the requested source revision cannot be established")
~~~

Dispatch separately refuses when a plan that had a Git identity loses it, and
when a plan that had none gains one. A working directory that is not a Git
checkout is still usable, but then the plan records `identity: "unavailable"`
and relies on the content manifest below instead of pretending otherwise.

*Test:* `IntegrityTests.test_requested_revision_that_cannot_be_established_is_refused`.

## 2. The working tree is bound, not just HEAD

`git status` was written into the *outcome*, after execution. Nothing bound the
files the procedure would read, so an approved plan could execute entirely
different source.

Every procedure now declares the inputs it reads or executes
(`portable-tests`: `src/**/*.py`, `tests/portable/**/*`, `pyproject.toml`;
`package-build`: `pyproject.toml`, `README.md`, `src/**/*`, `LICENSES/**/*`;
`reuse-lint`: the tree; named-file procedures: exactly their arguments). The
planner walks them, refuses links and non-regular files, rejects anything that
resolves outside the working directory, and freezes:

~~~json
"inputs": {"patterns": [...], "files": 187, "bytes": 1903211, "sha256": "..."}
~~~

`run` recomputes the manifest and refuses on any difference. A file set that
cannot be bound within the limits (20 000 files, 1 GiB) is refused rather than
partially bound.

*Tests:* `test_changed_working_tree_input_after_authorization_is_refused`,
`test_untracked_executable_input_appearing_after_authorization_is_refused`
(the second adds a new `.md` file matched by the `repository-audit` pattern).

## 3. Interpreter and imported implementation

The plan bound the interpreter's bytes and the eight supervisor modules. It did
not bind the rest of the installed package, and it did not record which module
file each procedure actually imports.

The plan now carries `implementation` (file count, byte count and a digest over
every `deskmate_formats/supervisor/*.py`) and `modules`: the resolved origin and
SHA-256 of each imported module (`unittest`, `reuse`, `build`,
`deskmate_formats.supervisor.repository_audit`). Dispatch re-resolves and
re-hashes them and refuses on drift.

*Test:* `test_changed_implementation_or_revision_is_refused`.

**Honest limit:** hashing the module that Python will import is not the same as
proving the import graph is closed. A transitive import not named by the
procedure is covered by the package digest only if it lives in the supervisor
package.

## 4. Fixed arguments versus repository execution

`portable-tests`, `package-build` and `repository-audit` run code from the
working tree. "No shell and no caller-supplied executable" is true and
insufficient: the reviewed *procedure* is fixed, the *code it runs* is not.

Each procedure now states `executes`: `fixed-script` (hash, compare),
`reviewed-repository-code` (tests, build, audit) or
`third-party-tool-over-repository-data` (REUSE). The classification is in
`descriptor()`, in the plan (`procedure_detail`) and in the catalog the CLI
prints, so an approver sees it before authorizing.

*Test:* `test_running_tests_and_building_packages_are_repository_execution`.

## 5. Canonical filesystem boundaries

The working directory was taken with `Path(value).absolute()`, which normalizes
but does not resolve links; procedure arguments were validated as relative
strings and then opened by the child relative to its own cwd.

Now:

- `_canonical_directory` refuses a working directory reached through a symlink,
  junction or reparse point anywhere in its prefix, and executes in the resolved
  path. A caller who passes the canonical path is unaffected.
- `_input_binding` refuses an input that is a link or not a regular file, and
  refuses one whose real path falls outside the real working directory.
- `_artifacts` walks the artifact tree with `scandir` and refuses links,
  junctions and non-regular files instead of following them, then verifies
  containment.
- The hash and compare scripts open with `O_NOFOLLOW` where the platform has it
  and validate `fstat` of the opened descriptor, not the path.

*Tests:* `test_working_directory_reached_through_a_link_is_refused`,
`test_input_that_is_a_link_is_refused` (skipped where the host cannot create
symlinks; exercised on the Ubuntu CI runner).

**Honest limit:** a check followed by an open is still a race. Removing it
entirely needs `openat`-style descriptor walking, which Python does not expose
portably; `O_NOFOLLOW` narrows it to the final component.

## 6. Declared limits were not applied

`MAX_FILE_BYTES` was declared, documented and exported, but the scripts called
`read_bytes()`. A 4 GiB fixture would have been read into memory.

Both scripts now take the per-file and aggregate limits as their first
arguments — so the numbers are in the plan and visible to a reviewer — and
stream in 1 MiB chunks, aborting with `input exceeds the reviewed size limit`
when either cap is crossed. Comparison opens both files, checks both sizes and
streams, so a mismatch is detected without loading either file.

*Tests:* `test_hash_and_compare_scripts_receive_their_reviewed_limits`,
`test_hash_script_enforces_its_own_limit_when_it_runs`,
`test_binding_refuses_an_input_over_the_declared_limit`.

## 7. Package builds and the network

`python -m build --wheel` creates an isolated environment by default and
installs build requirements from an index. That is a network dependency the plan
never declared.

`package-build` now runs `--no-isolation` and the child environment sets
`PIP_NO_INDEX=1`, `PIP_NO_INPUT=1`, `PIP_DISABLE_PIP_VERSION_CHECK=1`,
`PIP_CONFIG_FILE=os.devnull`, `UV_OFFLINE=1` and `UV_NO_INDEX=1`. The procedure
declares `network: "no-isolation"`.

*Test:* `test_package_build_refuses_isolation_and_offline_variables_are_set`.

**Honest limit:** this prevents the build backend from resolving dependencies.
It is not network isolation. A `setup.py` that opens a socket would still
succeed, and the procedure is classified as repository execution for exactly
that reason.

## 8. Resource identity

Leases were keyed by whatever string the caller typed. Two campaigns could each
hold `worktree:<their own name>` while pointing at the same directory and both
believe they had exclusivity.

Path-like resources (`worktree`, `guest-image`, `evidence`, `build`, `preview`)
now resolve through the registered campaign's own worktree, and the lease is
keyed by `sha256(normcase(realpath))`. Two labels for one directory are one
resource. A path lease must name a registered campaign, because otherwise there
is nothing to resolve.

*Tests:* `test_two_campaigns_naming_one_worktree_cannot_both_hold_it`,
`test_path_leases_require_a_registered_campaign`, and the demonstration section
of `tools/experimental/heterogeneous_workers_demo.py`.

**Registry schema:** the lease record gained `identity`, `session` and `scope`,
so the format is now version 2. A version 1 registry is refused with a clear
message rather than silently reinterpreted; the registry is private operator
state created days ago in this same campaign, and recreating it is cheap.

## 9. Reservation rollback

`reserve` acquired resources one at a time and, on failure, popped every name it
had "taken". When the failing reservation included a resource the same campaign
already held, that pre-existing lease was deleted — silently losing ownership.

`reserve` is now two-phase: it validates every identity, checks each existing
lease against the owner tuple, and only then writes all the records in one
commit. A failed validation writes nothing.

*Test:* `test_failed_reservation_preserves_a_preexisting_lease` (asserts the
original `acquired_at` survives the failed reservation).

## 10. Reclaim with a real new owner

`reclaim` finished with `acquire(..., pid=1, process_identity="reclaimed")`: a
fabricated owner that `verify_process` can never confirm, making the next
reclaim trivially easy.

Reclaim now requires `pid`, `process_identity` and a TTL, and refuses unless the
new owner is a live local process:

~~~python
if probe(pid, process_identity) != "alive":
    raise RegistryError("the new owner identity must be a live local process")
~~~

*Test:* `test_reclaim_requires_a_genuine_new_owner_and_no_surviving_descendant`.

## 11. Renew and release check the identity

Both compared only `campaign`. Any process that could open the registry could
renew or release another process's lease for the same campaign.

Both now require `pid` and `process_identity` and compare the full tuple.

*Test:* `test_renewal_and_release_require_the_recorded_identity`.

## 12. Owner death is not descendant death

`verify_process` samples one PID. A killed owner whose child kept running looked
`stopped`, and the lease could be reclaimed under a live process.

`supervisor/process_tree.py` adds bounded, read-only tree inspection:

- POSIX: each attempt runs in its own session, and the scan matches `/proc/*/stat`
  session ids, which survive reparenting to init.
- Windows: `ParentProcessId` is static, so the snapshot walk identifies
  descendants even after the parent exits.
- `tree_claim` records a session handle only when the process leads its own
  session. An ordinary shell process gets `scope: "process"`, which says plainly
  that descendants cannot be enumerated.

`Lease` now reports `owner_alive` and `descendants` separately, and reclamation
refuses `descendants: "alive"` and requires an explicit
`--confirm-descendants-stopped` when the tree is `unknown`.

*Tests:* `test_supervisor_process_tree.py`, including
`test_an_owner_that_exited_still_reports_a_living_descendant`, which kills the
owner and asserts the surviving grandchild is still reported.

## 13. Recovery does not close a live attempt

`recover` refused only when the child was `alive`; a missing `child.json` or an
`unknown` probe fell through and closed the attempt.

Recovery now refuses when the owner **or any descendant** is alive, and when the
tree is unknown it records that uncertainty explicitly
(`descendants: "unknown"`, `requires_manual_process_check: true`) instead of
treating it as proof that nothing is running.

*Test:* `test_recovery_refuses_a_live_child` (existing, still passing) plus the
tree tests above.

## 14. Tree termination

Termination already used `taskkill /F /T` on Windows and `killpg` on POSIX, and
the child is spawned with `CREATE_NEW_PROCESS_GROUP` or `start_new_session`. What
was missing was evidence that a grandchild actually dies.

`test_supervisor_process_tree` spawns a real parent that spawns a real child,
kills the parent, and asserts the child survives — then proves that killing the
tree clears it. The timeout and cancellation paths use the same `_stop_tree`, so
the mechanism is shared rather than separately asserted.

**Honest limit:** on Windows, a descendant that breaks away from the process
group or is reparented by a job object is not covered. The report says so rather
than claiming a guarantee.

## 15. Trusted-intake binding in the plan

Three of the review's "preserve" items were absent: `deterministic.prepare`
accepted only campaign, procedure, arguments and a working directory. The queue
id, sequence, revision, review token, source identity and idempotency key lived
only in the acceptance record.

`prepare` now takes an `acceptance` binding, validates that it names the same
procedure and arguments, and freezes it in the plan. The terminal outcome copies
it as `acceptance_binding`, so a receipt can be traced to the exact accepted
revision without consulting the private queue.

*Tests:* `test_plan_binds_acceptance_and_requires_revalidation`,
`test_acceptance_binding_is_visible_in_the_terminal_outcome`.

## 16. Superseded authorization

`prepare-task` could be followed by a new accepted revision, an expiry, or a
withdrawn acceptance, and `run` would dispatch anyway.

A plan with an acceptance block now requires a revalidation callback at
dispatch. The CLI builds it from the queue, calls `deterministic.accepted` again,
and compares `queue_id`, `id`, `revision`, `sequence`, `idempotency_key` and
`review_token` with the frozen binding. Missing the callback is itself a
refusal, so a caller cannot quietly skip the check.

*Tests:* `test_superseded_acceptance_refuses_dispatch_and_reports_it`,
`test_plan_binds_acceptance_and_refuses_without_revalidation`.

## 17. CLI exit states

`run` returned 0 for every outcome, and `status` used 3 for "needs inspection"
while cancellation needed a code of its own.

| Code | Meaning |
| --- | --- |
| 0 | completed |
| 1 | failed |
| 2 | refused (validation, supersession, missing revalidation) |
| 3 | cancelled |
| 4 | timed-out |
| 5 | uncertain |
| 6 | private storage or registry busy |
| 130 | interrupted |

The mapping is a single table (`EXIT_STATES`) so the five outcomes cannot drift
apart again.

*Tests:* `test_supervisor_deterministic_cli.py`, including a real timeout and a
real cancellation observed through the CLI.

## 18. Bounds and durability

- `_write_once` wrote directly to its final name; a crash mid-write left a
  truncated record that would later read as authoritative. It now writes a
  sibling temporary file, fsyncs, renames, and fsyncs the directory on POSIX.
- The artifact walk refuses links and enforces per-file, aggregate and count
  limits.
- Stdout/stderr capture is bounded but the pipe is drained; the tests assert both
  truncation at the limit and exact capture at the boundary.

*Tests:* `test_interrupted_record_write_leaves_no_partial_file`,
`test_artifact_byte_and_count_limits_are_enforced`,
`test_stdout_exactly_at_the_limit_is_not_truncated`,
`test_output_capture_is_bounded_but_the_stream_is_drained`.

## 19. Test reliability

Two earlier failures were fixed by widening hang guards. The review asks for
explicit conditions instead, and that is what the new tests use: they poll for a
*marker* (`spawned`, `attempt.json`, `child.json`) with a deadline and never
infer state from elapsed time.

The remaining fixed guards in `test_observer_codex_http.py` were left alone: that
module is outside this change, and editing five guard sites across three
observer test modules belongs in its own reviewable change. It is listed as a
follow-up.

## A contract change the full suite caught

Extending the procedure descriptor broke a pre-existing test:
`test_supervisor_procedures.py` asserted the exact key set of each catalog
entry, so the five new keys (`executes`, `inputs`, `modules`, `network`,
`limits`) failed seven assertions in the full run even though every module
passed in isolation.

The test was **updated, not relaxed**. It still asserts an exact key set — now
the full one — and additionally checks that `executes` and `network` fall in
their reviewed sets, that `inputs` and `modules` are lists of non-empty strings,
and that `limits` carries exactly `file_bytes`, `total_bytes` and `paths` with
the values the module exports. The argument-vector assertions were tightened the
same way: the reviewed caps must appear in argv at fixed positions, and the
package build must pass `--no-isolation` before `--outdir`.

A second regression surfaced the same way. `test_supervisor_workers.py`
demonstrated a failing procedure by preparing `hash-files` over a file that did
not exist; once named inputs became bindable content, that case is refused at
preparation, before dispatch. The intent was preserved rather than dropped: the
failing-procedure test now runs `portable-tests` over a synthetic worktree with
one deliberately failing test (state `failed`, exit 1, the assertion text in the
bounded stderr excerpt), and a new test asserts the missing-input refusal
directly.

This is the review's point in miniature: a descriptor that quietly grows new
fields is a changed interface, and the test that noticed was right. Refusing an
unbindable input earlier moves a failure from dispatch to preparation, which is
strictly safer — but it is still a behaviour change, and it belongs in a test
with its own name.

## Qualification

| Check | Result |
| --- | --- |
| Supervisor suite, full | 211 tests, OK (2 symlinked-path cases skipped on this host, exercised on Ubuntu CI) |
| Deterministic backend | 24 tests OK (2 symlink tests skipped on Windows) |
| CLI states and supersession | 5 tests OK |
| Procedure limits and classification | 9 tests OK |
| Process tree | 4 tests OK (see the 2026-11-27 review below for the corrected contract) |
| Campaign registry and leases | 12 tests OK |
| Snapshot collector | 9 tests OK |
| Observer HTTP and projection | 15 and 5 tests OK |
| `ruff check src tests/portable tools` | clean |
| `reuse lint` | compliant |
| `tools/audit_repository.py` | passed |

Real, harmless procedures were qualified on Windows: `hash-files` over
repository files, `fixture-compare` over `pyproject.toml`, and the two-campaign
demonstration that refuses a second campaign's claim on the same worktree. Linux
coverage runs in CI on both supported Python versions.

## What is still not claimed

- Cooperating-owner custody, not an operating system security boundary. Nothing
  here confines a process that ignores the registry.
- No network isolation; only a build backend that is told not to resolve.
- Transitive imports outside the supervisor package are not individually bound.
- A symlink race between verification and open is narrowed, not eliminated.
- No unattended service, scheduler daemon or automatic retry exists.

## Second independent review — 2026-11-27

A second review found that one of the corrections above was implemented in a
way that conflated two different questions, and that the CI matrix was right to
fail. The full analysis is in
[process-tree-observation-20261127.md](process-tree-observation-20261127.md).

### Disposition

| Finding | Disposition |
| --- | --- |
| Linux CI failure `'not-found' != 'stopped'` | Corrected in the implementation, not the test. The descendant verdict is no longer derived from the owner verdict. |
| Missing owner treated as descendant evidence | Removed. Owner and tree are sampled and reported separately. |
| Incomplete enumeration reported as an empty tree | `live_pids` now returns a `Scan` with an explicit `complete` flag; `[]` with `complete=True` is the only empty tree. |
| Unreadable or malformed `/proc` records silently absent | Classified as `degraded`; absence is then not proven. |
| Windows count limit used as a completeness proxy | Replaced by an explicit end-of-walk reason (`ERROR_NO_MORE_FILES` versus anything else). |
| Static parent identifiers and PID reuse | Creation stamps exclude pre-owner candidates; a reused owner number is `unknown`, never a guess. |
| A parent chain cannot prove descendants that outlive an intermediate parent | Accepted. `parent-chain` is no longer a durable scope: absence there is `unknown`, and `stopped()` is false on Windows until job-backed execution exists. |
| Observations compared across a reboot | Boot identity is recorded in the claim and already embedded in the process identity, so leases inherit the guard. |
| Unknown tree closed by recovery | Recovery refuses an unobservable tree unless the operator confirms explicitly; the confirmation is recorded. |
| Reclamation on an incomplete observation | Any non-`stopped` descendant verdict requires `--confirm-descendants-stopped`, and the scope, enumeration and reason are recorded. |
| Termination requested but never observed | `_stop_tree` re-scans, kills only positively observed PIDs, and records a `termination` observation; outcomes now carry `custody`. |
| Predictable record path could serve stale evidence | `status`/`recover` refuse a record whose `plan_sha256` is not this plan. |
| No containment mechanism stronger than a parent chain | Job Object experiment added and qualified on Windows; execution deliberately still does not claim it. |

That review also confirmed the parts of this report that hold: the plan binding,
single-use fence, canonical path identities, atomic publication and the
cooperating-owner limitation statement needed no change.

`Ran 218 tests ... OK (skipped=4)` locally, plus 4 Job Object tests.
