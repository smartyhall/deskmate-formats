"""Observation is not permission: control must bind to a process instance.

The reported defect was that a scan's PIDs were handed to a kill with no identity
check, that an unknown status was silently retained as "live", and that a Windows
parent chain could associate an unrelated process with a reused owner number.
These tests fence the *authority* contract separately from the observation one:
only an identity-bound member of a kernel-held scope may be signalled, a changed
identity is refused, and an unrelated process is never touched.
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

SLEEPER = "import time; time.sleep(60)"
SPAWNER = (
    "import subprocess, sys, time\n"
    "subprocess.Popen([sys.executable, '-I', '-c', 'import time; time.sleep(60)'])\n"
    "open(sys.argv[1], 'w').write('spawned')\n"
    "time.sleep(60)\n"
)

# A session claim whose session scan reports one member, and an owner that is
# demonstrably alive: the shape every authority question is asked about.
SESSION_CLAIM = {"pid": 424242, "identity": "linux-abc-100", "session": 424242,
                 "scope": "session", "boot": "abc"}
ONE_MEMBER = process_tree.Scan((424243,), True, "complete", "session", "session-scan-complete")


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
                mock.patch.object(process_control, "process_health_identity",
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
                mock.patch.object(process_control, "process_health_identity", return_value=None):
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
                mock.patch.object(process_control, "verify_process", return_value="alive"), \
                mock.patch.object(process_control, "process_health_identity",
                                  return_value="win-1b"):
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

    def test_a_member_bound_to_its_observed_identity_is_signalled(self):
        process = sleeper()
        self.addCleanup(stop, process)
        identity = process_health.process_health_identity(process.pid)
        self.assertIsNotNone(identity)
        result = process_control.signal(
            process_control.Member(process.pid, identity,
                                   process_control.group_leader(process.pid)))
        self.assertEqual(result["result"], "signalled")
        self.assertTrue(result["identity_matched"])
        self.assertIn(result["mechanism"], ("pidfd", "pid", "process-handle"))
        process.wait(timeout=30)
        self.assertIn(process_health.process_status(process.pid), ("stopped", "not-found"))

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
                mock.patch.object(process_control, "signal", return_value=refusal), \
                mock.patch.object(deterministic, "_STOP_ROUNDS", 2):
            result = deterministic._stop_tree(process, claim)
        self.assertEqual(result["signals"]["results"]["identity-mismatch"], 2)
        self.assertEqual(result["signals"]["refused"][0]["result"], "identity-mismatch")
        self.assertEqual(result["authority"]["members"], 1)

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
