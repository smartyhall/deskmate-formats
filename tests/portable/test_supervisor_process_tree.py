"""Owner death is not descendant death: bounded, read-only tree inspection.

These tests fence the observation contract, not one code path: the owner verdict
and the descendant verdict are independent, absence is only termination inside a
durable scope, and no enumeration limit may be reported as a complete scan.
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
from deskmate_formats.supervisor import process_tree

SPAWNER = (
    "import subprocess, sys, time\n"
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
    "open(sys.argv[1], 'w').write('spawned')\n"
    "time.sleep(30)\n"
)

POSIX = unittest.skipIf(os.name == "nt", "POSIX session semantics")


def kill(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=30)
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


class ProcessTreeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    def spawn(self):
        marker = self.root / "spawned"
        kwargs = {} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen([sys.executable, "-I", "-c", SPAWNER, str(marker)],
                                   **kwargs)
        self.addCleanup(kill, process.pid)
        for _ in range(600):
            if marker.exists():
                break
            time.sleep(0.02)
        self.assertTrue(marker.exists(), "the synthetic spawner never reported")
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        self.addCleanup(self.clean_tree, claim)
        return process, claim

    def clean_tree(self, claim):
        """Fixture cleanup only, not the production path.

        This test created the tree and has not reaped the member below, so it may
        end what it made. Production termination goes through
        ``process_control``, which grants no authority over a Windows parent
        chain precisely because that chain can name an unrelated process.
        """
        for _ in range(5):
            scan = process_tree.live_pids(claim)
            for pid in scan.pids:
                kill(pid)
            if not scan.pids:
                return
            time.sleep(0.1)

    def test_an_owner_that_exited_still_reports_a_living_descendant(self):
        process, claim = self.spawn()
        self.assertEqual(process_tree.tree_state(claim)["descendants"], "alive")
        kill(process.pid)
        process.wait(timeout=30)
        for _ in range(100):
            state = process_tree.tree_state(claim)
            if state["owner"] in process_tree.OWNER_GONE:
                break
            time.sleep(0.02)
        state = process_tree.tree_state(claim)
        self.assertIn(state["owner"], process_tree.OWNER_GONE)
        # The whole point: a dead owner says nothing about what it started.
        self.assertEqual(state["descendants"], "alive")
        self.assertFalse(process_tree.stopped(claim))
        self.clean_tree(claim)
        if claim["scope"] in process_tree.DURABLE_SCOPES:
            self.assertTrue(process_tree.stopped(claim))
        else:
            self.assertEqual(process_tree.live_pids(claim).pids, ())

    def test_a_stopped_tree_reports_no_descendants(self):
        """The owner's absence and the tree's emptiness are separate questions.

        A complete scan of the recorded session that finds no live member is
        positive evidence of termination, so the descendant verdict is
        ``stopped`` even though the owner itself is ``not-found``. Deriving the
        descendant verdict from the owner verdict would report ``not-found``
        here and refuse every honest reclamation after a clean exit.
        """
        process = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(0.2)"],
                                   **({} if os.name == "nt" else {"start_new_session": True}))
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        process.wait(timeout=30)
        for _ in range(100):
            if process_tree.stopped(claim):
                break
            time.sleep(0.02)
        state = process_tree.tree_state(claim)
        self.assertIn(state["owner"], process_tree.OWNER_GONE)
        if state["scope"] in process_tree.DURABLE_SCOPES:
            # A session cannot lose a member to reparenting, so no member found
            # after a complete walk is positive evidence of termination.
            self.assertEqual(state["descendants"], "stopped")
            self.assertEqual(state["live"], 0)
            self.assertEqual(state["enumeration"], "complete")
            self.assertTrue(process_tree.stopped(claim))
        else:
            # A Windows parent chain loses a grandchild as soon as the parent
            # between them exits, so it never proves absence.
            self.assertEqual(state["descendants"], "unknown")
            self.assertIsNone(state["live"])
            self.assertIn(state["reason"], ("scope-loses-orphans",
                                             "unverified-child-identities"))
            self.assertFalse(process_tree.stopped(claim))

    def test_owner_absence_is_not_propagated_to_the_tree(self):
        """The reported conflation, pinned independently of the host scope."""
        clean = process_tree.Scan((), True, "complete", "session", "session-scan-complete")
        claim = {"pid": 1, "identity": "linux-x-1", "session": 1, "scope": "session"}
        with mock.patch.object(process_tree, "verify_process", return_value="not-found"), \
                mock.patch.object(process_tree, "_scan", return_value=clean):
            state = process_tree.tree_state(claim)
            self.assertEqual((state["owner"], state["descendants"], state["live"]),
                             ("not-found", "stopped", 0))
            self.assertTrue(process_tree.stopped(claim))
        # The same clean tree with a live owner is still not a stopped tree.
        with mock.patch.object(process_tree, "verify_process", return_value="alive"), \
                mock.patch.object(process_tree, "_scan", return_value=clean):
            state = process_tree.tree_state(claim)
        self.assertEqual(state["descendants"], "stopped")
        self.assertFalse(process_tree.stopped(claim))

    @unittest.skipIf(os.name != "nt", "only a parent chain can lose an intermediate")
    def test_a_grandchild_behind_a_dead_parent_is_not_proof_of_absence(self):
        """Windows: one exit between the owner and a grandchild hides it.

        The chain is walked from the owner's identifier, so a descendant whose
        own parent has exited is simply not in the map. The verdict must be
        ``unknown``: reporting ``stopped`` here would authorise reclamation over
        a live process.
        """
        owner_script = (
            "import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, '-I', sys.argv[1], sys.argv[2], "
            "sys.argv[3], sys.argv[4]])\n"
            "time.sleep(60)\n")
        middle_script = (
            "import os, subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, '-I', sys.argv[1], sys.argv[2]])\n"
            "open(sys.argv[3], 'w').write(str(os.getpid()))\n"
            "time.sleep(60)\n")
        leaf_script = ("import os, sys, time\n"
                       "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
                       "time.sleep(60)\n")
        paths = {}
        for name, source in (("owner", owner_script), ("middle", middle_script),
                             ("leaf", leaf_script)):
            paths[name] = self.root / f"{name}.py"
            paths[name].write_text(source, encoding="utf-8")
        leaf_pid, middle_pid = self.root / "leaf.pid", self.root / "middle.pid"
        owner = subprocess.Popen(
            [sys.executable, "-I", "-c", owner_script, str(paths["middle"]),
             str(paths["leaf"]), str(leaf_pid), str(middle_pid)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.addCleanup(kill, owner.pid)
        claim = process_tree.tree_claim(owner.pid)
        self.assertIsNotNone(claim)
        for _ in range(600):
            if all(path.exists() and path.read_text() for path in (leaf_pid, middle_pid)):
                break
            time.sleep(0.02)
        self.assertTrue(all(path.exists() and path.read_text()
                            for path in (leaf_pid, middle_pid)),
                        "the synthetic chain never reported its members")
        self.addCleanup(kill, int(leaf_pid.read_text()))
        self.assertEqual(process_tree.tree_state(claim)["descendants"], "alive")
        middle = int(middle_pid.read_text())
        leaf = int(leaf_pid.read_text())
        kill(middle)
        for _ in range(250):
            if process_health.process_status(middle) in ("stopped", "not-found"):
                break
            time.sleep(0.02)
        self.assertIn(process_health.process_status(middle), ("stopped", "not-found"),
                      "the intermediate parent never exited")
        # The grandchild is still running, and the walk cannot reach it: its own
        # parent is gone, so nothing in the snapshot carries the owner as parent.
        self.assertEqual(process_health.process_status(leaf), "alive")
        scan = process_tree.live_pids(claim)
        self.assertNotIn(leaf, scan.pids,
                         "a grandchild behind a dead parent must stay out of reach")
        state = process_tree.tree_state(claim)
        self.assertNotEqual(state["descendants"], "stopped")
        self.assertFalse(process_tree.stopped(claim))

    def test_an_unknown_claim_is_never_read_as_stopped(self):
        for value in (None, {}, {"pid": 0}, {"pid": "1"}, {"pid": 4, "scope": "unclaimed"}):
            with self.subTest(value=value):
                state = process_tree.tree_state(value)
                self.assertEqual(state["descendants"], "unknown")
                self.assertIsNone(state["live"])
                self.assertFalse(process_tree.stopped(value))
                scan = process_tree.live_pids(value)
                self.assertEqual(scan.pids, ())
                self.assertFalse(scan.complete)

    def test_claim_scope_says_whether_descendants_can_be_proven(self):
        claim = process_tree.tree_claim(os.getpid())
        self.assertIsNotNone(claim)
        if os.name == "nt":
            self.assertEqual(claim["scope"], "parent-chain")
            self.assertNotIn("session", claim)
        else:
            self.assertEqual(claim["scope"],
                             "session" if os.getsid(0) == os.getpid() else "process")
            if claim["scope"] == "session":
                self.assertEqual(claim["session"], os.getpid())
                self.assertTrue(claim["boot"])

    @POSIX
    def test_a_scope_that_cannot_be_proven_never_reports_stopped(self):
        """A non-leader's parent chain loses orphans, so it can only assert life."""
        process = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(2)"])
        self.addCleanup(kill, process.pid)
        claim = process_tree.tree_claim(process.pid)
        self.assertIsNotNone(claim)
        self.assertEqual(claim["scope"], "process")
        process.wait(timeout=30)
        state = process_tree.tree_state(claim)
        self.assertEqual(state["owner"], "not-found")
        self.assertEqual(state["descendants"], "unknown")
        self.assertEqual(state["enumeration"], "incomplete")
        self.assertIsNone(state["live"])
        self.assertFalse(process_tree.stopped(claim))

    @POSIX
    def test_an_observation_bound_to_another_boot_is_not_evidence(self):
        """Start times are boot-relative; comparing across a reboot is unsound."""
        _, claim = self.spawn()
        self.assertEqual(claim["scope"], "session")
        stale = dict(claim, boot="00000000-0000-0000-0000-000000000000")
        state = process_tree.tree_state(stale)
        self.assertEqual(state["enumeration"], "unavailable")
        self.assertEqual(state["reason"], "boot-changed")
        self.assertEqual(state["descendants"], "unknown")
        self.assertIsNone(state["live"])
        self.assertFalse(process_tree.stopped(stale))
        # The identity itself carries the same binding, so a recorded lease
        # inherits the guard without an extra field.
        self.assertEqual(process_health.identity_boot(claim["identity"]), claim["boot"])

    def test_enumeration_limits_are_never_reported_as_complete(self):
        _, claim = self.spawn()
        with mock.patch.object(process_tree, "MAX_PROCESSES", 1):
            state = process_tree.tree_state(claim)
        self.assertEqual(state["enumeration"], "truncated")
        # A cut-short walk may still have seen a member; what it may never do is
        # conclude that the tree is empty.
        self.assertNotEqual(state["descendants"], "stopped")
        self.assertFalse(process_tree.stopped(claim))

    def test_live_pids_separates_findings_from_the_absence_of_findings(self):
        process, claim = self.spawn()
        scan = process_tree.live_pids(claim)
        self.assertTrue(scan.pids)
        self.assertNotIn(process.pid, scan.pids)
        # Findings are reported for any scope; only a durable scope may also
        # claim that their absence means the tree is empty.
        self.assertEqual(scan.complete, claim["scope"] in process_tree.DURABLE_SCOPES)
        self.clean_tree(claim)
        scan = process_tree.live_pids(claim)
        self.assertEqual(scan.pids, ())
        self.assertEqual(scan.complete, claim["scope"] in process_tree.DURABLE_SCOPES)


class IdentityStampTests(unittest.TestCase):
    """The identity encodes a creation stamp; reuse checks depend on it."""

    def test_only_recorded_forms_parse(self):
        self.assertEqual(process_health.start_stamp("linux-abc-4096"), 4096)
        self.assertEqual(process_health.start_stamp("win-1f4"), 0x1F4)
        for value in (None, 4, "", "linux-abc", "win-", "linux-abc-xyz", "other-1"):
            with self.subTest(value=value):
                self.assertIsNone(process_health.start_stamp(value))

    def test_the_boot_binding_survives_in_a_linux_identity(self):
        self.assertEqual(process_health.identity_boot("linux-abc-4096"), "abc")
        self.assertIsNone(process_health.identity_boot("win-1f4"))
        self.assertIsNone(process_health.identity_boot(None))
