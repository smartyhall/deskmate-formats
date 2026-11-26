"""CLI states, trusted-task revalidation and supersession between prepare and run."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time
import unittest
from unittest.mock import patch

from deskmate_formats.supervisor import deterministic, deterministic_cli, procedures
from deskmate_formats.supervisor.task_queue import open_queue

from task_fixture import TASK_PATH, TaskRepo

PYTHON = str(Path(sys.executable).resolve())
SLEEP_SCRIPT = "import time\ntime.sleep(30)\n"


def manifest(**changes):
    return {
        "schema_version": 3, "id": "sample", "revision": 1, "idempotency_key": "sample-1",
        "title": "Hash a synthetic fixture", "description": "Hash one tracked fixture file.",
        "category": "verification", "profile": "offline", "resources": ["source-read"],
        "dependencies": [],
        "deterministic": {"procedure": "hash-files", "arguments": {"paths": ["fixture.txt"]}},
    } | changes


class DeterministicCliTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.repo = TaskRepo(self.root / "repo")
        (self.repo.path / "fixture.txt").write_bytes(b"synthetic fixture\n")
        self.repo.git("add", "fixture.txt")
        self.commit = self.repo.commit(manifest())
        self.queue = self.root / "queue"
        self.source = self.repo.source()
        self.state = self.root / "attempt"
        with open_queue(self.queue, source=self.source):
            pass
        with open_queue(self.queue) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)
            queue.decide(self.commit, TASK_PATH, self.candidate.review_token,
                         "accepted", "Synthetic acceptance")

    def prepare_task(self):
        return deterministic_cli.main([
            "prepare-task", "--state", str(self.state), "--campaign", "synthetic-campaign",
            "--queue", str(self.queue), "--working-directory", str(self.repo.path),
            "sample", "1", "--review-token", self.candidate.review_token])

    def test_prepare_task_binds_the_acceptance_and_run_refuses_without_revalidation(self):
        self.assertEqual(self.prepare_task(), 0)
        plan = json.loads((self.state / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["acceptance"]["review_token"], self.candidate.review_token)
        self.assertEqual(plan["acceptance"]["idempotency_key"], "sample-1")
        self.assertEqual(plan["acceptance"]["source"]["commit"], self.commit)
        code = deterministic_cli.main([
            "run", "--state", str(self.state),
            "--authorization", deterministic._plan_digest(plan)])
        self.assertEqual(code, 2)
        self.assertFalse((self.state / "attempt.json").exists())

    def test_superseded_acceptance_refuses_dispatch_and_reports_it(self):
        self.assertEqual(self.prepare_task(), 0)
        plan, token = deterministic.load_plan(self.state)
        second = self.repo.commit(manifest(revision=2, idempotency_key="sample-2",
                                           title="Second revision"))
        with open_queue(self.queue) as queue:
            fresh = queue.discover(second, TASK_PATH)
            queue.decide(second, TASK_PATH, fresh.review_token, "accepted", "Second acceptance")
        code = deterministic_cli.main(["run", "--state", str(self.state),
                                       "--authorization", token, "--queue", str(self.queue)])
        self.assertEqual(code, 2)
        self.assertFalse((self.state / "attempt.json").exists())

    def test_accepted_task_runs_end_to_end_with_a_zero_exit_state(self):
        self.assertEqual(self.prepare_task(), 0)
        plan, token = deterministic.load_plan(self.state)
        self.assertEqual(deterministic_cli.main(
            ["run", "--state", str(self.state), "--authorization", token,
             "--queue", str(self.queue)]), 0)
        outcome = json.loads((self.state / "outcome.json").read_text(encoding="utf-8"))
        self.assertEqual((outcome["state"], outcome["exit_status"]), ("completed", 0))

    def test_every_procedure_state_has_its_own_exit_code(self):
        self.assertEqual(set(deterministic_cli.EXIT_STATES),
                         {"completed", "failed", "cancelled", "timed-out", "uncertain"})
        self.assertEqual(len(set(deterministic_cli.EXIT_STATES.values())), 5)
        self.assertEqual(deterministic_cli.EXIT_STATES["completed"], 0)
        self.assertNotEqual(deterministic_cli.EXIT_STATES["failed"], 0)

    def test_failure_timing_out_and_cancellation_are_distinguishable(self):
        with patch.object(procedures, "build", return_value=[PYTHON, "-I", "-c", "raise SystemExit(3)\n"]):
            self.assertEqual(deterministic_cli.main([
                "prepare", "--state", str(self.root / "failed"), "--campaign", "c",
                "--procedure", "hash-files", "--arguments", '{"paths": ["fixture.txt"]}',
                "--working-directory", str(self.repo.path)]), 0)
        plan, token = deterministic.load_plan(self.root / "failed")
        self.assertEqual(deterministic_cli.main([
            "run", "--state", str(self.root / "failed"), "--authorization", token]), 1)

        for name, expected, timeout in (("timed", 4, 1), ("cancelled", 3, 60)):
            state = self.root / name
            with patch.object(procedures, "build", return_value=[PYTHON, "-I", "-c", SLEEP_SCRIPT]):
                self.assertEqual(deterministic_cli.main([
                    "prepare", "--state", str(state), "--campaign", "c",
                    "--procedure", "hash-files",
                    "--arguments", '{"paths": ["fixture.txt"]}',
                    "--working-directory", str(self.repo.path),
                    "--timeout", str(timeout)]), 0)
            _, token = deterministic.load_plan(state)
            result = {}
            thread = Thread(target=lambda: result.update(code=deterministic_cli.main(
                ["run", "--state", str(state), "--authorization", token])))
            thread.start()
            for _ in range(600):
                if (state / "attempt.json").exists():
                    break
                time.sleep(0.02)
            if name == "cancelled":
                self.assertEqual(deterministic_cli.main(
                    ["cancel", "--state", str(state), "--authorization", token]), 0)
            thread.join(60)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result["code"], expected, name)


if __name__ == "__main__":
    unittest.main()
