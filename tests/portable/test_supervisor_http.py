"""Observe the offline S0 pipeline through the actual read-only HTTP listener."""

from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest
from unittest.mock import patch

from deskmate_formats.automation.readonly import Adapter
from deskmate_formats.observer.agent_feed import AgentJournalFeed
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.supervisor.ledger import DATABASE, open_ledger
from deskmate_formats.supervisor.operations import Operations
from deskmate_formats.supervisor.protocol import Approval, TransportError
from deskmate_formats.supervisor.telemetry import AppServerTelemetry

from mcp_fixture import NativePeer
from test_observer_http import LocalObserver
from test_supervisor_protocol import AVAILABLE, INPUT, fake


@unittest.skipUnless(AVAILABLE, "requires supervisor extra and Windows or Linux process identity")
class SupervisorHttpTests(LocalObserver):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.spool = self.root / "journal"
        self.receipts = self.root / "receipts"
        self.state = self.root / "synthetic.json"
        self.peer = NativePeer()
        self.addCleanup(self.peer.close)
        config = self.peer.config()
        config["observer"] = {"port": 0}
        self.owner = Adapter(config)
        self.addCleanup(self.owner.close)
        self.feed = self.enterContext(AgentJournalFeed(self.spool, interval=0.05))
        super().setUp()

    def make_server(self):
        return ObserverServer(self.owner.registry, port=0, agent_publication=self.feed.publication)

    def wait_for(self, predicate):
        deadline = monotonic() + 5
        while monotonic() < deadline:
            response = self.request("/api/v1/agents")[2]
            for agent in json.loads(response)["agents"]:
                if predicate(agent):
                    return agent
            sleep(0.02)
        self.fail("agent projection did not reach expected state")

    def pipeline(self, mode):
        contexts = self.enterContext(ExitStack())
        ledger = contexts.enter_context(open_ledger(self.receipts, create=True))
        client = contexts.enter_context(fake(self.state, mode))
        operations = Operations(client, ledger)
        feed = AppServerTelemetry(
            self.spool, generation=client.generation, pid=client.pid, process_identity=client.process_identity,
        )
        feed.connected()
        feed.sample_process()
        operations.execute("thread", "thread/start", {})
        return client, ledger, operations, feed

    def assert_no_guest_work(self):
        self.assertEqual((self.peer.connections, self.peer.authentications, self.peer.commands), (0, 0, []))
        self.assertEqual((self.peer.ms, self.peer.frames, self.peer.resets), (1000, 1, 1))

    def test_browser_observes_approval_and_terminal_without_authority(self):
        client, ledger, ops, feed = self.pipeline("approval")
        turn = ops.execute("turn", "turn/start", INPUT)["turn"]
        feed.bind(ledger.get("turn"))
        approvals = []
        while (event := ops.next_event(timeout=0.15)) is not None:
            feed.observe(event)
            if isinstance(event, Approval):
                approvals.append(event)
        approval, = approvals
        observed = self.wait_for(lambda agent: agent["state"] == "approval-needed")
        self.assertEqual((observed["reported_lifecycle"], observed["process"], observed["transport"],
                          observed["pending_approval_count"]), ("running", "alive", "recent", 1))
        db = self.receipts / DATABASE
        digest = sha256(db.read_bytes()).digest()
        state = self.state.read_bytes()
        with patch.object(client, "_write", side_effect=AssertionError("browser wrote to app-server")) as write:
            for path, method, status in (
                ("/api/v1/events", "GET", 200),
                ("/api/v1/events", "POST", 405),
                ("/api/v1/agents/codex-supervisor", "GET", 200),
                ("/api/v1/agents/codex-supervisor/approve", "GET", 404),
                ("/api/v1/agents/codex-supervisor?decision=accept", "GET", 400),
                ("/api/v1/operations", "GET", 404),
            ):
                self.assertEqual(self.request(path, method=method)[0], status)
            write.assert_not_called()
        self.assertEqual(sha256(db.read_bytes()).digest(), digest)
        self.assertEqual(self.state.read_bytes(), state)
        self.assertEqual(ledger.get("turn").state, "running")
        self.assert_no_guest_work()
        client.decline(approval, generation=client.generation, thread_id=INPUT["threadId"],
                       turn_id=turn["id"], authorized=True)
        while (event := ops.next_event(timeout=0.15)) is not None:
            feed.observe(event)
        self.assertEqual(ledger.get("turn").state, "completed")
        feed.disconnected()
        client.close()
        feed.sample_process()
        ended = self.wait_for(lambda agent: agent["process"] == "stopped"
                              and agent["transport"] == "disconnected")
        self.assertEqual((ended["state"], ended["transport"], ended["pending_approval_count"]),
                         ("completed", "disconnected", 0))
        self.assertEqual(ended["last_activity"]["type"], "turn.completed")
        body = self.request("/api/v1/events")[2]
        for sentinel in (b"private-canary", b"test-thread", b"synthetic-tool", turn["id"].encode(),
                         b'"decision"', b'"details"'):
            self.assertNotIn(sentinel, body)
        self.assertNotIn(b"private-canary", (self.spool / "events.jsonl").read_bytes())
        self.assertFalse(feed.publication_failed)
        self.assert_no_guest_work()

    def test_disconnect_reports_uncertainty_separately_from_live_process(self):
        client, ledger, ops, feed = self.pipeline("lost-ack-live")
        with self.assertRaises(TransportError):
            ops.execute("lost", "turn/start", INPUT)
        feed.disconnected()
        feed.sample_process()
        row = self.wait_for(lambda agent: agent["transport"] == "disconnected")
        self.assertEqual((row["state"], row["process"], row["reported_lifecycle"], row["last_activity"]),
                         ("disconnected", "alive", "unknown", None))
        self.assertEqual(ledger.get("lost").state, "needs-reconciliation")
        client.close()
        feed.sample_process()
        stopped = self.wait_for(lambda agent: agent["process"] == "stopped")
        self.assertEqual(stopped["reported_lifecycle"], "unknown")
        self.assert_no_guest_work()

    def test_early_terminal_failure_updates_receipt_and_projection(self):
        _, ledger, ops, feed = self.pipeline("failed")
        ops.execute("turn", "turn/start", INPUT)
        feed.bind(ledger.get("turn"))
        while (event := ops.next_event(timeout=0.15)) is not None:
            feed.observe(event)
        row = self.wait_for(lambda agent: agent["reported_lifecycle"] == "failed")
        self.assertEqual(row["last_activity"]["type"], "turn.failed")
        self.assertEqual(ledger.get("turn").state, "failed")
        self.assert_no_guest_work()
