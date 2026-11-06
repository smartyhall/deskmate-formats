"""Synthetic child through the private journal and existing read-only HTTP API."""

from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest

from codex_child_fixture import wrapper_command
from deskmate_formats.automation.readonly import Adapter
from deskmate_formats.observer.agent_feed import AgentJournalFeed
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.observer.journal import JournalBusy, publish_event, read_journal
from mcp_fixture import NativePeer
from observatory_fixture import event
from test_observer_codex_exec import FIXTURES
from test_observer_http import LocalObserver


class CodexHttpTests(LocalObserver):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        self.spool = root / "journal"
        self.gate = root / "release"
        self.peer = NativePeer()
        self.addCleanup(self.peer.close)
        config = self.peer.config()
        config["observer"] = {"port": 0}
        self.owner = Adapter(config)
        self.addCleanup(self.owner.close)
        self.feed_context = self.enterContext(ExitStack())
        self.baseline = self.native_counters()
        self.start_feed()

    def native_counters(self):
        return (self.peer.connections, self.peer.authentications, tuple(self.peer.commands),
                self.peer.ms, self.peer.frames, self.peer.resets)

    def start_feed(self):
        self.feed = self.feed_context.enter_context(AgentJournalFeed(self.spool, interval=0.05,
                                                                    quiet_seconds=0.05, stale_seconds=2))
        super().setUp()

    def make_server(self):
        return ObserverServer(self.owner.registry, port=0, agent_publication=self.feed.publication)

    def wait_for(self, predicate):
        deadline = monotonic() + 6
        while monotonic() < deadline:
            status, _, body = self.request("/api/v1/agents/codex")
            if status == 200:
                agent, = json.loads(body)["agents"]
                if predicate(agent):
                    return agent
            else:
                self.assertEqual(status, 404)
            sleep(0.03)
        self.fail("agent state did not appear in the existing API")

    def test_success_is_sanitized_and_replays_with_zero_native_connections(self):
        command = wrapper_command(self.spool, FIXTURES / "success.jsonl")
        result = subprocess.run(command, capture_output=True, timeout=10)
        self.assertEqual((result.returncode, result.stdout, result.stderr.splitlines()),
                         (0, b"", [b"synthetic child stderr"]))
        agent = self.wait_for(lambda row: row["process"] == "stopped" and row["transport"] == "disconnected")
        self.assertEqual((agent["state"], agent["reported_lifecycle"], agent["pending_approval_count"]),
                         ("completed", "completed", 0))
        self.assertEqual(agent["last_activity"]["type"], "turn.completed")
        self.assertFalse(agent["historical"])
        path = "/api/v1/agents/codex/events?after=0"
        status, _, body = self.request(path)
        self.assertEqual(status, 200)
        page = json.loads(body)
        types = [row["type"] for row in page["events"]]
        self.assertEqual([kind for kind in types if not kind.startswith(("process.", "source."))], [
            "session.started", "turn.started", "plan.updated", "command.started", "tool.started",
            "command.completed", "tool.completed", "tool.completed", "plan.updated", "agent.note",
            "plan.updated", "turn.completed",
        ])
        self.assertEqual(types.count("process.exited"), 1)
        self.assertEqual(types.count("source.disconnected"), 1)
        self.assertEqual(page["next_cursor"], agent["latest_cursor"])
        self.assertEqual(self.request("/api/v1/events?type=process.exited")[0], 200)
        self.assertEqual(self.request(path, method="POST")[0], 405)
        self.assertEqual(self.request("/api/v1/journal")[0], 404)
        self.assertIsNone(json.loads(self.request("/api/status")[2])["observation"])
        for sentinel in (b"private-", b"<script>", b"01234567-89ab", b"item_1", b"line_sha256",
                         b"aggregated_output", b'"details"', b"reasoning", b"approval.requested", b"test.completed"):
            self.assertNotIn(sentinel, body)
        records = self.private_records()
        self.assertEqual(len(records), len(types) + 1)
        self.assertEqual(records[1]["details"]["thread_id"], "01234567-89ab-4def-8123-456789abcdef")
        self.assertTrue(all(row["source"] == "codex-exec-0.166.0" for row in page["events"]))
        self.assertEqual(self.native_counters(), self.baseline)
        self.assertEqual(self.baseline, (0, 0, (), 1000, 1, 1))

        self.stop()
        self.server.server_close()
        self.feed_context.close()
        self.start_feed()
        historical = self.wait_for(lambda row: row["historical"])
        self.assertEqual((historical["state"], historical["process"], historical["transport"]),
                         ("completed", "stopped", "disconnected"))
        self.assertIsNone(historical["activity_age_ms"])
        self.assertEqual(self.request(path)[2], body)
        self.assertEqual(self.private_records(), records)
        self.assertEqual(self.native_counters(), self.baseline)

    def private_records(self):
        for _ in range(50):
            try:
                return read_journal(self.spool).records
            except JournalBusy:
                sleep(0.02)
        self.fail("private replay remained busy")

    @unittest.skipUnless(sys.platform in ("win32", "linux"), "requires local process identity verification")
    def test_silence_is_not_completion_and_missing_terminal_remains_unreported(self):
        command = wrapper_command(self.spool, FIXTURES / "open-turn.jsonl", "--gate", str(self.gate), "--exit", "7")
        with subprocess.Popen(command, stderr=subprocess.DEVNULL) as wrapper:
            try:
                silent = self.wait_for(lambda row: row["state"] == "alive-no-new-events"
                                       and row["last_activity"] and row["last_activity"]["type"] == "command.started")
                self.assertEqual((silent["process"], silent["transport"], silent["reported_lifecycle"]),
                                 ("alive", "recent", "running"))
                self.assertIsNotNone(silent["verified_pid"])
                self.assertEqual(silent["pending_approval_count"], 0)
                self.assertEqual(silent["last_activity"]["type"], "command.started")
                self.assertIsNone(wrapper.poll())
            finally:
                self.gate.touch()
            self.assertEqual(wrapper.wait(timeout=8), 7)
        stopped = self.wait_for(lambda row: row["process"] == "stopped" and row["transport"] == "disconnected")
        self.assertEqual((stopped["state"], stopped["reported_lifecycle"]), ("disconnected", "running"))
        self.assertEqual(stopped["last_activity"], silent["last_activity"])
        self.assertEqual(self.native_counters(), self.baseline)

    def test_explicit_local_approval_remains_distinct_from_unsupported_source_record(self):
        child = subprocess.run(wrapper_command(self.spool, FIXTURES / "anomalies.jsonl"),
                               stderr=subprocess.DEVNULL, timeout=10)
        self.assertEqual(child.returncode, 0)
        row = self.wait_for(lambda row: row["process"] == "stopped")
        self.assertEqual(row["pending_approval_count"], 0)
        body = self.request("/api/v1/agents/codex/events?category=source")[2]
        self.assertNotIn(b"private-unknown-marker", body)
        self.assertNotIn(b"explicit-but-unsupported", body)
        for _ in range(50):
            try:
                publish_event(self.spool, event(1, "approval.requested", agent="beta",
                                               correlation={"approval": "synthetic-request"}))
                break
            except JournalBusy:
                sleep(0.02)
        else:
            self.fail("explicit producer could not publish")
        deadline = monotonic() + 5
        while monotonic() < deadline:
            status, _, body = self.request("/api/v1/agents/beta")
            if status == 200:
                explicit, = json.loads(body)["agents"]
                self.assertEqual(explicit["pending_approval_ids"], ["synthetic-request"])
                break
            sleep(0.03)
        else:
            self.fail("explicit approval was not published")
        self.assertEqual(self.native_counters(), self.baseline)
