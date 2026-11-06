"""Exercise the operator interface across real process interruption and restart."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.supervisor.task_queue import open_queue

from task_fixture import REPOSITORY, TASK_PATH, TaskRepo, manifest


_CRASH = """
import os
import sys
from deskmate_formats.supervisor.task_queue import TaskQueue
from deskmate_formats.supervisor.task_cli import main

complete = TaskQueue._complete

def crash(queue, sequence, state):
    if sys.argv[1] == 'after':
        complete(queue, sequence, state)
        os._exit(91)
    with queue._write():
        queue._db.execute("UPDATE tasks SET state=?, resolved_at=prepared_at WHERE sequence=?",
                          (state, sequence))
        os._exit(91)

TaskQueue._complete = crash
raise SystemExit(main(sys.argv[2:]))
"""


class TaskCliTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.repo = TaskRepo(self.root / "repo")
        self.commit = self.repo.commit(manifest(description="Synthetic private canary"))
        self.private = self.root / "queue"
        self.command = [sys.executable, "-m", "deskmate_formats.supervisor.task_cli"]
        self.queue_args = ["--queue", str(self.private)]

    def invoke(self, *args, data=b"", expected=0):
        result = subprocess.run([*self.command, *self.queue_args, *args], input=data,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stderr.decode(errors="replace"))
        return result

    def initialize(self):
        self.invoke("init", "--checkout", str(self.repo.path), "--repository", REPOSITORY,
                    "--branch", "main", "--anchor", self.repo.anchor)
        result = self.invoke("discover", self.commit, TASK_PATH)
        candidate = json.loads(result.stdout)
        self.assertEqual(candidate["source"]["commit"], self.commit)
        self.assertEqual(candidate["manifest"]["description"], "Synthetic private canary")
        return candidate["review_token"]

    def decision_args(self, token, action="accept"):
        return (action, self.commit, TASK_PATH, "--review-token", token, "--reason-stdin")

    def test_read_only_review_and_explicit_rejection(self):
        self.invoke("list", expected=4)
        self.invoke("validate", data=json.dumps(manifest()).encode())
        self.invoke("validate", data=b'{"command":"echo private-canary"}', expected=2)
        self.invoke("dispatch", expected=2)
        token = self.initialize()
        self.invoke("inspect", "sample", "1", expected=3)
        self.assertIn(b"accepted=0, rejected=0", self.invoke("list").stdout)
        self.invoke(*self.decision_args(token), data=b"", expected=2)
        rejection = self.invoke(*self.decision_args(token, "reject"), data=b"Operator decline\r\n")
        self.assertEqual(json.loads(rejection.stdout)["state"], "rejected")
        listing = self.invoke("list").stdout
        self.assertIn(b"accepted=0, rejected=1", listing)
        self.assertNotIn(b"Operator decline", listing)
        self.assertEqual(json.loads(self.invoke("inspect", "sample", "1").stdout)["reason"],
                         "Operator decline")
        publication = ("publish", "sample", "1", "--journal", str(self.root / "journal"))
        self.invoke(*publication, "--journal-max-bytes", "1", expected=6)
        self.assertEqual(json.loads(self.invoke(*publication).stdout), {"created": True, "cursor": 1})
        self.assertEqual(json.loads(self.invoke(*publication).stdout), {"created": False, "cursor": 1})

    def test_process_exit_before_commit_preserves_unresolved_intent(self):
        token = self.initialize()
        result = subprocess.run([sys.executable, "-c", _CRASH, "before", *self.queue_args,
                                 *self.decision_args(token)], input=b"Explicit acceptance",
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 91, result.stderr)
        self.assertEqual(json.loads(self.invoke("inspect", "sample", "1").stdout)["state"], "unresolved")
        self.invoke(*self.decision_args(token), data=b"Retry", expected=5)
        settled = self.invoke("abandon", "sample", "1", "--review-token", token, "--reason-stdin",
                              data=b"Crash investigated")
        self.assertEqual(json.loads(settled.stdout)["state"], "abandoned")

    def test_process_exit_after_commit_recovers_one_receipt(self):
        token = self.initialize()
        result = subprocess.run([sys.executable, "-c", _CRASH, "after", *self.queue_args,
                                 *self.decision_args(token)], input=b"Explicit acceptance",
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 91, result.stderr)
        retry = self.invoke(*self.decision_args(token), data=b"Second delivery")
        receipt = json.loads(retry.stdout)
        self.assertEqual((receipt["state"], receipt["created"], receipt["reason"]),
                         ("accepted", False, "Explicit acceptance"))
        self.assertIn(b"accepted=1", self.invoke("list").stdout)

    def test_concurrent_processes_admit_at_most_one_receipt(self):
        token = self.initialize()
        argv = [*self.command, *self.queue_args, *self.decision_args(token)]
        with subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as first:
            with subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) as second:
                for child in (first, second):
                    child.stdin.write(b"Explicit acceptance")
                    child.stdin.close()
                    child.stdin = None
                results = [child.communicate(timeout=30) for child in (first, second)]
        self.assertIn(0, (first.returncode, second.returncode))
        created = []
        for child, (stdout, stderr) in zip((first, second), results):
            if child.returncode == 0:
                created.append(json.loads(stdout)["created"])
            else:
                self.assertEqual(child.returncode, 4, stderr)
                self.assertIn(b"busy", stderr)
        self.assertEqual(created.count(True), 1)
        with open_queue(self.private) as queue:
            self.assertEqual(len(queue.list()), 1)
