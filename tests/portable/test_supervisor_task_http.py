"""Exercise one-way queue publication through the actual Observatory listener."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from deskmate_formats.automation.readonly import Adapter
from deskmate_formats.observer.agent_feed import AgentJournalFeed
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.observer.journal import JournalError, JournalLimits, publish_event, read_journal
from deskmate_formats.supervisor.task_manifest import TaskError
from deskmate_formats.supervisor.task_publication import publish_decision
from deskmate_formats.supervisor.task_queue import DATABASE, open_queue

from mcp_fixture import NativePeer
from task_fixture import REPOSITORY, TASK_PATH, TaskRepo, manifest
from test_observer_http import LocalObserver


class TaskHttpTests(LocalObserver):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.private = self.root / "queue"
        self.spool = self.root / "journal"
        self.repo = TaskRepo(self.root / "repo")
        self.peer = NativePeer()
        self.addCleanup(self.peer.close)
        config = self.peer.config()
        config["observer"] = {"port": 0}
        self.owner = Adapter(config)
        self.addCleanup(self.owner.close)

    def make_server(self):
        return ObserverServer(self.owner.registry, port=0, agent_publication=self.feed.publication)

    def prepare_decisions(self):
        document = b"private-document-canary"
        self.repo.stage("docs/private-canary.md", document)
        self.repo.stage("ops/tasks/declined.json", json.dumps(manifest(
            id="declined", idempotency_key="private-key-declined",
        )).encode())
        commit = self.repo.commit(manifest(
            description="private-body-canary $(touch never-executed)",
            title="private-title-canary", idempotency_key="private-key-sample",
            instructions=[{"path": "docs/private-canary.md", "sha256": sha256(document).hexdigest()}],
        ))
        with open_queue(self.private, source=self.repo.source()) as queue:
            for path, state in ((TASK_PATH, "accepted"), ("ops/tasks/declined.json", "rejected")):
                token = queue.discover(commit, path).review_token
                queue.decide(commit, path, token, state, "private-reason-canary")

    def test_decisions_replay_through_http_with_no_queue_git_or_native_work(self):
        self.prepare_decisions()
        self.assertEqual(publish_decision(self.private, self.spool, "declined", 1), (1, True))
        self.assertEqual(publish_decision(self.private, self.spool, "sample", 1), (2, True))
        self.assertEqual(publish_decision(self.private, self.spool, "declined", 1), (1, False))
        publish_event(self.spool, {
            "schema_version": 1, "source": "synthetic", "agent_id": "synthetic",
            "run_id": "synthetic", "origin_id": "synthetic", "source_sequence": 1,
            "visibility": "observer", "type": "task.accepted", "summary": "Fictional replay event",
            "correlation": {"task": "event-only"},
        })
        private_rows = read_journal(self.spool).records
        self.assertEqual(private_rows[1]["correlation"], {"task": "sample"})
        self.assertIsNotNone(private_rows[1]["source_time_utc"])
        for secret in (REPOSITORY.encode(), TASK_PATH.encode(), b"private-canary.md", b"private-body-canary",
                       b"private-title-canary", b"private-document-canary", b"private-key-sample",
                       b"private-reason-canary"):
            self.assertNotIn(secret, (self.spool / "events.jsonl").read_bytes())
        # Start the collector after all appends, then replay the same history on restart.
        with AgentJournalFeed(self.spool) as first:
            history = first.publication.view().events
            self.assertEqual(len(history), 3)
        self.feed = self.enterContext(AgentJournalFeed(self.spool))
        self.assertEqual(history, self.feed.publication.view().events)
        super().setUp()
        db = self.private / DATABASE
        before = sha256(db.read_bytes()).digest()
        query = "/api/v1/events?category=task"
        expected = self.request(query)[2]
        events = json.loads(expected)["events"]
        self.assertEqual([event["type"] for event in events],
                         ["task.rejected", "task.accepted", "task.accepted"])
        self.assertIn("Task declined r1 rejected at ", events[0]["summary"])
        self.assertIn("accepted=1, rejected=1", events[0]["summary"])
        self.assertIn("Task sample r1 accepted at ", events[1]["summary"])
        self.assertIn("accepted=1, rejected=0", events[1]["summary"])
        self.assertEqual(json.loads(self.request("/api/v1/agents")[2])["agents"], [])
        with patch("deskmate_formats.supervisor.task_queue.sqlite3.connect",
                   side_effect=AssertionError("browser touched queue")) as db_open, patch(
                       "deskmate_formats.supervisor.task_git.TrustedSource._run",
                       side_effect=AssertionError("browser ran Git")) as git:
            for index in range(320):
                method = "GET" if index % 2 == 0 else "HEAD"
                status, _, body = self.request(query, method=method)
                self.assertEqual((status, body), (200, expected if method == "GET" else b""))
            self.assertEqual(self.request(query, method="POST")[0], 405)
            self.assertEqual(self.request("/api/v1/tasks/accept")[0], 404)
            db_open.assert_not_called()
            git.assert_not_called()
        self.assertEqual(sha256(db.read_bytes()).digest(), before)
        with open_queue(self.private) as queue:
            self.assertIsNone(queue.get("event-only", 1))
            self.assertEqual(queue.counts()["accepted"], 1)
        self.assertEqual((self.peer.connections, self.peer.authentications, self.peer.commands), (0, 0, []))
        self.assertEqual((self.peer.ms, self.peer.frames, self.peer.resets), (1000, 1, 1))

    def test_publication_failure_leaves_decision_and_separates_paths(self):
        self.prepare_decisions()
        with self.assertRaisesRegex(TaskError, "separate"):
            publish_decision(self.private, self.private / "journal", "sample", 1)
        with self.assertRaisesRegex(TaskError, "finalized"):
            publish_decision(self.private, self.spool, "event-only", 1)
        with self.assertRaises(JournalError):
            publish_decision(self.private, self.spool, "sample", 1, limits=JournalLimits(max_bytes=1))
        with open_queue(self.private) as queue:
            self.assertEqual(queue.get("sample", 1).state, "accepted")
        self.assertEqual(publish_decision(self.private, self.spool, "sample", 1), (1, True))
