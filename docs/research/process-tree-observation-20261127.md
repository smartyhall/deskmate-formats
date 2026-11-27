# Process-tree observation semantics

Date: 2026-11-27
Campaign: Supervisor and Observatory
Scope: `deskmate_formats.supervisor.process_tree`, `deskmate_formats.observer.process_health`,
`deskmate_formats.supervisor.job_object` (experimental), and every consumer of a tree
observation: lease reclamation, attempt recovery, cancellation, timeout handling and the
Observatory projection.

## 1. The reported failure was semantic

Both Linux configurations of run
[45803559898](https://github.com/smartyhall/deskmate-formats/actions/runs/45803559898) failed
`test_supervisor_process_tree.ProcessTreeTests.test_a_stopped_tree_reports_no_descendants`
with `AssertionError: 'not-found' != 'stopped'`.

The cause was one line in `tree_state`:

```python
"descendants": "not-found" if owner == "not-found" else "stopped"
```

The descendant verdict was derived from the *owner* verdict. On Linux a reaped owner is
`not-found`, so a complete scan of the recorded session that found **no** live member was
reported as `not-found` rather than `stopped`. On Windows the owner handle can still be
sampled after exit (`WaitForSingleObject` signalled → `stopped`), so the same code returned
`stopped` and the Windows jobs passed. The test was right; the implementation conflated two
independent questions.

Changing the test to accept either value would have removed the only fence against a real
reclamation hazard: every honest takeover after a clean exit would have needed an operator
override forever.

## 2. The contracts now implemented

| Question | Values | Established by |
| --- | --- | --- |
| Owner identity | recorded `(pid, identity)`; identity is a creation stamp | `process_health._sample` |
| Owner liveness | `alive`, `stopped`, `not-found`, `identity-mismatch`, `unknown` | sampling the recorded number and comparing stamps |
| Descendant identity | never individual; scope membership only | session id, or static parent chain |
| Descendant liveness | `alive`, `stopped`, `unknown` | complete enumeration of a durable scope |
| Enumeration completeness | `complete`, `truncated`, `timed-out`, `degraded`, `unavailable`, `incomplete` | explicit end-of-walk reason |
| Observation scope | `session`, `parent-chain`, `process`, `none`/`unclaimed` | how the claim was taken |
| Positive evidence of termination | owner in `OWNER_GONE` **and** `descendants == "stopped"` | both, never one |
| Unavailable observation | `unknown` with a reason string | any failed or degraded scan |
| Identity mismatch | owner gone, number reused | stamp comparison |
| Uncertainty | `unknown`; never `live == 0` | `live` is `None` when unknown |

Two rules carry most of the weight:

1. **A missing owner does not establish descendant termination.** The owner and the tree are
   sampled and reported separately.
2. **Positive findings survive incompleteness; absence does not.** A truncated or degraded
   scan that *found* a live member still reports `alive`, because something was observed. The
   same scan with no findings reports `unknown`, because nothing was proven.

`stopped(claim)` is true only for a complete scan of a non-lossy scope on the same boot as
the claim, with the owner positively gone.

## 3. Linux and POSIX

`/proc` is read, never signalled. Each record is classified before it is used:

| Record outcome | Classification | Effect on the verdict |
| --- | --- | --- |
| `FileNotFoundError` | the process exited during enumeration | none: expected, not a gap |
| `PermissionError`, `EIO`, other `OSError` | unobservable | `degraded`; absence is not proven |
| Short or non-numeric `stat` fields | malformed | `degraded`; absence is not proven |
| `Z`, `X`, `x` state | terminated, awaiting reaping | counted as terminated, not absent-and-alive |
| session matches, start time before the owner | session id reused, not a descendant | excluded; reason `session-id-reused` |
| count above `MAX_PROCESSES` | truncated | `unknown`: the walk never finished |
| deadline passed | timed out | `unknown` |

An inaccessible or malformed record is therefore never silently converted into evidence that
no relevant process exists.

**Session scope.** The runner starts each attempt with `start_new_session=True`, so the
attempt leads its own session, and every descendant inherits it unless it deliberately calls
`setsid`. A session exists as long as any member exists, so an empty session is genuine
positive evidence of termination. `tree_claim` records `scope: "session"` only when the
process leads its own session; recording the shared session of an ordinary process would make
every sibling look like a descendant.

**Process scope.** A non-leader has no durable handle: POSIX reparents orphans to init, so a
parent-chain walk loses members. It is still performed and its findings are reported, but
`descendants` stays `unknown` and `stopped()` stays false. `live_pids` reports
`complete=False` with reason `scope-not-durable`.

**Boot identity.** Linux start times are clock ticks since boot. Comparing a recorded start
time with a current one across a reboot is unsound in the unsafe direction: a long-lived
pre-reboot owner can have a larger start time than every post-reboot member, which would make
a fresh session look older than the owner and be excluded. The claim records the boot id in
the same canonical form the process identity embeds (`linux-<boot>-<start>`), so a recorded
lease inherits the same guard without a new registry field; a mismatch is `unknown` with
reason `boot-changed`.

**PID reuse.** Two independent checks: the owner's own number is compared by stamp
(`identity-mismatch`), and session members that started before the owner are excluded. A
member at the owner's pid that carries another stamp is never treated as the owner.

**Not claimed.** `hidepid` mounts, containers that rewrite `/proc`, and kernel threads with
unreadable records are handled as `degraded`/`unavailable`, not as empty sessions. A process
that calls `setsid` or leaves the group escapes the session and is not observable after the
owner exits; this is a property of the scope, documented rather than papered over.

## 4. Windows

`CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)` is walked record by record.

| Walk outcome | Classification |
| --- | --- |
| `Process32NextW` false with `ERROR_NO_MORE_FILES` | normal end of list → `complete` |
| `Process32NextW` false with any other error | `degraded`, reason `enumeration-ended-early` |
| `CreateToolhelp32Snapshot` or `Process32FirstW` failure | `unavailable` |
| entry count reaches `MAX_PROCESSES` | `truncated` |
| deadline reached | `timed-out` |

The previous implementation used `len(found) < MAX_PROCESSES` as its completeness flag, which
is a statement about findings, not about the walk: a scan that stopped at the cap with no
matches reported `complete`. It also ignored the `Process32NextW` error entirely. Both are
fixed.

**Static parent identifiers.** `ParentProcessId` is a field, not a relationship. It survives
the parent's exit, which is why the chain works at all after an owner dies, and it also
survives reuse of the parent's number, which is why it can lie. Every candidate child is
checked against the owner's creation stamp: a child created *before* the owner cannot be its
descendant. A candidate whose stamp cannot be read is kept (fail-safe) and the scan degrades.

When the owner's own number now carries a different stamp, the parent chain cannot separate
the original children from the new process's children, so the verdict is `unknown` with
reason `owner-pid-reused` rather than a guess in either direction.

**A detached child** cannot escape by reparenting, because Windows does not reparent; it stays
attached to the dead parent's number and remains discoverable. That is not the same as being
reachable.

**An intermediate parent that exits hides its children.** The walk starts at the owner's
identifier and follows parent fields through entries that exist in the snapshot. If
`owner → middle → leaf` and `middle` exits, nothing in the snapshot carries `owner` as its
parent, so `leaf` — whose parent field names the dead `middle` — is never reached. An empty
walk therefore proves nothing even though the walk itself completed. `parent-chain` is
consequently **not** a durable scope: findings are still positive evidence (`alive`), absence
is `unknown` with reason `scope-loses-orphans`, and `stopped()` is false on Windows. Only a
job object (§6) can make absence meaningful there. This corrects an earlier draft of this
document, which treated the static chain as lossless.

**A breakaway child** can leave a job (§6), which the parent chain does not model either.

## 5. Recovery consequences

Every consumer was traced and tightened:

| Consumer | Before | Now |
| --- | --- | --- |
| `campaigns.reclaim` | owner must be `stopped`/`not-found`; `unknown` descendants gated by a flag | also accepts `identity-mismatch`; **any** non-`stopped` descendant verdict is gated by `--confirm-descendants-stopped`, and the scope, enumeration and reason are recorded in the takeover record |
| `deterministic.recover` | refused only on a live owner or live descendant; closed an `unknown` tree as `uncertain` | refuses on a live owner/descendant **and** on an unobservable tree; an explicit `--confirm-descendants-stopped` records `descendants_confirmed` and `requires_manual_process_check` |
| `deterministic.status` | reported `owner` only | reports `descendants` and the observation `scope`/`enumeration`/`reason` |
| `deterministic._execute` | wrote `child.json` only when a claim succeeded | always writes a claim; a lost handle is written as `scope: "unclaimed"` and is visible to recovery instead of looking like "nothing was started" |
| `live_pids` | returned `[]` for an incomplete scan | returns a `Scan(pids, complete, enumeration, scope, reason)`; `[]` with `complete=True` is the only empty tree |
| `_stop_tree` | requested termination and returned nothing | requests, re-scans up to 20 rounds, kills only positively observed PIDs, and returns an observation recorded as `termination` in the outcome |
| Outcome receipt | no custody field | `custody`: `clean`, `descendants-alive` or `unobserved`, plus a limitation line when not clean |

A clean exit no longer implies an empty tree: the normal-exit path observes the tree too, so a
procedure that leaves a background process is recorded as `custody: "descendants-alive"`
instead of a silent `completed`.

## 6. Windows Job Objects

A job object is the only Windows mechanism that makes "this tree is over" an observation
rather than an inference.

`src/deskmate_formats/supervisor/job_object.py` is an **experiment**, not part of execution:

* `CreateJobObjectW` with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`;
* `AssignProcessToJobObject` by PID, reporting `process-denied` / `assign-denied` /
  `assign-failed` with the Win32 error rather than assuming adoption;
* `QueryInformationJobObject(JobObjectBasicAccountingInformation)` → `total`, `active`,
  `terminated`, where `active` is the object's own count of live members;
* `TerminateJobObject`, and `close()` which terminates the membership by the limit flag.

Qualified on the local Windows host with disposable synthetic processes
(`tests/portable/test_supervisor_job_object.py`, 4 tests, all passing):

1. A spawner that starts a 60-second grandchild is assigned to the job.
2. Killing **only** the spawner (`taskkill /F /PID`, no `/T`) leaves the grandchild running;
   the job still reports `active >= 1`, so the object observes what the dead owner cannot.
3. `terminate()` returns `active == 0` and the grandchild is gone from the process table.
4. Closing the handle alone kills the membership (kill-on-close).

What a job adds: membership that survives the owner, whole-tree termination in one call, and a
positive live-member count. It is the **only** Windows scope that can support a `stopped`
verdict; until execution creates and assigns one, every Windows tree verdict is `unknown` and
reclamation and recovery require explicit operator confirmation. What it does not add:

* **Not a sandbox.** Members still write to the filesystem and the network.
* **Breakaway.** A process created with `CREATE_BREAKAWAY_FROM_JOB` leaves, if the job permits
  breakaway. This implementation does not set `JOB_OBJECT_LIMIT_BREAKAWAY_OK`, so a member
  cannot request it, but a member already in an outer job can behave differently.
* **Nesting.** Windows 8+ nests jobs, so a process already inside the parent's job can be
  assigned to a new one; on older systems `AssignProcessToJobObject` fails with
  `ERROR_ACCESS_DENIED`. The module reports the failure; the test skips with the actual error.
* **Assignment race.** A child can spawn between `Popen` and `assign`. The race-free form is
  `CREATE_SUSPENDED` then assign then resume, which execution does not do yet.
* **Handle lifetime.** A job lives while a handle is open; a crash that leaks the handle keeps
  the membership alive, and `KILL_ON_JOB_CLOSE` only fires when the last handle closes.

**Disposition:** the module is merged as an experiment with its qualification tests. Execution
still uses the process-tree observation path, so no containment claim is made for procedures.
Wiring jobs into `_limited_subprocess` (suspended creation, assignment before resume, a
recorded job identity in the plan) is scoped as a successor change, because it changes the
execution contract rather than fixing an observation.

## 7. Regression coverage

| Contract | Test |
| --- | --- |
| Owner gone, tree empty, complete scan → `stopped` (the reported failure) | `test_a_stopped_tree_reports_no_descendants`, including a pinned `verify_process → not-found` case |
| Owner gone, descendant alive → `alive`, `stopped()` false | `test_an_owner_that_exited_still_reports_a_living_descendant` |
| A scope that loses members never proves termination | `test_a_scope_that_cannot_be_proven_never_reports_stopped` (POSIX) |
| An observation from another boot is not evidence | `test_an_observation_bound_to_another_boot_is_not_evidence` (POSIX) |
| Count limits are not completeness | `test_enumeration_limits_are_never_reported_as_complete` |
| Findings vs absence in `live_pids` | `test_live_pids_separates_findings_from_the_absence_of_findings` |
| Invalid claims are never `stopped` | `test_an_unknown_claim_is_never_read_as_stopped` |
| Identity stamp parsing | `IdentityStampTests` |
| Reclaim accepts a replaced owner number | `test_reclaim_accepts_a_replaced_owner_number` |
| Recovery refuses an unobservable tree, and never a live one | `test_interrupted_attempt_is_uncertain_and_never_replayed`, `test_recovery_refuses_a_live_child` |
| A record from another plan is not this attempt's evidence | `test_a_record_from_another_plan_is_never_read_as_this_attempt` |
| Owner absence is not propagated to the tree | `test_owner_absence_is_not_propagated_to_the_tree` (host-independent) |
| A grandchild behind a dead parent is not proof of absence | `test_a_grandchild_behind_a_dead_parent_is_not_proof_of_absence` (Windows) |
| Job containment (Windows) | `test_supervisor_job_object` |

Local result after the change: `Ran 218 tests ... OK (skipped=4)` for the Supervisor suite,
plus 4/4 Job Object tests. The two POSIX-only tests skip on Windows and are the ones that
exercise the Linux branch; they are the reason the CI matrix, not this host, decides whether
the Linux contract holds.

## 8. Remaining limitations

* A descendant that calls `setsid` (POSIX) or breaks away (Windows job) leaves the recorded
  scope; the observation then reports what it can see and never claims more.
* `MAX_PROCESSES` and the 3-second deadline are fixed constants; a very large host will
  report `truncated` rather than slow down.
* Zombie processes are treated as terminated; a parent that never reaps them keeps the PID in
  use, which the identity check handles but which does not affect the verdict.
* On Windows every tree verdict is `unknown` until job-backed execution exists, so reclamation
  and recovery there always take the explicit confirmation flag. That is the honest state, not
  a temporary test accommodation.
* Job-object integration into execution, and suspended-create assignment, remain open.
* Cancel and timeout termination is bounded by 20 rounds of 50 ms inside a 15-second budget;
  a process that ignores `SIGKILL` cannot exist, but one blocked in an uninterruptible kernel
  wait can outlive the rounds and is then recorded as `descendants: "alive"` rather than
  assumed gone.
* This document fences *observation*. Which observed member may be signalled, and with what
  identity evidence, is a separate contract recorded in the
  [termination-authority report](termination-authority-20261127.md); nothing in `live_pids`
  is authority to signal a PID.
