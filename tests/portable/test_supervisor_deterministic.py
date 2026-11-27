"""Deterministic attempt lifecycle: real subprocesses, durable receipts, no replay."""

from hashlib import sha256
import os
from pathlib import Path
import shutil
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
        (self.root / "README.md").write_text("synthetic input\n", encoding="utf-8")

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
        # The recorded executable is this running interpreter, whatever its name.
        self.assertEqual(outcome["argv"][0], str(Path(sys.executable).resolve()))
        self.assertEqual(outcome["limitations"][0][:25], "cooperating-owner custody")
        # The attempt is single-use and a plain replay is refused.
        with self.assertRaises(deterministic.DeterministicError):
            deterministic.run(self.state, authorization=attempt.plan_sha256)

    def test_a_record_from_another_plan_is_never_read_as_this_attempt(self):
        """A predictable record path must not let stale evidence look current."""
        first = self.prepare("print('one')\n")
        self.assertEqual(deterministic.run(self.state, authorization=first.plan_sha256)["state"],
                         "completed")
        other = self.root / "other"
        with patch.object(procedures, "build", return_value=[PYTHON, "-I", "-c", "print('two')\n"]):
            second = deterministic.prepare(
                other, campaign="synthetic-campaign", procedure="hash-files",
                arguments={"paths": ["README.md"]},
                working_directory=str(self.root), timeout_seconds=10)
        self.assertNotEqual(first.plan_sha256, second.plan_sha256)
        shutil.copyfile(self.state / "outcome.json", other / "outcome.json")
        with self.assertRaisesRegex(deterministic.DeterministicError, "another plan"):
            deterministic.status(other)
        with self.assertRaisesRegex(deterministic.DeterministicError, "another plan"):
            deterministic.recover(other)

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
        # No child record means no tree handle: whether anything is still
        # running cannot be observed, so recovery must not simply close the book.
        with self.assertRaisesRegex(deterministic.DeterministicError, "cannot be shown stopped"):
            deterministic.recover(self.state)
        recovered = deterministic.recover(self.state, confirm_descendants_stopped=True)
        self.assertEqual((recovered["state"], recovered["reason"]),
                         ("uncertain", "attempt-without-terminal-record"))
        self.assertEqual(recovered["descendants"], "unknown")
        self.assertTrue(recovered["descendants_confirmed"])
        self.assertTrue(recovered["requires_manual_process_check"])
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
        # An operator confirmation may not override a positively live tree.
        with self.assertRaises(deterministic.DeterministicError):
            deterministic.recover(self.state, confirm_descendants_stopped=True)
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
        with patch.object(deterministic, "implementation_binding",
                          return_value={"sha256": "0" * 64}):
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


def _symlinks_supported(directory):
    target = Path(directory) / "_link_target.txt"
    link = Path(directory) / "_link_probe.txt"
    try:
        target.write_text("x", encoding="utf-8")
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        return False
    finally:
        for path in (link, target):
            try:
                path.unlink()
            except OSError:
                pass
    return True


class IntegrityTests(unittest.TestCase):
    """Every identity the plan binds is re-established before dispatch."""

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.state = self.root / "attempt"
        (self.root / "README.md").write_text("synthetic input\n", encoding="utf-8")
        self.links = _symlinks_supported(self.root)

    def prepare(self, *, paths=("README.md",), procedure="hash-files", arguments=None,
                timeout=10, **extra):
        arguments = arguments if arguments is not None else {"paths": list(paths)}
        return deterministic.prepare(
            self.state, campaign="synthetic-campaign", procedure=procedure,
            arguments=arguments, working_directory=str(self.root),
            timeout_seconds=timeout, **extra)

    def test_requested_revision_that_cannot_be_established_is_refused(self):
        with self.assertRaisesRegex(deterministic.DeterministicError, "cannot be established"):
            self.prepare(source_commit="a" * 40)
        self.assertFalse(self.state.exists())

    def test_changed_working_tree_input_after_authorization_is_refused(self):
        attempt = self.prepare()
        (self.root / "README.md").write_text("changed after approval\n", encoding="utf-8")
        with patch.object(deterministic, "_execute",
                          side_effect=AssertionError("must not execute")):
            with self.assertRaisesRegex(deterministic.DeterministicError, "inputs changed"):
                deterministic.run(self.state, authorization=attempt.plan_sha256)
        self.assertFalse((self.state / "attempt.json").exists())

    def test_untracked_executable_input_appearing_after_authorization_is_refused(self):
        attempt = self.prepare(procedure="repository-audit", arguments={})
        (self.root / "notes-appearing-later.md").write_text("new\n", encoding="utf-8")
        with patch.object(deterministic, "_execute",
                          side_effect=AssertionError("must not execute")):
            with self.assertRaisesRegex(deterministic.DeterministicError, "inputs changed"):
                deterministic.run(self.state, authorization=attempt.plan_sha256)

    def test_plan_binds_acceptance_and_refuses_without_revalidation(self):
        acceptance = {"queue_id": "queue", "sequence": 1, "id": "sample", "revision": 1,
                      "idempotency_key": "sample-1", "review_token": "t" * 64,
                      "source": {"repository": "https://example.invalid/lab/synthetic.git",
                                 "branch": "main", "commit": "a" * 40,
                                 "path": "ops/tasks/sample.json", "blob": "b" * 40,
                                 "sha256": "c" * 64},
                      "procedure": "hash-files", "arguments": {"paths": ["README.md"]}}
        attempt = self.prepare(acceptance=acceptance)
        with patch.object(deterministic, "_execute",
                          side_effect=AssertionError("must not execute")):
            with self.assertRaisesRegex(deterministic.DeterministicError, "requires revalidation"):
                deterministic.run(self.state, authorization=attempt.plan_sha256)
            with self.assertRaisesRegex(deterministic.DeterministicError, "changed after preparation"):
                deterministic.run(self.state, authorization=attempt.plan_sha256,
                                  revalidate=lambda value: {**value, "revision": 2})
        outcome = deterministic.run(
            self.state, authorization=attempt.plan_sha256,
            revalidate=lambda value: dict(value))
        self.assertEqual(outcome["state"], "completed")
        self.assertEqual(outcome["acceptance_binding"]["id"], "sample")

    def test_acceptance_binding_is_visible_in_the_terminal_outcome(self):
        acceptance = {"queue_id": "queue", "sequence": 1, "id": "sample", "revision": 1,
                      "idempotency_key": "sample-1", "review_token": "t" * 64,
                      "source": {}, "procedure": "hash-files",
                      "arguments": {"paths": ["README.md"]}}
        attempt = self.prepare(acceptance=acceptance)
        outcome = deterministic.run(self.state, authorization=attempt.plan_sha256,
                                    revalidate=lambda value: dict(value))
        self.assertEqual(outcome["acceptance_binding"]["review_token"], "t" * 64)
        stored = deterministic.status(self.state)["outcome"]
        self.assertEqual(stored["acceptance_binding"]["id"], "sample")

    def test_acceptance_binding_must_match_the_requested_procedure(self):
        acceptance = {"queue_id": "queue", "sequence": 1, "id": "sample", "revision": 1,
                      "idempotency_key": "sample-1", "review_token": "t" * 64,
                      "source": {}, "procedure": "reuse-lint", "arguments": {}}
        with self.assertRaisesRegex(deterministic.DeterministicError, "does not match"):
            self.prepare(acceptance=acceptance)

    def test_working_directory_reached_through_a_link_is_refused(self):
        if not self.links:
            self.skipTest("this host cannot create symlinks")
        real = self.root / "real"
        real.mkdir()
        alias = self.root / "alias"
        os.symlink(real, alias)
        with self.assertRaisesRegex(deterministic.DeterministicError, "canonical path"):
            deterministic.prepare(self.state, campaign="c", procedure="hash-files",
                                  arguments={"paths": ["README.md"]},
                                  working_directory=str(alias))

    def test_input_that_is_a_link_is_refused(self):
        if not self.links:
            self.skipTest("this host cannot create symlinks")
        os.symlink(self.root / "README.md", self.root / "alias.txt")
        with self.assertRaisesRegex(deterministic.DeterministicError, "link"):
            self.prepare(paths=("alias.txt",))

    def test_artifact_byte_and_count_limits_are_enforced(self):
        with patch.object(procedures, "build", return_value=[PYTHON, "-I", "-c", ARTIFACT_SCRIPT]):
            attempt = self.prepare(timeout=20)
        with patch.object(deterministic, "MAX_ARTIFACT_BYTES", 8):
            outcome = deterministic.run(self.state, authorization=attempt.plan_sha256)
        self.assertEqual(outcome["state"], "completed")
        self.assertEqual(outcome["artifacts"], [])
        self.assertIn("byte limit", outcome["artifact_error"])
        self.assertTrue((self.state / "outcome.json").exists())

    def test_stdout_exactly_at_the_limit_is_not_truncated(self):
        with patch.object(procedures, "build",
                          return_value=[PYTHON, "-I", "-c", "import sys\nsys.stdout.write('x'*8)\n"]):
            attempt = deterministic.prepare(
                self.root / "second", campaign="c", procedure="hash-files",
                arguments={"paths": ["README.md"]}, working_directory=str(self.root))
        with patch.object(deterministic, "MAX_STDOUT_BYTES", 8):
            outcome = deterministic.run(self.root / "second",
                                        authorization=attempt.plan_sha256)
        self.assertFalse(outcome["stdout"]["truncated"])
        self.assertEqual((outcome["stdout"]["bytes"], outcome["stdout"]["captured_bytes"]),
                         (8, 8))

    def test_interrupted_record_write_leaves_no_partial_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "state"
            deterministic.storage_directory(root, create=True)
            with patch("deskmate_formats.supervisor.deterministic.os.replace",
                       side_effect=OSError("simulated crash")):
                with self.assertRaises(OSError):
                    deterministic._write_once(root / "plan.json", {"a": 1})
            self.assertFalse((root / "plan.json").exists())
            self.assertEqual([path.name for path in root.iterdir()], [])
            deterministic._write_once(root / "plan.json", {"a": 1})
            self.assertTrue((root / "plan.json").exists())
