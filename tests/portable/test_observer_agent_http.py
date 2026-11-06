"""Exercise agent routes, refresh isolation and journal state recovery on loopback."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from unittest.mock import patch

from deskmate_formats.observer.agent_feed import AgentJournalFeed
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.observer.journal import JournalBusy, publish_event
from observatory_fixture import event
from test_observer_http import LocalObserver


class AgentHttpTests(LocalObserver):
    def setUp(self):
        self.spool = Path(self.enterContext(TemporaryDirectory())) / "spool"
        publish_event(self.spool, event(summary="<script>alert('synthetic')</script>",
                                       details={"private": "synthetic-detail-sentinel"}))
        publish_event(self.spool, event(agent="beta", visibility="private", summary="private-event-sentinel"))
        publish_event(self.spool, event(2, "approval.requested", correlation={"approval": "request-1"}))
        publish_event(self.spool, event(agent="gamma"))
        publish_event(self.spool, event(3, "tool.failed", severity="error"))
        self.feed = self.enterContext(AgentJournalFeed(self.spool, interval=0.05))
        super().setUp()

    def make_server(self):
        return ObserverServer(self.registry, port=0, agent_publication=self.feed.publication, agent_page_limit=2)

    def body(self, path):
        code, headers, body = self.request(path)
        self.assertEqual(code, 200)
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertNotIn("access-control-allow-origin", headers)
        self.assertNotIn(b"synthetic-detail-sentinel", body)
        self.assertNotIn(b"private-event-sentinel", body)
        self.assertNotIn(b"ingested_monotonic_ns", body)
        self.assertNotIn(b"source_time_utc", body)
        return json.loads(body)

    def test_pagination_filters_privacy_and_read_only_methods(self):
        page = self.body("/api/v1/events?after=0&limit=999")
        self.assertEqual((page["schema_version"], page["limit"], page["has_more"]), (1, 2, True))
        self.assertEqual([item["cursor"] for item in page["events"]], [1, 3])
        self.assertEqual(page["events"][0]["summary"], "<script>alert('synthetic')</script>")
        after = page["next_cursor"]
        page = self.body(f"/api/v1/events?after={after}")
        self.assertEqual([item["cursor"] for item in page["events"]], [4, 5])
        self.assertFalse(page["has_more"])
        self.assertEqual(self.body("/api/v1/events?after=5")["next_cursor"], 5)
        tail = self.body("/api/v1/events?tail=1&limit=1")
        self.assertEqual([item["cursor"] for item in tail["events"]], [5])
        for query in ("category=tool&severity=error", "type=tool.failed&run=run-alpha",
                      "agent=alpha&origin=fixture-alpha&after=3&machine=synthetic-rsx"):
            self.assertEqual([item["cursor"] for item in self.body("/api/v1/events?" + query)["events"]], [5])
        alpha, = self.body("/api/v1/agents/alpha")["agents"]
        self.assertEqual((alpha["historical"], alpha["state"], alpha["pending_approval_count"]),
                         (True, "disconnected", 1))
        gamma, = self.body("/api/v1/agents?before=5")["agents"]
        self.assertEqual((gamma["agent_id"], gamma["machine_ids"]), ("gamma", []))
        self.assertEqual(self.body("/api/v1/agents/alpha/events?after=3")["events"][0]["cursor"], 5)
        for path, expected in (
            ("/api/v1/events?after=00", 400), ("/api/v1/events?limit=0", 400),
            ("/api/v1/events?after=9007199254740992", 400), ("/api/v1/events?tail=1&after=0", 400),
            ("/api/v1/events?limit=1&limit=2", 400), ("/api/v1/events?summary=raw", 400),
            ("/api/v1/events?type=thinking", 400), ("/api/v1/events?severity=critical", 400),
            ("/api/v1/agents/alpha?agent=beta", 400), ("/api/v1/agents/beta", 404),
            ("/api/v1/agents/alpha/approve", 404), ("/api/v1/journal", 404),
        ):
            self.assertEqual(self.request(path)[0], expected, path)
        path = "/api/v1/events?limit=1"
        code, headers, body = self.request(path, method="HEAD")
        self.assertEqual((code, body), (200, b""))
        self.assertEqual(int(headers["content-length"]), len(self.request(path)[2]))
        self.assertEqual(self.request(path, method="POST")[0], 405)
        self.assertEqual(self.request(path, headers={"Host": "elsewhere.example"})[0], 400)
        self.assertEqual(self.request(path, headers={"Origin": "http://elsewhere.example"})[0], 403)
        html = self.request("/")[2]
        self.assertIn(b"Agent activity", html)
        self.assertNotIn(b"alert('synthetic')", html)
        script = self.request("/dashboard.js")[2]
        self.assertIn(b"heading.textContent = title", script)
        self.assertNotIn(b"innerHTML", script)

    def test_background_poll_publishes_new_activity_and_shutdown_is_clean(self):
        deadline = monotonic() + 5
        while True:
            try:
                receipt = publish_event(self.spool, event(4, "milestone.completed"))
            except JournalBusy:
                if monotonic() >= deadline:
                    raise
                sleep(0.02)
            else:
                break
        while self.feed.publication.view().events[-1].cursor != receipt.cursor and monotonic() < deadline:
            sleep(0.02)
        self.assertEqual(self.feed.publication.view().events[-1].cursor, receipt.cursor)
        with patch("deskmate_formats.observer.http.query_snapshot",
                   side_effect=AssertionError("machine route invoked agent query")):
            self.assertEqual(self.request("/api/status")[0], 200)
        alpha, = self.body("/api/v1/agents/alpha")["agents"]
        self.assertEqual((alpha["state"], alpha["historical"], alpha["last_activity"]["cursor"]),
                         ("approval-needed", False, receipt.cursor))
        self.stop()
        self.server.server_close()
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(self.server.fileno(), -1)
