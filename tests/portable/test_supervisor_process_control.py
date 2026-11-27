"""Observation is not permission: control must bind to a process instance.

The reported defect was that a scan's PIDs were handed to a kill with no identity
check, that an unknown status was silently retained as "live", and that a Windows
parent chain could associate an unrelated process with a reused owner number.
These tests fence the *authority* contract separately from the observation one:
only an identity-bound member of a kernel-held scope may be signalled, a changed
or unreadable identity is refused, and no numeric PID kill stands in for a handle
this attempt cannot acquire.
"""

import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from unittest import mock
import unittest

from deskmate_formats.observer import process_health
from deskmate_formats.supervisor import deterministic, process_control, process_tree

POSIX = unittest.skipIf(os.name == "nt", "POSIX session semantics")
WINDOWS = unittest.skipIf(os.name != "nt", "Windows parent-chain semantics")
LINUX = unittest.skipIf(sys.platform != "linux", "Linux pidfd semantics")

SLEEPER = "import time; time.sleep(60)"
SPAWNER = (
    "import subprocess, sys, time\n"
    "subprocess.Popen([sys.executable, '-I', '-c', 'import time; time.sleep(60)'])\n"
    "open(sys.argv[1], 'w').write('spawned')\n"
    "time.sleep(60)\n"
)

# A session claim whose scan reports one member and an owner that is demonstrably
# alive: the shape every authority question is asked about.
SESSION_CLAIM = {"pid": 424242, "identity": "linux-abc-100", "session": 424242,
                 "scope": "session", "boot": "abc"}
ONE_MEMBER = process_tree.Scan((424243,), True, "complete", "session", "session-scan-complete",
                               "leader-current")


def stop(process):
    """Test cleanup only. Production termination is process_control's job."""
    if process.poll() is None:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(process.pid)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=30)
            else:
                os.kill(process.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        process.wait(timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pass


def sleeper():
    kwargs = {} if os.name == "nt" else {"start_new_session": True}
    return subprocess.Popen([sys.executable, "-I", "-c", SLEEPER], **kwargs)


def spawn_tree(root, name):
    marker = root / name
    kwargs = {} if os.name == "nt" else {"start_new_session": True}
    process = subprocess.Popen([sys.executable, "-I", "-c", SPAWNER, str(marker)], **kwargs)
    for _ in range(600):
        if marker.exists():
            break
        time.sleep(0.02)
    return process, marker.exists()


class LivenessAuthorityTests(unittest.TestCase):
    """Unknown liveness is neither life nor absence, and never permission."""

    def test_an_unknown_liveness_member_is_not_returned_and_not_called_absent(self):
        with mock.patch.object(process_tree, "_scan", return_value=ONE_MEMBER), \
                mock.patch.object(process_tree, "process_status", return_value="unknown"), \
                mock.patch.object(process_tree, "verify_process", return_value="stopped"):
            state = process_tree.tree_state(SESSION_CLAIM)
            self.assertEqual(state["descendants"], "unknown")
            self.assertEqual(state["enumeration"], "degraded")
            self.assertEqual(state["reason"], "unknown-member-liveness")
            self.assertIsNone(state["live"])
            self.assertFalse(process_tree.stopped(SESSION_CLAIM))
            scan = process_tree.live_pids(SESSION_CLAIM)
            self.assertEqual(scan.pids, ())
            self.assertFalse(scan.complete)
            authorization = process_control.authorize(SESSION_CLAIM)
        # No member may be signalled, and nothing said the tree is empty.
        self.assertEqual(authorization.members, ())
        self.assertNotEqual(authorization.enumeration, "complete")

    def test_only_a_positively_live_pid_is_reported(self):
        with mock.patch.object(process_tree, "_scan",
                               return_value=ONE_MEMBER._replace(pids=(11, 12, 13))), \
                mock.patch.object(process_tree, "process_status",
                                  side_effect=lambda pid: {11: "alive", 12: "stopped",
                                                           13: "unknown"}[pid]):
            scan = process_tree.live_pids(SESSION_CLAIM)
        self.assertEqual(scan.pids, (11,))
        self.assertFalse(scan.complete)

    def test_an_expired_deadline_is_never_a_complete_scan(self):
        process = sleeper()
        self.addCleanup(stop, process)
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        state = process_tree.tree_state(claim, deadline_seconds=-1)
        self.assertEqual(state["enumeration"], "timed-out")
        self.assertNotEqual(state["descendants"], "stopped")
        self.assertFalse(process_tree.stopped(claim, deadline_seconds=-1))


class MemberBindingTests(unittest.TestCase):
    """A member must carry the identity that was observed, or it is not a member."""

    def test_a_member_carries_the_identity_sampled_at_authorisation(self):
        with mock.patch.object(process_tree, "_scan", return_value=ONE_MEMBER), \
                mock.patch.object(process_tree, "process_status", return_value="alive"), \
                mock.patch.object(process_control, "verify_process", return_value="alive"), \
                mock.patch.object(process_tree, "member_identity",
                                  return_value="linux-abc-200"):
            authorization = process_control.authorize(SESSION_CLAIM)
        self.assertEqual([member.pid for member in authorization.members], [424243])
        self.assertEqual(authorization.members[0].identity, "linux-abc-200")
        self.assertEqual(authorization.reason, "identity-bound-members")
        self.assertEqual(authorization.owner.identity, "linux-abc-100")

    def test_an_unverifiable_member_identity_is_dropped_and_downgrades_the_scan(self):
        with mock.patch.object(process_tree, "_scan", return_value=ONE_MEMBER), \
                mock.patch.object(process_tree, "process_status", return_value="alive"), \
                mock.patch.object(process_control, "verify_process", return_value="alive"), \
                mock.patch.object(process_tree, "member_identity", return_value=None):
            authorization = process_control.authorize(SESSION_CLAIM)
        self.assertEqual(authorization.members, ())
        self.assertEqual(authorization.enumeration, "degraded")
        self.assertEqual(authorization.reason, "unverified-member-identities")

    def test_a_scope_that_cannot_bind_membership_grants_no_descendant_authority(self):
        """A reused number in a static chain can attach an unrelated process."""
        claim = {"pid": 424242, "identity": "win-1a", "scope": "parent-chain"}
        scan = process_tree.Scan((424243,), False, "incomplete", "parent-chain",
                                 "scope-loses-orphans")
        with mock.patch.object(process_tree, "_scan", return_value=scan), \
                mock.patch.object(process_tree, "process_status", return_value="alive"), \
                mock.patch.object(process_control, "verify_process", return_value="alive"):
            authorization = process_control.authorize(claim)
        self.assertEqual(authorization.members, ())
        self.assertEqual(authorization.reason, "scope-not-identity-bound")
        # The owner is still authorised by its own verified identity.
        self.assertEqual(authorization.owner.pid, 424242)
        self.assertFalse(authorization.owner.group)

    def test_a_reused_owner_number_grants_no_authority_at_all(self):
        claim = {"pid": 424242, "identity": "win-1a", "scope": "parent-chain"}
        with mock.patch.object(process_tree, "_scan", return_value=ONE_MEMBER), \
                mock.patch.object(process_tree, "process_status", return_value="alive"), \
                mock.patch.object(process_control, "verify_process",
                                  return_value="identity-mismatch"):
            authorization = process_control.authorize(claim)
        self.assertIsNone(authorization.owner)
        self.assertEqual(authorization.members, ())

    def test_a_claim_without_a_handle_is_never_authorised(self):
        for claim in (None, {}, {"pid": 0}, {"pid": "1"}, {"pid": 4, "scope": "unclaimed"}):
            with self.subTest(claim=claim):
                authorization = process_control.authorize(claim)
                self.assertIsNone(authorization.owner)
                self.assertEqual(authorization.members, ())
                self.assertEqual(authorization.reason, "no-tree-handle")

    @POSIX
    def test_membership_and_identity_come_from_the_same_record(self):
        """A member number reused into another session is not a member."""
        root = Path(self.enterContext(TemporaryDirectory()))
        process, ready = spawn_tree(root, "member")
        self.addCleanup(stop, process)
        self.assertTrue(ready)
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        self.assertEqual(claim["scope"], "session")
        found = process_tree.live_pids(claim).pids
        self.assertTrue(found)
        for pid in found:
            identity = process_tree.member_identity(claim, pid)
            self.assertIsNotNone(identity)
            self.assertEqual(identity, process_health.process_health_identity(pid))
        # The same numbers observed in a different session are not members, so
        # enumeration cannot be replayed as authority after a scope change.
        elsewhere = dict(claim, session=claim["session"] + 1)
        for pid in found:
            self.assertIsNone(process_tree.member_identity(elsewhere, pid))
        # A process outside the recorded session is never a member of it.
        self.assertIsNone(process_tree.member_identity(claim, os.getpid()))

    @POSIX
    def test_a_member_without_a_recorded_boot_cannot_be_bound(self):
        claim = dict(SESSION_CLAIM, identity=None, boot=None)
        self.assertIsNone(process_tree.member_identity(claim, 424243))


class SignalRefusalTests(unittest.TestCase):
    """A signal must reach the observed instance or nothing at all."""

    def test_a_changed_identity_is_refused_and_the_process_survives(self):
        process = sleeper()
        self.addCleanup(stop, process)
        stale = process_control.Member(process.pid,
                                       "win-1" if os.name == "nt" else "linux-deadbeef-1",
                                       False)
        result = process_control.signal(stale)
        self.assertEqual(result["result"], "identity-mismatch")
        self.assertFalse(result["identity_matched"])
        self.assertEqual(process_health.process_status(process.pid), "alive")
        self.assertIsNone(process.poll(), "an unrelated instance must not be signalled")

    def test_only_the_exact_stamp_of_this_number_is_an_identity_match(self):
        """The reuse case: an earlier or later holder's stamp on this number.

        The stamp is a creation tick, so it is compared only within one PID. A
        recycled number always belongs to a later instance, whose stamp differs;
        both directions are refused here.
        """
        if os.name != "nt" and not process_control._PIDFD_AVAILABLE:
            self.skipTest("this host exposes no identity-bound handle")
        process = sleeper()
        self.addCleanup(stop, process)
        current = process_health.process_health_identity(process.pid)
        self.assertIsNotNone(current)
        expected = process_health.start_stamp(current)
        boot = process_health.identity_boot(current)

        def stamped(delta):
            value = expected + delta
            return f"win-{value:x}" if boot is None else f"linux-{boot}-{value}"

        for delta in (-1, 1):
            with self.subTest(delta=delta):
                result = process_control.signal(
                    process_control.Member(process.pid, stamped(delta), False))
                self.assertEqual(result["result"], "identity-mismatch")
                self.assertFalse(result["identity_matched"])
                self.assertEqual(process_health.process_status(process.pid), "alive")

    @POSIX
    def test_an_unknown_verification_is_not_an_identity_match_on_the_group_path(self):
        process = sleeper()
        self.addCleanup(stop, process)
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        self.assertTrue(process_control.group_leader(process.pid))
        proof = process_control.custody(process, claim)
        self.assertIsNotNone(proof)
        member = process_control.Member(process.pid, claim["identity"], True)
        with mock.patch.object(process_control, "verify_process", return_value="unknown"):
            result = process_control.signal(member, group=True, custody=proof)
        self.assertEqual(result["result"], "unknown")
        self.assertIsNone(result["identity_matched"])
        self.assertEqual(process_health.process_status(process.pid), "alive")

    @LINUX
    def test_an_unknown_verification_is_not_an_identity_match_on_the_pidfd_path(self):
        process = sleeper()
        self.addCleanup(stop, process)
        identity = process_health.process_health_identity(process.pid)
        member = process_control.Member(process.pid, identity, False)
        with mock.patch.object(process_control, "verify_process", return_value="unknown"):
            result = process_control.signal(member)
        self.assertEqual(result["mechanism"], "pidfd")
        self.assertEqual(result["result"], "unknown")
        self.assertIsNone(result["identity_matched"])
        self.assertEqual(process_health.process_status(process.pid), "alive")

    @POSIX
    def test_no_identity_bound_handle_means_no_signal(self):
        """A numeric kill after a separate sample is not authority."""
        process = sleeper()
        self.addCleanup(stop, process)
        identity = process_health.process_health_identity(process.pid)
        with mock.patch.object(process_control, "_PIDFD_AVAILABLE", False):
            result = process_control.signal(process_control.Member(process.pid, identity, False))
        self.assertEqual(result["result"], "unavailable")
        self.assertEqual(result["mechanism"], "none")
        self.assertEqual(process_health.process_status(process.pid), "alive")

    def test_a_member_bound_to_its_observed_identity_is_signalled(self):
        if os.name != "nt" and not process_control._PIDFD_AVAILABLE:
            self.skipTest("this host exposes no identity-bound handle")
        process = sleeper()
        self.addCleanup(stop, process)
        identity = process_health.process_health_identity(process.pid)
        self.assertIsNotNone(identity)
        result = process_control.signal(
            process_control.Member(process.pid, identity,
                                   process_control.group_leader(process.pid)))
        self.assertEqual(result["result"], "signalled")
        self.assertTrue(result["identity_matched"])
        if sys.platform == "linux":
            # The claimed path must be the pidfd path, not the numeric fallback.
            self.assertEqual(result["mechanism"], "pidfd")
        process.wait(timeout=30)
        self.assertIn(process_health.process_status(process.pid), ("stopped", "not-found"))

    @LINUX
    def test_the_pidfd_capability_is_read_from_the_documented_namespace(self):
        self.assertIs(process_control._PIDFD_OPEN, os.pidfd_open)
        self.assertIs(process_control._PIDFD_SEND, getattr(signal, "pidfd_send_signal", None))
        self.assertTrue(process_control._PIDFD_AVAILABLE)

    @LINUX
    def test_a_bound_member_is_signalled_through_the_descriptor(self):
        """The real descriptor route, with only the send recorded."""
        process = sleeper()
        self.addCleanup(stop, process)
        identity = process_health.process_health_identity(process.pid)
        sent = []
        self.assertIsNotNone(process_control._PIDFD_SEND)

        def record(descriptor, number, *rest):
            sent.append((descriptor, number))

        with mock.patch.object(process_control, "_PIDFD_SEND", record):
            result = process_control.signal(process_control.Member(process.pid, identity, False))
        self.assertEqual(result["mechanism"], "pidfd")
        self.assertEqual(result["result"], "signalled")
        self.assertEqual([number for _, number in sent], [signal.SIGKILL])
        # Only the send was stubbed, so the instance is still running.
        self.assertEqual(process_health.process_status(process.pid), "alive")

    @POSIX
    def test_the_pidfd_route_opens_verifies_sends_and_closes(self):
        """The descriptor discipline, independent of the host kernel."""
        process = sleeper()
        self.addCleanup(stop, process)
        identity = process_health.process_health_identity(process.pid)
        opened, sent = [], []

        def open_fake(pid, flags):
            opened.append((pid, flags))
            return os.open(os.devnull, os.O_RDONLY)

        def send_fake(descriptor, number):
            sent.append((descriptor, number))

        with mock.patch.object(process_control, "_PIDFD_AVAILABLE", True), \
                mock.patch.object(process_control, "_PIDFD_OPEN", open_fake), \
                mock.patch.object(process_control, "_PIDFD_SEND", send_fake):
            result = process_control.signal(process_control.Member(process.pid, identity, False))
        self.assertEqual(result["mechanism"], "pidfd")
        self.assertEqual(result["result"], "signalled")
        self.assertEqual(opened, [(process.pid, 0)])
        self.assertEqual([number for _, number in sent], [signal.SIGKILL])
        # The implementation closes the descriptor it opened.
        with self.assertRaises(OSError):
            os.fstat(sent[0][0])
        self.assertEqual(process_health.process_status(process.pid), "alive")

    @POSIX
    def test_a_group_signal_is_refused_for_a_process_that_does_not_lead_its_group(self):
        """Signalling the wrong group would reach this attempt's own tree."""
        process = sleeper()
        self.addCleanup(stop, process)
        identity = process_health.process_health_identity(process.pid)
        result = process_control.signal(
            process_control.Member(process.pid, identity, False), group=True)
        self.assertEqual(result["result"], "refused")
        self.assertEqual(result["mechanism"], "group-not-owned")
        self.assertEqual(process_health.process_status(process.pid), "alive")


class SessionContinuityTests(unittest.TestCase):
    """A matching session number is not a proven session.

    The reported defect: a session whose leader record is gone, or is now held by
    a different instance, could still authorise every process carrying the old
    number in its ``sid`` field, because the only check was that the member's
    creation stamp was newer than the owner's. That stamp shows the member was
    created later; it says nothing about which session it joined.
    """

    AMBIGUOUS = process_tree.Scan((424243,), False, "ambiguous", "session",
                                  "session-continuity-unproven", "leader-absent")
    REUSED = process_tree.Scan((424243,), False, "ambiguous", "session",
                               "session-leader-reused", "leader-reused")

    def claim(self):
        return {"pid": 424242, "identity": "linux-abc-100", "session": 424242,
                "scope": "session", "boot": "abc"}

    def observe(self, scan):
        with mock.patch.object(process_tree, "_scan", return_value=scan), \
                mock.patch.object(process_tree, "process_status", return_value="alive"), \
                mock.patch.object(process_control, "verify_process", return_value="not-found"):
            return (process_tree.tree_state(self.claim()),
                    process_control.authorize(self.claim()),
                    process_tree.live_pids(self.claim()))

    def test_a_reused_session_number_grants_no_authority_and_claims_nothing(self):
        state, authorization, _ = self.observe(self.REUSED)
        self.assertEqual(authorization.members, ())
        self.assertEqual(authorization.reason, "session-continuity-unproven")
        self.assertEqual(state["continuity"], "leader-reused")
        # Strangers on a recycled number are neither this tree's descendants nor
        # evidence that this tree is empty.
        self.assertEqual(state["descendants"], "unknown")
        self.assertIsNone(state["live"])
        self.assertFalse(process_tree.stopped(self.claim()))

    def test_an_absent_leader_keeps_the_observation_and_withholds_authority(self):
        state, authorization, scan = self.observe(self.AMBIGUOUS)
        self.assertEqual(authorization.members, ())
        self.assertEqual(authorization.reason, "session-continuity-unproven")
        self.assertEqual(scan.pids, (424243,))
        # The finding survives as a finding: something is still in the session.
        self.assertEqual(state["descendants"], "alive")
        self.assertEqual(state["live"], 1)
        self.assertEqual(state["continuity"], "leader-absent")
        self.assertFalse(process_tree.stopped(self.claim()))

    def test_an_empty_proven_session_is_still_absence(self):
        clean = process_tree.Scan((), True, "complete", "session", "session-scan-complete",
                                  "leader-current")
        with mock.patch.object(process_tree, "_scan", return_value=clean), \
                mock.patch.object(process_control, "verify_process", return_value="not-found"):
            state = process_tree.tree_state(self.claim())
            self.assertTrue(process_tree.stopped(self.claim()))
        self.assertEqual((state["descendants"], state["live"]), ("stopped", 0))

    def test_uncertain_custody_is_not_reported_as_clean(self):
        termination = deterministic._termination(
            {"owner": "not-found", "descendants": "unknown", "live": None,
             "enumeration": "ambiguous", "reason": "session-continuity-unproven",
             "scope": "session", "continuity": "leader-absent"},
            process_control.NO_AUTHORITY, ())
        self.assertEqual(deterministic._custody(termination), "uncertain")
        self.assertEqual(termination["continuity"], "leader-absent")
        self.assertIsNone(termination["remaining"])

    def test_a_proven_session_is_still_authorised(self):
        with mock.patch.object(process_tree, "_scan", return_value=ONE_MEMBER), \
                mock.patch.object(process_tree, "process_status", return_value="alive"), \
                mock.patch.object(process_control, "verify_process", return_value="alive"), \
                mock.patch.object(process_tree, "member_identity", return_value="linux-abc-200"):
            authorization = process_control.authorize(self.claim())
        self.assertEqual([member.pid for member in authorization.members], [424243])
        self.assertEqual(authorization.reason, "identity-bound-members")


@LINUX
class SyntheticSessionScanTests(unittest.TestCase):
    """Session-leader reuse, without asking the host to recycle a real PID."""

    def claim(self, **overrides):
        boot = process_tree._boot_id()
        self.assertIsNotNone(boot, "a claim is bound to the boot it was taken on")
        claim = {"pid": 424242, "identity": f"linux-{boot}-100", "session": 424242,
                 "scope": "session", "boot": boot}
        claim.update(overrides)
        return claim

    @staticmethod
    def read(records):
        def _read(pid):
            try:
                return records[pid]
            except KeyError:
                raise FileNotFoundError(pid) from None
        return _read

    def patch(self, records):
        return (mock.patch.object(process_tree.os, "listdir",
                                 return_value=[str(pid) for pid in records]),
                mock.patch.object(process_tree, "_stat_fields", side_effect=self.read(records)),
                mock.patch.object(process_tree, "process_status", return_value="alive"))

    def scan(self, records, claim):
        listing, records_of, liveness = self.patch(records)
        with listing, records_of, liveness:
            return process_tree._scan(claim, time.monotonic() + 5)

    def test_a_leader_held_by_another_instance_revokes_the_session(self):
        """The number was issued again, so its members are strangers."""
        claim = self.claim()
        scan = self.scan({424242: (b"S", 1, 424242, 900),
                          424243: (b"S", 424242, 424242, 200)}, claim)
        self.assertEqual(scan.continuity, "leader-reused")
        self.assertEqual(scan.reason, "session-leader-reused")
        self.assertEqual(scan.pids, (424243,))
        self.assertFalse(scan.complete)

    def test_a_newer_member_stamp_is_not_continuity(self):
        """The old check compared only the member's stamp, which always passes."""
        claim = self.claim()
        scan = self.scan({424243: (b"S", 424242, 424242, 999)}, claim)
        self.assertEqual(scan.continuity, "leader-absent")
        self.assertEqual(scan.reason, "session-continuity-unproven")
        self.assertEqual(scan.pids, (424243,))
        self.assertFalse(scan.complete)

    def test_the_recorded_leader_record_binds_the_session(self):
        claim = self.claim()
        records = {424242: (b"S", 1, 424242, 100),
                   424243: (b"S", 424242, 424242, 200)}
        listing, records_of, liveness = self.patch(records)
        with listing, records_of, liveness:
            scan = process_tree._scan(claim, time.monotonic() + 5)
            self.assertEqual(scan.continuity, "leader-current")
            self.assertEqual(scan.pids, (424243,))
            self.assertTrue(scan.complete)
            # The same record that places the member in the session yields its
            # stamp, so the binding does not need a second read.
            self.assertEqual(process_tree.member_identity(claim, 424243),
                             f"linux-{claim['boot']}-200")

    def test_an_empty_session_is_absence_whether_or_not_a_leader_remains(self):
        for records, continuity in (({}, "leader-absent"),
                                    ({424242: (b"S", 1, 424242, 100)}, "leader-current")):
            with self.subTest(records=records):
                claim = self.claim()
                listing, records_of, liveness = self.patch(records)
                with listing, records_of, liveness:
                    state = process_tree.tree_state(claim)
                    self.assertTrue(process_tree.stopped(claim))
                self.assertEqual(state["descendants"], "stopped")
                self.assertEqual(state["continuity"], continuity)

    def test_member_identity_refuses_a_session_its_leader_does_not_bind(self):
        claim = self.claim()
        for records in ({424242: (b"S", 1, 424242, 900),
                         424243: (b"S", 424242, 424242, 200)},
                        {424243: (b"S", 424242, 424242, 200)}):
            with self.subTest(records=records):
                with mock.patch.object(process_tree, "_stat_fields",
                                       side_effect=self.read(records)):
                    self.assertIsNone(process_tree.member_identity(claim, 424243))


class GroupCustodyTests(unittest.TestCase):
    """A group signal needs custody of the child, not just an observed leader."""

    @POSIX
    def test_a_group_signal_without_custody_is_refused(self):
        process = sleeper()
        self.addCleanup(stop, process)
        identity = process_health.process_health_identity(process.pid)
        self.assertTrue(process_control.group_leader(process.pid))
        result = process_control.signal(process_control.Member(process.pid, identity, True),
                                        group=True)
        self.assertEqual(result["result"], "refused")
        self.assertEqual(result["mechanism"], "group-without-custody")
        self.assertEqual(process_health.process_status(process.pid), "alive")

    @POSIX
    def test_a_leader_this_attempt_never_spawned_has_no_custody(self):
        observed, owned = sleeper(), sleeper()
        self.addCleanup(stop, observed)
        self.addCleanup(stop, owned)
        claim = process_tree.tree_claim(owned.pid)
        self.assertIsNotNone(claim)
        proof = process_control.custody(owned, claim)
        self.assertIsNotNone(proof)
        result = process_control.signal(
            process_control.Member(observed.pid,
                                   process_health.process_health_identity(observed.pid), True),
            group=True, custody=proof)
        self.assertEqual(result["result"], "refused")
        self.assertEqual(result["mechanism"], "group-without-custody")
        self.assertEqual(process_health.process_status(observed.pid), "alive")

    @POSIX
    def test_a_reaped_child_can_no_longer_confer_group_custody(self):
        process = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(0.2)"],
                                   start_new_session=True)
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        process.wait(timeout=30)
        self.assertIsNotNone(process.returncode)
        self.assertIsNone(process_control.custody(process, claim))
        # A proof offered over the freed identifier is still re-verified against
        # the instance, so it cannot end whatever holds that number now.
        forged = process_control.Custody(claim["pid"], claim["identity"])
        result = process_control.signal(
            process_control.Member(claim["pid"], claim["identity"], True),
            group=True, custody=forged)
        self.assertNotEqual(result["result"], "signalled")
        self.assertEqual(result["mechanism"], "group")

    @POSIX
    def test_the_group_signal_is_issued_before_the_child_is_reaped(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        process, ready = spawn_tree(root, "group")
        self.addCleanup(stop, process)
        self.assertTrue(ready)
        claim = process_tree.tree_claim(process.pid)
        result = deterministic._stop_tree(process, claim)
        self.assertEqual(result["signals"]["sample"][0]["mechanism"], "group")
        self.assertEqual(result["signals"]["sample"][0]["result"], "signalled")
        self.assertIsNotNone(process.returncode, "the stop path must reap the child")
        self.assertEqual(result["descendants"], "stopped")
        self.assertEqual(result["continuity"], "leader-absent")

    def test_an_unbound_observation_never_reaches_the_signal_loop(self):
        process = sleeper()
        self.addCleanup(stop, process)
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        ambiguous = process_tree.Scan((process.pid + 1,), False, "ambiguous", "session",
                                      "session-continuity-unproven", "leader-absent")
        with mock.patch.object(process_tree, "_scan", return_value=ambiguous), \
                mock.patch.object(process_tree, "process_status", return_value="alive"), \
                mock.patch.object(process_control, "verify_process", return_value="not-found"), \
                mock.patch.object(process_control, "signal") as signalled:
            result = deterministic._stop_tree(process, claim)
        signalled.assert_not_called()
        self.assertEqual(result["authority"]["members"], 0)
        self.assertEqual(result["authority"]["reason"], "session-continuity-unproven")
        self.assertIsNotNone(process.returncode)


class TerminationPathTests(unittest.TestCase):
    """The deterministic backend must use the authority API, not bare identifiers."""

    def test_the_direct_child_is_terminated_through_a_bound_handle(self):
        process = sleeper()
        self.addCleanup(stop, process)
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        with mock.patch.object(deterministic.subprocess, "run") as run:
            result = deterministic._stop_tree(process, claim)
        # Neither ``taskkill /T`` nor a bare-PID kill: the child was terminated
        # through the handle this attempt owns.
        run.assert_not_called()
        self.assertIn("signalled", result["signals"]["results"])
        self.assertEqual(result["signals"]["results"]["signalled"], 1)
        self.assertIsNotNone(process.poll())
        if claim["scope"] in process_tree.DURABLE_SCOPES:
            self.assertEqual(result["descendants"], "stopped")
            self.assertEqual(result["authority"]["scope"], "session")
        else:
            # A parent chain cannot prove absence, so custody stays unknown.
            self.assertEqual(result["descendants"], "unknown")
            self.assertEqual(result["authority"]["reason"], "scope-not-identity-bound")
        self.assertNotIn("identity-mismatch", result["signals"]["results"])

    def test_a_refused_member_signal_is_recorded_rather_than_read_as_cleanup(self):
        process = sleeper()
        self.addCleanup(stop, process)
        claim = process_tree.tree_claim(process.pid)
        identity = process_health.process_health_identity(process.pid)
        refusal = {"pid": 10, "result": "identity-mismatch", "mechanism": "pidfd",
                   "identity_matched": False, "group": False}
        granted = process_control.Authorization(
            process_control.Member(process.pid, identity, False),
            (process_control.Member(10, "linux-abc-1", False),),
            "session", "complete", "identity-bound-members")
        with mock.patch.object(process_control, "authorize", return_value=granted), \
                mock.patch.object(process_control, "signal", return_value=refusal):
            result = deterministic._stop_tree(process, claim)
        self.assertGreaterEqual(result["signals"]["results"]["identity-mismatch"], 1)
        self.assertEqual(result["signals"]["refused"][0]["result"], "identity-mismatch")
        self.assertEqual(result["authority"]["members"], 1)

    def test_an_unavailable_handle_ends_the_rounds_instead_of_spinning(self):
        process = sleeper()
        self.addCleanup(stop, process)
        claim = process_tree.tree_claim(process.pid)
        identity = process_health.process_health_identity(process.pid)
        unavailable = {"pid": 10, "result": "unavailable", "mechanism": "none",
                       "identity_matched": None, "group": False}
        granted = process_control.Authorization(
            process_control.Member(process.pid, identity, False),
            (process_control.Member(10, "linux-abc-1", False),),
            "session", "complete", "identity-bound-members")
        with mock.patch.object(process_control, "authorize", return_value=granted), \
                mock.patch.object(process_control, "signal", return_value=unavailable):
            result = deterministic._stop_tree(process, claim)
        self.assertEqual(result["signals"]["results"]["unavailable"], 1)
        self.assertEqual(result["signals"]["refused"][0]["mechanism"], "none")

    @POSIX
    def test_a_descendant_of_another_tree_is_never_signalled(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        first, first_ready = spawn_tree(root, "first")
        second, second_ready = spawn_tree(root, "second")
        self.addCleanup(stop, first)
        self.addCleanup(stop, second)
        self.assertTrue(first_ready and second_ready)
        first_claim = process_tree.tree_claim(first.pid)
        second_claim = process_tree.tree_claim(second.pid)
        self.assertIsNotNone(first_claim)
        self.assertIsNotNone(second_claim)
        self.assertEqual(first_claim["scope"], "session")
        self.assertEqual(second_claim["scope"], "session")
        first_members = process_control.authorize(first_claim).members
        second_members = process_control.authorize(second_claim).members
        self.assertTrue(first_members and second_members)
        self.assertFalse({member.pid for member in first_members}
                         & {member.pid for member in second_members},
                         "two sessions must not share a member")
        result = deterministic._stop_tree(first, first_claim)
        self.assertEqual(result["descendants"], "stopped")
        for member in second_members:
            self.assertEqual(process_health.process_status(member.pid), "alive",
                             "a member of another session must not be signalled")
        self.assertIsNone(second.poll())
