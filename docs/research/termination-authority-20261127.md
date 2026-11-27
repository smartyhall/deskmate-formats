# Termination authority: observation is not permission to signal

Campaign: `freebuff/supervisor-and-observatory-infrastructure` (PR #191).
Author: Freebuff (Cloud, autonomous coding agent, 2026-11-27).
Base for this checkpoint: `c1e3f69`.
Scope: the deterministic backend's termination path, the process-control boundary and
the identity evidence each signal is bound to.

This document records a *code* change and its contracts. It repeats no native
experiment from the earlier campaign: the Job Object qualification and the Windows
parent-chain observations are reused as prior evidence, not re-measured.

## 1. The reported defect

The independent review of 2026-11-27 identified a distinction the previous
correction had not drawn. Process *observation* answers "what can be seen". Process
*control* answers "what may be signalled". The implementation had one mechanism for
both:

* `process_tree.live_pids` returned PIDs whose docstring said they were "safe to
  pass to a kill". It retained PIDs whose liveness sampled as `unknown` and carried
  no creation identity with the number.
* `deterministic._stop_tree` passed every returned PID to `_kill_pid`, which called
  `os.kill(pid, SIGKILL)` or `taskkill /F /PID`. Between the scan and the signal
  nothing re-established that the number still named the observed instance.
* `_stop_tree` also opened with `taskkill /F /T /PID <owner>` on Windows and
  `os.killpg(os.getpgid(pid))` on POSIX. `/T` walks *current* static parent fields,
  so a reused number anywhere under the owner can pull an unrelated process into
  the kill set; `getpgid` on a reaped number could name a group this attempt never
  created.
* A Windows parent-chain observation could associate an unrelated process with the
  tree even though `tree_state` already refused to *report* a reused owner.

The consequence is not a wrong verdict on a report: it is a signal delivered to a
process this attempt does not own.

## 2. Contracts now enforced

| Contract | Enforcement |
| --- | --- |
| Positively observed liveness | `process_tree._live` returns a PID only when it sampled `alive`. `unknown` is counted and reported, never returned as live. |
| Unknown liveness is neither life nor absence | A member with `unknown` status is excluded **and** downgrades the scan to `degraded` / `unknown-member-liveness`, so its absence from the tuple can never be read as an empty tree. |
| Findings survive incompleteness | A positively live member still makes the descendant verdict `alive` whatever the enumeration says. |
| Identity-bound member | `process_control.Member(pid, identity, group)` carries the creation stamp sampled when the member was authorised, so it names an instance, not a number. |
| Authorised owner | Only while `verify_process(pid, claim_identity) == "alive"`. `identity-mismatch` is evidence the owner is gone and never authority over the new holder. |
| Authorised descendants | Only for a scope whose membership the kernel holds. A parent chain, on either platform, grants none. |
| Signal | Every signal re-checks the identity and prefers an identity-bound OS handle; the mechanism and the refusal are recorded with the outcome. |
| Refusal is reported | `identity-mismatch`, `gone`, `unknown`, `refused` and `failed` are results. None is a successful cleanup. |

### Why a POSIX session is authority and a Windows parent chain is not

A POSIX session (and a process group) is keyed by the leader's `struct pid`. The
kernel holds a reference while any member survives, so the numeric identifier cannot
be recycled while the scope still contains something, and a member cannot be attached
by a stale record field. An empty, complete scan of that scope is therefore
termination, and the numeric group identifier still names this attempt's group.

A Windows `ParentProcessId` is a static field that is never updated. A grandchild
whose intermediate parent exited keeps pointing at a dead number; if that number is
reused, its new children inherit the same field and become indistinguishable from
this tree's members. No amount of identity filtering inside the walk can recover the
distinction, because the association itself is unfounded. The honest resolution is
that such a scope describes membership but does not own it.

## 3. What the code does now

`src/deskmate_formats/supervisor/process_control.py` (new) holds the whole authority
boundary, so `process_tree` keeps its documented read-only contract:

* `authorize(claim)` — one scan, then a per-member identity sample. Returns
  `Authorization(owner, members, scope, enumeration, reason)`. Members are dropped
  and the enumeration downgraded when a stamp cannot be read, when a stamp predates
  the owner, or when the deadline expires mid-authorisation.
* `signal(member, group=False)` — Linux `pidfd`: open the descriptor, *then* verify
  the identity, then signal through the descriptor, so a number recycled before the
  open is refused and a number recycled afterwards is unreachable. Windows: open the
  process once, read the creation `FILETIME` from that handle, then
  `TerminateProcess` on the same handle. Everywhere else: sample immediately before
  `os.kill` and record the mechanism as `pid`.
* `group_leader(pid)` — a group signal is honoured only for a member authorised as
  its own group leader.

`deterministic._stop_tree` now:

1. authorises the owner by identity; a verified group leader is signalled as a group
   **before** `wait`, while the unreaped leader's number still names its group;
2. otherwise terminates the direct child through the `Popen` object, which is an
   identity-bound handle on both platforms (Windows holds the handle; POSIX cannot
   recycle the number until this attempt reaps it);
3. re-authorises and signals identity-bound members in bounded rounds inside a 15 s
   budget, recording every result;
4. re-observes the tree and reports `owner`, `descendants`, `enumeration`, `scope`,
   the authority it had and the signals it sent, including refusals.

`taskkill` is no longer used at all: neither `/T` (which walks a replaceable field)
nor `/PID` (which re-resolves the number after any check).

`process_tree` also gained: a traversal deadline for both scans (previously only the
enumeration loop was bounded, while the parent walk was not), and Windows Toolhelp
completion now accepts **only** `ERROR_NO_MORE_FILES` as the end of the list — a zero
left in the error slot is an early stop, not a complete enumeration.

## 4. Behaviour that changed, and its cost

* **Windows descendant termination is gone.** A timeout or cancellation on Windows
  now terminates the owner and reports `descendants: "unknown"`; grandchildren that
  the parent chain could name are left alone. This is a real loss of cleanup
  capability, traded deliberately: the alternative was signalling processes the
  attempt cannot prove it owns. Recovery and lease reclamation there already require
  `--confirm-descendants-stopped`, so nothing gained authority from the change.
* **Unknown-liveness members are no longer passed to a kill.** A hung-but-unreadable
  process is reported, not signalled.
* **`live_pids` is narrower.** Its result is a set of positive findings, documented as
  such; `Scan.complete` remains the only field that may be read as absence.
* The qualification for a Windows `stopped` verdict is unchanged and still requires
  job-backed execution, which remains unimplemented.

## 5. Regression tests

`tests/portable/test_supervisor_process_control.py` (new):

| Defect | Test |
| --- | --- |
| Unknown status retained as live and killable | `test_an_unknown_liveness_member_is_not_returned_and_not_called_absent` |
| Only a positive sample counts as live | `test_only_a_positively_live_pid_is_reported` |
| An expired traversal deadline read as a complete scan | `test_an_expired_deadline_is_never_a_complete_scan` |
| Member not bound to its creation identity | `test_a_member_carries_the_identity_sampled_at_authorisation` |
| Unreadable member identity read as absent | `test_an_unverifiable_member_identity_is_dropped_and_downgrades_the_scan` |
| Parent chain authorised as ownership | `test_a_scope_that_cannot_bind_membership_grants_no_descendant_authority` |
| Reused owner number granting authority | `test_a_reused_owner_number_grants_no_authority_at_all` |
| Claim without a handle | `test_a_claim_without_a_handle_is_never_authorised` |
| **A changed identity is signalled anyway** | `test_a_changed_identity_is_refused_and_the_process_survives` (a real process survives) |
| Identity-bound signal reaches the instance | `test_a_member_bound_to_its_observed_identity_is_signalled` |
| Group signal redirected to this attempt's group | `test_a_group_signal_is_refused_for_a_process_that_does_not_lead_its_group` |
| `taskkill /T` tree walk in the backend | `test_the_direct_child_is_terminated_through_a_bound_handle` (asserts `subprocess.run` was never called) |
| Refusal recorded as cleanup | `test_a_refused_member_signal_is_recorded_rather_than_read_as_cleanup` |
| **Unrelated tree signalled** | `test_a_descendant_of_another_tree_is_never_signalled` (POSIX: two real sessions; the second's members stay alive) |

The test that matters most for the review's concern is the pair of real-process
tests: one proves a mismatched identity is refused and the process keeps running, the
other proves an independent tree's members survive a termination of a sibling tree.

Local result on the Windows host: `Ran 239 tests in 991.301s`, `OK (skipped=6)` for
the whole Supervisor discovery scope. Four of those skips are the usual platform
guards; the POSIX session tests that carry the new authority contract run in CI, which
is why the Linux matrix job decides whether that half holds.

## 6. Issue #201 inspection (documentation only; implementation deferred)

The operator's issue #201 records that isolated child launches (`python -I -m ...`)
ignore `PYTHONPATH`, so a child can exercise a wheel installed by another campaign
while the report names the parent's checkout. Inspection of this branch:

* `procedures._build_portable_tests` and `_build_reuse` launch without `-I`, so they
  inherit the `PYTHONPATH` that `deterministic.environment` points at the prepared
  working tree. Their imports follow the plan's `modules` binding.
* `procedures._build_audit`, `_build_hash`, `_build_compare` and
  `workspace.command`'s publication audit launch with `-I`. `_build_hash` and
  `_build_compare` scripts are self-contained and import nothing from this project.
  The **`repository-audit`** procedure does: `AUDIT_SCRIPT` begins
  `from deskmate_formats.supervisor import repository_audit`, so under `-I` it
  resolves from the installation, while `prepare` binds the parent's module origin.
  That is a real provenance gap of exactly the kind #201 describes.
* No new implementation is attempted here. What was added is disclosure: the outcome
  record now appends a limitation when a plan launches `-I` **and** binds a project
  module — "the child runs with `-I`, so it imports this package from the
  installation rather than the prepared working tree… (issue #201)". The
  campaign-owned environment and parent/child source receipts belong to the dedicated
  follow-up campaign.

## 7. Coordination

* PR #199 overlaps `pyproject.toml` and `tests/portable/task_fixture.py`. This
  checkpoint touches neither, so the existing synchronization correction is
  preserved unchanged and the eventual reconciliation is unaffected.
* No file under the performance worker's branch was read or modified, and no native
  experiment, emulator, provider credential or paid call was used.

## 8. Remaining limitations

* Windows descendant custody is unobservable without a job: the verdict stays
  `unknown`, and the backend no longer attempts to force it to `stopped`.
* A POSIX descendant that calls `setsid` leaves the session and is outside both the
  observation and the authority. It is reported, never claimed.
* The `pid` fallback (hosts with neither `pidfd` nor a Windows handle) leaves a
  non-zero window between the identity check and the signal. It is recorded as
  `mechanism: "pid"` rather than described as atomic.
* A `TerminateProcess`/`pidfd_send_signal` call that fails after the identity matched
  is reported as `failed`; the outcome then stays `unobserved`.
* Job-backed execution (`CREATE_SUSPENDED` → assign → resume) is still the only path
  to a Windows `stopped` verdict, and remains a separate change.
