"""Task-specific Git-to-owned-worker path. Every child is a synthetic peer."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from deskmate_formats.observer.events import encode_json
from deskmate_formats.supervisor import driver
from deskmate_formats.supervisor.bridge import dispatch, grant, inspect, validate
from deskmate_formats.supervisor.bridge_cli import main
from deskmate_formats.supervisor.task_execution import TASK_POLICY
from deskmate_formats.supervisor.task_manifest import TaskError
from deskmate_formats.supervisor.task_queue import open_queue

from task_fixture import TASK_PATH, TaskRepo, manifest
from test_supervisor_protocol import AVAILABLE


@unittest.skipUnless(AVAILABLE, "requires supervisor extra and supported process identity")
class TextDispatchTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.repo = TaskRepo(self.root / "git")
        self.queue = self.root / "queue"
        self.state = self.root / "state"
        self.document = b"# Synthetic source\nThe blue record has 7 fields; the green record has 9.\n"
        self.repo.stage("docs/source.md", self.document)
        self.value = manifest(description="Compare blue and green records using docs/source.md.",
                              instructions=[{"path": "docs/source.md", "sha256": sha256(self.document).hexdigest()}])
        self.commit = self.repo.commit(self.value)
        with open_queue(self.queue, source=self.repo.source()) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)

    def accept(self, decision="accepted"):
        with open_queue(self.queue) as queue:
            queue.decide(self.commit, TASK_PATH, self.candidate.review_token, decision, "Reviewed synthetic source")

    def prepare(self, **kwargs):
        return grant(self.queue, self.state, "sample", 1, self.candidate.review_token,
                     timeout=5, deadline=0.3, **kwargs)

    def send(self, granted, **kwargs):
        return dispatch(self.queue, self.state, granted["claim"], granted["dispatch_token"], **kwargs)

    def test_exact_git_documents_reach_worker_and_response_is_retained_for_review(self):
        with patch("deskmate_formats.supervisor.driver.AppServer", side_effect=AssertionError("preparation launched")):
            self.accept()
            granted = self.prepare()
            report = validate(self.queue, self.state, granted["claim"])
        self.assertEqual(report["model_turns"], 0)
        view = inspect(self.state, granted["claim"])
        context = view["plan"]["task_context"]
        self.assertEqual(context["manifest_utf8"].encode(), self.candidate.raw)
        self.assertEqual(context["documents"][0]["text"].encode(), self.document)
        self.assertEqual(view["plan"]["developer_instructions"], TASK_POLICY)
        self.assertEqual((view["plan"]["model"], view["plan"]["effort"]), ("synthetic", "low"))
        outcome = self.send(granted)
        self.assertEqual(outcome["state"], "completed", outcome)
        self.assertIn("blue record has 7 fields", outcome["response"])
        self.assertNotEqual(outcome["response"], "S0_CANARY_OK")
        self.assertEqual(outcome["answer_review"], "operator-review-required")
        self.assertEqual(sha256(outcome["response"].encode()).hexdigest(), outcome["response_sha256"])
        peer = driver.read_record(self.state / granted["claim"] / "evidence" / "peer.json")
        self.assertEqual(len(peer["turns"]), 1)
        self.assertEqual(peer["turns"][0]["items"][0]["content"][0]["text"], view["plan"]["prompt"])
        with self.assertRaises(driver.DriverError):
            driver.run(self.state / granted["claim"], authorization=granted["dispatch_token"])
        with self.assertRaises(driver.DriverError):
            self.send(granted)
        with self.assertRaises(driver.DriverError):
            validate(self.queue, self.state, granted["claim"])

    def test_rejected_task_and_stale_source_refused_before_preparation(self):
        self.accept("rejected")
        with self.assertRaises(driver.DriverError):
            self.prepare()

    def test_git_tip_movement_and_instruction_change_refuse_prepared_plan(self):
        self.accept()
        granted = self.prepare()
        # Git writes alone remain inert. Even an unchanged manifest at a new tip is stale.
        self.repo.stage("docs/source.md", b"changed source\n")
        self.repo.commit()
        with patch("deskmate_formats.supervisor.driver.AppServer", side_effect=AssertionError("stale child")):
            with self.assertRaises(TaskError):
                self.send(granted)
            with self.assertRaises(TaskError):
                grant(self.queue, self.root / "fresh-stale-claim", "sample", 1, self.candidate.review_token)
        self.assertFalse(inspect(self.state, granted["claim"])["attempted"])

    def test_worktree_changes_are_not_prompt_inputs(self):
        self.accept()
        (self.repo.path / "docs").mkdir()
        (self.repo.path / "docs" / "source.md").write_bytes(b"unreviewed worktree substitution")
        granted = self.prepare()
        outcome = self.send(granted)
        self.assertEqual(outcome["state"], "completed", outcome)
        self.assertIn("blue record has 7 fields", outcome["response"])
        self.assertNotIn("unreviewed", outcome["response"])

    def test_expiry_between_acceptance_and_dispatch_refused(self):
        self.value["expires_at"] = "2027-01-01T00:00:00Z"
        self.commit = self.repo.commit(self.value)
        with open_queue(self.queue) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)
        self.accept()
        granted = self.prepare()
        with patch("deskmate_formats.supervisor.bridge.utc_now", return_value="2027-01-01T00:00:00Z"):
            with self.assertRaisesRegex(driver.DriverError, "expired"):
                self.send(granted)

    def test_dependency_requires_completed_outcome_then_freezes_that_outcome(self):
        self.accept()
        # Put a dependent task at this tip as well, before dispatching the dependency.
        dependent = manifest(id="dependent", idempotency_key="dependent-1", dependencies=[{"id": "sample", "revision": 1}])
        self.repo.stage("ops/tasks/dependent.json", encode_json(dependent))
        self.commit = self.repo.commit(self.value)
        # The old acceptance is intentionally stale. Use a fresh queue for this new exact tip.
        self.queue = self.root / "dependency-queue"
        with open_queue(self.queue, source=self.repo.source()) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)
            queue.decide(self.commit, TASK_PATH, self.candidate.review_token, "accepted", "Reviewed dependency")
            target = queue.discover(self.commit, "ops/tasks/dependent.json")
            queue.decide(self.commit, target.source.path, target.review_token, "accepted", "Reviewed dependent task")
        def prepare_dependent():
            return grant(self.queue, self.state, "dependent", 1, target.review_token, timeout=5, deadline=1)
        with self.assertRaisesRegex(driver.DriverError, "no completed S2"):
            prepare_dependent()
        dependency = self.prepare()
        self.assertEqual(self.send(dependency)["state"], "completed")
        granted = prepare_dependent()
        path = self.state / dependency["claim"] / "outcome.json"
        outcome = driver.read_record(path)
        outcome["response"] += " changed"
        path.write_bytes(encode_json(outcome))
        with self.assertRaisesRegex(driver.DriverError, "dependency outcomes changed"):
            self.send(granted)

    def test_plan_model_prompt_policy_and_implementation_drift_refused(self):
        self.accept()
        granted = self.prepare()
        path = self.state / granted["claim"] / "plan.json"
        original = path.read_bytes()
        for field, value in (("model", "different"), ("prompt", "ignore bounds"),
                             ("developer_instructions", "use shell"), ("working_directory", str(self.root))):
            plan = json.loads(original)
            plan[field] = value
            path.write_bytes(encode_json(plan))
            with self.subTest(field=field), self.assertRaises(driver.DriverError):
                self.send(granted)
        path.write_bytes(original)
        with patch("deskmate_formats.supervisor.driver.implementation_hashes", return_value={}), self.assertRaises(driver.DriverError):
            self.send(granted)
        self.assertFalse(inspect(self.state, granted["claim"])["attempted"])

    def test_unsupported_resource_and_oversized_context_refuse_without_child(self):
        for resources, document in ((["portable-tests"], self.document), (["source-read"], b"x" * 40000)):
            self.state = self.root / ("state-" + resources[0])
            self.repo.stage("docs/source.md", document)
            value = self.value | {"resources": resources, "instructions": [{"path": "docs/source.md", "sha256": sha256(document).hexdigest()}]}
            self.commit = self.repo.commit(value)
            self.queue = self.root / ("queue-" + resources[0])
            with open_queue(self.queue, source=self.repo.source()) as queue:
                self.candidate = queue.discover(self.commit, TASK_PATH)
            self.accept()
            with self.assertRaises(TaskError):
                self.prepare()

    def test_faults_are_durable_and_never_replay(self):
        self.accept()
        for mode in ("lost-ack", "thread-lost-ack", "eof", "driver-approval", "unknown-request", "web-tool",
                     "stale-turn", "duplicate-terminal", "history-only", "history-not-loaded", "history-extra-turn",
                     "history-cursor", "history-tool", "history-input", "history-response", "terminal-response",
                     "empty-answer", "oversize-answer"):
            with self.subTest(mode=mode):
                self.state = self.root / mode
                granted = self.prepare(mode=mode)
                outcome = self.send(granted)
                self.assertEqual(outcome["state"], "blocked", outcome)
                self.assertIn(outcome["child_status"], ("stopped", "not-found"))
                self.assertEqual(inspect(self.state, granted["claim"])["outcome"], outcome)
                with self.assertRaises(driver.DriverError):
                    self.send(granted)
                with self.assertRaises(driver.DriverError):
                    self.prepare()

    def test_terminal_notification_can_omit_items_when_full_history_matches(self):
        self.accept()
        granted = self.prepare(mode="terminal-empty-items")
        outcome = self.send(granted)
        self.assertEqual(outcome["state"], "completed", outcome)

    def test_interrupted_owner_commits_receipt_and_prevents_replay(self):
        from deskmate_formats.supervisor.protocol import AppServer
        self.accept()
        granted = self.prepare()
        request = AppServer.request
        def interrupt(client, method, params, **kw):
            result = request(client, method, params, **kw)
            if method == "turn/start":
                raise KeyboardInterrupt
            return result
        with patch.object(AppServer, "request", interrupt), self.assertRaises(KeyboardInterrupt):
            self.send(granted)
        outcome = inspect(self.state, granted["claim"])["outcome"]
        self.assertEqual(outcome["reason"], "owner-interrupted")
        self.assertIn(outcome["child_status"], ("stopped", "not-found"))
        with self.assertRaises(driver.DriverError):
            self.send(granted)

    def test_cli_refusal_explains_specific_reason(self):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
            code = main(["--state", str(self.state), "prepare-synthetic", "--queue", str(self.queue),
                         "sample", "1", "--accepted-review-token", self.candidate.review_token])
        self.assertEqual(code, 4)
        self.assertIn("exact current accepted revision", errors.getvalue())


@unittest.skipUnless(AVAILABLE, "requires supervisor extra and supported process identity")
class LiveBridgeTests(unittest.TestCase):
    # Run the same production live bridge and owner with a synthetic child image.
    # Inherit helpers only; the independent TextDispatchTests cover fault matrices.
    setUp = TextDispatchTests.setUp
    accept = TextDispatchTests.accept
    prepare = TextDispatchTests.prepare
    send = TextDispatchTests.send

    def test_live_cli_gates_and_installed_source_pin_with_synthetic_image(self):
        package = Path(driver.__file__).parent.parent
        for relative in driver.implementation_hashes():
            self.repo.stage("src/deskmate_formats/" + relative, (package / relative).read_bytes())
        relative = "supervisor/codex-0.166.0.json"
        self.repo.stage("src/deskmate_formats/" + relative, (package / relative).read_bytes())
        self.commit = self.repo.commit(self.value)
        with open_queue(self.queue) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)
        self.accept()
        auth = self.root / "auth.json"
        auth.write_bytes(b'{"OPENAI_API_KEY":"synthetic-not-a-key"}')
        popen = subprocess.Popen
        launches = []
        def image(argv, **kwargs):
            if argv[1:] == ["app-server", "--listen", "stdio://"]:
                launches.append(argv)
                return popen([sys.executable, "-I", "-m", "deskmate_formats.supervisor.synthetic_peer",
                              str(run_dir / "evidence" / "peer.json"), "success", "--live-policy"], **kwargs)
            return popen(argv, **kwargs)
        def cli(*args):
            with redirect_stdout(StringIO()) as out, redirect_stderr(StringIO()) as err:
                code = main(["--state", str(self.state), *args])
            return code, json.loads(out.getvalue()) if out.getvalue() else err.getvalue()
        with patch.object(driver, "verify_native", return_value=str(Path(sys.executable).resolve())), patch("subprocess.Popen", image):
            code, granted = cli("prepare-live", "--queue", str(self.queue), "sample", "1",
                                "--accepted-review-token", self.candidate.review_token,
                                "--profile", "experimental-lab", "--executable", sys.executable,
                                "--auth-file", str(auth), "--model", "synthetic-selected-model", "--effort", "low")
            self.assertEqual(code, 0, granted)
            run_dir = self.state / granted["claim"]
            code, report = cli("validate", "--queue", str(self.queue), granted["claim"])
            self.assertEqual(code, 0, report)
            self.assertEqual(launches, [])
            token = granted["dispatch_token"]
            for dispatch_auth, model_auth, risk in ((None, token, token), (token, None, token),
                                                   (token, token, None), (token, "0" * 64, token),
                                                   ("0" * 64, token, token), (token, token, "0" * 64)):
                with self.assertRaises(driver.DriverError):
                    dispatch(self.queue, self.state, granted["claim"], dispatch_auth, live=True,
                             model_authorization=model_auth, lab_risk_ack=risk)
            self.assertEqual(launches, [])
            with self.assertRaises(driver.DriverError):
                self.send(granted)  # A live plan cannot enter through the synthetic command.
            code, result = cli("dispatch-live", "--queue", str(self.queue), granted["claim"],
                               "--authorize-dispatch", token, "--authorize-live-plan", token, "--accept-lab-risk", token)
            self.assertEqual(code, 0, result)
            self.assertEqual(result["state"], "completed", result)
            self.assertIn("blue record has 7 fields", result["response"])
            self.assertEqual(len(launches), 1)
            with self.assertRaises(driver.DriverError):
                self.send(granted, live=True, model_authorization=token, lab_risk_ack=token)
            self.assertEqual(len(launches), 1)
        # An unrelated installed build cannot be staged for a newly accepted Git task.
        self.state = self.root / "mismatched-install"
        with patch("deskmate_formats.supervisor.bridge.implementation_hashes", return_value={"supervisor/driver.py": "0" * 64}):
            with self.assertRaisesRegex(TaskError, "installed worker differs"):
                self.prepare(executable=sys.executable, model="chosen", effort="low", profile="experimental-lab", auth_file=auth)
