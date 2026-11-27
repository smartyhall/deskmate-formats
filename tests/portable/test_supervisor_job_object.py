"""Job Object containment: the object owns what a parent chain only describes.

The synthetic tree is a spawner that starts one long-lived grandchild and then
sleeps. Killing only the spawner reproduces the failure the parent chain cannot
see: the grandchild survives. A job that still reports an active member proves
containment observation without trusting the owner, and terminating the job must
leave both the object and the process table empty.
"""

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from deskmate_formats.observer.process_health import process_status
from deskmate_formats.supervisor import job_object

WINDOWS = unittest.skipIf(os.name != "nt", "Job Objects exist only on Windows")

GRANDCHILD = ("import os, sys, time\n"
              "open(sys.argv[1], 'w').write(str(os.getpid()))\n"
              "time.sleep(60)\n")
SPAWNER = ("import subprocess, sys\n"
           "subprocess.Popen([sys.executable, '-I', '-c', sys.argv[2], sys.argv[1]])\n"
           "import time; time.sleep(60)\n")


def kill(pid):
    subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=30)


@WINDOWS
class JobObjectTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        try:
            self.job = self.enterContext(job_object.Job())
        except job_object.JobError as error:
            self.skipTest(f"this host cannot provide a job object ({error})")
        self.addCleanup(self.cleanup_tree)

    def cleanup_tree(self):
        try:
            self.job.terminate()
        except job_object.JobError:
            pass
        self.job.close()

    def spawner(self):
        marker = self.root / "grandchild.pid"
        process = subprocess.Popen([sys.executable, "-I", "-c", SPAWNER,
                                    str(marker), GRANDCHILD],
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            self.job.assign(process.pid)
        except job_object.JobError as error:
            process.kill()
            self.skipTest(f"this host refuses job assignment ({error})")
        self.addCleanup(kill, process.pid)
        for _ in range(600):
            if marker.exists() and marker.read_text():
                break
            time.sleep(0.02)
        self.assertTrue(marker.exists() and marker.read_text(),
                        "the synthetic spawner never reported a grandchild")
        return process, int(marker.read_text())

    def test_the_job_still_owns_a_grandchild_after_its_owner_dies(self):
        process, grandchild = self.spawner()
        # The grandchild inherits the job on creation, so membership covers a
        # process the parent chain can only describe.
        state = self.job.state()
        self.assertIsNotNone(state)
        self.assertGreaterEqual(state["active"], 2)
        kill(process.pid)
        process.wait(timeout=30)
        state = self.job.state()
        self.assertIsNotNone(state)
        self.assertGreaterEqual(
            state["active"], 1,
            "a job must keep reporting members after the owner that started them is gone")
        self.assertEqual(job_object.containment({"job": self.job})["descendants"], "alive")
        terminated = self.job.terminate()
        self.assertIsNotNone(terminated)
        self.assertEqual(terminated["active"], 0)
        for _ in range(100):
            if process_status(grandchild) in ("stopped", "not-found"):
                break
            time.sleep(0.02)
        self.assertIn(process_status(grandchild), ("stopped", "not-found"))
        self.assertEqual(
            job_object.containment({"job": self.job}),
            {"descendants": "stopped", "enumeration": "complete",
             "reason": "job-membership-empty", "remaining": 0})

    def test_closing_the_handle_terminates_the_membership(self):
        process, grandchild = self.spawner()
        self.job.close()
        for _ in range(200):
            if process_status(grandchild) in ("stopped", "not-found"):
                break
            time.sleep(0.02)
        self.assertIn(process_status(grandchild), ("stopped", "not-found"))


class AvailabilityTests(unittest.TestCase):
    def test_availability_is_reported_rather_than_assumed(self):
        supported, reason = job_object.supported()
        self.assertEqual(supported, os.name == "nt")
        if not supported:
            self.assertEqual(reason, "not-windows")
            # Off Windows the module must refuse, not silently contain nothing.
            self.assertEqual(job_object.containment({"job": None}),
                             {"descendants": "unknown", "enumeration": "unavailable",
                              "reason": "no-job-handle"})

    def test_a_claim_without_a_job_is_unknown(self):
        for claim in (None, {}, {"pid": 1}, {"job": "not-a-job"}):
            with self.subTest(claim=claim):
                self.assertEqual(job_object.containment(claim)["descendants"], "unknown")
