"""Deterministic attempt lifecycle: real subprocesses, durable receipts, no replay."""

from hashlib import sha256
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Event, Thread
import time
import unittest
from unittest.mock import patch

from deskmate_formats.observer.events import encode_json
from deskmate_formats.supervisor import deterministic, procedures

PYTHON = str(Path(sys.executable).resolve())
ARTIFACT_SCRIPT = (
    "import os, pathlib, sys\n"
    "target = pathlib.Path(os.environ['DESKMATE_ARTIFACTS']) / 'report.json'\n"
    "target.write_text('{\"files\": []}')\n"
    "print('{\"files\": []}')\n"
)
SLEEP_SCRIPT = "import time\ntime.sleep(30)\n"


class DeterministicTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.state = self.root / "attempt"

    def prepare(self, script, *, timeout=10, campaign="synthetic-campaign"):
        with patch.object(procedures, "build", return_value=[PYTHON, "-I", "-c", script]):
            return deterministic.prepare(
                self.state, campaign=campaign, procedure="hash-files",
                arguments={"paths": ["README.md"]},
                working_directory=str(self.root), timeout_seconds=timeout)

    def test_successful_attempt_records_evidence_artifacts_and_structure(self):
        attempt = self.prepare(ARTIFACT_SCRIPT)
        outcome = deterministic.run(self.state, authorization=attempt.plan_sha256)
        self.assertEqual(outcome["state"], "completed")
        self.assertEqual(outcome["exit_status"], 0)
        self.assertFalse(outcome["timed_out"])
        self.assertEqual(outcome["artifacts"], [{
            "path": "report.json", "size": 13,
            "sha256": sha256(b'{"files": []}').hexdigest()}])
        self.assertEqual(outcome["structured_result"], {"files": []})
        self.assertEqual(outcome["stdout"]["excerpt"].strip(), '{"files": []}')
        self.assertEqual(outcome["stdout"]["sha256"],
                         sha256((self.state / "stdout.bin").read_bytes()).hexdigest())
        self.assertEqual(outcome["inference"]["required"], False)
        self.assertEqual(outcome["inference"]["measurements"], [])
        self.assertTrue(outcome["argv"][0].endswith(("python.exe", "python3", "python")))
        self.assertEqual(outcome["limitations"][0][:25], "cooperating-owner custody")
        # The attempt is single-use and a plain replay is refused.
        with self.assertRaises(deterministic.DeterministicError):
            deterministic.run(self.state, authorization=attempt.plan_sha256)

    def test_nonzero_exit_is_failed_not_completed(self):
        attempt = self.prepare("raise SystemExit(3)\n")
        outcome = deterministic.run(self.state, authorization=attempt.plan_sha256)
        self.assertEqual((outcome["state"], outcome["exit_status"], outcome["reason"]),
                         ("failed", 3, "nonzero-exit"))

    def test_timeout_stops_the_tree_and_is_recorded(self):
        attempt = self.prepare(SLEEP_SCRIPT, timeout=1)
        started = time.monotonic()
        outcome = deterministic.run(self.state, authorization=attempt.plan_sha256)
        elapsed = time.monotonic() - started
        self.assertEqual((outcome["state"], outcome["exit_status"]), ("timed-out", "timeout"))
        self.assertTrue(outcome["timed_out"])
        self.assertLess(elapsed, 20)
        self.assertGreaterEqual(outcome["elapsed_seconds"], 0.5)

    def test_authorized_cancellation_interrupts_a_running_attempt(self):
        attempt = self.prepare(SLEEP_SCRIPT, timeout=60)
        result = {}
        thread = Thread(target=lambda: result.update(
            outcome=deterministic.run(self.state, authorization=attempt.plan_sha256)))
        thread.start()
        for _ in range(400):
            if (self.state / "attempt.json").exists():
                break
            time.sleep(0.02)
        deterministic.cancel(self.state, authorization=attempt.plan_sha256)
        thread.join(60)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result["outcome"]["state"], "cancelled")
        self.assertTrue(result["outcome"]["cancelled"])

    def test_authorization_mismatch_and_bad_plans_write_no_fence(self):
        attempt = self.prepare("print('never')\n")
        with self.assertRaises(deterministic.DeterministicError):
            deterministic.run(self.state, authorization="0" * 64)
        self.assertFalse((self.state / "attempt.json").exists())
        with self.assertRaises(deterministic.DeterministicError):
            deterministic.cancel(self.state, authorization=attempt.plan_sha256)

    def test_interrupted_attempt_is_uncertain_and_never_replayed(self):
        attempt = self.prepare("print('never')\n")
        deterministic._write_once(self.state / "attempt.json", {
            "plan_sha256": attempt.plan_sha256, "started_at_utc": "2026-01-01T00:00:00Z",
            "attempt_id": attempt.attempt_id})
        view = deterministic.status(self.state)
        self.assertEqual(view["state"], "uncertain")
        self.assertTrue(view["requires_inspection"])
        with self.assertRaises(deterministic.DeterministicError):
            deterministic.run(self.state, authorization=attempt.plan_sha256)
        recovered = deterministic.recover(self.state)
        self.assertEqual((recovered["state"], recovered["reason"]),
                         ("uncertain", "attempt-without-terminal-record"))
        self.assertEqual(deterministic.recover(self.state), recovered)

    def test_recovery_refuses_a_live_child(self):
        attempt = self.prepare(SLEEP_SCRIPT, timeout=60)
        result = {}
        thread = Thread(target=lambda: result.update(
            outcome=deterministic.run(self.state, authorization=attempt.plan_sha256)))
        thread.start()
        for _ in range(400):
            if (self.state / "child.json").exists():
                break
            time.sleep(0.02)
        with self.assertRaises(deterministic.DeterministicError):
            deterministic.recover(self.state)
        deterministic.cancel(self.state, authorization=attempt.plan_sha256)
        thread.join(60)
        self.assertEqual(result["outcome"]["state"], "cancelled")

    def test_output_capture_is_bounded_but_the_stream_is_drained(self):
        attempt = self.prepare("import sys\nsys.stdout.write('x' * 400000)\n")
        outcome = deterministic.run(self.state, authorization=attempt.plan_sha256)
        self.assertEqual(outcome["state"], "completed")
        self.assertTrue(outcome["stdout"]["truncated"])
        self.assertEqual(outcome["stdout"]["bytes"], 400000)
        self.assertEqual(outcome["stdout"]["captured_bytes"], deterministic.MAX_STDOUT_BYTES)
        self.assertEqual((self.state / "stdout.bin").stat().st_size,
                         deterministic.MAX_STDOUT_BYTES)

    def test_changed_implementation_or_revision_is_refused(self):
        attempt = self.prepare("print('never')\n")
        with patch.object(deterministic, "implementation_hashes", return_value={"x.py": "0" * 64}):
            with self.assertRaisesRegex(deterministic.DeterministicError, "implementation changed"):
                deterministic.run(self.state, authorization=attempt.plan_sha256)
        self.assertFalse((self.state / "attempt.json").exists())

        other = self.root / "second"
        with patch.object(deterministic, "source_revision", return_value="a" * 40):
            attempt = deterministic.prepare(
                other, campaign="synthetic-campaign", procedure="hash-files",
                arguments={"paths": ["README.md"]}, working_directory=str(self.root))
        with patch.object(deterministic, "source_revision", return_value="b" * 40):
            with self.assertRaisesRegex(deterministic.DeterministicError, "revision changed"):
                deterministic.run(other, authorization=attempt.plan_sha256)

    def test_reservation_is_acquired_and_released_even_on_failure(self):
        attempt = self.prepare("raise SystemExit(1)\n")
        events = []

        def reservation(plan):
            events.append(("acquire", tuple(plan["resources"])))
            return lambda: events.append(("release", ()))

        deterministic.run(self.state, authorization=attempt.plan_sha256,
                          reservation=reservation)
        self.assertEqual(events, [("acquire", ("source-read",)), ("release", ())])

    def test_status_is_offline_and_reports_the_frozen_plan(self):
        attempt = self.prepare("print('x')\n")
        view = deterministic.status(self.state)
        self.assertEqual((view["state"], view["attempted"], view["terminal"]),
                         ("prepared", False, False))
        self.assertEqual(view["procedure"], "hash-files")
        self.assertEqual(view["arguments"], {"paths": ["README.md"]})
        self.assertTrue(view["implementation_unchanged"])

    def test_prepare_refuses_existing_directories_and_unknown_procedures(self):
        self.state.mkdir()
        with self.assertRaises(deterministic.DeterministicError):
            deterministic.prepare(self.state, campaign="c", procedure="hash-files",
                                  arguments={"paths": ["a"]}, working_directory=str(self.root))
        with self.assertRaises(procedures.ProcedureError):
            deterministic.prepare(self.root / "other", campaign="c", procedure="shell",
                                  arguments={}, working_directory=str(self.root))


class PlanEncodingTests(unittest.TestCase):
    def test_immutable_records_refuse_overwrite(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "state"
            deterministic.storage_directory(root, create=True)
            deterministic._write_once(root / "plan.json", {"a": 1})
            with self.assertRaises(deterministic.DeterministicError):
                deterministic._write_once(root / "plan.json", {"a": 2})
            self.assertEqual((root / "plan.json").read_bytes(),
                             encode_json({"a": 1}) + b"\n")
