"""Read-only campaign projection: measured activity, unknown state, escaped output."""

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.observer import campaigns

NOW = datetime(2026, 11, 26, 12, 10, 0, tzinfo=UTC)


def measurement(metric, value, unit, *, known=True, at="2026-11-26T12:05:00Z", source="ui-observation"):
    return {"metric": metric, "value": value if known else None, "unit": unit,
            "scope": "account", "semantics": "remaining", "source": source,
            "observed_at_utc": at if known else None, "known": known}


def snapshot():
    return {
        "schema_version": 1,
        "generated_at_utc": "2026-11-26T12:09:00Z",
        "campaigns": [
            {
                "id": "supervisor-audit", "owner": "Freebuff", "provider": "freebuff",
                "worker_kind": "freebuff", "status": "active", "branch": "freebuff/audit",
                "base_commit": "a" * 40, "milestone": "deterministic backend",
                "checkpoint": "none",
                "tasks": [{"id": "hash-fixtures", "revision": 1, "state": "completed",
                           "procedure": "hash-files", "worker": "deterministic-local",
                           "attempt": "attempt-1",
                           "started_at_utc": "2026-11-26T12:00:00Z",
                           "finished_at_utc": "2026-11-26T12:00:04Z",
                           "exit_status": 0, "result_sha256": "b" * 64}],
                "results": [{"label": "portable-tests", "state": "passed", "exit_status": 0}],
                "resources": [{"name": "worktree:supervisor-audit", "state": "held",
                               "owner": "supervisor-audit",
                               "expires_at": "2026-11-26T13:00:00Z", "stale": False}],
                "measurements": [measurement("allowance_remaining_hours", 21.0, "hours"),
                                 measurement("context_percent", None, "percent", known=False)],
                "evidence": [{"label": "attempt", "locator": "private/attempt-1",
                              "sha256": "c" * 64}],
            },
            {
                "id": "website", "owner": "ChatGPT", "provider": "chatgpt",
                "worker_kind": "chatgpt", "status": "blocked",
                "blockers": [{"summary": "awaiting operator review", "kind": "approval"}],
                "approvals": [{"id": "approval-1", "summary": "merge navigation PR"}],
                "tasks": [], "measurements": [],
            },
        ],
    }


class CampaignProjectionTests(unittest.TestCase):
    def test_projection_separates_measured_activity_from_unknown_state(self):
        view = campaigns.projection(snapshot(), now=NOW)
        self.assertEqual(view["campaign_count"], 2)
        self.assertEqual(view["task_states"], {"completed": 1})
        measured, unknown = view["campaigns"]
        self.assertEqual(measured["id"], "supervisor-audit")
        self.assertEqual(measured["activity"]["basis"], "measured")
        self.assertEqual(measured["activity"]["last_observed_at_utc"], "2026-11-26T12:00:00Z")
        self.assertEqual(measured["tasks"][0]["state_basis"], "receipt")
        self.assertEqual(unknown["activity"]["basis"], "unknown")
        self.assertIsNone(unknown["activity"]["last_observed_at_utc"])
        self.assertEqual(unknown["status"], "blocked")
        self.assertEqual(unknown["blockers"][0]["summary"], "awaiting operator review")
        self.assertFalse(view["stale"])

    def test_measurements_keep_source_and_freshness(self):
        view = campaigns.projection(snapshot(), now=NOW)
        known, missing = view["campaigns"][0]["measurements"]
        self.assertTrue(known["known"])
        self.assertEqual((known["value"], known["unit"]), (21.0, "hours"))
        self.assertTrue(known["fresh"])
        self.assertEqual(known["age_seconds"], 300.0)
        self.assertFalse(missing["known"])
        self.assertIsNone(missing["value"])
        stale = campaigns.projection(snapshot(), now=datetime(2026, 11, 26, 14, 0, tzinfo=UTC))
        self.assertTrue(stale["stale"])
        self.assertFalse(stale["campaigns"][0]["measurements"][0]["fresh"])

    def test_projection_does_not_mutate_the_snapshot(self):
        value = snapshot()
        reference = deepcopy(value)
        campaigns.projection(value, now=NOW)
        self.assertEqual(value, reference)

    def test_text_and_html_rendering_are_safe(self):
        value = snapshot()
        value["campaigns"][1]["owner"] = "<script>alert(1)</script>"
        view = campaigns.projection(value, now=NOW)
        html_type, html = campaigns.render(view, "html")
        self.assertEqual(html_type, "text/html; charset=utf-8")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        text_type, text = campaigns.render(view, "text")
        self.assertEqual(text_type, "text/plain; charset=us-ascii")
        text.encode("ascii")
        self.assertIn("supervisor-audit", text)
        json_type, body = campaigns.render(view, "json")
        self.assertEqual(json_type, "application/json")
        self.assertEqual(json.loads(body)["campaign_count"], 2)
        with self.assertRaises(campaigns.CampaignSnapshotError):
            campaigns.render(view, "xml")

    def test_unsupported_or_malformed_snapshots_are_refused(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "view.json"
            path.write_text(json.dumps(snapshot()))
            self.assertEqual(campaigns.load(path)["schema_version"], 1)
            for bad in ({"schema_version": 2, "generated_at_utc": "2026-11-26T12:00:00Z",
                         "campaigns": []},
                        {"schema_version": 1, "generated_at_utc": "not-a-time", "campaigns": []},
                        {"schema_version": 1, "generated_at_utc": "2026-11-26T12:00:00Z",
                         "campaigns": [{"id": "", "owner": "x"}]}):
                with self.subTest(bad=bad):
                    path.write_text(json.dumps(bad))
                    with self.assertRaises(campaigns.CampaignSnapshotError):
                        campaigns.load(path)
            path.write_bytes(b"{not json")
            with self.assertRaises(campaigns.CampaignSnapshotError):
                campaigns.load(path)
            path.write_bytes(b"x" * (campaigns.MAX_BYTES + 1))
            with self.assertRaises(campaigns.CampaignSnapshotError):
                campaigns.load(path)


if __name__ == "__main__":
    unittest.main()
