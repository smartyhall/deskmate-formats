"""Snapshot collection from real local records, with explicit gaps."""

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.observer import campaigns as projection
from deskmate_formats.supervisor import campaigns, deterministic, snapshot


class SnapshotCollectorTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.registry = self.root / "registry"
        self.worktree = self.root / "worktree"
        self.worktree.mkdir()
        (self.worktree / "README.md").write_text("synthetic\n", encoding="utf-8")
        with campaigns.open_registry(self.registry, create=True) as registry:
            registry.register("alpha", owner="Freebuff", provider="freebuff",
                              branch="freebuff/alpha", worktree=str(self.worktree),
                              purpose="Synthetic snapshot test")
            registry.acquire("worktree:alpha", "alpha", pid=os.getpid(),
                             process_identity="snapshot-owner", ttl_seconds=600)

    def attempt(self, name="attempt", *, campaign="alpha"):
        state = self.root / name
        attempt = deterministic.prepare(
            state, campaign=campaign, procedure="hash-files",
            arguments={"paths": ["README.md"]}, working_directory=str(self.worktree))
        return state, deterministic.run(state, authorization=attempt.plan_sha256)

    def test_snapshot_reports_measured_activity_from_real_outcomes(self):
        state, _ = self.attempt()
        now = datetime.now(UTC)
        document = snapshot.collect(registry_directory=self.registry, attempts=[state], now=now)
        self.assertFalse(document["synthetic"])
        self.assertEqual(document["unreachable"], [])
        entry = document["campaigns"][0]
        self.assertEqual((entry["id"], entry["status"], entry["provider"]),
                         ("alpha", "active", "freebuff"))
        task = entry["tasks"][0]
        self.assertEqual((task["state"], task["exit_status"]), ("completed", 0))
        self.assertEqual(task["worker"], "deterministic-local")
        self.assertEqual(entry["resources"][0]["name"], "worktree:alpha")
        self.assertEqual(entry["measurements"], [])
        kinds = {source["kind"] for source in entry["sources"]}
        self.assertEqual(kinds, {"recorded", "observed"})

    def test_unreachable_attempt_is_reported_without_a_private_path(self):
        document = snapshot.collect(registry_directory=self.registry,
                                    attempts=[self.root / "missing-attempt"])
        self.assertEqual(len(document["unreachable"]), 1)
        self.assertIn("missing-attempt", document["unreachable"][0])
        self.assertNotIn(str(self.root), json.dumps(document["unreachable"]))

    def test_an_unregistered_campaign_is_not_given_a_status_it_never_had(self):
        state, _ = self.attempt(campaign="unregistered")
        document = snapshot.collect(registry_directory=self.registry, attempts=[state])
        entry = {item["id"]: item for item in document["campaigns"]}["unregistered"]
        self.assertEqual(entry["status"], "unrecorded")
        self.assertEqual(entry["owner"], "unknown")
        self.assertEqual(entry["blockers"][0]["kind"], "registry")

    def test_receipts_supply_measurements_and_bad_receipts_are_unreachable(self):
        receipt = self.root / "receipt.json"
        receipt.write_text(json.dumps({
            "schema_version": 1, "campaign_id": "alpha", "checkpoint": "startup",
            "measurements": [{"metric": "allowance_remaining_hours", "value": None,
                              "unit": "hours", "scope": "account", "semantics": "remaining",
                              "source": "unavailable", "observed_at_utc": None, "known": False}],
        }), encoding="utf-8")
        broken = self.root / "broken.json"
        broken.write_text("{", encoding="utf-8")
        document = snapshot.collect(registry_directory=self.registry,
                                    receipts=[receipt, broken])
        entry = document["campaigns"][0]
        self.assertEqual(entry["measurements"][0]["metric"], "allowance_remaining_hours")
        self.assertFalse(entry["measurements"][0]["known"])
        self.assertIsNone(entry["measurements"][0]["value"])
        self.assertTrue(any("broken.json" in item for item in document["unreachable"]))

    def test_frozen_document_round_trips_through_the_read_only_projection(self):
        state, _ = self.attempt()
        output = self.root / "snapshot.json"
        document = snapshot.collect(registry_directory=self.registry, attempts=[state])
        snapshot.write(document, output)
        loaded = projection.load(output)
        view = projection.projection(loaded, now=datetime.now(UTC))
        self.assertEqual(view["campaign_count"], 1)
        self.assertEqual(view["unreachable"], [])
        self.assertEqual(view["campaigns"][0]["tasks"][0]["state_basis"], "receipt")
        text = projection.render(view, "text")[1]
        self.assertIn("Unreachable      0", text)
        self.assertIn("measured", text)

    def test_stale_and_synthetic_sources_stay_distinguishable(self):
        document = snapshot.collect(registry_directory=self.registry,
                                    now=datetime(2026, 11, 26, 12, 0, tzinfo=UTC))
        document["campaigns"][0]["synthetic"] = True
        view = projection.projection(document, now=datetime(2026, 11, 26, 14, 0, tzinfo=UTC))
        self.assertTrue(view["stale"])
        self.assertTrue(view["campaigns"][0]["synthetic"])
        self.assertEqual(view["campaigns"][0]["activity"]["basis"], "unknown")
        self.assertIn("SYNTHETIC", projection.render(view, "text")[1])
        self.assertIn("(synthetic)", projection.render(view, "html")[1])

    def test_invalid_unreachable_entries_are_refused(self):
        document = snapshot.collect(registry_directory=self.registry)
        document["unreachable"] = "not-a-list"
        with self.assertRaises(projection.CampaignSnapshotError):
            projection.validate(document)

    def test_unreadable_registry_is_a_refusal_not_an_empty_snapshot(self):
        with self.assertRaises(campaigns.RegistryError):
            snapshot.collect(registry_directory=self.root / "absent-registry")

    def test_lease_freshness_is_carried_from_the_registry(self):
        document = snapshot.collect(
            registry_directory=self.registry,
            now=datetime.now(UTC) + timedelta(hours=2))
        resource = document["campaigns"][0]["resources"][0]
        self.assertTrue(resource["stale"])
        self.assertIn("expires_at", resource)


if __name__ == "__main__":
    unittest.main()
