"""S1 discovery/acceptance to separately gated S0 synthetic worker and read-only HTTP."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from deskmate_formats.observer.agent_feed import AgentJournalFeed
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.supervisor.bridge import dispatch, grant, inspect
from deskmate_formats.supervisor.driver import DriverError, load_plan
from deskmate_formats.observer._private_storage import journal_lock
from deskmate_formats.supervisor.task_queue import open_queue

from task_fixture import TASK_PATH, TaskRepo, manifest
from test_observer_http import LocalObserver
from test_supervisor_protocol import AVAILABLE


@unittest.skipUnless(AVAILABLE, "requires supervisor extra and supported process identity")
class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.repo = TaskRepo(self.root / "git")
        self.queue = self.root / "queue"
        self.state = self.root / "bridge"
        self.commit = self.repo.commit(manifest(description="private-description $(never-run)"))
        with open_queue(self.queue, source=self.repo.source()) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)

    def accept(self):
        with open_queue(self.queue) as queue:
            return queue.decide(self.commit, TASK_PATH, self.candidate.review_token, "accepted", "Synthetic operator review")

    def grant(self, mode="success"):
        return grant(self.queue, self.state, "sample", 1, self.candidate.review_token, mode=mode)

    def test_acceptance_is_not_dispatch_and_grant_is_not_execution(self):
        with self.assertRaises(DriverError):
            self.grant()
        with patch("deskmate_formats.supervisor.driver.AppServer", side_effect=AssertionError("grant dispatched")):
            self.accept()
            result = self.grant()
        view = inspect(self.state, result["claim"])
        self.assertFalse(view["attempted"])
        self.assertEqual(view["operations"], [])
        self.assertEqual(result["binding"]["source"]["commit"], self.commit)
        self.assertEqual(result["binding"]["source"]["sha256"], sha256(self.candidate.raw).hexdigest())

    def test_exact_grant_single_dispatch_and_durable_receipt(self):
        self.accept()
        granted = self.grant()
        queue_bytes = (self.queue / "task-queue.sqlite3").read_bytes()
        with self.assertRaises(DriverError):
            dispatch(self.queue, self.state, granted["claim"], "0" * 64)
        result = dispatch(self.queue, self.state, granted["claim"], granted["dispatch_token"])
        self.assertEqual(result["state"], "completed", result)
        self.assertEqual(result["binding"], granted["binding"])
        before = (self.state / granted["claim"] / "evidence" / "peer.json").read_bytes()
        for action in (lambda: self.grant(), lambda: dispatch(self.queue, self.state, granted["claim"], granted["dispatch_token"])):
            with self.assertRaises(DriverError):
                action()
        self.assertEqual((self.state / granted["claim"] / "evidence" / "peer.json").read_bytes(), before)
        self.assertEqual((self.queue / "task-queue.sqlite3").read_bytes(), queue_bytes)
        self.assertEqual(inspect(self.state, granted["claim"])["outcome"], result)

    def test_git_movement_is_inert_and_new_accepted_revision_invalidates_old_grant(self):
        self.accept()
        granted = self.grant()
        commit = self.repo.commit(manifest(revision=2, idempotency_key="sample-2"))
        self.assertFalse(inspect(self.state, granted["claim"])["attempted"])
        with open_queue(self.queue) as queue:
            candidate = queue.discover(commit, TASK_PATH)
            queue.decide(commit, TASK_PATH, candidate.review_token, "accepted", "Review revised input")
        with self.assertRaises(DriverError):
            dispatch(self.queue, self.state, granted["claim"], granted["dispatch_token"])
        self.assertFalse(inspect(self.state, granted["claim"])["attempted"])

    def test_unknown_approval_and_lost_ack_leave_blocked_no_new_grant(self):
        for mode in ("driver-approval", "lost-ack"):
            with self.subTest(mode=mode):
                # Independent queue/state per experiment, no retry of an uncertain intent.
                self.state = self.root / mode
                if mode == "driver-approval":
                    self.accept()
                granted = self.grant(mode)
                result = dispatch(self.queue, self.state, granted["claim"], granted["dispatch_token"])
                self.assertEqual(result["state"], "blocked")
                with self.assertRaises(DriverError):
                    dispatch(self.queue, self.state, granted["claim"], granted["dispatch_token"])
                self.assertTrue(inspect(self.state, granted["claim"])["attempted"])

    def test_stale_acceptance_token_and_path_escape_refused(self):
        self.accept()
        with self.assertRaises(DriverError):
            grant(self.queue, self.state, "sample", 1, "0" * 64)
        with self.assertRaises(DriverError):
            dispatch(self.queue, self.state, "../escape", "0" * 64)

    def test_no_live_bridge_entry_point_or_worker_switch(self):
        self.accept()
        granted = self.grant()
        plan, _ = load_plan(self.state / granted["claim"])
        self.assertEqual(plan["kind"], "synthetic")
        self.assertIn("deskmate_formats.supervisor.synthetic_peer", plan["argv"])
        self.assertNotIn("app-server", plan["argv"])

    def test_single_state_lock_blocks_concurrent_dispatch_without_child(self):
        self.accept()
        granted = self.grant()
        with journal_lock(self.state), patch("subprocess.Popen", side_effect=AssertionError("concurrent child")):
            with self.assertRaises(OSError):
                dispatch(self.queue, self.state, granted["claim"], granted["dispatch_token"])
        self.assertFalse(inspect(self.state, granted["claim"])["attempted"])


@unittest.skipUnless(AVAILABLE, "requires supervisor extra and supported process identity")
class BridgeHttpTests(LocalObserver):
    def setUp(self):
        # The completed spool must exist before LocalObserver creates the listener.
        pass

    def make_server(self):
        return ObserverServer(self.registry, port=0, agent_publication=self.feed.publication)

    def test_completed_receipt_visible_without_control_or_private_data(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        repo = TaskRepo(root / "git")
        commit = repo.commit(manifest(description="private-description"))
        with open_queue(root / "queue", source=repo.source()) as queue:
            candidate = queue.discover(commit, TASK_PATH)
            queue.decide(commit, TASK_PATH, candidate.review_token, "accepted", "Synthetic approval")
        granted = grant(root / "queue", root / "bridge", "sample", 1, candidate.review_token)
        outcome = dispatch(root / "queue", root / "bridge", granted["claim"], granted["dispatch_token"])
        self.assertEqual(outcome["state"], "completed")
        run_dir = root / "bridge" / granted["claim"]
        self.feed = self.enterContext(AgentJournalFeed(run_dir / "spool"))
        super().setUp()
        paths = (run_dir / "receipts" / "operations.sqlite3", run_dir / "outcome.json",
                 run_dir / "evidence" / "peer.json", root / "queue" / "task-queue.sqlite3")
        before = [path.read_bytes() for path in paths]
        with patch("subprocess.Popen", side_effect=AssertionError("HTTP launched a child")), patch(
                "deskmate_formats.supervisor.task_queue.sqlite3.connect", side_effect=AssertionError("HTTP opened queue")):
            for _ in range(25):
                body = self.request("/api/v1/events")[2]
                self.assertIn(b"Synthetic dispatch completed", body)
                for secret in (b"private-description", b"test-thread", b"S0_CANARY_OK", str(root).encode()):
                    self.assertNotIn(secret, body)
            self.assertEqual(self.request("/api/v1/events", method="POST")[0], 405)
            self.assertEqual(self.request("/api/v1/dispatch")[0], 404)
            self.assertEqual(self.request("/api/v1/operations")[0], 404)
            self.assertEqual(self.request("/api/v1/agents?decision=accept")[0], 400)
        self.assertEqual([path.read_bytes() for path in paths], before)
        events = json.loads(body)["events"]
        self.assertTrue(any(row["type"] == "turn.completed" for row in events))
