"""Campaign registry, exclusive leases and reconciliation without blind takeover."""

from datetime import timedelta
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.supervisor import campaigns


class CampaignRegistryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.directory = self.root / "registry"

    def registry(self, *, create=False):
        return campaigns.open_registry(self.directory, create=create)

    def register(self, registry, identifier, provider="codex"):
        registry.register(identifier, owner="Synthetic Owner", provider=provider,
                          branch=f"codex/{identifier}", worktree=str(self.root / identifier),
                          purpose="Synthetic coordination test")

    def test_registration_status_and_handoff(self):
        with self.registry(create=True) as registry:
            record = registry.register(
                "audit-20261126", owner="Freebuff", provider="freebuff",
                branch="freebuff/audit", worktree=str(self.root / "wt"),
                purpose="Audit supervisor state", base_commit="a" * 40)
            self.assertEqual((record.status, record.provider, record.base_commit),
                             ("active", "freebuff", "a" * 40))
            with self.assertRaises(campaigns.RegistryError):
                registry.register("audit-20261126", owner="X", provider="codex",
                                  branch="codex/x", worktree=str(self.root), purpose="duplicate")
            for bad in ({"provider": "other"}, {"branch": "bad branch"},
                        {"worktree": "relative/path"}, {"base_commit": "abc"}):
                arguments = {"owner": "X", "provider": "codex", "branch": "codex/y",
                             "worktree": str(self.root), "purpose": "p"} | bad
                with self.subTest(bad=bad), self.assertRaises(campaigns.RegistryError):
                    registry.register("another", **arguments)
            self.assertEqual(registry.set_status("audit-20261126", "blocked",
                                                 reason="awaiting review").status, "blocked")
            self.assertEqual(registry.handoff("audit-20261126", owner="ChatGPT").owner, "ChatGPT")
            with self.assertRaises(campaigns.RegistryError):
                registry.set_status("unknown", "active")

    def test_conflicting_reservations_leave_the_registry_unchanged(self):
        now = campaigns.utcnow()
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("worktree:alpha", "alpha", pid=os.getpid(),
                             process_identity="synthetic-alpha", ttl_seconds=600, now=now)
            with self.assertRaises(campaigns.LeaseConflict):
                registry.acquire("worktree:alpha", "beta", pid=os.getpid(),
                                 process_identity="synthetic-beta", ttl_seconds=600, now=now)
            with self.assertRaises(campaigns.LeaseConflict):
                registry.reserve(["worktree:beta", "worktree:alpha"], "beta", pid=os.getpid(),
                                 process_identity="synthetic-beta", ttl_seconds=600, now=now)
            self.assertIsNone(registry.lease("worktree:beta", now=now))
            self.assertEqual(registry.lease("worktree:alpha", now=now).campaign, "alpha")
            with self.assertRaises(campaigns.RegistryError):
                registry.release("worktree:alpha", "beta")
            self.assertTrue(registry.release("worktree:alpha", "alpha"))
            self.assertIsNone(registry.lease("worktree:alpha", now=now))

    def test_expired_lease_blocks_implicit_takeover(self):
        now = campaigns.utcnow()
        later = now + timedelta(seconds=7200)
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("emulator:rsx-02", "alpha", pid=os.getpid(),
                             process_identity="synthetic-alpha", ttl_seconds=60, now=now)
            lease = registry.lease("emulator:rsx-02", now=later, probe=lambda *_: "alive")
            self.assertTrue(lease.stale)
            self.assertEqual(lease.campaign, "alpha")
            with self.assertRaises(campaigns.LeaseConflict):
                registry.acquire("emulator:rsx-02", "beta", pid=os.getpid(),
                                 process_identity="synthetic-beta", ttl_seconds=60, now=later)
            with self.assertRaisesRegex(campaigns.RegistryError, "has not expired"):
                registry.reclaim("emulator:rsx-02", "beta", operator_reason="Operator reassignment",
                                 now=now, probe=lambda *_: "stopped")

    def test_reclaim_requires_a_positively_dead_owner(self):
        now = campaigns.utcnow()
        later = now + timedelta(seconds=7200)
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("emulator:rsx-02", "alpha", pid=os.getpid(),
                             process_identity="synthetic-alpha", ttl_seconds=60, now=now)
            for observed in ("alive", "unknown", "identity-mismatch"):
                with self.subTest(observed=observed):
                    with self.assertRaisesRegex(campaigns.RegistryError,
                                                "not positively stopped"):
                        registry.reclaim("emulator:rsx-02", "beta",
                                         operator_reason="Operator reassignment",
                                         now=later, probe=lambda *_, value=observed: value)
            with self.assertRaises(campaigns.RegistryError):
                registry.reclaim("emulator:rsx-02", "beta", operator_reason="   ",
                                 now=later, probe=lambda *_: "stopped")
            reclaimed = registry.reclaim("emulator:rsx-02", "beta",
                                         operator_reason="Operator reassignment",
                                         now=later, probe=lambda *_: "stopped")
            self.assertEqual(reclaimed.campaign, "beta")
            takeover = registry.takeovers()[0]
            self.assertEqual((takeover["previous_campaign"], takeover["new_campaign"]),
                             ("alpha", "beta"))
            self.assertEqual(takeover["reason"], "Operator reassignment")

    def test_renewal_extends_only_the_owner(self):
        now = campaigns.utcnow()
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("socket:86box-01", "alpha", pid=os.getpid(),
                             process_identity="synthetic-alpha", ttl_seconds=60, now=now)
            renewed = registry.renew("socket:86box-01", "alpha", ttl_seconds=600, now=now)
            self.assertFalse(renewed.stale)
            with self.assertRaises(campaigns.RegistryError):
                registry.renew("socket:86box-01", "beta", ttl_seconds=600, now=now)

    def test_public_summary_omits_private_locators_and_process_identity(self):
        now = campaigns.utcnow()
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            registry.acquire("worktree:alpha", "alpha", pid=os.getpid(),
                             process_identity="synthetic-alpha", ttl_seconds=60, now=now)
            summary = campaigns.summarize(registry, now=now, probe=lambda *_: "alive")
        dumped = json.dumps(summary)
        self.assertEqual(summary["lease_count"], 1)
        self.assertNotIn(str(self.root), dumped)
        self.assertNotIn("synthetic-alpha", dumped)
        self.assertNotIn('"pid"', dumped)
        self.assertEqual(summary["campaigns"][0]["resources"][0]["name"], "worktree:alpha")

    def test_export_writes_the_public_summary(self):
        output = self.root / "view.json"
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            campaigns.export(registry, output)
        self.assertEqual(json.loads(output.read_text())["lease_count"], 0)


if __name__ == "__main__":
    unittest.main()
