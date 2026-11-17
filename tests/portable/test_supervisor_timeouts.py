"""S3 timeout selection, actual application, durable receipts and unchanged S0/S2 bounds."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
import unittest
from unittest.mock import patch

from deskmate_formats.observer._private_storage import storage_directory
from deskmate_formats.observer.events import encode_json
from deskmate_formats.supervisor import driver, editing, workspace
from deskmate_formats.supervisor.editing_cli import main
from deskmate_formats.supervisor.task_queue import open_queue
from task_fixture import TASK_PATH, manifest
import test_supervisor_editing as editing_tests


class TimeoutPolicyTests(unittest.TestCase):
    def test_s0_s2_refuse_editing_deadline_before_preparation_and_at_dispatch(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        context = {"class": "text-analysis-v1", "manifest_utf8": json.dumps(manifest()), "documents": []}
        for kind, kwargs in (("s0", {}), ("s2", {"binding": {"id": "synthetic"}, "task_context": context})):
            with self.subTest(kind=kind):
                path = root / kind
                with self.assertRaises(driver.DriverError):
                    driver.prepare(path, deadline=300, **kwargs)
                self.assertFalse(path.exists())
                driver.prepare(path, deadline=60, **kwargs)
                plan, _ = driver.load_plan(path)
                plan["deadline"] = 300
                (path / "plan.json").write_bytes(encode_json(plan))
                _, token = driver.load_plan(path)
                with patch.object(driver, "AppServer", side_effect=AssertionError("unexpected launch")):
                    with self.assertRaises(driver.DriverError):
                        driver.run(path, authorization=token, accepted_binding=kwargs.get("binding"),
                                   dispatch_authorization=token if kind == "s2" else None)
                self.assertFalse((path / "attempt.json").exists())

    def test_validation_profile_limits_and_partial_output_timeout_receipts(self):
        base = Path(self.enterContext(TemporaryDirectory()))
        root = storage_directory(base / "receipts", create=True)
        cases = (("test-portable-full", workspace.TEST_PROFILES["portable-full"], 1800),
                 ("test-synthetic-unit", workspace.TEST_PROFILES["synthetic-unit"], 600),
                 ("publication-audit", ["-I", "-c", workspace.AUDIT], 600),
                 ("reuse", ["-m", "reuse", "lint"], 600))
        for label, args, limit in cases:
            with self.subTest(label=label):
                def timeout(argv, **kwargs):
                    self.assertEqual(argv, [str(Path(sys.executable).resolve()), *args])
                    self.assertEqual(kwargs["timeout"], limit)
                    kwargs["stdout"].write(b"partial validation output\n")
                    raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
                with patch.object(workspace.subprocess, "run", side_effect=timeout):
                    receipt = workspace.command(root, base, label, args)
                self.assertEqual(receipt, driver.read_record(root / (label + ".json")))
                self.assertEqual(receipt["exit_status"], "timeout")
                self.assertEqual(receipt["timeout_seconds"], limit)
                self.assertEqual((root / (label + ".output")).read_bytes(), b"partial validation output\n")
                self.assertEqual(receipt["output_sha256"], sha256(b"partial validation output\n").hexdigest())


class EditingTimeoutTests(unittest.TestCase):
    setUp = editing_tests.EditingTests.setUp
    accept = editing_tests.EditingTests.accept
    send = editing_tests.EditingTests.send

    def prepare(self, *, deadline=300, mode="success"):
        return editing.grant(self.queue, self.state, "sample", 1, self.candidate.review_token,
                             task_class="source-edit-v1", authorize_checkpoint=True,
                             deadline=deadline, mode=mode, timeout=2)

    def cli_prepare(self, seconds):
        with redirect_stdout(StringIO()) as out, redirect_stderr(StringIO()) as err:
            code = main(["--state", str(self.state), "prepare-synthetic", "--queue", str(self.queue),
                         "sample", "1", "--accepted-review-token", self.candidate.review_token,
                         "--task-class", "source-edit-v1", "--plan-local-checkpoint",
                         "--observation-seconds", str(seconds)])
        return code, json.loads(out.getvalue()) if out.getvalue() else err.getvalue()

    def test_selected_cli_deadline_is_frozen_and_used_after_sixty_seconds(self):
        self.accept()
        code, grant = self.cli_prepare(120)
        self.assertEqual(code, 0, grant)
        plan, _ = driver.load_plan(self.state / grant["claim"])
        self.assertEqual(plan["deadline"], 120)
        offset = 0
        event = driver._event
        def advance(*args, **kwargs):
            nonlocal offset
            result = event(*args, **kwargs)
            if args[4] is not None:
                offset = 61
            return result
        # Advance the owner's clock beyond S0/S2's limit without a real minute-long wait.
        with patch.object(driver, "monotonic", side_effect=lambda: monotonic() + offset), patch.object(driver, "_event", advance):
            result = self.send(grant)
        self.assertEqual(result["state"], "completed", result)
        self.assertGreaterEqual(driver.read_record(self.state / grant["claim"] / "outcome.json")["elapsed_host_seconds"], 61)

    def test_invalid_s3_bounds_refuse_before_reserving_a_workspace(self):
        self.accept()
        for deadline in (0, -1, 301, float("inf"), float("nan")):
            with self.subTest(deadline=deadline), self.assertRaises(driver.DriverError):
                self.prepare(deadline=deadline)
            self.assertFalse(self.state.exists())
        for deadline in (0, 301):
            code, result = self.cli_prepare(deadline)
            self.assertEqual(code, 4, result)
            self.assertFalse(self.state.exists())
        grant = self.prepare()
        plan, _ = driver.load_plan(self.state / grant["claim"])
        self.assertEqual(plan["deadline"], 300)
        # The dispatch gate also refuses an over-bound plan even with its new exact digest.
        plan["deadline"] = 301
        (self.state / grant["claim"] / "plan.json").write_bytes(encode_json(plan))
        _, token = driver.load_plan(self.state / grant["claim"])
        grant["plan_sha256"] = token
        with self.assertRaises(driver.DriverError):
            self.send(grant)
        self.assertFalse((self.state / grant["claim"] / "attempt.json").exists())

    def test_changed_deadline_invalidates_the_original_exact_grant(self):
        self.accept()
        grant = self.prepare()
        root = self.state / grant["claim"]
        plan, _ = driver.load_plan(root)
        plan["deadline"] = 299
        (root / "plan.json").write_bytes(encode_json(plan))
        with self.assertRaisesRegex(driver.DriverError, "exact dispatch"):
            self.send(grant)
        self.assertFalse((root / "attempt.json").exists())

    def test_observation_timeout_retains_outcome_and_forbids_replay(self):
        self.accept()
        grant = self.prepare(deadline=0.02, mode="history-only")
        result = self.send(grant)
        self.assertEqual(result["state"], "blocked")
        root = self.state / grant["claim"]
        outcome = driver.read_record(root / "outcome.json")
        self.assertEqual(outcome["reason"], "observation deadline; execution outcome remains unresolved")
        self.assertTrue(Path(grant["workspace"]).is_dir())
        before = (root / "outcome.json").read_bytes()
        with self.assertRaises(driver.DriverError): self.send(grant)
        self.assertEqual((root / "outcome.json").read_bytes(), before)

    def test_portable_full_timeout_blocks_checkpoint_and_retains_workspace(self):
        value = self.candidate.manifest
        value["development"]["test_profiles"] = ["portable-full"]
        self.commit = self.repo.commit(value)
        with open_queue(self.queue) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)
        self.accept()
        grant = self.prepare()
        real_run = subprocess.run
        def timeout(argv, **kwargs):
            if argv[1:] == workspace.TEST_PROFILES["portable-full"]:
                self.assertEqual(kwargs["timeout"], 1800)
                kwargs["stdout"].write(b"portable-full partial output\n")
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            return real_run(argv, **kwargs)
        with patch.object(subprocess, "run", side_effect=timeout):
            result = self.send(grant)
        self.assertEqual(result["state"], "blocked", result)
        test = result["validation"][0]
        self.assertEqual((test["state"], test["exit_status"], test["timeout_seconds"]), ("failed", "timeout", 1800))
        root = self.state / grant["claim"]
        self.assertEqual(test["output_sha256"], sha256((root / "test-portable-full.output").read_bytes()).hexdigest())
        self.assertFalse((root / "checkpoint-object.json").exists())
        self.assertTrue(Path(grant["workspace"]).is_dir())
        self.assertEqual(workspace.git(grant["workspace"], "rev-parse", "HEAD").decode().strip(), self.source)
        with self.assertRaises(driver.DriverError): self.send(grant)
        plan, token = driver.load_plan(root)
        with self.assertRaises(driver.DriverError):
            workspace.checkpoint(root, plan["edit_workspace"], token, token, {"state": "completed"})
