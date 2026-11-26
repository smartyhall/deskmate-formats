"""Owner death is not descendant death: bounded, read-only tree inspection."""

import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from deskmate_formats.supervisor import process_tree

SPAWNER = (
    "import subprocess, sys, time\n"
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
    "open(sys.argv[1], 'w').write('spawned')\n"
    "time.sleep(30)\n"
)


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
        for _ in range(5):
            pids = process_tree.live_pids(claim)
            for pid in pids:
                kill(pid)
            if not pids:
                return
            time.sleep(0.1)

    def test_an_owner_that_exited_still_reports_a_living_descendant(self):
        process, claim = self.spawn()
        self.assertEqual(process_tree.tree_state(claim)["descendants"], "alive")
        kill(process.pid)
        process.wait(timeout=30)
        for _ in range(100):
            state = process_tree.tree_state(claim)
            if state["owner"] in ("stopped", "not-found"):
                break
            time.sleep(0.02)
        state = process_tree.tree_state(claim)
        self.assertIn(state["owner"], ("stopped", "not-found"))
        # The whole point: a dead owner says nothing about what it started.
        self.assertEqual(state["descendants"], "alive")
        self.assertFalse(process_tree.stopped(claim))
        self.clean_tree(claim)
        self.assertTrue(process_tree.stopped(claim))

    def test_a_stopped_tree_reports_no_descendants(self):
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
        self.assertEqual(state["descendants"], "stopped")
        self.assertTrue(process_tree.stopped(claim))

    def test_an_unknown_claim_is_never_read_as_stopped(self):
        for value in (None, {}, {"pid": 0}, {"pid": "1"}):
            state = process_tree.tree_state(value)
            self.assertEqual(state["descendants"], "unknown")
            self.assertFalse(process_tree.stopped(value))
        self.assertEqual(process_tree.live_pids({}), [])

    def test_claim_scope_says_whether_descendants_can_be_proven(self):
        claim = process_tree.tree_claim(os.getpid())
        self.assertIsNotNone(claim)
        self.assertIn(claim["scope"], ("session", "process"))
        if os.name == "nt":
            self.assertEqual(claim["scope"], "process")
        else:
            self.assertEqual(claim["scope"],
                             "session" if os.getsid(0) == os.getpid() else "process")
