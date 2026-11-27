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
| Signal | A descendant is signalled only through an identity-bound OS handle, after a verification that must return literally `alive`; the mechanism and every refusal are recorded with the outcome. |
| Session continuity | A session identifier is only the leader's number, so `authorize` requires the leader's own record to carry the recorded stamp (`continuity: "leader-current"`). A different instance on that number proves the original session ended; no record at all proves nothing. Either way the finding is kept and the authority withheld. |
| Group custody | `signal(..., group=True)` requires a `Custody(pid, identity)` proof for that very member: the direct child is unreaped and still verifies as the recorded instance. A leader that was merely observed — any descendant, or any process the caller never spawned — has none. |
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
* `signal(member, group=False)` — Linux `pidfd`: open the descriptor with
  `os.pidfd_open`, *then* verify the identity, then send with
  **`signal.pidfd_send_signal`** (the function lives in the `signal` module, not in
  `os`), so a number recycled before the open is refused and a number recycled
  afterwards is unreachable. Windows: open the process once, read the creation
  `FILETIME` from that handle, then `TerminateProcess` on the same handle. Every
  verification must return literally `alive`: `unknown` is refused, not matched. If
  neither handle is available the signal is refused as `unavailable` — there is no
  numeric PID fallback for a descendant.
* `group_leader(pid)` — a group signal is honoured only for a member authorised as
  its own group leader.
* `custody(process, claim)` — the proof a group signal additionally needs: the claim names
  that PID, the child has not been reaped (`returncode is None`, so the kernel still
  reserves its number), and `verify_process` returns `alive` for the recorded identity.
  Without it `_signal_group` refuses `group-without-custody`.

`deterministic._stop_tree` now:

1. authorises the owner by identity and takes custody of the direct child; a verified
   group leader is signalled as a group only with that custody, **before** `wait`, while
   the unreaped leader's number still names its group;
2. otherwise terminates the direct child through the `Popen` object, which is an
   identity-bound handle on both platforms (Windows holds the handle; POSIX cannot
   recycle the number until this attempt reaps it);
3. re-authorises and signals identity-bound members in bounded rounds inside a 15 s
   budget, recording every result — while the child is still unreaped, so each round can
   re-prove that the recorded session is this attempt's;
4. reaps the child, then re-observes the tree and reports `owner`, `descendants`,
   `enumeration`, `continuity`, `scope`, the authority it had and the signals it sent,
   including refusals.

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
| pidfd read from the wrong namespace | `test_the_pidfd_capability_is_read_from_the_documented_namespace` (Linux) |
| Descriptor discipline: open, verify, send, close | `test_the_pidfd_route_opens_verifies_sends_and_closes` (POSIX) |
| The real Linux route is selected, not a fallback | `test_a_member_bound_to_its_observed_identity_is_signalled` asserts `mechanism == "pidfd"` on Linux |
| `unknown` verification treated as a match | `test_an_unknown_verification_is_not_an_identity_match_on_the_pidfd_path`, `..._on_the_group_path` |
| Numeric kill standing in for a missing handle | `test_no_identity_bound_handle_means_no_signal` |
| Reuse between enumeration and authorisation | `test_only_the_exact_stamp_of_this_number_is_an_identity_match` (earlier and later holder), `test_membership_and_identity_come_from_the_same_record` |
| A stalled termination round retried into a claim | `test_an_unavailable_handle_ends_the_rounds_instead_of_spinning` |

Added by the third follow-up correction (§10), on synthetic session records rather than on
host PID reuse:

| Defect | Test |
| --- | --- |
| A recycled session number authorised strangers | `test_a_leader_held_by_another_instance_revokes_the_session`, `test_a_newer_member_stamp_is_not_continuity` |
| An absent leader's number treated as authority | `test_an_absent_leader_keeps_the_observation_and_withholds_authority` |
| Absence made to depend on continuity | `test_an_empty_session_is_absence_whether_or_not_a_leader_remains` |
| A group leader merely observed | `test_a_group_signal_without_custody_is_refused`, `test_a_leader_this_attempt_never_spawned_has_no_custody` |
| A reaped child's freed number taken as custody | `test_a_reaped_child_can_no_longer_confer_group_custody` |
| Cleanup attempted once the session was only digits | `test_the_group_signal_is_issued_before_the_child_is_reaped` |
| An unbound observation reaching the signal loop | `test_an_unbound_observation_never_reaches_the_signal_loop` |
| Uncertain custody reported as clean | `test_uncertain_custody_is_not_reported_as_clean` |

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
* A POSIX host with neither `pidfd_open` nor `pidfd_send_signal` (for example macOS)
  can terminate only its own direct child, through the `Popen` handle; descendants
  are reported as `unavailable` and left running. That is the fail-closed state, not
  a missing code path.
* A `TerminateProcess`/`pidfd_send_signal` call that fails after the identity matched
  is reported as `failed`; the outcome then stays `unobserved`.
* A session is authorised only while its leader record still carries the recorded
  identity. If the child was reaped by another route, the session can be identified only
  by its digits: live members are then reported as `descendants: "alive"` and never
  signalled, and custody is `uncertain` rather than clean.
* A group signal needs the unreaped direct child. Where custody is gone — the child
  already reaped, or a leader only observed — the group is not signalled and the
  per-member path is used instead.
* Job-backed execution (`CREATE_SUSPENDED` → assign → resume) is still the only path
  to a Windows `stopped` verdict, and remains a separate change.

## 9. Correction after the second follow-up review (2026-11-27)

The follow-up review (`pullrequestreview-6085614784`) found a concrete defect in the
new signalling path, and it was correct.

**The defect.** `_signal_pidfd` probed `os.pidfd_send_signal`. CPython exposes
`pidfd_send_signal` in the `signal` module (next to `os.pidfd_open`), so the probe
always returned `None` on Linux and every descendant signal silently took the numeric
fallback instead. The identity-bound path the documentation claimed was never selected
on any host. The regression test that should have caught it asserted only that the
mechanism was one of `("pidfd", "pid", "process-handle")`, which accepted the fallback
as a pass.

**Corrections.**

* The probe is now `getattr(os, "pidfd_open", None)` and
  `getattr(signal, "pidfd_send_signal", None)`, with an explicit comment recording
  which namespace each belongs to. A unit test asserts the module attributes are
  identical objects to the documented ones, and the end-to-end Linux test now asserts
  `mechanism == "pidfd"`.
* Positive verification is required. `verify_process` must return literally `alive`;
  `unknown` is refused on the pidfd path and on the group path, both covered by
  tests.
* No numeric PID kill remains for a descendant. `_signal_by_pid` is deleted: a host
  without an identity-bound handle reports `unavailable` and leaves the process
  running. The direct child is still terminated through the `Popen` handle, which is
  identity-bound on both platforms and is not a numeric kill.
* A refused group signal now falls back to the owned-child handle instead of leaving
  the child alive, and a termination round that delivers nothing ends immediately
  rather than repeating a refusal twenty times.
* Session membership is re-proved at authorisation time. `process_tree.member_identity`
  returns the creation stamp from the *same* read of the process record that yields
  the session identifier, so a number reused between two reads cannot satisfy the
  scope check with an identity that belongs to a different process. `authorize` uses
  it in place of a separate identity sample.
* Group signalling re-checks both the identity and that the number still leads its own
  group immediately before `killpg`, and refuses if the leader is not positively alive.

**What the Linux job then found.** With the corrected path actually running, the two
ubuntu jobs failed one *test assumption*, not the implementation: a first version of the
reuse test asserted that two independently spawned processes have different identities.
On Linux the stamp is the creation **tick** (10 ms at the usual clock rate), so two
processes started within one tick carry the same identity string. The implementation was
right and the test was wrong, but the episode pins a property worth stating: the stamp
identifies an instance only **together with the PID**, and identity equality across two
different PIDs means nothing. The reuse check always compares one PID against itself,
where a later holder is necessarily created later and so carries a strictly greater
stamp. That invariant is now in `process_health.start_stamp` and the `Member` comment,
and the test constructs an earlier and a later stamp for the *same* number instead.

**Scope held.** No new service, no emulator, no agent dispatch, no change to live
grants or to PR #199 or the issue #201 campaign's files. The local Windows host cannot
exercise the pidfd branch, so that half is settled by the ubuntu CI jobs; the Windows
half by the windows jobs.

## 10. Correction after the third follow-up review (2026-11-27)

Review `pullrequestreview-6086218760` accepted the pidfd selection, the positive
verification and the removal of numeric descendant signalling, and found that authority
could still be derived from an identifier without custody. Both findings were correct.

### A recycled session number authorised strangers

`_session_scan` admitted every process whose `sid` field equalled the recorded session
number and whose creation stamp was at or after the owner's. The stamp establishes only
that the member was created later; it says nothing about *which* session it joined. Once
the original session was completely gone the kernel could issue its number again, and a
new session's members would satisfy both conditions.

The identifier's own binding is the leader's record, and that is now read
(`process_tree._session_continuity`):

| Outcome | Meaning | Authority |
| --- | --- | --- |
| `leader-current` | the number is held by the recorded instance | members are bound and may be authorised |
| `leader-reused` | a different instance holds the number | the original session was destroyed; findings kept, nothing claimed |
| `leader-absent` | there is no leader record | the session may be the original one, but only its number says so |
| `unknown` | the record is unreadable, or the claim carries no comparable stamp | refused |

`authorize` refuses every member unless the continuity is `leader-current`, with reason
`session-continuity-unproven`; `member_identity` applies the same rule, so the two paths
cannot disagree. The finding is not discarded: `Scan.pids` keeps the observed PIDs,
`Scan.continuity` says they are unattributed, `tree_state` reports `continuity` beside its
verdict (`descendants: "unknown"` for `leader-reused`, whose processes belong to someone
else's session), and the outcome records `custody: "uncertain"` instead of a cleanup it
cannot demonstrate.

Absence deliberately does not depend on continuity, which preserves reclamation: a session
always contains its own leader, so an empty scan of the session number is sound whichever
session last held it. `stopped()` therefore still reports `stopped` after a completed
cleanup whose leader has since been reaped.

### A group signal needed custody, not leadership

`_signal_group` verified the leader's identity, checked that the number still led its own
group, and called `killpg(number)`. For the direct child that is sound only while it is
unreaped, and nothing in the signature said the caller held one: any `Member` marked
`group` was accepted, including a leader a scan had merely observed.

`signal(member, group=True, custody=...)` now requires a `Custody(pid, identity)` proof
from `custody(process, claim)`, returned only when the claim names this PID, the child has
not been reaped (`returncode is None`, so the kernel still reserves the number) and
`verify_process` returns literally `alive` for the recorded identity. Without it the
signal is refused as `group-without-custody` and the owned-child handle is used instead. A
leader that exits between authorisation and the signal opens no window onto another group:
it becomes a zombie the kernel keeps until reaped, and `verify_process` then returns
`stopped`, which is refused.

### The reap moved after the rounds

`_stop_tree` used to `wait` for the child and only then scan for survivors. By then the
child's number was free — exactly the state in which a session can be identified only by
its digits. The rounds now run between the signals and the reap, while the child is
unreaped (alive or zombie), so each round re-proves `leader-current` and can still signal
the survivors that broke out of the group. `_kill_owned_child` reads `process.returncode`
instead of calling `poll`, because polling reaps and would release the identifier the
rounds rely on.

### Licensing

Every general-documentation file this campaign authored — the eight research reports and
the five use receipts under `docs/evidence/agent-usage/` — carried a GPL-only sidecar.
`LICENSING.md` assigns general documentation and provenance metadata
`GPL-3.0-or-later OR CC-BY-SA-4.0`, and those sidecars now carry that dual offer. Software
stays GPL-only, the formal specifications keep their own category, and no third-party
notice changed.

### Coordination and scope

PR #206 (campaign-owned Python environments) and issue #207 (production launch
integration) are not absorbed here. PR #199's shared fixture and `pyproject.toml` are
untouched, so its 60-second fixture timeout and performance evidence are unchanged. No new
service, emulator, dispatch or execution authority was added; the tests build session
records instead of asking the host to recycle a PID, and the four-platform matrix at the
resulting head decides whether the POSIX branches hold.
